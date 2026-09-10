"""evals/run_eval.py 与 scripts/package_dist.py 的最小评测设施测试。

合成 fixture 全部在临时目录构造, 不依赖真实语料; 覆盖:
- build-holdout-index 的年份过滤正确性 (剔除数、保留年份完整、元数据保留)
- compare 的差异表输出 (metric/A/B/delta、缺失键、数值差值)
- package_dist 的排除规则 (scibox-* 剔除、state/.gitkeep 保留、VENDOR_NOTICES 生成)
- Regression* 系列: bug-reviewer 发现的 6 个 major 的回归测试
  (stdout 截断解析 / rc=2 误判 ok / year 强转 / version 路径遍历 /
   分发版路由死指引 / label 路径遍历)
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
RUN_EVAL_PATH = SKILL_ROOT / "evals" / "run_eval.py"
PACKAGE_DIST_PATH = SKILL_ROOT / "scripts" / "package_dist.py"


def load_module(path: Path, name: str):
    """从候选 skill 路径加载待测脚本。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_cases(years: dict[int, int]) -> list[dict]:
    """构造 {年份: 题数} 的合成案例数组。"""
    cases = []
    for year, n in years.items():
        for i in range(n):
            problem = chr(ord("A") + i)
            cases.append({"id": f"huaweibei_{year}_{problem}", "year": year,
                          "problem": problem, "title": f"合成题 {year}{problem}",
                          "paper_ids": [f"p{year}{i}"], "paper_count": 1})
    return cases


