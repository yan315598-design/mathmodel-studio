# CUMCM 相似题检索协议

## 使用时机

进入 Stage 1、2、3 时，先依据题面内容检索案例，再做题型判断和模型选择。题号字母只作来源标识，不作题型依据。

## 检索步骤

1. 从题面提取对象、输入、输出、约束、不确定性、评价指标和子问依赖。
2. 用完整题面文本或 100—500 字结构化摘要运行：

```powershell
python scripts/retrieve_cumcm_cases.py --index competitions/cumcm/cases/index.json --problem-file problem.txt --top-k 5
```

检索器会自动读取索引同目录下的 `manual_review_annotations.json`。该覆盖层包含 25 题、64 篇本地论文的跨论文人工复核；若文件不存在，检索器保持兼容并退回基础索引。也可显式指定：

```powershell
python scripts/retrieve_cumcm_cases.py `
  --index competitions/cumcm/cases/index.json `
  --manual-review competitions/cumcm/cases/manual_review_annotations.json `
  --problem-file problem.txt --top-k 5
```

3. 至少比较前 3 个案例。优先看“问题本质”和约束结构，不因领域名相同就直接迁移。
4. 从命中案例读取逐问依赖、跨论文路线、假设风险、必做验证、图表叙事和写作骨架；再按新题数据规模与假设重新选择。
5. 历史结果分歧只用于识别口径风险，禁止复制历史数值、参数、假设和论文原句。
6. 在模型选择记录中写明：采用的结构、拒绝的结构、迁移边界、对应案例 ID 和 evidence ID。

## 可信度

- `high`：同题有至少 3 篇论文证据，可用于观察历史分歧和共性。
- `medium`：有 1—2 篇论文证据，只用于候选生成。
- `problem_only`：只有题面；推荐链来自题面结构的人工归纳，不代表获奖方案。

所有案例都只能迁移结构，不能复制数值、结论、假设或论文表述。检索分数用于排序，不是模型正确率。

人工复核状态：

- `reviewed`：已比较逐问依赖、论文路线、结果分歧、假设、验证、图表和写作结构。
- `single_paper` 语义由 `reviewed_paper_count=1` 表示：只能作为可复算路线，不能声称跨论文共识。
- `missing_questions`：只表示 OCR 没有稳定切出对应摘要段，不表示论文没有作答。

## 选择规则

| 新题信号 | 优先查的知识文件 | 典型案例 |
|---|---|---|
| 受力、能量、光学、传播、守恒 | `distilled_modeling.md` 物理机理 | `cumcm_2022_A`、`cumcm_2023_A`、`cumcm_2025_B` |
| 轨迹、曲线、定位、碰撞、覆盖 | 几何与运动学 | `cumcm_2022_B`、`cumcm_2024_A`、`cumcm_2025_A` |
| 计划、调度、分配、策略、资源 | 优化与调度 | `cumcm_2021_C`、`cumcm_2024_B`、`cumcm_2024_C` |
| 时序、需求、风险、趋势 | 统计预测 | `cumcm_2023_C`、`cumcm_2023_E`、`cumcm_2025_C` |
| 指标、评分、排名 | 评价与排序 | 与其他主任务联合检索，不单独套权重法 |
| 路网、巷道、连通、逃生 | 网络与路径 | `cumcm_2025_D`、`cumcm_2024_E` |
| 光谱、波形、干涉、频域 | 信号处理 | `cumcm_2021_E`、`cumcm_2025_B` |
| 报文、时隙、共享、成功概率 | 通信调度 | `cumcm_2022_D` |
| 视频、关键点、类别、异常 | 图像识别 | `cumcm_2021_E`、`cumcm_2025_E` |
| 随机命中、离散事件、情景 | 仿真模拟 | `cumcm_2024_D`、`cumcm_2024_B` |

## 输出模板

```text
题面本质：<一句话>
相似案例：<ID 1>、<ID 2>、<ID 3>
可迁移结构：<模型链或约束结构>
不可迁移内容：<参数、假设、数据分布等>
候选方案：<至少三个>
必做验证：<与风险对应>
图表叙事：<机制—中间层—结果—可信边界>
写作骨架：<为什么—模型—求解—结果—验证—回答>
```
