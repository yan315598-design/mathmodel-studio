"""claim_consistency_check.py 的行为测试: 收敛矛盾 fail / 强结论缺证据 warn / 否定表述不误报。"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from claim_consistency_check import check_claims


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ClaimConsistencyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.draft = self.root / "draft"
        self.results = self.root / "results"
        self.draft.mkdir()
        self.results.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_convergence_contradiction_is_fail(self):
        """华数杯回归: 正文写收敛, 结果 converged=false → fail。"""
        _write(self.draft / "sec.md", "收敛性通过保留历史最优解和变化率阈值双重保证，五轮内逼近最优。\n")
        _write(self.results / "q4.json", json.dumps({"scenarios": [{"name": "renew60", "converged": False}]}))
        report = check_claims(self.draft, self.results)
        fails = [f for f in report["findings"] if f["level"] == "fail"]
        self.assertEqual(1, len(fails))
        self.assertEqual("convergence_contradiction", fails[0]["rule"])

    def test_convergence_negation_not_a_claim(self):
        _write(self.draft / "sec.md", "该场景在预算内未收敛，返回历史最好方案。\n")
        _write(self.results / "q4.json", json.dumps({"converged": False}))
        report = check_claims(self.draft, self.results)
        self.assertEqual([], [f for f in report["findings"] if f["rule"].startswith("convergence")])

    def test_convergence_without_criterion_warns(self):
        _write(self.draft / "sec.md", "算法收敛良好，结果稳定。\n")
        _write(self.results / "q1.json", json.dumps({"objective": 123}))
        report = check_claims(self.draft, self.results)
        warns = [f for f in report["findings"] if f["rule"] == "convergence_unsupported"]
        self.assertEqual(1, len(warns))
        self.assertEqual("warn", warns[0]["level"])

    def test_optimal_without_bound_warns(self):
        _write(self.draft / "sec.md", "求得全局最优解。\n")
        _write(self.results / "q1.json", json.dumps({"objective": 123}))
        report = check_claims(self.draft, self.results)
        self.assertEqual(1, len([f for f in report["findings"] if f["rule"] == "optimal_without_bound"]))

    def test_optimal_with_status_ok(self):
        _write(self.draft / "sec.md", "求得全局最优解。\n")
        _write(self.results / "q1.json", json.dumps({"status": "optimal", "objective": 123}))
        report = check_claims(self.draft, self.results)
        self.assertEqual(0, len([f for f in report["findings"] if f["rule"] == "optimal_without_bound"]))

    def test_improvement_without_baseline_warns(self):
        _write(self.draft / "sec.md", "本模型相比传统方法提升 12.3%。\n")
        _write(self.results / "q1.json", json.dumps({"objective": 123}))
        report = check_claims(self.draft, self.results)
        self.assertEqual(1, len([f for f in report["findings"] if f["rule"] == "improvement_without_baseline"]))

    def test_improvement_with_baseline_ok(self):
        _write(self.draft / "sec.md", "本模型相比贪心基线提升 12.3%。\n")
        _write(self.results / "q1.json", json.dumps({"baseline_greedy": 100, "ours": 112.3}))
        report = check_claims(self.draft, self.results)
        self.assertEqual(0, len([f for f in report["findings"] if f["rule"] == "improvement_without_baseline"]))

    def test_interval_inventory_info(self):
        """华数杯回归: 90%/80% 区间口径进入人工核对清单。"""
        _write(self.draft / "sec.md", "给出 90% 预测区间。\n另文称 80% 置信区间覆盖率良好。\n")
        _write(self.results / "q1.json", json.dumps({"objective": 1}))
        report = check_claims(self.draft, self.results)
        infos = [f for f in report["findings"] if f["rule"] == "interval_inventory"]
        self.assertEqual(1, len(infos))
        self.assertIn("90%", infos[0]["detail"])
        self.assertIn("80%", infos[0]["detail"])

    def test_clean_draft_no_fail(self):
        _write(self.draft / "sec.md", "在指定迭代预算内返回历史最好方案；该结果不构成收敛保证。\n")
        _write(self.results / "q4.json", json.dumps({"converged": True, "status": "optimal"}))
        report = check_claims(self.draft, self.results)
        self.assertEqual(0, report["n_fail"])

    def test_untraceable_number_warns(self):
        """正文编造的结果数字必须被拦: 0.9876 不在结果文件里。"""
        _write(self.draft / "sec.md", "测试集宏 F1 达到 0.9896，优于基线。\n另称准确率 0.9876。\n")
        _write(self.results / "q2.json", json.dumps({"f1_macro": 0.9896, "baseline_svm": 0.9665}))
        report = check_claims(self.draft, self.results)
        warns = [f for f in report["findings"] if f["rule"] == "untraceable_number"]
        self.assertEqual(1, len(warns))
        self.assertIn("0.9876", warns[0]["detail"])
        self.assertNotIn("0.9896", warns[0]["detail"])

    def test_number_percent_form_traced(self):
        """百分数口径可互认: 正文 98.96% 对应结果 0.9896。"""
        _write(self.draft / "sec.md", "宏 F1 为 98.96%。\n")
        _write(self.results / "q2.json", json.dumps({"f1_macro": 0.9896}))
        report = check_claims(self.draft, self.results)
        self.assertEqual([], [f for f in report["findings"] if f["rule"] == "untraceable_number"])

    def test_structural_constants_skipped(self):
        _write(self.draft / "sec.md", "统一重采样至 12kHz, 切片 1024 点, 共 161 个文件。\n")
        _write(self.results / "q1.json", json.dumps({"fs": 12}))
        report = check_claims(self.draft, self.results)
        self.assertEqual([], [f for f in report["findings"] if f["rule"] == "untraceable_number"])

    def test_contradicting_values_warns(self):
        """F2 案例回归: 同一对象指标出现两个不同值必须被拦。"""
        _write(self.draft / "abs.md",
               "留园幻境感评分为 174.1，拙政园综合分居首。\n"
               "后文复核：留园幻境感评分为 95.1，寄畅园综合分居首。\n")
        _write(self.results / "r.json", json.dumps({"v": 1}))
        report = check_claims(self.draft, self.results)
        warns = [f for f in report["findings"] if f["rule"] == "contradicting_values"]
        self.assertEqual(1, len(warns))
        self.assertIn("174.1", warns[0]["detail"])
        self.assertIn("95.1", warns[0]["detail"])

    def test_consistent_values_no_false_positive(self):
        _write(self.draft / "abs.md", "测试集宏 F1 为 0.9896。结果节复写：宏 F1 为 0.9896。\n")
        _write(self.results / "r.json", json.dumps({"f1_macro": 0.9896}))
        report = check_claims(self.draft, self.results)
        self.assertEqual([], [f for f in report["findings"] if f["rule"] == "contradicting_values"])


if __name__ == "__main__":
    unittest.main()
