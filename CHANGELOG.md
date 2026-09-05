# Changelog

本文件记录 mathmodel-studio 的全部重要变更。条目整理自 SKILL.md 与 README.md 的版本史（V1—V7.4 原文照抄）。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## 版本号映射表（v2.0.0 统一版本线）

历史曾存在三条编号线（V1—V7.5、V1.0.0 重置、v7.7—v7.10 回摆）。自 2.0.0 起统一为一条单调语义化线，映射如下：

| 旧编号 | 新编号 | 一句话 |
|---|---|---|
| V1 / V2 / V3 | 0.1.0 / 0.2.0 / 0.3.0 | 初次搭建 / 审计修复 20 条 / 模板瘦身 |
| V4 | 0.4.0 | 多竞赛通用化 + per-Qi 加权聚合 |
| V5 | 0.5.0 | harness 兼容 + 问答式交互 |
| V6 / V6.1 / V6.2 / V6.3 / V6.3.1 | 0.6.0–0.6.4 | Codex 打包 / dry-run 强化 / APMCM / 实战工作台 / 图表桥接 |
| V7.0 / V7.1 / V7.2 | 0.7.0 / 0.7.1 / 0.7.2 | 华数杯蒸馏 / CUMCM 纠错 / 华为杯 190 篇深蒸 |
| V7.3 / V7.4 | 0.7.3 / 0.7.4 | 三赛联合工作流 / 配色统一 + 工作区纪律 |
| V7.5 | 0.7.5 | 许可证剥离 + 评委模拟器 + 数字冻结 |
| V1.0.0（品牌重置） | 1.0.0 | 全资产自写 |
| v7.7.0 / v7.8.0 | 1.1.0 / 1.2.0 | 图表公共底座 + drawio 模板 / 示意图配色独立 |
| v7.9.0 / v7.9.1 | 1.3.0 / 1.3.1 | 版式令牌 + drawio 门禁 / 字重层级制 |
| v7.10.0 | 1.4.0 | vendor 内嵌三上游 + 图表路由重构 |

正文历史条目保留旧编号原文，按上表对照阅读。

## [2.2.0] — 2026-09-05（2025 届 21 篇深读入库 + 评测装置修复 + 2026 赛制核验）

- **新增（华为杯深读层）**: 2025 届 6 题 21 篇优秀论文全量逐篇深读（章节逻辑/逐问建模链/图表角色实判/可复用-不照搬/页码证据），并入 star_papers_deep.md 与 manual_paper_reviews.json（award=excellent_paper_selection, 不推测等级; figure role 逐图实判; 模板字段 null 或具体观察, 无模板填充）; 深读层现覆盖 2021 提名 12 篇 + 2025 优秀 21 篇
- **重构（华为杯写作层, 33 篇证据回流）**: writing_voice.md 扩容——新增 §3.5 推导写作（现实关系→符号化→逐条约束翻译→回到对象四步叙事 + 详略分级 + 式后三件套 + 计费口径对齐）、§5 由"结果报告"升级为"结果分析五步"（报→比→归因→分解→边界, 收录恶化逐 case 归因/负结果叙事/p 值裁决等 33 篇实证动作）、§6 结论三招（呼应题问原句/未完成如实写/局限写成条件清单）, 证据基础由 4 篇扩至 33 篇; 新增 writing_playbook.md（优化调度/预测回归/识别重构/监测诊断迁移/主观指标评价 5 题型分册: 公式-推导-结果分析差异化重点+动作+反例）; 新增 writing_examples.md（摘要/语气/公式/推导句/图解/结果归因/结论 7 类正反例对照库）; stage_08 局部写作路由与 SKILL.md 加载行同步
- **修复（评测装置）**: run_eval figqa 目标发现（figures/scripts/code 三目录扫 .py）+ --strict 使碰撞退出码可达; stage 5 新增 evidence_ledger 逐问追加（trace_claims 在短程评测不再恒 skipped）; holdout_protocol 判读提示
- **核验（当年规则）**: current_rules.md 依据第二十三届参赛通知全文初核（转载源+高校转发交叉印证, 待研创网原文确认）——赛制 100h（09-23 8:00→09-27 12:00）、MD5/PDF 双窗口提交、奖项结构; AI 披露未见专项条款; 标准文档相关项保持待核验（09-22 补齐）; 72h 作战表加 100h 重映射提示
- **变更**: distill_huaweibei_cases.py 重跑对齐统计/哈希层
- **终审修复**: 全库 33 篇深读覆盖口径统一（SKILL 矩阵/stage 00/README/architecture）; retrieve_cumcm_cases 身份显式分支（非 2021 即 2025 的隐式假设消除）; writing_examples 假章节引用改占位符; current_rules 待核验项数量与初核状态口径修正; "100h 实测"改"通知口径"; stage_05 evidence_ids 标注为溯源元数据（trace_claims 审计前六项）
- **新增（md 格式规范 + 公式编号升级）**: references/md_authoring_spec.md——md 真源的公式/符号/题注/编号规范, 依据 pandoc 3.8 双链实测（公式=Word 原生 OMML 对象、\tag 在 docx 链被静默丢弃、表题注在上/图题注在下天然成立）; render_paper.py 新增编号公式升级——md 中 $$…\qquad (N)$$(及误用的 \tag{N})在 PDF 链自动升级 equation 环境（居中+编号右顶格+自动重排）, docx 链保留块内右侧编号; 编辑器推荐 Typora→Obsidian(个人免费)/MarkText(开源)/VS Code 兜底; README 增"论文怎么写、怎么导出"流程图一节

