# -*- coding: utf-8 -*-
"""模型判别三件套模板: ROC / PR / 校准曲线 1×3 横向面板。

多模型对比时三个面板回答三个独立问题:
  (a) ROC —— 整体排序判别力, 曲线标注 AUC, 对角虚线为随机猜测参考;
  (b) PR   —— 类不平衡下更敏感的精确率-召回率权衡, 曲线标注 AP,
             水平虚线为正例率基线(无信息模型);
  (c) 校准 —— 预测概率是否可信, 10 等频分箱散点 + 完美校准对角线,
             图例附 ECE(期望校准误差)。

ROC/PR/校准指标全部 numpy 自算(阈值扫描 TPR/FPR、precision/recall
阶跃积分、等频分箱 ECE), 不依赖 sklearn。

用法（二选一）:
    1. 独立运行:
       python make_roc_pr.py [--palette academic_blue] [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录 mathmodel-figs/ 下,
       产出 300dpi PNG + SVG + PDF 三格式。
    2. 复制到项目后改 _demo_data() 与 plot_roc_pr() 入参。

输入说明:
    y_true: 0/1 真实标签数组; scores: {模型名: 分数数组}, 分数越大越判正。

figqa: 本模板按纯 --strict 通过(图例均落在面板右下空白区, 无盒内标签)。

退出码: 0 成功; 2 参数/IO 错误。
"""

from __future__ import annotations

import argparse
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

# figkit 位于本脚本上级目录 (scripts/), 注册后方可 from figkit import ...
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import (
    FIGSIZE,
    apply_style,
    despine,
    load_neutral,
    load_palette,
    panel_label,
    save_fig,
    ygrid,
)

# figqa 硬门脚本: templates/figures/scripts/templates/ → skill 根下 scripts/
FIGQA_SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "figqa.py"


# ============================================================
# numpy 自算指标 (不依赖 sklearn)
# ============================================================
def _trapz(y, x) -> float:
    """梯形积分; 兼容 numpy 1.x (trapz) 与 2.x (trapezoid) 双命名。"""
    fn = getattr(np, "trapezoid", None) or np.trapz
    return float(fn(y, x))


