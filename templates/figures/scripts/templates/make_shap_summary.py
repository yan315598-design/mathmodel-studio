# -*- coding: utf-8 -*-
"""SHAP 摘要图模板: 蜂窝图(beeswarm) / 特征重要性条形图(bar)双模式。

依赖 shap 官方库绘制; demo 不依赖 sklearn, 直接按固定种子构造模拟
SHAP 值矩阵(20 特征 × 200 样本, 重要性指数衰减 + 特征值相关符号),
复制到项目后把 shap_values / features 换成真实模型输出即可。

模式说明:
  --mode beeswarm  每特征一行散点蜂群(横=SHAP 值, 色=特征值高低),
                   使用 SHAP 官方红蓝色标(特征值语义色, 不套色板);
  --mode bar       特征按 mean|SHAP| 排序的条形图, 条色套 figkit 色板第 1 色。

用法（二选一）:
    1. 独立运行:
       python make_shap_summary.py [--mode beeswarm|bar] [--palette academic_blue]
                                   [--out 输出前缀]
       不给 --out 时示例图写入系统临时目录 mathmodel-figs/ 下,
       产出 300dpi PNG + SVG + PDF 三格式。
    2. 复制到项目后改 _demo_shap() 与 plot_shap_summary() 入参。

figqa: 本机无 shap 时脚本以退出码 3 提前退出(figqa 会报"执行失败",
属预期); 装 shap 后建议按纯 --strict 跑一次确认布局。

退出码: 0 成功; 2 参数/IO 错误; 3 缺少 shap 依赖。
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

# ---- 依赖守卫: shap 缺失时友好提示并以退出码 3 结束 ----
try:
    import shap
except ImportError:
    print("[依赖缺失] 请先 pip install shap（约 15MB），"
          "本模板依赖 SHAP 官方库绘制蜂窝图")
    sys.exit(3)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

# figkit 位于本脚本上级目录 (scripts/), 注册后方可 from figkit import ...
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import apply_style, load_neutral, load_palette, save_fig

# figqa 硬门脚本: templates/figures/scripts/templates/ → skill 根下 scripts/
FIGQA_SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "figqa.py"


def _demo_shap(n_samples: int = 200, n_features: int = 20, seed: int = 20240901):
    """构造模拟 SHAP 值: 返回 (shap_values, features, feature_names)。

    重要性随特征序指数衰减; SHAP 值与特征值正相关(高值推高预测),
    叠加噪声形成蜂窝图的经典竖向扩散形态。
    """
    rng = np.random.default_rng(seed)
    features = rng.standard_normal((n_samples, n_features))
    decay = np.exp(-np.arange(n_features) / 6.0)          # 重要性权重
    noise = rng.standard_normal((n_samples, n_features))
    shap_values = decay * (0.7 * features + 0.5 * noise)
    names = [f"特征 {i + 1:02d}" for i in range(n_features)]
    return shap_values, features, names


def plot_shap_summary(
    shap_values: np.ndarray,
    features: np.ndarray,
    feature_names: list[str],
    mode: str = "beeswarm",
    palette: str = "academic_blue",
    title: str | None = None,
    out_prefix: str | None = None,
) -> list[str]:
    """调用 shap.summary_plot 绘制摘要图并三格式导出, 返回写出路径列表。

    Args:
        shap_values: (n_samples, n_features) SHAP 贡献矩阵。
        features: 与 shap_values 同形状的特征值矩阵(beeswarm 横向色标用)。
        feature_names: n_features 个特征名。
        mode: "beeswarm"(蜂窝) 或 "bar"(重要性条形)。
        palette: 色板名, bar 模式条色取第 1 色; beeswarm 保留 SHAP 官方
            红蓝特征值色标(功能语义色, 不替换)。
        title: 图标题; None 按模式取默认。
        out_prefix: 输出前缀(不带扩展名); None 时写系统临时目录。

    Raises:
        ValueError: mode 非法 / 矩阵形状或特征名数不齐。
    """
    if mode not in ("beeswarm", "bar"):
        raise ValueError(f"mode 须为 beeswarm 或 bar, 实际: {mode!r}")
    shap_values = np.asarray(shap_values, dtype=float)
    features = np.asarray(features, dtype=float)
    if shap_values.ndim != 2:
        raise ValueError(f"shap_values 须为二维矩阵, 实际维度: {shap_values.ndim}")
    if features.shape != shap_values.shape:
        raise ValueError(f"features 形状 {features.shape} 与 shap_values {shap_values.shape} 不齐")
    if len(feature_names) != shap_values.shape[1]:
        raise ValueError(
            f"feature_names 数 {len(feature_names)} 与特征数 {shap_values.shape[1]} 不齐")

    apply_style()
    plot_size = (7.2, 0.32 * shap_values.shape[1] + 1.6)  # 特征数自适应高度
    common = dict(feature_names=feature_names, show=False,
                  plot_size=plot_size, max_display=len(feature_names))
    if mode == "beeswarm":
        shap.summary_plot(shap_values, features=features, plot_type="dot", **common)
        fig = plt.gcf()
        fig.suptitle(title or "SHAP 蜂窝图：特征贡献分布（色=特征值高低）",
                     fontsize=11, fontweight="bold", y=0.995)
    else:
        primary = load_palette(palette)[0]
        try:
            shap.summary_plot(shap_values, features=features, plot_type="bar",
                              color=primary, **common)
        except TypeError:  # 旧版 shap 的 summary_plot 不收 color 关键字
            shap.summary_plot(shap_values, features=features, plot_type="bar", **common)
        fig = plt.gcf()
        fig.suptitle(title or "SHAP 特征重要性（mean |SHAP|）",
                     fontsize=11, fontweight="bold", y=0.995)
    fig.text(0.01, 0.01, "SHAP > 0 表示推高预测", fontsize=8,
             color=load_neutral("faint"))
    if out_prefix is None:
        out_prefix = str(Path(tempfile.gettempdir()) / "mathmodel-figs"
                         / f"make_shap_summary_{mode}")
    return save_fig(fig, out_prefix)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="生成 SHAP 摘要图（模拟数据, beeswarm/bar 双模式）")
    parser.add_argument("--mode", default="beeswarm", choices=["beeswarm", "bar"],
                        help="绘图模式（默认 beeswarm）")
    parser.add_argument("--out", default=None,
                        help="输出文件前缀（自动追加 .png/.svg/.pdf）")
    parser.add_argument("--palette", default="academic_blue",
                        help="色板名（bar 模式条色; 默认 academic_blue）")
    args = parser.parse_args(argv)
    out = args.out or str(
        Path(tempfile.gettempdir()) / "mathmodel-figs"
        / f"make_shap_summary_{args.mode}")
    shap_values, features, names = _demo_shap()
    try:
        written = plot_shap_summary(shap_values, features, names,
                                    mode=args.mode, palette=args.palette,
                                    out_prefix=out)
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
