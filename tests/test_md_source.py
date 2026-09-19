"""md_source.py 的行为测试: 有序稿件发现 (与导出同源)、变长围栏 (四反引号围栏内
的三反引号不闭栏)、标题属性剥离 (参考文献 {-})、旧 \\bibitem 条目识别、文件角色、
容错读文本。这些口径被 export_final_docx.py 与 ref_order_audit.py 共用, 是
"审计扫的 == 导出的"的保证层。"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from md_source import (FenceTracker, bibitem_payload, discover_ordered_sources,
                       file_kind, has_heading_attrs, has_heading_outside_fences,
                       is_bibitem_line, iter_lines_outside_fences, parse_heading,
                       read_source_text, reference_section_spans,
                       strip_heading_attrs)


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class FenceTest(unittest.TestCase):
    def test_fenced_flags_boundary_and_content(self):
        text = "正文\n```python\ncode\n```\n尾"   # 无尾随换行: 行数与断言一一对应
        got = [(line, fenced) for _, line, fenced in iter_lines_outside_fences(text)]
        self.assertEqual([("正文", False), ("```python", True), ("code", True),
                          ("```", True), ("尾", False)], got)

    def test_four_backtick_fence_not_closed_by_three(self):
        """四反引号围栏内的 ``` 是内容 (审计原实现会提前闭栏, 误计栏内 [2])。"""
        text = "````\n```\n[2] 代码示例\n````\n\n[1] 正文引用"
        outside = [line for _, line, fenced in iter_lines_outside_fences(text)
                   if not fenced and line]
        self.assertEqual(["[1] 正文引用"], outside)

    def test_tilde_fence_and_length_rules(self):
        # ~~~ 开栏须 ~~~ 闭; 更长开栏用更短闭栏不成立
        text = "~~~\n```\n~~~\n\n正文\n~~~~\n~~~\n~~~~"
        fenced = [f for _, _, f in iter_lines_outside_fences(text)]
        self.assertEqual([True, True, True, False, False, True, True, True],
                         fenced)

    def test_backtick_info_string_is_not_fence(self):
        """反引号开栏的 info 串含反引号 → 不是围栏 (pandoc 口径)。"""
        t = FenceTracker()
        self.assertFalse(t.update("``` a`b"))
        self.assertFalse(t.in_fence)

    def test_indented_fence(self):
        t = FenceTracker()
        self.assertTrue(t.update("   ```"))
        self.assertTrue(t.update("```"))


class HeadingTest(unittest.TestCase):
    def test_parse_heading_levels_and_atx_close(self):
        self.assertEqual((2, "参考文献 {-}"), parse_heading("## 参考文献 {-}"))
        self.assertEqual((1, "摘要"), parse_heading("# 摘要 #"))
        self.assertEqual((3, "模型建立"), parse_heading("   ### 模型建立"))
        self.assertIsNone(parse_heading("#无空格"))
        self.assertIsNone(parse_heading("正文 ## 不算标题"))
        self.assertIsNone(parse_heading("####### 七级不是标题"))

    def test_strip_heading_attrs(self):
        self.assertEqual("参考文献", strip_heading_attrs("参考文献 {-}"))
        self.assertEqual("附录A 代码", strip_heading_attrs("附录A 代码 {.unnumbered}"))
        self.assertEqual("模型建立", strip_heading_attrs("模型建立"))
        # 连续属性块一并去掉; 非属性内容一字不动 (含数字的花括号不是属性块)
        self.assertEqual("摘要", strip_heading_attrs("摘要 {-} {.unnumbered}"))
        self.assertEqual("集合 A {1,2}", strip_heading_attrs("集合 A {1,2}"))
        self.assertEqual("情形 {1,2} 讨论", strip_heading_attrs("情形 {1,2} 讨论"))

    def test_has_heading_attrs(self):
        self.assertTrue(has_heading_attrs("参考文献 {-}"))
        self.assertFalse(has_heading_attrs("参考文献"))
        self.assertFalse(has_heading_attrs("集合 A {1,2}"))

    def test_has_heading_outside_fences(self):
        self.assertTrue(has_heading_outside_fences("## 标题"))
        self.assertFalse(has_heading_outside_fences("```\n# 注释不是标题\n```\n正文"))


