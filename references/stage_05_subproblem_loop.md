---
stage: 5
name: subproblem_loop
duration_h: 6-12 per Qi
inputs: [stage.2.decomposition, stage.3.selected_per_subproblem, stage.4.{assumptions, symbols}]
outputs: [stage.5.sub_problems.{Qi}.{model_name, math_formulation_path, code_path, results_path, figures, key_metrics, physical_meaning_summary, scores, iterations}, stage.5.cross_reference_chain, stage.5.assumption_change_history, state/evidence_ledger.json]
loads_reference: [model_catalog.md, rubrics.md§Stage_5, modeling_evidence_protocol.md]
loads_template: [code_starter/<problem_type>.py]
feedback: [L1_per_Qi, sub_checkpoint, L2_at_end_for_stage_3_4_consistency]
next: stage_06_robustness
---

# Stage 5 — 递归子问题循环 (Q1..Qn)：编排

**定位**：本文件只管**编排**（触发 / 输入产出 / 步骤顺序 / 必停点 / 失败处理 / 指针）。专业细节一律在权威源，本文件不复制；每步只给一句"做什么"和"去哪看"。
**时长**：6-12h × n 个子问题 | **反馈层**：L1 + 子检查点 | 约占全流程时间 50%。

## 触发与加载纪律

- 进入条件：题面已分解（stage 2）、选型已拍板（stage 3）、假设/符号已冻结（stage 4）；用户在 Codex 说"帮我求解/直接解这道题"时，**无 stage 3 选型记录必须先补走选择卡**，不得直接求解。
- 进 stage 5 前核对 `decision_log.stages.5.qi_count` 与题面实际子问数一致；不一致先回 stage 2 修正分解与 `qi_count`/`qi_weights`（否则 gate 5 的三来源对齐必然拦截）。
- 加载纪律：**按"本问链路"读**——只取当前步骤需要的小节与权威源章节，不整读本文件、不整读上游文档；跨问只重读被问到的那节。
- 并行：题面无依赖的 Qi（见 stage 2 `subproblem_dependency`）可按 `references/parallel_dispatch.md` 派子 agent 并行；**并行前冻结 stage 4 符号表与假设表（写锁）**，合并时做符号/单位/编号冲突检查；有依赖的 Qi 保持串行。

## 输入 / 产出

- 输入：stage 2 子问题卡片（含答题义务）、stage 3 选定模型、stage 4 假设/符号/术语；上游结果**只在题面或机制需要时**引入，不默认 Qi-1 复用。
- 产出（逐问）：数学模型完整公式 + 求解代码 + 数值结果 + 物理意义讨论 + **章节草稿卡**；跨问：依赖与固定输入的依据、单位与信息边界明确；对照证据：同口径横向对照（主模型 vs 基线，含失败路线）与支持归因所需的关键控制或适用消融（按实验循环）。
- 落盘：`decision_log.stages.5.sub_problems.Q<i>`（字段见 `templates/shared/decision_log.json`）+ `state/evidence_ledger.json` + 真源结果登记表。

## 循环编排（每问按序走完；括号=指回权威源）

正式图由 Agent 按 `references/figure_quality_layers.md` 自动设计、渲染、检查与精修。D.1 有明确授权即按真实对话登记，不重复询问常规设计；科学/成本/锁定风格改变仍须确认。

本问先以 `references/experiment_cycle.md` 的小实验检验关键风险，再扩到正式求解。新结果推翻计划时登记原因与受影响项；验证后按 `references/result_gallery.md` 检查是否存在有独立价值的展示候选，达到预算即停止。

