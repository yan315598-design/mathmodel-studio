# 工作区纪律与冻结协议（唯一工作区 + 真源 SSOT）

> 0.7.4 新增。为华为杯等 72-96h 赛制设计，适用于全部竞赛分支。
> 来源：多场历史实战复盘中沉淀的流程痛点——版本失控（一天内版本号连跳多级）、工作区互串、跨会话上下文丢失（交接文档膨胀至数百行）、论文与结果不一致（真源手抄数值与实际结果不符）。
> 核心原则：冻结约定必须有机器可执行形式；版本语义不靠文件名承载，靠 真源.md 修订记录承载。

---

## 1. 唯一工作区规则

**一题一目录**：一场比赛、一道题，同一时间只有一个活动工作区（即 cwd）。新会话不开新目录，回到同一 cwd 继续。

目录骨架（`references/stage_preseason.md` §④ 兵检时生成；赛前未兵检的，Stage 0 按本表补齐缺失项）：

```
<workspace>/
  state/               # decision_log.json（流程状态机）; skill_issues.md（台账, §11）
  results/             # 各子问结果（JSON/CSV，供脚本注入）      figures/  # 图表输出
  code/                # 求解代码                              paper_workspace/  # 论文工程（main.tex|main.md + sections/）
  _archive/            # 归档区，只进不出
  真源.md              # SSOT：口径/符号/假设/结果/图表/修订记录
  selection_sheet.md   # 选型总表：记录候选、比较和证据；正式选择栏与 stages.3.selected_per_subproblem 及 checkpoints.per_qi_selection 对齐
```

规则：

1. **另开工作区前必须先关旧的**：把旧目录整体移入 `_archive/`（如 `_archive/2026-huaweibei-v0/`），并关闭其中仍在跑的进程（jupyter / python / 监听脚本）。
2. **审计/写作脚本只认 cwd**：读 `results/`、`figures/`、`state/` 一律用相对路径或显式 cwd 参数，禁止跨目录读其他工作区的结果文件（历史实战复盘：审计脚本读旧目录结果，产出错误结论）。
3. **同竞赛旧工作区检测**：Stage 0 初始化时若发现同目录或父目录已有同竞赛工作区，先给用户编号菜单——`1) 移入 _archive  2) 查看差异  3) 取消`——不允许两个"活动"工作区并行（历史实战复盘：同一题目多个工作区互串）。

---

## 2. 真源.md SSOT 模板

数据、模型、符号、假设、图表、结论的**单文件权威**。与 `decision_log.json` 分工：**真源管内容口径，decision_log 管流程状态**——一个数字对不对查真源，一个阶段做没做完查 decision_log。

模板（Stage 0 初始化时落盘到工作区根目录；各表列头如下，示例行只示范格式）：

```markdown
# 真源.md（<竞赛>-<年份>-<题号>）
> 单一事实源。任何数字进论文前，本文件结果登记表必须有行。冲突文件移入 _archive/。

## 1. 口径冻结单
| 条目 | 内容 | 标签 | 冻结时间 |
| 时间轴 | 2020-01 ~ 2024-12, 月度 | FACT | h2 |
| 指标定义 | 利用率 = 实际产出 / 额定产能 | FACT | h2 |
| 方案命名 | 三阶段协同调度模型 | CHOICE | h3 |

FACT = 题面/数据给定的事实（有误须用户确认才改）; CHOICE = 我方选择（可改, 改须登记）。

## 2. 符号表 | 符号 | 含义 | 单位 | 出现于 |
## 3. 假设表 | # | 假设 | 依据 | 影响的子问 |
## 4. 数据冻结状态 | 附件 | 状态 | 校验 |      （如 附件1.xlsx | 已冻结 | 行数/缺失值快照）
## 5. 模型命名与诚实声明
- Q1 模型名: <命名>（反映真实机制, 不冒充未使用的方法）
- 负面结果如实报告: <哪些尝试失败, 结论是什么>
## 6. 结果登记表 | key | 数值 | 单位 | 生成脚本 | 时间戳 |
| q1.total_cost | 12345.6 | 元 | code/q1_solve.py | h14 |
## 7. 图表登记表 | 图号 | 回答什么问题 | 数据源 | 色板 | 类型 | 设计卡 | 终稿图注 | 状态 |
| fig3 | 两算法收敛速度差异 | results/q2_conv.json | academic_blue | 过程图 | 已写 | 两算法均在 1200 代内收敛, A 算法收敛更早且终值更优 | 已出 |
## 8. 修订记录 | 版本 | 时间 | 谁审查 | 改了什么 | 审计是否通过 |
| v1 | h2 | 用户 | 初建口径冻结单 | — |
```

