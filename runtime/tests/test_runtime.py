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

from mathmodel_agent import gate as gate_module
from mathmodel_agent import tools
from mathmodel_agent.config import AgentConfig, MODE_TOKEN_BUDGETS
from mathmodel_agent.gate import GateDecision, parse_action_json
from mathmodel_agent.llm import LLMResponse, TransientLLMError, _is_transient, call_with_retry
from mathmodel_agent.loop import StageDriver
from mathmodel_agent.mockllm import MockLLM
from mathmodel_agent.protocol import ArtifactPathError, parse_artifacts, write_artifact
from mathmodel_agent.prompts import _answered_checkpoint_section
from mathmodel_agent.sandbox import check_code, run_python
from mathmodel_agent.state import CheckpointKeyError, DecisionLog, StateSaveError, checkpoint_allowed

SKILL_ROOT = Path(__file__).resolve().parents[2]


def _init_ws(root: Path, competition: str = "huaweibei"):
    """建临时工作区 (中文目录名, 顺带覆盖 Windows 中文路径安全) 并初始化 state。"""
    ws = root / "工作区" / "ws"
    (ws / "inputs").mkdir(parents=True, exist_ok=True)
    config = AgentConfig.from_env(skill_root=SKILL_ROOT)
    state = DecisionLog.init_from_template(ws, SKILL_ROOT, competition=competition)
    return ws, config, state


def _answer(state: DecisionLog, key: str, answer: str = "mock 用户回答") -> None:
    """模拟 CLI answer 步骤 (trusted 路径登记必停点) 并落盘。"""
    state.record_checkpoint(key, answer)
    state.save()


class _FixedClient:
    """返回固定文本的假客户端 (协议错误等反例测试用)。"""

    def __init__(self, text: str) -> None:
        self.text = text

    def complete(self, role: str, prompt: str) -> LLMResponse:
        return LLMResponse(text=self.text, role=role, model="fixed", usage_tokens=10)


