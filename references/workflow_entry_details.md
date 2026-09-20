# 工作流按需细则

仅在启动、任务加载、故障处理或竞赛特化时读取对应小节。路径均相对于技能根目录。

明确任务直接执行入口路由；菜单只用于意图不清。启动只补缺失信息，已有回答直接复用。本文中恢复动作统一指向 `references/workspace_protocol.md` §4；旧式编号菜单示例按当前宿主交互能力呈现。

## 1. 范围与意图路由

覆盖：多竞赛选题比较、审题与分解、模型选型、求解与验证、灵敏度与稳健性、图表规划与出图、论文写作、模拟评审、提交打包。**纯概念问答、只改一段文字、只审一张图属于局部任务**——直接做，不启动五幕流程、不建 state、不写 decision_log。

| 用户说法 | 首要动作 |
|---|---|
| "开始建模" / "打××赛" | 给 `references/codex_practical_menu.md` 一屏菜单（1-5） |
| "华为杯" / "研究生赛" / "研赛" | 研究生赛专项：`huaweibei` + 跨赛共用层 + `competitions/huaweibei/` + 作战表 |
| "华数杯" | 华数杯专项：`huashubei` + 选题矩阵 + 图表包 + 72h 表，国一标准 |
| "比较 A/B/C 题" / "帮我选题" | Stage 1：`topic_specs.json` + 检索；华数杯加选题矩阵 |
| "用什么模型" / "给选型建议" | Stage 3 选择卡：候选短名单 + 《选型总表》，**不进求解** |
| "帮我求解" / "直接解这道题" | 查 state 后进 Stage 5；无 stage 3 选型记录**先补选择卡**，A0 不得跳过 |
| "帮我查文献" | 文献挂点（stage 1/3/5）：`references/literature_scout.md` + 脚本，方法卡标 review_status |
| "写摘要/问题分析/模型段/结果解释" | Stage 8 局部写作：只写该节、默认不写 state；实为求解/选型诉求时不得走本入口 |
| "画图/美化图/规划图表" | 图表桥：`figure_skill_bridge.md` 总路由表；华数杯加图表包 |
| "想用 Word 终改" / "出 docx 终稿" | docx 终稿通道：`references/docx_final_channel.md`（冻结后专用） |
| "终审论文" / "最后 6 小时" | Stage 9 极速终审：摘要定量、图表解释、符号一致、结论对应题问 |
| "继续 stage N" / "看进度" | 恢复 state：读 `cwd/state/decision_log.json`（§4） |

意图不清：直接给工作台菜单，让用户回复 `1-5`；明确的小实验或模型比较按 `references/experiment_cycle.md`，附件检查按 `references/multimodal_assets.md`，备选图按 `references/result_gallery.md`。

### Quick Start（用户首次说"开始建模"）

**🔴 CHECKPOINT · 启动写入前确认**：只有用户明确进入完整工作流才创建或修改 `cwd/state/decision_log.json`；咨询、润色、局部审稿不写 state。

Codex 首屏用 `references/codex_practical_menu.md` 工作台菜单：`1` 完整 5 幕 10 步（继续问 5 项）｜`2` 只比较 A/B/C 题 → Stage 1｜`3` 局部任务（写作/摘要/图表/终审）→ Stage 8 或 9｜`4` 选型建议 → Stage 3 选择卡，**不进求解**｜`5` 读已有 state 恢复。

完整流程四步（agent 自动完成）：① ≤50 字介绍；② 一次问齐 5 问——竞赛（默认 cumcm）/ 题号（依竞赛，可"未公布"）/ 队员与擅长 / 截止时间 / 题目 PDF 路径（可"未公布"）；③ 初始化——无 `cwd/state/decision_log.json` 则从 `templates/shared/decision_log.json` 复制并写入 `competition` 与 5 答，有则读 `current_stage` 恢复（§4）；④ 加载 `competitions/<comp>/winning_patterns.md` 一次建基线后进 Stage 0（`references/stage_00_kickoff.md`），不重复问已问过的问题。

**Codex 编号菜单**：Codex 无 `AskUserQuestion` 弹窗，一律用 Markdown 编号菜单（离散选择 `1)`—`5)`，第 5 项固定兜底"让我决定 — 推荐项与原因"）；自由文本只问短输入（队员分工/截止/PDF 路径）。用户回数字后 agent 自动写 state 并继续，不二次确认、不要求用户手写 JSON。主竞赛菜单固定 `1) huaweibei 研究生赛  2) huashubei 华数杯  3) cumcm 国赛  4) 其他竞赛  5) 让我决定`。

