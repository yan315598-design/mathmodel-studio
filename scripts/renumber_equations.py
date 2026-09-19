# -*- coding: utf-8 -*-
"""按出现顺序重排论文 md 中的公式编号。

背景：`references/md_authoring_spec.md` §4 规定公式编号手写在 `\\qquad (N)` 中，
插入或删除公式后必须全文重排编号，否则正文"式(N)"引用会指错。

本工具只负责**定义侧**：把所有 `\\qquad (N)` 按文档出现顺序重写为 1,2,3,...
引用侧（正文里的"式(N)"）语义不同，必须人工核对，工具会打印当前引用清单供对照。

运行：
    python scripts/renumber_equations.py --root <paper_workspace> --dry-run   # 只打印重排结果
    python scripts/renumber_equations.py --root <paper_workspace>             # 实际写入

文件范围：root 下的 0*.md 与 10_*.md（对应 render_paper 的 01..10 节文件），
跨文件连续编号。源自 2026 国赛 A 题项目侧自写工具（T-02），v2.7.0 收编通用化。
"""

import argparse
import glob
import re
from pathlib import Path

DEF_RE = re.compile(r"\\qquad\s*\((\d+)\)")
REF_RE = re.compile(r"式\s*\((\d+)\)")


def collect_files(root: Path) -> list[Path]:
    """root 下的节文件（0*.md + 10_*.md），按 render_paper 的节顺序排序。"""
    return [Path(f) for f in
            sorted(glob.glob(str(root / "0*.md"))) +
            sorted(glob.glob(str(root / "10_*.md")))]

def main() -> int:
    ap = argparse.ArgumentParser(description="按出现顺序重排 md 公式编号 (定义侧)")
    ap.add_argument("--root", type=str, default="paper_workspace",
                    help="论文工作区目录 (含 01..10_*.md 节文件), 默认 ./paper_workspace")
    ap.add_argument("--dry-run", action="store_true", help="只打印重排结果, 不写入")
    args = ap.parse_args()

    root = Path(args.root)
    files = collect_files(root)
    if not files:
        print(f"[FAIL] {root} 下未找到 0*.md / 10_*.md 节文件")
        return 1

    # 先把全部文件按顺序读入，保证编号跨文件连续
    contents = [(p, p.read_text(encoding="utf-8")) for p in files]

    counter = 0
    mapping = []
    new_contents = []
    for path, text in contents:
        def repl(m):
            nonlocal counter
            counter += 1
            old = int(m.group(1))
            mapping.append((path.name, old, counter))
            return "\\qquad (%d)" % counter

        new_contents.append((path, DEF_RE.sub(repl, text)))

    print(f"共 {counter} 条定义，按出现顺序重排：")
    changed = [(f, o, n) for f, o, n in mapping if o != n]
    for f, o, n in mapping:
        flag = "  <-- 变更" if o != n else ""
        print(f"  {f}: {o} -> {n}{flag}")
    print(f"\n实际发生变更 {len(changed)} 条。")

    refs = sorted({int(x) for x in REF_RE.findall("\n".join(t for _, t in contents))})
    print(f"正文当前引用的公式号：{refs}")
    print("注意：重排后必须人工核对上述引用是否仍然指向正确的公式。")

    if args.dry_run:
        print("\n[dry-run] 未写入文件。")
        return 0

    for path, text in new_contents:
        path.write_text(text, encoding="utf-8")
    print("\n[OK] 已写入。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
