# -*- coding: utf-8 -*-
"""双目标帕累托前沿图模板: 可行解散点云 + 非支配前沿高亮 + 理想/折中点。

academic_blue 主色高亮非支配前沿, 可行解浅灰淡化; 理想点用 L 形虚线指引,
折中点按"到理想点的归一化欧氏距离最近"自动选取。目标默认双双最小化,
可通过 minimize=(True, False) 等声明最大化方向。

用法（二选一）:
    1. 独立运行:
       python make_pareto_front.py [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录（gitignore 友好）, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 DEMO_POINTS 与 plot_pareto() 入参。

约定:
    - v7.7.0: 迁移 figkit + 三格式导出 + 中性色令牌。
    - 样式与色板统一经 scripts/figkit.py 加载（mathmodel.mplstyle + palettes.py,
      两者缺失时 figkit 内置等价内联回退）; 网格改 figkit.ygrid() 仅 y 向。

输入说明:
    points: 可行解序列, 每项 (目标1, 目标2) 二元组; 允许含受支配解,
            非支配子集自动筛选。

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

# ---- v7.7.0: 头部统一走共享库 figkit（样式/色板/导出/网格/中性色）----
# figkit.py 位于本脚本上二级 scripts/ 目录; 色板回退已内置于 figkit, 不再保留本文件副本
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    apply_style,
    load_neutral,
    load_palette,
    save_fig,
    ygrid,
)

# 示例数据: 总成本(万元) vs 总配送时间(小时) 的双目标可行解
DEMO_POINTS: list[tuple[float, float]] = [
    (0.38, 12.60), (0.71, 10.44), (1.06, 8.97), (1.19, 9.72), (1.44, 8.35),
    (1.82, 7.14), (2.05, 7.90), (2.31, 6.62), (2.49, 7.21), (2.76, 5.94),
    (2.98, 6.48), (3.21, 5.41), (3.44, 6.03), (3.66, 5.09), (3.90, 5.60),
    (4.13, 4.72), (4.38, 5.17), (4.61, 4.41), (4.84, 4.88), (5.06, 4.15),
    (5.30, 4.55), (5.53, 3.92), (5.77, 4.31), (6.01, 3.70), (6.22, 4.08),
    (6.47, 3.47), (6.71, 3.79), (6.94, 3.25), (7.18, 3.58), (7.42, 3.05),
    (7.63, 3.36), (7.88, 2.88), (8.10, 3.14), (8.34, 2.72), (8.58, 2.94),
    (8.81, 2.58), (9.05, 2.77), (9.29, 2.46), (9.52, 2.63), (9.76, 2.38),
    (0.52, 13.40), (0.93, 12.05), (1.61, 10.30), (2.16, 8.53), (2.53, 9.30),
    (3.05, 7.34), (3.58, 6.55), (4.02, 6.99), (4.55, 5.72), (5.01, 6.34),
    (5.48, 5.28), (5.96, 5.71), (6.39, 4.87), (6.87, 5.22), (7.35, 4.55),
    (7.79, 4.84), (8.27, 4.18), (8.70, 4.45), (9.18, 3.92), (9.63, 4.13),
    (0.85, 13.90), (1.33, 12.18), (1.78, 11.05), (2.26, 9.87), (2.74, 9.20),
    (3.23, 8.36), (3.70, 7.72), (4.18, 7.08), (4.66, 6.44), (5.14, 5.89),
    (5.62, 5.36), (6.10, 4.88), (6.57, 4.55), (7.05, 4.12), (7.53, 3.84),
    (8.01, 3.49), (8.49, 3.22), (8.97, 2.96), (9.44, 2.80), (9.92, 2.66),
]
OBJ_NAMES = ("总成本（万元）", "总配送时间（h）")


def _check_finite(values, label: str) -> None:
    """数值序列必须全为有限数值（排除 NaN/inf 与非数值）, 否则 ValueError 中文报错。"""
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{label} 含非有限数值或非数值: {v!r}")


def _nondominated(f1, f2, minimize, eps: float = 1e-12):
    """两目标下筛非支配解, 返回 (索引数组, 排序用的 axis0 顺序)。

    minimize 各轴 True=越小越优; 算法: 按 axis0 排序后单趟扫描 axis1
    的当前最优, O(n log n)。实现上把最大化轴取负, 统一化成双最小化。
    """
    import numpy as np

    sign = np.array([1.0 if minimize[0] else -1.0,
                     1.0 if minimize[1] else -1.0])
    a0 = f1 * sign[0]
    a1 = f2 * sign[1]
    order = np.lexsort((a1, a0))  # 先 axis0 后 axis1, 均升序
    keep: list[int] = []
    best_a1 = math.inf
    for idx in order:
        if a1[idx] < best_a1 - eps:  # 严格优于当前 axis1 纪录才保留
            keep.append(int(idx))
            best_a1 = float(a1[idx])
    keep.sort(key=lambda i: a0[i])  # 画线按 axis0 单调排列
    return np.asarray(keep, dtype=int)


def plot_pareto(
    points,
    obj_names: tuple[str, str] | None = None,
    minimize: tuple[bool, bool] = (True, True),
    title: str | None = None,
    out_stem: str | None = None,
) -> tuple[Path, Path]:
    """绘制帕累托前沿图并保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        points: (目标1, 目标2) 可行解序列, 至少 2 个。
        obj_names: 两目标轴名; None 用默认占位名。
        minimize: 两轴是否越小越优（默认双双最小化）。
        title: 图标题; None 用默认标题。
        out_stem: 输出文件前缀; None 时写系统临时目录。

    Raises:
        ValueError: points 为空/不足 2 个/行非二元组/含非有限数值/
            理想点或折中点计算失败（理论上不会触发, 防御性）。
    """
    import numpy as np

    rows = list(points)
    if not rows:
        raise ValueError("points 不能为空: 至少提供两个可行解")
    if len(rows) < 2:
        raise ValueError(f"points 至少需要 2 个可行解, 实际: {len(rows)} 个")
    for row in rows:
        if len(row) != 2:
            raise ValueError(f"points 每条必须是 (目标1, 目标2) 二元组, 实际: {row!r}")
        _check_finite(row, "可行解")
    if len(minimize) != 2 or not all(isinstance(m, bool) for m in minimize):
        raise ValueError(f"minimize 须为两个布尔值 (axis0, axis1), 实际: {minimize!r}")

    apply_style()
    f1 = np.asarray([r[0] for r in rows], dtype=float)
    f2 = np.asarray([r[1] for r in rows], dtype=float)
    colors = load_palette("academic_blue")
    blue, orange, red, grey = colors[0], colors[2], colors[3], load_neutral("edge_strong")
    xname, yname = obj_names or ("目标 1", "目标 2")

    # 非支配解筛选 + 理想点(各轴按 minimize 方向取最优) + 折中点(归一化空间距理想点最近)
    front_idx = _nondominated(f1, f2, minimize)
    xmin, xmax = float(f1.min()), float(f1.max())
    ymin, ymax = float(f2.min()), float(f2.max())
    # 最大化轴的理想值取 max, 距离方向取 max - value; 最小化轴取 min, value - min
    ideal_x = xmin if minimize[0] else xmax
    ideal_y = ymin if minimize[1] else ymax
    ideal = (ideal_x, ideal_y)
    xs, ys = (xmax - xmin) or 1.0, (ymax - ymin) or 1.0
    d1 = (f1 - xmin) / xs if minimize[0] else (xmax - f1) / xs
    d2 = (f2 - ymin) / ys if minimize[1] else (ymax - f2) / ys
    norm_dist = np.hypot(d1, d2)
    knee_idx = int(np.argmin(norm_dist))

    x_pad, y_pad = xs * 0.06, ys * 0.06
    fig, ax = plt.subplots(figsize=(8.0, 5.4))
    fig.subplots_adjust(left=0.115, right=0.975, top=0.93, bottom=0.115)

    # 可行解散点云（中性浅色低饱和, v7.7.0 改令牌取色）; 非支配解单独高亮
    ax.scatter(f1, f2, s=16, color=grey, alpha=0.62, linewidths=0,
               label="可行解", zorder=2)
    f1f, f2f = f1[front_idx], f2[front_idx]
    ax.plot(f1f, f2f, color=blue, linewidth=2.0, zorder=4,
            label="Pareto 前沿")
    ax.scatter(f1f, f2f, s=26, facecolor="white", edgecolor=blue,
               linewidth=1.2, zorder=5)

    # 理想点: 星标 + L 形虚线指引（从两条轴边指向星标）
    ax.plot([ideal[0], ideal[0]], [ymin - y_pad, ideal[1]], color=orange,
            linestyle="--", linewidth=1.1, alpha=0.8, zorder=3)
    ax.plot([xmin - x_pad, ideal[0]], [ideal[1], ideal[1]], color=orange,
            linestyle="--", linewidth=1.1, alpha=0.8, zorder=3)
    ax.scatter([ideal[0]], [ideal[1]], marker="*", s=190, color=orange,
               edgecolor="white", linewidth=0.6, zorder=7, label="理想点")

    # 折中点: 菱形高亮 + 到理想点连线
    ax.scatter([f1[knee_idx]], [f2[knee_idx]], marker="D", s=52,
               facecolor=red, edgecolor="white", linewidth=1.0, zorder=7,
               label="折中点")
    ax.plot([ideal[0], f1[knee_idx]], [ideal[1], f2[knee_idx]],
            color=red, linestyle=":", linewidth=1.1, alpha=0.85, zorder=6)

    # 理想点/折中点命名: 放轴区顶部留白带（y 上限之上预留 10% 高度, 保证不压点云）
    ax.set_xlim(xmin - x_pad, xmax + x_pad)
    ax.set_ylim(ymin - y_pad, ymax + y_pad * 2.6)
    top = ymax + y_pad * 2.6
    ax.text(ideal[0], top, "理想点", ha="left", va="top", fontsize=9,
            color=orange, zorder=8)
    ax.text(f1[knee_idx], top, "折中点", ha="center", va="top", fontsize=9,
            color=red, zorder=8)

    ax.set_xlabel(xname)
    ax.set_ylabel(yname)
    ax.set_title(title or "双目标优化 Pareto 前沿")
    ygrid(ax)  # v7.7.0: 散点/前沿图只留极淡 y 向网格

    legend = ax.legend(loc="upper right", frameon=True, fontsize=9)
    legend.set_zorder(10)
    return _save(fig, out_stem, "make_pareto_front")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """v7.7.0 经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成双目标帕累托前沿图（示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    try:
        png, svg = plot_pareto(DEMO_POINTS, OBJ_NAMES, out_stem=args.out)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    print(f"已输出: {png}")
    print(f"已输出: {svg}")
    print(f"已输出: {png.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
