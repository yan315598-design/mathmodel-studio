# -*- coding: utf-8 -*-
"""图表渲染碰撞检测（figure QA）。

对出图脚本逐一执行（runpy, Agg 后端）, 渲染后收集 Figure 内文本/图例/
色块/折线/散点的像素级 bounding box, 检测六类常见排版碰撞:

  1. text-over-patch        文本压在柱形/色块上（数值标签完全落在宿主柱内时豁免）
  2. legend-over-patch      图例框压住柱形/色块
  3. line-through-text      折线穿过文本框（线段-矩形求交用 Liang-Barsky 裁剪算法）
  4. point-under-text       数据点（marker/散点）落在文本框下
  5. text-over-text         文本框互相重叠（同一坐标轴的相邻刻度标签豁免）
  6. clipped-out-of-figure  文本/图例超出画布边界被裁掉

语义参照公开的 "bounding-box overlap QA" 思路, 全部自写实现。

用法:
    python scripts/figqa.py <figure.py 或目录> [--strict]
    python scripts/figqa.py --self-test

--strict 时只要检出任何碰撞即退出码 1, 便于接 CI/提交流水线。

退出码:
    0  未检出碰撞, 或 --self-test 全部通过
    1  --strict 下检出碰撞; --self-test 期望不满足
    2  输入不存在 / 出图脚本执行失败等致命错误

已知限制:
    - 文本-色块检测只覆盖 ax.patches（柱形 Rectangle/多边形）,
      imshow/QuadMesh 热力图上的数值标注（有意为之的常见用法）不在检测范围;
    - 刻度标签与网格线不参与 line-through-text / point-under-text;
    - 阴影区（axhspan）内放文字会被按 text-over-patch 报出。
"""

from __future__ import annotations

import argparse
import runpy
import sys
from dataclasses import dataclass
from pathlib import Path

# 容差常量: 重叠面积小于 MIN_AREA_PX 视为噪声; 求交前把文本框四边内缩
# INSET_PX, 避免贴边/切线级别的接触被误报。
MIN_AREA_PX = 2.0
INSET_PX = 0.75
# 越界检测专用: matplotlib 默认布局下刻度/轴标签常有 <5px 的画布微越界,
# 且 skill 标准样式 savefig.bbox=tight 落盘时会自动扩边收回, 不算真裁剪;
# 自由文本/图例仍按 INSET_PX 严格判。
CLIP_TOLERANCE_MANAGED_PX = 5.0

KIND_TEXT_OVER_PATCH = "text-over-patch"
KIND_LEGEND_OVER_PATCH = "legend-over-patch"
KIND_LINE_THROUGH_TEXT = "line-through-text"
KIND_POINT_UNDER_TEXT = "point-under-text"
KIND_TEXT_OVER_TEXT = "text-over-text"
KIND_CLIPPED = "clipped-out-of-figure"

KIND_CN = {
    KIND_TEXT_OVER_PATCH: "文本压色块",
    KIND_LEGEND_OVER_PATCH: "图例压色块",
    KIND_LINE_THROUGH_TEXT: "折线穿文本",
    KIND_POINT_UNDER_TEXT: "数据点压文本",
    KIND_TEXT_OVER_TEXT: "文本互相重叠",
    KIND_CLIPPED: "越界被裁剪",
}


@dataclass
class Collision:
    """一条碰撞记录。position 为重叠区中心或文本框中心（像素, 左下原点）。"""

    figure: str
    kind: str
    detail: str
    position: tuple[float, float]


# ============================================================
# 几何工具（教科书算法, 自实现）
# ============================================================
def _shrink(bbox, inset: float):
    """把 bbox 四边各内缩 inset 像素, 返回 (x0, y0, x1, y1)。"""
    return (
        bbox.x0 + inset,
        bbox.y0 + inset,
        bbox.x1 - inset,
        bbox.y1 - inset,
    )


def _overlap_area(a, b) -> float:
    """两个 bbox 的重叠面积; 不相交返回 0。"""
    w = min(a.x1, b.x1) - max(a.x0, b.x0)
    h = min(a.y1, b.y1) - max(a.y0, b.y0)
    if w <= 0 or h <= 0:
        return 0.0
    return w * h


def _rect_contains(outer, inner) -> bool:
    """inner 是否完全落在 outer 内（含等号）。"""
    return (
        outer.x0 <= inner.x0 and outer.y0 <= inner.y0
        and outer.x1 >= inner.x1 and outer.y1 >= inner.y1
    )


