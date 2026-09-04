# 研究生数学建模竞赛 2021—2025 全 30 题人工深度复核

> 证据范围：30 道题面、190 篇本地优秀论文全文证据包；2021 年 12 篇数模之星提名由目录确认。以下只迁移结构与逻辑，不迁移历史数值或原句。

> **v2.0.0 清理说明**：逐问证据行已重新生成——移除 47 个 OCR 噪声证据键（如 Q三四、Q一60、Q0、Q20）；27 题的逐问绑定无鉴别力（各问映射同一论文集合），已明确标注"题级绑定"，只有 2021B / 2023E / 2025B 三题为逐问级绑定。


## 2021A｜相关矩阵组的低复杂度计算和存储建模

- 范式：矩阵近似计算、压缩与复杂度约束优化
- 证据：题面 `graduate:problem_statement:2021-A:a3037b7258dd`；论文 7 篇；提名论文 2 篇。
- 问题本质：在精度阈值约束下，利用矩阵间相关性、低秩和稀疏结构，重构从 H 到 V、W 的计算与存储流程，并给出可复算的运算量账本。

### 逐问依赖

- Q1 先识别相关结构并分别压缩 SVD、求逆和矩阵乘法开销
- Q2 复用相关性和低秩结论设计 H、W 的压缩解压及误差控制
- Q3 联合 Q1 与 Q2，消除重复变换，形成端到端精度—计算—存储权衡

### 共识与路线

共同证据链：相关性、奇异值谱和稀疏性诊断 → 相关矩阵替代或抽样插值 → 随机/截断 SVD 与迭代求解替代直接求逆 → 压缩参数选择 → 逐数据集检查最低精度、误差和复杂度。

- 计算路线一以相邻矩阵替代和插值减少运算次数，适合相关性稳定的序列；路线二优化单次 SVD、求逆和乘法，泛化更稳但单次成本较高。
- 存储路线一用 SVD/低秩分解追求高压缩率；路线二用共享正交基、稀疏表示或帧间差分换取更低编解码成本。
- 端到端路线可串联前两问，也可共享基、索引和中间量；前者易审计，后者更高效但误差传播更难解释。
- 口径分歧：论文报告的复杂度降低倍数、压缩率和精度口径不同，必须先统一是否计入相关性计算、训练、索引、编解码和迭代停止成本。

### 假设与验证

- 相邻矩阵相关性在新数据上稳定 -> 决定替代与插值是否有效 -> 应做留组验证和最差组检查
- 忽略读写、比较或索引成本 -> 可能虚低工程复杂度 -> 应同时报告题定口径与实际运行口径
- 低秩或稀疏结构稳定 -> 决定压缩可迁移性 -> 应画奇异值谱并做阈值敏感性

必要检查：逐组最低精度而非只报均值；理论运算量与实际时间双账本；压缩率、编解码成本与误差同表；随机算法多种子和迭代收敛；端到端误差传播与消融。

### 图表与写作

- 结构：H-V-W 与可共享中间量流程图
- 机制：相关系数矩阵、奇异值谱和稀疏系数分布
- 结果：精度—复杂度—压缩率 Pareto 图
- 可信边界：最差数据组、阈值敏感性和收敛图

- 先用数据证据证明可利用的结构，再逐算子说明替代依据；每个优化紧跟复杂度公式、精度损失和适用条件，最后以端到端总账回答题目。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2021-A:263628145be6", "graduate:paper:2021-A:4d82179035ec", "graduate:paper:2021-A:46c616638a0b", "graduate:paper:2021-A:06331a4855e0", "graduate:paper:2021-A:008b9c475463", "graduate:paper:2021-A:4a4c708f7451", "graduate:paper:2021-A:00026fb2a520"], "Q2": ["graduate:paper:2021-A:263628145be6", "graduate:paper:2021-A:4d82179035ec", "graduate:paper:2021-A:46c616638a0b", "graduate:paper:2021-A:06331a4855e0", "graduate:paper:2021-A:008b9c475463", "graduate:paper:2021-A:4a4c708f7451", "graduate:paper:2021-A:00026fb2a520"], "Q3": ["graduate:paper:2021-A:263628145be6", "graduate:paper:2021-A:4d82179035ec", "graduate:paper:2021-A:46c616638a0b", "graduate:paper:2021-A:06331a4855e0", "graduate:paper:2021-A:008b9c475463", "graduate:paper:2021-A:4a4c708f7451", "graduate:paper:2021-A:00026fb2a520"]}

## 2021B｜空气质量预报二次建模

- 范式：多源时空序列校正预测
- 证据：题面 `graduate:problem_statement:2021-B:ddc2e2673570`；论文 9 篇；提名论文 2 篇。
- 问题本质：把一次数值预报、实测污染物和气象条件转化为误差校正问题，并判断何时引入邻站时空信息真正提升未来多日 AQI 预测。

### 逐问依赖

- Q1 统一 IAQI、AQI、首要污染物口径
- Q2 识别气象条件与污染物的关系并形成天气类型或特征层
- Q3 基于 Q1-Q2 建独立站点的二次预报
- Q4 在 Q3 上引入邻站空间传输和时序相关，比较协同模型是否增益

### 共识与路线

共同证据链：缺失异常与风向等周期变量处理 → 污染物—气象关系和天气型识别 → 一次预报误差或浓度的分污染物建模 → AQI 规则回算 → 独立与协同模型同口径时间外比较。

- 统计/树模型路线用 PCA、聚类、RF、SVR、XGBoost，解释性和小样本稳定性较好；深度时序路线用 LSTM、宽度学习或集成网络，能拟合非线性但更易泄漏。
- 二次预报可直接预测实测浓度，也可预测一次预报残差；残差路线更贴合任务且保留物理基线。
- 协同路线有特征拼接、空气流动修正和时空图网络；只有在邻站信息不含未来值且按污染物分别验证时才能声称提升。
- 口径分歧：协同预测对不同污染物可能一升一降，不能用单一平均指标概括；AQI、浓度误差和首要污染物命中率也不是同一目标。

### 假设与验证

- 未来实测气象可用 -> 可能形成信息泄漏 -> 应明确预报时可获得变量
- 站点关系稳定 -> 区域输送在风向变化时会失效 -> 应按天气型分层验证
- 污染排放结构不变 -> 突发源会破坏残差规律 -> 应保留异常日压力测试

必要检查：严格滚动或时间外验证；各污染物 MAE/RMSE/偏差和 AQI 误差；首要污染物命中与无首要污染物规则；独立模型与协同模型消融；极端污染日和不同预报步长分层。

### 图表与写作

- 结构：一次预报—误差校正—AQI 回算流程
- 机制：天气型、风向和污染物关系图
- 结果：逐污染物真实—预测及残差图
- 可信边界：站点/步长/污染等级误差矩阵

- 背景只落到一次预报偏差；问题分析先区分浓度、残差和 AQI 三层，正文逐污染物给基线、改进和增益，结论说明协同信息在哪些污染物和天气型有效。

逐问证据（逐问级绑定）：{"Q1": ["graduate:paper:2021-B:c890e2331541", "graduate:paper:2021-B:b8be27043db2", "graduate:paper:2021-B:a7c4ec823b57", "graduate:paper:2021-B:3d75ccf495b6", "graduate:paper:2021-B:d52dd94d753a", "graduate:paper:2021-B:a209cf095de8", "graduate:paper:2021-B:6b30e77487b0", "graduate:paper:2021-B:a983f1940341", "graduate:paper:2021-B:9d938d0e4179"], "Q2": ["graduate:paper:2021-B:c890e2331541", "graduate:paper:2021-B:b8be27043db2", "graduate:paper:2021-B:a7c4ec823b57", "graduate:paper:2021-B:3d75ccf495b6", "graduate:paper:2021-B:d52dd94d753a", "graduate:paper:2021-B:a209cf095de8", "graduate:paper:2021-B:6b30e77487b0", "graduate:paper:2021-B:a983f1940341", "graduate:paper:2021-B:9d938d0e4179"], "Q３": ["graduate:paper:2021-B:c890e2331541"], "Q3": ["graduate:paper:2021-B:c890e2331541", "graduate:paper:2021-B:b8be27043db2", "graduate:paper:2021-B:a7c4ec823b57", "graduate:paper:2021-B:3d75ccf495b6", "graduate:paper:2021-B:d52dd94d753a", "graduate:paper:2021-B:a209cf095de8", "graduate:paper:2021-B:6b30e77487b0", "graduate:paper:2021-B:a983f1940341", "graduate:paper:2021-B:9d938d0e4179"], "Q4": ["graduate:paper:2021-B:c890e2331541", "graduate:paper:2021-B:b8be27043db2", "graduate:paper:2021-B:a7c4ec823b57", "graduate:paper:2021-B:3d75ccf495b6", "graduate:paper:2021-B:d52dd94d753a", "graduate:paper:2021-B:a209cf095de8", "graduate:paper:2021-B:6b30e77487b0", "graduate:paper:2021-B:a983f1940341", "graduate:paper:2021-B:9d938d0e4179"]}

## 2021C｜帕金森病的脑深部电刺激治疗建模研究

- 范式：神经动力系统仿真与刺激参数优化
- 证据：题面 `graduate:problem_statement:2021-C:dbb42cffa347`；论文 7 篇；提名论文 2 篇。
- 问题本质：从单神经元动力学扩展到基底神经节网络，定义健康—病态差异的可计算指标，再优化刺激靶点、波形、频率和幅值。

### 逐问依赖

- Q1 标定单神经元在交直流和噪声刺激下的放电响应
- Q2 将 Q1 神经元通过兴奋/抑制突触组装为神经回路
- Q3 在 Q2 中构造健康与帕金森状态并定义差异指标
- Q4 用 Q3 指标优化 STN、GPi 等靶点的刺激参数
- Q5 扩展候选通路或靶点并与 Q4 同口径比较

### 共识与路线

共同证据链：Hodgkin-Huxley 状态方程 → 突触耦合与神经核团网络 → 健康/病态对照 → 放电频率、峰间距或中继可靠性指标 → 参数扫描后局部优化与靶点比较。

- 机理路线以 H-H 方程和突触网络为核心，可解释但参数多、计算重；特征分类路线用 SVM 等识别状态，效率高但依赖仿真标签。
- 刺激搜索可用网格/变步长保证可解释覆盖，也可用贪心或启发式加速；后者必须展示多初值稳定性。
- 靶点评价可直接比较放电波形，也可构造病态距离与能耗联合损失；联合损失更贴近治疗但权重需敏感性分析。
- 口径分歧：最优靶点、波形和参数受网络连接、病态构造、评价指标与能耗权重影响，历史参数只能作为仿真结果，不能写成临床建议。

### 假设与验证

- 少量同质神经元代表真实核团 -> 忽略个体异质性 -> 应扰动连接与参数
- 去除或改变单一通路代表帕金森状态 -> 病理过度简化 -> 应用多个病态指标验收
- 模型电刺激等同临床 DBS -> 外推风险高 -> 结论必须限定为理论仿真

必要检查：方程量纲和数值步长收敛；单神经元经典响应复现；网络连接和初值扰动；健康/病态指标可分离；刺激效果与能耗双目标；最优点邻域和多靶点同口径。

### 图表与写作

- 结构：神经元等效电路与核团连接图
- 机制：不同刺激下膜电位和相图
- 结果：健康—病态—刺激后放电对照
- 可信边界：参数热图、稳定区和数值收敛

- 按单元—网络—病态—干预逐层扩展；每次扩展先说明新增状态和参数，再用前一层的验证作接口，结尾区分仿真最优、模型局限和医学推广边界。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2021-C:a67de366bdc3", "graduate:paper:2021-C:9e463fdadba4", "graduate:paper:2021-C:c1465dc157c4", "graduate:paper:2021-C:b4fe907bc3f4", "graduate:paper:2021-C:077ee46748d2", "graduate:paper:2021-C:81d879f048b1", "graduate:paper:2021-C:46e34e5c1a24"], "Q2": ["graduate:paper:2021-C:a67de366bdc3", "graduate:paper:2021-C:9e463fdadba4", "graduate:paper:2021-C:c1465dc157c4", "graduate:paper:2021-C:b4fe907bc3f4", "graduate:paper:2021-C:077ee46748d2", "graduate:paper:2021-C:81d879f048b1", "graduate:paper:2021-C:46e34e5c1a24"], "Q3": ["graduate:paper:2021-C:a67de366bdc3", "graduate:paper:2021-C:9e463fdadba4", "graduate:paper:2021-C:c1465dc157c4", "graduate:paper:2021-C:b4fe907bc3f4", "graduate:paper:2021-C:077ee46748d2", "graduate:paper:2021-C:81d879f048b1", "graduate:paper:2021-C:46e34e5c1a24"], "Q4": ["graduate:paper:2021-C:a67de366bdc3", "graduate:paper:2021-C:9e463fdadba4", "graduate:paper:2021-C:c1465dc157c4", "graduate:paper:2021-C:b4fe907bc3f4", "graduate:paper:2021-C:077ee46748d2", "graduate:paper:2021-C:81d879f048b1", "graduate:paper:2021-C:46e34e5c1a24"], "Q5": ["graduate:paper:2021-C:a67de366bdc3", "graduate:paper:2021-C:9e463fdadba4", "graduate:paper:2021-C:c1465dc157c4", "graduate:paper:2021-C:b4fe907bc3f4", "graduate:paper:2021-C:077ee46748d2", "graduate:paper:2021-C:81d879f048b1", "graduate:paper:2021-C:46e34e5c1a24"]}

## 2021D｜抗乳腺癌候选药物的优化建模