> **两列写入纪律**：设计卡列——每张正式展示图生成前填写设计卡五要素，探索图不强制（回答什么问题 / 图型选择与理由 /
> 证据层 / 注释预算 / 评委一眼应看到什么，规范见 `references/figure_skill_bridge.md` 图叙事章），本列登记
> "已写/不适用（原始答案附件）"；作战地图仅在全局依赖概览有价值时采用。终稿图注列（v3.1.0）——stage 5 出图时把设计卡第 ⑤ 要素凝成
> 一句话写入本列，本列是论文图注的**唯一来源**：stage 8 组装**只许逐字复制**进 `![图 N …]` 题注，不得改写、
> 扩写或重述；写作期若须改图注，回本表改本列（走计划修订）再复制，正文不出现第二份图注文本。实测教训：
> 2026 国赛 A 题图 13 题注虚报"问题三与问题四并列"而图内只有问题三——写作 agent 自由改写图注所致。

规则：

1. **任何数字进论文前必须在结果登记表有行**（数值 + 生成脚本 + 时间戳三位一体，缺一不可）。
2. **禁止平行结论文件**：结论性数字只写在真源与由真源/脚本注入的论文里；`results/` 可包含机器结果及绑定来源的诊断报告，探索结果明确未冻结。发现冲突先回源核对并标记失效；不得用副本覆盖正式数字或自动删除用户内容。
3. **修订记录强制**：任何口径/结果/图表变更追加版本行（谁审查、改了什么、审计是否通过），只追加不删行。

---

## 3. 版本纪律

| 禁止 | 替代做法 |
|------|---------|
| 文件名后缀修订链（`v5_final_改2_最终.docx`，历史实战中曾叠出多层后缀） | `paper_workspace/main.md`（或 main.tex）**原地修订** + 真源修订记录追加版本行 |
| 复制多份摘要/正文对比 | 真源修订记录保留版本行，正文只留当前版 |
| 旧文件散落各目录 | `_archive/` 只进不出：移入不改名，移入后不回移 |

导出：定稿导出 docx/pdf 一律带**秒级**时间戳进 `submission/`（如 `submission/huaweibei_20260911_143012.pdf`）：docx 审阅件由 `scripts/export_docx.py` 导出，docx 终稿由 `scripts/export_final_docx.py` 导出（**秒级时间戳**；同秒重复导出自动改名 `_2/_3…`、不覆盖已有产物——**该口径只属终稿导出**，审阅件 `scripts/export_docx.py` 仍用分钟级命名），PDF 终检与提交包由 `scripts/package_submission.py` 管理。文件名时间戳只用于区分导出快照，**不承载版本语义**——版本语义只在真源修订记录里。

### 3.1 docx 审阅件协议

> v2.1.0 新增。md 是唯一真源，docx 仅作审阅件；md 真源的公式/符号/题注/编号写法遵守 `references/md_authoring_spec.md`（公式为 Word 原生公式对象，编号公式统一 `$$…\qquad (N)$$`（禁 `\tag`），表题注在上、图题注在下由 md 写法天然保证）。三条要点：① **docx = 审阅件、md = 真源**——正文修订永远发生在 md 上（原地修订 + 真源修订记录追加版本行）；② **导出走 `scripts/export_docx.py`**——输出 `<竞赛>_review_<时间戳>.docx` 进 `submission/`，`--reference-doc` 挂样式基准、`--dry-run` 预览 pandoc 命令；③ **批注人工合回，禁止反向覆盖**——Word 批注由 agent 读取后人工合回 md，禁止用 pandoc 反向转换覆盖真源。

> v2.9.0 **终稿通道例外**：stage 8 退出门禁全过且数字冻结完成后，登记 `docx_channel=true`（或 `final_chain=docx`），docx 升为终稿介质——人只在 Word 改呈现层（措辞/标点/间距/图位置），**图注/表注措辞变更须回源**（改 `真源.md` 图表登记表"终稿图注"列，不属 Word 白名单），纪律 = 数字回检门禁（`scripts/docx_number_recheck.py` 对冻结表逐条核对，FAIL 即回退 md 修改重走导出）。完整协议唯一权威源见 `references/docx_final_channel.md`，此处不重述；未登记切换时按审阅件模式执行。

