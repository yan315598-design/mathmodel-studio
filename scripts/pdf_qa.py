# -*- coding: utf-8 -*-
"""渲染后 PDF 终检: 提交前对成品 PDF 做四类机械检查。

  ① 页数超限      pypdf 读页数; --max-pages 或按 --competition 默认值
                   （mcm=25 页; 其他竞赛无内置默认, 跳过并提示）
  ② 重复图表标题  行首锚定的 "图 1：/表 2:/Figure 3:/Fig. 4/Table 5" 前缀
                   在全文出现多次即报重复编号（防正文引用误报, 只锚定行首）;
                   编号 key 跨语言统一: 图 1/Figure 1/Fig.1 → figure:1,
                   表 1/Table 1 → table:1（中英混排重复同样检出）
  ③ 匿名扫描      --anonymous 时: PDF 元数据（Author/Creator/Producer）含
                   人名模式则报; 第 1 页正文扫邮箱/11 位手机号/CJK 姓名启发式
                   （2-4 个连续汉字 + 分隔符 + "大学/学院" 上下文;
                   LaTeX/matplotlib 等工具词白名单排除）
  ④ 空白页检测    pypdf 提取每页文本 < 10 字符判空白页, 报告页码

用法:
    python scripts/pdf_qa.py paper.pdf --max-pages 25
    python scripts/pdf_qa.py paper.pdf --anonymous --competition mcm

报告分级 ✅ 通过 / ⚠️ 提示 / ❌ 违例; 存在 ❌ 时退出码 1。

退出码:
    0  无 ❌（⚠️ 不影响）
    1  存在 ❌ 违例, 或 pypdf 缺失导致关键检查无法执行
    2  PDF 不存在 / 无法解析等致命错误

已知限制:
    - 扫描版 PDF（无文本层）会把全部页判为空白页, 请人工复核;
    - CJK 姓名启发式只覆盖 "姓名 + 大学/学院" 相邻上下文这一常见署名格式。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BLANK_TEXT_CHARS = 10

# 各竞赛内置页数上限; 未登记的竞赛跳过页数检查仅提示
COMPETITION_PAGE_LIMITS: dict[str, int] = {"mcm": 25}

# 图表标题前缀: 行首锚定, 防 "如图 1 所示" 这类正文引用误报
CAPTION_PREFIX_RE = re.compile(
    r"^\s*((?:图\s?\d+|表\s?\d+|Figure\s?\d+|Fig\.\s?\d+|Table\s?\d+))"
    r"\s*[:：.]?",
    re.MULTILINE,
)


def caption_key(prefix: str) -> str:
    """把图表题前缀规范化为 (类型, 编号) key: 中英文统一。

    "图 1" / "Figure 1" / "Fig.1" → "figure:1"; "表 1" / "Table 1" → "table:1"。
    编号去前导零, 防止 "图 01" 与 "图 1" 漏判。
    """
    text = prefix.strip()
    number = str(int(re.search(r"\d+", text).group()))
    if text.startswith("图") or text.lower().startswith(("figure", "fig.")):
        return f"figure:{number}"
    return f"table:{number}"

# 元数据中的工具词白名单（小写子串匹配）: 这些 Creator/Producer 不是人名
TOOL_WHITELIST = (
    "latex", "tex live", "miktex", "pdftex", "xelatex", "lualatex", "bibtex",
    "biber", "matplotlib", "python", "numpy", "scipy", "zotero", "mendeley",
    "microsoft", "ms word", "office", "wps", "adobe", "acrobat", "ghostscript",
    "gpl", "pandoc", "overleaf", "kile", "texmaker", "pages", "quartz",
    "preview", "mac os", "cairo", "reportlab", "pypdf", "skia", "chrome",
    "edge", "firefox", "webkit", "openoffice", "libreoffice", "kingsoft",
)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_CN_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
# CJK 姓名启发式: 2-4 个连续汉字 + 分隔符 + 含"大学/学院"的校名片段
CJK_NAME_CONTEXT_RE = re.compile(
    r"([\u4e00-\u9fa5]{2,4})[ \t,，、;；]+[\u4e00-\u9fa5]{2,12}?(?:大学|学院)"
)
# 姓名标记词: "姓名: 张三" / "指导教师：李四"
NAME_MARKER_RE = re.compile(
    r"(?:姓名|作者|指导教师|联系人|队员|队长|参赛队员|成员)[：:\s]{0,3}"
    r"([\u4e00-\u9fa5]{2,4})(?![\u4e00-\u9fa5])"
)
# 元数据人名模式: 2 个及以上相邻的 "大写开头英文词"（如 Zhang San）
LATIN_NAME_RE = re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b")

# 常见非人名汉字组合（姓名启发式误报兜底）
CJK_NAME_BLACKLIST = {"我们", "本文", "队员", "作者", "指导", "教师", "同学", "全文", "附录"}


class Finding:
    """一条检查结果。level 取 'ok' / 'info' / 'error'。"""

    def __init__(self, level: str, message: str) -> None:
        self.level = level
        self.message = message

    @property
    def mark(self) -> str:
        return {"ok": "✅", "info": "⚠️ ", "error": "❌"}[self.level]


def _metadata_name_hits(reader) -> list[str]:
    """扫 PDF 元数据（Author/Creator/Producer）, 返回疑似人名/单位的片段。"""
    hits: list[str] = []
    meta = reader.metadata or {}
    fields: dict[str, str] = {}
    for key in ("Author", "Creator", "Producer"):
        try:
            value = meta.get(f"/{key}")
        except Exception:
            value = None
        if not value:
            value = getattr(meta, key.lower(), None)
        if value and str(value).strip():
            fields[key] = str(value).strip()
    for key, text in fields.items():
        lowered = text.lower()
        if any(tool in lowered for tool in TOOL_WHITELIST):
            continue
        if re.search(r"[\u4e00-\u9fa5]", text):
            hits.append(f"{key}='{text[:40]}' 含中文（疑似真实姓名/单位）")
            continue
        for match in LATIN_NAME_RE.finditer(text):
            hits.append(f"{key}='{text[:40]}' 含人名模式 '{match.group()}'")
    return hits


def _page1_name_hits(text: str) -> list[str]:
    """第 1 页正文匿名扫描, 返回疑似泄密片段。"""
    hits: list[str] = []
    for m in EMAIL_RE.finditer(text):
        hits.append(f"邮箱 {m.group()}")
    for m in PHONE_CN_RE.finditer(text):
        hits.append(f"手机号 {m.group()}")
    for m in CJK_NAME_CONTEXT_RE.finditer(text):
        if m.group(1) not in CJK_NAME_BLACKLIST:
            snippet = m.group(0)[:20]
            hits.append(f"疑似姓名+学校 '{snippet}'（启发式, 请人工确认）")
    for m in NAME_MARKER_RE.finditer(text):
        if m.group(1) not in CJK_NAME_BLACKLIST:
            hits.append(f"姓名标记词后跟 '{m.group(1)}'（启发式, 请人工确认）")
    return hits


def check_pdf(pdf_path: Path, max_pages: int | None, anonymous: bool,
              competition: str | None) -> tuple[list[Finding], bool]:
    """执行四类检查, 返回 (结果列表, 是否致命失败)。"""
    findings: list[Finding] = []

    # ① 页数: 上限优先级 --max-pages > --competition 内置默认
    if max_pages is None and competition:
        max_pages = COMPETITION_PAGE_LIMITS.get(competition.lower())

    import_result = _import_pypdf(findings)
    if not import_result:
        return findings, False

    try:
        reader, page_count = import_result(pdf_path)
    except Exception as exc:
        findings.append(Finding("error", f"PDF 无法解析: {exc}"))
        return findings, True

    if max_pages is not None:
        if page_count > max_pages:
            findings.append(
                Finding("error", f"页数超限: {page_count} 页 > 上限 {max_pages} 页")
            )
        else:
            findings.append(Finding("ok", f"页数合规: {page_count}/{max_pages} 页"))
    else:
        if competition and competition.lower() not in COMPETITION_PAGE_LIMITS:
            findings.append(
                Finding(
                    "info",
                    f"竞赛 '{competition}' 无内置页数上限, 跳过页数检查"
                    f"（可用 --max-pages 手动指定）",
                )
            )
        else:
            findings.append(Finding("info", "未指定页数上限, 跳过页数检查"))

    # ② 重复图表标题前缀
    caption_counter: dict[str, list[int]] = {}
    page_texts: list[str] = []
    for idx, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        page_texts.append(text)
        for m in CAPTION_PREFIX_RE.finditer(text):
            key = caption_key(m.group(1))
            caption_counter.setdefault(key, []).append(idx + 1)
    duplicates = {k: pages for k, pages in caption_counter.items() if len(pages) > 1}
    if duplicates:
        for key, pages in sorted(duplicates.items()):
            findings.append(
                Finding("error", f"图表标题前缀重复: '{key}' 出现 {len(pages)} 次（第 {pages} 页）")
            )
    else:
        findings.append(
            Finding(
                "ok",
                f"图表标题前缀无重复（共扫到 {len(caption_counter)} 个编号前缀）",
            )
        )

    # ③ 匿名扫描
    if anonymous:
        meta_hits = _metadata_name_hits(reader)
        for hit in meta_hits:
            findings.append(Finding("error", f"元数据疑似泄密: {hit}"))
        if not meta_hits:
            findings.append(Finding("ok", "元数据未检出人名模式"))
        body_hits = _page1_name_hits(page_texts[0]) if page_texts else []
        for hit in body_hits:
            findings.append(Finding("error", f"第 1 页疑似泄密: {hit}"))
        if not body_hits:
            findings.append(Finding("ok", "第 1 页未检出邮箱/手机号/姓名模式"))
    else:
        findings.append(Finding("info", "未启用 --anonymous, 跳过匿名扫描"))

    # ④ 空白页
    blank_pages = [i + 1 for i, t in enumerate(page_texts) if len(t.strip()) < BLANK_TEXT_CHARS]
    if blank_pages:
        findings.append(
            Finding("info", f"疑似空白页（文本 < {BLANK_TEXT_CHARS} 字符）: 第 {blank_pages} 页, 请人工确认")
        )
    else:
        findings.append(Finding("ok", f"无空白页（{page_count} 页全部有文本层）"))

    return findings, False


def _import_pypdf(findings: list[Finding]):
    """惰性导入 pypdf; 缺失时降级记 ⚠️ 并返回 None。"""
    try:
        from pypdf import PdfReader
    except ImportError:
        findings.append(
            Finding("info", "未安装 pypdf, 页数/重复标题/空白页检查降级跳过（pip install pypdf 后可用）")
        )
        return None

    def open_pdf(path: Path):
        reader = PdfReader(str(path))
        return reader, len(reader.pages)

    return open_pdf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="渲染后 PDF 终检: 页数/重复图表编号/匿名泄密/空白页"
    )
    parser.add_argument("pdf", help="待检 PDF 路径")
    parser.add_argument("--max-pages", type=int, default=None, help="页数上限")
    parser.add_argument("--anonymous", action="store_true", help="启用匿名泄密扫描")
    parser.add_argument("--competition", default=None, help="竞赛名（mcm 内置 25 页上限）")
    args = parser.parse_args(argv)

    pdf_path = Path(args.pdf).expanduser()
    if not pdf_path.exists():
        print(f"PDF 不存在: {pdf_path}")
        return 2

    findings, fatal = check_pdf(pdf_path, args.max_pages, args.anonymous, args.competition)

    print("=" * 60)
    print(f"pdf_qa 终检报告: {pdf_path.name}")
    print("=" * 60)
    for f in findings:
        print(f"  {f.mark} {f.message}")
    errors = [f for f in findings if f.level == "error"]
    print("-" * 60)
    print(f"合计: {len(errors)} 项 ❌, {sum(1 for f in findings if f.level == 'info')} 项 ⚠️")
    if fatal:
        return 2
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