## [2.1.0] — 2026-09-05（docx 审阅件导出：补齐协议既有承诺）

- **新增**: scripts/export_docx.py——从 paper_workspace md 真源导出带时间戳的 docx 审阅件（pandoc, 数学转 OMML, --reference-doc 样式, --dry-run）; 补齐 workspace_protocol 早已承诺但无实现的 docx 导出
- **协议**: workspace_protocol.md 新增 "docx 审阅件协议" 一节 (docx=审阅件, md=真源, 批注由 agent 合回, 禁止反向覆盖)
- **兵检**: 环境检查表加 pandoc 一行; 素材自查表加写作队员编辑器一行
- **审查修复**: 图片资源路径解析(resource-path)+同分钟覆盖保护+competition 文件名校验+异常路径受控(dry-run/清理/编码)

## [2.0.0] — 2026-09-04（版本线统一 + 开源前整顿）

自此版本起废弃历史双线版本号（7.5.0 → 1.0.0 品牌重置后又继续 7.7.0—7.10.0 的混乱），统一为语义化版本，后续严格递增。

- **统一**: SKILL.md 头部 / plugin.json / README 徽章全部对齐 2.0.0；SKILL.md 内联的 15 段历史更新日志移出，只留本文件指针（热路径 -88 行）
- **修复（华为杯知识库注水点）**: manual_paper_reviews.json 4 个模板填充字段加 provenance 标注；figure_table_logic 机械轮转角色修正事实性错标并降权；manual_review_annotations.json 清除 48 个 OCR 噪声证据键；17 个无鉴别力题的逐问绑定降级为 case_level；rating_contract 华为杯校准锚标注为未验证假设；index.json 2025D 坏标题修正；case_retrieval.md 评分公式改为与实现一致
- **新增**: scripts/distill_huaweibei_cases.py 可复现蒸馏流水线（统计+哈希层）；evals/ holdout 评测协议；references/data_acquisition.md 数据获取协议
- **变更**: stage_05 每问求解后立即产出章节草稿卡（write-as-you-solve），stage_08 退化为组装与统一文风
- **清理**: vendor/scibox-* 开源分发排除方案（见 VENDOR.md §5）；.agents 安装副本改 symlink 防漂移


## V7.10.0 — 2026-09-04（收编上游原版：vendor 内嵌 + 图表路由重构）

把 scibox-diagram / scibox-figure / diagram-design 三个上游 skill 的**原样副本**内嵌进 mathmodel-studio（`templates/figures/vendor/`），从"蒸馏复刻"升级为"自写体系 + 原版引擎"双轨：skill 自包含，不再依赖兄弟目录安装。

