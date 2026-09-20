"""Generate synthetic A-F examples. No contest data or claimed benchmark results."""

import argparse
import json
import hashlib
import html
import os
import time
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from scipy.special import logsumexp
from PIL import Image

from figure_composition import compose, paper_style, panel_labels, shared_colorbar, export_revision
from templates.make_field_contour import draw_field, plot_field_contour

VENDOR = Path(__file__).resolve().parents[1] / "vendor/icarus-figures"
sys.path.insert(0, str(VENDOR))
from paperfig import spectrum, network_graph

BLUE, GREEN, RED = "#0072B2", "#009E73", "#D55E00"


def scheduling(rng, folder):
    # Six independent serial schedules: dependencies are generated as chains.
    duration = rng.integers(2, 7, (6, 5))
    memory = rng.integers(10, 55, (6, 5))
    start = np.c_[np.zeros(6), np.cumsum(duration, axis=1)[:, :-1]]
    fig, axes = compose([["timeline", "memory"], ["timeline", "summary"]], height_mm=125,
                        width_ratios=[1.35, 1])
    for i in range(6):
        axes["timeline"].barh(np.full(5, i), duration[i], left=start[i], height=.65,
                              color=plt.cm.viridis(np.linspace(.2, .85, 5)), edgecolor="white")
    axes["timeline"].set(yticks=range(6), yticklabels=[f"Case {i+1}" for i in range(6)], xlabel="Time (ms)")
    for i in (0, 5):
        axes["memory"].step(np.r_[start[i], duration[i].sum()], np.r_[memory[i], 0],
                             where="post", label=f"Case {i+1}")
    axes["memory"].set(xlabel="Time (ms)", ylabel="Live memory (MiB)")
    axes["memory"].legend()
    axes["summary"].scatter(duration.sum(1), memory.max(1), color=GREEN)
    for i in range(6):
        axes["summary"].annotate(str(i+1), (duration[i].sum(), memory[i].max()), xytext=(4, 3), textcoords="offset points")
    axes["summary"].set(xlabel="Makespan (ms)", ylabel="Peak memory (MiB)")
    return fig, axes, dict(duration_ms=duration, memory_mib=memory, start_ms=start), {
        "cases": 6, "feasible": bool(np.all(start[:, 1:] >= start[:, :-1] + duration[:, :-1])),
        "dependency": "serial chain; one resource; each task releases memory at completion",
        "coordinate": "physical time, not scheduler step"}


def communication(rng, folder):
    channel = (rng.normal(size=(48, 24)) + 1j*rng.normal(size=(48, 24))) / np.sqrt(2)
    sinr = np.abs(channel)**2 / .15
    beta = 2.
    effective = -beta * (logsumexp(-sinr/beta, axis=1) - np.log(sinr.shape[1]))
    prediction = np.log2(1 + effective)
    labels = prediction + rng.normal(0, .07, len(prediction))
    residual = labels - prediction
    fig, axes = compose([["matrix", "calibration"], ["matrix", "residual"]], height_mm=125)
    im = axes["matrix"].imshow(10*np.log10(sinr), aspect="auto", cmap="viridis")
    fig.colorbar(im, ax=axes["matrix"], label="SINR (dB)", shrink=.7)
    axes["matrix"].set(xlabel="Subcarrier index", ylabel="Labeled sample index")
    axes["calibration"].scatter(prediction, labels, s=13, color=BLUE, alpha=.75)
    bounds = [min(labels.min(), prediction.min()), max(labels.max(), prediction.max())]
    axes["calibration"].plot(bounds, bounds, ":", color=".4")
    axes["calibration"].set(xlabel="EESM proxy (bit/s/Hz)", ylabel="Synthetic label (bit/s/Hz)")
    axes["residual"].scatter(prediction, residual, s=13, color=GREEN)
    axes["residual"].axhline(0, color=".4", ls=":")
    axes["residual"].set(xlabel="EESM proxy (bit/s/Hz)", ylabel="Residual (bit/s/Hz)")
    return fig, axes, dict(channel=channel, sinr_linear=sinr, prediction=prediction, labels=labels), {
        "beta_linear": beta, "rmse": float(np.sqrt(np.mean(residual**2))),
        "eesm_domain": "linear SINR", "label_unit": "bit/s/Hz; not an MCS index",
        "valid_labels": False, "valid_accuracy": None}


