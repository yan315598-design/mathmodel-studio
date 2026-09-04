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
                "k 为当前迭代号 ([ITER k]), critique.iteration 必须等于 k。")


def build_prompt(skill_root: Path, state: DecisionLog, workspace: Path,
                 stage: int, iteration: int = 0) -> str:
    """组装单个 stage 一次迭代的完整 prompt。"""
    ref_path = Path(skill_root) / "references" / STAGE_FILES.get(stage, "")
    ref = (ref_path.read_text(encoding="utf-8", errors="replace")[:REF_CHAR_CAP]
           if ref_path.exists() else "(stage reference 缺失)")
    return "\n\n".join([
        f"[STAGE {stage} {STAGE_LABELS.get(stage, '?')}] "
        f"competition={state.data.get('competition')} mode={state.data.get('mode')}",
        f"[ITER {iteration}]",
        "## stage reference (截断)\n" + ref,
        "## state 摘要\n" + json.dumps(state.summary(), ensure_ascii=False),
        "## workspace 文件\n" + ("\n".join(list_workspace(workspace)) or "(空)"),
        "## " + PROTOCOL_DOC,
    ])


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
