# 维护说明（docs/maintenance_notes.md）

> 维护期文档，**运行时不加载**（无任何 stage / 加载表引用它）。用途：查"旧写法现在去哪看"、查规则归属、
> 查入口任务的章节级加载套餐。改运行文档前先读本文件第 1、2 节。
> 历史叙述与版本事件仍以 `CHANGELOG.md` 为唯一权威源（本文件不复制历史条目）。

## 1. 规则归属速查（改文档前先认门）

| 主题 | 唯一权威源 | 常见误放位置 |
|---|---|---|
| 工作区/真源 SSOT/冻结与回源规则/`checkpoints` 条目形状 | `references/workspace_protocol.md` | stage 文件只写指针 |
| 中文竞赛呈现（版面/标点/摘要/公式/表格/图题/voice/终审 20 条） | `references/cn_presentation_spec.md` | abstract_template / stage_08 只写指针 |
| 图表路由、图叙事设计卡、判据线、示意图草稿通道 | `references/figure_skill_bridge.md` | `SKILL.md` 不写死模板数量 |
| docx 终稿通道（入口条件/白名单禁区/三步终检/回退） | `references/docx_final_channel.md` | workspace_protocol §3.1 只写例外指针 |
| AI 味诊断（词句十类 + 版式四类） | `references/ai_flavor_removal.md` | phrase_bank §14 只给替换建议 |
| 必停点定义与登记键 | `SKILL.md` 必停点协议节 | stage 文件引用，不重复定义 |
| 流程总览与加载表 / 任务加载套餐 | `SKILL.md` | 其它文档只写指针 |
| 历史与版本事件 | `CHANGELOG.md` | 本文件与 README 不复制条目 |
| 设计理由/历史机制说明 | `docs/legacy/architecture.md`（公开历史归档；维护期另有本地摘录，不随公开包发布） | 运行路径不承载 |

## 2. 迁移规则能力矩阵（旧主题 → 权威路径/标题）

查旧写法时先查本表：**旧写法在新版多半已被"指针化"或"归档"**，不要按旧文档整套复制。

| 旧主题 / 旧位置 | 现状 | 权威新路径（标题/章节） |
|---|---|---|
| `docs/legacy/architecture.md`（仓库级架构说明） | 已归档（v2.8.0）；设计理由仍以该归档为权威（2026-09-19 另摘出本地维护材料，不随公开包发布） | `docs/legacy/architecture.md`；运行文档不需要 |
| `references/workspace_protocol.md` §13「知识架构设计理由」 | 已迁出运行路径（2026-09-19） | 同上；原位仅留一行指针 |
| `docs/legacy/cumcm/distilled_structures.md`（章节结构提示） | 已废止并归档；残值保留 | `competitions/cumcm/phrase_bank.md` §13「章节模板卡」+ `references/stage_08_writing.md` 写作顺序 |
| `docs/legacy/cumcm/distilled_formats.md`（格式/编号示例） | 已废止并归档；残值保留 | `competitions/cumcm/phrase_bank.md` §13 + `references/cn_presentation_spec.md` §2.7/§5 |
| `docs/legacy/cumcm/distilled_phrases.md`（句式模板） | 已废止并归档 | `competitions/cumcm/phrase_bank.md` 各章 |
| `docs/legacy/runtime/`（薄执行器原型） | 已归档（v2.8.0），不在默认流程 | `SKILL.md` 必停点节"宿主强制未启用时的口径" |
| 图表"六类碰撞"（figqa 旧口径） | 已过期 | 七类（含 artist 遮挡）——`references/figure_skill_bridge.md` + `scripts/figqa.py` 模块头 |
| 数据图模板"17 件"、drawio"6 件" | 已过期（数字漂移，2026-09-19 修） | 25 件数据图 / 7 件 drawio——`references/figure_skill_bridge.md` 顶部总路由表 + `render_modeling_pack.py --list` |
| checkpoints 条目"5 个字段" | 已过期（2026-09-19 修） | **4 字段** `{status, asked_at, answer, source}`——`references/workspace_protocol.md` §12 |
| "题注文字可在 Word 里润色" | 已过期（与图注唯一来源冲突，2026-09-19 修） | **图注/表注措辞回源**——`references/docx_final_channel.md` 白名单/禁区表 + `references/workspace_protocol.md` §7 |
| "图表题 ≥ 五号"（统一数值） | 已过期 | **题注字号随当前链模板**——`references/cn_presentation_spec.md` §1.5 / §10 第 5 条 |
| 公式正斜"二选一"表述 | 已补严（2026-09-19） | 常规 GB 3102 惯例**不是"全斜"**；**未拍板时保持输入原状并提示**——`references/cn_presentation_spec.md` §5.6 + `figure_skill_bridge.md` 图叙事章 ④ |
| "AI 味/词频检查"被当作评分项 | 已纠偏 | 属**诊断建议**，不作 L1 硬评分——`references/ai_flavor_removal.md` 检查流程首段 + `config/rating_contract.json` `4_language_quality` |
| docx 期望层"每次重导出后必须手工重跑后处理" | 已过期 | 随 `export_final_docx.py --presentation` 默认执行（Step A-F，幂等）——`references/cn_presentation_spec.md` §5.1/§6.1/§7.6 |
| `scripts/skill_paths.py` 之前被描述为"两份独立安装并存" | 已纠偏（2026-09-19） | 按调用路径解析并打印当前根；本机 `.zcode/skills/mathmodel-studio` 是 Junction，指向 `.codex/skills/mathmodel-studio`（两条路径同源）——`SKILL.md` §8 |
| 版本历史叙述（SKILL.md / README 内的逐项清单） | 只留短标识 + 指针 | `CHANGELOG.md`（唯一权威源；未核验项如 D2/C7 不得在任何文档宣称完成） |

