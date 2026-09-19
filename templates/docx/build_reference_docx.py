"""build_reference_docx.py — 生成 docx 终稿通道的样式基准 reference.docx

以 pandoc 默认 reference.docx 为底 (pandoc --print-default-data-file 二进制捕获,
不经 shell 重定向避免 Windows 文本模式损坏), 用 python-docx 改成中文竞赛版式:

- 页面: A4, 四边距 2.5cm; 页脚居中页码 (PAGE 域, 宋体/Times 小五);
- Normal/正文: 宋体 + 西文 Times New Roman, 小四 (12pt), 行距 1.3,
  首行缩进 2 字符 (firstLineChars=200, Word 按字号自适应), 两端对齐;
- Heading 1/2/3: 黑体黑色加粗, 三号/四号/小四 (16/14/12pt), H1 居中、H2/H3 左对齐,
  并显式清掉首行缩进 (标题不继承正文缩进);
- Table Caption / Image Caption (含父级 Caption): 宋体小五 (9pt) 居中不缩进;
- Compact (紧凑列表/表格单元格): 清首行缩进, 防列表项被正文缩进带歪。

默认档 (样式源头合规, 呈现层后处理只兜底):
- B5① Table 样式表级三线: 上/下边框 single 1.5pt (w:sz=12 八分之一点制),
  insideH/insideV/left/right 显式 none, 无底纹 (shd=clear)。表头行下边框属
  行级直接格式, pandoc 不写, 留给导出链呈现层后处理; 样式侧只做表级;
- B5⑤ Compact: 段前/段后 0 + 单倍行距 (240/auto) + 首行缩进 0 —— 单元格段落
  不再继承 BodyText 的 1.8pt 段距与 Normal 的 1.3 倍行距;
- B3 Normal/Body Text 段后归零 (docDefaults 默认 10pt、Body Text 9pt 段后曾把
  摘要顶出第 1 页); Normal 的首行缩进 2 字符与 1.3 行距保持不变 (正文仍需)。

--loose: 保留旧行为 (B3/B5①/B5⑤ 一概不叠加), 供对照与回退。

幂等: 重复运行重新生成, 覆盖同目录 reference.docx。pandoc / python-docx 缺失时
报错退出码 2。产物随脚本一并入库; 再生成仅需重跑本脚本。

用法:
    python templates/docx/build_reference_docx.py            # 默认档, 生成脚本旁 reference.docx
    python templates/docx/build_reference_docx.py --loose    # 旧宽松档
    python templates/docx/build_reference_docx.py -o x.docx  # 指定输出路径

退出码: 0 成功; 2 pandoc/python-docx 不可用或写出失败。
"""

import argparse
import io
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor

PANDOC_INSTALL_HINT = ("pandoc 不可用; 请安装 pandoc 后重试: "
                       "https://pandoc.org/installing.html 或 winget install pandoc")

# 中文字号: 小四=12pt, 三号=16pt, 四号=14pt, 小五=9pt
BODY_SIZE = Pt(12)
HEADING_SIZES = {1: Pt(16), 2: Pt(14), 3: Pt(12)}
CAPTION_SIZE = Pt(9)
BLACK = RGBColor(0, 0, 0)


def _set_style_fonts(style, east_asian: str, latin: str) -> None:
    """设置样式字体: w:rFonts 显式指定 eastAsia/ascii/hAnsi, 剥掉主题字体属性。

    pandoc 默认 Heading 样式用 asciiTheme/majorEastAsia 主题字体, 不剥掉时
    显式字体不生效 (Word 优先解析主题属性)。
    """
    style.font.name = latin  # 写 w:ascii + w:hAnsi
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    for attr in ("asciiTheme", "eastAsiaTheme", "hAnsiTheme", "cstheme"):
        rfonts.attrib.pop(qn(f"w:{attr}"), None)
    rfonts.set(qn("w:eastAsia"), east_asian)


def _find_style(doc, name: str):
    """按样式名查找, 找不到再按 styleId 匹配 (pandoc 的 "Caption" 内部名是 "caption",
    python-docx 名称通道未命中时会在内部回退 id 匹配并打弃用告警, 此处显式吞掉)。"""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        try:
            return doc.styles[name]
        except KeyError:
            pass
    for style in doc.styles:
        if style.style_id == name:
            return style
    raise KeyError(name)


