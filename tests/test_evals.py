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
import re
import subprocess
import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
RUN_EVAL_PATH = SKILL_ROOT / "evals" / "run_eval.py"
PACKAGE_DIST_PATH = SKILL_ROOT / "scripts" / "package_dist.py"


def load_module(path: Path, name: str):
    """从候选 skill 路径加载待测脚本 (package_dist 含 @dataclass, 须先注册进 sys.modules)。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def make_link_or_skip(link: Path, target: Path) -> str:
    """在 link 处建指向 target 的目录链接; 返回 "symlink"/"junction"。

    Windows 无开发者模式时 os.symlink 抛特权错误, 退回 NTFS junction ——
    junction 的 is_symlink() 为 False, 只能靠 reparse 属性识别, 正是逃逸高发形态。
    """
    try:
        link.symlink_to(target, target_is_directory=True)
        return "symlink"
    except (OSError, NotImplementedError) as exc:
        created = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                                 capture_output=True)
        if created.returncode != 0:
            raise unittest.SkipTest(f"当前环境无法创建符号链接/junction: {exc}")
        return "junction"


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
    (root / "LICENSE").write_text("MIT", encoding="utf-8")
    # SKILL.md 带 YAML frontmatter: 横幅必须插在闭合 frontmatter 之后 (否则技能发现失效)
    (root / "SKILL.md").write_text(
        "---\nname: mathmodel-studio\ndescription: 合成技能\n---\n\n"
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
    # ---- 凭证/内部材料 (任意层级, 与 git 是否跟踪无关) ----
    (root / ".env").write_text("OPENAI" + "_API_KEY=placeholder-value-16\n", encoding="utf-8")
    (root / "secrets.json").write_text("{}", encoding="utf-8")
    (root / "references" / "secrets.json").write_text("{}", encoding="utf-8")
    (root / "references" / "notes.pem").write_text("pem", encoding="utf-8")
    (root / "references" / "private.md").write_text("内部草稿", encoding="utf-8")
    (root / "_internal_notes").mkdir()
    (root / "_internal_notes" / "private.md").write_text("内部笔记", encoding="utf-8")
    (root / "templates" / "_internal_notes").mkdir()
    (root / "templates" / "_internal_notes" / "deep.md").write_text("嵌套内部笔记", encoding="utf-8")
    # 凭证容器目录 (容器内文件常无扩展名, 不能被"后缀白名单扫描"兜住, 必须整棵剔除)
    (root / ".aws").mkdir()
    (root / ".aws" / "credentials").write_text("[default]\naws_access_key_id = placeholder\n",
                                               encoding="utf-8")
    (root / ".ssh").mkdir()
    (root / ".ssh" / "config").write_text("Host *\n  User placeholder\n", encoding="utf-8")
    (root / ".gnupg").mkdir()
    (root / ".gnupg" / "secring.gpg").write_bytes(b"gpg")
    (root / "references" / "credentials").write_text("token: placeholder\n", encoding="utf-8")
    # ---- 备份/临时/归档 (含 backup 前缀形态) ----
    (root / "tmp").mkdir()
    (root / "tmp" / "scratch.txt").write_text("临时", encoding="utf-8")
    (root / "backup").mkdir()
    (root / "backup" / "old_main.md").write_text("备份", encoding="utf-8")
    (root / "backup-2024").mkdir()
    (root / "backup-2024" / "paper.md").write_text("备份前缀", encoding="utf-8")
    (root / "backups_old").mkdir()
    (root / "backups_old" / "deep.md").write_text("备份前缀", encoding="utf-8")
    (root / "_archive" / "2025-v0").mkdir(parents=True)
    (root / "_archive" / "2025-v0" / "main.md").write_text("归档", encoding="utf-8")
    (root / "main.md.bak").write_text("备份", encoding="utf-8")
    (root / "references" / "draft.md.tmp").write_text("临时", encoding="utf-8")
    (root / "~$paper.docx").write_text("Office 锁文件残留", encoding="utf-8")
    # ---- 非公开项目材料: 用户工作区真实产出 + 人读本地语料 + 实战成品图 ----
    (root / "figures").mkdir()
    (root / "figures" / "q1_field.png").write_bytes(b"\x89PNG")
    (root / "results").mkdir()
    (root / "results" / "answer.json").write_text("{\"Q1\": 1}", encoding="utf-8")
    golden = root / "templates" / "figures" / "gallery" / "golden"
    golden.mkdir(parents=True)
    (golden / "Q1_C1_field.png").write_bytes(b"\x89PNG-project")
    (golden / "Q2_C1_stages.png").write_bytes(b"\x89PNG-project")
    (golden / "Q34_C1_gridconv.png").write_bytes(b"\x89PNG-project")
    (golden / "Q4_C2_routes.png").write_bytes(b"\x89PNG-project")
    # 大小写变体: 大小写不敏感文件系统上是同一张真实项目图, deny 必须归一命中
    (golden / "q1_c1_field.png").write_bytes(b"\x89PNG-project-lower")
    (golden / "make_answer_grid.png").write_bytes(b"\x89PNG-template")
    (root / "templates" / "figures" / "gallery" / "README.md").write_text(
        "# Golden Gallery\n\nQ1_C1_field.png 为实战成品。\n", encoding="utf-8")
    # ---- 白名单外内容 (用户工作区/未知顶层) ----
    (root / "paper_workspace").mkdir()
    (root / "paper_workspace" / "main.md").write_text("用户论文", encoding="utf-8")
    (root / "problem.txt").write_text("散落题面", encoding="utf-8")
    # ---- 开发测试与归档档 ----
    (root / "tests").mkdir()
    (root / "tests" / "test_x.py").write_text("# test", encoding="utf-8")
    (root / "docs" / "legacy").mkdir(parents=True)
    (root / "docs" / "legacy" / "architecture.md").write_text("# 归档", encoding="utf-8")
    (root / "maintenance" / "cumcm").mkdir(parents=True)
    (root / "maintenance" / "cumcm" / "case_library.md").write_text("# 人读库", encoding="utf-8")
    (root / "maintenance" / "cumcm" / "all_cases_manual_audit.md").write_text(
        "# 逐篇审读稿", encoding="utf-8")
    (root / "scripts" / "legacy").mkdir(parents=True)
    (root / "scripts" / "legacy" / "ingest_papers.py").write_text("# legacy", encoding="utf-8")


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
        _, rc, out = self._run()
        self.assertEqual(rc, 0, out)
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


class PackageSafetyRulesTests(unittest.TestCase):
    """package_dist 安全语义 (规格: 发布选择白名单三档 + 默认入包禁区)。

    覆盖: 凭证/内部材料/备份临时/非公开项目材料默认剔除 (无论 git tracked/ignored);
    真实项目图只做选择隔离、源仓库原件不删不移; 白名单外内容默认不放行;
    符号链接不跟随 (防路径逃逸); 文本疑似敏感扫描的阻断与脱敏; 发布清单与明细落点。
    """

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        build_fake_repo(self.repo)
        self.out = self.tmp / "dist_out"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, out: Path | None = None, *extra: str) -> tuple[int, str]:
        packager = load_module(PACKAGE_DIST_PATH, "package_dist_safety")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = packager.main(["--apply", "--out", str(out or self.out),
                                "--repo-root", str(self.repo), *extra])
        return rc, buffer.getvalue()

    def _dry(self, *extra: str) -> tuple[int, str]:
        packager = load_module(PACKAGE_DIST_PATH, "package_dist_safety_dry")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = packager.main(["--out", str(self.out), "--repo-root", str(self.repo), *extra])
        return rc, buffer.getvalue()

    def _dest(self, out: Path | None = None) -> Path:
        return (out or self.out) / "mathmodel-studio-9.9.9"

    def test_credentials_internal_and_backups_never_packed(self):
        """凭证/内部笔记/备份临时默认剔除, 与 git 是否跟踪无关 (按磁盘实况遍历)。"""
        rc, out = self._run()
        self.assertEqual(rc, 0, out)
        dest = self._dest()
        for rel in (".env", "secrets.json", "references/secrets.json", "references/notes.pem",
                    "references/private.md", "_internal_notes", "references/_internal_notes",
                    "templates/_internal_notes", "tmp", "backup", "_archive",
                    "main.md.bak", "references/draft.md.tmp", "~$paper.docx"):
            self.assertFalse((dest / rel).exists(), rel)
        # 源仓库原件未被删改 (只做选择隔离, 不删不移)
        self.assertTrue((self.repo / ".env").exists())
        self.assertTrue((self.repo / "_internal_notes" / "private.md").exists())
        self.assertTrue((self.repo / "templates" / "_internal_notes" / "deep.md").exists())

    def test_real_project_materials_isolated_not_deleted(self):
        """真实项目图/结果目录只做选择隔离; 模板样张与源仓库原件保留。"""
        rc, out = self._run()
        self.assertEqual(rc, 0, out)
        dest = self._dest()
        for rel in ("figures", "results"):
            self.assertFalse((dest / rel).exists(), rel)
        golden = dest / "templates" / "figures" / "gallery" / "golden"
        for name in ("Q1_C1_field.png", "Q2_C1_stages.png",
                     "Q34_C1_gridconv.png", "Q4_C2_routes.png"):
            self.assertFalse((golden / name).exists(), name)
            self.assertTrue(
                (self.repo / "templates" / "figures" / "gallery" / "golden" / name).exists())
        self.assertTrue((golden / "make_answer_grid.png").exists())

    def test_whitelist_default_deny(self):
        """白名单外内容 (用户工作区/散落文件) 默认不放行, dry-run 如实列出。"""
        rc, out = self._dry()
        self.assertEqual(rc, 0)
        self.assertIn("白名单外内容", out)
        # 目录级剪枝: 只记工作区目录本身, 不逐文件展开; 展示路径统一哈希化
        self.assertGreaterEqual(out.count("(不在发布选择白名单"), 2)
        self.assertNotIn("paper_workspace", out)
        self.assertNotIn("problem.txt", out)
        # 纳入清单同样哈希化: 不回显任何仓库相对路径
        self.assertNotIn("SKILL.md", out)
        self.assertNotIn("scripts/", out)
        self.assertIn("[runtime]", out)
        self.assertIn("[dev]", out)

    def test_dev_tier_optional(self):
        """开发测试档默认纳入, --no-dev 整档剔除; 运行资源不受影响。"""
        rc, out = self._run()
        self.assertEqual(rc, 0, out)
        dest = self._dest()
        for rel in ("tests/test_x.py", "evals/run_eval.py", "docs/legacy/architecture.md",
                    "scripts/legacy/ingest_papers.py"):
            self.assertTrue((dest / rel).exists(), rel)
        out2 = self.tmp / "dist_nodev"
        rc2, out2_text = self._run(out2, "--no-dev")
        self.assertEqual(rc2, 0, out2_text)
        dest2 = self._dest(out2)
        for rel in ("tests", "evals", "docs", "scripts/legacy"):
            self.assertFalse((dest2 / rel).exists(), rel)
        self.assertTrue((dest2 / "scripts" / "package_dist.py").exists())
        self.assertTrue((dest2 / "references" / "figure_skill_bridge.md").exists())
        self.assertIn("未纳入 (--no-dev)", (dest2 / "PACKAGE_CONTENTS.md").read_text(encoding="utf-8"))

    def test_maintenance_local_corpus_excluded_by_default(self):
        """人读本地语料 maintenance/ 默认按非公开材料剔除 (原件保留), 不依赖 --no-dev。"""
        packager = load_module(PACKAGE_DIST_PATH, "package_dist_maintenance")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = packager.main(["--out", str(self.out), "--repo-root", str(self.repo)])
        self.assertEqual(rc, 0)
        dry = buffer.getvalue()
        self.assertIn("(人读本地语料库", dry)
        self.assertNotIn("maintenance", dry)   # 剔除清单统一哈希化, 不回显原路径
        rc2, out2 = self._run()
        self.assertEqual(rc2, 0, out2)
        dest = self._dest()
        self.assertFalse((dest / "maintenance").exists())
        # 仅 --no-dev 删除不构成保护: 默认运行就必须拦住, 且原件分毫不动
        self.assertTrue((self.repo / "maintenance" / "cumcm" / "case_library.md").exists())
        self.assertTrue((self.repo / "maintenance" / "cumcm" / "all_cases_manual_audit.md").exists())
        manifest = (dest / "PACKAGE_CONTENTS.md").read_text(encoding="utf-8")
        # 清单只写资源名 maintenance（不带路径斜杠）: 该资源不在包内, 写成路径形态
        # 在分发副本里就是死链 (2026-09-19 公开修正)
        self.assertIn("maintenance", manifest)
        self.assertIn("人读本地语料库", manifest)

    def test_credential_containers_and_backup_prefixes_excluded(self):
        """凭证容器目录 (.aws/.ssh/.gnupg) 与 backup 前缀目录默认剔除 (容器内无扩展名也拦)。"""
        rc, out = self._run()
        self.assertEqual(rc, 0, out)
        dest = self._dest()
        for rel in (".aws", ".ssh", ".gnupg", "references/credentials", "backup-2024",
                    "backups_old"):
            self.assertFalse((dest / rel).exists(), rel)
        self.assertTrue((self.repo / ".aws" / "credentials").exists())
        self.assertTrue((self.repo / "backups_old" / "deep.md").exists())

    def test_required_entry_contract_blocks_packaging(self):
        """最小必需契约: 缺 SKILL.md / plugin.json / LICENSE 任一即拒绝打包。"""
        for missing in ("SKILL.md", "LICENSE"):
            with self.subTest(missing=missing):
                repo = self.tmp / f"repo_missing_{missing.replace('.', '_')}"
                build_fake_repo(repo)
                (repo / missing).unlink()
                out = self.tmp / f"dist_missing_{missing.replace('.', '_')}"
                packager = load_module(PACKAGE_DIST_PATH, f"package_dist_missing_{missing[:5]}")
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    rc = packager.main(["--apply", "--out", str(out), "--repo-root", str(repo)])
                self.assertEqual(rc, 1)
                self.assertIn("缺少必需入口资源", buffer.getvalue())
                self.assertFalse(any(out.glob("mathmodel-studio-*")) if out.exists() else False)

    def test_path_display_masked_in_report_and_stdout(self):
        """报告/标准输出的命中路径与扫描对象脱敏: 不回显敏感文件名与用户名段。"""
        token = "ghp_" + "Q1w2E3r4T5y6U7i8O9p0A1s2D3f4G5h6J7k8"
        leak = self.repo / "references" / "prod-token-2026.md"
        leak.write_text(f"token: {token}\n", encoding="utf-8")
        report = self.tmp / "masked_report.txt"
        packager = load_module(PACKAGE_DIST_PATH, "package_dist_mask")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = packager.main(["--scan-dir", str(self.repo), "--report", str(report)])
        self.assertEqual(rc, 1)
        out = buffer.getvalue()
        detail = report.read_text(encoding="utf-8")
        for text in (out, detail):
            self.assertNotIn("prod-token-2026.md", text)   # 敏感文件名不回显
            self.assertNotIn("references/", text)          # 目录分量同样不回显
            self.assertNotIn(token, text)                  # 密钥不完整回显
            self.assertIn("<", text)                       # whole-path 哈希占位
            self.assertNotIn("17366", text)                # 绝对路径分量不回显
        self.assertIn("[github-token]", detail)
        self.assertIn("sha256[:8]", detail)                # 给出反查法

    def test_link_escape_target_outside_repo_not_followed(self):
        """符号链接/junction 不跟随: 指向仓库外的目录不进包 (路径逃逸防线)。

        Windows 无开发者模式时 os.symlink 抛特权错误, 退回 NTFS junction ——
        junction 的 is_symlink() 为 False, 只能靠 reparse 属性识别, 正是逃逸高发形态。
        """
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "leak.txt").write_text("仓库外内容", encoding="utf-8")
        link_dir = self.repo / "references" / "linked_out"
        link_file = self.repo / "references" / "linked_file.md"
        portability = ""
        try:
            link_dir.symlink_to(outside, target_is_directory=True)
            link_file.symlink_to(outside / "leak.txt")
            portability = "symlink"
        except (OSError, NotImplementedError):
            portability = make_link_or_skip(link_dir, outside)  # junction 不需要特权
        rc, out = self._run()
        self.assertEqual(rc, 0, out)
        dest = self._dest()
        self.assertFalse((dest / "references" / "linked_out").exists())
        self.assertFalse((dest / "references" / "linked_out" / "leak.txt").exists())
        self.assertIn("符号链接", out)
        if portability == "symlink":
            self.assertFalse((dest / "references" / "linked_file.md").exists())
        # 仓库外目标未被读取/改动
        self.assertEqual((outside / "leak.txt").read_text(encoding="utf-8"), "仓库外内容")

    def test_suspected_credential_blocks_packaging(self):
        """纳入清单命中凭证类时阻断打包 (不复制), 且不回显完整疑似密钥。"""
        # 载荷分两段拼接: 测试文件自身不得被扫描器命中
        token = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
        (self.repo / "references" / "leak.md").write_text(f"token: {token}\n", encoding="utf-8")
        rc, out = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("已阻断发布", out)
        self.assertIn("[github-token]", out)
        self.assertFalse(self._dest().exists())
        self.assertNotIn(token, out)
        self.assertNotIn("C3d4E5f6", out)  # 中段同样不回显
        self.assertNotIn("leak.md", out)   # 命中路径哈希化, 不回显文件名
        # staging 语义: 阻断后不留半成品 (候选目录与 staging 都不应存在)
        self.assertEqual([p.name for p in self.out.glob(".package_dist-staging-*")], [])
        self.assertEqual([p.name for p in self.out.glob("mathmodel-studio-*")], [])
        # --allow-suspects 放行, 并在发布清单登记
        rc2, out2 = self._run(None, "--allow-suspects")
        self.assertEqual(rc2, 0, out2)
        self.assertIn("[WARN]", out2)
        manifest = (self._dest() / "PACKAGE_CONTENTS.md").read_text(encoding="utf-8")
        self.assertIn("--allow-suspects", manifest)

    def test_scan_dir_reports_and_masks(self):
        """--scan-dir: 扫描已有候选目录, 硬命中脱敏且退出码 1, 明细落 --report。"""
        cand = self.tmp / "candidate"
        (cand / "references").mkdir(parents=True)
        token = "ghp_" + "Z9y8X7w6V5u4T3s2R1q0P9o8N7m6L5k4J3i2"
        (cand / "references" / "leak.md").write_text(f"token={token}\n", encoding="utf-8")
        # 本地路径载荷同样拼接, 避免测试源文件自身被扫描器命中
        win_path = "C:" + "\\" + "Users" + "\\" + "someone" + "\\ws"
        (cand / "references" / "note.md").write_text(
            f"2026 国赛 A 题实测: 用户工作区 {win_path} 与 a@b.org\n", encoding="utf-8")
        report = self.tmp / "scan_report.txt"
        packager = load_module(PACKAGE_DIST_PATH, "package_dist_scandir")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = packager.main(["--scan-dir", str(cand), "--report", str(report)])
        out = buffer.getvalue()
        self.assertEqual(rc, 1)  # 硬命中 → 门禁语义的退出码 1
        self.assertIn("[github-token]", out)
        self.assertNotIn(token, out)
        detail = report.read_text(encoding="utf-8")
        self.assertIn("github-token", detail)
        self.assertNotIn(token, detail)  # 明细同样脱敏
        self.assertIn("private-source-note", detail)   # 私有来源声明只提示、不改写
        self.assertIn("2026 国赛 A 题", detail)
        self.assertIn("未做 OCR", detail)
        # 干净候选目录: 退出码 0
        clean = self.tmp / "clean"
        clean.mkdir()
        (clean / "README.md").write_text("# 干净候选\n", encoding="utf-8")
        buffer2 = io.StringIO()
        with contextlib.redirect_stdout(buffer2):
            rc2 = packager.main(["--scan-dir", str(clean)])
        self.assertEqual(rc2, 0)

    def test_quoted_and_bare_secret_keys_both_hard(self):
        """secret-assignment 同时覆盖裸键与引号键 (复审 P1: {"api_key": "..."} 曾漏报)。"""
        value = "abcdefghijklmnopqrstuv"
        variants = (
            ("bare-key", f'api_key="{value}"'),
            ("quoted-key", '{"api_key":"' + value + '"}'),
            ("quoted-password", '{"password":"' + "hunter2hunter2" + '"}'),
        )
        for name, payload in variants:
            with self.subTest(variant=name):
                repo = self.tmp / f"repo_{name}"
                build_fake_repo(repo)
                (repo / "references" / "config_note.md").write_text(payload + "\n",
                                                                   encoding="utf-8")
                out = self.tmp / f"dist_{name}"
                packager = load_module(PACKAGE_DIST_PATH, f"package_dist_json_{name[:6]}")
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    rc = packager.main(["--apply", "--out", str(out), "--repo-root", str(repo)])
                self.assertEqual(rc, 1, buffer.getvalue())
                self.assertIn("[secret-assignment]", buffer.getvalue())
                self.assertFalse((out / "mathmodel-studio-9.9.9").exists())
                self.assertNotIn(value, buffer.getvalue())

    def test_scan_tree_does_not_cross_junction(self):
        """--scan-dir 不穿 junction: 链接目标 (扫描根外) 的凭据不进扫描结果 (复审 P1)。"""
        outside = self.tmp / "outside_scan"
        outside.mkdir()
        token = "ghp_" + "M1n2B3v4C5x6Z7l8K9j0H1g2F3d4S5a6P7o8"
        (outside / "cred.md").write_text(f"token: {token}\n", encoding="utf-8")
        scan_root = self.tmp / "scanroot"
        scan_root.mkdir()
        (scan_root / "plain.md").write_text("# 普通文件\n", encoding="utf-8")
        make_link_or_skip(scan_root / "linked_scan", outside)
        packager = load_module(PACKAGE_DIST_PATH, "package_dist_junction")
        control = io.StringIO()
        with contextlib.redirect_stdout(control):
            rc_control = packager.main(["--scan-dir", str(outside)])  # 载荷本身可检出
        self.assertEqual(rc_control, 1, control.getvalue())
        report = self.tmp / "junction_scan.txt"
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = packager.main(["--scan-dir", str(scan_root), "--report", str(report)])
        self.assertEqual(rc, 0, buffer.getvalue())  # 穿过去才会被仓库外凭据染红
        self.assertNotIn(token, report.read_text(encoding="utf-8"))

    def test_error_display_has_no_path_or_name(self):
        """异常展示只给类型 + errno/winerror, 不用 str(exc) (OSError 串里常带路径/文件名)。"""
        packager = load_module(PACKAGE_DIST_PATH, "package_dist_errors")
        synthetic = "ghp_" + "S1y2N3t4H5e6T7i8C9_1v2" + "al3u4e5"
        err = OSError(13, "拒绝访问", f"prod-token-2026-{synthetic}.md")
        shown = packager.safe_error(err)
        self.assertIn("Error", shown)      # 只给异常类型名 (errno 13 → PermissionError)
        self.assertIn("errno=13", shown)
        for leak in ("拒绝访问", "prod-token-2026", synthetic, ".md"):
            self.assertNotIn(leak, shown)

    def test_manifest_and_scan_report_paths(self):
        """发布清单进包 (含分类计数); 扫描明细落 dist 根、不进包; 扫描覆盖生成件。"""
        _, dry_out = self._dry()
        dry_scanned = int(re.search(r"扫描文本文件 (\d+) 个", dry_out).group(1))
        rc, out = self._run()
        self.assertEqual(rc, 0, out)
        dest = self._dest()
        manifest = (dest / "PACKAGE_CONTENTS.md").read_text(encoding="utf-8")
        for text in ("运行资源", "开发测试与归档", "非公开项目材料", "凭证与内部材料",
                     "备份与临时", "许可证受限", "缓存与运行时产物", "白名单外内容"):
            self.assertIn(text, manifest)
        # 扫描集合 = staging 实际文件: 含生成的 VENDOR_NOTICES.md, 清单自身自引用排除
        apply_scanned = int(re.search(r"staging 实际文件中的 (\d+) 个文本文件", manifest).group(1))
        self.assertEqual(apply_scanned, dry_scanned + 1)
        report = self.out / "package_dist_scan_report.txt"
        self.assertTrue(report.exists())
        self.assertFalse((dest / report.name).exists())
        self.assertIn("包内容指纹", manifest)          # 复核钉版用
        self.assertIn("自引用排除", manifest)
        self.assertIn("路径已哈希化", manifest)
        self.assertNotIn("17366", manifest)
        self.assertEqual([p.name for p in self.out.glob(".package_dist-staging-*")], [])
        # 指纹必须覆盖"最终内容": 复算 (横幅与 VENDOR_NOTICES 已改, 清单自身排除)
        import hashlib
        payload = "".join(
            f"{rel}\0{hashlib.sha256(path.read_bytes()).hexdigest()}\n"
            for rel, path in sorted(
                (p.relative_to(dest).as_posix(), p) for p in dest.rglob("*")
                if p.is_file() and p.name != "PACKAGE_CONTENTS.md"))
        reported = [l for l in manifest.splitlines() if "包内容指纹" in l][0].split("`")[1]
        self.assertEqual(reported, hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16])
        # 分发副本横幅: 路由文档 + 样张说明 (源仓库不动)
        skill_dir = (dest / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("golden", skill_dir)
        gallery = (dest / "templates" / "figures" / "gallery" / "README.md").read_text(encoding="utf-8")
        self.assertTrue(gallery.lstrip().startswith(">"))
        self.assertIn("分发版说明", gallery)
        src_gallery = (self.repo / "templates" / "figures" / "gallery" / "README.md").read_text(
            encoding="utf-8")
        self.assertNotIn("分发版说明", src_gallery)


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
            # 源仓库原文件不动
            src_text = (self.repo / rel).read_text(encoding="utf-8")
            self.assertNotIn("分发版路由说明", src_text)
            if src_text.startswith("---"):  # 带 frontmatter: 横幅必须落在闭合 fm 之后
                self.assertTrue(dist_text.startswith("---\nname:"), rel)
                fm_end = dist_text.index("\n---", 3) + 4
                self.assertNotIn("分发版路由说明", dist_text[:fm_end], rel)
                self.assertIn("分发版路由说明", dist_text[fm_end:], rel)
            else:                           # 无 frontmatter: 横幅在文首
                self.assertTrue(dist_text.lstrip().startswith(">"), rel)
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
