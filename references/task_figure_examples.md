# 任务组合范例（显式启用）

需要首轮正式图、共享 axes/色标/图例，或 A-F 场景时读本页。旧 `render_modeling_pack.py` 的 ID、CLI、返回值、输出路径和样式不变；新路由显式调用：

```powershell
python <skill>/templates/figures/scripts/render_task_examples.py --output <workspace>/examples_revision1
```

可用 `--cases D` 或 `--cases ACE` 只生成指定示例；目录必须不存在。输出 `index.html` 可直接打开，各例提供输入/结果 `input_and_results.npz`、`facts.json`、180 mm 宽的 PNG/SVG/PDF、来源哈希及 final_size_96dpi 浏览图。所有数据明确标为 synthetic，许可随仓库 LICENSE；不得当作赛题实测结果。

| 范例 | 输入与输出 | 适用与不适用 |
|---|---|---|
| A 调度 | 六个独立链式依赖任务的 duration_ms / start_ms / memory_mib；时间线、占用曲线、性能-资源散点 | 演示六案例覆盖、资源无重叠和物理时间。不是通用调度求解器，不含 SPILL、多资源、地址布局的真实求解 |
| B 通信 | 复数 channel；abs(H)^2/noise 得线性 SINR，EESM 后计算谱效 proxy；矩阵、拟合/残差 | beta 是示例参数；标签单位为 bit/s/Hz，不是 MCS/速率索引。不对无标签 Valid 报准确率，不代替真实标定 |
| C 重构 | 96x160 灰度图、uint8 mask(0/255)、中心线/多项式拟合；原图/答案/拟合/残差 | 独立 answer_mask.png 不缩放，显示像素和 mm 换算。不声称实例裂隙识别/JRC/连通真值已实现 |
| D 时空场 | x/y(m)、t0/t1(m/s)、支持掩码；两时刻同色标及剖面 | 合成局部笛卡尔坐标，时间和高度见 facts；缺测为空，不将网格步长称为观测分辨率。真实 GIS 须用 reader 保留 CRS |
| E 信号 | 2048 Hz、4096 点波形；Welch PSD、STFT；原文件 group_id | 窗/重叠/频率单位存事实文件，目标准确率 null。不是迁移分类器；禁止把窗口当独立原文件划分。mechanism 是真实特征处理路径示意，不是虚构神经网络 |
| F 空间评价 | 十个明确命名合成对象、三分量及权重、200 组权重扰动、示例路线 | 十对象全部展示，区间为权重敏感性范围而非统计置信区间；路线仅 Garden 01，未建遮挡/可视域模型，外部验证 null |

每例函数返回 `(figure, axes, arrays, facts)`，可以单独调用或拆面板，列表不是图型白名单。正式任务优先使用已有结果；改计算、单位或语义须回到分析层，不在绘图中偷偷重训。

## 组合 API

`templates/figures/scripts/figure_composition.py` 仅管理 `compose`（原生 mosaic）、`paper_style`（局部 rc_context）、`shared_legend`、`shared_colorbar`、`panel_labels` 和 `export_revision`。

轴级函数：`templates.make_field_contour.draw_field`、`templates.make_prediction_fit.draw_prediction_series`。它们不保存、不关闭外部 Figure、不设置全局样式。旧包装器继续校验并以旧路径导出。

Icarus `spectrum` / `network_graph` 直接接已有 ax，不改 vendor。共享色标必须同单位、cmap、归一化口径；助手拒绝不同定标，单位由分析结果与设计卡核对。

`export_revision` 保留准确毫米画布（不做 tight 裁边），只写新目录。全部格式成功后才产生 complete manifest；失败留 INCOMPLETE.json 及已写文件，调用方 Figure 保持打开。多文件并非原子事务。旧 `figkit.save_fig` 行为原样保留。

## 验收与采用

运行成功只得到候选，`visual_review=pending`。按 `figure_quality_layers.md` 检查真实渲染和最终版心；无视觉能力不得标通过。D 提供同一完整合成输入的新旧对照，含缺测的 D 主示例独立保留。最终排版比较须使用相同物理宽度，不能比较两张不同缩放的截图。