def _set_first_line_chars(style, chars: int, twips: int) -> None:
    """首行缩进按"字符"设 (w:firstLineChars), 兼容性回退值 w:firstLine (缇)。

    200 = 2 字符; python-docx 只支持 firstLine (绝对量), firstLineChars 须 XML 直写,
    Word 实际按 firstLineChars 随字号自适应。
    """
    ppr = style.element.get_or_add_pPr()
    ind = ppr.find(qn("w:ind"))
    if ind is None:
        ind = ppr.makeelement(qn("w:ind"), {})
        ppr.append(ind)
    ind.set(qn("w:firstLineChars"), str(chars))
    ind.set(qn("w:firstLine"), str(twips))


# tblPr 子元素严格序列顺序中, 必须排在 w:tblBorders / w:shd 之后的标签
# (CT_TblPr: tblInd < tblBorders < shd < tblLayout < tblCellMar < tblLook)
_AFTER_TBL_BORDERS = ("w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook",
                      "w:tblCaption", "w:tblDescription")
_AFTER_TBL_SHD = ("w:tblLayout", "w:tblCellMar", "w:tblLook",
                  "w:tblCaption", "w:tblDescription")


def _insert_tblpr_child(tbl_pr, child, after_tags) -> None:
    """把 child 按 CT_TblPr 序列顺序插进 tblPr: 插到第一个属于 after_tags 的
    子元素之前, 没有则追加到末尾。乱序会被严格 OOXML 校验器拒收。"""
    tails = {qn(t) for t in after_tags}
    for existing in tbl_pr:
        if existing.tag in tails:
            existing.addprevious(child)
            return
    tbl_pr.append(child)


def _set_table_style_three_line(style) -> None:
    """Table 样式表级三线 (B5①): 上/下 single 1.5pt (w:sz=12, 八分之一点制),
    insideH/insideV/left/right 显式 none, 无底纹 (shd=clear)。

    python-docx 的样式 API 不暴露表级 tblBorders, 只能直操 styles 元素 XML
    (lxml)。表头行下边框属行级直接格式, pandoc 不写, 留给导出链呈现层后处理;
    本函数只做表级。幂等: 先剥掉已有 tblBorders/shd 再写。
    """
    tbl_pr = style.element.find(qn("w:tblPr"))
    if tbl_pr is None:
        tbl_pr = style.element.makeelement(qn("w:tblPr"), {})
        style.element.append(tbl_pr)
    for tag in ("w:tblBorders", "w:shd"):
        for el in tbl_pr.findall(qn(tag)):
            tbl_pr.remove(el)
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}'
        '><w:top w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
        '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
        '<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        "</w:tblBorders>")
    _insert_tblpr_child(tbl_pr, borders, _AFTER_TBL_BORDERS)
    shd = parse_xml(f'<w:shd {nsdecls("w")}'
                    ' w:val="clear" w:color="auto" w:fill="auto"/>')
    _insert_tblpr_child(tbl_pr, shd, _AFTER_TBL_SHD)


def _page_number_run_xml(paragraph) -> None:
    """向段落追加居中 PAGE 域 (fldChar begin/instrText/separate/end)。

    python-docx 无域 API, 按 WordprocessingML 手写; separate 后的占位文本 "1"
    在 Word 打开/打印时被真实页码刷新。
    """
    r_begin = paragraph.add_run()
    r_begin._r.append(paragraph._p.makeelement(qn("w:fldChar"),
                                               {qn("w:fldCharType"): "begin"}))
    r_instr = paragraph.add_run()
    instr = paragraph._p.makeelement(qn("w:instrText"), {})
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    r_instr._r.append(instr)
    r_sep = paragraph.add_run()
    r_sep._r.append(paragraph._p.makeelement(qn("w:fldChar"),
                                             {qn("w:fldCharType"): "separate"}))
    r_text = paragraph.add_run("1")
    r_end = paragraph.add_run()
    r_end._r.append(paragraph._p.makeelement(qn("w:fldChar"),
                                             {qn("w:fldCharType"): "end"}))
    for run in (r_text,):
        run.font.size = CAPTION_SIZE


