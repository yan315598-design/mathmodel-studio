"""ref_order_audit.py 的行为测试: 正确顺序 pass / 乱序报期望序 / 孤立文献 /
未定义引用 / 数学区间不误报 / 围栏与行内代码不计 / 章节密度 ⚠️ / CLI 退出码。"""

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ref_order_audit import audit_ref_order, main


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


REFS_2 = "## 参考文献\n\n[1] 张三. 方法甲[J]. 应用数学, 2023.\n\n[2] Smith J. Method B[J]. OR, 2024.\n"
REFS_3 = ("## 参考文献\n\n[1] 张三. 方法甲[J]. 应用数学, 2023.\n\n"
          "[2] Smith J. Method B[J]. OR, 2024.\n\n[3] 李四. 方法丙[M]. 北京: 高教社, 2020.\n")


class RefOrderAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _audit(self, files: dict) -> dict:
        entries = []
        for name, text in files.items():
            p = self.root / name
            _write(p, text)
            entries.append((name, p))
        return audit_ref_order(entries)

    @staticmethod
    def _rules(report, rule):
        return [f for f in report["findings"] if f["rule"] == rule]

    def test_correct_order_passes(self):
        report = self._audit({
            "refs.md": REFS_2,
            "body.md": "## 模型建立\n\n如文献[1]所示。文献[2]给出对照。\n",
        })
        self.assertEqual(0, report["n_fail"])
        self.assertEqual([1, 2], report["first_cite_sequence"])
        self.assertEqual("body.md:3", report["first_cite_locations"]["1"])

    def test_combined_citation_forms_parsed(self):
        """[N]/[a,b]/[a-b]/[a,b-c] 四种形态都计入首引序列。"""
        report = self._audit({
            "refs.md": ("## 参考文献\n\n" + "".join(
                f"[{i}] 作者{i}. 题目{i}[J]. 期刊, 2020.\n" for i in range(1, 10))),
            "body.md": "见[1]与[2,3]、[4-6]、[7,8-9]。\n",
        })
        self.assertEqual(list(range(1, 10)), report["first_cite_sequence"])
        self.assertEqual(0, report["n_fail"])

    def test_disorder_reports_expected_vs_actual(self):
        """首引即 [2] 必须报 fail, 且含期望序 vs 实际序。"""
        report = self._audit({
            "refs.md": REFS_2,
            "body.md": "如文献[2]所示，文献[1]给出基础。\n",
        })
        fails = self._rules(report, "first_cite_order")
        self.assertEqual(1, len(fails))
        self.assertIn("[2]", fails[0]["detail"])
        self.assertIn("[1]", fails[0]["detail"])
        self.assertIn("期望", fails[0]["detail"])

    def test_orphan_reference_fails(self):
        """文献表定义 [2] 但正文从未引用 → 孤立文献 fail。"""
        report = self._audit({
            "refs.md": REFS_2,
            "body.md": "如文献[1]所示。\n",
        })
        fails = self._rules(report, "orphan_reference")
        self.assertEqual(1, len(fails))
        self.assertIn("[2]", fails[0]["detail"])

    def test_undefined_citation_fails(self):
        """文献表编号跳跃 (缺 [3]), 正文引用 [3] → 未定义引用 fail。"""
        refs_gap = ("## 参考文献\n\n[1] 张三. 甲[J]. 期刊, 2023.\n\n"
                    "[2] 李四. 乙[J]. 期刊, 2024.\n\n[4] 王. 丁[J]. 期刊, 2025.\n")
        report = self._audit({
            "refs.md": refs_gap,
            "body.md": "文献[1]与[2]为基础，[3]为对照。\n",
        })
        fails = self._rules(report, "undefined_citation")
        self.assertEqual(1, len(fails))
        self.assertIn("[3]", fails[0]["detail"])

    def test_math_interval_not_false_positive(self):
        """$[0,1]$ 数学区间不计引用; 行内 $[1,1]$ 同样被数学段屏蔽。"""
        report = self._audit({
            "refs.md": "## 参考文献\n\n[1] 张三. 甲[J]. 期刊, 2023.\n",
            "body.md": "取 $x\\in[0,1]$；权重在 $[1,1]$ 内取值。如文献[1]所示。\n",
        })
        self.assertEqual([1], report["cited_numbers"])
        self.assertEqual([], [f for f in report["findings"] if f["level"] == "fail"])

    def test_out_of_range_bracket_is_warn_not_fail(self):
        """正文中 [40,80] 形似引用但超范围 → 只 ⚠️ 提示, 不 fail。"""
        report = self._audit({
            "refs.md": REFS_3,
            "body.md": "初始区间取 [40,80]；如文献[1]、[2,3]所示。\n",
        })
        self.assertEqual(0, report["n_fail"])
        self.assertEqual(1, len(self._rules(report, "out_of_range_bracket")))

    def test_fenced_and_inline_code_not_counted(self):
        """围栏内 `[2]` 与行内代码 span 中的 [2] 都不计引用。"""
        report = self._audit({
            "refs.md": REFS_2,
            "body.md": ("如文献[1]所示。\n\n```python\nidx = arr[2]\nrefs = [2]\n```\n\n"
                        "见 `x[2]` 处。\n"),
        })
        self.assertNotIn(2, [int(k) for k in report["first_cite_locations"]])
        fails = self._rules(report, "orphan_reference")
        self.assertEqual(1, len(fails))

    def test_zero_citation_chapter_warned(self):
        """零引用一级章列 ⚠️; 参考文献/附录章不计入密度检查。"""
        report = self._audit({
            "refs.md": "## 参考文献\n\n[1] 张三. 方法甲[J]. 应用数学, 2023.\n",
            "body.md": ("## 问题重述\n\n重述内容。\n\n## 模型建立\n\n如文献[1]所示。\n\n"
                        "## 附录 A 代码\n\nprint(1)\n"),
        })
        warns = self._rules(report, "zero_citation_chapter")
        self.assertEqual(1, len(warns))
        self.assertIn("问题重述", warns[0]["detail"])
        self.assertNotIn("附录", warns[0]["detail"])
        self.assertNotIn("参考文献", warns[0]["detail"])
        self.assertEqual(0, report["n_fail"])

    def test_no_reference_section_fails(self):
        report = self._audit({"body.md": "如文献[1]所示。\n"})
        self.assertEqual(1, len(self._rules(report, "no_reference_section")))
        self.assertEqual([], report["cited_numbers"])

    def test_workspace_mode_orders_files_naturally(self):
        """--workspace 按 01..10 自然排序: 跨文件首引顺序 1,2 pass; 2,1 fail。"""
        ws = self.root / "proj"
        good = {
            "01_intro.md": "如文献[1]所示。\n",
            "10_body.md": "文献[2]给出对照。\n",
            "09_references.md": REFS_2,
        }
        for name, text in good.items():
            _write(ws / "paper_workspace" / name, text)
        from ref_order_audit import _collect_workspace
        entries = _collect_workspace(ws)
        self.assertEqual(["01_intro.md", "09_references.md", "10_body.md"],
                         [name for name, _ in entries])
        report = audit_ref_order(entries)
        self.assertEqual(0, report["n_fail"])

        bad = {
            "01_intro.md": "如文献[2]所示。\n",
            "10_body.md": "文献[1]给出基础。\n",
            "09_references.md": REFS_2,
        }
        for name, text in bad.items():
            _write(ws / "paper_workspace" / name, text)
        report = audit_ref_order(_collect_workspace(ws))
        self.assertEqual(1, len(self._rules(report, "first_cite_order")))

    def test_cli_exit_codes(self):
        """clean 稿 exit 0; 乱序稿 exit 1。"""
        _write(self.root / "clean.md", "## 模型\n\n如文献[1]所示，文献[2]给出对照。\n\n" + REFS_2)
        _write(self.root / "dirty.md", "如文献[2]所示，文献[1]为基础。\n\n" + REFS_2)
        for fname, expected in (("clean.md", 0), ("dirty.md", 1)):
            with patch.object(sys, "argv",
                              ["ref_order_audit.py", "--files", str(self.root / fname)]):
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = main()
            self.assertEqual(expected, rc, fname)


