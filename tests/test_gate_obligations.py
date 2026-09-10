"""check_gate.py 必停点与答题义务台账 (stages.2.obligations) 的门禁行为测试。"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_gate import check_gate, check_checkpoint


def _base_log():
    return {
        "scores": {"8": [{"iteration": 0, "scores": {"1_abstract_5_paragraph": 8},
                          "min": 8, "mean": 8.0, "verdict": "pass",
                          "ts": "2026-09-08T12:00:00"}]},
        "stages": {"2": {"obligations": []}},
        "checkpoints": {},
    }


def _answered(answer="同意", source="chat", **extra):
    """构造一条真 answered 的 checkpoint 条目 (四项齐全)。"""
    entry = {"status": "answered", "asked_at": "2026-09-08T12:00:00",
             "answer": answer, "source": source}
    entry.update(extra)
    return entry


def _gate5_log():
    """构造除 per_qi_selection 可控外, 其余 gate 5 条件全部满足的 decision_log。"""
    return {
        "scores": {"5": [{"iteration": 0, "scores": {"1_subproblem_completeness": 8},
                          "min": 8, "mean": 8.0, "verdict": "pass",
                          "ts": "2026-09-08T12:00:00"}]},
        "stages": {"5": {"qi_count": 2,
                         "qi_status": {"Q1": "pass", "Q2": "pass"},
                         "sub_problems": {"Q1": {}, "Q2": {}}}},
        "checkpoints": {
            "figure_menu": {"Q1": _answered("两张图", count=2),
                            "Q2": _answered("两张图", count=2)},
            "qi_verdict": {"Q1": _answered("确认 pass"),
                           "Q2": _answered("确认 pass")},
            "per_qi_selection": {"Q1": _answered("主模型: 规划模型"),
                                 "Q2": _answered("baseline: 启发式")},
        },
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


class GatePerQiSelectionTest(unittest.TestCase):
    """第 6 个必停点 checkpoints.per_qi_selection (schema 3.2) 的门禁行为测试。"""

    def test_full_per_qi_selection_passes_gate5(self):
        result = check_gate(_gate5_log(), 5)
        self.assertTrue(result["pass"])

    def test_missing_field_blocks_gate5_with_hint(self):
        """旧 schema 3.0/3.1 state 缺 per_qi_selection 字段: FAIL 且提示补走 per-Qi 选型问答。"""
        log = _gate5_log()
        del log["checkpoints"]["per_qi_selection"]
        result = check_gate(log, 5)
        self.assertFalse(result["pass"])
        self.assertTrue(any("per_qi_selection" in m for m in result["missing"]))
        self.assertTrue(any("补走 per-Qi 选型问答即可" in n for n in result["notes"]))

    def test_incomplete_coverage_blocks_gate5(self):
        log = _gate5_log()
        del log["checkpoints"]["per_qi_selection"]["Q2"]
        result = check_gate(log, 5)
        self.assertFalse(result["pass"])
        self.assertTrue(any("per_qi_selection['Q2']" in m for m in result["missing"]))

    def test_bad_status_blocks_gate5(self):
        log = _gate5_log()
        log["checkpoints"]["per_qi_selection"]["Q1"]["status"] = "asked"
        result = check_gate(log, 5)
        self.assertFalse(result["pass"])
        self.assertTrue(any("per_qi_selection['Q1']" in m for m in result["missing"]))

    def test_untrusted_source_blocks_gate5(self):
        for bad in ("model", "auto"):
            log = _gate5_log()
            log["checkpoints"]["per_qi_selection"]["Q1"]["source"] = bad
            result = check_gate(log, 5)
            self.assertFalse(result["pass"], f"source={bad!r} 应拦截")
            self.assertTrue(any("per_qi_selection['Q1']" in m for m in result["missing"]))

    def test_user_cli_source_passes_gate5(self):
        log = _gate5_log()
        log["checkpoints"]["per_qi_selection"]["Q1"]["source"] = "user_cli"
        result = check_gate(log, 5)
        self.assertTrue(result["pass"])

    def test_checkpoint_dotted_key_queries(self):
        """--checkpoint per_qi_selection.Q1 单点查询: 已登记放行, 未登记拦截。"""
        log = _gate5_log()
        self.assertTrue(check_checkpoint(log, "per_qi_selection.Q1")["pass"])
        del log["checkpoints"]["per_qi_selection"]["Q1"]
        result = check_checkpoint(log, "per_qi_selection.Q1")
        self.assertFalse(result["pass"])
        self.assertTrue(any("per_qi_selection.Q1" in m for m in result["missing"]))

    def test_checkpoint_dotted_key_without_group_fails(self):
        """checkpoints 缺整个 per_qi_selection 组时, 点路径查询按未登记拦截。"""
        log = _gate5_log()
        del log["checkpoints"]["per_qi_selection"]
        result = check_checkpoint(log, "per_qi_selection.Q1")
        self.assertFalse(result["pass"])

    def test_checkpoint_bare_key_whole_check(self):
        """裸组名 per_qi_selection 按整体校验: 三来源对齐后逐问覆盖。"""
        log = _gate5_log()
        self.assertTrue(check_checkpoint(log, "per_qi_selection")["pass"])
        del log["checkpoints"]["per_qi_selection"]["Q2"]
        result = check_checkpoint(log, "per_qi_selection")
        self.assertFalse(result["pass"])
        self.assertTrue(any("per_qi_selection['Q2']" in m for m in result["missing"]))

    def test_checkpoint_bare_key_missing_field_hint(self):
        log = _gate5_log()
        del log["checkpoints"]["per_qi_selection"]
        result = check_checkpoint(log, "per_qi_selection")
        self.assertFalse(result["pass"])
        self.assertTrue(any("补走 per-Qi 选型问答即可" in m for m in result["missing"]))

    def test_checkpoint_illegal_key_still_fails(self):
        """裸 figure_menu / qi_verdict 组名仍不合法 (只有 per_qi_selection 接受裸组名)。"""
        for key in ("figure_menu", "qi_verdict", "per_qi_selection.Q0", "not_a_checkpoint"):
            result = check_checkpoint(_gate5_log(), key)
            self.assertFalse(result["pass"], f"键 {key!r} 应业务 FAIL")

    def test_gate5_old_state_without_checkpoints_lists_per_qi_selection(self):
        """旧 schema 3.0 state (无 checkpoints 字段): missing 清单含 per_qi_selection 及提示。"""
        log = _gate5_log()
        del log["checkpoints"]
        result = check_gate(log, 5)
        self.assertFalse(result["pass"])
        self.assertTrue(any("per_qi_selection" in m and "补走 per-Qi 选型问答即可" in m
                            for m in result["missing"]))


if __name__ == "__main__":
    unittest.main()
