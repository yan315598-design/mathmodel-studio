"""
run_eval.py — 最小评测 runner: 伪 holdout 索引构建 / 单次建模工作区指标采集 / 双跑对比

背景:
    本 skill 的蒸馏语料覆盖 2021-2025 全部赛题, 直接用任一届做端到端评测等于
    "开卷考试", 无法度量 prompt 改动对论文质量的真实影响。本脚本提供三件事:

    1. build-holdout-index: 把 competitions/<comp>/cases/ 的 index.json 与
       manual_review_annotations.json 过滤掉指定年份后, 写成 <out>/ 下的
       同名镜像目录 (源文件不动, 可随时弃用镜像恢复)。
    2. score-run: 对一个建模工作区目录调用现有 QA/评分脚本
       (score_artifact --mode judge / consistency_audit / trace_claims /
       figqa / pdf_qa, 存在哪个跑哪个, 缺失标记 skipped), 汇总为 JSON。
    3. compare: 并排打印两次评测的指标差异表 (metric / A / B / delta)。

判读约定 (与 evals/README.md 一致):
    status=ok      子脚本正常完成; exit_code 1 通常是质量门结果 (可比指标)
    status=skipped 输入缺失 (如工作区无 judge_input.json), 不参与对比
    status=error   子进程崩溃/超时/退出码非质量门语义 (如 rc=2 输入错)/
                   输出形态非预期 —— 该跑不可比, 先修环境

用法:
    python evals/run_eval.py build-holdout-index --competition huaweibei \
        --exclude-year 2024 --out evals/holdout_index
    python evals/run_eval.py score-run --workspace <建模工作区> --label myrun
    python evals/run_eval.py compare evals/results/a.json evals/results/b.json

协议详见 evals/holdout_protocol.md 与 evals/README.md。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# evals/ 的上一级即 skill 仓库根
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

# 单个 QA 脚本子进程超时 (秒); figqa 渲染图片可能较慢
TOOL_TIMEOUT_SECONDS = 180

# 指标 schema 版本 (compare 依赖扁平化 key 的稳定性)
EVAL_SCHEMA_VERSION = "eval-run-1.0"

# pdf_qa 报告尾部 "合计: N 项 ❌, M 项 ⚠️"
_PDF_QA_SUMMARY_RE = re.compile(r"合计:\s*(\d+)\s*项\s*❌,\s*(\d+)\s*项\s*⚠️")

# score-run 的 --label 直接作结果文件名前缀, 限单路径段安全字符集
# (字母/数字/下划线/中文开头, 后续可含 . -; 禁止路径分隔符与 ".." 前缀)
_LABEL_RE = re.compile(r"[\w][\w.-]*", re.UNICODE)

# 各工具结果 JSON 的必需字段; 末尾 JSON 缺这些字段 = 输出形态非预期 → error
_JUDGE_REQUIRED_KEYS = {"verdict"}
_AUDIT_REQUIRED_KEYS = {"summary", "exit_code"}
_TRACE_REQUIRED_KEYS = {"row_count", "complete_count", "abstract_ready"}


class EvalInputError(Exception):
    """输入数据非法 (JSON 损坏 / 字段类型错), 携带面向用户的可读信息。"""


# ============================================================================
# 通用小工具
# ============================================================================

def _tail(text: str, limit: int = 2000) -> str:
    """诊断用: 只保留文本尾部 (完整文本仅用于解析, 不整段入报告)。"""
    return text[-limit:]


def _parse_tool_json(stdout: str, required_keys: set[str]):
    """从完整 stdout 提取末尾的 JSON 对象并校验必需字段。

    返回 (payload, None) 或 (None, 原因):
    - 必须用完整 stdout 解析: 大输出 (多子问 trace_claims 可达数十 KB) 的
      JSON 起始行若被截掉, 从尾部拼接永远解析不出。
    - 只取"最后一个能从某行整段解析到末尾"的对象 (各工具均把结果 JSON
      打在最后), 再校验必需字段; 末尾 JSON 是别的对象 (stdout 含多个
      JSON 样行) 或缺字段 → 视为输出形态非预期, 不向前猜测。
    """
    lines = stdout.splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if not lines[i].startswith("{"):
            continue
        try:
            payload = json.loads("\n".join(lines[i:]))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and required_keys <= payload.keys():
            return payload, None
        return None, (f"stdout 末尾 JSON 缺少必需字段 {sorted(required_keys)}, "
                      f"实际字段: {sorted(payload) if isinstance(payload, dict) else type(payload).__name__}")
    return None, "stdout 中未找到以 { 开头且可整段解析的 JSON"


def _exit_code_error(exit_code, quality_codes: set[int]) -> str | None:
    """退出码分类: quality_codes 内 = 质量门结果 (status=ok, 可比);
    其余 (含 None=未运行) = 执行/输入错误 → status=error。返回原因或 None。"""
    if exit_code is None:
        return "子进程未运行或超时"
    if exit_code in quality_codes:
        return None
    return f"退出码 {exit_code} 非质量门语义 (质量门退出码: {sorted(quality_codes)})"


def _run_tool(script_name: str, tool_args: list[str]) -> dict:
    """运行 scripts/ 下一个脚本, 返回 {exit_code, stdout, stderr} (完整文本)。

    stdout 完整保留给 _parse_tool_json; 写入报告前由各采集函数截尾。
    超时/找不到脚本按 error 记录, 不让单工具失败拖垮整次评测。
    """
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        return {"status": "error", "reason": f"{script_name} 不存在", "exit_code": None,
                "stdout_tail": "", "stderr_tail": ""}
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path), *tool_args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO_ROOT), timeout=TOOL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "reason": f"超时 (>{TOOL_TIMEOUT_SECONDS}s)",
                "exit_code": None, "stdout_tail": "", "stderr_tail": ""}
    return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def _tool_error(reason: str, result: dict) -> dict:
    """组装 status=error 的工具记录 (附诊断尾部)。"""
    return {"status": "error", "reason": reason, "exit_code": result.get("exit_code"),
            "stdout_tail": _tail(result.get("stdout", "")),
            "stderr_tail": _tail(result.get("stderr", ""), 500)}


# ============================================================================
# 子命令 1: build-holdout-index
# ============================================================================

def _validate_year_field(value, case_id: str) -> int:
    """校验案例 year 字段是整数; 非法抛 EvalInputError (可读信息)。

    拒绝 bool (int 子类陷阱)、None、字符串、非整数 float (2024.9 强转会
    被截断误剔除整届)。
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvalInputError(f"案例 {case_id} 的 year 非法: {value!r} (须为整数)")
    if isinstance(value, float) and not value.is_integer():
        raise EvalInputError(f"案例 {case_id} 的 year 非法: {value!r} (非整数 float, 拒绝截断)")
    return int(value)


