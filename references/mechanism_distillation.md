# 局部机制蒸馏（候选）

## 提炼对象

从已读材料的小段机制开始，不批量重写语料。提炼 `难点 -> 基线遗漏 -> 数学表示 -> 模块必要性 -> 前提/接口 -> 反例 -> 实际验证 -> 迁移边界`。论文声称与本地复核分开，不把论文标签、出现频次、来源哈希或字段完整当作机制有效证据。

现有 `distill_huaweibei_cases.py` 的 scan/manifest/empirical/validate 保持来源与格式校验职责，本轮不将它改成自动理解论文的生成器。复用既有提取文本与页码，公式不清或来源冲突时回原件；不能用通用知识填补成已复核事实。

## 侧录格式与接入

工作区候选新增 `competitions/<comp>/cases/mechanism_reviews.json`，不修改旧案例索引。每条记录包含：

- `id / case_id / competition / question_id`：与既有案例精确对应。
- `source_refs`：来源位置、证据种类与复核范围，PDF 页码采用文件页序。
- `trigger / baseline_gap / representation / module_reason / assumptions / interface`：什么时候可借鉴，如何计算，模块为什么必要。
- `counterexample / validation / limitations / transfer_boundary`：能推翻机制的例子、实际做到的检验与未解决条件。
- `review_status`：`proposed`（尚未核验）、`source_checked`（来源局部核对）、`locally_tested`（本地有限检验）。最高一档也不代表普适有效。

`build_stage_pack.py` 仅在案例命中且 Stage 为 3/5/8/9 时附带对应记录，JSON 与 Markdown 都保留完整来源、状态和边界。没有新侧录则正常兼容旧库；有侧录但损坏必须报错，不静默当成没有。记录完整性校验不替代人工机制审查。

## 小批重提炼的验收

逐条用现有结果或正式函数反例核查；不为出现正收益更换案例或参数。允许记录“新模块没有改善”和“来源本身有矛盾”。失败改变机制或适用范围，不仅改措辞。进入新题时按当前数据重新检验，旧参数、结果与模型名不能直接成为新题答案。

案例侧录是开发资料，不是留出测试。只有新旧候选在隔离会话、同条件下实际完成任务，才能评价 Skill 行为；工具回归不能宣称提示词提升。
