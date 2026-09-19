"""pdf_qa 图表题编号 key 跨语言规范化与重复检出（P2-2 自测用例）。"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
PDFQA_PATH = SKILL_ROOT / "scripts" / "pdf_qa.py"


def load_module(path: Path, name: str):
    """从候选 skill 路径加载待测脚本。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CaptionKeyTests(unittest.TestCase):
    """覆盖中英文前缀归一与跨语言重复计数。"""

    @classmethod
    def setUpClass(cls):
        cls.pdfqa = load_module(PDFQA_PATH, "pdfqa_for_caption_tests")

    def test_key_normalization(self):
        """图 1 / Figure 1 / Fig.1 归并为 figure:1; 表 1 / Table 1 归并为 table:1。"""
        pairs = {
            "图 1": "figure:1",
            "图1": "figure:1",
            "Figure 1": "figure:1",
            "Fig.1": "figure:1",
            "Fig. 1": "figure:1",
            "表 2": "table:2",
            "Table 2": "table:2",
            "图 01": "figure:1",  # 前导零归并
        }
        for prefix, expected in pairs.items():
            self.assertEqual(self.pdfqa.caption_key(prefix), expected, prefix)

    def test_cross_language_duplicate_detected(self):
        """中文 "图 1" 与英文 "Figure 1" 同编号必须算重复。"""
        text = (
            "图 1：灵敏度分析结果\n"
            "正文若干行, 不触发行首锚定。\n"
            "Figure 1: sensitivity result\n"
            "表 1：参数表\n"
            "Table 2: another table\n"
        )
        counter: dict[str, list[int]] = {}
        for m in self.pdfqa.CAPTION_PREFIX_RE.finditer(text):
            key = self.pdfqa.caption_key(m.group(1))
            counter.setdefault(key, []).append(m.start())
        self.assertEqual(len(counter["figure:1"]), 2, "跨语言同编号未归并")
        self.assertEqual(len(counter["table:1"]), 1)
        self.assertEqual(len(counter["table:2"]), 1)
        # "如图 1 所示" 这类非行首引用不应计入
        inline = "正文中提到 如图 1 所示 的引用"
        self.assertIsNone(self.pdfqa.CAPTION_PREFIX_RE.search(inline))


class CaptionFormTests(unittest.TestCase):
    """T-07 回归: 行首正文引用 (中文换行) 不算题注, 真重复题注仍报。"""

    @classmethod
    def setUpClass(cls):
        cls.pdfqa = load_module(PDFQA_PATH, "pdfqa_for_caption_form_tests")

    def test_line_start_body_reference_skipped(self):
        """行首接续词 ("表 3 与表 4 给出…") 是正文引用, 不计入题注。"""
        text = (
            "表 3 与表 4 给出题面要求的核心指标对比。\n"
            "图 2 显示误差随迭代轮次快速下降。\n"
            "表 1：参数取值范围\n"
        )
        _, groups = self.pdfqa.scan_captions([text])
        self.assertEqual({}, {k: v for k, v in groups.items() if k[0].startswith("table:3")},
                         "行首正文引用 '表 3 与表 4…' 不应计入题注")
        self.assertNotIn("figure:2", {k[0] for k in groups},
                         "行首正文引用 '图 2 显示…' 不应计入题注")

    def test_true_duplicate_caption_reported(self):
        """同一编号题注文本完全相同地出现两次 → 仍报重复。"""
        text = (
            "表 1：参数取值范围\n"
            "若干正文…\n"
            "表 1：参数取值范围\n"
        )
        counter, groups = self.pdfqa.scan_captions([text])
        self.assertEqual(len(groups[("table:1", "参数取值范围")]), 2)
        self.assertEqual(len(counter["table:1"]), 2)

    def test_same_key_different_text_not_duplicate(self):
        """同编号但后续文本不同 (一处题注、一处行首引用) → 不算重复。"""
        text = (
            "图 1：灵敏度分析结果\n"
            "图 1 给出三组参数下的灵敏度曲线对比情况。\n"
        )
        _, groups = self.pdfqa.scan_captions([text])
        self.assertEqual({}, {k: v for k, v in groups.items() if len(v) > 1},
                         "题注与行首引用文本不同, 不应报重复")


if __name__ == "__main__":
    unittest.main()
