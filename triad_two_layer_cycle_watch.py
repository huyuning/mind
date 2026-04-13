#!/usr/bin/env python3
"""
两层三节点循环结构观察器（长时间运行）

功能
- 基于两层三节点全连接模型，长时间积分系统状态（RK4）
- 在线判别是否存在周期/近周期（Poincaré 截面 + 闭合自相关 + 状态回返）
- 周期性地打印/写入 JSONL 日志，持续运行直至用户中断

判别指标
- Poincaré 截面：选取相位差 φ_s - φ_w 的上穿 0 为截面，记录过截时刻序列 ΔT_k
  - 计算 period_mean / period_std / CV（变异系数）
  - CV < 0.02 视为强周期窗口；0.02~0.08 近周期；更大为非周期/多频
- 闭合自相关：对 core_closure(t) 进行自相关，寻找首个显著峰作为 T*
  - 峰值高度、峰位稳定性用于旁证周期性
- 状态回返：每隔 Δ采样记录 6 节点复状态向量（实虚 12 维），若与历史某点欧氏距离 < ε 且时间间隔 > Tmin，判定一次回返

输出
- 目录：resonance_data/triad_two_layer_cycle_watch_<timestamp>/
  - watch_log_<timestamp>.jsonl（每个报告周期一行 JSON）
  - state_samples_<timestamp>.npz（可选，保存稀疏抽样）
"""
from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


# ----------- 基础规格（复用扫描脚本的最小子集）-----------
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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="两层三节点循环结构观察器（持续运行）")
    # 动力学参数（与扫描脚本一致）
    p.add_argument("--dt", type=float, default=0.02, help="积分步长")
    p.add_argument("--seed", type=int, default=20260408, help="随机种子")
    p.add_argument("--omega-mem", type=float, default=1.0, help="内存覆写频率 omega_mem")
    p.add_argument("--omega-core-ratio", type=float, default=1.15, help="核心层相对 omega_mem 的比例")
    p.add_argument("--low-ratio", type=float, default=0.92, help="低于内存频率节点比例")
    p.add_argument("--equal-ratio", type=float, default=1.0, help="等于内存频率节点比例")
    p.add_argument("--high-ratio", type=float, default=1.08, help="高于内存频率节点比例")
    p.add_argument("--closure-lambda", type=float, default=0.6, help="闭合强度三阶增益项")
    # 观察/判别参数
    p.add_argument("--report-interval", type=float, default=5.0, help="每隔 N 秒输出一次报告")
    p.add_argument("--sample-interval-steps", type=int, default=10, help="每隔 N 步采样一次状态用于回返判别")
    p.add_argument("--return-epsilon", type=float, default=1e-2, help="状态回返判别阈值（12维欧氏距离）")
    p.add_argument("--return-min-sep", type=float, default=2.0, help="回返判别的最小时间间隔（避免零长度）")
    p.add_argument("--poincare-target", type=float, default=0.0, help="Poincaré 截面目标值（φ_s - φ_w）")
    p.add_argument("--poincare-band", type=float, default=0.05, help="截面带宽（用于上穿判别稳健性）")
    p.add_argument("--max-samples", type=int, default=20000, help="最多保存多少个稀疏采样点")
    return p.parse_args()


