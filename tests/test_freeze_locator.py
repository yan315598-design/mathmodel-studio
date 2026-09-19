"""C5 冻结协议补强测试: freeze_numbers locator 试解析 / verify 四分类 / check_gate 评分时效软检查。

口径:
- locator 三类形态: 纯点路径 a.b.c (含数组下标 a.b[0][1] 与顶层字段名特例) / 描述型
  (含中文/空格, 不做机器解析不警告) / 非 json 源 (暂不支持自动解析, 归描述型);
- 一致判据: 字符串等值 / 数值相对误差 <1e-9 / 源值按记录值有效位数舍入后相等;
- freeze 的 locator warn 不阻断、不改变退出码; verify 纯诊断恒 0;
- check_gate 评分时效: stage N 最新评分 ts (gate 5 含 5_per_qi) 早于
  results/paper_workspace/figures (深度<=2) 最新 mtime → notes 提示, 不改放行语义。
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_gate  # noqa: E402
import freeze_numbers  # noqa: E402


def _run(func, *args):
    """捕获 stdout 运行, 返回 (返回码, 输出)。"""
    out = io.StringIO()
    with redirect_stdout(out):
        code = func(*args)
    return code, out.getvalue()


class TmpCwdMixin(unittest.TestCase):
    """freeze_numbers 以 cwd 定位 state/, 测试统一切进临时工作区。"""

    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        os.chdir(self.ws)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _write_json(self, rel, payload):
        path = self.ws / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def _freeze(self, claim, value, locator, source="results/solve.json", unit="万元"):
        return _run(
            freeze_numbers.main,
            ["freeze", "--claim", claim, "--value", value,
             "--unit", unit, "--source", source, "--locator", locator],
        )

    def _store(self):
        store = self.ws / "state" / "frozen_numbers.json"
        return json.loads(store.read_text(encoding="utf-8")) if store.exists() else {}


class FreezeLocatorWarnTest(TmpCwdMixin):
    """freeze 落盘前的 locator 试解析: 一致静默, 对不上 warn 一行且不阻断。"""

    def test_dotted_path_consistent_value_silent(self):
        self._write_json("results/solve.json", {"data": {"total_cost": 4826.3}})
        code, out = self._freeze("q2_total_cost", "4826.3", "data.total_cost")
        self.assertEqual(code, 0)
        self.assertNotIn("[locator]", out)
        self.assertIn("已冻结", out)

    def test_top_level_field_consistent_silent(self):
        self._write_json("results/solve.json", {"runtime_seconds": 0.5})
        code, out = self._freeze("q1_runtime", "0.5", "runtime_seconds", unit="s")
        self.assertEqual(code, 0)
        self.assertNotIn("[locator]", out)

    def test_bracket_index_consistent_silent(self):
        self._write_json("results/profile.json", {"grid": [[1.0, 2.0], [3.0, 4.0]]})
        code, out = self._freeze("q1_cell", "3", "grid[1][0]", source="results/profile.json")
        self.assertEqual(code, 0)
        self.assertNotIn("[locator]", out)

    def test_rounded_display_value_consistent_silent(self):
        """论文数字是显示精度舍入值: 源 57.540555… vs 冻结 57.5406 属一致, 不 warn。"""
        self._write_json("results/t.json", {"t_star_h": 57.54055555555556})
        code, out = self._freeze("q3_t", "57.5406", "t_star_h", source="results/t.json", unit="h")
        self.assertEqual(code, 0)
        self.assertNotIn("[locator]", out)

    def test_scientific_notation_consistent_silent(self):
        self._write_json("results/v.json", {"residual": 2.3e-13})
        code, out = self._freeze("q1_res", "2.30e-13", "residual", source="results/v.json")
        self.assertEqual(code, 0)
        self.assertNotIn("[locator]", out)

    def test_string_value_equality_silent(self):
        self._write_json("results/s.json", {"site": "左边界第 1 节点"})
        code, out = self._freeze("q1_site", "左边界第 1 节点", "site",
                                 source="results/s.json", unit="-")
        self.assertEqual(code, 0)
        self.assertNotIn("[locator]", out)

    def test_numeric_mismatch_warns_but_freezes(self):
        """值对不上: warn 一行请人工确认, 但不阻断 (退出码仍 0, 照常落盘)。"""
        self._write_json("results/solve.json", {"data": {"total_cost": 4826.3}})
        code, out = self._freeze("q2_total_cost", "9999", "data.total_cost")
        self.assertEqual(code, 0)
        self.assertIn("[locator]", out)
        self.assertIn("请人工确认", out)
        self.assertIn("已冻结", out)
        self.assertIn("q2_total_cost", self._store())

    def test_missing_key_warns(self):
        self._write_json("results/solve.json", {"data": {"total_cost": 4826.3}})
        code, out = self._freeze("q2_x", "4826.3", "data.no_such_key")
        self.assertEqual(code, 0)
        self.assertIn("[locator]", out)
        self.assertIn("不存在", out)

    def test_bad_syntax_warns(self):
        self._write_json("results/solve.json", {"a": {"b": 1}})
        code, out = self._freeze("q_x", "1", "a..b")
        self.assertEqual(code, 0)
        self.assertIn("[locator]", out)
        self.assertIn("语法不合法", out)

    def test_container_locator_warns(self):
        """定位符指向 dict 容器而非叶子数值字段: 属可解析不一致, warn。"""
        self._write_json("results/v.json", {"physical_magnitudes": {"tau_heat_s": 2761.9}})
        code, out = self._freeze("q2_tau", "46.0", "physical_magnitudes",
                                 source="results/v.json", unit="min")
        self.assertEqual(code, 0)
        self.assertIn("[locator]", out)
        self.assertIn("容器", out)

    def test_chinese_descriptive_locator_no_warn(self):
        """纯中文描述定位符不做机器解析, 不警告。"""
        self._write_json("results/solve.json", {"data": {"total_cost": 4826.3}})
        code, out = self._freeze("q2_desc", "4826.3", "第 3 小时总成本（正文表 4）")
        self.assertEqual(code, 0)
        self.assertNotIn("[locator]", out)

    def test_nonjson_source_no_warn(self):
        """非 json 源第一版暂不支持自动解析, 归描述型, 不警告。"""
        xlsx = self.ws / "results" / "Q.xlsx"
        xlsx.parent.mkdir(parents=True, exist_ok=True)
        xlsx.write_bytes(b"PK\x03\x04fake")
        code, out = self._freeze("q5_x", "1.0", "Sheet1.A1", source="results/Q.xlsx")
        self.assertEqual(code, 0)
        self.assertNotIn("[locator]", out)

    def test_dry_run_warns_without_write(self):
        self._write_json("results/solve.json", {"total": 1})
        out_io = io.StringIO()
        with redirect_stdout(out_io):
            code = freeze_numbers.main(
                ["--dry-run", "freeze", "--claim", "c", "--value", "2",
                 "--unit", "-", "--source", "results/solve.json", "--locator", "total"])
        self.assertEqual(code, 0)
        self.assertIn("[locator]", out_io.getvalue())
        self.assertEqual(self._store(), {})


class VerifyCommandTest(TmpCwdMixin):
    """verify 子命令: 四分类统计与明细, 纯诊断恒 0。"""

    def _build_store(self):
        self._write_json("results/ok.json", {"total": 100.0})
        self._write_json("results/bad.json", {"total": 100.0, "pm": {"tau_s": 2761.9}})
        xlsx = self.ws / "results" / "Q.xlsx"
        xlsx.write_bytes(b"PK\x03\x04fake")
        store = {
            "ok_entry": {"value": "100", "unit": "-", "source_file": "results/ok.json",
                         "source_locator": "total", "source_sha256": "x",
                         "frozen_at": "2026-09-01T00:00:00", "frozen_by": "t",
                         "status": "frozen"},
            "mismatch_value": {"value": "999", "unit": "-", "source_file": "results/bad.json",
                               "source_locator": "total", "source_sha256": "x",
                               "frozen_at": "2026-09-01T00:00:00", "frozen_by": "t",
                               "status": "frozen"},
            "mismatch_dict": {"value": "46.0", "unit": "min", "source_file": "results/bad.json",
                              "source_locator": "pm", "source_sha256": "x",
                              "frozen_at": "2026-09-01T00:00:00", "frozen_by": "t",
                              "status": "frozen"},
            "desc_cn": {"value": "1", "unit": "-", "source_file": "results/ok.json",
                        "source_locator": "第 1800 s 中心温度", "source_sha256": "x",
                        "frozen_at": "2026-09-01T00:00:00", "frozen_by": "t",
                        "status": "frozen"},
            "desc_xlsx": {"value": "1", "unit": "-", "source_file": "results/Q.xlsx",
                          "source_locator": "Sheet1.A1", "source_sha256": "x",
                          "frozen_at": "2026-09-01T00:00:00", "frozen_by": "t",
                          "status": "frozen"},
            "fail_key": {"value": "1", "unit": "-", "source_file": "results/ok.json",
                         "source_locator": "no_such.key", "source_sha256": "x",
                         "frozen_at": "2026-09-01T00:00:00", "frozen_by": "t",
                         "status": "frozen"},
            "fail_missing": {"value": "1", "unit": "-", "source_file": "results/absent.json",
                             "source_locator": "x", "source_sha256": "x",
                             "frozen_at": "2026-09-01T00:00:00", "frozen_by": "t",
                             "status": "frozen"},
        }
        (self.ws / "state").mkdir(exist_ok=True)
        (self.ws / "state" / "frozen_numbers.json").write_text(
            json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
        return store

    def test_verify_four_category_stats(self):
        self._build_store()
        code, out = _run(freeze_numbers.main, ["verify"])
        self.assertEqual(code, 0)
        self.assertIn("可解析且一致 1", out)
        self.assertIn("可解析不一致 2", out)
        self.assertIn("描述型 2", out)
        self.assertIn("解析失败 2", out)
        self.assertIn("共 7 条", out)
        self.assertIn("✅ [ok_entry]", out)
        self.assertIn("❌ [mismatch_value]", out)
        self.assertIn("❌ [mismatch_dict]", out)
        self.assertIn("ℹ️ [desc_cn]", out)
        self.assertIn("ℹ️ [desc_xlsx]", out)
        self.assertIn("暂不支持自动解析", out)
        self.assertIn("⚠️ [fail_key]", out)
        self.assertIn("⚠️ [fail_missing]", out)
        self.assertIn("描述型不视为问题", out)

    def test_verify_is_readonly(self):
        self._build_store()
        before = (self.ws / "state" / "frozen_numbers.json").read_text(encoding="utf-8")
        _run(freeze_numbers.main, ["verify"])
        after = (self.ws / "state" / "frozen_numbers.json").read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_verify_empty_store(self):
        code, out = _run(freeze_numbers.main, ["verify"])
        self.assertEqual(code, 0)
        self.assertIn("冻结清单为空", out)


class ScoreFreshnessTest(unittest.TestCase):
    """check_gate 评分时效软检查: 旧评分 + 新产物 → 提示; 新评分 → 不提示。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        self.now = datetime.now().astimezone()

    def tearDown(self):
        self._tmp.cleanup()

    def _make_workspace(self, score_ts, artifact_mtime=None, with_artifacts=True):
        """造最小工作区: state/decision_log.json + results/ 产物 (mtime 可指定)。"""
        state = self.ws / "state"
        state.mkdir(parents=True, exist_ok=True)
        log = {
            "scores": {"8": [{"iteration": 0, "scores": {"1_abstract_5_paragraph": 8},
                              "min": 8, "mean": 8.0, "verdict": "pass", "ts": score_ts}]},
            "stages": {},
            "checkpoints": {},
        }
        (state / "decision_log.json").write_text(json.dumps(log), encoding="utf-8")
        if with_artifacts:
            results = self.ws / "results"
            results.mkdir(exist_ok=True)
            artifact = results / "solve.json"
            artifact.write_text("{}", encoding="utf-8")
            if artifact_mtime is not None:
                os.utime(artifact, (artifact_mtime, artifact_mtime))
        return log

    def _freshness_notes(self, log, gate=8):
        result = check_gate.check_gate(log, gate, workspace=self.ws)
        return [n for n in result["notes"] if "评分时间戳早于产物最新 mtime" in n]

    def test_stale_score_prompts_note(self):
        score_ts = (self.now - timedelta(hours=2)).isoformat()
        log = self._make_workspace(score_ts,
                                   artifact_mtime=(self.now - timedelta(hours=1)).timestamp())
        notes = self._freshness_notes(log)
        self.assertEqual(len(notes), 1)
        self.assertIn("stage 8", notes[0])
        self.assertIn("建议复评", notes[0])
        self.assertIn("不阻断", notes[0])

    def test_stale_note_does_not_change_pass(self):
        """提示纯加注: 放行仍放行 (评分本身合法, 只是旧)。"""
        score_ts = (self.now - timedelta(hours=2)).isoformat()
        log = self._make_workspace(score_ts,
                                   artifact_mtime=(self.now - timedelta(hours=1)).timestamp())
        result = check_gate.check_gate(log, 8, workspace=self.ws)
        self.assertTrue(result["pass"])

    def test_fresh_score_no_note(self):
        score_ts = self.now.isoformat()
        log = self._make_workspace(score_ts,
                                   artifact_mtime=(self.now - timedelta(hours=1)).timestamp())
        self.assertEqual(self._freshness_notes(log), [])

    def test_naive_ts_treated_as_local(self):
        """naive 评分 ts 按本地时区参与比较, 同样能触发提示。"""
        naive_past = (datetime.now() - timedelta(hours=3)).replace(microsecond=0).isoformat()
        log = self._make_workspace(naive_past,
                                   artifact_mtime=(self.now - timedelta(hours=1)).timestamp())
        self.assertEqual(len(self._freshness_notes(log)), 1)

    def test_no_artifact_dirs_no_note(self):
        score_ts = (self.now - timedelta(hours=2)).isoformat()
        log = self._make_workspace(score_ts, with_artifacts=False)
        self.assertEqual(self._freshness_notes(log), [])

    def test_no_workspace_no_note(self):
        """不传 workspace (既有调用方式) 不做时效检查, 保持行为兼容。"""
        score_ts = (self.now - timedelta(hours=2)).isoformat()
        log = self._make_workspace(score_ts,
                                   artifact_mtime=(self.now - timedelta(hours=1)).timestamp())
        result = check_gate.check_gate(log, 8)
        self.assertFalse(any("评分时间戳早于产物最新 mtime" in n for n in result["notes"]))

    def test_scan_depth_limited(self):
        """mtime 扫描深度 <=2: 第 3 层的新文件不参与比较。"""
        score_ts = (self.now - timedelta(hours=1)).isoformat()
        log = self._make_workspace(score_ts,
                                   artifact_mtime=(self.now - timedelta(hours=2)).timestamp())
        deep = self.ws / "results" / "sub1" / "sub2"
        deep.mkdir(parents=True)
        deep_file = deep / "too_deep.json"
        deep_file.write_text("{}", encoding="utf-8")
        future = (self.now + timedelta(hours=1)).timestamp()
        os.utime(deep_file, (future, future))
        self.assertEqual(self._freshness_notes(log), [])  # 深层新文件不触发

    def test_gate5_takes_latest_of_dual_paths(self):
        """gate 5 双路径: 取 scores['5'] 与 scores['5_per_qi'] 的最新 ts。"""
        old_ts = (self.now - timedelta(hours=3)).isoformat()
        new_ts = (self.now - timedelta(minutes=30)).isoformat()
        log = {
            "scores": {
                "5": [{"iteration": 0, "scores": {"1_subproblem_completeness": 8},
                       "min": 8, "mean": 8.0, "verdict": "pass", "ts": old_ts}],
                "5_per_qi": [{"iteration": 0, "qi_id": "Q1",
                              "scores": {"1_correctness": 8}, "min": 8, "mean": 8.0,
                              "verdict": "pass", "ts": new_ts}],
            },
            "stages": {},
            "checkpoints": {},
        }
        state = self.ws / "state"
        state.mkdir(parents=True, exist_ok=True)
        (state / "decision_log.json").write_text(json.dumps(log), encoding="utf-8")
        results = self.ws / "results"
        results.mkdir(exist_ok=True)
        artifact = results / "Q1.json"
        artifact.write_text("{}", encoding="utf-8")
        os.utime(artifact, ((self.now - timedelta(hours=1)).timestamp(),) * 2)
        # per-Qi 评分 (30 分钟前) 新于产物 (1 小时前): 整体不提示
        self.assertEqual(self._freshness_notes(log, gate=5), [])
        # 两条评分都旧于产物 → 提示 stage 5
        log["scores"]["5_per_qi"][0]["ts"] = old_ts
        notes = self._freshness_notes(log, gate=5)
        self.assertEqual(len(notes), 1)
        self.assertIn("stage 5", notes[0])

    def test_main_wiring_prints_hint(self):
        """端到端: main() 从 decision_log 路径推导工作区, 文本输出带 [提示] 行。"""
        score_ts = (self.now - timedelta(hours=2)).isoformat()
        self._make_workspace(score_ts,
                             artifact_mtime=(self.now - timedelta(hours=1)).timestamp())
        argv = ["check_gate.py", "--gate", "8",
                "--decision-log", str(self.ws / "state" / "decision_log.json")]
        out = io.StringIO()
        with redirect_stdout(out), mock.patch("sys.argv", argv):
            code = check_gate.main()
        self.assertEqual(code, 0)
        self.assertIn("[提示]", out.getvalue())
        self.assertIn("stage 8 评分时间戳早于产物最新 mtime", out.getvalue())
        self.assertIn("建议复评", out.getvalue())

    def test_main_wiring_fresh_score_no_hint(self):
        score_ts = self.now.isoformat()
        self._make_workspace(score_ts,
                             artifact_mtime=(self.now - timedelta(hours=1)).timestamp())
        argv = ["check_gate.py", "--gate", "8",
                "--decision-log", str(self.ws / "state" / "decision_log.json")]
        out = io.StringIO()
        with redirect_stdout(out), mock.patch("sys.argv", argv):
            code = check_gate.main()
        self.assertEqual(code, 0)
        self.assertNotIn("评分时间戳早于产物最新 mtime", out.getvalue())


if __name__ == "__main__":
    unittest.main()
