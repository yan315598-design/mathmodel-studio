"""
package_dist.py — 开源分发打包: 把 skill 仓库复制到 dist/mathmodel-studio-<version>/

version 从 .codex-plugin/plugin.json 读取 (限安全单段字符集, 防路径遍历)。

发布选择是**白名单制**: 只有下列顶层条目 (或注明的子路径) 才可能入包, 其余
顶层内容 (用户工作区、私有目录、未知目录与散落文件) 一律按「白名单外内容」剔除。
剔除与 git 是否跟踪无关——本脚本按文件系统实况遍历, 被 .gitignore 忽略但仍在
磁盘上的内容同样受规则约束。

    ① 运行资源 (runtime): 缺任一项 skill 都跑不起来
       SKILL.md  README.md  LICENSE  AGENTS.md  CHANGELOG.md
       .editorconfig/.gitattributes/.gitignore  .codex-plugin/  .claude-plugin/
       agents/  competitions/  config/  references/  scripts/  skills/  templates/
    ② 开发测试与归档 (dev, 可选): tests/  evals/  docs/  scripts/legacy/
       运行时不加载 (docs/legacy 自带"运行时不加载"声明); --no-dev 时整档剔除。
       注意: SKILL.md 等处仍以 `docs/legacy/...` 记述归档去向, --no-dev 会让这些
       记述悬空 (属精简变体取舍, 默认发布不剔除)。
    ③ 永不入包 (deny, 优先级最高, 路径比对大小写归一):
       凭证与内部材料  任意层级的 .env/.env.*/secrets.json/credentials.json/
                        credentials/*.pem/*.key/*.p12/*.pfx/id_rsa*/id_ed25519*/
                        .netrc/.git-credentials/.npmrc/.pypirc/private.md/answer.json;
                        凭证容器目录 _internal_notes/ .aws/ .ssh/ .gnupg/
       备份与临时      任意层级的 tmp/ temp/ backup* (含 backups_old 等前缀形态)/
                        %TEMP%/、*.bak/*.bak.*/*.tmp/*.orig/*.rej/*~/~$*
       非公开项目材料  figures/ 与 results/ (用户工作区真实项目产出, 含 answer.json)、
                        maintenance/ (人读本地语料库, 可能含原始私有语料/逐篇审读稿)、
                        templates/figures/gallery/golden/ 下 4 张实战成品图
                        (2026 国赛 A 题返工成品)、工作区归档 _archive/。
                        **只做选择隔离, 源仓库原件不删不移**
       许可证受限      templates/figures/vendor/scibox-diagram/ 与 scibox-figure/
                        (sci-box 上游未附正式 LICENSE, 见 templates/figures/vendor/VENDOR.md §5)
       缓存与运行时    .git/  .pytest_cache/  **/__pycache__/  .mimosa/  dist/
                        outputs/  evals/results/;  state/ 仅保留 .gitkeep 占位

符号链接与 Windows junction/reparse point 一律不随包分发 (防指向仓库外的路径逃逸);
遍历与扫描都不跟随链接, 且每项 resolve 后必须仍在仓库/候选根内。

最小必需契约: SKILL.md、.codex-plugin/plugin.json、LICENSE 缺任一即拒绝打包 (不做全量完整性检查)。

--apply 时:
  - 复制到 dist 根下的**唯一 staging 目录**, 先在 staging 内生成全部固定内容
    (横幅、VENDOR_NOTICES.md), 再扫描 staging 内的**最终字节**并计算逐文件 sha256 与
    包指纹 (指纹覆盖全部最终文件, **清单自身排除** —— 清单在指纹之后写入);
    同时做祖先非链接校验 (先扫源再复制存在 TOCTOU 窗口);
  - 命中凭证类 (hard) 默认**阻断发布** (候选目录不生成, staging 清理; --allow-suspects
    放行并记入清单); 私有来源声明/本地路径/邮箱类 (soft) 仅提示;
  - 发布只做**同盘 rename** (有界重试, 失败即失败): 不做 move/copytree 回退 —— 竞态下
    move 会把 staging 搬成 dest 的子目录并"成功", copytree 半途失败会留下半成品包;
    清理只针对自有 staging;
  - 包内生成 PACKAGE_CONTENTS.md (发布清单: 分档计数/剔除分类/许可证边界/扫描摘要/包指纹)
    与 VENDOR_NOTICES.md (第三方内容与许可证); 横幅注入在**闭合 frontmatter 之后**
    (直接 prepend 会让宿主技能发现失效), 覆盖 SKILL.md、references/figure_skill_bridge.md、
    templates/figures/gallery/README.md (源仓库文件不动);
  - 全量扫描明细 (逐条文本命中 + 哈希化文件指纹) 写到 <dist 根>/package_dist_scan_report.txt,
    不进包; 图像/PDF 未扫描 (未做 OCR), 需视觉通道另行复核。

路径展示统一口径 (命中/扫描对象/指纹清单/剔除清单/异常路径): 只给
**整体 sha256(原路径字符串) 前 8 位 + 安全扩展名**, 不回显任何路径分量 (目录名同样可能
自带敏感信息); 反查按同一算法对候选树逐个路径比对。

用法:
    python scripts/package_dist.py                  # --dry-run 默认: 打印清单/分档统计/扫描摘要
    python scripts/package_dist.py --apply          # 复制 + 生成 VENDOR_NOTICES / PACKAGE_CONTENTS
    python scripts/package_dist.py --apply --no-dev # 剔除开发测试与归档档
    python scripts/package_dist.py --scan-dir dist/mathmodel-studio-3.1.0 --report scan.txt
                                                    # 只扫描已有候选目录 (整合后复扫用)
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import shutil
import stat
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parent.parent

# version 拼入目标路径, 限单段安全字符集: 字母/数字开头, 后接 字母/数字/./_/-
# (拒绝 "../escaped"、"a/b" 等路径形态)
_VERSION_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z._-]*")

# ============================ 发布选择白名单 ============================
SELECT_TIER_RUNTIME = "runtime"
SELECT_TIER_DEV = "dev"

TIER_LABELS = {
    SELECT_TIER_RUNTIME: "运行资源",
    SELECT_TIER_DEV: "开发测试与归档 (--no-dev 可整档剔除)",
}

# ① 运行资源: 缺任一项 skill 都跑不起来
SELECT_RUNTIME_PREFIXES = (
    "SKILL.md", "README.md", "LICENSE", "AGENTS.md", "CHANGELOG.md",
    ".editorconfig", ".gitattributes", ".gitignore",
    ".codex-plugin", ".claude-plugin",
    "agents", "competitions", "config", "references", "scripts", "skills", "templates",
)

# ② 开发测试与归档: 运行时不加载 (scripts/legacy 判 dev 先于 scripts 的 runtime 档)。
#    注: maintenance/ 不在此档——人读本地语料默认按非公开材料剔除 (见 EXCLUDED_REL_PATHS)。
SELECT_DEV_PREFIXES = ("tests", "evals", "docs", "scripts/legacy")

# ============================ 永不入包 (deny) ============================
EXCL_CREDENTIAL = "凭证与内部材料"
EXCL_TEMP = "备份与临时"
EXCL_NONPUBLIC = "非公开项目材料"
EXCL_LICENSE = "许可证受限"
EXCL_RUNTIME = "缓存与运行时产物"
EXCL_OUTSIDE = "白名单外内容"
EXCL_LINK = "符号链接与重解析点"

# 报告与清单里的类别顺序 (固定, 便于逐次比对)
EXCL_CATEGORY_ORDER = (
    EXCL_CREDENTIAL, EXCL_TEMP, EXCL_NONPUBLIC, EXCL_LICENSE,
    EXCL_RUNTIME, EXCL_OUTSIDE, EXCL_LINK,
)

# 任意层级按目录名剔除 (键统一小写, 比对时目录名 .lower(); 类别见 EXCL_* 常量)
EXCLUDED_DIR_KINDS = {
    ".git": EXCL_RUNTIME,
    ".pytest_cache": EXCL_RUNTIME,
    "__pycache__": EXCL_RUNTIME,
    "dist": EXCL_RUNTIME,
    ".mimosa": EXCL_RUNTIME,
    "%temp%": EXCL_TEMP,
    "tmp": EXCL_TEMP,
    "temp": EXCL_TEMP,
    "backup": EXCL_TEMP,
    "backups": EXCL_TEMP,
    "_internal_notes": EXCL_CREDENTIAL,
    "_archive": EXCL_NONPUBLIC,
    # 凭证容器目录 (目录内文件常无扩展名/不在扫描白名单, 必须按容器整棵剔除)
    ".aws": EXCL_CREDENTIAL,
    ".ssh": EXCL_CREDENTIAL,
    ".gnupg": EXCL_CREDENTIAL,
}

# 任意层级按目录名前缀剔除 (备份类: backup / backups / backups_old / backup-2024 …)
EXCLUDED_DIR_PREFIXES: tuple[tuple[str, str], ...] = (("backup", EXCL_TEMP),)

# 任意层级按文件名剔除: 凭证/密钥/内部笔记 (与 git 是否跟踪无关)
# 含无扩展名的凭证容器文件 (.aws/credentials 等目录已整棵剔除, 这里兜住散落同名文件)
SENSITIVE_FILE_NAMES = frozenset({
    ".env", ".netrc", "secrets.json", "credentials.json", "credentials", "private.md",
    "answer.json", "id_rsa", "id_ed25519", ".git-credentials", ".npmrc", ".pypirc",
})
SENSITIVE_FILE_GLOBS = (".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*")

# 任意层级按文件名剔除: 备份/临时/编辑器残留
TEMP_FILE_GLOBS = ("*.bak", "*.bak.*", "*.tmp", "*.orig", "*.rej", "*~", "~$*")

# 真实项目成品图 (非公开项目材料): 只做选择隔离, 源仓库原件不删不移。
# gallery/README.md 声明这 4 张为 2026 国赛 A 题返工成品; 新增实战成品请在此登记。
NONPUBLIC_GOLDEN_FIGURES = (
    "templates/figures/gallery/golden/Q1_C1_field.png",
    "templates/figures/gallery/golden/Q2_C1_stages.png",
    "templates/figures/gallery/golden/Q34_C1_gridconv.png",
    "templates/figures/gallery/golden/Q4_C2_routes.png",
)

# 相对仓库根的精确路径剔除: rel → (类别, 说明); 文件本身命中或落在被剔目录内。
# 比对按小写归一 (Windows/macOS 文件系统大小写不敏感, 不做归一会漏放)。
EXCLUDED_REL_PATHS: dict[str, tuple[str, str]] = {
    "evals/results": (EXCL_RUNTIME, "评测结果为本地运行时产物"),
    "outputs": (EXCL_RUNTIME, "运行时图表输出目录 (vendor 冒烟测试可再生产物)"),
    "state": (EXCL_RUNTIME, "运行时状态目录 (仅保留 .gitkeep 占位)"),
    "figures": (EXCL_NONPUBLIC, "用户工作区图表输出 (真实项目图, 非公开项目材料)"),
    "results": (EXCL_NONPUBLIC, "用户工作区结果目录 (含 answer.json 等真实结果)"),
    "maintenance": (
        EXCL_NONPUBLIC,
        "人读本地语料库 (可能含原始私有语料/逐篇审读稿); 默认不进公开分发, 源仓库保留原件"),
    "templates/figures/vendor/scibox-diagram": (
        EXCL_LICENSE, "sci-box 上游未附正式 LICENSE, 不得再分发 (VENDOR.md §5)"),
    "templates/figures/vendor/scibox-figure": (
        EXCL_LICENSE, "sci-box 上游未附正式 LICENSE, 不得再分发 (VENDOR.md §5)"),
    **{fig: (EXCL_NONPUBLIC, "2026 国赛 A 题实战成品图 (真实项目交付物, 非公开项目材料)")
       for fig in NONPUBLIC_GOLDEN_FIGURES},
}
_EXCLUDED_REL_PATHS_LOWER = {rel.lower(): val for rel, val in EXCLUDED_REL_PATHS.items()}

# 最小必需契约: 缺任一项的"分发包"不可用 (入口 / 版本源 / 许可), 直接阻断而非照常出包
REQUIRED_ENTRIES = ("SKILL.md", ".codex-plugin/plugin.json", "LICENSE")

# state/ 整目录剔除但保留 .gitkeep 占位 (写入侧特判)
STATE_KEEP_FILE = Path("state") / ".gitkeep"

# 分发副本中需要注入横幅的文档: rel → 横幅正文 (源仓库不动, 只改 dist 里的副本)
# 注意: 横幅里的"被剔除资源"一律写资源名 (如 scibox-diagram), 不写仓库路径形态 ——
# 分发副本里那些路径不存在, 写成路径会被 test_doc_links 判为死链 (2026-09-19 修正)。
_ROUTE_BANNER = (
    "> **分发版路由说明**: 本分发包不含上游参考 `scibox-diagram` 与 `scibox-figure` "
    "(sci-box 上游无正式 LICENSE, 不得再分发; 二者**不是本包内的可用本地路径**, "
    "需要时请自行从上游获取), 详见 VENDOR_NOTICES.md。\n"
    "> 公开路由走本包实际随附的内容: 示意图用 "
    "`templates/figures/scripts/render_drawio_pack.py` / `render_diagram_pack.py`, "
    "数据图用 `templates/figures/scripts/render_modeling_pack.py`, 答辩/展示 HTML 用随包的 "
    "`templates/figures/vendor/diagram-design/` (MIT); scibox 独有的高密度示意图模板与"
    "非库图型 (tpe_surface、cv_roc_ci 等) 在分发版不可用, 属能力留白而非等价替代。\n"
    "> 另: `templates/figures/gallery/golden/` 的 4 张实战成品图 (Q1_C1_field / Q2_C1_stages / "
    "Q34_C1_gridconv / Q4_C2_routes) 属非公开项目材料, 分发版按默认选择规则隔离 "
    "(该目录保留 3 张模板样张); 识图先行纪律照旧, 见该目录 README 的分发版说明。\n\n"
)

_GOLDEN_BANNER = (
    "> **分发版说明**: 本分发包不含 `templates/figures/gallery/golden/` 下的 4 张实战成品图 "
    "(Q1_C1_field / Q2_C1_stages / Q34_C1_gridconv / Q4_C2_routes —— 真实项目交付物, 属非公开"
    "项目材料, 打包时按默认选择规则隔离, 原件留在源仓库)。下方表格中这 4 行在分发版没有"
    "对应文件; 需要视觉锚点时用同目录保留的 3 张 make_* 模板样张。\n\n"
)

DOC_BANNERS: dict[str, str] = {
    "SKILL.md": _ROUTE_BANNER,
    "references/figure_skill_bridge.md": _ROUTE_BANNER,
    "templates/figures/gallery/README.md": _GOLDEN_BANNER,
}

# ============================ 疑似敏感信息扫描 ============================
# 文本后缀白名单: 二进制/图片/PDF 一律跳过 (本脚本不做 OCR, 图内文字需视觉通道另行复核)。
SCAN_TEXT_SUFFIXES = frozenset({
    ".md", ".markdown", ".txt", ".rst", ".json", ".jsonl", ".py", ".toml", ".cfg",
    ".ini", ".yml", ".yaml", ".tex", ".bib", ".csv", ".tsv", ".drawio", ".mplstyle",
    ".sh", ".ps1", ".bat", ".cmd", ".html", ".css", ".js", ".mjs",
})
SCAN_TEXT_NAMES = frozenset({".gitignore", ".gitattributes", ".editorconfig", ".env.example"})
SCAN_MAX_BYTES = 2 * 1024 * 1024

# (名称, 级别, 正则, 是否脱敏输出): hard = 凭证类, 命中默认阻断打包; soft = 人工复核提示
TEXT_SCAN_PATTERNS: tuple[tuple[str, str, re.Pattern[str], bool], ...] = (
    ("private-key-block", "hard", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), True),
    ("github-token", "hard", re.compile(r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{20,}\b"), True),
    ("github-pat", "hard", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), True),
    ("openai-key", "hard", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{24,}\b"), True),
    ("aws-akid", "hard", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), True),
    ("google-api-key", "hard", re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"), True),
    ("slack-token", "hard", re.compile(r"\bxox[abprs]-[0-9A-Za-z\-]{10,}\b"), True),
    ("secret-assignment", "hard", re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret"
        r"|secret[_-]?key|password|passwd)\b[\"']?\s*[:=]\s*[\"']([^\"'\n]{12,})[\"']"), True),
    ("env-secret-line", "hard", re.compile(
        r"(?m)^[A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)[A-Z0-9_]*"
        r"\s*=\s*[\"']?[A-Za-z0-9+/=_\-]{16,}[\"']?\s*$"), True),
    ("windows-user-path", "soft", re.compile(r"[A-Za-z]:\\+Users\\+[^\s\"'`)\]|;]+"), True),
    ("unix-home-path", "soft", re.compile(r"(?<![\w./])/(?:home|Users)/[A-Za-z0-9._\-]+/"), True),
    ("email-address", "soft", re.compile(
        r"\b[A-Za-z0-9._%+\-]+@(?!(?:example\.(?:com|org|net)|localhost)\b)"
        r"[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), True),
    ("private-source-note", "soft", re.compile(
        r"2026\s*国赛\s*A\s*题|实战复盘|返工成品|实测台账"), False),
    ("private-record-location", "soft", re.compile(r"用户工作区|不入库"), False),
    ("internal-notes-ref", "soft", re.compile(r"_internal_notes|内部工作笔记"), False),
)

# 扫描边界声明 (进 PACKAGE_CONTENTS.md 与扫描报告, 防止把"扫过"读成"已去敏")
SCAN_BOUNDARY_NOTE = (
    "扫描范围: 纳入清单中的文本文件 (按后缀白名单); 二进制/图片/PDF 未扫描, 未做 OCR; "
    "命中仅为人工复核候选, 不构成「已去敏」结论 (私有来源声明类提示需项目侧决策); "
    "扫描器自身文件与其测试会命中自身词表 (自指噪声), 复核时按类别与文件筛选。"
)


@dataclass(frozen=True)
class PackEntry:
    """打包清单条目: rel 为相对仓库根的 posix 路径, size 仅对纳入条目有意义。"""

    rel: str
    size: int
    kind: str
    label: str


@dataclass(frozen=True)
class SuspectHit:
    """疑似敏感信息命中一条: level 取 hard(凭证类)/soft(复核提示)。"""

    rel: str
    line: int
    pattern: str
    level: str
    excerpt: str


def read_version(repo_root: Path) -> str:
    """从 .codex-plugin/plugin.json 读 version 并校验安全字符集。

    缺失/损坏/非对象/含路径分隔符 → 抛 OSError/ValueError (调用方转 [FAIL])。
    """
    plugin_path = repo_root / ".codex-plugin" / "plugin.json"
    if not plugin_path.exists():
        raise FileNotFoundError(f"plugin.json 不存在 ({display_path(str(plugin_path))})")
    with open(plugin_path, "r", encoding="utf-8") as f:
        plugin = json.load(f)
    if not isinstance(plugin, dict):
        raise ValueError(f"plugin.json 顶层必须是 JSON 对象 ({display_path(str(plugin_path))})")
    version = plugin.get("version")
    if not version or not isinstance(version, str):
        raise ValueError(f"plugin.json 缺 version 字符串字段 ({display_path(str(plugin_path))})")
    if not _VERSION_RE.fullmatch(version):
        raise ValueError(
            f"version 含不安全字符: {version!r} "
            f"(仅允许字母/数字开头, 后接 字母/数字/./_/-, 防路径越界)")
    return version


def _matches(rel_posix: str, prefixes: tuple[str, ...]) -> bool:
    """相对路径是否等于白名单条目或落在其下 (按路径分量边界, 不用裸字符串前缀)。"""
    return any(rel_posix == prefix or rel_posix.startswith(prefix + "/") for prefix in prefixes)


def selection_tier(rel_posix: str) -> str | None:
    """白名单档位: dev 档先判 (scripts/legacy 属 dev); 均未命中返回 None。"""
    if _matches(rel_posix, SELECT_DEV_PREFIXES):
        return SELECT_TIER_DEV
    if _matches(rel_posix, SELECT_RUNTIME_PREFIXES):
        return SELECT_TIER_RUNTIME
    return None


def _is_sensitive_name(name: str) -> bool:
    """凭证/密钥/内部笔记文件名判定 (任意层级; 大小写不敏感)。"""
    lowered = name.lower()
    if lowered in SENSITIVE_FILE_NAMES:
        return True
    return any(fnmatch.fnmatchcase(lowered, pat) for pat in SENSITIVE_FILE_GLOBS)


def _is_temp_name(name: str) -> bool:
    """备份/临时/编辑器残留文件名判定 (任意层级; 大小写不敏感)。"""
    lowered = name.lower()
    return any(fnmatch.fnmatchcase(lowered, pat) for pat in TEMP_FILE_GLOBS)


def _excluded_dir_kind(name: str) -> tuple[str, str] | None:
    """目录名 → (剔除类别, 命中规则名); 精确名优先, 再判备份前缀 (backup*/backups_old)。

    命中规则名用于展示区分: 精确名来自固定规则表 (可回显), 前缀命中可能是任意内容 (不回显)。
    """
    lowered = name.lower()
    kind = EXCLUDED_DIR_KINDS.get(lowered)
    if kind is not None:
        return kind, "name"
    for prefix, prefix_kind in EXCLUDED_DIR_PREFIXES:
        if lowered.startswith(prefix):
            return prefix_kind, "prefix"
    return None


def classify_path(rel_posix: str, parts: tuple[str, ...]) -> tuple[str, str]:
    """一条相对路径的发布选择判定 → (kind, label)。

    kind 取 SELECT_TIER_* 表示纳入 (label 为档位说明); 取 EXCL_* 表示剔除 (label 为原因)。
    优先级: 任意层级目录名剔除 > 精确路径 deny (小写归一) > 任意层级文件名 (凭证/临时)
            > 白名单档位 > 白名单外剔除。
    """
    name = parts[-1] if parts else rel_posix
    if rel_posix == STATE_KEEP_FILE.as_posix():
        return (SELECT_TIER_RUNTIME, "state/ 目录占位 (仅 .gitkeep)")
    for part in parts:  # 任意层级目录名 (大小写不敏感)
        hit = _excluded_dir_kind(part)
        if hit is not None:
            kind, matched_by = hit
            label = (f"按目录名剔除 ({part}/)" if matched_by == "name"
                     else "按目录前缀剔除 (backup*)")  # 前缀命中不回显实际目录名
            return (kind, label)
    lowered_rel = rel_posix.lower()  # 精确 deny 小写归一: 大小写不敏感文件系统上不可绕过
    for rel_path, (kind, label) in _EXCLUDED_REL_PATHS_LOWER.items():
        if lowered_rel == rel_path or lowered_rel.startswith(rel_path + "/"):
            return (kind, label)
    if _is_sensitive_name(name):
        return (EXCL_CREDENTIAL, "凭证/内部材料文件名")  # 不回显文件名 (可能自带敏感信息)
    if _is_temp_name(name):
        return (EXCL_TEMP, "备份/临时文件名")
    tier = selection_tier(rel_posix)
    if tier is None:
        return (EXCL_OUTSIDE, "不在发布选择白名单 (用户工作区/未知内容默认不放行)")
    return (tier, TIER_LABELS[tier])


def missing_required(included: list[PackEntry]) -> list[str]:
    """最小必需契约核验: 返回缺失的必需入口资源 (缺失即拒绝打包)。

    只要求"入口/版本源/许可"三件, 不做全量完整性检查 (那是 tests 的职责)。
    """
    present = {entry.rel.lower() for entry in included}
    return [rel for rel in REQUIRED_ENTRIES if rel.lower() not in present]


def _is_linklike(entry: Path) -> bool:
    """符号链接 / Windows junction 判定。

    NTFS junction 的 `is_symlink()` 为 False, 需另查 stat 的 reparse point 属性;
    两者都可能指向仓库外, 故一律不随包分发。
    """
    if entry.is_symlink():
        return True
    try:
        info = entry.stat(follow_symlinks=False)
    except OSError:
        return False
    attrs = getattr(info, "st_file_attributes", 0)
    return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def collect_plan(repo_root: Path) -> dict:
    """遍历仓库, 返回 {"included": [PackEntry], "excluded": [PackEntry]}。

    命中剔除规则的目录整棵子树剪枝、不深入; state/ 例外——记录目录级剔除条目后
    仍继续遍历, 仅放行 .gitkeep (其余子项不重复计数)。符号链接/junction 一律不跟随。
    """
    included: list[PackEntry] = []
    excluded: list[PackEntry] = []

    def walk(dir_path: Path, rel_dir: Path) -> None:
        try:
            entries = sorted(dir_path.iterdir())
        except OSError as exc:
            excluded.append(PackEntry(rel_dir.as_posix() or ".", 0, EXCL_RUNTIME,
                                      f"无法读取 ({safe_error(exc)})"))
            return
        for entry in entries:
            rel = rel_dir / entry.name
            rel_posix = rel.as_posix()
            if _is_linklike(entry):
                excluded.append(PackEntry(
                    rel_posix, 0, EXCL_LINK, "符号链接/junction (不随包分发, 防指向仓库外)"))
                continue
            if entry.is_dir():
                kind, label = classify_path(rel_posix, rel.parts)
                if kind in (SELECT_TIER_RUNTIME, SELECT_TIER_DEV):
                    walk(entry, rel)
                    continue
                excluded.append(PackEntry(rel_posix, 0, kind, label))
                if rel.parts[0] == "state":
                    # state/ 不剪枝: 仅为拾取 .gitkeep, 其余子项静默跳过
                    walk(entry, rel)
                continue
            if rel.parts[0] == "state" and rel_posix != STATE_KEEP_FILE.as_posix():
                continue  # 已由 state/ 目录条目汇总, 不逐文件计数
            try:
                size = entry.stat().st_size
            except OSError as exc:
                excluded.append(PackEntry(rel_posix, 0, EXCL_RUNTIME,
                                              f"无法读取 ({safe_error(exc)})"))
                continue
            kind, label = classify_path(rel_posix, rel.parts)
            if kind in (SELECT_TIER_RUNTIME, SELECT_TIER_DEV):
                included.append(PackEntry(rel_posix, size, kind, label))
            else:
                excluded.append(PackEntry(rel_posix, 0, kind, label))

    walk(repo_root, Path("."))
    return {"included": included, "excluded": excluded}


def walk_files(root: Path) -> list[Path]:
    """遍历 root 内普通文件 (不跟随符号链接/junction, 且 resolve 后必须仍在 root 内)。

    `Path.rglob` 在 Windows 上会穿过 junction (is_symlink() 为 False), 故改为显式
    剪枝遍历: 进入子目录前先判链接, 再校验解析结果落在 root 内 (防跨出读仓库外内容)。
    """
    root_resolved = root.resolve()
    found: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if _is_linklike(entry):
                continue
            try:
                if entry.is_dir():
                    stack.append(entry)
                    continue
                if not entry.is_file() or not entry.resolve().is_relative_to(root_resolved):
                    continue
            except OSError:
                continue
            found.append(entry)
    return found


def verify_package(dest: Path, expected: set[str]) -> list[str]:
    """回读目标目录, 返回计划外的相对路径 (防复制阶段混入未登记内容)。"""
    unexpected = []
    for path in walk_files(dest):
        rel = path.relative_to(dest).as_posix()
        if rel not in expected:
            unexpected.append(rel)
    return sorted(unexpected)


def _sha256_file(path: Path) -> str:
    """文件内容 sha256 (十六进制全串); 读取失败返回空串。"""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def package_digest(hashes: dict[str, str]) -> str:
    """包内容指纹: 对 (rel, sha256) 有序清单再哈希, 取前 16 位 (供复核钉版)。"""
    payload = "".join(f"{rel}\0{digest}\n" for rel, digest in sorted(hashes.items()))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _human_size(num_bytes: int) -> str:
    """字节数转人类可读 (KB/MB)。"""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / 1024 / 1024:.2f} MB"


def safe_error(exc: BaseException) -> str:
    """异常的安全展示串: 只给类型 + errno/winerror, **不用 str(exc)**。

    OSError 的字符串通常带文件路径/文件名 (Windows 尤甚), 属敏感展示; 调用方需要
    定位时用 display_path 另行给出哈希化标识。
    """
    parts = [exc.__class__.__name__]
    errno = getattr(exc, "errno", None)
    winerror = getattr(exc, "winerror", None)
    if errno is not None:
        parts.append(f"errno={errno}")
    if winerror is not None:
        parts.append(f"winerror={winerror}")
    return " ".join(parts)


def display_path(text: str) -> str:
    """展示用路径标识 (统一口径): 整体 sha256 前 8 位 + 安全扩展名。

    **不回显原路径任何分量** (目录名同样可能自带敏感信息), 只保留一个普通扩展名便于
    分辨文件类型 (形如 `\\.md`/`\\.json` 才保留)。命中/扫描对象/指纹清单/剔除清单/
    异常路径全部走这里。反查: 对目标树逐个候选路径算 sha256(原字符串)[:8] 比对。
    """
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    suffix = Path(text).suffix.lower()
    tail = suffix if re.fullmatch(r"\.[a-z0-9]{1,8}", suffix) else ""
    return f"<{digest}>{tail}"


def mask_snippet(snippet: str) -> str:
    """脱敏展示: 保留首 4/末 2 字符, 中间以 * 替代 (不打印完整疑似密钥)。"""
    text = snippet.strip()
    if len(text) <= 6:
        return "*" * len(text)
    return f"{text[:4]}{'*' * min(len(text) - 6, 12)}{text[-2:]}"


def _read_scan_text(path: Path) -> str | None:
    """读取待扫描文本; 过大/二进制/读取失败返回 None (跳过)。"""
    try:
        if path.stat().st_size > SCAN_MAX_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace")


def scan_text(rel: str, text: str) -> list[SuspectHit]:
    """扫描单份文本的疑似敏感信息, 返回命中清单 (按模式表顺序)。"""
    hits: list[SuspectHit] = []
    for name, level, pattern, masked in TEXT_SCAN_PATTERNS:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            snippet = match.group(0)
            hits.append(SuspectHit(
                rel=rel, line=line, pattern=name, level=level,
                excerpt=mask_snippet(snippet) if masked else snippet[:40].strip()))
    return hits


def scan_files(pairs: list[tuple[str, Path]]) -> dict:
    """扫描 (rel, path) 清单 → {"hard": [...], "soft": [...], "scanned": n, "skipped": n}。

    只扫后缀白名单内的文本文件; 非文本与超大文件计入 skipped (不做 OCR)。
    """
    hard: list[SuspectHit] = []
    soft: list[SuspectHit] = []
    scanned = skipped = 0
    for rel, path in pairs:
        if path.suffix.lower() not in SCAN_TEXT_SUFFIXES and path.name not in SCAN_TEXT_NAMES:
            skipped += 1
            continue
        text = _read_scan_text(path)
        if text is None:
            skipped += 1
            continue
        scanned += 1
        for hit in scan_text(rel, text):
            (hard if hit.level == "hard" else soft).append(hit)
    return {"hard": hard, "soft": soft, "scanned": scanned, "skipped": skipped}


def scan_tree(root: Path) -> dict:
    """扫描已有目录 (发布候选) 的文本疑似敏感信息; 返回结构与 scan_files 一致。

    与遍历侧同口径: 不跟随符号链接/junction (walk_files 剪枝 + resolve 落在 root 内)。
    """
    return scan_files([(path.relative_to(root).as_posix(), path) for path in walk_files(root)])


def publish_staging(staging: Path, dest: Path) -> None:
    """把 staging 落成候选目录: 同盘 rename, 有界重试; 失败即失败。

    不做 move/copytree 回退: 竞态下 dest 已被创建时 move 会把 staging 搬成 dest 的
    子目录并"成功", copytree 半途失败还会留下半成品正式包。Windows 上 rename 不覆盖
    已存在目录 (WinError 183), 因此 rename 成功即"由本次新建"; 清理只针对自有 staging。
    """
    last: OSError | None = None
    for attempt in range(3):
        try:
            staging.rename(dest)
            return
        except OSError as exc:
            if dest.exists():  # 目标已被抢先创建 (竞态): 不再重试, 直接失败
                raise
            last = exc
            time.sleep(0.2 * (attempt + 1))
    raise OSError(f"候选目录 rename 失败 (重试 3 次): {last}")


def _group_counts(entries: list[PackEntry]) -> dict[str, tuple[int, int]]:
    """按 kind 聚合 (路径数, 字节数)。"""
    counts: dict[str, tuple[int, int]] = {}
    for entry in entries:
        count, size = counts.get(entry.kind, (0, 0))
        counts[entry.kind] = (count + 1, size + entry.size)
    return counts


def render_scan_report(scan: dict, *, target: str,
                       digests: dict[str, str] | None = None) -> str:
    """渲染扫描明细报告 (可复核文本), 落到 dist 根、不进包。

    只列文本命中; 命中路径与扫描对象一律 display_path 脱敏 (不回显任何路径分量)。
    图像/PDF 未扫描 (未做 OCR), 需视觉通道另行复核 (图像清单一类的补充材料属维护报告)。
    digests 给出时附包内容指纹清单 (哈希化 rel + sha256 前 16 位), 供复核钉版。
    """
    lines = [
        "# package_dist 扫描明细 (不进分发包)",
        "",
        f"- 扫描对象: {display_path(target)}",
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 文本文件: 已扫 {scan['scanned']} 个, 跳过 (非文本/超大) {scan['skipped']} 个",
        f"- 硬命中 (凭证类): {len(scan['hard'])} 处; 软提示 (私有来源/本地路径/邮箱): {len(scan['soft'])} 处",
        f"- 边界: {SCAN_BOUNDARY_NOTE}",
        "- 路径展示: 统一为整体 sha256(原路径字符串) 前 8 位 + 安全扩展名 (不回显任何路径分量); "
        "反查对目标树逐个候选路径算 sha256[:8] 比对",
        "",
        "## 硬命中 (凭证类, 已脱敏)",
        "",
    ]
    lines += [f"- {display_path(hit.rel)}:{hit.line}  [{hit.pattern}]  {hit.excerpt}"
              for hit in scan["hard"]] or ["- (无)"]
    lines += ["", "## 软提示 (私有来源声明/本地路径/邮箱, 人工复核候选)", ""]
    lines += [f"- {display_path(hit.rel)}:{hit.line}  [{hit.pattern}]  {hit.excerpt}"
              for hit in scan["soft"]] or ["- (无)"]
    if digests:
        lines += ["", f"## 包内容指纹 ({len(digests)} 个文件; sha256 前 16 位, 路径已哈希化)", ""]
        lines += [f"- {display_path(rel)}  {digest[:16]}" for rel, digest in sorted(digests.items())]
        lines += ["", f"- 包指纹 (聚合): {package_digest(digests)}"]
    lines.append("")
    return "\n".join(lines)


def render_manifest(repo_root: Path, version: str, included: list[PackEntry],
                    excluded: list[PackEntry], scan: dict, *, no_dev: bool,
                    allow_suspects: bool, report_name: str,
                    digest: str) -> str:
    """渲染发布清单 PACKAGE_CONTENTS.md (分档计数/剔除分类/许可证边界/扫描摘要)。

    来源路径哈希化; 包指纹覆盖最终包内容 (不含本清单自身, 自引用排除)。
    """
    tiers = _group_counts(included)
    excl = _group_counts(excluded)
    dev_count, dev_size = tiers.get(SELECT_TIER_DEV, (0, 0))
    run_count, run_size = tiers.get(SELECT_TIER_RUNTIME, (0, 0))
    total_count, total_size = run_count + dev_count, run_size + dev_size
    lines = [
        "# 发布清单 (PACKAGE CONTENTS)",
        "",
        f"- 包名/版本: `mathmodel-studio-{version}` (version 来自 `.codex-plugin/plugin.json`)",
        f"- 来源仓库: {display_path(str(repo_root))} (路径已哈希化)",
        f"- 包内容指纹 (sha256/16): `{digest}` — 覆盖包内全部文件 (不含本清单自身, 自引用排除)",
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "- 选择规则: 白名单三档 (运行资源 / 开发测试与归档 / 永不入包), "
        "完整规则见 `scripts/package_dist.py` 模块 docstring",
        f"- 开发测试档: {'未纳入 (--no-dev)' if no_dev else '已纳入 (--no-dev 可整档剔除)'}",
        "",
        "## 纳入统计",
        "",
        "| 档位 | 文件数 | 大小 |",
        "|---|---|---|",
        f"| 运行资源 | {run_count} | {_human_size(run_size)} |",
        f"| 开发测试与归档 | {dev_count} | {_human_size(dev_size)} |",
        f"| 合计 | {total_count} | {_human_size(total_size)} |",
        "",
        "## 剔除统计 (按类别)",
        "",
        "| 类别 | 路径数 | 说明 |",
        "|---|---|---|",
    ]
    for kind in EXCL_CATEGORY_ORDER:
        count, _size = excl.get(kind, (0, 0))
        if count:
            lines.append(f"| {kind} | {count} | {_EXCL_CATEGORY_DOC[kind]} |")
    lines += [
        "",
        "**非公开项目材料 (默认不进公开分发, 源仓库保留原件)**: 真实项目成品图与用户工作区 "
        "结果目录 (资源名 figures、results, 含 `answer.json`)、以及人读本地语料库 "
        "(资源名 maintenance, 可能含原始私有语料) 按默认选择规则隔离 —— 这些资源"
        "**不在本包内** (上表计数是源仓库侧的剔除台账, 不是包内路径)。凭证类文件/目录 "
        "(.env / secrets.json / *.pem / *.key / private.md / `.aws/` / `.ssh/` / `.gnupg/` 等) "
        "任意层级默认剔除, 与 git 是否跟踪无关。",
        "",
        "## 许可证边界",
        "",
        "- 未随包分发: 上游参考 `scibox-diagram`、`scibox-figure` "
        "(sci-box 上游未附正式 LICENSE, 不得再分发) —— 二者不在本包内, 不是可用本地路径; "
        "详见 `VENDOR_NOTICES.md`",
        "- 随附: `vendor/diagram-design/` (MIT)、`vendor/icarus-figures/` (MIT, 见其 LICENSE), "
        "本仓库自身代码 MIT (见 LICENSE)",
        "",
        "## 疑似敏感信息扫描 (文本)",
        "",
        f"- 扫描: staging 实际文件中的 {scan['scanned']} 个文本文件 "
        f"(后缀白名单; 跳过 {scan['skipped']} 个非文本/超大; 含生成件, 本清单自身自引用排除)",
        f"- 硬命中 (凭证类): {len(scan['hard'])} 处"
        + (" [--allow-suspects 放行, 需人工确认]" if allow_suspects and scan["hard"] else ""),
        f"- 软提示 (私有来源声明/本地路径/邮箱): {len(scan['soft'])} 处 — 人工复核候选, 未去敏",
        f"- 边界: {SCAN_BOUNDARY_NOTE}",
        f"- 明细 (逐条命中, 已脱敏): `{report_name}` (dist 根, 不进包)",
        "",
        "## 已知覆盖边界",
        "",
        "- 图像/PDF 内文字未扫描 (未做 OCR), 需视觉通道另行复核 (非自动清单, 属维护侧补充材料)",
        "- 私有来源声明 (references/ 内 2026 国赛 A 题实测类叙述) 只做提示, 不做改写",
        "",
    ]
    return "\n".join(lines)


_EXCL_CATEGORY_DOC = {
    EXCL_CREDENTIAL: "凭证/密钥/内部笔记 (任意层级, 与 git 跟踪无关)",
    EXCL_TEMP: "备份/临时/编辑器残留 (任意层级)",
    EXCL_NONPUBLIC: "非公开项目材料 (真实项目成品图、用户工作区结果)",
    EXCL_LICENSE: "上游无正式 LICENSE, 不可再分发",
    EXCL_RUNTIME: "缓存/运行时产物 (可再生产)",
    EXCL_OUTSIDE: "不在发布选择白名单 (用户工作区/未知内容)",
    EXCL_LINK: "符号链接/junction (防指向仓库外)",
}


VENDOR_NOTICES = """# 第三方内容剔除说明 (VENDOR NOTICES)

