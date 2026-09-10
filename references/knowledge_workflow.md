# 三赛知识工作流（cumcm / huaweibei / huashubei）

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
- 研究生赛的 2021 数模之星提名论文子问使用 `star_paper_full_text`；2025 届优秀论文选子问（v2.2.0）使用 `excellent_paper_full_text`，两者同为逐篇全文深读但奖项身份不混用；华数杯蒸馏任务链使用 `paper_pattern` 或 `problem_summary_only`，不得冒充原题逐问。

## 2. Stage 知识包

进入 Stage 1、3、5、8、9 时，由 agent 运行：

```bash
python scripts/build_stage_pack.py --competition <comp|all> --stage <1|3|5|8|9> --query "<新题描述>" --output state/stage_<N>_knowledge.json
```

知识包只保留当前阶段需要的命中案例、子问接口、路线、假设风险、必要验证、图表叙事、写作骨架和 evidence ID，避免把全文证据包装入上下文。

### 域级 playbook 层（研究生赛）

- 定位：`competitions/huaweibei/distilled_modeling.md` 定风险路线，`competitions/huaweibei/playbooks/` 给域内具体动作——先按八类风险 + 信号诊断分类命中，再读对应域文件，不覆盖任何既有蒸馏文件。
- 加载时机：stage 1 作为题目域命中提示；stage 3 动作清单作为候选生成输入之一（不替代缺口驱动选型），并可经 `competitions/huaweibei/papers/domain_index.md` 按 paper_id 检索深读材料。
- 证据纪律：动作条目五要素（基线失效/机制/前提接口/反例/迁移边界）齐全并逐条标 review_status，条目数按证据定，无配额语言。

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

## 7. 外源文献检索层

本地案例库与 playbook 未命中题域时的补充通道（协议全文见
`references/literature_scout.md`），由 agent 运行：

```bash
python scripts/literature_scout.py "<english query>" --n 5 [--engine openalex|crossref|arxiv]
```

- 引擎路由：OpenAlex 主检索（免 key）；429/503 自动降级 Crossref（只取
  DOI/标题/期刊/年份）；arXiv 用于预印本补充。只接受英文 query。
- 挂点仅三处：stage 1 选题避坑、stage 3 选型补充（playbook 未命中域时触发）、
  stage 5 翻车点验证；其余阶段不触发。
- 缓存与落盘：同 query 24h 内读 `state/literature_cache.json`；方法卡（13 字段
  固定 schema）落 `state/literature/<timestamp>.json`，单卡 ≤500 token。
- 衔接机制侧录：外源方法卡先过四要素核验（题名/作者/期刊/年份）与撤稿检查，
  转写成机制条目并标 `review_status`（proposed→source_checked→locally_tested），
  才能进入选择卡与模型链；`proposed` 不得作为拍板依据。
- 边界：不接知网/万方（无合规 API，中文文献走 `reference_skill_bridge.md` 的
  cnki 桥接）、不做本地向量库、不分发获奖论文 PDF。
