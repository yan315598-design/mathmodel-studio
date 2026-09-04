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
    2: {"decomposition": ["Q1 数据画像", "Q2 优化模型", "Q3 灵敏度分析"],
        "key_variables": ["x_ij", "c_j"], "key_constraints": ["容量上限"],
        "objective_per_subproblem": {"Q1": "清洗与统计画像", "Q2": "最小化总延迟"}},
}


def _artifact(rel: str, payload: str) -> str:
    """渲染一个工件围栏块。"""
    return f"```artifact:{rel}\n{payload}\n```"


class MockLLM:
    """确定性 mock: 按 prompt 的 [STAGE n] 与 [ITER k] 标记返回罐装响应。

    响应始终包含 state/probe.json 探针工件; stage 0-9 附带状态补丁;
    stage 0-2 附带 critique 工件以打通评分链路。构造参数用于制造反例:
    refine_until={stage: k} 在 iteration<k 时返回低分 refine;
    block_stages 返回高危 issue (verdict=block); bad_critique_stages 返回
    schema 非法的 critique (score_artifact exit 1)。
    """

    def __init__(self, refine_until: dict[int, int] | None = None,
                 block_stages: Iterable[int] = (),
                 bad_critique_stages: Iterable[int] = ()) -> None:
        self.refine_until = refine_until or {}
        self.block_stages = set(block_stages)
        self.bad_critique = set(bad_critique_stages)
        self.calls: list[tuple[str, int | None, int]] = []

    def complete(self, role: str, prompt: str) -> LLMResponse:
        """返回罐装响应; stage/iteration 从 prompt 标记解析。"""
        stage_m = _STAGE_RE.search(prompt)
        iter_m = _ITER_RE.search(prompt)
        stage = int(stage_m.group(1)) if stage_m else None
        iteration = int(iter_m.group(1)) if iter_m else 0
        self.calls.append((role, stage, iteration))
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