本分发包在打包时 (`scripts/package_dist.py`) 剔除了以下内容:

## 1. 许可证受限内容 (未随包分发, 不可再分发)

| 未随包分发的资源 (资源名) | 原因 |
|---|---|
| `scibox-diagram` | 上游 [jihe520/sci-box] 未附正式 LICENSE 文件 (见本包内 `templates/figures/vendor/VENDOR.md` §5), 再分发前必须移出 |
| `scibox-figure` | 同上 |

二者**不在本包内**, 也不是可用本地路径; 本包随附的上游副本只有 MIT 的
`diagram-design` 与 `icarus-figures` 两个。

**对终端用户的影响**: `SKILL.md` 与 `references/figure_skill_bridge.md` 中指向
scibox-diagram / scibox-figure 的首选路由在分发版不可用。打包器已在分发副本的这两份文档顶部注入
"分发版路由说明"横幅, 公开路由改走本包实际随附的内容:

- 论文示意图 (drawio): 自写可编辑模板 7 件 (`templates/figures/scripts/render_drawio_pack.py`), 落盘自动过版式门禁 (XML 自验 + drawio_check 体检)
- 论文示意图 (matplotlib): 自写直出模板 4 件 (`templates/figures/scripts/render_diagram_pack.py`), 该脚本只打印 figqa 提示, **不自动执行**——生成后按提示另跑 `figqa.py`
- 数据图: `templates/figures/scripts/render_modeling_pack.py` (25 件, 统一色板 + figqa/figure_lint 硬门)
- 答辩/展示 HTML: `templates/figures/vendor/diagram-design/` 仍保留 (上游 MIT, 见其 THIRD_PARTY_LICENSES.md)

