# -*- coding: utf-8 -*-
"""泰勒图模板: 多模型 vs 观测 REF 的综合精度对比（极坐标自绘, 不依赖 SkillMetrics）。

几何约定:
  - 径向 = 标准差 σ, 角度 = arccos(相关系数 r), 观测为 REF 星标参考点;
  - 以 REF 为圆心的绿色虚线弧为 RMSE(cRMSD) 等值线:
    d² = σ_m² + σ_o² − 2 r σ_m σ_o  →  r(θ) = σ_o cosθ + √(d² − σ_o² sin²θ);
  - 相关系数全部非负时只画 0..90° 四分之一圆, 存在负 r 时自动扩展到 180°;
  - 图例列出各模型名与决定系数 R², 放图下方横排。

用法（二选一）:
    1. 独立运行:
       python make_taylor_diagram.py [--palette academic_blue] [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录 mathmodel-figs/ 下,
       产出 300dpi PNG + SVG + PDF 三格式。
    2. 复制到项目后改 DEMO_MODELS 与 plot_taylor() 入参。

输入说明:
    models: [(模型名, 标准差 σ_m, 相关系数 r), ...]; r ∈ [−1, 1]。

figqa: 本模板按纯 --strict 通过(极坐标, 径向刻度标签放在 135° 空白方位,
模型点/等值线弧均不与文本相交)。若自定义数据导致弧线贴上刻度标签,
可在 figqa 命令追加 --allow-box-labels 降噪(本图无盒内标签, 一般不需要)。

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

# figkit 位于本脚本上级目录 (scripts/), 注册后方可 from figkit import ...
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import (
    FIGSIZE,
    apply_style,
    load_neutral,
    load_palette,
    save_fig,
)

# figqa 硬门脚本: templates/figures/scripts/templates/ → skill 根下 scripts/
FIGQA_SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "figqa.py"

# 角度刻度上标注的相关系数取值(0..90° 半圆优先, −0.2 供扩展半圆使用)
R_TICK_VALUES = [1.0, 0.9, 0.8, 0.6, 0.4, 0.2, 0.0, -0.2]

# demo: 观测 σ=1.60, 四个模型(最后一个是负相关, 触发 0..180° 扩展半圆)
OBS_SIGMA = 1.60
DEMO_MODELS: list[tuple[str, float, float]] = [
    ("模型 A", 1.50, 0.93),
    ("模型 B", 1.20, 0.78),
    ("模型 C", 2.10, 0.55),
    ("模型 D", 0.90, -0.18),
]
# RMSE 等值线半径(与 σ 同单位), 图例统一说明
RMSE_LEVELS = (0.6, 1.2, 1.8)


def _rmse_arc(sigma_obs: float, d: float, theta_max: float, r_max: float,
              n: int = 361) -> list[tuple[np.ndarray, np.ndarray]]:
    """算以 (θ=0, r=σ_obs) 的 REF 点为圆心、半径 d 的圆弧(上半支)。

    只保留 0 ≤ r ≤ r_max 的段(极坐标下超出径向上限/负半径的点不会被
    裁剪而是画到圆盘外, 会穿过盘外刻度标签), 并按连续性拆成若干
    无 NaN 子段返回 [(theta_seg, r_seg), ...] —— 不用 NaN 断线,
    避免下游像素级 QA 工具对 NaN 端点的误判。

    Raises:
        ValueError: d ≤ 0 或 σ_obs ≤ 0。
    """
    if d <= 0:
        raise ValueError(f"RMSE 等值线半径须为正, 实际: {d}")
    theta = np.linspace(0.0, theta_max, n)
    r_all = _arc_r(sigma_obs, d, theta)
    radicand = d * d - (sigma_obs * np.sin(theta)) ** 2
    valid = (radicand >= 0) & (r_all >= 0) & (r_all <= r_max)
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    start = None
    for i, ok in enumerate(valid):
        if ok and start is None:
            start = i
        elif not ok and start is not None:
            segments.append((theta[start:i], r_all[start:i]))
            start = None
    if start is not None:
        segments.append((theta[start:], r_all[start:]))
    return segments


def _arc_r(sigma_obs: float, d: float, theta: np.ndarray) -> np.ndarray:
    """圆弧径向坐标 r(θ) = σ_o cosθ + √(d² − σ_o² sin²θ)（输入须为有效段）。"""
    radicand = d * d - (sigma_obs * np.sin(theta)) ** 2
    return sigma_obs * np.cos(theta) + np.sqrt(np.maximum(radicand, 0.0))


def plot_taylor(
    obs_sigma: float,
    models: list[tuple[str, float, float]],
    palette: str = "academic_blue",
    rmse_levels: tuple[float, ...] = RMSE_LEVELS,
    title: str | None = None,
    out_prefix: str | None = None,
) -> list[str]:
    """绘制泰勒图并三格式导出, 返回写出路径列表。

    Args:
        obs_sigma: 观测标准差 σ_o (REF 参考点径向位置)。
        models: [(模型名, 标准差 σ_m, 相关系数 r)] 列表, 按顺序取色板色。
        palette: 色板名, 默认 academic_blue。
        rmse_levels: RMSE 等值线半径元组(与 σ 同单位)。
        title: 已弃用（1.4.1 图题纪律: 图名放论文 caption, 不入图内）;
            保留参数仅为兼容旧调用, 不再渲染。
        out_prefix: 输出前缀(不带扩展名); None 时写系统临时目录。

    Raises:
        ValueError: obs_sigma ≤ 0 / models 为空 / σ_m ≤ 0 / r 超出 [−1, 1] /
            模型数超过色板可分配颜色数。
    """
    if obs_sigma <= 0:
        raise ValueError(f"obs_sigma 须为正, 实际: {obs_sigma}")
    if not models:
        raise ValueError("models 不能为空: 至少提供一个 (名称, σ, r) 三元组")
    for name, sigma, r in models:
        if sigma <= 0:
            raise ValueError(f"模型 '{name}' 标准差须为正, 实际: {sigma}")
        if not -1.0 <= r <= 1.0:
            raise ValueError(f"模型 '{name}' 相关系数须在 [-1, 1], 实际: {r}")
    apply_style()
    colors = load_palette(palette)
    if len(models) + 1 > len(colors):
        raise ValueError(
            f"模型数+观测 {len(models) + 1} 超过色板 '{palette}' 的 {len(colors)} 个可用颜色"
        )
    ink = load_neutral("ink")
    # RMSE 等值线用色板中的绿(第 5 色), 对应令牌"绿=达标/参考"语义
    arc_green = colors[4]

    has_neg_r = any(r < 0 for _, _, r in models)
    theta_max_deg = 180.0 if has_neg_r else 90.0
    theta_max = np.radians(theta_max_deg)
    sigma_all = [obs_sigma] + [m[1] for m in models]
    r_max = max(sigma_all) * 1.18

    fig = plt.figure(figsize=FIGSIZE["square"])
    ax = fig.add_subplot(projection="polar")
    fig.subplots_adjust(left=0.08, right=0.94, top=0.90, bottom=0.24)
    ax.set_thetamin(0.0)
    ax.set_thetamax(theta_max_deg)
    ax.set_rlim(0.0, r_max)
    ax.grid(True, color=load_neutral("grid"), alpha=0.45, linewidth=0.7)
    ax.spines["polar"].set_color(load_neutral("edge"))

    # 角度刻度 = 相关系数; 径向刻度放在 135° (半圆外/空白方位, 避开数据)
    tick_degs, tick_labels = [], []
    for v in R_TICK_VALUES:
        deg = float(np.degrees(np.arccos(v)))
        if deg <= theta_max_deg + 1e-9:
            tick_degs.append(deg)
            tick_labels.append(f"{v:.1f}")
    ax.set_thetagrids(tick_degs, tick_labels, fontsize=9)
    r_step = 0.5
    r_ticks = [t for t in np.arange(r_step, r_max, r_step)]
    ax.set_rgrids(r_ticks, angle=135.0, fontsize=9)

    # RMSE 等值线弧: 三条半径共用一个图例项(具体 d 值见模块 docstring)
    for i, d in enumerate(rmse_levels):
        for j, (t_seg, r_seg) in enumerate(_rmse_arc(obs_sigma, d, theta_max, r_max)):
            ax.plot(t_seg, r_seg, linestyle="--", linewidth=1.1, color=arc_green,
                    alpha=0.85, zorder=2,
                    label="cRMSD 等值线" if (i == 0 and j == 0) else None)

    # 观测 REF 星标(黑色星, 白描边)
    ax.plot([0.0], [obs_sigma], marker="*", markersize=17, linestyle="none",
            color=ink, markeredgecolor="white", markeredgewidth=1.0, zorder=6,
            label=f"观测 REF（σ={obs_sigma:.2f}）")

    # 模型散点: 实心色 + 白描边
    for color, (name, sigma, r) in zip(colors, models):
        theta = float(np.arccos(r))
        ax.plot([theta], [sigma], marker="o", markersize=9, linestyle="none",
                markerfacecolor=color, markeredgecolor="white",
                markeredgewidth=1.2, zorder=6, label=f"{name}（R²={r * r:.2f}）")

    # 右下角几何说明(半圆盘只占 axes 上半, 右下角为空白)
    ax.text(0.99, 0.02, "径向 = 标准差 σ　角度 = arccos(相关系数 r)",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8,
            color=load_neutral("secondary"))

    # 1.4.1 图题纪律: 图名与结论写进论文 caption, 不烘焙进图内
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=2,
              fontsize=9, columnspacing=1.2)
    if out_prefix is None:
        out_prefix = str(Path(tempfile.gettempdir()) / "mathmodel-figs"
                         / "make_taylor_diagram")
    return save_fig(fig, out_prefix)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="生成泰勒图（多模型 vs 观测 REF, 示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    parser.add_argument("--palette", default="academic_blue",
                        help="色板名（默认 academic_blue）")
    args = parser.parse_args(argv)
    out = args.out or str(
        Path(tempfile.gettempdir()) / "mathmodel-figs" / "make_taylor_diagram")
    try:
        written = plot_taylor(OBS_SIGMA, DEMO_MODELS, palette=args.palette,
                              out_prefix=out)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    for path in written:
        print(f"已输出: {path}")
    print(f"[提示] 出图后跑该模板的 figqa 硬门: "
          f"python {FIGQA_SCRIPT} <图脚本或输出目录> --strict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