def _point_in_rect(px: float, py: float, rect) -> bool:
    return rect[0] <= px <= rect[2] and rect[1] <= py <= rect[3]


def liang_barsky_clip(p1, p2, rect):
    """Liang-Barsky 线段裁剪: 求线段 p1-p2 与矩形 rect 的可见部分。

    Args:
        p1, p2: 线段两端点 (x, y)。
        rect: 矩形 (xmin, ymin, xmax, ymax)。

    Returns:
        裁剪后的两端点元组; 线段与矩形无交则返回 None。
    """
    x1, y1 = p1
    x2, y2 = p2
    xmin, ymin, xmax, ymax = rect
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - xmin), (dx, xmax - x1), (-dy, y1 - ymin), (dy, ymax - y1)):
        if p == 0.0:
            if q < 0.0:
                return None
        else:
            r = q / p
            if p < 0.0:
                if r > t1:
                    return None
                if r > t0:
                    t0 = r
            else:
                if r < t0:
                    return None
                if r < t1:
                    t1 = r
    return (x1 + t0 * dx, y1 + t0 * dy), (x1 + t1 * dx, y1 + t1 * dy)


def _is_numeric_label(text: str) -> bool:
    """数值标签启发式: 去掉千分位逗号/百分号/单位空白后可解析为 float。"""
    token = text.strip().replace(",", "").replace("%", "")
    try:
        float(token)
    except ValueError:
        return False
    return True


def _center(bbox) -> tuple[float, float]:
    return ((bbox.x0 + bbox.x1) / 2.0, (bbox.y0 + bbox.y1) / 2.0)


