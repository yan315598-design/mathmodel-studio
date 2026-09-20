# -*- coding: utf-8 -*-
"""图表渲染碰撞检测（figure QA）。

对出图脚本逐一执行（runpy, Agg 后端）, 渲染后收集 Figure 内文本/图例/
色块/折线/散点的像素级 bounding box, 检测七类常见排版碰撞:

  1. text-over-patch        文本压在柱形/色块上（数值标签完全落在宿主柱内时豁免）
  2. legend-over-patch      图例框压住柱形/色块
  3. line-through-text      折线穿过文本框（线段-矩形求交用 Liang-Barsky 裁剪算法）
  4. point-under-text       数据点（marker/散点）落在文本框下
  5. text-over-text         文本框互相重叠（同一坐标轴的相邻刻度标签豁免）
  6. clipped-out-of-figure  文本/图例超出画布边界被裁掉
  7. artist-bbox 相交       artist 语义级遮挡（get_window_extent 窗口 bbox）:
     - text-over-inset          文本被 inset 放大区整块盖住（A4/S-10 实测盲区）
     - text-over-legend         文本压图例框（图例内自身文本豁免）
     - legend-text-overlap      图例条目文本与其他文本重叠（同图例条目互检豁免）
     - tick-label-overlap       同轴相邻刻度标签叠印（x/y 轴与色条各自成组;
                                 A4: 色条 0.15/0.20 叠印 8.9px² 原不报）。
                                 旋转标签只按**旋转排版矩形**提示（包围盒 45°
                                 时放大约 √2 倍会假报; 排版框相交 ≠ 墨迹相交,
                                 无墨迹证据故一律 ⚠️ 不进硬门）
     - legend-over-line         图例框压折线/参考线, ⚠️ 仅提示不阻断（合法穿越常见）

语义参照公开的 "bounding-box overlap QA" 思路, 全部自写实现。

用法:
    python scripts/figqa.py <figure.py 或目录> [--strict]
    python scripts/figqa.py --self-test

--strict 时只要检出任何 ❌ 级碰撞即退出码 1（⚠️ 提示级不阻断）,
便于接 CI/提交流水线。

退出码:
    0  未检出碰撞, 或 --self-test 全部通过
    1  --strict 下检出 ❌ 级碰撞; --self-test 期望不满足
    2  输入不存在 / 出图脚本执行失败等致命错误

已知限制:
    - 文本-色块检测只覆盖 ax.patches（柱形 Rectangle/多边形）,
      imshow/QuadMesh 热力图上的数值标注（有意为之的常见用法）不在检测范围;
    - 刻度标签与网格线不参与 line-through-text / point-under-text;
    - 阴影区（axhspan）内放文字会被按 text-over-patch 报出。
"""

from __future__ import annotations

import argparse
import math
import runpy
import sys
from dataclasses import dataclass
from pathlib import Path

# 容差常量: 重叠面积小于 MIN_AREA_PX 视为噪声; 求交前把文本框四边内缩
# INSET_PX, 避免贴边/切线级别的接触被误报。
MIN_AREA_PX = 2.0
INSET_PX = 0.75
# 第七类 artist-bbox 相交专用阈值: 文本/图例/inset 之间的窗口 bbox 相交
# 面积大于该值才报（比 MIN_AREA_PX 保守, 给版式贴边留余量）;
# 同轴相邻刻度标签叠印用更严的 TICK_AREA_PX（色条 0.15/0.20 叠印 8.9px²
# 属于必须报出的量级, 而 locator 自动排布的刻度留白通常 >4px）。
ARTIST_AREA_PX = 4.0
TICK_AREA_PX = 2.0
# 旋转刻度标签: 轴对齐包围盒在 30-45° 时必然比排版矩形大（45° 约 √2 倍）, 直接拿
# 包围盒重叠判"相邻刻度叠印"会把斜排标签误报成碰撞（实测: 相邻类别标签包围盒
# 相交 2200-3600px² 而字形零重叠, A 题 Q6_F2 同型）。判据改为: 先把包围盒换算回
# 旋转**排版矩形**（文本排版框, 不是墨迹轮廓）再求交（见 _rotated_glyph_rect）。
# 但排版矩形相交 ≠ 墨迹相交: 细笔画/长空白文本（如 "I    I"）排版框交 455px²
# 而真实墨迹 0 像素。**本检测不测墨迹**, 拿不到墨迹证据就不进硬门——旋转标签
# 一律 ⚠️ 提示, 只有非旋转标签按绝对面积阈值判 ❌。
ROT_SHAPE_TOL_PX = 1.0        # 换算包围盒尺寸与实测尺寸的允许差（px）
ROT_SAME_ANGLE_TOL_DEG = 1.0  # 相邻两标签视为同角度的允许差（度）
# 越界检测专用: matplotlib 默认布局下刻度/轴标签常有 <5px 的画布微越界,
# 且 skill 标准样式 savefig.bbox=tight 落盘时会自动扩边收回, 不算真裁剪;
# 自由文本/图例仍按 INSET_PX 严格判。
CLIP_TOLERANCE_MANAGED_PX = 5.0

KIND_TEXT_OVER_PATCH = "text-over-patch"
KIND_LEGEND_OVER_PATCH = "legend-over-patch"
KIND_LINE_THROUGH_TEXT = "line-through-text"
KIND_POINT_UNDER_TEXT = "point-under-text"
KIND_TEXT_OVER_TEXT = "text-over-text"
KIND_CLIPPED = "clipped-out-of-figure"
# 第七类: artist 语义级遮挡（窗口 bbox 相交）
KIND_TEXT_OVER_INSET = "text-over-inset"
KIND_TEXT_OVER_LEGEND = "text-over-legend"
KIND_LEGEND_TEXT_OVERLAP = "legend-text-overlap"
KIND_TICK_LABEL_OVERLAP = "tick-label-overlap"
KIND_LEGEND_OVER_LINE = "legend-over-line"

SEV_ERROR = "error"
SEV_WARN = "warn"

