---
stage: 3
name: model_selection
duration_h: 2-3
inputs: [stage.2.{decomposition, objective_per_subproblem, data_schema}]
outputs: [stage.3.{candidate_models, selected_per_subproblem, rejection_log, toy_demos_passed, red_team, model_family_consistency}]
loads_reference: [model_catalog.md, rubrics.md§Stage_3, winning_patterns.md]
loads_template: [code_starter/<problem_type>.py]
feedback: [L1, counterfactual_exploration_in_championship]
next: stage_04_foundation
---

# Stage 3 — 模型选型与机制设计

**时长**: 2-3h | **反馈层**: L1 + 针对核心失败边界的反事实探索

---

## 目标

按 `references/modeling_evidence_protocol.md` 选主模型并认真比较可行替代。先做概念到指标的转换，再选求解器。不强制族数、统一库或修饰词；模型变化须说明依据并核对接口。

---

## 输入

- stage 2 输出: 子问题卡片 + 目标函数雏形 + 数据 schema
- `references/model_catalog.md` 必读

### 国赛 / 研究生赛 / 华数杯案例入口

当 `competition` 为 `cumcm`、`huaweibei` 或 `huashubei` 时，先由 agent 运行 `scripts/build_stage_pack.py --competition <competition> --stage 3`；需要跨赛结构参考时使用 `--competition all`。对命中案例和子问读取 `question_dependency`、`recommended_chain`、`paper_route_comparison` 和 `assumption_risks`：

- 候选模型来自跨论文路线差异，不按历史出现次数投票。
- 选型理由必须说明新题与历史案例在目标、约束、数据和假设上的相同与不同。
- `result_disagreements` 只用于发现口径风险，历史数值和参数不得进入当前题结果。
- 在 `rejection_log` 记录案例 ID、evidence ID、拒绝路线及原因。
- 华数杯 `S1-S4` 是蒸馏任务链，不是原题逐问；2020—2022 的 `problem_summary_only` 只能启发路线，不能称为论文共识。

华为杯赛题先按八类风险 + 信号诊断分类（`competitions/huaweibei/distilled_modeling.md`），命中后分两步定位 playbook：先读 `competitions/huaweibei/playbooks/README.md` 的域→文件映射表，再加载映射表中的英文文件名（signal_diagnosis.md / spatial_geometry.md / scheduling_optimization.md）：动作清单补充候选生成（不替代缺口驱动选型，不按条目数投票）；需要深读材料时经 `competitions/huaweibei/papers/domain_index.md` 命中 paper_id 后定向读 `manual_paper_reviews.json`，2021 届模板字段（derivation_logic/solver_logic 等）不作为逐篇结论引用。

## 产出

- 每个 Qi 的主模型、真实名称、选型理由和必要模块接口
- 可行替代及取舍证据；无可行替代则说明限制
- 可调用的小规模原型；正式实现不同则重新验证
- (championship) red-team 攻击与回应

---

## 操作流程

### Step 1: 问题类型映射 (10 min)

对每个 Qi,查 `model_catalog.md` §0 速查表:

```
Q1: "求最优生产计划" → 优化类 (LP/IP)
Q2: "考虑库存约束" → 优化类 (MIP) + 启发式
Q3: "随机需求下的稳健决策" → 鲁棒优化 / 随机规划 / 蒙特卡罗
```

### Step 2: 基线与替代路线 (45 min)

至少考虑一个实质不同的可行替代，不强制三个族。下例主要是同一整数规划问题的不同求解技术，不冒充三种数学机制：

```
Q1 候选:
  候选 A: 整数线性规划 (优化族)
    - Python: cvxpy + GUROBI/CBC
    - 时间复杂度: 一般整数线性规划为 NP-hard，特殊结构另证
    - 优势: 可表达离散约束，求解器可报告界与间隙
    - 风险: 数据规模大时求解慢
  
  候选 B: 遗传算法 (启发式族)
    - Python: deap
    - 时间: O(代数 × 种群)
    - 优势: 大规模可扩展
    - 风险: 不保证最优, 需调参
  
  候选 C: 拉格朗日松弛 + 列生成 (优化族变体)
    - 自实现
    - 优势: 特定结构可利用分解并构造界，界的质量需验证
    - 风险: 实现复杂, 时间不够
```

