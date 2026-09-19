"""D1 skill 根路径统一动态解析测试。

口径:
- `scripts/skill_paths.py` 是根路径唯一真源: 按**调用路径**向上找 SKILL.md,
  不强制 resolve (从链接入口调用就报链接路径), 便于人判断当前用哪一份;
- 全仓库 python 源码不得含用户目录绝对路径 (`C:\\Users\\...`);
- `render_modeling_pack.py --list` / `export_final_docx.py` 启动时的命令示例
  与 V0 日志都用运行时根, 且打印出的 figqa 路径必须真实存在;
- 链接安装 (junction / symlink) 下 `describe()` 附带真实路径。

链接相关断言一律用临时目录内自建的假 skill + junction, 不读取也不改动真实安装
入口 (`~/.codex`, `~/.zcode`); 无权限建 junction 时 skip 并给出原因。
"""

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import skill_paths  # noqa: E402

# 用户目录绝对路径 (盘符 + Users); 文档中的相对写法 (references/...) 不受限制
ABS_USER_PATH_RE = re.compile(r"[A-Za-z]:[\\/]{1,2}Users[\\/]", re.IGNORECASE)
# figqa 命令提示: 根路径可含空格, 不能按空白切分 (旧 \S+ 写法在含空格路径下解析失败)
FIGQA_HINT_RE = re.compile(r'python\s+"?([^"]+?figqa\.py)"?')


def _py_files():
    for base in ("scripts", "templates"):
        for path in (ROOT / base).rglob("*.py"):
            if "__pycache__" in path.parts or "legacy" in path.parts:
                continue
            yield path


def _run_list(script: Path) -> subprocess.CompletedProcess:
    """跑 `--list`; 子进程强制 UTF-8 输出, 临时目录含中文/空格时也能正确解析。"""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, str(script), "--list"],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)


def _write_fake_skill(base: Path) -> Path:
    """临时目录内建最小假 skill: SKILL.md + scripts/ + render_modeling_pack.py。

    目录名故意含空格, 覆盖含空格路径下的提示解析; 被测脚本
    (skill_paths.py / render_modeling_pack.py) 从当前安装复制, figqa.py 用
    占位文件 (只断言提示路径存在, 不执行)。
    """
    root = base / "fake skill root"
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "SKILL.md").write_text("# fake skill (test fixture)\n", encoding="utf-8")
    (root / "scripts" / "skill_paths.py").write_bytes(
        (ROOT / "scripts" / "skill_paths.py").read_bytes())
    (root / "scripts" / "figqa.py").write_text(
        "# placeholder (test fixture)\n", encoding="utf-8")
    pack = root / "templates" / "figures" / "scripts"
    pack.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        ROOT / "templates" / "figures" / "scripts" / "render_modeling_pack.py",
        pack / "render_modeling_pack.py")
    return root


def _make_junction(link: Path, target: Path) -> None:
    """只对自建临时路径建 Windows junction (mklink /J); 失败抛 RuntimeError。"""
    if os.name != "nt":
        raise RuntimeError(f"junction 仅 Windows 可用 (os.name={os.name!r})")
    proc = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                          capture_output=True, text=True, errors="replace")
    if proc.returncode != 0:
        detail = ((proc.stdout or "") + (proc.stderr or "")).strip()
        raise RuntimeError(f"mklink /J 失败 rc={proc.returncode}: {detail}")


