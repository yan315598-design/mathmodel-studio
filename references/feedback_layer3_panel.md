# Feedback Layer 3 — 终局 5 视角 Panel

> stage 9 终审时调用一次。5 个独立视角并行评审, 聚合后定向重跑最弱阶段一次。这是把"局部最优"推到"全局最优"的关键一跳。

---

## 多竞赛差异化

panel personas 由 `competitions/<decision_log.competition>/rubric_overlay.json` 的 `panel_personas` 字段定义。各竞赛侧重不同:

| Competition | 默认 5 视角 | 加权重点 |
|---|---|---|
| cumcm | 数学严谨 / 模型创新 / 代码正确 / 写作呈现 / 评委 30 秒 | judge_30s ×1.5 |
| mcm | Rigor / Novelty / Communication / 30-Second Judge / Policy (D/E/F) | novelty ×1.5, judge_30s ×1.5, policy ×1.2 |
| diangong | 电力工程师 / 数据分析 / 数学严谨 / 写作呈现 / 评委 30 秒 | engineering ×1.5, judge_30s ×1.4 |
| apmcm | 评委 30 秒 / 模型适配 / 数据复现 / 图表呈现 / 中文写作 | judge_30s ×1.5, model_fit ×1.3 |

下文给出 cumcm 默认 5 视角的 prompt 模板, 其他竞赛在 prompt 头部替换 `competition_label / focus / weight` 即可 (具体 prompt 模板见 `competitions/<comp>/rubric_overlay.json` 的 panel_personas 描述, 后续可独立外置)。

---

## 设计哲学

**为什么需要 panel?**

L1 用同一份 rubric 自评容易被自己 game (rubric 上得分高, 实际质量未必高)。L3 用 5 个**独立视角 + 不同侧重**, 强制论文从多个轴向都过关, 才能逼近一等奖标准。

5 视角必须是**互斥且互补**, 任一视角缺失都可能导致系统性盲点。

---

## 盲评信息隔离与冲突裁决 (0.7.5)

评委行为研究: 评审者一旦知道及格阈值、他人评分或历史分数, 会系统性贴线打分或从众。Panel 按下表隔离信息, 编排方负责重算与裁决。

### 信息隔离三规则 (任一违反 → 该席输出视为被污染, 作废重派)

| # | 规则 | 违反示例 |
|---|---|---|
| 1 | 每个 persona 只拿三样东西: 自己的 focus 定义 + 所需章节材料 + 评分 schema | 给数学严谨席附带了写作席的点评或全文之外的摘要 |
| 2 | 不得提供其他视角输出、历史 panel 分数、团队倾向 | prompt 里写"上一轮均分 7.8, 这轮冲 8" |
| 3 | 不得告知及格阈值 / 目标线 / 奖项比例 | prompt 里写"mean ≥ 8 才能进下一阶段" |

### verdict 由编排方重算

**模型自报的乐观 verdict 不可信**。最终 verdict 由编排方 (主流程 / `scripts/score_artifact.py`) 按 `config/rating_contract.json` 的 `verdict_policy` 与 `blind_panel` 配置重算; panelist JSON 里的 verdict 字段仅作自报参考, 不直接驱动流程决策。

### 冲突裁决: >20 分差禁平均

同一共享维度 (摘要、同一张图、同一问结果) 上两席分差 >20 (0-100 口径; 等价于 1-10 口径 >2 分):

1. **禁止平均**——均值会掩盖真实分歧
2. 编排方并排审查两席引用的证据位置, 标出证据更具体的一席
3. **只重派离群席一次** (与中位数偏差更大的一席), 重派结果为最终值
4. 重派计入迭代预算 (`verdict_policy.max_iterations = 3`), 不无限重派

### 与 SKILL.md 收敛准则的一致性

stage 级 verdict 七态 (block / pass_early / pass / pass_with_review / refine / refine_partial / carryover) 与 SKILL.md 收敛准则表保持一致, 本节不改动; panel 级 first/second/third/sub_award 映射同样不变。