- **新增**：`templates/figures/vendor/{scibox-diagram, scibox-figure, diagram-design}/` 三个上游原样副本（上游更新时整目录替换，本地不改写）+ `vendor/VENDOR.md` 出处/许可证/使用纪律说明。scibox-diagram：论文示意图 drawio 4 模板（五带路线图/三栏框架/三栏阶段流程/横版任务流水线，content JSON 驱动，单模板 99+ 图元的高密度信息架构）+ 从零手写与高保真复刻纪律 + check_layout.py 体检 + 100 个 Tabler 图标；scibox-figure：11 件科研绘图复刻模板（cv-roc-ci / paired-raincloud / tpe-surface / marginal-grid 等本 skill 未覆盖图型）；diagram-design v2.6：39 类编辑级 HTML/SVG 图表（答辩/展示场景，LICENSE.upstream 已随附）
- **变更**：`references/figure_skill_bridge.md` 顶部新增图表能力总路由表——论文示意图高密度交付默认走 vendor scibox-diagram；自写 drawio 6 模板保留为轻量快速路径；数据图仍以自写 17 件为默认（统一色板 + figqa/figure_lint 硬门），缺图型转 scibox-figure；答辩/网页/海报走 diagram-design；照图复刻走 scibox-diagram replication 路径
- **许可证注意**：sci-box 上游仓库未附正式 LICENSE 文件（README 宣称开源，Tabler 图标 MIT 见 ATTRIBUTION.md）；再分发 mathmodel-studio 前须确认上游补证或将 scibox-* 移出分发包，详见 `vendor/VENDOR.md` §5
- **验证**：vendored scibox-diagram framework_3col 从 vendor 路径生成 131 图元 .drawio 且其 check_layout FAIL 0 / WARN 0；vendored scibox-figure taylor-diagram 三格式渲染通过（默认输出写其自身 绘图复刻/outputs/，路由文档已注明产物须移出 vendor）；自写体系自测无回归
- 自写体系（v7.8 色族 / v7.9 版式令牌与门禁 / v7.9.1 字重层级与两段式卡）全部保留：自写管 LaTeX 正文三格式出图与竞赛工作流，vendor 管高密度 drawio 与展示级 HTML

## V7.9.1 — 2026-09-04（追平 sci-box 信息架构：字重层级制 + 两段式富文本卡 + 质检升维）

与 sci-box/diagram-design 实物逐图对比后的差距修正版：v7.9.0 补齐了"纪律与门禁"，本版补齐"信息架构与字重层级"——差距分析结论：此前复刻了配色和零件但没复刻语义槽位，且"全字加粗"是对 sci-box 的误读（其内容卡正文为常规字重，只有旗标/标题条加粗）。

- **变更（L1 纪律修正）**：字重层级制取代"全字加粗"——加粗只给标题条/徽章/卡片标题，卡内正文与明细常规字重（`design_tokens.md` §4.5 修订，`diagram_box` 默认 `bold=False`，drawio 族化 `card()` 默认常规字重）；连线默认降重 lw 1.3 + 小箭头头 mutation_scale 11（连线退居二线）；描边令牌新增 card=1.0 档（`DIAGRAM_STROKE_W` 现为 hairline/card/default/strong = 0.8/1.0/1.2/2.0 四档）
- **新增（L2 结构化零件）**：`figkit.rich_box()` 两段式富文本卡（bold 标题行 body 档 + regular 明细行 note 档次级色，超框先缩明细再缩标题，`detail_mono=True` 时纯 ASCII 明细走等宽链）；`num_badge()` 圈号圆徽章；`vlabel()` 竖排标签（逐字堆叠，禁 rotate）；`footnote_bar()` 结论脚注条（左族色 tick + 左对齐小字）；drawio 侧 `Diagram.rich_card()`（`<b>` 标题 + `<font>` 降档明细，单元格级 fontStyle=0）与 `Diagram.vlabel()`
- **变更（L3 模板语义槽位重写）**：mpl + drawio 的 roadmap/framework 共 4 个模板从"一行文字通用卡"升级为语义槽位版式——节点 = (标题, 明细) 槽位、色带右缘竖排阶段目标（roadmap）、行圈号徽章（framework）、图末结论脚注（roadmap）；roadmap 层间扇入箭头修正为"无头折线+竖直箭头"两段路由（消灭横抵盒顶的侧向箭头）；示例数据升级为含明细行的真实感内容；均向后兼容 v7.8.0 纯字符串调用（退化为单行卡）
- **新增（L4 质检升维）**：`drawio_check.py` 三个 WARN 级平庸信号——全字加粗（≥5 个文字元素且 >90% 加粗）/ 实心盒 >20（密度超预算，建议拆总览+细节）/ 连线描边 >2.0（强调用色不用粗）；`figure_skill_bridge.md` 新增 §3.5 示意图双门（机器体检 + 渲染目检九区盘点清单，"不看渲染图不算画完"入流程）
- **验证**：figkit/drawio_builder 自测通过（含 rich_box/rich_card/vlabel 冒烟与字重回退断言）；mpl roadmap/framework 重渲 + 渲染图人工验收通过；6 个 drawio 模板门禁全过（roadmap/framework 两重写模板 FAIL 0 / WARN 0）；figqa 硬门 diagrams/ 0 检出

