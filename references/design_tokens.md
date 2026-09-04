# 设计令牌 (Design Tokens) · mathmodel-studio v7.9.1

> 本文是全 skill 图表/示意图的**审美宪法**。所有 make_*.py 模板、drawio 生成器、
> 新图表必须从这里取令牌，禁止另行发明色值/字号/间距。
> 实现出口：配色 `style/palettes.py`，共享工具 `scripts/figkit.py`。
> v7.8.0：示意图与数据图表配色彻底分类（§1.5 色族 / §4.5 示意图族版式）。
> v7.9.0：编辑级排版纪律（§4.6）—— 4px 网格 / 圆角·描边·字阶梯 /
> 焦点盒规则 / 连接器六条军规 / 中文排版预算，蒸馏自 diagram-design (MIT)
> 与 sci-box scibox-diagram (MIT)；drawio 版式体检门禁 `drawio/drawio_check.py`。
> v7.9.1：追平 sci-box 信息架构 —— 字重层级制取代全字加粗（§4.5）、
> 两段式富文本卡（`figkit.rich_box` / drawio `rich_card`）、编号徽章/竖排标签/
> 结论脚注条零件、连线降重（1.3/小箭头头）、描边增 card=1.0 档、
> drawio_check 三个 WARN 级平庸检测、示意图"机器体检+九区盘点"双门
> （`figure_skill_bridge.md` §3.5）。

## 1. 色彩令牌

### 1.1 语义色（数据系列）
一律走 `palettes.get_palette(name)` / `figkit.load_palette(name)`，按绘制顺序取色。
可用色板：`academic_blue`(默认) / `cool_nature` / `muted_earth` / `okabe_ito` /
`npg` / `aaas` / `lancet` / `nejm`（后四套为 v7.7 新增真期刊板，蒸馏自 ggsci 公开色值）。

### 1.2 中性色令牌（非语义灰）
**禁止硬编码灰色系**，一律 `figkit.load_neutral(name)`：

| 令牌 | 色值 | 用途 |
|---|---|---|
| `ink` | #1F2A36 | 标题/正文主文字（近黑深蓝灰，比纯黑柔和） |
| `secondary` | #46535F | 次级文字、注释、轴标签 |
| `faint` | #8A97A3 | 弱化文字、水印级说明 |
| `grid` | #D9DEE4 | 数据图网格线 |
| `edge` | #C7D3DE | 卡片/节点盒描边 |
| `edge_strong` | #A9BDD0 | 节点盒强调描边 |
| `arrow` | #6B7B8C | 示意图连接箭头/参考线 |
| `panel_bg` | #F5F7FA | 面板/泳道浅底色 |
| `hairline` | #E8ECF0 | 分隔细线 |
| `white` | #FFFFFF | 卡片底 |

### 1.3 浅化/深化
一律 `palettes.tint(color, f)`（向白）/ `palettes.shade(color, f)`（向黑），
多层级渐变用 `palettes.tint_series(color, n)`。禁止手写浅化常量表。

### 1.4 语义角色纪律
- 主模型=色板第 1 色；基线=第 2 色或中性灰，全文恒定；
- 强调橙**每图至多一处**；红=风险/劣化，绿=达标/改进；
- 热力图发散色必须 0 居中（`get_cmap("correlation")` + center=0）。

### 1.5 示意图色族（v7.8.0，与 §1.1 数据色板彻底分类）
示意图（流程图/架构图/技术路线图/框架图）**不走 §1.1 数据色板**，一律走
`palettes.DIAGRAM_FAMILIES` 浅底色族（7 族 × 8 角色，色值蒸馏自 sci-box
scibox-diagram, MIT；全量色值表见 `color_typology.md` §2.4），
模板经 `figkit.load_diagram_family / load_diagram_families / load_diagram_page`
取色，drawio 走 `drawio_builder` 的 `family=` 参数：

| 角色 | 用途 |
|---|---|
| `fill` | 内容盒浅底（卡片/节点默认底色） |
| `stroke` | 内容盒描边（同族深一档，卡宽 1.2） |
| `accent` | 强调填充（子标题条/高亮盒/高亮描边 2.0） |
| `deep` | 深一档内容填充（次级层级盒） |
| `header` / `header_stroke` | 实色标题条底（配白字）与标题条描边 |
| `edge` | 连接器/箭头色（跨族不混色，一条连线只用一族） |
| `chevron` | 旗标/徽章填充（浅底配墨黑加粗字） |

页面令牌 `DIAGRAM_PAGE`：`ink` #262626（示意图墨黑）、`title_bar` #4F80BD
（通栏标题条）、`band_sep` #5B6B78（点线分带）等。固定族序
`DIAGRAM_ORDER_GENERIC`（通用 n 阶段）与 `DIAGRAM_ORDER_ROADMAP`
（五带路线图叙事）。

