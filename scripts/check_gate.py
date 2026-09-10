"""
check_gate.py — 阶段推进门禁脚本 (v2.3.0)

功能:
1. --gate N: 检查"从 stage N 推进到 N+1"的放行条件 (N = 0..8)
   - 必停点检查: decision_log.checkpoints 中对应键必须真 answered
     (status=="answered" + asked_at 可解析 ISO 时间 + answer 非空 + source ∈ {chat, user_cli},
      缺一即未答; source 缺失或非 chat/user_cli 视为未答)
     - gate 0 → checkpoints.kickoff_5q (启动 5 问)
     - gate 2 → checkpoints.analysis_confirm (Stage 2 审题呈现确认)
     - gate 3 → checkpoints.card_decision (Stage 3 选择卡拍板)
     - gate 5 → checkpoints.figure_menu["Q<i>"] 与 checkpoints.qi_verdict["Q<i>"]
       (qi_verdict 按问即问即登记: 每个 Qi 的 per-Qi L1 评分产出 verdict 时逐问
        向用户确认并登记; 聚合整体决策登记进 stages["5"], 不复制进 qi_verdict;
        figure_menu 条目另须 count (int 0-9), count≤1 时须 exception: true + 非空
        reason, 即 D.1 例外确认)
     gate 5 的子问集合按完成态三来源语义: stages.5.qi_count (严格正 int) /
     qi_status 键 / sub_problems 键 (排除 _template) 三者必须全部登记且集合相等
   - 评分落盘检查 (E 合并): scores 必须有 stage N 的合法评分记录
     (stage 5 双路径: scores["5"] stage-level 或 scores["5_per_qi"] 覆盖全部 Qi)
   - 答题义务台账 (候选版, 仅 gate 5/8): stages.2.obligations 存在时校验
     (unstarted 拦截; partial 提示披露义务; 缺失仅提示不拦截)
2. --checkpoint <key>: 只查该必停点是否真 answered, 不查 scores
   (阶段中途人工停点用; 合法键: kickoff_5q / analysis_confirm / card_decision /
    figure_menu.Q<n> / qi_verdict.Q<n>, 其余键业务 FAIL)
3. 只读脚本: 绝不写 decision_log; 不提供任何跳过/绕过开关

退出码: 0 = 放行; 1 = 拦截 (缺失项以中文清单列出); 2 = argparse 标准 CLI
参数语法错误 (argparse 自身行为, 业务放行/拦截一律只返回 0/1)。

路径协议:
- decision_log: 默认 cwd/state/decision_log.json, 可用 MATHMODEL_STATE_DIR (兼容老 CUMCM_STATE_DIR) 或 --decision-log 覆盖

用法:
    python scripts/check_gate.py --gate 2
    python scripts/check_gate.py --gate 5 --json
    python scripts/check_gate.py --checkpoint analysis_confirm
"""

import json
import math
import os
import re
import argparse
from datetime import datetime
from pathlib import Path


# 必停点键 → 关联 gate (与 SKILL.md "必停点协议 (v2.3.0)" / decision_log 模板 _checkpoints_doc 一致)
SINGLE_GATE_CHECKPOINTS = {
    0: "kickoff_5q",
    2: "analysis_confirm",
    3: "card_decision",
}

VALID_GATES = set(range(0, 9))

# 合法子问键: Q 后跟不含前导零的正整数 (Q1, Q2, ...; Q0/Q01/Q999x 均不合规格)
QI_KEY_RE = re.compile(r"^Q[1-9]\d*$")

# --checkpoint 合法键: 三个单值必停点 + 两个点路径组 (组必须带 .Q<n>, 不接受裸组名)
_CHECKPOINT_KEY_RE = re.compile(
    r"^(kickoff_5q|analysis_confirm|card_decision|(figure_menu|qi_verdict)\.Q[1-9]\d*)$")

# 评分 verdict 合法集合 (与 scripts/score_artifact.py VALID_VERDICTS 保持一致;
# 不直接 import, 保证本脚本在任意 cwd 独立可跑)
VALID_VERDICTS = {
    "block", "pass_early", "pass", "pass_with_review",
    "refine", "refine_partial", "carryover"
}

