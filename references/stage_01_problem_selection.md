---
stage: 1
name: problem_selection
duration_h: 2-3
inputs: [stage.0.problem_scan, problem_pdfs[<topic_letters>], decision_log.competition]
outputs: [stage.1.{selected, rationale, rejected_alternatives, candidates_assessed, risks_identified}, root.task_type]
loads_reference: [rubrics.md§Stage_1, model_catalog.md§0, competitions/<competition>/topic_specs.json]
feedback: [L1]
next: stage_02_analysis
---

# Stage 1 — 选题 (多题对比 → 1)

**时长**: 2-3h | **反馈层**: L1 | **关键决策点**: 一旦选定,24h 内不允许更改

---

## 目标

在题号体系内 (huaweibei A-F / huashubei A-C / cumcm A-E / mcm A-F / diangong A-B / apmcm A-C), 选出**最契合团队优势 + 时间预算 + 数据可获取性**的一题, 且决策有据可查、不可悔棋。

**第一步必做**: 加载 `competitions/<competition>/topic_specs.json` 获取题号清单。若 `fixed_letter_to_type=false`，先按题面内容动态分类，再写 `decision_log.task_type`；禁止从题号字母推断题型。

华为杯赛题动态分类后进一步对齐 `competitions/huaweibei/distilled_modeling.md` 八类风险 + 信号诊断（playbooks 层域命名），命中后分两步定位 playbook：先读 `competitions/huaweibei/playbooks/README.md` 的域→文件映射表，再加载映射表中的英文文件名（signal_diagnosis.md / spatial_geometry.md / scheduling_optimization.md）：其"常见翻车点"供 Step 3 风险识别参考，动作清单不在选题阶段展开。

---

## 输入

- stage 0 元信息 + 题目预扫
- 三道题的官方 PDF (用户提供路径)

## 产出

- `decision_log.stages.1.selected`: 选定题号
- `decision_log.stages.1.rationale`: 选择理由 (≥5 行)
- `decision_log.stages.1.rejected_alternatives`: 另两题及不选理由 (各 ≥3 行)
- `decision_log.stages.1.candidates_assessed`: 三题对比矩阵 (5 维)

---

## 操作流程

### Step 0: 加载竞赛题号体系 (5 min, 必做)

```bash
# 路径: <skill>/competitions/<competition>/topic_specs.json
# 加载后得到题号清单；仅当 topic_specs 明确声明固定映射时才读取 task_type_key
```

题号体系总览 (引用 `topic_specs.json`):

| Competition | 题号 | 默认子问数 | 主要类型 |
|---|---|---|---|
| huaweibei | A-F，仅作题号 | 按当年题面 | 中文；按内容动态分类，30 个历史案例可检索 |
| huashubei | A-C，仅作当届题号；历史规律只作本赛经验 | 3-5 | 中文；18 个历史案例可检索 |
| cumcm | A-E，仅作题号 | 3-5 | 中文；按内容动态分类，25 个历史案例可检索 |
| mcm   | A 连续, B 离散, C 数据, D 网络, E 跨学科, F 政策 | 3-6 | 英文 + Letter (D/E/F) |
| diangong | A 电力工程, B 能源数据 | 6-8 | 中文工程 |
| apmcm | A 几何/优化, B 数据预测, C 算法优化/高级模型 | 3-5 | 中文论文 |

### Step 1: 三题信息提取 (45 min,并行)

对国赛、研究生赛和华数杯，先由 agent 运行 `scripts/build_stage_pack.py --competition <当前竞赛> --stage 1`；需要跨赛结构参考时改用 `--competition all`。检索结果必须保留竞赛键与证据等级，不能用历史题号替代当前题型判断。

为每道题提取:
- **核心任务** (1 句话)
- **子问题数与各自难点**
- **附件数据** (大小、格式、是否需清洗)
- **预估问题类型** (model_catalog.md 1-10 类)
- **历年类似题** (若知道)

输出三张表 (markdown):

```
## A 题: <标题>
- 核心: ...
- 子问题: Q1 ... / Q2 ... / Q3 ...
- 数据: 附件 1 (5MB CSV), ...
- 类型: 优化类 + 预测类
- 类似题: 2022 A
```

### Step 2: 实战 5 维对比矩阵 (30 min)

| 维度 | 权重 | A 题 | B 题 | C 题 |
|------|-----|------|------|------|
| 1. 团队匹配 | 0.25 | 8 | 6 | 7 |
| 2. 数据风险 | 0.25 | 7 | 5 | 8 |
| 3. 可出图性 | 0.15 | 8 | 7 | 9 |
| 4. 模型可落地 | 0.20 | 9 | 7 | 6 |
| 5. 写作可讲清 | 0.15 | 8 | 6 | 7 |
| **加权总分** | | **7.65** | **6.10** | **7.10** |

