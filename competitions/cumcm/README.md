# CUMCM 国赛特化层

全国大学生数学建模竞赛专用知识库。运行时按题面内容检索案例，A/B/C/D/E 只作题号，不直接决定模型。

| 字段 | 值 |
|---|---|
| 竞赛代码 | `cumcm` |
| 时长 / 队员 | 72 小时 / 3 人 |
| 语言 / 编译器 | 中文 / xelatex |
| 模板 | `templates/latex/cumcm/main.tex` (自写 ctexart) |
| 引用格式 | GB/T 7714 |
| 语料状态 | 32 篇官方展廊 + 1 篇可核验国二 + 25 个题面案例 |
| 排除资料 | 58 篇误标为国赛的“华为杯”研究生论文 |

## 运行时文件

| 文件 | 用途 | 阶段 |
|---|---|---|
| `case_retrieval.md` | 相似题检索和可信度协议 | Stage 1—3 |
| `cases/index.json` | 25 个案例的基础结构化索引 | Stage 1—5 |
| `cases/manual_review_annotations.json` | 25 题、64 篇论文的人工复核覆盖层 | Stage 1/3/5/8 |
| `cases/annotations.json` | 可重建的人工深度标注 | 维护期 |
| `case_library.md` | 案例人读视图 | 人工复核 |
| `all_cases_manual_audit.md` | 人工复核的人读总表 | 人工审计 |
| `distilled_modeling.md` | 九类内容型建模范式 | Stage 3/5 |
| `distilled_figures.md` | 图表证据组合 | Stage 5/8 |
| `winning_patterns.md` | 高质量论文原则 | Stage 8 |
| `empirical.json` | 可靠覆盖的摘要字数与页数分位 | Stage 8 |
| `rubric_overlay.json` | CUMCM 评分与来源审计要求 | Stage 3/8/9 |
| `source_manifest.json` | 来源、哈希、状态和排除理由 | 审计 |

`distilled_phrases.md`、`distilled_naming.md`、`distilled_structures.md` 和 `distilled_formats.md` 属于旧写作辅助层；其中任何旧定量表述都不得覆盖 `empirical.json` 和 `winning_patterns.md` 的新规则。

## 来源

- 教育部中国大学生在线优秀论文展廊：2023—2025 共 32 篇。
- `Jackyleo-Zhao/cumcm-2025`：2025 C 题国二论文与代码。
- `CosmicLinks/cumcm-problems`：2021—2025 题面。
- `zhanwen/MathModel` 的 58 篇旧资料仅作排除审计，不进入知识库。

下载和蒸馏脚本见 `scripts/download_cumcm_papers.py`、`scripts/distill_cumcm_cases.py` 和 `scripts/retrieve_cumcm_cases.py`。

## 人工复核覆盖层

运行时检索器自动把 `manual_review_annotations.json` 合并到基础索引，但不覆盖基础来源计数。`paper_count/evidence_level` 继续表示原可核验库，`reviewed_paper_count/reviewed_evidence_ids` 表示本地 64 篇论文复核证据。历史结果仅用于发现口径差异，不能作为新题答案。
