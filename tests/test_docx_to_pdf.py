"""docx_to_pdf.py 转换调度的单元测试 (不依赖真实 Word/soffice, 用假转换器):
P1-6 旧 PDF 不得被当新转换成功 / 临时目录原子替换与清理;
P2-9 假成功降级下一条、退出码 1/2 分流。"""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import docx_to_pdf
from docx_to_pdf import main, try_converters


def _noop_converter(docx_path, pdf_path):
    """假成功: 什么都不写 (模拟转换器静默失败/残留旧文件场景)。"""


def _ok_converter(docx_path, pdf_path):
    pdf_path.write_bytes(b"NEW-PDF")


def _bad_converter(docx_path, pdf_path):
    raise RuntimeError("boom")


class TryConvertersTest(unittest.TestCase):
    def _setup(self, tmp: str):
        docx = Path(tmp) / "final.docx"
        docx.write_bytes(b"PK-fake")
        target = Path(tmp) / "final.pdf"
        return docx, target

    def test_silent_converter_leaves_stale_pdf_untouched(self):
        """P1-6 回归: 转换器无产物时, 目标旁已存在的旧 PDF 不得被当作本次成功。"""
        with tempfile.TemporaryDirectory() as tmp:
            docx, target = self._setup(tmp)
            target.write_bytes(b"OLD-PDF")
            rc, name = try_converters([("fake", _noop_converter)], docx, target)
            self.assertEqual(1, rc)
            self.assertIsNone(name)
            self.assertEqual(b"OLD-PDF", target.read_bytes())  # 旧文件原样未动

    def test_successful_converter_atomically_replaces_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            docx, target = self._setup(tmp)
            target.write_bytes(b"OLD-PDF")
            rc, name = try_converters([("fake", _ok_converter)], docx, target)
            self.assertEqual(0, rc)
            self.assertEqual("fake", name)
            self.assertEqual(b"NEW-PDF", target.read_bytes())
            leftovers = [p for p in Path(tmp).iterdir()
                         if p.name.startswith(".docx2pdf_tmp_")]
            self.assertEqual([], leftovers)  # 临时目录用后即删

    def test_failed_converter_falls_through_to_next(self):
        """P2-9 回归: 首条转换器抛错后降级尝试下一条, 不直接判败。"""
        with tempfile.TemporaryDirectory() as tmp:
            docx, target = self._setup(tmp)
            rc, name = try_converters(
                [("bad", _bad_converter), ("good", _ok_converter)], docx, target)
            self.assertEqual(0, rc)
            self.assertEqual("good", name)
            self.assertEqual(b"NEW-PDF", target.read_bytes())

    def test_all_converters_fail_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            docx, target = self._setup(tmp)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc, name = try_converters(
                    [("bad1", _bad_converter), ("silent", _noop_converter)],
                    docx, target)
            self.assertEqual(1, rc)
            self.assertIsNone(name)
            self.assertIn("bad1", buf.getvalue())
            self.assertIn("silent", buf.getvalue())

    def test_tmp_dir_is_exclusive_and_only_own_removed(self):
        """v3.1.0: 临时目录用 mkdtemp 独占 (原 PID+ms 命名会被并发进程互删),
        且只清自己那次创建的目录 —— 外来同前缀目录不得被删。"""
        with tempfile.TemporaryDirectory() as tmp:
            docx, target = self._setup(tmp)
            foreign = Path(tmp) / ".docx2pdf_tmp_foreign"
            foreign.mkdir()
            (foreign / "keep.txt").write_bytes(b"FOREIGN")
            seen = []

            def _record_and_write(docx_path, pdf_path):
                seen.append(pdf_path.parent)
                pdf_path.write_bytes(b"NEW-PDF")

            rc, _name = try_converters([("fake", _record_and_write)], docx, target)
            self.assertEqual(0, rc)
            self.assertEqual(1, len(seen))
            self.assertNotEqual(foreign, seen[0])        # 不与外来目录同名
            self.assertFalse(seen[0].exists())           # 自己的目录已清理
            self.assertTrue((foreign / "keep.txt").is_file())  # 外来目录原样保留

    def test_two_concurrent_runs_use_distinct_tmp_dirs(self):
        """两次转换各自 mkdtemp: 目录名必不重复 (并发互删的根本原因已消除)。"""
        with tempfile.TemporaryDirectory() as tmp:
            docx, target = self._setup(tmp)
            seen = []

            def _record_and_fail(docx_path, pdf_path):
                seen.append(pdf_path.parent)
                raise RuntimeError("boom")

            with contextlib.redirect_stdout(io.StringIO()):
                try_converters([("a", _record_and_fail)], docx, target)
                try_converters([("b", _record_and_fail)], docx, target)
            self.assertEqual(2, len(seen))
            self.assertNotEqual(seen[0], seen[1])
            self.assertTrue(all(not d.exists() for d in seen))

    def test_missing_target_parent_dir_is_created(self):
        """--out 指向尚不存在的子目录: 先建父目录再 mkdtemp, 不得抛未捕获异常。"""
        with tempfile.TemporaryDirectory() as tmp:
            docx, _ = self._setup(tmp)
            target = Path(tmp) / "out" / "deep" / "final.pdf"
            with contextlib.redirect_stdout(io.StringIO()):
                rc, name = try_converters([("ok", _ok_converter)], docx, target)
            self.assertEqual(0, rc)
            self.assertEqual("ok", name)
            self.assertEqual(b"NEW-PDF", target.read_bytes())

    def test_tmp_dir_creation_failure_returns_1(self):
        """mkdtemp/mkdir 失败 → 记错误并降级, 返回 (1, None), 不抛异常。"""
        with tempfile.TemporaryDirectory() as tmp:
            docx, target = self._setup(tmp)
            original = docx_to_pdf.tempfile.mkdtemp

            def _boom(*a, **kw):
                raise OSError("mkdtemp boom")

            docx_to_pdf.tempfile.mkdtemp = _boom
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc, name = try_converters([("fake", _ok_converter)], docx, target)
            finally:
                docx_to_pdf.tempfile.mkdtemp = original
            self.assertEqual(1, rc)
            self.assertIsNone(name)
            self.assertIn("临时目录创建失败", buf.getvalue())


class MainExitCodeTest(unittest.TestCase):
    def test_no_converters_available_exits_2(self):
        """P2-9 回归: 无任何可用转换器 = 环境错误 exit 2。"""
        with tempfile.TemporaryDirectory() as tmp:
            docx = Path(tmp) / "f.docx"
            docx.write_bytes(b"PK")
            original = docx_to_pdf.available_converters
            docx_to_pdf.available_converters = lambda: []
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = main([str(docx)])
            finally:
                docx_to_pdf.available_converters = original
            self.assertEqual(2, rc)

    def test_converter_present_but_failing_exits_1(self):
        """P2-9 回归: 转换器存在但转换失败 = 业务失败 exit 1 (非 2)。"""
        with tempfile.TemporaryDirectory() as tmp:
            docx = Path(tmp) / "f.docx"
            docx.write_bytes(b"PK")
            original = docx_to_pdf.available_converters
            docx_to_pdf.available_converters = lambda: [("fake", _bad_converter)]
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = main([str(docx)])
            finally:
                docx_to_pdf.available_converters = original
            self.assertEqual(1, rc)

    def test_missing_docx_exits_2(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main([str(Path("___nope___.docx"))])
        self.assertEqual(2, rc)


if __name__ == "__main__":
    unittest.main()
