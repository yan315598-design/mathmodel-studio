# Golden Gallery · 视觉回归基线（v7.8.0）

本目录收录全部图表模板的**参考样图**，用途：

1. **视觉回归**：改动 `style/`（palettes.py / mathmodel.mplstyle）或 `figkit.py` 后，
   重新渲染同名模板并肉眼/像素对比本目录基线，防止审美悄悄退化。
2. **选型预览**：规划图表时先翻这里挑模板，再去 `scripts/render_*_pack.py --list` 查参数。

> v7.8.0 起配色分两类：**数据图**走高饱和数据色板（PALETTES），
> **示意图/流程图**走浅底色族（DIAGRAM_FAMILIES），见 `references/color_typology.md`。

## 数据图（14 件，PNG 基线；shap_summary / chord_diagram 依赖第三方库不入基线）

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

## 示意图（5 件，matplotlib 版）

| 文件 | 模板 |
|---|---|
| make_technical_route_flowchart.png | 多栏技术路线图（四阶段虚线容器版式） |
| make_diagram_framework_3col.png | 三栏研究框架 |
| make_diagram_module.png | 模块化功能框图 |
| make_diagram_roadmap.png | 五层技术路线图 |
| make_diagram_stageflow.png | 横向阶段流水线 |

## drawio 可编辑模板（6 件，.drawio 基线）

`make_drawio_{roadmap,framework,flow3col,stageflow,swimlane,mechanism}.drawio` —
用 draw.io 打开即可编辑；对应的重新生成命令见 `scripts/render_drawio_pack.py --list`。

## 再生成方式

逐模板重渲染：`python scripts/render_modeling_pack.py <id> --out <前缀>`（示意图用
render_diagram_pack.py，drawio 用 render_drawio_pack.py），比对 PNG 后覆盖基线。