- 范式：高维 QSAR 预测与多性质约束优化
- 证据：题面 `graduate:problem_statement:2021-D:0659b4322a79`；论文 7 篇；提名论文 2 篇。
- 问题本质：从高维分子描述符中形成稳定特征集，分别预测生物活性与五类 ADMET 性质，再在模型可信域内寻找兼顾活性和安全性的描述符范围。

### 逐问依赖

- Q1 从 729 个描述符筛选不超过 20 个活性关键特征
- Q2 用 Q1 特征建活性回归并预测测试化合物
- Q3 建五个 ADMET 分类器并处理类别不平衡
- Q4 将 Q2-Q3 模型作为代理目标，搜索同时满足活性与至少三项 ADMET 的描述符区域

### 共识与路线

共同证据链：常量、缺失和冗余特征清理 → 多方法特征重要性与独立性筛选 → 回归/分类模型比较与调参 → 不平衡处理和多指标验证 → 代理模型驱动的多目标搜索与跨问特征交集解释。

- 特征筛选有相关/互信息/灰色关联的过滤式路线，也有 RF、弹性网、XGBoost 的嵌入式路线；集成排序较稳但必须在训练折内执行。
- 活性预测比较 XGBoost、深度森林、Stacking、SVM 和 MLP；复杂模型只有在重复外部划分中稳定优于基线才值得采用。
- ADMET 可用独立二分类器、原型网络或并行 MLP；类别不平衡下应优先 AUC、F1、召回与校准。
- Q4 的 PSO/DE 代理优化能给候选范围，但若离开训练数据流形，最优点可能是模型幻觉。
- 口径分歧：关键描述符集合和最优范围随筛选方法、随机划分、重采样、目标权重及代理模型而变，交集可作稳健性线索，不能替代化学验证。

### 假设与验证

- 训练测试同分布 -> 决定预测能否迁移 -> 应做适用域检查
- 描述符之外无关键因素 -> 忽略结构和实验条件 -> 结论限于给定数据
- 代理模型在搜索区准确 -> 启发式会钻模型漏洞 -> 应约束到样本凸包/近邻域并复核

必要检查：特征选择嵌套交叉验证；回归残差与外部验证；分类不平衡指标和概率校准；多随机种子稳定性；优化解适用域距离与局部扰动；跨模型候选一致性。

### 图表与写作

- 结构：四问共用数据和代理模型流程
- 机制：相关热图、特征重要性与嵌入分布
- 结果：回归散点、分类 ROC/混淆矩阵和候选范围表
- 可信边界：学习曲线、适用域和优化前沿

- 背景压缩到‘实验筛选成本高’；每问都分训练数据处理、模型选择、验证、测试输出，Q4 必须把预测候选写成待实验验证的描述符区域。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2021-D:f9ac7ba22b06", "graduate:paper:2021-D:0355de2dacb1", "graduate:paper:2021-D:030d46444652", "graduate:paper:2021-D:6adc2185fdce", "graduate:paper:2021-D:322ec9baf97a", "graduate:paper:2021-D:f2ebfff348d4", "graduate:paper:2021-D:7b24dd86646c"], "Q2": ["graduate:paper:2021-D:f9ac7ba22b06", "graduate:paper:2021-D:0355de2dacb1", "graduate:paper:2021-D:030d46444652", "graduate:paper:2021-D:6adc2185fdce", "graduate:paper:2021-D:322ec9baf97a", "graduate:paper:2021-D:f2ebfff348d4", "graduate:paper:2021-D:7b24dd86646c"], "Q3": ["graduate:paper:2021-D:f9ac7ba22b06", "graduate:paper:2021-D:0355de2dacb1", "graduate:paper:2021-D:030d46444652", "graduate:paper:2021-D:6adc2185fdce", "graduate:paper:2021-D:322ec9baf97a", "graduate:paper:2021-D:f2ebfff348d4", "graduate:paper:2021-D:7b24dd86646c"], "Q4": ["graduate:paper:2021-D:f9ac7ba22b06", "graduate:paper:2021-D:0355de2dacb1", "graduate:paper:2021-D:030d46444652", "graduate:paper:2021-D:6adc2185fdce", "graduate:paper:2021-D:322ec9baf97a", "graduate:paper:2021-D:f2ebfff348d4", "graduate:paper:2021-D:7b24dd86646c"]}

## 2021E｜信号干扰下的超宽带（UWB）精确定位问题

- 范式：鲁棒定位、干扰识别与轨迹滤波
- 证据：题面 `graduate:problem_statement:2021-E:6af6f1b329cb`；论文 7 篇；提名论文 2 篇。
- 问题本质：把锚点测距中的异常、非视距偏差和运动连续性分层处理，形成正常/异常统一的三维定位和动态轨迹估计流程。

### 逐问依赖

- Q1 清洗测距文件并构造代表样本
- Q2 在已知场景下分别建立正常与异常测距的静态定位
- Q3 将 Q2 迁移到新场景或新靶点
- Q4 从残差和几何特征识别信号是否受干扰
- Q5 先用 Q4 分流到 Q2/Q3 定位器，再利用运动连续性平滑轨迹

### 共识与路线

共同证据链：重复、缺失和异常测距处理 → TOF 几何与最小二乘初值 → 残差加权、基站剔除或学习型修正 → 正常/异常分类 → 卡尔曼或平滑模型整合动态轨迹。

- 解析路线用最小二乘、残差加权和基站组合，结构清晰且可解释；学习路线用 BP、ELM、MLP 或树模型修正坐标，精度可能更高但依赖场景。
- 异常处理可假设至多一个锚点异常并枚举，也可训练置信度分类器；前者适合可控干扰，后者适合复杂误差但需概率校准。
- 场景迁移可重编码锚点几何到损失函数，也可重训模型；前者更节省样本。
- 口径分歧：二维与三维误差、平均绝对误差与 RMSE、正常与异常样本的评价口径不同；z 方向几何条件较弱，不能用平面精度代表三维精度。

### 假设与验证

- 任一时刻至多一个锚点异常 -> 多路径并发时失效 -> 应模拟多锚点异常
- 异常只使距离增大 -> 某些处理链可能出现负偏差 -> 应检查残差符号
- 采样间隔固定且运动平滑 -> 突然转向会被过度平滑 -> 应报告滤波延迟

必要检查：锚点几何可观测性；正常/异常分层误差；二维与三维同报；新场景迁移验证；分类混淆和置信度；轨迹连续性与转弯响应。

### 图表与写作

- 结构：锚点—靶点三维几何与统一定位框架
- 机制：测距残差、基站组合和置信度
- 结果：预测点云、误差分布与轨迹
- 可信边界：不同干扰数、几何区域和滤波参数敏感性

- 先区分测距清洗、静态定位、干扰识别、动态滤波四层；每层说明输入输出接口，结果始终分 x/y/z、二维/三维和正常/异常报告。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2021-E:34f1734cd05c", "graduate:paper:2021-E:70ab97e8463e", "graduate:paper:2021-E:866534c9a8c4", "graduate:paper:2021-E:1ab32070017d", "graduate:paper:2021-E:de4f8276b314", "graduate:paper:2021-E:c05b8131f46d"], "Q2": ["graduate:paper:2021-E:34f1734cd05c", "graduate:paper:2021-E:70ab97e8463e", "graduate:paper:2021-E:866534c9a8c4", "graduate:paper:2021-E:1ab32070017d", "graduate:paper:2021-E:de4f8276b314", "graduate:paper:2021-E:c05b8131f46d"], "Q3": ["graduate:paper:2021-E:34f1734cd05c", "graduate:paper:2021-E:70ab97e8463e", "graduate:paper:2021-E:866534c9a8c4", "graduate:paper:2021-E:1ab32070017d", "graduate:paper:2021-E:de4f8276b314", "graduate:paper:2021-E:c05b8131f46d"], "Q4": ["graduate:paper:2021-E:34f1734cd05c", "graduate:paper:2021-E:70ab97e8463e", "graduate:paper:2021-E:866534c9a8c4", "graduate:paper:2021-E:1ab32070017d", "graduate:paper:2021-E:de4f8276b314", "graduate:paper:2021-E:c05b8131f46d"], "Q5": ["graduate:paper:2021-E:34f1734cd05c", "graduate:paper:2021-E:70ab97e8463e", "graduate:paper:2021-E:866534c9a8c4", "graduate:paper:2021-E:1ab32070017d", "graduate:paper:2021-E:de4f8276b314", "graduate:paper:2021-E:c05b8131f46d"]}

## 2021F｜航空公司机组优化排班问题

- 范式：大规模多层级人员调度与组合优化
- 证据：题面 `graduate:problem_statement:2021-F:52e787ebfba5`；论文 7 篇；提名论文 2 篇。
- 问题本质：把航段、执勤、任务环和人员资格组织成可行连接网络，在覆盖、乘机、成本、公平与计算规模之间进行分层优化。

### 逐问依赖

- Q1 只在航段层完成资格满足和航班覆盖
- Q2 在 Q1 上组装执勤并加入时长、成本和平衡约束
- Q3 将执勤连接为任务环和完整排班，处理返基地与跨日连续性

### 共识与路线

共同证据链：时间戳和机场/资格标准化 → 航段可连接矩阵 → 航段—执勤—任务环分层生成 → 0-1 规划或集合覆盖 → 启发式求大规模实例并用小规模精确解校验。

- MILP 路线约束透明、可给下界，适合小规模和局部子问题；规则启发式、列生成或分解路线能处理大规模，但最优性证据较弱。
- 多目标可用词典序锁定覆盖后再降成本，也可加权求和；加权法更快但权重会改变业务优先级。
- 一体化排班能减少局部失配，但规模巨大；分层法可审计，必须保留层间回修。
- 口径分歧：不同论文在未覆盖航班、乘机次数、替补资格、执勤成本和公平性之间取舍不同，不能只比较单项最小值；大规模结果还受预生成规则影响。

### 假设与验证

- 排班周期前后无历史任务 -> 边界航班可能被错误放宽 -> 应补首尾状态
- 航班准点且连接时间确定 -> 延误会破坏可行性 -> 应做缓冲情景
- 加权目标代表真实优先级 -> 权重主导方案 -> 应报告词典序或 Pareto 对照

必要检查：每航班资格和人数逐条验收；连接时间、基地和执勤规则；小规模最优解或下界；大规模运行时间和可行率；权重/连接阈值敏感性；延误鲁棒性。

### 图表与写作

- 结构：航段—执勤—任务环层级图
- 机制：可连接网络和算法流程
- 结果：覆盖、成本、乘机与公平性同表
- 可信边界：规模曲线、最优间隙和阈值敏感性

- 先定义四个业务对象和连接规则，再把每条规则翻译为约束；小数据用于证明模型正确，大数据用于证明算法可用，结论按覆盖、成本、公平、鲁棒性分别回答。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2021-F:a9ab71b6dd7e", "graduate:paper:2021-F:3a5031ca36a1", "graduate:paper:2021-F:458b9a043a8e", "graduate:paper:2021-F:692dba6dcf37", "graduate:paper:2021-F:860ef2caf0a9", "graduate:paper:2021-F:8da8ff7c36fa", "graduate:paper:2021-F:eeeffef378bb"], "Q2": ["graduate:paper:2021-F:a9ab71b6dd7e", "graduate:paper:2021-F:3a5031ca36a1", "graduate:paper:2021-F:458b9a043a8e", "graduate:paper:2021-F:692dba6dcf37", "graduate:paper:2021-F:860ef2caf0a9", "graduate:paper:2021-F:8da8ff7c36fa", "graduate:paper:2021-F:eeeffef378bb"], "Q3": ["graduate:paper:2021-F:a9ab71b6dd7e", "graduate:paper:2021-F:3a5031ca36a1", "graduate:paper:2021-F:458b9a043a8e", "graduate:paper:2021-F:692dba6dcf37", "graduate:paper:2021-F:860ef2caf0a9", "graduate:paper:2021-F:8da8ff7c36fa", "graduate:paper:2021-F:eeeffef378bb"]}

## 2022A｜移动场景超分辨定位问题

- 范式：阵列信号稀疏重构与移动目标定位
- 证据：题面 `graduate:problem_statement:2022-A:7ec7071a62ae`；论文 8 篇；提名论文 0 篇。
- 问题本质：利用跨时刻、跨天线和运动先验突破单帧分辨率限制，从混合观测中估计多目标位置、速度或轨迹，并量化可辨识边界。

### 逐问依赖

- Q1 建立静态或单时刻观测模型并识别超分辨条件
- Q2 利用移动产生的多帧信息联合估计位置与运动状态
- Q3 在噪声、模型失配或多目标场景下增强鲁棒性
- Q4 比较方法复杂度、精度和分辨极限并形成工程方案

### 共识与路线

共同证据链：信号同步、去噪和阵列几何 → 观测字典或参数化传播模型 → 谱估计/稀疏重构得到粗位置 → 跨帧匹配与轨迹约束 → 仿真和给定数据上的定位误差验证。

- MUSIC/ESPRIT 等子空间方法速度快、参数少，但依赖源数和协方差质量；压缩感知/稀疏贝叶斯可做超分辨，但网格失配和计算量更明显。
- 逐帧定位后滤波易实现，联合时空重构能利用运动信息但优化更难。
- 数据驱动网络可学习误差修正，必须与物理基线比较并验证新轨迹泛化。
- 口径分歧：定位误差、分辨率、成功率和运行时间需在相同信噪比、目标间距、快拍数及坐标口径下比较。

### 假设与验证

- 阵列和时钟完全标定 -> 微小偏差会形成系统误差 -> 应做标定敏感性
- 目标数已知且运动平滑 -> 交叉/出现消失时失效 -> 应做数据关联测试
- 离散网格含真实位置 -> 产生基偏差 -> 应加离网修正

