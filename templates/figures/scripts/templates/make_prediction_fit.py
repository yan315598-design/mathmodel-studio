# -*- coding: utf-8 -*-
"""预测拟合效果图模板: 上子图真实值 vs 预测值时间序列 + 置信区间填充带,
下子图残差散点（零参考虚线）, 共享 x 轴, (a)(b) 子图编号。

cool_nature 冷色期刊风; 训练/预测分界画竖虚线并浅色衬底区分两段。

用法（二选一）:
    1. 独立运行:
       python make_prediction_fit.py [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录（gitignore 友好）, 产出 300dpi PNG + SVG + PDF。
    2. 复制到项目后改 DEMO_* 与 plot_prediction() 入参。

约定:
    - v7.7.0: 迁移 figkit + 三格式导出 + 中性色令牌。
    - 样式与色板统一经 scripts/figkit.py 加载（mathmodel.mplstyle + palettes.py,
      两者缺失时 figkit 内置等价内联回退）; 网格改 figkit.ygrid() 仅 y 向。
      (a)(b) 子图编号沿用轴内标题版式（改 panel_label 会动布局, 保守不迁移）。

输入说明:
    actual/prediction/ci_lo/ci_hi/t 须等长; ci_lo/ci_hi 可为 None（不画置信带）,
    也可在某点给 None 表示该时刻无区间（自动断带）。split 为训练/预测分界索引
    （None 表示不分段）; 残差 = actual - prediction（仅统计非空重叠段）。

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

# ---- v7.7.0: 头部统一走共享库 figkit（样式/色板/导出/网格/中性色）----
# figkit.py 位于本脚本上二级 scripts/ 目录; 色板回退已内置于 figkit, 不再保留本文件副本
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from figkit import (
    apply_style,
    load_neutral,
    load_palette,
    save_fig,
    ygrid,
)

# 示例数据: 前 60 期历史 + 后 20 期预测（风电功率, MW）
T = list(range(0, 80))
SPLIT = 60
ACTUAL = [
    42.9, 44.1, 43.6, 45.4, 47.2, 46.8, 48.6, 50.1, 49.5, 51.4,
    53.0, 54.2, 55.9, 57.3, 58.8, 60.1, 61.5, 62.8, 63.6, 64.9,
    66.0, 65.4, 64.2, 63.1, 61.8, 60.5, 59.2, 57.9, 56.8, 55.4,
    54.1, 52.9, 51.5, 50.3, 49.0, 47.8, 46.6, 45.3, 44.1, 43.0,
    42.1, 43.5, 45.2, 46.8, 48.0, 49.6, 51.2, 52.9, 54.5, 56.1,
    57.6, 59.2, 60.8, 62.0, 63.5, 64.9, 66.2, 67.5, 68.6, 69.4,
    70.1, 70.6, 71.0, 71.2, 70.8, 70.1, 69.2, 68.1, 66.8, 65.4,
    64.0, 62.5, 61.1, 59.6, 58.2, 56.9, 55.6, 54.3, 53.1, 52.0,
]
PREDICTION = [
    None, None, None, None, None, None, None, None, None, None,
    None, None, None, None, None, None, None, None, None, None,
    None, None, None, None, None, None, None, None, None, None,
    None, None, None, None, None, None, None, None, None, None,
    None, None, None, None, None, None, None, None, None, None,
    None, None, None, None, None, None, None, None, None, None,
    69.6, 69.9, 70.4, 70.5, 70.2, 69.6, 68.7, 67.6, 66.3, 64.9,
    63.5, 62.0, 60.6, 59.1, 57.7, 56.4, 55.1, 53.8, 52.6, 51.5,
]
CI_LO = [None] * SPLIT + [
    67.9, 67.9, 68.1, 67.9, 67.3, 66.4, 65.2, 63.8, 62.2, 60.5,
    58.8, 57.0, 55.3, 53.5, 51.8, 50.2, 48.6, 47.0, 45.5, 44.1,
]
CI_HI = [None] * SPLIT + [
    71.3, 71.9, 72.7, 73.1, 73.1, 72.8, 72.2, 71.4, 70.4, 69.3,
    68.2, 67.0, 65.9, 64.7, 63.6, 62.6, 61.6, 60.6, 59.7, 58.9,
]


def _check_finite(values, label: str, allow_none: bool = True) -> None:
    """数值序列必须全为有限数值或 None（允许 None 时）, 否则 ValueError 中文报错。"""
    for v in values:
        if v is None and allow_none:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{label} 含非有限数值或非数值: {v!r}")


def plot_prediction(
    actual: list[float],
    prediction: list,
    ci_lo: list | None = None,
    ci_hi: list | None = None,
    t: list | None = None,
    split: int | None = None,
    actual_label: str = "真实值",
    pred_label: str = "预测值",
    quantity: str = "指标值",
    out_stem: str | None = None,
) -> tuple[Path, Path]:
    """绘制预测拟合图（上: 时间序列+置信带; 下: 残差）并保存 PNG+SVG+PDF 三格式,

    Args:
        actual: 真实值序列。
        prediction: 预测均值序列（训练段可为 None）。
        ci_lo/ci_hi: 置信区间下/上界, 与 actual 等长; 可整体为 None 或逐点 None。
        t: 时间轴（与 actual 等长）; None 时取 0..len-1。
        split: 训练/预测分界索引; None 不画分界线。
        actual_label/pred_label: 图例文案。
        quantity: 指标名（进 y 轴标签）。
        out_stem: 输出文件前缀; None 时写系统临时目录。

    Raises:
        ValueError: 数据为空 / 长度不齐 / 含非有限值 / split 越界 /
            ci_lo 与 ci_hi 只给一侧。
    """
    import numpy as np

    if not actual:
        raise ValueError("actual 不能为空")
    n = len(actual)
    if prediction is None or len(prediction) != n:
        raise ValueError(f"prediction 长度 {0 if prediction is None else len(prediction)}"
                         f" 与 actual 长度 {n} 不齐")
    if (ci_lo is None) != (ci_hi is None):
        raise ValueError("ci_lo 与 ci_hi 必须同时提供或同时为 None")
    for name, seq in (("actual", actual), ("prediction", prediction)):
        _check_finite(list(seq), name, allow_none=name == "prediction")
    if ci_lo is not None:
        if len(ci_lo) != n or len(ci_hi) != n:
            raise ValueError("ci_lo/ci_hi 长度与 actual 不齐")
        _check_finite(list(ci_lo), "ci_lo")
        _check_finite(list(ci_hi), "ci_hi")
        for i, (lo, hi) in enumerate(zip(ci_lo, ci_hi)):
            if lo is not None and hi is not None and hi < lo:
                raise ValueError(f"第 {i} 期置信区间上界 {hi} < 下界 {lo}")
    if t is None:
        t = list(range(n))
    elif len(t) != n:
        raise ValueError(f"t 长度 {len(t)} 与 actual 长度 {n} 不齐")
    _check_finite(list(t), "t", allow_none=False)
    if split is not None and not (0 < split < n):
        raise ValueError(f"split 分界索引需在 (0, {n}) 内, 实际: {split}")

    apply_style()
    colors = load_palette("cool_nature")
    dark, blue, light, orange = colors[0], colors[1], colors[3], colors[4]
    split_line = load_neutral("arrow")   # 训练/预测分界线: 参考线灰令牌
    zero_line = load_neutral("secondary")  # 残差零参考线: 次级文字令牌
    x = np.asarray(t, dtype=float)
    act = np.asarray(actual, dtype=float)
    # prediction 可含 None（训练段无预测）, 转 NaN 后断线/断带自动处理
    pred_raw = np.array([np.nan if v is None else v for v in prediction],
                        dtype=float)
    pred_mask = np.isfinite(pred_raw)

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(8.2, 6.6), sharex=True,
        gridspec_kw={"height_ratios": [2.1, 1.0]},
    )
    fig.subplots_adjust(left=0.105, right=0.755, top=0.94, bottom=0.105,
                        hspace=0.30)

    # ---- 上子图: 时间序列 + 置信区间带 ----
    if split is not None:
        ax_top.axvspan(x[split], x[-1], facecolor=light, alpha=0.10, zorder=0)
    ax_top.plot(x, act, color=dark, linewidth=1.7, zorder=4, label=actual_label)
    if ci_lo is not None and any(v is not None for v in ci_lo):
        lo = np.ma.masked_invalid(
            np.array([np.nan if v is None else v for v in ci_lo], dtype=float))
        hi = np.ma.masked_invalid(
            np.array([np.nan if v is None else v for v in ci_hi], dtype=float))
        ax_top.fill_between(x, lo, hi, color=orange, alpha=0.18, linewidth=0,
                            zorder=2, label="95% 置信区间")
    # 预测曲线只取有限子集绘制, 避免 NaN 断点数据进入线段几何
    ax_top.plot(x[pred_mask], pred_raw[pred_mask], color=orange,
                linewidth=1.7, linestyle="--", zorder=5, label=pred_label)
    if split is not None:
        ax_top.axvline(x[split], color=split_line, linestyle=":", linewidth=1.1,
                       zorder=3)
    ax_top.set_title("(a) 真实值 vs 预测值")
    ax_top.set_ylabel(quantity)
    ax_top.legend(loc="upper left", bbox_to_anchor=(1.005, 0.985),
                  frameon=True, fontsize=9)
    ygrid(ax_top)  # v7.7.0: 时间序列只留极淡 y 向网格

    # ---- 下子图: 残差散点（仅对预测非空段） ----
    res = act[pred_mask] - pred_raw[pred_mask]
    if res.size == 0:
        raise ValueError("prediction 全为 None: 无法计算残差, 请至少给出一段预测值")
    ax_bot.axhline(0.0, color=zero_line, linewidth=1.1, zorder=2)
    if split is not None:
        ax_bot.axvline(x[split], color=split_line, linestyle=":", linewidth=1.1,
                       zorder=1)
    ax_bot.scatter(x[pred_mask], res, s=17, color=blue, alpha=0.85, zorder=3)
    ax_bot.set_title("(b) 预测残差")
    base = quantity.split("（")[0].strip() or quantity
    ax_bot.set_ylabel(f"残差（{base}）" if "（" in quantity else f"残差 / {quantity}")
    # 残差全 0(完美预测)时保底 ±1e-6, 避免 set_ylim(0,0) 退化图退化
    rmax = max(float(np.abs(res).max()), 1e-6)
    ax_bot.set_ylim(-rmax * 1.7, rmax * 1.7)
    ygrid(ax_bot)

    ax_bot.set_xlabel("时间 / 期")
    # 共享 x: 上轴隐藏刻度文字, 只在下轴显示
    ax_top.tick_params(labelbottom=False)
    return _save(fig, out_stem, "make_prediction_fit")


def _save(fig, out_stem: str | None, default_name: str) -> tuple[Path, Path]:
    """v7.7.0 经 figkit.save_fig 一次导出 PNG+SVG+PDF 三格式; 返回前两个路径。"""
    if out_stem is None:
        out_stem = str(Path(tempfile.gettempdir()) / default_name)
    written = save_fig(fig, out_stem)
    return Path(written[0]), Path(written[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成预测拟合效果图（示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    args = parser.parse_args(argv)
    try:
        png, svg = plot_prediction(
            ACTUAL, PREDICTION, CI_LO, CI_HI, T, SPLIT, quantity="功率（MW）",
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
