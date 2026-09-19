# docx 终稿通道协议（冻结后的 Word 终改链）

> v2.9.0 新增。定位：md 真源 → **docx 终稿**（人在 Word 改呈现层）→ PDF → 终检。
> 与审阅件模式（`scripts/export_docx.py`，docx 只给队员圈批注）是两条不同定位的链；
> 本通道的 docx 本身就是终稿介质。依据：`讨论稿_skill改进_20260915.md` §4 的
> 5 个缺口（终改只能在 LaTeX 源里做、Word 用户被排除在终稿环节外等）已端到端实测定位。

## 通道总览

```
Stage 8 退出门禁全过（冻结/claim/xref/呈现 20 条）
  → decision_log 登记 docx_channel=true（声明切换，此后 md 冻结）
  → scripts/export_final_docx.py  （编号注入 + 封面块 + reference.docx 样式；输出文件名带**秒级**时间戳，同秒重复导出自动改名 `_2/_3…`，不覆盖已有产物——**该秒级 + 安全后缀只属本终稿导出**，审阅件 `scripts/export_docx.py` 仍是分钟级旧口径）
  → 人在 Word 改呈现层（白名单见下；禁区：任何数字/公式/表值/结论）
  → scripts/docx_to_pdf.py        （Word COM 主路径，soffice 兜底）
  → 终检三件套：scripts/docx_number_recheck.py（数字回检）
              + docx 版 PDF 逐页视觉验收（复用 stage_09 流程）
              + cn_presentation_spec §10 二十条对该 PDF 重查
  → 若动了禁区内容：回退 md 修改、重跑门禁、重新导出（见回退条款）
```

## 入口条件（三条全过才准进）

1. **Stage 8 退出门禁全过**：冻结 / claim 证据链 / 交叉引用 / 呈现 20 条检查完成。
2. **冻结完成**：`state/frozen_numbers.json` 覆盖摘要与正文全部关键数字，无 stale 条目。
3. **声明切换登记**：在 `cwd/state/decision_log.json` 记 `docx_channel: true`
   （声明后 md 真源冻结，任何正文修订走回退条款，不许双头改）。
   **v2.9.1 起**：stage 8 样张先行时已选终稿链的，`final_chain: "docx"` 本身即切换声明，
   无需再记 `docx_channel`（两键等价，查任一即可）。

数字还在变（结果未收敛 / 冻结表还在增长）的阶段**禁用**本通道——先回 md 链改完再进。

## 人改白名单 / 禁区

进 Word 之后只许改**呈现层**：

| 白名单（允许） | 禁区（一律不许动） |
|---|---|
| 措辞润色、错别字、标点（全角体系，cn_spec §2） | 任何数字（含有效位、正负号、单位） |
| 段落间距、行距、字号在规范区间内微调 | 任何公式（OMML 对象一个字符都不改） |
| 图位置、图幅（宽度 85-100%/60-80% 版心内） | 任何表格单元格的值 |
| 关键词分隔、空行、分页位置、节号引用修正（见下） | 结论的方向与强度（"约/不超过/显著"等限定词） |
| — | 参考文献条目内容 |
| — | **图注/表注措辞**（唯一来源在 `真源.md` 图表登记表"终稿图注"列：须回源改该列再重新导出，Word 侧只可改字号/位置等呈现属性） |

判断不准时的默认动作：不改，回 md 链改。

> **硬编码节号引用注意事项**：md 正文中手写的"详见 5.2 节"式节号引用，若当初按
> tex 链编号写成，在 docx 链下编号可能不同（tex 链章名由 LaTeX 模板硬编码分层，
> docx 链按 md `##` 直接成章，同一标题的层级与序号会错位——如 tex 链的 5.1 节
> 在 docx 链可能是第 9 章）。人改阶段**必须逐条核对并修正节号指向**（属呈现层
> 可改范围，不算禁区）；终稿 PDF 视觉验收时把节引用指向列入抽查明细。

## 三步终检（docx 定稿必过）

1. **数字回检（硬门禁）**：`python scripts/docx_number_recheck.py --docx <终稿.docx> --frozen state/frozen_numbers.json`
   —— 冻结表每条数字必须仍在全文出现（科学记数法等价、缩写形态 warn）；
   FAIL 即呈现层改动触及禁区，走回退条款。退出码 1 = 拦截。
2. **docx 版 PDF 逐页视觉回证**：`python scripts/docx_to_pdf.py <终稿.docx>` 出 PDF 后**逐页回证、
   结论带页码**（范围与回证项单权威 = `references/cn_presentation_spec.md` §9.2：标题页/摘要页/图表页/
   公式页/参考文献页/附录页全覆盖；抽页只能记"局部检查"，覆盖不全标 `未完成`）。
   派发前先 `python scripts/pdf_qa.py <终稿.pdf> --page-map` 取页码映射表随 prompt 给出（C3），
   验收对象用带时间戳副本，禁止同名覆盖；结论只能来自真实渲染页。
3. **呈现 20 条重查**：`cn_presentation_spec.md` §10 二十条对该 PDF 同样适用——
   docx 通道时验收对象是 docx 版 PDF，不是 tex 链 PDF。图页另按 §7.6 核对"图与图注同页 /
   页尾空白 <1/3 页"（导出链 Step F 已自动 keepNext，留白过大时按 §7.3 调图宽或收束图前段落）。

三件全过才可打包提交（提交流程仍走 `references/submission_checklists.md`）。

