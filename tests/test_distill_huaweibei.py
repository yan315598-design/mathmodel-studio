"""华为杯蒸馏流水线脚本（scripts/distill_huaweibei_cases.py）的合成语料测试。

全部 fixture 在 tmp_path 内用 fitz 现场生成，不依赖真实语料目录。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import fitz
import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "distill_huaweibei_cases.py"


def load_module():
    """加载待测脚本模块。"""
    spec = importlib.util.spec_from_file_location("distill_huaweibei_cases", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_paper_pdf(path: Path, abstract_body: str, pages: int = 1) -> None:
    """生成首页带"摘 要……关键词"文本的小 PDF，其余页留白。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    first = document.new_page()
    first.insert_text((72, 72), "摘  要", fontname="china-s", fontsize=12)
    first.insert_text((72, 96), abstract_body, fontname="china-s", fontsize=12)
    first.insert_text((72, 120), "关键词：测试；拟合", fontname="china-s", fontsize=12)
    for _ in range(pages - 1):
        document.new_page()
    document.save(path)
    document.close()


def run_module(argv: list[str], capsys):
    """以 CLI 参数调用脚本 main 并返回 (退出码, 合并输出)。"""
    module = load_module()
    code = module.main(argv)
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def digest_of(path: Path) -> str:
    """fixture 专用哈希（文件都很小，直接整读）。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------ 分位数 ----


def test_percentile_linear_interpolation():
    """手算对照：n=4 时 (n-1)*p 非整数需要 floor/ceil 线性插值。"""
    module = load_module()
    values = [10.0, 20.0, 30.0, 40.0]
    assert module.percentile(values, 0.25) == pytest.approx(17.5)   # 10 + 0.75*(20-10)
    assert module.percentile(values, 0.5) == pytest.approx(25.0)    # 20 + 0.5*(30-20)
    assert module.percentile(values, 0.75) == pytest.approx(32.5)   # 30 + 0.25*(40-30)
    assert module.percentile([7.0], 0.9) == 7.0
    with pytest.raises(ValueError):
        module.percentile([], 0.5)


def test_summarize_block_matches_manual_computation():
    """summarize 输出 n/min/p25/p50/p75/max/mean，均值保留 4 位小数。"""
    module = load_module()
    stats = module.summarize([2, 3, 4, 5])
    assert stats == {"n": 4, "min": 2.0, "p25": 2.75, "p50": 3.5, "p75": 4.25, "max": 5.0, "mean": 3.5}
    assert module.summarize([])["n"] == 0


# ------------------------------------------------- 摘要口径（major 5）----


def test_extract_abstract_chars_marker_variants():
    """摘要口径：头标记须在行首且可跨行，尾标记接受关键词/关键字，空白全部剔除。"""
    module = load_module()
    assert module.extract_abstract_chars("摘  要：\n本文  建立 模型。\n关键词：拟合") == 7   # 本文建立模型。
    assert module.extract_abstract_chars("摘\n要\n全文综述与评价。\n关键字：拟合") == 8     # 全文综述与评价。
    assert module.extract_abstract_chars("正文没有摘要标记。") is None
    assert module.extract_abstract_chars("摘要只有开头没有结尾。") is None


def test_extract_abstract_chars_ignores_inline_mentions():
    """正文句中提到"摘要/关键词"不得触发头标记或提前截断尾标记。"""
    module = load_module()
    # "摘要"在句中而非行首：不应识别出摘要段。
    assert module.extract_abstract_chars("正文提到摘要：这里不是摘要。关键字：foo") is None
    # 行中"关键词"不是尾标记，只有行首的"关键词"才截断。
    text = "摘 要：\n本文建立模型。\n文中提到关键词不应截断。\n关键词：拟合"
    assert module.extract_abstract_chars(text) == 19   # 本文建立模型。+ 文中提到关键词不应截断。


# ------------------------------------------------------ build-empirical ----


PAPER_RELS = [
    "2021年中国研究生数学建模竞赛优秀论文/A/A21100001.pdf",
    "2021年中国研究生数学建模竞赛优秀论文/A/A21100002.pdf",
    "2021年中国研究生数学建模竞赛优秀论文/获数模之星提名奖（12篇）/A21100003.pdf",
    "2021年中国研究生数学建模竞赛优秀论文/获数模之星提名奖（12篇）/A21100004.pdf",
]


def build_empirical_corpus(root: Path, include_bad: bool = True) -> Path:
    """构造 4 篇可解析论文（2 优秀 + 2 提名）的迷你语料，可选附加一个损坏 PDF。

    摘要体用重复字符书写，长度无歧义：优秀组 [8, 20]，提名组 [12, 18]。
    页数：优秀组 [2, 4]，提名组 [3, 5]。
    """
    excellent = root / "2021年中国研究生数学建模竞赛优秀论文"
    write_paper_pdf(excellent / "A" / "A21100001.pdf", "甲" * 8, pages=2)
    write_paper_pdf(excellent / "A" / "A21100002.pdf", "乙" * 20, pages=4)
    star_dir = excellent / "获数模之星提名奖（12篇）"
    write_paper_pdf(star_dir / "A21100003.pdf", "丙" * 12, pages=3)
    write_paper_pdf(star_dir / "A21100004.pdf", "丁" * 18, pages=5)
    if include_bad:
        # 损坏 PDF：计入提取失败与论文总数，但不参与页数与摘要统计。
        bad = excellent / "A" / "A21100009.pdf"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"not a pdf")
    return root


def stub_empirical_payload() -> dict:
    """与真实 empirical.json 同构、数值全错的占位文件。"""
    bogus = {"n": 1, "min": 1.0, "p25": 1.0, "p50": 1.0, "p75": 1.0, "max": 1.0, "mean": 1.0}
    group = {"papers": 1, "reliable_for_reference": {"pdf_pages": dict(bogus), "abstract_chars": dict(bogus)},
             "analysis_only": {"headings_detected": dict(bogus)}}
    return {
        "schema_version": "huaweibei-empirical-analysis-1.0",
        "competition": "huaweibei",
        "source": {"status": "empirical_local_2021_2025", "papers": 99, "note": "占位"},
        "dims": {"abstract_chars": dict(bogus), "document_pages": dict(bogus), "pdf_pages": dict(bogus)},
        "coverage": {"years": [2019], "papers": 99, "star_nominees": 99,
                     "extraction_failures": 99, "abstract_extraction_coverage": 99},
        "groups": {"overall": json.loads(json.dumps(group)),
                   "star_nominees": json.loads(json.dumps(group)),
                   "official_excellent": json.loads(json.dumps(group))},
        "scoring_policy": {"allowed_reference_metrics": ["pdf_pages"], "reason": "占位，--apply 不得改动"},
    }


def write_stub_empirical(path: Path) -> None:
    """写入占位 empirical.json 并返回其文本，便于断言未被改动。"""
    path.write_text(json.dumps(stub_empirical_payload(), ensure_ascii=False), encoding="utf-8")


def paper_manifest(corpus: Path, rels: list[str], award_tiers: dict[str, str | None] | None = None) -> dict:
    """为指定论文路径生成 manifest；award_tiers 里值为 None 表示省略该字段。"""
    award_tiers = award_tiers or {}
    records = []
    for rel in rels:
        record = {"evidence_id": f"graduate:paper:2021-A:{digest_of(corpus / rel)[:12]}",
                  "path": rel, "kind": "paper", "sha256": digest_of(corpus / rel)}
        award = award_tiers.get(rel, "star_nominee")
        if award is not None:
            record["award_tier"] = award
        records.append(record)
    return {"schema_version": "graduate-corpus-1.0", "records": records,
            "inventory": [{"path": r["path"], "kind": "paper"} for r in records],
            "failures": [], "exact_duplicate_groups": {}}


def test_build_empirical_dry_run_flags_stale_state(tmp_path, capsys):
    """[major 1] 脏 empirical/存在提取失败时 dry-run 退出码 1，且不写文件。"""
    module = load_module()
    corpus = build_empirical_corpus(tmp_path / "corpus", include_bad=True)
    empirical_path = tmp_path / "empirical.json"
    write_stub_empirical(empirical_path)
    before = empirical_path.read_text(encoding="utf-8")

    code, output = run_module(
        ["build-empirical", "--corpus-root", str(corpus), "--manifest", "none",
         "--empirical", str(empirical_path)], capsys)

    assert code == 1
    assert "dry-run" in output and "退出码 1" in output
    assert empirical_path.read_text(encoding="utf-8") == before
    assert "A21100009.pdf" in output and "extraction-failure" in output
    assert "论文 5 篇（提名 2，优秀 3）" in output
    # overall 页数 [2,3,4,5]：p25=2.75 p50=3.5 p75=4.25；提名摘要 [12,18]：p50=15.0；
    # 优秀摘要 [8,20]：p25=11.0 p50=14.0 mean=14.0
    assert module.summarize([2, 3, 4, 5])["p25"] == 2.75
    assert module.summarize([12, 18]) == {"n": 2, "min": 12.0, "p25": 13.5, "p50": 15.0,
                                          "p75": 16.5, "max": 18.0, "mean": 15.0}
    assert module.summarize([8, 20])["p25"] == 11.0
    assert "3.5" in output and "15.0" in output and "14.0" in output


def test_build_empirical_apply_updates_only_numeric_layers(tmp_path, capsys):
    """--apply 只更新数值层；随后 dry-run 干净语料退出码 0；不留 .tmp 残留。"""
    corpus = build_empirical_corpus(tmp_path / "corpus", include_bad=False)
    empirical_path = tmp_path / "empirical.json"
    write_stub_empirical(empirical_path)

    code, output = run_module(
        ["build-empirical", "--corpus-root", str(corpus), "--manifest", "none",
         "--empirical", str(empirical_path), "--apply"], capsys)
    assert code == 0
    assert "已写回" in output
    assert not list(tmp_path.rglob("*.tmp"))

    updated = json.loads(empirical_path.read_text(encoding="utf-8"))
    assert updated["schema_version"] == "huaweibei-empirical-analysis-1.0"
    assert updated["scoring_policy"]["reason"] == "占位，--apply 不得改动"
    assert updated["source"]["papers"] == 4
    assert updated["coverage"] == {"years": [2021], "papers": 4, "star_nominees": 2,
                                   "extraction_failures": 0, "abstract_extraction_coverage": 4}
    assert updated["dims"]["pdf_pages"]["p50"] == 3.5
    assert updated["dims"]["document_pages"] == updated["dims"]["pdf_pages"]
    assert updated["dims"]["abstract_chars"]["p50"] == 15.0
    assert updated["groups"]["overall"]["papers"] == 4
    assert updated["groups"]["star_nominees"]["papers"] == 2
    assert updated["groups"]["star_nominees"]["reliable_for_reference"]["abstract_chars"]["p25"] == 13.5
    assert updated["groups"]["official_excellent"]["papers"] == 2
    # 未重算的字段原样保留
    assert updated["groups"]["overall"]["analysis_only"]["headings_detected"]["n"] == 1

    code, output = run_module(
        ["build-empirical", "--corpus-root", str(corpus), "--manifest", "none",
         "--empirical", str(empirical_path)], capsys)
    assert code == 0
    assert "重算一致且无提取失败，退出码 0" in output


def test_build_empirical_apply_blocked_by_open_failure(tmp_path, capsys):
    """[major 2] PDF 打不开时 --apply 被阻止且文件不变；--force-rebuild 可显式跳过。"""
    corpus = build_empirical_corpus(tmp_path / "corpus", include_bad=True)
    empirical_path = tmp_path / "empirical.json"
    write_stub_empirical(empirical_path)
    before = empirical_path.read_text(encoding="utf-8")

    code, output = run_module(
        ["build-empirical", "--corpus-root", str(corpus), "--manifest", "none",
         "--empirical", str(empirical_path), "--apply"], capsys)
    assert code == 1
    assert "[blocked] 1 篇论文 PDF 无法打开" in output
    assert "A21100009.pdf" in output
    assert empirical_path.read_text(encoding="utf-8") == before

    code, output = run_module(
        ["build-empirical", "--corpus-root", str(corpus), "--manifest", "none",
         "--empirical", str(empirical_path), "--apply", "--force-rebuild"], capsys)
    assert code == 0
    assert "--force-rebuild：跳过" in output and "已写回" in output
    updated = json.loads(empirical_path.read_text(encoding="utf-8"))
    assert updated["coverage"]["extraction_failures"] == 1
    assert not list(tmp_path.rglob("*.tmp"))


def test_build_empirical_apply_blocked_by_manifest_count_mismatch(tmp_path, capsys):
    """[major 2] 语料论文数与 manifest 论文记录数不一致时阻止写回，--force-rebuild 放行。"""
    corpus = build_empirical_corpus(tmp_path / "corpus", include_bad=False)
    manifest_path = tmp_path / "source_manifest.json"
    manifest_path.write_text(json.dumps(paper_manifest(corpus, PAPER_RELS[:2]), ensure_ascii=False),
                             encoding="utf-8")
    empirical_path = tmp_path / "empirical.json"
    write_stub_empirical(empirical_path)
    before = empirical_path.read_text(encoding="utf-8")

    code, output = run_module(
        ["build-empirical", "--corpus-root", str(corpus), "--manifest", str(manifest_path),
         "--empirical", str(empirical_path), "--apply"], capsys)
    assert code == 1
    assert "语料论文数 4 与 manifest 论文记录数 2 不一致" in output
    assert empirical_path.read_text(encoding="utf-8") == before

    code, output = run_module(
        ["build-empirical", "--corpus-root", str(corpus), "--manifest", str(manifest_path),
         "--empirical", str(empirical_path), "--apply", "--force-rebuild"], capsys)
    assert code == 0
    assert json.loads(empirical_path.read_text(encoding="utf-8"))["coverage"]["papers"] == 4


def test_star_classification_prefers_manifest_award_tier(tmp_path, capsys):
    """[minor 2] 提名身份优先取 manifest award_tier，路径含"提名"只作兜底。"""
    corpus = build_empirical_corpus(tmp_path / "corpus", include_bad=False)
    tiers = {
        PAPER_RELS[0]: "star_nominee",           # 普通路径但 manifest 标记提名 -> 计入提名
        PAPER_RELS[1]: "official_excellent",
        PAPER_RELS[2]: None,                      # 无 award_tier -> 回退路径启发式（提名目录）-> 提名
        PAPER_RELS[3]: "official_excellent",      # 提名目录但 manifest 标记优秀 -> 不计提名
    }
    manifest_path = tmp_path / "source_manifest.json"
    manifest_path.write_text(json.dumps(paper_manifest(corpus, PAPER_RELS, tiers), ensure_ascii=False),
                             encoding="utf-8")
    empirical_path = tmp_path / "empirical.json"
    write_stub_empirical(empirical_path)

    code, output = run_module(
        ["build-empirical", "--corpus-root", str(corpus), "--manifest", str(manifest_path),
         "--empirical", str(empirical_path)], capsys)
    assert code == 1   # 占位 empirical 必有差异；这里只关心分组计数
    assert "论文 4 篇（提名 2，优秀 2）" in output


# ------------------------------------------------- 目录推断（minor 1）----


def test_infer_placement_year_from_nested_dirs():
    """[minor 1] 顶层目录无年份时逐级搜索目录组件；多候选年份报冲突。"""
    module = load_module()
    placement = module.infer_placement("优秀论文/2021/A/A00001.pdf")
    assert placement["kind"] == "paper"
    assert placement["year"] == 2021
    assert placement["problem"] == "A"
    assert placement["year_conflict"] is None
    conflicted = module.infer_placement("优秀论文/2021/2022/A00001.pdf")
    assert conflicted["year"] == 2021
    assert conflicted["year_conflict"] == [2021, 2022]
    # 附件数据里的内容年份（如年鉴目录）不构成候选，不触发冲突。
    data = module.infer_placement("2022年中国研究生数学建模竞赛赛题/2022年E题/数据集/2017年鉴/a.doc")
    assert data["year"] == 2022
    assert data["year_conflict"] is None


# ----------------------------------------------------- verify-manifest ----


def build_verify_corpus(root: Path) -> Path:
    """两文件迷你语料：一篇论文 PDF + 一份赛题 docx。"""
    write_paper_pdf(root / "2021年中国研究生数学建模竞赛优秀论文" / "A" / "A21100001.pdf", "摘要正文。")
    statement = root / "2021年中国研究生数学建模竞赛赛题" / "2021年A题" / "相关矩阵题面.docx"
    statement.parent.mkdir(parents=True, exist_ok=True)
    statement.write_text("题面内容", encoding="utf-8")
    return root


def manifest_payload(corpus: Path) -> dict:
    """为迷你语料生成哈希正确的 manifest。"""
    paper_rel = "2021年中国研究生数学建模竞赛优秀论文/A/A21100001.pdf"
    statement_rel = "2021年中国研究生数学建模竞赛赛题/2021年A题/相关矩阵题面.docx"
    records = []
    for rel, kind in ((paper_rel, "paper"), (statement_rel, "problem_statement")):
        digest = digest_of(corpus / rel)
        records.append({"evidence_id": f"graduate:{kind}:2021-A:{digest[:12]}", "path": rel, "kind": kind,
                        "sha256": digest, "size_bytes": (corpus / rel).stat().st_size})
    inventory = [{"path": record["path"], "kind": record["kind"]} for record in records]
    return {"schema_version": "graduate-corpus-1.0", "records": records, "inventory": inventory,
            "failures": [], "exact_duplicate_groups": {}}


def test_verify_manifest_clean_then_drift(tmp_path, capsys):
    """哈希一致时退出码 0；改动/缺失/新增三类漂移都能检出且退出码 1。"""
    corpus = build_verify_corpus(tmp_path / "corpus")
    manifest_path = tmp_path / "source_manifest.json"
    manifest_path.write_text(json.dumps(manifest_payload(corpus), ensure_ascii=False), encoding="utf-8")

    code, output = run_module(
        ["verify-manifest", "--corpus-root", str(corpus), "--manifest", str(manifest_path)], capsys)
    assert code == 0
    assert "一致" in output

    paper = corpus / "2021年中国研究生数学建模竞赛优秀论文" / "A" / "A21100001.pdf"
    paper.write_bytes(paper.read_bytes() + b"tampered")
    (corpus / "2021年中国研究生数学建模竞赛赛题" / "2021年A题" / "相关矩阵题面.docx").unlink()
    write_paper_pdf(corpus / "2021年中国研究生数学建模竞赛优秀论文" / "A" / "A21100002.pdf", "新增论文。")

    code, output = run_module(
        ["verify-manifest", "--corpus-root", str(corpus), "--manifest", str(manifest_path)], capsys)
    assert code == 1
    assert "[changed] 2021年中国研究生数学建模竞赛优秀论文/A/A21100001.pdf" in output
    assert "[missing] 2021年中国研究生数学建模竞赛赛题/2021年A题/相关矩阵题面.docx" in output
    assert "A21100002.pdf" in output and "unregistered" in output


def test_input_errors_return_exit_code_two(tmp_path, capsys):
    """[major 6] JSON 损坏/字段缺失等输入错误统一退出码 2 并给出可读消息。"""
    corpus = build_verify_corpus(tmp_path / "corpus")

    binary = tmp_path / "binary_manifest.json"
    binary.write_bytes(b"\xff\xfe\x00bogus")
    code, output = run_module(
        ["verify-manifest", "--corpus-root", str(corpus), "--manifest", str(binary)], capsys)
    assert code == 2
    assert "JSON 解析失败" in output and str(binary) in output

    broken = json.loads(json.dumps(manifest_payload(corpus)))
    del broken["records"][0]["sha256"]
    fieldless = tmp_path / "fieldless_manifest.json"
    fieldless.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
    code, output = run_module(
        ["verify-manifest", "--corpus-root", str(corpus), "--manifest", str(fieldless)], capsys)
    assert code == 2
    assert "缺少字段 'sha256'" in output

    root = build_knowledge_root(tmp_path / "knowledge", dirty=False)
    manifest_path = root / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["records"][0]["evidence_id"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    code, output = run_module(["validate", "--knowledge-root", str(root)], capsys)
    assert code == 2
    assert "evidence_id" in output


# ----------------------------------------------------------- validate ----


def build_knowledge_root(root: Path, dirty: bool, warn_case: bool = False) -> Path:
    """构造 validate 所需的迷你知识库（manifest + 标注 + 深读 + 索引）。

    dirty=True 注入各类缺陷；warn_case=True 在干净基线上追加一个
    case_level 且缺 Q2 的案例（应降级为 WARN 而非 FAIL）。
    """
    root.mkdir(parents=True)
    paper_records = []
    for index in range(12):
        # 前 12 位 hex 保持唯一，evidence_id 与 sha256 引用才不会撞车。
        sha = f"{index:012x}" + "0" * 52
        paper_records.append({
            "evidence_id": f"graduate:paper:2021-A:{sha[:12]}",
            "path": f"2021年中国研究生数学建模竞赛优秀论文/A/A21100{index:02d}.pdf",
            "kind": "paper", "award_tier": "official_excellent", "year": 2021, "problem": "A",
            "sha256": sha, "size_bytes": 100, "extension": ".pdf",
        })
    if dirty:
        # 深读条目 2 对应的 manifest 记录不是提名，用于触发 award_tier 校验。
        paper_records[2]["award_tier"] = "official_excellent"
    else:
        for record in paper_records:
            record["award_tier"] = "star_nominee"
    # v2.2.0 起深读层两届并存：再补 21 篇 2025 优秀论文选记录（前缀从 20 起
    # 避开 2021 块的 0-11），clean/dirty 两种模式 tier 均为官方档。
    for index in range(20, 41):
        sha = f"{index:012x}" + "0" * 52
        paper_records.append({
            "evidence_id": f"graduate:paper:2025-B:{sha[:12]}",
            "path": f"2025年研究生数学建模竞赛优秀论文选/B题优秀论文/B题-{index:02d}.pdf",
            "kind": "paper", "award_tier": "official_excellent", "year": 2025, "problem": "B",
            "sha256": sha, "size_bytes": 100, "extension": ".pdf",
        })
    problem_record = {
        "evidence_id": "graduate:problem_statement:2021-A:aaaaaaaaaaaa",
        "path": "2021年中国研究生数学建模竞赛赛题/2021年A题/题目.docx", "kind": "problem_statement",
        "sha256": "b" * 64,
    }
    manifest = {"schema_version": "graduate-corpus-1.0", "records": paper_records + [problem_record],
                "inventory": [], "failures": [], "exact_duplicate_groups": {}}
    (root / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    good_paper_id = paper_records[0]["evidence_id"]
    cases = []
    if dirty:
        cases.append({
            "id": "huaweibei_2021_BAD1",
            "question_dependency": ["Q1", "Q2", "Q3"],
            "question_evidence_ids": {"Q1": [good_paper_id], "Q三四": [good_paper_id], "Q9": [good_paper_id]},
            "evidence_ids": [good_paper_id], "star_evidence_ids": [good_paper_id],
            "source_evidence_id": problem_record["evidence_id"],
            "question_binding_scope": "question_level",
        })
        cases.append({
            "id": "huaweibei_2021_BAD2",
            "question_dependency": ["Q1", "Q2"],
            "question_evidence_ids": {"Q1": ["graduate:paper:2021-A:deadbeefdead"], "Q2": []},
            "evidence_ids": [], "star_evidence_ids": [],
            "source_evidence_id": problem_record["evidence_id"],
        })
    cases.append({
        "id": "huaweibei_2021_A",
        "question_dependency": ["Q1", "Q2"],
        "question_evidence_ids": {"Q1": [good_paper_id], "Q2": [good_paper_id]},
        "evidence_ids": [good_paper_id], "star_evidence_ids": [good_paper_id],
        "source_evidence_id": problem_record["evidence_id"],
        "question_binding_scope": "case_level",
    })
    if warn_case:
        cases.append({
            "id": "huaweibei_2021_WARN",
            "question_dependency": ["Q1", "Q2"],
            "question_evidence_ids": {"Q1": [good_paper_id]},
            "evidence_ids": [good_paper_id], "star_evidence_ids": [good_paper_id],
            "source_evidence_id": problem_record["evidence_id"],
            "question_binding_scope": "case_level",
        })
    annotations = {"schema_version": "huaweibei-manual-cases-1.0", "cases": cases}
    (root / "cases").mkdir(parents=True)
    (root / "cases" / "manual_review_annotations.json").write_text(
        json.dumps(annotations, ensure_ascii=False), encoding="utf-8")

    papers = []
    for index, record in enumerate(paper_records):
        # dirty 注入只命中 index 0-6（均属 2021 块），2025 块保持干净。
        entry = {
            "paper_id": record["evidence_id"],
            "year": record["year"],
            "sha256": record["sha256"],
            "figure_table_logic": [{"page": 1, "kind": "figure", "caption": "技术路线图"}],
        }
        if dirty:
            if index == 0:
                entry["figure_table_logic"].append({"page": 0, "kind": "figure", "caption": "  "})
            elif index == 1:
                entry["sha256"] = "f" * 64                       # 哈希指向不存在的记录
            elif index == 3:
                entry["sha256"] = paper_records[4]["sha256"]     # paper_id 与 sha256 指向不同记录
            elif index == 4:
                entry["figure_table_logic"] = []                  # 图表条目为空
            elif index == 5:
                entry["figure_table_logic"] = [{"page": 2, "kind": "  ", "caption": "空类型"}]
            elif index == 6:
                entry["paper_id"] = "graduate:paper:2021-Z:000000000000"   # 不存在的 paper_id
        papers.append(entry)
    reviews = {"schema_version": "huaweibei-manual-stars-1.0", "papers": papers,
               "field_provenance": {"manually_reviewed": ["figure_table_logic.caption"]}}
    if dirty:
        reviews.pop("field_provenance")
    (root / "papers").mkdir()
    (root / "papers" / "manual_paper_reviews.json").write_text(
        json.dumps(reviews, ensure_ascii=False), encoding="utf-8")

    index_cases = [{"id": "huaweibei_2021_A", "title": "相关矩阵组的低复杂度计算和存储建模"}]
    if dirty:
        index_cases.append({"id": "huaweibei_2021_BAD1", "title": "坏标题："})
        index_cases.append({"id": "huaweibei_2021_BAD2", "title": "   "})
        index_cases.append({"id": "huaweibei_2021_GHOST", "title": "索引独有 id"})
    if warn_case:
        index_cases.append({"id": "huaweibei_2021_WARN", "title": "缺逐问键的案例"})
    (root / "cases" / "index.json").write_text(
        json.dumps({"schema_version": "huaweibei-cases-1.0", "cases": index_cases}, ensure_ascii=False),
        encoding="utf-8")
    return root


def test_validate_detects_noise_keys_and_bad_titles(tmp_path, capsys):
    """噪声/越界/缺失问号键、坏引用、坏深读与坏标题都会被判 FAIL。"""
    root = build_knowledge_root(tmp_path / "knowledge", dirty=True)
    code, output = run_module(["validate", "--knowledge-root", str(root)], capsys)
    assert code == 1
    # 问号键类 [major 3]
    assert "Q三四" in output
    assert "Q9" in output
    assert "缺少问号键 ['Q2', 'Q3']" in output          # question_level 缺键是 FAIL
    assert "evidence 列表为空" in output
    assert "deadbeefdead" in output
    assert "question_binding_scope" in output
    # 深读记录身份类 [major 4]
    assert "paper_id 无法在 manifest 的论文记录中解析" in output
    assert "未指向同一条 manifest 论文记录" in output
    assert "award_tier 非该届期望 'star_nominee'" in output
    assert "figure_table_logic 为空" in output
    assert "kind 为空" in output
    assert "caption 为空" in output
    assert "page 非正整数" in output
    assert "field_provenance" in output
    # 索引与跨文件一致性 [minor 3]
    assert "以中文冒号结尾" in output
    assert "title 为空" in output
    assert "有而 manual_review_annotations.json 缺少的 case id: ['huaweibei_2021_GHOST']" in output


def test_validate_clean_fixture_passes(tmp_path, capsys):
    """干净 fixture 下 validate 退出码 0。"""
    root = build_knowledge_root(tmp_path / "knowledge", dirty=False)
    code, output = run_module(["validate", "--knowledge-root", str(root)], capsys)
    assert code == 0
    assert "校验通过" in output
    assert "[WARN]" not in output and "[FAIL]" not in output


def test_validate_case_level_missing_questions_warns_not_fails(tmp_path, capsys):
    """[major 3] case_level 缺问号键降级为 WARN，不导致退出码 1。"""
    root = build_knowledge_root(tmp_path / "knowledge", dirty=False, warn_case=True)
    code, output = run_module(["validate", "--knowledge-root", str(root)], capsys)
    assert code == 0
    assert "[WARN] manual_review_annotations.json#huaweibei_2021_WARN question_evidence_ids 缺少问号键 ['Q2']" in output
    assert "可按 case_level 降级豁免" in output
    assert "[FAIL]" not in output


def test_validate_empty_annotation_cases_fail(tmp_path, capsys):
    """[minor 3] 标注案例表为空属于 FAIL，同时触发与索引的 id 集合不一致。"""
    root = build_knowledge_root(tmp_path / "knowledge", dirty=False)
    annotations_path = root / "cases" / "manual_review_annotations.json"
    annotations_path.write_text(json.dumps({"schema_version": "x", "cases": []}, ensure_ascii=False),
                                encoding="utf-8")
    code, output = run_module(["validate", "--knowledge-root", str(root)], capsys)
    assert code == 1
    assert "manual_review_annotations.json cases 为空" in output
    assert "有而 manual_review_annotations.json 缺少的 case id" in output


# ------------------------------------------------------------- CLI ----


def test_cli_help_available():
    """--help 可用（子进程真跑一遍 CLI 入口）。"""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--help"],
        capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
        timeout=60,
    )
    assert result.returncode == 0
    assert "scan" in result.stdout and "verify-manifest" in result.stdout
    assert "build-empirical" in result.stdout and "validate" in result.stdout
