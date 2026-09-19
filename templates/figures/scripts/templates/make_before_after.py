# -*- coding: utf-8 -*-
"""前后对照双联模板: 同坐标散点（t-SNE 式嵌入）或分布（直方）两模式。

存在前后对照（优化前/后、处理前/后、两阶段嵌入）时默认用本模板,
不画两张独立图（图叙事纪律: 对照式构图优先）。两面板强制同坐标同尺度
（sharex/sharey）, 散点模式前=灰、后=红（可配）; 分布模式每面板以己方
填充 + 对方虚线轮廓同坐标叠加（对照层）, 面板标题"前/后"可配。

用法（二选一）:
    1. 独立运行:
       python make_before_after.py [--demo] [--mode scatter|dist]
                                   [--before-label 优化前] [--after-label 优化后]
                                   [--out 输出前缀]
       --demo 显式渲染内置示例（不给 --out 时示例图写入系统临时目录）,
       产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 _demo_scatter()/_demo_dist() 与 plot_before_after() 入参。

约定:
    - 3.0.0 新增。样式与色板统一经 scripts/figkit.py 加载; 前态取中性灰
      （faint 令牌, 弱化）, 后态取 academic_blue 第 4 色（红, 强调改变结果）。

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
    load_neutral,
    load_palette,
    restore_style_on_error,
    save_fig,
)

BEFORE_COLOR = load_neutral("faint")                 # 前态 = 中性灰
AFTER_COLOR = load_palette("academic_blue")[3]       # 后态 = 红


def _demo_scatter() -> tuple[np.ndarray, np.ndarray]:
    """构造示例: 300 个样本两簇, 前态重叠混杂 → 后态分离, 返回 (前 Nx2, 后 Nx2)。"""
    rng = np.random.default_rng(7)
    n_half = 150
    labels = np.concatenate([np.zeros(n_half), np.ones(n_half)])
    angles = rng.uniform(0, 2 * np.pi, 300)
    radii = rng.normal(0.0, 1.0, 300)
    before = np.column_stack([
        0.6 * labels + 1.1 * radii * np.cos(angles) * 0.9,
        0.4 * labels + 0.8 * radii * np.sin(angles),
    ])
    after = np.column_stack([
        np.where(labels == 0, -1.6, 2.2) + 0.55 * radii * np.cos(angles),
        np.where(labels == 0, -0.9, 1.3) + 0.55 * radii * np.sin(angles),
    ])
    return before, after


def _demo_dist() -> tuple[np.ndarray, np.ndarray]:
    """构造示例: 同批样本的健康得分, 优化前 N(0.52, 0.12) → 优化后 N(0.68, 0.09)。"""
    rng = np.random.default_rng(11)
    before = rng.normal(0.52, 0.12, 400)
    after = 0.52 + (rng.normal(0.0, 0.09, 400) + 0.16)
    return before, after


@restore_style_on_error
def plot_before_after(
    before: np.ndarray,
    after: np.ndarray,
    mode: str = "scatter",
    before_label: str = "前",
    after_label: str = "后",
    axis_labels: tuple[str, str] | None = None,
    out_stem: str | None = None,
) -> tuple[Path, Path]:
    """绘制前后对照双联图, 保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        before/after: 前后两态数据。scatter 模式为 Nx2 坐标（嵌入）;
            dist 模式为一维得分序列。两者形状须一致且非空。
        mode: "scatter"（t-SNE 式嵌入散点）或 "dist"（直方分布叠加）。
        before_label/after_label: 面板标题（轴含义级, ≤6 中文字符当量）。
        axis_labels: (x 轴名, y 轴名); None 时 scatter 用 ("维度 1", "维度 2"),
            dist 用 ("得分", "占比")。
        out_stem: 输出文件前缀; None 时写系统临时目录。

    Raises:
        ValueError: mode 非法、数据形状不符模式要求、含非有限值或空数据。
    """
    b = np.asarray(before, dtype=float)
    a = np.asarray(after, dtype=float)
    if mode == "scatter":
        if b.ndim != 2 or b.shape[1] != 2 or a.shape != b.shape:
            raise ValueError(
                f"scatter 模式 before/after 须为同形 Nx2 坐标, 实际 "
                f"{b.shape} vs {a.shape}")
    elif mode == "dist":
        if b.ndim != 1 or a.ndim != 1 or len(b) == 0 or len(a) == 0:
            raise ValueError(
                f"dist 模式 before/after 须为非空一维序列, 实际 "
                f"{b.shape} vs {a.shape}")
    else:
        raise ValueError(f"mode 需为 scatter/dist, 实际 {mode!r}")
    if not (np.all(np.isfinite(b)) and np.all(np.isfinite(a))):
        raise ValueError("before/after 含非有限数值(NaN/inf)")
    if axis_labels is None:
        axis_labels = (("维度 1", "维度 2") if mode == "scatter"
                       else ("得分", "占比"))

    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(FIGSIZE["wide"][0],
                                            FIGSIZE["wide"][1] * 0.58),
                             layout="constrained", sharex=True, sharey=True)
    if mode == "scatter":
        for ax, data, color in ((axes[0], b, BEFORE_COLOR),
                                (axes[1], a, AFTER_COLOR)):
            ax.scatter(data[:, 0], data[:, 1], s=10, color=color, alpha=0.75,
                       linewidths=0.3, edgecolors="white")
            ax.set_ylabel(axis_labels[1])
        axes[0].set_xlabel(axis_labels[0])
        axes[1].set_xlabel(axis_labels[0])
    else:
        all_vals = np.concatenate([b, a])
        bins = np.linspace(all_vals.min(), all_vals.max(), 24)
        for ax, own, other, color in (
                (axes[0], b, a, BEFORE_COLOR), (axes[1], a, b, AFTER_COLOR)):
            ax.hist(other, bins=bins, density=True, histtype="step",
                    linestyle="--", color=(AFTER_COLOR if ax is axes[0]
                                           else BEFORE_COLOR),
                    linewidth=1.3)
            ax.hist(own, bins=bins, density=True, color=color, alpha=0.72)
            ax.set_ylabel(axis_labels[1])
        axes[0].set_xlabel(axis_labels[0])
        axes[1].set_xlabel(axis_labels[0])
        # 分布模式图例放画布顶（constrained layout 自动留位）: 灰=前、红=后,
        # 面板内己方填充 + 对方虚线轮廓, 色即编码
        from matplotlib.lines import Line2D
        from matplotlib.patches import Patch

        fig.legend(
            handles=[Patch(facecolor=BEFORE_COLOR, alpha=0.72,
                           label=before_label),
                     Line2D([0], [0], color=AFTER_COLOR, linestyle="--",
                            linewidth=1.3, label=after_label)],
            loc="outside upper center", ncol=2, frameon=False)
    axes[0].set_title(before_label)
    axes[1].set_title(after_label)
    return _save(fig, out_stem, "make_before_after")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成前后对照双联图（示例数据）")
    parser.add_argument("--demo", action="store_true",
                        help="渲染内置示例数据（默认行为, 显式确认用）")
    parser.add_argument("--mode", default="scatter",
                        choices=("scatter", "dist"),
                        help="模式: scatter(t-SNE 式嵌入散点, 默认)/dist(直方分布)")
    parser.add_argument("--before-label", default="前",
                        help="前面板标题（默认: 前）")
    parser.add_argument("--after-label", default="后",
                        help="后面板标题（默认: 后）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    if args.mode == "scatter":
        before, after = _demo_scatter()
    else:
        before, after = _demo_dist()
    try:
        png, svg = plot_before_after(
            before, after, mode=args.mode,
            before_label=args.before_label,
            after_label=args.after_label,
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