必要检查：单目标解析或仿真特例；信噪比—间距—快拍数相图；离网偏差；跨帧身份保持；复杂度和实时性；新运动模式验证。

### 图表与写作

- 结构：阵列、目标和移动观测几何
- 机制：空间谱/稀疏系数与跨帧关联
- 结果：真实—估计轨迹和误差
- 可信边界：分辨成功率相图与运行时间

- 先写可辨识性和分辨率定义，再给定位算法；每个改进必须说明利用了哪一维冗余，结论同时回答精度、分辨极限和计算代价。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2022-A:7ee8303a43bd", "graduate:paper:2022-A:f76c04ca6910", "graduate:paper:2022-A:4b5ed2725493", "graduate:paper:2022-A:42f2ea4ef1ed", "graduate:paper:2022-A:6b58b5bed888", "graduate:paper:2022-A:193333ef5b35", "graduate:paper:2022-A:70e064a803fa", "graduate:paper:2022-A:4704bf03e2b2"], "Q2": ["graduate:paper:2022-A:7ee8303a43bd", "graduate:paper:2022-A:f76c04ca6910", "graduate:paper:2022-A:4b5ed2725493", "graduate:paper:2022-A:42f2ea4ef1ed", "graduate:paper:2022-A:6b58b5bed888", "graduate:paper:2022-A:193333ef5b35", "graduate:paper:2022-A:70e064a803fa", "graduate:paper:2022-A:4704bf03e2b2"], "Q3": ["graduate:paper:2022-A:7ee8303a43bd", "graduate:paper:2022-A:f76c04ca6910", "graduate:paper:2022-A:4b5ed2725493", "graduate:paper:2022-A:42f2ea4ef1ed", "graduate:paper:2022-A:6b58b5bed888", "graduate:paper:2022-A:193333ef5b35", "graduate:paper:2022-A:70e064a803fa", "graduate:paper:2022-A:4704bf03e2b2"], "Q4": ["graduate:paper:2022-A:7ee8303a43bd", "graduate:paper:2022-A:f76c04ca6910", "graduate:paper:2022-A:4b5ed2725493", "graduate:paper:2022-A:42f2ea4ef1ed", "graduate:paper:2022-A:6b58b5bed888", "graduate:paper:2022-A:193333ef5b35", "graduate:paper:2022-A:70e064a803fa", "graduate:paper:2022-A:4704bf03e2b2"]}

## 2022B｜方形件组批优化问题

- 范式：制造批次聚类、装载与整数优化
- 证据：题面 `graduate:problem_statement:2022-B:c83a5dd70126`；论文 7 篇；提名论文 0 篇。
- 问题本质：把规格相近或工艺兼容的方形件分组为批次，在容量、尺寸、工序和交付约束下减少批次数、材料浪费或换型成本。

### 逐问依赖

- Q1 建立单批可行性和损失口径
- Q2 对给定订单完成静态组批与排样
- Q3 加入生产节拍、交期或多设备约束形成调度
- Q4 对规模扩展或扰动订单给滚动方案

### 共识与路线

共同证据链：尺寸与工艺属性标准化 → 相似度/兼容图构造 → 聚类或候选批次生成 → 0-1 规划/启发式选择批次 → 利用率、批次数与交期验收。

- 聚类路线快速形成同类批次，适合先分后排但不保证全局最优；集合划分/MILP 能统一约束但候选组合爆炸。
- 二维排样可用精确几何、规则装箱或启发式；规则法速度快但应与面积下界比较。
- 静态一次组批适合订单固定，滚动优化更适合插单但需控制方案变动。
- 口径分歧：批次、利用率、余料和换型次数取决于旋转规则、边距、设备容量及目标优先级，结果不可跨口径直接比较。

### 假设与验证

- 方形件可任意旋转/拼接 -> 工艺方向可能不允许 -> 应显式建约束
- 只按面积判断可装 -> 忽略几何不可排 -> 应输出实际排样
- 订单确定且无插单 -> 计划脆弱 -> 应做滚动情景

必要检查：尺寸和数量守恒；每批几何与工艺可行；面积下界和批次数下界；大规模运行时间；目标权重敏感性；插单/设备故障情景。

### 图表与写作

- 结构：订单—批次—设备关系图
- 机制：兼容矩阵和代表性排样图
- 结果：批次数、利用率、换型和延期对比
- 可信边界：规模曲线与扰动重排成本

- 先定义‘可同批’和损失，再解释候选批次如何产生、全局如何选择；结果表必须与可视排样和约束验收对应。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2022-B:6f83d846eedd", "graduate:paper:2022-B:d6169464f185", "graduate:paper:2022-B:c5c2f5c81d40", "graduate:paper:2022-B:ba7977544ad1", "graduate:paper:2022-B:2e4a14ce1ad1", "graduate:paper:2022-B:bb9c1003ae99", "graduate:paper:2022-B:0e7b28a3f5bc"], "Q2": ["graduate:paper:2022-B:6f83d846eedd", "graduate:paper:2022-B:d6169464f185", "graduate:paper:2022-B:c5c2f5c81d40", "graduate:paper:2022-B:ba7977544ad1", "graduate:paper:2022-B:2e4a14ce1ad1", "graduate:paper:2022-B:bb9c1003ae99", "graduate:paper:2022-B:0e7b28a3f5bc"]}

## 2022C｜汽车制造涂装-总装缓存调序区调度优化问题

- 范式：带缓存和工艺约束的车辆重排序
- 证据：题面 `graduate:problem_statement:2022-C:157226574e34`；论文 7 篇；提名论文 0 篇。
- 问题本质：利用有限缓存道改变涂装出车顺序，使总装车型、颜色或选装序列满足节拍与均衡规则，同时最小化违约和换序成本。

### 逐问依赖

- Q1 解析进入缓存前序列和总装目标规则
- Q2 在固定缓存结构下安排入道、出道和车辆顺序
- Q3 加入多类序列约束、故障或动态到车
- Q4 评价方案可实施性和实时调度策略

### 共识与路线

共同证据链：车辆属性编码 → 缓存道状态转移 → 规则违约惩罚 → 入道/出道联合调度 → 小规模精确解与大规模启发式。

- MILP/动态规划能严谨表示缓存状态，适合小规模；遗传、模拟退火和规则启发式更能处理全量序列。
- 加权惩罚易求解但掩盖硬规则；词典序先保硬约束再优化软指标更符合生产。
- 离线全局序列质量高，滚动窗口更实时但窗口太短会造成后效。
- 口径分歧：不同论文对违约次数、连续车型限制、缓存操作和初末状态定义不同，应先统一再比较。

### 假设与验证

- 缓存操作瞬时且无故障 -> 低估节拍冲突 -> 应加入操作时间
- 所有规则可加权互换 -> 可能牺牲关键硬约束 -> 应分硬软层
- 未来车辆序列完全已知 -> 动态生产不成立 -> 应滚动验证

必要检查：逐时缓存容量与先进/后出规则；每车唯一进出且数量守恒；硬规则零违约；与原序列和简单规则基线比较；窗口长度/算法种子敏感性；实时运行时间。

### 图表与写作

- 结构：涂装—缓存道—总装流程
- 机制：缓存状态时间线和一次换序示例
- 结果：规则违约热图与目标对比
- 可信边界：窗口、故障和到车扰动

- 先把缓存物理动作写成状态方程，再写总装序列规则；正文用一个小例子证明状态转移正确，再报告全量结果和违约明细。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2022-C:a8df9e907b82", "graduate:paper:2022-C:5837d7d5283d", "graduate:paper:2022-C:560712b8aa46", "graduate:paper:2022-C:c109ebf5fa9c", "graduate:paper:2022-C:8b44b3955a1d", "graduate:paper:2022-C:050ba3aea273", "graduate:paper:2022-C:5fa92336a1b1"], "Q2": ["graduate:paper:2022-C:a8df9e907b82", "graduate:paper:2022-C:5837d7d5283d", "graduate:paper:2022-C:560712b8aa46", "graduate:paper:2022-C:c109ebf5fa9c", "graduate:paper:2022-C:8b44b3955a1d", "graduate:paper:2022-C:050ba3aea273", "graduate:paper:2022-C:5fa92336a1b1"]}

## 2022D｜PISA架构芯片资源排布问题

- 范式：程序依赖图上的分级资源排布
- 证据：题面 `graduate:problem_statement:2022-D:ae01f7d2c334`；论文 7 篇；提名论文 0 篇。
- 问题本质：把 P4 程序基本块及操作映射到有限流水级，在依赖、时序、HASH/ALU 等资源上限和互斥路径共享条件下最小化级数或资源浪费。

### 逐问依赖

- Q1 在基本依赖与每级资源约束下完成排布
- Q2 识别不共路径的基本块并允许互斥资源共享
- 后续扩展若存在则在前两问上处理更多流图、资源类型或优化目标

### 共识与路线

共同证据链：程序转 DAG/控制流图 → 基本块内先后约束 → 路径互斥和可共享关系 → 分级 0-1 决策 → 可行性校验与级数/资源利用评价。

- MILP/约束规划能准确表达依赖、级数和容量，便于证明；拓扑排序、列表调度和元启发式适合大图。
- 保守路线不给不同基本块共享资源，易可行但浪费；路径敏感路线利用控制流互斥，提高利用率但必须证明两块不共执行路径。
- 先压缩级数再均衡资源的词典序目标比单一加权更易解释。
- 口径分歧：流水级数和资源利用率受基本块可达性定义、共享规则、是否允许空级和目标优先级影响。

### 假设与验证

- 互斥基本块绝不并行 -> 控制流分析错误会导致资源冲突 -> 应做可达性验证
- 同级操作无组合时延 -> 可能违反芯片频率 -> 应加入关键路径
- 资源类型可独立计数 -> 实际布线/端口耦合被忽略 -> 限定模型边界

必要检查：DAG 无环与依赖顺序；每级各资源不超限；共享仅发生在互斥路径；级数下界或小规模最优解；不同流图规模运行时间；关键资源敏感性。

### 图表与写作

- 结构：控制流图和流水级排布图
- 机制：路径互斥/共享示例
- 结果：每级资源堆叠图和利用率
- 可信边界：级数下界、资源上限敏感性和运行时间

- 先定义基本块可达与共享判据，再把依赖、容量和目标逐条翻译；结果不只给级号，还要逐级验收资源和路径。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2022-D:e1e8632f2e10", "graduate:paper:2022-D:7dcd04bc4399", "graduate:paper:2022-D:8d7c36f66d10", "graduate:paper:2022-D:e69dbf4920ac", "graduate:paper:2022-D:df2e78d06070", "graduate:paper:2022-D:d2dcf6990653", "graduate:paper:2022-D:7751354cf5ca"], "Q2": ["graduate:paper:2022-D:e1e8632f2e10", "graduate:paper:2022-D:7dcd04bc4399", "graduate:paper:2022-D:8d7c36f66d10", "graduate:paper:2022-D:e69dbf4920ac", "graduate:paper:2022-D:df2e78d06070", "graduate:paper:2022-D:d2dcf6990653", "graduate:paper:2022-D:7751354cf5ca"]}

## 2022E｜草原放牧策略研究

- 范式：生态系统动力学、预测与可持续决策
- 证据：题面 `graduate:problem_statement:2022-E:f98502ddf2e5`；论文 7 篇；提名论文 0 篇。
- 问题本质：把降水、土壤水分、植被生物量、放牧强度、碳氮和退化程度连成状态系统，寻找兼顾生产与生态恢复的放牧策略。

### 逐问依赖

- Q1 定量刻画不同放牧强度对土壤水分和植被生物量的影响
- Q2 在 Q1 关系上预测不同深度土壤水分或植被状态
- Q3 扩展到土壤碳氮等理化性质
- Q4 建立沙漠化/板结化等退化评价
- Q5 若要求策略优化，则综合前四问确定可持续载畜强度和轮牧安排

### 共识与路线

共同证据链：多源数据时间空间对齐 → 水量/生物量机理或回归关系 → 时序预测 → 土壤性质与碳氮估计 → 退化综合评价 → 放牧强度情景优化。

- 水分—生物量可用微分方程强调机制，也可用 RF、LSTM 等预测；机理模型外推更有依据，机器学习短期精度可能更高。
- 退化评价有熵权-TOPSIS、PCA、聚类和沙漠化指数；权重客观不等于因果，需与实测等级对照。
- 策略优化可用情景扫描或 PSO/多目标优化；生态阈值应作为硬约束而非仅加权。
- 口径分歧：不同数据深度、年份、放牧区和退化指标导致趋势及最优载畜量差异，不能把单点预测当整个草原结论。

### 假设与验证

- 监测点代表区域 -> 空间异质性被忽略 -> 应分区或层级建模
- 未来气候延续历史 -> 干旱年预测失效 -> 应做气候情景
- 相关关系代表生态机制 -> 可能误导策略 -> 应用水量/物质守恒或文献约束

必要检查：时间外和空间外验证；水量/生物量非负与守恒；不同深度误差；权重和聚类稳定性；极端干旱/强放牧情景；策略的生态阈值与收益双验收。

### 图表与写作

- 结构：气候—土壤—植被—放牧因果图
- 机制：水分和生物量状态曲线
- 结果：退化地图/等级与策略前沿
- 可信边界：区域、年份和气候情景误差

