# Changelog

本文件记录 mathmodel-studio 的全部重要变更。条目整理自 SKILL.md 与 README.md 的版本史（V1—V7.4 原文照抄）。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [3.4.0] 数据假设驱动研究与证据检查（2026-09-21）

- 合并 Stage 3 重复流程，以观察、失效假设和决定性实验组织候选；表示、模型及训练分开验证，探索池不受最终展示数量约束。
- 实验预算按训练诊断和研究缺口分档，内部验证选配置，外层评价；联合改造有收益后补关键控制，不强制全排列消融。
- 统一研究与写作的文献预算，保留 benchmark_smoke / contest / practice 策略；消除旧固定次数、篇数、语种配额与主模型外源强制要求，来源真实性继续核验。
- 证据协议核对真实关键行为与子问范围；无标签目标的零预测只触发复核，不强制补齐类别；信号诊断改为物理错位驱动的条件性路线。
- 修复历史refine后pass仍被阻断、描述性斜杠被误当证据路径、列表或显式路径对象缺文件漏检。
- 对齐案例入口、评分、模板和宿主交互；保留state schema、旧评分键、experiments-1/2与CLI，不新增阶段、数据库、审批或自动预算引擎。

验收范围与限制见 `docs/release_3_4_review.md`。本轮未完成跨题新旧技能对照；一次外部API连通不代表全部服务已验证，不以版本号保证建模质量或比赛结果。

本变更必须同改的文件：`SKILL.md`、`README.md`、两份 plugin.json、`ARCHITECTURE.md`、`CHANGELOG.md`、Stage 3/实验/证据/文献协议、活动调用者、信号playbook、`check_gate.py`、`trace_claims.py`及相关测试。发布清单由分发脚本按最终字节重新生成。

<!--
同步清单（v2.8.0 起的硬性模板，写新条目前先读）：
每个条目末尾必须列"本变更必须同改的文件"，漏列 = 评审打回。典型三类：
1. 必停点变更 → 同改 SKILL.md（必停点协议）+ scripts/check_gate.py
   + references/stage_05_subproblem_loop.md + references/decision_ui_map.md
   （条目 JSON 形状另同步 references/workspace_protocol.md §12）；
2. 版本号变更 → 同改 SKILL.md（标题+版本段）+ CHANGELOG.md（本文件首条）
   + README.md（徽章+开发日志表）+ .claude-plugin/plugin.json + .codex-plugin/plugin.json
   （tests/test_version_sync.py 会拦漏改）；
3. 图表模板数量/路由变更 → 同改 references/figure_skill_bridge.md（顶部总路由表）
   + SKILL.md（图表任务加载行，只写指针不写死数量）+ templates/figures/gallery/README（计数）。
其他易漏点：归档/移库文件 → grep 旧路径清零（tests/test_doc_links.py 会拦残留）；
竞赛经验统计 → 同步该赛 empirical.json + empirical_notes.md + winning_patterns.md。
-->

## [3.3.0] 正式图组合与分型验收（2026-09-20）

- 新增显式 axes 组合、共享图例/色条、毫米版心和独立修订导出；旧模板 ID、CLI、返回值、Stage/state/冻结链与 save_fig 失败行为保留。
- 新增 A-F 六类可运行合成范例；原 mask 保持编码与尺寸，未知标签不报告准确率。范例是可拆装参考，不是强制流程。
- 实验比较 experiments-2 区分预测/优化/数值任务、实例内重复、多目标与成本缺测；图库 figure-candidates-2 分离生命周期与去向，不自动晋升诊断图。
- 修复预测缺口连线、原图与预览质量混用、figqa 混合坐标及收敛标签相交；普通 TIFF/GeoTIFF 分流并增强 NPZ/NetCDF 元数据。
- 审查补强：保持数学字体政策、共享色标定标检查、时间划分校验、全部 mask 原图验证和 SVG 主动/外部内容拒绝。
- 移除 `docs/legacy/` 历史归档目录（旧薄执行器原型与废止蒸馏文档，维护者本地留存备份），全库指向该目录的公开引用同步改为移出说明；收紧 `export_docx.py` 与 `run_eval.py` 输出路径写法并补越界/竞赛名校验，`docx_presentation_postprocess.py` 拒绝含 DTD/实体定义的 document.xml。
- 规则分层并消除作战地图必选、探索图强制设计卡、已有授权仍重复确认等冲突；打包横幅避免重复注入。
- 视觉目检及部分可选专业后端仍未完成，范例保持候选；不以机器检查或版本号宣称终稿审美合格。详见 docs/upgrade_acceptance.md。

本变更必须同改的文件：SKILL.md、README.md、两份 plugin.json、ARCHITECTURE.md、图表桥/工作区/Stage 5 协议、新增组合/读取/比较/图库模块、分发脚本及相关测试。

## [3.2.0] 按需能力与实验驱动流程（2026-09-20）

- 精简 Skill 默认入口，条件性启动、套餐、竞赛与故障说明下沉，保留阶段和门禁接口。
- 新增多类型附件元数据检查及保留帧号、时间戳的视频单帧提取；可选读取器按需导入。
- 新增同协议实验结果比较，核对重复实验、预算和证据哈希，避免用最终测试集选型。
- 从审题期锁图改为证据需求登记、小实验修订、正式出图前冻结。
- 新增多模态图路由和备选图库，不强制候选模型族数、综合图配额或持续生成。
- 验证范围与本机限制记录在 docs/upgrade_acceptance.md；不宣称未安装媒体/地理后端已实测。

本变更必须同改的文件：SKILL.md、README.md、两份 plugin.json、ARCHITECTURE.md、references/README.md、Stage 2/3/5 与 figure_skill_bridge.md、新增工具和配套 reference、回归测试。

## [3.1.0] 建模流程与导出修复（2026-09-19）

- 精简入口和阶段文档，保留关键确认、数字回源和逐页验收。
- 修复绘图兼容、数字回检、引用处理及 Word 导出问题。
- 补齐文档处理依赖，更新安装说明和首页，完善分发过滤。

回归验证：651 项通过，1 项可选依赖跳过，1 项真实联网测试排除。

### 技术记录

本轮在已有实现上修复与精简，保留六必停点、恢复、冻结/回源、用户输出链、图表与逐页视觉终验。

- 入口与阶段页改为按任务/章节加载，权威正文去重迁移；实际规模与读取实验分开报告，不用静态折算或测试数量证明效率。
- 修复旧绘图位置参数兼容、数值格式、甘特单位/小数、异常 rc/Figure 清理与目录检查中断；旋转文字矩形相交只警告，收敛档差标注不再冒充点值。
- 数字回检以明确主张绑定优先，修复小差值冲突被全局同值覆盖、来源路径越界和极小数异号混淆；复用已有来源登记，区分值证据与仅登记路径。
- Word 按政策保留正确正斜混排，逐节版心与保守编号处理、表格排版、秒级终稿独占输出、并发转换临时目录；共享 Markdown 文献发现、围栏/区段与编号口径。
- 分发改为显式白名单、敏感目录排除、Junction 剪枝、日志路径脱敏、最终 staging 扫描/指纹及失败不混入既有候选。真实案例原件保留而默认排公开包；扫描不是完整去敏证明。

