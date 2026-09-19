---
name: mathmodel-studio
description: 数学建模竞赛全流程助手。从选题、审题、建模、求解、验算，到写论文、画图、模拟评审、打包提交，按阶段带你走完一篇可提交的竞赛论文。支持华为杯研究生赛、CUMCM 国赛、华数杯、MCM/ICM 美赛、电工杯、APMCM 亚太杯。内置从历年优秀论文提炼的建模经验库和分题型写作范式；图表统一配色、出图自动质检；论文里每个数字都可回溯；提交前有评委模拟终审。全程问答式，用户只需选编号。Use when the user says 建模、数模、开始建模、数学建模、华为杯、研究生赛、研究生数学建模竞赛、华数杯、CUMCM、国赛、MCM、ICM、美赛、电工杯、APMCM、亚太杯、选题、相似题、模型选择、灵敏度分析、稳健性检验、摘要写作、图表规划、图表配色、论文润色、论文审阅、终审、评委模拟、提交打包.
---

> **分发版路由说明**: 本分发包不含上游参考 `scibox-diagram` 与 `scibox-figure` (sci-box 上游无正式 LICENSE, 不得再分发; 二者**不是本包内的可用本地路径**, 需要时请自行从上游获取), 详见 VENDOR_NOTICES.md。
> 公开路由走本包实际随附的内容: 示意图用 `templates/figures/scripts/render_drawio_pack.py` / `render_diagram_pack.py`, 数据图用 `templates/figures/scripts/render_modeling_pack.py`, 答辩/展示 HTML 用随包的 `templates/figures/vendor/diagram-design/` (MIT); scibox 独有的高密度示意图模板与非库图型 (tpe_surface、cv_roc_ci 等) 在分发版不可用, 属能力留白而非等价替代。
> 另: `templates/figures/gallery/golden/` 的 4 张实战成品图 (Q1_C1_field / Q2_C1_stages / Q34_C1_gridconv / Q4_C2_routes) 属非公开项目材料, 分发版按默认选择规则隔离 (该目录保留 3 张模板样张); 识图先行纪律照旧, 见该目录 README 的分发版说明。

# mathmodel-studio — 数学建模 多竞赛通用 Skill (v3.1.0, 数模工坊 MathModel Studio)

## 版本与定位

**当前版本 v3.1.0**（2026-09-19）。历史与本次能力修复、精简及验证边界见 `CHANGELOG.md`；未经执行或仅局部核验的能力不得宣称完整通过。

把"3-4 天打 1 篇竞赛论文"拆成**五幕十阶段**（内部 stage -1~9，懒加载文件与 decision_log schema 不变）的可检查步骤，全程问答式：用户只回答编号问题，不敲命令、不编辑 JSON。六个一等竞赛：`huaweibei` 研究生赛 / `huashubei` 华数杯 / `cumcm` 国赛 / `mcm` 美赛 / `diangong` 电工杯 / `apmcm` 亚太杯；研究生赛、华数杯、国赛共享检索、模型接口与论文证据链，但题目、奖项、经验统计和案例身份严格隔离，**`huaweibei`（研究生赛）与 `huashubei`（华数杯）不得互换**。

**建模证据纪律**：进入 Stage 2/3/5/8 时按需读 `references/modeling_evidence_protocol.md`，机制案例另读 `references/mechanism_distillation.md`。历史范例中的固定变量数、强制凑三族、修饰词命名和默认复用不再作为质量要求；题面给定输入优先于跨问复用。

## 0. 读取与执行纪律（先读本节）

| 纪律 | 口径 |
|---|---|
| 非递归加载 | 只加载当前阶段、当前输出链或故障兜底**需要的章节**；被引文件里的引用一律不自动展开（**没有"权威源"例外**）——权威源也只在被本任务规则点到时才读，其余留作指针 |
| 不重复读 | 已加载文件不再整读；二次需要只取小节（grep / offset 定位） |
| 子代理最小规则 | 委派只给：必需文件清单 + 输出契约 + 验收命令；禁止"整个目录自己找"式派发 |
| 脚本摘要优先 | 先看摘要行与退出码；失败才展开完整日志，并把失败原文交给下一个处理者 |
| 按需依赖检查 | 执行前只核对**本次要用**的命令与文件（存在性 / `--help` / 字段名），不做全库预检 |
| 硬门不可削弱 | 六必停点、`check_gate.py`、图表硬门、数字冻结与回检、资格门、提交清单必须逐条通过；建议性检查（AI 味诊断、词频统计、视觉基准对照等）可标"未适用/未测"并写明理由，**不得虚标 pass** |

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

