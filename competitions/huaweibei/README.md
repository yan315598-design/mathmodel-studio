# 中国研究生数学建模竞赛经验分支

竞赛键：`huaweibei`。本分支对应中国研究生数学建模竞赛，历史上常被称为“华为杯”，不要与华数杯 `huashubei` 混淆。

## 证据范围

- 2021—2025 年 30 道题。
- 190 篇本地优秀论文，全文共 12458 页。
- 2021 年目录确认的 12 篇“数模之星提名奖”论文。
- 2022—2025 年论文不推测提名身份。

## 使用顺序

1. Stage 1：加载 `topic_specs.json`、`case_retrieval.md` 和 `cases/index.json`，按题面内容检索，不把 A-F 固定成题型。
2. Stage 3：从命中案例读取路线比较、假设风险和必要验证，再结合通用模型库选路线。
3. Stage 5：使用逐问依赖和“为什么—模型—中间状态—结果—验证—回答”闭环。
4. Stage 8：加载 `winning_patterns.md`、`abstract_template.md`、`paper_skeleton.md`、`phrase_bank.md`、`distilled_figures.md`。
5. Stage 9：加载 `anti_patterns.md` 和 `rubric_overlay.json`，核对来源、口径、边界和奖项陈述。

## 文件职责

- `cases/index.json`：30 道题的检索基础索引。
- `cases/manual_review_annotations.json`：30 题人工深度复核覆盖层。
- `papers/manual_paper_reviews.json`：12 篇提名论文逐篇深读。
- `all_cases_manual_audit.md`、`star_papers_deep.md`：适合人工阅读的总稿。
- `distilled_modeling.md`：跨题型的建模链和路线选择。
- `distilled_figures.md`：结构—机制—结果—可信边界图表逻辑。
- `distilled_structures.md`、`distilled_formats.md`：章节功能与表达格式。
- `empirical.json`、`empirical_notes.md`：描述统计及限制。
- `source_manifest.json`：本地来源、哈希、页数和提取状态。

## 强制边界

- 只迁移结构、论证动作和验证逻辑。
- 历史数据、参数、阈值、权重、结果和原句必须针对当前题重做。
- 单篇路线不能冒充跨论文共识。
- 奖项身份必须有目录或官方证据。

