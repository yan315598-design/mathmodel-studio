# 绘图升级候选验收边界

本文件是维护记录，不默认进入运行上下文。2026-09-20 版本对齐为 3.3.0；用户授权审查后同步本机 Codex/ZCode/Claude Code 安装，不授权外部发布或推送。安装结果与备份见维护工作区 outputs/release-3.3。既存 v3.2 工具不计为本次新造能力。

## 兼容

Stage/state/冻结链、旧模板 ID/CLI、位置参数/返回路径、默认样式保持。旧 save_fig 仍可能保留部分输出并关闭 Figure；新 export_revision 是独立显式入口。

数据错误单列：prediction 内部 None 保持断线；图库原图质量与 preview 解耦。SVG/PDF 有位图或无法检查时 unknown，不凭后缀宣称矢量；至少一份检查合格的正式原图才允许 v1 入图库。

实际样张还复现 figqa 的混合坐标错误：axhline/axvline 须按 artist 自身 transform 检查。修复同时恢复真实相交检出；旧 convergence-sequence 的档差标签补避判据线，数值/接口不变。未删除测试或弱化门禁。

## 后端范围

本轮环境 Python 3.13.9、Matplotlib 3.10.6、NumPy 2.3.5、SciPy 1.16.3、Pillow 12.0.0、xarray 2025.10.1；沿用可用解释器，不安装/升级全局依赖。

- 基础 Matplotlib、Icarus 轴级绘图通过合成场景实际渲染验证，不修改 vendor。
- 新增普通 TIFF（Pillow）、NPZ（NumPy）以及 NetCDF（xarray + SciPy engine）实际文件验证；不是只查 import。
- WAV/CSV/NPY/HDF5/MAT 继续由既有维护测试验证。仅验证具体 reader/样本，不宣称全格式覆盖。
- rasterio/fiona/laspy/Marsilea/PyVista 不可用，本轮未验证；真实 GIS/点云/3D 制图不在完成清单。GeoTIFF 标记检测仅用于路由，不证明 GIS 读取已支持。
- 视频实际抽帧、原始 PTS、压缩音频仍未验证；没有以静态图片或 WAV 冒充。
- 普通 TIFF 无内嵌地理标记不等于不存在 sidecar 坐标。地图须显式核查 sidecar/CRS，不静默视作已知坐标。

## 视觉与分发

生成候选不等于视觉合格。view_image 目前仅返回编码对象，未完成目检。需要查看 A-F 全部真实图及最终 180 mm 排版页；元数据、bbox 和非空像素只能检查结构。

随包样例均为合成数据，不包含受限赛题/论文素材。真实 D/E 小样本验证仅在维护工作区留存，不入安装包。本机安装使用默认完整分发选择，保留按需开发文档，避免 no-dev 变体的历史引用悬空；不声称完成对外发布去敏。

实际命令、各批结果、产物清单及最终限制在维护工作区 outputs/upgrade/acceptance.md 与 progress.md 保存。
