"""Opt-in axes composition at manuscript dimensions; legacy exports stay untouched."""

from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from figkit import apply_style


@contextmanager
def paper_style():
    with mpl.rc_context():
        apply_style(upright_math=None)
        mpl.rcParams.update({"font.size": 9, "axes.labelsize": 9,
                             "axes.titlesize": 10, "xtick.labelsize": 8,
                             "ytick.labelsize": 8, "legend.fontsize": 8,
                             "axes.grid": False})
        yield


def compose(mosaic, *, width_mm=180, height_mm=115, **kwargs):
    if any(isinstance(v, bool) or not math.isfinite(v) or v <= 0
           for v in (width_mm, height_mm)):
        raise ValueError("physical dimensions must be positive finite millimetres")
    return plt.subplot_mosaic(mosaic, figsize=(width_mm / 25.4, height_mm / 25.4),
                              layout="constrained", **kwargs)


def shared_legend(fig, axes, **kwargs):
    unique = {}
    for ax in axes:
        handles, labels = ax.get_legend_handles_labels()
        for handle, label in zip(handles, labels):
            unique.setdefault(label, handle)
    kwargs.setdefault("loc", "outside lower center")
    kwargs.setdefault("ncols", max(1, len(unique)))
    return fig.legend(unique.values(), unique.keys(), **kwargs)


def shared_colorbar(fig, mappables, axes, *, label, **kwargs):
    maps = list(mappables)
    if not maps:
        raise ValueError("at least one mappable required")
    import numpy as np
    first = maps[0]
    for m in maps[1:]:
        # Custom/nonlinear norms may hide parameters: require one shared instance.
        same_norm = m.norm is first.norm or (
            type(m.norm) is type(first.norm) is mpl.colors.Normalize
            and (m.norm.vmin, m.norm.vmax, m.norm.clip) ==
                (first.norm.vmin, first.norm.vmax, first.norm.clip))
        same_cmap = m.cmap is first.cmap or (
            m.cmap.N == first.cmap.N and
            np.array_equal(m.cmap(np.arange(-1, m.cmap.N+1)),
                           first.cmap(np.arange(-1, first.cmap.N+1))) and
            np.array_equal(m.cmap.get_bad(), first.cmap.get_bad()))
        if not same_norm or not same_cmap:
            raise ValueError("shared colorbar requires identical normalization and colormap")
    return fig.colorbar(maps[0], ax=list(axes), label=label, **kwargs)


def panel_labels(axes):
    return [ax.set_title(f"({chr(97 + i)})", loc="left", fontweight="bold")
            for i, ax in enumerate(axes)]


def export_revision(fig, directory, *, metadata=None):
    """Reserve a new directory; completion manifest appears only after all exports.

    A failed revision retains an explicit incomplete marker for diagnosis, never
    overwrites a prior revision, and never closes the caller's Figure.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    marker = directory / "INCOMPLETE.json"
    marker.write_text(json.dumps({"status": "incomplete"}), encoding="utf-8")
    files = []
    with mpl.rc_context({"savefig.bbox": None}):
        for ext in ("png", "svg", "pdf"):
            path = directory / f"figure.{ext}"
            fig.savefig(path, dpi=300, bbox_inches=None)
            files.append({"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    record = {"schema_version": "figure-export-1", "status": "complete",
              "width_mm": float(fig.get_figwidth() * 25.4),
              "height_mm": float(fig.get_figheight() * 25.4), "files": files,
              "metadata": metadata or {}, "visual_review": "pending"}
    (directory / "manifest.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    marker.unlink()
    return record
