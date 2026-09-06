---
stage: 9
name: review
duration_h: 2-6
inputs: [paper.tex, decision_log_full, decision_log.competition]
outputs: [stage.9.{anti_patterns_check, panel_scores, weakest_section, redo_log, red_team_record, skill_issues_consumed, final_pdf_path, submission_ready}]
loads_reference: [competitions/<competition>/anti_patterns.md, competitions/<competition>/rubric_overlay.json, feedback_layer3_panel.md]
loads_template: [templates/latex/<competition>/]
feedback: [L1, L3_5_panel, red_team_in_championship]
next: SUBMIT
---

# Stage 9 — 终稿审核 + 视觉化润色 + Panel 多视角评审

**时长**: 2-6h（按竞赛分支） | **反馈层**: L1 + L3 panel | **冲刺最后一步**

---

## 目标

把 stage 8 的论文从 "完整可读" 推到 "评委想给最高奖"。核心是**多视角对抗审查 + 反模式逐条对照** (按 competition 切换 anti_patterns 与 panel personas)。

图表终审必须加载 `references/figure_skill_bridge.md`, 按 `nature-figure` 的质检思想检查: 核心结论、证据链、字号、坐标单位、图注、颜色一致性、SVG/PDF 可编辑性。

---

## 终审顺序纪律 (0.7.5 评委模拟器)

评审顺序不可调换: **先过资格门, 再冻结标准, 最后才读论文打分**。顺序反了会出现"看完论文倒推标准"的锚定——这是评委行为研究中确认度最高的偏差。无论走完整流程还是"最后 6 小时"极速终审路径, 前置门都必须先过。

```text
Step 0 资格门 (7 条硬规则, 任一不过 → 不具备获奖资格, 不打分不修分)
  ↓ 全部通过
Step 1 冻结本题原子扣分清单 (读题后、读论文前写出来)
  ↓ 清单冻结
原有检查流程 (极速终审路径 / 操作流程 Step 1-9 / Panel, 编号沿用 0.7.4 原文)
```

### Step 0: 资格门 (qualification gate)

7 条硬规则逐条核对, 每条指向 `references/submission_checklists.md` 的对应节:

| # | 硬规则 | 核对要点 | 指向 |
|---|---|---|---|
| 1 | 承诺书页 | 按当年官方模板, 签名齐全 | `submission_checklists.md` 对应竞赛节 |
| 2 | 编号页 | 竞赛系统统一生成, 位置正确 | 同上 |
| 3 | 摘要独占页 | 中文赛首页摘要独立成页; mcm 为 Summary Sheet | `submission_checklists.md` 通用终检 10 条 #7 |
| 4 | 页码起算 | 页码从正文首页起算; 摘要/承诺书/编号页是否计入页数按当年模板 | 对应竞赛节 + LaTeX 模板 |
| 5 | 匿名性 | 正文/页眉/图例/代码注释无队号以外的身份信息 | 通用终检 10 条 #6 + 对应竞赛节 |
| 6 | 页数 | 按竞赛动态口径 (0.7.4, 不回退): mcm 总 PDF ≤25 页 (含附录) 为硬规则; 中文竞赛按当年通知, 通知未明确硬上限时仅提示不计入门 | 通用终检 10 条 #1 |
| 7 | 引用合规 | 参考文献格式统一; AI 使用披露按当年通知 | 对应竞赛节 (mcm AI 使用报告行) |

任一条不过 → 输出结论 **"不具备获奖资格"**, 列出未过条目与修复动作, 直接返回用户; **不进入打分, 不做分数修补**。资格是入场券不是扣分项——格式再好、模型再新都救不回资格缺失。

当 `competition=huaweibei` 时, 资格门前必须先重读 `competitions/huaweibei/current_rules.md` 并核对 Last verified 日期戳 (协议见该文件; 逾期未核验则先提示用户人工核验官方规则)。

### Step 1: 冻结本题原子扣分清单

读题 (stage 2 产出) 之后、读论文之前, 先把本题的原子检查清单写下来并冻结:

- 每个评分块拆到**原子标准**粒度: 一条标准只检查一件事, 可用"是/否"判定
- 清单写入 `state/judge_deduction_checklist.json` (或 `decision_log.stages.9.deduction_checklist`), 冻结后评审期内不得增删改
- 评审中确需补充标准 → 只能以"追加项"记录并标注补充理由, 不得用它倒推已评块的分数
- 模板与扣分分档见下节"评委模拟器评分范式"

