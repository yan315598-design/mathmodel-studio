"""decision_log.json 的读写封装: 模板初始化、原子写盘、阶段推进与事件日志。"""
from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

import re

from .config import MODE_TOKEN_BUDGETS

STATE_REL = Path("state") / "decision_log.json"

# 合法子问键: Q 后跟不含前导零的正整数 (与 scripts/check_gate.py QI_KEY_RE 口径一致)
QI_KEY_RE = re.compile(r"^Q[1-9]\d*$")

# 各 stage 允许的必停点键 (checkpoint_request / CLI answer 共用的 allowlist)。
# -1 = 该 stage 无任何必停点 (出现即 protocol_error)。
CHECKPOINT_ALLOWLIST: dict[int, set[str] | None] = {
    0: {"kickoff_5q"},
    2: {"analysis_confirm"},
    3: {"card_decision"},
    5: None,  # 动态: figure_menu.Q<n> / qi_verdict.Q<n>
}


class CheckpointKeyError(ValueError):
    """必停点键不合法 (不在当前 stage 的 allowlist 内 / 格式错误 / 元键)。"""


def checkpoint_allowed(stage: int, key: str) -> bool:
    """判断 key 是否属于 stage 的必停点 allowlist (runtime 与 CLI answer 共用)。"""
    if not isinstance(key, str) or not key or key.startswith("_"):
        return False
    allowed = CHECKPOINT_ALLOWLIST.get(stage, -1)
    if allowed == -1:
        return False
    if allowed is not None:
        return key in allowed
    # 动态 allowlist (stage 5): figure_menu.Q<n> / qi_verdict.Q<n>
    top, _, qi = key.partition(".")
    return top in ("figure_menu", "qi_verdict") and bool(QI_KEY_RE.match(qi))
_EVENT_CAP = 200  # events.log 上限, 超出截断旧事件
_REPLACE_ATTEMPTS = 5  # Windows 下目标文件被占用时 os.replace 的重试次数
_REPLACE_BASE_DELAY = 0.1


class StateSaveError(RuntimeError):
    """状态写盘失败 (重试耗尽); 内存态保持完整, 原文件未破坏, 可稍后重试。"""


def validate_qi_count(actual_count) -> None:
    """F5: stage 2 actual_qi_count 预检 — 必须正 int (bool 排除), 否则 ValueError。

    独立于 confirm_qi_count 暴露, 供 loop 在 merge patch 之前拦截非法值,
    保证 blocked 路径零 state 污染。
    """
    if isinstance(actual_count, bool) or not isinstance(actual_count, int) \
            or actual_count < 1:
        raise ValueError(f"actual_count 必须是正整数, 实际: {actual_count!r}")


