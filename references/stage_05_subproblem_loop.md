---
stage: 5
name: subproblem_loop
duration_h: 6-12 per Qi
inputs: [stage.2.decomposition, stage.3.selected_per_subproblem, stage.4.{assumptions, symbols}]
outputs: [stage.5.sub_problems.{Qi}.{model_name, math_formulation_path, code_path, results_path, figures, key_metrics, physical_meaning_summary, scores, iterations}, stage.5.cross_reference_chain, stage.5.assumption_change_history, state/evidence_ledger.json]
loads_reference: [model_catalog.md, winning_patterns.md(验证与风险节), rubrics.md§Stage_5]
loads_template: [code_starter/<problem_type>.py]
feedback: [L1_per_Qi, sub_checkpoint, L2_at_end_for_stage_3_4_consistency]
next: stage_06_robustness
---

# Stage 5 — 递归子问题循环 (Q1..Qn)

**时长**: 6-12h × n 个子问题 | **反馈层**: L1 + 子检查点 | **占整个 skill 时间约 50%**

---

## 目标

按 `references/modeling_evidence_protocol.md` 为每问完成建模、正式求解、验证和分析，并更新真源中的答题义务。跨问只建立题面要求或机制支持的依赖；题面指定固定输入时保持独立。

**并行加速 (0.7.4 新增)**: 题面无依赖的 Qi（见 stage 2 的 `subproblem_dependency`）可按 `references/parallel_dispatch.md` 派子 agent 并行求解——并行前先冻结 stage 4 符号表与假设表（写锁）, 合并时做符号/单位/编号冲突检查; 有依赖的 Qi（如 Q3 用 Q2 的输出）保持串行, 沿用本章单 Qi 循环。

---

## 输入

- stage 2 子问题卡片
- stage 3 选定模型 + toy demo 通过
- stage 4 假设/符号/术语
- 仅在题面和机制需要时加载相应上游结果；不是默认 Qi-1

**加载时核对 (v2.3.0)**: 进入 stage 5 前先核对 `decision_log.stages.5.qi_count` 与题面实际子问数是否一致（该值在 stage 2 分解确认后按实际子问数写入，见 `references/stage_02_analysis.md`）；不一致时不要开始循环，先回到 stage 2 修正分解与 `qi_count`/`qi_weights`，否则 gate 5 的三来源对齐检查必然拦截。

### 三赛子问级案例约束

当 `competition` 为 `cumcm`、`huaweibei` 或 `huashubei` 时，每个 Qi 开始前由 agent 运行 `scripts/build_stage_pack.py --competition <competition> --stage 5`，读取命中子问的模型接口、上游中间量、`required_solution_checks` 和 evidence ID：

1. 用逐问依赖核对本问输入是否真正来自上游，而不是并列拼接模型。
2. 从假设风险中选出会改变当前结论的 1—3 项，写入本问检查点。
3. 必做验证按“风险—中间量—验证方法—判据”落地，不能只写“模型稳定”。
4. 历史结果只能用于数量级警戒和口径核对，禁止作为当前求解输出或正确答案。
5. 每个采用的历史结构记录案例 ID 和 evidence ID，正式论文引用仍需回到可引用原文。
6. 研究生赛提名论文子问可提供全文页码证据；华数杯蒸馏任务链必须标明不是原题逐问。

## 产出

- 每 Qi 的: 数学模型完整公式 + 求解代码 + 数值结果 + 物理意义讨论 + **章节草稿卡** (`paper_workspace/sections/q{i}_draft.md`, 内容覆盖下述五项即可，长度由内容决定, 趁热在上下文最新鲜时写)。图表口径: 每张图须绑定一个主张和上游数据，数量由论证需要决定（不设每问下限）；经 D.1 菜单用户确认数量与样式后生成。
- 每问追加一行 `state/evidence_ledger.json` (见 E2/E3, stage 8 paper_plan 的 evidence_ledger 子集, 供 trace_claims 审计)
- 跨子问题: 依赖或独立输入的依据、单位和信息边界明确
- **对照证据 (候选版)**：结果节必须有同口径横向对照（主模型 vs 基线；若 stage 3 登记了失败/备用路线或实际出现过失败路线，一并列出含负数）。模型含新增模块时给消融（去掉该模块的结果）；无新增模块或无可信失败路线时记录依据，不虚构。对照表口径（划分/指标/预算）逐列一致；模块无增益如实报告，不撤下。
- 写入 `decision_log.stages.5.sub_problems.{Q1, Q2, Q3, ...}`