- 背景落到可持续载畜决策；每问都说明前一问输出如何成为状态或约束，结论按预测、生态风险和策略适用区域分开。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2022-E:ea0ba69ea7db", "graduate:paper:2022-E:84521bb3d18a", "graduate:paper:2022-E:5c26affd748a", "graduate:paper:2022-E:3fe8db58775d", "graduate:paper:2022-E:4047c1a98e1a", "graduate:paper:2022-E:c5d89a8d8935", "graduate:paper:2022-E:6e3f56650ebc"], "Q2": ["graduate:paper:2022-E:ea0ba69ea7db", "graduate:paper:2022-E:84521bb3d18a", "graduate:paper:2022-E:5c26affd748a", "graduate:paper:2022-E:3fe8db58775d", "graduate:paper:2022-E:4047c1a98e1a", "graduate:paper:2022-E:c5d89a8d8935", "graduate:paper:2022-E:6e3f56650ebc"], "Q3": ["graduate:paper:2022-E:ea0ba69ea7db", "graduate:paper:2022-E:84521bb3d18a", "graduate:paper:2022-E:5c26affd748a", "graduate:paper:2022-E:3fe8db58775d", "graduate:paper:2022-E:4047c1a98e1a", "graduate:paper:2022-E:c5d89a8d8935", "graduate:paper:2022-E:6e3f56650ebc"], "Q4": ["graduate:paper:2022-E:ea0ba69ea7db", "graduate:paper:2022-E:84521bb3d18a", "graduate:paper:2022-E:5c26affd748a", "graduate:paper:2022-E:3fe8db58775d", "graduate:paper:2022-E:4047c1a98e1a", "graduate:paper:2022-E:c5d89a8d8935", "graduate:paper:2022-E:6e3f56650ebc"], "Q5": ["graduate:paper:2022-E:ea0ba69ea7db", "graduate:paper:2022-E:84521bb3d18a", "graduate:paper:2022-E:5c26affd748a", "graduate:paper:2022-E:3fe8db58775d", "graduate:paper:2022-E:4047c1a98e1a", "graduate:paper:2022-E:c5d89a8d8935", "graduate:paper:2022-E:6e3f56650ebc"]}

## 2022F｜COVID-19疫情期间生活物资的科学管理问题

- 范式：应急物流、设施选址与动态分配
- 证据：题面 `graduate:problem_statement:2022-F:92b21b0630d1`；论文 7 篇；提名论文 0 篇。
- 问题本质：在疫情风险、居民需求、接触机会、库存与运输能力共同约束下，构建投放点—分拣点—小区的韧性供应网络。

### 逐问依赖

- Q1 评估大规模生活物资流动与疫情变化的关系
- Q2 基于人口、疫情和路网评价并优化投放/分拣/储备点
- Q3 分析供需时序并调整每日发放
- Q4 复用 Q2-Q3 构建三级网络、车辆路径和封控预案

### 共识与路线

共同证据链：疫情与物资数据清洗 → SIR/SEIR 或时间序列反事实比较 → 投放点需求评价与选址 → 库存—需求动态分配 → 分拣点—小区路径优化与备用点。

- 疫情影响评估有 SIR/SEIR、ARIMA/Prophet/LSTM 和突变检验；反事实预测若无控制变量，结论只能写关联性。
- 选址可用聚类+覆盖模型、熵权/TOPSIS 或多目标遗传算法；前者直观，后者能纳入成本和韧性。
- 分配可用库存规则、DEA 评价或供需优化；路径用 VRP、最短路与元启发式。
- 口径分歧：投放点和分拣点最优数量差异大，主要来自服务半径、人口口径、建设成本、疫情权重与备用能力定义；不能直接投票。

### 假设与验证

- 物资发放直接导致疫情下降 -> 存在政策和时间混杂 -> 应做滞后/对照分析
- 居民需求按人口线性 -> 特殊人群和库存被忽略 -> 应分层
- 两点直线距离代表路网 -> 会低估配送成本 -> 应尽量用道路距离

必要检查：反事实模型的时间外误差与滞后敏感性；供需和库存守恒；服务覆盖和容量；路径载重与时间窗；随机关闭点的韧性；多情景总成本与接触风险。

### 图表与写作

- 结构：储备—分拣—投放—居民三级网络
- 机制：疫情与物资时序及滞后
- 结果：覆盖地图、库存曲线和路径图
- 可信边界：备用点、需求激增和道路受阻情景

- 先谨慎界定物资与疫情的关联证据，再依次写选址、分配和路径；预案要用触发条件、状态更新和备用方案表达，而不是只给静态地图。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2022-F:c96e8a64f25b", "graduate:paper:2022-F:14817f01a096", "graduate:paper:2022-F:b9f044b3f565", "graduate:paper:2022-F:2b02838f289d", "graduate:paper:2022-F:fb0babe524b9", "graduate:paper:2022-F:4f407ad33c7a", "graduate:paper:2022-F:5bbfdd257360"], "Q2": ["graduate:paper:2022-F:c96e8a64f25b", "graduate:paper:2022-F:14817f01a096", "graduate:paper:2022-F:b9f044b3f565", "graduate:paper:2022-F:2b02838f289d", "graduate:paper:2022-F:fb0babe524b9", "graduate:paper:2022-F:4f407ad33c7a", "graduate:paper:2022-F:5bbfdd257360"], "Q3": ["graduate:paper:2022-F:c96e8a64f25b", "graduate:paper:2022-F:14817f01a096", "graduate:paper:2022-F:b9f044b3f565", "graduate:paper:2022-F:2b02838f289d", "graduate:paper:2022-F:fb0babe524b9", "graduate:paper:2022-F:4f407ad33c7a", "graduate:paper:2022-F:5bbfdd257360"], "Q4": ["graduate:paper:2022-F:c96e8a64f25b", "graduate:paper:2022-F:14817f01a096", "graduate:paper:2022-F:b9f044b3f565", "graduate:paper:2022-F:2b02838f289d", "graduate:paper:2022-F:fb0babe524b9", "graduate:paper:2022-F:4f407ad33c7a", "graduate:paper:2022-F:5bbfdd257360"]}

## 2023A｜WLAN网络信道接入机制建模

- 范式：随机接入协议的马尔可夫建模与参数优化
- 证据：题面 `graduate:problem_statement:2023-A:15e8f8f55039`；论文 10 篇；提名论文 0 篇。
- 问题本质：把 CSMA/CA 退避、竞争、碰撞、重传和信道状态转成可求稳态的随机过程，解释吞吐、时延和公平性如何随网络规模及接入参数变化。

### 逐问依赖

- Q1 建立单类节点的基础接入和碰撞概率模型
- Q2 扩展不同业务、速率或竞争窗口并计算吞吐/时延
- Q3 加入隐藏节点、干扰或动态负载
- Q4 优化接入参数并在多场景下验证

### 共识与路线

共同证据链：协议事件和时隙口径 → 节点退避马尔可夫链 → 发送概率—碰撞概率不动点 → 吞吐/时延/公平指标 → 仿真或枚举校验 → 竞争窗口等参数优化。

- Bianchi 类二维马尔可夫链解析性强，适合饱和同质节点；离散事件仿真能处理复杂协议但解释和搜索成本更高。
- 不动点迭代适合求稳态，动态规划/元启发式适合参数优化；必须给收敛和多初值。
- 单一吞吐最大化可能损害时延与公平，应采用约束或 Pareto。
- 口径分歧：吞吐率是否含协议开销、时延起止事件、饱和/非饱和和碰撞模型不同会产生不可直接比较的结果。

### 假设与验证

- 节点独立同分布且饱和 -> 真实突发业务失效 -> 应加非饱和情景
- 碰撞概率恒定 -> 退避阶段相关性被忽略 -> 应用仿真复核
- 信道理想无捕获 -> 强弱节点场景偏差 -> 应做误码/捕获敏感性

必要检查：概率归一和不动点收敛；单节点/低负载特例；解析与离散事件仿真；吞吐时延公平同报；规模和参数敏感性；优化策略跨场景稳定性。

### 图表与写作

- 结构：协议状态机和马尔可夫链
- 机制：发送/碰撞概率不动点曲线
- 结果：吞吐—时延—公平曲线
- 可信边界：节点数、负载和信道误差相图

- 先把一个时隙内事件说清，再写状态转移；从概率到性能指标逐式解释，优化段必须指出改善的机制和牺牲的指标。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2023-A:d0104b0e2c70", "graduate:paper:2023-A:6b5f1e1db98c", "graduate:paper:2023-A:ee462e5f89a4", "graduate:paper:2023-A:e7b9703cb19d", "graduate:paper:2023-A:45b8269848e7", "graduate:paper:2023-A:a06aa534c3bb", "graduate:paper:2023-A:a0981c4046bc", "graduate:paper:2023-A:aad533fb34f4", "graduate:paper:2023-A:82524f06613f", "graduate:paper:2023-A:8b0b0eada424"], "Q2": ["graduate:paper:2023-A:d0104b0e2c70", "graduate:paper:2023-A:6b5f1e1db98c", "graduate:paper:2023-A:ee462e5f89a4", "graduate:paper:2023-A:e7b9703cb19d", "graduate:paper:2023-A:45b8269848e7", "graduate:paper:2023-A:a06aa534c3bb", "graduate:paper:2023-A:a0981c4046bc", "graduate:paper:2023-A:aad533fb34f4", "graduate:paper:2023-A:82524f06613f", "graduate:paper:2023-A:8b0b0eada424"], "Q3": ["graduate:paper:2023-A:d0104b0e2c70", "graduate:paper:2023-A:6b5f1e1db98c", "graduate:paper:2023-A:ee462e5f89a4", "graduate:paper:2023-A:e7b9703cb19d", "graduate:paper:2023-A:45b8269848e7", "graduate:paper:2023-A:a06aa534c3bb", "graduate:paper:2023-A:a0981c4046bc", "graduate:paper:2023-A:aad533fb34f4", "graduate:paper:2023-A:82524f06613f", "graduate:paper:2023-A:8b0b0eada424"], "Q4": ["graduate:paper:2023-A:d0104b0e2c70", "graduate:paper:2023-A:6b5f1e1db98c", "graduate:paper:2023-A:ee462e5f89a4", "graduate:paper:2023-A:e7b9703cb19d", "graduate:paper:2023-A:45b8269848e7", "graduate:paper:2023-A:a06aa534c3bb", "graduate:paper:2023-A:a0981c4046bc", "graduate:paper:2023-A:aad533fb34f4", "graduate:paper:2023-A:82524f06613f", "graduate:paper:2023-A:8b0b0eada424"]}

## 2023B｜DFT类矩阵的整数分解逼近

- 范式：整数矩阵因子分解、硬件复杂度与逼近误差优化
- 证据：题面 `graduate:problem_statement:2023-B:f433f551a7bd`；论文 9 篇；提名论文 0 篇。
- 问题本质：把 DFT 及 Kronecker 类矩阵近似分解为稀疏、低取值范围的整数矩阵连乘，在乘法器数量、位宽、加法量和变换精度间求可实现方案。

### 逐问依赖

- Q1 固定整数范围，优先减少非零乘法器
- Q2 限制因子元素实虚部取值范围，比较硬件复杂度
- Q3 同时优化稀疏性与取值范围
- Q4 推广到 Kronecker 等其他矩阵
- Q5 在 Q3 基础上加入明确精度约束并形成折中

### 共识与路线

共同证据链：DFT 结构和对称性分析 → 整数因子参数化 → 稀疏度/位宽硬件代理 → 组合或连续松弛搜索 → 误差、复杂度和信号任务验证。

- 解析分解利用蝶形、Kronecker 和对称结构，硬件解释强但可搜索空间有限；遗传/退火/整数规划可发现新结构但需证明可复现。
- 逐层贪心量化速度快，却可能累积误差；联合多因子优化质量更高但维度大。
- 矩阵范数误差易算，通信/图像任务误差更贴近应用；二者应同时报告。
- 口径分歧：乘法器是否把 ±1、±j 计入，系数量化位宽、缩放因子和精度范数不同会改变复杂度排名。

### 假设与验证

- 硬件复杂度可由非零数和取值范围完全代表 -> 忽略布线与关键路径 -> 结论限于代理指标
- 缩放无成本 -> 实际量化会增加资源 -> 应计入
- 训练信号代表所有输入 -> 矩阵误差可能集中在特定方向 -> 应做最坏方向或谱范数

必要检查：因子连乘复算；整数和稀疏约束逐项验收；不同范数误差；乘加和位宽统一账本；标准信号任务对照；随机搜索多次稳定性。

### 图表与写作

- 结构：DFT/蝶形和因子连乘图
- 机制：整数系数分布与层间误差累积
- 结果：硬件复杂度—精度 Pareto 前沿
- 可信边界：矩阵规模、位宽和输入信号敏感性

