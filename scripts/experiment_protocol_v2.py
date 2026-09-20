"""Explicit task-aware comparison; no implicit cross-instance scalarization."""

import math
import re
import statistics
from datetime import datetime
from pathlib import Path

from inspect_assets import sha256


def number(value, label, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label}: finite number required")
    if positive and value < 0:
        raise ValueError(f"{label}: nonnegative number required")
    return float(value)


def compare_v2(data: dict, base: Path) -> dict:
    protocol = data["protocol"]
    task = protocol.get("task")
    if task not in {"prediction", "optimization", "numerical"}:
        raise ValueError("task must be prediction, optimization or numerical")
    if not re.fullmatch("[0-9a-f]{64}", str(protocol.get("dataset_sha256", ""))):
        raise ValueError("dataset_sha256 required")
    if task == "prediction":
        if protocol.get("evaluation_role") != "validation":
            raise ValueError("prediction selection requires validation, never final test")
        if not re.fullmatch("[0-9a-f]{64}", str(protocol.get("split_id", ""))):
            raise ValueError("split_id snapshot required")
        split = protocol.get("split", {})
        if split.get("unit") not in {"sample", "group", "time"}:
            raise ValueError("explicit sample/group/time split required")
        train, valid = split.get("train", []), split.get("validation", [])
        if not all(isinstance(v, list) for v in (train, valid)):
            raise ValueError("split identifiers must be lists")
        if any(isinstance(v, bool) or not isinstance(v, (str, int, float))
               or (isinstance(v, str) and not v.strip())
               or (isinstance(v, (int, float)) and not math.isfinite(v)) for v in train+valid):
            raise ValueError("split identifiers must be nonempty strings or finite numbers")
        if not train or not valid or len(set(train)) != len(train) or len(set(valid)) != len(valid):
            raise ValueError("nonempty unique split identifiers required")
        if set(train) & set(valid):
            raise ValueError("train/validation leakage")
        if split["unit"] == "time":
            if all(isinstance(v, str) for v in train+valid):
                try:
                    train = [datetime.fromisoformat(v) for v in train]
                    valid = [datetime.fromisoformat(v) for v in valid]
                except ValueError as error:
                    raise ValueError("time strings must be ISO-8601 timestamps") from error
            elif not all(isinstance(v, (int, float)) for v in train+valid):
                raise ValueError("time split must not mix numbers and timestamps")
            try:
                if max(train) >= min(valid):
                    raise ValueError("time split must be ordered without future leakage")
            except TypeError as error:
                raise ValueError("time split must use consistent timezone awareness") from error
    elif protocol.get("evaluation_role") != "benchmark":
        raise ValueError("optimization/numerical require benchmark role")
    objectives = protocol.get("objectives", [])
    if not objectives or any(not isinstance(o.get("name"), str) or not o["name"].strip()
                             or o.get("direction") not in {"min", "max"} or not o.get("unit") for o in objectives):
        raise ValueError("objectives need name, direction and unit")
    names = [o["name"] for o in objectives]
    if len(set(names)) != len(names):
        raise ValueError("duplicate objectives")
    instances = protocol.get("instances", [])
    repeats = protocol.get("repeats", [])
    for label, values in (("instances", instances), ("repeats", repeats)):
        if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v for v in values) or len(set(values)) != len(values):
            raise ValueError(f"{label} must contain unique nonempty strings")
    budget = number(protocol["budget_s"], "budget_s", True)
    if budget == 0:
        raise ValueError("budget_s must be positive")
    required = {(instance, repeat) for instance in instances for repeat in repeats}
    rows, excluded, ids = [], [], set()
    for candidate in data["candidates"]:
        key = candidate["id"]
        if not isinstance(key, str) or not key or key in ids:
            raise ValueError("unique nonempty candidate ids required")
        ids.add(key)
        if candidate.get("status") != "completed":
            excluded.append({"id": key, "reason": candidate.get("reason", "not completed")})
            continue
        if candidate.get("protocol") != protocol:
            raise ValueError(f"{key}: protocol differs")
        if not isinstance(candidate.get("interpretability"), str) or not candidate["interpretability"].strip():
            raise ValueError(f"{key}: interpretability explanation required")
        runs = candidate["runs"]
        if len(runs) != len(required) or {(r["instance"], r["repeat"]) for r in runs} != required:
            raise ValueError(f"{key}: incomplete/duplicate instance-repeat grid")
        times, memories, reasons = [], [], []
        values = {instance: {name: [] for name in names} for instance in instances}
        for run in runs:
            evidence = run["evidence"]
            path = base / evidence["path"]
            if not path.is_file() or sha256(path) != evidence["sha256"]:
                raise ValueError(f"{key}: stale evidence")
            if run.get("feasible") is not True:
                reasons.append("infeasible or feasibility unknown")
                continue
            if set(run["metrics"]) != set(names):
                raise ValueError(f"{key}: all declared objectives required")
            for name in names:
                values[run["instance"]][name].append(number(run["metrics"][name], name))
            elapsed = run.get("elapsed_s")
            memory = run.get("peak_memory_mb")
            times.append(None if elapsed is None else number(elapsed, "elapsed_s", True))
            memories.append(None if memory is None else number(memory, "peak_memory_mb", True))
            if elapsed is not None and elapsed > budget:
                reasons.append("per-run budget exceeded")
        if reasons:
            excluded.append({"id": key, "reason": "; ".join(sorted(set(reasons)))})
            continue
        complete_time = all(t is not None for t in times)
        complete_memory = all(m is not None for m in memories)
        rows.append({"id": key, "instances": {i: {n: {"mean": statistics.mean(v),
                     "std": statistics.stdev(v) if len(v) > 1 else None, "n": len(v)}
                     for n, v in measures.items()} for i, measures in values.items()},
                     "mean_elapsed_s": statistics.mean(times) if complete_time else None,
                     "peak_memory_mb": max(memories) if complete_memory else None,
                     "cost_status": "complete" if complete_time and complete_memory else "partial",
                     "budget_status": "verified" if complete_time else "unknown",
                     "interpretability": candidate["interpretability"]})
    if not rows:
        raise ValueError("no feasible completed candidate")
    def vector(row):
        return [row["instances"][i][o["name"]]["mean"] * (1 if o["direction"] == "min" else -1)
                for i in instances for o in objectives]
    def dominates(a, b):
        av, bv = vector(a), vector(b)
        return all(x <= y for x,y in zip(av,bv)) and any(x < y for x,y in zip(av,bv))
    front = [r["id"] for r in rows if not any(dominates(other, r) for other in rows)]
    partial = any(r["cost_status"] == "partial" for r in rows)
    recommendation = front[0] if len(front) == 1 and not partial else None
    return {"schema_version": "comparison-2", "protocol": protocol, "ranking": rows,
            "ranking_kind": "unordered per-instance summaries", "pareto_front": front,
            "recommendation": recommendation, "excluded": excluded,
            "selection_status": "partial" if partial else "provisional",
            "policy": "dominance across declared instance-objective coordinates; no scalarization or cost imputation",
            "warnings": (["single repeat: within-instance stability unknown"] if len(repeats) == 1 else [])
                        + (["missing costs: no complete ranking or budget guarantee"] if partial else [])
                        + (["single candidate: no competitive evidence"] if len(rows) == 1 else [])}
