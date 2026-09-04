# Scripts 工具说明

## 比赛运行时

| 脚本 | 用途 |
|---|---|
| `score_artifact.py` | 按统一评分契约处理各阶段评分、加权和 verdict |
| `extract_diff.py` | 生成或应用局部精修 patch |
| `render_paper.py` | 把论文工作区渲染为 LaTeX/PDF |
| `retrieve_cases.py` | 三赛联合题目级/子问级检索 |
| `retrieve_cumcm_cases.py` | 检索核心实现与旧命令兼容入口 |
| `build_stage_pack.py` | 为 Stage 1/3/5/8/9 生成最小知识包 |
| `generate_paper_plan.py` | 按子问依赖生成动态骨架、图表计划和证据账本 |
| `trace_claims.py` | 审计问题到摘要主张的完整证据链 |
| `update_knowledge.py` | 用文件哈希管理增量与知识版本 |
| `build_huashubei_cases.py` | 重建华数杯 18 题证据分级案例索引 |
| `package_submission.py` | 提交打包：文件检查 + 页数/命名 + zip + 备份 + MD5 (v7.4) |
| `freeze_numbers.py` | 数字冻结：claim↔源文件 SHA-256 绑定与 stale 检测 (v7.5) |
| `run_manifest.py` | 运行清单：脚本/输入/输出哈希链记录与漂移核验 (v7.5) |
| `figqa.py` | 图表渲染碰撞检测（六类，--strict 硬门，--self-test 自检） (v7.5) |
| `figure_lint.py` | 图表设计规则 lint（图例/标记/基线/cmap/spines） (v7.5) |
| `pdf_qa.py` | 渲染后 PDF 终检：页数/重复图题/匿名扫描/空白页 (v7.5) |

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

脚本缓存 PDF 文本/OCR，重跑不会重复识别。它会合并 `cases/annotations.json` 的人工深度标注，生成 `cases/index.json`、`case_library.md` 和 `source_manifest.json`。

3. 依赖：

```powershell
pip install -r scripts/requirements-distill.txt
```

## 已弃用审计脚本

`ingest_papers.py` 是旧 91 篇语料的历史烘焙器。该批资料混入 58 篇“华为杯”研究生论文，不得再用来生成 CUMCM 统计真值；仅保留用于复核旧产物。

## 状态路径

用户状态默认位于 `cwd/state/decision_log.json`，可用 `MATHMODEL_STATE_DIR` 覆盖。用户论文和结果位于当前工作目录，不写入 skill。
