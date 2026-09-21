"""Evidence path checks preserve labels while checking structured artifacts."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import json

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "trace_claims.py"
spec = importlib.util.spec_from_file_location("trace_claims_paths", SCRIPT)
tracer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tracer)


def row(**updates):
    value = dict(question="任务", model="模型", result="召回率/精确率均提高",
                 validation="train/test 隔离已核对", figure=["F1"], abstract_claim="主张")
    value.update(updates)
    return value


def test_prose_slashes_and_figure_ids_remain_compatible():
    assert tracer.trace_claims([row()])["abstract_ready"]


def test_missing_artifact_string_blocks(tmp_path):
    result = tracer.trace_claims([row(result=str(tmp_path / "missing.json"))])
    assert not result["abstract_ready"]


def test_missing_artifact_in_list_blocks(tmp_path):
    result = tracer.trace_claims([row(figure=["F1", str(tmp_path / "missing.png")])])
    assert not result["abstract_ready"]


def test_explicit_extensionless_path_blocks(tmp_path):
    result = tracer.trace_claims([row(validation={"path": str(tmp_path / "missing")})])
    assert not result["abstract_ready"]


def test_nested_structured_path_blocks(tmp_path):
    value = {"artifacts": [{"file_path": str(tmp_path / "missing.csv"), "label": "结果"}]}
    assert not tracer.trace_claims([row(result=value)])["abstract_ready"]


def test_existing_paths_and_labels_pass(tmp_path):
    artifact = tmp_path / "证据 with spaces.json"
    artifact.write_text("{}", encoding="utf-8")
    value = row(result={"path": str(artifact), "description": "召回率/精确率"},
                validation=[str(artifact)], figure=["F1"])
    assert tracer.trace_claims([value])["abstract_ready"]


def test_remote_url_not_treated_as_local_path():
    assert not tracer.missing_path("https://example.org/results.json")


def test_strict_cli_rejects_nested_missing_paths(tmp_path):
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps([row(figure=[{"path": str(tmp_path / "missing.svg")}])]), encoding="utf-8")
    process = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), "--input", str(ledger), "--strict"],
                             capture_output=True, text=True, encoding="utf-8")
    assert process.returncode == 2
    assert json.loads(process.stdout)["abstract_gate"] == "block_untraced_claims"


def test_directory_does_not_substitute_for_evidence_file(tmp_path):
    directory = tmp_path / "result.json"
    directory.mkdir()
    assert not tracer.trace_claims([row(result=str(directory))])["abstract_ready"]


def test_empty_explicit_path_is_not_evidence():
    assert not tracer.trace_claims([row(result={"path": ""})])["abstract_ready"]
