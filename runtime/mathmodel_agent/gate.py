"""质量门: 解析 score_artifact 结构化输出, 决定 stage 推进/迭代/携带/停机。

对齐 references/feedback_layer1_critic.md 收敛准则:
pass/pass_early/pass_with_review 才推进; refine 在 stage 内迭代 (受限 max_iter);
block 停机不推进; 迭代耗尽显式 carryover; blocking 工具失败不推进质量门。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import tools
from .state import DecisionLog

ADVANCE = "advance"      # 推进下一 stage
ITERATE = "iterate"      # stage 内再迭代 (refine)
CARRYOVER = "carryover"  # 迭代耗尽, 显式携带债务推进
BLOCKED = "blocked"      # 停机, 不推进, 等用户介入


@dataclass
class GateDecision:
    """一次质量门判定的结果。"""

    action: str
    verdict: str | None = None
    reason: str = ""


def parse_action_json(stdout: str) -> dict[str, Any] | None:
    """从工具 stdout 提取最后一个含 "action" 键的 JSON 对象 (score_artifact 的决策输出)。"""
    decoder = json.JSONDecoder()
    found: dict[str, Any] | None = None
    idx = 0
    while idx < len(stdout):
        pos = stdout.find("{", idx)
        if pos < 0:
            break
        try:
            obj, end = decoder.raw_decode(stdout, pos)
        except json.JSONDecodeError:
            idx = pos + 1
            continue
        if isinstance(obj, dict) and "action" in obj:
            found = obj
        idx = max(end, pos + 1)
    return found


def decide(reports: list[dict[str, Any]], remaining_iters: int) -> GateDecision:
    """依据工具报告判定 stage 去向; 报告顺序即执行顺序。"""
    for report in reports:  # 1) blocking 工具失败优先判停/迭代
        spec = tools.TOOLS.get(report["name"])
        if spec is not None and spec.blocking and not report["ok"]:
            if report["name"] == "score_artifact" and remaining_iters > 0:
                return GateDecision(ITERATE, reason="score_artifact 执行失败, 重新生成 critique")
            return GateDecision(BLOCKED,
                                reason=f"blocking 工具 {report['name']} 失败 (exit={report['exit_code']})")
    score_reports = [r for r in reports if r["name"] == "score_artifact"]
    if not score_reports:  # 本 stage 无 critique 工件 -> 无评分门, 直接推进
        return GateDecision(ADVANCE, reason="无评分门")
    action_json = parse_action_json(score_reports[-1]["stdout_tail"])
    if action_json is None:
        return GateDecision(BLOCKED if remaining_iters <= 0 else ITERATE,
                            reason="无法从 score_artifact stdout 解析决策 JSON")
    action = action_json.get("action")
    verdict = action_json.get("verdict")
    if action == "next_stage":
        return GateDecision(ADVANCE, verdict=verdict, reason=f"verdict={verdict}")
    if action == "section_patch":
        return GateDecision(ITERATE, verdict=verdict,
                            reason=f"verdict={verdict}, stage 内迭代" if remaining_iters > 0
                            else "迭代预算已尽")
    if action == "carryover":
        return GateDecision(CARRYOVER, verdict=verdict, reason="max_iter 耗尽, 显式 carryover")
    if action == "halt":
        return GateDecision(BLOCKED, verdict=verdict,
                            reason=f"verdict={verdict}: {action_json.get('reason', '高危问题')}")
    return GateDecision(BLOCKED, reason=f"未知 action: {action!r}")


def run_stage_tools(state: DecisionLog, workspace: Path, skill_root: Path,
                    stage: int, written: list[str],
                    print_fn: "Callable[[str], None] | None" = None) -> list[dict[str, Any]]:
    """执行 stage 工具计划; 返回结构化报告列表 (评分门 + 阶段固定工具)。"""
    reports: list[dict[str, Any]] = []
    critiques = [p for p in written if p.startswith("state/") and "critique" in p]
    for critique in critiques:
        result = tools.run_tool("score_artifact", workspace, skill_root,
                                stage=stage, critique=str(Path(workspace) / critique))
        reports.append(result.to_dict())
        _emit(result, print_fn)
    for name, params in _tool_plan(state, workspace, stage):
        result = tools.run_tool(name, workspace, skill_root, **params)
        reports.append(result.to_dict())
        _emit(result, print_fn)
    return reports


def _tool_plan(state: DecisionLog, workspace: Path, stage: int) -> list[tuple[str, dict]]:
    """阶段→固定工具策略 (原型级: 选题检索在 stage 1, 终稿审计在 stage 9)。"""
    problem = workspace / "inputs" / "problem.txt"
    if stage == 1 and problem.exists():
        return [("retrieve_cases", {"problem_file": str(problem),
                                    "competition": state.data.get("competition"),
                                    "top_k": 3})]
    if stage == 9:
        return [("consistency_audit", {}), ("freeze_numbers", {"action": "list"})]
    return []


def _emit(result, print_fn) -> None:  # noqa: ANN001
    if print_fn is not None:
        status = "ok" if result.ok else f"FAIL(exit={result.exit_code})"
        print_fn(f"tool {result.name}: {status}")
