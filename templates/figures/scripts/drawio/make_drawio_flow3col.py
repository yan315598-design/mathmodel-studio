# -*- coding: utf-8 -*-
"""draw.io 多列阶段流程图（drawio 模板包 · flow3col, 默认三/四列泳道,
1.2.0 族化版）。

与 matplotlib 版 make_technical_route_flowchart.py 同信息架构, 用 drawio
语言重写: N 列阶段泳道（默认 4 列）, 列头实色标题条（族序取
DIAGRAM_ORDER_GENERIC, 族 header 底 + header_stroke 描边 + 白色加粗字）,
列内步骤族色浅底圆角卡片自上而下以正交连线推进（族 edge 色）, 列头之间
横向流转连线（左列族 edge 色）。输出 .drawio, draw.io 桌面版/网页版打开
即编辑。

确定性布局: 页面坐标原点左上、y 向下; 列宽/卡高由文字换行结果动态计算,
中文字宽估算均衡换行, 超宽自动缩字号（下限 8.5pt）, 仍放不下打印 [警告]。

用法:
    python make_drawio_flow3col.py --out 输出前缀 [--palette academic_blue]
        [--cols 4]
    不给 --out 时示例图写入系统临时目录, 产出 <前缀>.drawio。

退出码: 0 成功; 2 参数/数据错误。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from drawio_builder import (  # noqa: E402
    Diagram, base_parser, block_height, finalize, fit_text,
    get_diagram_families, get_palette, label_html,
)

# 示例数据: (阶段名, [该阶段步骤...]); 阶段自左向右流转, 步骤自上而下推进
DEMO_STAGES: list[tuple[str, list[str]]] = [
    ("问题分析", ["题目解读与数据勘察", "关键约束识别", "评价指标体系构建"]),
    ("模型建立", ["主规划模型（混合整数）", "碳约束与不确定性建模", "稳健性指标量化"]),
    ("求解与算法", ["分支定界精确求解", "自适应遗传算法", "蒙特卡洛场景模拟"]),
    ("结果与验证", ["灵敏度龙卷风分析", "多场景稳健性对比", "结论与方案建议"]),
]
_CN_NUMS = ["一", "二", "三", "四", "五", "六"]

# 页面几何（px, y 向下; 页边距 >= 40）
CANVAS_W = 1100.0
MARGIN = 40.0
COL_GAP = 56.0          # 列间通道（横向流转连线活动区）
BOX_GAP = 30.0          # 步骤卡间空隙（下行连线活动区）
HEADER_H = 44.0
TITLE_ZONE = 72.0
HEADER_GAP = 34.0
BOTTOM_PAD = 44.0
BOX_FS, BOX_FS_MIN = 10.5, 8.5
HEADER_FS, HEADER_FS_MIN = 13.0, 10.0
CARD_MIN_H = 44.0
TEXT_PAD = 14.0


def _demo_stages(cols: int) -> list[tuple[str, list[str]]]:
    """由 demo 数据推导指定列数的内容; 超出部分用可编辑占位。"""
    stages = DEMO_STAGES[:cols]
    for i in range(len(DEMO_STAGES), cols):
        cn = _CN_NUMS[i] if i < len(_CN_NUMS) else str(i + 1)
        stages.append((f"补充阶段{cn}", ["（双击编辑: 补充本阶段步骤）"]))
    return stages


def build_flow3col(stages: list[tuple[str, list[str]]],
                   palette: str = "academic_blue",
                   title_text: str = "技术路线流程图") -> Diagram:
    """构建多列阶段流程图的 Diagram（不落盘）。

    Args:
        stages: (阶段名, [步骤...]) 列表, 2-6 列, 阶段自左向右流转。
        palette: 色板名。
        title_text: 图标题。

    Raises:
        ValueError: 列数/行结构/空文本不合法, 或色板名未知。
    """
    if not 2 <= len(stages) <= 6:
        raise ValueError(f"阶段流程图需要 2-6 列, 实际 {len(stages)} 列")
    for i, stage in enumerate(stages):
        if len(stage) != 2:
            raise ValueError(f"stages 第 {i + 1} 项必须是 (阶段名, [步骤...]) "
                             f"二元组, 实际: {stage!r}")
        stage_name, steps = stage
        if not str(stage_name).strip():
            raise ValueError(f"第 {i + 1} 列阶段名为空")
        if not steps:
            raise ValueError(f"阶段 {stage_name!r} 的步骤列表为空")
        for step in steps:
            if not str(step).strip():
                raise ValueError(f"阶段 {stage_name!r} 存在空步骤描述")

    get_palette(palette)   # 兼容校验: --palette 仍须是已注册色板名
    fams = get_diagram_families(n=len(stages))   # DIAGRAM_ORDER_GENERIC 前 n 族
    warnings: list[str] = []
    n = len(stages)
    col_w = (CANVAS_W - 2 * MARGIN - (n - 1) * COL_GAP) / n
    col_x = [MARGIN + i * (col_w + COL_GAP) for i in range(n)]

    # 逐列逐步骤换行算卡高, 求各列总高
    col_lines: list[list[list[str]]] = []
    col_fs: list[list[float]] = []
    col_heights: list[float] = []
    for i, (_name, steps) in enumerate(stages):
        linss, fss, hs = [], [], []
        for j, step in enumerate(steps):
            lines, fs = fit_text(step, col_w - 2 * TEXT_PAD, BOX_FS, BOX_FS_MIN,
                                 max_lines=5, ctx=f"列 {i + 1} 步骤 {j + 1}",
                                 warnings=warnings)
            linss.append(lines)
            fss.append(fs)
            hs.append(block_height(len(lines), fs, min_h=CARD_MIN_H))
        col_lines.append(linss)
        col_fs.append(fss)
        col_heights.append(sum(hs) + (len(hs) - 1) * BOX_GAP)
    body_top = TITLE_ZONE + HEADER_H + HEADER_GAP
    canvas_h = body_top + max(col_heights) + BOTTOM_PAD

    d = Diagram(page_width=CANVAS_W, page_height=canvas_h, name="技术路线流程图")
    d.title("title", title_text, 40, 18, CANVAS_W - 80, 34)

    # 1) 列头横条（实色标题条: 各列取 GENERIC 族序, 族 header 底白字）
    for i, (stage_name, _steps) in enumerate(stages):
        lines, fs = fit_text(stage_name, col_w - 2 * 12.0, HEADER_FS,
                             HEADER_FS_MIN, max_lines=1,
                             ctx=f"列头 {stage_name!r}", warnings=warnings)
        d.header_bar(f"col{i + 1}_header", label_html(lines), col_x[i],
                     TITLE_ZONE, col_w, HEADER_H, family=fams[i], font_size=fs)

    # 2) 列内步骤卡片（族色浅底, 自上而下）与列内下行连线（本族 edge 色）
    for i, (_name, steps) in enumerate(stages):
        cursor = body_top
        cx = col_x[i]
        prev_id: str | None = None
        for j in range(len(steps)):
            h = block_height(len(col_lines[i][j]), col_fs[i][j], min_h=CARD_MIN_H)
            step_id = f"col{i + 1}_step{j + 1}"
            d.card(step_id, label_html(col_lines[i][j]),
                   cx, cursor, col_w, h, font_size=col_fs[i][j], family=fams[i])
            if prev_id is not None:
                d.edge(prev_id, step_id, exit_dir="down", entry_dir="top",
                       stroke=fams[i]["edge"])
            prev_id = step_id
            cursor += h + BOX_GAP

    # 3) 列头之间横向流转连线（左列头右缘 → 右列头左缘, 左列族 edge 色）
    for i in range(n - 1):
        d.edge(f"col{i + 1}_header", f"col{i + 2}_header",
               exit_dir="right", entry_dir="left", stroke=fams[i]["edge"])

    for w in warnings:
        print(f"[警告] {w}")
    return d


def main(argv: list[str] | None = None) -> int:
    parser: argparse.ArgumentParser = base_parser(
        "生成 draw.io 多列阶段流程图（示例数据, 输出可编辑 .drawio）")
    parser.add_argument("--cols", type=int, default=4, metavar="N",
                        help="阶段列数, 2-6, 默认 4")
    args = parser.parse_args(argv)
    if not 2 <= args.cols <= 6:
        print(f"[参数错误] --cols 需在 2..6 之间, 实际 {args.cols}")
        return 2
    try:
        diagram = build_flow3col(_demo_stages(args.cols), palette=args.palette)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    return finalize(diagram, args.out, "make_drawio_flow3col")


if __name__ == "__main__":
    sys.exit(main())