检查候选是否在假设、表示、可行域或求解预算上有实质差异；不因同族否决。新增模块说明缺口、接口和去掉模块的对照。

### Step 3: 选型决策矩阵 (30 min)

为每个 Qi 做加权评分:

| 维度 | 权重 | 候选A | 候选B | 候选C |
|------|-----|------|------|------|
| 1. 适配度 (与问题契合) | 0.30 | 9 | 7 | 9 |
| 2. 求解可行性 (库支持/复杂度) | 0.25 | 8 | 9 | 5 |
| 3. 时间预算 (实施所需 h) | 0.20 | 8 | 7 | 4 |
| 4. 创新空间 (变体可能性) | 0.15 | 6 | 8 | 9 |
| 5. 文献支持 (参考资料) | 0.10 | 9 | 9 | 6 |
| **加权** | | **8.05** | **7.85** | **6.45** |

→ 选 候选 A (整数线性规划)。

### Step 4: 名称与真实实现 (15 min)

可以直接用“整数线性规划”。仅在公式和代码实际具备相应结构时使用限定词，不借名称表示未经验证的优越性：

可选形式：`<真实限定条件> + <核心模型>`。

候选名:
- "基于 Lagrangian 松弛的混合整数线性规划模型"
- "考虑动态约束的 MILP 优化模型"
- "二阶锥松弛改进 MILP"

最终选 1 个写入 `decision_log.stages.3.selected_per_subproblem.Q1`。

### Step 5: Toy Demo 验证 (45 min)

原型范围按风险决定，不按固定行数或数据比例。下例只是求解器可用性原型，正式函数须另过关键反例：

```python
# Q1 toy demo - 验证 cvxpy 能跑通
import cvxpy as cp
import numpy as np

# 模拟参数
n = 5  # 真实是 100,这里用 5
p = np.random.rand(n) * 100
B = 200

x = cp.Variable(n, integer=True)
objective = cp.Maximize(p @ x)
constraints = [cp.sum(x) <= B, x >= 0, x <= 50]
prob = cp.Problem(objective, constraints)
prob.solve(solver=cp.GLPK_MI)

print("Q1 toy demo 通过, 求解时间:", prob.solver_stats.solve_time)
print("最优解:", x.value)
```

要求:
- 状态与可行性正确；不可行实例也须正确处理
- 时间在事先记录的预算内
- 核心定义/接口反例使用真实调用函数；未实现部分明确待验证

不通过 → 候选无效,回 Step 2 换。

### Step 6: 跨子问题模型族协调 (10 min)

按题面实际依赖检查单位、时间步长、样本单位和信息可用性，防止固定输入被误替换。不同库和模型族可以并存，不将统一工具作为质量证据。

写入 `decision_log.stages.3` 的 "model_family_consistency" 字段。

### Step 7 (championship 模式): Red-team 攻击 (30 min)

> 假装最严苛评委,列出本模型选择被 reject 的最强理由（数量按实际风险，不设下限）,并给出**可信回应**。

例:
```
攻击 1: "你说用 MILP 但数据规模 1000+, 求解时间不可控"
回应: "已做 toy demo, 1000 规模在 GUROBI 下 < 5min;
      备用方案: GA 启发式 (候选 B) 已实现, 可作为 fallback"

攻击 2: "Q3 用蒙特卡罗, 但样本数 N 没说"
回应: "stage 5 会做 N=1000/5000/10000 收敛性测试, 
      取首个稳定 N (估计 2000) "

攻击 3: "命名 '改进 MILP', 改进点是什么?"
回应: "(a) Lagrangian 松弛降低规模, 
       (b) warm start 复用 Q1 解, 
       (c) 添加 Benders 切平面"
```

写入 `decision_log.stages.3.red_team`。

### Step 8: 输出移交 (10 min)

写入 `decision_log.stages.3`:
```json
{
  "candidate_models": [...],
  "selected_per_subproblem": {
    "Q1": {"name": "...", "library": "cvxpy", "rationale": "..."},
    "Q2": {...},
    "Q3": {...}
  },
  "rejection_log": [...],
  "toy_demos_passed": true,
  "red_team": [...],
  "model_family_consistency": "..."
}
```

