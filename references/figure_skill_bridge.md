> **分发版路由说明**: 本分发包不含上游参考 `scibox-diagram` 与 `scibox-figure` (sci-box 上游无正式 LICENSE, 不得再分发; 二者**不是本包内的可用本地路径**, 需要时请自行从上游获取), 详见 VENDOR_NOTICES.md。
> 公开路由走本包实际随附的内容: 示意图用 `templates/figures/scripts/render_drawio_pack.py` / `render_diagram_pack.py`, 数据图用 `templates/figures/scripts/render_modeling_pack.py`, 答辩/展示 HTML 用随包的 `templates/figures/vendor/diagram-design/` (MIT); scibox 独有的高密度示意图模板与非库图型 (tpe_surface、cv_roc_ci 等) 在分发版不可用, 属能力留白而非等价替代。
> 另: `templates/figures/gallery/golden/` 的 4 张实战成品图 (Q1_C1_field / Q2_C1_stages / Q34_C1_gridconv / Q4_C2_routes) 属非公开项目材料, 分发版按默认选择规则隔离 (该目录保留 3 张模板样张); 识图先行纪律照旧, 见该目录 README 的分发版说明。

# Figure Skill Bridge

本文件定义 mathmodel-studio 与画图能力的协作方式：让论文里的图表先有论证目的，再生成，最后做可读性检查。

视频、音频、遥感、点云、算法结构、物理机理与综合图的专项路由，以及备选图库生命周期，按需读取 `references/result_gallery.md`。

**规则优先级**：正式图和答案附件按 `references/figure_quality_layers.md` 分层验收。题面必交与科学正确高于图数/面板/节点/卡片建议；首轮正式图由 Agent 自动设计精修，旧接口和锁定风格保留。

需要组合或 A-F 任务范例时显式启用 `references/task_figure_examples.md`，旧模板默认调用不变。

---

## 图表能力总路由（1.4.0 起以此为准）

mathmodel-studio 图表体系 = 自写模板库（下节）+ **vendor 内嵌的上游 skill / 项目副本**（`templates/figures/vendor/`，出处与许可证见 `templates/figures/vendor/VENDOR.md`）。其中上游副本 scibox-diagram 与 scibox-figure 因上游未附正式 LICENSE，**不随公开仓库与分发包分发**——在公开/克隆环境里它们不是可用本地路径，公开路由按下方"开源分发版注意"走随包的模板与 MIT vendor。按需求路由：

