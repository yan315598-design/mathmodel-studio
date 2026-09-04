# -*- coding: utf-8 -*-
"""灵敏度龙卷风图模板: 参数 ±扰动 对输出指标的影响, 水平条按灵敏度排序。

发散色 RdBu_r 语义: 负向影响偏蓝、正向影响偏红, 零线居中。

用法（二选一）:
    1. 独立运行:
       python make_tornado_sensitivity.py [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录（gitignore 友好）, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 PARAMS/plot_tornado() 的输入数据。

约定:
    - v7.7.0: 迁移 figkit + 三格式导出 + 中性色令牌。
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

# ---- v7.7.0: 头部统一走共享库 figkit（样式/色板/导出/colormap 语义/中性色）----
# figkit.py 位于本脚本上二级 scripts/ 目录; 色板回退已内置于 figkit, 不再保留本文件副本
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    apply_style,
    get_cmap,
    load_neutral,
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


def plot_tornado(
    params: list[tuple[str, float, float]],
    metric: str = "总成本",
    delta: float = 0.10,
    out_stem: str | None = None,
) -> tuple[Path, Path]:
    """绘制龙卷风图并保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        params: (参数名, -δ 变化率, +δ 变化率) 列表, 变化率为输出相对变化。
        metric: 被扰动的输出指标名（进轴标签/标题）。
        delta: 扰动幅度（仅用于图例/标题文案）。
        out_stem: 输出文件前缀; None 时写系统临时目录。

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

    apply_style()
    import numpy as np

    # 按灵敏度（两向影响的最大绝对值）降序排列, 最敏感的参数放最上方
    rows = sorted(params, key=lambda r: max(abs(r[1]), abs(r[2])))
    names = [r[0] for r in rows]
    lows = np.array([r[1] for r in rows])
    highs = np.array([r[2] for r in rows])

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    y = np.arange(len(rows))
    bar_h = 0.36
    cmap = matplotlib.colormaps[get_cmap("diverging")]  # v7.7.0: 发散色经语义出口
    vmax = max(np.abs(np.concatenate([lows, highs])).max() * 1.15, 1e-6)
    norm = matplotlib.colors.Normalize(vmin=-vmax, vmax=vmax)

    ax.barh(y + bar_h / 2, highs, height=bar_h, color=cmap(norm(highs)),
            edgecolor="white", linewidth=0.6)
    ax.barh(y - bar_h / 2, lows, height=bar_h, color=cmap(norm(lows)),
            edgecolor="white", linewidth=0.6)

    # 条端数值标签: 放在远离零线一侧, 避免压条压线
    pad = vmax * 0.02
    for yi, v in zip(y + bar_h / 2, highs):
        ax.text(v + pad, yi, f"{v:+.1%}", va="center", ha="left", fontsize=9)
    for yi, v in zip(y - bar_h / 2, lows):
        ax.text(v - pad, yi, f"{v:+.1%}", va="center", ha="right", fontsize=9)

    ax.axvline(0.0, color=load_neutral("arrow"), linewidth=1.2)
    ax.set_yticks(y, names)
    ax.set_xlim(-vmax * 1.25, vmax * 1.25)
    # 龙卷风图横向条读数方向在 x（读数导向）: 保留 x 向网格, 关闭 y 向
    ax.xaxis.grid(True, color=load_neutral("grid"), alpha=0.45, linewidth=0.7)
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)
    from matplotlib.ticker import PercentFormatter

    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    ax.set_xlabel(f"参数 ±{delta:.0%} 扰动下{metric}的相对变化")
    ax.set_title(f"参数灵敏度龙卷风图（{metric}, ±{delta:.0%} 扰动）")

    # 语义图例: 颜色编码影响方向而非扰动方向
    from matplotlib.patches import Patch

    ax.legend(
        handles=[
            Patch(color=cmap(0.15), label="负向影响（输出下降）"),
            Patch(color=cmap(0.85), label="正向影响（输出上升）"),
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
