# -*- coding: utf-8 -*-
"""示意图/流程图模板包 dispatcher（4 个示意图模板的统一入口）。

与 render_modeling_pack.py（建模图表包）相互独立、互不影响, 本脚本只分发
templates/figures/scripts/diagrams/ 下的 4 个示意图模板:

    roadmap     竖版五带技术路线图   (roadmap)
    framework   三栏研究框架图       (framework)
    stageflow   横向阶段流水线图     (stageflow)
    module      模块化功能框图       (module)

用法:
    python render_diagram_pack.py <子命令> [模板参数...]
    python render_diagram_pack.py --list

子命令即模板 id 或别名, 其余参数原样转发给模板脚本, 例如:
    python render_diagram_pack.py roadmap --out figs/roadmap
    python render_diagram_pack.py stageflow --highlight 3 --out figs/flow

退出码: 0 成功; 1 模板执行失败; 2 未知模板/用法错误。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TEMPLATES: dict[str, tuple[str, str]] = {
    "roadmap": (
        "make_diagram_roadmap.py",
        "竖版五带技术路线图: 5 层色带自顶向下, 每层 1-3 节点, "
        "DIAGRAM_FAMILIES 五族色带(blue/blue/orange/purple/teal)",
    ),
    "framework": (
        "make_diagram_framework_3col.py",
        "三栏研究框架图: 子问题→方法模型→结果产出 2-4 行横向映射, "
        "三栏绑 blue/orange/teal 三族",
    ),
    "stageflow": (
        "make_diagram_stageflow.py",
        "横向阶段流水线: 4-6 阶段框 + 编号徽章 + 框下说明, "
        "阶段族序取 DIAGRAM_ORDER_GENERIC, --highlight 族 accent 描边强调",
    ),
    "module": (
        "make_diagram_module.py",
        "模块化功能框图: 中心总模型(grey 族) + 4-6 卫星模块双向数据流, "
        "卫星每枚一族(DIAGRAM_ORDER_GENERIC)",
    ),
}

ALIASES = {
    "tech-roadmap": "roadmap",
    "roadmap-5": "roadmap",
    "framework-3col": "framework",
    "3col": "framework",
    "pipeline": "stageflow",
    "stage-flow": "stageflow",
    "flow": "stageflow",
    "module-map": "module",
    "modules": "module",
}

SKILL_ROOT = Path(__file__).resolve().parents[3]
FIGQA_SCRIPT = SKILL_ROOT / "scripts" / "figqa.py"

# 示意图的盒内/徽章内标签属有意版式, 全部模板的 figqa 硬门固定带豁免开关
BOX_LABEL_TEMPLATES = set(TEMPLATES)


def figqa_hint(template_id: str) -> str:
    """返回该模板推荐的 figqa 硬门命令行（示意图盒内标签固定豁免）。"""
    flag = " --allow-box-labels" if template_id in BOX_LABEL_TEMPLATES else ""
    return f"python {FIGQA_SCRIPT} <图脚本或输出目录> --strict{flag}"


def resolve(value: str) -> str:
    """把模板 id 或别名解析为标准 id, 未知值时 SystemExit。"""
    key = value.strip().lower().replace("_", "-")
    if key in TEMPLATES:
        return key
    if key in ALIASES:
        return ALIASES[key]
    raise SystemExit(
        f"未知模板: {value}\n可用模板 id: {', '.join(sorted(TEMPLATES))}"
        f"\n别名: {', '.join(sorted(ALIASES))}"
    )


def print_list() -> None:
    """输出模板清单表 + 每个模板推荐的 figqa 硬门命令。"""
    id_width = max(len(k) for k in TEMPLATES) + 2
    file_width = max(len(v[0]) for v in TEMPLATES.values()) + 2
    print(f"{'模板 id'.ljust(id_width)}{'脚本文件'.ljust(file_width)}说明")
    for template_id, (file_name, desc) in sorted(TEMPLATES.items()):
        print(f"{template_id.ljust(id_width)}{file_name.ljust(file_width)}{desc}")
    if ALIASES:
        print(f"\n别名: {', '.join(f'{k} -> {v}' for k, v in sorted(ALIASES.items()))}")
    print("\nfigqa 硬门命令 (示意图盒内/徽章内标签为有意版式, 固定加 --allow-box-labels):")
    for template_id in sorted(TEMPLATES):
        print(f"  [{template_id}] {figqa_hint(template_id)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="渲染示意图/流程图模板包（4 个模板的统一入口）"
    )
    parser.add_argument("--list", action="store_true", help="列出支持的模板清单")
    parser.add_argument(
        "template", nargs="?", default=None,
        help="模板 id 或别名（roadmap/framework/stageflow/module）",
    )
    # REMAINDER 捕获首个位置参数之后的全部内容（含 -- 开头的模板参数）,
    # 不用 argparse 子解析器: 子解析器会把转发参数误判为本脚本的未知项
    parser.add_argument("extra", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.list:
        print_list()
        return 0
    if not args.template:
        parser.error("需要模板 id, 或用 --list 查看清单")
    template_id = resolve(args.template)
    script = Path(__file__).resolve().parent / "diagrams" / TEMPLATES[template_id][0]
    if not script.exists():
        print(f"模板脚本缺失: {script}")
        return 2
    cmd = [sys.executable, str(script), *args.extra]
    print(f"$ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, check=False)
    print(f"\n[提示] 出图后跑该模板的 figqa 硬门: {figqa_hint(template_id)}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