## 2. 字阶 (pt, 300dpi 输出)

| 角色 | 字号 | 字重 |
|---|---|---|
| 图标题 | 11 | bold |
| 轴标签 | 10 | regular |
| 刻度/图例 | 9 | regular |
| 子图标签 (a)(b)(c) | 11 | bold（figkit.panel_label 统一 -0.08/1.04） |
| 示意图节点正文 | 9–10.5 | regular |
| 示意图徽章/列头 | 10.5–12 | bold 白字 |
| 图内注释 | 8–9 | regular（下限 8pt，低于此必须重构布局而不是缩字） |

字体：sans 回退链 Microsoft YaHei → SimHei → PingFang SC → Arial；
公式走 mathtext（`$\mathrm{...}$`），中英混排时西文不换字体。
**mono 等宽链**（v7.9.0，`figkit.mono_chain()` / drawio `mono=True`）：
Consolas → DejaVu Sans Mono → Courier New，**只给数字/参数/公式标签**
（如 `RMSE=2.31`、`k=5`）；节点名/标题/正文永远 sans，中文不走 mono
（mono 字体无中文字形）。mono 是"技术性内容"专用，不是 blanket dev 风。

## 3. 数据图版式

- 尺寸：优先物理栏宽预设 `figkit.FIGSIZE`（single 89mm / onehalf 120mm / double 183mm），
  竞赛正文图沿用 `default` (7.2×4.5in)。
- spines：只留左+下（`figkit.despine` 已默认）；刻度朝外+次级刻度（mplstyle 已内置）。
- 网格：**默认只留极淡 y 向** `figkit.ygrid(ax)`；x 向网格仅在读数导向图（如甘特）开启。
- 图例：无边框（mplstyle 已设 frameon False）；≤4 项放图内空白区，>4 项放图下方横排；
  禁止挡数据。
- 标记：数据点白芯描边（markerfacecolor=white, markeredgewidth≈1.2）提升层次；
  辅助点（可行解/样本云）用低 alpha 中性灰退到背景。
- 导出：`figkit.save_fig(fig, prefix)` 三格式 PNG(300dpi)+SVG+PDF。

## 4. 示意图版式（流程图/框架图）

### 4.1—4.4 通用底座（v7.7.0）

- 画布：逻辑坐标=像素（dpi=100），节点盒圆角 `boxstyle="round,pad=...,rounding_size=8"`。
- 换行：一律 `figkit.wrap_text_balanced()`，消除吊行；盒内文字上下留白 ≥0.35 倍行高。
- 连接器：**默认正交圆角** `figkit.elbow_arrow()`（vh=层间下行，hv=栏间右行）；
  斜线仅在表达"汇聚/分发"语义时用 `straight_arrow(rad=0.08)` 微弧。
- 标题：图上方居中 12pt bold `ink`，与图体间距 ≥24px；可加 9pt `secondary` 副标题行。

### 4.5 示意图族版式（v7.8.0, sci-box 扁平风; v7.9.1 字重层级制修订）

- 脚本头部：`apply_style()` 后紧跟 `figkit.use_diagram_font()`（YaHei 真 700 粗体优先）。
- 内容卡：**两段式富文本卡** `figkit.rich_box()`（drawio 用 `rich_card()`）——
  **bold 标题行**（方法/动作名, body 档 10.5）+ **regular 明细行**（参数/口径/
  产出形式, note 档 9, 次级色; 纯 ASCII 明细可 `detail_mono=True` 走等宽链）。
  信息密度来自内容结构, 不来自加粗。单行卡（diagram_box）只用于标签性短词。
- **字重层级制**（v7.9.1 起, 取代"全字加粗"）：加粗只给标题条/徽章/卡片标题;
  卡内正文与明细一律常规字重。全字加粗 = 没有层级（drawio_check 有
  全字加粗 WARN 兜底）。
- 标题条 `figkit.diagram_header()`：族 `header` 实色底 + `header_stroke` 描边 +
  **白色加粗**字（白字只允许出现在实色标题条上）。
- 徽章/旗标：`figkit.num_badge()`（圈号圆徽章）/ drawio `badge()`：族 `chevron`
  浅底 + 族 `stroke` 描边 + 墨黑加粗字（结构件加粗）。
- 竖排标签：`figkit.vlabel()` / drawio `vlabel()` 逐字堆叠, 禁 rotate/horizontal=0。
- 结论脚注条：`figkit.footnote_bar()`（左族色 tick + 左对齐 note 档小字）。
- 连接器：族 `edge` 色（`figkit.family_edge()`）, 跨族不混色; **v7.9.1 起默认
  降重 lw 1.3 / 小箭头头**（连线退居二线, 内容才是主角; 强调主干用色不用粗）。
