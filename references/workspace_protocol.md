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
  state/               # decision_log.json（流程状态机）; skill_issues.md（自我纠错台账, §11）
  results/             # 各子问结果（JSON/CSV，供脚本注入）
  figures/             # 图表输出
  code/                # 求解代码
  paper_workspace/     # 论文工程（main.tex 或 main.md + sections/）
  _archive/            # 归档区，只进不出
  真源.md              # SSOT：口径/符号/假设/结果/图表/修订记录
```

规则：

1. **另开工作区前必须先关旧的**：把旧目录整体移入 `_archive/`（如 `_archive/2026-huaweibei-v0/`），并关闭其中仍在跑的进程（jupyter / python / 监听脚本）。
2. **审计/写作脚本只认 cwd**：读 `results/`、`figures/`、`state/` 一律用相对路径或显式 cwd 参数，禁止跨目录读其他工作区的结果文件（历史实战复盘：审计脚本读旧目录结果，产出错误结论）。
3. **同竞赛旧工作区检测**：Stage 0 初始化时若发现同目录或父目录已有同竞赛工作区，先给用户编号菜单——`1) 移入 _archive  2) 查看差异  3) 取消`——不允许两个"活动"工作区并行（历史实战复盘：同一题目多个工作区互串）。

---

## 2. 真源.md SSOT 模板

数据、模型、符号、假设、图表、结论的**单文件权威**。与 `decision_log.json` 分工：**真源管内容口径，decision_log 管流程状态**——一个数字对不对查真源，一个阶段做没做完查 decision_log。

模板（Stage 0 初始化时落盘到工作区根目录）：

```markdown
# 真源.md（<竞赛>-<年份>-<题号>）
> 单一事实源。任何数字进论文前，本文件结果登记表必须有行。冲突文件移入 _archive/。

## 1. 口径冻结单
| 条目 | 内容 | 标签 | 冻结时间 |
|------|------|------|---------|
| 时间轴 | 2020-01 ~ 2024-12, 月度 | FACT | h2 |
| 指标定义 | 利用率 = 实际产出 / 额定产能 | FACT | h2 |
| 方案命名 | 三阶段协同调度模型 | CHOICE | h3 |

FACT = 题面/数据给定的事实（有误须用户确认才改）; CHOICE = 我方选择（可改, 改须登记）。

## 2. 符号表
| 符号 | 含义 | 单位 | 出现于 |
|------|------|------|--------|

## 3. 假设表
| # | 假设 | 依据 | 影响的子问 |
|---|------|------|-----------|

## 4. 数据冻结状态
| 附件 | 状态 | 校验 |
|------|------|------|
| 附件1.xlsx | 已冻结 | 行数/缺失值快照, 修改时间 |

## 5. 模型命名与诚实声明
- Q1 模型名: <命名>（反映真实机制, 不冒充未使用的方法, 如不冒充 ε-constraint）
- 负面结果如实报告: <哪些尝试失败, 结论是什么>

## 6. 结果登记表
| key | 数值 | 单位 | 生成脚本 | 时间戳 |
|-----|------|------|---------|--------|
| q1.total_cost | 12345.6 | 元 | code/q1_solve.py | h14 |

## 7. 图表登记表
| 图号 | 回答什么问题 | 数据源 | 色板 | 类型 | 状态 |
|------|-------------|--------|------|------|------|
| fig3 | 两算法收敛速度差异 | results/q2_conv.json | academic_blue | 过程图 | 已出 |