def _load_and_filter_cases(src: Path, exclude_year: int):
    """读取并校验案例 JSON, 返回 (保留 cases, 剔除 cases, 原始 dict)。

    文件不存在返回 None; 顶层非对象 / cases 非数组 / 元素非对象 / year 非法
    均抛 EvalInputError。只过滤顶层 cases 数组, 其余顶层键 (如
    manual_review_annotations.json 的 v2_cleanup 元数据) 原样保留。
    """
    if not src.exists():
        return None
    try:
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalInputError(f"{src.name} 无法解析: {exc}") from exc
    if not isinstance(data, dict):
        raise EvalInputError(f"{src.name} 顶层必须是 JSON 对象, 实际: {type(data).__name__}")
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise EvalInputError(f"{src.name} 的 cases 必须是数组, 实际: {type(cases).__name__}")
    kept, removed = [], []
    for case in cases:
        if not isinstance(case, dict):
            raise EvalInputError(f"{src.name} 的 cases 元素必须是对象: {case!r}")
        case_id = str(case.get("id", "<无 id>"))
        year = _validate_year_field(case.get("year"), case_id)
        (removed if year == exclude_year else kept).append(case)
    return kept, removed, data


def cmd_build_holdout_index(args) -> int:
    """把 competitions/<comp>/cases/ 过滤指定年份后镜像到 --out 目录。"""
    repo_root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT
    cases_dir = repo_root / "competitions" / args.competition / "cases"

    try:
        filtered = _load_and_filter_cases(cases_dir / "index.json", args.exclude_year)
    except EvalInputError as exc:
        print(f"[FAIL] {exc}")
        return 1
    if filtered is None:
        print(f"[FAIL] 案例索引不存在: {cases_dir / 'index.json'}")
        return 1
    kept_cases, removed_cases, index_data = filtered
    total = len(index_data.get("cases", []))

    try:
        filtered_ann = _load_and_filter_cases(
            cases_dir / "manual_review_annotations.json", args.exclude_year)
    except EvalInputError as exc:
        print(f"[FAIL] {exc}")
        return 1

    out_cases_dir = Path(args.out) / "competitions" / args.competition / "cases"
    out_cases_dir.mkdir(parents=True, exist_ok=True)

    mirror_index = dict(index_data)
    mirror_index["cases"] = kept_cases
    out_index_path = out_cases_dir / "index.json"
    with open(out_index_path, "w", encoding="utf-8") as f:
        json.dump(mirror_index, f, ensure_ascii=False, indent=1)
    print(f"index.json: {total} -> {len(kept_cases)} (剔除 {total - len(kept_cases)} 条, "
          f"exclude_year={args.exclude_year})")
    for case in removed_cases:
        print(f"  剔除: {case.get('id', '?')}")

    if filtered_ann is None:
        print("manual_review_annotations.json: 不存在, 跳过")
    else:
        kept_ann, _removed_ann, ann_data = filtered_ann
        mirror_ann = dict(ann_data)
        mirror_ann["cases"] = kept_ann
        out_ann_path = out_cases_dir / "manual_review_annotations.json"
        with open(out_ann_path, "w", encoding="utf-8") as f:
            json.dump(mirror_ann, f, ensure_ascii=False, indent=1)
        ann_total = len(ann_data.get("cases", []))
        print(f"manual_review_annotations.json: {ann_total} -> {len(kept_ann)} "
              f"(剔除 {ann_total - len(kept_ann)} 条)")

    print(f"[OK] holdout 索引镜像: {out_cases_dir}")
    print(f"     检索时用 --index {out_index_path} (manual-review 默认读同目录镜像)")
    return 0


