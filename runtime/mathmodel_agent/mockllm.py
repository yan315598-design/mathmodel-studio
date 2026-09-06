"""MockLLM: 确定性罐装响应, 供无 API key 环境与测试使用。"""
from __future__ import annotations

import json
import re
from typing import Iterable

from .llm import LLMResponse

_STAGE_RE = re.compile(r"\[STAGE (\d+)")
_ITER_RE = re.compile(r"\[ITER (\d+)\]")

# 与 scripts/score_artifact.py 基线 DIM_WHITELIST 的 stage 0-2 一致
# (mock 仅对 0-2 产出 critique; 评审维度以脚本内白名单为准, 此处只为罐装数据)
_MOCK_DIMS = {
    0: ["1_role_clarity", "2_tools_ready", "3_time_planning",
        "4_problem_scan", "5_collab_protocol"],
    1: ["1_three_options_depth", "2_team_strength_match", "3_risk_identification",
        "4_time_feasibility", "5_decision_record_quality"],
    2: ["1_subproblem_decomposition", "2_key_variables_count", "3_math_skeleton_present",
        "4_data_alignment", "5_subproblem_dependency_identified"],
}

# 各 stage 的 decision_log.stages[n] 浅合并补丁 (罐头内容)
_STAGE_PATCHES = {
    0: {"team_roles": {"r1": "建模", "r2": "编程", "r3": "写作"},
        "tools_ready": ["python", "latex"],
        "checklist_completed": True,
        "problem_scan": {"problem_id": "A", "domain_keywords": ["优化", "调度"],
                         "subproblem_count": 3}},
    1: {"candidates_assessed": ["A", "B", "C"], "selected": "A",
        "rationale": "mock: 数据可得性与队伍技能匹配度最高",
        "rejected_alternatives": ["B", "C"], "risks_identified": ["数据噪声偏大"]},
    # F5: actual_qi_count = stage 2 分解出的实际子问数, runtime 据此原子迁移 stages["5"]
    2: {"decomposition": ["Q1 数据画像", "Q2 优化模型", "Q3 灵敏度分析"],
        "key_variables": ["x_ij", "c_j"], "key_constraints": ["容量上限"],
        "objective_per_subproblem": {"Q1": "清洗与统计画像", "Q2": "最小化总延迟"},
        "actual_qi_count": 3},
    # stage 9 终态字段: runtime 终态校验要求两字段为 true 才判 completed
    9: {"skill_issues_consumed": True, "submission_ready": True},
}

# 各 stage 需要申请的必停点 (v2.3.0 HIL-lite): mock 在正文发 checkpoint_request 指令,
# 由 runtime paused → CLI answer → resume 完成; mock 绝不自写 checkpoints 内容。
# gate 1/4/6-8 无专属必停点, 只查 scores。
_CHECKPOINT_REQUESTS = {
    0: "kickoff_5q",
    2: "analysis_confirm",
}
_CP_ANSWERED_RE = re.compile(r"^\[CP_ANSWERED (\S+)\]", re.MULTILINE)


def _artifact(rel: str, payload: str) -> str:
    """渲染一个工件围栏块。"""
    return f"```artifact:{rel}\n{payload}\n```"


