"""
仿真类 code starter — 对应论文 §5.x 仿真 / §6 灵敏度
适用: 蒙特卡罗 / 拉丁超立方采样 (LHS) / 系统动力学 ODE / Agent-based

国赛超高频: 与灵敏度分析联用 (winning_patterns.md 灵敏度节)
如实际使用 LHS，名称如实写 "拉丁超立方蒙特卡罗稳健性仿真"
"""

import math

import numpy as np
import pandas as pd
from scipy.stats import qmc
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
from pathlib import Path


def _demo_bootstrap() -> None:
    """示例模式的副作用（固定种子 + 建目录）只在 `__main__` 分支执行。

    审查教训: 这三行原先在模块顶层, 任何 `import simulation`（如测试收集）都会
    重置全局 RNG 并在 CWD 建目录, 静默污染同进程的其它测试。
    """
    np.random.seed(42)
    Path("results").mkdir(exist_ok=True)
    Path("figures").mkdir(exist_ok=True)


# ============================================================
# 1. 蒙特卡罗 (Monte Carlo) 基本框架
# ============================================================
def monte_carlo(simulator, n_samples=1000, **distributions):
    """
    Args:
        simulator: 单次仿真函数, 接受关键字参数, 返回标量或 dict
        n_samples: 样本数
        distributions: dict of {param_name: callable returning ndarray of size n}
    Returns:
        list of simulator return values
    """
    samples = {k: dist(n_samples) for k, dist in distributions.items()}
    results = []
    for i in range(n_samples):
        kwargs = {k: samples[k][i] for k in distributions}
        results.append(simulator(**kwargs))
    return results, samples


# ============================================================
# 2. 拉丁超立方采样 LHS  ⭐ 一等奖标配
# ============================================================
def lhs_sampling(d, n, bounds=None, seed=42):
    """
    Args:
        d: 维度 (扰动参数数量)
        n: 样本数
        bounds: list of (low, high) tuples, 长度 d. 默认 [0, 1]
    Returns:
        ndarray (n, d)
    """
    sampler = qmc.LatinHypercube(d=d, seed=seed)
    unit = sampler.random(n=n)  # ∈ [0, 1]^d
    if bounds is None:
        return unit
    lows = np.array([b[0] for b in bounds])
    highs = np.array([b[1] for b in bounds])
    return lows + unit * (highs - lows)


def joint_sensitivity_lhs(simulator, baseline_params, perturbation_levels=None, n_samples=200):
    """
    对所有 baseline_params 做联合 LHS 扰动 (winning_patterns §7)

    Args:
        simulator: callable(**params) -> scalar
        baseline_params: dict {param: baseline_value}
        perturbation_levels: list of perturbation ratios, e.g., [0.05, 0.10, 0.20]
        n_samples: per level
    Returns:
        dict {level: {"samples": ndarray, "outputs": ndarray, "stats": dict}}
    """
    if perturbation_levels is None:
        perturbation_levels = [0.05, 0.10, 0.20]

    param_names = list(baseline_params.keys())
    d = len(param_names)
    baseline_values = np.array([baseline_params[k] for k in param_names])

    results = {}
    for level in perturbation_levels:
        bounds = [(v * (1 - level), v * (1 + level)) for v in baseline_values]
        samples = lhs_sampling(d, n_samples, bounds)
        outputs = []
        for i in range(n_samples):
            params = {k: samples[i, j] for j, k in enumerate(param_names)}
            outputs.append(simulator(**params))
        outputs = np.array(outputs)
        stats = {
            "mean": outputs.mean(),
            "std": outputs.std(),
            "p5": np.percentile(outputs, 5),
            "p95": np.percentile(outputs, 95),
            "cv": outputs.std() / abs(outputs.mean() + 1e-12),
        }
        results[level] = {"samples": samples, "outputs": outputs, "stats": stats}
    return results, param_names


# ============================================================
# 3. Sobol 全局灵敏度 (championship 升级)
# ============================================================
def sobol_indices(simulator, param_names, baseline_params, n_samples=1024):
    """
    需要 SALib 库
    Returns: dict {param: {S1, ST}}
    """
    try:
        from SALib.sample import saltelli
        from SALib.analyze import sobol
    except ImportError:
        print("⚠ SALib 未安装, 跳过 Sobol")
        return None

    bounds = [[v * 0.8, v * 1.2] for v in baseline_params.values()]
    problem = {
        "num_vars": len(param_names),
        "names": param_names,
        "bounds": bounds,
    }
    samples = saltelli.sample(problem, n_samples)
    outputs = np.array([simulator(**dict(zip(param_names, s))) for s in samples])
    Si = sobol.analyze(problem, outputs, print_to_console=False)
    return {param: {"S1": float(Si["S1"][i]), "ST": float(Si["ST"][i])}
            for i, param in enumerate(param_names)}


