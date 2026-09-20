# 多类型图与备选图库

触发：结果已具备可解释内容，需要匹配图型、构造综合图或查看未入文候选。已有设计卡、配色、图内文字与质检规则继续归 `references/figure_skill_bridge.md`；此处只定义按数据类型路由及备选图库生命周期。

## 数据类型决定图型

| 证据 | 展示方式 | 必须保留 |
|---|---|---|
| 统计结果、误差、对照 | 现有 matplotlib 数据图模板 | 样本量、单位、指标口径、适当的不确定性 |
| 视频 | 真实帧序列 + 对应时间曲线 | 每帧原始帧号/时间、同一裁剪与颜色口径 |
| 音频 | 波形 + 频谱或语谱 | 采样率、声道、窗长/重叠、频率和时间单位 |
| 遥感、地图 | rasterio 读图后结合地图绘制 | CRS、分辨率、nodata、波段、色标、合法来源 |
| 点云 | Open3D 或现有 3D 库的正交视图/剖面 | 坐标尺度、视角、采样比例、颜色含义 |
| 科学多维数组 | 物理坐标剖面、切片、等值面 | 变量、单位、切片坐标、维度顺序 |
| 算法内部结构 | 现有 drawio framework/flow 模板 | 真正实现的张量尺寸、分支、输入输出与训练/推理区别 |
| 工程物理机理 | 现有 drawio mechanism 或几何绘图 | 坐标、边界条件、物理量、作用方向及比例是否示意 |
| 逐问综合图 | 有论证关系的多面板组合 | 每个 panel 的独立证据贡献、来源与共享坐标/色标口径 |

每问考虑是否值得有一张主要综合图；已有答案图足够、证据不适合合并或版面不足时不增加。严禁用固定张数、装饰面板或未实现的网络结构充实页面。

## 结果发现与停止条件

在每问验证完成、稳健性完成、写作前各检查一次已有结果：误差在哪里集中、哪种方法失效、敏感性是否反转、是否存在代表性场景。先登记候选及其独立价值，再选择生成；没有新结果或预算耗尽就停止，不持续递归挖图，不新造数据。

默认一批图库最多 12 张，可在清单 `max_items` 调整；这是浏览和生成预算，不是论文图量目标。优先复用已验证图片，确有新证据才调用图表桥生成。正式出图沿用 D.1 的已授权范围；原诊断图必须重新完成正式设计卡、冻结与质检才能转为候选。

## 文件契约与浏览

`figure-candidates-1` 清单含 `max_items` 和 `figures`。每项字段：

- `figure_id / question / claim / caption`：标识、子问、独立主张、题注。
- `status`：`candidate / paper / appendix / diagnostic / rejected`；`qa` 为真实质检结果 `passed` 才入图库。
- `source / preview`：各为 `{path, sha256}`，路径相对清单；source 指上游结果，preview 是已渲染位图。
- `originals`：原图/可编辑文件列表，每个含 `{path, sha256}`。
- `width_mm / parameters`：实际入文宽度与处理参数（可以为空对象表示无变换）。

```bash
python <skill>/scripts/build_result_gallery.py results/Q1_figure_candidates.json --output figures/gallery_v1
```

工具生成本地 `index.html`、真实缩略图、原图副本和带说明的 `manifest.json`，可直接打开，不需要服务。原图检查独立于预览：展示栅格按入文宽度计算有效分辨率；SVG/PDF 检查实际内容，混合位图不自动认作纯矢量。v1 要求至少一个原图通过检查，低清预览不否决合格原图；哈希不符拒绝。机器检查不代替语义与视觉质检。

## 显式 v2 浏览

需要查看诊断或待审图时用 `figure-candidates-2`，其余字段沿用 v1，status 改为 diagnostic/candidate/reviewed/adopted/rejected，destination 单独记录（未知为 unknown）。结果 schema 为 gallery-2。

诊断/未审/低清原图可以浏览，但 delivery_status=not_verified，不能自动晋升。reviewed/adopted 仍需 qa=passed 且原图检查通过；工具不改变用户输入状态。rejected 记录 reason、来源和排除状态。max_items 仍是单批浏览预算，超出要求另开批次，不截断题面必交覆盖。

v2 的过期/缺失来源列入排除原因，不用旧图冒充新结果。原 mask 可声明 `object=mask, destination=answer_attachment, native={size:[width,height], mode:"L", values:[0,255]}`；检查原尺寸、模式和声明编码，不套展示 dpi，也不重采样。native 必须来自题面/源文件，哈希与人工科学检查仍不可省略。

图库是备选证据，不自动修改论文或 state；正文只选有独立贡献的图，随后按既有生成输出契约和证据台账登记。输入清单或来源更新后生成新版本，旧图库不能作为最新结果。
