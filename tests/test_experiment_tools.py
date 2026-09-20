"""Behavioral checks for asset metadata, comparable experiments and candidate galleries."""

import copy
import json
import sys
import wave
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inspect_assets import inspect, extract_frame, sha256
from compare_experiments import compare
from build_result_gallery import build


def test_wav_metadata(tmp_path):
    path = tmp_path / "tone.wav"
    with wave.open(str(path), "wb") as stream:
        stream.setparams((2, 2, 8000, 0, "NONE", "not compressed"))
        stream.writeframes(b"\0" * 32000)
    record = inspect(path)
    assert record["status"] == "inspected"
    assert record["metadata"]["duration_s"] == 1
    assert record["metadata"]["channels"] == 2
    assert record["sha256"] == sha256(path)


@pytest.mark.parametrize("name,content,status", [
    ("bad.wav", b"broken", "error"),
    ("cloud.pcd", b"header", "unsupported_reader"),
    ("data.csv", b"a,b\n1,2\n3\n", "inspected"),
])
def test_asset_status(tmp_path, name, content, status):
    path = tmp_path / name
    path.write_bytes(content)
    record = inspect(path)
    assert record["status"] == status
    if name.endswith(".csv"):
        assert record["metadata"]["sample_width_consistent"] is False


def test_missing_media_dependency(tmp_path, monkeypatch):
    monkeypatch.setattr("inspect_assets.shutil.which", lambda _: None)
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"x")
    assert inspect(path)["status"] == "missing_dependency"


def test_frame_bounds(tmp_path):
    with pytest.raises(ValueError):
        extract_frame(tmp_path / "x", -1, tmp_path / "out.png")


def experiments(tmp_path):
    evidence = tmp_path / "metrics.json"
    evidence.write_text('{"measured": true}', encoding="utf-8")
    protocol = {"task": "regression", "dataset_sha256": "a" * 64, "split_id": "b" * 64,
                "metric": "rmse", "direction": "min", "evaluation_role": "validation",
                "budget_s": 10, "practical_tolerance": 0.05, "replicates": ["fold0", "fold1"]}
    candidates = []
    for name, values in [("baseline", [1, 1]), ("complex", [0.8, 1.16])]:
        candidates.append({"id": name, "status": "completed", "protocol": copy.deepcopy(protocol),
                           "interpretability": "linear coefficients" if name == "baseline" else "feature analysis",
                           "runs": [{"replicate": fold, "value": value, "elapsed_s": 2,
                                     "peak_memory_mb": 20, "feasible": True,
                                     "evidence": {"path": evidence.name, "sha256": sha256(evidence)}}
                                    for fold, value in zip(protocol["replicates"], values)]})
    return {"schema_version": "experiments-1", "protocol": protocol, "candidates": candidates}


def test_comparison_prefers_stability_within_tolerance(tmp_path):
    report = compare(experiments(tmp_path), tmp_path)
    assert report["ranking"][0]["id"] == "complex"
    assert report["recommendation"] == "baseline"
    assert report["selection_status"] == "provisional"


@pytest.mark.parametrize("mutation", ["test", "protocol", "nan", "duplicate", "infeasible", "stale", "fake_hash"])
def test_invalid_experiments_rejected(tmp_path, mutation):
    data = experiments(tmp_path)
    candidate = data["candidates"][0]
    if mutation == "test":
        data["protocol"]["evaluation_role"] = "test"
    elif mutation == "protocol":
        candidate["protocol"]["split_id"] = "other"
    elif mutation == "nan":
        candidate["runs"][0]["value"] = float("nan")
    elif mutation == "duplicate":
        candidate["runs"][1]["replicate"] = "fold0"
    elif mutation == "infeasible":
        candidate["runs"][0]["feasible"] = False
    elif mutation == "fake_hash":
        data["protocol"]["dataset_sha256"] = "not-a-hash"
    else:
        (tmp_path / "metrics.json").write_text("changed")
    with pytest.raises(ValueError):
        compare(data, tmp_path)


def test_timed_out_candidate_is_retained_as_excluded(tmp_path):
    data = experiments(tmp_path)
    data["candidates"][0]["runs"][0]["elapsed_s"] = 11
    report = compare(data, tmp_path)
    assert report["excluded"][0]["id"] == "baseline"
    assert report["recommendation"] == "complex"


def gallery_manifest(tmp_path):
    source = tmp_path / "result.json"
    source.write_text('{"value": 42}', encoding="utf-8")
    image = tmp_path / "plot.png"
    Image.new("RGB", (1200, 600), "#167e69").save(image)
    artifact = {"path": image.name, "sha256": sha256(image)}
    item = {"figure_id": "Q1_F1", "question": "Q1", "claim": "<script>not executable</script>",
            "caption": "measured result", "status": "candidate", "qa": "passed", "width_mm": 90,
            "parameters": {}, "source": {"path": source.name, "sha256": sha256(source)},
            "preview": artifact, "originals": [artifact]}
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps({"schema_version": "figure-candidates-1", "figures": [item]}), encoding="utf-8")
    return path


def test_gallery_builds_portable_files_and_escapes_text(tmp_path):
    manifest = gallery_manifest(tmp_path)
    output = tmp_path / "gallery"
    report = build(manifest, output)
    page = (output / "index.html").read_text(encoding="utf-8")
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert (output / "thumb_0.png").is_file()
    assert (output / "original_0_0.png").is_file()
    assert report["promotion"] == "none"
    with pytest.raises(ValueError):
        build(manifest, output)


@pytest.mark.parametrize("change", ["diagnostic", "failed", "low_dpi"])
def test_gallery_excludes_unqualified_figures(tmp_path, change):
    manifest = gallery_manifest(tmp_path)
    data = json.loads(manifest.read_text())
    item = data["figures"][0]
    if change == "diagnostic":
        item["status"] = "diagnostic"
    elif change == "failed":
        item["qa"] = "failed"
    else:
        item["width_mm"] = 500
    manifest.write_text(json.dumps(data))
    report = build(manifest, tmp_path / "gallery")
    assert len(report["included"]) == 0
    assert len(report["skipped"]) == 1


def test_gallery_rejects_stale_source_before_writing(tmp_path):
    manifest = gallery_manifest(tmp_path)
    (tmp_path / "result.json").write_text("changed")
    output = tmp_path / "gallery"
    with pytest.raises(ValueError):
        build(manifest, output)
    assert not output.exists()


def test_scientific_headers(tmp_path):
    import numpy as np
    import h5py
    from scipy.io import savemat

    array = np.zeros((3, 4))
    np.save(tmp_path / "array.npy", array)
    with h5py.File(tmp_path / "array.h5", "w") as store:
        store["signal"] = array
    savemat(tmp_path / "array.mat", {"signal": array})
    for name in ("array.npy", "array.h5", "array.mat"):
        assert inspect(tmp_path / name)["status"] == "inspected"