# ============================================================================
# 子命令 2: score-run
# ============================================================================

def _score_judge(workspace: Path) -> dict:
    """评委模拟器: 消费 <ws>/state/judge_input.json, 记录 final/tier/verdict。

    质量门退出码 {0, 1}: rc=1 且解析出 verdict=not_eligible 是资格门失败
    (可比); rc=1 但无合法结果 JSON = schema/输入错 → error。
    """
    judge_input = workspace / "state" / "judge_input.json"
    if not judge_input.exists():
        return {"status": "skipped", "reason": "state/judge_input.json 不存在"}
    result = _run_tool("score_artifact.py",
                       ["--mode", "judge", "--judge-input", str(judge_input)])
    if result.get("exit_code") is None:
        return result
    payload, parse_reason = _parse_tool_json(result["stdout"], _JUDGE_REQUIRED_KEYS)
    if payload is None:
        return _tool_error(f"judge 结果解析失败: {parse_reason}", result)
    verdict = payload.get("verdict")
    if verdict not in ("eligible", "not_eligible"):
        return _tool_error(f"judge verdict 非预期: {verdict!r}", result)
    summary = {"status": "ok", "exit_code": result["exit_code"], "verdict": verdict}
    for key in ("final", "raw", "tier", "format_score"):
        if key in payload:
            summary[key] = payload[key]
    if verdict == "not_eligible":
        summary["failed_qualifications"] = payload.get("failed_qualifications", [])
    summary["stdout_tail"] = _tail(result["stdout"], 600)
    return summary


def _score_consistency_audit(workspace: Path) -> dict:
    """一致性审计: 质量门 {0=无❌, 1=有❌}; rc=2 (工作区/IO 错) → error。"""
    result = _run_tool("consistency_audit.py",
                       ["--workspace", str(workspace), "--json"])
    if result.get("exit_code") is None:
        return result
    reason = _exit_code_error(result["exit_code"], quality_codes={0, 1})
    if reason:
        return _tool_error(reason, result)
    payload, parse_reason = _parse_tool_json(result["stdout"], _AUDIT_REQUIRED_KEYS)
    if payload is None:
        return _tool_error(f"audit 结果解析失败: {parse_reason}", result)
    counts = payload.get("summary") or {}
    return {"status": "ok", "exit_code": result["exit_code"],
            "error_count": counts.get("error"), "warn_count": counts.get("warn")}


