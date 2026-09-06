# 统一图表配色体系（0.7.4 建立 · 1.1.0 扩展 · 1.2.0 示意图色族分类）

> 全 skill 图表配色的**单一权威源**。八套标准色板（含 1.1.0 四套真期刊板）+ 中性色令牌 + 示意图色族（1.2.0）+ 数据类型映射 + 硬规则 + 灰度校验。
> 代码实现: `templates/figures/style/palettes.py` | 基础样式: `templates/figures/style/mathmodel.mplstyle`
> 设计令牌章程（色值/字阶/版式/反模式全量）: `references/design_tokens.md` | 模板公共底座: `templates/figures/scripts/figkit.py`
> 色板全部蒸馏自历史竞赛工作区的实战验证配色与 ggsci 公开色值; 示意图色族蒸馏自 sci-box scibox-diagram (MIT), 不是想象的"最佳实践"。

---

## 1. 旧口径废止声明

0.7.4 前, 配色规范有三处互相矛盾的口径, 自本文件发布起**全部废止**:

| 旧口径 | 位置 | 处置 |
|---|---|---|
| `CHAMPION_PALETTE = ['#2E86AB', '#A23B72', ...]` | `references/huashubei_figure_pack.md` §0 | 保留为 `academic_blue` 的向后兼容别名（`get_palette('champion_palette')` 等价生效）; 色值历史: 历史竞赛工作区实战验证配色, 原 #A23B72 已由主色 #1F4E79 取代并补中性灰 #6C757D |
| "配色统一（matplotlib + seaborn-deep, 不要默认 tableau）" | `references/stage_09_review.md` Step 2 | 已改为指向本文件 |
| 11 个模板脚本各自硬编码颜色（Times/Arial 混用, 无中文 fallback） | `templates/figures/scripts/templates/make_*.py` | **已全部改造**（1.1.0）: 14 个既有模板全部迁移 figkit + palettes, 情况见 §7 |

**冲突裁决规则**: 任何文件与本文件冲突时, 以本文件 + `palettes.py` 为准。

---

## 2. 标准色板

0.7.4 四套（实战蒸馏） + 1.1.0 四套真期刊色板（蒸馏自 ggsci 公开色值），详见下表与 2.1-2.3。

### 2.0 实战蒸馏四套（0.7.4）

| 色板 | 色值（顺序即绘制顺序） | 来源与气质 |
|---|---|---|
| `academic_blue`（默认） | `#1F4E79 #2E86AB #F18F01 #C73E1D #3B8C6E #6C757D` | 历史竞赛工作区实战验证配色。高对比蓝橙体系, 中文竞赛评委最熟悉; 灰 `#6C757D` 专用参考线/网格; 备用第 7 色 `#7E57C2` |
| `cool_nature` | `#2C3E50 #1F77B4 #17A2B8 #6E8EBF #D97706 #C0392B` | 历史竞赛工作区 `fig_style.py`。冷色 Nature/IEEE 期刊风, `#D97706` 橙为唯一强调色, `#C0392B` 红仅作警告; 配 (a)(b)(c) 子图编号 + 去顶右 spines |
| `muted_earth` | `#506B84 #A77A43 #6E8B74 #8B4F4A #7C8A96 #39444D` | 历史竞赛工作区 `plot_utils.py` PAPER_COLORS。灰蓝金低饱和, 稳重学术; 各色有 `*_light` 浅变体（`#DCE5EC #E6D7BE #DCE7DF #EADAD8`）可作填充底色 |
| `okabe_ito` | `#0072B2 #E69F00 #009E73 #D55E00 #CC79A7 #56B4E9 #F0E442 #000000` | Okabe-Ito 色盲通用标准色。MCM 英文赛 / 需灰度打印 / 评委可能色弱时的兜底 |

### 2.1 真期刊色板（1.1.0 新增，蒸馏自 ggsci 公开色值）

