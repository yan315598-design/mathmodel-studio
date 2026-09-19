"""pdf_qa 文本层工件扫描（A1）: 7 类模式命中 / 干净通过 / CLI 开关与退出码。

对应 2026 国赛 A 题实战三起构建事故（md 源码当正文、\times 写坏、
引用断链占位）的机器拦截回归用例。
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import shutil
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
PDFQA_PATH = SKILL_ROOT / "scripts" / "pdf_qa.py"

try:
    import fitz  # noqa: F401  生成测试 PDF 用
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


def load_module(path: Path, name: str):
    """从候选 skill 路径加载待测脚本。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ScanArtifactsUnitTests(unittest.TestCase):
    """scan_artifacts 纯函数级: 7 类模式 / 误报防护 / 上下文窗口。"""

    @classmethod
    def setUpClass(cls):
        cls.pdfqa = load_module(PDFQA_PATH, "pdfqa_for_artifact_unit_tests")

    def test_all_seven_patterns_detected(self):
        """一次喂入 7 类工件, 每类都必须命中且页码正确。"""
        text = (
            "前文。\n"
            "## 问题二 协同任务规划\n"            # md 标题残留（行首 ##）
            "|:---:|:---:|\n"                      # 管道表残留（分隔行）
            "量级为 3 imes 10 的情形\n"            # LaTeX 残骸（空格包裹 imes）
            "修复脚本把 \\frac 写坏\n"             # LaTeX 残骸（字面 \frac）
            "<span>样式残留</span>\n"              # HTML 残留
            "系数\ta\tb\r孤立回车\n"               # 控制字符（TAB + 孤立 CR）
            "错误!未找到引用源。\n"                 # 引用失败占位（半角 !）
            "全角变体错误！未找到引用源\n"          # 引用失败占位（全角 ！）
            "参数？？超限\n"                        # 引用失败占位（？？）
            "见[?]标注\n"                          # 引用失败占位（[?]）
            "$E = mc^2$ 能量关系\n"                # 未渲染数学定界
        )
        hits = self.pdfqa.scan_artifacts([text])
        names = {name for _page, name, _ctx in hits}
        for expected in ("md标题残留", "管道表残留", "LaTeX命令残骸", "HTML残留",
                         "控制字符", "引用失败占位", "未渲染数学定界"):
            self.assertIn(expected, names, f"模式 {expected} 未命中")
        pages = {page for page, _name, _ctx in hits}
        self.assertEqual(pages, {1}, "单页输入的命中页码应为 1")

    def test_hash_prefix_and_inline_heading(self):
        """行首 ### 经 ^## 前缀命中; 行内 " ## " 单独命中。"""
        hits = self.pdfqa.scan_artifacts(["### 三级标题\n正文中的 ## 井号标题\n"])
        contexts = [ctx for _p, n, ctx in hits if n == "md标题残留"]
        self.assertEqual(len(contexts), 2, "### 行首与行内 ## 应各命中一次")

    def test_digit_glued_imes_variants(self):
        """"9.1imes10-5"（TAB 被吞）与 "9.1 imes10-5"（TAB 归一空格）都命中。"""
        hits = self.pdfqa.scan_artifacts(["9.1imes10-5 一处\n9.1 imes10-5 另一处\n"])
        glued = [h for h in hits if h[1] == "LaTeX命令残骸"]
        self.assertEqual(len(glued), 2, "数字黏连 imes 的两种形态都应命中")

    def test_math_delimiter_rule(self):
        """行以 $ 开头且 $>=2 命中; 单 $ 或非行首不命中。"""
        text = "$x$ 单行成对\n$y 单定界\n价格 $5 一档\n$a$ 与 $b$ 并列\n总量 c=1\n"
        hits = [h for h in self.pdfqa.scan_artifacts([text]) if h[1] == "未渲染数学定界"]
        contexts = [ctx for _p, _n, ctx in hits]
        self.assertEqual(len(contexts), 2, "两个行首成对定界行应命中")
        self.assertNotIn("$y", "".join(contexts), "行首单 $ 不应命中（<2 次）")
        self.assertNotIn("$5", "".join(contexts), "非行首 $ 不应命中")

    def test_clean_text_no_false_positives(self):
        """正常英文/数学文本（times、trace、|A-B|、孤立 $）零命中。"""
        text = (
            "3 times 10 的量级, trace 记录与 rack 支架均正常。\n"
            "残差 |A-B| / |A|+|B| 定义见式 (10)。\n"
            "矩阵 a|b|c 分量正常, 价格 $5 一档。\n"
            "无工件正文第二行。\n"
        )
        self.assertEqual(self.pdfqa.scan_artifacts([text]), [],
                         "干净文本不应有任何工件命中")

    def test_context_window_and_escape(self):
        """上下文取命中点前后各 20 字符, 越界加省略号, 控制字符转义可见。"""
        text = "x" * 25 + " ## H" + "y" * 25 + "\n尾行\ta\n"
        hits = self.pdfqa.scan_artifacts([text])
        by_name = {}
        for _p, name, ctx in hits:
            by_name.setdefault(name, []).append(ctx)
        md_ctx = by_name["md标题残留"][0]
        self.assertTrue(md_ctx.startswith("…") and md_ctx.endswith("…"), "截断处应有省略号")
        self.assertIn(" ## H", md_ctx)
        self.assertIn("\\t", by_name["控制字符"][0], "TAB 应转义为 \\t 显示")

    def test_page_numbering(self):
        """第 2 页命中必须带页码 2（多页输入）。"""
        hits = self.pdfqa.scan_artifacts(["干净页。\n", "另一页。\n## 残留标题\n"])
        self.assertEqual([(p, n) for p, n, _c in hits], [(2, "md标题残留")])


