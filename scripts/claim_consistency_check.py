"""
claim_consistency_check.py — 结论-结果一致性核验 (候选版)

用途: 防止"有限证据写成更强结论" (2026-09-07 诊断 P0: 结果未收敛写成收敛、
无界写成全局最优、跨口径误差写成同口径提升)。本脚本只做可机器判定的部分,
输出分三级:

- fail: 文字与结果文件直接矛盾 (如 draft 声称收敛但结果 converged=false)
- warn: 强结论词缺少对应证据字段 (需人工核对, 不拦截)
- info: 口径清单 (列出所有区间/置信表述, 供人工核对分母与水平)

用法:
    python scripts/claim_consistency_check.py --draft paper_workspace/sections --results results/
    python scripts/claim_consistency_check.py --draft abstract.md --results results/ --strict

退出码: 默认 0 (报告模式); --strict 时存在 fail 级发现返回 1。
本脚本不判断结论是否正确, 只判断文字是否与结果文件状态冲突; 通过不等于结论成立。
"""

import argparse
import json
import re
import sys
from pathlib import Path

# 收敛类强表述 (排除否定: 未收敛/不收敛/收敛域等)
CONVERGENCE_CLAIM = re.compile(r"(?<![未不无极])收敛(?!域|半径|速度)(?:性)?(?:通过|良好|保证|得到|达到|验证)?")
CONVERGENCE_NEGATION = re.compile(r"(未|不|无法|未能)收敛")
# 最优类强表述
OPTIMAL_CLAIM = re.compile(r"全局最优|最优性(?:保证|证明)|证明[^。]{0,6}最优|数学上最优|理论最优")
# 带数值的提升/改进类表述
IMPROVEMENT_CLAIM = re.compile(r"(提升|改进|提高|降低|减少|优化)[^。]{0,15}?\d+(?:\.\d+)?\s*%")
# 区间/置信/覆盖率口径 (info 级清单)
INTERVAL_CLAIM = re.compile(r"\d+(?:\.\d+)?\s*%[^。]{0,12}(?:区间|置信|覆盖率)|(?:区间|置信|覆盖率)[^。]{0,12}\d+(?:\.\d+)?\s*%")

# 结果文件中的证据键 (小写匹配)
BOUND_EVIDENCE_KEYS = ("gap", "bound", "certificate", "proof", "lower_bound", "upper_bound", "dual")
BASELINE_EVIDENCE_KEYS = ("baseline", "对照", "base_", "greedy")
OPTIMAL_STATUS_VALUES = ("optimal", "optimal_inaccurate")

# 数字可追溯抽查 (候选版): 摘要/正文中的关键数字必须能在结果文件中找到同值
# 只抽查"像结果"的数字: 小数, 或 ≥4 位整数; 跳过常见结构常数与年份
NUMBER_PATTERN = re.compile(r"(?<![\w.\-])(-?\d+\.\d+|-?\d{4,})(?![\w.%])")
NUMBER_SKIP = {1024, 2048, 4096, 8192, 1000, 10000}
NUMBER_MAX_WARN = 15

# 同对象两数值矛盾 (候选版): 同一对象+同一指标的表述在文中出现两个不同值 (F2 案例型)
# 上下文 = 数字前的 2-15 个连续汉字/词干; 只查小数或 ≥3 位整数, 降低噪声
CONTEXT_NUMBER_PATTERN = re.compile(
    r"(?P<ctx>[一-鿿\w]{2,15})[\s为是达约到：:，,]*?(?P<num>-?\d+\.\d+|-?\d{3,})(?![\w.%])")
CONTRADICTION_CTX_SKIP = {"图", "表", "公式", "模型", "结果", "方法", "算法", "数据", "样本"}


def _norm_ctx(ctx: str) -> str:
    return re.sub(r"[\s，,。：:为是达约到（）()的与和]", "", ctx)


def _number_traced(token: str, values: list[float]) -> bool:
    """正文数字在结果数值集合中是否可追溯。

    按正文给出的精度做舍入匹配 (正文写 0.99 可舍入命中 0.9896; 写 0.9876 不能命中 0.9896);
    百分数口径互认 (98.96% ↔ 0.9896)。整数要求精确同值。
    """
    try:
        x = float(token)
    except ValueError:
        return True
    nd = len(token.lstrip("-").split(".")[1]) if "." in token else 0
    if nd == 0:
        return any(v == x for v in values)
    rx = round(x, nd)
    for v in values:
        for cand in (v, v * 100.0, v / 100.0):
            if round(cand, nd) == rx:
                return True
    return False


