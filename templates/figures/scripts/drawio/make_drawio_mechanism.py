# -*- coding: utf-8 -*-
"""draw.io 机理示意图（drawio 模板包 · mechanism, 闭环反馈/仓室模型骨架,
1.2.0 族化版）。

中心主体大框（grey 族 accent 浅底 + header_stroke 描边 + 墨黑加粗字）+
4-6 个环绕要素卡片呈椭圆环等角排布（每要素一族, 族序取
DIAGRAM_ORDER_GENERIC; 族 fill 浅底 + 族 stroke 描边）, 中心与要素之间
双向正交连线并带数据流标签（要素族 edge 色）; 末要素 → 首要素一条虚线
"闭环反馈"连线沿环外侧锚定, 构成通用闭环/仓室机理骨架。输出 .drawio,
draw.io 桌面版/网页版打开即编辑。

确定性布局: 页面坐标原点左上、y 向下; 环半径/画布尺寸按要素数固定推导,
中文字宽估算均衡换行, 超宽自动缩字号（下限 8.5pt）, 仍放不下打印 [警告]。

用法:
    python make_drawio_mechanism.py --out 输出前缀 [--palette academic_blue]
        [--modules 4]
    不给 --out 时示例图写入系统临时目录, 产出 <前缀>.drawio。

退出码: 0 成功; 2 参数/数据错误。
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from drawio_builder import (  # noqa: E402
    DIAGRAM_INK, Diagram, base_parser, block_height, finalize, fit_text,
    get_diagram_family, get_diagram_families, get_palette, label_html,
    neutral,
)

# 示例数据: 中心主体文本行 与 环绕要素 (要素名, 与中心的数据流名)
DEMO_CENTER: list[str] = ["组合优化总模型", "多源输入融合 · 多目标方案寻优"]
DEMO_MODULES: list[tuple[str, str]] = [
    ("数据预处理", "样本集"),
    ("需求预测", "预测序列"),
    ("调度寻优", "可行方案"),
    ("评估反馈", "评估反馈"),
]
_CN_NUMS = ["一", "二", "三", "四", "五", "六"]

# 页面几何（px, y 向下; 页边距 >= 40）
MARGIN_X = 40.0
RX, RY = 430.0, 250.0           # 环半轴（水平/垂直）
CENTER_W, CENTER_H = 340.0, 150.0
SAT_W, SAT_H = 240.0, 84.0
TITLE_ZONE = 76.0
RING_PAD = 8.0
BOTTOM_PAD = 44.0
SAT_FS, SAT_FS_MIN = 11.0, 8.5
CENTER_FS, CENTER_FS_MIN = 13.0, 10.5
FLOW_FS = 9.0


def _outward_dir(angle_deg: float) -> str:
    """环上某角度的朝外方向（left/right/up/down）, 供闭环连线外缘锚定。"""
    rad = math.radians(angle_deg)
    c, s = math.cos(rad), math.sin(rad)   # s>0 在环上方（y 向下坐标系）
    if abs(c) >= abs(s):
        return "right" if c > 0 else "left"
    return "up" if s > 0 else "down"


def _demo_modules(count: int) -> list[tuple[str, str]]:
    """由 demo 数据推导指定要素数; 超出部分用可编辑占位。"""
    modules = DEMO_MODULES[:count]
    for i in range(len(DEMO_MODULES), count):
        cn = _CN_NUMS[i] if i < len(_CN_NUMS) else str(i + 1)
        modules.append((f"补充要素{cn}", "关联数据流"))
    return modules


def build_mechanism(modules: list[tuple[str, str]],
                    center_lines: list[str] | None = None,
                    palette: str = "academic_blue",
                    title_text: str = "组合模型机理结构") -> Diagram:
    """构建机理示意图（中心主体 + 环绕要素 + 双向数据流 + 闭环反馈）的 Diagram。

    Args:
        modules: 4-6 条 (要素名, 与中心的数据流名)。
        center_lines: 中心主体文本 1-2 行; None 用模块级 DEMO_CENTER。
        palette: 色板名。
        title_text: 图标题。

    Raises:
        ValueError: 要素数/行结构/空文本不合法, 或色板名未知。
    """
    if not 4 <= len(modules) <= 6:
        raise ValueError(f"机理示意图需要 4-6 个环绕要素, 实际 {len(modules)} 个")
    for i, module in enumerate(modules):
        if len(module) != 2:
            raise ValueError(f"modules 第 {i + 1} 项必须是 (要素名, 数据流名) "
                             f"二元组, 实际: {module!r}")
        for field in module:
            if not str(field).strip():
                raise ValueError(f"要素 {module!r} 存在空字段")
    center = center_lines if center_lines is not None else DEMO_CENTER
    if not 1 <= len(center) <= 2 or any(not str(ln).strip() for ln in center):
        raise ValueError("center_lines 需 1-2 行非空文本")

    get_palette(palette)   # 兼容校验: --palette 仍须是已注册色板名
    center_fam = get_diagram_family("grey")
    sat_fams = get_diagram_families(n=len(modules))   # GENERIC 序每要素一族
    warnings: list[str] = []
    k = len(modules)
    half_w = RX + SAT_W / 2 + MARGIN_X
    canvas_w = 2 * half_w
    cx = canvas_w / 2
    cy = TITLE_ZONE + RY + SAT_H / 2 + RING_PAD
    canvas_h = TITLE_ZONE + 2 * RY + SAT_H + 2 * RING_PAD + BOTTOM_PAD

    d = Diagram(page_width=canvas_w, page_height=canvas_h, name="机理示意图")
    d.title("title", title_text, 40, 18, canvas_w - 80, 34)

    # 1) 环绕要素卡片（椭圆环等角排布, 0 号在正上方; 族 fill 浅底 + 族 stroke 描边）
    angles = [90.0 - i * 360.0 / k for i in range(k)]
    sat_ids = [f"module{i + 1}" for i in range(k)]
    for i, (name, _flow) in enumerate(modules):
        ang = math.radians(angles[i])
        sx = cx + RX * math.cos(ang)
        sy = cy - RY * math.sin(ang)          # y 向下: sin>0 在上方
        lines, fs = fit_text(name, SAT_W - 2 * 14.0, SAT_FS, SAT_FS_MIN,
                             max_h=SAT_H - 12, ctx=f"要素 {name!r}",
                             warnings=warnings)
        d.card(sat_ids[i], label_html(lines), sx - SAT_W / 2, sy - SAT_H / 2,
               SAT_W, SAT_H, font_size=fs, family=sat_fams[i],
               stroke_width=1.6)

    # 2) 中心主体大框（grey 族 accent 浅底 + header_stroke 描边 + 墨黑加粗字）
    c_lines: list[str] = []
    c_fs = CENTER_FS
    for ln in center:
        lines, c_fs = fit_text(ln, CENTER_W - 2 * 20.0, CENTER_FS,
                               CENTER_FS_MIN, max_lines=2,
                               ctx=f"中心文本 {ln!r}", warnings=warnings)
        c_lines.extend(lines)
    d.card("center", label_html(c_lines), cx - CENTER_W / 2, cy - CENTER_H / 2,
           CENTER_W, CENTER_H, font_size=c_fs,
           fill=center_fam["accent"], stroke=center_fam["header_stroke"],
           text_color=DIAGRAM_INK, bold=True)

    # 3) 中心 ↔ 要素 双向数据流连线（带标签, 要素族 edge 色）
    for i, (_name, flow) in enumerate(modules):
        d.edge("center", sat_ids[i], label=flow, stroke=sat_fams[i]["edge"],
               bidirectional=True, font_size=FLOW_FS)

    # 4) 闭环反馈: 末要素 → 首要素, 虚线沿环外侧锚定（不入中心区）
    d.edge(sat_ids[-1], sat_ids[0], label="闭环反馈", dashed=True,
           stroke=neutral("faint"),
           exit_dir=_outward_dir(angles[-1]), entry_dir=_outward_dir(angles[0]))

    for w in warnings:
        print(f"[警告] {w}")
    return d


def main(argv: list[str] | None = None) -> int:
    parser: argparse.ArgumentParser = base_parser(
        "生成 draw.io 机理示意图（中心 + 环绕要素 + 闭环反馈, 输出可编辑 .drawio）")
    parser.add_argument("--modules", type=int, default=4, metavar="N",
                        help="环绕要素数, 4-6, 默认 4（超出示例部分用占位）")
    args = parser.parse_args(argv)
    if not 4 <= args.modules <= 6:
        print(f"[参数错误] --modules 需在 4..6 之间, 实际 {args.modules}")
        return 2
    try:
        diagram = build_mechanism(_demo_modules(args.modules),
                                  palette=args.palette)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    return finalize(diagram, args.out, "make_drawio_mechanism")


if __name__ == "__main__":
    sys.exit(main())
