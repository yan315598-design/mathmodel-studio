# -*- coding: utf-8 -*-
"""和弦图模板: 部门/类别间流量迁移矩阵的 Circos 弦图(依赖 pycirclize)。

用 pycirclize 的 Circos.chord_diagram() 便捷入口: 扇区宽度=行列和,
弦(link)=非对角流量; 扇区与弦同色, 色值来自 figkit 色板循环取色,
部门名标签画在环外(r=110)竖排朝外。

用法（二选一）:
    1. 独立运行:
       python make_chord_diagram.py [--palette academic_blue] [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录 mathmodel-figs/ 下,
       产出 300dpi PNG + SVG + PDF 三格式。
    2. 复制到项目后改 DEMO_LABELS/DEMO_MATRIX 与 plot_chord() 入参。

输入说明:
    matrix: N×N 非负流量矩阵, 对角线(部门内部流转)也会画弦,
            demo 中刻意把对角占比压到 ~55% 突出跨部门迁移;
    labels: N 个部门名, 与行列顺序一致。

figqa: 本机无 pycirclize 时脚本以退出码 3 提前退出(figqa 会报
"执行失败", 属预期); 装库后建议按纯 --strict 跑一次确认布局。

退出码: 0 成功; 2 参数/IO 错误; 3 缺少 pycirclize 依赖。
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

# ---- 依赖守卫: pycirclize 缺失时友好提示并以退出码 3 结束 ----
try:
    from pycirclize import Circos
except ImportError:
    print("[依赖缺失] 请先 pip install pycirclize，"
          "本模板依赖 pycirclize 绘制和弦图")
    sys.exit(3)

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd

# figkit 位于本脚本上级目录 (scripts/), 注册后方可 from figkit import ...
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import apply_style, load_neutral, load_palette, save_fig

# figqa 硬门脚本: templates/figures/scripts/templates/ → skill 根下 scripts/
FIGQA_SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "figqa.py"

# demo: 6 部门年度人才迁移矩阵(行=迁出部门, 列=迁入部门, 对角=内部流转)
DEMO_LABELS = ["研发", "生产", "市场", "销售", "人力", "财务"]


def _demo_matrix(seed: int = 20240901) -> np.ndarray:
    """内置 demo 流量矩阵: 对角占 ~55%, 非对角随机不对称迁移。"""
    rng = np.random.default_rng(seed)
    n = len(DEMO_LABELS)
    total = rng.integers(30, 90, size=(n, n))
    np.fill_diagonal(total, 0)
    diag = total.sum(axis=1) * 0.55 + rng.integers(10, 30, size=n)
    np.fill_diagonal(total, diag)
    return total.astype(int)


def plot_chord(
    matrix: np.ndarray,
    labels: list[str],
    palette: str = "academic_blue",
    title: str | None = None,
    out_prefix: str | None = None,
) -> list[str]:
    """绘制和弦图并三格式导出, 返回写出路径列表。

    Args:
        matrix: N×N 非负流量矩阵(行=迁出, 列=迁入)。
        labels: N 个部门名(扇区标签, 与行列顺序一致)。
        palette: 色板名, 扇区/弦色按顺序循环取色。
        title: 已弃用（1.4.1 图题纪律: 图名放论文 caption, 不入图内）;
            保留参数仅为兼容旧调用, 不再渲染。
        out_prefix: 输出前缀(不带扩展名); None 时写系统临时目录。

    Raises:
        ValueError: matrix 非方阵/含负值/行列数与 labels 不齐。
    """
    matrix = np.asarray(matrix)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"matrix 须为 N×N 方阵, 实际: {matrix.shape}")
    n = matrix.shape[0]
    if len(labels) != n:
        raise ValueError(f"labels 数 {len(labels)} 与矩阵阶数 {n} 不齐")
    if np.any(matrix < 0):
        raise ValueError("matrix 须为非负流量矩阵")
    apply_style()
    colors = load_palette(palette)
    # 部门数可能超过色板长度, 循环取色
    color_map = {label: colors[i % len(colors)] for i, label in enumerate(labels)}

    # DataFrame 携带行列名, 新版 chord_diagram 以此命名扇区;
    # 旧版签名(data=..., labels=...) 以 TypeError 兜底回退
    frame = pd.DataFrame(matrix, index=labels, columns=labels)
    label_kws = dict(r=110, orientation="vertical", size=11,
                     color=load_neutral("ink"))
    link_kws = dict(direction=1, ec=load_neutral("white"), lw=0.3, alpha=0.75)
    try:
        circos = Circos.chord_diagram(matrix=frame, cmap=color_map,
                                      label_kws=label_kws, link_kws=link_kws)
    except TypeError:
        circos = Circos.chord_diagram(data=matrix, labels=labels)

    fig = circos.plotfig(figsize=(7.2, 7.2))
    # 1.4.1 图题纪律: 图名与结论写进论文 caption, 不烘焙进图内
    if out_prefix is None:
        out_prefix = str(Path(tempfile.gettempdir()) / "mathmodel-figs"
                         / "make_chord_diagram")
    return save_fig(fig, out_prefix)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="生成部门和弦图（6 部门迁移矩阵, 示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    parser.add_argument("--palette", default="academic_blue",
                        help="色板名（默认 academic_blue）")
    args = parser.parse_args(argv)
    out = args.out or str(
        Path(tempfile.gettempdir()) / "mathmodel-figs" / "make_chord_diagram")
    try:
        written = plot_chord(_demo_matrix(), DEMO_LABELS,
                             palette=args.palette, out_prefix=out)
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
