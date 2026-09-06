# -*- coding: utf-8 -*-
"""
mathmodel-studio 1.2.0 图表共享工具库 (figkit)
================================================================
所有 make_*.py 模板脚本的公共底座, 取代各脚本内联的重复代码:

  - apply_style()        一键加载 ../style/mathmodel.mplstyle (带等价内联回退)
  - load_palette()       动态导入 ../style/palettes.py (失败走内联最小副本)
  - save_fig()           PNG+SVG+PDF 三格式一次导出 (补齐 0.7.4 文档承诺)
  - figsize 预设         期刊物理栏宽 mm → inch (89/120/183mm)
  - panel_label()        (a)(b)(c) 子图标签, 全 skill 统一偏移
  - despine() / ygrid()  坐标轴与网格的现代处理
  - wrap_text_balanced() CJK 感知均衡换行, 消除吊行
  - elbow_arrow()        正交圆角连接器 (示意图替代斜插直线箭头)
  - soft_shadow()        卡片微阴影 path effect
  - check_cjk_font()     中文字体可用性检查与提示

1.2.0 新增示意图色族助手（与数据色板彻底分类, 复刻 sci-box 扁平风）:
  - load_diagram_family()/load_diagram_families()/load_diagram_page()
                        取示意图色族/页面令牌（失败走内联副本）
  - load_diagram_order() 取族序（generic/roadmap）
  - use_diagram_font()   示意图字体链（YaHei 真 700 粗体优先）
  - diagram_box()        浅底+同族描边+墨黑加粗字卡片
  - diagram_header()     实色标题条（族 header 底 + 白色加粗字）
  - family_edge()        族 edge 色连接器（转调 elbow_arrow）

1.3.0 新增编辑级版式令牌与连接器纪律（蒸馏自 diagram-design, MIT）:
  - load_diagram_token() 版式令牌（radius 4/6/8, stroke_w 0.8/1.2/2.0,
                        font_ramp 16/12/10.5/9 扁平字阶）
  - snap4()              4px 网格捕捉（坐标/尺寸/间距硬规则）
  - diagram_box(focal=)  焦点盒（accent 底 + strong 描边; 每图至多 2 个）
  - fan_offsets()        共边多连接器的分数附着位 k/(n+1)
  - bus_fan_v()/bus_fan_h()  "竖线+横母线+分支"一分多连接器（替代 N 条斜线）
  - mono_chain()/mono_text() 数字/参数标签等宽字体链（mono 不给节点名）

典型用法 (模板脚本头部):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # scripts/
    from figkit import apply_style, load_palette, save_fig, FIGSIZE
    apply_style()
    colors = load_palette("academic_blue")

示意图模板头部:
    apply_style(); use_diagram_font()
    fams = load_diagram_families(n=4)
    diagram_box(ax, x, y_top, w, h, text, fams[0])

自测: python figkit.py
"""
from __future__ import annotations

import importlib.util
import math
import os
import sys
import tempfile
from pathlib import Path

# 画布与输出的字体缓存指向系统临时目录, 避免在 skill/项目目录落垃圾文件
os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "mathmodel-mplconfig")
)

STYLE_DIR = Path(__file__).resolve().parents[1] / "style"
MPLSTYLE_PATH = STYLE_DIR / "mathmodel.mplstyle"
PALETTES_PATH = STYLE_DIR / "palettes.py"

# ---- 内联色板副本（最后回退用）: 与 style/palettes.py 全量同步 ----
# 正常路径走动态导入; 只有 palettes.py 缺失/损坏时才落到这份副本。
_PALETTES_FALLBACK: dict[str, list[str]] = {
    "academic_blue": ["#1F4E79", "#2E86AB", "#F18F01", "#C73E1D", "#3B8C6E", "#6C757D"],
    "cool_nature": ["#2C3E50", "#1F77B4", "#17A2B8", "#6C8EBF", "#D97706", "#C0392B"],
    "muted_earth": ["#506B84", "#A77A43", "#6E8B74", "#8B4F4A", "#7C8A96", "#39444D"],
    "okabe_ito": ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9",
                  "#F0E442", "#000000"],
    "npg": ["#E64B35", "#4DBBD5", "#00A087", "#3C5488",
            "#F39B7F", "#8491B4", "#91D1C2", "#DC0000", "#7E6148", "#B09C85"],
    "aaas": ["#3B4992", "#EE0000", "#008B45", "#631879",
             "#008280", "#BB0021", "#5F559B", "#A20056", "#808180", "#1B1919"],
    "lancet": ["#00468B", "#ED0000", "#42B540", "#0099B4",
               "#925E9F", "#FDAF91", "#AD002A", "#ADB6B6", "#1B1919"],
    "nejm": ["#BC3C29", "#0072B5", "#E18727", "#20854E",
             "#7876B1", "#6F99AD", "#FFDC91", "#EE4C97"],
}

_NEUTRALS_FALLBACK = {
    "ink": "#1F2A36", "secondary": "#46535F", "faint": "#8A97A3",
    "grid": "#D9DEE4", "edge": "#C7D3DE", "edge_strong": "#A9BDD0",
    "arrow": "#6B7B8C", "panel_bg": "#F5F7FA", "hairline": "#E8ECF0",
    "white": "#FFFFFF",
}

# ---- 内联示意图色族副本（最后回退用）: 与 style/palettes.py 全量同步 ----
# 色值 1:1 蒸馏自 sci-box scibox-diagram (MIT); 正常路径走动态导入,
# 只有 palettes.py 缺失/损坏时才落到这份副本。修改色值请以 palettes.py 为准。
_DIAGRAM_FAMILIES_FALLBACK: dict[str, dict[str, str]] = {
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

_DIAGRAM_PAGE_FALLBACK = {
    "bg": "#F2EEF7", "ink": "#262626", "title_bar": "#4F80BD", "band_sep": "#5B6B78",
    "frame": "#808080", "loop_arrow": "#CCCCD6", "white": "#FFFFFF",
}
_DIAGRAM_ORDER_GENERIC_FALLBACK = ["blue", "teal", "olive", "orange", "purple", "green", "grey"]
_DIAGRAM_ORDER_ROADMAP_FALLBACK = ["blue", "blue", "orange", "purple", "teal"]
_DIAGRAM_FONT_FALLBACK = ["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans SC",
                          "Arial Unicode MS", "Helvetica"]

# ---- 1.3.0 版式令牌内联副本（与 palettes.py 全量同步; 蒸馏自 diagram-design, MIT）----
_DIAGRAM_TOKENS_FALLBACK = {
    "radius": {"sm": 4, "md": 6, "lg": 8},
    "stroke_w": {"hairline": 0.8, "card": 1.0, "default": 1.2, "strong": 2.0},
    "font_ramp": {"title": 16, "header": 12, "body": 10.5, "note": 9},
}
_DIAGRAM_GRID_FALLBACK = 4
_DIAGRAM_FONT_MONO_FALLBACK = ["Consolas", "DejaVu Sans Mono", "Courier New"]
FOCAL_MAX = 2   # 焦点盒上限: 每图至多 1-2 个焦点节点, 超过等于没有焦点

_palettes_mod = None  # 缓存动态导入的 palettes 模块


# ============================================================
# 样式与色板加载
# ============================================================
def apply_style() -> bool:
    """加载 ../style/mathmodel.mplstyle; 文件缺失时回退等价内联 rcParams。

    Returns:
        True 表示成功加载 .mplstyle 文件, False 表示走了内联回退。
    """
    import matplotlib.pyplot as plt

    if MPLSTYLE_PATH.is_file():
        plt.style.use(str(MPLSTYLE_PATH))
        return True
    # 内联回退: 与 mathmodel.mplstyle 关键项保持一致
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "PingFang SC",
                            "Arial Unicode MS", "Arial"],
        "axes.unicode_minus": False,
        "axes.prop_cycle": plt.cycler(color=_PALETTES_FALLBACK["academic_blue"]),
        "lines.linewidth": 1.8,
        "axes.linewidth": 0.9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linestyle": "--",
        "axes.axisbelow": True,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "legend.frameon": False,
        "figure.dpi": 110,
        "figure.figsize": (7.2, 4.5),
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.transparent": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "xtick.direction": "out",
        "ytick.direction": "out",
    })
    return False