## V7.9.0 — 2026-09-04（编辑级排版纪律 + drawio 版式门禁）

在 v7.8.0 配色分类的基础上，把 diagram-design（cathrynlavery, MIT）的编辑级排版纪律与 sci-box scibox-diagram（jihe520，上游未附 LICENSE，见 VENDOR.md §5）的中文示意图工程纪律蒸馏进示意图体系：色值层（v7.8.0）之上补齐**版式令牌层 + 连接器纪律 + 机器体检门禁**。

- **新增**：`palettes.py` 版式令牌层 — `DIAGRAM_GRID`（4px 网格硬规则）/ `DIAGRAM_RADIUS`（圆角阶梯 sm/md/lg=4/6/8，上限 10）/ `DIAGRAM_STROKE_W`（描边三档 hairline/default/strong=0.8/1.2/2.0）/ `DIAGRAM_FONT_RAMP`（扁平字阶 title/header/body/note=16/12/10.5/9）/ `DIAGRAM_FONT_MONO`（数字/参数标签等宽链 Consolas→DejaVu Sans Mono→Courier New）/ `DIAGRAM_FOCAL_MAX=2`（焦点盒上限）；取口 `get_diagram_token()` 与 `snap4()` 网格捕捉，全部进自测
- **新增**：`figkit.py` 示意图助手 — `load_diagram_token()/snap4()/mono_chain()/mono_text()`（mono 只给数字/参数标签，节点名永远 sans）、`fan_offsets(n)`（共边多连接器附着位 k/(n+1)）、`bus_fan_v()/bus_fan_h()`（"竖线+横母线+分支"一分多连接器，替代 N 条独立斜线）；`diagram_box(focal=True)` 焦点盒（族 accent 底 + strong 2.0 描边）；`diagram_box/diagram_header` 缺省字号/圆角/描边改走令牌
- **新增**：`drawio_builder.py` 纪律化 — `card(focal=True)` 焦点盒；`edge(exit_frac=/entry_frac=)` 分数锚点（沿边 0..1 附着位）与 `fan_edges()` 一分多自动扇出；`text(mono=True)` / `edge(mono_label=True)` 等宽数字标签；族化 `card()/header_bar()` 默认描边对齐令牌三档（族化卡 1.2，非族化保持 1.0 向后兼容）；`snap4()` 网格捕捉
- **新增**：`drawio_check.py` 版式体检门禁（`templates/figures/scripts/drawio/`，sci-box check_layout 移植，阈值对齐本 skill 宪法）— FAIL: 文字溢出/越出画布/重复 id/实心盒重叠(>30% 小盒面积)/连线穿盒/位图内嵌；WARN: 端点压盒边/疑似空盒/字号 >4 档/填充色发散；中文字宽按真实度量（east_asian_width: 全角=字号、半角=字号/2、行高=字号+3），与生成器 1.45/0.72 保守换行模型互补；虚线容器/点线分带/无描边底色块豁免重叠判定
- **变更**：`drawio_builder.finalize()` 落盘后自动运行 drawio_check（FAIL 即退出码 1；`MATHMODEL_DRAWIO_CHECK=0` 关闭，`MATHMODEL_DRAWIO_STRICT=1` 时 WARN 也判失败）；`render_drawio_pack.py` 质量门文案同步
- **文档**：`design_tokens.md` 新增 §4.6 编辑级排版纪律（先排栅格再写图元 / 4px 网格 / 圆角·描边阶梯 / 焦点盒规则 / 连接器六条军规 / 密度 4/10 与删除纪律（节点 >9 拆总览+细节）/ 中文排版预算（16px 字号 160px 盒每行 ≤9 汉字、竖排逐字 `<br>` 禁 `horizontal=0`）/ "机器体检 + 渲染图两轮目检"双门）+ §2 mono 字梯队 + §6 反模式新增 8 条；SKILL.md 更新说明与加载协议同步
- **验证**：palettes/figkit/drawio_builder 自测全过（含 focal/bus/mono/snap4 冒烟与非法入参分支）；6 个 drawio 模板经 dispatcher 全部 FAIL 0 / WARN 0；负例（溢出+重叠+越界+重复 id+位图）drawio_check 全部检出且退出码 1；4 个 matplotlib 示意图模板重渲 + figqa `--strict --allow-box-labels` 0 检出；4 个数据图模板（tornado/prediction-fit/ranking-bar/confusion-matrix）回归通过

## V7.8.0 — 2026-09-04（示意图配色体系独立）