def _score_trace_claims(workspace: Path) -> dict:
    """证据链追踪: 消费 state/paper_plan.json (或 state/evidence_ledger.json)。

    不加 --strict 时退出码恒 0; 非零即输入/解析错 → error。
    """
    candidates = [workspace / "state" / "paper_plan.json",
                  workspace / "state" / "evidence_ledger.json"]
    ledger = next((p for p in candidates if p.exists()), None)
    if ledger is None:
        return {"status": "skipped", "reason": "state/paper_plan.json 不存在"}
    result = _run_tool("trace_claims.py", ["--input", str(ledger)])
    if result.get("exit_code") is None:
        return result
    reason = _exit_code_error(result["exit_code"], quality_codes={0})
    if reason:
        return _tool_error(reason, result)
    payload, parse_reason = _parse_tool_json(result["stdout"], _TRACE_REQUIRED_KEYS)
    if payload is None:
        return _tool_error(f"trace_claims 结果解析失败: {parse_reason}", result)
    return {"status": "ok", "exit_code": result["exit_code"], "input": ledger.name,
            "rows": payload.get("row_count"),
            "complete": payload.get("complete_count"),
            "incomplete": payload.get("incomplete_count"),
            "coverage": payload.get("coverage"),
            "abstract_ready": payload.get("abstract_ready"),
            "abstract_gate": payload.get("abstract_gate")}


def _score_figqa(workspace: Path) -> dict:
    """图表碰撞检测: 质量门 {0=无碰撞, 1=检出碰撞}; rc=2 (输入/渲染错) → error。"""
    figures_dir = workspace / "figures"
    if not figures_dir.is_dir():
        return {"status": "skipped", "reason": "figures/ 目录不存在"}
    result = _run_tool("figqa.py", [str(figures_dir)])
    if result.get("exit_code") is None:
        return result
    reason = _exit_code_error(result["exit_code"], quality_codes={0, 1})
    if reason:
        return _tool_error(reason, result)
    return {"status": "ok", "exit_code": result["exit_code"],
            "stdout_tail": _tail(result["stdout"], 600)}


def _find_pdf(workspace: Path) -> Path | None:
    """按约定路径优先、全工作区兜底找一个待检 PDF。"""
    for candidate in (workspace / "paper.pdf",
                      workspace / "paper_workspace" / "paper.pdf",
                      workspace / "build" / "paper.pdf"):
        if candidate.exists():
            return candidate
    pdfs = sorted(workspace.rglob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    return pdfs[0] if pdfs else None


def _score_pdf_qa(workspace: Path) -> dict:
    """PDF 终检: 质量门 {0=无❌, 1=有❌}; rc=2 (fatal/PDF 打不开) 或摘要行
    解析不出 → error。"""
    pdf_path = _find_pdf(workspace)
    if pdf_path is None:
        return {"status": "skipped", "reason": "工作区内无 PDF"}
    result = _run_tool("pdf_qa.py", [str(pdf_path)])
    if result.get("exit_code") is None:
        return result
    reason = _exit_code_error(result["exit_code"], quality_codes={0, 1})
    if reason:
        return _tool_error(reason, result)
    summary = {"status": "ok", "exit_code": result["exit_code"],
               "pdf": pdf_path.relative_to(workspace).as_posix()}
    match = _PDF_QA_SUMMARY_RE.search(result["stdout"])
    if match:
        summary["error_count"] = int(match.group(1))
        summary["info_count"] = int(match.group(2))
    else:
        return _tool_error("pdf_qa 摘要行 (合计: N 项 ❌) 解析失败", result)
    return summary


def _summarize_decision_log(workspace: Path) -> dict:
    """汇总 state/decision_log.json 各 stage 最后一次评分 (无则空)。"""
    log_path = workspace / "state" / "decision_log.json"
    if not log_path.exists():
        return {"status": "skipped", "reason": "state/decision_log.json 不存在"}
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            log = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "error", "reason": f"decision_log 无法解析: {exc}"}
    if not isinstance(log, dict):
        return {"status": "error",
                "reason": f"decision_log 顶层必须是 JSON 对象, 实际: {type(log).__name__}"}
    stages = {}
    for stage_key, entries in (log.get("scores") or {}).items():
        if isinstance(entries, list) and entries:
            last = entries[-1]
            stages[stage_key] = {
                "iterations": len(entries),
                "min": last.get("min"),
                "mean": last.get("mean"),
                "verdict": last.get("verdict"),
            }
    return {
        "status": "ok",
        "competition": log.get("competition"),
        "task_type": log.get("task_type"),
        "stage_count": len(stages),
        "stages": stages,
    }