def _load_palettes_module():
    """动态导入 ../style/palettes.py, 失败返回 None (调用方走回退)。"""
    global _palettes_mod
    if _palettes_mod is not None:
        return _palettes_mod
    if not PALETTES_PATH.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("mathmodel_palettes", PALETTES_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _palettes_mod = mod
        return mod
    except Exception:
        return None


def load_palette(name: str | None = None) -> list[str]:
    """取色板色值列表; palettes.py 不可用时回退内联副本。"""
    mod = _load_palettes_module()
    if mod is not None:
        try:
            return mod.get_palette(name)
        except (ValueError, AttributeError):
            pass
    key = (name or "academic_blue").lower()
    alias = {"champion_palette": "academic_blue", "nature": "npg", "science": "aaas"}
    key = alias.get(key, key)
    if key not in _PALETTES_FALLBACK:
        raise ValueError(
            f"未知色板 '{name}' 且 palettes.py 不可用; "
            f"内联副本仅含: {sorted(_PALETTES_FALLBACK)}"
        )
    return list(_PALETTES_FALLBACK[key])


def load_neutral(name: str) -> str:
    """取中性色令牌; palettes.py 不可用时回退内联副本。"""
    mod = _load_palettes_module()
    if mod is not None:
        try:
            return mod.get_neutral(name)
        except (ValueError, AttributeError):
            pass
    if name not in _NEUTRALS_FALLBACK:
        raise ValueError(f"未知中性色令牌 '{name}'. 可用: {sorted(_NEUTRALS_FALLBACK)}")
    return _NEUTRALS_FALLBACK[name]


def apply_palette(name: str | None = None, ax=None) -> list[str]:
    """取色并注入 prop_cycle (全局或指定 Axes), 返回实际色值列表。"""
    colors = load_palette(name)
    import matplotlib as mpl
    if ax is None:
        mpl.rcParams["axes.prop_cycle"] = mpl.cycler(color=colors)
    else:
        ax.set_prop_cycle(color=colors)
    return colors


def get_cmap(kind: str) -> str:
    """按语义取 colormap 名 (diverging/correlation 须以 0 为中心)。"""
    mod = _load_palettes_module()
    if mod is not None:
        try:
            return mod.get_cmap(kind)
        except (ValueError, AttributeError):
            pass
    fallback = {"sequential": "viridis", "diverging": "RdBu_r",
                "correlation": "RdBu_r", "confusion_matrix": "Blues",
                "heatmap": "viridis", "sequential_alt": "cividis"}
    if kind not in fallback:
        raise ValueError(f"未知 cmap 类型 '{kind}'. 可用: {sorted(fallback)}")
    return fallback[kind]


def tint(hex_color: str, factor: float) -> str:
    """向白混合浅化; palettes.py 不可用时本地计算。"""
    mod = _load_palettes_module()
    if mod is not None and hasattr(mod, "tint"):
        return mod.tint(hex_color, factor)
    text = hex_color.strip().lstrip("#")
    r, g, b = int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
    f = min(max(factor, 0.0), 1.0)
    return "#{:02X}{:02X}{:02X}".format(
        round(r + (255 - r) * f), round(g + (255 - g) * f), round(b + (255 - b) * f))


def shade(hex_color: str, factor: float) -> str:
    """向黑混合深化; palettes.py 不可用时本地计算。"""
    mod = _load_palettes_module()
    if mod is not None and hasattr(mod, "shade"):
        return mod.shade(hex_color, factor)
    text = hex_color.strip().lstrip("#")
    r, g, b = int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
    f = min(max(factor, 0.0), 1.0)
    return "#{:02X}{:02X}{:02X}".format(
        round(r * (1 - f)), round(g * (1 - f)), round(b * (1 - f)))


# ============================================================
# 示意图色族/页面令牌/字体链 (1.2.0, 优先走 palettes, 失败回退内联副本)
# ============================================================
def load_diagram_family(name: str) -> dict[str, str]:
    """取一枝示意图色族（8 角色色值字典副本）; palettes.py 不可用时回退内联副本。"""
    mod = _load_palettes_module()
    if mod is not None and hasattr(mod, "get_diagram_family"):
        try:
            return mod.get_diagram_family(name)
        except ValueError:
            pass
    key = str(name).strip().lower()
    if key not in _DIAGRAM_FAMILIES_FALLBACK:
        raise ValueError(
            f"未知示意图色族 '{name}' 且 palettes.py 不可用; "
            f"内联副本仅含: {sorted(_DIAGRAM_FAMILIES_FALLBACK)}"
        )
    return dict(_DIAGRAM_FAMILIES_FALLBACK[key])


def _diagram_families_fallback(order: list[str] | None,
                               n: int | None) -> list[dict[str, str]]:
    """内联回退实现: 语义/入参校验与 palettes.get_diagram_families 一致。

    order 为空列表或 n < 1 抛 ValueError（与 palettes 路径同型）,
    绝不走到 `i % len(seq)` 的除零。
    """
    seq = list(order) if order is not None else list(_DIAGRAM_ORDER_GENERIC_FALLBACK)
    if not seq:
        raise ValueError("order 不能为空列表")
    if n is not None:
        if n < 1:
            raise ValueError(f"n 必须 >= 1, 实际 {n}")
        seq = [seq[i % len(seq)] for i in range(n)]
    return [load_diagram_family(k) for k in seq]


def load_diagram_families(order: list[str] | None = None,
                          n: int | None = None) -> list[dict[str, str]]:
    """按顺序取 n 族示意图色族; order 缺省用 GENERIC 序, n 超长时循环取。

    Raises:
        ValueError: order 为空列表 / n < 1 / 族名未注册（palettes 与内联
            两路校验口径一致）。
    """
    mod = _load_palettes_module()
    if mod is not None and hasattr(mod, "get_diagram_families"):
        try:
            return mod.get_diagram_families(order, n)
        except ValueError:
            pass
    return _diagram_families_fallback(order, n)


def load_diagram_page(token: str) -> str:
    """取示意图页面令牌（bg/ink/title_bar/band_sep/frame/loop_arrow/white）。"""
    mod = _load_palettes_module()
    if mod is not None and hasattr(mod, "get_diagram_page"):
        try:
            return mod.get_diagram_page(token)
        except ValueError:
            pass
    if token not in _DIAGRAM_PAGE_FALLBACK:
        raise ValueError(
            f"未知示意图页面令牌 '{token}'. 可用: {sorted(_DIAGRAM_PAGE_FALLBACK)}")
    return _DIAGRAM_PAGE_FALLBACK[token]


def load_diagram_order(kind: str = "generic") -> list[str]:
    """取示意图族序: "generic"（通用 n 阶段）或 "roadmap"（五带路线图叙事）。"""
    mod = _load_palettes_module()
    attr = f"DIAGRAM_ORDER_{kind.upper()}"
    if mod is not None and hasattr(mod, attr):
        return list(getattr(mod, attr))
    fallback = {"generic": _DIAGRAM_ORDER_GENERIC_FALLBACK,
                "roadmap": _DIAGRAM_ORDER_ROADMAP_FALLBACK}
    if kind not in fallback:
        raise ValueError(f"未知族序类型 '{kind}'. 可用: {sorted(fallback)}")
    return list(fallback[kind])


# ============================================================
# 示意图版式令牌取口 (1.3.0): 网格/圆角/描边/字阶/mono
# ============================================================
def load_diagram_token(group: str, key: str):
    """取版式令牌: group=radius/stroke_w/font_ramp, key=档位名。

    radius → sm/md/lg (4/6/8, 上限 10); stroke_w → hairline/default/strong
    (0.8/1.2/2.0); font_ramp → title/header/body/note (16/12/10.5/9)。
    """
    mod = _load_palettes_module()
    if mod is not None and hasattr(mod, "get_diagram_token"):
        try:
            return mod.get_diagram_token(group, key)
        except ValueError:
            pass
    try:
        return _DIAGRAM_TOKENS_FALLBACK[group][key]
    except KeyError:
        raise ValueError(
            f"未知示意图令牌 '{group}/{key}'. 可用组: {sorted(_DIAGRAM_TOKENS_FALLBACK)}; "
            f"各组档位: {{k: sorted(v) for k, v in _DIAGRAM_TOKENS_FALLBACK.items()}}"
        ) from None


def snap4(value: float, grid: int | None = None) -> float:
    """坐标/尺寸捕捉到 4px 网格（diagram-design 硬规则, 本地化为示意图纪律）。

    一切手排坐标、盒宽盒高、行列间距先过 snap4; 同族元素必须同宽同步距。
    """
    if grid is None:
        mod = _load_palettes_module()
        grid = int(getattr(mod, "DIAGRAM_GRID", _DIAGRAM_GRID_FALLBACK)
                   ) if mod is not None else _DIAGRAM_GRID_FALLBACK
    if grid <= 0:
        raise ValueError(f"grid 必须为正, 实际 {grid}")
    snapped = round(value / grid) * grid
    return int(snapped) if snapped == int(snapped) else float(snapped)


def mono_chain() -> list[str]:
    """数字/参数/公式标签的等宽字体链（Consolas 优先, 全平台有兜底）。

    纪律（diagram-design）: mono 只给"技术性内容"（数值、参数、端口式标签）,
    节点名/标题永远用 sans; 中文不走 mono（mono 字体无中文字形）。
    """
    mod = _load_palettes_module()
    if mod is not None and hasattr(mod, "DIAGRAM_FONT_MONO"):
        return list(mod.DIAGRAM_FONT_MONO)
    return list(_DIAGRAM_FONT_MONO_FALLBACK)


def mono_text(ax, x: float, y: float, text: str, fontsize: float | None = None,
              color: str | None = None, ha: str = "center", va: str = "center",
              bold: bool = False, zorder: int = 6):
    """放一个等宽字体的数字/参数标签（如 "RMSE=2.31"），仅 ASCII 内容。

    fontsize 缺省取字阶 note 档; color 缺省取 secondary 令牌。
    """
    fs = fontsize if fontsize is not None else load_diagram_token("font_ramp", "note")
    return ax.text(x, y, text, ha=ha, va=va, fontsize=fs,
                   fontfamily=mono_chain(),
                   color=color or load_neutral("secondary"),
                   fontweight="bold" if bold else "normal", zorder=zorder)


def use_diagram_font() -> None:
    """把 rcParams 字体链切到示意图专用链（YaHei 真 700 粗体优先）。

    示意图全字加粗（sci-box 扁平排版纪律）, Noto Sans SC 为可变字体、
    matplotlib 只注册到 weight=100, 加粗不可用, 只作链末兜底。
    示意图脚本应在 apply_style() 之后调用本函数。

    注意: 本函数修改**全局** rcParams, 供独立出图脚本进程使用; 同一进程
    后续要画数据图/其他图之前, 必须重新 apply_style() 复位字体链,
    否则示意图字体链会泄漏到后续图。
    """
    import matplotlib.pyplot as plt

    mod = _load_palettes_module()
    chain = (list(getattr(mod, "DIAGRAM_FONT_FAMILY"))
             if mod is not None and hasattr(mod, "DIAGRAM_FONT_FAMILY")
             else list(_DIAGRAM_FONT_FALLBACK))
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = chain
    plt.rcParams["axes.unicode_minus"] = False


# ============================================================
# 期刊物理尺寸 (mm → inch) 与画布预设
# ============================================================
MM_PER_INCH = 25.4


def mm(width_mm: float, height_mm: float | None = None) -> tuple[float, float]:
    """毫米尺寸 → matplotlib figsize (inch)。height 缺省时按黄金比 0.68 取。"""
    if height_mm is None:
        height_mm = width_mm * 0.68
    return (width_mm / MM_PER_INCH, height_mm / MM_PER_INCH)


# 期刊/竞赛常用物理栏宽预设 (width_mm, 推荐 height_mm)
FIGSIZE: dict[str, tuple[float, float]] = {
    "single":    mm(89, 62),     # 期刊单栏
    "onehalf":   mm(120, 82),    # 1.5 栏
    "double":    mm(183, 120),   # 期刊双栏
    "wide":      mm(183, 92),    # 双栏宽幅 (横向流水线/对比)
    "square":    mm(89, 89),     # 单栏方形 (热力图/相关矩阵)
    "default":   (7.2, 4.5),     # 沿用 0.7.4 竞赛正文图默认
    "roadmap":   (10.0, 7.0),    # 五层技术路线图
    "framework": (11.0, 4.6),    # 三栏研究框架
}


# ============================================================
# 三格式导出 (补齐 0.7.4 文档承诺的 PNG+SVG+PDF)
# ============================================================
def save_fig(fig, out_prefix, formats: tuple[str, ...] = ("png", "svg", "pdf"),
             close: bool = True) -> list[str]:
    """按前缀一次导出多格式, 返回写出的文件路径列表。

    Args:
        fig: matplotlib Figure。
        out_prefix: 输出前缀 (不带扩展名); 末段目录不存在会自动创建。
        formats: 格式元组, 默认 ("png", "svg", "pdf"); png 走 savefig.dpi(300),
                 svg/pdf 为矢量, 字体策略由 mplstyle 的 svg.fonttype/pdf.fonttype 决定。
        close: 导出后是否 plt.close(fig) 释放内存。

    异常行为: 某一格式 savefig 抛异常（如非法格式名）时, close=True 会先
    close(fig) 再让异常向上抛（不泄漏 figure）; 异常前已写出的部分文件保留
    在磁盘上不回滚, 由调用方决定清理。
    """
    import matplotlib.pyplot as plt

    prefix = Path(str(out_prefix))
    prefix.parent.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    try:
        for fmt in formats:
            path = f"{prefix}.{fmt}"
            fig.savefig(path)
            written.append(path)
    finally:
        if close:
            plt.close(fig)
    return written


# ============================================================
# 坐标轴/网格/子图标签
# ============================================================
def despine(ax, keep: tuple[str, ...] = ("left", "bottom")):
    """只保留指定 spines (默认左+下), 其余隐藏。"""
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(side in keep)


def ygrid(ax, color: str | None = None, alpha: float = 0.45, lw: float = 0.7):
    """只留极淡 y 向网格 (期刊数据图惯例), 关闭 x 向网格。"""
    ax.yaxis.grid(True, color=color or load_neutral("grid"),
                  alpha=alpha, linewidth=lw, linestyle="-")
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)


