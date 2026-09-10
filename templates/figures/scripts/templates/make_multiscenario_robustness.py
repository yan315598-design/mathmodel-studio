# -*- coding: utf-8 -*-
"""多场景稳健性对比模板: 各场景指标分布的箱线图/小提琴图 + 基准参考线。

cool_nature 色板（冷色 Nature/IEEE 期刊风）。

用法（二选一）:
    1. 独立运行:
       python make_multiscenario_robustness.py [--mode box|violin] [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录（gitignore 友好）, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 SCENARIOS/BASELINE 与 plot_robustness() 入参。

约定:
    - 1.1.0: 迁移 figkit + 三格式导出 + 中性色令牌。
    - 样式与色板统一经 scripts/figkit.py 加载（mathmodel.mplstyle + palettes.py,
      两者缺失时 figkit 内置等价内联回退）; 网格改 figkit.ygrid() 仅 y 向。

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

# ---- 1.1.0: 头部统一走共享库 figkit（样式/色板/导出/网格）----
# figkit.py 位于本脚本上二级 scripts/ 目录; 色板回退已内置于 figkit, 不再保留本文件副本
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    apply_style,
    load_palette,
    save_fig,
    ygrid,
)

# 示例数据: 各场景的服务水平样本（可换成功率/误差/收益等任意指标）
SCENARIOS: dict[str, list[float]] = {
    "基准场景": [0.862, 0.871, 0.858, 0.880, 0.865, 0.874, 0.869, 0.883],
    "需求 +20%": [0.823, 0.838, 0.812, 0.845, 0.830, 0.819, 0.841, 0.827],
    "运力 -15%": [0.798, 0.815, 0.786, 0.809, 0.792, 0.803, 0.818, 0.794],
    "极端天气": [0.762, 0.785, 0.748, 0.796, 0.771, 0.758, 0.789, 0.766],
}
BASELINE = 0.866  # 基准参考线（如合同承诺的服务水平）


def _check_finite(values, label: str) -> None:
    """数值序列必须全为有限数值（排除 NaN/inf 与非数值）, 否则 ValueError 中文报错。"""
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{label} 含非有限数值或非数值: {v!r}")


def plot_robustness(
    scenarios: dict[str, list[float]],
    baseline: float,
    metric: str = "服务水平",
    mode: str = "box",
    out_stem: str | None = None,
) -> tuple[Path, Path]:
    """绘制多场景稳健性对比图并保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        scenarios: 场景名 → 指标样本列表。
        baseline: 基准参考线值（画水平虚线并在图内标注）。
        metric: 指标名（进 y 轴标签）。
        mode: box=箱线图, violin=小提琴图。
        out_stem: 输出文件前缀; None 时写系统临时目录。

    Raises:
        ValueError: scenarios 为空 / 某场景样本列表为空 / 样本或 baseline
            非有限数值。
    """
    if not scenarios:
        raise ValueError("scenarios 不能为空: 至少提供一个场景")
    for name, samples in scenarios.items():
        if not samples:
            raise ValueError(f"场景 {name!r} 的样本列表为空")
        _check_finite(samples, f"场景 {name!r} 样本")
    _check_finite((baseline,), "baseline")

    apply_style()
    colors = load_palette("cool_nature")
    dark, orange, red = colors[0], colors[4], colors[5]  # 深蓝灰/均值橙/基准红
    names = list(scenarios)
    data = [scenarios[n] for n in names]
    fig, ax = plt.subplots(figsize=(7.2, 4.5))

    if mode == "violin":
        parts = ax.violinplot(data, positions=range(len(names)),
                              showmedians=True, widths=0.7)
        for body, color in zip(parts["bodies"], colors):
            body.set_facecolor(color)
            body.set_alpha(0.55)
            body.set_edgecolor(color)
        for key in ("cbars", "cmins", "cmaxes", "cmedians"):
            parts[key].set_color(dark)
            parts[key].set_linewidth(1.2)
    else:
        bp = ax.boxplot(data, positions=range(len(names)), widths=0.5,
                        patch_artist=True, showmeans=True,
                        medianprops=dict(color=dark, linewidth=1.4),
                        meanprops=dict(marker="D", markerfacecolor=orange,
                                       markeredgecolor="none", markersize=5))
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.55)
            patch.set_edgecolor(color)

    # 先固定 y 轴范围, 让标注偏移量有确定的参照
    all_values = [v for samples in data for v in samples]
    lo, hi = min(all_values), max(all_values)
    span = (hi - lo) or 1.0
    ax.set_ylim(lo - span * 0.15, hi + span * 0.28)
    ygrid(ax)  # 1.1.0: 箱线/小提琴对比只留极淡 y 向网格

    # 基准参考线: 虚线横贯, 文字放在线上方右侧留白处
    ax.axhline(baseline, color=red, linestyle="--", linewidth=1.4)
    ax.text(
        len(names) - 0.42,
        baseline + span * 0.025,
        f"基准线 {baseline:.3f}",
        color=red,
        ha="right",
        va="bottom",
        fontsize=9,
    )

    # 各场景中位数标注: 放在样本最大值上方, 不压箱体/中线/均值标记
    for i, samples in enumerate(data):
        median = sorted(samples)[len(samples) // 2]
        ax.text(i, max(samples) + span * 0.04, f"中位 {median:.3f}",
                ha="center", va="bottom", fontsize=9)

    ax.set_xticks(range(len(names)), names)
    ax.set_ylabel(metric)
    # 1.4.1 图题纪律: 图名与结论写进论文 caption, 不烘焙进图内
    return _save(fig, out_stem, "make_multiscenario_robustness")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """1.1.0 经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成多场景稳健性对比图（示例数据）")
    parser.add_argument("--mode", choices=["box", "violin"], default="box",
                        help="box=箱线图（默认）, violin=小提琴图")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    try:
        png, svg = plot_robustness(SCENARIOS, BASELINE, mode=args.mode, out_stem=args.out)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    print(f"已输出: {png}")
    print(f"已输出: {svg}")
    print(f"已输出: {png.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
