# -*- coding: utf-8 -*-
"""v1.0.0 建模图表模板包 dispatcher（17 个数据图模板的统一入口）。

示意图（流程图/框架图等）由同目录 render_diagram_pack.py 分发。

用法:
    python render_modeling_pack.py <子命令> [模板参数...]
    python render_modeling_pack.py --list

子命令即模板 id, 其余参数原样转发给模板脚本, 例如:
    python render_modeling_pack.py optimization-allocation --mode gantt --out figs/alloc
    python render_modeling_pack.py tornado --out figs/tornado
    python render_modeling_pack.py heatmap --out figs/heatmap

退出码: 0 成功; 1 模板执行失败; 2 未知模板/用法错误。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TEMPLATES: dict[str, tuple[str, str]] = {
    "tornado-sensitivity": (
        "make_tornado_sensitivity.py",
        "灵敏度龙卷风图: 参数 ±扰动 vs 输出变化, 水平条排序, RdBu_r 发散色",
    ),
    "optimization-allocation": (
        "make_optimization_allocation.py",
        "优化分配结果: 堆叠条/甘特双模式, academic_blue 色板",
    ),
    "multiscenario-robustness": (
        "make_multiscenario_robustness.py",
        "多场景稳健性对比: 箱线/小提琴 + 基准参考线, cool_nature 色板",
    ),
    "technical-route-flowchart": (
        "make_technical_route_flowchart.py",
        "技术路线图: 矩形+箭头确定性布局, 中文字宽估算自动换行, PNG+SVG",
    ),
    "radar-evaluation": (
        "make_radar_evaluation.py",
        "评价雷达图: 多方案×多指标归一化评分, 多边形叠加, 图例外置",
    ),
    "correlation-heatmap": (
        "make_correlation_heatmap.py",
        "相关性/灵敏度热力图: RdBu_r 发散色 center=0, 黑白自适应字, 显著性星号",
    ),
    "pareto-front": (
        "make_pareto_front.py",
        "帕累托前沿图: 可行解散点云+非支配前沿高亮, 理想点/折中点标注",
    ),
    "prediction-fit": (
        "make_prediction_fit.py",
        "预测拟合图: 真实vs预测序列+置信带(上), 残差(下), 共享 x 轴",
    ),
    "ranking-bar": (
        "make_ranking_bar.py",
        "评价排序条形图: 横向条按得分排序, 指标权重贡献堆叠分解",
    ),
    "convergence-curve": (
        "make_convergence_curve.py",
        "算法收敛曲线: 多算法对比, 最优值虚线, 收敛代次标记, 可选 log 轴",
    ),
    "roc-pr": (
        "make_roc_pr.py",
        "模型判别三件套: ROC(AUC)/PR(AP)/校准曲线(ECE) 1×3 面板, numpy 自算指标",
    ),
    "taylor-diagram": (
        "make_taylor_diagram.py",
        "泰勒图: 极坐标 σ×arccos(r), REF 星标 + cRMSD 绿虚线等值线, 图例附 R²",
    ),
    "raincloud": (
        "make_raincloud.py",
        "云雨图: 云(KDE 半小提琴)+箱线+雨(抖动散点) 三层叠加, 多组分布对比",
    ),
    "circular-heatmap": (
        "make_circular_heatmap.py",
        "环形热图: N 样本×M 指标径向分层, 外圈样本标签, 右侧归一化色标",
    ),
    "confusion-matrix": (
        "make_confusion_matrix.py",
        "美化混淆矩阵: 计数+行百分比双行标注, 召回率色标, 准确率副标题",
    ),
    "shap-summary": (
        "make_shap_summary.py",
        "SHAP 摘要图: beeswarm/bar 双模式(依赖 shap, 缺失时退出码 3 提示安装)",
    ),
    "chord-diagram": (
        "make_chord_diagram.py",
        "和弦图: 部门迁移矩阵 Circos 弦图(依赖 pycirclize, 缺失时退出码 3)",
    ),
}

ALIASES = {
    "tornado": "tornado-sensitivity",
    "sensitivity": "tornado-sensitivity",
    "allocation": "optimization-allocation",
    "gantt": "optimization-allocation",
    "robustness": "multiscenario-robustness",
    "scenario": "multiscenario-robustness",
    "flowchart": "technical-route-flowchart",
    "route": "technical-route-flowchart",
    "radar": "radar-evaluation",
    "雷达": "radar-evaluation",
    "雷达图": "radar-evaluation",
    "heatmap": "correlation-heatmap",
    "热力图": "correlation-heatmap",
    "相关性": "correlation-heatmap",
    "pareto": "pareto-front",
    "帕累托": "pareto-front",
    "前沿": "pareto-front",
    "prediction": "prediction-fit",
    "预测": "prediction-fit",
    "拟合": "prediction-fit",
    "ranking": "ranking-bar",
    "排序": "ranking-bar",
    "convergence": "convergence-curve",
    "收敛": "convergence-curve",
    "roc": "roc-pr",
    "pr": "roc-pr",
    "判别": "roc-pr",
    "taylor": "taylor-diagram",
    "泰勒图": "taylor-diagram",
    "云雨图": "raincloud",
    "云雨": "raincloud",
    "circular": "circular-heatmap",
    "环形热图": "circular-heatmap",
    "环形": "circular-heatmap",
    "confusion": "confusion-matrix",
    "混淆矩阵": "confusion-matrix",
    "shap": "shap-summary",
    "chord": "chord-diagram",
    "和弦图": "chord-diagram",
}

SKILL_ROOT = Path(__file__).resolve().parents[3]
FIGQA_SCRIPT = SKILL_ROOT / "scripts" / "figqa.py"

# 流程图/技术路线图的盒内标签是合法版式, figqa 硬门固定带 --allow-box-labels;
# 其余模板盒内文字视为碰撞, 用纯 --strict (分模板规则见 references/figure_skill_bridge.md)
BOX_LABEL_TEMPLATES = {"technical-route-flowchart"}


def figqa_hint(template_id: str) -> str:
    """返回该模板推荐的 figqa 硬门命令行（分模板豁免规则）。"""
    flag = " --allow-box-labels" if template_id in BOX_LABEL_TEMPLATES else ""
    return f"python {FIGQA_SCRIPT} <图脚本或输出目录> --strict{flag}"


def resolve(value: str) -> str:
    """把模板 id 或别名解析为标准 id, 未知值时 SystemExit(由 main 捕获转退出码 2)。"""
    key = value.strip().lower().replace("_", "-")
    if key in TEMPLATES:
        return key
    if key in ALIASES:
        return ALIASES[key]
    raise SystemExit(
        f"未知模板: {value}\n可用模板 id: {', '.join(sorted(TEMPLATES))}"
        f"\n别名: {', '.join(sorted(ALIASES))}"
    )


def print_list() -> None:
    """输出模板清单表 + 每个模板推荐的 figqa 硬门命令。"""
    id_width = max(len(k) for k in TEMPLATES) + 2
    file_width = max(len(v[0]) for v in TEMPLATES.values()) + 2
    print(f"{'模板 id'.ljust(id_width)}{'脚本文件'.ljust(file_width)}说明")
    for template_id, (file_name, desc) in sorted(TEMPLATES.items()):
        print(f"{template_id.ljust(id_width)}{file_name.ljust(file_width)}{desc}")
    if ALIASES:
        print(f"\n别名: {', '.join(f'{k} -> {v}' for k, v in sorted(ALIASES.items()))}")
    print("\nfigqa 硬门命令 (分模板; 技术路线图盒内标签合法, 固定加 --allow-box-labels):")
    for template_id in sorted(TEMPLATES):
        print(f"  [{template_id}] {figqa_hint(template_id)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="渲染 v1.0.0 建模图表模板包（17 个模板的统一入口）"
    )
    parser.add_argument("--list", action="store_true", help="列出支持的模板清单")
    parser.add_argument(
        "template", nargs="?", default=None,
        help="模板 id 或别名（radar/heatmap/pareto/prediction/ranking/"
             "convergence/tornado-sensitivity/allocation/robustness/flowchart 等）",
    )
    # REMAINDER 捕获首个位置参数之后的全部内容（含 -- 开头的模板参数）,
    # 不用 argparse 子解析器: 子解析器会把转发参数误判为本脚本的未知项
    parser.add_argument("extra", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.list:
        print_list()
        return 0
    if not args.template:
        parser.error("需要模板 id, 或用 --list 查看清单")
    try:
        # resolve 的 SystemExit 在此转为退出码 2 (docstring 契约),
        # 否则字符串 SystemExit 会被解释成 rc=1
        template_id = resolve(args.template)
    except SystemExit as exc:
        print(str(exc.code if isinstance(exc.code, str) else exc), file=sys.stderr)
        return 2
    script = Path(__file__).resolve().parent / "templates" / TEMPLATES[template_id][0]
    if not script.exists():
        print(f"模板脚本缺失: {script}")
        return 2
    cmd = [sys.executable, str(script), *args.extra]
    print(f"$ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, check=False)
    print(f"\n[提示] 出图后跑该模板的 figqa 硬门: {figqa_hint(template_id)}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