意图不清：直接给工作台菜单，让用户回复 `1-5`。

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

## 3. 六必停点（唯一登记路径 `decision_log.checkpoints`）

**必停点**（历史病根 = agent 自写自走、该问不问；已固化为"登记 + 程序门禁"）：**任何模式下都必须真问用户**（Claude Code 用 `AskUserQuestion`，Codex 用编号菜单）；条目形状固定四字段：

```json
{"status": "answered", "asked_at": "<ISO>", "answer": "<用户选择摘要>", "source": "chat"}
```

`source` 白名单只有 `chat`（主 agent 问答后写）与 `user_cli`（已归档薄执行器 CLI 写入）；缺失或非白名单值（model/llm/agent/auto）视为未答，`scripts/check_gate.py` 拦截。形状与扩展字段单点权威源 `references/workspace_protocol.md` §12。

| 必停点 | 触发时机 | 登记键 |
|---|---|---|
| 启动 5 问 | 完整流程启动时一次问齐（竞赛/题号/队员/截止/PDF） | `checkpoints.kickoff_5q` |
| 审题呈现确认 | Stage 2 四查呈现后、进入分解前 | `checkpoints.analysis_confirm` |
| 选择卡拍板 | Stage 3 人类拍板门（先亮短名单 + 候选档案） | `checkpoints.card_decision` |
| 每问图表菜单 | Stage 5 每个 Qi 验证通过后、生成图表前（D.1） | `checkpoints.figure_menu["Q<i>"]` |
| 每问 verdict | 每问 L1 评分产出 verdict 时**即问即登记** | `checkpoints.qi_verdict["Q<i>"]` |
| 每问选型确认 | Stage 5 每个 Qi 求解前（A0）；与 stage 3 一致时轻量确认，不一致或无记录必须出完整选择卡 | `checkpoints.per_qi_selection["Q<i>"]` |

**程序门禁**：阶段末尾跑 `python scripts/check_gate.py --gate <N>`（N=0-8）；阶段中途人工停点用 `--checkpoint <key>`（如 `figure_menu.Q1`），只查该停点登记、不查 scores。exit 0 放行；exit 1 拦截并输出缺失清单——按 verdict=block 同级处理（暂停 + 编号菜单：缺停点补问，缺评分先跑 L1 自评 + `score_artifact.py` 落盘）。门禁同时要求 stage N 合法评分记录（stage 5 双路径：`scores["5"]` 或覆盖全部 Qi 的 `scores["5_per_qi"]`，满足其一）。**没有跳过/绕过开关**；旧 state 无 `checkpoints`（schema 3.0）判 FAIL 属预期；语法错误 exit 2，业务放行/拦截只返回 0/1。

**宿主强制未启用时的口径**：本 skill 以 skill 身份安装、未注册插件 hook，门禁由 agent 在阶段末尾主动运行（协议要求，非物理拦截）；要物理拦截需在插件身份下注册 `PreToolUse` hook，或用提交期 `package_submission.py` 校验。

## 4. 状态持久化与恢复（核心约束）

- 每阶段开头 `Read cwd/state/decision_log.json` 核对 `current_stage`；结尾更新 stage 节点（核心决策 + 摒弃方案 + 评分）后才 `current_stage += 1`（先过 `check_gate.py --gate <N>`）。
- **恢复四步**（规则单点在 `references/workspace_protocol.md` §4，这里只留短提醒）：读 `cwd/state/decision_log.json` → `真源.md` 口径冻结单 + 修订记录末 5 行 → 冻结/运行清单检查 → 输出"当前阶段 / 已冻结项 / 待办 3 条"给用户确认。只读该节、不整读该文件、不读其余 stage 文件；**脚本按 `<skill>/scripts/` 检测**，缺依赖/json 缺失记 `未执行/缺依赖` 并如实报告（不得当作已核验通过，硬门不因跳过而放行）。"继续 stage N"再按 §9 加载。
- **局部任务不建 state**：只答概念、润色一段、审一张图不写 `decision_log.json`；确需落盘时说明"已/未写入 state"。
- **不可逆动作**（删 state、覆盖正文、批量移动文件、回退多阶段、清空结果目录）先经用户确认；默认新增备份或追加事件，不直接覆盖。
- 关键字段：root `competition` / `task_type` / `mode` / `interaction` / `checkpoints` / `current_stage` / `budget` / `events`；stage 5 扩展 `qi_count` / `qi_weights` / `qi_status`；scores 含 `weighted_mean` / `review_qis` / `refine_qis`；终稿链 `final_chain`（`tex` 默认 | `docx`）。模板 `templates/shared/decision_log.json`。