class BuildHoldoutIndexTests(unittest.TestCase):
    """build-holdout-index: 过滤指定年份后写镜像, 源文件不动。"""

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        cases_dir = self.tmp / "competitions" / "huaweibei" / "cases"
        cases_dir.mkdir(parents=True)
        self.cases = make_cases({2021: 2, 2023: 1, 2024: 3, 2025: 1})
        index = {"schema_version": "huaweibei-problems-1.0", "cases": self.cases}
        (cases_dir / "index.json").write_text(
            json.dumps(index, ensure_ascii=False), encoding="utf-8")
        annotations = {
            "schema_version": "huaweibei-manual-cases-1.0",
            "cases": [dict(c, paradigm=f"范式{c['problem']}",
                           consensus_chain=["步骤1", "步骤2"]) for c in self.cases],
            "v2_cleanup": {"date": "2026-01-01", "removed_noise_keys": ["x"],
                           "note": "元数据应原样保留"},
        }
        (cases_dir / "manual_review_annotations.json").write_text(
            json.dumps(annotations, ensure_ascii=False), encoding="utf-8")
        self.out = self.tmp / "holdout_out"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self):
        runner = load_module(RUN_EVAL_PATH, "run_eval_build")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = runner.main([
                "build-holdout-index", "--competition", "huaweibei",
                "--exclude-year", "2024", "--out", str(self.out),
                "--repo-root", str(self.tmp)])
        return runner, rc, buffer.getvalue()

    def test_filter_counts_and_stdout(self):
        """剔除年份后案例数正确, 打印剔除前后计数与被剔除 id。"""
        _, rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("7 -> 4", out)
        self.assertIn("剔除 3 条", out)
        for pid in ("huaweibei_2024_A", "huaweibei_2024_B", "huaweibei_2024_C"):
            self.assertIn(pid, out)

    def test_kept_years_intact_and_metadata_preserved(self):
        """保留年份案例一字不少, 顶层元数据 (v2_cleanup) 原样保留。"""
        _, rc, _ = self._run()
        self.assertEqual(rc, 0)
        mirror_cases = self.out / "competitions" / "huaweibei" / "cases"
        index = json.loads((mirror_cases / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["schema_version"], "huaweibei-problems-1.0")
        self.assertEqual([c["id"] for c in index["cases"]],
                         [c["id"] for c in self.cases if c["year"] != 2024])
        self.assertTrue(all(c["year"] != 2024 for c in index["cases"]))
        annotations = json.loads(
            (mirror_cases / "manual_review_annotations.json").read_text(encoding="utf-8"))
        self.assertEqual(len(annotations["cases"]), 4)
        self.assertEqual(annotations["v2_cleanup"]["note"], "元数据应原样保留")
        self.assertTrue(all("paradigm" in c for c in annotations["cases"]))

    def test_source_files_untouched(self):
        """镜像操作不修改源索引。"""
        src = self.tmp / "competitions" / "huaweibei" / "cases" / "index.json"
        before = src.read_text(encoding="utf-8")
        _, rc, _ = self._run()
        self.assertEqual(rc, 0)
        self.assertEqual(src.read_text(encoding="utf-8"), before)

    def test_missing_index_fails(self):
        """索引不存在时报错退出码 1。"""
        (self.tmp / "competitions" / "huaweibei" / "cases" / "index.json").unlink()
        runner = load_module(RUN_EVAL_PATH, "run_eval_build_missing")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = runner.main([
                "build-holdout-index", "--competition", "huaweibei",
                "--exclude-year", "2024", "--out", str(self.out),
                "--repo-root", str(self.tmp)])
        self.assertEqual(rc, 1)
        self.assertIn("[FAIL]", buffer.getvalue())


class CompareTests(unittest.TestCase):
    """compare: 指标差异表 (metric / A / B / delta)。"""

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_run(self, name: str, payload: dict) -> Path:
        path = self.tmp / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def _run_compare(self, path_a: Path, path_b: Path):
        runner = load_module(RUN_EVAL_PATH, "run_eval_compare")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = runner.main(["compare", str(path_a), str(path_b)])
        return rc, buffer.getvalue()

    def test_diff_table_rows(self):
        """数值差值带符号、缺失键标 <缺失>、相同值无 delta。"""
        run_a = {"tools": {"score_artifact_judge": {"final": 63.75, "exit_code": 0}},
                 "label": "a", "artifacts": {"files": [1, 2, 3]}}
        run_b = {"tools": {"score_artifact_judge": {"final": 75.0, "exit_code": 0,
                                                    "tier": "国一边缘"}},
                 "label": "b", "artifacts": {"files": [1, 2]}}
        path_a, path_b = self._write_run("a.json", run_a), self._write_run("b.json", run_b)
        rc, out = self._run_compare(path_a, path_b)
        self.assertEqual(rc, 0)
        self.assertIn("delta", out)
        self.assertIn("+11.25", out)
        self.assertIn("国一边缘", out)
        # A 缺 tier 键 → <缺失>
        self.assertRegex(out, r"tools\.score_artifact_judge\.tier\s+<缺失>")
        # 列表折叠为计数
        self.assertRegex(out, r"artifacts\.files\s+<list:3>\s+<list:2>")
        # 相同的 exit_code 显示 +0 (无回归)
        exit_line = next(l for l in out.splitlines() if "exit_code" in l)
        self.assertTrue(exit_line.rstrip().endswith("+0"), exit_line)

    def test_missing_file_fails(self):
        """结果文件不存在时退出码 1。"""
        path_a = self._write_run("a.json", {"label": "a"})
        rc, out = self._run_compare(path_a, self.tmp / "nope.json")
        self.assertEqual(rc, 1)
        self.assertIn("[FAIL]", out)


def build_fake_repo(root: Path) -> None:
    """构造覆盖全部排除规则的假仓库树。"""
    (root / ".git" / "objects").mkdir(parents=True)
    (root / ".git" / "objects" / "x.txt").write_text("git", encoding="utf-8")
    (root / ".pytest_cache" / "v").mkdir(parents=True)
    (root / ".pytest_cache" / "v" / "cache.json").write_text("{}", encoding="utf-8")
    (root / "%TEMP%" ).mkdir()
    (root / "%TEMP%" / "mm_rain.png").write_bytes(b"\x89PNG")
    (root / "scripts" / "__pycache__").mkdir(parents=True)
    (root / "scripts" / "__pycache__" / "pkg.cpython-313.pyc").write_text("pyc", encoding="utf-8")
    (root / "scripts" / "package_dist.py").write_text("# script", encoding="utf-8")
    (root / "state").mkdir()
    (root / "state" / ".gitkeep").write_text("占位说明", encoding="utf-8")
    (root / "state" / "knowledge_manifest.json").write_text("{}", encoding="utf-8")
    (root / "evals" / "results").mkdir(parents=True)
    (root / "evals" / "results" / "run_x.json").write_text("{}", encoding="utf-8")
    (root / "evals" / "run_eval.py").write_text("# eval", encoding="utf-8")
    vendor = root / "templates" / "figures" / "vendor"
    (vendor / "scibox-diagram").mkdir(parents=True)
    (vendor / "scibox-diagram" / "SKILL.md").write_text("upstream-no-license", encoding="utf-8")
    (vendor / "scibox-figure" / "tpl").mkdir(parents=True)
    (vendor / "scibox-figure" / "tpl" / "taylor.py").write_text("# tpl", encoding="utf-8")
    (vendor / "diagram-design").mkdir(parents=True)
    (vendor / "diagram-design" / "SKILL.md").write_text("mit-upstream", encoding="utf-8")
    (vendor / "VENDOR.md").write_text("# vendor", encoding="utf-8")
    (root / ".codex-plugin").mkdir()
    (root / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"name": "mathmodel-studio", "version": "9.9.9"}), encoding="utf-8")
    (root / "SKILL.md").write_text(
        "# skill\n\n高密度示意图默认走 `templates/figures/vendor/scibox-diagram/`。\n",
        encoding="utf-8")
    (root / "references").mkdir()
    (root / "references" / "figure_skill_bridge.md").write_text(
        "# 图表桥接\n\n差异数据图型走 `templates/figures/vendor/scibox-figure/`。\n",
        encoding="utf-8")
    (root / "dist").mkdir()
    (root / "dist" / "old.txt").write_text("旧包, 防自递归", encoding="utf-8")
    (root / ".mimosa" / "hook-state").mkdir(parents=True)
    (root / ".mimosa" / "hook-state" / "sess_x.json").write_text("{}", encoding="utf-8")
    (root / "outputs" / "figures").mkdir(parents=True)
    (root / "outputs" / "figures" / "_smoke_test.png").write_bytes(b"\x89PNG")