def _grouped_tp_fp(y_true: np.ndarray, score: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """按 score 降序排列后按唯一 score 分组, 返回各组结束处的 (TP, FP) 累积。

    相同 score 的样本属同一阈值组, 组内正负例必须一次性同时累积(ties 修正,
    与 sklearn 阈值唯一化语义一致), 否则平局会被逐样本扫描误算成全对/全错。
    """
    order = np.argsort(-score, kind="stable")
    y = y_true[order]
    group_ends = np.concatenate(
        (np.flatnonzero(np.diff(score[order])) + 1, [len(y)]))
    tp = np.cumsum(y)[group_ends - 1]
    fp = np.cumsum(1.0 - y)[group_ends - 1]
    return tp, fp


def _roc_curve(y_true: np.ndarray, score: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """阈值扫描自算 ROC 曲线与 AUC。

    按 score 降序、相同 score 同组一次性累积 TP/FP 得到 FPR/TPR 阶梯
    (与 sklearn.roc_curve 的唯一阈值语义同义), AUC 用梯形法对该阶梯积分,
    平局样本等价于按 0.5 判对计。返回 (fpr, tpr, auc), 均从原点 (0,0) 起步。

    Raises:
        ValueError: y_true 非 0/1 标签或全同类(无法定义 TPR)。
    """
    if not np.all(np.isin(y_true, (0.0, 1.0))):
        raise ValueError("y_true 必须只含 0/1 标签")
    if y_true.sum() in (0, len(y_true)):
        raise ValueError("y_true 不能全为同一类, 否则 ROC 无定义")
    tp, fp = _grouped_tp_fp(y_true, score)
    tpr = np.concatenate(([0.0], tp / tp[-1]))
    fpr = np.concatenate(([0.0], fp / fp[-1]))
    return fpr, tpr, _trapz(tpr, fpr)


def _pr_curve(y_true: np.ndarray, score: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float]:
    """阈值扫描自算 PR 曲线、AP 与正例率。

    阈值分组同 _grouped_tp_fp; AP = Σ (R_i − R_{i−1})·P_i (阶跃右连续积分,
    与 sklearn average_precision_score 同义); 曲线从 (0, 1) 起步补齐。
    返回 (recall, precision, ap, prevalence)。
    """
    tp, fp = _grouped_tp_fp(y_true, score)
    n_pos = float(tp[-1])
    recall = np.concatenate(([0.0], tp / n_pos))
    precision = np.concatenate(([1.0], tp / (tp + fp)))
    ap = float(np.sum(np.diff(recall) * precision[1:]))
    return recall, precision, ap, n_pos / len(y_true)


def _calibration(y_true: np.ndarray, score: np.ndarray, n_bins: int = 10):
    """等频分箱校准: 返回 (预测概率均值, 实际正例率, 箱样本权重, ECE)。

    ECE = Σ_b (n_b / n)·|acc_b − conf_b|, 越接近 0 校准越好。
    分箱边界取 score 的 n_bins+1 分位数, 空箱(重复分位)自动跳过。
    """
    edges = np.quantile(score, np.linspace(0.0, 1.0, n_bins + 1))
    idx = np.digitize(score, edges[1:-1])
    prob, frac, weights = [], [], []
    for b in range(n_bins):
        mask = idx == b
        if not mask.any():
            continue
        prob.append(float(score[mask].mean()))
        frac.append(float(y_true[mask].mean()))
        weights.append(int(mask.sum()))
    w = np.asarray(weights, dtype=float)
    ece = float(np.sum(w / w.sum() * np.abs(np.asarray(frac) - np.asarray(prob))))
    return np.asarray(prob), np.asarray(frac), w, ece


# ============================================================
# 主绘图
# ============================================================
def plot_roc_pr(
    y_true,
    scores: dict[str, np.ndarray],
    palette: str = "academic_blue",
    title: str | None = None,
    out_prefix: str | None = None,
) -> list[str]:
    """绘制 ROC/PR/校准 1×3 面板并三格式导出, 返回写出路径列表。

    Args:
        y_true: 0/1 真实标签一维数组。
        scores: {模型名: 判别分数数组}, 分数越大越判正; 按字典顺序取色板色。
        palette: 色板名 (figkit.load_palette), 默认 academic_blue。
        title: 整图标题; None 用默认。
        out_prefix: 输出前缀(不带扩展名); None 时写系统临时目录。

    Raises:
        ValueError: y_true/scores 为空、y_true 非一维、长度不齐、标签非 0/1、
            score 非一维/含非有限值/越出 [0,1](校准面板按概率解释)、
            模型数超过色板可分配颜色数。
    """
    y = np.asarray(y_true, dtype=float)
    if y.ndim != 1:
        raise ValueError(f"y_true 必须为一维数组, 实际维度: {y.ndim}")
    if y.size == 0:
        raise ValueError("y_true 不能为空")
    if not scores:
        raise ValueError("scores 至少提供一个模型的分数")
    if not np.all(np.isin(y, (0.0, 1.0))):
        raise ValueError("y_true 必须只含 0/1 标签")
    for name, s in scores.items():
        s = np.asarray(s, dtype=float)
        if s.ndim != 1:
            raise ValueError(f"模型 '{name}' 分数必须为一维数组, 实际维度: {s.ndim}")
        if s.shape != y.shape:
            raise ValueError(f"模型 '{name}' 分数长度 {s.shape[0]} 与 y_true 长度 {y.shape[0]} 不齐")
        if not np.all(np.isfinite(s)):
            raise ValueError(f"模型 '{name}' 分数含非有限值(NaN/inf), 无法阈值扫描")
        if np.any((s < 0.0) | (s > 1.0)):
            raise ValueError(f"模型 '{name}' 分数须在 [0,1] 区间(校准面板按概率解释)")
    apply_style()
    colors = load_palette(palette)
    if len(scores) > len(colors):
        raise ValueError(
            f"模型数 {len(scores)} 超过色板 '{palette}' 的 {len(colors)} 个可用颜色"
        )
    ref_grey = load_neutral("arrow")

    fig, axes = plt.subplots(1, 3, figsize=FIGSIZE["wide"])
    fig.subplots_adjust(left=0.065, right=0.985, top=0.80, bottom=0.16, wspace=0.34)
    axes = list(axes)

    # ---- (a) ROC ----
    ax = axes[0]
    ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1.0, color=ref_grey,
            zorder=2, label="随机猜测")
    for color, (name, score) in zip(colors, scores.items()):
        fpr, tpr, auc = _roc_curve(y, np.asarray(score, dtype=float))
        ax.plot(fpr, tpr, color=color, linewidth=1.8, zorder=3,
                label=f"{name}（AUC={auc:.3f}）")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xticks([0, 0.5, 1])
    ax.set_yticks([0, 0.5, 1])
    ax.set_title("ROC 曲线")
    ax.set_xlabel("假正例率（FPR）")
    ax.set_ylabel("真正例率（TPR）")
    ax.legend(loc="lower right", fontsize=9)
    ygrid(ax)
    despine(ax)
    panel_label(ax, "a")

    # ---- (b) PR ----
    ax = axes[1]
    _, _, _, prevalence = _pr_curve(y, np.asarray(next(iter(scores.values())), dtype=float))
    ax.axhline(prevalence, linestyle="--", linewidth=1.0, color=ref_grey, zorder=2,
               label=f"正例率基线（{prevalence:.2f}）")
    for color, (name, score) in zip(colors, scores.items()):
        rec, pre, ap, _ = _pr_curve(y, np.asarray(score, dtype=float))
        ax.plot(rec, pre, color=color, linewidth=1.8, zorder=3,
                label=f"{name}（AP={ap:.3f}）")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xticks([0, 0.5, 1])
    ax.set_yticks([0, 0.5, 1])
    ax.set_title("PR 曲线")
    ax.set_xlabel("召回率（Recall）")
    ax.set_ylabel("精确率（Precision）")
    ax.legend(loc="lower right", fontsize=9)
    ygrid(ax)
    despine(ax)
    panel_label(ax, "b")

    # ---- (c) 校准 ----
    ax = axes[2]
    ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1.0, color=ref_grey,
            zorder=2, label="完美校准")
    for color, (name, score) in zip(colors, scores.items()):
        prob, frac, _, ece = _calibration(y, np.asarray(score, dtype=float))
        ax.plot(prob, frac, linestyle="none", marker="o", markersize=6.5,
                markerfacecolor="white", markeredgecolor=color, markeredgewidth=1.3,
                color=color, zorder=4, label=f"{name}（ECE={ece:.3f}）")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xticks([0, 0.5, 1])
    ax.set_yticks([0, 0.5, 1])
    ax.set_title("校准曲线")
    ax.set_xlabel("预测概率均值")
    ax.set_ylabel("实际正例频率")
    ax.legend(loc="lower right", fontsize=9)
    ygrid(ax)
    despine(ax)
    panel_label(ax, "c")

    fig.suptitle(title or "模型判别能力与概率校准诊断", fontsize=11,
                 fontweight="bold", y=0.985)
    if out_prefix is None:
        out_prefix = str(Path(tempfile.gettempdir()) / "mathmodel-figs" / "make_roc_pr")
    return save_fig(fig, out_prefix)


def _demo_data() -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """内置 demo: 600 样本(正例率约 0.35), 三个判别力递减的模型。"""
    rng = np.random.default_rng(20240501)
    n = 600
    y = (rng.random(n) < 0.35).astype(float)
    noise = rng.standard_normal(n)
    scores: dict[str, np.ndarray] = {}
    for name, strength in (("模型 A", 2.4), ("模型 B", 1.1), ("模型 C", 0.45)):
        logit = strength * (2.0 * y - 1.0) + noise
        scores[name] = 1.0 / (1.0 + np.exp(-logit))
    return y, scores


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="生成模型判别三件套 ROC/PR/校准曲线（示例数据）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    parser.add_argument("--palette", default="academic_blue",
                        help="色板名（默认 academic_blue）")
    args = parser.parse_args(argv)
    out = args.out or str(
        Path(tempfile.gettempdir()) / "mathmodel-figs" / "make_roc_pr")
    y, scores = _demo_data()
    try:
        written = plot_roc_pr(y, scores, palette=args.palette, out_prefix=out)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    for path in written:
        print(f"已输出: {path}")
    print(f"[提示] 出图后跑该模板的 figqa 硬门: "
          f"python {FIGQA_SCRIPT} <图脚本或输出目录> --strict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
