---
stage: 0
name: kickoff
duration_h: 1
inputs: [user_inputs.{competition, problem_id, team_size, deadline, pdf_path}]
outputs: [stage.0.{team_roles, tools_ready, problem_scan, time_budget_h, collab_protocol, checklist_completed}, root.{competition, task_type}]
loads_reference: [competitions/<competition>/winning_patterns.md, competitions/<competition>/topic_specs.json, competitions/<competition>/README.md]
loads_template: [templates/shared/decision_log.json, templates/shared/requirements.txt]
feedback: [L1]
next: stage_01_problem_selection
---

# Stage 0 — 团队启动与资料预扫

**时长**: 1h | **反馈层**: L1 | **触发**: skill 首次启动 / 用户说"开始建模"

---

## 目标

在题目正式公布前(或公布后立即),把队伍状态调到"上手即可执行",避免后续阶段因协作/工具/角色问题反复返工。

---

## 输入

- 用户提供: 队员数 (默认 3) / 截止时间 / 模式偏好
- (若题目已发布) 题目 PDF 文件路径

## 产出

- `state/decision_log.json` 初始化,问题元信息填好
- 角色分工表 (写入 `decision_log.stages.0.team_roles`)
- 工具就绪 checklist
- 初步问题域识别 (优化 / 预测 / 评价 / 分类 / 仿真 / 综合) → 影响 stage 3

---

## 操作流程

### Step 1: 元信息收集 (5 min) — 问答式

**一次性问 5 题** (Claude Code: 单条 AskUserQuestion; Codex CLI: 5 个编号列表, 见 `references/harness_compat.md` §1):

1. **竞赛** — 主选项: `1) huaweibei 研究生赛  2) huashubei 华数杯  3) cumcm 国赛  4) 其他竞赛  5) 让我决定`；选择 4 后再选 mcm / diangong / apmcm
2. **题号** — 依竞赛动态生成选项 (huaweibei A-F / huashubei A-C / cumcm A-E / mcm A-F / diangong A-B / apmcm A-C / `未公布`)
3. **队员数与各人擅长** — 自由文本 (例: "3 人, 张建模, 李编程, 王写作")
4. **截止时间** — 自由文本 (ISO 字符串或 "距现在 X 小时")
5. **题目 PDF 路径** — 自由文本 ("未公布"亦可)

**禁止**让用户手动编辑 decision_log.json; 拿到答案后由 agent 自动写入。**必停点登记 (v2.3.0)**: 本 5 问是六个必停点之一, 用户作答后写入 `decision_log.checkpoints.kickoff_5q`（`{"status": "answered", "asked_at": "<ISO>", "answer": "<5 问答案摘要>", "source": "chat"}`；source 缺失或非 chat/user_cli 视为未答，check_gate 拦截）; 推进 stage 1 前必须 `python scripts/check_gate.py --gate 0` 放行（见 SKILL.md 必停点协议）。

Codex 首屏固定模板:

```text
启动数学建模工作流, 10 阶段 + 多竞赛, 全程问答式。

【需要你选择: Q1 竞赛】

  1) huaweibei 研究生赛（华为杯）— 中文, A-F 题，字母不固定映射题型
  2) huashubei 华数杯 — 中文, A-C 题
  3) cumcm 国赛 — 中文, A-E 题
  4) 其他竞赛 — 继续选择 mcm / diangong / apmcm
  5) 让我决定 — 按上下文判断，否则先按 cumcm 建立 state

Q2 题号: 回复 A/B/C/... 或"未公布"。
Q3 队员数与擅长: 例 "3 人, 张建模, 李 Python, 王写作"。
Q4 截止时间: 例 "2026-09-07 20:00" 或 "距现在 72 小时"。
Q5 题目 PDF 路径: 回复本地路径或"未公布"。
```

若用户问"为什么没有选择界面 UI", 回答: "Codex 这里通常没有弹窗选择 UI, 所以我用编号菜单代替; 你回复数字即可。" 随后立即给上面的首屏模板, 不让用户改 JSON。

写入:
- `decision_log.competition` ← 第 1 问
- `decision_log.problem_meta.{year, letter, title, deadline_iso, team_size}` ← 第 2-4 问
- `decision_log.events.log` ← 第 5 问 (PDF 路径)

**自动推断** (基于 competition 字段, 加载 `competitions/<comp>/README.md` 与 `topic_specs.json`):
- 时长预算按竞赛 README 和当届通知读取；缺失时才使用历史常见时长
- 写作语言 (huaweibei/huashubei/cumcm/diangong/apmcm 中文 / mcm 英文)
- LaTeX 编译器 (中文分支 xelatex / mcm pdflatex)
- 默认子问题数 (用于 stage 5 时间预算)