class MockLLM:
    """确定性 mock: 按 prompt 的 [STAGE n] 与 [ITER k] 标记返回罐装响应。

    响应始终包含 state/probe.json 探针工件; stage 0-9 附带状态补丁;
    stage 0-2 附带 critique 工件以打通评分链路。必停点按 HIL-lite 协议走:
    在 stage 0/2 正文发 `checkpoint_request: <key>` 指令, 当 prompt 中已出现
    该 key 的 [CP_ANSWERED <key>] 标记 (用户已 answer) 则不再申请。
    构造参数用于制造反例: refine_until/block_stages/bad_critique_stages 同前;
    checkpoint_patch_stages 产出被禁的 state/checkpoints_patch.json 工件
    (LLM 试图自证必停点 → runtime blocked); bad_checkpoint_request_stages
    发非法 key 的 checkpoint_request (→ blocked)。
    """

    def __init__(self, refine_until: dict[int, int] | None = None,
                 block_stages: Iterable[int] = (),
                 bad_critique_stages: Iterable[int] = (),
                 checkpoint_patch_stages: Iterable[int] = (),
                 bad_checkpoint_request_stages: Iterable[int] = ()) -> None:
        self.refine_until = refine_until or {}
        self.block_stages = set(block_stages)
        self.bad_critique = set(bad_critique_stages)
        self.checkpoint_patch_stages = set(checkpoint_patch_stages)
        self.bad_checkpoint_request_stages = set(bad_checkpoint_request_stages)
        self.calls: list[tuple[str, int | None, int]] = []
        self.last_prompt: str | None = None

    def complete(self, role: str, prompt: str) -> LLMResponse:
        """返回罐装响应; stage/iteration 从 prompt 标记解析。"""
        stage_m = _STAGE_RE.search(prompt)
        iter_m = _ITER_RE.search(prompt)
        stage = int(stage_m.group(1)) if stage_m else None
        iteration = int(iter_m.group(1)) if iter_m else 0
        self.calls.append((role, stage, iteration))
        self.last_prompt = prompt
        return LLMResponse(text=self._render(role, stage, iteration), role=role,
                           model="mock", usage_tokens=len(prompt) // 4 + 256)

    def _render(self, role: str, stage: int | None, iteration: int) -> str:
        n = stage if stage is not None else -1
        parts = [
            f"(mock/{role}) stage {n} iter {iteration} 分析: 占位结论, 验证 prompt 组装与路由。",
            _artifact("state/probe.json",
                      json.dumps({"stage": n, "iter": iteration, "role": role, "ok": True},
                                 ensure_ascii=False, indent=2)),
        ]
        if n in _STAGE_PATCHES:
            parts.append(_artifact(f"state/stage_{n}_patch.json",
                                   json.dumps(_STAGE_PATCHES[n], ensure_ascii=False, indent=2)))
        if n in self.checkpoint_patch_stages:  # 反例: LLM 试图自写必停点登记
            parts.append(_artifact("state/checkpoints_patch.json", json.dumps(
                {"kickoff_5q": {"status": "answered", "answer": "mock 伪造"}},
                ensure_ascii=False, indent=2)))
        if n in self.bad_checkpoint_request_stages:  # 反例: 非法 key 申请
            parts.append("checkpoint_request: not_a_checkpoint")
        elif n in _CHECKPOINT_REQUESTS:
            key = _CHECKPOINT_REQUESTS[n]
            answered_keys = set(_CP_ANSWERED_RE.findall(self.last_prompt or ""))
            if key not in answered_keys:
                parts.append(f"checkpoint_request: {key}")
        if n in _MOCK_DIMS:
            parts.append(_artifact(f"state/critique_stage{n}_v{iteration}.json",
                                   json.dumps(self._critique(n, iteration),
                                              ensure_ascii=False, indent=2)))
        return "\n\n".join(parts)

    def _critique(self, stage: int, iteration: int) -> dict:
        """构造 critique; 按构造参数决定 pass/refine/block/非法 四种形态。"""
        if stage in self.bad_critique:
            dims: dict = {"bogus_dim": {"score": 8, "evidence": "非法维度键"}}  # schema 必败
            issues: list = []
            verdict = "pass"  # verdict 无所谓, 校验阶段即 exit 1
        elif stage in self.block_stages:
            dims = {d: {"score": 3, "evidence": "mock 高危证据"} for d in _MOCK_DIMS[stage]}
            issues = [{"severity": "high", "issue": "mock 高危问题, 需用户介入"}]
            verdict = "block"
        elif iteration < self.refine_until.get(stage, 0):
            dims = {d: {"score": 6, "evidence": "mock 待精修证据"} for d in _MOCK_DIMS[stage]}
            issues = [{"severity": "low", "issue": "mock 待精修"}]
            verdict = "refine"
        else:
            dims = {d: {"score": 8, "evidence": f"mock stage {stage} 证据"}
                    for d in _MOCK_DIMS[stage]}
            issues = []
            verdict = "pass"
        scores = [v["score"] for v in dims.values()]
        return {"stage_id": stage, "iteration": iteration, "scores": dims,
                "min_score": min(scores), "mean_score": sum(scores) / len(scores),
                "issues": issues, "verdict": verdict}
