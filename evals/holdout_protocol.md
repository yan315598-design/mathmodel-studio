# 伪 holdout 协议 (pseudo-holdout protocol)

## 为什么需要

本 skill 的蒸馏语料覆盖 huaweibei **2021-2025 全部 30 题**(索引见
`competitions/huaweibei/cases/index.json`, 每届 6 题、共 190 篇论文的蒸馏结论)。
任何一届题目的题型分解、建模路线、图表角色都在检索可达范围内——
**不剔除直接评测等于开卷考试**: agent 靠检索命中"见过的高度相似案例"得高分,
分数反映的是语料覆盖度而非建模能力, prompt 改动的真实效果被淹没。

伪 holdout = 评测时临时把某一届从检索索引剔除, 模拟"未见过的题"。

## 推荐剔除届

**2024 届**(6 题, 索引内 24 篇论文引用)。理由: 距今最近、题面风格与当前规则
(`competitions/huaweibei/current_rules.md`)衔接; 剔除后仍保留 2021-2023/2025 共
24 题做检索底座, 覆盖面损失最小。

## 操作步骤

1. **构建剔除镜像**(源文件不动, 只写新目录):

   ```bash
   python evals/run_eval.py build-holdout-index --competition huaweibei \
       --exclude-year 2024 --out evals/holdout_index
   ```

   输出形如 `index.json: 30 -> 24 (剔除 6 条, exclude_year=2024)`,
   镜像落在 `evals/holdout_index/competitions/huaweibei/cases/`。

2. **检索全部走镜像**。现有检索器 `scripts/retrieve_cumcm_cases.py` 原生支持索引覆盖:

   ```bash
   python scripts/retrieve_cumcm_cases.py --competition huaweibei \
       --index evals/holdout_index/competitions/huaweibei/cases/index.json \
       --problem-file <2024 题面> --level both
   ```

   `--manual-review` 缺省读取索引同目录的 `manual_review_annotations.json`,
   即自动用剔除后的镜像, 无需额外参数。**不要**省略 `--index`——省略即回落到
   仓库内完整索引, holdout 立即失效。

3. **用 2024 真题走完整 10 阶段工作流**直到 `paper.pdf`, 得到建模工作区。

4. **采集指标并对比**:

   ```bash
   python evals/run_eval.py score-run --workspace <工作区> --label holdout-2024-<版本号>
   python evals/run_eval.py compare evals/results/<旧版>.json evals/results/<新版>.json
   ```

## 恢复方法

镜像只是新增目录, **随时整目录删除即恢复原状**:

```bash
rm -rf evals/holdout_index
```

`build-holdout-index` 不修改 `competitions/` 下任何源文件; 日常训练/实战不受影响。

## 泄漏警告 (leakage)

剔除索引只挡住"检索"这一条泄漏路径, 以下残余泄漏源必须在评测报告里如实声明:

1. **蒸馏结论残留**: `competitions/huaweibei/distilled_*.md`、`star_papers_deep.md`
   等文档是全届语料蒸馏产物, 可能包含 2024 题的方法论片段。评测时若 agent 读到
   这些文件, 属于轻度泄漏 (迁移的是模式而非数值, 与实战条件一致), 报告中注明即可。
2. **empirical 校准锚点**: `empirical.json` 的分位数含 2024 论文统计, 会进入
   L1 评分的 evidence 注入。这是评分口径的一部分, 两跑之间恒定, 不影响 A/B 对比。
3. **模型自身知识**: 底座模型可能见过 2024 赛题与获奖论文公开内容, 本协议无法
   剔除; 结论表述为"伪 holdout"而非严格 holdout, 正是为此。
4. **不得反向操作**: 严禁为了提分把 2024 案例从镜像里加回来, 或在评测会话里
   直接读 `competitions/huaweibei/cases/index.json` 原文件。
5. **换届轮换**: 2024 被针对性优化过 prompt 后, 建议下一轮换剔除 2023 复测,
   防止对单一 holdout 届过拟合。
