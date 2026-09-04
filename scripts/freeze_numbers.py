# -*- coding: utf-8 -*-
"""数字冻结协议: 把论文中引用的关键数字与其数据源哈希绑定, 源变了就报过期。

配套 references/workspace_protocol.md 的 frozen_numbers 概念: 论文定稿/
送审阶段, 摘要与正文引用的关键数字（总量/提升率/误差等）登记为 claim,
冻结时记录数据源文件的 SHA-256; 之后任何重跑/改数据让源文件哈希漂移,
check 都会把受影响的 claim 标记为 stale 并提醒回填数字。

数据文件: cwd/state/frozen_numbers.json, schema:
    {claim_id: {value, unit, source_file, source_locator, source_sha256,
                frozen_at, frozen_by, status}}
status: frozen=已冻结, stale=源哈希漂移待回填。

子命令:
    freeze   --claim <id> --value <v> --unit <u> --source <file> --locator <json.path>
             计算源文件 SHA-256 后冻结; 重复 claim 需先 unfreeze
    check    遍历全部 claim 重算源哈希, 漂移者置 stale 并中文报告
    unfreeze --claim <id> --reason <文本>   解冻并在 state/freeze_change_log.md 追加行
    list     表格输出当前冻结清单

全部写操作原子落盘（临时文件 + os.replace）; --dry-run 只打印不写。

用法示例:
    python scripts/freeze_numbers.py freeze --claim q2_total_cost \\
        --value 4826.3 --unit 万元 --source results/solve.json --locator data.total_cost
    python scripts/freeze_numbers.py check
    python scripts/freeze_numbers.py unfreeze --claim q2_total_cost --reason "数据源重跑"

退出码:
    0  成功 / check 无过期
    1  check 检出 stale; unfreeze 的 claim 不存在
    2  参数/IO 错误
"""

from __future__ import annotations

import argparse
import datetime as _dt
import getpass
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

STATE_REL = Path("state") / "frozen_numbers.json"
CHANGELOG_REL = Path("state") / "freeze_change_log.md"


def _sha256_file(path: Path) -> str:
    """流式计算文件 SHA-256（大文件友好）。"""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _load(store: Path) -> dict:
    """读冻结清单; 不存在返回空 dict, 损坏则报致命错误。"""
    if not store.exists():
        return {}
    try:
        payload = json.loads(store.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"❌ 冻结清单不可读: {store} ({exc})")
        raise SystemExit(2)
    if not isinstance(payload, dict):
        print(f"❌ 冻结清单结构错误（顶层应为对象）: {store}")
        raise SystemExit(2)
    return payload


def _atomic_write_json(store: Path, payload: dict) -> None:
    """原子写 JSON: 同目录临时文件 + os.replace, 半写不落坏文件。"""
    store.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(store.parent), prefix=store.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp_name, store)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _append_changelog(line: str, dry_run: bool = False) -> None:
    """向 state/freeze_change_log.md 追加一行（原子写整文件）。"""
    log = Path.cwd() / CHANGELOG_REL
    text = log.read_text(encoding="utf-8") if log.exists() else "# 数字冻结变更日志\n"
    new_text = text.rstrip("\n") + "\n" + line + "\n"
    if dry_run:
        print(f"[dry-run] 将追加到 {CHANGELOG_REL}: {line}")
        return
    log.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(log.parent), prefix=log.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        os.replace(tmp_name, log)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def cmd_freeze(args) -> int:
    store = Path.cwd() / STATE_REL
    payload = _load(store)
    if args.claim in payload:
        print(f"❌ claim '{args.claim}' 已冻结（状态 {payload[args.claim]['status']}）, "
              f"如需更新请先 unfreeze")
        return 2
    source = Path(args.source)
    if not source.is_file():
        print(f"❌ 数据源文件不存在: {source}")
        return 2
    record = {
        "value": args.value,
        "unit": args.unit,
        "source_file": source.as_posix(),
        "source_locator": args.locator,
        "source_sha256": _sha256_file(source),
        "frozen_at": _now(),
        "frozen_by": getpass.getuser(),
        "status": "frozen",
    }
    if args.dry_run:
        print(f"[dry-run] 将冻结 '{args.claim}': {json.dumps(record, ensure_ascii=False)}")
        return 0
    payload[args.claim] = record
    _atomic_write_json(store, payload)
    print(f"✅ 已冻结 '{args.claim}' = {args.value} {args.unit} "
          f"（源 {record['source_file']} @ {record['source_sha256'][:12]}…）")
    return 0


