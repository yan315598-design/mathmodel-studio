# -*- coding: utf-8 -*-
"""draw.io 三栏研究框架图（drawio 模板包 · framework, 1.3.1 语义槽位版）。

与 matplotlib 版 make_diagram_framework_3col.py 同信息架构, 用 drawio
语言重写: 三栏"子问题 → 方法模型 → 结果产出", 栏头实色标题条
（族 header 底 + header_stroke 描边 + 白色加粗字）, 三栏分别绑定
blue/orange/teal 色族, 2-4 行映射。1.3.1 起升级为语义槽位版式:

  - 内容卡 = rich_card 两段式: **bold 标题行** + regular 明细行
    （note 档 9px 次级色, 单元格级不加粗, 密度来自内容结构）;
  - 每行左侧挂圈号徽章（椭圆徽章, blue 族 chevron 浅底）;
  - 行内栏间正交右行连线降重（1.3）, 发起栏族 edge 色。

输出 .drawio, draw.io 桌面版/网页版打开即编辑。落盘后 finalize()
自动跑 drawio_check.py 版式门禁（FAIL 即退出码 1）。

用法:
    python make_drawio_framework.py --out 输出前缀 [--palette academic_blue]
        [--rows 3]
    不给 --out 时示例图写入系统临时目录, 产出 <前缀>.drawio。

退出码: 0 成功; 1 版式门禁 FAIL; 2 参数/数据错误。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from drawio_builder import (  # noqa: E402
    DIAGRAM_FONT_RAMP, Diagram, base_parser, finalize, fit_text,
    get_diagram_families, get_palette, label_html, wrap_text_balanced,
)

# 示例数据 1.3.1: 每行 ((问标题, 问明细), (法标题, 法明细), (果标题, 果明细))
# 明细行写"参数/口径/产出形式", 是信息密度的主要来源——换成你的真实内容
COLUMN_NAMES = ["子问题", "方法模型", "结果产出"]
COLUMN_FAMILIES = ["blue", "orange", "teal"]   # 三栏绑定的示意图色族
DEMO_ROWS = [
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
PLACEHOLDER_ROW = (("（双击编辑: 补充子问题）", ""),
                   ("（双击编辑: 补充方法模型）", ""),
                   ("（双击编辑: 补充结果产出）", ""))
ROW_NUMS = "①②③④"

# 页面几何（px, y 向下; 页边距 >= 40, 坐标全部对齐 4px 网格）
CANVAS_W = 1220.0
ML = 40.0
BADGE_CX = 24.0          # 行圈号徽章中心 x（左页边区内）
COL_X0 = 64.0            # 三栏区左边界
LANE_W = 40.0            # 栏间连线通道宽
CHIP_H = 44.0            # 栏头横条高
TITLE_ZONE = 84.0
HEADER_GAP = 28.0
ROW_GAP = 24.0
BOTTOM_PAD = 44.0
CARD_MIN_H = 64.0
BODY_FS, NOTE_FS = DIAGRAM_FONT_RAMP["body"], DIAGRAM_FONT_RAMP["note"]
HEADER_FS, HEADER_FS_MIN = 13.5, 10.0
TEXT_PAD = 14.0


def _rich_card_h(title: str, detail: str, max_w: float) -> float:
    """按内容估算两段式卡高: 标题行 + 明细行 + 块间 4px + 上下 14px。"""
    t_lines = wrap_text_balanced(title, max_w, BODY_FS)
    h = len(t_lines) * BODY_FS * 1.5
    if detail.strip():
        d_lines = wrap_text_balanced(detail, max_w, NOTE_FS)
        h += 4.0 + len(d_lines) * NOTE_FS * 1.5
    return max(h + 14.0, CARD_MIN_H)


def build_framework(rows, palette: str = "academic_blue",
                    title_text: str = "研究框架图") -> Diagram:
    """构建三栏研究框架图的 Diagram（不落盘）。

    Args:
        rows: 2-4 条; 每条三个单元格 (标题, 明细) 二元组。
        palette: 色板名（保留兼容; 仅校验合法名, 栏色由色族接管）。
        title_text: 图标题。

    Raises:
        ValueError: 行数/行结构/空标题不合法, 或色板名未知。
    """
    if not 2 <= len(rows) <= 4:
        raise ValueError(f"三栏研究框架图需要 2-4 行映射, 实际 {len(rows)} 行")
    for r, row in enumerate(rows):
        if len(row) != 3:
            raise ValueError(f"rows 第 {r + 1} 行必须是三个单元格, 实际: {row!r}")
        for cell in row:
            if len(cell) != 2 or not str(cell[0]).strip():
                raise ValueError(f"第 {r + 1} 行单元格须为 (标题, 明细), "
                                 f"实际: {cell!r}")

    get_palette(palette)   # 兼容校验: --palette 仍须是已注册色板名
    fams = get_diagram_families(COLUMN_FAMILIES, 3)   # blue/orange/teal 三族
    warnings: list[str] = []
    col_w = (CANVAS_W - COL_X0 - ML - 2 * LANE_W) / 3
    col_x = [COL_X0 + i * (col_w + LANE_W) for i in range(3)]
    max_text_w = col_w - 2 * TEXT_PAD

    # 逐行预估卡高（行高随内容自适应）, 再反推页面总高
    row_heights: list[float] = []
    for row in rows:
        row_heights.append(max(_rich_card_h(t, det, max_text_w)
                               for t, det in row))
    canvas_h = (TITLE_ZONE + CHIP_H + HEADER_GAP + sum(row_heights)
                + (len(rows) - 1) * ROW_GAP + BOTTOM_PAD)

    d = Diagram(page_width=CANVAS_W, page_height=canvas_h, name="研究框架图")
    d.title("title", title_text, 40, 22, CANVAS_W - 80, 34)

    # 1) 栏头横条（实色标题条: 族 header 底 + header_stroke 描边 + 白色加粗字）
    header_y = TITLE_ZONE
    for c, name in enumerate(COLUMN_NAMES):
        lines, fs = fit_text(name, col_w - 2 * 12.0, HEADER_FS, HEADER_FS_MIN,
                             max_lines=1, ctx=f"栏头 {name!r}",
                             warnings=warnings)
        d.header_bar(f"col{c + 1}_header", label_html(lines),
                     col_x[c], header_y, col_w, CHIP_H, family=fams[c],
                     font_size=fs)

    # 2) 各行: 圈号徽章 + 两段式富文本卡 + 行内右行连线
    cursor = header_y + CHIP_H + HEADER_GAP
    for r in range(len(rows)):
        h = row_heights[r]
        d.badge(f"row{r + 1}_num", ROW_NUMS[r], BADGE_CX - 14,
                cursor + h / 2 - 14, 28, 28, shape="ellipse",
                family=fams[0], font_size=NOTE_FS)
        for c in range(3):
            t, det = rows[r][c]
            d.rich_card(f"row{r + 1}_col{c + 1}", t, det,
                        col_x[c], cursor, col_w, h, family=fams[c])
        for c in range(2):
            d.edge(f"row{r + 1}_col{c + 1}", f"row{r + 1}_col{c + 2}",
                   exit_dir="right", entry_dir="left", stroke=fams[c]["edge"])
        cursor += h + ROW_GAP
    for w in warnings:
        print(f"[警告] {w}")
    return d


def main(argv: list[str] | None = None) -> int:
    parser: argparse.ArgumentParser = base_parser(
        "生成 draw.io 三栏研究框架图（示例数据, 输出可编辑 .drawio）")
    parser.add_argument("--rows", type=int, default=3, metavar="N",
                        help="映射行数, 2-4, 默认 3（超出示例部分用占位行）")
    args = parser.parse_args(argv)
    if not 2 <= args.rows <= 4:
        print(f"[参数错误] --rows 需在 2..4 之间, 实际 {args.rows}")
        return 2
    rows = DEMO_ROWS[:args.rows]
    while len(rows) < args.rows:
        rows.append(PLACEHOLDER_ROW)
    try:
        diagram = build_framework(rows, palette=args.palette)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    return finalize(diagram, args.out, "make_drawio_framework")


if __name__ == "__main__":
    sys.exit(main())