## 3. 加载落点

任务/场景的**章节级加载套餐只在 `SKILL.md` §2 维护**（单一来源，避免双份漂移）；本文件不复制套餐表。维护时要查"某任务该读哪节"直接看 `SKILL.md` §2 与 §9/§10。

## 4. 维护期规则

1. **判层必摘**（`references/README.md` §二）：判"旧层/弃用/已归档"时同一改必须摘加载表、grep 清零全库正面引用（`CHANGELOG.md` 历史叙述豁免）、残值先迁移再 `git mv` 进 `docs/legacy/`。
2. **禁止双份维护**：数值口径（模板数/字号/页数区间/色值/字段数）在第二处出现那一刻就开始漂移；第二处只写指针。
3. **硬门清单（不得削弱）**：六必停点 + `scripts/check_gate.py` + 图表硬门（`scripts/figqa.py --strict`、`scripts/figure_lint.py`）+ 数字冻结与回检（`scripts/freeze_numbers.py`、`scripts/docx_number_recheck.py`）+ 提交资格门与提交清单。建议性检查（AI 味诊断、词频统计、视觉基准对照、加粗/段长）允许标 `未适用`/`未测` 并写明理由，**不得假 pass**。
4. **不宣称未核验完成**：未跑过的脚本能力、未实测的链路、版本历史中未核验的条目（如 D2 导出时间戳、C7）不得写成"已完成/已验证"；脚本能力描述以 `--help` 与模块头实测为准。
5. **改后回归**：`tests/test_version_sync.py`（版本五处一致；`SKILL.md` 恰一处 `**当前版本 vX.Y.Z**`）、`tests/test_doc_links.py`（全库 .md 相对路径死链）。回归建议在**隔离副本**（复制到临时目录）运行，避免往源树写 `.pytest_cache` 等中间产物。

## 5. 变更留痕政策

- 维护期对历史条目的纠偏不改写 `CHANGELOG.md` 原文（历史叙述是审计线索），由维护方另行加"纠偏说明"。
- 本文件只记录**规则归属与迁移映射**；每次维护的逐项证据、字符/行数统计与七场景静态读取估算放在维护工作区报告，不写入运行文档。
