---
name: mathmodel-studio
description: 数学建模竞赛全流程助手。从选题、审题、建模、求解、验算，到写论文、画图、模拟评审、打包提交，按阶段带你走完一篇可提交的竞赛论文。支持华为杯研究生赛、CUMCM 国赛、华数杯、MCM/ICM 美赛、电工杯、APMCM 亚太杯。内置从历年优秀论文提炼的建模经验库和分题型写作范式；图表统一配色、出图自动质检；论文里每个数字都可回溯；提交前有评委模拟终审。全程问答式，用户只需选编号。Use when the user says 建模、数模、开始建模、数学建模、华为杯、研究生赛、研究生数学建模竞赛、华数杯、CUMCM、国赛、MCM、ICM、美赛、电工杯、APMCM、亚太杯、选题、相似题、模型选择、灵敏度分析、稳健性检验、摘要写作、图表规划、图表配色、论文润色、论文审阅、终审、评委模拟、提交打包.
---

# mathmodel-studio — 数学建模 多竞赛通用 Skill (v2.5.0, 数模工坊 MathModel Studio)

## 版本与总述

**当前版本 v2.5.0**（2026-09-10）。本版做了三件事：① 给华为杯三个常考领域（信号诊断、空间几何、调度优化）各写了一份"高手动作手册"——写清普通做法在哪失效、优秀论文补了什么机制、什么情况下不适用，每条都标证据来源；② 33 篇深读论文支持按领域快速检索；③ 图表规范对齐正式论文：图名和结论写在图注里，不烧进图片本身，并有自动检查把关。上一版 v2.4.0（2026-09-09）主打建模证据纪律与必停点门禁。完整历史见 `CHANGELOG.md`。

建模证据纪律（现行规则）：进入 Stage 2/3/5/8 时按需读取 `references/modeling_evidence_protocol.md`，机制案例另读 `references/mechanism_distillation.md`。历史范例中的固定变量数、强制凑三族、修饰词命名和默认复用，不再作为质量要求；题面给定输入优先于跨问复用。

流程分五幕、共十个阶段（-1~9），把"3-4 天打 1 篇竞赛论文"变成可检查的步骤，全程问答式——用户只需回答编号问题，不必手敲命令。每阶段产出经过自评打分和局部精修，终局由多评委模拟评审把关。六个竞赛分支中，研究生赛、华数杯和国赛共享检索、模型接口与论文证据链，但题目、奖项、经验统计和案例身份严格隔离。

图表能力速览：自写模板 27 件（数据图 17 + 示意图 4 + 可编辑 drawio 6），统一色板，出图自动过质量检查——文字重叠越界直接报错，图内不放图名（图名写图注）。复杂多面板主图、物理场图、网络流图、TikZ 框架图由内嵌开源图表库补齐，路由细则见 `references/figure_skill_bridge.md`。

---

## Codex 编号菜单协议

Codex CLI / Codex app 通常不会弹出 Claude Code 的 `AskUserQuestion` 选择界面。运行在 Codex 时, 不等待、不承诺弹窗 UI; 直接用 Markdown 编号菜单完成选择。

固定规则:
- 离散选择必须给 `1)` 到最多 `5)` 的编号菜单。
- 主竞赛菜单固定为 `1) huaweibei 研究生赛  2) huashubei 华数杯  3) cumcm 国赛  4) 其他竞赛  5) 让我决定`；选择 4 后再选 mcm / diangong / apmcm。上下文出现“华为杯/研究生赛”时默认 `huaweibei`，出现“华数杯”时默认 `huashubei`。
- 题号、模型、verdict、是否进入下一阶段等选择都沿用编号菜单。
- 自由文本只问短输入, 例如队员分工、截止时间、题目 PDF 路径。
- 用户回复数字后, agent 自动写入 `cwd/state/decision_log.json` 并继续下一步; 不要求用户手写 JSON, 不二次确认。

Codex 菜单格式:

```text
【需要你选择: <一句话标题>】

  1) <选项 A> — <一句话解释>
  2) <选项 B> — <一句话解释>
  3) <选项 C> — <一句话解释>
  4) <选项 D> — <一句话解释>
  5) 让我决定 — <推荐项和原因>

回复数字 (1-5) 或直接告诉我你的选择。
```

---

## Codex 实战入口路由

当用户在 Codex 中用自然语言召唤本 skill, 先按意图路由, 不必强行从 Stage 0 开始。

| 用户说法 | 入口 | 首要动作 |
|---|---|---|
| "开始建模" / "我要打国赛/研究生赛/华数杯" | 工作台菜单 | 先给 `references/codex_practical_menu.md` 的一屏式菜单 |
| "华为杯" / "研究生赛" / "研赛" | **研究生赛专项** | competition=`huaweibei`; 加载跨赛共用层与 `competitions/huaweibei/` 独立分支 + `references/huaweibei_battle_plan_72h.md` 作战表 |
| "华数杯" / "我要打华数杯" / "华数杯国一" | **华数杯专项** | 加载 `references/huashubei_battle_plan_72h.md`, competition=huashubei, 国一标准 |
| "比较 A/B/C 题" / "帮我选题" / "华数杯选哪题" | Stage 1 | 加载 `topic_specs.json`; **huashubei 额外加载 `references/huashubei_topic_decision.md`** |
| "写摘要" / "写华数杯摘要" / "写亚太杯摘要" | Stage 8 局部写作 | 加载对应竞赛 `abstract_template.md` + `phrase_bank.md` |
| "写问题分析/模型段/结果解释/图表说明" | Stage 8 局部写作 | 只生成对应章节, 不改 state, 除非用户要求进入完整流程 |
| "画图/生成图/美化图/规划图表/终审图表" | 图表桥接 | 加载 `references/figure_skill_bridge.md`（配色规范：`references/color_typology.md` + 设计令牌宪法 `references/design_tokens.md`; 1.4.0 起总路由表在桥接文件顶部）; 论文示意图高密度交付默认走 `templates/figures/vendor/scibox-diagram/`（开源分发版无 scibox-*, 自动降级为自写 drawio/matplotlib 模板, 见桥接文件"开源分发版注意"）, 轻量快速路径用自写 drawio 模板 `render_drawio_pack.py --list`, 示意图配色默认走 `DIAGRAM_FAMILIES` 色族（与数据图表色板分离, 见 `color_typology.md` §2.4）; 复杂多面板主图/物理场图/网络流图/TikZ 框架图走 `vendor/icarus-figures/`（v2.3.0, 约束见 VENDOR.md 第 6 条）; **huashubei 额外加载 `references/huashubei_figure_pack.md`** |
| "终审论文" / "最后 6 小时检查" | Stage 9 | 进入极速终审路径, 优先查摘要定量结果、图表解释、符号一致、结论对应题问 |
| "继续 stage N" / "看进度" | 恢复 state | 读 `cwd/state/decision_log.json`, 加载对应 stage |