## 2. 任务加载套餐（按任务一次取齐，章节级指针）

**指针优先到小节**：`workspace_protocol` / `cn_presentation_spec` / `figure_skill_bridge` / stage 文件都是大部头，能指小节就不整本加载；下面"章节"列给的就是该任务真正要读的范围。

| # | 任务 | 加载（含章节） | 产出 |
|---|---|---|---|
| 1 | 启动完整流程 | 本文件 §1 + `references/codex_practical_menu.md` + `references/workspace_protocol.md` §1/§2/§4 | 5 答入 state + Stage 0 骨架 |
| 2 | 选题比较 | `competitions/<comp>/topic_specs.json` + `case_retrieval.md` + `scripts/build_stage_pack.py --stage 1`；华数杯加 `references/huashubei_topic_decision.md` | 选题建议（编号菜单拍板） |
| 3 | 模型选型 | `references/stage_03_model_selection.md` 选择卡节 + `references/model_catalog.md` 对应域 + 题目域 playbook；文献挂点 ≤2 次/≤5 篇 | 候选短名单 + 《选型总表》`cwd/selection_sheet.md` |
| 4 | 子问求解 | `references/stage_05_subproblem_loop.md` 本问链路（A0→A/B/C/C.1→D/D.1→E/E2/E3→F/G/H）+ `references/modeling_evidence_protocol.md`；出图加 `references/figure_skill_bridge.md` 图叙事章 + 出图决策菜单节；**冻结时点/改源/数字进稿时**按需只读 `references/workspace_protocol.md` §5（冻结时点）/ §6（数字注入）/ §9（改数四步）/ §10（哈希级联失效）对应小节 | 每问结果 + 草稿卡 + per-Qi 评分 |
| 5 | 论文写作 | `references/stage_08_writing.md` 写作顺序 + 对应章节 + `<comp>/{abstract_template, phrase_bank, paper_skeleton}.md` + `references/cn_presentation_spec.md` 相关节；十类自查 `references/ai_flavor_removal.md`；**数字进稿/改源时**加 `references/workspace_protocol.md` §6/§9/§10 对应小节 | md 真源正文 + 摘要三遍 + 机检（claim/文献序） |
| 6 | 局部单图 / 单节（不写 state） | 单图：`references/figure_skill_bridge.md` 图叙事章 + `references/cn_presentation_spec.md` §7；单节：`references/ai_flavor_removal.md` + `<comp>/phrase_bank.md`；**不加载 stage 5/8/9 全书** | 该图/该节成品 |
| 7 | docx 终稿链 | `references/docx_final_channel.md` + `references/cn_presentation_spec.md` §5.1/§5.6/§6/§7/§10 | docx → PDF + 数字回检 |
| 8 | 终审提交（加载较多） | `references/stage_09_review.md` + `<comp>/anti_patterns.md` + `<comp>/rubric_overlay.json` + `references/cn_presentation_spec.md` §10（清单）+ §9.2（**视觉回证单权威**：逐页、带页码）；panel 加 `references/feedback_layer3_panel.md`；数字冻结/回检及 stale 处置读 `references/workspace_protocol.md` §9/§10，涉及改源、重新注入时按需读 §5/§6 | 机检链（trace_claims→consistency→judge→pdf_qa→package）+ 提交包 |

## 5. 模式与预算

`fast` 侧重 L1，`standard` 默认 L1+L2，`championship` 在时间允许时加 panel、校准与核心风险反事实。历史 token 参考上限分别为 50k/200k/500k，不是必须耗尽的目标。不足 6 小时时优先 Stage 9 的高风险检查；其余按队伍剩余时间确定求解与成稿预算。`interaction=detailed|auto` 沿用已有用户选择，明确任务不重复问；必停点登记仍按 SKILL.md。

## 7. 条件加载：失败兜底

