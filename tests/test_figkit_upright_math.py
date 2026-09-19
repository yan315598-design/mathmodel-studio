# -*- coding: utf-8 -*-
"""B4 图内数学字体正斜政策测试 (v3.1.0)。

背景: 2026 国赛 A 题正文按 cn_presentation_spec §5.6 拍板"全局正体"(631 处
斜体清零), 但图内轴标签仍是斜体数学符号——图文两套字体是最难排查的不一致。
口径:
- `figkit.apply_style()` 默认保持 golden 样张行为（数学符号斜体）;
- `apply_style(upright_math=True)` → `mathtext.default = regular`（图内正体）;
- `apply_style(upright_math=False)` → **显式复位**为常规数学正斜（斜体）:
  `plt.style.use()` 不覆盖 mplstyle 未声明的键, 不复位会让正体跨调用残留;
- `apply_style(upright_math=None)` → 不碰当前政策（mplstyle 里放开
  `mathtext.default : regular` 注释行是第二开启路径, 调用方自设政策时也不该被覆盖）;
- mplstyle 内含开关说明行与注释掉的 `mathtext.default : regular`
  （第二开启路径, 默认不生效）;
- 设计卡第 ④ 要素处登记该政策（figure_skill_bridge.md）。
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "templates" / "figures" / "scripts"
MPLSTYLE = SKILL_ROOT / "templates" / "figures" / "style" / "mathmodel.mplstyle"
BRIDGE = SKILL_ROOT / "references" / "figure_skill_bridge.md"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location("_figkit_b4", SCRIPTS_DIR / "figkit.py")
figkit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = figkit
spec.loader.exec_module(figkit)


class TestUprightMathPolicy(unittest.TestCase):
    """注意: apply_style() 会全局改 rcParams（含 spines 可见性等），
    每个用例必须在 `plt.rc_context()` 里跑——否则会污染同进程其它 lint 测试
    （R7 顶右 spine 用例实测被带崩过）。"""

    def test_default_is_italic(self):
        with plt.rc_context():
            figkit.apply_style()
            self.assertEqual(plt.rcParams["mathtext.default"], "it")

    def test_upright_math_switch(self):
        with plt.rc_context():
            figkit.apply_style(upright_math=True)
            self.assertEqual(plt.rcParams["mathtext.default"], "regular")

    def test_false_restores_italic_after_true(self):
        """True→False 必须切回常规数学正斜。

        `plt.style.use()` 只覆盖样式文件里声明过的键, 而 .mplstyle 不声明
        `mathtext.default`; 不复位的话同一进程里"先画全正体论文的图, 再画
        常规图"就串了（图文两套字体反向版）。
        """
        with plt.rc_context():
            figkit.apply_style(upright_math=True)
            self.assertEqual(plt.rcParams["mathtext.default"], "regular")
            figkit.apply_style(upright_math=False)
            self.assertEqual(plt.rcParams["mathtext.default"], "it")
            figkit.apply_style()          # 默认入参 = False, 同样复位
            self.assertEqual(plt.rcParams["mathtext.default"], "it")

    def test_false_restores_italic_in_inline_fallback(self):
        """mplstyle 缺失走内联回退时, False 同样必须复位（回退分支曾是漏网处:
        它用 rcParams.update 打补丁, 不复位就永远停在 regular）。"""
        missing = MPLSTYLE.with_name("__not_installed__.mplstyle")
        orig = figkit.MPLSTYLE_PATH
        figkit.MPLSTYLE_PATH = missing
        try:
            with plt.rc_context():
                self.assertFalse(figkit.apply_style(upright_math=True),
                                 "回退分支应返回 False（未加载 mplstyle）")
                self.assertEqual(plt.rcParams["mathtext.default"], "regular")
                figkit.apply_style(upright_math=False)
                self.assertEqual(plt.rcParams["mathtext.default"], "it")
        finally:
            figkit.MPLSTYLE_PATH = orig

    def test_none_keeps_external_policy(self):
        """None = 不碰当前政策: mplstyle 放开行启用正体的第二条路径照旧可用。"""
        with plt.rc_context():
            plt.rcParams["mathtext.default"] = "regular"
            figkit.apply_style(upright_math=None)
            self.assertEqual(plt.rcParams["mathtext.default"], "regular",
                             "None 不该覆盖外部设定的正体政策")
            plt.rcParams["mathtext.default"] = "it"
            figkit.apply_style(upright_math=None)
            self.assertEqual(plt.rcParams["mathtext.default"], "it",
                             "None 也不该把外部政策改成正体")
            figkit.apply_style(upright_math=False)   # 显式 False 才复位
            self.assertEqual(plt.rcParams["mathtext.default"], "it")

    def test_style_is_restored_outside_context(self):
        """rc_context 退出后不残留样式改动（防跨文件污染回归）。"""
        before = plt.rcParams["axes.spines.top"]
        with plt.rc_context():
            figkit.apply_style(upright_math=True)
            self.assertFalse(plt.rcParams["axes.spines.top"])
        self.assertEqual(plt.rcParams["axes.spines.top"], before)

    def test_mplstyle_documents_switch(self):
        text = MPLSTYLE.read_text(encoding="utf-8")
        self.assertIn("mathtext.default : regular", text)
        # 注释态（默认不生效）: 生效行本身必须被 # 注释掉
        for line in text.splitlines():
            if line.strip() == "mathtext.default : regular":
                self.fail("mplstyle 里 mathtext.default 未注释, 会默认改变 golden 行为")
        self.assertIn("upright_math=True", text)

    def test_design_card_mentions_policy(self):
        self.assertIn("正斜政策", BRIDGE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
