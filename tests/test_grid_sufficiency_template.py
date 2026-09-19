# -*- coding: utf-8 -*-
"""C6 网格充分性检查模板测试 (v3.1.0)。

口径 (references/stage_06_robustness.md "边界层骤变档的量化触发判据与最小检验口径"):
- 触发判据: 边界层敏感量相对基线档跳变 > 10× → 该档必须做粗/细网格专项检验;
- 欠分辨判据: 同一时刻关键量在粗/细两档网格下的相对变化 > 20% → 剔除出排序;
- 模板脚本内的阈值常量必须与规范文档一致 (防文档-代码漂移)。

用例参数一律取**明显合成值** (整十/整百), 不引用任何真实题目的量或网格档。
"""

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "shared" / "code_starter" / "simulation.py"
DOC = ROOT / "references" / "stage_06_robustness.md"

spec = importlib.util.spec_from_file_location("_c6_simulation", TEMPLATE)
simulation = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = simulation
spec.loader.exec_module(simulation)

# ---- 合成参数 (非任何真实题目数据) ----
BASE = 12.0             # 基线档敏感量
NEAR = 13.0             # 合成近邻档: 13/12 ≈ 1.08×, 不触发默认 10× 档
PERT_TRIGGER = 3000.0   # 合成骤变档: 3000/12 = 250×, 触发专项检验
COARSE, FINE = 64, 256  # 合成粗/细两档网格 (4 倍加密)