**scibox 独有能力在分发版不可用**: scibox-diagram 的 4 件高密度示意图模板与
scibox-figure 的 11 件差异图型 (tpe_surface、marginal_grid、cv_roc_ci 等) 已随资源
一并剔除, 分发版没有等价替代 (属能力留白); 需要时请自行从上游仓库获取并遵守其许可条款。

## 2. 非公开项目材料与凭证类内容 (默认剔除, 与 git 跟踪无关)

| 未随包分发的内容 (资源名/模式) | 原因 |
|---|---|
| `figures`、`results` (含 `answer.json`) | 用户工作区真实项目产出, 非公开项目材料; 源仓库原件保留, 只做选择隔离 |
| `maintenance` | 人读本地语料库 (可能含原始私有语料/逐篇审读稿); 默认不进公开分发, 源仓库保留原件 |
| `templates/figures/gallery/golden/` 4 张实战成品图 (Q1_C1_field / Q2_C1_stages / Q34_C1_gridconv / Q4_C2_routes) | 2026 国赛 A 题返工成品, 非公开项目材料; 分发版保留该目录 3 张 make_* 模板样张, 已注入分发版说明 |
| `.env` / `.env.*` / `secrets.json` / `credentials.json` / `credentials` / `*.pem` / `*.key` / `private.md` / `answer.json` / `id_rsa*` / `.netrc` / `.git-credentials` / `.npmrc` / `.pypirc` | 凭证与密钥类, 任意层级默认剔除 (与 git 是否跟踪无关) |
| `_internal_notes/`、`.aws/`、`.ssh/`、`.gnupg/` | 内部笔记与凭证容器目录, 整棵剔除 (容器内文件常无扩展名, 不依赖扫描发现) |
| `_archive/`、`tmp/`、`temp/`、`backup*` (含 `backups_old` 等)、`*.bak` / `*.bak.*` / `*.tmp` / `*.orig` / `*.rej` / `*~` / `~$*` | 归档与备份/临时文件 |