def _inventory_artifacts(workspace: Path) -> dict:
    """产物文件清单 (相对路径 + 字节数)。

    state/ 与 results/ 是流程状态/中间结果目录, __pycache__ 是缓存,
    均不计入 (与 evals/README.md 的口径一致)。
    """
    excluded_roots = {"state", "results"}
    files = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(workspace).parts
        if "__pycache__" in rel_parts or rel_parts[0] in excluded_roots:
            continue
        files.append({"path": "/".join(rel_parts),
                      "bytes": path.stat().st_size})
    return {"file_count": len(files),
            "total_bytes": sum(f["bytes"] for f in files),
            "files": files}


def cmd_score_run(args) -> int:
    """采集工作区指标并写 evals/results/<label>_<timestamp>.json。"""
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        print(f"[FAIL] 工作区不存在: {workspace}")
        return 1
    if not _LABEL_RE.fullmatch(args.label):
        print(f"[FAIL] label 含不安全字符 (仅允许字母/数字/下划线/中文开头, "
              f"后接 字母/数字/下划线/中文/./-): {args.label!r}")
        return 1

    report = {
        "schema_version": EVAL_SCHEMA_VERSION,
        "label": args.label,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "workspace": str(workspace),
        "tools": {
            "score_artifact_judge": _score_judge(workspace),
            "consistency_audit": _score_consistency_audit(workspace),
            "trace_claims": _score_trace_claims(workspace),
            "figqa": _score_figqa(workspace),
            "pdf_qa": _score_pdf_qa(workspace),
        },
        "decision_log": _summarize_decision_log(workspace),
        "artifacts": _inventory_artifacts(workspace),
    }

    out_dir = (Path(args.out_dir) if args.out_dir else RESULTS_DIR).resolve()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{args.label}_{stamp}.json"
    if out_path.resolve().parent != out_dir:
        print(f"[FAIL] 结果文件路径越界: {out_path.resolve()} 不在 {out_dir} 内")
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"score-run [{args.label}] workspace={workspace}")
    for name, tool in report["tools"].items():
        code = tool.get("exit_code")
        line = f"  {name}: status={tool['status']}"
        if code is not None:
            line += f", exit_code={code}"
        if tool["status"] == "error":
            line += f", reason={tool.get('reason', '?')}"
        print(line)
    dl = report["decision_log"]
    print(f"  decision_log: {dl.get('status')}"
          + (f", stages={dl.get('stage_count')}" if dl.get("status") == "ok" else ""))
    print(f"  artifacts: {report['artifacts']['file_count']} 文件, "
          f"{report['artifacts']['total_bytes']} 字节")
    print(f"[OK] 结果已写入 {out_path}")
    return 0


# ============================================================================
# 子命令 3: compare
# ============================================================================

def flatten_metrics(obj, prefix: str = "") -> dict:
    """把评测 JSON 扁平化为 {点路径: 标量}。

    dict 递归展开; list 折叠为 "<list:N>" 标量 (文件清单等长列表不逐项成行,
    长度差异本身就是可对比指标); None/布尔/数字/字符串原样保留。
    """
    flat: dict = {}
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flat.update(flatten_metrics(value, path))
        elif isinstance(value, list):
            flat[path] = f"<list:{len(value)}>"
        else:
            flat[path] = value
    return flat


