"""Optional local browser smoke: run directly; no browser downloads or server."""

import json
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_result_gallery import build
from inspect_assets import sha256


def main():
    with tempfile.TemporaryDirectory(prefix="mathmodel-gallery-") as directory:
        root = Path(directory)
        source = root / "result.json"
        source.write_text(json.dumps({"demo_only": True, "x": [1, 2, 3, 4], "error": [0.6, 0.3, 0.2, 0.15]}))
        values = json.loads(source.read_text())
        figure, ax = plt.subplots(figsize=(5, 3))
        ax.plot(values["x"], values["error"], "o-", color="#168578")
        ax.set(xlabel="Iteration", ylabel="Error (demo)")
        image = root / "curve.png"
        figure.savefig(image, dpi=300, bbox_inches="tight")
        plt.close(figure)
        image_ref = {"path": image.name, "sha256": sha256(image)}
        data = {"schema_version": "figure-candidates-1", "figures": [{
            "figure_id": "demo_Q1", "question": "Q1", "claim": "Synthetic example: decreasing residual",
            "caption": "Demo result, not competition evidence", "status": "candidate", "qa": "passed",
            "width_mm": 90, "parameters": {"demo_only": True},
            "source": {"path": source.name, "sha256": sha256(source)}, "preview": image_ref,
            "originals": [image_ref]}]}
        manifest = root / "candidates.json"
        manifest.write_text(json.dumps(data))
        gallery = root / "gallery"
        build(manifest, gallery)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            for width, height in ((1365, 900), (390, 844)):
                page.set_viewport_size({"width": width, "height": height})
                page.goto((gallery / "index.html").as_uri())
                assert page.locator("img").evaluate("img => img.complete && img.naturalWidth > 0")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.locator("summary").click()
                assert page.locator("details").get_attribute("open") is not None
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                screenshot = Path(__file__).resolve().parents[1] / "outputs" / f"gallery_{width}.png"
                screenshot.parent.mkdir(exist_ok=True)
                page.screenshot(path=str(screenshot), full_page=True)
                print(f"screenshot={screenshot}")
                page.locator("a").click()
                page.wait_for_url("**/original_0_0.png")
                assert page.locator("img").evaluate("img => img.complete && img.naturalWidth > 0")
            assert not errors
            browser.close()
    print("browser: 2 passed, 0 failed")


if __name__ == "__main__":
    main()
