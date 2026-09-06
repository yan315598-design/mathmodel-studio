# -*- coding: utf-8 -*-
"""draw.io 泳道流程图（drawio 模板包 · swimlane, 1.2.0 族化版）。

横排 3-4 条泳道（数据层/模型层/求解层/应用层, 族序取 DIAGRAM_ORDER_GENERIC）:
每条泳道为族 fill 浅底色带, 左端道名徽章（族 chevron 浅底 + 族 stroke 描边 +
墨黑加粗字）, 泳道内族色浅底圆角步骤卡片自左向右按序号推进, 跨泳道流转用
正交连线（发起泳道族 edge 色; 下行/上行锚定, 同层右行）。输出 .drawio,
draw.io 桌面版/网页版打开即编辑。

确定性布局: 页面坐标原点左上、y 向下; 步骤列等距分布, 中文字宽估算均衡
换行, 超宽自动缩字号（下限 8.5pt）, 仍放不下打印 [警告]。

用法:
    python make_drawio_swimlane.py --out 输出前缀 [--palette academic_blue]
        [--lanes 4]
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

# 示例数据: 每泳道 (道名, [道内步骤...]); 步骤按"道 1 从左到右 → 道 2 ..."
# 的蛇形顺序串成主流程, 相邻步骤同道右行、跨道正交上下行
DEMO_LANES_4: list[tuple[str, list[str]]] = [
    ("数据层", ["多源时序数据采集", "清洗·填补·标准化"]),
    ("模型层", ["评价指标体系构建", "多目标优化主模型"]),
    ("求解层", ["NSGA-II 混合求解", "灵敏度与稳健性检验"]),
    ("应用层", ["多情景方案评估", "调度决策建议输出"]),
]
DEMO_LANES_3: list[tuple[str, list[str]]] = [
    ("数据层", ["多源时序数据采集", "清洗·填补·标准化"]),
    ("模型层", ["评价指标体系构建", "多目标优化主模型"]),
    ("求解层", ["NSGA-II 混合求解", "方案评估与决策建议"]),
]

# 页面几何（px, y 向下; 页边距 >= 40）
CANVAS_W = 1220.0
ML, MR = 40.0, 40.0
LABEL_W = 120.0          # 道名徽章宽
LABEL_GAP = 20.0         # 徽章与步骤区间距
LANE_H = 96.0            # 泳道带高
LANE_GAP = 24.0          # 泳道带间距
TITLE_ZONE = 84.0
BOTTOM_PAD = 44.0
NODE_GAP = 18.0          # 步骤卡横向间距
STEP_FS, STEP_FS_MIN = 10.5, 8.5
LABEL_FS = 12.0


def build_swimlane(lanes: list[tuple[str, list[str]]],
                   palette: str = "academic_blue",
                   title_text: str = "建模求解泳道流程图") -> Diagram:
    """构建泳道流程图的 Diagram（不落盘）。

    Args:
        lanes: 3-4 条 (道名, [道内步骤...]); 各道步骤数建议一致。
        palette: 色板名。
        title_text: 图标题。

    Raises:
        ValueError: 泳道数/行结构/空文本不合法, 或色板名未知。
    """
    if not 3 <= len(lanes) <= 4:
        raise ValueError(f"泳道图需要 3-4 条泳道, 实际 {len(lanes)} 条")
    for i, lane_def in enumerate(lanes):
        if len(lane_def) != 2:
            raise ValueError(f"lanes 第 {i + 1} 条必须是 (道名, [步骤...]) "
                             f"二元组, 实际: {lane_def!r}")
        lane_name, steps = lane_def
        if not str(lane_name).strip():
            raise ValueError(f"第 {i + 1} 条泳道道名为空")
        if not steps:
            raise ValueError(f"泳道 {lane_name!r} 的步骤列表为空")
        for step in steps:
            if not str(step).strip():
                raise ValueError(f"泳道 {lane_name!r} 存在空步骤文字")

    get_palette(palette)   # 兼容校验: --palette 仍须是已注册色板名
    fams = get_diagram_families(n=len(lanes))   # DIAGRAM_ORDER_GENERIC 前 n 族
    warnings: list[str] = []
    n_lanes = len(lanes)
    n_cols = max(len(steps) for _name, steps in lanes)
    zone_x = ML + LABEL_W + LABEL_GAP
    zone_w = CANVAS_W - zone_x - MR
    node_w = (zone_w - (n_cols - 1) * NODE_GAP) / n_cols
    lane_y = [TITLE_ZONE + i * (LANE_H + LANE_GAP) for i in range(n_lanes)]
    canvas_h = TITLE_ZONE + n_lanes * LANE_H + (n_lanes - 1) * LANE_GAP + BOTTOM_PAD

    d = Diagram(page_width=CANVAS_W, page_height=canvas_h, name="泳道流程图")
    d.title("title", title_text, 40, 22, CANVAS_W - 80, 34)

    # 1) 泳道底色带（族 fill 浅底, 先注册居下层）与道名徽章
    #    （族 chevron 浅底 + 族 stroke 描边 + 墨黑加粗字）
    for i, (lane_name, _steps) in enumerate(lanes):
        d.lane(f"lane{i + 1}_bg", ML, lane_y[i], CANVAS_W - ML - MR, LANE_H,
               family=fams[i])
        d.badge(f"lane{i + 1}_label", lane_name, ML, lane_y[i] + 8,
                LABEL_W, LANE_H - 16, family=fams[i], font_size=LABEL_FS)

    # 2) 步骤卡片（本泳道族色浅底）: 全局序号蛇形铺开（道 i 的第 k 步放第 k 列）, 先卡后线
    seq: list[tuple[int, int]] = []   # (泳道序, 列序) 按主流程顺序
    for i in range(n_lanes):
        for k in range(len(lanes[i][1])):
            seq.append((i, k))
    heights: dict[tuple[int, int], float] = {}
    for i, (lane_name, steps) in enumerate(lanes):
        for k, step in enumerate(steps):
            lines, fs = fit_text(step, node_w - 2 * 12.0, STEP_FS, STEP_FS_MIN,
                                 max_h=LANE_H - 16, ctx=f"泳道 {lane_name!r} 步骤 {k + 1}",
                                 warnings=warnings)
            h = block_height(len(lines), fs, min_h=42.0)
            heights[(i, k)] = h
            x = zone_x + k * (node_w + NODE_GAP)
            d.card(f"step{i * n_cols + k + 1}", label_html(lines),
                   x, lane_y[i] + (LANE_H - h) / 2, node_w, h, font_size=fs,
                   family=fams[i])

    # 3) 主流程连线（发起泳道族 edge 色）: 同道右行, 跨道正交下/上行（锚定出/入方向）
    for s in range(len(seq) - 1):
        i, k = seq[s]
        j, m = seq[s + 1]
        src_id = f"step{i * n_cols + k + 1}"
        dst_id = f"step{j * n_cols + m + 1}"
        if i == j:   # 同泳道: 右行
            d.edge(src_id, dst_id, exit_dir="right", entry_dir="left",
                   stroke=fams[i]["edge"])
        elif j > i:  # 下行泳道
            d.edge(src_id, dst_id, exit_dir="down", entry_dir="top",
                   stroke=fams[i]["edge"])
        else:        # 上行泳道
            d.edge(src_id, dst_id, exit_dir="up", entry_dir="bottom",
                   stroke=fams[i]["edge"])

    for w in warnings:
        print(f"[警告] {w}")
    return d


def main(argv: list[str] | None = None) -> int:
    parser: argparse.ArgumentParser = base_parser(
        "生成 draw.io 泳道流程图（示例数据, 输出可编辑 .drawio）")
    parser.add_argument("--lanes", type=int, default=4, choices=[3, 4],
                        help="泳道条数, 3 或 4, 默认 4（数据/模型/求解/应用）")
    args = parser.parse_args(argv)
    demo = DEMO_LANES_4 if args.lanes == 4 else DEMO_LANES_3
    try:
        diagram = build_swimlane(demo, palette=args.palette)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    return finalize(diagram, args.out, "make_drawio_swimlane")


if __name__ == "__main__":
    sys.exit(main())
