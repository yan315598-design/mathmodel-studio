"""Counterexamples for task-aware comparisons; no fake benchmark winners."""

import copy
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_experiments import compare
from inspect_assets import sha256


def fixture(tmp_path, task="optimization"):
    evidence = tmp_path / "observations.json"
    evidence.write_text('{"synthetic": true}')
    protocol = {"task": task, "dataset_sha256": "a"*64,
                "evaluation_role": "benchmark", "budget_s": 10,
                "instances": ["small", "large"], "repeats": ["0", "1"],
                "objectives": [{"name": "error", "direction": "min", "unit": "1"}]}
    if task == "prediction":
        protocol.update(evaluation_role="validation", split_id="b"*64,
                        split={"unit": "group", "train": ["file1"], "validation": ["file2"]})
    data = {"schema_version": "experiments-2", "protocol": protocol, "candidates": []}
    for key, offset in (("one", 0), ("two", 1)):
        data["candidates"].append({"id": key, "status": "completed", "protocol": copy.deepcopy(protocol),
          "interpretability": "synthetic baseline", "runs": [
            {"instance": instance, "repeat": repeat, "metrics": {"error": base+offset},
             "elapsed_s": 1, "peak_memory_mb": 10, "feasible": True,
             "evidence": {"path": evidence.name, "sha256": sha256(evidence)}}
            for instance, base in (("small", 1), ("large", 1000)) for repeat in ("0", "1")]})
    return data


def sync(data):
    for c in data["candidates"]:
        c["protocol"] = copy.deepcopy(data["protocol"])


@pytest.mark.parametrize("task", ["prediction", "optimization", "numerical"])
def test_task_protocols_and_within_instance_stability(tmp_path, task):
    report = compare(fixture(tmp_path, task), tmp_path)
    assert report["schema_version"] == "comparison-2"
    assert report["recommendation"] == "one"
    assert report["ranking"][0]["instances"]["large"]["error"]["std"] == 0
    assert "std" not in report["ranking"][0]


@pytest.mark.parametrize("field", ["elapsed_s", "peak_memory_mb"])
def test_unknown_cost_is_not_zero_or_complete_ranking(tmp_path, field):
    data = fixture(tmp_path)
    data["candidates"][0]["runs"][0][field] = None
    report = compare(data, tmp_path)
    assert report["selection_status"] == "partial" and report["recommendation"] is None
    key = "mean_elapsed_s" if field == "elapsed_s" else field
    assert report["ranking"][0][key] is None


def test_tradeoffs_preserve_nondominated_candidates(tmp_path):
    data = fixture(tmp_path)
    data["protocol"]["objectives"].append({"name": "utility", "direction": "max", "unit": "1"})
    sync(data)
    for c in data["candidates"]:
        for run in c["runs"]:
            run["metrics"]["utility"] = 1 if c["id"] == "one" else 2
    report = compare(data, tmp_path)
    assert set(report["pareto_front"]) == {"one", "two"}
    assert report["recommendation"] is None


def test_single_repeat_stability_unknown(tmp_path):
    data = fixture(tmp_path)
    data["protocol"]["repeats"] = ["0"]
    sync(data)
    for c in data["candidates"]:
        c["runs"] = [r for r in c["runs"] if r["repeat"] == "0"]
    report = compare(data, tmp_path)
    assert report["ranking"][0]["instances"]["small"]["error"]["std"] is None
    assert report["warnings"]


@pytest.mark.parametrize("mutation", ["final_test", "group_leak", "future", "protocol", "missing_metric",
                                      "nan", "duplicate", "stale", "negative_cost", "fake_hash"])
def test_reject_invalid(tmp_path, mutation):
    data = fixture(tmp_path, "prediction")
    if mutation == "final_test":
        data["protocol"]["evaluation_role"] = "test"
    elif mutation == "group_leak":
        data["protocol"]["split"]["validation"] = ["file1"]
    elif mutation == "future":
        data["protocol"]["split"] = {"unit": "time", "train": [3, 4], "validation": [1, 2]}
    elif mutation == "fake_hash":
        data["protocol"]["dataset_sha256"] = "fake"
    sync(data)
    run = data["candidates"][0]["runs"][0]
    if mutation == "protocol":
        data["candidates"][0]["protocol"]["task"] = "other"
    elif mutation == "missing_metric":
        run["metrics"] = {}
    elif mutation == "nan":
        run["metrics"]["error"] = float("nan")
    elif mutation == "duplicate":
        data["candidates"][0]["runs"][1] = copy.deepcopy(run)
    elif mutation == "stale":
        (tmp_path / "observations.json").write_text("changed")
    elif mutation == "negative_cost":
        run["elapsed_s"] = -1
    with pytest.raises(ValueError):
        compare(data, tmp_path)


@pytest.mark.parametrize("change", ["infeasible", "over_budget"])
def test_excluded_not_ranked(tmp_path, change):
    data = fixture(tmp_path)
    data["candidates"][0]["runs"][0].update({"feasible": False} if change == "infeasible" else {"elapsed_s": 20})
    report = compare(data, tmp_path)
    assert report["excluded"][0]["id"] == "one"
    assert [r["id"] for r in report["ranking"]] == ["two"]


@pytest.mark.parametrize("unit", ["group", "time"])
def test_ordered_time_and_independent_groups_are_accepted(tmp_path, unit):
    data = fixture(tmp_path, "prediction")
    data["protocol"]["split"] = {"unit": unit, "train": [1, 2], "validation": [3, 4]}
    sync(data)
    assert compare(data, tmp_path)["recommendation"] == "one"
