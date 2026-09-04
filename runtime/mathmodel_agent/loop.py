"""StageDriver: 阶段循环 = 组装 prompt → LLM → 解析工件 → 工具质检 → 质量门 → 推进。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from . import gate
from .gate import GateDecision
from .prompts import STAGE_LABELS, STAGE_ROLES, build_prompt
from .protocol import ArtifactPathError, parse_artifacts, write_artifact
from .state import DecisionLog, StateSaveError

MAX_STAGE_ITERS = 3  # stage 内 refine 迭代上限 (与 score_artifact --max-iter 默认一致)


class StageDriver:
    """驱动 stage 序列; 推进与否由质量门 (gate.py) 决定, 不无条件 current_stage + 1。"""

    def __init__(self, config, client, state: DecisionLog, workspace: Path,
                 out: Callable[[str], None] = print) -> None:  # noqa: ANN001
        self.config = config
        self.client = client
        self.state = state
        self.workspace = Path(workspace)
        self.out = out

    # ---- 主循环 ----
    def run(self, from_stage: int, to_stage: int, dry_run: bool = False) -> str:
        """顺序执行 [from_stage, to_stage]; 返回 completed/blocked/save_failed。"""
        for stage in range(from_stage, to_stage + 1):
            outcome = self.run_stage(stage, dry_run=dry_run)
            if outcome in ("blocked", "save_failed"):
                return outcome
        return "completed"

    def run_stage(self, stage: int, dry_run: bool = False) -> str:
        """执行单个 stage; refine 在 stage 内迭代, 质量门决定推进/携带/停机。"""
        role = STAGE_ROLES.get(stage, "extraction")
        for iteration in range(MAX_STAGE_ITERS):
            prompt = build_prompt(self.config.skill_root, self.state, self.workspace,
                                  stage, iteration)
            self.out(f"========== stage {stage} {STAGE_LABELS.get(stage, '?')} iter={iteration} "
                     f"(role={role}, prompt={len(prompt)} chars) ==========")
            if dry_run:
                self.out(f"[dry-run] prompt 摘要: {prompt[:200]!r}")
                return "dry-run"
            response = self.client.complete(role, prompt)
            written = self._write_artifacts(response.text)
            self.out(f"llm({response.model}) -> {len(response.text)} chars, "
                     f"工件 {len(written)} 个: {', '.join(written) or '(无)'}")
            self._apply_patch(stage, written)
            self.state.add_tokens(response.usage_tokens)
            self.state.append_event("stage_done", stage=stage, iteration=iteration,
                                    artifacts=written)
            if not self._save():
                return "save_failed"
            reports = gate.run_stage_tools(self.state, self.workspace,
                                           self.config.skill_root, stage, written,
                                           print_fn=self.out)
            decision = self._reload_and_decide(reports, MAX_STAGE_ITERS - 1 - iteration)
            if decision.action == gate.ADVANCE:
                return self._advance(stage, decision)
            if decision.action == gate.ITERATE:
                self.out(f"[gate] refine (iter {iteration} -> {iteration + 1}): {decision.reason}")
                continue
            if decision.action == gate.CARRYOVER:
                self.state.append_event("carryover", stage=stage, verdict=decision.verdict,
                                        reason=decision.reason)
                return self._advance(stage, decision)
            return self._block(stage, decision)
        self.state.append_event("carryover", stage=stage, reason="stage 内迭代耗尽仍 refine")
        return self._advance(stage, GateDecision(gate.CARRYOVER, reason="迭代耗尽仍 refine"))

    # ---- 子步骤 ----
    def _write_artifacts(self, text: str) -> list[str]:
        """解析并落盘全部工件块; 协议错误与非法路径记事件, 不静默丢弃。"""
        parsed = parse_artifacts(text)
        for error in parsed.errors:
            self.state.append_event("protocol_error", detail=error)
            self.out(f"[warn] 协议错误: {error}")
        written: list[str] = []
        for rel, content in parsed.artifacts:
            try:
                write_artifact(self.workspace, rel, content)
                written.append(rel)
            except ArtifactPathError as exc:
                self.state.append_event("artifact_rejected", path=rel, reason=str(exc))
                self.out(f"[warn] 工件被拒: {exc}")
        return written

    def _apply_patch(self, stage: int, written: list[str]) -> None:
        """若产出了 state/stage_<n>_patch.json 则浅合并进 stages[n]。"""
        patch_rel = f"state/stage_{stage}_patch.json"
        if patch_rel in written:
            patch = json.loads((self.workspace / patch_rel).read_text(encoding="utf-8"))
            self.state.merge_stage_patch(stage, patch)

    def _reload_and_decide(self, reports: list[dict], remaining_iters: int) -> GateDecision:
        """重读磁盘 state (外部脚本可能改写), 再交质量门判定。

        磁盘文件损坏时保留内存态、记 state_reload_failed 事件并落盘修复,
        同时把本轮工具按失败处理 (不静默推进质量门)。
        """
        if self.state.reload():
            for report in reports:
                self.state.append_event("tool_called", name=report["name"],
                                        ok=report["ok"], exit_code=report["exit_code"])
            return gate.decide(reports, remaining_iters)
        self.state.append_event("state_reload_failed", tools=[r["name"] for r in reports])
        self._save()  # 用内存态修复磁盘上的损坏文件
        if remaining_iters > 0 and any(r["name"] == "score_artifact" for r in reports):
            return GateDecision(gate.ITERATE, reason="state 损坏已用内存态修复, 重跑评分门")
        return GateDecision(gate.BLOCKED, reason="state 文件损坏且无迭代预算")

    def _advance(self, stage: int, decision: GateDecision) -> str:
        """推进 current_stage 并落盘; 返回 advanced/carryover/save_failed。"""
        previous = self.state.data.get("current_stage")
        self.state.advance_stage(stage + 1)
        if not self._save():
            return "save_failed"
        budget = self.state.data.get("budget", {})
        self.out(f"[gate] {decision.action} ({decision.reason}); state: current_stage "
                 f"{previous} -> {self.state.data.get('current_stage')} "
                 f"(tokens {budget.get('tokens_used')}/{budget.get('tokens_cap')})")
        return decision.action if decision.action != gate.ADVANCE else "advanced"

    def _block(self, stage: int, decision: GateDecision) -> str:
        """停机: 不推进, blocked 状态写入 state 与事件日志。"""
        self.state.append_event("blocked", stage=stage, verdict=decision.verdict,
                                reason=decision.reason)
        self.state.data.setdefault("stages", {}).setdefault(str(stage), {})["blocked"] = decision.reason
        self._save()
        self.out(f"[halt] stage {stage} blocked: {decision.reason}")
        return "blocked"

    def _save(self) -> bool:
        """save 的安全包装; 失败时输出可恢复错误信息而非崩溃。"""
        try:
            self.state.save()
            return True
        except StateSaveError as exc:
            self.out(f"[FAIL] {exc}")
            return False