class MockEndToEndTest(unittest.TestCase):
    """MockLLM 驱动 stage 0-2 全链路 (checkpoint_request → paused → answer → 推进)。"""

    def test_stages_0_to_2_hil_lite_chain(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            (ws / "inputs" / "problem.txt").write_text("某电动车充电站选址与调度优化问题", encoding="utf-8")
            lines: list[str] = []
            driver = StageDriver(config, MockLLM(), state, ws, out=lines.append)
            # 第一轮: stage 0 发 checkpoint_request → paused, 未推进未评分
            self.assertEqual(driver.run(0, 2), "paused")
            self.assertEqual(state.data["current_stage"], 0)
            self.assertEqual(state.data["pending_checkpoint"], "kickoff_5q")
            self.assertEqual(state.data["scores"]["0"], [])  # 未评分即暂停
            # 未 answer 重跑: 仍 paused, 不调 LLM
            self.assertEqual(driver.run(0, 2), "paused")
            # answer 后从 paused 恢复: stage 0 推进, stage 2 再次 paused
            _answer(state, "kickoff_5q")
            self.assertEqual(driver.run(state.data["current_stage"], 2), "paused")
            self.assertEqual(state.data["current_stage"], 2)
            self.assertEqual(state.data["pending_checkpoint"], "analysis_confirm")
            _answer(state, "analysis_confirm")
            self.assertEqual(driver.run(state.data["current_stage"], 2), "completed")
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current_stage"], 3)  # pass 推进 0-2 → 3
            self.assertNotIn("pending_checkpoint", data)  # 恢复后 pending 已清除
            self.assertTrue((ws / "state" / "probe.json").exists())
            self.assertEqual(data["stages"]["0"]["checklist_completed"], True)  # 补丁已合并
            self.assertEqual(data["stages"]["1"]["selected"], "A")
            self.assertEqual(data["scores"]["0"][0]["verdict"], "pass")
            self.assertEqual(data["iterations"]["0"], 1)
            self.assertEqual(data["checkpoints"]["kickoff_5q"]["source"], "user_cli")
            # F5: stage 2 的 actual_qi_count 已原子迁移进 stages["5"]
            self.assertEqual(data["stages"]["5"]["qi_count"], 3)
            self.assertIsInstance(data["stages"]["5"]["qi_count"], int)
            self.assertEqual(data["stages"]["5"]["qi_weights"], [1.0, 1.0, 1.0])
            confirmed = [e for e in data["events"]["log"]
                         if e["kind"] == "qi_count_confirmed"]
            self.assertEqual(confirmed[-1]["actual_count"], 3)
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


class CheckpointHilTest(unittest.TestCase):
    """R1: LLM 自写 checkpoints_patch → blocked; 错 stage answer 被拒; 深合并保留三 Qi。"""

    def test_llm_checkpoints_patch_blocks_without_pollution(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            driver = StageDriver(config, MockLLM(checkpoint_patch_stages={0}), state, ws,
                                 out=lambda *_: None)
            self.assertEqual(driver.run_stage(0), "blocked")
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current_stage"], 0)
            self.assertEqual(data["checkpoints"], {})  # LLM 工件未进 state
            self.assertIn("protocol_error", [e["kind"] for e in data["events"]["log"]])
            self.assertFalse((ws / "state" / "checkpoints_patch.json").exists())

    def test_bad_checkpoint_request_key_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            driver = StageDriver(config, MockLLM(bad_checkpoint_request_stages={0}), state, ws,
                                 out=lambda *_: None)
            self.assertEqual(driver.run_stage(0), "blocked")
            self.assertNotIn("pending_checkpoint", state.data)

    def test_checkpoint_request_outside_allowlist_stage_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            client = _FixedClient("checkpoint_request: kickoff_5q\n\n正文")
            driver = StageDriver(config, client, state, ws, out=lambda *_: None)
            self.assertEqual(driver.run_stage(1), "blocked")  # stage 1 无必停点

    def test_wrong_stage_answer_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            with self.assertRaises(CheckpointKeyError):
                state.record_checkpoint("analysis_confirm", "太早")  # stage 0 只允许 kickoff_5q
            with self.assertRaises(CheckpointKeyError):
                state.record_checkpoint("_template", "元键被拒")
            state.advance_stage(5)
            with self.assertRaises(CheckpointKeyError):
                state.record_checkpoint("figure_menu.Q999x", "格式错")
            with self.assertRaises(CheckpointKeyError):
                state.record_checkpoint("figure_menu", "缺 Qi 键")

    def test_deep_merge_keeps_all_three_qis(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            state.advance_stage(5)
            # F2: figure_menu 登记必须携带 --count (与 check_gate 同口径)
            with self.assertRaises(CheckpointKeyError):
                state.record_checkpoint("figure_menu.Q1", "缺 count 被拒")
            for qi in ("Q1", "Q2", "Q3"):
                state.record_checkpoint(f"figure_menu.{qi}", f"{qi} 两张图", count=2)
            menu = state.data["checkpoints"]["figure_menu"]
            self.assertEqual(set(menu), {"Q1", "Q2", "Q3"})  # 连续登记三键全保留
            for entry in menu.values():
                self.assertEqual(entry["status"], "answered")
                self.assertEqual(entry["source"], "user_cli")
                self.assertEqual(entry["count"], 2)
            # 已 answered 的 Qi 覆盖需 --force
            with self.assertRaises(CheckpointKeyError):
                state.record_checkpoint("figure_menu.Q2", "改主意", count=2)
            state.record_checkpoint("figure_menu.Q2", "改主意", force=True, count=2)
            self.assertEqual(menu["Q2"]["answer"], "改主意")

    def test_per_qi_selection_allowed_at_stage5(self):
        """第 6 个必停点: per_qi_selection.Q<n> 仅 stage 5 放行, 格式校验不放宽。"""
        self.assertTrue(checkpoint_allowed(5, "per_qi_selection.Q1"))
        self.assertFalse(checkpoint_allowed(4, "per_qi_selection.Q1"))  # 仅 stage 5
        self.assertFalse(checkpoint_allowed(5, "per_qi_selection"))  # 裸组名不带 Qi 键
        self.assertFalse(checkpoint_allowed(5, "per_qi_selection.Q01"))  # 前导零仍被拒

    def test_per_qi_selection_recorded_and_answered(self):
        """stage 5 可登记 per_qi_selection.Q1 且判已答, 应答注入 prompt 上下文。"""
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            state.advance_stage(5)
            state.record_checkpoint("per_qi_selection.Q1", "沿用 stage 3 拍板选型")
            self.assertTrue(state.checkpoint_is_answered("per_qi_selection.Q1"))
            entry = state.data["checkpoints"]["per_qi_selection"]["Q1"]
            self.assertEqual(entry["status"], "answered")
            self.assertEqual(entry["source"], "user_cli")
            self.assertIn("[CP_ANSWERED per_qi_selection.Q1]",
                          _answered_checkpoint_section(state))

    def test_empty_answer_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            with self.assertRaises(CheckpointKeyError):
                state.record_checkpoint("kickoff_5q", "  ")


class QualityGateTest(unittest.TestCase):
    """P1-1: verdict 参与推进决策 (低分不推进 / block 停机 / carryover 显式化)。

    stage 0 有 kickoff_5q 必停点: 先模拟 CLI answer 再驱动, mock 见
    [CP_ANSWERED] 标记后不再发 checkpoint_request。
    """

    def _driven_stage0(self, td: str, client: MockLLM) -> tuple[StageDriver, Path]:
        ws, config, state = _init_ws(Path(td))
        _answer(state, "kickoff_5q")
        return StageDriver(config, client, state, ws, out=lambda *_: None), ws

    def test_refine_iterates_then_pass_advances(self):
        with tempfile.TemporaryDirectory() as td:
            client = MockLLM(refine_until={0: 1})  # iter0 低分 refine, iter1 pass
            driver, ws = self._driven_stage0(td, client)
            outcome = driver.run_stage(0)
            self.assertEqual(outcome, "advanced")
            self.assertEqual([c[2] for c in client.calls], [0, 1])  # stage 内迭代两次
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current_stage"], 1)
            self.assertEqual(len(data["scores"]["0"]), 2)  # v0 refine + v1 pass
            self.assertEqual(data["iterations"]["0"], 2)

    def test_low_score_refine_forever_becomes_carryover(self):
        with tempfile.TemporaryDirectory() as td:
            client = MockLLM(refine_until={0: 99})  # 永远低分 refine
            driver, ws = self._driven_stage0(td, client)
            outcome = driver.run_stage(0)
            self.assertEqual(outcome, "carryover")  # 迭代耗尽显式携带, 不静默
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current_stage"], 1)
            kinds = [e["kind"] for e in data["events"]["log"]]
            self.assertIn("carryover", kinds)
            self.assertEqual(len(client.calls), 3)  # 迭代上限 = 3

    def test_block_halt_does_not_advance(self):
        with tempfile.TemporaryDirectory() as td:
            client = MockLLM(block_stages={0})  # 高危 issue → verdict=block
            driver, ws = self._driven_stage0(td, client)
            outcome = driver.run_stage(0)
            self.assertEqual(outcome, "blocked")
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current_stage"], 0)  # 不推进
            self.assertEqual(data["stages"]["0"]["blocked"], mock.ANY)
            self.assertIn("blocked", [e["kind"] for e in data["events"]["log"]])

    def test_score_tool_failure_does_not_advance(self):
        with tempfile.TemporaryDirectory() as td:
            client = MockLLM(bad_critique_stages={0})  # critique schema 非法 → exit 1
            driver, ws = self._driven_stage0(td, client)
            outcome = driver.run_stage(0)
            self.assertEqual(outcome, "blocked")  # 3 次迭代全失败 → 停机不推进
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current_stage"], 0)
            failed = [e for e in data["events"]["log"]
                      if e["kind"] == "tool_called" and e["name"] == "score_artifact"]
            self.assertEqual(len(failed), 3)
            self.assertFalse(all(e["ok"] for e in failed))


class Stage9TerminalTest(unittest.TestCase):
    """R2: Stage 9 是终点, 无 gate 9 门禁, 终态字段齐备才 completed, current_stage 保持 9。"""

    def _stage9_ready_state(self, td: str, *, from_stage: int = 9) -> tuple[Path, object, DecisionLog]:
        ws, config, state = _init_ws(Path(td))
        state.advance_stage(from_stage)
        state.data.setdefault("stages", {})["9"].update(
            {"skill_issues_consumed": True, "submission_ready": True})
        state.save()
        return ws, config, state

    def test_stage9_advance_completes_without_gate(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = self._stage9_ready_state(td)
            driver = StageDriver(config, MockLLM(), state, ws, out=lambda *_: None)
            with mock.patch.object(StageDriver, "_run_check_gate",
                                   side_effect=AssertionError("stage 9 不应过 check_gate")):
                outcome = driver._advance(9, GateDecision(gate_module.ADVANCE, reason="test"))
            self.assertEqual(outcome, "completed")
            self.assertEqual(state.data["current_stage"], 9)  # 不推到 10

    def test_stage8_force_enter_completes_at_stage9(self):
        """从 stage 8 force 进入 stage 9: 终态 current_stage 必须落在 9。"""
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = self._stage9_ready_state(td, from_stage=8)
            self.assertEqual(state.data["current_stage"], 8)
            driver = StageDriver(config, MockLLM(), state, ws, out=lambda *_: None)
            outcome = driver._advance(9, GateDecision(gate_module.ADVANCE, reason="test"))
            self.assertEqual(outcome, "completed")
            self.assertEqual(state.data["current_stage"], 9)

    def test_stage9_missing_terminal_fields_pauses(self):
        """缺 skill_issues_consumed / submission_ready → paused 列缺失, 不判 completed。"""
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            state.advance_stage(9)
            state.save()  # 模板默认 skill_issues_consumed=false / submission_ready=false
            driver = StageDriver(config, MockLLM(), state, ws, out=lambda *_: None)
            outcome = driver._advance(9, GateDecision(gate_module.ADVANCE, reason="test"))
            self.assertEqual(outcome, "paused")
            self.assertEqual(state.data["current_stage"], 9)
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            event = [e for e in data["events"]["log"]
                     if e["kind"] == "stage9_terminal_missing"][-1]
            joined = "; ".join(event["missing"])
            self.assertIn("skill_issues_consumed", joined)
            self.assertIn("submission_ready", joined)


class SourceTrustTest(unittest.TestCase):
    """F1: runtime 面只认 source == "user_cli"; 其他 source 一律视为未答。"""

    def test_forged_source_treated_as_unanswered(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            state.record_checkpoint("kickoff_5q", "真回答")
            self.assertTrue(state.checkpoint_is_answered("kickoff_5q"))
            state.data["checkpoints"]["kickoff_5q"]["source"] = "model"  # 伪造来源
            self.assertFalse(state.checkpoint_is_answered("kickoff_5q"))
            state.data["pending_checkpoint"] = "kickoff_5q"
            state.save()
            lines: list[str] = []
            config = AgentConfig.from_env(skill_root=SKILL_ROOT)
            driver = StageDriver(config, MockLLM(), state, ws, out=lines.append)
            self.assertEqual(driver.run(0, 2), "paused")  # source 不可信 → 仍视为待应答

    def test_missing_source_treated_as_unanswered(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            state.record_checkpoint("kickoff_5q", "真回答")
            del state.data["checkpoints"]["kickoff_5q"]["source"]
            self.assertFalse(state.checkpoint_is_answered("kickoff_5q"))


class CheckpointRequestParamTest(unittest.TestCase):
    """F2: record_checkpoint 的 figure_menu 结构化参数 (count/exception/reason)。"""

    def test_figure_menu_count_written(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            state.advance_stage(5)
            state.record_checkpoint("figure_menu.Q1", "2 张", count=2)
            entry = state.data["checkpoints"]["figure_menu"]["Q1"]
            self.assertEqual(entry["count"], 2)
            self.assertNotIn("exception", entry)

    def test_count_low_requires_exception_and_reason(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            state.advance_stage(5)
            with self.assertRaises(CheckpointKeyError):
                state.record_checkpoint("figure_menu.Q1", "1 张", count=1)  # 缺 exception
            with self.assertRaises(CheckpointKeyError):
                state.record_checkpoint("figure_menu.Q1", "1 张", count=1,
                                        exception=True, reason=" ")  # 空 reason
            state.record_checkpoint("figure_menu.Q1", "1 张", count=1,
                                    exception=True, reason="用户确认以表格呈现")
            self.assertEqual(state.data["checkpoints"]["figure_menu"]["Q1"]["count"], 1)

    def test_count_out_of_range_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            state.advance_stage(5)
            with self.assertRaises(CheckpointKeyError):
                state.record_checkpoint("figure_menu.Q1", "10 张", count=10)

    def test_structured_params_rejected_for_non_figure_key(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            with self.assertRaises(CheckpointKeyError):
                state.record_checkpoint("kickoff_5q", "回答", count=2)
            with self.assertRaises(CheckpointKeyError):
                state.record_checkpoint("kickoff_5q", "回答", reason="无关")

    def test_corrupted_checkpoints_root_raises_key_error(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            state.data["checkpoints"] = "broken"
            with self.assertRaises(CheckpointKeyError):  # 不 traceback
                state.record_checkpoint("kickoff_5q", "回答")


class CheckpointRequestPrecedenceTest(unittest.TestCase):
    """F3: checkpoint_request 解析先于工件落盘; 重复/多重申请语义。"""

    def test_request_with_artifacts_writes_nothing_and_pauses(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            driver = StageDriver(config, MockLLM(), state, ws, out=lambda *_: None)
            self.assertEqual(driver.run_stage(0), "paused")
            self.assertEqual(state.data["pending_checkpoint"], "kickoff_5q")
            # request 与工件同响应: 工件一律不落盘
            self.assertFalse((ws / "state" / "probe.json").exists())
            self.assertFalse((ws / "state" / "stage_0_patch.json").exists())

    def test_repeated_request_for_answered_key_ignored_and_advances(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            _answer(state, "kickoff_5q")
            text = ("checkpoint_request: kickoff_5q\n\n"
                    "```artifact:state/probe.json\n{\"ok\": true}\n```")
            driver = StageDriver(config, _FixedClient(text), state, ws, out=lambda *_: None)
            with mock.patch.object(StageDriver, "_run_check_gate", return_value=None):
                outcome = driver.run_stage(0)
            self.assertEqual(outcome, "advanced")  # 不暂停, 继续推进
            self.assertNotIn("pending_checkpoint", state.data)
            self.assertTrue((ws / "state" / "probe.json").exists())  # 工件正常落盘
            kinds = [e["kind"] for e in state.data["events"]["log"]]
            self.assertIn("checkpoint_request_ignored", kinds)

    def test_multiple_different_requests_block_without_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            text = ("checkpoint_request: kickoff_5q\ncheckpoint_request: analysis_confirm\n\n"
                    "```artifact:state/probe.json\n{\"ok\": true}\n```")
            driver = StageDriver(config, _FixedClient(text), state, ws, out=lambda *_: None)
            self.assertEqual(driver.run_stage(0), "blocked")
            self.assertNotIn("pending_checkpoint", state.data)
            self.assertFalse((ws / "state" / "probe.json").exists())  # 不写工件

    def test_malformed_request_trailing_token_blocks_without_artifacts(self):
        """F3: 凡以 checkpoint_request: 开头的行必须整体合法, 尾随 token 即畸形 blocked。"""
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            text = ("checkpoint_request: kickoff_5q extra\n\n"
                    "```artifact:state/probe.json\n{\"ok\": true}\n```")
            driver = StageDriver(config, _FixedClient(text), state, ws, out=lambda *_: None)
            self.assertEqual(driver.run_stage(0), "blocked")
            self.assertNotIn("pending_checkpoint", state.data)
            self.assertFalse((ws / "state" / "probe.json").exists())  # 工件未落盘
            kinds = [e["kind"] for e in state.data["events"]["log"]]
            self.assertIn("blocked", kinds)

    def test_malformed_request_empty_key_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            driver = StageDriver(config, _FixedClient("checkpoint_request:  \n\n正文"),
                                 state, ws, out=lambda *_: None)
            self.assertEqual(driver.run_stage(0), "blocked")
            self.assertNotIn("pending_checkpoint", state.data)

    def test_malformed_request_leading_spaces_extra_token_blocks(self):
        """前导空格的候选行 (strip 后命中前缀) 同样必须整体合法。"""
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            text = "   checkpoint_request: kickoff_5q extra"
            driver = StageDriver(config, _FixedClient(text), state, ws, out=lambda *_: None)
            self.assertEqual(driver.run_stage(0), "blocked")
            self.assertFalse((ws / "state" / "probe.json").exists())


class ConfirmQiCountTest(unittest.TestCase):
    """F5: stage 2 实际子问数 → stages["5"].qi_count/qi_weights 原子迁移。"""

    def test_confirm_qi_count_atomic_migration(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            state.confirm_qi_count(3)
            self.assertEqual(state.data["stages"]["5"]["qi_count"], 3)
            self.assertEqual(state.data["stages"]["5"]["qi_weights"], [1.0, 1.0, 1.0])
            confirmed = [e for e in state.data["events"]["log"]
                         if e["kind"] == "qi_count_confirmed"]
            self.assertEqual(confirmed[-1]["actual_count"], 3)
            self.assertTrue(confirmed[-1]["ts"])  # 事件带时间戳
            # 一次性落盘: 磁盘与内存一致
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["stages"]["5"]["qi_count"], 3)

    def test_confirm_qi_count_invalid_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws, _, state = _init_ws(Path(td))
            before = json.dumps(state.data, sort_keys=True, ensure_ascii=False)
            for bad in (0, -1, True, "3", 2.5, None):
                with self.assertRaises(ValueError):
                    state.confirm_qi_count(bad)
            self.assertEqual(json.dumps(state.data, sort_keys=True, ensure_ascii=False),
                             before)  # 校验失败 state 不变

    def test_stage2_patch_with_bad_qi_count_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            ws, config, state = _init_ws(Path(td))
            _answer(state, "kickoff_5q")
            patch = json.dumps({"decomposition": ["Q1"], "actual_qi_count": "三"},
                               ensure_ascii=False)
            text = f"```artifact:state/stage_2_patch.json\n{patch}\n```"
            driver = StageDriver(config, _FixedClient(text), state, ws, out=lambda *_: None)
            with mock.patch.object(StageDriver, "_run_check_gate", return_value=None):
                self.assertEqual(driver.run_stage(2), "blocked")
            self.assertNotIn("qi_count_confirmed",
                             [e["kind"] for e in state.data["events"]["log"]])
            # 零污染: 校验先于 merge, 磁盘 stages["2"] 不得含非法 patch 内容
            disk = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            s2 = disk["stages"].get("2", {})
            self.assertNotEqual(s2.get("decomposition"), ["Q1"])  # 模板空值, 补丁值未合入
            self.assertNotIn("actual_qi_count", s2)
            self.assertIsNone(disk["stages"].get("5", {}).get("qi_count"))  # 迁移未发生


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
    """P2-6: --from-stage 一致性校验与 backtrack; R1: answer 子命令 HIL-lite 全链。"""

    def _run_cli(self, *argv: str) -> tuple[int, str]:
        from mathmodel_agent.cli import main
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(["run", *argv])
        return code, buffer.getvalue()

    def _answer_cli(self, ws: Path, key: str, answer: str = "cli 用户回答",
                    *extra: str) -> tuple[int, str]:
        from mathmodel_agent.cli import main
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(["answer", "--workspace", str(ws), "--key", key,
                         "--answer", answer, *extra])
        return code, buffer.getvalue()

    def _finish_stage0(self, ws: Path) -> None:
        """run → paused → answer → run → completed 的 CLI 全链。"""
        code, output = self._run_cli("--workspace", str(ws), "--mock", "--to-stage", "0")
        self.assertEqual(code, 3, output)  # paused 与 blocked 同级停机
        self.assertIn("必停点待人工应答", output)
        code, output = self._answer_cli(ws, "kickoff_5q")
        self.assertEqual(code, 0, output)
        self.assertIn("重跑 run", output)
        code, output = self._run_cli("--workspace", str(ws), "--mock", "--to-stage", "0")
        self.assertEqual(code, 0, output)
        self.assertIn("[done: completed]", output)

    def test_fresh_workspace_pause_answer_resume(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            self._finish_stage0(ws)
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current_stage"], 1)
            self.assertEqual(data["checkpoints"]["kickoff_5q"]["source"], "user_cli")

    def test_answer_wrong_key_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            self._run_cli("--workspace", str(ws), "--mock", "--to-stage", "0")  # paused
            code, output = self._answer_cli(ws, "analysis_confirm")  # stage 0 不允许
            self.assertEqual(code, 2, output)
            self.assertIn("[FAIL]", output)

    def test_mismatched_from_stage_requires_force(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            self._finish_stage0(ws)
            code, output = self._run_cli("--workspace", str(ws), "--mock",
                                         "--from-stage", "0", "--to-stage", "0")
            self.assertEqual(code, 2)  # 拒绝不一致起点
            self.assertIn("--force", output)

    def test_force_records_backtrack_event(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            self._finish_stage0(ws)
            code, output = self._run_cli("--workspace", str(ws), "--mock", "--force",
                                         "--from-stage", "0", "--to-stage", "0")
            self.assertEqual(code, 0, output)
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            backtracks = [e for e in data["events"]["log"] if e["kind"] == "backtrack"]
            self.assertEqual(len(backtracks), 1)
            self.assertEqual(backtracks[0]["to"], 0)

    def test_answer_without_pending_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            self._run_cli("--workspace", str(ws), "--mock", "--to-stage", "0",
                          "--dry-run")  # 只初始化, 无 pending
            code, output = self._answer_cli(ws, "kickoff_5q")
            self.assertEqual(code, 2, output)
            self.assertIn("pending_checkpoint 缺失", output)
            self.assertIn("--force", output)

    def test_answer_mismatched_pending_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            self._run_cli("--workspace", str(ws), "--mock", "--to-stage", "0")  # paused
            code, output = self._answer_cli(ws, "figure_menu.Q1")  # 不在 stage 0, 与 pending 不匹配
            self.assertEqual(code, 2, output)
            self.assertIn("不匹配", output)

    def test_answer_force_overrides_pending(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            # 无 pending + --force: 人工管理覆盖可用, 警告可见
            self._run_cli("--workspace", str(ws), "--mock", "--to-stage", "0", "--dry-run")
            code, output = self._answer_cli(ws, "kickoff_5q", "cli 用户回答", "--force")
            self.assertEqual(code, 0, output)
            self.assertIn("[警告]", output)
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertNotIn("pending_checkpoint", data)  # force 清除 pending
            self.assertEqual(data["checkpoints"]["kickoff_5q"]["source"], "user_cli")
            # 已答键再次 --force 覆盖
            code, output = self._answer_cli(ws, "kickoff_5q", "第二次回答", "--force")
            self.assertEqual(code, 0, output)
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["checkpoints"]["kickoff_5q"]["answer"], "第二次回答")

    def test_answer_figure_menu_with_count(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            self._run_cli("--workspace", str(ws), "--mock", "--to-stage", "0", "--dry-run")
            state = DecisionLog.load(ws)
            assert state is not None
            state.advance_stage(5)
            state.data["pending_checkpoint"] = "figure_menu.Q1"
            state.save()
            code, output = self._answer_cli(ws, "figure_menu.Q1", "2 张",
                                            "--count", "2")
            self.assertEqual(code, 0, output)
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            entry = data["checkpoints"]["figure_menu"]["Q1"]
            self.assertEqual(entry["count"], 2)
            self.assertEqual(entry["source"], "user_cli")
            self.assertNotIn("pending_checkpoint", data)
            # count=1 无 exception: CLI 同口径拒绝
            state = DecisionLog.load(ws)
            assert state is not None
            state.data["pending_checkpoint"] = "figure_menu.Q2"
            state.save()
            code, output = self._answer_cli(ws, "figure_menu.Q2", "1 张",
                                            "--count", "1")
            self.assertEqual(code, 2, output)
            self.assertIn("D.1", output)
            # 带例外则通过
            code, output = self._answer_cli(ws, "figure_menu.Q2", "1 张",
                                            "--count", "1", "--exception",
                                            "--reason", "用户确认表格替代")
            self.assertEqual(code, 0, output)
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["checkpoints"]["figure_menu"]["Q2"]["exception"], True)

    def test_answer_figure_menu_missing_count_rejected(self):
        """F2: figure_menu 缺 --count → exit 2, pending 保留, state 无写盘。"""
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            self._run_cli("--workspace", str(ws), "--mock", "--to-stage", "0", "--dry-run")
            state = DecisionLog.load(ws)
            assert state is not None
            state.advance_stage(5)
            state.data["pending_checkpoint"] = "figure_menu.Q1"
            state.save()
            before = (ws / "state" / "decision_log.json").read_text(encoding="utf-8")
            code, output = self._answer_cli(ws, "figure_menu.Q1", "2 张")  # 缺 --count
            self.assertEqual(code, 2, output)
            self.assertIn("--count", output)
            self.assertEqual((ws / "state" / "decision_log.json").read_text(encoding="utf-8"),
                             before)  # state 无写盘
            reloaded = DecisionLog.load(ws)
            assert reloaded is not None
            self.assertEqual(reloaded.data["pending_checkpoint"], "figure_menu.Q1")  # pending 保留
            self.assertNotIn("figure_menu", reloaded.data["checkpoints"])
            # 补 --count 后通过
            code, output = self._answer_cli(ws, "figure_menu.Q1", "2 张", "--count", "2")
            self.assertEqual(code, 0, output)
            data = json.loads((ws / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(data["checkpoints"]["figure_menu"]["Q1"]["count"], 2)
            self.assertNotIn("pending_checkpoint", data)

    def test_answer_structured_params_rejected_for_plain_key(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            self._run_cli("--workspace", str(ws), "--mock", "--to-stage", "0")  # paused
            code, output = self._answer_cli(ws, "kickoff_5q", "回答", "--count", "2")
            self.assertEqual(code, 2, output)
            self.assertIn("仅对 figure_menu.Q<n>", output)

    def test_answer_with_corrupted_checkpoints_root_chinese_error(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            self._run_cli("--workspace", str(ws), "--mock", "--to-stage", "0", "--dry-run")
            state = DecisionLog.load(ws)
            assert state is not None
            state.data["checkpoints"] = "broken"  # 根级损坏
            state.data["pending_checkpoint"] = "kickoff_5q"
            state.save()
            code, output = self._answer_cli(ws, "kickoff_5q")
            self.assertEqual(code, 2, output)
            self.assertIn("损坏", output)
            self.assertNotIn("Traceback", output)


if __name__ == "__main__":
    unittest.main()