---

## 5 视角定义

### Panelist 1: 数学严谨视角

**关注**:
- 定理 / 引理 引用是否准确
- 推导是否有跳跃
- 边界条件是否处理
- 单位是否一致
- 符号是否首次出现就定义
- 概率/集合/极限符号使用是否规范

**最容易抓的问题**: 公式排版乱、符号重复、推导跳步、缺边界条件

**Prompt**:
```
You are a mathematics professor reviewing a CUMCM math modeling paper. 
Your job: rigorous mathematical scrutiny ONLY. 
Ignore writing style, ignore code quality.

Read the paper sections (especially §5 模型建立与求解):
{paper_section_5}

Score 5 dimensions (1-10) and report up to 3 must_fix issues:

{
  "panelist": "math_rigor",
  "scores": {
    "1_theorem_correctness": {...},
    "2_derivation_jumps": {...},
    "3_boundary_handling": {...},
    "4_units_consistency": {...},
    "5_symbol_definition": {...}
  },
  "verdict": "first|second|third|sub_award",
  "must_fix": [
    {"where": "§X.Y formula (Z.W)", "issue": "...", "fix": "..."}
  ]
}
```

### Panelist 2: 模型创新视角

**关注**:
- 模型是否有真实的机制差异（状态/损失/约束/算法/验证方式的实质改变），还是教科书直用?
- 名称与实际实现是否一致（无"改进/混合"类名不副实修饰）?
- 跨学科融合 (e.g., 优化 + ML, 仿真 + 统计)?
- 真正创新还是组合换皮?
- 文献新颖度 (近 3 年引用占比)?

**最容易抓的问题**: textbook 模型直接用、命名空泛、文献过老

**Prompt**:
```
You are a senior modeling researcher (e.g., 国赛评委长期参与者).
Your job: assess MODELING NOVELTY ONLY.
Ignore math errors, ignore writing.

Read the paper (especially §3 模型选型部分 + §5 各模型建立节):
{paper_relevant}

模型是否只有教科书名字，还是有真实的机制差异（状态/损失/约束/算法/验证方式的实质改变）？
名称与实际实现是否一致（无"改进/混合"类名不副实的修饰）？
Is there genuine cross-disciplinary fusion?
Are the cited references from past 3 years?

Output:
{
  "panelist": "modeling_innovation",
  "scores": {
    "1_mechanism_difference_quality": {...},
    "2_cross_disciplinary_fusion": {...},
    "3_substantive_innovation": {...},
    "4_literature_freshness": {...},
    "5_innovation_argument_quality": {...}
  },
  "verdict": "...",
  "must_fix": [...]
}
```

### Panelist 3: 代码正确视角

**关注**:
- 可复现性 (random seed, 环境, 数据路径)
- 注释质量与位置
- 命名规范 (变量、函数)
- 明显的 bug
- 效率 (有没有 O(n^3) 套循环又不必要的)

**最容易抓的问题**: 无 seed、注释中英混杂、变量名缩写过度、有调试残留

**Prompt**:
```
You are a senior software engineer reviewing the appendix code.
Focus ONLY on code quality. Ignore math, ignore paper writing.

Code (from appendix A):
{appendix_code}

Output:
{
  "panelist": "code_quality",
  "scores": {
    "1_reproducibility": {...},
    "2_correctness_obvious_bugs": {...},
    "3_readability_naming": {...},
    "4_comment_quality": {...},
    "5_efficiency_no_waste": {...}
  },
  "verdict": "...",
  "must_fix": [...]
}
```

### Panelist 4: 写作呈现视角

**关注**:
- 摘要结构是否完整覆盖题问 (段数按竞赛模板，不强制固定段数)
- 章节完整、层级清晰
- 公式编号、图表编号正确
- 引用格式 GB/T 7714
- 配色 / 字体 / 字号 全文一致
- 中英文混排格式 (空格)