**历史条目纠偏（以下旧记录保留为历史，不能作为当前实现契约）**：原 A4 的“40%矩形判真叠印”已撤销；A5 不再以统一5%差值带豁免明确冲突；字体不是无条件正体；C6 的10倍/20%仅示例默认可配置；D2 秒级独占仅验证终稿导出，审阅导出仍旧；C7 来源覆盖已补值证据/路径登记区分，但不是全自动语义溯源。原“26项”与分组编号并不一致，本次不沿用该总数作完成量。图表和摘要失效传播仍须流程回源，不自动改论文。

**验证边界**：独立语义复核、隔离合成测试与真实渲染视觉验收分别记录。前向S3保留原失败及另存返工证据；候选式 claim 检查的通用对象语义仍有限。读取实验受共享上下文、在途变化与基线污染影响，不声称严格A/B或30%–50%读取降幅。缺依赖、未测、警告均不冒充通过。完整本地验收及恢复记录置于 maintenance 目录（默认不分发）。

**本变更同改的文件**：`SKILL.md`、`README.md`、本条、阶段与权威协议、`scripts/` 相关检查/Word/分发模块、绘图模板及对应测试；规则迁移索引见 `docs/maintenance_notes.md`。两份 plugin 元数据版本同步为3.1.0。

### 2026-09-18 原始记录：实战缺口机器拦截专项（历史）

依据 2026 国赛 A 题《药材的烘干问题》全流程实战重跑（出图→写作→终审，含跨家族 bug-reviewer 复审与五席位评委 panel）+ 台账 S-01～S-15 + 用户呈现层反馈七项，把"开卷即见"的硬伤逐一变成机器可拦的检查。逐项依据与状态见工作区 `skill优化清单_v3.0.1.md`。

**A 质检门禁（8 项）**
- A1 `pdf_qa.py --artifact-scan`（默认开）: 文本层 7 类构建事故指纹（`##` 残留、管道表源码、HTML 残片、`\times`/`imes` 类 LaTeX 残骸、裸控制字符、引用断链占位）任一命中即 ❌。
- A2 `export_final_docx.py` 前置 md 卫生 lint: 标题/题注前缺空行自动补（打印 diff 摘要）、TAB 与奇数 `$` 报错退出、>28 字符无断点长 token 警告（表格列断行点）。实测三起事故（整表以源码形态印出、`## 问题二` 印成正文、`9.1imes10-5`）全部拦在导出前。
- A3 `scripts/docx_presentation_postprocess.py` 沉淀并接线: `export_final_docx --presentation`（默认开）在导出尾部自动跑呈现层后处理；`docx_to_pdf.py` 转换前检测漏跑并警告；幂等（第二遍 0 处理）。
- A4 `figqa.py` 第七类 artist-bbox 遮挡: text×inset / text×legend / legend×text / 刻度标签互压按面积阈值报 ❌，legend×line 报 ⚠️（S-10 inset 整块盖住穿越点标注、色条刻度叠印 8.9px 都曾漏检）。**旋转刻度标签按占比判据**：|rotation|>1° 的标签其轴对齐 bbox 相邻必然相交（现场回归实测 125–1048px² 而字形不重叠），改按"重叠 > 较小框面积 40%"判真叠印，未旋转仍按绝对面积严判（S-20）。
- A5 `docx_number_recheck.py` 缩写分级: ≥3 位有效数字的冻结项"仅见缩写"升为 stage 9 必查清单；A 级冲突加**相对差 ≥5%** 带（同前缀邻近值是显示精度差异、非冲突），新增 A-候选非阻断档与 A/B/C 三级报告；真阳性（0.7403/0.7 歧义）仍拦。
- A6 `consistency_audit.py` 认 docx 链题注语法（`: 表 N` / `![图 N …]`）并做式编号闭环；对本次工作区 92 条误报归零。
- A7 `figure_lint.py` 豁免通道: R9 对等值线数值标签（`QuadContourSet.labelTexts` 归属）与"纯数值+单位"串豁免——后者为**词法判定**：token 先剥离数值语法（含科学计数法 `1.2e-05`）与装饰（含单位幂 `m^2`），剩余须是单位词（白名单 + `kg/kg`/`m/s`/`W/(m·K)` 组合，micro sign U+00B5 与希腊 mu U+03BC 归一），故 `30 ℃`/`123456.789 Hz` 豁免而 `Model improves after 10 iterations` 仍计注释（S-11/S-18/S-19）；R4 增 `--grid-annotate` 声明位；`--strict` 改为只拦 error、warn 列清单，`--strict-warn` 保留旧语义。
- A8 新增 `scripts/ref_order_audit.py`: GB/T 7714 首引顺序审计（首引序列须 1..N 递增、孤立文献、零引用主章），并入 stage 8/9 机检。

**B 模板与资产（5 项）**
- B1 25 件数据图模板版式决策参数化: 轴名/脚注文案/面板标题/参考线图例文案/图例位置统一暴露入参，默认值 = 原字面量（向后兼容）；`panel_label()` 返回 Text 对象。项目侧薄封装可退化为直接调用。
- B2 `make_threshold_inversion` 修复项入库: inset 四角自适应避让标注/图例 + `star_symbol` / `star_value`（印冻结值防末位漂移）。
- B3 `build_reference_docx.py` Normal/Body Text `space_after` 默认 0（中文首行缩进+零段距惯例），`--loose` 保留旧行为。
- B4 图内字体正斜随全文政策: `figkit.apply_style(upright_math=True)` 与 mplstyle 注释开关（默认仍斜体 = golden 行为），设计卡第 ④ 要素登记政策。
- B5 docx 链表格呈现五项（三线/自适应/居中/行禁拆/单元格零缩进零段距单倍行距）源头（reference.docx `Table` 样式）+ 后处理（Step C/D/E）双落地。

**C 流程与协议（7 项）**
- C1 D.1 图表菜单允许四问合并单轮拍板（`menu_form` 扩展字段入 workspace_protocol §12；仍逐问登记、必停点性质不变）。
- C2 "识图先行"写进委派协议（golden 样张先由视觉通道转版式锚点描述再入 prompt；禁止只给路径让无视觉执行器自读）。
- C3 视觉验收派发协议: `pdf_qa --page-map` 机器提取"页码→首行关键词/图表编号"映射表随 prompt 给出；验收对象一律带时间戳副本、禁止同名覆盖。
- C4 stage 5 验证维度加"正文公式 = 生产代码离散形式"逐条对照（panel math_rigor 的 P1 发现，全链最贵返工）。
- C5 冻结协议补强: `freeze_numbers` locator 试解析（解析不到给 warn）、`check_gate` 评分时效软检查。
- C6 参数档网格充分性硬规则: 边界层敏感量跳变 >10× 的档必须先做粗/细网格检验，同一时刻关键量相对变化 >20% 判欠分辨、剔除出排序；可运行模板 `templates/shared/code_starter/simulation.py` 第 6 节。
- C8 写作 AI 味模式库增补**版式层四类**（段落长度均匀/加粗层级失效/枚举骨架/结构套话）与可运行自查，stage 8 自查升为十四类。

**D 脚本健壮性（3 项）**
- D1 新增 `scripts/skill_paths.py` 作为根路径唯一真源: 按调用路径推导（`.codex`/`.zcode` 两份安装并存时报告当前使用的那份），`--list`/帮助文本运行时拼路径，启动打印 `[skill] root=…`；全仓库禁用写死用户目录绝对路径。
- D2 导出时间戳精度到秒（`%H%M%S`），护栏只拦完全同名（原分钟级导致两次 `sleep 62`）。
- D3 `consistency_audit` 符号脱节白名单（代码围栏与常用哑变量豁免，246 条误报归零）。