## 5. 流程编排与门禁

| 幕 | 步骤（stage） | 时长 |
|---|---|---|
| 一、备战与选题 | 赛前兵检 (-1) → 启动 (0) → 选题 (1) | 兵检 2-4h（赛前）+ 1h + 2-4h |
| 二、审题与选型 | 审题四查 (2) → 模型选型 (3) → 假设符号 (4) | 2-3h + 2-4h + 1h |
| 三、建模求解 | 子问循环 (5) → 稳健性 (6) | 6-12h × n + 2-3h |
| 四、论文成稿 | 模型评价 (7) → 写作组装 (8) | 1-2h + 12-30h |
| 五、终审提交 | 终审 (9) | 2-6h |

**质量门 1**（每步结束）：rubric 自评 + verdict，不过不推进。**质量门 2**（第五幕）：评委模拟器 panel + 校准。**跨幕回检**内嵌第三、四幕末尾，定向回滚不重做整幕。

verdict 优先级：`block`（high-severity，暂停请用户介入）> `pass_early`（min≥9 且 mean≥9）> `pass`（min≥7 且 mean≥8）> `pass_with_review`（stage 5 有 Qi 待复查）> `refine`（section-patch，iter cap 3）> `refine_partial`（只修失败 Qi）> `carryover`。`weighted_mean = Σ(s_i×w_i)/Σ(w_i)`，权重取 `config/dim_weights.json[<comp>][<task_type>]`（clamp [0.7, 1.5]）。三处定义（`feedback_layer1_critic.md` / `rubrics.md` / `score_artifact.py`）必须一致。

**迭代预算**：每阶段 refine ≤3 轮；跨阶段返工与并行重派设总预算，耗尽后不得静默继续——输出结构化 `decision_memo`（blocked_item / tried / best_so_far / options / recommendation）交用户编号决策（模板 `references/parallel_dispatch.md`）。验收"三选二"独立来源规则见 `references/workspace_protocol.md` §7。

**模式**：`fast`（≤50k，L1）/ `standard`（≤200k，L1+L2，默认）/ `championship`（≤500k，L1+L2+L3+L4+red-team）。剩余时间：>60h 或 24-60h → standard（最后 6h 升 championship）；6-24h → fast + championship 终审；<6h → 直接进 stage 9。`interaction` 正交：`detailed`（默认，必停点外关键自由参数也问）| `auto`（仅用户明确要求时开，**六必停点永远要问**）。

## 6. 输出链与呈现政策（跨阶段）

- **终稿链与按链终审**：`decision_log.final_chain` = `tex`（默认）| `docx`；写作全程只写 md 真源。`final_chain=docx` 时 tex 专属检查（Overfull 等）标"未适用"，改跑 `docx_number_recheck.py`，呈现验收对象是 docx 版 PDF。**换链须用户确认**（§7）。
- **md 真源与 Word 边界、图注/表注回源、题注字号与题式、数学字体正斜政策**：全部只在权威源里定稿——`references/docx_final_channel.md`（Word 白名单/禁区 + 回源）、`references/cn_presentation_spec.md` §1.5/§5.6（题注随模板、正斜二选一且"未拍板不做切换"）；本文件不重述口径。图内数学字体三态由调用方按用户政策显式传参（`figkit.apply_style(upright_math=True|False|None)`，**该函数不读 `decision_log`**）。
- **图表双分野**：数据图 = 代码生成 + 门禁（数字只取冻结结果，改图 = 改脚本重跑 `figqa.py --strict` + `figure_lint.py`）；示意图 = 草稿 + 可编辑源文件（drawio 优先）+ **人工精修回贴**，stage 8 只收录无 `.draft` 后缀版本；作战地图每篇 1 张必选。设计卡五要素/判据线纪律/配色语义见 `references/figure_skill_bridge.md`。
- **数字与引用终验**：图表与摘要主张回溯结果文件与冻结数字（`trace_claims.py --strict`、`claim_consistency_check.py --strict`、`freeze_numbers.py check`、`consistency_audit.py`、`ref_order_audit.py`）；**未测/未适用/未核验如实标注**（"未测"不得写成"已验证"），诚实声明进真源与 decision_log。
- **自包含与联网例外**：运行时不联网，唯一例外是 `literature_scout`（stage 1/3/5 挂点）；各竞赛经验统计与来源审计见 `competitions/<comp>/empirical_notes.md` + `source_manifest.json`（seed 降确定性）；资产按 LICENSE (MIT) 分发，`templates/figures/vendor/` 为上游副本（见 `templates/figures/vendor/VENDOR.md`）。

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

