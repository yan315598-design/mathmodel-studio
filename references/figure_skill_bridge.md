# Figure Skill Bridge

本文件定义 mathmodel-studio 与画图能力的协作方式。目标是让数学建模论文里的图表先有论证目的, 再生成高质量图, 最后做可读性检查。

---

## 图表能力总路由（v7.10.0 起以此为准）

mathmodel-studio 图表体系 = 自写模板库（下节）+ **vendor 内嵌的三个上游 skill 原样副本**
（`templates/figures/vendor/`, 出处与许可证见 `vendor/VENDOR.md`）。按需求路由:

| 需求 | 首选 | 备选/说明 |
|---|---|---|
| **论文示意图/技术路线图/研究框架图/阶段流程图**（要密集信息架构、drawio 可编辑、答辩级质量） | `vendor/scibox-diagram/` 4 模板（content JSON 驱动: roadmap-5band / framework-3col / stageflow-3col / taskflow-land）, 体检走其自带 `scripts/check_layout.py` | 快速出轻量小图用自写 `render_drawio_pack.py` 6 模板（v7.9.1 两段式卡版, 落盘过 drawio_check 门禁）; matplotlib 直出 PNG 用 `render_diagram_pack.py` 4 模板 |
| **照着参考图复刻示意图** | `vendor/scibox-diagram/references/replication.md` 高保真复刻路径（像素标定 + 四件中间产物 + ≥3 轮迭代） | — |
| **数据图（论文正文 Type 3/4）** | 自写 `render_modeling_pack.py` 17 件（统一色板 + figqa/figure_lint 硬门） | 图型不在库内时走 `vendor/scibox-figure/`（cv-roc-ci / paired-raincloud / tpe-surface / marginal-grid 等差异图型, `scripts/render_template.py --list`） |
| **答辩 PPT / 网页 / 海报级图表** | `vendor/diagram-design/`（39 类编辑级 HTML/SVG, 4px 网格 + 焦点色纪律） | 不进 LaTeX 正文; 中文内容注意其字体链为英文系, 需自行换栈 |
| **交互式 HTML** | `math-figure-generator` 的 plotly/pyecharts 轨道 | — |

> **开源分发版注意（v2.0.0）**：`vendor/scibox-diagram/` 与 `vendor/scibox-figure/` 因上游未附正式 LICENSE，**不进入 git 公开仓库与分发包**（`vendor/diagram-design/` 为 MIT，正常随附）。克隆/分发版中上述两个目录不存在时，路由自动降级：论文示意图走自写 drawio 6 模板（`render_drawio_pack.py`）+ matplotlib 4 模板（`render_diagram_pack.py`）；差异数据图型（cv-roc-ci / tpe-surface 等）在分发版不可用，或自行获取 sci-box 放入 `vendor/` 后恢复完整路由。

**vendor 使用纪律**: 不改写 vendor 内文件; scibox-figure 默认把输出写在其自身
`绘图复刻/outputs/` 目录, 出图后把产物移动到 `paper/figures/` 或 `results/`
对应位置, 不要把论文引用指向 vendor 内部路径。

---

## 本地图表模板库 (v7.7.0 自写版, 优先复用)

**在调用外部 skill 之前, 先检查 `<skill>/templates/figures/scripts/` 是否有现成模板可用.** 现库 17 件数据图模板（`templates/`）+ 4 件示意图模板（`diagrams/`）+ 6 件 drawio 可编辑模板（`drawio/`），全部为本 skill 自写的确定性脚本, 统一接入 `templates/figures/style/palettes.py` 色板与 mathmodel.mplstyle, 直接用能节省时间且保证可复现.

**入口**: `python <skill>/templates/figures/scripts/render_modeling_pack.py <id> --out <目录>`

| Template ID | 图类型 | 适用场景 |
|---|---|---|
| `tornado` | 灵敏度龙卷风图 | 参数 ± 扰动对输出的影响排序 (Stage 5/6 刚需) |
| `allocation` | 优化分配结果图 (甘特/堆叠条双模式) | 调度/资源分配类优化结果展示 |
| `robustness` | 多场景稳健性对比 (箱线/小提琴+参考线) | 稳健性/多场景分析 (Stage 6) |
| `flowchart` | 技术路线图 (确定性布局+中文换行) | 问题分析章/Our Work 流程图 |

> 下表为初始 4 件历史常用模板；**完整 17 件数据图模板清单及别名以 `render_modeling_pack.py --list` 为准**（v7.7.0 新增 roc-pr / taylor-diagram / raincloud / circular-heatmap / confusion-matrix / shap-summary / chord-diagram 7 件）。