# 评分记录必填字段 (score_artifact.py update_decision_log 写入口径)
SCORE_ENTRY_REQUIRED_FIELDS = ("iteration", "scores", "min", "mean", "verdict", "ts")

# 答题义务台账状态 (候选版, modeling_evidence_protocol.md Stage 2)
OBLIGATION_STATUS = ("unstarted", "partial", "verified")


def resolve_decision_log_path(cli_arg: str = None) -> Path:
    """路径解析协议: CLI > MATHMODEL_STATE_DIR > CUMCM_STATE_DIR (兼容) > cwd/state/decision_log.json"""
    if cli_arg:
        return Path(cli_arg)
    env_dir = os.environ.get("MATHMODEL_STATE_DIR") or os.environ.get("CUMCM_STATE_DIR")
    if env_dir:
        return Path(env_dir) / "decision_log.json"
    return Path.cwd() / "state" / "decision_log.json"


def load_decision_log(path: Path) -> dict:
    """读 decision_log; 文件不存在/读失败/JSON 损坏时抛对应异常, 由 main 统一中文输出。"""
    if not path.exists():
        raise FileNotFoundError(f"{path} 不存在。请先 stage 0 初始化 (cp <skill>/templates/shared/decision_log.json {path})")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# trusted 来源: 主 agent 流程 (chat) 与 runtime CLI answer (user_cli);
# 其余值 (model/llm/agent/auto/mock/缺失) 一律视为未答
TRUSTED_SOURCES = ("chat", "user_cli")


def is_answered(entry) -> bool:
    """checkpoints 条目是否已由用户真实作答。

    四项缺一即未答: status == "answered"; asked_at 非空且可解析为 ISO 时间;
    answer 为非空字符串; source ∈ {"chat", "user_cli"}。
    """
    if not isinstance(entry, dict) or entry.get("status") != "answered":
        return False
    asked_at = entry.get("asked_at")
    if not isinstance(asked_at, str) or not asked_at.strip():
        return False
    try:
        datetime.fromisoformat(asked_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    answer = entry.get("answer")
    if not (isinstance(answer, str) and bool(answer.strip())):
        return False
    return entry.get("source") in TRUSTED_SOURCES


def _unanswered_note(entry) -> str:
    """未答原因中关于来源的补充说明 (source 缺失或非 chat/user_cli)。"""
    if isinstance(entry, dict) and entry.get("source") not in TRUSTED_SOURCES:
        return f"; 来源不可信/缺失 (source={entry.get('source')!r}, 须为 chat 或 user_cli)"
    return ""


def shallow_schema_problems(log) -> list:
    """浅层 schema 校验: 语法合法但类型损坏的 decision_log 统一转中文缺失项, 不抛 traceback。"""
    problems = []
    if not isinstance(log, dict):
        return [f"decision_log 顶层必须是 JSON 对象, 实际类型: {type(log).__name__}"]
    for field in ("scores", "stages"):
        value = log.get(field)
        if not isinstance(value, dict):  # 缺失或显式 null 同样拦截 (None 不是 dict)
            problems.append(f"decision_log.{field} 格式错误 (缺失或为 null, 应为 dict, 实际 {type(value).__name__}), 需修复 decision_log")
    if "checkpoints" in log:
        checkpoints = log["checkpoints"]
        # 旧 schema (3.0) 完全没有该字段按未登记处理; 有字段但类型损坏才算格式错误
        if checkpoints is not None and not isinstance(checkpoints, dict):
            problems.append(f"decision_log.checkpoints 格式错误 (应为 dict 或缺失, 实际 {type(checkpoints).__name__}), 需修复 decision_log")
    stages = log.get("stages")
    if isinstance(stages, dict):
        stage5 = stages.get("5")
        if stage5 is not None and not isinstance(stage5, dict):
            problems.append(f"decision_log.stages['5'] 格式错误 (应为 dict, 实际 {type(stage5).__name__}), 需修复 decision_log")
        elif isinstance(stage5, dict):
            for field in ("qi_status", "sub_problems"):
                value = stage5.get(field)
                if value is not None and not isinstance(value, dict):
                    problems.append(f"decision_log.stages.5.{field} 格式错误 (应为 dict, 实际 {type(value).__name__}), 需修复 decision_log")
    checkpoints = log.get("checkpoints") if isinstance(log, dict) else None
    if isinstance(checkpoints, dict):
        for field in ("figure_menu", "qi_verdict"):
            value = checkpoints.get(field)
            if value is not None and not isinstance(value, dict):
                problems.append(f"decision_log.checkpoints.{field} 格式错误 (应为 dict, 实际 {type(value).__name__}), 需修复 decision_log")
    return problems


def _stage5_dict(log: dict) -> dict:
    """安全取 stages['5'] 为 dict (类型损坏时返回空 dict, 由 shallow_schema 先行拦截)。"""
    stages = log.get("stages")
    if not isinstance(stages, dict):
        return {}
    stage5 = stages.get("5")
    return stage5 if isinstance(stage5, dict) else {}


def _normalize_qi_keys(raw: dict, field: str, notes: list) -> set:
    """把 qi_status / sub_problems 的键正规化为 Q<n> 集合 (孤立键记 warning 并排除)。"""
    keys = set()
    for key in raw.keys():
        if key == "_template":
            continue
        if QI_KEY_RE.match(str(key)):
            keys.add(str(key))
        else:
            notes.append(f"[warning] stages.5.{field} 存在不合 Q<n> 规格的孤立键 {key!r}, 已忽略")
    return keys


def _is_finite_number(value) -> bool:
    """有限数值 (int/float 且非 bool、非 nan/inf)。"""
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value))


