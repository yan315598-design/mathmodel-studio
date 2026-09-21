# references/ 治理规则（一规则一家 · Rule Ownership）

> v2.8.0 新增。本文件是防"skills 打架"的疫苗条款，源自三方审计
> （deepseek 硬数据 / GLM-5.3 规则归属地图 / GPT-5.6 对抗复审，2026-09-15）。
> 审计结论：同一规则主题被多文件各自立法、随后漂移成冲突（6 项硬冲突皆由此生），
> 而非字面重复。对策 = 每个规则主题指定唯一权威源，其余位置只写指针。

## 一、一规则一家（评审硬条款）

1. 每个规则主题**全库只允许一个权威源文件**（见下表）。新规则必须写进它的家；
   写进别处 = 评审打回。
2. 非权威源位置需要提及该规则时，只写**一行指针**（"XX 规则唯一权威源是 `<文件>`,
   此处不重述"），不复制数值口径或清单。
3. 数值口径（模板数、字数分位、页数区间、色值）尤其不得双份维护——
   数字在第二处出现的那一刻就开始漂移。

### 规则主题 → 唯一权威源对照表

| # | 主题 | 唯一权威源 | 其余各处 |
|---|---|---|---|
| R1 | 摘要结构/句式/填空 | `<comp>/abstract_template.md`（各赛独立） | stage_08 指针 |
| R1 | 摘要字数分位 | `<comp>/empirical.json` + `empirical_notes.md` | 不得硬编码 IQR |
| R1 | 摘要呈现验收（导语/加粗 6-12/关键词） | `cn_presentation_spec.md` §3 | abstract_template 一行指针 |
| R2 | 图题格式与图内纪律 | `cn_presentation_spec.md` §7 | bridge / stage_08 指针 |
| R2 | md 源题注/图写法 | `md_authoring_spec.md` §3 | 与 cn_spec §7 互相对齐引用 |
| R3 | 公式 md 源写法（编号/禁 \tag） | `md_authoring_spec.md` §1 | stage_08 示例遵守 |
| R3 | 公式呈现验收（居中/右顶格/超宽拆） | `cn_presentation_spec.md` §5 | — |
| R4 | 表格规范 | `cn_presentation_spec.md` §6 + `md_authoring_spec.md` 避免清单 | stage_08 示例标注指针 |
| R5 | 页数口径（22-25=正文+参考文献，附录不计） | `cn_presentation_spec.md` §1.6 | SKILL / paper_skeleton / stage_09 压成指针+一句 |
| R6 | 必停点定义与登记语义 | `SKILL.md` 必停点协议节（agent 可达性优先，不搬出） | stage 文件引用 |
| R6 | checkpoints 条目 JSON schema | `workspace_protocol.md` §12 | stage_05 只写指针 |
| R6 | 必停点程序语义 | `scripts/check_gate.py` | — |
| R7 | 色值（色板/NEUTRALS/示意图色族） | `color_typology.md` + `templates/figures/style/palettes.py` | design_tokens 删 NEUTRALS 副本 |
| R7 | 字阶/版式/间距令牌 | `design_tokens.md` | — |
| R8 | 图表路由（什么图走什么模板/vendor） | `figure_skill_bridge.md` 顶部总路由表 | SKILL.md 不写死模板数量 |
| R9 | 写作 voice 呈现密度 | `cn_presentation_spec.md` §8 | — |
| R9 | AI 痕迹清单 | `ai_flavor_removal.md` | — |
| R9 | huaweibei 写作语域 | `competitions/huaweibei/writing_voice.md` | — |
| R10 | 流程总览与按 stage 加载表 | `SKILL.md`（SSOT） | codex_practical_menu 同源注记；stage 文件 frontmatter 供机器校验 |
| R11 | 编号体系（图表公式 章节式 vs 全局） | `cn_presentation_spec.md` §4 + `md_authoring_spec.md` §4 | 默认全局连续 |
| R12 | 中文标点全角体系 | `cn_presentation_spec.md` §2 | abstract_template 等指针 |
| R13 | docx 终稿通道（冻结后 Word 终改协议） | `docx_final_channel.md`（v2.9.0） | workspace_protocol §3.1 只写例外指针；SKILL 入口路由 + stage 8 行各一指针 |
| R14 | 图叙事设计卡/判据线/对照构图/量化标签/示意图草稿通道 | `figure_skill_bridge.md` 图叙事章（v3.0.0） | stage_05 / stage_08 / cn_presentation_spec §7 / parallel_dispatch 挂接点 3.5 指针；配色语义（色与线型绑定）归 R7 的 `color_typology.md` 配色语义表；图题/注释预算/图宽呈现仍归 R2（`cn_presentation_spec.md` §7） |
| R15 | 附件读取与多模态元数据 | `multimodal_assets.md` + `scripts/inspect_assets.py` | Stage 2 指针 |
| R16 | 小实验、同口径模型比较、动态计划 | `experiment_cycle.md` + `scripts/compare_experiments.py` | Stage 2/3/5 指针 |
| R17 | 多类型图路由与候选图库 | `result_gallery.md` + `scripts/build_result_gallery.py` | 图表桥与 Stage 5 指针 |

| R18 | 候选研究、四轴证据与移交范围 | `stage_03_model_selection.md` | playbook仅给条件线索，选型评分见rubrics |
| R19 | 检索profile、阅读预算与停止条件 | `literature_scout.md` | 引用桥与阶段页只引用；真实性与格式归reference_skill_bridge |
| R20 | 定义、关键实现行为与主张边界 | `modeling_evidence_protocol.md` | Stage 3/5/6/8按需引用，不复制检查清单 |

## 二、判层必摘（"判而不摘"禁令）

任何文件被判"旧层/弃用/已归档"时，**同一个 PR 必须完成**：

1. 从 `SKILL.md` 加载表（通用加载 / 按 stage 表 / 竞赛专项加载）摘除该文件；
2. 摘除全库全部正面加载引用（grep 文件名确认零残留；CHANGELOG 历史叙述豁免）；
3. 有价值残值先迁移到权威源（登记迁出位置），再整体移出公开仓库并在维护者
   本地归档（原历史归档目录已于 v3.3.0 整体移出，保持证据链的方式改为本地留存）。

依据：2.7.0 前 `SKILL.md` stage 8 加载表仍在加载已被 README 判旧层的
distilled_structures/distilled_formats，"判而不摘"是字数/图题/编号三类冲突
至今仍会被 agent 读到的直接根因。

## 三、配套机制

- **版本同步门禁**: `tests/test_version_sync.py` 断言发版五处版本号一致
  （SKILL.md / CHANGELOG 首条 / README 徽章 / plugin.json×2）。
- **死链回归**: `tests/test_doc_links.py` 全库 .md 相对路径检查，防归档/移库后残留旧路径。
- **CHANGELOG 同步清单**: 每个 CHANGELOG 条目末尾必须列"本变更必须同改的文件"
  （模板见 CHANGELOG.md 顶部注释）。
