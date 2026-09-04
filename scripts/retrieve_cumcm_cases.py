"""检索国赛、研究生赛或华数杯案例，并支持题目级与子问级结果。"""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
from collections import Counter
from pathlib import Path


TAG_PATTERNS = {
    "物理机理": r"物理|机理|受力|运动|温度|传热|电磁|流体|扩散",
    "优化决策": r"优化|最优|调度|分配|路径|选址|策略|目标函数|约束",
    "预测": r"预测|趋势|未来|时间序列",
    "评价排序": r"评价|排序|排名|指标|权重",
    "统计推断": r"统计|检验|相关|回归|置信",
    "分类识别": r"分类|识别|判别|标签",
    "聚类分群": r"聚类|分群",
    "网络与路径": r"网络|节点|边|路径|连通|拓扑",
    "仿真模拟": r"仿真|模拟|随机",
    "数据清洗": r"缺失|异常|清洗|预处理",
}

SUPPORTED_COMPETITIONS = {
    "cumcm": "CUMCM 国赛",
    "huaweibei": "中国研究生数学建模竞赛（华为杯）",
    "huashubei": "华数杯",
}

JOINT_COMPETITION_KEY = "all"

SKILL_ROOT = Path(__file__).resolve().parent.parent


def tokenize(text: str) -> Counter:
    """用英文词和中文二元组构造轻量检索特征。"""
    normalized = re.sub(r"\s+", "", text.lower())
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", normalized))
    grams = [chinese[index:index + 2] for index in range(max(0, len(chinese) - 1))]
    words = re.findall(r"[a-z][a-z0-9_+-]{1,}", normalized)
    return Counter(grams + words)


def case_text(case: dict) -> str:
    """把案例的结构化标签合成检索文本。"""
    fields = [case.get("title", ""), case.get("essence", ""),
              case.get("problem_essence", ""), case.get("paradigm", ""),
              *case.get("task_tags", []), *case.get("domain_tags", []),
              *case.get("recommended_chain", []), *case.get("question_dependency", []),
              *case.get("consensus_chain", []), *case.get("paper_route_comparison", []),
              *case.get("assumption_risks", []), *case.get("required_solution_checks", []),
              *case.get("required_validation", []), case.get("transfer_boundary", "")]
    fields.extend(item["name"] for item in case.get("model_families", []))
    fields.extend(item["name"] for item in case.get("validation_methods", []))
    return " ".join(fields)


def question_text(question: dict) -> str:
    """把子问记录合成检索文本。"""
    fields = [
        question.get("title", ""), question.get("question", ""),
        question.get("motivation", ""), question.get("input_output", ""),
        question.get("derivation_logic", ""), question.get("solver_logic", ""),
        question.get("result_interpretation", ""), question.get("validation_link", ""),
        question.get("transition", ""), question.get("transfer_boundary", ""),
        *question.get("model_chain", []), *question.get("intermediate_outputs", []),
        *question.get("required_checks", []), *question.get("figure_story", []),
    ]
    return " ".join(str(value) for value in fields if value)


def cosine(query: Counter, document: Counter, idf: dict[str, float]) -> float:
    """计算带逆文档频率权重的余弦相似度。"""
    common = set(query) & set(document)
    numerator = sum(query[token] * document[token] * idf.get(token, 1.0) ** 2 for token in common)
    query_norm = math.sqrt(sum((count * idf.get(token, 1.0)) ** 2 for token, count in query.items()))
    doc_norm = math.sqrt(sum((count * idf.get(token, 1.0)) ** 2 for token, count in document.items()))
    return numerator / (query_norm * doc_norm) if query_norm and doc_norm else 0.0


