"""Maintenance-only evidence: rendered QA, equal-width PDF, local browser checks."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "templates/figures/scripts"))

import matplotlib.pyplot as plt
import numpy as np
import fitz
from figqa import analyze_figure
from figure_lint import lint_figure
from figure_composition import paper_style
from render_task_examples import BUILDERS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("examples", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    qa = {}
    for key, builder in BUILDERS.items():
        import tempfile
        with tempfile.TemporaryDirectory(prefix="figure-upgrade-qa-") as temporary:
            with paper_style():
                from figure_composition import panel_labels
                fig, axes, _, _ = builder(np.random.default_rng(20260920+ord(key)), Path(temporary))
                panel_labels(axes.values())
                fig.set_dpi(300)
                collisions = analyze_figure(fig, key)
                violations = lint_figure(fig, key)
                qa[key] = {"collisions": [asdict(c) for c in collisions],
                           "lint": [asdict(v) for v in violations]}
                plt.close(fig)
    (args.output / "machine-qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    # Same-input old and new plots both placed at 180 mm, on the same A4 page.
    mm = 72/25.4
    with fitz.open() as doc:
        page = doc.new_page(width=210*mm, height=297*mm)
        for label, path, top in (
            ("Legacy / same synthetic input / 180 mm", args.examples / "D/legacy_same_input.pdf", 22),
            ("Composition / same synthetic input / 180 mm", args.examples / "D/comparison_new/figure.pdf", 153),
        ):
            page.insert_text((15*mm, (top-5)*mm), label, fontsize=10)
            with fitz.open(path) as source:
                height = source[0].rect.height/source[0].rect.width*180*mm
                page.show_pdf_page(fitz.Rect(15*mm, top*mm, 195*mm, top*mm+height), source, 0)
        doc.save(args.output / "same-input-180mm.pdf")
        page.get_pixmap(dpi=144).save(args.output / "same-input-180mm.png")
    with fitz.open() as doc:
        for key in BUILDERS:
            page = doc.new_page(width=210*mm, height=297*mm)
            page.insert_text((15*mm, 18*mm), f"{key} / synthetic / candidate / visual review pending", fontsize=10)
            with fitz.open(args.examples / key / "composed/figure.pdf") as source:
                height = source[0].rect.height/source[0].rect.width*180*mm
                page.show_pdf_page(fitz.Rect(15*mm, 25*mm, 195*mm, 25*mm+height), source, 0)
        doc.save(args.output / "examples-180mm.pdf")
        for index, page in enumerate(doc):
            page.get_pixmap(dpi=144).save(args.output / f"page-{index+1}.png")
    from playwright.sync_api import sync_playwright
    browser_checks = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            for width, height in ((1365, 900), (390, 844)):
                page = browser.new_page(viewport={"width": width, "height": height})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto((args.examples / "index.html").resolve().as_uri())
                assert page.locator("img").count() == 6
                assert page.locator("img").evaluate_all("images => images.every(i => i.complete && i.naturalWidth > 0)")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert not errors
                page.screenshot(path=str(args.output / f"browser-{width}.png"), full_page=True)
                browser_checks.append({"width": width, "status": "passed"})
                page.close()
        finally:
            browser.close()
    (args.output / "browser.json").write_text(json.dumps(browser_checks, indent=2))
    print("browser: 2 passed, 0 failed")
    for key, checks in qa.items():
        print(f"{key}: collisions={len(checks['collisions'])}, lint={len(checks['lint'])}")
    print("visual review: not performed; all figures remain candidates")


if __name__ == "__main__":
    main()
