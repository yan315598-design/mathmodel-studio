# 实验比较 v2

只有跨任务、实例内重复、多目标或未知成本场景使用 `experiments-2`；`experiments-1` 输入/输出和推荐排序不变。命令仍是 compare_experiments.py，不训练模型。

## 协议

protocol 必含 `task`（prediction/optimization/numerical）、`dataset_sha256`、`evaluation_role`、正数 `budget_s`、非空唯一的 `instances` 与 `repeats`、`objectives`。

objectives 每项为 `{name, direction: min|max, unit}`，名字唯一。所有候选必须使用完全相同的 protocol，每个实例与重复组合恰有一条 run；科学指标缺失/非有限值拒绝。

prediction 还须 `evaluation_role=validation`、SHA-256 `split_id`、`split={unit: sample|group|time, train: [...], validation: [...]}`。ID 不重叠；time 需可排序的统一数值或规范时间，训练全部早于验证。group 的 ID 指原文件/实体，不是切窗。工具可查清单矛盾，不能证明真实训练未泄漏；哈希快照与模型运行仍须证据链。

optimization/numerical 用 `evaluation_role=benchmark`，不要求虚构训练划分。数值任务目标可为误差，实例可为不同网格/步长，但不同实例不混算稳定性。

candidate 含唯一 `id`、`status=completed`、protocol 副本、非空 interpretability 说明及 runs。run 为：

```json
{"instance":"case1","repeat":"seed1","metrics":{"error":0.01},
 "feasible":true,"elapsed_s":1.2,"peak_memory_mb":null,
 "evidence":{"path":"result.json","sha256":"<actual SHA-256>"}}
```

时间/内存 null 或缺省为 unknown，不补零；预算核查只在时间已测时成立。不可行/超时保留排除原因。interpretability 是人工决策依据，不冒称已量化。

## 结果

comparison-2 的 `ranking` 保留可遍历入口，但 `ranking_kind=unordered per-instance summaries` 明确它不是完整排名。每个实例/目标独立报告均值、样本标准差、重复数；单次标准差为 null。

`pareto_front` 在所有实例-目标坐标上按方向判非支配，不擅自归一化或标量化。多个非支配候选不推冠军；任何成本缺测不产生完整推荐。唯一非支配候选且成本完整时，只给 provisional 推荐。想采用权重/容差或解释性成本权衡，先记录科学决策后独立分析，不偷偷改变 v1。

开发包包含 test_experiment_v2 的可运行输入构造与正反例；正式报告只读取真实测量及匹配哈希文件。