def fetch_pandoc_reference() -> bytes:
    """二进制捕获 pandoc 默认 reference.docx (capture_output 避免 shell 重定位损坏)。"""
    try:
        r = subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"],
                           capture_output=True)
    except FileNotFoundError:
        print(f"[FAIL] {PANDOC_INSTALL_HINT}")
        raise SystemExit(2)
    if r.returncode != 0 or not r.stdout.startswith(b"PK"):
        print(f"[FAIL] pandoc 未能输出默认 reference.docx: "
              f"{r.stderr.decode('utf-8', 'replace').strip()[:200]}")
        raise SystemExit(2)
    return r.stdout


def build_reference_docx(loose: bool = False) -> Document:
    """在 pandoc 默认 reference.docx 上叠加中文竞赛版式, 返回内存中的 Document。

    loose=True 走旧行为: 不叠加 B3 (Normal/Body Text 段后归零)、B5① (Table
    表级三线)、B5⑤ (Compact 零段距单倍行距), 供对照与回退。
    """
    doc = Document(io.BytesIO(fetch_pandoc_reference()))

    # ---- 页面: A4 + 四边 2.5cm ----
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    # ---- 页脚居中页码 ----
    footer = section.footer
    footer.is_linked_to_previous = False
    para = footer.paragraphs[0]
    para.text = ""
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _page_number_run_xml(para)

    # ---- Normal: 宋体小四 + Times, 1.3 行距, 首行缩进 2 字符, 两端对齐 ----
    normal = _find_style(doc, "Normal")
    _set_style_fonts(normal, "宋体", "Times New Roman")
    normal.font.size = BODY_SIZE
    normal.paragraph_format.line_spacing = 1.3
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    _set_first_line_chars(normal, 200, 480)  # 2 字符 ≈ 24pt = 480 缇
    if not loose:
        # B3: pandoc docDefaults 默认段后 200 缇 (10pt), 显式归零
        # (中文正文靠首行缩进分段, 不靠段后空距; 首行缩进/1.3 行距保持不变)
        normal.paragraph_format.space_after = Pt(0)

    # ---- Body Text (pandoc 正文段落样式, First Paragraph 亦 basedOn 它):
    #      B3 默认档段后归零 —— 原 9pt 段后曾把 8 段式摘要顶出第 1 页 ----
    if not loose:
        body_text = _find_style(doc, "Body Text")
        body_text.paragraph_format.space_after = Pt(0)

    # ---- Heading 1/2/3: 黑体黑色加粗, 16/14/12pt; H1 居中; 不带正文缩进 ----
    for level, size in HEADING_SIZES.items():
        style = _find_style(doc, f"Heading {level}")
        _set_style_fonts(style, "黑体", "黑体")  # 编号数字也用黑体, 与中文标题一致
        style.font.size = size
        style.font.bold = True
        style.font.color.rgb = BLACK  # 去掉 pandoc 默认蓝
        style.paragraph_format.first_line_indent = Pt(0)
        _set_first_line_chars(style, 0, 0)
        style.paragraph_format.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT)

    # ---- 题注: 宋体小五黑色居中不缩进不斜体 (Caption 是 Table/Image Caption
    #      的父样式, pandoc 默认带 <w:i/> 斜体, 子样式须显式覆盖) ----
    for name in ("Caption", "Table Caption", "Image Caption"):
        style = _find_style(doc, name)
        _set_style_fonts(style, "宋体", "Times New Roman")
        style.font.size = CAPTION_SIZE
        style.font.bold = False
        style.font.italic = False
        style.font.color.rgb = BLACK
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        style.paragraph_format.first_line_indent = Pt(0)
        _set_first_line_chars(style, 0, 0)

    # ---- Compact (紧凑列表/表格单元格): 清首行缩进; 默认档再加 B5⑤
    #      零段距 + 单倍行距 (单元格段落不再继承 BodyText 的 1.8pt 段距
    #      与 Normal 的 1.3 倍行距) ----
    compact = _find_style(doc, "Compact")
    compact.paragraph_format.first_line_indent = Pt(0)
    _set_first_line_chars(compact, 0, 0)
    if not loose:
        compact.paragraph_format.space_before = Pt(0)
        compact.paragraph_format.space_after = Pt(0)
        compact.paragraph_format.line_spacing = 1.0  # 240/auto 单倍

    # ---- Table 样式 (pandoc 给数据表挂的): 默认档表级三线 (B5①);
    #      表头行下边框属行级直接格式, 留给导出链呈现层后处理 ----
    if not loose:
        _set_table_style_three_line(_find_style(doc, "Table"))

    return doc


