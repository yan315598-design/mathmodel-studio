# Vendor 第三方 Skill 收编说明（1.4.0 建立, v2.3.0 增补 icarus-figures）

本目录内嵌四个上游开源 skill / 项目的副本，供 mathmodel-studio
图表工作流直接调用，使 skill 自包含、不依赖兄弟目录安装。

> 准确性说明（v2.0.0 修正）：diagram-design 为上游原样副本；scibox-diagram / scibox-figure
> 的内容与上游一致，但 frontmatter 的 `name` 字段在本机沙箱环境中曾被改写
>（scibox-figure 为 `mathmodel-figure-templates`），即并非上游仓库的逐字节原样形态。
> 上游更新时以官方仓库为准整目录替换。

## 收编清单

| 目录 | 上游 | 许可证 | 内容 |
|---|---|---|---|
| `scibox-diagram/` | [jihe520/sci-box](https://github.com/jihe520/sci-box) `skills/scibox-diagram` | ⚠️ 上游仓库未附 LICENSE 文件（README 宣称开源；Tabler 图标为 MIT，见该目录 ATTRIBUTION.md） | 论文示意图 drawio 模板 4 件（五带路线图/三栏框架/三栏阶段流程/横版任务流水线）+ 从零手写与高保真复刻纪律 + check_layout.py 体检 + 100 个 Tabler 图标 |
| `scibox-figure/` | 同上 `skills/scibox-figure` | 同上 ⚠️ | 科研绘图复刻模板 11 件（cv_roc_ci / paired_raincloud / taylor / chord / circular_heatmap / tpe_surface 等） |
| `diagram-design/` | [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) `skills/diagram-design` v2.6 | MIT（见该目录 LICENSE.upstream 与 THIRD_PARTY_LICENSES.md） | 39 类编辑级 HTML/SVG 图表设计系统（答辩/展示/网页场景） |
| `icarus-figures/` | [TAO-QKV/Icarus-Figures](https://github.com/TAO-QKV/Icarus-Figures) `main @ 0bcaa40c07ef`（2026-06-30, codeload tarball 全仓库原样收编） | MIT（LICENSE 原样随附, © 2026 TAO-QKV） | 出版级科研图表 skill 全仓库: `paperfig` 包（`paper_style` 预设 + 48 个可调用图函数）+ `.claude/skills/icarus-figures/` 下 SKILL.md 与 figure-cookbook / figure-critique / framework-figures / caption-and-quality 四参考 + `scripts/critique.py` 可运行质量门 + `examples/hero_tikz/` 5 个可编译 TikZ 框架图范例 + 复杂多面板 examples 图库 |

## 使用纪律

1. **不改写 vendor 内的文件**——上游更新时整目录替换；本地定制请放到
   vendor 之外（本 skill 自己的模板在 `templates/figures/scripts/`）。
2. scibox-diagram 的 drawio 模板以 content JSON 驱动，详见其 SKILL.md；
   我们的 `templates/figures/scripts/drawio/` 6 件轻量模板继续作为
   "快速出小图"路径，两者并存（路由规则见 `references/figure_skill_bridge.md`）。
3. scibox-figure 与本 skill 17 件数据图模板有部分图型重叠
   （chord/circular_heatmap/taylor 等）：默认用本 skill 模板（统一色板/门禁），
   需要"照着参考图复刻"或我们的模板没有的图型（tpe_surface、marginal_grid、
   cv_roc_ci 等）时走 scibox-figure。
4. diagram-design 产出 HTML/SVG，面向答辩 PPT/网页/海报，不进 LaTeX 正文。
5. 许可证注意：sci-box 上游仓库未附正式 LICENSE 文件。本 skill 分发自用时
   保留 ATTRIBUTION 即可；若要再分发 mathmodel-studio（插件市场等公开渠道），
   请先确认上游补发许可证，或将 scibox-* 两个目录移出分发包（mathmodel
   自身代码不受影响——1.2.0/1.3.0 的色族与纪律均为蒸馏自写）。
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
   自写 17 件模板（统一色板 + 确定性脚本）, icarus 只接自写库没有的能力。