如果用户意图不清, Codex 直接给工作台菜单, 让用户回复 `1-5`。

---

## 触发与首要动作

当用户提到数学建模竞赛、选题、建模、求解、灵敏度、论文、摘要、终审、`$mathmodel-studio`、"开始建模"、"打国赛/美赛/电工杯/亚太杯"、"APMCM"、"亚太赛"时，立即启用本 skill。

首要动作固定为:
1. 用不超过 50 字说明已启动多竞赛 5 幕 10 步问答式流程。
2. 先做实战入口路由；若是局部写作/终审/选题比较, 直接进入对应入口。
3. 若要完整流程, 检查 `<cwd>/state/decision_log.json` 是否存在。
4. 若存在，先读 `competition`、`current_stage`、`mode` 并恢复；若不存在，Codex 直接输出工作台菜单并一次性问 5 个启动问题。
5. 只加载当前阶段需要的 reference，不一次性读完整资料库。

如果用户只想问概念、改一段论文或审一张图表，不启动完整五幕流程；直接完成该小任务，并说明未写入 state。

---

## 多 Runtime 入口

兼容 skills 标准的运行环境优先按 skill 目录发现本文件:

- 用户级安装: `$HOME/.agents/skills/mathmodel-studio/`
- 项目级安装: `<repo>/.agents/skills/mathmodel-studio/`
- UI 元数据: `agents/openai.yaml`
- 插件分发元数据: `.codex-plugin/plugin.json` + `skills/mathmodel-studio/SKILL.md` shim
- 项目指导: `AGENTS.md` 仍可作为 repo / workspace 级 instructions, 但不是唯一入口

当 skill 已安装后, 用户可直接说"开始建模"或显式说"使用 `$mathmodel-studio` 开始建模"。

---

## Harness 兼容 (Claude Code / Codex)

本 skill v1.0.0 以多 runtime skills 标准为一等入口, 同时保持 harness-agnostic 设计:

| harness | 入口文件 | 用户交互工具 | 状态文件 |
|---------|---------|-------------|---------|
| Claude Code | `SKILL.md` (本文件) | `AskUserQuestion` 工具 | `cwd/state/decision_log.json` |
| Codex CLI / Codex app | skill 目录中的 `SKILL.md` + 可选 `AGENTS.md` | markdown 编号列表 | 同上 (**互通**) |

跨 harness 互通: day 1 用 Codex 跑 stage 0-2, day 2 切回 Claude Code 接着 stage 3+, 状态完全保留。详见 `references/harness_compat.md`。

---

## 问答式优先 (Friendly Mode)

**核心原则**: 用户只需回答**编号问题**, 不应被要求手敲 bash / python / json。

- 离散选项 (选竞赛 / 选题 / 选模型 / verdict 决策) → **必须**用问答式
- 自由文本 (PDF 路径 / 截止时间) → 单行回复
- 状态读写 (decision_log.json) → agent 自动完成
- 每个 stage 的关键决策点都有 "让我决定 (推荐 X)" 兜底选项, 用户无脑选 4 也能跑通

Claude Code: 用 `AskUserQuestion` 工具; Codex: 用 markdown 编号列表 (最多 1-5, 含兜底)。两者语义等价, 见 `references/harness_compat.md` §1。

**交互密度 `interaction` (v2.3.0)**: decision_log 新增正交字段 `interaction`，取值 `"detailed"`（默认）| `"auto"`。detailed 下必停点之外的**关键自由参数**（假设取舍、图表风格细节、章节侧重）也要问；auto 仅当用户明确说"自动模式 / 少问点 / 你自己定"时开启（写入 `decision_log.interaction`），且只减少必停点之外的细节提问密度——**五个必停点永远要问**。注意与 `mode`（fast / standard / championship）的区分：`mode` 管 token 档位与反馈深度，`interaction` 管提问密度，两者正交、不得混用、不得互相覆盖。

---

## 必停点协议 (v2.3.0)

2025 华为杯 F 题实测病根：agent 全程自写自走，设计的必停点全部未问。本节把必停点从"约定"升级为"登记 + 程序门禁"。

**五个必停点**——任何模式下都必须**真问用户**（Claude Code 用 `AskUserQuestion`；Codex 用编号菜单），**唯一登记路径是 `decision_log.checkpoints`**，登记条目形如 `{"status": "answered", "asked_at": "<ISO>", "answer": "<用户选择摘要>", "source": "chat"}`（主 agent 流程经用户问答后由 agent 写入，`source` 固定为 `"chat"`；runtime 薄执行器的 trusted 写入是 CLI `answer` 命令，`source` 为 `"user_cli"`）。**`source` 缺失或非 `chat`/`user_cli` 的值（model/llm/agent/auto 等）一律视为未答，`check_gate.py` 拦截**：

