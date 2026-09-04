---
stage: 2
name: analysis
duration_h: 2-3
inputs: [stage.1.selected, problem_pdf, attachment_data_paths]
outputs: [stage.2.{decomposition, key_variables, key_constraints, objective_per_subproblem, data_schema, subproblem_dependency}]
loads_reference: [rubrics.md§Stage_2]
feedback: [L1]
next: stage_03_model_selection
---

# Stage 2 — 问题深度解析与分解

**时长**: 2-3h | **反馈层**: L1

---

## 目标

把题目从**自然语言描述**转化为**数学语言骨架**: 识别决策变量、目标函数、约束、子问题间关系。这一步质量决定后续 5/6/8 阶段的天花板。

---

## 输入

- stage 1 输出: 选定题号 + 子问题清单 + 数据路径
- 题目原文 (再读一次)
- 附件数据 (用 pandas/Read 扫一遍 schema)

## 产出

- 子问题分解树 (Q1/Q2/Q3 的输入/输出/约束/目标)
- 关键变量清单 (≥10 个,标注决策/状态/参数)
- 子问题间关联图 (谁依赖谁的结果)
- 目标函数雏形 (符号级,不必精确)
- 数据 schema 与变量映射

---

## 审题门 (v1.0.0 强化, 通过才进操作流程)

**选题错、边界漏、目标偏是最高频翻车源。** 进入分解前必须过三查，每查都有编号确认（选项卡见 `references/decision_ui_map.md` Stage 2）：

| 查 | 内容 | 产出 |
|---|---|---|
| 边界查 | 题面硬约束逐条摘录（数据范围/方法禁令/输出格式/时间粒度）；"题面没禁止但我能用吗"信息清单（用了题设不可知信息 = 解作废） | 边界清单写入真源.md |
| 目标查 | 每问的最小交付是什么（一个数/一个方案/一个排名/一段机理）；目标可判定化（什么叫"够好"——精度阈值/可行性/对比基线） | 最小交付清单 |
| 假设查 | 逐问预列假设草案，标关键/简化两级；每条配支撑来源（文献/数据/常识） | 假设草案表（Stage 4 定稿） |

**质询子 agent（红队）**：三查完成后，按 `references/parallel_dispatch.md` 花名册派一个"审题质询员"（独立 context，只给题面+三查清单，不给你的结论），任务是找茬：边界漏项、目标误读、假设过强、子问遗漏。质询输出逐条处理（采纳/驳回+理由），写入真源.md 修订记录。无子 agent 能力时主 agent 换视角自审并标注 `manual_fallback`。

---

## 操作流程

### Step 1: 题目精读 (30 min)

**精读三遍,每遍不同任务:**

第一遍 (10 min): 抓动词。题目让你做什么? "求最优..." / "预测..." / "评价..." → 决定问题类型。

第二遍 (10 min): 抓约束。哪些条件不能违反? 列出来。

第三遍 (10 min): 抓数据接口。哪些参数题目会给? 哪些要从附件提? 哪些要假设?

### Step 2: 子问题正式分解 (45 min)

对每个 sub-problem Qi,填写卡片:

```
Q1 卡片
├── 自然语言描述: <一句话提炼>
├── 输入:
│   - 题目给定参数: ...
│   - 附件数据: 附件 1 第 X 列
│   - 上游问题结果: 无 (Q1 是入口)
├── 输出 (最终决策变量):
│   - x_1, x_2, ... (含义、单位)
├── 约束:
│   - C1: ...
│   - C2: ...
├── 目标:
│   - 最小化/最大化 <什么>
├── 问题类型: <model_catalog 第几类>
└── 难度估计: easy / medium / hard
```

**关键**: Q3 卡片的"上游依赖"列必须明确写: 是否依赖 Q1 / Q2 结果?
若题目允许且没明示,**默认要求 Q3 复用 Q1/Q2 结果** (winning_patterns §5)。

### Step 3: 关键变量统一编号 (30 min)

跨子问题统一符号 (anti_pattern B4: 符号重复定义):

```
全局变量表 (stage 4 会复制到论文)

| 符号 | 含义 | 单位 | 类型 | 出现于 |
|------|-----|------|------|-------|
| x_i | 第 i 个产品的产量 | 件 | 决策变量 | Q1, Q2 |
| p_i | 第 i 个产品的单价 | 元/件 | 参数 (附件 1) | Q1, Q3 |
| α  | 折扣率 | 无量纲 | 参数 | Q3 |
| ξ  | 需求随机扰动 | 件 | 随机变量 | Q3 |
| ... |
```

≥10 个变量。

### Step 4: 数据 schema 扫描 (30 min)

