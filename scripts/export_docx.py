"""export_docx.py — md 真源 → docx 审阅件导出 (v2.1.0 新增)

定位: workspace_protocol.md §3 "导出" 承诺 "定稿导出 docx/pdf 一律带时间戳进
submission/", 本脚本是其中 docx 侧的实现。docx 仅为审阅件 (导出给只会 Word 的
队员圈批注), md 才是真源; 正文修订永远发生在 md, 批注由 agent 读取后人工合回,
禁止 pandoc 反向转换覆盖真源 (协议 §3.1)。

功能:
1. 拼接 <workspace>/ 下 md 真源:
   - --files 显式指定时按给定顺序拼接 (相对路径按 workspace 解析)
   - 缺省自动发现: main.md 存在则只用它; 否则 abstract_draft.md (存在才加)
     + sections/*.md 按文件名自然排序 (q1 在 q10 前)
2. pandoc 转 docx: 数学 $..$/$$..$$ 自动转 Word OMML 公式, 管道表格直转;
   --reference-doc 可挂样式基准 docx (透传给 pandoc)
3. 相对路径图片经 --resource-path 解析 (各源文件父目录 + workspace 根/父目录,
   去重保序); pandoc 报 "Could not fetch resource" 时不视为失败, 打 [WARN]
   列出缺图 (docx 可能缺图但不阻断导出)
4. 输出 <out-dir>/<competition>_review_<YYYYMMDD_HHMM>.docx (本地时间),
   与 package_submission.py 共用 submission/ 目录约定; 目标已存在 (同分钟
   重复导出) 时拒绝覆盖直接报错; 临时拼接 md 放系统临时目录, 用完删除

competition 来源: --competition > <workspace>/../state/decision_log.json 的
competition 字段 (读不到/文件损坏均静默回退) > "paper"。仅用作输出文件名前缀,
须为安全文件名 (非空/不含 / \\ : * ? " < > | 与控制字符/非 Windows 保留名/
非纯点); CLI 传入非法值报错退出, decision_log 读到非法值回退 "paper"。

用法:
    python scripts/export_docx.py                                    # paper_workspace/ → submission/
    python scripts/export_docx.py --workspace ws/ --competition huaweibei
    python scripts/export_docx.py --files main.md sections/q1_draft.md  # 显式拼接顺序
    python scripts/export_docx.py --reference-doc style.docx           # 挂样式基准
    python scripts/export_docx.py --dry-run                           # 只打印 pandoc 命令 (无 pandoc 也可)

退出码: 0 成功导出 (或 dry-run 预览); 2 输入错误 (workspace 不存在/无 md 可拼/
文件缺失/读取失败/--reference-doc 缺失/competition 非法/同分钟目标已存在) 或
pandoc 不可用/执行失败。
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# 数学 $..$ 直转 (docx 输出为 Word OMML 公式) + 管道表格直转, 与 render_paper 的
# md→tex 同一入口语法, 保证两路解析口径一致
PANDOC_FROM = "markdown+tex_math_dollars+pipe_tables"

PANDOC_INSTALL_HINT = ("pandoc 不可用; 请安装 pandoc 后重试: "
                       "https://pandoc.org/installing.html 或 winget install pandoc")

# Windows 保留设备名 (不带扩展或作为主文件名均非法), 不区分大小写
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL",
                     *(f"COM{i}" for i in range(1, 10)),
                     *(f"LPT{i}" for i in range(1, 10))}


def natural_key(name: str) -> list:
    """自然排序键: 文件名按 数字段数值 + 非数字段 混合比较, 使 q1 排在 q10 前。"""
    return [int(tok) if tok.isdigit() else tok.lower()
            for tok in re.split(r"(\d+)", name)]


def is_safe_filename(name: str) -> bool:
    """校验 competition 可否安全用作输出文件名段 (Windows 兼容口径)。

    非法: 空串/纯点; 含 / \\ : * ? " < > | 或控制字符; Windows 保留设备名
    (CON / PRN / AUX / NUL / COM1-9 / LPT1-9, 含作为主文件名的情形)。
    """
    if not name or name.strip(".") == "":
        return False
    if any(ch in name for ch in '/\\:*?"<>|'):
        return False
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        return False
    stem = name.split(".")[0].upper()
    return name.upper() not in _WINDOWS_RESERVED and stem not in _WINDOWS_RESERVED


def discover_md_files(workspace: Path) -> list:
    """自动发现待拼接 md, 返回按拼接顺序排列的路径列表 (空列表 = 一个 md 都没有)。

    规则: main.md 存在则只用它 (单文件真源); 否则 abstract_draft.md (存在才加)
    + sections/*.md 按文件名自然排序。
    """
    main_md = workspace / "main.md"
    if main_md.is_file():
        return [main_md]
    found = []
    abstract = workspace / "abstract_draft.md"
    if abstract.is_file():
        found.append(abstract)
    sections_dir = workspace / "sections"
    if sections_dir.is_dir():
        found.extend(sorted(sections_dir.glob("*.md"),
                            key=lambda p: natural_key(p.name)))
    return found


def resolve_files(workspace: Path, files_arg) -> list:
    """确定拼接清单: --files 显式列表优先 (按给定顺序), 否则自动发现。

    显式列表中的相对路径按 workspace 解析; 文件存在性由调用方统一校验。
    """
    if files_arg:
        picked = []
        for raw in files_arg:
            p = Path(raw)
            if not p.is_absolute():
                p = workspace / p
            picked.append(p)
        return picked
    return discover_md_files(workspace)


def resolve_competition(cli_arg, workspace: Path) -> str:
    """优先级: --competition > decision_log.competition > "paper"。

    decision_log 路径按工作区骨架约定取 <workspace>/../state/decision_log.json;
    读不到/文件损坏/字段缺失均静默回退 "paper" (本脚本只做导出, 不因状态文件
    问题阻断审阅件生成)。decision_log 读到非安全文件名的值时打提示并同样回退;
    CLI 显式传入的值不在此校验 (非法即报错退出, 由调用方处理)。
    """
    if cli_arg:
        return cli_arg
    log_path = workspace.parent / "state" / "decision_log.json"
    try:
        data = json.loads(log_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # 文件不存在/损坏/编码错 一律静默回退
        return "paper"
    comp = data.get("competition") if isinstance(data, dict) else None
    if not comp:
        return "paper"
    if not is_safe_filename(comp):
        print(f"[WARN] decision_log.competition={comp!r} 不是安全文件名, 回退用 'paper'")
        return "paper"
    return comp


def build_resource_dirs(md_files: list, workspace: Path) -> list:
    """构造 pandoc --resource-path 目录清单 (去重保序)。

    拼接 md 位于系统临时目录, 正文里的相对图片路径 (如 ../figures/x.png)
    需要显式给出解析基准: 各源文件父目录 + workspace 根 + workspace 父目录
    (覆盖工作区骨架中 figures/ 与 paper_workspace/ 同级的惯例布局)。
    """
    dirs = [p.parent for p in md_files] + [workspace, workspace.parent]
    seen, unique = set(), []
    for d in dirs:
        key = os.path.normcase(str(d.resolve()))
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


def build_pandoc_cmd(tmp_md: Path, out_docx: Path, resource_dirs: list,
                     reference_doc) -> list:
    """组装 pandoc 命令行: 输入拼接 md, 数学/管道表格直转, 输出 docx。

    dry-run 与真实执行共用本函数, 保证打印的命令即真实命令。
    """
    cmd = ["pandoc", str(tmp_md), "-f", PANDOC_FROM]
    for d in resource_dirs:  # 多次追加同名 flag, 免去平台路径分隔符问题
        cmd += ["--resource-path", str(d)]
    if reference_doc is not None:
        cmd += ["--reference-doc", str(reference_doc)]
    cmd += ["-o", str(out_docx)]
    return cmd


def has_pandoc() -> bool:
    """探测本机 pandoc 是否可调用 (脚本内自实现, 不 import render_paper 避免副作用)。"""
    try:
        r = subprocess.run(["pandoc", "--version"],
                           capture_output=True, text=True, encoding="utf-8")
        return r.returncode == 0
    except FileNotFoundError:
        return False


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台中文兜底
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="md 真源 → docx 审阅件导出 (v2.1.0); docx=审阅件 md=真源, "
                    "批注由 agent 读取后合回 md, 禁止反向转换覆盖真源")
    parser.add_argument("--workspace", type=Path, default=Path("paper_workspace"),
                        help="md 真源目录 (默认 paper_workspace)")
    parser.add_argument("--out-dir", type=Path, default=Path("submission"),
                        help="输出目录 (默认 submission, 不存在则创建)")
    parser.add_argument("--competition", default=None,
                        help="输出文件名前缀 (须为安全文件名); 缺省读 "
                             "<workspace>/../state/decision_log.json 的 "
                             "competition 字段, 再缺省用 paper")
    parser.add_argument("--files", nargs="+", metavar="MD", default=None,
                        help="显式指定 md 文件列表, 按给定顺序拼接 "
                             "(相对路径按 workspace 解析); 缺省自动发现")
    parser.add_argument("--reference-doc", type=Path, default=None,
                        help="pandoc --reference-doc 样式基准 docx (透传)")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印将执行的 pandoc 命令, 不执行、不写文件 "
                             "(无需安装 pandoc)")
    args = parser.parse_args(argv)

    workspace = args.workspace
    if not workspace.is_dir():
        print(f"[FAIL] workspace {workspace} 不存在")
        return 2

    md_files = resolve_files(workspace, args.files)
    missing = [str(p) for p in md_files if not p.is_file()]
    if missing:
        print(f"[FAIL] 以下 md 文件不存在: {missing}")
        return 2
    if not md_files:
        print(f"[FAIL] {workspace} 下未发现任何 md (main.md / abstract_draft.md / "
              f"sections/*.md 均无), 无可导出内容; 或用 --files 显式指定")
        return 2

    if args.reference_doc is not None and not args.reference_doc.is_file():
        print(f"[FAIL] --reference-doc 指定的 {args.reference_doc} 不存在")
        return 2

    competition = resolve_competition(args.competition, workspace)
    if args.competition is not None and not is_safe_filename(competition):
        print(f"[FAIL] --competition {args.competition!r} 不是安全文件名 "
              f"(须非空、不含 / \\ : * ? \" < > | 与控制字符、非 Windows 保留名、非纯点)")
        return 2

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = args.out_dir / f"{competition}_review_{timestamp}.docx"
    if out_path.exists():
        # 分钟级时间戳: 同一分钟重复导出会同名, 拒绝静默覆盖
        print(f"[FAIL] {out_path} 已存在 (同一分钟内已导出过); "
              f"等待下一分钟或用 --out-dir 换目录, 不覆盖旧文件")
        return 2

    # dry-run 与真实执行共用同一命令构造 (打印的命令即真实命令);
    # dry-run 不写临时 md、不建 out-dir、不探测/调用 pandoc
    resource_dirs = build_resource_dirs(md_files, workspace)
    tmp_md = Path(tempfile.gettempdir()) / f"export_docx_{os.getpid()}_{timestamp}.md"
    cmd = build_pandoc_cmd(tmp_md, out_path, resource_dirs, args.reference_doc)
    if args.dry_run:
        print(f"[OK] dry-run: 将拼接 {len(md_files)} 个 md → {out_path}")
        print(f"     {shlex.join(cmd)}")
        return 0

    # 真实执行: 读源 → 建 out-dir → 探测/调用 pandoc
    contents = []
    for p in md_files:
        try:
            contents.append(p.read_text(encoding="utf-8").rstrip("\n"))
        except (OSError, UnicodeError) as e:
            print(f"[FAIL] 读取 {p} 失败: {e}; md 真源请保存为 UTF-8 编码")
            return 2
    # 拼接 md: 文件间补空行, 避免相邻文件的标题/列表粘连;
    # \tag{N} 预归一为 \qquad (N)——pandoc 数学解析器会吞掉 \tag 的反斜杠导致
    # docx 里编号直接消失 (实测), 归一后 Word 审阅件能显示块内右侧编号
    merged = "\n\n".join(contents) + "\n"
    merged = re.sub(
        r"\$\$(.+?)\\tag\s*\{(\d+)\}\s*\$\$",
        lambda m: f"$${m.group(1).strip()} \\qquad ({m.group(2)})$$",
        merged, flags=re.DOTALL)

    try:
        args.out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"[FAIL] 创建输出目录 {args.out_dir} 失败: {e}")
        return 2

    if not has_pandoc():
        print(f"[FAIL] {PANDOC_INSTALL_HINT}")
        return 2

    try:
        try:
            with open(tmp_md, "w", encoding="utf-8") as f:
                f.write(merged)
        except OSError as e:
            print(f"[FAIL] 写临时拼接文件 {tmp_md} 失败: {e}")
            return 2
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        except FileNotFoundError:
            print(f"[FAIL] {PANDOC_INSTALL_HINT}")
            return 2
        if r.returncode != 0:
            print(f"[FAIL] pandoc 退出码 {r.returncode}: {r.stderr.strip()}")
            print(f"       {PANDOC_INSTALL_HINT}")
            return 2
        # 缺图是降级告警不是失败: pandoc 退出 0 但 docx 内无该图, 须向用户亮出
        if "Could not fetch resource" in r.stderr:
            print("[WARN] 部分图片资源未找到, docx 可能缺图:")
            for line in r.stderr.splitlines():
                if "Could not fetch resource" in line:
                    print(f"     {line.strip()}")
    finally:
        # 清理失败只告警, 不改变退出码 (不让 PermissionError 覆盖 pandoc 结果)
        try:
            tmp_md.unlink(missing_ok=True)
        except OSError:
            print(f"[WARN] 临时文件清理失败: {tmp_md}")

    try:
        if not out_path.is_file():
            raise FileNotFoundError(str(out_path))
        size = out_path.stat().st_size
    except OSError:
        print(f"[FAIL] pandoc 声称成功但未生成可读的 {out_path}")
        return 2

    print(f"[OK] 已导出 docx 审阅件: {out_path.resolve()} ({size} 字节)")
    print(f"     来源 {len(md_files)} 个 md (真源); docx 仅作审阅, 修订请改 md 后重新导出")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
