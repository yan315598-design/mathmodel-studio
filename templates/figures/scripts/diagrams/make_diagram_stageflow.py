# -*- coding: utf-8 -*-
"""横向阶段流水线图（示意图模板包 · stageflow, v7.8.0 示意图色族版）。

4-6 个阶段框在画布中部等距排开, 框间画粗箭头表示流转方向; 每框上方
一个圆形编号徽章（1/2/3...）, 框下方一行说明文字。阶段族序取
DIAGRAM_ORDER_GENERIC: 阶段框 = 实色标题条样式（族 header 底 +
header_stroke 描边 + 白色加粗字）, 编号徽章 = 族 chevron 底 + 族 stroke
描边 + 墨黑加粗字, 框下说明 = 无框墨黑加粗, 框间箭头 = 左侧阶段族 edge
色。--highlight 把第 N 阶段（1 起编号）的描边改族 accent 并加粗到 2.0
（不再叠数据色板的橙色强调）。

确定性布局: 画布逻辑坐标 = 像素（dpi=100）, 画布宽随阶段数自动伸缩, 画布
高按内容实际底部（最高说明块）+ 少量 padding 自顶向下推导（v7.8.0 修复
底部大片空白带）, 中文字宽估算换行, 不依赖任何 GUI/字体测量, 输出可复现。
阶段名/说明过长时自动缩小字号（下限 8.5/7.5pt）, 仍放不下打印 [警告] 溢出
提示。

用法（二选一）:
    1. 独立运行:
       python make_diagram_stageflow.py [--out 输出前缀] [--highlight 阶段编号]
       不给 --out 时示例图写入系统临时目录, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 STAGES 数据。

版本:
    v7.8.0: 迁移示意图色族体系——阶段框改实色标题条样式, 徽章改族
        chevron 底墨黑字, 说明文字墨黑加粗, --highlight 改族 accent 描边
        （弃 academic_blue 深底白字 + 橙色数据色强调）。
    v7.7.0: 迁移 figkit + 三格式导出 + 中性色令牌。

质量门:
    python scripts/figqa.py templates/figures/scripts/diagrams/make_diagram_stageflow.py \\
        --strict --allow-box-labels   （盒内标签/徽章为有意版式）

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
from matplotlib.patches import Circle, FancyBboxPatch

# ---- v7.8.0: 头部统一走共享库 figkit（样式/色族/导出/换行）----
# figkit.py 位于本脚本上级 scripts/ 目录; 色族回退已内置于 figkit
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    apply_style,
    load_diagram_families,
    load_diagram_page,
    load_neutral,
    save_fig,
    use_diagram_font,
    wrap_text_balanced,
)

# 示例数据: (阶段名, 框下一句说明); 支持 4-6 个阶段
STAGES: list[tuple[str, str]] = [
    ("问题分析", "解读题目背景, 提炼目标函数与硬约束"),
    ("数据处理", "清洗异常值, 完成填补、标准化与特征构造"),
    ("模型构建", "搭建多目标主模型并刻画参数不确定性"),
    ("算法求解", "精确/启发式组合求解, 输出 Pareto 方案集"),
    ("验证应用", "稳健性检验与灵敏度分析, 给出决策建议"),
]

# 画布逻辑坐标 = 像素（dpi=100）; matplotlib 字号以 pt 计, 1pt = 100/72 px
# 文本宽度/换行统一走 figkit.wrap_text_balanced（CJK 感知 + 均衡断行防吊行）
LINE_PITCH = 1.36    # 行距系数: 实际行距 ≈ 字号×1.317×行距参数, 留余量

STAGE_BOX_H = 84.0
STAGE_W = 168.0
ARROW_GAP = 60.0
BADGE_R = 15.0
# 画布高不再用固定常量: plot_stageflow 内按标题/徽章/框/说明块实际高度推导
TITLE_FS = 16.0
NAME_FS, NAME_FS_MIN = 11.5, 8.5
CAP_FS, CAP_FS_MIN = 9.0, 7.5


def _fit_to_box(text: str, max_w: float, fs: float, fs_min: float,
                box_h: float, line_spacing: float, warn_ctx: str,
                warnings: list[str]) -> tuple[list[str], float]:
    """换行 + 溢出缩小字号兜底, 以盒高为准; 缩到下限仍超高时打 [警告]。"""
    pitch = LINE_PITCH * line_spacing
    lines = wrap_text_balanced(text, max_w, fs)
    while len(lines) * fs * pitch > box_h and fs > fs_min:
        fs = max(fs - 0.5, fs_min)
        lines = wrap_text_balanced(text, max_w, fs)
    if len(lines) * fs * pitch > box_h:
        warnings.append(
            f"{warn_ctx} 文字过长: 缩至最小字号 {fs_min:.1f}pt 后仍超高, "
            f"建议精简文案"
        )
    return lines, fs


def plot_stageflow(stages: list[tuple[str, str]],
                   highlight: int | None = None,
                   out_stem: str | None = None,
                   title: str = "研究阶段流程") -> tuple[Path, Path]:
    """绘制横向阶段流水线图并保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        stages: 4-6 条 (阶段名, 说明文字)。
        highlight: 1 起编号的当前/关键阶段; None 不强调。
        out_stem: 输出文件前缀; None 时写系统临时目录。
        title: 图标题。

    Raises:
        ValueError: stages 数不在 [4,6] / 行不是二元组 / 阶段名或说明为空 /
            highlight 越界。
    """
    if not 4 <= len(stages) <= 6:
        raise ValueError(f"横向阶段流水线图需要 4-6 个阶段, 实际 {len(stages)} 个")
    for stage in stages:
        if len(stage) != 2:
            raise ValueError(f"stages 每条必须是 (阶段名, 说明) 二元组, 实际: {stage!r}")
        name, caption = stage
        if not str(name).strip():
            raise ValueError(f"阶段名不能为空: {stage!r}")
        if not str(caption).strip():
            raise ValueError(f"阶段 {name!r} 的说明文字为空")
    if highlight is not None and not 1 <= highlight <= len(stages):
        raise ValueError(f"--highlight 需在 1..{len(stages)} 之间, 实际 {highlight}")

    warnings: list[str] = []
    apply_style()
    use_diagram_font()
    fams = load_diagram_families(n=len(stages))   # DIAGRAM_ORDER_GENERIC 前 n 族
    ink = load_diagram_page("ink")

    n = len(stages)
    margin = 36.0
    CANVAS_W = 2 * margin + n * STAGE_W + (n - 1) * ARROW_GAP
    centers = [margin + STAGE_W / 2 + i * (STAGE_W + ARROW_GAP) for i in range(n)]
    name_max_w = STAGE_W - 2 * 12.0
    cap_max_w = STAGE_W - 6.0
    box_h = STAGE_BOX_H

    # 说明文字先换行定高（画布高度取决于最高说明块, 须在建图前算好）。
    # 画布高按内容自顶向下推导（消灭底部空白带）:
    #   标题中心(30) → 徽章中心(再 64) → 阶段框中心(再 76 = 框半高 42 + 间距 34)
    #   → 框底 + 14 间距 → 说明块(实际高) → 底部 34 padding
    cap_fit: list[tuple[list[str], float]] = []
    for i, (_name, caption) in enumerate(stages):
        cap_fit.append(_fit_to_box(caption, cap_max_w, CAP_FS, CAP_FS_MIN,
                                   100.0, 1.35, f"阶段 {i + 1} 说明", warnings))
    cap_block_h = max(len(lines) * fs * LINE_PITCH * 1.35 for lines, fs in cap_fit)
    TITLE_DROP = 30.0       # 标题中心距画布顶
    TITLE_TO_BADGE = 64.0   # 标题中心 → 徽章中心（沿原版间距）
    BADGE_TO_BOX = 76.0     # 徽章中心 → 阶段框中心（沿原版间距）
    CAP_GAP = 14.0          # 阶段框底 → 说明文字块顶
    BOTTOM_PAD = 34.0
    CANVAS_H = (TITLE_DROP + TITLE_TO_BADGE + BADGE_TO_BOX + box_h / 2
                + CAP_GAP + cap_block_h + BOTTOM_PAD)
    title_y = CANVAS_H - TITLE_DROP
    badge_cy = CANVAS_H - TITLE_DROP - TITLE_TO_BADGE
    cy = badge_cy - BADGE_TO_BOX           # 阶段框中心纵坐标
    cap_bottom = cy - box_h / 2 - CAP_GAP  # 说明块顶边（y 向上坐标系）

    fig = plt.figure(figsize=(CANVAS_W / 100.0, CANVAS_H / 100.0), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CANVAS_W)
    ax.set_ylim(0, CANVAS_H)
    ax.axis("off")
    ax.text(CANVAS_W / 2, title_y, title, ha="center", va="center",
            fontsize=TITLE_FS, fontweight="bold", color=ink)

    # 阶段框（实色标题条样式: 族 header 底 + header_stroke 描边 + 白色加粗字）:
    # 高亮阶段描边改族 accent 并加粗到 2.0; 整盒单层填色, 不叠色不加阴影
    for i, (name, _caption) in enumerate(stages):
        is_hl = highlight is not None and i == highlight - 1
        lines, fs = _fit_to_box(name, name_max_w, NAME_FS, NAME_FS_MIN,
                                box_h - 12.0, 1.45, f"阶段 {i + 1} 名称", warnings)
        patch = FancyBboxPatch(
            (centers[i] - STAGE_W / 2, cy + box_h / 2 - box_h), STAGE_W, box_h,
            boxstyle="round,pad=2,rounding_size=10",
            facecolor=fams[i]["header"],
            edgecolor=fams[i]["accent"] if is_hl else fams[i]["header_stroke"],
            linewidth=2.0 if is_hl else 1.2,
        )
        ax.add_patch(patch)
        ax.text(centers[i], cy, "\n".join(lines), ha="center", va="center",
                fontsize=fs, color=load_diagram_page("white"), fontweight="bold",
                linespacing=1.45, zorder=5)

    # 编号徽章（圆形）: 族 chevron 底 + 族 stroke 描边 + 墨黑加粗字
    for i in range(n):
        ax.add_patch(Circle((centers[i], badge_cy), BADGE_R,
                            facecolor=fams[i]["chevron"],
                            edgecolor=fams[i]["stroke"], linewidth=1.2, zorder=4))
        ax.text(centers[i], badge_cy, str(i + 1), ha="center", va="center",
                fontsize=11.5, color=ink, fontweight="bold", zorder=5)

    # 框间箭头（阶段框中线高度; 取左侧阶段的族 edge 色; v7.9.1 降重:
    # 连线退居二线, lw 1.6 + 小箭头头, 强调用色不用粗）
    for i in range(n - 1):
        ax.annotate(
            "",
            xy=(centers[i + 1] - STAGE_W / 2, cy),
            xytext=(centers[i] + STAGE_W / 2, cy),
            arrowprops=dict(arrowstyle="-|>", color=fams[i]["edge"], lw=1.6,
                            shrinkA=0, shrinkB=0, mutation_scale=13),
        )

    # 框下说明文字（不落色块; v7.9.1 字重层级制: 说明文字常规字重 + 次级色,
    # 行距 1.35 紧凑排版, 用建图前算好的行)
    for i, (lines, fs) in enumerate(cap_fit):
        h = len(lines) * fs * LINE_PITCH * 1.35
        ax.text(centers[i], cap_bottom - h / 2, "\n".join(lines),
                ha="center", va="center", fontsize=fs,
                color=load_neutral("secondary"),
                linespacing=1.35, zorder=5)

    for w in warnings:
        print(f"[警告] {w}")

    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / "make_diagram_stageflow")
    written = [Path(p) for p in save_fig(fig, out_stem)]
    return written[0], written[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="生成横向阶段流水线图（示例数据, 4-6 阶段）"
    )
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    parser.add_argument("--highlight", type=int, default=None, metavar="N",
                        help="把第 N 个阶段（1 起）描边改族 accent 并加粗到 2.0")
    args = parser.parse_args(argv)
    try:
        png, svg = plot_stageflow(STAGES, highlight=args.highlight, out_stem=args.out)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    print(f"已输出: {png}")
    print(f"已输出: {svg}")
    print(f"已输出: {png.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
