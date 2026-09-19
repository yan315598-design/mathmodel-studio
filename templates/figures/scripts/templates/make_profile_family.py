# -*- coding: utf-8 -*-
"""剖面族模板: N 条剖面按连续变量（时间/参数）渐变着色 + colorbar 标注变量名。

证据分两层: 剖面曲线族（数据层, viridis 连续渐变编码连续变量）+
可选判据竖线（判据层, 红虚线, 图例注明判据值）。剖面方向约定: 横轴=场量,
纵轴=深度/位置并倒置（越往下越深）, 符合物理场剖面读图习惯。

用法（二选一）:
    1. 独立运行:
       python make_profile_family.py [--demo] [--out 输出前缀]
       --demo 显式渲染内置示例（不给 --out 时示例图写入系统临时目录）,
       产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 _demo_profiles() 与 plot_profile_family() 入参。

约定:
    - 3.0.0 新增（图叙事纪律: 连续变量用渐变不用离散色轮）。
    - 样式与色板统一经 scripts/figkit.py 加载; 渐变色取
      figkit.get_cmap("sequential"), 判据线取 academic_blue 第 4 色（红）虚线。

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
import numpy as np

# ---- figkit 位于本脚本上二级 scripts/ 目录, 注册后方可 from figkit import ----
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    FIGSIZE,
    apply_style,
    get_cmap,
    load_palette,
    restore_style_on_error,
    save_fig,
)

CRITERION_COLOR = load_palette("academic_blue")[3]   # 判据线=红虚线


def _demo_profiles() -> tuple[np.ndarray, list[np.ndarray], np.ndarray]:
    """构造示例: 干燥 8 个时刻的板材温度-深度剖面, 返回 (深度, 剖面列表, 时刻数组)。"""
    depth = np.linspace(0.0, 20.0, 81)   # cm
    times = np.linspace(0.0, 7.0, 8)     # h
    profiles = []
    for t in times:
        penetration = 2.4 + 1.15 * math.sqrt(t + 0.4)
        profiles.append(24.0 + 58.0 * np.exp(-depth / penetration))
    return depth, profiles, times


@restore_style_on_error
def plot_profile_family(
    depth: np.ndarray,
    profiles: list[np.ndarray],
    values: list[float],
    var_label: str = "时刻 (h)",
    value_label: str = "温度 (°C)",
    depth_label: str = "深度 (cm)",
    criterion: float | None = None,
    criterion_label: str = "判据线",
    out_stem: str | None = None,
    *,
    legend_loc: str = "upper right",
) -> tuple[Path, Path]:
    """绘制剖面族图（渐变着色 + colorbar + 可选判据线）, 保存 PNG+SVG+PDF。

    Args:
        depth: 公共纵轴坐标（剖面位置/深度, 一维递增或递减均可）。
        profiles: 剖面列表, 每条与 depth 同长。
        values: 与 profiles 一一对应的连续变量值（时间/参数）, 驱动渐变着色。
        var_label: colorbar 轴名（连续变量名）。
        value_label: 横轴（场量）名。
        depth_label: 纵轴（位置/深度）名。
        criterion: 判据值（对场量画竖直红虚线）; None 时不画判据层。
        criterion_label: 判据线图例文案。
        out_stem: 输出文件前缀; None 时写系统临时目录。
        legend_loc: 判据线图例位置（仅限关键字; 3.0.1 参数化, 默认
            "upper right"; 判据线右侧区域有剖面线穿过时改 "lower right"/
            "upper left"）。

    Raises:
        ValueError: 剖面/变量数为空或长度不齐、坐标或场量含非有限值、
            values 非有限、剖面长度与 depth 不齐等。
    """
    z = np.asarray(depth, dtype=float)
    if z.ndim != 1 or len(z) < 2:
        raise ValueError(f"depth 须为一维坐标（长度 ≥2）, 实际 shape {z.shape}")
    if not profiles or len(values) != len(profiles):
        raise ValueError(
            f"profiles 与 values 须一一对应且非空, 实际 {len(profiles)} 条 vs {len(values)} 个值")
    if not np.all(np.isfinite(z)):
        raise ValueError("depth 含非有限数值(NaN/inf)")
    for i, p in enumerate(profiles):
        arr = np.asarray(p, dtype=float)
        if arr.shape != z.shape:
            raise ValueError(f"profiles[{i}] 长度 {arr.shape} 与 depth {z.shape} 不齐")
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"profiles[{i}] 含非有限数值(NaN/inf)")
    vals = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(vals)):
        raise ValueError("values 含非有限数值(NaN/inf)")
    if criterion is not None and not math.isfinite(criterion):
        raise ValueError(f"criterion 须为有限数值, 实际 {criterion!r}")

    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE["onehalf"], layout="constrained")
    cmap = matplotlib.colormaps[get_cmap("sequential")]
    norm = matplotlib.colors.Normalize(vmin=float(vals.min()), vmax=float(vals.max()))
    for v, p in zip(vals, profiles):
        ax.plot(p, z, color=cmap(norm(v)), linewidth=1.6, solid_capstyle="round")

    if criterion is not None:
        from matplotlib.lines import Line2D

        ax.axvline(criterion, color=CRITERION_COLOR, linestyle="--", linewidth=1.6)
        ax.legend(
            [Line2D([0], [0], color=CRITERION_COLOR, linestyle="--", linewidth=1.6)],
            [f"{criterion_label} = {criterion:g}"],
            loc=legend_loc, frameon=True)

    ax.set_xlabel(value_label)
    ax.set_ylabel(depth_label)
    ax.set_ylim(float(z.max()), float(z.min()))   # 深度倒置: 越往下越深
    ax.set_xlim(right=float(max(np.max(p) for p in profiles)) * 1.06)
    sm = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.045, pad=0.02)
    cbar.set_label(var_label)
    return _save(fig, out_stem, "make_profile_family")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成剖面族图（示例数据）")
    parser.add_argument("--demo", action="store_true",
                        help="渲染内置示例数据（默认行为, 显式确认用）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    depth, profiles, times = _demo_profiles()
    try:
        png, svg = plot_profile_family(
            depth, profiles, list(times),
            var_label="时刻 (h)",
            value_label="温度 (°C)",
            depth_label="深度 (cm)",
            criterion=60.0,
            criterion_label="判据 60 °C",
            out_stem=args.out,
        )
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    print(f"已输出: {png}")
    print(f"已输出: {svg}")
    print(f"已输出: {png.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
