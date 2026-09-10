"""
run_rubric_regression.py — 已知坏产物的规则回归 (候选版)

对 evals/rubric_regression/cases.json:
- type=scriptable: 落盘 fixture 后实际运行 scripts/claim_consistency_check.py 的
  check_claims, 断言出现期望 level/rule 的发现。
- type=static_rule: 核验规则文件仍包含覆盖该类问题的关键表述 (防规则被删退化)。
- type=static_rule_absent: 核验规则文件不再含配额类表述。
- type=manual: 只登记列出; 行为验证依赖留出题新旧对照, 本脚本不宣称。

退出码: 全部通过 0; 任一失败 1。
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from claim_consistency_check import check_claims

CASES_PATH = Path(__file__).resolve().parent / "cases.json"


def run_scriptable(case: dict) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        draft = root / "draft"
        results = root / "results"
        draft.mkdir()
        results.mkdir()
        (draft / "case.md").write_text(case["draft_text"], encoding="utf-8")
        (results / "case.json").write_text(
            json.dumps(case["results_json"], ensure_ascii=False), encoding="utf-8")
        report = check_claims(draft, results)
    expect = case["expect"]
    hit = any(f["level"] == expect["level"] and f["rule"] == expect["rule"]
              for f in report["findings"])
    if hit:
        return True, f"命中 {expect['level']}/{expect['rule']}"
    return False, (f"期望 {expect['level']}/{expect['rule']} 未命中; "
                   f"实际 findings: {[(f['level'], f['rule']) for f in report['findings']]}")


def run_static_rule(case: dict) -> tuple[bool, str]:
    text = (ROOT / case["rule_file"]).read_text(encoding="utf-8")
    missing = [t for t in case["rule_text_must_contain"] if t not in text]
    if missing:
        return False, f"{case['rule_file']} 缺少关键表述: {missing}"
    return True, "规则文本在位"


def run_static_rule_absent(case: dict) -> tuple[bool, str]:
    text = (ROOT / case["rule_file"]).read_text(encoding="utf-8")
    present = [t for t in case["rule_text_must_not_contain"] if t in text]
    if present:
        return False, f"{case['rule_file']} 仍含配额表述: {present}"
    return True, "配额表述已移除"


def run_static_rule_absent_multi(case: dict) -> tuple[bool, str]:
    """多文件扫描版本: 任一文件含禁用配额表述即失败。"""
    hits = []
    for rel in case["rule_files"]:
        path = ROOT / rel
        if not path.exists():
            hits.append(f"{rel}: 文件不存在")
            continue
        text = path.read_text(encoding="utf-8")
        present = [t for t in case["rule_text_must_not_contain"] if t in text]
        if present:
            hits.append(f"{rel}: {present}")
    if hits:
        return False, "配额回潮: " + "; ".join(hits)
    return True, f"{len(case['rule_files'])} 个文件无配额表述"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except AttributeError:
        pass
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    failures = 0
    manual = 0
    for case in cases:
        ctype = case["type"]
        if ctype == "scriptable":
            ok, msg = run_scriptable(case)
        elif ctype == "static_rule":
            ok, msg = run_static_rule(case)
        elif ctype == "static_rule_absent":
            ok, msg = run_static_rule_absent(case)
        elif ctype == "static_rule_absent_multi":
            ok, msg = run_static_rule_absent_multi(case)
        else:
            manual += 1
            print(f"  [manual] {case['id']}: 登记在案, 行为验证走留出对照 — {case['expect']}")
            continue
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"  [{status}] {case['id']}: {msg}")
    print(f"rubric 回归: {len(cases) - manual - failures}/{len(cases) - manual} 通过 "
          f"(另有 {manual} 条 manual 登记)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
