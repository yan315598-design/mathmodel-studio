"""Real rendering regressions for missing observations and export quality."""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "templates/figures/scripts"))
from build_result_gallery import build
from inspect_assets import sha256
from templates import make_prediction_fit as prediction


def test_prediction_internal_gap_is_not_connected(tmp_path):
    # Inspect the actual SVG path as well as rendering all three real exports.
    result = prediction.plot_prediction(
        [1., 2., 3., 4., 5.], [1., 2., None, 4., 5.],
        out_stem=str(tmp_path / "gap"), pred_label="PRED_GAP")
    import xml.etree.ElementTree as ET
    tree = ET.parse(result[1])
    paths = [e.attrib.get("d", "") for e in tree.iter()
             if e.tag.endswith("}path") and "stroke-dasharray" in e.attrib.get("style", "")]
    assert any(path.count("M ") == 2 for path in paths), paths
    assert result[0].with_suffix(".pdf").is_file()


def manifest_for(tmp_path, original, preview_size=(120, 60)):
    source = tmp_path / "result.json"
    source.write_text('{"synthetic": true}', encoding="utf-8")
    preview = tmp_path / "preview.png"
    Image.new("RGB", preview_size, "white").save(preview)
    def artifact(path):
        return {"path": path.name, "sha256": sha256(path)}
    item = {"figure_id": "F1", "question": "Q1", "claim": "synthetic",
            "caption": "Example", "parameters": {}, "status": "candidate",
            "qa": "passed", "width_mm": 90, "source": artifact(source),
            "preview": artifact(preview), "originals": [artifact(original)]}
    manifest = tmp_path / "candidates.json"
    manifest.write_text(json.dumps({"schema_version": "figure-candidates-1", "figures": [item]}))
    return manifest


def test_vector_original_allows_small_preview(tmp_path):
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    original = tmp_path / "original.svg"
    fig.savefig(original)
    plt.close(fig)
    report = build(manifest_for(tmp_path, original), tmp_path / "gallery")
    assert len(report["included"]) == 1


def test_high_resolution_preview_cannot_hide_low_original(tmp_path):
    original = tmp_path / "original.png"
    Image.new("RGB", (120, 60)).save(original)
    report = build(manifest_for(tmp_path, original, (1600, 800)), tmp_path / "gallery")
    assert not report["included"]
    assert "original" in report["skipped"][0]["reason"]


def test_svg_suffix_is_not_proof_of_vector_quality(tmp_path):
    original = tmp_path / "original.svg"
    original.write_text('<svg xmlns="http://www.w3.org/2000/svg"><image width="10" height="10"/></svg>')
    report = build(manifest_for(tmp_path, original, (1600, 800)), tmp_path / "gallery")
    assert not report["included"]


def test_composition_local_style_and_external_axes(tmp_path):
    from figure_composition import paper_style, compose, shared_colorbar, shared_legend, export_revision
    from templates.make_field_contour import draw_field
    before = dict(matplotlib.rcParams)
    with paper_style():
        fig, axes = compose([["a", "b"]], width_mm=180, height_mm=80)
        x, y = np.meshgrid(np.arange(4), np.arange(3))
        values = np.arange(12, dtype=float).reshape(3, 4)
        values[0, 0] = np.nan
        maps = [draw_field(ax, x, y, values, vmin=0, vmax=12) for ax in axes.values()]
        assert np.ma.getmaskarray(maps[0].get_array()).sum() == 1
        assert maps[0].axes is axes["a"]
        assert shared_colorbar(fig, maps, axes.values(), label="Speed (m/s)").ax.figure is fig
        for ax in axes.values():
            ax.plot([0, 1], [0, 1], label="Same")
        assert len(shared_legend(fig, axes.values()).get_texts()) == 1
        report = export_revision(fig, tmp_path / "revision")
        with Image.open(tmp_path / "revision/figure.png") as image:
            assert abs(image.width - 180/25.4*300) < 2
        assert report["status"] == "complete"
        assert plt.fignum_exists(fig.number)
        with pytest.raises(FileExistsError):
            export_revision(fig, tmp_path / "revision")
        maps[1].set_clim(0, 20)
        with pytest.raises(ValueError, match="normalization"):
            shared_colorbar(fig, maps, axes.values(), label="Speed")
        with pytest.raises(ValueError):
            draw_field(axes["a"], x, y, np.full_like(values, np.inf))
        plt.close(fig)
    assert dict(matplotlib.rcParams) == before


def test_revision_failure_is_explicit_and_preserves_figure(tmp_path):
    from figure_composition import export_revision
    fig, ax = plt.subplots()
    ax.text(.5, .5, "$\\unknowncommand$")
    with pytest.raises(ValueError):
        export_revision(fig, tmp_path / "bad")
    assert (tmp_path / "bad/INCOMPLETE.json").is_file()
    assert not (tmp_path / "bad/manifest.json").exists()
    assert plt.fignum_exists(fig.number)
    plt.close(fig)