- 先定义硬件代理和误差口径；每问沿‘新增限制—分解方法—可行解—复杂度—精度’展开，Q5 用 Pareto 而非单一最优收束。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2023-B:347798782815", "graduate:paper:2023-B:fa8df61ba4fe", "graduate:paper:2023-B:a844250094c7", "graduate:paper:2023-B:166b58049cd0", "graduate:paper:2023-B:0d36bb7b8f4c", "graduate:paper:2023-B:32b9dc631576", "graduate:paper:2023-B:4dc3fe33a57b", "graduate:paper:2023-B:83c53c0fe68b", "graduate:paper:2023-B:c02b682ad79a"], "Q2": ["graduate:paper:2023-B:347798782815", "graduate:paper:2023-B:fa8df61ba4fe", "graduate:paper:2023-B:a844250094c7", "graduate:paper:2023-B:166b58049cd0", "graduate:paper:2023-B:0d36bb7b8f4c", "graduate:paper:2023-B:32b9dc631576", "graduate:paper:2023-B:4dc3fe33a57b", "graduate:paper:2023-B:83c53c0fe68b", "graduate:paper:2023-B:c02b682ad79a"], "Q3": ["graduate:paper:2023-B:347798782815", "graduate:paper:2023-B:fa8df61ba4fe", "graduate:paper:2023-B:a844250094c7", "graduate:paper:2023-B:166b58049cd0", "graduate:paper:2023-B:0d36bb7b8f4c", "graduate:paper:2023-B:32b9dc631576", "graduate:paper:2023-B:4dc3fe33a57b", "graduate:paper:2023-B:83c53c0fe68b", "graduate:paper:2023-B:c02b682ad79a"], "Q4": ["graduate:paper:2023-B:347798782815", "graduate:paper:2023-B:fa8df61ba4fe", "graduate:paper:2023-B:a844250094c7", "graduate:paper:2023-B:166b58049cd0", "graduate:paper:2023-B:0d36bb7b8f4c", "graduate:paper:2023-B:32b9dc631576", "graduate:paper:2023-B:4dc3fe33a57b", "graduate:paper:2023-B:83c53c0fe68b", "graduate:paper:2023-B:c02b682ad79a"], "Q5": ["graduate:paper:2023-B:347798782815", "graduate:paper:2023-B:fa8df61ba4fe", "graduate:paper:2023-B:a844250094c7", "graduate:paper:2023-B:166b58049cd0", "graduate:paper:2023-B:0d36bb7b8f4c", "graduate:paper:2023-B:32b9dc631576", "graduate:paper:2023-B:4dc3fe33a57b", "graduate:paper:2023-B:83c53c0fe68b", "graduate:paper:2023-B:c02b682ad79a"]}

## 2023C｜大规模创新类竞赛评审方案研究

- 范式：评委分配、评分校准与公平排序
- 证据：题面 `graduate:problem_statement:2023-C:241b35946047`；论文 10 篇；提名论文 0 篇。
- 问题本质：在专业匹配、回避、工作量和有限评审资源约束下分配项目，并消除评委尺度差异，得到稳定、可解释且可复核的晋级排序。

### 逐问依赖

- Q1 诊断现有评分的评委偏差与项目差异
- Q2 设计项目—评委匹配和工作量均衡方案
- Q3 建立评分标准化/校准与排序
- Q4 在复评或跨组比较中检验稳定性并优化规则

### 共识与路线

共同证据链：缺失、异常和回避关系处理 → 评委严宽度/一致性估计 → 匹配图或 0-1 分配 → 分层标准化/统计校准 → 排名稳定性和模拟复评。

- 分配可用匈牙利、网络流/MILP 保证全局约束，也可用聚类和遗传算法兼顾语义匹配。
- 评分校准有组内 Z 分数、秩变换、两因素模型、IRT/贝叶斯层级模型；简单方法透明，层级模型能分离项目质量与评委偏差。
- 排序可用加权综合或不确定性区间；临界项目应触发复评而非强行精确排序。
- 口径分歧：排名变化来自校准方式、缺失处理、评委可靠性权重和晋级阈值，不能只比较最终名次一致率。

### 假设与验证

- 评委偏差跨项目稳定 -> 专业子领域中可能变化 -> 应分层估计
- 项目真实质量可由加性模型表示 -> 交互偏好被忽略 -> 应检查残差
- 历史评分无策略行为 -> 可能存在抱团或极端分 -> 应做异常评委诊断

必要检查：回避和专业匹配零违约；工作量均衡；评委间一致性；校准前后排名稳定和临界区；模拟缺评委/极端评分；复评命中率或不确定区间覆盖。

### 图表与写作

- 结构：项目—评委二部图
- 机制：评委严宽度和分数分布
- 结果：校准前后排名/晋级变化
- 可信边界：临界项目区间与扰动稳定性

- 先把公平拆为专业匹配、负载、评分尺度和排名稳定四类；方法段逐一对应，结论不能只给名单，要解释复评机制和争议边界。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2023-C:48705675e604", "graduate:paper:2023-C:80e3c2b85d26", "graduate:paper:2023-C:ec41ae36192c", "graduate:paper:2023-C:539179b74a7d", "graduate:paper:2023-C:cbb8f63b92aa", "graduate:paper:2023-C:221af1758a11", "graduate:paper:2023-C:a8b6f9f4a638", "graduate:paper:2023-C:18029df70b77", "graduate:paper:2023-C:abffb428040b", "graduate:paper:2023-C:afaf815e03d4"], "Q2": ["graduate:paper:2023-C:48705675e604", "graduate:paper:2023-C:80e3c2b85d26", "graduate:paper:2023-C:ec41ae36192c", "graduate:paper:2023-C:539179b74a7d", "graduate:paper:2023-C:cbb8f63b92aa", "graduate:paper:2023-C:221af1758a11", "graduate:paper:2023-C:a8b6f9f4a638", "graduate:paper:2023-C:18029df70b77", "graduate:paper:2023-C:abffb428040b", "graduate:paper:2023-C:afaf815e03d4"], "Q3": ["graduate:paper:2023-C:48705675e604", "graduate:paper:2023-C:80e3c2b85d26", "graduate:paper:2023-C:ec41ae36192c", "graduate:paper:2023-C:539179b74a7d", "graduate:paper:2023-C:cbb8f63b92aa", "graduate:paper:2023-C:221af1758a11", "graduate:paper:2023-C:a8b6f9f4a638", "graduate:paper:2023-C:18029df70b77", "graduate:paper:2023-C:abffb428040b", "graduate:paper:2023-C:afaf815e03d4"], "Q4": ["graduate:paper:2023-C:48705675e604", "graduate:paper:2023-C:80e3c2b85d26", "graduate:paper:2023-C:ec41ae36192c", "graduate:paper:2023-C:539179b74a7d", "graduate:paper:2023-C:cbb8f63b92aa", "graduate:paper:2023-C:221af1758a11", "graduate:paper:2023-C:a8b6f9f4a638", "graduate:paper:2023-C:18029df70b77", "graduate:paper:2023-C:abffb428040b", "graduate:paper:2023-C:afaf815e03d4"]}

## 2023D｜区域双碳目标与路径规划研究

- 范式：碳排放核算、情景预测与政策路径优化
- 证据：题面 `graduate:problem_statement:2023-D:03b15ecbf04a`；论文 9 篇；提名论文 0 篇。
- 问题本质：统一区域碳排放核算口径，识别经济—人口—能源驱动因素，预测基准情景并反推达峰、降碳和中和目标所需的政策组合。

### 逐问依赖

- Q1 核算并分析碳排放、经济、人口和能源现状
- Q2 基于 Q1 驱动关系预测多指标基准轨迹
- Q3 在 Q2 上设置达峰/中和目标和政策情景，优化能源、产业与碳汇路径

### 共识与路线

共同证据链：能源活动数据与排放因子统一 → 趋势和驱动分解 → 人口/经济/能源预测 → 多情景碳排放模拟 → 成本、发展与目标约束下路径选择。

- 预测有回归、灰色、ARIMA、LSTM 和系统动力学；短序列下简单模型更稳，系统动力学更适合政策解释。
- 驱动分析可用 STIRPAT/LMDI、相关和特征重要性；因果边界需谨慎。
- 路径规划可用情景扫描、PSO/多目标优化或动态规划；应区分参数情景与真正决策变量。
- 口径分歧：达峰年份和碳中和缺口强烈依赖核算边界、排放因子、GDP 价格口径、碳汇定义和政策强度，必须用情景区间表达。

### 假设与验证

- 排放因子固定 -> 技术变化会改变核算 -> 应做区间
- 历史增长关系持续 -> 结构转型时失效 -> 应设情景断点
- 碳汇可按计划增长 -> 土地和自然约束被忽略 -> 应给容量上限

必要检查：单位和核算边界；历史回测与滚动预测；排放恒等式或 LMDI 重构；情景参数透明；目标达成与政策成本同验收；关键因子敏感性和不确定区间。

### 图表与写作

- 结构：排放核算与驱动因果图
- 机制：LMDI/弹性贡献
- 结果：基准和政策情景轨迹
- 可信边界：关键参数扇形区间与目标可行域

- 背景直接落到区域路径决策；Q1 定口径，Q2 给基准，Q3 才谈政策，结尾分‘预测结论、实现条件、不可控风险’三层。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2023-D:b7842f71a6ab", "graduate:paper:2023-D:be65227642b1", "graduate:paper:2023-D:ccf97a878496", "graduate:paper:2023-D:3724e20f6da1", "graduate:paper:2023-D:aea4e5e843d7", "graduate:paper:2023-D:3d158a2578e0", "graduate:paper:2023-D:b1c5d4e41159", "graduate:paper:2023-D:0368cd43a8e3", "graduate:paper:2023-D:99181e11ced3"], "Q2": ["graduate:paper:2023-D:b7842f71a6ab", "graduate:paper:2023-D:be65227642b1", "graduate:paper:2023-D:ccf97a878496", "graduate:paper:2023-D:3724e20f6da1", "graduate:paper:2023-D:aea4e5e843d7", "graduate:paper:2023-D:3d158a2578e0", "graduate:paper:2023-D:b1c5d4e41159", "graduate:paper:2023-D:0368cd43a8e3", "graduate:paper:2023-D:99181e11ced3"], "Q3": ["graduate:paper:2023-D:b7842f71a6ab", "graduate:paper:2023-D:be65227642b1", "graduate:paper:2023-D:ccf97a878496", "graduate:paper:2023-D:3724e20f6da1", "graduate:paper:2023-D:aea4e5e843d7", "graduate:paper:2023-D:3d158a2578e0", "graduate:paper:2023-D:b1c5d4e41159", "graduate:paper:2023-D:0368cd43a8e3", "graduate:paper:2023-D:99181e11ced3"]}

## 2023E｜出血性脑卒中临床智能诊疗建模

- 范式：纵向医学影像特征与临床风险预测
- 证据：题面 `graduate:problem_statement:2023-E:b789932d0c32`；论文 10 篇；提名论文 0 篇。
- 问题本质：融合基线临床、治疗、影像组学和多时点随访，预测血肿扩张、组织水肿及预后，并区分相关性、个体风险与治疗效果。

### 逐问依赖

- Q1 定义并识别早期血肿扩张
- Q2 建立血肿/水肿随时间演化并进行亚型聚类
- Q3 融合治疗和个体特征预测结局
- Q4 解释关键因素并形成风险分层或辅助建议

### 共识与路线

共同证据链：患者级清洗和时间对齐 → 影像体积/形态变化构造标签 → 特征筛选与不平衡处理 → 分类/回归/聚类模型 → 患者级交叉验证与可解释性。

- Logistic/Cox/混合效应模型解释性强；RF、XGBoost、SVM 和深度模型能拟合非线性但需严格防泄漏。
- 水肿演化可用轨迹聚类、时间函数或混合效应模型；逐时点独立回归会丢失个体内相关。
- 治疗变量直接入模只能做预测，若声称疗效需倾向评分、因果图或分层敏感性。
- 口径分歧：血肿扩张阈值、时间窗、缺失随访、患者划分和结局指标不同会改变性能；竞赛数据的高准确率不能外推临床。

### 假设与验证

- 同一患者多次记录独立 -> 会数据泄漏 -> 必须按患者划分
- 缺失随机 -> 重症失访可能有偏 -> 应做缺失机制敏感性
- 治疗与结局关系无混杂 -> 实际严重度决定治疗 -> 不能直接写因果

必要检查：患者级拆分；不平衡指标与校准；时间窗和标签阈值敏感性；外部或留中心验证；轨迹聚类稳定性；治疗混杂分析；医学边界声明。

### 图表与写作

- 结构：患者时间线和数据融合图
- 机制：血肿/水肿轨迹与亚型
- 结果：ROC/PR、校准和个体风险
- 可信边界：亚组误差、缺失和阈值敏感性

- 先定义临床事件和时间窗，再写模型；性能、校准、解释和临床边界分别呈现，结论使用‘风险预测/关联’而不是‘诊断/疗效证明’。

逐问证据（逐问级绑定）：{"Q1": ["graduate:paper:2023-E:3f4621bddfbb", "graduate:paper:2023-E:0b97a60eedbe", "graduate:paper:2023-E:455bbe350f9b", "graduate:paper:2023-E:ed9d2f8c1d44", "graduate:paper:2023-E:3f818f083871", "graduate:paper:2023-E:eaa884b73993", "graduate:paper:2023-E:ab6183848dc6", "graduate:paper:2023-E:5c42b2bfe22e", "graduate:paper:2023-E:f7c0743f16ee", "graduate:paper:2023-E:9a48c6fe4537"], "Q2": ["graduate:paper:2023-E:3f4621bddfbb", "graduate:paper:2023-E:0b97a60eedbe", "graduate:paper:2023-E:455bbe350f9b", "graduate:paper:2023-E:ed9d2f8c1d44", "graduate:paper:2023-E:3f818f083871", "graduate:paper:2023-E:eaa884b73993", "graduate:paper:2023-E:ab6183848dc6", "graduate:paper:2023-E:5c42b2bfe22e", "graduate:paper:2023-E:f7c0743f16ee", "graduate:paper:2023-E:9a48c6fe4537"], "Q3": ["graduate:paper:2023-E:3f4621bddfbb", "graduate:paper:2023-E:0b97a60eedbe", "graduate:paper:2023-E:455bbe350f9b", "graduate:paper:2023-E:ed9d2f8c1d44", "graduate:paper:2023-E:3f818f083871", "graduate:paper:2023-E:eaa884b73993", "graduate:paper:2023-E:ab6183848dc6", "graduate:paper:2023-E:5c42b2bfe22e", "graduate:paper:2023-E:f7c0743f16ee", "graduate:paper:2023-E:9a48c6fe4537"], "Q4": ["graduate:paper:2023-E:3f4621bddfbb", "graduate:paper:2023-E:9a48c6fe4537"]}

