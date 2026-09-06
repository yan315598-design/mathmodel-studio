# -*- coding: utf-8 -*-
"""draw.io 可编辑流程图生成器 · mxGraph XML builder（零第三方依赖, 1.3.0 版式令牌化）。

把"节点/连线"结构序列化为 draw.io 桌面版/网页版可直接打开编辑的 .drawio
文件（mxfile > diagram > mxGraphModel > root > mxCell 结构, 含 id=0/1 根节点）。
颜色一律取 templates/figures/style/palettes.py 的色板与中性色令牌
（references/design_tokens.md §1/§4/§5）, palettes.py 不可用时回退内联
academic_blue + NEUTRALS + 示意图色族 + 版式令牌最小副本。1.2.0 起示意图类
模板的阶段/泳道/卡片着色走 DIAGRAM_FAMILIES 浅底色族（与数据色板分类）,
card()/badge()/header_bar()/lane() 均支持 family= 族名（或族字典）:
不传 family 时保持既有配色行为（向后兼容）。

1.3.0（编辑级排版纪律, 蒸馏自 diagram-design (MIT) + sci-box (MIT)）:
  - snap4()            4px 网格捕捉（坐标/尺寸/间距硬规则）
  - card(focal=True)   焦点盒: 族 accent 底 + 族 stroke 描边 strong 档 2.0,
                       每图至多 DIAGRAM_FOCAL_MAX=2 个
  - 分数锚点           edge(..., exit_frac=/entry_frac=) 沿边 0..1 附着位;
                       fan_edges() 一分多自动按 k/(n+1) 扇形排开
  - mono 字体链        text(mono=True) / edge(mono_label=True),
                       仅数字/参数/公式标签（Consolas 优先）
  - 描边令牌对齐       族化 card/header_bar 默认描边对齐 DIAGRAM_STROKE_W
  - 版式门禁           finalize() 自动运行同目录 drawio_check.py
                       （FAIL 即退出码 1; MATHMODEL_DRAWIO_CHECK=0 关闭,
                       MATHMODEL_DRAWIO_STRICT=1 时 WARN 也判失败）

坐标约定: drawio 页面坐标原点在左上角, y 向下; 页面尺寸由 Diagram 的
page_width/page_height 写入 mxGraphModel, 布局留白 >= 40px。
渲染层级: 同一 Diagram 内先 add 的节点在下层, 模板应先加泳道/层带背景,
再加卡片/徽章（drawio 按文档顺序叠放）。

数据结构:
    Node   顶点: id/label/x/y/w/h/style
    Edge   连线: src/dst/style/label（可带出/入锚点方向 down/up/left/right
          与分数锚点 exit_frac/entry_frac）
    Diagram 一页画布: 节点/连线容器, write() 落盘 .drawio

便捷构造（Diagram 方法, 均创建并注册后返回 Node/Edge）:
    card()            圆角卡片; family= 族名时族 fill 底 + 族 stroke 描边 +
                      fontStyle=1 + #262626 墨黑加粗字（sci-box 风格串）;
                      focal=True 时为焦点盒（accent 底 + 2.0 描边）
    badge()           徽章; family= 族名时族 chevron 底 + 族 stroke 描边 +
                      墨黑加粗字（浅底旗标）
    lane()            泳道/层带底色框; family= 族名时族 fill 底
    header_bar()      列头横条; family= 族名时族 header 实色底 +
                      header_stroke 描边 + 白色加粗字
    dashed_container() 虚线分组容器（族 stroke, dashPattern=4 4, 无填充）
    band_sep()        点线分带框（dashPattern=1 3, 默认 DIAGRAM_PAGE band_sep）
    edge()            正交圆角连线 + block 箭头（可双向/虚线/带标签/锚定方向
                      与分数位置/等宽数字标签）
    fan_edges()       一分多扇出（附着点 k/(n+1) 自动均分）
    title()           图标题文本节点（无框, 16pt bold ink）
    text()            无框注释文字（次级色; mono=True 走等宽数字标签）

文字工具（复刻 figkit.char_width_px / wrap_text_balanced 的逻辑, 字号单位
与 drawio fontSize 直接映射）:
    char_width() / text_width() / wrap_text() / wrap_text_balanced()
    label_html()  换行结果拼 <br> 的 label（write 时统一 XML 转义）
    fit_text()    均衡换行 + 超高自动缩字号（下限 fs_min）, 溢出记 [警告]
    block_height() n 行文本的建议盒高

自验: write() 落盘后 validate_drawio_file()（stdlib minidom）复查 XML
合法性与节点/连线计数; finalize() 再跑 drawio_check.py 版式体检。

用法:
    from drawio_builder import Diagram
    d = Diagram(page_width=1220, page_height=900, name="技术路线图")
    d.title("title", "研究技术路线图", 0, 18, 1220, 34)
    d.card("layer1_node1", "节点一", 60, 120, 200, 60, family="blue")
    d.dashed_container("layer1_group", 50, 110, 220, 90, "blue")
    d.edge("layer1_node1", "layer2_node1", exit_dir="down", entry_dir="top")
    d.write("out/roadmap")            # -> out/roadmap.drawio

退出码约定（配合模板 CLI）: 0 成功; 1 版式门禁 FAIL; 2 参数/数据/IO 错误。
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# ============================================================
# 色板接入: 优先 import style/palettes.py, 失败回退内联最小副本
# ============================================================

_STYLE_DIR = Path(__file__).resolve().parents[2] / "style"
if str(_STYLE_DIR) not in sys.path:
    sys.path.insert(0, str(_STYLE_DIR))

try:
    from palettes import (
        NEUTRALS, get_palette, shade, tint, tint_series,
        get_diagram_family, get_diagram_families, get_diagram_page,
        DIAGRAM_ORDER_GENERIC, DIAGRAM_ORDER_ROADMAP,
        DIAGRAM_GRID, DIAGRAM_RADIUS, DIAGRAM_STROKE_W, DIAGRAM_FONT_RAMP,
        DIAGRAM_FONT_MONO, DIAGRAM_FOCAL_MAX, snap4,
    )

    _PALETTES_SOURCE = "style/palettes.py"
except Exception as _exc:  # noqa: BLE001 - 回退路径需要兜住一切导入问题
    print(f"[提示] 导入 palettes.py 失败({_exc}), drawio 生成器改用内联色板副本")
    _PALETTES_SOURCE = "内联副本"
    NEUTRALS = {
        "ink": "#1F2A36", "secondary": "#46535F", "faint": "#8A97A3",
        "grid": "#D9DEE4", "edge": "#C7D3DE", "edge_strong": "#A9BDD0",
        "arrow": "#6B7B8C", "panel_bg": "#F5F7FA", "hairline": "#E8ECF0",
        "white": "#FFFFFF",
    }
    # 内联回退色板: 与 style/palettes.py 及 figkit._PALETTES_FALLBACK 全量同步
    _FALLBACK_PALETTES: dict[str, list[str]] = {
        "academic_blue": ["#1F4E79", "#2E86AB", "#F18F01", "#C73E1D", "#3B8C6E", "#6C757D"],
        "cool_nature": ["#2C3E50", "#1F77B4", "#17A2B8", "#6C8EBF", "#D97706", "#C0392B"],
        "muted_earth": ["#506B84", "#A77A43", "#6E8B74", "#8B4F4A", "#7C8A96", "#39444D"],
        "okabe_ito": ["#0072B2", "#E69F00", "#009E73", "#D55E00",
                      "#CC79A7", "#56B4E9", "#F0E442", "#000000"],
        "npg": ["#E64B35", "#4DBBD5", "#00A087", "#3C5488",
                "#F39B7F", "#8491B4", "#91D1C2", "#DC0000", "#7E6148", "#B09C85"],
        "aaas": ["#3B4992", "#EE0000", "#008B45", "#631879",
                 "#008280", "#BB0021", "#5F559B", "#A20056", "#808180", "#1B1919"],
        "lancet": ["#00468B", "#ED0000", "#42B540", "#0099B4",
                   "#925E9F", "#FDAF91", "#AD002A", "#ADB6B6", "#1B1919"],
        "nejm": ["#BC3C29", "#0072B5", "#E18727", "#20854E",
                 "#7876B1", "#6F99AD", "#FFDC91", "#EE4C97"],
    }

    def get_palette(name: str | None = None) -> list[str]:
        """内联回退: 全 8 套色板 + 别名, 语义同 palettes.get_palette。"""
        key = (name or "academic_blue").lower()
        alias = {"champion_palette": "academic_blue", "nature": "npg", "science": "aaas"}
        key = alias.get(key, key)
        if key not in _FALLBACK_PALETTES:
            raise ValueError(
                f"内联回退色板仅含: {sorted(_FALLBACK_PALETTES)}, 未知色板 '{name}'")
        return list(_FALLBACK_PALETTES[key])

    def _mix(hex_color: str, factor: float, toward: int) -> str:
        text = hex_color.strip().lstrip("#")
        r, g, b = (int(text[i:i + 2], 16) for i in (0, 2, 4))
        f = min(max(factor, 0.0), 1.0)
        return "#{:02X}{:02X}{:02X}".format(
            *(round(c + (toward - c) * f) for c in (r, g, b)))

    def tint(hex_color: str, factor: float) -> str:
        """向白混合（内联回退实现, 逻辑同 palettes.tint）。"""
        return _mix(hex_color, factor, 255)

    def shade(hex_color: str, factor: float) -> str:
        """向黑混合（内联回退实现, 逻辑同 palettes.shade）。"""
        return _mix(hex_color, factor, 0)

    def tint_series(hex_color: str, n: int,
                    lo: float = 0.80, hi: float = 0.42) -> list[str]:
        """n 级等差浅化序列（内联回退实现, 逻辑同 palettes.tint_series）。"""
        if n < 1:
            raise ValueError("n 必须 >= 1")
        if n == 1:
            return [tint(hex_color, hi)]
        step = (lo - hi) / (n - 1)
        return [tint(hex_color, lo - i * step) for i in range(n)]

    # ---- 内联示意图色族副本: 与 style/palettes.py DIAGRAM_FAMILIES 全量同步 ----
    # 色值 1:1 蒸馏自 sci-box scibox-diagram (MIT)
    DIAGRAM_FAMILIES: dict[str, dict[str, str]] = {
        "blue":   {"fill": "#EEF6FD", "stroke": "#3B547F", "accent": "#B6D8F6", "deep": "#A8C0EA",
                   "header": "#4060B0", "header_stroke": "#2C4488", "edge": "#1F3F6B", "chevron": "#98D0ED"},
        "orange": {"fill": "#FCEAD9", "stroke": "#C08B5C", "accent": "#FDDECD", "deep": "#F8D0B0",
                   "header": "#D06818", "header_stroke": "#A04E10", "edge": "#7B5530", "chevron": "#F8D5B3"},
        "purple": {"fill": "#E5DFEB", "stroke": "#9B979F", "accent": "#CCC2DB", "deep": "#C8C1D9",
                   "header": "#8D84A8", "header_stroke": "#6E6584", "edge": "#7F5FAF", "chevron": "#C8C1D9"},
        "teal":   {"fill": "#DBEEF4", "stroke": "#668D89", "accent": "#BAE2E4", "deep": "#A8E0E0",
                   "header": "#1F6F6F", "header_stroke": "#14504F", "edge": "#5F8484", "chevron": "#D4EAE4"},
        "green":  {"fill": "#E6F4DC", "stroke": "#6A9A4A", "accent": "#C8E8B0", "deep": "#C8E8B0",
                   "header": "#3A5A22", "header_stroke": "#2A4318", "edge": "#3A5A22", "chevron": "#D8EEC8"},
        "olive":  {"fill": "#FBF3D2", "stroke": "#B8A23A", "accent": "#F6E6A4", "deep": "#F6E6A4",
                   "header": "#8A7A1A", "header_stroke": "#665A12", "edge": "#665A12", "chevron": "#F6E6A4"},
        "grey":   {"fill": "#F2F4F6", "stroke": "#8A97A3", "accent": "#DDE4EA", "deep": "#D9D9D9",
                   "header": "#5B6B78", "header_stroke": "#46535F", "edge": "#5B6B78", "chevron": "#E4E9EE"},
    }
    DIAGRAM_PAGE = {
        "bg": "#F2EEF7", "ink": "#262626", "title_bar": "#4F80BD",
        "band_sep": "#5B6B78", "frame": "#808080", "loop_arrow": "#CCCCD6",
        "white": "#FFFFFF",
    }
    DIAGRAM_ORDER_GENERIC = ["blue", "teal", "olive", "orange", "purple", "green", "grey"]
    DIAGRAM_ORDER_ROADMAP = ["blue", "blue", "orange", "purple", "teal"]

    def get_diagram_family(name: str) -> dict[str, str]:
        """内联回退: 取一枝示意图色族, 语义同 palettes.get_diagram_family。"""
        key = str(name).strip().lower()
        if key not in DIAGRAM_FAMILIES:
            raise ValueError(
                f"内联色族副本仅含: {sorted(DIAGRAM_FAMILIES)}, 未知色族 '{name}'")
        return dict(DIAGRAM_FAMILIES[key])

    def get_diagram_families(order: list[str] | None = None,
                             n: int | None = None) -> list[dict[str, str]]:
        """内联回退: 按序取 n 族, 语义同 palettes.get_diagram_families。"""
        seq = list(order) if order is not None else list(DIAGRAM_ORDER_GENERIC)
        if not seq:
            raise ValueError("order 不能为空列表")
        if n is not None:
            if n < 1:
                raise ValueError(f"n 必须 >= 1, 实际 {n}")
            seq = [seq[i % len(seq)] for i in range(n)]
        return [get_diagram_family(k) for k in seq]

    def get_diagram_page(token: str) -> str:
        """内联回退: 取示意图页面令牌, 语义同 palettes.get_diagram_page。"""
        if token not in DIAGRAM_PAGE:
            raise ValueError(
                f"内联页面令牌仅含: {sorted(DIAGRAM_PAGE)}, 未知令牌 '{token}'")
        return DIAGRAM_PAGE[token]

    # ---- 1.3.0/1.3.1 版式令牌内联副本: 与 style/palettes.py 全量同步 ----
    # （蒸馏自 diagram-design, MIT: 4px 网格/圆角 ≤10/描边四档/扁平字阶/mono 专用）
    DIAGRAM_GRID = 4
    DIAGRAM_RADIUS = {"sm": 4, "md": 6, "lg": 8}
    DIAGRAM_STROKE_W = {"hairline": 0.8, "card": 1.0, "default": 1.2, "strong": 2.0}
    DIAGRAM_FONT_RAMP = {"title": 16, "header": 12, "body": 10.5, "note": 9}
    DIAGRAM_FONT_MONO = ["Consolas", "DejaVu Sans Mono", "Courier New"]
    DIAGRAM_FOCAL_MAX = 2

    def snap4(value: float, grid: int = DIAGRAM_GRID) -> float:
        """内联回退: 4px 网格捕捉, 语义同 palettes.snap4。"""
        if grid <= 0:
            raise ValueError(f"grid 必须为正, 实际 {grid}")
        snapped = round(value / grid) * grid
        return int(snapped) if snapped == int(snapped) else float(snapped)


def neutral(name: str) -> str:
    """按令牌名取中性色（design_tokens.md §1.2, 统一走 NEUTRALS）。"""
    try:
        return NEUTRALS[name]
    except KeyError:
        raise ValueError(
            f"未知中性色令牌 '{name}'. 可用: {sorted(NEUTRALS)}") from None


FONT_FAMILY = "Microsoft YaHei,PingFang SC,Hiragino Sans GB,Helvetica"   # sci-box style 串字体族
FONT_MONO = ",".join(DIAGRAM_FONT_MONO)  # 等宽链: 仅数字/参数/公式标签, 不给节点名
DIAGRAM_INK = "#262626"            # sci-box 墨黑（族化盒内文字默认色）


def _resolve_family(family) -> dict[str, str]:
    """family 参数归一化: 族名（str）→ 族字典; 传字典原样返回。

    Raises:
        ValueError: 族名未注册。
    """
    if isinstance(family, dict):
        return family
    return get_diagram_family(family)

# ============================================================
# CJK 感知文字宽度与均衡换行（复刻 figkit.char_width_px / wrap_text_balanced）
# ============================================================
CHAR_WIDE = 1.45    # 全角字符 ≈ 1.45×字号
CHAR_HALF = 0.72    # 半角字符 ≈ 0.72×字号
CHAR_NARROW = 0.50  # 窄半角 (i l j t f . , : ; ' ! 空格)
LINE_PITCH = 1.5    # 多行文本行距系数（drawio 字号单位直接映射）


def char_width(ch: str, fontsize: float) -> float:
    """估算单字符显示宽: 全角≈1.45×字号, 半角≈0.72×字号,
    窄半角≈0.5×字号（经验值, 免 GUI 测量, 与 figkit.char_width_px 一致）。"""
    if ord(ch) > 0x2E7F:  # CJK 及全角符号区间
        return fontsize * CHAR_WIDE
    if ch in "iljtf.,:;'! ":
        return fontsize * CHAR_NARROW
    return fontsize * CHAR_HALF


def text_width(text: str, fontsize: float) -> float:
    """估算整串显示宽。"""
    return sum(char_width(c, fontsize) for c in text)


def wrap_text(text: str, max_width: float, fontsize: float) -> list[str]:
    """贪心换行: 逐字符累积, 超宽断行; 返回行列表。"""
    lines: list[str] = []
    current, current_w = "", 0.0
    for ch in text:
        w = char_width(ch, fontsize)
        if current and current_w + w > max_width:
            lines.append(current)
            current, current_w = ch, w
        else:
            current += ch
            current_w += w
    if current:
        lines.append(current)
    return lines or [""]


def wrap_text_balanced(text: str, max_width: float,
                       fontsize: float) -> list[str]:
    """均衡换行: 在贪心行数不变的前提下让各行宽度尽量接近, 消除吊行。

    做法: 先贪心得行数 n; 再以 总宽/n × 1.15 为目标宽度重新贪心,
    若行数不变则采用, 否则回退贪心结果（与 figkit.wrap_text_balanced 一致）。
    """
    greedy = wrap_text(text, max_width, fontsize)
    if len(greedy) <= 1:
        return greedy
    target = text_width(text, fontsize) / len(greedy) * 1.15
    if target >= max_width:
        return greedy
    balanced = wrap_text(text, target, fontsize)
    return balanced if len(balanced) == len(greedy) else greedy


def label_html(lines: list[str]) -> str:
    """把换行结果拼成 drawio label（html=1 下 <br> 即换行, XML 转义由写出统一处理）。"""
    return "<br>".join(lines)


def block_height(n_lines: int, fontsize: float, pitch: float = LINE_PITCH,
                 pad: float = 12.0, min_h: float = 0.0) -> float:
    """n 行文本的建议盒高（含上下留白, 不低于 min_h）。"""
    return max(n_lines * fontsize * pitch + pad, min_h)


def fit_text(text: str, max_w: float, fs: float, fs_min: float, *,
             max_h: float | None = None, max_lines: int | None = None,
             pitch: float = LINE_PITCH, pad: float = 12.0,
             ctx: str = "", warnings: list[str] | None = None
             ) -> tuple[list[str], float]:
    """均衡换行 + 溢出自动缩字号（下限 fs_min）, 返回 (行列表, 最终字号)。

    Args:
        text: 原始文本（不含换行符）。
        max_w: 单行最大显示宽（已扣除盒内左右留白）。
        fs / fs_min: 起始字号 / 最小字号。
        max_h / max_lines: 溢出判据, 至少给一项（盒内可用高 / 最大行数）。
        ctx: 警告文案里的定位前缀（如 "层 2 节点 3"）。
        warnings: 警告收集列表; None 时不收集。
    """
    if max_h is None and max_lines is None:
        raise ValueError("fit_text 需要 max_h 或 max_lines 至少一项")

    def overflow(lines: list[str], size: float) -> bool:
        if max_h is not None:
            return block_height(len(lines), size, pitch, pad) > max_h
        return len(lines) > (max_lines or 0)

    lines = wrap_text_balanced(text, max_w, fs)
    while overflow(lines, fs) and fs > fs_min:
        fs = max(round(fs - 0.5, 1), fs_min)
        lines = wrap_text_balanced(text, max_w, fs)
    if overflow(lines, fs) and warnings is not None:
        warnings.append(
            f"{ctx} 文字过长: 缩至最小字号 {fs_min:.1f} 后仍放不下, 建议精简文案"
        )
    return lines, fs


# ============================================================
# 数据结构
# ============================================================
@dataclass
class Node:
    """drawio 顶点: id 语义化命名（如 layer1_node2）, label 可含 <br>。"""

    id: str
    label: str
    x: float
    y: float
    w: float
    h: float
    style: str


@dataclass
class Edge:
    """drawio 连线: src/dst 为 Node id, 可带出/入锚点方向便于正交路由。

    exit_frac/entry_frac（1.3.0）: 与方向联用的分数锚点（0..1 沿边比例）,
    多条连线共用一条盒边时按 k/(n+1) 扇形排开（diagram-design 连接器
    纪律 4: 任何两条连线不共享同一附着点, 间距 ≥12px）。
    """

    src: str
    dst: str
    style: str = ""
    label: str = ""
    exit_dir: str | None = None    # "down"/"up"/"left"/"right"
    entry_dir: str | None = None   # "top"/"bottom"/"left"/"right"
    id: str = ""                   # 空则自动生成 edge_<src>__<dst>_N
    exit_frac: float | None = None   # 沿 exit_dir 边的 0..1 附着位置
    entry_frac: float | None = None  # 沿 entry_dir 边的 0..1 附着位置


# 连接锚点: 方向 → (相对 x, 相对 y)
_ANCHORS = {
    "down": (0.5, 1.0), "up": (0.5, 0.0),
    "left": (0.0, 0.5), "right": (1.0, 0.5),
    "top": (0.5, 0.0), "bottom": (0.5, 1.0),
}


def _num(value: float) -> str:
    """数值转简洁字符串（整数值去小数, 其余保留 1 位）。"""
    rounded = round(value, 1)
    return str(int(rounded)) if rounded == int(rounded) else f"{rounded:.1f}"


def _esc(text: str) -> str:
    """XML 属性转义（手写以精确控制, & 必须最先替换）。"""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;"))


def _font_bits(font_size: float, color: str, bold: bool = False,
               align: str = "center", valign: str = "middle") -> list[str]:
    """字体样式片段: 字族/字号/字色/字重/对齐（design_tokens.md §2）。"""
    parts = [f"fontFamily={FONT_FAMILY}", f"fontSize={_num(font_size)}",
             f"fontColor={color}"]
    if bold:
        parts.append("fontStyle=1")
    parts.append(f"align={align}")
    parts.append(f"verticalAlign={valign}")
    return parts


class Diagram:
    """一页 drawio 画布: 有序节点/连线容器, write() 输出标准 .drawio。"""

    def __init__(self, page_width: float = 1169, page_height: float = 826,
                 name: str = "流程图") -> None:
        page_width, page_height = float(page_width), float(page_height)
        if not math.isfinite(page_width) or page_width <= 0:
            raise ValueError(f"page_width 须为正有限数, 实际: {page_width}")
        if not math.isfinite(page_height) or page_height <= 0:
            raise ValueError(f"page_height 须为正有限数, 实际: {page_height}")
        self.page_width = page_width
        self.page_height = page_height
        self.name = name
        self.nodes: list[Node] = []
        self.edges: list[Edge] = []
        self._index: dict[str, Node] = {}

    # ---------- 注册与查询 ----------
    @property
    def node_count(self) -> int:
        """顶点数（不含 id=0/1 根节点）。"""
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """连线数。"""
        return len(self.edges)

    def add_node(self, node: Node) -> Node:
        """注册顶点; id 重复或几何非法(非有限/非正尺寸)时抛 ValueError。"""
        if not node.id or not str(node.id).strip():
            raise ValueError(f"节点 id 不能为空: {node!r}")
        if node.id in ("0", "1"):
            raise ValueError(f"节点 id {node.id!r} 与 mxGraph 根节点冲突")
        if node.id in self._index:
            raise ValueError(f"节点 id 重复: {node.id!r}")
        if not (math.isfinite(node.x) and math.isfinite(node.y)):
            raise ValueError(f"节点 {node.id!r} 坐标须为有限数: x={node.x}, y={node.y}")
        if not (math.isfinite(node.w) and math.isfinite(node.h)):
            raise ValueError(f"节点 {node.id!r} 尺寸须为有限数: w={node.w}, h={node.h}")
        if node.w <= 0 or node.h <= 0:
            raise ValueError(f"节点 {node.id!r} 尺寸必须为正: w={node.w}, h={node.h}")
        self._index[node.id] = node
        self.nodes.append(node)
        return node

    def node(self, node_id: str) -> Node:
        """按 id 取顶点; 不存在时抛 ValueError。"""
        try:
            return self._index[node_id]
        except KeyError:
            raise ValueError(f"未知节点 id: {node_id!r}") from None

    def add_edge(self, edge: Edge) -> Edge:
        """注册连线; src/dst 必须已存在, 锚点方向非法时抛 ValueError。

        exit_frac/entry_frac 与方向联用: 沿该方向边的 0..1 比例处附着
        （down/bottom: exitX=frac,exitY=1; up/top: exitX=frac,exitY=0;
        left: exitX=0,exitY=frac; right: exitX=1,exitY=frac）;
        不给 frac 时保持边中点（1.2.0 行为）。
        """
        for endpoint in (edge.src, edge.dst):
            if endpoint not in self._index:
                raise ValueError(f"连线端点 {endpoint!r} 未注册（先 add 节点再连线）")
        style = edge.style.rstrip(";")

        def _anchor(dir_name: str, frac: float | None, prefix: str) -> str:
            if dir_name not in _ANCHORS:
                raise ValueError(
                    f"{prefix}_dir 非法: {dir_name!r}, 合法值: {sorted(_ANCHORS)}")
            if frac is not None and not (0.0 <= frac <= 1.0):
                raise ValueError(f"{prefix}_frac 须在 [0,1], 实际 {frac}")
            x, y = _ANCHORS[dir_name]
            if frac is not None:
                if dir_name in ("left", "right"):
                    y = frac          # 竖直边: frac 沿 y
                else:
                    x = frac          # 水平边: frac 沿 x
            return (f";{prefix}X={_num(x)};{prefix}Y={_num(y)}"
                    f";{prefix}Dx=0;{prefix}Dy=0")

        if edge.exit_dir:
            style += _anchor(edge.exit_dir, edge.exit_frac, "exit")
        if edge.entry_dir:
            style += _anchor(edge.entry_dir, edge.entry_frac, "entry")
        edge.style = style
        self.edges.append(edge)
        return edge

    # ---------- 便捷构造（创建 + 注册 + 返回） ----------
    def card(self, node_id: str, label: str, x: float, y: float,
             w: float, h: float, *, font_size: float = 10.5,
             fill: str | None = None, stroke: str | None = None,
             text_color: str | None = None, bold: bool | None = None,
             stroke_width: float | None = None, dashed: bool = False,
             family=None, focal: bool = False) -> Node:
        """圆角卡片, arcSize=8（design_tokens.md §4 / sci-box 风格串）。

        family 给族名（或族字典）时: 族 fill 底 + 族 stroke 描边 +
        fontStyle 按 bold 参数 + #262626 墨黑字（sci-box 扁平卡片）, 描边默认
        对齐描边令牌 card 档 1.0（1.3.1 降重; focal 焦点盒为 strong 档 2.0）;
        显式传入的 fill/stroke/text_color/bold/stroke_width 仍可覆盖族默认。
        1.3.1 起族化卡默认 **常规字重**（bold=False）——加粗只给标题条/
        徽章/卡片标题, 全字加粗会把层级抹平（design_tokens §4.5）。
        不传 family 保持白底 + edge 描边 + 常规墨字（1.1.0 行为, 向后兼容,
        描边默认 1.0）。

        focal=True（1.3.0, diagram-design focal rule）: 焦点盒 = 族 accent
        底 + 族 stroke 描边 strong 档 2.0。每图至多 2 个焦点, 超过等于
        没有焦点（DIAGRAM_FOCAL_MAX）。
        """
        if family is not None:
            fam = _resolve_family(family)
            if focal:
                fill = fill or fam["accent"]
            else:
                fill = fill or fam["fill"]
            stroke = stroke or fam["stroke"]
            text_color = text_color or DIAGRAM_INK
            bold = False if bold is None else bold
        if stroke_width is None:
            if focal:
                stroke_width = DIAGRAM_STROKE_W["strong"]
            else:
                stroke_width = (DIAGRAM_STROKE_W["card"] if family is not None
                                else 1.0)
        parts = ["rounded=1", "arcSize=8", "whiteSpace=wrap", "html=1",
                 f"fillColor={fill or neutral('white')}",
                 f"strokeColor={stroke or neutral('edge')}",
                 f"strokeWidth={_num(stroke_width)}"]
        if dashed:
            parts.append("dashed=1")
        parts += _font_bits(font_size, text_color or neutral("ink"),
                            True if bold else False)
        return self.add_node(Node(node_id, label, x, y, w, h,
                                  ";".join(parts) + ";"))

    def badge(self, node_id: str, label: str, x: float, y: float,
              w: float, h: float, *, fill: str | None = None,
              shape: str = "round", font_size: float = 11,
              text_color: str | None = None, bold: bool = True,
              stroke: str | None = None,
              stroke_width: float = 1.0, family=None) -> Node:
        """徽章: shape="round" 圆角矩形 / "ellipse" 圆形。

        默认深底白字（色板第 1 色）; family 给族名（或族字典）时改为
        族 chevron 浅底 + 族 stroke 描边 + #262626 墨黑加粗字
        （sci-box 浅底旗标, 不再深底白字）。
        """
        head = (["ellipse=1"] if shape == "ellipse"
                else ["rounded=1", "arcSize=8"])
        if family is not None:
            fam = _resolve_family(family)
            fill = fill or fam["chevron"]
            stroke = stroke or fam["stroke"]
            text_color = text_color or DIAGRAM_INK
        parts = head + ["whiteSpace=wrap", "html=1",
                        f"fillColor={fill or get_palette(None)[0]}",
                        f"strokeColor={stroke or fill or get_palette(None)[0]}",
                        f"strokeWidth={_num(stroke_width)}"]
        parts += _font_bits(font_size, text_color or neutral("white"), bold)
        return self.add_node(Node(node_id, label, x, y, w, h,
                                  ";".join(parts) + ";"))

    def lane(self, node_id: str, x: float, y: float, w: float, h: float, *,
             fill: str | None = None, stroke: str = "none",
             stroke_width: float = 1.0, family=None) -> Node:
        """泳道/层带底色框: 默认 panel_bg 纯色无描边（§4 层带规范）。

        family 给族名（或族字典）时底色取族 fill（浅底色带）。
        """
        if family is not None:
            fill = fill or _resolve_family(family)["fill"]
        parts = ["rounded=0", "whiteSpace=wrap", "html=1",
                 f"fillColor={fill or neutral('panel_bg')}",
                 f"strokeColor={stroke}"]
        if stroke != "none":
            parts.append(f"strokeWidth={_num(stroke_width)}")
        return self.add_node(Node(node_id, "", x, y, w, h, ";".join(parts) + ";"))

    def header_bar(self, node_id: str, label: str, x: float, y: float,
                   w: float, h: float, *, fill: str | None = None,
                   font_size: float = 12, stroke: str | None = None,
                   stroke_width: float | None = None, family=None) -> Node:
        """列头横条: 实色底 + 白色加粗字（§4 徽章/列头规范）。

        默认色板第 1 色; family 给族名（或族字典）时取族 header 实色底 +
        header_stroke 描边（sci-box TONES 标题条）, 描边默认对齐令牌
        default 档 1.2（不传 family 保持 1.0 向后兼容）。
        """
        if family is not None:
            fam = _resolve_family(family)
            fill = fill or fam["header"]
            stroke = stroke or fam["header_stroke"]
        if stroke_width is None:
            stroke_width = DIAGRAM_STROKE_W["default"] if family is not None else 1.0
        color = fill or get_palette(None)[0]
        parts = ["rounded=1", "arcSize=8", "whiteSpace=wrap", "html=1",
                 f"fillColor={color}", f"strokeColor={stroke or color}",
                 f"strokeWidth={_num(stroke_width)}"]
        parts += _font_bits(font_size, neutral("white"), bold=True)
        return self.add_node(Node(node_id, label, x, y, w, h,
                                  ";".join(parts) + ";"))

    def dashed_container(self, node_id: str, x: float, y: float, w: float,
                         h: float, family=None, *, stroke: str | None = None,
                         stroke_width: float = 1.2) -> Node:
        """虚线分组容器: fillColor=none + dashed=1 + dashPattern=4 4。

        描边默认取 family 的 stroke 色（族名或族字典）; 显式 stroke 可覆盖。
        """
        if family is not None:
            stroke = stroke or _resolve_family(family)["stroke"]
        if stroke is None:
            raise ValueError("dashed_container 需要 family 或 stroke 之一")
        parts = ["rounded=0", "whiteSpace=wrap", "html=1", "fillColor=none",
                 f"strokeColor={stroke}", f"strokeWidth={_num(stroke_width)}",
                 "dashed=1", "dashPattern=4 4"]
        return self.add_node(Node(node_id, "", x, y, w, h, ";".join(parts) + ";"))

    def band_sep(self, node_id: str, x: float, y: float, w: float, h: float,
                 *, color: str | None = None, stroke_width: float = 1.0) -> Node:
        """点线分带框: fillColor=none + dashPattern=1 3（sci-box 分带参考线）。

        默认取 DIAGRAM_PAGE 的 band_sep 令牌色。
        """
        parts = ["rounded=0", "whiteSpace=wrap", "html=1", "fillColor=none",
                 f"strokeColor={color or get_diagram_page('band_sep')}",
                 f"strokeWidth={_num(stroke_width)}",
                 "dashed=1", "dashPattern=1 3"]
        return self.add_node(Node(node_id, "", x, y, w, h, ";".join(parts) + ";"))

    def title(self, node_id: str, text: str, x: float, y: float,
              w: float, h: float, *, font_size: float = 16,
              color: str | None = None) -> Node:
        """图标题: 无框居中文本, 16pt bold ink（§4 标题规范）。"""
        return self.text(node_id, text, x, y, w, h, font_size=font_size,
                         color=color or neutral("ink"), bold=True)

    def text(self, node_id: str, text: str, x: float, y: float,
             w: float, h: float, *, font_size: float = 9,
             color: str | None = None, bold: bool = False,
             align: str = "center", mono: bool = False) -> Node:
        """无框注释文字（默认 9pt secondary, 下限 8pt 见 §2）。

        mono=True（1.3.0）: 等宽字体链, 仅用于数字/参数/公式标签
        （如 "RMSE=2.31"）; 节点名/说明文字不给 mono（diagram-design
        纪律: mono 是"技术性内容"专用, 不是 blanket dev 风）。
        """
        parts = ["text", "html=1", "strokeColor=none", "fillColor=none",
                 "whiteSpace=wrap", "rounded=0"]
        parts += _font_bits(font_size, color or neutral("secondary"),
                            bold, align=align)
        if mono:
            parts = [p for p in parts if not p.startswith("fontFamily=")]
            parts.append(f"fontFamily={FONT_MONO}")
        return self.add_node(Node(node_id, text, x, y, w, h,
                                  ";".join(parts) + ";"))

    def edge(self, src: str, dst: str, *, label: str = "",
             stroke: str | None = None, dashed: bool = False,
             bidirectional: bool = False, no_arrow: bool = False,
             stroke_width: float = 1.3, font_size: float = 9,
             exit_dir: str | None = None, entry_dir: str | None = None,
             exit_frac: float | None = None, entry_frac: float | None = None,
             mono_label: bool = False, edge_id: str = "") -> Edge:
        """正交圆角连线: 默认 block 箭头 + arrow 令牌描边（§4 连接器规范）。

        Args:
            exit_dir/entry_dir: 锚点方向 down/up/left/right（entry 亦接受
                top/bottom 别名）, 给定时连线端点确定, 便于层间下行/栏间右行。
            exit_frac/entry_frac: 分数锚点（1.3.0）: 多条连线共用一条盒边时
                按 k/(n+1) 扇形排开, 不共享同一附着点（diagram-design 纪律 4）;
                可直接用 fan_edges() 自动分配。
            bidirectional: 双向箭头（机理图数据流）。
            no_arrow: 无箭头纯连线（背景引导线/母线干段）。
            mono_label: 边标签用等宽字体（仅数字/参数标签）。
        """
        parts = ["edgeStyle=orthogonalEdgeStyle", "rounded=1", "html=1",
                 "jettySize=auto", "orthogonalLoop=1",
                 f"strokeColor={stroke or neutral('arrow')}",
                 f"strokeWidth={_num(stroke_width)}"]
        if no_arrow:
            parts += ["endArrow=none", "endFill=0"]
        else:
            parts += ["endArrow=block", "endFill=1"]
        if bidirectional:
            parts += ["startArrow=block", "startFill=1"]
        if dashed:
            parts.append("dashed=1")
        label_font = FONT_MONO if mono_label else FONT_FAMILY
        parts += [f"fontFamily={label_font}", f"fontSize={_num(font_size)}",
                  f"fontColor={neutral('secondary')}",
                  f"labelBackgroundColor={neutral('white')}"]
        return self.add_edge(Edge(src, dst, ";".join(parts) + ";", label,
                                  exit_dir, entry_dir, edge_id,
                                  exit_frac, entry_frac))

    def fan_edges(self, src: str, dsts: list[str], *,
                  exit_dir: str = "down", entry_dir: str = "top",
                  family=None, labels: list[str] | None = None,
                  **edge_kw) -> list[Edge]:
        """一分多扇出: 源盒一条边上的 n 个附着点按 k/(n+1) 均匀扇开。

        sci-box 连接器纪律: 一分多不画 N 条从同一点出发的斜线;
        diagram-design 纪律 4: 共边多连线附着点间距 ≥12px
        （k/(n+1) 均分, 调用方保证盒宽足够）。family 给族名时连线取族
        edge 色（跨族不混色）。返回创建的 Edge 列表。
        """
        n = len(dsts)
        if n < 1:
            raise ValueError("dsts 不能为空")
        fracs = [(k + 1) / (n + 1) for k in range(n)]
        stroke = edge_kw.pop("stroke", None)
        if family is not None:
            stroke = stroke or _resolve_family(family)["edge"]
        created = []
        for i, dst in enumerate(dsts):
            created.append(self.edge(
                src, dst,
                label=(labels[i] if labels else ""),
                stroke=stroke,
                exit_dir=exit_dir, entry_dir=entry_dir,
                exit_frac=fracs[i], **edge_kw))
        return created

    def rich_card(self, node_id: str, title: str, detail: str,
                  x: float, y: float, w: float, h: float, *,
                  family, title_fs: float | None = None,
                  detail_fs: float | None = None, focal: bool = False,
                  detail_mono: bool = False) -> Node:
        """两段式富文本卡（1.3.1）: bold 标题行 + regular 明细行（次级色小字）。

        信息密度来自内容结构而不是加粗: 单元格级 fontStyle=0, 标题经
        <b> 加粗, 明细经 <font> 降档（note 档 9px, 次级色 #46535F）;
        detail_mono=True 且明细为纯 ASCII 时明细走等宽链（mono 无中文字形,
        含中文自动回退 sans）。detail 为空串时退化为加粗单行卡。

        focal=True 时焦点盒: 族 accent 底 + strong 档 2.0 描边（每图 ≤2 个）。
        """
        fam = _resolve_family(family)
        if title_fs is None:
            title_fs = DIAGRAM_FONT_RAMP["body"]
        if detail_fs is None:
            detail_fs = DIAGRAM_FONT_RAMP["note"]
        if detail_mono and any(ord(c) > 0x2E7F for c in detail):
            detail_mono = False
        if detail.strip():
            detail_style = f"font-size:{_num(detail_fs)}px"
            detail_face = (f' face="{FONT_MONO}"' if detail_mono else "")
            label = (f"<b>{title}</b><br>"
                     f"<font{detail_face} style=\"{detail_style}\" "
                     f"color=\"{neutral('secondary')}\">{detail}</font>")
        else:
            label = f"<b>{title}</b>"
        parts = ["rounded=1", "arcSize=8", "whiteSpace=wrap", "html=1",
                 f"fillColor={fam['accent'] if focal else fam['fill']}",
                 f"strokeColor={fam['stroke']}",
                 f"strokeWidth={_num(DIAGRAM_STROKE_W['strong'] if focal else DIAGRAM_STROKE_W['card'])}"]
        parts += _font_bits(title_fs, DIAGRAM_INK, bold=False)
        return self.add_node(Node(node_id, label, x, y, w, h,
                                  ";".join(parts) + ";"))

    def vlabel(self, node_id: str, text: str, x: float, y: float,
               w: float, h: float, *, font_size: float = 9,
               color: str | None = None, bold: bool = False) -> Node:
        """竖排标签（1.3.1）: 逐字 <br> 堆叠, 禁用 horizontal=0
        （sci-box 纪律: 旋转会让中文躺倒）。用于色带右侧阶段目标标注。"""
        return self.text(node_id, "<br>".join(text), x, y, w, h,
                         font_size=font_size, color=color, bold=bold)

    # ---------- 序列化 ----------
    def to_xml(self) -> str:
        """手写拼 mxGraph XML（属性值统一 _esc 转义, 含中文/引号安全）。"""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<mxfile host="mathmodel-studio" type="device">',
            f'  <diagram id="drawio-page-1" name="{_esc(self.name)}">',
            f'    <mxGraphModel dx="1000" dy="700" grid="1" gridSize="10"'
            ' guides="1" tooltips="1" connect="1" arrows="1" fold="1"'
            ' page="1" pageScale="1"'
            f' pageWidth="{_num(self.page_width)}"'
            f' pageHeight="{_num(self.page_height)}"'
            ' math="0" shadow="0">',
            "      <root>",
            '        <mxCell id="0" />',
            '        <mxCell id="1" parent="0" />',
        ]
        for node in self.nodes:
            lines += [
                f'        <mxCell id="{_esc(node.id)}" value="{_esc(node.label)}"'
                f' style="{_esc(node.style)}" vertex="1" parent="1">',
                f'          <mxGeometry x="{_num(node.x)}" y="{_num(node.y)}"'
                f' width="{_num(node.w)}" height="{_num(node.h)}"'
                ' as="geometry" />',
                "        </mxCell>",
            ]
        for i, edge in enumerate(self.edges, start=1):
            cell_id = edge.id or f"edge_{edge.src}__{edge.dst}_{i}"
            lines += [
                f'        <mxCell id="{_esc(cell_id)}" value="{_esc(edge.label)}"'
                f' style="{_esc(edge.style)}" edge="1" parent="1"'
                f' source="{_esc(edge.src)}" target="{_esc(edge.dst)}">',
                '          <mxGeometry relative="1" as="geometry" />',
                "        </mxCell>",
            ]
        lines += [
            "      </root>",
            "    </mxGraphModel>",
            "  </diagram>",
            "</mxfile>",
        ]
        return "\n".join(lines) + "\n"

    def write(self, path) -> Path:
        """写出 .drawio 文件（前缀自动补 .drawio 后缀）, 返回实际路径。"""
        out = Path(str(path))
        if not out.name.lower().endswith(".drawio"):
            out = out.with_name(out.name + ".drawio")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.to_xml(), encoding="utf-8")
        return out


# ============================================================
# 自验与 CLI 公共件
# ============================================================
def validate_drawio_file(path) -> tuple[int, int]:
    """用 stdlib minidom 解析 .drawio, 校验结构合法, 返回 (顶点数, 连线数)。

    Raises:
        ValueError: 缺 mxfile/mxGraphModel/root 结构。
        xml.dom.minidom 解析异常原样抛出（文件非法）。
    """
    from xml.dom import minidom

    doc = minidom.parse(str(path))
    try:
        for tag in ("mxfile", "mxGraphModel", "root"):
            if not doc.getElementsByTagName(tag):
                raise ValueError(f"缺 <{tag}> 结构, 不是合法 .drawio 文件")
        cells = doc.getElementsByTagName("mxCell")
        vertices = sum(1 for c in cells if c.getAttribute("vertex") == "1")
        edges = sum(1 for c in cells if c.getAttribute("edge") == "1")
        return vertices, edges
    finally:
        doc.unlink()


def default_out_stem(stem_name: str) -> str:
    """--out 缺省时写入系统临时目录（gitignore 友好）。"""
    return str(Path(tempfile.gettempdir()) / stem_name)


def base_parser(description: str) -> argparse.ArgumentParser:
    """模板 CLI 公共参数: --out / --palette（模板再补自己的特有参数）。"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .drawio; 缺省写系统临时目录）")
    parser.add_argument("--palette", default="academic_blue",
                        help="色板名: academic_blue(默认)/cool_nature/muted_earth/"
                             "okabe_ito/npg/aaas/lancet/nejm")
    return parser


