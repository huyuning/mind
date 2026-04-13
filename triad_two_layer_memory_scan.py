#!/usr/bin/env python3
"""
两层三节点全连接模型仿真

模型说明
- 第一层（核心层）: 三节点全连接，同频运行，频率取核心最高频率 omega_core
- 第二层（内存阈值层）: 三节点全连接，分别取低于/等于/高于内存覆写频率
- 跨层连接: 默认采用一一对应映射
    s <-> l, w <-> e, a <-> h
- 节点动力学: Stuart-Landau 风格复振子
- 数值求解: RK4

输出
- resonance_data/triad_two_layer_memory_scan_<timestamp>/
  - summary_<timestamp>.json
  - state_series_<timestamp>.npz
  - amplitudes_<timestamp>.png
  - phases_<timestamp>.png
  - closure_<timestamp>.png
  - locking_<timestamp>.png
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


CORE_NAMES = ("s", "w", "a")
MEM_NAMES = ("l", "e", "h")
NODE_NAMES = CORE_NAMES + MEM_NAMES
NODE_INDEX = {name: idx for idx, name in enumerate(NODE_NAMES)}


@dataclass
class NodeSpec:
    alpha: float
    omega: float
    beta: float
    drive_amp: float
    drive_freq: float
    drive_phase: float


@dataclass
class EdgeSpec:
    src: str
    dst: str
    active: int
    base_strength: float
    strength_mod_amp: float
    strength_mod_freq: float
    base_phase: float
    phase_drift: float


@dataclass
class Summary:
    dt: float
    steps: int
    duration: float
    omega_core: float
    omega_mem: float
    omega_low: float
    omega_equal: float
    omega_high: float
    core_closure_mean: float
    mem_closure_mean: float
    cross_locking_mean: float
    strong_core_fraction: float
    strong_mem_fraction: float
    node_mean_amplitudes: Dict[str, float]
    node_mean_phases: Dict[str, float]
    pair_locking: Dict[str, float]


def create_output_dir() -> Path:
    out_dir = Path("./resonance_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="两层三节点全连接模型仿真")
    p.add_argument("--duration", type=float, default=120.0, help="总仿真时长")
    p.add_argument("--dt", type=float, default=0.02, help="积分步长")
    p.add_argument("--seed", type=int, default=20260408, help="随机种子")
    p.add_argument("--omega-mem", type=float, default=1.0, help="内存覆写频率 omega_mem")
    p.add_argument(
        "--omega-core-ratio",
        type=float,
        default=1.15,
        help="核心层频率相对 omega_mem 的比例（核心最高频率）",
    )
    p.add_argument("--low-ratio", type=float, default=0.92, help="低于内存频率节点比例")
    p.add_argument("--equal-ratio", type=float, default=1.0, help="等于内存频率节点比例")
    p.add_argument("--high-ratio", type=float, default=1.08, help="高于内存频率节点比例")
    p.add_argument("--closure-lambda", type=float, default=0.6, help="闭合强度三阶增益项")
    p.add_argument("--core-threshold", type=float, default=2.2, help="核心层强意识候选阈值")
    p.add_argument("--mem-threshold", type=float, default=1.2, help="内存层强耦合阈值")
    return p.parse_args()


def build_node_specs(args: argparse.Namespace) -> List[NodeSpec]:
    omega_mem = args.omega_mem
    omega_core = args.omega_core_ratio * omega_mem
    omega_low = args.low_ratio * omega_mem
    omega_equal = args.equal_ratio * omega_mem
    omega_high = args.high_ratio * omega_mem

    return [
        # 核心层: 同频核心
        NodeSpec(alpha=0.12, omega=omega_core, beta=0.08, drive_amp=0.035, drive_freq=0.08, drive_phase=0.0),
        NodeSpec(alpha=0.11, omega=omega_core, beta=0.08, drive_amp=0.030, drive_freq=0.08, drive_phase=2.0 * np.pi / 3.0),
        NodeSpec(alpha=0.10, omega=omega_core, beta=0.08, drive_amp=0.028, drive_freq=0.08, drive_phase=4.0 * np.pi / 3.0),
        # 内存阈值层: 低于 / 等于 / 高于
        NodeSpec(alpha=0.08, omega=omega_low, beta=0.07, drive_amp=0.018, drive_freq=0.05, drive_phase=0.2),
        NodeSpec(alpha=0.09, omega=omega_equal, beta=0.07, drive_amp=0.020, drive_freq=0.05, drive_phase=1.8),
        NodeSpec(alpha=0.08, omega=omega_high, beta=0.07, drive_amp=0.022, drive_freq=0.05, drive_phase=3.7),
    ]


def build_edge_specs(args: argparse.Namespace) -> List[EdgeSpec]:
    omega_core = args.omega_core_ratio * args.omega_mem
    omega_mem = args.omega_mem

    edges: List[EdgeSpec] = []

    # 第一层: 核心三角，全连接，同频主相位
    core_pairs = [("s", "w"), ("w", "s"), ("w", "a"), ("a", "w"), ("a", "s"), ("s", "a")]
    core_strengths = {
        ("s", "w"): 0.85,
        ("w", "s"): 0.78,
        ("w", "a"): 0.82,
        ("a", "w"): 0.74,
        ("a", "s"): 0.88,
        ("s", "a"): 0.76,
    }
    core_phases = {
        ("s", "w"): 0.0,
        ("w", "s"): 0.0,
        ("w", "a"): 2.0 * np.pi / 3.0,
        ("a", "w"): 2.0 * np.pi / 3.0,
        ("a", "s"): 4.0 * np.pi / 3.0,
        ("s", "a"): 4.0 * np.pi / 3.0,
    }
    for src, dst in core_pairs:
        edges.append(
            EdgeSpec(
                src=src,
                dst=dst,
                active=1,
                base_strength=core_strengths[(src, dst)],
                strength_mod_amp=0.04,
                strength_mod_freq=0.03 * omega_core,
                base_phase=core_phases[(src, dst)],
                phase_drift=0.0,  # 初始同频核心
            )
        )

    # 第二层: 阈值层三角，全连接，频率通过节点自振体现
    mem_pairs = [("l", "e"), ("e", "l"), ("e", "h"), ("h", "e"), ("h", "l"), ("l", "h")]
    mem_strengths = {
        ("l", "e"): 0.38,
        ("e", "l"): 0.34,
        ("e", "h"): 0.42,
        ("h", "e"): 0.36,
        ("h", "l"): 0.33,
        ("l", "h"): 0.31,
    }
    mem_phases = {
        ("l", "e"): 0.1,
        ("e", "l"): -0.1,
        ("e", "h"): 1.1,
        ("h", "e"): -1.0,
        ("h", "l"): 2.2,
        ("l", "h"): -2.0,
    }
    for src, dst in mem_pairs:
        edges.append(
            EdgeSpec(
                src=src,
                dst=dst,
                active=1,
                base_strength=mem_strengths[(src, dst)],
                strength_mod_amp=0.03,
                strength_mod_freq=0.04 * omega_mem,
                base_phase=mem_phases[(src, dst)],
                phase_drift=0.015,  # 第二层允许缓慢调频漂移
            )
        )

    # 跨层: 一一对应
    cross_map = [("s", "l"), ("w", "e"), ("a", "h")]
    for src, dst in cross_map:
        edges.append(
            EdgeSpec(
                src=src,
                dst=dst,
                active=1,
                base_strength=0.30,
                strength_mod_amp=0.02,
                strength_mod_freq=0.025 * omega_mem,
                base_phase=0.0,
                phase_drift=0.01,
            )
        )
        edges.append(
            EdgeSpec(
                src=dst,
                dst=src,
                active=1,
                base_strength=0.22,
                strength_mod_amp=0.02,
                strength_mod_freq=0.020 * omega_mem,
                base_phase=0.15,
                phase_drift=0.01,
            )
        )

    return edges


def initial_state() -> np.ndarray:
    # 核心层强、阈值层弱
    x0 = np.zeros(6, dtype=np.complex128)
    x0[NODE_INDEX["s"]] = 1.00 * np.exp(1j * 0.0)
    x0[NODE_INDEX["w"]] = 0.98 * np.exp(1j * (2.0 * np.pi / 3.0))
    x0[NODE_INDEX["a"]] = 0.96 * np.exp(1j * (4.0 * np.pi / 3.0))
    x0[NODE_INDEX["l"]] = 0.25 * np.exp(1j * 0.2)
    x0[NODE_INDEX["e"]] = 0.25 * np.exp(1j * 1.8)
    x0[NODE_INDEX["h"]] = 0.25 * np.exp(1j * 3.7)
    return x0


def edge_complex_value(edge: EdgeSpec, t: float) -> complex:
    if not edge.active:
        return 0.0 + 0.0j
    strength = edge.base_strength + edge.strength_mod_amp * np.cos(2.0 * np.pi * edge.strength_mod_freq * t)
    strength = max(strength, 0.0)
    phase = edge.base_phase + edge.phase_drift * t
    return strength * np.exp(1j * phase)


def coupling_matrix(edges: List[EdgeSpec], t: float) -> np.ndarray:
    z = np.zeros((6, 6), dtype=np.complex128)
    for edge in edges:
        i = NODE_INDEX[edge.src]
        j = NODE_INDEX[edge.dst]
        z[i, j] = edge_complex_value(edge, t)
    return z


def derivative(x: np.ndarray, t: float, node_specs: List[NodeSpec], edge_specs: List[EdgeSpec]) -> np.ndarray:
    z = coupling_matrix(edge_specs, t)
    dx = np.zeros_like(x)
    for i, spec in enumerate(node_specs):
        self_term = (spec.alpha + 1j * spec.omega - spec.beta * (np.abs(x[i]) ** 2)) * x[i]
        drive_term = spec.drive_amp * np.exp(1j * (2.0 * np.pi * spec.drive_freq * t + spec.drive_phase))
        coupling_term = np.sum(z[:, i] * x) - z[i, i] * x[i]
        dx[i] = self_term + drive_term + coupling_term
    return dx


def rk4_step(x: np.ndarray, t: float, dt: float, node_specs: List[NodeSpec], edge_specs: List[EdgeSpec]) -> np.ndarray:
    k1 = derivative(x, t, node_specs, edge_specs)
    k2 = derivative(x + 0.5 * dt * k1, t + 0.5 * dt, node_specs, edge_specs)
    k3 = derivative(x + 0.5 * dt * k2, t + 0.5 * dt, node_specs, edge_specs)
    k4 = derivative(x + dt * k3, t + dt, node_specs, edge_specs)
    return x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def triad_closure(amplitudes: np.ndarray, closure_lambda: float) -> float:
    x, y, z = amplitudes
    return float(x * y + y * z + z * x + closure_lambda * x * y * z)


def pair_locking(series: np.ndarray, i: int, j: int) -> float:
    delta = np.angle(series[:, i]) - np.angle(series[:, j])
    return float(np.abs(np.mean(np.exp(1j * delta))))


def simulate(args: argparse.Namespace) -> Tuple[Dict[str, object], Path]:
    node_specs = build_node_specs(args)
    edge_specs = build_edge_specs(args)

    steps = int(np.floor(args.duration / args.dt))
    times = np.linspace(0.0, args.dt * (steps - 1), steps, dtype=np.float64)
    x = initial_state()

    node_series = np.zeros((steps, 6), dtype=np.complex128)
    core_closure_series = np.zeros(steps, dtype=np.float64)
    mem_closure_series = np.zeros(steps, dtype=np.float64)
    cross_locking_series = np.zeros(steps, dtype=np.float64)

    for step, t in enumerate(times):
        node_series[step] = x
        amp = np.abs(x)
        core_closure_series[step] = triad_closure(amp[:3], args.closure_lambda)
        mem_closure_series[step] = triad_closure(amp[3:], args.closure_lambda)

        phase_core = np.angle(x[:3])
        phase_mem = np.angle(x[3:])
        corr = np.abs(np.mean(np.exp(1j * (phase_core - phase_mem))))
        cross_locking_series[step] = float(corr)

        x = rk4_step(x, float(t), args.dt, node_specs, edge_specs)

    amplitudes = np.abs(node_series)
    phases = np.angle(node_series)

    omega_core = args.omega_core_ratio * args.omega_mem
    omega_low = args.low_ratio * args.omega_mem
    omega_equal = args.equal_ratio * args.omega_mem
    omega_high = args.high_ratio * args.omega_mem

    summary = Summary(
        dt=float(args.dt),
        steps=steps,
        duration=float(times[-1]) if len(times) else 0.0,
        omega_core=float(omega_core),
        omega_mem=float(args.omega_mem),
        omega_low=float(omega_low),
        omega_equal=float(omega_equal),
        omega_high=float(omega_high),
        core_closure_mean=float(np.mean(core_closure_series)),
        mem_closure_mean=float(np.mean(mem_closure_series)),
        cross_locking_mean=float(np.mean(cross_locking_series)),
        strong_core_fraction=float(np.mean(core_closure_series >= args.core_threshold)),
        strong_mem_fraction=float(np.mean(mem_closure_series >= args.mem_threshold)),
        node_mean_amplitudes={name: float(np.mean(amplitudes[:, idx])) for idx, name in enumerate(NODE_NAMES)},
        node_mean_phases={name: float(np.angle(np.mean(np.exp(1j * phases[:, idx])))) for idx, name in enumerate(NODE_NAMES)},
        pair_locking={
            "core_s_w": pair_locking(node_series, NODE_INDEX["s"], NODE_INDEX["w"]),
            "core_w_a": pair_locking(node_series, NODE_INDEX["w"], NODE_INDEX["a"]),
            "core_a_s": pair_locking(node_series, NODE_INDEX["a"], NODE_INDEX["s"]),
            "mem_l_e": pair_locking(node_series, NODE_INDEX["l"], NODE_INDEX["e"]),
            "mem_e_h": pair_locking(node_series, NODE_INDEX["e"], NODE_INDEX["h"]),
            "mem_h_l": pair_locking(node_series, NODE_INDEX["h"], NODE_INDEX["l"]),
            "cross_s_l": pair_locking(node_series, NODE_INDEX["s"], NODE_INDEX["l"]),
            "cross_w_e": pair_locking(node_series, NODE_INDEX["w"], NODE_INDEX["e"]),
            "cross_a_h": pair_locking(node_series, NODE_INDEX["a"], NODE_INDEX["h"]),
        },
    )

    out_root = create_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / f"triad_two_layer_memory_scan_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        run_dir / f"state_series_{timestamp}.npz",
        times=times,
        node_series=node_series,
        amplitudes=amplitudes,
        phases=phases,
        core_closure_series=core_closure_series,
        mem_closure_series=mem_closure_series,
        cross_locking_series=cross_locking_series,
    )

    result: Dict[str, object] = {
        "model": "triad_two_layer_memory_scan",
        "timestamp": timestamp,
        "node_order": list(NODE_NAMES),
        "node_specs": [asdict(spec) for spec in node_specs],
        "edge_specs": [asdict(spec) for spec in edge_specs],
        "summary": asdict(summary),
        "thresholds": {
            "core_threshold": float(args.core_threshold),
            "mem_threshold": float(args.mem_threshold),
            "closure_lambda": float(args.closure_lambda),
        },
        "notes": [
            "第一层为核心同频三节点全连接图，频率取 omega_core。",
            "第二层为低于/等于/高于内存覆写频率的三节点全连接图。",
            "跨层采用 s<->l, w<->e, a<->h 一一对应耦合。",
        ],
    }
    (run_dir / f"summary_{timestamp}.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    plot_amplitudes(run_dir / f"amplitudes_{timestamp}.png", times, amplitudes)
    plot_phases(run_dir / f"phases_{timestamp}.png", times, phases)
    plot_closure(
        run_dir / f"closure_{timestamp}.png",
        times,
        core_closure_series,
        mem_closure_series,
        args.core_threshold,
        args.mem_threshold,
    )
    plot_locking(run_dir / f"locking_{timestamp}.png", times, cross_locking_series)

    return result, run_dir


def plot_amplitudes(output_path: Path, times: np.ndarray, amplitudes: np.ndarray) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for idx, name in enumerate(CORE_NAMES):
        axes[0].plot(times, amplitudes[:, idx], linewidth=1.5, label=name)
    axes[0].set_title("Core Layer Amplitudes")
    axes[0].set_ylabel("|xi|")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend()

    for idx, name in enumerate(MEM_NAMES, start=3):
        axes[1].plot(times, amplitudes[:, idx], linewidth=1.5, label=NODE_NAMES[idx])
    axes[1].set_title("Memory Threshold Layer Amplitudes")
    axes[1].set_xlabel("time")
    axes[1].set_ylabel("|xi|")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_phases(output_path: Path, times: np.ndarray, phases: np.ndarray) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for idx, name in enumerate(CORE_NAMES):
        axes[0].plot(times, phases[:, idx], linewidth=1.4, label=name)
    axes[0].set_title("Core Layer Phases")
    axes[0].set_ylabel("phase")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend()

    for idx, name in enumerate(MEM_NAMES, start=3):
        axes[1].plot(times, phases[:, idx], linewidth=1.4, label=NODE_NAMES[idx])
    axes[1].set_title("Memory Threshold Layer Phases")
    axes[1].set_xlabel("time")
    axes[1].set_ylabel("phase")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_closure(
    output_path: Path,
    times: np.ndarray,
    core_closure: np.ndarray,
    mem_closure: np.ndarray,
    core_threshold: float,
    mem_threshold: float,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(times, core_closure, linewidth=1.6, color="tab:red", label="core closure")
    ax.plot(times, mem_closure, linewidth=1.5, color="tab:blue", label="memory closure")
    ax.axhline(core_threshold, color="tab:red", linestyle="--", linewidth=1.0, alpha=0.8, label="core threshold")
    ax.axhline(mem_threshold, color="tab:blue", linestyle="--", linewidth=1.0, alpha=0.8, label="memory threshold")
    ax.set_title("Layer Closure Strength")
    ax.set_xlabel("time")
    ax.set_ylabel("T_psi")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_locking(output_path: Path, times: np.ndarray, cross_locking: np.ndarray) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(times, cross_locking, linewidth=1.6, color="tab:green")
    ax.set_title("Cross-layer Locking")
    ax.set_xlabel("time")
    ax.set_ylabel("locking strength")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    result, run_dir = simulate(args)
    print(json.dumps({"run_dir": str(run_dir), "summary": result["summary"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