# ============================================================
# 4. ODE 系统仿真 (e.g., 改进 SEIR, 国赛传染病题)
# ============================================================
def seir_with_quarantine(t, y, beta, sigma, gamma, kappa):
    """
    SEIR 含潜伏期与隔离（仅在实现该结构时以此命名）

    y = [S, E, I, R]
    """
    S, E, I, R = y
    N = S + E + I + R
    dS = -beta * S * I / N
    dE = beta * S * I / N - sigma * E
    dI = sigma * E - gamma * I - kappa * I  # kappa 是隔离率
    dR = gamma * I + kappa * I
    return [dS, dE, dI, dR]


def simulate_seir(N=10000, I0=10, beta=0.3, sigma=0.2, gamma=0.1, kappa=0.05, T=180):
    y0 = [N - I0, 0, I0, 0]
    sol = solve_ivp(seir_with_quarantine, (0, T), y0,
                     args=(beta, sigma, gamma, kappa), dense_output=True,
                     t_eval=np.arange(0, T + 1))
    return {"t": sol.t, "S": sol.y[0], "E": sol.y[1], "I": sol.y[2], "R": sol.y[3],
            "peak_I": sol.y[2].max(), "peak_t": sol.t[sol.y[2].argmax()]}


# ============================================================
# 5. 可视化辅助
# ============================================================
def plot_lhs_pairs(samples, outputs, param_names):
    """
    pairs plot (sensitivity_table.md 图 1)
    """
    df = pd.DataFrame(samples, columns=param_names)
    df["output"] = outputs
    try:
        import seaborn as sns
        g = sns.pairplot(df, diag_kind="kde", plot_kws={"alpha": 0.4})
        return g.fig
    except ImportError:
        # 备用: 简单矩阵
        d = len(param_names)
        fig, axes = plt.subplots(d, d, figsize=(d*3, d*3))
        for i in range(d):
            for j in range(d):
                if i == j:
                    axes[i, j].hist(samples[:, i], bins=20, color='steelblue')
                else:
                    axes[i, j].scatter(samples[:, j], samples[:, i],
                                        c=outputs, cmap='viridis', s=10, alpha=0.5)
                if i == d - 1:
                    axes[i, j].set_xlabel(param_names[j])
                if j == 0:
                    axes[i, j].set_ylabel(param_names[i])
        plt.tight_layout()
        return fig


def plot_tornado(sobol_result, output_label="目标函数"):
    """
    Tornado 图 (sensitivity_table.md 图 2)
    """
    sorted_items = sorted(sobol_result.items(), key=lambda x: x[1]["S1"])
    names = [item[0] for item in sorted_items]
    s1s = [item[1]["S1"] for item in sorted_items]
    sts = [item[1]["ST"] for item in sorted_items]

    y = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(y - 0.2, s1s, 0.4, label="一阶 $S_1$", color="steelblue")
    ax.barh(y + 0.2, sts, 0.4, label="总指数 $S_T$", color="orangered")
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel("Sobol 灵敏度指数")
    ax.set_title(f"{output_label} 单参数灵敏度排序")
    ax.legend()
    plt.tight_layout()
    return fig


# ============================================================
# 6. 网格/离散充分性检查 (v3.1.0, stage 6 硬规则; 源于 2026 国赛 A 题实测算例)
# ============================================================
# 规则 (references/stage_06_robustness.md "参数档的网格/离散充分性检查"):
#   触发: 扰动档使边界层敏感量相对基线档跳变 > BOUNDARY_JUMP_TRIGGER (默认 10×, 可按题覆盖)
#   判据: 同一时刻的边界敏感量在粗/细两档网格下的相对变化 > 20% → 该档欠分辨
#   处置: 该档从灵敏度排序中剔除, 报告与论文如实标注"网格受限、未量化"
# v3.1.1: 10×/20% 是规范锚定的**默认档**, 可按题覆盖 (grid_check_required 的
# trigger / check_grid_sufficiency 的 under_resolved_tol); 两档对比只声明
# "这两档的证据", 不构成网格无关性或参数充分性的普遍证明。
BOUNDARY_JUMP_TRIGGER = 10.0     # 边界层敏感量跳变倍数阈值 (默认档, 可覆盖)
GRID_UNDER_RESOLVED = 0.20       # 粗/细网格关键量相对变化阈值 (默认档, 可覆盖)


