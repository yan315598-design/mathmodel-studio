# 华数杯案例检索

## 数据范围

- 2020—2025 共 18 个题级案例。
- 2020—2022 无本地优秀论文，证据等级为 `problem_summary_only`。
- 2023—2025 每题关联两篇优秀论文的蒸馏模式，证据等级为 `paper_pattern`。
- `S1-S4` 是从题型知识提炼的任务链，不是原题逐问转录。

## 调用

由 agent 运行：

```bash
python scripts/retrieve_cases.py --competition huashubei --level both --query "<题面或子问描述>"
```

需要跨赛参考时使用 `--competition all`，但输出中的 `competition`、`evidence_level` 和 `transfer_boundary` 必须保留。

## 使用边界

- 可以迁移：问题抽象、模型接口、假设风险、验证方法、图表角色和章节闭环。
- 不可迁移：历史数值、参数、权重、阈值、结论、原句和奖项判断。
- 新题的逐问结构必须回到当前题面重建，不以 `S1-S4` 代替题面。
