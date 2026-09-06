# -*- coding: utf-8 -*-
"""相关性 / 灵敏度矩阵热力图模板: RdBu_r 发散色, 0 居中对称色标。

格内数值按背景亮度自动选黑/白字, 可选显著性星号（* p<0.05, ** p<0.01）,
方阵与非方阵输入均支持; 指标名过长时列标签自动倾斜防压叠。

用法（二选一）:
    1. 独立运行:
       python make_correlation_heatmap.py [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录（gitignore 友好）, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 CORR_MATRIX/ROW_NAMES/COL_NAMES 与 plot_heatmap() 入参。

约定:
    - 1.1.0: 迁移 figkit + 三格式导出 + 中性色令牌。
    - 样式与色板统一经 scripts/figkit.py 加载（mathmodel.mplstyle + palettes.py,
      两者缺失时 figkit 内置等价内联回退）; 发散色取 figkit.get_cmap("correlation"),
      使用时保持 0 居中对称色标。

输入说明:
    matrix: 二维数值矩阵（list[list[float]] / numpy 数组）, 行列均可非等长;
            数值任意有限实数, 色标按 |值| 最大值对称居中（0 为中间色）。
    pvalues: 与 matrix 同形的显著性 p 值矩阵; 仅在存在时叠加星号。

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

# ---- 1.1.0: 头部统一走共享库 figkit（样式/色板/导出/colormap 语义）----
# figkit.py 位于本脚本上二级 scripts/ 目录; 色板回退已内置于 figkit, 不再保留本文件副本
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    apply_style,
    get_cmap,
    load_neutral,
    save_fig,
)

# 示例数据: 六项物流指标相关系数矩阵（方阵, 行名=列名）
CORR_MATRIX: list[list[float]] = [
    [1.000, 0.512, -0.683, 0.724, 0.638, -0.152],
    [0.512, 1.000, -0.471, 0.498, 0.421, -0.087],
    [-0.683, -0.471, 1.000, -0.604, -0.558, 0.204],
    [0.724, 0.498, -0.604, 1.000, 0.697, -0.119],
    [0.638, 0.421, -0.558, 0.697, 1.000, -0.135],
    [-0.152, -0.087, 0.204, -0.119, -0.135, 1.000],
]
ROW_NAMES = ["运输成本", "运输时效", "准时率", "碳排放", "服务满意度", "信息化水平"]
COL_NAMES = ROW_NAMES
# 演示用显著性标记: 对角线恒 1 无检验意义用 nan 排除星号
PVALUES: list[list[float | None]] = [
    [None, 0.021, 0.001, 0.003, 0.012, 0.499],
    [0.021, None, 0.033, 0.026, 0.048, 0.702],
    [0.001, 0.033, None, 0.006, 0.009, 0.374],
    [0.003, 0.026, 0.006, None, 0.001, 0.603],
    [0.012, 0.048, 0.009, 0.001, None, 0.552],
    [0.499, 0.702, 0.374, 0.603, 0.552, None],
]


def _luminance(hex_color: str) -> float:
    """hex 色值的感知灰阶 (0~255): 0.299R+0.587G+0.114B, 用于选黑/白前景字。"""
    text = hex_color.strip().lstrip("#")
    r = int(text[0:2], 16)
    g = int(text[2:4], 16)
    b = int(text[4:6], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def plot_heatmap(
    matrix,
    row_names: list[str] | None = None,
    col_names: list[str] | None = None,
    pvalues: list[list] | None = None,
    value_label: str = "相关系数",
    title: str | None = None,
    annotate: bool = True,
    digits: int = 2,
    out_stem: str | None = None,
) -> tuple[Path, Path]:
    """绘制发散色热力图并保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        matrix: 二维数值矩阵（任意行列数）; 转成 float 数组并检查有限性。
        row_names/col_names: 行列指标名, 长度须分别等于矩阵行/列数。
        pvalues: 与 matrix 同形的显著性 p 值矩阵; None 时不标注星号。
        value_label: 色标轴名（相关矩阵建议 "相关系数"）。
        title: 图标题; None 时用默认标题。
        annotate: 是否在格内标注数值。
        digits: 数值小数位。
        out_stem: 输出文件前缀; None 时写系统临时目录。

    Raises:
        ValueError: 矩阵为空/非矩形/含非有限值; 名称长度不齐; pvalues 形状或
            取值非法（须为 (0,1] 或 None/NaN）。
    """
    import numpy as np

    arr = np.asarray(matrix, dtype=float)
    if arr.ndim != 2 or arr.shape[0] == 0 or arr.shape[1] == 0:
        raise ValueError(f"matrix 必须是非空二维矩阵, 实际 shape: {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("matrix 含非有限数值(NaN/inf)")
    rows, cols = arr.shape
    if row_names is None:
        row_names = [f"指标 {i + 1}" for i in range(rows)]
    if col_names is None:
        col_names = [f"指标 {j + 1}" for j in range(cols)]
    if len(row_names) != rows or len(col_names) != cols:
        raise ValueError(
            f"名称长度与矩阵不齐: 行名 {len(row_names)} vs {rows} 行, "
            f"列名 {len(col_names)} vs {cols} 列"
        )
    if any(not str(n).strip() for n in list(row_names) + list(col_names)):
        raise ValueError("row_names/col_names 含空名称")
    if not (0 <= digits <= 4):
        raise ValueError(f"digits 需在 [0, 4], 实际: {digits}")

    if pvalues is not None:
        p_arr = np.asarray(pvalues, dtype=float)
        if p_arr.shape != arr.shape:
            raise ValueError(
                f"pvalues 形状 {p_arr.shape} 与 matrix {arr.shape} 不一致"
            )
        valid = np.isnan(p_arr) | ((p_arr > 0.0) & (p_arr <= 1.0))
        if not np.all(valid):
            raise ValueError("pvalues 须为 (0, 1] 区间值（NaN 表示不检验, 不标星）")
    else:
        p_arr = np.full(arr.shape, np.nan)

    apply_style()
    vmax = float(np.max(np.abs(arr))) or 1.0

    # 画布按行列数比例分配, 保证格子在 300dpi 下有可读宽度
    fig_w = max(5.6, 1.9 + 0.72 * cols)
    fig_h = max(4.2, 1.6 + 0.56 * rows)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.subplots_adjust(left=0.14, right=0.80, top=0.92, bottom=0.13)
    ax.set_position([0.13, 0.14, 0.66, 0.76])

    im = ax.imshow(
        arr,
        cmap=get_cmap("correlation"),  # 1.1.0: 发散色经 figkit/palettes 语义出口
        vmin=-vmax,
        vmax=vmax,
        aspect="auto",
        interpolation="nearest",
    )
    # 热力图为特殊网格: 主网格线会压在色块上故弃用, 改白色次网格画格线
    # （数据图的 ygrid-only 惯例在此不适用, 保持 imshow 网格语义）
    ax.grid(False)

    # 格线（白色细线）与数值/星号标注
    ax.set_xticks(np.arange(cols) + 0.5, minor=True)
    ax.set_yticks(np.arange(rows) + 0.5, minor=True)
    ax.grid(True, which="minor", color="white", linewidth=1.4)
    ax.tick_params(which="minor", length=0)

    if annotate:
        for i in range(rows):
            for j in range(cols):
                bg = im.cmap(im.norm(arr[i, j]))
                fg = "white" if _luminance(matplotlib.colors.to_hex(bg)) < 150 else "black"
                star = ""
                p = p_arr[i, j]
                if np.isfinite(p):
                    star = "**" if p < 0.01 else ("*" if p < 0.05 else "")
                ax.text(j, i, f"{arr[i, j]:.{digits}f}{star}", ha="center",
                        va="center", color=fg, fontsize=8.5)

    ax.set_xticks(range(cols))
    ax.set_xticklabels(col_names, rotation=32 if any(len(str(c)) > 4 for c in col_names) else 0,
                       ha="right", rotation_mode="anchor")
    ax.set_yticks(range(rows))
    ax.set_yticklabels(row_names)
    ax.tick_params(top=False, bottom=True, left=True, right=False)

    cbar = fig.colorbar(im, ax=ax, fraction=0.030, pad=0.035)
    cbar.set_label(value_label)
    cbar.ax.tick_params(labelsize=9)
    ax.set_title(title or f"{value_label}热力图")

    # 显著性脚注: 只在提供 pvalues 时出现; 放画布左下角避开轴区
    if pvalues is not None:
        fig.text(0.13, 0.025, "显著性: ** p<0.01,  * p<0.05", fontsize=8.5,
                 color=load_neutral("secondary"))
    return _save(fig, out_stem, "make_correlation_heatmap")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """1.1.0 经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成相关性/灵敏度热力图（示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    try:
        png, svg = plot_heatmap(
            CORR_MATRIX, ROW_NAMES, COL_NAMES, pvalues=PVALUES, out_stem=args.out
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
