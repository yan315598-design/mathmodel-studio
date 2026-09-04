"""package_submission.py — 竞赛提交物终检与打包 (v7.4.0 新增)

功能:
1. 读 cwd/state/decision_log.json 得 competition (--competition 可覆盖)
2. 按 references/submission_checklists.md 对应竞赛节做机器可查项:
   - 论文 PDF 存在性 (默认自动搜索, --paper 可指定)
   - 代码附件 (code/ 目录或工作区 *.py)
   - pdf_qa 终检 (v7.5.0 并入, scripts/pdf_qa.py import 调用): 页数上限/
     重复图表编号/匿名扫描/空白页, 页数口径统一走 pdf_qa; 其 ❌(error)
     违例纳入 blocking_fail (--apply 拒打包 exit 1); pypdf 缺失时该步
     整体 ⚠️ 跳过, 不阻断
   - 文件名规范 (空格/队号提示, 按竞赛 hint)
3. 默认 dry-run 只出中文检查报告; --apply 才执行:
   - 打包 zip 到 <out>/<comp>_<timestamp>.zip (out 默认 cwd/submission)
   - 复制备份到 <out>/backup/, 打印 zip MD5
4. 承诺书/摘要独立成页等语义项脚本不做判断, 报告尾部按
   references/submission_checklists.md 逐条提示人工核对 (匿名性已由
   pdf_qa 机器扫描兜底, 语义项仍建议人工复核)。

用法:
    python scripts/package_submission.py                        # dry-run 预览
    python scripts/package_submission.py --apply                # 实际打包
    python scripts/package_submission.py --competition mcm --paper paper/mcm.pdf
    python scripts/package_submission.py --apply --out ./submission

退出码: dry-run 恒为 0 (预览不阻断); --apply 时任一 ❌ 拒绝打包并返回 1。
"""

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

VALID_COMPETITIONS = ("cumcm", "mcm", "huaweibei", "huashubei", "diangong", "apmcm")

# 每竞赛机器可查规则; note_items 摘自 references/submission_checklists.md, 标注保留原文
COMPETITION_RULES = {
    "cumcm": {
        "page_limit": None,
        "filename_hint": "论文文件名通常含队号 [以当年通知为准]",
        "note_items": [
            ("承诺书页 + 编号专用页已并入论文 PDF", "以当年通知为准"),
            ("支撑材料单独打包且不含承诺书", "确定"),
            ("提交后记录 MD5/系统回执并截图留证", "确定"),
        ],
    },
    "mcm": {
        "page_limit": 25,
        "filename_hint": "英文文件名, 无空格; 队号按当年说明 [以当年通知为准]",
        "note_items": [
            ("首页为整页 Summary Sheet (250-350 词)", "确定"),
            ("匿名性: 正文/摘要无队员姓名与校名", "确定"),
            ("AI 使用报告置于附录或参考文献后", "以当年通知为准"),
        ],
    },
    "huaweibei": {
        "page_limit": None,
        "filename_hint": "文件名通常含队号 [以当年通知为准]",
        "note_items": [
            ("编号页/承诺书按当年模板执行", "以当年通知为准"),
            ("正文匿名性自查 (无姓名/学校)", "以当年通知为准"),
        ],
    },
    "huashubei": {
        "page_limit": None,
        "filename_hint": "文件名按当年通知 (通常含队号)",
        "note_items": [
            ("承诺书/签名页与命名规范", "以当年通知为准"),
            ("提交通道与附件大小限制", "以当年通知为准"),
        ],
    },
    "diangong": {
        "page_limit": None,
        "filename_hint": "文件名按当年通知",
        "note_items": [
            ("摘要 4 段式 600-1000 字, 页数参考 25-30 页", "以当年通知为准"),
            ("承诺书/编号页与文件命名", "以当年通知为准"),
        ],
    },
    "apmcm": {
        "page_limit": None,
        "filename_hint": "文件名按当年通知",
        "note_items": [
            ("论文语种与五段式摘要约 800 字", "以当年通知为准"),
            ("身份信息要求以当年通知为准", "以当年通知为准"),
        ],
    },
}