用 pandas 快速扫附件:

```python
import pandas as pd
df = pd.read_excel("附件1.xlsx")
print(df.shape)
print(df.dtypes)
print(df.describe())
print(df.isnull().sum())
```

输出 schema 卡片:
```
附件 1 (xlsx):
- 行数: 1234, 列数: 8
- 时间跨度: 2020-01 ~ 2024-12 月度
- 缺失: 列 "需求量" 缺失 5%
- 异常: 列 "价格" 有 3 个 outlier (>3σ)
- 与变量映射: p_i ← 列 "价格", d_i ← 列 "需求量"
```

### Step 5: 子问题关系图 (15 min)

以 mermaid / ASCII 表达:

```
Q1 (求最优生产计划) 
  ↓ x_i*
Q2 (考虑库存约束)
  ↓ 库存阈值 K*
Q3 (随机需求下的稳健决策)
  ↓ 引用 Q1 的 x_i* 与 Q2 的 K* 
最终: 决策方案 + 风险评估
```

写入 `decision_log.stages.2.decomposition`。

### Step 6: 目标函数雏形 (30 min)

每个 Qi 写出符号化目标 (不必完整,要框架):

```
Q1: max  Σ_i p_i * x_i  - C(x)
    s.t. Σ_i x_i ≤ B (预算)
         x_i ≥ 0, x_i ∈ Z

Q2: 在 Q1 基础上加约束 K_i ≤ K_max
    
Q3: max E_ξ [ Σ_i p_i * x_i - C(x) - λ * Var(...) ]
    使用 Q1 的 x* 作为 warm start
```

### Step 7: 输出移交 (5 min)

写入 `decision_log.stages.2`:
```json
{
  "decomposition": [...],
  "key_variables": [...],
  "key_constraints": [...],
  "objective_per_subproblem": {"Q1": "...", "Q2": "...", "Q3": "..."},
  "data_schema": {...},
  "subproblem_dependency": {"Q1": [], "Q2": ["Q1"], "Q3": ["Q1", "Q2"]}
}
```

---

## 图表规格冻结 (v7.4.0 新增)

解析完题面 (Step 1-6) 即定图表规格, 不等出结果后临时规划。历史实战教训：图表规格未提前冻结导致多轮返工，初版一图 2-3 条线信息密度过低。

**动作**:

1. 每个子问题给张数预算 (多子问题赛制总量 10-20 张起步)。
2. 每张图在 `真源.md` 图表登记表 (`references/workspace_protocol.md` §2) 登记四要素:
   - **回答什么问题** (无论证价值的图不画)
   - **数据源** (`results/` 哪个文件或哪段中间状态)
   - **色板** — 取自 `templates/figures/style/palettes.py` 八套之一 (默认 academic_blue; 另有 v7.7 期刊板 npg / aaas / lancet / nejm), 选用规则见 `references/color_typology.md`
   - **类型** — 过程图 (机理 / 中间状态 / 算法行为) 还是结果图
3. 信息密度标准: 每图 ≥2 个信息维度 (如 对比+趋势 / 灵敏度+排序), 过程图:结果图 ≈ 1:2。
4. 规格 24h 后冻结; 变更须在 `真源.md` 修订记录登记 (时间/原因/影响)。

**与 `scripts/generate_paper_plan.py` 的关系**: 该脚本从案例库生成图表候选, 每张带四要素 (role / supports_claim / upstream_data / required_checks); 本节登记表由 agent 对当前题目定制并作为权威。两者互补: 脚本候选可并入登记表, 冲突时以登记表为准。

---

## L1 Rubric (`rubrics.md` Stage 2)

| 维度 | 满分行为 |
|------|---------|
| 1. 子问题分解清晰度 | 每 Qi 卡片完整 |
| 2. 关键变量识别 | ≥10,标注类型 |
| 3. 数学化程度 | 每 Qi 有目标雏形 |
| 4. 数据契合度 | schema 已扫,变量映射清楚 |
| 5. 子问题关联性 | Q3 是否依赖 Q1/Q2 已识别 |

---

## 常见坑

- 题目仅读一次就开干 → 强制读 3 遍
- 子问题间符号不统一 (B4) → 统一变量表
- 附件数据没扫 → strictly 必做 Step 4
- Q3 没考虑复用 Q1/Q2 (G1) → Step 2 卡片"上游依赖"列硬要求

---

## 退出条件

1. 三个子问题卡片完整
2. 全局变量表 ≥10 项
3. 数据 schema 扫描完成
4. Q3 复用关系明确 (是 / 否,有理由)
5. L1 rubric 全维 ≥7

→ 跳转 `stage_03_model_selection.md`