| 必停点 | 触发时机 | 登记键 | 呈现方式 |
|---|---|---|---|
| 启动 5 问 | 完整流程启动时一次性 5 问（竞赛/题号/队员/截止/PDF） | `checkpoints.kickoff_5q` | AskUserQuestion 或 Codex 编号菜单 |
| 审题呈现确认 | Stage 2 审题门四查呈现后、进入分解前 | `checkpoints.analysis_confirm` | 同上 |
| 选择卡拍板 | Stage 3 选择卡人类拍板门（先亮短名单+候选档案，用户拍板） | `checkpoints.card_decision` | 同上 |
| 每问图表菜单 | Stage 5 每个 Qi 验证通过后、生成图表前（见 `references/stage_05_subproblem_loop.md`） | `checkpoints.figure_menu["Q<i>"]` | 同上 |
| 每问 verdict | Stage 5 每个 Qi 的 per-Qi L1 评分产出 verdict 时**即问即登记**该问条目（refine_partial 时明确问修哪问）；聚合整体决策登记进 `stages["5"]` 既有字段，不复制进 qi_verdict | `checkpoints.qi_verdict["Q<i>"]` | 同上 |

**程序门禁**: stage 推进前必须跑 `python scripts/check_gate.py --gate <N>`（N 为当前 stage，0-8；`--gate N` 只在阶段末尾退出条件处跑，阶段中途的人工停点用 `--checkpoint <key>` 只查该必停点登记、不查 scores）。exit 0 放行；exit 1 拦截并输出缺失项中文清单——与 verdict=block 同级处理：**暂停 + 编号菜单**，缺必停点就补问，缺评分落盘就先跑 rubric L1 自评 + `score_artifact.py`。门禁同时强制 `scores` 里存在 stage N 的合法评分记录（E 合并；stage 5 双路径：`scores["5"]` stage-level 或 `scores["5_per_qi"]` 覆盖全部 Qi，满足其一即可），L1 评分一次没落盘即拦截。**没有跳过/绕过开关**；旧 state 无 `checkpoints` 字段（schema 3.0）时判 FAIL 属预期行为，补走必停点问答即可。CLI 参数语法错误为 argparse 标准 exit 2，业务放行/拦截一律只返回 0/1。


---

## 路径解析协议 (任何阶段必读)

| 类型 | 位置 | 例 |
|------|------|-----|
| skill 内通用 | skill 根目录的相对路径 | `references/stage_05_subproblem_loop.md`, `templates/shared/decision_log.json` |
| **竞赛特化** | `competitions/<comp>/...` 按 decision_log.competition dispatch | `competitions/cumcm/winning_patterns.md`, `competitions/mcm/abstract_template.md` |
| **LaTeX 模板** | `templates/latex/<comp>/` | `templates/latex/cumcm/main.tex`, `templates/latex/mcm/main.tex` |
| 用户产物 | 用户 `cwd/` 相对路径 | `cwd/state/`, `cwd/results/`, `cwd/figures/`, `cwd/paper_workspace/` |
| state 持久化 | `cwd/state/decision_log.json` | 各 stage 必读必写 |
| 环境变量 | `MATHMODEL_STATE_DIR` (兼容 `CUMCM_STATE_DIR`) / `MATHMODEL_COMPETITION` 可覆盖 | scripts 用此变量 |

约定: `<skill>/` = skill 安装目录, `<cwd>/` = 用户 cwd, `<comp>/` = 当前竞赛 (`huaweibei` | `huashubei` | `cumcm` | `mcm` | `diangong` | `apmcm`)。其中 `huaweibei` 是研究生赛，不能与 `huashubei` 华数杯互换。

---

## Quick Start (用户首次说"开始建模")

**🔴 CHECKPOINT · 启动写入前确认**: 只有在用户明确要进入完整工作流时，才创建或修改 `cwd/state/decision_log.json`。如果用户只是咨询、润色或局部审稿，不写 state。

Codex 首屏优先加载 `references/codex_practical_menu.md` 的"比赛工作台菜单"。用户回复:
- `1` → 完整 5 幕 10 步流程, 继续问竞赛/题号/队员/截止/PDF。
- `2` → 只做 A/B/C 题比较, 进入 Stage 1。
- `3` → 局部写作, 进入 Stage 8 写作菜单。
- `4` → 终审论文, 进入 Stage 9。
- `5` → 读取已有 state, 恢复当前阶段。

```
1. 一段话介绍 (≤50 字): "启动数学建模工作流, 5 幕 10 步 + 多竞赛, 全程问答式."

2. 一次性 5 问 (Claude Code: AskUserQuestion 单条消息; Codex: 一条消息内给首屏 5 项, 其中离散项用编号菜单):
   - 竞赛 (huaweibei 研究生赛 / huashubei 华数杯 / cumcm 国赛 / mcm 美赛 / diangong 电工杯 / apmcm 亚太杯中文赛；按用户上下文选择，否则默认 cumcm)
   - 题号 (依竞赛: huaweibei A-F，且字母不固定映射题型 / huashubei A-C / cumcm A-E / mcm A-F / diangong A-B / apmcm A-C; "未公布"亦可)
   - 队员数 + 各人擅长 (建模/编程/写作)
   - 截止时间 (ISO 字符串或 "距现在 X 小时")
   - 题目 PDF 路径 ("未公布"亦可)

3. 自动初始化 (agent 自动完成, 不要让用户编辑 json):
   - 不存在 cwd/state/decision_log.json → cp <skill>/templates/shared/decision_log.json
   - 写入 decision_log.competition = <选定竞赛>
   - 已存在 → 读 current_stage 字段决定恢复点

4. 加载 competitions/<comp>/winning_patterns.md 一次 (建立基线), 后续不再读

5. 进入 Stage 0 (references/stage_00_kickoff.md), 不重复问已问过的问题
```