---

## 4. 会话恢复协议

跨会话上下文丢失的解法不是写更长的交接文档（历史实战中曾积累多份交接 md 与 CONTEXT.md），而是固定四步开场（agent 自动执行，不向用户索要交接）。**本节是恢复规则的单点入口**，其余文档只写短提醒：

1. 读 `state/decision_log.json` → 流程状态（当前阶段 / 各 Qi 状态 / 评分历史）。
2. 读 `真源.md` 的口径冻结单 + 修订记录末尾 5 行 → 内容口径与最近变更。
3. 跑 `freeze_numbers.py check` 与 `run_manifest.py verify`（脚本从 **`<skill>/scripts/`** 解析，不是工作区内——见 §9/§10）→ 报告 stale 项；脚本或依赖缺失时**记 `未执行/缺依赖` 并向用户如实报告（不得当作已核验通过，硬门不因跳过而放行）**，不中断恢复流程。
4. 输出 **当前阶段 / 已冻结项 / 待办**（并列 stale 清单）；用户明确要求继续时直接按记录推进。只有缺少必要科学决策或触及冻结变更才等待确认，不重复询问已有授权。

规则：**禁止写超过 50 行的交接文档**（交接信息只落真源.md 与 decision_log.json，不落第三处）；会话结束前把"待办 3 条"写入 `decision_log.events.log`（一行一条，不写散文）。

---

## 5. 冻结时点

以 72h 赛制为基准；更长赛程按比例后移（见各竞赛作战表）。

| 时点 | 冻结内容 | 之后允许 | 推翻条件 |
|------|---------|---------|---------|
| h8 | 登记每问证据需求和暂定展示方案 | 按探索与基线实验修订图型 | 真源登记原因与影响 |
| h24 | 口径冻结单；复查图表计划是否已有证据 | 图型随实验完善；FACT 有误须用户确认 | 真源登记；正式规格在验证后的 D.1 冻结 |
| 48h | 模型主结构 | 只修 bug 与补灵敏度分析 | 用户编号菜单确认 + 真源登记 |
| 60h | 结果数字 | 只写不改模型（数字注入，§6） | 不推翻；重算属重大事故，须用户确认 |

48h 后请求推翻模型主结构，必须显式给用户编号菜单（`1) 同意推翻, 重排剩余时间预算  2) 部分推翻: 只换 <子模块>, 主框架保留  3) 驳回, 继续按现模型修 bug`），禁止静默推翻。

---

---

## 6. 数字注入规则

60h 起论文数字一律由脚本从 `results/` 生成并注入，**禁止手抄**。历史实战复盘：真源手抄数值与实际结果不符，一处错全文皆旧。

`code/inject_numbers.py` 骨架（复制进工作区 code/ 后按需改造；读 `results/*.json` 登记值，替换 `paper_workspace/` 内 `{{key}}` 占位符）：

```python
"""数字注入示意: results/*.json 登记值 -> paper_workspace/main.md 的 {{key}}。"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # 工作区根

def inject(text, registry):
    def sub(m):
        key = m.group(1)
        if key not in registry:
            raise KeyError(f"results/ 无 {key}: 禁止手抄, 先补真源结果登记表")
        return str(registry[key])
    return re.sub(r"\{\{([\w.]+)\}\}", sub, text)

# 使用: 合并 results/*.json 为 registry, 对 main.md 执行 inject 后原地写回
```

注入后自查：`grep "{{" paper_workspace/main.md` 零残留才算通过；占位符缺失即报错，不许"先手填个数"。

---

## 7. 独立验收规则（元教训固化）

历史复盘：审计报告宣称"已具国一水平"，用户独立审查却发现多项根本性风险。结论：**验收结论不许由产出方自证**。

任何"审计通过 / 已达 X 水平 / 可以提交"结论，必须满足以下**三选二**：

1. **脚本审计输出**：可复现的命令与输出（`scripts/trace_claims.py --strict`、`scripts/score_artifact.py`、`scripts/package_submission.py` dry-run；用户侧自建的全链审计脚本同属此类）。
2. **非产出方复核**：用户本人，或换一个未参与产出的 agent 以审查角色重看一遍。
3. **checklist 逐条打钩**：对照 `references/submission_checklists.md` 等清单逐项 ☐→☑，不许"总体感觉没问题"。

产出方自评一律视为**待验证**，不得作为放行依据；Stage 9 panel 前必须先跑脚本审计（第 1 类），否则 panel 结论无效。

