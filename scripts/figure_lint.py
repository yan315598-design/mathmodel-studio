# -*- coding: utf-8 -*-
"""图表设计规则 lint: 对出图脚本执行后审计 Axes/Figure 设计规则。

规则（每条附中文解释与修复建议）:
  R1 图例项数 > 5 警告, > 8 报错          -> 拆分子图或改直接标注
  R2 折线逐点 marker 且数据点 > 25 警告    -> 去掉 marker 或降密度
  R3 柱状图 y 轴未含 0 警告（log 轴除外）  -> set_ylim 下界归 0
  R4 已标数值的小矩阵热力图带 colorbar 警告 -> 二选一, 信息冗余;
     仅矩阵规模 ≤16×16 触发, 大矩阵场图的等值线行内标签不在此列 (T-08);
     设计卡已声明"格注+色条并存"理由时用 --grid-annotate 声明豁免 (A7)
  R5 标题显示宽度过长（> 28 个中文字符当量）警告 -> 缩短或换行
  R6 使用 jet / rainbow colormap 报错      -> 换 viridis/RdBu_r 等感知均匀色
  R7 未去顶右 spines 警告                  -> 用 templates/figures/style/mathmodel.mplstyle;
     存在 twinx 右轴时豁免右 spine (右轴刻度载体, T-08)
  R8 图内图题: 非空 suptitle 或单面板 set_title 报错, 多面板标题
     > 6 中文字符当量警告                   -> 图名应放在论文 caption, 不在图内;
                                              示意图等特殊版式用 --allow-infigure-title 跳过
  R9 注释预算: 数据图面板解释性文本框 > ANNOTATION_BUDGET(2) 条警告
     -> 图叙事纪律"数据图 ≤2 条解释性注释"; 判据线/参考线/图例/数值标签/
        面板标号 (a)(b) 不计入; A7 起等值线数值标签 (ax.clabel) 与
        "纯数值+单位"串亦豁免（词法判定: 每个 token 去掉数字与数值装饰后
        只能是单位词, 见 `_is_pure_value_label`）; 示意图经 --allow-box-labels
        或 --schematic 豁免

用法:
    python scripts/figure_lint.py <figure.py 或目录> [--strict | --strict-warn]
                                                        [--allow-infigure-title]
                                                        [--allow-box-labels | --schematic]
                                                        [--grid-annotate]
    python scripts/figure_lint.py --self-test

退出码:
    0  无 error 级违例（--strict 下 warn 只列清单不失败）
    1  存在 error 级违例; --strict-warn 时存在任何违例（含警告）
    2  输入不存在 / 出图脚本执行失败等致命错误

语义分层 (A7): `--strict` = 严格模式但**只拦 error**, warn 列清单供逐条确认;
`--strict-warn` = 旧 `--strict` 语义（warn 也拦）。改动理由: 此前 warn 计失败使
CI 语义混乱——R9/R4 这类"启发式近似"的 warn 级规则会把合规图判成失败, 而
`figqa --strict` 的像素碰撞才是硬门禁。
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from figqa import _setup_chinese_font, run_figure_script

STYLE_HINT = (
    "修复建议: plt.style.use(r'<skill>/templates/figures/style/mathmodel.mplstyle')"
)

LEGEND_WARN, LEGEND_ERROR = 5, 8
MARKER_POINT_LIMIT = 25
HEATMAP_MAX_CELLS = 16  # "小矩阵"判定: 标注单元数上限
TITLE_CJK_LIMIT = 28.0  # 中文字符当量
PANEL_TITLE_CJK_LIMIT = 6.0  # R8: 多面板 panel 标题中文字符当量上限
BAD_CMAPS = {"jet", "rainbow"}
ANNOTATION_BUDGET = 2  # R9: 数据图单面板解释性文本条数上限（判据线/图例等不计）
PANEL_LABEL_RE = re.compile(r"^\([a-zA-Z]\)$")  # 面板标号 (a)/(b)/…（不计注释）
# A7: 纯数值+单位形态（如 "30 ℃"、"0.3 kg/kg"、"0.42 h"、"12.5%"）——量化标签,
# 不计入 R9 注释预算（纪律 ⑥ 鼓励这类标注）。判定用**词法结构**而不是字符白名单:
# 每个空白/顿号分隔的 token 要么含数字, 要么是单位词（显式白名单）或单位组合
# （kg/kg、m/s、W/(m·K)）。纯字符白名单两次被复审证伪: 先是 "Hmm..." 这类纯字母串
# 被误豁免, 放宽字母后又把 "Model improves after 10 iterations" 整句放过。
# 数字判定用 any(isdigit) 而非正则前瞻（`.*` 不跨行, 多行标签会漏豁免）。
_UNIT_WORDS = {
    # 拉丁/希腊单位
    "kg", "g", "mg", "ug", "μg", "t", "ton", "m", "cm", "mm", "um", "μm", "km",
    "dm", "nm", "s", "ms", "us", "min", "h", "hr", "d", "day", "k", "℃", "c",
    "°c", "f", "kpa", "pa", "mpa", "gpa", "bar", "atm", "mmhg", "torr",
    "w", "kw", "mw", "j", "kj", "mj", "kcal", "ev", "kev", "kwh",
    "hz", "khz", "mhz", "ghz",
    "n", "kn", "mol", "mmol", "l", "ml", "ul", "μl", "r", "rpm", "db",
    "ppm", "ppb", "%", "‰",
    # 中文单位/量词
    "元", "万元", "亿元", "件", "个", "次", "台", "套", "张", "页", "人",
    "天", "小时", "分钟", "秒", "度", "吨", "克", "千克", "公斤", "斤", "米",
    "厘米", "毫米", "微米", "千米", "公里", "升", "毫升", "千瓦", "度电",
    "赫兹", "帕", "牛", "瓦", "焦",
}
# 数值语法: 整数/小数 + 可选科学计数法指数（1.2e-05 的 e 不是单位词）;
# 单位幂（m^2 / s^-1）的 `^` 与指数在数值剥离阶段一并去掉
_NUM_RE = re.compile(r"(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
_NUM_DECOR_RE = re.compile(r"[\s.,×±%°\-–+^]+")
# micro sign (U+00B5) 与希腊 mu (U+03BC) 是不同码点, 统一到希腊 mu 再比对
_MICRO_MAP = str.maketrans({"\u00b5": "\u03bc", "\u00b0": "\u00b0"})


def _is_unit_token(token: str) -> bool:
    """token 是否为"数值 + 单位"形态: 去掉数值语法与装饰后, 剩余只能是单位词。

    如 "30"、"0.3"、"1.234567e-05"、"123456.789"、"kg/kg"、"m/s"、"m^2"、
    "W/(m·K)" 通过; "示意图盒内说明文字0"、"Model"、"iterations"、"提高"
    不通过（中文/英文词不是单位词）。
    """
    stripped = _NUM_RE.sub(" ", token.translate(_MICRO_MAP))
    stripped = _NUM_DECOR_RE.sub(" ", stripped)
    for part in re.split(r"[\s/·*×]+", stripped):
        core = part.strip("()（）[].")
        # 单位词比对前统一微符号与大小写（µm / μm / UM 等价）
        if core and core.lower().replace("\u00b5", "\u03bc") not in _UNIT_WORDS:
            return False
    return True


def _is_pure_value_label(text: str) -> bool:
    """纯数值+单位标签判定（见上方 A7 说明）。要求至少含一个数字。"""
    if not any(ch.isdigit() for ch in text):
        return False
    return all(_is_unit_token(tok)
               for tok in re.split(r"[\s,;，；、]+", text.strip()) if tok)


@dataclass
class Violation:
    """一条规则违例。severity 取 'warn' 或 'error'。"""

    figure: str
    rule: str
    severity: str
    detail: str


def _cjk_width(text: str) -> float:
    """中文当量宽度: 全角字符计 1, 半角计 0.5。"""
    return sum(1.0 if ord(ch) > 0x2E80 else 0.5 for ch in text)


def _is_numeric_label(text: str) -> bool:
    token = text.strip().replace(",", "").replace("%", "")
    try:
        float(token)
    except ValueError:
        return False
    return True


def _is_quantitative_label(text: str) -> bool:
    """量化标签启发式（R9 豁免用, 比纯数值标签宽一档）。

    图叙事纪律要求过程图/柱图带量化计数（数值/百分比/显著性星号/短前缀）,
    这类标签不是"解释性文字"。两类判定:
      1. 去掉常见数值装饰（千分位/百分号/显著性星号/括号/空白/换行）后
         逐行可解析为 float（如 "0.72**"、"145\\n(48%)"）;
      2. 含数字且中文当量宽度 ≤6 的短定量标注（如 "中位 0.871"、"DE 29代"、
         "R²=0.92"）。长句（如 "首次穿越 λ* = 0.420" 当量 ~9.5）仍计注释。
    已知边界（复审 P2-4）: 规则 2 会放行 "提高 23%"、"显著 3.2倍" 这类
    动词性短评+数字（宽度 ≤6 且含数字即中）——纪律 ⑥ 本身鼓励短定量标注,
    且 R9 仅 warn 级, 属有意接受的启发式近似, 不再收紧。
    """
    stripped_lines = [
        ln.strip().replace(",", "").replace("%", "").replace("*", "")
        .replace("(", "").replace(")", "").replace("（", "").replace("）", "")
        for ln in text.splitlines() if ln.strip()
    ]
    if stripped_lines:
        try:
            for ln in stripped_lines:
                float(ln)
            return True
        except ValueError:
            pass
    if any(ch.isdigit() for ch in text) and _cjk_width(text) <= 6.0:
        return True
    return False


def _contour_label_ids(ax) -> set[int]:
    """收集等值线数值标签 (ax.clabel) 的 Text 对象 id（R9 豁免用, 清单 A7）。

    等值线数值标签是量化标签（cn_presentation_spec §7.2 明写"量化标签不计入
    注释预算"），但 ax.clabel 生成的 Text 会进 ax.texts, 与解释性注释同池。
    归属判据取 QuadContourSet.labelTexts（mpl 稳定公开属性, 实测与 ax.texts
    中的对象同一）, 不同版本漂移时退回空集（不豁免, 保持旧行为）。
    """
    ids: set[int] = set()
    for coll in getattr(ax, "collections", []):
        for text in getattr(coll, "labelTexts", []) or []:
            ids.add(id(text))
    return ids


def _explanatory_notes(ax) -> list[str]:
    """收集该面板的解释性文本（R9 判定近似法）。

    ax.texts 本就不含轴标签与刻度（它们挂在 xaxis/yaxis 上）; 在此基础上
    再豁免: 面板标号 (a)/(b)、数值/量化标签、与图例条目同文的文本（判据线/
    参考线常以内联文本代替图例, 与图例同文即视为判据层标注而非解释）、
    等值线数值标签（A7: QuadContourSet.labelTexts 归属）、纯数值+单位串
    （A7: 词法判定, 见 `_is_pure_value_label`）
    （A7: 如 "30 ℃"、"0.42 h"）、极坐标类别刻度标签。
    剩余长度 ≥4 的文本视为解释性注释。
    """
    legend_texts = set()
    legend = ax.get_legend()
    if legend is not None:
        legend_texts = {t.get_text().strip() for t in legend.get_texts()}
    contour_ids = _contour_label_ids(ax)
    is_polar = getattr(ax, "name", "") == "polar"
    if is_polar:
        try:
            r_thresh = 0.9 * float(ax.get_rmax())
        except Exception:
            is_polar = False
    notes: list[str] = []
    for artist in ax.texts:
        text = artist.get_text().strip()
        if len(text) < 4:
            continue
        if PANEL_LABEL_RE.match(text):
            continue
        if _is_quantitative_label(text):
            continue
        if id(artist) in contour_ids:
            continue
        if _is_pure_value_label(text):
            continue
        if text in legend_texts:
            continue
        if is_polar:
            try:
                _theta, r = artist.get_position()
                if float(r) >= r_thresh:
                    continue  # 极轴类别刻度标签（雷达图类别名）
            except Exception:
                pass
        notes.append(text)
    return notes


def _axes_titles(ax) -> list[str]:
    """收集 axes 全部非空标题: center/left/right 三个位置各查一次, 去重保序。

    R5/R8 均不能只读居中标题——set_title(..., loc="left"/"right") 时
    get_title()（居中位）返回空串, 只查居中会漏检。
    """
    titles: list[str] = []
    for loc in ("center", "left", "right"):
        try:
            text = ax.get_title(loc=loc).strip()
        except Exception:
            text = ""
        if text and text not in titles:
            titles.append(text)
    return titles


def _is_colorbar_axes(ax) -> bool:
    """判定 colorbar 附属轴。

    fig.colorbar() 会向 fig.axes 追加一个附属轴; 若按 len(fig.axes) 数面板,
    单热力图 + colorbar 会被误判成双面板, 绕过 R8 单面板标题检查。
    判定信号按版本从新到旧回退（_colorbar 是私有属性, 不能只依赖它存在）:
    1. ax._colorbar 指向 Colorbar 实例（新版 mpl 在 colorbar 轴上挂该引用）;
    2. isinstance(ax, Colorbar)（部分版本 Colorbar 以 Axes 子类身份直接进 fig.axes）;
    3. 默认 label 恰为 '<colorbar>'（make_axes 的历史稳定默认值, 旧版 mpl 回退信号）。
    """
    from matplotlib.colorbar import Colorbar

    if isinstance(getattr(ax, "_colorbar", None), Colorbar):
        return True
    if isinstance(ax, Colorbar):
        return True
    try:
        return ax.get_label() == "<colorbar>"
    except Exception:
        return False


def _twinned_with(a, b) -> bool:
    """a 与 b 是否为 twinx/twiny 双轴关系（共享同一绘图区）。"""
    grouper = getattr(a, "_twinned_axes", None)
    if grouper is None:
        return False
    try:
        return b in grouper.get_siblings(a)
    except Exception:
        return False


def _count_logical_panels(fig) -> int:
    """统计逻辑面板数: 排除 colorbar 附属轴; twinx/twiny 双轴与其宿主算同一面板。

    R8 的单面板/多面板分支据此判定, 不能直接用 len(fig.axes)。
    """
    panels: list[list] = []
    for ax in fig.axes:
        if _is_colorbar_axes(ax):
            continue
        for panel in panels:
            if any(_twinned_with(member, ax) for member in panel):
                panel.append(ax)
                break
        else:
            panels.append([ax])
    return len(panels)


def _axes_overlap(a, b) -> bool:
    """两 axes 绘图区位置是否重叠 (figure 坐标系 bbox 相交)。"""
    try:
        return a.get_position().overlaps(b.get_position())
    except Exception:
        return False


def _yticks_on_right(ax) -> bool:
    """y 轴刻度/刻度标签是否位于右侧 (twinx 右轴特征)。"""
    try:
        if ax.yaxis.get_ticks_position() == "right":
            return True
    except Exception:
        pass
    try:
        return ax.yaxis.get_label_position() == "right"
    except Exception:
        return False


def _is_twinned_right_carrier(ax, fig) -> bool:
    """ax 的 right spine 是否为 twinx 双轴对的刻度载体 (axes 级判定, 复审 P1-3)。

    用 matplotlib 内部 grouper (`_twinned_with`) 判定双轴关系, 不用"位置重叠 +
    刻度居右"启发式——后者会把 inset 轴压主轴误判为 twinx, 且全图作用域的豁免
    会让混排图中普通子图的 right spine 漏报。
    """
    for other in fig.axes:
        if other is ax or _is_colorbar_axes(other):
            continue
        if _twinned_with(ax, other) or _twinned_with(other, ax):
            if _yticks_on_right(ax) or _yticks_on_right(other):
                return True
    return False


def _image_matrix_shape(images: list) -> tuple[int, int] | None:
    """估计热力图/场图的矩阵规模 (行, 列)。

    取第一个可判定的 2-D 数据源: imshow 的 get_array() 直接是 (M, N);
    QuadMesh (pcolormesh) 旧版 get_array() 为展平数组, 回退到角点坐标
    get_coordinates() 的 (M+1, N+1) 网格。均无法判定时返回 None。
    """
    for artist in images:
        get_array = getattr(artist, "get_array", None)
        if get_array is not None:
            try:
                arr = get_array()
            except Exception:
                arr = None
            if arr is not None and getattr(arr, "ndim", 0) == 2:
                return (arr.shape[0], arr.shape[1])
        get_coords = getattr(artist, "get_coordinates", None)
        if get_coords is not None:
            try:
                coords = get_coords()
                return (coords.shape[0] - 1, coords.shape[1] - 1)
            except Exception:
                pass
    return None


def lint_figure(fig, name: str, allow_infigure_title: bool = False,
                allow_box_labels: bool = False,
                grid_annotate: bool = False) -> list[Violation]:
    """对单个 Figure 执行全部规则, 返回违例列表。

    allow_infigure_title: True 时跳过 R8 图内图题规则（示意图/特殊版式逃生门）。
    allow_box_labels: True 时跳过 R9 注释预算规则（示意图盒内标签/说明是
        合法版式; --schematic 显式路由走同一豁免）。
    grid_annotate: True 时跳过 R4 热图冗余规则（A7 声明位: 设计卡已声明
        "格注 + 色条并存"的理由——如逐格数值是结论本身、色条负责跨面板可比,
        两者不冗余; 只跳过 R4, 不影响其它规则）。
    """
    out: list[Violation] = []

    def add(rule: str, severity: str, detail: str) -> None:
        out.append(Violation(name, rule, severity, detail))

    has_colorbar = any(
        getattr(ax, "_colorbar", None) is not None for ax in fig.axes
    )

    for ax in fig.axes:
        # R1 图例项数
        legend = ax.get_legend()
        if legend is not None:
            n = len(legend.get_texts())
            if n > LEGEND_ERROR:
                add("R1-图例项数", "error", f"图例 {n} 项 (> {LEGEND_ERROR}), 评委阅读负担过重; 建议拆子图或直接标注")
            elif n > LEGEND_WARN:
                add("R1-图例项数", "warn", f"图例 {n} 项 (> {LEGEND_WARN}); 建议精简")

        # R2 逐点 marker 且点数过多
        for ln in ax.lines:
            xy = ln.get_xydata()
            if ln.get_marker() not in ("", "None", None, "none") and len(xy) > MARKER_POINT_LIMIT:
                add(
                    "R2-逐点marker",
                    "warn",
                    f'折线 "{ln.get_label()[:20]}" {len(xy)} 个点仍逐点 marker, 300dpi 下糊成串; '
                    "建议去掉 marker 或抽样",
                )

        # R3 柱状图 y 轴未含 0
        from matplotlib.container import BarContainer

        has_bars = any(isinstance(c, BarContainer) for c in ax.containers)
        ymin, _ = ax.get_ylim()
        if has_bars and ax.get_yscale() != "log" and ymin > 1e-9:
            add(
                "R3-柱图截零",
                "warn",
                f"柱状图 y 轴下界 {ymin:.3g} > 0, 截零柱高会夸大差异; log 轴除外, 建议下界归 0",
            )

        # R4 已标数值的小矩阵热力图 + colorbar 冗余
        # (T-08: 矩阵规模 >16×16 的大场图不触发——等值线行内标签是定向标注,
        #  非逐格标注; 矩阵规模无法判定时维持原判定)
        images = list(ax.get_images()) + [
            c for c in ax.collections if type(c).__name__ == "QuadMesh"
        ]
        numeric_texts = [t for t in ax.texts if _is_numeric_label(t.get_text())]
        if (images and 0 < len(numeric_texts) <= HEATMAP_MAX_CELLS and has_colorbar
                and not grid_annotate):
            shape = _image_matrix_shape(images)
            small_matrix = shape is None or (
                shape[0] <= HEATMAP_MAX_CELLS and shape[1] <= HEATMAP_MAX_CELLS)
            if small_matrix:
                add(
                    "R4-热图colorbar冗余",
                    "warn",
                    f"小矩阵热力图已逐格标注 {len(numeric_texts)} 个数值又带 colorbar, 信息冗余; 建议二选一",
                )

        # R6 jet / rainbow colormap
        for artist in images:
            cmap = getattr(artist, "get_cmap", lambda: None)()
            if cmap is not None and cmap.name.lower() in BAD_CMAPS:
                add(
                    "R6-劣质cmap",
                    "error",
                    f"使用 {cmap.name} colormap, 亮度不单调且对色盲不友好; "
                    "建议 viridis（连续）或 RdBu_r（发散）",
                )

        # R7 去顶右 spines
        # 注: 极坐标(PolarAxes)的 spines 只有 polar/start/end/inner, 无 top/right,
        # 用 get() 容错跳过; 雷达图等极坐标图不适用此规则。
        # T-08: twinx 双轴对的 right spine 是右轴刻度载体, 按 axes 级豁免 (top 仍需去除);
        # 混排图中普通子图的 right spine 不豁免 (复审 P1-3: 豁免从全图作用域细化到 axes)。
        visible = [
            k for k in ("top", "right")
            if k in ax.spines and ax.spines[k].get_visible()
        ]
        if "right" in visible and _is_twinned_right_carrier(ax, fig):
            visible = [k for k in visible if k != "right"]
        if visible:
            add(
                "R7-spines",
                "warn",
                f"顶/右 spines 未去除 ({'/'.join(visible)}); {STYLE_HINT}",
            )

        # R9 注释预算: 数据图单面板解释性文本 ≤ ANNOTATION_BUDGET 条
        # （判据线/参考线图例文本、数值标签、面板标号均不计入; 示意图
        #   经 allow_box_labels/--schematic 整体豁免）
        if not allow_box_labels:
            notes = _explanatory_notes(ax)
            if len(notes) > ANNOTATION_BUDGET:
                preview = "; ".join(notes[:3])
                add(
                    "R9-注释预算",
                    "warn",
                    f"面板解释性文本 {len(notes)} 条 (> {ANNOTATION_BUDGET}): "
                    f"“{preview}…”; 数据图注释预算 ≤{ANNOTATION_BUDGET} 条"
                    "（判据线/图例/数值标签不计）, 建议移入论文 caption 或精简; "
                    "示意图可用 --allow-box-labels/--schematic 豁免",
                )

    # R5 标题过宽
    titles = []
    for ax in fig.axes:
        titles.extend(_axes_titles(ax))  # center/left/right 三位置全查
    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is not None and suptitle.get_text().strip():
        titles.append(suptitle.get_text())
    for title in titles:
        width = _cjk_width(title)
        if width > TITLE_CJK_LIMIT:
            add(
                "R5-标题过宽",
                "warn",
                f"标题显示宽度 {width:.1f} 当量字符 (> {TITLE_CJK_LIMIT:g}): “{title[:30]}…”; "
                "建议缩短或拆两行",
            )

    # R8 图内图题: 图名应放在论文 caption（"图 X …"题注）, 不在图内。
    # 数据图纪律; 示意图/特殊版式可用 --allow-infigure-title 跳过本规则。
    if not allow_infigure_title:
        suptitle = getattr(fig, "_suptitle", None)
        if suptitle is not None and suptitle.get_text().strip():
            add(
                "R8-图内图题",
                "error",
                f"图内出现 suptitle “{suptitle.get_text()[:30]}”: 图名应放在论文 caption, "
                "不在图内; 示意图等特殊版式可用 --allow-infigure-title 跳过",
            )
        n_panels = _count_logical_panels(fig)
        for ax in fig.axes:
            for title in _axes_titles(ax):
                if n_panels == 1:
                    add(
                        "R8-图内图题",
                        "error",
                        f"单面板图内出现标题 “{title[:30]}”: 图名应放在论文 caption, "
                        "不在图内; 示意图等特殊版式可用 --allow-infigure-title 跳过",
                    )
                else:
                    width = _cjk_width(title)
                    if width > PANEL_TITLE_CJK_LIMIT:
                        add(
                            "R8-图内图题",
                            "warn",
                            f"多面板 panel 标题 “{title[:30]}” 宽 {width:.1f} 当量字符 "
                            f"(> {PANEL_TITLE_CJK_LIMIT:g}), 只允许短轴含义标签（如 ROC/PR/残差）; "
                            "图名放论文 caption",
                        )
    return out


def _figure_name(fig, index: int, script: Path) -> str:
    for getter in (
        lambda: fig._suptitle.get_text() if getattr(fig, "_suptitle", None) else "",
        lambda: fig.axes[0].get_title() if fig.axes else "",
    ):
        try:
            text = getter().strip()
        except Exception:
            text = ""
        if text:
            return text[:40]
    return f"{script.name}#图{index + 1}"


def print_report(script: Path, violations: list[Violation]) -> None:
    print(f"\n[脚本] {script}")
    if not violations:
        print("  ✅ 无违例")
        return
    for v in violations:
        mark = "❌" if v.severity == "error" else "⚠️ "
        print(f"  {mark} {v.rule}({v.severity}): {v.detail}  [图: {v.figure}]")


def check_path(target: Path, strict: bool, allow_infigure_title: bool = False,
               allow_box_labels: bool = False, grid_annotate: bool = False,
               strict_warn: bool = False) -> int:
    """检测单个脚本或目录, 返回退出码。

    allow_infigure_title: True 时跳过 R8 图内图题规则（示意图/特殊版式逃生门）。
    allow_box_labels: True 时跳过 R9 注释预算规则（示意图逃生门）。
    grid_annotate: True 时跳过 R4 热图冗余规则（A7 声明位: 设计卡已声明
        "格注 + 色条并存"理由）。
    strict / strict_warn (A7): `--strict` = 严格模式, **error 计失败、warn 只列
        清单不失败**（清单末尾提示改用 --strict-warn）; `--strict-warn` = 旧语义
        （warn 也计入失败）。默认（两者都无）= 仅 error 计失败。
    """
    if target.is_dir():
        scripts = sorted(p for p in target.glob("*.py") if p.name != "__init__.py")
    else:
        scripts = [target]
    if not scripts:
        print(f"输入不存在或目录无 .py 脚本: {target}")
        return 2
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _setup_chinese_font(plt)
    all_violations: list[Violation] = []
    failures = 0
    for script in scripts:
        try:
            figures = run_figure_script(script)
        except Exception as exc:
            print(f"\n[脚本] {script}\n  ❌ 执行失败: {exc}")
            failures += 1
            continue
        script_violations: list[Violation] = []
        for idx, fig in enumerate(figures):
            script_violations.extend(lint_figure(
                fig, _figure_name(fig, idx, script),
                allow_infigure_title=allow_infigure_title,
                allow_box_labels=allow_box_labels,
                grid_annotate=grid_annotate))
            plt.close(fig)
        print_report(script, script_violations)
        all_violations.extend(script_violations)
    errors = [v for v in all_violations if v.severity == "error"]
    warns = [v for v in all_violations if v.severity == "warn"]
    print(f"\n共检测 {len(scripts) - failures} 个脚本: {len(errors)} 错误, {len(warns)} 警告。")
    if failures:
        return 2
    if warns and strict:
        print(f"⚠ warn 清单 {len(warns)} 条（--strict: 不阻断, 逐条确认即可; "
              f"需要 warn 阻断请用 --strict-warn）")
    if errors or (strict_warn and all_violations) or (strict and errors):
        return 1
    return 0


def _self_test() -> int:
    """合成图验证 8 条规则均可触发、正确图零误报。"""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    _setup_chinese_font(plt)
    violations: dict[str, list[Violation]] = {}

    # 触发 R1/R2/R3/R6/R7/R8(suptitle)/R9 的图
    fig, ax = plt.subplots(figsize=(6, 4))
    for i in range(9):
        ax.plot(np.linspace(0, 1, 40), label=f"序列{i}", marker="o")
    ax.bar([0.5], [5])
    ax.set_ylim(3, 5)
    im = ax.imshow(np.random.rand(2, 2), cmap="jet", extent=[0, 1, 0, 1], aspect="auto")
    fig.colorbar(im)
    ax.legend()
    fig.suptitle("不该出现的图内总标题")  # R8: suptitle -> error
    ax.text(0.3, 0.4, "第一条解释性注释")  # R9: 超预算的解释性文本
    ax.text(0.3, 0.6, "第二条解释性注释")
    ax.text(0.3, 0.8, "第三条解释性注释")
    violations["bad"] = lint_figure(fig, "规则触发图")
    plt.close(fig)

    # 触发 R4 的小矩阵热力图 + colorbar
    fig, ax = plt.subplots()
    data = np.random.rand(3, 3)
    im = ax.imshow(data, cmap="viridis")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center")
    fig.colorbar(im)
    violations["heatmap"] = lint_figure(fig, "热力图冗余")
    plt.close(fig)

    # 触发 R5 的超长标题
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    ax.set_title("这是一段特别特别特别特别特别特别特别特别长的论文图表标题用来触发规则五")
    violations["title"] = lint_figure(fig, "长标题图")
    plt.close(fig)

    # 正确图: 应零违例（单面板不放图内标题, 图名进 caption）
    fig, ax = plt.subplots()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.plot(np.linspace(0, 1, 10), marker="o", label="仅一例")
    ax.bar([0.2], [1])
    ax.set_ylim(0, None)
    ax.legend()
    violations["clean"] = lint_figure(fig, "干净图")
    plt.close(fig)

    ok = True
    rules_hit = {v.rule.split("-")[0] for v in violations["bad"] + violations["heatmap"] + violations["title"]}
    for rule_id in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"):
        if rule_id not in rules_hit:
            print(f"[自测] ❌ 规则 {rule_id} 未被触发")
            ok = False
        else:
            print(f"[自测] ✅ 规则 {rule_id} 已触发")
    if violations["clean"]:
        print(f"[自测] ❌ 干净图被误报 {len(violations['clean'])} 处:")
        for v in violations["clean"]:
            print(f"        {v.rule}: {v.detail}")
        ok = False
    else:
        print("[自测] ✅ 干净图 0 误报")
    print("[自测] " + ("全部通过 ✅" if ok else "存在失败 ❌"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="图表设计规则 lint: 图例密度/marker/截零/colorbar 冗余/标题宽度/cmap/spines/图内图题/注释预算"
    )
    parser.add_argument("target", nargs="?", help="figure.py 脚本或其所在目录")
    parser.add_argument("--strict", action="store_true",
                        help="严格模式: error 计失败; warn 只列清单不失败（A7 起; "
                             "需要 warn 阻断请用 --strict-warn）")
    parser.add_argument("--strict-warn", action="store_true",
                        help="warn 也计入失败（A7 前的 --strict 旧语义）")
    parser.add_argument("--allow-infigure-title", action="store_true",
                        help="跳过 R8 图内图题规则（示意图/特殊版式逃生门）")
    parser.add_argument("--allow-box-labels", action="store_true",
                        help="跳过 R9 注释预算规则（示意图盒内标签/说明逃生门）")
    parser.add_argument("--grid-annotate", action="store_true",
                        help="跳过 R4 热图冗余规则（设计卡已声明格注+色条并存理由）")
    parser.add_argument("--schematic", action="store_true",
                        help="显式按示意图路由检查（等价 --allow-box-labels 的 R9 豁免）")
    parser.add_argument("--self-test", action="store_true", help="内置合成图自测")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()
    if not args.target:
        parser.error("需要提供 figure.py 或目录, 或使用 --self-test")
    target = Path(args.target).expanduser()
    if not target.exists():
        print(f"输入不存在: {target}")
        return 2
    return check_path(target, args.strict,
                      allow_infigure_title=args.allow_infigure_title,
                      allow_box_labels=args.allow_box_labels or args.schematic,
                      grid_annotate=args.grid_annotate,
                      strict_warn=args.strict_warn)


if __name__ == "__main__":
    sys.exit(main())
