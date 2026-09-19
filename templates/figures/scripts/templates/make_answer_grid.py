# -*- coding: utf-8 -*-
"""结果交付网格模板: M×N 数值/概率热力网格, 格内自适应黑白数值 + 色条。

结果交付范式（16×4）: 行=样本/文件/方案, 列=类别/时刻/工况, 格=数值或
概率。评委回答"每个样本每个时刻的结论是什么"直接读格。色标支持连续
（viridis）与发散（RdBu_r 以决策线 0.5 居中, 蓝红即未达/达标两阵营）;
格内数值按背景亮度自适应黑/白字, 保证打印黑白仍可读。

用法（二选一）:
    1. 独立运行:
       python make_answer_grid.py [--demo] [--cmap sequential|diverging]
                                   [--out 输出前缀]
       --demo 显式渲染内置示例（不给 --out 时示例图写入系统临时目录）,
       产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 _demo_grid() 与 plot_answer_grid() 入参。

约定:
    - 3.0.0 新增（图叙事纪律: 结果交付范式 + 量化标签——格内即数值）。
    - 连续色取 figkit.get_cmap("sequential"), 发散色取
      figkit.get_cmap("diverging") 且以 center 居中对称。

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
    apply_style,
    get_cmap,
    restore_style_on_error,
    save_fig,
)


def _luminance(hex_color: str) -> float:
    """hex 色值的感知灰阶 (0~255): 0.299R+0.587G+0.114B, 用于选黑/白前景字。"""
    text = hex_color.strip().lstrip("#")
    r = int(text[0:2], 16)
    g = int(text[2:4], 16)
    b = int(text[4:6], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def _demo_grid() -> tuple[np.ndarray, list[str], list[str]]:
    """构造示例: 16 个样本 × 4 个时刻的达标概率（16×4 结果交付范式）。"""
    rng = np.random.default_rng(2026)
    rows = [f"样本 {i:02d}" for i in range(1, 17)]
    cols = ["t = 0 h", "t = 1 h", "t = 2 h", "t = 3 h"]
    base = rng.uniform(0.25, 0.72, size=(16, 4))
    drift = np.outer(np.linspace(-0.15, 0.25, 16), np.linspace(0.1, 0.4, 4))
    values = np.clip(base + drift, 0.02, 0.98)
    return values, rows, cols


@restore_style_on_error
def plot_answer_grid(
    values: np.ndarray,
    row_names: list[str] | None = None,
    col_names: list[str] | None = None,
    value_label: str = "达标概率",
    cmap_kind: str = "diverging",
    center: float | None = 0.5,
    digits: int = 2,
    annotate: bool = True,
    out_stem: str | None = None,
    *,
    xlabel: str | None = None,
    ylabel: str | None = None,
) -> tuple[Path, Path]:
    """绘制结果交付网格（M×N 热力网格 + 格内数值 + 色条）, 保存 PNG+SVG+PDF。

    Args:
        values: M×N 数值矩阵（概率/指标值）。
        row_names/col_names: 行列名; None 时自动编号（行=样本, 列=类别）。
        value_label: 色条轴名。
        cmap_kind: "diverging"（默认, 以 center 居中对称）或 "sequential"。
        center: 发散色对称中心（默认 0.5, 决策线）; cmap_kind="sequential"
            或 None 时忽略。
        digits: 格内数值小数位。
        annotate: 是否格内标数值（自适应黑/白字）。
        out_stem: 输出文件前缀; None 时写系统临时目录。
        xlabel/ylabel: 列/行轴名（仅限关键字; 3.0.1 参数化, 如 "距中心距离
            r (cm)"/"时间 t (h)"; None 时不画轴名——保持原版式）。

    Raises:
        ValueError: 矩阵为空/非二维/含非有限值、名称长度不齐、digits 越界、
            center 非有限或不在数据范围内。
    """
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 2 or arr.shape[0] == 0 or arr.shape[1] == 0:
        raise ValueError(f"values 必须是非空二维矩阵, 实际 shape: {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("values 含非有限数值(NaN/inf)")
    rows_n, cols_n = arr.shape
    if row_names is None:
        row_names = [f"样本 {i + 1:02d}" for i in range(rows_n)]
    if col_names is None:
        col_names = [f"类别 {j + 1}" for j in range(cols_n)]
    if len(row_names) != rows_n or len(col_names) != cols_n:
        raise ValueError(
            f"名称长度与矩阵不齐: 行名 {len(row_names)} vs {rows_n} 行, "
            f"列名 {len(col_names)} vs {cols_n} 列")
    if any(not str(n).strip() for n in list(row_names) + list(col_names)):
        raise ValueError("row_names/col_names 含空名称")
    if not 0 <= digits <= 4:
        raise ValueError(f"digits 需在 [0, 4], 实际 {digits}")
    if cmap_kind not in ("diverging", "sequential"):
        raise ValueError(f"cmap_kind 需为 diverging/sequential, 实际 {cmap_kind!r}")

    vmin, vmax = float(arr.min()), float(arr.max())
    if cmap_kind == "diverging":
        if center is None:
            center = 0.5
        if not math.isfinite(center) or not vmin <= center <= vmax:
            raise ValueError(
                f"center 须为有限值且在数据范围 [{vmin:.3g}, {vmax:.3g}] 内, "
                f"实际 {center!r}")
        half = max(abs(vmax - center), abs(center - vmin)) or 1.0
        vmin, vmax = center - half, center + half

    apply_style()
    fig_w = max(4.6, 1.4 + 0.95 * cols_n)
    fig_h = max(3.4, 0.9 + 0.42 * rows_n)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), layout="constrained")
    im = ax.imshow(arr, cmap=get_cmap(cmap_kind), vmin=vmin, vmax=vmax,
                   aspect="auto", interpolation="nearest")
    ax.grid(False)
    # 白色细网格线画格（imshow 网格语义, 同相关性热力图模板）
    ax.set_xticks(np.arange(cols_n) + 0.5, minor=True)
    ax.set_yticks(np.arange(rows_n) + 0.5, minor=True)
    ax.grid(True, which="minor", color="white", linewidth=1.2)
    ax.tick_params(which="minor", length=0)

    if annotate:
        cell_fs = 8.5 if rows_n * cols_n <= 96 else 7.0
        for i in range(rows_n):
            for j in range(cols_n):
                bg = im.cmap(im.norm(arr[i, j]))
                fg = ("white"
                      if _luminance(matplotlib.colors.to_hex(bg)) < 150
                      else "black")
                ax.text(j, i, f"{arr[i, j]:.{digits}f}", ha="center",
                        va="center", color=fg, fontsize=cell_fs)

    ax.set_xticks(range(cols_n))
    ax.set_xticklabels(col_names)
    ax.set_yticks(range(rows_n))
    ax.set_yticklabels(row_names, fontsize=8)
    ax.tick_params(top=False, bottom=True, left=True, right=False)
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    cbar = fig.colorbar(im, ax=ax, fraction=0.030, pad=0.035)
    cbar.set_label(value_label)
    cbar.ax.tick_params(labelsize=9)
    return _save(fig, out_stem, "make_answer_grid")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成结果交付网格（示例数据）")
    parser.add_argument("--demo", action="store_true",
                        help="渲染内置示例数据（默认行为, 显式确认用）")
    parser.add_argument("--cmap", default="diverging",
                        choices=("diverging", "sequential"),
                        help="色标类型: diverging(默认, 0.5 居中)/sequential")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    values, rows, cols = _demo_grid()
    try:
        png, svg = plot_answer_grid(
            values, rows, cols,
            value_label="达标概率",
            cmap_kind=args.cmap,
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