图表生成必须遵守 `references/figure_skill_bridge.md` 和 `references/knowledge_workflow.md`：先写 `role / supports_claim / upstream_data / required_checks`，再用 `math-figure-generator` 生成 Type 3 论文图或 Type 4 附录图，不把默认 matplotlib 草图直接放进正文。

---

## 递归循环结构

```
for Qi in [Q1, Q2, ..., Qn]:
    A0. 本问选型确认 (必停点, v2.6.0)
    A. 模型完整化 (45 min)
    B. 求解实现 (2-4h)
    C. 结果验证 (30 min)
    D. 子灵敏度 (1h, optional 但建议)
    D.1 图表选择菜单 (必停点, 用户拍板后才出图, 见下)
    E. 物理意义 (15 min)
    E2. 章节草稿卡 (20-30 min, write-as-you-solve, 见下)
    E3. evidence_ledger 追加 (5 min)
    F. L1 自评 + 必要时 diff-only 精修
    G. 输出移交 (写 decision_log)
    H. 子检查点: Qi 是否引用上游? 符号是否与 stage 4 一致?
```

### E2. 章节草稿卡 (write-as-you-solve, v2.0.0)

每问验证通过后**立即**写该问的论文章节草稿卡, 存 `paper_workspace/sections/q{i}_draft.md`。此时求解上下文最新鲜, 拖到 Stage 8 再回忆会丢细节、出口径漂移。

草稿卡内容 (每问一张, 是给 Stage 8 组装的半成品, 不是终稿; 长度由内容决定):
1. 模型段草稿: 目标式 + 约束 + "式中:"解释块骨架 (符号/含义/单位/机制角色)
2. 求解段草稿: 算法 + 关键参数赋值及依据 + 停止条件
3. 结果段草稿: 分组定量结果 (带单位) + 运行时间/规模 + 成立条件 + **同口径横向对照表（主模型/基线/失败路线）与关键模块消融**
4. 图注草稿: 每张图的图前引导句 + 图后解读句 (看见什么→支持什么→不能推出什么)
5. 移交句: 本问产出给 Q_{i+1} 的中间量清单

写作语气与定量密度按 `competitions/<comp>/writing_voice.md` (华为杯) 或通用写作规范执行。草稿卡数字必须引用已冻结数字, 禁止手抄。

每问草稿卡完成后, 同步向 `state/evidence_ledger.json` 追加该问一行 (JSON 数组, 不存在则新建)。字段: `question` (如 Q1)、`model` (模型名+一句话)、`result` (关键定量结果, 引用冻结数字)、`figure` (图表文件名或结果表编号)、`validation` (验证方式)、`abstract_claim` (该问摘要句, 可先空)、`evidence_ids` (结果/代码文件路径; 溯源元数据——trace_claims 审计前六项, 此字段供人工回查与打包核验, 强烈建议填写)。该文件是 stage 8 paper_plan 的 evidence_ledger 子集, `scripts/trace_claims.py` 两种输入 (`state/paper_plan.json` 或独立 ledger) 均可消费——短程/中断的运行也能被证据链审计。

---

## 单 Qi 操作流程详解

### A0. 本问选型确认 (必停点, v2.6.0)

进入求解前（A 之前）亮出本问选型——主模型 + baseline + 条件性备用及触发条件 + 依据与文献来源 + 失效边界（与 stage 3 选择卡"档案五列"同口径）, 用户拍板后才进 A/B:

- 本问选型与 stage 3 已拍板方案（`decision_log.stages.3.selected_per_subproblem["Q<i>"]`）**一致**时, 只做轻量确认: 一行摘要 + 编号菜单 `1 继续 2 换模型 3 看完整候选档案`。
- **不一致或本问无 stage 3 记录**时, 必须出完整选择卡（按 `stage_03_model_selection.md` 选择卡规格, 档案五列含"依据与文献"）。
- 登记必停点 `decision_log.checkpoints.per_qi_selection["Q<i>"]`, 条目形如 `{"status": "answered", "asked_at": "<ISO>", "answer": "<用户选择摘要>", "source": "chat"}`（runtime 侧经 CLI answer 登记的条目 source 为 user_cli, 同形）; source 缺失或非 chat/user_cli 视为未答, check_gate 拦截（见 SKILL.md 必停点协议）。
- 确认后更新《选型总表》`cwd/selection_sheet.md` 对应行（stage 3 生成初版, 本步更新该问行）。
- `check_gate.py --gate 5` 与 `--checkpoint per_qi_selection.Q<n>` 逐问校验。

