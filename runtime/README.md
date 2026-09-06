# mathmodel-agent — 薄 agent runtime 原型

证明一个架构假设：**skill 即大脑，薄 runtime 即执行器**。`SKILL.md + references/ + scripts/ + competitions/`
承载全部建模知识与工具；本包只是一个几百行的独立 Python 执行器，替代 Claude Code / Codex 这类
重型宿主 harness 的驱动职责：组 prompt、调 LLM、跑脚本、执行代码、持久化状态。

## 架构

```
mathmodel_agent/
  config.py    AgentConfig: 角色→模型 (extraction/solving/writing/review 四档)、
               API key 从环境变量读 (MATHMODEL_LLM_API_KEY, 角色级 MATHMODEL_LLM_API_KEY_<ROLE> 可覆盖)、
               mode (fast/standard/championship) → token 预算
  llm.py       LLMClient 协议 + 统一重试 (指数退避, 最多 3 次; 按 status_code 优先判定可重试:
               429/408/5xx 重试, 其他 4xx 立即失败) + LiteLLMClient (import litellm 延迟到首次调用)
  mockllm.py   MockLLM: 按 prompt 的 [STAGE n]/[ITER k] 标记返回确定性罐装响应;
               可注入 refine/block/非法 critique 反例 (从 llm.py 拆出)
  state.py     decision_log.json 读写封装; 从 templates/shared/ 初始化; 原子写盘
               (临时文件+os.replace, PermissionError 指数退避重试 5 次, 耗尽抛可恢复的
               StateSaveError); reload 遇损坏文件保留内存态不抛出
  tools.py     skill 工具注册表: retrieve_cases / score_artifact / figqa /
               consistency_audit / freeze_numbers, 子进程调用 (300s 超时), 结构化 dict 返回;
               blocking=True 的工具失败时所在 stage 不得推进
  sandbox.py   python 片段执行: 正则黑名单 (含 from-import / getattr 拼接变体) +
               cwd 限定 workspace + 产物差分登记 (新增/变更/删除三类)
  protocol.py  ```artifact:<相对路径> 围栏块协议: 逐行解析 (路径可含空格),
               嵌套 fence 原样保留, 未闭合/畸形块记协议错误不静默丢弃
  prompts.py   prompt 组装: stage reference + [ITER k] + state 摘要 + workspace 文件清单 +
               必停点用户应答上下文 (恢复后注入)
  gate.py      质量门: 解析 score_artifact 结构化输出, 判定 advance/iterate/carryover/blocked
               (对齐 references/feedback_layer1_critic.md 收敛准则)
  loop.py      StageDriver: 组 prompt → LLM → 工件落盘 → patch 合并 → 工具质检 →
               质量门 → check_gate 门禁 (v2.3.0, _advance 前强制子进程执行, FAIL paused) →
               推进; refine 在 stage 内迭代 (上限 3); checkpoint_request → paused;
               LLM 产出 state/checkpoints_patch.json → protocol_error blocked;
               stage 2 patch 携带 actual_qi_count (实际子问数) 时经 confirm_qi_count
               原子迁移 stages["5"].qi_count/qi_weights (记 qi_count_confirmed 事件);
               stage 9 是终点 (无 gate 9, 完成即 completed, current_stage 保持 9)
  cli.py       命令行入口: run 驱动流程; answer 人工应答必停点 (trusted 写入 checkpoints)
```

### 必停点 HIL-lite 流程 (v2.3.0)

checkpoint 只能由"人"写, LLM 一律不可写:

```text
LLM 正文发 `checkpoint_request: <key>` (唯一合法申请方式)
  → runtime 先全文扫描 (finditer) 再决定动作:
     恰好 1 个合法且未答的 request → 不写任何工件, 保存 pending_checkpoint, 状态 paused;
     request 指向的 key 已 answered → 视为无 request (记 checkpoint_request_ignored 事件,
       正常写工件继续推进, 防死循环);
     ≥2 个不同 key、任一非法 key (不在 stage allowlist) 或任一畸形行 (凡以
     `checkpoint_request:` 开头的行, strip 后前缀匹配即候选; 冒号后必须恰好一个非空
     key, 空 key/尾随多余 token 均算畸形) → protocol_error, blocked, 不写工件
  → 用户执行: python -m mathmodel_agent answer --workspace <dir> --key <key> --answer "<回答>"
    [--count N] [--exception] [--reason "..."]
    (record_checkpoint trusted 路径: 校验 allowlist、figure_menu/qi_verdict 按 Qi 深合并、
     已 answered 覆盖需 --force、拒绝下划线元键; source=user_cli, runtime 判"已答"
     只认 source == "user_cli" 的条目)
  → 重跑 run: pending 已 answered 即清除并从 current_stage 继续,
    用户答案以「必停点用户应答」小节注入下一轮 prompt