ICONS = {"ok": "✅", "warn": "⚠️ ", "fail": "❌"}

def load_competition(state_path: Path, override: str) -> str:
    """从 state/decision_log.json 读 competition; --competition 优先。读不到抛 SystemExit(中文提示)。"""
    if override:
        if override not in VALID_COMPETITIONS:
            raise SystemExit(f"未知竞赛 {override}; 可选: {', '.join(VALID_COMPETITIONS)}")
        return override
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"未找到 {state_path} 且未传 --competition; 无法确定竞赛")
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"读取 {state_path} 失败: {exc}")
    comp = data.get("competition")
    if comp not in VALID_COMPETITIONS:
        raise SystemExit(f"decision_log.competition={comp!r} 不在六竞赛白名单; 用 --competition 覆盖")
    return comp


def find_paper(workspace: Path, paper_arg: str):
    """按 --paper 指定或工作区惯例路径搜索论文 PDF, 返回 (Path|None, 说明)。"""
    if paper_arg:
        p = Path(paper_arg)
        return (p, "--paper 指定") if p.is_file() else (None, f"--paper 指定的 {paper_arg} 不存在")
    candidates = []
    for pattern in ("*.pdf", "paper_workspace/*.pdf", "paper/*.pdf"):
        candidates.extend(workspace.glob(pattern))
    if not candidates:
        return None, "工作区顶层 / paper_workspace/ / paper/ 均无 PDF"
    newest = max(candidates, key=lambda p: p.stat().st_mtime)
    return newest, f"自动搜索命中 {len(candidates)} 个 PDF, 取最新"


