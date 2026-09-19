"""LLM 输出工件块协议: ```artifact:<相对路径> 围栏解析与安全落盘。

解析为逐行扫描 (非正则整体匹配): 工件头允许含空格的路径;
内容中的成对嵌套 ``` 围栏原样保留; 未闭合/畸形块记入 errors 不静默丢弃。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

FENCE_OPEN = "```artifact:"
FENCE_CLOSE = "```"


@dataclass
class ParsedArtifacts:
    """一次解析的结果: 合法工件 + 协议错误列表 (供上层记事件)。"""

    artifacts: list[tuple[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ArtifactPathError(ValueError):
    """工件相对路径非法 (绝对路径 / 目录逃逸 / 空路径)。"""


def parse_artifacts(text: str) -> ParsedArtifacts:
    """解析全部工件围栏块; 畸形/未闭合块写入 errors 而不是静默跳过。"""
    result = ParsedArtifacts()
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped.startswith(FENCE_OPEN):
            if "```artifact" in stripped and not stripped.startswith(FENCE_OPEN):
                result.errors.append(f"疑似工件块但无法识别: {stripped[:80]!r}")
            i += 1
            continue
        header = stripped[len(FENCE_OPEN):].strip()
        if not header or "`" in header:
            result.errors.append(f"工件头非法 (空路径或含反引号): {stripped[:80]!r}")
            i += 1
            continue
        body: list[str] = []
        depth = 0  # 内容中未配对的嵌套围栏层数
        j = i + 1
        closed = False
        while j < len(lines):
            cur = lines[j].strip()
            if cur.startswith("```"):
                # 嵌套围栏: ```lang 开一层, 裸 ``` 闭一层 (成对的原样保留在内容里);
                # depth==0 时的裸 ``` 才是工件块自身的闭合
                if cur == FENCE_CLOSE:
                    if depth == 0:
                        closed = True
                        break
                    depth -= 1
                else:
                    depth += 1
            body.append(lines[j])
            j += 1
        if not closed:
            result.errors.append(f"工件块未闭合: {header!r}")
            i = j + 1
            continue
        result.artifacts.append((header, "\n".join(body)))
        i = j + 1
    return result


def safe_target(workspace: Path, rel: str) -> Path:
    """把工件相对路径限定在 workspace 内; 绝对路径或含 .. 逃逸即拒绝。"""
    if not rel or rel.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", rel):
        raise ArtifactPathError(f"工件路径必须是 workspace 相对路径: {rel!r}")
    target = (Path(workspace) / rel).resolve()
    root = Path(workspace).resolve()
    if not os.path.normcase(str(target)).startswith(os.path.normcase(str(root)) + os.sep):
        raise ArtifactPathError(f"工件路径逃逸出 workspace: {rel!r}")
    return target


def write_artifact(workspace: Path, rel: str, content: str) -> Path:
    """把工件内容写入 workspace 内目标文件 (utf-8, 自动创建父目录)。"""
    target = safe_target(workspace, rel)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")
    return target