**已有 state 触发** (用户中途回到 skill):
```
1. 读 cwd/state/decision_log.json 的 competition 与 current_stage
2. 加载对应 stage_NN.md (按需结合 competitions/<comp>/* 内容)
3. 不重复读 winning_patterns
```

---

## 失败兜底协议

| 触发条件 | 一线处理 | 仍失败兜底 |
|---|---|---|
| 题目 PDF 路径不存在或打不开 | 请用户重新给路径；若题目未公布，记录为 `problem_pdf="pending"` | 用题号和已知竞赛规则进入 Stage 0，不编造题面 |
| `decision_log.json` 不存在 | 从 `templates/shared/decision_log.json` 复制并写入 5 个启动答案 | 模板也找不到时，只在对话中维护临时状态，并提示 state 未落盘 |
| `decision_log.json` 损坏或字段缺失 | 先备份为 `decision_log.bak.<timestamp>.json`，再用模板补齐缺字段 | 不能备份时暂停，展示损坏位置，请用户确认是否重建 |
| competition 缺失或不合法 | 用主菜单选择 huaweibei / huashubei / cumcm / 其他竞赛 | 按上下文推断（华为杯/研究生赛→huaweibei，华数杯→huashubei），否则默认 cumcm，并在 state events 写明原因 |
| 当前 stage reference 找不到 | 回到流程总览的五幕索引，加载相邻阶段和 `rubrics.md` 的通用规则 | 暂停该阶段，说明缺失文件，不跳过关键评审 |
| 评分脚本运行失败 | 读取报错，先检查输入 JSON、Python 环境和路径 | 改用 rubric 手工评分，并在结果里标注 `manual_fallback` |
| LaTeX 编译失败 | 定位首个报错，优先修模板变量、图片路径、中文编译器 | 输出可提交的 markdown/tex 草稿，说明 PDF 未生成 |
| token 超预算 | 降级 mode，并只保留阶段摘要、关键数据和文件路径 | 仍超预算时暂停长文生成，先让用户确认优先完成的章节 |

---

## 六个一等竞赛 × 三模式矩阵

时长 / 语言 / 模板 / 数据状态 由 competition 决定; token 预算 / 反馈深度由 mode 决定。两者**正交组合**。

| Competition | 时长 | 语言 | LaTeX | 子问数 IQR | 数据状态 |
|---|---|---|---|---|---|
| **huaweibei** | 100h (2026 通知口径, 赛前以官方通知复核) | 中文 | xelatex / ctex | 按当年题面 | **empirical_local_2021_2025（30题+190篇；33篇深读: 12篇2021提名+21篇2025优秀选）** |
| **huashubei** | 72h | 中文 | xelatex / ctex | [3, 5] | **empirical_local_6years (6届18题+18篇优秀论文, 国一标准蒸馏)** |
| cumcm | 72h | 中文 | xelatex / ctexart (自写) | [3, 5] | verified (33 篇论文 + 25 个案例) |
| mcm | 96h | English | pdflatex / article | [3, 6] | seed v0.1 |
| diangong | 72h | 中文 | xelatex / ctex | [6, 8] | seed v0.1 |
| apmcm | 72h | 中文 | xelatex / ctex | [3, 5] | empirical_local_2024_2025 (赛题6份+优秀论文12篇) |

**华数杯专项说明 (0.7.0)**: huashubei 是 0.7.0 重点升级的一等竞赛, 有完整经验库 (`competitions/huashubei/` 14 文件) + 专项工作流三件套 (选题决策/图表包/72h时间表), 数据基线最完整 (6 届 18 题 18 篇)。目标定位: 国家级一等奖。

| Mode | Token | 反馈层 | 用途 |
|---|---|---|---|
| fast | ≤ 50k | L1 单次 | 选题试跑 / sanity check |
| standard | ≤ 200k | L1+L2 | 默认主流程 |
| championship | ≤ 500k | L1+L2+L3+L4 + red-team | 提交前最后冲刺 |

模式自动推荐 (按距 deadline 剩余):
- > 60h: standard (最后 6h 升 championship)
- 24-60h: standard
- 6-24h: fast 关键阶段 + championship 终审
- < 6h: 直接进 stage 9 (championship)

---

## 流程总览：5 幕 10 步 + 2 道质量门

**对用户呈现为五幕**；内部实现仍按 stage -1~9 懒加载文件组织，stage 编号不变（decision_log schema、脚本、测试全部兼容）。

| 幕 | 步骤 (stage) | 干什么 | 时长 |
|---|---|---|---|
| 一、备战与选题 | 赛前兵检 (-1) → 启动 (0) → 选题 (1) | 模板预编译与 solver 冒烟；工作区初始化；多题对比定一题 | 兵检 2-4h (赛前) + 1h + 2-4h |
| 二、审题与选型 | 审题四查 (2) → 模型选型 (3) → 假设符号 (4) | 边界/权利/目标/假设四查防读错题 + 图表规格冻结；短名单带候选档案比较拍板；假设/符号/术语冻结 | 2-3h + 2-4h + 1h |
| 三、建模求解 | 子问循环 (5) → 稳健性 (6) | 每问 A-H 步求解，验证后立即写章节草稿卡（E2 write-as-you-solve）；全局灵敏度/稳健性 | 6-12h × n + 2-3h |
| 四、论文成稿 | 模型评价 (7) → 写作组装 (8) | 优缺点与推广；草稿卡组装成正文 + 摘要三遍制 | 1-2h + 12-30h |
| 五、终审提交 | 终审 (9) | 评委模拟器 panel：资格门 + 扣分制 + 校准锚；一致性审计与打包 | 2-6h |