| 色板 | 色值（顺序即绘制顺序） | 来源与建议场景 |
|---|---|---|
| `npg`（Nature） | `#E64B35 #4DBBD5 #00A087 #3C5488 #F39B7F #8491B4 #91D1C2 #DC0000 #7E6148 #B09C85` | Nature Reviews 系：朱红/青/墨绿/靛蓝主四色, 高辨识暖冷对撞。英文投稿 / 答辩 PPT / 近年 ML·生信论文风；别名 `nature` |
| `aaas`（Science） | `#3B4992 #EE0000 #008B45 #631879 #008280 #BB0021 #5F559B #A20056 #808180 #1B1919` | Science 系：靛蓝主色 + 克制红，稳重经典；别名 `science`。组合序列多的对比图 |
| `lancet`（Lancet） | `#00468B #ED0000 #42B540 #0099B4 #925E9F #FDAF91 #AD002A #ADB6B6 #1B1919` | 医学期刊：皇家蓝/正红经典对色。风险-对照类（A/B 分组）分析 |
| `nejm`（NEJM） | `#BC3C29 #0072B5 #E18727 #20854E #7876B1 #6F99AD #FFDC91 #EE4C97` | 新英格兰医学杂志：砖红/钢蓝主对色 + 琥珀/松绿辅助，低攻击性高级感。临床/流行病学图表 |

**场景规则**：期刊色板面向"论文投递/答辩呈现"的审美目标；中文竞赛正文图仍推荐 `academic_blue`（§4）。一篇论文只绑定一套主色板，摘要图与正文图逐色一致；使用期刊板时在图表计划的 `palette` 字段写 `npg/aaas/lancet/nejm` 之一。`npg` 与 `aaas` 自带口语别名（`palettes.get_palette('nature')` / `get_palette('science')`）。

### 2.2 中性色令牌 NEUTRALS（1.1.0）

所有"非语义灰色"（正文、文字层级、网格、描边、箭头、面板底）一律从 `palettes.NEUTRALS` 取，**禁止在脚本里另行硬编码灰色系**。取色走 `get_neutral(name)`（模板脚本走 `figkit.load_neutral(name)`）：

| 令牌 | 色值 | 用途 |
|---|---|---|
| `ink` | `#1F2A36` | 标题/正文主文字（近黑深蓝灰，比纯黑柔和） |
| `secondary` | `#46535F` | 次级文字、注释、轴标签 |
| `faint` | `#8A97A3` | 弱化文字、水印级说明 |
| `grid` | `#D9DEE4` | 数据图网格线（`figkit.ygrid` 默认色） |
| `edge` | `#C7D3DE` | 卡片/节点盒描边 |
| `edge_strong` | `#A9BDD0` | 节点盒强调描边 |
| `arrow` | `#6B7B8C` | 示意图连接箭头、参考基准线 |
| `panel_bg` | `#F5F7FA` | 面板/泳道浅底色 |
| `hairline` | `#E8ECF0` | 分隔细线 |
| `white` | `#FFFFFF` | 卡片底/纯白背景 |

语义角色 → 取色规则见 `palettes.SEMANTIC_ROLES`（primary/baseline/accent/risk/ok/reference），role 只约束语义，实际色值由所选色板与 NEUTRALS 共同决定。

### 2.3 参数化浅化/深化（1.1.0）

替代各模板手写的浅化常量表（`*_light`、`strip_white` 等），同一套 API 由 `palettes.py` 提供、`figkit` 转发：

```python
from palettes import tint, shade, tint_series
light = tint("#1F4E79", 0.80)        # 向白混合 80% → 面板底色/色带浅化; faction: 0=原色 1=纯白, 常用 0.4-0.9
dark  = shade("#F18F01", 0.20)       # 向黑混合 20% → 描边/徽章压深; 常用 0.15-0.4
strip = tint_series("#1F4E79", 5)    # 5 级等差浅化序列 (roadmap 层带默认: lo=0.80 → hi=0.42)
```

`grayscale_check(colors, all_pairs=True)` 在 1.1.0 支持全两两组合校验（默认仍只查相邻对），多系列同图场景用 `all_pairs=True` 更严。

### 2.4 示意图（diagram）配色体系（1.2.0 新增）

**分类原则（本节是 1.2.0 的核心变更）**：配色按图类彻底分类，两套体系并列、互不影响——

