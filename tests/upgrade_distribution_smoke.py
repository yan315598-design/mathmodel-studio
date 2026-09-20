"""Copy the real runtime selection to a new local directory and exercise it."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from package_dist import collect_plan, missing_required, scan_files, SELECT_TIER_RUNTIME


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    plan = collect_plan(ROOT)
    included = [item for item in plan["included"] if item.kind == SELECT_TIER_RUNTIME]
    assert not missing_required(included)
    scan = scan_files([(item.rel, ROOT / item.rel) for item in included])
    assert not scan["hard"]
    snapshot = output / "runtime"
    for item in included:
        target = snapshot / item.rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / item.rel, target)
    for name in ("SKILL.md", "AGENTS.md", "templates/figures/scripts/figure_composition.py",
                 "templates/figures/scripts/render_task_examples.py", "scripts/experiment_protocol_v2.py"):
        assert (snapshot / name).is_file()
    checks = []
    commands = [
        [sys.executable, "templates/figures/scripts/render_modeling_pack.py", "--list"],
        [sys.executable, "scripts/compare_experiments.py", "--help"],
        [sys.executable, "scripts/build_result_gallery.py", "--help"],
        [sys.executable, "scripts/inspect_assets.py", "--help"],
        [sys.executable, "templates/figures/scripts/render_task_examples.py", "--cases", "D",
         "--output", str(output / "sample")],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=snapshot, text=True, encoding="utf-8", capture_output=True)
        checks.append({"command": command[1:], "returncode": result.returncode,
                       "stdout": result.stdout, "stderr": result.stderr})
    report = {"kind": "local no-dev selection snapshot, not published",
              "runtime_files": len(included), "runtime_bytes": sum(item.size for item in included),
              "entry_bytes": {name: (snapshot / name).stat().st_size for name in ("SKILL.md", "AGENTS.md")},
              "hard_scan_hits": len(scan["hard"]), "soft_scan_hits": len(scan["soft"]),
              "scan_boundary": "text only; soft findings require human review",
              "checks": checks, "files": [item.rel for item in included]}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    failures = sum(c["returncode"] != 0 for c in checks)
    print(f"distribution: {len(checks)-failures} passed, {failures} failed")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
