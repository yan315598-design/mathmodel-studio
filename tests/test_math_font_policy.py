"""math_font_policy.py 的行为测试: 政策来源优先级 (cli > 顶层标量键 > 自由文本)、
别名键、冲突/非法值警告不判定、**不做任意深度 DFS** (events/历史 stage 里的旧值
不被当现行政策)、override 非法值报错、decision_log 定位与容错读取。"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from math_font_policy import (POLICY_CONVENTIONAL, POLICY_UNSPECIFIED,
                              POLICY_UPRIGHT, decision_log_path,
                              locate_decision_log, normalize_policy_token,
                              read_decision_log, read_decision_log_file,
                              resolve_math_font_policy, scan_free_text,
                              searched_paths_note)


class NormalizeTokenTest(unittest.TestCase):
    def test_upright_forms(self):
        for raw in ("upright", "UPRIGHT", "regular", "roman", "正体", "全局正体",
                    "直立体", " global_upright "):
            if raw.strip() == "global_upright":
                continue
            self.assertEqual(POLICY_UPRIGHT, normalize_policy_token(raw), raw)
        self.assertEqual(POLICY_UPRIGHT, normalize_policy_token(True))

    def test_conventional_forms(self):
        for raw in ("italic", "conventional", "GB3102", "gb/t 3102", "常规",
                    "常规正斜", "斜体", "默认", "default"):
            self.assertEqual(POLICY_CONVENTIONAL, normalize_policy_token(raw), raw)
        self.assertEqual(POLICY_CONVENTIONAL, normalize_policy_token(False))

    def test_illegal_values_not_guessed(self):
        for raw in ("黑体", "mixed", "混合", "", None, 3, 1.0, ["upright"], {"a": 1}):
            self.assertIsNone(normalize_policy_token(raw), repr(raw))


class ScanFreeTextTest(unittest.TestCase):
    def test_single_side(self):
        self.assertEqual(POLICY_UPRIGHT, scan_free_text("公式全局正体, 与图内一致"))
        self.assertEqual(POLICY_CONVENTIONAL, scan_free_text("按 GB 3102 惯例, 变量斜体"))

    def test_both_sides_or_negation_not_decided(self):
        self.assertIsNone(scan_free_text("正体与斜体混排, 未定"))
        self.assertIsNone(scan_free_text("不用正体, 保持斜体"))
        self.assertIsNone(scan_free_text("没有采用常规正斜"))
        self.assertIsNone(scan_free_text("与字体无关的备注"))


class ResolveTest(unittest.TestCase):
    def _resolve(self, log, override=None):
        return resolve_math_font_policy(log, override)

    def test_unspecified_warns_with_searched_paths(self):
        policy, source, warns = self._resolve({})
        self.assertEqual(POLICY_UNSPECIFIED, policy)
        self.assertEqual("", source)
        self.assertTrue(any("未登记" in w for w in warns))
        self.assertIn("math_font", searched_paths_note())

    def test_scalar_keys_and_alias(self):
        for key in ("math_font", "math_font_policy", "upright_math"):
            policy, source, _ = self._resolve({key: "upright"})
            self.assertEqual(POLICY_UPRIGHT, policy, key)
            self.assertIn(key, source)
        policy, source, _ = self._resolve({"upright_math": False})
        self.assertEqual(POLICY_CONVENTIONAL, policy)

    def test_free_text_notes_last_resort(self):
        policy, source, _ = self._resolve(
            {"stages": {"0": {"notes": "全文公式取全局正体"}}})
        self.assertEqual(POLICY_UPRIGHT, policy)
        self.assertIn("自由文本", source)

    def test_scalar_wins_over_free_text(self):
        log = {"math_font": "conventional",
               "stages": {"0": {"notes": "全局正体"}}}
        policy, source, _ = self._resolve(log)
        self.assertEqual(POLICY_CONVENTIONAL, policy)
        self.assertNotIn("自由文本", source)

    def test_conflicting_keys_warn_and_keep_input(self):
        policy, source, warns = self._resolve(
            {"math_font": "upright", "math_font_policy": "conventional"})
        self.assertEqual(POLICY_UNSPECIFIED, policy)
        self.assertIn("conflict", source)
        self.assertTrue(any("不同政策" in w for w in warns))

    def test_illegal_value_warns_and_falls_through(self):
        policy, _, warns = self._resolve({"math_font": "黑体"})
        self.assertEqual(POLICY_UNSPECIFIED, policy)
        self.assertTrue(any("无法归一" in w for w in warns))
        # 非法值不阻断自由文本层的判定
        policy, source, _ = self._resolve(
            {"math_font": 3, "stages": {"0": {"notes": "采用全局正体"}}})
        self.assertEqual(POLICY_UPRIGHT, policy)

    def test_no_deep_search_ignores_historical_and_event_values(self):
        """不做 DFS: events.log 与 stage 历史字段里的旧方案不得当选。"""
        log = {
            "events": {"log": [{"type": "backtrack", "math_font": "upright"}]},
            "stages": {"3": {"rejection_log": [{"math_font_policy": "conventional"}]}},
            "scores": {"8": [{"upright_math": True}]},
        }
        policy, source, warns = self._resolve(log)
        self.assertEqual(POLICY_UNSPECIFIED, policy)
        self.assertEqual("", source)
        self.assertTrue(any("未登记" in w for w in warns))

    def test_override_wins(self):
        policy, source, warns = self._resolve({"math_font": "conventional"},
                                             override="upright")
        self.assertEqual(POLICY_UPRIGHT, policy)
        self.assertIn("cli", source)
        self.assertEqual([], warns)

    def test_override_auto_reads_log(self):
        policy, _, _ = self._resolve({"math_font": "upright"}, override="auto")
        self.assertEqual(POLICY_UPRIGHT, policy)

    def test_override_illegal_raises(self):
        with self.assertRaises(ValueError):
            self._resolve({}, override="bold")

    def test_non_dict_log_is_unspecified(self):
        for log in (None, [], "upright", 3):
            policy, _, _ = resolve_math_font_policy(log)
            self.assertEqual(POLICY_UNSPECIFIED, policy, repr(log))


class DecisionLogIOTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_path_convention(self):
        ws = self.root / "paper_workspace"
        self.assertEqual(self.root / "state" / "decision_log.json",
                         decision_log_path(ws))

    def test_read_returns_dict_or_empty(self):
        ws = self.root / "paper_workspace"
        ws.mkdir(parents=True, exist_ok=True)
        state = self.root / "state"
        state.mkdir(parents=True, exist_ok=True)
        (state / "decision_log.json").write_text(
            json.dumps({"math_font": "upright"}), encoding="utf-8")
        self.assertEqual({"math_font": "upright"}, read_decision_log(ws))
        # 损坏 / 非对象 → 空 dict (静默回退, 由政策层给警告)
        (state / "decision_log.json").write_text("{bad json", encoding="utf-8")
        self.assertEqual({}, read_decision_log(ws))
        (state / "decision_log.json").write_text("[1,2]", encoding="utf-8")
        self.assertEqual({}, read_decision_log(ws))
        self.assertEqual({}, read_decision_log(self.root / "nope_ws"))
        self.assertEqual({}, read_decision_log_file(self.root / "nope.json"))

    def test_locate_from_docx_parents(self):
        proj = self.root / "proj"
        sub = proj / "submission"
        sub.mkdir(parents=True, exist_ok=True)
        (proj / "state").mkdir(parents=True, exist_ok=True)
        log = proj / "state" / "decision_log.json"
        log.write_text("{}", encoding="utf-8")
        found, where = locate_decision_log(sub / "x_final.docx")
        self.assertEqual(log, found)
        self.assertIn("自动定位", where)
        # 找不到 → None + 原因 (不加判定)
        lonely = self.root / "lonely"
        lonely.mkdir()
        found, where = locate_decision_log(lonely / "x.docx", max_up=1)
        self.assertIsNone(found)
        self.assertIn("未找到", where)


if __name__ == "__main__":
    unittest.main()