**最容易抓的问题**: 摘要不规范、图表配色乱、引用不规范

**Prompt**:
```
You are an editor for a top Chinese journal.
Focus ONLY on PRESENTATION. Ignore math correctness, ignore code.

Read the full paper structure + abstract + figures/tables:
{paper_layout}

Score:
{
  "panelist": "presentation",
  "scores": {
    "1_abstract_5_paragraph": {...},
    "2_section_completeness": {...},
    "3_figure_table_quality": {...},
    "4_citation_format": {...},
    "5_visual_consistency": {...}
  },
  "verdict": "...",
  "must_fix": [...]
}
```

### Panelist 5: 评委视角 (最重要 ⭐)

**关注**:
- 30 秒内能不能 get 到核心?
- 这篇能不能放进 一等奖 stack?
- 第一眼最吸引/反感的是什么?

**这个视角不严格遵循 rubric, 而是模拟评委的真实心理**。

**Prompt** (最关键):
```
You are a CUMCM grader who has just read 50 papers today and is tired.
You give this paper 30 seconds to scan: title, abstract, opening of §5, 
some figures, conclusion.

Be honest: which stack will you put it in?
- 一等奖 (top 1.5%) — "I want to give this an award"
- 二等奖 (top 8%) — "Solid but not memorable"
- 三等奖 (top 25%) — "Acceptable, not noteworthy"
- 不入选 (其余) — "Has significant problems"

What's the FIRST thing your eye catches (good or bad)?
What would make you upgrade it one tier?

This panelist's verdict is the OVERALL verdict for the paper.

Output:
{
  "panelist": "judge_30s",
  "scores": {
    "1_first_impression": {...},
    "2_abstract_stickiness": {...},
    "3_figure_visual_punch": {...},
    "4_innovation_signal": {...},
    "5_overall_polish": {...}
  },
  "verdict": "first|second|third|sub_award",  // CRITICAL FIELD
  "first_eye_catch": "...",  // 第一眼看到的东西 (好或坏)
  "upgrade_path": "...",  // 升一级需要做什么
  "must_fix": [...]
}
```

---

## 并行执行 (Task tool 调用范式)

5 个 panelist 必须**独立**, 不能看到其他 panelist 的输出。

### 推荐方式: 一条消息内并发 5 个 Agent 子代理

```
Claude 主流程在 stage 9 Step 3 执行:

# 在单条响应中调用 5 次 Agent tool:
Agent({
  description: "Panelist 1 数学严谨",
  subagent_type: "general-purpose",
  prompt: """
  <Panelist 1 完整 prompt 见本文件 §Panelist 1>
  
  paper.tex 内容:
  <粘贴完整 paper.tex 或 §5/§6 关键章节, 视 token 预算>
  
  必须严格按下面 JSON schema 输出 (无任何前后文字):
  {"panelist": "math_rigor", "scores": {...}, "verdict": "...", "must_fix": [...]}
  """
})
Agent({description: "Panelist 2 模型创新", ..., prompt: "<§Panelist 2>"})
Agent({description: "Panelist 3 代码正确", ..., prompt: "<§Panelist 3>"})
Agent({description: "Panelist 4 写作呈现", ..., prompt: "<§Panelist 4>"})
Agent({description: "Panelist 5 评委视角", ..., prompt: "<§Panelist 5>"})

# 5 个独立 subagent 并发执行, 各自返回 JSON, 主进程收集到 panel_outputs 数组
```

每个子代理获得**全新 context**, 没有看到其他 panelist 的输出, 也没有 stage 0-8 的决策日志(避免被既往评分锚定)。

### 降级方式: 串行 + context 隔离

若环境不支持并发 (e.g., codex 单线程), 改为:
1. 每个 panelist 起一个**新 conversation** (`/clear` 或独立调用)
2. 输入仅: panelist prompt + paper.tex (不传任何 stage 0-8 的内容)
3. 输出 JSON 落盘到 `cwd/state/panel_<panelist>.json`
4. 主进程读 5 个 JSON 文件做聚合

