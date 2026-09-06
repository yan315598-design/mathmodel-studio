# -*- coding: utf-8 -*-
"""技术路线图模板: matplotlib 四阶段列式技术路线图（示意图色族版）。

版式（1.2.0 整体重写, 复刻 sci-box 扁平风）:
    顶部通栏实色标题条（DIAGRAM_PAGE title_bar #4F80BD 白字）→ 其下 4 个
    阶段列, 每列 = 实色标题条（族 header 底白字, diagram_header）+ 虚线
    容器（族 stroke, dash 4 4）内 2-4 张内容卡（浅底 + 同族描边 + 墨黑
    加粗字, diagram_box）; 列间箭头取左列族 edge 色, 列内连接线全部为
    "上一张卡底边中点 → 下一张卡顶边中点"的段式短箭头（标题条→首卡同理,
    本族 edge 色, 线段只存在于卡间空隙, 不穿卡面）。阶段族序取
    DIAGRAM_ORDER_GENERIC 前 4 族（blue/teal/olive/orange）, 与数据图表
    色板彻底分类。

确定性布局: 画布逻辑坐标 = 像素（dpi=100）, 中文字宽估算均衡换行, 画布
高按各列内容卡实际行数推导, 不依赖任何 GUI/字体测量, 输出可复现。文字
过长自动缩字号（下限 8pt）, 仍放不下打印 [警告] 溢出提示, 不静默裁字。

用法（二选一）:
    1. 独立运行:
       python make_technical_route_flowchart.py [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录（gitignore 友好）, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 STAGES 数据。

版本:
    1.2.0: 整体重写迁移 figkit 示意图族体系——弃内联私有色板副本,
      卡片全部入盒（消灭裸文本节点压箭头线）, 画布高按内容计算（消灭
      底部大片空白）, apply_style() 后 use_diagram_font() 全字加粗。
    1.1.0: 迁移 figkit + 三格式导出 + 中性色令牌。

质量门:
    python scripts/figqa.py templates/figures/scripts/templates/make_technical_route_flowchart.py \\
        --strict --allow-box-labels   （盒内标签为有意版式）

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

# ---- 1.2.0: 整体走 figkit 示意图族体系（样式/色族/卡片/标题条/连接器）----
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    DIAGRAM_LINE_PITCH,
    apply_style,
    diagram_box,
    diagram_header,
    elbow_arrow,
    load_diagram_families,
    load_diagram_page,
    save_fig,
    use_diagram_font,
    wrap_text_balanced,
)

# 示例数据: (阶段名, [该阶段的步骤描述...]); 阶段自左向右, 步骤自上而下
STAGES: list[tuple[str, list[str]]] = [
    ("问题分析", ["题目解读与数据勘察", "关键约束识别", "评价指标体系构建"]),
    ("模型建立", ["主规划模型（混合整数）", "碳约束与不确定性建模", "稳健性指标量化"]),
    ("求解与算法", ["分支定界精确求解", "自适应遗传算法", "蒙特卡洛场景模拟"]),
    ("结果与验证", ["灵敏度龙卷风分析", "多场景稳健性对比", "结论与方案建议"]),
]

# 画布逻辑坐标 = 像素（dpi=100 下 1 单位 = 1 px）, 字宽估算才有确定基准
CANVAS_W = 1240.0
ML, MR = 40.0, 40.0
COL_GAP = 64.0            # 列间通道（列间箭头活动区）
HEADER_H = 42.0           # 阶段标题条高
HEADER_GAP = 18.0         # 标题条与虚线容器间距
TITLE_BAR_H = 46.0        # 顶部通栏标题条高
TITLE_ZONE = 34.0 + TITLE_BAR_H + 24.0   # 顶部留白 + 标题条 + 标题条下空隙
BOTTOM_PAD = 36.0
BOX_FS, BOX_FS_MIN = 10.5, 8.0
HEADER_FS = 12.0
TITLE_FS = 15.5
CARD_MIN_H = 44.0
CARD_GAP = 26.0           # 列内卡间空隙（向下箭头活动区）
CONT_PAD = 12.0           # 虚线容器内边距（卡片与虚线框的间隙）
TEXT_PAD = 14.0


def _card_height(text: str, w: float, fs: float, fs_min: float) -> tuple[list[str], float, float]:
    """按 diagram_box 同一套换行/缩字号规则预估卡高, 返回 (行, 字号, 卡高)。"""
    lines = wrap_text_balanced(text, w - 2 * TEXT_PAD, fs)
    while len(lines) * fs * DIAGRAM_LINE_PITCH + 12.0 > 92.0 and fs > fs_min:
        fs = max(fs - 0.5, fs_min)
        lines = wrap_text_balanced(text, w - 2 * TEXT_PAD, fs)
    h = max(len(lines) * fs * DIAGRAM_LINE_PITCH + 12.0, CARD_MIN_H)
    return lines, fs, h


def plot_flowchart(stages: list[tuple[str, list[str]]],
                   out_stem: str | None = None,
                   title: str = "技术路线图") -> tuple[Path, Path]:
    """绘制技术路线图并保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        stages: (阶段名, 步骤描述列表); 2-6 列, 阶段自左向右流转,
            每列步骤 2-4 张自上而下推进。
        out_stem: 输出文件前缀; None 时写系统临时目录。
        title: 图标题（画在顶部通栏实色标题条内, 白字加粗）。

    Raises:
        ValueError: stages 为空 / 行不是二元组 / 阶段名为空 / 步骤列表
            为空或不在 [2,4] / 存在空步骤描述。
    """
    if not stages:
        raise ValueError("stages 不能为空: 至少提供一条 (阶段名, [步骤...]) 记录")
    for stage in stages:
        if len(stage) != 2:
            raise ValueError(f"stages 每条必须是 (阶段名, [步骤...]) 二元组, 实际: {stage!r}")
        stage_name, steps = stage
        if not str(stage_name).strip():
            raise ValueError(f"阶段名不能为空: {stage!r}")
        if not 2 <= len(steps) <= 4:
            raise ValueError(f"阶段 {stage_name!r} 的步骤数 {len(steps)} 不在 [2, 4] 范围")
        for step in steps:
            if not str(step).strip():
                raise ValueError(f"阶段 {stage_name!r} 存在空步骤描述")

    apply_style()
    use_diagram_font()
    n = len(stages)
    fams = load_diagram_families(n=n)   # DIAGRAM_ORDER_GENERIC 前 n 族

    col_w = (CANVAS_W - ML - MR - (n - 1) * COL_GAP) / n
    col_x = [ML + i * (col_w + COL_GAP) for i in range(n)]

    # 逐列逐步骤换行算卡高 → 各列容器高 → 画布高按内容精确推导
    col_cards: list[list[tuple[list[str], float, float]]] = []
    for _name, steps in stages:
        col_cards.append([
            _card_height(step, col_w - 2 * CONT_PAD, BOX_FS, BOX_FS_MIN)
            for step in steps
        ])
    col_body_h = [sum(h for *_u, h in cards) + (len(cards) - 1) * CARD_GAP
                  + 2 * CONT_PAD for cards in col_cards]
    canvas_h = TITLE_ZONE + HEADER_H + HEADER_GAP + max(col_body_h) + BOTTOM_PAD

    fig = plt.figure(figsize=(CANVAS_W / 100.0, canvas_h / 100.0), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CANVAS_W)
    ax.set_ylim(0, canvas_h)
    ax.axis("off")

    # 1) 顶部通栏实色标题条（DIAGRAM_PAGE title_bar + 白字加粗）
    bar = plt.Rectangle((ML, canvas_h - TITLE_ZONE + 34.0 - TITLE_BAR_H),
                        CANVAS_W - ML - MR, TITLE_BAR_H,
                        facecolor=load_diagram_page("title_bar"),
                        edgecolor=load_diagram_page("title_bar"), linewidth=1.2,
                        zorder=2)
    ax.add_patch(bar)
    ax.text(CANVAS_W / 2, canvas_h - TITLE_ZONE + 34.0 - TITLE_BAR_H / 2, title,
            ha="center", va="center", fontsize=TITLE_FS,
            color=load_diagram_page("white"), fontweight="bold", zorder=5)

    header_top = canvas_h - TITLE_ZONE - HEADER_H
    header_boxes: list[tuple[float, float]] = []   # (列中心 x, 标题条底边 y)
    for i, (stage_name, _steps) in enumerate(stages):
        diagram_header(ax, col_x[i], header_top, col_w, HEADER_H,
                       stage_name, fams[i], fontsize=HEADER_FS)
        header_boxes.append((col_x[i] + col_w / 2, header_top - HEADER_H))

    # 2) 各列: 虚线分组容器（族 stroke, dash 4 4）+ 容器内纵向内容卡
    cont_top = header_boxes[0][1] - HEADER_GAP
    for i, cards in enumerate(col_cards):
        x0, x1 = col_x[i], col_x[i] + col_w
        y_top, y_bot = cont_top, cont_top - col_body_h[i]
        # 虚线容器画成折线（Line2D）而非 patch: figqa 把无填充大 patch 的
        # bbox 当色块, 会误伤容器内卡片的盒内标签豁免
        ax.plot([x0, x1, x1, x0, x0], [y_top, y_top, y_bot, y_bot, y_top],
                linestyle=(0, (4, 4)), color=fams[i]["stroke"],
                linewidth=1.2, zorder=1, solid_capstyle="butt")
        cursor = y_top - CONT_PAD
        card_w = col_w - 2 * CONT_PAD
        prev_bottom: float | None = None
        for j, (lines, fs, h) in enumerate(cards):
            cx = col_x[i] + col_w / 2
            card_lines, card_fs = diagram_box(
                ax, col_x[i] + CONT_PAD, cursor, card_w, h,
                stages[i][1][j], fams[i], fontsize=BOX_FS, fs_min=BOX_FS_MIN)
            assert card_lines == lines and card_fs == fs  # 布局预估与绘制一致
            if prev_bottom is None:
                # 标题条底边中点 → 首卡顶边中点（同一段短连接线, 本族 edge 色）
                elbow_arrow(ax, (cx, header_boxes[i][1] - 1), (cx, cursor + 1),
                            color=fams[i]["edge"], direction="vh", rad=0.0)
            else:
                # 卡间短连接线: 上一张卡底边中点 → 本卡顶边中点（箭头尖落在
                # 卡顶边上方 1px, 线段只存在于卡间空隙, 不穿过卡面/文字）
                elbow_arrow(ax, (cx, prev_bottom - 1), (cx, cursor + 1),
                            color=fams[i]["edge"], direction="vh", rad=0.0)
            prev_bottom = cursor - h
            cursor = prev_bottom - CARD_GAP

    # 3) 列间箭头（左列族 edge 色）: 左列标题条右缘中点 → 次列左缘中点
    for i in range(n - 1):
        y_mid = header_top - HEADER_H / 2
        elbow_arrow(ax, (col_x[i] + col_w + 2, y_mid),
                    (col_x[i + 1] - 2, y_mid),
                    color=fams[i]["edge"], direction="hv", rad=0.0)

    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / "make_technical_route_flowchart")
    written = [Path(p) for p in save_fig(fig, out_stem)]
    return written[0], written[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成技术路线图（示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    try:
        png, svg = plot_flowchart(STAGES, out_stem=args.out)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    print(f"已输出: {png}")
    print(f"已输出: {svg}")
    print(f"已输出: {png.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