**使用约定**:
- 调用 `render_modeling_pack.py --list` 看完整清单（含每个模板推荐的 figqa 命令）
- 每个模板经 `figkit.save_fig()` 一次落盘 PNG(300dpi) + SVG + PDF 三格式, 确定性种子可复现
- 模板自带"示例数据", 替换为真实结果数据后再进论文; 色板与样式默认取 `templates/figures/style/`, 自定义须符合 `references/color_typology.md`
- 出图后按 v7.5.0 硬门跑 figqa 与 `scripts/figure_lint.py`; figqa 命令**分模板**:
  - `flowchart`（技术路线图）: 盒内文字是合法版式, 固定加豁免 `python <skill>/scripts/figqa.py <图脚本/目录> --strict --allow-box-labels`
  - 其余模板（tornado / allocation / robustness）及 math-figure-generator 产出: `python <skill>/scripts/figqa.py <图脚本/目录> --strict`

**调用流程**:
1. 用户描述需求 → Agent 按上表选模板 id
2. Agent 运行 `render_modeling_pack.py <id> --out <workspace>/figures/` (或直接运行 `templates/figures/scripts/templates/make_*.py`)
3. 输出改名为符合论文命名规范的 `paper/figures/Fig_Q*.svg/png`
4. 替换脚本里的示例数据为真实结果数据
5. 检查输出契约字段 (见文末) 并跑 figqa/figure_lint 硬门

若需求不在 17 个数据图模板覆盖范围（SHAP / 云雨图 / 泰勒图 / ROC-PR / 和弦图等已在库内），或需要可编辑流程/机理图，drawio 可编辑模板由 `render_drawio_pack.py` 生成（6 模板：roadmap / framework / flow3col / stageflow / swimlane / mechanism），draw.io 打开微调后导出 PNG/PDF/SVG；其余需求才进入下面的"已安装画图相关 skills"流程。

---

## 已安装画图相关 skills

优先使用以下三类:

| Skill | 用途 | mathmodel 触发场景 |
|---|---|---|
| `figure-table-planner` | 规划每问需要哪些图表, 并按诊断图/对比图/论文图/附录图分类 | Stage 5 结果出来后, Stage 8 写作前 |
| `math-figure-generator` | 生成数模论文图, 包括评价图、预测图、优化结果图、灵敏度图、流程图、热力图、多子图 | 用户说"画图/生成图/美化图", 或 Stage 5/6 需要论文图 |
| `nature-figure` | 高标准论文图质检, 强调结论、证据链、可编辑 SVG/PDF/TIFF、字号和重叠风险 | Stage 9 终审, 或用户要求"高质量/论文级/Nature 风格" |

辅助使用:
- `canvas-design`: 只用于海报、封面、宣传视觉, 不用于数模论文核心图。
- `web-artifacts-builder`: 只用于交互式网页或可视化 demo, 不用于论文静态图。
- `algorithmic-art`: 只用于艺术性图像, 不用于竞赛论文证据图。

---

## 三段式工作流

### 1. 先规划

在生成论文图前, 先用 `figure-table-planner` 的四类图表分类:

| 类型 | 名称 | 是否进正文 | 用途 |
|---|---|---|---|
| Type 1 | 诊断图 | 通常不进 | 检查残差、异常值、相关性、收敛 |
| Type 2 | 对比图 | 可选 | 比较候选模型、基线和主模型 |
| Type 3 | 论文图 | 必须进 | 支撑正文核心结论 |
| Type 4 | 附录图 | 进附录 | 补充稳健性、完整场景和细节 |

每张图必须写清:
- 支撑哪一句结论。
- 数据来源路径。
- 放在论文哪一节。
- 是否已有结果, 还是缺少源数据。

### 2. 再生成

生成图时使用 `math-figure-generator` 的数模图谱:

| 任务 | 推荐图 | 本地模板 (templates/figures/, 优先复用) |
|---|---|---|
| 评价排序 | 横向排序条形图、雷达图、热力图 | `taylor-diagram` (多模型对比) / `circular-heatmap` |
| 预测拟合 | 真实-预测散点图、趋势线、置信带 | `prediction-fit` / `correlation-heatmap` |
| 分类评估 | ROC 曲线 + 置信区间 | `roc-pr` |
| 模型解释 | SHAP、特征重要性 | `shap-summary` |
| 分布对比 | 云雨图、箱线图 | `raincloud` |
| 关系网络 | 流向、相关性 | `chord-diagram` |
| 超参搜索 | 优化曲面 | (无现成模板, 走 math-figure-generator) |
| 未来预测 | 折线图 + 置信区间 | (无现成模板, 走 math-figure-generator) |
| 优化结果 | 分配柱状图、堆叠图、路径图、网络图 | `optimization-allocation` (分配堆叠/甘特) |
| 灵敏度 | 龙卷风图、扰动曲线、热力图 | `tornado-sensitivity` (龙卷风/灵敏度) |
| 稳健性 | 多场景对比图、箱线图、分位区间 | `multiscenario-robustness` (多场景稳健性) |
| 流程说明 | 工作流图、模型结构图、算法流程图 | drawio 模板包（`render_drawio_pack.py`, 6 模板, draw.io 微调后导出 PNG/PDF/SVG）或 `technical-route-flowchart` |