def finalize(diagram: Diagram, out_stem: str | None,
             fallback_stem: str, *, check: bool = True) -> int:
    """写盘 + minidom 自验 + drawio_check 版式体检; 返回 CLI 退出码。

    版式体检（1.3.0）: 同目录 drawio_check.py 可用时自动运行
    （文字溢出/越界/重复 id/实心盒重叠/连线穿盒/位图内嵌为 FAIL,
    端点压边/疑似空盒/字号档数超标为 WARN）。FAIL 即返回 1。
    环境变量: MATHMODEL_DRAWIO_CHECK=0 关闭体检; MATHMODEL_DRAWIO_STRICT=1
    时 WARN 也判失败。
    """
    try:
        stem = out_stem or default_out_stem(fallback_stem)
        path = diagram.write(stem)
        vertices, edges = validate_drawio_file(path)
    except (OSError, ValueError) as exc:
        print(f"[错误] {exc}")
        return 2
    print(f"已输出: {path}")
    print(f"自验通过: XML 合法, {vertices} 节点 / {edges} 连线 (minidom 解析)")
    if check and os.environ.get("MATHMODEL_DRAWIO_CHECK", "1") != "0":
        try:
            import drawio_check
        except ImportError:
            print("[提示] drawio_check.py 不在同目录, 跳过版式体检")
            return 0
        strict = os.environ.get("MATHMODEL_DRAWIO_STRICT") == "1"
        fails, warns = drawio_check.check_file(path)
        for m in fails:
            print(f"  [FAIL] {m}")
        for m in warns:
            print(f"  [WARN] {m}")
        if fails or (strict and warns):
            print(f"[版式门禁] 未通过: FAIL {len(fails)} / WARN {len(warns)}"
                  f"（修图指引见 design_tokens.md §4.6）")
            return 1
        print(f"版式体检通过: FAIL 0 / WARN {len(warns)} (drawio_check)")
    return 0