def create_output_dir() -> Path:
    out_dir = Path("./resonance_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def build_node_specs(args: argparse.Namespace) -> List[NodeSpec]:
    omega_mem = args.omega_mem
    omega_core = args.omega_core_ratio * omega_mem
    omega_low = args.low_ratio * omega_mem
    omega_equal = args.equal_ratio * omega_mem
    omega_high = args.high_ratio * omega_mem
    return [
        # 核心层
        NodeSpec(alpha=0.12, omega=omega_core, beta=0.08, drive_amp=0.035, drive_freq=0.08, drive_phase=0.0),
        NodeSpec(alpha=0.11, omega=omega_core, beta=0.08, drive_amp=0.030, drive_freq=0.08, drive_phase=2.0 * np.pi / 3.0),
        NodeSpec(alpha=0.10, omega=omega_core, beta=0.08, drive_amp=0.028, drive_freq=0.08, drive_phase=4.0 * np.pi / 3.0),
        # 阈值层
        NodeSpec(alpha=0.08, omega=omega_low, beta=0.07, drive_amp=0.018, drive_freq=0.05, drive_phase=0.2),
        NodeSpec(alpha=0.09, omega=omega_equal, beta=0.07, drive_amp=0.020, drive_freq=0.05, drive_phase=1.8),
        NodeSpec(alpha=0.08, omega=omega_high, beta=0.07, drive_amp=0.022, drive_freq=0.05, drive_phase=3.7),
    ]


def build_edge_specs(args: argparse.Namespace) -> List[EdgeSpec]:
    omega_core = args.omega_core_ratio * args.omega_mem
    omega_mem = args.omega_mem
    edges: List[EdgeSpec] = []
    # 核心三角
    core_pairs = [("s", "w"), ("w", "s"), ("w", "a"), ("a", "w"), ("a", "s"), ("s", "a")]
    core_strengths = {
        ("s", "w"): 0.85, ("w", "s"): 0.78, ("w", "a"): 0.82,
        ("a", "w"): 0.74, ("a", "s"): 0.88, ("s", "a"): 0.76,
    }
    core_phases = {
        ("s", "w"): 0.0, ("w", "s"): 0.0,
        ("w", "a"): 2.0 * np.pi / 3.0, ("a", "w"): 2.0 * np.pi / 3.0,
        ("a", "s"): 4.0 * np.pi / 3.0, ("s", "a"): 4.0 * np.pi / 3.0,
    }
    for src, dst in core_pairs:
        edges.append(EdgeSpec(
            src=src, dst=dst, active=1,
            base_strength=core_strengths[(src, dst)],
            strength_mod_amp=0.04, strength_mod_freq=0.03 * omega_core,
            base_phase=core_phases[(src, dst)], phase_drift=0.0
        ))
    # 阈值层三角
    mem_pairs = [("l", "e"), ("e", "l"), ("e", "h"), ("h", "e"), ("h", "l"), ("l", "h")]
    mem_strengths = {
        ("l", "e"): 0.38, ("e", "l"): 0.34, ("e", "h"): 0.42,
        ("h", "e"): 0.36, ("h", "l"): 0.33, ("l", "h"): 0.31,
    }
    mem_phases = {
        ("l", "e"): 0.1, ("e", "l"): -0.1,
        ("e", "h"): 1.1, ("h", "e"): -1.0,
        ("h", "l"): 2.2, ("l", "h"): -2.0,
    }
    for src, dst in mem_pairs:
        edges.append(EdgeSpec(
            src=src, dst=dst, active=1,
            base_strength=mem_strengths[(src, dst)],
            strength_mod_amp=0.03, strength_mod_freq=0.04 * omega_mem,
            base_phase=mem_phases[(src, dst)], phase_drift=0.015
        ))
    # 跨层映射
    cross_map = [("s", "l"), ("w", "e"), ("a", "h")]
    for src, dst in cross_map:
        edges.append(EdgeSpec(
            src=src, dst=dst, active=1,
            base_strength=0.30, strength_mod_amp=0.02,
            strength_mod_freq=0.025 * omega_mem, base_phase=0.0, phase_drift=0.01
        ))
        edges.append(EdgeSpec(
            src=dst, dst=src, active=1,
            base_strength=0.22, strength_mod_amp=0.02,
            strength_mod_freq=0.020 * omega_mem, base_phase=0.15, phase_drift=0.01
        ))
    return edges


def initial_state() -> np.ndarray:
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
    for e in edges:
        i = NODE_INDEX[e.src]
        j = NODE_INDEX[e.dst]
        z[i, j] = edge_complex_value(e, t)
    return z


def derivative(x: np.ndarray, t: float, node_specs: List[NodeSpec], edges: List[EdgeSpec]) -> np.ndarray:
    z = coupling_matrix(edges, t)
    dx = np.zeros_like(x)
    for i, spec in enumerate(node_specs):
        self_term = (spec.alpha + 1j * spec.omega - spec.beta * (np.abs(x[i]) ** 2)) * x[i]
        drive_term = spec.drive_amp * np.exp(1j * (2.0 * np.pi * spec.drive_freq * t + spec.drive_phase))
        coupling_term = np.sum(z[:, i] * x) - z[i, i] * x[i]
        dx[i] = self_term + drive_term + coupling_term
    return dx


def rk4_step(x: np.ndarray, t: float, dt: float, node_specs: List[NodeSpec], edges: List[EdgeSpec]) -> np.ndarray:
    k1 = derivative(x, t, node_specs, edges)
    k2 = derivative(x + 0.5 * dt * k1, t + 0.5 * dt, node_specs, edges)
    k3 = derivative(x + 0.5 * dt * k2, t + 0.5 * dt, node_specs, edges)
    k4 = derivative(x + dt * k3, t + dt, node_specs, edges)
    return x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def triad_closure(amplitudes3: np.ndarray, closure_lambda: float) -> float:
    x, y, z = amplitudes3
    return float(x * y + y * z + z * x + closure_lambda * x * y * z)


def autocorr_first_peak(y: np.ndarray, max_lag: int) -> Tuple[int, float]:
    """简单自相关首峰估计：返回 (lag_idx, peak_value)。若无显著峰返回 (0, 0)."""
    y = np.asarray(y, dtype=float)
    y = y - np.mean(y)
    if np.allclose(y, 0.0):
        return 0, 0.0
    ac = np.correlate(y, y, mode="full")[len(y) - 1: len(y) - 1 + max_lag]
    if ac[0] == 0:
        return 0, 0.0
    ac = ac / ac[0]
    # 找第一个明显峰（忽略 lag=0）
    peak_val = 0.0
    peak_idx = 0
    for i in range(1, len(ac) - 1):
        if ac[i] > ac[i - 1] and ac[i] > ac[i + 1] and ac[i] > 0.3:
            peak_val = float(ac[i])
            peak_idx = int(i)
            break
    return peak_idx, peak_val


def main() -> None:
    args = parse_args()
    np.random.seed(args.seed)

    node_specs = build_node_specs(args)
    edge_specs = build_edge_specs(args)

    out_root = create_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / f"triad_two_layer_cycle_watch_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / f"watch_log_{timestamp}.jsonl"
    state_path = run_dir / f"state_samples_{timestamp}.npz"

    # 初始化状态
    x = initial_state()
    t = 0.0
    dt = float(args.dt)

    # 观测缓存
    last_report_twall = time.time()
    closure_core_trace: List[float] = []
    poincare_times: List[float] = []
    poincare_last_val = None  # φ_s - φ_w 上穿检测

    sample_states: List[np.ndarray] = []  # 稀疏采样（用于回返）
    sample_times: List[float] = []

    max_samples = int(args.max_samples)
    eps_ret = float(args.return_epsilon)
    ret_min_sep = float(args.return_min_sep)
    sample_interval_steps = int(args.sample_interval_steps)

    # 稳健阈值
    poincare_target = float(args.poincare_target)
    poincare_band = float(args.poincare_band)

    # 主循环（直到用户中断）
    step = 0
    try:
        with log_path.open("w", encoding="utf-8") as fp:
            while True:
                # 记录
                amp = np.abs(x)
                phase = np.angle(x)
                closure_core_trace.append(triad_closure(amp[:3], args.closure_lambda))

                # Poincaré：φ_s - φ_w 上穿 0
                phi_sw = float(np.angle(np.exp(1j * (phase[NODE_INDEX["s"]] - phase[NODE_INDEX["w"]]))))
                if poincare_last_val is not None:
                    # 落在带宽内且发生上穿
                    if (poincare_last_val < poincare_target - poincare_band) and (phi_sw >= poincare_target + poincare_band):
                        poincare_times.append(t)
                poincare_last_val = phi_sw

                # 稀疏采样
                if step % sample_interval_steps == 0:
                    if len(sample_states) < max_samples:
                        sample_states.append(x.copy())
                        sample_times.append(t)
                    else:
                        # 环形队列：丢弃最早
                        sample_states.pop(0)
                        sample_times.pop(0)
                        sample_states.append(x.copy())
                        sample_times.append(t)

                # 积分一步
                x = rk4_step(x, t, dt, node_specs, edge_specs)
                t += dt
                step += 1

                # 周期报告
                now = time.time()
                if now - last_report_twall >= float(args.report_interval):
                    # Poincaré 统计
                    periods = []
                    if len(poincare_times) >= 3:
                        periods = np.diff(np.array(poincare_times, dtype=np.float64))
                    period_mean = float(np.mean(periods)) if len(periods) > 0 else None
                    period_std = float(np.std(periods)) if len(periods) > 0 else None
                    period_cv = float(period_std / period_mean) if period_mean and period_mean > 0 else None

                    # 闭合自相关首峰
                    max_lag = min(2000, len(closure_core_trace) - 2) if len(closure_core_trace) > 5 else 0
                    ac_lag, ac_peak = (0, 0.0)
                    if max_lag > 10:
                        ac_lag, ac_peak = autocorr_first_peak(np.array(closure_core_trace[-max_lag * 2:], dtype=np.float64), max_lag)

                    # 状态回返计数（近似）：将最后一个采样与更早的采样进行 ε 判别
                    n_returns = 0
                    if len(sample_states) >= 3:
                        ref = sample_states[-1]
                        tref = sample_times[-1]
                        ref_vec = np.concatenate([ref.real, ref.imag])
                        for k in range(len(sample_states) - 3):
                            if tref - sample_times[k] < ret_min_sep:
                                continue
                            vec = np.concatenate([sample_states[k].real, sample_states[k].imag])
                            d = float(np.linalg.norm(ref_vec - vec))
                            if d <= eps_ret:
                                n_returns += 1
                                break

                    record = {
                        "t": round(t, 6),
                        "steps": step,
                        "poincare_period_mean": period_mean,
                        "poincare_period_std": period_std,
                        "poincare_period_cv": period_cv,
                        "ac_first_peak_lag_steps": int(ac_lag),
                        "ac_first_peak_height": round(float(ac_peak), 6),
                        "state_returns_detected": int(n_returns),
                        "trace_length": len(closure_core_trace),
                    }
                    fp.write(json.dumps(record, ensure_ascii=False) + "\n")
                    fp.flush()
                    print(json.dumps(record, ensure_ascii=False))
                    last_report_twall = now
    except KeyboardInterrupt:
        pass
    finally:
        # 保存稀疏样本
        try:
            np.savez_compressed(
                state_path,
                sample_times=np.array(sample_times, dtype=np.float64),
                sample_states=np.stack(sample_states, axis=0) if sample_states else np.zeros((0, 6), dtype=np.complex128),
            )
        except Exception as e:
            print("保存样本失败:", e)


if __name__ == "__main__":
    main()