| 触发 | 一线处理 | 仍失败兜底 |
|---|---|---|
| 题目 PDF 打不开 | 请用户重给路径；未公布记 `problem_pdf="pending"` | 用题号与已知规则进 Stage 0，不编造题面 |
| `decision_log.json` 不存在 | 从模板复制并写入启动 5 答 | 只在对话维护临时状态，提示 state 未落盘 |
| state 损坏/缺字段 | 备份为 `decision_log.bak.<ts>.json` 后按模板补齐 | 不能备份则暂停、展示损坏位置、请用户确认重建 |
| competition 缺失/非法 | 主菜单选 huaweibei / huashubei / cumcm / 其他 | 按上下文推断（华为杯→huaweibei、华数杯→huashubei），否则默认 cumcm 并写 events |
| 当前 stage reference 缺失 | 回五幕索引，加载相邻阶段 + `references/rubrics.md` 通用规则 | 暂停该阶段并说明缺失文件，不跳过关键评审 |
| 评分脚本失败 | 读报错，查输入 JSON / Python 环境 / 路径 | 改 rubric 手工评分并标 `manual_fallback` |
| 编译/转换失败 | LaTeX：定位首个报错（模板变量/图片路径/中文编译器）；docx：`docx_to_pdf.py` 自动落 soffice 兜底 | 交付 md/tex 草稿并说明 PDF 未生成；或手动另存 PDF。**换终稿链（tex↔docx）必须经用户明确同意并登记 `final_chain`，不得擅自切链** |
| token 超预算 | 降级 mode，只保留阶段摘要、关键数据与路径 | 暂停长文生成，先让用户确认优先章节 |

## 10. 竞赛专项加载（competition=X 时加件）

| 竞赛 | 按**当前 stage** 触发加件（不要整包同时加载） |
|---|---|
| huashubei 华数杯 | stage 0：`references/huashubei_battle_plan_72h.md`；stage 1：`references/huashubei_topic_decision.md`；stage 3/5：`competitions/huashubei/distilled_modeling.md`；stage 5/8：`references/huashubei_figure_pack.md`；stage 8：`competitions/huashubei/` 的 `winning_patterns.md` / `abstract_template.md` / `phrase_bank.md` / `paper_skeleton.md` / `empirical.json`；stage 9：`competitions/huashubei/anti_patterns.md` + `rubric_overlay.json`（6 维国一 overlay + 4 角色 panel） |
| huaweibei 研究生赛 | stage 0：`references/huaweibei_battle_plan_72h.md`（含 h48 硬冻结 + 独立验收三选二）；stage 1/3：`competitions/huaweibei/topic_specs.json` + `case_retrieval.md`；stage 3：`competitions/huaweibei/playbooks/` 命中域 + `competitions/huaweibei/papers/domain_index.md`（命中后按 paper_id 定向读 `competitions/huaweibei/papers/manual_paper_reviews.json`）；stage 4/8：`references/cross_competition_distillation.md`；stage 5/8：`competitions/huaweibei/distilled_modeling.md` + `distilled_figures.md`；stage 8：`writing_voice.md`（必载）+ `writing_playbook.md` + `writing_examples.md` + 该赛 abstract/phrase/papers 件；stage 9：先核 `current_rules.md` 日期戳，再用 `anti_patterns.md` + `rubric_overlay.json`（五角色 panel） |
| cumcm 国赛 | stage 1/3：`competitions/cumcm/topic_specs.json` + `case_retrieval.md`；stage 3：`competitions/cumcm/playbooks/` 命中域（先读其 README 域→文件映射）；stage 1/3/5：`competitions/cumcm/distilled_modeling.md`；stage 5/8：`competitions/cumcm/distilled_figures.md`；stage 8：`winning_patterns.md` / `abstract_template.md` / `phrase_bank.md` / `paper_skeleton.md`；stage 9：`anti_patterns.md` + `rubric_overlay.json`。页数口径见 `references/cn_presentation_spec.md` §1.6；旧辅助层已随 v3.3.0 移出公开仓库（残值在 `phrase_bank.md` §13） |
| mcm 美赛 | stage 8：`competitions/mcm/memo_letter_guide.md` + `competitions/mcm/abstract_template.md` + `templates/latex/mcm/main.tex`；不适用 docx 中文终稿通道 |
| diangong / apmcm | 按所在 stage 读各自 `competitions/<comp>/` 对应件（topic_specs / abstract_template / phrase_bank / anti_patterns …）；基线 `seed v0.1` / `empirical_local_2024_2025`，输出标注 seed 并降低结论确定性 |
