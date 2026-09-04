"""skill 工具注册表: scripts/ 子进程包装 (300s 超时、结构化返回、不 import 脚本)。"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

TOOL_TIMEOUT_S = 300.0
_STDOUT_TAIL = 2000  # 结构化返回只保留 stdout/stderr 尾部


@dataclass
class ToolResult:
    """一次工具子进程调用的结构化结果。"""

    name: str
    args: list[str]
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        """退出码 0 且未超时视为成功。"""
        return self.exit_code == 0 and not self.timed_out

    def to_dict(self) -> dict[str, Any]:
        """转为可 JSON 序列化的 dict。"""
        return {"name": self.name, "args": self.args, "exit_code": self.exit_code,
                "ok": self.ok, "timed_out": self.timed_out,
                "stdout_tail": self.stdout[-_STDOUT_TAIL:],
                "stderr_tail": self.stderr[-_STDOUT_TAIL:]}


@dataclass
class ToolSpec:
    """一个 skill 脚本工具的声明: 参数 schema + 命令行构造器 + 质量门属性。

    blocking=True 的工具执行失败 (ok=False) 时, 所在 stage 不得静默推进。
    """

    name: str
    script: str
    description: str
    params: dict[str, dict[str, Any]]
    build_args: Callable[[dict[str, Any]], list[str]]
    blocking: bool = False


def _val(params: dict[str, Any], key: str) -> Any:
    """取非空参数值 (None/空串视为未提供)。"""
    value = params.get(key)
    return value if value not in (None, "") else None


def _retrieve_args(p: dict[str, Any]) -> list[str]:
    args: list[str] = []
    if _val(p, "query"):
        args += ["--query", str(p["query"])]
    if _val(p, "problem_file"):
        args += ["--problem-file", str(p["problem_file"])]
    for key, flag in (("competition", "--competition"), ("level", "--level"),
                      ("top_k", "--top-k")):
        if _val(p, key):
            args += [flag, str(p[key])]
    args += ["--format", str(p.get("format") or "json")]
    return args


def _score_args(p: dict[str, Any]) -> list[str]:
    return ["--stage", str(p["stage"]), "--critique", str(p["critique"]),
            "--max-iter", str(p.get("max_iter") or 3)]


def _figqa_args(p: dict[str, Any]) -> list[str]:
    args: list[str] = []
    args += ["--strict"] if p.get("strict") else []
    args += ["--allow-box-labels"] if p.get("allow_box_labels") else []
    args += ["--self-test"] if p.get("self_test") else []
    if _val(p, "target"):
        args.append(str(p["target"]))
    return args


def _audit_args(p: dict[str, Any]) -> list[str]:
    # workspace 由子进程 cwd 承载 (脚本只认 cwd, 见 workspace_protocol.md)
    args = ["--json"]
    if _val(p, "paper"):
        args += ["--paper", str(p["paper"])]
    return args


def _freeze_args(p: dict[str, Any]) -> list[str]:
    return [str(p.get("action") or "list")] + [str(a) for a in (p.get("args") or [])]


TOOLS: dict[str, ToolSpec] = {spec.name: spec for spec in (
    ToolSpec("retrieve_cases", "retrieve_cases.py", "相似案例检索 (题目级/子问级, 三赛联合索引)", {
        "query": {"type": "str", "required": False, "desc": "检索关键词, 与 problem_file 二选一"},
        "problem_file": {"type": "path", "required": False, "desc": "题面文件路径"},
        "competition": {"type": "str", "required": False, "desc": "cumcm|huaweibei|huashubei|all"},
        "level": {"type": "str", "required": False, "desc": "case|question|both"},
        "top_k": {"type": "int", "required": False, "desc": "返回条数, 默认 5"}}, _retrieve_args),
    ToolSpec("score_artifact", "score_artifact.py", "阶段工件 L1 评分与 verdict (critique 契约)", {
        "stage": {"type": "int", "required": True, "desc": "阶段编号 0-9"},
        "critique": {"type": "path", "required": True, "desc": "critique JSON 路径"},
        "max_iter": {"type": "int", "required": False, "desc": "精修上限, 默认 3"}},
        _score_args, blocking=True),
    ToolSpec("figqa", "figqa.py", "图表渲染碰撞检测 (六类像素级排版碰撞)", {
        "target": {"type": "path", "required": False, "desc": "figure.py 或其目录"},
        "strict": {"type": "bool", "required": False, "desc": "检出碰撞时退出码 1"},
        "allow_box_labels": {"type": "bool", "required": False, "desc": "豁免盒内标签"},
        "self_test": {"type": "bool", "required": False, "desc": "内置合成图自测"}}, _figqa_args),
    ToolSpec("consistency_audit", "consistency_audit.py", "论文一致性审计 (未冻结数字/摘要-结论/图表引用)", {
        "paper": {"type": "path", "required": False, "desc": "指定单个正文文件, 默认扫描 paper_workspace/"}},
        _audit_args, blocking=True),
    ToolSpec("freeze_numbers", "freeze_numbers.py", "数字冻结协议 (关键数字与数据源哈希绑定)", {
        "action": {"type": "str", "required": False, "desc": "freeze|check|unfreeze|list, 默认 list"},
        "args": {"type": "list", "required": False, "desc": "子命令附加参数"}},
        _freeze_args, blocking=True),
)}


def run_tool(name: str, workspace: Path, skill_root: Path, **params: Any) -> ToolResult:
    """以 workspace 为 cwd 子进程执行 skill 脚本, 返回结构化结果。

    退出码语义由各脚本自带 (0=通过, 1=检出问题/参数错误), 由 ok 字段承载。
    """
    if name not in TOOLS:
        raise KeyError(f"未注册工具: {name!r}; 可用: {sorted(TOOLS)}")
    spec = TOOLS[name]
    args = spec.build_args(params)
    cmd = [sys.executable, str(Path(skill_root) / "scripts" / spec.script), *args]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    try:
        proc = subprocess.run(cmd, cwd=str(workspace), capture_output=True,
                              timeout=TOOL_TIMEOUT_S, env=env)
    except subprocess.TimeoutExpired:
        return ToolResult(name, args, exit_code=-1, stdout="",
                          stderr=f"timeout after {TOOL_TIMEOUT_S:.0f}s", timed_out=True)
    decode = lambda b: (b or b"").decode("utf-8", errors="replace")  # noqa: E731
    return ToolResult(name, args, exit_code=proc.returncode,
                      stdout=decode(proc.stdout), stderr=decode(proc.stderr))
