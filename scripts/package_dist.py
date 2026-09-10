"""
package_dist.py — 开源分发打包: 把 skill 仓库复制到 dist/mathmodel-studio-<version>/

version 从 .codex-plugin/plugin.json 读取 (限安全单段字符集, 防路径遍历)。剔除以下内容:

    运行时/缓存 (可再生产物):
      .git/  .pytest_cache/  **/__pycache__/  %TEMP%/  dist/  evals/results/
      .mimosa/  outputs/  state/ (仅保留 .gitkeep, 保证目录占位)
    许可证受限 (不可再分发, 见 templates/figures/vendor/VENDOR.md §5):
      templates/figures/vendor/scibox-diagram/
      templates/figures/vendor/scibox-figure/
      (sci-box 上游未附正式 LICENSE)

剔除后:
  - 在 dist 根生成 VENDOR_NOTICES.md, 说明被剔除内容及对终端用户的影响;
  - 在分发副本的 SKILL.md 与 references/figure_skill_bridge.md 顶部注入
    "分发版路由说明"横幅 (这两份文档仍把 vendor/scibox-* 列为首选路径,
    分发版中该路径已不存在; 源仓库文件不动)。

用法:
    python scripts/package_dist.py             # --dry-run 默认: 打印清单与大小
    python scripts/package_dist.py --apply     # 真正复制 + 生成 VENDOR_NOTICES.md
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parent.parent

# version 拼入目标路径, 限单段安全字符集: 字母/数字开头, 后接 字母/数字/./_/-
# (拒绝 "../escaped"、"a/b" 等路径形态)
_VERSION_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z._-]*")

# 任意层级按目录名剔除 (缓存/版本库/运行时产物; dist 防自递归复制)
EXCLUDED_DIR_NAMES = {".git", ".pytest_cache", "__pycache__", "%TEMP%", "dist", ".mimosa"}

# 相对仓库根的精确路径剔除; reason 会进 VENDOR_NOTICES.md / dry-run 统计
EXCLUDED_REL_DIRS = {
    "evals/results": "评测结果为本地运行时产物",
    "outputs": "运行时图表输出目录 (vendor 冒烟测试可再生产物)",
    "templates/figures/vendor/scibox-diagram": (
        "sci-box 上游未附正式 LICENSE, 不得再分发 (VENDOR.md §5)"),
    "templates/figures/vendor/scibox-figure": (
        "sci-box 上游未附正式 LICENSE, 不得再分发 (VENDOR.md §5)"),
}

# state/ 整目录剔除但保留 .gitkeep 占位 (写入侧特判)
STATE_KEEP_FILE = Path("state") / ".gitkeep"

# 分发副本中需要注入路由降级横幅的文档 (源仓库不动, 只改 dist 里的副本)
ROUTE_DOC_FILES = ("SKILL.md", "references/figure_skill_bridge.md")

_ROUTE_BANNER = (
    "> **分发版路由说明**: 本分发包已剔除 `templates/figures/vendor/scibox-diagram/` 与 "
    "`templates/figures/vendor/scibox-figure/` (上游无正式 LICENSE, 详见 VENDOR_NOTICES.md)。\n"
    "> 文中所有指向 vendor/scibox-* 的首选路由在分发版一律改走自写模板: 示意图用 "
    "`templates/figures/scripts/render_drawio_pack.py` / `render_diagram_pack.py`, "
    "数据图用 `render_modeling_pack.py`; scibox 独有的高密度示意图模板与非库图型 "
    "(tpe_surface、cv_roc_ci 等) 在分发版不可用, 需要时请自行从上游获取。\n\n"
)


def read_version(repo_root: Path) -> str:
    """从 .codex-plugin/plugin.json 读 version 并校验安全字符集。

    缺失/损坏/非对象/含路径分隔符 → 抛 OSError/ValueError (调用方转 [FAIL])。
    """
    plugin_path = repo_root / ".codex-plugin" / "plugin.json"
    if not plugin_path.exists():
        raise FileNotFoundError(f"plugin.json 不存在: {plugin_path}")
    with open(plugin_path, "r", encoding="utf-8") as f:
        plugin = json.load(f)
    if not isinstance(plugin, dict):
        raise ValueError(f"plugin.json 顶层必须是 JSON 对象: {plugin_path}")
    version = plugin.get("version")
    if not version or not isinstance(version, str):
        raise ValueError(f"plugin.json 缺 version 字符串字段: {plugin_path}")
    if not _VERSION_RE.fullmatch(version):
        raise ValueError(
            f"version 含不安全字符: {version!r} "
            f"(仅允许字母/数字开头, 后接 字母/数字/./_/-, 防路径越界)")
    return version


def exclusion_reason(rel_posix: str, parts: tuple[str, ...]) -> str | None:
    """判断一个相对路径是否被剔除; 返回原因或 None。

    目录名规则命中 → 缓存/版本库类原因; 精确路径命中 → 对应说明;
    state/ 特例 → 只放行 state/.gitkeep。
    """
    if STATE_KEEP_FILE.as_posix() == rel_posix:
        return None
    if parts[0] == "state":
        return "运行时状态目录 (仅保留 .gitkeep)"
    for part in parts:
        if part in EXCLUDED_DIR_NAMES:
            return f"缓存/运行时目录 ({part}/)"
    # 精确路径: 文件本身命中, 或落在被剔除目录内
    for rel_dir, reason in EXCLUDED_REL_DIRS.items():
        if rel_posix == rel_dir or rel_posix.startswith(rel_dir + "/"):
            return reason
    return None


def collect_plan(repo_root: Path) -> dict:
    """遍历仓库, 返回 {included: [(rel, bytes)], excluded: [(rel, reason)]}。

    命中剔除规则的目录整棵子树剪枝、不深入; state/ 例外——记录目录级
    剔除条目后仍继续遍历, 仅放行 .gitkeep (子项不重复计数)。
    """
    included: list[tuple[Path, int]] = []
    excluded: list[tuple[str, str]] = []

    def walk(dir_path: Path, rel_dir: Path):
        try:
            entries = sorted(dir_path.iterdir())
        except OSError as exc:
            excluded.append((rel_dir.as_posix() or ".", f"无法读取: {exc}"))
            return
        for entry in entries:
            rel = rel_dir / entry.name
            rel_posix = rel.as_posix()
            if entry.is_dir():
                reason = exclusion_reason(rel_posix, rel.parts)
                if reason is None:
                    walk(entry, rel)
                    continue
                excluded.append((rel_posix, reason))
                if rel.parts[0] == "state":
                    # state/ 不剪枝: 仅为拾取 .gitkeep, 其余子项静默跳过
                    walk(entry, rel)
                continue
            if rel.parts[0] == "state" and rel_posix != STATE_KEEP_FILE.as_posix():
                continue  # 已由 state/ 目录条目汇总, 不逐文件计数
            reason = exclusion_reason(rel_posix, rel.parts)
            if reason is None:
                included.append((rel, entry.stat().st_size))
            else:
                excluded.append((rel_posix, reason))

    walk(repo_root, Path("."))
    return {"included": included, "excluded": excluded}


def _human_size(num_bytes: int) -> str:
    """字节数转人类可读 (KB/MB)。"""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / 1024 / 1024:.2f} MB"


VENDOR_NOTICES = """# 第三方内容剔除说明 (VENDOR NOTICES)