def _describe_doc(doc: Document) -> str:
    """回读内存文档各关键样式属性, 组装生成摘要 (供人眼核对 B3/B5①/B5⑤)。"""

    def pt(value):
        return "继承" if value is None else f"{value.pt:g}pt"

    def spacing_line(style):
        ppr = style.element.find(qn("w:pPr"))
        spacing = ppr.find(qn("w:spacing")) if ppr is not None else None
        if spacing is None or spacing.get(qn("w:line")) is None:
            return "继承"
        rule = spacing.get(qn("w:lineRule")) or "auto"
        return f"{int(spacing.get(qn('w:line'))) / 240:g}x({rule})"

    def para_desc(style):
        pf = style.paragraph_format
        return (f"段前 {pt(pf.space_before)} / 段后 {pt(pf.space_after)} / "
                f"行距 {spacing_line(style)}")

    def first_line_chars(style):
        ppr = style.element.find(qn("w:pPr"))
        ind = ppr.find(qn("w:ind")) if ppr is not None else None
        if ind is None or ind.get(qn("w:firstLineChars")) is None:
            return "继承"
        return f"{ind.get(qn('w:firstLineChars'))}字符"

    def table_desc():
        table = _find_style(doc, "Table")
        tbl_pr = table.element.find(qn("w:tblPr"))
        borders = tbl_pr.find(qn("w:tblBorders")) if tbl_pr is not None else None
        if borders is None:
            return "表级无边框定义 (--loose 旧档)"
        parts = []
        for tag in ("top", "bottom", "left", "right", "insideH", "insideV"):
            el = borders.find(qn(f"w:{tag}"))
            if el is None:
                parts.append(f"{tag}=未定义")
                continue
            sz = el.get(qn("w:sz"))
            parts.append(f"{tag}={el.get(qn('w:val'))}" + (f"/sz={sz}" if sz else ""))
        shd = tbl_pr.find(qn("w:shd"))
        shade = "clear(无底纹)" if shd is not None and shd.get(qn("w:val")) == "clear" \
            else (shd.get(qn("w:val")) if shd is not None else "未定义")
        return f"{', '.join(parts)}; 底纹 {shade}"

    normal = _find_style(doc, "Normal")
    body_text = _find_style(doc, "Body Text")
    compact = _find_style(doc, "Compact")
    return (
        "     [B3 段后归零] Normal: " + para_desc(normal) + "\n"
        "                    Body Text: " + para_desc(body_text) + "\n"
        "     [B5① 表级三线] Table: " + table_desc() + "\n"
        "     [B5⑤ 零段距单倍] Compact: " + para_desc(compact)
        + f" / 首行 {first_line_chars(compact)}"
    )


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台中文兜底
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="生成 docx 终稿通道的样式基准 reference.docx (pandoc 默认底 + 中文竞赛版式)")
    parser.add_argument("-o", "--output", type=Path,
                        default=Path(__file__).with_name("reference.docx"),
                        help="输出路径 (默认脚本同目录 reference.docx)")
    parser.add_argument("--loose", action="store_true",
                        help="旧宽松档: 不叠加 B3/B5①/B5⑤ 样式源头修复 (段后/三线/Compact 段距)")
    args = parser.parse_args(argv)

    doc = build_reference_docx(loose=args.loose)
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        doc.save(args.output)
    except OSError as e:
        print(f"[FAIL] 写出 {args.output} 失败: {e}")
        return 2
    tier = "loose 旧档" if args.loose else "默认档 (B3/B5①/B5⑤ 样式源头合规)"
    print(f"[OK] 已生成样式基准 ({tier}): {args.output.resolve()} "
          f"({args.output.stat().st_size} 字节)")
    print("     A4/2.5cm | 宋体小四+Times/1.3 行距/首行 2 字符 | 黑体 H1-3 (16/14/12pt) | "
          "题注宋体 9pt 黑色居中非斜体 | 页脚居中页码")
    print(_describe_doc(doc).rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
