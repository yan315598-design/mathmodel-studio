"""reference.docx 样式源头合规测试 (优化清单 v3.1.0: B3 + B5① + B5⑤)。

对随库的 templates/docx/reference.docx 与内存重建的默认档 / --loose 档断言:

- B5① Table 样式 (pandoc 给数据表挂的) 表级边框: 上/下 single w:sz=12 (1.5pt),
  insideH/insideV/left/right 显式 none, 无底纹 (shd=clear); 表头行下边框属
  行级直接格式 (pandoc 不写), 不在样式侧;
- B5⑤ Compact (pandoc 单元格段落用): 段前/段后 0, 单倍行距 (line=240/auto),
  首行缩进 0;
- B3 Normal/Body Text: 段后 0; Normal 的首行缩进 2 字符 (firstLineChars=200)
  与 1.3 行距 (line=312/auto) 保持不变;
- --loose 档保留旧值: Normal 段后继承 docDefaults、Body Text 段后 9pt、
  Compact 段前后 1.8pt/行距继承、Table 无表级边框。
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "templates" / "docx"))

from docx import Document  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Pt  # noqa: E402

from build_reference_docx import _find_style, build_reference_docx  # noqa: E402

HAS_PANDOC = shutil.which("pandoc") is not None
try:
    import docx  # noqa: F401
    HAS_PYTHON_DOCX = True
except ImportError:
    HAS_PYTHON_DOCX = False

REF_DOCX = ROOT / "templates" / "docx" / "reference.docx"
BUILD_SCRIPT = ROOT / "templates" / "docx" / "build_reference_docx.py"


def _tbl_border(style, tag):
    """回读 Table 样式表级 tblBorders 中 tag 的 (val, sz); 任一层缺失返回 None。"""
    tbl_pr = style.element.find(qn("w:tblPr"))
    if tbl_pr is None:
        return None
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        return None
    el = borders.find(qn(f"w:{tag}"))
    if el is None:
        return None
    return el.get(qn("w:val")), el.get(qn("w:sz"))


def _ppr_child(style, tag):
    ppr = style.element.find(qn("w:pPr"))
    return None if ppr is None else ppr.find(qn(tag))


def _attr(style, holder_tag, attr):
    """回读样式 pPr 下 holder_tag 元素 (如 w:spacing/w:ind) 的属性值。

    holder_tag 传短名 (w:spacing), attr 须传 qn() 后的完整属性名。
    """
    holder = _ppr_child(style, holder_tag)
    return None if holder is None else holder.get(attr)


class DefaultTierAssertionsMixin:
    """默认档四项断言, 供随库产物与内存重建产物共用。"""

    def assert_table_style_three_line(self, doc):
        table = _find_style(doc, "Table")
        for tag in ("top", "bottom"):
            self.assertEqual(("single", "12"), _tbl_border(table, tag),
                             f"表级 {tag} 边框应为 single 1.5pt (w:sz=12)")
        for tag in ("left", "right", "insideH", "insideV"):
            self.assertEqual(("none", "0"), _tbl_border(table, tag),
                             f"表级 {tag} 边框应显式 none")
        tbl_pr = table.element.find(qn("w:tblPr"))
        shd = tbl_pr.find(qn("w:shd"))
        self.assertIsNotNone(shd, "Table 样式应有显式无底纹声明")
        self.assertEqual("clear", shd.get(qn("w:val")))
        # CT_TblPr 序列顺序: tblInd < tblBorders < shd < tblCellMar (严格校验器要求)
        tags = [child.tag for child in tbl_pr]
        self.assertLess(tags.index(qn("w:tblBorders")), tags.index(qn("w:shd")))
        self.assertLess(tags.index(qn("w:shd")), tags.index(qn("w:tblCellMar")))

    def assert_compact_zero_spacing_single_line(self, doc):
        compact = _find_style(doc, "Compact")
        pf = compact.paragraph_format
        self.assertEqual(Pt(0), pf.space_before)
        self.assertEqual(Pt(0), pf.space_after)
        self.assertEqual(1.0, pf.line_spacing)
        self.assertEqual("240", _attr(compact, "w:spacing", qn("w:line")))
        self.assertEqual("auto", _attr(compact, "w:spacing", qn("w:lineRule")))
        self.assertEqual(Pt(0), pf.first_line_indent)
        self.assertEqual("0", _attr(compact, "w:ind", qn("w:firstLineChars")))

    def assert_normal_and_bodytext_zero_after(self, doc):
        normal = _find_style(doc, "Normal")
        pf = normal.paragraph_format
        self.assertEqual(Pt(0), pf.space_after, "B3: Normal 段后应归零")
        self.assertEqual("0", _attr(normal, "w:spacing", qn("w:after")))
        # Normal 的正文属性保持不变 (首行缩进 2 字符 + 1.3 行距)
        self.assertEqual(1.3, pf.line_spacing)
        self.assertEqual("312", _attr(normal, "w:spacing", qn("w:line")))
        self.assertEqual("auto", _attr(normal, "w:spacing", qn("w:lineRule")))
        self.assertEqual("200", _attr(normal, "w:ind", qn("w:firstLineChars")))
        self.assertEqual("480", _attr(normal, "w:ind", qn("w:firstLine")))
        body_text = _find_style(doc, "Body Text")
        self.assertEqual(Pt(0), body_text.paragraph_format.space_after,
                         "B3: Body Text 段后应归零")
        # 段前 9pt 是 pandoc 既有定义, 本项只归零段后 (段前不在 B3 范围)
        self.assertEqual(Pt(9), body_text.paragraph_format.space_before)


@unittest.skipUnless(REF_DOCX.exists(), "缺少随库 templates/docx/reference.docx")
@unittest.skipUnless(HAS_PYTHON_DOCX, "需要 python-docx")
class ShippedReferenceDocxTest(DefaultTierAssertionsMixin, unittest.TestCase):
    """随库 reference.docx 产物本身的 B3/B5①/B5⑤ 合规性。"""

    @classmethod
    def setUpClass(cls):
        cls.doc = Document(str(REF_DOCX))

    def test_b5_1_table_style_three_line(self):
        self.assert_table_style_three_line(self.doc)

    def test_b5_5_compact_zero_spacing_single_line(self):
        self.assert_compact_zero_spacing_single_line(self.doc)

    def test_b3_normal_bodytext_zero_after_keeps_indent(self):
        self.assert_normal_and_bodytext_zero_after(self.doc)


@unittest.skipUnless(HAS_PANDOC and HAS_PYTHON_DOCX, "需要 pandoc + python-docx")
class DefaultTierBuildTest(DefaultTierAssertionsMixin, unittest.TestCase):
    """内存重建默认档: 与随库产物同一组断言, 防脚本改动后忘记重生成 reference.docx。"""

    @classmethod
    def setUpClass(cls):
        cls.doc = build_reference_docx()

    def test_b5_1_table_style_three_line(self):
        self.assert_table_style_three_line(self.doc)

    def test_b5_5_compact_zero_spacing_single_line(self):
        self.assert_compact_zero_spacing_single_line(self.doc)

    def test_b3_normal_bodytext_zero_after_keeps_indent(self):
        self.assert_normal_and_bodytext_zero_after(self.doc)


@unittest.skipUnless(HAS_PANDOC and HAS_PYTHON_DOCX, "需要 pandoc + python-docx")
class LooseTierBuildTest(unittest.TestCase):
    """--loose 旧档: B3/B5①/B5⑤ 一概不叠加, 各样式保持 pandoc 旧值。"""

    @classmethod
    def setUpClass(cls):
        cls.doc = build_reference_docx(loose=True)

    def test_table_style_has_no_table_level_borders(self):
        self.assertIsNone(_tbl_border(_find_style(self.doc, "Table"), "top"))
        self.assertIsNone(_tbl_border(_find_style(self.doc, "Table"), "bottom"))

    def test_compact_keeps_legacy_spacing(self):
        pf = _find_style(self.doc, "Compact").paragraph_format
        self.assertEqual(Pt(1.8), pf.space_before)  # pandoc 默认 36 缇
        self.assertEqual(Pt(1.8), pf.space_after)
        self.assertIsNone(pf.line_spacing)  # 继承 (Normal 1.3 倍)
        self.assertEqual(Pt(0), pf.first_line_indent)  # 清首行缩进是旧行为, 保留

    def test_normal_bodytext_keep_legacy_after(self):
        normal = _find_style(self.doc, "Normal")
        self.assertIsNone(normal.paragraph_format.space_after)  # 继承 docDefaults 10pt
        self.assertEqual("200",
                         _attr(normal, "w:ind", qn("w:firstLineChars")))
        body_text = _find_style(self.doc, "Body Text")
        self.assertEqual(Pt(9), body_text.paragraph_format.space_after)


@unittest.skipUnless(HAS_PANDOC and HAS_PYTHON_DOCX, "需要 pandoc + python-docx")
class LooseCliTest(unittest.TestCase):
    """CLI --loose 分支冒烟: 退出码 0 且写出的文件为旧档 (无表级边框)。"""

    def test_loose_flag_writes_legacy_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "loose.docx"
            proc = subprocess.run(
                [sys.executable, str(BUILD_SCRIPT), "--loose", "-o", str(out)],
                capture_output=True)
            self.assertEqual(0, proc.returncode,
                             proc.stderr.decode("utf-8", "replace"))
            self.assertTrue(out.exists())
            doc = Document(str(out))
            self.assertIsNone(_tbl_border(_find_style(doc, "Table"), "top"))
            self.assertEqual(Pt(9),
                             _find_style(doc, "Body Text").paragraph_format.space_after)


if __name__ == "__main__":
    unittest.main()