本分发包在打包时 (`scripts/package_dist.py`) 剔除了以下内容:

## 1. 许可证受限内容 (不可再分发)

| 被剔除路径 | 原因 |
|---|---|
| `templates/figures/vendor/scibox-diagram/` | 上游 [jihe520/sci-box] 未附正式 LICENSE 文件 (见仓库内 `templates/figures/vendor/VENDOR.md` §5), 再分发前必须移出 |
| `templates/figures/vendor/scibox-figure/` | 同上 |

**对终端用户的影响**: `SKILL.md` 与 `references/figure_skill_bridge.md` 中指向
vendor/scibox-* 的首选路由在分发版不可用。打包器已在分发副本的这两份文档顶部注入
"分发版路由说明"横幅, 路由改走自写模板:

- 论文示意图: `templates/figures/scripts/` 自写 drawio 可编辑模板 (6 件, 落盘自动过版式门禁)
- 数据图: `templates/figures/scripts/render_modeling_pack.py` (17 件, 统一色板 + figqa/figure_lint 硬门)
- 答辩/展示 HTML: `templates/figures/vendor/diagram-design/` 仍保留 (上游 MIT, 见其 THIRD_PARTY_LICENSES.md)

**scibox 独有能力在分发版不可用**: scibox-diagram 的 4 件高密度示意图模板与
scibox-figure 的 11 件差异图型 (tpe_surface、marginal_grid、cv_roc_ci 等) 已随目录
剔除, 分发版没有等价替代; 需要时请自行从上游仓库获取并遵守其许可条款。

## 2. 运行时/缓存产物 (可再生产)