> 呈现层后处理链（v3.1.0 起）：`export_final_docx.py --presentation`（默认开）导出尾部自动跑
> `docx_presentation_postprocess.py` 六步——A 数学字体政策（见下）/ B 编号右顶格 / C 数据表三线 /
> D 自适应+逐节版心+居中+行禁拆 / E 单元格排版（短列居中、长文本列整体左、零缩进零段距单倍行距）/ F 图与图注同页（keepNext）。
> 每步统计在导出日志的 `[Step X]` 行, 便于核对（改图改表后重导出即可, 无需手工重跑）。
>
> **数学字体政策（v3.1.0 定版）**：`docx_presentation_postprocess.py --math-font auto|upright|conventional`
> （默认 `auto` = 读 `decision_log` 顶层 `math_font`/`math_font_policy`/`upright_math`，`stages.0.notes` 兜底；
> 解析器 `scripts/math_font_policy.py`）。`upright` 才注入 `m:sty="p"`；`conventional` 与**未登记/冲突**时
> **保持输入并告警**（不逐字符改斜、不静默取舍）。Step A 不撤销既有 `m:sty="p"`：成稿已是"全刷正体"而政策
> 改判 `conventional` 时，正确动作是**回源改政策后重导出**，不在 docx 上反向处理。
> **节末公式段**（段落自带 `sectPr` 且为 display 公式）跳过包表并告警——须回源把公式移出节界。
> **窄支持与告警清单（不假装通过；命中即回源）**：① 独立公式尾编号支持**两种明确形态**：(a) `oMathPara` 公式段 + `\qquad` 幸存空白 + `(N)`（H1 判据）；(b) **独立 `oMath` + 尾部纯编号段**（保守白名单：恰一个直接 `oMath`、编号 run 全在公式之后、run 内仅 rPr + 单个 `w:t`、编号文本纯为 "(N)"）。**形似的复杂形态**（超链/字段/换行/嵌套/编号在前/夹带说明文字）**保持输入并计数告警 → 回源整形成上述两形态之一**；紧贴主体的括号（`f(1)`/`a+(2)`）一字不动；② **多栏节**未建模（按单栏版心算 + 未支持警告）→ 多栏稿回源评估；③ **裸函数名**（如 `exp`）源侧须写 `\exp`，否则按普通字母变量渲染；④ 参考文献 `\bibitem` 的转换范围：**references 角色文件整文件**（无标题时导出侧合成"## 参考文献"）**或**正文文件里的**显式"参考文献"节**（标题级 ≤2，即 `#`/`##` 等，同级或更高级标题闭节）；两处之外的条目**一律明确告警未转换、不算通过**（与 `ref_order_audit` 的 outside 提示对应）。


## 回退条款

- docx_number_recheck FAIL，或视觉验收发现需要动禁区内容：
  1. 把要改的内容回写到 md 真源（`paper_workspace/`，原地修订 + 真源修订记录追加版本行）；
  2. 重跑受影响的门禁（freeze_numbers check / claim 链 / consistency_audit）；
  3. 重新 `export_final_docx.py` 导出（时间戳新文件，不覆盖旧导出）；
  4. 旧的违规 docx 移入 `_archive/`，不得再作为终稿候选。
- 禁止在 Word 里直接改数字后重跑导出——导出会从 md 重新生成，Word 侧改动全部丢失。

## 与审阅件模式的关系

- `export_docx.py`（审阅件）默认模式**不变**：docx 只作圈批注载体，批注由 agent
  读取后人工合回 md，禁止反向转换覆盖真源（workspace_protocol §3.1 全文继续有效）。
- 本通道是 §3.1 的**终稿例外**：冻结完成并登记切换后，docx 升为终稿介质，
  纪律 = 数字回检门禁（本文档三步终检）；未登记切换时一切按审阅件模式执行。

## 何时不该用

- **mcm 等英文赛不适用**：英文赛走 LaTeX/Memo 链，呈现规范不同，本通道的
  版式（宋体小四/黑体标题/首行缩进）是中文竞赛口径。
- **数字还在变的阶段禁用**：见入口条件——冻结前的 docx 终改等于在沙上盖楼。
- 只需要队友看稿圈批注：走 `export_docx.py` 审阅件，别进本通道。

## 故障兜底

| 症状 | 处置 |
|---|---|
| 本机无 Word 但有 LibreOffice | `docx_to_pdf.py` 自动落 soffice 无头转换 |
| Word 和 soffice 都没有 | 手动用任意 Word 兼容编辑器打开 docx → 另存为 PDF；或装 pywin32 + Word |
| Word COM 卡住/残留进程 | 脚本已 try/finally Quit；仍残留时任务管理器结束 WINWORD 后重试 |
| pandoc 报缺图 | 检查 `figures/` 相对 `paper_workspace/` 的位置；缺图是降级告警不是失败 |
| 样式基准丢失 | 重跑 `python templates/docx/build_reference_docx.py` 再生成 reference.docx |

## 配套脚本

| 脚本 | 职责 |
|---|---|
| `scripts/export_final_docx.py` | md → docx 终稿（图表编号注入、封面块、参考文献/附录豁免编号） |
| `templates/docx/build_reference_docx.py` | 生成样式基准 `templates/docx/reference.docx`（A4/宋体小四/黑体标题/页脚页码） |
| `scripts/docx_to_pdf.py` | docx → PDF（Word COM 主路径，PowerShell COM 与 soffice 兜底） |
| `scripts/docx_number_recheck.py` | 终稿数字回检（冻结表底线门禁 + 新数字软清单） |
