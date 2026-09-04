# -*- coding: utf-8 -*-
"""模块化功能框图（示意图模板包 · module, v7.8.0 示意图色族版）。

中心"总模型"大框 + 四周 4-6 个卫星模块框（模块呈环状等角排布）; 中心与每个
卫星之间画双向箭头（数据流名称标在箭头中点旁）。卫星模块只露模块名与
输入/输出两个接口标签, 不画内部细节。中心模块 = grey 族 accent 浅底 +
header_stroke 描边（视觉最稳的浅底重心）, 卫星模块每枚一族
（DIAGRAM_ORDER_GENERIC 顺序: 族 fill 浅底 + 族 stroke 描边 + 墨黑加粗字）,
双向箭头 = 卫星族 edge 色。

确定性布局: 画布逻辑坐标 = 像素（dpi=100）, 画布尺寸按卫星数与环半径固定
推导, 中文字宽估算换行, 不依赖任何 GUI/字体测量, 输出可复现。文字过长自动
缩小字号（下限 8pt）, 仍放不下打印 [警告] 溢出提示。

用法（二选一）:
    1. 独立运行:
       python make_diagram_module.py [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 MODULES / CENTER_LINES 数据。

版本:
    v7.8.0: 迁移示意图色族体系——弃 cool_nature 数据色板, 中心改 grey 族
        accent+header_stroke, 卫星每枚一族（GENERIC 序）, 双向箭头取卫星
        族 edge 色, 全字加粗墨黑（去 soft_shadow 扁平化）。
    v7.7.0: 迁移 figkit + 三格式导出 + 中性色令牌。

质量门:
    python scripts/figqa.py templates/figures/scripts/diagrams/make_diagram_module.py \\
        --strict --allow-box-labels   （盒内标签为有意版式）

退出码: 0 成功; 2 参数/数据错误。
"""

from __future__ import annotations

import argparse
import math
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
from matplotlib.patches import FancyBboxPatch

# ---- v7.8.0: 头部统一走共享库 figkit（样式/色族/导出/连接器）----
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    apply_style,
    load_diagram_family,
    load_diagram_families,
    load_diagram_page,
    load_neutral,
    save_fig,
    straight_arrow,
    text_width_px,
    use_diagram_font,
    wrap_text_balanced,
)

# 示例数据: 中心总模型名称（1-3 行）与卫星模块
# 每卫星: (模块名, 输入接口, 输出接口, 中心-模块双向数据流名称)
CENTER_LINES: list[str] = ["组合优化总模型", "多源输入融合 · 多目标方案寻优"]
MODULES: list[tuple[str, str, str, str]] = [
    ("数据预处理模块", "原始多源时序数据", "清洗标准化样本集", "样本集"),
    ("需求预测模块", "样本集与特征参数", "滚动需求预测序列", "预测序列"),
    ("调度寻优模块", "预测序列与运行约束", "Pareto 可行方案集", "可行方案"),
    ("评估反馈模块", "候选方案与指标权重", "稳健性排序与决策建议", "评估反馈"),
]

# 画布几何常量（逻辑像素）: 环半径、中心/卫星盒半宽高
# matplotlib 字号以 pt 计, 1pt = 100/72 px; 字宽/行距按 dpi=100 实测校准
# 文本宽度/换行统一走 figkit.wrap_text_balanced（CJK 感知 + 均衡断行防吊行）
LINE_PITCH = 1.36    # 行距系数: 实际行距 ≈ 字号×1.317×行距参数, 留余量

RX, RY = 460.0, 300.0
CENTER_HALF = (165.0, 70.0)
SAT_HALF = (120.0, 50.0)
NAME_FS, NAME_FS_MIN = 10.5, 8.5
IFACE_FS, IFACE_FS_MIN = 8.5, 8.0
FLOW_FS = 9.0
TITLE_FS = 16.0
CANVAS_H = 820.0
CY = 405.0  # 中心纵坐标（标题区下移补偿后仍留足顶部空间）