默认输出:
- `paper/figures/*.svg` 作为主文件。
- `paper/figures/*.png` 作为备用。
- 论文图最低 300 dpi。
- 字号不低于 7 pt, 终审推荐不低于 9 pt。

### 3. 最后质检

Stage 9 或用户要求"终审图表"时, 使用 `nature-figure` 的质检思想:

- 图是否只表达一个核心结论。
- 每个 panel 是否提供独立证据。
- 文字是否可读, 没有出界和重叠。
- 坐标、单位、图注、图例是否齐全。
- 同一模型或方法在全文是否保持同一颜色。
- 是否有可编辑 SVG/PDF 版本。

### 3.5 示意图双门: 机器体检 + 渲染目检（v7.9.1, 流程图/框架图/路线图必走）

机器体检只能查"硬伤"（溢出/越界/重叠/穿盒），查不出"平庸"（密度低、
层级平、重心散）。所有示意图（流程图/架构图/技术路线图/机理图）进论文前
必须过两道门:

**第一道 · 机器体检（自动）**
- matplotlib 示意图: `figqa.py <脚本或目录> --strict --allow-box-labels` 零检出。
- drawio 示意图: `finalize()` 落盘自动跑 `drawio_check.py`（FAIL 即退出码 1）;
  手工改过的 .drawio 文件交付前手动补跑 `python drawio/drawio_check.py <file>`。
  三个 WARN 级"平庸信号"要当真处理: 全字加粗 / 实心盒 >20 / 连线描边 >2.0。

**第二道 · 渲染目检（九区盘点, 不看渲染图不算画完）**
打开渲染出的 PNG（不是源文件）, 至少两轮, 逐项盘点:
1. 文字溢出/压线/出界;
2. 箭头方向与语义一致（尤其分发、汇流、双向）; 箭头必须竖直/水平进盒边,
   不斜插、不横抵盒顶;
3. 同族元素对齐同宽（列基线、步距、4px 网格）;
4. 数值/术语与正文、结果文件逐字一致;
5. 视觉重心: 焦点盒 ≤2 个, 一眼能看到最重要的节点;
6. 字重层级: 标题条/徽章加粗、卡内标题加粗、明细常规 —— 不是全图一个重量;
7. 密度: 节点 >9 个考虑拆总览+细节; 每卡是否都有"标题+明细"两段信息,
   单行白盒太多说明信息架构没做;
8. 连线: 一分多走母线不走 N 条斜线; 共边多线附着点扇开 ≥12px;
9. 留白: 无底部大片空白, 画布高按内容推导。

任一项不过 → 修源文件重渲 → 重新盘点, 直到两轮全清。

---

## mathmodel 调用规则

| 用户说法 | 使用策略 |
|---|---|
| "帮我规划图表" | 先走 `figure-table-planner`, 输出每问图表计划 |
| "根据结果生成图" | 先确认数据路径和图要支撑的结论, 再走 `math-figure-generator` |
| "美化这张图" | 用 `math-figure-generator` 重画或改样式, 保留原数据 |
| "终审图表" | 用 `nature-figure` 质检规则, 输出问题清单和修改优先级 |
| "画流程图" | 若是论文流程/算法流程, 用 `math-figure-generator`; 若是艺术海报, 才用 `canvas-design` |

---

## 禁止事项

- 不为没有数据或结果的结论编造图。
- 不把诊断图冒充论文图。
- 配色统一走 `references/color_typology.md` 与 `templates/figures/style/palettes.py`（八套色板含四套期刊板 npg/aaas/lancet/nejm、中性色令牌、灰度校验、语义绑定）: 不用默认 tableau 直出, 不用彩虹色, 不让同一方法在不同图里换颜色。
- 不把关键证据只放在附录。
- 不生成没有图注、坐标单位和正文解释的 Type 3 论文图。

---

## 输出给论文的最低标准

每张 Type 3 论文图至少包含:

```json
{
  "figure_id": "Fig.Q1.1",
  "type": "Type 3 paper figure",
  "claim_supported": "该图支撑的一句话结论",
  "source_artifact": "results/Q1/...",
  "paper_section": "5.1.3",
  "output_files": ["paper/figures/Fig_Q1_1.svg", "paper/figures/Fig_Q1_1.png"],
  "caption": "图注说明读者应该看到什么结论",
  "template_used": "templates/figures/scripts/templates/make_tornado_sensitivity.py",
  "palette": "academic_blue",
  "qa": {
    "axis_units": true,
    "caption_ready": true,
    "font_readable": true,
    "no_overlap": true,
    "color_consistent": true
  }
}
```

> v6.4 新增字段 `template_used`: 记录每张图用了哪个本地模板 (路径相对 skill 根). 没用本地模板 (纯 math-figure-generator 生成) 时填 `null`, 方便 stage_09_review 回溯图表来源.

> v7.4.0 新增字段 `palette`: 该图使用的色板, 取 `templates/figures/style/palettes.py` 八套之一 (v7.7.0: academic_blue/cool_nature/muted_earth/okabe_ito + npg/aaas/lancet/nejm), 选型规则见 `references/color_typology.md`.

> v7.4.0 两套 schema 不混用: **图表计划** (`generate_paper_plan.py` 输出, 进 decision_log) 五要素 = role / supports_claim / upstream_data / required_checks / palette; **生成输出契约** (上图 Type 3 论文图 JSON) 五要素 = claim_supported / source_artifact / caption / qa / palette. 计划描述"要什么图", 契约描述"生成了什么图", 字段名各自独立, 不得互相搬用.

---

## 图原型四分类（v7.5.0 新增）

> v7.4.0 的 Type 1-4 按**去处**分（诊断/对比/论文/附录）; 图原型按**画布构成**分, 回答"这张图的版面长什么样"。两者正交: 每张 Type 3 论文图都要再登记一个原型。每个图表计划（五要素 schema）新增备注 `layout_prototype` 字段登记原型。

| 原型 | 画布构成 | 适用 | 典型例 |
|---|---|---|---|
| 定量网格 | 2-6 个等尺寸子图阵列 | 多模型/多指标系统性对比 | 2×2 灵敏度矩阵、ROC×PR 双联 |
| 示意主导 | 示意图占 40-60% 画布, 数据图为辅 | 机理/流程/结构先行, 数据佐证 | 模型框架图 + 一小块收敛曲线 |
| 数据+图例混合 | 主数据图 + 侧栏图例/注释块 | 分组多、需旁注解释的分类图 | 分组条形图 + 色彩语义侧栏 |
| 非对称混合 | 主图占 ~70% + 1-2 个小型辅助图 | 一主结论 + 局部放大/分布补充 | 趋势主图 + 残差小图 |

**panel 级证据规则**:

1. 不为填满画布加图——每个子图必须声明**独立证据贡献**（支撑哪句结论/回答哪个质疑）, 声明不出来的子图删掉或并入主图。
2. 定量网格里每个 panel 证据贡献不同才并列; 同质 panel（只换了个参数值）合并为一个 panel + 图例。
3. 原型登记后改版面构成 = 改图表计划, 走计划修订, 不只改脚本。

## 导出三格式纪律（v7.5.0 新增, v7.7.0 兑现）

论文图统一一次导出三格式。**v7.7.0 起由 `figkit.save_fig(fig, out_prefix)` 落盘**：默认一次写出 `{prefix}.png`（300dpi）+ `{prefix}.svg` + `{prefix}.pdf` 三文件并返回路径列表，模板脚本与手写图统一走这一入口，不再逐图手写 `savefig`。

| 格式 | 用途 | 关键设置 |
|---|---|---|
| SVG | 论文工程主文件, 改稿可直接编辑文字 | `svg.fonttype = none`（文字保留为文本, 不转路径） |
| PDF | LaTeX 排版嵌入 | `pdf.fonttype = 42`（TrueType, 嵌入字体可复制可检索） |
| PNG 300dpi | 存档 / Word 稿 / 检查预览 | `savefig.dpi = 300` |

两项字体设置 `templates/figures/style/mathmodel.mplstyle` 已内置（v7.5.0 起补齐 `svg.fonttype: none` 与 `pdf.fonttype: 42`）, 加载 mplstyle 后无需逐图设置; 用其他样式出图时须手动补这两项。设置动机: 文字不转路径 → 改稿期改字号/措辞**不用重渲染**, 直接在 SVG/PDF 编辑器里改; 重渲染意味着重跑数据链, 违反最小改动纪律。

输出契约的 `output_files` 三格式齐列（svg/pdf/png），直接取 `save_fig()` 返回的文件路径列表；至少 svg + png 两联，要求 LaTeX 嵌入时 pdf 同批落盘（v7.7.0 起 `save_fig` 默认已含 pdf，不再需要稿后补导出）。
