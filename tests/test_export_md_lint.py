"""export_final_docx.py 的 md 卫生 lint 测试 (v3.1.0, 清单 A2 + 复审 H3/M4):

- 自动修复: ①标题行上一行非空且非标题 → 补空行; ②": 题注" 行与紧随表格/图片
  间缺空行 → 补 (连续标题/文档首行/已有空行不误修);
- 报错: ③TAB 控制字符; ⑤单段落 $ 计数奇数 (多行 $$ 块偶数不误报; H3: 行内
  code span 与 \\$ 转义剔除后再计数, 不误杀字面美元/代码示例);
- 警告: ④单元格 >28 字符且无空格/U+200B/CJK 的长 token (插零宽空格后消警);
- 代码围栏 (```/~~~) 内容一律豁免;
- M4: lint 逐源文件在读入原貌上执行——含 \\tag 的多行公式块压缩变换后,
  TAB 等行号仍按源文件行号报告;
- main() dry-run 接线: 修复打印摘要 / 致命项 exit 2 并列 文件:行。"""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from export_final_docx import MdLintFatal, lint_md, main

LONG_TOKEN = "code/very_long_module_name/pipeline_v3.py"  # 42 字符


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_main(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(argv)
    return rc, buf.getvalue()


class HeadingBlankLineFixTest(unittest.TestCase):
    def test_missing_blank_above_heading_fixed(self):
        md = "正文段落紧贴标题\n## 一 问题重述\n后文。\n"
        fixed, fixes, warns = lint_md(md)
        self.assertEqual("正文段落紧贴标题\n\n## 一 问题重述\n后文。\n", fixed)
        self.assertEqual(1, len(fixes))
        self.assertIn("拼接md:2", fixes[0])  # 报告原始行号 (标题所在行)
        self.assertEqual([], warns)

    def test_consecutive_headings_not_modified(self):
        md = "## 甲\n### 乙\n正文\n"
        fixed, fixes, _ = lint_md(md)
        self.assertEqual(md, fixed)
        self.assertEqual([], fixes)

    def test_heading_at_document_start_not_modified(self):
        md = "## 甲\n正文\n"
        self.assertEqual(md, lint_md(md)[0])

    def test_properly_spaced_heading_untouched(self):
        md = "正文\n\n## 甲\n"
        self.assertEqual(md, lint_md(md)[0])


class CaptionGapFixTest(unittest.TestCase):
    def test_caption_stuck_to_table_fixed(self):
        md = ": 表 1 数据\n| a | b |\n|---|---|\n| 1 | 2 |\n"
        fixed, fixes, _ = lint_md(md)
        self.assertIn(": 表 1 数据\n\n| a | b |", fixed)
        self.assertEqual(1, len(fixes))

    def test_caption_stuck_to_image_fixed(self):
        md = ": 图 1 图题\n![alt](figs/a.png)\n"
        fixed, fixes, _ = lint_md(md)
        self.assertIn(": 图 1 图题\n\n![alt](figs/a.png)", fixed)
        self.assertEqual(1, len(fixes))

    def test_caption_with_blank_gap_untouched(self):
        """本仓库 md 约定: 题注与表之间恰一空行 (pandoc 挂接口径), 不得再加。"""
        md = ": 表 1 数据\n\n| a | b |\n|---|---|\n"
        self.assertEqual(md, lint_md(md)[0])

    def test_caption_at_document_end_untouched(self):
        self.assertEqual(": 表 1\n", lint_md(": 表 1\n")[0])


class FatalLintTest(unittest.TestCase):
    def test_tab_raises_with_location(self):
        with self.assertRaises(MdLintFatal) as ctx:
            lint_md("正\t文\n第二行\t继续\n")
        problems = ctx.exception.problems
        self.assertEqual(2, len(problems))
        self.assertIn("拼接md:1", problems[0])
        self.assertIn("TAB", problems[0])
        self.assertIn("拼接md:2", problems[1])

    def test_odd_dollar_count_raises(self):
        with self.assertRaises(MdLintFatal) as ctx:
            lint_md("设 $x$ 与 $y 为变量\n")
        self.assertEqual(1, len(ctx.exception.problems))
        self.assertIn("奇数", ctx.exception.problems[0])
        self.assertIn("拼接md:1", ctx.exception.problems[0])

    def test_odd_dollar_reported_at_paragraph_start(self):
        """多行段落: 报段落首行行号; 围栏行/空行是段落边界。"""
        md = "段落首行\n第二行 $\n\n正常段 $ok$\n"
        with self.assertRaises(MdLintFatal) as ctx:
            lint_md(md)
        self.assertEqual(1, len(ctx.exception.problems))
        self.assertIn("拼接md:1", ctx.exception.problems[0])

    def test_multiline_display_math_even_count_ok(self):
        md = "引言。\n\n$$\nx = 1\n$$\n"
        fixed, fixes, warns = lint_md(md)
        self.assertEqual(md, fixed)
        self.assertEqual([], fixes)
        self.assertEqual([], warns)

    def test_even_inline_dollars_ok(self):
        self.assertEqual("甲 $a$ 乙 $b$ 丙\n", lint_md("甲 $a$ 乙 $b$ 丙\n")[0])

    def test_escaped_dollar_not_counted(self):
        """H3 回归: \\$ 是字面美元, 不参与定界计数。"""
        self.assertEqual("Price \\$5. 类元\n", lint_md("Price \\$5. 类元\n")[0])
        self.assertEqual("甲 \\$5 乙 $x$ 丙\n", lint_md("甲 \\$5 乙 $x$ 丙\n")[0])

    def test_even_backslash_count_keeps_dollar(self):
        r"""H3 回归: "\$x" 中 \\ 是字面反斜杠、$ 未被转义, 奇数计数仍报错。"""
        with self.assertRaises(MdLintFatal):
            lint_md("a \\\\$x\n")  # 源文本 a \\$x → $ 计 1

    def test_inline_code_span_dollar_not_counted(self):
        """H3 回归: 行内 code span 里的 $ 不是公式定界符。"""
        self.assertEqual("Use `$` as delimiter.\n",
                         lint_md("Use `$` as delimiter.\n")[0])
        self.assertEqual("``a $ b`` 结束\n", lint_md("``a $ b`` 结束\n")[0])

    def test_table_cell_formulas_not_killed(self):
        """H3 回归: 表格单元格内合法公式与字面美元不误杀。"""
        md = "| 公式 | 价格 |\n|---|---|\n| $f(x)=1$ | \\$5 |\n"
        fixed, _, warns = lint_md(md)
        self.assertEqual(md, fixed)
        self.assertEqual([], warns)  # 也不断行点误报


class LongTokenWarningTest(unittest.TestCase):
    def test_long_ascii_token_in_cell_warns(self):
        md = f"| 文件 | {LONG_TOKEN} |\n|---|---|\n| 1 | 2 |\n"
        fixed, fixes, warns = lint_md(md)
        self.assertEqual(md, fixed)  # 警告不改文本
        self.assertEqual(1, len(warns))
        self.assertIn("U+200B", warns[0])
        self.assertIn("拼接md:1", warns[0])

    def test_zero_width_space_silences_warning(self):
        token = LONG_TOKEN.replace("/", "/\u200b")
        md = f"| 文件 | {token} |\n|---|---|\n"
        _, _, warns = lint_md(md)
        self.assertEqual([], warns)

    def test_long_cjk_token_exempt(self):
        """CJK 字符 Word 可自然断行, 不属于断行点问题, 不警。"""
        cjk = "这是一段很长很长的中文说明文字超过二十八个字符没有空格出现" * 1
        self.assertGreater(len(cjk), 28)
        _, _, warns = lint_md(f"| 说明 | {cjk} |\n|---|---|\n")
        self.assertEqual([], warns)

    def test_short_token_ok(self):
        _, _, warns = lint_md("| a | short/name.py |\n|---|---|\n")
        self.assertEqual([], warns)


class FenceExemptionTest(unittest.TestCase):
    def test_fenced_content_exempt_from_all_rules(self):
        md = ("```python\n"
              "if\tx:\n"
              "    # 不是标题\n"
              f"    path = '{LONG_TOKEN}'\n"
              "    s = '$'\n"
              "```\n"
              "正文 $ok$\n")
        fixed, fixes, warns = lint_md(md)
        self.assertEqual(md, fixed)
        self.assertEqual([], fixes)
        self.assertEqual([], warns)

    def test_tilde_fence_dollar_exempt(self):
        self.assertEqual("~~~\n$$\n~~~\n", lint_md("~~~\n$$\n~~~\n")[0])

    def test_heading_below_open_fence_not_fixed(self):
        md = "~~~\n fenced ## 假标题\n"
        self.assertEqual(md, lint_md(md)[0])


class LocCallableTest(unittest.TestCase):
    def test_custom_loc_used_in_messages(self):
        with self.assertRaises(MdLintFatal) as ctx:
            lint_md("a\tb\n", loc=lambda n: f"01_x.md:{n}")
        self.assertIn("01_x.md:1", ctx.exception.problems[0])


class MainLintWiringTest(unittest.TestCase):
    """lint 在 pandoc 前 (dry-run 同样执行): 修复打印摘要、致命项 exit 2。"""

    def test_dry_run_reports_autofix_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "paper_workspace"
            _write(ws / "01_abstract.md", "摘要正文。\n")
            _write(ws / "02_body.md", "正文段\n## 一章\n")
            rc, out = _run_main(["--workspace", str(ws), "--out-dir",
                                 str(Path(tmp) / "s"), "--dry-run"])
            self.assertEqual(0, rc)
            self.assertIn("[lint] md 卫生自动修复 1 处", out)
            self.assertIn("02_body.md:2", out)  # 文件:行 归因

    def test_dry_run_tab_fatals_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "paper_workspace"
            _write(ws / "01_abstract.md", "摘要\t正文。\n")
            rc, out = _run_main(["--workspace", str(ws), "--dry-run"])
            self.assertEqual(2, rc)
            self.assertIn("md 卫生 lint 拦截 1 处", out)
            self.assertIn("01_abstract.md:1", out)

    def test_dry_run_odd_dollar_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "paper_workspace"
            _write(ws / "01_abstract.md", "摘要正文。\n\n设 $x 为变量\n")
            rc, out = _run_main(["--workspace", str(ws), "--dry-run"])
            self.assertEqual(2, rc)
            self.assertIn("奇数", out)

    def test_dry_run_long_token_warns_but_exits_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "paper_workspace"
            _write(ws / "01_abstract.md", "摘要正文。\n")
            _write(ws / "02_body.md",
                   f"## 一章\n\n: 表题\n\n| 文件 |\n|---|\n| {LONG_TOKEN} |\n")
            rc, out = _run_main(["--workspace", str(ws), "--out-dir",
                                 str(Path(tmp) / "s"), "--dry-run"])
            self.assertEqual(0, rc)
            self.assertIn("[WARN]", out)
            self.assertIn("U+200B", out)

    def test_line_numbers_survive_tag_compression(self):
        """M4 回归: \\tag 多行公式块在后续 normalize_md_tag 会被压缩减行,
        但 lint 在读入原貌上先执行——TAB 行号必须报源文件真实行号。"""
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "paper_workspace"
            _write(ws / "01_abstract.md",
                   "摘要正文。\n"
                   "\n"
                   "$$\n"
                   "x = 1 \\tag{5}\n"
                   "$$\n"
                   "\n"
                   "正\t文带 TAB\n")  # TAB 在源文件第 7 行
            rc, out = _run_main(["--workspace", str(ws), "--dry-run"])
            self.assertEqual(2, rc)
            self.assertIn("01_abstract.md:7", out)

    def test_multi_file_tab_attributed_to_own_file(self):
        """M4 回归: 多文件拼接场景, TAB 归因到所在文件与其文件内行号。"""
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "paper_workspace"
            _write(ws / "01_abstract.md", "摘要。\n\n$$\na = 2\n$$\n")
            _write(ws / "02_body.md", "正文。\n\n带\tTAB 行\n")  # 02 第 3 行
            rc, out = _run_main(["--workspace", str(ws), "--dry-run"])
            self.assertEqual(2, rc)
            self.assertIn("02_body.md:3", out)
            self.assertNotIn("01_abstract.md:3", out)


if __name__ == "__main__":
    unittest.main()