def _ray_box_interval(p0, d, center, half) -> tuple[float | None, float | None]:
    """射线 p0 + t*d 与矩形盒（中心 center, 半宽半高 half）相交的
    [t_enter, t_exit]; 无交返回 (None, None)。"""
    tlo, thi = -math.inf, math.inf
    for p_axis, d_axis, c_axis, h_axis in zip(p0, d, center, half):
        if abs(d_axis) < 1e-9:
            if not (c_axis - h_axis <= p_axis <= c_axis + h_axis):
                return None, None
            continue
        t1 = (c_axis - h_axis - p_axis) / d_axis
        t2 = (c_axis + h_axis - p_axis) / d_axis
        tlo = max(tlo, min(t1, t2))
        thi = min(thi, max(t1, t2))
    if thi < tlo or thi < 0:
        return None, None
    return tlo, thi


def _draw_text_block(ax, lines: list[str], x: float, y: float, va: str,
                     fontsize: float, color: str, ha: str = "left",
                     bold: bool = False, **kw) -> None:
    """文本块（v7.9.1 字重层级制: 默认常规字重, 标题/徽章调用点显式 bold=True）。"""
    ax.text(x, y, "\n".join(lines), ha=ha, va=va, fontsize=fontsize,
            color=color, fontweight="bold" if bold else "normal",
            linespacing=1.4, zorder=5, **kw)