## 2023F｜强对流降水临近预报

- 范式：多变量雷达时空预测与定量降水估计
- 证据：题面 `graduate:problem_statement:2023-F:e948f6800868`；论文 10 篇；提名论文 0 篇。
- 问题本质：从 ZH、ZDR、KDP 提取微物理和运动信息，预测未来雷达回波、缓解极端回波模糊、估计降水并量化双偏振变量的增益。

### 逐问依赖

- Q1 用过去 10 帧三变量预测未来 10 帧 ZH
- Q2 在 Q1 上设计损失/生成机制保留强回波细节
- Q3 独立用 ZH、ZDR 估计降水量且不得使用 KDP
- Q4 对 Q1-Q3 做变量消融、贡献评价和融合优化

### 共识与路线

共同证据链：雷达质量控制和时空对齐 → 运动/微物理特征提取 → 时空预测网络或外推基线 → 极端感知损失/生成细化 → QPE 回归 → 双偏振消融和分强度验证。

- ConvLSTM/U-Net/Transformer 等判别式模型稳定但易平均化；GAN、扩散或多尺度损失能增强细节，却可能生成虚假强回波。
- 光流/外推是必要物理基线，深度模型应证明在增长消散场景的增益。
- QPE 可用 Z-R 扩展、回归/树模型或神经网络；物理公式可解释，数据驱动更灵活。
- 口径分歧：MSE/SSIM 与 CSI/POD/FAR 对极端降水的偏好不同；视觉更锐利不代表定量更准确，双偏振增益需按阈值和提前量报告。

### 假设与验证

- 训练测试事件独立 -> 若随机切帧会泄漏同一过程 -> 应按天气过程划分
- 双偏振变量质量稳定 -> 衰减/杂波会误导 -> 应质控
- 生成细节真实 -> 可能幻觉 -> 应做可靠性和质量守恒

必要检查：按过程时间外验证；多提前量指标；多阈值 CSI/POD/FAR；与持续性/光流基线比较；变量和损失消融；强降水可靠性与空间位移误差。

### 图表与写作

- 结构：输入—特征—预报—QPE—消融流程
- 机制：微物理变量和运动场
- 结果：多提前量回波组图与阈值指标
- 可信边界：极端样本、可靠性图和失败案例

- 每问先定义任务、输入输出和指标；预报图必须与定量表配对，Q4 只把独立消融和跨事件稳定增益写成双偏振贡献。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2023-F:5c24c2b41755", "graduate:paper:2023-F:af1baaf342a7", "graduate:paper:2023-F:0ed7c722e94b", "graduate:paper:2023-F:705431603c73", "graduate:paper:2023-F:8467e27c13df", "graduate:paper:2023-F:a2ba47b1f9d5", "graduate:paper:2023-F:d4884b88fc13", "graduate:paper:2023-F:31c43c38d60f", "graduate:paper:2023-F:b6f0112b1100", "graduate:paper:2023-F:8f756547e790"], "Q2": ["graduate:paper:2023-F:5c24c2b41755", "graduate:paper:2023-F:af1baaf342a7", "graduate:paper:2023-F:0ed7c722e94b", "graduate:paper:2023-F:705431603c73", "graduate:paper:2023-F:8467e27c13df", "graduate:paper:2023-F:a2ba47b1f9d5", "graduate:paper:2023-F:d4884b88fc13", "graduate:paper:2023-F:31c43c38d60f", "graduate:paper:2023-F:b6f0112b1100", "graduate:paper:2023-F:8f756547e790"], "Q3": ["graduate:paper:2023-F:5c24c2b41755", "graduate:paper:2023-F:af1baaf342a7", "graduate:paper:2023-F:0ed7c722e94b", "graduate:paper:2023-F:705431603c73", "graduate:paper:2023-F:8467e27c13df", "graduate:paper:2023-F:a2ba47b1f9d5", "graduate:paper:2023-F:d4884b88fc13", "graduate:paper:2023-F:31c43c38d60f", "graduate:paper:2023-F:b6f0112b1100", "graduate:paper:2023-F:8f756547e790"], "Q4": ["graduate:paper:2023-F:5c24c2b41755", "graduate:paper:2023-F:af1baaf342a7", "graduate:paper:2023-F:0ed7c722e94b", "graduate:paper:2023-F:705431603c73", "graduate:paper:2023-F:8467e27c13df", "graduate:paper:2023-F:a2ba47b1f9d5", "graduate:paper:2023-F:d4884b88fc13", "graduate:paper:2023-F:31c43c38d60f", "graduate:paper:2023-F:b6f0112b1100", "graduate:paper:2023-F:8f756547e790"]}

## 2024A｜风电场有功功率优化分配

- 范式：疲劳代理建模与鲁棒多机功率调度
- 证据：题面 `graduate:problem_statement:2024-A:c831960048c4`；论文 4 篇；提名论文 0 篇。
- 问题本质：在满足风场总功率指令的同时，利用低成本载荷估计均衡主轴和塔架疲劳，并在通信延迟、噪声及实时性下保持可行。

### 逐问依赖

- Q1 构造主轴/塔架疲劳损伤的低复杂度指标
- Q2 用风速和功率估计推力与扭矩，提供 Q1 所需载荷
- Q3 以 Q1-Q2 为代价和约束分配各机组有功功率
- Q4 在 Q3 上加入通信延迟与测量噪声，形成鲁棒实时策略

### 共识与路线

共同证据链：SCADA 清洗与工况分段 → 疲劳等效载荷或损伤代理 → 推力/扭矩估计 → 总功率守恒下多目标调度 → 滚动求解与延迟噪声仿真。

- 载荷估计可用物理代理、回归/树模型或神经网络；物理模型外推稳，数据模型精度高但需跨机组验证。
- 调度可用二次规划/MPC 获得实时性，也可用 GA/PSO 求非凸目标；后者必须证明时间预算。
- 延迟可做状态预测补偿，噪声可做滤波/鲁棒优化；只平滑信号不足以证明闭环鲁棒。
- 口径分歧：疲劳指标、总功率跟踪误差、机组可用功率和权重口径不同会改变最优分配；必须与均分或原策略同口径比较。

### 假设与验证

- 疲劳代理可替代雨流计数 -> 可能遗漏载荷循环 -> 应离线校验
- 机组独立无尾流耦合 -> 分配会改变下游风速 -> 应做尾流敏感性
- 延迟和噪声分布固定 -> 极端通信失效时不稳 -> 应做上界情景

必要检查：总功率与单机边界逐时满足；载荷代理对真实损伤的校准；基线对比；求解时间；延迟/噪声压力测试；跨机组与跨工况验证。

### 图表与写作

- 结构：风场调度闭环
- 机制：风速—功率—推力/扭矩—疲劳链
- 结果：单机功率与疲劳均衡图
- 可信边界：延迟噪声相图和求解时间

- 先证明低复杂度指标能代表疲劳，再进入优化；Q4 以闭环时间线解释延迟如何传播，结果同时报功率跟踪、疲劳和实时性。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2024-A:4850450d3388", "graduate:paper:2024-A:c971501020f4", "graduate:paper:2024-A:11a031ae7f6b", "graduate:paper:2024-A:daa73a15a67f"], "Q2": ["graduate:paper:2024-A:4850450d3388", "graduate:paper:2024-A:c971501020f4", "graduate:paper:2024-A:11a031ae7f6b", "graduate:paper:2024-A:daa73a15a67f"], "Q3": ["graduate:paper:2024-A:4850450d3388", "graduate:paper:2024-A:c971501020f4", "graduate:paper:2024-A:11a031ae7f6b", "graduate:paper:2024-A:daa73a15a67f"], "Q4": ["graduate:paper:2024-A:4850450d3388", "graduate:paper:2024-A:c971501020f4", "graduate:paper:2024-A:11a031ae7f6b", "graduate:paper:2024-A:daa73a15a67f"]}

## 2024B｜WLAN组网中网络吞吐量建模

- 范式：无线网络干扰、接入与吞吐预测
- 证据：题面 `graduate:problem_statement:2024-B:eb22bc2ce14e`；论文 4 篇；提名论文 0 篇。
- 问题本质：从拓扑、信号质量、业务负载和竞争接入机制估计多 AP/STA 网络吞吐，并解释干扰耦合与参数调整。

### 逐问依赖

- Q1 建立单链路速率或成功概率模型
- Q2 加入同频竞争和邻接干扰形成组网吞吐
- Q3 对多业务/多拓扑预测或校准
- Q4 优化信道、功率、关联或接入参数

### 共识与路线

共同证据链：链路与拓扑数据清洗 → SNR/MCS/成功率或学习型链路模型 → 干扰图和竞争域 → 吞吐聚合 → 仿真/实测校准 → 组网参数优化。

- 机理路线用 SINR、马尔可夫接入和冲突图，可解释；RF/XGBoost/神经网络能吸收复杂特征，但拓扑外泛化是关键。
- 全局图模型能表示干扰传播，特征拼接更简单；图模型需与节点重排和新规模测试。
- 优化可用图着色/整数规划或元启发式，吞吐最大化需同时约束公平与稳定。
- 口径分歧：吞吐是 PHY 速率、MAC 有效载荷还是端到端应用速率，是否计重传和协议开销，决定数值口径。

### 假设与验证

- 干扰可叠加且平稳 -> 突发竞争失效 -> 应分负载验证
- 训练拓扑代表新网络 -> 规模迁移可能失败 -> 应外推测试
- 节点流量饱和 -> 轻载吞吐模型偏差 -> 应加业务分布

必要检查：单链路上界；协议开销账本；解析/仿真/实测三方对照；新拓扑和新规模验证；公平性；优化前后可行与稳定。

### 图表与写作

- 结构：AP/STA 拓扑和干扰图
- 机制：SINR/MCS/竞争关系
- 结果：预测—实测吞吐及优化前后热图
- 可信边界：负载、规模和拓扑外误差

- 先定义吞吐口径和时间窗，再从链路到网络聚合；每个数据模型特征都要对应物理含义，优化结论附公平和拓扑适用边界。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2024-B:4a289c99bb42", "graduate:paper:2024-B:15ea1a64e74c", "graduate:paper:2024-B:8106f2c97188", "graduate:paper:2024-B:1845bbac5134"], "Q2": ["graduate:paper:2024-B:4a289c99bb42", "graduate:paper:2024-B:15ea1a64e74c", "graduate:paper:2024-B:8106f2c97188", "graduate:paper:2024-B:1845bbac5134"], "Q3": ["graduate:paper:2024-B:4a289c99bb42", "graduate:paper:2024-B:15ea1a64e74c", "graduate:paper:2024-B:8106f2c97188", "graduate:paper:2024-B:1845bbac5134"]}

## 2024C｜数据驱动下磁性元件的磁芯损耗建模

- 范式：波形特征、损耗预测与材料工况多目标优化
- 证据：题面 `graduate:problem_statement:2024-C:b5ce5cddbc63`；论文 4 篇；提名论文 0 篇。
- 问题本质：从温度、频率、材料和非正弦磁通波形预测磁芯损耗，分离因素与交互作用，并寻找低损耗、高传输能力工况。

### 逐问依赖

- Q1 识别和分类励磁波形并提取形状特征
- Q2 分析温度、材料、波形等因素及交互对损耗影响
- Q3 建立可跨工况的损耗预测模型并与经验公式比较
- Q4 联合损耗和传输能力优化材料及工况

### 共识与路线

共同证据链：异常值与单位处理 → 波形时频/统计特征 → 因素效应与交互 → Steinmetz 修正或机器学习回归 → 多目标优化与敏感性。

- 经验公式修正解释性强，但复杂波形和材料泛化有限；RF/XGBoost/SVR/神经网络预测强，需物理约束和外推测试。
- 波形可用人工峰度、斜率、频谱特征，也可用一维网络自动学习；人工特征更可解释。
- 优化可用 PSO/GA/NSGA-II；应把预测适用域和可制造条件作为约束。
- 口径分歧：损耗单位、对数变换、训练划分、材料编码和传输能力定义不同会改变误差及最优工况。

### 假设与验证

- 同一记录的相邻采样可随机拆分 -> 严重泄漏 -> 按实验工况分组
- 训练范围外仍可预测 -> 优化会外推 -> 适用域约束
- 经验公式误差独立 -> 残差可能有工况结构 -> 应画残差

必要检查：按工况/材料分组验证；与 Steinmetz 基线比较；残差随频率温度材料分层；特征和模型消融；预测区间；优化点近邻数据与扰动。

### 图表与写作

- 结构：数据—特征—预测—优化流程
- 机制：典型波形和因素交互图
- 结果：真实—预测、误差和 Pareto 前沿
- 可信边界：适用域、分材料误差与敏感性

- 先用波形图解释特征，再谈模型；预测和因素分析分开陈述，Q4 把最优解写成受模型适用域约束的候选工况。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2024-C:5a590f9a5a71", "graduate:paper:2024-C:70d872a1f738", "graduate:paper:2024-C:d1e04b4fbf2b", "graduate:paper:2024-C:d6f267f3c7b5"], "Q2": ["graduate:paper:2024-C:5a590f9a5a71", "graduate:paper:2024-C:70d872a1f738", "graduate:paper:2024-C:d1e04b4fbf2b", "graduate:paper:2024-C:d6f267f3c7b5"], "Q3": ["graduate:paper:2024-C:5a590f9a5a71", "graduate:paper:2024-C:70d872a1f738", "graduate:paper:2024-C:d1e04b4fbf2b", "graduate:paper:2024-C:d6f267f3c7b5"], "Q4": ["graduate:paper:2024-C:5a590f9a5a71", "graduate:paper:2024-C:70d872a1f738", "graduate:paper:2024-C:d1e04b4fbf2b", "graduate:paper:2024-C:d6f267f3c7b5"]}

