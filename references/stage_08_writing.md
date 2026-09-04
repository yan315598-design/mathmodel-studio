---
stage: 8
name: writing
duration_h: 12-30
inputs: [decision_log.stages.0-7, decision_log.competition, decision_log.task_type]
outputs: [stage.8.{section_word_counts, figures_per_subproblem, tables_per_subproblem, abstract_drafts, anchor_phrase_hits, danger_phrase_hits}, paper.tex]
loads_reference: [competitions/<competition>/winning_patterns.md, competitions/<competition>/phrase_bank.md, competitions/<competition>/anti_patterns.md, competitions/<competition>/empirical.json]
loads_template: [competitions/<competition>/paper_skeleton.md, competitions/<competition>/abstract_template.md, templates/latex/<competition>/]
feedback: [L1, L2_at_end]
next: stage_09_review
---

# Stage 8 — 论文写作 (摘要三遍制)

**时长**: 12-30h（按竞赛和题目复杂度） | **反馈层**: L1 | **占整个 skill 时间约 25-30%**

---

## 目标

把前面 0-7 阶段的产出**装配**成最终论文。**不重新建模, 不重新求解** (若发现需要, 触发 L2 而非自行回退)。页数与摘要长度只作样本校准，提交格式与证据闭环优先:
- cumcm: 中文摘要按逐问闭环；历史页数和字数只作样本参考
- huaweibei: 页数与摘要长度只参考本地 190 篇完整覆盖分位，不设硬性获奖门槛；摘要按逐问方法—结果—验证闭环
- huashubei: 18 篇样本只校准信息密度；图表数和正文字数不设获奖门槛
- mcm: 总 PDF ≤ 25 页 (含摘要页/正文/参考文献/附录, 以当年官方通知为准), 1-page Summary 250-350 词 + Letter (D/E/F), Memo/Letter 写法见 `competitions/mcm/memo_letter_guide.md`  (英文)
- diangong: 25-30 页, 4 段式摘要 600-1000 字 (中文工程)
- apmcm: 23-54 页, 五段式摘要约 800 字 (中文, 本地 12 篇 p25-p75)

---

## 输入

- stage 0-7 全部 decision_log 内容
- **按 competition 加载** (路径: `<skill>/competitions/<decision_log.competition>/`):
  - `paper_skeleton.md` (论文骨架)
  - `abstract_template.md` (按竞赛独立模板加载；研究生赛与华数杯不得互换)
  - `winning_patterns.md` (写作 anchor)
  - `phrase_bank.md` (写作 anchor)
  - `anti_patterns.md§A_I` (写作时回避)
  - `empirical.json` (只对完整覆盖且被 scoring_policy 允许的字段注入 evidence)
- LaTeX 模板: `<skill>/templates/latex/<competition>/`

### 三赛动态写作入口

国赛、研究生赛和华数杯先由 agent 生成 Stage 8 知识包，再运行 `scripts/generate_paper_plan.py` 生成动态章节、图表计划和证据账本。读取 `figure_story` 和 `writing_blueprint` 时遵守：

- 每问按“为什么需要该步骤—模型与输入—中间状态—数值结果—针对风险的验证—直接回答题问”成段。
- 图表按“结构/机制、过程/中间层、结果、可信边界”组成一组，正文逐图解释其支撑的结论。
- `result_disagreements` 用来提醒单位、分母、基线和目标函数口径，不得复制历史数值。
- 只迁移叙事结构，不复制历史论文原句；evidence ID 是内部审计线索，不直接替代正式参考文献。
- `huaweibei` 如需参考数模之星写法，只按 evidence ID 定向读取 `papers/manual_paper_reviews.json`；2022—2025 不标记或推测提名身份。
- 每个摘要主张写入前必须在 `evidence_ledger` 中形成 `question → model → result → validation → figure → abstract_claim` 完整链；运行 `scripts/trace_claims.py --strict` 未通过时不得定稿摘要。
- 华数杯图表数量只作样本观察，不设固定获奖门槛；每张图必须绑定唯一主张、上游数据和必要检查。
- **现存 6 套自写模板** (v7.5 路线 A 收敛, 旧 13 套第三方模板已全部剥离):
  - cumcm / huaweibei / huashubei / mcm / diangong / apmcm, 均为本项目自写资产并预编译验证; 模板存在不代表对应知识分支可混用
  - 英文论文统一用 `templates/latex/mcm/main.tex` (英文仅此 1 套)
  - 全部用 xelatex (中文) 或 pdflatex (英文), 走 `main_template` 模式 (复制 main.tex + 自动注入 sections/<sec>.tex)

## 产出