## 8. 修订记录
| 版本 | 时间 | 谁审查 | 改了什么 | 审计是否通过 |
|------|------|--------|---------|-------------|
| v1 | h2 | 用户 | 初建口径冻结单 | — |
```

规则：

1. **任何数字进论文前必须在结果登记表有行**（数值 + 生成脚本 + 时间戳三位一体，缺一不可）。
2. **禁止平行结论文件**：结论性数字只写在真源与由真源/脚本注入的论文里；`results/` 只存机器可读原始结果。发现与真源冲突的结论性 md/txt，立即移入 `_archive/`。
3. **修订记录强制**：任何口径/结果/图表变更追加版本行（谁审查、改了什么、审计是否通过），只追加不删行。

---

## 3. 版本纪律

| 禁止 | 替代做法 |
|------|---------|
| 文件名后缀修订链（`v5_final_改2_最终.docx`，历史实战中曾叠出多层后缀） | `paper_workspace/main.md`（或 main.tex）**原地修订** + 真源修订记录追加版本行 |
| 复制多份摘要/正文对比 | 真源修订记录保留版本行，正文只留当前版 |
| 旧文件散落各目录 | `_archive/` 只进不出：移入不改名，移入后不回移 |

导出：定稿导出 docx/pdf 一律带时间戳进 `submission/`（如 `submission/huaweibei_20260911_1430.pdf`），统一写入 `submission/`：docx 审阅件由 `scripts/export_docx.py` 导出，PDF 终检与提交包由 `scripts/package_submission.py` 管理。文件名时间戳只用于区分导出快照，**不承载版本语义**——版本语义只在真源修订记录里。

### 3.1 docx 审阅件协议

> v2.1.0 新增。补齐本节"导出"承诺的 docx 侧实现（此前只有约定、没有脚本）；md 是唯一真源，docx 仅作审阅件。md 真源的公式/符号/题注/编号写法一律遵守 `references/md_authoring_spec.md`（v2.2.0，双链实测口径）——公式是 Word 原生公式对象，编号公式统一 `$$…\qquad (N)$$`（禁 `\tag`，docx 链会丢编号），表题注在上、图题注在下由 md 写法天然保证。

1. **docx = 审阅件，md = 真源**：docx 只用于导出给只会 Word 的队员圈批注；正文修订永远发生在 `paper_workspace/` 的 md 真源上（原地修订 + 真源修订记录追加版本行，同 §3 上表纪律）。
2. **导出走 `scripts/export_docx.py`**：输出 `<竞赛>_review_<时间戳>.docx` 进 `submission/`（时间戳只区分快照、不承载版本语义，同上）；`--reference-doc` 可挂样式基准文档，`--dry-run` 可预览将执行的 pandoc 命令。
3. **批注人工合回，禁止反向覆盖**：Word 队员的批注/改动由 agent 读取后转述，人工合回 md 真源；**禁止用 pandoc 把 docx 反向转换为 md 覆盖真源**。

---

## 4. 会话恢复协议

跨会话上下文丢失的解法不是写更长的交接文档（历史实战中曾积累多份交接 md 与 CONTEXT.md），而是固定四步开场：

新会话开场（agent 自动执行，不向用户索要交接）：

1. 读 `state/decision_log.json` → 流程状态（当前阶段 / 各 Qi 状态 / 评分历史）。
2. 读 `真源.md` 的**口径冻结单 + 修订记录末尾 5 行** → 内容口径与最近变更。
3. 跑 `scripts/freeze_numbers.py check` 与 `scripts/run_manifest.py verify`（0.7.5 配套脚本，见 §9/§10）→ 报告 stale 项；工作区里没有这两个脚本时跳过本步，不报错不阻塞。
4. 输出三行给用户确认：**当前阶段 / 已冻结项 / 待办 3 条**（第 3 步发现 stale 项时，stale 清单并入本行向用户亮出）。用户确认后才继续动工。

规则：

- **禁止写超过 50 行的交接文档**；交接信息必须落在真源.md 与 decision_log.json 里，不落第三处。
- 会话结束前把"待办 3 条"写入 decision_log 的 `events.log`（一行一条），不写散文。

---

## 5. 冻结时点

以 72h 赛制为基准；更长赛程按比例后移（见各竞赛作战表）。

| 时点 | 冻结内容 | 之后允许 | 推翻条件 |
|------|---------|---------|---------|
| h8 | 图表规格定稿（张数预算 / 每图论证价值 / 色板） | h24 前仍可修订（在真源.md 修订记录登记时间/原因/影响） | 用户确认 + 真源登记 |
| h24 | 口径冻结单 + 图表规格硬冻结 | 改 CHOICE 条目（登记）；FACT 有误须用户确认 | 用户确认 + 真源登记 |
| 48h | 模型主结构 | 只修 bug 与补灵敏度分析 | 用户编号菜单确认 + 真源登记 |
| 60h | 结果数字 | 只写不改模型（数字注入，§6） | 不推翻；重算属重大事故，须用户确认 |

48h 后请求推翻模型主结构，必须显式给用户编号菜单，禁止静默推翻：

```text
【h48 后请求推翻模型主结构: <旧> → <新>, 理由: ...】

  1) 同意推翻, 重排剩余时间预算（写作压缩风险已知悉）
  2) 部分推翻: 只换 <子模块>, 主框架保留
  3) 驳回, 继续按现模型修 bug