---

## 选择卡（人类拍板门, 0.7.5 新增）

短名单定稿到 `decision_log.stages.3` 之前过一道**人类拍板门**: 模型选择是全论文最大的单点决策, 该由用户拍板, 不由 agent 默契通过。

**短名单规格**: 每个Qi进入选择卡的短名单 = **1 主 + 1 baseline + 至多 1 条件性备用**。备用必须有**显式触发条件**（"主模型在 X 条件下失效时启用", 触发条件直接用 model_catalog.md §12 的失效边界）, 写不出触发条件的备用不留。

**选择卡出卡顺序（候选版修订）**:

1. **先亮短名单，每个候选带取舍档案**——不在看到候选前凭空问偏好（早期伪精确偏好会提前剪掉正确候选）。档案四列:
   - 防守的输出形式（该候选产出的是排序 / 数值 / 方案 / 政策建议）
   - 不可接受的失败模式（该候选最可能怎么死：无解 / 精度崩 / 超时 / 结果反直觉）
   - 失效边界与触发条件（直接用 model_catalog.md §12）
   - 实验预算（该候选预计的求解/调参时长）
2. 展示短名单与档案对照表，标注哪些是**题面硬约束决定**的（如目标域无标签→只能无监督域适应），哪些才是**真正的偏好权衡**——硬约束项不给用户"选错"的空间，偏好项才交给用户。
3. 用户拍板（可以推翻 agent 推荐，理由可留空）。

**decision_log 登记**:

- 用户的选择连同理由写入 `decision_log.stages.3.choice_card`: `{"answers": <用户对候选档案的拍板记录>, "chosen": <主模型>, "rationale_user": <用户理由>}`。
- **必停点登记 (v2.3.0)**: 拍板结果同步写入 `decision_log.checkpoints.card_decision`（`{"status": "answered", "asked_at": "<ISO>", "answer": "<用户拍板摘要>", "source": "chat"}`；source 缺失或非 chat/user_cli 视为未答，check_gate 拦截）；推进 stage 4 前必须 `python scripts/check_gate.py --gate 3` 放行（见 SKILL.md 必停点协议）。
- AI 可代录**答案原文**, 但**不得代写理由**——理由栏空着就空着, 等用户补; 填 AI 生成的"用户理由"属于伪造决策记录。
- 被淘汰的方法进 `rejection_log` 归档备注: 记淘汰原因与"何种题目形态下应重新考虑", 防止 Stage 5 遇阻时把已淘汰方法不声不响地捡回来。

与 Step 3 决策矩阵的关系: 矩阵算分是 agent 的参谋结论, 选择卡是用户的拍板记录; 两者不一致时以选择卡为准, 矩阵留档供回溯。

---

## L1 Rubric

| 维度 | 满分行为 |
|------|---------|
| 1. 候选比较 | 有实质差异的可行替代及证据，不按族数评分 |
| 2. 选型理由 | 每候选有适配 + 不选原因 |
| 3. 名称与机制 | 名称对应公式、模块和实现，不要求修饰词 |
| 4. 求解可行性 | 原型范围明确，关键正式函数反例已验证或明确待验证 |
| 5. 文献支撑 | 关键选型主张有可核验来源（文献/数据/机理），不设篇数下限 |

championship 额外: red_team 攻击须覆盖最高风险边界且每个有可信回应，不设条数下限。

## 常见坑

- C1 直接抄 textbook → 核对本题概念、数据、接口，而不是更换名称
- C2 模型不匹配 → Step 1 速查表对照
- C3 名异实同 → 检查实质差异，不强制换族
- C4 选型理由薄弱 → Step 3 5 维矩阵
- C5 不验证可行性 → Step 5 toy demo

## 退出条件

1. 每 Qi 选型完成，名称对应机制
2. 替代方案及取舍证据明确；无可行替代时披露限制
3. toy demo 通过
4. (championship) red-team 覆盖最高风险边界 + 回应
5. L1 全维 ≥7

→ 跳转 `stage_04_foundation.md`