## 2024D｜大数据驱动的地理综合问题

- 范式：多源地理数据融合、区域表征与空间推断
- 证据：题面 `graduate:problem_statement:2024-D:809d5f046809`；论文 4 篇；提名论文 0 篇。
- 问题本质：把不同尺度、坐标和语义的自然与人文地理数据对齐为区域特征，完成分类、综合评价或空间关系推断，并控制空间自相关造成的虚高。

### 逐问依赖

- Q1 完成多源地理数据清洗、坐标和尺度统一
- Q2 构建区域综合特征并识别空间类型/格局
- Q3 预测或解释目标地理属性
- Q4 将结果用于分区、评价或决策并验证空间稳定性

### 共识与路线

共同证据链：空间数据质控和重采样 → 特征构造与降维 → 聚类/分类/回归 → 地图化与空间统计 → 空间交叉验证和尺度敏感性。

- 综合指标/PCA/聚类透明，适合区域分型；RF/XGBoost/SVM 精度高但需解释；空间或图模型可利用邻接关系。
- 栅格统一便于计算却会受可变空间单元问题影响；行政单元分析易解释但边界效应明显。
- 普通随机验证会让相邻区域互泄漏，空间块验证更可信。
- 口径分歧：分区数、评价等级和重要因素随空间尺度、标准化、缺失填补和权重变化，地图边界不是自然真值。

### 假设与验证

- 同尺度重采样不损失信息 -> 小尺度现象被平滑 -> 做多尺度分析
- 邻近样本独立 -> 指标虚高 -> 空间块验证
- 综合权重稳定 -> 区域政策偏好改变结论 -> 敏感性

必要检查：坐标、分辨率和单位；空间块交叉验证；聚类稳定性；空间残差自相关；多尺度/权重敏感性；地图与原始典型区核验。

### 图表与写作

- 结构：多源图层和统一网格
- 机制：特征贡献与空间自相关
- 结果：分区/预测地图和典型区剖面
- 可信边界：空间残差、多尺度边界变化与不确定性地图

- 问题分析先写尺度和空间依赖，再选模型；每张地图必须带图例、尺度和不确定性解释，结论区分数据格局、模型推断和决策含义。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2024-D:aeb92dce70ae", "graduate:paper:2024-D:696720b81628", "graduate:paper:2024-D:bddb98b1da13", "graduate:paper:2024-D:1024773fe2b1"], "Q2": ["graduate:paper:2024-D:aeb92dce70ae", "graduate:paper:2024-D:696720b81628", "graduate:paper:2024-D:bddb98b1da13", "graduate:paper:2024-D:1024773fe2b1"], "Q3": ["graduate:paper:2024-D:aeb92dce70ae", "graduate:paper:2024-D:696720b81628", "graduate:paper:2024-D:bddb98b1da13", "graduate:paper:2024-D:1024773fe2b1"], "Q4": ["graduate:paper:2024-D:aeb92dce70ae", "graduate:paper:2024-D:696720b81628", "graduate:paper:2024-D:bddb98b1da13", "graduate:paper:2024-D:1024773fe2b1"]}

## 2024E｜高速公路应急车道紧急启用模型

- 范式：交通状态识别、拥堵预测与控制触发
- 证据：题面 `graduate:problem_statement:2024-E:3f957fcd69f9`；论文 4 篇；提名论文 0 篇。
- 问题本质：从视频或流量观测识别瓶颈形成，预测拥堵演化，并决定何时、何处启用应急车道，使通行改善覆盖安全和执法成本。

### 逐问依赖

- Q1 提取流量、速度、密度和事件状态
- Q2 识别/预测拥堵及持续时间
- Q3 构造应急车道启用触发和空间范围
- Q4 以交通流、排队、安全和误触发同口径评价

### 共识与路线

共同证据链：视频/检测器数据清洗 → 交通流状态和瓶颈识别 → 短时预测 → 触发阈值或控制优化 → 微观/宏观仿真与策略前后比较。

- 基本图/排队模型可解释拥堵形成；LSTM、SVM、树模型能预测复杂状态但需时间外验证。
- 固定阈值易部署但情景适应差；MPC/PSO 等动态控制更灵活但计算和传感依赖高。
- 车道级视觉识别提供事件证据，交通流模型提供网络后果，二者应串联。
- 口径分歧：通行能力、平均速度、排队长度和总延误不同指标可能给相反结论；安全事件未计入时不能只追求速度。

### 假设与验证

- 驾驶员完全遵循启用指令 -> 真实渗透率有限 -> 应分情景
- 应急车道无故障车辆 -> 安全风险被忽略 -> 保留最低安全容量
- 历史车流代表突发事件 -> 应做事故/恶劣天气压力测试

必要检查：流量守恒与单位；时间外预测；触发迟滞防频繁开关；策略前后同一需求；不同服从率和事故情景；安全约束和误触发率。

### 图表与写作

- 结构：路段、检测点和瓶颈示意
- 机制：速度—密度—流量与排队波
- 结果：启用前后时空速度图
- 可信边界：服从率、事故和阈值敏感性

- 先定义拥堵状态和触发事件，再写预测与控制；结果需展示时间线，说明提前多久、启用多长、改善什么以及安全代价。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2024-E:c519ccae1b28", "graduate:paper:2024-E:ec78e4a82565", "graduate:paper:2024-E:68cdac7fa58e", "graduate:paper:2024-E:9fa5ec441502"], "Q2": ["graduate:paper:2024-E:c519ccae1b28", "graduate:paper:2024-E:ec78e4a82565", "graduate:paper:2024-E:68cdac7fa58e", "graduate:paper:2024-E:9fa5ec441502"], "Q3": ["graduate:paper:2024-E:c519ccae1b28", "graduate:paper:2024-E:ec78e4a82565", "graduate:paper:2024-E:68cdac7fa58e", "graduate:paper:2024-E:9fa5ec441502"], "Q4": ["graduate:paper:2024-E:c519ccae1b28", "graduate:paper:2024-E:ec78e4a82565", "graduate:paper:2024-E:68cdac7fa58e", "graduate:paper:2024-E:9fa5ec441502"]}

## 2024F｜X射线脉冲星光子到达时间建模

- 范式：稀疏光子事件的周期估计与到达时刻反演
- 证据：题面 `graduate:problem_statement:2024-F:b9f7eb8fa175`；论文 4 篇；提名论文 0 篇。
- 问题本质：从含背景噪声的稀疏光子事件流恢复脉冲轮廓、频率和相位，并估计稳定、带不确定度的脉冲到达时间。

### 逐问依赖

- Q1 清洗光子事件并估计周期/频率
- Q2 折叠事件构造脉冲轮廓和模板
- Q3 通过相关或似然估计 TOA 并修正漂移
- Q4 评价不同计数率、噪声和时间窗下精度

### 共识与路线

共同证据链：事件时间校正和背景处理 → 周期搜索 → 相位折叠 → 模板匹配/最大似然 → TOA 序列拟合 → 蒙特卡罗或分段稳定性。

- FFT/周期图速度快但稀疏事件需分箱；Z²、epoch folding 或事件似然保留更多信息。
- 互相关模板匹配直观，Poisson 最大似然更符合计数统计；模板质量决定偏差。
- 固定窗口平滑但时间分辨率低，自适应窗口需在方差和跟踪间权衡。
- 口径分歧：不同时间基准、分箱宽度、模板和相位零点会改变 TOA；精度必须附时间单位和置信区间。

### 假设与验证

- 光子计数独立泊松 -> 探测器死时间可能破坏 -> 应检查
- 脉冲轮廓稳定 -> 能段/时间变化会偏移模板 -> 分段比较
- 背景平稳 -> 空间环境变化失效 -> 自适应估计

必要检查：时间单位和重心校正；注入信号回收；分箱/窗口敏感性；不同周期估计互证；Poisson 置信区间；低计数和高背景压力测试。

### 图表与写作

- 结构：事件处理到 TOA 流程
- 机制：周期谱和相位折叠轮廓
- 结果：模板匹配与 TOA 残差
- 可信边界：计数率、背景和窗口误差曲线

- 正文沿事件—周期—轮廓—相位—TOA 展开；每个时间值都交代基准、单位和不确定度，结论不以漂亮轮廓替代到达时刻误差。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2024-F:524e70a4d611", "graduate:paper:2024-F:414aa98ed580", "graduate:paper:2024-F:cb62b69d7980", "graduate:paper:2024-F:7cdf9715fc23"], "Q2": ["graduate:paper:2024-F:524e70a4d611", "graduate:paper:2024-F:414aa98ed580", "graduate:paper:2024-F:cb62b69d7980", "graduate:paper:2024-F:7cdf9715fc23"], "Q3": ["graduate:paper:2024-F:524e70a4d611", "graduate:paper:2024-F:414aa98ed580", "graduate:paper:2024-F:cb62b69d7980", "graduate:paper:2024-F:7cdf9715fc23"], "Q4": ["graduate:paper:2024-F:524e70a4d611", "graduate:paper:2024-F:414aa98ed580", "graduate:paper:2024-F:cb62b69d7980", "graduate:paper:2024-F:7cdf9715fc23"]}

## 2025A｜通用神经网络处理器下的核内调度问题

- 范式：计算图分块、片上存储与多资源调度
- 证据：题面 `graduate:problem_statement:2025-A:3fcc53e26081`；论文 4 篇；提名论文 0 篇。
- 问题本质：把神经网络算子分解为受计算单元、片上存储、带宽和依赖约束的任务，在减少搬运和空闲的同时缩短核内执行时间。

### 逐问依赖

- Q1 建立算子/任务 DAG 与硬件资源模型
- Q2 在固定映射下优化任务顺序和并行执行
- Q3 联合分块、缓存驻留和数据搬运
- Q4 扩展多核或复杂网络并优化延迟、能耗和利用率

### 共识与路线

共同证据链：计算图和张量生命周期 → 任务分块与依赖 → 计算/存储/带宽资源约束 → 列表调度、整数规划或元启发式 → 周期级仿真和基线比较。

- MILP/约束规划适合小图并提供最优基准；列表调度、关键路径、禁忌/退火/遗传适合大图。
- 先分块再调度实现简单但可能错过数据复用；联合优化质量高却搜索维度巨大。
- 图神经或强化学习策略可学习调度，但需与经典启发式在新网络和新硬件上比较。
- 口径分歧：周期、吞吐和能耗是否计入 DMA、同步、双缓冲和尾块，决定方案排名；理论并行度不能等同实际利用率。

### 假设与验证

- 计算/搬运时间可线性叠加 -> 争用与流水重叠可能改变 -> 周期仿真
- 任务可任意切分 -> 尾块和对齐开销被忽略 -> 加入离散约束
- 硬件参数固定准确 -> 实测差异 -> 做扰动校准

必要检查：DAG 依赖和张量生命周期；各时刻资源不超限；内存峰值；小实例最优解；周期级仿真；新网络/尺寸泛化；调度开销和求解时间。

### 图表与写作

- 结构：算子 DAG 与硬件资源图
- 机制：张量驻留和时间—资源甘特图
- 结果：延迟、带宽、利用率和能耗对比
- 可信边界：网络规模、存储容量和带宽敏感性

- 先定义硬件时间口径，再把算子转换成任务；正文用甘特图打开并行和等待机制，结果同时报告计算、搬运、空闲和调度开销。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2025-A:eb15efe91f40", "graduate:paper:2025-A:d26284fb65c7", "graduate:paper:2025-A:becbc09c579f", "graduate:paper:2025-A:186cc0cdae39"], "Q2": ["graduate:paper:2025-A:eb15efe91f40", "graduate:paper:2025-A:d26284fb65c7", "graduate:paper:2025-A:becbc09c579f", "graduate:paper:2025-A:186cc0cdae39"], "Q3": ["graduate:paper:2025-A:eb15efe91f40", "graduate:paper:2025-A:d26284fb65c7", "graduate:paper:2025-A:becbc09c579f", "graduate:paper:2025-A:186cc0cdae39"]}

## 2025B｜无线通信系统链路速率建模

- 范式：信道质量到链路速率的概率预测与自适应
- 证据：题面 `graduate:problem_statement:2025-B:a1bae6ee69ad`；论文 3 篇；提名论文 0 篇。
- 问题本质：从信道测量、干扰、编码调制和重传信息预测可实现速率或块错误率，并选择兼顾吞吐与可靠性的链路参数。

### 逐问依赖

- Q1 清洗并分析信道质量与实际速率关系
- Q2 建立 BLER/速率映射模型
- Q3 处理多场景、时变或不确定信道
- Q4 用预测分布完成 MCS/资源选择并验证收益

### 共识与路线

共同证据链：信道和速率口径统一 → 物理特征与统计关系 → 回归/分类或机理映射 → 概率校准 → 链路自适应决策 → 时间外与场景外验证。

- Shannon/有效 SINR 和逻辑 BLER 曲线可解释；树模型/神经网络能吸收非线性和交互。
- 点预测简单但无法控制可靠性；分位数/概率模型更适合 MCS 决策。
- 离线最优 MCS 是上界，在线策略需考虑反馈延迟和切换成本。
- 口径分歧：速率是否为物理层、MAC 有效或应用吞吐，以及 BLER 目标、重传和带宽口径不同会导致不可比。

### 假设与验证

