# -*- coding: utf-8 -*-
"""灵敏度龙卷风图模板: 参数 ±扰动 对输出指标的影响, 水平条按灵敏度排序。

发散色 RdBu_r 语义: 负向影响偏蓝、正向影响偏红, 零线居中。

用法（二选一）:
    1. 独立运行:
       python make_tornado_sensitivity.py [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录（gitignore 友好）, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 PARAMS/plot_tornado() 的输入数据。

约定:
    - 1.1.0: 迁移 figkit + 三格式导出 + 中性色令牌。
    - 样式与色板统一经 scripts/figkit.py 加载（mathmodel.mplstyle + palettes.py,
      两者缺失时 figkit 内置等价内联回退）; 发散色经 figkit.get_cmap("diverging"),
      横向条读数方向在 x, 保留 x 向网格。

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

# ---- 1.1.0: 头部统一走共享库 figkit（样式/色板/导出/colormap 语义/中性色）----
# figkit.py 位于本脚本上二级 scripts/ 目录; 色板回退已内置于 figkit, 不再保留本文件副本
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    apply_style,
    get_cmap,
    load_neutral,
    restore_style_on_error,
    save_fig,
)

# 示例数据: (参数名, -10% 扰动下输出变化率, +10% 扰动下输出变化率)
PARAMS: list[tuple[str, float, float]] = [
    ("单位运输成本", -0.062, 0.058),
    ("需求波动率", -0.118, 0.135),
    ("仓储固定成本", -0.031, 0.029),
    ("服务水平系数", -0.084, 0.092),
    ("碳排惩罚因子", -0.023, 0.026),
    ("初始库存量", -0.047, 0.041),
]


def _check_finite(values, label: str) -> None:
    """数值序列必须全为有限数值（排除 NaN/inf 与非数值）, 否则 ValueError 中文报错。"""
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{label} 含非有限数值或非数值: {v!r}")


@restore_style_on_error
def plot_tornado(
    params: list[tuple[str, float, float]],
    metric: str = "总成本",
    delta: float = 0.10,
    out_stem: str | None = None,
    *,
    label_fmt: "str | object" = "{:+.1%}",
    axis_percent: bool = True,
    xlabel: str | None = None,
    legend_labels: tuple[str, str] | None = None,
    figsize: tuple[float, float] | None = None,
) -> tuple[Path, Path]:
    """绘制龙卷风图并保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        params: (参数名, -δ 变化率, +δ 变化率) 列表, 变化率为输出相对变化。
        metric: 被扰动的输出指标名（进 x 轴标签）。
        delta: 扰动幅度（进 x 轴标签文案）。
        out_stem: 输出文件前缀; None 时写系统临时目录。
        label_fmt: 条端数值标签格式（仅限关键字）, 三种形态——① 完整格式模板
            （默认 "{:+.1%}" 相对变化率口径，含 `{}` 占位符即按 str.format
            填值, 占位符收**数值**变化率）;
            ② 纯 format spec（如 "+.1%" 或 ".3f"，按 f-string 格式规格处理）;
            ③ 单参数可调用对象（如绝对值口径 v: f"{v:+.2f} h"）。v3.1.0 参数化。
        axis_percent: True 时 x 轴刻度按百分比格式化（PercentFormatter,
            默认, 与相对变化率口径配套）; False 时回到默认数值刻度
            （绝对量纲口径）; 3.0.1 参数化。**轴刻度与条端标签须同口径**:
            条端走绝对量纲（label_fmt 用 ".3f" 等）时这里同步传 False。
        xlabel: x 轴名全称覆盖; None 时保持默认组合文案
            f"参数 ±{delta:.0%} 扰动下{metric}的相对变化"。
        legend_labels: (负向图例文案, 正向图例文案); None 保持默认
            （"负向影响（输出下降）"/"正向影响（输出上升）"）;
            3.0.1 参数化（供注入基线等额外图例语义时改写）。
        figsize: 画布尺寸; None 保持默认 (7.2, 4.5)（多参数行数多时
            可传更高画布, 3.0.1 参数化）。

    Raises:
        ValueError: params 为空 / 行不是三元组 / 参数名为空 / 变化率非有限数值。
    """
    if not params:
        raise ValueError("params 不能为空: 至少提供一条 (参数名, -δ 变化率, +δ 变化率) 记录")
    for row in params:
        if len(row) != 3:
            raise ValueError(f"params 每条必须是 (参数名, -δ 变化率, +δ 变化率) 三元组, 实际: {row!r}")
        name, low, high = row
        if not str(name).strip():
            raise ValueError(f"参数名不能为空: {row!r}")
        _check_finite((low, high), f"参数 {name!r} 的变化率")
    if callable(label_fmt):
        fmt_value = label_fmt
    elif "{" in str(label_fmt):
        # 完整格式模板（默认 "{:+.1%}"）: 用 str.format 填值
        fmt_value = lambda v: str(label_fmt).format(v)  # noqa: E731
    else:
        # 纯 format spec（如 "+.1%"）: 走 f-string 格式规格
        fmt_value = lambda v: f"{v:{label_fmt}}"  # noqa: E731 - format spec 字符串闭包

    import numpy as np

    # 按灵敏度（两向影响的最大绝对值）降序排列, 最敏感的参数放最上方
    rows = sorted(params, key=lambda r: max(abs(r[1]), abs(r[2])))
    names = [r[0] for r in rows]
    lows = np.array([r[1] for r in rows])
    highs = np.array([r[2] for r in rows])

    # 标签预格式化（建图前完成, 审查要求）: 用**真实数据**逐个格式化并缓存——
    #   ① 不留"试值成功、真值失败"的窗口, 也不留未关闭 Figure（畸形串
    #      "{"/"{missing}"/"{1}" 曾抛在建图之后, Figure 进全局管理器泄漏）;
    #   ② 不像固定试值那样误拒只对实际数据域有效的 callable
    #      （如 lambda v: f"{math.log10(v):.2f}" 在负数试值上会 domain error）。
    # 顺序要点: 本步在 apply_style() **之前**——格式串非法时连全局 rcParams
    # 都不该动（第四轮审查实测: 先 apply_style 会让失败调用留下样式副作用）。
    try:
        labels_high = [fmt_value(float(v)) for v in highs]
        labels_low = [fmt_value(float(v)) for v in lows]
    except Exception as exc:  # noqa: BLE001 - 统一转成带指引的 ValueError
        raise ValueError(
            f"label_fmt 无法格式化条端数值: {label_fmt!r} ({exc!r}); "
            f"请用完整模板 \"{{:+.1%}}\"、纯 spec \"+.1%\" 或单参数可调用对象"
        ) from exc

    apply_style()
    fig, ax = plt.subplots(figsize=figsize or (7.2, 4.5))
    y = np.arange(len(rows))
    bar_h = 0.36
    cmap = matplotlib.colormaps[get_cmap("diverging")]  # 1.1.0: 发散色经语义出口
    vmax = max(np.abs(np.concatenate([lows, highs])).max() * 1.15, 1e-6)
    norm = matplotlib.colors.Normalize(vmin=-vmax, vmax=vmax)

    ax.barh(y + bar_h / 2, highs, height=bar_h, color=cmap(norm(highs)),
            edgecolor="white", linewidth=0.6)
    ax.barh(y - bar_h / 2, lows, height=bar_h, color=cmap(norm(lows)),
            edgecolor="white", linewidth=0.6)

    # 条端数值标签: 放在远离零线一侧, 避免压条压线（文案用上面预格式化的结果）
    pad = vmax * 0.02
    for yi, v, text in zip(y + bar_h / 2, highs, labels_high):
        ax.text(v + pad, yi, text, va="center", ha="left", fontsize=9)
    for yi, v, text in zip(y - bar_h / 2, lows, labels_low):
        ax.text(v - pad, yi, text, va="center", ha="right", fontsize=9)

    ax.axvline(0.0, color=load_neutral("arrow"), linewidth=1.2)
    ax.set_yticks(y, names)
    ax.set_xlim(-vmax * 1.25, vmax * 1.25)
    # 龙卷风图横向条读数方向在 x（读数导向）: 保留 x 向网格, 关闭 y 向
    ax.xaxis.grid(True, color=load_neutral("grid"), alpha=0.45, linewidth=0.7)
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)
    if axis_percent:
        from matplotlib.ticker import PercentFormatter

        ax.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    ax.set_xlabel(xlabel if xlabel is not None
                  else f"参数 ±{delta:.0%} 扰动下{metric}的相对变化")
    # 1.4.1 图题纪律: 图名与结论写进论文 caption, 不烘焙进图内

    # 语义图例: 颜色编码影响方向而非扰动方向
    from matplotlib.patches import Patch

    neg_label, pos_label = legend_labels or ("负向影响（输出下降）",
                                             "正向影响（输出上升）")
    ax.legend(
        handles=[
            Patch(color=cmap(0.15), label=neg_label),
            Patch(color=cmap(0.85), label=pos_label),
        ],
        loc="lower right",
        frameon=True,
    )

    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / "make_tornado_sensitivity_demo")
    written = [Path(p) for p in save_fig(fig, out_stem)]
    return written[0], written[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成灵敏度龙卷风图（示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    try:
        png, svg = plot_tornado(PARAMS, out_stem=args.out)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    print(f"已输出: {png}")
    print(f"已输出: {svg}")
    print(f"已输出: {png.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
