# 深读域级索引（stage 3 消费入口）

- 用途：stage 3 选型时命中深读材料的索引入口——按题目域查到相关论文后，按 paper_id 定向读 `manual_paper_reviews.json` 对应条目，不做全文遍历。
- 来源：`competitions/huaweibei/papers/manual_paper_reviews.json` 全 33 篇（2021 届提名 12 篇 + 2025 届优秀选 21 篇，无抽样）；生成日期 2026-09-09。
- 域命名：与 `../playbooks/` 层一致（`../distilled_modeling.md` 八类风险 + 信号诊断）。
- 本索引不搬论文数值与原句；各篇报告的页码、表格编号均系论文声称。

## field_provenance 警示（引用前必读）

> v2.0.0 审计修正：template_guidance 字段为通用写作纪律模板（全 12 篇逐字相同），不得当作该篇论文的逐篇深读结论引用；figure_table_logic.role 原为机械轮转分配，除 caption_quality 标注与 v2.0.0 修正的两处错标外未逐图复核，引用时按弱证据处理。

- 2021 届 12 篇中不得当逐篇结论引用的字段：`modeling_body_by_q.{derivation_logic, solver_logic, result_interpretation}`、`transfer_boundary`、`figure_table_logic.{upstream_data, why_this_form, narrative_order, interpretation, claim}`；`figure_table_logic.role` 为弱证据。
- 2025 届 21 篇上述对应字段为逐篇人工复核，可引用；`figure_table_logic.{claim, upstream_data, why_this_form, narrative_order, interpretation}` 为空或仅作观察。
- 2025 届 21 条 award_level 一律为 excellent_paper_selection、star_status 一律为 not_locally_identified：来源仅为《2025年研究生数学建模竞赛优秀论文选》目录身份，本地无任何提名/等级证据，不推测。

## 锚点写法

- `papers[N]` 指 JSON `papers` 数组下标 N；`paper_id` 为稳定标识，与下标一一对应。
- 逐篇深读核心字段统一为：`papers[N].modeling_body_by_q[*].{motivation, input_output, model_chain, intermediate_outputs, transition}` + 顶层 `reusable_patterns` / `anti_patterns`（下表缩写 RP/AP）。
- 验证字段两届命名不同：2021 届为 `modeling_body_by_q[*].validation_link`，2025 届为 `modeling_body_by_q[*].validation`。
- `modeling_body_by_q` 数组按题序排列（无显式 question_id 字段），`[*]` 即 Q1..Qk，k 见各篇"锚点"列。

## 域分布总览

| 域 | 篇数 | papers 下标 |
|---|---|---|
| 计算与存储 | 2 | 0, 1 |
| 时空预测 | 2 | 2, 3 |
| 动力系统 | 2 | 4, 5 |
| 调度优化 | 6 | 10, 11, 12, 13, 14, 15 |
| 高维预测 | 5 | 6, 7, 16, 17, 18 |
| 多源融合 | 2 | 24, 25 |
| 空间几何 | 7 | 8, 9, 19, 20, 21, 22, 23 |
| 综合评价 | 4 | 29, 30, 31, 32 |
| 信号诊断 | 3 | 26, 27, 28 |

全部 33 篇均落到固定域，无域待定篇目。

## 逐篇索引

