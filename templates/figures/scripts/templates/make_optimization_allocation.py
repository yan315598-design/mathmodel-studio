# -*- coding: utf-8 -*-
"""优化分配结果图模板: 堆叠条（资源构成）与甘特（时序排产）双模式。

academic_blue 色板（中文竞赛主战色系）。

用法（二选一）:
    1. 独立运行:
       python make_optimization_allocation.py [--mode stacked|gantt] [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录（gitignore 友好）, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 ALLOCATION / GANTT 数据与 plot_*() 入参。

约定:
    - 1.1.0: 迁移 figkit + 三格式导出 + 中性色令牌。
    - 样式与色板统一经 scripts/figkit.py 加载（mathmodel.mplstyle + palettes.py,
      两者缺失时 figkit 内置等价内联回退）; 堆叠条网格走 figkit.ygrid() 仅 y 向,
      甘特图按读数方向保留 x 向网格（见 plot_gantt 内注释）。

退出码: 0 成功; 2 参数/IO 错误。
"""

from __future__ import annotations

import argparse
import math
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

# ---- 1.1.0: 头部统一走共享库 figkit（样式/色板/导出/网格）----
# figkit.py 位于本脚本上二级 scripts/ 目录; 色板回退已内置于 figkit, 不再保留本文件副本
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    apply_style,
    load_neutral,
    load_palette,
    save_fig,
    ygrid,
)

# 堆叠条模式示例数据: 各决策单元的资源类别分配量
ALLOCATION: dict[str, list[float]] = {
    "单元": ["中心仓 A", "中心仓 B", "前置仓 C", "前置仓 D", "应急仓 E"],
    "日常补货": [42, 35, 28, 22, 12],
    "促销增量": [18, 12, 15, 9, 6],
    "安全储备": [10, 14, 8, 12, 20],
    "应急预留": [5, 4, 6, 7, 8],
}

# 甘特模式示例数据: (任务, 起始天, 持续天数, 资源类别)
GANTT: list[tuple[str, float, float, str]] = [
    ("需求预测", 0, 2, "日常补货"),
    ("库存盘点", 1, 3, "安全储备"),
    ("干线调拨", 2, 4, "日常补货"),
    ("促销铺货", 6, 3, "促销增量"),
    ("应急演练", 9, 2, "应急预留"),
    ("复盘结算", 11, 2, "安全储备"),
]


def _check_finite(values, label: str) -> None:
    """数值序列必须全为有限数值（排除 NaN/inf 与非数值）, 否则 ValueError 中文报错。"""
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{label} 含非有限数值或非数值: {v!r}")


def plot_stacked(allocation: dict[str, list[float]], out_stem: str | None = None,
                 unit: str = "吨") -> tuple[Path, Path]:
    """堆叠条模式: x=决策单元, 分段=资源类别, 顶部标总量。

    Raises:
        ValueError: '单元' 列表为空 / 无资源类别列 / 类别序列长度与单元数
            不一致（zip 会静默截断）/ 数值非有限。
    """
    units = allocation.get("单元")
    if not units:
        raise ValueError("allocation 缺少非空的 '单元' 列表")
    categories = [k for k in allocation if k != "单元"]
    if not categories:
        raise ValueError("allocation 缺少资源类别数据（除 '单元' 外至少一列）")
    for cat in categories:
        values = allocation[cat]
        if not isinstance(values, (list, tuple)):
            raise ValueError(f"类别 {cat!r} 必须是数值列表, 实际: {type(values).__name__}")
        if len(values) != len(units):
            raise ValueError(
                f"类别 {cat!r} 长度 {len(values)} 与单元数 {len(units)} 不一致"
                f"（zip 会静默截断）"
            )
        _check_finite(values, f"类别 {cat!r}")

    apply_style()
    colors = load_palette("academic_blue")
    units = allocation["单元"]
    categories = [k for k in allocation if k != "单元"]
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    bottoms = [0.0] * len(units)
    for cat, color in zip(categories, colors):
        values = allocation[cat]
        ax.bar(units, values, bottom=bottoms, label=cat, color=color,
               edgecolor="white", linewidth=0.6, width=0.58)
        bottoms = [b + v for b, v in zip(bottoms, values)]
    for x, total in zip(range(len(units)), bottoms):
        ax.text(x, total + max(bottoms) * 0.02, f"{total:.0f}",
                ha="center", va="bottom", fontsize=10)
    ax.set_ylabel(f"分配量（{unit}）")
    ax.set_ylim(0, max(bottoms) * 1.12)
    ygrid(ax)  # 1.1.0: 堆叠条只留极淡 y 向网格
    # 1.4.1 图题纪律: 图名与结论写进论文 caption, 不烘焙进图内
    ax.legend(loc="upper right", ncol=2)
    return _save(fig, out_stem, "make_optimization_allocation_stacked")


