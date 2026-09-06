# 华数杯图表能力强化包

> 图表是区分国一与国二的关键。本包提供按题型的图表模板 + 可运行代码。
> 基于 18 篇优秀论文蒸馏。加载时机：stage 5/8 图表任务，"画图"/"美化图"/"规划图表"时。

---

## 0. 通用样式配置（所有图前必跑）

```python
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

# 国一论文级样式配置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 中文
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3

# 国一配色: 避免彩虹色; 0.7.4 起以 skill 仓库 templates/figures/style/palettes.py 为准 (academic_blue)
import sys
from pathlib import Path
try:
    _style_dir = Path(__file__).resolve().parents[1] / 'templates' / 'figures' / 'style'
    sys.path.insert(0, str(_style_dir))
    from palettes import get_palette
    CHAMPION_PALETTE = get_palette('academic_blue')  # champion_palette 为其向后兼容别名
except Exception:  # 导入失败或 __file__ 不可用 (片段在工作区独立运行) 时用回退副本
    # 回退副本, 以 templates/figures/style/palettes.py 为准
    CHAMPION_PALETTE = ['#1F4E79', '#2E86AB', '#F18F01', '#C73E1D', '#3B8C6E', '#6C757D']
mpl.rcParams['axes.prop_cycle'] = mpl.cycler(color=CHAMPION_PALETTE)
```

> **0.7.4 过渡说明**: 配色已统一到 `references/color_typology.md` 与 `templates/figures/style/palettes.py`。
> `CHAMPION_PALETTE` 保留为 `academic_blue` 的向后兼容别名（`palettes.get_palette('champion_palette')` 等价生效）;
> 色值历史来源为历史竞赛工作区实战验证配色, 原 `#A23B72` 已由主色 `#1F4E79` 取代并补中性灰 `#6C757D`。
> 新代码请直接 `apply_palette('academic_blue')` 并加载 `templates/figures/style/mathmodel.mplstyle`, 下方 14 段代码模板暂保持原样（过渡方案见 color_typology.md §7）。

> **1.1.0 指引**: 设计令牌统一出口 `references/design_tokens.md`（色板/中性色/字号/间距令牌，脚本禁止另立数值）；流程/机理/路线图优先使用 drawio 可编辑模板 `templates/figures/scripts/render_drawio_pack.py`（roadmap / framework / flow3col / stageflow / swimlane / mechanism 共 6 模板，draw.io 打开微调后导出 PNG/PDF/SVG）；英文投稿/答辩可选四套真期刊色板 npg / aaas / lancet / nejm（`palettes.py` 1.1.0，经 `figkit.load_palette()` 取用，色值以该文件为准）。

---

## 1. A 题图表模板（物理工程）

### 1.1 物理示意图（矢量，必备）

A 题物理示意图必须矢量输出（PDF/SVG），标注尺寸/角度/坐标系。

```python
fig, ax = plt.subplots(figsize=(8, 6))
# 示例: 机械臂连杆示意
from matplotlib.patches import FancyArrowPatch, Rectangle
# 画连杆
for i in range(6):
    ax.plot([x[i], x[i+1]], [y[i], y[i+1]], 'k-', lw=3)
    ax.plot(x[i], y[i], 'ko', markersize=10)
    ax.annotate(f'关节{i+1}', (x[i], y[i]), textcoords='offset points', xytext=(10,5))
# 标注角度
ax.annotate('', xy=(x2,y2), xytext=(x1,y1),
            arrowprops=dict(arrowstyle='->', lw=2, color='red'))
ax.set_xlabel('X (mm)'); ax.set_ylabel('Y (mm)')
ax.set_title('图X 六自由度机械臂位姿示意图')
ax.set_aspect('equal')
plt.savefig('fig_robot_schematic.pdf')  # 矢量!
```

### 1.2 3D 轨迹/曲面可视化（加分项）

```python
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')
ax.plot(xs, ys, zs, linewidth=2, label='末端轨迹')
ax.scatter(xs[0], ys[0], zs[0], color='green', s=100, label='起点')
ax.scatter(xs[-1], ys[-1], zs[-1], color='red', s=100, label='终点')
ax.set_xlabel('X (mm)'); ax.set_ylabel('Y (mm)'); ax.set_zlabel('Z (mm)')
ax.set_title('图X 末端执行器三维运动轨迹')
ax.legend()
plt.savefig('fig_3d_trajectory.pdf')
```

### 1.3 收敛曲线（算法性能）

