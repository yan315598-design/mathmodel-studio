"""Release review regressions: scientific claims and conservative composition."""
import copy
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "templates/figures/scripts")]
from figure_composition import paper_style, shared_colorbar, shared_legend
from figure_export_quality import original_quality
from build_result_gallery import build
from inspect_assets import sha256
from test_figure_upgrade import manifest_for
from test_experiment_v2 import fixture, sync
from compare_experiments import compare
from package_dist import _insert_banner


@pytest.mark.parametrize("text", ["# Body\n", "---\nname: example\n---\n\n# Body\n"])
def test_distribution_banner_is_idempotent(text):
    banner = "> Distribution boundary.\n\n"
    first = _insert_banner(text, banner)
    assert first.count(banner.strip()) == 1
    assert _insert_banner(first, banner) == first
    assert (first.startswith("---")) == text.startswith("---")


def test_preserve_locked_math_policy():
    with matplotlib.rc_context({"mathtext.default": "regular"}):
        with paper_style():
            assert matplotlib.rcParams["mathtext.default"] == "regular"


@pytest.mark.parametrize("norm", ["power", "boundary"])
def test_shared_colorbar_rejects_different_internal_mapping(norm):
    fig, axes = plt.subplots(1, 2)
    if norm == "power":
        norms = [matplotlib.colors.PowerNorm(g, vmin=0, vmax=1) for g in (.5, 2)]
    else:
        norms = [matplotlib.colors.BoundaryNorm(b, 256) for b in ([0,.2,1],[0,.8,1])]
    images = [ax.imshow([[0,1]], norm=n) for ax,n in zip(axes,norms)]
    try:
        with pytest.raises(ValueError, match="normalization"):
            shared_colorbar(fig, images, axes, label="Value")
    finally:
        plt.close(fig)


def test_shared_legend_accepts_location_override():
    fig, ax = plt.subplots()
    ax.plot([1,2], label="model")
    try:
        assert shared_legend(fig, [ax], loc="upper center", ncols=1)
    finally:
        plt.close(fig)


def test_every_mask_original_must_pass(tmp_path):
    good, bad = tmp_path / "good.png", tmp_path / "bad.png"
    Image.new("L", (16,12), 0).save(good)
    Image.new("L", (16,12), 7).save(bad)
    path = manifest_for(tmp_path, good)
    data = json.loads(path.read_text())
    data["schema_version"] = "figure-candidates-2"
    item = data["figures"][0]
    item.update(status="reviewed", object="mask", destination="answer_attachment",
                native={"size":[16,12], "mode":"L", "values":[0,255]})
    item["originals"].append({"path":bad.name,"sha256":sha256(bad)})
    path.write_text(json.dumps(data))
    assert build(path, tmp_path / "gallery")["included"][0]["delivery_status"] == "not_verified"


@pytest.mark.parametrize("split", [
    {"unit":"time", "train":[float("nan")], "validation":[1]},
    {"unit":"time", "train":["2025-2-01"], "validation":["2025-10-01"]},
    {"unit":"group", "train":"file1", "validation":"file2"},
])
def test_malformed_split_rejected(tmp_path, split):
    data = fixture(tmp_path, "prediction")
    data["protocol"]["split"] = split
    sync(data)
    with pytest.raises(ValueError):
        compare(data, tmp_path)


@pytest.mark.parametrize("content", [
    '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><rect width="10" height="10"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><use href="https://example.com/a.svg#x"/><rect width="10" height="10"/></svg>',
])
def test_active_or_remote_svg_rejected(tmp_path, content):
    path = tmp_path / "active.svg"
    path.write_text(content)
    with pytest.raises(ValueError):
        original_quality(path, 90)
