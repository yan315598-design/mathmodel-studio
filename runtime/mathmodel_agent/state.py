"""decision_log.json 的读写封装: 模板初始化、原子写盘、阶段推进与事件日志。"""
from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from .config import MODE_TOKEN_BUDGETS

STATE_REL = Path("state") / "decision_log.json"
_EVENT_CAP = 200  # events.log 上限, 超出截断旧事件
_REPLACE_ATTEMPTS = 5  # Windows 下目标文件被占用时 os.replace 的重试次数
_REPLACE_BASE_DELAY = 0.1


class StateSaveError(RuntimeError):
    """状态写盘失败 (重试耗尽); 内存态保持完整, 原文件未破坏, 可稍后重试。"""


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
        """把 state/stage_<n>_patch.json 的内容浅合并进 stages[n]。"""
        target = self.data.setdefault("stages", {}).setdefault(str(stage), {})
        target.update({k: v for k, v in patch.items() if not str(k).startswith("_")})

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