| 需求 | 首选 | 备选/说明 |
|---|---|---|
| **论文示意图/技术路线图/研究框架图/阶段流程图**（密集信息架构、drawio 可编辑、答辩级质量） | 自写 `render_drawio_pack.py` 7 模板（1.3.1 两段式卡版 + v3.0.0 作战地图 ga3band，落盘过 drawio_check 门禁）; matplotlib 直出 PNG 用 `render_diagram_pack.py` 4 模板 | 需要更高密度的上游示意图模板时，用**未随公开仓库与分发包分发的可选上游参考** `scibox-diagram`（4 模板，content JSON 驱动: roadmap-5band / framework-3col / stageflow-3col / taskflow-land，体检走其自带 check_layout.py）——公开环境里不是可用本地路径，按需自行从上游获取（见下方"开源分发版注意"） |
| **照着参考图复刻示意图** | 自写 `render_drawio_pack.py` / `render_diagram_pack.py` 模板按参考图重建（像素标定 + 中间产物留档 + 迭代验收） | `scibox-diagram` 的 replication.md 高保真复刻路径（四件中间产物 + ≥3 轮迭代）同为未分发的可选上游参考，不随包提供，需要时自行获取 |
| **数据图（论文正文 Type 3/4）** | 自写 `render_modeling_pack.py` 25 件（统一色板 + figqa/figure_lint 硬门；v3.0.0 新增物理场 6 件与场景 2 件） | 图型不在库内时：走自写模板组合或随包的 `vendor/icarus-figures/`（MIT）；`scibox-figure` 的 11 件差异图型（cv-roc-ci / paired-raincloud / tpe-surface / marginal-grid 等）是未分发的可选上游参考，需要时自行获取 |
| **复杂多面板论文主图（证据链式构图）** | 新组合入口见 `references/task_figure_examples.md`；已有 Icarus 使用 ax 参数复用 | 单图、主辅或对照按论证需要选择，不限定每篇张数；旧项目沿用锁定样式 |
| **物理场·动力学图（等高线场/流场/相图/轨迹/频谱/三元图）与网络集合流图（桑基/弦图/网络图/venn）** | 等高线场/剖面族/路径叠加场**优先自写** `render_modeling_pack.py` 物理场 6 件（field-contour / profile-family / threshold-inversion / convergence-sequence / contrast-pair / route-on-field，v3.0.0）；流场/相图/频谱/桑基/弦图/网络图走 `vendor/icarus-figures/` paperfig 48 函数直调（`streamplot_field` / `phase_portrait` / `spectrum` / `sankey` / `chord` / `network_graph` 等） | ML 诊断（roc/pr/calibration/convergence）优先自写库，缺件才走 icarus |
| **TikZ 框架图/技术路线图（与正文同源 LaTeX，嵌入真实方法对象）** | `vendor/icarus-figures/examples/hero_tikz/` 5 个可编译范例 + 其 `.claude/skills/icarus-figures/references/framework-figures.md`（§K 原创独立 TikZ → `\includegraphics`，零编译风险） | drawio 路线图仍是默认；xelatex/ctex 链下 TikZ 中文节点需先冒烟编译一张 |
| **答辩 PPT / 网页 / 海报级图表** | `vendor/diagram-design/`（39 类编辑级 HTML/SVG，4px 网格 + 焦点色纪律） | 不进 LaTeX 正文；中文内容需自行换字体栈 |
| **交互式 HTML** | `math-figure-generator` 的 plotly/pyecharts 轨道 | — |

> **开源分发版注意（v2.0.0, v2.3.0 增补；2026-09-19 公开路由口径修正）**：`scibox-diagram` 与 `scibox-figure` 因上游未附正式 LICENSE，**未随公开仓库与分发包分发**；公开/克隆环境里二者**不是可用本地路径**（仅维护方本地工作副本可能保留），一律按"未分发可选上游参考"处理——需要其高密度示意图模板或非库图型时自行从上游获取并遵守其许可条款。公开路由一律走**实际随包保留**的内容：论文示意图自写 drawio 7 模板（`render_drawio_pack.py`）+ matplotlib 4 模板（`render_diagram_pack.py`）；数据图 `render_modeling_pack.py` 25 件，缺图型接 `vendor/icarus-figures/`；答辩/网页/海报 `vendor/diagram-design/`（39 类编辑级 HTML/SVG）。二者均为 MIT，正常随附且分发版可用；icarus-figures 的使用约束（不启用 journal 列宽 / 产物出 vendor / 双质量门）见 `templates/figures/vendor/VENDOR.md` 第 6 条。

**vendor 使用纪律**：不改写 vendor 内文件；scibox-figure 默认把输出写在其自身 `绘图复刻/outputs/` 目录，出图后把产物移动到 `paper/figures/` 或 `results/`，不要把论文引用指向 vendor 内部路径。icarus-figures 路由的图（paperfig / TikZ）同样适用：先读其 `.claude/skills/icarus-figures/SKILL.md` 的硬规则（可复现脚本 + 三格式矢量 + 单位/不确定度上屏），产物落 cwd，再过本 skill figqa/figure_lint 门。

**图内注释与目视验收**：版心/字号按 `references/cn_presentation_spec.md` §7.2/§7.3；科学、交付、类型与设计建议分层见 `references/figure_quality_layers.md`。委派输入与回证按 `references/parallel_dispatch.md` 挂接点 3.5；终稿逐页视觉回证按 `references/cn_presentation_spec.md` §9.2。Agent 可完成机制图精修，未看图仍是草稿。

