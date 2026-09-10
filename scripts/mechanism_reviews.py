"""Load optional, provenance-preserving local mechanism reviews."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_FIELDS = (
    "id", "case_id", "competition", "question_id", "trigger", "baseline_gap",
    "representation", "module_reason", "interface", "counterexample", "transfer_boundary",
)
STATUSES = {"proposed", "source_checked", "locally_tested"}


def nonempty_text(value):
    return isinstance(value, str) and bool(value.strip())


def validate_payload(payload, competition):
    if not isinstance(payload, dict) or payload.get("schema_version") != "mechanism-review-1.0":
        raise ValueError("Unsupported mechanism review schema")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("Mechanism records must be an array")
    seen = set()
    for index, record in enumerate(records):
        prefix = f"Mechanism record {index}"
        if not isinstance(record, dict) or any(not nonempty_text(record.get(k)) for k in TEXT_FIELDS):
            raise ValueError(f"{prefix}: missing required text")
        if record["id"] in seen:
            raise ValueError(f"{prefix}: duplicate id {record['id']}")
        seen.add(record["id"])
        if record["competition"] != competition:
            raise ValueError(f"{prefix}: competition mismatch")
        if record.get("review_status") not in STATUSES:
            raise ValueError(f"{prefix}: invalid review status")
        for field in ("assumptions", "limitations"):
            values = record.get(field)
            if not isinstance(values, list) or not values or not all(map(nonempty_text, values)):
                raise ValueError(f"{prefix}: {field} must contain explicit conditions")
        refs = record.get("source_refs")
        if not isinstance(refs, list) or not refs or any(
            not isinstance(ref, dict) or any(not nonempty_text(ref.get(k)) for k in ("kind", "location", "scope"))
            for ref in refs
        ):
            raise ValueError(f"{prefix}: source provenance required")
        validation = record.get("validation")
        if not isinstance(validation, dict) or any(
            not nonempty_text(validation.get(k)) for k in ("level", "observation", "not_established")
        ):
            raise ValueError(f"{prefix}: validation scope required")
    return records


def load_mechanism_reviews(case_hits, stage, root=ROOT):
    """An absent sidecar is compatible; a present invalid sidecar fails visibly."""
    if stage not in (3, 5, 8, 9):
        return []
    selected = {}
    for hit in case_hits:
        competition = hit["competition"]
        if not nonempty_text(competition) or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in competition):
            raise ValueError("Invalid competition key")
        selected.setdefault(competition, set()).add(hit["id"])
    reviews = []
    for competition, case_ids in selected.items():
        path = Path(root) / "competitions" / competition / "cases" / "mechanism_reviews.json"
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            records = validate_payload(payload, competition)
        except (ValueError, OSError) as exc:
            raise ValueError(f"{path}: {exc}") from exc
        reviews.extend(record for record in records if record["case_id"] in case_ids)
    return reviews
