# -*- coding: utf-8 -*-
"""路径叠加场图模板: 底图场 + 路径折线 + 起终点标记（星/叉）+ 途经点。

航线/游线/迭代轨迹通用: 底图场（等值线/热力, 数据层）+ 最优路径
（主色白描边折线, 对照层）+ 起点星/终点叉/途经点（量化标记层）。
路径绕开底图高代价区一眼可核验（图叙事纪律: 答案图可核验）。

用法（二选一）:
    1. 独立运行:
       python make_route_on_field.py [--demo] [--out 输出前缀]
       --demo 显式渲染内置示例（不给 --out 时示例图写入系统临时目录）,
       产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 _demo_route() 与 plot_route_on_field() 入参。

约定:
    - 3.0.0 新增。样式与色板统一经 scripts/figkit.py 加载; 底图场色取
      figkit.get_cmap("sequential"), 路径取 academic_blue 主色 + 白描边
      （深浅底都可见）, 起点星取第 3 色、终点叉取第 4 色（红）。

退出码: 0 成功; 2 参数/IO 错误。
"""

from __future__ import annotations

import argparse
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
import numpy as np

# ---- figkit 位于本脚本上二级 scripts/ 目录, 注册后方可 from figkit import ----
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    FIGSIZE,
    apply_style,
    get_cmap,
    load_palette,
    restore_style_on_error,
    save_fig,
)

_COLORS = load_palette("academic_blue")
ROUTE_COLOR = _COLORS[0]      # 路径 = 主色
START_COLOR = _COLORS[2]      # 起点星 = 亮橙
END_COLOR = _COLORS[3]        # 终点叉 = 红


def _demo_route() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """构造示例: 代价场（中央高代价团）+ 绕行路径, 返回 (X, Y, 场, 路径 Nx2)。"""
    x = np.linspace(0.0, 10.0, 101)
    y = np.linspace(0.0, 6.0, 61)
    X, Y = np.meshgrid(x, y)
    cost = 1.0 + 3.2 * np.exp(-((X - 5.0) ** 2 + (Y - 3.4) ** 2) / 5.0)
    route = np.array([
        [0.5, 1.0], [2.5, 0.9], [4.4, 1.1], [6.4, 1.9],
        [8.0, 3.2], [9.5, 5.0],
    ])
    return X, Y, cost, route


@restore_style_on_error
def plot_route_on_field(
    X: np.ndarray,
    Y: np.ndarray,
    field: np.ndarray,
    route: np.ndarray,
    route_label: str = "最优路径",
    value_label: str = "通行代价",
    coord_label: str = "(km)",
    out_stem: str | None = None,
    *,
    xlabel: str | None = None,
    ylabel: str | None = None,
    start_label: str = "起点",
    end_label: str = "终点",
    legend_loc: str = "upper left",
) -> tuple[Path, Path]:
    """绘制路径叠加场图, 保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        X/Y: 二维网格坐标（np.meshgrid 输出）。
        field: 底图场, shape 与 X 一致。
        route: 路径顶点 Nx2 数组（列 = x, y）, 首点画星、末点画叉、
            中间点画途经小圆。
        route_label: 路径图例文案。
        value_label: 色条轴名。
        coord_label: 坐标单位后缀（轴名拼 "x "+coord_label）。
        out_stem: 输出文件前缀; None 时写系统临时目录。
        xlabel/ylabel: 坐标轴全名（仅限关键字; 3.0.1 参数化; None 时保持原
            拼接行为 f"x {coord_label}" / f"y {coord_label}"——坐标非物理长度时
            显式传轴名, 如 "经度"/"时间 t (s)"）。
        start_label/end_label: 起/终点图例文案（仅限关键字; 3.0.1 参数化,
            默认 "起点"/"终点"）。
        legend_loc: 图例位置（仅限关键字; 3.0.1 参数化, 默认 "upper left";
            路径起点在左上时改 "lower left"/"upper right" 防压路径）。

    Raises:
        ValueError: 网格/场形状不一致、场含非有限值、route 非 Nx2 或少于
            2 点、路径顶点越出网格范围。
    """
    arr = np.asarray(field, dtype=float)
    if X.ndim != 2 or X.shape != Y.shape or arr.shape != X.shape:
        raise ValueError(f"X/Y/field 须同形二维, 实际 {X.shape}/{Y.shape}/{arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("field 含非有限数值(NaN/inf)")
    pts = np.asarray(route, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 2:
        raise ValueError(f"route 须为 Nx2 路径顶点（≥2 点）, 实际 shape {pts.shape}")
    if not np.all(np.isfinite(pts)):
        raise ValueError("route 含非有限数值(NaN/inf)")
    if (pts[:, 0].min() < X.min() or pts[:, 0].max() > X.max()
            or pts[:, 1].min() < Y.min() or pts[:, 1].max() > Y.max()):
        raise ValueError("route 顶点越出底图网格范围, 路径须画在场内")

    apply_style()
    from matplotlib import patheffects
    from matplotlib.lines import Line2D

    fig, ax = plt.subplots(figsize=(FIGSIZE["onehalf"][0] * 1.22,
                                    FIGSIZE["onehalf"][1]),
                           layout="constrained")
    im = ax.pcolormesh(X, Y, arr, cmap=get_cmap("sequential"),
                       shading="auto", rasterized=True)
    ax.grid(False)

    # 路径: 主色 + 白描边（浅深底均可见）; 途经点小白心圆
    ax.plot(pts[:, 0], pts[:, 1], color=ROUTE_COLOR, linewidth=2.2,
            path_effects=[patheffects.withStroke(linewidth=4.0,
                                                 foreground="white")],
            zorder=5, solid_capstyle="round")
    ax.plot(pts[1:-1, 0], pts[1:-1, 1], linestyle="none", marker="o",
            markersize=4.5, markerfacecolor="white",
            markeredgecolor=ROUTE_COLOR, markeredgewidth=1.2, zorder=6)
    ax.plot([pts[0, 0]], [pts[0, 1]], linestyle="none", marker="*",
            markersize=15, markerfacecolor=START_COLOR,
            markeredgecolor="white", markeredgewidth=0.8, zorder=7)
    ax.plot([pts[-1, 0]], [pts[-1, 1]], linestyle="none", marker="X",
            markersize=11, markerfacecolor=END_COLOR,
            markeredgecolor="white", markeredgewidth=0.8, zorder=7)

    ax.legend(
        [Line2D([0], [0], color=ROUTE_COLOR, linewidth=2.2),
         Line2D([0], [0], linestyle="none", marker="*", markersize=13,
                markerfacecolor=START_COLOR, markeredgecolor="white"),
         Line2D([0], [0], linestyle="none", marker="X", markersize=10,
                markerfacecolor=END_COLOR, markeredgecolor="white")],
        [route_label, start_label, end_label],
        loc=legend_loc, frameon=True, framealpha=0.95)
    ax.set_xlabel(xlabel if xlabel is not None else f"x {coord_label}")
    ax.set_ylabel(ylabel if ylabel is not None else f"y {coord_label}")
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    cbar.set_label(value_label)
    return _save(fig, out_stem, "make_route_on_field")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成路径叠加场图（示例数据）")
    parser.add_argument("--demo", action="store_true",
                        help="渲染内置示例数据（默认行为, 显式确认用）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    X, Y, cost, route = _demo_route()
    try:
        png, svg = plot_route_on_field(
            X, Y, cost, route,
            route_label="最优路径",
            value_label="通行代价",
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