**识图先行：golden 样张先转"版式锚点描述"再委派（v3.1.0）**：出图委派前若存在 golden 样张（风格试产比选拍板样张、复刻参考图或模板 gallery 成品），**必须**先由视觉通道（vision-reader 类多模态角色，或主 agent 多模态自看；总则见 `references/parallel_dispatch.md` 模型档位路由）把样张转成结构化"版式锚点描述"随设计卡并入委派 prompt；**禁止只给样张路径让无视觉执行器自读**。版式锚点描述最小字段集：面板布局（行列数与各面板内容主次）/ 轴与单位（各面板轴标签原文与单位）/ 色条与图例（有无、位置、条目形态）/ 判据线形态（线型、颜色、图例标注方式）/ 量化标签形态（柱顶数值、图例 R²、面板计数等）/ 面板标号样式（(a)(b)(c) 的位置与字号层级）。依据：2026 国赛 A 题实测中视觉通道先把 7 张 golden 样张逐字段转成版式锚点再喂给无视觉的出图执行器，出图一次过门率显著提高；本条即 `references/parallel_dispatch.md` 挂接点 3.5 第 ⑥ 条。

---

## 图叙事与示意图分野（v3.0.0 起以此为准）

本节维护设计卡与构图选择；历史样本不等于全部论文已经完整阅读或视觉审查。题面与实际结果优先，科学/交付/设计层级见 `references/figure_quality_layers.md`。图题与版心见 `references/cn_presentation_spec.md` §7，颜色见 `references/color_typology.md`。

### 1. 两个分野总原则（数据图 ≠ 示意图）

- **为什么**：两类图失败模式不同——数据图败在数字漂移与不可复现，示意图败在低密度模板图；一条流水线套两类图必然牺牲一方。
- **怎么做**：数据图由代码和冻结结果生成；机制图保留可编辑源与真实方法关系。两类均由 Agent 完成设计、渲染、检查与必要精修；规则见 `references/figure_quality_layers.md`。旧草稿必须经审查生成新候选，不能以删除 `.draft` 后缀代替验收。
- **自查**：每张图先归类分野；数据图无 figqa/figure_lint 门禁记录 = 不入库；示意图仍带 `.draft` 后缀 = 不进正文。

### 2. 图叙事设计卡（每张正式展示图，探索阶段不强制）

- **为什么**：优秀论文的图先有论证目的再有工艺；没有设计卡的图最容易退化成"跑完代码顺手出图"。
- **怎么做**：沿用图表登记，记录 ① 回答的问题，② 图型及理由，③ 可追溯数据/判据/对照，④ 版心与标注，⑤ 一眼所见。证据层按用途选择，不为凑两层添加无关判据；原 mask/空间答案按题面检查。常规标注由 Agent 决定，既有数学字体政策保持；只有改变锁定政策才询问。字号与注释参考 `references/cn_presentation_spec.md` §7，适用边界见分层验收。
- **数学字体正斜政策**：`figkit.apply_style` 由调用方显式传参，不读取 decision_log。`upright_math=True` 为全局正体，`False` 显式复位为常规斜体，`None` 保持现有 rc 状态。沿用已登记政策；未经授权不改变锁定政策。三态实现见 `templates/figures/scripts/figkit.py`。
- 设计卡登记进 `真源.md` 图表登记表，复用已有信息；D.1 按下节处理已有授权与需要确认的科学决策。
- **自查**：五要素任一项写不出 = 先补设计再动代码；出图后对照 ⑤ 自问"评委第一眼看到的是它吗"——不是则改构图，不是加注释。

### 3. 作战地图（需要全局依赖概览时）