每维评分必须有**一句话依据** (写在表下方)。

五维解释:
- **团队匹配**: 是否贴合队伍建模、编程、写作的真实能力。
- **数据风险**: 附件是否可读、可清洗、规模是否能在比赛时间内处理；分数越高表示风险越低。
- **可出图性**: 是否天然能产出流程图、对比图、热力图、灵敏度图等可解释图表。
- **模型可落地**: 主要模型是否能在 6-12 小时内跑出可信结果。
- **写作可讲清**: 模型逻辑、结果意义、创新点是否容易讲给评委听。

如果用户只问"帮我比较 A/B/C 题", 直接输出这张矩阵和推荐结论; 不创建 state, 除非用户明确说"进入完整流程"。

### Step 3: 风险识别 (30 min)

为最高分题 (e.g., A) 列 ≥3 个潜在坑 + 应对策略:

```
风险 1: 附件 1 数据有缺失
  应对: 用 KNN 填补; 若 >20% 缺失则 stage 2 重判可行性

风险 2: 子问题 3 涉及偏微分方程, 团队不擅长
  应对: 用差分逼近 + 蒙特卡罗仿真替代解析解
  
风险 3: 求解时间可能 > 30 min
  应对: 先 toy demo, 实际数据规模降采样
```

### Step 4: 决策与锁定 (15 min) — 问答式

**呈现给用户** (Claude Code: AskUserQuestion; Codex CLI: 编号列表):

```
【基于 5 维对比矩阵, 推荐选题】

  1) A 题 — 加权 7.65 (最高), 优势: 模型可落地 9 分
  2) B 题 — 加权 6.10, 优势: 可出图性 7 分, 但数据风险偏高
  3) C 题 — 加权 7.10, 优势: 可出图性 9 分
  4) 暂不锁题 — 先补读题面或附件
  5) 让我决定 (推荐 1)

回复数字 (1-5)。
```

用户选定后, **agent 自动写入** `decision_log.stages.1` (不要让用户编辑 json):
```json
{
  "selected": "A",
  "rationale": "... 5 行依据 ...",
  "rejected_alternatives": [
    {"题号": "B", "reason": "..."},
    {"题号": "C", "reason": "..."}
  ],
  "candidates_assessed": [...],
  "risks_identified": [...]
}
```

**同步写 root 字段**:
- `decision_log.task_type` ← `topic_specs.json[selected].task_type_key` (e.g. `A_optimization` for cumcm-A)
- `decision_log.problem_meta.estimate_qi_count` ← 预估子问数（可选）: `topic_specs.json[selected].expected_subproblem_count` 的中位（区间且中位非整数十则不写；specs 无该字段不写）。仅为预估，供 stage 2 分解时参考。**stage 1 不再直接写 `stages.5.qi_count` / `qi_weights`**——stage 5 实际使用的 `qi_count` 在 stage 2 分解确认后按实际子问数写入（见 `stage_02_analysis.md`），gate 5 以该实际值为准。

**锁定承诺**: 24h 内不允许更改。如必须更改 (附件数据完全不可用等),需 L2 强触发 + 用户二次确认。

### Step 5: 移交 (5 min)

输出给 stage 2 的"问题输入包":
- 选定题号
- 子问题清单
- 附件数据路径
- 预估问题类型
- 风险清单

---

## L1 Rubric (`rubrics.md` Stage 1)

| 维度 | 满分行为 |
|------|---------|
| 1. 三题对比深度 | 每题 5+ 评估点 |
| 2. 团队优势匹配 | 选题理由含"我们擅长 X,本题需要 X" |
| 3. 风险识别 | ≥3 潜在坑 + 应对 |
| 4. 时间可行性 | 已估各阶段所需 h,合计 ≤72h |
| 5. 决策记录质量 | rationale + rejected_alternatives ≥3 行依据 |

退出: 全维 ≥7。

---

## 常见坑

- **J2** 选题摇摆: 锁定后强制 24h
- 三题都说不清: 信号是 Step 1 没读透题,回 stage 0 重读题目 PDF
- 选了团队最擅长但题目本身天花板低的题: rubric 5 (创新空间) ≥6 才算过

---

## 退出条件

1. 选定题号 + 锁定承诺
2. decision_log.stages.1 完整 (5 个 key 都有内容)
3. L1 rubric 全维 ≥7
4. 风险清单已有应对

→ 跳转 `stage_02_analysis.md`
