# -*- coding: utf-8 -*-
"""三栏研究框架图（示意图模板包 · framework, 1.3.1 语义槽位重写版）。

三栏结构: 左栏"子问题"、中栏"方法模型"、右栏"结果产出"; 每行构成一条
"问题→方法→结果"映射链, 行内栏间画横向箭头串联。1.3.1 起升级为
语义槽位版式（追平 sci-box framework-3col 的信息架构）:

  - 内容卡 = 两段式富文本卡 rich_box: **bold 标题行**（问题/方法/结果名）
    + regular 明细行（参数/口径/产出形式, note 档次级色）;
  - 每行左侧挂圈号徽章 num_badge（行索引, 族 chevron 浅底）;
  - 栏标题保持实色标题条（族 header 底白字, 结构件加粗）;
  - 行内映射箭头降重（lw 1.3 / 小箭头头）, 发起栏族 edge 色。

三栏分别绑定 blue/orange/teal 三族（DIAGRAM_FAMILIES）。支持 2-4 行映射。
数据模型: ROWS = [((问标题, 问明细), (法标题, 法明细), (果标题, 果明细)), ...];
单元格兼容纯字符串（视为只有标题）。向后兼容 1.2.0 纯字符串三元组调用。

确定性布局: 画布逻辑坐标 = 像素（dpi=100）, 中文字宽估算均衡换行,
行高由各行实际换行结果动态计算, 不依赖任何 GUI/字体测量, 输出可复现。
文字过长自动缩字号（明细先于标题）, 仍放不下打印 [警告] 不静默裁字。

用法（二选一）:
    1. 独立运行:
       python make_diagram_framework_3col.py [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 ROWS / COLUMNS 数据。

版本:
    1.3.1: 语义槽位重写——两段式富文本卡/行圈号徽章, 字重回层级制
        （栏头与徽章加粗, 卡内明细常规）, 连线降重。
    1.2.0: 迁移示意图色族体系; 1.1.0: 迁移 figkit + 三格式导出。

质量门:
    python scripts/figqa.py templates/figures/scripts/diagrams/make_diagram_framework_3col.py \\
        --strict --allow-box-labels   （盒内标签为有意版式）

退出码: 0 成功; 2 参数/数据错误。
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "mathmodel-mplconfig")
)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

# ---- 头部统一走共享库 figkit（样式/色族/卡片/标题条/连接器/结构化零件）----
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    DIAGRAM_LINE_PITCH,
    apply_style,
    diagram_header,
    elbow_arrow,
    load_diagram_families,
    load_diagram_page,
    num_badge,
    rich_box,
    save_fig,
    use_diagram_font,
    wrap_text_balanced,
)

# 示例数据 1.3.1: 每行 ((问标题, 问明细), (法标题, 法明细), (果标题, 果明细))
# 明细行写"参数/口径/产出形式", 是信息密度的主要来源——换成你的真实内容
COLUMNS: list[tuple[str, str]] = [
    ("子问题", "#1F4E79"),
    ("方法模型", "#2E86AB"),
    ("结果产出", "#3B8C6E"),
]
COLUMN_FAMILIES = ["blue", "orange", "teal"]   # 三栏绑定的示意图色族
ROWS = [
    (("指标体系如何构建？", "关键环节刻画 · 指标可量化"),
     ("CRITIC-熵权组合赋权", "客观赋权 · 组合修正"),
     ("指标权重表", "量化口径 · 权重向量")),
    (("多目标冲突如何寻优？", "供水 · 发电 · 生态"),
     ("多目标规划 + NSGA-II", "非支配排序 · 精英保留"),
     ("Pareto 前沿", "折中方案推荐")),
    (("方案稳健性如何？", "参数扰动 ±10%"),
     ("Sobol 全局灵敏度分析", "多情景交叉对比"),
     ("灵敏度排序", "稳健性结论")),
]

# 画布逻辑坐标 = 像素（dpi=100）; matplotlib 字号以 pt 计, 1pt = 100/72 px
CANVAS_W = 1220.0
TITLE_FS = 16.0
TEXT_PAD = 14.0
ROW_GAP = 26.0
CARD_MIN_H = 64.0
CHIP_H = 44.0
BODY_FS, NOTE_FS = 10.5, 9.0
ROW_NUMS = "①②③④"


def _normalize_cell(cell) -> tuple[str, str]:
    """单元格归一化: 纯字符串 → (标题, ""); 二元组 → (标题, 明细)。"""
    if isinstance(cell, str):
        if not cell.strip():
            raise ValueError("存在空单元格内容")
        return cell, ""
    if len(cell) != 2 or not str(cell[0]).strip():
        raise ValueError(f"单元格须为 (标题, 明细), 实际: {cell!r}")
    return str(cell[0]), str(cell[1])


def _est_card_h(title: str, detail: str, max_w: float) -> float:
    """按内容估算两段式卡高: 标题行 + 明细行 + 块间 4px + 上下 12px。"""
    t_lines = wrap_text_balanced(title, max_w, BODY_FS)
    h = len(t_lines) * BODY_FS * DIAGRAM_LINE_PITCH
    if detail.strip():
        d_lines = wrap_text_balanced(detail, max_w, NOTE_FS)
        h += 4.0 + len(d_lines) * NOTE_FS * DIAGRAM_LINE_PITCH
    return max(h + 16.0, CARD_MIN_H)


def plot_framework(rows, columns=None, out_stem: str | None = None,
                   title: str = "研究框架图") -> tuple[Path, Path]:
    """绘制三栏研究框架图并保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        rows: 2-4 条; 每条三个单元格, 单元格为 (标题, 明细) 或纯字符串。
        columns: 3 条 (栏标题, 强调色); None 时用模块级 COLUMNS 默认。
            栏色由 COLUMN_FAMILIES（blue/orange/teal）接管, 第二元忽略
            （保留参数形状向后兼容）。
        out_stem: 输出文件前缀; None 时写系统临时目录。
        title: 图标题。

    Raises:
        ValueError: rows 行数不在 [2,4] / 行不是三格 / 有空标题 / columns 非法。
    """
    cols = columns if columns is not None else COLUMNS
    if not 2 <= len(rows) <= 4:
        raise ValueError(f"三栏研究框架图需要 2-4 行映射, 实际 {len(rows)} 行")
    norm_rows = []
    for row in rows:
        if len(row) != 3:
            raise ValueError(f"rows 每条必须是三个单元格, 实际: {row!r}")
        norm_rows.append(tuple(_normalize_cell(cell) for cell in row))
    if len(cols) != 3:
        raise ValueError(f"columns 需要恰好 3 栏 (栏标题, 强调色), 实际 {len(cols)}")
    for name, _color in cols:
        if not str(name).strip():
            raise ValueError("columns 存在空栏标题")

    apply_style()
    use_diagram_font()
    fams = load_diagram_families(order=COLUMN_FAMILIES, n=3)
    ink = load_diagram_page("ink")

    # 横向几何: 左圈号徽章区 + 三栏等宽 + 栏间箭头通道
    ML = 40.0
    BADGE_CX = 24.0
    col_x0 = 64.0
    lane_w = 40.0
    col_w = (CANVAS_W - col_x0 - ML - 2 * lane_w) / 3
    col_x = [col_x0 + i * (col_w + lane_w) for i in range(3)]
    max_text_w = col_w - 2 * TEXT_PAD

    # 纵向几何: 逐行预估卡高（行高随内容自适应）, 再反推画布总高
    row_heights = []
    for row in norm_rows:
        row_heights.append(max(_est_card_h(t, d, max_text_w) for t, d in row))

    top_zone = 64.0 + CHIP_H + 30.0          # 标题区 + 栏头条 + 栏头下空隙
    CANVAS_H = top_zone + sum(row_heights) + (len(rows) - 1) * ROW_GAP + 30.0
    title_y = CANVAS_H - 32
    header_top = CANVAS_H - 64.0

    fig = plt.figure(figsize=(CANVAS_W / 100.0, CANVAS_H / 100.0), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CANVAS_W)
    ax.set_ylim(0, CANVAS_H)
    ax.axis("off")
    ax.text(CANVAS_W / 2, title_y, title, ha="center", va="center",
            fontsize=TITLE_FS, fontweight="bold", color=ink)

    # 1) 栏标题实色条（族 header 底白字, diagram_header）
    for c, (name, _color) in enumerate(cols):
        diagram_header(ax, col_x[c], header_top, col_w, CHIP_H, name, fams[c])

    # 2) 各行: 圈号徽章 + 两段式内容卡 + 行内栏间箭头
    cursor = header_top - CHIP_H - 26.0
    for r in range(len(norm_rows)):
        h = row_heights[r]
        cy = cursor - h / 2
        num_badge(ax, BADGE_CX, cy, 14.0, ROW_NUMS[r], fams[0], fontsize=10.5)
        for c in range(3):
            t, det = norm_rows[r][c]
            rich_box(ax, col_x[c], cursor, col_w, h, t, det, fams[c])
        for c in range(2):
            # 同 y 端点下 hv 拐角与终点重合, rad 置 0 避免 AngleRad 除零告警
            elbow_arrow(ax, (col_x[c] + col_w, cy), (col_x[c + 1], cy),
                        color=fams[c]["edge"], direction="hv", rad=0.0)
        cursor -= h + ROW_GAP

    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / "make_diagram_framework_3col")
    written = [Path(p) for p in save_fig(fig, out_stem)]
    return written[0], written[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成三栏研究框架图（示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    try:
        png, svg = plot_framework(ROWS, out_stem=args.out)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    print(f"已输出: {png}")
    print(f"已输出: {svg}")
    print(f"已输出: {png.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
