"""runtime 原型测试: MockLLM 端到端 / 质量门 / 原子写 / 沙箱 / 重试 / 工具 / 协议 / CLI。"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mathmodel_agent import tools
from mathmodel_agent.config import AgentConfig, MODE_TOKEN_BUDGETS
from mathmodel_agent.gate import parse_action_json
from mathmodel_agent.llm import LLMResponse, TransientLLMError, _is_transient, call_with_retry
from mathmodel_agent.loop import StageDriver
from mathmodel_agent.mockllm import MockLLM
from mathmodel_agent.protocol import ArtifactPathError, parse_artifacts, write_artifact
from mathmodel_agent.sandbox import check_code, run_python
from mathmodel_agent.state import DecisionLog, StateSaveError

SKILL_ROOT = Path(__file__).resolve().parents[2]


def _init_ws(root: Path, competition: str = "huaweibei"):
    """建临时工作区 (中文目录名, 顺带覆盖 Windows 中文路径安全) 并初始化 state。"""
    ws = root / "工作区" / "ws"
    (ws / "inputs").mkdir(parents=True, exist_ok=True)
    config = AgentConfig.from_env(skill_root=SKILL_ROOT)
    state = DecisionLog.init_from_template(ws, SKILL_ROOT, competition=competition)
    return ws, config, state


class _FixedClient:
    """返回固定文本的假客户端 (协议错误等反例测试用)。"""

    def __init__(self, text: str) -> None:
        self.text = text

    def complete(self, role: str, prompt: str) -> LLMResponse:
        return LLMResponse(text=self.text, role=role, model="fixed", usage_tokens=10)


class MockEndToEndTest(unittest.TestCase):
    """MockLLM 驱动 stage 0-2 全链路 (LLM → 工件 → 补丁 → score_artifact → 质量门 → 推进)。"""

    def test_stages_0_to_2(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            (ws / "inputs" / "problem.txt").write_text("某电动车充电站选址与调度优化问题", encoding="utf-8")
            lines: list[str] = []
            driver = StageDriver(config, MockLLM(), state, ws, out=lines.append)
            status = driver.run(0, 2)
            self.assertEqual(status, "completed")
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current_stage"], 3)  # pass 推进 0-2 → 3
            self.assertTrue((ws / "state" / "probe.json").exists())
            self.assertEqual(data["stages"]["0"]["checklist_completed"], True)  # 补丁已合并
            self.assertEqual(data["stages"]["1"]["selected"], "A")
            self.assertEqual(data["scores"]["0"][0]["verdict"], "pass")
            self.assertEqual(data["iterations"]["0"], 1)
            names = {e["name"] for e in data["events"]["log"] if e["kind"] == "tool_called"}
            self.assertIn("score_artifact", names)
            self.assertIn("retrieve_cases", names)  # stage 1 题面检索已触发
            leftovers = [p.name for p in (ws / "state").iterdir() if p.name.endswith(".tmp")]
            self.assertEqual(leftovers, [])  # score_artifact 原子写无残留 (P1-2)

    def test_dry_run_skips_llm(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            client = MockLLM()
            lines: list[str] = []
            StageDriver(config, client, state, ws, out=lines.append).run(0, 1, dry_run=True)
            self.assertEqual(client.calls, [])  # 未调用 LLM
            self.assertEqual(state.data["current_stage"], 0)  # 状态未推进


class QualityGateTest(unittest.TestCase):
    """P1-1: verdict 参与推进决策 (低分不推进 / block 停机 / carryover 显式化)。"""

    def test_refine_iterates_then_pass_advances(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            client = MockLLM(refine_until={0: 1})  # iter0 低分 refine, iter1 pass
            driver = StageDriver(config, client, state, ws, out=lambda *_: None)
            outcome = driver.run_stage(0)
            self.assertEqual(outcome, "advanced")
            self.assertEqual([c[2] for c in client.calls], [0, 1])  # stage 内迭代两次
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current_stage"], 1)
            self.assertEqual(len(data["scores"]["0"]), 2)  # v0 refine + v1 pass
            self.assertEqual(data["iterations"]["0"], 2)

    def test_low_score_refine_forever_becomes_carryover(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            client = MockLLM(refine_until={0: 99})  # 永远低分 refine
            driver = StageDriver(config, client, state, ws, out=lambda *_: None)
            outcome = driver.run_stage(0)
            self.assertEqual(outcome, "carryover")  # 迭代耗尽显式携带, 不静默
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current_stage"], 1)
            kinds = [e["kind"] for e in data["events"]["log"]]
            self.assertIn("carryover", kinds)
            self.assertEqual(len(client.calls), 3)  # 迭代上限 = 3

    def test_block_halt_does_not_advance(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            client = MockLLM(block_stages={0})  # 高危 issue → verdict=block
            driver = StageDriver(config, client, state, ws, out=lambda *_: None)
            outcome = driver.run_stage(0)
            self.assertEqual(outcome, "blocked")
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current_stage"], 0)  # 不推进
            self.assertEqual(data["stages"]["0"]["blocked"], mock.ANY)
            self.assertIn("blocked", [e["kind"] for e in data["events"]["log"]])

    def test_score_tool_failure_does_not_advance(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            client = MockLLM(bad_critique_stages={0})  # critique schema 非法 → exit 1
            driver = StageDriver(config, client, state, ws, out=lambda *_: None)
            outcome = driver.run_stage(0)
            self.assertEqual(outcome, "blocked")  # 3 次迭代全失败 → 停机不推进
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current_stage"], 0)
            failed = [e for e in data["events"]["log"]
                      if e["kind"] == "tool_called" and e["name"] == "score_artifact"]
            self.assertEqual(len(failed), 3)
            self.assertFalse(all(e["ok"] for e in failed))


class AtomicWriteTest(unittest.TestCase):
    """P1-2/P1-3: 原子写、写盘中断恢复、PermissionError 有限重试。"""

    def test_save_leaves_no_tmp_and_valid_json(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            state.advance_stage(5)
            state.save()
            leftovers = [p.name for p in (ws / "state").iterdir() if p.name.endswith(".tmp")]
            self.assertEqual(leftovers, [])
            reloaded = DecisionLog.load(ws)
            assert reloaded is not None
            self.assertEqual(reloaded.data["current_stage"], 5)

    def test_failed_save_keeps_original(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            original = state.path.read_text(encoding="utf-8")
            state.data["stages"]["0"]["bad"] = object()  # 不可 JSON 序列化
            with self.assertRaises(TypeError):
                state.save()
            self.assertEqual(state.path.read_text(encoding="utf-8"), original)  # 原文件未受损

    def test_replace_retries_on_permission_error(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            real_replace = os.replace
            sleeps: list[float] = []
            calls = {"n": 0}

            def flaky_replace(src, dst):
                calls["n"] += 1
                if calls["n"] <= 2:
                    raise PermissionError("file in use by another process")
                return real_replace(src, dst)

            with mock.patch("os.replace", side_effect=flaky_replace):
                state.advance_stage(2)
                state.save(sleep=sleeps.append)
            self.assertEqual(calls["n"], 3)  # 2 次失败 + 第 3 次成功
            self.assertEqual(len(sleeps), 2)  # 指数退避两次
            self.assertEqual(DecisionLog.load(ws).data["current_stage"], 2)

    def test_replace_exhaustion_raises_recoverable_error(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            original = state.path.read_text(encoding="utf-8")

            def always_locked(src, dst):
                raise PermissionError("locked forever")

            with mock.patch("os.replace", side_effect=always_locked):
                state.advance_stage(7)
                with self.assertRaises(StateSaveError):
                    state.save(sleep=lambda _s: None)
            self.assertEqual(state.path.read_text(encoding="utf-8"), original)  # 原文件保留
            self.assertEqual(state.data["current_stage"], 7)  # 内存态未破坏
            leftovers = [p.name for p in (ws / "state").iterdir() if p.name.endswith(".tmp")]
            self.assertEqual(leftovers, [])  # 临时文件已清理

    def test_reload_on_corrupt_file_keeps_memory_and_recovers(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            state.append_event("stage_done", stage=0)  # 内存态领先于磁盘
            state.path.write_text('{"truncated": ', encoding="utf-8")  # 模拟工具写盘中断
            self.assertFalse(state.reload())  # 不抛出
            kinds = [e["kind"] for e in state.data["events"]["log"]]
            self.assertIn("stage_done", kinds)  # 内存态保留
            state.save()  # 用内存态修复磁盘
            self.assertTrue(state.reload())


class SandboxTest(unittest.TestCase):
    """沙箱黑名单 (含 from-import / getattr 绕过) 与三态产物登记。"""

    def test_dangerous_patterns_rejected(self):
        snippets = [
            'import os\nos.system("dir")',
            "from os import system\nsystem('dir')",
            "from subprocess import run\nrun(['dir'])",
            "__import__('subprocess').run(['dir'])",
            'getattr(os, "sys" + "tem")("dir")',
            "import shutil\nshutil.rmtree('C:/Users')",
            "import socket\nsocket.socket()",
            "import requests\nrequests.get('http://x')",
            'open("C:/Windows/evil.txt", "w")',
        ]
        for code in snippets:
            self.assertTrue(check_code(code), f"应检出危险模式: {code!r}")
        self.assertEqual(check_code("from pathlib import Path\nprint('ok')"), [])
        with tempfile.TemporaryDirectory() as td:
            result = run_python('from os import system\nsystem("echo hi")', Path(td) / "ws")
            self.assertTrue(result.rejected)
            self.assertTrue(result.violations)

    def test_run_python_tracks_added_changed_removed(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            (ws / "results").mkdir(parents=True)
            (ws / "results" / "out.json").write_text('{"v": 1}', encoding="utf-8")
            (ws / "old.txt").write_text("x", encoding="utf-8")
            code = ("from pathlib import Path\n"
                    "Path('results/out.json').write_text('{\"v\": 2}', encoding='utf-8')\n"
                    "Path('new.txt').write_text('new', encoding='utf-8')\n"
                    "Path('old.txt').unlink()")
            result = run_python(code, ws)
            self.assertTrue(result.ok, result.stderr)
            self.assertEqual(result.changes["added"], ["new.txt"])
            self.assertEqual(result.changes["changed"], ["results/out.json"])
            self.assertEqual(result.changes["removed"], ["old.txt"])
            self.assertIn("results/out.json", result.produced_files)


class RetryTest(unittest.TestCase):
    """call_with_retry 与 _is_transient (status_code 优先)。"""

    def test_succeeds_after_transient_failures(self):
        counter = {"n": 0}

        def flaky():
            counter["n"] += 1
            if counter["n"] < 3:
                raise TransientLLMError("rate limit 429")
            return "ok"

        self.assertEqual(call_with_retry(flaky, attempts=3, base_delay=0.0), "ok")
        self.assertEqual(counter["n"], 3)

    def test_exhausts_and_raises_last(self):
        def always_fail():
            raise TransientLLMError("timeout")

        with self.assertRaises(TransientLLMError):
            call_with_retry(always_fail, attempts=3, base_delay=0.0)

    def test_non_transient_not_retried(self):
        counter = {"n": 0}

        def broken():
            counter["n"] += 1
            raise ValueError("hard error")

        with self.assertRaises(ValueError):
            call_with_retry(broken, attempts=3, base_delay=0.0, retry_on=(TransientLLMError,))
        self.assertEqual(counter["n"], 1)

    def test_is_transient_by_status_code(self):
        class HTTPish(Exception):
            def __init__(self, status_code):
                super().__init__(f"http {status_code}")
                self.status_code = status_code

        self.assertTrue(_is_transient(HTTPish(429)))   # 限流 → 重试
        self.assertTrue(_is_transient(HTTPish(503)))   # 5xx → 重试
        self.assertFalse(_is_transient(HTTPish(401)))  # 认证错 → 立即失败
        self.assertFalse(_is_transient(HTTPish(400)))  # 参数错 → 立即失败
        self.assertTrue(_is_transient(TimeoutError("read timed out")))  # 无状态码 → 类型匹配
        self.assertTrue(_is_transient(ConnectionError("Connection reset by peer")))  # 文本回退


class ToolsTest(unittest.TestCase):
    """工具子进程调用的结构化返回与退出码语义。"""

    def test_unknown_tool_raises(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(KeyError):
                tools.run_tool("no_such_tool", Path(td), SKILL_ROOT)

    def test_blocking_flags(self):
        self.assertTrue(tools.TOOLS["score_artifact"].blocking)
        self.assertTrue(tools.TOOLS["consistency_audit"].blocking)
        self.assertTrue(tools.TOOLS["freeze_numbers"].blocking)
        self.assertFalse(tools.TOOLS["retrieve_cases"].blocking)

    def test_retrieve_cases_structured_return(self):
        with tempfile.TemporaryDirectory() as td:
            result = tools.run_tool("retrieve_cases", Path(td), SKILL_ROOT,
                                    query="网络优化 调度", competition="huaweibei", top_k=2)
            self.assertTrue(result.ok, result.stderr)
            self.assertTrue(result.to_dict()["ok"])
            self.assertIn("case_results", result.stdout)
            json.loads(result.stdout)  # 完整 stdout 是合法 JSON

    def test_score_artifact_updates_decision_log(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            critique = {
                "stage_id": 0, "iteration": 0, "min_score": 8, "mean_score": 8.0,
                "issues": [], "verdict": "pass",
                "scores": {d: {"score": 8, "evidence": "测试证据"} for d in (
                    "1_role_clarity", "2_tools_ready", "3_time_planning",
                    "4_problem_scan", "5_collab_protocol")}}
            critique_path = ws / "state" / "critique_stage0_v0.json"
            critique_path.write_text(json.dumps(critique, ensure_ascii=False), encoding="utf-8")
            result = tools.run_tool("score_artifact", ws, SKILL_ROOT,
                                    stage=0, critique=str(critique_path))
            self.assertTrue(result.ok, result.stderr)
            self.assertIn("next_stage", result.stdout)
            reloaded = DecisionLog.load(ws)
            assert reloaded is not None
            self.assertTrue(reloaded.data["scores"]["0"])
            self.assertEqual(reloaded.data["iterations"]["0"], 1)
            self.assertEqual(parse_action_json(result.stdout)["action"], "next_stage")

    def test_figqa_self_test(self):
        with tempfile.TemporaryDirectory() as td:
            result = tools.run_tool("figqa", Path(td), SKILL_ROOT, self_test=True)
            self.assertTrue(result.ok, result.stderr)


class ProtocolTest(unittest.TestCase):
    """工件围栏块解析: 空格路径 / 嵌套 fence / 未闭合报错 / 路径安全。"""

    def test_parse_two_blocks(self):
        parsed = parse_artifacts(
            "说明\n```artifact:state/probe.json\n{\"a\": 1}\n```\n"
            "中间\n```artifact:results/x.csv\n1,2\n```")
        self.assertEqual([p for p, _ in parsed.artifacts], ["state/probe.json", "results/x.csv"])
        self.assertEqual(parsed.artifacts[1][1].strip(), "1,2")
        self.assertEqual(parsed.errors, [])

    def test_path_with_spaces(self):
        parsed = parse_artifacts("```artifact:reports/my report.md\n正文\n```")
        self.assertEqual(parsed.artifacts[0][0], "reports/my report.md")
        with tempfile.TemporaryDirectory() as td:
            target = write_artifact(Path(td), "reports/my report.md", parsed.artifacts[0][1])
            self.assertTrue(target.exists())

    def test_nested_fences_preserved_and_unclosed_reported(self):
        parsed = parse_artifacts(
            "```artifact:paper/draft.md\n标题\n```python\nprint('内嵌代码')\n```\n尾行\n```")
        content = parsed.artifacts[0][1]
        self.assertIn("```python", content)  # 嵌套围栏未被截断
        self.assertIn("尾行", content)
        self.assertEqual(parsed.errors, [])
        bad = parse_artifacts("```artifact:state/x.json\n{\"a\": 1}\n未闭合")
        self.assertEqual(bad.artifacts, [])
        self.assertTrue(any("未闭合" in e for e in bad.errors))

    def test_unrecognized_block_reported_not_silent(self):
        parsed = parse_artifacts("```artifactX:path\n内容\n```")  # 疑似但非本协议
        self.assertEqual(parsed.artifacts, [])
        self.assertTrue(parsed.errors)
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            driver = StageDriver(config, _FixedClient("```artifact:broken\n无闭合"), state, ws,
                                 out=lambda *_: None)
            driver.run_stage(0)
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertIn("protocol_error", [e["kind"] for e in data["events"]["log"]])

    def test_escape_and_absolute_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            with self.assertRaises(ArtifactPathError):
                write_artifact(ws, "../outside.txt", "x")
            with self.assertRaises(ArtifactPathError):
                write_artifact(ws, "C:/Windows/evil.txt", "x")
            self.assertTrue(write_artifact(ws, "state/probe.json", "{}").exists())


class ConfigTest(unittest.TestCase):
    """角色→模型映射与 API key 环境变量解析。"""

    def test_from_env_overrides(self):
        env = {"MATHMODEL_LLM_API_KEY": "global-key",
               "MATHMODEL_LLM_API_KEY_REVIEW": "review-key",
               "MATHMODEL_MODEL_SOLVING": "deepseek/deepseek-chat"}
        with mock.patch.dict(os.environ, env, clear=False):
            config = AgentConfig.from_env(skill_root=SKILL_ROOT, mode="fast")
            self.assertEqual(config.api_key_for("solving"), "global-key")  # 回退全局
            self.assertEqual(config.api_key_for("review"), "review-key")  # 角色级覆盖
        self.assertEqual(config.model_for("solving"), "deepseek/deepseek-chat")
        self.assertEqual(config.token_budget, MODE_TOKEN_BUDGETS["fast"])

    def test_invalid_mode_rejected(self):
        with self.assertRaises(ValueError):
            AgentConfig.from_env(skill_root=SKILL_ROOT, mode="turbo")


class CliTest(unittest.TestCase):
    """P2-6: --from-stage 与 state.current_stage 一致性校验与 backtrack。"""

    def _run_cli(self, *argv: str) -> tuple[int, str]:
        from mathmodel_agent.cli import main
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(["run", *argv])
        return code, buffer.getvalue()

    def test_fresh_workspace_default_start(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            code, output = self._run_cli("--workspace", str(ws), "--mock", "--to-stage", "0")
            self.assertEqual(code, 0, output)
            self.assertIn("[done: completed]", output)

    def test_mismatched_from_stage_requires_force(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            code, output = self._run_cli("--workspace", str(ws), "--mock", "--to-stage", "0")
            self.assertEqual(code, 0)
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current_stage"], 1)
            code, output = self._run_cli("--workspace", str(ws), "--mock",
                                         "--from-stage", "0", "--to-stage", "0")
            self.assertEqual(code, 2)  # 拒绝不一致起点
            self.assertIn("--force", output)

    def test_force_records_backtrack_event(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            self._run_cli("--workspace", str(ws), "--mock", "--to-stage", "0")
            code, output = self._run_cli("--workspace", str(ws), "--mock", "--force",
                                         "--from-stage", "0", "--to-stage", "0")
            self.assertEqual(code, 0, output)
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            backtracks = [e for e in data["events"]["log"] if e["kind"] == "backtrack"]
            self.assertEqual(len(backtracks), 1)
            self.assertEqual(backtracks[0]["to"], 0)


if __name__ == "__main__":
    unittest.main()
