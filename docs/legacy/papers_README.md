# 论文资料库 (papers)

> 本目录是**辅助参考资料**, skill 主体不依赖这里的内容运行。获奖论文共性已按竞赛分别蒸馏进 `competitions/<comp>/winning_patterns.md` 静态知识。

## 当前内容

可能包含通过 git clone 拉取的开源仓库:
- `MathModel/` (zhanwen): 历年题目分类 + 算法资料
- `Math_Model_repo/` (personqianduixue): LaTeX 模板 + 算法仓 (论文在百度云,GitHub 仅索引)

## 如何手动补充

直接下载渠道有限, 优先级如下:

### 1. 教育部"中国大学生在线"展厅 (官方公开)
- URL: https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/
- 操作: 浏览器手动进入 → 选年份 → 选题号 → 下载 PDF → 投放到本目录
- 优势: 官方权威, 都是真实一等奖
- 限制: 每年仅展出极少 (3-5 篇/题)

### 2. GitHub 公开 repo
搜索 keyword:
- "CUMCM" / "数学建模" / "国一"
- "national first prize" math modeling
- 历年获奖学校的个人 repo (如中山大学、清华、上交)

### 3. CSDN / 知乎 / B 站
质量参差, 但有汇总贴。例:
- https://blog.csdn.net/qq_37345758/article/details/134295998 (2023 国赛)
- https://blog.csdn.net/2401_86936045/article/details/141719882 (历年汇总, 国一学长整理)

CSDN 会要求注册或下载券, 注意辨别真伪。

### 4. 数模社 / 数模君 / 数学建模交流群
非官方, 但可能有更多。需付费或加群。

## 使用方法（历史流程已退役）

收集到 PDF 后跑 `scripts/ingest_papers.py` 烘焙统计的旧流程已退役：脚本产物仅保留复核用，不得再生成统计真值；脚本已移入 scripts/legacy/（v2.8.0）。新收集的 PDF 不再走烘焙链；如需更新经验统计，按 `competitions/<comp>/empirical_notes.md` 的口径人工登记并同步该竞赛的 `empirical.json` 与 `winning_patterns.md`。

## 重要提示

skill 运行时**不读**这里的 PDF (避免污染上下文 + token 浪费)。
本目录内容只在你想**手动补充/更新模式**时使用。
即使本目录为空, skill 仍可完整运行。
