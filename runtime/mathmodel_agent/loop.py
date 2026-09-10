"""StageDriver: 阶段循环 = 组装 prompt → LLM → 解析工件 → 工具质检 → 质量门 → check_gate 门禁 → 推进。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

from . import gate
from .gate import GateDecision
from .prompts import STAGE_LABELS, STAGE_ROLES, build_prompt
from .protocol import ArtifactPathError, parse_artifacts, write_artifact
from .state import DecisionLog, StateSaveError, checkpoint_allowed, validate_qi_count

MAX_STAGE_ITERS = 3  # stage 内 refine 迭代上限 (与 score_artifact --max-iter 默认一致)

# LLM 申请必停点的唯一合法方式: 正文一行 `checkpoint_request: <key>`
# (凡以该前缀开头的行必须整体合法, 解析见 _parse_checkpoint_request)
CHECKPOINT_REQUEST_PREFIX = "checkpoint_request:"
# LLM 绝不可产出该工件 (自证必停点 = protocol_error)
CHECKPOINTS_PATCH_REL = "state/checkpoints_patch.json"


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
        """顺序执行 [from_stage, to_stage]; 返回 completed/blocked/paused/save_failed。

        恢复语义: state 有未应答的 pending_checkpoint → 直接 paused (不调 LLM);
        pending 已被 CLI answer 登记 → 清除 pending 后从 current_stage 继续。
        """
        pending = self.state.data.get("pending_checkpoint")
        if pending is not None:
            if self.state.checkpoint_is_answered(pending):
                self.state.data.pop("pending_checkpoint", None)
                self.state.append_event("checkpoint_resumed", key=pending)
                self._save()
            else:
                self.out(f"[pause] 必停点 {pending} 待人工应答, "
                         f"运行 answer 命令登记后再重跑 run")
                return "paused"
        for stage in range(from_stage, to_stage + 1):
            outcome = self.run_stage(stage, dry_run=dry_run)
            if outcome in ("blocked", "paused", "save_failed", "completed"):
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
            if CHECKPOINTS_PATCH_REL in response.text:
                # LLM 试图自证必停点 (生成 checkpoints_patch 工件) → 协议违规, 立即停机
                self.state.append_event(
                    "protocol_error",
                    detail=f"LLM 产出 {CHECKPOINTS_PATCH_REL} 工件: 必停点只能经 "
                           f"checkpoint_request 指令 + CLI answer 由人工登记")
                return self._block(stage, GateDecision(
                    gate.BLOCKED,
                    reason=f"LLM 试图自写 {CHECKPOINTS_PATCH_REL} 自证必停点 (protocol_error); "
                           f"必停点只能由人工经 answer 命令登记"))
            # F3: 先全文扫描 checkpoint_request, 再决定是否落盘工件——
            # 合法未答的 request 一律不写任何工件 (paused 等人工应答)
            request, request_error, request_ignored = self._parse_checkpoint_request(
                stage, response.text)
            if request_error is not None:
                return self._block(stage, GateDecision(gate.BLOCKED, reason=request_error))
            if request is not None:
                self.state.data["pending_checkpoint"] = request
                self.state.append_event("checkpoint_requested", stage=stage, key=request)
                if not self._save():
                    return "save_failed"
                self.out(f"[pause] 必停点 {request} 待人工应答, "
                         f"运行 answer 命令登记后再重跑 run")
                return "paused"
            if request_ignored:
                # 已答 key 的重复申请: 忽略, 正常写工件继续推进 (防死循环)
                key = request_ignored
                self.state.append_event("checkpoint_request_ignored", stage=stage, key=key,
                                        detail="该必停点已 answered, 重复申请已忽略")
                self.out(f"[ignore] 必停点 {key} 已 answered, 重复 checkpoint_request 已忽略")
            written = self._write_artifacts(response.text)
            self.out(f"llm({response.model}) -> {len(response.text)} chars, "
                     f"工件 {len(written)} 个: {', '.join(written) or '(无)'}")
            if not self._apply_patch(stage, written):
                return self._block(stage, GateDecision(
                    gate.BLOCKED, reason=f"state/stage_{stage}_patch.json 畸形 (protocol_error), "
                                         f"state 未被污染; 修复后重跑"))
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

    def _parse_checkpoint_request(self, stage: int, text: str) -> tuple[str | None, str | None, str | None]:
        """解析 `checkpoint_request: <key>` 指令 (LLM 申请必停点的唯一合法方式)。

        全文 finditer 收集全部申请后再判定, 任一路径下工件是否落盘由调用方按返回值决定:
        - (key, None, None) = 恰好 1 个合法且未答的申请 (同 key 重复出现按 1 个算),
          调用方不写工件, 登记 pending 后 paused;
        - (None, None, key) = 申请指向的 key 已 answered → 视为无申请 (忽略, 防死循环);
        - (None, None, None) = 无申请;
        - (None, reason, None) = 非法申请 (畸形行 / key 不在 allowlist / ≥2 个不同 key)
          → protocol_error, 调用方据此 blocked, 不写工件。
        """
        keys: list[str] = []
        # F3: 先按行收集所有以 checkpoint_request: 开头的候选行 (strip 后前缀匹配),
        # 每个候选行必须整体合法 (冒号后恰好一个非空 token, 无尾随内容),
        # 否则视为 protocol_error——不是"正则不匹配就当不存在"
        for raw in text.splitlines():
            line = raw.strip()
            if not line.startswith(CHECKPOINT_REQUEST_PREFIX):
                continue
            tokens = line[len(CHECKPOINT_REQUEST_PREFIX):].split()
            if len(tokens) != 1:
                return None, (f"checkpoint_request 指令畸形: {line!r} "
                              f"(合法形态为一行 'checkpoint_request: <key>', 冒号后恰好一个 "
                              f"非空 key, 无尾随内容; 空 key / 多余 token 均算畸形)"), None
            keys.append(tokens[0])
        if not keys:
            return None, None, None
        invalid = [k for k in keys if not checkpoint_allowed(stage, k)]
        if invalid:
            return None, (f"checkpoint_request 含非法 key: {', '.join(sorted(set(invalid)))} "
                          f"(不属于 stage {stage} 的必停点 allowlist; 合法: "
                          f"stage 0→kickoff_5q; 2→analysis_confirm; 3→card_decision; "
                          f"5→figure_menu.Q<n>/qi_verdict.Q<n>/per_qi_selection.Q<n>; "
                          f"其余 stage 无必停点)"), None
        unique = sorted(set(keys))
        if len(unique) > 1:
            return None, (f"一次响应出现 {len(unique)} 个不同 key 的 checkpoint_request "
                          f"({', '.join(unique)}), 只允许 1 个"), None
        key = unique[0]
        if self.state.checkpoint_is_answered(key):
            return None, None, key
        return key, None, None

    def _apply_patch(self, stage: int, written: list[str]) -> bool:
        """若产出了 state/stage_<n>_patch.json 则浅合并进 stages[n]。

        checkpoints 一律不合并 (必停点只能由 CLI answer 的 trusted 路径写入);
        patch JSON 损坏 / 顶层非 dict → 协议错误, 返回 False 由调用方停机, 不污染 state。
        """
        patch_rel = f"state/stage_{stage}_patch.json"
        if patch_rel not in written:
            return True
        try:
            patch = json.loads((self.workspace / patch_rel).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            self.state.append_event("protocol_error",
                                    detail=f"{patch_rel} 不是合法 JSON: {exc}")
            return False
        if not isinstance(patch, dict):
            self.state.append_event("protocol_error",
                                    detail=f"{patch_rel} 顶层必须是 JSON 对象, "
                                           f"实际: {type(patch).__name__}")
            return False
        actual = None
        if stage == 2 and "actual_qi_count" in patch:
            # F5: 校验先于 merge — 非法 actual_qi_count 不得污染 stages["2"]
            actual = patch.get("actual_qi_count")
            try:
                validate_qi_count(actual)
            except ValueError as exc:
                self.state.append_event(
                    "protocol_error",
                    detail=f"stage 2 patch 的 actual_qi_count 非法: {exc}")
                return False
        self.state.merge_stage_patch(stage, patch)
        if actual is not None:
            # F5: stage 2 分解确认后原子迁移 stages["5"].qi_count / qi_weights
            # (已过 validate_qi_count 预检, 此处不再抛 ValueError)
            self.state.confirm_qi_count(actual)
        return True

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

    def _run_check_gate(self, stage: int) -> list[str] | None:
        """v2.3.0 门禁: 推进前强制子进程跑 skill 的 scripts/check_gate.py --gate <stage>。

        Returns: None = 放行 (exit 0); list[str] = 拦截缺失项 (中文, 来自 --json 输出)。
        """
        script = Path(self.config.skill_root) / "scripts" / "check_gate.py"
        try:
            proc = subprocess.run(
                [sys.executable, str(script), "--gate", str(stage), "--json"],
                cwd=self.workspace, capture_output=True, text=True,
                encoding="utf-8", timeout=120)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return [f"check_gate 子进程执行失败: {exc}"]
        if proc.returncode == 0:
            return None
        try:
            return json.loads(proc.stdout).get("missing") or [
                f"check_gate exit {proc.returncode}"]
        except json.JSONDecodeError:
            return [f"check_gate exit {proc.returncode}: "
                    f"{(proc.stdout + proc.stderr).strip()[:500]}"]

    def _advance(self, stage: int, decision: GateDecision) -> str:
        """推进 current_stage 并落盘; 推进前强制过 check_gate 门禁, FAIL 则 paused 不推进。

        Stage 9 是终点: 无 gate 9-10 门禁, 完成即 completed, current_stage 保持 9 不推到 10。
        """
        if stage >= 9:
            # Stage 9 终态加固: 无论从哪个 stage force 进入, 终态 current_stage==9;
            # 落盘失败 → save_failed; 终态字段缺失 → paused 列出缺失 (不判 completed)
            self.state.advance_stage(9)
            stages = self.state.data.get("stages")
            stage9 = stages.get("9") if isinstance(stages, dict) else None
            stage9 = stage9 if isinstance(stage9, dict) else {}
            missing = []
            if stage9.get("skill_issues_consumed") is not True:
                missing.append("stages['9'].skill_issues_consumed != true "
                               "(skill_issues 台账未消费)")
            if stage9.get("submission_ready") is not True:
                missing.append("stages['9'].submission_ready != true (终稿未确认可提交)")
            if missing:
                self.state.append_event("stage9_terminal_missing", missing=missing)
                if not self._save():
                    return "save_failed"
                self.out(f"[gate] stage 9 终态校验缺失, 不判完成: {'; '.join(missing)}")
                return "paused"
            if not self._save():
                return "save_failed"
            self.out(f"[gate] {decision.action} ({decision.reason}); stage 9 终态: "
                     f"current_stage 保持 {self.state.data.get('current_stage')}, 流程完成")
            return "completed"
        gate_missing = self._run_check_gate(stage)
        if gate_missing is not None:
            self.state.append_event("gate_failed", stage=stage, missing=gate_missing)
            self.state.data.setdefault("stages", {}).setdefault(str(stage), {})[
                "paused_gate"] = gate_missing
            self._save()
            self.out(f"[gate] check_gate FAIL: stage {stage} 不推进 (paused), 缺失项: "
                     f"{'; '.join(gate_missing)}")
            return "paused"
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
