"""decision_log 模板的 final_chain 字段（v2.9.1 终稿链选择）回归测试。

模板 templates/shared/decision_log.json 必须：
- 是合法 JSON；
- 含 final_chain 字段且默认 "tex"；
- 文档注释枚举只允许 tex | docx（与 stage_08 终稿链选择菜单一致）。
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_ROOT / "templates" / "shared" / "decision_log.json"


class FinalChainTemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    def test_template_is_valid_json(self):
        self.assertIsInstance(self.data, dict)

    def test_final_chain_default_tex(self):
        self.assertEqual("tex", self.data.get("final_chain"),
                         "final_chain 缺省必须是 tex（LaTeX 链为默认终稿链）")

    def test_final_chain_doc_enum(self):
        doc = self.data.get("_final_chain_doc", "")
        self.assertIn("tex", doc)
        self.assertIn("docx", doc)
        self.assertIn("样张先行", doc, "_final_chain_doc 应说明选择时机（stage 8 样张先行）")

    def test_schema_version_unchanged(self):
        # final_chain 是正交新字段, 不改变 schema 版本契约
        self.assertEqual("3.2", self.data.get("_schema_version"))


if __name__ == "__main__":
    unittest.main()
