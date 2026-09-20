---
stage: 9
name: review
duration_h: 2-6
inputs: [paper.tex, decision_log_full, decision_log.competition]
outputs: [stage.9.{anti_patterns_check, panel_scores, weakest_section, redo_log, red_team_record, skill_issues_consumed, final_pdf_path, submission_ready}]
loads_reference: [competitions/<competition>/anti_patterns.md, competitions/<competition>/rubric_overlay.json, feedback_layer3_panel.md]
loads_template: [templates/latex/<competition>/]
feedback: [L1, L3_5_panel, red_team_in_championship]
next: SUBMIT
---

# Stage 9 — 终稿审核 + 视觉化润色 + Panel 多视角评审：编排

**定位**：本文件只管**编排**（顺序纪律 / 步骤 / 必停点 / 失败处理 / 指针）。评分口径、panel 定义、呈现 20 条、提交清单都在权威源。
**时长**：2-6h | **反馈层**：L1 + L3 panel | 全流程终点。

## 触发与入口

- 进入条件：stage 8 退出门禁全过（含摘要证据链 `abstract_gate=pass`）。
- 用户在 Codex 说"终审论文 / 最后 6 小时检查"时走**极速终审路径**（见下），不启动完整长 panel。
- 终审前必须跑 `python scripts/trace_claims.py --input state/paper_plan.json --strict`；`abstract_gate` 不是 `pass` 时先修缺失结果或验证，不进入终稿 panel。
- 终稿链口径：`decision_log.final_chain=docx` 时，本阶段一切验收以 **docx 版 PDF** 为对象（tex 专属项标"未适用"，改跑 `scripts/docx_number_recheck.py`；协议 `references/docx_final_channel.md`）。

## 输入 / 产出

- 输入：`paper.tex` / 论文 PDF、全部 figures/ tables/、decision_log 全量、按 competition 加载 `anti_patterns.md` + `rubric_overlay.json` 的 `panel_personas`、`config/rating_contract.json`、`state/paper_plan.json` + `state/evidence_trace.json`、`state/skill_issues.md`（台账，终审必读）。
- huaweibei 附加：先重读 `competitions/huaweibei/current_rules.md` 并核对日期戳；确认知识、案例、统计与奖项字段均来自该目录，2022—2025 未被推测为提名。
- 产出：最终 PDF（或 docx 链产物）、L3 panel 评分 + 瓶颈段一次重做、(championship) red-team 记录、`decision_log.stages.9`（含 `submission_ready`）。

## 顺序纪律（不可调换）

先**过资格门**，再**冻结标准**，最后才**读论文打分**——顺序反了会出现"看完论文倒推标准"的锚定偏差。

```
Step 0 资格门（7 条硬规则，任一不过 → "不具备获奖资格"，不打分不修分，直接返回用户）
  ↓ 全过
Step 1 冻结本题原子扣分清单（读题后、读论文前写下来并冻结；评审中补标准只能作为追加项，不得倒推已评块分数）
  ↓ 冻结
Step 1..9 操作流程（含 panel）
```

- **Step 0 资格门**：7 条硬规则 = 承诺书页 / 编号页 / 摘要独占页 / 页码起算 / 匿名性 / 页数口径 / 引用合规，逐条指向 `references/submission_checklists.md` 对应节；页数口径唯一权威源 `references/cn_presentation_spec.md` §1.6（mcm 总 PDF ≤25 页含附录为硬规则）。
- **Step 1**：清单写入 `state/judge_deduction_checklist.json`（或 `decision_log.stages.9.deduction_checklist`），冻结后评审期内不得增删改。

## 操作流程（Step 1-9）

图表检查分层见 `references/figure_quality_layers.md`：科学、必交和实际尺寸可读性是硬条件；面板/节点/卡片风格是建议。预览不替代原图，未看真实渲染不得记视觉通过。

