# -*- coding: utf-8 -*-
"""模板旧 API 兼容回归: 位置参数顺序 + 旧关键字 + 输出路径（A1/A2 清单）。

背景: 3.0.1 参数化批次把入参插进了旧位置串中间（如
`plot_answer_grid(..., annotate, xlabel, ylabel, out_stem)`）。关键字调用不受影响,
**位置调用会静默错位**——`plot_ranking(scores, weights, "综合得分", "图名", out)`
里 `"图名"` 被当成 `total_fmt`, 直到渲染才炸或干脆悄悄变形。本测试按
`git show 4e203ef:<路径>` 实测的旧签名建表, 锁三件事:

  1. 旧位置参数**顺序表**与旧版逐字一致（新增入参必须是 keyword-only,
     不得插进位置串）;
  2. 12 个模板用**全位置**调用（含 out_stem 位置传参）与**全关键字**调用
     渲染同一份数据, 两条路径产物一致（规范化 SVG 逐字比对, 抹掉
     dc:date 与随机 id/url 哈希）——这既证明位置槽位没错位, 也证明旧关键字
     含义未变;
  3. out_stem 真的被用上: 三格式落在指定前缀处, 且不是默认临时目录图。

参数报错与格式报错的资源卫生（不留 Figure、不动全局 rcParams）见
tests/test_template_format_errors.py。
"""

from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无显示环境固定 Agg
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "templates" / "figures" / "scripts"
TEMPLATES_DIR = SCRIPTS_DIR / "templates"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# ---- 旧 API 表（实测自 git show 4e203ef:templates/figures/scripts/templates/<stem>.py）----
# 每项: 模块文件 stem → (函数名, 旧位置参数名列表含 out_stem, 旧位置参数的取值)
# 取值表只覆盖位置参数; 新增的 keyword-only 入参不在表内（它们不属于旧 API）。
OLD_POSITIONAL_API: dict[str, tuple[str, list[str]]] = {
    "make_answer_grid": ("plot_answer_grid", [
        "values", "row_names", "col_names", "value_label", "cmap_kind",
        "center", "digits", "annotate", "out_stem"]),
    "make_contrast_pair": ("plot_contrast_pair", [
        "X", "Y", "field_a", "field_b", "title_a", "title_b", "diff_threshold",
        "value_label", "cmap_kind", "out_stem"]),
    "make_convergence_curve": ("plot_convergence", [
        "histories", "best_value", "converged", "ylog", "title", "out_stem"]),
    "make_convergence_sequence": ("plot_convergence_sequence", [
        "n_values", "errors", "param_label", "metric_label", "tolerance",
        "richardson", "loglog", "annotate_gaps", "out_stem"]),
    "make_field_contour": ("plot_field_contour", [
        "X", "Y", "fields", "panel_titles", "criterion", "criterion_label",
        "value_label", "share_scale", "cmap_kind", "out_stem"]),
    "make_multiscenario_robustness": ("plot_robustness", [
        "scenarios", "baseline", "metric", "mode", "out_stem"]),
    "make_prediction_fit": ("plot_prediction", [
        "actual", "prediction", "ci_lo", "ci_hi", "t", "split", "actual_label",
        "pred_label", "quantity", "out_stem"]),
    "make_profile_family": ("plot_profile_family", [
        "depth", "profiles", "values", "var_label", "value_label", "depth_label",
        "criterion", "criterion_label", "out_stem"]),
    "make_ranking_bar": ("plot_ranking", [
        "scores", "weights", "xlabel", "title", "out_stem"]),
    "make_route_on_field": ("plot_route_on_field", [
        "X", "Y", "field", "route", "route_label", "value_label", "coord_label",
        "out_stem"]),
    "make_threshold_inversion": ("plot_threshold_inversion", [
        "param", "metric", "threshold", "param_label", "metric_label",
        "threshold_label", "digits", "out_stem"]),
    "make_tornado_sensitivity": ("plot_tornado", [
        "params", "metric", "delta", "out_stem"]),
}

_LOADED: dict[str, object] = {}


