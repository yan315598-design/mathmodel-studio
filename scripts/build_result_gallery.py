"""Build a local, portable gallery of verified candidate figures, without promoting them to a paper."""

from __future__ import annotations

import argparse
import html
import json
import math
import shutil
from pathlib import Path

from inspect_assets import sha256
from figure_export_quality import original_quality


def verified(base: Path, artifact: dict) -> Path:
    path = (base / artifact["path"]).resolve()
    if not path.is_file() or sha256(path) != artifact["sha256"]:
        raise ValueError(f"missing or stale artifact: {artifact['path']}")
    return path


def build(manifest: Path, output: Path) -> dict:
    from PIL import Image

    if output.exists():
        raise ValueError("gallery directory exists; use a new revision")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    version2 = data.get("schema_version") == "figure-candidates-2"
    if data.get("schema_version") not in {"figure-candidates-1", "figure-candidates-2"}:
        raise ValueError("expected figure-candidates-1 or figure-candidates-2")
    limit = data.get("max_items", 12)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("max_items must be between 1 and 100")
    entries, skipped, ids = [], [], set()
    for item in data["figures"]:
        key = item["figure_id"]
        if not isinstance(key, str) or not key or key in ids:
            raise ValueError("figure ids must be unique nonempty strings")
        ids.add(key)
        if version2 and item.get("status") not in {"diagnostic", "candidate", "reviewed", "adopted", "rejected"}:
            raise ValueError(f"{key}: invalid v2 lifecycle status")
        if version2 and item.get("status") == "rejected":
            skipped.append({"figure_id": key, "reason": item.get("reason", "rejected; reason unknown"),
                            "source": item.get("source"), "status": "rejected"})
            continue
        if not version2 and item.get("status") not in {"candidate", "paper", "appendix"}:
            skipped.append({"figure_id": key, "reason": "diagnostic or rejected"})
            continue
        if not version2 and item.get("qa") != "passed":
            skipped.append({"figure_id": key, "reason": "QA not passed"})
            continue
        for field in ("question", "claim", "caption", "parameters"):
            if field not in item or item[field] in (None, ""):
                raise ValueError(f"{key}: {field} required")
        width = item["width_mm"]
        if isinstance(width, bool) or not isinstance(width, (float, int)) or not math.isfinite(width) or width <= 0:
            raise ValueError(f"{key}: width_mm must be positive")
        try:
            source = verified(manifest.parent, item["source"])
            image_path = verified(manifest.parent, item["preview"])
            originals = [verified(manifest.parent, asset) for asset in item.get("originals", [])]
        except ValueError as error:
            if not version2:
                raise
            skipped.append({"figure_id": key, "reason": str(error), "source": item.get("source"),
                            "status": item["status"]})
            continue
        if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("preview must be a bitmap, not executable markup")
        with Image.open(image_path) as image:
            image.verify()
        with Image.open(image_path) as image:
            dpi = image.width / (width / 25.4)
        if not originals or any(path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".svg", ".pdf", ".drawio", ".tif", ".tiff"} for path in originals):
            raise ValueError(f"{key}: supported original files required")
        native_mask = version2 and item.get("object") == "mask" and item.get("destination") == "answer_attachment"
        if native_mask:
            expected = item.get("native", {})
            if not expected.get("size") or not expected.get("mode"):
                raise ValueError(f"{key}: mask requires native size [width,height] and mode")
            quality = []
            for path in originals:
                with Image.open(path) as image:
                    image.load()
                    matches = list(image.size) == expected["size"] and image.mode == expected["mode"]
                    if "values" in expected:
                        import numpy as np
                        matches = matches and set(np.unique(np.asarray(image)).tolist()) <= set(expected["values"])
                quality.append({"path": path.name, "kind": "native_mask",
                                "status": "passed" if matches else "failed",
                                "reason": "native size/mode/declared coding; no resampling or dpi requirement"})
        else:
            quality = [original_quality(path, width) for path in originals]
        if not version2 and not any(record["status"] == "passed" for record in quality):
            skipped.append({"figure_id": key, "reason": "no verified print-quality original", "original_checks": quality})
            continue
        item = dict(item, original_checks=quality)
        if version2:
            item["destination"] = item.get("destination", "unknown")
            original_passed = (all if native_mask else any)(r["status"] == "passed" for r in quality)
            item["delivery_status"] = ("reviewed_candidate" if item.get("qa") == "passed"
                                       and item["status"] in {"reviewed", "adopted"}
                                       and original_passed else "not_verified")
            item["review_reason"] = ("QA, lifecycle or original quality incomplete"
                                     if item["delivery_status"] == "not_verified" else "no automatic promotion")
        entries.append((item, image_path, originals, dpi, source))
    if len(entries) > limit:
        raise ValueError(f"gallery budget exceeded: {len(entries)} > {limit}; curate candidates first")
    output.mkdir(parents=True)
    cards = []
    for index, (item, image_path, originals, dpi, _) in enumerate(entries):
        thumb = f"thumb_{index}.png"
        with Image.open(image_path) as image:
            image.thumbnail((640, 420))
            image.convert("RGB").save(output / thumb)
        links = []
        for number, path in enumerate(originals):
            name = f"original_{index}_{number}{path.suffix.lower()}"
            shutil.copyfile(path, output / name)
            links.append(f'<a href="{name}">{html.escape(path.name)}</a>')
        title = html.escape(f"{item['question']} / {item['figure_id']}")
        cards.append(f'<article><h2>{title}</h2><img src="{thumb}" alt="{html.escape(item["caption"], quote=True)}">'
                     f'<p>{html.escape(item["claim"])}</p><p>{html.escape(item["caption"])}</p>'
                     f'<p>{html.escape(item["status"])} | preview {dpi:.0f} dpi | {item["width_mm"]} mm</p>'
                     f'<p>{html.escape(item.get("delivery_status", "candidate"))} / {html.escape(item.get("destination", "unknown"))}</p>'
                     f'<p>{" | ".join(links)}</p><details><summary>Provenance</summary><pre>'
                     f'{html.escape(json.dumps({k: item[k] for k in ("source", "parameters")}, ensure_ascii=False, indent=2))}'
                     '</pre></details></article>')
    page = ('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Result Gallery</title><style>'
            'body{font:16px system-ui;margin:24px;color:#242424;background:#fafafa;letter-spacing:0}'
            'main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:20px}'
            'article{border:1px solid #ccc;border-radius:6px;padding:16px;min-width:0;background:white}'
            'h1{font-size:24px}h2{font-size:18px}img{width:100%;height:230px;object-fit:contain}'
            'p,pre,a,h2{overflow-wrap:anywhere}pre{white-space:pre-wrap}a{color:#156e65}'
            '</style><h1>Result Gallery</h1><main>' + ''.join(cards) + '</main></html>')
    (output / "index.html").write_text(page, encoding="utf-8")
    report = {"schema_version": "gallery-2" if version2 else "gallery-1", "included": [row[0] for row in entries], "skipped": skipped,
              "manifest_sha256": sha256(manifest), "promotion": "none"}
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build(args.manifest, args.output)
    except (ValueError, KeyError, TypeError, OSError, ImportError) as error:
        parser.exit(2, f"[ERROR] {error}\n")
    print(f"[gallery] included={len(report['included'])} skipped={len(report['skipped'])} output={args.output / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
