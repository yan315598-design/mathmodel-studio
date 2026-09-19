# Scripts 工具说明

## 比赛运行时

| 脚本 | 用途 |
|---|---|
| `score_artifact.py` | 按统一评分契约处理各阶段评分、加权和 verdict |
| `check_gate.py` | 阶段推进门禁：必停点 checkpoints 登记 + L1 评分落盘双校验，exit 1 拦截并中文列缺失项 (v2.3) |
| `extract_diff.py` | 生成或应用局部精修 patch |
| `render_paper.py` | 把论文工作区渲染为 LaTeX/PDF |
| `renumber_equations.py` | 按出现顺序重排 md 公式编号（定义侧），打印正文引用清单供人工核对 (v2.7.0) |
| `retrieve_cases.py` | 三赛联合题目级/子问级检索 |
| `retrieve_cumcm_cases.py` | 检索核心实现与旧命令兼容入口 |
| `build_stage_pack.py` | 为 Stage 1/3/5/8/9 生成最小知识包 |
| `generate_paper_plan.py` | 按子问依赖生成动态骨架、图表计划和证据账本 |
| `trace_claims.py` | 审计问题到摘要主张的完整证据链 |
| `update_knowledge.py` | 用文件哈希管理增量与知识版本 |
| `package_submission.py` | 提交打包：文件检查 + 页数/命名 + zip + 备份 + MD5 (0.7.4) |
| `freeze_numbers.py` | 数字冻结：claim↔源文件 SHA-256 绑定与 stale 检测 (0.7.5) |
| `run_manifest.py` | 运行清单：脚本/输入/输出哈希链记录与漂移核验 (0.7.5) |
| `figqa.py` | 图表渲染碰撞检测（七类，含 artist 遮挡；--strict 硬门，--self-test 自检） (0.7.5；v3.1.0 增第七类) |
| `figure_lint.py` | 图表设计规则 lint（图例/标记/基线/cmap/spines/图名/注释预算；R9/R4 豁免通道与 `--strict`/`--strict-warn` 分层） (0.7.5；v3.1.0 分层) |
| `pdf_qa.py` | 渲染后 PDF 终检：页数/重复图题/匿名扫描/空白页/文本层工件扫描/`--page-map` 页码映射 (0.7.5；v3.1.0 增后两项) |
| `docx_presentation_postprocess.py` | 按登记的数学字体政策处理；编号、逐节公式表宽、三线表、表体与单元格对齐、图注同页独立执行。未指定字体保留输入并提示，常规正斜不等于全部斜体。 |
| `ref_order_audit.py` | 参考文献 GB/T 7714 首引顺序审计（乱序/孤立/未定义引用，并入 stage 8/9 机检） (v3.1.0) |
| `skill_paths.py` | 按调用路径定位 skill 根，并可报告链接入口对应的真实路径；不要求所有脚本采用同一种导入写法。 |
| `claim_consistency_check.py` | 结论-结果核验：正文"收敛/最优/提升/区间"强结论 vs 结果文件状态 + 数字可追溯（结果文件同值舍入匹配）+ 同对象两数值矛盾；fail/warn/info 三级，--strict 时 fail 即 exit 1 (候选版) |
| `mechanism_reviews.py` | 机制侧录加载与校验：`competitions/<comp>/cases/mechanism_reviews.json` → Stage 3/5/8/9 知识包附带 (候选版) |

相似案例检索：

```powershell
python scripts/retrieve_cases.py `
  --competition all --level both `
  --problem-file problem.txt --top-k 5
```

`--competition` 支持 `cumcm`、`huaweibei`、`huashubei` 和 `all`。联合检索保留竞赛与证据身份；华数杯 S1-S4 是蒸馏任务链，不是原题逐问。

Stage 8 的典型内部调用链：

```powershell
python scripts/build_stage_pack.py --competition all --stage 8 --problem-file problem.txt --output state/stage_8_knowledge.json
python scripts/generate_paper_plan.py --stage-pack state/stage_8_knowledge.json --output state/paper_plan.json
python scripts/trace_claims.py --input state/paper_plan.json --output state/evidence_trace.json --strict
```

知识增量默认只预览；明确更新时才写入清单：

```powershell
python scripts/update_knowledge.py --source <资料目录>
python scripts/update_knowledge.py --source <资料目录> --apply
```

## CUMCM 知识库维护

1. 下载并生成来源清单：