def panel_label(ax, label: str, x: float = -0.08, y: float = 1.04,
                fontsize: float = 11, bold: bool = True):
    """子图标签 (a)/(b)/(c), transAxes 坐标, 全 skill 统一偏移 -0.08/1.04。"""
    ax.text(x, y, f"({label})", transform=ax.transAxes,
            fontsize=fontsize, fontweight="bold" if bold else "normal",
            va="bottom", ha="left", color=load_neutral("ink"))


# ============================================================
# CJK 感知文字宽度与均衡换行
# ============================================================
def char_width_px(ch: str, fontsize: float) -> float:
    """估算单字符像素宽: 全角≈1.45×字号, 半角≈0.72×字号 (经验值, 免 GUI 测量)。"""
    if ord(ch) > 0x2E7F:  # CJK 及全角符号区间
        return fontsize * 1.45
    if ch in "iljtf.,:;'! ":
        return fontsize * 0.5
    return fontsize * 0.72


def text_width_px(text: str, fontsize: float) -> float:
    """估算整串像素宽。"""
    return sum(char_width_px(c, fontsize) for c in text)


def wrap_text(text: str, max_width_px: float, fontsize: float) -> list[str]:
    """贪心换行 (0.7.4 行为, 保留兼容): 逐字符累积, 超宽即断行。"""
    lines: list[str] = []
    current = ""
    current_w = 0.0
    for ch in text:
        w = char_width_px(ch, fontsize)
        if current and current_w + w > max_width_px:
            lines.append(current)
            current, current_w = ch, w
        else:
            current += ch
            current_w += w
    if current:
        lines.append(current)
    return lines or [""]