绝对不能在同一个 conversation 串行问 5 个 panelist (后 4 个会被前 1 个污染)。

### 收集格式

5 份 panelist 输出统一存入:
```
cwd/state/panel_v1.json:
{
  "panel_v1": {
    "panelist_1_math": {...},
    "panelist_2_innovation": {...},
    "panelist_3_code": {...},
    "panelist_4_writing": {...},
    "panelist_5_judge": {...}
  }
}
```

---

## 聚合器 (Aggregator)

```python
def aggregate(panel_outputs):
    # 5 份 JSON
    overall = {
        "verdicts": [p["verdict"] for p in panel_outputs],
        "mean_score": mean([mean(p["scores"].values()) for p in panel_outputs]),
        "min_panelist": min(panel_outputs, key=lambda p: mean(p["scores"].values())),
        "all_must_fix": flatten([p["must_fix"] for p in panel_outputs]),
        "judge_verdict": next(p for p in panel_outputs if p["panelist"] == "judge_30s")["verdict"]
    }
    
    # 决定整体定级
    if overall["judge_verdict"] == "first" and overall["mean_score"] >= 8.5:
        return "PASS_FIRST"
    elif overall["judge_verdict"] == "first" and overall["mean_score"] >= 8.0:
        return "PASS_FIRST_MARGINAL"
    elif overall["judge_verdict"] == "second":
        return "PASS_SECOND" 
    else:
        # 找瓶颈, 定向重跑
        bottleneck_panelist = overall["min_panelist"]
        bottleneck_concerns = bottleneck_panelist["must_fix"]
        return ("REDO_TARGETED", bottleneck_concerns)
```

> 聚合时若同一共享维度两席分差 >20 (0-100 口径), 按 §盲评信息隔离与冲突裁决 处理: 禁止平均, 只重派离群席一次。verdict 一律由编排方按 `config/rating_contract.json` 重算, 不采信模型自报值。

---

## 定向重跑

```python
def targeted_redo(concerns, paper):
    # 把 concerns 映射回阶段
    for concern in concerns:
        if "code" in concern["where"].lower():
            stage_to_revise = 8  # appendix code
        elif "abstract" in concern["where"].lower():
            stage_to_revise = 8  # abstract
        elif "sensitivity" in concern["where"].lower():
            stage_to_revise = 6
        elif "model" in concern["where"].lower():
            stage_to_revise = 5
        # ...
        
        # diff-only patch
        patch = generate_patch(concern, paper, stage_to_revise)
        paper = apply_patch(paper, patch)
    
    return paper
```

只重跑**一次**, 不死循环 (避免无限优化耗尽 token)。

---

## 最终决策

```python
def final_decision(initial_panel, post_redo_panel):
    if post_redo_panel["judge_verdict"] in ["first", "second"]:
        return "SUBMIT"
    
    if time_remaining < 1h:
        return "SUBMIT"  # 时间紧, 提交当前最好版本
    
    # 再做一次 (championship 模式才有这个机会)
    if mode == "championship":
        return targeted_redo(post_redo_panel["must_fix"], paper)
    
    return "SUBMIT"
```

---

## 时间预算

5 panelist 并行 + 聚合 + 1 次定向重跑 + 第二次 panel:
- 默认: 1.5h
- 严格: 1h (跳过 red-team)
- 完整 (championship): 2.5h (含 red-team 一次)

---

## 输出与日志

写入 `decision_log.stages.9.panel_scores`:
```json
{
  "panel_v1": {
    "panelist_1_math": {...},
    "panelist_2_innovation": {...},
    "panelist_3_code": {...},
    "panelist_4_writing": {...},
    "panelist_5_judge": {...}
  },
  "aggregate_v1": {"verdict": "...", "bottleneck": "..."},
  "redo_actions": [...],
  "panel_v2": {...},
  "final_verdict": "first|second|third|sub_award"
}
```