class LinkedSkillFixtureMixin:
    """临时假 skill + 隔离 junction 的公共装配; 只碰自建临时路径。"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tmp = tempfile.TemporaryDirectory(prefix="mm_skill_root_")
        cls.addClassCleanup(tmp.cleanup)
        cls.tmpdir = Path(tmp.name)
        cls.fake_root = _write_fake_skill(cls.tmpdir)
        cls.fake_link = cls.tmpdir / "linked skill root"
        try:
            _make_junction(cls.fake_link, cls.fake_root)
        except RuntimeError as exc:
            raise unittest.SkipTest(f"临时目录无法建 junction, 跳过链接断言: {exc}")


class TestSkillRootResolution(unittest.TestCase):
    def test_skill_root_found_by_walking_up(self):
        self.assertTrue((ROOT / "SKILL.md").is_file())
        self.assertEqual(skill_paths.skill_root(__file__), ROOT)
        # 任意深度都一致 (scripts/ 与 templates/figures/scripts/ 两种调用点)
        for rel in ("scripts/skill_paths.py",
                    "scripts/export_final_docx.py",
                    "templates/figures/scripts/render_modeling_pack.py",
                    "templates/figures/scripts/templates/make_field_contour.py"):
            self.assertEqual(skill_paths.skill_root(ROOT / rel), ROOT, rel)

    def test_skill_root_accepts_directory_and_raises_when_lost(self):
        """审查 low 回归: 传目录本身应从该目录查起; 找不到根时须抛异常。"""
        self.assertEqual(skill_paths.skill_root(ROOT), ROOT)
        self.assertEqual(skill_paths.skill_root(ROOT / "scripts"), ROOT)
        for bogus in ("C:/_absent_skill_probe_/x.py", "C:/", "/"):
            with self.assertRaises(ValueError):
                skill_paths.skill_root(bogus)

    def test_no_absolute_user_path_in_sources(self):
        """全仓库 python 源码不得写死用户目录绝对路径。"""
        hits = []
        for path in _py_files():
            for i, text in enumerate(
                    path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if ABS_USER_PATH_RE.search(text):
                    hits.append(f"{path.relative_to(ROOT)}:{i}: {text.strip()[:90]}")
        self.assertEqual(hits, [], "源码含写死的用户目录路径:\n" + "\n".join(hits))


class TestLinkedInstallResolution(LinkedSkillFixtureMixin, unittest.TestCase):
    """链接入口路径保真 + describe/--list 提示 (自建 junction, 不依赖真实安装)。"""

    def test_invoked_link_path_is_preserved(self):
        """从链接入口调用就报链接路径, 不被 resolve 回真实安装 (两份入口的判定依据)。"""
        invoked = self.fake_link / "scripts" / "skill_paths.py"
        root = skill_paths.skill_root(invoked)
        self.assertEqual(os.path.normcase(str(root)),
                         os.path.normcase(str(self.fake_link)),
                         "按调用路径推导应保留链接入口路径")
        # 真实路径解析是另一条独立信息, 用于日志
        real = skill_paths.real_root(root)
        self.assertTrue((real / "SKILL.md").is_file())
        self.assertEqual(os.path.normcase(str(real)),
                         os.path.normcase(os.path.realpath(self.fake_root)))

    def test_describe_reports_root_and_symlink(self):
        line = skill_paths.describe(ROOT / "scripts" / "export_final_docx.py")
        self.assertTrue(line.startswith("[skill] root="), line)
        link_line = skill_paths.describe(self.fake_link / "scripts" / "skill_paths.py")
        self.assertTrue(link_line.startswith(f"[skill] root={self.fake_link}"), link_line)
        self.assertIn("symlink ->", link_line)  # 兼容文本暂保留, API 不变
        self.assertIn(str(skill_paths.real_root(self.fake_root)), link_line)

    def test_list_hints_from_linked_install_point_to_that_install(self):
        script = (self.fake_link / "templates" / "figures" / "scripts"
                  / "render_modeling_pack.py")
        proc = _run_list(script)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("[skill] root=", proc.stdout, "--list 应打印当前使用的根 (V0 日志)")
        self.assertIn(str(self.fake_link), proc.stdout, "从链接入口调用应提示链接路径")
        hints = FIGQA_HINT_RE.findall(proc.stdout)
        self.assertTrue(hints, "未解析到 figqa 命令提示 (路径含空格?):\n" + proc.stdout)
        for hint in set(hints):
            self.assertTrue(Path(hint).is_file(), f"提示路径不存在: {hint}")
            self.assertTrue(hint.lower().startswith(str(self.fake_link).lower()),
                            f"提示路径不在链接入口 {self.fake_link} 下: {hint}")


class TestCommandHintsUseRuntimeRoot(unittest.TestCase):
    def test_list_hints_point_to_existing_figqa(self):
        script = ROOT / "templates" / "figures" / "scripts" / "render_modeling_pack.py"
        proc = _run_list(script)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        self.assertIn("[skill] root=", out, "--list 应打印当前使用的根 (V0 日志)")
        hints = FIGQA_HINT_RE.findall(out)
        self.assertTrue(hints, "未解析到 figqa 命令提示")
        for hint in set(hints):
            self.assertTrue(Path(hint).is_file(), f"提示路径不存在: {hint}")
        # 提示路径应落在当前调用根内 (而非另一份安装)
        self.assertTrue(all(str(ROOT).lower() in h.lower() for h in hints),
                        f"提示路径不在当前根 {ROOT} 下: {set(hints)}")

    def test_export_final_docx_logs_root_and_default_reference(self):
        import export_final_docx  # noqa: E402

        buf = io.StringIO()
        with redirect_stdout(buf), self.assertRaises(SystemExit):
            export_final_docx.main(["--help"])  # 根日志在解析参数之前打印
        self.assertIn("[skill] root=", buf.getvalue())

        # 缺省 reference-doc 由本次导入的 module 根推出, 且必须真实存在
        module_root = skill_paths.skill_root(export_final_docx.__file__)
        self.assertEqual(os.path.normcase(str(module_root)),
                         os.path.normcase(str(ROOT)),
                         "本次导入的 export_final_docx 必须来自当前测试根")
        default_ref = module_root / "templates" / "docx" / "reference.docx"
        self.assertTrue(default_ref.is_file(),
                        f"缺省 reference-doc 不在本次 module 根或不存在: {default_ref}")


if __name__ == "__main__":
    unittest.main()
