# 架构

## 运行结构

`SKILL.md` 负责意图、不可省略的约束、阶段索引。当前阶段 reference 负责步骤，领域 reference 负责特定决策。脚本执行确定性检查与转换；竞赛库和图表模板作为按需资源，不进入默认上下文。

```text
用户任务 -> SKILL 路由 -> 当前阶段 / 局部能力
                         | 附件检查 -> assets-1
                         | 小实验   -> experiments-1/2 -> comparison-1/2
                         | 结果出图 -> figure-candidates-1/2 -> gallery-1/2
                         v
                 既有 decision_log / evidence_ledger
                 run_manifest / 冻结数字 / 正文回检
```

三个新工具之间通过文件交换，不引入服务、数据库、注册中心或新的阶段机。比较工具只消费真实实验；图库只消费已生成图片。Agent 负责领域判断、调用现有库执行模型与绘图，工具负责结构、协议、来源、预算的可重复检查。

## 单一职责

| 内容 | 维护位置 |
|---|---|
| 必停点与阶段入口 | `SKILL.md` |
| 启动、套餐、故障、竞赛特化 | `references/workflow_entry_details.md`，按节加载 |
| 资产检查与边界 | `references/multimodal_assets.md` + `scripts/inspect_assets.py` |
| 小实验和比较 | `references/experiment_cycle.md` + `scripts/compare_experiments.py` |
| 多模态图与候选图库 | `references/result_gallery.md` + `scripts/build_result_gallery.py` |
| 冻结、运行追溯、数字注入 | 既有 `references/workspace_protocol.md` 和配套脚本 |
| 图表设计和正式质检 | 既有 `references/figure_skill_bridge.md` |

## 减重边界

显式组合入口：`figure_composition.py` 管局部样式、毫米画布与共享图例/色条；模板 draw_* 只绘制 caller-owned axes；旧包装器照旧保存。`export_revision` 独立新目录与完成标记，不改变 save_fig 旧失败语义。

比较器按 schema 路由 experiments-1 或按需加载 experiment_protocol_v2（experiments-2）；图库 v2 分离生命周期与去向，不修改 state。原图质量检查独立为 figure_export_quality，preview 不承担原图认证。A-F 范例和分层验收通过图表桥按需加载，不增加主入口默认引用树。

减少默认加载的字节、重复决策规则与不必要交互；不通过删除案例、模板或门禁缩小功能。专项引用仍保留，但不得在加载入口时递归展开。脚本按需导入可选库，新增媒体和科学读取器不进入全量 requirements 默认安装。

保留现有 state schema 与评分键，已有工作区不做整库迁移。再次移交Stage 3时按已有证据补齐缺失研究字段，未知仍为unknown，不重置已答checkpoint。新契约只在实际使用时生成，旧项目不需要补空清单。原始附件、模型求解和论文终稿继续受既有验证约束；新增工具的“元数据检查成功”或“推荐候选”不等于科学结论已验证。

## 验证范围

回归关注协议不一致、测试集误用、重复实验、证据漂移、损坏输入、缺依赖及图库排除。媒体/地理/科学后端分别依赖本机工具，未安装后端不宣称实测。绘图历史限制见 `docs/upgrade_acceptance.md`；v3.4验收范围见 `docs/release_3_4_review.md`。

## v3.4研究规则归属

Stage 3维护候选与选择范围；experiment_cycle维护预算、内部选型和公平实验；modeling_evidence_protocol维护定义、关键实现行为与主张边界。literature_scout统一各阶段研究profile与停止条件，reference_skill_bridge只管来源获取、真实性和引用格式；playbook只给条件性领域线索。调用者用指针，不复制配额或评分正文。

`fairness_comparison.by_subproblem`是可选范围说明，不参与新状态机；现有notes也可表达。机器门禁检查结构、最新verdict与可识别的本地证据路径，不自动证明模型充分优化、因果归因或目标正确率。Stage 3字段补记不等于证据升级。