class PackageDistTests(unittest.TestCase):
    """package_dist: 排除规则与 VENDOR_NOTICES.md 生成。"""

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        build_fake_repo(self.repo)
        self.out = self.tmp / "dist_out"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *extra):
        packager = load_module(PACKAGE_DIST_PATH, "package_dist_test")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = packager.main(["--apply", "--out", str(self.out),
                                "--repo-root", str(self.repo), *extra])
        return packager, rc, buffer.getvalue()

    def _dest(self) -> Path:
        return self.out / "mathmodel-studio-9.9.9"

    def test_apply_exclusion_rules(self):
        """scibox-* 与缓存/运行时路径被剔除, 正常文件与 .gitkeep 保留。"""
        _, rc, _ = self._run()
        self.assertEqual(rc, 0)
        dest = self._dest()
        self.assertTrue((dest / "SKILL.md").exists())
        self.assertTrue((dest / "scripts" / "package_dist.py").exists())
        self.assertTrue((dest / "evals" / "run_eval.py").exists())
        self.assertTrue((dest / "templates" / "figures" / "vendor" / "VENDOR.md").exists())
        # MIT 上游保留, 无 LICENSE 上游剔除
        self.assertTrue((dest / "templates" / "figures" / "vendor" / "diagram-design").is_dir())
        self.assertFalse((dest / "templates" / "figures" / "vendor" / "scibox-diagram").exists())
        self.assertFalse((dest / "templates" / "figures" / "vendor" / "scibox-figure").exists())
        # state 只留 .gitkeep 且内容原样
        self.assertTrue((dest / "state" / ".gitkeep").exists())
        self.assertEqual((dest / "state" / ".gitkeep").read_text(encoding="utf-8"), "占位说明")
        self.assertFalse((dest / "state" / "knowledge_manifest.json").exists())
        # 缓存/运行时路径
        self.assertFalse((dest / ".git").exists())
        self.assertFalse((dest / ".pytest_cache").exists())
        self.assertFalse((dest / "scripts" / "__pycache__").exists())
        self.assertFalse((dest / "%TEMP%").exists())
        self.assertFalse((dest / "evals" / "results").exists())
        self.assertFalse((dest / ".mimosa").exists())
        self.assertFalse((dest / "outputs").exists())
        # dist 本体不进包 (防自递归)
        self.assertFalse((dest / "dist").exists())

    def test_vendor_notices_generated(self):
        """dist 根生成 VENDOR_NOTICES.md, 说明被剔除内容与降级影响。"""
        _, rc, _ = self._run()
        self.assertEqual(rc, 0)
        notices = self._dest() / "VENDOR_NOTICES.md"
        self.assertTrue(notices.exists())
        text = notices.read_text(encoding="utf-8")
        self.assertIn("scibox-diagram", text)
        self.assertIn("scibox-figure", text)
        self.assertIn("VENDOR.md", text)
        self.assertIn("diagram-design", text)

    def test_dry_run_writes_nothing(self):
        """默认 dry-run 不落盘, 打印统计。"""
        packager = load_module(PACKAGE_DIST_PATH, "package_dist_dry")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = packager.main(["--out", str(self.out), "--repo-root", str(self.repo)])
        self.assertEqual(rc, 0)
        self.assertFalse(self.out.exists())
        self.assertIn("9.9.9", buffer.getvalue())
        self.assertIn("[DRY-RUN]", buffer.getvalue())

    def test_reapply_refuses_overwrite(self):
        """目标已存在时拒绝覆盖, 退出码 1。"""
        _, rc, _ = self._run()
        self.assertEqual(rc, 0)
        _, rc2, out2 = self._run()
        self.assertEqual(rc2, 1)
        self.assertIn("拒绝覆盖", out2)