---

## 输入

- `paper.tex` (stage 8 产出)
- 全部 figures/ tables/
- decision_log 全部
- **按 competition 加载** (路径: `<skill>/competitions/<decision_log.competition>/`):
  - `anti_patterns.md`（逐条对照，使用当前竞赛独立文件）
  - `rubric_overlay.json` 的 `panel_personas`（研究生赛额外检查竞赛键、奖项身份和证据边界）
- `config/rating_contract.json`（统一评分、证据政策和硬失败规则）
- `state/paper_plan.json` 与 `state/evidence_trace.json`（动态骨架和结果证据链）
- `state/skill_issues.md`（自我纠错台账, workspace_protocol §11——终审必读，见 Step 8）

当 `competition=huaweibei` 时，必须确认当前知识、案例、统计和奖项字段均来自 `competitions/huaweibei/`，并检查 2022—2025 未被推测为数模之星提名。

终审前由 agent 运行 `scripts/trace_claims.py --input state/paper_plan.json --strict`。若 `abstract_gate` 不是 `pass`，先修缺失结果或验证，不进入终稿 panel。

## 产出

- 最终 `paper.pdf` (xelatex 编译完成)
- L3 panel 5 视角评分 + 瓶颈段一次重做
- (championship) red-team 攻击与回应记录

---

## 评委模拟器评分范式 (0.7.5 扣分制)

评委行为研究的一致结论: 真实评委是**扣分制**而非给分制——从基准分往下找错, 找到才扣。终审引入扣分制口径, 作为 Panelist 5 (评委视角) 与 red-team 的算术底座; L3 panel 的 1-10 分 schema 与 `config/rating_contract.json` 的 `score_scale` 不变, 两套口径并行记录。

### 原子扣分表 (模板)

| 块 | 原子标准 | 权重 W | 可得上限 (0.90×W) | 扣分 | 证据位置 |
|---|---|---|---|---|---|
| 摘要 | 每问给方法 + 关键结果 + 验证方式 | 20 | 18.0 | 1-2-3 分档 | p.1 摘要第 X 段 |
| 模型 | 每个子问题有明确数学对象、约束与假设支撑 | 25 | 22.5 | 1-2-3 分档 | §5.Y, p.N |
| 求解 | 算法可行、结果可复现、复杂度合理 | 20 | 18.0 | 1-2-3 分档 | §5/附录, p.N |
| 验证 | 灵敏度/误差/守恒审计至少一类且量化 | 15 | 13.5 | 1-2-3 分档 | §6, p.N |
| 写作 | 图表自明、符号一致、章节闭环、引用规范 | 20 | 18.0 | 1-2-3 分档 | 全文 |

权重 W 按本题冻结的原子清单配置, 上表为缺省参考。

**扣分分档** (每笔扣分对应一档, 单条标准最多扣 3):

| 档 | 定义 | 典型例子 |
|---|---|---|
| -1 | 轻微缺失 | 表述不清、图注不完整、格式小瑕疵, 不影响结论 |
| -2 | 实质缺失或不一致 | 摘要与正文结果矛盾、缺验证、假设无支撑 |
| -3 | 核心错误 | 模型对象错、结果不可信、答非所问、解不可行 |

**算术可复现**: 每笔扣分必须能指到具体页码/段落 (证据位置列), 无法指认证据的扣分无效。块得分 = max(0, 0.90×W − Σ该块扣分); 原始分 = Σ块得分。

### 评委从不给满分 (90% 封顶)

数值条目的可得分上限 = 权重 × 0.90 (`config/rating_contract.json` 的 `judge_reserve_cap`)。某块扣分为 0 且得分已达上限时, 标注 **"评委满分保留"**——这是评委群体的保留分行为, 不是论文缺陷; 不要为冲满分而对已达上限的块过度润色, 边际收益应投向仍被扣分的块。

### 格式是全局乘数, 不是并列维度

```text
最终分 = 原始分 × clamp((格式分 + 10) / 20, 0, 1),   格式分 ∈ [-10, +10]
```

| 格式分 | 乘数 | 效果 |
|---|---|---|
| +10 (格式优秀) | 1.00 | 封顶, 格式好不额外加分 |
| 0 (中性的底) | 0.50 | 内容分已折半 |
| -10 (格式灾难) | 0.00 | 全部内容分清零 |