```powershell
python scripts/download_cumcm_papers.py --output-dir <corpus>
```

默认只下载官方展廊、可核验 GitHub 论文/代码和题面。只有显式传入 `--include-legacy-non-cumcm` 才会把旧误标资料放入隔离目录；隔离资料不能参与案例和统计。

2. 蒸馏并重建案例：

```powershell
python scripts/distill_cumcm_cases.py `
  --corpus-dir <corpus> `
  --knowledge-dir competitions/cumcm `
  --ocr selected --workers 1
```

脚本缓存 PDF 文本/OCR，重跑不会重复识别。它会合并 `competitions/cumcm/cases/annotations.json` 的人工深度标注，生成 `competitions/cumcm/cases/index.json` 和 `source_manifest.json`；人读视图 `case_library.md`（v2.8.0 起从运行路径迁出）写到维护方本地的 maintenance 语料目录，**不随公开分发包发布**——公开包内可用的对应内容是 `competitions/cumcm/cases/index.json` 与 `competitions/cumcm/cases/manual_review_annotations.json`。

3. 依赖：

```powershell
pip install -r scripts/requirements-distill.txt
```

## 已弃用审计脚本（已移入 scripts/legacy/）

`ingest_papers.py` 是旧 91 篇语料的历史烘焙器。该批资料混入 58 篇“华为杯”研究生论文，不得再用来生成 CUMCM 统计真值；仅保留用于复核旧产物。**v2.8.0 起移入 `scripts/legacy/ingest_papers.py`。**

`build_huashubei_cases.py` 同口径：**一次性烘焙脚本**，用于把本地华数杯资料蒸馏进案例库（重建 18 题证据分级案例索引）。既无工作流挂点也无测试，不属于工作流调用链，仅在需要重建该索引时手动运行。**v2.8.0 起移入 `scripts/legacy/build_huashubei_cases.py`。**

### 历史重建配方（build_huashubei_cases.py 要点摘录）

需要重建华数杯案例索引（`competitions/huashubei/cases/index.json`）时，按 `scripts/legacy/build_huashubei_cases.py` 执行；其知识设计要点：

1. **profile 三类（TYPE_PROFILES）**：按题型 A/B/C 各配一份档案——A=物理工程机理、数值仿真与参数优化；B=运筹、组合优化与资源调度；C=数据分析、综合评价、预测分类与规划。每份含 `paradigm`（范式一句话）、`assumption_risks`（2 条假设风险）、`required_solution_checks`（4 条必做验证）、`figure_story`（4 角色图表叙事）、`writing_blueprint`（写作蓝图一句话）。
2. **18 条任务链（TASK_CHAINS）**：A 题型 6 条（传热 PDE/电磁谐振/半导体多目标/传热几何/机器人运动学/多物理场）、B 题型 6 条（二维下料/三维装箱/MRP 调度/配色/VLSI 布局/5G 资源调度）、C 题型 6 条（评价进步/营销分类/回归多目标/干预优化/评价+TSP 路线/光谱统计），每条是 4 步蒸馏任务链（如"数据质量和指标构造 → 客观/组合赋权 → 综合评价与进步分解 → 权重稳健性和政策解释"）。
3. **证据分级与 S1-S4 边界**：案例的 `evidence_level` 二分——2023-2025 有优秀论文支撑的 `paper_pattern`（evidence_id 形如 `huashubei:paper_pattern:<file_stem>`），2020-2022 仅题面的 `problem_summary_only`（evidence_id 形如 `huashubei:problem_summary:<year>-<problem>`）。`question_dependency` 写成 "S1-S4 蒸馏任务链"，`question_granularity` 固定 `distilled_stage_not_original_question`——**S1-S4 是可复用任务链，不是原题逐问转录**；`transfer_boundary` 固定声明"只迁移方法接口、验证和图表角色，必须回到当年或新题题面重建子问、参数、约束和结论"。
4. **输入输出**：读 `competitions/huashubei/topic_specs.json`（题面规格）与 `empirical.json`（论文登记），写 `competitions/huashubei/cases/index.json`（schema `case-index-2.0`，含 source_policy：2020-2022 `problem_summary_only` / 2023-2025 `topic_summary_plus_two_paper_patterns_per_problem`）。

## 状态路径

用户状态默认位于 `cwd/state/decision_log.json`，可用 `MATHMODEL_STATE_DIR` 覆盖。用户论文和结果位于当前工作目录，不写入 skill。
