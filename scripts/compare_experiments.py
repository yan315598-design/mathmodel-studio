"""Compare measured candidates under one evaluation protocol, without training models."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from pathlib import Path

from inspect_assets import sha256


def finite(value, label: str, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if nonnegative and value < 0:
        raise ValueError(f"{label} must be nonnegative")
    return float(value)


def compare(data: dict, base: Path) -> dict:
    if data.get("schema_version") == "experiments-2":
        from experiment_protocol_v2 import compare_v2
        return compare_v2(data, base)
    if data.get("schema_version") != "experiments-1":
        raise ValueError("expected schema_version experiments-1")
    protocol = data["protocol"]
    for field in ("task", "dataset_sha256", "split_id", "metric", "direction", "evaluation_role", "budget_s"):
        if not protocol.get(field):
            raise ValueError(f"protocol requires {field}")
    if protocol["direction"] not in {"min", "max"}:
        raise ValueError("direction must be min or max")
    if protocol["evaluation_role"] != "validation":
        raise ValueError("model selection must use validation, not final test scores")
    for field in ("dataset_sha256", "split_id"):
        if not isinstance(protocol[field], str) or not re.fullmatch(r"[0-9a-f]{64}", protocol[field]):
            raise ValueError(f"{field} must be a SHA-256 snapshot identifier")
    budget = finite(protocol["budget_s"], "budget_s", True)
    tolerance = finite(protocol.get("practical_tolerance", 0), "practical_tolerance", True)
    keys = protocol["replicates"]
    if not isinstance(keys, list) or not keys or any(not isinstance(k, str) or not k for k in keys):
        raise ValueError("replicates must be nonempty fold/seed/instance identifiers")
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate replicate identifiers")
    candidates = data["candidates"]
    if not candidates:
        raise ValueError("no candidates supplied")
    rows, excluded, ids = [], [], set()
    for candidate in candidates:
        name = candidate["id"]
        if not isinstance(name, str) or not name or name in ids:
            raise ValueError("candidate identifiers must be unique nonempty strings")
        ids.add(name)
        if candidate.get("status") != "completed":
            excluded.append({"id": name, "reason": candidate.get("reason", "not completed")})
            continue
        if candidate.get("protocol") != protocol:
            raise ValueError(f"{name}: evaluation protocol differs")
        explanation = candidate.get("interpretability")
        if not isinstance(explanation, str) or not explanation.strip():
            raise ValueError(f"{name}: interpretability description required")
        runs = candidate["runs"]
        if len(runs) != len(keys) or {run["replicate"] for run in runs} != set(keys):
            raise ValueError(f"{name}: missing or duplicate replicates")
        values, times, memory = [], [], []
        for run in runs:
            if run.get("feasible") is not True:
                raise ValueError(f"{name}: infeasible run cannot enter ranking")
            values.append(finite(run["value"], f"{name}.value"))
            times.append(finite(run["elapsed_s"], f"{name}.elapsed_s", True))
            memory.append(finite(run["peak_memory_mb"], f"{name}.peak_memory_mb", True))
            evidence = run["evidence"]
            artifact = (base / evidence["path"]).resolve()
            if not artifact.is_file() or sha256(artifact) != evidence["sha256"]:
                raise ValueError(f"{name}: missing or stale evidence {evidence['path']}")
        if any(elapsed > budget for elapsed in times):
            excluded.append({"id": name, "reason": "per-run time budget exceeded"})
            continue
        rows.append({"id": name, "mean": statistics.mean(values),
                     "std": statistics.stdev(values) if len(values) > 1 else None,
                     "mean_elapsed_s": statistics.mean(times), "peak_memory_mb": max(memory),
                     "interpretability": explanation, "replicates": len(values)})
    if not rows:
        raise ValueError("no feasible completed candidate within budget")
    sign = 1 if protocol["direction"] == "min" else -1
    rows.sort(key=lambda row: (sign * row["mean"], row["id"]))
    best = rows[0]["mean"]
    shortlist = [row for row in rows if abs(row["mean"] - best) <= tolerance]
    recommendation = min(shortlist, key=lambda row: (
        row["std"] if row["std"] is not None else math.inf,
        row["mean_elapsed_s"], row["peak_memory_mb"], row["id"]))
    return {"schema_version": "comparison-1", "protocol": protocol, "ranking": rows,
            "excluded": excluded, "recommendation": recommendation["id"],
            "selection_status": "provisional", "policy": "metric tolerance, then stability, time, memory; review interpretability",
            "warnings": (["single replicate: stability not measured"] if len(keys) == 1 else [])
                        + (["single candidate: no competitive evidence"] if len(rows) == 1 else [])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("output exists; use a new report path")
        report = compare(json.loads(args.manifest.read_text(encoding="utf-8")), args.manifest.parent)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"[ERROR] {error}\n")
    print(f"[comparison] candidates={len(report['ranking'])} provisional={report['recommendation']} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