def boundary_jump_ratio(value_pert: float, value_base: float) -> float:
    """扰动档相对基线档的边界层敏感量跳变倍数 (判是否触发网格专项检验)。

    例 (合成值): 基线 12.0 → 扰动档 3000.0 时返回 250.0 (> 10 触发)。
    比值尺度无关, 小量级同样适用。
    """
    if value_base == 0:
        return float("inf") if value_pert != 0 else 1.0
    return abs(value_pert / value_base)


def grid_check_required(value_pert: float, value_base: float,
                        trigger: float = BOUNDARY_JUMP_TRIGGER) -> bool:
    """扰动档是否触发粗/细网格专项检验 (跳变倍数 > trigger)。

    trigger 默认 10× 只是规范默认档, 可按题覆盖 (不强加): 量纲/量级与样例不同的
    题按自身收敛历史设定。跳变比非有限 (NaN/inf) 时 fail-closed 返回 True ——
    无法判定"没有跳变"就必须做专项检验, 不允许静默放过。
    """
    if isinstance(trigger, bool) or not isinstance(trigger, (int, float)) \
            or not math.isfinite(trigger) or trigger <= 0:
        raise ValueError(f"跳变触发倍数 trigger 必须为正的有限数, 收到 {trigger!r}")
    ratio = boundary_jump_ratio(value_pert, value_base)
    if not math.isfinite(ratio):
        print(f"[网格充分性] 跳变比非有限 ({ratio}) → fail-closed: 触发粗/细网格专项检验")
        return True
    return ratio > trigger


def _validated_grids(grids) -> tuple:
    """校验粗/细两档网格必须是**真加密**: 两个不同的正有限数且 coarse < fine。

    相同档 (没有加密)、倒序档 (相对变化的分母写反)、非正/非有限/非数值档都会
    静默产出无意义结论 —— 一律 ValueError 拒收, 不让"看起来通过"的结论流出。
    """
    try:
        n_coarse, n_fine = grids
    except (TypeError, ValueError):
        raise ValueError(f"grids 必须是 (粗档, 细档) 二元组, 收到 {grids!r}")
    for name, n in (("粗档", n_coarse), ("细档", n_fine)):
        if isinstance(n, bool) or not isinstance(n, (int, float)):
            raise ValueError(f"{name}网格 {n!r} 不是数值")
        if not math.isfinite(n) or n <= 0:
            raise ValueError(f"{name}网格 {n!r} 不是正的有限数")
    if float(n_coarse) == float(n_fine):
        raise ValueError(f"粗/细网格相同 ({n_coarse!r}) —— 没有加密, 无从判定分辨率")
    if float(n_coarse) > float(n_fine):
        raise ValueError(f"网格倒序 (粗 {n_coarse!r} > 细 {n_fine!r}) —— "
                         "相对变化的分母会写反, 须按 (粗档, 细档) 传入")
    return n_coarse, n_fine


