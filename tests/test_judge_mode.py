"""--mode judge 评委模拟器: 资格门 / 90% 封顶 / 格式乘数 / 离群席冲突。"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCORE_PATH = SKILL_ROOT / "scripts" / "score_artifact.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_module(path: Path, name: str):
    """从候选 skill 路径加载待测脚本。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class JudgeModeTests(unittest.TestCase):
    """覆盖 judge 输入校验、资格门、扣分封顶、格式乘数与离群席。"""

    @classmethod
    def setUpClass(cls):
        cls.scorer = load_module(SCORE_PATH, "score_judge_mode")

    def _fixture(self, name: str) -> dict:
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def test_qualification_fail_not_eligible(self):
        """资格门任一 pass=false → not_eligible, 不再计分。"""
        data = self._fixture("judge_qualification_fail.json")
        ok, msg = self.scorer.validate_judge_input(data)
        self.assertTrue(ok, msg)
        result = self.scorer.compute_judge_score(data)
        self.assertEqual(result["verdict"], "not_eligible")
        self.assertIn("不具备获奖资格", result["message"])
        self.assertIn("页数不超当年上限", result["failed_qualifications"])
        self.assertNotIn("raw", result)

    def test_cap_90_and_reserve(self):
        """block_score 封顶在 cap×weight, 保留 (1-cap)×weight, huaweibei 给出锚点档位。"""
        data = self._fixture("judge_cap_90.json")
        result = self.scorer.compute_judge_score(data)
        self.assertEqual(result["verdict"], "eligible")
        # 建模 60 无扣分 -> 54; 写作 40 扣 8 -> 0.9*40-8 = 28
        by_name = {b["name"]: b for b in result["blocks"]}
        self.assertAlmostEqual(by_name["建模与求解"]["score"], 54.0, places=6)
        self.assertAlmostEqual(by_name["写作与呈现"]["score"], 28.0, places=6)
        self.assertAlmostEqual(result["raw"], 82.0, places=6)
        self.assertAlmostEqual(result["reserve_total"], 10.0, places=6)
        self.assertEqual(result["tier"], "国一区间候选")

    def test_format_multiplier(self):
        """format_score=0 → 乘数 0.5; 非 huaweibei 竞赛不作跨赛分布推断。"""
        data = self._fixture("judge_format_multiplier.json")
        result = self.scorer.compute_judge_score(data)
        self.assertAlmostEqual(result["format_multiplier"], 0.5, places=6)
        self.assertAlmostEqual(result["final"], result["raw"] * 0.5, places=2)
        self.assertIsNone(result["tier"])
        self.assertEqual(result["calibration_note"], "不作跨赛分布推断")

    def test_panel_conflict_detection(self):
        """共享维度分差>20 判离群并给重派建议; 分差<=20 不误报。"""
        data = self._fixture("judge_panel_conflict.json")
        result = self.scorer.compute_judge_score(data)
        self.assertTrue(result["panel_conflict"])
        dims = {c["dim"] for c in result["panel_conflicts"]}
        self.assertEqual(dims, {"modeling"})  # writing (80 vs 72) 不应报
        self.assertIsNotNone(result["reassign_advice"])
        self.assertIn("禁止平均", result["reassign_advice"])

    def test_validate_rejects_bad_input(self):
        """schema 错误 (非法竞赛 / weight 缺失 / format_score 非数值) 被拒。"""
        base = self._fixture("judge_format_multiplier.json")
        bad_comp = dict(base, competition="nope")
        ok, _ = self.scorer.validate_judge_input(bad_comp)
        self.assertFalse(ok)
        bad_weight = dict(base, blocks=[{"name": "x", "deductions": []}])
        ok, _ = self.scorer.validate_judge_input(bad_weight)
        self.assertFalse(ok)
        bad_fmt = dict(base, format_score="high")
        ok, _ = self.scorer.validate_judge_input(bad_fmt)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