**质量门 1**（每步结束，原 L1）：rubric 自评 + verdict 判定，不过不推进。**质量门 2**（第五幕，原 L3+L4）：评委模拟器多席位 panel + 校准。**跨幕回检**（原 L2）内嵌在第三、四幕末尾，定向回滚不重做整幕。

各阶段细节（reference / 反馈 / 竞赛差异点）见对应 `references/stage_NN_*.md`；差异速查：题号体系（huaweibei A-F 不映射题型 / huashubei A-C / cumcm A-E / mcm A-F / diangong A-B / apmcm A-C）、时长语言编译器由竞赛决定、stage 5 子问数与 per-Qi 加权聚合、stage 8 摘要类型（五段 / 1-page+Letter / 四段）。

---

## 加载协议 (节省 token 的关键)

**只在进入阶段 N 时加载** `references/stage_NN_*.md`。**切勿**一次性全读。

每阶段通用:
- 每阶段开头: `cwd/state/decision_log.json` 必读
- 每阶段结尾: `cwd/state/decision_log.json` 必写 (核心决策 + 5 维评分)
- stage 1-9: `references/rubrics.md` 对应章节 (L1 评分用)

### 通用与跨阶段加载

- 触发反馈时: 对应 `references/feedback_layer*.md`; harness 适配差异 (Codex 用户必读): `references/harness_compat.md`
- 任何并行派发前: `references/parallel_dispatch.md`; 迭代预算耗尽输出 `decision_memo`
- 外部数据需求 (任何阶段): `references/data_acquisition.md` (数据源优先级/数据集登记 SSOT/网络安全约束/论文数据声明)
- stage 2/8 文献需求: `references/reference_skill_bridge.md` (检索硬上限 ≤5 次/阶段, T1→T3 路由, 四要素核验, 期刊分级与参数溯源)
- 图表任务: `references/figure_skill_bridge.md` (路由总表见其顶部); 规划用 `figure-table-planner`, 生成用 `math-figure-generator`, 终审质检用 `nature-figure` 的 QA 规则; 数据图 17 件 `templates/figures/scripts/render_modeling_pack.py --list`; 示意图 4 件 `templates/figures/scripts/render_diagram_pack.py --list`; drawio 可编辑模板 6 件 `templates/figures/scripts/render_drawio_pack.py --list`（落盘自动过 `drawio_check.py` 版式门禁, FAIL 即退出码 1）; vendor 路由: 高密度论文示意图走 `templates/figures/vendor/scibox-diagram/`（4 模板, content JSON 驱动）, 差异数据图型走 `vendor/scibox-figure/`, 答辩/展示级 HTML 走 `vendor/diagram-design/`, 复杂多面板主图（hero panel）、物理场/动力学/网络流图、TikZ 框架图走 `vendor/icarus-figures/`（paperfig 48 函数 + 5 个可编译 TikZ 范例; 不启用 journal 列宽, 产物落 cwd, critique.py 与 figqa/figure_lint 双门都过; 路由细则见 `figure_skill_bridge.md`）
- 图表硬门: 出图后跑 `scripts/figqa.py --strict` (六类碰撞) + `scripts/figure_lint.py` (设计规则); 新图模板 `templates/figures/scripts/` (tornado/优化分配/多场景/技术路线图, dispatcher `render_modeling_pack.py`)
- 图表配色: `references/color_typology.md` + 设计令牌宪法 `references/design_tokens.md` + `templates/figures/style/{palettes.py, mathmodel.mplstyle}`; 模板脚本公共底座 `templates/figures/scripts/figkit.py`; 图表计划记录 `palette` 字段
- 任何 stage 推进前: `scripts/check_gate.py --gate <N>` 门禁 (必停点 + 评分落盘, 见”必停点协议 (v2.3.0)”)
- 数字冻结: `scripts/freeze_numbers.py` (freeze/check/unfreeze/list, workspace_protocol §9); 运行清单: `scripts/run_manifest.py` (record/verify, §10 级联失效)
- 三赛联合工具: 题目/子问检索 `scripts/retrieve_cases.py --competition all --level both`; Stage 知识包 `scripts/build_stage_pack.py --stage 1|3|5|8|9`; 动态骨架与图表计划 `scripts/generate_paper_plan.py`; 结果证据追踪 `scripts/trace_claims.py`; 增量更新与版本 `scripts/update_knowledge.py`（默认预览, 明确更新时才用 `--apply`）
- 决策弹窗: 所有选项卡以 `references/decision_ui_map.md` 为唯一登记处
- 评分重释: `config/rating_contract.json` dimension_interpretations 16 键, 配额不作评分依据; L1 分数落盘带 `self_assessed: true`

### 按 stage 加载表

