"""Inspect formal originals, not browser previews. Unknown is not a pass."""

from pathlib import Path
import math
import re
import xml.etree.ElementTree as ET


def original_quality(path: Path, width_mm: float) -> dict:
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}:
        from PIL import Image
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            dpi = image.width * 25.4 / width_mm
            # Rasterizers truncate fractional canvas pixels at the requested dpi.
            required_pixels = max(1, math.floor(width_mm / 25.4 * 300))
            return {"path": path.name, "kind": "raster", "dpi": dpi,
                    "status": "passed" if image.width >= required_pixels else "failed",
                    "reason": "original effective resolution"}
    if suffix == ".svg":
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as error:
            raise ValueError(f"invalid SVG content: {path.name}") from error
        tags = {node.tag.rsplit("}", 1)[-1] for node in root.iter()}
        if root.tag != "{http://www.w3.org/2000/svg}svg":
            raise ValueError(f"invalid SVG root: {path.name}")
        if tags & {"script", "foreignObject"}:
            raise ValueError(f"active SVG content: {path.name}")
        for node in root.iter():
            for key, value in node.attrib.items():
                key = key.rsplit("}", 1)[-1].lower()
                if key.startswith("on") or (key == "href" and not value.startswith(("#", "data:image/"))):
                    raise ValueError(f"active or external SVG reference: {path.name}")
            css = node.attrib.get("style", "") + (node.text or "" if node.tag.endswith("}style") else "")
            if re.search(r"@import|url\(\s*['\"]?(?!#)[^)]", css, re.IGNORECASE):
                raise ValueError(f"external SVG style reference: {path.name}")
        if "image" not in tags and tags & {"path", "line", "rect", "circle", "text", "polyline", "polygon", "ellipse"}:
            return {"path": path.name, "kind": "vector", "status": "passed"}
        return {"path": path.name, "kind": "mixed_or_empty", "status": "unknown",
                "reason": "embedded raster requires image-specific scale review"}
    if suffix == ".pdf":
        try:
            import fitz
        except ImportError:
            return {"path": path.name, "status": "unknown", "reason": "PDF inspection needs PyMuPDF"}
        with fitz.open(path) as doc:
            if len(doc) == 1 and not doc[0].get_images() and (doc[0].get_drawings() or doc[0].get_text().strip()):
                return {"path": path.name, "kind": "vector", "status": "passed"}
        return {"path": path.name, "status": "unknown", "reason": "PDF needs page/image-specific review"}
    return {"path": path.name, "status": "unknown", "reason": "editable source is not a formal export"}