class RefOrderV310Test(unittest.TestCase):
    """v3.1.0 口径修复: {-} 标题 / 旧 bibitem / 变长围栏 / 只审导出稿。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _audit(self, files: dict) -> dict:
        entries = []
        for name, text in files.items():
            p = self.root / name
            _write(p, text)
            entries.append((name, p))
        return audit_ref_order(entries)

    @staticmethod
    def _rules(report, rule):
        return [f for f in report["findings"] if f["rule"] == rule]

    def test_unnumbered_marked_refs_heading_recognized(self):
        """参考文献标题带 pandoc {-} 时仍须认出文献表 (此前报 no_reference_section)。"""
        report = self._audit({
            "09_references.md": "## 参考文献 {-}\n\n[1] 张三. 甲[J]. 期刊, 2023.\n",
            "02_body.md": "## 模型建立\n\n如文献[1]所示。\n",
        })
        self.assertEqual(0, report["n_fail"])
        self.assertEqual([1], report["first_cite_sequence"])

    def test_old_bibitem_entries_recognized(self):
        """真源里的旧式 \\bibitem 条目按出现顺序计为文献表 (与导出转 [N] 同序)。"""
        refs = ("## 参考文献 {-}\n\n"
                "\\bibitem{r1} 张三. 甲[J]. 期刊, 2023.\n\n"
                "\\bibitem[模板]{r2} 李四. 乙[M]. 北京: 高教社, 2024.\n")
        ok = self._audit({"09_references.md": refs,
                          "02_body.md": "## 模型建立\n\n文献[1]与[2]为基础。\n"})
        self.assertEqual(0, ok["n_fail"])
        self.assertEqual([1, 2], ok["first_cite_sequence"])
        orphan = self._audit({"09_references.md": refs,
                              "02_body.md": "如文献[1]所示。\n"})
        self.assertEqual(1, len(self._rules(orphan, "orphan_reference")))

    def test_four_backtick_fence_content_not_counted(self):
        """四反引号围栏内的 ``` 不提前闭栏 → 栏内 [2] 不计引用。"""
        body = ("## 模型建立\n\n如文献[1]所示。\n\n"
                "````\n```\nidx = arr[2]\n```\n````\n")
        report = self._audit({
            "refs.md": "## 参考文献\n\n[1] 张三. 甲[J]. 期刊, 2023.\n",
            "body.md": body,
        })
        self.assertEqual([1], report["cited_numbers"])
        self.assertEqual(0, report["n_fail"])

    def test_workspace_mode_audits_only_export_sources(self):
        """--workspace 只审会被导出的 md: notes/README 里的 [2] 不再污染审计。"""
        ws = self.root / "proj" / "paper_workspace"
        _write(ws / "01_abstract.md", "如文献[1]所示。\n")
        _write(ws / "09_references.md", REFS_2)
        _write(ws / "notes.md", "草稿: 这里写了 [2] 与 [9] 的想法。\n")
        _write(ws / "README.md", "参见 [2]。\n")
        from ref_order_audit import _collect_workspace
        entries = _collect_workspace(self.root / "proj")
        self.assertEqual(["01_abstract.md", "09_references.md"],
                         [name for name, _ in entries])
        report = audit_ref_order(entries, discovery="nn_series")
        self.assertEqual([1], report["first_cite_sequence"])
        self.assertEqual("nn_series", report["discovery"])


    def test_refs_file_without_heading_audited_as_references(self):
        """P2: 09_references.md 只有 bibitem 无标题 → 与导出同源认定整文件即文献表,
        不再误报 no_reference_section, 且 defined 与导出的 [N] 编号一致。"""
        ws = self.root / "proj" / "paper_workspace"
        _write(ws / "01_body.md", "## 模型建立\n\n如文献[1]所示。\n")
        _write(ws / "09_references.md", "\\bibitem{r1} 张三. 甲[J]. 期刊, 2023.\n")
        from ref_order_audit import _collect_workspace
        report = audit_ref_order(_collect_workspace(self.root / "proj"))
        self.assertEqual([], [f["rule"] for f in report["findings"]])
        self.assertEqual([1], report["defined_numbers"])
        self.assertEqual([1], report["first_cite_sequence"])


    def test_bibitem_outside_refs_warns(self):
        """不在文献表区内的 \\bibitem: 导出不转换 → 审计必须报 ⚠️, 不得静默 pass。"""
        report = self._audit({
            "02_body.md": ("## 模型建立\n\n如文献[1]所示。\n\n"
                           "\\bibitem{stray} 漏在正文里的条目\n"),
            "09_references.md": "## 参考文献\n\n[1] 张三. 甲[J]. 期刊, 2023.\n",
        })
        warns = [f for f in report["findings"] if f["rule"] == "bibitem_outside_refs"]
        self.assertEqual(1, len(warns))
        self.assertIn("02_body.md:5", warns[0]["detail"])
        self.assertEqual(0, report["n_fail"])   # 编号顺序本身没问题, 只提示


if __name__ == "__main__":
    unittest.main()
