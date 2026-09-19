# -*- coding: utf-8 -*-
"""make_threshold_inversion.py 模板回归测试（优化清单 B2）。

锁定本会话三处模板修复, 防回归:
  1. inset 四角自适应——修复前固定右下角, 参数跨度大时「首次穿越」标注
     右端伸入右下角区域, 被 inset 整块盖住(A 题实测; v3.1.0 起 figqa 第七类
     artist-bbox 已能兜同类遮挡, 模板内的确定性避让仍由本测试守护——门禁是
     兜底, 模板不该产出需要兜底的图);
  2. star_symbol 入参——修复前硬编码 "λ*", 参数是时间等场景无法改符号;
  3. star_value 入参——标注印冻结值而非图内插值(数字漂移防线: 图内数字
     必须与结果登记表逐字一致), 含越出参数范围的 ValueError 校验。

组织方式与 test_new_figure_templates.FirstCrossingBoundaryTests 一致:
importlib 直载模板模块(独立模块名, 不与既有测试的 sys.modules 键冲突),
出图走 tempfile 临时目录(out_stem 语义: 前缀自动追加 .png/.svg/.pdf)。
figkit.save_fig 默认 close=True, 断言 window_extent 需要活 figure,
故临时把模块内 save_fig 绑定替换为 close=False 的透传包装。
"""

from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from matplotlib.transforms import Bbox

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = (REPO_ROOT / "templates" / "figures" / "scripts" / "templates"
                 / "make_threshold_inversion.py")

# 修复前 inset 的固定右下角位置（axes fraction: x0, y0, w, h）。
# 用作测试 1 的场景前置: 标注须真的伸进这块区域, 否则用例没踩中历史 bug。
_LEGACY_BR_RECT = (0.60, 0.09, 0.36, 0.34)