| 图类 | 用途 | 配色体系 | 设计逻辑 |
|---|---|---|---|
| 数据图表（figure） | 折线/柱状/热力图/雷达等**数据系列对比** | §2 的 `PALETTES` 高饱和色板 | 高饱和、高对比，区分的是**数据系列** |
| 示意图（diagram） | 流程图/架构图/技术路线图/框架图等**结构表达** | 本节 `DIAGRAM_FAMILIES` 浅底色族 | 浅底色 + 同族深描边 + 实色标题条，表达的是**结构层级** |

示意图**禁止**再取数据色板做阶段/泳道/卡片着色（1.1.0 及之前"一个配色套全部"的用法废止）；数据图表也**不取**色族。中性色令牌（§2.2）两套体系继续共用。

7 族色值（每族 8 角色，色值 1:1 蒸馏自 sci-box 的 scibox-diagram 技能包（MIT 许可，风格参考其 roadmap-5band/stageflow/framework-3col 模板实测色），浅底色族为 sci-box 扁平风复刻）：

| 族 | fill 浅底 | stroke 描边 | accent 强调 | deep 深一档 | header 标题条 | header_stroke | edge 连接器 | chevron 旗标 |
|---|---|---|---|---|---|---|---|---|
| `blue` | #EEF6FD | #3B547F | #B6D8F6 | #A8C0EA | #4060B0 | #2C4488 | #1F3F6B | #98D0ED |
| `orange` | #FCEAD9 | #C08B5C | #FDDECD | #F8D0B0 | #D06818 | #A04E10 | #7B5530 | #F8D5B3 |
| `purple` | #E5DFEB | #9B979F | #CCC2DB | #C8C1D9 | #8D84A8 | #6E6584 | #7F5FAF | #C8C1D9 |
| `teal` | #DBEEF4 | #668D89 | #BAE2E4 | #A8E0E0 | #1F6F6F | #14504F | #5F8484 | #D4EAE4 |
| `green` | #E6F4DC | #6A9A4A | #C8E8B0 | #C8E8B0 | #3A5A22 | #2A4318 | #3A5A22 | #D8EEC8 |
| `olive` | #FBF3D2 | #B8A23A | #F6E6A4 | #F6E6A4 | #8A7A1A | #665A12 | #665A12 | #F6E6A4 |
| `grey` | #F2F4F6 | #8A97A3 | #DDE4EA | #D9D9D9 | #5B6B78 | #46535F | #5B6B78 | #E4E9EE |

角色语义：`fill`=内容盒浅底；`stroke`=内容盒描边（同族深一档）；`accent`=强调填充（子标题条/高亮盒）；`deep`=深一档内容填充；`header`=实色标题条底（配白字）；`header_stroke`=标题条描边；`edge`=连接器/箭头色（**跨族不混色**，一条连线只用一族）；`chevron`=旗标/徽章填充（浅底配墨黑加粗字）。

页面级令牌 `DIAGRAM_PAGE`：`bg` #F2EEF7（海报式页底，正文图一般不用）、`ink` #262626（示意图墨黑，全字加粗）、`title_bar` #4F80BD（通栏标题条）、`band_sep` #5B6B78（点线分带）、`frame` #808080、`loop_arrow` #CCCCD6、`white` #FFFFFF。

取色 API（`palettes.py`，模板脚本经 `figkit` 同名 `load_diagram_*` 转发，drawio 走 `drawio_builder`）：

```python
from palettes import get_diagram_family, get_diagram_families, get_diagram_page

fam = get_diagram_family("blue")            # 单族 8 角色字典
fams = get_diagram_families(n=4)            # DIAGRAM_ORDER_GENERIC 前 4 族（超长循环取）
fams = get_diagram_families(DIAGRAM_ORDER_ROADMAP, 5)   # 五带路线图族序
ink = get_diagram_page("ink")               # 页面令牌
```

