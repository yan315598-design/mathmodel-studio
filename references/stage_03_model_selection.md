---
stage: 3
name: model_selection
duration_h: 按风险、算力与剩余赛时分配
inputs: [stage.2.{decomposition, objective_per_subproblem, data_schema}]
outputs: [stage.3.{research_status, candidate_models, selected_per_subproblem, rejection_log, evidence_status, fairness_comparison, open_risks, toy_demos_passed, red_team, model_family_consistency}]
loads_reference: [model_catalog.md, rubrics.md§Stage_3]
next: stage_04_foundation
---

# Stage 3 — 模型选型与机制设计

## 目标与边界

从题目、数据和误差出发，生成能解释失效原因的候选，经实验比较后提出推荐。路线可以包含数据处理、表示、模型、求解算法、适配和解释；不以算法名、模块数量或复杂程度评价创新。

保持四种研究状态：`explore`（发现）、`validate`（验证）、`recommend`（范围明确的推荐）、`frozen`（用户确认并移交）。新证据可以使推荐退回探索或验证；不增加子阶段、审批或候选配额。用户要求执行且已有授权时直接开展实验，仅问建议时不自动训练。

当前任务只加载模型目录命中域及相关协议，不通读全部目录。实际实验与预算遵循 `references/experiment_cycle.md`；定义、实现和主张边界遵循 `references/modeling_evidence_protocol.md`。

## A. 发现候选：先提出能被否定的假设

对当前最值得投入的方向，在既有 `selection_sheet.md` 简记：

> 观察 → 失效假设 → 能区别替代解释的实验 → 结果 → 下一步。

假设可来自题面机理、数据审计、分组误差、文献或类比推导，不要求每条先有文献。说明什么结果支持它、什么结果会使它失去优先级。无需给所有想到的候选填卡。

候选应能修复具体缺口。例如表示压缩可能丢信息、目标与代理不一致、搜索未收敛、采集条件提供类别捷径。分开判断表示、读出模型和训练过程：一次弱实现不能否定表示或整个方法族；已有表示可先换合理读出器检验，也允许复杂组合先整体试验，再对最可能影响归因的模块补控制。

根据本题的目标、数据、约束和主要不确定性决定需要比较的路线。比较对象可以是模型、表示、数据处理、求解算法、训练过程或它们的组合；也可以在没有可区分的替代解释时只验证一条路线。候选数量和结构由问题与证据决定，不为凑类别或数量增加方案。数学模型和求解算法分列；新增模块说明输入输出、前提和接收方；创新体现为本题有依据且可验证的设计，不要求目录外方法或修饰名称。

### 按需使用历史案例

竞赛为 `cumcm`、`huaweibei` 或 `huashubei`，且历史类比有助于当前缺口时，可运行 `scripts/build_stage_pack.py --competition <competition> --stage 3`。定向读取命中项的 `question_dependency`、`recommended_chain`、`paper_route_comparison`、`assumption_risks`，不按出现次数投票。记录采用或拒绝的理由及本题条件差异；历史数值、参数和预测不能作为本题答案。

华为杯/国赛先读对应 `competitions/<competition>/playbooks/README.md` 的域映射，再加载命中域；需要方法原文线索才查该赛论文索引。华数杯S1–S4为蒸馏任务链，不是原题逐问；题面摘要不冒充论文共识。案例资源不可用时保留缺口，不阻断题面推导和本地实验。

## B. 验证与比较：给路线合理的验证机会

最小实验围绕当前最大不确定性，检查接口、训练诊断、可行性或泛化。合成原型只证明所覆盖的机制；正式函数不同，需要在实际函数上复查关键反例。发现失败后先区分方法前提、实现错误、资源不足与数据问题，再决定补预算、改路线或淘汰。

实验记录 `protocol_status=compliant|deviated|unknown` 及依据。偏差未解决或执行情况未知时，结果留作诊断，不进入正常排名；负收益本身不是协议失败。公平性由数据权限、外层评价和训练侧选型机会决定，不要求所有模型使用相同epoch。预算、训练诊断、数据隔离与比较工具契约统一见 `references/experiment_cycle.md`，此处不另设一套规则。

保留四轴证据，适用于当前入围候选，不为探索池批量补空表：