def rank_cases(query_text: str, cases: list[dict]) -> list[dict]:
    """综合文本相似度、任务标签和证据等级排序案例。"""
    vectors = [tokenize(case_text(case)) for case in cases]
    document_frequency = Counter()
    for vector in vectors:
        document_frequency.update(vector.keys())
    total = max(1, len(cases))
    idf = {token: math.log((total + 1) / (count + 1)) + 1 for token, count in document_frequency.items()}
    query_vector = tokenize(query_text)
    query_tags = {name for name, pattern in TAG_PATTERNS.items() if re.search(pattern, query_text)}
    ranked = []
    for case, vector in zip(cases, vectors):
        text_score = cosine(query_vector, vector, idf)
        searchable_text = case_text(case)
        case_tags = {name for name, pattern in TAG_PATTERNS.items() if re.search(pattern, searchable_text)}
        tag_score = len(query_tags & case_tags) / max(1, len(query_tags))
        base_evidence = {"high": 0.08, "medium": 0.05, "problem_only": 0.0}.get(case.get("evidence_level"), 0.0)
        manual_count = case.get("reviewed_paper_count", 0)
        manual_evidence = 0.08 if manual_count >= 3 else 0.05 if manual_count == 2 else 0.03 if manual_count == 1 else 0.0
        review_bonus = 0.02 if case.get("manual_status") == "reviewed" else 0.0
        score = min(1.0, text_score * 0.76 + tag_score * 0.14 + max(base_evidence, manual_evidence) + review_bonus)
        ranked.append({"score": round(score, 4), "matched_tags": sorted(query_tags & case_tags), "case": case})
    return sorted(ranked, key=lambda item: (
        -item["score"],
        -item["case"].get("reviewed_paper_count", 0),
        -item["case"].get("paper_count", 0),
    ))


def rank_questions(query_text: str, questions: list[dict]) -> list[dict]:
    """综合文本相似度、任务标签和证据粒度对子问排序。"""
    vectors = [tokenize(question_text(question)) for question in questions]
    document_frequency = Counter()
    for vector in vectors:
        document_frequency.update(vector.keys())
    total = max(1, len(questions))
    idf = {token: math.log((total + 1) / (count + 1)) + 1
           for token, count in document_frequency.items()}
    query_vector = tokenize(query_text)
    query_tags = {name for name, pattern in TAG_PATTERNS.items() if re.search(pattern, query_text)}
    evidence_bonus = {
        "star_paper_full_text": 0.12,
        "cross_paper_manual": 0.09,
        "paper_pattern": 0.05,
        "problem_summary_only": 0.0,
    }
    ranked = []
    for question, vector in zip(questions, vectors):
        text_score = cosine(query_vector, vector, idf)
        searchable_text = question_text(question)
        question_tags = {name for name, pattern in TAG_PATTERNS.items()
                         if re.search(pattern, searchable_text)}
        tag_score = len(query_tags & question_tags) / max(1, len(query_tags))
        bonus = evidence_bonus.get(question.get("evidence_level"), 0.0)
        score = min(1.0, text_score * 0.80 + tag_score * 0.10 + bonus)
        ranked.append({
            "score": round(score, 4),
            "matched_tags": sorted(query_tags & question_tags),
            "question": question,
        })
    return sorted(ranked, key=lambda item: (
        -item["score"],
        -len(item["question"].get("evidence_ids", [])),
        item["question"].get("id", ""),
    ))


def balanced_top_k(ranked: list[dict], top_k: int, payload_key: str,
                   competition: str) -> list[dict]:
    """联合检索在容量允许时保证三赛各有一条，再按原相似度顺序补齐。"""
    limit = max(1, top_k)
    if competition != JOINT_COMPETITION_KEY or limit < len(SUPPORTED_COMPETITIONS):
        return ranked[:limit]
    selected_indexes = set()
    for competition_key in SUPPORTED_COMPETITIONS:
        for index, item in enumerate(ranked):
            if item[payload_key].get("competition") == competition_key:
                selected_indexes.add(index)
                break
    for index in range(len(ranked)):
        if len(selected_indexes) >= limit:
            break
        selected_indexes.add(index)
    return [ranked[index] for index in sorted(selected_indexes)[:limit]]