- **为什么**：整体依赖与关键结果的概览有助于定位论证；不把历史样本观察当作所有题目的普遍要求。
- **怎么做**：确有全局依赖说明价值时，使用子问题色带、真实依赖箭头和结果缩略；stage 2 纳入计划、stage 8 按真实结果生成。不强制整页或每篇一张；Agent 按第 1 条精修并验收。
- **自查**：色带覆盖全部子问题；箭头是真实因果/依赖而非装饰；每张缩略图能在 `figures/` 找到同名成品。

### 4. 判据线纪律

- **为什么**：判据线画进图内是"物理严谨"的第一图面信号（特征频率虚线、R²=0.7 阈值虚线、容量红虚线、β 参考线加粗）。
- **怎么做**：凡图支撑的结论带阈值/判据/基线/理论值，必须画进图内——线型与颜色按 `references/color_typology.md` 配色语义表（判据线红虚线、基线/参考灰黑虚线），图例注明判据值；无判据可画时在设计卡写明"本图无判据层"的理由，不留默认沉默。
- **自查**：逐图念出它支撑的结论——结论含阈值/判据/基线/理论值而图内无对应线 = 补线，或改结论表述。

### 5. 对照式构图优先

- **为什么**：优秀论文的对照一律同坐标（迁移前后同坐标对照、原图-真值-预测三联、raw vs aligned 分布）；两张独立图把对齐工作转嫁给评委。
- **怎么做**：存在对照关系（前后/有无/两法/两档网格/官方 vs 模型）时默认同坐标对照面板（共享坐标轴与色标），不画两张独立图；对照面板各自仍是独立证据，遵守下文"图原型四分类"的 panel 级证据规则。
- **自查**：本问结论是否隐含对照关系；有而画成两张独立图 = 合并为对照面板。

### 6. 量化标签

- **为什么**：图自证可信，评委不用回正文找数（实测形态：像素计数 9,295→5,607→3,261、面板标数据点数、柱顶数值、图例写 R²=0.8129）。
- **怎么做**：过程图面板带量化计数（像素数/样本数/迭代数/数据点数）；柱状图柱顶标数值；拟合/预测图图例带 R²/N/AUC；地图/GIS 类带比例尺与色条。标签数字必须来自冻结结果，不得手抄估算。
- **自查**：没读过正文的人看图 10 秒能否复述关键量级；每个量化标签能否在结果登记表/冻结文件找到出处。

### 7. 用途类型（可多选）

- **为什么**：答案图本身就是交付物（概率热力图、编号 t-SNE、官方路线 vs 模型路线同底图对照）；用途不清的图既不支撑结论也不交付答案。
- **怎么做**：登记答案/机制/验证用途，可多选；作战地图是一种构图。定量展示可考虑数值、判据和对照；原 mask、空间答案等按题面格式验收，不强制三选二。
- **自查**：用途、来源和必交对象齐全，类型专属检查见分层验收。

### 8. 不学清单（优秀论文也犯的错）

- **为什么**：常见错误包括图号重号、题注错配、引用断链、不可追溯素材、坐标截断夸大差异和低信息重复面板；不以未经核验的论文覆盖量背书。
- **怎么做**：不粘贴教材/文献/AI 生成图（示意图必须自绘，走第 1 条草稿通道）；不刷同版式低增量重复面板（同质 panel 合并，独立证据贡献声明见"图原型四分类"）；图题/编号/引用逐条人工核对；禁纵轴截断夸大差异（确需截断时显式标断轴并说明）。
- **自查**：终审对 `figures/` 全目录核对——外部图片零来源、重复版式面板逐个有独立证据贡献、图表引用闭合（`scripts/consistency_audit.py`）。

---

### 3.7 出图决策菜单（D.1 口径 · 唯一权威源）

> 本节承接原 stage_05「D.1 图表选择菜单」的细则（v2.3.0 起为必停点，v3.0.0 加叙事确认，v3.1.0 加合并形态）。stage 文件只写"出图前必须过 D.1 必停点"并指回本节。

