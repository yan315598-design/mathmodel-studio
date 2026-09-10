# 域级 Playbook 层（v2.5.0 新增）

## 定位

`distilled_modeling.md` 回答"这个赛题风险属于哪类、优先走什么路线"；本层回答"**这个域里高手具体做了什么动作、基线为什么不够**"。两者是分层关系：先按八类风险分类命中本层，再用动作清单补充 stage 3 候选生成，**不替代缺口驱动选型**。

- 本层是**新增层**：不覆盖 distilled_modeling / distilled_figures 等任何既有蒸馏文件。
- 消费方：stage 1 选题命中提示（该题属哪个域）、stage 3 选型（动作清单作为候选生成输入之一）、stage 5 图表组合参考、stage 8 写作侧重。

## 域命名纪律

复用 `../distilled_modeling.md` 八类风险分类命名，不另起炉灶。当前例外一处：**信号诊断**为八类外新增域（2025 E 题证据充分而八类无信号处理类目），其余扩域时优先对齐八类名。

| 域 | 文件 | 证据基础 |
|---|---|---|
| 信号诊断 | `signal_diagnosis.md` | E 题五轮 A/B（analysis/e_ab_test）+ 优秀论文深读（analysis/e_papers）+ mechanism_reviews E×3 |
| 空间几何 | `spatial_geometry.md` | F 题诊断（modeling_gap_review）+ Q1 试点（q1_pilot）+ mechanism_reviews F×2 |
| 调度优化 | `scheduling_optimization.md` | 33 篇深读（papers/manual_paper_reviews.json）中调度类论文提取 |

## 六节格式契约（每份 playbook 必须齐）

1. **触发条件**：什么题目特征/数据形态适用本域。
2. **常见翻车点**：必须来自实证（我方实验或论文审读发现），不写通用套话。
3. **惊艳动作清单**（核心节）：每条五要素——基线在哪失效 → 机制 → 前提/接口 → 反例 → 迁移边界；每条标注**证据来源**（论文N / 我方实验 / 双向）与 review_status（proposed / source_checked / locally_tested）。
4. **图表组合**：该域四层证据（结构/机制/结果/可信边界）各画什么；遵守文末图内标注纪律。
5. **验证设计**：验证动作与该域风险一一对应。
6. **写作重点**：该域摘要/正文侧重。

## 证据纪律（红线）

- 答不出"基线在哪失效"的动作不进 playbook。
- 不写配额语言（"至少 N 个动作/翻车点"）；条目数按证据定，动作数不足就少写。
- 论文声称与本地复核分开标注；不搬论文数值/原句。
- 可机制化的条目同时并入 `../cases/mechanism_reviews.json`（`python -m pytest tests/test_mechanism_reviews.py -q` 必须过）。

## 图内标注纪律（所有 playbook 图表节共用，v2.5.0）

对齐优秀论文/期刊惯例，数据图（Type 3）**图内不放图名与说明文字，图名和结论写进 caption**：

- **保留**：轴标签（含单位）、刻度与刻度标签、图例、多面板标号 (a)(b)(c)、必要参考线与关键点标记（全文 ≤3 处，且每处在正文有对应论证句）。
- **不放**：图题（matplotlib 的 suptitle / 单面板 set_title）、结论句、大段说明文字、数据来源注、装饰性边框/背景色块。
- **示意图豁免**：技术路线图/流程图/框架图的标题条是版式组成部分，不受本条约束（走 figqa `--allow-box-labels` 通道；该参数只豁免示意图盒内文字，不关闭 figure_lint R8）。若示意图仍被 figure_lint R8 检出（如 matplotlib 直出示意图），用 `--allow-infigure-title` 逃生门。
- **panel 短标签**：多面板图各 panel 允许 ≤6 个中文字符当量的轴含义短标签（如 "ROC"、"残差"），超出部分移入 caption。