| stage | 额外加载 |
|-------|----------|
| -1 赛前 (T-7~T-1) | `references/stage_preseason.md` 跑一次兵检, 输出 `state/preseason_report.json` |
| 0 | `references/workspace_protocol.md` (唯一工作区/真源 SSOT/会话恢复四步; 检测同竞赛旧工作区必须先编号菜单确认归档); 真源 md 的公式/符号/题注/编号格式规范 `references/md_authoring_spec.md` (PDF/docx 双链实测口径); `state/skill_issues.md` 台账随工作区骨架创建, 自我纠错时追加 (协议见 `references/workspace_protocol.md` §11); 华数杯/研究生赛各自 `battle_plan_72h` 作战表 (见竞赛专项加载) |
| 1 | `competitions/<comp>/topic_specs.json`; 国赛、研究生赛和华数杯加载各自 `case_retrieval.md`，由 agent 运行 `scripts/build_stage_pack.py --stage 1`；需要跨赛结构参考时使用 `--competition all`; 华数杯另加 `references/huashubei_topic_decision.md` 选题决策矩阵 (见竞赛专项加载) |
| 2 | 审题门: 边界/权利/目标/假设四查 + 审题质询员红队 (stage_02 内嵌); 建模防错查 `references/modeling_norms.md` 对应题型节; 义务台账 `decision_log.stages.2.obligations` 镜像, gate 5/8 校验 unstarted 拦截; 末尾图表规格冻结 (stage_02 内嵌小节), 登记进真源.md 图表登记表 |
| 3 | stage 3/5 建模通用: `references/model_catalog.md` (含 §12 失效边界) + `references/knowledge_workflow.md`，运行 Stage 知识包与子问级检索，使用路线比较、假设风险和必做验证，禁止迁移历史数值; “选择卡”人类拍板门 (stage_03 内嵌); 外源文献检索（`scripts/literature_scout.py` + `references/literature_scout.md`，playbook 未命中域时触发，方法卡需过四要素核验）; 研究生赛另加 `competitions/huaweibei/playbooks/` 与 `competitions/huaweibei/papers/domain_index.md` (见竞赛专项加载); 国赛另加 `competitions/cumcm/playbooks/` 五域手册 (见竞赛专项加载) |
| 5 | per-Qi 评分跑完后调 `scripts/score_artifact.py --mode aggregate_qi` 聚合; 每问验证后写章节草稿卡 `paper_workspace/sections/q{i}_draft.md` (write-as-you-solve, 见 stage_05 E2 节); stage 8 组装时优先复用草稿卡; 图表 (stage 5/8): CUMCM/研究生赛加载各自 `distilled_figures.md`, 从命中案例的 `figure_story` 组织“结构—机制—中间状态—结果—可信边界”，基础 `figure_plan` 只作兜底 |
| 8 | `competitions/<comp>/{winning_patterns, phrase_bank, abstract_template, paper_skeleton}.md` (各赛加件见竞赛专项加载)；运行 `generate_paper_plan.py` 生成动态章节、图表计划和 evidence ledger; 经验校准: 先加载 `config/rating_contract.json`，再与 `competitions/<comp>/empirical.json.scoring_policy` 取交集，国赛、研究生赛、华数杯只允许可靠的摘要长度和页数校准，图表数/章节数/正文字数/词频均不得作硬阈值; CUMCM/研究生赛写作: 从命中案例读取 `writing_blueprint`，按“为什么—模型—中间状态—结果—验证—回答”写每问，研究生赛另按需读取 `papers/manual_paper_reviews.json` 的章节逻辑，只迁移结构，不复制原句; 每节成稿: `references/ai_flavor_removal.md` 十类自查; 重述/附录用 `templates/shared/{restatement_card.md, appendix_checklist.md}`; 结论核验 (stage 5/8): `scripts/claim_consistency_check.py --draft <正文> --results results/ [--strict]` (收敛/最优/提升 vs 结果文件状态); mcm 写作: `competitions/mcm/memo_letter_guide.md` (Memo/Letter 框架) |
| 9 | `competitions/<comp>/anti_patterns.md` + `rubric_overlay.json` 的 panel personas；运行 `trace_claims.py --strict`，摘要证据链未通过则阻断终稿; 一致性 (stage 8/9): `scripts/consistency_audit.py` (未冻结数字/摘要结论打架/图表断链/符号脱节/版本错乱); 评委模拟器（stage_09 内嵌：资格门 → 冻结原子扣分清单 → 扣分制 + 格式乘数）, panel 隔离规则见 `references/feedback_layer3_panel.md`; huaweibei 先核对 `competitions/huaweibei/current_rules.md` 日期戳; 提交终检 `scripts/pdf_qa.py` (页数/重复图题/匿名扫描/空白页) 并入 package_submission 流程; 提交: `references/submission_checklists.md` + `scripts/package_submission.py` (默认 dry-run); docx 审阅件导出 `scripts/export_docx.py` (md 真源 → submission/ 时间戳 docx); 终审核对 `state/skill_issues.md` 台账 |

### 竞赛专项加载 (competition=X 时)

**huashubei (华数杯)**:
- stage 0 kickoff: `references/huashubei_battle_plan_72h.md` (72h 逐小时时间表)
- stage 1 选题: `references/huashubei_topic_decision.md` (选题决策矩阵) + `competitions/huashubei/topic_specs.json`
- stage 3/5 建模: `competitions/huashubei/distilled_modeling.md` (A/B/C 三题型分章建模范式)
- stage 5/8 图表: `references/huashubei_figure_pack.md` (按题型图表代码模板)
- stage 8 写作: `competitions/huashubei/{winning_patterns, abstract_template, phrase_bank, paper_skeleton, distilled_structures, distilled_formats}.md`
- stage 8 评分: `competitions/huashubei/empirical.json` + `rubric_overlay.json` (6 维度国一标准)
- stage 9 终审: `competitions/huashubei/anti_patterns.md` (32 条) + rubric_overlay 的 4 角色 panel

