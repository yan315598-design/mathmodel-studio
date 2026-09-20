# 多类型附件

触发：附件并非单一表格，或用户要求检查本地素材。先检查实际文件与元数据，再只加载命中类型所需的库。文件扩展名仅作路由提示；成功打开也不代表内容已通过领域验证。

## 检查与分析边界

```bash
python <skill>/scripts/inspect_assets.py data/raw/sample.wav data/raw/map.tif --output results/assets_v1.json
python <skill>/scripts/inspect_assets.py data/raw/video.mp4 --frame 120 --image data/processed/frame120.png --output results/frame120.json
```

清单 `assets-1` 含原路径、大小、SHA-256、类型、元数据及状态；`inspected` 仅表示已完成该读取器声明范围的元数据检查。`missing_dependency / unsupported_reader / error` 不算通过；进程 exit 1 表示存在未完成项，其他文件继续检查。目录不自动递归，Agent 显式传入附件文件，不扫描整个工作区。

原始附件不修改；派生产物记录原始清单 ID、处理脚本、参数和输出哈希，关键运行接 `scripts/run_manifest.py`。外部获取仍按 `references/data_acquisition.md` 登记 `datasets.json`；本地附件清单不代替许可和来源记录。

| 类型 | 已实现检查 | 按任务开展的分析 / 可选依赖 |
|---|---|---|
| CSV/TSV | 表头、前 100 行列宽 | pandas 全量清洗；非 UTF-8 输入须显式指定编码转换副本 |
| XLSX/Parquet | 表单范围 / 行列与 schema | openpyxl / pyarrow；不自动全量载入 |
| 图片 | 解码校验、尺寸、通道 | Pillow；检查标尺、原始分辨率、裁剪来源 |
| 视频 | 编码、帧率、时长、时间基 | FFmpeg 的 ffprobe；抽帧保存零基解码帧号与原始 PTS，不用帧号除平均帧率代替变帧率时间 |
| 音频 | WAV 采样率、声道、位深、帧数、时长；其他音频流头 | WAV 使用标准库，其他格式用 ffprobe；波形/频谱/STFT 用 scipy 或 librosa，记录窗口、重叠、频率单位与声道合并方式 |
| 地理矢量 | 要素数、CRS、范围、字段 | fiona；叠图前统一 CRS，地理坐标不直接当米 |
| 栅格/遥感 | 波段、尺寸、CRS、变换、nodata、dtype | 地理标记 TIFF/.geotiff 用 rasterio；普通 TIFF 用 Pillow，sidecar/CRS 边界见下节 |
| LAS/LAZ 点云 | 点数、边界、缩放与偏移的头信息 | laspy；坐标与强度分析另读实际点，LAZ 解码需要对应后端 |
| NPY/HDF5/NetCDF/MAT | shape、dtype、维度/变量头 | numpy / h5py / xarray / scipy；NetCDF 需要可用读取后端，MAT v7.3 按 HDF5 处理 |
| NPZ | 前 100 个数组的 shape/dtype，禁用 pickle | NumPy；压缩数组读取会解压，先判断成本 |
| PLY/PCD/XLS/文档/未知类型 | 类型识别，明确标 unsupported_reader | 任务需要时使用 Open3D / pandas / 文档工具，不称为已读取 |

检查脚本没有执行语音转录、视频语义理解或科学分析。只有调用相应工具、验证输出后才报告分析完成。视频默认最多探查 10000 个 packet，抽取一帧；参数 `--scan-limit` 可按预算调整，超范围直接报错，不静默抽错帧。

## 进入工作流

Stage 2 将时间、空间坐标、单位、样本实体与各问输入对应起来。Stage 3/5 先小样本试读，再安排块读取、降采样或窗口计算；对训练数据与验证数据使用同一确定的处理口径。展示路由见 `references/result_gallery.md`，数据图出图仍复用现有图表桥。
## 读取边界

普通 TIFF 先用 Pillow 检查内嵌地理标记；没有标记记录 ordinary_tiff，sidecar 未解析，不认作已知 CRS。有标记或 .geotiff 必须走 rasterio，缺依赖明确返回，不降级冒充地图读取。

NPZ 以 allow_pickle=False 按需读前 100 个数组的形状/类型（压缩数组会解压，巨大数组先估算成本）。NetCDF 保留 dataset/variable attributes、单位和未解码时间坐标口径。记录 capability.metadata / analysis=not_run 与 provenance；不把“读取成功”当分析或质检通过。