| 步 | 做什么（一句话） | 权威源 / 落盘 |
|---|---|---|
| A0 | 本问选型确认（**必停点**）：与 stage 3 一致时轻量确认，不一致或无记录出完整选择卡；拍板后更新《选型总表》该行 | SKILL.md 必停点协议；选择卡规格 `references/stage_03_model_selection.md`；登记形状 `references/workspace_protocol.md` §12 |
| A | 模型完整化：变量/参数/约束编号 + LaTeX 公式，名称只反映真实实现 | 数学对象与命名纪律 `references/modeling_evidence_protocol.md` Stage 3 节 |
| B | 求解实现：中文注释、首行"对应论文 §X"、seed、关键字状态 print、结果落 `results/` | 代码样例 `templates/shared/code_starter/`；anti_pattern D1/D4（`competitions/<comp>/anti_patterns.md`） |
| C | 结果验证四查：状态（可行/最优/超时）→ 约束与单位 → 反例 → 同口径对照（基线也须可行）；国赛/研究生赛/华数杯按 Stage 5 知识包命中案例的 `required_solution_checks` 逐项核验并登记 evidence ID，不迁移历史数值 | 验证纪律 `references/modeling_evidence_protocol.md` Stage 5 节；知识包入口见下“精准指针”；收敛时程纪律见下 |
| C.1 | 按实际模型核对公式与代码；控制方程复杂时可单列 `results/Q{i}_formula_code_map.md`，否则复用验证记录 | **`references/modeling_evidence_protocol.md` Stage 5 节**（表模板 + 三条判定口径） |
| D | 子灵敏度：只计算并落盘（机器可读文件），**不出图** | `references/modeling_evidence_protocol.md` Stage 5 节"敏感性"（区分固定方案换参数评价 vs 每情景重新决策） |
| D.1 | 正式出图决策（**必停点**）：登记数量 / 风格 / 逐图叙事；已有有效授权直接登记，缺必要科学决策才询问 | **`references/figure_skill_bridge.md` 出图决策菜单节**（含 0/1 张披露、合并菜单、风格试产）；登记形状 `references/workspace_protocol.md` §12 |
| D.2 | 图表契约与生成：写清 core claim / figure type / source artifact / palette / 设计卡五要素 / 判据线 / 注释预算 → 生成 → 过 `figqa.py --strict` + `figure_lint.py` | 图表纪律 `references/figure_skill_bridge.md`；命中案例的 `figure_story` 组证据组 |
| E | 物理意义：数值 → 现实含义，含与同口径基线的对比（篇幅由内容决定） | 写作语域 `competitions/huaweibei/writing_voice.md`（研究生赛） |
| E2 | 章节草稿卡写入 `paper_workspace/sections/q{i}_draft.md`（write-as-you-solve） | **`references/modeling_evidence_protocol.md` Stage 8 节**（五件内容 + 冻结数字要求） |
| E3 | `state/evidence_ledger.json` 追加该问一行 | 同上（字段表） |
| F | L1 自评（per-Qi 5 维）+ 必要时 diff-only 精修；任一维 <7 → 精修，iter cap 3 | 维度与阈值 `references/rubrics.md` Stage 5 节；评分落盘 `scripts/score_artifact.py` |
| G | 输出移交：写 `decision_log.stages.5.sub_problems.Q<i>` | 字段模板 `templates/shared/decision_log.json` |
| H | 子检查点：复用链（题面要求？固定输入？）→ 符号一致 → 假设一致 → 假设变更历史核对 | 假设变更历史协议见下"失败处理" |

### 两条阶段纪律（本阶段原生）

1. **收敛性验证的时程纪律**：凡用网格/步长收敛序列作验证证据，扫描必须针对**本问判据物理量、在它真正成熟的时程**上做，不得跟着题面要求的输出窗口走。执行口径：先写出本问判据量（如"过程完成时刻""某时刻的关键场量"），再把收敛序列打到判据量自身上（判据量随离散参数 N 的变化），并确认扫描时程覆盖判据成熟时刻。依据为历史实测算例：早期窗口扫网格会误判"已收敛"，同一粗网格在判据成熟时刻与收敛解相差明显，属典型误判。
2. **网格/离散充分性**：扰动档按参数空间组织时，凡使边界层/薄层厚度骤减的档（传质/换热系数数量级放大、扩散系数数量级减小），原收敛网格对该档不再收敛。触发与判据用 `templates/shared/code_starter/simulation.py` 第 6 节（`boundary_jump_ratio` + `check_grid_sufficiency`）——**阈值 10×/20% 是实测算例锚定的默认档、可按题覆盖并登记，不是跨题普遍门槛**；判欠分辨的档从灵敏度排序剔除并如实标注"网格受限、未量化"。

## 必停点与门禁