- `paper.tex` (或 markdown 中间产物 + 转 tex)
- `figures/` 全部图 (统一配色)
- `tables/` 全部表 (LaTeX booktabs)
- 最终 PDF (xelatex 编译)

---

## Codex 写作工作台

用户如果只说"写摘要"、"写问题分析"、"写模型段"、"写结果解释"或"写图表说明", 不强制进入完整 Stage 8。按下面路由局部完成, 默认不写 state:

| 用户任务 | 必读资料 | 输出 |
|---|---|---|
| 摘要 | `<comp>/abstract_template.md`, `<comp>/phrase_bank.md`, stage 5-7 结果 | 中文摘要或 MCM Summary, 含问题分解、方法、关键数值、稳健性、推广价值 |
| 问题分析 | 题面、stage 2 分解、`paper_skeleton.md` | 每问一段"本质-难点-方法-承接" |
| 模型段 | stage 3-5 产出、符号表 | 变量、目标函数、约束、算法步骤、求解说明 |
| 结果解释 | stage 5 结果、stage 6 稳健性 | 数值结论 + 物理意义 + 对题问的回答 |
| 图表规划/生成/说明 | `references/figure_skill_bridge.md`, figures/tables、`distilled_figures.md`(如有) | 图表计划、论文图生成要求、图注、坐标单位检查、正文解释句 |

Codex 子菜单见 `references/codex_practical_menu.md`。如果用户选择"图表规划/生成/质检", 先用 `figure-table-planner` 思路确定 Type 1-4, 再用 `math-figure-generator` 生成论文图, 最后按 `nature-figure` 质检可读性。若用户选择"让我决定", 优先补摘要或结果解释, 因为这两项最影响评委第一印象。

---

## 写作顺序 (反直觉但有效)

**摘要三遍制** (v7.4.0 修订, 与 `references/huashubei_battle_plan_72h.md` 的"摘要写 3 遍"对齐): 骨架期写初稿定主线（6 句式: 问题→方法→关键结果→验证→结论）→ 全部结果完成后按证据账本重写 → 终审前终审润色; 最终版以 `scripts/trace_claims.py --strict` 闭环为准。

```
1. 写正文 §1 问题重述         (30 min, 用 templates/shared/restatement_card.md)
2. 写正文 §2 问题分析         (1h)
3. 写正文 §3 模型假设         (30 min, 复用 stage 4)
4. 写正文 §4 符号说明         (15 min, 复用 stage 4)
5. ⭐ 摘要初稿定主线          (30 min, §1-§4 骨架成后写 6 句式, 不写定量细节)
6. 组装 §5.1 Q1 模型与求解   (1-1.5h, 基于 stage 5 章节草稿卡 q1_draft.md 扩写+统一文风; 无草稿卡时才从零写, 2-3h)
7. 组装 §5.2 Q2              (1-1.5h, 同上)
8. 组装 §5.3 Q3              (1-1.5h, 同上)
9. 写正文 §6 灵敏度          (1h, 复用 stage 6)
10. 写正文 §7 评价与推广      (1h, 复用 stage 7)
11. 写正文 §8 参考文献        (30 min, 整理)
12. 写附录 (代码 + 数据表)    (30 min, 用 templates/shared/appendix_checklist.md)
13. ⭐ 摘要重写 (结果完成后)   (45 min, 按 evidence_ledger 证据账本逐问重写; huaweibei 按 writing_voice.md §2 六要素密度检查)
14. ⭐ 整篇 L1 自评 + 修订    (1-2h)
15. ⭐ 摘要终审润色           (30 min, 终审前)
```

理由: 初稿防跑偏 (先把 6 句主线定下来, 正文围绕主线展开), 重写防"摘要绑架" (定量结果全部落定后按证据账本重写, 每个数字可追踪), 终审润色只改表达不改数据。

每节成稿后立即跑两个小循环 (v7.4.0 新增):
- **引用缺口补查**: 本节需要文献支撑而现有文献不够时, 按 `references/reference_skill_bridge.md` 补查, 硬上限 5 次搜索, 够用即停。
- **去 AI 味自查**: 按 `references/ai_flavor_removal.md` 的 8 条 yes/no 清单自查本节, 不过就地修改后再进下一节。

---

## 各节写作详细 prompt

### §1 问题重述 (1-2 页, 30 min)

**快速卡**: `templates/shared/restatement_card.md` (结构/字数/边界/写后自查)。

**关键**: 不要原文照抄, 要用自己语言提炼。

模板:
```
1. 问题背景

随着 <领域>的不断发展, <问题>已成为亟需解决的关键问题。
本题以 <具体场景>为背景, ...

2. 问题描述

题目给出了 <数据资源>, 要求解决以下三个子问题:

问题一: <自己语言重述, 不直接抄题>
问题二: ...
问题三: ...
```