回复数字。
```

---

## 6. 数字注入规则

60h 起论文数字一律由脚本从 `results/` 生成并注入，**禁止手抄**。历史实战复盘：真源手抄数值与实际结果不符，一处错全文皆旧。

`code/inject_numbers.py` 示意（复制进工作区 code/ 后按需改造；读 `results/*.json` 登记值，替换 `paper_workspace/` 内 `{{key}}` 占位符）：

```python
"""数字注入示意: results/*.json 登记值 -> paper_workspace/main.md 的 {{key}}。"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # 工作区根

def load_registry():
    merged = {}
    for p in sorted((ROOT / "results").glob("*.json")):
        merged.update(json.loads(p.read_text(encoding="utf-8")))
    return merged

def inject(text, registry):
    def sub(m):
        key = m.group(1)
        if key not in registry:
            raise KeyError(f"results/ 无 {key}: 禁止手抄, 先补真源结果登记表")
        return str(registry[key])
    return re.sub(r"\{\{([\w.]+)\}\}", sub, text)

if __name__ == "__main__":
    md = ROOT / "paper_workspace" / "main.md"
    md.write_text(inject(md.read_text(encoding="utf-8"), load_registry()), encoding="utf-8")
    print("注入完成; 残留 {{ 占位符必须为 0")
```

注入后自查：`grep "{{" paper_workspace/main.md` 零残留才算通过；占位符缺失即报错，不许"先手填个数"。

---

## 7. 独立验收规则（元教训固化）

历史实战复盘：审计报告宣称"已具国一水平"，用户独立审查却发现多项根本性风险。结论：**验收结论不许由产出方自证**。

任何"审计通过 / 已达 X 水平 / 可以提交"结论，必须满足以下**三选二**：

1. **脚本审计输出**：可复现的命令与输出（`scripts/trace_claims.py --strict`、`scripts/score_artifact.py`、`scripts/package_submission.py` dry-run；用户侧自建的全链审计脚本同属此类）。
2. **非产出方复核**：用户本人，或换一个未参与产出的 agent 以审查角色重看一遍。
3. **checklist 逐条打钩**：对照 `references/submission_checklists.md` 等清单逐项 ☐→☑，不许"总体感觉没问题"。

产出方自评一律视为**待验证**，不得作为放行依据。Stage 9 panel 评审前必须先跑脚本审计（第 1 类），否则 panel 结论无效。

---

## 8. 与 10 阶段的挂接

| Stage | 动作 | 指针 |
|-------|------|------|
| 0 kickoff | 建工作区骨架 + 真源.md 落盘；检测旧工作区；已有真源走会话恢复四步 | `references/stage_00_kickoff.md` Step 3 |
| 1 选题 | 选题锁定后立即锁口径冻结单（FACT/CHOICE） | `references/stage_01_problem_selection.md` |
| 2 解析 | 图表规格冻结（张数预算 / 论证价值 / 色板）写入图表登记表 | `references/stage_02_analysis.md` 图表规格冻结节 |
| 5 子问循环 | 每问完成即登记结果表 + 跑单项审计，不等总审 | `references/stage_05_subproblem_loop.md` |
| 8 写作 | 数字注入（60h 后只写不改模型） | `references/stage_08_writing.md` |
| 9 终审 | 独立验收三选二；panel 前必跑脚本审计 | `references/stage_09_review.md` |

赛前兵检（工作区骨架生成）：`references/stage_preseason.md` §④。逐小时冻结时点排布：`references/huaweibei_battle_plan_72h.md`、`references/huashubei_battle_plan_72h.md`。

---

## 9. frozen_numbers 数字冻结

> 0.7.5 新增。`scripts/freeze_numbers.py` 为 0.7.5 配套脚本（可能尚未落盘，落盘前本节按约定口径执行）。**frozen_numbers 是 §5"h60 结果数字冻结"的机器执行层**：§5 定时点（60h 起只写不改模型），本节定登记与校验的落地形式， 两者一条链， 不构成第二套口径。

**登记规则**：论文数字进稿前必须经 `scripts/freeze_numbers.py freeze` 登记，每条 frozen claim 含七字段：

| 字段 | 含义 | 示例 |
|------|------|------|
| `claim_id` | 主张标识（建议 `Qi.键名` 对齐真源结果登记表 key） | `q1.total_cost` |
| `value` | 冻结时的数值 | `12345.6` |
| `unit` | 单位 | `元` |
| `source_file` | 数值来源文件（`results/` 下机器可读产物） | `results/q1_solution.json` |
| `source_locator` | 文件内定位（键路径 / 行号 / 列名） | `total.cost` |
| `source_sha256` | 来源文件内容的 SHA-256 | `a3f0…` |
| `frozen_at` | 冻结时间戳 | `h61` |

操作纪律：

1. **冻结后禁止手改**：七字段任何一项都不许直接编辑登记文件——数字要变只能走流程（下条），手改即等同 §6 禁止的手抄。
2. **改数四步**：`freeze_numbers.py unfreeze <claim_id>` → 改源（模型/数据/脚本）→ 重跑生成新 `results/` 产物 → `freeze_numbers.py freeze` 重新登记。四步之外没有"顺手改一下"。
3. **每阶段末跑 `freeze_numbers.py check`**：核对每条 claim 的 `value` 与 `source_sha256` 是否仍与当前 `results/` 一致，输出 stale 清单。
4. **stale 数字禁止进摘要与结论**：check 未通过（源文件哈希已变）的 claim 视为失效，摘要、结论与正文结论句不得引用；须先走改数四步。
5. 与 §6 数字注入衔接：注入脚本从 `results/` 取值，frozen_numbers 保证"注入那一刻源没有变过"——注入前若 check 报 stale，先重跑再注入。

---

## 10. 运行清单与哈希级联失效

> 0.7.5 新增。`scripts/run_manifest.py` 为 0.7.5 配套脚本（可能尚未落盘）。解决"哪次运行产出了这份结果、结果还能不能信"的追溯问题。

**登记规则**：关键求解运行（生成进稿数字或论文图表的那些）用 `scripts/run_manifest.py record` 登记，每次运行四要素：**脚本 / 命令 / 退出码 / 输入输出 SHA-256**。登记由脚本在运行后自动完成，不事后补记、不凭记忆填；声明的脚本/输入/输出文件不存在时 record 直接拒绝登记（exit 2）。record 为读-改-写整体替换，由锁文件串行保护——**record 串行执行，勿并发**（并发冲突 exit 3）。

`run_manifest.py verify` 对照 manifest 重算输入输出哈希，判断每次运行是否仍然有效。防篡改为**逐行自哈希 + 链式双锚**：每条记录带 `self_sha256`（本记录规范化 JSON 的哈希，尾行被改也检出）与 `prev_sha256`（指上一行原文哈希，删改前一行即断链）；记录中任何 `sha256:null` 一律判"记录含缺失文件"错误。

**级联失效规则**：

| 触发 | 后果 | 处置 |
|------|------|------|
| 结果文件哈希变（重跑/手改/部分覆盖） | 依赖它的 frozen claim 全部 stale（§9 check 会捕获） | 走 §9 改数四步 |
| 结果文件哈希变 | 以该结果为数据的图表失效 | 重生成图，图表登记表状态改"待重出" |
| 结果文件哈希变 | 引用该数字的摘要主张失效 | 摘要相应句重写，数字以新 frozen 值为准 |
| 输入数据或求解脚本哈希变 | 该运行及其全部下游产物失效 | 重跑该运行，`record` 新条目，旧条目标记不复用 |

一句话版本：**结果文件哈希一变，依赖它的 frozen claim / 图表 / 摘要主张全部 stale，必须重跑 `freeze_numbers.py check`（或 verify）与 `scripts/trace_claims.py` 重新闭环**，闭环前相关主张不得进稿。

**红线**：绝不用手改 manifest 或 frozen_numbers 登记文件里的 `status`、哈希字段来"消除"stale——状态只能由脚本按实际文件内容判定，手改状态等于伪造审计结论（同 §7 独立验收精神：结论不许由产出方自证）。


---

## 11. skill_issues 台账协议

> v2.3.0 新增（正式化）。2025 华为杯 F 题实测发现 agent 的流程偏差（必停点未问、评分未落盘）没有留痕，复盘时只能靠回忆。本节把"自我纠错留痕"定为固定协议。

**路径**: `cwd/state/skill_issues.md`。Stage 0 初始化工作区骨架时创建——**不存在时从 `<skill>/templates/shared/skill_issues.md` 复制**（模板自带表头与条目格式说明，不用 touch 建零字节空文件），随骨架清单一起落盘。

**登记规则**: agent 每次自我纠错——发现自己流程偏差并修复（例如"该问的必停点没问，补问后登记 checkpoints"、"L1 评分漏跑，补跑 score_artifact.py 落盘"）——追加一条：

```markdown
| S-NN | 日期 | 现象 | 根因 | 临时处理 | 是/否 |
```

（表格行式，与 `templates/shared/skill_issues.md` 模板列结构一致：编号 | 日期 | 现象 | 根因 | 临时处理 | 是否建议入版。）

- `S-NN`: 流水号（S-01, S-02, ...），只追加不改写旧条目（同 §2 修订记录纪律）。
- `是否建议入版`: `是` / `否`。属 skill 设计缺陷（而非本次执行失误）的填"是"。

**终审消费**: Stage 9 终审时读本台账；存在"建议入版"条目时，向用户提示沉淀——列出条目，由用户决定是否反馈进 skill 仓库（用户拍板，agent 不擅自改 skill）。
