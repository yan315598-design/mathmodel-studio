# -*- coding: utf-8 -*-
"""draw.io 横向任务流水线图（drawio 模板包 · stageflow, 1.2.0 族化版）。

与 matplotlib 版 make_diagram_stageflow.py 同信息架构, 用 drawio 语言重写:
4-6 个阶段框等距横排（实色标题条样式: 族 header 底 + header_stroke 描边 +
白色加粗字, 族序取 DIAGRAM_ORDER_GENERIC）, 框上方圆形编号徽章（族 chevron
浅底 + 族 stroke 描边 + 墨黑加粗字）, 框间粗箭头（左侧阶段族 edge 色）,
框下方墨黑加粗说明文字。--highlight 把第 N 阶段（1 起）的描边改族 accent
并加粗到 2.0（不再叠数据色板的橙色强调）。输出 .drawio, draw.io 桌面版/
网页版打开即编辑。

确定性布局: 页面坐标原点左上、y 向下; 页宽随阶段数伸缩, 中文字宽估算
均衡换行, 超宽自动缩字号（阶段名下限 8.5pt / 说明下限 8pt）, 仍放不下
打印 [警告]。

用法:
    python make_drawio_stageflow.py --out 输出前缀 [--palette academic_blue]
        [--stages 5] [--highlight N]
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
    DIAGRAM_INK, Diagram, base_parser, block_height, finalize, fit_text,
    get_diagram_families, get_palette, label_html,
)

# 示例数据: (阶段名, 框下一句说明); 4-6 个阶段
DEMO_STAGES: list[tuple[str, str]] = [
    ("问题分析", "解读题目背景, 提炼目标函数与硬约束"),
    ("数据处理", "清洗异常值, 完成填补、标准化与特征构造"),
    ("模型构建", "搭建多目标主模型并刻画参数不确定性"),
    ("算法求解", "精确/启发式组合求解, 输出 Pareto 方案集"),
    ("验证应用", "稳健性检验与灵敏度分析, 给出决策建议"),
]

# 页面几何（px, y 向下; 页边距 >= 40）
MARGIN = 40.0
STAGE_W = 168.0
ARROW_GAP = 60.0       # 框间连线通道宽
STAGE_BOX_H = 84.0
BADGE_D = 30.0         # 圆形编号徽章直径
TITLE_ZONE = 74.0      # 标题区
BADGE_GAP = 22.0       # 徽章与阶段框间距
CAP_GAP = 14.0         # 说明文字与阶段框间距
BOTTOM_PAD = 44.0
NAME_FS, NAME_FS_MIN = 11.5, 8.5
CAP_FS, CAP_FS_MIN = 9.0, 8.0
ARROW_STROKE_W = 3.2


def _demo_stages(count: int) -> list[tuple[str, str]]:
    """由 demo 数据推导指定阶段数; 超出部分用可编辑占位。"""
    stages = DEMO_STAGES[:count]
    while len(stages) < count:
        stages.append(("补充阶段", "双击编辑: 补充本阶段说明"))
    return stages


def build_stageflow(stages: list[tuple[str, str]],
                    highlight: int | None = None,
                    palette: str = "academic_blue",
                    title_text: str = "研究阶段流程") -> Diagram:
    """构建横向任务流水线的 Diagram（不落盘）。

    Args:
        stages: 4-6 条 (阶段名, 说明文字)。
        highlight: 1 起编号的强调阶段; None 不强调。
        palette: 色板名。
        title_text: 图标题。

    Raises:
        ValueError: 阶段数/行结构/空文本/highlight 越界, 或色板名未知。
    """
    if not 4 <= len(stages) <= 6:
        raise ValueError(f"横向流水线需要 4-6 个阶段, 实际 {len(stages)} 个")
    for i, stage in enumerate(stages):
        if len(stage) != 2:
            raise ValueError(f"stages 第 {i + 1} 项必须是 (阶段名, 说明) "
                             f"二元组, 实际: {stage!r}")
        name, caption = stage
        if not str(name).strip():
            raise ValueError(f"第 {i + 1} 个阶段名为空")
        if not str(caption).strip():
            raise ValueError(f"阶段 {name!r} 的说明文字为空")
    if highlight is not None and not 1 <= highlight <= len(stages):
        raise ValueError(f"--highlight 需在 1..{len(stages)} 之间, 实际 {highlight}")

    get_palette(palette)   # 兼容校验: --palette 仍须是已注册色板名
    fams = get_diagram_families(n=len(stages))   # DIAGRAM_ORDER_GENERIC 前 n 族
    warnings: list[str] = []
    n = len(stages)
    canvas_w = 2 * MARGIN + n * STAGE_W + (n - 1) * ARROW_GAP

    # 说明文字先换行（决定画布高度）
    cap_lines: list[list[str]] = []
    cap_fs: list[float] = []
    for i, (_name, caption) in enumerate(stages):
        lines, fs = fit_text(caption, STAGE_W - 6.0, CAP_FS, CAP_FS_MIN,
                             max_lines=4, pitch=1.35, pad=8,
                             ctx=f"阶段 {i + 1} 说明", warnings=warnings)
        cap_lines.append(lines)
        cap_fs.append(fs)
    badge_y = TITLE_ZONE
    box_y = badge_y + BADGE_D + BADGE_GAP
    cap_y = box_y + STAGE_BOX_H + CAP_GAP
    cap_h = max(block_height(len(lines), fs, pitch=1.35, pad=8)
                for lines, fs in zip(cap_lines, cap_fs))
    canvas_h = cap_y + cap_h + BOTTOM_PAD

    d = Diagram(page_width=canvas_w, page_height=canvas_h, name="阶段流程")
    d.title("title", title_text, 40, 18, canvas_w - 80, 34)

    centers = [MARGIN + STAGE_W / 2 + i * (STAGE_W + ARROW_GAP) for i in range(n)]

    # 1) 阶段框（实色标题条: 族 header 底 + header_stroke 描边 + 白色加粗字;
    #    高亮阶段描边改族 accent 并加粗到 2.0, 每图至多一处）
    for i, (name, _caption) in enumerate(stages):
        is_hl = highlight is not None and i == highlight - 1
        lines, fs = fit_text(name, STAGE_W - 2 * 12.0, NAME_FS, NAME_FS_MIN,
                             max_h=STAGE_BOX_H - 12, ctx=f"阶段 {i + 1} 名称",
                             warnings=warnings)
        d.header_bar(f"stage{i + 1}_box", label_html(lines),
                     centers[i] - STAGE_W / 2, box_y, STAGE_W, STAGE_BOX_H,
                     family=fams[i], font_size=fs,
                     stroke=fams[i]["accent"] if is_hl else None,
                     stroke_width=2.0 if is_hl else 1.2)

    # 2) 圆形编号徽章（框上方; 族 chevron 浅底 + 族 stroke 描边 + 墨黑加粗字）
    for i in range(n):
        d.badge(f"stage{i + 1}_badge", str(i + 1),
                centers[i] - BADGE_D / 2, badge_y, BADGE_D, BADGE_D,
                family=fams[i], shape="ellipse", font_size=11.5)

    # 3) 框间粗箭头（阶段框中线高度, 左缘 → 右缘; 取左侧阶段族 edge 色）
    for i in range(n - 1):
        d.edge(f"stage{i + 1}_box", f"stage{i + 2}_box",
               exit_dir="right", entry_dir="left",
               stroke=fams[i]["edge"], stroke_width=ARROW_STROKE_W)

    # 4) 框下说明文字（无框文本, 墨黑加粗, 不落色块）
    for i in range(n):
        d.text(f"stage{i + 1}_caption", label_html(cap_lines[i]),
               centers[i] - STAGE_W / 2, cap_y, STAGE_W, cap_h,
               font_size=cap_fs[i], color=DIAGRAM_INK, bold=True)

    for w in warnings:
        print(f"[警告] {w}")
    return d


def main(argv: list[str] | None = None) -> int:
    parser: argparse.ArgumentParser = base_parser(
        "生成 draw.io 横向任务流水线图（示例数据, 输出可编辑 .drawio）")
    parser.add_argument("--stages", type=int, default=5, metavar="N",
                        help="阶段数, 4-6, 默认 5（超出示例部分用占位）")
    parser.add_argument("--highlight", type=int, default=None, metavar="N",
                        help="把第 N 个阶段（1 起）描边改族 accent 并加粗到 2.0")
    args = parser.parse_args(argv)
    if not 4 <= args.stages <= 6:
        print(f"[参数错误] --stages 需在 4..6 之间, 实际 {args.stages}")
        return 2
    try:
        diagram = build_stageflow(_demo_stages(args.stages),
                                  highlight=args.highlight, palette=args.palette)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    return finalize(diagram, args.out, "make_drawio_stageflow")


if __name__ == "__main__":
    sys.exit(main())
