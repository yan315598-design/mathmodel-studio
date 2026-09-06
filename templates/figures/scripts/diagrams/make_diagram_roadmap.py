# -*- coding: utf-8 -*-
"""竖版五带技术路线图（示意图模板包 · roadmap, 1.3.1 语义槽位重写版）。

五个横向色带层自上而下排布: 问题提出 → 数据处理 → 模型构建 → 求解验证 →
结论应用。1.3.1 起从"一行文字通用卡"升级为**语义槽位版式**（追平
sci-box roadmap-5band 的信息架构）:

  - 每条色带: 左侧 圈号+层名 徽章(chip) + 右侧竖排阶段目标(vlabel)
    + 中间内容卡区 + 带缘点线分带;
  - 内容卡 = 两段式富文本卡 rich_box: **bold 标题行**（方法/动作, body 档）
    + regular 明细行（参数/口径, note 档次级色）——信息密度来自内容结构;
  - 层间正交下行箭头降重（lw 1.3 / 小箭头头）, 取下一层族 edge 色;
  - 图末可挂结论脚注条 footnote_bar（左族色 tick + 左对齐小字）。

数据模型: BANDS = [(层名, 阶段目标, [(标题, 明细), ...]), ...] 恰好 5 条,
每条 1-3 个节点; 节点也兼容纯字符串（退化为单行卡）。向后兼容 1.2.0 的
[(层名, [节点文字...])] 二元组调用——二元组时阶段目标省略、节点视为标题。

确定性布局: 画布逻辑坐标 = 像素（dpi=100）, 中文字宽估算均衡换行,
不依赖任何 GUI/字体测量, 输出可复现。文字过长自动缩字号（明细先于标题）,
仍放不下打印 [警告] 不静默裁字。

用法（二选一）:
    1. 独立运行:
       python make_diagram_roadmap.py [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 BANDS 数据（标题/明细都换成你的真实研究内容）。

版本:
    1.3.1: 语义槽位重写——两段式富文本卡/圈号徽章/竖排阶段目标/结论脚注,
        字重回层级制（标题条与徽章加粗, 卡内正文常规）, 连线降重。
    1.2.0: 迁移示意图色族体系; 1.1.0: 迁移 figkit + 三格式导出。

质量门:
    python scripts/figqa.py templates/figures/scripts/diagrams/make_diagram_roadmap.py \\
        --strict --allow-box-labels   （盒内标签为有意版式）

退出码: 0 成功; 2 参数/数据错误。
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

# ---- 头部统一走共享库 figkit（样式/色族/卡片/导出/换行/连接器/结构化零件）----
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    apply_style,
    elbow_arrow,
    footnote_bar,
    load_diagram_families,
    load_diagram_order,
    load_diagram_page,
    num_badge,
    rich_box,
    save_fig,
    use_diagram_font,
    vlabel,
    wrap_text_balanced,
)

# 示例数据 1.3.1: (层名, 阶段目标, [(标题, 明细), ...]); 每层 1-3 个节点
# 明细行写"参数/口径/方法细节", 是信息密度的主要来源——换成你的真实内容
BANDS: list[tuple[str, str, list[tuple[str, str]]]] = [
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

# 画布逻辑坐标 = 像素（dpi=100）; matplotlib 字号以 pt 计, 1pt = 100/72 px
CANVAS_W = 1220
BAND_H = 116.0        # 色带（层）高: 容纳两段式卡 68 + 上下呼吸区
BAND_GAP = 54.0       # 层间空隙（下行箭头活动区）
CARD_H = 68.0         # 两段式内容卡高
CARD_H_SINGLE = 44.0  # 单节点带的内容卡高（单行退化时仍按两段式排版）
CHIP_FS = 13.0
TITLE_FS = 16.0
LINE_PITCH = 1.36 * 1.45
LAYER_NUMS = "①②③④⑤"


def _draw_chip(ax, x: float, y_top: float, w: float, h: float, name: str,
               num: str, family: dict[str, str], ink: str) -> None:
    """层名徽章: 圈号 + 层名（族 chevron 底 + 族 stroke 描边 + 墨黑加粗字）。

    徽章是结构件, 保持加粗（字重层级制）; 超宽自动换行/超高缩字号。
    """
    from matplotlib.patches import FancyBboxPatch

    text = f"{num} {name}"
    fs = CHIP_FS
    lines = wrap_text_balanced(text, w - 20.0, fs)
    while len(lines) * fs * LINE_PITCH > h - 8.0 and fs > 9.0:
        fs = max(fs - 1.0, 9.0)
        lines = wrap_text_balanced(text, w - 20.0, fs)
    if len(lines) * fs * LINE_PITCH > h - 8.0:
        print(f"[警告] 层名 {text!r} 过长: 徽章内放不下, 建议精简层名")
    patch = FancyBboxPatch(
        (x, y_top - h), w, h,
        boxstyle="round,pad=2,rounding_size=8",
        facecolor=family["chevron"], edgecolor=family["stroke"],
        linewidth=1.0, zorder=2,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y_top - h / 2, "\n".join(lines), ha="center",
            va="center", fontsize=fs, color=ink, fontweight="bold",
            linespacing=1.45, zorder=5)


def _normalize_bands(bands) -> list[tuple[str, str, list[tuple[str, str]]]]:
    """入参归一化: 兼容 1.2.0 二元组 (层名, [文字...]) 与 1.3.1 三元组
    (层名, 阶段目标, [(标题, 明细)...]); 节点兼容纯字符串（视为只有标题）。"""
    out = []
    for band in bands:
        if len(band) == 2:                       # 旧版二元组
            name, nodes = band
            goal = ""
        elif len(band) == 3:
            name, goal, nodes = band
        else:
            raise ValueError(f"每条必须是 (层名, [节点...]) 或 (层名, 目标, [节点...]), "
                             f"实际: {band!r}")
        if not str(name).strip():
            raise ValueError(f"层名不能为空: {band!r}")
        if not 1 <= len(nodes) <= 3:
            raise ValueError(f"层 {name!r} 节点数 {len(nodes)} 不在 [1, 3] 范围")
        norm_nodes = []
        for node in nodes:
            if isinstance(node, str):
                if not node.strip():
                    raise ValueError(f"层 {name!r} 存在空节点文字")
                norm_nodes.append((node, ""))
            else:
                if len(node) != 2 or not str(node[0]).strip():
                    raise ValueError(f"层 {name!r} 节点须为 (标题, 明细), 实际: {node!r}")
                norm_nodes.append((str(node[0]), str(node[1])))
        out.append((str(name), str(goal), norm_nodes))
    return out


def _next_node_index(k: int, cnt: int, cnt_next: int) -> int:
    """第 k 个节点向下映射到下一层第几个节点（按相对位置成比例收敛）。"""
    if cnt_next <= 1:
        return 0
    if cnt <= 1:
        return (cnt_next - 1) // 2  # 单宽盒流向下一层居中节点
    return int(round(k * (cnt_next - 1) / max(cnt - 1, 1)))


def plot_roadmap(bands, out_stem: str | None = None,
                 title: str = "研究技术路线图",
                 conclusion: str | None = CONCLUSION) -> tuple[Path, Path]:
    """绘制竖版五带技术路线图并保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        bands: 恰好 5 条; 推荐 1.3.1 三元组 (层名, 阶段目标, [(标题, 明细)...]),
            兼容旧二元组 (层名, [节点文字...])。每层 1-3 个节点。
        out_stem: 输出文件前缀; None 时写系统临时目录。
        title: 图标题。
        conclusion: 图末结论脚注条文字; None 或空串时不画。

    Raises:
        ValueError: 层数不为 5 / 行结构非法 / 层名为空 / 节点数越界 / 空文字。
    """
    bands = _normalize_bands(bands)
    if len(bands) != 5:
        raise ValueError(f"竖版五带技术路线图需要恰好 5 层, 实际 {len(bands)} 层")

    apply_style()
    use_diagram_font()
    fams = load_diagram_families(order=load_diagram_order("roadmap"), n=5)
    ink = load_diagram_page("ink")
    band_sep = load_diagram_page("band_sep")

    # 横向几何: 左徽章 + 中内容区 + 右竖排目标
    ML = 40.0
    chip_w, chip_gap = 172.0, 20.0
    VL_W, VL_GAP = 24.0, 16.0     # 右侧竖排标签区
    MR = 40.0
    zone_x0 = ML + chip_w + chip_gap
    zone_w = CANVAS_W - zone_x0 - MR - VL_W - VL_GAP
    vl_x = CANVAS_W - MR - VL_W / 2
    node_gap = 24.0

    # 纵向几何
    step = BAND_H + BAND_GAP
    foot_zone = 56.0 if conclusion else 24.0
    CANVAS_H = 5 * BAND_H + 4 * BAND_GAP + 100.0 + foot_zone
    top_band_y = CANVAS_H - 64.0
    band_top = [top_band_y - i * step for i in range(5)]

    fig = plt.figure(figsize=(CANVAS_W / 100.0, CANVAS_H / 100.0), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CANVAS_W)
    ax.set_ylim(0, CANVAS_H)
    ax.axis("off")
    ax.text(CANVAS_W / 2, CANVAS_H - 32, title, ha="center", va="center",
            fontsize=TITLE_FS, fontweight="bold", color=ink)

    # 1) 五条色带底 + 点线分带（fill_between/plot 为折线, 不参与 figqa 色块误判）
    for i in range(5):
        top, bot = band_top[i], band_top[i] - BAND_H
        ax.fill_between([ML, CANVAS_W - MR], [bot, bot], [top, top],
                        color=fams[i]["fill"], zorder=0)
        ax.plot([ML, CANVAS_W - MR, CANVAS_W - MR, ML, ML],
                [top, top, bot, bot, top],
                linestyle=(0, (1, 3)), color=band_sep, linewidth=1.0,
                zorder=1, solid_capstyle="butt")

    # 2) 徽章 + 竖排目标 + 两段式内容卡
    card_pos: list[list[tuple[float, float, float]]] = []   # 每卡 (中心x, 宽, 高)
    for i, (name, goal, nodes) in enumerate(bands):
        cy = band_top[i] - BAND_H / 2
        _draw_chip(ax, ML, cy + (BAND_H - 24.0) / 2, chip_w, BAND_H - 24.0,
                   name, LAYER_NUMS[i], fams[i], ink)
        if goal:
            vlabel(ax, vl_x, cy, goal, color=fams[i]["edge"], bold=False)
        row = []
        cnt = len(nodes)
        for k, (node_title, node_detail) in enumerate(nodes):
            if cnt == 1:
                w = min(zone_w, 560.0)
                cx = zone_x0 + zone_w / 2
            else:
                w = (zone_w - (cnt - 1) * node_gap) / cnt
                cx = zone_x0 + k * (w + node_gap) + w / 2
            h = CARD_H if node_detail else CARD_H_SINGLE
            rich_box(ax, cx - w / 2, cy + h / 2, w, h,
                     node_title, node_detail, fams[i])
            row.append((cx, w, h))
        card_pos.append(row)

    # 3) 层间下行箭头（下一层族 edge 色; 扇入时落点在盒顶错开）
    #    路由纪律: 箭头必须以竖直方向进入盒顶——x 有偏移时拆成
    #    "vh 无头折线 + 竖直箭头"两段, 避免箭头横着抵在盒顶上
    for i in range(4):
        rows_cur, rows_nxt = card_pos[i], card_pos[i + 1]
        incoming: dict[int, list[int]] = {j: [] for j in range(len(rows_nxt))}
        for k in range(len(rows_cur)):
            incoming[_next_node_index(k, len(rows_cur), len(rows_nxt))].append(k)
        for j, sources in incoming.items():
            if not sources:
                continue
            nx, nw, nh = rows_nxt[j]
            y_top_next = band_top[i + 1] - (BAND_H - nh) / 2
            m = len(sources)
            spread = min(44.0, nw / (m + 1))
            for order, k in enumerate(sources):
                cx, w, h = rows_cur[k]
                y_bot = band_top[i] - (BAND_H - h) / 2 - h
                land_x = nx + (order - (m - 1) / 2) * spread if m > 1 else nx
                color = fams[i + 1]["edge"]
                if abs(land_x - cx) <= 1e-6:
                    # 上下对齐: 单根竖直箭头
                    elbow_arrow(ax, (cx, y_bot + 1), (land_x, y_top_next - 1),
                                color=color, direction="vh", rad=0.0)
                else:
                    # x 有偏移: 无头 vh 折线到目标正上方, 再竖直箭头进盒顶
                    y_mid = (y_bot + y_top_next) / 2
                    elbow_arrow(ax, (cx, y_bot + 1), (land_x, y_mid),
                                color=color, direction="vh", rad=6.0,
                                arrowstyle="-")
                    elbow_arrow(ax, (land_x, y_mid), (land_x, y_top_next - 1),
                                color=color, direction="vh", rad=0.0)

    # 4) 图末结论脚注条（可选）
    if conclusion:
        footnote_bar(ax, ML, band_top[4] - BAND_H - BAND_GAP / 2 + 14.0,
                     CANVAS_W - ML - MR, 30.0, conclusion, fams[4])

    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / "make_diagram_roadmap")
    written = [Path(p) for p in save_fig(fig, out_stem)]
    return written[0], written[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成竖版五带技术路线图（示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    try:
        png, svg = plot_roadmap(BANDS, out_stem=args.out)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    print(f"已输出: {png}")
    print(f"已输出: {svg}")
    print(f"已输出: {png.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