def merge_manual_reviews(cases: list[dict], manual_payload: dict | None) -> list[dict]:
    """以不覆盖基础来源字段的方式合并人工复核覆盖层。"""
    if not manual_payload:
        return cases
    manual_cases = {item["id"]: item for item in manual_payload.get("cases", [])}
    merged_cases = []
    manual_fields = (
        "title", "source_title", "paradigm", "source_paradigm", "problem_essence", "source_problem_essence",
        "transfer_boundary", "source_transfer_boundary", "question_dependency", "consensus_chain",
        "paper_route_comparison", "result_disagreements", "assumption_risks",
        "required_solution_checks", "figure_story", "writing_blueprint",
        "source_review_flags", "manual_status", "review_scope",
    )
    for source_case in cases:
        case = copy.deepcopy(source_case)
        manual = manual_cases.get(case["id"])
        if manual:
            case["source_essence"] = case.get("essence")
            case["source_recommended_chain"] = case.get("recommended_chain", [])
            case["source_required_validation"] = case.get("required_validation", [])
            case["source_figure_plan"] = case.get("figure_plan", [])
            for field in manual_fields:
                case[field] = manual.get(field)
            case["essence"] = manual.get("problem_essence", case.get("essence"))
            case["recommended_chain"] = manual.get("consensus_chain", case.get("recommended_chain", []))
            case["required_validation"] = manual.get("required_solution_checks", case.get("required_validation", []))
            case["figure_plan"] = manual.get("figure_story", case.get("figure_plan", []))
            case["reviewed_evidence_ids"] = manual.get("evidence_ids", [])
            case["reviewed_paper_count"] = len(case["reviewed_evidence_ids"])
            count = case["reviewed_paper_count"]
            case["manual_evidence_level"] = "cross_paper_high" if count >= 3 else "cross_paper_medium" if count == 2 else "single_paper"
            case["question_evidence_ids"] = manual.get("question_evidence_ids", {})
            case["evidence_quality"] = manual.get("evidence_quality", [])
        merged_cases.append(case)
    return merged_cases


def load_competition_cases(competition: str, index_path: Path | None = None,
                           manual_path: Path | None = None) -> list[dict]:
    """加载单个竞赛案例，并保留竞赛身份。"""
    resolved_index = index_path or SKILL_ROOT / "competitions" / competition / "cases" / "index.json"
    if not resolved_index.exists():
        raise FileNotFoundError(f"案例索引不存在: {resolved_index}")
    payload = json.loads(resolved_index.read_text(encoding="utf-8"))
    resolved_manual = manual_path or resolved_index.parent / "manual_review_annotations.json"
    manual_payload = (json.loads(resolved_manual.read_text(encoding="utf-8"))
                      if resolved_manual.exists() else None)
    cases = merge_manual_reviews(payload.get("cases", []), manual_payload)
    for case in cases:
        case["competition"] = case.get("competition", competition)
        if case["competition"] != competition:
            raise ValueError(f"索引 {resolved_index} 包含其他竞赛案例: {case.get('id', '<missing>')}")
    return cases


def load_cases(competition: str, index_path: Path | None = None,
               manual_path: Path | None = None) -> list[dict]:
    """加载单赛或三赛联合案例。"""
    if competition == JOINT_COMPETITION_KEY:
        if index_path or manual_path:
            raise ValueError("competition=all 时不能使用单一 --index/--manual-review")
        cases = []
        for key in SUPPORTED_COMPETITIONS:
            cases.extend(load_competition_cases(key))
        return cases
    return load_competition_cases(competition, index_path, manual_path)


def canonical_question_id(text: str, index: int) -> str:
    """从描述开头提取 Q 编号，提取失败时使用顺序编号。"""
    match = re.match(r"\s*Q?\s*(\d+)", text, flags=re.IGNORECASE)
    return f"Q{match.group(1)}" if match else f"S{index}"


def evidence_for_question(case: dict, question_id: str) -> list[str]:
    """兼容 Q1 与 1 两种人工证据键。"""
    mapping = case.get("question_evidence_ids", {}) or {}
    numeric = question_id[1:] if question_id.startswith("Q") else question_id
    return list(mapping.get(question_id) or mapping.get(numeric) or [])


def build_case_questions(cases: list[dict]) -> list[dict]:
    """把案例的逐问依赖拆成可独立检索的子问记录。"""
    records = []
    for case in cases:
        dependencies = case.get("question_dependency", []) or []
        for index, dependency in enumerate(dependencies, 1):
            question_id = canonical_question_id(str(dependency), index)
            evidence_ids = evidence_for_question(case, question_id)
            if case.get("manual_status") == "reviewed":
                evidence_level = "cross_paper_manual"
            else:
                evidence_level = case.get("question_evidence_level", case.get("evidence_level", "problem_summary_only"))
            records.append({
                "id": f"{case['id']}:{question_id}",
                "competition": case["competition"],
                "case_id": case["id"],
                "year": case.get("year"),
                "problem": case.get("problem"),
                "title": case.get("title", ""),
                "question_id": question_id,
                "question": str(dependency),
                "model_chain": case.get("recommended_chain", []),
                "required_checks": case.get("required_solution_checks", case.get("required_validation", [])),
                "figure_story": case.get("figure_story", case.get("figure_plan", [])),
                "transition": case.get("writing_blueprint", [""])[0] if case.get("writing_blueprint") else "",
                "transfer_boundary": case.get("transfer_boundary", ""),
                "evidence_level": evidence_level,
                "evidence_ids": (evidence_ids or case.get("reviewed_evidence_ids", [])
                                 or case.get("evidence_ids", [])),
                "source_type": "case_annotation",
            })
    return records