class DecisionLog:
    """流程状态机: 与 skill 的 cwd/state/decision_log.json 完全同构。"""

    def __init__(self, data: dict, path: Path) -> None:
        self.data = data
        self.path = path

    # ---- 加载与初始化 ----
    @classmethod
    def load(cls, workspace: Path) -> "DecisionLog | None":
        """加载已有 state; 不存在返回 None (由调用方决定是否初始化)。"""
        path = Path(workspace) / STATE_REL
        if not path.exists():
            return None
        return cls(json.loads(path.read_text(encoding="utf-8")), path)

    @classmethod
    def init_from_template(cls, workspace: Path, skill_root: Path, *,
                           competition: str, mode: str = "standard",
                           problem: str | None = None) -> "DecisionLog":
        """从 templates/shared/decision_log.json 初始化并落盘。"""
        template = Path(skill_root) / "templates" / "shared" / "decision_log.json"
        data = json.loads(template.read_text(encoding="utf-8"))
        data["competition"] = competition
        data["mode"] = mode
        data["started_at"] = datetime.now().isoformat(timespec="seconds")
        if problem:
            data["problem"] = problem
        data.setdefault("budget", {})
        data["budget"]["tokens_cap"] = MODE_TOKEN_BUDGETS.get(mode, data["budget"].get("tokens_cap", 200_000))
        log = cls(data, Path(workspace) / STATE_REL)
        log.save()
        return log

    # ---- 持久化 ----
    def save(self, sleep: Callable[[float], None] = time.sleep) -> None:
        """原子写盘: 同目录临时文件 + os.replace; 目标被占用时有限重试。

        重试耗尽抛 StateSaveError (原文件保留, 内存态不动, 可恢复)。
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.data, ensure_ascii=False, indent=2)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".decision_log.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
            self._replace_with_retry(tmp, sleep)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def _replace_with_retry(self, tmp: str, sleep: Callable[[float], None]) -> None:
        """os.replace 对 PermissionError 指数退避重试 (Windows 文件句柄占用场景)。"""
        delay = _REPLACE_BASE_DELAY
        for attempt in range(_REPLACE_ATTEMPTS):
            try:
                os.replace(tmp, self.path)
                return
            except PermissionError as exc:
                if attempt == _REPLACE_ATTEMPTS - 1:
                    raise StateSaveError(
                        f"decision_log.json 写盘失败 (重试 {_REPLACE_ATTEMPTS} 次, "
                        f"文件可能被其他进程占用): {exc}; 内存态未破坏, 可重试") from exc
                sleep(delay)
                delay *= 2

    def reload(self) -> bool:
        """从磁盘重读 (score_artifact 等外部脚本会直接改写该文件)。

        磁盘文件损坏/不完整时返回 False 并保留内存态, 不抛出;
        调用方随后 save() 即可用内存态修复磁盘文件。
        """
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            return True
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return False

    # ---- 状态更新 ----
    def advance_stage(self, stage: int) -> None:
        """推进 current_stage (只前进不后退)。"""
        current = int(self.data.get("current_stage") or 0)
        self.data["current_stage"] = max(current, int(stage))

    def add_tokens(self, n: int) -> None:
        """累计 token 用量到 budget.tokens_used。"""
        budget = self.data.setdefault("budget", {})
        budget["tokens_used"] = int(budget.get("tokens_used") or 0) + int(n)

    def merge_stage_patch(self, stage: int, patch: dict) -> None:
        """把 state/stage_<n>_patch.json 的内容浅合并进 stages[n]。

        patch 必须是 dict (畸形输入由调用方拦截, 不在此静默吞掉)。"""
        if not isinstance(patch, dict):
            raise TypeError(f"stage patch 必须是 dict, 实际: {type(patch).__name__}")
        target = self.data.setdefault("stages", {}).setdefault(str(stage), {})
        target.update({k: v for k, v in patch.items() if not str(k).startswith("_")})

    # ---- 必停点 (trusted 路径: 只能由 CLI answer / 用户侧写入) ----
    def checkpoint_is_answered(self, key: str) -> bool:
        """checkpoints 中该键是否已被真实作答 (is_answered 三条件)。"""
        node: object = self.data.get("checkpoints")
        for part in key.split("."):
            if not isinstance(node, dict):
                return False
            node = node.get(part)
        return (isinstance(node, dict) and node.get("status") == "answered"
                and isinstance(node.get("asked_at"), str) and node.get("asked_at").strip()
                and isinstance(node.get("answer"), str) and bool(node.get("answer").strip())
                and node.get("source") == "user_cli")  # runtime 面只认自己的 trusted 写入

    def record_checkpoint(self, key: str, answer: str, note: str | None = None,
                          force: bool = False, count: int | None = None,
                          exception: bool = False, reason: str | None = None) -> None:
        """trusted 写入: 登记"用户已作答"的必停点条目 (仅 CLI answer 调用, LLM 不可达)。

        - key 必须过当前 stage 的 allowlist (错 stage / 元键 / 格式错 → CheckpointKeyError)
        - figure_menu / qi_verdict 按 Qi 键深合并 (连续登记 Q1/Q2/Q3 三键全保留)
        - 单值键或同一 Qi 已有 answered 值时需 force=True 才覆盖
        - answer 必须是非空字符串
        - 根级 checkpoints 损坏 (非 dict) → CheckpointKeyError, 不 traceback
        - count / exception / reason 仅对 figure_menu.Q<n> 键有效 (图表菜单结构化参数):
          count 须为 0-9 的整数; count≤1 时须 exception=True 且 reason 非空 (D.1 例外确认)
        """
        stage = int(self.data.get("current_stage") or 0)
        if not checkpoint_allowed(stage, key):
            raise CheckpointKeyError(
                f"必停点 {key!r} 不属于 stage {stage} 的 allowlist "
                f"(合法: stage 0→kickoff_5q; 2→analysis_confirm; 3→card_decision; "
                f"5→figure_menu.Q<n>/qi_verdict.Q<n>; 其余 stage 无必停点)")
        if not isinstance(answer, str) or not answer.strip():
            raise CheckpointKeyError("answer 必须是非空字符串")
        is_figure_menu = key.startswith("figure_menu.Q")
        if not is_figure_menu and (count is not None or exception or reason is not None):
            raise CheckpointKeyError(
                "--count/--exception/--reason 仅对 figure_menu.Q<n> 键有效 "
                f"(当前键: {key!r})")
        if is_figure_menu and count is None:
            # F2: 与 check_gate _figure_menu_content_problems 同口径, count 必填
            raise CheckpointKeyError(
                f"figure_menu 必停点 {key!r} 缺图表数量: answer 命令须补 "
                f"--count <0-9 的整数> (count≤1 另须 --exception 加非空 --reason)")
        if count is not None:
            if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 9:
                raise CheckpointKeyError(f"count 必须是 0-9 的整数, 实际: {count!r}")
            if count <= 1 and (exception is not True or not isinstance(reason, str)
                               or not reason.strip()):
                raise CheckpointKeyError(
                    f"count={count} 低于每问默认 ≥2 图的硬门, 须走 D.1 例外确认: "
                    "--exception 加非空 --reason (经用户确认的例外理由)")
        checkpoints = self.data.get("checkpoints")
        if not isinstance(checkpoints, dict):
            raise CheckpointKeyError(
                f"decision_log.checkpoints 损坏 (应为 dict, 实际 {type(checkpoints).__name__}), "
                "需先修复 state 再登记必停点")
        node = checkpoints
        parts = key.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
            if not isinstance(node, dict):
                raise CheckpointKeyError(f"checkpoints.{part} 已被非 dict 值占用, 无法登记")
        leaf = parts[-1]
        existing = node.get(leaf)
        if existing is not None and (not isinstance(existing, dict)
                                     or existing.get("status") == "answered") and not force:
            raise CheckpointKeyError(
                f"checkpoints.{key} 已有登记值, 覆盖需 --force")
        entry = {"status": "answered",
                 "asked_at": datetime.now().isoformat(timespec="seconds"),
                 "answer": answer,
                 "source": "user_cli"}
        if note:
            entry["note"] = note
        if count is not None:
            entry["count"] = count
        if exception:
            entry["exception"] = True
        if reason is not None:
            entry["reason"] = reason
        node[leaf] = entry
        if self.data.get("pending_checkpoint") == key:
            del self.data["pending_checkpoint"]
        self.append_event("checkpoint_answered", key=key, source="user_cli")

    def confirm_qi_count(self, actual_count: int) -> None:
        """F5: stage 2 分解确认后的原子迁移 — 写 stages["5"].qi_count、按实际子问数
        重建 qi_weights (默认均匀 [1.0]*n, 对齐 stage_05_subproblem_loop.md)、
        追加 qi_count_confirmed 事件并一次性落盘。

        actual_count 必须是正 int (bool 排除), 否则抛 ValueError 且 state 不变。
        调用方可先用 validate_qi_count() 预检, 保证 merge 前拦截非法值。
        """
        validate_qi_count(actual_count)
        stage5 = self.data.setdefault("stages", {}).setdefault("5", {})
        stage5["qi_count"] = actual_count
        stage5["qi_weights"] = [1.0] * actual_count
        self.append_event("qi_count_confirmed", actual_count=actual_count)
        self.save()

    def append_event(self, kind: str, **fields) -> None:
        """追加时间线事件 (backtrack/tool_called/stage_done/blocked 等)。"""
        log = self.data.setdefault("events", {}).setdefault("log", [])
        log.append({"ts": datetime.now().isoformat(timespec="seconds"),
                    "kind": kind, **fields})
        if len(log) > _EVENT_CAP:
            del log[:-_EVENT_CAP]

    # ---- 摘要 ----
    def summary(self) -> dict:
        """给 prompt 用的紧凑摘要 (不展开完整 stages)。"""
        scores = self.data.get("scores", {})
        return {
            "competition": self.data.get("competition"),
            "mode": self.data.get("mode"),
            "current_stage": self.data.get("current_stage"),
            "started_at": self.data.get("started_at"),
            "budget": self.data.get("budget", {}),
            "problem": self.data.get("problem"),
            "scored_stages": sorted(k for k, v in scores.items() if v),
        }