### A. 模型完整化 (45 min)

把任务对应的数学对象与实际入选模型升级为正式公式，先检查概念代理和模块接口。以下优化示例不适用于所有题型：

```
问题 Q1 数学模型 (基于 Lagrangian 松弛的混合整数线性规划):

Decision Variables:
  x_i ∈ {0, 1, ..., 50}, i = 1, ..., 100

Parameters:
  p_i: 单价 (元/件), 来自附件 1 列 P
  c_i: 成本 (元/件), 来自附件 1 列 C
  B: 总预算 (元), B = 100000

Objective:
  max f(x) = Σ_i (p_i - c_i) x_i

Constraints:
  C1: Σ_i c_i x_i ≤ B             (实际成本预算)
  C2: x_i ≤ 50                     (单品上限)
  C3: x_i ≥ 0, integer

求解技术:
  下例直接调用 MILP 求解器；未实现拉格朗日松弛，不以其命名。
```

要求:
- 每个变量、参数、约束都有编号
- 公式用 LaTeX (即使现在是 markdown, stage 8 直接复制)
- 新增模块只在实际实现且有对照证据时讨论贡献，不要求存在改进

### B. 求解实现 (2-4h)

用 Python (numpy/scipy/sklearn/cvxpy) 实现。**约定**:

```python
"""
Q1 求解 - 对应论文 §5.1
带成本预算的整数线性规划
"""
import numpy as np
import pandas as pd
import cvxpy as cp
import matplotlib.pyplot as plt
np.random.seed(42)  # 可复现性

# Step 1: 加载数据
df = pd.read_excel("data/附件1.xlsx")
p = df["price"].values
c = df["cost"].values
n = len(p)
B = 100000

# Step 2: 建模
x = cp.Variable(n, integer=True)
profit = (p - c) @ x
constraints = [
    c @ x <= B,
    x >= 0,
    x <= 50
]
prob = cp.Problem(cp.Maximize(profit), constraints)

# Step 3: 求解
prob.solve(solver=cp.GLPK_MI)
print(f"Q1 求解状态: {prob.status}")
print(f"目标函数值: {prob.value:.2f}")
print(f"求解时间: {prob.solver_stats.solve_time:.2f} s")

# Step 4: 保存结果
if x.value is None:
    raise RuntimeError(f"No usable solution: {prob.status}")
x_star = np.rint(x.value).astype(int)
if np.any(x_star < 0) or np.any(x_star > 50) or c @ x_star > B + 1e-6:
    raise RuntimeError("Rounded solution is infeasible")
np.save("results/Q1_x.npy", x_star)
```

代码要求:
- 中文注释 (anti_pattern D1)
- 首行明确 "对应论文 §X" (正文-代码双向可追踪)
- 设 random seed (anti_pattern D4)
- `print` 关键状态 (sanity check)
- 结果保存到 `results/Qi_*.npy` 或 `.csv`

### C. 结果验证 (30 min)

在正式调用函数上检查，不另写理想化玩具算法替代：

1. **状态**：区分可行、最优、超时、不可行；仅有可行解不声称最优。
2. **约束与单位**：重算守恒、容量、时段、预算和接口增量。
3. **反例**：优先测试目标会偏好的错误行为、边界、离散化和接口。
4. **对照**：基线也须可行，输入/权限/评价定义一致；允许相同或更差。

```python
# 边界 case 测试
if np.any(c <= 0):
    raise ValueError("This baseline assumes positive unit costs")
x_greedy = np.zeros(n, dtype=int)
remaining = float(B)
for i in np.argsort(-((p - c) / c), kind="stable"):
    if p[i] <= c[i]:
        continue
    x_greedy[i] = min(50, int(remaining // c[i]))
    remaining -= c[i] * x_greedy[i]
assert c @ x_greedy <= B + 1e-6
profit_greedy = ((p - c) * x_greedy).sum()
print(f"贪心基线利润: {profit_greedy:.2f}")
print(f"本模型利润: {prob.value:.2f}")
if profit_greedy > 0:
    print(f"相对提升: {(prob.value - profit_greedy) / profit_greedy * 100:.2f}%")
else:  # 贪心基线利润为 0 时相对提升无定义, 输出绝对差并标 N/A, 不让 sanity check 崩溃
    print(f"绝对差: {prob.value - profit_greedy:.2f} (贪心基线为 0, 相对提升 N/A)")
```

