---
stage: 6
name: robustness
duration_h: 2-3
inputs: [stage.5.sub_problems.{Qi}.{code_path, key_metrics}, stage.4.{assumptions, symbols}, stage.3.selected_per_subproblem]
outputs: [stage.6.{params_varied_jointly, method, deltas, robust_intervals, stability_verdict, failure_warning, L2_backtrack, figures}]
loads_reference: [winning_patterns.md(灵敏度节), rubrics.md§Stage_6, anti_patterns.md§F]
loads_template: [code_starter/simulation.py, sensitivity_table.md]
feedback: [L1, L2_cross_stage]
next: stage_07_evaluation
---

# Stage 6 — 全局灵敏度 / 稳健性分析

**时长**: 2-3h | **反馈层**: L1 + L2 (跨阶段回检触发点)

---

## 目标

回答两个问题：结论在哪些参数/假设条件下成立，在哪里失效。方法按风险选择——参数间相互作用重要时联合扰动，需要归因时做方差分解，计算昂贵时少量有依据的情景分析同样合格。不以求样方法本身区分档次。

---

## 输入

- stage 5 各 Qi 的求解器代码 (复用)
- stage 4 符号表 + 假设
- stage 3 模型选择 (本节会触发对其的 L2 回检)

## 产出

- 灵敏度分析报告 (扰动参数选择有依据 + 结论稳定性/失效边界 + 稳健范围表)
- 稳健性结论 (write to `decision_log.stages.6.stability_verdict`)
- 失效边界（如实报告：观察到的失效条件，或测试范围内未观察到失效）
- L2 回检报告: 模型选择前提是否被推翻

稳健性图表遵守 `references/figure_skill_bridge.md`: 龙卷风图、扰动曲线、热力图必须说明支撑的稳健性结论, 并输出可编辑 SVG + PNG 备用图。

---

## 操作流程

### Step 1: 选定扰动参数 (15 min)

从 stage 4 符号表的"参数"行中, 优先选**会改变结论**的参数。数量按结论风险决定，可以是 1 个也可以是多个。

判断标准:
- 出现在目标函数中的系数 (高优先级)
- 出现在多个约束中的参数 (高)
- 来自附件数据且数据本身有不确定性 (高)
- 决策者可调控 (中)

写入 `decision_log.stages.6.params_varied_jointly`，每个参数附选择理由。

### Step 2: 选定扰动方法 (10 min)

| 方法 | 适用 | Python |
|------|-----|--------|
| **OAT** (一变一) | 参数少、需逐参数解释、或计算昂贵时的合理选择 | 自实现 for 循环 |
| **LHS** (拉丁超立方) | 参数间相互作用重要、需联合扰动 | `scipy.stats.qmc.LatinHypercube` |
| **Sobol** (索博尔) | 需要定量归因各参数贡献 | `SALib` 库 |
| **Morris** (莫里斯) | 大量参数 (>10) 筛选 | `SALib` |
| **情景分析** | 扰动不是统计分布而是具体假设（如题面情景） | 逐情景重求解 |

方法选择写依据；允许"少量可解释情景优于无依据的复杂采样"（winning_patterns.md 灵敏度节）。

### Step 3: 扰动幅度 (10 min)

幅度对应实际不确定性来源（测量误差、数据修订、情景假设），并写明依据，不设固定档位。例：

```
测量误差主导: ±5%
正常波动:     ±10%
极端情景:     ±20%
```

### Step 4: 运行扰动求解 (1-2h)

```python
from scipy.stats.qmc import LatinHypercube
import numpy as np

# 选 3 个参数: p (单价), c (成本), B (预算)
n_samples = 200
sampler = LatinHypercube(d=3, seed=42)
unit_samples = sampler.random(n=n_samples)

# 三档扰动
for level, delta in [("low", 0.05), ("med", 0.10), ("high", 0.20)]:
    objectives = []
    decision_changes = []
    for s in unit_samples:
        # s ∈ [0,1]^3 → 缩放到 [1-delta, 1+delta]^3
        factors = 1 + (2*s - 1) * delta
        p_pert = p * factors[0]
        c_pert = c * factors[1]
        B_pert = B * factors[2]
        # 重新求解 (复用 stage 5 代码)
        result = solve_Q1(p_pert, c_pert, B_pert)
        objectives.append(result.value)
        decision_changes.append(np.linalg.norm(result.x - x_star_baseline))
    
    # 报告
    obj_arr = np.array(objectives)
    print(f"档位 {level} (±{delta*100:.0f}%):")
    print(f"  目标函数 5%-95% 区间: [{np.percentile(obj_arr, 5):.2f}, {np.percentile(obj_arr, 95):.2f}]")
    print(f"  相对基线偏差: {(obj_arr.std() / obj_arr.mean()) * 100:.2f}%")
```

样本数按结论稳定性决定（如分位区间随样本数变化已平稳）；单次求解昂贵时减样本并注明。

### Step 5: 可视化 (30 min)

图表数量由论证需要决定（不设下限），每张图必须支撑一个稳健性结论。

生成前先写图表契约:

```text
图表契约:
- Core claim: <模型在 ±10% 扰动内保持稳定 / 参数 B 是主要风险源>
- Figure type: robustness-sensitivity
- Source artifact: results/stage6_lhs_samples.csv
- Paper section: 6.2 或附录
- Output: paper/figures/stage6_robustness.svg + .png
```

**图 1: 联合扰动散点矩阵 (pairs plot)**

```python
import seaborn as sns
import pandas as pd
df_sens = pd.DataFrame({
    "p_factor": p_factors, "c_factor": c_factors, "B_factor": B_factors,
    "objective": objectives
})
sns.pairplot(df_sens, hue="objective", diag_kind="kde")
plt.savefig("figures/sensitivity_pairs.png", dpi=300)
```

**图 2: 龙卷风图 / Tornado** (单参数贡献度排序)

```python
contributions = {p: corr(p_factor, objective), c: corr(...), B: corr(...)}
sorted_contrib = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)
# 横向 bar
```

(championship) **图 3: Sobol 一阶 + 总效应指数**

### Step 6: 稳健区间报告表 (15 min)

```
表 N. 多变量联合灵敏度分析结果

| 扰动幅度 | 目标函数 [5%, 95%] | 决策变量 L2 范数偏差 | 稳健性 |
|---------|------------------|-------------------|-------|
| ±5%    | [85800, 88600]   | < 2 件            | 极稳健 |
| ±10%   | [83200, 91100]   | < 5 件            | 较稳健 |
| ±20%   | [76400, 96800]   | < 12 件           | 临界稳健 |
```

### Step 7: 失效边界 (15 min) ⭐

如实报告两种结果之一：
- 测试范围内观察到失效或结论翻转 → 写出临界条件、表现与影响（写入评价节）。
- 未观察到失效 → 报告实际测试范围，说明"在该范围内未观察到失效"，不编造临界参数。

例 (观察到失效时的写法):
```
失稳警告: 当预算 B 减少 30% 以上时, 最优解切换为完全不同的产品组合 (Hamming 距 > 50%), 
表明 B = 70k 是模型相变点。在评价节 §7 讨论该警告, 
并提议改用鲁棒优化 (anti_pattern H1, 自我批判要具体)。
```

写入 `decision_log.stages.6.failure_warning`。

### Step 8: L2 跨阶段回检 (15 min) ⭐

读 `decision_log`, 验证:

1. **stage 3 模型选择是否仍合理?**
   - 例: stage 3 选 LP 假设线性, 但本节 ±20% 下结果非线性 → 应在 stage 7 评价节显式讨论, 或考虑回 stage 3 升级为 NLP/鲁棒
   - 不退回 (除非完全推翻), 但**记录到 stage 7 评价**

2. **stage 4 假设是否被本节挑战?**
   - 例: 假设 "需求服从泊松", 本节扰动表明非泊松也成立 → 假设非必要, 可放宽

3. **stage 5 子问题间复用是否在扰动下崩溃?**
   - 例: Q3 用 Q1 的 x* 作为 warm start, 但 Q1 在 ±10% 下解集已切换 → Q3 也需重做, 或显式说明 Q3 在哪些参数范围内仍成立

L2 输出:
```json
{
  "backtrack_targets": ["stage_3", "stage_5_Q3"],
  "verdict": "no_revert | revise_stage_7 | full_revert",
  "notes": "..."
}
```

`verdict` 通常是 `revise_stage_7` (在评价节讨论限制), `full_revert` 极少触发。

### Step 9: 输出移交 (10 min)

写入 `decision_log.stages.6`:
```json
{
  "params_varied_jointly": ["p", "c", "B"],
  "method": "LHS, n=200/档",
  "deltas": [0.05, 0.10, 0.20],
  "robust_intervals": {...},
  "stability_verdict": "在 ±10% 扰动内极稳健, ±20% 临界稳健",
  "failure_warning": "B 降 30%+ 触发解集切换",
  "L2_backtrack": {...},
  "figures": ["..."]
}
```

---

## L1 Rubric

| 维度 | 满分行为 |
|------|---------|
| 1. 扰动围绕结论 | 优先扰动会改变结论的参数，方法选择有依据 |
| 2. 扰动幅度有据 | 幅度对应实际不确定性来源并写明依据，不设固定档位 |
| 3. 输出对应决策 | 报告结论是否翻转、决策变化与决策损失 |
| 4. 稳健范围定量 | 明确口径下结论成立的参数范围 |
| 5. 失效边界 | 如实报告失效条件或测试范围，不编造临界参数 |

## 常见坑

- F1 不做灵敏度 → 阻塞,必须做
- F2 方法与问题脱节 → 按结论风险选方法；相互作用重要时不能只逐参数扰动
- F3 扰动幅度不切实际 → 幅度必须有来源依据
- F4 不报稳健范围 → Step 6 表格

## 退出条件

1. 扰动参数、方法、幅度均有依据并落盘
2. 稳健范围表与支撑图完成
3. 失效边界如实报告（观察到的失效或测试范围）
4. L2 回检完成 (verdict 写入)
5. L1 全维 ≥7

→ 跳转 `stage_07_evaluation.md`