# ============================================================
# 脚本执行与 Figure 收集
# ============================================================
def run_figure_script(script: Path) -> list:
    """在当前进程执行出图脚本, 返回其创建的全部 Figure 对象列表。

    通过临时替换 Figure.__init__ 登记新建对象, 覆盖 plt.figure /
    plt.subplots / 直接实例化 Figure 等全部创建路径; 脚本内部 plt.close
    只解除 pyplot 管理, Figure 及其 canvas 引用仍可用, 渲染分析不受影响。
    """
    import matplotlib.figure as mfigure

    created: list = []
    orig_init = mfigure.Figure.__dict__["__init__"]

    def _recording_init(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        created.append(self)

    mfigure.Figure.__init__ = _recording_init
    saved_argv = sys.argv
    sys.argv = [str(script)]  # 目标脚本的 argparse 不应看到 figqa 自己的参数
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as exc:  # 脚本里 sys.exit(0) 属正常结束
        if exc.code not in (None, 0):
            raise
    finally:
        mfigure.Figure.__init__ = orig_init
        sys.argv = saved_argv
    return created


# ============================================================
# 单图检测
# ============================================================
def _setup_chinese_font(plt) -> None:
    """给 Agg 渲染注入中文回退字体链, 与 mathmodel.mplstyle 约定一致。

    缺中文字形时 CJK 文本会被画成方框, 像素 bbox 测量失真。
    """
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei", "SimHei", "PingFang SC", "Arial Unicode MS",
        "Arial", "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def _visible_tick_texts(ax):
    """取真实可见的刻度标签文本对象。

    get_xticklabels() 会返回 locator 生成的全部刻度, 含视图区间外
    不会被绘制的"幽灵刻度"（其 bbox 常在画布外）, 必须按位置过滤;
    axis("off") 的坐标轴同样整组跳过。
    """
    texts = []
    if not getattr(ax, "axison", True):
        return texts
    for axis in (ax.xaxis, ax.yaxis):
        lo, hi = axis.get_view_interval()
        if lo > hi:
            lo, hi = hi, lo
        for tick in axis.get_major_ticks():
            loc = tick.get_loc()
            if loc is None or not (lo - 1e-9 <= loc <= hi + 1e-9):
                continue
            for label in (tick.label1, tick.label2):
                if (
                    label is not None
                    and label.get_visible()
                    and label.get_text().strip()
                ):
                    texts.append(label)
    return texts


def _collect_texts(fig, renderer):
    """收集图内全部文本的 (artist, bbox, 组别)。组别用于文本互压豁免。"""
    items = []
    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is not None and suptitle.get_text().strip():
        items.append((suptitle, suptitle.get_window_extent(renderer), "suptitle"))
    for ax in fig.axes:
        candidates = [(a, "axes-text") for a in ax.texts]  # 含 Annotation
        for artist in (ax.xaxis.label, ax.yaxis.label):
            if artist is not None and artist.get_text().strip():
                candidates.append((artist, "axis-label"))
        if ax.get_title().strip():
            candidates.append((ax.title, "axes-text"))
        candidates.extend((a, "tick") for a in _visible_tick_texts(ax))
        for artist, role in candidates:
            if not artist.get_text().strip():
                continue
            try:
                bbox = artist.get_window_extent(renderer)
            except Exception:
                continue
            items.append((artist, bbox, role))
    return items


def _figure_name(fig, index: int, script: Path) -> str:
    for getter in (
        lambda: fig._suptitle.get_text() if getattr(fig, "_suptitle", None) else "",
        lambda: fig.axes[0].get_title() if fig.axes else "",
    ):
        try:
            text = getter().strip()
        except Exception:
            text = ""
        if text:
            return text[:40]
    return f"{script.name}#图{index + 1}"


def analyze_figure(fig, name: str, script: Path | None = None,
                   allow_box_labels: bool = False) -> list[Collision]:
    """渲染单个 Figure 并返回检出的碰撞列表。

    Args:
        allow_box_labels: 豁免"完全落在单个色块内"的文本（流程图/示意图的
            盒内标签是有意设计）; 默认 False 保持严格语义（数值标签豁免仍生效）。
    """
    import numpy as np

    script = script or Path(name)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    collisions: list[Collision] = []

    texts = _collect_texts(fig, renderer)
    patches = []
    lines = []
    markers = []  # (artist, display_points)
    legends = []
    for ax in fig.axes:
        for patch in ax.patches:
            try:
                patches.append((patch, patch.get_window_extent(renderer)))
            except Exception:
                continue
        for ln in ax.lines:
            xy = ln.get_xydata()
            if xy is None or len(xy) < 1:
                continue
            pts = ax.transData.transform(np.asarray(xy, dtype=float))
            if ln.get_linestyle() not in ("None", "", None) and len(pts) >= 2:
                lines.append((ln, pts))
            if ln.get_marker() not in ("", "None", None, "none"):
                markers.append((ln, pts))
        from matplotlib.collections import PathCollection

        for coll in ax.collections:
            if not isinstance(coll, PathCollection):
                continue
            offsets = np.asarray(coll.get_offsets())
            if len(offsets) == 0:
                continue
            transform = coll.get_offset_transform()
            markers.append((coll, transform.transform(offsets)))
        legend = ax.get_legend()
        if legend is not None:
            try:
                legends.append((legend, legend.get_window_extent(renderer)))
            except Exception:
                continue

    # --- 1. text-over-patch（数值标签完全落在宿主柱内时豁免） ---
    def _contained_in_exactly_one_patch(bbox) -> bool:
        return sum(1 for _p, pb in patches if _rect_contains(pb, bbox)) == 1

    for artist, bbox, _role in texts:
        for patch, pbox in patches:
            if _overlap_area(bbox, pbox) < MIN_AREA_PX:
                continue
            if _is_numeric_label(artist.get_text()) and _rect_contains(pbox, bbox):
                continue  # 柱内数值标签, 有意为之
            if allow_box_labels and _contained_in_exactly_one_patch(bbox):
                continue  # 流程图/示意图的盒内标签, 有意为之
            area = _overlap_area(bbox, pbox)
            collisions.append(
                Collision(
                    name,
                    KIND_TEXT_OVER_PATCH,
                    f'文本 "{artist.get_text()[:24]}" 与色块重叠 {area:.0f}px²',
                    _center(bbox),
                )
            )
            break

    # --- 2. legend-over-patch ---
    for legend, lbox in legends:
        for patch, pbox in patches:
            area = _overlap_area(lbox, pbox)
            if area < MIN_AREA_PX:
                continue
            collisions.append(
                Collision(
                    name,
                    KIND_LEGEND_OVER_PATCH,
                    f'图例（{len(legend.get_texts())} 项）与色块重叠 {area:.0f}px²',
                    _center(lbox),
                )
            )
            break

    # --- 3. line-through-text ---
    for ln, pts in lines:
        segs = list(zip(pts[:-1], pts[1:]))
        for artist, bbox, _role in texts:
            rect = _shrink(bbox, INSET_PX)
            if rect[0] >= rect[2] or rect[1] >= rect[3]:
                continue
            hit = any(
                liang_barsky_clip(s[0], s[1], rect) is not None for s in segs
            )
            if hit:
                collisions.append(
                    Collision(
                        name,
                        KIND_LINE_THROUGH_TEXT,
                        f'折线 "{ln.get_label()[:24]}" 穿过文本 '
                        f'"{artist.get_text()[:24]}"',
                        _center(bbox),
                    )
                )

    # --- 4. point-under-text ---
    for artist, pts in markers:
        flat = [(float(x), float(y)) for x, y in pts]
        for text_artist, bbox, _role in texts:
            rect = _shrink(bbox, INSET_PX)
            if rect[0] >= rect[2] or rect[1] >= rect[3]:
                continue
            count = sum(1 for px, py in flat if _point_in_rect(px, py, rect))
            if count:
                label = getattr(artist, "get_label", lambda: "")() or "散点"
                collisions.append(
                    Collision(
                        name,
                        KIND_POINT_UNDER_TEXT,
                        f'"{label}" 的 {count} 个数据点落在文本 '
                        f'"{text_artist.get_text()[:24]}" 下',
                        _center(bbox),
                    )
                )

    # --- 5. text-over-text（同组刻度标签互相豁免） ---
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a_artist, a_box, a_role = texts[i]
            b_artist, b_box, b_role = texts[j]
            if a_role == b_role == "tick":
                continue  # 同轴刻度由 locator 自动排布
            area = _overlap_area(a_box, b_box)
            if area < MIN_AREA_PX:
                continue
            collisions.append(
                Collision(
                    name,
                    KIND_TEXT_OVER_TEXT,
                    f'文本 "{a_artist.get_text()[:20]}" 与 '
                    f'"{b_artist.get_text()[:20]}" 重叠 {area:.0f}px²',
                    (
                        (max(a_box.x0, b_box.x0) + min(a_box.x1, b_box.x1)) / 2.0,
                        (max(a_box.y0, b_box.y0) + min(a_box.y1, b_box.y1)) / 2.0,
                    ),
                )
            )

    # --- 6. clipped-out-of-figure ---
    fb = fig.bbox
    candidates = [
        (
            a,
            b,
            "文本",
            CLIP_TOLERANCE_MANAGED_PX if role in ("tick", "axis-label") else INSET_PX,
        )
        for a, b, role in texts
    ]
    candidates += [(l, b, "图例", INSET_PX) for l, b in legends]
    for artist, bbox, what, tol in candidates:
        if (
            bbox.x0 < fb.x0 - tol or bbox.y0 < fb.y0 - tol
            or bbox.x1 > fb.x1 + tol or bbox.y1 > fb.y1 + tol
        ):
            text = artist.get_text()[:24] if hasattr(artist, "get_text") else ""
            collisions.append(
                Collision(
                    name,
                    KIND_CLIPPED,
                    f"{what} {('`' + text + '`') if text else ''} 超出画布边界",
                    _center(bbox),
                )
            )
    return collisions


# ============================================================
# 报告
# ============================================================
def print_report(script: Path, collisions: list[Collision]) -> None:
    by_kind: dict[str, list[Collision]] = {}
    for c in collisions:
        by_kind.setdefault(c.kind, []).append(c)
    print(f"\n[脚本] {script}")
    if not collisions:
        print("  ✅ 未检出碰撞")
        return
    for kind in (
        KIND_TEXT_OVER_PATCH,
        KIND_LEGEND_OVER_PATCH,
        KIND_LINE_THROUGH_TEXT,
        KIND_POINT_UNDER_TEXT,
        KIND_TEXT_OVER_TEXT,
        KIND_CLIPPED,
    ):
        for c in by_kind.get(kind, []):
            print(
                f"  ❌ {kind}（{KIND_CN[kind]}）: {c.detail}"
                f" @ ({c.position[0]:.0f}, {c.position[1]:.0f})px"
                f"  [图: {c.figure}]"
            )


def check_path(target: Path, strict: bool, allow_box_labels: bool = False) -> int:
    """检测单个脚本或目录下全部 .py 出图脚本, 返回退出码。"""
    if target.is_dir():
        scripts = sorted(p for p in target.glob("*.py") if p.name != "__init__.py")
    else:
        scripts = [target]
    if not scripts:
        print(f"输入不存在或目录无 .py 脚本: {target}")
        return 2
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _setup_chinese_font(plt)
    total = 0
    failures = 0
    for script in scripts:
        try:
            figures = run_figure_script(script)
        except Exception as exc:  # 出图脚本自身失败属于致命错误
            print(f"\n[脚本] {script}\n  ❌ 执行失败: {exc}")
            failures += 1
            continue
        collisions: list[Collision] = []
        for idx, fig in enumerate(figures):
            try:
                collisions.extend(
                    analyze_figure(
                        fig, _figure_name(fig, idx, script), script,
                        allow_box_labels=allow_box_labels,
                    )
                )
            finally:
                plt.close(fig)
        print_report(script, collisions)
        total += len(collisions)
    print(f"\n共检测 {len(scripts) - failures} 个脚本, 检出 {total} 处碰撞。")
    if failures:
        return 2
    if total and strict:
        return 1
    return 0


# ============================================================
# 自测
# ============================================================
def _self_test() -> int:
    """内置 3 张合成图验证检出能力: 干净图/文字压线图/图例压柱图。"""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    _setup_chinese_font(plt)

    def make_clean():
        fig, ax = plt.subplots(figsize=(6, 4))
        x = np.linspace(0, 10, 30)
        ax.plot(x, np.sin(x), label="sin(x)")
        ax.plot(x, np.cos(x), label="cos(x)")
        ax.legend(loc="lower left")
        ax.set_title("干净示例图")
        ax.set_xlabel("x")
        ax.set_ylabel("值")
        return fig

    def make_text_over_line():
        fig, ax = plt.subplots(figsize=(6, 4))
        x = np.linspace(0, 10, 200)
        ax.plot(x, 5 * x, label="趋势线")
        ax.text(4.2, 22, "关键转折", fontsize=12)  # 压在陡峭线段上
        ax.set_title("文字压线示例")
        return fig

    def make_legend_over_bar():
        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar([0, 1, 2, 3], [9, 9.5, 9.2, 9.4], width=0.6)
        for rect in bars:  # 柱内数值标签: 应被豁免, 不产生 text-over-patch
            ax.text(
                rect.get_x() + rect.get_width() / 2,
                rect.get_height() - 0.8,
                f"{rect.get_height():.1f}",
                ha="center",
                color="white",
            )
        ax.set_ylim(0, 10)
        ax.legend(["方案 A"], loc="upper center")  # 压在高柱上
        ax.set_title("图例压柱示例")
        return fig

    ok = True
    for name, factory, expect_kind in (
        ("干净图", make_clean, None),
        ("文字压线图", make_text_over_line, KIND_LINE_THROUGH_TEXT),
        ("图例压柱图", make_legend_over_bar, KIND_LEGEND_OVER_PATCH),
    ):
        fig = factory()
        collisions = analyze_figure(fig, name)
        plt.close(fig)
        kinds = {c.kind for c in collisions}
        detail = "; ".join(f"{c.kind}: {c.detail}" for c in collisions) or "无"
        print(f"[自测] {name}: {detail}")
        if expect_kind is None:
            if collisions:
                print(f"  ❌ 干净图被误报 {len(collisions)} 处")
                ok = False
            else:
                print("  ✅ 干净图 0 误报")
        else:
            if expect_kind not in kinds:
                print(f"  ❌ 未检出期望的 {expect_kind}")
                ok = False
            else:
                print(f"  ✅ 检出 {expect_kind}")
            if KIND_TEXT_OVER_PATCH in kinds:
                print("  ❌ 柱内数值标签未被豁免, 出现 text-over-patch 误报")
                ok = False
    print("[自测] " + ("全部通过 ✅" if ok else "存在失败 ❌"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="图表渲染碰撞检测: 执行出图脚本并检查六类像素级排版碰撞"
    )
    parser.add_argument("target", nargs="?", help="figure.py 脚本或其所在目录")
    parser.add_argument("--strict", action="store_true", help="检出碰撞时退出码 1")
    parser.add_argument(
        "--allow-box-labels",
        action="store_true",
        help="豁免完全落在单个色块内的文本（流程图/示意图盒内标签）",
    )
    parser.add_argument("--self-test", action="store_true", help="内置合成图自测")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()
    if not args.target:
        parser.error("需要提供 figure.py 或目录, 或使用 --self-test")
    target = Path(args.target).expanduser()
    if not target.exists():
        print(f"输入不存在: {target}")
        return 2
    return check_path(target, args.strict, args.allow_box_labels)


if __name__ == "__main__":
    sys.exit(main())
