---
stage: -1
name: preseason
duration_h: 2-4 (赛前一次性)
inputs: [user.competition, 本机环境]
outputs: [state/preseason_report.json, 工作区骨架, git 仓库]
loads_reference: [references/submission_checklists.md]
loads_template: [templates/shared/decision_log.json, templates/latex/<competition>/]
feedback: []
next: stage_00_kickoff
---

# Stage -1 — 赛前兵检 (T-7 ~ T-1 天)

> v7.4.0 新增：把"赛中才发现环境/模板翻车"的风险前移到赛前一次性解决。

**定位**: 比赛开始前 T-7 ~ T-1 天运行一次 | **不消耗赛中时间预算** | **输出**: `state/preseason_report.json`

---

## 为什么需要

历史教训集中在环境侧: 早年用过的一批第三方 LaTeX 模板存在编译 bug, 都是赛中第一次编译才暴露, 每次损失 1-3 小时（v7.5 路线 A 已剥离全部第三方模板, 换为 6 套自写模板: cumcm / huaweibei / huashubei / mcm / diangong / apmcm, 均随仓库预编译验证过）。同类风险还有: solver 缺失（GLPK_MI / HIGHS）、中文工具链没装、pypdf 缺失导致页数检查失效。兵检的目标 = 开赛前把这些问题全部暴露并给出绕过方案, 让 Stage 0-9 不再被环境问题打断。

---

## 运行时机与输入

- 触发: 用户说"赛前准备 / 兵检 / 检查环境 / 马上比赛了"
- 输入: 目标竞赛（六选一: cumcm / mcm / huaweibei / huashubei / diangong / apmcm）
- 输出: `state/preseason_report.json`（字段清单见文末）+ 工作区骨架 + git 仓库
- 兵检全部通过后, 赛中不再重复本阶段

---

## ① 环境兵检 checklist

| 检查项 | 命令/方法 | 通过标准 | 不通过处理 |
|---|---|---|---|
| Python | `python --version` | ≥ 3.9 | 安装 3.10+ 后重跑 |
| cvxpy | `python -c "import cvxpy; print(cvxpy.__version__)"` | 无异常 | `pip install cvxpy` |
| matplotlib | 同上 | 无异常 | `pip install matplotlib` |
| pandas | 同上 | 无异常 | `pip install pandas` |
| pypdf | `python -c "import pypdf"` | 无异常 | 可选依赖; 缺失只影响 `package_submission.py` 页数统计, 报 ⚠️ 不报 ❌ |
| xelatex | `xelatex --version` | 输出版本号 | 安装 TeX Live / MiKTeX; 中文赛另验中文字体（`fc-list :lang=zh` 或编译一次带中文的最小文档） |
| pandoc | `pandoc --version` | 输出版本号 | 安装 pandoc 后重跑（https://pandoc.org/installing.html 或 `winget install pandoc`）; 缺失只报 ⚠️ 不报 ❌（md→tex 有手工正则回退, docx 仅审阅件）, 不阻塞开赛 |
| MILP solver | 跑下方冒烟脚本 | `status=optimal` 且 < 60s | 见脚本注释的备选链 |

pandoc 用途备注: `render_paper.py` 的 md→tex 转换与 `export_docx.py` 的 docx 审阅件导出都依赖它。缺失时 render_paper 自动回退手工正则（降级可用，仅告警）; export_docx 无回退、直接失败（exit 2）。

**MILP 冒烟测试（50 变量计时）**:

```python
# 冒烟测试: 50 变量 MILP, 验证 cvxpy + 求解器链路, 计时
import time
import numpy as np
import cvxpy as cp

np.random.seed(42)
n = 50
c = np.random.uniform(1, 10, n)
p = c + np.random.uniform(0.5, 2, n)
x = cp.Variable(n, integer=True)
prob = cp.Problem(cp.Maximize((p - c) @ x),
                  [cp.sum(c * x) <= 100, x >= 0, x <= 5])
t0 = time.time()
# 备选链: GLPK_MI → HIGHS → SCIP 依次回退, 实际用上的 solver 名写入兵检报告
used_solver = None
for solver in (cp.GLPK_MI, cp.HIGHS, cp.SCIP):
    try:
        prob.solve(solver=solver)
        used_solver = solver
        break
    except cp.error.SolverError:
        print(f"solver {solver} 不可用, 试备选链下一个")
elapsed = time.time() - t0
print(f"status={prob.status}, obj={prob.value:.1f}, 用时 {elapsed:.1f}s, solver={used_solver}")
# 通过: status=optimal 且 elapsed < 60s; used_solver 名与用时写入兵检报告 (env.milp_solver.name)
```

求解时间写入报告后有两个用途: Stage 5 排求解时长预期; 超过 60s 说明 solver 链路有问题（常见是 cvxpy 没装原生求解器, 回退到了极慢的默认实现）。

---

## ② LaTeX 模板预编译

对目标竞赛模板 `templates/latex/<competition>/` 做一次空编译:

```bash
# 复制到临时目录, 避免污染 skill 仓库
cp -r <skill>/templates/latex/<competition>/ /tmp/precompile_test/
cd /tmp/precompile_test
xelatex -interaction=nonstopmode main.tex     # 中文赛 (含 apmcm 亚太杯中文赛)
pdflatex -interaction=nonstopmode main.tex    # 英文赛 (仅 mcm)
# 通过标准: 生成 main.pdf 且退出码 0; 记录 warning/error 摘要进报告
```

**6 套自写模板预编译状态**: v7.5 起仓库内 6 套模板（cumcm / huaweibei / huashubei / mcm / diangong / apmcm）全部为本项目自写资产（ctexart / article 骨架, 无第三方 cls 依赖）, 均已随仓库预编译验证。本机兵检仍须重跑一次空编译——字体（Linux 下中文字体缺失是常见翻车点）、TeX 发行版版本差异只能本机暴露。

原则:

1. 六大竞赛的全部 6 套模板以本机兵检实测结果为准, 不预设"一定通过"。
2. 手工修复只在**临时副本**上做, 修好后把 diff 报告用户, 由用户决定是否回写 skill。
3. 无法修复时, 在报告中标记 `blocking_issues`, 并给用户编号菜单选择换模板或带伤开赛（换模板 = 改 `loads_template` 指向 + 重跑预编译）。

---

## ③ 案例库预热

对目标竞赛跑一次 `scripts/retrieve_cases.py` 冒烟查询, 确认索引可加载、无异常:

```bash
python <skill>/scripts/retrieve_cases.py --competition <comp> --query "<领域词, 如 优化>" --top-k 3
```

通过标准: 命令正常退出且返回 ≥1 条案例（cumcm / huaweibei / huashubei 有本地索引; mcm / diangong / apmcm 无索引时跳过本项并在报告标注 `not_applicable`）。

---

## ④ 工作区骨架生成

在用户比赛工作目录生成:

```
<workspace>/
  state/               # decision_log.json (从 templates/shared/decision_log.json 复制)
  results/             # 各 Qi 结果
  figures/             # 图表输出
  code/                # 求解代码
  paper_workspace/     # 论文工程 (main.tex + sections/)
```

约定:

1. `state/decision_log.json` 必须从 `templates/shared/decision_log.json` 复制, 不手写。
2. `decision_log.competition` 在骨架生成时填入目标竞赛。
3. `requirements.txt` 从 `templates/shared/requirements.txt` 复制, 兵检通过即视为环境基线。

---

## ⑤ git 初始化与提交节奏

```bash
cd <workspace>
git init
git add -A && git commit -m "preseason: workspace skeleton"
```

提交节奏约定（赛中执行, 兵检时只约定不执行）:

| 时点 | 提交内容 |
|---|---|
| 每完成一个 Qi | code/ + results/ + decision_log 快照 |
| 每阶段退出时 | 全量快照, message 带阶段号 (如 `stage5 done`) |
| 论文每成稿一节 | paper_workspace/ 快照 |
| 提交打包后 | submission/ zip 的 hash |

`.gitignore` 建议: `__pycache__/`, `*.aux`, `*.log`, `*.synctex.gz`, 大于 50MB 的数据文件。

---

## ⑥ 赛前素材自查

| 素材 | 说明 |
|---|---|
| LaTeX 模板 | ② 已预编译通过的那一套, 复制进 paper_workspace/ |
| 承诺书 | 打印/扫描件是否就绪（是否需要按当年通知签名盖章 → `references/submission_checklists.md`） |
| 报名号/队号 | 记录在 state/ 下的备忘文件, 提交命名要用 |
| 竞赛系统账号 | 提前登录一次, 避免赛中出现账号问题 |
| 往年通知 | 核对提交格式细节（页数/文件名/附件要求）, 逐项标注 [以当年通知为准] |
| 写作队员编辑器 | Obsidian（个人免费）或 MarkText（开源）等 WYSIWYG markdown 编辑器安装并试改一段（含 `$...$` 公式预览）; Word 队员用它参与 md 修订（docx 仅审阅件, 见 workspace_protocol §3.1） |

写作队员编辑器选型（免费, 三选一）:

| 编辑器 | 费用/许可 | 适合谁 | 一句话 |
|---|---|---|---|
| Obsidian（默认推荐） | 个人使用免费 | 大多数人 | 实时预览模式体验接近 Typora, 公式渲染好, 持续更新 |
| MarkText | 开源免费 | 想要完全开源 | 界面最像 Typora; 项目 2022 年后停更, 装 0.17.1 够用 |
| VS Code（兜底） | 免费 | 队里已有代码环境 | 自带 Markdown 预览 (Ctrl+Shift+V), 编辑/预览分栏, 非打字即所见 |

验证口径: 试改一段含 `$...$` 公式与管道表格的 md, 公式正常渲染即过关。

---

## 兵检报告字段清单

`state/preseason_report.json`:

```json
{
  "generated_at": "2026-08-30T20:00:00",
  "competition": "huashubei",
  "env": {
    "python": "3.11.4",
    "packages": {"cvxpy": "1.4.1", "matplotlib": "3.8.2", "pandas": "2.1.4", "pypdf": "4.2.0"},
    "xelatex": true,
    "pandoc": true,
    "milp_solver": {"name": "GLPK_MI", "status": "optimal", "solve_time_s": 0.8}
  },
  "latex_precompile": {"template": "huashubei", "passed": true, "log_excerpt": ""},
  "case_library_smoke": {"query": "优化", "hits": 3},
  "workspace": {"dirs": ["state", "results", "figures", "code", "paper_workspace"], "decision_log_copied": true},
  "git": {"initialized": true, "initial_commit": "preseason: workspace skeleton"},
  "materials": {"latex_template": true, "commitment_letter": true, "team_id_recorded": true, "markdown_editor": true},
  "overall": "pass",
  "blocking_issues": []
}
```

`overall=pass` 条件: 环境兵检无 ❌ 且模板预编译通过。`blocking_issues` 非空时 `overall=fail`。pandoc 缺失报 ⚠️ 不报 ❌（render_paper 的 md→tex 有手工正则回退, docx 仅审阅件）, 不阻塞开赛。

---

## 编号菜单交互

兵检跑完后, agent 汇总并问用户一次（Claude Code: AskUserQuestion; Codex/ZCode: 编号列表）:

```
【兵检完成: overall=pass/fail, 阻塞项 N 个】

  1) 全部通过, 冻结环境, 等开赛 (推荐)
  2) 只重跑失败的检查项
  3) 换目标竞赛重跑整个兵检
  4) 手工修 LaTeX 模板后重新预编译
  5) 让我决定

回复数字。
```

→ 通过后开赛时直接进 `stage_00_kickoff.md`, 不重复兵检。