示意图（diagram/流程图/架构图/技术路线图）配色与数据图表配色**彻底分类**，并 1:1 复刻 sci-box scibox-diagram（上游未附 LICENSE）的视觉风格：浅底色族 + 同族深描边 + 实色标题条 + 扁平字号全加粗。数据图表（templates/ 下 16 个 make_*.py）一行未动。

- **新增**：`palettes.py` 示意图色系注册表 — `DIAGRAM_FAMILIES`（7 族 × 8 角色: fill/stroke/accent/deep/header/header_stroke/edge/chevron, 色值蒸馏自 sci-box（上游未附 LICENSE））+ `DIAGRAM_PAGE` 页面令牌（ink #262626/title_bar #4F80BD/band_sep 等）+ `DIAGRAM_ORDER_GENERIC`/`DIAGRAM_ORDER_ROADMAP` 固定族序 + `DIAGRAM_FONT_FAMILY` 字体链（YaHei 真 700 粗体优先, Noto Sans SC 可变字体只做回退末端）+ `get_diagram_family/get_diagram_families/get_diagram_page` 取色接口（自测校验 8 角色完备与色值合法）
- **新增**：`figkit.py` 示意图助手 — `load_diagram_family/families/page/order`（palettes 优先, 失败走全量内联副本）、`use_diagram_font()`、`diagram_box()`（浅底+同族描边+墨黑加粗字卡片, 超高自动缩字号）、`diagram_header()`（实色标题条白字）、`family_edge()`（族色连接器）
- **变更**：5 个 matplotlib 示意图模板全部迁到新族系 — `make_technical_route_flowchart.py` **整体重写**（通栏实色标题条 + 4 阶段列实色标题条 + 虚线容器内容卡 + 列间/列内族色箭头, 消灭裸文本节点压线与画布底部大片空白, 弃内联私有色板副本）; roadmap 五带族序 = DIAGRAM_ORDER_ROADMAP（层带族 fill 底 + chevron 层名徽章 + 点线分带 + 下一层族 edge 箭头）; stageflow 阶段框改实色标题条样式（--highlight 改族 accent 描边 2.0）; framework 三栏绑 blue/orange/teal; module 弃 cool_nature（中心 grey 族 accent+header_stroke, 卫星每枚一族）
- **变更**：`drawio_builder.py` 族化 — 字体串统一 sci-box style（Microsoft YaHei,PingFang SC,Hiragino Sans GB,Helvetica）; `card()/badge()/header_bar()/lane()` 新增 `family=` 参数（不传保持 v7.7.0 行为向后兼容）; 新增 `dashed_container()`（4 4 虚线容器）与 `band_sep()`（1 3 点线分带）; 6 个 make_drawio_*.py 阶段/泳道/卡片/连线着色改按族取色（roadmap 用 ROADMAP 序, 其余 GENERIC 序, 结构布局不动）
- **变更**：字体排版纪律 — 示意图脚本 `apply_style()` 后 `use_diagram_font()`, 图内文字全 `fontweight="bold"`、墨黑 #262626（白字只在实色标题条上）, 字号扁平（标题 15-16 / 标题条 11-12 / 正文 10-10.5 / 注释 9, 全图不超过 3 档）; 卡片弃 soft_shadow（扁平风）
- **文档**：`color_typology.md` 新增 §2.4 示意图配色体系（分类原则 + 7 族色值表 + 取色 API + sci-box 来源（无 LICENSE，再分发受限））; `design_tokens.md` 新增 §1.5 色族令牌与 §4.5 示意图族版式（描边宽度体系: 卡 1.2 / 强调 2.0 / 容器虚线 1.2）; SKILL.md 图表桥接小节点明配色分类; render_diagram_pack/render_drawio_pack 描述文案同步
- **验证**：palettes/figkit/drawio_builder 自测通过; 5 张 gallery PNG + 6 个 .drawio 重新生成; figqa 硬门 `diagrams/ --strict --allow-box-labels` 与 `make_technical_route_flowchart.py --strict --allow-box-labels` 均 0 检出; 数据图表模板 figqa 回归无新增失败项

## V7.7.0 — 2026-09-03（图表体系升级）

图表模板包刷新、公共底座落地、期刊色板接入：全库图表配色统一收敛到 `templates/figures/style/palettes.py` 唯一权威源，三格式产出契约真正落地。