KIND_CN = {
    KIND_TEXT_OVER_PATCH: "文本压色块",
    KIND_LEGEND_OVER_PATCH: "图例压色块",
    KIND_LINE_THROUGH_TEXT: "折线穿文本",
    KIND_POINT_UNDER_TEXT: "数据点压文本",
    KIND_TEXT_OVER_TEXT: "文本互相重叠",
    KIND_CLIPPED: "越界被裁剪",
    KIND_TEXT_OVER_INSET: "文本压inset放大区",
    KIND_TEXT_OVER_LEGEND: "文本压图例框",
    KIND_LEGEND_TEXT_OVERLAP: "图例文本重叠",
    KIND_TICK_LABEL_OVERLAP: "刻度标签叠印",
    KIND_LEGEND_OVER_LINE: "图例压折线",
}


@dataclass
class Collision:
    """一条碰撞记录。position 为重叠区中心或文本框中心（像素, 左下原点）。

    severity: "error"（❌, 计入 --strict 失败）或 "warn"（⚠️ 仅提示,
    合法场景常见, 不阻断）。默认 error, 与历史行为一致。
    """

    figure: str
    kind: str
    detail: str
    position: tuple[float, float]
    severity: str = SEV_ERROR


# ============================================================
# 几何工具（教科书算法, 自实现）
# ============================================================
def _shrink(bbox, inset: float):
    """把 bbox 四边各内缩 inset 像素, 返回 (x0, y0, x1, y1)。"""
    return (
        bbox.x0 + inset,
        bbox.y0 + inset,
        bbox.x1 - inset,
        bbox.y1 - inset,
    )


def _overlap_area(a, b) -> float:
    """两个 bbox 的重叠面积; 不相交返回 0。"""
    w = min(a.x1, b.x1) - max(a.x0, b.x0)
    h = min(a.y1, b.y1) - max(a.y0, b.y0)
    if w <= 0 or h <= 0:
        return 0.0
    return w * h


def _bbox_area(box) -> float:
    """bbox 面积。"""
    return max(box.x1 - box.x0, 0.0) * max(box.y1 - box.y0, 0.0)


def _rotation_of(artist) -> bool:
    """文本是否带旋转（>1°）。旋转文本的轴对齐 bbox 会放大, 不能直接比面积。"""
    try:
        return abs(float(artist.get_rotation()) % 180.0) > 1.0
    except Exception:
        return False


def _rotated_glyph_rect(artist, renderer):
    """旋转文本的**旋转排版矩形** (cx, cy, w, h, deg) + 证据串。

    注意这不是墨迹轮廓: `get_window_extent` 给的是文本**排版框**（含行距与
    空白字符宽度）, 空白多的文本（`"I        I"`）排版框很宽而墨迹只在两端。
    本函数只做几何换算, 不含像素测量。

    旋转文本的 `get_window_extent` 给的是**轴对齐包围盒**: 45° 时比排版框大
    约 √2 倍, 直接拿它与邻标签求交会把"斜排相邻标签"误报成叠印（实测相邻类别
    标签包围盒相交 2200-3600px² 而字形零重叠）。换算办法:

      1. 临时把 rotation 归零, 量未旋转排版框 (w, h);
      2. 用 (w, h, θ) 预测包围盒尺寸 `w|cosθ|+h|sinθ|` × `w|sinθ|+h|cosθ|`,
         与实测包围盒逐边比对——**自洽才可信**: 不一致说明归零引出了重排
         （换行/字号变化）, 换算不成立;
      3. 位置取实测包围盒中心（矩形中心对称, 绕任一点旋转都不改变中心）。

    本函数只做单标签换算, 不涉全局; 相邻标签是否相交由 _rotated_pair_overlap
    判定, 严重级由调用方定（拿不到墨迹证据 → 只提示）。

    Returns:
        ((cx, cy, w, h, deg) | None, 证据串)。证据串含角度与字号, 供报告引用。
    """
    try:
        deg = float(artist.get_rotation()) % 180.0
        fontsize = float(artist.get_fontsize())
    except Exception:
        return None, "旋转角/字号不可读"
    evidence = f"θ={deg:.0f}°, {fontsize:.0f}pt"
    try:
        aabb = artist.get_window_extent(renderer)
        saved = artist.get_rotation()
        artist.set_rotation(0.0)
        try:
            flat = artist.get_window_extent(renderer)
        finally:
            artist.set_rotation(saved)
    except Exception:
        return None, evidence + ", 包围盒不可测"
    rad = math.radians(deg)
    c, s = abs(math.cos(rad)), abs(math.sin(rad))
    pred_w = flat.width * c + flat.height * s
    pred_h = flat.width * s + flat.height * c
    if (abs(pred_w - aabb.width) > ROT_SHAPE_TOL_PX
            or abs(pred_h - aabb.height) > ROT_SHAPE_TOL_PX):
        return None, (evidence + f", 包围盒不自洽(Δw={abs(pred_w - aabb.width):.1f}"
                                 f"px Δh={abs(pred_h - aabb.height):.1f}px)")
    return (
        ((aabb.x0 + aabb.x1) / 2.0, (aabb.y0 + aabb.y1) / 2.0,
         flat.width, flat.height, deg),
        evidence,
    )


def _rotated_pair_overlap(rect_a, rect_b):
    """两个**旋转排版矩形**的交面积; 角度不一致（无法共坐标系）时返回 None。

    两矩形同角时, 把两者一起反向旋转 -θ（刚体变换, 公共枢轴取原点即可保持相对
    位置）→ 在该坐标系里它们都是轴对齐矩形, 交面积即真排版框交面积, 没有包围盒
    放大的水分。交面积 ≠ 墨迹相交（空白多的文本仍会算出不小的交面积）。
    """
    cx_a, cy_a, w_a, h_a, deg_a = rect_a
    cx_b, cy_b, w_b, h_b, deg_b = rect_b
    if abs(deg_a - deg_b) % 180.0 > ROT_SAME_ANGLE_TOL_DEG:
        return None
    rad = math.radians(deg_a)
    c, s = math.cos(rad), math.sin(rad)

    def _frame(x: float, y: float) -> tuple[float, float]:
        return (x * c + y * s, -x * s + y * c)

    ax_, ay_ = _frame(cx_a, cy_a)
    bx_, by_ = _frame(cx_b, cy_b)
    box_a = (ax_ - w_a / 2, ay_ - h_a / 2, ax_ + w_a / 2, ay_ + h_a / 2)
    box_b = (bx_ - w_b / 2, by_ - h_b / 2, bx_ + w_b / 2, by_ + h_b / 2)
    w = min(box_a[2], box_b[2]) - max(box_a[0], box_b[0])
    h = min(box_a[3], box_b[3]) - max(box_a[1], box_b[1])
    return max(w, 0.0) * max(h, 0.0)


