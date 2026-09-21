---
name: mathmodel-studio
description: 数学建模竞赛助手：审题、附件检查、模型选型与实验、求解验证、科研绘图、论文整理和提交检查。支持研究生赛、国赛、华数杯、MCM/ICM、电工杯和亚太杯；也可只处理已有题目、结果或论文的局部任务。
---

# MathModel Studio

**当前版本 v3.4.0**。完整流程或局部任务均可；只加载当前工作需要的参考，不递归展开引用。

## 1. 任务路由与 Quick Start

先识别用户要完成的交付物。已明确任务就直接进入对应入口，不重复展示菜单、不重复询问已知信息。意图不清才使用 `references/codex_practical_menu.md`。

| 请求 | 读取与动作 |
|---|---|
| 开始完整建模 | `references/workflow_entry_details.md` Quick Start：收集竞赛、题号、队员、截止时间、题目路径；按已有回答初始化或恢复 state |
| 附件识别、视频、音频、地图、点云 | `references/multimodal_assets.md`；先检查元数据和依赖，再按需分析 |
| 选题 | Stage 1；竞赛题型与检索按 `references/workflow_entry_details.md` 竞赛专项 |
| 模型建议 | Stage 3 选择卡；仅建议时不运行实验 |
| 小实验、模型比较、直接求解 | `references/experiment_cycle.md`；明确执行请求时先做有预算的小实验，正式求解仍过选择卡与 A0 |
| 画图、算法结构、物理机理、综合图 | `references/figure_skill_bridge.md`；多类型或备选图库加 `references/result_gallery.md` |
| 写作、摘要、润色 | Stage 8 的对应小节；局部任务不启动完整流程 |
| Word 终稿 | `references/docx_final_channel.md`；冻结后专用 |
| 终审、提交 | Stage 9；检查随最终输出链选择 |
| 继续、看进度 | `references/workspace_protocol.md` §4；报告当前进度、缺口和下一步 |

## 2. 最小执行约束

- 用户产物位于 `<cwd>`；技能资源位于 `<skill>`。根路径由 `scripts/skill_paths.py` 解析，环境变量沿用 `MATHMODEL_STATE_DIR` / `MATHMODEL_COMPETITION`。
- 只在完整流程中维护 `state/decision_log.json`。局部任务可产生附件清单、实验报告或图，但不顺手创建完整流程 state。
- 当前阶段开始读 state；末尾先评分、过 `scripts/check_gate.py --gate N`，再更新阶段。恢复、数字冻结、改源和级联失效按 `references/workspace_protocol.md` 对应章节。
- 题面与附件优先。历史案例只迁移结构与验证方法，不迁移数值。`huaweibei` 研究生赛与 `huashubei` 华数杯严格隔离。
- 先探索和基线，再完善模型与图型；探索产物不能直接充当正式结论。正式数字继续走冻结、运行清单和主张回检。
- 工具只检查本次需要的依赖；缺依赖记为缺失，不自动安装全部科学计算或媒体库。联网获取按 `references/data_acquisition.md`，文献按 `references/literature_scout.md`；离线材料不足时如实说明。
- 不编造数据、用户回答、实验结果或验收状态。失败先读摘要，必要时展开日志；有预算地修复，不能解决则交代缺口。
- 首轮正式图由 Agent 设计、渲染、检查与精修；示意图保留可编辑源，数据图来自真实结果。分层验收按图表桥；终稿只收已验收成品。
- 分发许可与不可用上游能力见 `VENDOR_NOTICES.md`。不把未随包提供的模板称作本地能力。

## 3. 必停点协议

完整流程保留六类决策及程序门禁；用户已有明确回答可直接登记，不二次确认。没有回答不得自写自走。已授权的小实验不等于正式主模型拍板。

| 时机 | `checkpoints` 登记键 |
|---|---|
| 启动信息齐备 | `kickoff_5q` |
| 审题呈现后 | `analysis_confirm` |
| 主模型选择卡 | `card_decision` |
| 每问正式求解前 A0 | `per_qi_selection.Qi` |
| 每问正式出图前 D.1 | `figure_menu.Qi` |
| 每问评分 verdict | `qi_verdict.Qi` |

条目形状为 `status / asked_at / answer / source`；schema 唯一来源是 `references/workspace_protocol.md` §12。`source` 仅接受真实对话 `chat` 或 `user_cli`。Codex 使用当前宿主支持的交互工具；没有时用简短编号选择，不让用户编辑 JSON。

`check_gate.py --checkpoint <key>` 核对单项，`--gate <N>` 检查阶段评分与停点；exit 0 放行、1 拦截、2 参数错误。Stage 5 保留整体评分或全部 Qi 评分两条路径。作为普通 skill 时由 agent 主动运行，不能宣称存在宿主物理拦截。

## 4. 按 Stage 加载

只读取当前阶段；具体任务套餐、章节定位和竞赛加件见 `references/workflow_entry_details.md` 对应节，不整本加载。

| Stage | 入口 |
|---|---|
| -1 赛前 | `references/stage_preseason.md` |
| 0 启动 | `references/stage_00_kickoff.md`；工作区协议 §1/§2/§4 |
| 1 选题 | `references/stage_01_problem_selection.md` |
| 2 审题 | `references/stage_02_analysis.md`；附件按需检查 |
| 3 选型 | `references/stage_03_model_selection.md`；模型目录只读命中域 |
| 4 假设符号 | `references/stage_04_foundation.md` |
| 5 逐问求解 | `references/stage_05_subproblem_loop.md`；实验、验证、出图、草稿闭环 |
| 6 稳健性 | `references/stage_06_robustness.md` |
| 7 评价 | `references/stage_07_evaluation.md` |
| 8 写作 | `references/stage_08_writing.md`；竞赛模板与呈现规范按节加载 |
| 9 终审 | `references/stage_09_review.md`；按最终输出链验收 |

## 5. 评分、输出与维护

评分阈值唯一来源为 `references/rubrics.md`，执行由 `scripts/score_artifact.py` 负责；每阶段 refine 最多三轮，超过预算输出已尝试方案、当前最好结果和待决策项。模式与时间预算见 `references/workflow_entry_details.md` §5，只在需要时加载反馈层。

论文以 Markdown 真源维护；`final_chain=tex|docx`，换链需用户明确选择。进入写作或改数时读取工作区协议 §5/§6/§9/§10，保留冻结、主张追溯和终稿回检；各链不适用的检查标注未适用。

维护规则归属见 `references/README.md`；架构见 `ARCHITECTURE.md`；版本历史见 `CHANGELOG.md`。新能力优先复用现有脚本和按需 reference，不复制整套阶段或另建 state 引擎。改路由须核对调用者，改接口须验证对应行为。