def validate_score_entries(entries, per_qi: bool = False) -> list:
    """
    校验 scores[stage_key] 评分记录列表的结构 (对齐 score_artifact.py 写入口径)。

    要求: 非空 list; 每条为 dict, 含 iteration/scores/min/mean/verdict/ts:
    - iteration: 非负 int (bool 不算)
    - scores: 非空 dict 且值为有限数值
    - min/mean: 有限数值 (bool/nan/inf 不算)
    - verdict ∈ VALID_VERDICTS
    - ts: 非空字符串且可解析为时间
    - per_qi 条目另须 qi_id: str 且匹配 QI_KEY_RE (Q1, Q2, ...; 防非字符串键入集合)
    """
    problems = []
    if not isinstance(entries, list) or not entries:
        return [f"须为非空 list, 实际: {type(entries).__name__}" if not isinstance(entries, list) else "为空 list"]
    for i, entry in enumerate(entries):
        label = f"第 {i + 1} 条"
        if not isinstance(entry, dict):
            problems.append(f"{label} 不是 dict ({type(entry).__name__})")
            continue
        for field in SCORE_ENTRY_REQUIRED_FIELDS:
            if field not in entry:
                problems.append(f"{label} 缺字段 {field}")
        iteration = entry.get("iteration")
        if "iteration" in entry and (isinstance(iteration, bool)
                                     or not isinstance(iteration, int) or iteration < 0):
            problems.append(f"{label}.iteration 必须是非负整数, 实际: {iteration!r}")
        scores = entry.get("scores")
        if "scores" in entry:
            if not isinstance(scores, dict) or not scores:
                problems.append(f"{label}.scores 必须是非空 dict, 实际: {type(scores).__name__}")
            else:
                bad = [k for k, v in scores.items() if not _is_finite_number(v)]
                if bad:
                    problems.append(f"{label}.scores 存在非有限数值的维度分: {', '.join(map(str, bad[:5]))}")
        for field in ("min", "mean"):
            value = entry.get(field)
            if field in entry and not _is_finite_number(value):
                problems.append(f"{label}.{field} 必须是有限数字, 实际: {value!r}")
        ts = entry.get("ts")
        if "ts" in entry:
            if not isinstance(ts, str) or not ts.strip():
                problems.append(f"{label}.ts 必须是非空字符串, 实际: {ts!r}")
            else:
                try:
                    datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    problems.append(f"{label}.ts 不是可解析的时间: {ts!r}")
        if per_qi:
            qi_id = entry.get("qi_id")
            if not isinstance(qi_id, str) or not QI_KEY_RE.match(qi_id):
                problems.append(f"{label}.qi_id 非法 (必须是形如 Q1/Q2 的字符串): {qi_id!r}")
        verdict = entry.get("verdict")
        if "verdict" in entry and verdict not in VALID_VERDICTS:
            problems.append(f"{label}.verdict 非法: {verdict!r} (合法集合见 score_artifact.py VALID_VERDICTS)")
    return problems


