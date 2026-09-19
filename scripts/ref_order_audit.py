"""
ref_order_audit.py — 文献编号顺序审计 (GB/T 7714 顺序编码制)

用途: 防止"文献编号与首引顺序不符" (2026 A 题实战: 20 条文献首引即 [20],
§5 建模主体 360 行零引用, decision_log 自评却记通过——评委现场 30 秒就能
验出的失分点)。顺序编码制要求文献按正文首次引用先后编号: 第一处引用必须
是 [1], 之后每个新编号按首次出现依次 +1。本脚本做三类机器检查:

- fail ❌: ① 首引顺序非 1..N 严格递增 (逐条报期望序 vs 实际序);
           ② 文献表 (## 参考文献 节) 与正文引用集合不一致
              (孤立文献 = 定义未引用 / 未定义引用 = 引用未定义)
- warn ⚠️: ③ 一级章 (## 级) 文献引用计数为 0 (建模/求解主章零引用是典型
           弱点; 参考文献/附录章为结构性章节不计入);
           疑似引用但编号超出文献表范围 (也可能是数学区间, 只提示不拦截)

误报防护 (保守口径, 输出中注明):
- 只把 [数字] / [数字,数字…] / [数字-数字] (可混排, 如 [1,3-5]) 且全部
  编号 ∈ 1..N (N = 文献表最大编号) 的方括号组计为引用候选。含 0 的组
  (数学区间 [0,1]) 与超范围的组不计——代价是超出 N 的真引用只进 ⚠️
  疑似清单, 不作 fail;
- 跳过代码围栏 (``` / ~~~, **变长**: ```` 开栏时其中的 ``` 是内容, 不提前
  闭栏)、行内代码 span、数学段 ($$..$$ 跨行跟踪与行内 $..$)——数学区间
  \\in[0,1] 与 LaTeX \\\\[3pt] 类内容不参与匹配;
- 4 位以上数字 (年份 [2019-2020]) 天然不匹配; markdown 链接定义 [1]: 、
  链接 [1](url)、转义 \\[ 与图片 ![](...) 不计。

v3.1.0 口径修复 (与终稿导出同源, 见 scripts/md_source.py):
- **文献表识别**: 终稿导出会给标题加 pandoc 不编号标记, 文献表实际是
  "## 参考文献 {-}"——标题比对前先去掉文末属性块 (此前认不出, 直接误报
  no_reference_section); 同时容忍标题内空格 ("参 考 文 献");
- **旧 \\bibitem 条目**: 真源约定 09_references.md 存 \\bibitem (export 导出时
  才转 [N]), 审计直接在源上跑, 故 \\bibitem{key} / \\bibitem[标签]{key} 行也
  计为文献条目 (按出现顺序自增编号, 与导出的 [N] 编号一致);
- **围栏/标题/行内代码解析**全部改走 md_source (与编号注入、md 卫生 lint 同一
  状态机), 四反引号围栏内的三反引号不再被当成闭栏;
- **--workspace 只审"会被导出"的 md**: 稿件发现走 md_source.discover_ordered_
  sources (NN_*.md 系列优先, 否则 main.md / abstract_draft+sections), 不再
  递归扫 paper_workspace/**/*.md——草稿/notes/README 里的 [N] 不再污染审计。

用法:
    python scripts/ref_order_audit.py --workspace <项目根>       # 按**导出同一套**有序稿件扫描
    python scripts/ref_order_audit.py --files paper.md refs.md  # 直接指定 md 文件 (按给定顺序扫描)
    python scripts/ref_order_audit.py --files ... --json        # 机器可读输出

退出码: 0 = 无 fail; 1 = 存在 fail; 2 = 输入不存在。
通过只代表编号顺序合规, 不评判文献内容与权威性。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 共享 md 源解析 (与 export_final_docx.py 同源): 围栏状态机/标题解析/属性剥离/
# bibitem 识别/有序稿件发现——审计口径必须与"实际导出"一致, 否则查的不是成稿。
from md_source import (INLINE_CODE_RE, REFS_HEADING_TEXT, REF_ENTRY_RE,
                       FenceTracker, allocate_reference_numbers,
                       bibitem_payload, compact_title, discover_ordered_sources,
                       file_kind, has_heading_attrs, is_bibitem_line,
                       parse_heading, read_source_text, strip_heading_attrs)

# 引用候选: 1-3 位数字的 单个/逗号组合/连字符区间 (可混排)。排除 markdown
# 链接定义 [1]:、链接 [1](…)、转义 \[…、图片 ![…](…)
CITATION_RE = re.compile(r"(?<![\\!])\[(\d{1,3}(?:\s*[,，–-]\s*\d{1,3})*)\](?![:(])")
# 文献表条目行首 [N] 形态与"显式编号"正则唯一真源在 md_source (导出/审计共用)
REF_ENTRY_EXPLICIT_RE = REF_ENTRY_RE
# 密度检查不计入的章: 参考文献是定义区, 附录是代码/数据清单, 引用密度无意义
DENSITY_SKIP_TITLE_PREFIX = ("参考文献", "附录")
# 参考文献节标题 (## 或 # 级; 比对时去属性块与空白)
# 参考文献节标题 (## 或 # 级; 比对时去属性块与空白) —— 真源在 md_source
REFS_HEADING_TEXT = REFS_HEADING_TEXT

MAX_SUSPECT_SAMPLE = 8  # ⚠️ 疑似超范围清单的抽样上限


def _compact_title(title: str) -> str:
    """标题比对用紧凑形态 (md_source.compact_title 的兼容别名)。"""
    return compact_title(title)


def _strip_code_math(line: str, in_display: bool) -> tuple[str, bool]:
    """屏蔽行内代码 span 与数学段, 返回 (可扫描文本, 新的 display 状态)。

    - 行内代码 (`...` / ``...``, 同长反引号闭合; 正则走 md_source.INLINE_CODE_RE,
      与导出的 $ 计数同一口径) 整体替换为等长空白;
    - $$ 成对翻转载跨行 display 数学状态, 处于 display 内的整段不输出;
    - 行内 $...$ (含未闭合到行尾) 不输出。$$ 与 $ 的内容都不再参与
      引用匹配, 数学区间 [0,1] / [40,80] 因此不误报。
    """
    line = INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), line)
    out: list[str] = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch == "$" and i + 1 < n and line[i + 1] == "$":
            in_display = not in_display
            i += 2
            continue
        if ch == "$":
            if in_display:
                i += 1
                continue
            j = line.find("$", i + 1)
            i = n if j == -1 else j + 1
            continue
        if not in_display:
            out.append(ch)
        i += 1
    return "".join(out), in_display


def _parse_tokens(spec: str) -> list[tuple[int, int]] | None:
    """把引用组内容解析为 [(a,b), ...] token 列表 (单数字 a==b, 区间 a<=b)。

    非引用形态 (区间反向如 [3-1]) 返回 None, 调用方按数学/杂项跳过。"""
    tokens: list[tuple[int, int]] = []
    for raw_tok in re.split(r"[,，]", spec):
        tok = raw_tok.strip()
        parts = re.split(r"[–-]", tok)
        if len(parts) == 1:
            if not parts[0].isdigit():
                return None
            v = int(parts[0])
            tokens.append((v, v))
        elif len(parts) == 2:
            a, b = parts[0].strip(), parts[1].strip()
            if not (a.isdigit() and b.isdigit()):
                return None
            av, bv = int(a), int(b)
            if bv < av:
                return None
            tokens.append((av, bv))
        else:
            return None
    return tokens


def audit_ref_order(entries: list[tuple[str, Path]], discovery: str | None = None) -> dict:
    """对按文档顺序给定的 (显示名, 路径) 列表做文献编号顺序审计。

    返回 dict: 首引序列 / 新编号→首引位置 / 章节引用密度 / findings。
    findings 的 level: "fail" (❌, exit 1) 与 "warn" (⚠️, 人工核对)。
    discovery 只作报告用 (稿件发现策略名, 见 md_source.discover_ordered_sources)。
    """
    chapters: list[dict] = []          # 有序: {"title","file","line","count"} (## 级章)
    chapter_by_key: dict[tuple, dict] = {}
    defined: dict[int, str] = {}       # 文献表编号 -> "file:line"
    candidates: list[tuple[str, int, str, dict]] = []  # (file, line, 组内容, 章记录)
    dup_warns: list[str] = []          # 显式编号重复等 (条目分配函数返回的警告)
    loose_bibitems: list[tuple[str, int]] = []   # 不在文献表区内的 \bibitem (file, line)

    def _pseudo_chapter(fname: str) -> dict:
        """文件首个 ## 标题之前的引用归属"文首"伪章 (如无标题的摘要文件)。"""
        key = (fname, 0)
        if key not in chapter_by_key:
            rec = {"title": f"文首·{fname}", "file": fname, "line": 0, "count": 0}
            chapter_by_key[key] = rec
            chapters.append(rec)
        return chapter_by_key[key]

    for fname, path in entries:
        text = read_source_text(path)
        # 围栏/display 数学/文献表区状态均不跨文件 (refs 文件可能排在正文文件之后)
        tracker = FenceTracker()
        in_display = False
        # P2 修复: references 角色文件 (09_references.md 等) 无标题时导出侧会合成
        # "## 参考文献", 审计侧按同一 file_kind 认定"整文件即文献表"——不再因缺标题
        # 报 no_reference_section。该判定只影响语义, 不改任何行号 (行号仍按源文件)。
        in_refs = file_kind(path) == "references"
        refs_level = 0
        cur_chapter: dict | None = None
        ref_entries: list = []      # [(行内序号, 行号, 形态, 显式编号|None)]
        for lineno, raw in enumerate(text.splitlines(), 1):
            # 围栏 (变长: ```` 内的 ``` 是内容) 与导出/编号注入共用状态机
            if tracker.update(raw) or tracker.in_fence:
                continue
            scanned, in_display = _strip_code_math(raw, in_display)
            parsed = parse_heading(scanned)
            if parsed:
                level, raw_title = parsed
                title = strip_heading_attrs(raw_title)   # 去 "{-}" 等属性块
                title_cmp = _compact_title(title)
                if in_refs and level <= refs_level:
                    in_refs = False
                if not in_refs and level <= 2 and title_cmp == REFS_HEADING_TEXT:
                    in_refs = True
                    refs_level = level
                    cur_chapter = None  # 文献表是定义区, 不进密度统计
                elif not in_refs and level == 2:
                    if title_cmp.startswith(DENSITY_SKIP_TITLE_PREFIX):
                        cur_chapter = None
                    else:
                        key = (fname, lineno)
                        rec = {"title": title, "file": fname, "line": lineno, "count": 0}
                        chapter_by_key[key] = rec
                        chapters.append(rec)
                        cur_chapter = rec
                continue
            if in_refs:
                # 条目编号**只在文件末尾统一分配** (md_source.allocate_reference_numbers):
                # 显式 [N] 保号, \bibitem 取未被占用的最小正整数 —— 与导出的
                # convert_bibitems 同一规则。原实现 (bibitem 自增 + [N] 推游标) 在
                # "[1] Alpha + \bibitem{b} Beta" 混排时算出 defined={1,2} 判 pass,
                # 而导出产出 "[1] Alpha/[1] Beta" 重号 (bug-reviewer P1)。
                if is_bibitem_line(scanned):
                    ref_entries.append((lineno, "bibitem", None))
                else:
                    em = REF_ENTRY_RE.match(scanned)
                    if em:
                        ref_entries.append((lineno, "explicit", int(em.group(1))))
                continue
            if is_bibitem_line(scanned):
                # 不在任何文献表区内的 \bibitem: 导出不会转换 (非 references 文件
                # 只在显式 "## 参考文献" 节内转), 审计也必须报出来 —— 两端一致报
                # "未支持", 不能一边静默忽略一边判 pass。
                loose_bibitems.append((fname, lineno))
            for cm in CITATION_RE.finditer(scanned):
                ch_rec = cur_chapter if cur_chapter is not None else _pseudo_chapter(fname)
                candidates.append((fname, lineno, cm.group(1), ch_rec))

        # 本文件条目编号统一分配 (与导出 convert_bibitems 共用同一函数 → 两端一致)
        if ref_entries:
            numbers, warns = allocate_reference_numbers(
                [(0, lineno, kind, num) for lineno, kind, num in ref_entries])
            for (lineno, _kind, _num), num in zip(ref_entries, numbers):
                defined.setdefault(num, f"{fname}:{lineno}")
            dup_warns.extend(f"{fname}: {w}" for w in warns)

    # 保守口径: N = 文献表最大编号; 无文献表时 N=0 (任何组都不计引用)
    n_total = max(defined) if defined else 0
    first_loc: dict[int, str] = {}
    sequence: list[int] = []
    suspects: list[tuple[str, int, str]] = []
    for fname, lineno, spec, ch_rec in candidates:
        tokens = _parse_tokens(spec)
        if tokens is None:
            continue
        lo = min(a for a, _ in tokens)
        hi = max(b for _, b in tokens)
        if lo < 1:
            continue  # 含 0: 数学区间形态, 不计
        if hi <= n_total:
            for a, b in tokens:
                for num in range(a, b + 1):
                    if num not in first_loc:
                        first_loc[num] = f"{fname}:{lineno}"
                        sequence.append(num)
                    ch_rec["count"] += 1
        elif hi <= 999:
            suspects.append((fname, lineno, spec))

    findings: list[dict] = []
    if not defined:
        findings.append({
            "level": "fail", "rule": "no_reference_section",
            "detail": "未找到 `## 参考文献` 文献表 (识别 #/## 级标题, 节内行首 [N] 为条目); "
                      "无文献表时正文方括号组一律不计引用 (保守口径)。",
        })

    # 检查 ①: 首引顺序 = 1..N 严格递增 (期望序 = 尚未出现的最小编号)
    seen: set[int] = set()
    expected = 1
    for num in sequence:
        if num in seen:
            continue
        if num != expected:
            findings.append({
                "level": "fail", "rule": "first_cite_order",
                "detail": f"首引顺序断裂: 实际首引 [{num}], 期望 [{expected}] "
                          f"(第 {len(seen) + 1} 个新编号, 首次出现于 {first_loc[num]}; "
                          f"顺序编码制要求第一处引用即 [1], 新编号按首次出现依次 +1)",
            })
        seen.add(num)
        while expected in seen:
            expected += 1

    # 检查 ②: 被引集合 = 定义集合
    orphan = sorted(set(defined) - set(first_loc))
    if orphan:
        locs = "; ".join(f"[{n}] ({defined[n]})" for n in orphan)
        findings.append({
            "level": "fail", "rule": "orphan_reference",
            "detail": f"文献表 {len(orphan)} 条从未被正文引用 (孤立文献): {locs}。"
                      "未被引用的条目应删除, 或在正文补引。",
        })
    undefined = sorted(set(first_loc) - set(defined))
    if undefined:
        locs = "; ".join(f"[{n}] ({first_loc[n]})" for n in undefined)
        findings.append({
            "level": "fail", "rule": "undefined_citation",
            "detail": f"正文引用了文献表未定义的编号: {locs}。文献表缺条或编号跳跃, 须补齐。",
        })

    # 检查 ③: 章节引用密度 (参考文献/附录章已排除)
    zero = [c for c in chapters if c["count"] == 0]
    if zero:
        names = "; ".join(f"{c['title']} ({c['file']}:{c['line']})" for c in zero)
        findings.append({
            "level": "warn", "rule": "zero_citation_chapter",
            "detail": f"以下 {len(zero)} 个一级章文献引用计数为 0: {names}。"
                      "建模/求解主章零引用是典型弱点 (2026 A 题实测: §5 主体 360 行零引用)。",
        })

    if suspects:
        sample = "; ".join(f"[{s}] ({f}:{l})" for f, l, s in suspects[:MAX_SUSPECT_SAMPLE])
        findings.append({
            "level": "warn", "rule": "out_of_range_bracket",
            "detail": f"{len(suspects)} 处方括号组形似引用但编号超出文献表范围 (N={n_total}): {sample}"
                      f"{' …' if len(suspects) > MAX_SUSPECT_SAMPLE else ''}。"
                      "按保守口径未计为引用; 若为真引用须扩文献表, 若为数学区间可忽略。",
        })

    if dup_warns:
        findings.append({
            "level": "warn", "rule": "duplicate_reference_number",
            "detail": "; ".join(dup_warns) + "。重复编号会让导出后文献表与正文引用对不上, "
                      "请修正 md 里的显式编号或删掉重复条目。",
        })

    if loose_bibitems:
        shown = ", ".join(f"{f}:{n}" for f, n in loose_bibitems[:MAX_SUSPECT_SAMPLE])
        findings.append({
            "level": "warn", "rule": "bibitem_outside_refs",
            "detail": f"{len(loose_bibitems)} 行 \\bibitem 不在任何文献表区 ("
                      f"\"## 参考文献\" 节或 references 角色文件) 内: {shown}"
                      f"{' …' if len(loose_bibitems) > MAX_SUSPECT_SAMPLE else ''}。"
                      "导出侧同样不转换这些行 (会在终稿里留原始 LaTeX 命令), 请加 "
                      "\"## 参考文献\" 标题或在 references 文件里维护。",
        })

    return {
        "files": [fname for fname, _ in entries],
        "discovery": discovery or "files",
        "n_references": len(defined),
        "max_reference_number": n_total,
        "first_cite_sequence": sequence,
        "first_cite_locations": {str(k): first_loc[k] for k in sorted(first_loc)},
        "cited_numbers": sorted(first_loc),
        "defined_numbers": sorted(defined),
        "chapters": [{"title": c["title"], "file": c["file"], "line": c["line"],
                      "citations": c["count"]} for c in chapters],
        "findings": findings,
        "n_fail": sum(1 for f in findings if f["level"] == "fail"),
        "n_warn": sum(1 for f in findings if f["level"] == "warn"),
        "note": "口径: 只把全部编号 ∈ 1..N 的 [N]/[N,M]/[N-M] 组计为引用 (N=文献表最大编号); "
                "文献表条目支持 [N] 与旧式 \\bibitem 两种形态; "
                "跳过代码围栏 (变长)、行内代码与数学段; 含 0 或超范围的组不计。"
                "通过只代表编号顺序合规, 不评判文献内容。",
    }