- 虚线分组容器：linestyle `(0,(4,4))`、族 `stroke`、无填充、宽 1.2；
  点线分带：`(0,(1,3))`、`DIAGRAM_PAGE["band_sep"]`（matplotlib 用 ax.plot 画框,
  避免 figqa 盒内标签豁免被容器 patch 误伤; drawio 用 dashed_container()/band_sep()）。
- **描边宽度体系**（四档, 不再随手给）：hairline 0.8 / **card 1.0**（内容卡,
  v7.9.1 降重）/ default 1.2（标题条、容器虚线）/ strong 2.0（焦点盒、--highlight）。
- **字号扁平纪律**（全图不超过 4 档）：图标题 16、标题条 12、卡标题 10.5、
  明细/注释 9。
- **禁止裸文本节点**：任何节点文字必须落在卡片里（figqa line-through-text /
  text-over-patch 零检出）；画布高按内容推导, 不留底部大片空白。

### 4.6 编辑级排版纪律（v7.9.0, 蒸馏自 diagram-design (MIT) + sci-box (MIT)）

以下纪律同时适用于 matplotlib 示意图与 drawio 生成器；令牌实现见
`palettes.py`（`DIAGRAM_GRID/DIAGRAM_RADIUS/DIAGRAM_STROKE_W/DIAGRAM_FONT_RAMP/
DIAGRAM_FOCAL_MAX/DIAGRAM_FONT_MONO`, 取口 `get_diagram_token()/snap4()`,
figkit 同签名转发）。

**① 网格与对齐（先排栅格，再写图元）**
- **4px 网格硬规则**：一切坐标、盒宽盒高、行列间距必须可被 4 整除
  （`figkit.snap4()` / `drawio_builder.snap4()`）；这是"不像 AI 随手摆"的
  最廉价手段。
- 同族元素**共用左边界与同宽度**；数量可变的组用等分公式
  `size = (span - (n-1)*gap) / n`，第 i 个起点 `a + i*(size+gap)`，禁手算每个坐标。
- 同族纵向步距固定，族间留 2–3 倍步距。

**② 圆角与描边阶梯**
- 圆角：`radius` 令牌 sm/md/lg = 4/6/8，**上限 10**（再大显"AI 味"）。
- 描边：`stroke_w` 令牌 hairline/card/default/strong = 0.8/1.0/1.2/2.0 四档，
  内容卡 1.0、标题条与容器虚线 1.2、焦点盒 2.0，不随手给值；
  连线默认 1.3 + 小箭头头（mutation_scale 11），强调主干用色不用粗。

**③ 焦点盒规则（focal rule）**
- 每图至多 **2 个焦点节点**（`DIAGRAM_FOCAL_MAX`）：焦点 = 族 accent 底 +
  族 stroke 描边 2.0（`figkit.diagram_box(focal=True)` / drawio
  `card(focal=True)`）。焦点给"全文最重要的 1–2 个节点"；超过 2 个等于没有焦点。

**④ 连接器六条军规**（违反任一条即返工）
1. 非共轴节点之间**只用正交圆角连线**（`figkit.elbow_arrow()` / drawio
   `edgeStyle=orthogonalEdgeStyle;rounded=1`），**禁止斜线**；
   "汇聚/分发"语义用下方母线，不用斜线。
2. 一分多/多合一画成"**竖线 + 横母线 + 分支**"（`figkit.bus_fan_v()/bus_fan_h()`；
   drawio 用无箭头干段 + 分支箭头），不画 N 条独立斜线。
3. 多条连线共用一条盒边时，附着点按 **k/(n+1) 扇形排开**、间距 ≥12px
   （`figkit.fan_offsets(n)` / drawio `fan_edges()`），任何两条连线
   不共享同一附着点。
4. 连线**不穿过非端点盒子**；实在绕不开时改虚线（表"穿越而非交互"），
   且标签放在可见端。drawio 侧由 `drawio_check.py` 连线穿盒检查兜底。
5. 边标签不压线：标签与连线之间留 ≥6px 间隙，drawio 标签自带
   `labelBackgroundColor=white` 遮底。
6. 端点离盒边 1px，不正好压在边界上（否则渲染器与体检都容易误判）。

**⑤ 密度与删除纪律**
- 目标密度 4/10：技术完备但不需要导读。**节点 >9 个就拆成总览图+细节图**。
- 最高质量的修改通常是删除：两个永远同进同退的节点合并为一个；
  布局已自明的关系不画线。
- 画不出语义的箭头不要画（谁到谁、单向双向、扇入扇出必须说得清）。