| Step | 做什么（一句话） | 权威源 / 入口 |
|---|---|---|
| 1 反模式逐条对照 (45 min) | 按本竞赛 `anti_patterns.md` 逐项判定：high → 立即修；medium → 标记，panel 后再定；通过 → 记录 | `competitions/<comp>/anti_patterns.md` |
| 2 视觉化润色 + 呈现终检 (45 min) | 图/表/公式/全文一致性的机器可查项 + **呈现 20 条逐项判定（硬门 pass，建议项可"未适用/未测"）** | `references/cn_presentation_spec.md` §10（清单）+ §7（图题与图内纪律）；配色 `references/color_typology.md` |
| 2b 视觉回证派发 | **逐页回证、结论带页码**（标题页/摘要页/图表页/公式页/参考文献页/附录页全覆盖；抽页只能记"局部检查"、覆盖不全标 `未完成`）；两步前置 = `scripts/pdf_qa.py <终稿.pdf> --page-map` 映射表随 prompt 给出 + 验收对象用带时间戳副本、禁止同名覆盖 | **回证项与范围单权威 `references/cn_presentation_spec.md` §9.2**；派发协议 `references/parallel_dispatch.md`；识图先行 `references/figure_skill_bridge.md` |
| 2c 视觉基准对照（建议项） | 有基准 PDF 时渲染代表页逐项对照（可扫读性/加粗密度/图占版面/图题/留白/标点）；无基准标 `未适用`，**不得假 pass** | 对照结论写入 `真源.md` 修订记录 |
| 2d 文献首引机检 | `scripts/ref_order_audit.py --workspace <项目根>`；exit 1 先修再进 panel | — |
| 3 L3 5 视角 Panel (1h) ⭐ | 单条消息并发 5 个 panelist（或串行 + 独立 conversation）；输出 JSON → 编排方聚合找瓶颈段 | **`references/feedback_layer3_panel.md`**（视角定义/隔离/聚合） |
| 4 定向重跑瓶颈段 (45 min) | 只修 must_fix（high 立即 diff-only 修；medium 记录，时间紧可跳过），不重做整阶段 | — |
| 5 二次 Panel (15 min) | 只对修订段落复评；panelist 5 上升 → 收工；未达标且预算耗尽 → 提交当前版本 | `references/feedback_layer3_panel.md` |
| 6 Red-team（championship, 30 min） | 演最严苛评委给 ≥3 条 reject 理由 + 作者 100 字反驳；反驳弱 → 修，反驳强 → 在 §7 加"潜在质疑回应" | — |
| 7 编译 + PDF 输出 (15 min) | xelatex 三编（或 docx 链转换）；检查页数口径、无 `??`、无成片 overfull、PDF 可开 | 页数口径 `references/cn_presentation_spec.md` §1.6 |
| 8 台账沉淀 (5 min) | 读 `state/skill_issues.md`；筛"建议入版"条目 → 编号菜单让用户拍板是否反馈（**agent 不擅自改 skill 仓库**） | `references/workspace_protocol.md` §11 |
| 9 最终输出 (5 min) | 写 `decision_log.stages.9`（anti_patterns_check / panel_scores / weakest_section / redo_log / red_team_record / final_pdf_path / skill_issues_consumed / submission_ready） | 字段模板 `templates/shared/decision_log.json` |

**时序硬约束**：`submission_ready=true` 必须在 Step 8 台账消费完成之后写入。

**极速终审（"最后 6 小时 / 马上提交"，30-60 min）**：不启动长 panel，按固定优先级查 5 项——① 摘要结果证据（逐问方法/结果/验证/边界；可量化任务必须给关键数值或排序结论）；② 图表解释（坐标/单位/图注 + 正文解释）；③ 符号一致（符号表/公式/图表/正文）；④ 结论对应题问（每问有明确回答）；⑤ 高危反模式（本竞赛 `anti_patterns.md` 只抓 high）。输出：提交风险（低/中/高）+ 必须立即修 + 可暂缓 + 提交前最后动作；风险为高时必须给 `1-5` 编号菜单（先修摘要/图表/符号/结论/让我决定）。

## 必停点与失败处理

| 触发 | 处理 |
|---|---|
| 资格门任一条不过 | 输出"不具备获奖资格" + 未过条目与修复动作，直接返回用户；**不进入打分、不做分数修补** |
| 疑似泄漏（结果好得离谱） | 标记并按 0 分挂起该块，查明前不奖励高分（口径 `references/feedback_layer3_panel.md` 评委模拟器节） |
| 视觉关未执行 / 无法判定 | 如实记 `未测`，不得写"视觉通过"；不得用源码或文本层检索代替 |
| 建议项未做（基准对照/加粗密度等） | 记 `未适用`/`未测` 并写理由，**不得假 pass**；用户硬门不因此放行 |
| panel 分歧 >20 分差 | 禁平均，按 `references/feedback_layer3_panel.md` 冲突裁决 |
| 时间预算耗尽 | 提交当前版本并标注未达标项（不得改分） |

## 精准指针

| 主题 | 权威源 |
|---|---|
| 评委模拟器扣分制（原子扣分表/90% 封顶/格式乘数/校准锚/负锚点） | `references/feedback_layer3_panel.md` 评委模拟器节；入口 `scripts/score_artifact.py --mode judge` |
| 5 视角定义、盲评隔离、聚合、冲突裁决 | `references/feedback_layer3_panel.md`（主体） |
| 呈现 20 条与视觉走查 | `references/cn_presentation_spec.md` §10 + §9 |
| 提交清单（承诺书/编号页/匿名/页数/引用合规） | `references/submission_checklists.md` |
| 反模式条目 | `competitions/<comp>/anti_patterns.md` |
| 验收"三选二"独立来源 | `references/workspace_protocol.md` §7 |
| 台账协议 | `references/workspace_protocol.md` §11 |
| PDF/页数/工件扫描/页码映射 | `scripts/pdf_qa.py`（`--artifact-scan` 默认开、`--page-map`） |
| rubric 维度 | `references/rubrics.md` Stage 9 节 |

## 退出条件（整个 skill 终点）

1. 本竞赛 anti_patterns 全部通过或高危项清零；panel 的人工建议按三态登记（`pass`/`未适用`/`未测` 各写理由，**建议项不强求全 pass，但不得假 pass**）；用户硬门——资格门、`check_gate.py`、图表门、数字冻结与回检、提交清单——必须全过
2. L3 panel mean ≥ 8，panelist 5 verdict ≥ "second"（理想 "first"）
3. PDF 编译成功（docx 链以 docx 版 PDF 为对象）
4. (championship) red-team 攻击全部有可信回应
5. `decision_log.stages.9.submission_ready == true`

→ **提交!**