- **新增**：drawio 可编辑模板包 — `templates/figures/scripts/drawio/`（roadmap / framework / flow3col / stageflow / swimlane / mechanism 共 6 模板）+ `render_drawio_pack.py` dispatcher，零依赖 mxGraph XML 生成器（`drawio_builder.py`），draw.io 打开即编辑；每个模板落盘后内置 minidom 自验（XML 合法性 + 节点/连线计数）
- **新增**：7 个高级图表模板 — roc_pr / taylor_diagram / raincloud / circular_heatmap / confusion_matrix / shap_summary / chord_diagram（`templates/figures/scripts/templates/`），`render_modeling_pack.py` 现 17 件（10 旧 + 7 新）
- **新增**：figkit.py 公共底座 — `save_fig`（PNG+SVG+PDF 三格式一次落盘）/ `load_palette` / `apply_style` / `despine` / `ygrid` / `panel_label` / figsize 预设 / CJK 均衡换行 / 正交连接器 / 微阴影，取代各模板内联重复代码
- **新增**：设计令牌 — `references/design_tokens.md`（色板/中性色/字号/间距/圆角/连接器令牌出口）
- **新增**：palettes.py 扩展 — npg / aaas / lancet / nejm 四套真期刊色板（蒸馏自 ggsci 公开数据）+ NEUTRALS 中性色令牌 + tint / shade / tint_series 参数化浅化深化 + grayscale_check all_pairs 全对模式
- **变更**：14 个既有模板迁移 figkit（数据图 10 + 示意图 4）— 删内联色板副本、三格式 PNG+SVG+PDF 导出真正落地、网格 y 向化、示意图均衡换行 + 正交连接器 + 微阴影 + 中性色令牌
- **变更**：mplstyle 细化 — 刻度朝外 + 次级刻度 + 图例无边框
- **变更**：math-figure-generator 配色对接 — 该 skill 配色体系对接本 skill 唯一色源（palettes.py），废弃 Office 默认色系与截图衍生色板 C/D
- **修复**：framework 卡片左色条与圆角裁切瑕疵（示意图渲染缺陷）
- **修复**：示意图中文换行吊行（孤行字）
- **修复**：文档承诺 PDF 导出未兑现 — 旧模板只落 PNG+SVG，save_fig 三格式落地后补齐

## V1.0.0 — 2026-09-02（品牌重置 "数模工坊 MathModel Studio"）

自 V7.5.0 起全部资产为自写或自由许可，版本号重新从 1.0.0 起算；目录标识符保持 `mathmodel-studio` 不变，显示名暂定"数模工坊 MathModel Studio"。

- **建模规范知识库自写重建**：`references/modeling_norms.md`（六大题型判别信号/选型主线/高频陷阱/必做验证 + 数据处理/假设边界/量纲纪律 + 全局反模式表）
- **图模板库扩容至 14 件**：数据图新增雷达评价/相关性热力图/帕累托前沿/预测拟合/排序条形/收敛曲线 6 件（`templates/figures/scripts/templates/`，全部通过 figqa 零碰撞 + figure_lint 零错误）；新增示意图包 `templates/figures/scripts/diagrams/`（五带路线图/三栏框架/阶段流水线/模块框图 + `render_diagram_pack.py` dispatcher）
- **Stage 2 审题门强化**：边界查/目标查/假设查三查 + 审题质询员红队子 agent，通过才进问题分解
- **一致性审计器**：`scripts/consistency_audit.py`（未冻结数字/摘要-结论打架/图表引用断链/符号表脱节/版本错乱五项检查，含 5 个 pytest）
- **子 agent 花名册**：`references/parallel_dispatch.md` 登记 8 类角色（题面提取/审题质询/文献核验/子问求解/代码审计/章节起草/一致性审计/评委席位）
- **决策 UI 映射**：`references/decision_ui_map.md` 登记全部阶段决策点的选项卡规范（AskUserQuestion 与编号菜单双端一致）

## V7.5.0 — 2026-09-02

许可证剥离 + 评委模拟器 + 真实性机器验证 + 发布工程化（与 SKILL.md v7.5.0 更新日志同口径）。

