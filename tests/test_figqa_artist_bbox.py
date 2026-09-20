# -*- coding: utf-8 -*-
"""figqa 第七类 artist-bbox 相交检查的检出/豁免/阻断语义单测（A4）。

覆盖三起实战漏检的复现与豁免纪律:
  - S-10: inset 放大区整块盖住穿越点标注 → text-over-inset ❌
  - 色条刻度标签叠印（实测 0.15/0.20 叠 8.9px² 原不报）→ tick-label-overlap ❌
  - 图例框遮断参考线/曲线 → legend-over-line ⚠️ 仅提示, 不阻断退出码
  - 图例压标注 → text-over-legend ❌; 图例文本与他文本叠印 →
    legend-text-overlap ❌; 同一图例条目互检豁免、图例自家文本豁免自家框、
    inset 自家刻度豁免 inset 区域。
端到端: --strict 下 ❌ 退出码 1、纯 ⚠️ 退出码 0。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
FIGQA_PATH = SKILL_ROOT / "scripts" / "figqa.py"


def load_figqa():
    """加载 scripts/figqa.py（dataclass 须先注册进 sys.modules）。"""
    spec = importlib.util.spec_from_file_location("figqa_for_artist_bbox_tests", FIGQA_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ms_cjk_font_available() -> bool:
    """两个旋转标签用例的相交几何（>500/>1000 px²）源自 Windows 现场案例，
    依赖微软中文字体的字形度量；无微软字体（如 Linux CI 只有 Noto）时构造
    不出同等相交，跳过而非放宽断言。"""
    from matplotlib import font_manager
    names = {f.name for f in font_manager.fontManager.ttflist}
    return bool(names & {"Microsoft YaHei", "SimHei", "PingFang SC"})


class ArtistBboxTestCase(unittest.TestCase):
    """公共装置: Agg + 中文字体链 + analyze_figure 直调。"""

    @classmethod
    def setUpClass(cls):
        cls.figqa = load_figqa()
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        cls.figqa._setup_chinese_font(plt)
        cls.plt = plt

    @classmethod
    def tearDownClass(cls):
        cls.plt.close("all")

    def _analyze(self, fig, name="测试图"):
        return self.figqa.analyze_figure(fig, name)

    def _kinds(self, fig):
        return {c.kind for c in self._analyze(fig)}

    def _errors(self, fig):
        return [c for c in self._analyze(fig) if c.severity != self.figqa.SEV_WARN]

    # ---- 旋转刻度证据用例的公共小工具 ----
    def _max_adjacent_aabb_overlap(self, fig) -> float:
        """同轴相邻刻度标签的轴对齐包围盒最大交面积（px²）。"""
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        best = 0.0
        for _axis_name, labels in self.figqa._tick_label_runs(fig):
            boxes = [lb.get_window_extent(renderer) for lb in labels]
            for ba, bb in zip(boxes, boxes[1:]):
                best = max(best, self.figqa._overlap_area(ba, bb))
        return best

    def _ink_overlap_px(self, fig, i: int, j: int) -> int:
        """像素级真值: 只显示第 i / 第 j 个刻度标签各渲染一次, 数墨迹重叠像素。

        作为几何判据的独立对照（"真叠印"必须有真墨迹重叠, 不是算出来的）。
        """
        import numpy as np

        labels = fig.axes[0].get_xticklabels()

        def snap(show):
            for k, text in enumerate(labels):
                text.set_visible(k in show)
            fig.canvas.draw()
            arr = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
            for text in labels:
                text.set_visible(True)
            return arr

        base = snap(set())
        a = snap({i})
        b = snap({j})
        return int(((a != base).any(axis=2) & (b != base).any(axis=2)).sum())


class TextOverInsetTests(ArtistBboxTestCase):
    """7c: 文本被 inset 放大区盖住（S-10 复现）与自家文本豁免。"""

    def test_inset_covering_annotation_is_error(self):
        """主图标注被 inset 整块盖住 → text-over-inset ❌。"""
        fig, ax = self.plt.subplots(figsize=(6, 4))
        ax.plot([0.0, 1.0], [0.0, 1.0])
        ax.text(0.66, 0.66, "首次穿越 λ* = 57.5406", fontsize=11)
        axins = ax.inset_axes([0.60, 0.55, 0.36, 0.34])
        axins.plot([0.0, 1.0], [0.0, 1.0])
        try:
            hits = [c for c in self._analyze(fig)
                    if c.kind == self.figqa.KIND_TEXT_OVER_INSET]
            self.assertTrue(hits, "inset 盖标注未被报出")
            self.assertIn("首次穿越", hits[0].detail)
            for c in hits:
                self.assertNotEqual(c.severity, self.figqa.SEV_WARN)
        finally:
            self.plt.close(fig)

    def test_inset_own_texts_exempt(self):
        """正常布局: inset 自家刻度/文本落自家区域, 不报 text-over-inset。"""
        import numpy as np

        fig, ax = self.plt.subplots(figsize=(6, 4))
        x = np.linspace(0.0, 1.0, 60)
        ax.plot(x, x)
        ax.text(0.08, 0.86, "曲线斜率约 1", fontsize=10)  # 左上角, 离 inset 远
        axins = ax.inset_axes([0.60, 0.12, 0.36, 0.34])
        axins.plot(x, x)
        try:
            self.assertNotIn(self.figqa.KIND_TEXT_OVER_INSET, self._kinds(fig))
            self.assertFalse(self._errors(fig), f"干净图被误报: {self._errors(fig)}")
        finally:
            self.plt.close(fig)


class TextOverLegendTests(ArtistBboxTestCase):
    """7a/7b: 文本压图例框、图例文本叠印, 及图例内部豁免。"""

    def test_annotation_under_legend_is_error(self):
        """图例压住自由标注 → text-over-legend ❌。"""
        fig, ax = self.plt.subplots(figsize=(6, 4))
        ax.plot([0, 10], [0, 1], label="趋势线")
        ax.legend(loc="upper right")
        # transAxes 定位到图例框内部, 确保与图例 bbox 相交
        ax.text(0.83, 0.90, "峰值标注文本", transform=ax.transAxes,
                fontsize=11)
        try:
            hits = [c for c in self._analyze(fig)
                    if c.kind == self.figqa.KIND_TEXT_OVER_LEGEND]
            self.assertTrue(hits, "图例压标注未被报出")
            for c in hits:
                self.assertIn("峰值标注", c.detail)
        finally:
            self.plt.close(fig)

    def test_legend_internal_texts_exempt(self):
        """正常图例: 自家条目在自家框内、条目之间互不报。"""
        fig, ax = self.plt.subplots(figsize=(6, 4))
        import numpy as np

        x = np.linspace(0, 10, 30)
        ax.plot(x, np.sin(x), label="方案甲")
        ax.plot(x, np.cos(x), label="方案乙")
        ax.legend(loc="upper right", title="图例标题")
        try:
            self.assertNotIn(self.figqa.KIND_TEXT_OVER_LEGEND, self._kinds(fig))
            self.assertNotIn(self.figqa.KIND_LEGEND_TEXT_OVERLAP, self._kinds(fig))
            self.assertFalse(self._errors(fig), f"干净图被误报: {self._errors(fig)}")
        finally:
            self.plt.close(fig)

    def test_two_legends_overlapping_reports_text_overlap(self):
        """轴级图例与图级图例同位 → 图例间文本/框叠印必报其一 ❌。

        两图例完全同位时逐对文本互落对方框内, 7a 按压框报出后 7b 去重,
        故断言两种 kind 至少其一（不能重复计两条）。
        """
        import numpy as np

        fig, ax = self.plt.subplots(figsize=(6, 4))
        x = np.linspace(0, 10, 30)
        line, = ax.plot(x, np.sin(x))
        ax.legend([line], ["轴级图例条目"], loc="upper left")
        # 画布级图例精确锚到轴级图例正中（fig.legend 的 upper left 在画布
        # 角、位于轴区之外, 不锚定则两图例实际不相交）
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bb = ax.get_legend().get_window_extent(renderer)
        (fx0, fy0), (fx1, fy1) = fig.transFigure.inverted().transform(
            [(bb.x0, bb.y0), (bb.x1, bb.y1)])
        fig.legend([line], ["画布级图例条目"], loc="center",
                   bbox_to_anchor=((fx0 + fx1) / 2, (fy0 + fy1) / 2))
        try:
            kinds = self._kinds(fig)
            self.assertTrue(
                kinds & {self.figqa.KIND_TEXT_OVER_LEGEND,
                         self.figqa.KIND_LEGEND_TEXT_OVERLAP},
                f"两图例叠印未被报出, 实际 kinds={kinds}")
        finally:
            self.plt.close(fig)


class TickLabelOverlapTests(ArtistBboxTestCase):
    """7d: 同轴相邻刻度标签叠印（色条 0.15/0.20 叠 8.9px² 实测形态复现）。"""

    def test_colorbar_dense_tick_labels_reported(self):
        """色条刻度过密 → 相邻刻度标签叠印 ❌。

        复现实测形态: 色条刻度 0.15/0.20 两两叠印 8.9px²（刻度文本挂
        label2 侧, 修复前只查 label1 时漏检）。
        """
        fig, ax = self.plt.subplots(figsize=(4.2, 3.2))
        im = ax.imshow([[0.28, 0.30], [0.32, 0.34]])
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_ticks([0.300, 0.302, 0.304])
        cbar.set_ticklabels(["0.1500", "0.1550", "0.1600"])
        try:
            hits = [c for c in self._analyze(fig)
                    if c.kind == self.figqa.KIND_TICK_LABEL_OVERLAP]
            self.assertTrue(hits, "色条刻度叠印未被报出")
            self.assertTrue(any("0.1500" in c.detail for c in hits),
                            f"叠印明细异常: {[c.detail for c in hits]}")
            for c in hits:
                self.assertNotEqual(c.severity, self.figqa.SEV_WARN)
        finally:
            self.plt.close(fig)

    def test_normal_ticks_not_reported(self):
        """常规稀疏刻度不报。"""
        fig, ax = self.plt.subplots(figsize=(6, 4))
        ax.plot([0, 1, 2, 3], [0, 1, 0, 1])
        try:
            self.assertNotIn(self.figqa.KIND_TICK_LABEL_OVERLAP, self._kinds(fig))
        finally:
            self.plt.close(fig)

    @unittest.skipUnless(_ms_cjk_font_available(), "相交几何依赖微软中文字体度量")
    def test_rotated_long_tick_labels_not_reported(self):
        """旋转 35° 的长中文类别标签: 轴对齐 bbox 相交不算叠印（A 题 Q6_F2 假阳性）。

        旋转文本的 `get_window_extent` 是**轴对齐**包围盒, 相邻长标签必然相交而
        字形不重叠。用例先断言"包围盒确实大幅相交"（否则用例没踩中旋转路径）,
        再断言不报——判定改用真字形矩形换算, 见 RotatedTickLabelEvidenceTests。
        """
        fig, ax = self.plt.subplots(figsize=(4.0, 3.0))
        labels = ["示例参数一号", "示例参数二号", "示例量 $x_1$",
                  "示例参数三号", "示例参数四号"]
        ax.bar(range(len(labels)), [0.12, 0.73, -0.01, 0.08, 0.01])
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=35, ha="right")
        fig.tight_layout()
        try:
            self.assertGreater(self._max_adjacent_aabb_overlap(fig), 500.0,
                               "用例未踩中旋转包围盒相交场景")
            hits = [c for c in self._analyze(fig)
                    if c.kind == self.figqa.KIND_TICK_LABEL_OVERLAP]
            self.assertEqual([], hits, f"旋转标签被误报: {[c.detail for c in hits]}")
        finally:
            self.plt.close(fig)


class RotatedTickLabelEvidenceTests(ArtistBboxTestCase):
    """7d 旋转刻度: 真叠印才报 ❌（带角度/字号/DPI 证据）, 换算不可信只 ⚠️。

    背景: 判定旋转刻度叠印不能直接拿轴对齐包围盒（45° 时约放大 √2 倍）。
    实现把它换算回真字形矩形再求交（figqa._rotated_glyph_rect）。本组用例
    用**像素墨迹**做独立真值, 覆盖三种结局:
      - 真碰撞   → ❌ 且明细含角度/字号/DPI 证据;
      - 非碰撞   → 不报（包围盒大幅相交的前提下）;
      - 证据不足 → ⚠️（相邻两标签角度不同, 无法共坐标系）, 不阻断。
    """

    def test_real_rotated_collision_is_warning_with_evidence(self):
        """窄横轴 + 8 个 45° 短标签: 墨迹真的重叠, 但 figqa 无墨迹证据 → 只能 ⚠️。

        评审口径: 排版矩形相交 ≠ 墨迹相交（"I        I" 这类空白多的文本排版框
        交 455px² 而真实重叠 0 像素）, figqa 不做像素测量, 因此旋转标签一律提示,
        明细必须写明"排版矩形"与"无墨迹证据", 并且带角度/字号/DPI 证据。
        """
        fig, ax = self.plt.subplots(figsize=(1.6, 1.4))
        ax.imshow([[0.0] * 8] * 3)
        ax.set_xticks(range(8), ["甲乙丙丁戊"] * 8, rotation=45, ha="right")
        try:
            ink = [self._ink_overlap_px(fig, i, i + 1) for i in range(7)]
            self.assertTrue(all(v > 0 for v in ink),
                            f"用例未构造出真墨迹重叠: {ink}")
            hits = [c for c in self._analyze(fig)
                    if c.kind == self.figqa.KIND_TICK_LABEL_OVERLAP]
            self.assertTrue(hits, "旋转标签相交未提示")
            for c in hits:
                self.assertEqual(c.severity, self.figqa.SEV_WARN,
                                 f"旋转标签无墨迹证据却进了硬门: {c.detail}")
                self.assertIn("排版矩形", c.detail, f"措辞不准（应说排版矩形）: {c.detail}")
                self.assertIn("无墨迹证据", c.detail)
                self.assertIn("θ=45", c.detail, f"明细缺角度证据: {c.detail}")
                self.assertIn("pt", c.detail, f"明细缺字号证据: {c.detail}")
                self.assertIn("dpi", c.detail, f"明细缺 DPI 证据: {c.detail}")
        finally:
            self.plt.close(fig)

    def test_sparse_rotated_text_rects_overlap_but_no_ink(self):
        """评审复现场景: "I        I" 45° 相邻, 排版矩形交数百 px² 而墨迹零重叠。

        这条锁两件事: ① 即使排版框大幅相交也不许报 ❌（无墨迹证据）;
        ② 明细分母写明是排版矩形而不是"字形叠印"。
        """
        fig, ax = self.plt.subplots(figsize=(4.0, 3.0))
        ax.set_xlim(0.0, 1.0)
        ax.set_xticks([0.5, 0.52])
        ax.set_xticklabels(["I          I", "I          I"], rotation=45, ha="right")
        try:
            ink = self._ink_overlap_px(fig, 0, 1)
            self.assertEqual(ink, 0, "用例本意是零墨迹重叠")
            hits = [c for c in self._analyze(fig)
                    if c.kind == self.figqa.KIND_TICK_LABEL_OVERLAP]
            self.assertTrue(hits, "用例未踩中排版矩形相交场景（评审场景没测到）")
            for c in hits:
                self.assertEqual(c.severity, self.figqa.SEV_WARN,
                                 f"零墨迹重叠却报硬门: {c.detail}")
                self.assertIn("排版矩形", c.detail)
                self.assertNotIn("字形叠印", c.detail,
                                 "措辞把排版矩形说成了字形（评审指摘）")
                self.assertIn("无墨迹证据", c.detail)
                self.assertIn("pt", c.detail)
                self.assertIn("dpi", c.detail)
        finally:
            self.plt.close(fig)

    @unittest.skipUnless(_ms_cjk_font_available(), "相交几何依赖微软中文字体度量")
    def test_false_rotated_overlap_not_reported(self):
        """30° 斜排长标签: 包围盒相交 >1000px²、墨迹零重叠 → 不报。"""
        fig, ax = self.plt.subplots(figsize=(5.0, 3.0))
        ax.imshow([[0.0] * 5] * 3)
        ax.set_xticks(range(5), ["甲乙丙丁戊己庚辛"] * 5, rotation=30, ha="right")
        try:
            self.assertGreater(self._max_adjacent_aabb_overlap(fig), 1000.0,
                               "用例未踩中旋转包围盒大幅相交场景")
            self.assertEqual([0] * 4,
                             [self._ink_overlap_px(fig, i, i + 1) for i in range(4)],
                             "用例本意是零墨迹重叠")
            hits = [c for c in self._analyze(fig)
                    if c.kind == self.figqa.KIND_TICK_LABEL_OVERLAP]
            self.assertEqual([], hits, f"斜排假叠印被误报: {[c.detail for c in hits]}")
        finally:
            self.plt.close(fig)

    def test_mixed_angles_are_warning_not_hard_gate(self):
        """相邻标签角度不同（45°/12° 交错）: 换算不可信 → ⚠️, 绝不进硬门。"""
        fig, ax = self.plt.subplots(figsize=(2.0, 1.6), layout="constrained")
        ax.imshow([[0.0] * 6] * 3)
        ax.set_xticks(range(6), ["甲乙丙丁戊"] * 6)
        for text, deg in zip(ax.get_xticklabels(), (45, 12, 45, 12, 45, 12)):
            text.set_rotation(deg)
            text.set_ha("right")
        try:
            hits = [c for c in self._analyze(fig)
                    if c.kind == self.figqa.KIND_TICK_LABEL_OVERLAP]
            self.assertTrue(hits, "交错角度的相邻标签未被提示")
            for c in hits:
                self.assertEqual(c.severity, self.figqa.SEV_WARN,
                                 f"证据不足却进了硬门: {c.detail}")
                self.assertIn("不可信", c.detail)
        finally:
            self.plt.close(fig)


class LegendOverLineTests(ArtistBboxTestCase):
    """7e: 图例框压折线/参考线 → ⚠️ 提示, 不计入错误。"""

    def test_legend_over_reference_line_is_warning(self):
        """图例压住 axhline 参考线 → legend-over-line, severity=warn。"""
        import numpy as np

        fig, ax = self.plt.subplots(figsize=(6, 4))
        x = np.linspace(0, 10, 100)
        ax.plot(x, np.sin(x), label="曲线")
        ax.axhline(0.0, color="gray", linestyle="--", label="参考线")
        ax.legend(loc="center")
        try:
            hits = [c for c in self._analyze(fig)
                    if c.kind == self.figqa.KIND_LEGEND_OVER_LINE]
            self.assertTrue(hits, "图例压参考线未提示")
            for c in hits:
                self.assertEqual(c.severity, self.figqa.SEV_WARN)
            # ⚠️ 不产生任何 ❌ 级碰撞
            self.assertFalse(self._errors(fig), f"⚠️ 检查泄漏成 ❌: {self._errors(fig)}")
        finally:
            self.plt.close(fig)

    def test_legend_away_from_line_no_warning(self):
        """图例不压线时无提示（参考线居中、曲线上限远离左上角图例）。"""
        import numpy as np

        fig, ax = self.plt.subplots(figsize=(6, 4))
        x = np.linspace(0, 10, 100)
        ax.plot(x, np.sin(x) * 0.3 + 0.5, label="曲线")
        ax.axhline(0.0, color="red", linestyle="--", label="判据阈值")
        ax.set_ylim(-2.0, 2.0)  # 参考线压中位, 曲线峰值仅到 40% 高度
        ax.legend(loc="upper left")
        try:
            self.assertNotIn(self.figqa.KIND_LEGEND_OVER_LINE, self._kinds(fig))
        finally:
            self.plt.close(fig)


class CleanFigureTests(ArtistBboxTestCase):
    """干净图零误报（含全部第七类子检查）。"""

    def test_clean_figure_zero_errors(self):
        import numpy as np

        fig, ax = self.plt.subplots(figsize=(6, 4))
        x = np.linspace(0, 10, 30)
        ax.plot(x, np.sin(x), label="sin(x)")
        ax.plot(x, np.cos(x), label="cos(x)")
        ax.legend(loc="lower left")
        ax.set_title("干净示例图")
        ax.set_xlabel("x")
        ax.set_ylabel("值")
        try:
            collisions = self._analyze(fig)
            errors = [c for c in collisions if c.severity != self.figqa.SEV_WARN]
            self.assertFalse(errors, f"干净图被误报: {errors}")
        finally:
            self.plt.close(fig)


class CliExitSemanticsTests(unittest.TestCase):
    """端到端: 出图脚本经 figqa CLI 的 ❌/⚠️ 退出码语义。"""

    INSET_ERROR_FIGURE = """\
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot([0.0, 1.0], [0.0, 1.0])
ax.text(0.66, 0.66, "被 inset 盖住的标注")
axins = ax.inset_axes([0.60, 0.55, 0.36, 0.34])
axins.plot([0.0, 1.0], [0.0, 1.0])
"""

    LEGEND_OVER_LINE_ONLY_FIGURE = """\
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(figsize=(6, 4))
x = np.linspace(0, 10, 100)
ax.plot(x, np.sin(x), label="曲线")
ax.axhline(0.0, color="gray", linestyle="--", label="参考线")
ax.legend(loc="center")
"""

    def _run_figqa(self, source: str, *extra: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "fixture_fig.py"
            script.write_text(source, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(FIGQA_PATH), str(script), *extra],
                capture_output=True, text=True, check=False)

    def test_error_collision_fails_strict(self):
        result = self._run_figqa(self.INSET_ERROR_FIGURE, "--strict")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("text-over-inset", result.stdout)

    def test_error_collision_rc0_without_strict(self):
        result = self._run_figqa(self.INSET_ERROR_FIGURE)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_warning_only_passes_strict(self):
        """仅 ⚠️ 提示（图例压参考线）时 --strict 仍退出码 0。"""
        result = self._run_figqa(self.LEGEND_OVER_LINE_ONLY_FIGURE, "--strict")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("legend-over-line", result.stdout)
        self.assertIn("不阻断", result.stdout)


class DirectoryRunResilienceTests(unittest.TestCase):
    """目录级检测的两条纪律（评审指摘 3）:

      - 模板用 `sys.exit(非0)` 报缺依赖时, 只能算**该脚本失败**, 不得让整轮检测
        中断, 也不得被当成通过;
      - 脚本自己 `apply_style()` 改的全局 rcParams 不得带到下一个脚本（否则检测
        结果随脚本顺序漂移, 且不是真实出图状态）。
    """

    MISSING_DEP_FIGURE = """\
