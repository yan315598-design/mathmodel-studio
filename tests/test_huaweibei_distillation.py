"""验证研究生赛深度蒸馏、路由隔离、检索合并和评分边界。"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
COMP_ROOT = SKILL_ROOT / "competitions" / "huaweibei"
SCRIPT_PATH = SKILL_ROOT / "scripts" / "retrieve_cumcm_cases.py"
SCORE_PATH = SKILL_ROOT / "scripts" / "score_artifact.py"


def load_module(path: Path, name: str):
    """从候选 skill 路径加载待测脚本。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class HuaweibeiDistillationTests(unittest.TestCase):
    """覆盖语料数量、人工证据、运行时路由和禁用规则。"""

    @classmethod
    def setUpClass(cls):
        """加载研究生赛案例、论文深读、统计与检索器。"""
        cls.retriever = load_module(SCRIPT_PATH, "retrieve_cases_for_huaweibei")
        cls.scorer = load_module(SCORE_PATH, "score_huaweibei")
        cls.index = json.loads((COMP_ROOT / "cases" / "index.json").read_text(encoding="utf-8"))
        cls.manual = json.loads(
            (COMP_ROOT / "cases" / "manual_review_annotations.json").read_text(encoding="utf-8")
        )
        cls.paper_reviews = json.loads(
            (COMP_ROOT / "papers" / "manual_paper_reviews.json").read_text(encoding="utf-8")
        )["papers"]
        cls.empirical = json.loads((COMP_ROOT / "empirical.json").read_text(encoding="utf-8"))
        cls.cases = cls.retriever.merge_manual_reviews(cls.index["cases"], cls.manual)

    def test_full_case_and_paper_coverage(self):
        """30 题覆盖 190 篇论文且每篇只归入一个案例。"""
        self.assertEqual(len(self.cases), 30)
        self.assertEqual(len({case["id"] for case in self.cases}), 30)
        evidence_ids = {evidence_id for case in self.manual["cases"] for evidence_id in case["evidence_ids"]}
        self.assertEqual(len(evidence_ids), 190)
        self.assertEqual(sum(case["reviewed_paper_count"] for case in self.manual["cases"]), 190)

    def test_star_paper_and_question_coverage(self):
        """12 篇提名论文和 48 个子问逐篇深读完整。"""
        self.assertEqual(len(self.paper_reviews), 12)
        self.assertEqual(sum(len(paper["modeling_body_by_q"]) for paper in self.paper_reviews), 48)
        self.assertTrue(all(paper["review_status"] == "manually_reviewed" for paper in self.paper_reviews))

    def test_all_core_sections_have_page_evidence(self):
        """摘要、背景、问题分析、假设、结尾和每个子问都有页码证据。"""
        required_sections = {"abstract", "background", "problem_analysis", "assumptions", "conclusion"}
        for paper in self.paper_reviews:
            self.assertTrue(required_sections.issubset(paper["section_logic"]))
            for section_name in required_sections:
                refs = paper["section_logic"][section_name]["evidence_refs"]
                self.assertTrue(refs)
                self.assertTrue(all(ref.get("page") for ref in refs))
            for question in paper["modeling_body_by_q"]:
                self.assertTrue(question["evidence_refs"])
                self.assertTrue(all(ref.get("page_start") and ref.get("page_end") for ref in question["evidence_refs"]))
            self.assertTrue(all(item.get("page") for item in paper["figure_table_logic"]))

    def test_award_identity_boundary(self):
        """只有 2021 年目录证据被标为数模之星提名。"""
        self.assertTrue(all(paper["year"] == 2021 for paper in self.paper_reviews))
        self.assertTrue(all(paper["star_status"] == "directory_confirmed_nominee" for paper in self.paper_reviews))
        for case in self.manual["cases"]:
            if case["year"] != 2021:
                self.assertFalse(case["star_evidence_ids"])

    def test_competition_key_and_letter_rules(self):
        """研究生赛与华数杯分键，A-F 不固定映射题型。"""
        topic_specs = json.loads((COMP_ROOT / "topic_specs.json").read_text(encoding="utf-8"))
        huashu_specs = json.loads(
            (SKILL_ROOT / "competitions" / "huashubei" / "topic_specs.json").read_text(encoding="utf-8")
        )
        self.assertEqual(topic_specs["competition"], "huaweibei")
        self.assertEqual(huashu_specs["competition"], "huashubei")
        self.assertNotEqual(topic_specs["competition"], huashu_specs["competition"])
        self.assertFalse(topic_specs["fixed_letter_to_type"])
        self.assertEqual(topic_specs["problem_letters"], list("ABCDEF"))

    def test_manual_overlay_is_merged_for_retrieval(self):
        """检索运行时读取路线、假设、验证、图表和写作人工字段。"""
        required_fields = (
            "question_dependency", "consensus_chain", "paper_route_comparison",
            "assumption_risks", "required_solution_checks", "figure_story", "writing_blueprint",
        )
        self.assertTrue(all(case["manual_status"] == "reviewed" for case in self.cases))
        self.assertTrue(all(all(case.get(field) for field in required_fields) for case in self.cases))
        results = self.retriever.rank_cases("低空湍流监测和安全航路规划", self.cases)[:1]
        self.assertEqual(results[0]["case"]["id"], "huaweibei_2025_D")
        report = self.retriever.render_markdown(results, "huaweibei")
        self.assertIn("研究生数学建模竞赛", report)
        self.assertIn("历史数值、参数、假设和论文原句禁止直接迁移", report)

    def test_corrected_titles_reach_runtime(self):
        """人工纠正的四个题名进入运行时检索结果。"""
        case_map = {case["id"]: case for case in self.cases}
        expected = {
            "huaweibei_2021_D": "抗乳腺癌候选药物的优化建模",
            "huaweibei_2023_B": "DFT类矩阵的整数分解逼近",
            "huaweibei_2023_F": "强对流降水临近预报",
            "huaweibei_2025_D": "低空湍流监测及最优航路规划",
        }
        for case_id, title in expected.items():
            self.assertEqual(case_map[case_id]["title"], title)

    def test_empirical_scoring_exposes_only_reliable_metrics(self):
        """评分层只暴露摘要长度和页数，不暴露图表等自动识别指标。"""
        allowed = set(self.empirical["scoring_policy"]["allowed_reference_metrics"])
        self.assertEqual(allowed, {"abstract_chars", "document_pages", "pdf_pages"})
        self.assertEqual(set(self.empirical["dims"]), allowed)
        self.assertNotIn("figures_detected", self.empirical["dims"])
        self.assertIn("IQR=", self.scorer.inject_evidence("abstract_chars", 1400, self.empirical))
        self.assertIn("禁止作为评分阈值", self.scorer.inject_evidence("figures_detected", 30, self.empirical))

    def test_scoring_dimension_count_follows_competition_overlay(self):
        """国赛/研究生赛保持五维，华数杯 Stage 8 的六维契约可用。"""
        self.assertEqual(len(self.scorer.load_dim_whitelist("huaweibei", 8)), 5)
        huashu_dims = self.scorer.load_dim_whitelist("huashubei", 8)
        self.assertEqual(len(huashu_dims), 6)
        critique = {
            "stage_id": 8,
            "iteration": 0,
            "scores": {dim: {"score": 8, "evidence": "test"} for dim in huashu_dims},
            "min_score": 8,
            "mean_score": 8,
            "issues": [],
            "verdict": "pass",
        }
        self.assertEqual(self.scorer.validate_critique(critique, 8, "huashubei"), (True, "ok"))

    def test_all_json_files_parse(self):
        """候选 skill 的全部 JSON 文件可解析。"""
        failures = []
        for path in SKILL_ROOT.rglob("*.json"):
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                failures.append(f"{path}: {exc}")
        self.assertFalse(failures, failures)

    def test_stage_routes_include_huaweibei(self):
        """Stage 1/3/5/8/9 均能路由研究生赛独立分支。"""
        stage_files = [
            "stage_01_problem_selection.md", "stage_03_model_selection.md",
            "stage_05_subproblem_loop.md", "stage_08_writing.md", "stage_09_review.md",
        ]
        for filename in stage_files:
            content = (SKILL_ROOT / "references" / filename).read_text(encoding="utf-8")
            self.assertIn("huaweibei", content, filename)


if __name__ == "__main__":
    unittest.main()