class RegressionMajor1Tests(unittest.TestCase):
    """major 1 回归: stdout 截断导致大 JSON 解析失败 (指标全丢)。

    旧实现只把 stdout 尾部 2000 字符传给解析器, 多子问 trace_claims 输出
    数十 KB 时 JSON 起始行被截掉 → parse_error 却记 status=ok。
    """

    def test_large_trace_output_parsed_from_full_stdout(self):
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        try:
            ws = tmp / "ws"
            (ws / "state").mkdir(parents=True)
            filler = "建模路线与验证手段的合成描述" * 12  # 每字段 ~150 字
            rows = [{"question_id": f"Q{i}", "question": f"题面 {filler}",
                     "model": f"模型 {filler}", "result": f"结果 {filler}",
                     "validation": f"验证 {filler}", "figure": f"图 {filler}",
                     "abstract_claim": f"主张 {filler}"} for i in range(60)]
            (ws / "state" / "paper_plan.json").write_text(
                json.dumps({"evidence_ledger": rows}, ensure_ascii=False), encoding="utf-8")
            runner = load_module(RUN_EVAL_PATH, "run_eval_major1")
            result = runner._score_trace_claims(ws)
            self.assertEqual(result["status"], "ok", result)
            self.assertEqual(result["rows"], 60)
            self.assertNotIn("parse_error", result)
            self.assertGreater(len(str(result)), 0)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_parse_tool_json_validates_required_keys(self):
        """末尾 JSON 缺必需字段/多 JSON 样行取错对象 → 返回失败原因而非误判。"""
        runner = load_module(RUN_EVAL_PATH, "run_eval_major1b")
        # 无关 JSON 打在末尾 → 缺 verdict 字段 → 拒绝
        payload, reason = runner._parse_tool_json('{"other": 1}\n', {"verdict"})
        self.assertIsNone(payload)
        self.assertIn("必需字段", reason)
        # 两个 JSON: 前者无关、末者是结果 → 取末者并过校验
        payload, reason = runner._parse_tool_json(
            '{"other": 1}\n{"verdict": "eligible", "final": 80}\n', {"verdict"})
        self.assertIsNone(reason)
        self.assertEqual(payload["verdict"], "eligible")
        # 完全没有 JSON
        payload, reason = runner._parse_tool_json("plain text\n", {"verdict"})
        self.assertIsNone(payload)
        self.assertIn("未找到", reason)