- 本阶段三个必停点：**A0 每问选型确认**、**D.1 每问图表菜单**、**每问 verdict 即问即登记**（`qi_verdict["Q<i>"]`）；聚合后的整体决策登记进 `decision_log.stages["5"]`，**不得复制进 qi_verdict**（一次问答复制到所有 Qi 等于伪造逐问确认）。
- 每问/每阶段推进前跑 `python scripts/check_gate.py --gate 5` 与 `--checkpoint per_qi_selection.Q<n>` / `figure_menu.Q<n>`（语义见 `SKILL.md` 必停点协议）；exit 1 按 verdict=block 同级处理（暂停 + 编号菜单）。
- 聚合与 verdict：per-Qi 加权聚合、差异化降级（`refine_partial` 只修弱问）、`score_artifact.py --mode aggregate_qi` 调用与 gate 5 双路径落盘口径 → **`references/rubrics.md` per-Qi 聚合节**；verdict 阈值表 → `references/rubrics.md` 阈值汇总 + `SKILL.md` §5。

## 失败处理

| 触发 | 处理 |
|---|---|
| 某问 L1 不过（任一维 <7） | 只精修该问（section-patch），iter +1；cap 3 后仍不过 → `carryover`，标记交 L2/终审 |
| 某问 min <7 而其他问已 pass | `refine_partial`：只重跑该问 A-G，不动其他问 |
| 实验出现方法前提或机制缺口 | 触发 stage 5 文献挂点（按profile定向检索方法名与失效场景，寻找失效证据与替代路线），登记 `decision_log.stages.5.literature_searches`（协议 `references/literature_scout.md`） |
| 收敛/网格不足 | 不得写"已收敛"；按上一节两条纪律处理，结论处如实标注"未量化/未解决" |
| 结果不可行或状态异常 | 不伪装最优（状态/可行性/性能分开报告，`references/modeling_evidence_protocol.md` Stage 5 节） |
| 假设被 L2 patch 后 | 走 H 的子检查：依赖该假设 → 重跑 A/B 并同步 C/D 与证据；不依赖 → 标记"Q<i> 不受 patch X 影响" |
| 输出/结果缺失 | 记 `unstarted`/`partial` 进答题义务表（stage 2 镜像），交接缺口与状态，**不宣称答完** |

## 精准指针

| 主题 | 权威源 |
|---|---|
| 公式-代码一致性（表模板 + 判定三条） | `references/modeling_evidence_protocol.md` Stage 5 节 |
| 草稿卡五件 + evidence_ledger 字段 | `references/modeling_evidence_protocol.md` Stage 8 节 |
| 出图决策菜单 / 0-1 披露 / 合并菜单 / 风格试产 | `references/figure_skill_bridge.md` 出图决策菜单节 |
| 图表路由、设计卡五要素、判据线、示意图草稿通道 | `references/figure_skill_bridge.md` 图叙事章 + 顶部总路由表 |
| per-Qi 聚合、差异化降级、verdict 阈值 | `references/rubrics.md` Stage 5 节 + 阈值汇总 |
| 必停点定义/登记键、`check_gate` 语义 | `SKILL.md` 必停点协议；条目形状 `references/workspace_protocol.md` §12 |
| 并行派发、子代理最小规则 | `references/parallel_dispatch.md` |
| 模型候选、失效边界 | `references/model_catalog.md`（含 §12 失效边界） |
| 子问级案例检索与迁移边界 | `scripts/build_stage_pack.py --stage 5` + `competitions/<comp>/case_retrieval.md` |

## 退出条件（整个 stage 5）

1. 所有 Qi 通过 per-Qi rubric（全维 ≥7）**或** verdict ∈ {pass, pass_with_review} 经聚合
2. Stage-level rubric 全维 ≥7（维度见 `references/rubrics.md` Stage 5 节）
3. 题面依赖与固定输入均满足；未完成的义务保留状态与缺口，不宣称全部答完
4. (championship) red-team 一次，针对最弱 Qi（优先 `review_qis`）
5. 触发 L2：回检 stage 3（选型前提是否被结果推翻）+ stage 4（符号一致）+ review_qis（若 verdict=pass_with_review）

→ 跳转 `stage_06_robustness.md`（stage 6 复用本阶段求解器代码；stage 8 直接基于本阶段草稿卡组装）
