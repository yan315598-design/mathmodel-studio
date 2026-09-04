# -*- coding: utf-8 -*-
"""draw.io 竖版多层层带技术路线图（drawio 模板包 · roadmap, v7.9.1 语义槽位版）。

与 matplotlib 版 make_diagram_roadmap.py 同信息架构、同一套示例数据,
用 drawio 语言重写。层带族序取 DIAGRAM_ORDER_ROADMAP（默认 5 层即
blue/blue/orange/purple/teal, 层数更多时循环取）。v7.9.1 起升级为
语义槽位版式（追平 sci-box roadmap-5band 的信息架构）:

  - 每条色带: 族 fill 底 + 点线分带框 + 左侧 圈号+层名 徽章
    + 右侧竖排阶段目标（vlabel, 逐字 <br> 堆叠, 禁 horizontal=0）;
  - 内容卡 = rich_card 两段式: **bold 标题行** + regular 明细行
    （note 档 9px 次级色, 单元格级不加粗, 密度来自内容结构）;
  - 层间正交下行连线降重（1.3）, 取下一层族 edge 色;
  - 图末结论脚注（左对齐次级小字）。

输出 .drawio, draw.io 桌面版/网页版打开即编辑。--palette 参数保留兼容
（仅校验, 层带着色已由色族接管）。

确定性布局: 页面坐标原点左上、y 向下; 中文字宽估算均衡换行
（drawio_builder.wrap_text_balanced, 字号单位与 drawio fontSize 直接映射）,
超宽自动缩字号（下限 8pt）, 仍放不下打印 [警告] 不静默裁字。
落盘后 finalize() 自动跑 drawio_check.py 版式门禁（FAIL 即退出码 1）。

用法:
    python make_drawio_roadmap.py --out 输出前缀 [--palette academic_blue]
        [--layers 5] [--nodes 3,3,2,2,1] [--config demo]
    不给 --out 时示例图写入系统临时目录, 产出 <前缀>.drawio。

示例数据（--config demo, 与 matplotlib 版 roadmap 同示例）:
    问题提出 → 数据处理 → 模型构建 → 求解验证 → 结论应用

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
    DIAGRAM_FONT_RAMP, DIAGRAM_ORDER_ROADMAP, Diagram, base_parser,
    finalize, fit_text, get_diagram_families, get_palette, label_html,
    neutral, wrap_text_balanced,
)

# 示例数据（--config demo）v7.9.1: (层名, 阶段目标, [(标题, 明细), ...])
# 明细行写"参数/口径/方法细节", 是信息密度的主要来源——换成你的真实内容
DEMO_BANDS: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("问题提出", "明确边界", [
        ("题目背景解读", "关键目标 × 边界条件"),
        ("问题分解", "决策变量 · 约束梳理"),
        ("评价指标初筛", "可量化 · 可获取 · 低共线"),
    ]),
    ("数据处理", "干净可用", [
        ("数据清洗", "IQR 异常值 · 缺失率 <5%"),
        ("标准化与特征构造", "量纲统一 + 主成分降维"),
        ("探索性分析", "分布形态 · 相关性 ρ<0.6"),
    ]),
    ("模型构建", "可解可算", [
        ("多目标优化主模型", "min f1,f2 s.t. 约束集"),
        ("不确定性场景刻画", "情景集 × 关键参数"),
    ]),
    ("求解验证", "结果可信", [
        ("混合求解框架", "精确求解 + NSGA-II"),
        ("灵敏度与稳健性", "Sobol 全局 · ±10% 扰动"),
    ]),
    ("结论应用", "落地可用", [
        ("结论凝练与决策建议", "多情景对比 · 调度方案"),
    ]),
]
CONCLUSION = "技术路线闭环: 问题分解 → 数据治理 → 多目标建模 → 求解验证 → 决策应用, 各阶段产出互为下游输入"

_CN_NUMS = ["一", "二", "三", "四", "五"]
LAYER_NUMS_CIRCLED = "①②③④⑤⑥⑦⑧"   # 层数 <= 8 用圈号, 更长回退 01-05 补零

# 页面几何（px, y 向下; 页边距 >= 40, 坐标全部对齐 4px 网格）
CANVAS_W = 1220.0
BAND_H = 116.0          # 层带（色带）高: 容纳两段式卡 + 上下呼吸区
BAND_GAP = 52.0         # 层间空隙（下行连线活动区）
ML, CHIP_W, CHIP_GAP, MR = 40.0, 172.0, 20.0, 40.0
VL_W, VL_GAP = 24.0, 16.0   # 右侧竖排阶段目标区
TITLE_ZONE = 84.0       # 顶部标题区
BOTTOM_PAD = 60.0       # 底部（含结论脚注）
CHIP_FS, CHIP_FS_MIN = 13.0, 9.0
NODE_GAP = 24.0
TEXT_PAD = 14.0
BODY_FS, NOTE_FS = DIAGRAM_FONT_RAMP["body"], DIAGRAM_FONT_RAMP["note"]


def _rich_card_h(title: str, detail: str, max_w: float) -> float:
    """按内容估算两段式卡高: 标题行 + 明细行 + 块间 4px + 上下 14px。"""
    t_lines = wrap_text_balanced(title, max_w, BODY_FS)
    h = len(t_lines) * BODY_FS * 1.5
    if detail.strip():
        d_lines = wrap_text_balanced(detail, max_w, NOTE_FS)
        h += 4.0 + len(d_lines) * NOTE_FS * 1.5
    return max(h + 14.0, 56.0)


def _demo_bands(layers: int, counts: list[int]):
    """由 demo 数据推导指定层数/每层节点数的层带内容; 超出部分用可编辑占位。"""
    names = [band[0] for band in DEMO_BANDS]
    goals = [band[1] for band in DEMO_BANDS]
    texts = [list(band[2]) for band in DEMO_BANDS]
    base = len(names)   # demo 层数（5）; 层数上限 8, 超出最多补 3 个"深化研究"层
    for i in range(base, layers):
        names.append(f"深化研究{_CN_NUMS[i - base]}")
        goals.append("")
        texts.append([])
    bands = []
    for i in range(layers):
        nodes = texts[i][:counts[i]]
        while len(nodes) < counts[i]:
            nodes.append(("（双击编辑: 补充本节点内容）", ""))
        bands.append((names[i], goals[i], nodes))
    return bands


def _parse_counts(raw: str | None, layers: int) -> list[int]:
    """解析 --nodes: 单整数（所有层同数）或逗号分隔的每层节点数。"""
    if raw is None:
        counts = [len(band[2]) for band in DEMO_BANDS]
        counts = counts[:layers]
        while len(counts) < layers:
            counts.append(1)
        return counts
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ValueError("--nodes 不能为空")
    try:
        values = [int(p) for p in parts]
    except ValueError:
        raise ValueError(f"--nodes 需为整数或逗号分隔整数列表, 实际: {raw!r}") from None
    if len(values) == 1:
        values = values * layers
    if len(values) != layers:
        raise ValueError(f"--nodes 需要 {layers} 项（或 1 项全层同数）, 实际 {len(values)} 项")
    for v in values:
        if not 1 <= v <= 3:
            raise ValueError(f"每层节点数需在 [1, 3], 实际含 {v}")
    return values


def _next_node_index(k: int, cnt: int, cnt_next: int) -> int:
    """第 k 个节点向下映射到下一层第几个节点（按相对位置成比例收敛）。"""
    if cnt_next <= 1:
        return 0
    if cnt <= 1:
        return (cnt_next - 1) // 2   # 单宽盒流向下一层居中节点
    return int(round(k * (cnt_next - 1) / (cnt - 1)))


def build_roadmap(bands, palette: str = "academic_blue",
                  title_text: str = "研究技术路线图",
                  conclusion: str | None = CONCLUSION) -> Diagram:
    """构建竖版层带技术路线图的 Diagram（不落盘）。

    Args:
        bands: (层名, 阶段目标, [(标题, 明细)...]) 列表, 每层 1-3 节点,
            自上而下流动; 阶段目标可空串（不画竖排标签）。
        palette: 色板名（保留兼容; 仅校验合法名, 层带着色由色族接管）。
        title_text: 图标题。
        conclusion: 图末结论脚注文字; None 或空串时不画。

    Raises:
        ValueError: 层数/节点数/文本不合法, 或色板名未知。
    """
    if not 2 <= len(bands) <= 8:
        raise ValueError(f"技术路线图需要 2-8 层, 实际 {len(bands)} 层")
    for i, band in enumerate(bands):
        name, goal, nodes = band
        if not str(name).strip():
            raise ValueError(f"第 {i + 1} 层层名为空")
        if not 1 <= len(nodes) <= 3:
            raise ValueError(f"层 {name!r} 节点数 {len(nodes)} 不在 [1, 3] 范围")
        for node in nodes:
            if len(node) != 2 or not str(node[0]).strip():
                raise ValueError(f"层 {name!r} 节点须为 (标题, 明细), 实际: {node!r}")

    get_palette(palette)   # 兼容校验: --palette 仍须是已注册色板名
    warnings: list[str] = []
    n_layers = len(bands)
    # 层带族序: DIAGRAM_ORDER_ROADMAP（层数超出时循环取）
    fams = get_diagram_families(DIAGRAM_ORDER_ROADMAP, n_layers)
    zone_x0 = ML + CHIP_W + CHIP_GAP
    zone_w = CANVAS_W - zone_x0 - MR - VL_W - VL_GAP
    vl_x = CANVAS_W - MR - VL_W
    canvas_h = TITLE_ZONE + n_layers * BAND_H + (n_layers - 1) * BAND_GAP + BOTTOM_PAD

    d = Diagram(page_width=CANVAS_W, page_height=canvas_h, name="技术路线图")
    d.title("title", title_text, 40, 22, CANVAS_W - 80, 34)

    band_y = [TITLE_ZONE + i * (BAND_H + BAND_GAP) for i in range(n_layers)]
    # 1) 层带底色（族 fill, 先注册位于卡片下层）+ 点线分带框
    for i in range(n_layers):
        d.lane(f"layer{i + 1}_band", ML, band_y[i], CANVAS_W - ML - MR, BAND_H,
               family=fams[i])
        d.band_sep(f"layer{i + 1}_sep", ML, band_y[i], CANVAS_W - ML - MR, BAND_H)

    # 2) 左侧编号徽章 + 右侧竖排目标 + 层内两段式富文本卡
    node_rows: list[list[tuple[str, float, float]]] = []   # 每节点 (id, 盒宽, 盒高)
    for i, (name, goal, nodes) in enumerate(bands):
        chip_label = (f"{LAYER_NUMS_CIRCLED[i]} {name}" if n_layers <= 8
                      else f"{i + 1:02d} {name}")
        lines, fs = fit_text(chip_label, CHIP_W - 20, CHIP_FS, CHIP_FS_MIN,
                             max_h=BAND_H - 20 - 8, pad=8,
                             ctx=f"层 {i + 1} 徽章", warnings=warnings)
        d.badge(f"layer{i + 1}_badge", label_html(lines), ML, band_y[i] + 10,
                CHIP_W, BAND_H - 20, family=fams[i], font_size=fs)
        if goal:
            d.vlabel(f"layer{i + 1}_goal", goal, vl_x, band_y[i] + 12,
                     VL_W, BAND_H - 24, font_size=NOTE_FS,
                     color=fams[i]["edge"])
        rows: list[tuple[str, float, float]] = []
        cnt = len(nodes)
        for k, (node_title, node_detail) in enumerate(nodes):
            if cnt == 1:
                w = min(zone_w, 560.0)
                cx = zone_x0 + zone_w / 2
            else:
                w = (zone_w - (cnt - 1) * NODE_GAP) / cnt
                cx = zone_x0 + k * (w + NODE_GAP) + w / 2
            h = _rich_card_h(node_title, node_detail, w - 2 * TEXT_PAD)
            if h > BAND_H - 16:
                warnings.append(f"层 {i + 1} 节点 {k + 1} 内容偏多, "
                                f"卡高 {h:.0f}px 超带内可用 {BAND_H - 16:.0f}px")
                h = BAND_H - 16
            d.rich_card(f"layer{i + 1}_node{k + 1}", node_title, node_detail,
                        cx - w / 2, band_y[i] + (BAND_H - h) / 2, w, h,
                        family=fams[i])
            rows.append((f"layer{i + 1}_node{k + 1}", w, h))
        node_rows.append(rows)

    # 3) 层间正交下行连线（每个节点指向下一层映射节点, 取下一层族 edge 色）
    for i in range(n_layers - 1):
        for k in range(len(node_rows[i])):
            j = _next_node_index(k, len(node_rows[i]), len(node_rows[i + 1]))
            d.edge(node_rows[i][k][0], node_rows[i + 1][j][0],
                   exit_dir="down", entry_dir="top",
                   stroke=fams[i + 1]["edge"])

    # 4) 图末结论脚注（左对齐次级小字）
    if conclusion:
        d.text("conclusion", conclusion, ML, canvas_h - BOTTOM_PAD + 12,
               CANVAS_W - ML - MR, 24, font_size=NOTE_FS,
               color=neutral("secondary"), align="left")

    for w in warnings:
        print(f"[警告] {w}")
    return d


def main(argv: list[str] | None = None) -> int:
    parser: argparse.ArgumentParser = base_parser(
        "生成 draw.io 竖版层带技术路线图（示例数据, 输出可编辑 .drawio）")
    parser.add_argument("--layers", type=int, default=5, metavar="N",
                        help="层数, 2-8, 默认 5")
    parser.add_argument("--nodes", default=None, metavar="3,3,2,2,1",
                        help="每层节点数: 单整数或逗号分隔列表（每层 1-3）, "
                             "默认取示例数据的 3,3,2,2,1")
    parser.add_argument("--config", default="demo", choices=["demo"],
                        help="内容配置, 目前仅内置 demo 示例")
    args = parser.parse_args(argv)
    if not 2 <= args.layers <= 8:
        print(f"[参数错误] --layers 需在 2..8 之间, 实际 {args.layers}")
        return 2
    try:
        counts = _parse_counts(args.nodes, args.layers)
        diagram = build_roadmap(_demo_bands(args.layers, counts),
                                palette=args.palette)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    return finalize(diagram, args.out, "make_drawio_roadmap")


if __name__ == "__main__":
    sys.exit(main())
