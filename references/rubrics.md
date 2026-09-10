# 评分细则 (rubrics)

> 多竞赛统一评分契约。基础维度、分数范围、证据要求和 verdict 来自 `config/rating_contract.json`；竞赛 overlay 只覆盖差异，维度数可不同。L1 Critic 直接 JSON 化使用。

候选版按 `modeling_evidence_protocol.md` 解释历史评分键：变量 count 看必要量完整；candidate_diversity 看有效替代与取舍；naming_variant 看名称与实际机制一致；cross_reference_chain 看题面依赖与固定输入正确。不得因变量少、候选不足三个、无修饰词或合理独立求解扣分；竞赛历史范例不覆盖这些语义。

---

## Overlay 协议 (v3.0)

| 层级 | 来源 | 加载 |
|------|------|------|
| 通用基础 | `config/rating_contract.json` + 本文件解释 | 所有一等竞赛分支共享 |
| 竞赛特化 dim 名 | `competitions/<comp>/rubric_overlay.json` 的 `dim_whitelist` | score_artifact.py 自动合并 |
| 题型 dim 权重 | `config/dim_weights.json[<comp>][<task_type>]` | compute_verdict 加权 mean |
| 实测分位 | `competitions/<comp>/empirical.json` | inject_evidence 注入 evidence |

`task_type` 由 stage 1 选题后填入 decision_log; null 时 default 全 1.0 等价老逻辑。

---

## 多竞赛评分维度对照

### CUMCM 国赛 (来源: 组委会公布 + 评委复盘)

| 维度 | 权重 | 关键检查项 |
|------|-----|----------|
| **摘要质量** | 30% | 结构覆盖题问 / 量化结果 / 创新表述 / 字数 IQR [748, 1146] |
| **模型建立** | 25% | 与问题契合 / 假设有支撑 / 数学严谨 / 名称与机制一致 |
| **求解与结果** | 20% | 算法合理 / 代码可复现 / 结果可视化 / 物理意义 |
| **写作呈现** | 15% | 章节完整 / 公式编号规范 / 图表清晰 / 语言流畅 |
| **创新性** | 10% | 真实机制差异 / 缺口驱动的组合 / 跨学科融合 |

### MCM/ICM 美赛 (来源: COMAP scoring rubric)

| 维度 | 关键检查项 |
|------|----------|
| **1-page Summary** | 250-350 词 / ≥3 quantitative / takeaway / 单页 |
| **Approach & Modeling** | novel approach / assumption support / 严谨 |
| **Solution & Results** | 算法 / 复现性 / sensitivity 是独立大节 |
| **Communication** | 写作清晰 / 图表 self-contained / 术语精确 |
| **Letter** (D/E/F) | actionable recommendations / plain language / caveat |

### 电工杯 (来源: 公开评审标准估算, seed v0.1)

| 维度 | 关键检查项 |
|------|----------|
| **工程实用性** | 落地可行 / 投资估算 / 阶段实施 |
| **物理意义** | 数值带 kW/kWh/% / 工程语义 |
| **数据完整性** | 题目附件全部使用 / 预处理章节 |
| **多场景对比** | ≥3 场景 / 工程参数扰动 |
| **写作呈现** | GB/T 7714 / 工程惯用图表 |

---

## L1 阶段级 rubric (5 维 × 1-10)

每阶段产出后,Critic 输出以下 JSON:

```json
{
  "stage_id": 0-9,
  "iteration": 0-3,
  "scores": {
    "<dim_key_snake_case>": {"name": "中文名称", "score": 1-10, "evidence": "产物定位(文件/表/行)+简评, ≤80字"},
    ...
  },
  "min_score": <number>,
  "mean_score": <number>,
  "issues": [
    {"severity": "high|medium|low", "where": "...", "anti_pattern_id": "A1|null", "fix": "..."},
    ...
  ],
  "verdict": "block | pass_early | pass | refine"
}
```