if __name__ == "__main__":
    # 自测: 生成一个最小两节点图（含族化节点冒烟）到临时目录并自验
    _d = Diagram(page_width=560, page_height=360, name="builder 自测")
    _d.title("title", "drawio_builder 自测", 0, 16, 560, 32)
    _d.card("node_a", "节点甲 & <测试>", 80, 120, 160, 60)
    _d.card("node_b", label_html(["节点乙", "第二行"]), 320, 120, 160, 60)
    # 1.2.0 族化冒烟: 族色卡 + 族化徽章/标题条 + 虚线容器 + 点线分带
    _d.card("node_fam", "族色卡", 80, 220, 160, 50, family="blue")
    _d.badge("badge_fam", "①", 260, 220, 40, 50, family="blue")
    _d.header_bar("header_fam", "标题条", 320, 220, 160, 50, family="blue")
    _d.dashed_container("group_fam", 70, 210, 420, 70, "blue")
    _d.band_sep("band_fam", 70, 296, 420, 40)
    _d.edge("node_a", "node_b", label="流转",
            exit_dir="right", entry_dir="left")
    # 1.3.0 冒烟: focal 焦点卡 + 分数锚点扇出 + mono 标签 + snap4 网格
    assert snap4(13) == 4 * round(13 / 4)
    _d.card("node_focal", "焦点卡", 80, 40, 160, 50, family="orange", focal=True)
    _d.text("mono_note", "RMSE=2.31", 320, 40, 120, 24, mono=True)
    _d.fan_edges("node_a", ["node_b", "node_fam"], exit_dir="down",
                 entry_dir="top", family="blue")
    _edge = _d.edges[-1]
    assert "exitX=0.67" in _edge.style or "exitX=0.7" in _edge.style, _edge.style
    _mono_node = next(n for n in _d.nodes if n.id == "mono_note")
    assert f"fontFamily={FONT_MONO}" in _mono_node.style
    # 1.3.1 冒烟: 两段式富文本卡 + 竖排标签; 族化卡默认常规字重
    _d.rich_card("node_rich", "灵敏度分析", "Sobol 全局灵敏度", 320, 300, 200, 56,
                 family="teal")
    _rich = next(n for n in _d.nodes if n.id == "node_rich")
    assert "<b>灵敏度分析</b>" in _rich.label and "font-size:9px" in _rich.label
    assert "fontStyle=1" not in _rich.style          # 富文本卡单元格级不加粗
    _d.vlabel("vlab", "阶段目标", 520, 120, 24, 90)
    _vl = next(n for n in _d.nodes if n.id == "vlab")
    assert _vl.label == "阶<br>段<br>目<br>标"
    _fam_card = next(n for n in _d.nodes if n.id == "node_fam")
    assert "fontStyle=1" not in _fam_card.style      # 1.3.1 族化卡默认常规字重
    sys.exit(finalize(_d, None, "drawio_builder_selftest"))