def wrap_text_balanced(text: str, max_width_px: float, fontsize: float) -> list[str]:
    """均衡换行 (1.1.0 新增): 在贪心行数不变的前提下让各行宽度尽量接近,
    消除"末尾一字独占一行"的吊行。

    做法: 先贪心得行数 n; 再以 总宽/n × 1.15 为目标宽度重新贪心,
    若行数不变则采用, 否则回退贪心结果。对 2-4 行的卡片文本效果显著。
    """
    greedy = wrap_text(text, max_width_px, fontsize)
    if len(greedy) <= 1:
        return greedy
    total_w = text_width_px(text, fontsize)
    target = total_w / len(greedy) * 1.15
    if target >= max_width_px:
        return greedy
    balanced = wrap_text(text, target, fontsize)
    return balanced if len(balanced) == len(greedy) else greedy


# ============================================================
# 示意图连接器与装饰 (1.1.0 新增)
# ============================================================
def elbow_arrow(ax, xy_from: tuple[float, float], xy_to: tuple[float, float],
                color: str | None = None, lw: float = 1.3,
                direction: str = "vh", rad: float = 6.0,
                arrowstyle: str = "-|>", mutation_scale: float = 11.0,
                zorder: int = 3):
    """正交圆角连接器: 替代示意图里斜插的直线箭头。

    Args:
        xy_from/xy_to: 起点/终点 (数据坐标), 通常取盒边中点。
        direction: "vh" 先垂后平 (上下层间), "hv" 先平后垂 (左右栏间)。
        rad: 拐角圆角半径 (数据坐标单位, 0 则为直角)。
        lw/mutation_scale: 1.3.1 起默认降重 (1.3 / 11)——连线退居二线,
            内容才是主角（编辑级纪律, §4.6④）; 需强调时显式给大值。
        其余参数同 FancyArrowPatch。
    """
    from matplotlib.patches import FancyArrowPatch

    style = ("angle,angleA=90,angleB=0" if direction == "vh"
             else "angle,angleA=0,angleB=90")
    if rad:
        style += f",rad={rad}"
    arrow = FancyArrowPatch(
        xy_from, xy_to, connectionstyle=style,
        arrowstyle=arrowstyle, mutation_scale=mutation_scale,
        color=color or load_neutral("arrow"), linewidth=lw,
        zorder=zorder, shrinkA=0, shrinkB=0,
    )
    ax.add_patch(arrow)
    return arrow


def straight_arrow(ax, xy_from, xy_to, color: str | None = None,
                   lw: float = 1.3, rad: float = 0.0, **kwargs):
    """微弧直线连接器 (需要优雅斜线时用, rad 控制弯曲; 1.3.1 降重默认)。"""
    from matplotlib.patches import FancyArrowPatch

    style = f"arc3,rad={rad}"
    arrow = FancyArrowPatch(
        xy_from, xy_to, connectionstyle=style,
        arrowstyle=kwargs.pop("arrowstyle", "-|>"),
        mutation_scale=kwargs.pop("mutation_scale", 11.0),
        color=color or load_neutral("arrow"), linewidth=lw,
        zorder=kwargs.pop("zorder", 3), shrinkA=0, shrinkB=0, **kwargs,
    )
    ax.add_patch(arrow)
    return arrow


