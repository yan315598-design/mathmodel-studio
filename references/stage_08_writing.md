---
stage: 8
name: writing
duration_h: 12-30
inputs: [decision_log.stages.0-7, decision_log.competition, decision_log.task_type]
outputs: [stage.8.{section_word_counts, figures_per_subproblem, tables_per_subproblem, abstract_drafts, anchor_phrase_hits, danger_phrase_hits}, paper.tex]
loads_reference: [competitions/<competition>/winning_patterns.md, competitions/<competition>/phrase_bank.md, competitions/<competition>/anti_patterns.md, competitions/<competition>/empirical.json, references/cn_presentation_spec.md]
loads_template: [competitions/<competition>/paper_skeleton.md, competitions/<competition>/abstract_template.md, templates/latex/<competition>/]
feedback: [L1, L2_at_end]
next: stage_09_review
---

# Stage 8 — 论文写作（摘要三遍制）：编排

**定位**：本文件只管**编排**（触发 / 输入产出 / 顺序 / 关口 / 失败处理 / 指针）。各节的**写法**（句式、结构、呈现口径、AI 味）都在权威源，本文件不复制。
**时长**：12-30h | **反馈层**：L1（末尾 L2）| 约占全流程时间 25-30%。

## 触发与入口

- 完整写作：stage 0-7 完成后进入；**不重新建模、不重新求解**（发现需要 → 触发 L2，不自行回退）。
- 局部任务（用户只说"写摘要 / 写问题分析 / 写模型段 / 写结果解释 / 写图表说明"）：按下表只做该节，**默认不写 state**；若诉求实为**求解或选型**，不得走本入口（必须过 stage 3 选择卡与 A0）。

| 用户任务 | 必读（章节级） | 输出 |
|---|---|---|
| 摘要 | `<comp>/abstract_template.md` + `<comp>/phrase_bank.md` §1 + stage 5-7 结果 | 中文摘要 / MCM Summary（问题分解、方法、关键数值、稳健性、推广） |
| 问题分析 | 题面、stage 2 分解、`<comp>/paper_skeleton.md` | 每问一段"本质—难点—方法—承接" |
| 模型段 | stage 3-5 产出、符号表；huaweibei 另按题型读 `writing_playbook.md`，推导按 `writing_voice.md` §3.5 四步叙事 | 变量、目标、约束、算法步骤、求解说明 |
| 结果解释 | stage 5 结果、stage 6 稳健性；huaweibei 按 `writing_voice.md` §5 五步（报→比→归因→分解→边界） | 数值结论 + 物理意义 + 对题问的回答 |
| 图表规划/说明 | `references/figure_skill_bridge.md` + `distilled_figures.md`（如有） | 图表计划、图注、坐标单位检查、正文解释句 |

任务不清时给编号菜单（`references/codex_practical_menu.md`）；用户选"让我决定"时优先补摘要或结果解释。

## 输入 / 产出

- 输入：stage 0-7 全部 decision_log；按 competition 加载 `paper_skeleton.md` / `abstract_template.md`（研究生赛与华数杯不得互换）/ `winning_patterns.md` / `phrase_bank.md` / `anti_patterns.md §A_I` / `empirical.json`（只对完整覆盖且被 `scoring_policy` 允许的字段注入 evidence）；中文竞赛必载 `references/cn_presentation_spec.md`（**按节加载**，终检才整读 §10）；LaTeX 模板 `templates/latex/<comp>/`。
- 产出：md 真源正文（`paper_workspace/`）+ `figures/` + `tables/` + 最终 PDF（或 docx 终稿链产物）；`decision_log.stages.8`；`state/evidence_ledger.json`（摘要主张逐问齐备）。
- 先跑 `scripts/generate_paper_plan.py` 生成动态章节、图表计划与证据账本；三赛写作从命中案例读 `writing_blueprint`/`figure_story`，**只迁移结构不复制原句**，历史数值一律不得迁移。

## 写作编排

**三个关口（按序，缺一不可）**

1. **样张先行**：全量铺开前先产 1 页样张（摘要初稿 + §5 任一问的一节正文，含 1 图 1 表）**真实渲染成 PDF** 给用户过目——版式/标点/加粗路标/图题长度/段落密度是否合意，反馈落实后再全量写作。**样张关即视觉关**：结论必须来自渲染页的真实视觉判定（用户过目或环境视觉通道），**不得用 md 源码、文本层字符检索替代**；未渲染不得记"样张已确认"。`interaction=detailed` 不可跳过；`auto` 可跳过但须登记。
2. **终稿链选择（与样张同行问）**：编号菜单 `1) LaTeX（默认）2) docx 终稿通道`，写入 `decision_log.final_chain`（`tex`|`docx`）。写作全程仍写 md 真源；选 `docx` 时 stage 8 内容门禁照过、tex 专属质检可跳过，出口自动按 docx 通道推进，呈现终检以 docx 版 PDF 为对象，协议唯一权威源 `references/docx_final_channel.md`。**冻结完成前任何链下都禁止人改 docx**；用户说"少问/你自己定"时按 `tex` 登记并注明。
3. **摘要三遍制**：骨架期写初稿定主线（6 句式：问题→方法→关键结果→验证→结论）→ 全部结果完成后按证据账本重写 → 终审前终审润色。定稿前提是 `scripts/trace_claims.py --strict` 的 `abstract_gate=pass`。

