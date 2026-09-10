"""package_submission.py gate 8 门禁预检的行为测试。

覆盖: gate 8 通过放行 / 未过拒绝 (含中文缺失项摘要) / --allow-gate-fail
降级警告 / decision_log 缺失或损坏仅提示不拦截; 以及 dry-run 明示
"正式打包会被拒绝" 但退出码仍 0 的既有口径。
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SUBMISSION_PATH = SKILL_ROOT / "scripts" / "package_submission.py"


def load_module(path: Path, name: str):
    """从候选 skill 路径加载待测脚本。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_pdf(path: Path) -> None:
    """生成单页含文本层的最小合法 PDF, 让论文/pdf_qa 检查可走通。"""
    content = b"BT /F1 12 Tf 72 720 Td (Submission smoke paper text.) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
         b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"),
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (i, obj)
    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objects) + 1, xref_pos))
    path.write_bytes(bytes(out))


def _passing_log():
    """gate 8 放行 (scores['8'] 合法) 且带 competition 的 decision_log。"""
    return {
        "competition": "cumcm",
        "scores": {"8": [{"iteration": 0, "scores": {"1_abstract_5_paragraph": 8},
                          "min": 8, "mean": 8.0, "verdict": "pass",
                          "ts": "2026-09-08T12:00:00"}]},
        "stages": {},
        "checkpoints": {},
    }


def _failing_log():
    """缺评分/必停点登记 (scores 为空) 的 decision_log, gate 8 必拦。"""
    return {"competition": "cumcm", "scores": {}, "stages": {}, "checkpoints": {}}


class Gate8PrecheckTests(unittest.TestCase):
    """main 层面: gate 8 预检决定打包放行/拒绝; dry-run 同样预检。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ws = self.tmp / "ws"
        (self.ws / "state").mkdir(parents=True)
        make_pdf(self.ws / "paper.pdf")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_log(self, log):
        (self.ws / "state" / "decision_log.json").write_text(
            json.dumps(log, ensure_ascii=False), encoding="utf-8")

    def _run(self, argv):
        """在临时 workspace 下跑 main (脚本以 cwd 为工作区), 捕获退出码与输出。"""
        runner = load_module(PACKAGE_SUBMISSION_PATH, "pkg_submission_gate8")
        buffer = io.StringIO()
        old_cwd = Path.cwd()
        os.chdir(self.ws)
        try:
            with contextlib.redirect_stdout(buffer):
                rc = runner.main(argv)
        finally:
            os.chdir(old_cwd)
        return rc, buffer.getvalue()

    def test_gate8_pass_packs(self):
        """gate 8 已过: --apply 正常打包, 报告含 ok 行。"""
        self._write_log(_passing_log())
        rc, out = self._run(["--apply"])
        self.assertEqual(rc, 0)
        self.assertIn("gate 8 已过", out)
        self.assertIn("打包完成", out)

    def test_gate8_fail_rejected_with_missing_summary(self):
        """gate 8 未过: --apply 拒绝打包, 输出含中文缺失项与逃生开关提示。"""
        self._write_log(_failing_log())
        rc, out = self._run(["--apply"])
        self.assertEqual(rc, 1)
        self.assertIn("gate 8 未过", out)
        self.assertIn("scores['8']", out)  # check_gate 的中文缺失项摘要
        self.assertIn("--allow-gate-fail", out)
        self.assertNotIn("打包完成", out)

    def test_gate8_fail_dry_run_warns_will_be_rejected(self):
        """dry-run 同样预检并明示会被拒绝, 但退出码保持 0 (预览不阻断)。"""
        self._write_log(_failing_log())
        rc, out = self._run([])
        self.assertEqual(rc, 0)
        self.assertIn("gate 8 未过", out)
        self.assertIn("正式打包 (--apply) 会被拒绝", out)

    def test_allow_gate_fail_packs_with_warning(self):
        """--allow-gate-fail: 降级放行并打印醒目中文警告, 打包不被拒。"""
        self._write_log(_failing_log())
        rc, out = self._run(["--apply", "--allow-gate-fail"])
        self.assertEqual(rc, 0)
        self.assertIn("已在 gate 8 门禁未通过的情况下继续打包", out)
        self.assertIn("必停点登记", out)
        self.assertIn("打包完成", out)

    def test_missing_decision_log_warns_not_blocks(self):
        """state/decision_log.json 缺失: 仅 ⚠️ 未校验, 不拦截 --competition 覆盖流程。"""
        rc, out = self._run(["--apply", "--competition", "cumcm"])
        self.assertEqual(rc, 0)
        self.assertIn("gate 8 未校验", out)
        self.assertNotIn("gate 8 未过", out)
        self.assertIn("打包完成", out)

    def test_corrupt_decision_log_warns_not_blocks(self):
        """decision_log 损坏 (非法 JSON): 同缺失口径, 仅 ⚠️ 不拦截。"""
        (self.ws / "state" / "decision_log.json").write_text("{not json", encoding="utf-8")
        rc, out = self._run(["--apply", "--competition", "cumcm"])
        self.assertEqual(rc, 0)
        self.assertIn("gate 8 未校验", out)


if __name__ == "__main__":
    unittest.main()
