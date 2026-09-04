# -*- coding: utf-8 -*-
"""运行清单与哈希链: 记录每次关键运行的可验证证据, 事后可查漂移。

概念: 论文流水线里每个关键运行（求解/出图/统计）追加一行 JSON 记录到
cwd/results/run_manifest.jsonl（append-only）, 内容含:
    脚本路径 + 脚本 SHA-256 / 命令行 / 退出码 / 输入文件哈希 / 输出文件哈希 / 时间戳
每条记录带双重锚:
    - prev_sha256: 指向上一行原始文本的 SHA-256, 形成链式哈希——删改任何
      有后继的行都会断链
    - self_sha256: 对本记录（不含 self_sha256 字段）规范化 JSON 的 SHA-256
      ——尾行（无后继）被篡改也会被逐行重算发现
record 为读-改-写整体替换, 由锁文件串行保护——**record 串行执行, 勿并发**。

子命令:
    record  --script <path> --cmd "<命令>" --exit <code>
            [--inputs f1,f2] [--outputs o1,o2]
            自动计算脚本/输入/输出哈希后追加一行。
            声明的 script/inputs/outputs 任一不存在 → 报错退出 2（不登记）。
    verify  重算所有记录的脚本/输入/输出哈希 + 逐行 self_sha256 + 链式
            prev_sha256 双重校验; 记录里的 sha256:null 一律视为
            "记录含缺失文件"错误。任何漂移/断链/篡改中文报告并退出码 1
    report  人类可读摘要（记录数/时间范围/脚本/退出码分布）

自包含示例:
    python scripts/run_manifest.py record --script code/solve.py \\
        --cmd "python code/solve.py --cfg base.json" --exit 0 \\
        --inputs data/raw.csv,code/solve.py --outputs results/solve.json
    python scripts/run_manifest.py verify
    python scripts/run_manifest.py report

    # 一条龙自测（临时目录内 record→verify→篡改→verify 检出）:
    python scripts/run_manifest.py --self-test

退出码:
    0  成功 / verify 无漂移
    1  verify 发现哈希漂移、链断裂或记录篡改
    2  参数/IO 错误（含声明文件不存在）
    3  record 并发冲突（锁文件被另一进程持有）
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

MANIFEST_REL = Path("results") / "run_manifest.jsonl"


def _sha256_file(path: Path) -> str | None:
    """文件 SHA-256; 文件不存在返回 None（记录缺失状态而非报错）。"""
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _record_self_hash(record: dict) -> str:
    """记录的自哈希: 对该记录（去掉 self_sha256 字段）的规范化 JSON 求 SHA-256。

    规范化 = json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    与写入时字段顺序无关, verify 端可稳定重算。
    """
    payload = {k: v for k, v in record.items() if k != "self_sha256"}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    return _sha256_text(canonical)


def _now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _parse_file_list(value: str | None) -> list[str]:
    """逗号分隔的文件列表 -> 去空格后的列表。"""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _manifest_path(base: Path) -> Path:
    return base / MANIFEST_REL


def _read_records(base: Path) -> list[tuple[str, dict]]:
    """读全部记录行, 返回 [(原始行文本, 解析对象)]; 空文件返回空列表。"""
    manifest = _manifest_path(base)
    if not manifest.exists():
        return []
    records: list[tuple[str, dict]] = []
    for line_no, raw in enumerate(
        manifest.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw.strip():
            continue
        try:
            records.append((raw, json.loads(raw)))
        except json.JSONDecodeError as exc:
            print(f"❌ 第 {line_no} 行不是合法 JSON（疑似被篡改）: {exc}")
            raise SystemExit(1)
    return records


def _append_record(base: Path, record: dict) -> None:
    """原子性追加一行（锁保护读-改-写 -> 临时文件整体替换）。

    record 串行执行: 靠 manifest 旁 .run_manifest.lock（O_CREAT|O_EXCL 独占）
    防并发, 冲突时 SystemExit(3); finally 释放锁。
    """
    manifest = _manifest_path(base)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    lock_path = manifest.parent / ".run_manifest.lock"
    try:
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print("❌ 另一个 record 正在进行（锁文件 .run_manifest.lock 被持有）。"
              "record 串行执行, 勿并发; 若确认无并发, 删除该锁文件后重试。")
        raise SystemExit(3)
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines() if manifest.exists() else []
        lines = [ln for ln in lines if ln.strip()]
        record["prev_sha256"] = _sha256_text(lines[-1]) if lines else None
        record["self_sha256"] = _record_self_hash(record)
        lines.append(json.dumps(record, ensure_ascii=False))
        fd, tmp_name = tempfile.mkstemp(
            dir=str(manifest.parent), prefix=manifest.name + ".", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            os.replace(tmp_name, manifest)
        except BaseException:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise
    finally:
        os.close(lock_fd)
        try:
            os.unlink(lock_path)
        except OSError:
            # 记录已写入, 锁残留只影响下一次 record (会得到明确的 exit 3 提示)
            pass


def _file_entries(base: Path, paths: list[str]) -> list[dict]:
    """把文件列表转成 [{path, sha256}]。

    调用方 (cmd_record) 已校验文件存在, 此处 sha256 恒非 null;
    verify 端若读到 null 一律按"记录含缺失文件"报错。
    """
    return [{"path": p, "sha256": _sha256_file(base / p)} for p in paths]


def cmd_record(args, base: Path | None = None) -> int:
    base = base or Path.cwd()
    script = Path(args.script)
    if not (base / script).is_file():
        print(f"❌ 脚本不存在: {script}")
        return 2
    inputs = _parse_file_list(args.inputs)
    outputs = _parse_file_list(args.outputs)
    missing = [p for p in inputs + outputs if not (base / p).is_file()]
    if missing:
        print(f"❌ 声明的输入/输出文件不存在, 拒绝登记: {', '.join(missing)}")
        return 2
    record = {
        "timestamp": _now(),
        "script": script.as_posix(),
        "script_sha256": _sha256_file(base / script),
        "cmd": args.cmd,
        "exit_code": args.exit,
        "inputs": _file_entries(base, inputs),
        "outputs": _file_entries(base, outputs),
    }
    _append_record(base, record)
    print(f"✅ 已记录运行: {record['script']}（exit={record['exit_code']}, "
          f"inputs={len(record['inputs'])}, outputs={len(record['outputs'])}）")
    return 0


def cmd_verify(args, base: Path | None = None) -> int:
    """重算全部哈希并校验链完整性, 漂移/断链中文报告, 返回 0/1。"""
    base = base or Path.cwd()
    records = _read_records(base)
    if not records:
        print("运行清单为空（results/run_manifest.jsonl）, 无可校验内容。")
        return 0
    problems: list[str] = []

    for index, (raw, record) in enumerate(records):
        tag = f"记录#{index + 1}（{record.get('script', '?')}）"

        # 哈希链: 本行 prev_sha256 应等于上一行原始文本哈希
        expected_prev = _sha256_text(records[index - 1][0]) if index else None
        if record.get("prev_sha256") != expected_prev:
            problems.append(
                f"{tag} 哈希链断裂: prev_sha256 与上一行实际哈希不符"
                f"（期望 {str(expected_prev)[:12]}…, 实际 {str(record.get('prev_sha256'))[:12]}…）, "
                f"清单可能被删改"
            )

        # 逐行自哈希: 重算 self_sha256, 尾行篡改也在此检出
        if "self_sha256" not in record:
            problems.append(f"{tag} 缺 self_sha256 字段（旧版清单或被篡改）")
        elif record.get("self_sha256") != _record_self_hash(record):
            problems.append(
                f"{tag} 行自哈希不符: 记录字段被篡改"
                f"（期望 {_record_self_hash(record)[:12]}…, "
                f"实际 {str(record.get('self_sha256'))[:12]}…）"
            )

        # 记录含缺失文件: sha256:null 一律错误（文件当场消失同样由下面漂移检查兜住）
        if record.get("script_sha256") is None:
            problems.append(f"{tag} 记录含缺失文件: script {record.get('script')}")
        else:
            current = _sha256_file(base / record.get("script", ""))
            if current != record.get("script_sha256"):
                frozen = str(record.get("script_sha256"))
                detail = "文件缺失" if current is None else f"{frozen[:12]}… -> {current[:12]}…"
                problems.append(f"{tag} 脚本哈希漂移: {record.get('script')} ({detail})")
        for field, label in (("inputs", "输入"), ("outputs", "输出")):
            for entry in record.get(field, []):
                path, frozen = entry.get("path"), entry.get("sha256")
                if frozen is None:
                    problems.append(f"{tag} 记录含缺失文件: {label} {path}")
                    continue
                current_hash = _sha256_file(base / path)
                if current_hash != frozen:
                    detail = (
                        "文件缺失" if current_hash is None
                        else f"{str(frozen)[:12]}… -> {current_hash[:12]}…"
                    )
                    problems.append(f"{tag} {label}文件漂移: {path} ({detail})")

    if problems:
        print(f"❌ 检出 {len(problems)} 处漂移/断链:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"✅ 共 {len(records)} 条运行记录, 全部哈希与链条校验通过。")
    return 0


def cmd_report(args, base: Path | None = None) -> int:
    base = base or Path.cwd()
    records = _read_records(base)
    if not records:
        print("运行清单为空（results/run_manifest.jsonl）。")
        return 0
    parsed = [r for _raw, r in records]
    scripts = sorted({r.get("script", "?") for r in parsed})
    timestamps = [r.get("timestamp", "") for r in parsed]
    exits: dict[str, int] = {}
    for r in parsed:
        key = str(r.get("exit_code"))
        exits[key] = exits.get(key, 0) + 1
    n_inputs = sum(len(r.get("inputs", [])) for r in parsed)
    n_outputs = sum(len(r.get("outputs", [])) for r in parsed)
    print("=" * 60)
    print(f"运行清单摘要: {_manifest_path(base)}")
    print("=" * 60)
    print(f"记录条数: {len(parsed)}")
    print(f"时间范围: {min(timestamps) or '-'} ~ {max(timestamps) or '-'}")
    print(f"涉及脚本: {len(scripts)} 个")
    for s in scripts:
        print(f"  - {s}")
    print(f"退出码分布: " + ", ".join(f"exit={k} x{v}" for k, v in sorted(exits.items())))
    print(f"输入文件引用: {n_inputs} 次, 输出文件引用: {n_outputs} 次")
    return 0


def _self_test() -> int:
    """临时目录内走一遍 record→verify→篡改→verify 检出 流程。"""
    with tempfile.TemporaryDirectory(prefix="run_manifest_selftest_") as tmp:
        base = Path(tmp)
        (base / "code").mkdir()
        (base / "code" / "solve.py").write_text("print('v1')\n", encoding="utf-8")
        (base / "data.csv").write_text("x,y\n1,2\n", encoding="utf-8")
        (base / "results").mkdir()
        (base / "results" / "out.json").write_text('{"v": 1}', encoding="utf-8")

        def run_once() -> int:
            ns = argparse.Namespace(
                script="code/solve.py", cmd="python code/solve.py",
                exit=0, inputs="data.csv,code/solve.py", outputs="results/out.json",
            )
            return cmd_record(ns, base)

        def verify_once() -> int:
            return cmd_verify(argparse.Namespace(), base)

        ok = run_once() == 0 and verify_once() == 0
        print("[自测] record + verify(初始) 通过" if ok else "[自测] ❌ 初始流程失败")

        # 声明不存在的输入 -> record 拒绝登记 (exit 2), 清单不变
        ns_missing = argparse.Namespace(
            script="code/solve.py", cmd="python code/solve.py --ghost",
            exit=0, inputs="ghost.csv", outputs=None,
        )
        before = _manifest_path(base).read_text(encoding="utf-8")
        reject_missing = cmd_record(ns_missing, base) == 2 and \
            _manifest_path(base).read_text(encoding="utf-8") == before
        print("[自测] 声明缺失文件被拒绝登记(exit 2)" if reject_missing
              else "[自测] ❌ 缺失文件未被拒绝")

        # 篡改脚本内容 -> 脚本哈希漂移应被检出
        (base / "code" / "solve.py").write_text("print('v2')\n", encoding="utf-8")
        script_drift = verify_once() == 1
        print("[自测] 篡改脚本被检出" if script_drift else "[自测] ❌ 脚本篡改未检出")
        (base / "code" / "solve.py").write_text("print('v1')\n", encoding="utf-8")

        # 篡改输出文件 -> 输出哈希漂移应被检出
        (base / "results" / "out.json").write_text('{"v": 999}', encoding="utf-8")
        output_drift = verify_once() == 1
        print("[自测] 篡改输出文件被检出" if output_drift else "[自测] ❌ 输出篡改未检出")
        (base / "results" / "out.json").write_text('{"v": 1}', encoding="utf-8")

        # 再记一条形成链, 然后篡改首行 -> 哈希链断裂 + 逐行自哈希应被检出
        ok2 = run_once() == 0 and verify_once() == 0
        if not ok2:
            print("[自测] ❌ 第二条记录后 verify 失败")
        manifest = _manifest_path(base)
        forged = manifest.read_text(encoding="utf-8").replace(
            "python code/solve.py", "python code/tampered.py", 1
        )
        manifest.write_text(forged, encoding="utf-8")
        chain_broken = verify_once() == 1
        print("[自测] 清单被篡改导致断链被检出" if chain_broken else "[自测] ❌ 断链未检出")

        # 篡改末行 cmd 字段 (尾行无后继, 链式锚失效) -> 逐行自哈希必须检出
        lines = manifest.read_text(encoding="utf-8").splitlines()
        last = json.loads(lines[-1])
        last["cmd"] = "python code/evil.py --steal"
        lines[-1] = json.dumps(last, ensure_ascii=False)
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tail_tampered = verify_once() == 1
        print("[自测] 篡改末行 cmd 字段被逐行自哈希检出" if tail_tampered
              else "[自测] ❌ 末行篡改未检出")

        # 记录含 sha256:null -> verify 报"记录含缺失文件"并 exit 1
        lines = manifest.read_text(encoding="utf-8").splitlines()
        lines = [ln for ln in lines if ln.strip()]
        null_record = {
            "timestamp": _now(),
            "script": "code/solve.py",
            "script_sha256": _sha256_file(base / "code" / "solve.py"),
            "cmd": "python code/solve.py --legacy",
            "exit_code": 0,
            "inputs": [{"path": "ghost.csv", "sha256": None}],
            "outputs": [],
        }
        null_record["prev_sha256"] = _sha256_text(lines[-1])
        null_record["self_sha256"] = _record_self_hash(null_record)
        lines.append(json.dumps(null_record, ensure_ascii=False))
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        null_detected = verify_once() == 1
        print("[自测] sha256:null 记录被 verify 判错" if null_detected
              else "[自测] ❌ null 哈希记录未被判错")
        # 移除该手工行, 清单留在当前状态 (末行篡改用例的状态保留, 不再 verify)
        lines = manifest.read_text(encoding="utf-8").splitlines()
        manifest.write_text("\n".join(l for l in lines if "legacy" not in l) + "\n",
                            encoding="utf-8")

        report_ok = cmd_report(argparse.Namespace(), base) == 0
        passed = (ok and reject_missing and script_drift and output_drift
                  and ok2 and chain_broken and tail_tampered and null_detected
                  and report_ok)
        print("[自测] " + ("全部通过 ✅" if passed else "存在失败 ❌"))
        return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="运行清单与哈希链: 关键运行的命令/退出码/输入输出哈希存证"
    )
    parser.add_argument("--self-test", action="store_true", help="临时目录内全流程自测")
    sub = parser.add_subparsers(dest="command")

    p_record = sub.add_parser("record", help="记录一次运行（自动算哈希追加）")
    p_record.add_argument("--script", required=True, help="脚本路径（相对 cwd）")
    p_record.add_argument("--cmd", required=True, help='完整命令行字符串, 如 "python solve.py"')
    p_record.add_argument("--exit", type=int, required=True, help="退出码")
    p_record.add_argument("--inputs", default=None, help="输入文件, 逗号分隔")
    p_record.add_argument("--outputs", default=None, help="输出文件, 逗号分隔")
    p_record.set_defaults(func=cmd_record)

    p_verify = sub.add_parser("verify", help="重算哈希+校验链, 漂移报错")
    p_verify.set_defaults(func=cmd_verify)

    p_report = sub.add_parser("report", help="人类可读摘要")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    if not args.command:
        parser.error("需要子命令 record/verify/report, 或用 --self-test")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
