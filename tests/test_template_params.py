# -*- coding: utf-8 -*-
"""B1 版式决策参数化回归: 新入参生效 + 默认值不变 (清单 B1)。

背景 (2026 A 题实战): 图叙事 golden 样张的版式决策没全部成为入参, 项目侧被迫
写薄封装承接 (S-09 field-contour 轴标签硬编码等)。本批把"被改写的点"统一暴露
为入参, 默认值 = 原字面量 (向后兼容: 不传参与改前产物一致)。

口径:
- 生效判据: 传自定义文案 → 产物 SVG 文本层出现该文案 (figkit 已设
  `svg.fonttype=none`, 文字保留为可检索文本);
- 默认判据: 不传参 → 出现原默认文案 (现行为不变);
- 签名判据: 关键入参名出现在函数签名里 (防回归删除);
- gantt/xlabel 等纯轴名入参同理。
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无显示环境 (CI/子进程) 固定 Agg

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "templates" / "figures" / "scripts"
TEMPLATES_DIR = SCRIPTS_DIR / "templates"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

_LOADED: dict[str, object] = {}


def load(stem: str):
    """按文件名加载模板模块 (与工作区 import_template 同手法)。"""
    if stem in _LOADED:
        return _LOADED[stem]
    spec = importlib.util.spec_from_file_location(f"_b1_{stem}", TEMPLATES_DIR / f"{stem}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    _LOADED[stem] = mod
    return mod


def render_text(fn, tmp: Path, **kwargs) -> str:
    """调模板函数渲染到 tmp/x, 返回 SVG 文本层 (可直接断言文案)。

    输出入参名按模板约定自动适配 (out_stem 或 out_prefix)。
    **在 plt.rc_context() 内渲染**: 模板内部会调 apply_style() 改全局 rcParams
    (spines 可见性等), 不隔离会污染同进程的 figure_lint 用例 (审查实测)。
    """
    import inspect

    import matplotlib.pyplot as plt

    params = inspect.signature(fn).parameters
    key = "out_stem" if "out_stem" in params else "out_prefix"
    kwargs[key] = str(tmp / "x")
    with plt.rc_context():
        fn(**kwargs)
    svg = tmp / "x.svg"
    assert svg.is_file(), f"未写出 SVG: {svg}"
    return svg.read_text(encoding="utf-8")


def legend_anchor(text: str) -> tuple[float, float] | None:
    """取 SVG 中 legend_1 组内首个文本的 (x, y) —— 用于断言图例位置真的改变。

    (审查指摘: 只断言文本存在不足以证明 legend_loc 生效。)
    """
    import re

    idx = text.find('id="legend_1"')
    if idx < 0:
        return None
    match = re.search(r'<text[^>]*x="([\d.]+)"[^>]*y="([\d.]+)"', text[idx:idx + 3000])
    return (float(match.group(1)), float(match.group(2))) if match else None


def has_param(stem: str, fn_name: str, *names: str) -> None:
    """签名守卫: 关键入参必须存在。"""
    import inspect

    mod = load(stem)
    params = inspect.signature(getattr(mod, fn_name)).parameters
    for name in names:
        assert name in params, f"{stem}.{fn_name} 缺少入参 {name!r}"


class TestFieldClassParams(unittest.TestCase):
    """场/剖面/路径类 (工作区薄封装直接受益的 6 件)。"""

    def _mesh(self):
        import numpy as np

        x = np.linspace(0.0, 1.0, 12)
        y = np.linspace(0.0, 1.0, 10)
        X, Y = np.meshgrid(x, y)
        return X, Y

    def test_field_contour_labels_and_legend_loc(self):
        import numpy as np

        has_param("make_field_contour", "plot_field_contour",
                  "xlabel", "ylabel", "legend_loc")
        mod = load("make_field_contour")
        X, Y = self._mesh()
        field = np.hypot(X - 0.5, Y - 0.5)
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            text = render_text(mod.plot_field_contour, tmp, X=X, Y=Y, fields=[field],
                               criterion=0.3, xlabel="时间 t (s)",
                               ylabel="径向距离 r (mm)", legend_loc="lower left")
            self.assertIn("时间 t (s)", text)
            self.assertIn("径向距离 r (mm)", text)
            left_anchor = legend_anchor(text)
            self.assertIsNotNone(left_anchor, "未解析到图例锚点")
            text = render_text(mod.plot_field_contour, tmp, X=X, Y=Y, fields=[field],
                               criterion=0.3)
            self.assertIn("x (cm)", text)  # 默认不变
            default_anchor = legend_anchor(text)
            self.assertIsNotNone(default_anchor)
            # legend_loc 真的改变了图例位置（upper left vs lower left: y 差一个轴高）
            self.assertGreater(abs(left_anchor[1] - default_anchor[1]), 5.0)
            self.assertNotEqual(left_anchor, default_anchor)

    def test_route_on_field_start_end_and_legend(self):
        import numpy as np

        has_param("make_route_on_field", "plot_route_on_field",
                  "xlabel", "ylabel", "start_label", "end_label", "legend_loc")
        mod = load("make_route_on_field")
        X, Y = self._mesh()
        field = np.hypot(X - 0.5, Y - 0.5)
        route = np.array([[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]])
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            text = render_text(mod.plot_route_on_field, tmp, X=X, Y=Y, field=field,
                               route=route, start_label="出发港", end_label="目的港",
                               legend_loc="lower left")
            self.assertIn("出发港", text)
            self.assertIn("目的港", text)
            text = render_text(mod.plot_route_on_field, tmp, X=X, Y=Y, field=field,
                               route=route)
            self.assertIn("起点", text)
            self.assertIn("终点", text)

    def test_profile_family_legend_loc(self):
        import numpy as np

        has_param("make_profile_family", "plot_profile_family", "legend_loc")
        mod = load("make_profile_family")
        depth = np.linspace(0.0, 1.0, 20)
        profiles = [depth * k for k in (0.5, 1.0, 1.5)]
        with tempfile.TemporaryDirectory() as td:
            text = render_text(mod.plot_profile_family, Path(td), depth=depth,
                               profiles=profiles, values=[1.0, 2.0, 3.0],
                               criterion=1.2, legend_loc="lower right")
            self.assertIn("判据线", text)

    def test_contrast_pair_legend_loc(self):
        import numpy as np

        has_param("make_contrast_pair", "plot_contrast_pair", "xlabel", "ylabel",
                  "legend_loc")
        mod = load("make_contrast_pair")
        X, Y = self._mesh()
        a = np.hypot(X - 0.5, Y - 0.5)
        with tempfile.TemporaryDirectory() as td:
            text = render_text(mod.plot_contrast_pair, Path(td), X=X, Y=Y,
                               field_a=a, field_b=a * 1.2, diff_threshold=0.1,
                               legend_loc="upper left")
            self.assertIn("|Δ| &gt;", text)  # SVG 文本层把 > 转义为 &gt;

    def test_threshold_inversion_legend_loc_and_star(self):
        import numpy as np

        has_param("make_threshold_inversion", "plot_threshold_inversion",
                  "param_label", "metric_label", "star_symbol", "legend_loc")
        mod = load("make_threshold_inversion")
        param = np.linspace(0.0, 10.0, 101)
        metric = np.linspace(0.0, 1.0, 101)
        with tempfile.TemporaryDirectory() as td:
            text = render_text(mod.plot_threshold_inversion, Path(td), param=param,
                               metric=metric, threshold=0.5, star_symbol="t*",
                               legend_loc="lower left")
            self.assertIn("t*", text)


class TestLabelClassParams(unittest.TestCase):
    """热力/分类/评价/预测类的文案与标题入参。"""

    def test_confusion_matrix_labels(self):
        import numpy as np

        has_param("make_confusion_matrix", "plot_confusion_matrix",
                  "xlabel", "ylabel", "cbar_label")
        mod = load("make_confusion_matrix")
        matrix = np.array([[8, 2], [1, 9]])
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            text = render_text(mod.plot_confusion_matrix, tmp, matrix=matrix,
                               class_names=["A", "B"], xlabel="Predicted",
                               ylabel="Actual", cbar_label="Recall")
            self.assertIn("Predicted", text)
            self.assertIn("Actual", text)
            self.assertIn("Recall", text)
            text = render_text(mod.plot_confusion_matrix, tmp, matrix=matrix,
                               class_names=["A", "B"])
            self.assertIn("预测类别", text)
            self.assertIn("真实类别", text)

    def test_circular_heatmap_cbar_label(self):
        import numpy as np

        has_param("make_circular_heatmap", "plot_circular_heatmap", "cbar_label")
        mod = load("make_circular_heatmap")
        values = np.linspace(0.0, 1.0, 12).reshape(4, 3)
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            text = render_text(mod.plot_circular_heatmap, tmp, values=values,
                               sample_names=["S1", "S2", "S3", "S4"],
                               metric_names=["m1", "m2", "m3"],
                               cbar_label="归一化硫含量")
            self.assertIn("归一化硫含量", text)
            text = render_text(mod.plot_circular_heatmap, tmp, values=values,
                               sample_names=["S1", "S2", "S3", "S4"],
                               metric_names=["m1", "m2", "m3"])
            self.assertIn("归一化得分", text)

    def test_correlation_heatmap_significance_note(self):
        import numpy as np

        has_param("make_correlation_heatmap", "plot_heatmap", "significance_note")
        mod = load("make_correlation_heatmap")
        matrix = np.array([[1.0, 0.4], [0.4, 1.0]])
        pvalues = np.array([[1.0, 0.01], [0.01, 1.0]])  # 对角 1.0 = 不显著
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            text = render_text(mod.plot_heatmap, tmp, matrix=matrix,
                               row_names=["a", "b"], col_names=["a", "b"],
                               pvalues=pvalues,
                               significance_note="显著性: *** p<0.001")
            self.assertIn("*** p&lt;0.001", text)
            text = render_text(mod.plot_heatmap, tmp, matrix=matrix,
                               row_names=["a", "b"], col_names=["a", "b"],
                               pvalues=pvalues)
            self.assertIn("p&lt;0.01", text)  # 默认脚注在

    def test_gantt_xlabel(self):
        has_param("make_optimization_allocation", "plot_gantt", "xlabel")
        mod = load("make_optimization_allocation")
        tasks = [("工序 A", 0.0, 2.0, "设备"), ("工序 B", 2.0, 3.0, "人力")]
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            text = render_text(mod.plot_gantt, tmp, tasks=tasks,
                               xlabel="执行时间（h）")
            self.assertIn("执行时间（h）", text)
            text = render_text(mod.plot_gantt, tmp, tasks=tasks)
            self.assertIn("执行时间（天）", text)

    def test_roc_pr_panel_titles_and_axis_labels(self):
        import numpy as np

        has_param("make_roc_pr", "plot_roc_pr", "panel_titles", "axis_labels")
        mod = load("make_roc_pr")
        rng = np.random.default_rng(7)
        y = (rng.random(60) > 0.5).astype(float)
        scores = {"M1": np.clip(0.5 + 0.3 * (y - 0.5) + rng.normal(0, 0.15, 60), 0, 1)}
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            text = render_text(mod.plot_roc_pr, tmp, y_true=y, scores=scores,
                               panel_titles=("ROC", "PR", "Calib"),
                               axis_labels={"roc_x": "FPR", "roc_y": "TPR"})
            for expect in ("ROC", "PR", "Calib", "FPR", "TPR"):
                self.assertIn(expect, text)
            text = render_text(mod.plot_roc_pr, tmp, y_true=y, scores=scores)
            self.assertIn("ROC 曲线", text)
            self.assertIn("假正例率（FPR）", text)

    def test_pareto_point_labels(self):
        import numpy as np

        has_param("make_pareto_front", "plot_pareto", "ideal_label", "knee_label")
        mod = load("make_pareto_front")
        pts = [(float(i), float(10 - i) ** 2) for i in range(1, 8)]
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            text = render_text(mod.plot_pareto, tmp, points=pts,
                               ideal_label="理想解", knee_label="膝点")
            self.assertIn("理想解", text)
            self.assertIn("膝点", text)
            text = render_text(mod.plot_pareto, tmp, points=pts)
            self.assertIn("理想点", text)
            self.assertIn("折中点", text)
            # 空串关闭该标注
            text = render_text(mod.plot_pareto, tmp, points=pts, knee_label="")
            self.assertNotIn("折中点", text)

    def test_prediction_fit_panel_titles(self):
        has_param("make_prediction_fit", "plot_prediction", "panel_titles")
        mod = load("make_prediction_fit")
        actual = [1.0, 1.1, 1.2, 1.3, 1.4]
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            text = render_text(mod.plot_prediction, tmp, actual=actual,
                               prediction=[1.0, 1.1, 1.2, 1.3, 1.4],
                               panel_titles=("(a) 序列", "(b) 偏差"))
            self.assertIn("(a) 序列", text)
            self.assertIn("(b) 偏差", text)
            text = render_text(mod.plot_prediction, tmp, actual=actual,
                               prediction=[1.0, 1.1, 1.2, 1.3, 1.4])
            self.assertIn("(a) 拟合", text)
            self.assertIn("(b) 残差", text)

    def test_taylor_note(self):
        has_param("make_taylor_diagram", "plot_taylor", "note")
        mod = load("make_taylor_diagram")
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            text = render_text(mod.plot_taylor, tmp, obs_sigma=1.6,
                               models=[("A", 1.5, 0.9)], note="径向 σ　角度 r")
            self.assertIn("径向 σ", text)
            text = render_text(mod.plot_taylor, tmp, obs_sigma=1.6,
                               models=[("A", 1.5, 0.9)], note="")
            self.assertNotIn("arccos", text)

    def test_shap_note(self):
        try:
            import shap  # noqa: F401
        except ImportError:
            self.skipTest("未安装 shap, 按约定跳过")
        import numpy as np

        has_param("make_shap_summary", "plot_shap_summary", "note")
        mod = load("make_shap_summary")
        rng = np.random.default_rng(3)
        values = rng.normal(size=(30, 4))
        feats = rng.normal(size=(30, 4))
        names = ["f1", "f2", "f3", "f4"]
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            text = render_text(mod.plot_shap_summary, tmp, shap_values=values,
                               features=feats, feature_names=names,
                               note="正值推高风险")
            self.assertIn("正值推高风险", text)


class TestFormatParams(unittest.TestCase):
    """审查 high 回归: 默认格式参数必须可用（多一层花括号曾让默认调用直接 ValueError）。"""

    def test_tornado_default_and_three_formats(self):
        has_param("make_tornado_sensitivity", "plot_tornado", "label_fmt")
        mod = load("make_tornado_sensitivity")
        params = [("参数 A", -0.10, 0.15), ("参数 B", 0.05, -0.20)]
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            # 默认（完整格式模板 "{:+.1%}"）→ 必须能渲染, 且标签是百分比形态
            text = render_text(mod.plot_tornado, tmp, params=params)
            self.assertIn("%", text)
            # 纯 format spec
            render_text(mod.plot_tornado, tmp, params=params, label_fmt=".4f")
            # 可调用对象
            render_text(mod.plot_tornado, tmp, params=params,
                        label_fmt=lambda v: f"{v:+.2f} h")
            self.assertIn("h", (tmp / "x.svg").read_text(encoding="utf-8"))

    def test_multiscenario_baseline_label_placeholder(self):
        has_param("make_multiscenario_robustness", "plot_robustness",
                  "baseline_label")
        mod = load("make_multiscenario_robustness")
        scenarios = {"方案 A": [1.0, 1.1, 0.9], "方案 B": [1.3, 1.25, 1.35]}
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            text = render_text(mod.plot_robustness, tmp, scenarios=scenarios,
                               baseline=0.85, metric="综合得分",
                               baseline_label="合同承诺 {value:.1%}")
            self.assertIn("85.0%", text)  # 占位符收到数值, 能按 %.1% 格式化
            text = render_text(mod.plot_robustness, tmp, scenarios=scenarios,
                               baseline=0.85, metric="综合得分")
            self.assertIn("基准线 0.850", text)  # 默认不变

    def test_tornado_malformed_format_raises_before_figure(self):
        """审查 low 回归: 畸形格式串必须在建图前抛 ValueError（不留泄漏 Figure）,
        且不得改动全局 rcParams（预格式化在 apply_style 之前, 第四轮审查实测）。"""
        import matplotlib.pyplot as plt

        mod = load("make_tornado_sensitivity")
        params = [("参数 A", -0.10, 0.15)]
        n_before = len(plt.get_fignums())
        spine_before = plt.rcParams["axes.spines.top"]
        for bad in ("{", "{missing}", "{1}"):
            with self.assertRaises(ValueError) as ctx:
                mod.plot_tornado(params, label_fmt=bad)
            self.assertIn("label_fmt", str(ctx.exception))
        self.assertEqual(len(plt.get_fignums()), n_before,
                         "异常路径不得残留未关闭的 Figure")
        self.assertEqual(plt.rcParams["axes.spines.top"], spine_before,
                         "异常路径不得改动全局 rcParams")

    def test_tornado_callable_valid_on_actual_domain(self):
        """审查 med 回归: 只对实际数据域有效的 callable 不得被固定试值误拒。

        `f"{math.log10(v):.2f}"` 在负数试值上会 domain error, 但本题数据全为正 →
        预格式化用**真实数据**逐个做, 应正常渲染。
        """
        import math

        mod = load("make_tornado_sensitivity")
        with tempfile.TemporaryDirectory() as td:
            text = render_text(mod.plot_tornado, Path(td),
                               params=[("参数 A", 0.10, 0.20)],
                               label_fmt=lambda v: f"{math.log10(v):.2f}")
            # 变化率 0.10/0.20 → log10 = -1.00 / -0.70（SVG 里负号为 U+2212 或 -）
            self.assertIn("-1.00", text)
            self.assertIn("-0.70", text)


if __name__ == "__main__":
    unittest.main()
