"""审计论文中的问题、模型、结果、验证、图表与摘要主张证据链。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CHAIN_FIELDS = ("question", "model", "result", "validation", "figure", "abstract_claim")


def has_content(value) -> bool:
    """判断字符串、列表或对象是否包含有效内容。"""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def normalize_rows(payload: dict | list) -> list[dict]:
    """兼容论文计划与独立 evidence_ledger 两种输入。"""
    if isinstance(payload, list):
        return payload
    rows = payload.get("evidence_ledger")
    if rows is None:
        rows = payload.get("claims")
    if not isinstance(rows, list):
        raise ValueError("输入必须是 evidence_ledger/claims 数组，或直接是数组")
    return rows


def audit_row(row: dict, index: int) -> dict:
    """审计一条子问证据链并返回缺口和风险。"""
    row_id = row.get("question_id") or row.get("id") or f"row_{index}"
    missing = [field for field in CHAIN_FIELDS if not has_content(row.get(field))]
    issues = []
    if has_content(row.get("abstract_claim")) and not has_content(row.get("result")):
        issues.append("摘要主张没有结果支撑")
    if has_content(row.get("abstract_claim")) and not has_content(row.get("validation")):
        issues.append("摘要主张没有验证支撑")
    if has_content(row.get("result")) and not has_content(row.get("figure")):
        issues.append("结果尚未绑定图表或精确结果表")
    if has_content(row.get("model")) and not has_content(row.get("question")):
        issues.append("模型没有绑定题面任务")
    completed = len(CHAIN_FIELDS) - len(missing)
    return {
        "id": row_id,
        "status": "complete" if not missing and not issues else "incomplete",
        "coverage": round(completed / len(CHAIN_FIELDS), 4),
        "missing": missing,
        "issues": issues,
        "evidence_ids": row.get("evidence_ids", []),
        "chain": {field: row.get(field) for field in CHAIN_FIELDS},
    }


def trace_claims(payload: dict | list) -> dict:
    """生成整篇论文的证据链覆盖率、硬缺口和摘要门禁结论。"""
    rows = normalize_rows(payload)
    audited = [audit_row(row, index) for index, row in enumerate(rows, 1)]
    complete = sum(1 for row in audited if row["status"] == "complete")
    total = len(audited)
    missing_counts = {field: sum(field in row["missing"] for row in audited) for field in CHAIN_FIELDS}
    abstract_ready = total > 0 and complete == total
    return {
        "schema_version": "evidence-trace-1.0",
        "row_count": total,
        "complete_count": complete,
        "incomplete_count": total - complete,
        "coverage": round(sum(row["coverage"] for row in audited) / total, 4) if total else 0.0,
        "abstract_ready": abstract_ready,
        "abstract_gate": ("pass" if abstract_ready else "block_untraced_claims"),
        "missing_counts": missing_counts,
        "rows": audited,
    }


def render_markdown(report: dict) -> str:
    """把证据追踪结果渲染为简明审计报告。"""
    lines = [
        "# 论文结果证据追踪",
        "",
        f"- 完整链：{report['complete_count']}/{report['row_count']}",
        f"- 总覆盖率：{report['coverage']:.1%}",
        f"- 摘要门禁：`{report['abstract_gate']}`",
        "",
    ]
    for row in report["rows"]:
        lines.append(f"## {row['id']}：{row['status']}")
        lines.append("")
        lines.append(f"- 缺失：{'、'.join(row['missing']) or '无'}")
        lines.append(f"- 风险：{'；'.join(row['issues']) or '无'}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    """读取证据账本并输出审计结果。"""
    parser = argparse.ArgumentParser(description="追踪问题到摘要主张的证据链")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true", help="存在不完整证据链时返回失败码")
    args = parser.parse_args()

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        report = trace_claims(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    content = (json.dumps(report, ensure_ascii=False, indent=2) + "\n"
               if args.format == "json" else render_markdown(report))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"[OK] output={args.output}")
    else:
        print(content, end="")
    return 2 if args.strict and not report["abstract_ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
