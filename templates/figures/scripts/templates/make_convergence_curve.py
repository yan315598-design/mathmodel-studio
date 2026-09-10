# -*- coding: utf-8 -*-
"""算法收敛曲线模板: 多算法目标值随迭代下降对比, 全局最优水平虚线标注,
各算法收敛代次以顶点标记 + 竖虚线 + 代次文字三重标记。

academic_blue 色板顺序配色; --log 切对数 y 轴（收敛型数值常跨数量级）。

用法（二选一）:
    1. 独立运行:
       python make_convergence_curve.py [--log] [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录（gitignore 友好）, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 DEMO_HISTORIES/BEST_VALUE/CONVERGED 与 plot_convergence() 入参。

约定:
    - 1.1.0: 迁移 figkit + 三格式导出 + 中性色令牌。
    - 样式与色板统一经 scripts/figkit.py 加载（mathmodel.mplstyle + palettes.py,
      两者缺失时 figkit 内置等价内联回退）; 网格改 figkit.ygrid() 仅 y 向。

输入说明:
    histories: 算法名 → 每代目标值列表（可不等长, 建议单调不增）。
    best_value: 全局最优参考值（画水平虚线并进图例）。
    converged: 可选, 算法名 → 收敛代次(1 基, 不超过该算法长度)。

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

# ---- 1.1.0: 头部统一走共享库 figkit（样式/色板/导出/网格/中性色）----
# figkit.py 位于本脚本上二级 scripts/ 目录; 色板回退已内置于 figkit, 不再保留本文件副本
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    apply_style,
    load_neutral,
    load_palette,
    save_fig,
    ygrid,
)

# 示例数据: 三种启发式算法最小化某目标时的每代最优值（长度可不同）
DEMO_HISTORIES: dict[str, list[float]] = {
    "DE（差分进化）": [
        150.3, 120.8, 101.9, 89.4, 80.7, 74.2, 69.0, 64.8, 61.3, 58.4,
        56.0, 53.9, 52.1, 50.6, 49.2, 48.0, 46.9, 45.9, 45.0, 44.2,
        43.5, 42.8, 42.2, 41.6, 41.1, 40.6, 40.1, 39.7, 39.3, 38.9,
        38.5, 38.2, 37.9, 37.5, 37.2, 36.9, 36.7, 36.4, 36.1, 35.9,
    ],
    "PSO（粒子群）": [
        168.8, 129.4, 105.6, 88.2, 76.4, 68.1, 61.9, 57.2, 53.6, 50.7,
        48.2, 46.1, 44.3, 42.8, 41.4, 40.2, 39.1, 38.2, 37.3, 36.5,
        35.8, 35.1, 34.5, 33.9, 33.4, 32.9, 32.4, 32.0, 31.6, 31.2,
        30.8, 30.5, 30.1, 29.8, 29.5, 29.2, 28.9, 28.7, 28.4, 28.2,
        27.9, 27.7, 27.5, 27.3, 27.0, 26.8, 26.6, 26.4, 26.3, 26.1,
        25.9, 25.7, 25.6, 25.4, 25.2, 25.1, 24.9, 24.8, 24.6, 24.5,
    ],
    "GA（遗传算法）": [
        182.4, 166.1, 152.3, 141.0, 132.5, 125.1, 119.2, 114.5, 110.6, 107.2,
        104.4, 102.0, 99.8, 97.6, 95.7, 93.9, 92.2, 90.6, 89.1, 87.6,
        86.3, 85.0, 83.8, 82.7, 81.6, 80.6, 79.6, 78.7, 77.8, 77.0,
        76.2, 75.4, 74.7, 74.0, 73.3, 72.7, 72.1, 71.5, 70.9, 70.4,
        69.8, 69.3, 68.8, 68.3, 67.8, 67.4, 66.9, 66.5, 66.1, 65.7,
        65.3, 64.9, 64.6, 64.2, 63.9, 63.5, 63.2, 62.9, 62.6, 62.3,
        62.0, 61.7, 61.4, 61.2, 60.9, 60.7, 60.4, 60.2, 59.9, 59.7,
        59.5, 59.3, 59.0, 58.8, 58.6, 58.4, 58.2, 58.0, 57.8, 57.7,
    ],
}
BEST_VALUE = 24.0  # 已知全局最优（参考线）
CONVERGED = {"DE（差分进化）": 29, "PSO（粒子群）": 44, "GA（遗传算法）": 73}


def _check_finite(values, label: str) -> None:
    """数值序列必须全为有限数值（排除 NaN/inf 与非数值）, 否则 ValueError 中文报错。"""
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{label} 含非有限数值或非数值: {v!r}")


def _text_px_width(text: str, font_px: float) -> float:
    """按全角/半角估算文本像素宽（全角=font_px, 半角=0.5*font_px + 微留白）。"""
    width = sum(font_px if ord(ch) > 0x2E80 else font_px * 0.5 for ch in text)
    return width + 4.0


def plot_convergence(
    histories: dict[str, list[float]],
    best_value: float,
    converged: dict[str, int] | None = None,
    ylog: bool = False,
    title: str | None = None,
    out_stem: str | None = None,
) -> tuple[Path, Path]:
    """绘制算法收敛曲线对比图并保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        histories: 算法名 → 每代目标值（1 基迭代, 长度 >= 2）。
        best_value: 全局最优参考值, 画水平虚线。
        converged: 可选, 算法名 → 收敛代次（1 基, 须 <= 该算法长度）。
        ylog: True 时 y 轴取对数刻度（要求全部值为正）。
        title: 已弃用（1.4.1 图题纪律: 图名放论文 caption, 不入图内）;
            保留参数仅为兼容旧调用, 不再渲染。
        out_stem: 输出文件前缀; None 时写系统临时目录。

    Raises:
        ValueError: histories 为空 / 序列长度不足 2 / 含非有限值 /
            best_value 非有限 / converged 指向未知算法或越界 /
            ylog 下存在非正值。
    """
    if not histories:
        raise ValueError("histories 不能为空: 至少提供一种算法的收敛序列")
    for name in histories:
        if not str(name).strip():
            raise ValueError("算法名不能为空")
    for name, seq in histories.items():
        if len(seq) < 2:
            raise ValueError(f"算法 {name!r} 收敛序列长度 {len(seq)} < 2, 无法画曲线")
        _check_finite(seq, f"算法 {name!r} 收敛值")
        if ylog and any(v <= 0.0 for v in seq):
            raise ValueError(
                f"--log 需要全正值, 算法 {name!r} 存在 <= 0 的值; "
                "请平移指标或去掉 --log"
            )
    _check_finite((best_value,), "best_value")
    if ylog and best_value <= 0.0:
        raise ValueError("--log 下 best_value 须为正")

    marks: list[tuple[int, str]] = []
    if converged:
        for name, gen in converged.items():
            if name not in histories:
                raise ValueError(
                    f"converged 指向未知算法 {name!r}; 可用算法: {sorted(histories)}"
                )
            if not isinstance(gen, int) or isinstance(gen, bool):
                raise ValueError(f"算法 {name!r} 收敛代次须为整数, 实际: {gen!r}")
            if not (0 < gen <= len(histories[name])):
                raise ValueError(
                    f"算法 {name!r} 收敛代次 {gen} 越界, 应在 1..{len(histories[name])}"
                )
            marks.append((int(gen), name))
        marks.sort(key=lambda m: m[0])

    apply_style()
    import numpy as np

    colors = load_palette("academic_blue")
    ref_grey = load_neutral("arrow")  # 参考线灰: design_tokens 语义角色 reference
    lo_all = min(min(v) for v in histories.values())
    hi_all = max(max(v) for v in histories.values())
    lo = min(lo_all, best_value)
    hi = hi_all

    fig, ax = plt.subplots(figsize=(9.4, 5.4))
    # 右侧 24% 白边放图例; 图名按 1.4.1 图题纪律放论文 caption, 代次文字用 axes 分数坐标压在轴内顶部
    fig.subplots_adjust(left=0.115, right=0.755, top=0.93, bottom=0.115)

    max_len = max(len(v) for v in histories.values())
    order = sorted(histories)
    for i, name in enumerate(order):
        vals = np.asarray(histories[name], dtype=float)
        ax.plot(np.arange(1, len(vals) + 1), vals,
                color=colors[i % len(colors)], linewidth=1.8, label=name, zorder=4)

    # 坐标范围: y 下限压到最优线之下, 上限略留白
    if ylog:
        ratio = (hi / lo) if lo > 0 else 1.0
        ymin = lo / (ratio ** 0.10)
        ytop = hi * (ratio ** 0.05)
    else:
        span = max(hi - lo, 1e-9)
        ymin = lo - span * 0.06
        ytop = hi + span * 0.08
    ax.set_ylim(ymin, ytop)
    ax.set_xlim(1, max_len)
    ygrid(ax)  # 1.1.0: 默认只留极淡 y 向网格, 关闭 x 向

    # 收敛标记: 白芯顶点 + 竖虚线到底 + 顶部代次文字（x 数据坐标 / y 轴分数坐标,
    # 同层文字横向错开, 放不下时逐层下移, 保证互不重叠）
    if marks:
        px_per_unit = (ax.transData.transform((2.0, 0.0))[0]
                       - ax.transData.transform((1.0, 0.0))[0])
        font_px = 8.5 / 72.0 * fig.dpi
        placed: list[tuple[float, float, int]] = []  # (x_left, x_right, level)
        for gen, name in marks:
            color = colors[order.index(name) % len(colors)]
            val = float(histories[name][gen - 1])
            ax.scatter([gen], [val], s=48, facecolor="white", edgecolor=color,
                       linewidth=1.5, zorder=6)
            ax.plot([gen, gen], [ymin, val], color=color, linestyle=":",
                    linewidth=1.0, alpha=0.75, zorder=2)
            text = f"{name.split('（')[0]} {gen}代"
            half = _text_px_width(text, font_px) / 2.0 / max(px_per_unit, 1e-9)
            level = 0
            while level < 4:
                conflict = any(
                    abs(gen - cx) < half + other_half + 1.0
                    for cx, other_half, other_level in placed
                    if other_level == level
                )
                if not conflict:
                    break
                level += 1
            placed.append((gen, half, level))
            # x 用数据坐标(代次), y 用轴分数坐标(顶部向下排层), 两种坐标系并存
            ax.annotate(text, xy=(gen, 0.955 - 0.058 * level),
                        xycoords=("data", "axes fraction"),
                        ha="center", va="bottom", fontsize=8.5,
                        color=load_neutral("secondary"), zorder=8)

    # 最优参考线（参考线灰虚线, 进图例说明精确值）
    ax.plot([1, max_len], [best_value, best_value], color=ref_grey, linestyle="--",
            linewidth=1.3, zorder=3,
            label=f"全局最优线（{best_value:.6g}）")

    if ylog:
        ax.set_yscale("log")
    ax.set_xlabel("迭代次数")
    ax.set_ylabel("目标函数值")
    # 1.4.1 图题纪律: 图名与结论写进论文 caption, 不烘焙进图内
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 0.99), frameon=True,
              fontsize=9)
    return _save(fig, out_stem, "make_convergence_curve")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """1.1.0 经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成多算法收敛曲线对比图（示例数据）")
    parser.add_argument("--log", action="store_true", help="y 轴取对数刻度")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    try:
        png, svg = plot_convergence(
            DEMO_HISTORIES, BEST_VALUE, CONVERGED, ylog=args.log, out_stem=args.out
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
