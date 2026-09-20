# -*- coding: utf-8 -*-
"""物理场图模板: pcolormesh 场 + 红虚线判据等值线 + 共享色标多面板。

证据分两层: 场分布（数据层）+ 判据等值线（判据层, 红虚线, 图例注明判据值）。
多面板 1×N 时每面板独立场但默认共享色标（share_scale=True, 色条只画一条,
面板间可直接比大小）; share_scale=False 时各面板自算色标范围并各自挂色条
（此时跨面板读数必须以各自色条为准）。

用法（二选一）:
    1. 独立运行:
       python make_field_contour.py [--demo] [--out 输出前缀]
       --demo 显式渲染内置示例（不给 --out 时示例图写入系统临时目录,
       gitignore 友好）, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 _demo_fields() 的 X/Y/FIELDS 与 plot_field_contour() 入参。

约定:
    - 3.0.0 新增（图叙事纪律: 场图必带判据层）。
    - 样式与色板统一经 scripts/figkit.py 加载; 连续场色取
      figkit.get_cmap("sequential"), 判据等值线取 academic_blue 第 4 色
      （红）虚线——判据线配色语义见 references/color_typology.md 配色语义表。
    - 注释预算: 本模板默认只保留判据线图例（图例不计入注释预算）。

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
import numpy as np

# ---- figkit 位于本脚本上二级 scripts/ 目录, 注册后方可 from figkit import ----
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    FIGSIZE,
    apply_style,
    get_cmap,
    load_neutral,
    load_palette,
    restore_style_on_error,
    save_fig,
)

# 判据线固定红虚线（配色语义表: 判据线=红虚线; 取 academic_blue 第 4 色）
CRITERION_COLOR = load_palette("academic_blue")[3]


def draw_field(ax, X, Y, field, *, cmap="viridis", vmin=None, vmax=None,
               norm=None, rasterized=True):
    """Draw on caller-owned axes without changing style, saving or closing."""
    x, y, values = np.asarray(X), np.asarray(Y), np.asarray(field, dtype=float)
    if values.ndim != 2 or x.shape != values.shape or y.shape != values.shape:
        raise ValueError("X/Y/field must be matching 2D arrays")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or np.isinf(values).any():
        raise ValueError("coordinates must be finite; field may contain NaN but not infinity")
    if not np.isfinite(values).any():
        raise ValueError("field has no observed values")
    return ax.pcolormesh(x, y, np.ma.masked_invalid(values), cmap=cmap,
                         vmin=vmin, vmax=vmax, norm=norm,
                         shading="auto", rasterized=rasterized)


def _demo_fields() -> tuple[np.ndarray, np.ndarray, list[np.ndarray], list[float]]:
    """构造示例场: 10cm×6cm 板面温度场, 三个时刻热斑扩展, 返回 (X, Y, 场列表, 时刻列表)。"""
    x = np.linspace(0.0, 10.0, 61)
    y = np.linspace(0.0, 6.0, 37)
    X, Y = np.meshgrid(x, y)
    fields = []
    for t in (2.0, 4.0, 6.0):
        spread = 1.2 + 0.35 * t
        fields.append(
            24.0 + 52.0 * np.exp(-((X - 3.5 - 0.4 * t) ** 2 + (Y - 3.0) ** 2)
                                 / (2 * spread ** 2))
        )
    return X, Y, fields, [2.0, 4.0, 6.0]


@restore_style_on_error
def plot_field_contour(
    X: np.ndarray,
    Y: np.ndarray,
    fields: list[np.ndarray],
    panel_titles: list[str] | None = None,
    criterion: float | None = None,
    criterion_label: str = "判据等值线",
    value_label: str = "温度 (°C)",
    share_scale: bool = True,
    cmap_kind: str = "sequential",
    out_stem: str | None = None,
    *,
    xlabel: str = "x (cm)",
    ylabel: str = "y (cm)",
    legend_loc: str = "upper left",
) -> tuple[Path, Path]:
    """绘制物理场图（多面板共享色标 + 判据等值线）, 保存 PNG+SVG+PDF, 返回前两个路径。

    Args:
        X/Y: 二维网格坐标（np.meshgrid 输出, 形状一致）。
        fields: 场列表（每个 shape 同 X）; 长度即面板数, 建议 1-4。
        panel_titles: 各面板短标题（轴含义级, ≤6 中文字符当量）; None 时自动编号。
        criterion: 判据值; 画出该等值线（红虚线, 图例注明）; None 时不画判据层。
        criterion_label: 判据线图例文案。
        value_label: 色条轴名。
        share_scale: True 时全面板共享 vmin/vmax（跨面板可比）; False 各自定标。
        cmap_kind: figkit.get_cmap 语义类型（sequential/diverging）。
        out_stem: 输出文件前缀; None 时写系统临时目录。
        xlabel/ylabel: 坐标轴名（仅限关键字; 3.0.1 参数化, 默认保持
            "x (cm)"/"y (cm)"; 如"半径-时间"平面场传 "时间 t (s)"/
            "径向距离 r (mm)"）。
        legend_loc: 判据线图例位置（仅限关键字; 3.0.1 参数化, 默认
            "upper left"; 高值区在左上时改 "lower left"/"upper right" 防压场;
            判据线不带图例时忽略）。

    Raises:
        ValueError: 网格/场形状不一致、场含非有限值、criterion 越出全部场范围、
            标题数与面板数不齐等。
    """
    if X.ndim != 2 or X.shape != Y.shape:
        raise ValueError(f"X/Y 须为同形二维网格, 实际 X{X.shape} Y{Y.shape}")
    if not fields:
        raise ValueError("fields 不能为空: 至少提供一个场")
    for i, f in enumerate(fields):
        if f.shape != X.shape:
            raise ValueError(f"fields[{i}] 形状 {f.shape} 与网格 {X.shape} 不一致")
        if not np.all(np.isfinite(f)):
            raise ValueError(f"fields[{i}] 含非有限数值(NaN/inf)")
    if panel_titles is None:
        panel_titles = [f"场 {i + 1}" for i in range(len(fields))]
    if len(panel_titles) != len(fields):
        raise ValueError(f"panel_titles 数 {len(panel_titles)} 与面板数 {len(fields)} 不齐")

    lo = min(float(np.min(f)) for f in fields)
    hi = max(float(np.max(f)) for f in fields)
    if criterion is not None:
        if not math.isfinite(criterion):
            raise ValueError(f"criterion 须为有限数值, 实际 {criterion!r}")
        if not any(lo <= criterion <= float(np.max(f)) for f in fields):
            raise ValueError(
                f"判据值 {criterion} 越出全部场的取值范围 [{lo:.3g}, {hi:.3g}], "
                "等值线画不出来; 请核对判据或改用无判据层模式")

    apply_style()
    n = len(fields)
    fig, axes = plt.subplots(
        1, n, figsize=(FIGSIZE["wide"][0], FIGSIZE["wide"][1] * 0.78),
        sharey=True, layout="constrained")
    axes = np.atleast_1d(axes)
    cmap = matplotlib.colormaps[get_cmap(cmap_kind)]
    vmin, vmax = (lo, hi) if share_scale else (None, None)

    legend_proxy = None
    im = None
    for ax, f, title in zip(axes, fields, panel_titles):
        if not share_scale:
            vmin, vmax = float(np.min(f)), float(np.max(f))
        im = draw_field(ax, X, Y, f, cmap=cmap, vmin=vmin, vmax=vmax)
        if criterion is not None:
            cs = ax.contour(X, Y, f, levels=[criterion],
                            colors=[CRITERION_COLOR], linestyles="--",
                            linewidths=1.6)
            if legend_proxy is None:
                legend_proxy = cs
        ax.set_title(title)
        ax.grid(False)
        ax.set_xlabel(xlabel)
    axes[0].set_ylabel(ylabel)

    if criterion is not None and legend_proxy is not None:
        # 判据线图例: 用 Line2D 代理（QuadContourSet 的图例接口随 mpl 版本漂移）
        from matplotlib.lines import Line2D

        axes[0].legend(
            [Line2D([0], [0], color=CRITERION_COLOR, linestyle="--",
                    linewidth=1.6)],
            [f"{criterion_label} = {criterion:g}"],
            loc=legend_loc, frameon=True)
    if share_scale or len(axes) == 1:
        # 共享色标（或单面板）: 一条 colorbar 代表全部面板
        cbar = fig.colorbar(im, ax=list(axes), shrink=0.9, pad=0.02)
        cbar.set_label(value_label)
    else:
        # 非共享色标多面板: 每面板独立定标, 必须各自挂 colorbar,
        # 否则前 N-1 个面板被末面板色条静默误读 (复审 P1-1)
        for ax, f in zip(axes, fields):
            cbar = fig.colorbar(
                matplotlib.cm.ScalarMappable(
                    norm=matplotlib.colors.Normalize(
                        vmin=float(np.min(f)), vmax=float(np.max(f))),
                    cmap=cmap),
                ax=ax, shrink=0.9, pad=0.02)
            cbar.set_label(value_label)
    return _save(fig, out_stem, "make_field_contour")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成物理场图（示例数据）")
    parser.add_argument("--demo", action="store_true",
                        help="渲染内置示例数据（默认行为, 显式确认用）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    X, Y, fields, times = _demo_fields()
    try:
        png, svg = plot_field_contour(
            X, Y, fields,
            panel_titles=[f"t = {t:g} h" for t in times],
            criterion=48.0,
            criterion_label="判据 48 °C",
            value_label="温度 (°C)",
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