每个 Qi 求解并验证通过后、进入正式生成前，登记 `checkpoints.figure_menu["Q<i>"]`（形状见 `references/workspace_protocol.md` §12）。已有明确授权由 Agent 决定时直接据真实对话登记下列内容；缺决策或触及科学/成本/锁定风格边界时才呈现菜单等待回答：

1. **本问图表数量**：`1) 0 张  2) 1 张  3) 2 张  4) 3+ 张  5) 让我决定`（0 张意味着该问以表格呈现结果，需用户显式选）。
2. **样式风格**（选项取自本文件顶部总路由表）：自写 25 件数据图（统一色板）/ vendor icarus 多面板主图 / 物理场·网络流图 / 示意图 drawio / TikZ 框架图。
3. **叙事结构确认**（v3.0.0）：对拟出的每张图逐图念出图叙事设计卡的 ① 回答什么问题、② 图型选择及为什么、⑤ 评委一眼应看到什么；用户可当场改叙事——**图型与构图跟着叙事走，不是反过来**。

纪律：正式图须有有效授权与登记；探索图可直接生成至 `results/figures_diagnostic/`，未经正式审查不可进稿。

**0/1 张的披露登记**：图表数量不设评分下限，但选 0/1 张属低频决策，agent 必须先说明该问的证据呈现方式（表格/文字替代）；`figure_menu["Q<i>"]` 条目追加 `"count": <0|1>, "exception": true` 与理由，并在 `真源.md` 图表登记表同步标注——登记用途是决策追溯，不是扣分豁免。

**合并菜单形态**：需要补决策时，可在各 Qi 验证完成后一次呈现全篇计划；已授权自动设计则直接逐问登记。已有字段 `menu_form: consolidated_4q_single_round` 只用于真实合并问答，保留兼容，不把一次笼统确认冒充科学决策。每问均保存数量、narrative 与依据，题面必交覆盖独立核对。

**风格试产比选（v2.7.0，全文首次出图前必做）**：第一次出图前，先用 1-2 张最有代表性的图各产 2 套风格样张（如 academic_blue 期刊风 vs paperfig/icarus 风），**渲染成图**后给用户比选（样张本身也走识图先行：先转版式锚点描述再入委派 prompt），拍板一套作为全文统一风格并写入菜单登记与 `真源.md` 图表登记表；后续各问只沿用，不逐问重选。用户明确说"沿用上次/你定"时可跳过并登记。

**与 Stage 2 证据需求的衔接**：stage 2 登记待回答问题和数据来源，图型暂定；小实验与正式验证后，本节菜单落实数量、样式和叙事并冻结正式规格。修订须回写登记表，实验驱动规则见 `references/experiment_cycle.md`。

---

## 本地图表模板库（1.1.0 自写版，优先复用）

**在调用外部 skill 之前，先检查 `<skill>/templates/figures/scripts/` 是否有现成模板可用。** 现库 25 件数据图模板（`templates/`）+ 4 件示意图模板（`diagrams/`）+ 7 件 drawio 可编辑模板（`drawio/`，含作战地图 ga3band），全部为本 skill 自写的确定性脚本，统一接入 `templates/figures/style/palettes.py` 色板与 mathmodel.mplstyle，直接用能省时间且保证可复现。

**入口**：`python <skill>/templates/figures/scripts/render_modeling_pack.py <id> --out <目录>`。常用 id：`tornado-sensitivity`（灵敏度龙卷风）/ `optimization-allocation`（优化分配，甘特/堆叠双模式）/ `multiscenario-robustness`（多场景稳健性）/ `technical-route-flowchart`（技术路线图，确定性布局 + 中文换行）。**完整 25 件清单及别名以 `render_modeling_pack.py --list` 为准**（含 roc-pr / taylor-diagram / raincloud / circular-heatmap / confusion-matrix / shap-summary / chord-diagram 7 件，以及 v3.0.0 新增 field-contour / profile-family / threshold-inversion / convergence-sequence / contrast-pair / route-on-field / answer-grid / before-after 8 件）；需要可编辑流程/机理图时用 `render_drawio_pack.py`（7 模板：roadmap / framework / flow3col / stageflow / swimlane / mechanism / ga3band），draw.io 打开微调后导出 PNG/PDF/SVG。

