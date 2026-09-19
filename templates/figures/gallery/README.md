> **分发版说明**: 本分发包不含 `templates/figures/gallery/golden/` 下的 4 张实战成品图 (Q1_C1_field / Q2_C1_stages / Q34_C1_gridconv / Q4_C2_routes —— 真实项目交付物, 属非公开项目材料, 打包时按默认选择规则隔离, 原件留在源仓库)。下方表格中这 4 行在分发版没有对应文件; 需要视觉锚点时用同目录保留的 3 张 make_* 模板样张。

# Golden Gallery · 视觉回归基线（1.2.0）

本目录收录全部图表模板的**参考样图**，用途：

1. **视觉回归**：改动 `style/`（palettes.py / mathmodel.mplstyle）或 `figkit.py` 后，
   重新渲染同名模板并肉眼/像素对比本目录基线，防止审美悄悄退化。
2. **选型预览**：规划图表时先翻这里挑模板，再去 `scripts/render_*_pack.py --list` 查参数。

> 1.2.0 起配色分两类：**数据图**走高饱和数据色板（PALETTES），
> **示意图/流程图**走浅底色族（DIAGRAM_FAMILIES），见 `references/color_typology.md`。

## 数据图（23 件，PNG 基线；shap_summary / chord_diagram 依赖第三方库不入基线）

| 文件 | 模板 |
|---|---|
| make_convergence_curve.png | 算法收敛曲线 |
| make_correlation_heatmap.png | 相关性热力图 |
| make_multiscenario_robustness.png | 多场景稳健性 |
| make_optimization_allocation.png | 优化分配（堆叠/甘特） |
| make_pareto_front.png | Pareto 前沿 |
| make_prediction_fit.png | 预测拟合 + 残差 |
| make_radar_evaluation.png | 评价雷达图 |
| make_ranking_bar.png | 排序条形 + 贡献分解 |
| make_tornado_sensitivity.png | 灵敏度龙卷风图 |
| make_roc_pr.png | ROC + PR + 校准三面板 |
| make_taylor_diagram.png | 泰勒图 |
| make_raincloud.png | 云雨图 |
| make_circular_heatmap.png | 环形热图 |
| make_confusion_matrix.png | 混淆矩阵 |
| make_technical_route_flowchart.png | 多栏技术路线图（四阶段虚线容器版式，随 render_modeling_pack 分发） |
| make_field_contour.png | 物理场等值线 + 判据等值线（v3.0.0） |
| make_profile_family.png | 剖面族渐变着色（v3.0.0） |
| make_threshold_inversion.png | 阈值穿越反演 + 双边锁定 inset（v3.0.0） |
| make_convergence_sequence.png | 网格/步长收敛序列 + Richardson 外推（v3.0.0） |
| make_contrast_pair.png | 对照双联同坐标（v3.0.0） |
| make_route_on_field.png | 路径叠加场图（v3.0.0） |
| make_answer_grid.png | 结果交付数值网格（v3.0.0） |
| make_before_after.png | 前后对照双联（v3.0.0） |

## 示意图（4 件，matplotlib 版）

| 文件 | 模板 |
|---|---|
| make_diagram_framework_3col.png | 三栏研究框架 |
| make_diagram_module.png | 模块化功能框图 |
| make_diagram_roadmap.png | 五层技术路线图 |
| make_diagram_stageflow.png | 横向阶段流水线 |

## drawio 可编辑模板（7 件，.drawio 基线）

`make_drawio_{roadmap,framework,flow3col,stageflow,swimlane,mechanism,graphical_abstract}.drawio` —
用 draw.io 打开即可编辑；对应的重新生成命令见 `templates/figures/scripts/render_drawio_pack.py --list`。

## golden 样张（7 件，3.0.0 新增）

`templates/figures/gallery/golden/` 收录"图叙事纪律"的视觉锚点：**出图 agent 先看样张再画**，
新图达不到样张的证据密度与判据层就不该交。每张注明好在哪、对应哪条纪律
（纪律条文与设计卡五要素见 `references/figure_skill_bridge.md` 图叙事章）。

| 文件 | 好在哪（对应纪律） |
|---|---|
| Q1_C1_field.png | 场图+剖面对照三面板：时空云图 (a)(b) 带判据等值线（30/33 °C、含水率 1.8-2.4 虚线），(c) 沿半径的 T/C 剖面曲线并标注初值 C₀/T₀。**证据层 ≥2（数据层+判据层+对照层）、判据线纪律、量化标签** |
| Q2_C1_stages.png | 四面板阶段叙事：环境边界条件 (a) → 场分布 (b) → 时程演化 (c)(d)，逐面板推进干燥阶段；中心/表面双曲线对照 + 烘干判据 0.15 kg/kg 红虚线。**图叙事设计卡①"回答什么问题"逐面板落实、判据线纪律、对照式构图** |
| Q34_C1_gridconv.png | 收敛序列双面板：(a) 离散参数→判据量 t*(N) 双序列 + Richardson 外推线（外推值入图例）；(b) 收敛误差 log 轴 + 观测阶参考 p≈2.59/2.05 + 逐档误差数值。**判据线/参考线分层（红虚线判据、灰虚线参考）、量化标签、验证图范式** |
| Q4_C2_routes.png | 双路线对照：(a) 两序列同坐标比 Cmax(t)，判据 C*=0.15 红虚线 + 差异量化 Δt*=1.55 h (3.0%)；(b) 两路线 \|ΔC\| 剖面。**对照式构图优先（不画两张独立图）、判据线纪律、量化标签** |
| make_threshold_inversion.png | 新模板样张：阈值穿越反演。主曲线 + 判据红虚线 + 首次穿越点标注 + inset 双边锁定（穿越前后相邻两档夹住穿越点）。**答案图"可核验"三选二（数值+判据线+对照全占）、注释预算 ≤2** |
| make_answer_grid.png | 新模板样张：结果交付网格 16×4。行=样本、列=时刻，格内自适应黑白数值 + 0.5 居中发散色条。**结果交付范式（评委逐格可核验）、量化标签** |
| make_contrast_pair.png | 新模板样张：对照双联场图。同坐标同尺度 + 共享色标 + 差异判据 \|Δ\|>3 红虚线圈出。**对照式构图优先、判据线纪律** |

再生成：4 张 Q\*\_* 为 2026 国赛 A 题返工成品（人工核过版式，勿改）；3 张 make_\* 样张用
`python templates/figures/scripts/render_modeling_pack.py <id> --out <前缀>` 重渲染比对。

## 再生成方式

逐模板重渲染：`python templates/figures/scripts/render_modeling_pack.py <id> --out <前缀>`（示意图用
render_diagram_pack.py，drawio 用 render_drawio_pack.py，均在仓库根运行），比对 PNG 后覆盖基线。