def check_gate(log: dict, gate: int) -> dict:
    """
    检查 gate N 的放行条件。返回 {"pass": bool, "missing": [中文缺失项], "notes": [提示]}。
    """
    missing = []
    notes = []

    schema_problems = shallow_schema_problems(log)
    if schema_problems:
        return {"pass": False, "missing": schema_problems, "notes": notes}

    scores = log.get("scores", {})

    # 1. 评分落盘 (E 合并)
    if gate == 5:
        # 双路径: scores["5"] (stage-level) 或 scores["5_per_qi"] (per-Qi, 覆盖全部 Qi)
        stage_level = scores.get("5")
        per_qi = scores.get("5_per_qi")
        problems_a = validate_score_entries(stage_level) if stage_level else ["scores['5'] 为空"]
        problems_b = []
        if per_qi:
            problems_b = validate_score_entries(per_qi, per_qi=True)
            if not problems_b and isinstance(per_qi, list):
                covered = {e.get("qi_id") for e in per_qi if isinstance(e, dict)}
                expected, _ = expected_qis(log, notes)
                if expected is not None:
                    gaps = sorted(expected - covered)
                    if gaps:
                        problems_b.append(f"scores['5_per_qi'] 未覆盖全部子问, 缺: {', '.join(gaps)}")
        else:
            problems_b = ["scores['5_per_qi'] 为空"]
        if problems_a and problems_b:
            missing.append(
                "scores['5'] 与 scores['5_per_qi'] 双路径均不合格 (满足其一即可): "
                f"scores['5'] 问题: {'; '.join(problems_a)}; "
                f"scores['5_per_qi'] 问题: {'; '.join(problems_b)}. "
                "先跑 rubric L1 自评 + score_artifact.py 落盘 "
                "(stage-level: python scripts/score_artifact.py --stage 5 --critique <critique.json>; "
                "per-Qi: 加 --variant per_qi --qi-id Q<i>)")
    else:
        entries = scores.get(str(gate))
        problems = validate_score_entries(entries) if entries else [f"scores['{gate}'] 为空"]
        if problems:
            missing.append(
                f"scores['{gate}'] 不合格: {'; '.join(problems)}. "
                f"先跑 rubric L1 自评 + score_artifact.py 落盘 "
                f"(python scripts/score_artifact.py --stage {gate} --critique <critique.json>)")

    # 2. 必停点 checkpoints
    checkpoints = log.get("checkpoints")
    if checkpoints is None:
        # 旧 schema (v3.0) 无 checkpoints 字段: 按 unanswered 处理, 不 crash
        notes.append("decision_log 无 checkpoints 字段 (旧 schema 3.0 state)。这是 v2.3.0 起门禁的预期拦截, 需重新走必停点问答并登记 checkpoints (详见 SKILL.md 必停点协议)。")
        if gate in SINGLE_GATE_CHECKPOINTS or gate == 5:
            key_names = [SINGLE_GATE_CHECKPOINTS[gate]] if gate in SINGLE_GATE_CHECKPOINTS else ["figure_menu", "qi_verdict"]
            for key in key_names:
                missing.append(f"checkpoints.{key} 缺失 (旧 state): 必停点未登记, 需真问用户后登记")
        return {"pass": False, "missing": missing, "notes": notes}

    if gate in SINGLE_GATE_CHECKPOINTS:
        key = SINGLE_GATE_CHECKPOINTS[gate]
        entry = checkpoints.get(key)
        if not is_answered(entry):
            missing.append(f"checkpoints.{key} 未 answered (status/asked_at/answer/source "
                           f"四项缺一即未答, source 须为 chat 或 user_cli)"
                           f"{_unanswered_note(entry)}: 必停点未真问用户, 先问再登记")
    elif gate == 5:
        expected, enum_problems = expected_qis(log, notes)
        if enum_problems:
            missing.extend(enum_problems)
        if expected is not None:
            figure_menu = checkpoints.get("figure_menu") or {}
            qi_verdict = checkpoints.get("qi_verdict") or {}
            for qi in sorted(expected):
                entry = figure_menu.get(qi)
                if not is_answered(entry):
                    missing.append(f"checkpoints.figure_menu['{qi}'] 未 answered"
                                   f"{_unanswered_note(entry)}: 该问图表菜单未真问用户")
                else:
                    missing.extend(_figure_menu_content_problems(qi, entry))
                if not is_answered(qi_verdict.get(qi)):
                    missing.append(f"checkpoints.qi_verdict['{qi}'] 未 answered"
                                   f"{_unanswered_note(qi_verdict.get(qi))}: 该问 verdict 未经用户逐问确认")

    # 3. 答题义务台账镜像 (候选版; 仅 gate 5/8)
    if gate in (5, 8):
        ob_missing, ob_notes = _obligation_problems(log, gate)
        missing.extend(ob_missing)
        notes.extend(ob_notes)

    return {"pass": not missing, "missing": missing, "notes": notes}


