"""Axes-relative reference lines must be checked at their rendered coordinates."""

import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from figqa import analyze_figure, KIND_LINE_THROUGH_TEXT


@pytest.mark.parametrize("reference", ["horizontal", "vertical"])
def test_reference_line_transform_clear_and_actual_collision(reference):
    fig, ax = plt.subplots()
    ax.set(xlim=(10, 20), ylim=(10, 20))
    if reference == "horizontal":
        ax.axhline(15, label="reference")
        point = (.5, .5)
    else:
        ax.axvline(15, label="reference")
        point = (.5, .5)
    clear_point = (.5, .8) if reference == "horizontal" else (.8, .5)
    ax.text(*clear_point, "clear", transform=ax.transAxes)
    assert not [c for c in analyze_figure(fig, "clear") if c.kind == KIND_LINE_THROUGH_TEXT]
    ax.text(*point, "actual collision", transform=ax.transAxes, ha="center", va="center")
    assert [c for c in analyze_figure(fig, "collision") if c.kind == KIND_LINE_THROUGH_TEXT]
    plt.close(fig)