| 被剔除路径 | 原因 |
|---|---|
| `.git/`, `.pytest_cache/`, `**/__pycache__/`, `%TEMP%/`, `dist/`, `.mimosa/` | 版本库、缓存与本地工具会话状态 |
| `state/` | 运行时状态目录, 仅保留 `.gitkeep` 占位 |
| `evals/results/` | 本地评测结果, 运行 `evals/run_eval.py score-run` 再生 |
| `outputs/` | 运行时图表输出目录 (vendor 冒烟测试可再生产物) |

完整规则与默认 dry-run 行为见 `scripts/package_dist.py` 模块 docstring。
"""


def rewrite_route_docs(dest: Path) -> list[str]:
    """在分发副本的路由文档顶部注入 vendor 剔除横幅, 返回改写的相对路径。

    只 prepend 不改写正文 (正文散布的 scibox 提及由横幅统一声明降级);
    源仓库文件不被触碰。
    """
    rewritten = []
    for rel in ROUTE_DOC_FILES:
        path = dest / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        path.write_text(_ROUTE_BANNER + text, encoding="utf-8")
        rewritten.append(rel)
    return rewritten


def cmd_package(args) -> int:
    """dry-run 打印清单/大小; --apply 复制并生成 VENDOR_NOTICES.md。"""
    repo_root = Path(args.repo_root).resolve() if args.repo_root else _SKILL_ROOT
    if not repo_root.is_dir():
        print(f"[FAIL] 仓库根不存在: {repo_root}")
        return 1
    try:
        version = read_version(repo_root)
    except (OSError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        return 1

    dist_root = (Path(args.out).resolve() if args.out else repo_root / "dist")
    dest = dist_root / f"mathmodel-studio-{version}"
    # 双保险: version 已限字符集, 此处再校验 resolve 后仍在 dist 根内
    if not dest.resolve().is_relative_to(dist_root.resolve()):
        print(f"[FAIL] 目标路径越界: {dest.resolve()} 不在 {dist_root.resolve()} 内")
        return 1

    plan = collect_plan(repo_root)
    included, excluded = plan["included"], plan["excluded"]
    total_bytes = sum(size for _, size in included)
    vendored = [rel for rel, reason in excluded if "LICENSE" in reason]

    print(f"仓库: {repo_root}")
    print(f"版本: {version} (来自 .codex-plugin/plugin.json)")
    print(f"目标: {dest}")
    print(f"纳入: {len(included)} 个文件, 共 {_human_size(total_bytes)}")
    print(f"剔除: {len(excluded)} 个路径 (其中许可证受限 {len(vendored)} 个)")

    if not args.apply:
        print("\n[剔除清单]")
        for rel, reason in excluded:
            print(f"  - {rel}  ({reason})")
        print("\n[纳入清单]")
        for rel, size in included:
            print(f"  + {rel.as_posix()}  ({_human_size(size)})")
        print("\n[DRY-RUN] 未复制任何文件; 加 --apply 真正打包 "
              "(dist 根将生成 VENDOR_NOTICES.md, 路由文档注入降级横幅)")
        return 0

    if dest.exists():
        print(f"[FAIL] 目标已存在, 拒绝覆盖: {dest}")
        return 1
    dest.mkdir(parents=True)
    copied = 0
    for rel, _size in included:
        src = repo_root / rel
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    # state/ 无 .gitkeep 时也保证占位 (空 state 目录不入包)
    state_keep = dest / STATE_KEEP_FILE
    if not state_keep.exists():
        state_keep.parent.mkdir(parents=True, exist_ok=True)
        state_keep.touch()
    rewritten = rewrite_route_docs(dest)
    notices = dest / "VENDOR_NOTICES.md"
    notices.write_text(VENDOR_NOTICES, encoding="utf-8")
    print(f"\n[OK] 复制 {copied} 个文件 -> {dest}")
    if rewritten:
        print(f"[OK] 路由降级横幅已注入: {', '.join(rewritten)}")
    print(f"[OK] 生成 {notices}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="package_dist.py",
        description="开源分发打包: 复制仓库到 dist/mathmodel-studio-<version>/, "
                    "剔除缓存/运行时产物与许可证受限的 vendor 目录")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", dest="apply", action="store_false",
                      help="只打印文件清单与大小 (默认行为)")
    mode.add_argument("--apply", dest="apply", action="store_true",
                      help="真正复制并生成 VENDOR_NOTICES.md")
    parser.set_defaults(apply=False)
    parser.add_argument("--out", type=Path, default=None,
                        help="dist 根目录 (默认 <repo>/dist/)")
    parser.add_argument("--repo-root", type=Path, default=None,
                        help="仓库根目录 (默认脚本所在仓库; 供合成 fixture 测试用)")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    return cmd_package(args)


if __name__ == "__main__":
    sys.exit(main())
