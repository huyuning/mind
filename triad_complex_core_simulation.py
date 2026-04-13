#!/usr/bin/env python3
"""
三节点复数图动态仿真框架

目标
- 用最小三节点全连接复数图模拟意识本源核的动态变化；
- 跟踪节点复状态 xi_i(t) 与边复耦合 z_ij(t) 的协同演化；
- 输出三角闭合强度 T_psi、节点幅度/相位、边强度/相位等可视化结果。

模型
- 节点: s(自模拟), w(自覆写), a(自回归)
- 边: 全连接 0-1 骨架上的复数耦合 z_ij(t)=A_ij r_ij(t) exp(i phi_ij(t))
- 动力学: 采用最小 Stuart-Landau 风格复振子

输出
- resonance_data/triad_complex_core_<timestamp>/
  - summary_<timestamp>.json
  - state_series_<timestamp>.npz
  - amplitudes_<timestamp>.png
  - phases_<timestamp>.png
  - closure_strength_<timestamp>.png
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


NODE_NAMES = ("s", "w", "a")
NODE_INDEX = {name: idx for idx, name in enumerate(NODE_NAMES)}


@dataclass
class NodeDynamics:
    alpha: float
    omega: float
    beta: float
    drive_amp: float
    drive_freq: float
    drive_phase: float


@dataclass
class EdgeDynamics:
    src: str
    dst: str
    active: int
    base_strength: float
    strength_mod_amp: float
    strength_mod_freq: float
    base_phase: float
    phase_drift: float


@dataclass
class SimulationSummary:
    dt: float
    steps: int
    duration: float
    closure_mean: float
    closure_std: float
    closure_peak: float
    strong_core_fraction: float
    node_mean_amplitudes: Dict[str, float]
    node_mean_phases: Dict[str, float]
    mean_pair_locking: Dict[str, float]


def create_output_dir() -> Path:
    out_dir = Path("./resonance_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="三节点复数图动态仿真框架")
    parser.add_argument("--duration", type=float, default=200.0, help="总仿真时长")
    parser.add_argument("--dt", type=float, default=0.02, help="时间步长")
    parser.add_argument("--seed", type=int, default=20260408, help="随机种子")
    parser.add_argument(
        "--closure-lambda",
        type=float,
        default=0.6,
        help="三角闭合强度中的三阶增益系数 lambda",
    )
    parser.add_argument(
        "--strong-threshold",
        type=float,
        default=2.0,
        help="判断进入强意识候选区的闭合强度阈值",
    )
    return parser.parse_args()


def default_node_specs() -> List[NodeDynamics]:
    return [
        NodeDynamics(alpha=0.12, omega=0.95, beta=0.08, drive_amp=0.04, drive_freq=0.12, drive_phase=0.0),
        NodeDynamics(alpha=0.10, omega=1.05, beta=0.09, drive_amp=0.03, drive_freq=0.09, drive_phase=1.1),
        NodeDynamics(alpha=0.11, omega=0.88, beta=0.07, drive_amp=0.035, drive_freq=0.11, drive_phase=2.0),
    ]


def default_edge_specs() -> List[EdgeDynamics]:
    return [
        EdgeDynamics("s", "w", 1, 0.30, 0.08, 0.08, 0.25, 0.06),
        EdgeDynamics("w", "s", 1, 0.28, 0.06, 0.10, 1.15, 0.04),
        EdgeDynamics("w", "a", 1, 0.32, 0.09, 0.07, 0.70, 0.05),
        EdgeDynamics("a", "w", 1, 0.26, 0.07, 0.06, 1.80, 0.05),
        EdgeDynamics("a", "s", 1, 0.34, 0.10, 0.09, 1.35, 0.03),
        EdgeDynamics("s", "a", 1, 0.29, 0.05, 0.05, 2.40, 0.07),
    ]


def build_adjacency(edges: List[EdgeDynamics]) -> np.ndarray:
    adjacency = np.zeros((3, 3), dtype=np.int8)
    for edge in edges:
        adjacency[NODE_INDEX[edge.src], NODE_INDEX[edge.dst]] = edge.active
    return adjacency


def edge_complex_value(edge: EdgeDynamics, t: float) -> complex:
    if not edge.active:
        return 0.0 + 0.0j
    strength = edge.base_strength + edge.strength_mod_amp * np.cos(2.0 * np.pi * edge.strength_mod_freq * t)
    strength = max(strength, 0.0)
    phase = edge.base_phase + edge.phase_drift * t
    return edge.active * strength * np.exp(1j * phase)


def compute_coupling_matrix(edges: List[EdgeDynamics], t: float) -> np.ndarray:
    z = np.zeros((3, 3), dtype=np.complex128)
    for edge in edges:
        i = NODE_INDEX[edge.src]
        j = NODE_INDEX[edge.dst]
        z[i, j] = edge_complex_value(edge, t)
    return z


def compute_derivative(
    x: np.ndarray,
    t: float,
    node_specs: List[NodeDynamics],
    edge_specs: List[EdgeDynamics],
) -> np.ndarray:
    z = compute_coupling_matrix(edge_specs, t)
    dx = np.zeros_like(x)
    for i, spec in enumerate(node_specs):
        self_term = (spec.alpha + 1j * spec.omega - spec.beta * (np.abs(x[i]) ** 2)) * x[i]
        drive_term = spec.drive_amp * np.exp(1j * (2.0 * np.pi * spec.drive_freq * t + spec.drive_phase))
        coupling_term = np.sum(z[:, i] * x) - z[i, i] * x[i]
        dx[i] = self_term + drive_term + coupling_term
    return dx


def rk4_step(
    x: np.ndarray,
    t: float,
    dt: float,
    node_specs: List[NodeDynamics],
    edge_specs: List[EdgeDynamics],
) -> np.ndarray:
    k1 = compute_derivative(x, t, node_specs, edge_specs)
    k2 = compute_derivative(x + 0.5 * dt * k1, t + 0.5 * dt, node_specs, edge_specs)
    k3 = compute_derivative(x + 0.5 * dt * k2, t + 0.5 * dt, node_specs, edge_specs)
    k4 = compute_derivative(x + dt * k3, t + dt, node_specs, edge_specs)
    return x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def closure_strength(node_state: np.ndarray, closure_lambda: float) -> float:
    s_amp, w_amp, a_amp = np.abs(node_state)
    return float(
        s_amp * w_amp
        + w_amp * a_amp
        + a_amp * s_amp
        + closure_lambda * s_amp * w_amp * a_amp
    )


def pair_locking(node_series: np.ndarray) -> Dict[str, float]:
    phase = np.angle(node_series)
    pairs = [(0, 1, "s-w"), (1, 2, "w-a"), (2, 0, "a-s")]
    out: Dict[str, float] = {}
    for i, j, label in pairs:
        delta = phase[:, i] - phase[:, j]
        out[label] = float(np.abs(np.mean(np.exp(1j * delta))))
    return out


def simulate(args: argparse.Namespace) -> Tuple[Dict[str, object], Path]:
    rng = np.random.default_rng(args.seed)
    node_specs = default_node_specs()
    edge_specs = default_edge_specs()

    steps = int(np.floor(args.duration / args.dt))
    times = np.linspace(0.0, args.dt * (steps - 1), steps, dtype=np.float64)

    x = (
        0.2 * rng.normal(size=3)
        + 1j * 0.2 * rng.normal(size=3)
    ).astype(np.complex128)

    node_series = np.zeros((steps, 3), dtype=np.complex128)
    closure_series = np.zeros(steps, dtype=np.float64)
    edge_strength_series = np.zeros((steps, 3, 3), dtype=np.float64)
    edge_phase_series = np.zeros((steps, 3, 3), dtype=np.float64)

    for step, t in enumerate(times):
        node_series[step] = x
        closure_series[step] = closure_strength(x, args.closure_lambda)

        z = compute_coupling_matrix(edge_specs, float(t))
        edge_strength_series[step] = np.abs(z)
        edge_phase_series[step] = np.angle(z)

        x = rk4_step(x, float(t), args.dt, node_specs, edge_specs)

    amplitudes = np.abs(node_series)
    phases = np.angle(node_series)

    pair_metrics = pair_locking(node_series)
    summary = SimulationSummary(
        dt=float(args.dt),
        steps=steps,
        duration=float(times[-1]) if len(times) else 0.0,
        closure_mean=float(np.mean(closure_series)),
        closure_std=float(np.std(closure_series)),
        closure_peak=float(np.max(closure_series)),
        strong_core_fraction=float(np.mean(closure_series >= args.strong_threshold)),
        node_mean_amplitudes={name: float(np.mean(amplitudes[:, idx])) for idx, name in enumerate(NODE_NAMES)},
        node_mean_phases={name: float(np.angle(np.mean(np.exp(1j * phases[:, idx])))) for idx, name in enumerate(NODE_NAMES)},
        mean_pair_locking=pair_metrics,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = create_output_dir() / f"triad_complex_core_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        run_dir / f"state_series_{timestamp}.npz",
        times=times,
        node_series=node_series,
        amplitudes=amplitudes,
        phases=phases,
        closure_series=closure_series,
        edge_strength_series=edge_strength_series,
        edge_phase_series=edge_phase_series,
        adjacency=build_adjacency(edge_specs),
    )

    result: Dict[str, object] = {
        "model": "triad_complex_core",
        "timestamp": timestamp,
        "node_order": list(NODE_NAMES),
        "node_specs": [asdict(spec) for spec in node_specs],
        "edge_specs": [asdict(spec) for spec in edge_specs],
        "summary": asdict(summary),
        "thresholds": {
            "strong_threshold": float(args.strong_threshold),
            "closure_lambda": float(args.closure_lambda),
        },
        "notes": [
            "三节点分别对应双向自模拟(s)、双向自覆写(w)、双向自回归(a)。",
            "0-1 骨架由边 active 指定，复数边权同时编码耦合强度与相位偏向。",
            "闭合强度 T_psi 用于近似表征稳固三角的形成程度。",
        ],
    }
    (run_dir / f"summary_{timestamp}.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    plot_amplitudes(run_dir / f"amplitudes_{timestamp}.png", times, amplitudes)
    plot_phases(run_dir / f"phases_{timestamp}.png", times, phases)
    plot_closure(
        run_dir / f"closure_strength_{timestamp}.png",
        times,
        closure_series,
        args.strong_threshold,
    )

    return result, run_dir


def plot_amplitudes(output_path: Path, times: np.ndarray, amplitudes: np.ndarray) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for idx, name in enumerate(NODE_NAMES):
        ax.plot(times, amplitudes[:, idx], label=f"{name} amplitude", linewidth=1.6)
    ax.set_title("Triad Complex Core: Node Amplitudes")
    ax.set_xlabel("time")
    ax.set_ylabel("|xi(t)|")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_phases(output_path: Path, times: np.ndarray, phases: np.ndarray) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for idx, name in enumerate(NODE_NAMES):
        ax.plot(times, phases[:, idx], label=f"{name} phase", linewidth=1.4)
    ax.set_title("Triad Complex Core: Node Phases")
    ax.set_xlabel("time")
    ax.set_ylabel("arg(xi(t))")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_closure(output_path: Path, times: np.ndarray, closure_series: np.ndarray, threshold: float) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(times, closure_series, color="tab:red", linewidth=1.6, label="T_psi")
    ax.axhline(threshold, color="black", linestyle="--", linewidth=1.0, label="strong threshold")
    ax.set_title("Triad Complex Core: Closure Strength")
    ax.set_xlabel("time")
    ax.set_ylabel("T_psi")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    result, run_dir = simulate(args)
    print(json.dumps({"run_dir": str(run_dir), "summary": result["summary"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