def cmd_check(args) -> int:
    store = Path.cwd() / STATE_REL
    payload = _load(store)
    if not payload:
        print("冻结清单为空, 无需检查。")
        return 0
    stale: list[str] = []
    for claim_id, record in payload.items():
        source = Path(record.get("source_file", ""))
        if not source.is_file():
            record["status"] = "stale"
            stale.append(claim_id)
            print(f"❌ [{claim_id}] 数据源缺失: {source}")
            continue
        current = _sha256_file(source)
        if current != record.get("source_sha256"):
            record["status"] = "stale"
            stale.append(claim_id)
            print(
                f"❌ [{claim_id}] 数字过期: 源文件已变化 "
                f"（冻结时 {str(record.get('source_sha256'))[:12]}… -> 现在 {current[:12]}…）, "
                f"数值 {record.get('value')} {record.get('unit')} 需回填或重新冻结"
            )
        else:
            record["status"] = "frozen"
            print(f"✅ [{claim_id}] 源哈希一致, {record.get('value')} {record.get('unit')} 有效")
    if stale and not args.dry_run:
        _atomic_write_json(store, payload)  # 把 stale 状态落盘
    if stale:
        print(f"\n共 {len(stale)} 个数字过期: {', '.join(stale)}")
        return 1
    print(f"\n全部 {len(payload)} 个冻结数字均有效。")
    return 0


def cmd_unfreeze(args) -> int:
    store = Path.cwd() / STATE_REL
    payload = _load(store)
    record = payload.get(args.claim)
    if record is None:
        print(f"❌ claim '{args.claim}' 不在冻结清单中")
        return 1
    del payload[args.claim]
    line = (
        f"| {_now()} | {getpass.getuser()} | unfreeze | {args.claim} | "
        f"{record.get('value')} {record.get('unit')} | {args.reason} |"
    )
    if args.dry_run:
        print(f"[dry-run] 将删除 '{args.claim}' 并追加变更日志")
        _append_changelog(line, dry_run=True)
        return 0
    _atomic_write_json(store, payload)
    _append_changelog(line)
    print(f"✅ 已解冻 '{args.claim}'（原因: {args.reason}）, 变更已记录到 {CHANGELOG_REL}")
    return 0


def cmd_list(args) -> int:
    payload = _load(Path.cwd() / STATE_REL)
    if not payload:
        print("冻结清单为空。")
        return 0
    headers = ("claim", "数值", "单位", "状态", "数据源", "冻结时间")
    rows = [
        (
            claim_id,
            str(record.get("value")),
            str(record.get("unit")),
            str(record.get("status")),
            str(record.get("source_file")),
            str(record.get("frozen_at", ""))[:19],
        )
        for claim_id, record in sorted(payload.items())
    ]
    widths = [
        max(len(headers[i]), *(len(r[i]) for r in rows)) for i in range(len(headers))
    ]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt.format(*row))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="数字冻结协议: 关键数字与数据源哈希绑定, 源漂移即报 stale"
    )
    parser.add_argument("--dry-run", action="store_true", help="只打印将发生的变化, 不写文件")
    sub = parser.add_subparsers(dest="command", required=True)

    p_freeze = sub.add_parser("freeze", help="冻结一个数字 claim")
    p_freeze.add_argument("--claim", required=True, help="数字唯一标识, 如 q2_total_cost")
    p_freeze.add_argument("--value", required=True, help="数字值")
    p_freeze.add_argument("--unit", required=True, help="单位, 如 万元 / %")
    p_freeze.add_argument("--source", required=True, help="数据源文件路径（相对 cwd）")
    p_freeze.add_argument("--locator", required=True, help="源内定位符, 如 data.total_cost")
    p_freeze.set_defaults(func=cmd_freeze)

    p_check = sub.add_parser("check", help="重算全部源哈希, 漂移者置 stale")
    p_check.set_defaults(func=cmd_check)

    p_unfreeze = sub.add_parser("unfreeze", help="解冻 claim 并写变更日志")
    p_unfreeze.add_argument("--claim", required=True, help="要解冻的数字标识")
    p_unfreeze.add_argument("--reason", required=True, help="解冻原因（写入变更日志）")
    p_unfreeze.set_defaults(func=cmd_unfreeze)

    p_list = sub.add_parser("list", help="表格输出冻结清单")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
