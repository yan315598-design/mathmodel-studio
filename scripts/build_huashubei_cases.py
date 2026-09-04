"""从华数杯题型规格与论文统计生成带证据边界的 18 题案例索引。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent

TYPE_PROFILES = {
    "A": {
        "paradigm": "物理工程机理、数值仿真与参数优化",
        "assumption_risks": [
            "边界条件或材料均匀性简化会改变机理结论，必须做边界与材料参数敏感性",
            "只拟合结果而不校验守恒、量纲和物理范围，会得到数值正确但工程失真的解",
        ],
        "required_solution_checks": [
            "量纲、守恒与物理范围检查", "网格或步长收敛", "参数扰动与基线对比", "优化解可实施性",
        ],
        "figure_story": [
            "结构与边界条件示意图", "机理中间场或轨迹图", "参数响应与优化前后对比", "收敛和敏感性图",
        ],
        "writing_blueprint": [
            "按物理对象—控制方程—离散求解—参数辨识—优化—物理验证推进，每个公式后解释量纲与工程含义。",
        ],
    },
    "B": {
        "paradigm": "运筹、组合优化与资源调度",
        "assumption_risks": [
            "遗漏业务约束或把软约束误写为硬约束，会生成不可执行方案",
            "启发式单次最优不代表稳定最优，必须报告多种子、下界或精确小规模基线",
        ],
        "required_solution_checks": [
            "逐约束可行性审计", "小规模精确解或下界对照", "多种子稳定性", "复杂度与运行时间双报告",
        ],
        "figure_story": [
            "决策变量与约束关系图", "方案布局或调度甘特图", "收敛与基线对比", "约束余量和敏感性图",
        ],
        "writing_blueprint": [
            "按业务对象—变量—目标—约束—求解器—可行性—基线—敏感性推进，先证明能执行再解释为何更优。",
        ],
    },
    "C": {
        "paradigm": "数据分析、综合评价、预测分类与规划",
        "assumption_risks": [
            "数据缺失、异常、泄漏或样本选择偏差会把模型性能与现实能力混淆",
            "权重、阈值和评价口径若未经检验，会让排序或策略随主观设置翻转",
        ],
        "required_solution_checks": [
            "数据质量与泄漏检查", "交叉验证或留出验证", "权重与阈值敏感性", "基线模型和误差分层",
        ],
        "figure_story": [
            "数据质量与分布图", "变量关系或特征贡献图", "预测/评价结果与基线对比", "误差、稳定性或路线图",
        ],
        "writing_blueprint": [
            "按数据审计—指标或特征—基线—主模型—解释—验证—决策推进，结果必须同时报告总体与最差分组。",
        ],
    },
}

TASK_CHAINS = {
    "A_heat_transfer_pde": ["多层传热与相变机理", "控制方程和边界条件", "数值离散与参数校准", "防护性能和敏感性"],
    "A_electromagnetic_resonance": ["线圈互感与谐振等效电路", "偏移工况的数值积分", "效率与功率约束", "参数匹配优化"],
    "A_semiconductor_multiobjective": ["器件机理与振荡约束", "性能代理或电路求解", "多目标 Pareto 优化", "工艺容差验证"],
    "A_heat_transfer_geometry": ["纤维结构和等效热物性", "瞬态传热数值模型", "参数反演", "结构优化与物理校验"],
    "A_robot_kinematics_path": ["D-H 坐标与正逆运动学", "可达域和碰撞约束", "关节角与路径优化", "能耗和可实施性验证"],
    "A_multiphysics_mechanism": ["成孔动力学机理链", "多物理过程耦合", "参数辨识与代理模型", "反射性能优化和双路互证"],
    "B_cutting_stock_2d": ["切割模式和利用率定义", "模式枚举或列生成", "整数规划求解", "排样可视化和下界对照"],
    "B_3d_bin_packing_stochastic": ["货舱几何与载重约束", "三维装箱决策", "机会约束处理不确定性", "装载可行性与稳健性"],
    "B_mrp_scheduling_stochastic": ["BOM 与产能展开", "批量和库存决策", "检修与随机需求协同调度", "滚动计划压力测试"],
    "B_colormatching_optimization": ["K-M 光学或配色机理", "配方变量与色差目标", "非线性/多目标求解", "实配误差和敏感性"],
    "B_vlsi_placement_nphard": ["网表与布局约束", "线长和拥塞代理", "启发式/多目标全局布局", "小规模基线和可布线性"],
    "B_5g_resource_scheduling": ["业务等级和时频资源定义", "跨周期调度约束", "混合优化或强化启发式", "时延、吞吐和稳定性"],
    "C_evaluation_progress": ["数据质量和指标构造", "客观/组合赋权", "综合评价与进步分解", "权重稳健性和政策解释"],
    "C_classification_marketing": ["客户数据清洗与特征工程", "购买意愿基线分类", "集成模型和解释", "分层营销策略与验证"],
    "C_regression_multiobjective": ["工艺—结构—性能两级关系", "回归和变量筛选", "多目标性能控制", "残差与外推边界"],
    "C_classification_treatment_opt": ["母婴数据审计", "影响因素和行为分类", "干预变量优化", "分组误差与反事实边界"],
    "C_evaluation_tsp_routing": ["城市指标和吸引力评价", "候选城市筛选", "多目标路线规划", "路线可行性和权重敏感性"],
    "C_spectrum_analysis_stats": ["光谱标准参数计算", "昼夜照明多目标优化", "睡眠实验统计检验", "负面结果与适用边界"],
}


def build_cases(spec: dict, empirical: dict) -> list[dict]:
    """生成 18 题案例，明确原题子问与蒸馏任务链的区别。"""
    paper_files = {}
    for paper in empirical.get("papers", []):
        paper_files.setdefault((paper["year"], paper["topic"]), []).append(paper["file"])

    cases = []
    for problem, topic in spec["topics"].items():
        profile = TYPE_PROFILES[problem]
        for example in topic["historical_examples"]:
            year = example["year"]
            task_type = example["task_type"]
            chain = TASK_CHAINS[task_type]
            files = sorted(paper_files.get((year, problem), []))
            has_papers = bool(files)
            evidence_level = "paper_pattern" if has_papers else "problem_summary_only"
            evidence_ids = ([f"huashubei:paper_pattern:{Path(name).stem}" for name in files]
                            if has_papers else [f"huashubei:problem_summary:{year}-{problem}"])
            cases.append({
                "id": f"huashubei_{year}_{problem}",
                "competition": "huashubei",
                "year": year,
                "problem": problem,
                "title": example["name"],
                "task_type": task_type,
                "paradigm": profile["paradigm"],
                "essence": f"围绕{example['name']}，把领域对象转成可计算机制、约束或指标，并形成可验证的决策闭环。",
                "problem_essence": f"围绕{example['name']}，把领域对象转成可计算机制、约束或指标，并形成可验证的决策闭环。",
                "question_dependency": [f"S{index} 蒸馏任务链：{step}" for index, step in enumerate(chain, 1)],
                "question_granularity": "distilled_stage_not_original_question",
                "recommended_chain": chain,
                "consensus_chain": chain if has_papers else [],
                "paper_route_comparison": [],
                "assumption_risks": profile["assumption_risks"],
                "required_solution_checks": profile["required_solution_checks"],
                "required_validation": profile["required_solution_checks"],
                "figure_story": profile["figure_story"],
                "figure_plan": profile["figure_story"],
                "writing_blueprint": profile["writing_blueprint"],
                "paper_count": len(files),
                "evidence_level": evidence_level,
                "question_evidence_level": evidence_level,
                "evidence_scope": ("topic_summary_plus_2023_2025_paper_patterns"
                                   if has_papers else "topic_and_problem_summary_only"),
                "evidence_ids": evidence_ids,
                "reviewed_paper_count": 0,
                "manual_status": "distilled_pattern" if has_papers else "summary_only",
                "transfer_boundary": (
                    "该记录的 S1-S4 是可复用任务链，不是原题逐问转录。只迁移方法接口、验证和图表角色；"
                    "必须回到当年或新题题面重建子问、参数、约束和结论。"
                ),
            })
    return sorted(cases, key=lambda item: (item["year"], item["problem"]))


def main() -> int:
    """读取候选版知识文件并写出稳定案例索引。"""
    parser = argparse.ArgumentParser(description="生成华数杯 18 题案例索引")
    base = SKILL_ROOT / "competitions" / "huashubei"
    parser.add_argument("--topic-specs", type=Path, default=base / "topic_specs.json")
    parser.add_argument("--empirical", type=Path, default=base / "empirical.json")
    parser.add_argument("--output", type=Path, default=base / "cases" / "index.json")
    args = parser.parse_args()

    spec = json.loads(args.topic_specs.read_text(encoding="utf-8"))
    empirical = json.loads(args.empirical.read_text(encoding="utf-8"))
    payload = {
        "schema_version": "case-index-2.0",
        "competition": "huashubei",
        "source_policy": {
            "2020_2022": "problem_summary_only",
            "2023_2025": "topic_summary_plus_two_paper_patterns_per_problem",
            "question_boundary": "S1-S4 are distilled stages, not original question text",
        },
        "cases": build_cases(spec, empirical),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] cases={len(payload['cases'])} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