示例: 原始分 85, 格式分 +8 → 85 × 0.90 = 76.5; 格式分 +4 → 85 × 0.70 = 59.5; 格式分 -4 → 85 × 0.30 = 25.5。含义: 格式混乱会连带压低评委对全部内容块的判断, 终审期修格式的边际收益通常高于再改模型。

### 校准与目标线

| 锚点 (huaweibei, 评委行为研究) | 含义 |
|---|---|
| 80+/100 (扣分制口径) | ≈ 前 2%, 国一名义区间 |
| 65-79 | ≈ 前 13%, 国一/国二边界带 |
| 内部冲国一目标线 | 扣分制口径 80/100 |

- 研究生赛 (huaweibei) 按此锚校准; 其他竞赛按 `references/submission_checklists.md` 与各自 `rubric_overlay.json`, **禁止跨赛套用分布**
- 评委 (panelist) 不应看到目标线与阈值——盲评隔离规则见 `feedback_layer3_panel.md` §盲评信息隔离与冲突裁决; 锚点只供编排方与用户解读分数

### 两个必查项

1. **疑似泄漏检测**: 结果好得离谱 (相对误差远好于官方锚带、精度逼近信息论下界、排序与官方答案完全一致) → 标记"疑似泄漏", 检查是否用了测试集标签、未来信息或官方结果。查明前该块按 0 分挂起, 不奖励高分。
2. **创新盲区披露**: 评审结论必须附声明"本评审按常见获奖模式校准, 可能低估非常规原创路径"。评委模拟器对非常规方法容易误判为不规范, 是否保留该路径由用户终裁。

### 四条通用负锚点 (跨题通用)

| # | 负锚点 | 判定 | 处理 |
|---|---|---|---|
| 1 | 可行先于最优 | 解违反硬约束 (不可行) 却在讨论最优性 | 求解块 -3; 最优性论证作废 |
| 2 | 守恒/平衡律审计 | 质量/能量/流量/资金等守恒或平衡关系不闭合 | 对应块 -2 起, 直至修复 |
| 3 | 信息可观测性 | 用了题设不可知信息 (未来数据/未公开标签/隐含答案) | 解作废, 按核心错误 -3 |
| 4 | 约束数据几何 | 成分/比例数据 (逐行和为常数) 未做 log-ratio 等变换就直接上通用统计 (相关/回归/PCA), 产生伪结论 | 统计结论作废, 验证块 -2 起 |

---

## 最后 6 小时极速终审

当用户说"最后 6 小时"、"马上提交"、"只做最终检查"时, 先走 30-60 分钟极速终审, 不启动完整长 panel。

优先级固定:
1. **摘要结果证据**: 是否逐问说明方法、结果、验证和边界；可量化任务必须给关键数值或排序结论。
2. **图表解释**: 核心图表是否有坐标、单位、图注, 正文是否解释图表说明了什么。
3. **符号一致**: 符号表、公式、图表、正文变量名是否一致。
4. **结论对应题问**: 每一问是否有明确回答, 不是只展示模型过程。
5. **高危反模式**: 对照 `<comp>/anti_patterns.md`, 只抓 high-severity。

输出格式:

```text
提交风险: 低/中/高

必须立即修:
1. <问题> — <怎么修, 预计耗时>
2. ...

可以暂缓:
1. <问题> — <原因>

提交前最后动作:
- <编译/页数/文件名/附件检查>
```

如果风险为高, 必须给用户 `1-5` 编号菜单选择"先修摘要/先修图表/先修符号/先修结论/让我决定"。

---

## 操作流程

### Step 1: 反模式逐条对照 (45 min) ⭐

**强制读** `<skill>/competitions/<competition>/anti_patterns.md`, 按本竞赛条目逐项打勾:

```
A. 摘要类 (5 条)
[ ] A1. 摘要有未追踪结果? → 逐问绑定 result、validation 和 figure
[ ] A2. 摘要不分段? → 5 段
[ ] A3. 摘要与论文不符? → 交叉对照
[ ] A4. 关键词低质量? → 检查
[ ] A5. 摘要信息密度异常? → 按当前竞赛可靠样本分位校准，不设统一硬字数

B. 假设与符号 (6 条)
[ ] B1. 假设无支撑? → 全有
[ ] B2. 假设过多? → ≤7
[ ] ...

C. 模型选型 (5 条)
[ ] ...

D. 求解 (5 条)
[ ] D1. 代码无注释? → 中文注释
[ ] ...

(E-J 共 16 条同样)

E. 结果分析 (4 条)
F. 灵敏度 (4 条)
G. 子问题协调 (2 条)
H. 评价 (3 条)
I. 写作呈现 (5 条)
J. 流程协作 (3 条)
```

