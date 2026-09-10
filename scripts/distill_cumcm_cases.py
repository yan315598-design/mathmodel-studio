"""从国赛论文与题面语料生成可追溯的逐题案例索引。

脚本把原文和 OCR 文本留在外部语料目录，只把模型、验证、图表、任务标签与
来源哈希写入 skill，避免保存大段论文原文。
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import fitz


MODEL_PATTERNS = {
    "线性规划": r"线性规划|LP模型",
    "整数规划": r"整数规划|混合整数|0[-－]?1规划|二进制规划|MILP",
    "多目标优化": r"多目标|帕累托|Pareto|NSGA",
    "动态规划": r"动态规划|Bellman",
    "非线性规划": r"非线性规划|非凸优化|序列二次规划|SQP",
    "遗传算法": r"遗传算法|GA算法|NSGA[-－]?II",
    "粒子群": r"粒子群|PSO",
    "差分进化": r"差分进化|DE算法",
    "模拟退火": r"模拟退火|SA算法",
    "蚁群算法": r"蚁群算法|ACO",
    "贪心与局部搜索": r"贪心算法|局部搜索|邻域搜索|禁忌搜索|变邻域",
    "图搜索": r"A\*|A-star|Dijkstra|迪杰斯特拉|Floyd|最短路",
    "网络流": r"网络流|最大流|最小费用流|二分图匹配",
    "蒙特卡罗": r"蒙特卡罗|Monte Carlo|随机模拟",
    "熵权-TOPSIS": r"熵权|TOPSIS|逼近理想解",
    "层次分析": r"层次分析|AHP",
    "主成分与因子": r"主成分|PCA|因子分析",
    "灰色模型": r"灰色预测|GM\s*\(1\s*,\s*1\)|灰色关联",
    "时间序列": r"ARIMA|SARIMA|时间序列|指数平滑|Prophet",
    "回归模型": r"线性回归|多元回归|岭回归|Lasso|Logistic|逻辑回归|多项式回归",
    "随机森林": r"随机森林|Random Forest",
    "支持向量机": r"支持向量|SVM|SVR",
    "梯度提升树": r"XGBoost|LightGBM|CatBoost|梯度提升",
    "神经网络": r"神经网络|BP网络|CNN|卷积神经|LSTM|GRU|Transformer",
    "聚类分析": r"聚类|K[-－]?means|DBSCAN|层次聚类",
    "插值与拟合": r"插值|曲线拟合|最小二乘|样条|Kriging|克里金",
    "常微分方程": r"常微分方程|微分方程组|ODE|龙格库塔|Runge",
    "偏微分方程": r"偏微分方程|PDE|热传导方程|扩散方程|波动方程",
    "有限差分": r"有限差分|差分格式",
    "有限元": r"有限元|Finite Element|FEM",
    "马尔可夫模型": r"马尔可夫|Markov",
    "排队模型": r"排队论|排队模型|M/M/",
    "元胞自动机": r"元胞自动机|Cellular Automata",
    "系统动力学": r"系统动力学|System Dynamics",
    "几何与运动学": r"运动学|轨迹方程|几何关系|坐标变换|刚体变换",
    "图像与信号处理": r"图像处理|信号处理|傅里叶|小波|频谱|边缘检测",
}

TASK_PATTERNS = {
    "物理机理": r"机理|物理|受力|运动学|动力学|传热|温度场|电磁|光学|流体|扩散",
    "优化决策": r"最优|优化|调度|分配|路径|选址|策略|决策变量|目标函数|约束",
    "预测": r"预测|趋势|未来|时间序列",
    "评价排序": r"评价|排名|排序|指标体系|权重|综合得分",
    "统计推断": r"统计|显著性|假设检验|相关性|回归|方差分析|置信区间",
    "分类识别": r"分类|识别|判别|标签|准确率|混淆矩阵",
    "聚类分群": r"聚类|分群|类别发现",
    "网络与路径": r"网络|图论|节点|边|路径|连通|拓扑",
    "仿真模拟": r"仿真|模拟|随机过程|蒙特卡罗",
    "数据清洗": r"缺失值|异常值|数据清洗|预处理|标准化|归一化",
}

VALIDATION_PATTERNS = {
    "灵敏度分析": r"灵敏度|敏感性",
    "稳健性检验": r"稳健性|鲁棒性|扰动实验",
    "误差分析": r"误差分析|相对误差|绝对误差|均方误差|RMSE|MAE|MAPE",
    "交叉验证": r"交叉验证|cross[- ]validation|训练集|测试集",
    "显著性检验": r"显著性检验|p值|P值|t检验|卡方检验|方差分析",
    "残差诊断": r"残差|正态性检验|异方差|自相关",
    "算法对比": r"对比实验|算法对比|基准函数|消融实验|基准模型",
    "收敛检验": r"收敛曲线|收敛性|迭代次数",
    "外部验证": r"外部数据|实际数据验证|案例验证|历史数据验证",
}

FIGURE_PATTERNS = {
    "流程图": r"流程图|技术路线",
    "收敛曲线": r"收敛曲线|适应度曲线|迭代曲线",
    "灵敏度图": r"灵敏度图|敏感性图|扰动曲线",
    "拟合与误差图": r"拟合图|预测对比|残差图|误差图",
    "热力图": r"热力图|相关系数矩阵",
    "三维图": r"三维图|3D|三维曲面|空间轨迹",
    "路径与网络图": r"路径图|网络图|拓扑图|路线图",
    "分布图": r"直方图|箱线图|核密度|分布图",
    "评价对比图": r"雷达图|柱状图|排名图|方案对比",
}

DOMAIN_PATTERNS = {
    "交通物流": r"交通|车辆|物流|配送|运输|道路|航线",
    "生产制造": r"生产|制造|加工|装配|供应链|库存",
    "生态环境": r"生态|环境|污染|碳排放|气候|水质",
    "农业食品": r"农业|农作物|种植|食品|农田",
    "医疗健康": r"医疗|疾病|健康|患者|药物|睡眠",
    "能源电力": r"能源|电力|电网|光伏|风电|储能|充电",
    "通信网络": r"通信|网络|带宽|基站|信号|频谱",
    "航空航天": r"无人机|导弹|飞行|航天|轨道",
    "材料工程": r"材料|应力|结构|温度|传热|振动",
    "社会经济": r"经济|人口|社会|旅游|政策|市场",
    "体育运动": r"运动员|比赛|训练|跳远|体能",
}


def normalize_text(text: str) -> str:
    """压缩空白并修正常见 OCR 分隔。"""
    text = text.replace("\x00", " ").replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chinese_count(text: str) -> int:
    """统计中文字符，判断 PDF 是否有可用文本层。"""
    return sum("\u4e00" <= char <= "\u9fff" for char in text)


def selected_pages(page_count: int) -> list[int]:
    """为快速 OCR 选择摘要、正文采样页和结尾检验页。"""
    indexes = {0, 1, 2}
    indexes.update(range(4, page_count, 4))
    indexes.update(range(max(0, page_count - 3), page_count))
    return sorted(index for index in indexes if index < page_count)


def ocr_page(page, engine) -> str:
    """用 RapidOCR 识别一页图片型 PDF。"""
    import numpy as np

    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0), alpha=False)
    image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
    result = engine(image)
    return "\n".join(result.txts or ())


def cache_path_for(pdf: Path, corpus: Path) -> Path:
    """按语料相对路径生成文本缓存路径。"""
    relative = pdf.relative_to(corpus)
    return corpus / "extracted_text" / relative.with_suffix(relative.suffix + ".txt")


def extract_pdf(pdf: Path, corpus: Path, ocr_mode: str) -> tuple[str, dict]:
    """优先读取文本层，必要时按策略执行 OCR，并缓存结果。"""
    cache = cache_path_for(pdf, corpus)
    meta_path = cache.with_suffix(cache.suffix + ".json")
    if cache.is_file() and meta_path.is_file():
        return cache.read_text(encoding="utf-8"), json.loads(meta_path.read_text(encoding="utf-8"))
    document = fitz.open(pdf)
    page_texts = [page.get_text("text", sort=True) for page in document]
    text_layer = normalize_text("\n\n".join(page_texts))
    meta = {"pages": len(document), "text_layer_chars": chinese_count(text_layer), "method": "text"}
    if chinese_count(text_layer) < max(500, len(document) * 60) and ocr_mode != "none":
        from rapidocr import RapidOCR

        indexes = list(range(len(document))) if ocr_mode == "full" else selected_pages(len(document))
        engine = RapidOCR(params={
            "EngineConfig.onnxruntime.intra_op_num_threads": 4,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
        })
        recognized = []
        for index in indexes:
            recognized.append(f"\n[PAGE {index + 1}]\n{ocr_page(document[index], engine)}")
        text_layer = normalize_text("\n".join(recognized))
        meta.update({"method": f"ocr_{ocr_mode}", "ocr_pages": [index + 1 for index in indexes]})
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text_layer, encoding="utf-8")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return text_layer, meta


def infer_year_problem(path: Path, kind: str) -> tuple[int | None, str | None, str]:
    """从目录和文件名推断年份、题号与证据编号。"""
    normalized = path.as_posix()
    # 年份必须是独立的四位数字，避免把语料缓存日期（如 20260805）误判为 2026 年。
    year_match = re.search(r"(?<!\d)(20\d{2})(?!\d)", normalized)
    year = int(year_match.group(1)) if year_match else None
    problem = None
    if "github_2025" in normalized and path.name == "paper.pdf":
        year, problem = 2025, "C"
    patterns = [r"/([A-F])/[^/]+\.pdf$", r"cumcm20\d{2}([a-f])", r"[/_-]([A-F])\d", r"([A-F])题"]
    for pattern in patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            problem = match.group(1).upper()
            break
    evidence_id = f"{kind}:{year or 'unknown'}-{problem or 'unknown'}:{path.stem}"
    return year, problem, evidence_id


def first_title(text: str, year: int | None, problem: str | None) -> str:
    """从题面或论文首页提取简短标题。"""
    clean = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    if problem:
        title_match = re.search(rf"{problem}\s*题\s*[:：]?\s*([^\n]{{3,70}})", text, re.IGNORECASE)
        if title_match:
            return normalize_text(title_match.group(1)).split("\n")[0][:70]
    for line in clean[:25]:
        if 5 <= len(line) <= 70 and not re.search(r"全国大学生|参赛队号|摘要|承诺书|编号", line):
            return line
    return f"{year or ''}{problem or ''}题"


def extract_abstract(text: str) -> str:
    """提取摘要，供方法链识别但不直接写入 skill。"""
    patterns = [
        r"摘\s*要\s*[:：]?\s*(.{150,3500}?)(?=关\s*键\s*词|关键词)",
        r"摘要\s*(.{150,3500}?)(?=关键词|一[、.]|\n1[、.])",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return normalize_text(match.group(1))[:3500]
    return normalize_text(text[:3500])


def detect_terms(text: str, patterns: dict[str, str]) -> list[str]:
    """按首次出现顺序识别规范化术语。"""
    found = []
    for name, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found.append((match.start(), name))
    return [name for _, name in sorted(found)]


def extract_question_chains(abstract: str) -> list[dict]:
    """从摘要中提取各小问的模型链证据。"""
    marker = re.compile(r"针对问题\s*([一二三四五六七八九十\d]+)\s*[：:]?")
    matches = list(marker.finditer(abstract))
    chains = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(abstract)
        segment = abstract[match.start():end]
        chains.append({"question": match.group(1), "models": detect_terms(segment, MODEL_PATTERNS),
                       "validations": detect_terms(segment, VALIDATION_PATTERNS), "evidence": segment[:800]})
    return chains


def analyze_pdf(pdf: Path, corpus: Path, kind: str, ocr_mode: str) -> dict:
    """把一份题面或论文转换为结构化证据。"""
    text, extraction = extract_pdf(pdf, corpus, ocr_mode)
    year, problem, evidence_id = infer_year_problem(pdf, kind)
    abstract = extract_abstract(text) if kind == "paper" else ""
    analysis_text = abstract if abstract else text[:12_000]
    normalized_path = pdf.as_posix()
    award_level = "official_exhibition" if "/official/" in normalized_path else "national_second_with_code" if "github_2025" in normalized_path else "problem"
    return {
        "evidence_id": evidence_id,
        "kind": kind,
        "year": year,
        "problem": problem,
        "title": first_title(text, year, problem),
        "relative_path": pdf.relative_to(corpus).as_posix(),
        "award_level": award_level,
        "is_primary_problem": kind == "problem" and "附件" not in pdf.name,
        "extraction": extraction,
        "chinese_chars": chinese_count(text),
        "models": detect_terms(analysis_text, MODEL_PATTERNS),
        "tasks": detect_terms(text[:20_000], TASK_PATTERNS),
        "domains": detect_terms(text[:20_000], DOMAIN_PATTERNS),
        "validations": detect_terms(text, VALIDATION_PATTERNS),
        "figures": detect_terms(text, FIGURE_PATTERNS),
        "question_chains": extract_question_chains(abstract),
        "abstract": abstract,
    }


def compact_source_manifest(corpus: Path) -> dict:
    """删除本机绝对路径，保留来源、哈希和大小。"""
    source = json.loads((corpus / "download_manifest.json").read_text(encoding="utf-8"))
    records = []
    for item in source.get("records", []):
        compact = {key: value for key, value in item.items() if key != "local_path"}
        if item.get("repo") == "zhanwen/MathModel" and item.get("kind") == "paper_2023":
            compact["status"] = "excluded"
            compact["exclusion_reason"] = "文件首页表明其属于华为杯中国研究生数学建模竞赛，不是 CUMCM"
        records.append(compact)
    return {"schema_version": "1.0", "generated_at": source.get("generated_at"), "records": records,
            "failures": source.get("failures", [])}


def build_cases(records: list[dict], annotations: dict[str, dict] | None = None) -> list[dict]:
    """按年份和题号聚合论文证据与题面标签。"""
    annotations = annotations or {}
    groups: dict[tuple[int, str], list[dict]] = defaultdict(list)
    problems: dict[tuple[int, str], dict] = {}
    for record in records:
        if not record.get("year") or not record.get("problem"):
            continue
        key = (record["year"], record["problem"])
        if record["kind"] == "problem":
            if key not in problems or record.get("is_primary_problem"):
                problems[key] = record
        else:
            groups[key].append(record)
    cases = []
    for key in sorted(set(groups) | set(problems)):
        year, problem = key
        papers = groups.get(key, [])
        statement = problems.get(key)
        counters = {name: Counter() for name in ("models", "tasks", "domains", "validations", "figures")}
        for record in papers + ([statement] if statement else []):
            for name in counters:
                counters[name].update(record.get(name, []))
        model_chains = []
        for paper in papers:
            chain = []
            for question in paper.get("question_chains", []):
                chain.extend(question.get("models", []))
            chain = list(dict.fromkeys(chain))
            if chain and chain not in model_chains:
                model_chains.append(chain)
        evidence_level = "high" if len(papers) >= 3 else "medium" if papers else "problem_only"
        case = {
            "id": f"cumcm_{year}_{problem}", "year": year, "problem": problem,
            "title": statement["title"] if statement else (papers[0]["title"] if papers else f"{year}{problem}题"),
            "task_tags": [name for name, _ in counters["tasks"].most_common()],
            "domain_tags": [name for name, _ in counters["domains"].most_common()],
            "model_families": [{"name": name, "paper_count": count} for name, count in counters["models"].most_common()],
            "validation_methods": [{"name": name, "paper_count": count} for name, count in counters["validations"].most_common()],
            "figure_types": [{"name": name, "paper_count": count} for name, count in counters["figures"].most_common()],
            "model_chains": model_chains[:8], "paper_count": len(papers), "evidence_level": evidence_level,
            "evidence_ids": [record["evidence_id"] for record in papers],
            "problem_evidence_id": statement["evidence_id"] if statement else None,
            # 标签为关键词自动抽取, 可能含噪声; annotations 可提供人工覆盖
            "tag_provenance": "auto_keyword_unverified",
            # 无论文证据时 recommended_chain 为题面推断, 不能与论文证据链等价使用
            "chain_confidence": "paper_derived" if papers else "problem_inferred",
        }
        case.update(annotations.get(case["id"], {}))
        cases.append(case)
    return cases


def render_case_library(cases: list[dict]) -> str:
    """生成便于人工复核的案例库说明。"""
    lines = ["# CUMCM 逐题案例知识库", "", "> 模型和检验来自论文摘要/正文识别；只表示历史使用情况，不等于推荐直接套用。", ""]
    for case in cases:
        models = "、".join(item["name"] for item in case["model_families"][:8]) or "暂无论文证据"
        checks = "、".join(item["name"] for item in case["validation_methods"][:6]) or "未识别"
        recommended = " → ".join(case.get("recommended_chain", [])) or "待结合新题设计"
        boundary = case.get("transfer_boundary", "只迁移建模思想，重新核对数据、假设和约束。")
        lines.extend([
            f"## {case['year']} {case['problem']}题：{case['title']}", "",
            f"- 证据：{case['paper_count']} 篇论文，等级 `{case['evidence_level']}`。",
            f"- 问题本质：{case.get('essence', '待人工标注')}。",
            f"- 任务标签：{'、'.join(case['task_tags']) or '待人工标注'}。",
            f"- 领域标签：{'、'.join(case['domain_tags']) or '待人工标注'}。",
            f"- 历史模型：{models}。", f"- 推荐模型链：{recommended}。",
            f"- 历史检验：{checks}。", f"- 迁移边界：{boundary}", "",
        ])
    return "\n".join(lines)


def main() -> int:
    """扫描语料、缓存提取文本并生成案例索引。"""
    parser = argparse.ArgumentParser(description="深度蒸馏 CUMCM 逐题案例")
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--knowledge-dir", type=Path, required=True)
    parser.add_argument("--ocr", choices=("none", "selected", "full"), default="selected")
    parser.add_argument("--workers", type=int, default=1, help="OCR 并行数，建议 2-3")
    args = parser.parse_args()
    corpus = args.corpus_dir.resolve()
    knowledge = args.knowledge_dir.resolve()
    evidence_dir = corpus / "distilled_evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    paper_pdfs = sorted((corpus / "papers" / "official").rglob("*.pdf"))
    verified_extra = corpus / "papers" / "github_2025" / "paper" / "paper.pdf"
    if verified_extra.is_file():
        paper_pdfs.append(verified_extra)
    problem_pdfs = sorted((corpus / "problems").rglob("*.pdf"))
    jobs = [(pdf, "paper") for pdf in paper_pdfs] + [(pdf, "problem") for pdf in problem_pdfs]
    records = []
    failures = []
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 4))) as pool:
        futures = {pool.submit(analyze_pdf, pdf, corpus, kind, args.ocr): (pdf, kind) for pdf, kind in jobs}
        for index, future in enumerate(as_completed(futures), 1):
            pdf, kind = futures[future]
            try:
                records.append(future.result())
                status = kind
            except Exception as exc:
                failures.append({"relative_path": pdf.relative_to(corpus).as_posix(), "kind": kind, "error": str(exc)})
                status = "failed"
            print(f"[{index}/{len(jobs)}] {status} {pdf.relative_to(corpus)}", flush=True)
    evidence_payload = {"records": records, "failures": failures}
    (evidence_dir / "records.json").write_text(json.dumps(evidence_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    cases_dir = knowledge / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    annotation_path = cases_dir / "annotations.json"
    annotations = json.loads(annotation_path.read_text(encoding="utf-8")).get("cases", {}) if annotation_path.is_file() else {}
    cases = build_cases(records, annotations)
    index = {"schema_version": "1.0", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
             "competition": "cumcm", "cases": cases}
    (cases_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    (knowledge / "case_library.md").write_text(render_case_library(cases), encoding="utf-8")
    (knowledge / "source_manifest.json").write_text(
        json.dumps(compact_source_manifest(corpus), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"完成：论文 {len(paper_pdfs)}，题面 {len(problem_pdfs)}，案例 {len(cases)}，失败 {len(failures)}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