def reconstruction(rng, folder):
    y, x = np.mgrid[:96, :160]
    center = 45 + 10*np.sin(x/20)
    mask = (np.abs(y-center) < 2).astype(np.uint8)*255
    image = np.clip(.7 + .1*rng.normal(size=x.shape) - .5*(mask > 0), 0, 1)
    Image.fromarray(mask).save(folder / "answer_mask.png")
    fitted = np.polyval(np.polyfit(np.arange(160), center[0], 5), np.arange(160))
    fig, axes = compose([["image", "mask"], ["fit", "residual"]], height_mm=115)
    for key, data in (("image", image), ("mask", mask)):
        axes[key].imshow(data, cmap="gray", vmin=0, vmax=1 if key == "image" else 255,
                          interpolation="nearest")
        axes[key].set(xlabel="Column (px)", ylabel="Row (px)")
    axes["fit"].plot(np.arange(160)*.1, center[0]*.1, color=BLUE, label="Synthetic center")
    axes["fit"].plot(np.arange(160)*.1, fitted*.1, "--", color=RED, label="Polynomial fit")
    axes["fit"].set(xlabel="x (mm)", ylabel="y (mm)")
    axes["fit"].legend(fontsize=7)
    axes["residual"].plot(np.arange(160)*.1, (center[0]-fitted)*.1, color=GREEN)
    axes["residual"].axhline(0, color=".4", ls=":")
    axes["residual"].set(xlabel="x (mm)", ylabel="Residual (mm)")
    return fig, axes, dict(image=image, mask=mask, center_px=center[0], fitted_px=fitted), {
        "mask_shape": list(mask.shape), "mask_encoding": "uint8: 0,255", "pixel_size_mm": .1,
        "fit_rmse_mm": float(np.sqrt(np.mean((center[0]-fitted)**2))*.1),
        "connectivity": "not inferred; synthetic reference, not field truth"}


def field(rng, folder):
    x, y = np.meshgrid(np.linspace(0, 1000, 45), np.linspace(0, 600, 30))
    z = 3 + 2*np.exp(-((x-500)**2+(y-300)**2)/80000)
    missing = (x < 140) & (y > 400)
    observed = z.copy()
    observed[missing] = np.nan
    later = observed + .3*np.sin(x/150)
    fig, axes = compose([["t0", "t1"], ["profile", "profile"]], height_mm=130,
                        height_ratios=[1.5, 1])
    maps = [draw_field(axes[key], x, y, values, vmin=2.5, vmax=5.4)
            for key, values in (("t0", observed), ("t1", later))]
    for key in ("t0", "t1"):
        axes[key].set(xlabel="Local east (m)", ylabel="Local north (m)", aspect="equal")
    shared_colorbar(fig, maps, [axes["t0"], axes["t1"]], label="Speed (m/s)", shrink=.8)
    for values, label in ((observed, "00:00 UTC"), (later, "00:10 UTC")):
        axes["profile"].plot(x[15], values[15], label=label)
    axes["profile"].set(xlabel="Local east (m), north = 310 m", ylabel="Speed (m/s)")
    axes["profile"].legend()
    return fig, axes, dict(x=x, y=y, t0=observed, t1=later, support=~missing), {
        "crs": "synthetic local Cartesian metres; no EPSG assignment", "height_m": 100,
        "times": ["2026-01-01T00:00:00Z", "2026-01-01T00:10:00Z"],
        "grid_spacing_m": [float(x[0,1]-x[0,0]), float(y[1,0]-y[0,0])],
        "observation_resolution": "not applicable: analytic synthetic field"}


def diagnosis(rng, folder):
    fs = 2048
    t = np.arange(fs*2)/fs
    wave = (1+.45*np.sin(2*np.pi*25*t))*np.sin(2*np.pi*240*t) + .15*rng.normal(size=len(t))
    freq, psd = signal.welch(wave, fs, window="hann", nperseg=512, noverlap=256)
    ff, tt, zz = signal.stft(wave, fs, window="hann", nperseg=256, noverlap=192)
    fig, axes = compose([["wave", "wave"], ["spectrum", "stft"]], height_mm=120)
    axes["wave"].plot(t[:512], wave[:512], color=BLUE, lw=.8)
    axes["wave"].set(xlabel="Time (s)", ylabel="Amplitude (a.u.)")
    spectrum(freq, psd, xlabel="Frequency (Hz)", ylabel="PSD (a.u.^2/Hz)", fill=False, ax=axes["spectrum"])
    axes["spectrum"].axvline(240, ls=":", color=RED, label="Carrier 240 Hz")
    axes["spectrum"].set(xlim=(0, 500))
    axes["spectrum"].legend(fontsize=7)
    im = axes["stft"].pcolormesh(tt, ff, 20*np.log10(np.maximum(abs(zz), 1e-8)), cmap="magma", shading="auto", rasterized=True)
    axes["stft"].set(xlabel="Time (s)", ylabel="Frequency (Hz)", ylim=(0, 500))
    fig.colorbar(im, ax=axes["stft"], label="Amplitude (dB re 1 a.u.)")
    return fig, axes, dict(time_s=t, signal=wave, frequency_hz=freq, psd=psd), {
        "sample_rate_hz": fs, "welch_window": "hann", "welch_nperseg": 512,
        "stft_nperseg": 256, "stft_noverlap": 192, "rpm": None,
        "group_id": "synthetic_original_file_01", "target_labels": False, "target_accuracy": None}