每条:
- 命中 high-severity → 立即修
- 命中 medium → 标记, panel 后再决定是否修
- 通过 → ✅

### Step 2: 视觉化润色 (45 min)

**图**:
- 字号 ≥9pt? (anti_pattern E3)
- 配色以 `references/color_typology.md` 为准 (色板/灰度校验/语义绑定), 不直接使用 seaborn 默认或 tableau 默认
- 标题简短信息密度高 (e.g., "图 5: 多变量 LHS 灵敏度散点矩阵")
- 横纵轴标签 + 单位
- legend 位置不遮挡
- Type 3 论文图是否都有 `claim_supported`、`source_artifact`、`caption`
- 是否存在 Type 1 诊断图误放进正文
- 同一模型/方法在全文是否保持同一颜色
- 色板一致性 + 灰度可区分 (对照 `references/color_typology.md` 硬规则, `palettes.grayscale_check` 校验)

**表**:
- LaTeX booktabs (`\toprule \midrule \bottomrule`)
- 数值对齐 (千分位、小数位统一)
- 单位放在表头或单独列

**公式**:
- 编号格式统一 ((5.1) 还是 (5.1.1)?)
- 长公式分行, 用 `align`
- 关键公式给文字解释

**全文一致性**:
- 字体: 西文 Times / 中文宋体 / 标题黑体 (`templates/latex/cumcm/main.tex` 自写 ctexart 默认)
- 段间距: 1.0 倍
- 双倍行距 / 1.5 倍 (按官方要求)

### Step 3: L3 5 视角 Panel (1h) ⭐ 核心

完整 5 视角定义、JSON schema、聚合器、定向重跑逻辑见 **`references/feedback_layer3_panel.md`** (单一权威源, 不在此重复)。

Panelist 5 (评委视角) 在本轮按上文"评委模拟器评分范式"以扣分制口径给出 0-100 扣分明细 (算术可复现), 与既有 1-10 schema 分数并行记录; prompt 注入遵守 `feedback_layer3_panel.md` §盲评信息隔离与冲突裁决 (不给阈值、不给他人输出、verdict 由编排方重算)。

**调用范式** (Claude 在此 stage 实际操作):

```
单条消息内并发 5 个 Agent 子代理 (subagent_type=general-purpose):

Agent 1 → prompt: "<feedback_layer3_panel.md §Panelist 1 数学严谨视角的 prompt + paper.tex 内容>"
Agent 2 → prompt: "<§Panelist 2 模型创新视角>"
Agent 3 → prompt: "<§Panelist 3 代码正确视角>"
Agent 4 → prompt: "<§Panelist 4 写作呈现视角>"
Agent 5 → prompt: "<§Panelist 5 评委视角 — 最关键>"

每个 Agent 独立返回一份 JSON (按 layer3 schema), 主流程聚合。
```

**降级方案**: 若环境不允许并发子代理, 改为串行但**每个 panelist 单独 conversation**:
- 每个 panelist 起新 conversation, 加载自己的 prompt + paper, 输出 JSON 文件
- 不同 panelist 之间不共享 context (避免互相污染)
- 主进程读 5 个 JSON 文件做聚合

不论并发还是串行, **聚合逻辑** 见 `feedback_layer3_panel.md` "聚合器" 节。

#### 聚合: 找瓶颈段

```python
panelist_scores = [...]  # 5 份
overall_min = min(panelist_scores, key=lambda p: p["mean_score"])
weakest_panelist = overall_min["panelist"]
weakest_concerns = overall_min["must_fix"]

# 把 must_fix 映射回阶段
mapped_stages = map_concerns_to_stages(weakest_concerns)
# e.g., "代码注释" → stage 8 §附录
# e.g., "灵敏度仅 2 参数" → stage 6
```

### Step 4: 定向重跑瓶颈段 (45 min)

只针对 panel 找出的 must_fix 修, 不重做整个阶段:

```
def targeted_redo(weakest_concerns, paper_tex):
    for concern in weakest_concerns:
        if concern.severity == "high":
            # diff-only 修订
            patch = generate_patch(concern, paper_tex)
            paper_tex = apply_patch(paper_tex, patch)
        elif concern.severity == "medium":
            log(concern)  # 记录但暂不修, 时间紧时跳过
    return paper_tex
```