类别计数与实际剔除路径级明细见包内 `PACKAGE_CONTENTS.md` (明细报告落在 dist 根, 不进包)。

## 3. 运行时/缓存产物 (可再生产)

| 被剔除路径 | 原因 |
|---|---|
| `.git/`, `.pytest_cache/`, `**/__pycache__/`, `%TEMP%/`, `dist/`, `.mimosa/` | 版本库、缓存与本地工具会话状态 |
| `state/` | 运行时状态目录, 仅保留 `.gitkeep` 占位 |
| `evals/results/` | 本地评测结果, 运行 `evals/run_eval.py score-run` 再生 |
| `outputs/` | 运行时图表输出目录 (vendor 冒烟测试可再生产物) |

完整规则与默认 dry-run 行为见 `scripts/package_dist.py` 模块 docstring。
"""


def _insert_banner(text: str, banner: str) -> str:
    """把横幅插到 YAML frontmatter 之后 (无 frontmatter 时插到文首)。

    SKILL.md 的 frontmatter 必须在文件最前, 直接 prepend 会让宿主技能发现失效
    (v3.1.0 复审 P2 修正)。
    """
    if not text.startswith("---"):
        return banner + text
    lines = text.splitlines(keepends=True)
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            head = "".join(lines[: index + 1])
            tail = "".join(lines[index + 1:]).lstrip("\n")
            return f"{head}\n{banner}{tail}"
    return banner + text


def rewrite_route_docs(dest: Path) -> list[str]:
    """在分发副本的指定文档注入横幅 (frontmatter 之后), 返回改写的相对路径。

    只加横幅不改写正文 (正文散布的 scibox / golden 提及由横幅统一声明降级);
    源仓库文件不被触碰。
    """
    rewritten = []
    for rel, banner in DOC_BANNERS.items():
        path = dest / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        path.write_text(_insert_banner(text, banner), encoding="utf-8")
        rewritten.append(rel)
    return rewritten


def _print_hits(hits: list[SuspectHit], limit: int) -> None:
    """打印命中 (截断到 limit 条, 路径脱敏); 说明明细去向由调用方给。"""
    for hit in hits[:limit]:
        print(f"  - {display_path(hit.rel)}:{hit.line}  [{hit.pattern}]  {hit.excerpt}")
    if len(hits) > limit:
        print(f"  ... 其余 {len(hits) - limit} 条见明细报告 (路径同样脱敏, 按 sha256(rel)[:8] 反查)")


def _print_scan_summary(scan: dict) -> None:
    """打印扫描摘要 + 命中样例 (路径脱敏)。"""
    print("\n[疑似敏感信息扫描]")
    print(f"  扫描文本文件 {scan['scanned']} 个 (跳过非文本/超大 {scan['skipped']} 个); "
          f"硬命中 {len(scan['hard'])} / 软提示 {len(scan['soft'])}")
    if scan["hard"]:
        _print_hits(scan["hard"], 10)
    if scan["soft"]:
        _print_hits(scan["soft"], 5)
        print(f"  软提示共 {len(scan['soft'])} 处: 私有来源声明/本地路径类, 属人工复核候选 "
              "(扫描不等于已去敏)")


def _print_plan_summary(included: list[PackEntry], excluded: list[PackEntry]) -> None:
    """打印分档/分类统计 (dry-run 与 apply 共用)。"""
    tiers = _group_counts(included)
    excl = _group_counts(excluded)
    run_count, run_size = tiers.get(SELECT_TIER_RUNTIME, (0, 0))
    dev_count, dev_size = tiers.get(SELECT_TIER_DEV, (0, 0))
    total_bytes = sum(entry.size for entry in included)
    print(f"纳入: {len(included)} 个文件, 共 {_human_size(total_bytes)}"
          f" (运行资源 {run_count} / {_human_size(run_size)}, "
          f"开发测试与归档 {dev_count} / {_human_size(dev_size)})")
    parts = [f"{kind} {excl[kind][0]}" for kind in EXCL_CATEGORY_ORDER if kind in excl]
    print(f"剔除: {len(excluded)} 个路径 ({'; '.join(parts) if parts else '无'})")


def cmd_package(args) -> int:
    """dry-run 打印清单/分档统计/扫描摘要; --apply 复制并生成说明与清单。"""
    repo_root = Path(args.repo_root).resolve() if args.repo_root else _SKILL_ROOT
    if not repo_root.is_dir():
        print(f"[FAIL] 仓库根不存在: {display_path(str(repo_root))}")
        return 1
    try:
        version = read_version(repo_root)
    except (OSError, ValueError) as exc:
        print(f"[FAIL] {exc}")  # 本模块自抛文案, 路径已 display_path 化
        return 1

    dist_root = (Path(args.out).resolve() if args.out else repo_root / "dist")
    dest = dist_root / f"mathmodel-studio-{version}"
    # 双保险: version 已限字符集, 此处再校验 resolve 后仍在 dist 根内
    if not dest.resolve().is_relative_to(dist_root.resolve()):
        print(f"[FAIL] 目标路径越界: {display_path(str(dest.resolve()))} "
              f"不在 {display_path(str(dist_root.resolve()))} 内")
        return 1
    if args.apply and dest.exists():
        print(f"[FAIL] 目标已存在, 拒绝覆盖: {display_path(str(dest))}")
        return 1

    plan = collect_plan(repo_root)
    included = [entry for entry in plan["included"]
                if not (args.no_dev and entry.kind == SELECT_TIER_DEV)]
    excluded = list(plan["excluded"])

    missing = missing_required(included)
    if missing:
        print(f"[FAIL] 缺少必需入口资源 (最小契约 {', '.join(REQUIRED_ENTRIES)}): "
              f"{', '.join(missing)}")
        return 1

    print(f"仓库: {display_path(str(repo_root))} (路径已哈希化)")
    print(f"版本: {version} (来自 .codex-plugin/plugin.json)")
    print(f"目标: {display_path(str(dest))}")
    _print_plan_summary(included, excluded)

    if not args.apply:
        scan = scan_files([(entry.rel, repo_root / entry.rel) for entry in included])
        _print_scan_summary(scan)
        print("  (dry-run 扫源文件集合; 生成件与横幅文档只在 --apply 的 staging 内存在)")
        print("\n[剔除清单]")
        for entry in excluded:
            print(f"  - {display_path(entry.rel)}  ({entry.label})")
        print("\n[纳入清单]")
        for entry in included:
            print(f"  + {display_path(entry.rel)}  ({_human_size(entry.size)})  [{entry.kind}]")
        print("  (清单路径统一哈希化显示; 反查按 sha256(相对路径)[:8] 比对)")
        print("\n[DRY-RUN] 未复制任何文件; 加 --apply 真正打包 "
              "(dist 根将生成 VENDOR_NOTICES.md / PACKAGE_CONTENTS.md, 路由文档注入横幅)")
        return 0

    # --- 唯一 staging: 先把纳入清单复制进来, 扫描"最终将发布的字节", 通过后才发布 ---
    # (先扫源再复制存在 TOCTOU: 复制到的字节可能从未被扫描; 故扫描对象是 staging 内实际字节)
    dist_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".package_dist-staging-", dir=dist_root))
    try:
        for entry in included:
            src = repo_root / entry.rel
            dst = staging / entry.rel
            # 祖先非链接校验: 计划与复制之间若被换成 junction/链接, resolve 会落到仓库外
            if not src.resolve().is_relative_to(repo_root):
                raise OSError(f"源路径解析越界 (疑似被替换为链接): {display_path(entry.rel)}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        # state/ 无 .gitkeep 时也保证占位 (空 state 目录不入包)
        state_keep = staging / STATE_KEEP_FILE
        if not state_keep.exists():
            state_keep.parent.mkdir(parents=True, exist_ok=True)
            state_keep.touch()
        # 固定内容 (横幅/VENDOR_NOTICES) 先落, 再扫/hash —— 保证指纹覆盖最终内容
        rewritten = rewrite_route_docs(staging)
        notices = staging / "VENDOR_NOTICES.md"
        notices.write_text(VENDOR_NOTICES, encoding="utf-8")
        staged = [PackEntry(e.rel, (staging / e.rel).stat().st_size, e.kind, e.label)
                  for e in included]

        # 扫描对象 = staging 内**实际**文件集合 (含生成的 VENDOR_NOTICES 与改写后的横幅文档,
        # 不再按源清单枚举 —— 否则会漏掉生成件); PACKAGE_CONTENTS.md 自引用排除 (此刻尚未生成)
        scan_pairs = [(path.relative_to(staging).as_posix(), path)
                      for path in walk_files(staging)
                      if path.name != "PACKAGE_CONTENTS.md"]
        scan = scan_files(scan_pairs)
        _print_scan_summary(scan)
        if scan["hard"] and not args.allow_suspects:
            print("[FAIL] 已复制字节中存在凭证类 (hard) 疑似敏感信息, 已阻断发布 "
                  "(候选目录未生成, staging 已清理)")
            print("       处置: 从源仓库移除或改占位后重跑; 确认为误报时加 --allow-suspects "
                  "(会记入 PACKAGE_CONTENTS.md)")
            return 1
        if scan["hard"]:
            print("[WARN] --allow-suspects 已放行上述硬命中 (记入发布清单)")

        # 指纹: 覆盖此时 staging 内全部文件 (即最终包内容); 清单自身最后写, 天然不入指纹
        hashes = {path.relative_to(staging).as_posix(): _sha256_file(path)
                  for path in walk_files(staging)}
        digest = package_digest(hashes)
        manifest = staging / "PACKAGE_CONTENTS.md"
        report_name = "package_dist_scan_report.txt"
        manifest.write_text(
            render_manifest(repo_root, version, staged, excluded, scan,
                            no_dev=args.no_dev, allow_suspects=args.allow_suspects,
                            report_name=report_name, digest=digest),
            encoding="utf-8")

        expected = {entry.rel for entry in included}
        expected |= {STATE_KEEP_FILE.as_posix(), "VENDOR_NOTICES.md", "PACKAGE_CONTENTS.md"}
        unexpected = verify_package(staging, expected)
        if unexpected:
            print(f"[FAIL] staging 出现计划外文件 {len(unexpected)} 个, 拒绝发布: "
                  f"{', '.join(display_path(rel) for rel in unexpected[:5])}")
            return 1
        if args.report is not None:
            print("[WARN] --report 仅用于 --scan-dir 模式, 已忽略 "
                  "(打包模式的明细固定写 dist 根, 保证不进包)")
        publish_staging(staging, dest)  # 全部通过才落候选目录
    except OSError as exc:
        print(f"[FAIL] 打包中断 ({safe_error(exc)}); 失败详情不回显 (可能含路径/文件名)")
        return 1
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    report_path = dist_root / report_name
    report_path.write_text(
        render_scan_report(scan, target=str(repo_root), digests=hashes), encoding="utf-8")
    print()
    print(f"[OK] 复制 {len(included)} 个文件 -> {display_path(str(dest))}")
    print(f"[OK] 包内容指纹 (sha256/16): {digest}")
    if rewritten:
        print(f"[OK] 分发版横幅已注入 (frontmatter 之后): {', '.join(rewritten)}")
    print(f"[OK] 生成 VENDOR_NOTICES.md / PACKAGE_CONTENTS.md")
    print(f"[OK] 扫描明细 (不进包, 含文件指纹): {display_path(str(report_path))}")
    return 0


def cmd_scan_dir(scan_root: Path, report: Path | None) -> int:
    """只扫描已有目录 (发布候选) 的文本疑似敏感信息: 硬命中退出码 1, 其余 0。

    图像/PDF 不在扫描范围 (未做 OCR); 需要图像复核清单时另出维护报告。
    """
    if not scan_root.is_dir():
        print(f"[FAIL] 目录不存在: {display_path(str(scan_root))}")
        return 1
    scan = scan_tree(scan_root)
    print(f"扫描对象: {display_path(str(scan_root))}")
    print(f"文本文件: 已扫 {scan['scanned']} 个 (跳过非文本/超大 {scan['skipped']} 个)")
    print(f"硬命中 (凭证类): {len(scan['hard'])} 处 / 软提示: {len(scan['soft'])} 处")
    if scan["hard"]:
        _print_hits(scan["hard"], 10)
    if scan["soft"]:
        _print_hits(scan["soft"], 5)
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            render_scan_report(scan, target=str(scan_root)), encoding="utf-8")
        print(f"[OK] 明细报告: {display_path(str(report))}")
    else:
        print("[提示] 加 --report <文件> 落全量明细")
    print(f"边界: {SCAN_BOUNDARY_NOTE}")
    return 1 if scan["hard"] else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="package_dist.py",
        description="开源分发打包: 复制仓库到 dist/mathmodel-studio-<version>/, "
                    "按白名单剔除缓存/运行时产物、许可证受限内容、凭证与非公开项目材料")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", dest="apply", action="store_false",
                      help="只打印文件清单与大小 (默认行为)")
    mode.add_argument("--apply", dest="apply", action="store_true",
                      help="真正复制并生成 VENDOR_NOTICES.md / PACKAGE_CONTENTS.md")
    mode.add_argument("--scan-dir", type=Path, default=None, metavar="DIR",
                      help="只扫描已有候选目录的文本疑似敏感信息 (不打包)")
    parser.set_defaults(apply=False)
    parser.add_argument("--out", type=Path, default=None,
                        help="dist 根目录 (默认 <repo>/dist/)")
    parser.add_argument("--repo-root", type=Path, default=None,
                        help="仓库根目录 (默认脚本所在仓库; 供合成 fixture 测试用)")
    parser.add_argument("--no-dev", dest="no_dev", action="store_true",
                        help="剔除开发测试与归档档 (tests/ evals/ docs/ maintenance/ scripts/legacy/)")
    parser.add_argument("--allow-suspects", dest="allow_suspects", action="store_true",
                        help="文本扫描硬命中 (凭证类) 时仍继续打包 (记入 PACKAGE_CONTENTS.md)")
    parser.add_argument("--report", type=Path, default=None,
                        help="--scan-dir 模式的明细报告落盘路径")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    if args.scan_dir is not None:
        return cmd_scan_dir(Path(args.scan_dir).resolve(), args.report)
    return cmd_package(args)


if __name__ == "__main__":
    sys.exit(main())
