# -*- coding: utf-8 -*-
"""评价排序条形图模板: 方案按综合得分降序横向条, 条身按指标贡献加权堆叠分解,
得分数值标注条端。academic_blue 系逐指标配色, 图例置于图下方。

用法（二选一）:
    1. 独立运行:
       python make_ranking_bar.py [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录（gitignore 友好）, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 DEMO_SCORES/DEMO_WEIGHTS 与 plot_ranking() 入参。

约定:
    - v7.7.0: 迁移 figkit + 三格式导出 + 中性色令牌。
    - 样式与色板统一经 scripts/figkit.py 加载（mathmodel.mplstyle + palettes.py,
      两者缺失时 figkit 内置等价内联回退）; 横向条读数方向在 x, 保留 x 向网格。

输入说明:
    scores: 方案名 → {指标名: 得分}; weights: 指标名 → 权重(>=0)。
    每段贡献 = 权重 × 得分, 条长 = 各段贡献之和 = 综合得分。
    得分/权重须非负（评价类输出天然非负; 负贡献无法堆叠, 请先正向化）。

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

# ---- v7.7.0: 头部统一走共享库 figkit（样式/色板/导出/中性色）----
# figkit.py 位于本脚本上二级 scripts/ 目录; 色板回退已内置于 figkit, 不再保留本文件副本
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    apply_style,
    load_neutral,
    load_palette,
    save_fig,
)

# 示例数据: 五个物流方案在五项指标(百分制)下的得分与权重
DEMO_SCORES: dict[str, dict[str, float]] = {
    "方案 A": {"经济性": 86.0, "准时率": 74.0, "绿色度": 65.0, "可靠性": 88.0, "信息化": 70.0},
    "方案 B": {"经济性": 78.0, "准时率": 82.0, "绿色度": 71.0, "可靠性": 76.0, "信息化": 85.0},
    "方案 C": {"经济性": 90.0, "准时率": 60.0, "绿色度": 80.0, "可靠性": 62.0, "信息化": 58.0},
    "方案 D": {"经济性": 65.0, "准时率": 70.0, "绿色度": 76.0, "可靠性": 58.0, "信息化": 66.0},
    "方案 E": {"经济性": 80.0, "准时率": 68.0, "绿色度": 60.0, "可靠性": 70.0, "信息化": 62.0},
}
DEMO_WEIGHTS: dict[str, float] = {
    "经济性": 0.30, "准时率": 0.25, "绿色度": 0.20, "可靠性": 0.15, "信息化": 0.10,
}


def _check_finite(values, label: str) -> None:
    """数值序列必须全为有限数值（排除 NaN/inf 与非数值）, 否则 ValueError 中文报错。"""
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{label} 含非有限数值或非数值: {v!r}")


def plot_ranking(
    scores: dict[str, dict[str, float]],
    weights: dict[str, float],
    xlabel: str = "综合得分",
    title: str | None = None,
    out_stem: str | None = None,
) -> tuple[Path, Path]:
    """绘制评价排序（权重分解堆叠）条形图并保存 PNG+SVG+PDF 三格式。

    Args:
        scores: 方案名 → {指标名: 得分}; 各方案须覆盖与 weights 相同的指标集。
        weights: 指标名 → 权重, 顺序即堆叠段顺序（dict 保持插入序）。
        xlabel: x 轴名（默认 "综合得分"）。
        title: 图标题; None 用默认标题。
        out_stem: 输出文件前缀; None 时写系统临时目录。

    Raises:
        ValueError: scores/weights 为空 / 指标集不一致 / 得分权重非负约束 /
            名称含空串 / 数值非有限。
    """
    if not scores:
        raise ValueError("scores 不能为空: 至少提供一个方案")
    if not weights:
        raise ValueError("weights 不能为空: 至少提供一个指标权重")
    for name, comp in scores.items():
        if not str(name).strip():
            raise ValueError("方案名不能为空")
        if not comp:
            raise ValueError(f"方案 {name!r} 的指标得分字典为空")
        _check_finite(list(comp.values()), f"方案 {name!r} 得分")
        for v in comp.values():
            if v < 0.0:
                raise ValueError(
                    f"方案 {name!r} 存在负得分 {v}; 评价得分应非负, 请先正向化"
                )
    for ind, w in weights.items():
        if not str(ind).strip():
            raise ValueError("指标名不能为空")
        _check_finite((w,), f"指标 {ind!r} 权重")
        if w < 0.0:
            raise ValueError(f"指标 {ind!r} 权重 {w} < 0; 权重应非负")
    inds = list(weights)
    for name, comp in scores.items():
        if set(comp) != set(inds):
            missing = sorted(set(inds) - set(comp))
            extra = sorted(set(comp) - set(inds))
            msg = f"方案 {name!r} 指标集与 weights 不一致"
            if missing:
                msg += f"; 缺少: {missing}"
            if extra:
                msg += f"; 多余: {extra}"
            raise ValueError(msg)
    if len(inds) > 8:
        raise ValueError(f"指标数 {len(inds)} > 8, 堆叠段过多难辨认; 请合并同类指标")

    apply_style()
    import numpy as np

    colors = load_palette("academic_blue")

    # 每方案各段贡献 = w * score, 总得分 = 求和; 按总得分降序排条
    contrib: dict[str, np.ndarray] = {}
    totals: dict[str, float] = {}
    for name, comp in scores.items():
        c = np.asarray([comp[ind] for ind in inds], dtype=float) * np.asarray(
            [weights[ind] for ind in inds], dtype=float)
        contrib[name] = c
        totals[name] = float(c.sum())
    order = sorted(scores, key=lambda n: totals[n], reverse=True)
    xmax = max(totals.values())

    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    # 底部为数值轴标签与指标图例预留 24%; 左侧由自适应测量再收紧
    fig.subplots_adjust(left=0.02, right=0.985, top=0.90, bottom=0.24)
    n_row = len(order)
    y = np.arange(n_row)[::-1]  # 第一名放最上

    for i, name in enumerate(order):
        c = contrib[name]
        left = 0.0
        for j, val in enumerate(c):
            if val <= 0.0:
                continue
            ax.barh(y[i], val, left=left, height=0.58, color=colors[j % len(colors)],
                    edgecolor="white", linewidth=0.5, zorder=3)
            left += val
        ax.text(left, y[i], f" {totals[name]:.2f}", va="center", ha="left",
                fontsize=9, color=load_neutral("ink"), zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels(order)
    ax.set_ylim(-0.62, n_row - 0.38)
    ax.set_xlim(0.0, xmax * 1.22)
    ax.set_xlabel(xlabel)
    ax.set_title(title or "方案综合评分排序（按指标贡献分解）")
    # 横向条读数方向在 x（同甘特属读数导向图）: 保留 x 向网格, 关闭 y 向
    ax.xaxis.grid(True, color=load_neutral("grid"), alpha=0.45, linewidth=0.7)
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)
    _fit_left_margin(fig, ax, pad_px=14)  # 长方案名防画布左缘裁剪

    # 指标贡献图例: 横向单行外置图下方（轴底之上还有 xlabel, 锚点取 -0.13）
    handles = [
        plt.Line2D([0], [0], marker="s", markersize=11, linewidth=0,
                   markerfacecolor=colors[j % len(colors)], label=inds[j])
        for j in range(len(inds))
    ]
    ax.legend(
        handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.135),
        ncol=len(inds), frameon=True, fontsize=9, columnspacing=1.2,
        handletextpad=0.6,
    )
    return _save(fig, out_stem, "make_ranking_bar")


def _fit_left_margin(fig, ax, pad_px: float = 14.0) -> None:
    """按 y 刻度标签实际渲染宽度右移坐标轴, 防止超长分类名被画布左缘裁切。"""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    leftmost = min(
        (lbl.get_window_extent(renderer).x0
         for lbl in ax.get_yticklabels() if lbl.get_text().strip()),
        default=None,
    )
    if leftmost is None or leftmost >= pad_px:
        return
    pos = ax.get_position()
    canvas_w = fig.bbox.width
    new_x0 = (pos.x0 * canvas_w + (pad_px - leftmost)) / canvas_w
    ax.set_position([new_x0, pos.y0, pos.x1 - new_x0, pos.height])
    fig.canvas.draw()


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """v7.7.0 经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成评价排序（权重分解）条形图（示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    try:
        png, svg = plot_ranking(DEMO_SCORES, DEMO_WEIGHTS, out_stem=args.out)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    print(f"已输出: {png}")
    print(f"已输出: {svg}")
    print(f"已输出: {png.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
