"""验证 v7.3 三赛联合检索、知识包、证据链、评分契约和增量更新。"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def load_module(filename: str, module_name: str):
    """从 scripts 目录加载独立脚本模块。"""
    path = SKILL_ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class V73KnowledgeWorkflowTest(unittest.TestCase):
    """覆盖 v7.3 八项升级的主要契约。"""

    @classmethod
    def setUpClass(cls):
        """一次加载脚本并注册同目录导入。"""
        cls.retrieval = load_module("retrieve_cumcm_cases.py", "retrieve_cumcm_cases")
        import sys
        sys.modules["retrieve_cumcm_cases"] = cls.retrieval
        cls.stage_pack = load_module("build_stage_pack.py", "build_stage_pack")
        sys.modules["build_stage_pack"] = cls.stage_pack
        cls.paper_plan = load_module("generate_paper_plan.py", "generate_paper_plan")
        cls.tracer = load_module("trace_claims.py", "trace_claims")
        cls.updater = load_module("update_knowledge.py", "update_knowledge")
        cls.scorer = load_module("score_artifact.py", "score_artifact_v73")

    def test_huashubei_case_index_has_evidence_boundary(self):
        """华数杯 18 题应区分有论文模式与仅题面摘要。"""
        path = SKILL_ROOT / "competitions" / "huashubei" / "cases" / "index.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(18, len(payload["cases"]))
        levels = [case["evidence_level"] for case in payload["cases"]]
        self.assertEqual(9, levels.count("problem_summary_only"))
        self.assertEqual(9, levels.count("paper_pattern"))
        self.assertTrue(all(case["competition"] == "huashubei" for case in payload["cases"]))
        self.assertTrue(all(case["question_granularity"] == "distilled_stage_not_original_question"
                            for case in payload["cases"]))

    def test_joint_case_and_question_inventory(self):
        """联合检索应覆盖三赛并保留 48 个提名论文子问。"""
        cases = self.retrieval.load_cases("all")
        self.assertEqual(73, len(cases))
        self.assertEqual({"cumcm", "huaweibei", "huashubei"}, {case["competition"] for case in cases})
        star_questions = self.retrieval.load_star_paper_questions("all")
        self.assertEqual(48, len(star_questions))
        self.assertTrue(all(item["evidence_level"] == "star_paper_full_text" for item in star_questions))

    def test_huashubei_retrieval(self):
        """华数杯查询应命中对应历史案例。"""
        cases = self.retrieval.load_cases("huashubei")
        hit = self.retrieval.rank_cases("网络切片无线资源管理 时延 吞吐 跨周期调度", cases)[0]
        self.assertEqual("huashubei_2025_B", hit["case"]["id"])

    def test_stage_pack_contains_required_fields(self):
        """Stage 5 知识包应同时提供路线、验证、图表与证据。"""
        pack = self.stage_pack.build_stage_pack("组合优化 调度 约束可行性", "all", 5, 3)
        self.assertEqual("stage-pack-1.0", pack["schema_version"])
        self.assertEqual(3, len(pack["case_hits"]))
        self.assertEqual(3, len(pack["question_hits"]))
        self.assertTrue(pack["route_options"])
        self.assertTrue(pack["required_validations"])
        self.assertTrue(pack["figure_story"])
        self.assertTrue(all(hit["competition"] in {"cumcm", "huaweibei", "huashubei"}
                            for hit in pack["case_hits"]))
        self.assertEqual({"cumcm", "huaweibei", "huashubei"},
                         {hit["competition"] for hit in pack["case_hits"]})
        self.assertEqual({"cumcm", "huaweibei", "huashubei"},
                         {hit["competition"] for hit in pack["question_hits"]})

    def test_dynamic_plan_and_figure_contract(self):
        """论文骨架应由子问依赖生成，图表需绑定主张和上游数据。"""
        pack = self.stage_pack.build_stage_pack("矩阵压缩 复杂度 精度验证", "huaweibei", 8, 2)
        plan = self.paper_plan.generate_plan(pack)
        question_sections = [section for section in plan["sections"] if section.get("question_id")]
        self.assertGreaterEqual(len(question_sections), 3)
        self.assertEqual(len(question_sections), len(plan["evidence_ledger"]))
        for figure in plan["figure_plan"]:
            self.assertTrue(figure["role"])
            self.assertTrue(figure["supports_claim"])
            self.assertTrue(figure["upstream_data"])
            self.assertTrue(figure["required_checks"])

    def test_claim_trace_blocks_and_passes(self):
        """空证据模板应阻断摘要，完整链应通过。"""
        incomplete = self.tracer.trace_claims({"evidence_ledger": [{"question_id": "Q1", "question": "任务"}]})
        self.assertFalse(incomplete["abstract_ready"])
        complete_row = {
            "question_id": "Q1", "question": "任务", "model": "模型", "result": "结果",
            "validation": "验证", "figure": ["F1"], "abstract_claim": "主张",
        }
        complete = self.tracer.trace_claims({"evidence_ledger": [complete_row]})
        self.assertTrue(complete["abstract_ready"])
        self.assertEqual("pass", complete["abstract_gate"])

    def test_rating_contract_and_huashubei_evidence_policy(self):
        """评分契约应有效，华数杯图表数不得作为硬阈值。"""
        ok, message = self.scorer.validate_rating_contract()
        self.assertTrue(ok, message)
        self.assertEqual(6, len(self.scorer.load_dim_whitelist("huashubei", 8)))
        empirical = self.scorer.load_empirical("huashubei")
        evidence = self.scorer.inject_evidence("fig_count", 20, empirical, competition="huashubei")
        self.assertIn("禁止作为评分阈值", evidence)

    def test_incremental_manifest_skips_unchanged(self):
        """增量清单只把新增和变化文件送入后续处理。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "knowledge.md"
            source.write_text("v1", encoding="utf-8")
            first = self.updater.scan_files([source])
            initial = self.updater.compare({}, first)
            self.assertEqual(1, len(initial["to_process"]))
            previous = {"files": first}
            unchanged = self.updater.compare(previous, self.updater.scan_files([source]))
            self.assertEqual([], unchanged["to_process"])
            source.write_text("v2", encoding="utf-8")
            changed = self.updater.compare(previous, self.updater.scan_files([source]))
            self.assertEqual(1, len(changed["changed"]))


if __name__ == "__main__":
    unittest.main()