class TestGridSufficiencyTemplate(unittest.TestCase):
    def test_thresholds_match_doc(self):
        self.assertEqual(simulation.BOUNDARY_JUMP_TRIGGER, 10.0)
        self.assertEqual(simulation.GRID_UNDER_RESOLVED, 0.20)
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn(">10×", doc)
        self.assertIn(">20%", doc)
        self.assertIn("simulation.py", doc)  # 规范指向模板脚本

    def test_boundary_jump_ratio_triggers(self):
        # 合成骤变档: BASE → PERT_TRIGGER 即 250×, 远超默认触发档
        ratio = simulation.boundary_jump_ratio(PERT_TRIGGER, BASE)
        self.assertGreater(ratio, simulation.BOUNDARY_JUMP_TRIGGER)
        self.assertLess(simulation.boundary_jump_ratio(NEAR, BASE),
                        simulation.BOUNDARY_JUMP_TRIGGER)

    def test_under_resolved_branch(self):
        report = simulation.check_grid_sufficiency(
            lambda n: {"v": 10.0 if n == COARSE else 4.0},
            lambda sol: sol["v"], (COARSE, FINE), label="示例边界敏感量")
        self.assertTrue(report["under_resolved"])
        self.assertGreater(report["rel_change"], simulation.GRID_UNDER_RESOLVED)

    def test_converged_branch(self):
        report = simulation.check_grid_sufficiency(
            lambda n: {"v": 10.0 if n == COARSE else 9.85},
            lambda sol: sol["v"], (COARSE, FINE))
        self.assertFalse(report["under_resolved"])

    def test_nan_is_fail_closed(self):
        """审查 high 回归: 非有限值不得被判"网格充分"（NaN 曾被放行进入排序）。"""
        report = simulation.check_grid_sufficiency(
            lambda n: {"v": 1.0 if n == COARSE else float("nan")},
            lambda sol: sol["v"], (COARSE, FINE))
        self.assertFalse(report["finite"])
        self.assertTrue(report["under_resolved"])

    def test_zero_fine_grid_value(self):
        """细网格关键量为 0: 相对误差无定义, 粗档非 0 即判不一致。"""
        report = simulation.check_grid_sufficiency(
            lambda n: {"v": 1e-3 if n == COARSE else 0.0},
            lambda sol: sol["v"], (COARSE, FINE))
        self.assertEqual(report["rel_change"], float("inf"))
        self.assertTrue(report["under_resolved"])
        report = simulation.check_grid_sufficiency(
            lambda n: {"v": 0.0 if n == COARSE else 0.0},
            lambda sol: sol["v"], (COARSE, FINE))
        self.assertEqual(report["rel_change"], 0.0)
        self.assertFalse(report["under_resolved"])

    def test_no_relative_epsilon_scale_effect(self):
        """审查 med 回归: 不再用绝对 epsilon 当分母（小量纲下会掩盖 50% 偏差）。"""
        report = simulation.check_grid_sufficiency(
            lambda n: {"v": 1e-15 if n == COARSE else 2e-15},
            lambda sol: sol["v"], (COARSE, FINE))
        self.assertAlmostEqual(report["rel_change"], 0.5, places=6)
        self.assertTrue(report["under_resolved"])

    # ---- v3.1.1: 非法网格必须拒收 (相同/倒序/非正/非有限/非数值) ----
    def test_reject_identical_grids(self):
        with self.assertRaises(ValueError) as ctx:
            simulation.check_grid_sufficiency(
                lambda n: {"v": 1.0}, lambda sol: sol["v"], (COARSE, COARSE))
        self.assertIn("相同", str(ctx.exception))

    def test_reject_reversed_grids(self):
        with self.assertRaises(ValueError) as ctx:
            simulation.check_grid_sufficiency(
                lambda n: {"v": 1.0}, lambda sol: sol["v"], (FINE, COARSE))
        self.assertIn("倒序", str(ctx.exception))

    def test_reject_nonpositive_nan_and_bad_arity_grids(self):
        for grids in ((0, FINE), (COARSE, 0), (-COARSE, FINE), (float("nan"), FINE),
                      (COARSE, float("inf")), ("a", FINE)):
            with self.assertRaises(ValueError, msg=repr(grids)):
                simulation.check_grid_sufficiency(
                    lambda n: {"v": 1.0}, lambda sol: sol["v"], grids)
        with self.assertRaises(ValueError):
            simulation.check_grid_sufficiency(
                lambda n: {"v": 1.0}, lambda sol: sol["v"], (COARSE, FINE, FINE * 2))

    def test_reject_invalid_tolerance(self):
        for tol in (0, -0.2, float("nan")):
            with self.assertRaises(ValueError, msg=repr(tol)):
                simulation.check_grid_sufficiency(
                    lambda n: {"v": 1.0}, lambda sol: sol["v"], (COARSE, FINE),
                    under_resolved_tol=tol)

    def test_tolerance_configurable(self):
        """相对变化 25%: 默认档 20% 判欠分辨; 容限抬到 50% 则通过 (容限真在起作用)。"""
        solve = lambda n: {"v": 10.0 if n == COARSE else 8.0}
        default = simulation.check_grid_sufficiency(solve, lambda s: s["v"], (COARSE, FINE))
        relaxed = simulation.check_grid_sufficiency(
            solve, lambda s: s["v"], (COARSE, FINE), under_resolved_tol=0.5)
        self.assertTrue(default["under_resolved"])
        self.assertEqual(0.20, default["tolerance"])
        self.assertFalse(relaxed["under_resolved"])
        self.assertEqual(0.5, relaxed["tolerance"])

    def test_scope_note_declares_two_tiers_only(self):
        """只声明两档网格的检查证据, 不构成普遍充分性证明 (v3.1.1)。"""
        report = simulation.check_grid_sufficiency(
            lambda n: {"v": 1.0}, lambda sol: sol["v"], (COARSE, FINE))
        self.assertIn("两档", report["scope_note"])
        self.assertIn("不构成", report["scope_note"])

    # ---- v3.1.1: 触发判据可覆盖; NaN/零值/小量级不静默放过 ----
    def test_grid_check_required_threshold_overridable(self):
        self.assertFalse(simulation.grid_check_required(NEAR, BASE))
        self.assertTrue(simulation.grid_check_required(NEAR, BASE, trigger=1.05))
        self.assertTrue(simulation.grid_check_required(PERT_TRIGGER, BASE))

    def test_grid_check_required_nan_is_fail_closed(self):
        """跳变比非有限 (NaN/基线为 0) 时不能静默跳过: fail-closed 触发专项检验。"""
        self.assertTrue(simulation.grid_check_required(float("nan"), BASE))
        self.assertTrue(simulation.grid_check_required(1.0, 0.0))
        self.assertFalse(simulation.grid_check_required(0.0, 0.0))
        with self.assertRaises(ValueError):
            simulation.grid_check_required(1.0, 1.0, trigger=0)

    def test_small_magnitude_values_are_scale_free(self):
        """小量级按相对变化判定, 不因绝对量级小而放过 (1e-15 → 5e-14 属 50×)。"""
        self.assertTrue(simulation.grid_check_required(5e-14, 1e-15))
        self.assertFalse(simulation.grid_check_required(2e-15, 1e-15))
        report = simulation.check_grid_sufficiency(
            lambda n: {"v": 1e-300 if n == COARSE else 2e-300},
            lambda sol: sol["v"], (COARSE, FINE))
        self.assertAlmostEqual(report["rel_change"], 0.5, places=6)
        self.assertTrue(report["under_resolved"])

    def test_zero_and_inf_values_fail_closed(self):
        report = simulation.check_grid_sufficiency(
            lambda n: {"v": 1e-3 if n == COARSE else 0.0},
            lambda sol: sol["v"], (COARSE, FINE))
        self.assertEqual(float("inf"), report["rel_change"])
        self.assertTrue(report["under_resolved"])
        report = simulation.check_grid_sufficiency(
            lambda n: {"v": float("inf") if n == COARSE else 1.0},
            lambda sol: sol["v"], (COARSE, FINE))
        self.assertFalse(report["finite"])
        self.assertTrue(report["under_resolved"])


if __name__ == "__main__":
    unittest.main()