**dim key 命名约定**: 各 stage 的 5 个 `scores` 字段必须用**英文 snake_case**, 与 `feedback_layer1_critic.md §6` 各 stage 列出的固定集合精确一致 (`scripts/score_artifact.py` 加白名单校验)。下面各 stage 表第一列写中文是为了人读, 实际 JSON 输出用英文 key, **中文写在 `name` 子字段**。

退出条件: 见本文件末尾"阈值汇总"节, 与 SKILL.md / feedback_layer1_critic.md / score_artifact.py 三处统一。

---

### Stage 0 — 团队启动

| 维度 | 满分行为 (10) | 失败行为 (1) |
|------|-------------|-------------|
| 1. 角色分工明确性 | 建模/编程/写作 三人各有主责且互备 | 全员都"什么都做" |
| 2. 工具就绪度 | Python/LaTeX/Git/通讯工具 全员可用 | 临场装环境 |
| 3. 时间盒规划 | 3 天每 6h 一个 milestone,有 buffer | 无计划 |
| 4. 题目预扫信号 | 已识别问题域 (优化/预测/评价等) | 未读题 |
| 5. 协作约定 | 命名规范、版本控制、daily standup 时间 | 无规范 |

---

### Stage 1 — 选题

| 维度 | 满分行为 |
|------|---------|
| 1. 三题对比深度 | 三题各列 5+ 评估点 (难度/数据/契合度/工具/参考资料) |
| 2. 团队优势匹配 | 选题理由含"我们擅长 X,本题需要 X" |
| 3. 风险识别 | 列出 ≥3 个本题潜在坑及预案 |
| 4. 时间可行性 | 已估各阶段所需 h,合计 ≤72h |
| 5. 决策记录质量 | rationale + rejected_alternatives 都有 ≥3 行依据 |

退出条件: 选定题号 + decision_log.json stage 1 节点完整 + 全维 ≥7。

---

### Stage 2 — 问题深度解析

| 维度 | 满分行为 |
|------|---------|
| 1. 子问题分解清晰度 | 每个 sub-problem 的输入/输出/约束明确 |
| 2. 关键变量识别 | 必要量完整，类型与单位明确，不设数量下限 |
| 3. 数学化程度 | 数学对象符合任务类型，非优化题不强设目标 |
| 4. 数据契合度 | 题目附件数据已扫描,与变量映射清楚 |
| 5. 子问题关联性 | 已识别 Q3 是否依赖 Q1/Q2 (一等奖必查) |

---

### Stage 3 — 模型选型

| 维度 | 满分行为 |
|------|---------|
| 1. 候选比较 | 至少考虑一个认真可行的替代；无可行替代时说明证据，不凑族数 |
| 2. 选型理由 | 每个候选有 (a) 适配理由 (b) 不选的原因 |
| 3. 名称与机制 | 名称对应公式与实现，新增模块有必要性与接口，不要求修饰词 |
| 4. 求解可行性 | 已确认 Python 库存在 + 时间复杂度可承受 |
| 5. 文献支撑 | 至少 2 篇引用支持选型 (题目领域内) |

championship 模式额外: red-team "假装最严苛评委,本模型选择被 reject 的最强理由?" → 必须有可信回应。

---

### Stage 4 — Foundation (假设 + 符号 + 术语)

| 维度 | 满分行为 |
|------|---------|
| 1. 假设覆盖 | 关键假设无遗漏，每条都被某个结论需要；不设数量区间 |
| 2. 假设支撑 | 每条配 (a) 文献 / (b) 数据观察 / (c) 物理意义 三选一 |
| 3. 符号唯一性 | 同一符号不同含义 = 0 分;每符号有单位 |
| 4. 与模型一致性 | stage 5 后回检,无矛盾 |
| 5. 术语规范 | 专业术语首次出现给定义，中英对照；不设条数下限 |

---

### Stage 5 — 子问题递归循环 (per Qi)

