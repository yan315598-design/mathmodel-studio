"""prompt 组装: stage reference + state 摘要 + workspace 文件清单 + 输出协议。"""
from __future__ import annotations

import json
from pathlib import Path

from .state import DecisionLog

# stage 编号 -> 标签; 文件名按 references/stage_NN_<label>.md 约定推导
STAGE_LABELS = {0: "kickoff", 1: "problem_selection", 2: "analysis", 3: "model_selection",
                4: "foundation", 5: "subproblem_loop", 6: "robustness", 7: "evaluation",
                8: "writing", 9: "review"}
STAGE_FILES = {i: f"stage_{i:02d}_{label}.md" for i, label in STAGE_LABELS.items()}
# 角色分档: 0-2 信息抽取, 3-6 建模求解, 7-8 论文写作, 9 评审
STAGE_ROLES = {**{i: "extraction" for i in range(3)}, **{i: "solving" for i in (3, 4, 5, 6)},
               **{i: "writing" for i in (7, 8)}, 9: "review"}
REF_CHAR_CAP = 4000  # stage reference 注入 prompt 的字符上限 (原型级截断)

PROTOCOL_DOC = ("输出协议: 结论写正文; 需要落盘的文件用围栏块 "
                "```artifact:<workspace相对路径>\\n<文件内容>``` 输出, 一个块一个文件。"
                "state/stage_<n>_patch.json 会被浅合并进 decision_log.stages[n]; "
                "state/critique_stage<n>_v{k}.json 会触发 score_artifact 评分, "
                "k 为当前迭代号 ([ITER k]), critique.iteration 必须等于 k。"
                "绝不生成 state/checkpoints_patch.json 或任何 checkpoints 内容——"
                "必停点只能经 checkpoint_request 指令由人工登记 (见必停点协议)。")

# v2.3.0 必停点协议 (完整协议见 SKILL.md): 单独注入, 不受 stage reference 截断影响。
# checkpoint 只能由"人"写: LLM 只能发 checkpoint_request 指令申请, 绝不可自写登记。
CHECKPOINT_DOC = (
    "## 必停点协议 (v2.3.0, HIL-lite, 全文见 SKILL.md)\n"
    "六个必停点必须真实问过用户并由人工登记; LLM 只能**申请**, 不能**登记**:\n"
    "1. 到达必停点时, 在正文单独一行输出指令 `checkpoint_request: <key>` (取值: "
    "stage 0→kickoff_5q; 2→analysis_confirm; 3→card_decision; "
    "5→figure_menu.Q<n> / qi_verdict.Q<n> / per_qi_selection.Q<n>; "
    "其余 stage 无必停点, 不得出现该指令)。\n"
    "2. runtime 会暂停 (paused) 并等待用户经 CLI answer 命令作答; "
    "恢复后用户答案会以「必停点用户应答」小节注入对话, 基于它继续本 stage。\n"
    "3. 绝不生成 state/checkpoints_patch.json 工件或任何 checkpoint 文件/条目内容——"
    "那会被视为伪造必停点 (protocol_error) 并立即停机。\n"
    "任何 stage 推进前 scripts/check_gate.py --gate <N> 必须放行; "
    "runtime 在 _advance() 强制子进程执行, FAIL 即 paused 不推进。")


def build_prompt(skill_root: Path, state: DecisionLog, workspace: Path,
                 stage: int, iteration: int = 0) -> str:
    """组装单个 stage 一次迭代的完整 prompt。"""
    ref_path = Path(skill_root) / "references" / STAGE_FILES.get(stage, "")
    ref = (ref_path.read_text(encoding="utf-8", errors="replace")[:REF_CHAR_CAP]
           if ref_path.exists() else "(stage reference 缺失)")
    sections = [
        f"[STAGE {stage} {STAGE_LABELS.get(stage, '?')}] "
        f"competition={state.data.get('competition')} mode={state.data.get('mode')}",
        f"[ITER {iteration}]",
        "## stage reference (截断)\n" + ref,
        "## " + CHECKPOINT_DOC,
    ]
    sections.append(_answered_checkpoint_section(state))
    sections += [
        "## state 摘要\n" + json.dumps(state.summary(), ensure_ascii=False),
        "## workspace 文件\n" + ("\n".join(list_workspace(workspace)) or "(空)"),
        "## " + PROTOCOL_DOC,
    ]
    return "\n\n".join(sections)


def _answered_checkpoint_section(state: DecisionLog) -> str:
    """已由用户经 CLI answer 登记的必停点上下文 (恢复后注入, LLM 据此继续)。

    [CP_ANSWERED <key>] 是给 MockLLM 用的机器标记, 不受人类可读文案变化影响。
    """
    lines = ["## 必停点用户应答 (人工经 answer 命令登记, 恢复后据此继续)"]
    checkpoints = state.data.get("checkpoints")
    found = False
    if isinstance(checkpoints, dict):
        for top in ("kickoff_5q", "analysis_confirm", "card_decision"):
            if state.checkpoint_is_answered(top):
                entry = checkpoints[top]
                lines.append(f"[CP_ANSWERED {top}] answer: {entry.get('answer')}")
                found = True
        for group in ("figure_menu", "qi_verdict", "per_qi_selection"):
            node = checkpoints.get(group)
            if isinstance(node, dict):
                for qi in sorted(node):
                    key = f"{group}.{qi}"
                    if state.checkpoint_is_answered(key):
                        lines.append(f"[CP_ANSWERED {key}] answer: {node[qi].get('answer')}")
                        found = True
    if not found:
        lines.append("(暂无)")
    return "\n".join(lines)


def list_workspace(workspace: Path, cap: int = 60) -> list[str]:
    """workspace 相对路径清单 (跳过缓存/归档目录, 上限 cap 条)。"""
    skips = {"_runtime", "_archive", "__pycache__"}
    files: list[str] = []
    for path in sorted(Path(workspace).rglob("*")):
        if len(files) >= cap:
            break
        rel = path.relative_to(workspace)
        if path.is_file() and not (skips & set(rel.parts)):
            files.append(rel.as_posix())
    return files
