"""Validate generated example manifests and exercise v2 diagnostic gallery."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from inspect_assets import sha256
from build_result_gallery import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("examples", type=Path)
    args = parser.parse_args()
    root = args.examples.resolve()
    passed = 0
    for manifest in root.rglob("manifest.json"):
        data = json.loads(manifest.read_text())
        for ref in data["files"]:
            path = manifest.parent / ref["path"]
            assert path.is_file() and sha256(path) == ref["sha256"]
            passed += 1
        for key in ("source", "facts"):
            ref = data["metadata"].get(key)
            if ref:
                path = manifest.parent / ref["path"]
                assert path.is_file() and sha256(path) == ref["sha256"]
                passed += 1
        assert data["visual_review"] == "pending"
    run = json.loads((root / "run.json").read_text())
    script = ROOT / "templates/figures/scripts/render_task_examples.py"
    assert run["script"]["sha256"] == sha256(script)
    passed += 1
    figures = []
    for item in json.loads((root / "index.json").read_text()):
        key = item["case"]
        def ref(path):
            return {"path": path.relative_to(root).as_posix(), "sha256": sha256(path)}
        figures.append({"figure_id": key, "question": key, "claim": "Synthetic task example",
                        "caption": "Candidate; visual review pending", "status": "candidate", "qa": "unknown",
                        "destination": "exploration", "width_mm": 180, "parameters": {"synthetic": True},
                        "source": item["source"], "preview": ref(root / key / "final_size_96dpi.png"),
                        "originals": [ref(root / key / "composed" / f"figure.{ext}") for ext in ("png", "svg", "pdf")]})
    manifest = root / "gallery-input.json"
    with manifest.open("x", encoding="utf-8") as stream:
        json.dump({"schema_version": "figure-candidates-2", "figures": figures}, stream, indent=2)
    report = build(manifest, root / "gallery")
    assert len(report["included"]) == 6 and report["promotion"] == "none"
    assert all(item["delivery_status"] == "not_verified" for item in report["included"])
    assert all(any(check["status"] == "passed" for check in item["original_checks"]) for item in report["included"])
    passed += 3
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            for width, height in ((1365, 900), (390, 844)):
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto((root / "gallery/index.html").as_uri())
                assert page.locator("article").count() == 6
                assert page.locator("img").evaluate_all("xs=>xs.every(x=>x.complete&&x.naturalWidth>0)")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.locator("summary").first.click()
                assert page.locator("details").first.get_attribute("open") is not None
                page.screenshot(path=str(root / f"gallery/browser-{width}.png"), full_page=True)
                page.close()
                passed += 1
        finally:
            browser.close()
    (root / "integrity.json").write_text(json.dumps({"passed": passed, "failed": 0,
        "visual_review": "not_performed", "browser_checks_included": 2}, indent=2))
    print(f"integrity: {passed} passed, 0 failed")


if __name__ == "__main__":
    main()