**使用约定**：
- 每个模板经 `figkit.save_fig()` 一次落盘 PNG(300dpi) + SVG + PDF 三格式，确定性种子可复现；模板自带"示例数据"，替换为真实结果数据后再进论文；色板与样式默认取 `templates/figures/style/`，自定义须符合 `references/color_typology.md`。
- 出图后跑硬门：`python <skill>/scripts/figqa.py <图脚本/目录> --strict`（`technical-route-flowchart` 与示意图固定加 `--allow-box-labels`，盒内文字是合法版式）+ `scripts/figure_lint.py`。
- `figure_lint.py` 的语义分层（v3.1.0，清单 A7）：**硬门禁是 figqa 的像素碰撞**（`--strict`）；figure_lint 的 `--strict` 只拦 error 级、warn 列清单供逐条确认，需要 warn 也拦时用 `--strict-warn`。R9 注释预算对等值线数值标签（`ax.clabel`）与"纯数值+单位"串豁免（后者按词法判定：去掉数字与数值装饰后每个 token 只能是单位词——`30 ℃`/`0.3 kg/kg` 豁免，`Model improves after 10 iterations` 仍计注释）；设计卡已声明"格注+色条并存"理由时用 `--grid-annotate` 跳过 R4。判据与实测依据见 `scripts/figure_lint.py` 模块头。
- **两类检出的措辞纪律**（不得把启发式写成确定性）：① **旋转刻度标签**类重叠——旋转矩形相交并不等于墨迹重叠（零墨迹重叠也可能相交），此类命中按告警处理并交人工判读，**不得写成"确定性硬失败"或"真字形判定"**；② **目录批量跑**——逐个脚本记录结果，**缺可选依赖或单个脚本失败记为失败并继续检查其余脚本**（不中断整批），失败绝不计为通过。两者当前行为以 `scripts/figqa.py` 的实现与 `--help` 为准。

**调用流程**：① 用户描述需求 → agent 按总路由表与 `--list` 选模板 id；② 运行 `render_modeling_pack.py <id> --out <workspace>/figures/`（或直接运行 `templates/figures/scripts/templates/make_*.py`）；③ 输出改名为符合论文命名规范的 `paper/figures/Fig_Q*.svg/png`；④ 替换示例数据为真实结果数据；⑤ 检查输出契约字段（见文末）并跑 figqa/figure_lint 硬门。

---

## 已安装画图相关 skills

优先使用三类：`figure-table-planner`（规划每问需要哪些图表，按诊断/对比/论文/附录图分类；Stage 5 结果出来后、Stage 8 写作前）、`math-figure-generator`（生成数模论文图：评价图、预测图、优化结果图、灵敏度图、流程图、热力图、多子图）、`nature-figure`（高标准论文图质检：结论、证据链、可编辑 SVG/PDF/TIFF、字号与重叠风险；Stage 9 终审用）。辅助：`canvas-design` 只用于海报/封面/宣传视觉；`web-artifacts-builder` 只用于交互网页 demo；`algorithmic-art` 只用于艺术图像——三者都不用于竞赛论文证据图。

---

## 三段式工作流

### 1. 先规划

生成前先用 `figure-table-planner` 的四类图表分类：Type 1 诊断图（通常不进正文；残差/异常值/相关性/收敛，留 `results/figures_diagnostic/`）、Type 2 对比图（可选）、Type 3 论文图（必须进；支撑正文核心结论）、Type 4 附录图（补稳健性、完整场景与细节）。每张图必须写清：支撑哪句结论、数据来源路径、放哪一节、是否已有结果。

### 2. 再生成

按任务选图与本地模板（优先复用）：