def soft_shadow(patch=None, offset: tuple[float, float] = (1.2, -1.2),
                alpha: float = 0.12):
    """给 FancyBboxPatch/Rectangle 加微阴影 path effect (卡片浮起感)。

    用法: box.set_path_effects(figkit.soft_shadow(box)) 或直接
    patch.set_path_effects(soft_shadow())。
    patch 参数当前未参与计算(保留以兼容既有调用形式), 可省略。
    注意阴影会使 figqa 色块统计略有变化, 示意图模板已按此校准。
    """
    from matplotlib import patheffects

    return [patheffects.SimplePatchShadow(offset=offset, alpha=alpha,
                                          shadow_rgbFace=(0.12, 0.16, 0.22),
                                          rho=0.985),
            patheffects.Normal()]


# ============================================================
# 示意图卡片/标题条/族色连接器 (1.2.0, 复刻 sci-box 扁平风:
# 浅底 + 同族描边 + 墨黑加粗字, 全部不加 soft_shadow)
# ============================================================
# 多行文本行高估算: 实际行距 ≈ 字号×1.317×行距系数(1.45), 再留余量
# （与 diagrams/ 模板既有 LINE_PITCH = 1.36 * 1.45 同源）
DIAGRAM_LINE_PITCH = 1.36 * 1.45
DIAGRAM_TEXT_PAD = 14.0  # 卡内左右留白（换行可用宽 = w - 2*pad）


def _diagram_lines_height(nlines: int, fontsize: float,
                          pad: float = 12.0, min_h: float = 0.0) -> float:
    """示意图盒内 n 行文本的占用高估算（含上下余量, 不低于 min_h）。"""
    return max(nlines * fontsize * DIAGRAM_LINE_PITCH + pad, min_h)


def _check_fontsize(*pairs: tuple[str, float]) -> None:
    """校验字号入参为有限正数（防 inf/nan 卡死"缩字号"循环）。"""
    for name, value in pairs:
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} 必须为有限正数, 实际 {value!r}")


def diagram_box(ax, x: float, y_top: float, w: float, h: float, text: str,
                family: dict[str, str], fontsize: float | None = None,
                fs_min: float = 8.0, rounded: float | None = None,
                accent: bool = False, focal: bool = False,
                bold: bool = False, text_color: str | None = None
                ) -> tuple[list[str], float]:
    """画一个"浅底+同族描边+墨黑字"的示意图卡片（sci-box 扁平风, 无阴影）。

    Args:
        ax: 目标 Axes（画布逻辑坐标 = 像素, dpi=100）。
        x/y_top/w/h: 左上角 x、顶边 y 与宽高（y 轴向上, 顶边为 y_top）。
        text: 卡片文本（自动均衡换行）。
        family: 色族字典（load_diagram_family / load_diagram_families 取得）。
        fontsize/fs_min: 起始字号（缺省取字阶 body 档 10.5）/ 超高缩字下限;
            须为有限正数。
        rounded: 圆角半径（缺省取圆角阶梯 lg=8, 上限 10）。
        accent: True 时底色用 family["accent"]（子标题/高亮盒）。
        focal: True 时为焦点盒 —— accent 底 + 族 stroke 描边 2.0（strong 档）。
            每图至多 FOCAL_MAX=2 个（diagram-design focal rule）, 超过等于没有焦点。
        bold: 字重。1.3.1 起默认 False（卡内正文常规字重）——加粗只给
            标题条/徽章/卡片标题, 全字加粗会把层级抹平（§4.5 字重层级制）。
        text_color: 文字色; 默认 DIAGRAM_PAGE ink(#262626)。

    Returns:
        (实际行列表, 实际字号)。缩到下限仍放不下时打印 [警告], 不静默裁字。

    Raises:
        ValueError: fontsize/fs_min 非有限正数。
    """
    from matplotlib.patches import FancyBboxPatch

    if fontsize is None:
        fontsize = load_diagram_token("font_ramp", "body")
    if rounded is None:
        rounded = load_diagram_token("radius", "lg")
    _check_fontsize(("fontsize", fontsize), ("fs_min", fs_min))
    ink = text_color or load_diagram_page("ink")
    fs = float(fontsize)
    lines = wrap_text_balanced(text, w - 2 * DIAGRAM_TEXT_PAD, fs)
    while _diagram_lines_height(len(lines), fs) > h and fs > fs_min:
        fs = max(fs - 0.5, fs_min)
        lines = wrap_text_balanced(text, w - 2 * DIAGRAM_TEXT_PAD, fs)
    if _diagram_lines_height(len(lines), fs) > h:
        print(f"[警告] 卡片文字过长: {text[:18]!r} 缩至最小字号 {fs_min:.1f}pt "
              f"后仍需 {len(lines)} 行, 盒内恐溢出, 建议精简文案")
    patch = FancyBboxPatch(
        (x, y_top - h), w, h,
        boxstyle=f"round,pad=2,rounding_size={rounded}",
        facecolor=family["accent"] if (accent or focal) else family["fill"],
        edgecolor=family["stroke"],
        linewidth=(load_diagram_token("stroke_w", "strong") if focal
                   else load_diagram_token("stroke_w", "card")),
        zorder=2,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y_top - h / 2, "\n".join(lines), ha="center",
            va="center", fontsize=fs, color=ink,
            fontweight="bold" if bold else "normal",
            linespacing=1.45, zorder=5)
    return lines, fs


def diagram_header(ax, x: float, y_top: float, w: float, h: float, text: str,
                   family: dict[str, str], fontsize: float | None = None,
                   rounded: float | None = None) -> None:
    """实色标题条: family header 底 + header_stroke 描边 + 白色加粗字。

    sci-box TONES 式标题条（列头/阶段头）; 文字超宽自动换行、超高缩字号
    （下限 9pt）, 仍放不下打印 [警告]。fontsize 缺省取字阶 header 档(12),
    圆角缺省取阶梯 lg(8)。

    Raises:
        ValueError: fontsize 非有限正数。
    """
    from matplotlib.patches import FancyBboxPatch

    if fontsize is None:
        fontsize = load_diagram_token("font_ramp", "header")
    if rounded is None:
        rounded = load_diagram_token("radius", "lg")
    _check_fontsize(("fontsize", fontsize))
    fs = float(fontsize)
    lines = wrap_text_balanced(text, w - 2 * 12.0, fs)
    while len(lines) * fs * DIAGRAM_LINE_PITCH > h - 8.0 and fs > 9.0:
        fs = max(fs - 1.0, 9.0)
        lines = wrap_text_balanced(text, w - 2 * 12.0, fs)
    if len(lines) * fs * DIAGRAM_LINE_PITCH > h - 8.0:
        print(f"[警告] 标题条文字过长: {text[:18]!r} 色条内放不下, 建议精简标题")
    patch = FancyBboxPatch(
        (x, y_top - h), w, h,
        boxstyle=f"round,pad=2,rounding_size={rounded}",
        facecolor=family["header"],
        edgecolor=family["header_stroke"],
        linewidth=load_diagram_token("stroke_w", "default"),
        zorder=2,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y_top - h / 2, "\n".join(lines), ha="center",
            va="center", fontsize=fs, color=load_diagram_page("white"),
            fontweight="bold", linespacing=1.45, zorder=5)


