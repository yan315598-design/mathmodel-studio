# 架构说明

## 核心调用关系

```text
用户题面
  -> SKILL.md 阶段路由
  -> competitions/<comp>/topic_specs.json
  -> 三赛题目级 / 子问级检索
       -> cases/index.json
       -> cases/manual_review_annotations.json
       -> case_retrieval.md
  -> scripts/build_stage_pack.py
  -> scripts/generate_paper_plan.py
       -> 动态章节 + 图表证据计划 + evidence ledger
  -> scripts/trace_claims.py
  -> distilled_modeling.md / distilled_figures.md
  -> references/stage_00..09 + rubrics.md
  -> config/rating_contract.json + rubric_overlay.json
  -> scripts/score_artifact.py
  -> state/decision_log.json
  -> scripts/render_paper.py
```

## 文件与模块职责

| 路径 | 职责 |
|---|---|
| `SKILL.md` | 触发、阶段路由、加载协议和安全边界 |
| `AGENTS.md` | Codex 项目级入口与编号菜单适配 |
| `agents/openai.yaml` | Codex UI 名称和默认提示 |
| `references/stage_00..09` | 各阶段工作步骤和检查点 |
| `references/model_catalog.md` | 跨竞赛候选模型目录 |
| `references/knowledge_workflow_v73.md` | 三赛联合检索、Stage 知识包、证据链和增量更新协议 |
| `competitions/<comp>/` | 竞赛规则、知识和评分覆盖层 |
| `config/dim_weights.json` | 竞赛 × 内容型任务 × 阶段的评分权重 |
| `config/rating_contract.json` | 所有竞赛共享的评分、证据、verdict 和硬失败契约 |
| `scripts/score_artifact.py` | 评分、受 scoring_policy 限制的经验指标注入和 verdict 计算 |
| `scripts/build_stage_pack.py` | 为 Stage 1/3/5/8/9 生成最小知识包 |
| `scripts/generate_paper_plan.py` | 按子问依赖生成动态骨架、图表计划和证据账本 |
| `scripts/trace_claims.py` | 审计问题到摘要主张的完整证据链 |
| `scripts/update_knowledge.py` | 用 SHA-256 跟踪增量与知识版本，跳过未变化文件 |
| `scripts/render_paper.py` | 论文模板渲染与编译 (md 节 → tex → PDF) |
| `templates/latex/<comp>/` | 自写竞赛 LaTeX 模板, 共 6 套: cumcm / huaweibei / huashubei / mcm / diangong / apmcm |
| `templates/figures/style/` | 图表样式资产 (matplotlib 样式文件与调色板) |
| `templates/shared/` | 各阶段通用 markdown 模板与代码起步骨架 |

## 国赛、研究生赛与华数杯知识链

| 路径 | 职责 |
|---|---|
| `scripts/download_cumcm_papers.py` | 下载来源、校验哈希、记录失败并隔离误标资料 |
| `scripts/distill_cumcm_cases.py` | 提取文本/OCR、识别方法与验证、按年份题号聚合案例 |
| `competitions/cumcm/cases/annotations.json` | 保存人工归纳的问题本质、模型链、验证、图表和边界 |
| `competitions/cumcm/cases/index.json` | 自动证据与人工标注合并后的运行时检索索引 |
| `competitions/cumcm/cases/manual_review_annotations.json` | 25 题跨论文人工复核覆盖层，提供路线分歧、假设、验证、图表和写作字段 |
| `scripts/retrieve_cases.py` | 三赛统一入口，支持 `cumcm|huaweibei|huashubei|all` 和 `case|question|both` |
| `scripts/retrieve_cumcm_cases.py` | 检索核心实现和旧命令兼容入口 |
| `competitions/cumcm/distilled_modeling.md` | 九类内容型建模范式 |
| `competitions/cumcm/distilled_figures.md` | 各任务的最小图表证据组合 |
| `competitions/cumcm/empirical.json` | 只有完整覆盖指标才能进入评分的可靠统计 |
| `competitions/cumcm/source_manifest.json` | 来源、哈希、状态和排除理由 |
| `competitions/huaweibei/cases/index.json` | 2021—2025 共 30 个研究生赛基础案例 |
| `competitions/huaweibei/cases/manual_review_annotations.json` | 30 题的逐问依赖、路线比较、假设、验证、图表和写作覆盖层 |
| `competitions/huaweibei/papers/manual_paper_reviews.json` | 12 篇 2021 数模之星提名论文的逐篇、逐问深读 |
| `competitions/huashubei/cases/index.json` | 18 题华数杯案例；明确区分论文模式与仅题面摘要 |
| `scripts/build_huashubei_cases.py` | 从题型规格和论文统计重建华数杯案例索引 |
| `references/cross_competition_distillation.md` | 研究生赛、华数杯、国赛可共享结构与必须隔离的证据边界 |

## 关键设计决定

- CUMCM 采用内容优先分类，题号只用于定位历史案例。
- 研究生赛同样采用内容优先分类，A-F 不固定映射题型；`huaweibei` 与 `huashubei` 始终隔离。
- 三赛共享检索协议、方法接口、章节逻辑和图表叙事；题目、奖项、统计、模板和案例身份分别加载。
- Stage 知识包只携带当前阶段字段，避免把大体量证据包一次装入上下文。
- 图表必须绑定角色、唯一主张、上游数据和必要检查；数量不是获奖硬门槛。
- 摘要主张必须通过结果证据链，缺结果或验证时由 `trace_claims.py` 阻断。
- 评分公共规则集中在统一契约，竞赛 overlay 只描述差异。
- 知识更新使用文件哈希和语义版本；未变化文件不重跑，移除记录不触发自动删除。
- 自动抽取负责“论文出现过什么”，人工标注负责“如何迁移、何时不能迁移”。
- 基础索引与人工复核在读取时合并，不改写来源计数；Stage 3/5/8 只消费命中案例字段，避免一次加载完整 64 篇证据。
- 历史数值只用于口径和数量级警戒，禁止进入新题求解结果。
- 证据等级区分全文提名论文、跨论文人工层、论文模式和仅题面摘要，题面归纳不冒充获奖论文证据。
- 原始 PDF 留在外部语料缓存，不放入 skill；skill 只保存改写后的模式、来源清单和证据 ID。
- 58 篇误标研究生论文只作来源审计，不能进入案例、统计、评分或写作规律。
- 详细知识按阶段懒加载，`SKILL.md` 只保存路由规则。