def load(stem: str):
    """按文件名加载模板模块（与 test_template_params.load 同手法, 模块名独立）。"""
    if stem in _LOADED:
        return _LOADED[stem]
    spec = importlib.util.spec_from_file_location(f"_apicompat_{stem}",
                                                 TEMPLATES_DIR / f"{stem}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    _LOADED[stem] = mod
    return mod


def old_call_values() -> dict[str, dict]:
    """旧位置参数的取值表（每模板一份, 值取常量以保证两次渲染可比）。"""
    import numpy as np

    x = np.linspace(0.0, 1.0, 14)
    y = np.linspace(0.0, 1.0, 12)
    X, Y = np.meshgrid(x, y)
    field = np.hypot(X - 0.5, Y - 0.5)
    grid = np.linspace(0.2, 0.9, 12).reshape(4, 3)
    return {
        "make_answer_grid": {
            "values": grid, "row_names": ["样本 1", "样本 2", "样本 3", "样本 4"],
            "col_names": ["类别 1", "类别 2", "类别 3"], "value_label": "达标概率",
            "cmap_kind": "sequential", "center": 0.5, "digits": 3,
            "annotate": False},
        "make_contrast_pair": {
            "X": X, "Y": Y, "field_a": field, "field_b": field * 1.3,
            "title_a": "基准图", "title_b": "改进图", "diff_threshold": 0.1,
            "value_label": "温度 (°C)", "cmap_kind": "diverging"},
        "make_convergence_curve": {
            "histories": {"GA": [float(v) for v in np.linspace(10, 1, 40)],
                          "PSO": [float(v) for v in np.linspace(12, 1.2, 30)]},
            "best_value": 1.0, "converged": {"GA": 28}, "ylog": False,
            "title": "弃用图名不入图"},
        "make_convergence_sequence": {
            "n_values": np.array([50.0, 100.0, 200.0, 400.0]),
            "errors": np.array([4e-2, 1e-2, 2.5e-3, 6e-4]),
            "param_label": "网格规模 N", "metric_label": "误差 e",
            "tolerance": 1e-3, "richardson": True, "loglog": True,
            "annotate_gaps": True},
        "make_field_contour": {
            "X": X, "Y": Y, "fields": [field, field * 0.8],
            "panel_titles": ["t = 0", "t = 1"], "criterion": 0.4,
            "criterion_label": "判据等值线", "value_label": "温度 (°C)",
            "share_scale": True, "cmap_kind": "sequential"},
        "make_multiscenario_robustness": {
            "scenarios": {"场景 A": [1.0, 1.1, 0.9], "场景 B": [1.3, 1.25, 1.35]},
            "baseline": 0.85, "metric": "服务水平", "mode": "box"},
        "make_prediction_fit": {
            "actual": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
            "prediction": [1.02, 1.08, 1.25, 1.28, 1.45, 1.48],
            "ci_lo": [0.9, 1.0, 1.1, 1.2, 1.3, 1.4],
            "ci_hi": [1.1, 1.2, 1.3, 1.4, 1.5, 1.6],
            "t": [0, 1, 2, 3, 4, 5], "split": 3,
            "actual_label": "真实值", "pred_label": "预测值", "quantity": "指标值"},
        "make_profile_family": {
            "depth": np.linspace(0.0, 1.0, 20),
            "profiles": [np.linspace(0.0, 1.0, 20) * k for k in (0.5, 1.0, 1.5)],
            "values": [1.0, 2.0, 3.0], "var_label": "时刻 (h)",
            "value_label": "温度 (°C)", "depth_label": "深度 (cm)",
            "criterion": 1.2, "criterion_label": "判据线"},
        "make_ranking_bar": {
            "scores": {"方案甲": {"成本": 0.8, "效率": 0.6},
                       "方案乙": {"成本": 0.5, "效率": 0.9}},
            "weights": {"成本": 0.4, "效率": 0.6}, "xlabel": "综合得分",
            "title": "弃用图名不入图"},
        "make_route_on_field": {
            "X": X, "Y": Y, "field": field,
            "route": np.array([[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]]),
            "route_label": "最优路径", "value_label": "通行代价", "coord_label": "(km)"},
        "make_threshold_inversion": {
            "param": np.linspace(0.0, 10.0, 101),
            "metric": np.linspace(0.0, 1.0, 101), "threshold": 0.5,
            "param_label": "参数 λ", "metric_label": "指标 S",
            "threshold_label": "判据阈值", "digits": 3},
        "make_tornado_sensitivity": {
            "params": [("参数 A", -0.10, 0.15), ("参数 B", 0.05, -0.20)],
            "metric": "总成本", "delta": 0.10},
    }


# ---- SVG 规范化: 抹掉每次渲染都变的噪声（时间戳与随机 id/url 哈希） ----
_SVG_NOISE = (
    (re.compile(r"<dc:date>[^<]*</dc:date>"), "<dc:date>X</dc:date>"),
    (re.compile(r"<cc:Work[^>]*>.*?</cc:Work>", re.S), "<cc:Work/>"),
    (re.compile(r'id="[^"]*"'), 'id="X"'),
    (re.compile(r"url\(#[^)]*\)"), "url(#X)"),
    (re.compile(r'xlink:href="#[^"]*"'), 'xlink:href="#X"'),
)


def normalize_svg(path: Path) -> str:
    """读 SVG 并抹掉时间戳/随机 id, 用于两次渲染的结构等价比对。"""
    text = path.read_text(encoding="utf-8")
    for pattern, repl in _SVG_NOISE:
        text = pattern.sub(repl, text)
    return text


def call_template(fn, args: tuple, kwargs: dict, out_stem: str):
    """在 rc_context 内调用模板（样式不外溢）, 返回 (返回值, 产物路径元组)。

    资源卫生口径: 调用**失败**时关掉本次新建的全部 Figure（否则泄漏进全局
    管理器, 污染同进程后续用例）; 调用成功时不动 Figure 生命周期——产物已由
    模板内的 save_fig(close=True) 收尾, 若将来模板改为返回活 Figure, 调用方
    仍能继续用（不提前 close）。
    """
    before = set(plt.get_fignums())
    try:
        with plt.rc_context():
            result = fn(*args, **kwargs)
    except Exception:
        for num in set(plt.get_fignums()) - before:
            plt.close(num)
        raise
    paths = result if isinstance(result, (list, tuple)) else [result]
    return result, tuple(Path(p) for p in paths)


def render_both_ways(stem: str, out_dir: Path):
    """同一份数据分别走"全位置"与"全关键字"两条旧调用路径, 各渲染一次。

    Returns:
        (positional_paths, keyword_paths, positional_svg, keyword_svg, out_stem)
    """
    fn_name, pos_names = OLD_POSITIONAL_API[stem]
    fn = getattr(load(stem), fn_name)
    values = old_call_values()[stem]
    out_stem = str(out_dir / stem)
    args = tuple(values[name] for name in pos_names[:-1]) + (out_stem,)
    _res, pos_paths = call_template(fn, args, {}, out_stem)

    kw_dir = out_dir / "kw"
    kw_dir.mkdir(parents=True, exist_ok=True)
    kw_stem = str(kw_dir / stem)
    kwargs = {name: values[name] for name in pos_names[:-1]}
    kwargs["out_stem"] = kw_stem
    _res2, kw_paths = call_template(fn, (), kwargs, kw_stem)
    return (pos_paths, kw_paths,
            normalize_svg(Path(out_stem + ".svg")),
            normalize_svg(Path(kw_stem + ".svg")),
            out_stem)


class OldApiContractTests(unittest.TestCase):
    """旧位置/旧关键字/输出路径三件套 + keyword-only 约束。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.rendered: dict[str, tuple] = {}
        cls.errors: dict[str, str] = {}
        for stem in OLD_POSITIONAL_API:
            try:
                cls.rendered[stem] = render_both_ways(stem, cls.tmp)
            except Exception as exc:  # 渲染失败在下面逐个用例里报错, 不中断收集
                cls.errors[stem] = f"{type(exc).__name__}: {exc}"

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    # ---- 1. 位置参数顺序表 ----
    def test_positional_table_matches_old_api(self):
        """位置参数名与顺序必须与 4e203ef 实测旧签名逐字一致。"""
        import inspect

        for stem, (fn_name, old_pos) in OLD_POSITIONAL_API.items():
            with self.subTest(模板=stem):
                sig = inspect.signature(getattr(load(stem), fn_name))
                now = [n for n, p in sig.parameters.items()
                       if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
                self.assertEqual(
                    now, old_pos,
                    f"{stem}.{fn_name} 位置参数串被改动: 旧={old_pos} 现={now}")

    # ---- 2. 新增参数必须 keyword-only ----
    def test_new_params_are_keyword_only(self):
        """旧 API 之外的入参必须是 keyword-only（不得插进位置串）。"""
        import inspect

        for stem, (fn_name, old_pos) in OLD_POSITIONAL_API.items():
            with self.subTest(模板=stem):
                sig = inspect.signature(getattr(load(stem), fn_name))
                added = [n for n in sig.parameters if n not in old_pos]
                self.assertTrue(added, f"{stem}.{fn_name} 未检出新增入参, 用例失去意义")
                bad = [n for n in added
                       if sig.parameters[n].kind is not inspect.Parameter.KEYWORD_ONLY]
                self.assertEqual(
                    bad, [], f"{stem}.{fn_name} 这些新增入参不是 keyword-only: {bad}")

    # ---- 3. 旧位置 vs 旧关键字: 产物一致 + 输出路径生效 ----
    def test_old_positional_and_keyword_calls_agree(self):
        """全位置调用与全关键字调用渲染同一张图; out_stem 落在指定前缀。"""
        for stem in OLD_POSITIONAL_API:
            with self.subTest(模板=stem):
                if stem in self.errors:
                    self.fail(f"{stem} 旧 API 调用失败: {self.errors[stem]}")
                pos_paths, kw_paths, pos_svg, kw_svg, out_stem = self.rendered[stem]

                # 输出路径: 三格式齐、非空、就在指定的 out_stem 前缀处
                for paths, stem_used in ((pos_paths, out_stem),):
                    exts = {p.suffix for p in paths}
                    self.assertEqual(exts, {".png", ".svg"},
                                     f"{stem} 返回路径异常: {paths}")
                    for path in paths:
                        self.assertTrue(path.is_file(), f"{stem} 未写出 {path}")
                        self.assertGreater(path.stat().st_size, 0,
                                           f"{stem} 产物为空: {path}")
                        self.assertEqual(str(path.parent), str(Path(stem_used).parent),
                                         f"{stem} 产物没落在指定 out_stem 目录")
                    for ext in (".png", ".svg", ".pdf"):
                        f = Path(stem_used + ext)
                        self.assertTrue(f.is_file() and f.stat().st_size > 0,
                                        f"{stem} 缺 {ext} 产物: {f}")
                # 关键字路径同样三格式齐全
                for ext in (".png", ".svg", ".pdf"):
                    f = Path(kw_paths[0].with_suffix("").as_posix() + ext)
                    self.assertTrue(f.is_file() and f.stat().st_size > 0,
                                    f"{stem} 关键字路径缺 {ext} 产物: {f}")

                # 位置槽位与关键字槽位同义: 规范化 SVG 逐字一致
                self.assertEqual(
                    pos_svg, kw_svg,
                    f"{stem} 位置调用与关键字调用产物不一致——位置槽位错位"
                    f"或旧关键字含义被改")

    # ---- 4. 覆盖度守卫: 12 个模板一个都不能少 ----
    def test_covers_exactly_twelve_templates(self):
        self.assertEqual(len(OLD_POSITIONAL_API), 12)
        self.assertEqual(set(self.rendered), set(OLD_POSITIONAL_API))


class RenderPackCliHintTests(unittest.TestCase):
    """figures 包 CLI 能力核实: --list 可用, 且提示命令里含空格的路径带引号。

    安装根常在 `Program Files` 或含空格的用户名/项目名下; 提示命令不加引号时
    复制到终端会被 shell 拆成多个参数（路径测试代理实测）。
    """

    PACK = SCRIPTS_DIR / "render_modeling_pack.py"

    def test_list_runs_and_hint_paths_exist(self):
        import subprocess

        proc = subprocess.run([sys.executable, str(self.PACK), "--list"],
                              capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        hints = re.findall(r'python\s+"?([^"]+?figqa\.py)"?', proc.stdout)
        self.assertTrue(hints, f"--list 未给出 figqa 命令提示:\n{proc.stdout[:400]}")
        for hint in set(hints):
            self.assertTrue(Path(hint).is_file(), f"提示路径不存在: {hint}")

    def test_quote_arg_wraps_paths_with_spaces(self):
        spec = importlib.util.spec_from_file_location("_apicompat_pack", self.PACK)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        self.assertEqual(mod.quote_arg("C:/plain/figqa.py"), "C:/plain/figqa.py")
        self.assertEqual(mod.quote_arg("C:/Program Files/figqa.py"),
                         '"C:/Program Files/figqa.py"')
        self.assertEqual(mod.quote_arg(Path("C:/a b/c/figqa.py")),
                         '"C:\\a b\\c\\figqa.py"' if "\\" in str(Path("C:/a b/c"))
                         else '"C:/a b/c/figqa.py"')


if __name__ == "__main__":
    unittest.main()
