"""figure_lint R8 图内图题规则单测（1.4.1 图题纪律）。

覆盖: 非空 suptitle -> ERROR; 单面板非空 title -> ERROR;
colorbar/twinx 附属轴不改变单面板判定（加 colorbar / twinx 后仍报 ERROR）;
loc="left"/"right" 标题同样检出; 多面板 ≤6 中文字符当量短标签 -> PASS;
超宽 -> WARN; 逃生门 --allow-infigure-title / allow_infigure_title=True 跳过全部 R8 检查。
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


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


class FigureLintR8Tests(unittest.TestCase):
    """R8: 图名应放在论文 caption, 不在图内。"""

    @classmethod
    def setUpClass(cls):
        # figure_lint 顶层 `from figqa import ...` 需要 scripts/ 可导入
        sys.path.insert(0, str(SCRIPTS_DIR))
        cls.figure_lint = load_module(FIGURE_LINT_PATH, "figure_lint_for_r8_tests")
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        cls.plt = plt

    @classmethod
    def tearDownClass(cls):
        cls.plt.close("all")

    def _r8(self, fig, **kwargs):
        return [
            v for v in self.figure_lint.lint_figure(fig, "R8 测试图", **kwargs)
            if v.rule.startswith("R8")
        ]

    def test_suptitle_is_error(self):
        """非空 fig.suptitle -> ERROR（计入退出码）。"""
        fig = self.plt.figure()
        ax = fig.add_subplot()
        ax.plot([0, 1], [0, 1])
        fig.suptitle("不该烘焙进图的总标题")
        found = self._r8(fig)
        self.assertTrue(found)
        self.assertTrue(all(v.severity == "error" for v in found))
        self.assertIn("caption", found[0].detail)
        self.plt.close(fig)

    def test_single_panel_title_is_error(self):
        """单面板（fig.axes 长度 1）且该 axes 非空 title -> ERROR。"""
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        ax.set_title("单面板图名")
        found = self._r8(fig)
        self.assertTrue(found)
        self.assertTrue(all(v.severity == "error" for v in found))
        self.assertIn("caption", found[0].detail)
        self.plt.close(fig)

    def test_multi_panel_short_labels_pass(self):
        """多面板 ≤6 中文字符当量短标签 -> 无 R8 违例。"""
        fig, axes = self.plt.subplots(1, 2)
        axes[0].plot([0, 1], [0, 1])
        axes[0].set_title("ROC")
        axes[1].plot([0, 1], [1, 0])
        axes[1].set_title("残差")
        self.assertEqual(self._r8(fig), [])
        self.plt.close(fig)

    def test_multi_panel_long_label_warns(self):
        """多面板标题 >6 中文字符当量 -> WARN（非 ERROR）。"""
        fig, axes = self.plt.subplots(1, 2)
        axes[0].plot([0, 1], [0, 1])
        axes[0].set_title("这是一个远超六个中文字符当量上限的面板标题")
        axes[1].plot([0, 1], [1, 0])
        found = self._r8(fig)
        self.assertTrue(found)
        self.assertTrue(all(v.severity == "warn" for v in found))
        self.plt.close(fig)

    def test_colorbar_single_panel_title_is_error(self):
        """单热力图 + fig.colorbar 后 fig.axes 长度变 2, 仍按单面板报 ERROR。"""
        fig, ax = self.plt.subplots()
        im = ax.imshow(np.random.rand(3, 3), cmap="viridis")
        fig.colorbar(im, ax=ax)
        ax.set_title("热力图单面板图名")
        found = self._r8(fig)
        self.assertTrue(found)
        self.assertTrue(all(v.severity == "error" for v in found))
        self.assertIn("caption", found[0].detail)
        self.plt.close(fig)

    def test_colorbar_without_private_attr_still_single_panel(self):
        """模拟旧版 matplotlib: colorbar 轴无 _colorbar 私有属性时,
        靠默认 label '<colorbar>' 回退识别, 单面板标题仍报 ERROR。"""
        fig, ax = self.plt.subplots()
        im = ax.imshow(np.random.rand(3, 3), cmap="viridis")
        cbar = fig.colorbar(im, ax=ax)
        for a in fig.axes:
            if a is not ax and hasattr(a, "_colorbar"):
                del a._colorbar
        self.assertEqual(cbar.ax.get_label(), "<colorbar>")
        ax.set_title("热力图单面板图名")
        found = self._r8(fig)
        self.assertTrue(found)
        self.assertTrue(all(v.severity == "error" for v in found))
        self.plt.close(fig)

    def test_twinx_single_panel_title_is_error(self):
        """单面板 + twinx 双轴（两 axes 共享绘图区）仍按单面板报 ERROR。"""
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        axr = ax.twinx()
        axr.plot([0, 1], [1, 0])
        ax.set_title("双轴单面板图名")
        found = self._r8(fig)
        self.assertTrue(found)
        self.assertTrue(all(v.severity == "error" for v in found))
        self.plt.close(fig)

    def test_left_loc_title_is_error(self):
        """set_title(loc="left") 后居中位 get_title() 为空, 三位置全查才不漏检。"""
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        ax.set_title("放在左侧的单面板图名不应漏检", loc="left")
        found = self._r8(fig)
        self.assertTrue(found)
        self.assertTrue(all(v.severity == "error" for v in found))
        self.plt.close(fig)

    def test_right_loc_short_label_multi_panel_pass(self):
        """多面板 loc="right" ≤6 当量短标签 -> 无 R8 违例（PASS）。"""
        fig, axes = self.plt.subplots(1, 2)
        axes[0].plot([0, 1], [0, 1])
        axes[0].set_title("ROC", loc="right")
        axes[1].plot([0, 1], [1, 0])
        axes[1].set_title("残差", loc="right")
        self.assertEqual(self._r8(fig), [])
        self.plt.close(fig)

    def test_escape_hatch_skips_r8(self):
        """allow_infigure_title=True 跳过全部 R8 检查（示意图逃生门）。"""
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        ax.set_title("示意图标题")
        fig.suptitle("示意图总标题")
        self.assertEqual(self._r8(fig, allow_infigure_title=True), [])
        self.plt.close(fig)


class FigureLintR8CliTests(unittest.TestCase):
    """CLI 逃生门 --allow-infigure-title 的退出码行为。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS_DIR))
        cls.figure_lint = load_module(FIGURE_LINT_PATH, "figure_lint_for_r8_cli_tests")

    @staticmethod
    def _write_script(tmp: Path) -> Path:
        script = tmp / "r8_cli_case.py"
        script.write_text(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "fig, ax = plt.subplots()\n"
            "ax.plot([0, 1], [0, 1])\n"
            "fig.suptitle('图内总标题')\n",
            encoding="utf-8",
        )
        return script

    def test_cli_suptitle_fails_without_escape(self):
        """默认: 带非空 suptitle 的脚本退出码 1。"""
        with tempfile.TemporaryDirectory() as td:
            script = self._write_script(Path(td))
            self.assertEqual(self.figure_lint.main([str(script)]), 1)

    def test_cli_escape_door_passes(self):
        """--allow-infigure-title: 同一脚本退出码 0。"""
        with tempfile.TemporaryDirectory() as td:
            script = self._write_script(Path(td))
            self.assertEqual(
                self.figure_lint.main([str(script), "--allow-infigure-title"]), 0
            )


if __name__ == "__main__":
    unittest.main()