def spatial(rng, folder):
    names = [f"Garden {i+1:02}" for i in range(10)]
    components = rng.uniform(.2, 1, (10, 3))
    weights = np.array([.4, .35, .25])
    score = components @ weights
    perturb = rng.dirichlet(weights*100, size=200)
    scores = components @ perturb.T
    low, high = np.quantile(scores, [.05, .95], axis=1)
    route = np.cumsum(rng.normal(size=(60, 2)), axis=0)*5
    distance = np.r_[0, np.cumsum(np.linalg.norm(np.diff(route, axis=0), axis=1))]
    fig, axes = compose([["route", "scores"], ["profile", "scores"]], height_mm=140,
                        width_ratios=[1, 1.25])
    axes["route"].plot(*route.T, color=BLUE)
    axes["route"].scatter(*route[[0,-1]].T, c=[GREEN, RED], s=25)
    axes["route"].set(xlabel="Local x (m)", ylabel="Local y (m)", aspect="equal")
    axes["profile"].plot(distance, np.sin(distance/30)*.2+.6, color=GREEN)
    axes["profile"].set(xlabel="Along-route distance (m)", ylabel="Synthetic openness (1)")
    left = np.zeros(10)
    for j, (name, color) in enumerate(zip(("View", "Access", "Variety"), (BLUE, GREEN, "#E69F00"))):
        part = components[:,j]*weights[j]
        axes["scores"].barh(names, part, left=left, color=color, label=name, height=.55)
        left += part
    axes["scores"].errorbar(score, np.arange(10), xerr=[np.maximum(0,score-low), np.maximum(0,high-score)],
                            fmt="none", ecolor=".2", capsize=2, lw=.8)
    axes["scores"].set(xlabel="Weighted score (1)", xlim=(0, 1))
    axes["scores"].legend(loc="lower right", fontsize=7)
    return fig, axes, dict(components=components, weights=weights, score=score, perturb_scores=scores,
                           route=route, distance=distance), {
        "objects": names, "sensitivity": "5-95% weight-perturbation range; not confidence interval",
        "external_validation": None, "route_scope": "synthetic Garden 01 only; scores cover all ten"}


BUILDERS = dict(A=scheduling, B=communication, C=reconstruction, D=field, E=diagnosis, F=spatial)


def mechanism(folder):
    """Editable schematic of the implemented E signal path, not a learned model."""
    with paper_style():
        fig, axes = compose([["pipeline"]], width_mm=180, height_mm=65)
        source_path = folder.parent / "E/input_and_results.npz"
        with np.load(source_path, allow_pickle=False) as stored:
            wave = stored["signal"]
            bins = len(stored["frequency_hz"])
        _, _, stft = signal.stft(wave, 2048, window="hann", nperseg=256, noverlap=192)
        nodes = [f"Input\n{len(wave)} samples", f"Welch\n{bins} bins",
                 f"STFT\n{stft.shape[0]} x {stft.shape[1]}", "PSD panel", "Time-frequency\npanel"]
        edges = [(nodes[0], nodes[1]), (nodes[0], nodes[2]), (nodes[1], nodes[3]), (nodes[2], nodes[4])]
        positions = {nodes[0]: (0, .5), nodes[1]: (1, .85), nodes[2]: (1, .15),
                     nodes[3]: (2, .85), nodes[4]: (2, .15)}
        ax = axes["pipeline"]
        network_graph(edges, nodes=nodes, pos=positions, directed=True, labels=False, ax=ax)
        for name, (x, y) in positions.items():
            ax.annotate(name, (x, y), xytext=(0, 17), textcoords="offset points", ha="center", fontsize=8)
        ax.set(xlim=(-.35, 2.4), ylim=(-.1, 1.25))
        export_revision(fig, folder, metadata={"synthetic": True, "scope": "E implemented feature pipeline; schematic",
                        "source": artifact(source_path, folder)})
        plt.close(fig)


