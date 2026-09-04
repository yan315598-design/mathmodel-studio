"""验证 CUMCM 人工复核覆盖层、检索质量和阶段接入契约。"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "retrieve_cumcm_cases.py"
INDEX_PATH = SKILL_ROOT / "competitions" / "cumcm" / "cases" / "index.json"
MANUAL_PATH = SKILL_ROOT / "competitions" / "cumcm" / "cases" / "manual_review_annotations.json"


def load_retriever():
    """从候选 skill 路径加载检索模块。"""
    spec = importlib.util.spec_from_file_location("retrieve_cumcm_cases", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ManualRetrievalTests(unittest.TestCase):
    """覆盖结构合并、检索路由和防误用规则。"""

    @classmethod
    def setUpClass(cls):
        """加载基础索引、人工复核和合并后的 25 题。"""
        cls.module = load_retriever()
        cls.index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        cls.manual = json.loads(MANUAL_PATH.read_text(encoding="utf-8"))
        cls.cases = cls.module.merge_manual_reviews(cls.index["cases"], cls.manual)
        cls.case_map = {case["id"]: case for case in cls.cases}

    def test_manual_coverage(self):
        """25 题、64 篇人工证据和 reviewed 状态完整。"""
        self.assertEqual(len(self.cases), 25)
        self.assertEqual(len({case["id"] for case in self.cases}), 25)
        self.assertTrue(all(case["manual_status"] == "reviewed" for case in self.cases))
        ids = {value for case in self.cases for value in case["reviewed_evidence_ids"]}
        self.assertEqual(len(ids), 64)

    def test_base_provenance_is_preserved(self):
        """人工证据不覆盖原可核验库的论文计数和等级。"""
        base = {case["id"]: case for case in self.index["cases"]}
        for case_id, case in self.case_map.items():
            self.assertEqual(case["paper_count"], base[case_id]["paper_count"])
            self.assertEqual(case["evidence_level"], base[case_id]["evidence_level"])

    def test_corrected_runtime_overrides(self):
        """两处错误范式、本质和运行时推荐链均由人工结论纠正。"""
        communication = self.case_map["cumcm_2022_D"]
        inventory = self.case_map["cumcm_2022_E"]
        self.assertEqual(communication["paradigm"], "通信时隙调度与概率可靠性")
        self.assertIn("报文共享调度", communication["essence"])
        self.assertNotIn("压缩编码", communication["recommended_chain"])
        self.assertEqual(inventory["paradigm"], "需求预测与库存生产决策")
        self.assertIn("库存资金", inventory["essence"])
        self.assertIn("滚动时间序列预测", inventory["recommended_chain"])
        self.assertIn("混合整数规划", inventory["source_recommended_chain"])

    def test_required_stage_fields(self):
        """每题都具备 Stage 3、5、8 所需人工字段。"""
        fields = (
            "question_dependency", "consensus_chain", "paper_route_comparison",
            "result_disagreements", "assumption_risks", "required_solution_checks",
            "figure_story", "writing_blueprint", "reviewed_evidence_ids",
        )
        self.assertTrue(all(all(case.get(field) for field in fields) for case in self.cases))

    def test_markdown_forbids_historical_value_reuse(self):
        """检索报告明确禁止历史数值迁移并输出 evidence ID。"""
        result = self.module.rank_cases("库存服务水平和两周生产提前期", self.cases)[:1]
        report = self.module.render_markdown(result)
        self.assertIn("历史数值、参数、假设和论文原句禁止直接迁移", report)
        self.assertIn("历史结果分歧（仅用于校准）", report)
        self.assertIn("人工证据 ID", report)

    def test_unknown_style_queries(self):
        """25 个陌生题式查询均把对应案例排在第一名。"""
        queries = {
            "cumcm_2021_A": "大型可变形反射曲面通过执行器调整节点，使入射电磁波聚焦，并评价接收效率",
            "cumcm_2021_B": "少量化学试验研究温度催化剂配比对产率影响，优化工艺并追加五次实验",
            "cumcm_2021_C": "从供应商历史供货中筛选合作方，联合制定订购、库存和运输损耗方案",
            "cumcm_2021_D": "连续生产材料出现废段，需要按目标长度在线切割并随异常时刻滚动调整",
            "cumcm_2021_E": "利用近红外和中红外高维光谱识别样品类别与产地并判断未知样本",
            "cumcm_2022_A": "浮子振子受波浪激励产生垂荡纵摇，优化直线和旋转阻尼以提高平均功率",
            "cumcm_2022_B": "无人集群只能接收方位角，利用少量信号源定位并迭代校正圆形队形",
            "cumcm_2022_C": "闭合化学成分数据分析风化差异，对文物聚类并鉴别未知类别",
            "cumcm_2022_D": "多个站点在有限时隙内共享短报文，发送存在成功概率，需要最短轮次和冗余调度",
            "cumcm_2022_E": "预测小批量产品周需求，设置安全库存，在服务水平约束下平衡库存资金和生产提前期",
            "cumcm_2023_A": "太阳能塔式镜场计算余弦遮挡截断效率并优化定日镜布局和尺寸",
            "cumcm_2023_B": "多波束声呐在倾斜海底规划测线，控制重叠率、漏测面积和总航程",
            "cumcm_2023_C": "生鲜商品存在损耗和价格弹性，需要预测销量并联合制定补货定价策略",
            "cumcm_2023_D": "繁殖动物分阶段占用有限栏位，优化批次间隔并考虑怀孕随机性",
            "cumcm_2023_E": "河流流量含沙量有缺失和突变，需要分析季节周期并预测水沙变化",
            "cumcm_2024_A": "长链刚性板沿螺线移动，递推位置速度、检测碰撞并设计调头路径",
            "cumcm_2024_B": "零部件有次品率，通过抽样检验后决定检测装配拆解以最大化期望利润",
            "cumcm_2024_C": "多地块多作物多年轮作，在销量价格产量不确定下制定种植计划",
            "cumcm_2024_D": "三维随机误差下计算投放武器命中潜艇概率并优化引爆深度",
            "cumcm_2024_E": "根据路网流量速度识别拥堵，优化信号管控并估算停车资源需求",
            "cumcm_2025_A": "无人平台投放烟幕形成球形云团，需要完全遮蔽目标并优化多弹时间窗",
            "cumcm_2025_B": "从不同入射角的干涉光谱反演薄膜厚度，比较双光束和多光束模型",
            "cumcm_2025_C": "重复检测数据研究孕周和体重指数，优化检测时点并判定染色体异常",
            "cumcm_2025_D": "矿井网络突水后模拟水位传播，根据时变可通行边规划逃生和动态改道",
            "cumcm_2025_E": "视频人体关键点识别起跳落地，提取姿态特征预测成绩并给个体反馈",
        }
        failures = {}
        for expected, query in queries.items():
            top_ids = [item["case"]["id"] for item in self.module.rank_cases(query, self.cases)[:3]]
            if expected != top_ids[0]:
                failures[expected] = top_ids
        self.assertFalse(failures, failures)

    def test_without_manual_layer_is_backward_compatible(self):
        """人工复核文件缺失时仍返回原基础案例结构。"""
        merged = self.module.merge_manual_reviews(self.index["cases"], None)
        self.assertEqual(merged, self.index["cases"])
        self.assertNotIn("manual_status", merged[0])

    def test_single_paper_cases_are_not_called_consensus(self):
        """单篇题的分歧字段明确说明证据限制。"""
        single_cases = [case for case in self.cases if case["reviewed_paper_count"] == 1]
        self.assertTrue(single_cases)
        self.assertTrue(all("仅一篇" in "".join(case["result_disagreements"]) for case in single_cases))

    def test_stage_documents_reference_manual_fields(self):
        """Stage 3、5、8 已分别接入路线、验证和写作字段。"""
        stage_3 = (SKILL_ROOT / "references" / "stage_03_model_selection.md").read_text(encoding="utf-8")
        stage_5 = (SKILL_ROOT / "references" / "stage_05_subproblem_loop.md").read_text(encoding="utf-8")
        stage_8 = (SKILL_ROOT / "references" / "stage_08_writing.md").read_text(encoding="utf-8")
        self.assertIn("paper_route_comparison", stage_3)
        self.assertIn("required_solution_checks", stage_5)
        self.assertIn("writing_blueprint", stage_8)


if __name__ == "__main__":
    unittest.main()