def load_star_paper_questions(competition: str) -> list[dict]:
    """加载有全文页码证据的提名论文子问；当前仅研究生赛具备该层。"""
    if competition not in ("huaweibei", JOINT_COMPETITION_KEY):
        return []
    path = SKILL_ROOT / "competitions" / "huaweibei" / "papers" / "manual_paper_reviews.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for paper in payload.get("papers", []):
        for body in paper.get("modeling_body_by_q", []):
            question_id = body.get("question", "Q?")
            records.append({
                "id": f"{paper['paper_id']}:{question_id}",
                "competition": "huaweibei",
                "case_id": paper.get("case_id"),
                "paper_id": paper.get("paper_id"),
                "year": paper.get("year"),
                "problem": paper.get("problem"),
                "title": paper.get("title", ""),
                "question_id": question_id,
                "question": body.get("motivation", question_id),
                "motivation": body.get("motivation", ""),
                "input_output": body.get("input_output", ""),
                "model_chain": body.get("model_chain", []),
                "derivation_logic": body.get("derivation_logic", ""),
                "solver_logic": body.get("solver_logic", ""),
                "intermediate_outputs": body.get("intermediate_outputs", []),
                "result_interpretation": body.get("result_interpretation", ""),
                "validation_link": body.get("validation_link", ""),
                "transition": body.get("transition", ""),
                "figure_story": [],
                "transfer_boundary": paper.get("transfer_boundary", ""),
                "evidence_level": "star_paper_full_text",
                "evidence_ids": [paper.get("paper_id")],
                "evidence_refs": body.get("evidence_refs", []),
                "source_type": "star_paper_review",
            })
    return records


def build_questions(cases: list[dict], competition: str) -> list[dict]:
    """聚合题级人工层与提名论文全文层的子问。"""
    return build_case_questions(cases) + load_star_paper_questions(competition)


def joined(case: dict, field: str, fallback: str = "未记录") -> str:
    """把人工复核数组压缩为适合检索报告的一行文本。"""
    values = case.get(field) or []
    return "；".join(str(value).rstrip("。；") for value in values) if values else fallback


def render_markdown(results: list[dict], competition: str = "cumcm") -> str:
    """把检索结果整理成建模阶段可读的短报告。"""
    competition_name = ("研究生赛、华数杯与国赛联合" if competition == JOINT_COMPETITION_KEY
                        else SUPPORTED_COMPETITIONS.get(competition, competition))
    lines = [
        f"# {competition_name}相似案例检索",
        "",
        "> 只迁移问题结构、验证方法和叙事方式。历史数值、参数、假设和论文原句禁止直接迁移。",
        "",
    ]
    for index, item in enumerate(results, 1):
        case = item["case"]
        models = "、".join(model["name"] for model in case.get("model_families", [])[:6]) or "无论文证据"
        validations = "、".join(method["name"] for method in case.get("validation_methods", [])[:5]) or "未识别"
        chain = " → ".join(case.get("recommended_chain", [])) or models
        required = "、".join(case.get("required_validation", [])) or validations
        boundary = case.get("transfer_boundary", "只迁移建模思想，必须重新核对新题数据、假设、约束和量纲。")
        evidence_ids = case.get("reviewed_evidence_ids", [])
        evidence_text = "、".join(f"`{value}`" for value in evidence_ids) or "无人工论文证据"
        lines.extend([
            f"## {index}. [{case.get('competition', competition)}] {case['year']} {case['problem']}题：{case['title']}", "",
            f"- 相似度：{item['score']:.4f}；匹配任务：{'、'.join(item['matched_tags']) or '文本相似'}。",
            f"- 基础索引证据：{case.get('paper_count', 0)} 篇，等级 `{case.get('evidence_level', 'count_only')}`；人工复核证据：{case.get('reviewed_paper_count', 0)} 篇，等级 `{case.get('manual_evidence_level', 'none')}`，状态 `{case.get('manual_status', 'unreviewed')}`。",
            f"- 复核范式：{case.get('paradigm', '未标注')}。",
            f"- 问题本质：{case.get('essence', '未标注')}。", f"- 推荐模型链：{chain}。",
            f"- 逐问依赖：{joined(case, 'question_dependency')}。",
            f"- 跨论文共识链：{joined(case, 'consensus_chain', chain)}。",
            f"- 路线比较：{joined(case, 'paper_route_comparison', models)}。",
            f"- 历史结果分歧（仅用于校准）：{joined(case, 'result_disagreements')}。",
            f"- 主要假设风险：{joined(case, 'assumption_risks')}。",
            f"- 必做验证：{joined(case, 'required_solution_checks', required)}。",
            f"- 图表叙事：{joined(case, 'figure_story')}。",
            f"- 写作骨架：{joined(case, 'writing_blueprint')}。",
            f"- 人工证据 ID：{evidence_text}。",
            f"- 使用边界：{boundary}",
            "",
        ])
    return "\n".join(lines)