@pytest.mark.parametrize("key", list("ABCDEF"))
def test_task_examples_scientific_invariants(tmp_path, key):
    from render_task_examples import BUILDERS
    from figure_composition import paper_style
    with paper_style():
        fig, axes, arrays, facts = BUILDERS[key](np.random.default_rng(20260920+ord(key)), tmp_path)
        fig.canvas.draw()
        assert fig.get_figwidth()*25.4 == pytest.approx(180)
        assert len(axes) >= 2
        if key == "A":
            assert facts["cases"] == 6 and facts["feasible"]
            assert np.all(arrays["start_ms"][:, 1:] >= arrays["start_ms"][:, :-1] + arrays["duration_ms"][:, :-1])
        elif key == "B":
            assert np.iscomplexobj(arrays["channel"])
            assert np.all(arrays["sinr_linear"] >= 0)
            assert facts["valid_accuracy"] is None
            assert facts["rmse"] == pytest.approx(np.sqrt(np.mean((arrays["labels"]-arrays["prediction"])**2)))
        elif key == "C":
            with Image.open(tmp_path / "answer_mask.png") as mask:
                assert mask.size == (160, 96) and mask.mode == "L"
                np.testing.assert_array_equal(np.asarray(mask), arrays["mask"])
        elif key == "D":
            assert np.array_equal(np.isnan(arrays["t0"]), ~arrays["support"])
            assert facts["crs"] and len(facts["times"]) == 2
        elif key == "E":
            assert facts["target_accuracy"] is None and facts["group_id"]
            assert arrays["frequency_hz"][np.argmax(arrays["psd"])] == pytest.approx(240, abs=4)
        else:
            assert len(facts["objects"]) == 10 and facts["external_validation"] is None
            np.testing.assert_allclose(arrays["score"], arrays["components"] @ arrays["weights"])
        plt.close(fig)


def test_v2_diagnostic_is_visible_but_not_promoted(tmp_path):
    original = tmp_path / "original.png"
    Image.new("RGB", (120, 60)).save(original)
    manifest = manifest_for(tmp_path, original)
    data = json.loads(manifest.read_text())
    data["schema_version"] = "figure-candidates-2"
    data["figures"][0].update(status="diagnostic", qa="unknown", destination="exploration")
    manifest.write_text(json.dumps(data))
    report = build(manifest, tmp_path / "gallery")
    assert report["schema_version"] == "gallery-2"
    assert report["included"][0]["status"] == "diagnostic"
    assert report["included"][0]["delivery_status"] == "not_verified"
    assert report["promotion"] == "none"


@pytest.mark.parametrize("invalid", [False, True])
def test_v2_native_mask_checks_encoding_not_print_dpi(tmp_path, invalid):
    original = tmp_path / "mask.png"
    values = np.zeros((12, 16), dtype=np.uint8)
    values[3:6] = 255
    Image.fromarray(values).save(original)
    before = sha256(original)
    manifest = manifest_for(tmp_path, original)
    data = json.loads(manifest.read_text())
    data["schema_version"] = "figure-candidates-2"
    data["figures"][0].update(status="reviewed", destination="answer_attachment", object="mask",
                              native={"size": [16, 12], "mode": "L", "values": [0, 1] if invalid else [0, 255]})
    manifest.write_text(json.dumps(data))
    result = build(manifest, tmp_path / "gallery")["included"][0]
    assert result["delivery_status"] == ("not_verified" if invalid else "reviewed_candidate")
    assert sha256(original) == before


def test_v2_stale_and_rejected_keep_reasons(tmp_path):
    import copy
    original = tmp_path / "original.png"
    Image.new("RGB", (1200, 600)).save(original)
    manifest = manifest_for(tmp_path, original)
    data = json.loads(manifest.read_text())
    data["schema_version"] = "figure-candidates-2"
    rejected = copy.deepcopy(data["figures"][0])
    rejected.update(figure_id="F2", status="rejected", reason="duplicates existing result")
    data["figures"].append(rejected)
    manifest.write_text(json.dumps(data))
    (tmp_path / "result.json").write_text("changed")
    report = build(manifest, tmp_path / "gallery")
    assert not report["included"]
    assert "stale" in report["skipped"][0]["reason"]
    assert report["skipped"][1]["reason"] == "duplicates existing result"
    assert all(item["source"] for item in report["skipped"])


def test_invalid_svg_is_rejected(tmp_path):
    original = tmp_path / "broken.svg"
    original.write_text("not xml")
    with pytest.raises(ValueError, match="invalid SVG"):
        build(manifest_for(tmp_path, original), tmp_path / "gallery")
    assert not (tmp_path / "gallery").exists()


def test_gallery_budget_does_not_silently_drop_required_figures(tmp_path):
    import copy
    original = tmp_path / "original.png"
    Image.new("RGB", (1200, 600)).save(original)
    manifest = manifest_for(tmp_path, original)
    data = json.loads(manifest.read_text())
    data.update(schema_version="figure-candidates-2", max_items=1)
    second = copy.deepcopy(data["figures"][0])
    second.update(figure_id="F2", required=True)
    data["figures"].append(second)
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="budget exceeded"):
        build(manifest, tmp_path / "gallery")
    assert not (tmp_path / "gallery").exists()


def test_axis_prediction_does_not_mutate_style_or_close():
    before = dict(matplotlib.rcParams)
    fig, ax = plt.subplots()
    line = prediction.draw_prediction_series(ax, [0, 1, 2], [1, None, 3])
    assert np.isnan(line.get_ydata()[1])
    assert plt.fignum_exists(fig.number)
    with pytest.raises(ValueError):
        prediction.draw_prediction_series(ax, [0, 1], [1, float("inf")])
    assert dict(matplotlib.rcParams) == before
    plt.close(fig)


@pytest.mark.parametrize("width,passed", [(2125, True), (2124, False)])
def test_original_resolution_allows_only_fractional_pixel_rounding(tmp_path, width, passed):
    from figure_export_quality import original_quality
    path = tmp_path / "canvas.png"
    Image.new("RGB", (width, 400)).save(path)
    assert (original_quality(path, 180)["status"] == "passed") is passed