class RegressionMajor2Tests(unittest.TestCase):
    """major 2 回归: rc=2 (输入/IO 错) 被记 status=ok。

    旧实现不区分退出码语义; consistency_audit 对不存在的工作区返回 2。
    """

    def test_audit_exit2_is_error_not_ok(self):
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        try:
            not_a_dir = tmp / "file.txt"
            not_a_dir.write_text("x", encoding="utf-8")
            runner = load_module(RUN_EVAL_PATH, "run_eval_major2")
            result = runner._score_consistency_audit(not_a_dir)
            self.assertEqual(result["status"], "error", result)
            self.assertEqual(result["exit_code"], 2)
            self.assertIn("质量门", result["reason"])
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


class RegressionMajor3Tests(unittest.TestCase):
    """major 3 回归: year 强转 int 无保护 (None→TypeError, 'wat'→ValueError,
    2024.9→截断误剔除)。非法值必须给可读 [FAIL] 而非 traceback。"""

    def _make_index(self, tmp, bad_year):
        cases_dir = tmp / "competitions" / "huaweibei" / "cases"
        cases_dir.mkdir(parents=True, exist_ok=True)
        cases = [{"id": "huaweibei_2023_A", "year": 2023, "problem": "A"},
                 {"id": "huaweibei_bad_X", "year": bad_year, "problem": "X"}]
        (cases_dir / "index.json").write_text(
            json.dumps({"schema_version": "x", "cases": cases}, ensure_ascii=False),
            encoding="utf-8")
        return cases_dir

    def test_invalid_year_rejected_readable(self):
        import tempfile
        for bad_year in (None, "wat", 2024.9, True):
            with self.subTest(bad_year=bad_year):
                tmp = Path(tempfile.mkdtemp())
                try:
                    self._make_index(tmp, bad_year)
                    runner = load_module(RUN_EVAL_PATH, "run_eval_major3")
                    out = tmp / "mirror"
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        rc = runner.main([
                            "build-holdout-index", "--competition", "huaweibei",
                            "--exclude-year", "2024", "--out", str(out),
                            "--repo-root", str(tmp)])
                    self.assertEqual(rc, 1)
                    self.assertIn("[FAIL]", buffer.getvalue())
                    self.assertIn("huaweibei_bad_X", buffer.getvalue())
                    # 校验失败时不写半截镜像
                    self.assertFalse(out.exists())
                finally:
                    import shutil
                    shutil.rmtree(tmp, ignore_errors=True)

    def test_non_object_top_level_rejected(self):
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        try:
            cases_dir = tmp / "competitions" / "huaweibei" / "cases"
            cases_dir.mkdir(parents=True)
            (cases_dir / "index.json").write_text("[]", encoding="utf-8")
            runner = load_module(RUN_EVAL_PATH, "run_eval_major3b")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                rc = runner.main([
                    "build-holdout-index", "--competition", "huaweibei",
                    "--exclude-year", "2024", "--out", str(tmp / "mirror"),
                    "--repo-root", str(tmp)])
            self.assertEqual(rc, 1)
            self.assertIn("[FAIL]", buffer.getvalue())
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