def _collect_workspace(workspace: Path) -> list[tuple[str, Path]] | None:
    """项目根 → 与终稿导出**同一套**有序稿件发现 (md_source.discover_ordered_sources)。

    v3.1.0 修复: 原实现递归扫 paper_workspace/**/*.md, 把草稿/notes/README 等
    非导出 md 也算进引用与文献表 → 审计结论与成稿不符 (2026 A 题维护实测)。
    现在只审"真会被导出拼接的那些 md" (NN_*.md 系列优先, 否则 main.md /
    abstract_draft.md + sections/*.md), 顺序也与导出完全一致。
    未找到任何 md → None (调用方按输入错误 exit 2)。
    """
    pw = workspace / "paper_workspace"
    base, rel_base = (pw, pw) if pw.is_dir() else (workspace, workspace)
    paths, _mode = discover_ordered_sources(base)
    if not paths:
        return None
    return [(p.relative_to(rel_base).as_posix(), p) for p in paths]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except AttributeError:
        pass
    parser = argparse.ArgumentParser(description="文献编号顺序审计 (GB/T 7714 顺序编码制)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="项目根目录 (按**终稿导出同一套**有序稿件发现"
                                           "扫描: paper_workspace/ 下 NN_*.md 系列, 否则 "
                                           "main.md / abstract_draft+sections)")
    group.add_argument("--files", nargs="+", metavar="MD", help="md 文件列表 (按给定顺序扫描)")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = parser.parse_args()

    discovery = "files"
    if args.workspace:
        ws = Path(args.workspace)
        if not ws.is_dir():
            print(f"[错误] workspace 不存在: {ws}")
            return 2
        entries = _collect_workspace(ws)
        if not entries:
            print(f"[错误] {ws / 'paper_workspace'} (或 {ws} 本身) 下未找到可导出的 md "
                  f"(NN_*.md 系列 / main.md / abstract_draft+sections 均无)")
            return 2
        pw = ws / "paper_workspace"
        base = pw if pw.is_dir() else ws
        discovery = discover_ordered_sources(base)[1]
    else:
        entries = []
        for f in args.files:
            p = Path(f)
            if not p.is_file():
                print(f"[错误] 文件不存在: {p}")
                return 2
            entries.append((str(p), p))

    report = audit_ref_order(entries, discovery=discovery)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"文献编号顺序审计: {report['n_fail']} fail / {report['n_warn']} warn — "
              f"文献表 {report['n_references']} 条 (最大编号 {report['max_reference_number']}), "
              f"正文引用覆盖 {len(report['cited_numbers'])} 条 (扫描 {len(report['files'])} 个文件, "
              f"发现策略 {report['discovery']})")
        seq = report["first_cite_sequence"]
        print(f"  首引序列: {','.join(map(str, seq)) if seq else '(未发现引用)'}")
        locs = report["first_cite_locations"]
        if locs:
            pairs = [f"[{k}] {v}" for k, v in locs.items()]
            print("  新编号→首引位置:")
            for i in range(0, len(pairs), 4):
                print("    " + " | ".join(pairs[i:i + 4]))
        for f in report["findings"]:
            mark = "❌" if f["level"] == "fail" else "⚠️"
            print(f"  {mark} {f['rule']}: {f['detail']}")
        if not report["findings"]:
            print("  ✅ 三类检查全部通过: 首引顺序 1..N 严格递增; 被引集合=定义集合; 无零引用一级章")
        print(f"  {report['note']}")
    return 1 if report["n_fail"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
