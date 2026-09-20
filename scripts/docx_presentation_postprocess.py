# -*- coding: utf-8 -*-
"""docx_presentation_postprocess.py — docx 呈现层统一后处理 (v3.1.0 新增)

合并 2026 国赛 A 题终稿实测验证过的两个工作区脚本 (docx_equation_postprocess.py +
docx_table_threeline.py), 六步一体化, 是 cn_presentation_spec §5.1/§5.6/§6.1/§6.2/§7.3
docx 链实现条目的唯一脚本源:

  Step A 数学字体正斜 (§5.6): **按 decision_log 政策执行**——政策 upright (全局
        正体) 时给所有 m:oMath 下的 m:r 注入/改写 m:rPr/m:sty val="p"; 政策
        conventional 或未登记时**保持输入一字不动并警告** (绝不把所有 math run
        刷成斜体——那会把用户/ pandoc 已写好的正体 sin、单位、算符一起改坏)。
        政策解析见 math_font_policy.py (显式键清单 + 冲突/非法一律警告不判定)。
  Step B 编号右顶格 (§5.1): body 直接子层含 m:oMathPara 的段落 (display 公式) →
        无边框三列表格 (空窄列｜公式居中｜编号右对齐普通文本)。pandoc 把编号
        "(N)" 留在 OMML 公式对象内部紧贴公式右端, 本步把它提出来。
        真编号判据 (H1): "(N)" 前必须存在幸存空白字符 (\\qquad 渲染产物,
        实证 U+2001×2 专属 run); f(1)/a+(2) 紧贴公式主体的括号不是编号,
        一字不动——防止静默改写数学内容。
        包裹表宽度 = **公式段所在节的版心** (pgSz.w − pgMar.left − pgMar.right
        − gutter), 逐节计算 (v3.1.0 修: 原写死 9072 twips 只对 A4+2.5cm 成立,
        多节/换页宽时编号右侧不顶格)。两个不假装能处理的边界: ① 节末段本身是
        公式段 → 跳过不包表 (搬进表格单元格会让 Word 拒绝打开该 docx) 并警告;
        ② 多栏节 (w:cols num>1 或列宽不等) → 宽度仍按单栏版心算, 发**明确未支持
        警告** (多栏每栏宽 = (版心−栏间距)/栏数, 本脚本不建模)。
  Step C 数据表三线 (§6.1): 跳过含 oMathPara 的表 (公式包裹表必须无边框)——
        上下 single sz=12 (1.5pt)、表头行单元格下边框 sz=6 (0.75pt)、
        insideH/insideV/left/right 一律 none、底纹清 auto。
  Step D 自适应+居中 (§6.2): tblW=5000 pct (撑满版心) + tblPr/jc=center +
        tblLayout=autofit (列宽随内容重分配, 修等宽布局把长文件名挤断行) +
        数据表各行 trPr/cantSplit (行禁拆, 防单元格内容被页界劈半)。
  Step E 单元格排版 (§6.2): 数据表内全部段落 spacing before/after=0 +
        line=240 auto (单倍行距) + ind 全零——直接格式覆盖 Compact/Normal 样式链。
        **单倍行距是本链既定口径 (用户明确要求), 不改成 1.3 倍等通用 Word 惯例。**
  Step E2 单元格对齐 (§6.2, v3.1.0 新增): 单元格段落 jc——短列居中 (数值与文字
        同规则), **长文本列整列左对齐** (列内任一单元格文本 ≥ CELL_LONG_TEXT_CHARS
        字符), 长文本列清单进报告供人在表注说明。与 Step D 的**表体居中**
        (tblPr/jc) 分开两步: 表体居中和单元格段落对齐是两件事。
  Step F 图与图注同页 (§7.3, E6): body 直接子层含图片的段落加 w:keepNext,
        防图注被页界与图劈开; 只处理图段, 不动表格内图片。

步间独立性 (v3.1.0 明确): A (字体) / B (公式编号) / C/D/E/E2 (表格) / F (图注)
是互相独立的操作——A 因政策缺席或跳过**不影响**其余各步照常执行; 各步统计独立
成行输出, 便于核对哪一步做了什么。Step E2 只写 jc, 不碰 C 写的三线边框与 E 写的
零缩进/零段距/单倍行距 (回归测试逐属性断言"保持")。

纪律 (逐条来自实测事故, 改动前读注释):
  - 幂等: Step B 只处理 body 直接子层段落 (已在表格内的天然跳过), 重复运行第二遍
    处理数为 0; Step A 重复注入前先查已有 m:sty; C/D/E/E2 直接格式覆盖写。
  - Step B 编号提取须跨 run 拼接 (pandoc 把 "(N)" 拆成 '('、'N'、')' 多个 m:t),
    删除按「待删字符数 = 总长 − 匹配起点」从尾回溯——曾误把"应保留数"当
    "待删数", 从尾反向删光公式正文 (渲染验证抓出)。
  - Step B 单元格段落必须清零首行缩进 (Normal 样式 2 字符缩进会把窄列里的
    "(N)" 挤成两行——实测事故)。
  - lxml 顺序: 先 addprevious 表格占位、再把公式段落 append 进中列 (反序会报
    "cannot add ancestor as sibling")。
  - 相邻 w:tbl 之间补空段, 否则 Word 把相邻表格合并成一张。
  - 每次重导出 docx 后必须重跑 (导出会重新生成公式段/表格); export_final_docx.py
    --presentation (默认开) 已在导出尾部同进程自动调用 process()。
  - 原地保存前自动备份 <名>.pre_pp.bak.docx (存在则不覆盖)。
  - Step A 只按政策注入/不注入, **不撤销**已存在的 m:sty="p"——pandoc 自身就给
    函数名/算符/数字写 p (\\sin、\\mathrm{}、\\text{}), 与上一轮"全局正体"全刷的
    产物逐 run 不可区分; 政策改成 conventional 时正确动作是**回源重导出**
    (md → docx), 不是在 docx 上做不可靠的逆向擦除 (检测到疑似全刷会打印警示)。

用法:
    python scripts/docx_presentation_postprocess.py --docx <路径>   (--docx 必填)
        政策来源: --math-font upright|conventional 显式指定 > decision_log
        (--workspace 给 paper_workspace, 或按 docx 路径上溯自动定位 state/
        decision_log.json) > 未登记 (保持输入 + 警告)。
导出链接线: export_final_docx.py --presentation (默认开) 自动执行, 并把
--workspace 与其解析到的政策透传进来;
docx_to_pdf.py 转换前用 find_unprocessed_equation_numbers() 检测漏跑并警告。

退出码: 0 处理完成; 2 用法错误 (--docx 缺失/文件不存在/--math-font 取值非法)。
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

# 数学字体正斜政策解析 (decision_log 读取 + 判定) 的单一真源
from math_font_policy import (POLICY_CONVENTIONAL, POLICY_LABELS,
                              POLICY_UNSPECIFIED, POLICY_UPRIGHT,
                              decision_log_path, locate_decision_log,
                              read_decision_log, read_decision_log_file,
                              resolve_math_font_policy)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"

RULE_SIDES = ("top", "bottom")
OFF_SIDES = ("insideH", "insideV", "left", "right")
SZ_RULE = "12"    # 1.5pt 粗线 (数据表上下边)
SZ_HEADER = "6"   # 0.75pt 细线 (表头行下)

# ---- Step B 包裹表宽度 (按公式段所在节版心; 不再用 9072 常量) ----
EQ_NUM_COL_TWIPS = 726       # 左右占位/编号列宽 0.5in (实测足以容纳 "(12)")
EQ_NUM_COL_MIN_TWIPS = 240   # 版心过窄时占位列下限
EQ_MID_MIN_TWIPS = 1440      # 公式中列下限 1in
# ECMA-376 §17.6.12/§17.6.13 的 pgSz/pgMar 缺省值 (Word 的隐含默认):
# Letter 12240×15840 twips + 四边距 1in → 版心 9360。缺项时按此补, 不另拍常量。
OOXML_DEFAULT_PAGE_W = 12240
OOXML_DEFAULT_MARGIN = 1440

# ---- Step E2 长文本列阈值 (单元格文本达到此字符数 → 该列整列左对齐) ----
CELL_LONG_TEXT_CHARS = 20

# ---- Step A "疑似已被全刷正体"启发式 (仅告警, 不据此改文档) ----
LETTER_RE = re.compile(r"[A-Za-z\u0370-\u03ff]")
MIN_FLOOD_LETTER_RUNS = 5

# 真编号判据 (H1, 实证于 pandoc 3.x OMML 产物): 编号 "(N)" 前必须存在**幸存的
# 空白字符**。$$x=1 \qquad (1)$$ 的 \qquad 渲染为专属空白 run (U+2001×2), 满足;
# $$f(1)$$ / $$a+(2)$$ / $$a + (2)$$ (pandoc 直接丢弃普通空格, 'a + (2)' 也产
# 'a+(2)') 的 "(" 紧贴公式主体, 不满足——不得误当编号提出、静默改写数学内容。
NUMBERED_TAIL_RE = re.compile(r"\s\((\d+)\)\s*$")

# ---- OOXML schema 子元素序 (H2: 直接格式注入必须按序, 否则 tblBorders 落到
# tblLook/tblCaption 之后、spacing 插到 pStyle 之前, Word 严格校验拒开) ----
_TBLPR_SEQ = ("tblStyle", "tblpPr", "tblOverlap", "bidiVisual",
              "tblStyleRowBandSize", "tblStyleColBandSize", "tblW", "jc",
              "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout",
              "tblCellMar", "tblLook", "tblCaption", "tblDescription",
              "tblPrChange")
_TRPR_SEQ = ("cnfStyle", "divId", "gridBefore", "gridAfter", "wBefore",
             "wAfter", "cantSplit", "trHeight", "tblHeader", "tblCellSpacing",
             "jc", "hidden", "ins", "del", "trPrChange")
_TCPR_SEQ = ("cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders",
             "shd", "noWrap", "tcMar", "textDirection", "tcFitText", "vAlign",
             "hideMark", "headers", "cellIns", "cellDel", "cellMerge",
             "tcPrChange")
_PPR_SEQ = ("pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr",
            "widowControl", "numPr", "suppressLineNumbers", "pBdr", "shd",
            "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
            "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN",
            "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind",
            "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc",
            "textDirection", "textAlignment", "textboxTightWrap",
            "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange")
_BORDER_SEQ = ("top", "left", "bottom", "right", "insideH", "insideV",
               "tl2br", "tr2bl")


def _get_or_add(parent, tag: str, seq: tuple):
    """按 OOXML schema 子元素序 (w: 命名空间) 获取/创建 parent 的子元素。

    已存在 → 原位返回; 不存在 → 创建并插到「首个已存在的 schema 后继元素」
    之前, 无后继则追加。不依赖 python-docx 元素类 (Step B 新造的 pPr 是裸
    lxml 元素, 没有 get_or_add_* 方法), 对两类元素统一生效。
    """
    qtag = wq(tag)
    child = parent.find(qtag)
    if child is not None:
        return child
    child = parent.makeelement(qtag, {})
    successors = {wq(t) for t in seq[seq.index(tag) + 1:]}
    for node in parent:
        if node.tag in successors:
            node.addprevious(child)
            return child
    parent.append(child)
    return child


def wq(tag: str) -> str:
    return "{%s}%s" % (W, tag)


def mq(tag: str) -> str:
    return "{%s}%s" % (M, tag)


# ---- Step A: 数学字体正斜 (§5.6, 政策驱动) ----

def upright_all_math(root) -> int:
    """所有 m:oMath 下的 m:r 注入/改写 m:rPr/m:sty val=p (全局正体)。返回处理 run 数。

    只在政策 upright 时调用 (调用方 process() 判定); 政策为 conventional 或未
    登记时不得调用——Word 的默认渲染 (字母斜体、函数/算符/数字正体) 本身就是
    GB 3102 惯例形态, 而"给所有 run 写 i"会把用户已写好的正体一起改坏。
    """
    n = 0
    for omath in root.iter(mq("oMath")):
        for r in omath.iter(mq("r")):
            rpr = r.find(mq("rPr"))
            if rpr is None:
                rpr = r.makeelement(mq("rPr"), {})
                r.insert(0, rpr)
            sty = rpr.find(mq("sty"))
            if sty is None:
                sty = rpr.makeelement(mq("sty"), {})
                rpr.append(sty)
            sty.set(mq("val"), "p")
            n += 1
    return n


def upright_letter_run_stats(root) -> tuple:
    """(带 m:sty=p 的字母 run 数, 字母 run 总数) —— "疑似已被全刷正体"启发式。

    pandoc 自身只给函数名/算符/数字写 m:sty=p (\\sin、\\mathrm{}、\\text{}),
    字母变量 run 不带 sty (Word 默认渲染为斜体); 因此"字母 run 也全部带 p"是
    上一轮全局正体后处理留下的特征。仅用于告警文案, **不据此改动文档**:
    \\mathrm/\\text 多的稿子也会抬高该数, 故判据是"全部字母 run 都是 p 且总数
    ≥ MIN_FLOOD_LETTER_RUNS"。
    """
    flagged = letters = 0
    for omath in root.iter(mq("oMath")):
        for r in omath.iter(mq("r")):
            if not any(LETTER_RE.search(t.text or "") for t in r.findall(mq("t"))):
                continue
            letters += 1
            sty = r.find(mq("rPr") + "/" + mq("sty"))
            if sty is not None and sty.get(mq("val")) == "p":
                flagged += 1
    return flagged, letters


# ---- Step B: 编号右顶格 (§5.1) ----

def _zero_indent(ppr) -> None:
    """清零段落缩进**全部**分量: 首行/悬挂/左右 (含 Chars 变体)。

    Normal/Compact 样式链可能带 2 字符首行缩进 (会把窄单元格里的编号 '(N)' 挤成
    两行——实测事故), 也可能带悬挂缩进 (hanging/hangingChars: 列表或 `\\item` 风格
    残留); 只清 firstLine 压不住字符单位的那一项, 悬挂缩进更会整段右移。ind 按
    schema 序插入 (H2)。公式段与编号单元段落共用本函数 (公式段也清悬挂)。
    """
    ind = _get_or_add(ppr, "ind", _PPR_SEQ)
    for key in ("firstLine", "firstLineChars", "hanging", "hangingChars",
                "left", "leftChars", "right", "rightChars"):
        ind.set(wq(key), "0")


def _set_compact_spacing(ppr) -> None:
    """写"单倍行距 + 零段前段后 + 关自动间距" (含 Lines/autospacing 变体)。

    公式包裹表三列 (左空/公式/编号) 与数据表单元格共用。为什么要连 Lines 与
    autospacing 一起写: 只写 before/after 时, 样式链继承的多倍行距 (line=360
    auto 等) 或 *Autospacing 仍生效, Word 的行盒会把该列文字压在自己的盒底——
    单元格虽 vAlign=center, 三列行盒不等高时编号就"掉"到公式主体下方 (judge
    2026-09-19 S3 复验: 水平定位 pass、编号明显偏低)。三列统一紧凑行盒才稳。
    按 pPr schema 序插入/覆盖 (H2)。
    """
    sp = _get_or_add(ppr, "spacing", _PPR_SEQ)
    for key in ("before", "after", "beforeLines", "afterLines",
                "beforeAutospacing", "afterAutospacing"):
        sp.set(wq(key), "0")
    sp.set(wq("line"), "240")
    sp.set(wq("lineRule"), "auto")


def _empty_paragraph(jc: str | None = None, text: str | None = None):
    from lxml import etree

    p = etree.Element(wq("p"))
    ppr = etree.SubElement(p, wq("pPr"))
    _set_compact_spacing(ppr)
    _zero_indent(ppr)
    if jc:
        etree.SubElement(ppr, wq("jc"), {wq("val"): jc})
    if text:
        r = etree.SubElement(p, wq("r"))
        t = etree.SubElement(r, wq("t"))
        t.text = text
    return p


def _set_paragraph_center(p) -> None:
    """公式段居中 + 紧凑行盒 (与左右两列同一行高基准, 防编号偏低)。

    v3.1.0 修 (judge S3 复验): 原实现只清缩进 + 写 jc, 段落行距/段距仍随样式链
    (FirstParagraph/BodyText 的多倍行距) —— 公式列行盒比编号列高, 垂直居中后
    编号视觉上低于公式主体。这里补写紧凑 spacing (与编号列、空列一致)。
    """
    ppr = p.find(wq("pPr"))
    if ppr is None:
        ppr = p.makeelement(wq("pPr"), {})
        p.insert(0, ppr)
    _zero_indent(ppr)
    _set_compact_spacing(ppr)
    _get_or_add(ppr, "jc", _PPR_SEQ).set(wq("val"), "center")


def _multicol_note(sectpr) -> str | None:
    """多栏节的"未支持"说明; 非多栏返回 None。

    触发: w:cols/@w:num > 1, 或列宽不等 (equalWidth=0 / 各 w:col/@w:w 不一致)。
    **只发警告, 不改宽度算法**: 包裹表宽度仍按单栏版心 (pgSz−pgMar−gutter) 算;
    多栏节的每栏实际可用宽 = (版心−栏间距)/栏数, 本脚本不建模——不能让"逐节
    动态宽度"看起来已经支持多栏。
    """
    cols = sectpr.find(wq("cols")) if sectpr is not None else None
    if cols is None:
        return None
    raw_num = cols.get(wq("num"))
    num = int(raw_num) if (raw_num or "").isdigit() else 1
    widths = [c.get(wq("w")) for c in cols.findall(wq("col"))]
    equal = cols.get(wq("equalWidth"))
    unequal = (equal is not None and equal not in ("1", "true")) or \
        len({w for w in widths if w}) > 1
    if num <= 1 and not unequal:
        return None
    return f"w:cols num={num}" + (" 且列宽不等" if unequal else "")


def _section_text_width(sectpr) -> tuple:
    """sectPr → (版心宽 twips | None, 多栏未支持说明 | None)。

    版心宽 = pgSz.w − pgMar.left − pgMar.right − pgMar.gutter。
    缺 pgSz/pgMar 或缺具体属性时按 ECMA-376 缺省值补 (Letter 12240×15840、
    四边距 1in) —— 这是 Word 的隐含默认而非本项目拍的常量。横向节的 pgSz.w 已是
    长边 (Word 写出时已换位), 不再换位; gutter 从可用宽度里扣 (装订线占版心)。
    sectpr 为 None 或算出的宽度 ≤0 → (None, None), 由调用方走全局兜底 + 告警。
    多栏节 (w:cols) **不建模**, 第二个返回值是给用户的未支持说明 (见 _multicol_note)。
    """
    if sectpr is None:
        return None, None

    def _attr_int(el, tag, default):
        if el is None:
            return default
        raw = el.get(wq(tag))
        if raw is None or not raw.lstrip("-").isdigit():
            return default
        return int(raw)

    pgsz = sectpr.find(wq("pgSz"))
    mar = sectpr.find(wq("pgMar"))
    width = _attr_int(pgsz, "w", OOXML_DEFAULT_PAGE_W)
    # gutter 缺省是 0 (不是 margin 缺省的 1440), 单独取
    gutter = _attr_int(mar, "gutter", 0)
    avail = width - _attr_int(mar, "left", OOXML_DEFAULT_MARGIN) \
        - _attr_int(mar, "right", OOXML_DEFAULT_MARGIN) - gutter
    note = _multicol_note(sectpr)
    return (avail if avail > 0 else None), note


def _section_width_map(root) -> tuple:
    """({id(body 直接子元素): 版心宽 twips | None}, {id: 多栏未支持说明 | None})。

    OOXML 节模型: sectPr 存于该节**最后一个**段落的 w:pPr (段末节属性), 文档
    末节存于 body 直属 w:sectPr。故沿 body 子元素正向走, 遇到 p/pPr/sectPr 就把
    该 sectPr 分给"自上一个节末以来"的全部子元素 (含该段本身); 尾部剩余归
    body/sectPr。这就是 Word 的节归属判定——多节不同页宽时各节按各自的版心。

    键用 id(元素) (lxml 元素在树存活期间地址稳定), 调用方按元素查表; 第二个 map
    只对多栏节非 None (说明见 _multicol_note)。
    """
    body = root.find(wq("body"))
    if body is None:
        return {}, {}
    out: dict = {}
    notes: dict = {}
    pending: list = []
    for child in body:
        pending.append(child)
        if child.tag != wq("p"):
            continue
        ppr = child.find(wq("pPr"))
        if ppr is None:
            continue
        sect = ppr.find(wq("sectPr"))
        if sect is None:
            continue
        width, note = _section_text_width(sect)
        for el in pending:
            out[id(el)] = width
            notes[id(el)] = note
        pending = []
    tail_width, tail_note = _section_text_width(body.find(wq("sectPr")))
    for el in pending:
        out[id(el)] = tail_width
        notes[id(el)] = tail_note
    return out, notes


def _equation_table_widths(avail: int) -> tuple:
    """(左占位, 公式中列, 右编号列) twips, 总宽 = 所在节版心宽。

    左右占位列固定 EQ_NUM_COL_TWIPS (0.5in); 版心窄到中列不足 EQ_MID_MIN_TWIPS
    时收窄占位列 (不低于 EQ_NUM_COL_MIN_TWIPS), 中列吃掉剩余宽度——中列越宽,
    长公式越不容易顶破版心 (公式对象不能折行, 只能给足宽度)。
    """
    outer = EQ_NUM_COL_TWIPS
    if avail - 2 * outer < EQ_MID_MIN_TWIPS:
        outer = max(EQ_NUM_COL_MIN_TWIPS, (avail - EQ_MID_MIN_TWIPS) // 2)
    return outer, max(avail - 2 * outer, 1), outer


def _make_equation_table(number: str, widths: tuple):
    """构造无边框三列表格 (空第二列), 返回 (tbl, 中列单元格)。公式段落由调用方
    在把表格插回原位置之后再移入中列——顺序不能反 (lxml 禁止把祖先作兄弟插入)。"""
    from lxml import etree

    tbl = etree.Element(wq("tbl"))
    tblpr = etree.SubElement(tbl, wq("tblPr"))
    etree.SubElement(tblpr, wq("tblW"), {wq("w"): str(sum(widths)), wq("type"): "dxa"})
    borders = etree.SubElement(tblpr, wq("tblBorders"))
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        etree.SubElement(borders, wq(side),
                         {wq("val"): "none", wq("sz"): "0",
                          wq("space"): "0", wq("color"): "auto"})
    etree.SubElement(tblpr, wq("tblLayout"), {wq("type"): "fixed"})
    mar = etree.SubElement(tblpr, wq("tblCellMar"))
    for side in ("top", "left", "bottom", "right"):
        etree.SubElement(mar, wq(side), {wq("w"): "0", wq("type"): "dxa"})
    grid = etree.SubElement(tbl, wq("tblGrid"))
    for wd in widths:
        etree.SubElement(grid, wq("gridCol"), {wq("w"): str(wd)})

    tr = etree.SubElement(tbl, wq("tr"))
    cells = []
    for wd in widths:
        tc = etree.SubElement(tr, wq("tc"))
        tcpr = etree.SubElement(tc, wq("tcPr"))
        etree.SubElement(tcpr, wq("tcW"), {wq("w"): str(wd), wq("type"): "dxa"})
        tb = etree.SubElement(tcpr, wq("tcBorders"))
        for side in ("top", "left", "bottom", "right"):
            etree.SubElement(tb, wq(side),
                             {wq("val"): "nil", wq("sz"): "0",
                              wq("space"): "0", wq("color"): "auto"})
        etree.SubElement(tcpr, wq("vAlign"), {wq("val"): "center"})
        cells.append(tc)

    cells[0].append(_empty_paragraph())
    cells[2].append(_empty_paragraph(jc="right", text=f"({number})"))
    return tbl, cells[1]


def extract_numbers_and_wrap(root) -> tuple:
    """Step B: body 直接子层的 display 公式段落 → 三列表格。

    返回 (处理数, 编号列表, 各包裹表总宽去重升序列表 twips, 缺省版心兜底数,
    节末公式段跳过数, 多栏未支持说明列表): 表宽列表供报告核对"逐节版心"是否生效
    (全部节同宽时只有一项); 兜底数 = 无法判定所在节版心的段数; 跳过数 = 本身是
    节末段 (pPr/sectPr) 的编号公式段数 (不包表, 见循环内注释); 多栏说明只对
    被包裹公式所在节登记 (多栏版心未建模, 宽度按单栏算, 明确告知而非假装修好)。
    包裹表宽度取该公式段**所在节的版心** (_section_width_map); 无法判定所在节
    版心时按 OOXML 缺省页宽/边距补全 (12240/1440) 并计入 fallback 计数。
    宽度映射在任何搬段之前算好 (_section_width_map 基于原始 body 结构), 故
    "节末段本身是公式段"时也按其结束的那一节取版心 (但该段会被跳过不包表)。
    """
    from lxml import etree  # noqa: F401  (与工作区脚本保持同一实现语境)

    body = root.find(wq("body"))
    paras = [p for p in list(body)
             if p.tag == wq("p") and p.find(".//" + mq("oMathPara")) is not None]
    width_map, note_map = _section_width_map(root)
    fallback = OOXML_DEFAULT_PAGE_W - 2 * OOXML_DEFAULT_MARGIN
    done, numbers, used_widths, n_fallback, n_sect_skip = 0, [], set(), 0, 0
    multicol_notes: list = []
    for p in paras:
        # 节末段 (pPr/sectPr) 是公式段时**不包表**: 把带节属性的段落搬进表格
        # 单元格会把节界藏进 tc 内, Word 直接拒绝打开该 docx (实测: Word COM
        # Documents.Open 报"Word 在试图打开文件时遇到错误"), 且静默挪动节界本身
        # 就是版面事故。处置 = 跳过该段编号右顶格 + 报告 (回源把节界改到空段/
        # 非公式段后重导出), 不假装修好。
        ppr = p.find(wq("pPr"))
        if ppr is not None and ppr.find(wq("sectPr")) is not None:
            n_sect_skip += 1
            continue
        mts = [t for t in p.findall(".//" + mq("t")) if t.text]
        # pandoc 会把编号 "(N)" 拆成多个 m:t run (如 '('、'1'、')'),
        # 须跨 run 拼接匹配, 再按字符数从尾部回溯删除。
        full = "".join(t.text for t in mts)
        m = NUMBERED_TAIL_RE.search(full)
        if m is None:
            continue
        num = m.group(1)
        # 尾部待删字符数 = 匹配段长度 (此前误把"应保留数"当"待删数",
        # 会从尾反向删光公式正文、只留开头几字符——渲染验证抓出后修正);
        # 匹配起点含编号前的空白分隔 (\qquad 产物), 一并删净 (H1)
        to_remove = len(full) - m.start()
        for t in reversed(mts):
            if to_remove <= 0:
                break
            text = t.text
            if len(text) <= to_remove:
                to_remove -= len(text)
                t.getparent().remove(t)
            else:
                t.text = text[: len(text) - to_remove]
                to_remove = 0
        # 裁掉公式尾部残留的 \qquad 空格
        rest = [t for t in p.findall(".//" + mq("t")) if t.text]
        if rest:
            rest[-1].text = rest[-1].text.rstrip()
            if not rest[-1].text:
                rest[-1].getparent().remove(rest[-1])
        avail = width_map.get(id(p))
        if avail is None:  # 无 sectPr/缺 pgSz: 按 OOXML 缺省值补全 (报告里计数)
            avail = fallback
            n_fallback += 1
        note = note_map.get(id(p))
        if note and note not in multicol_notes:
            multicol_notes.append(note)
        widths = _equation_table_widths(avail)
        used_widths.add(sum(widths))
        _wrap_equation_paragraph(p, num, widths)
        numbers.append(num)
        done += 1
    # 相邻表格之间补空段 (防 Word 合并)
    _pad_between_adjacent_tables(body)
    return done, numbers, sorted(used_widths), n_fallback, n_sect_skip, multicol_notes


def _wrap_equation_paragraph(p, num: str, widths: tuple) -> None:
    """把公式段包成"占位｜公式居中｜编号右对齐"三列表格 (原地搬运)。

    lxml 顺序: 先插表格占位 (此时 p 仍在 body), 再把 p 移进中列 —— 反序会报
    "cannot add ancestor as sibling"。
    """
    tbl, mid_cell = _make_equation_table(num, widths)
    p.addprevious(tbl)
    _set_paragraph_center(p)
    mid_cell.append(p)


def _pad_between_adjacent_tables(body) -> None:
    """相邻 w:tbl 之间补空段 (否则 Word 把相邻表格合并成一张)。"""
    children = list(body)
    for i, ch in enumerate(children):
        if ch.tag == wq("tbl") and i + 1 < len(children) \
                and children[i + 1].tag == wq("tbl"):
            children[i + 1].addprevious(_empty_paragraph())


def _loose_number_runs(p) -> tuple:
    """"独立 oMath + 尾部普通文本编号"段落的 (待删编号 run 列表, 编号, 说明)。

    返回三态:
      (runs, num, None)      可处理 —— 通过下面的保守结构白名单;
      (None, None, None)     与本形态无关 (无 oMath / 无尾部编号), 不处理不告警;
      (None, None, 原因串)   形似但结构复杂或编号在前 —— **保持输入 + 告警**。

    白名单 (任一不满足即拒绝, 宁可告警也不猜):
      ① 无 m:oMathPara;
      ② 直接子层**恰有一个** m:oMath;
      ③ 直接子层除该 oMath 外只允许 w:r (出现 w:hyperlink / w:fldSimple /
         w:smartTag / sdt / 图片等复杂内容 → 拒绝);
      ④ 每个 w:r 只允许 rPr + 恰一个 w:t (含 w:br/w:tab/drawing 等 → 拒绝:
        此类 run 不能整条删除, 会连带删掉换行/图形);
      ⑤ 编号 run 全部在 oMath **之后** (编号在前 → 拒绝: 搬走会改变阅读顺序);
      ⑥ 这些 w:t 拼起来恰为 "(N)"/" (N)"。

    候选判据**独立于 Step B 的 H1 空白判据** (NUMBERED_TAIL_RE 要求编号前有幸存
    空白; 那是 oMathPara 真编号的判据, **不改**): 这里只看**普通文本 (w:t, 含
    hyperlink/field 等嵌套)** 自己是否落在尾部 "(N)" 形态——公式与编号之间有没有
    空白都不影响, 因为 pandoc 少写 display 环境时编号可能紧贴公式 (x=1(1))。
    普通文本里确有 "(N)" 但不在尾部 (典型是编号在公式之前) → 保持输入 + 告警。
    """
    if p.find(".//" + mq("oMathPara")) is not None:
        return None, None, None
    plain_text = "".join(t.text or "" for t in p.findall(".//" + wq("t")))
    if re.search(r"\((\d+)\)\s*$", plain_text) is None:
        # 普通文本尾部没有编号形态: 段里有编号但不在尾部 → 保持输入 + 告警;
        # 完全没编号 → 与本形态无关
        if p.find(mq("oMath")) is not None and re.search(r"\((\d+)\)", plain_text):
            return None, None, "编号不在段落尾部 (通常在公式之前), 保持输入"
        return None, None, None

    direct = [c for c in p if c.tag != wq("pPr")]
    omaths = [c for c in direct if c.tag == mq("oMath")]
    if len(omaths) != 1:
        return None, None, f"直接子层 oMath 数为 {len(omaths)} (白名单要求恰 1)"
    others = [c for c in direct if c.tag not in (mq("oMath"), wq("r"))]
    if others:
        names = ", ".join(sorted({c.tag.split("}")[-1] for c in others}))
        return None, None, f"含非纯文本 run 的复杂内容 ({names})"
    if not [c for c in direct if c.tag == wq("r")]:
        return None, None, "无编号文本 run"

    omath_idx = direct.index(omaths[0])
    num_runs = []
    for i, c in enumerate(direct):
        if c.tag != wq("r"):
            continue
        kids = [k for k in c if k.tag != wq("rPr")]
        if len(kids) != 1 or kids[0].tag != wq("t"):
            return None, None, "编号 run 含非纯文本内容 (br/tab/嵌套等), 不能整条删除"
        num_runs.append((i < omath_idx, c))
    if any(before for before, _ in num_runs):
        return None, None, "编号 run 出现在公式之前"
    text = "".join(k.text or "" for _, c in num_runs for k in c.findall(wq("t")))
    m = re.fullmatch(r"\s*\((\d+)\)\s*", text)
    if m is None:
        return None, None, f"编号文本非纯编号 ({text!r})"
    return [c for _, c in num_runs], m.group(1), None


def _to_display_math(p, omath) -> None:
    """把段内直接子元素 m:oMath 包成 m:oMathPara (居中 display 公式)。

    只对"独立公式段"调用 (段内普通文本恰为编号): 这样产出的包裹表与 Step B 的
    形态完全一致 (含 oMathPara), C/D/E/E2 的"公式包裹表跳过"判据天然生效, 不会给
    公式表加三线/autofit; 也不是"把公式变成普通行内"(方向相反: 行内 → display)。
    """
    from lxml import etree

    para = etree.Element(mq("oMathPara"))
    pr = etree.SubElement(para, mq("oMathParaPr"))
    etree.SubElement(pr, mq("jc")).set(mq("val"), "center")
    omath.addprevious(para)
    omath.getparent().remove(omath)
    para.append(omath)


def wrap_standalone_math_numbers(root, width_map: dict, fallback: int) -> tuple:
    """窄口径补 Step B: "独立 oMath + 尾部普通文本编号"段落也按同一制式包表。

    只处理**通过保守结构白名单**的段落 (_loose_number_runs 六条: 恰一直接 oMath、
    编号 run 在公式之后、run 内只有 rPr+单个 w:t、编号文本纯为 "(N)"), S3 实测形态
    (oMath 与 " (1)" 同段, 参见 evaluation-before/fixtures 的 S3 合成件) 属于此列。
    形似的复杂形态 (超链/字段/换行/编号在前/夹带说明文字) 一律**保持输入 + 计数告警**,
    回源改用 $$…\\qquad (N)$$ display 公式重导出; 不做通用公式识别重构。
    节末段同样跳过不搬。
    返回 (包表数, 跳过数, 仅告警数): 跳过数 = 因是节末段而放弃的段数。
    """
    body = root.find(wq("body"))
    if body is None:
        return 0, 0, 0
    wrapped = skipped = warn_only = 0
    for p in [c for c in list(body) if c.tag == wq("p")]:
        if p.find(".//" + mq("oMathPara")) is not None:
            continue                       # 已由 Step B 处理
        if p.find(".//" + wq("drawing")) is not None:
            continue                       # 含图段不动
        runs, num, reason = _loose_number_runs(p)
        if runs is None:
            if reason is not None:         # 形似但复杂/编号在前 → 只告警, 不动文档
                warn_only += 1
            continue
        ppr = p.find(wq("pPr"))
        if ppr is not None and ppr.find(wq("sectPr")) is not None:
            skipped += 1                   # 节末段: 搬进表格会让 Word 拒绝打开
            continue
        omath = p.find(mq("oMath"))
        _to_display_math(p, omath)
        for r in runs:                     # 已白名单保证: 纯编号文本, 可整条删
            p.remove(r)
        avail = width_map.get(id(p))
        if avail is None:
            avail = fallback
        _wrap_equation_paragraph(p, num, _equation_table_widths(avail))
        wrapped += 1
    _pad_between_adjacent_tables(body)
    return wrapped, skipped, warn_only


# ---- Step C/D/E: 数据表 (§6.1/§6.2) ----

def _has_display_math(tbl) -> bool:
    """公式编号包裹表 (Step B 产物) 必须保持无边框固定布局, 三线/自适应/居中/
    行禁拆/单元格排版一律跳过。"""
    return tbl.find(".//" + mq("oMathPara")) is not None


def _set_border(parent, side: str, val: str, sz: str) -> None:
    b = _get_or_add(parent, side, _BORDER_SEQ)
    b.set(wq("val"), val)
    b.set(wq("sz"), sz)
    b.set(wq("space"), "0")
    b.set(wq("color"), "000000")


def _ensure_tbl_borders(tblpr):
    # tblBorders 按 schema 序插入 (H2): 必须落在 tblLook/tblCaption 之前
    return _get_or_add(tblpr, "tblBorders", _TBLPR_SEQ)


def threeline_all(root) -> int:
    """Step C: 数据表三线制式 (booktabs 等价)。返回处理表数。"""
    n = 0
    for tbl in root.findall(".//" + wq("tbl")):
        if _has_display_math(tbl):
            continue  # 公式编号包裹表: 必须无边框
        tblpr = tbl.find(wq("tblPr"))
        if tblpr is None:
            continue
        b = _ensure_tbl_borders(tblpr)
        for side in RULE_SIDES:
            _set_border(b, side, "single", SZ_RULE)
        for side in OFF_SIDES:
            _set_border(b, side, "none", "0")
        # 表头行下边框
        first_tr = tbl.find(wq("tr"))
        if first_tr is not None:
            for tc in first_tr.findall(wq("tc")):
                tcpr = tc.find(wq("tcPr"))
                if tcpr is None:
                    tcpr = tc.makeelement(wq("tcPr"), {})
                    tc.insert(0, tcpr)
                # tcBorders 按 schema 序插入 (H2): 须在 shd/vAlign 之前
                tcb = _get_or_add(tcpr, "tcBorders", _TCPR_SEQ)
                _set_border(tcb, "bottom", "single", SZ_HEADER)
        # 清底纹
        for shd in tbl.findall(".//" + wq("shd")):
            shd.set(wq("fill"), "auto")
            shd.set(wq("val"), "clear")
        n += 1
    return n


def fit_and_center(root) -> int:
    """Step D: tblW→100% pct (撑满版心) + tblLayout→autofit (列宽随内容重分配,
    修 pandoc 等宽 gridCol 把长内容列挤断行的缺陷) + tblPr 注入 jc=center (表体
    居中) + 数据表各行 trPr/cantSplit (行禁拆——行跨页拆分会把单元格内容劈成
    两半, 产生孤立残行)。返回处理表数。"""
    n = 0
    for tbl in root.findall(".//" + wq("tbl")):
        if _has_display_math(tbl):
            continue
        tblpr = tbl.find(wq("tblPr"))
        if tblpr is None:
            continue
        # tblW: 撑满版心 (100% pct; 已是的保持不动)
        tw = _get_or_add(tblpr, "tblW", _TBLPR_SEQ)
        tw.set(wq("w"), "5000")
        tw.set(wq("type"), "pct")
        # jc: 表体居中 (schema 序: 紧跟 tblW 之后)
        _get_or_add(tblpr, "jc", _TBLPR_SEQ).set(wq("val"), "center")
        # tblLayout: fixed → autofit (schema 序: tblBorders 之后、tblCellMar/tblLook 之前)
        _get_or_add(tblpr, "tblLayout", _TBLPR_SEQ).set(wq("type"), "autofit")
        # cantSplit: 行禁拆 (trPr 须为 tr 首子元素; cantSplit 按 trPr 序插入,
        # 须在 trHeight/tblHeader 之前)
        for tr in tbl.findall(wq("tr")):
            trpr = tr.find(wq("trPr"))
            if trpr is None:
                trpr = tr.makeelement(wq("trPr"), {})
                tr.insert(0, trpr)
            _get_or_add(trpr, "cantSplit", _TRPR_SEQ)
        n += 1
    return n


def normalize_cell_paragraphs(root) -> int:
    """Step E: 单元格文字零缩进、零段距、单倍行距 (公式段悬挂一并清零)。

    pandoc 把单元格段落挂 Compact 样式 (段前段后各 1.8pt、行距经样式链继承
    Normal 的 1.3 倍)。本步对数据表内全部段落直写 pPr: spacing before/after=0
    + **beforeLines/afterLines=0 + beforeAutospacing/afterAutospacing=0 (关自动
    间距)** + line=240 auto (单倍) + ind 全零 (含 hanging/hangingChars, 见
    _zero_indent)——直接格式覆盖样式链, 成稿不受 reference.docx 样式定义影响。

    为什么连 Lines/autospacing 一起写: 只写 before/after 时, 样式链或前次编辑
    留下的 beforeLines (段前行数) 与 *Autospacing (自动间距开关) 仍会生效——
    Word 的优先级是 autospacing > lines > twips, 漏掉就是"看着零段距实际有"。
    """
    n = 0
    for tbl in root.findall(".//" + wq("tbl")):
        if _has_display_math(tbl):
            continue
        for p in tbl.findall(".//" + wq("p")):
            ppr = p.find(wq("pPr"))
            if ppr is None:
                ppr = p.makeelement(wq("pPr"), {})
                p.insert(0, ppr)
            # spacing/ind 按 pPr schema 序插入 (H2): 不得落在 pStyle 之前、
            # 也不得落到 rPr/sectPr 之后 (此前 insert(0)/追加两头像过)
            _set_compact_spacing(ppr)
            _zero_indent(ppr)   # ind 全零 (含 hanging/hangingChars)
            n += 1
    return n


# ---- Step E2: 单元格段落对齐 (§6.2, 长文本例外) ----

def _set_paragraph_align(p, jc: str) -> None:
    """写段落 jc=jc (按 pPr schema 序插入/覆盖), 其余直接格式一字不动。"""
    ppr = p.find(wq("pPr"))
    if ppr is None:
        ppr = p.makeelement(wq("pPr"), {})
        p.insert(0, ppr)
    _get_or_add(ppr, "jc", _PPR_SEQ).set(wq("val"), jc)


def _row_column_spans(tr) -> list:
    """行内 [(tc, 起始列号, 跨列数)] —— 按 gridSpan 累加得到真实列位 (缺省 1)。

    合并单元格按它覆盖的列区间参与列判定 (gridSpan 缺省/非法值按 1 处理)。
    """
    out = []
    col = 0
    for tc in tr.findall(wq("tc")):
        span = 1
        tcpr = tc.find(wq("tcPr"))
        if tcpr is not None:
            gs = tcpr.find(wq("gridSpan"))
            if gs is not None and (gs.get(wq("val")) or "").isdigit():
                span = max(int(gs.get(wq("val"))), 1)
        out.append((tc, col, span))
        col += span
    return out


def _cell_text_length(tc) -> int:
    """单元格纯文本字符数 (w:t 拼接后剔除空白与零宽断行点 U+200B)。

    零宽空格是 md 源里插的断行点 (不是内容), 空格/换行也不是判"长文本"的依据;
    数字与字母按 1 字符计 (阈值口径 = 字符数, 与 §6.2 的"长文本列"直觉一致)。
    """
    text = "".join(t.text or "" for t in tc.findall(".//" + wq("t")))
    return len(re.sub(r"[\s\u200b]+", "", text))


def align_cell_paragraphs(root, long_text_chars: int = CELL_LONG_TEXT_CHARS) -> tuple:
    """Step E2: 单元格段落对齐 (§6.2): 短列居中, 长文本列整列左对齐。

    与 Step D 的**表体居中** (tblPr/jc=center) 分开两步: 本步只写单元格段落的
    pPr/jc, 不动表级属性。长文本例外按**列**判定 (列内任一单元格文本 ≥
    long_text_chars 字符 → 该列整列左对齐), 保证 §6.2 的"全表统一"; 判定结果
    写进返回的说明行, 供人在表注里说明 (规范: 长文本列可左对齐但需全表统一并在
    表注说明)。零宽断行点与空白不计入长度 (_cell_text_length)。
    公式编号包裹表跳过 (其段落 jc 已由 Step B 定好); 只写 jc, C 的三线边框与
    E 的零缩进/零段距/单倍行距一律保持。返回 (处理段落数, 说明行列表)。
    """
    n = 0
    notes = []
    data_idx = 0
    for tbl in root.findall(".//" + wq("tbl")):
        if _has_display_math(tbl):
            continue
        data_idx += 1  # 说明行里的"数据表 N"只数数据表 (公式包裹表不算)
        rows = tbl.findall(wq("tr"))
        max_len: dict = {}
        for tr in rows:
            for tc, col, span in _row_column_spans(tr):
                length = _cell_text_length(tc)
                for c in range(col, col + span):
                    if length > max_len.get(c, -1):
                        max_len[c] = length
        long_cols = sorted(c for c, length in max_len.items()
                           if length >= long_text_chars)
        for tr in rows:
            for tc, col, span in _row_column_spans(tr):
                jc = "left" if any(col <= c < col + span for c in long_cols) \
                    else "center"
                for p in tc.findall(wq("p")):
                    _set_paragraph_align(p, jc)
                    n += 1
        if long_cols:
            cols = ", ".join(f"第 {c + 1} 列" for c in long_cols)
            longest = max(max_len[c] for c in long_cols)
            notes.append(
                f"数据表 {data_idx}: {cols} 判定为长文本列 (最长 {longest} 字符), "
                f"已整列左对齐、其余列居中 — 请在表注说明 (§6.2)")
    return n, notes


# ---- Step F: 图与图注同页 (E6) ----

def keep_figure_with_caption(root) -> int:
    """Step F: 含内联图片的段落加 w:keepNext（图与其下方图注不分页）。返回处理数。

    docx 链没有 LaTeX 的浮动机制, 图被推到下一页时往往把图注留在上一页
    （2026 国赛 A 题终稿 p16/p28 出现半页空白 + 图注孤立）。Word 的对位手段是
    段级 keepNext: 含 w:drawing 的段落标 keepNext 后, 该段与**紧随的下一段**
    （本条链里是图注）强制同页, 图与图注不再被页界劈开。
    只对 body 直接子层段落生效（表格内图片是版面构件, 不动）; 已幂等。
    注意: 本步不消除"图前留白"本身（那是内容排版固有现象）, 只保证图注不脱图;
    留白过大时按 cn_presentation_spec §7.3 调图宽或收束图前段落。
    """
    n = 0
    body = root.find(wq("body"))
    if body is None:
        return 0
    paras = body.findall(wq("p"))
    for idx, p in enumerate(paras):
        if p.find(".//" + wq("drawing")) is None:
            continue
        if idx + 1 >= len(paras):
            continue  # 文末图无后继段, keepNext 无意义
        ppr = p.find(wq("pPr"))
        if ppr is None:
            ppr = p.makeelement(wq("pPr"), {})
            p.insert(0, ppr)
        kn = _get_or_add(ppr, "keepNext", _PPR_SEQ)
        if kn.get(wq("val")) != "1":
            kn.set(wq("val"), "1")
            n += 1
    return n


# ---- 函数式入口 / 统计 / 检测 ----

def _resolve_policy(docx_path, workspace, override, decision_log) -> tuple:
    """政策解析统一入口, 返回 (policy, source, warnings)。

    优先级: decision_log 参数 (调用方已读入) > --math-font 显式 override >
    <workspace>/../state/decision_log.json (骨架约定) > <workspace>/state/
    decision_log.json (用户把项目根当 workspace 传时的兜底) > 按 docx 路径上溯
    自动定位 > 未登记 (保持输入 + 警告, 见 math_font_policy)。
    """
    if decision_log is not None:
        return resolve_math_font_policy(decision_log, override)
    if override not in (None, "auto"):
        return resolve_math_font_policy({}, override)  # cli 显式: 不读文件
    if workspace is not None:
        ws = Path(workspace)
        for cand in (decision_log_path(ws), ws / "state" / "decision_log.json"):
            if cand.is_file():
                return resolve_math_font_policy(read_decision_log_file(cand), override)
        policy, source, warns = resolve_math_font_policy({}, override)
        return policy, source, warns + [f"[政策] {ws} 下未找到 state/decision_log.json"]
    log_path, where = locate_decision_log(docx_path)
    if log_path is None:
        policy, source, warns = resolve_math_font_policy({}, override)
        return policy, source, warns + [f"[政策] {where}"]
    # 自动定位时把用到的 decision_log 写进 source, 报告里能看出读的是哪个文件
    policy, source, warns = resolve_math_font_policy(
        read_decision_log_file(log_path), override)
    return policy, (f"{source} @ {log_path}" if source else ""), warns


def process(docx_path, make_backup: bool = True, workspace=None,
            math_font: str | None = None, decision_log=None) -> dict:
    """六步呈现层后处理 (原地保存), 返回各 Step 统计 dict (含诊断 warnings)。

    参数:
      make_backup: 落 <名>.pre_pp.bak.docx 备份 (存在则不覆盖); 导出链传 False。
      workspace:   paper_workspace 路径, 用于读 <workspace>/../state/decision_log.json;
                   缺省按 docx 路径上溯自动定位 (见 _resolve_policy)。
      math_font:   "upright"|"conventional" 显式指定政策; None/"auto" = 读 decision_log。
      decision_log: 直接传 decision_log dict (优先于文件读取, 便于调用方/测试注入)。

    Step A 政策语义 (math_font_policy.resolve_math_font_policy):
      - upright: 给所有 m:oMath run 注入/改写 m:sty="p";
      - conventional: **保持输入一字不动** (Word 默认即 GB 3102 惯例形态: 字母
        斜体、函数/算符/数字正体); 本步不做逐字符正斜判定, 也不宣称"已实现/已
        校验常规正斜"——若输入已被上一轮全刷正体, 正确动作是回源重导出 (警告里
        会点明), 不在 docx 上做不可靠的逆向擦除;
      - unspecified: 同样保持输入, 并警告请登记政策。
      政策只影响 Step A; B~F 照常执行 (步间独立)。

    Step 顺序固定 A→B→C→D→E→E2→F: B 产出的公式包裹表含 oMathPara, 是 C/D/E/E2
    的天然跳过标记 (顺序颠倒会让公式表也被改坏); F 只认 body 直接子层的图片段,
    放在最后以免影响前面的表结构判定。统计键:
      math_font_policy / math_font_source / upright_runs / upright_letter_runs /
      equations_wrapped / equation_numbers / equation_widths /
      equation_width_fallbacks / threeline_tables / fit_tables / cell_paragraphs /
      cell_aligned / long_text_columns / figures_kept / warnings /
      backup_path / backup_created
    """
    from docx import Document

    path = Path(docx_path)
    if not path.is_file():
        raise FileNotFoundError(f"docx 不存在: {path}")
    policy, source, warnings = _resolve_policy(docx_path, workspace, math_font,
                                               decision_log)
    stats = {"backup_path": None, "backup_created": False,
             "math_font_policy": policy, "math_font_source": source,
             "warnings": list(warnings)}
    if make_backup:
        bak = path.with_name(path.stem + ".pre_pp.bak.docx")
        if not bak.exists():  # 存在则不覆盖 (保留最早一份 = 后处理前原始态)
            shutil.copyfile(path, bak)
            stats["backup_created"] = True
        stats["backup_path"] = str(bak)

    doc = Document(str(path))
    root = doc.element

    # ---- Step A: 数学字体正斜 (政策驱动; 不撤销不可区分的既有 m:sty) ----
    if policy == POLICY_UPRIGHT:
        stats["upright_runs"] = upright_all_math(root)
        stats["upright_letter_runs"] = upright_letter_run_stats(root)
    else:
        stats["upright_runs"] = 0
        flagged, letters = upright_letter_run_stats(root)
        stats["upright_letter_runs"] = (flagged, letters)
        if policy == POLICY_CONVENTIONAL:
            stats["warnings"].append(
                "[Step A] 政策 conventional: 保持输入未注入——Word 默认渲染 "
                "(字母斜体、函数/算符/数字正体) 即 GB 3102 惯例所需形态; 本脚本不做"
                "逐字符正斜判定, 不等于已实现或已校验常规正斜")
        else:
            stats["warnings"].append(
                "[Step A] 未登记数学字体政策: 保持输入一字未改; 请按 "
                "cn_presentation_spec §5.6 拍板后登记 (或用 --math-font 显式指定) 再重跑")
        if letters >= MIN_FLOOD_LETTER_RUNS and flagged == letters:
            stats["warnings"].append(
                f"[Step A] 输入 {letters} 个字母 math run 全部带 m:sty=p — 疑似上一轮"
                f"\"全局正体\"全刷的产物 (\\mathrm/\\text 多时也会如此); 该标记与 pandoc "
                f"自带标记逐 run 不可区分, 本脚本不撤销: 政策若改为 conventional, 请"
                f"回源重导出 (md → docx) 而不是在 docx 上逆向擦除")

    n_eq, numbers, widths, n_fb, n_sect_skip, multicol = \
        extract_numbers_and_wrap(root)
    stats["equations_wrapped"] = n_eq
    stats["equation_numbers"] = numbers
    stats["equation_widths"] = widths
    stats["equation_width_fallbacks"] = n_fb
    stats["equation_section_break_skips"] = n_sect_skip
    stats["equation_width_multicol"] = multicol
    if n_fb:
        fallback_w = OOXML_DEFAULT_PAGE_W - 2 * OOXML_DEFAULT_MARGIN
        stats["warnings"].append(
            f"[Step B] {n_fb} 处公式段无法判定所在节版心 (缺 sectPr/pgSz), 已按 "
            f"OOXML 缺省值处理 (页宽 {OOXML_DEFAULT_PAGE_W} − 左右边距 "
            f"{OOXML_DEFAULT_MARGIN}×2 = {fallback_w} twips)")
    if n_sect_skip:
        stats["warnings"].append(
            f"[Step B] {n_sect_skip} 处编号公式段同时是节末段 (pPr/sectPr), 已跳过"
            f"编号右顶格 (不包表): 把带节属性的段落搬进表格单元格会让 Word 拒绝"
            f"打开该 docx, 且节界归属会被静默挪动。请回源把节界改到空段/非公式段"
            f"之后再重导出")
    for note in multicol:
        stats["warnings"].append(
            f"[Step B] 公式段所在节是多栏节 ({note}) — **多栏版心未支持**: 包裹表"
            f"宽度按单栏版心 (pgSz−pgMar−gutter) 计算, 不是每栏实际可用宽; 请人工"
            f"核对编号是否右顶格, 或把该公式移到单栏节")

    # ---- Step B2: 独立 oMath + 普通文本编号 (S3 前向发现; 窄口径) ----
    # pandoc 少写 display 环境时, 公式段是 m:oMath + 普通文本 "(N)" (不是
    # m:oMathPara), Step B 不管它 → 原实现 0 处理却 exit 0, 呈现合格是假象。
    # 窄口径: 段内普通文本恰为 "(N)" → 包成同样的编号表 (并把 oMath 升级为居中
    # display); 其余形似形态只计数告警, 请回源改用 display 公式重导出。
    width_map2, note_map2 = _section_width_map(root)
    loose_wrapped, loose_skipped, loose_warn = wrap_standalone_math_numbers(
        root, width_map2, OOXML_DEFAULT_PAGE_W - 2 * OOXML_DEFAULT_MARGIN)
    stats["equations_wrapped_standalone"] = loose_wrapped
    stats["standalone_section_break_skips"] = loose_skipped
    stats["standalone_math_uncovered"] = loose_warn
    if loose_wrapped:
        stats["warnings"].append(
            f"[Step B2] {loose_wrapped} 处「独立 oMath + 普通文本编号」段落已按同一"
            f"制式包表 (窄口径: 段内普通文本恰为 \"(N)\"; 公式升级为居中 display)")
    if loose_skipped:
        stats["warnings"].append(
            f"[Step B2] {loose_skipped} 处此类段落同时是节末段 (pPr/sectPr), 已跳过"
            f"不包表 (同 Step B 的 Word 拒绝打开问题), 请回源调整节界")
    if loose_warn:
        stats["warnings"].append(
            f"[Step B2] {loose_warn} 处段落含独立 OMML 公式 + 尾部编号但**不是 display "
            f"公式段** (m:oMath 而非 m:oMathPara): 未覆盖, 编号未右顶格 — 请在 md 用 "
            f"$$…\\qquad (N)$$ display 公式重导出后重跑, 不要当已呈现合格")

    stats["threeline_tables"] = threeline_all(root)
    stats["fit_tables"] = fit_and_center(root)
    stats["cell_paragraphs"] = normalize_cell_paragraphs(root)
    cell_aligned, long_notes = align_cell_paragraphs(root)
    stats["cell_aligned"] = cell_aligned
    stats["long_text_columns"] = long_notes
    stats["figures_kept"] = keep_figure_with_caption(root)
    doc.save(str(path))
    return stats


def format_report(stats: dict) -> list:
    """把 process() 统计格式化为报告行 (CLI 与 export_final_docx 共用口径)。"""
    nums = stats.get("equation_numbers") or []
    nums_preview = ", ".join(nums[:10]) + ("…" if len(nums) > 10 else "") if nums else ""
    policy = stats.get("math_font_policy", POLICY_UNSPECIFIED)
    label = POLICY_LABELS.get(policy, policy)
    source = stats.get("math_font_source") or ""
    if policy == POLICY_UPRIGHT:
        a_detail = f"注入 m:sty=p {stats.get('upright_runs', 0)} 个"
    else:
        a_detail = "保持输入未注入 (本脚本不判定逐字符正斜)"
    widths = stats.get("equation_widths") or []
    width_note = ""
    if widths:
        shown = "/".join(str(w) for w in widths[:4]) + ("…" if len(widths) > 4 else "")
        width_note = f"; 表宽按所在节版心 {shown} twips"
        if stats.get("equation_width_fallbacks"):
            width_note += f" (另有 {stats['equation_width_fallbacks']} 处走缺省版心)"
    lines = [
        f"[Step A] 数学字体政策 {label}: {a_detail}"
        + (f" (来源 {source})" if source else " (未登记)"),
        f"[Step B] 公式编号右顶格: {stats.get('equations_wrapped', 0)} 处"
        + (f" (编号 {nums_preview})" if nums_preview else "") + width_note,
        f"[Step C] 数据表三线: {stats.get('threeline_tables', 0)} 张 (公式包裹表已跳过)",
        f"[Step D] 自适应+居中: {stats.get('fit_tables', 0)} 张 "
        f"(tblW=100% + jc=center + autofit + cantSplit)",
        f"[Step E] 单元格排版: {stats.get('cell_paragraphs', 0)} 段 "
        f"(零缩进/零段距/单倍行距)",
        f"[Step E2] 单元格对齐: {stats.get('cell_aligned', 0)} 段 "
        f"(短列居中/长文本列整列左对齐)",
        f"[Step F] 图与图注同页: {stats.get('figures_kept', 0)} 处 (keepNext)",
    ]
    for note in stats.get("long_text_columns") or []:
        lines.append(f"[Step E2] {note}")
    for warn in stats.get("warnings") or []:
        lines.append(f"[WARN] {warn}")
    if stats.get("backup_path"):
        note = "新建" if stats.get("backup_created") else "已存在未覆盖"
        lines.append(f"[备份] {stats['backup_path']} ({note})")
    return lines


def find_unprocessed_equation_numbers(docx_path) -> list:
    """检测 docx 是否未经呈现层后处理: body 直接子层存在尾部带 "(N)" 的公式段。

    两种形态都算未处理 (Step B/B2 处理后这些段落已移入表格, body 直接子层应为 0):
      ① 标准 display 公式段 (m:oMathPara) —— pandoc 正常产物;
      ② **独立 oMath + 普通文本编号** (S3 前向发现: 段内是 m:oMath 与 w:t 里的
         " (N)", 无 oMathPara) —— Step B2 能包表的窄口径形态 (段内普通文本恰为编号)。
    真编号判据与 Step B 完全同一 (NUMBERED_TAIL_RE, H1): f(1)/a+(2) 这类
    紧贴公式主体的括号不算未处理编号, 不误报。返回编号字符串列表。

    stdlib 实现 (zipfile + ElementTree), 不依赖 python-docx——docx_to_pdf.py
    的转换前警告用它, 不给纯转换环境新增依赖。
    """
    path = Path(docx_path)
    with ZipFile(path) as zf:
        xml_bytes = zf.read("word/document.xml")
    # XXE 防护: 正常 Word 导出的 document.xml 不含 DTD, 携带实体定义一律拒解析
    if b"<!DOCTYPE" in xml_bytes or b"<!ENTITY" in xml_bytes:
        raise ValueError("document.xml 含 DTD/实体定义, 拒绝解析 (XXE 防护)")
    root = ET.fromstring(xml_bytes)
    body = root.find(wq("body"))
    if body is None:
        return []
    numbers = []
    for p in body:
        if p.tag != wq("p"):
            continue
        if p.find(".//" + mq("oMathPara")) is not None:
            # 标准 display 公式段: 用 Step B 的真编号判据 (编号前须有幸存空白, H1)
            full = "".join(t.text or "" for t in p.findall(".//" + mq("t")))
            m = NUMBERED_TAIL_RE.search(full)
        elif p.find(mq("oMath")) is not None:
            # 形态 ② (B2): 编号是**普通文本**, 与公式间可有/无空白 → 独立判据:
            # 普通文本 (含嵌套) 尾部 "(N)"。与 Step B 的空白判据无关 (H1 不改)。
            plain = "".join(t.text or "" for t in p.findall(".//" + wq("t")))
            m = re.search(r"\((\d+)\)\s*$", plain)
        else:
            continue
        if m:
            numbers.append(m.group(1))
    return numbers


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台中文兜底
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(
        description="docx 呈现层统一后处理: 公式字体政策/编号右顶格 + 数据表三线/"
                    "自适应居中行禁拆/单元格排版对齐 (v3.1.0)")
    ap.add_argument("--docx", required=True, type=Path,
                    help="待处理 docx 路径 (必填; 导出链已默认自动执行本处理)")
    ap.add_argument("--math-font", choices=("auto",) + (POLICY_UPRIGHT,
                                                        POLICY_CONVENTIONAL),
                    default="auto",
                    help="数学字体正斜政策: auto (默认, 读 decision_log) | "
                         "upright 全局正体 (注入 m:sty=p) | conventional 保持输入 "
                         "(Word 默认: 字母斜体/算符数字正体); 政策未登记时保持输入"
                         "并警告, 不会把所有公式刷成斜体")
    ap.add_argument("--workspace", type=Path, default=None,
                    help="md 真源目录 (paper_workspace), 用于定位 "
                         "<workspace>/../state/decision_log.json; 缺省按 --docx 路径"
                         "上溯自动定位 state/decision_log.json")
    args = ap.parse_args(argv)

    if not args.docx.is_file():
        print(f"[FAIL] docx 不存在: {args.docx}")
        return 2
    stats = process(args.docx, workspace=args.workspace, math_font=args.math_font)
    for line in format_report(stats):
        print(line)
    print(f"[OK] 已写 {args.docx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