**⑥ 中文排版预算（sci-box 实测口径，drawio/手写布局用）**
- 全角 ≈ 字号宽，半角 ≈ 字号/2，行高 ≈ 字号 + 3；盒可用宽 = 宽 − 8。
  **16px 字号下 160px 宽的盒子每行最多 9 个汉字**。
- 竖排文字逐字 `<br>` 堆叠，**禁用 `horizontal=0`**（中文会躺倒）。
- `overflow=visible` 只给无外框的独立标签；有框盒子加了它，文字溢出框外不报错。
- 生成器侧用更保守的 1.45/0.72 字宽模型换行（宁宽勿溢），体检侧用真实
  度量判溢出（`drawio_check.py`），两层互补。

**⑦ 版式门禁（drawio）**
`finalize()` 落盘后自动跑 `drawio/drawio_check.py`：文字溢出/越界/重复 id/
实心盒重叠（>30% 小盒面积）/连线穿盒/位图内嵌 = **FAIL（退出码 1）**；
端点压边/疑似空盒/字号 >4 档/填充色发散 = WARN；v7.9.1 起 WARN 新增三个
**平庸信号**：全字加粗（>90% 文字元素加粗）、实心盒 >20（密度超预算）、
连线描边 >2.0。
`MATHMODEL_DRAWIO_CHECK=0` 关闭，`MATHMODEL_DRAWIO_STRICT=1` 时 WARN 也失败。
也可手动体检任意文件：`python drawio/drawio_check.py <file> [--strict]`。
机器体检通过后仍须**看渲染图**做九区盘点（`figure_skill_bridge.md` §3.5）：
机器查得出硬伤，查不出平庸。

## 5. draw.io 可编辑模板（drawio 生成器）

- 生成器输出 .drawio (mxGraph XML)，样式必须与 §1–§4 令牌一一对应：
  圆角 rounded=1，arcSize≈8；连线 edgeStyle=orthogonalEdgeStyle，rounded=1。
- v7.8.0 族化：示意图类模板的阶段/泳道/卡片/徽章/标题条着色走
  `DIAGRAM_FAMILIES`（`card()/badge()/header_bar()/lane()` 传 `family=族名`,
  不传保持 v7.7.0 配色行为向后兼容）：族化卡片 fill=族 fill、stroke=族 stroke、
  `fontStyle=1`、`fontColor=#262626`；族化徽章 chevron 底 + 族 stroke 描边 +
  墨黑加粗字；族化标题条 header 实色底白字；另有 `dashed_container()`（4 4 虚线
  容器）与 `band_sep()`（1 3 点线分带）。
- v7.9.0 纪律化：`card(focal=True)` 焦点盒（accent 底 + 2.0 描边，每图 ≤2 个）；
  `edge(exit_frac=/entry_frac=)` 分数锚点与 `fan_edges()` 一分多扇出
  （附着点 k/(n+1)）；`text(mono=True)` / `edge(mono_label=True)` 等宽数字标签；
  族化卡/标题条默认描边对齐 `DIAGRAM_STROKE_W`（default 1.2 / strong 2.0）；
  `snap4()` 4px 网格捕捉；`finalize()` 自动跑 `drawio_check.py` 版式门禁
  （§4.6⑦）。
- 字体族在 drawio 里统一写
  `fontFamily=Microsoft YaHei,PingFang SC,Hiragino Sans GB,Helvetica`
  （sci-box style 串），字号与 §2/§4.5 字阶对应（drawio 默认单位 pt，直接映射）；
  数字标签用 `fontFamily=Consolas,DejaVu Sans Mono,Courier New`。
- 每个模板页留 ≥40px 页边距；节点 id 语义化（如 `layer1_node2`），方便用户定位编辑。

## 6. 反模式（禁止清单）

- ❌ 彩虹/jet colormap；❌ Office 默认色（#C00000/#7030A0/#00B0F0 系）；
- ❌ 纯黑 #000000 正文（用 ink）；❌ 直吊行/盒内贴边文字；
- ❌ 双 y 轴（除附录诊断图）；❌ 3D 效果/渐变柱体/阴影柱体；
- ❌ 图内超过 2 处强调色；❌ 脚本内硬编码任何灰色（走 NEUTRALS）。
- ❌ 非共轴节点间画斜线（必须正交圆角）；❌ 一分多画 N 条独立斜线（用母线）；
- ❌ 多条连线共享同一盒边附着点（按 k/(n+1) 扇开 ≥12px）；
- ❌ 焦点盒超过 2 个（等于没有焦点）；❌ 圆角 >10px / 描边随手给值；
- ❌ 节点名用等宽字体（mono 只给数字/参数标签）；
- ❌ 坐标不吸 4px 网格（先 `snap4()`）；
- ❌ 一张图超过 9 个节点还不拆总览+细节。