约束/实现/口径检查失败则修复或标明不适用；性能未改善不判实现失败。将失败及剩余答题义务保留到移交。

### D. 子灵敏度 (1h, 强烈建议)

只对本子问题做局部灵敏度 (全局留 stage 6)。**本步只计算并落盘结果, 不出图**——图表要等 D.1 菜单用户确认后在 D.2 生成:

```python
# 对单价 p 做 ±10% 扰动
deltas = [-0.1, -0.05, 0, 0.05, 0.1]
profits = []
for d in deltas:
    p_perturb = p * (1 + d)
    # 固定方案换参数评价，并非重新求解
    profit_d = (p_perturb - c) @ x_star  # 用同一 x*, 看新参数下利润
    profits.append(profit_d)

# 只落盘机器可读结果; 画图在 D.1 确认后的 D.2 做
pd.DataFrame({"delta": deltas, "profit": profits}).to_csv(
    "results/Q1_sensitivity.csv", index=False)
```

### D.1 图表选择菜单 (必停点, v2.3.0)

每个子问 Qi 求解并验证通过后（Step C 通过、进入图表生成之前，与 E2 草稿卡写作相对顺序自定但必须在出图前），agent **必须**向用户呈现"图表选择菜单"，用户选定后才生成图表：

1. **本问图表数量**: `1) 0 张  2) 1 张  3) 2 张  4) 3+ 张  5) 让我决定`（0 张意味着该问以表格呈现结果，需用户显式选）。
2. **样式风格**（选项取自 `references/figure_skill_bridge.md` 顶部总路由表）: 自写 17 件数据图（统一色板）/ vendor icarus 多面板主图 / 物理场·网络流图 / 示意图 drawio / TikZ 框架图，菜单给编号 + 兜底"让我决定"。

**菜单确认前禁止任何正式图落盘**（"不问不出图"）。诊断图（调试残差/收敛等）如确需，仅存 `results/figures_diagnostic/` 且**不可进稿**。

**0/1 张的披露登记**: 图表数量不设评分下限（见 rubric 表维度 4 与 `config/rating_contract.json` 重释），但用户选 0/1 张属于低频决策，agent 必须先说明该问的证据呈现方式（表格/文字替代）；`figure_menu["Q<i>"]` 条目须追加 `"count": <0|1>, "exception": true` 与理由（条目形如 `{"status": "answered", "asked_at": "<ISO>", "answer": "1 张", "source": "chat", "count": 1, "exception": true, "reason": "<用户理由>"}`），并在 `真源.md` 图表登记表同步标注——登记用途是决策追溯，不是扣分豁免。

用户选择写入 `decision_log.checkpoints.figure_menu["Q<i>"]`，条目形如 `{"status": "answered", "asked_at": "<ISO>", "answer": "2 张, icarus 多面板主图", "source": "chat", "count": 2}`（count 为该问图表数量，int 0-9 必填；source 缺失或非 chat/user_cli 视为未答，check_gate 拦截——runtime 侧经 CLI answer 登记的条目 source 为 user_cli，同形）。**不问不出图**——这是六个必停点之一，`check_gate.py --gate 5` 与 `--checkpoint figure_menu.Q<n>` 会逐问校验。

**与 Stage 2 图表规格冻结的衔接**: stage 2 冻结的是规格框架（真源.md 图表登记表：每图回答什么问题 / 数据源 / 色板 / 类型）；本节菜单是逐问落实（数量 + 样式路由的最终确认）。两者不冲突——菜单结果若与登记表规格冲突，以菜单为准并回写登记表修订记录。

### D.2 图表契约与生成 (30 min)

每个 Qi 的图表数量按 D.1 菜单用户确认执行（典型组合如下，不设下限）：
- 1 张 Type 3 论文图: 支撑本问核心结论。
- 1 张 Type 2/Type 4 图: 用于方法对比或附录稳健性。

CUMCM 或研究生赛命中案例存在 `figure_story` 时，优先将图表组织为“结构/机制 → 中间状态 → 最终结果 → 可信边界”的证据组；不照搬历史图形数量和数值。

