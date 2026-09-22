# v3.4.1 源码与分发清单说明

此文件位于Git源码仓库，源码以提交号和v3.4.1标签定位。旧版本分发包的文件计数与内容指纹不适用于当前源码，因此不沿用。

需要独立分发包时，运行 `python scripts/package_dist.py --apply`。脚本根据实际入包文件生成该包专用的PACKAGE_CONTENTS与内容指纹；GitHub按标签提供的源码归档与此筛选包不同。

分发边界见 `VENDOR_NOTICES.md`，本轮验证范围见 `docs/release_3_4_review.md`。