def load_pdf_qa():
    """import 同目录的 scripts/pdf_qa.py, 返回模块; 不可用返回 None。"""
    qa_path = Path(__file__).resolve().parent / "pdf_qa.py"
    if not qa_path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("pdf_qa", qa_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_pdf_qa_checks(results, paper: Path, comp: str, page_limit) -> bool:
    """调用 pdf_qa.check_pdf 做页数/重复图题/匿名/空白页检查。

    追加结果到 results; 返回是否产生阻塞项 (❌ error)。pdf_qa 不可用或
    pypdf 缺失 (findings 只有 info 降级提示) 时整体 ⚠️ 跳过, 不阻断。
    """
    qa = load_pdf_qa()
    if qa is None:
        results.append(("warn", "pdf_qa 终检", "scripts/pdf_qa.py 不可用, 该步跳过"))
        return False
    findings, _fatal = qa.check_pdf(
        paper, max_pages=page_limit, anonymous=True, competition=comp)
    level_map = {"ok": "ok", "info": "warn", "error": "fail"}
    blocking = False
    for f in findings:
        status = level_map[f.level]
        results.append((status, "pdf_qa 终检", f.message))
        if status == "fail":
            blocking = True
    return blocking


def collect_code_files(workspace: Path):
    """收集应进 zip 的代码文件: code/ 递归 + 顶层/paper_workspace 的 *.py。"""
    files = [p for p in workspace.glob("code/**/*") if p.is_file()]
    files += list(workspace.glob("*.py")) + list(workspace.glob("paper_workspace/**/*.py"))
    return sorted(set(files))


def run_checks(workspace: Path, comp: str, paper_arg: str):
    """执行全部检查, 返回 (results, paper_path, blocking_fail)。results: [(status, label, detail)]。"""
    rules = COMPETITION_RULES[comp]
    results = []

    state_path = workspace / "state" / "decision_log.json"
    if state_path.is_file():
        results.append(("ok", "state/decision_log.json", f"competition={comp}"))
    else:
        results.append(("warn", "state/decision_log.json", "不存在 (竞赛来自 --competition)"))

    paper, how = find_paper(workspace, paper_arg)
    blocking_fail = False
    if paper is None:
        results.append(("fail", "论文 PDF", how))
        blocking_fail = True
    else:
        rel = paper.relative_to(workspace) if paper.is_relative_to(workspace) else paper
        results.append(("ok", "论文 PDF", f"{rel} ({how})"))

        if " " in paper.name:
            results.append(("warn", "文件名规范", f"'{paper.name}' 含空格, 建议去除"))
        else:
            results.append(("ok", "文件名规范", rules["filename_hint"]))

        # pdf_qa 终检 (v7.5.0 并入): 页数/重复图题/匿名/空白页, 单一口径
        if run_pdf_qa_checks(results, paper, comp, rules["page_limit"]):
            blocking_fail = True

    code_files = collect_code_files(workspace)
    if code_files:
        results.append(("ok", "代码附件", f"{len(code_files)} 个文件待打包 (code/ 及 *.py)"))
    else:
        results.append(("warn", "代码附件", "未发现 code/ 或 *.py; 若支撑材料另行打包可忽略"))

    for label, tag in rules["note_items"]:
        results.append(("warn", f"人工核对: {label}", f"[{tag}]"))
    return results, paper, blocking_fail


def print_report(comp: str, results, apply: bool) -> None:
    print(f"\n===== 提交物检查报告 ({comp}, {'--apply 实打包' if apply else 'dry-run 预览'}) =====")
    for status, label, detail in results:
        print(f"  {ICONS[status]} {label}: {detail}")
    fails = sum(1 for s, _, _ in results if s == "fail")
    warns = sum(1 for s, _, _ in results if s == "warn")
    print(f"===== 汇总: ❌ {fails} / ⚠️ {warns} / ✅ {len(results) - fails - warns} =====\n")


def build_zip(workspace: Path, comp: str, out_dir: Path, paper: Path, code_files) -> Path:
    """打包论文 + 代码到 <out_dir>/<comp>_<timestamp>.zip, 备份到 <out_dir>/backup/, 返回 zip 路径。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{comp}_{timestamp}.zip"
    suffix = 2
    while zip_path.exists():  # 同秒重复 --apply 时追加序号, 避免无声覆盖
        zip_path = out_dir / f"{comp}_{timestamp}_{suffix}.zip"
        suffix += 1

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(paper, arcname=paper.name)
        for f in code_files:
            arc = f.relative_to(workspace) if f.is_relative_to(workspace) else Path(f.name)
            zf.write(f, arcname=str(arc))
        readme = workspace / "README.md"
        if readme.is_file():
            zf.write(readme, arcname="README.md")

    backup_dir = out_dir / "backup"
    backup_dir.mkdir(exist_ok=True)
    shutil.copy2(zip_path, backup_dir / zip_path.name)
    return zip_path


def md5_of(path: Path) -> str:
    digest = hashlib.md5()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台中文/符号兜底
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="竞赛提交物终检与打包 (v7.4.0); 检查项定义见 references/submission_checklists.md")
    parser.add_argument("--competition", choices=VALID_COMPETITIONS,
                        help="覆盖 state/decision_log.json 中的竞赛")
    parser.add_argument("--paper", help="论文 PDF 路径; 缺省时自动搜索工作区")
    parser.add_argument("--apply", action="store_true", help="实际打包 (默认 dry-run 预览)")
    parser.add_argument("--out", type=Path, default=None,
                        help="输出目录 (默认 cwd/submission)")
    args = parser.parse_args(argv)

    workspace = Path.cwd()
    comp = load_competition(workspace / "state" / "decision_log.json", args.competition)
    results, paper, blocking_fail = run_checks(workspace, comp, args.paper)
    print_report(comp, results, args.apply)

    if not args.apply:
        print("dry-run 预览结束; 确认无误后加 --apply 打包。语义项 (承诺书/匿名性/摘要成页) 请按报告提示人工核对。")
        return 0
    if blocking_fail:
        print("存在 ❌ 阻塞项, 拒绝打包; 修复后重试。")
        return 1
    out_dir = args.out if args.out else workspace / "submission"
    zip_path = build_zip(workspace, comp, out_dir, paper, collect_code_files(workspace))
    print(f"✅ 打包完成: {zip_path}")
    print(f"✅ 备份: {out_dir / 'backup' / zip_path.name}")
    print(f"✅ MD5: {md5_of(zip_path)}")
    print("提交后请截图系统回执留证 (通用终检第 10 条)。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