def plot_module(modules: list[tuple[str, str, str, str]],
                center_lines: list[str] | None = None,
                out_stem: str | None = None,
                title: str = "组合模型总体结构") -> tuple[Path, Path]:
    """绘制模块化功能框图并保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        modules: 4-6 条 (模块名, 输入, 输出, 数据流名)。
        center_lines: 中心总模型文本 1-3 行; None 用模块级 CENTER_LINES。
        out_stem: 输出文件前缀; None 时写系统临时目录。
        title: 图标题。

    Raises:
        ValueError: modules 数不在 [4,6] / 行不是四元组 / 存在空字段 /
            center_lines 为空或超过 3 行。
    """
    center = center_lines if center_lines is not None else CENTER_LINES
    warnings: list[str] = []
    if not 4 <= len(modules) <= 6:
        raise ValueError(f"模块化功能框图需要 4-6 个卫星模块, 实际 {len(modules)} 个")
    for m in modules:
        if len(m) != 4:
            raise ValueError(f"modules 每条必须是 (模块名, 输入, 输出, 数据流名) "
                             f"四元组, 实际: {m!r}")
        for field in m:
            if not str(field).strip():
                raise ValueError(f"模块 {m!r} 存在空字段")
    if not center or not 1 <= len(center) <= 3:
        raise ValueError(f"center_lines 需 1-3 行非空文本, 实际 {len(center)} 行")
    for line in center:
        if not str(line).strip():
            raise ValueError("center_lines 存在空行")

    apply_style()
    use_diagram_font()
    center_fam = load_diagram_family("grey")
    sat_fams = load_diagram_families(n=len(modules))   # GENERIC 序每卫星一族
    ink = load_diagram_page("ink")

    k = len(modules)
    W_half = RX + SAT_HALF[0] + 44.0
    CANVAS_W = 2 * W_half
    fig = plt.figure(figsize=(CANVAS_W / 100.0, CANVAS_H / 100.0), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CANVAS_W)
    ax.set_ylim(0, CANVAS_H)
    ax.axis("off")
    ax.text(CANVAS_W / 2, CANVAS_H - 32, title, ha="center", va="center",
            fontsize=TITLE_FS, fontweight="bold", color=ink)

    # 1) 卫星模块盒（族 fill 浅底 + 族 stroke 描边, 顶部模块名 + 底部输入/输出接口）
    sat_centers: list[tuple[float, float]] = []
    module_boxes: list[tuple[tuple[float, float], dict[str, str]]] = []
    for i, (name, inp, outp, _flow) in enumerate(modules):
        fam = sat_fams[i]
        ang = math.radians(90.0 - i * 360.0 / k)
        sx = CANVAS_W / 2 + RX * math.cos(ang)
        sy = CY + RY * math.sin(ang)
        sat_centers.append((sx, sy))
        module_boxes.append(((sx, sy), fam))
        x0, x1 = sx - SAT_HALF[0], sx + SAT_HALF[0]
        y_top, y_bot = sy + SAT_HALF[1], sy - SAT_HALF[1]
        max_w = 2 * SAT_HALF[0] - 16.0

        name_lines = wrap_text_balanced(name, max_w, NAME_FS)
        in_lines = wrap_text_balanced(f"输入: {inp}", max_w, IFACE_FS)
        out_lines = wrap_text_balanced(f"输出: {outp}", max_w, IFACE_FS)
        pitch = LINE_PITCH * 1.4  # 本图文本行距统一 1.4
        budget = 2 * SAT_HALF[1] - 16.0  # 盒内可用高（含锚点间距）
        need = (len(name_lines) * NAME_FS * pitch + 8.0
                + len(in_lines) * IFACE_FS * pitch + 6.0
                + len(out_lines) * IFACE_FS * pitch)
        if need > budget:
            name_lines = wrap_text_balanced(name, max_w, NAME_FS_MIN)
            need = (len(name_lines) * NAME_FS_MIN * pitch + 8.0
                    + len(in_lines) * IFACE_FS * pitch + 6.0
                    + len(out_lines) * IFACE_FS * pitch)
            if need > budget:
                warnings.append(
                    f"模块 {name!r} 文字过多: 缩至最小字号后仍需 {need:.0f}px "
                    f"(盒内可用 {budget:.0f}px), 建议精简接口描述"
                )

        patch = FancyBboxPatch(
            (x0, y_bot), 2 * SAT_HALF[0], 2 * SAT_HALF[1],
            boxstyle="round,pad=2,rounding_size=8",
            facecolor=fam["fill"], edgecolor=fam["stroke"], linewidth=1.0,
        )
        ax.add_patch(patch)
        name_fs = NAME_FS_MIN if need > budget else NAME_FS
        _draw_text_block(ax, name_lines, x0 + 10, y_top - 5, "top",
                         name_fs, ink, bold=True)
        in_h = len(in_lines) * IFACE_FS * LINE_PITCH * 1.4
        _draw_text_block(ax, in_lines, x0 + 10, y_bot + 8, "bottom",
                         IFACE_FS, ink)
        _draw_text_block(ax, out_lines, x0 + 10, y_bot + 8 + in_h + 6, "bottom",
                         IFACE_FS, ink)

    # 2) 中心总模型大框（grey 族 accent 浅底 + header_stroke 描边, 墨黑加粗;
    #    标题/说明按行高自适应排版防溢出）
    cw, ch = CENTER_HALF
    cx0, cy_b = CANVAS_W / 2 - cw, CY - ch
    ax.add_patch(FancyBboxPatch(
        (cx0, cy_b), 2 * cw, 2 * ch,
        boxstyle="round,pad=3,rounding_size=12",
        facecolor=center_fam["accent"], edgecolor=center_fam["header_stroke"],
        linewidth=1.2,
    ))
    inner_w = 2 * cw - 26.0
    pitch = LINE_PITCH * 1.4  # 中心文本行距统一 1.4
    fs_t, fs_t_min = 13.0, 10.5
    title_lines = wrap_text_balanced(center[0], inner_w, fs_t)
    if len(center) > 1:
        sub_lines: list[str] = []
        for ln in center[1:]:
            sub_lines.extend(wrap_text_balanced(ln, inner_w, 10.0))
    else:
        sub_lines = []
    inner_h = 2 * ch - 34.0
    while ((len(title_lines) * fs_t + len(sub_lines) * 10.0) * pitch + 8.0
            > inner_h and fs_t > fs_t_min):
        fs_t = max(fs_t - 0.5, fs_t_min)
        title_lines = wrap_text_balanced(center[0], inner_w, fs_t)
    if (len(title_lines) * fs_t + len(sub_lines) * 10.0) * pitch + 8.0 > inner_h:
        warnings.append(
            f"总模型文本过长: 缩至最小字号后仍需排版, 建议精简 center_lines"
        )
    title_h = len(title_lines) * fs_t * pitch
    y_title_top = CY + ch - 16.0
    _draw_text_block(ax, title_lines, CANVAS_W / 2, y_title_top, "top",
                     fs_t, ink, ha="center", bold=True)
    if sub_lines:
        sub_h = len(sub_lines) * 10.0 * pitch
        y_sub_bot = y_title_top - title_h - 10.0
        if y_sub_bot - sub_h < CY - ch + 14.0:  # 挤到盒底时压缩说明行距
            y_sub_bot = CY - ch + 14.0 + sub_h
        _draw_text_block(ax, sub_lines, CANVAS_W / 2, y_sub_bot, "bottom",
                         10.0, load_neutral("secondary"), ha="center")

    # 3) 中心 ↔ 卫星 双向箭头（卫星族 edge 色, rad=0.08 微弧, 汇聚/分发
    #    语义用斜线）+ 数据流名称标签（墨黑加粗）
    c0 = (CANVAS_W / 2, CY)
    arrow_rad = 0.08
    for i, ((sx, sy), fam) in enumerate(module_boxes):
        d = (sx - c0[0], sy - c0[1])
        norm = math.hypot(*d)
        if norm < 1e-6:
            continue
        d = (d[0] / norm, d[1] / norm)
        t_enter, _ = _ray_box_interval(c0, d, (sx, sy), SAT_HALF)
        _, t_exit = _ray_box_interval(c0, d, c0, CENTER_HALF)
        if t_enter is None or t_exit is None or t_enter <= t_exit:
            continue
        pe = (c0[0] + d[0] * t_exit, c0[1] + d[1] * t_exit)
        ps = (c0[0] + d[0] * t_enter, c0[1] + d[1] * t_enter)
        straight_arrow(ax, pe, ps, color=fam["edge"], lw=2.0,
                       rad=arrow_rad, arrowstyle="<|-|>", mutation_scale=16)
        # 数据流名: 放在弧线背侧（-n 法向）。figqa 按 patch 矩形 bbox 判重叠,
        # 偏移量需盖过"弧顶+箭头翼"半包络 + 文字盒在法向上的投影半宽, 自适应计算
        flow = modules[i][3]
        chord = math.hypot(ps[0] - pe[0], ps[1] - pe[1])
        bbox_half_u = max(arrow_rad * chord, 16.0 / 2) + 1.5
        hw = text_width_px(flow, FLOW_FS) / 2 + 2.0   # 水平文字半宽
        hh = FLOW_FS * 1.45 / 2                       # 水平文字半高
        proj_u = abs(d[1]) * hw + abs(d[0]) * hh      # 文字盒投影到法向 u 的半延展
        offset = bbox_half_u + proj_u + 3.0
        mid = ((pe[0] + ps[0]) / 2 + offset * d[1],
               (pe[1] + ps[1]) / 2 - offset * d[0])
        ax.text(mid[0], mid[1], flow, ha="center", va="center",
                fontsize=FLOW_FS, color=load_neutral("secondary"), zorder=6)

    for w in warnings:
        print(f"[警告] {w}")

    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / "make_diagram_module")
    written = [Path(p) for p in save_fig(fig, out_stem)]
    return written[0], written[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="生成模块化功能框图（示例数据, 4-6 个卫星模块）"
    )
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    try:
        png, svg = plot_module(MODULES, out_stem=args.out)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    print(f"已输出: {png}")
    print(f"已输出: {svg}")
    print(f"已输出: {png.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
