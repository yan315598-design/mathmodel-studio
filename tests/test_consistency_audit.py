"""consistency_audit 论文一致性审计: 干净样例 exit 0 / 脏样例 exit 1。"""

from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