def _iter_json_values(obj, path=""):
    """递归产出 (path, key_lower, value) 供证据键搜索与数值收集。
    dict 产出键值对; list 产出标量元素 (key 形如 [i]); 嵌套结构递归。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield (f"{path}.{k}", str(k).lower(), v)
            yield from _iter_json_values(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                yield from _iter_json_values(v, f"{path}[{i}]")
            else:
                yield (f"{path}[{i}]", f"[{i}]", v)


def _load_results(results_dir: Path):
    """返回 dict: converged_false / converged_seen / evidence_keys / status_values / files_read / numeric_values。"""
    converged_false = []
    converged_seen = False
    evidence_keys = set()
    status_values = set()
    numeric_values = []
    files_read = 0
    for path in sorted(results_dir.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue
        files_read += 1
        for loc, key, value in _iter_json_values(data):
            if key == "converged":
                converged_seen = True
                if value is False:
                    converged_false.append(f"{path.name}:{loc}")
            for ek in BOUND_EVIDENCE_KEYS:
                if ek in key:
                    evidence_keys.add(ek)
            for bk in BASELINE_EVIDENCE_KEYS:
                if bk in key:
                    evidence_keys.add(bk)
            if key == "status" and isinstance(value, str) and value.lower() in OPTIMAL_STATUS_VALUES:
                status_values.add(value.lower())
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric_values.append(float(value))
    return {
        "converged_false": converged_false,
        "converged_seen": converged_seen,
        "evidence_keys": evidence_keys,
        "status_values": status_values,
        "files_read": files_read,
        "numeric_values": numeric_values,
    }


def _iter_drafts(draft_path: Path):
    """产出 (file, lineno, line_text)。支持单文件或目录 (递归 *.md/*.tex)。"""
    files = [draft_path] if draft_path.is_file() else sorted(
        p for p in draft_path.rglob("*") if p.suffix in (".md", ".tex"))
    for path in files:
        try:
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                yield path.name, lineno, line
        except (UnicodeDecodeError, OSError):
            continue


def check_claims(draft_path: Path, results_dir: Path) -> dict:
    res = _load_results(results_dir)
    converged_false = res["converged_false"]
    evidence_keys = res["evidence_keys"]
    status_values = res["status_values"]
    files_read = res["files_read"]

    convergence_claims = []  # (file, line, snippet)
    optimal_claims = []
    improvement_claims = []
    interval_claims = []
    draft_numbers = {}  # value -> (file, line) 首次出现位置
    ctx_numbers = {}  # norm_ctx -> [(value_str, file, line)] 同对象两数值检测
    for fname, lineno, line in _iter_drafts(draft_path):
        for m in CONVERGENCE_CLAIM.finditer(line):
            if CONVERGENCE_NEGATION.search(line[max(0, m.start() - 4):m.end() + 1]):
                continue
            convergence_claims.append((fname, lineno, line.strip()[:60]))
            break
        if OPTIMAL_CLAIM.search(line):
            optimal_claims.append((fname, lineno, line.strip()[:60]))
        if IMPROVEMENT_CLAIM.search(line):
            improvement_claims.append((fname, lineno, line.strip()[:60]))
        for m in INTERVAL_CLAIM.finditer(line):
            interval_claims.append((fname, lineno, m.group(0)[:60]))
        for m in NUMBER_PATTERN.finditer(line):
            raw = m.group(1)
            try:
                value = float(raw)
            except ValueError:
                continue
            if value.is_integer() and (int(abs(value)) in NUMBER_SKIP or 1900 <= value <= 2100):
                continue
            draft_numbers.setdefault(raw, (fname, lineno))
        for m in CONTEXT_NUMBER_PATTERN.finditer(line):
            ctx = _norm_ctx(m.group("ctx"))
            if len(ctx) < 2 or ctx in CONTRADICTION_CTX_SKIP:
                continue
            ctx_numbers.setdefault(ctx, []).append((m.group("num"), fname, lineno))

    findings = []
    # 规则 1: 收敛矛盾 (fail) / 缺判据 (warn)
    if convergence_claims and converged_false:
        findings.append({
            "level": "fail",
            "rule": "convergence_contradiction",
            "detail": f"正文存在收敛类表述 {len(convergence_claims)} 处, 但结果文件含 converged=false: "
                      f"{', '.join(converged_false[:5])}. 首处文字: "
                      f"{convergence_claims[0][0]}:{convergence_claims[0][1]}",
        })
    elif convergence_claims and files_read and not res["converged_seen"]:
        findings.append({
            "level": "warn",
            "rule": "convergence_unsupported",
            "detail": f"正文存在收敛类表述 {len(convergence_claims)} 处, 但结果文件未见收敛判据字段 "
                      f"(converged)。需预先判据 + 实际轨迹, 或改写为'预算内返回历史最好方案'。",
        })

    # 规则 2: 最优表述缺界/证书 (warn)
    has_bound = bool(evidence_keys & set(BOUND_EVIDENCE_KEYS)) or bool(status_values)
    if optimal_claims and not has_bound:
        findings.append({
            "level": "warn",
            "rule": "optimal_without_bound",
            "detail": f"正文存在全局最优类表述 {len(optimal_claims)} 处, 但结果文件未见 "
                      f"gap/bound/certificate 或 status=optimal 证据。首处: "
                      f"{optimal_claims[0][0]}:{optimal_claims[0][1]}",
        })

    # 规则 3: 带数值提升缺基线 (warn)
    has_baseline = bool(evidence_keys & set(BASELINE_EVIDENCE_KEYS))
    if improvement_claims and not has_baseline:
        findings.append({
            "level": "warn",
            "rule": "improvement_without_baseline",
            "detail": f"正文存在带数值的提升/改进表述 {len(improvement_claims)} 处, 但结果文件未见 "
                      f"baseline/对照字段。提升必须与同口径基线比较。首处: "
                      f"{improvement_claims[0][0]}:{improvement_claims[0][1]}",
        })

    # 规则 4: 区间口径清单 (info)
    if interval_claims:
        findings.append({
            "level": "info",
            "rule": "interval_inventory",
            "detail": f"共 {len(interval_claims)} 处区间/置信/覆盖率表述, 请人工核对水平、分母与"
                      f"代码分位数一致 (诊断案例: 正文 90% 区间 vs 代码 10%/90% 分位): "
                      + "; ".join(f"{f}:{l} {s}" for f, l, s in interval_claims[:8]),
        })

    # 规则 5: 数字可追溯 (warn) — 正文数字须在结果文件中按精度舍入匹配 (百分数口径互认)
    if files_read and draft_numbers:
        values = res["numeric_values"]
        untraced = [(tok, loc) for tok, loc in draft_numbers.items()
                    if not _number_traced(tok, values)]
        if untraced:
            sample = "; ".join(f"{tok} ({f}:{l})" for tok, (f, l) in untraced[:NUMBER_MAX_WARN])
            findings.append({
                "level": "warn",
                "rule": "untraceable_number",
                "detail": f"正文 {len(untraced)} 个数字在结果文件中找不到同值 (按正文精度舍入匹配): "
                          f"{sample}{' …' if len(untraced) > NUMBER_MAX_WARN else ''}。"
                          "关键数字必须来自结果文件; 若为估算/常量请在正文说明口径。",
            })

    # 规则 6: 同对象两数值矛盾 (warn) — 同一上下文键出现两个不同数值 (F2 案例型)
    contradictions = []
    for ctx, entries in ctx_numbers.items():
        distinct = {tok for tok, _, _ in entries}
        if len(distinct) > 1:
            locs = "; ".join(f"{tok}({f}:{l})" for tok, f, l in entries[:4])
            contradictions.append(f"{ctx}: {locs}")
    if contradictions:
        findings.append({
            "level": "warn",
            "rule": "contradicting_values",
            "detail": f"同一对象的指标出现多个不同值 {len(contradictions)} 组: "
                      + " | ".join(contradictions[:8])
                      + "。须统一口径或说明差异原因。",
        })

    n_fail = sum(1 for f in findings if f["level"] == "fail")
    n_warn = sum(1 for f in findings if f["level"] == "warn")
    return {
        "findings": findings,
        "n_fail": n_fail,
        "n_warn": n_warn,
        "n_info": sum(1 for f in findings if f["level"] == "info"),
        "results_files_read": files_read,
        "note": "本脚本只检查文字与结果文件状态是否冲突; 通过不代表结论成立。",
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except AttributeError:
        pass
    parser = argparse.ArgumentParser(description="结论-结果一致性核验 (候选版)")
    parser.add_argument("--draft", required=True, help="正文/摘要 md 或 tex 文件, 或目录")
    parser.add_argument("--results", required=True, help="结果目录 (递归读取 *.json)")
    parser.add_argument("--strict", action="store_true", help="存在 fail 级发现时 exit 1")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = parser.parse_args()

    draft_path, results_dir = Path(args.draft), Path(args.results)
    if not draft_path.exists():
        print(f"[FAIL] draft 不存在: {draft_path}")
        return 1
    if not results_dir.exists():
        print(f"[FAIL] results 不存在: {results_dir}")
        return 1

    report = check_claims(draft_path, results_dir)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"结论-结果核验: {report['n_fail']} fail / {report['n_warn']} warn / "
              f"{report['n_info']} info (读取结果文件 {report['results_files_read']} 个)")
        for f in report["findings"]:
            print(f"  [{f['level']}] {f['rule']}: {f['detail']}")
        print(f"  说明: {report['note']}")
    if args.strict and report["n_fail"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