@unittest.skipUnless(HAS_FITZ, "pymupdf 未安装, 无法现场生成测试 PDF")
class ArtifactScanCLITests(unittest.TestCase):
    """CLI 端到端: fitz 现场造 PDF（含工件/干净/混合）, 断言退出码与报告。"""

    @classmethod
    def setUpClass(cls):
        cls.pdfqa = load_module(PDFQA_PATH, "pdfqa_for_artifact_cli_tests")
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="pdfqa_artifacts_"))
        # 含工件 PDF: 第 1 页排版语法类, 第 2 页占位符类
        dirty_pages = [
            [
                "模型概述与求解流程说明。",
                "## 问题二 无人机集群协同任务规划",
                "|符号|含义|单位|",
                "|:---:|:---:|:---:|",
                "量级为 3 imes 10 的负五次方, 且 9.1imes10-5 为事故残留。",
                "\\frac{1}{2} 命令未编译。",
                "<span>样式片段原样印出。",
                "$E = mc^2$ 公式未转对象。",
            ],
            [
                "结果讨论章节正文。",
                "错误!未找到引用源。",
                "参数？？超出预期范围。",
                "标注见[?]处。",
            ],
        ]
        # 干净 PDF: 正常中英文正文, 不触任何模式与其余四类检查
        clean_pages = [
            [
                "灵敏度分析显示误差随迭代轮次单调下降, 验证了离散格式的数值稳定性。",
                "全部数字来自冻结台账, 图形由脚本自动生成并经机器门检查。",
                "The convergence criterion is satisfied across all grid levels.",
            ],
        ]
        # 混合 PDF: 第 1 页干净, 第 2 页才有工件
        mixed_pages = [
            ["干净的首页正文, 交代建模框架与假设条件。"],
            ["附录前的残留页。", "## 附录残留标题", "|---|---|"],
        ]
        cls.dirty_pdf = cls.tmpdir / "dirty.pdf"
        cls.clean_pdf = cls.tmpdir / "clean.pdf"
        cls.mixed_pdf = cls.tmpdir / "mixed.pdf"
        for path, pages in ((cls.dirty_pdf, dirty_pages),
                            (cls.clean_pdf, clean_pages),
                            (cls.mixed_pdf, mixed_pages)):
            cls._build_pdf(path, pages)

    @staticmethod
    def _build_pdf(path: Path, pages: list[list[str]]) -> None:
        """fitz 生成多页小 PDF; 文本框必须完全容纳, 否则测试数据不完整。"""
        doc = fitz.open()
        rect = fitz.Rect(50, 50, 545, 780)
        for lines in pages:
            page = doc.new_page()
            rc = page.insert_textbox(rect, "\n".join(lines),
                                     fontname="china-s", fontsize=11)
            assert rc >= 0, f"测试 PDF 文本溢出: {path.name}"
        doc.save(str(path))
        doc.close()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def run_cli(self, pdf: Path, *flags: str) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = self.pdfqa.main([str(pdf), *flags])
        return code, buf.getvalue()

    def test_dirty_pdf_reports_errors_with_pages(self):
        """含工件 PDF 报 ❌ 且逐条带页码与模式名, 退出码 1。"""
        code, out = self.run_cli(self.dirty_pdf)
        self.assertEqual(code, 1, "检出工件必须 exit 1")
        for name in ("md标题残留", "管道表残留", "LaTeX命令残骸", "HTML残留",
                     "未渲染数学定界", "引用失败占位"):
            self.assertIn(f"文本工件[{name}]", out, f"报告缺少 {name}")
        self.assertIn("第 1 页 文本工件[md标题残留]", out, "第 1 页命中缺页码")
        self.assertIn("第 2 页 文本工件[引用失败占位]", out, "第 2 页命中缺页码")
        self.assertIn("合计:", out)
        self.assertIn("❌", out)

    def test_clean_pdf_passes(self):
        """干净 PDF 工件扫描通过, 退出码 0。"""
        code, out = self.run_cli(self.clean_pdf)
        self.assertEqual(code, 0, "干净 PDF 不应产生 ❌")
        self.assertIn("文本层工件扫描通过", out)
        self.assertNotIn("文本工件[", out)

    def test_mixed_pdf_pages_attributed(self):
        """混合 PDF 只在第 2 页报工件, 第 1 页不受牵连。"""
        code, out = self.run_cli(self.mixed_pdf)
        self.assertEqual(code, 1)
        self.assertIn("第 2 页 文本工件[md标题残留]", out)
        self.assertNotIn("第 1 页 文本工件[", out, "干净页不应有工件命中")

    def test_no_artifact_scan_flag_skips(self):
        """--no-artifact-scan 跳过工件扫描: 同一脏 PDF 退出码回到 0。"""
        code, out = self.run_cli(self.dirty_pdf, "--no-artifact-scan")
        self.assertEqual(code, 0, "关闭工件扫描后脏 PDF 其余检查应全绿")
        self.assertIn("--no-artifact-scan 关闭文本层工件扫描", out)
        self.assertNotIn("文本工件[", out)
        self.assertNotIn("文本层工件扫描通过", out)