固定族序：`DIAGRAM_ORDER_GENERIC = [blue, teal, olive, orange, purple, green, grey]`（通用 n 阶段取色）；`DIAGRAM_ORDER_ROADMAP = [blue, blue, orange, purple, teal]`（五带路线图，1:1 sci-box 叙事）。字体链 `DIAGRAM_FONT_FAMILY`：Microsoft YaHei（有真 700 粗体）→ SimHei → PingFang SC → Noto Sans SC（可变字体，matplotlib 只注册到 weight=100、加粗不可用，仅作末端兜底）→ Arial Unicode MS → Helvetica；示意图脚本在 `apply_style()` 后调 `figkit.use_diagram_font()`。**注意**：`use_diagram_font()` 修改**全局** rcParams，供独立出图脚本进程使用；同一进程后续要画数据图/其他图之前，必须重新 `apply_style()` 复位字体链，否则示意图字体链会泄漏到后续图。

连续型 colormap 约定（`CMAPS`, 同样在 `palettes.py`）:

| kind | cmap | 语义 |
|---|---|---|
| `sequential` | `viridis` | 数值梯度, 感知均匀且灰度友好 |
| `diverging` | `RdBu_r` | 双向对比（残差/灵敏度正负）, 中点对齐 0 |
| `correlation` | `RdBu_r` | 相关系数矩阵, -1 蓝 ~ +1 红 |
| `confusion_matrix` | `Blues` | 混淆矩阵, 计数越大越深 |
| `heatmap` | `viridis` | 通用热力图默认, 语义特殊时按上表换 |

---

## 3. 数据类型 → 配色方案

先按数据类型选"配色方式", 再按场景挑色板:

| 数据类型 | 配色方式 | 取值 |
|---|---|---|
| 分类（模型对比/方案对比/梯队） | 离散色板 | `academic_blue` / `okabe_ito`（≤6 序列用前者, 需色盲安全用后者） |
| 数值梯度（人口密度/得分/利用率） | 顺序 colormap | `viridis`（禁 jet/rainbow） |
| 双向对比（残差/相关系数/灵敏度正负） | 双向 colormap | `RdBu_r`, 中点必须是 0 或基准值 |
| 热力图（矩阵/转移概率） | 按语义 | 计数矩阵 `Blues`, 连续场 `viridis`, 正负语义 `RdBu_r` |
| 组内层级（同维度深浅） | 单色明度渐变 | 取主色系深→浅（如 cool_nature 的 REGION_COLOR 做法） |

## 4. 场景 → 色板推荐

| 场景 | 推荐色板 | 理由 |
|---|---|---|
| 中文竞赛（华数杯/妈妈杯/亚太杯）正文图 | `academic_blue` | 评委熟悉的高对比蓝橙, 白底黑字打印效果好 |
| 机理图/流程图, 追求期刊感 | `cool_nature` | 低饱和冷色 + 单强调色, Nature/IEEE 观感 |
| 评价对比类（多方法权重/排序/雷达） | `muted_earth` | 低饱和不刺眼, 多方法并列时区分度够 |
| MCM/ICM 英文赛, 或论文需灰度打印 | `okabe_ito` | 色盲安全 + 明度跨度大, 灰度下仍可区分 |
| 摘要页核心图 | 与正文同色板 | 摘要图必须与正文对应图**逐色一致** |

一篇论文只用一套主色板（全文绑定）, 特殊图（如色盲兜底）需在图表计划里写明原因。

### 选色决策流程（30 秒）

1. 这张图画完后要进正文还是只做诊断? → 诊断图用默认 `academic_blue` 快速出, 不纠结。
2. 数据是分类还是数值? → 分类走色板（§3 第 1 行）, 数值走 colormap（§3 第 2-4 行）。
3. 正文图属于哪个场景? → 查 §4 场景表定主色板, 写进图表计划的 `palette` 字段。
4. 序列数 >6? → 先减序列（分组/分面/合并）, 而不是找更大的色板。
5. 出图后跑 `grayscale_check` → 有警告的相邻对补线型/marker。
6. 换图检查: 这张图里的"本文模型"颜色, 是否与前面图里的一致? 不一致立即改。

### 语义绑定示例（规则 1 的落地写法）

