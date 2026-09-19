# Vendor 第三方 Skill 收编说明（1.4.0 建立, v2.3.0 增补 icarus-figures）

本目录收录上游开源 skill / 项目的副本，供 mathmodel-studio
图表工作流直接调用，使 skill 自包含、不依赖兄弟目录安装。

> **分发口径（2026-09-19 修正）**：公开仓库与公开分发包里**只有 MIT 的两份**——
> `diagram-design/` 与 `icarus-figures/`。`scibox-diagram/` 与 `scibox-figure/`
> 上游未附正式 LICENSE，**未随公开仓库与分发包分发**（仅维护方本地工作副本可能保留），
> 在公开/克隆环境里**不是可用本地路径**；公开路由见 `references/figure_skill_bridge.md`
> "开源分发版注意" 与包内 VENDOR_NOTICES.md（若存在）。本文件对这两者的"内容/能力"
> 描述只作上游参考说明，不表示本分发包内含该目录。

> 准确性说明（v2.0.0 修正）：diagram-design 为上游原样副本；scibox-diagram / scibox-figure
> 的内容与上游一致，但 frontmatter 的 `name` 字段在本机沙箱环境中曾被改写
>（scibox-figure 为 `mathmodel-figure-templates`），即并非上游仓库的逐字节原样形态。
> 上游更新时以官方仓库为准整目录替换。

## 收编清单

| 目录 | 上游 | 许可证 | 内容 |
|---|---|---|---|
| `scibox-diagram/` | [jihe520/sci-box](https://github.com/jihe520/sci-box) `skills/scibox-diagram` | ⚠️ 上游仓库未附 LICENSE 文件（README 宣称开源；Tabler 图标为 MIT，见该目录 ATTRIBUTION.md）—— **未获明确许可证，不随公开仓库与分发包分发** | 论文示意图 drawio 模板 4 件（五带路线图/三栏框架/三栏阶段流程/横版任务流水线）+ 从零手写与高保真复刻纪律 + check_layout.py 体检 + 100 个 Tabler 图标 |
| `scibox-figure/` | 同上 `skills/scibox-figure` | 同上 ⚠️ —— **未获明确许可证，不随公开仓库与分发包分发** | 科研绘图复刻模板 11 件（cv_roc_ci / paired_raincloud / taylor / chord / circular_heatmap / tpe_surface 等） |
| `diagram-design/` | [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) `skills/diagram-design` v2.6 | MIT（见该目录 LICENSE.upstream 与 THIRD_PARTY_LICENSES.md） | 39 类编辑级 HTML/SVG 图表设计系统（答辩/展示/网页场景） |
| `icarus-figures/` | [TAO-QKV/Icarus-Figures](https://github.com/TAO-QKV/Icarus-Figures) `main @ 0bcaa40c07ef`（2026-06-30, codeload tarball 全仓库原样收编） | MIT（LICENSE 原样随附, © 2026 TAO-QKV） | 出版级科研图表 skill 全仓库: `paperfig` 包（`paper_style` 预设 + 48 个可调用图函数）+ `.claude/skills/icarus-figures/` 下 SKILL.md 与 figure-cookbook / figure-critique / framework-figures / caption-and-quality 四参考 + `scripts/critique.py` 可运行质量门 + `examples/hero_tikz/` 5 个可编译 TikZ 框架图范例 + 复杂多面板 examples 图库 |

## 使用纪律

1. **不改写 vendor 内的文件**——上游更新时整目录替换；本地定制请放到
   vendor 之外（本 skill 自己的模板在 `templates/figures/scripts/`）。
2. scibox-diagram 的 drawio 模板以 content JSON 驱动，详见其 SKILL.md；
   我们的 `templates/figures/scripts/drawio/` 7 件轻量模板继续作为
   "快速出小图"路径（公开路由默认即此路径；scibox-diagram 未随公开包分发，
   本地完整副本存在时两者并存，路由规则见 `references/figure_skill_bridge.md`）。
3. scibox-figure 与本 skill 25 件数据图模板有部分图型重叠
   （chord/circular_heatmap/taylor 等）：默认用本 skill 模板（统一色板/门禁），
   需要"照着参考图复刻"或我们的模板没有的图型（tpe_surface、marginal_grid、
   cv_roc_ci 等）时，从上游自行获取 scibox-figure（未随公开包分发）。
4. diagram-design 产出 HTML/SVG，面向答辩 PPT/网页/海报，不进 LaTeX 正文。
5. 许可证注意：sci-box 上游仓库未附正式 LICENSE 文件，**仅"保留 ATTRIBUTION/署名"
   不构成上游授权，也不满足再分发条件**。因此 scibox-diagram 与 scibox-figure
   **不随公开仓库与公开分发包分发**（本仓库已按此执行：二者在 .gitignore 与
   打包排除清单内；公开路由改走自写模板与 MIT vendor，见
   `references/figure_skill_bridge.md`）。本地自用副本不受影响；若将来上游补发
   明确许可证，再按其条款评估是否纳入分发（mathmodel 自身代码与 1.2.0/1.3.0
   的色族/纪律均为蒸馏自写，不受影响）。
6. icarus-figures 路由（v2.3.0, 详见 `references/figure_skill_bridge.md`）:
   复杂多面板论文主图（hero panel + insets）/ 物理场·动力学图（等高线/流场/相图/
   轨迹/频谱）/ 网络与集合流图（桑基/弦图/网络）需要时走它；TikZ 框架图/
   技术路线图需与正文同源 LaTeX 编译时走其 `examples/hero_tikz/` 范例。
   使用约束: ① journal 列宽预设（nature 89mm 等）不用于竞赛版式——竞赛论文
   A4 全宽, `paper_style()` 不传 `journal` 参数; ② 色板默认用其自带
   colorblind-safe 预设, 若对齐本 skill 色族须符合 `references/color_typology.md`;
   ③ 产物写到用户 cwd 的 `figures/`, 不把论文引用指向 vendor 内部路径;
   ④ icarus 路由的图两道门都过——上游 `scripts/critique.py` 质量门 +
   本 skill `figqa.py --strict` / `figure_lint.py`; ⑤ 常规单件统计图仍优先
   自写 25 件模板（统一色板 + 确定性脚本）, icarus 只接自写库没有的能力。