- 反馈信道即时 -> 延迟会造成过时 CSI -> 应做时间偏移
- 训练场景覆盖部署 -> 新干扰分布失效 -> 场景外验证
- 样本独立 -> 同一链路连续记录泄漏 -> 按会话划分

必要检查：单位和速率上界；按会话时间外验证；BLER 概率校准；场景/用户分层误差；反馈延迟；在线吞吐和可靠性双验收。

### 图表与写作

- 结构：CSI—BLER/速率—MCS 决策闭环
- 机制：信道质量与成功率曲线
- 结果：预测—实测与策略吞吐
- 可信边界：场景外、延迟和可靠性图

- 先定义速率和可靠性目标，再说明预测怎样进入决策；结论必须同时给吞吐增益、失败率和适用信道范围。

逐问证据（逐问级绑定）：{"Q1": ["graduate:paper:2025-B:150cea22b1aa", "graduate:paper:2025-B:29ae1e65a24d", "graduate:paper:2025-B:31f63f2fc4de"], "Q2": ["graduate:paper:2025-B:150cea22b1aa", "graduate:paper:2025-B:29ae1e65a24d", "graduate:paper:2025-B:31f63f2fc4de"], "Q3": ["graduate:paper:2025-B:150cea22b1aa", "graduate:paper:2025-B:29ae1e65a24d", "graduate:paper:2025-B:31f63f2fc4de"], "Q4": ["graduate:paper:2025-B:150cea22b1aa"]}

## 2025C｜围岩裂隙精准识别与三维模型重构

- 范式：钻孔图像分割、裂隙参数反演与网络重构
- 证据：题面 `graduate:problem_statement:2025-C:d040a3b09a8a`；论文 5 篇；提名论文 0 篇。
- 问题本质：从孔壁展开图识别裂隙像素，拟合正弦迹线和复杂形态，跨钻孔推断裂隙面连通并构建带不确定度的三维网络。

### 逐问依赖

- Q1 像素级分割裂隙与干扰
- Q2 对正弦状裂隙拟合倾角、倾向等参数
- Q3 对分叉、交叉和不规则裂隙进行定量描述
- Q4 将 Q2-Q3 的几何和位置跨孔匹配，分析连通并三维重构

### 共识与路线

共同证据链：图像增强与标注 → 传统/深度分割 → 连通域和曲线提取 → 正弦/几何鲁棒拟合 → 裂隙属性聚类与跨孔匹配 → 三维面片/网络重构。

- 阈值、形态学和传统特征可解释、对标注需求低；U-Net/YOLO/迁移学习对复杂纹理更强但需防域偏移。
- 正弦拟合可用最小二乘/RANSAC/智能优化；RANSAC 抗离群，元启发式需给收敛。
- 三维连通可用几何相交、图模型或概率匹配；确定性硬连接容易过度推断。
- 口径分歧：分割精度、裂隙数、倾角和连通率受图像尺度、裂隙宽度阈值、曲线拼接和跨孔容差影响。

### 假设与验证

- 展开图几何无畸变 -> 深度和拼接误差会偏移 -> 应校正
- 迹线对应平面裂隙 -> 弯曲裂隙不成立 -> Q3 单独处理
- 跨孔相近参数即同一裂隙 -> 可能误连 -> 概率和不确定区间

必要检查：像素 IoU/召回和裂隙级指标；参数仿真回收；RANSAC/拟合残差；跨孔匹配消融；三维几何一致性；连通概率和人工典型案例。

### 图表与写作

- 结构：孔壁展开到三维坐标流程
- 机制：分割掩膜、中心线和正弦拟合
- 结果：裂隙参数表与三维网络
- 可信边界：残差、匹配概率和重构不确定性

- 逐问保持像素—曲线—裂隙面—网络的对象升级；每层交代坐标变换和误差如何传到下一层，三维图旁必须说明不可确定连接。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2025-C:40a3c73c0409", "graduate:paper:2025-C:f3f0fc9a1a7f", "graduate:paper:2025-C:dde3aad6c5f6", "graduate:paper:2025-C:eaf6375148b2", "graduate:paper:2025-C:a69f6c1c55ae"], "Q2": ["graduate:paper:2025-C:40a3c73c0409", "graduate:paper:2025-C:f3f0fc9a1a7f", "graduate:paper:2025-C:dde3aad6c5f6", "graduate:paper:2025-C:eaf6375148b2", "graduate:paper:2025-C:a69f6c1c55ae"], "Q3": ["graduate:paper:2025-C:40a3c73c0409", "graduate:paper:2025-C:f3f0fc9a1a7f", "graduate:paper:2025-C:dde3aad6c5f6", "graduate:paper:2025-C:eaf6375148b2", "graduate:paper:2025-C:a69f6c1c55ae"], "Q4": ["graduate:paper:2025-C:40a3c73c0409", "graduate:paper:2025-C:f3f0fc9a1a7f", "graduate:paper:2025-C:dde3aad6c5f6", "graduate:paper:2025-C:eaf6375148b2", "graduate:paper:2025-C:a69f6c1c55ae"]}

## 2025D｜低空湍流监测及最优航路规划

- 范式：多源气象融合、湍流预报与风险航路规划
- 证据：题面 `graduate:problem_statement:2025-D:2f9e363265c8`；论文 2 篇；提名论文 0 篇。
- 问题本质：把不同设备、分辨率和物理指标的观测校准到统一三维湍流强度场，再用数值预报或短时外推预测风险，规划兼顾湍流与航程的时空航路。

### 逐问依赖

- Q1 用风廓线+微波辐射计建可靠模型 a，再蒸馏仅风廓线模型 b
- Q2 融合自动站、风廓线和多普勒雷达建立 100m×50m 三维模型 c
- Q3 以 c 校准数值预报模型 d 并预报 05-08 时；另建仅观测外推模型 e 预报 05-06 时，两类预报分别驱动航路规划

### 共识与路线

共同证据链：设备质控与时空坐标统一 → TKE/耗散率/Richardson 等指标构造 → a-b 教师校准 → 多源三维融合 c → 数值预报诊断 d 与观测外推 e → 时变风险图上的路径优化。

- 物理诊断指标外推合理但分辨率受数据限制；树模型/神经网络可学习 b 对 a、d 对 c 的映射，需防把插值当真实湍流。
- 三维融合可用客观分析/克里金、加权插值或学习模型；权重应随设备覆盖与天气状态变化。
- 路径可用 A*/Dijkstra、蚁群或多目标优化；静态最短路不足以处理随时间变化的风险场。
- 口径分歧：不同湍流强度指标不能直接数值合并，必须先归一或标定；航路最优取决于风险积分、最大风险、航程和禁飞区权重。

### 假设与验证

- a 可作真值 -> 其本身也有仪器和公式误差 -> 应写参考标准而非绝对真值
- 插值到 100m 即具有 100m 信息 -> 伪分辨率 -> 报有效分辨率
- 飞行器不受风场影响且速度固定 -> 时空路径偏差 -> 应做时间同步

必要检查：设备时间空间对齐；留站/留时验证；a-b、c-d、c-e 分层误差；晴空/降水分情景；物理边界和空间平滑；路径逐时可行与风险；预报不确定性鲁棒路径。

### 图表与写作

- 结构：设备覆盖、a-e 模型和航路闭环
- 机制：垂直廓线与多源权重
- 结果：三维湍流场、预报差异和航路
- 可信边界：留站误差、不确定性场和风险—航程前沿

- 以 a→b、观测→c、c→d/e 的教师—学生链组织正文；每次插值都说明信息来源和有效分辨率，路径段逐时验收风险而非只画空间线。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2025-D:ac2d33da18fa", "graduate:paper:2025-D:95743f6ef8d6"], "Q2": ["graduate:paper:2025-D:ac2d33da18fa", "graduate:paper:2025-D:95743f6ef8d6"], "Q3": ["graduate:paper:2025-D:ac2d33da18fa", "graduate:paper:2025-D:95743f6ef8d6"]}

## 2025E｜高速列车轴承智能故障诊断问题

- 范式：振动信号表征、迁移诊断与可解释学习
- 证据：题面 `graduate:problem_statement:2025-E:7a4299f7d1ea`；论文 3 篇；提名论文 0 篇。
- 问题本质：从源域标注轴承信号学习稳健故障特征，适配目标列车工况和设备域偏移，输出带置信度和机理解释的故障类别。

### 逐问依赖

- Q1 完成源域信号清洗、分段和时频特征
- Q2 建立并验证源域故障分类基线
- Q3 识别源/目标域差异并进行迁移或域适应
- Q4 对目标样本诊断并解释关键频带、冲击或模型决策

### 共识与路线

共同证据链：采样率/转速和分段统一 → 去噪与时频变换 → 统计/包络/小波特征或端到端网络 → 源域分类 → 域对齐/迁移 → 目标置信度和可解释性。

- 手工时域、频域、包络特征+SVM/RF 小样本稳且有机理；CNN/Transformer 自动特征强但易学设备特征。
- 迁移可用特征归一、MMD/CORAL、对抗域适应或微调；无目标标签时不能用目标测试结果调参。
- 解释可用频带消融、Grad-CAM/SHAP，必须回到轴承故障特征频率。
- 口径分歧：随机切片会让同一原始记录进入训练和测试造成虚高；准确率、宏 F1 与目标域无标签评估口径不同。

### 假设与验证

- 切片独立 -> 数据泄漏 -> 按原始工况文件分组
- 源目标标签空间一致 -> 未知故障会被强制分类 -> 增加拒识
- 转速稳定 -> 特征频率漂移 -> 阶次跟踪或归一

必要检查：按原始记录/工况分组验证；宏 F1 和混淆矩阵；转速/负载分层；迁移前后域距离；无目标标签调参边界；拒识与概率校准；机理特征对应。

### 图表与写作

- 结构：源域—域适应—目标诊断流程
- 机制：时频图、包络谱和域嵌入
- 结果：混淆矩阵与目标概率
- 可信边界：工况外误差、校准和未知类拒识

- 数据划分规则要在模型前写清；结果分源域、迁移增益、目标置信和解释四层，结论不把目标伪标签当真实准确率。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2025-E:e86c6a47cc19", "graduate:paper:2025-E:fd49424d2937", "graduate:paper:2025-E:b4f1d4ea6551"], "Q2": ["graduate:paper:2025-E:e86c6a47cc19", "graduate:paper:2025-E:fd49424d2937", "graduate:paper:2025-E:b4f1d4ea6551"], "Q3": ["graduate:paper:2025-E:e86c6a47cc19", "graduate:paper:2025-E:fd49424d2937", "graduate:paper:2025-E:b4f1d4ea6551"], "Q4": ["graduate:paper:2025-E:e86c6a47cc19", "graduate:paper:2025-E:fd49424d2937", "graduate:paper:2025-E:b4f1d4ea6551"]}

## 2025F｜江南古典园林的美学特征建模

- 范式：空间句法、视域序列与多指标美学评价
- 证据：题面 `graduate:problem_statement:2025-F:e8d5edea0e3c`；论文 4 篇；提名论文 0 篇。
- 问题本质：把游线、视域、空间开合、尺度、要素构成和布局关系转成可重复计算的美学指标，解释移步异景、小中见大和园林相似性。

### 逐问依赖

- Q1 基于路径网络与视域变化量化移步异景的趣味性
- Q2 结合空间开合、遮挡、尺度层次和可见性量化小中见大的幻境感
- Q3 复用 Q1-Q2 特征并加入要素/拓扑，建立有法无式的相似度与分类

### 共识与路线

共同证据链：地图矢量化与要素标注 → 路径图和代表游线 → 视域/景观序列特征 → 空间开合与层次指标 → 综合评价和相似度 → 专家/游客或扰动验证。

- 空间句法和图论解释游线结构；GIS/视域分析直接刻画可见性；图像/语义特征补充景观构成。
- 固定推荐游线便于比较但带主观性；全路径采样更客观但计算大。
- 相似度可用加权距离、聚类或图匹配；只比面积和要素比例会丢失布局关系。
- 口径分歧：最优游线、权重和园林相似排序受入口、步长、视点高度、遮挡模型和专家偏好影响，不能当唯一审美真值。

### 假设与验证

- 二维地图足以代表视景 -> 高度、植被季相被忽略 -> 限定或加入三维
- 游客按单一路径匀速 -> 行为偏差 -> 多路径/停留情景
- 综合权重代表审美 -> 群体差异 -> 专家与数据双验证

必要检查：矢量化和尺度校准；路径连通与采样稳定；视域算法典型点核验；步长/入口/视点敏感性；权重和聚类稳定性；专家/游客一致性；相似度留一验证。

### 图表与写作

- 结构：园林要素、路径和视域图层
- 机制：沿游线视域开合序列
- 结果：三类美学指标雷达/地图与相似网络
- 可信边界：参数扰动、不同游线和主观一致性

- 先把抽象美学词拆成可观察机制，再定义指标；正文沿游线顺序讲视觉变化，图表用于证明空间叙事，结论保留审美多解性。

逐问证据（题级绑定，各问证据同集合）：{"Q1": ["graduate:paper:2025-F:77892f7dcdfe", "graduate:paper:2025-F:20b9a3fbb48f", "graduate:paper:2025-F:b18c1289e4f1", "graduate:paper:2025-F:861c3d805408"], "Q2": ["graduate:paper:2025-F:77892f7dcdfe", "graduate:paper:2025-F:20b9a3fbb48f", "graduate:paper:2025-F:b18c1289e4f1", "graduate:paper:2025-F:861c3d805408"], "Q3": ["graduate:paper:2025-F:77892f7dcdfe", "graduate:paper:2025-F:20b9a3fbb48f", "graduate:paper:2025-F:b18c1289e4f1", "graduate:paper:2025-F:861c3d805408"]}
