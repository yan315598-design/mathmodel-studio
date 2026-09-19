# -*- coding: utf-8 -*-
"""draw.io 作战地图模板（graphical_abstract_3band）单测（WP-B B3/B6 规格）。

覆盖: content JSON schema 校验（非法结构 ValueError）、JSON 驱动渲染 +
drawio_check 版式门（FAIL 0）、CLI 缺省文件名 F0_route.draft.drawio。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DRAWIO_DIR = (REPO_ROOT / "templates" / "figures" / "scripts" / "drawio")
TEMPLATE_PATH = DRAWIO_DIR / "make_drawio_graphical_abstract.py"


def load_module(path: Path, name: str):
    """从 drawio/ 目录加载待测模板（其内部自行注册 drawio_builder 导入路径）。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _valid_content() -> dict:
    """最小合法 content（两带, 覆盖必填字段与因果标签）。"""
    return {
        "title": "作战地图测试",
        "bands": [
            {"problem": "问题一", "question": "场如何演化",
             "methods": ["模型甲"],
             "key_result": "结果一", "key_detail": "e=0.1",
             "thumbnail": "F1.png", "causal_to_next": "输出 → 输入"},
            {"problem": "问题二", "question": "参数如何反演",
             "methods": ["模型乙", "模型丙"],
             "key_result": "结果二", "key_detail": "λ=0.42",
             "thumbnail": "F2.png"},
        ],
    }


class GraphicalAbstractContentTests(unittest.TestCase):
    """content JSON schema 校验。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(DRAWIO_DIR))
        cls.ga = load_module(TEMPLATE_PATH, "ga_template_for_tests")

    def test_valid_content_passes(self):
        normalized = self.ga.validate_content(_valid_content())
        self.assertEqual(len(normalized["bands"]), 2)
        self.assertEqual(normalized["title"], "作战地图测试")

    def test_top_level_not_dict_raises(self):
        with self.assertRaises(ValueError):
            self.ga.validate_content([1, 2])

    def test_bands_count_out_of_range_raises(self):
        content = _valid_content()
        content["bands"] = [content["bands"][0]]
        with self.assertRaises(ValueError):
            self.ga.validate_content(content)

    def test_missing_required_field_raises(self):
        content = _valid_content()
        del content["bands"][0]["key_result"]
        with self.assertRaises(ValueError):
            self.ga.validate_content(content)

    def test_bad_methods_raises(self):
        for bad in ([], ["方法甲", "方法乙", "方法丙", "方法丁"], ["方法甲", 7]):
            content = _valid_content()
            content["bands"][0]["methods"] = bad
            with self.assertRaises(ValueError):
                self.ga.validate_content(content)


class GraphicalAbstractRenderTests(unittest.TestCase):
    """JSON 驱动渲染 + drawio_check 版式门。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(DRAWIO_DIR))
        cls.ga = load_module(TEMPLATE_PATH, "ga_template_for_render_tests")

    def test_render_demo_passes_drawio_check(self):
        """内置三问示例: 落盘 XML 合法 + 版式体检 FAIL 0。"""
        import drawio_check
        import drawio_builder

        diagram = self.ga.build_graphical_abstract(self.ga.DEMO_CONTENT)
        with tempfile.TemporaryDirectory() as td:
            path = diagram.write(Path(td) / "ga_demo")
            vertices, edges = drawio_builder.validate_drawio_file(path)
            # 3 带 × (色带+标题条+缩略图) + 2-3 方法卡/结果卡 + 标题 + 2 因果箭头
            self.assertGreaterEqual(vertices, 16)
            self.assertEqual(edges, 2)
            fails, _warns = drawio_check.check_file(str(path))
            self.assertEqual(fails, [], msg="; ".join(fails))

    def test_render_custom_content_two_bands(self):
        """自定义两带内容: 渲染成功且因果箭头数 = 带数 - 1。"""
        import drawio_builder

        diagram = self.ga.build_graphical_abstract(_valid_content())
        self.assertEqual(diagram.edge_count, 1)
        with tempfile.TemporaryDirectory() as td:
            path = diagram.write(Path(td) / "ga_custom")
            vertices, edges = drawio_builder.validate_drawio_file(path)
            self.assertEqual(edges, 1)
            self.assertGreaterEqual(vertices, 10)


class GraphicalAbstractCliTests(unittest.TestCase):
    """CLI 行为: 缺省文件名 F0_route.draft.drawio（草稿协议）。"""

    def test_default_output_name_is_draft_protocol(self):
        with tempfile.TemporaryDirectory() as td:
            # 借道 --out 指到临时目录下的同名前缀, 校验 .drawio 后缀自动补全;
            # 缺省临时目录路径本身由 finalize/default_out_stem 约定覆盖
            stem = Path(td) / "F0_route.draft"
            result = subprocess.run(
                [sys.executable, str(TEMPLATE_PATH), "--out", str(stem)],
                capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            out = Path(str(stem) + ".drawio")
            self.assertTrue(out.is_file() and out.stat().st_size > 0,
                            f"缺省草稿文件缺失: {out}")

    def test_bad_content_file_returns_2(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text('{"bands": []}', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(TEMPLATE_PATH), "--content", str(bad)],
                capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("参数错误", result.stdout)


if __name__ == "__main__":
    unittest.main()