def family_edge(ax, xy_from: tuple[float, float], xy_to: tuple[float, float],
                family: dict[str, str], **kw):
    """族色连接器: elbow_arrow 包一层, color 固定取 family["edge"]。"""
    return elbow_arrow(ax, xy_from, xy_to, color=family["edge"], **kw)


# ============================================================
# 扇出/扇入母线连接器 (1.3.0): "竖线+横母线+分支"纪律
# 一分多/多合一不画 N 条独立斜线（sci-box 连接器纪律）;
# 同源多箭头的附着点按 L*k/(N+1) 扇形排开、间距 ≥12px
# （diagram-design connector rule 4）。
# ============================================================
def fan_offsets(n: int) -> list[float]:
    """n 个连接器共用一条盒边时的分数附着位: k/(n+1), k=1..n。

    配合盒宽/盒高换算成坐标: x = box_x + w * frac。相邻附着点物理间距
    = w/(n+1), 调用方保证盒宽使其间距 ≥12px（小盒至少 8px）。
    """
    if n < 1:
        raise ValueError(f"n 必须 >= 1, 实际 {n}")
    return [(k + 1) / (n + 1) for k in range(n)]


def bus_fan_v(ax, origin: tuple[float, float],
              targets: list[tuple[float, float]], family: dict[str, str],
              bus_y: float | None = None, lw: float = 1.6,
              mutation_scale: float = 14.0, zorder: int = 3):
    """竖向一分多母线: 源点竖线下行 → 横母线 → 各分支竖直箭头进入目标。

    Args:
        origin: 源盒出口点 (x, y)，通常为底边中点。
        targets: 各目标盒入口点列表 [(x, y_top), ...]，通常为顶边中点。
        family: 色族字典（取 edge 色, 全母线同一族）。
        bus_y: 横母线 y 坐标; 缺省取 origin 与目标中位 y 的中点。
    """
    from matplotlib.patches import FancyArrowPatch

    if not targets:
        raise ValueError("targets 不能为空")
    ox, oy = origin
    if bus_y is None:
        mid_ty = sorted(t[1] for t in targets)[len(targets) // 2]
        bus_y = (oy + mid_ty) / 2.0
    color = family["edge"]
    # 竖线 trunk + 横母线（无箭头, 纯线段）
    ax.plot([ox, ox], [oy, bus_y], color=color, lw=lw, zorder=zorder,
            solid_capstyle="round")
    xs = [t[0] for t in targets]
    ax.plot([min(min(xs), ox), max(max(xs), ox)], [bus_y, bus_y],
            color=color, lw=lw, zorder=zorder, solid_capstyle="round")
    # 分支: 母线 → 目标（带箭头）
    for tx, ty in targets:
        arrow = FancyArrowPatch((tx, bus_y), (tx, ty), arrowstyle="-|>",
                                mutation_scale=mutation_scale, color=color,
                                lw=lw, zorder=zorder, shrinkA=0, shrinkB=0)
        ax.add_patch(arrow)


def bus_fan_h(ax, origin: tuple[float, float],
              targets: list[tuple[float, float]], family: dict[str, str],
              bus_x: float | None = None, lw: float = 1.6,
              mutation_scale: float = 14.0, zorder: int = 3):
    """横向一分多母线: 源点水平右行 → 竖母线 → 各分支水平箭头进入目标。

    origin 通常为源盒右边中点, targets 为目标盒左边中点列表。
    """
    from matplotlib.patches import FancyArrowPatch

    if not targets:
        raise ValueError("targets 不能为空")
    ox, oy = origin
    if bus_x is None:
        mid_tx = sorted(t[0] for t in targets)[len(targets) // 2]
        bus_x = (ox + mid_tx) / 2.0
    color = family["edge"]
    ax.plot([ox, bus_x], [oy, oy], color=color, lw=lw, zorder=zorder,
            solid_capstyle="round")
    ys = [t[1] for t in targets]
    ax.plot([bus_x, bus_x], [min(min(ys), oy), max(max(ys), oy)],
            color=color, lw=lw, zorder=zorder, solid_capstyle="round")
    for tx, ty in targets:
        arrow = FancyArrowPatch((bus_x, ty), (tx, ty), arrowstyle="-|>",
                                mutation_scale=mutation_scale, color=color,
                                lw=lw, zorder=zorder, shrinkA=0, shrinkB=0)
        ax.add_patch(arrow)


# ============================================================
# 结构化零件 (1.3.1): 两段式富文本卡 / 编号徽章 / 竖排标签 / 脚注条
# 信息密度纪律: 内容卡 = "bold 标题行 + regular 明细行"两段式, 明细行走
# note 档次级色（纯 ASCII 明细可走 mono 链）; 密度来自内容结构, 不来自加粗
# ============================================================
def rich_box(ax, x: float, y_top: float, w: float, h: float,
             title: str, detail: str, family: dict[str, str],
             title_fs: float | None = None, detail_fs: float | None = None,
             rounded: float | None = None, accent: bool = False,
             focal: bool = False, detail_mono: bool = False,
             min_h: float = 56.0) -> None:
    """两段式富文本卡: bold 标题行（body 档）+ regular 明细行（note 档, 次级色）。

    卡内文字总高超盒时先缩明细行字号（下限 7.5）, 再缩标题字号（下限 9）,
    仍放不下打印 [警告]。detail 为空串时退化为单行卡（标题垂直居中）。
    detail_mono=True 时明细行走等宽链（仅当明细是数字/参数类 ASCII 内容;
    含中文时自动回退 sans, 因为 mono 字体无中文字形）。
    """
    from matplotlib.patches import FancyBboxPatch

    if title_fs is None:
        title_fs = load_diagram_token("font_ramp", "body")
    if detail_fs is None:
        detail_fs = load_diagram_token("font_ramp", "note")
    if rounded is None:
        rounded = load_diagram_token("radius", "lg")
    _check_fontsize(("title_fs", title_fs), ("detail_fs", detail_fs))
    ink = load_diagram_page("ink")
    secondary = load_neutral("secondary")
    if detail_mono and any(ord(c) > 0x2E7F for c in detail):
        detail_mono = False   # mono 字体无中文字形, 自动回退

    pad_w = w - 2 * DIAGRAM_TEXT_PAD
    t_lines = wrap_text_balanced(title, pad_w, title_fs)
    d_lines: list[str] = []
    if detail.strip():
        d_lines = wrap_text_balanced(detail, pad_w, detail_fs)
        # 先缩明细
        while (_diagram_lines_height(len(t_lines), title_fs)
               + _diagram_lines_height(len(d_lines), detail_fs, pad=4)
               > h - 6) and detail_fs > 7.5:
            detail_fs = max(detail_fs - 0.5, 7.5)
            d_lines = wrap_text_balanced(detail, pad_w, detail_fs)
    # 再缩标题
    while (_diagram_lines_height(len(t_lines), title_fs)
           + (_diagram_lines_height(len(d_lines), detail_fs, pad=4)
              if d_lines else 0.0) > h - 6) and title_fs > 9.0:
        title_fs = max(title_fs - 0.5, 9.0)
        t_lines = wrap_text_balanced(title, pad_w, title_fs)
    total_h = (_diagram_lines_height(len(t_lines), title_fs)
               + (_diagram_lines_height(len(d_lines), detail_fs, pad=4)
                  if d_lines else 0.0))
    if total_h > h - 6:
        print(f"[警告] 富文本卡内容过长: {title[:14]!r} 两段排下仍需 "
              f"{total_h:.0f}px > 盒高 {h:.0f}px, 建议精简文案")

    patch = FancyBboxPatch(
        (x, y_top - h), w, h,
        boxstyle=f"round,pad=2,rounding_size={rounded}",
        facecolor=family["accent"] if (accent or focal) else family["fill"],
        edgecolor=family["stroke"],
        linewidth=(load_diagram_token("stroke_w", "strong") if focal
                   else load_diagram_token("stroke_w", "card")),
        zorder=2,
    )
    ax.add_patch(patch)
    if not d_lines:
        ax.text(x + w / 2, y_top - h / 2, "\n".join(t_lines), ha="center",
                va="center", fontsize=title_fs, color=ink, fontweight="bold",
                linespacing=1.4, zorder=5)
        return
    # 两段式: 标题块 + 明细块垂直堆叠居中（块间 4px 间隙）
    block_gap = 4.0
    t_h = len(t_lines) * title_fs * DIAGRAM_LINE_PITCH
    d_h = len(d_lines) * detail_fs * DIAGRAM_LINE_PITCH
    start_y = y_top - (h - (t_h + block_gap + d_h)) / 2   # 标题块顶
    ax.text(x + w / 2, start_y - t_h / 2, "\n".join(t_lines), ha="center",
            va="center", fontsize=title_fs, color=ink, fontweight="bold",
            linespacing=1.4, zorder=5)
    ax.text(x + w / 2, start_y - t_h - block_gap - d_h / 2, "\n".join(d_lines),
            ha="center", va="center", fontsize=detail_fs, color=secondary,
            linespacing=1.35, zorder=5,
            fontfamily=mono_chain() if detail_mono else None)


def num_badge(ax, cx: float, cy: float, r: float, text: str,
              family: dict[str, str], fontsize: float | None = None) -> None:
    """编号圆徽章: 族 chevron 浅底 + 族 stroke 描边 + 墨黑加粗字（①②③…）。

    r 为半径（数据坐标 px）; 徽章是结构件, 保持加粗（§4.5 字重层级制）。
    """
    from matplotlib.patches import Circle

    if fontsize is None:
        fontsize = load_diagram_token("font_ramp", "header")
    patch = Circle((cx, cy), r, facecolor=family["chevron"],
                   edgecolor=family["stroke"],
                   linewidth=load_diagram_token("stroke_w", "card"), zorder=4)
    ax.add_patch(patch)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize,
            color=load_diagram_page("ink"), fontweight="bold", zorder=5)


def vlabel(ax, x: float, y_center: float, text: str,
           fontsize: float | None = None, color: str | None = None,
           bold: bool = False, zorder: int = 5) -> None:
    """竖排标签: 逐字堆叠（sci-box 纪律: 禁用 rotate=90, 中文会躺倒）。

    用于色带右侧/画布边缘的阶段目标标注。字色默认次级色, note 档。
    """
    fs = fontsize if fontsize is not None else load_diagram_token("font_ramp", "note")
    ax.text(x, y_center, "\n".join(text), ha="center", va="center",
            fontsize=fs, color=color or load_neutral("secondary"),
            fontweight="bold" if bold else "normal",
            linespacing=1.05, zorder=zorder)


def footnote_bar(ax, x: float, y_top: float, w: float, h: float, text: str,
                 family: dict[str, str], fontsize: float | None = None) -> None:
    """结论脚注条: 左侧族色竖 tick + 左对齐常规小字（note 档, 次级色）。

    用于色带底部/图末的"本阶段结论"注记; 不是标题条, 不加粗不实色。
    """
    from matplotlib.patches import Rectangle

    fs = fontsize if fontsize is not None else load_diagram_token("font_ramp", "note")
    _check_fontsize(("fontsize", fs))
    tick = Rectangle((x, y_top - h), 4.0, h, facecolor=family["header"],
                     edgecolor="none", zorder=3)
    ax.add_patch(tick)
    lines = wrap_text_balanced(text, w - 16.0, fs)
    while _diagram_lines_height(len(lines), fs, pad=4) > h and fs > 7.5:
        fs = max(fs - 0.5, 7.5)
        lines = wrap_text_balanced(text, w - 16.0, fs)
    if _diagram_lines_height(len(lines), fs, pad=4) > h:
        print(f"[警告] 脚注条文字过长: {text[:18]!r} 建议精简")
    ax.text(x + 12.0, y_top - h / 2, "\n".join(lines), ha="left", va="center",
            fontsize=fs, color=load_neutral("secondary"), linespacing=1.35,
            zorder=5)


def check_cjk_font() -> tuple[bool, str]:
    """检查首选中文字体是否可用, 返回 (是否可用, 实际命中的字体名)。"""
    from matplotlib import font_manager

    preferred = ["Microsoft YaHei", "SimHei", "PingFang SC", "Arial Unicode MS"]
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in preferred:
        if name in installed:
            return True, name
    return False, "无 (中文将显示为方块, 请安装 Microsoft YaHei 或 SimHei)"


# ============================================================
# 自测: python figkit.py
# ============================================================
if __name__ == "__main__":
    print("=" * 62)
    print("mathmodel-studio 1.2.0 figkit 自测")
    print("=" * 62)
    ok_style = apply_style()
    print(f"apply_style(): {'加载 mplstyle' if ok_style else '内联回退'}")
    print(f"load_palette('npg')[:4] = {load_palette('npg')[:4]}")
    print(f"load_neutral('grid') = {load_neutral('grid')}")
    print(f"get_cmap('correlation') = {get_cmap('correlation')}")
    print(f"mm(89, 62) = {tuple(round(v, 3) for v in mm(89, 62))}")
    print(f"FIGSIZE 预设: {sorted(FIGSIZE)}")
    demo = "最优方案对参数扰动与情景假设的稳健性如何？"
    print(f"贪心换行: {wrap_text(demo, 240, 10)}")
    print(f"均衡换行: {wrap_text_balanced(demo, 240, 10)}")
    ok_font, font_name = check_cjk_font()
    print(f"中文字体: {font_name} ({'可用' if ok_font else '缺失'})")

    # ---- 1.2.0: 示意图色族助手自测 ----
    fam = load_diagram_family("blue")
    fams = load_diagram_families(n=4)
    print(f"load_diagram_family('blue') edge = {fam['edge']}")
    print(f"load_diagram_families(n=4) = {[f['fill'] for f in fams]}")
    print(f"load_diagram_order('roadmap') = {load_diagram_order('roadmap')}")
    print(f"load_diagram_page('ink') = {load_diagram_page('ink')}")
    # 内联回退分支校验: 空 order / 未知族名须抛 ValueError（不得除零崩溃）
    for bad_order in ([], ["magenta"]):
        try:
            _diagram_families_fallback(bad_order, 2)
            raise AssertionError(f"回退分支对 {bad_order!r} 未报错")
        except ValueError as exc:
            assert ("不能为空" in str(exc)) or ("magenta" in str(exc)), exc
    try:
        load_diagram_families([], None)   # 两路（palettes/内联）口径一致
        raise AssertionError("空 order 未报错")
    except ValueError:
        pass
    print("load_diagram_families 空 order/未知族名 -> ValueError: 通过")
    use_diagram_font()
    import matplotlib.pyplot as plt
    print(f"use_diagram_font() 后 font.sans-serif 首位 = "
          f"{plt.rcParams['font.sans-serif'][0]}")

    # 冒烟: 画一张最小示意图（标题条 + 两张卡片 + 族色箭头）走三格式导出
    fig, ax = plt.subplots(figsize=(6.0, 3.2), dpi=100)
    ax.set_xlim(0, 600)
    ax.set_ylim(0, 320)
    ax.axis("off")
    diagram_header(ax, 30, 310, 540, 44, "示意图助手冒烟", fam)
    lines1, fs1 = diagram_box(ax, 30, 250, 240, 52, "浅底卡片一号", fam)
    lines2, fs2 = diagram_box(ax, 330, 250, 240, 52, "强调卡片二号(accent)",
                              fam, accent=True)
    family_edge(ax, (274, 224), (326, 224), fam, direction="hv", rad=0)
    assert lines1 and fs1 > 0 and lines2 and fs2 > 0

    # ---- 1.3.0: 版式令牌 + focal + 母线 + mono 冒烟 ----
    assert snap4(13) == 12 and snap4(14, grid=4) == 16
    assert load_diagram_token("radius", "lg") == 8
    assert load_diagram_token("stroke_w", "strong") == 2.0
    assert load_diagram_token("font_ramp", "title") == 16
    assert fan_offsets(3) == [0.25, 0.5, 0.75]
    try:
        fan_offsets(0)
        raise AssertionError("fan_offsets(0) 未报错")
    except ValueError:
        pass
    # focal 卡: accent 底 + strong 描边
    diagram_box(ax, 30, 180, 240, 52, "焦点卡(focal)", fam, focal=True)
    # 竖向母线一分二 + 横向母线一分二
    bus_fan_v(ax, (390, 172), [(330, 120), (450, 120)], fam)
    bus_fan_h(ax, (270, 146), [(300, 130), (300, 162)], fam)
    mono_text(ax, 480, 60, "RMSE=2.31")
    assert mono_chain()[0] == "Consolas"
    print("1.3.0 令牌/focal/bus/mono 冒烟: 通过")

    # ---- 1.3.1: 结构化零件冒烟（两段式卡/编号徽章/竖排标签/脚注条）----
    fam2 = load_diagram_family("teal")
    rich_box(ax, 30, 110, 240, 64, "灵敏度分析", "Sobol 全局灵敏度", fam2)
    rich_box(ax, 330, 110, 240, 64, "稳健性检验", "n=1000 次扰动", fam2,
             detail_mono=True)
    rich_box(ax, 30, 30, 240, 36, "单行退化卡", "", fam2)   # detail 空 → 退化
    num_badge(ax, 580, 200, 16, "1", fam)
    vlabel(ax, 588, 120, "阶段目标")
    footnote_bar(ax, 330, 40, 240, 28, "本阶段结论: 模型对 ±10% 扰动稳健", fam2)
    print("1.3.1 rich_box/num_badge/vlabel/footnote_bar 冒烟: 通过")

    # 字号入参校验: inf/nan/非正数须 ValueError（防缩字号循环死循环）
    fig_v, ax_v = plt.subplots(figsize=(3.0, 2.0))
    for bad in (float("inf"), float("nan"), 0.0, -3.0):
        for fn, kwargs in ((diagram_box, {"fontsize": bad}),
                           (diagram_box, {"fs_min": bad}),
                           (diagram_header, {"fontsize": bad})):
            try:
                fn(ax_v, 10, 180, 200, 60, "校验", fam, **kwargs)
                raise AssertionError(f"{fn.__name__} 对 {bad!r} 未报错")
            except ValueError:
                pass
    plt.close(fig_v)
    print("diagram_box/diagram_header 字号入参校验: 通过")

    # save_fig 异常路径: 非法格式抛 ValueError 且 close=True 时 figure 已 close
    fig_s, _ax_s = plt.subplots(figsize=(3.0, 2.0))
    try:
        save_fig(fig_s, str(Path(tempfile.gettempdir()) / "figkit_bad_fmt"),
                 formats=("png", "bogus"))
        raise AssertionError("非法格式未抛异常")
    except ValueError:
        pass
    assert fig_s.number not in plt.get_fignums(), "save_fig 异常路径未 close figure"
    print("save_fig 非法格式 -> 异常且 figure 已 close: 通过")

    out = Path(tempfile.gettempdir()) / "figkit_diagram_smoke"
    written = save_fig(fig, out)
    print(f"diagram 冒烟: {[Path(p).name for p in written]}")
    for p in written:
        assert Path(p).is_file() and Path(p).stat().st_size > 0, p

    # 冒烟: 数据图最小样张（原有路径回归）
    fig, ax = plt.subplots(figsize=FIGSIZE["default"])
    ax.plot([0, 1, 2], [0, 1, 0], color=load_palette()[0])
    ygrid(ax)
    out = Path(tempfile.gettempdir()) / "figkit_smoke"
    written = save_fig(fig, out)
    print(f"save_fig 冒烟: {[Path(p).name for p in written]}")
    for p in written:
        assert Path(p).is_file() and Path(p).stat().st_size > 0, p
    print("自测完成, 无异常。")
