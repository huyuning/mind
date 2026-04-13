#!/usr/bin/env python3
"""
分形嵌套版：三节点复数图动态仿真

概要
- 在 triad_complex_core_simulation 的最小三节点复核基础上，构建分形嵌套结构：
  层级 0 是根三元核；每个三元核在下一层复制出 3 个子三元核（对应 s,w,a），形成 3^L 规模；
  子三元核的节点与父三元核同名节点之间存在下行/上行耦合，强度按层级缩放。
- 每个三元核内部仍是全连接复耦合；跨层连接采用缩放的复边权。

输出
- resonance_data/triad_complex_fractal_<timestamp>/
  - summary_*.json          : 指标汇总
  - state_series_*.npz      : 序列数据（时间、节点状态、层级映射、三元映射）
  - closure_global_*.png    : 全局闭合强度时间序列
  - closure_levels_*.png    : 各层闭合强度平均时间序列
  - closure_raster_*.png    : 各三元核闭合强度栅格图（时间×三元核索引）
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ----------- 基本配置与数据结构 -----------
TRIAD_NODE_NAMES = ("s", "w", "a")
TRIAD_NODE_IDX = {n: i for i, n in enumerate(TRIAD_NODE_NAMES)}


@dataclass
class NodeDynamics:
    alpha: float
    omega: float
    beta: float
    drive_amp: float
    drive_freq: float
    drive_phase: float


@dataclass
class TriadIntraEdge:
    src_local: str
    dst_local: str
    active: int
    base_strength: float
    strength_mod_amp: float
    strength_mod_freq: float
    base_phase: float
    phase_drift: float


@dataclass
class FractalCoupling:
    # 父 -> 子（下行）缩放；子 -> 父（上行）缩放
    down_strength_scale: float
    down_phase_drift: float
    up_strength_scale: float
    up_phase_drift: float


@dataclass
class SimulationSummary:
    levels: int
    triad_count: int
    node_count: int
    dt: float
    steps: int
    duration: float
    closure_global_mean: float
    closure_global_std: float
    closure_global_peak: float
    strong_core_fraction: float
    per_level_closure_mean: List[float]
    per_level_locking_mean: Dict[str, float]


# ----------- 构造分形三元结构 -----------
def build_triad_hierarchy(levels: int) -> Tuple[List[Tuple[int, ...]], Dict[Tuple[int, ...], int]]:
    """
    返回：
    - triads: 每个三元核的路径（层级序列），根为 ()，其子为 (0),(1),(2)...
    - triad_index: path -> triad_id
    """
    assert levels >= 1
    triads: List[Tuple[int, ...]] = []

    def dfs(path: Tuple[int, ...], depth: int):
        triads.append(path)
        if depth == levels - 1:
            return
        for k in range(3):  # 每层复制 3 个子三元核
            dfs(path + (k,), depth + 1)

    dfs((), 0)
    triad_index = {p: i for i, p in enumerate(triads)}
    return triads, triad_index


def triad_parent(path: Tuple[int, ...]) -> Tuple[int, ...] | None:
    if len(path) == 0:
        return None
    return path[:-1]


def triad_node_global_index(triad_id: int, local_node: str) -> int:
    return triad_id * 3 + TRIAD_NODE_IDX[local_node]


def create_output_dir() -> Path:
    out_dir = Path("./resonance_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


# ----------- 默认参数 -----------
def default_node_specs() -> List[NodeDynamics]:
    # 三元核内 3 个节点的缺省自振子参数（可在不同层按缩放修饰）
    return [
        NodeDynamics(alpha=0.12, omega=0.95, beta=0.08, drive_amp=0.04, drive_freq=0.10, drive_phase=0.0),
        NodeDynamics(alpha=0.10, omega=1.05, beta=0.09, drive_amp=0.03, drive_freq=0.08, drive_phase=1.2),
        NodeDynamics(alpha=0.11, omega=0.90, beta=0.07, drive_amp=0.035, drive_freq=0.09, drive_phase=2.1),
    ]


def default_intra_edges() -> List[TriadIntraEdge]:
    # 局部三元核内部的全连接复耦合
    return [
        TriadIntraEdge("s", "w", 1, 0.30, 0.06, 0.07, 0.20, 0.05),
        TriadIntraEdge("w", "s", 1, 0.28, 0.05, 0.09, 1.10, 0.04),
        TriadIntraEdge("w", "a", 1, 0.32, 0.07, 0.06, 0.70, 0.05),
        TriadIntraEdge("a", "w", 1, 0.26, 0.06, 0.05, 1.80, 0.05),
        TriadIntraEdge("a", "s", 1, 0.34, 0.08, 0.08, 1.35, 0.03),
        TriadIntraEdge("s", "a", 1, 0.29, 0.04, 0.05, 2.40, 0.06),
    ]


def default_fractal_coupling() -> FractalCoupling:
    return FractalCoupling(
        down_strength_scale=0.45,  # 父->子耦合强度缩放
        down_phase_drift=0.04,
        up_strength_scale=0.25,  # 子->父耦合强度缩放
        up_phase_drift=0.03,
    )


# ----------- 解析参数 -----------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="分形嵌套版三节点复数图仿真")
    p.add_argument("--levels", type=int, default=2, help="分形层数（>=1）")
    p.add_argument("--duration", type=float, default=150.0, help="总仿真时长")
    p.add_argument("--dt", type=float, default=0.02, help="时间步长")
    p.add_argument("--seed", type=int, default=260408, help="随机种子")
    p.add_argument("--closure-lambda", type=float, default=0.6, help="闭合强度三阶项系数")
    p.add_argument("--strong-threshold", type=float, default=2.2, help="强意识候选阈值")
    p.add_argument("--layer-omega-scale", type=float, default=0.92, help="层级向下的自频缩放")
    p.add_argument("--layer-drive-scale", type=float, default=0.85, help="层级向下的外驱缩放")
    return p.parse_args()


# ----------- 动力学构造 -----------
def edge_complex_value(base_strength: float, mod_amp: float, mod_freq: float, base_phase: float, phase_drift: float, t: float) -> complex:
    strength = base_strength + mod_amp * np.cos(2.0 * np.pi * mod_freq * t)
    strength = max(strength, 0.0)
    phase = base_phase + phase_drift * t
    return strength * np.exp(1j * phase)


def build_coupling_matrix(
    t: float,
    triads: List[Tuple[int, ...]],
    triad_index: Dict[Tuple[int, ...], int],
    node_specs_per_level: List[List[NodeDynamics]],
    intra_edges: List[TriadIntraEdge],
    fractal: FractalCoupling,
) -> np.ndarray:
    triad_count = len(triads)
    N = triad_count * 3
    Z = np.zeros((N, N), dtype=np.complex128)

    # 1) 三元核内部复耦合
    for triad_id, path in enumerate(triads):
        level = len(path)
        # intra
        for e in intra_edges:
            if not e.active:
                continue
            i_local = TRIAD_NODE_IDX[e.src_local]
            j_local = TRIAD_NODE_IDX[e.dst_local]
            i = triad_node_global_index(triad_id, e.src_local)
            j = triad_node_global_index(triad_id, e.dst_local)
            Z[i, j] = edge_complex_value(e.base_strength, e.strength_mod_amp, e.strength_mod_freq, e.base_phase, e.phase_drift, t)

    # 2) 父子同名节点的跨层复耦合（双向）
    for triad_id, path in enumerate(triads):
        parent = triad_parent(path)
        if parent is None:
            continue
        parent_id = triad_index[parent]
        child_kind = path[-1]  # 0->s,1->w,2->a
        name = TRIAD_NODE_NAMES[child_kind]
        child_node = triad_node_global_index(triad_id, name)
        parent_node = triad_node_global_index(parent_id, name)
        # 父->子
        Z[parent_node, child_node] += fractal.down_strength_scale * np.exp(1j * fractal.down_phase_drift * t)
        # 子->父
        Z[child_node, parent_node] += fractal.up_strength_scale * np.exp(1j * fractal.up_phase_drift * t)
    return Z


def node_params_for_level(base_specs: List[NodeDynamics], level: int, omega_scale: float, drive_scale: float) -> List[NodeDynamics]:
    out: List[NodeDynamics] = []
    for spec in base_specs:
        out.append(
            NodeDynamics(
                alpha=spec.alpha,
                omega=float(spec.omega * (omega_scale ** level)),
                beta=spec.beta,
                drive_amp=float(spec.drive_amp * (drive_scale ** level)),
                drive_freq=spec.drive_freq,
                drive_phase=spec.drive_phase,
            )
        )
    return out


def compute_derivative(
    X: np.ndarray,
    t: float,
    triads: List[Tuple[int, ...]],
    triad_index: Dict[Tuple[int, ...], int],
    node_specs_per_level: List[List[NodeDynamics]],
    intra_edges: List[TriadIntraEdge],
    fractal: FractalCoupling,
) -> np.ndarray:
    Z = build_coupling_matrix(t, triads, triad_index, node_specs_per_level, intra_edges, fractal)
    dX = np.zeros_like(X)
    for triad_id, path in enumerate(triads):
        level = len(path)
        specs = node_specs_per_level[level]
        for local_name, local_idx in TRIAD_NODE_IDX.items():
            idx = triad_node_global_index(triad_id, local_name)
            spec = specs[local_idx]
            self_term = (spec.alpha + 1j * spec.omega - spec.beta * (np.abs(X[idx]) ** 2)) * X[idx]
            drive_term = spec.drive_amp * np.exp(1j * (2.0 * np.pi * spec.drive_freq * t + spec.drive_phase))
            coupling_term = np.sum(Z[:, idx] * X) - Z[idx, idx] * X[idx]
            dX[idx] = self_term + drive_term + coupling_term
    return dX


def rk4_step(
    X: np.ndarray,
    t: float,
    dt: float,
    triads: List[Tuple[int, ...]],
    triad_index: Dict[Tuple[int, ...], int],
    node_specs_per_level: List[List[NodeDynamics]],
    intra_edges: List[TriadIntraEdge],
    fractal: FractalCoupling,
) -> np.ndarray:
    k1 = compute_derivative(X, t, triads, triad_index, node_specs_per_level, intra_edges, fractal)
    k2 = compute_derivative(X + 0.5 * dt * k1, t + 0.5 * dt, triads, triad_index, node_specs_per_level, intra_edges, fractal)
    k3 = compute_derivative(X + 0.5 * dt * k2, t + 0.5 * dt, triads, triad_index, node_specs_per_level, intra_edges, fractal)
    k4 = compute_derivative(X + dt * k3, t + dt, triads, triad_index, node_specs_per_level, intra_edges, fractal)
    return X + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


# ----------- 指标与绘图 -----------
def closure_strength_triads(X: np.ndarray, triad_count: int, closure_lambda: float) -> np.ndarray:
    closure = np.zeros(triad_count, dtype=np.float64)
    for triad_id in range(triad_count):
        s = np.abs(X[triad_id * 3 + 0])
        w = np.abs(X[triad_id * 3 + 1])
        a = np.abs(X[triad_id * 3 + 2])
        closure[triad_id] = s * w + w * a + a * s + closure_lambda * s * w * a
    return closure


def pair_locking_levelwise(node_series: np.ndarray, triads: List[Tuple[int, ...]]) -> Dict[str, float]:
    phases = np.angle(node_series)
    pairs = [(0, 1, "s-w"), (1, 2, "w-a"), (2, 0, "a-s")]
    levels = [len(p) for p in triads]
    max_level = max(levels) if levels else 0
    out: Dict[str, float] = {}
    for i, j, label in pairs:
        vals: List[float] = []
        for lvl in range(max_level + 1):
            idxs = [k for k, p in enumerate(triads) if len(p) == lvl]
            if not idxs:
                continue
            # 把同层所有三元核节点拼一起计算锁相
            delta = []
            for triad_id in idxs:
                ni = triad_id * 3 + i
                nj = triad_id * 3 + j
                delta.append(phases[:, ni] - phases[:, nj])
            delta_all = np.concatenate(delta, axis=0)
            vals.append(float(np.abs(np.mean(np.exp(1j * delta_all)))))
        out[f"{label}_mean"] = float(np.mean(vals)) if vals else 0.0
    return out


def plot_global_closure(path: Path, times: np.ndarray, closure_global: np.ndarray, threshold: float) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(times, closure_global, color="tab:red", linewidth=1.6, label="T_psi_global_mean")
    ax.axhline(threshold, color="black", linestyle="--", linewidth=1.0, label="strong threshold")
    ax.set_xlabel("time")
    ax.set_ylabel("T_psi (mean over triads)")
    ax.set_title("Fractal Triad: Global Closure Strength")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_levels_closure(path: Path, times: np.ndarray, closure_levels: np.ndarray) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for lvl in range(closure_levels.shape[1]):
        ax.plot(times, closure_levels[:, lvl], linewidth=1.4, label=f"level {lvl}")
    ax.set_xlabel("time")
    ax.set_ylabel("T_psi (mean per level)")
    ax.set_title("Fractal Triad: Level-wise Closure Strength")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_closure_raster(path: Path, closure_raster: np.ndarray) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(closure_raster.T, aspect="auto", origin="lower", cmap="viridis")
    ax.set_xlabel("time index")
    ax.set_ylabel("triad id")
    ax.set_title("Fractal Triad: T_psi Raster (triads x time)")
    fig.colorbar(im, ax=ax, orientation="vertical", label="T_psi")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


# ----------- 主流程 -----------
def simulate(args: argparse.Namespace) -> Tuple[Dict[str, object], Path]:
    rng = np.random.default_rng(args.seed)
    triads, triad_index = build_triad_hierarchy(args.levels)
    triad_count = len(triads)
    node_count = triad_count * 3

    # 层级参数表
    base_node_specs = default_node_specs()
    node_specs_per_level: List[List[NodeDynamics]] = []
    max_level = max(len(p) for p in triads)
    for lvl in range(max_level + 1):
        node_specs_per_level.append(
            node_params_for_level(base_node_specs, lvl, args.layer_omega_scale, args.layer_drive_scale)
        )

    intra_edges = default_intra_edges()
    fractal_cfg = default_fractal_coupling()

    steps = int(np.floor(args.duration / args.dt))
    times = np.linspace(0.0, args.dt * (steps - 1), steps, dtype=np.float64)

    # 初值
    X = (0.15 * rng.normal(size=node_count) + 1j * 0.15 * rng.normal(size=node_count)).astype(np.complex128)

    node_series = np.zeros((steps, node_count), dtype=np.complex128)
    closure_raster = np.zeros((steps, triad_count), dtype=np.float64)
    closure_levels = np.zeros((steps, max_level + 1), dtype=np.float64)
    closure_global = np.zeros(steps, dtype=np.float64)

    level_groups: List[List[int]] = []
    for lvl in range(max_level + 1):
        level_groups.append([k for k, p in enumerate(triads) if len(p) == lvl])

    for ti, t in enumerate(times):
        node_series[ti] = X
        triad_closure = closure_strength_triads(X, triad_count, args.closure_lambda)
        closure_raster[ti] = triad_closure
        closure_global[ti] = float(np.mean(triad_closure))
        for lvl in range(max_level + 1):
            ids = level_groups[lvl]
            closure_levels[ti, lvl] = float(np.mean(triad_closure[ids])) if ids else 0.0
        # 演化一步
        X = rk4_step(
            X,
            float(t),
            args.dt,
            triads,
            triad_index,
            node_specs_per_level,
            intra_edges,
            fractal_cfg,
        )

    # 指标
    pair_metrics = pair_locking_levelwise(node_series, triads)
    summary = SimulationSummary(
        levels=int(args.levels),
        triad_count=int(triad_count),
        node_count=int(node_count),
        dt=float(args.dt),
        steps=steps,
        duration=float(times[-1]) if len(times) else 0.0,
        closure_global_mean=float(np.mean(closure_global)),
        closure_global_std=float(np.std(closure_global)),
        closure_global_peak=float(np.max(closure_global)),
        strong_core_fraction=float(np.mean(closure_global >= args.strong_threshold)),
        per_level_closure_mean=[float(np.mean(closure_levels[:, lvl])) for lvl in range(max_level + 1)],
        per_level_locking_mean=pair_metrics,
    )

    # 输出
    out_root = create_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / f"triad_complex_fractal_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        run_dir / f"state_series_{timestamp}.npz",
        times=times,
        node_series=node_series,
        closure_raster=closure_raster,
        closure_levels=closure_levels,
        closure_global=closure_global,
        triads=np.array([np.array(p, dtype=np.int32) for p in triads], dtype=object),
    )

    result: Dict[str, object] = {
        "model": "triad_complex_fractal",
        "timestamp": timestamp,
        "levels": int(args.levels),
        "triad_count": int(triad_count),
        "node_count": int(node_count),
        "summary": asdict(summary),
        "thresholds": {
            "strong_threshold": float(args.strong_threshold),
            "closure_lambda": float(args.closure_lambda),
        },
        "notes": [
            "分形层数决定三元核总数为 sum_{l=0}^{L-1} 3^l。",
            "父子同名节点存在双向复耦合，强度按层级缩放。",
            "闭合强度 T_psi 用于近似评估稳固三角形成程度（全局与分层）。",
        ],
    }
    (run_dir / f"summary_{timestamp}.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    plot_global_closure(run_dir / f"closure_global_{timestamp}.png", times, closure_global, args.strong_threshold)
    plot_levels_closure(run_dir / f"closure_levels_{timestamp}.png", times, closure_levels)
    plot_closure_raster(run_dir / f"closure_raster_{timestamp}.png", closure_raster)

    return result, run_dir


def main() -> None:
    args = parse_args()
    result, run_dir = simulate(args)
    print(json.dumps({"run_dir": str(run_dir), "summary": result["summary"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