| 任务 | 推荐图 | 本地模板 |
|---|---|---|
| 评价排序 / 分类评估 | 排序条、雷达、热力图、ROC-PR、混淆矩阵 | `taylor-diagram` / `circular-heatmap` / `radar-evaluation` / `ranking-bar` / `roc-pr` / `confusion-matrix` |
| 预测拟合 / 分布对比 / 模型解释 | 真实-预测散点、云雨图、SHAP | `prediction-fit` / `correlation-heatmap` / `raincloud` / `shap-summary` |
| 关系网络 / 优化结果 | 弦图、流向；分配柱状、堆叠、路径、Pareto | `chord-diagram` / `optimization-allocation` / `pareto-front` / `route-on-field` |
| 灵敏度 / 稳健性 | 龙卷风、扰动曲线、多场景分位 | `tornado-sensitivity` / `multiscenario-robustness` |
| 物理场 / 收敛 | 等高线、剖面族、阈值穿越、收敛序列 | `field-contour` / `profile-family` / `threshold-inversion` / `convergence-curve` / `convergence-sequence` |
| 流程说明 | 工作流图、模型结构图、算法流程图 | `render_drawio_pack.py`（7 模板）或 `technical-route-flowchart` |
| 超参搜索 / 未来预测 | 优化曲面 / 折线 + 置信区间 | 无现成模板，走 `math-figure-generator` |

默认展示输出：`paper/figures/*.svg` 主文件 + `*.png` 备用；展示栅格在最终版心检查 300 dpi，原像素答案不重采样。字号在最终尺寸不低于 7 pt，终审推荐 ≥9 pt。

### 3. 最后质检

Stage 9 或用户要求"终审图表"时按 `nature-figure` 的质检思想：图是否只表达一个核心结论；每个 panel 是否提供独立证据；文字是否可读、无出界重叠；坐标/单位/图例是否齐全（图注在图下方而非图内）；同一模型或方法在全文是否同一颜色；是否有可编辑 SVG/PDF 版本。

### 3.5 示意图双门：机器体检 + 渲染目检（1.3.1，流程图/框架图/路线图必走）

机器体检只能查"硬伤"（溢出/越界/重叠/穿盒），查不出"平庸"（密度低、层级平、重心散）。所有示意图进论文前必须过两道门：

**第一道 · 机器体检（自动）**：matplotlib 示意图跑 `figqa.py <脚本或目录> --strict --allow-box-labels` 零检出；drawio 示意图由 `finalize()` 落盘自动跑 `drawio_check.py`（FAIL 即退出码 1），手工改过的 `.drawio` 交付前手动补跑 `python templates/figures/scripts/drawio/drawio_check.py <file>`。三个 WARN 级"平庸信号"要当真处理：全字加粗 / 实心盒 >20 / 连线描边 >2.0。

**第二道 · 渲染目检**：打开真实渲染图及最终入文尺寸，检查文字/线条遮挡、关系方向、对齐、术语数值、视觉主次、字重、密度和留白。发现缺陷修源重渲；通过后不强制重复轮次。卡片、母线、焦点数和拆图只是机制流程图建议，不套用真实网络、物理几何或原始影像；视觉能力不可用时登记未完成。

### 3.6 图内标题与标注纪律（1.4.1 新增；v2.8.0 指针化）

数据图（Type 3）图内不放图名/结论句、"保留项"清单与 panel 短标签（≤6 个中文字符当量）的完整口径唯一权威源是 `references/cn_presentation_spec.md` §7.2，本文件不重述。此处只登记工具侧门禁与豁免通道：**示意图豁免**（流程图/技术路线图/框架图的标题条是版式组成部分，走 `--allow-box-labels` / `--allow-infigure-title` 通道）；**门禁**（`figure_lint.py` R8：非空 suptitle 或单面板 set_title 报错，多面板标题超宽警告；示意图等特殊版式用逃生门 `--allow-infigure-title` 跳过）。

---

## mathmodel 调用规则

