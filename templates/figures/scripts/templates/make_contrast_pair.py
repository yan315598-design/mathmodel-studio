# -*- coding: utf-8 -*-
"""对照双联模板: 同坐标同尺度左右两面板, 共享色标, 差异区红虚线判据圈出。

存在对照关系（前后/两法/两档网格）时默认用本模板, 不画两张独立图
（图叙事纪律: 对照式构图优先）。两面板共享 vmin/vmax 与坐标范围,
色差即方法差; 右面板叠加差异判据等值线（|A−B| > 阈值的区域, 红虚线,
图例注明阈值）, 差异区一眼锁定。

用法（二选一）:
    1. 独立运行:
       python make_contrast_pair.py [--demo] [--out 输出前缀]
       --demo 显式渲染内置示例（不给 --out 时示例图写入系统临时目录）,
       产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 _demo_fields() 与 plot_contrast_pair() 入参。

约定:
    - 3.0.0 新增（图叙事纪律: 对照式构图优先; 差异层=判据层）。
    - 连续场色取 figkit.get_cmap("sequential"); 差异判据线取
      academic_blue 第 4 色（红）虚线。

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
    load_palette,
    restore_style_on_error,
    save_fig,
)

CRITERION_COLOR = load_palette("academic_blue")[3]   # 差异判据线 = 红虚线


def _demo_fields() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """构造示例: 同一温度场的两法解（基准 vs 改进, 热斑位置/强度略不同）。"""
    x = np.linspace(0.0, 10.0, 71)
    y = np.linspace(0.0, 6.0, 43)
    X, Y = np.meshgrid(x, y)
    base = 24.0 + 46.0 * np.exp(-((X - 4.2) ** 2 + (Y - 3.0) ** 2) / 8.0)
    improved = 24.0 + 52.0 * np.exp(-((X - 4.8) ** 2 + (Y - 2.8) ** 2) / 6.5)
    return X, Y, base, improved


@restore_style_on_error
def plot_contrast_pair(
    X: np.ndarray,
    Y: np.ndarray,
    field_a: np.ndarray,
    field_b: np.ndarray,
    title_a: str = "基准",
    title_b: str = "改进",
    diff_threshold: float | None = None,
    value_label: str = "温度 (°C)",
    cmap_kind: str = "sequential",
    out_stem: str | None = None,
    *,
    xlabel: str = "x (cm)",
    ylabel: str = "y (cm)",
    legend_loc: str = "upper right",
) -> tuple[Path, Path]:
    """绘制对照双联场图（同尺度 + 共享色标 + 差异判据圈出）, 保存 PNG+SVG+PDF。

    Args:
        X/Y: 二维网格坐标（np.meshgrid 输出, 两场共用）。
        field_a/field_b: 对照两场, shape 与 X 一致（A=基准/前, B=改进/后）。
        title_a/title_b: 面板短标题（轴含义级, ≤6 中文字符当量）。
        diff_threshold: 差异判据阈值; 右面板圈出 |A−B|>阈值的等值线（红虚线）;
            None 时不画差异层。
        value_label: 色条轴名。
        cmap_kind: figkit.get_cmap 语义类型。
        out_stem: 输出文件前缀; None 时写系统临时目录。
        xlabel/ylabel: 坐标轴名（仅限关键字; 3.0.1 参数化, 默认保持
            "x (cm)"/"y (cm)"）。
        legend_loc: 差异判据图例位置（仅限关键字; 3.0.1 参数化, 默认
            "upper right"; 差异区在右上时改 "upper left"/"lower right"）。

    Raises:
        ValueError: 网格/场形状不一致、场含非有限值、diff_threshold 非正
            或越出差异范围。
    """
    for name, f in (("field_a", field_a), ("field_b", field_b)):
        arr = np.asarray(f, dtype=float)
        if arr.shape != X.shape or Y.shape != X.shape:
            raise ValueError(f"{name}/X/Y 须同形, 实际 {arr.shape} / {X.shape} / {Y.shape}")
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} 含非有限数值(NaN/inf)")
    if diff_threshold is not None:
        diff = np.abs(np.asarray(field_a, dtype=float)
                      - np.asarray(field_b, dtype=float))
        if not (math.isfinite(diff_threshold) and diff_threshold > 0):
            raise ValueError(f"diff_threshold 须为正有限值, 实际 {diff_threshold!r}")
        if diff_threshold >= float(diff.max()):
            raise ValueError(
                f"差异阈值 {diff_threshold} 越出差异范围 [0, {diff.max():.3g}], "
                "判据等值线画不出来; 请核对阈值")

    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(FIGSIZE["wide"][0],
                                            FIGSIZE["wide"][1] * 0.62),
                             layout="constrained", sharey=True)
    a, b = np.asarray(field_a, dtype=float), np.asarray(field_b, dtype=float)
    vmin = float(min(a.min(), b.min()))
    vmax = float(max(a.max(), b.max()))
    cmap = matplotlib.colormaps[get_cmap(cmap_kind)]
    im0 = axes[0].pcolormesh(X, Y, a, cmap=cmap, vmin=vmin, vmax=vmax,
                             shading="auto", rasterized=True)
    axes[0].set_title(title_a)
    im1 = axes[1].pcolormesh(X, Y, b, cmap=cmap, vmin=vmin, vmax=vmax,
                             shading="auto", rasterized=True)
    axes[1].set_title(title_b)
    for ax in axes:
        ax.grid(False)
        ax.set_xlabel(xlabel)
        ax.set_xlim(float(X.min()), float(X.max()))
        ax.set_ylim(float(Y.min()), float(Y.max()))
    axes[0].set_ylabel(ylabel)

    if diff_threshold is not None:
        from matplotlib.lines import Line2D

        axes[1].contour(X, Y, np.abs(a - b), levels=[diff_threshold],
                        colors=[CRITERION_COLOR], linestyles="--", linewidths=1.6)
        axes[1].legend(
            [Line2D([0], [0], color=CRITERION_COLOR, linestyle="--",
                    linewidth=1.6)],
            [f"|Δ| > {diff_threshold:g}"],
            loc=legend_loc, frameon=True)
    cbar = fig.colorbar(im1, ax=list(axes), shrink=0.9, pad=0.02)
    cbar.set_label(value_label)
    return _save(fig, out_stem, "make_contrast_pair")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成对照双联场图（示例数据）")
    parser.add_argument("--demo", action="store_true",
                        help="渲染内置示例数据（默认行为, 显式确认用）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    X, Y, base, improved = _demo_fields()
    try:
        png, svg = plot_contrast_pair(
            X, Y, base, improved,
            title_a="基准解",
            title_b="改进解",
            diff_threshold=3.0,
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