**E 规范文档（5 项）**：E1 md 空行/字符卫生规范（`md_authoring_spec` §3/§3.1）、E2 公式编号 docx 链实现与自查（`cn_presentation_spec` §5.1）、E3 公式正斜二选一政策（§5.6）、E4 图注唯一来源协议（图表登记表"终稿图注"列 + stage 8 只许逐字复制）、E5 表格断行控制（并入 A2/B5）、E6 图与图注同页与页尾留白指引（§7.6 + 导出后处理 Step F `keepNext`）。

**测试**：459 passed（本版起点 258）+ 新增 `test_presentation_postprocess` / `test_export_md_lint` / `test_pdf_qa_artifacts` / `test_figqa_artist_bbox` / `test_docx_number_recheck` / `test_consistency_audit_docx` / `test_ref_order_audit` / `test_freeze_locator` / `test_reference_docx_styles` / `test_template_params` / `test_skill_root_resolution` / `test_figkit_upright_math` / `test_grid_sufficiency_template` / `test_threshold_inversion_regression`；回归用例一律取本工作区事故现场（`_archive/` 旧稿与 `.bak` 中间态）。

**本变更必须同改的文件**：`SKILL.md`（标题+版本段+图表能力速览）、`CHANGELOG.md`（本条）、`README.md`（徽章+开发日志）、`.claude-plugin/plugin.json`、`.codex-plugin/plugin.json`（版本五处，`test_version_sync.py` 拦漏改）；`references/cn_presentation_spec.md`（§5.1/§5.6/§6.1/§6.2/§7.6）、`references/md_authoring_spec.md`（§3/§3.1）、`references/workspace_protocol.md`（§7 终稿图注列、§12 menu_form）、`references/stage_04/05/06/08/09`、`references/figure_skill_bridge.md`、`references/parallel_dispatch.md`、`references/ai_flavor_removal.md`、`competitions/cumcm/phrase_bank.md`、`scripts/`（新增 `skill_paths.py`、`ref_order_audit.py`、`docx_presentation_postprocess.py` 等）、`templates/`（25 件模板 + mplstyle + code_starter）、`tests/`。

## [3.0.0] 图表叙事专项：设计卡 + 作战地图 + 判据线纪律 + 示意图草稿通道 (2026-09-16)

依据 2025 华为杯 21 篇优秀论文 598 张图页全量分析（A-F 六组精读，实测记录存于用户工作区 `_figcompare/` 与讨论稿，不入库）。

**规范（图叙事章，`references/figure_skill_bridge.md` 新增）**
- 两个分野总原则：数据图=代码生成+门禁；示意图=草稿+可编辑源文件（drawio>SVG>PNG）+人工精修回贴（`*.draft.drawio` 命名协议，stage 8 只收已精修版）。
- 图叙事设计卡五要素（回答什么问题/图型/证据层/注释预算/评委一眼所见）：stage 5 出图前必填，登记真源.md 图表登记表"设计卡"列（`workspace_protocol.md` §7 同步加列）；D.1 图表菜单加第 3 问"叙事结构确认"（narrative 摘要字段，纯记录不入门禁）。
- 作战地图强制件：每篇 1 张整页 graphical abstract（三问题色带+因果箭头+嵌真实结果），stage 2 登记必选、stage 8 生成，本身走草稿通道。
- 判据线纪律（阈值/判据/基线必画进图）+ 配色语义表（`color_typology.md` 新增：判据=红虚线/基线=灰黑虚线/主模型=主色/对照=对色或灰；硬规则 10 收限为点/区域强调）。
- 对照式构图优先（有对照关系默认同坐标对照面板）；量化标签（过程图带计数、柱顶标值、图例带 R²/N）；用途类型四类（答案图强制"可核验"三选二）；不学清单（不贴教材/AI 图、不刷低增量重复面板、图题编号引用逐条核对、禁纵轴截断）。
- 出图委派协议三条扩五条（`parallel_dispatch.md` 挂接点 3.5：+设计卡五要素、+示意图只交草稿）。

**模板与门禁**
- 数据图模板 17→25 件：物理场 6 件（field-contour / profile-family / threshold-inversion / convergence-sequence / contrast-pair / route-on-field）+ 场景 2 件（answer-grid 结果交付网格 / before-after 前后对照），全部接入 render_modeling_pack 并过 figqa/figure_lint 双门。
- drawio 模板 6→7 件：作战地图 `graphical_abstract_3band`（三问题色带 content JSON 驱动，默认交付 .draft.drawio）。
- `figure_lint.py` 新增 R9 注释预算检查（数据图面板解释性文本 >2 条 warn，判据线图例与量化标签豁免，示意图经 --allow-box-labels/--schematic 豁免）。
- gallery：8 件新模板基线 PNG + ga3band drawio 基线入库；新增 `golden/` 范式样张 7 张（4 张实战返工成品 + 3 张新模板样张，每张注明对应图叙事纪律）。

**测试**：`tests/test_new_figure_templates.py`（8 模板 smoke + `_first_crossing` 边界 4 用例）、`tests/test_figure_lint_r9.py`（R9 回归 6 用例含极轴类别标签）、`tests/test_drawio_graphical_abstract.py`（JSON schema+门禁）。

**复审修正（跨家族语义复审后）**：`make_field_contour` 非共享色标多面板改每面板独立 colorbar（原单条会静默误导）；`figure_lint` R9 加极轴类别标签豁免（`ax.name == "polar"` 且 r≥0.9·rmax，修雷达图误报）；`make_threshold_inversion` 补末档点恰压阈值的穿越定位与标注防溢出；cn_spec §7.2 注释预算措辞定版（量化标签不计）；配色语义表补"连续/发散色标端色不作语义定向"；清理 gallery 前缀散落文件。

> 本变更同改文件：references/figure_skill_bridge.md + references/stage_05_subproblem_loop.md
> + references/stage_02_analysis.md + references/stage_08_writing.md + references/cn_presentation_spec.md
> + references/color_typology.md + references/parallel_dispatch.md + references/README.md
> + references/workspace_protocol.md + templates/figures/scripts/(模板×8+两个 dispatcher)
> + templates/figures/scripts/drawio/make_drawio_graphical_abstract.py + templates/figures/gallery/
> + scripts/figure_lint.py + tests/×3 + 版本五处（SKILL.md/CHANGELOG/README/plugin.json×2）


## [2.9.1] 写作期终稿链选择 (2026-09-16)

- `decision_log` 新增正交字段 `final_chain`（`tex` 默认 | `docx`）：stage 8 样张先行时以编号菜单确定终稿链（`references/stage_08_writing.md` 新增"终稿链选择"节）；写作全程仍写 md 真源，选择只影响 stage 8 出口的渲染与终检路径。
- `references/docx_final_channel.md`：入口条件 3 增补——`final_chain=docx` 与 `docx_channel=true` 等价，任一为切换声明；`references/stage_09_review.md` Step 2 补终稿链口径（final_chain=docx 时验收以 docx 版 PDF 为对象，tex 专属检查跳过、改跑 docx_number_recheck）。
- 冻结完成前任何链下禁止人改 docx 的护栏不变。
- 新增 `tests/test_final_chain_template.py`（模板字段默认值/枚举注释/schema 版本不变 4 用例）。

> 本变更同改文件：templates/shared/decision_log.json + references/stage_08_writing.md
> + references/docx_final_channel.md + references/stage_09_review.md
> + tests/test_final_chain_template.py + 版本五处（SKILL.md/CHANGELOG/README/plugin.json×2）