**huaweibei (研究生赛)**:
- 通用入口: `references/cross_competition_distillation.md`，只共享结构与方法接口
- stage 0: `references/huaweibei_battle_plan_72h.md` (逐小时作战表 + h48 硬冻结[72h 基线时点, 2026 100h 赛制按表头映射转换] + 独立验收三选二), 与 huashubei 作战表同级
- stage 1/3/5: `competitions/huaweibei/topic_specs.json` + `case_retrieval.md` + `distilled_modeling.md` + `scripts/retrieve_cases.py --competition huaweibei`
- stage 1/3: `competitions/huaweibei/playbooks/`（按题目域命中 README 索引后读对应域文件; playbook 动作清单是 stage 3 候选生成输入之一, 不替代缺口驱动选型）
- stage 3: `competitions/huaweibei/papers/domain_index.md`（33 篇深读域级索引, 命中后按 paper_id 定向读 `papers/manual_paper_reviews.json`）
- stage 5/8 图表: `competitions/huaweibei/distilled_figures.md` + 命中案例 `figure_story`
- stage 8 写作: `competitions/huaweibei/{winning_patterns, abstract_template, phrase_bank, paper_skeleton, distilled_structures, distilled_formats, writing_voice, writing_playbook, writing_examples}.md`（writing_voice 管语气/摘要定量密度/公式呈现/推导四步叙事/结果分析五步/结论三招, 为华为杯写作必载件; writing_playbook 按 5 题型给公式-推导-结果分析差异化重点; writing_examples 为正反例对照库, 证据基础 33 篇深读）；需要提名（2021）/优秀论文（2025）范式时按证据 ID 读取 `papers/manual_paper_reviews.json`
- stage 8 评分: 只使用 `empirical.json` 中摘要长度和页数的完整覆盖分位
- stage 9 终审: `anti_patterns.md` + `rubric_overlay.json` 的五角色 panel，强制检查竞赛键、奖项身份和来源边界

**cumcm (国赛)**:
- stage 1/3/5: `competitions/cumcm/topic_specs.json` + `case_retrieval.md` + `distilled_modeling.md`（九类内容范式）+ `scripts/build_stage_pack.py --competition cumcm`
- stage 1/3: `competitions/cumcm/playbooks/`（五域：优化决策/几何物理/机器学习数据分析/仿真路径/概率统计；先读 README 域→文件映射再加载域文件; 动作清单是 stage 3 候选生成输入之一, 不替代缺口驱动选型; 证据基础 25 篇获奖论文方法链, 全部 source_checked）
- stage 5/8 图表: `competitions/cumcm/distilled_figures.md` + 命中案例图表叙事
- stage 8 写作: `competitions/cumcm/{winning_patterns, abstract_template, phrase_bank, paper_skeleton, distilled_structures, distilled_formats}.md`
- stage 9 终审: `competitions/cumcm/anti_patterns.md` + `rubric_overlay.json` panel

---

## 收敛准则 (统一定义, 三处一致)

**🔴 CHECKPOINT · verdict 决策**: `block`、`carryover`、从 stage 5 进入 stage 6、从 stage 8 进入终稿审核前，都必须给用户编号选择；不要擅自越过高风险结论。任何 stage 推进前必须跑 `scripts/check_gate.py --gate <N>`，FAIL 时按 verdict=block 同级处理（见"必停点协议"）。

**verdict 优先级 (从高到低)**:

| verdict | 触发 | 行为 |
|---------|------|------|
| `block` | issues 含 ≥1 high-severity | 暂停 skill, 用户介入 |
| `pass_early` | raw_min ≥ 9 AND weighted_mean ≥ 9 | iter-1 早退 |
| `pass` | raw_min ≥ 7 AND weighted_mean ≥ 8 | 进下一阶段 |
| `pass_with_review` *(stage 5)* | 任 Qi mark_for_review 但加权阈值满足 | 进 stage 6, L2 必读 review_qis |
| `refine` | 其他 | section-patch 精修, iter+=1 (cap 3) |
| `refine_partial` *(stage 5)* | 任 Qi.min < 7, 其他 Qi 已 pass | 仅 refine 该 Qi, 不动其他 |
| `carryover` | iter == 3 仍 refine | 进下一阶段, 标记由 L2 处理 |

`weighted_mean` = Σ(s_i × w_i) / Σ(w_i), 权重来自 `config/dim_weights.json[<comp>][<task_type>]` (clamp [0.7, 1.5]); `task_type=default` 全 1.0 等价老逻辑。

**迭代预算 (0.7.4)**: 每阶段 refine ≤3 轮 (上表); 全程跨阶段返工与并行任务重派设总预算, 耗尽后不许静默继续——必须输出结构化 `decision_memo` (blocked_item / tried / best_so_far / options / recommendation) 交用户编号决策, 模板见 `references/parallel_dispatch.md`。验收结论三选二独立来源规则见 `references/workspace_protocol.md` §7 (产出方自评一律视为待验证)。

此定义在 `feedback_layer1_critic.md` / `rubrics.md` / `scripts/score_artifact.py` 三处必须**完全一致**。

---

## 状态持久化

每阶段:
- 开头: `Read cwd/state/decision_log.json`, 核对 current_stage 与上下文
- 结尾: 更新 stage 节点 (核心决策 + 摒弃方案 + 评分), `current_stage += 1` 前必须跑 `scripts/check_gate.py --gate <N>` 且 exit 0（必停点 + 评分落盘双门禁, 见"必停点协议"）

**🔴 CHECKPOINT · 不可逆动作**: 删除 state、覆盖论文正文、批量移动用户文件、回退多个 stage、清空结果目录前，必须先让用户确认。默认做法是新增备份或追加事件，不直接覆盖。

`decision_log.json` v3.1 schema 关键字段 (与 `templates/shared/decision_log.json` 对齐):
- root: `competition`, `task_type`, `mode`, `interaction`, `checkpoints`, `current_stage`, `budget`, `events`
- stage_5 扩展: `qi_count`, `qi_weights`, `qi_status`
- scores 扩展: 含 `weighted_mean`, `review_qis`, `refine_qis` (stage 5 加权聚合用)

L2 跨阶段回检 (stage 5/6/8 末尾) 读这个文件主动找冲突, 触发**定向回滚**: 不重做整阶段, 只针对冲突点。