| 轴 | 含义 |
|---|---|
| `bibliography_verified` | 外源出处核验；本地推导没有文献时可为not_applicable，并说明来源 |
| `mechanism_reviewed` | 理解定义、前提、接口、反例与适用边界 |
| `implementation_validated` | 关键真实行为已核验，注明覆盖范围；运行成功不等于此项通过 |
| `effect_evaluated` | 本题已测范围内的效果，可为positive、neutral、negative或inconclusive |

前三轴取 `unknown|pass|fail|not_applicable`，效果轴取 `unknown|positive|neutral|negative|inconclusive`。旧 `proposed/source_checked/locally_tested` 仅为来源线索，不能自动映射为全部pass。实现核验通过不代表效果正向。

### 文献发现与转译

有未解决的机制、反例或实现缺口时，按 `references/literature_scout.md` 检索，先查已有记录和缓存。对影响决策的来源简记：它支持哪个前提、能转成哪个候选或实验、哪些条件与本题不同。只找到题名或摘要，不升级为机制已核验。没有新信息就停止泛搜；不设文献数量或组合数量配额。

## C. 推荐与移交：完成度带范围

在现有选择表主动说明推荐、实测证据、替代方案、代价和未解决风险。区分“值得继续”“开发范围内优于基线”“可正式求解”“目标环境有效”。一问比较完成不升级其他问；用户选择研究方向也不升级科学证据。

`fairness_comparison` 沿用现有字段，可在 `notes` 说明范围；复杂任务可选加 `by_subproblem`，不要求旧工作区补该字段。整体仍有影响当前选型的比较缺口时记 `in_progress`，可以给条件性推荐并继续已授权实验。跨域无标签不能直接计算真实准确率，但可完成范围明确的代理比较；这些限制必须随推荐保留。

正式选择卡展示当前值得保留的路线及其依据、关键取舍、失效条件和验证范围。路线可以是单一方法，也可以包含多个模块；保留或省略某条路线都应由本题证据、资源和剩余时间解释。没有外源依据则明确为题面推导或本地实测。

题面硬约束与用户偏好分开。例如目标无标签限制监督训练和准确率评价，但仍允许直接迁移、机理诊断、域泛化或无监督适配。不要将尚未验证的效果交给用户拍板代替实验。

正式定型使用真实 `card_decision` 回答，已有明确选择不重复询问；不得编造用户理由。将选择写入 `selected_per_subproblem`，同步选择表的正式选择栏，未选的探索候选仍可留在表中。淘汰项记原因和重新考虑的触发条件。按跨问实际依赖检查单位、样本单位、信息权限与接口，不强求统一模型族或库。

### 状态与兼容性

保持现有decision_log schema和六类checkpoint，不新增阶段机。Stage 3记录：

```json
{
  "research_status": "explore|validate|recommend|frozen",
  "candidate_models": [],
  "selected_per_subproblem": {},
  "evidence_status": {},
  "fairness_comparison": {
    "status": "not_started|in_progress|complete|not_applicable",
    "protocol_id": "", "split_id": "", "metric": "",
    "budget_s": null, "aggregation_unit": "", "notes": ""
  },
  "open_risks": [], "rejection_log": [],
  "toy_demos_passed": false, "red_team": [],
  "model_family_consistency": ""
}
```

恢复旧工作区时不重置模型、历史结果或已答checkpoint；只在重新做Stage 3移交时依据现存证据补缺字段，未知保留unknown，不能批量升级为pass。旧schema无须整库迁移。选择表既容纳探索记录，也呈现正式选择，不再要求整张表只是selected字段的渲染。

`recommend`允许范围明确的条件性推荐；正式移交要求比较complete或有理由的not_applicable、证据与选择记录齐备、阶段评分通过及真实用户确认。`check_gate.py --gate 3`核对移交记录（兼容recommend并已确认的旧调用顺序）；Agent在实际移交时记frozen，不凭布尔状态宣称效果已证。关键比较缺口未解决则继续验证，不索取形式批准。

L1评分唯一口径见 `references/rubrics.md` 的Stage 3；最高风险质询按需进行，不设攻击条数。门禁用于正式移交，不为内部探索新增停点。

→ `stage_04_foundation.md`
