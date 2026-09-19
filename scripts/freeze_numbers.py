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
             计算源文件 SHA-256 后冻结; 重复 claim 需先 unfreeze。
             落盘前对 locator 做一次试解析 (C5): 点路径 a.b.c / 顶层字段名 /
             数组下标 a.b[0][1] 三类形态尝试在 json 源中取值并与 --value 比对,
             对不上只 warn 一行请人工确认, 不阻断 (描述型定位符含中文/空格不警告;
             非 json 源第一版暂不支持自动解析, 同样不警告)
    check    遍历全部 claim 重算源哈希, 漂移者置 stale 并中文报告
    verify   对全部冻结条目跑同一 locator 试解析, 输出四分类统计与明细:
             可解析且一致 (✅) / 可解析不一致 (❌) / 描述型 (ℹ️, 不视为问题) /
             解析失败 (⚠️); 纯诊断恒返回 0, 不改任何记录
    unfreeze --claim <id> --reason <文本>   解冻并在 state/freeze_change_log.md 追加行
    list     表格输出当前冻结清单

全部写操作原子落盘（临时文件 + os.replace）; --dry-run 只打印不写。

用法示例:
    python scripts/freeze_numbers.py freeze --claim q2_total_cost \\
        --value 4826.3 --unit 万元 --source results/solve.json --locator data.total_cost
    python scripts/freeze_numbers.py check
    python scripts/freeze_numbers.py verify
    python scripts/freeze_numbers.py unfreeze --claim q2_total_cost --reason "数据源重跑"

退出码:
    0  成功 / check 无过期 (verify 恒 0, freeze 的 locator warn 不改变退出码)
    1  check 检出 stale; unfreeze 的 claim 不存在
    2  参数/IO 错误