字数: 600-1200 字。
**禁止**: 大段抄题。**禁止**: 仅用 1 句话重述 (信息密度太低)。

### §2 问题分析 (2-3 页, 1h)

每子问题一段:
```
2.1 问题一分析

本质上, 问题一是一个 <类型>问题。需要在 <约束>下, 寻找 <决策变量>使 
<目标函数>取得最优。

由于 <难点>, 直接求解较为困难。本文采用 <策略>: ...
图 1 给出了问题一的求解流程。

[流程图占位]

(衔接到 §5.1)
```

**关键加分**: 流程图 (mermaid 转 PNG / TikZ)。

### §3 模型假设 (0.5-1 页, 30 min)

直接复用 `decision_log.stages.4.assumptions`:

```
3. 模型假设

为简化模型并保证可解性, 本文做出如下假设:

(1) **短期内市场需求服从泊松分布。**
    依据: 文献 [3] 表明零售业短期需求服从泊松; 附件 1 数据 χ² 检验 p=0.34 不拒绝。

(2) ...

(3) ...
```

3-7 条, 每条带支撑 (winning_patterns §6)。

### §4 符号说明 (0.5-1 页, 15 min)

LaTeX 表格 (booktabs):

```latex
\begin{table}[h]
\centering
\caption{符号说明}
\begin{tabular}{cccl}
\toprule
符号 & 含义 & 单位 & 类型 \\
\midrule
$x_i$ & 第 $i$ 个产品产量 & 件 & 决策变量 \\
$p_i$ & 第 $i$ 个产品单价 & 元/件 & 参数 (附件 1) \\
$d_i$ & 第 $i$ 个产品需求 & 件 & 随机变量 \\
\bottomrule
\end{tabular}
\end{table}
```

≥10 行, 全单位 (anti_pattern B5)。

### §5 模型建立与求解 (12-16 页, 6-9h, 主体)

每子问题 4-6 页, 结构严格:

```
5.1 问题一: <模型族变体名>

5.1.1 模型建立

本节针对问题一建立 <动态权重 AHP-熵权混合评价> 模型 (winning_patterns §4 命名变体).

设 <决策变量, 引用 §4>。
目标函数: ...
$$\max f(x) = \sum_i (p_i - c_i) x_i \quad \text{(5.1)}$$

约束条件:
$$\text{(C1)} \quad \sum_i c_i x_i \leq B \quad \text{(5.2)}$$
$$\text{(C2)} \quad x_i \in \{0, 1, ..., 50\} \quad \text{(5.3)}$$

5.1.2 求解算法

针对 (5.1)-(5.3), 我们采用 Lagrangian 松弛, 具体步骤如下:
**Step 1**: ...
**Step 2**: ...

算法流程见图 2。

[流程图]

5.1.3 求解结果与分析

通过 Python 调用 cvxpy + GUROBI 求解, 经 4.2 秒收敛, 得到最优解 x* = (12, 0, 25, ...), 
最优利润 87234 元 (相比贪心基线 +12.3%)。

[图 3: x* 分布柱状图]
[图 4: 与基线对比]

求解结果显示, ... <stage 5 物理意义讨论, 复用>。
```

**强制 checklist** (winning_patterns §3, §4, §5, §8):
- [ ] 模型有命名变体
- [ ] 公式编号 ≥5 个 (整个 §5.1)
- [ ] 流程图 + 结果图 + 灵敏度图 ≥3 张
- [ ] 数据表 ≥1
- [ ] 物理意义段 ≥1
- [ ] (Q3) 显式引用 Q1/Q2 结果

### §6 灵敏度分析 (2-3 页, 1h)

直接复用 `decision_log.stages.6`:

```
6. 灵敏度分析与稳健性检验

6.1 分析方法

为评估模型对参数变化的敏感程度, 本文采用拉丁超立方抽样 (LHS) 
对 ($p, c, B$) 进行联合扰动, 在 ±5%, ±10%, ±20% 三档下各抽样 200 个点。

6.2 分析结果

[表 N: 稳健区间]
[图 N: pairs plot]
[图 N: tornado]

6.3 失稳预警

实验进一步发现, 当预算 $B$ 减少 30% 以上时, 最优解切换为 ... 
(从 stage 6 直接复用)
```

### §7 模型评价与推广 (1-2 页, 1h)

直接复用 `decision_log.stages.7`:

```
7. 模型评价与推广

7.1 模型优点
(1) **<优点 1>**: <证据>。
(2) ...
(3) ...

7.2 模型缺点

(1) **<缺点 1>**: 当前 <现象>。若改用 <替代方法>, 在 <指标> 上可提升 X%, 
    但需 <代价>。
(2) ...
(3) ...

7.3 模型改进方向
(1) **<改进 1>**: ...

7.4 模型推广

本模型可推广至 **<场景 1>**, 适配方式: ...
也可推广至 **<场景 2>**, 适配方式: ...
```

### §8 参考文献 (0.5-1 页, 30 min)

**国赛要求 ≥10 条**, 用 GB/T 7714 格式:

```
[1] 张三, 李四. 基于 ... 的 ... 研究 [J]. 系统工程学报, 2023, 38(4): 567-580.
[2] Smith J, Doe A. A novel approach to ... [J]. Operations Research, 2024, 72(3): 1234-1250.
[3] ...
```

类型混合: ≥4 中文期刊, ≥3 英文期刊, ≥1 教材或工具书。

### 附录 A: 程序代码 (30 min)

**清单卡**: `templates/shared/appendix_checklist.md` (内容白名单/代码规范/正文-附录引用对应/页数控制)。

每段代码 (anti_pattern D1):
- 中文注释
- 首行 "对应 §X.Y.Z"
- 删除 print 调试残留

```python
# Q1 求解 - 对应论文 §5.1.2
# Lagrangian 松弛混合整数线性规划
import numpy as np
import cvxpy as cp

# 加载数据
...
```

### ⭐ 摘要 (三遍制: 初稿定主线 → 结果完成后重写 → 终审前润色)

按上文"写作顺序"的三遍制执行: 第 5 步写 6 句式初稿, 第 13 步按 evidence_ledger 重写, 第 15 步终审润色; 重写版以 `scripts/trace_claims.py --strict` 的 `abstract_gate=pass` 为定稿前提。

调用 `competitions/<competition>/abstract_template.md`（按竞赛加载, 研究生赛与华数杯不得互换）:

```
本文针对 <核心任务>, 综合考虑 <因素 1, 2, 3>, 建立了 <核心模型族>模型, 
通过 <求解方法> 求解, 得到 <总体定量结果>。

针对问题一, ... 得到 <定量结果 1>。
针对问题二, ... 得到 <定量结果 2>。
针对问题三, ... 得到 <定量结果 3>。

对模型进行了多变量联合灵敏度分析, 在参数 ±10% 扰动内, 输出指标偏差小于 X%, 
验证了模型的稳健性。

本文创新点在于: 
① <创新点 1>; 
② <创新点 2>; 
③ <创新点 3>。

所建模型可推广至 <场景 1> 和 <场景 2>。

**关键词**: <核心问题>, <核心方法>, <辅助方法>, <分析手段>, <应用领域>
```

**严格自检**:
- 字数 600-900 (anti_pattern A5)
- ≥3 个定量结果 (anti_pattern A1)
- 5 段顺序正确 (anti_pattern A2)
- 与正文一致 (anti_pattern A3)
- 关键词 4-6 个高质量 (anti_pattern A4)

---

## L1 Rubric

先读取 `config/rating_contract.json`，再由当前竞赛 `rubric_overlay.json` 覆盖差异。下表只表示默认中文论文基线，华数杯 Stage 8 使用六维 overlay。

| 维度 | 满分行为 |
|------|---------|
| 1. 摘要闭环 | 每问都有模型、结果、验证和边界，且通过 evidence trace |
| 2. 章节完整性 | 按动态子问骨架覆盖题面全部交付 |
| 3. 公式 / 图表 / 引用 | 编号规范，图表绑定主张与上游数据，引用可核验 |
| 4. 语言质量 | 摘要 5 段全部命中 phrase_bank §12 anchor + 危险句式零命中 |
| 5. 视觉一致性 | 字号/配色/字体全文统一 |

## 常见坑

- A1-A5 摘要类全部 → 摘要三遍制 + 自检 5 项
- D1 代码无注释 → 中文注释 (附录)
- I1-I5 写作呈现 → `templates/latex/cumcm/main.tex` (自写 ctexart) 自动统一格式

## 退出条件

1. 动态骨架覆盖全部题问，附录按提交要求完成
2. 摘要证据链 `abstract_gate=pass`
3. 每张图表绑定唯一主张、上游数据、必要检查和正文解释
4. 关键公式、结果、图表和引用编号可追踪
5. xelatex (中文竞赛, 含 apmcm) 或 pdflatex (英文 mcm) 编译无错
6. L1 全维 ≥7
7. **L2 跨阶段回检**: 论文内容与 decision_log 0-7 一致, 无新增内容偏离

→ 跳转 `stage_09_review.md`