## 8. 与 10 阶段的挂接

| Stage | 动作 | 指针 |
|-------|------|------|
| 0 kickoff | 建骨架 + 真源.md 落盘；检测旧工作区；已有真源走会话恢复四步 | `references/stage_00_kickoff.md` Step 3 |
| 1 选题 | 选题锁定后立即锁口径冻结单（FACT/CHOICE） | `references/stage_01_problem_selection.md` |
| 2 解析 | 证据需求与暂定图表方案写入登记表，实验后完善 | `references/stage_02_analysis.md` 证据需求与图表计划节 |
| 5 / 8 / 9 | 每问完成即登记结果表；写作期数字注入；终审独立验收三选二 | `references/stage_05_subproblem_loop.md` / `references/stage_08_writing.md` / `references/stage_09_review.md` |

赛前兵检（工作区骨架生成）：`references/stage_preseason.md` §④。逐小时冻结时点排布：`references/huaweibei_battle_plan_72h.md`、`references/huashubei_battle_plan_72h.md`。

---

## 9. frozen_numbers 数字冻结

> 0.7.5 新增。`scripts/freeze_numbers.py`：**frozen_numbers 是 §5"h60 结果数字冻结"的机器执行层**（§5 定"60h 起只写不改模型"，本节定登记与校验的落地形式），两者一条链，不构成第二套口径。

**登记规则**：论文数字进稿前必须经 `scripts/freeze_numbers.py freeze` 登记，每条 frozen claim 含七字段——`claim_id`（建议 `Qi.键名` 对齐真源结果登记表 key，如 `q1.total_cost`）/ `value` / `unit` / `source_file`（`results/` 下机器可读产物）/ `source_locator`（键路径、行号或列名）/ `source_sha256`（来源文件内容哈希）/ `frozen_at`（时间戳，如 `h61`）。

操作纪律：

1. **冻结后禁止手改**：七字段任何一项都不许直接编辑登记文件——数字要变只能走流程（下条），手改即等同 §6 禁止的手抄。
2. **改数四步**：`freeze_numbers.py unfreeze <claim_id>` → 改源（模型/数据/脚本）→ 重跑生成新 `results/` 产物 → `freeze_numbers.py freeze` 重新登记。四步之外没有"顺手改一下"。
3. **每阶段末跑 `freeze_numbers.py check`**：核对每条 claim 的 `value` 与 `source_sha256` 是否仍与当前 `results/` 一致，输出 stale 清单；locator 可解析性用 `verify`（试解析不给结论，纯诊断）。
4. **stale 数字禁止进摘要与结论**：check 未通过（源哈希已变）的 claim 视为失效，摘要、结论与正文结论句不得引用；须先走改数四步。
5. 与 §6 数字注入衔接：注入脚本从 `results/` 取值，frozen_numbers 保证"注入那一刻源没有变过"——注入前若 check 报 stale，先重跑再注入。

---

## 10. 运行清单与哈希级联失效

> 0.7.5 新增。`scripts/run_manifest.py`：解决"哪次运行产出了这份结果、结果还能不能信"的追溯问题。

**登记规则**：关键求解运行（生成进稿数字或论文图表的那些）用 `run_manifest.py record` 登记，每次运行四要素——**脚本 / 命令 / 退出码 / 输入输出 SHA-256**；由脚本在运行后自动完成，不事后补记。声明的脚本/输入/输出文件不存在时 record 拒绝登记（exit 2）；record 为读-改-写整体替换，由锁文件串行保护——**record 串行执行，勿并发**（并发冲突 exit 3）。

`run_manifest.py verify` 对照 manifest 重算输入输出哈希，判断每次运行是否仍然有效。防篡改为**逐行自哈希 + 链式双锚**：每条记录带 `self_sha256`（本记录规范化 JSON 的哈希）与 `prev_sha256`（上一行原文哈希，删改前一行即断链）；记录中任何 `sha256:null` 一律判"记录含缺失文件"错误。

**级联失效规则**：结果文件哈希变（重跑/手改/部分覆盖）→ ① 依赖它的 frozen claim 全部 stale（§9 check 捕获）；② 以该结果为数据的图表失效 → 重生成图、图表登记表状态改"待重出"；③ 引用该数字的摘要主张失效 → 摘要相应句重写、数字以新 frozen 值为准。输入数据或求解脚本哈希变 → 该运行及其全部下游产物失效，重跑该运行并 `record` 新条目，旧条目标记不复用。

