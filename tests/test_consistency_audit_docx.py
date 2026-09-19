# -*- coding: utf-8 -*-
"""consistency_audit A6+D3 回归: docx 链题注语法 / 公式编号闭环 / 符号白名单。

背景 (skill优化清单 v3.1.0 A6/D3, 2026 A 题实战):
  - 图表引用闭环原先只认 "题注含 图N/表N" 与 \\label 两种形态, 对 docx 链
    md 真源的 ": 表 N：…" 题注与 "![图 N …](路径)" 图题恒报未定义 (92 条误报);
  - 符号脱节检查对哑变量/代码变量 (i, e, a, b, w, delta) 大量误报。
本文件验证: 第三形态题注识别、图/表/式三组闭环+连续性、数量短语豁免、
围栏 (```/~~~ 变长配对) 与行内代码跳过、单字母白名单与下标吸收,
且既有 tex 链/行式题注形态不回归 (test_consistency_audit.py 覆盖)。
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = SKILL_ROOT / "scripts" / "consistency_audit.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _build_ws(root: Path, fixture: str) -> Path:
    ws = root / ("ws_" + fixture.removesuffix(".md"))
    paper = ws / "paper_workspace"
    paper.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FIXTURES / fixture, paper / fixture)
    return ws


class DocxCaptionCleanTests(unittest.TestCase):
    """干净 docx 链样例: 三形态题注全闭环 + 白名单/围栏豁免 -> 零检出 exit 0。"""

    @classmethod
    def setUpClass(cls):
        cls.audit = load_module(AUDIT_PATH, "consistency_audit_docx_clean")

    def test_clean_docx_chain_exit_0(self):
        with tempfile.TemporaryDirectory(prefix="audit_docx_clean_") as td:
            ws = _build_ws(Path(td), "consistency_audit_docx_clean.md")
            rc = self.audit.main(["--workspace", str(ws)])
            result = self.audit.run_audit(ws, None)
        msgs = [f["msg"] for f in result["findings"]]
        self.assertEqual(rc, 0, f"干净 docx 链样例应 exit 0, 检出: {msgs}")
        self.assertEqual(result["error"], 0, msgs)
        self.assertEqual(result["warn"], 0, f"不应有 ⚠️ 检出: {msgs}")

    def test_docx_defs_collected_and_closed(self):
        """: 表 N / ![图 N / \\qquad (N) 三组定义均应进入定义集并全部闭环。"""
        with tempfile.TemporaryDirectory(prefix="audit_docx_defs_") as td:
            ws = _build_ws(Path(td), "consistency_audit_docx_clean.md")
            doc = self.audit.Doc(self.audit.collect_body_files(ws, None))
            doc.assemble()
        figs = sorted({t for t, _ in doc.figdefs}, key=int)
        tabs = sorted({t for t, _ in doc.tabdefs}, key=int)
        eqs = sorted({t for t, _ in doc.eqdefs}, key=int)
        self.assertEqual(figs, ["1", "2", "3"],
                         "![图 N 图题应计入图定义 (含行式题注 图 3：)")
        self.assertEqual(tabs, ["1", "2", "3"],
                         "': 表 N' 题注应计入表定义 (含行式题注 表 3：)")
        self.assertEqual(eqs, ["1", "2", "3"],
                         "$$ 块内 \\qquad (N) 应计入式定义 (含跨行 $$ 块)")
        self.assertEqual({t for t, _ in doc.eqrefs}, {"1", "2", "3"},
                         "式（1）/式(2)/式（3) 全半角括号引用都应识别")

    def test_measure_phrase_not_reference(self):
        """"结果表 50 格逐格" 是格数描述, 不得报 表 [50] 未定义。"""
        with tempfile.TemporaryDirectory(prefix="audit_docx_meas_") as td:
            ws = _build_ws(Path(td), "consistency_audit_docx_clean.md")
            result = self.audit.run_audit(ws, None)
        for f in result["findings"]:
            self.assertNotIn("[50]", f["msg"], f"数量短语误判: {f['msg']}")

    def test_fences_do_not_eat_rest_of_doc(self):
        """~~~ 围栏内嵌 ``` 行、四反引号围栏内嵌 ``` 行均不误关栏。

        若配对错误, 围栏后的 "# 结论" 会被吞掉, 检查 2 将因缺结论数字而跳过。
        """
        with tempfile.TemporaryDirectory(prefix="audit_docx_fence_") as td:
            ws = _build_ws(Path(td), "consistency_audit_docx_clean.md")
            result = self.audit.run_audit(ws, None)
        st2 = result["stats"][2]
        self.assertFalse(st2.get("skipped"),
                         "围栏误配对会吞掉结论章节, 使检查 2 被跳过")
        self.assertEqual(st2.get("conclusion_numbers"), 1,
                         "结论章节的 '18 个' 应仍被扫描到")


class DocxCaptionDirtyTests(unittest.TestCase):
    """脏 docx 链样例: 断链/跳号/孤立定义/未登记符号逐项命中, exit 1。"""

    @classmethod
    def setUpClass(cls):
        cls.audit = load_module(AUDIT_PATH, "consistency_audit_docx_dirty")

    @classmethod
    def _run(cls):
        with tempfile.TemporaryDirectory(prefix="audit_docx_dirty_") as td:
            ws = _build_ws(Path(td), "consistency_audit_docx_dirty.md")
            return cls.audit.run_audit(ws, None)

    def test_exit_1_with_breaks(self):
        result = self._run()
        self.assertEqual(result["exit"], 1)
        self.assertGreaterEqual(result["stats"][3]["error"], 3)

    def test_eq_reference_without_definition(self):
        result = self._run()
        self.assertTrue(
            any(f["check"] == 3 and f["severity"] == "error"
                and "式编号 [9]" in f["msg"] for f in result["findings"]),
            [f["msg"] for f in result["findings"] if f["check"] == 3])

    def test_fig_reference_without_definition(self):
        result = self._run()
        self.assertTrue(
            any(f["check"] == 3 and f["severity"] == "error"
                and "图编号 [5]" in f["msg"] for f in result["findings"]))

    def test_numbering_discontinuity(self):
        result = self._run()
        fig_gap = any(f["severity"] == "error" and "图编号不连续" in f["msg"]
                      and "缺" in f["msg"] for f in result["findings"]
                      if f["check"] == 3)
        eq_gap = any(f["severity"] == "error" and "式编号不连续" in f["msg"]
                     for f in result["findings"] if f["check"] == 3)
        self.assertTrue(fig_gap, "图 1,3 跳号 (缺 2) 应报不连续")
        self.assertTrue(eq_gap, "式 5,6,7 起编 (缺 1-4) 应报不连续")

    def test_orphan_definitions_warned(self):
        result = self._run()
        msgs = [f["msg"] for f in result["findings"] if f["check"] == 3]
        for need in ("图 [3] 已定义但正文从未引用",
                     "表 [1] 已定义但正文从未引用",
                     "式 [7] 已定义但正文从未引用"):
            self.assertTrue(any(need in m for m in msgs), f"缺: {need}; 有: {msgs}")

    def test_fenced_content_not_scanned(self):
        result = self._run()
        for f in result["findings"]:
            self.assertNotIn("[99]", f["msg"], "围栏内 图 99 不应计为引用")
            self.assertNotIn("[98]", f["msg"])

    def test_subscript_absorbed_into_base(self):
        """$q_j$ 按基名 q 告警, 下标 j 不得作为独立符号出现。"""
        result = self._run()
        q_msgs = [f["msg"] for f in result["findings"]
                  if f["check"] == 4 and "符号" in f["msg"]
                  and re.search(r": q \(符号表现有", f["msg"])]
        self.assertTrue(q_msgs, "基名 q 未登记应告警")
        for m in q_msgs:
            self.assertNotIn("j", m, f"下标 j 应被吸收: {m}")


class SymbolWhitelistUnitTests(unittest.TestCase):
    """D3 单元: 白名单常量、下标吸收、\\mathrm 单位剥离。"""

    @classmethod
    def setUpClass(cls):
        cls.audit = load_module(AUDIT_PATH, "consistency_audit_symbols")

    def test_whitelist_constant(self):
        self.assertEqual(
            self.audit.SYMBOL_WHITELIST,
            {"i", "j", "k", "n", "m", "e", "a", "b", "x", "y", "t"})

    def test_chunk_roots_subscript_absorbed(self):
        roots = self.audit._chunk_roots
        self.assertEqual(roots("r_i"), {"r"}, "下标 i 吸收进 $r_i$ 基名")
        self.assertEqual(roots("q_{j+1}"), {"q"}, "花括下标表达式同样吸收")
        self.assertEqual(roots("i\\Delta r"), {"i", "delta", "r"},
                         "裸 i 与 \\Delta r 各保持独立根")
        self.assertNotIn("i", roots("C_{i+1}-C_{i}"))
        self.assertEqual(roots("a_i=(r_e^2-r_w^2)/2"), {"a", "r"},
                         "下标 e/w 吸收, 只余基名与裸字母")

    def test_chunk_roots_mathrm_units_stripped(self):
        roots = self.audit._chunk_roots
        self.assertEqual(roots("\\mathrm{J/(kg\\cdot K)}"), set(),
                         "罗马体单位不算符号")
        self.assertEqual(roots("\\text{个}"), set())

    def test_chunk_roots_superscript_kept(self):
        roots = self.audit._chunk_roots
        self.assertEqual(roots("e^{-0.89/C}"), {"e", "C"},
                         "上标 (指数) 内符号保持原行为, e 交白名单豁免")


if __name__ == "__main__":
    unittest.main()
