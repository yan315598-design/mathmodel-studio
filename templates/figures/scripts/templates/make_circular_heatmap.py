# -*- coding: utf-8 -*-
"""环形热图模板: N 样本 × M 指标的径向分层极坐标热图(自绘, 不依赖 pyCirclize)。

几何约定:
  - 角度 = 样本扇区(N 个, 均分去掉一个 12° 标签缺口后的圆周);
  - 径向 = 指标环(M 个同心环, 内→外按指标顺序), pcolormesh 上色,
    白色细缝分隔(QuadMesh 与 imshow 热图同属 figqa 的免检口径);
  - 颜色 = 每列 min-max 归一化值映射 get_cmap("sequential");
  - 外圈样本名沿径向竖排(永远正立可读); 指标名以"径向内→外顺序"
    一行文字放在图下方(受 figqa 检测); 右侧 colorbar 标"归一化得分"。

用法（二选一）:
    1. 独立运行:
       python make_circular_heatmap.py [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录 mathmodel-figs/ 下,
       产出 300dpi PNG + SVG + PDF 三格式。
    2. 复制到项目后改 _demo_data() 与 plot_circular_heatmap() 入参。

输入说明:
    values: N×M 二维数组(有限数值); 行=样本, 列=指标, 列内 min-max 归一化。

figqa: 本模板按纯 --strict 通过。

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
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

# figkit 位于本脚本上级目录 (scripts/), 注册后方可 from figkit import ...
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import (
    FIGSIZE,
    apply_style,
    get_cmap,
    load_neutral,
    save_fig,
)

# figqa 硬门脚本: templates/figures/scripts/templates/ → skill 根下 scripts/
FIGQA_SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "figqa.py"

# 几何常量: 标签缺口张角与最内环内径(圆心留空心), 单位为极坐标比例
GAP_DEG = 12.0
R_INNER = 0.18
LABEL_PAD = 1.06  # 样本名放置半径 = 外径 × 1.06


def _demo_data() -> tuple[np.ndarray, list[str], list[str]]:
    """内置 demo: 12 样本 × 5 指标(固定种子, 各列分布形态刻意不同)。"""
    rng = np.random.default_rng(20240901)
    n_samples, n_metrics = 12, 5
    base = rng.random((n_samples, n_metrics))
    # 给不同指标注入结构性差异: 指标 0 随样本序线性升, 指标 3 波动, 其余随机
    base[:, 0] = np.linspace(0.15, 0.95, n_samples) + rng.normal(0, 0.05, n_samples)
    base[:, 3] = 0.5 + 0.35 * np.sin(np.linspace(0, 3 * np.pi, n_samples)) \
        + rng.normal(0, 0.07, n_samples)
    values = np.clip(base, 0.0, 1.0)
    samples = [f"S{i + 1:02d}" for i in range(n_samples)]
    metrics = ["精度", "效率", "稳健", "泛化", "经济"]
    return values, samples, metrics


def plot_circular_heatmap(
    values: np.ndarray,
    sample_names: list[str],
    metric_names: list[str],
    title: str | None = None,
    out_prefix: str | None = None,
) -> list[str]:
    """绘制环形热图并三格式导出, 返回写出路径列表。

    Args:
        values: N×M 数值矩阵(行=样本, 列=指标), 列内 min-max 归一化后上色。
        sample_names: N 个样本名(外圈标签)。
        metric_names: M 个指标名(内→外环, 圆外右侧行标签)。
        title: 已弃用（1.4.1 图题纪律: 图名放论文 caption, 不入图内）;
            保留参数仅为兼容旧调用, 不再渲染。
        out_prefix: 输出前缀(不带扩展名); None 时写系统临时目录。

    Raises:
        ValueError: 矩阵非二维/行列数与名字数不齐/元素非有限。
    """
    values = np.asarray(values, dtype=float)
    if values.ndim != 2:
        raise ValueError(f"values 须为 N×M 二维数组, 实际维度: {values.ndim}")
    n_samples, n_metrics = values.shape
    if n_samples < 3 or n_metrics < 2:
        raise ValueError(f"至少 3 样本 × 2 指标, 实际: {n_samples}×{n_metrics}")
    if len(sample_names) != n_samples:
        raise ValueError(f"sample_names 数 {len(sample_names)} 与样本数 {n_samples} 不齐")
    if len(metric_names) != n_metrics:
        raise ValueError(f"metric_names 数 {len(metric_names)} 与指标数 {n_metrics} 不齐")
    if not np.all(np.isfinite(values)):
        raise ValueError("values 含非有限数值(NaN/inf)")

    apply_style()
    # 每列 min-max 归一化(全列相同值时归 0.5, 避免除零)
    span = values.max(axis=0) - values.min(axis=0)
    normed = np.where(span > 0,
                      (values - values.min(axis=0)) / np.where(span > 0, span, 1.0),
                      0.5)
    cmap = plt.get_cmap(get_cmap("sequential"))

    fig = plt.figure(figsize=FIGSIZE["square"])
    ax = fig.add_subplot(projection="polar")
    fig.subplots_adjust(left=0.12, right=0.78, top=0.88, bottom=0.10)
    ax.set_axis_off()  # 极轴刻度全部隐藏, 标签全部自绘

    # 扇区角度: 去掉 12° 标签缺口后的圆周均分, 缺口中心放在 0°(3 点钟方向)
    theta_edges = np.linspace(-GAP_DEG / 2, 360.0 - GAP_DEG / 2, n_samples + 1)
    sector_deg = 360.0 / n_samples
    centers_deg = (theta_edges[:-1] + theta_edges[1:]) / 2.0
    centers_rad = np.radians(centers_deg)

    # 色块: pcolormesh 一次性铺 N×M 环形网格(白细缝分隔; QuadMesh 不进
    # ax.patches, 与 imshow 数值标注同属像素级 QA 的既有豁免口径)
    r_edges = R_INNER + (1.0 - R_INNER) / n_metrics * np.arange(n_metrics + 1)
    ax.pcolormesh(np.radians(theta_edges), r_edges, normed.T, cmap=cmap,
                  edgecolors=load_neutral("white"), linewidth=0.6,
                  shading="flat", zorder=3)

    # 外圈样本名: 沿径向竖排且永远正立(右半圆 rotation=deg−90, 左半圆 +90)
    for deg, rad, name in zip(centers_deg, centers_rad, sample_names):
        if 0 < deg < 180:
            rotation, ha = deg - 90.0, "left"
        else:
            rotation, ha = deg + 90.0, "right"
        ax.text(rad, LABEL_PAD, name, ha=ha, va="center", rotation=rotation,
                rotation_mode="anchor", fontsize=8.5,
                color=load_neutral("secondary"))

    # 色标: figure 级 colorbar 放右侧
    sm = ScalarMappable(norm=Normalize(0.0, 1.0), cmap=cmap)
    cbar = fig.colorbar(sm, ax=ax, pad=0.14, fraction=0.05)
    cbar.set_label("归一化得分", fontsize=9)
    cbar.ax.tick_params(labelsize=8)
    cbar.outline.set_edgecolor(load_neutral("edge"))

    # 1.4.1 图题纪律: 图名与结论写进论文 caption, 不烘焙进图内

    # 指标名: 以"径向内→外"顺序一行文字放在图下方居中(axes 坐标文本,
    # 受 figqa 碰撞检测监督; 位于最下方样本标签与画布底边之间的空带)
    ax.text(0.5, -0.09, "径向内 → 外：" + " · ".join(metric_names),
            transform=ax.transAxes, ha="center", va="top", fontsize=9,
            color=load_neutral("ink"))

    if out_prefix is None:
        out_prefix = str(Path(tempfile.gettempdir()) / "mathmodel-figs"
                         / "make_circular_heatmap")
    return save_fig(fig, out_prefix)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="生成环形热图（12 样本 × 5 指标, 示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    out = args.out or str(
        Path(tempfile.gettempdir()) / "mathmodel-figs" / "make_circular_heatmap")
    values, samples, metrics = _demo_data()
    try:
        written = plot_circular_heatmap(values, samples, metrics, out_prefix=out)
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