def _obligation_problems(log: dict, gate: int) -> tuple:
    """答题义务台账镜像检查 (候选版, modeling_evidence_protocol.md Stage 2)。

    stages.2.obligations 缺失 → 仅 notes 提示 (兼容旧 state 与未采用台账的流程);
    存在则校验: 非空 list, 每条含 id/min_output, status ∈ {unstarted, partial, verified}。
    unstarted → FAIL (必须先完成或经用户确认降级情景并在台账记录);
    partial → 不拦截, 但 gate 5 提示移交纪律, gate 8 提示 stage 9 须确认正文如实披露。
    """
    missing, notes = [], []
    stages = log.get("stages")
    stage2 = stages.get("2") if isinstance(stages, dict) else None
    if not isinstance(stage2, dict) or "obligations" not in stage2:
        notes.append("stages.2.obligations 未登记 (答题义务台账镜像): 候选版建议 stage 2 "
                     "把每条题面义务写为 {id, statement, min_output, status, gap}, 供 gate 5/8 追踪漏答")
        return missing, notes
    obs = stage2.get("obligations")
    if not isinstance(obs, list) or not obs:
        missing.append("stages.2.obligations 已登记但为空或类型错误 (应为非空 list)")
        return missing, notes
    unstarted, partial = [], []
    for i, ob in enumerate(obs):
        label = f"stages.2.obligations[{i}]"
        if not isinstance(ob, dict):
            missing.append(f"{label} 不是 dict")
            continue
        ob_id = str(ob.get("id", "")).strip()
        if not ob_id:
            missing.append(f"{label} 缺 id")
            ob_id = f"#{i}"
        if not str(ob.get("min_output", "")).strip():
            missing.append(f"{label} (id={ob_id}) 缺 min_output (该义务的最小可验收输出)")
        status = ob.get("status")
        if status not in OBLIGATION_STATUS:
            missing.append(f"{label} (id={ob_id}) status 非法: {status!r} "
                           f"(合法: {'/'.join(OBLIGATION_STATUS)})")
        elif status == "unstarted":
            unstarted.append(ob_id)
        elif status == "partial":
            partial.append(ob_id)
    if unstarted:
        missing.append(f"答题义务仍未启动: {', '.join(unstarted)} — "
                       "先完成，或经用户确认降级为明确情景/范围并在台账记录缺口")
    if partial:
        if gate == 5:
            notes.append(f"答题义务 partial: {', '.join(partial)} — "
                         "允许带缺口移交, 但 stage 8 正文不得写成已全部回答")
        else:
            notes.append(f"答题义务 partial: {', '.join(partial)} — "
                         "stage 9 须确认正文与摘要已如实披露缺口与适用范围")
    return missing, notes


