# -*- coding: utf-8 -*-
"""drawio_check.py — 对任意 .drawio 做版式体检（针对中文示意图调校）。

用法:
    python drawio_check.py fig.drawio                  # 体检（FAIL 即退出码 1）
    python drawio_check.py fig.drawio --strict         # WARN 也算失败
    python drawio_check.py fig.drawio --max-font-tiers 4

FAIL（硬伤）: 文字溢出、元素越界、id 重复、实心盒重叠、连线穿盒、内嵌位图。
WARN（建议）: 端点压盒边、有填充无文字的疑似空盒、字号档数过多、填充色发散;
  v7.9.1 新增平庸检测 —— 全字加粗（字重层级被抹平）、实心盒 >20（密度超预算,
  建议拆总览+细节）、连线描边 >2.0（连线过重, 强调用色不用粗）。

中文字宽模型（与 sci-box check_layout 一致, 比生成器的 1.45/0.72 保守估值
更接近真实排版）: 全角(east_asian_width ∈ W/F) ≈ 字号, 其余 ≈ 字号/2,
行高 ≈ 字号 + 3。生成器保守换行、体检按真实度量判溢出, 两层互补。

豁免规则（刻意排版不算缺陷）:
  - strokeColor=none 的文字/底色块 与 dashed+fillColor=none 的虚线容器/
    点线分带, 不参与实心盒重叠判定;
  - 紧密堆叠的行列间距、同族尺寸对齐不查（前者是刻意排版, 后者机器判族
    必然误报 —— 交给 render 后的人眼九区盘点）。

规则蒸馏自 sci-box scibox-diagram scripts/check_layout.py (MIT),
阈值对齐 mathmodel-studio design_tokens.md §4.5/§4.6（字号 ≤4 档、
焦点盒 ≤2、描边三档 0.8/1.2/2.0）。

退出码: 0 通过; 1 有 FAIL（--strict 时有 WARN 也算）; 2 文件/参数错误。
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

DEFAULT_MAX_FONT_TIERS = 4     # design_tokens §4.5: 标题/标题条/正文/注释 4 档封顶
DEFAULT_MAX_FILLS = 12         # 族化配色下一张图的正常填充色数上限


def style_of(style: str) -> dict[str, str]:
    """drawio style 串 → 键值 dict（无值键记为 '1'）。"""
    out: dict[str, str] = {}
    for kv in (style or "").split(";"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            out[k.strip()] = v.strip()
        elif kv.strip():
            out[kv.strip()] = "1"
    return out


def text_w(line: str, fs: float) -> float:
    """估算单行显示宽: 全角≈fs, 半角≈fs/2（east_asian_width 判定）。"""
    return sum(fs if unicodedata.east_asian_width(c) in ("W", "F") else fs / 2
               for c in line)


def plain(value: str) -> str:
    """drawio label(html=1) → 纯文本: <br> 转换行, 去其余标签, 反转义实体。"""
    v = re.sub(r"<br\s*/?>", "\n", value or "", flags=re.I)
    v = re.sub(r"<[^>]+>", "", v)
    return (v.replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&apos;", "'")
             .replace("&amp;", "&"))


def seg_rect(x1: float, y1: float, x2: float, y2: float, rect) -> bool:
    """线段与矩形是否相交（含边界接触）。"""
    rx, ry, rw, rh = rect
    if (max(x1, x2) < rx or min(x1, x2) > rx + rw
            or max(y1, y2) < ry or min(y1, y2) > ry + rh):
        return False
    if x1 == x2 or y1 == y2:  # 正交线段: 包围盒相交即相交
        return True
    for ax, ay, bx, by in ((rx, ry, rx + rw, ry), (rx, ry + rh, rx + rw, ry + rh),
                           (rx, ry, rx, ry + rh), (rx + rw, ry, rx + rw, ry + rh)):
        d1 = (x2 - x1) * (ay - y1) - (y2 - y1) * (ax - x1)
        d2 = (x2 - x1) * (by - y1) - (y2 - y1) * (bx - x1)
        d3 = (bx - ax) * (y1 - ay) - (by - ay) * (x1 - ax)
        d4 = (bx - ax) * (y2 - ay) - (by - ay) * (x2 - ax)
        if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
            return True
    return False


def check_file(path: str, *, max_font_tiers: int = DEFAULT_MAX_FONT_TIERS,
               max_fills: int = DEFAULT_MAX_FILLS,
               overlap_area_frac: float = 0.30) -> tuple[list[str], list[str]]:
    """体检一个 .drawio 文件, 返回 (fails, warns)。

    Args:
        max_font_tiers: 全图带文字盒的字号档数上限（design_tokens §4.5 扁平字阶）。
        max_fills: 实心盒填充色种数上限（族化配色下 >12 视为发散）。
        overlap_area_frac: 实心盒重叠面积占较小盒比例超过该值才记 FAIL;
            徽章压卡边、标题条骑层带等刻意贴合（小面积交叠）不算缺陷。
    """
    fails: list[str] = []
    warns: list[str] = []

    try:
        root = ET.parse(str(path)).getroot()
    except (ET.ParseError, OSError) as exc:
        return [f"文件无法解析: {exc}"], []

    model = next(root.iter("mxGraphModel"), None)
    if model is None:
        return ["缺 <mxGraphModel> 结构, 不是合法 .drawio 文件"], []
    pw = float(model.get("pageWidth", 0) or 0)
    ph = float(model.get("pageHeight", 0) or 0)

    boxes: list[dict] = []
    edge_paths: list[tuple[str, list[tuple[float, float]]]] = []
    edge_styles: list[tuple[str, dict[str, str]]] = []   # v7.9.1: 全量连线样式（线重检查）
    ids: dict[str, int] = {}

    for cell in root.iter("mxCell"):
        cid = cell.get("id")
        if cid in ids:
            fails.append(f"id 重复: {cid}")
        ids[cid] = 1
        st = style_of(cell.get("style"))
        geom = cell.find("mxGeometry")

        if cell.get("vertex") == "1" and geom is not None:
            x = float(geom.get("x", 0) or 0)
            y = float(geom.get("y", 0) or 0)
            w = float(geom.get("width", 0) or 0)
            h = float(geom.get("height", 0) or 0)
            fs = float(st.get("fontSize", 12) or 12)
            txt = plain(cell.get("value"))
            raw = cell.get("style") or ""
            if "data:image/png" in raw or "data:image/jpeg" in raw:
                fails.append(f"{cid}: 内嵌位图（要求可编辑时整块不可再改）")
            is_text = st.get("strokeColor") == "none" or raw.startswith("text")
            is_frame = st.get("dashed") == "1" and st.get("fillColor") == "none"
            is_shape = "shape=" in raw
            boxes.append({
                "id": cid, "r": (x, y, w, h), "fs": fs, "txt": txt,
                "fill": st.get("fillColor"),
                "solid": not (is_text or is_frame),
                "bold": "fontStyle" in st and st["fontStyle"] not in ("0", ""),
            })
            if (not txt.strip() and not is_text and not is_frame and not is_shape
                    and st.get("fillColor") not in (None, "none")):
                warns.append(f"{cid}: 有填充有描边却没有文字, 疑似漏填")
            if pw and (x < -1 or y < -1 or x + w > pw + 1 or y + h > ph + 1):
                fails.append(f"{cid}: 越出画布 ({x:g},{y:g} {w:g}×{h:g})")
            if txt.strip() and w and h and "shape=singleArrow" not in raw:
                lines = txt.split("\n")
                for ln in lines:
                    # 单字居中边距极小（竖排堆叠常见）, 多字按两侧各 4px 估
                    usable = w - (8 if len(ln) > 1 else 2)
                    if text_w(ln, fs) > usable:
                        fails.append(
                            f'{cid}: 文字溢出 "{ln[:18]}" 需 '
                            f"{text_w(ln, fs):.0f}px > 可用 {usable:.0f}px")
                        break
                if len(lines) * (fs + 3) > h * (1.4 if is_text else 1.0):
                    fails.append(f"{cid}: {len(lines)} 行放不下（槽高 {h:g}px）")

        elif cell.get("edge") == "1" and geom is not None:
            edge_styles.append((cid, st))
            pts: list[tuple[float, float]] = []
            sp = geom.find("mxPoint[@as='sourcePoint']")
            tp = geom.find("mxPoint[@as='targetPoint']")
            arr = geom.find("Array[@as='points']")
            if sp is not None:
                pts.append((float(sp.get("x", 0)), float(sp.get("y", 0))))
            if arr is not None:
                pts += [(float(p.get("x", 0)), float(p.get("y", 0))) for p in arr]
            if tp is not None:
                pts.append((float(tp.get("x", 0)), float(tp.get("y", 0))))
            if len(pts) >= 2:
                edge_paths.append((cid, pts))

    # ---- 实心盒两两重叠（面积占比超阈值才算; 虚线容器/文字/底色块已豁免）----
    solid = [b for b in boxes if b["solid"]]
    for i in range(len(solid)):
        for j in range(i + 1, len(solid)):
            x1, y1, w1, h1 = solid[i]["r"]
            x2, y2, w2, h2 = solid[j]["r"]
            inter_w = min(x1 + w1, x2 + w2) - max(x1, x2)
            inter_h = min(y1 + h1, y2 + h2) - max(y1, y2)
            if inter_w > 0 and inter_h > 0:
                smaller = min(w1 * h1, w2 * h2)
                if smaller > 0 and (inter_w * inter_h) / smaller > overlap_area_frac:
                    fails.append(f"{solid[i]['id']} 与 {solid[j]['id']} 重叠")

    # ---- 连线穿盒（仅对显式折点路径可查; 引用式连线交给渲染后目检）----
    for cid, pts in edge_paths:
        for k in range(len(pts) - 1):
            x1, y1 = pts[k]
            x2, y2 = pts[k + 1]
            for b in solid:
                bx, by, bw, bh = b["r"]
                on_border = (abs(x1 - bx) < 0.6 or abs(x1 - bx - bw) < 0.6
                             or abs(y1 - by) < 0.6 or abs(y1 - by - bh) < 0.6)
                ends_here = (k == 0
                             and bx - 0.6 <= x1 <= bx + bw + 0.6
                             and by - 0.6 <= y1 <= by + bh + 0.6)
                if ends_here and on_border:
                    warns.append(f"{cid}: 端点压在 {b['id']} 边界上, 建议外移 1px")
                    continue
                if seg_rect(x1, y1, x2, y2, b["r"]):
                    fails.append(f"{cid}: 穿过盒子 {b['id']}")
                    break

    # ---- 字号与配色收敛度（design_tokens §4.5 扁平字阶纪律）----
    sizes = sorted({b["fs"] for b in boxes if b["txt"].strip()})
    if len(sizes) > max_font_tiers:
        warns.append(f"字号 {len(sizes)} 种（{sizes}）, 层级过多, "
                     f"建议收敛到 ≤{max_font_tiers} 档（标题/标题条/正文/注释）")
    fills = {b["fill"] for b in solid if b["fill"] not in (None, "none")}
    if len(fills) > max_fills:
        warns.append(f"填充色 {len(fills)} 种, 配色发散, 建议同语义同族同色")

    # ---- v7.9.1 平庸检测（WARN 级: 机器查不出"平庸", 但能查到这三个信号）----
    # 1) 全字加粗: ≥5 个带文字顶点且 >90% 加粗 → 字重层级被抹平
    #    （design_tokens §4.5: 加粗只给标题条/徽章/卡片标题, 正文常规）
    text_boxes = [b for b in boxes if b["txt"].strip()]
    if len(text_boxes) >= 5:
        bold_ratio = sum(1 for b in text_boxes if b["bold"]) / len(text_boxes)
        if bold_ratio > 0.9:
            warns.append(f"{len(text_boxes)} 个文字元素 {bold_ratio:.0%} 加粗, "
                         f"字重层级被抹平——建议正文改常规字重, 加粗只给标题/徽章")
    # 2) 密度预算: 实心盒 >20 个 → 超出单图复杂度预算
    #    （diagram-design: 节点 >9 就该考虑拆总览+细节, 20 是带容器的上限）
    if len(solid) > 20:
        warns.append(f"实心盒 {len(solid)} 个 >20, 密度超单图预算, "
                     f"建议拆成总览图 + 细节图")
    # 3) 连线过重: 任一连线 strokeWidth > 2.0 → 连线退居二线原则
    #    （内容才是主角; 强调主干用色不用粗）
    heavy = [cid for cid, st in edge_styles
             if float(st.get("strokeWidth", 1) or 1) > 2.0]
    if heavy:
        warns.append(f"连线描边 >2.0: {', '.join(heavy[:3])}"
                     f"{' 等' if len(heavy) > 3 else ''}, 建议降到 1.2-1.6, "
                     f"强调用族色而不是加粗")

    seen: set[str] = set()
    fails = [m for m in fails if not (m in seen or seen.add(m))]
    warns = [m for m in warns if not (m in seen or seen.add(m))]
    return fails, warns


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="drawio 版式体检（中文示意图调校）")
    ap.add_argument("drawio", help=".drawio 文件路径")
    ap.add_argument("--strict", action="store_true", help="WARN 也算失败")
    ap.add_argument("--max-font-tiers", type=int, default=DEFAULT_MAX_FONT_TIERS,
                    help=f"字号档数上限（默认 {DEFAULT_MAX_FONT_TIERS}）")
    ap.add_argument("--max-fills", type=int, default=DEFAULT_MAX_FILLS,
                    help=f"填充色种数上限（默认 {DEFAULT_MAX_FILLS}）")
    args = ap.parse_args(argv)

    fails, warns = check_file(args.drawio,
                              max_font_tiers=args.max_font_tiers,
                              max_fills=args.max_fills)
    if fails and fails[0].startswith(("文件无法解析", "缺 <")):
        # check_file 的解析/IO 错误早退路径: 单元素 FAIL, 转退出码 2
        print(f" FAIL {fails[0]}")
        return 2
    print(f"{args.drawio}: FAIL {len(fails)} / WARN {len(warns)}")
    for m in fails:
        print(f"  FAIL {m}")
    for m in warns:
        print(f"  WARN {m}")
    if fails or (args.strict and warns):
        return 1
    print("✓ 版式体检通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