def artifact(path, base):
    return {"path": Path(os.path.relpath(path, base)).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def render(output: Path, cases="ABCDEF"):
    started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    summary = []
    for key in cases:
        folder = output / key
        folder.mkdir()
        with paper_style():
            fig, axes, arrays, facts = BUILDERS[key](np.random.default_rng(20260920+ord(key)), folder)
            panel_labels(axes.values())
            np.savez(folder / "input_and_results.npz", **arrays)
            # Reload the archived artifact before export; the saved source is inspectable.
            with np.load(folder / "input_and_results.npz", allow_pickle=False) as stored:
                for name, value in arrays.items():
                    np.testing.assert_array_equal(stored[name], value)
            (folder / "facts.json").write_text(json.dumps(dict(synthetic=True, **facts), indent=2), encoding="utf-8")
            export_revision(fig, folder / "composed", metadata={"synthetic": True, "case": key,
                            "source": artifact(folder / "input_and_results.npz", folder / "composed"),
                            "facts": artifact(folder / "facts.json", folder / "composed")})
            plt.close(fig)
        summary.append({"case": key, "preview": f"{key}/composed/figure.png", "status": "candidate",
                        "visual_review": "pending", "synthetic": True})
        if key == "D":
            # A separate analytic fixture avoids imputing missing observations.
            base = 3 + 2*np.exp(-((arrays["x"]-500)**2+(arrays["y"]-300)**2)/80000)
            complete = [base, base + .3*np.sin(arrays["x"]/150)]
            np.savez(folder / "comparison_input.npz", x=arrays["x"], y=arrays["y"], t0=complete[0], t1=complete[1])
            with paper_style():
                plot_field_contour(arrays["x"], arrays["y"], complete,
                                   panel_titles=["t0", "t1"], value_label="Speed (m/s)",
                                   xlabel="East (m)", ylabel="North (m)",
                                   out_stem=str(folder / "legacy_same_input"))
                fig, axs = compose([["t0", "t1"]], height_mm=78)
                maps = [draw_field(ax, arrays["x"], arrays["y"], z, vmin=min(a.min() for a in complete),
                                   vmax=max(a.max() for a in complete)) for ax,z in zip(axs.values(),complete)]
                for ax in axs.values():
                    ax.set(xlabel="East (m)", ylabel="North (m)", aspect="equal")
                shared_colorbar(fig, maps, axs.values(), label="Speed (m/s)", shrink=.8)
                panel_labels(axs.values())
                export_revision(fig, folder / "comparison_new", metadata={"synthetic": True,
                                "source": artifact(folder / "comparison_input.npz", folder / "comparison_new")})
                plt.close(fig)
    if "E" in cases:
        mechanism(output / "mechanism")
    cards = []
    for row in summary:
        folder = output / row["case"]
        row["source"] = artifact(folder / "input_and_results.npz", output)
        row["facts"] = artifact(folder / "facts.json", output)
        with Image.open(folder / "composed/figure.png") as image:
            image.thumbnail((680, 900))
            image.save(folder / "final_size_96dpi.png")
        cards.append(f'<section><h2>{html.escape(row["case"])} / synthetic / visual review pending</h2>'
                     f'<img src="{row["case"]}/final_size_96dpi.png" style="width:180mm;max-width:100%;height:auto">'
                     f'<p><a href="{row["case"]}/composed/figure.pdf">PDF at 180 mm</a> | '
                     f'<a href="{row["case"]}/composed/figure.svg">Editable SVG</a> | '
                     f'<a href="{row["case"]}/facts.json">Facts</a></p></section>')
    (output / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>Synthetic examples</title>'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<style>body{font:14px system-ui;margin:24px;color:#242424}section{border-bottom:1px solid #ddd;padding:12px 0}h2{font-size:16px}</style>'
            '<h1>Task examples</h1>' + ''.join(cards), encoding="utf-8")
    (output / "run.json").write_text(json.dumps({"elapsed_s": time.perf_counter()-started,
            "matplotlib": matplotlib.__version__, "numpy": np.__version__,
            "script": {"sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            "seed": "20260920 + ord(case)", "license": "repository LICENSE; synthetic data",
            "visual_review": "pending"}, indent=2), encoding="utf-8")
    (output / "index.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cases", default="ABCDEF")
    args = parser.parse_args()
    if not args.cases or len(set(args.cases)) != len(args.cases) or set(args.cases)-set(BUILDERS):
        parser.error("cases must contain unique letters from ABCDEF")
    render(args.output, args.cases)