def _load_result_json(path: Path):
    """读取评测结果 JSON; 返回 (dict, None) 或 (None, 可读错误)。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"无法读取: {exc}"
    if not isinstance(data, dict):
        return None, f"顶层必须是 JSON 对象, 实际: {type(data).__name__}"
    return data, None


def _format_delta(value_a, value_b) -> str:
    """双方均为数值时返回 B-A 的带符号差值, 否则空串。"""
    if isinstance(value_a, bool) or isinstance(value_b, bool):
        return ""
    if isinstance(value_a, (int, float)) and isinstance(value_b, (int, float)):
        delta = value_b - value_a
        if isinstance(value_a, int) and isinstance(value_b, int):
            return f"{delta:+d}"
        return f"{delta:+.2f}"
    return ""


# 表格单元格最大显示宽度 (stdout_tail 等长诊断串截断, 完整内容看结果 JSON)
_CELL_MAX_CHARS = 40


def _display(value) -> str:
    """单元格显示文本: 超长字符串截断加省略号。"""
    text = str(value)
    if len(text) > _CELL_MAX_CHARS:
        return text[:_CELL_MAX_CHARS - 1] + "…"
    return text


def cmd_compare(args) -> int:
    """并排打印两次评测的指标差异表。"""
    paths = [Path(args.run_a), Path(args.run_b)]
    runs = []
    for path in paths:
        if not path.exists():
            print(f"[FAIL] 结果文件不存在: {path}")
            return 1
        data, err = _load_result_json(path)
        if data is None:
            print(f"[FAIL] {path}: {err}")
            return 1
        runs.append(data)
    flat_a = flatten_metrics(runs[0])
    flat_b = flatten_metrics(runs[1])

    metrics = sorted(set(flat_a) | set(flat_b))
    rows = []
    for metric in metrics:
        value_a = flat_a.get(metric, "<缺失>")
        value_b = flat_b.get(metric, "<缺失>")
        rows.append((metric, value_a, value_b, _format_delta(value_a, value_b)))

    name_a, name_b = paths[0].name, paths[1].name
    displays = [(r[0], _display(r[1]), _display(r[2])) for r in rows]
    widths = (max([len("metric")] + [len(d[0]) for d in displays]),
              max([len(name_a)] + [len(d[1]) for d in displays]),
              max([len(name_b)] + [len(d[2]) for d in displays]))
    header = (f"{'metric':<{widths[0]}}  {'A':<{widths[1]}}  {'B':<{widths[2]}}  delta")
    print(header)
    print(f"{'':<{widths[0]}}  {name_a:<{widths[1]}}  {name_b:<{widths[2]}}")
    print("-" * len(header))
    for (metric, value_a, value_b, delta), (_, disp_a, disp_b) in zip(rows, displays):
        print(f"{metric:<{widths[0]}}  {disp_a:<{widths[1]}}  "
              f"{disp_b:<{widths[2]}}  {delta}")
    return 0


# ============================================================================
# CLI
# ============================================================================

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_eval.py",
        description="mathmodel-studio 最小评测 runner (伪 holdout / score-run / compare)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser(
        "build-holdout-index", help="过滤指定年份后镜像案例索引 (源文件不动)")
    p_build.add_argument("--competition", default="huaweibei",
                         help="竞赛名 (默认 huaweibei)")
    p_build.add_argument("--exclude-year", type=int, required=True,
                         help="要剔除的年份 (如 2024)")
    p_build.add_argument("--out", type=Path, required=True,
                         help="镜像输出目录 (写入 <out>/competitions/<comp>/cases/)")
    p_build.add_argument("--repo-root", type=Path, default=None,
                         help="仓库根目录 (默认脚本所在仓库; 供合成 fixture 测试用)")

    p_score = sub.add_parser("score-run", help="采集一个建模工作区的评测指标")
    p_score.add_argument("--workspace", type=Path, required=True,
                         help="建模工作区目录 (含 state/ figures/ paper_workspace/ 等)")
    p_score.add_argument("--label", required=True, help="本次评测标签 (结果文件名前缀)")
    p_score.add_argument("--out-dir", type=Path, default=None,
                         help="结果输出目录 (默认 <repo>/evals/results/)")

    p_cmp = sub.add_parser("compare", help="并排打印两次评测的指标差异表")
    p_cmp.add_argument("run_a", type=Path, help="评测结果 JSON A")
    p_cmp.add_argument("run_b", type=Path, help="评测结果 JSON B")

    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    if args.command == "build-holdout-index":
        return cmd_build_holdout_index(args)
    if args.command == "score-run":
        return cmd_score_run(args)
    return cmd_compare(args)


if __name__ == "__main__":
    sys.exit(main())
