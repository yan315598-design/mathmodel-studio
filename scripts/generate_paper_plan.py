"""依据相似案例与子问依赖生成动态论文骨架、图表计划和证据账本模板。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from build_stage_pack import build_stage_pack


ROLE_CLAIMS = {
    "结构": "说明问题对象、变量和子问之间如何连接",
    "机制": "说明模型中间状态为何产生当前趋势",
    "结果": "精确比较方案、指标或关键输出",
    "可信边界": "证明收敛、稳健性、误差或适用范围",
}


def question_id_from_text(text: str, index: int) -> str:
    """提取 Q/S 编号，缺失时使用 Q 顺序编号。"""
    match = re.match(r"\s*([QS]\d+|Q?\d+)", text, flags=re.IGNORECASE)
    return match.group(1).upper() if match else f"Q{index}"


def detect_role(story: str) -> str:
    """从图表叙事文本识别证据角色。"""
    for role in ROLE_CLAIMS:
        if role in story:
            return role
    if any(word in story for word in ("收敛", "敏感", "误差", "稳健", "余量")):
        return "可信边界"
    if any(word in story for word in ("对比", "结果", "排序", "路线", "甘特")):
        return "结果"
    if any(word in story for word in ("流程", "依赖", "结构", "示意")):
        return "结构"
    return "机制"


def build_question_sections(case: dict, question_hits: list[dict]) -> list[dict]:
    """按子问依赖生成章节，每问保持输入到回答的闭环。"""
    dependencies = case.get("question_dependency", [])
    if not dependencies:
        dependencies = [hit.get("question") for hit in question_hits if hit.get("question")]
    if not dependencies:
        dependencies = ["Q1 按题面定义首个待求解任务"]

    hit_by_id = {}
    for hit in question_hits:
        if hit.get("case_id") == case.get("id") and hit.get("question_id"):
            hit_by_id.setdefault(hit["question_id"], hit)

    sections = []
    previous = None
    for index, dependency in enumerate(dependencies, 1):
        question_id = question_id_from_text(str(dependency), index)
        hit = hit_by_id.get(question_id, {})
        sections.append({
            "id": f"modeling_{question_id.lower()}",
            "question_id": question_id,
            "title": f"{question_id} 模型建立、求解与回答",
            "question_task": dependency,
            "depends_on": previous,
            "input_output": hit.get("input_output") or "按题面写清输入、输出、硬约束和评价指标",
            "model_chain": hit.get("model_chain") or case.get("recommended_chain", []),
            "subsections": [
                "任务与路线选择依据", "变量、约束与模型建立", "算法与中间状态",
                "结果解释与必要验证", "本问回答与传递给后问的中间量",
            ],
            "required_checks": hit.get("required_checks") or case.get("required_checks", []),
            "evidence_ids": hit.get("evidence_ids") or case.get("evidence_ids", []),
            "closing_rule": "用结果—验证—题面回答三句收束，不以算法介绍代替答案。",
        })
        previous = question_id
    return sections


def build_figure_plan(case: dict, question_sections: list[dict]) -> list[dict]:
    """把图表叙事转换成可追踪主张的图表计划。"""
    stories = case.get("figure_story", []) or [
        "结构：全文技术路线与子问依赖", "机制：关键中间状态", "结果：主指标与基线对比", "可信边界：稳健性与误差",
    ]
    checks = case.get("required_checks", [])
    figures = []
    for index, story in enumerate(stories, 1):
        role = detect_role(story)
        question = question_sections[min(index - 1, len(question_sections) - 1)]
        figures.append({
            "id": f"F{index}",
            "question_id": question["question_id"],
            "role": role,
            "title": story,
            "supports_claim": ROLE_CLAIMS[role],
            "upstream_data": question["input_output"],
            "required_checks": checks[:3] or ["数据口径一致", "坐标、单位和图例完整", "正文解释可见趋势"],
            # 色板默认 academic_blue; 生成参数无题型/竞赛偏好, 不在此映射 cool_nature/muted_earth
            "palette": "academic_blue",
            "narrative_position": f"放在 {question['question_id']} 对应推导或结果之后",
            "interpretation_rule": "正文指出比较对象、可见趋势、改变的判断和不能推出的结论。",
        })
    return figures


def build_evidence_ledger(question_sections: list[dict], figure_plan: list[dict]) -> list[dict]:
    """为每个子问生成问题到摘要主张的完整证据链占位。"""
    rows = []
    for section in question_sections:
        figures = [item["id"] for item in figure_plan if item["question_id"] == section["question_id"]]
        rows.append({
            "question_id": section["question_id"],
            "question": section["question_task"],
            "model": None,
            "result": None,
            "validation": None,
            "figure": figures,
            "abstract_claim": None,
            "evidence_ids": section["evidence_ids"],
        })
    return rows


def generate_plan(pack: dict) -> dict:
    """从 Stage 知识包生成动态论文计划。"""
    if not pack.get("case_hits"):
        raise ValueError("Stage 知识包没有 case_hits，无法生成动态骨架")
    case = pack["case_hits"][0]
    question_sections = build_question_sections(case, pack.get("question_hits", []))
    figure_plan = build_figure_plan(case, question_sections)
    return {
        "schema_version": "paper-plan-1.0",
        "competition": pack.get("competition"),
        "query": pack.get("query"),
        "reference_case": {
            "id": case.get("id"),
            "competition": case.get("competition"),
            "title": case.get("title"),
            "evidence_level": case.get("evidence_level"),
            "transfer_boundary": case.get("transfer_boundary"),
        },
        "sections": [
            {"id": "abstract", "title": "摘要", "purpose": "按子问顺序写任务、模型、关键结果、验证和边界，只纳入证据账本已闭环的主张。"},
            {"id": "background", "title": "问题背景与重述", "purpose": "用现实后果—现有缺口—可计算对象—本文交付四步落到题面。"},
            {"id": "problem_analysis", "title": "问题分析", "purpose": "标出每问输入、输出、约束、评价指标和前后依赖，并给全文路线图。"},
            {"id": "assumptions", "title": "模型假设", "purpose": "每条按依据—简化—偏差—验证去向书写，题面定义与模型假设分开。"},
            {"id": "symbols", "title": "符号说明", "purpose": "只保留正文使用的符号，统一单位、上下标和向量矩阵体例。"},
            *question_sections,
            {"id": "robustness", "title": "稳健性、敏感性与误差分析", "purpose": "汇总各问局部验证，并给出模型失效边界。"},
            {"id": "evaluation", "title": "模型评价与推广", "purpose": "优缺点必须由正文证据支持；推广另列成立条件。"},
            {"id": "conclusion", "title": "结论", "purpose": "按题面顺序逐问回答，区分已验证结论、限制和现实解释。"},
        ],
        "figure_plan": figure_plan,
        "evidence_ledger": build_evidence_ledger(question_sections, figure_plan),
        "abstract_gate": "只有 model、result、validation、figure 与 abstract_claim 全部可追踪的行才能进入摘要。",
        "writing_blueprint": pack.get("writing_blueprint", []),
        "warnings": pack.get("warnings", []),
    }


def render_markdown(plan: dict) -> str:
    """把论文计划渲染为可直接执行的 Markdown。"""
    lines = [
        "# 动态论文骨架",
        "",
        f"- 参考案例：[{plan['reference_case']['competition']}] {plan['reference_case']['title']}",
        f"- 摘要门禁：{plan['abstract_gate']}",
        "",
        "## 章节",
        "",
    ]
    for section in plan["sections"]:
        lines.append(f"- **{section['title']}**：{section.get('purpose', section.get('question_task', ''))}")
    lines.extend(["", "## 图表证据计划", ""])
    for figure in plan["figure_plan"]:
        lines.append(f"- `{figure['id']}` [{figure['role']}] {figure['title']}；支撑：{figure['supports_claim']}；上游：{figure['upstream_data']}")
    lines.extend(["", "## 证据账本", ""])
    for row in plan["evidence_ledger"]:
        lines.append(f"- `{row['question_id']}`：问题 → 模型 → 结果 → 验证 → {','.join(row['figure']) or '待规划图'} → 摘要主张")
    return "\n".join(lines) + "\n"


def main() -> int:
    """解析知识包或查询，并输出论文计划。"""
    parser = argparse.ArgumentParser(description="生成动态论文骨架与图表证据计划")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--stage-pack", type=Path)
    source.add_argument("--query")
    parser.add_argument("--competition", choices=("all", "cumcm", "huaweibei", "huashubei"), default="all")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    pack = (json.loads(args.stage_pack.read_text(encoding="utf-8"))
            if args.stage_pack else build_stage_pack(args.query, args.competition, 8, max(1, args.top_k)))
    try:
        plan = generate_plan(pack)
    except ValueError as exc:
        parser.error(str(exc))
    content = (json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
               if args.format == "json" else render_markdown(plan))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"[OK] output={args.output}")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
