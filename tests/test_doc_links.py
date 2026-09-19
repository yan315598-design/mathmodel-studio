# -*- coding: utf-8 -*-
"""文档相对路径死链回归测试（v2.8.0 治理机制）。

背景：Phase 0 修复了 45 条死链（quick_runner 审计清单），本测试把检查逻辑固化为
正式回归，防止归档/移库/改名后再产生死链。逻辑参考 Phase 0 的临时脚本
`_p0_link_check.py`（收编为全量扫描）。

检查对象：仓库内全部 .md 文件中 ``反引号内联代码`` 与 ``[文本](目标)`` 链接里的
"像路径的字符串"，按 (引用文件所在目录 / 仓库根) 两级解析，目标存在（文件或目录）
即通过。

扫描排除（历史叙述/外部资产豁免，逐条理由）：
- .git / __pycache__ / .pytest_cache   —— 非文档资产；
- docs/legacy/    —— 归档区，内部引用按归档当时的状态冻结，不随现状修；
- templates/figures/vendor/ —— 上游开源 skill 原样副本，不做本仓库级路径校验；
- maintenance/    —— 维护期人读总稿（历史叙述），豁免；
- CHANGELOG.md    —— 只读历史叙事，引用的是当时存在的文件（如已删除的
  tests/test_prompts.json），改写历史条目反而破坏审计线索；
- evals/holdout_index/、evals/results/ —— 评测时生成的目录，仓库里不存在属预期。

候选豁免（占位符与工作区路径，规则来自 Phase 0 实测误报）：
- 含 <> * {} [] () … 或 "..." —— 模板占位/通配/省略写法；
- 含 ":" —— 命令、qualified ref（如 scripts/x.py:SYMBOL）或 URL 协议；
- 以 $ # http: https: mailto: / 开头 —— 变量、锚点、URL、斜杠命令；
- 以 .agents/ .claude/ $HOME 开头 —— 用户环境安装位置，不在仓库内
  （.codex-plugin/ .claude-plugin/ 是仓库内真实路径，不豁免）；
- 以 cwd/ state/ results/ figures/ code/ paper/ data/ submission/
  paper_workspace/ _archive/ workspace/ 开头 —— 用户工作区路径，非仓库资产
  （注意 state/ 既是工作区前缀也蒙蔽仓库同名空目录，工作区语义优先）；
- 不含 "/" 的裸文件名（如 `check_gate.py`、`rubrics.md`）—— 需 <comp>/scripts/
  等语境才能解析的简写，Phase 0 审计未把它们列为死链，不做机器判定。

判定范围收窄：候选需以仓库顶级目录开头（agents/ competitions/ config/ docs/
evals/ maintenance/ references/ scripts/ skills/ templates/ tests/）或带文件扩展名
（覆盖 ../.. 相对引用），其余斜杠串（GitHub 仓库名、npg/aaas/lancet/nejm 色板列举、
word/media/ pandoc 内部路径等叙述性斜杠）不判。
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

EXCLUDE_DIR_PARTS = {".git", "__pycache__", ".pytest_cache"}
EXCLUDE_PATH_PREFIXES = (
    "docs/legacy/",
    "templates/figures/vendor/",
    "maintenance/",
)
EXCLUDE_FILES = {"CHANGELOG.md"}

BACKTICK_RE = re.compile(r"`([^`\n]+)`")
MDLINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

# 用户工作区 / 评测生成物前缀：不是仓库资产，目标不存在属预期。
WORKSPACE_PREFIXES = (
    "cwd/", "state/", "results/", "figures/", "code/", "paper/", "data/",
    "submission/", "paper_workspace/", "_archive/", "workspace/",
    "evals/holdout_index/", "evals/results/",
)

# 用户环境安装位置（.codex-plugin/ 与 .claude-plugin/ 是仓库内路径，不在此列）。
INSTALL_PREFIXES = (".agents/", ".claude/", "$HOME")

# 仓库顶级目录：以这些开头的斜杠串一律纳入判定。
REPO_TOP_DIRS = (
    "agents/", "competitions/", "config/", "docs/", "evals/",
    "maintenance/", "references/", "scripts/", "skills/",
    "templates/", "tests/",
)

EXT_RE = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,9}$")

BAD_CHARS = set("<>*{}[]()…:")


def iter_markdown_files() -> list[Path]:
    files = []
    for path in REPO_ROOT.rglob("*.md"):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(part in EXCLUDE_DIR_PARTS for part in path.parts):
            continue
        if rel.startswith(EXCLUDE_PATH_PREFIXES):
            continue
        if rel in EXCLUDE_FILES:
            continue
        files.append(path)
    return sorted(files)


def extract_candidates(text: str) -> list[str]:
    spans = [m.group(1) for m in BACKTICK_RE.finditer(text)]
    spans += [m.group(1) for m in MDLINK_RE.finditer(text)]
    return spans


def is_checkable(candidate: str) -> bool:
    """判定一个反引号/链接字符串是否纳入路径检查。"""
    s = candidate.strip().rstrip(".,;:，。；：）)】»")
    if not s or "/" not in s:
        return False
    if " " in s or "\\" in s:
        return False
    if any(ch in BAD_CHARS for ch in s):
        return False
    if "..." in s:
        return False
    if s.startswith(("$", "#", "http:", "https:", "mailto:", "/")):
        return False
    if s.startswith(INSTALL_PREFIXES):
        return False
    target = s.split("#", 1)[0]
    if not target or target.startswith(WORKSPACE_PREFIXES):
        return False
    if "__pycache__" in target:
        return False
    if target.startswith(REPO_TOP_DIRS) or EXT_RE.search(target):
        return True
    return False


def resolve_target(md_file: Path, target: str) -> bool:
    return (md_file.parent / target).exists() or (REPO_ROOT / target).exists()


def collect_dead_links() -> list[str]:
    dead = []
    for md_file in iter_markdown_files():
        text = md_file.read_text(encoding="utf-8", errors="replace")
        for candidate in extract_candidates(text):
            cleaned = candidate.strip().rstrip(".,;:，。；：）)】»")
            if not is_checkable(candidate):
                continue
            target = cleaned.split("#", 1)[0]
            if not resolve_target(md_file, target):
                dead.append(f"{md_file.relative_to(REPO_ROOT).as_posix()} -> {target}")
    return dead


def test_no_dead_relative_links():
    dead = collect_dead_links()
    assert not dead, "发现死链（引用了不存在的仓库相对路径）:\n" + "\n".join(dead)
