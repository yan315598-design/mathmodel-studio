# 第三方内容剔除说明 (VENDOR NOTICES)

本分发包在打包时 (`scripts/package_dist.py`) 剔除了以下内容:

## 1. 许可证受限内容 (未随包分发, 不可再分发)

| 未随包分发的资源 (资源名) | 原因 |
|---|---|
| `scibox-diagram` | 上游 [jihe520/sci-box] 未附正式 LICENSE 文件 (见本包内 `templates/figures/vendor/VENDOR.md` §5), 再分发前必须移出 |
| `scibox-figure` | 同上 |

二者**不在本包内**, 也不是可用本地路径; 本包随附的上游副本只有 MIT 的
`diagram-design` 与 `icarus-figures` 两个。

**对终端用户的影响**: `SKILL.md` 与 `references/figure_skill_bridge.md` 中指向
scibox-diagram / scibox-figure 的首选路由在分发版不可用。打包器已在分发副本的这两份文档顶部注入
"分发版路由说明"横幅, 公开路由改走本包实际随附的内容:

- 论文示意图 (drawio): 自写可编辑模板 7 件 (`templates/figures/scripts/render_drawio_pack.py`), 落盘自动过版式门禁 (XML 自验 + drawio_check 体检)
- 论文示意图 (matplotlib): 自写直出模板 4 件 (`templates/figures/scripts/render_diagram_pack.py`), 该脚本只打印 figqa 提示, **不自动执行**——生成后按提示另跑 `figqa.py`
- 数据图: `templates/figures/scripts/render_modeling_pack.py` (25 件, 统一色板 + figqa/figure_lint 硬门)
- 答辩/展示 HTML: `templates/figures/vendor/diagram-design/` 仍保留 (上游 MIT, 见其 THIRD_PARTY_LICENSES.md)

**scibox 独有能力在分发版不可用**: scibox-diagram 的 4 件高密度示意图模板与
scibox-figure 的 11 件差异图型 (tpe_surface、marginal_grid、cv_roc_ci 等) 已随资源
一并剔除, 分发版没有等价替代 (属能力留白); 需要时请自行从上游仓库获取并遵守其许可条款。

## 2. 非公开项目材料与凭证类内容 (默认剔除, 与 git 跟踪无关)

| 未随包分发的内容 (资源名/模式) | 原因 |
|---|---|
| `figures`、`results` (含 `answer.json`) | 用户工作区真实项目产出, 非公开项目材料; 源仓库原件保留, 只做选择隔离 |
| `maintenance` | 人读本地语料库 (可能含原始私有语料/逐篇审读稿); 默认不进公开分发, 源仓库保留原件 |
| `templates/figures/gallery/golden/` 4 张实战成品图 (Q1_C1_field / Q2_C1_stages / Q34_C1_gridconv / Q4_C2_routes) | 2026 国赛 A 题返工成品, 非公开项目材料; 分发版保留该目录 3 张 make_* 模板样张, 已注入分发版说明 |
| `.env` / `.env.*` / `secrets.json` / `credentials.json` / `credentials` / `*.pem` / `*.key` / `private.md` / `answer.json` / `id_rsa*` / `.netrc` / `.git-credentials` / `.npmrc` / `.pypirc` | 凭证与密钥类, 任意层级默认剔除 (与 git 是否跟踪无关) |
| `_internal_notes/`、`.aws/`、`.ssh/`、`.gnupg/` | 内部笔记与凭证容器目录, 整棵剔除 (容器内文件常无扩展名, 不依赖扫描发现) |
| `_archive/`、`tmp/`、`temp/`、`backup*` (含 `backups_old` 等)、`*.bak` / `*.bak.*` / `*.tmp` / `*.orig` / `*.rej` / `*~` / `~$*` | 归档与备份/临时文件 |

类别计数与实际剔除路径级明细见包内 `PACKAGE_CONTENTS.md` (明细报告落在 dist 根, 不进包)。

## 3. 运行时/缓存产物 (可再生产)

| 被剔除路径 | 原因 |
|---|---|
| `.git/`, `.pytest_cache/`, `**/__pycache__/`, `%TEMP%/`, `dist/`, `.mimosa/` | 版本库、缓存与本地工具会话状态 |
| `state/` | 运行时状态目录, 仅保留 `.gitkeep` 占位 |
| `evals/results/` | 本地评测结果, 运行 `evals/run_eval.py score-run` 再生 |
| `outputs/` | 运行时图表输出目录 (vendor 冒烟测试可再生产物) |

完整规则与默认 dry-run 行为见 `scripts/package_dist.py` 模块 docstring。