```

answer 默认要求 `state.pending_checkpoint == key` 才接受（无 pending 或不匹配 → 中文报错
exit 2，提示先由流程发起 checkpoint_request）；`--force` 保留为人工管理覆盖（打印明显警告、
跳过 pending 匹配、允许覆盖已答条目并清除 pending）。`--count/--exception/--reason` 仅对
`figure_menu.Q<n>` 键有效（其他键携带即报错）：count 为 0-9 整数，count≤1 须 `--exception`
加非空 `--reason`（D.1 例外确认，与 check_gate 口径一致）；`figure_menu.Q<n>` 的 `--count`
为必填（缺 `--count` 即 exit 2，pending 保留、state 不写盘，与 check_gate 同口径）。

LLM 生成 `state/checkpoints_patch.json` 工件或任何 checkpoint 内容 = 伪造必停点
(protocol_error) → 立即 blocked; 非 allowlist key 或一次多个不同 key 的 checkpoint_request
同样 blocked。

关键约定：**runtime 不 import skill 的任何脚本**，全部通过子进程调用（cwd=workspace）；
`scripts/score_artifact.py` 对 `decision_log.json` 的写盘同为原子写（临时文件+os.replace），
与 runtime 的 state 协议一致，双方可交替驱动同一工作区。stage 是否推进由质量门决定：
verdict 为 pass/pass_early/pass_with_review 才推进；refine 在 stage 内迭代；block 停机并把
blocked 状态写入 state；迭代耗尽显式记 carryover 事件；blocking 工具失败不推进。

## 使用

```bash
cd runtime
python -m pytest tests/ -q          # 全部测试 (零依赖, 标准库即可)

# mock 模式端到端冒烟 (无 API key、零网络请求), stage 0-2:
python -m mathmodel_agent run --workspace <tmp_dir> --mock --from-stage 0

# 真实模式 (需 litellm 与 key):
pip install -e '.[litellm]'
export MATHMODEL_LLM_API_KEY=sk-...
python -m mathmodel_agent run --workspace <dir> --competition huaweibei \
    --problem 题面.txt --from-stage 0
```

常用参数：`--from-stage` 默认取 `state.current_stage`（与 state 不一致的显式回退/跳阶段需
`--force`，并记 backtrack 事件）；`--to-stage`（单 stage 试运行）；`--dry-run`（只打印
prompt 摘要，不调 LLM）；`--mode fast|standard|championship`（token 预算）；`--skill-root`
（默认从包位置自动探测仓库根）。退出码：0 成功 / 2 参数或起点不一致 / 3 质量门 blocked、
必停点待人工应答或门禁 paused / 4 状态写盘失败。环境变量：`MATHMODEL_MODEL_<ROLE>` 覆盖
角色模型，`MATHMODEL_LLM_API_KEY(_<ROLE>)` 提供 key。

必停点应答（`answer` 子命令，HIL-lite 的人工侧）：

```bash
python -m mathmodel_agent answer --workspace <dir> --key kickoff_5q --answer "<用户回答>" [--note ...] [--force]
# figure_menu.Q<n> 专用结构化参数: --count 2 (0-9 整数); count≤1 时另须 --exception --reason "<例外理由>"
```

## 沙箱与安全的诚实边界

沙箱是**尽力约束，不是安全边界**：正则黑名单拒绝 shell 调用 / subprocess / from-import 与
`__import__` 动态导入 / getattr 拼接 / rmtree / 网络库，cwd 限定在 workspace，产物以执行前后
文件 (mtime, size) 差分登记。绕过手段很多（写文件再由外部执行、编码混淆、黑名单未覆盖的
动态构造等），真正的隔离需要容器或操作系统级沙箱。网络访问同理：黑名单挡住常见网络库，
但无法保证 socket 不可用。本 runtime 自身除 litellm 调用（仅非 mock 模式）外不发起任何
网络请求，也不校验 URL。

## 能做什么 / 还不能做什么

- 能：mock 模式跑通 stage 0-2 全链路（工件协议、补丁合并、score_artifact 评分、
  retrieve_cases 检索、verdict 驱动的推进/迭代/携带/停机、断点恢复、backtrack 审计）；
  必停点 HIL-lite 全链（checkpoint_request → paused → CLI answer → 恢复继续, LLM 自写
  checkpoints 一律 blocked）；五件 skill 工具的结构化调用与 blocking 语义；代码沙箱执行
  与三态产物登记；原子状态写（含 PermissionError 重试）；LLM 重试与按 status_code 的
  失败分类。
- 还不能：真实 LLM 接入未验证（LiteLLMClient 有适配但无 key 环境实测）；prompt 工程
  是占位（仅 reference 截断注入，未做竞赛分支路由/知识包加载；v2.3.0 必停点协议已单独
  注入不受截断影响）；完整编号菜单交互（图表菜单五选项、D.1 例外确认等）由 SKILL.md
  驱动的主流程承载，本 runtime 只保证"必停点未人工应答不推进"的门禁硬约束；
  stage 3-8 的工具策略只有骨架；无 L2-L4 反馈层与评委模拟器编排。