- **路线 A 许可证剥离**：移除全部第三方受限资产（旧 13 套第三方 LaTeX 模板、cumcmthesis、verify_paper.sh、旧图模板等）；LaTeX 模板干净室重写为 6 套自写（cumcm/huaweibei/huashubei/mcm/diangong/apmcm，xelatex/pdflatex 全部编译通过，6 套均随仓库预编译验证）；图表模板换新自写 4 件（龙卷风灵敏度/优化分配/多场景稳健性/技术路线图，`templates/figures/scripts/` + `render_modeling_pack.py` dispatcher）。全库资产现为自写或自由许可，MIT 开源/商用无冲突。
- **评委模拟器终审**（stage_09 + feedback_layer3 + rating_contract）：资格硬规则前置门（任一不过即"不具备获奖资格"）→ 先冻结原子扣分清单再读论文 → 扣分制评分（1-2-3 原子分档、90% 封顶与"评委满分保留"、格式乘数全局加权）+ 盲评信息隔离（评委不见阈值、verdict 编排方重算、共享维度 >20 分差禁平均只重派离群席）+ 华为杯校准锚（扣分制 80+/100 ≈ 国一区间）；`scripts/score_artifact.py --mode judge` 可执行化消费 rating_contract 的 scoring_mode/judge_reserve_cap/format_multiplier/qualification_gate/calibration_anchors。
- **真实性机器验证**：`scripts/freeze_numbers.py` 数字冻结（claim↔源文件 SHA-256 绑定，过期自动标 stale）+ `scripts/run_manifest.py` 运行哈希链（逐行自哈希 + 链式双锚，脚本/输入/输出漂移检测，record 锁保护串行执行）+ 级联失效规则（workspace_protocol §9-§10）。
- **图表硬门**：`scripts/figqa.py`（六类渲染碰撞检测，接线进出图流程；技术路线图盒内标签合法，固定 `--allow-box-labels`）+ `scripts/figure_lint.py`（设计规则 lint：图例>5/逐点标记>25/非零基线/禁 jet 等）+ `scripts/pdf_qa.py`（重复图题跨语言归一/匿名性扫描/空白页/页数，并入 `package_submission.py` 提交流程）。
- **写作增强**：去 AI 味升级为十类（新增频率配额表与工作流话术泄漏正则）；文献桥接补期刊含金量分级与参数溯源；模型选型强制"首选+备选+首选失效边界"三件套；新增 MCM Memo/Letter 指南；图表导出三格式纪律（svg.fonttype=none / pdf.fonttype=42 / 300dpi PNG）。
- **发布工程化**：新增 LICENSE(MIT) / CHANGELOG.md / .gitattributes / .editorconfig；全库脱敏（本机路径与个人痕迹清零）；行尾统一 LF；版本号统一 7.5.0。

## V7.4

实战复盘驱动升级。

- 统一配色体系 (`templates/figures/style/` 4 套色板 + mplstyle + `color_typology.md`，废止三处矛盾口径)
- 工作区纪律 (`workspace_protocol.md`：唯一工作区/真源 SSOT/冻结时点/数字注入/独立验收三选二)
- 华为杯 72h 作战表
- Stage -1 赛前兵检
- 子 agent 并行调度协议 + 迭代预算 decision_memo
- 文献获取桥接 (检索硬上限 + T1→T3 路由)
- 去 AI 味写作规范
- 6 竞赛提交清单 + `package_submission.py` 打包脚本
- 摘要三遍制统一口径
- huashubei phrase_bank 补预处理句式与 L1 anchor

## V7.3

三赛联合知识工作流。

- 新增 `all` 联合检索与 `case/question/both` 双层检索；73 个三赛案例和研究生赛 48 个提名论文子问保留竞赛与证据身份，Top-K 容量允许时保证三赛均有命中。
- Stage 1/3/5/8/9 可自动生成最小知识包；Stage 8 按子问依赖生成动态论文骨架。
- 建立 `question → model → result → validation → figure → abstract_claim` 证据账本，未闭环主张阻断摘要。
- 图表计划统一记录 `role / supports_claim / upstream_data / required_checks`，不以固定数量代替论证。
- 新增 `config/rating_contract.json` 统一评分契约；竞赛 overlay 只覆盖差异，华数杯图表数仅作样本观察。
- 新增 SHA-256 增量清单与知识版本管理，未变化文件不重跑，删除只记录不自动执行。

## V7.2

研究生赛深度蒸馏。

- 新增 `competitions/huaweibei/`：2021—2025 共 30 题、190 篇优秀论文、12 篇有目录依据的 2021 数模之星提名论文。
- 30 题全部具备问题本质、逐问依赖、路线比较、假设风险、验证、图表叙事和写作骨架；12 篇提名论文另有逐篇章节与 48 个子问深读。
- `huaweibei` 与 `huashubei` 永久分键；研究生赛 A-F 只表示题号，不固定映射题型；2022—2025 不推测数模之星身份。
- 国赛/研究生赛共用案例检索器，运行时合并基础索引与人工复核覆盖层；历史数值、参数、结论和原句禁止迁移。