生成前写清图表契约:

```text
图表契约:
- Core claim: <这张图支撑的一句话结论>
- Figure type: <optimization-result / prediction-fit / evaluation-ranking / robustness-sensitivity / workflow-diagram>
- Source artifact: <results/Qi_*.csv 或 *.npy, 扁平命名与 canonical 一致>
- Paper section: <5.i.3 或附录>
- Palette: <academic_blue / cool_nature / muted_earth / okabe_ito, 选型规则见 references/color_typology.md>
- Output: SVG primary + PNG secondary
```

随后按 `math-figure-generator` 的规范生成 `paper/figures/*.svg` 和 `paper/figures/*.png`。Step D 的子灵敏度图（若 D.1 菜单为该问选定了灵敏度图）在此步从 `results/Qi_sensitivity.csv` 生成。若只是调试残差、异常值或收敛, 标为 Type 1 诊断图并留在 `results/figures_diagnostic/`, 不放正文。

### E. 物理意义讨论 (15 min)

把数值翻译成现实含义（篇幅由内容决定，不设段落/字数下限；含与同口径基线的对比）:

```
求解结果显示, 最优生产计划为 x* = (12, 0, 25, ...), 总利润 87234 元。
其中产品 1 (高单价低成本) 与产品 5 (低成本高需求) 占据主要产能, 
产品 2 因利润率仅 5% 而被全部跳过。这与零售行业 80/20 规律一致, 
即少数高利润 SKU 贡献主要收益。

相比贪心基线, 本模型利润提升 12.3%。
提升主要来自 Lagrangian 松弛对预算约束的精细处理, 
使总成本接近预算上限 (达到 99.4% 预算利用率), 而贪心仅 87.5%。
```

### F. L1 自评 + diff-only 精修

调用 `feedback_layer1_critic.md` 协议:
- 输出 5 维 JSON 评分
- 若任一维 <7 → diff-only 精修, iter+=1, 上限 3
- 全维 ≥9 → 早退
- 某子问 verdict=refine 且 iter=2 仍无改善、且怀疑方法本身不适用时, 触发 stage 5 文献挂点（1 次定向检索: 方法名 + 失效场景, 只找失效证据与替代路线）, 登记 `decision_log.stages.5.literature_searches`（协议见 `references/literature_scout.md`）

### G. 输出移交

写入 `decision_log.stages.5.sub_problems.Q1`:
```json
{
  "model_name": "...",
  "math_formulation_path": "results/Q1_model.tex",
  "code_path": "results/Q1_solve.py",
  "results_path": "results/Q1_x.npy",
  "figures": ["figures/Q1_flow.png", "figures/Q1_results.png", "figures/Q1_sensitivity.png"],
  "key_metrics": {"objective": 87234, "solve_time_s": 12.3, "improvement_vs_baseline": "12.3%"},
  "physical_meaning_summary": "...",
  "scores": {...},
  "iterations": 1
}
```

### H. 子检查点 (跨 Qi 后)

进入 Qi+1 之前,**自检**:

1. **复用链**: Q2 是否要用 Q1 的 x_star?
   - 题目要求? → 必须用
   - 题目未明确? → 核对固定输入、统计单位、信息可用性和机制需要，再说明取舍
   - 题目禁止? → 跳过

2. **符号一致**: Qi 中用的 x, p, c 是否与 stage 4 符号表一致?
   - 不一致 → 立即更新本 Qi 或更新符号表 (二选一并记录)

3. **假设一致**: Qi 模型是否引入了新假设?
   - 是 → 回 stage 4 加假设, 写入 decision_log
   - 否则 → 继续

4. **假设变更历史检查** (P2-3 新增) ⭐: 若 stage 4 的某假设在已完成 Qi 之后被 patch (L2 触发), 自检该 Qi 是否依赖被改假设。
   - **依赖** → 判断是否改变模型/输入/最优决策；需要时重跑 Step A/B，再重跑 C/D，更新相关义务与证据，不能只验证旧结果
   - **不依赖** → 在 `decision_log.stages.5.assumption_change_history` 标记 "Qi 不受 patch X 影响, 跳过重跑"
   - 检查方法: 读 `decision_log.events.log` 找 `type=L2_backtrack` 且 `target=stage.4.assumptions[k]` 的记录, 然后 grep Qi 的代码与 math_formulation 是否引用 assumption k