## [2.9.0] docx 终稿通道：冻结后 Word 终改 + 数字回检门禁 (2026-09-16)

> 依据 `讨论稿_skill改进_20260915.md` §4 的 5 个缺口（终改只能在 LaTeX 源里做、
> 只会 Word 的用户被排除在终稿环节外、docx 审阅件无法升为终稿介质等，已端到端实测定位）。
> 定位：md 真源 → docx 终稿（人改呈现层）→ PDF → 终检；审阅件模式（export_docx.py）默认行为不变。

**新增脚本 (scripts/)**
- `export_final_docx.py`：md → docx 终稿。缺省自动发现升级（`NN_*.md` 数字前缀系列自然排序，回退 main.md/sections 约定）；pandoc 之前做图/表编号注入（图 alt 加"图 N "、表 `: 题注` 加"表 N "，按文档出现顺序、幂等，无题注管道表收警告不打号——与 LaTeX 链口径一致，实测对账图 10/表 7/文献 20 三项齐平）；`\tag{N}` 归一 `\qquad (N)`（同 export_docx）；参考文献 `\bibitem` 行转 `[N] ` 列表、参考文献/附录章标题合成并豁免编号（pandoc `{-}`）；pandoc `--number-sections --shift-heading-level-by=-1`；pandoc 之后 python-docx 插标题块（黑体三号居中标题 + 题号/队号行 + "摘　要"标题段）并在正文第一章前分页；默认挂 `templates/docx/reference.docx` 样式基准。
- `docx_to_pdf.py`：Word COM 主路径（pywin32 只读打开 → SaveAs FileFormat=17 → try/finally Quit 防进程残留）→ PowerShell COM 单行兜底 → soffice 无头兜底；pymupdf 打印页数。
- `docx_number_recheck.py`：终稿数字回检。硬门禁=冻结表每条数字（或 display 字段）必须在 docx 全文出现（规范化：千分位/负号/上标；科学记数法等价匹配复用 claim_consistency 的 `_sci_traced` 思路，实测 docx 的 `$2.30\times10^{-13}$` OMML 展平为 "2.30imes10-13" 可命中 `2.30e-13`）；原值未见但存在非零缩写形态（如 -4.8822 摘要写 4.88）走 warn 不 FAIL；软检查=≥4 位有效数字的结果样新数字清单（纯整数/年份/display 公式常数豁免）。文本提取按文档序并入 OMML m:t 并在公式块间补分隔，防相邻公式展平粘连把指数串位。缺失即 exit 1。

**新增模板与协议**
- `templates/docx/build_reference_docx.py` + 生成产物 `templates/docx/reference.docx`（脚本一并入库可再生成）：pandoc 默认 reference.docx 为底，A4 四边 2.5cm、页脚居中 PAGE 域、宋体小四 + Times/1.3 行距/首行缩进 2 字符/两端对齐、黑体黑色 H1-3（16/14/12pt，H1 居中）、题注宋体 9pt 居中。
- `references/docx_final_channel.md`：通道唯一权威源（入口条件三条/人改白名单与禁区/三步终检/回退条款/与审阅件模式关系/何时不该用/故障兜底）。

**既有文档挂接（各一指针，不重述规则）**
- `SKILL.md`：实战入口路由表加"想用 Word 终改/出 docx 终稿"行；stage 8 加载行末尾加 docx 通道指针。
- `references/workspace_protocol.md` §3.1：加"终稿通道例外"段（登记 docx_channel=true 后 docx 升为终稿介质，纪律=数字回检门禁）。
- `references/cn_presentation_spec.md` §10：加"终稿链二选一（tex/docx），20 条对 docx 版 PDF 同样适用"。
- `references/submission_checklists.md`：通用终检表表下注加 docx 通道检查项（不占行号，防引用断裂）。
- `references/README.md`：R 表登记 R13（docx 终稿通道 → docx_final_channel.md）。

