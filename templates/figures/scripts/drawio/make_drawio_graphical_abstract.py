# -*- coding: utf-8 -*-
"""draw.io 作战地图 · 三问题色带总览（drawio 模板包 · graphical_abstract_3band）。

整页 graphical abstract: 三个横向色带（问题一/二/三各绑一枝 DIAGRAM_FAMILIES
色族）, 每带内容框由 content JSON 驱动（问题/方法/关键结果/缩略图占位）,
带间因果箭头标注上一问输出如何驱动下一问。评委一页看懂全文骨架。

示意图草稿协议（图叙事纪律: 示意图走"草稿 + 人工精修"通道）:
    - 默认交付 .drawio（draw.io 打开即编辑）; 文件名默认 F0_route.draft.drawio,
      .draft 后缀 = 待人工精修, 精修后去 .draft 入 figures/, stage 8 只收
      无 .draft 版本;
    - --png 可选导出 PNG 预览（需要本机装有 drawio CLI, 未装则提示跳过,
      可在 draw.io 桌面/网页版手动导出）;
    - 缩略图框是占位: 精修时必须嵌入真实结果图, 不得画假图。

content JSON schema（--content 自定义时）:
    {
      "title": "作战地图：三问题一页总览",
      "bands": [
        {"problem": "问题一", "question": "……？",
         "methods": ["方法甲", "方法乙"],          # 1-3 条
         "key_result": "关键结果", "key_detail": "数值/口径",
         "thumbnail": "F1_temp_field.png",          # 缩略图占位提示
         "causal_to_next": "输出 → 输入"},          # 仅非末带使用
        …  # 2-5 带
      ]
    }

用法:
    python make_drawio_graphical_abstract.py [--content 内容.json] [--png]
                                             [--out 输出前缀]
    不给 --out 时默认写入系统临时目录 F0_route.draft.drawio。

退出码: 0 成功; 1 版式门禁 FAIL; 2 参数/数据/IO 错误。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from drawio_builder import (  # noqa: E402
    DIAGRAM_FONT_RAMP, Diagram, base_parser, default_out_stem, finalize,
    fit_text, get_diagram_families, get_palette, label_html, snap4,
    wrap_text_balanced,
)

# 三带绑定的示意图色族（蓝/橙/青, 三问视觉分区）
BAND_FAMILIES = ["blue", "orange", "teal"]

# 内置示例内容（--content 缺省时使用; 换成你的三问真实内容）
DEMO_CONTENT = {
    "title": "作战地图：三问题一页总览",
    "bands": [
        {
            "problem": "问题一",
            "question": "板材干燥温度场如何演化",
            "methods": ["PDE 热传导模型", "有限体积离散"],
            "key_result": "温度场演化规律",
            "key_detail": "最大误差 0.8 °C",
            "thumbnail": "F1_temp_field.png",
            "causal_to_next": "输出温度场 → 驱动水分迁移",
        },
        {
            "problem": "问题二",
            "question": "含水率何时形成干壳",
            "methods": ["耦合扩散模型", "Crank-Nicolson 求解"],
            "key_result": "干壳形成时刻",
            "key_detail": "t* = 2.4 h",
            "thumbnail": "Q2_C1_stages.png",
            "causal_to_next": "输出临界判据 → 反演工艺窗口",
        },
        {
            "problem": "问题三/四",
            "question": "工艺参数如何反演优化",
            "methods": ["阈值穿越反演", "网格收敛验证"],
            "key_result": "最优工艺参数窗口",
            "key_detail": "λ ∈ [0.42, 0.58]",
            "thumbnail": "Q34_C1_gridconv.png",
        },
    ],
}

# 页面几何（px, y 向下; 页边距 ≥40, 坐标对齐 4px 网格）
CANVAS_W = 1220.0
ML = 40.0                       # 页左右边距
TITLE_ZONE = 56.0               # 顶部标题区高
HEADER_W = 190.0                # 带左侧问题标题条宽
HEADER_PAD = 8.0                # 色带内边距
GAP_X = 16.0                    # 卡片横向间距
GAP_Y = 12.0                    # 内容行与缩略图行间距
THUMB_H = 52.0                  # 缩略图占位高
RESULT_W = 320.0                # 关键结果卡宽
BAND_GAP = 44.0                 # 带间距（容纳因果箭头与标签）
BOTTOM_PAD = 40.0
BODY_FS, NOTE_FS = (DIAGRAM_FONT_RAMP["body"],
                    DIAGRAM_FONT_RAMP["note"])
HEADER_FS, HEADER_FS_MIN = 12.0, 9.0
TEXT_PAD = 14.0
DEFAULT_STEM = "F0_route.draft"   # 草稿协议文件名（finalize 自动补 .drawio）


def _card_h(title: str, detail: str, max_w: float, min_h: float = 56.0) -> float:
    """按内容估算卡高: 标题行 + 明细行 + 块间 4px + 上下留白。"""
    t_lines = wrap_text_balanced(title, max_w, BODY_FS)
    h = len(t_lines) * BODY_FS * 1.5
    if detail.strip():
        d_lines = wrap_text_balanced(detail, max_w, NOTE_FS)
        h += 4.0 + len(d_lines) * NOTE_FS * 1.5
    return max(h + 14.0, min_h)


def validate_content(content) -> dict:
    """校验 content JSON 结构, 返回规范化后的 dict。

    Raises:
        ValueError: 顶层不是 dict、bands 缺失/条数越界（2-5）、带内字段
            缺失或类型/条数不合法。
    """
    if not isinstance(content, dict):
        raise ValueError(f"content 顶层须为 JSON 对象, 实际 {type(content).__name__}")
    bands = content.get("bands")
    if not isinstance(bands, list) or not 2 <= len(bands) <= 5:
        raise ValueError("bands 须为 2-5 条色带的列表（三问题范式默认 3 条）")
    title = content.get("title", DEMO_CONTENT["title"])
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title 须为非空字符串")
    for i, band in enumerate(bands):
        if not isinstance(band, dict):
            raise ValueError(f"bands[{i}] 须为 JSON 对象, 实际 {type(band).__name__}")
        for key in ("problem", "question", "key_result"):
            value = band.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"bands[{i}].{key} 须为非空字符串")
        methods = band.get("methods")
        if (not isinstance(methods, list) or not 1 <= len(methods) <= 3
                or any(not isinstance(m, str) or not m.strip() for m in methods)):
            raise ValueError(f"bands[{i}].methods 须为 1-3 条非空字符串列表")
        for key in ("key_detail", "thumbnail", "causal_to_next"):
            value = band.get(key, "")
            if not isinstance(value, str):
                raise ValueError(f"bands[{i}].{key} 须为字符串（可为空）")
    return {"title": title, "bands": bands}


def build_graphical_abstract(content: dict,
                             palette: str = "academic_blue") -> Diagram:
    """构建三带作战地图的 Diagram（不落盘）。

    Args:
        content: validate_content 通过的内容 dict（title + bands）。
        palette: 色板名（兼容校验; 带色由 DIAGRAM_FAMILIES 色族接管）。

    Raises:
        ValueError: content 结构不合法或色板名未知。
    """
    content = validate_content(content)
    get_palette(palette)   # 兼容校验: --palette 仍须是已注册色板名
    n = len(content["bands"])
    # 三带绑三族; 带数 >3 时按蓝/橙/青循环续族
    band_order = [BAND_FAMILIES[i % len(BAND_FAMILIES)] for i in range(n)]
    fams = get_diagram_families(band_order, n)
    warnings: list[str] = []
    band_w = CANVAS_W - 2 * ML
    content_x0 = ML + HEADER_PAD + HEADER_W + HEADER_PAD
    content_w = band_w - 2 * HEADER_PAD - HEADER_W - HEADER_PAD
    methods_w = content_w - RESULT_W - GAP_X
    n_methods_max = 3
    method_w = (methods_w - (n_methods_max - 1) * GAP_X) / n_methods_max

    # 逐带预估内容卡高（方法卡取该带最高者）, 带高随内容自适应
    band_heights: list[float] = []
    for band in content["bands"]:
        m_h = max(_card_h(m, "", method_w - 2 * TEXT_PAD) for m in band["methods"])
        r_h = _card_h(band["key_result"], band.get("key_detail", ""),
                      RESULT_W - 2 * TEXT_PAD)
        row_h = max(m_h, r_h)
        band_heights.append(snap4(HEADER_PAD + row_h + GAP_Y + THUMB_H + HEADER_PAD))
    canvas_h = snap4(TITLE_ZONE + sum(band_heights)
                     + (n - 1) * BAND_GAP + BOTTOM_PAD)

    d = Diagram(page_width=CANVAS_W, page_height=canvas_h, name="作战地图")
    d.title("title", content["title"], ML, 14, band_w, 34)

    cursor = TITLE_ZONE
    for bi, band in enumerate(content["bands"]):
        h = band_heights[bi]
        fam = fams[bi]
        # 1) 色带底（族 fill 浅底, 无描边: 底色块不参与重叠判定）
        d.lane(f"band{bi + 1}", ML, cursor, band_w, h, family=fam)
        # 2) 带左侧问题标题条（族 header 实色 + 白字: 问题名 + 短问句）
        q_lines, q_fs = fit_text(
            band["question"], HEADER_W - 2 * 12.0, HEADER_FS, HEADER_FS_MIN,
            max_h=h - 16.0 - 30.0, ctx=f"bands[{bi}].question", warnings=warnings)
        d.header_bar(
            f"band{bi + 1}_header",
            label_html([band["problem"]]) + "<br>" + label_html(q_lines),
            ML + HEADER_PAD, cursor + HEADER_PAD, HEADER_W, h - 2 * HEADER_PAD,
            family=fam, font_size=q_fs)
        # 3) 方法卡行（两段式富文本卡, 常规字重） + 关键结果卡（末带 focal）
        m_h = max(_card_h(m, "", method_w - 2 * TEXT_PAD) for m in band["methods"])
        r_h = _card_h(band["key_result"], band.get("key_detail", ""),
                      RESULT_W - 2 * TEXT_PAD)
        row_h = max(m_h, r_h)
        per_w = (methods_w - (len(band["methods"]) - 1) * GAP_X) / len(band["methods"])
        for mi, method in enumerate(band["methods"]):
            d.rich_card(f"band{bi + 1}_method{mi + 1}", method, "",
                        content_x0 + mi * (per_w + GAP_X), cursor + HEADER_PAD,
                        per_w, row_h, family=fam)
        d.rich_card(
            f"band{bi + 1}_result", band["key_result"],
            band.get("key_detail", ""),
            ML + band_w - HEADER_PAD - RESULT_W, cursor + HEADER_PAD,
            RESULT_W, row_h, family=fam, focal=(bi == n - 1))
        # 4) 缩略图占位（虚线卡: 精修时替换为真实结果图, 不得画假图）
        thumb_hint = band.get("thumbnail", "").strip()
        thumb_text = (f"缩略图占位: {thumb_hint}（精修时嵌入真实结果）"
                      if thumb_hint else "缩略图占位（精修时嵌入真实结果）")
        t_lines, _t_fs = fit_text(thumb_text, content_w - 2 * 12.0, NOTE_FS,
                                  8.0, max_lines=2,
                                  ctx=f"bands[{bi}].thumbnail", warnings=warnings)
        d.card(f"band{bi + 1}_thumb", label_html(t_lines),
               content_x0, cursor + HEADER_PAD + row_h + GAP_Y,
               content_w, THUMB_H, font_size=NOTE_FS, family=fam,
               dashed=True, bold=False)
        cursor += h
        if bi < n - 1:
            cursor += BAND_GAP
    # 5) 带间因果箭头（上一带输出 → 下一带输入; 族色取目标带）——
    #    全部色带建完后再连（连线端点须已注册）
    for bi in range(n - 1):
        d.edge(f"band{bi + 1}", f"band{bi + 2}",
               label=content["bands"][bi].get("causal_to_next", "").strip(),
               stroke=fams[bi + 1]["edge"], stroke_width=1.6,
               exit_dir="down", entry_dir="top")
    for w in warnings:
        print(f"[警告] {w}")
    return d


def _try_export_png(drawio_path: Path) -> bool:
    """调用 drawio CLI 导出 PNG 预览; 未装 CLI 时提示跳过, 返回是否成功。"""
    exe = shutil.which("drawio") or shutil.which("draw.io")
    if exe is None:
        print("[提示] 未找到 drawio CLI, 跳过 PNG 预览; .drawio 已交付, "
              "可在 draw.io 桌面/网页版打开后导出 PNG")
        return False
    png_path = drawio_path.with_suffix(".png")
    result = subprocess.run(
        [exe, "--export", "--format", "png", "--output", str(png_path),
         str(drawio_path)], check=False, capture_output=True, text=True)
    if result.returncode != 0 or not png_path.is_file():
        print(f"[提示] drawio CLI 导出失败: {result.stderr.strip() or result.stdout.strip()}")
        return False
    print(f"已输出: {png_path}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser: argparse.ArgumentParser = base_parser(
        "生成 draw.io 作战地图·三问题色带总览（示例数据, 输出可编辑 .drawio 草稿）")
    parser.add_argument("--content", default=None, metavar="JSON",
                        help="内容 JSON 文件路径（schema 见模块 docstring; "
                             "缺省用内置三问示例）")
    parser.add_argument("--png", action="store_true",
                        help="额外导出 PNG 预览（需要本机装有 drawio CLI）")
    args = parser.parse_args(argv)

    if args.content is None:
        content = DEMO_CONTENT
    else:
        path = Path(args.content).expanduser()
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[参数错误] 读取 content JSON 失败: {exc}")
            return 2
    try:
        diagram = build_graphical_abstract(content, palette=args.palette)
    except ValueError as exc:
        print(f"[参数错误] {exc}")
        return 2
    rc = finalize(diagram, args.out, DEFAULT_STEM)
    if rc == 0 and args.png:
        # args.out 为空时与 finalize 同源取缺省临时目录路径, 保证 PNG 落在
        # .drawio 旁边
        stem = (args.out if args.out is not None
                else default_out_stem(DEFAULT_STEM))
        out_drawio = (Path(stem) if str(stem).lower().endswith(".drawio")
                      else Path(str(stem) + ".drawio"))
        _try_export_png(out_drawio)
    return rc


if __name__ == "__main__":
    sys.exit(main())
