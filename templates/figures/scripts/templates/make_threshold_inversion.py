# -*- coding: utf-8 -*-
"""阈值穿越反演图模板: 主曲线 + 阈值红虚线 + 穿越点标记 + inset 放大双边锁定。

反演读法: 指标随参数单调变化, 与判据阈值的交点即"临界参数"。本模板自动
插值定位首次穿越点并放大其邻域（inset）, 锁定穿越前后相邻两档数据点
（双边锁定: 穿越点必落在两档之间, 反演结论可核验）。

证据分三层: 主曲线（数据层）+ 阈值红虚线（判据层, 图例注明阈值）+
穿越点与其邻域放大（对照层）。注释预算内置: 全图只标穿越点一处, 阈值走图例。

用法（二选一）:
    1. 独立运行:
       python make_threshold_inversion.py [--demo] [--out 输出前缀]
       --demo 显式渲染内置示例（不给 --out 时示例图写入系统临时目录）,
       产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 _demo_curve() 与 plot_threshold_inversion() 入参。

约定:
    - 3.0.0 新增（图叙事纪律: 答案图须"可核验"——标数值+判据线+对照三选二）。
    - 阈值线取 academic_blue 第 4 色（红）虚线; 穿越点用主色实心标记。

退出码: 0 成功; 2 参数/IO 错误。
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import tempfile
from pathlib import Path

# 画布与输出的字体缓存指向系统临时目录, 避免在 skill/项目目录落垃圾文件
os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "mathmodel-mplconfig")
)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox
import numpy as np

# ---- figkit 位于本脚本上二级 scripts/ 目录, 注册后方可 from figkit import ----
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    FIGSIZE,
    apply_style,
    load_neutral,
    load_palette,
    restore_style_on_error,
    save_fig,
)

MAIN_COLOR = load_palette("academic_blue")[0]     # 主曲线/穿越点 = 主色
CRITERION_COLOR = load_palette("academic_blue")[3]   # 阈值线 = 红虚线


def _demo_curve() -> tuple[np.ndarray, np.ndarray]:
    """构造示例: 干燥强度指标 S 随参数 λ 单调上升, 返回 (λ, S)。"""
    lam = np.linspace(0.0, 1.0, 101)
    metric = 1.0 / (1.0 + np.exp(-12.0 * (lam - 0.42)))
    return lam, metric


def _first_crossing(param: np.ndarray, metric: np.ndarray,
                    threshold: float) -> tuple[int, float]:
    """定位首次穿越: 返回 (穿越前末档下标 i, 插值穿越参数)。

    metric[i] 与 metric[i+1] 严格夹住 threshold（双边锁定用）;
    上升/下降穿越均支持, 取序列中最先发生者。
    """
    for i in range(len(metric) - 1):
        lo, hi = metric[i], metric[i + 1]
        if lo == threshold:   # 档点恰好压在阈值上: 该档即穿越点
            return i, float(param[i])
        if (lo - threshold) * (hi - threshold) < 0:
            frac = (threshold - lo) / (hi - lo)
            return i, float(param[i] + frac * (param[i + 1] - param[i]))
    if metric[-1] == threshold:  # 末档点恰压阈值 (复审 P2-3): 末档即穿越点
        return len(metric) - 2, float(param[-1])
    raise ValueError(
        f"指标序列未穿越阈值 {threshold}: 序列范围 [{metric.min():.4g}, "
        f"{metric.max():.4g}], 请核对判据值或换用场图模板")


@restore_style_on_error
def plot_threshold_inversion(
    param: np.ndarray,
    metric: np.ndarray,
    threshold: float,
    param_label: str = "参数 λ",
    metric_label: str = "指标 S",
    threshold_label: str = "判据阈值",
    digits: int = 3,
    out_stem: str | None = None,
    *,
    star_symbol: str = "λ*",
    star_value: float | None = None,
    legend_loc: str = "upper left",
) -> tuple[Path, Path]:
    """绘制阈值穿越反演图（主曲线+阈值+穿越点+inset 双边锁定）, 保存 PNG+SVG+PDF。

    Args:
        param/metric: 一维同长序列（参数与指标）; 须存在对 threshold 的穿越。
        threshold: 判据阈值（红虚线）。
        param_label/metric_label: 轴名。
        threshold_label: 阈值线图例文案。
        digits: 穿越点标注的小数位。
        out_stem: 输出文件前缀; None 时写系统临时目录。
        star_symbol: 穿越点符号名（仅限关键字; 默认 "λ*"）; 参数是时间时
            传 "t*" 等。
        star_value: 标注用的穿越值（仅限关键字）; None 时用插值穿越点。
            **论文里传冻结值**——插值穿越点与冻结值常差末位（本题 57.5403 vs
            冻结 57.5406 h），图内数字必须与结果登记表逐字一致（数字漂移防线）。
        legend_loc: 阈值线图例位置（仅限关键字; 3.0.1 参数化, 默认
            "upper left"; 曲线在左上时改 "lower left"/"upper right"）。

    Raises:
        ValueError: 序列为空/长度不齐/含非有限值/阈值非有限/未发生穿越。
    """
    x = np.asarray(param, dtype=float)
    y = np.asarray(metric, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y):
        raise ValueError(f"param/metric 须为同长一维序列, 实际 {x.shape} vs {y.shape}")
    if len(x) < 3:
        raise ValueError(f"序列长度须 ≥3 才能谈穿越邻域, 实际 {len(x)}")
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise ValueError("param/metric 含非有限数值(NaN/inf)")
    if not math.isfinite(threshold):
        raise ValueError(f"threshold 须为有限数值, 实际 {threshold!r}")
    if not 0 <= digits <= 6:
        raise ValueError(f"digits 需在 [0, 6], 实际 {digits}")
    if star_value is not None:
        if not math.isfinite(star_value):
            raise ValueError(f"star_value 须为有限数值, 实际 {star_value!r}")
        if not x.min() <= star_value <= x.max():
            raise ValueError(
                f"star_value {star_value} 越出参数范围 [{x.min():g}, {x.max():g}]")

    i0, x_star = _first_crossing(x, y, threshold)
    annot_star = float(star_value) if star_value is not None else x_star
    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE["onehalf"], layout="constrained")

    ax.plot(x, y, color=MAIN_COLOR, linewidth=1.8, label=metric_label)
    ax.axhline(threshold, color=CRITERION_COLOR, linestyle="--", linewidth=1.6,
               label=f"{threshold_label} = {threshold:g}")
    ax.plot([x_star], [threshold], marker="o", markersize=7, color=MAIN_COLOR,
            markeredgecolor="white", markeredgewidth=1.2, zorder=5)
    # 穿越点标注（全图唯一解释性注释, 指向穿越点; 阈值走图例不计注释预算）。
    # 不用 annotate+arrowprops: figqa 对 Annotation 取"文本+箭头"联合 bbox,
    # 箭头端点落在主曲线上会误报 line-through-text; 改为独立文本 + 细引导线。
    # 默认放穿越点左上方（曲线在该侧低于文本, 无碰撞）; 左侧会溢出 y 轴区时
    # 改放右下方（曲线已穿到上方, 下方无碰撞, 复审 P2-3）。
    span_x, span_y = float(x.max() - x.min()), float(y.max() - y.min())
    if x_star - 0.26 * span_x >= x.min():
        text_x, text_y = x_star - 0.26 * span_x, threshold + 0.26 * span_y
    else:
        text_x, text_y = x_star + 0.03 * span_x, threshold - 0.22 * span_y
    ax.text(text_x, text_y,
            f"首次穿越 {star_symbol} = {annot_star:.{digits}f}",
            fontsize=9.5, color=load_neutral("ink"), ha="left", va="bottom")
    ann = ax.texts[-1]
    ax.plot([x_star - 0.11 * span_x, x_star - 0.012 * span_x],
            [threshold + 0.21 * span_y, threshold + 0.016 * span_y],
            color=load_neutral("arrow"), linewidth=0.9, zorder=3,
            solid_capstyle="round")
    ax.set_xlabel(param_label)
    ax.set_ylabel(metric_label)
    ax.set_ylim(min(y.min(), threshold) - 0.06 * (y.max() - y.min()),
                y.max() + 0.10 * (y.max() - y.min()))
    ax.legend(loc=legend_loc, frameon=True)

    # ---- inset 放大: 穿越点邻域 + 双边锁定（相邻两档数据点夹住穿越） ----
    # 角落自适应（v3.0.0 修复）: inset 原先固定在右下角, 但标注文本的落点由参数
    # 跨度决定, 参数跨度大时文本右端会伸进右下角区域, 被 inset 整块盖住——A 题实测
    # 命中（当时 figqa 只查像素文本/色块/折线三类, 不查 axes 级遮挡; v3.1.0 已补
    # 第七类 artist-bbox 检查兜同类问题, 模板内的确定性避让仍保留——门禁是兜底,
    # 模板不该产出需要兜底的图）。
    # 做法: 四角中先排除与标注/图例包围盒相交的, 再选主曲线落在窗口内数据点最少的
    # 一角; 确定性计算, 无随机分支。
    span_x = 0.06 * (x.max() - x.min())
    span_y = 0.10 * (y.max() - y.min())
    inset_w, inset_h = 0.36, 0.34
    corners = [(0.60, 0.09), (0.60, 0.53), (0.04, 0.09), (0.04, 0.53)]
    axins = None
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        ann_bbox = ann.get_window_extent(renderer)
        leg = ax.get_legend()
        leg_bbox = leg.get_window_extent(renderer) if leg is not None else None
        ax_bbox = ax.get_window_extent(renderer)
        xlim, ylim = ax.get_xlim(), ax.get_ylim()

        def _corner_rect(x0: float, y0: float) -> Bbox:
            return Bbox.from_bounds(
                ax_bbox.x0 + x0 * ax_bbox.width,
                ax_bbox.y0 + y0 * ax_bbox.height,
                inset_w * ax_bbox.width, inset_h * ax_bbox.height)

        best, best_score = None, None
        for x0, y0 in corners:
            rect = _corner_rect(x0, y0)
            if rect.overlaps(ann_bbox):
                continue
            if leg_bbox is not None and rect.overlaps(leg_bbox):
                continue
            xa = xlim[0] + x0 * (xlim[1] - xlim[0])
            xb = xlim[0] + (x0 + inset_w) * (xlim[1] - xlim[0])
            ya = ylim[0] + y0 * (ylim[1] - ylim[0])
            yb = ylim[0] + (y0 + inset_h) * (ylim[1] - ylim[0])
            inside = int(np.count_nonzero(
                (x >= xa) & (x <= xb) & (y >= ya) & (y <= yb)))
            if best_score is None or inside < best_score:
                best, best_score = (x0, y0), inside
        if best is None:
            # 四角皆与标注或图例相交（极端版面）: 退回原始右下角, 并抬高标注避让
            best = (0.60, 0.09)
            ann.set_position((text_x, threshold + 0.55 * span_y))
        axins = ax.inset_axes([best[0], best[1], inset_w, inset_h])
    except Exception:  # 渲染器不可用（非 Agg 后端）时退回固定右下角
        axins = ax.inset_axes([0.60, 0.09, inset_w, inset_h])
    axins.plot(x, y, color=MAIN_COLOR, linewidth=1.6)
    axins.axhline(threshold, color=CRITERION_COLOR, linestyle="--", linewidth=1.4)
    axins.plot([x[i0], x[i0 + 1]], [y[i0], y[i0 + 1]], linestyle="none",
               marker="o", markersize=5, markerfacecolor="none",
               markeredgecolor=load_neutral("secondary"), zorder=5)
    axins.plot([x_star], [threshold], marker="o", markersize=6,
               color=MAIN_COLOR, markeredgecolor="white", markeredgewidth=1.0,
               zorder=6)
    axins.set_xlim(x_star - span_x, x_star + span_x)
    axins.set_ylim(threshold - span_y, threshold + span_y)
    axins.tick_params(labelsize=8)
    axins.set_facecolor("white")
    # 主图上标记 inset 对应的放大窗口（无填充矩形, 不与任何文本重叠）
    from matplotlib.patches import Rectangle

    ax.add_patch(Rectangle((x_star - span_x, threshold - span_y), 2 * span_x,
                           2 * span_y, fill=False,
                           edgecolor=load_neutral("edge_strong"), linewidth=1.0,
                           zorder=4))
    return _save(fig, out_stem, "make_threshold_inversion")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成阈值穿越反演图（示例数据）")
    parser.add_argument("--demo", action="store_true",
                        help="渲染内置示例数据（默认行为, 显式确认用）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    lam, metric = _demo_curve()
    try:
        png, svg = plot_threshold_inversion(
            lam, metric, 0.5,
            param_label="参数 λ",
            metric_label="指标 S",
            threshold_label="判据阈值",
            out_stem=args.out,
        )
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    print(f"已输出: {png}")
    print(f"已输出: {svg}")
    print(f"已输出: {png.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