### Step 5: 二次 Panel (15 min)

重做后再跑一次 panel (只对修订段落):
- 若 panelist 5 (评委视角) 评分上升 → 收工
- 若仍未达标且时间预算用尽 → 提交当前版本

### Step 6: (championship) Red-team 终极攻击 (30 min)

```
你是国赛历史上最严苛的评委, 你的任务是给这篇论文找出 ≥3 个 reject 理由,
并模拟你会写在评分表上的批注。然后, 论文作者(你扮演)给出 100 字以内的反驳。
```

输出:
```json
{
  "attacks": [
    {"point": "...", "reviewer_note": "...", "rebuttal": "..."},
    ...
  ]
}
```

如反驳力弱 → 修, 如反驳有力 → 在 §7 评价节加一条"潜在质疑回应"。

### Step 7: xelatex 编译 + PDF 输出 (15 min)

```bash
cd <工作区>/paper_workspace/
xelatex paper.tex
xelatex paper.tex   # 二编以解决目录与交叉引用
xelatex paper.tex   # 三编 (保险)
```

检查:
- [ ] PDF 页数按 competition 查 `references/submission_checklists.md` 对应节: mcm 总 PDF ≤ 25 页 (含附录, 以当年通知为准); 中文竞赛无硬页数时按当年通知, 不作硬阻断仅提示
- [ ] 无未解决的 `??` 交叉引用
- [ ] 无 underfull/overfull 大量警告
- [ ] PDF 可正常打开

### Step 8: skill_issues 台账沉淀 (5 min, v2.3.0)

读 `state/skill_issues.md` 台账（不存在则提示跳过）：

1. 筛出"是否建议入版 = 是"的条目（属 skill 设计缺陷，而非本次执行失误）。
2. 存在时向用户给编号菜单：`1) 逐条确认沉淀到 skill 仓库（反馈给维护者）  2) 仅保留台账留痕  3) 让我决定`——**用户拍板，agent 不擅自改 skill 仓库**。
3. 用户确认沉淀的条目，整理为条目清单（编号/现象/根因）写入 `state/` 下的反馈文件或按用户指定的渠道交付；台账本身不改写旧条目。

**时序硬约束**: `submission_ready=true` 必须在本步台账消费完成之后才写入（Step 9）——终审没读完自我纠错台账不算结束。

### Step 9: 最终输出 (5 min)

在 Step 8 台账消费完成后，写入 `decision_log.stages.9`:
```json
{
  "anti_patterns_check": {"total": "<按竞赛 anti_patterns 条目数>", "passed": 30, "fixed": 2, "deferred": 0},
  "panel_scores": {
    "panelist_1_math": {...},
    "panelist_2_innovation": {...},
    "panelist_3_code": {...},
    "panelist_4_writing": {...},
    "panelist_5_judge": {...}
  },
  "weakest_section": "...",
  "redo_log": [...],
  "red_team_record": [...],
  "final_pdf_path": "paper.pdf",
  "skill_issues_consumed": true,
  "submission_ready": true
}
```

---

## L3 Panel 退出条件

- panelist 5 (评委视角) verdict ∈ {"first", "second"} → 提交
- 若 "third" 但时间预算耗尽 → 提交 + 标记 (没办法)
- 若 "first" 且 mean ≥ 9.0 → 庆祝 🎉

## L1 Stage Rubric

| 维度 | 满分 |
|------|-----|
| 1. 反模式覆盖 | 32/32 通过或 ≥30 |
| 2. 视觉一致性 | 字号/配色/字体全统一 |
| 3. Panel 一致性 | 5 视角 mean ≥ 8 |
| 4. 瓶颈处理 | weakest must_fix 已修 |
| 5. PDF 编译 | 无错误; 页数按 competition 查 `submission_checklists.md` (mcm 总 PDF ≤ 25 含附录; 中文竞赛按当年通知, 不作硬阻断) |

## 退出条件 (整个 skill 终点)

1. 本竞赛 anti_patterns 全部通过或高危项清零
2. L3 panel mean ≥ 8, panelist 5 verdict ≥ "second" (理想 "first")
3. PDF 编译成功
4. (championship) red-team 攻击全部有可信回应
5. decision_log.stages.9.submission_ready == true

→ **提交!**