def render_question_markdown(results: list[dict], competition: str) -> str:
    """把子问检索结果整理为可追溯短报告。"""
    competition_name = ("研究生赛、华数杯与国赛联合" if competition == JOINT_COMPETITION_KEY
                        else SUPPORTED_COMPETITIONS.get(competition, competition))
    lines = [
        f"# {competition_name}子问级检索",
        "",
        "> 子问结果只迁移接口、推导顺序、验证和图表角色；历史参数、结果与原句必须重做。",
        "",
    ]
    for index, item in enumerate(results, 1):
        question = item["question"]
        lines.extend([
            f"## {index}. [{question['competition']}] {question.get('year')} {question.get('problem')}题 {question.get('question_id')}：{question.get('title')}",
            "",
            f"- 相似度：{item['score']:.4f}；来源层：`{question.get('source_type')}`；证据等级：`{question.get('evidence_level')}`。",
            f"- 子问任务：{question.get('question', '未记录')}。",
            f"- 模型链：{' → '.join(question.get('model_chain', [])) or '未记录'}。",
            f"- 中间量：{'、'.join(question.get('intermediate_outputs', [])) or '需按新题定义'}。",
            f"- 必做验证：{'、'.join(question.get('required_checks', [])) or question.get('validation_link', '未记录')}。",
            f"- 图表角色：{'、'.join(question.get('figure_story', [])) or '需按新题生成'}。",
            f"- 证据 ID：{'、'.join(question.get('evidence_ids', [])) or '无论文级证据'}。",
            f"- 使用边界：{question.get('transfer_boundary', '不得迁移历史数值和结论。')}",
            "",
        ])
    return "\n".join(lines)


def main() -> int:
    """读取查询并输出前若干相似案例。"""
    parser = argparse.ArgumentParser(description="检索国赛、研究生赛或华数杯深度蒸馏案例")
    parser.add_argument("--competition", choices=sorted([*SUPPORTED_COMPETITIONS, JOINT_COMPETITION_KEY]), default="cumcm")
    parser.add_argument("--level", choices=("case", "question", "both"), default="case",
                        help="题目级、子问级或同时检索")
    parser.add_argument("--index", type=Path, help="案例索引；默认按 competition 从 skill 内加载")
    parser.add_argument("--manual-review", type=Path, help="人工复核 JSON；默认读取索引同目录下的 manual_review_annotations.json")
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--query")
    query_group.add_argument("--problem-file", type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    if args.competition == JOINT_COMPETITION_KEY and (args.index or args.manual_review):
        parser.error("competition=all 时不能使用 --index 或 --manual-review")
    query_text = args.query if args.query is not None else args.problem_file.read_text(encoding="utf-8")
    try:
        cases = load_cases(args.competition, args.index, args.manual_review)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    case_results = balanced_top_k(rank_cases(query_text, cases), args.top_k, "case", args.competition)
    questions = build_questions(cases, args.competition)
    question_results = balanced_top_k(
        rank_questions(query_text, questions), args.top_k, "question", args.competition
    )
    if args.format == "json":
        payload = {
            "schema_version": "case-retrieval-2.0",
            "competition": args.competition,
            "level": args.level,
        }
        if args.level in ("case", "both"):
            payload["case_results"] = case_results
        if args.level in ("question", "both"):
            payload["question_results"] = question_results
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        blocks = []
        if args.level in ("case", "both"):
            blocks.append(render_markdown(case_results, args.competition))
        if args.level in ("question", "both"):
            blocks.append(render_question_markdown(question_results, args.competition))
        print("\n\n".join(blocks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