一句话：**结果文件哈希一变，依赖它的 frozen claim / 图表 / 摘要主张全部 stale**，必须重跑 `freeze_numbers.py check`（或 verify）与 `scripts/trace_claims.py` 重新闭环，闭环前相关主张不得进稿。

**红线**：绝不用手改 manifest 或 frozen_numbers 登记文件里的 `status`、哈希字段来"消除"stale——状态只能由脚本按实际文件内容判定，手改状态等于伪造审计结论（同 §7 独立验收精神：结论不许由产出方自证）。


---

## 11. skill_issues 台账协议

> v2.3.0 新增（正式化）。2025 华为杯 F 题实测发现 agent 的流程偏差（必停点未问、评分未落盘）没有留痕，复盘时只能靠回忆。本节把"自我纠错留痕"定为固定协议。

**路径与创建**：`cwd/state/skill_issues.md`，Stage 0 初始化骨架时创建——**不存在时从 `<skill>/templates/shared/skill_issues.md` 复制**（模板自带表头与条目格式），随骨架清单一起落盘。

**登记规则**：agent 每次自我纠错（发现自己流程偏差并修复，如"必停点没问→补问后登记 checkpoints""L1 评分漏跑→补跑 `score_artifact.py` 落盘"）追加一行：`| S-NN | 日期 | 现象 | 根因 | 临时处理 | 是/否 |`（列结构与模板一致）。`S-NN` 为流水号（S-01, S-02, ...），**只追加不改写旧条目**（同 §2 修订记录纪律）；末列"是否建议入版"属 skill 设计缺陷（而非本次执行失误）填"是"。

**终审消费**：Stage 9 终审时读本台账；存在"建议入版"条目时向用户提示沉淀——列出条目，由用户决定是否反馈进 skill 仓库（**用户拍板，agent 不擅自改 skill**）。

---

## 12. checkpoints 条目 JSON schema（单点成文, v2.8.0）

> 六个必停点的定义、触发时机与登记键以 `SKILL.md` "必停点协议"节为唯一权威源（agent 可达性优先，不在此重复）；本节只单点固定 **`decision_log.checkpoints.*` 条目的 JSON 形状**——此前该形状在 stage_05 内重复出现 4 次，是漂移源。`scripts/check_gate.py` 是本 schema 的程序执行层。

**基础条目**（全部必停点通用，4 个字段缺一不可）：

```json
{"status": "answered", "asked_at": "<ISO 时间戳>", "answer": "<用户选择摘要>", "source": "chat"}
```

- `status`: 固定 `"answered"`；`asked_at` / `answer`: 提问时间戳与用户选择摘要。
- `source`: 白名单 `chat` / `user_cli`。主 agent 经用户问答后写入，固定 `"chat"`；已归档薄执行器（v3.3.0 起移出公开仓库）经 CLI `answer` 子命令 trusted 写入时为 `"user_cli"`。**缺失或非白名单值（model/llm/agent/auto 等）一律视为未答，`check_gate.py` 拦截。**

**扩展字段**（仅 `figure_menu["Q<i>"]` 用，逐问写入）：`count`（0-9，该问图表数量，必填）；0/1 张时加 `exception: true` + `reason`（低频决策披露登记，用途是决策追溯、不是扣分豁免）；`narrative`（逐图一行摘要：问题/图型/一眼所见，D.1 第 3 问结果，纯记录不入门禁）；多问菜单合并成一轮呈现时加 `menu_form: "consolidated_4q_single_round"`（字段值固定，三问/四问通用；形态定义见 `references/figure_skill_bridge.md` 出图决策菜单节"合并菜单形态"——**登记仍逐问写入**，合并的只是呈现轮次）。其余登记键（`kickoff_5q` / `analysis_confirm` / `card_decision` / `qi_verdict["Q<i>"]` / `per_qi_selection["Q<i>"]`）只用基础条目；stage 文件引用本 schema 时写"条目形状见 `references/workspace_protocol.md` §12"，不再内联 JSON 示例。

---

## 13. 知识架构设计理由（已迁出运行路径）

> 原 §13「知识架构设计理由」（v2.8.0 由历史归档 architecture.md 摘录）于 2026-09-19 维护期整体迁出运行路径；该归档于 v3.3.0 起移出公开仓库（维护者本地留存）。本节运行时不需要，仅保留指针，别再搬回本文件。归属与迁移规则对照见 `docs/maintenance_notes.md`。
