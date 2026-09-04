"""CLI 入口: python -m mathmodel_agent run --workspace <dir> [--mock] ..."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .config import AgentConfig
from .llm import LiteLLMClient
from .loop import StageDriver
from .mockllm import MockLLM
from .state import DecisionLog

DEFAULT_SKILL_ROOT = Path(__file__).resolve().parents[2]
# 对齐 references/workspace_protocol.md 的工作区骨架
WORKSPACE_DIRS = ("state", "results", "figures", "code", "paper_workspace",
                  "_archive", "inputs", "_runtime")
# 退出码: 0 成功; 2 参数/一致性错误; 3 质量门 blocked; 4 状态写盘失败
EXIT_USAGE, EXIT_BLOCKED, EXIT_SAVE_FAILED = 2, 3, 4


def build_parser() -> argparse.ArgumentParser:
    """构造 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="mathmodel_agent", description="mathmodel-studio 薄 agent runtime 原型")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="驱动 stage 流程")
    run.add_argument("--workspace", required=True, help="工作区目录 (一题一目录)")
    run.add_argument("--competition", default="cumcm",
                     help="cumcm|huaweibei|huashubei|mcm|diangong|apmcm (默认 cumcm)")
    run.add_argument("--problem", default=None,
                     help="题面文件路径, 会被复制到 workspace/inputs/problem.txt")
    run.add_argument("--from-stage", type=int, default=None,
                     help="起始 stage; 默认取 state.current_stage (无 state 则 0)")
    run.add_argument("--to-stage", type=int, default=None, help="默认: mock 2, 真实 9")
    run.add_argument("--mode", default="standard",
                     choices=["fast", "standard", "championship"], help="token 预算档位")
    run.add_argument("--skill-root", default=None,
                     help="mathmodel-studio 仓库根目录 (默认自动探测)")
    run.add_argument("--mock", action="store_true", help="使用 MockLLM, 不发任何网络请求")
    run.add_argument("--dry-run", action="store_true",
                     help="只打印 prompt 摘要, 不调用 LLM")
    run.add_argument("--force", action="store_true",
                     help="允许 --from-stage 与 state.current_stage 不一致 (记 backtrack 事件)")
    return parser


def cmd_run(args: argparse.Namespace) -> int:
    """run 子命令: 建工作区 → 初始化 state → 校验起点 → 驱动 stage。"""
    skill_root = (Path(args.skill_root).resolve() if args.skill_root else DEFAULT_SKILL_ROOT)
    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    for dirname in WORKSPACE_DIRS:
        (workspace / dirname).mkdir(exist_ok=True)
    config = AgentConfig.from_env(skill_root=skill_root, mode=args.mode)
    if args.problem:
        shutil.copyfile(args.problem, workspace / "inputs" / "problem.txt")
    state = DecisionLog.load(workspace) or DecisionLog.init_from_template(
        workspace, skill_root, competition=args.competition, mode=args.mode,
        problem="inputs/problem.txt" if args.problem else None)
    current = int(state.data.get("current_stage") or 0)
    start = args.from_stage if args.from_stage is not None else current
    if start != current:  # 显式回退/跳阶段必须 --force, 且记 backtrack 事件
        if not args.force:
            print(f"[FAIL] --from-stage {start} 与 state.current_stage={current} 不一致; "
                  f"显式回退需 --force")
            return EXIT_USAGE
        state.append_event("backtrack", **{"from": current, "to": start})
        state.save()
    to_stage = args.to_stage if args.to_stage is not None else (2 if args.mock else 9)
    if not 0 <= start <= to_stage <= 9:
        print(f"[FAIL] stage 区间非法: [{start}, {to_stage}]")
        return EXIT_USAGE
    client = MockLLM() if args.mock else LiteLLMClient(config)
    driver = StageDriver(config=config, client=client, state=state, workspace=workspace)
    status = driver.run(start, to_stage, dry_run=args.dry_run)
    budget = state.data.get("budget", {})
    print(f"\n[done: {status}] competition={state.data.get('competition')} "
          f"current_stage={state.data.get('current_stage')} "
          f"tokens={budget.get('tokens_used')}/{budget.get('tokens_cap')}")
    return {"blocked": EXIT_BLOCKED, "save_failed": EXIT_SAVE_FAILED}.get(status, 0)


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口 (由 __main__.py 调用)。"""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows GBK 控制台兜底
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
