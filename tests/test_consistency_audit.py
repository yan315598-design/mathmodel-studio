"""consistency_audit 论文一致性审计: 干净样例 exit 0 / 脏样例 exit 1。"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
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


def _build_ws(root: Path, fixture: str, frozen: dict | None,
              version_files: list[str]) -> Path:
    ws = root / ("ws_" + fixture.removesuffix(".md"))
    paper = ws / "paper_workspace"
    paper.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FIXTURES / fixture, paper / fixture)
    if frozen is not None:
        (ws / "state").mkdir(exist_ok=True)
        (ws / "state" / "frozen_numbers.json").write_text(
            json.dumps(frozen, ensure_ascii=False, indent=2), encoding="utf-8")
    for name in version_files:
        (ws / name).write_text("", encoding="utf-8")
    return ws


FROZEN = {
    "q2.unit_cost": {"value": 4368, "unit": "元/吨",
                     "source_file": "results/q2.json", "source_sha256": "x"},
    "q2.reduce": {"value": 12.5, "unit": "%"},
    "q3.cap": {"value": 2000, "unit": "MWh"},
}


class ConsistencyAuditTests(unittest.TestCase):
    """干净样例零检出 exit 0; 脏样例五项全命中 exit 1。"""

    @classmethod
    def setUpClass(cls):
        cls.audit = load_module(AUDIT_PATH, "consistency_audit")

    def test_clean_sample_exit_0(self):
        with tempfile.TemporaryDirectory(prefix="audit_clean_") as td:
            ws = _build_ws(Path(td), "consistency_audit_clean.md", None, [])
            rc = self.audit.main(["--workspace", str(ws)])
        self.assertEqual(rc, 0, "干净样例应 exit 0 (无任何检出)")

    def test_clean_sample_zero_findings(self):
        with tempfile.TemporaryDirectory(prefix="audit_clean_") as td:
            ws = _build_ws(Path(td), "consistency_audit_clean.md", None, [])
            result = self.audit.run_audit(ws, None)
        self.assertEqual(result["error"], 0)
        self.assertEqual(result["warn"], 0, "干净样例不应有任何 ⚠️/❌ 检出")

    def test_dirty_sample_exit_1_with_all_checks(self):
        with tempfile.TemporaryDirectory(prefix="audit_dirty_") as td:
            ws = _build_ws(Path(td), "consistency_audit_dirty.md",
                           FROZEN, ["论文_最终版.docx", "摘要_副本.md"])
            rc = self.audit.main(["--workspace", str(ws)])
            result = self.audit.run_audit(ws, None)
        self.assertEqual(rc, 1, "脏样例应 exit 1 (存在 ❌)")
        self.assertGreaterEqual(result["error"], 1)
        kinds = {(f["check"], f["severity"]) for f in result["findings"]}
        for need in [(1, "error"), (2, "error"), (3, "error"),
                     (1, "warn"), (3, "warn"), (4, "warn"), (5, "warn")]:
            self.assertIn(need, kinds,
                          f"脏样例应检出 {need}: "
                          + str([f["msg"] for f in result["findings"] if f["check"] == need[0]]))

    def test_json_output_shape(self):
        with tempfile.TemporaryDirectory(prefix="audit_json_") as td:
            ws = _build_ws(Path(td), "consistency_audit_dirty.md",
                           FROZEN, ["论文_最终版.docx", "摘要_副本.md"])
            result = self.audit.run_audit(ws, None)
        j = self.audit.to_json(result)
        self.assertEqual(j["exit_code"], 1)
        self.assertEqual(j["summary"]["error"], result["error"])
        self.assertEqual(len(j["checks"]), 5)
        self.assertTrue(all(c["status"] in ("ok", "warn", "error", "skipped")
                            for c in j["checks"]))

    def test_missing_workspace_exit_2(self):
        with tempfile.TemporaryDirectory(prefix="audit_miss_") as td:
            rc = self.audit.main(["--workspace", str(Path(td) / "nope")])
        self.assertEqual(rc, 2, "工作区不存在应 exit 2")

    def test_tex_autonumber_refs_close(self):
        """T-06 回归: caption 不手写 "图 N" 的自动编号 + 正文纯文本引用应闭环。

        \label{fig:3} 的数字部分与 longtable 内 caption 计数序均应计入定义集,
        "图 3"/"表 1" 不得再报 "引用了未定义的编号"。
        """
        with tempfile.TemporaryDirectory(prefix="audit_autonum_") as td:
            ws = _build_ws(Path(td), "consistency_audit_autonum.tex", None, [])
            result = self.audit.run_audit(ws, None)
        stats3 = result["stats"][3]
        self.assertEqual(
            stats3["error"], 0,
            str([f["msg"] for f in result["findings"] if f["check"] == 3]))
        self.assertEqual(result["exit"], 0, "自动编号闭环样例应 exit 0")

    # ---- v3.1.1: 归档过滤只按工作区相对目录名 (绝对路径同名父目录不再误排除) ----

    def _ws_under(self, td: str, *segments: str) -> Path:
        """把工作区建在指定路径片段下 (片段含 tmp/results 等 SKIP_DIRS 名)。"""
        ws = Path(td).joinpath(*segments)
        paper = ws / "paper_workspace"
        paper.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FIXTURES / "consistency_audit_clean.md", paper / "main.md")
        return ws

    def test_workspace_under_tmp_segment_still_audits(self):
        """回归: 工作区绝对路径含 tmp 段时, 正文不得被判为已归档而漏检全部正文
        (修复前 collect_body_files 直接抛 "paper_workspace 下未找到 .md/.tex")。"""
        for segment in ("tmp", "results", "state", "code"):
            with tempfile.TemporaryDirectory(prefix="audit_skipdir_") as td:
                ws = self._ws_under(td, segment, "ws")
                files = self.audit.collect_body_files(ws, None)
                self.assertEqual(1, len(files), segment)
                self.assertEqual("main.md", files[0].name, segment)
                result = self.audit.run_audit(ws, None)
                self.assertEqual(0, result["error"], segment)
                self.assertEqual(0, result["warn"], segment)
                self.assertEqual(0, result["exit"], segment)

    def test_nested_archive_dirs_inside_workspace_still_excluded(self):
        """对照: 工作区**内部**的 _archive/ 与 tmp/ 正文仍不参与审计 (原语义保留)。"""
        with tempfile.TemporaryDirectory(prefix="audit_archive_") as td:
            ws = self._ws_under(td, "tmp", "ws")
            paper = ws / "paper_workspace"
            for name in ("_archive/old.md", "tmp/scratch.tex", "submission/copy.md"):
                path = paper / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(FIXTURES / "consistency_audit_dirty.md", path)
            files = self.audit.collect_body_files(ws, None)
            self.assertEqual(["main.md"], [f.name for f in files])
            result = self.audit.run_audit(ws, None)
            self.assertEqual(0, result["exit"], "归档目录内的脏稿不得参与审计")

    def test_paper_dir_mode_keeps_relative_archive_filter(self):
        """--paper 指向目录时, 归档过滤仍按工作区相对目录名生效。"""
        with tempfile.TemporaryDirectory(prefix="audit_paperdir_") as td:
            ws = self._ws_under(td, "tmp", "ws")
            sections = ws / "paper_workspace" / "sections"
            sections.mkdir(parents=True, exist_ok=True)
            shutil.copy2(FIXTURES / "consistency_audit_clean.md", sections / "sub.md")
            (sections / "_archive").mkdir()
            shutil.copy2(FIXTURES / "consistency_audit_dirty.md",
                         sections / "_archive" / "old.md")
            files = self.audit.collect_body_files(ws, str(sections))
            names = sorted(f.name for f in files)
            self.assertEqual(["sub.md"], names)
            result = self.audit.run_audit(ws, str(sections))
            self.assertEqual(0, result["exit"])

    def test_summary_caps_printed_findings_and_reports_detail_path(self):
        """人读输出是摘要: 每检查最多 PRINT_FINDINGS_CAP 处; --report 落盘完整报告。"""
        with tempfile.TemporaryDirectory(prefix="audit_report_") as td:
            ws = _build_ws(Path(td), "consistency_audit_dirty.md",
                           FROZEN, ["论文_最终版.docx", "摘要_副本.md"])
            report_path = Path(td) / "state" / "audit_report.json"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = self.audit.main(["--workspace", str(ws),
                                      "--report", str(report_path)])
            out = buf.getvalue()
            self.assertEqual(rc, 1)
            self.assertIn("详细报告:", out)
            data = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(1, data["exit_code"])
            clean = self.audit.to_json(self.audit.run_audit(ws, None))
            self.assertEqual(clean["summary"], data["summary"])
            printed = [ln for ln in out.splitlines() if ln.startswith("  ") and "[" in ln]
            self.assertLessEqual(len(printed), 5 * self.audit.PRINT_FINDINGS_CAP)
        # 未给 --report 时给出去哪儿看完整清单的指路行
        with tempfile.TemporaryDirectory(prefix="audit_summary_") as td:
            ws = _build_ws(Path(td), "consistency_audit_dirty.md",
                           FROZEN, ["论文_最终版.docx", "摘要_副本.md"])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = self.audit.main(["--workspace", str(ws)])
            self.assertEqual(rc, 1)
            self.assertIn("完整清单: --json", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