每个 sub-problem 跑一次 5 维 rubric,**外加** stage-level overall:

#### Per-Qi rubric:

| 维度 | 满分行为 |
|------|---------|
| 1. 模型与问题契合 | 目标函数 / 决策变量 / 约束 与题面一一对应 |
| 2. 数学严谨性 | 推导无跳跃,符号一致,边界条件齐全 |
| 3. 求解正确性 | 代码可运行,结果数量级合理,通过 sanity check |
| 4. 结果可视化 | 图表支撑本问主张且绑定上游数据，数量由论证需要决定 (不设每问下限；0/1 图走 D.1 例外登记) |
| 5. 物理意义讨论 | 数值 → 现实含义 (≥1 段文字) |

#### Stage-level (跨子问题):

- **依赖与接口**：核对题面要求的复用与固定输入；不默认要求调用前问
- **变量一致性**: 不同子问题间变量符号统一

退出条件: 所有 Qi 通过 + 题面依赖与固定输入核对完成 + 全维 ≥7。

---

### Stage 6 — 全局灵敏度 / 稳健性

| 维度 | 满分行为 |
|------|---------|
| 1. 扰动围绕结论 | 优先扰动会改变结论的参数；参数数量与方法按问题风险选择，不强制联合扰动或特定采样法 |
| 2. 扰动幅度有据 | 幅度对应实际不确定性来源并写明依据，不设固定档位 |
| 3. 输出对应决策 | 报告结论是否翻转、决策变化与决策损失，不只报目标值 |
| 4. 稳健范围定量 | 在明确口径下给出结论成立的参数范围 |
| 5. 失效边界 | 已观察到失效条件则写出阈值与表现；未观察到则报告测试范围，不编造临界参数 |

L2 触发: 末尾跨阶段回检 stage 3 的模型选择前提是否被本节结果推翻。

---

### Stage 7 — 模型评价 + 推广

| 维度 | 满分行为 |
|------|---------|
| 1. 优点有据 | 每条优点配可核验证据 (数据/实验/对照)；无证据的优点不写，不设条数下限 |
| 2. 缺点真实 | 缺点来自实际观察到的缺口或失败，说明影响方向与条件；改进幅度有依据才量化，不凑条数 |
| 3. 改进可行 | 改进路径说明所需数据/算力/时间及预期改变的证据，不设条数下限 |
| 4. 推广有界 | 推广说明适配条件与需修改的假设；无合理推广时如实说明，不硬写 |
| 5. 自我批判可信度 | 不写"假设理想化"等套话 (anti_patterns.md 自动检) |

---

### Stage 8 — 论文写作

| 维度 | 满分行为 |
|------|---------|
| 1. 摘要闭环 | 按题问覆盖模型、结果、验证和边界，摘要主张全部通过证据追踪 |
| 2. 章节完整性 | 动态子问骨架覆盖题面全部交付，无空节 |
| 3. 公式 / 图表 / 引用 | 编号规范，图表绑定主张和上游数据，引用来源可核验 |
| 4. 语言质量 | 句长适度,无明显语病，术语准确；phrase_bank 仅作可选参考，命中率不作评分依据 |
| 5. 视觉一致性 | 字号/配色/字体 全文统一,无 Word/Excel 默认输出 |

---

### Stage 9 — 终稿审核

5 视角 panel (Layer 3),每个 panelist 独立打分:

| Panelist | 关注 |
|----------|------|
| **数学严谨** | 定理引用、推导、边界条件、单位 |
| **模型创新** | 真实机制差异、缺口驱动的模块组合、文献新颖度 |
| **代码正确** | 复现性、注释、变量名、可读性 |
| **写作呈现** | 摘要、章节、图表、引用、配色 |
| **评委视角** | 30 秒能不能 get 到核心? "想给一等奖的冲动" |

每位 panelist 输出:
```json
{"panelist": "...", "scores": {dim1..dim5}, "verdict": "first|second|third|sub_award", "must_fix": [...]}
```