class ThresholdInversionRegressionTests(unittest.TestCase):
    """三处修复的回归: inset 避让 / star_symbol+star_value / 越界校验 / 默认兼容。"""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "make_threshold_inversion_regression", TEMPLATE_PATH)
        cls.mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.mod
        spec.loader.exec_module(cls.mod)

    # ---- 公共小工具 -------------------------------------------------
    def _render(self, param, metric, threshold, out_stem, **kwargs):
        """渲染一次并保留活 figure 供 bbox 断言; 返回 (png, svg, fig)。

        模块内 save_fig 被 close=False 包装替换并在 finally 还原——只影响
        本次调用的 figure 生命周期, 不触碰 figkit 源码与其他调用方。

        样式隔离: 模板内部会 apply_style() 改全局 rcParams（spines 可见性等）,
        不还原会污染同进程其它用例——figure_lint 的 R7 顶右 spine 用例实测被带崩
        （"top spine 未去除仍应报 R7" 但实际查的是全局 rcParams）。快照在调用前取,
        用例结束时还原; figure 仍在模板样式生效期间绘制, bbox 断言不受影响。
        """
        mod = self.mod
        orig_save = mod.save_fig
        holder = {}

        def _keep_open(fig, out_prefix, **kw):
            holder["fig"] = fig
            kw.setdefault("close", False)
            return orig_save(fig, out_prefix, **kw)

        self.addCleanup(self.mod.plt.rcParams.update, dict(self.mod.plt.rcParams))
        mod.save_fig = _keep_open
        try:
            png, svg = mod.plot_threshold_inversion(param, metric, threshold,
                                                    out_stem=out_stem, **kwargs)
        finally:
            mod.save_fig = orig_save
        return png, svg, holder["fig"]

    def _annotation(self, ax):
        """取主图上唯一解释性注释「首次穿越 ...」的 Text 对象（ax.texts 内）。"""
        return next(tx for tx in ax.texts if "首次穿越" in tx.get_text())

    @staticmethod
    def _drawn_renderer(fig):
        """Agg 后端完整 draw 后取 renderer, 与存盘像素布局一致。"""
        fig.canvas.draw()
        return fig.canvas.get_renderer()

    # ---- 用例 1: inset 四角自适应避让标注 ---------------------------
    def test_inset_corner_adaptive_avoids_annotation(self):
        """右下标注场景: 实际 inset 的 window_extent 与标注文本不相交。

        构造参数跨度大(0~5000)的单调下降 sigmoid, 穿越点在 frac=0.24<0.26,
        标注按模板规则落到穿越点右下方, 右端伸入修复前的固定右下角 inset
        区域(旧版 inset 整块盖字)。先断言场景成立, 再断言自适应选角后
        inset 与标注 bbox 完全不相交。
        """
        t = np.linspace(0.0, 5000.0, 1001)
        metric = 1.0 / (1.0 + np.exp(0.002 * (t - 1200.0)))  # 单调下降, t=1200 穿越 0.5
        with tempfile.TemporaryDirectory() as td:
            png, _svg, fig = self._render(t, metric, 0.5,
                                          str(Path(td) / "inset_adaptive"))
            self.addCleanup(self.mod.plt.close, fig)
            renderer = self._drawn_renderer(fig)
            ax = fig.axes[0]
            ann = self._annotation(ax)
            axins = ax.child_axes[0]
            ann_bb = ann.get_window_extent(renderer)
            ax_bb = ax.get_window_extent(renderer)
            ins_bb = axins.get_window_extent(renderer)

            # 前置: 标注确实伸进历史 bug 的固定右下角区域, 用例踩中场景
            lx, ly, lw, lh = _LEGACY_BR_RECT
            legacy = Bbox.from_bounds(ax_bb.x0 + lx * ax_bb.width,
                                      ax_bb.y0 + ly * ax_bb.height,
                                      lw * ax_bb.width, lh * ax_bb.height)
            self.assertTrue(legacy.overlaps(ann_bb),
                            "测试数据未触发右下角遮挡场景: 标注未伸入旧固定 "
                            f"inset 区域 (ann={ann_bb.bounds}, legacy={legacy.bounds})")

            # 断言: 自适应选角的 inset 与标注文本不相交
            self.assertFalse(
                ins_bb.overlaps(ann_bb),
                f"inset {ins_bb.bounds} 与「首次穿越」标注 {ann_bb.bounds} 相交")

            self.assertTrue(png.is_file() and png.stat().st_size > 0,
                            f"PNG 缺失或为空: {png}")

    # ---- 用例 2: star_symbol / star_value 冻结值入图 -----------------
    def test_star_symbol_and_frozen_value_in_annotation(self):
        """自定义符号与冻结值: 标注含 "t* = 57.5406", 不含插值 "50.0000"。

        线性下降曲线的插值穿越恰在 t=50.0; 传 star_value=57.5406 后图内
        必须逐字印冻结值, 插值数字不得出现（数字漂移防线）。
        """
        t = np.linspace(0.0, 100.0, 1001)
        metric = 1.0 - t / 100.0                       # 插值穿越点 = 50.0
        with tempfile.TemporaryDirectory() as td:
            _png, _svg, fig = self._render(
                t, metric, 0.5, str(Path(td) / "frozen"),
                star_symbol="t*", star_value=57.5406, digits=4)
            self.addCleanup(self.mod.plt.close, fig)
            text = self._annotation(fig.axes[0]).get_text()
            self.assertIn("t* = 57.5406", text)        # 冻结值逐字入图
            self.assertNotIn("λ*", text)               # 符号已替换, 不残留默认
            self.assertNotIn("50.0000", text)          # 图内插值不得出现

    # ---- 用例 3: star_value 越界/非有限 → ValueError -----------------
    def test_star_value_out_of_range_raises(self):
        """star_value 越出参数范围或非有限 → ValueError, 且不落任何输出文件。"""
        t = np.linspace(0.0, 100.0, 11)
        metric = np.linspace(1.0, 0.0, 11)
        with tempfile.TemporaryDirectory() as td:
            cases = ((150.0, "越出参数范围"),    # 高于参数上限
                     (-0.5, "越出参数范围"),     # 低于参数下限
                     (float("nan"), "须为有限数值"))
            for bad, msg in cases:
                with self.assertRaises(ValueError) as ctx:
                    self.mod.plot_threshold_inversion(
                        t, metric, 0.5, star_value=bad,
                        out_stem=str(Path(td) / "bad"))
                self.assertIn(msg, str(ctx.exception))
            self.assertEqual(list(Path(td).iterdir()), [],
                             "校验失败仍写出了输出文件")

    # ---- 用例 4: 默认入参向后兼容 -----------------------------------
    def test_default_params_keep_lambda_star_annotation(self):
        """不传新入参不崩: 标注仍为 "λ* = <插值>"，三格式输出齐全。"""
        lam, metric = self.mod._demo_curve()           # 内置上升 sigmoid, 穿越恰 0.42
        with tempfile.TemporaryDirectory() as td:
            png, svg, fig = self._render(lam, metric, 0.5,
                                         str(Path(td) / "default"))
            self.addCleanup(self.mod.plt.close, fig)
            text = self._annotation(fig.axes[0]).get_text()
            self.assertIn("λ*", text)                  # 默认符号未变
            m = re.search(r"=\s*([0-9.]+)", text)
            self.assertIsNotNone(m, f"标注中未找到数值: {text!r}")
            self.assertAlmostEqual(float(m.group(1)), 0.420, delta=5e-4)
            for path in (png, svg, png.with_suffix(".pdf")):
                self.assertTrue(path.is_file() and path.stat().st_size > 0,
                                f"输出缺失或为空: {path}")


if __name__ == "__main__":
    unittest.main()
