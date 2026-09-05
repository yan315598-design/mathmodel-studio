# mathmodel-studio（数模工坊）

> 数学建模竞赛的论文生产流程 skill：从审题、建模到终审，按阶段带着你走完一篇可提交的论文。支持华为杯（研究生赛）、CUMCM 国赛、华数杯、MCM/ICM 美赛、电工杯、APMCM 亚太杯中文赛。

[![Version](https://img.shields.io/badge/version-v2.2.0-blueviolet)](#开发日志)
[![Competitions](https://img.shields.io/badge/competitions-6-orange)](#支持的竞赛)
[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](./templates/shared/requirements.txt)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#license)

---

## 这是什么

数学建模竞赛要在 3-4 天内完成选题、建模、求解、验证、写作、提交一整篇论文，最常见的失败不是模型不会建，而是流程崩盘：摘要里的数字和正文对不上、图表风格混乱、某问的验证忘了做、截止前两小时才发现格式违规。

这个 skill 把整场比赛拆成可检查的阶段，每个阶段自带验收标准：agent 按流程陪你走，每一步产出什么、什么叫做完、什么情况下必须停下来问你，都有明确规定。

## 核心优势

**1. 真实蒸馏的竞赛知识库，不是拍脑袋的"经验"**
华为杯 2021—2025 全部 30 题 + 190 篇优秀论文（12458 页）逐题人工复核，33 篇逐篇深读（12 篇 2021 数模之星提名 + 21 篇 2025 优秀论文选全量）。蒸馏的对象是**结构、解法与表达习惯**：每题的问题本质、逐问依赖、候选路线比较、假设风险与必做验证、图表叙事、写作骨架（`competitions/*/cases/` 与 `distilled_*.md`）；深读论文的章节逻辑、推导叙事与"摘要六要素"写作纪律（`writing_voice.md` + 题型分册 `writing_playbook.md` + 正反例库 `writing_examples.md`）；以及获奖论文的反模式清单。每条知识的来源文件都有 SHA-256 登记，可用 `scripts/distill_huaweibei_cases.py verify-manifest` 机器核验。国赛 33 篇可核验论文 + 25 个逐题案例、华数杯 18 题 18 篇同样独立成库。

**2. 评委模拟器终审**
提交前过一道模拟评审：资格硬规则（如"摘要主张必须可追踪到结果"）任一不过即判不具备获奖资格；通过资格门后按原子扣分清单评分，多席位评委盲评、分差过大自动重派。终审不看感觉，看单子。

**3. 论文数字全部可回溯**
每个结果数字与产出它的源文件做 SHA-256 绑定（`freeze_numbers.py`），源文件一变数字自动标 stale；`trace_claims.py` 审计"问题→模型→结果→验证→图→摘要主张"的证据链，未闭环的主张进不了摘要；`consistency_audit.py` 查未冻结数字、摘要与结论打架、图表断链、符号脱节。

**4. 图表有硬门，不是"能看就行"**
17 件数据图 + 4 件示意图 + 6 件 drawio 可编辑模板全部自写，统一色板（含色盲安全与期刊色板）；`figqa.py` 做像素级渲染碰撞检测（文字越界/压线/重叠直接报 FAIL），`drawio_check.py` 做版式体检，图表不合格过不了门。

**5. 全程问答式，用户不当运维**
选题、选模型、是否通过质量门，全部给编号选项，回个数字就推进；每个决策点都有"让我决定（推荐 X）"兜底。用户不需要敲命令、不需要编辑 JSON，状态文件由 agent 自动读写。

**6. 可回归、可复现**
75 个单元测试 + holdout 评测协议（剔除某一届案例再试跑，模拟真实新题）+ 蒸馏流水线可重跑。改一版 prompt 是变好还是变坏，跑一遍 `evals/run_eval.py` 对比就知道。

## 流程：5 幕 10 步 + 2 道质量门

| 幕 | 步骤 | 干什么 |
|---|---|---|
| 一、备战与选题 | 赛前兵检 → 启动 → 选题 | 模板预编译与求解器冒烟（赛前跑一次）；定竞赛定题；多题对比矩阵 |
| 二、审题与选型 | 审题三查 → 模型选型 → 假设符号 | 边界/目标/假设三查防读错题；≥3 条候选路线比较（各带失效边界）后拍板；假设表、符号表冻结 |
| 三、建模求解 | 子问循环 → 稳健性 | 每问"建模→求解→验证→物理解释"循环，验证通过立即写章节草稿卡（write-as-you-solve）；最后做多变量联合扰动 |
| 四、论文成稿 | 模型评价 → 写作组装 | 草稿卡组装成正文（不重写），摘要三遍制（骨架→证据重写→终审润色） |
| 五、终审提交 | 终审 → 打包 | 评委模拟器 + 一致性审计 + 提交清单检查 + zip 打包（含 MD5 与备份） |

**质量门 1**（每步结束）：rubric 五维自评，不过不推进；单问不合格只返修该问，不重做整幕。
**质量门 2**（第五幕）：评委模拟器多席位 panel，资格门 + 扣分制。

**一次实战长这样**：你说"开始建模" → 回答 5 个问题（竞赛/题号/队员/截止/题目 PDF）→ 每幕推进前你会看到本幕产物和自评分 → 卡住时给结构化决策备忘（试过什么/目前最好/下一步选项）→ 终稿前评委模拟器出扣分清单 → 一键打包。

## 支持的竞赛

| 竞赛 | 时长 | 语言 | 数据状态 |
|------|------|------|---------|
| 研究生赛（华为杯） | 100h（2026 通知口径） | 中文 | 本地 2021—2025：30 题 + 190 篇优秀论文 + 33 篇深读（12 提名 + 21 优秀选） |
| 华数杯 | 72h | 中文 | 本地 2020—2025：18 题 + 18 篇 |
| CUMCM 国赛 | 72h | 中文 | 可核验：33 篇论文 + 25 个案例 |
| MCM/ICM 美赛 | 96h | English | seed v0.1（公开评审标准 + 教材共识） |
| 电工杯 | 72h | 中文 | seed v0.1（历年题量估算） |
| APMCM 亚太杯中文赛 | 72h | 中文 | 本地 2024/2025 赛题 + 优秀论文 |

各竞赛的题目、统计、模板严格隔离，联合检索不等于混库。

## LaTeX 模板与图表资产

- **6 套自写竞赛 LaTeX 模板**（`templates/latex/`）：华为杯、国赛、华数杯、美赛、电工杯、亚太杯，全部通过 xelatex/pdflatex 编译验证，无第三方模板许可证风险。
- **27 件自写图表模板**（`templates/figures/`）：数据图 17 件（龙卷风灵敏度/帕累托前沿/泰勒图/云雨图等）、示意图 4 件、drawio 可编辑模板 6 件；另收编 MIT 许可的 diagram-design（39 类展示级 HTML/SVG 图表，供答辩）。
- **起手代码**（`templates/shared/code_starter/`）：优化/预测/评价/分类/仿真五类骨架。

## 论文怎么写、怎么导出

正文以 markdown 为**唯一真源**（`paper_workspace/` 下，写作队员用 Obsidian 或 MarkText 这类免费的所见即所得编辑器即可参与，公式实时预览，不需要记语法）；LaTeX 与 Word 都是它的下游产物：

```text
                  ┌─→ render_paper.py 自动转 tex → xelatex → PDF   （正式提交件）
  md（唯一真源）──┤
    所有修改都在这  └─→ export_docx.py → docx                        （审阅件，给 Word 队员圈批注）
                                   │
                   批注/改动由 agent 读取后合回 ──→ md
```

三条纪律：改论文永远改 md，不手改生成的 tex/docx（下次渲染会被覆盖）；需要精细排版时直接在 md 里写原生 LaTeX 公式/表格，渲染原样通过；终稿最后几小时可"锁版"转纯 tex 手写微调（此后不再从 md 组装）。各赛提交物均为 PDF。

写作队员的编辑器选型（免费，三选一）：

| 编辑器 | 适合谁 | 一句话 |
| --- | --- | --- |
| Obsidian（推荐默认） | 大多数人 | 个人使用免费、持续更新、实时预览模式和 Typora 体验几乎一样，公式渲染好 |
| MarkText | 想要完全开源的 | 免费开源、界面最像 Typora，但项目 2022 年后基本停更，装最新版 0.17.1 够用 |
| VS Code（兜底） | 队里本来就有代码环境 | 自带 Markdown 预览（Ctrl+Shift+V），不用装新东西，但预览和编辑是分开两栏，不是打字即所见 |

## 怎么用

```bash
# Codex / 兼容 agents
git clone https://github.com/yan315598-design/mathmodel-studio.git ~/.agents/skills/mathmodel-studio

# Claude Code
git clone https://github.com/yan315598-design/mathmodel-studio.git ~/.claude/skills/mathmodel-studio

# 装 Python 依赖
pip install -r ~/.agents/skills/mathmodel-studio/templates/shared/requirements.txt
```

装好后直接说"开始建模"，或 `$mathmodel-studio`。也可以只做局部的事："帮我比较 A/B/C 题"、"写摘要"、"最后 6 小时终审论文"、"画一张帕累托前沿图"。

状态全部存在你工作目录的 `state/decision_log.json`，换 harness（Codex ↔ Claude Code）接力不丢进度。`runtime/` 目录另附一个薄 agent runtime 原型（skill 即大脑、litellm 可选依赖、mock 模式可无 key 演示），供二次开发参考。

## 结构

```
SKILL.md                      # 主入口：流程定义 + 加载协议 + 收敛准则
AGENTS.md                     # Codex 项目级入口（harness 差异说明）
competitions/                 # 六个竞赛的特化知识库（案例/摘要模板/反模式/评分覆盖层）
references/                   # stage_00–09 细则、写作与图表规范、反馈层、72h 作战表
templates/latex/              # 6 套自写竞赛 LaTeX 模板
templates/figures/            # 27 件自写图表模板 + 色板 + 质检脚本
scripts/                      # 检索/评分/证据追踪/数字冻结/图表硬门/打包等 20+ 工具
evals/                        # holdout 评测协议与跑分 runner
runtime/                      # 薄 agent runtime 原型
tests/                        # 75 个单元测试
docs/architecture.md          # 架构说明
```

## 三种模式

| 模式 | Token | 耗时 | 适用 |
|------|-------|------|------|
| fast | ≤ 50k | ~30 min | 选题试跑 / sanity check |
| standard（默认） | ≤ 200k | ~6h | 主流程 |
| championship | ≤ 500k | ~12h | 提交前冲刺（含 panel + 校准 + red-team） |

## 数据来源与合规

- 全部模板与脚本为自写或自由许可资产；`competitions/` 下内容为公开赛题与获奖论文的**结构性总结**，不含原文，版权归原作者与组委会。
- 蒸馏的主体是结构、解法、写作与图表设计；摘要长度、页数等统计仅作范围参考（如"摘要明显偏薄"的体检提示），不进评分、不作获奖分数线。样本均为获奖论文、无失败对照，存在幸存者偏差。
- MCM 与电工杯为 seed v0.1，可靠度低于国赛与研究生赛分支，输出会标注。
- 华为杯提名论文身份仅 2021 年 12 篇有目录依据；2022—2025 不推测。

## 开发日志

详细历史见 [CHANGELOG.md](./CHANGELOG.md)（含旧版本号映射表）。

| 版本 | 里程碑 |
|---|---|
| 2.2.0 | 2025 届 21 篇优秀论文深读入库 + 评测装置修复 + 2026 赛制核验 |
| 2.1.0 | docx 审阅件导出 + 审查修复 |
| 2.0.0 | 开源首发：知识库注水修复、写作层重修、可复现蒸馏流水线、evals、runtime 原型 |
| 1.4.0 | 图表体系收口：自写模板 + 质检硬门 |
| 1.0.0 | 全资产自写，许可证干净（MIT） |
| 0.7.5 | 评委模拟器终审、数字冻结 |
| 0.7.2 | 华为杯 190 篇优秀论文深度蒸馏 |
| 0.5.0 | 问答式交互、跨 harness 状态互通 |
| 0.1.0 | 首次搭建 |

## License

MIT（见 LICENSE 文件）。`templates/figures/vendor/diagram-design/` 为上游 MIT 资产；`vendor/scibox-*` 因上游未附 LICENSE 不随仓库分发，详见 `templates/figures/vendor/VENDOR.md`。

发现 bug / 建议欢迎开 issue。