聚合器:
- 找最低分 panelist 的 must_fix
- 定向重跑对应阶段一次
- 重跑后再次 panel,若仍未达标则提交 (时间预算优先)

---

## 阈值汇总 (与 SKILL.md / feedback_layer1_critic.md / score_artifact.py 统一)

**verdict 优先级 (从高到低)**:

| verdict | 触发条件 | 行为 |
|---------|---------|-----|
| `block` | issues 含 ≥1 high-severity | 暂停 skill, 用户介入 |
| `pass_early` | raw_min ≥ 9 AND weighted_mean ≥ 9 | iter-1 早退, 节省 token |
| `pass` | raw_min ≥ 7 AND weighted_mean ≥ 8 | 进下一阶段 |
| `pass_with_review` *(stage 5)* | 任 Qi mark_for_review 但加权阈值满足 | 进 stage 6, L2 必读 review_qis |
| `refine` | 其他 | section-patch 精修, iter+=1 (cap 3) |
| `refine_partial` *(stage 5)* | 任 Qi.min < 7, 但其他 Qi 已 pass | 仅 refine 标记 Qi, 不动其他 |
| `carryover` | iter == 3 仍 refine 或 refine_partial | 进下一阶段, 标记由 L2 处理 |

`weighted_mean` = Σ(s_i × w_i) / Σ(w_i), 其中 w_i 来自 `config/dim_weights.json` 题型加权 (clamp [0.7, 1.5]); `task_type=default` 全 1.0 等价老逻辑。

**自评性质 (候选版新增)**: L1 分数由产出方或其同族模型自评，按 `references/workspace_protocol.md` §7 一律视为**待验证信号**，不是质量证明。verdict 的实质约束力来自 high-severity issues 与 `rating_contract.json` 的 hard_fail_rules，分数阈值只驱动流程节奏（是否精修/早退），不得被正文、摘要或交付说明引用为质量证据。stage 9 panel 与终审必须独立复核产物本身。数量配额（变量数、候选数、图数、假设数、优缺点条数、词库命中率）一律不作为评分依据。

**与等级对应** (用于评估 / 不直接驱动 verdict；下表为内部经验猜测，无公开校准来源，禁止作为获奖承诺):
| 大致等级 | 单维最低 | 均值 |
|---------|---------|------|
| 一等奖 | ≥8 | ≥9 |
| 二等奖 | ≥7 | ≥8 |
| 三等奖 | ≥6 | ≥7 |
| 不达标 | <6 | - |

---

## 与 winning_patterns / anti_patterns / empirical 的对应

本文件 rubric 项 ↔ `competitions/<comp>/winning_patterns.md` 段落 (路径按 decision_log.competition dispatch):
- abstract.* (stage 8 dim 1) → patterns §1, §9 + anti_patterns §A
- paper.section_completeness (stage 8 dim 2) → patterns §2 + anti_patterns §I
- paper.figure_density → patterns §3 + anti_patterns §E
- model.naming (stage 3 dim 3) → patterns §4 + anti_patterns §C1
- subproblems.cross_reference (stage 5 stage-level dim 2) → patterns §5 + anti_patterns §G
- assumptions.support (stage 4 dim 2) → patterns §6 + anti_patterns §B
- sensitivity.multivariate (stage 6 dim 1) → patterns §7 + anti_patterns §F
- evaluation.limitations_real (stage 7 dim 2) → patterns §8 + anti_patterns §H

统一评分先加载 `config/rating_contract.json`，竞赛 overlay 只覆盖差异。数量指标只有同时被评分契约与 `empirical.json.scoring_policy.allowed_reference_metrics` 允许时才能注入 evidence。国赛、研究生赛和华数杯只允许可靠的摘要长度与页数用于校准；图表数、章节数、正文字数和词频不得作硬阈值。MCM / 电工杯 seed v0.1 应弱化数值判断，强化问题匹配。
- evaluation.real_critique → patterns §8