| 用户说法 | 使用策略 |
|---|---|
| "帮我规划图表" | 先走 `figure-table-planner`，输出每问图表计划 |
| "根据结果生成图" | 先确认数据路径和图要支撑的结论，再走 `math-figure-generator` 或本地模板 |
| "美化这张图" | 用 `math-figure-generator` 重画或改样式，保留原数据 |
| "终审图表" | 用 `nature-figure` 质检规则，输出问题清单和修改优先级 |
| "画流程图" | 论文流程/算法流程用 `math-figure-generator` 或 drawio 模板；艺术海报才用 `canvas-design` |

## 禁止事项

不为没有数据或结果的结论编造图；不把诊断图冒充论文图；配色统一走 `references/color_typology.md` 与 `templates/figures/style/palettes.py`（八套色板含四套期刊板 npg/aaas/lancet/nejm、中性色令牌、灰度校验、语义绑定）——不用默认 tableau 直出、不用彩虹色、不让同一方法在不同图里换颜色；不把关键证据只放附录；不生成没有图注、坐标单位和正文解释的 Type 3 论文图。

---

## 输出给论文的最低标准

每张 Type 3 论文图至少登记：`figure_id` / `type` / `claim_supported`（支撑的一句话结论）/ `source_artifact`（上游结果路径）/ `paper_section` / `output_files`（svg/pdf/png 三格式路径）/ `caption`（图注，逐字来自真源图表登记表"终稿图注"列）/ `template_used`（本地模板路径，纯外部生成填 `null`）/ `palette`（八套色板之一）/ `qa`（`axis_units` / `caption_ready` / `font_readable` / `no_overlap` / `color_consistent` 五项为真）。

> **两套 schema 不混用（0.7.4）**：**图表计划**（`generate_paper_plan.py` 输出，进 decision_log）五要素 = role / supports_claim / upstream_data / required_checks / palette，描述"要什么图"；**生成输出契约**（上图）描述"生成了什么图"。字段名各自独立，不得互相搬用。

## 图原型四分类（0.7.5 新增）

> 0.7.4 的 Type 1-4 按**去处**分，图原型按**画布构成**分，两者正交：每张 Type 3 论文图都要再登记一个原型（图表计划五要素 schema 的备注 `layout_prototype` 字段）。

| 原型 | 画布构成 | 适用 | 典型例 |
|---|---|---|---|
| 定量网格 | 2-6 个等尺寸子图阵列 | 多模型/多指标系统性对比 | 2×2 灵敏度矩阵、ROC×PR 双联 |
| 示意主导 | 示意图占 40-60% 画布, 数据图为辅 | 机理/流程/结构先行, 数据佐证 | 模型框架图 + 一小块收敛曲线 |
| 数据+图例混合 | 主数据图 + 侧栏图例/注释块 | 分组多、需旁注解释的分类图 | 分组条形图 + 色彩语义侧栏 |
| 非对称混合 | 主图占 ~70% + 1-2 个小型辅助图 | 一主结论 + 局部放大/分布补充 | 趋势主图 + 残差小图 |

**panel 级证据规则**：① 不为填满画布加图——每个子图必须声明**独立证据贡献**，声明不出来的删掉或并入主图；② 定量网格里每个 panel 证据贡献不同才并列，同质 panel（只换了个参数值）合并为一个 panel + 图例；③ 原型登记后改版面构成 = 改图表计划，走计划修订，不只改脚本。

## 导出三格式纪律（0.7.5 新增, 1.1.0 兑现）

旧模板保持 `figkit.save_fig(fig, out_prefix)` 的 PNG(300dpi)/SVG/PDF 路径与失败语义。显式组合用 `export_revision` 保持物理版心并记录完整性，见 `references/task_figure_examples.md`。两条路径的展示成品均检查实际内容；SVG/PDF 可能嵌有位图，不能凭后缀宣称全矢量。原 mask/原始影像附件保持题面尺寸编码，不套展示 dpi 或三格式要求。图注仍来自真源，最终尺寸与类型检查按分层验收。