```python
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(range(len(fitness)), fitness, linewidth=2, color=CHAMPION_PALETTE[0])
ax.axhline(y=best, color='r', linestyle='--', label=f'最优值 {best:.4f}')
ax.set_xlabel('迭代次数'); ax.set_ylabel('目标函数值')
ax.set_title('图X 差分进化算法收敛曲线')
ax.legend()
plt.savefig('fig_convergence.pdf')
```

### 1.4 优化前后对比（证明改进有效）

```python
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].plot(before_x, before_y, 'r-', lw=2); axes[0].set_title('(a) 优化前')
axes[1].plot(after_x, after_y, 'g-', lw=2); axes[1].set_title('(b) 优化后')
for ax in axes:
    ax.set_xlabel('时间 (s)'); ax.set_ylabel('温度 (℃)')
plt.savefig('fig_compare.pdf')
```

---

## 2. B 题图表模板（运筹优化）

### 2.1 算法流程图（graphviz，必备）

```python
from graphviz import Digraph
dot = Digraph(comment='算法流程')
dot.attr(rankdir='TB', size='8,10')
dot.node('S', '开始'); dot.node('I', '初始化种群')
dot.node('E', '评估适应度'); dot.node('C', '交叉变异')
dot.node('J', '判断收敛?'); dot.node('O', '输出最优解')
dot.edges(['SI','IE','EC','CJ'])
dot.edge('J', 'E', label='否'); dot.edge('J', 'O', label='是')
dot.render('fig_algo_flow', format='pdf', cleanup=True)
```

### 2.2 帕累托前沿（多目标必备）

```python
fig, ax = plt.subplots(figsize=(8, 6))
ax.scatter(pareto_f1, pareto_f2, c=CHAMPION_PALETTE[0], s=50, label='Pareto 最优解')
ax.scatter(all_f1, all_f2, c='lightgray', s=10, alpha=0.3, label='所有解')
ax.scatter(chosen_f1, chosen_f2, c='red', s=200, marker='*', label='决策点')
ax.set_xlabel('目标1: 总线长'); ax.set_ylabel('目标2: 最大密度')
ax.set_title('图X 双目标优化帕累托前沿')
ax.legend()
plt.savefig('fig_pareto.pdf')
```

### 2.3 灵敏度九联图（国一加分，2023_B_2 风格）

```python
fig, axes = plt.subplots(3, 3, figsize=(15, 12))
params = ['alpha', 'beta', 'gamma', 'delta', 'eps', 'pop', 'iter', 'pc', 'pm']
for ax, param in zip(axes.flat, params):
    values, results = sensitivity_data[param]
    ax.plot(values, results, 'o-', linewidth=2)
    ax.axvline(x=default[param], color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel(param); ax.set_ylabel('目标值')
fig.suptitle('图X 九参数灵敏度分析', fontsize=14)
plt.tight_layout()
plt.savefig('fig_sensitivity_9.pdf')
```

### 2.4 基准函数收敛对比（B 题国一杀手锏）

```python
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(sa_conv, label=f'SA ({sa_iter}次)', color=CHAMPION_PALETTE[1])
ax.plot(pso_conv, label=f'PSO ({pso_iter}次)', color=CHAMPION_PALETTE[2])
ax.plot(sapso_conv, label=f'SA-PSO ({sapso_iter}次)', color=CHAMPION_PALETTE[0])
ax.axhline(y=0, color='k', linestyle='--', alpha=0.3)
ax.set_xlabel('迭代次数'); ax.set_ylabel('Ackley 函数值')
ax.set_title('图X Ackley 基准函数算法收敛对比')
ax.legend()
plt.savefig('fig_benchmark_ackley.pdf')
```

### 2.5 布局/资源分配可视化

```python
fig, ax = plt.subplots(figsize=(10, 8))
# VLSI 布局
for cell in cells:
    rect = plt.Rectangle((cell.x, cell.y), cell.w, cell.h,
                          linewidth=1, edgecolor='black', facecolor=cell.color, alpha=0.7)
    ax.add_patch(rect)
ax.set_xlim(0, chip_w); ax.set_ylim(0, chip_h)
ax.set_xlabel('X 坐标'); ax.set_ylabel('Y 坐标')
ax.set_title('图X VLSI 单元布局优化结果')
plt.savefig('fig_layout.pdf')
```

---

## 3. C 题图表模板（数据评价/规划）

### 3.1 相关性热力图（探索性分析必备）

```python
import seaborn as sns
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(df.corr(), annot=True, fmt='.2f', cmap='RdBu_r', center=0,
            square=True, ax=ax, cbar_kws={'label': '相关系数'})
ax.set_title('图X 指标相关性热力图')
plt.savefig('fig_corr_heatmap.pdf')
```