| 语义 | 绑定色（academic_blue） | 说明 |
|---|---|---|
| 本文主模型/主方案 | `#1F4E79` 第 1 色 | 全文所有图的第一序列 |
| 对比基线/其他方案 | `#2E86AB` 第 2 色 | 次序列统一青蓝 |
| 关键阈值/强调点 | `#F18F01` 橙 | 每图最多一处 |
| 亏损区/风险区 | `#C73E1D` 红 | 只用于负面语义 |
| 盈利区/达标区 | `#3B8C6E` 绿 | 只用于正面语义 |
| 参考线/网格/无关序列 | `#6C757D` 灰 | 不参与数据叙事 |

---

## 5. 硬规则（终审逐条对照）

1. **同一语义绑定同一颜色**: 同一模型/方案/方法全文同色, 换图不换色; 摘要图与正文图逐色一致。
2. **每图 ≤1 个强调色**: 强调色（橙/红）只给关键结论那条线, 其余序列用主色系。
3. **禁用 jet/rainbow/高饱和荧光色**: 数值梯度一律 `viridis` 系。
4. **不用 matplotlib 默认 tableau 直出**: 出图前必须 `apply_palette()` 或加载 `mathmodel.mplstyle`。
5. **序列数 >6 时不再加色**: 改分组（groupby）、分面（facet）或合并低频类目, 色板最多 6-8 色。
6. **灰度校验**: 正文图配色须过 `grayscale_check(colors)`（相邻色亮度差 ≥0.15）; 不达标的相邻对必须配不同线型/marker/填充。
7. **图表背景纯白**: `figure.facecolor`/`axes.facecolor` 均为 white, 不用灰色底/透明底进正文。
8. **网格淡灰虚线**: `grid.alpha ≤0.3`, `linestyle='--'`, 网格在数据之下。
9. **中文字体必须走 mplstyle 回退链**: `Microsoft YaHei → SimHei → PingFang SC → Arial Unicode MS → Arial`, 禁止脚本里单写 `SimHei` 一种; `axes.unicode_minus=False`。
10. **语义色定向**: 红=风险/亏损/差, 绿=盈利/达标/好, 橙=强调/阈值; 不反转。
11. **色板外自定义色**必须写进图表计划（figure plan）的备注, 说明为什么四套色板都不适用。
12. **300dpi 起步**: 正文图 `savefig.dpi=300`, SVG/PDF 矢量优先。

---

## 6. 与工作流的挂接

| 环节 | 动作 |
|---|---|
| Stage 5（建模出图） | 生成任何图之前加载本文件; 图表计划的每张图记录 `palette` 字段 |
| Stage 8（写作配图） | 正文图按 §4 场景表选板; 图注中颜色词与实际颜色一致（"蓝线为本文模型"就必须是主色蓝） |
| Stage 9（终审） | 按 §5 硬规则逐条 QA; 特别查规则 1（跨图同色）与规则 6（灰度） |
| `figure-table-planner` | 规划输出中每张图带 `palette` 字段（八套之一，含 1.1.0 期刊板 npg/aaas/lancet/nejm；自定义色需备注原因） |
| `nature-figure` | 终审按本文件硬规则出问题清单 |
| `figure_skill_bridge.md` | 输出契约已含 `palette` 字段, 与本文件闭环 |

---

## 7. 模板脚本迁移状态（1.1.0 完成）

0.7.4 时 `templates/figures/scripts/templates/` 下 11 个模板与 4 件示意图各自硬编码颜色/样式（Times/Arial 混用、无中文 fallback），当时暂不改造以保持模板确定性输出。**1.1.0 已全部完成迁移**:

- **14 个既有模板全部接入 `figkit.py` 公共底座**：删除内联 `PALETTES_FALLBACK`；样式走 `apply_style()`、色板走 `load_palette()`、中性色走 `load_neutral()`、浅化走 `tint()/tint_series()`；数据图模板出图统一 `figkit.ygrid()`（仅 y 向网格）+ `save_fig()` 三格式导出；4 件示意图换 `wrap_text_balanced()` 均衡换行 + `elbow_arrow()` 正交连接器 + `soft_shadow()` 微阴影 + 中性色令牌。
- **迁移后 figqa 硬门 14/14 通过**（示意图盒内标签合法, 加 `--allow-box-labels` 豁免）；新增 7 件高级模板（roc-pr/taylor-diagram/raincloud/circular-heatmap/confusion-matrix/shap-summary/chord-diagram）与 6 件 drawio 可编辑模板走同一套 figkit/palettes 管线。
- 现在模板原始输出即可进正文（样式/色板已达标）；在工作区改写时保持 `apply_style()` + `load_palette('<选中色板>')` + `save_fig()` 三件套，不要退化为硬编码 hex。

