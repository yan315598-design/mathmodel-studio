"""figure_lint R4/R7 降噪回归（T-08）。

覆盖: twinx 双轴图的右 spine 豁免（top 仍需去除）;
大矩阵场图（1801×161）带 colorbar 不触发 R4; 10×10 小热图带 colorbar 仍触发 R4;
_image_matrix_shape 对 imshow 与 pcolormesh 的规模判定。
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
FIGURE_LINT_PATH = SCRIPTS_DIR / "figure_lint.py"


def load_module(path: Path, name: str):
    """从候选 skill 路径加载待测脚本（dataclass 需先注册 sys.modules）。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FigureLintR4R7Tests(unittest.TestCase):
    """T-08 回归: 设计必需的右 spine 与大矩阵 colorbar 不再计为违例。"""

    @classmethod
    def setUpClass(cls):
        # figure_lint 顶层 `from figqa import ...` 需要 scripts/ 可导入
        sys.path.insert(0, str(SCRIPTS_DIR))
        cls.figure_lint = load_module(FIGURE_LINT_PATH, "figure_lint_for_r4r7_tests")
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        cls.plt = plt

    @classmethod
    def tearDownClass(cls):
        cls.plt.close("all")

    def _violations(self, fig):
        return self.figure_lint.lint_figure(fig, "R4/R7 回归图")

    # ---- R7: twinx 右轴豁免 -------------------------------------------

    def test_twinx_right_spine_exempt(self):
        """twinx 双轴图 (top 已去除, right 保留作右轴刻度) 不再报 R7。"""
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        axr = ax.twinx()
        axr.plot([0, 1], [1, 0])
        for a in (ax, axr):
            a.spines["top"].set_visible(False)
        r7 = [v for v in self._violations(fig) if v.rule.startswith("R7")]
        self.assertEqual([], r7, "twinx 右轴的 right spine 应豁免")
        self.plt.close(fig)

    def test_twinx_top_spine_still_warned(self):
        """twinx 只豁免 right; top spine 未去除仍应报 (只点名 top)。"""
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        axr = ax.twinx()
        axr.plot([0, 1], [1, 0])
        r7 = [v for v in self._violations(fig) if v.rule.startswith("R7")]
        self.assertTrue(r7, "top spine 未去除仍应报 R7")
        self.assertTrue(all("top" in v.detail and "right" not in v.detail for v in r7))
        self.plt.close(fig)

    def test_plain_axes_right_spine_still_warned(self):
        """无 twinx 的普通单轴图 right spine 未去除仍报 R7 (原行为不回退)。"""
        fig, ax = self.plt.subplots()
        ax.plot([0, 1], [0, 1])
        ax.spines["top"].set_visible(False)
        r7 = [v for v in self._violations(fig) if v.rule.startswith("R7")]
        self.assertEqual(1, len(r7))
        self.assertIn("right", r7[0].detail)
        self.plt.close(fig)

    def test_mixed_figure_plain_subplot_right_spine_still_warned(self):
        """混排图: 只有 ax2 是 twinx, 普通子图 ax1 的 right spine 不豁免 (复审 P1-3)。"""
        fig, (ax1, ax2) = self.plt.subplots(1, 2)
        ax1.plot([0, 1], [0, 1])
        ax2.plot([0, 1], [0, 1])
        ax2r = ax2.twinx()
        ax2r.plot([0, 1], [1, 0])
        for a in (ax1, ax2, ax2r):
            a.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)  # 宿主让位, 右 spine 由 twinx 轴承载
        r7 = [v for v in self._violations(fig) if v.rule.startswith("R7")]
        self.assertEqual(1, len(r7), "普通子图 ax1 的 right spine 应仍报 R7")
        self.assertIn("right", r7[0].detail)
        self.plt.close(fig)

    # ---- R4: 矩阵规模触发条件 ------------------------------------------

    def test_large_matrix_heatmap_not_flagged(self):
        """1801×161 大矩阵场图带 colorbar + 少量行内数值标注不触发 R4。"""
        fig, ax = self.plt.subplots()
        data = np.random.rand(1801, 161)
        im = ax.imshow(data, cmap="viridis", aspect="auto")
        for k in range(8):
            ax.text(20 * k, 900, f"{0.1 * k:.2f}", ha="center", va="center")
        fig.colorbar(im)
        r4 = [v for v in self._violations(fig) if v.rule.startswith("R4")]
        self.assertEqual([], r4, "大矩阵场图的行内标签不是逐格标注, 不应报 R4")
        self.plt.close(fig)

    def test_small_heatmap_with_colorbar_still_warns(self):
        """10×10 小热图带 colorbar + 数值标注仍触发 R4 (原降噪不误伤)。"""
        fig, ax = self.plt.subplots()
        data = np.random.rand(10, 10)
        im = ax.imshow(data, cmap="viridis")
        for i, j in ((0, 0), (0, 9), (9, 0), (9, 9), (4, 4)):  # 5 个关键格标注 (<=16)
            ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center")
        fig.colorbar(im)
        r4 = [v for v in self._violations(fig) if v.rule.startswith("R4")]
        self.assertEqual(1, len(r4))
        self.plt.close(fig)

    def test_image_matrix_shape_imshow_and_pcolormesh(self):
        """_image_matrix_shape: imshow 取 get_array(), pcolormesh 取角点网格。"""
        fig, ax = self.plt.subplots()
        im = ax.imshow(np.random.rand(6, 9))
        self.assertEqual((6, 9), self.figure_lint._image_matrix_shape([im]))
        fig2, ax2 = self.plt.subplots()
        mesh = ax2.pcolormesh(np.random.rand(5, 7))
        shape = self.figure_lint._image_matrix_shape([mesh])
        self.assertIn(shape, ((5, 7), (4, 6)))  # 新版 get_array 2-D / 旧版角点回退
        self.plt.close(fig)
        self.plt.close(fig2)


if __name__ == "__main__":
    unittest.main()