**测试**
- 新增 `tests/test_export_final_docx.py`（编号注入文档序号语义/混合编号占号/编号冲突报错/幂等/无题注警告/```与~~~变长围栏免疫/标题合成/摘要标题豁免/dry-run 无 pandoc 可跑/真链路导出验标题块与题注样式，pandoc 或 python-docx 缺失时 skip）、`tests/test_docx_number_recheck.py`（缺失 exit 1/在则 exit 0/带符号与中文边界 token/缩写完整 token 匹配/e 记法与 ×10 形态分列/下溢 log10 域/表格数字/纯 JSON 输出/退出码 2 口径）与 `tests/test_docx_to_pdf.py`（假转换器单测：静默失败不得把旧 PDF 当成功、失败降级下一条、临时目录原子替换与清理、退出码 1/2 分流）。

**复审修正（bug-reviewer 返工 6×P1 + 4×P2，含最小反例回归）**
- P1-1 编号注入改"文档序号"语义：已有编号项同样占号，与序号不一致抛 NumberingConflict（不静默重号）；P2-7 围栏状态机支持 ~~~ 与变长反引号，编号与标题预处理共用。
- P1-2/P1-3/P1-4 数字回检 token 层重写：带符号完整 token（-4.8 命中、-2.30×10⁻¹³ 不得匹配 2.30e-13）；中文紧邻不算词边界、拉丁标识符紧邻仍排除；正文采集 e/E 记法统一进科学记数等价；等价比较改 (带符号尾数,指数) 对——常规域相对比较不设绝对容差下限，非零下溢/上溢走 log10 域，符号不同即不等。
- P1-5 缩写回退改完整数值 token + 半末位区间判定（兼容 half-up/half-even），子串命中不再放行（104.88 ≠ 4.8822 的缩写）。
- P1-6/P2-9 docx_to_pdf：各转换路径先输出到目标旁一次性空临时目录，确认新产物有效后 os.replace 原子落位（旧 PDF 不可能被当新转换成功）；假成功/无产物降级下一条；转换器存在但全失败=exit 1、全部不可用=exit 2。
- P2-8 md 自带 "## 摘要" 标题：豁免编号；正文分页跳过摘要标题、落在第一个正文章标题；P2-10 上述全部固化为回归用例。

**本变更必须同改的文件**：`scripts/export_final_docx.py`、`scripts/docx_to_pdf.py`、`scripts/docx_number_recheck.py`、`templates/docx/build_reference_docx.py`、`templates/docx/reference.docx`、`references/docx_final_channel.md`、`references/README.md`、`references/workspace_protocol.md`、`references/cn_presentation_spec.md`、`references/submission_checklists.md`、`SKILL.md`（路由表+stage 8 行+版本段）、`tests/test_export_final_docx.py`、`tests/test_docx_number_recheck.py`、`tests/test_docx_to_pdf.py`、`CHANGELOG.md`（本条）、`README.md`（徽章+开发日志）、`.claude-plugin/plugin.json`、`.codex-plugin/plugin.json`。

## [2.8.0] 瘦身专项：指针化 + 归档/移库 + runtime 归档 + 治理机制 (2026-09-15)

> 含先行落地的 Phase 0（冲突清零）。依据三方审计：deepseek-v4-flash 硬数据（111 处版本号、段落级重复率实测）、GLM-5.3 规则归属地图（18 主题）、GPT-5.6 对抗复审（推翻 5 项"看着安全实则危险"的删除提案）。病灶定性：同一规则主题被多文件各自立法后漂移成冲突——对策是"每主题唯一权威源 + 其余指针"，不是删文字。

**Phase 0 冲突清零（先行落地，本条一并收录）**
- 公式编号统一"默认全局连续"：`cn_presentation_spec.md` §5.1 收窄（章节式需 `\numberwithin`+登记），stage_08 示例改全局编号。
- 图题格式定版"图 N 说明"（无冒号）：cn_spec §7.1 与 `md_authoring_spec.md` §3 对齐。
- 摘要字数改"按 empirical 分位提示，不作硬门槛"：abstract_template / paper_skeleton / stage_08 / anti_patterns / rubrics / feedback_layer1 六处同改。
- 删除 `competitions/cumcm/distilled_naming.md`（修饰词命名与证据纪律正面冲突，三方一致"删优于并"）。
- 版本元数据同步 2.7.0（plugin.json×2 + README 徽章）。
- gallery/README 计数修正。
- SKILL.md stage 8 加载表摘除已判旧层的 distilled_structures/distilled_formats（"判而不摘"根因），残值迁移：formats §6 衔接句→stage_08、§5 中英混排空格→cn_spec §2.7、structures 章节模板卡→phrase_bank §13。
- 45 条死链逐条修复（paper_skeleton 前缀错误、figure_skill_bridge 8 条、design_tokens 路径等 12 文件）。
- ingest_papers/build_huashubei_cases 的正面引用改"历史流程已退役"口径。
- distilled_formats §1/§2 加废止头注（归档前过渡保护）。

**指针化（8 组，重复内容改一行指针，消除约 560 行双份维护）**
- figure_skill_bridge 两处图内注释预算/图宽重述 → 指针 cn_spec §7.2/§7.3（保留工具侧门禁说明）。
- stage_08 图名/caption 重述 → 指针 cn_spec §7；Phase 0 漏网的冒号式图题示例"图 X：…"改"图 X 说明"无冒号式。
- design_tokens 删除 NEUTRALS 十行令牌副本 → 指针 color_typology §2.2；两文件头部互写管辖边界（色值=color_typology+palettes.py，字阶/版式/间距=design_tokens）。
- SKILL.md 三段图表路由长重述（能力速览/Codex 入口图表行/加载协议三行）各压至 1-2 行；模板数量口径只在 figure_skill_bridge 与各 `--list` 维护，SKILL.md 不再写死数量。
- stage_05 的 checkpoints 条目 JSON 4 份副本并一：schema 单点成文于 `workspace_protocol.md` 新增 §12（SKILL.md 必停点协议节的登记语义保留不动，agent 可达性优先），stage_05 四处改指针。
- AGENTS.md 启动节（约 58 行）改"强制读取 SKILL.md Quick Start"指针；保留 harness 差异表与 cwd/skill 路径协议。
- codex_practical_menu 常用说法路由表加"与 SKILL.md 实战入口路由表同源"注记（文件保留，懒加载设计）。
- 页数口径 5 处重述（SKILL.md stage 8 行 / paper_skeleton 头注 / stage_09 三处）压成"指针 + 22-25 页（正文+参考文献，附录不计）"一句，权威源 cn_spec §1.6。

**归档与移库（git mv 移动不删除，保持证据链）**
- `docs/legacy/`：cumcm 旧写作辅助三件（distilled_phrases/distilled_structures/distilled_formats，残值已迁）、references/papers/README（改 `docs/legacy/papers_README.md`）、docs/architecture.md（设计理由——懒加载/证据隔离等——先摘入 workspace_protocol 新增 §13）。
- `scripts/legacy/`：ingest_papers.py、build_huashubei_cases.py 移入并加 DEPRECATED 头注（已退役、不得再生成统计真值、保留复核用）；重建配方（profile 三类/18 条任务链/证据分级与 S1-S4 边界）写入 scripts/README"历史重建配方"节；build_huashubei_cases 的 SKILL_ROOT 改 parents[2] 保住手动运行能力。
- `maintenance/`（按赛分子目录，不跨赛合并同名文件）：huaweibei star_papers_deep.md（1975 行）/ all_cases_manual_audit.md（1235 行）、cumcm case_library.md（278 行）/ all_cases_manual_audit.md（404 行）；同步改 evals/holdout_protocol.md 留出泄漏源路径（防评测污染）、两赛 README 与 writing_voice/writing_playbook 引用、distill_cumcm_cases.py 的 case_library 输出路径。
- `docs/legacy/runtime/`：实验性薄执行器整目录归档（stage 3-8 未实现）；SKILL.md"多 Runtime 入口"节压缩为归档口径（保留"物理拦截需插件 hook"语义）；全库 runtime/mathmodel_agent 引用同步（score_artifact.py 注释改归档路径）；归档 README 加归档横幅。
- 移库后全库 grep 旧路径清零（CHANGELOG 历史叙述豁免）。

**治理机制（防"skills 打架"疫苗）**
- 新增 `references/README.md`：一规则一家条款 + R1-R12 规则主题→唯一权威源对照表 + 判层必摘条款（判旧层必须同 PR 摘加载表与正面引用）。
- 新增 `tests/test_version_sync.py`：断言发版五处版本号一致（SKILL.md 版本段/CHANGELOG 首条/README 徽章/plugin.json×2），已做改坏变红验证。
- 新增 `tests/test_doc_links.py`：全库 .md 相对路径死链检查（收编 Phase 0 临时脚本；排除 docs/legacy、vendor、maintenance、CHANGELOG 历史叙述，豁免规则在文件头注释写清），已做改坏变红验证；顺手抓出并修复 5 处 ingest_papers 旧路径残留。
- CHANGELOG 顶部加"同步清单"模板注释：每条目末尾必须列"本变更必须同改的文件"。

**明确不做**（三方裁决）：不删 mechanism_distillation（build_stage_pack 携带其输出）；不动 huaweibei/source_manifest.json（distill 脚本硬读校验）；不把必停点登记语义搬出 SKILL.md；不删 huaweibei distilled_structures 摘要节（有依赖方）；不合并 codex_practical_menu（懒加载+harness 适配）；feedback L1-4 合并与 stage_05 重组留二期；竞赛间同名文件不跨赛合并。

**回归**：`python -m pytest tests/ -q` 170 passed + 4 subtests（新增 2 个治理测试；runtime/tests 随目录移出 tests/ 发现面，不受影响）。

**本变更必须同改的文件**（同步清单）：版本号五处（SKILL.md 标题+版本段、CHANGELOG 本条、README.md 徽章+开发日志、.claude-plugin/plugin.json、.codex-plugin/plugin.json）；归档移库引用面（AGENTS.md、SKILL.md、references/{figure_skill_bridge, stage_05_subproblem_loop, stage_08_writing, stage_09_review, workspace_protocol, codex_practical_menu, design_tokens, color_typology, cn_presentation_spec}、competitions/{cumcm,huaweibei,diangong,mcm} 下 README/empirical_notes/writing_voice/writing_playbook/phrase_bank/paper_skeleton、evals/holdout_protocol.md、scripts/README.md、scripts/distill_cumcm_cases.py、scripts/score_artifact.py）；治理新文件（references/README.md、tests/test_version_sync.py、tests/test_doc_links.py）。


## [2.7.0] 呈现质量专项：呈现规范 + 编译链修复 + 页数口径统一 + 出图纪律 + 审计脚本误报修复 (2026-09-15)

源自 2026 国赛 A 题《药材的烘干问题》全程实测（压力测试报告 T-01~T-09、自我纠错台账 S-01~S-08、用户格式反馈 10 条、与 2025 优秀论文 A196 的 64 页对照）。

**新增**
- `references/cn_presentation_spec.md`：中文竞赛论文呈现规范（cumcm/huaweibei/huashubei/diangong/apmcm 通用），stage 8/9 呈现层唯一权威源。十章：版面硬规范（页码页脚居中/禁用页眉/摘要独占页/行距≥1.25 禁止压缩凑页数/页数口径统一）、全角标点体系（含 grep 自查表）、摘要呈现（"针对问题N："导语段、关键结果加粗 6-12 处、"只读加粗复述答案"盲测）、标题体系（两种合法风格选定一致）、公式（居中+编号、超版心 80% 必拆、Overfull >5pt 清零）、表格（三线表/单元格居中/所有表必须编号且被引用）、图与图题（图题 ≤2 行、图内注释每面板 ≤2 条、图宽与物理高度下限）、正文写作 voice（重点前置：段首结论、每段 ≤6 行、结果段三步、假设 ≤8 条每条 ≤2 行）、验收门禁、终审 20 条清单。
- Stage 8"样张先行"步骤（`stage_08_writing.md`）：全量写作前先产 1 页样张（摘要+一节正文）给用户过目风格；退出条件新增呈现规范 20 条自查与样张确认两条。
- Stage 9"视觉基准对照协议"（`stage_09_review.md` Step 2）：用户提供优秀论文 PDF 作锚点，逐页对照摘要可扫读性/加粗密度/图占比/图题长度/版面留白/标点一致性。
- Stage 5 风格试产比选（`stage_05_subproblem_loop.md` D.1）：首次出图前产 2 套风格样张用户拍板；C 节新增收敛性验证时程纪律（S-01：收敛扫描必须打到判据量成熟时程，不得跟着题面输出窗口走）。
- Stage 6 参数档网格充分性检查（`stage_06_robustness.md` Step 4，S-05）：使边界层骤减的参数档必须单独做网格收敛检查，未通过从灵敏度排序剔除并如实标注。
- 出图委派协议三条（`parallel_dispatch.md` 挂接点 3.5，T-05/S-08）：改动必重跑 figqa --strict 并贴原始输出；交付前逐张 Read 自检五项清单；figqa 通过=必要非充分必须声明。
- `figure_skill_bridge.md` 图内注释预算与图宽/物理尺寸规则。
- `scripts/renumber_equations.py`：公式编号增删后按出现顺序重排定义 + 打印引用清单供人工核对（`--root` 接口）。

**修复**
- pandoc 3.x 编译链（T-01，开箱即坏）：6 套 `templates/latex/*/main.tex` 与 `scripts/render_paper.py` 幂等注入 `\providecommand{\pandocbounded}[1]{#1}` + `array` + `calc`；负向对照实测剥掉三件套编译即失败，修复承重。
- 页数口径三处统一（T-04/S-06）：`submission_checklists.md` cumcm 节（无硬上限按当年通知不作硬阻断）、`paper_skeleton.md`（22-25 页=正文+参考文献、附录不计）、stage_09 已有口径留指针；明令禁止以缩小行距/字号压缩版面凑页数。
- `consistency_audit.py`（T-06/S-07）：图表引用闭环支持 LaTeX 自动编号——`\label{fig:N}/\label{tab:N}` 数字部分计入定义集；longtable 环境纳入 caption 计数序（此前 pandoc 表格全部漏定义）。
- `pdf_qa.py`（T-07）：重复题注检查修复中文换行误报——行首命中后做题注形态判定（分隔符/接续词区分），同编号仅后续文本完全相同才算重复。
- `figure_lint.py`（T-08）：R7 顶/右 spine 警告在存在 twinx 右轴时豁免（top 仍报）；R4 小热力图 colorbar 警告加触发条件矩阵规模 ≤16×16。
- `claim_consistency_check.py`（T-09）：科学记数法等价匹配（e-13/×10⁻¹³/\times10^{-13} 同值）；只出现在 display-math 内的公式常数豁免；豁免与等价降级 info。
- `md_authoring_spec.md` 避免清单补三条 pandoc 陷阱（T-02）：caption 必须紧贴表格否则丢表号；无题注 longtable 也占 table 计数器；手写 `\qquad (N)` 编号增删后必须全文重排。

**摘要模板**
- `competitions/cumcm/abstract_template.md`：段 3 改"针对问题N："导语式；新增"呈现要求"小节（关键结果加粗/标点全角/关键词格式）；自检清单 +3 项；完整示例整体改写（导语分段、关键数字加粗、全角标点）。

**补完（同日二次，对照 2025 优秀论文 7 篇全量分析后）**
- 图题格式定版为"图 N 说明"（无冒号，与 `md_authoring_spec.md` §3 一致，7 篇中 4 篇同式），`cn_presentation_spec.md` §7.1 定稿；公式编号定版"默认全局连续"（7 篇中 6 篇如此），同文件 §5.1 收窄。
- 版本元数据同步：两个 plugin.json 与 README 徽章/开发日志 → 2.7.0。
- `paper_skeleton.md`：新增"9. AI 使用说明"占位节（7/7 篇优秀论文均含 AI 披露，两式可选）与各问"5.x.4 模型总结"收束段占位（学自 B060/C023）；`stage_08_writing.md` §5 强制 checklist 加收束段一项；`submission_checklists.md` cumcm 节加 AI 披露检查行；外部实测引用统一注明"存于用户工作区不入库"。

**回归**：tests/ 全量 169 passed + 4 subtests（1 个 OpenAlex 联网用例按环境跳过）；四脚本各附修复回归用例；6 套模板各自引擎编译通过；render_paper 全链三编零 Undefined control sequence、零 Overfull。
**审查**：跨家族语义复审发现 5 项 P1 已全部修复并附探针证据——`_sci_traced` 超大指数 OverflowError 崩溃与 1e-300 容差下限吞真矛盾（改 log10 域回退 + 真相对容差）；R7 twinx 豁免从全图作用域细化到 axes 级（复用 `_twinned_with` grouper，混排图普通子图不再误豁免）；label 派生自动编号定义只进闭环不进"从未引用"告警（含 ":" 符号 token 同样跳过，纯 \label+\ref 文档零噪声）；stage_09 资格门页码口径与 cn_presentation_spec §1.2 对齐。另加代码围栏内 `$$` 不翻转 display-math 状态机保护。


## [2.6.0] 选型告知前移 + 文献检索默认触发 + 加载引用修通 (2026-09-11)

- 选型告知前移到用户可见：路由表新增模型选型入口（"这道题用什么模型"直进 Stage 3 选择卡，不进入求解）与"帮我求解"入口（无 stage 3 选型记录必须先补走选择卡，不得直接求解）；选择卡加"依据与文献"列；新增《选型总表》`cwd/selection_sheet.md`（人读产物，stage 3 生成初版、stage 5 每问 `A0` 确认后更新对应行；机器真源仍是 `decision_log.stages.3.selected_per_subproblem`）。
- 外源文献检索由"未命中才触发"改为选型期默认触发：stage 1/3/5 三挂点、stage 3 选型期默认触发（不再以 playbook 未命中域为前提），单挂点预算 ≤2 次检索、单次 ≤5 篇，命中 24h 缓存不重复消耗配额；按 stage 加载表与"与外部资源的关系"两处口径统一。
- 必停点 5→6：新增第 6 必停点"每问选型确认"（Stage 5 每个 Qi 求解前 `A0` 步，登记键 `checkpoints.per_qi_selection["Q<i>"]`）；与 stage 3 已拍板方案一致时轻量确认（一行摘要 + 编号菜单），不一致或本问无 stage 3 记录时出完整选择卡；与 `card_decision` 各自独立登记，不得互相顶替。
- 加载不到的文件引用修通 11 处：反馈层通配 `feedback_layer*.md` 展开为 L1-L4 四个显式路径（流程总览、用户指令快捷同步补 L2/L4 文件名）；按 stage 加载表补 stage 4/6/7 三行（`stage_04_foundation` / `stage_06_robustness` / `stage_07_evaluation`）；竞赛经验笔记 `competitions/<comp>/empirical_notes.md` 入数据来源声明；三处裸 `case_retrieval.md`、`source_manifest.json`、收敛准则 `feedback_layer1_critic.md` 改显式路径；vendor scibox-* 两处加"本分发版不含、自动降级"括注；`runtime/`（薄执行器，必停点代码强制）与 `evals/`（留出题评测 + 反例回归）补可达入口；局部写作入口加"求解或选型必须先过 stage 3 选择卡"护栏。
- 工具挂点补齐：三赛联合工具补 `scripts/retrieve_cumcm_cases.py` 向后兼容入口（检索 `competitions/cumcm/cases/index.json`）；stage 9 补 `scripts/score_artifact.py --mode judge` 可执行入口。
- 版本元数据统一 v2.6.0：SKILL.md 标题与版本段、`.claude-plugin/plugin.json`（原漂移为 2.2.0）、`.codex-plugin/plugin.json` 统一 2.6.0。
- 提交打包补 gate 8 门禁预检：`scripts/package_submission.py` 在打包前直接 import `check_gate.py` 校验 gate 8（不起子进程），未过则拒绝打包且 dry-run 同样预检并明示"正式打包会被拒绝"；decision_log 缺失或无法解析时仅 ⚠️ 提示不拦截（保持 `--competition` 覆盖、无 state 预览的既有行为）；新增 `--allow-gate-fail` 显式逃生门（降级放行并打印中文警告）。文档同步 submission_checklists / SKILL.md stage 9 行，tests 新增 `test_package_submission_gate8.py`（6 用例）。

## [2.5.0] 领域 playbook 层 + 图表图题纪律 + 结构整理 (2026-09-10, 已转正安装)

> 依据 analysis/playbook_plan.md（六层蒸馏资产盘点：写作/案例层达标不重蒸，建模层缺域级深度动作）。bug-reviewer 两轮审查闭环（P0 调度 playbook 证据降级规则入文件）。

- 新增域级 playbook 层 `competitions/huaweibei/playbooks/`（README 契约 + 三域：信号诊断 8 动作 / 空间几何 6 动作 / 调度优化 9 动作）：每条动作五要素（基线失效→机制→前提/接口→反例→迁移边界）+ 证据来源（论文深读/我方实验/双向）+ review_status 三态；失效面无论文实证锚点的条目降级 proposed（文件内含降级规则声明）。接线 stage 1（域命中提示）/ stage 3（候选生成输入之一，不替代缺口驱动选型）。
- 深读层域级消费入口 `competitions/huaweibei/papers/domain_index.md`：33 篇逐篇 paper_id→域→核心动作→JSON 锚点，stage 3 按域命中后定向读取。
- 机制库 +1 条 `huaweibei_2021_F_optimality_anchoring`（最优性锚定，现 6 条）。
- 图表"图题进 caption"纪律（对齐优秀论文惯例）：15 个数据图模板删除图内标题（suptitle/单面板 set_title，多面板保留 ≤6 中文字符当量短标签）；`figure_lint.py` 新增 R8 硬门（三位置标题收集 + colorbar/twinx 逻辑面板判定含旧版 mpl `<colorbar>` label 回退 + `--allow-infigure-title` 逃生门），R5 同步修三位置漏检；文档同步 figure_skill_bridge 3.6 节 / stage_08 / distilled_figures / playbooks README。tests +13（test_figure_lint_r8）。
- 结构整理（依据 analysis/reorg_audit/ 双路审计：引用矩阵 + 官方加载集）：
  - SKILL.md 加载协议由 8 个版本历史块重组为"通用与跨阶段 / 按 stage 加载表 / 竞赛专项"三段式（76→61 行，加载指令路径 token 差集为空；删除的仅为版本叙事与过期的"候选版新增 (未安装)"标签，其内容已随 2.4.0 转正）。
  - 元数据统一 v2.5.0：SKILL.md 标题（原漂移为 v2.3.0）、README badge（原 v2.2.0）与开发日志表补 2.3.0-2.5.0 三行、knowledge_workflow.md H1 去 0.7.3 前缀。
  - 陈旧引用修复：SKILL.md 路由表 scibox-diagram 补"分发版自动降级"注记；references/papers/README.md 两处 winning_patterns 路径改指 competitions/<comp>/。
  - 删除运行残留：技能内 `.mimosa/`×2、`outputs/figures/_smoke_test.*`、`__pycache__`/`.pytest_cache`、Windows 保留名误建文件 NUL（内容经核对为 mechanism_reviews.json 子集，备份于 analysis/reorg_audit/salvage/）、tests 目录残留的 test_prompts.json（14 条行为提示词从未被任何测试加载，同目录备份，该文件已随本条删除）。
  - `package_dist.py` 排除规则补 `.mimosa/` 与 `outputs/`（可再生产物不进分发包），test_evals 同步断言。
- 外源文献检索层：`scripts/literature_scout.py` + 协议文档 `references/literature_scout.md` + 16 测试（OpenAlex 主检索 + Crossref 429/503 自动降级 + arXiv 预印本补充，stage 1/3/5 挂点，方法卡 literature-card-1.0）。审查后修复：journal 字段取期刊名（display_name）而非出版商、payload 增加 total_results 命中量级、SSRF 白名单、缓存降级回填、自包含声明加联网例外、限流口径更正为"匿名约 100 次/天"。
- 回归：pytest 201 passed + 4 subtests（含 literature_scout 16 测试）；rubric 回归 6/6；quota_gaming_wide_scan 扫描面 10→15 文件（纳入 playbook 层）零命中。
- 描述文案去 AI 味（转正后补）：SKILL.md frontmatter 触发描述、版本与总述、README 顶栏、plugin.json 三段描述改为直白表述——删去"赛前兵检/Stage 知识包/多 runtime 入口/AGENTS.md packaging/state 互通"等开发视角黑话与工具名堆砌；agent 加载协议内的文件路径为功能路径，不在清理范围。

## [2.4.0] 建模与证据强化 (2026-09-09, 经 E 题留出对照五轮验证 + 两轮独立审查后转正)

> 依据 analysis/modeling_gap_review_2026-09-07.md 诊断与 revision_plan.md。E 题留出对照（stage 0-3/4-5Q1Q2/Q3/stage8/N 类修复）+ 一致性审查与 GPT 审查全部通过后安装。

- 新增 `references/modeling_evidence_protocol.md`（答题义务/概念操作化/缺口驱动组合/正式实现反例/证据约束写作）与 `references/mechanism_distillation.md` + `competitions/huaweibei/cases/mechanism_reviews.json` 机制侧录，`build_stage_pack.py` 自动附带。
- 评分层对齐：`rating_contract.json` dimension_interpretations 16 键重释旧配额键；hard_fail_rules +3（结论与结果状态冲突/自评分数当证据/数量配额当质量）；rubrics.md 与 stage 02/04/05/06/07/08/09 去除变量数、候选族数、修饰词命名、假设条数、图数、优缺点条数、扰动方法与档位硬编码、phrase_bank 命中计分。
- `score_artifact.py` 落盘条目标记 `self_assessed: true`；L1 分数降级为流程信号。
- 答题义务台账：`decision_log.stages.2.obligations` 镜像（模板已带），`check_gate.py --gate 5/8` 校验 unstarted 拦截 / partial 提示披露。
- 新增 `scripts/claim_consistency_check.py`：正文强结论（收敛/最优/提升/区间口径）与结果文件状态核验，fail/warn/info 三级。
- 案例层：cumcm 2023_B 标签人工修正；distill 生成器新增 tag_provenance 与 chain_confidence 字段。
- 回归：`evals/rubric_regression/`（6 例已知坏产物）；tests 新增 17 条。
- 复审轮补充（2026-09-09）：审题门三查→四查（新增权利查，红队职责加权利遗漏）；选择卡改候选档案制（SKILL.md/decision_ui_map/stage_03 三处同步）；templates/shared 假设与符号模板去数量区间；winning_patterns 全部引用改按节名；claim_consistency_check 加规则 5（数字可追溯）与规则 6（同对象两数值矛盾）；stage_08 退出加证据账本完整与真源对账；diangong/huashubei/mcm 知识层配额清剿；regression 扫描面扩至模板与竞赛层（quota_gaming_wide_scan）。

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

## [2.3.0] — 2026-09-06（2025 华为杯 F 题实测修复：必停点 + 程序门禁）

实测背景：2025 华为杯 F 题全流程跑完后发现 agent 全程自写自走——设计的必停点全部未问、L1 评分一次没落盘、图表无确认就出图、stage 状态与实际脱节。本版把"约定"升级为"登记 + 程序门禁"。

### 新增

- **五必停点协议（SKILL.md 新节）**: 启动 5 问（`kickoff_5q`）/ Stage 2 审题呈现确认（`analysis_confirm`）/ Stage 3 选择卡拍板（`card_decision`）/ Stage 5 每问图表菜单（`figure_menu["Q<i>"]`）/ Stage 5 每问 verdict（`qi_verdict["Q<i>"]`）。任何模式下都必须真问用户，唯一登记路径是 `decision_log.checkpoints`；五个键名在 SKILL.md / check_gate.py / stage_00/02/03/05 / decision_log 模板中逐字一致
- **`scripts/check_gate.py` 程序门禁**: `--gate N`（0-8）校验必停点登记 + `scores` 里 stage N 非空评分记录（E 合并，L1 评分未落盘即拦截并提示先跑 score_artifact.py），exit 1 拦截并输出缺失项中文清单，`--json` 机器可读；旧 schema 3.0 state 无 checkpoints 字段按 unanswered 处理不 crash；只读、无跳过开关；scripts/README.md 补索引行
- **默认细问模式 `interaction` 字段**: decision_log 新增 `interaction`（detailed 默认 | auto），auto 仅当用户明确说"自动模式/少问点/你自己定"时开启，只减少必停点之外的细节提问密度，五个必停点永远要问；与 mode（token 档位）正交，文档写清两者区别
- **Stage 5 每问图表菜单（stage_05 新增 D.1 步）**: 每个 Qi 验证通过后必须呈现图表数量（0/1/2/3+）+ 样式风格（自写 17 件数据图 / icarus 多面板主图 / 物理场·网络流图 / drawio 示意图 / TikZ 框架图 + "让我决定"）菜单，用户选定后出图并登记 figure_menu；qi_verdict 同步登记；与 Stage 2 图表规格冻结（规格框架）衔接不冲突
- **skill_issues 台账正式化（workspace_protocol §11）**: `cwd/state/skill_issues.md`，stage 0 随骨架创建（骨架清单 + stage_00 初始化命令同步）；自我纠错追加 `- S-NN | 日期 | 现象 | 根因 | 临时处理 | 是否建议入版`；stage 9 终审读台账，有"建议入版"项提示用户沉淀
- **icarus-figures vendor 收编（MIT）**: `templates/figures/vendor/icarus-figures/` 全仓库原样内嵌（paperfig 48 函数 + 5 个可编译 TikZ 范例），补齐复杂多面板主图、物理场/动力学图、网络流图与 TikZ 框架图；`references/figure_skill_bridge.md` 总路由表加 3 行路由；`templates/figures/vendor/VENDOR.md` 第 6 条登记出处与使用约束；SKILL.md 图表条目同步

### 变更

- `templates/shared/decision_log.json`: schema 3.0 → 3.1——新增顶层 `checkpoints`（默认 `{}`，含 `_checkpoints_doc`）与 `interaction`（默认 detailed，含 `_interaction_doc`）
- **全库活文档旧版本号统一**: 活文档（SKILL.md / references / templates / competitions / docs / runtime / AGENTS.md 等 60+ 文件）中 v7.x 旧线编号按 CHANGELOG 映射表统一转新编号线（v7.10.0→1.4.0、v7.9.x→1.3.x、v7.8.0→1.2.0、v7.7.x→1.1.0、v7.0-7.5→0.7.0-0.7.5、V6→0.6.0），共 285+ 处；`references/knowledge_workflow.md` 由旧名 knowledge_workflow_v73.md 更名而来（4 处引用同步）；CHANGELOG 历史条目与映射表按"原文照抄"政策保留旧编号；`dist/` 发布快照冻结不动
- SKILL.md: 版本头 v2.3.0；收敛准则 / 状态持久化两节加 check_gate 门禁引用；反例黑名单新增"必停点自问自答/跳过不登记（2025F 实测病根）"一行；加载协议加 v2.3.0 按需加载条目（skill_issues + check_gate）
- stage_00（启动 5 问 + 目录初始化）、stage_02（审题呈现确认）、stage_03（选择卡拍板）各补必停点登记话术与 check_gate 放行引用，不重写既有流程

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

- **新增**：`templates/figures/vendor/{scibox-diagram, scibox-figure, diagram-design}/` 三个上游原样副本（上游更新时整目录替换，本地不改写）+ `templates/figures/vendor/VENDOR.md` 出处/许可证/使用纪律说明。scibox-diagram：论文示意图 drawio 4 模板（五带路线图/三栏框架/三栏阶段流程/横版任务流水线，content JSON 驱动，单模板 99+ 图元的高密度信息架构）+ 从零手写与高保真复刻纪律 + check_layout.py 体检 + 100 个 Tabler 图标；scibox-figure：11 件科研绘图复刻模板（cv-roc-ci / paired-raincloud / tpe-surface / marginal-grid 等本 skill 未覆盖图型）；diagram-design v2.6：39 类编辑级 HTML/SVG 图表（答辩/展示场景，LICENSE.upstream 已随附）
- **变更**：`references/figure_skill_bridge.md` 顶部新增图表能力总路由表——论文示意图高密度交付默认走 vendor scibox-diagram；自写 drawio 6 模板保留为轻量快速路径；数据图仍以自写 17 件为默认（统一色板 + figqa/figure_lint 硬门），缺图型转 scibox-figure；答辩/网页/海报走 diagram-design；照图复刻走 scibox-diagram replication 路径
- **许可证注意**：sci-box 上游仓库未附正式 LICENSE 文件（README 宣称开源，Tabler 图标 MIT 见 ATTRIBUTION.md）；再分发 mathmodel-studio 前须确认上游补证或将 scibox-* 移出分发包，详见 `templates/figures/vendor/VENDOR.md` §5
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