---

## L1 Rubric (Per-Qi)

| 维度 | 满分行为 |
|------|---------|
| 1. 模型与问题契合 | 目标/变量/约束 与题面 1:1 |
| 2. 数学严谨性 | 符号一致, 推导无跳跃 |
| 3. 求解正确性 | 代码运行 + sanity check 通过 |
| 4. 结果可视化 | 每张图绑定一个主张与上游数据，数量由论证需要决定（不设下限；0/1 图按 D.1 登记披露理由） |
| 5. 物理意义讨论 | 数值已翻译成现实含义，含与同口径基线的对比（篇幅由内容决定） |

## L1 Rubric (Stage-level)

| 维度 | 满分行为 |
|------|---------|
| 1. 子问题完整性 | 所有 Qi 都跑完 |
| 2. 依赖与接口 | 题面要求的依赖正确，固定输入未被误替换，单位/时段一致 |
| 3. 符号一致 | 全 Qi 用同一套 stage 4 符号 |
| 4. 视觉密度 | 图表覆盖"结构/机制、中间状态、结果、可信边界"中与本题相关的角色，不设数量下限 |
| 5. 时间预算 | 未超 stage 5 预算 30% |

## 常见坑

- D1-D5 求解类全部 → Step B/C 严格执行
- E1-E4 结果分析类 → Step E 物理意义必写
- G1 子问题各做各 → Step H 子检查点强制
- G2 子问题模型族突变 → 切换需在 H 显式记录触发条件

## H.2 per-Qi 差异化降级机制 (v3.0 新增)

老逻辑下若 Q1 mean=8.5 / Q2 mean=7.2 / Q3 mean=8.8, 整体 mean=8.2 min=7.2, **技术上 pass 但 Q2 弱被掩盖**。新协议引入 per-Qi 加权聚合 + 差异化降级:

### 聚合规则

```python
# 加载 decision_log.stages.5.qi_weights (默认 [1.0]*qi_count)
qi_results = [{qi: 'Q1', min: 8, mean: 8.5}, {qi: 'Q2', min: 7, mean: 7.2}, {qi: 'Q3', min: 8, mean: 8.8}]
qi_weights = decision_log.stages.5.qi_weights  # e.g. [1.0, 1.5, 1.0] 若 Q2 是题目核心

weighted_mean = Σ(qi.mean × weight) / Σ(weight)
weighted_min  = min(qi.min for qi in qi_results)

# Qi 状态判定 (单 Qi 独立):
for qi in qi_results:
    if qi.min >= 7 and qi.mean >= 8: qi.status = "pass"
    elif qi.min >= 7:                qi.status = "mark_for_review"   # 该 Qi 单独弱, 但仍可接受
    else:                            qi.status = "refine"             # 该 Qi 需重做
```

### Verdict 决策

| 场景 | verdict | 后续 |
|------|---------|------|
| 全 Qi pass + weighted_min ≥ 9 + weighted_mean ≥ 9 | `pass_early` | iter-1 早退 |
| 全 Qi pass + weighted_min ≥ 7 + weighted_mean ≥ 8 | `pass` | 进 stage 6 |
| 任 Qi mark_for_review + 加权阈值满足 | `pass_with_review` | 进 stage 6, **L2 必读 review_qis** (写入 stage 5 末尾的 L2 触发条件) |
| 任 Qi refine | `refine_partial` | **只 refine 该 Qi**, 不动其他 Qi (省 token + 时间) |
| 其他 (含 weighted_mean < 8) | `refine` | 全 stage refine (按老逻辑) |

### 示例

`Q2 mean=7.2 min=7` (mark_for_review) + Q1/Q3 都 pass + weighted_mean=8.2:
- verdict = `pass_with_review`, review_qis = ["Q2"]
- decision_log.stages.5.qi_status = {"Q1": "pass", "Q2": "mark_for_review", "Q3": "pass"}
- L2 在 stage 5 末尾必读 Q2 段, 检查"是否需要 stage 6 顺便重跑 Q2 灵敏度"

`Q2 min=5` (refine) + Q1/Q3 都 pass:
- verdict = `refine_partial`, refine_qis = ["Q2"]
- 只重跑 Q2 的 Step A-G; Q1/Q3 不动 (节省 ~60% 时间)
- iter+=1 仅对 Q2; 老 iter cap 3 仍生效, Q2 三次仍 refine 则 carryover