class PageMapTests(unittest.TestCase):
    """C3: --page-map 页码→首行关键词/图表编号 映射表 (视觉验收派发用)。"""

    @classmethod
    def setUpClass(cls):
        cls.pdf_qa = load_module(PDFQA_PATH, "pdf_qa_for_pagemap_tests")

    def test_page_map_marks_headings_and_numbers(self):
        pages = [
            "\n".join(["摘 要", "本文研究...", "图 1 示意", "表 2 汇总"]),
            "\n".join(["", "", "5.3 求解结果与分析", "正文...", "图 3 曲线"]),
            "",
        ]
        sheet = self.pdf_qa.build_page_map(pages)
        self.assertEqual(len(sheet), 3)
        self.assertTrue(sheet[0].startswith("p  1: 摘 要"))
        self.assertIn("[图 1; 表 2]", sheet[0])
        self.assertTrue(sheet[1].startswith("p  2: 5.3 求解结果与分析"))
        self.assertIn("[图 3]", sheet[1])
        self.assertIn("(空白页)", sheet[2])

    def test_page_map_cli_on_real_pdf(self):
        if not HAS_FITZ:
            self.skipTest("未安装 pymupdf, 无法生成/读取 PDF")
        import fitz

        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "t.pdf"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Dummy", fontname="helv")
            doc.save(str(pdf))
            doc.close()
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                rc = self.pdf_qa.main([str(pdf), "--page-map"])
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn("[page-map]", out)
            self.assertIn("p  1:", out)


if __name__ == "__main__":
    unittest.main()
