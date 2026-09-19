# -*- coding: utf-8 -*-
r"""渲染后 PDF 终检: 提交前对成品 PDF 做五类机械检查。

  ① 页数超限      pypdf 读页数; --max-pages 或按 --competition 默认值
                   （mcm=25 页; 其他竞赛无内置默认, 跳过并提示）
  ② 重复图表标题  行首锚定的 "图 1：/表 2:/Figure 3:/Fig. 4/Table 5" 前缀
                   做题注形态判定后计数（T-07 修复: 无 :：. 分隔符且命中词后紧跟
                   接续词判为正文引用跳过; 同编号仅当行内后续文本完全相同才算重复）;
                   编号 key 跨语言统一: 图 1/Figure 1/Fig.1 → figure:1,
                   表 1/Table 1 → table:1（中英混排重复同样检出）
  ③ 匿名扫描      --anonymous 时: PDF 元数据（Author/Creator/Producer）含
                   人名模式则报; 第 1 页正文扫邮箱/11 位手机号/CJK 姓名启发式
                   （2-4 个连续汉字 + 分隔符 + "大学/学院" 上下文;
                   LaTeX/matplotlib 等工具词白名单排除）
  ④ 空白页检测    pypdf 提取每页文本 < 10 字符判空白页, 报告页码
  ⑤ 文本层工件    --artifact-scan 默认开启（--no-artifact-scan 关闭）: 用
                   PyMuPDF 逐页取文本层, 检索渲染事故指纹——md 标题残留（行首
                   ## 或行内 " ## "）、管道表残行（|:---| 形态）、LaTeX 命令
                   残骸（" imes "/" rac "/" qquad " 碎片、数字黏连 imes 与字面
                   \times/\frac/\qquad）、HTML 片段（<span/<div/<br）、控制字符
                   （TAB/孤立 CR）、引用失败占位（错误!未找到引用源/？？/[?]）、
                   行首 $ 且该行 $ ≥2 次的未渲染数学; 每条命中报页码+模式+前后
                   各 20 字符上下文（A1: 2026 国赛 A 题三起构建事故的机器拦截）

用法:
    python scripts/pdf_qa.py paper.pdf --max-pages 25
    python scripts/pdf_qa.py paper.pdf --anonymous --competition mcm
    python scripts/pdf_qa.py paper.pdf --no-artifact-scan
    python scripts/pdf_qa.py paper.pdf --page-map          # 页码→首行关键词/图表编号表
                                                          # （视觉验收派发用, 见 stage_09 Step 2 / 清单 C3）

报告分级 ✅ 通过 / ⚠️ 提示 / ❌ 违例; 存在 ❌ 时退出码 1。

退出码:
    0  无 ❌（⚠️ 不影响）
    1  存在 ❌ 违例, 或 pypdf 缺失导致关键检查无法执行
    2  PDF 不存在 / 无法解析等致命错误

已知限制:
    - 扫描版 PDF（无文本层）会把全部页判为空白页, 请人工复核;
    - CJK 姓名启发式只覆盖 "姓名 + 大学/学院" 相邻上下文这一常见署名格式;
    - 工件扫描的 " imes " 类碎片模式要求前后空格包裹; TAB 在 fitz 提取中
      可能被归一为空格, 届时由数字黏连 imes 变体与控制字符检查兜底。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BLANK_TEXT_CHARS = 10

# 各竞赛内置页数上限; 未登记的竞赛跳过页数检查仅提示
COMPETITION_PAGE_LIMITS: dict[str, int] = {"mcm": 25}

# 图表标题前缀: 行首锚定, 防 "如图 1 所示" 这类正文引用误报。
# 捕获组: 1=前缀, 2=分隔符(:：.), 3=行内后续文本 (供题注形态判定)
CAPTION_PREFIX_RE = re.compile(
    r"^\s*((?:图\s?\d+|表\s?\d+|Figure\s?\d+|Fig\.\s?\d+|Table\s?\d+))"
    r"\s*([:：.]?)[ \t]*(.*)$",
    re.MULTILINE,
)

# T-07 修复: 中文换行会把正文引用顶到行首 (如 "表 3 与表 4 给出题面要求的…")。
# 行首命中后做题注形态判定:
#   ① 无 :：. 分隔符且命中词后紧跟接续词 → 正文引用, 跳过;
#   ② 同一编号仅当行内后续文本完全相同才算重复 (真重复题注逐字一致)。
CAPTION_CONTINUATION_RE = re.compile(r"^(与|显示|给出|中|如|见|由|为|是|表明|可知|所示|的)")


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


def _is_caption_form(match: re.Match) -> bool:
    """行首命中是否题注形态 (T-07): 无 :：. 分隔符且后续以接续词开头 → 正文引用。

    已知取舍 (复审 P2-1): 无分隔符且以接续词开头的合法题注 (如"图 3 显示…曲线")
    会被判为正文引用而漏检其重复——本 skill 的图题规范 (cn_presentation_spec §7,
    "图 N：说明"带分隔符) 下不受影响; 仅当论文不用分隔符风格时该检查对此类题注失效。
    """
    if match.group(2):  # 有 :：. 分隔符 → 题注形态
        return True
    return not CAPTION_CONTINUATION_RE.match(match.group(3).lstrip())


def scan_captions(page_texts: list[str]) -> tuple[dict[str, list[int]], dict[tuple[str, str], list[int]]]:
    """扫全部页文本的行首题注形态命中。

    返回 (编号计数, (编号 key, 后续文本) → 页码列表)。后续文本取命中行内
    剩余部分并去空白后比较: 同编号同文本出现多次才构成重复题注。
    """
    caption_counter: dict[str, list[int]] = {}
    caption_groups: dict[tuple[str, str], list[int]] = {}
    for idx, text in enumerate(page_texts):
        for m in CAPTION_PREFIX_RE.finditer(text):
            if not _is_caption_form(m):
                continue
            key = caption_key(m.group(1))
            rest = re.sub(r"\s+", "", m.group(3))
            caption_counter.setdefault(key, []).append(idx + 1)
            caption_groups.setdefault((key, rest), []).append(idx + 1)
    return caption_counter, caption_groups

# ⑤ 文本层工件指纹 (A1): 每项 (模式名, 正则), 对 fitz 提取的逐页文本全文检索;
# "未渲染数学定界" 在 scan_artifacts 里按行判定, 不在本表。
#   - md 标题残留: pandoc 未解析的 "## 标题" 被当正文印出（行首 ## 含 ### 等更长
#     前缀; 行内 " ## " 覆盖前有空白被并行的形态）;
#   - 管道表残留: 表格分隔行 "|:---:|:---:|" 形态（题注与表格间缺空行时
#     pandoc 整块不解析, 2026 国赛 A 题事故 ①）;
#   - LaTeX 命令残骸: " imes "/" rac "/" qquad " 为反斜杠被写坏后的空格包裹
#     碎片; (?<=\d)imes / (?<=\d[ \t])imes 覆盖事故 ② 的 "9.1imes10-5" 及其
#     TAB 被归一为空格的变体; 字面 \times/\frac/\qquad 为未编译命令;
#   - HTML 残留: 原样印出的 <span/<div/<br 片段;
#   - 控制字符: TAB/孤立 CR 是 md 卫生事故在文本层的指纹;
#   - 引用失败占位: Word 交叉引用断链的 "错误!未找到引用源"（含全角 ！ 变体）、
#     全角 ？？ 与 [?]。
ARTIFACT_CONTEXT_CHARS = 20   # 命中上下文: 前后各取的字符数
ARTIFACT_MAX_FINDINGS = 40    # 单次扫描最多逐条输出的命中数, 防整页源码事故刷屏

ARTIFACT_TEXT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("md标题残留", re.compile(r"(?m)^##| ## ")),
    ("管道表残留", re.compile(r"\|[:\-|]{3,}")),
    ("LaTeX命令残骸",
     re.compile(r" imes | rac | qquad |(?<=\d[ \t])imes|(?<=\d)imes|\\times|\\frac|\\qquad")),
    ("HTML残留", re.compile(r"<span|<div|<br")),
    ("控制字符", re.compile(r"\t|\r(?!\n)")),
    ("引用失败占位", re.compile(r"错误[!！]未找到引用源|？？|\[\?\]")),
]


def _artifact_context(text: str, start: int, end: int) -> str:
    """取命中片段前后各 ARTIFACT_CONTEXT_CHARS 字符; 控制字符转义为可见形态。"""
    left = max(0, start - ARTIFACT_CONTEXT_CHARS)
    right = min(len(text), end + ARTIFACT_CONTEXT_CHARS)
    ctx = text[left:right].replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")
    lead = "…" if left > 0 else ""
    tail = "…" if right < len(text) else ""
    return f"{lead}{ctx}{tail}"


def scan_artifacts(page_texts: list[str]) -> list[tuple[int, str, str]]:
    """对每页文本层跑 7 类工件模式, 返回 (页码, 模式名, 上下文) 命中列表。

    前 6 类按 ARTIFACT_TEXT_PATTERNS 全文正则检索; "未渲染数学定界" 按行判定:
    行以 $ 开头且该行 $ 出现 ≥2 次（成对定界符未转公式对象的指纹）。
    """
    hits: list[tuple[int, str, str]] = []
    for idx, text in enumerate(page_texts):
        for name, pattern in ARTIFACT_TEXT_PATTERNS:
            for m in pattern.finditer(text):
                hits.append((idx + 1, name, _artifact_context(text, m.start(), m.end())))
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("$") and stripped.count("$") >= 2:
                snippet = stripped[:ARTIFACT_CONTEXT_CHARS * 2]
                hits.append((idx + 1, "未渲染数学定界",
                             snippet + ("…" if len(stripped) > len(snippet) else "")))
    return hits


def _fitz_page_texts(pdf_path: Path, findings: list[Finding]) -> list[str] | None:
    """PyMuPDF 逐页取文本层; 未安装/读取失败时记 ⚠️ 并返回 None (调用方降级)。

    工件扫描用 fitz 而非 pypdf: fitz 保留行结构与原始空白, 对控制字符和
    行首锚定模式更忠实。
    """
    try:
        import fitz  # pymupdf
    except ImportError:
        findings.append(
            Finding("info", "未安装 pymupdf, 文本层工件扫描降级跳过（pip install pymupdf 后可用）")
        )
        return None
    try:
        with fitz.open(str(pdf_path)) as doc:
            return [page.get_text() or "" for page in doc]
    except Exception as exc:
        findings.append(Finding("info", f"pymupdf 读取文本层失败, 工件扫描降级跳过: {exc}"))
        return None


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
              competition: str | None, artifact_scan: bool = True
              ) -> tuple[list[Finding], bool]:
    """执行五类检查, 返回 (结果列表, 是否致命失败)。"""
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

    # ② 重复图表标题前缀 (题注形态判定, 见 scan_captions)
    page_texts: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        page_texts.append(text)
    caption_counter, caption_groups = scan_captions(page_texts)
    duplicates = {k: pages for k, pages in caption_groups.items() if len(pages) > 1}
    if duplicates:
        for (key, rest), pages in sorted(duplicates.items()):
            shown = rest[:16] + "…" if len(rest) > 16 else rest
            findings.append(
                Finding("error", f"图表标题重复: '{key}' 题注“{shown}”出现 {len(pages)} 次（第 {pages} 页）")
            )
    else:
        findings.append(
            Finding(
                "ok",
                f"图表标题无重复（共扫到 {len(caption_counter)} 个编号题注）",
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

    # ⑤ 文本层工件扫描 (A1): fitz 取文本层, 检索渲染事故指纹
    if artifact_scan:
        fitz_texts = _fitz_page_texts(pdf_path, findings)
        if fitz_texts is not None:
            artifact_hits = scan_artifacts(fitz_texts)
            for page_no, name, context in artifact_hits[:ARTIFACT_MAX_FINDINGS]:
                findings.append(
                    Finding("error", f"第 {page_no} 页 文本工件[{name}]: {context}")
                )
            if len(artifact_hits) > ARTIFACT_MAX_FINDINGS:
                findings.append(
                    Finding(
                        "error",
                        f"文本工件命中过多: 共 {len(artifact_hits)} 处, "
                        f"仅逐条列出前 {ARTIFACT_MAX_FINDINGS} 处",
                    )
                )
            if not artifact_hits:
                findings.append(
                    Finding("ok", f"文本层工件扫描通过（{len(fitz_texts)} 页 × 7 类模式）")
                )
    else:
        findings.append(Finding("info", "已用 --no-artifact-scan 关闭文本层工件扫描"))

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


def build_page_map(page_texts: list[str], max_keywords: int = 6) -> list[str]:
    """从 PDF 文本层提取"页码 → 首行关键词"映射表（C3, v3.1.0）。

    用途: 视觉验收（judge/逐页目检）派发前，把页码-内容对应关系以机器提取的
    形式随 prompt 一并给出——2026 国赛 A 题实测中手工维护的页码-内容映射错位
    一次（p35 实际是 AI 说明+附录），错位的映射表会让视觉结论整体失效。

    每页取: 首行非空行（截断 60 字符）+ 该页出现的图表编号（图 N / 表 N）。
    """
    sheet: list[str] = []
    for idx, text in enumerate(page_texts, 1):
        lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
        head = lines[0][:60] if lines else "(空白页)"
        extra = lines[1:1 + max_keywords]
        figs = re.findall(r"图\s*(\d+)", text or "")
        tabs = re.findall(r"表\s*(\d+)", text or "")
        marks: list[str] = []
        if figs:
            marks.append("图 " + "/".join(dict.fromkeys(figs))[:40])
        if tabs:
            marks.append("表 " + "/".join(dict.fromkeys(tabs))[:40])
        tail = ("  | " + " · ".join(extra)[:120]) if extra else ""
        mark = ("  [" + "; ".join(marks) + "]") if marks else ""
        sheet.append(f"p{idx:>3}: {head}{tail}{mark}")
    return sheet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="渲染后 PDF 终检: 页数/重复图表编号/匿名泄密/空白页/文本层工件"
    )
    parser.add_argument("pdf", help="待检 PDF 路径")
    parser.add_argument("--max-pages", type=int, default=None, help="页数上限")
    parser.add_argument("--anonymous", action="store_true", help="启用匿名泄密扫描")
    parser.add_argument("--competition", default=None, help="竞赛名（mcm 内置 25 页上限）")
    parser.add_argument("--artifact-scan", dest="artifact_scan", action="store_true",
                        default=True, help="启用文本层工件扫描（默认开启）")
    parser.add_argument("--no-artifact-scan", dest="artifact_scan", action="store_false",
                        help="关闭文本层工件扫描")
    parser.add_argument("--page-map", action="store_true",
                        help="只输出「页码 → 首行关键词/图表编号」映射表"
                             "（视觉验收派发用, C3）")
    args = parser.parse_args(argv)

    pdf_path = Path(args.pdf).expanduser()
    if not pdf_path.exists():
        print(f"PDF 不存在: {pdf_path}")
        return 2

    if args.page_map:
        findings: list[Finding] = []
        texts = _fitz_page_texts(pdf_path, findings)
        if texts is None:
            print("需要 pymupdf(fitz) 才能提取页码映射表: pip install pymupdf")
            return 2
        for line in build_page_map(texts):
            print(line)
        print(f"\n[page-map] 共 {len(texts)} 页; 派发视觉验收时随 prompt 附带本表, "
              f"并要求验收方按页码逐页回证")
        return 0

    findings, fatal = check_pdf(pdf_path, args.max_pages, args.anonymous, args.competition,
                                artifact_scan=args.artifact_scan)

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
