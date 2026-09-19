# -*- coding: utf-8 -*-
"""3.0.0 新增 8 个数据图模板的 smoke 测试（WP-B B1/B2 规格）。

每个模板一条用例: --demo 渲染成功（退出码 0）+ PNG 非空 +
figqa --strict 碰撞门通过。缺第三方依赖的模板按既有约定以退出码 3
提前退出, 测试转 skip（本批 8 件均为 numpy/matplotlib 内依赖, 正常必跑）。
before-after 另补 dist 模式渲染用例（figqa 只跑脚本默认参数, dist 模式
覆盖不到碰撞门, 至少守住渲染链）。
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "templates" / "figures" / "scripts" / "templates"
FIGQA_SCRIPT = REPO_ROOT / "scripts" / "figqa.py"


def _render_and_check(script: Path, extra_args: list[str]) -> None:
    """--demo 渲染 + PNG 非空 + figqa --strict; 退出码 3 转 skip。"""
    with tempfile.TemporaryDirectory() as td:
        stem = Path(td) / script.stem
        result = subprocess.run(
            [sys.executable, str(script), "--demo", *extra_args,
             "--out", str(stem)],
            capture_output=True, text=True, check=False)
        if result.returncode == 3:
            raise unittest.SkipTest(f"{script.name} 缺第三方依赖, 按约定跳过")
        assert result.returncode == 0, (
            f"{script.name} 渲染失败 rc={result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}")
        png = stem.with_suffix(".png")
        assert png.is_file() and png.stat().st_size > 0, f"PNG 缺失或为空: {png}"
    figqa = subprocess.run(
        [sys.executable, str(FIGQA_SCRIPT), str(script), "--strict"],
        capture_output=True, text=True, check=False)
    assert figqa.returncode == 0, (
        f"{script.name} 未过 figqa --strict\n{figqa.stdout}\n{figqa.stderr}")


class NewFigureTemplateSmokeTests(unittest.TestCase):
    """8 个新模板的 --demo 渲染与 figqa 硬门 smoke。"""

    def test_field_contour(self):
        _render_and_check(TEMPLATES_DIR / "make_field_contour.py", [])

    def test_profile_family(self):
        _render_and_check(TEMPLATES_DIR / "make_profile_family.py", [])

    def test_threshold_inversion(self):
        _render_and_check(TEMPLATES_DIR / "make_threshold_inversion.py", [])

    def test_convergence_sequence(self):
        _render_and_check(TEMPLATES_DIR / "make_convergence_sequence.py", [])

    def test_contrast_pair(self):
        _render_and_check(TEMPLATES_DIR / "make_contrast_pair.py", [])

    def test_route_on_field(self):
        _render_and_check(TEMPLATES_DIR / "make_route_on_field.py", [])

    def test_answer_grid(self):
        _render_and_check(TEMPLATES_DIR / "make_answer_grid.py", [])

    def test_before_after(self):
        _render_and_check(TEMPLATES_DIR / "make_before_after.py", [])

    def test_before_after_dist_mode_renders(self):
        """dist 模式渲染链冒烟（figqa 默认参数跑不到该分支）。"""
        with tempfile.TemporaryDirectory() as td:
            stem = Path(td) / "before_after_dist"
            result = subprocess.run(
                [sys.executable, str(TEMPLATES_DIR / "make_before_after.py"),
                 "--demo", "--mode", "dist", "--out", str(stem)],
                capture_output=True, text=True, check=False)
            assert result.returncode == 0, (
                f"dist 模式渲染失败 rc={result.returncode}\n{result.stderr}")
            png = stem.with_suffix(".png")
            assert png.is_file() and png.stat().st_size > 0, f"PNG 缺失: {png}"


class FirstCrossingBoundaryTests(unittest.TestCase):
    """_first_crossing 边界回归（复审 P2-3/P2-5）。"""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "make_threshold_inversion_for_tests",
            TEMPLATES_DIR / "make_threshold_inversion.py")
        cls.mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.mod
        spec.loader.exec_module(cls.mod)

    def _cross(self, metric, threshold=0.5, param=None):
        import numpy as np
        p = np.asarray(param if param is not None else
                      np.linspace(0.0, 1.0, len(metric)))
        m = np.asarray(metric, dtype=float)
        return self.mod._first_crossing(p, m, threshold)

    def test_endpoint_exact_threshold_is_crossing(self):
        """末档点恰压阈值 → 末档即穿越点（修复前抛"未穿越"）。"""
        idx, x_star = self._cross([0.1, 0.3, 0.5], 0.5)
        self.assertEqual(idx, 1)
        self.assertAlmostEqual(x_star, 1.0)

    def test_middle_point_exact_threshold(self):
        """中间档恰压阈值 → 该档即穿越点。"""
        idx, x_star = self._cross([0.1, 0.5, 0.9], 0.5)
        self.assertEqual(idx, 1)
        self.assertAlmostEqual(x_star, 0.5)

    def test_descending_crossing(self):
        """下降穿越同样定位（线性插值到精确穿越参数）。"""
        idx, x_star = self._cross([0.9, 0.4, 0.1], 0.5)
        self.assertEqual(idx, 0)
        # frac = (0.5-0.9)/(0.4-0.9) = 0.8 → x = 0 + 0.8*(0.5-0) = 0.4
        self.assertAlmostEqual(x_star, 0.4)

    def test_no_crossing_raises(self):
        """序列不穿越 → ValueError 且消息含序列范围。"""
        with self.assertRaises(ValueError) as ctx:
            self._cross([0.1, 0.2, 0.3], 0.5)
        self.assertIn("未穿越", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
