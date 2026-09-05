"""华为杯（中国研究生数学建模竞赛）语料蒸馏的可复现校验流水线。

知识库 competitions/huaweibei/ 此前由库外一次性流程产出，本脚本把其中
"机器可校验层"固化成可重跑命令：

- scan            扫描语料根，按年份/题号输出赛题、论文、附件与论文页数预览；
- verify-manifest 对 source_manifest.json 逐条重算 sha256，报告缺失/变更/未登记漂移；
- build-empirical 从论文 PDF 重算页数与摘要净字符统计，默认与 empirical.json
                  对比打印差异，--apply 才写回（保留 schema_version 与 scoring_policy）；
- validate        校验人工层文件（manual_review_annotations.json、
                  manual_paper_reviews.json、cases/index.json）的完整性。

所有子命令默认只读，仅 build-empirical --apply 会写文件。
退出码：0 无发现；1 存在漂移、校验失败或 build-empirical dry-run 发现
数值差异/提取失败；2 输入错误（文件缺失、JSON 损坏、manifest 字段不全等）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import fitz


SKILL_ROOT = Path(__file__).resolve().parent.parent
COMP_ROOT = SKILL_ROOT / "competitions" / "huaweibei"
# 语料根不在源码中硬编码（开源卫生）：用环境变量 MATHMODEL_HUAWEIBEI_CORPUS 或 --corpus-root 指定。
_env_corpus = os.environ.get("MATHMODEL_HUAWEIBEI_CORPUS")
DEFAULT_CORPUS_ROOT = Path(_env_corpus) if _env_corpus else None
DEFAULT_MANIFEST = COMP_ROOT / "source_manifest.json"
DEFAULT_EMPIRICAL = COMP_ROOT / "empirical.json"

# 语料根下的提取缓存目录与系统垃圾文件不参与清单核对。
EXCLUDED_DIR_NAMES = {"extracted_text"}
JUNK_FILE_NAMES = {"thumbs.db", "desktop.ini", ".ds_store"}

PROBLEM_TREE_MARKER = "赛题"
PAPER_TREE_MARKER = "优秀论文"
STAR_DIR_MARKER = "提名"
STATEMENT_SUFFIXES = {".pdf", ".doc", ".docx"}
# 赛题目录下带这些字样的文件按附件处理（启发式兜底，登记文件以 manifest 为准）。
ATTACHMENT_NAME_HINT = re.compile(r"附件|数据|说明|readme|通知|承诺书", re.IGNORECASE)
PROBLEM_DIR_PATTERN = re.compile(r"^(?:20\d{2}年)?([A-F])题$")
# 头尾标记都锚定行首（re.MULTILINE ^）：正文句中提到"摘要/关键词"不应触发
# 头标记或提前截断尾标记；摘/要 之间的 \s* 允许"摘\n要："这类跨行标题。
ABSTRACT_HEAD = re.compile(r"^[ \t\u3000]*摘\s*要[ \t\u3000]*[:：]?\s*", re.MULTILINE)
# 尾部标记按同义形态同时接受"关键词/关键字"：语料中 23 篇论文使用"关键字"，
# 不接受会使可复现口径与原库 n=190 的覆盖率产生无谓偏差。
ABSTRACT_TAIL = re.compile(r"^[ \t\u3000]*关\s*键\s*[词字]", re.MULTILINE)
WHITESPACE = re.compile(r"\s+")
# 规范问号键：Q + ASCII 数字（全角数字如 Q３ 属于 OCR 噪声，v2 清理口径内应剔除）。
QUESTION_KEY_PATTERN = re.compile(r"^Q[0-9]+$")

QUANTILE_NAMES = (("p25", 0.25), ("p50", 0.5), ("p75", 0.75))


def ensure_utf8_stdout() -> None:
    """Windows 管道默认本地编码，切换到 UTF-8 保证中文表格不乱码。"""
    for stream in (sys.stdout, sys.stderr):
        if stream.encoding and stream.encoding.lower().replace("-", "") != "utf8":
            stream.reconfigure(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict:
    """读取 JSON 文件，缺失或解析失败时抛出可定位的错误（由 main 统一转退出码 2）。"""
    if not path.is_file():
        raise FileNotFoundError(f"文件不存在: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"JSON 解析失败: {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    """流式计算文件哈希，避免把大 PDF 一次读入内存。"""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_corpus_root(value):
    """None（未设环境变量与参数）时给出可读错误，而非 AttributeError。"""
    if value is None:
        raise SystemExit(
            "错误：未指定语料根。请用 --corpus-root 参数或设置环境变量 "
            "MATHMODEL_HUAWEIBEI_CORPUS 指向华为杯语料目录。"
        )
    return value


def iter_corpus_files(corpus_root: Path):
    """遍历语料根下的内容文件，跳过提取缓存目录与系统垃圾文件。"""
    for path in sorted(corpus_root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.relative_to(corpus_root).parts):
            continue
        if path.name.lower() in JUNK_FILE_NAMES:
            continue
        yield path


def relative_posix(path: Path, corpus_root: Path) -> str:
    """返回相对语料根的正斜杠路径，与 manifest 的 path 字段同构。"""
    return path.relative_to(corpus_root).as_posix()


YEAR_COMPONENT = re.compile(r"^(20\d{2})(?!\d)")
COMPETITION_MARKERS = ("赛题", "优秀论文", "竞赛")


def infer_year(dir_parts: list[str]) -> tuple[int | None, list[int]]:
    """逐级搜索目录组件推断年份，返回（年份, 全部候选）。

    只认纯年份目录（如 "2021"），或顶层/带竞赛语境（赛题、优秀论文、竞赛）
    的年份前缀目录；附件数据里的"2017年鉴"这类内容年份不算候选。
    出现多个不同候选时取最上层的一个，由调用方提示冲突。
    """
    candidates: list[int] = []
    for index, part in enumerate(dir_parts):
        match = YEAR_COMPONENT.match(part)
        if not match:
            continue
        if part == match.group(1) or index == 0 or any(marker in part for marker in COMPETITION_MARKERS):
            year = int(match.group(1))
            if year not in candidates:
                candidates.append(year)
    if not candidates:
        return None, []
    return candidates[0], candidates


def infer_placement(rel_posix: str) -> dict:
    """按目录与文件名启发式推断文件的类别、年份、题号与提名标记。

    返回 dict(kind, year, problem, star, year_conflict)；year_conflict 在目录
    中出现多个不同候选年份时给出候选列表，否则为 None。无法归类的 kind="other"。
    启发式只做兜底，已登记文件以 manifest 的 kind 为准。
    """
    parts = rel_posix.split("/")
    top = parts[0]
    year, year_candidates = infer_year(parts[:-1])
    year_conflict = year_candidates if len(year_candidates) > 1 else None
    name = parts[-1]
    suffix = Path(name).suffix.lower()

    if PAPER_TREE_MARKER in top:
        star = any(STAR_DIR_MARKER in part for part in parts)
        problem = None
        for part in parts[1:-1]:
            if re.fullmatch(r"[A-F]", part):
                problem = part
                break
            match = re.fullmatch(r"([A-F])题(?:优秀论文)?", part)
            if match:
                problem = match.group(1)
                break
        if problem is None:
            # 提名目录与 2022/2023 平铺命名都把题号写在文件名首字母。
            match = re.match(r"^([A-F])(?:\d{4,}|题|-)", name)
            problem = match.group(1) if match else None
        return {"kind": "paper", "year": year, "problem": problem, "star": star, "year_conflict": year_conflict}

    if PROBLEM_TREE_MARKER in top:
        problem = None
        problem_dir_index = None
        for index, part in enumerate(parts[1:-1], start=1):
            match = PROBLEM_DIR_PATTERN.fullmatch(part)
            if match:
                problem = match.group(1)
                problem_dir_index = index
                break
        direct_statement = False
        if problem_dir_index is not None:
            # 题面文件必须直接位于题号目录内，中间只允许再嵌套同名的 "X题" 目录
            #（2024/2025 赛题存在 E题/E题/xxx.docx 这类双层结构）。
            intermediates = parts[problem_dir_index + 1:-1]
            direct_statement = (
                suffix in STATEMENT_SUFFIXES
                and all(PROBLEM_DIR_PATTERN.fullmatch(part) for part in intermediates)
                and not ATTACHMENT_NAME_HINT.search(name)
            )
        if direct_statement:
            return {"kind": "problem_statement", "year": year, "problem": problem, "star": False,
                    "year_conflict": year_conflict}
        return {"kind": "attachment_document", "year": year, "problem": problem, "star": False,
                "year_conflict": year_conflict}

    return {"kind": "other", "year": year, "problem": None, "star": False, "year_conflict": year_conflict}


def scan_placements(corpus_root: Path, manifest: dict | None) -> tuple[list[dict], list[str]]:
    """扫描语料并融合 manifest 分类：已登记文件用 manifest 的 kind 与 award_tier。

    返回 (placements, warnings)；warnings 汇总去重后的年份冲突提示。
    提名身份优先取 manifest 的 award_tier 字段（inventory 项无该字段时才回退
    到路径含"提名"的启发式）。
    """
    manifest_records: dict[str, dict] = {}
    if manifest:
        for record in manifest.get("records", []):
            manifest_records[record["path"]] = record
        for item in manifest.get("inventory", []):
            manifest_records.setdefault(item["path"], item)
    placements = []
    warnings: list[str] = []
    seen_year_conflicts: set[tuple[int, ...]] = set()
    for path in iter_corpus_files(corpus_root):
        rel = relative_posix(path, corpus_root)
        placement = infer_placement(rel)
        placement["path"] = rel
        placement["absolute"] = path
        record = manifest_records.get(rel)
        placement["registered"] = record is not None
        if record is not None:
            placement["kind"] = record.get("kind", placement["kind"])
            award_tier = record.get("award_tier")
            if award_tier:
                placement["star"] = award_tier == "star_nominee"
            elif placement["kind"] == "paper":
                placement["star"] = STAR_DIR_MARKER in rel
        conflict = placement.pop("year_conflict")
        if conflict and tuple(conflict) not in seen_year_conflicts:
            seen_year_conflicts.add(tuple(conflict))
            warnings.append(f"路径出现多个候选年份 {conflict}，取 {placement['year']}（示例 {rel}）")
        placements.append(placement)
    return placements, warnings


def load_manifest_argument(value: str) -> dict | None:
    """解析 --manifest 参数：路径或 "none"（禁用登记底册）。"""
    if value.lower() == "none":
        return None
    return load_json(Path(value))


def pdf_page_count(path: Path) -> int | None:
    """返回 PDF 页数；无法打开时返回 None 由调用方计入提取失败。"""
    try:
        with fitz.open(path) as document:
            return len(document)
    except Exception:
        return None


# ---------------------------------------------------------------- scan ----


def cmd_scan(args: argparse.Namespace) -> int:
    """输出按年份/题号分组的语料清单预览。"""
    corpus_root = resolve_corpus_root(args.corpus_root).resolve()
    if not corpus_root.is_dir():
        print(f"错误：语料根不存在: {corpus_root}")
        return 2
    manifest = load_manifest_argument(args.manifest) if args.manifest else None
    placements, warnings = scan_placements(corpus_root, manifest)
    for warning in warnings:
        print(f"警告：{warning}")

    rows: dict[tuple, dict] = defaultdict(lambda: {"problems": 0, "papers": 0, "attachments": 0, "pages": 0})
    for placement in placements:
        key = (placement["year"], placement["problem"] or "?")
        row = rows[key]
        kind = placement["kind"]
        if kind == "problem_statement":
            row["problems"] += 1
        elif kind == "paper":
            row["papers"] += 1
            pages = pdf_page_count(placement["absolute"])
            row["pages"] += pages or 0
        else:
            row["attachments"] += 1

    header = f"{'年份':<6}{'题':<4}{'赛题':>4}{'论文':>5}{'附件':>5}{'论文页数':>9}"
    print(header)
    print("-" * len(header))
    totals = {"problems": 0, "papers": 0, "attachments": 0, "pages": 0, "stars": 0}
    for (year, problem), row in sorted(rows.items(), key=lambda item: (item[0][0] or 0, item[0][1])):
        print(f"{year or '?':<6}{problem:<4}{row['problems']:>4}{row['papers']:>5}{row['attachments']:>5}{row['pages']:>9}")
        for field in totals:
            totals[field] += row.get(field, 0)
    totals["stars"] = sum(1 for item in placements if item["kind"] == "paper" and item["star"])
    print("-" * len(header))
    print(f"{'合计':<6}{'':<4}{totals['problems']:>4}{totals['papers']:>5}{totals['attachments']:>5}{totals['pages']:>9}")
    print(f"提名论文 {totals['stars']} 篇；内容文件 {len(placements)} 个", end="")
    if manifest is not None:
        unregistered = sum(1 for item in placements if not item["registered"])
        print(f"，其中清单未登记 {unregistered} 个（scan 的分类以 manifest 为准，未登记文件按启发式归类）")
    else:
        print("（未提供 manifest，全部按启发式归类）")
    return 0


# ---------------------------------------------------- verify-manifest ----


def cmd_verify_manifest(args: argparse.Namespace) -> int:
    """重算 manifest 每条记录的 sha256 并报告三类漂移。"""
    corpus_root = resolve_corpus_root(args.corpus_root).resolve()
    if not corpus_root.is_dir():
        print(f"错误：语料根不存在: {corpus_root}")
        return 2
    manifest = load_manifest_argument(args.manifest)
    if manifest is None:
        print("错误：verify-manifest 需要 manifest 文件（--manifest 不能为 none）")
        return 2

    missing: list[str] = []
    changed: list[tuple[str, str, str]] = []
    for record in manifest.get("records", []):
        # path/sha256 是核对的前提，字段缺失按输入错误处理（退出码 2）。
        for field in ("path", "sha256"):
            if field not in record:
                raise KeyError(f"manifest 记录缺少字段 {field!r}: {json.dumps(record, ensure_ascii=False)[:200]}")
        rel = record["path"]
        path = corpus_root / rel
        if not path.is_file():
            missing.append(rel)
            continue
        actual = sha256_file(path)
        if actual != record["sha256"]:
            changed.append((rel, record["sha256"], actual))

    inventory_paths = {item["path"] for item in manifest.get("inventory", [])}
    record_paths = {record["path"] for record in manifest.get("records", [])}
    disk_paths = {relative_posix(path, corpus_root) for path in iter_corpus_files(corpus_root)}
    inventory_missing = sorted((inventory_paths | record_paths) - disk_paths)
    unregistered = sorted(disk_paths - inventory_paths - record_paths)

    print(f"manifest 记录 {len(manifest.get('records', []))} 条，inventory {len(inventory_paths)} 条，"
          f"语料文件 {len(disk_paths)} 个")
    print(f"缺失 {len(missing)}，变更 {len(changed)}，未登记 {len(unregistered)}，"
          f"inventory 缺失 {len(inventory_missing)}")
    for rel in missing:
        print(f"[missing] {rel}")
    for rel, old, new in changed:
        print(f"[changed] {rel}\n  manifest {old}\n  actual   {new}")
    if inventory_missing:
        print(f"[inventory-missing] {len(inventory_missing)} 个 inventory 路径在语料中不存在：")
        for rel in inventory_missing[:20]:
            print(f"  {rel}")
        if len(inventory_missing) > 20:
            print(f"  ... 其余 {len(inventory_missing) - 20} 个省略")
    if unregistered:
        by_top: dict[str, int] = defaultdict(int)
        for rel in unregistered:
            by_top[rel.split("/")[0]] += 1
        print(f"[unregistered] {len(unregistered)} 个语料文件未登记，按顶层目录分布：")
        for top, count in sorted(by_top.items(), key=lambda item: -item[1]):
            print(f"  {count:>4}  {top}")
        for rel in unregistered[:15]:
            print(f"  - {rel}")
        if len(unregistered) > 15:
            print(f"  ... 其余 {len(unregistered) - 15} 个省略")

    drift = bool(missing or changed or unregistered or inventory_missing)
    if drift:
        print("结论：存在漂移，退出码 1")
    else:
        print("结论：manifest 与语料一致")
    return 1 if drift else 0


# ----------------------------------------------------- build-empirical ----


def percentile(sorted_values: list[float], q: float) -> float:
    """线性插值分位数：sorted 后按 (n-1)*q 定位，floor/ceil 之间线性插值。"""
    if not sorted_values:
        raise ValueError("分位数需要非空样本")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = (len(sorted_values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(sorted_values[lower])
    weight = position - lower
    return float(sorted_values[lower] + weight * (sorted_values[upper] - sorted_values[lower]))


def summarize(values: list[float]) -> dict:
    """汇总 n/min/p25/p50/p75/max/mean，均值保留 4 位小数；空样本各统计量记 0。"""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"n": 0, "min": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "max": 0.0, "mean": 0.0}
    stats = {
        "n": len(ordered),
        "min": percentile(ordered, 0.0),
        "max": percentile(ordered, 1.0),
        "mean": round(sum(ordered) / len(ordered), 4) if ordered else 0.0,
    }
    for name, q in QUANTILE_NAMES:
        stats[name] = round(percentile(ordered, q), 2)
    ordered_stats = ["n", "min", "p25", "p50", "p75", "max", "mean"]
    return {key: stats[key] for key in ordered_stats}


def extract_abstract_chars(text: str) -> int | None:
    """统计摘要净字符数："摘 要"起至"关键词/关键字"止，去除全部空白后计 Unicode 字符。

    找不到头或尾标记时返回 None，由调用方计入 extraction_failures。
    """
    head = ABSTRACT_HEAD.search(text)
    if not head:
        return None
    tail = ABSTRACT_TAIL.search(text, head.end())
    if not tail:
        return None
    body = text[head.end():tail.start()]
    return len(WHITESPACE.sub("", body))


def analyze_paper(placement: dict, evidence_by_path: dict[str, str]) -> dict:
    """提取单篇论文的页数与摘要净字符数，并给出可定位的 paper id。"""
    rel = placement["path"]
    paper_id = evidence_by_path.get(rel)
    if paper_id is None:
        paper_id = f"graduate:paper:{placement['year'] or 'unknown'}-{placement['problem'] or 'unknown'}:{sha256_file(placement['absolute'])[:12]}"
    result = {"path": rel, "paper_id": paper_id, "star": placement["star"], "pages": None, "abstract_chars": None}
    try:
        with fitz.open(placement["absolute"]) as document:
            result["pages"] = len(document)
            # 口径为"首页起到关键词止"，不设页数上限；个别论文的摘要
            # 连同标题页会延伸到第 4-5 页才出现关键词行。
            text = "\n".join(page.get_text("text") for page in document)
    except Exception:
        return result
    result["abstract_chars"] = extract_abstract_chars(text)
    return result


def group_stat_block(papers: list[dict]) -> dict:
    """按现有 empirical.json 的组结构生成 reliable_for_reference 统计块。"""
    pages = [paper["pages"] for paper in papers if paper["pages"] is not None]
    abstracts = [paper["abstract_chars"] for paper in papers if paper["abstract_chars"] is not None]
    return {
        "pdf_pages": summarize(pages),
        "abstract_chars": summarize(abstracts),
    }


def flatten_diff(old: dict, new: dict, prefix: str) -> list[tuple[str, object, object]]:
    """对比新旧数值块，返回 (字段路径, 旧值, 新值) 差异列表。"""
    diffs = []
    for key in new:
        old_value = old.get(key)
        new_value = new[key]
        if isinstance(new_value, dict):
            diffs.extend(flatten_diff(old_value if isinstance(old_value, dict) else {}, new_value, f"{prefix}.{key}"))
        elif old_value != new_value:
            diffs.append((f"{prefix}.{key}", old_value, new_value))
    return diffs


def cmd_build_empirical(args: argparse.Namespace) -> int:
    """重算 empirical 统计；默认 dry-run 对比（有差异或提取失败退出码 1），--apply 才写回。"""
    corpus_root = resolve_corpus_root(args.corpus_root).resolve()
    if not corpus_root.is_dir():
        print(f"错误：语料根不存在: {corpus_root}")
        return 2
    manifest = load_manifest_argument(args.manifest) if args.manifest else None
    empirical_path = args.empirical.resolve()
    empirical = load_json(empirical_path)

    scanned, warnings = scan_placements(corpus_root, manifest)
    for warning in warnings:
        print(f"警告：{warning}")
    placements = [item for item in scanned if item["kind"] == "paper"]
    evidence_by_path = {}
    if manifest:
        for record in manifest.get("records", []):
            if record.get("kind") == "paper":
                evidence_by_path[record["path"]] = record["evidence_id"]
    analyzed = [analyze_paper(item, evidence_by_path) for item in placements]

    stars = [paper for paper in analyzed if paper["star"]]
    officials = [paper for paper in analyzed if not paper["star"]]
    failures = [paper for paper in analyzed if paper["abstract_chars"] is None]
    open_failures = [paper for paper in analyzed if paper["pages"] is None]

    all_pages = [paper["pages"] for paper in analyzed if paper["pages"] is not None]
    all_abstracts = [paper["abstract_chars"] for paper in analyzed if paper["abstract_chars"] is not None]
    new_dims = {
        "abstract_chars": summarize(all_abstracts),
        # 现库口径下 document_pages 与 pdf_pages 同源（均为 fitz 页数），保持一致。
        "document_pages": summarize(all_pages),
        "pdf_pages": summarize(all_pages),
    }
    years = sorted({item["year"] for item in placements if item["year"]})
    new_coverage = {
        "years": years,
        "papers": len(analyzed),
        "star_nominees": len(stars),
        "extraction_failures": len(failures),
        "abstract_extraction_coverage": len(all_abstracts),
    }
    new_groups = {}
    for name, group in (("overall", analyzed), ("star_nominees", stars), ("official_excellent", officials)):
        new_groups[name] = {"papers": len(group), "reliable_for_reference": group_stat_block(group)}

    diffs = []
    diffs += flatten_diff(empirical.get("dims", {}), new_dims, "dims")
    diffs += flatten_diff(empirical.get("coverage", {}), new_coverage, "coverage")
    if empirical.get("source", {}).get("papers") != len(analyzed):
        diffs.append(("source.papers", empirical.get("source", {}).get("papers"), len(analyzed)))
    for name, block in new_groups.items():
        old_group = empirical.get("groups", {}).get(name, {})
        if old_group.get("papers") != block["papers"]:
            diffs.append((f"groups.{name}.papers", old_group.get("papers"), block["papers"]))
        diffs += flatten_diff(old_group.get("reliable_for_reference", {}), block["reliable_for_reference"],
                              f"groups.{name}.reliable_for_reference")

    print(f"论文 {len(analyzed)} 篇（提名 {len(stars)}，优秀 {len(officials)}），"
          f"摘要提取成功 {len(all_abstracts)}，失败 {len(failures)}")
    for paper in failures:
        print(f"[extraction-failure] {paper['paper_id']}  {paper['path']}")
    if diffs:
        print(f"与 {empirical_path.name} 存在 {len(diffs)} 处数值差异：")
        print(f"{'字段':<52}{'旧值':>12}{'新值':>12}")
        for field, old_value, new_value in diffs:
            print(f"{field:<52}{str(old_value):>12}{str(new_value):>12}")
    else:
        print(f"重算结果与 {empirical_path.name} 的可比数值完全一致")

    if not args.apply:
        if diffs or failures:
            print("dry-run：存在上述差异/提取失败，退出码 1；未写回任何文件（--apply 才写回）")
            return 1
        print("dry-run：重算一致且无提取失败，退出码 0；未写回任何文件")
        return 0

    # --apply 防护：空语料属硬性防护；打开失败与论文数量漂移可由 --force-rebuild 显式跳过。
    hard_blockers: list[str] = []
    forceable_blockers: list[str] = []
    if not placements:
        hard_blockers.append("语料中没有可识别的论文文件，拒绝用空统计覆盖 empirical.json")
    if open_failures:
        forceable_blockers.append(f"{len(open_failures)} 篇论文 PDF 无法打开: "
                                  + ", ".join(paper["path"] for paper in open_failures))
    if manifest is not None:
        manifest_paper_records = sum(1 for record in manifest.get("records", []) if record.get("kind") == "paper")
        if len(placements) != manifest_paper_records:
            forceable_blockers.append(
                f"语料论文数 {len(placements)} 与 manifest 论文记录数 {manifest_paper_records} 不一致")
    if hard_blockers:
        for blocker in hard_blockers + forceable_blockers:
            print(f"[blocked] {blocker}")
        print("已阻止写回：空语料防护不可用 --force-rebuild 跳过")
        return 1
    if forceable_blockers and not args.force_rebuild:
        for blocker in forceable_blockers:
            print(f"[blocked] {blocker}")
        print("已阻止写回：修复上述问题，或使用 --force-rebuild 显式重建")
        return 1
    if forceable_blockers:
        print(f"--force-rebuild：跳过 {len(forceable_blockers)} 项防护继续写回")

    empirical["dims"] = new_dims
    empirical["coverage"] = new_coverage
    empirical.setdefault("source", {})["papers"] = len(analyzed)
    groups = empirical.setdefault("groups", {})
    for name, block in new_groups.items():
        groups.setdefault(name, {})
        groups[name]["papers"] = block["papers"]
        groups[name]["reliable_for_reference"] = block["reliable_for_reference"]
    # 临时文件 + 原子替换，避免写一半损坏现有 empirical.json。
    temp_path = empirical_path.with_suffix(empirical_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(empirical, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp_path, empirical_path)
    print(f"已写回 {empirical_path}（schema_version 与 scoring_policy 及 analysis_only 等其余字段保持不动）")
    return 0


# ------------------------------------------------------------ validate ----


def validate_annotations(annotations: dict, evidence_ids: set[str]) -> tuple[list[str], list[str]]:
    """校验 manual_review_annotations.json 的问号键覆盖、证据引用与绑定口径。

    问号键必须覆盖 Q1..Qn（n=len(question_dependency)）。缺键时若该题
    question_binding_scope=case_level（逐问绑定无鉴别力、按题级证据使用），
    降级为 WARN；question_level 缺键仍是 FAIL。
    """
    failures = []
    warns = []
    for case in annotations.get("cases", []):
        case_id = case.get("id", "<无id>")
        dependencies = case.get("question_dependency", [])
        if not dependencies:
            failures.append(f"manual_review_annotations.json#{case_id} question_dependency 为空")
        scope = case.get("question_binding_scope")
        question_ids = case.get("question_evidence_ids", {})
        expected = {f"Q{number}" for number in range(1, len(dependencies) + 1)}
        missing = sorted(expected - set(question_ids), key=lambda key: int(key[1:]))
        if missing:
            message = (f"manual_review_annotations.json#{case_id} question_evidence_ids 缺少问号键 "
                       f"{missing}（该题共 {len(dependencies)} 问）")
            if scope == "case_level":
                warns.append(message + "（case_level 逐问绑定无鉴别力，可按 case_level 降级豁免）")
            else:
                failures.append(message)
        for key in question_ids:
            match = QUESTION_KEY_PATTERN.fullmatch(key)
            number = int(key[1:]) if match else None
            # 规范形式校验：Q３（全角数字）虽能被宽松正则匹配，但属于 OCR 噪声键，
            # 会以非规范形式参与逐问绑定，按 v2 清理口径判 FAIL。
            if not match or key != f"Q{number}" or not 1 <= number <= len(dependencies):
                failures.append(
                    f"manual_review_annotations.json#{case_id} question_evidence_ids 噪声或越界键 "
                    f"{key!r}（该题共 {len(dependencies)} 问）")
        for field in ("source_evidence_id",):
            if case.get(field) and case[field] not in evidence_ids:
                failures.append(f"manual_review_annotations.json#{case_id} {field} 无法解析: {case[field]}")
        for field in ("evidence_ids", "star_evidence_ids"):
            for evidence_id in case.get(field, []):
                if evidence_id not in evidence_ids:
                    failures.append(f"manual_review_annotations.json#{case_id} {field} 无法解析: {evidence_id}")
        for key, ids in question_ids.items():
            if not ids:
                failures.append(f"manual_review_annotations.json#{case_id} question_evidence_ids[{key}] evidence 列表为空")
            for evidence_id in ids:
                if evidence_id not in evidence_ids:
                    failures.append(f"manual_review_annotations.json#{case_id} question_evidence_ids[{key}] 无法解析: {evidence_id}")
        if scope not in ("case_level", "question_level"):
            failures.append(
                f"manual_review_annotations.json#{case_id} question_binding_scope 缺失或非法: "
                f"{case.get('question_binding_scope')!r}")
    return failures, warns


def validate_paper_reviews(reviews: dict, manifest: dict) -> list[str]:
    """校验 manual_paper_reviews.json 的 33 篇齐全、记录身份一致与图表条目。

    深读层两届并存：2021 年 12 篇（star_nominee 提名）+ 2025 年 21 篇
    （official_excellent 优秀论文选）。paper_id 与 sha256 必须指向 manifest
    中同一条 kind=paper 且 award_tier 等于该届期望档位的记录，防止伪造 id
    复用其他记录的哈希。
    """
    failures = []
    papers = reviews.get("papers", [])
    expected_by_year = {2021: (12, "star_nominee"), 2025: (21, "official_excellent")}
    actual_by_year: dict[int, int] = {}
    for paper in papers:
        year = paper.get("year")
        actual_by_year[year] = actual_by_year.get(year, 0) + 1
    for year, (count, _tier) in sorted(expected_by_year.items()):
        actual = actual_by_year.pop(year, 0)
        if actual != count:
            failures.append(f"manual_paper_reviews.json {year} 届深读应为 {count} 篇，实际 {actual} 篇")
    for year, actual in sorted(actual_by_year.items(), key=lambda item: str(item[0])):
        failures.append(f"manual_paper_reviews.json 出现未声明届别的条目: year={year!r} 共 {actual} 篇")
    if len({paper.get("paper_id") for paper in papers}) != len(papers):
        failures.append("manual_paper_reviews.json 存在重复 paper_id")
    provenance = reviews.get("field_provenance")
    if not isinstance(provenance, dict) or not provenance:
        failures.append("manual_paper_reviews.json 缺少顶层 field_provenance 声明")
    paper_records_by_id = {record["evidence_id"]: record for record in manifest.get("records", [])
                           if record.get("kind") == "paper"}
    paper_records_by_sha = {record["sha256"]: record for record in manifest.get("records", [])
                            if record.get("kind") == "paper"}
    for paper in papers:
        paper_id = paper.get("paper_id", "<无paper_id>")
        record = paper_records_by_id.get(paper_id)
        if record is None:
            failures.append(f"manual_paper_reviews.json#{paper_id} paper_id 无法在 manifest 的论文记录中解析")
        else:
            expected_tier = expected_by_year.get(paper.get("year"), (0, None))[1]
            if record.get("award_tier") != expected_tier:
                failures.append(f"manual_paper_reviews.json#{paper_id} 对应 manifest 记录 award_tier "
                                f"非该届期望 {expected_tier!r}: {record.get('award_tier')!r}")
            if paper_records_by_sha.get(paper.get("sha256")) is not record:
                failures.append(f"manual_paper_reviews.json#{paper_id} paper_id 与 sha256 "
                                f"未指向同一条 manifest 论文记录")
        logic = paper.get("figure_table_logic")
        if not logic:
            failures.append(f"manual_paper_reviews.json#{paper_id} figure_table_logic 为空")
            continue
        for index, item in enumerate(logic):
            location = f"manual_paper_reviews.json#{paper_id} figure_table_logic[{index}]"
            if not str(item.get("caption", "")).strip():
                failures.append(f"{location} caption 为空")
            if not str(item.get("kind", "")).strip():
                failures.append(f"{location} kind 为空")
            page = item.get("page")
            if not isinstance(page, int) or isinstance(page, bool) or page <= 0:
                failures.append(f"{location} page 非正整数: {page!r}")
    return failures


def validate_cross_file_consistency(annotations: dict, index: dict) -> list[str]:
    """标注与索引的 case id 集合必须一致，且两个案例表都不允许为空。"""
    failures = []
    annotation_ids = [case.get("id") for case in annotations.get("cases", [])]
    index_ids = [case.get("id") for case in index.get("cases", [])]
    if not annotation_ids:
        failures.append("manual_review_annotations.json cases 为空")
    if not index_ids:
        failures.append("cases/index.json cases 为空")
    only_annotations = sorted(set(annotation_ids) - set(index_ids))
    only_index = sorted(set(index_ids) - set(annotation_ids))
    if only_annotations:
        failures.append(f"manual_review_annotations.json 有而 cases/index.json 缺少的 case id: {only_annotations}")
    if only_index:
        failures.append(f"cases/index.json 有而 manual_review_annotations.json 缺少的 case id: {only_index}")
    return failures


def validate_case_index(index: dict) -> list[str]:
    """校验 cases/index.json 每题标题非空且不以中文冒号结尾。"""
    failures = []
    for case in index.get("cases", []):
        case_id = case.get("id", "<无id>")
        title = case.get("title")
        if not isinstance(title, str) or not title.strip():
            failures.append(f"cases/index.json#{case_id} title 为空")
        elif title.rstrip().endswith("："):
            failures.append(f"cases/index.json#{case_id} title 以中文冒号结尾: {title!r}")
    return failures


def cmd_validate(args: argparse.Namespace) -> int:
    """校验人工层三个 JSON 的完整性，任一 FAIL 退出码 1。"""
    knowledge_root = args.knowledge_root.resolve()
    try:
        manifest = load_json(knowledge_root / "source_manifest.json")
        annotations = load_json(knowledge_root / "cases" / "manual_review_annotations.json")
        reviews = load_json(knowledge_root / "papers" / "manual_paper_reviews.json")
        index = load_json(knowledge_root / "cases" / "index.json")
    except FileNotFoundError as exc:
        print(f"[FAIL] {exc}")
        return 1
    for record in manifest.get("records", []):
        if "evidence_id" not in record or "sha256" not in record:
            raise KeyError(f"manifest 记录缺少 evidence_id/sha256 字段: "
                           f"{json.dumps(record, ensure_ascii=False)[:200]}")
    evidence_ids = {record["evidence_id"] for record in manifest.get("records", [])}

    annotation_failures, annotation_warns = validate_annotations(annotations, evidence_ids)
    failures = []
    failures += annotation_failures
    failures += validate_paper_reviews(reviews, manifest)
    failures += validate_case_index(index)
    failures += validate_cross_file_consistency(annotations, index)

    for warn in annotation_warns:
        print(f"[WARN] {warn}")
    for item in failures:
        print(f"[FAIL] {item}")
    if failures:
        print(f"校验失败：{len(failures)} 处（另有 {len(annotation_warns)} 处 WARN）")
        return 1
    case_count = len(annotations.get("cases", []))
    review_count = len(reviews.get("papers", []))
    suffix = f"，另有 {len(annotation_warns)} 处 WARN" if annotation_warns else ""
    print(f"校验通过：{case_count} 题标注、{review_count} 篇论文深读与案例索引均与 manifest 一致"
          f"（manifest 证据 {len(evidence_ids)} 条{suffix}）")
    return 0


# --------------------------------------------------------------- main ----


def build_parser() -> argparse.ArgumentParser:
    """构造子命令解析器。"""
    parser = argparse.ArgumentParser(description="华为杯语料蒸馏的可复现校验流水线")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="扫描语料根输出清单预览")
    scan_parser.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    scan_parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST),
                             help="分类底册路径，传 none 禁用（默认用 skill 内 source_manifest.json）")
    scan_parser.set_defaults(handler=cmd_scan)

    verify_parser = subparsers.add_parser("verify-manifest", help="重算 manifest 哈希并报告漂移")
    verify_parser.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    verify_parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    verify_parser.set_defaults(handler=cmd_verify_manifest)

    empirical_parser = subparsers.add_parser("build-empirical", help="重算统计并对比/写回 empirical.json")
    empirical_parser.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    empirical_parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    empirical_parser.add_argument("--empirical", type=Path, default=DEFAULT_EMPIRICAL)
    empirical_parser.add_argument("--apply", action="store_true", help="写回 empirical.json（默认只对比）")
    empirical_parser.add_argument("--force-rebuild", action="store_true",
                                  help="跳过打开失败/论文数量一致性防护强制写回（空语料防护不可跳过）")
    empirical_parser.set_defaults(handler=cmd_build_empirical)

    validate_parser = subparsers.add_parser("validate", help="人工层完整性校验")
    validate_parser.add_argument("--knowledge-root", type=Path, default=COMP_ROOT)
    validate_parser.set_defaults(handler=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    """命令入口，按子命令分发并返回退出码。

    输入类错误（文件缺失/损坏、manifest 字段不全、类型不符）统一转退出码 2，
    避免以回溯或退出码 1（发现类）混淆输入错误。
    """
    ensure_utf8_stdout()
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except KeyError as exc:
        # str(KeyError) 返回参数的 repr，引号会被转义，这里取原始消息。
        detail = exc.args[0] if exc.args else str(exc)
        print(f"错误：KeyError: {detail}")
        return 2
    except (OSError, TypeError, ValueError) as exc:
        print(f"错误：{type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
