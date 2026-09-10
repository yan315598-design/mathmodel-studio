# -*- coding: utf-8 -*-
"""美化混淆矩阵模板: 计数 + 行归一化百分比双行标注, 召回率色标。

色块按行归一化值(召回率)映射 get_cmap("confusion_matrix")(Blues),
格内双行显示"计数 / (行百分比)", 文字黑白按背景亮度自适应
(W3C 相对亮度 0.299R+0.587G+0.114B 阈值 0.55); 右侧 colorbar 标"召回率"。
图名与总体准确率等结论按 1.4.1 图题纪律写进论文 caption, 不入图内。

用法（二选一）:
    1. 独立运行:
       python make_confusion_matrix.py [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录 mathmodel-figs/ 下,
       产出 300dpi PNG + SVG + PDF 三格式。
    2. 复制到项目后改 _demo_data() 与 plot_confusion_matrix() 入参。

输入说明:
    matrix: N×N 计数矩阵(非负整数), 行=真实类别, 列=预测类别。

figqa: 本模板按纯 --strict 通过(imshow 数值标注属 figqa 既有豁免口径)。

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
    get_cmap,
    load_neutral,
    save_fig,
)

# figqa 硬门脚本: templates/figures/scripts/templates/ → skill 根下 scripts/
FIGQA_SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "figqa.py"

# 文字黑白自适应亮度阈值(0~1, W3C 加权亮度高于此用深字, 低于用白字)
LUMA_THRESHOLD = 0.55


def _demo_data() -> tuple[np.ndarray, list[str]]:
    """内置 demo: 4 分类病情分级, 真实先验递减 + 相邻类混淆(固定种子)。"""
    rng = np.random.default_rng(20240901)
    classes = ["健康", "轻度", "中度", "重度"]
    prior = np.array([0.40, 0.30, 0.20, 0.10])
    n = 400
    y_true = rng.choice(4, size=n, p=prior)
    # 预测 = 真实类为主, 向相邻类泄漏(病情分级典型误差结构)
    leak = np.array([
        [0.84, 0.12, 0.03, 0.01],   # 健康
        [0.14, 0.71, 0.12, 0.03],   # 轻度
        [0.04, 0.16, 0.66, 0.14],   # 中度
        [0.01, 0.04, 0.18, 0.77],   # 重度
    ])
    matrix = np.zeros((4, 4), dtype=int)
    for t in y_true:
        matrix[t, rng.choice(4, p=leak[t])] += 1
    return matrix, classes


def _text_color_for(rgba: tuple) -> str:
    """按色块背景亮度选文字色: 亮底用 ink 深字, 暗底用白字。"""
    r, g, b = rgba[:3]
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    return load_neutral("ink") if luma > LUMA_THRESHOLD else "white"


def plot_confusion_matrix(
    matrix: np.ndarray,
    class_names: list[str],
    title: str | None = None,
    out_prefix: str | None = None,
) -> list[str]:
    """绘制美化混淆矩阵并三格式导出, 返回写出路径列表。

    Args:
        matrix: N×N 非负整数计数矩阵(行=真实, 列=预测)。
        class_names: N 个类别名(轴刻度)。
        title: 已弃用（1.4.1 图题纪律: 图名放论文 caption, 不入图内）;
            保留参数仅为兼容旧调用, 不再渲染; 总体准确率等结论也一并移出图内。
        out_prefix: 输出前缀(不带扩展名); None 时写系统临时目录。

    Raises:
        ValueError: 矩阵非方阵/形状与类别数不齐/含负数或非整数/全零。
    """
    matrix = np.asarray(matrix)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"matrix 须为 N×N 方阵, 实际: {matrix.shape}")
    n = matrix.shape[0]
    if len(class_names) != n:
        raise ValueError(f"class_names 数 {len(class_names)} 与类别数 {n} 不齐")
    # 有限性先于整型校验: inf 会伪装成"整数"通过 floor 比较后在下游爆 OverflowError
    if not np.all(np.isfinite(matrix)):
        raise ValueError("matrix 含非有限值(NaN/inf), 须为非负整数计数")
    if matrix.sum() <= 0:
        raise ValueError("matrix 全零, 无法计算归一化与准确率")
    if np.any(matrix < 0) or not np.all(matrix == np.floor(matrix)):
        raise ValueError("matrix 须为非负整数计数")

    apply_style()
    accuracy = float(np.trace(matrix)) / float(matrix.sum())
    row_sums = matrix.sum(axis=1, keepdims=True)
    recall_norm = matrix / np.where(row_sums > 0, row_sums, 1.0)  # 行归一化(召回率)
    cmap = plt.get_cmap(get_cmap("confusion_matrix"))

    fig, ax = plt.subplots(figsize=FIGSIZE["square"])
    fig.subplots_adjust(left=0.17, right=0.86, top=0.83, bottom=0.12)
    im = ax.imshow(recall_norm, cmap=cmap, vmin=0.0, vmax=1.0)

    # 格内双行标注: 计数 + 行百分比; 黑白字按背景亮度自适应
    for i in range(n):
        for j in range(n):
            color = _text_color_for(cmap(recall_norm[i, j]))
            ax.text(j, i, f"{matrix[i, j]}\n({recall_norm[i, j]:.1%})",
                    ha="center", va="center", fontsize=9, color=color,
                    linespacing=1.25)

    ax.set_xticks(range(n), class_names)
    ax.set_yticks(range(n), class_names)
    ax.set_xlabel("预测类别")
    ax.set_ylabel("真实类别")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)

    # 1.4.1 图题纪律: 图名与"总体准确率"等结论写进论文 caption, 不入图内

    cbar = fig.colorbar(im, ax=ax, shrink=0.82, pad=0.03)
    cbar.set_label("召回率（行归一化）", fontsize=9)
    cbar.ax.tick_params(labelsize=8)
    cbar.outline.set_edgecolor(load_neutral("edge"))

    if out_prefix is None:
        out_prefix = str(Path(tempfile.gettempdir()) / "mathmodel-figs"
                         / "make_confusion_matrix")
    return save_fig(fig, out_prefix)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="生成美化混淆矩阵（4 分类, 示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    out = args.out or str(
        Path(tempfile.gettempdir()) / "mathmodel-figs" / "make_confusion_matrix")
    matrix, classes = _demo_data()
    try:
        written = plot_confusion_matrix(matrix, classes, out_prefix=out)
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
