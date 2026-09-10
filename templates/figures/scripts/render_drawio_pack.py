# -*- coding: utf-8 -*-
"""draw.io 可编辑流程图模板包 dispatcher（6 个 drawio 模板的统一入口）。

与 render_diagram_pack.py（matplotlib 示意图包）相互独立、互不影响,
本脚本只分发 templates/figures/scripts/drawio/ 下的 6 个 drawio 模板,
输出 .drawio（mxGraph XML）, draw.io 桌面版/网页版打开即编辑:

    roadmap     竖版层带技术路线图   (roadmap)
    framework   三栏研究框架图       (framework)
    flow3col    多列阶段流程图       (flow3col)
    stageflow   横向阶段流水线       (stageflow)
    swimlane    泳道流程图           (swimlane)
    mechanism   机理示意图           (mechanism)

用法:
    python render_drawio_pack.py <子命令> [模板参数...]
    python render_drawio_pack.py --list

子命令即模板 id、英文别名或中文别名, 其余参数原样转发给模板脚本, 例如:
    python render_drawio_pack.py roadmap --out figs/roadmap
    python render_drawio_pack.py 路线图 --out figs/roadmap
    python render_drawio_pack.py stageflow --highlight 3 --out figs/flow

注意: figqa.py 只检测 matplotlib .py 出图脚本, 不支持 .drawio 文件;
.drawio 的质量门是两层: 落盘后 XML 自验（合法性 + 节点/连线计数）
+ 1.3.0 起 finalize() 自动运行 drawio_check.py 版式体检（文字溢出/越界/
重复 id/实心盒重叠/连线穿盒/位图内嵌 = FAIL,  FAIL 即退出码 1;
MATHMODEL_DRAWIO_CHECK=0 关闭, MATHMODEL_DRAWIO_STRICT=1 时 WARN 也判失败）。
也可单独体检任意 .drawio: python drawio/drawio_check.py <文件> [--strict]

退出码: 0 成功; 1 模板执行失败或版式门禁 FAIL; 2 未知模板/用法错误
（与 render_modeling_pack.py 契约一致; render_diagram_pack.py 为既有行为不动）。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TEMPLATES: dict[str, tuple[str, str]] = {
    "roadmap": (
        "make_drawio_roadmap.py",
        "竖版层带技术路线图: DIAGRAM_FAMILIES 族色层带(DIAGRAM_ORDER_ROADMAP) "
        "+ ①②③ 浅底徽章 + 层间正交下行, --layers/--nodes 可配",
    ),
    "framework": (
        "make_drawio_framework.py",
        "三栏研究框架图: 子问题→方法模型→结果产出 2-4 行映射, "
        "三栏绑 blue/orange/teal 三族",
    ),
    "flow3col": (
        "make_drawio_flow3col.py",
        "多列阶段流程图: N 列泳道（默认 4）, 列头实色标题条(族序 GENERIC), "
        "列内下行+列间右行",
    ),
    "stageflow": (
        "make_drawio_stageflow.py",
        "横向任务流水线: 4-6 阶段横排 + 圆形编号徽章 + 框下说明, "
        "--highlight 族 accent 描边强调",
    ),
    "swimlane": (
        "make_drawio_swimlane.py",
        "泳道流程图: 数据/模型/求解/应用 3-4 条泳道(每道一族), 节点跨泳道流转",
    ),
    "mechanism": (
        "make_drawio_mechanism.py",
        "机理示意图: 中心主体(grey 族) + 4-6 环绕要素(每要素一族), "
        "双向数据流 + 闭环反馈虚线",
    ),
}

ALIASES = {
    # 英文别名
    "tech-roadmap": "roadmap",
    "roadmap-5": "roadmap",
    "framework-3col": "framework",
    "3col": "framework",
    "flow-3col": "flow3col",
    "flowchart": "flow3col",
    "pipeline": "stageflow",
    "stage-flow": "stageflow",
    "lane": "swimlane",
    "lanes": "swimlane",
    "feedback": "mechanism",
    "compartment": "mechanism",
    # 中文别名
    "路线图": "roadmap",
    "技术路线图": "roadmap",
    "框架": "framework",
    "研究框架": "framework",
    "三栏流程": "flow3col",
    "三栏流程图": "flow3col",
    "流程图": "flow3col",
    "流水线": "stageflow",
    "泳道": "swimlane",
    "泳道图": "swimlane",
    "机理": "mechanism",
    "机理图": "mechanism",
}


def resolve(value: str) -> str:
    """把模板 id / 英文别名 / 中文别名解析为标准 id, 未知值时 SystemExit(由 main 捕获转退出码 2)。"""
    key = value.strip()
    lower = key.lower()
    if lower in TEMPLATES:
        return lower
    if key in ALIASES:
        return ALIASES[key]
    if lower in ALIASES:
        return ALIASES[lower]
    raise SystemExit(
        f"未知模板: {value}\n可用模板 id: {', '.join(sorted(TEMPLATES))}"
        f"\n别名: {', '.join(f'{k} -> {v}' for k, v in sorted(ALIASES.items()))}"
    )


def print_list() -> None:
    """输出模板清单表 + 中文别名 + 自验说明。"""
    id_width = max(len(k) for k in TEMPLATES) + 2
    file_width = max(len(v[0]) for v in TEMPLATES.values()) + 2
    print(f"{'模板 id'.ljust(id_width)}{'脚本文件'.ljust(file_width)}说明")
    for template_id, (file_name, desc) in sorted(TEMPLATES.items()):
        print(f"{template_id.ljust(id_width)}{file_name.ljust(file_width)}{desc}")
    print("\n中文别名: " + ", ".join(
        f"{k} -> {v}" for k, v in sorted(ALIASES.items()) if not k.isascii()))
    print("英文别名: " + ", ".join(
        f"{k} -> {v}" for k, v in sorted(ALIASES.items()) if k.isascii()))
    print("\n质量门: figqa.py 只检测 matplotlib 出图脚本, 不支持 .drawio 文件;"
          "\n.drawio 两层质量门: XML 自验 + drawio_check.py 版式体检"
          "\n（文字溢出/越界/重叠/穿盒/位图 = FAIL 即退出码 1;"
          "\n MATHMODEL_DRAWIO_CHECK=0 关闭, MATHMODEL_DRAWIO_STRICT=1 时 WARN 也失败）。")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="渲染 draw.io 可编辑流程图模板包（6 个模板的统一入口）"
    )
    parser.add_argument("--list", action="store_true", help="列出支持的模板清单")
    parser.add_argument(
        "template", nargs="?", default=None,
        help="模板 id / 别名（roadmap/framework/flow3col/stageflow/swimlane/"
             "mechanism 或 路线图/框架/三栏流程/流水线/泳道/机理）",
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
    try:
        # resolve 的 SystemExit 在此转为退出码 2 (docstring 契约),
        # 否则字符串 SystemExit 会被解释成 rc=1
        template_id = resolve(args.template)
    except SystemExit as exc:
        print(str(exc.code if isinstance(exc.code, str) else exc), file=sys.stderr)
        return 2
    script = Path(__file__).resolve().parent / "drawio" / TEMPLATES[template_id][0]
    if not script.exists():
        print(f"模板脚本缺失: {script}")
        return 2
    cmd = [sys.executable, str(script), *args.extra]
    print(f"$ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