**正文写作顺序（可复用骨架）**：§1 问题重述（用 `templates/shared/restatement_card.md`）→ §2 问题分析（含流程图）→ §3 模型假设（复用 stage 4，每条带依据）→ §4 符号说明（booktabs 三线表，全单位）→ ⭐摘要初稿 → 逐问组装 §5.i（基于 `paper_workspace/sections/q{i}_draft.md` 草稿卡扩写；无草稿卡才从零写）→ §6 灵敏度（复用 stage 6）→ §7 评价与推广（复用 stage 7）→ §8 参考文献 → 附录（`templates/shared/appendix_checklist.md`）→ ⭐摘要重写（按证据账本）→ 整篇 L1 自评 + 修订 → ⭐摘要终审润色。理由：初稿防跑偏、重写防"摘要绑架"、润色只改表达不改数据。
各节写法与模板句：`<comp>/phrase_bank.md`（按章取用，**同款句式每节 ≤1 次**）+ `paper_skeleton.md`；附录代码三段式（中文注释 / 首行"对应 §X.Y.Z" / 删除 print 残留）见 `anti_patterns.md` D1。

**每节成稿后两个小循环**：① 引用缺口补查（按 `references/reference_skill_bridge.md`，硬上限 5 次搜索，够用即停）；② 去 AI 味自查（`references/ai_flavor_removal.md` 词句十类；版式四类为**建议性**、全文级、在终审跑）。

## 必停点与失败处理

| 触发 | 处理 |
|---|---|
| 写作期需要动模型/结果 | 不自行回退：触发 L2（`references/feedback_layer2_backtrack.md`）定向回滚 |
| 图注需改 | **回源**：改 `真源.md` 图表登记表"终稿图注"列（唯一来源），正文只逐字复制；不得就地改写 |
| 示意图仍是 `*.draft` | 列出清单提醒用户精修回贴；正文只收录无 `.draft` 后缀版本（分野协议 `references/figure_skill_bridge.md` 图叙事章） |
| 作战地图缩略 | 必须是真实结果成品，不得画假图 |
| 证据链不完整 | `trace_claims.py --strict` 不过 → 不得定稿摘要；缺口按 unstarted/partial 如实披露 |
| 结算-结果矛盾 | `scripts/claim_consistency_check.py --draft <正文> --results results/ [--strict]`；warn/info 人工核对后在真源登记处理结果 |
| 文献首引乱序 | `scripts/ref_order_audit.py --workspace <项目根>`；exit 1 先修再进摘要重写 |
| 经验校准越界 | 只取 `config/rating_contract.json` ∩ `competitions/<comp>/empirical.json.scoring_policy`；图表数/章节数/正文字数/词频**不作硬阈值** |
| 编译/导出失败 | 见 `SKILL.md` §7 失败兜底（换链须用户确认） |

## 精准指针

| 主题 | 权威源 |
|---|---|
| 摘要结构/句式/填空 | `competitions/<comp>/abstract_template.md`（各赛独立）+ `phrase_bank.md` §1 |
| 呈现规范（版面/标点/摘要加粗/公式/表格/图题/voice/终审 20 条） | `references/cn_presentation_spec.md`（按节） |
| 章节结构提示与模板句 | `competitions/<comp>/phrase_bank.md` §13 + `paper_skeleton.md` |
| AI 味词句十类 / 版式四类（建议） | `references/ai_flavor_removal.md` |
| huaweibei 语域/推导/结果五步 | `competitions/huaweibei/writing_voice.md`（+ `writing_playbook.md` / `writing_examples.md`） |
| 图表纪律、出图菜单、图注来源 | `references/figure_skill_bridge.md`；登记表与"设计卡 / 终稿图注"两列写入纪律 `references/workspace_protocol.md` §2 真源模板 |
| docx 终稿通道 | `references/docx_final_channel.md` |
| 证据约束写作（主张-证据表、摘要诚实口径） | `references/modeling_evidence_protocol.md` Stage 8 节 |
| rubric 维度 | `references/rubrics.md` Stage 8 节 |

## 退出条件

1. 动态骨架覆盖全部题问，附录按提交要求完成
2. 摘要证据链 `abstract_gate=pass`；证据账本中摘要实际覆盖的每个 Qi 行有非空 `abstract_claim`
3. 每张图表绑定唯一主张、上游数据、必要检查和正文解释；图注逐字来自真源"终稿图注"列
4. 关键公式、结果、图表与引用编号可追踪；真源对账已抽查（`scripts/freeze_numbers.py check` 辅助）
5. xelatex（中文竞赛，含 apmcm）或 pdflatex（英文 mcm）编译无错（docx 链按链产物验收）
6. 结论-结果核验通过（`claim_consistency_check.py --strict` exit 0）；文献首引顺序机检通过
7. 呈现规范自查：中文竞赛按 `cn_presentation_spec.md` §10 逐条给结论（硬门 pass，建议项可"未适用/未测"但不得假 pass）
8. 样张已确认（视觉关）；L1 全维 ≥7；L2 跨阶段回检无新增偏离

→ 跳转 `stage_09_review.md`
