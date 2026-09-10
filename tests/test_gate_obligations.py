"""check_gate.py 答题义务台账镜像 (stages.2.obligations) 的门禁行为测试。"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_gate import check_gate


def _base_log():
    return {
        "scores": {"8": [{"iteration": 0, "scores": {"1_abstract_5_paragraph": 8},
                          "min": 8, "mean": 8.0, "verdict": "pass",
                          "ts": "2026-09-08T12:00:00"}]},
        "stages": {"2": {"obligations": []}},
        "checkpoints": {},
    }


class GateObligationsTest(unittest.TestCase):
    def _log_with(self, obligations):
        log = _base_log()
        log["stages"]["2"]["obligations"] = obligations
        return log

    def test_absent_obligations_notes_only(self):
        log = _base_log()
        del log["stages"]["2"]["obligations"]
        result = check_gate(log, 8)
        self.assertTrue(result["pass"])
        self.assertTrue(any("obligations" in n for n in result["notes"]))

    def test_unstarted_blocks_gate_8(self):
        log = self._log_with([
            {"id": "OB1", "statement": "Q1 路径", "min_output": "路线图", "status": "unstarted"},
            {"id": "OB2", "statement": "Q2 评分", "min_output": "评分表", "status": "verified"},
        ])
        result = check_gate(log, 8)
        self.assertFalse(result["pass"])
        self.assertTrue(any("OB1" in m for m in result["missing"]))

    def test_partial_passes_with_note(self):
        log = self._log_with([
            {"id": "OB1", "statement": "Q1 路径", "min_output": "路线图", "status": "partial"},
        ])
        result = check_gate(log, 8)
        self.assertTrue(result["pass"])
        self.assertTrue(any("OB1" in n for n in result["notes"]))

    def test_all_verified_passes(self):
        log = self._log_with([
            {"id": "OB1", "statement": "Q1 路径", "min_output": "路线图", "status": "verified"},
        ])
        result = check_gate(log, 8)
        self.assertTrue(result["pass"])

    def test_empty_list_fails(self):
        result = check_gate(self._log_with([]), 8)
        self.assertFalse(result["pass"])

    def test_bad_status_fails(self):
        log = self._log_with([
            {"id": "OB1", "statement": "Q1", "min_output": "x", "status": "done"},
        ])
        result = check_gate(log, 8)
        self.assertFalse(result["pass"])
        self.assertTrue(any("status 非法" in m for m in result["missing"]))

    def test_missing_min_output_fails(self):
        log = self._log_with([{"id": "OB1", "statement": "Q1", "status": "verified"}])
        result = check_gate(log, 8)
        self.assertFalse(result["pass"])

    def test_gate_3_ignores_obligations(self):
        """义务检查只挂 gate 5/8, 不影响其他 gate。"""
        log = self._log_with([
            {"id": "OB1", "statement": "Q1", "min_output": "x", "status": "unstarted"},
        ])
        # gate 3 需要 scores["3"] + card_decision; 这里只验证义务不报错传播
        result = check_gate(log, 3)
        self.assertFalse(any("义务" in m for m in result["missing"]))


if __name__ == "__main__":
    unittest.main()