---

## 8. 速查

一行取色:

```bash
python -c "import sys; sys.path.insert(0, r'<skill>/templates/figures/style'); from palettes import get_palette; print(get_palette('academic_blue'))"
```

标准用法（style + 色板 + 灰度校验三件套）:

```python
import sys
sys.path.insert(0, r'<skill>/templates/figures/style')
import matplotlib.pyplot as plt

plt.style.use(r'<skill>/templates/figures/style/mathmodel.mplstyle')  # 字体/字号/spines/网格

from palettes import apply_palette, grayscale_check, get_cmap
apply_palette('academic_blue')            # 或给单子图: apply_palette('cool_nature', ax=ax)
ok, warns = grayscale_check(get_palette('academic_blue'))
# warns 非空 → 给对应相邻序列补不同线型/marker, 不是换色板

ax.imshow(corr, cmap=get_cmap('correlation'), vmin=-1, vmax=1)  # 相关矩阵必配 vmin/vmax
```

纯取色（不依赖 matplotlib）: `from palettes import get_palette; colors = get_palette('muted_earth')`。

旧名兼容: `get_palette('champion_palette')` ≡ `get_palette('academic_blue')`。

自测: `python <skill>/templates/figures/style/palettes.py` 输出四套色板 + 灰度校验结果。

---

## 9. 导出与交付（0.7.5 新增）

### 字体嵌入设置（改稿不重渲染）

| 设置 | 值 | 效果 |
|---|---|---|
| `svg.fonttype` | `none` | SVG 里文字保留为文本, 不转路径; 改稿期改字号/措辞直接在编辑器里改, 不用重跑数据链 |
| `pdf.fonttype` | `42` | PDF 嵌入 TrueType 字体, 可复制可检索, 期刊/LaTeX 接受 |

两项 0.7.5 起已写入 `mathmodel.mplstyle`, 加载 mplstyle（模板脚本经由 `figkit.apply_style()`）即生效; 自定义脚本若绕过 mplstyle 出图, 必须手动补这两项, 否则改稿就要重渲染。

### 三格式一次导出

1.1.0 起模板统一走 `figkit.save_fig()`，一次导出 PNG+SVG+PDF 三格式、由同一渲染状态落盘、自动创建输出目录；PDF 由该函数**真正落盘**（不再只是文档承诺）。模板脚本内一行即可:

```python
from figkit import save_fig
save_fig(fig, "Fig_Q1")        # 默认 ("png", "svg", "pdf"), png 走 300dpi
# 或按需: save_fig(fig, "Fig_Q1", formats=("svg", "pdf"))
```

手写自定义脚本时可手动逐格式导出（效果等价，但必须都写）:

```python
fig.savefig('Fig_Q1.svg')          # 主文件: 可编辑
fig.savefig('Fig_Q1.pdf')          # LaTeX 嵌入
fig.savefig('Fig_Q1.png', dpi=300) # 存档 / Word 稿
```

一次导出的意义: 三份文件来自同一渲染状态, 不存在"SVG 改了 PNG 还是旧版"的漂移; 分次导出等于给改稿埋雷。

### 语义配色交付原则

- **绿 / 红仅保留给方向信号**: 增益/达标用绿（`#3B8C6E` 系）, 损失/风险用红（`#C73E1D` 系）, 与 §5 硬规则 10 一致; 没有"好坏"语义的序列一律不碰这两色。
- **中性数据用蓝灰橙**: 无方向含义的分类/梯度/对比序列, 在主色板的蓝、灰、橙里取（如 `academic_blue` 的 `#1F4E79 #2E86AB #F18F01 #6C757D`）。
- 交付前自检: 全文把红绿序列拉出来问一句"这序列有方向含义吗", 没有就换中性色。