---

## Token 预算纪律

- L1 Critic 强制 JSON 输出, ~500 token/次
- 精修策略: section-level patch (`scripts/extract_diff.py`), 不重传完整 artifact (省 ~60% token)
- references/ 与 competitions/ 文件**懒加载**, 本 SKILL.md 主体 ≤ 6k tokens
- 阶段完成后, artifact 摘要 + 关键数据 + 路径写入 decision_log, 不在上下文保留全文
- 超预算 30% → 自动降级 (championship → standard, standard → fast)

---

## 用户指令快捷

- "进入 stage N" / "重做 stage N" → 跳转
- "切到研究生赛/华为杯" → `huaweibei`；"切到华数杯" → `huashubei`；其他竞赛按标准 key 修改 `decision_log.competition`（注意已有 state 兼容性）
- "升级到 championship" → 启用 L3 + L4 + red-team
- "切到 fast" → 关闭迭代
- "回退到 stage M" → 读 decision_log, 回退 current_stage 并清理 ≥M 节点
- "做 L2 回检" → 立即触发 cross-stage backtrack
- "看进度" → 输出 decision_log 摘要 + 当前评分

---

## 反例黑名单

不要做以下事情:

| 反模式 | 为什么不做 | 正确做法 |
|---|---|---|
| 一上来让用户手敲命令或编辑 JSON | 违背问答式优先，用户在赶比赛 | agent 自动读写文件；只让用户回答编号问题或给路径 |
| 一次性读完整 `references/`、`competitions/` | 浪费上下文，后续阶段反而丢细节 | 进入哪个 stage 读哪个 stage，竞赛特化文件按需读 |
| 为了推进流程编造题面、数据、评审要求 | 会污染模型和论文结论 | 缺资料就标记 pending，并用假设表明确占位 |
| block 以后继续自动精修 | 高严重问题需要人决定方向 | 暂停并给 2-4 个编号处理选项 |
| 单 Qi 不合格就重做整个 stage 5 | 浪费时间，破坏已通过子问题 | 用 `refine_partial` 只修失败 Qi |
| 把 seed v0.1 当稳定经验 | MCM/电工杯资料可靠度低于 CUMCM | 输出中标注 seed，并降低结论确定性 |
| 终稿前只看语言不看一致性 | 数模论文常败在符号、数据、结论不一致 | stage 9 必跑 anti_patterns + panel personas |
| 必停点自问自答/跳过不登记 | 2025F 实测病根：agent 自写自走 | checkpoints 登记 + check_gate 放行 |
| 删除或覆盖用户原稿 | 竞赛期间不可逆损失风险高 | 用 patch、新文件或备份路径交付 |

---

## 数据来源声明

- **`competitions/huashubei/`**: 用户本地 2020—2025 共 18 题；2023—2025 优秀论文 18 篇。18 题已进入案例索引，2020—2022 明确为 `problem_summary_only`，2023—2025 为 `paper_pattern`；S1-S4 是蒸馏任务链而非原题逐问。图表数量只作样本观察，不是官方门槛
- **`competitions/huaweibei/`** (0.7.2): 用户本地 2021—2025 共 30 题、190 篇优秀论文，30 题全量人工复核；12 篇 2021 数模之星提名论文完成摘要、背景、问题分析、假设、逐问正文、结尾和图表逻辑深读；2025 届 21 篇优秀论文全量深读（v2.2.0，award=excellent_paper_selection 不推测等级，2022—2024 仍无深读层）。2022—2025 无本地提名身份依据，不推测；A-F 不固定映射题型
- `competitions/cumcm/`: 32 篇官方展廊论文 + 1 篇可核验国二论文 + 25 个历年题面案例；58 篇旧误标研究生论文已隔离，来源见 `source_manifest.json`
- `competitions/mcm/`: SEED v0.1, 基于 COMAP 公开 scoring rubric + Outstanding Winner 公开模式手写; empirical 占位
- `competitions/diangong/`: SEED v0.1, 基于历年题量 + 公开评审标准估算; empirical 占位
- `competitions/apmcm/`: 本地 2024/2025 APMCM 中文赛赛题 6 份 + 优秀论文 12 篇蒸馏, 不含联网资料
- 通用模型清单 `references/model_catalog.md` 跨竞赛复用
- **模板与脚本资产 (0.7.5 起)**: `templates/latex/` 6 套竞赛模板、`templates/figures/` 自写色板/样式/图模板与脚本、`scripts/` 全部脚本、`references/` 全部规范文档均为本 skill 自写资产，按 LICENSE (MIT) 分发。历史版本曾吸收第三方资产，0.7.5 已全部移除并干净室重写，详见 CHANGELOG.md。**例外（1.4.0）**: `templates/figures/vendor/` 为三个上游开源 skill 的原样收编副本（scibox-diagram / scibox-figure / diagram-design），其版权与许可证归上游所有，出处与限制见 `vendor/VENDOR.md`；sci-box 上游未附正式 LICENSE，再分发前须按 VENDOR.md §5 处理。

后续如有 30+ MCM Outstanding 或电工杯一等奖 PDF, 可用 `scripts/ingest_papers.py --competition <comp>` 重新烘焙覆盖 seed。

---

## 与外部资源的关系

skill 自包含, 运行时不联网。外源文献检索层（literature_scout）为例外, 仅在 stage 1/3/5 挂点触发时联网, 其余资产保持自包含。下列离线资源可作人工补充:
- 国赛: `personqianduixue/Math_Model`, `datawhalechina/intro-mathmodel`, `dxs.moe.gov.cn` 优秀论文展廊
- 美赛: COMAP 官网 `comap.com`, `MCM Tutorial` (Frank Giordano)
- 电工杯: 中国电机工程学会论文集
