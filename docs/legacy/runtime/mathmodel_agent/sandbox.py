"""代码执行沙箱: subprocess 跑 python 片段, 尽力约束 (非安全边界, 见 README)。

约束为正则黑名单 + cwd 隔离的"尽力而为", 明确可被绕过 (写文件再外部执行、
编码混淆、本表未覆盖的动态构造如 getattr 拼接之外的手法等);
真正的进程级隔离 (seccomp/Job Object/容器) 不在原型范围内。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# (正则, 违规说明): 命中即拒绝执行
DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"os\.(?:system|popen|exec\w*|spawn\w*)\s*\(", "shell/进程调用 (os.system 等)"),
    (r"from\s+os\s+import\s+[^#\n]*\b(?:system|popen|exec\w*|spawn\w*)\b", "from os import system/popen"),
    (r"\bsubprocess\b|from\s+subprocess\s+import\b", "subprocess 使用/导入 (含递归逃逸)"),
    (r"__import__\s*\(\s*['\"](?:subprocess|socket|ctypes|shutil|os)['\"]", "__import__ 动态导入危险模块"),
    (r"\bimport\s+(?:subprocess|socket|ctypes)\b|from\s+(?:socket|ctypes)\s+import\b", "导入危险模块"),
    (r"getattr\s*\(\s*(?:os|shutil|builtins|globals\s*\(\s*\)|__import__)\b", "getattr 动态拼接调用危险属性"),
    (r"shutil\.rmtree", "shutil.rmtree 删除目录树"),
    (r"\bsocket\b", "socket 网络访问"),
    (r"\b(?:urllib|requests|http\.client|aiohttp)\b", "网络库导入/使用"),
    (r"open\s*\(\s*['\"][A-Za-z]:[\\/]", "绝对路径文件写入 (Windows 盘符)"),
    (r"open\s*\(\s*['\"]/", "绝对路径文件写入 (POSIX)"),
    (r"\beval\s*\(\s*input", "eval(input()) 任意代码执行"),
]
_COMPILED = [(re.compile(pattern), desc) for pattern, desc in DANGEROUS_PATTERNS]


def check_code(code: str) -> list[str]:
    """返回命中的危险模式说明列表; 空列表表示未检出。"""
    return [desc for pattern, desc in _COMPILED if pattern.search(code)]


@dataclass
class ExecResult:
    """一次沙箱执行的结构化结果。"""

    ok: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float = 0.0
    changes: dict[str, list[str]] = field(default_factory=dict)
    rejected: bool = False
    violations: list[str] = field(default_factory=list)

    @property
    def produced_files(self) -> list[str]:
        """新增+变更的文件 (兼容旧口径)。"""
        return self.changes.get("added", []) + self.changes.get("changed", [])

    def to_dict(self) -> dict:
        """转为可 JSON 序列化的 dict。"""
        return {"ok": self.ok, "exit_code": self.exit_code, "rejected": self.rejected,
                "violations": self.violations, "duration_s": round(self.duration_s, 3),
                "stdout_tail": self.stdout[-2000:], "stderr_tail": self.stderr[-2000:],
                "changes": self.changes}


def _snapshot(workspace: Path) -> dict[str, tuple[int, int]]:
    """workspace 文件快照: 相对路径 -> (mtime_ns, size), 跳过 _runtime 缓存目录。"""
    return {p.relative_to(workspace).as_posix(): (p.stat().st_mtime_ns, p.stat().st_size)
            for p in workspace.rglob("*")
            if p.is_file() and "_runtime" not in p.relative_to(workspace).parts}


def _diff(before: dict[str, tuple[int, int]], after: dict[str, tuple[int, int]]) -> dict[str, list[str]]:
    """按 (mtime, size) 差分出新增/变更/删除三类文件。"""
    return {"added": sorted(after.keys() - before.keys()),
            "changed": sorted(k for k in before.keys() & after.keys() if before[k] != after[k]),
            "removed": sorted(before.keys() - after.keys())}


def run_python(code: str, workspace: Path, timeout_s: float = 60.0) -> ExecResult:
    """在 workspace 内执行 python 片段: 先过黑名单, 再子进程运行并差分产物。

    片段写入 workspace/_runtime/exec_<ts>.py 后以 cwd=workspace 执行,
    保证工作目录内的相对路径写入都落在 workspace。
    """
    violations = check_code(code)
    if violations:
        return ExecResult(ok=False, exit_code=-1, stdout="", stderr="",
                          rejected=True, violations=violations)
    workspace = Path(workspace)
    runtime_dir = workspace / "_runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    script = runtime_dir / f"exec_{time.strftime('%H%M%S')}_{os.getpid()}.py"
    script.write_text(code, encoding="utf-8", newline="\n")
    before = _snapshot(workspace)
    started = time.monotonic()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    try:
        proc = subprocess.run([sys.executable, str(script)], cwd=str(workspace),
                              capture_output=True, timeout=timeout_s, env=env)
        result = ExecResult(ok=proc.returncode == 0, exit_code=proc.returncode,
                            stdout=proc.stdout.decode("utf-8", errors="replace"),
                            stderr=proc.stderr.decode("utf-8", errors="replace"))
    except subprocess.TimeoutExpired:
        result = ExecResult(ok=False, exit_code=-1, stdout="", stderr=f"timeout after {timeout_s}s")
    result.duration_s = time.monotonic() - started
    after = _snapshot(workspace)
    result.changes = _diff(before, after)
    return result