## V7.1

CUMCM 来源纠错和深度案例库。

- 重下载并校验 32 篇官方展廊论文、1 篇可核验国二论文、2021-2025 共 26 份题面，聚合为 25 个可检索案例。
- 排除 58 篇旧误标的"华为杯"研究生论文，旧"91 篇真国赛"统计不再作为评分真值。
- 新增内容型相似案例检索、九类建模范式、逐题模型链、必做验证、图表组合和迁移边界。
- CUMCM 按题面内容分类，A/B/C/D/E 只表示题号，不再固定映射为题型。

## V7.0

华数杯国一专项升级。

- 新增 `competitions/huashubei/` 完整经验库 (14 文件)：基于 2020-2025 共 6 届 18 道赛题 + 18 篇优秀论文全部本地蒸馏, 深度超过 apmcm。
- 三题型分别建模范式：A 题物理工程机理 + B 题运筹优化 + C 题数据评价, 各题型独立的建模主线、方法库、创新点构造、图表模板、反模式。
- 华数杯专项工作流三件套：选题决策矩阵工具 + 图表能力强化包(按题型代码模板) + 72h 作战时间表(逐小时里程碑)。
- 国一标准评分 overlay：6 维度(模型命名定量摘要/章节闭环/题型方法匹配/图表解释密度/机理算法洞察深度/诚实可复现), 按题型差异化要求 + 4 角色 panel 评委。
- 华数杯从"仅 LaTeX 模板"升级为有完整经验库的一等竞赛, 与 cumcm/mcm/diangong/apmcm 并列。

## V6.5

- 纯 LaTeX 后端, 17 套竞赛模板 (含 huashubei xelatex 模板)。(已被 V7.0 继承)

## V6.3.1

- Figure bridge — 新增 `references/figure_skill_bridge.md`, 接入 `figure-table-planner` / `math-figure-generator` / `nature-figure` 三段式图表规划、生成和终审质检。

## V6.3

- Codex 实战工作台版 — 新增 `references/codex_practical_menu.md`, 强化自然语言入口路由、Stage 1 实战选题矩阵、Stage 8 局部写作入口和 Stage 9 极速终审路径。

## V6.2

- APMCM 接入 — 新增 `competitions/apmcm/`、本地 2024/2025 蒸馏资料、APMCM 题型权重、渲染模板和四竞赛入口说明。

## V6.1

- Darwin dry-run upgrade — 强化 frontmatter 触发词、首要动作、启动/决策/不可逆动作检查点、失败兜底表、反例黑名单和 README runtime-neutral 表达；新增 `test-prompts.json` 作为后续实测复评输入。

## V6

- Codex-native packaging — 按 OpenAI Codex Skills / AGENTS.md / Plugins 官方形态补齐 `agents/openai.yaml`、`.codex-plugin/plugin.json` 与 `skills/mathmodel-studio/` plugin shim, README 改为 `.agents/skills/` 安装方式, `AGENTS.md` 降级为项目级 instructions shim, `references/harness_compat.md` 同步 Codex skill / plugin 发现协议. 运行时 workflow、评分脚本与 `decision_log.json` schema 保持兼容.

## V5

- harness-agnostic — 新增 `AGENTS.md` 作为 Codex CLI 入口, `references/harness_compat.md` 定义跨 harness 行为约定, `decision_log.json` 跨 Claude Code / Codex CLI 互通.
- Friendly Mode — 所有关键决策点 (选题/选模型/verdict/refine 决策) 强制问答式 (编号选项 + "让我决定" 兜底), 用户不再需要手敲 bash / python / 编辑 json.
- stage_00 / stage_01 / stage_05 已落实问答式样板, 其余 stage 由 SKILL.md 顶层协议统一约束.

## V4

- 早期多竞赛通用化 (`competitions/{cumcm,mcm,diangong}/`); 评分系统升级 — empirical 真正进入 L1 prompt; Stage 5 per-Qi 加权聚合 + 差异化降级 (`pass_with_review` / `refine_partial` 两个新 verdict); 题型 dim 权重 (`config/dim_weights.json`); SKILL.md 由 9k 字节瘦身到 ≤ 6k.

## V3

- 模板瘦身 + 91 篇 PDF 蒸馏成 4 份 markdown 后删除 PDF (释放 494MB).

## V2

- 审计修了 20 条 (协议矛盾、schema 漂移、脚本 bug).

## V1

- 初次搭建, 10 阶段 + 4 反馈层.