def plot_gantt(tasks: list[tuple[str, float, float, str]],
               out_stem: str | None = None) -> tuple[Path, Path]:
    """甘特模式: y=任务, x=时间, 颜色=资源类别（broken_barh）。

    Raises:
        ValueError: tasks 为空 / 行不是四元组 / 任务名为空 / 起始或持续
            时间非有限数值 / 持续时间为负。
    """
    if not tasks:
        raise ValueError("tasks 不能为空: 至少提供一条 (任务, 起始天, 持续天数, 资源类别) 记录")
    for task in tasks:
        if len(task) != 4:
            raise ValueError(f"tasks 每条必须是 (任务, 起始, 持续, 类别) 四元组, 实际: {task!r}")
        name, start, duration, _cat = task
        if not str(name).strip():
            raise ValueError(f"任务名不能为空: {task!r}")
        _check_finite((start, duration), f"任务 {name!r} 的起始/持续时间")
        if duration < 0:
            raise ValueError(f"任务 {name!r} 持续时间为负: {duration}")

    apply_style()
    colors = load_palette("academic_blue")
    cat_names = []
    for _, _, _, cat in tasks:
        if cat not in cat_names:
            cat_names.append(cat)
    cat_color = {cat: colors[i % len(colors)] for i, cat in enumerate(cat_names)}

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    names = [t[0] for t in tasks]
    for yi, (name, start, duration, cat) in enumerate(tasks):
        # broken_barh 的 y 以条底为基准, 统一减 0.3 使条带以任务刻度为中心
        ax.broken_barh([(start, duration)], (yi - 0.3, 0.6),
                       facecolors=cat_color[cat], edgecolor="white")
        ax.text(start + duration + 0.15, yi, f"{duration:.0f} 天",
                va="center", ha="left", fontsize=9)
    ax.set_yticks(range(len(names)), names)
    ax.set_xlabel("执行时间（天）")
    ax.set_xlim(0, max(s + d for _, s, d, _ in tasks) + 3)
    # 甘特图为读数导向图: 按令牌保留 x 向网格读时间, 关闭 y 向（任务行自有条带分隔）
    ax.xaxis.grid(True, color=load_neutral("grid"), alpha=0.45, linewidth=0.7)
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)
    # 1.4.1 图题纪律: 图名与结论写进论文 caption, 不烘焙进图内
    from matplotlib.patches import Patch

    ax.legend(
        handles=[Patch(facecolor=cat_color[c], label=c) for c in cat_names],
        loc="lower right",
    )
    return _save(fig, out_stem, "make_optimization_allocation_gantt")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """1.1.0 经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成优化分配结果图（示例数据）")
    parser.add_argument("--mode", choices=["stacked", "gantt"], default="stacked",
                        help="stacked=资源构成堆叠条（默认）, gantt=执行计划甘特图")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    try:
        if args.mode == "gantt":
            png, svg = plot_gantt(GANTT, out_stem=args.out)
        else:
            png, svg = plot_stacked(ALLOCATION, out_stem=args.out)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    print(f"已输出: {png}")
    print(f"已输出: {svg}")
    print(f"已输出: {png.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
