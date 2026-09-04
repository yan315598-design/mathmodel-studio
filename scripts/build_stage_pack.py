"""按当前 Stage 检索三赛知识，并生成最小可用知识包。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from retrieve_cumcm_cases import (
    JOINT_COMPETITION_KEY,
    SUPPORTED_COMPETITIONS,
    balanced_top_k,
    build_questions,
    load_cases,
    rank_cases,
    rank_questions,
)


STAGE_FOCUS = {
    1: ["比较相似题的任务结构", "识别团队风险与证据边界", "题号不代替题型判断"],
    3: ["比较至少两条模型路线", "用数据条件和失效风险说明选择", "禁止迁移历史参数"],
    5: ["按子问接口递归求解", "打开中间状态", "为每个假设安排验证"],
    8: ["按子问闭环生成章节", "让图表支持唯一主张", "摘要只写已验证结果"],
    9: ["追踪问题到摘要的证据链", "检查竞赛身份与来源边界", "阻断无验证结论"],
}


def unique_values(values: list) -> list:
    """按首次出现顺序去重，并忽略空值。"""
    seen = set()
    output = []
    for value in values:
        marker = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if value and marker not in seen:
            seen.add(marker)
            output.append(value)
    return output


def compact_case(hit: dict) -> dict:
    """把案例命中压缩为 Stage 所需字段，避免携带全文证据包。"""
    case = hit["case"]
    return {
        "id": case.get("id"),
        "competition": case.get("competition"),
        "year": case.get("year"),
        "problem": case.get("problem"),
        "title": case.get("title"),
        "score": hit.get("score"),
        "task_type": case.get("task_type"),
        "paradigm": case.get("paradigm"),
        "problem_essence": case.get("essence", case.get("problem_essence")),
        "question_dependency": case.get("question_dependency", []),
        "recommended_chain": case.get("recommended_chain", []),
        "route_comparison": case.get("paper_route_comparison", []),
        "assumption_risks": case.get("assumption_risks", []),
        "required_checks": case.get("required_solution_checks", case.get("required_validation", [])),
        "figure_story": case.get("figure_story", case.get("figure_plan", [])),
        "writing_blueprint": case.get("writing_blueprint", []),
        "evidence_level": case.get("manual_evidence_level", case.get("evidence_level")),
        "evidence_scope": case.get("evidence_scope", case.get("review_scope")),
        "evidence_ids": case.get("reviewed_evidence_ids", case.get("evidence_ids", [])),
        "transfer_boundary": case.get("transfer_boundary"),
    }


def compact_question(hit: dict) -> dict:
    """把子问命中压缩为模型接口与证据字段。"""
    question = hit["question"]
    return {
        "id": question.get("id"),
        "competition": question.get("competition"),
        "case_id": question.get("case_id"),
        "paper_id": question.get("paper_id"),
        "year": question.get("year"),
        "problem": question.get("problem"),
        "question_id": question.get("question_id"),
        "question": question.get("question"),
        "score": hit.get("score"),
        "input_output": question.get("input_output"),
        "model_chain": question.get("model_chain", []),
        "intermediate_outputs": question.get("intermediate_outputs", []),
        "required_checks": question.get("required_checks", []),
        "validation_link": question.get("validation_link"),
        "transition": question.get("transition"),
        "evidence_level": question.get("evidence_level"),
        "evidence_ids": question.get("evidence_ids", []),
        "evidence_refs": question.get("evidence_refs", []),
        "transfer_boundary": question.get("transfer_boundary"),
    }


def build_stage_pack(query: str, competition: str, stage: int, top_k: int = 3) -> dict:
    """生成带检索命中、路线、验证、图表和写作字段的 Stage 知识包。"""
    cases = load_cases(competition)
    ranked_cases = balanced_top_k(rank_cases(query, cases), top_k, "case", competition)
    case_hits = [compact_case(hit) for hit in ranked_cases]
    questions = build_questions(cases, competition)
    ranked_questions = balanced_top_k(rank_questions(query, questions), top_k, "question", competition)
    question_hits = [compact_question(hit) for hit in ranked_questions]

    routes = unique_values([
        route
        for case in case_hits
        for route in ([" → ".join(case["recommended_chain"])] + case["route_comparison"])
        if route
    ])
    assumptions = unique_values([value for case in case_hits for value in case["assumption_risks"]])
    validations = unique_values(
        [value for case in case_hits for value in case["required_checks"]]
        + [value for question in question_hits for value in question["required_checks"]]
        + [question["validation_link"] for question in question_hits if question["validation_link"]]
    )
    figures = unique_values([value for case in case_hits for value in case["figure_story"]])
    writing = unique_values([value for case in case_hits for value in case["writing_blueprint"]])
    evidence_ids = unique_values(
        [value for case in case_hits for value in case["evidence_ids"]]
        + [value for question in question_hits for value in question["evidence_ids"]]
    )
    warnings = unique_values([
        case["transfer_boundary"] for case in case_hits if case["transfer_boundary"]
    ] + [
        "联合检索只共享方法接口和论文结构；竞赛、奖项、统计、模板和案例身份保持隔离。"
        if competition == JOINT_COMPETITION_KEY else ""
    ])

    return {
        "schema_version": "stage-pack-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "competition": competition,
        "stage": stage,
        "query": query,
        "stage_focus": STAGE_FOCUS[stage],
        "transfer_policy": "只迁移结构、方法接口、验证和叙事；历史数值、参数、权重、结论与原句必须重做。",
        "case_hits": case_hits,
        "question_hits": question_hits if stage in (3, 5, 8, 9) else [],
        "route_options": routes if stage in (3, 5) else [],
        "assumption_risks": assumptions if stage in (3, 5, 9) else [],
        "required_validations": validations if stage in (5, 8, 9) else [],
        "figure_story": figures if stage in (5, 8, 9) else [],
        "writing_blueprint": writing if stage in (8, 9) else [],
        "evidence_ids": evidence_ids,
        "warnings": warnings,
    }


def render_markdown(pack: dict) -> str:
    """把 Stage 知识包渲染为比赛期间可快速阅读的 Markdown。"""
    lines = [
        f"# Stage {pack['stage']} 知识包",
        "",
        f"- 竞赛范围：`{pack['competition']}`",
        f"- 查询：{pack['query']}",
        f"- 迁移规则：{pack['transfer_policy']}",
        "",
        "## 当前重点",
        "",
        *[f"- {item}" for item in pack["stage_focus"]],
        "",
        "## 相似案例",
        "",
    ]
    for hit in pack["case_hits"]:
        lines.append(f"- [{hit['competition']}] {hit['year']} {hit['problem']}题 {hit['title']}（{hit['score']:.4f}，{hit['evidence_level']}）")
    sections = [
        ("候选路线", "route_options"),
        ("假设风险", "assumption_risks"),
        ("必要验证", "required_validations"),
        ("图表叙事", "figure_story"),
        ("写作骨架", "writing_blueprint"),
        ("边界提醒", "warnings"),
    ]
    for title, key in sections:
        if pack.get(key):
            lines.extend(["", f"## {title}", "", *[f"- {value}" for value in pack[key]]])
    return "\n".join(lines) + "\n"


def main() -> int:
    """解析命令行并输出 JSON 或 Markdown 知识包。"""
    parser = argparse.ArgumentParser(description="按 Stage 生成三赛知识包")
    parser.add_argument("--competition", choices=sorted([*SUPPORTED_COMPETITIONS, JOINT_COMPETITION_KEY]), default="all")
    parser.add_argument("--stage", type=int, choices=sorted(STAGE_FOCUS), required=True)
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--query")
    query_group.add_argument("--problem-file", type=Path)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    query = args.query if args.query is not None else args.problem_file.read_text(encoding="utf-8")
    pack = build_stage_pack(query, args.competition, args.stage, max(1, args.top_k))
    content = (json.dumps(pack, ensure_ascii=False, indent=2) + "\n"
               if args.format == "json" else render_markdown(pack))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"[OK] output={args.output}")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