## 8. 路径解析（任何阶段必读）

| 类型 | 位置 | 例 |
|---|---|---|
| skill 内通用 | skill 根相对路径 | `references/stage_05_subproblem_loop.md`、`templates/shared/decision_log.json` |
| 竞赛特化 / 模板 | `competitions/<comp>/...`（按 `decision_log.competition` dispatch）、`templates/latex/<comp>/` | `competitions/cumcm/winning_patterns.md`、`templates/latex/cumcm/main.tex` |
| 用户产物 / state | 用户 `cwd/` 相对路径；`cwd/state/decision_log.json` 各 stage 必读必写 | `cwd/results/`、`cwd/figures/`、`cwd/paper_workspace/`；同目录 `frozen_numbers.json`、`evidence_ledger.json`、`skill_issues.md` |
| 环境变量 / skill 根 | `MATHMODEL_STATE_DIR`（兼容 `CUMCM_STATE_DIR`）/ `MATHMODEL_COMPETITION`；根路径唯一真源 `scripts/skill_paths.py`——按调用路径解析并打印当前根（安装位置、软链或 Junction 入口统一由它解析，文档不写死本机路径） | `python scripts/skill_paths.py` |

`<skill>` = skill 安装目录，`<cwd>` = 用户 cwd，`<comp>` = 当前竞赛（huaweibei | huashubei | cumcm | mcm | diangong | apmcm）。

## 9. 按 stage 加载（只加载当前阶段，切勿全读；细节与章节范围见 §2 对应套餐）

| stage | 文件 | 何时进入 |
|---|---|---|
| -1 | `references/stage_preseason.md` | 赛前兵检 → `state/preseason_report.json` |
| 0 | `references/workspace_protocol.md` §1/§2/§4/§11/§12 + `references/md_authoring_spec.md` | 工作区初始化与恢复（套餐 1） |
| 1 | `references/stage_01_problem_selection.md` + `competitions/<comp>/topic_specs.json` + `case_retrieval.md` | 选题比较（套餐 2） |
| 2 | `references/stage_02_analysis.md` + `references/modeling_norms.md` | 审题四查/分解/义务台账/图表规格冻结 |
| 3 | `references/stage_03_model_selection.md` + `references/model_catalog.md`（含 §12 失效边界）+ `references/knowledge_workflow.md` | 选型（套餐 3）；**禁止迁移历史数值** |
| 4 | `references/stage_04_foundation.md` + `templates/shared/notation_table.md` | 假设/符号/术语冻结 |
| 5 | `references/stage_05_subproblem_loop.md` + `references/modeling_evidence_protocol.md` | 子问循环（套餐 4）：A0→A/B/C/C.1→D/D.1→E/E2/E3→F/G/H |
| 6 | `references/stage_06_robustness.md` + `templates/shared/sensitivity_table.md` | 全局灵敏度/稳健性 |
| 7 | `references/stage_07_evaluation.md` | 模型评价与推广 |
| 8 | `references/stage_08_writing.md` + `<comp>/{winning_patterns, phrase_bank, abstract_template, paper_skeleton}.md` + `references/cn_presentation_spec.md` | 写作（套餐 5）；样张先行 + 终稿链选择见 §6 |
| 9 | `references/stage_09_review.md` + `competitions/<comp>/anti_patterns.md` + `rubric_overlay.json` | 终审提交（套餐 8） |

通用挂载（只在触发时读）：反馈层 `references/feedback_layer{1,2,3,4}_*.md`；harness `references/harness_compat.md`；派发前 `references/parallel_dispatch.md`（识图先行：**无视觉执行器不得自读图片**）；数据 `references/data_acquisition.md`；文献 `references/reference_skill_bridge.md`；配色 `references/color_typology.md`、令牌 `references/design_tokens.md`、选项卡 `references/decision_ui_map.md`、评分契约 `config/rating_contract.json`。

## 10. 竞赛专项加载（competition=X 时加件）