def expected_qis(log: dict, notes: list) -> tuple:
    """
    完成态语义 (仅 gate 5 用): 三来源必须**全部存在且指向同一集合**。

    - qi_count 必须是严格正 int (存在但 null/bool/字符串/非正 → FAIL 列出实际值)
    - qi_status 必须是非空 dict (非 dict 或空 → FAIL)
    - sub_problems 排除 "_template" 后必须非空 (非 dict 或空 → FAIL)
    - 三者集合必须相等 (不等 → FAIL 并列出各来源)

    Returns: (集合, []) 三来源对齐; (None, [FAIL 缺失项]) 任一条件不满足。
    """
    stage5 = _stage5_dict(log)
    problems = []
    qi_count = stage5.get("qi_count")
    if type(qi_count) is not int or qi_count <= 0:
        problems.append(f"stages.5.qi_count 必须是正整数, 实际值: {qi_count!r}")
        count_set = None
    else:
        count_set = {f"Q{i}" for i in range(1, qi_count + 1)}
    sources = {}
    for field in ("qi_status", "sub_problems"):
        raw = stage5.get(field)
        if not isinstance(raw, dict):
            problems.append(f"stages.5.{field} 缺失或类型错误 (应为非空 dict, 实际 {type(raw).__name__})")
            continue
        keys = _normalize_qi_keys(raw, field, notes)
        if not keys:
            problems.append(f"stages.5.{field} 为空 (排除 _template 后无任何 Q<n> 键), 无法完成三来源对齐")
        else:
            sources[field] = keys
    if problems:
        return None, problems + [
            "stage 5 子问三来源 (qi_count / qi_status / sub_problems) 必须全部登记且指向同一集合, "
            "请先补齐 stages.5 登记, 再走必停点问答"]
    if count_set != sources["qi_status"] or count_set != sources["sub_problems"]:
        detail = (f"qi_count: {sorted(count_set)}; "
                  f"qi_status: {sorted(sources['qi_status'])}; "
                  f"sub_problems: {sorted(sources['sub_problems'])}")
        return None, [f"stage 5 子问来源间不一致 (qi_count / qi_status / sub_problems 须指向同一集合): {detail}。"
                      "请核对 stages.5.qi_count 与实际子问登记, 修复后再走必停点问答"]
    return count_set, []


def _figure_menu_content_problems(qi: str, entry) -> list:
    """figure_menu 条目内容校验 (R4.4): 必须有 count (int 0-9); count≤1 时必须
    exception: true 且 reason 非空 (D.1 例外确认), 否则 FAIL。"""
    problems = []
    count = entry.get("count") if isinstance(entry, dict) else None
    if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 9:
        problems.append(f"checkpoints.figure_menu['{qi}'].count 非法 (须为 0-9 的整数), 实际: {count!r}")
    elif count <= 1:
        if entry.get("exception") is not True:
            problems.append(f"checkpoints.figure_menu['{qi}'].count={count} 为低频决策, "
                            "须按 D.1 登记披露: 条目加 \"exception\": true")
        reason = entry.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            problems.append(f"checkpoints.figure_menu['{qi}'].count={count} 须登记非空 reason "
                            "(该问 0/1 图的证据呈现方式说明, 作决策追溯)")
    return problems


def check_checkpoint(log: dict, key: str) -> dict:
    """
    --checkpoint 模式: 只查指定必停点是否真 answered, 不查 scores。
    key 只接受: kickoff_5q / analysis_confirm / card_decision / figure_menu.Q<n> /
    qi_verdict.Q<n> (n≥1); 其余键业务 FAIL 并列出合法格式。
    """
    if not _CHECKPOINT_KEY_RE.match(key or ""):
        return {"pass": False,
                "missing": [f"--checkpoint 键 {key!r} 不合法。合法格式: kickoff_5q / "
                            "analysis_confirm / card_decision / figure_menu.Q<n> / "
                            "qi_verdict.Q<n> (n 为 ≥1 的整数, 不含前导零)"],
                "notes": []}
    schema_problems = shallow_schema_problems(log)
    if schema_problems:
        return {"pass": False, "missing": schema_problems, "notes": []}
    value = log.get("checkpoints")
    if value is None:
        return {"pass": False,
                "missing": [f"checkpoints.{key} 缺失 (旧 schema 3.0 state 或未登记): 必停点未真问用户, 先问再登记"],
                "notes": ["decision_log 无 checkpoints 字段 (旧 schema 3.0 state)。这是 v2.3.0 起门禁的预期拦截, 需补走必停点问答并登记 checkpoints (详见 SKILL.md 必停点协议)。"]}
    node = value
    traversed = []
    for part in key.split("."):
        if not isinstance(node, dict):
            return {"pass": False,
                    "missing": [f"checkpoints.{'.'.join(traversed)} 不是 dict, 无法继续取 {part}"],
                    "notes": []}
        traversed.append(part)
        node = node.get(part)
    dotted = ".".join(traversed)
    if not is_answered(node):
        return {"pass": False,
                "missing": [f"checkpoints.{dotted} 未 answered (status/asked_at/answer/source "
                            f"四项缺一即未答, source 须为 chat 或 user_cli)"
                            f"{_unanswered_note(node)}: 必停点未真问用户, 先问再登记"],
                "notes": []}
    if dotted.startswith("figure_menu.Q"):
        # 与 gate 5 同口径的 figure_menu 内容校验 (count 必填 0-9; count≤1 须 exception+reason)
        problems = _figure_menu_content_problems(dotted.split(".", 1)[1], node)
        if problems:
            return {"pass": False, "missing": problems, "notes": []}
    return {"pass": True, "missing": [], "notes": []}