"""

from __future__ import annotations

import argparse
import datetime as _dt
import getpass
import hashlib
import json
import math
import os
import re
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


# --------------------------------------------------------------- locator 试解析 (C5)
# 描述型定位符: 含 CJK 字符或空白 (如 "第 1800 s 中心温度 (°C)"), 视为纯描述, 不做机器解析
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
# locator 四分类
LOCATOR_CATEGORIES = ("ok", "mismatch", "descriptive", "fail")


def _locator_tokens(locator: str):
    """点路径 + 数组下标语法的 tokenize: a.b[0][1].c -> [('k','a'), ('k','b'), ('i',0), ('i',1), ('k','c')]。

    纯点路径 (a.b.c) 与顶层字段名 (a) 都是该语法的特例。语法不合法 (空串/空段 a..b /
    悬空点 a. / 前置下标 [0].a) 返回 None。
    """
    tokens: list = []
    i, n = 0, len(locator)
    expect_key = True  # 段首: 期待键名, 不期待 '.' 或 '['
    while i < n:
        ch = locator[i]
        if ch == ".":
            if expect_key:
                return None
            expect_key = True
            i += 1
        elif ch == "[":
            m = re.match(r"\[(\d+)\]", locator[i:])
            if not m or expect_key:
                return None
            tokens.append(("i", int(m.group(1))))
            i += m.end()
        else:
            m = re.match(r"[^.\[\]]+", locator[i:])
            if not m or not expect_key:
                return None
            tokens.append(("k", m.group(0)))
            expect_key = False
            i += m.end()
    if expect_key or not tokens:
        return None
    return tokens


def _resolve_locator(data, locator: str):
    """在已加载的 json 对象里按定位符取值。Returns (value, None) 或 (None, 中文原因)。"""
    tokens = _locator_tokens(locator)
    if tokens is None:
        return None, "定位符语法不合法"
    node = data
    for typ, tok in tokens:
        if typ == "k":
            if not isinstance(node, dict) or tok not in node:
                return None, f"键 '{tok}' 不存在"
            node = node[tok]
        else:
            if not isinstance(node, list) or tok >= len(node):
                return None, f"下标 [{tok}] 越界或目标不是数组"
            node = node[tok]
    return node, None


def _is_descriptive_locator(locator: str) -> bool:
    """描述型定位符: 空串 / 含 CJK 字符 / 含任意空白字符。"""
    if not locator or not locator.strip():
        return True
    return bool(_CJK_RE.search(locator)) or any(ch.isspace() for ch in locator)


def _sig_digits(text: str):
    """数值字符串的有效位数 ("57.5406" -> 6, "2.30e-13" -> 3, "0.00025" -> 2); 非数值返回 None。"""
    m = re.match(r"^[+-]?(\d*\.?\d+)(?:[eE][+-]?\d+)?$", text.strip())
    if not m:
        return None
    digits = m.group(1).replace(".", "").lstrip("0")
    return len(digits) or 1


def _values_consistent(parsed, recorded) -> bool:
    """源中解析值与冻结记录值是否一致。

    三种一致口径 (任一满足即可):
    1. 字符串等值 (非数值字段, 如站点名);
    2. 数值相对误差 < 1e-9;
    3. 源值按记录值有效位数舍入后相等 —— 论文数字是显示精度的舍入值
       (源 57.540555… vs 冻结 57.5406 属一致)。
    """
    rs = str(recorded).strip()
    if isinstance(parsed, str) and parsed.strip() == rs:
        return True
    if isinstance(parsed, bool) or not isinstance(parsed, (int, float)):
        return False
    try:
        rv = float(rs)
    except ValueError:
        return False
    sv = float(parsed)
    if math.isclose(sv, rv, rel_tol=1e-9, abs_tol=0.0):
        return True
    sig = _sig_digits(rs)
    if sig is not None:
        try:
            rounded = float(f"{sv:.{sig}g}")
        except (ValueError, OverflowError):
            rounded = None
        if rounded is not None and math.isclose(rounded, rv, rel_tol=1e-12, abs_tol=1e-15):
            return True
    return False


def _locator_check(source: Path, locator, recorded):
    """单条冻结记录的 locator 试解析 (第一版仅支持 json 源, 其余类型归描述型不硬解)。

    Returns (category, detail):
      ok          可解析且与记录值一致 (detail 为取到的值)
      mismatch    可解析但取值对不上, 如指向 dict/list 容器或数值不一致
      descriptive 描述型定位符 / 非 json 源暂不支持自动解析 (不视为问题)
      fail        解析失败: 语法不合法 / 键下标不存在 / 源缺失或不可读
    """
    locator = "" if locator is None else str(locator)
    if _is_descriptive_locator(locator):
        return "descriptive", "描述型定位符 (含中文/空格), 不做机器解析"
    if source.suffix.lower() != ".json":
        suffix = source.suffix if source.suffix else "(无后缀)"
        return "descriptive", f"源类型 {suffix} 暂不支持自动解析 (第一版仅 json), 按描述型统计"
    try:
        with source.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return "fail", f"源文件缺失: {source.as_posix()}"
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return "fail", f"源不是可读 JSON: {exc}"
    parsed, err = _resolve_locator(data, locator)
    if err is not None:
        return "fail", f"路径 '{locator}' 解析失败: {err}"
    if _values_consistent(parsed, recorded):
        return "ok", f"取值 {parsed!r}"
    if isinstance(parsed, (dict, list)):
        kind = "dict" if isinstance(parsed, dict) else "list"
        return "mismatch", f"定位符指向 {kind} 容器而非叶子字段, 须写到具体数值键"
    return "mismatch", f"取值 {parsed!r} 与冻结值 {recorded!r} 不一致"


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
    # locator 试解析 (C5): 对不上只 warn 请人工确认, 不阻断 (描述型/非 json 源不警告)
    category, detail = _locator_check(source, args.locator, args.value)
    if category in ("mismatch", "fail"):
        print(f"[locator] 未能在源中解析到与值一致的字段（{detail}）— "
              f"描述型定位符不在此列；请人工确认 locator 可追溯后再定稿。")
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


def cmd_verify(args) -> int:
    """对全部冻结条目跑 locator 试解析, 四分类统计 + 明细。纯诊断: 恒返回 0, 不改任何记录。"""
    payload = _load(Path.cwd() / STATE_REL)
    if not payload:
        print("冻结清单为空, 无可核验条目。")
        return 0
    buckets: dict = {cat: [] for cat in LOCATOR_CATEGORIES}
    for claim_id, record in sorted(payload.items()):
        source = Path(str(record.get("source_file", "")))
        category, detail = _locator_check(
            source, record.get("source_locator"), record.get("value")
        )
        buckets[category].append(
            (claim_id, str(record.get("source_file", "")),
             str(record.get("source_locator", "")), detail)
        )
    titles = {
        "ok": "可解析且一致",
        "mismatch": "可解析不一致 (❌)",
        "descriptive": "描述型 / 暂不支持自动解析",
        "fail": "解析失败 (⚠️)",
    }
    marks = {"ok": "✅", "mismatch": "❌", "descriptive": "ℹ️", "fail": "⚠️"}
    for cat in LOCATOR_CATEGORIES:
        if not buckets[cat]:
            continue
        print(f"\n[{titles[cat]}] {len(buckets[cat])} 条")
        for claim_id, src, loc, detail in buckets[cat]:
            line = f"  {marks[cat]} [{claim_id}] {src} @ {loc}"
            if cat != "ok":
                line += f" — {detail}"
            print(line)
    print(
        f"\n定位符核验汇总: 可解析且一致 {len(buckets['ok'])} / "
        f"可解析不一致 {len(buckets['mismatch'])} (❌) / "
        f"描述型 {len(buckets['descriptive'])} / "
        f"解析失败 {len(buckets['fail'])} (⚠️) — 共 {len(payload)} 条; "
        "描述型不视为问题, ❌/⚠️ 需人工修 locator 或补结果字段"
    )
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

    p_verify = sub.add_parser(
        "verify",
        help="对全部冻结条目试解析 locator, 输出四分类统计与明细 (纯诊断, 不改记录)",
    )
    p_verify.set_defaults(func=cmd_verify)

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