| # | paper_id | 域 | 核心建模动作（一句话） | JSON 锚点 |
|---|---|---|---|---|
| 0 | graduate:paper:2021-A:4a4c708f7451 | 计算与存储 | 矩阵间相关阈值决定是否复用正交基，随机正交基截断 SVD + SOR 迭代替代直接求逆；存储上 SVD 低秩与压缩感知双路线按资源场景取舍 | papers[0].modeling_body_by_q[*]（Q1-Q3）；RP/AP |
| 1 | graduate:paper:2021-A:00026fb2a520 | 计算与存储 | 成本剖析锁定支配算子后用幂法热启动降阶求第二特征向量；按行重组大矩阵 SVD 主成分压缩，压缩结果直接服务计算 | papers[1].modeling_body_by_q[*]（Q1-Q3）；RP/AP |
| 2 | graduate:paper:2021-B:a983f1940341 | 时空预测 | IAQI 规则基线后：SVD/Spearman 筛选 + 两步聚类分天气型，逐污染物选模型（CEEMDAN+SVR / LSTM / Lasso 组合），GRU-GCN 引入邻站空间协同并逐污染物报告正负增益 | papers[2].modeling_body_by_q[*]（Q1-Q4）；RP/AP |
| 3 | graduate:paper:2021-B:9d938d0e4179 | 时空预测 | Fuzzy-BLS 通用基线 + 残差诊断后用时变 Lotka-Volterra 机理层修正难预测污染物；邻站协同显式使用风向坐标与距离权重 | papers[3].modeling_body_by_q[*]（Q1-Q4）；RP/AP |
| 4 | graduate:paper:2021-C:81d879f048b1 | 动力系统 | H-H 单元—突触网络—健康/病态对照—干预优化四层级：差异指标直接成为后问损失，粗扫+变步长搜索刺激波形与靶点 | papers[4].modeling_body_by_q[*]（Q1-Q5）；RP/AP |
| 5 | graduate:paper:2021-C:46e34e5c1a24 | 动力系统 | 直流/交流/噪声分岔区间刻画 + SVM 把复杂波形压缩为可验证状态分类作刺激有效性判据，FPGA 与数值仿真互证 | papers[5].modeling_body_by_q[*]（Q1-Q5）；RP/AP |
| 6 | graduate:paper:2021-D:f2ebfff348d4 | 高维预测 | 漏斗式特征筛选（方差→相关去冗余→多法集成排序）；Borderline-SMOTE + 原型网络逐项 ADMET；代理模型 + 专家初始化 PSO 混合整数搜描述符区间 | papers[6].modeling_body_by_q[*]（Q1-Q4）；RP/AP |
| 7 | graduate:paper:2021-D:7b24dd86646c | 高维预测 | 多类重要性加权融合后独立筛选；多回归器统一指标矩阵横评；多个 MLP 代理 + 差分进化搜综合优描述符区域 | papers[7].modeling_body_by_q[*]（Q1-Q4）；RP/AP |
| 8 | graduate:paper:2021-E:c05b8131f46d | 空间几何 | 解析最小二乘给初值、ELM/BP 只做残差修正；锚点组合+残差加权抑制异常测距；RF 用同源残差特征做干扰分类再分流定位器（见注 1） | papers[8].modeling_body_by_q[*]（Q1-Q5）；RP/AP |
| 9 | graduate:paper:2021-E:3a20e5cc482d | 空间几何 | 把物理几何损失编码进 MLP（LS-MLP 即可微优化器），多初值预测用聚类/置信度聚合；场景迁移只替换锚点物理参数；卡尔曼滤波收动态轨迹（见注 1） | papers[9].modeling_body_by_q[*]（Q1-Q5）；RP/AP |
| 10 | graduate:paper:2021-F:8da8ff7c36fa | 调度优化 | 0-1 ILP 航段分配（回路按连接时间编组）→ 扩展 ILP 加执勤规则/成本/公平 → 任务环 0-1 乘积线性化 + 虚拟人员决策；航段—执勤—任务环三层对象，小规模与精确最优对齐 | papers[10].modeling_body_by_q[*]（Q1-Q3）；validation_link；RP/AP |
| 11 | graduate:paper:2021-F:eeeffef378bb | 调度优化 | 可换航班/任务环连接规则预计算为稀疏矩阵，覆盖/乘机/替补加权目标 + 时序优先启发式；公平用最大偏差（min-max）线性化 | papers[11].modeling_body_by_q[*]（Q1-Q3）；validation_link；RP/AP |
| 12 | graduate:paper:2025-A:eb15efe91f40 | 调度优化 | 先建 ILP/MIP 再因决策变量规模显式降级：拓扑合法邻域的 SA（Q1）、Chaitin 图着色 + 分层求解 + ILP+Rounding（Q2）、继承约束 MILP + 同 Pipe 序与搬运量约束 + 三策略（Q3）；结果恶化逐算例归因 | papers[12].modeling_body_by_q[*]（Q1-Q3）；validation；RP/AP |
| 13 | graduate:paper:2025-A:d26284fb65c7 | 调度优化 | 优先规则贪心 + 禁忌搜索（Q1）；ABQPSO 四段编码 [seq\|alloc\|spill\|offset] + 约束违反度与修复算子分层编号一一对应（Q2）；DPEA 双种群 Pareto（Q3）；事件驱动扫描线查非重叠约束 | papers[13].modeling_body_by_q[*]（Q1-Q3）；validation；RP/AP |
| 14 | graduate:paper:2025-A:becbc09c579f | 调度优化 | 关键路径 DP + 三分量优先级（L0 自动机/内存压力/关键路径）贪心（Q1）；自适应 first-fit + victim 显式建模为带权集合覆盖并给贪心近似比（Q2）；执行时间模型 + 三策略闭环模拟 DOSA（Q3）；约束编号法典 + 每算法配定理证明 | papers[14].modeling_body_by_q[*]（Q1-Q3）；validation；RP/AP |
| 15 | graduate:paper:2025-A:186cc0cdae39 | 调度优化 | 多贪心 × SA/TS/GA 横评后主动提交简单贪心并写明理由（Q1）；GP 把缓存分配/victim 策略演化为可读规则树、按算子类别独立训练（Q2）；NSGA-II（编码含规则树子树交叉）vs MOPSO（Q3） | papers[15].modeling_body_by_q[*]（Q1-Q3）；validation；RP/AP |
| 16 | graduate:paper:2025-B:150cea22b1aa | 高维预测 | EESM 物理基线 + 六类改进模型共享"聚合器+单调映射头"骨架横评；TxBF 迁移只换特征层（SVD 主奇异值）加分布对齐（中位平移/IQR 缩放），无标签域用分布一致性评估 | papers[16].modeling_body_by_q[*]（Q1-Q3）；validation；RP/AP |
| 17 | graduate:paper:2025-B:29ae1e65a24d | 高维预测 | 时间同步 IQR 剔除 + 从符号错误概率/Chernoff 界重构指数映射给 EESM 物理推导；TxBF 主奇异值占比同一物理量在注意力权重与特征三处复用 | papers[17].modeling_body_by_q[*]（Q1-Q3）；validation；RP/AP |
| 18 | graduate:paper:2025-B:31f63f2fc4de | 高维预测 | Isotonic 物理基线 + HGBR 残差学习 + 闭式最小二乘融合；GroupKFold 按终端分组防泄漏、折内校准、OOF 求融合权重；岭化凸融合退化被诚实论证 | papers[18].modeling_body_by_q[*]（Q1-Q3）；validation；RP/AP |
| 19 | graduate:paper:2025-C:40a3c73c0409 | 空间几何 | CLAHE+双边滤波 + ResNet50-ASPP-注意力 U-Net 分割；细化中心线 + LM/RANSAC/Huber-IRLS 拟合正弦四参；连通概率加权指数模型 + AHP/投影寻踪-GA 双轨打分补钻 | papers[19].modeling_body_by_q[*]（Q1-Q4）；validation；RP/AP |
| 20 | graduate:paper:2025-C:f3f0fc9a1a7f | 空间几何 | 光照分解矫正 + Gabor 方向增强，K-Means/Canny/YOLOv8 三方案；梯度下降-牛顿混合 vs 线性网络双优化器赛马 + R2 裁决；体素信息熵 + 信息增益补钻闭环 | papers[20].modeling_body_by_q[*]（Q1-Q4）；validation；RP/AP |
| 21 | graduate:paper:2025-C:dde3aad6c5f6 | 空间几何 | 多种传统检测法逐个红框展示成功/失效后加权投票；DBSCAN+RANSAC vs 滑窗 Hough 双模型多指标 + 显著性 p 值裁决；傅里叶主轮廓+DWT 细节分层表征 + Bootstrap 置信区间；乘积连通模型 + DFS + 序贯贪心补钻 | papers[21].modeling_body_by_q[*]（Q1-Q4）；validation；RP/AP |
| 22 | graduate:paper:2025-C:eaf6375148b2 | 空间几何 | 光照归一化 + Frangi 管状滤波（完整记录 ML 失败与数据泄露发现后转向传统方法）；闭运算连接 + 质心 DBSCAN"先聚合后提纯"；蒙特卡洛法向量抽样做不确定性传递 | papers[22].modeling_body_by_q[*]（Q1-Q4）；validation；RP/AP |
| 23 | graduate:paper:2025-C:a69f6c1c55ae | 空间几何 | FFT 频谱诊断驱动的带阻去噪 + DeepLabV3+外部公开集迁移；迭代式模型驱动聚类（最大碎片拟合假设模型→MAE 阈值吸收碎片→重拟合）；JRC 用巴顿标准轮廓做外部真值基准；三因子连通 + 图论 DFS + 序贯补钻 | papers[23].modeling_body_by_q[*]（Q1-Q4）；validation；RP/AP |
| 24 | graduate:paper:2025-D:ac2d33da18fa | 多源融合 | 双资料基准模型 a 标定单资料模型 b（每问内置参照系）；VAD 反演 + X/S 波段加权背景场 + 最优插值 OI 融合三维场；NWP 诊断 A* 与观测外推 LSTM+聚类降维蚁群两套航路（见注 3） | papers[24].modeling_body_by_q[*]（Q1-Q3）；validation；RP/AP |
| 25 | graduate:paper:2025-D:95743f6ef8d6 | 多源融合 | 位温/Ri/TKE 合成指标 a 标定 b（多种回归器 Train/Test 横评并指认过拟合者）；变分融合（观测+背景+平滑项）+ 卡尔曼外推 + 误差传播置信度场；分层二次标定诊断场 + A* 风险厌恶改进 + 鲁棒机会约束 | papers[25].modeling_body_by_q[*]（Q1-Q3）；validation；RP/AP |
| 26 | graduate:paper:2025-E:e86c6a47cc19 | 信号诊断 | 采样率/传感器端/测点位每个"选哪个"都配统计量（奈奎斯特+特征频率、MMD、包络谱残差 SNR）；四路特征筛选取交集；改进 CDA+IJDA+DDM+I-Softmax 迁移，逐样本用故障机理频谱人工复核 | papers[26].modeling_body_by_q[*]（Q1-Q4）；validation；RP/AP |
| 27 | graduate:paper:2025-E:fd49424d2937 | 信号诊断 | TVFEMD-WESK 与 GWO-MOMEDA 两阶段去噪（中间失败状态如实呈现强化方法必要性）；手工特征 MixHop 图融合；ViT 骨干 + MMD/CORAL 联合对齐 + 动态调度；质心-方差对齐审计做可解释性 | papers[27].modeling_body_by_q[*]（Q1-Q4）；validation；RP/AP |
| 28 | graduate:paper:2025-E:b4f1d4ea6551 | 信号诊断 | 质量加权滑窗筛选保留低分样本防分布窄化；手工特征 + ViT 深度特征融合；DANN+MMD+伪标签三阶段训练；无标签评估用消融表+内聚/匹配无监督指标+物理机理三重防线；可解释性指标对照表 | papers[28].modeling_body_by_q[*]（Q1-Q4）；validation；RP/AP |
| 29 | graduate:paper:2025-F:77892f7dcdfe | 综合评价 | Voronoi 路径骨架 + 射线视景矩阵，"移步异景"拆成马尔科夫时间维（小概率转移=意外）+ 汉明空间维；景观生态学+空间句法双阈值表量化开合；三模态高维相似度 + 近园全流程泛化 | papers[29].modeling_body_by_q[*]（Q1-Q3）；validation；RP/AP |
| 30 | graduate:paper:2025-F:20b9a3fbb48f | 综合评价 | 边界配对中轴线 + 扇形视域 + 元素类型加权异景；Shannon 熵 + 倒 V 型适宜性函数（过简过繁都扣分）；三重相似度 + Ward 聚类 + 扩展美学 + 三园外部验证 | papers[30].modeling_body_by_q[*]（Q1-Q3）；validation；RP/AP |
| 31 | graduate:paper:2025-F:b18c1289e4f1 | 综合评价 | 离散曲率弯曲能量 + FoV 景观向量余弦异景 + IGA 多目标（DFS 随机游走初始化保证连通、多策略变异带寻路修复）；AHP+CRITIC 组合赋权；MKL 融合核 + 度量学习 + 持久同调/HMM 集成相似度（深度模块公式陈列无落地被深读点名） | papers[31].modeling_body_by_q[*]（Q1-Q3）；validation；RP/AP |
| 32 | graduate:paper:2025-F:861c3d805408 | 综合评价 | 植物通行/视域双圆盘分离建模；异景度量防作弊链条（JS 距离→除段长→温和权重→归一）；GMM-MRF 空间约束聚类 + 分位数标定（寄畅园基准）；α 数据驱动定参 + 鹤园外部验证 | papers[32].modeling_body_by_q[*]（Q1-Q3）；validation；RP/AP |

## 边界注记

1. papers[8]/papers[9]（2021_E UWB 定位）主轴是几何定位（最小二乘+残差修正），其中干扰识别子任务（残差特征分类分流）形态接近信号诊断；按主建模动作归空间几何，信号诊断工作可回查其 Q4/Q5。
2. papers[6]/papers[7]（2021_D 药物）Q4 均为"代理模型 + 演化搜索描述符区间"，形态接近调度优化中的代理加速，但主轴是高维特征筛选与预测，归高维预测。
3. papers[24]/papers[25]（2025_D）Q3 含 A*/蚁群航路规划（类调度动作），主轴是多源融合监测，归多源融合；调度域 playbook 不收这两篇。
4. papers[10]–papers[15]（调度域 6 篇）的逐篇动作提取与跨篇观察见 `analysis/playbook_extract/scheduling_actions_raw.md`，消费入口为 `../playbooks/scheduling_optimization.md`。
