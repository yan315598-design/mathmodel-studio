# evals/ — 最小评测设施

改一版 prompt / 工作流后, 回答"论文质量到底变好还是变坏"的端到端回归手段。
核心思路: **伪 holdout** (把评测届从检索索引剔除, 模拟未见过的题) + **指标采集** (对建模工作区跑现有 QA/评分脚本) + **双跑对比**。

## 组成

| 文件 | 用途 |
|---|---|
| `run_eval.py` | 评测 runner, 三个子命令 (见下) |
| `holdout_protocol.md` | 伪 holdout 协议: 操作步骤、恢复方法、泄漏警告 |
| `results/` | `score-run` 的输出目录 (JSON, 已加入分发排除清单) |

## 三个子命令

```bash
# 1. 构建剔除 2024 届后的检索索引镜像 (源文件不动)
python evals/run_eval.py build-holdout-index --competition huaweibei \
    --exclude-year 2024 --out evals/holdout_index

# 2. 对一个建模工作区采集指标, 写 evals/results/<label>_<timestamp>.json
python evals/run_eval.py score-run --workspace <建模工作区> --label myrun

# 3. 并排对比两次评测 (metric / A / B / delta)
python evals/run_eval.py compare evals/results/a.json evals/results/b.json
```

## 指标定义

`score-run` 逐项调用 `scripts/` 下现有脚本 (存在哪个跑哪个, 输入缺失记 `status=skipped`),
结果 JSON 的关键字段:

| 指标 | 来源脚本 | 含义 |
|---|---|---|
| `tools.score_artifact_judge.final` | `score_artifact.py --mode judge` | 评委模拟器终审分 (扣分制 × 格式乘数), 越高越好 |
| `tools.score_artifact_judge.tier` | 同上 | 校准锚点档位 (仅 huaweibei: 国一区间候选/国一边缘/未达目标线) |
| `tools.score_artifact_judge.exit_code` | 同上 | 1 = 资格门未过 (不具备获奖资格), 比分数更硬 |
| `tools.consistency_audit.error_count` | `consistency_audit.py --json` | ❌ 级问题数 (数字冲突/摘要结论打架/引用断链), 目标 0 |
| `tools.consistency_audit.warn_count` | 同上 | ⚠️ 级提示数, 越少越好 |
| `tools.trace_claims.complete` / `incomplete` | `trace_claims.py` | 证据链完整/不完整的子问数 |
| `tools.trace_claims.coverage` | 同上 | 六链字段覆盖率 (0-1) |
| `tools.trace_claims.abstract_gate` | 同上 | `pass` / `block_untraced_claims` |
| `tools.figqa.exit_code` | `figqa.py` | 0=无碰撞, 1=检出排版碰撞, 2=输入/渲染错误 |
| `tools.pdf_qa.error_count` | `pdf_qa.py` | 终检 PDF ❌ 项数 (页数/编号/匿名/空白页) |
| `decision_log.stages.<n>.{min,mean,verdict}` | 直接读 `state/decision_log.json` | 各 stage 最后一次 L1 评分 |
| `artifacts.file_count` / `total_bytes` | 目录扫描 | 产物文件清单与体积, `state/`、`results/` 与 `__pycache__/` 不计入 (防止"高分但缺产物"的回归) |

判读约定: **先看硬门** (judge exit_code、audit error_count、pdf_qa error_count、abstract_gate 必须不为坏值), **再看连续指标** (judge final、coverage 走 compare 看 delta)。

`status` 三态:
- `ok` — 子脚本正常完成; 此时 `exit_code=1` 通常是**质量门结果** (审计发现 ❌ / 检出碰撞 / 资格门未过), 是可比指标;
- `skipped` — 输入缺失 (如工作区无 judge_input.json), 不参与对比;
- `error` — 子进程崩溃/超时、退出码非质量门语义 (如 rc=2 输入/IO 错)、或输出 JSON 缺必需字段解析失败; **该跑不可比, 先修环境**。

## 完整流程

1. 按 `holdout_protocol.md` 构建 holdout 索引并用它完成一次建模 (得到工作区 A)。
2. 改 prompt / 工作流, 用同样协议再跑一次 (工作区 B)。
3. `score-run` 两次 (label 区分), `compare` 出差异表, 硬门全绿且连续指标不倒退才算改进。

## 注意

- `score-run` 只读工作区, 不修改任何文件; 结果写到本仓库 `evals/results/`。
- 评测结果 JSON 含 `stdout_tail` 诊断片段, 供排查子脚本异常, 不作为对比指标。
- 本设施不依赖外部语料; 工作区由建模流程本身产生。
