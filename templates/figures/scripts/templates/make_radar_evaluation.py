# -*- coding: utf-8 -*-
"""多方案综合评价雷达图模板: 多方案 × 多指标归一化评分, 多边形叠加对比。

academic_blue 色板逐方案填色(alpha 0.15), 指标名沿径向外移防重叠,
图例固定外置画布右侧。

用法（二选一）:
    1. 独立运行:
       python make_radar_evaluation.py [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录（gitignore 友好）, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 DEMO 数据与 plot_radar() 入参。

约定:
    - 1.1.0: 迁移 figkit + 三格式导出 + 中性色令牌。
    - 样式与色板统一经 scripts/figkit.py 加载（mathmodel.mplstyle + palettes.py,
      两者缺失时 figkit 内置等价内联回退）; 极坐标自绘参考环, 不走 ygrid。

输入说明:
    data: 方案名 → 各指标归一化得分列表(0~1, 越接近 1 越优;
          成本/时间类指标请先做 1 - 归一 处理), 各方案等长且长度 >= 3。

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

# ---- 1.1.0: 头部统一走共享库 figkit（样式/色板/导出/中性色）----
# figkit.py 位于本脚本上二级 scripts/ 目录; 色板回退已内置于 figkit, 不再保留本文件副本
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    apply_style,
    load_neutral,
    load_palette,
    save_fig,
)

# 示例数据: 方案名 → 六项指标归一化得分(0~1, 已按"越高越优"折算)
DEMO_DATA: dict[str, list[float]] = {
    "方案A（成本优先）": [0.90, 0.76, 0.84, 0.88, 0.70, 0.78],
    "方案B（均衡策略）": [0.72, 0.88, 0.80, 0.70, 0.85, 0.83],
    "方案C（时效优先）": [0.60, 0.65, 0.72, 0.56, 0.68, 0.75],
}
DEMO_LABELS = ["物流成本", "运输时效", "准时率", "碳排放", "库存周转", "服务满意度"]


def _check_finite(values, label: str) -> None:
    """数值序列必须全为有限数值（排除 NaN/inf 与非数值）, 否则 ValueError 中文报错。"""
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{label} 含非有限数值或非数值: {v!r}")


def plot_radar(
    data: dict[str, list[float]],
    labels: list[str],
    metric_unit: str = "得分",
    title: str | None = None,
    fill_alpha: float = 0.15,
    out_stem: str | None = None,
) -> tuple[Path, Path]:
    """绘制多方案评价雷达图并保存 PNG+SVG+PDF 三格式, 返回前两个输出路径。

    Args:
        data: 方案名 → 各指标归一化得分(0~1), 全部等长且 >= 3 项。
        labels: 指标名列表, 与每个方案的得分列表等长且顺序一致。
        metric_unit: 得分轴单位（进图例/刻度文案, 默认 "得分"）。
        title: 图标题; None 时用默认标题。
        fill_alpha: 多边形填充透明度, 默认 0.15。
        out_stem: 输出文件前缀; None 时写系统临时目录。

    Raises:
        ValueError: data 为空 / 指标少于 3 个 / 行长度不齐或与 labels 不等长 /
            得分非有限或越出 [0, 1] / 名称含空串。
    """
    if not data:
        raise ValueError("data 不能为空: 至少提供一个方案的得分")
    if not labels or len(labels) < 3:
        raise ValueError(f"指标数需 >= 3（雷达图至少三轴）, 实际: {len(labels)} 个")
    if len({str(lb).strip() for lb in labels}) != len(labels):
        raise ValueError("labels 存在重复指标名")
    for name, scores in data.items():
        if not str(name).strip():
            raise ValueError("方案名不能为空")
        if len(scores) != len(labels):
            raise ValueError(
                f"方案 {name!r} 得分 {len(scores)} 项与指标 {len(labels)} 项长度不齐"
            )
        _check_finite(scores, f"方案 {name!r} 得分")
        for v in scores:
            if v < 0.0 or v > 1.0:
                raise ValueError(
                    f"方案 {name!r} 得分 {v} 越出 [0, 1]（归一化评分域）; "
                    "成本/时间类反向指标请先做 1 - 归一 再传入"
                )
    if fill_alpha <= 0.0 or fill_alpha > 1.0:
        raise ValueError(f"fill_alpha 需在 (0, 1], 实际: {fill_alpha}")

    apply_style()
    import numpy as np

    colors = load_palette("academic_blue")
    ring_grey = load_neutral("arrow")  # 参考环/辐线灰: reference 语义令牌
    label_ink = load_neutral("ink")
    names = list(data)
    n = len(labels)
    thetas = np.linspace(np.pi / 2, np.pi / 2 - 2 * np.pi, n, endpoint=False)
    thetas_deg = np.rad2deg(thetas)

    # 画布右侧预留图例区: 圆占据左 52%, 中心约在 30% 处;
    # 垂直加高让顶部标签与标题各得其所
    fig = plt.figure(figsize=(9.2, 6.4))
    ax = fig.add_axes([0.09, 0.045, 0.52, 0.91], projection="polar")
    ax.set_rlim(0.0, 1.0)
    ax.set_yticks([])
    ax.grid(False)
    ax.set_axis_off()  # 去掉默认圆框与辐线, 全部自绘保证风格一致
    for spine_key in ("polar", "start", "end", "inner"):
        try:
            ax.spines[spine_key].set_visible(False)
        except KeyError:
            pass

    # 同心参考环 + 半径辐线: 细灰虚线族, 只做刻度参照
    # （极坐标自绘参照环, 不适用数据图的 ygrid-only 惯例）
    ring_ang = np.linspace(0.0, 2.0 * np.pi, 400)
    for level, lw, alpha in ((0.25, 0.7, 0.30), (0.5, 0.7, 0.30),
                             (0.75, 0.7, 0.30), (1.0, 1.1, 0.85)):
        ax.plot(ring_ang, np.full_like(ring_ang, level), color=ring_grey,
                linewidth=lw, alpha=alpha, zorder=0.5)
    for th in thetas:
        ax.plot([th, th], [0.0, 1.0], color=ring_grey, linewidth=0.6,
                alpha=0.45, zorder=0.5)

    # 指标轴标签: 沿径向外移到环外, 按象限选 ha/va, 天然不压环不压多边形
    for i, (th, name) in enumerate(zip(thetas_deg, labels)):
        x, y = math.cos(math.radians(th)), math.sin(math.radians(th))
        ha = "left" if x > 0.30 else ("right" if x < -0.30 else "center")
        va = "bottom" if y > 0.30 else ("top" if y < -0.30 else "center")
        ax.text(math.radians(th), 1.155, name, ha=ha, va=va, fontsize=10,
                color=label_ink, zorder=6)

    # 各方案多边形: 顶点 + 半透明填充 + 描边, 色板逐方案
    pts = np.append(thetas, thetas[0])
    for i, name in enumerate(names):
        scores = np.asarray(data[name], dtype=float)
        ring = np.append(scores, scores[0])
        ax.plot(pts, ring, color=colors[i % len(colors)], linewidth=1.9,
                zorder=4, label=name)
        ax.fill(pts, ring, color=colors[i % len(colors)], alpha=fill_alpha,
                linewidth=0.0, zorder=3)

    # 标题: 顶部指标标签之上仍有 ~30px 空间, 用 fig.text 精确居中于圆心上方
    title = title or f"多方案综合评价雷达图（{metric_unit} 0~1）"
    fig.text(0.35, 0.968, title, ha="center", va="baseline", fontsize=12)

    # 图例固定外置右侧预留区; 锚点需越过极轴外圈指标标签带 (标签约伸到 axes 1.2x), 取 1.30 防重叠
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.30, 0.98),
        frameon=True,
        fontsize=9.5,
        title="方案",
    )
    return _save(fig, out_stem, "make_radar_evaluation")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """1.1.0 经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成多方案综合评价雷达图（示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    try:
        png, svg = plot_radar(DEMO_DATA, DEMO_LABELS, out_stem=args.out)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    print(f"已输出: {png}")
    print(f"已输出: {svg}")
    print(f"已输出: {png.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