def check_grid_sufficiency(solve_at_grid, probe, grids, label="边界敏感量",
                           under_resolved_tol: float | None = None):
    """粗/细网格专项检验: 同一时刻的关键量在两种离散下的相对变化。

    Args:
        solve_at_grid: callable(n) -> 解对象; n 为网格节点数(或 1/步长)档位。
        probe: callable(solution) -> float; 取"同一时刻的边界敏感量"
            (二维场题取场内极值, 一维题取表面值), 时刻固定在早期/峰值时刻,
            两档必须取同一时刻同一物理位置。
        grids: (粗档 n, 细档 n) 二元组, 如 (64, 256); 必须 coarse < fine
            (相同/倒序/非正/NaN 一律 ValueError, 见 _validated_grids)。
        label: 报告用的量名。
        under_resolved_tol: 欠分辨判据的相对变化容限, None 取规范默认档
            GRID_UNDER_RESOLVED (20%); 可按题覆盖, 必须是正的有限数。
    Returns:
        dict: {"coarse"/"fine"/"values", "rel_change", "under_resolved",
            "finite", "tolerance", "scope_note", "note"}。相对变化以**细网格**为
        分母（参考误差定义）; under_resolved=True 即该档欠分辨, 不得进入灵敏度排序。
        两档值非有限(NaN/inf)时 fail-closed: under_resolved=True + finite=False
        ——未收敛的信号绝不能当"网格充分"放行（审查实测 NaN 曾被判通过）。
        scope_note 固定声明证据范围: 只有受检两档的对比证据, 不构成普遍充分性证明。
    """
    n_coarse, n_fine = _validated_grids(grids)
    tol = GRID_UNDER_RESOLVED if under_resolved_tol is None else under_resolved_tol
    if isinstance(tol, bool) or not isinstance(tol, (int, float)) \
            or not math.isfinite(tol) or tol <= 0:
        raise ValueError(f"under_resolved_tol 必须为正的有限数, 收到 {under_resolved_tol!r}")
    scope_note = (f"只声明受检两档网格 {n_coarse}/{n_fine} 的对比证据 (容限 {tol:.0%}); "
                  "不构成网格无关性或参数充分性的普遍证明, 阈值可按题覆盖")
    v_coarse = float(probe(solve_at_grid(n_coarse)))
    v_fine = float(probe(solve_at_grid(n_fine)))
    finite = math.isfinite(v_coarse) and math.isfinite(v_fine)
    if not finite:
        print(f"[网格充分性] {label}: {n_coarse} 档 {v_coarse} vs {n_fine} 档 {v_fine} "
              f"→ 非有限值, 无法判定")
        print("  ⚠ fail-closed: 视为欠分辨（该档剔除出排序, 并检查求解是否发散）")
        return {"coarse": n_coarse, "fine": n_fine,
                "values": {n_coarse: v_coarse, n_fine: v_fine},
                "rel_change": float("nan"), "under_resolved": True,
                "finite": False, "tolerance": tol, "scope_note": scope_note,
                "note": "非有限值, fail-closed 判欠分辨"}
    if v_fine != 0:
        rel_change = abs(v_coarse - v_fine) / abs(v_fine)
    else:
        # 细网格关键量为 0: 相对误差无定义, 只要粗档非 0 即视为不一致
        rel_change = 0.0 if v_coarse == 0 else float("inf")
    under = rel_change > tol
    report = {
        "coarse": n_coarse, "fine": n_fine,
        "values": {n_coarse: v_coarse, n_fine: v_fine},
        "rel_change": rel_change,
        "under_resolved": under,
        "finite": True,
        "tolerance": tol,
        "scope_note": scope_note,
        "note": "相对变化以细网格为分母",
    }
    print(f"[网格充分性] {label}: {n_coarse} 档 {v_coarse:.6g} vs "
          f"{n_fine} 档 {v_fine:.6g} → 相对细网格变化 {rel_change * 100:.2f}%")
    if under:
        print(f"  ⚠ 判欠分辨 (> {tol:.0%}): 该档从灵敏度排序中剔除, "
              f"报告与论文标注'网格受限、未量化'")
    else:
        print("  ✓ 网格充分: 该档数值可参与灵敏度排序")
    print(f"  · 证据范围: {scope_note}")
    return report


# ============================================================
# 主流程示例 (对应论文 §5.x + §6)
# ============================================================
if __name__ == "__main__":
    _demo_bootstrap()
    # SEIR 仿真示例
    result = simulate_seir(N=10000, I0=10, beta=0.3, sigma=0.2, gamma=0.1, kappa=0.05)
    print(f"峰值感染数: {result['peak_I']:.0f}")
    print(f"峰值时间: 第 {result['peak_t']:.1f} 天")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(result["t"], result["S"], label="易感 S")
    ax.plot(result["t"], result["E"], label="潜伏 E")
    ax.plot(result["t"], result["I"], label="感染 I", color='red', lw=2)
    ax.plot(result["t"], result["R"], label="康复 R")
    ax.set_xlabel("时间 (天)")
    ax.set_ylabel("人数")
    ax.set_title("改进 SEIR 模型仿真")
    ax.legend()
    plt.tight_layout()
    plt.savefig("figures/simulation_seir.png", dpi=300)

    # LHS 联合灵敏度
    def simulator(beta, sigma, gamma, kappa):
        r = simulate_seir(beta=beta, sigma=sigma, gamma=gamma, kappa=kappa)
        return r["peak_I"]

    baseline = {"beta": 0.3, "sigma": 0.2, "gamma": 0.1, "kappa": 0.05}
    sens_results, param_names = joint_sensitivity_lhs(
        simulator, baseline, perturbation_levels=[0.05, 0.10, 0.20], n_samples=100
    )
    for level, r in sens_results.items():
        print(f"\n扰动 ±{level*100:.0f}%:")
        print(f"  Peak I 5%-95% 区间: [{r['stats']['p5']:.0f}, {r['stats']['p95']:.0f}]")
        print(f"  CV: {r['stats']['cv']*100:.2f}%")

    # 画 LHS pairs (取 ±10% 档)
    fig = plot_lhs_pairs(sens_results[0.10]["samples"],
                          sens_results[0.10]["outputs"], param_names)
    plt.savefig("figures/simulation_lhs_pairs.png", dpi=300)
    print("\n所有图已保存 figures/")
