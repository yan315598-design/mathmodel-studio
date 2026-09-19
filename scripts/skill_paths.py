#!/usr/bin/env python
"""skill 根路径唯一真源 (D1)。

调用入口可能是 junction / symlink, 指向同一份 skill 安装 (例如
`.zcode/skills/mathmodel-studio` 链到 `.codex/skills/mathmodel-studio`)。
根目录按**调用路径**向上找 `SKILL.md` (判据: 同时有 `SKILL.md` 与 `scripts/` 目录),
不强制 `resolve()` 到真实路径——从哪个入口调用就报哪个入口, 便于人判断当前用的是哪一份;
符号链接解析后的真实路径由 `real_root()` 单独给出, `describe()` 在两者不同时附带真实路径
(V0 级日志)。

用法:
    from skill_paths import skill_root, describe
    SKILL_ROOT = skill_root(__file__)
    print(describe(__file__))
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["skill_root", "describe", "real_root"]


def skill_root(from_file: str | Path) -> Path:
    """按调用路径向上推导 skill 根。

    `from_file` 传 `__file__` 即可 (任意深度); 也接受 skill 内目录路径
    (从该目录本身开始查)。判据: 该目录同时含 `SKILL.md` 与 `scripts/`。
    找不到时抛 ValueError——不静默退回某个祖辈目录 (审查实测: 传 skill 根
    目录本身或 `C:/` 时原先会返回错误目录 / IndexError)。
    """
    here = Path(from_file).absolute()
    start = here if here.is_dir() else here.parent
    for parent in (start, *start.parents):
        if (parent / "SKILL.md").is_file() and (parent / "scripts").is_dir():
            return parent
    raise ValueError(
        f"无法从 {from_file!r} 向上找到 skill 根 (须含 SKILL.md 与 scripts/); "
        f"请传入 skill 内的文件或目录路径"
    )


def real_root(root: Path) -> Path:
    """真实路径 (符号链接解析后)。与 `root` 不同即说明当前是链接安装。"""
    return Path(os.path.realpath(root))


def describe(from_file: str | Path) -> str:
    """返回当前根的 V0 级日志行; 链接安装时附带真实路径。"""
    root = skill_root(from_file)
    real = real_root(root)
    line = f"[skill] root={root}"
    if str(real) != str(root):
        line += f" (symlink -> {real})"
    return line


def main() -> int:  # 直接运行即打印当前根 (自查 / 排查用)
    import sys

    print(describe(sys.argv[1] if len(sys.argv) > 1 else __file__))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