| 竞赛 | 按**当前 stage** 触发加件（不要整包同时加载） |
|---|---|
| huashubei 华数杯 | stage 0：`references/huashubei_battle_plan_72h.md`；stage 1：`references/huashubei_topic_decision.md`；stage 3/5：`competitions/huashubei/distilled_modeling.md`；stage 5/8：`references/huashubei_figure_pack.md`；stage 8：`competitions/huashubei/` 的 `winning_patterns.md` / `abstract_template.md` / `phrase_bank.md` / `paper_skeleton.md` / `empirical.json`；stage 9：`competitions/huashubei/anti_patterns.md` + `rubric_overlay.json`（6 维国一 overlay + 4 角色 panel） |
| huaweibei 研究生赛 | stage 0：`references/huaweibei_battle_plan_72h.md`（含 h48 硬冻结 + 独立验收三选二）；stage 1/3：`competitions/huaweibei/topic_specs.json` + `case_retrieval.md`；stage 3：`competitions/huaweibei/playbooks/` 命中域 + `competitions/huaweibei/papers/domain_index.md`（命中后按 paper_id 定向读 `competitions/huaweibei/papers/manual_paper_reviews.json`）；stage 4/8：`references/cross_competition_distillation.md`；stage 5/8：`competitions/huaweibei/distilled_modeling.md` + `distilled_figures.md`；stage 8：`writing_voice.md`（必载）+ `writing_playbook.md` + `writing_examples.md` + 该赛 abstract/phrase/papers 件；stage 9：先核 `current_rules.md` 日期戳，再用 `anti_patterns.md` + `rubric_overlay.json`（五角色 panel） |
| cumcm 国赛 | stage 1/3：`competitions/cumcm/topic_specs.json` + `case_retrieval.md`；stage 3：`competitions/cumcm/playbooks/` 命中域（先读其 README 域→文件映射）；stage 1/3/5：`competitions/cumcm/distilled_modeling.md`；stage 5/8：`competitions/cumcm/distilled_figures.md`；stage 8：`winning_patterns.md` / `abstract_template.md` / `phrase_bank.md` / `paper_skeleton.md`；stage 9：`anti_patterns.md` + `rubric_overlay.json`。页数口径见 `references/cn_presentation_spec.md` §1.6；旧辅助层已归档 `docs/legacy/cumcm/`（残值在 `phrase_bank.md` §13） |
| mcm 美赛 | stage 8：`competitions/mcm/memo_letter_guide.md` + `competitions/mcm/abstract_template.md` + `templates/latex/mcm/main.tex`；不适用 docx 中文终稿通道 |
| diangong / apmcm | 按所在 stage 读各自 `competitions/<comp>/` 对应件（topic_specs / abstract_template / phrase_bank / anti_patterns …）；基线 `seed v0.1` / `empirical_local_2024_2025`，输出标注 seed 并降低结论确定性 |

## 11. 反例黑名单

| 反模式 | 正确做法 |
|---|---|
| 让用户手敲命令或编辑 JSON | agent 自动读写文件，用户只回答编号问题或给路径 |
| 一次性读完 `references/`、`competitions/` | 进哪个 stage 读哪个，竞赛特化文件按需读 |
| 编造题面、数据、评审要求 | 缺资料标 pending，用假设表明确占位 |
| 局部任务顺手建/改 state | 只在用户明确进入完整流程时才写 state |
| 求解绕开选型（跳过选择卡或 A0） | 先出候选档案与选择卡，拍板后再求解 |
| block 后继续精修 / 必停点自问自答 | 暂停给 2-4 个编号选项；checkpoints 登记 + `check_gate.py` 放行 |
| 把 seed 当稳定经验 / 把"未测"写成"已验证" | 标注 seed 降确定性；未测/未适用如实标注 |

## 12. 治理与维护入口

- **一规则一家 + 判层必摘**：每个规则主题全库只有一个权威源，其余位置只写一行指针（R1-R14 对照表与"判层同改"清单见 `references/README.md`）；判"旧层/已归档"时同一改必须摘加载表、清零全库正面引用、残值迁移后再 `git mv` 进 `docs/legacy/`。
- **迁移规则能力矩阵**（旧主题 → 权威新路径/标题、已归档层与残值去向）见 `docs/maintenance_notes.md`——查旧写法先查矩阵，不复制整套旧文档。
- **历史与版本**：`CHANGELOG.md` 是历史唯一权威源（本文件与 README 不重述）；版本号五处同步门禁 `tests/test_version_sync.py`，死链回归 `tests/test_doc_links.py`。
