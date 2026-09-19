# -*- coding: utf-8 -*-
"""建模图表模板包 dispatcher（25 个数据图模板的统一入口）。

示意图（流程图/框架图等）由同目录 render_diagram_pack.py 分发,
drawio 可编辑模板由 render_drawio_pack.py 分发。

用法:
    python render_modeling_pack.py <子命令> [模板参数...]
    python render_modeling_pack.py --list

子命令即模板 id, 其余参数原样转发给模板脚本, 例如:
    python render_modeling_pack.py optimization-allocation --mode gantt --out figs/alloc
    python render_modeling_pack.py tornado --out figs/tornado
    python render_modeling_pack.py heatmap --out figs/heatmap
    python render_modeling_pack.py field-contour --out figs/field
    python render_modeling_pack.py before-after --mode dist --out figs/ba

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
    # ---- 3.0.0 物理场/场景模板（图叙事纪律: 判据层 + 对照构图 + 量化标签）----
    "field-contour": (
        "make_field_contour.py",
        "物理场图: pcolormesh 场 + 红虚线判据等值线 + 共享色标多面板",
    ),
    "profile-family": (
        "make_profile_family.py",
        "剖面族: N 条剖面按连续变量 viridis 渐变着色 + colorbar + 可选判据线",
    ),
    "threshold-inversion": (
        "make_threshold_inversion.py",
        "阈值穿越反演: 主曲线 + 阈值红虚线 + 穿越点 + inset 双边锁定放大",
    ),
    "convergence-sequence": (
        "make_convergence_sequence.py",
        "收敛序列: 误差随离散参数变化 + Richardson 外推虚线 + 档差标注 + log-log 可选",
    ),
    "contrast-pair": (
        "make_contrast_pair.py",
        "对照双联: 同坐标同尺度两面板(前后/两法/两档), 共享色标 + 差异判据圈出",
    ),
    "route-on-field": (
        "make_route_on_field.py",
        "路径叠加场图: 底图场 + 主色路径折线 + 起点星/终点叉/途经点",
    ),
    "answer-grid": (
        "make_answer_grid.py",
        "结果交付网格: M×N 数值/概率热力网格(16×4 范式), 格内自适应黑白数值 + 色条",
    ),
    "before-after": (
        "make_before_after.py",
        "前后对照双联: 同坐标散点(t-SNE 式)或直方分布双模式, 前灰后红",
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
    # ---- 3.0.0 物理场/场景模板别名 ----
    "field": "field-contour",
    "场图": "field-contour",
    "等值线": "field-contour",
    "profile": "profile-family",
    "剖面": "profile-family",
    "剖面族": "profile-family",
    "threshold": "threshold-inversion",
    "反演": "threshold-inversion",
    "穿越": "threshold-inversion",
    "收敛序列": "convergence-sequence",
    "网格收敛": "convergence-sequence",
    "gridconv": "convergence-sequence",
    "contrast": "contrast-pair",
    "对照": "contrast-pair",
    "对照双联": "contrast-pair",
    "路径": "route-on-field",
    "航线": "route-on-field",
    "轨迹": "route-on-field",
    "answer": "answer-grid",
    "结果网格": "answer-grid",
    "答案网格": "answer-grid",
    "before": "before-after",
    "after": "before-after",
    "前后": "before-after",
    "前后对照": "before-after",
}

def _import_skill_paths():
    """导入根路径唯一真源 scripts/skill_paths.py (D1)。

    先按调用路径向上找含 SKILL.md 的 skill 根 (.codex/.zcode 两份安装并存时
    取当前调用的那一份), 把其 scripts/ 挂进 sys.path; 找不到时退回本文件所在安装。
    """
    root = Path(__file__).resolve().parents[3]
    for parent in Path(__file__).absolute().parents:
        if (parent / "SKILL.md").is_file() and (parent / "scripts").is_dir():
            root = parent
            break
    sys.path.insert(0, str(root / "scripts"))
    import skill_paths

    return skill_paths


_skill_paths = _import_skill_paths()
SKILL_ROOT = _skill_paths.skill_root(__file__)
FIGQA_SCRIPT = SKILL_ROOT / "scripts" / "figqa.py"

# 流程图/技术路线图的盒内标签是合法版式, figqa 硬门固定带 --allow-box-labels;
# 其余模板盒内文字视为碰撞, 用纯 --strict (分模板规则见 references/figure_skill_bridge.md)
BOX_LABEL_TEMPLATES = {"technical-route-flowchart"}


def quote_arg(value: object) -> str:
    """回显命令行参数: 含空白的路径加双引号, 复制粘贴到终端即可直接跑。

    安装根常在 `Program Files`、用户目录含空格、项目名带空格——不加引号时
    `--list` 里那条 figqa 命令会被 shell 拆成多个参数而失败（本函数只做回显,
    不参与真正的执行: 真正执行走 subprocess 的列表传参, 无需转义）。
    """
    text = str(value)
    if text and any(ch.isspace() for ch in text) and not (
            text.startswith('"') and text.endswith('"')):
        return f'"{text}"'
    return text


def figqa_hint(template_id: str) -> str:
    """返回该模板推荐的 figqa 硬门命令行（分模板豁免规则）。"""
    flag = " --allow-box-labels" if template_id in BOX_LABEL_TEMPLATES else ""
    return f"python {quote_arg(FIGQA_SCRIPT)} <图脚本或输出目录> --strict{flag}"


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
    print(_skill_paths.describe(__file__))  # V0 日志: 当前使用的安装根 (D1)
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
        description="渲染建模图表模板包（25 个模板的统一入口）"
    )
    parser.add_argument("--list", action="store_true", help="列出支持的模板清单")
    parser.add_argument(
        "template", nargs="?", default=None,
        help="模板 id 或别名（radar/heatmap/pareto/prediction/ranking/"
             "convergence/tornado-sensitivity/allocation/robustness/flowchart/"
             "field-contour/threshold-inversion/answer-grid/before-after 等）",
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
    print(f"$ {' '.join(quote_arg(part) for part in cmd)}", flush=True)
    result = subprocess.run(cmd, check=False)  # 列表传参, 无需 shell 转义
    print(f"\n[提示] 出图后跑该模板的 figqa 硬门: {figqa_hint(template_id)}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