import sys
import matplotlib
matplotlib.use("Agg")
print("[依赖缺失] 本模板依赖 not_installed_lib")
sys.exit(3)
"""

    CLEAN_FIGURE = """\
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot([0, 1, 2, 3], [0, 1, 0, 1])
ax.set_xlabel("x")
ax.set_ylabel("y")
"""

    POLLUTING_FIGURE = """\
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.size"] = 42          # 巨大字号: 后一个脚本会跟着变形
fig, ax = plt.subplots(figsize=(6, 4))
ax.plot([0, 1, 2, 3], [0, 1, 0, 1])
"""

    def _run_dir(self, sources: dict, *extra: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as td:
            for name, source in sources.items():
                (Path(td) / name).write_text(source, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(FIGQA_PATH), td, *extra],
                capture_output=True, text=True, check=False)

    def test_systemexit_is_per_script_failure_not_abort(self):
        """缺依赖模板 sys.exit(3): 记为该脚本失败并继续跑下一个, 退出码 2（非 0）。"""
        result = self._run_dir({"a_missing_dep.py": self.MISSING_DEP_FIGURE,
                                "b_clean.py": self.CLEAN_FIGURE}, "--strict")
        self.assertEqual(result.returncode, 2,
                         f"缺依赖脚本必须判失败而不是通过:\n{result.stdout}")
        self.assertIn("执行失败", result.stdout)
        self.assertIn("exit=3", result.stdout)
        # 关键: 后一个脚本仍被检测（整轮没被 SystemExit 打断）
        self.assertIn("b_clean.py", result.stdout)
        self.assertIn("未检出碰撞", result.stdout)
        self.assertNotIn("b_clean.py\n  ❌", result.stdout)

    def test_rcparams_isolated_between_scripts(self):
        """前一个脚本把字号改到 42, 后一个脚本仍按干净样式出图（0 碰撞）。"""
        result = self._run_dir({"a_polluting.py": self.POLLUTING_FIGURE,
                                "b_clean.py": self.CLEAN_FIGURE}, "--strict")
        out = result.stdout
        second = out[out.find("b_clean.py"):]
        self.assertTrue(second, f"未跑到第二个脚本:\n{out}")
        self.assertIn("✅ 未检出碰撞", second,
                      f"rcParams 未隔离（后一个脚本被前一个的样式带崩）:\n{out}")
        self.assertNotIn("❌", second, f"后一个脚本被污染:\n{second}")


if __name__ == "__main__":
    unittest.main()