### 调用脚本 + verdict 问答确认 (v5 Friendly Mode)

```bash
# 在所有 Qi 跑完 per-Qi critic 后, agent 自动触发 (用户不必敲):
python scripts/score_artifact.py --mode aggregate_qi --qi-results state/qi_results.json
# qi_results.json schema: {qi_results: [{qi, min, mean, scores}], qi_weights: [...]}
# 输出: {verdict, weighted_min, weighted_mean, qi_status, review_qis, refine_qis}
```

**评分落盘与 gate 5 双路径口径 (v2.3.0)**: `aggregate_qi` 只打印聚合结果、不写回 `decision_log.scores["5"]`；agent 须把 `qi_status`/`review_qis`/`refine_qis` 手工写回 `decision_log.stages["5"]`。`check_gate.py --gate 5` 的评分检查按双路径放行：`scores["5"]`（stage-level，跑过 `--stage 5` 不带 variant 的 critique）非空且结构合法，**或** `scores["5_per_qi"]`（每问 `--variant per_qi --qi-id Q<i>` 落盘）非空、覆盖全部 Qi 且结构合法——满足其一即可。

脚本出 `verdict` 后, agent **问用户一次**确认 (Claude Code: AskUserQuestion; Codex CLI: 编号列表):

```
【Stage 5 聚合完成: verdict=refine_partial, Q2 需 refine, Q1/Q3 已 pass】

  1) 按推荐 refine Q2 (重跑 Q2 Step A-G, Q1/Q3 不动, 约 4-8h)
  2) 全 stage refine (含 Q1/Q3, 约 12-24h, 不推荐)
  3) 强制 carryover, 接受当前结果进 stage 6 (Q2 弱点留 stage 9 panel 处理)
  4) 让我决定 (推荐 1)

回复数字。
```

用户回复后 agent 自动执行, **不要**让用户编辑 decision_log 或重跑脚本。

**qi_verdict 的登记口径 (v2.3.0, 防伪造逐问确认)**: qi_verdict 是**逐问即问即登记**的——每个 Qi 的 per-Qi L1 评分产出该问 verdict 时（refine_partial 则在问清修哪问之后），就向用户确认该问结论并写入 `decision_log.checkpoints.qi_verdict["Q<i>"]`（必停点, 条目形如 `{"status": "answered", "asked_at": "<ISO>", "answer": "Q1 pass, 用户确认", "source": "chat"}`；source 缺失或非 chat/user_cli 视为未答，check_gate 拦截）。**聚合后的整体决策**（如本节编号菜单的选择）登记进 `decision_log.stages["5"]` 既有字段（`qi_status` 与 `events.log`），**不得复制登记进 qi_verdict 的任何条目**——一次问答复制到所有 Qi 等于伪造逐问确认。`check_gate.py --gate 5` 按 Qi 逐问校验 qi_verdict，见 SKILL.md 必停点协议。

### qi_weights 调整时机

默认 `[1.0] * qi_count` 由 stage 2 分解确认后按实际子问数重建（`decision_log.stages.5.qi_count` 取 stage 2 分解出的实际子问数，runtime 侧由 `confirm_qi_count` 原子迁移并记 `qi_count_confirmed` 事件）。用户可在 stage 5 第一个 Qi 完成时根据题目重要性调整 (e.g., `[1.0, 1.5, 1.0]` 若 Q2 是核心)。调整后写回 `decision_log.stages.5.qi_weights`, 后续聚合按新权重。

---

## 退出条件 (整个 stage 5)

1. 所有 Qi 通过 per-Qi rubric (全维 ≥7) **或** verdict ∈ {pass, pass_with_review} 经 H.2 聚合
2. Stage-level rubric 全维 ≥7
3. 题面依赖和固定输入均满足；尚未完成的义务保留状态与缺口，不宣称全部答完
4. (championship) red-team 一次,针对最弱的 Qi (优先 review_qis)
5. 触发 L2: 跨阶段回检 stage 3 (模型选择前提是否被结果推翻) + stage 4 (符号一致性) + **review_qis 列表 (若 verdict=pass_with_review)**

→ 跳转 `stage_06_robustness.md`

---

## 与 stage 6/8 的衔接

stage 6 全局灵敏度需要本节的求解器代码 (重用)。
stage 8 写论文 §5 直接基于本节产出, 每 Qi 一个小节。