`task_type` 字段在 stage 1 解析题面后再填。若 `topic_specs.json.fixed_letter_to_type=false`（如 huaweibei），必须按题面对象、任务、数据、约束和主要风险动态分类，不能从题号字母推断。

### Step 2: 角色分工 (10 min)

强制 3 主责 + 互备:

| 角色 | 主责内容 | 互备 |
|------|---------|------|
| **建模主** | stage 2/3/4/5 主导,数学公式 | 编程主 |
| **编程主** | stage 5 求解、stage 6 灵敏度 | 建模主 |
| **写作主** | stage 8 主导,stage 1/9 协助 | 全员 |

**反模式 J1** (anti_patterns.md): "三人都全栈但都不深" — 拒绝。
强制每人写一句"我对这道题/这个角色的最大顾虑是什么"。

### Step 3: 工具就绪 checklist (15 min)

逐项确认 (bash 验证):

```bash
python --version           # ≥ 3.9

# 完整依赖检查 (一次性安装见 templates/requirements.txt)
python -c "import numpy, scipy, sklearn, cvxpy, matplotlib, pandas, statsmodels, seaborn, SALib, pdfplumber, imblearn"

# 关键 solver 检查 (优化类必备)
python -c "import cvxpy; assert 'GLPK_MI' in cvxpy.installed_solvers(), '需 pip install cvxopt'"

# LaTeX 必备
xelatex --version          # 中文赛模板 (templates/latex/cumcm/main.tex 自写 ctexart) 用 xelatex (非 pdflatex)

which git
```

如缺依赖, 一键安装:
```bash
pip install -r <skill>/templates/shared/requirements.txt
```

**目录初始化** (agent 自动执行, 不要让用户敲命令; 先 cd 到工作区根目录再执行, 不要在工作区下创建字面 `cwd/` 子目录):
```bash
mkdir -p state results figures code paper_workspace _archive
cp <skill>/templates/shared/decision_log.json state/decision_log.json   # 仅当不存在时
cp <skill>/templates/shared/skill_issues.md state/skill_issues.md      # 自我纠错台账 (workspace_protocol.md §11), 仅当不存在时 (模板含表头, 不建零字节空文件)
```

**工作区纪律** (0.7.4, 全文见 `references/workspace_protocol.md`): 上述初始化按协议 §1 执行, 并补齐骨架差异 (`code/`、`_archive/`) 与 `真源.md` SSOT 模板 (协议 §2)。若同目录或父目录检测到同竞赛旧工作区, 先给用户编号菜单确认再初始化:

1. 旧工作区整体移入 `_archive/` 后新建 (推荐)
2. 查看两目录差异后再决定
3. 取消初始化

若 `真源.md` 已存在, 不重建——走协议 §4 会话恢复四步 (读 decision_log → 读真源口径冻结单与修订记录末尾 → 跑数字冻结与运行清单校验 → 向用户报告当前阶段/已冻结/待办 3 条)。

写入 `decision_log.competition` 字段: agent 用 Read + Edit/Write (Claude Code) 或 apply_patch (Codex CLI) 完成, 不要让用户跑 `python -c ...`。

确认 (按 competition 分支):
| competition | LaTeX 模板 | 引擎 | 静态资料 |
|---|---|---|---|
| huaweibei | `<skill>/templates/latex/huaweibei/main.tex` | xelatex | 30 题 + 190 篇论文 + 33 篇深读 (12 篇 2021 提名 + 21 篇 2025 优秀选) |
| huashubei | `<skill>/templates/latex/huashubei/main.tex` | xelatex | 6 届 18 题 + 18 篇优秀论文 |
| cumcm | `<skill>/templates/latex/cumcm/main.tex` | xelatex | 33 篇可核验论文 + 25 个逐题案例 |
| mcm | `<skill>/templates/latex/mcm/main.tex` | pdflatex | seed v0.1 |
| diangong | `<skill>/templates/latex/diangong/main.tex` | xelatex | seed v0.1 |
| apmcm | `<skill>/templates/latex/apmcm/main.tex` | xelatex | 本地 2024/2025 蒸馏 |

### Step 4: 题目预扫 (题目公布后,15 min)

用户提供题目 PDF 后,Claude 用 Read 工具读 PDF (前 5 页) 做快速识别:

输出格式:
```json
{
  "problem_id": "2024-A",
  "domain_keywords": ["调度", "最优化", "时变"],
  "data_attachments": ["附件1: ...", "附件2: ..."],
  "subproblem_count": 3,
  "primary_problem_type": "优化类",
  "secondary_types": ["仿真类"],
  "estimated_difficulty": "medium",
  "data_size_signal": "中等 (附件 ≤ 50MB)"
}
```

写入 `decision_log.events.log`,作为 stage 1 输入。

### Step 5: 时间预算分配 (10 min)

根据 deadline 倒推 (h), 按 competition 分支:

#### CUMCM 国赛 (72h)
| 阶段 | 配额 | 调整建议 |
|-----|------|---------|
| 0 | 1 | 固定 |
| 1 | 3 | 选题难度大 +1h |
| 2 | 3 | 多子问 +1h |
| 3 | 3 | 不熟领域 +1h |
| 4 | 1 | 固定 |
| 5 | 30 (10/子问) | 主体, 保大头 |
| 6 | 3 | 固定 |
| 7 | 2 | 固定 |
| 8 | 20 | 主体, 保大头 |
| 9 | 4 | 固定 |
| buffer | 2 | 应急 |
| **合计** | **72** | |

#### APMCM 亚太杯中文赛 (72h)

- 0-4h: 选题 + 题面与附件预扫
- 4-12h: 问题分解 + 数据/几何/算法路线确定
- 12-42h: 分问题建模、求解、结果图表
- 42-58h: 摘要、正文和图表解释
- 58-72h: 稳健性、终审、排版和提交

#### MCM 美赛 (96h)
| 阶段 | 配额 | 备注 |
|-----|------|------|
| 0 | 1.5 | |
| 1 | 4 | 6 题号选择更复杂 |
| 2 | 3 | |
| 3 | 4 | novel approach 思考时间 |
| 4 | 1 | |
| 5 | 38 (8-10/子问 × 4-5 子问) | 主体 |
| 6 | 3 | sensitivity 必做 |
| 7 | 2 | |
| 8 | 30 | 1-page summary + Letter (D/E/F) 需打磨 |
| 9 | 6 | 终审 + grammar + reproducibility |
| buffer | 3.5 | 应急 |
| **合计** | **96** | |

#### 电工杯 (72h, 但子问 6-8)
| 阶段 | 配额 | 备注 |
|-----|------|------|
| 0 | 1 | |
| 1 | 2 | 题号选择简单 |
| 2 | 3 | 子问多, 分解时间 |
| 3 | 2 | |
| 4 | 1.5 | 数据预处理章节准备 |
| 5 | 36 (4.5-6/子问 × 6-8 子问) | **主问 3-4 详写, 加分 2-3 简写** |
| 6 | 3 | 工程参数扰动 |
| 7 | 2 | |
| 8 | 18 | 25-30 页 |
| 9 | 3 | |
| buffer | 0.5 | 应急 |
| **合计** | **72** | |

如总剩余少于上述, 按比例压缩, 但 stage 5/8 不低于 60% 的默认值。

### Step 6: 协作约定 (5 min)

写入 `decision_log.stages.0.notes`:
- 命名规范: 文件 / 变量 / Python 模块
- 版本控制: git 提交频率 (每 2h 一次)
- 沟通节奏: 每 4h 5 分钟同步
- 求助升级: 卡住超 1h 必须群内 broadcast

---

## L1 Rubric (5 维 × 1-10)

参考 `rubrics.md` Stage 0 节。每维必须 ≥7 才通过。

```json
{
  "stage_id": 0,
  "scores": {
    "1_role_clarity": {...},
    "2_tools_ready": {...},
    "3_time_planning": {...},
    "4_problem_scan": {...},
    "5_collab_protocol": {...}
  }
}
```

## 常见坑 (anti_patterns)

- **J1**: 三人都全栈不深 → 强制角色主责
- **J2**: 选题摇摆 (跳到 stage 1 才出现)
- **J3**: 写作留到最后 → time budget 把 stage 8 提前到 day 2

## 退出条件

1. `decision_log.stages.0.checklist_completed == true`
2. 团队角色明确,工具全员 ready
3. (若题目已发布) 题目预扫完成
4. L1 rubric 全维 ≥7

→ 跳转 `stage_01_problem_selection.md`

---

## 与 Stage 1 的衔接

把 Step 4 的题目预扫 JSON 作为 stage 1 的"上下文输入"传过去,避免重新读题。
