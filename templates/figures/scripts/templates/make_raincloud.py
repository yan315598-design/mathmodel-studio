# -*- coding: utf-8 -*-
"""云雨图模板: 多组分布对比(云=KDE 半小提琴 / 箱=五数概括 / 雨=样本点)。

水平条带排布(组沿 y 轴、数值沿 x 轴), 每组条带内三层叠加:
  上层 = 云, 高斯核 KDE 半小提琴(numpy 自实现, 带宽按 Silverman 法则,
          各组共享同一密度→宽度比例尺, 组间云高可直接比较);
  中层 = 箱, 细窄白底箱线(自绘, 只保留箱体/中位线/上下须);
  下层 = 雨, 原始样本抖动散点(低 alpha 色板色, 垂直抖动用固定种子)。

不依赖 seaborn/ptitprince, matplotlib+numpy 零三方依赖。

用法（二选一）:
    1. 独立运行:
       python make_raincloud.py [--palette academic_blue] [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录 mathmodel-figs/ 下,
       产出 300dpi PNG + SVG + PDF 三格式。
    2. 复制到项目后改 _demo_data() 与 plot_raincloud() 入参。

输入说明:
    groups: [(组名, 数值数组), ...]; 数组至少 8 个有限值(够估 KDE 与分位)。

figqa: 本模板按纯 --strict 通过。注意: 本图数值轴为 x, 网格开 x 向
(读数导向图, 与甘特同例), 未用 figkit.ygrid()(它是 y 向网格)。

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
from matplotlib.patches import Rectangle

# figkit 位于本脚本上级目录 (scripts/), 注册后方可 from figkit import ...
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import (
    FIGSIZE,
    apply_style,
    despine,
    load_neutral,
    load_palette,
    save_fig,
)

# figqa 硬门脚本: templates/figures/scripts/templates/ → skill 根下 scripts/
FIGQA_SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "figqa.py"

# 条带几何: 云占 y∈[i+0.05, i+0.42], 箱占 i±0.05, 雨占 y∈[i−0.42, i−0.08]
CLOUD_TOP = 0.42
BOX_HALF = 0.05
RAIN_TOP, RAIN_DEPTH = 0.08, 0.34


def silverman_bandwidth(values: np.ndarray) -> float:
    """Silverman 经验带宽 h = 0.9·min(s, IQR/1.34)·n^(−1/5)。

    Raises:
        ValueError: 样本不足 8 个或标准差为 0。
    """
    n = values.size
    if n < 8:
        raise ValueError(f"KDE 至少需要 8 个样本, 实际: {n}")
    s = float(np.std(values, ddof=1))
    q75, q25 = np.percentile(values, [75, 25])
    iqr = float(q75 - q25)
    scale = min(s, iqr / 1.34) if iqr > 0 else s
    if scale <= 0:
        raise ValueError("样本退化(标准差为 0), 无法估核密度带宽")
    return 0.9 * scale * n ** (-0.2)


def gaussian_kde(values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """高斯核密度估计(逐点叠加, 与 scipy.stats.gaussian_kde 同口径)。"""
    h = silverman_bandwidth(values)
    z = (grid[:, None] - values[None, :]) / h
    dens = np.exp(-0.5 * z * z).sum(axis=1) / (values.size * h * np.sqrt(2 * np.pi))
    return dens


def plot_raincloud(
    groups: list[tuple[str, np.ndarray]],
    palette: str = "academic_blue",
    value_name: str = "指标值",
    title: str | None = None,
    out_prefix: str | None = None,
    seed: int = 20240501,
) -> list[str]:
    """绘制水平云雨图并三格式导出, 返回写出路径列表。

    Args:
        groups: [(组名, 数值数组)], 按顺序自下而上排列, 按顺序取色板色。
        palette: 色板名, 默认 academic_blue。
        value_name: 数值轴名(进 x 轴标签)。
        title: 已弃用（1.4.1 图题纪律: 图名放论文 caption, 不入图内）;
            保留参数仅为兼容旧调用, 不再渲染。
        out_prefix: 输出前缀(不带扩展名); None 时写系统临时目录。
        seed: 雨点垂直抖动的随机种子(固定可复现)。

    Raises:
        ValueError: groups 为空 / 样本不足 / 含非有限数值 /
            组数超过色板可分配颜色数。
    """
    if not groups:
        raise ValueError("groups 不能为空: 至少提供一组 (组名, 数值数组)")
    for name, values in groups:
        values = np.asarray(values, dtype=float)
        if values.size < 8:
            raise ValueError(f"组 '{name}' 样本数 {values.size} < 8, 无法估 KDE")
        if not np.all(np.isfinite(values)):
            raise ValueError(f"组 '{name}' 含非有限数值(NaN/inf)")
    apply_style()
    colors = load_palette(palette)
    if len(groups) > len(colors):
        raise ValueError(
            f"组数 {len(groups)} 超过色板 '{palette}' 的 {len(colors)} 个可用颜色"
        )
    rng = np.random.default_rng(seed)

    fig, ax = plt.subplots(figsize=FIGSIZE["wide"])
    fig.subplots_adjust(left=0.13, right=0.975, top=0.88, bottom=0.13)

    # 显示域: 0.5%/99.5% 分位截断, 之外的极端样本贴边显示(不丢弃);
    # 所有 artist 的数据坐标一律限制在显示域内, 避免 xlim 外的点
    # 经像素级 QA 工具按未裁剪几何误判为压到轴外刻度标签。
    all_values = np.concatenate([np.asarray(v, dtype=float) for _, v in groups])
    x_lo = float(np.quantile(all_values, 0.005))
    x_hi = float(np.quantile(all_values, 0.995))
    pad = (x_hi - x_lo) * 0.06 or 1.0
    x_lo, x_hi = x_lo - pad, x_hi + pad
    ax.set_xlim(x_lo, x_hi)
    clipped = [(name, np.clip(np.asarray(v, dtype=float), x_lo, x_hi))
               for name, v in groups]
    # 各组共用同一密度→宽度比例(峰值最高的云满高, 其余按真实峰高矮下去)
    peak = 0.0
    kdes: list[tuple[np.ndarray, np.ndarray]] = []
    for _, values in clipped:
        h = silverman_bandwidth(values)
        grid = np.linspace(max(values.min() - 3 * h, x_lo),
                           min(values.max() + 3 * h, x_hi), 256)
        dens = gaussian_kde(values, grid)
        kdes.append((grid, dens))
        peak = max(peak, float(dens.max()))
    width_scale = (CLOUD_TOP - 0.04) / peak

    for i, (color, (name, values), (grid, dens)) in enumerate(
            zip(colors, clipped, kdes)):
        values = np.asarray(values, dtype=float)

        # ---- 云: 上层半小提琴(KDE 填充 + 轮廓线, fill 是 PolyCollection) ----
        ax.fill_between(grid, i + 0.04, i + 0.04 + dens * width_scale,
                        color=color, alpha=0.50, linewidth=0, zorder=2)
        ax.plot(grid, i + 0.04 + dens * width_scale, color=color,
                linewidth=1.4, zorder=3)

        # ---- 箱: 中层细窄白底箱线(自绘, 五数概括) ----
        q1, med, q3 = np.percentile(values, [25, 50, 75])
        iqr = q3 - q1
        w_lo = float(values[values >= q1 - 1.5 * iqr].min())
        w_hi = float(values[values <= q3 + 1.5 * iqr].max())
        ax.add_patch(Rectangle((q1, i - BOX_HALF), q3 - q1, 2 * BOX_HALF,
                               facecolor="white", edgecolor=color,
                               linewidth=1.2, zorder=4))
        ax.plot([med, med], [i - BOX_HALF, i + BOX_HALF], color=color,
                linewidth=1.8, zorder=5)
        ax.plot([w_lo, q1], [i, i], color=color, linewidth=1.1, zorder=3)
        ax.plot([q3, w_hi], [i, i], color=color, linewidth=1.1, zorder=3)
        for w in (w_lo, w_hi):
            ax.plot([w, w], [i - 0.02, i + 0.02], color=color,
                    linewidth=1.1, zorder=3)

        # ---- 雨: 下层抖动散点(x=原始值, y=条带内均匀铺开) ----
        jitter_y = i - RAIN_TOP - RAIN_DEPTH * rng.random(values.size)
        ax.scatter(values, jitter_y, s=11, color=color, alpha=0.45,
                   edgecolors="none", zorder=3)

    ax.set_yticks(range(len(groups)), [name for name, _ in groups])
    ax.set_ylim(-0.55, len(groups) - 0.45)
    ax.set_xlabel(value_name)
    # 1.4.1 图题纪律: 图名与结论写进论文 caption, 不烘焙进图内
    # 数值轴为 x → 读数导向开 x 向网格(ygrid 的转置语义, 见模块 docstring)
    ax.xaxis.grid(True, color=load_neutral("grid"), alpha=0.45, linewidth=0.7)
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)
    despine(ax, keep=("bottom",))
    if out_prefix is None:
        out_prefix = str(Path(tempfile.gettempdir()) / "mathmodel-figs"
                         / "make_raincloud")
    return save_fig(fig, out_prefix)


def _demo_data() -> list[tuple[str, np.ndarray]]:
    """内置 demo: 四组典型分布形态(正态/双峰/右偏/重尾), 每组 120 样本。"""
    rng = np.random.default_rng(20240501)
    n = 120
    bimodal = np.concatenate([
        rng.normal(35, 6, n // 2), rng.normal(62, 7, n // 2)])
    return [
        ("对照组（正态）", rng.normal(50, 10, n)),
        ("干预 A（双峰）", bimodal),
        ("干预 B（右偏）", 40 + rng.exponential(12, n)),
        ("干预 C（重尾）", 45 + rng.standard_t(3, n) * 9),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="生成云雨图（四组典型分布, 示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    parser.add_argument("--palette", default="academic_blue",
                        help="色板名（默认 academic_blue）")
    args = parser.parse_args(argv)
    out = args.out or str(
        Path(tempfile.gettempdir()) / "mathmodel-figs" / "make_raincloud")
    try:
        written = plot_raincloud(_demo_data(), palette=args.palette,
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