def _rect_contains(outer, inner) -> bool:
    """inner 是否完全落在 outer 内（含等号）。"""
    return (
        outer.x0 <= inner.x0 and outer.y0 <= inner.y0
        and outer.x1 >= inner.x1 and outer.y1 >= inner.y1
    )


def _point_in_rect(px: float, py: float, rect) -> bool:
    return rect[0] <= px <= rect[2] and rect[1] <= py <= rect[3]


def liang_barsky_clip(p1, p2, rect):
    """Liang-Barsky 线段裁剪: 求线段 p1-p2 与矩形 rect 的可见部分。

    Args:
        p1, p2: 线段两端点 (x, y)。
        rect: 矩形 (xmin, ymin, xmax, ymax)。

    Returns:
        裁剪后的两端点元组; 线段与矩形无交则返回 None。
    """
    x1, y1 = p1
    x2, y2 = p2
    xmin, ymin, xmax, ymax = rect
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - xmin), (dx, xmax - x1), (-dy, y1 - ymin), (dy, ymax - y1)):
        if p == 0.0:
            if q < 0.0:
                return None
        else:
            r = q / p
            if p < 0.0:
                if r > t1:
                    return None
                if r > t0:
                    t0 = r
            else:
                if r < t0:
                    return None
                if r < t1:
                    t1 = r
    return (x1 + t0 * dx, y1 + t0 * dy), (x1 + t1 * dx, y1 + t1 * dy)


def _is_numeric_label(text: str) -> bool:
    """数值标签启发式: 去掉千分位逗号/百分号/单位空白后可解析为 float。"""
    token = text.strip().replace(",", "").replace("%", "")
    try:
        float(token)
    except ValueError:
        return False
    return True


def _center(bbox) -> tuple[float, float]:
    return ((bbox.x0 + bbox.x1) / 2.0, (bbox.y0 + bbox.y1) / 2.0)


def _overlap_center(a, b) -> tuple[float, float]:
    """两个 bbox 相交区域的中心（无相交时退回 a 的中心）。"""
    return (
        (max(a.x0, b.x0) + min(a.x1, b.x1)) / 2.0,
        (max(a.y0, b.y0) + min(a.y1, b.y1)) / 2.0,
    )