class BibitemTest(unittest.TestCase):
    def test_recognizes_both_forms(self):
        self.assertTrue(is_bibitem_line("\\bibitem{k1} 张三. 甲[J]."))
        self.assertTrue(is_bibitem_line("\\bibitem[模板]{k2} 李四."))
        self.assertTrue(is_bibitem_line("  \\bibitem{k3} 缩进也算"))
        self.assertFalse(is_bibitem_line("[1] 已转换条目"))
        self.assertFalse(is_bibitem_line("正文提到 \\bibitem 不是条目"))

    def test_payload_removes_command_head(self):
        self.assertEqual("张三. 甲[J].", bibitem_payload("\\bibitem{k1} 张三. 甲[J]."))
        self.assertEqual("李四.", bibitem_payload("\\bibitem[模板]{k2} 李四."))
        self.assertEqual("原文", bibitem_payload("原文"))


class FileKindTest(unittest.TestCase):
    def test_kind_mapping(self):
        cases = {
            "09_references.md": "references",
            "09_参考文献.md": "references",
            "10_appendix.md": "appendix",
            "10_附录A.md": "appendix",
            "02_body.md": "body",
            "references_summary_body.md": "references",
        }
        for name, kind in cases.items():
            self.assertEqual(kind, file_kind(Path(name)), name)


class DiscoverTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        self.pw = self.ws / "paper_workspace"

    def tearDown(self):
        self.tmp.cleanup()

    def test_nn_series_natural_order_and_non_export_md_excluded(self):
        for name in ("10_appendix.md", "01_abstract.md", "02_body.md",
                     "notes.md", "README.md", "draft-03-ideas.md"):
            _write(self.pw / name, "x\n")
        paths, mode = discover_ordered_sources(self.pw)
        self.assertEqual("nn_series", mode)
        self.assertEqual(["01_abstract.md", "02_body.md", "10_appendix.md"],
                         [p.name for p in paths])
        self.assertNotIn("notes.md", [p.name for p in paths])

    def test_fallback_to_sections_convention(self):
        _write(self.pw / "abstract_draft.md", "摘要\n")
        _write(self.pw / "sections" / "q10.md", "十\n")
        _write(self.pw / "sections" / "q2.md", "二\n")
        paths, mode = discover_ordered_sources(self.pw)
        self.assertEqual("md_convention", mode)
        self.assertEqual(["abstract_draft.md", "q2.md", "q10.md"],
                         [p.name for p in paths])

    def test_main_md_wins(self):
        _write(self.pw / "main.md", "全文\n")
        _write(self.pw / "sections" / "q1.md", "附\n")
        paths, mode = discover_ordered_sources(self.pw)
        self.assertEqual("md_convention", mode)
        self.assertEqual(["main.md"], [p.name for p in paths])

    def test_empty_workspace(self):
        self.pw.mkdir(parents=True, exist_ok=True)
        self.assertEqual(([], "none"), discover_ordered_sources(self.pw))


class ReadSourceTextTest(unittest.TestCase):
    def test_invalid_utf8_replaced_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.md"
            p.write_bytes(b"\xff\xfe abc\n")
            text = read_source_text(p)  # 不抛 UnicodeDecodeError
            self.assertIn("abc", text)


class ReferenceSectionSpansTest(unittest.TestCase):
    """正文文件内嵌 "## 参考文献" 节的行区间 (导出与审计同源口径)。"""

    def test_span_covers_section_until_same_level_heading(self):
        text = "\n".join([
            "# 论文",                      # 0
            "正文如文献[1]所示。",          # 1
            "",                            # 2
            "## 参考文献 {-}",              # 3
            "",                            # 4
            "[1] Alpha。",                 # 5
            "",                            # 6
            "\\bibitem{b} Beta。",         # 7
            "",                            # 8
            "## 附录 A",                   # 9
            "\\bibitem{stray} 附录项",      # 10
        ])
        self.assertEqual([(3, 8)], reference_section_spans(text))

    def test_no_refs_heading_no_span(self):
        self.assertEqual([], reference_section_spans("## 模型\n\n正文\n"))

    def test_deeper_subheading_does_not_close_section(self):
        text = "## 参考文献\n\n### 分组\n\n[1] A。\n\n## 附录\n"
        self.assertEqual([(0, 5)], reference_section_spans(text))


if __name__ == "__main__":
    unittest.main()