### 3.2 地图类可视化（2024C 杀手锏）

```python
import folium
from folium.plugins import MarkerCluster

m = folium.Map(location=[35, 105], zoom_start=4)
marker_cluster = MarkerCluster().add_to(m)
for city in top50_cities:
    folium.Marker(
        location=[city.lat, city.lon],
        popup=f"{city.name}: {city.score:.2f}",
        icon=folium.Icon(color='red' if city.rank<=10 else 'orange' if city.rank<=30 else 'blue')
    ).add_to(marker_cluster)
# 游玩路线
folium.PolyLine(route_coords, color='blue', weight=3, opacity=0.7).add_to(m)
m.save('fig_china_map.html')
```

### 3.3 雷达图（多维评价）

```python
from math import pi
fig = plt.figure(figsize=(8, 8))
ax = fig.add_subplot(111, polar=True)
categories = ['交通','环保','人文','美食','气候','消费']
N = len(categories)
angles = [n / float(N) * 2 * pi for n in range(N)] + [0]
for city, values in [('成都', chengdu_vals), ('大理', dali_vals)]:
    values = values + [values[0]]
    ax.plot(angles, values, linewidth=2, label=city)
    ax.fill(angles, values, alpha=0.15)
ax.set_xticks(angles[:-1]); ax.set_xticklabels(categories)
ax.set_title('图X TOP2 城市多维评价雷达图')
ax.legend(loc='upper right')
plt.savefig('fig_radar.pdf')
```

### 3.4 3D 响应曲面（参数优化）

```python
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')
X, Y = np.meshgrid(w1_range, w2_range)
ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.8)
ax.scatter(best_w1, best_w2, best_obj, color='red', s=100, label='最优解')
ax.set_xlabel('权重 w1'); ax.set_ylabel('权重 w2'); ax.set_zlabel('目标值')
ax.set_title('图X 双参数权重响应曲面')
plt.savefig('fig_surface_3d.pdf')
```

### 3.5 p 值热力图（统计检验，2025C 风格）

```python
fig, ax = plt.subplots(figsize=(8, 6))
metrics = ['深睡眠比例','睡眠效率','入睡时间','觉醒次数']
groups = ['对照组','日间模式','夜间模式']
p_matrix = np.array([[0.5, 0.009, 0.02, 0.15],[0.3, 0.04, 0.008, 0.25]])
sns.heatmap(p_matrix, annot=True, fmt='.3f', cmap='RdYlGn_r',
            xticklabels=metrics, yticklabels=groups, ax=ax,
            cbar_kws={'label': 'p 值'}, vmin=0, vmax=0.1)
ax.set_title('图X 各指标统计检验 p 值热力图 (<0.05 显著)')
plt.savefig('fig_pvalue_heatmap.pdf')
```

### 3.6 混淆矩阵（分类结果）

```python
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
cm = confusion_matrix(y_true, y_pred, labels=['安静型','中等型','矛盾型'])
disp = ConfusionMatrixDisplay(cm, display_labels=['安静型','中等型','矛盾型'])
disp.plot(cmap='Blues', values_format='d')
plt.title('图X 婴儿行为三分类混淆矩阵')
plt.savefig('fig_confusion.pdf')
```

---

## 4. 图表质检清单（交付前必查）

### A 题图表
- [ ] 物理示意图为矢量图（PDF/SVG）。
- [ ] 3D 轨迹有坐标轴和视角说明。
- [ ] 收敛曲线标出最优解位置。
- [ ] 优化前后对比图统一坐标范围。
- [ ] 每张图后有中文解释。

### B 题图表
- [ ] 算法流程图用 graphviz/draw.io 矢量输出。
- [ ] 帕累托前沿高亮决策点。
- [ ] 灵敏度九联图统一 y 轴范围。
- [ ] 基准函数对比标注各算法收敛次数。
- [ ] 布局图有坐标轴和尺寸标注。

### C 题图表
- [ ] 热力图有颜色条和数值标注。
- [ ] 地图有图例和路线。
- [ ] 雷达图各轴标签清晰。
- [ ] 3D 曲面标出最优解。
- [ ] p 值热力图标注显著性阈值（0.05）。
- [ ] 混淆矩阵归一化或标注总数。

### 通用
- [ ] 坐标轴有名称和单位。
- [ ] 配色 3-5 种，无彩虹色。
- [ ] 矢量图或 ≥300DPI。
- [ ] 中文不乱码。
- [ ] 图表数量由论证需要决定；每张均绑定主张、上游数据和必要检查。
- [ ] 每张图正文有"由图 X 可见…"引用。