# ============================================================
# 脚本执行与 Figure 收集
# ============================================================
def run_figure_script(script: Path) -> list:
    """在当前进程执行出图脚本, 返回其创建的全部 Figure 对象列表。

    通过临时替换 Figure.__init__ 登记新建对象, 覆盖 plt.figure /
    plt.subplots / 直接实例化 Figure 等全部创建路径; 脚本内部 plt.close
    只解除 pyplot 管理, Figure 及其 canvas 引用仍可用, 渲染分析不受影响。
    """
    import matplotlib.figure as mfigure

    created: list = []
    orig_init = mfigure.Figure.__dict__["__init__"]

    def _recording_init(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        created.append(self)

    mfigure.Figure.__init__ = _recording_init
    saved_argv = sys.argv
    sys.argv = [str(script)]  # 目标脚本的 argparse 不应看到 figqa 自己的参数
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as exc:  # 脚本里 sys.exit(0) 属正常结束
        if exc.code not in (None, 0):
            raise
    finally:
        mfigure.Figure.__init__ = orig_init
        sys.argv = saved_argv
    return created


# ============================================================
# 单图检测
# ============================================================
def _setup_chinese_font(plt) -> None:
    """给 Agg 渲染注入中文回退字体链, 与 mathmodel.mplstyle 约定一致。

    缺中文字形时 CJK 文本会被画成方框, 像素 bbox 测量失真。
    """
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei", "SimHei", "PingFang SC", "Arial Unicode MS",
        "Arial", "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def _visible_tick_texts(ax):
    """取真实可见的刻度标签文本对象。

    get_xticklabels() 会返回 locator 生成的全部刻度, 含视图区间外
    不会被绘制的"幽灵刻度"（其 bbox 常在画布外）, 必须按位置过滤;
    axis("off") 的坐标轴同样整组跳过。
    """
    texts = []
    if not getattr(ax, "axison", True):
        return texts
    for axis in (ax.xaxis, ax.yaxis):
        lo, hi = axis.get_view_interval()
        if lo > hi:
            lo, hi = hi, lo
        for tick in axis.get_major_ticks():
            loc = tick.get_loc()
            if loc is None or not (lo - 1e-9 <= loc <= hi + 1e-9):
                continue
            for label in (tick.label1, tick.label2):
                if (
                    label is not None
                    and label.get_visible()
                    and label.get_text().strip()
                ):
                    texts.append(label)
    return texts


def _collect_texts(fig, renderer):
    """收集图内全部文本的 (artist, bbox, 组别)。组别用于文本互压豁免。"""
    items = []
    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is not None and suptitle.get_text().strip():
        items.append((suptitle, suptitle.get_window_extent(renderer), "suptitle"))
    for ax in fig.axes:
        candidates = [(a, "axes-text") for a in ax.texts]  # 含 Annotation
        for artist in (ax.xaxis.label, ax.yaxis.label):
            if artist is not None and artist.get_text().strip():
                candidates.append((artist, "axis-label"))
        if ax.get_title().strip():
            candidates.append((ax.title, "axes-text"))
        candidates.extend((a, "tick") for a in _visible_tick_texts(ax))
        for artist, role in candidates:
            if not artist.get_text().strip():
                continue
            try:
                bbox = artist.get_window_extent(renderer)
            except Exception:
                continue
            items.append((artist, bbox, role))
    return items


# ============================================================
# 第七类: artist-bbox 相交（窗口级语义遮挡）
# ============================================================
def _collect_legends(fig):
    """收集图级 + 轴级全部 Legend 对象（fig.legend 不在 ax.get_legend 里）。"""
    legends = []
    for ax in fig.axes:
        legend = ax.get_legend()
        if legend is not None:
            legends.append(legend)
    legends.extend(getattr(fig, "legends", []))
    return legends


def _collect_artist_texts(fig, renderer):
    """收集 artist-bbox 检查用的文本: (artist, bbox, 宿主axes或None, 所属legend或None)。

    覆盖 _collect_texts 的全部来源（自由文本/轴名/图名/刻度）另加图例条目
    文本与图例标题; 宿主 axes 用于 inset 豁免（图例文本归 legend.axes 所有,
    图级 legend 的条目归 None）; 所属 legend 用于"同一图例条目互检豁免"与
    "图例自身 bbox 对自己的文本豁免"。
    """
    items: list[tuple] = []

    def _add(artist, owner, legend=None):
        if not artist.get_text().strip():
            return
        try:
            bbox = artist.get_window_extent(renderer)
        except Exception:
            return
        items.append((artist, bbox, owner, legend))

    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is not None:
        _add(suptitle, None)
    for ax in fig.axes:
        for artist in ax.texts:
            _add(artist, ax)
        for artist in (ax.xaxis.label, ax.yaxis.label):
            if artist is not None:
                _add(artist, ax)
        if ax.get_title().strip():
            _add(ax.title, ax)
        for artist in _visible_tick_texts(ax):
            _add(artist, ax)
        legend = ax.get_legend()
        if legend is not None:
            for text in legend.get_texts():
                _add(text, ax, legend)
            if legend.get_title() is not None:
                _add(legend.get_title(), ax, legend)
    for legend in getattr(fig, "legends", []):
        owner = legend.axes  # 图级 legend 为 None
        for text in legend.get_texts():
            _add(text, owner, legend)
        if legend.get_title() is not None:
            _add(legend.get_title(), owner, legend)
    return items


def _axes_family(ax) -> set:
    """ax 自身与其全部后代 axes（inset 嵌套）的集合——inset 自家文本豁免用。"""
    family = {ax}
    stack = list(getattr(ax, "child_axes", []))
    while stack:
        child = stack.pop()
        if child not in family:
            family.add(child)
            stack.extend(getattr(child, "child_axes", []))
    return family


def _collect_insets(fig, renderer):
    """收集 inset 放大区: (inset_axes, bbox)。

    只认 ax.child_axes 中窗口尺寸严格小于宿主的子 axes——旧版 mpl 把 twinx
    也登记为 child, 但其 bbox 与宿主同位同大, 按尺寸排除; 色条 axes 不在
    child_axes 内, 天然不参与（色条留白属于版式约定）。
    """
    insets = []
    for ax in fig.axes:
        try:
            host_box = ax.get_window_extent(renderer)
        except Exception:
            continue
        for child in getattr(ax, "child_axes", []):
            try:
                cbox = child.get_window_extent(renderer)
            except Exception:
                continue
            if (cbox.width < host_box.width - 2.0
                    and cbox.height < host_box.height - 2.0):
                insets.append((child, cbox))
    return insets


def _tick_label_runs(fig):
    """按 (axes, axis) 分组收集可见主刻度 label, 按刻度位置升序。

    每个刻度取其"生效侧"的 label（label1 优先, 无效再取 label2——竖色条的
    刻度文本挂在 label2 侧, 只看 label1 会漏掉色条刻度叠印）。返回
    [(axis_label, [label_artist, ...]), ...]; 相邻叠印只查同组内位置相邻的
    一对——不同轴/不同面板的刻度互不比较（面板相邻属合法版式）。
    """
    runs = []
    for ax in fig.axes:
        if not getattr(ax, "axison", True):
            continue
        for axis, axis_name in ((ax.xaxis, "x"), (ax.yaxis, "y")):
            lo, hi = axis.get_view_interval()
            if lo > hi:
                lo, hi = hi, lo
            pairs = []
            for tick in axis.get_major_ticks():
                loc = tick.get_loc()
                if loc is None or not (lo - 1e-9 <= loc <= hi + 1e-9):
                    continue
                label = None
                for cand in (tick.label1, tick.label2):
                    if (cand is not None and cand.get_visible()
                            and cand.get_text().strip()):
                        label = cand
                        break
                if label is not None:
                    pairs.append((float(loc), label))
            if len(pairs) >= 2:
                pairs.sort(key=lambda t: t[0])
                runs.append((f"{axis_name}轴", [p[1] for p in pairs]))
    return runs


def check_artist_bbox(fig, name: str, renderer, lines) -> list[Collision]:
    """第七类 artist-bbox 相交检查（A4）。

    覆盖像素碰撞管不到的语义级遮挡: inset 盖标注 / 文本压图例 / 图例文本
    与外文叠印 / 同轴相邻刻度叠印（❌）与图例压折线（⚠️ 不阻断）。

    Args:
        lines: analyze_figure 已收集的 [(Line2D, display_points, host_axes)],
            只在图例相交检查里复用, 不另遍历大图全部 artist。
    """
    collisions: list[Collision] = []
    items = _collect_artist_texts(fig, renderer)
    legend_boxes = []
    for legend in _collect_legends(fig):
        try:
            legend_boxes.append((legend, legend.get_window_extent(renderer)))
        except Exception:
            continue

    # --- 7a. 文本压图例框（图例内自身文本豁免） ---
    for artist, bbox, _owner, legend_ref in items:
        for legend, lbox in legend_boxes:
            if legend_ref is legend:
                continue  # 图例自家文本在自家框内, 有意为之
            area = _overlap_area(bbox, lbox)
            if area > ARTIST_AREA_PX:
                collisions.append(
                    Collision(
                        name,
                        KIND_TEXT_OVER_LEGEND,
                        f'文本 "{artist.get_text()[:20]}" 压图例框'
                        f"（{len(legend.get_texts())} 项）重叠 {area:.0f}px²",
                        _overlap_center(bbox, lbox),
                    )
                )
                break

    # --- 7b. 图例条目文本与其他文本叠印（同一图例条目互检豁免） ---
    for i in range(len(items)):
        a_artist, a_box, _ao, a_legend = items[i]
        if a_legend is None:
            continue  # 非图例文本两两叠印由第 5 类 text-over-text 负责
        a_host_box = next(
            (lb for lg, lb in legend_boxes if lg is a_legend), None)
        for j in range(len(items)):
            if i == j:
                continue
            b_artist, b_box, _bo, b_legend = items[j]
            if a_legend is b_legend:
                continue  # 同一图例的条目互检豁免
            if b_legend is not None and j < i:
                continue  # 图例文本×图例文本只按 i<j 报一次
            if (a_host_box is not None
                    and _overlap_area(b_box, a_host_box) > ARTIST_AREA_PX):
                continue  # b 已由 7a 按压图例框报出, 不重复计
            area = _overlap_area(a_box, b_box)
            if area > ARTIST_AREA_PX:
                collisions.append(
                    Collision(
                        name,
                        KIND_LEGEND_TEXT_OVERLAP,
                        f'图例文本 "{a_artist.get_text()[:20]}" 与 '
                        f'"{b_artist.get_text()[:20]}" 重叠 {area:.0f}px²',
                        _overlap_center(a_box, b_box),
                    )
                )

    # --- 7c. 文本被 inset 放大区盖住（inset 自家文本豁免） ---
    for inset, ibox in _collect_insets(fig, renderer):
        family = _axes_family(inset)
        for artist, bbox, owner, _legend_ref in items:
            if owner in family:
                continue  # inset 自身（及其嵌套子 axes）的文本在自家区域内
            area = _overlap_area(bbox, ibox)
            if area > ARTIST_AREA_PX:
                collisions.append(
                    Collision(
                        name,
                        KIND_TEXT_OVER_INSET,
                        f'文本 "{artist.get_text()[:20]}" 被 inset 放大区'
                        f"遮挡 {area:.0f}px²",
                        _overlap_center(bbox, ibox),
                    )
                )

    # --- 7d. 同轴相邻刻度标签叠印（x/y 轴与色条各自成组） ---
    for axis_name, labels in _tick_label_runs(fig):
        boxes = []
        for label in labels:
            try:
                boxes.append((label, label.get_window_extent(renderer)))
            except Exception:
                continue
        for (la, ba), (lb, bb) in zip(boxes, boxes[1:]):
            area = _overlap_area(ba, bb)
            if area <= TICK_AREA_PX:
                continue
            if _rotation_of(la) or _rotation_of(lb):
                # 旋转标签: 轴对齐包围盒 45° 时比排版框大约 √2 倍, 实测相邻
                # 斜排标签包围盒可相交 2200-3600px² 而字形零重叠。换算回旋转
                # 排版矩形再比, 但**排版框相交 ≠ 墨迹相交**（"I        I" 这类
                # 空白多的文本排版框交 455px² 而真实重叠 0 像素）——本检测不测
                # 墨迹, 拿不到墨迹证据就不进硬门: 旋转标签一律 ⚠️ 提示。
                rect_a, ev_a = _rotated_glyph_rect(la, renderer)
                rect_b, ev_b = _rotated_glyph_rect(lb, renderer)
                glyph_area = (_rotated_pair_overlap(rect_a, rect_b)
                              if rect_a is not None and rect_b is not None else None)
                if glyph_area is None:
                    detail = (f'{axis_name}相邻刻度 "{la.get_text()[:20]}" 与 '
                              f'"{lb.get_text()[:20]}" 包围盒相交 {area:.0f}px², '
                              f"旋转排版矩形换算不可信（{ev_a} / {ev_b}, "
                              f"{fig.dpi:.0f}dpi）, 仅供参考")
                else:
                    if glyph_area <= TICK_AREA_PX:
                        continue
                    detail = (f'{axis_name}相邻旋转刻度 "{la.get_text()[:20]}" 与 '
                              f'"{lb.get_text()[:20]}" 排版矩形相交 '
                              f"{glyph_area:.0f}px²（{ev_a} / {ev_b}, "
                              f"{fig.dpi:.0f}dpi）: 无墨迹证据, 仅提示, "
                              f"请目视确认是否真叠字")
                collisions.append(
                    Collision(
                        name,
                        KIND_TICK_LABEL_OVERLAP,
                        detail,
                        _overlap_center(ba, bb),
                        severity=SEV_WARN,
                    )
                )
                continue
            collisions.append(
                Collision(
                    name,
                    KIND_TICK_LABEL_OVERLAP,
                    f'{axis_name}相邻刻度 "{la.get_text()[:20]}" 与 '
                    f'"{lb.get_text()[:20]}" 叠印 {area:.0f}px²',
                    _overlap_center(ba, bb),
                )
            )

    # --- 7e. 图例框压折线/参考线（⚠️ 仅提示, 合法穿越常见） ---
    # 精确到线段与图例框相交（Liang-Barsky）, 不用整条线的包围盒——
    # 对角长线的 bbox 几乎盖满轴区, 纯 bbox 判定会对绝大多数轴内图例误提示。
    # 坐标变换用线自身 transform: axhline/axvline 参考线是混合变换,
    # 套 ax.transData 会得到错误短段（图例压参考线正是最常见的提示场景）。
    import numpy as np

    for legend, lbox in legend_boxes:
        rect = _shrink(lbox, INSET_PX)
        if rect[0] >= rect[2] or rect[1] >= rect[3]:
            continue
        host = legend.axes
        for ln, _pts, ln_ax in lines:
            if host is not None and ln_ax is not host:
                continue
            xy = ln.get_xydata()
            if xy is None or len(xy) < 1:
                continue
            try:
                pts = ln.get_transform().transform(
                    np.asarray(xy, dtype=float))
            except Exception:
                continue
            has_line = ln.get_linestyle() not in ("None", "", None)
            has_marker = ln.get_marker() not in ("", "None", None, "none")
            if not (has_line or has_marker):
                continue
            hit = None
            if has_line and len(pts) >= 2:
                for seg_a, seg_b in zip(pts[:-1], pts[1:]):
                    clipped = liang_barsky_clip(
                        (float(seg_a[0]), float(seg_a[1])),
                        (float(seg_b[0]), float(seg_b[1])),
                        rect,
                    )
                    if clipped is not None:
                        hit = (
                            (clipped[0][0] + clipped[1][0]) / 2.0,
                            (clipped[0][1] + clipped[1][1]) / 2.0,
                        )
                        break
            if hit is None and has_marker:
                for px, py in pts:
                    if _point_in_rect(float(px), float(py), rect):
                        hit = (float(px), float(py))
                        break
            if hit is not None:
                collisions.append(
                    Collision(
                        name,
                        KIND_LEGEND_OVER_LINE,
                        f'图例（{len(legend.get_texts())} 项）压折线 '
                        f'"{ln.get_label()[:20]}"（合法穿越常见, 仅提示）',
                        hit,
                        severity=SEV_WARN,
                    )
                )
    return collisions


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


def analyze_figure(fig, name: str, script: Path | None = None,
                   allow_box_labels: bool = False) -> list[Collision]:
    """渲染单个 Figure 并返回检出的碰撞列表。

    Args:
        allow_box_labels: 豁免"完全落在单个色块内"的文本（流程图/示意图的
            盒内标签是有意设计）; 默认 False 保持严格语义（数值标签豁免仍生效）。
    """
    import numpy as np

    script = script or Path(name)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    collisions: list[Collision] = []

    texts = _collect_texts(fig, renderer)
    patches = []
    lines = []
    markers = []  # (artist, display_points)
    legends = []
    for ax in fig.axes:
        for patch in ax.patches:
            try:
                patches.append((patch, patch.get_window_extent(renderer)))
            except Exception:
                continue
        for ln in ax.lines:
            xy = ln.get_xydata()
            if xy is None or len(xy) < 1:
                continue
            # Reference lines mix axes/data coordinates; use the artist transform.
            pts = ln.get_transform().transform(np.asarray(xy, dtype=float))
            if ln.get_linestyle() not in ("None", "", None) and len(pts) >= 2:
                lines.append((ln, pts, ax))  # 7e 图例压折线按宿主 axes 过滤
            if ln.get_marker() not in ("", "None", None, "none"):
                markers.append((ln, pts))
        from matplotlib.collections import PathCollection

        for coll in ax.collections:
            if not isinstance(coll, PathCollection):
                continue
            offsets = np.asarray(coll.get_offsets())
            if len(offsets) == 0:
                continue
            transform = coll.get_offset_transform()
            markers.append((coll, transform.transform(offsets)))
        legend = ax.get_legend()
        if legend is not None:
            try:
                legends.append((legend, legend.get_window_extent(renderer)))
            except Exception:
                continue

    # --- 1. text-over-patch（数值标签完全落在宿主柱内时豁免） ---
    def _contained_in_exactly_one_patch(bbox) -> bool:
        return sum(1 for _p, pb in patches if _rect_contains(pb, bbox)) == 1

    for artist, bbox, _role in texts:
        for patch, pbox in patches:
            if _overlap_area(bbox, pbox) < MIN_AREA_PX:
                continue
            if _is_numeric_label(artist.get_text()) and _rect_contains(pbox, bbox):
                continue  # 柱内数值标签, 有意为之
            if allow_box_labels and _contained_in_exactly_one_patch(bbox):
                continue  # 流程图/示意图的盒内标签, 有意为之
            area = _overlap_area(bbox, pbox)
            collisions.append(
                Collision(
                    name,
                    KIND_TEXT_OVER_PATCH,
                    f'文本 "{artist.get_text()[:24]}" 与色块重叠 {area:.0f}px²',
                    _center(bbox),
                )
            )
            break

    # --- 2. legend-over-patch ---
    for legend, lbox in legends:
        for patch, pbox in patches:
            area = _overlap_area(lbox, pbox)
            if area < MIN_AREA_PX:
                continue
            collisions.append(
                Collision(
                    name,
                    KIND_LEGEND_OVER_PATCH,
                    f'图例（{len(legend.get_texts())} 项）与色块重叠 {area:.0f}px²',
                    _center(lbox),
                )
            )
            break

    # --- 3. line-through-text ---
    for ln, pts, _ln_ax in lines:
        segs = list(zip(pts[:-1], pts[1:]))
        for artist, bbox, _role in texts:
            rect = _shrink(bbox, INSET_PX)
            if rect[0] >= rect[2] or rect[1] >= rect[3]:
                continue
            hit = any(
                liang_barsky_clip(s[0], s[1], rect) is not None for s in segs
            )
            if hit:
                collisions.append(
                    Collision(
                        name,
                        KIND_LINE_THROUGH_TEXT,
                        f'折线 "{ln.get_label()[:24]}" 穿过文本 '
                        f'"{artist.get_text()[:24]}"',
                        _center(bbox),
                    )
                )

    # --- 4. point-under-text ---
    for artist, pts in markers:
        flat = [(float(x), float(y)) for x, y in pts]
        for text_artist, bbox, _role in texts:
            rect = _shrink(bbox, INSET_PX)
            if rect[0] >= rect[2] or rect[1] >= rect[3]:
                continue
            count = sum(1 for px, py in flat if _point_in_rect(px, py, rect))
            if count:
                label = getattr(artist, "get_label", lambda: "")() or "散点"
                collisions.append(
                    Collision(
                        name,
                        KIND_POINT_UNDER_TEXT,
                        f'"{label}" 的 {count} 个数据点落在文本 '
                        f'"{text_artist.get_text()[:24]}" 下',
                        _center(bbox),
                    )
                )

    # --- 5. text-over-text（同组刻度标签互相豁免） ---
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a_artist, a_box, a_role = texts[i]
            b_artist, b_box, b_role = texts[j]
            if a_role == b_role == "tick":
                continue  # 同轴刻度由 locator 自动排布
            area = _overlap_area(a_box, b_box)
            if area < MIN_AREA_PX:
                continue
            collisions.append(
                Collision(
                    name,
                    KIND_TEXT_OVER_TEXT,
                    f'文本 "{a_artist.get_text()[:20]}" 与 '
                    f'"{b_artist.get_text()[:20]}" 重叠 {area:.0f}px²',
                    (
                        (max(a_box.x0, b_box.x0) + min(a_box.x1, b_box.x1)) / 2.0,
                        (max(a_box.y0, b_box.y0) + min(a_box.y1, b_box.y1)) / 2.0,
                    ),
                )
            )

    # --- 6. clipped-out-of-figure ---
    fb = fig.bbox
    candidates = [
        (
            a,
            b,
            "文本",
            CLIP_TOLERANCE_MANAGED_PX if role in ("tick", "axis-label") else INSET_PX,
        )
        for a, b, role in texts
    ]
    candidates += [(l, b, "图例", INSET_PX) for l, b in legends]
    for artist, bbox, what, tol in candidates:
        if (
            bbox.x0 < fb.x0 - tol or bbox.y0 < fb.y0 - tol
            or bbox.x1 > fb.x1 + tol or bbox.y1 > fb.y1 + tol
        ):
            text = artist.get_text()[:24] if hasattr(artist, "get_text") else ""
            collisions.append(
                Collision(
                    name,
                    KIND_CLIPPED,
                    f"{what} {('`' + text + '`') if text else ''} 超出画布边界",
                    _center(bbox),
                )
            )

    # --- 7. artist-bbox 相交（A4: artist 语义级遮挡, 含 ⚠️ 提示级） ---
    collisions.extend(check_artist_bbox(fig, name, renderer, lines))
    return collisions


# ============================================================
# 报告
# ============================================================
def print_report(script: Path, collisions: list[Collision]) -> None:
    by_kind: dict[str, list[Collision]] = {}
    for c in collisions:
        by_kind.setdefault(c.kind, []).append(c)
    print(f"\n[脚本] {script}")
    if not collisions:
        print("  ✅ 未检出碰撞")
        return
    for kind in (
        KIND_TEXT_OVER_PATCH,
        KIND_LEGEND_OVER_PATCH,
        KIND_LINE_THROUGH_TEXT,
        KIND_POINT_UNDER_TEXT,
        KIND_TEXT_OVER_TEXT,
        KIND_CLIPPED,
        KIND_TEXT_OVER_INSET,
        KIND_TEXT_OVER_LEGEND,
        KIND_LEGEND_TEXT_OVERLAP,
        KIND_TICK_LABEL_OVERLAP,
        KIND_LEGEND_OVER_LINE,
    ):
        for c in by_kind.get(kind, []):
            icon = "⚠️" if c.severity == SEV_WARN else "❌"
            print(
                f"  {icon} {kind}（{KIND_CN[kind]}）: {c.detail}"
                f" @ ({c.position[0]:.0f}, {c.position[1]:.0f})px"
                f"  [图: {c.figure}]"
            )


def _close_new_figures(plt, fignums_before: set) -> None:
    """关掉本次调用新建、分析结束后仍留在全局管理器里的 Figure（脚本间防泄漏）。"""
    for num in set(plt.get_fignums()) - fignums_before:
        plt.close(num)


def check_path(target: Path, strict: bool, allow_box_labels: bool = False) -> int:
    """检测单个脚本或目录下全部 .py 出图脚本, 返回退出码。

    脚本间隔离（评审指摘）: 出图模板自己会调 `apply_style()` 改全局 rcParams,
    不还原会让**后一个脚本在前一个脚本的样式上出图**——检测结果随脚本顺序漂移,
    且不是真实出图状态。故每个脚本前统一回到基线 rcParams, 脚本跑完后再还原,
    并关掉该脚本遗留的 Figure（失败脚本的图不会进分析, 但会一直挂在全局管理器里）。

    脚本用 `sys.exit(非0)` 报依赖缺失/用法错误时, `run_figure_script` 会把
    SystemExit 原样抛出（SystemExit 不是 Exception）——必须在此**局部捕获**并
    计为该脚本失败, 否则一次目录级检测会被单个缺依赖模板整体中断, 且缺依赖的
    模板不能被当成"通过"。
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
    baseline_rc = dict(plt.rcParams)   # 脚本间隔离基线: 含中文字体链设置
    total = 0
    warns = 0
    failures = 0
    for script in scripts:
        plt.rcParams.update(baseline_rc)   # 每个脚本都从干净样式起步
        fignums_before = set(plt.get_fignums())
        try:
            figures = run_figure_script(script)
        except SystemExit as exc:  # 模板自行退出（缺依赖/用法错误）
            code = exc.code if exc.code is not None else 0
            print(f"\n[脚本] {script}\n  ❌ 执行失败: 模板自行退出 (exit={code})")
            failures += 1
            _close_new_figures(plt, fignums_before)
            continue
        except Exception as exc:  # 出图脚本自身失败属于致命错误
            print(f"\n[脚本] {script}\n  ❌ 执行失败: {exc}")
            failures += 1
            _close_new_figures(plt, fignums_before)
            continue
        collisions: list[Collision] = []
        for idx, fig in enumerate(figures):
            try:
                collisions.extend(
                    analyze_figure(
                        fig, _figure_name(fig, idx, script), script,
                        allow_box_labels=allow_box_labels,
                    )
                )
            finally:
                plt.close(fig)
        _close_new_figures(plt, fignums_before)
        print_report(script, collisions)
        total += sum(1 for c in collisions if c.severity != SEV_WARN)
        warns += sum(1 for c in collisions if c.severity == SEV_WARN)
    summary = f"\n共检测 {len(scripts) - failures} 个脚本, 检出 {total} 处碰撞"
    if warns:
        summary += f"（另有 {warns} 处 ⚠️ 提示, 不阻断）"
    print(summary + "。")
    if failures:
        return 2
    if total and strict:
        return 1  # ⚠️ 提示级不计入失败: 图例压折线的合法穿越常见
    return 0


# ============================================================
# 自测
# ============================================================
def _self_test() -> int:
    """内置 5 张合成图验证检出能力: 干净图/文字压线图/图例压柱图/inset盖标注/图例压线。"""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    _setup_chinese_font(plt)

    def make_clean():
        fig, ax = plt.subplots(figsize=(6, 4))
        x = np.linspace(0, 10, 30)
        ax.plot(x, np.sin(x), label="sin(x)")
        ax.plot(x, np.cos(x), label="cos(x)")
        ax.legend(loc="lower left")
        ax.set_title("干净示例图")
        ax.set_xlabel("x")
        ax.set_ylabel("值")
        return fig

    def make_inset_cover_text():
        fig, ax = plt.subplots(figsize=(6, 4))
        x = np.linspace(0, 1, 50)
        ax.plot(x, x)
        ax.text(0.66, 0.66, "关键标注", fontsize=11)  # 被 inset 整块盖住
        axins = ax.inset_axes([0.60, 0.55, 0.36, 0.34])
        axins.plot(x, x)
        return fig

    def make_legend_over_line():
        fig, ax = plt.subplots(figsize=(6, 4))
        x = np.linspace(0, 10, 100)
        ax.plot(x, np.sin(x), label="曲线")
        ax.axhline(0.0, color="gray", linestyle="--", label="参考线")
        ax.legend(loc="center")  # 恰压 y=0 参考线: ⚠️ 提示不阻断
        return fig

    def make_text_over_line():
        fig, ax = plt.subplots(figsize=(6, 4))
        x = np.linspace(0, 10, 200)
        ax.plot(x, 5 * x, label="趋势线")
        ax.text(4.2, 22, "关键转折", fontsize=12)  # 压在陡峭线段上
        ax.set_title("文字压线示例")
        return fig

    def make_legend_over_bar():
        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar([0, 1, 2, 3], [9, 9.5, 9.2, 9.4], width=0.6)
        for rect in bars:  # 柱内数值标签: 应被豁免, 不产生 text-over-patch
            ax.text(
                rect.get_x() + rect.get_width() / 2,
                rect.get_height() - 0.8,
                f"{rect.get_height():.1f}",
                ha="center",
                color="white",
            )
        ax.set_ylim(0, 10)
        ax.legend(["方案 A"], loc="upper center")  # 压在高柱上
        ax.set_title("图例压柱示例")
        return fig

    def make_rotated_labels_clean():
        """斜排假叠印: 30° 长类别名, 轴对齐包围盒相交 >2000px² 但字形零重叠。"""
        fig, ax = plt.subplots(figsize=(5.0, 3.0), layout="constrained")
        ax.imshow(np.zeros((3, 5)))
        ax.set_xticks(range(5), ["甲乙丙丁戊己庚辛"] * 5, rotation=30, ha="right")
        return fig

    def make_rotated_labels_collide():
        """斜排真叠印: 窄横轴 + 8 个 45° 短标签, 字形真的压在一起。"""
        fig, ax = plt.subplots(figsize=(1.6, 1.4), layout="constrained")
        ax.imshow(np.zeros((3, 8)))
        ax.set_xticks(range(8), ["甲乙丙丁戊"] * 8, rotation=45, ha="right")
        return fig

    ok = True
    for name, factory, expect_kind in (
        ("干净图", make_clean, None),
        ("文字压线图", make_text_over_line, KIND_LINE_THROUGH_TEXT),
        ("图例压柱图", make_legend_over_bar, KIND_LEGEND_OVER_PATCH),
        ("inset盖标注图", make_inset_cover_text, KIND_TEXT_OVER_INSET),
        ("图例压线图", make_legend_over_line, KIND_LEGEND_OVER_LINE),
        ("斜排假叠印图", make_rotated_labels_clean, None),
        ("斜排真叠印图", make_rotated_labels_collide, KIND_TICK_LABEL_OVERLAP),
    ):
        fig = factory()
        collisions = analyze_figure(fig, name)
        plt.close(fig)
        kinds = {c.kind for c in collisions}
        detail = "; ".join(f"{c.kind}: {c.detail}" for c in collisions) or "无"
        print(f"[自测] {name}: {detail}")
        if expect_kind is None:
            errors = [c for c in collisions if c.severity != SEV_WARN]
            if errors:
                print(f"  ❌ 干净图被误报 {len(errors)} 处")
                ok = False
            else:
                print(f"  ✅ 干净图 0 误报（⚠️ 提示 {len(collisions)} 处, 不阻断）")
        else:
            if expect_kind not in kinds:
                print(f"  ❌ 未检出期望的 {expect_kind}")
                ok = False
            else:
                print(f"  ✅ 检出 {expect_kind}")
            if KIND_TEXT_OVER_PATCH in kinds:
                print("  ❌ 柱内数值标签未被豁免, 出现 text-over-patch 误报")
                ok = False
    print("[自测] " + ("全部通过 ✅" if ok else "存在失败 ❌"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="图表渲染碰撞检测: 执行出图脚本并检查七类像素级排版碰撞"
    )
    parser.add_argument("target", nargs="?", help="figure.py 脚本或其所在目录")
    parser.add_argument("--strict", action="store_true", help="检出碰撞时退出码 1")
    parser.add_argument(
        "--allow-box-labels",
        action="store_true",
        help="豁免完全落在单个色块内的文本（流程图/示意图盒内标签）",
    )
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
    return check_path(target, args.strict, args.allow_box_labels)


if __name__ == "__main__":
    sys.exit(main())
