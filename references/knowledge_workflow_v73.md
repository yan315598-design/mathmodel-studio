# v7.3 三赛知识工作流

## 核心原则

- 将 `cumcm`、`huaweibei`、`huashubei` 放在同一检索和写作工作流中。
- 永久隔离竞赛身份、奖项、统计、题面、模板和来源清单。
- 只迁移问题结构、模型接口、验证逻辑、图表角色和章节功能。
- 禁止迁移历史参数、权重、结果、结论和论文原句。

## 1. 联合与子问检索

由 agent 运行：

```bash
python scripts/retrieve_cases.py --competition all --level both --query "<新题描述>" --top-k 5
```

- `--competition`：`cumcm | huaweibei | huashubei | all`。
- `--level`：`case | question | both`。
- 联合结果始终保留 `competition`。
- 当 `--competition all` 且 `top-k >= 3` 时，先保证三赛各至少一条，再按相似度补齐，避免高证据赛种挤掉其他分支。
- 研究生赛的 2021 数模之星提名论文子问使用 `star_paper_full_text`；华数杯蒸馏任务链使用 `paper_pattern` 或 `problem_summary_only`，不得冒充原题逐问。

## 2. Stage 知识包

进入 Stage 1、3、5、8、9 时，由 agent 运行：

```bash
python scripts/build_stage_pack.py --competition <comp|all> --stage <1|3|5|8|9> --query "<新题描述>" --output state/stage_<N>_knowledge.json
```

知识包只保留当前阶段需要的命中案例、子问接口、路线、假设风险、必要验证、图表叙事、写作骨架和 evidence ID，避免把全文证据包装入上下文。

## 3. 动态论文骨架与图表计划

Stage 8 由 agent 运行：

```bash
python scripts/generate_paper_plan.py --stage-pack state/stage_8_knowledge.json --output state/paper_plan.json
```

章节由真实 `question_dependency` 动态生成，不固定复制某篇论文目录。每个子问按以下顺序闭环：

```text
任务与路线选择 -> 变量/约束/模型 -> 算法与中间状态
-> 结果解释与验证 -> 回答题问 -> 传递给下一问的中间量
```

每张图必须包含：

- `role`：结构、机制、结果或可信边界。
- `supports_claim`：唯一主张。
- `upstream_data`：变量、算法输出或实验数据。
- `required_checks`：生成前必须完成的口径、单位、可行性或稳健性检查。

图表数量由论证需要决定，不设固定获奖门槛。

## 4. 论文结果证据追踪

填写 `paper_plan.json.evidence_ledger` 后，由 agent 运行：

```bash
python scripts/trace_claims.py --input state/paper_plan.json --output state/evidence_trace.json --strict
```

每个子问必须形成：

```text
question -> model -> result -> validation -> figure -> abstract_claim
```

任一摘要主张缺结果或验证时，`abstract_gate=block_untraced_claims`，不得进入终稿摘要。

## 5. 统一评分契约

- 共享契约：`config/rating_contract.json`。
- 竞赛差异：`competitions/<comp>/rubric_overlay.json`。
- overlay 只覆盖不同维度和 panel，不复制公共判定规则。
- 经验分位只作校准；华数杯图表数、表格数和正文字数只作观察，不能作为硬阈值。

## 6. 增量更新

先预览，再在明确更新时写入：

```bash
python scripts/update_knowledge.py --source <资料目录>
python scripts/update_knowledge.py --source <资料目录> --apply
```

清单记录 SHA-256、版本和变更历史。只有 `added` 与 `changed` 进入 `to_process`；`unchanged` 不重跑，`removed` 只记录，不自动删除任何文件。