def _emit(result: dict, args, decision_log_path: Path, mode: str) -> int:
    """统一输出 (文本 / --json)。"""
    if args.json:
        print(json.dumps({
            "mode": mode,
            "gate": getattr(args, "gate", None),
            "checkpoint": getattr(args, "checkpoint", None),
            "decision_log": str(decision_log_path),
            "pass": result["pass"],
            "missing": result["missing"],
            "notes": result["notes"],
        }, ensure_ascii=False, indent=2))
    else:
        if result["pass"]:
            if mode == "gate":
                print(f"[PASS] gate {args.gate} → {args.gate + 1} 放行 (checkpoints 与 scores 均已登记)")
            else:
                print(f"[PASS] checkpoints.{args.checkpoint} 已 answered")
        else:
            label = (f"gate {args.gate} → {args.gate + 1} 拦截" if mode == "gate"
                     else f"checkpoints.{args.checkpoint} 拦截")
            print(f"[FAIL] {label}, 缺失项:")
            for item in result["missing"]:
                print(f"  - {item}")
        for note in result["notes"]:
            print(f"  {note}" if note.startswith("[warning]") else f"  [提示] {note}")
    return 0 if result["pass"] else 1


def main() -> int:
    # Windows CP936 控制台下 --json 输出中文防止 UnicodeEncodeError
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except AttributeError:
        pass  # 非 TextIOWrapper 场景 (重定向到自定义对象), 忽略

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--gate", type=int,
                       help="检查从 stage N 推进到 N+1 的放行条件 (N = 0-8)")
    group.add_argument("--checkpoint", type=str, metavar="KEY",
                       help="只查该必停点是否 answered (不查 scores), 如 analysis_confirm / figure_menu.Q1")
    parser.add_argument("--decision-log", type=str, default=None,
                        help="覆盖路径解析协议; 默认 cwd/state/decision_log.json")
    parser.add_argument("--json", action="store_true",
                        help="输出机器可读 JSON 结果")
    args = parser.parse_args()

    if args.gate is not None and args.gate not in VALID_GATES:
        print(f"[FAIL] --gate 必须 ∈ 0-8, 实际: {args.gate}")
        return 1

    decision_log_path = resolve_decision_log_path(args.decision_log)

    try:
        log = load_decision_log(decision_log_path)
    except FileNotFoundError as exc:
        print(f"[FAIL] {exc}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"[FAIL] {decision_log_path} 不是合法 JSON: {exc}")
        return 1
    except UnicodeDecodeError as exc:
        print(f"[FAIL] {decision_log_path} 不是合法 UTF-8 文件: {exc}")
        return 1
    except OSError as exc:
        print(f"[FAIL] 无法读取 {decision_log_path}: {exc}")
        return 1

    if args.checkpoint is not None:
        result = check_checkpoint(log, args.checkpoint)
        return _emit(result, args, decision_log_path, "checkpoint")

    result = check_gate(log, args.gate)
    return _emit(result, args, decision_log_path, "gate")


if __name__ == "__main__":
    import sys
    sys.exit(main())