class RegressionMajor4Tests(unittest.TestCase):
    """major 4 回归: plugin version 未校验直接拼路径 → 路径遍历写穿 dist 根。"""

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        build_fake_repo(self.repo)
        (self.repo / ".codex-plugin" / "plugin.json").write_text(
            json.dumps({"name": "mathmodel-studio", "version": "../../escaped"}),
            encoding="utf-8")
        self.out = self.tmp / "dist_out"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_version_traversal_rejected(self):
        packager = load_module(PACKAGE_DIST_PATH, "package_dist_major4")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = packager.main(["--apply", "--out", str(self.out),
                                "--repo-root", str(self.repo)])
        self.assertEqual(rc, 1, buffer.getvalue())
        self.assertIn("[FAIL]", buffer.getvalue())
        self.assertIn("version", buffer.getvalue())
        # 未创建任何目标 (含越界路径 tmp/escaped) 与 dist 根下的残留
        self.assertFalse((self.tmp / "escaped").exists())
        self.assertFalse(any(self.out.glob("mathmodel-studio-*")) if self.out.exists() else False)


class RegressionMajor5Tests(unittest.TestCase):
    """major 5 回归: 分发副本的路由文档仍指向被剔除的 vendor/scibox-*, 死指引。

    修复后 --apply 在分发副本的 SKILL.md / references/figure_skill_bridge.md
    顶部注入降级横幅, VENDOR_NOTICES 如实声明"分发版不可用"。
    """

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        build_fake_repo(self.repo)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_route_banner_injected_and_source_untouched(self):
        packager = load_module(PACKAGE_DIST_PATH, "package_dist_major5")
        out = self.tmp / "dist_out"
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = packager.main(["--apply", "--out", str(out),
                                "--repo-root", str(self.repo)])
        self.assertEqual(rc, 0, buffer.getvalue())
        dest = out / "mathmodel-studio-9.9.9"
        for rel in ("SKILL.md", "references/figure_skill_bridge.md"):
            dist_text = (dest / rel).read_text(encoding="utf-8")
            self.assertIn("分发版路由说明", dist_text)
            self.assertIn("scibox", dist_text)
            self.assertIn("VENDOR_NOTICES.md", dist_text)
            # 横幅在顶部
            self.assertTrue(dist_text.lstrip().startswith(">"), rel)
            # 源仓库原文件不动
            src_text = (self.repo / rel).read_text(encoding="utf-8")
            self.assertNotIn("分发版路由说明", src_text)
        notices = (dest / "VENDOR_NOTICES.md").read_text(encoding="utf-8")
        self.assertIn("不可用", notices)
        self.assertIn("figure_skill_bridge.md", notices)


class RegressionMajor6Tests(unittest.TestCase):
    """major 6 回归: --label 未净化直接做文件名, '../../x' 可写出 out-dir。"""

    def test_label_traversal_rejected_and_valid_accepted(self):
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        try:
            ws = tmp / "ws"
            ws.mkdir()
            runner = load_module(RUN_EVAL_PATH, "run_eval_major6")
            out_dir = tmp / "results"
            # 非法 label: 拒绝且不越界写文件
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                rc = runner.main(["score-run", "--workspace", str(ws),
                                  "--label", "../../escaped", "--out-dir", str(out_dir)])
            self.assertEqual(rc, 1)
            self.assertIn("[FAIL]", buffer.getvalue())
            self.assertIn("label", buffer.getvalue())
            self.assertFalse(list(tmp.glob("escaped_*.json")))
            self.assertFalse(list(out_dir.glob("*.json")) if out_dir.exists() else False)
            # 合法 label 正常落盘到 out-dir 内
            buffer_ok = io.StringIO()
            with contextlib.redirect_stdout(buffer_ok):
                rc_ok = runner.main(["score-run", "--workspace", str(ws),
                                     "--label", "holdout-2024_v2", "--out-dir", str(out_dir)])
            self.assertEqual(rc_ok, 0, buffer_ok.getvalue())
            written = list(out_dir.glob("holdout-2024_v2_*.json"))
            self.assertEqual(len(written), 1)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
