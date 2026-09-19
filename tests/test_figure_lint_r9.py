# -*- coding: utf-8 -*-
"""figure_lint R9 注释预算规则单测（3.0.0 图叙事纪律）。

覆盖三个回归用例（WP-B B4 规格）:
  1. 超预算报: 数据图面板 3 条解释性文本（> ANNOTATION_BUDGET=2）→ R9 warn;
  2. 判据线图例不报: 判据线走图例（图例文本不计）, 与图例同文的内联
     判据标注同样豁免, 数值标签/面板标号也不计入;
  3. 示意图豁免: allow_box_labels=True（--allow-box-labels / --schematic
     的代码入口）整体跳过 R9。
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
FIGURE_LINT_PATH = SCRIPTS_DIR / "figure_lint.py"


def load_module(path: Path, name: str):
    """从候选 skill 路径加载待测脚本。

    figure_lint 含 @dataclass, 须先注册进 sys.modules 再执行,
    否则 dataclass 解析 cls.__module__ 时找不到模块。
    """
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FigureLintR9Tests(unittest.TestCase):
    """R9: 数据图单面板解释性文本 ≤ ANNOTATION_BUDGET 条。"""

    @classmethod
    def setUpClass(cls):
        # figure_lint 顶层 `from figqa import ...` 需要 scripts/ 可导入
        sys.path.insert(0, str(SCRIPTS_DIR))
        cls.figure_lint = load_module(FIGURE_LINT_PATH, "figure_lint_for_r9_tests")
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        cls.plt = plt

    @classmethod
    def tearDownClass(cls):
        cls.plt.close("all")

    def _r9(self, fig, **kwargs):
        return [
            v for v in self.figure_lint.lint_figure(fig, "R9 测试图", **kwargs)
            if v.rule.startswith("R9")
        ]

    def test_over_budget_panel_warns(self):
        """用例 1: 面板 3 条解释性文本（> 2）→ R9 warn, 消息带预算与豁免提示。"""
        self.assertEqual(self.figure_lint.ANNOTATION_BUDGET, 2)
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        ax.text(0.2, 0.3, "第一条解释性注释")
        ax.text(0.2, 0.5, "第二条解释性注释")
        ax.text(0.2, 0.7, "第三条解释性注释")
        found = self._r9(fig)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, "warn")
        self.assertIn("3 条", found[0].detail)
        self.plt.close(fig)

    def test_criterion_legend_texts_not_counted(self):
        """用例 2: 判据线走图例 + 图例同文内联标注 + 数值标签/面板标号 → 不报。"""
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1], label="指标 S")
        ax.axhline(0.5, color="red", linestyle="--", label="判据阈值 = 0.5")
        ax.legend()
        # 与图例条目同文的内联判据标注（判据线图例对应文本, 豁免）
        ax.text(0.05, 0.53, "判据阈值 = 0.5")
        # 数值标签（量化标签纪律, 豁免）与面板标号 (a)（长度 <4, 豁免）
        ax.text(0.4, 0.42, "0.42")
        ax.text(0.02, 0.98, "(a)")
        self.assertEqual(self._r9(fig), [])
        # 直接锚定豁免逻辑本身: 删除图例同文豁免后此处必须出现该文本
        # (lint 层预算=2 时仅 1 条 note 不报警, 单测会变异存活, 复审 P2-5)
        self.assertEqual(self.figure_lint._explanatory_notes(ax), [])
        self.plt.close(fig)

    def test_polar_category_labels_not_counted(self):
        """用例 4: 极坐标雷达图的类别标签（r > 0.9*rmax 的 ax.text）不计注释 (复审 P1-2)。"""
        import numpy as np
        fig = self.plt.figure()
        ax = fig.add_subplot(111, projection="polar")
        ax.set_rlim(0.0, 1.0)
        for a in np.linspace(0, 2 * np.pi, 6, endpoint=False):
            ax.text(a, 1.155, "物流成本类标签", fontsize=10)
        self.assertEqual(self.figure_lint._explanatory_notes(ax), [])
        self.assertEqual(self._r9(fig), [])
        self.plt.close(fig)

    def test_schematic_flag_exempts_r9(self):
        """用例 3: allow_box_labels=True（--allow-box-labels/--schematic 入口）整体豁免 R9。"""
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        for k in range(5):
            ax.text(0.1, 0.2 + 0.1 * k, f"示意图盒内说明文字{k}")
        self.assertTrue(self._r9(fig))   # 豁免前: 5 条解释性文本必报
        self.plt.close(fig)
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        for k in range(5):
            ax.text(0.1, 0.2 + 0.1 * k, f"示意图盒内说明文字{k}")
        self.assertEqual(self._r9(fig, allow_box_labels=True), [])
        self.plt.close(fig)

    # ---- A7 新增豁免: 等值线数值标签 / 纯数值+单位串 / R4 声明位 ----

    def test_clabel_value_labels_exempt(self):
        """A7: 等值线数值标签（ax.clabel）属量化标签, 不计入注释预算（S-11）。

        差分断言（复审要求的强度）: 同一条长标签文本, 作为 clabel 时豁免（归属
        判据 `QuadContourSet.labelTexts`）, 作为普通 ax.text 时会计入注释——两条
        同时成立才证明豁免来自"对象归属"而非文本形态。
        """
        import numpy as np

        label_text = "等级 0.3（超限）"  # 长且含中文, 两种文本启发式都不豁免
        fig, ax = self.plt.subplots()
        X, Y = np.meshgrid(np.linspace(0, 1, 20), np.linspace(0, 1, 20))
        cs = ax.contour(X, Y, X * Y, levels=[0.3])
        ax.clabel(cs, inline=True, fmt="等级 %g（超限）")
        self.assertEqual([t.get_text() for t in ax.texts], [label_text])
        self.assertEqual(self.figure_lint._explanatory_notes(ax), [])
        self.plt.close(fig)
        # 同文本作为普通文本 → 必须计入
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        ax.text(0.1, 0.5, label_text)
        self.assertEqual(self.figure_lint._explanatory_notes(ax), [label_text])
        self.plt.close(fig)

    def test_pure_value_with_unit_exempt(self):
        """A7: "纯数值+单位"串是量化标签, 不计入预算（直接断言 notes 为空）。

        差分: 同图的纯数值串全部豁免, 而一旦混入英文长句（含数字但不含单位词）
        必须被计入——单靠"旧启发式恰好也豁免短标签"不能通过本用例。
        """
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        texts = ("30 ℃", "0.42 h", "12.5 %", "1.20 m/s",
                 "1.2345 0.9876 0.4567", "kg/kg\n1.2345 0.9876")
        for text in texts:
            ax.text(0.1, 0.5, text)
        self.assertEqual(self.figure_lint._explanatory_notes(ax), [])
        self.plt.close(fig)
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        long_text = "Model improves after 10 iterations"
        ax.text(0.1, 0.5, long_text)
        self.assertEqual(self.figure_lint._explanatory_notes(ax), [long_text])
        self.plt.close(fig)

    def test_pure_value_requires_digit_and_unit_word(self):
        """A7 反例回归: 纯字母串与"含数字的英文长句"都不得被误豁免（两轮复审实测）。"""
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        for text in ("Hmm...", "hmmm", "shhh", "Error decreases by 20 percent",
                     "Stop after 100 iterations"):
            ax.text(0.1, 0.5, text)
        self.assertEqual(sorted(self.figure_lint._explanatory_notes(ax)),
                         sorted(["Hmm...", "hmmm", "shhh",
                                 "Error decreases by 20 percent",
                                 "Stop after 100 iterations"]))
        self.plt.close(fig)

    def test_explanatory_sentence_still_counted(self):
        """A7 豁免不放松解释性长句: 3 条解释性注释仍报 R9。"""
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        for text in ("第一次出现极值", "曲线在此处转折", "该段几乎水平"):
            ax.text(0.1, 0.5, text)
        rules = [v.rule for v in self._r9(fig)]
        self.assertTrue(any(r.startswith("R9") for r in rules))
        self.plt.close(fig)

    def test_grid_annotate_declaration_exempts_r4(self):
        """A7: --grid-annotate 声明位跳过 R4（格注+色条并存有理由）。"""
        import numpy as np

        fig, ax = self.plt.subplots()
        ax.imshow(np.arange(9).reshape(3, 3), cmap="viridis")
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{i * 3 + j}")
        fig.colorbar(ax.images[0], ax=ax)
        self.assertTrue(any(v.rule.startswith("R4")
                            for v in self.figure_lint.lint_figure(fig, "R4 默认")))
        self.assertFalse(any(v.rule.startswith("R4")
                             for v in self.figure_lint.lint_figure(
                                 fig, "R4 声明豁免", grid_annotate=True)))
        self.plt.close(fig)


class FigureLintR9CliTests(unittest.TestCase):
    """CLI 豁免门 --allow-box-labels / --schematic 的退出码行为。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS_DIR))
        cls.figure_lint = load_module(FIGURE_LINT_PATH, "figure_lint_for_r9_cli_tests")

    @staticmethod
    def _write_script(tmp: Path) -> Path:
        script = tmp / "r9_cli_case.py"
        # 顶/右 spines 去除（避免 R7 在 --strict 下抢戏, 本测试只考察 R9）
        script.write_text(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "fig, ax = plt.subplots()\n"
            "ax.plot([0, 1], [0, 1])\n"
            "ax.spines['top'].set_visible(False)\n"
            "ax.spines['right'].set_visible(False)\n"
            "ax.text(0.2, 0.3, '第一条解释性注释')\n"
            "ax.text(0.2, 0.5, '第二条解释性注释')\n"
            "ax.text(0.2, 0.7, '第三条解释性注释')\n",
            encoding="utf-8",
        )
        return script

    def test_cli_strict_warn_fails_without_escape(self):
        """--strict-warn 且有 R9 warn → 退出码 1（旧 --strict 语义, A7 起改名）。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            script = self._write_script(Path(td))
            self.assertEqual(
                self.figure_lint.main([str(script), "--strict-warn"]), 1)

    def test_cli_strict_lists_warn_without_failing(self):
        """--strict → warn 只列清单不失败 (A7 新语义: 只拦 error), 退出码 0。"""
        import contextlib
        import io
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            script = self._write_script(Path(td))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = self.figure_lint.main([str(script), "--strict"])
            self.assertEqual(rc, 0)
            self.assertIn("--strict-warn", buf.getvalue())  # 清单末尾给出改判提示

    def test_cli_schematic_flags_pass(self):
        """--schematic（与 --allow-box-labels 等价）→ 退出码 0。"""
        import tempfile

        for flag in ("--allow-box-labels", "--schematic"):
            with tempfile.TemporaryDirectory() as td:
                script = self._write_script(Path(td))
                self.assertEqual(
                    self.figure_lint.main([str(script), "--strict-warn", flag]), 0,
                    msg=f"flag={flag}")

if __name__ == "__main__":
    unittest.main()
