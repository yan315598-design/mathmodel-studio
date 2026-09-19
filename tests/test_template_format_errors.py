# -*- coding: utf-8 -*-
"""格式化入参与路径报错的资源卫生（A3 清单）。

两件事, 都用**真实模板调用**验证（不只看 figkit.format_label 这个 helper）:

  1. 文案模板/格式规格的占位符收**数值**——传 `"{value:.2e}"` 这类格式规格必须
     生效; 若模板内部先把数值 f-string 成字符串再填, 会报
     "Unknown format code 'e' for object of type 'str'"。
  2. 格式错误与路径错误都不得留资源污染:
     - 不留未关闭的 Figure（figure 进全局管理器会在同进程后续用例/调用里累积,
       长跑流水线上表现为内存爬升与 "More than 20 figures" 警告）;
     - 不动全局 rcParams（apply_style() 会改 spines/网格等; 报错路径若已改过,
       后续调用就继承了半套样式）;
     - 不落半张图（out_stem 处不得出现产物文件）。

路径错误用"父目录被同名文件占位"构造（跨平台稳定的 OSError 分支）: 模板内部
走 figkit.save_fig, 其 mkdir 也在 try/finally 内, figure 必须被 close。
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无显示环境固定 Agg
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "templates" / "figures" / "scripts"
TEMPLATES_DIR = SCRIPTS_DIR / "templates"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# apply_style() 会写的键（报错路径不得改动其中的任何一个）
STYLE_KEYS = (
    "mathtext.default", "axes.spines.top", "axes.spines.right", "axes.linewidth",
    "axes.grid", "axes.axisbelow", "grid.alpha", "grid.linestyle",
    "savefig.dpi", "savefig.bbox", "svg.fonttype", "pdf.fonttype",
    "xtick.direction", "ytick.direction", "legend.frameon", "font.family",
    "axes.unicode_minus", "figure.figsize", "figure.dpi", "lines.linewidth",
)


def style_snapshot() -> dict:
    """取 apply_style() 受影响键的快照, 用于断言报错路径无 rcParams 副作用。"""
    return {key: plt.rcParams[key] for key in STYLE_KEYS}


def load(stem: str):
    """按文件名加载模板模块（模块名独立, 不与其它测试的 sys.modules 键冲突）。"""
    spec = importlib.util.spec_from_file_location(f"_fmterr_{stem}",
                                                 TEMPLATES_DIR / f"{stem}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class ResourceHygieneTestCase(unittest.TestCase):
    """公共装置: 直接调用模板（**不外包 rc_context**）+ 报错后兜底清理。

    评审指摘: 之前把待测调用包在 `plt.rc_context()` 里, 等于让测试装置替实现兜底
    ——异常路径改了 rcParams 也会被 context 退出时还原, 断言恒真（假通过）。
    现在直接调用、直接比快照; 只在本用例确实失败时用 cleanup 把现场还原,
    免得污染同进程其他用例。
    """

    def setUp(self):
        self._fignums_before = set(plt.get_fignums())
        self._rc_snapshot = dict(plt.rcParams)   # 仅用于失败后兜底还原
        self.addCleanup(self._restore_rc)
        self.addCleanup(self._assert_no_leaked_figure)

    def _restore_rc(self):
        plt.rcParams.update(self._rc_snapshot)

    def _assert_no_leaked_figure(self):
        leaked = set(plt.get_fignums()) - self._fignums_before
        for num in leaked:
            plt.close(num)
        self.assertEqual(leaked, set(), "用例结束后仍有未关闭的 Figure（泄漏）")

    def call_expect_error(self, fn, *args, **kwargs):
        """直调模板并断言抛 ValueError/OSError; 返回异常对象。

        直调（无 rc_context）: 报错路径若改过任何受影响键, 断言必须能看见。
        """
        rcs_before = style_snapshot()
        with self.assertRaises((ValueError, OSError)) as ctx:
            fn(*args, **kwargs)
        self.assertEqual(style_snapshot(), rcs_before,
                         "报错路径改动了全局 rcParams（样式副作用）")
        return ctx.exception


class FormatPlaceholderTests(ResourceHygieneTestCase):
    """占位符收数值: 格式规格必须由模板侧生效（不是先 str 再填）。"""

    def test_convergence_best_label_numeric_placeholder(self):
        mod = load("make_convergence_curve")
        histories = {"GA": [10.0, 5.0, 2.0, 1.0]}
        with tempfile.TemporaryDirectory() as td:
            stem = str(Path(td) / "conv")
            with plt.rc_context():
                mod.plot_convergence(histories, 1.0, best_label="{value:.2e}",
                                     out_stem=stem)
            text = Path(stem + ".svg").read_text(encoding="utf-8")
            self.assertIn("1.00e+00", text)      # 格式规格 .2e 真的生效

    def test_convergence_sequence_label_placeholders(self):
        """{p:.2f} / 收敛判据 {value:.1e} 都要按数值格式化（不是字符串代换）。"""
        import math

        import numpy as np

        mod = load("make_convergence_sequence")
        ns = np.array([50.0, 100.0, 200.0, 400.0])
        es = np.array([4e-2, 1e-2, 2.5e-3, 6e-4])
        with tempfile.TemporaryDirectory() as td:
            stem = str(Path(td) / "seq")
            with plt.rc_context():
                mod.plot_convergence_sequence(
                    ns, es, tolerance=1e-3,
                    richardson_label="观测阶 p = {p:.2f}",
                    tolerance_label="判据 {value:.1e}", out_stem=stem)
            text = Path(stem + ".svg").read_text(encoding="utf-8")
            # 观测阶数按 .2f 格式化（与模板内的定阶公式同源计算）
            p_order = math.log(es[0] / es[1]) / math.log(ns[1] / ns[0])
            self.assertIn(f"观测阶 p = {p_order:.2f}", text)
            self.assertIn("判据 1.0e-03", text)

    def test_robustness_baseline_label_numeric_placeholder(self):
        mod = load("make_multiscenario_robustness")
        scenarios = {"场景 A": [1.0, 1.1, 0.9]}
        with tempfile.TemporaryDirectory() as td:
            stem = str(Path(td) / "rob")
            with plt.rc_context():
                mod.plot_robustness(scenarios, 0.85,
                                    baseline_label="承诺 {value:.2e}", out_stem=stem)
            self.assertIn("8.50e-01",
                          Path(stem + ".svg").read_text(encoding="utf-8"))

    def test_ranking_total_fmt_is_format_spec(self):
        """total_fmt 是 format spec（不是模板）: 小数位由它决定。"""
        mod = load("make_ranking_bar")
        scores = {"方案甲": {"成本": 0.8, "效率": 0.6}}
        weights = {"成本": 0.4, "效率": 0.6}
        with tempfile.TemporaryDirectory() as td:
            stem = str(Path(td) / "rank")
            with plt.rc_context():
                mod.plot_ranking(scores, weights, total_fmt=".1%", out_stem=stem)
            self.assertIn("68.0%", Path(stem + ".svg").read_text(encoding="utf-8"))


class FormatErrorTests(ResourceHygieneTestCase):
    """格式串畸形: 建图前抛 ValueError, 不留 Figure / 不留产物 / 不动 rcParams。"""

    def _call_with_bad(self, stem: str, field: str, bad: str, out_stem: str):
        """按 (模板, 畸形入参名) 派发一次真实模板调用（该入参注入畸形值）。"""
        import numpy as np

        mod = load(stem)
        if stem == "make_convergence_curve":
            return mod.plot_convergence({"GA": [10.0, 8.0, 5.0, 3.0, 1.0]}, 1.0,
                                        out_stem=out_stem, **{field: bad})
        if stem == "make_convergence_sequence":
            return mod.plot_convergence_sequence(
                np.array([50.0, 100.0, 200.0, 400.0]),
                np.array([4e-2, 1e-2, 2.5e-3, 6e-4]),
                tolerance=1e-3, out_stem=out_stem, **{field: bad})
        if stem == "make_multiscenario_robustness":
            return mod.plot_robustness({"场景 A": [1.0, 1.1, 0.9]}, 0.85,
                                       out_stem=out_stem, **{field: bad})
        if stem == "make_ranking_bar":
            return mod.plot_ranking({"方案甲": {"成本": 0.8, "效率": 0.6}},
                                    {"成本": 0.4, "效率": 0.6},
                                    out_stem=out_stem, **{field: bad})
        if stem == "make_tornado_sensitivity":
            return mod.plot_tornado([("参数 A", -0.1, 0.15)], out_stem=out_stem,
                                    **{field: bad})
        if stem == "make_threshold_inversion":
            return mod.plot_threshold_inversion(np.linspace(0.0, 10.0, 101),
                                                np.linspace(0.0, 1.0, 101), 0.5,
                                                out_stem=out_stem, **{field: bad})
        raise AssertionError(f"未覆盖的模板: {stem}")

    # (模板 stem, 注入畸形的入参名, 畸形值) —— 覆盖全部格式化入口
    MALFORMED_CASES = (
        ("make_convergence_curve", "best_label", "{"),
        ("make_convergence_curve", "best_label", "{missing}"),
        ("make_convergence_sequence", "gap_fmt", "q"),
        ("make_convergence_sequence", "richardson_label", "{"),
        ("make_convergence_sequence", "tolerance_label", "{value:.2f"),
        ("make_multiscenario_robustness", "baseline_label", "{1}"),
        ("make_ranking_bar", "total_fmt", "q"),
        ("make_tornado_sensitivity", "label_fmt", "{"),
    )

    def test_malformed_formats_raise_before_figure(self):
        """各格式化入口 × 畸形串: ValueError 带入参名, 无产物, 无 Figure/rcParams 残留。"""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            for stem_name, field, bad in self.MALFORMED_CASES:
                with self.subTest(模板=stem_name, 入参=field, 坏值=bad):
                    out = str(tmp / f"bad_{stem_name}_{field}")
                    exc = self.call_expect_error(self._call_with_bad,
                                                 stem_name, field, bad, out)
                    self.assertIn(field, str(exc),
                                  "报错信息未指明是哪个入参（排障要靠它定位）")
                    self.assertEqual(list(tmp.glob(Path(out).name + "*")), [],
                                     "报错路径写出了产物文件")

    def test_valid_spec_still_renders_after_failure(self):
        """报错不污染后续合法调用（同一进程内先坏后好, 好的一次照常出图）。"""
        mod = load("make_ranking_bar")
        scores = {"方案甲": {"成本": 0.8, "效率": 0.6}}
        weights = {"成本": 0.4, "效率": 0.6}
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self.call_expect_error(mod.plot_ranking, scores, weights,
                                   total_fmt="q", out_stem=str(tmp / "bad"))
            with plt.rc_context():
                png, svg = mod.plot_ranking(scores, weights, out_stem=str(tmp / "ok"))
            for path in (png, svg):
                self.assertTrue(path.is_file() and path.stat().st_size > 0, path)


class PathErrorTests(ResourceHygieneTestCase):
    """路径报错: 父目录被同名文件占位 → OSError, figure 必须已 close。"""

    def test_template_path_error_closes_figure(self):
        mod = load("make_convergence_curve")
        with tempfile.TemporaryDirectory() as td:
            blocker = Path(td) / "blocked"
            blocker.write_text("占位文件", encoding="utf-8")
            stem = str(blocker / "out")          # 父目录是文件, mkdir 必失败
            self.call_expect_error(mod.plot_convergence,
                                   {"GA": [10.0, 8.0, 5.0, 3.0, 1.0]}, 1.0,
                                   out_stem=stem)

    def test_save_fig_path_error_closes_figure(self):
        """figkit.save_fig 的 mkdir 也在 try/finally 内（路径错也不漏 figure）。"""
        from figkit import save_fig

        with tempfile.TemporaryDirectory() as td:
            blocker = Path(td) / "blocked"
            blocker.write_text("占位文件", encoding="utf-8")
            fig = plt.figure()
            num = fig.number
            with self.assertRaises(OSError):
                save_fig(fig, str(blocker / "out"))
            self.assertNotIn(num, plt.get_fignums(),
                             "路径报错后 figure 未关闭")


class GanttUnitConsistencyTests(ResourceHygieneTestCase):
    """甘特: 轴名与条端时长标签共用同一单位（不再一图两套单位）+ 不静默取整。"""

    TASKS = [("工序 A", 0.0, 2.0, "设备"), ("工序 B", 2.0, 3.0, "人力"),
             ("工序 C", 5.5, 1.5, "设备")]

    def _render_svg(self, name: str, **kwargs) -> str:
        mod = load("make_optimization_allocation")
        with tempfile.TemporaryDirectory() as td:
            stem = str(Path(td) / name)
            mod.plot_gantt(self.TASKS, out_stem=stem, **kwargs)
            return Path(stem + ".svg").read_text(encoding="utf-8")

    def test_default_unit_day(self):
        text = self._render_svg("gantt")
        self.assertIn("执行时间（天）", text)   # 轴名
        self.assertIn("2 天", text)            # 条端时长（同一单位）
        self.assertIn("3 天", text)

    def test_unit_switch_applies_to_axis_and_bar_ends(self):
        text = self._render_svg("gantt_h", unit="小时")
        self.assertIn("执行时间（小时）", text)
        self.assertIn("2 小时", text)
        self.assertIn("3 小时", text)
        self.assertNotIn("天", text, "同一张图里混了两套时间单位")

    def test_non_integer_duration_not_silently_rounded(self):
        """0.5 步长的时长必须原样印出（老默认 .0f 会把 1.5 印成 "2", 读数与条长不符）。"""
        text = self._render_svg("gantt_frac", unit="小时")
        self.assertIn("1.5 小时", text)            # 1.5 不许被静默取整
        self.assertEqual(text.count("2 小时"), 1)  # "2 小时" 只来自 2.0 那一条
        self.assertIn("3 小时", text)

    def test_explicit_duration_fmt_keeps_rounding(self):
        """显式传 .0f 时取整行为保留（老口径仍可用, 只是必须显式声明）。"""
        text = self._render_svg("gantt_round", unit="小时", duration_fmt=".0f")
        self.assertIn("2 小时", text)
        self.assertNotIn("1.5 小时", text)

    def test_malformed_duration_fmt_raises_before_figure(self):
        mod = load("make_optimization_allocation")
        with tempfile.TemporaryDirectory() as td:
            stem = str(Path(td) / "bad")
            exc = self.call_expect_error(mod.plot_gantt, self.TASKS,
                                         out_stem=stem, duration_fmt="q")
            self.assertIn("duration_fmt", str(exc))
            self.assertEqual(list(Path(td).iterdir()), [], "报错路径写出了产物")


class LegendAvoidsCriterionLineTests(ResourceHygieneTestCase):
    """收敛序列: 有判据线时图例默认外置（judge 复核: lower left 曾盖住 1e-3 红判据线）。"""

    def _fig(self, tolerance: float | None = 1e-3, **kwargs):
        import numpy as np

        mod = load("make_convergence_sequence")
        holder = {}
        orig = mod.save_fig

        def _keep(fig, out_prefix, **kw):
            holder["fig"] = fig
            kw.setdefault("close", False)
            return orig(fig, out_prefix, **kw)

        mod.save_fig = _keep
        try:
            with tempfile.TemporaryDirectory() as td:
                mod.plot_convergence_sequence(
                    np.array([50.0, 100.0, 200.0, 400.0]),
                    np.array([4e-2, 1e-2, 2.5e-3, 6e-4]),
                    tolerance=tolerance, out_stem=str(Path(td) / "x"), **kwargs)
        finally:
            mod.save_fig = orig
        fig = holder["fig"]
        self.addCleanup(plt.close, fig)
        return fig

    def test_default_legend_is_outside_axes_with_criterion_line(self):
        fig = self._fig()
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        ax = fig.axes[0]
        legend = ax.get_legend()
        self.assertIsNotNone(legend, "未生成图例")
        lb = legend.get_window_extent(renderer)
        ab = ax.get_window_extent(renderer)
        # 外置 = 与轴区不相交（右置会改轴宽把档差标签拉进参考线, 故实现在轴上方）
        self.assertFalse(lb.overlaps(ab),
                         f"图例 {lb.bounds} 仍在轴区 {ab.bounds} 内: 判据线是全宽"
                         f"水平线, 轴内任一角都可能压线")
        # 判据线确实画了（前置: 用例踩中带判据线的场景）
        ys = [ln.get_ydata()[0] for ln in ax.lines if len(ln.get_ydata()) == 2
              and abs(float(ln.get_ydata()[0]) - 1e-3) < 1e-15]
        self.assertTrue(ys, "用例未画判据线, 失去意义")

    def test_explicit_legend_loc_stays_inside(self):
        fig = self._fig(legend_loc="lower left")
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        ax = fig.axes[0]
        lb = ax.get_legend().get_window_extent(renderer)
        ab = ax.get_window_extent(renderer)
        self.assertGreater(lb.x0, ab.x0, "显式 legend_loc 应仍放轴内（用户可控）")
        self.assertLess(lb.x1, ab.x1 + 0.5)

    def test_no_criterion_line_keeps_lower_left_default(self):
        fig = self._fig(tolerance=None)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        ax = fig.axes[0]
        lb = ax.get_legend().get_window_extent(renderer)
        ab = ax.get_window_extent(renderer)
        self.assertLess(lb.x1, ab.x1 + 0.5, "无判据线时不该外置（保持旧默认）")
        self.assertLess(lb.y1, (ab.y0 + ab.y1) / 2, "应落在下半区（lower）")


class GapAnnotationSemanticsTests(ResourceHygieneTestCase):
    """档差标注的语义与可读性（judge 复核: 裸数值被读成点值）。

    锁三件事:
      1. 值确实是相邻档差 e_i − e_{i+1}（不是点值、不是累计差）;
      2. 默认带 "Δ" 前缀（自述"这是差值"）, 裸数值不再是默认;
      3. 旧口径可用（显式传 gap_prefix=""）。
    """

    NS = (50.0, 100.0, 200.0, 400.0)

    def _render(self, **kwargs) -> str:
        import numpy as np

        mod = load("make_convergence_sequence")
        with tempfile.TemporaryDirectory() as td:
            stem = str(Path(td) / "seq")
            mod.plot_convergence_sequence(
                np.array(self.NS), np.array([4e-2, 1e-2, 2.5e-3, 6e-4]),
                out_stem=stem, **kwargs)
            return Path(stem + ".svg").read_text(encoding="utf-8")

    def test_default_labels_are_prefixed_adjacent_differences(self):
        text = self._render()
        gaps = [f"{4e-2 - 1e-2:.1e}", f"{1e-2 - 2.5e-3:.1e}", f"{2.5e-3 - 6e-4:.1e}"]
        for gap in gaps:
            self.assertIn("Δ" + gap, text, f"档差 {gap} 未带 Δ 前缀（裸数不可读）")
        # 点值不得冒充档差: 数据点值一个都不该以 "Δ" 前缀出现
        for point in ("4.0e-02", "1.0e-02", "2.5e-03", "6.0e-04"):
            self.assertNotIn("Δ" + point, text,
                             f"{point} 是点值, 不该被标成档差")

    def test_prefix_is_configurable_and_bare_numbers_available(self):
        text = self._render(gap_prefix="")
        self.assertIn("3.0e-02", text)
        self.assertNotIn("Δ3.0e-02", text, "显式空前缀时不该再带 Δ")
        text = self._render(gap_prefix="Δe= ")
        self.assertIn("Δe= 3.0e-02", text)

    def test_gap_values_are_not_point_values(self):
        """单档差数据: 标注必须等于差值, 且不等于任何点值。"""
        import numpy as np

        mod = load("make_convergence_sequence")
        with tempfile.TemporaryDirectory() as td:
            stem = str(Path(td) / "seq2")
            mod.plot_convergence_sequence(
                np.array([100.0, 200.0, 400.0]), np.array([1.0e-2, 4.0e-3, 1.0e-3]),
                out_stem=stem)
            text = Path(stem + ".svg").read_text(encoding="utf-8")
        self.assertIn("Δ6.0e-03", text)          # 1.0e-2 − 4.0e-3
        self.assertIn("Δ3.0e-03", text)          # 4.0e-3 − 1.0e-3
        for point in ("1.0e-02", "4.0e-03", "1.0e-03"):
            self.assertNotIn("Δ" + point, text, f"点值 {point} 被误标成档差")

    def test_omitted_gap_labels_warn_with_interval_and_value(self):
        """两个候选落点都被参考线穿过: 允许省略, 但**必须出 WARN**（评审 P2）。

        省略是版面兜底, 不是静默丢信息: stdout 要写明省略的区间（N=…→…）与该区间
        的差值, 方便图注补值; 同时返回契约与产物不变（仍三格式落盘）。
        """
        import contextlib
        import io

        import numpy as np

        mod = load("make_convergence_sequence")
        with tempfile.TemporaryDirectory() as td:
            stem = str(Path(td) / "omitted")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ret = mod.plot_convergence_sequence(
                    np.array([100.0, 101.0, 102.0]), np.array([1.0, 0.1, 0.01]),
                    gap_prefix="Δe = adjacent difference ", out_stem=stem)
            out = buf.getvalue()
            self.assertEqual([Path(p).suffix for p in ret], [".png", ".svg"],
                             "省略路径不得改变返回契约")
            for ext in (".png", ".svg", ".pdf"):
                f = Path(stem + ext)
                self.assertTrue(f.is_file() and f.stat().st_size > 0, f"缺产物 {f}")
            svg_text = Path(stem + ".svg").read_text(encoding="utf-8")
        self.assertIn("已省略", out, f"省略未出提示:\n{out}")
        self.assertIn("N=100→101", out, f"提示未写明区间:\n{out}")
        self.assertIn("N=101→102", out, f"提示未写明区间:\n{out}")
        self.assertIn("9.0e-01", out, f"提示未写明差值:\n{out}")
        self.assertIn("9.0e-02", out, f"提示未写明差值:\n{out}")
        # 图内确实没画这两只标签（省略生效, 不是画了又提示）
        self.assertNotIn("adjacent difference", svg_text)


if __name__ == "__main__":
    unittest.main()
