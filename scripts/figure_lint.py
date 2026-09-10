# -*- coding: utf-8 -*-
"""图表设计规则 lint: 对出图脚本执行后审计 Axes/Figure 设计规则。

规则（每条附中文解释与修复建议）:
  R1 图例项数 > 5 警告, > 8 报错          -> 拆分子图或改直接标注
  R2 折线逐点 marker 且数据点 > 25 警告    -> 去掉 marker 或降密度
  R3 柱状图 y 轴未含 0 警告（log 轴除外）  -> set_ylim 下界归 0
  R4 已标数值的小矩阵热力图带 colorbar 警告 -> 二选一, 信息冗余
  R5 标题显示宽度过长（> 28 个中文字符当量）警告 -> 缩短或换行
  R6 使用 jet / rainbow colormap 报错      -> 换 viridis/RdBu_r 等感知均匀色
  R7 未去顶右 spines 警告                  -> 用 templates/figures/style/mathmodel.mplstyle
  R8 图内图题: 非空 suptitle 或单面板 set_title 报错, 多面板标题
     > 6 中文字符当量警告                   -> 图名应放在论文 caption, 不在图内;
                                              示意图等特殊版式用 --allow-infigure-title 跳过

用法:
    python scripts/figure_lint.py <figure.py 或目录> [--strict] [--allow-infigure-title]
    python scripts/figure_lint.py --self-test

退出码:
    0  无 rule 违例
    1  存在 error 级违例; --strict 时存在任何违例（含警告）
    2  输入不存在 / 出图脚本执行失败等致命错误
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from figqa import _setup_chinese_font, run_figure_script

STYLE_HINT = (
    "修复建议: plt.style.use(r'<skill>/templates/figures/style/mathmodel.mplstyle')"
)

LEGEND_WARN, LEGEND_ERROR = 5, 8
MARKER_POINT_LIMIT = 25
HEATMAP_MAX_CELLS = 16  # "小矩阵"判定: 标注单元数上限
TITLE_CJK_LIMIT = 28.0  # 中文字符当量
PANEL_TITLE_CJK_LIMIT = 6.0  # R8: 多面板 panel 标题中文字符当量上限
BAD_CMAPS = {"jet", "rainbow"}


@dataclass
class Violation:
    """一条规则违例。severity 取 'warn' 或 'error'。"""

    figure: str
    rule: str
    severity: str
    detail: str


def _cjk_width(text: str) -> float:
    """中文当量宽度: 全角字符计 1, 半角计 0.5。"""
    return sum(1.0 if ord(ch) > 0x2E80 else 0.5 for ch in text)


def _is_numeric_label(text: str) -> bool:
    token = text.strip().replace(",", "").replace("%", "")
    try:
        float(token)
    except ValueError:
        return False
    return True


def _axes_titles(ax) -> list[str]:
    """收集 axes 全部非空标题: center/left/right 三个位置各查一次, 去重保序。

    R5/R8 均不能只读居中标题——set_title(..., loc="left"/"right") 时
    get_title()（居中位）返回空串, 只查居中会漏检。
    """
    titles: list[str] = []
    for loc in ("center", "left", "right"):
        try:
            text = ax.get_title(loc=loc).strip()
        except Exception:
            text = ""
        if text and text not in titles:
            titles.append(text)
    return titles


def _is_colorbar_axes(ax) -> bool:
    """判定 colorbar 附属轴。

    fig.colorbar() 会向 fig.axes 追加一个附属轴; 若按 len(fig.axes) 数面板,
    单热力图 + colorbar 会被误判成双面板, 绕过 R8 单面板标题检查。
    判定信号按版本从新到旧回退（_colorbar 是私有属性, 不能只依赖它存在）:
    1. ax._colorbar 指向 Colorbar 实例（新版 mpl 在 colorbar 轴上挂该引用）;
    2. isinstance(ax, Colorbar)（部分版本 Colorbar 以 Axes 子类身份直接进 fig.axes）;
    3. 默认 label 恰为 '<colorbar>'（make_axes 的历史稳定默认值, 旧版 mpl 回退信号）。
    """
    from matplotlib.colorbar import Colorbar

    if isinstance(getattr(ax, "_colorbar", None), Colorbar):
        return True
    if isinstance(ax, Colorbar):
        return True
    try:
        return ax.get_label() == "<colorbar>"
    except Exception:
        return False


def _twinned_with(a, b) -> bool:
    """a 与 b 是否为 twinx/twiny 双轴关系（共享同一绘图区）。"""
    grouper = getattr(a, "_twinned_axes", None)
    if grouper is None:
        return False
    try:
        return b in grouper.get_siblings(a)
    except Exception:
        return False


def _count_logical_panels(fig) -> int:
    """统计逻辑面板数: 排除 colorbar 附属轴; twinx/twiny 双轴与其宿主算同一面板。

    R8 的单面板/多面板分支据此判定, 不能直接用 len(fig.axes)。
    """
    panels: list[list] = []
    for ax in fig.axes:
        if _is_colorbar_axes(ax):
            continue
        for panel in panels:
            if any(_twinned_with(member, ax) for member in panel):
                panel.append(ax)
                break
        else:
            panels.append([ax])
    return len(panels)


def lint_figure(fig, name: str, allow_infigure_title: bool = False) -> list[Violation]:
    """对单个 Figure 执行全部规则, 返回违例列表。

    allow_infigure_title: True 时跳过 R8 图内图题规则（示意图/特殊版式逃生门）。
    """
    out: list[Violation] = []

    def add(rule: str, severity: str, detail: str) -> None:
        out.append(Violation(name, rule, severity, detail))

    has_colorbar = any(
        getattr(ax, "_colorbar", None) is not None for ax in fig.axes
    )

    for ax in fig.axes:
        # R1 图例项数
        legend = ax.get_legend()
        if legend is not None:
            n = len(legend.get_texts())
            if n > LEGEND_ERROR:
                add("R1-图例项数", "error", f"图例 {n} 项 (> {LEGEND_ERROR}), 评委阅读负担过重; 建议拆子图或直接标注")
            elif n > LEGEND_WARN:
                add("R1-图例项数", "warn", f"图例 {n} 项 (> {LEGEND_WARN}); 建议精简")

        # R2 逐点 marker 且点数过多
        for ln in ax.lines:
            xy = ln.get_xydata()
            if ln.get_marker() not in ("", "None", None, "none") and len(xy) > MARKER_POINT_LIMIT:
                add(
                    "R2-逐点marker",
                    "warn",
                    f'折线 "{ln.get_label()[:20]}" {len(xy)} 个点仍逐点 marker, 300dpi 下糊成串; '
                    "建议去掉 marker 或抽样",
                )

        # R3 柱状图 y 轴未含 0
        from matplotlib.container import BarContainer

        has_bars = any(isinstance(c, BarContainer) for c in ax.containers)
        ymin, _ = ax.get_ylim()
        if has_bars and ax.get_yscale() != "log" and ymin > 1e-9:
            add(
                "R3-柱图截零",
                "warn",
                f"柱状图 y 轴下界 {ymin:.3g} > 0, 截零柱高会夸大差异; log 轴除外, 建议下界归 0",
            )

        # R4 已标数值的小矩阵热力图 + colorbar 冗余
        images = list(ax.get_images()) + [
            c for c in ax.collections if type(c).__name__ == "QuadMesh"
        ]
        numeric_texts = [t for t in ax.texts if _is_numeric_label(t.get_text())]
        if images and 0 < len(numeric_texts) <= HEATMAP_MAX_CELLS and has_colorbar:
            add(
                "R4-热图colorbar冗余",
                "warn",
                f"小矩阵热力图已逐格标注 {len(numeric_texts)} 个数值又带 colorbar, 信息冗余; 建议二选一",
            )

        # R6 jet / rainbow colormap
        for artist in images:
            cmap = getattr(artist, "get_cmap", lambda: None)()
            if cmap is not None and cmap.name.lower() in BAD_CMAPS:
                add(
                    "R6-劣质cmap",
                    "error",
                    f"使用 {cmap.name} colormap, 亮度不单调且对色盲不友好; "
                    "建议 viridis（连续）或 RdBu_r（发散）",
                )

        # R7 去顶右 spines
        # 注: 极坐标(PolarAxes)的 spines 只有 polar/start/end/inner, 无 top/right,
        # 用 get() 容错跳过; 雷达图等极坐标图不适用此规则。
        visible = [
            k for k in ("top", "right")
            if k in ax.spines and ax.spines[k].get_visible()
        ]
        if visible:
            add(
                "R7-spines",
                "warn",
                f"顶/右 spines 未去除 ({'/'.join(visible)}); {STYLE_HINT}",
            )

    # R5 标题过宽
    titles = []
    for ax in fig.axes:
        titles.extend(_axes_titles(ax))  # center/left/right 三位置全查
    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is not None and suptitle.get_text().strip():
        titles.append(suptitle.get_text())
    for title in titles:
        width = _cjk_width(title)
        if width > TITLE_CJK_LIMIT:
            add(
                "R5-标题过宽",
                "warn",
                f"标题显示宽度 {width:.1f} 当量字符 (> {TITLE_CJK_LIMIT:g}): “{title[:30]}…”; "
                "建议缩短或拆两行",
            )

    # R8 图内图题: 图名应放在论文 caption（"图 X …"题注）, 不在图内。
    # 数据图纪律; 示意图/特殊版式可用 --allow-infigure-title 跳过本规则。
    if not allow_infigure_title:
        suptitle = getattr(fig, "_suptitle", None)
        if suptitle is not None and suptitle.get_text().strip():
            add(
                "R8-图内图题",
                "error",
                f"图内出现 suptitle “{suptitle.get_text()[:30]}”: 图名应放在论文 caption, "
                "不在图内; 示意图等特殊版式可用 --allow-infigure-title 跳过",
            )
        n_panels = _count_logical_panels(fig)
        for ax in fig.axes:
            for title in _axes_titles(ax):
                if n_panels == 1:
                    add(
                        "R8-图内图题",
                        "error",
                        f"单面板图内出现标题 “{title[:30]}”: 图名应放在论文 caption, "
                        "不在图内; 示意图等特殊版式可用 --allow-infigure-title 跳过",
                    )
                else:
                    width = _cjk_width(title)
                    if width > PANEL_TITLE_CJK_LIMIT:
                        add(
                            "R8-图内图题",
                            "warn",
                            f"多面板 panel 标题 “{title[:30]}” 宽 {width:.1f} 当量字符 "
                            f"(> {PANEL_TITLE_CJK_LIMIT:g}), 只允许短轴含义标签（如 ROC/PR/残差）; "
                            "图名放论文 caption",
                        )
    return out


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


def print_report(script: Path, violations: list[Violation]) -> None:
    print(f"\n[脚本] {script}")
    if not violations:
        print("  ✅ 无违例")
        return
    for v in violations:
        mark = "❌" if v.severity == "error" else "⚠️ "
        print(f"  {mark} {v.rule}({v.severity}): {v.detail}  [图: {v.figure}]")


def check_path(target: Path, strict: bool, allow_infigure_title: bool = False) -> int:
    """检测单个脚本或目录, 返回退出码。

    allow_infigure_title: True 时跳过 R8 图内图题规则（示意图/特殊版式逃生门）。
    """
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
    all_violations: list[Violation] = []
    failures = 0
    for script in scripts:
        try:
            figures = run_figure_script(script)
        except Exception as exc:
            print(f"\n[脚本] {script}\n  ❌ 执行失败: {exc}")
            failures += 1
            continue
        script_violations: list[Violation] = []
        for idx, fig in enumerate(figures):
            script_violations.extend(lint_figure(
                fig, _figure_name(fig, idx, script),
                allow_infigure_title=allow_infigure_title))
            plt.close(fig)
        print_report(script, script_violations)
        all_violations.extend(script_violations)
    errors = [v for v in all_violations if v.severity == "error"]
    warns = [v for v in all_violations if v.severity == "warn"]
    print(f"\n共检测 {len(scripts) - failures} 个脚本: {len(errors)} 错误, {len(warns)} 警告。")
    if failures:
        return 2
    if errors or (strict and all_violations):
        return 1
    return 0


def _self_test() -> int:
    """合成图验证 8 条规则均可触发、正确图零误报。"""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    _setup_chinese_font(plt)
    violations: dict[str, list[Violation]] = {}

    # 触发 R1/R2/R3/R6/R7/R8(suptitle) 的图
    fig, ax = plt.subplots(figsize=(6, 4))
    for i in range(9):
        ax.plot(np.linspace(0, 1, 40), label=f"序列{i}", marker="o")
    ax.bar([0.5], [5])
    ax.set_ylim(3, 5)
    im = ax.imshow(np.random.rand(2, 2), cmap="jet", extent=[0, 1, 0, 1], aspect="auto")
    fig.colorbar(im)
    ax.legend()
    fig.suptitle("不该出现的图内总标题")  # R8: suptitle -> error
    violations["bad"] = lint_figure(fig, "规则触发图")
    plt.close(fig)

    # 触发 R4 的小矩阵热力图 + colorbar
    fig, ax = plt.subplots()
    data = np.random.rand(3, 3)
    im = ax.imshow(data, cmap="viridis")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center")
    fig.colorbar(im)
    violations["heatmap"] = lint_figure(fig, "热力图冗余")
    plt.close(fig)

    # 触发 R5 的超长标题
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    ax.set_title("这是一段特别特别特别特别特别特别特别特别长的论文图表标题用来触发规则五")
    violations["title"] = lint_figure(fig, "长标题图")
    plt.close(fig)

    # 正确图: 应零违例（单面板不放图内标题, 图名进 caption）
    fig, ax = plt.subplots()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.plot(np.linspace(0, 1, 10), marker="o", label="仅一例")
    ax.bar([0.2], [1])
    ax.set_ylim(0, None)
    ax.legend()
    violations["clean"] = lint_figure(fig, "干净图")
    plt.close(fig)

    ok = True
    rules_hit = {v.rule.split("-")[0] for v in violations["bad"] + violations["heatmap"] + violations["title"]}
    for rule_id in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"):
        if rule_id not in rules_hit:
            print(f"[自测] ❌ 规则 {rule_id} 未被触发")
            ok = False
        else:
            print(f"[自测] ✅ 规则 {rule_id} 已触发")
    if violations["clean"]:
        print(f"[自测] ❌ 干净图被误报 {len(violations['clean'])} 处:")
        for v in violations["clean"]:
            print(f"        {v.rule}: {v.detail}")
        ok = False
    else:
        print("[自测] ✅ 干净图 0 误报")
    print("[自测] " + ("全部通过 ✅" if ok else "存在失败 ❌"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="图表设计规则 lint: 图例密度/marker/截零/colorbar 冗余/标题宽度/cmap/spines/图内图题"
    )
    parser.add_argument("target", nargs="?", help="figure.py 脚本或其所在目录")
    parser.add_argument("--strict", action="store_true", help="警告也计入失败")
    parser.add_argument("--allow-infigure-title", action="store_true",
                        help="跳过 R8 图内图题规则（示意图/特殊版式逃生门）")
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
    return check_path(target, args.strict,
                      allow_infigure_title=args.allow_infigure_title)


if __name__ == "__main__":
    sys.exit(main())
