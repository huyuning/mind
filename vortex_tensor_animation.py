#!/usr/bin/env python3
"""
二维共振矩阵叠加成三维漩涡的张量动画

设计意图
- 把每一帧的二维共振矩阵视为时间轴上的切片，随时间堆叠形成一个 3D 标量张量 V[t, y, x]。
- “主轴扰动”以一个、两个或三个轴向行波的相位调制体现到每帧的二维数据上（共振条纹/锁相带）。
- 通过动画展示：左侧为当前二维幅度切片，右侧为至今的时间最大投影（MIP），形象呈现 3D 漩涡管的逐步成形。

模型概要
- 复场 X(x, y, t) = A(x, y, t) * exp(i * phi(x, y, t))
- 静态涡旋核：phi_vortex = q * atan2(y - y0, x - x0),  A_vortex ~ tanh(r/rc)
- 主轴扰动（轴向行波相位调制）：
    phi_axis(x, y, t) = eps * cos(kappa * (a · r) - omega * t + phi0)
  其中 a 为单位轴向向量、r=(x, y)
- 若同时引入多个主轴，则总相位为各主轴调制之和，并通过干涉项把相位共振反馈到幅度：
    phi_total = phi_vortex + sum_m phi_axis_m
    A_total = A_vortex * (1 + gain * resonance_mix)
- 若开启类氢模式，则在振幅场中再叠加：
    1) 中心势场 V(r) = -alpha / (r + eps)
    2) 离散壳层约束：r_n ≈ a0 * n^2
- 合成：X = A_total * exp(i * phi_total)

输出
- 帧图（PNG）与可选 GIF 动画（若系统安装 Pillow）
- 保存 3D 张量体 V[t, y, x]（幅度）到 resonance_data/vortex_volume_*.npy
- 保存元数据 JSON

用法
    python3 vortex_tensor_animation.py \
        --N 128 --T 160 --axis 0 1 --epsilon 0.8 --kappa 0.12 --omega 0.25 \
        --axis2 1 0.3 --epsilon2 0.55 --kappa2 0.16 --omega2 0.37 \
        --axis3 -0.8 0.5 --epsilon3 0.45 --kappa3 0.23 --omega3 0.41 \
        --hydrogen-like --bohr-radius 5.0 --shell-count 3 --potential-strength 2.2 \
        --charge 1 --rc 6.0 --gif
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Tuple, List, Dict
from itertools import combinations

import numpy as np

import matplotlib
matplotlib.use("Agg")  # 无交互后端，便于服务器/CI
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize


@dataclass
class AxisPerturbation:
    axis: Tuple[float, float]     # 主轴方向 (ax, ay)
    epsilon: float                # 相位调制幅度
    kappa: float                  # 轴向波数
    omega: float                  # 轴向角频率
    phi0: float                   # 初相


@dataclass
class VortexSpec:
    center: Tuple[float, float]   # (x0, y0)
    charge: int                   # q = ±1, ±2, ...
    rc: float                     # 核尺度
    amplitude: float              # 基础幅度


@dataclass
class HydrogenLikeSpec:
    enabled: bool
    potential_strength: float
    potential_softening: float
    bohr_radius: float
    shell_count: int
    shell_width: float
    shell_weight: float
    core_weight: float
    shell_breathing: float
    shell_drift: float


@dataclass
class ClosureResonanceSpec:
    enabled: bool
    time_samples: int
    closure_threshold: float
    shell_projection_scale: float
    chi0: float


def unit(vx: float, vy: float) -> Tuple[float, float]:
    n = math.hypot(vx, vy)
    if n < 1e-12:
        return (1.0, 0.0)
    return (vx / n, vy / n)


def meshgrid_centered(N: int, extent: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    构造以 0 为中心、范围 [-extent, extent] 的正方形网格。
    返回 X, Y 坐标矩阵（shape: [N, N]）。
    """
    xs = np.linspace(-extent, extent, N, dtype=np.float64)
    ys = np.linspace(-extent, extent, N, dtype=np.float64)
    X, Y = np.meshgrid(xs, ys)
    return X, Y


def make_static_vortex(
    X: np.ndarray,
    Y: np.ndarray,
    spec: VortexSpec,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    生成静态涡旋核的复场 (幅度 A, 相位 phi, 复值场 Z)。
    A ≈ A0 * tanh(r/rc)，phi = q * atan2(y - y0, x - x0)
    """
    x0, y0 = spec.center
    dx = X - x0
    dy = Y - y0
    r = np.hypot(dx, dy)
    # 幅度从中心 0 过渡到外圈 A0
    A = spec.amplitude * np.tanh(r / (spec.rc + 1e-9))
    # 相位绕转
    phi = spec.charge * np.arctan2(dy, dx)
    Z = A * np.exp(1j * phi)
    return A, phi, Z


def radial_distance(
    X: np.ndarray,
    Y: np.ndarray,
    center: Tuple[float, float],
) -> np.ndarray:
    x0, y0 = center
    return np.hypot(X - x0, Y - y0)


def apply_axis_phase_modulation(
    X: np.ndarray,
    Y: np.ndarray,
    t: float,
    perturb: AxisPerturbation,
) -> np.ndarray:
    """
    计算轴向相位调制：phi_axis(x, y, t) = eps * cos(kappa * (a · r) - omega * t + phi0)
    返回相位调制矩阵（shape: [N, N]）。
    """
    ax, ay = unit(*perturb.axis)
    proj = ax * X + ay * Y
    phi_axis = perturb.epsilon * np.cos(perturb.kappa * proj - perturb.omega * t + perturb.phi0)
    return phi_axis


def combine_axis_perturbations(
    X: np.ndarray,
    Y: np.ndarray,
    t: float,
    perturbations: List[AxisPerturbation],
    resonance_gain: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    合并一个或多个主轴扰动。

    返回：
    - total_phase: 所有主轴相位调制之和
    - amplitude_modulation: 由主轴共振干涉形成的幅度调制因子（均值约为 1）
    """
    if not perturbations:
        return np.zeros_like(X), np.ones_like(X)

    phase_fields = [
        apply_axis_phase_modulation(X, Y, t=t, perturb=perturb)
        for perturb in perturbations
    ]
    total_phase = np.sum(phase_fields, axis=0)

    # 单轴时有节律性起伏；多轴时叠加两两/三重干涉，形成更复杂的异向网络
    cosine_stack = np.array([np.cos(field) for field in phase_fields], dtype=np.float64)
    mean_resonance = np.mean(cosine_stack, axis=0)

    if len(phase_fields) == 1:
        resonance_mix = mean_resonance
    else:
        pairwise_terms = []
        for i, j in combinations(range(len(phase_fields)), 2):
            pairwise_terms.append(cosine_stack[i] * cosine_stack[j])
        pairwise_interference = np.mean(pairwise_terms, axis=0)

        if len(phase_fields) >= 3:
            triple_interference = np.prod(cosine_stack, axis=0)
            resonance_mix = (
                0.45 * mean_resonance
                + 0.35 * pairwise_interference
                + 0.20 * triple_interference
            )
        else:
            resonance_mix = 0.60 * mean_resonance + 0.40 * pairwise_interference

    amplitude_modulation = 1.0 + resonance_gain * resonance_mix
    amplitude_modulation = np.clip(amplitude_modulation, 0.05, None)
    return total_phase, amplitude_modulation


def build_hydrogen_like_envelope(
    r: np.ndarray,
    t: float,
    spec: HydrogenLikeSpec,
) -> Tuple[np.ndarray, np.ndarray, List[float]]:
    """
    构造类氢原子振幅包络。

    返回：
    - envelope: 叠加了中心势场与离散壳层的归一化包络
    - potential: 中心势场 V(r)
    - shell_radii: 当前时刻各壳层中心半径
    """
    potential = -spec.potential_strength / (r + spec.potential_softening)
    abs_potential = np.abs(potential)
    potential_norm = abs_potential / (abs_potential.max() + 1e-12)

    core_profile = spec.core_weight * np.exp(-r / (spec.bohr_radius + 1e-12))
    core_profile *= 0.45 + 0.55 * potential_norm

    shell_profile = np.zeros_like(r, dtype=np.float64)
    shell_radii: List[float] = []
    for n in range(1, spec.shell_count + 1):
        nominal_radius = spec.bohr_radius * (n**2)
        breathing = 1.0 + spec.shell_drift * math.sin(0.14 * t + 0.7 * n)
        shell_radius = nominal_radius * breathing
        shell_width = spec.shell_width * spec.bohr_radius * (1.0 + 0.18 * n)
        shell_amplitude = spec.shell_weight * math.exp(-0.55 * (n - 1))
        shell_time_gain = 1.0 + spec.shell_breathing * math.sin(0.19 * t + 0.9 * n)
        shell_profile += shell_amplitude * shell_time_gain * np.exp(
            -0.5 * ((r - shell_radius) / (shell_width + 1e-12)) ** 2
        )
        shell_radii.append(float(shell_radius))

    envelope = core_profile + shell_profile
    envelope /= envelope.max() + 1e-12
    envelope = np.clip(envelope, 0.0, 1.0)
    return envelope, potential, shell_radii


def closure_resonance_score(
    perturbations: List[AxisPerturbation],
    shell_radii: List[float],
    closure_spec: ClosureResonanceSpec,
) -> Dict[str, object]:
    """
    计算多轴模型的闭合共振评分。

    采用简化的壳层-相对相位误差泛函：
        C_n(T) = sum_{i<j} [1 - cos(DeltaTheta_ij,n(T))]
    其中
        DeltaTheta_ij,n(T)
        = (kappa_i L_i,n - kappa_j L_j,n)
          - (omega_i - omega_j) T
          + (phi_i0 - phi_j0)

    返回每个壳层的最优闭合时间、最小误差、闭合强度以及
    Omega_l*、chi_l、Delta chi_l、Delta D_l 等层级时间流速相关量。
    稳定岛判据使用“按主轴对数量归一化后的平均闭合误差”，避免多主轴时
    由于 pair 数增加而把阈值压得过严。
    """
    if not closure_spec.enabled or len(perturbations) < 2 or not shell_radii:
        return {
            "enabled": closure_spec.enabled,
            "shell_scores": [],
            "total_closure_error": None,
            "stable_island": None,
        }

    max_omega = max(abs(p.omega) for p in perturbations)
    time_horizon = max(2.0 * math.pi / (max_omega + 1e-9) * 6.0, 20.0)
    times = np.linspace(0.0, time_horizon, closure_spec.time_samples, dtype=np.float64)

    pair_count_total = max(len(perturbations) * (len(perturbations) - 1) // 2, 1)
    shell_scores: List[Dict[str, float]] = []
    total_errors: List[float] = []

    for shell_index, radius in enumerate(shell_radii, start=1):
        per_time_errors = []
        for T in times:
            closure_error = 0.0
            for i, j in combinations(range(len(perturbations)), 2):
                pi = perturbations[i]
                pj = perturbations[j]
                # 用壳层半径乘以统一投影系数，近似各轴在该壳层上的有效投影长度
                Li = closure_spec.shell_projection_scale * radius
                Lj = closure_spec.shell_projection_scale * radius
                delta_theta = (
                    (pi.kappa * Li - pj.kappa * Lj)
                    - (pi.omega - pj.omega) * T
                    + (pi.phi0 - pj.phi0)
                )
                closure_error += 1.0 - math.cos(delta_theta)
            per_time_errors.append(closure_error)

        per_time_errors_arr = np.array(per_time_errors, dtype=np.float64)
        min_idx = int(np.argmin(per_time_errors_arr))
        min_error = float(per_time_errors_arr[min_idx])
        best_time = float(times[min_idx])
        min_error_normalized = float(min_error / pair_count_total)
        closure_strength = float(math.exp(-min_error_normalized))

        axis_errors = []
        for i in range(len(perturbations)):
            per_axis_error = 0.0
            pair_count = 0
            for j in range(len(perturbations)):
                if i == j:
                    continue
                pi = perturbations[i]
                pj = perturbations[j]
                Li = closure_spec.shell_projection_scale * radius
                Lj = closure_spec.shell_projection_scale * radius
                delta_theta = (
                    (pi.kappa * Li - pj.kappa * Lj)
                    - (pi.omega - pj.omega) * best_time
                    + (pi.phi0 - pj.phi0)
                )
                per_axis_error += 1.0 - math.cos(delta_theta)
                pair_count += 1
            axis_errors.append(per_axis_error / max(pair_count, 1))

        axis_weights = np.exp(-np.array(axis_errors, dtype=np.float64))
        omega_values = np.array([p.omega for p in perturbations], dtype=np.float64)
        omega_star = float(np.sum(axis_weights * omega_values) / (np.sum(axis_weights) + 1e-12))
        omega_star_abs = abs(omega_star)
        chi_level = float(closure_spec.chi0 / (omega_star_abs + 1e-12))
        d_scale = float(omega_star / (closure_spec.chi0 + 1e-12))
        shell_scores.append(
            {
                "shell_index": float(shell_index),
                "radius": float(radius),
                "best_closure_time": best_time,
                "closure_error": min_error,
                "closure_error_normalized": min_error_normalized,
                "closure_strength": closure_strength,
                "omega_star": omega_star,
                "chi_level": chi_level,
                "D_scale": d_scale,
            }
        )
        total_errors.append(min_error)

    total_closure_error = float(np.mean(total_errors)) if total_errors else None
    total_closure_error_normalized = (
        float(total_closure_error / pair_count_total)
        if total_closure_error is not None
        else None
    )
    stable_island = bool(
        total_closure_error_normalized is not None
        and total_closure_error_normalized < closure_spec.closure_threshold
    )

    delta_chi = []
    delta_d_scale = []
    for i in range(len(shell_scores) - 1):
        delta_chi.append(shell_scores[i + 1]["chi_level"] - shell_scores[i]["chi_level"])
        delta_d_scale.append(shell_scores[i + 1]["D_scale"] - shell_scores[i]["D_scale"])

    return {
        "enabled": True,
        "time_horizon": time_horizon,
        "time_samples": closure_spec.time_samples,
        "shell_scores": shell_scores,
        "delta_chi": delta_chi,
        "delta_D_scale": delta_d_scale,
        "pair_count": pair_count_total,
        "total_closure_error": total_closure_error,
        "total_closure_error_normalized": total_closure_error_normalized,
        "stable_island": stable_island,
    }


def create_output_dir() -> Path:
    out_dir = Path("./resonance_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def try_build_gif(frames: List[Path], gif_path: Path, fps: int = 20) -> bool:
    """
    若系统具备 Pillow，则用 PillowWriter 合成 GIF；否则返回 False。
    """
    try:
        from matplotlib.animation import PillowWriter
    except Exception:
        return False

    try:
        # 重新渲染 gif（更节省内存：逐帧读图）
        fig, ax = plt.subplots()
        ax.axis("off")
        img = None
        writer = PillowWriter(fps=fps)
        with writer.saving(fig, str(gif_path), dpi=100):
            for f in frames:
                arr = plt.imread(str(f))
                if img is None:
                    img = ax.imshow(arr)
                else:
                    img.set_data(arr)
                writer.grab_frame()
        plt.close(fig)
        return True
    except Exception:
        return False


def simulate_tensor_animation(
    N: int,
    T: int,
    extent: float,
    vortex: VortexSpec,
    perturbations: List[AxisPerturbation],
    hydrogen_like: HydrogenLikeSpec,
    closure_spec: ClosureResonanceSpec,
    gif: bool,
    resonance_gain: float,
    seed: int | None = None,
) -> Dict[str, object]:
    """
    生成 T 帧二维复场（幅度图像），随时间堆叠得到 V[t, y, x]，并输出动画帧图/GIF。
    """
    if seed is not None:
        np.random.seed(seed)

    out_dir = create_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"vortex_tensor_{timestamp}"
    run_dir = out_dir / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    # 网格
    X, Y = meshgrid_centered(N, extent)
    r = radial_distance(X, Y, vortex.center)
    # 静态涡旋核
    A0, phi0, Z0 = make_static_vortex(X, Y, vortex)

    # 动画配置
    vmin, vmax = 0.0, max(1.0, float(A0.max()))
    norm = Normalize(vmin=vmin, vmax=vmax)
    frames: List[Path] = []

    # 3D 张量体（幅度）
    V = np.zeros((T, N, N), dtype=np.float32)
    # 累积最大投影（MIP）：展示“管”逐步形成
    MIP = np.zeros((N, N), dtype=np.float32)
    shell_history: List[List[float]] = []
    last_potential_stats: Dict[str, float] | None = None
    closure_result: Dict[str, object] | None = None
    omega_star_history: List[List[float]] = []
    chi_history: List[List[float]] = []
    delta_chi_history: List[List[float]] = []
    delta_d_scale_history: List[List[float]] = []

    # 生成帧
    for t_idx in range(T):
        t = float(t_idx)
        # 多主轴相位调制与共振干涉
        phi_axis, amplitude_modulation = combine_axis_perturbations(
            X,
            Y,
            t=t,
            perturbations=perturbations,
            resonance_gain=resonance_gain,
        )
        # 合成振幅场：默认采用涡旋核；类氢模式下叠加中心势场与离散壳层
        base_envelope = A0
        if hydrogen_like.enabled:
            hydrogen_envelope, potential, shell_radii = build_hydrogen_like_envelope(
                r=r,
                t=t,
                spec=hydrogen_like,
            )
            # 保留少量涡旋核结构，使原始模型的旋涡相位仍参与壳层分裂
            base_envelope = vortex.amplitude * (0.28 * A0 + 0.72 * hydrogen_envelope)
            shell_history.append(shell_radii)
            last_potential_stats = {
                "min": float(np.min(potential)),
                "max": float(np.max(potential)),
            }
            closure_result = closure_resonance_score(
                perturbations=perturbations,
                shell_radii=shell_radii,
                closure_spec=closure_spec,
            )
            if closure_result.get("enabled") and closure_result.get("shell_scores"):
                omega_star_history.append(
                    [float(item["omega_star"]) for item in closure_result["shell_scores"]]
                )
                chi_history.append(
                    [float(item["chi_level"]) for item in closure_result["shell_scores"]]
                )
                delta_chi_history.append(
                    [float(value) for value in closure_result.get("delta_chi", [])]
                )
                delta_d_scale_history.append(
                    [float(value) for value in closure_result.get("delta_D_scale", [])]
                )

        # 合成复场：主轴扰动同时写入相位与幅度
        At = base_envelope * amplitude_modulation
        Zt = At * np.exp(1j * (phi0 + phi_axis))
        At = np.abs(Zt)
        V[t_idx] = At.astype(np.float32)
        # 更新 MIP
        np.maximum(MIP, At, out=MIP)

        # 绘制当前帧
        fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
        ax0, ax1 = axes[0]
        ax2, ax3 = axes[1]

        im0 = ax0.imshow(At, cmap="viridis", origin="lower", norm=norm)
        mode_label = "hydrogen" if hydrogen_like.enabled else "vortex"
        ax0.set_title(f"Amplitude |X(x,y,t)|  t={t_idx}  axes={len(perturbations)}  mode={mode_label}")
        ax0.set_xlabel("x")
        ax0.set_ylabel("y")
        fig.colorbar(im0, ax=ax0, fraction=0.046, pad=0.04)

        im1 = ax1.imshow(MIP, cmap="magma", origin="lower", norm=Normalize(vmin=vmin, vmax=vmax))
        ax1.set_title("MIP over time (max_t |X|)")
        ax1.set_xlabel("x")
        ax1.set_ylabel("y")
        fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)

        if chi_history:
            current_chi = np.array(chi_history[-1], dtype=np.float64)
            levels = np.arange(1, len(current_chi) + 1, dtype=int)
            ax2.plot(levels, current_chi, marker="o", color="tab:blue", label=r"$\chi_\ell$")
            ax2.set_title("Hierarchy Time Flow")
            ax2.set_xlabel("level / shell index")
            ax2.set_ylabel(r"$\chi_\ell$")
            ax2.grid(alpha=0.3)

            current_delta = np.array(delta_chi_history[-1], dtype=np.float64) if delta_chi_history[-1] else np.array([])
            if current_delta.size > 0:
                ax2_twin = ax2.twinx()
                ax2_twin.bar(levels[:-1] + 0.15, current_delta, width=0.25, alpha=0.25, color="tab:red", label=r"$\Delta \chi_\ell$")
                ax2_twin.set_ylabel(r"$\Delta \chi_\ell$")

            chi_arr = np.array(chi_history, dtype=np.float64).T
            xmax = max(1, chi_arr.shape[1] - 1)
            im3 = ax3.imshow(
                chi_arr,
                cmap="cividis",
                aspect="auto",
                origin="lower",
                extent=[0, xmax, 1, chi_arr.shape[0]],
            )
            ax3.set_title(r"Hierarchy Flow Heatmap $\chi_\ell(t)$")
            ax3.set_xlabel("time frame")
            ax3.set_ylabel("level / shell index")
            fig.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04)
        else:
            ax2.text(0.5, 0.5, "Enable hydrogen + closure analysis", ha="center", va="center")
            ax2.set_axis_off()
            ax3.text(0.5, 0.5, "No hierarchy flow history", ha="center", va="center")
            ax3.set_axis_off()

        frame_path = run_dir / f"frame_{t_idx:04d}.png"
        fig.savefig(frame_path, dpi=120)
        plt.close(fig)
        frames.append(frame_path)

    # 保存 3D 张量与元数据
    vol_path = run_dir / f"vortex_volume_{timestamp}.npy"
    np.save(vol_path, V)
    hierarchy_path = None
    if chi_history:
        hierarchy_path = run_dir / f"hierarchy_metrics_{timestamp}.npz"
        np.savez(
            hierarchy_path,
            omega_star_history=np.array(omega_star_history, dtype=np.float64),
            chi_history=np.array(chi_history, dtype=np.float64),
            delta_chi_history=np.array(delta_chi_history, dtype=np.float64) if delta_chi_history else np.empty((0, 0)),
            delta_D_scale_history=np.array(delta_d_scale_history, dtype=np.float64) if delta_d_scale_history else np.empty((0, 0)),
        )

    meta = {
        "run_name": run_name,
        "timestamp": timestamp,
        "grid_size": N,
        "frames": T,
        "extent": extent,
        "vortex": asdict(vortex),
        "perturbations": [asdict(perturb) for perturb in perturbations],
        "hydrogen_like": asdict(hydrogen_like),
        "closure_resonance": closure_result,
        "resonance_gain": resonance_gain,
        "volume_path": str(vol_path),
        "hierarchy_metrics_path": str(hierarchy_path) if hierarchy_path is not None else None,
        "frame_examples": [str(frames[i]) for i in (0, T // 4, T // 2, (3 * T) // 4, T - 1) if 0 <= i < T],
    }
    if shell_history:
        meta["shell_radius_history"] = shell_history
    if chi_history:
        meta["omega_star_history"] = omega_star_history
        meta["chi_history"] = chi_history
        meta["delta_chi_history"] = delta_chi_history
        meta["delta_D_scale_history"] = delta_d_scale_history
    if last_potential_stats is not None:
        meta["potential_stats"] = last_potential_stats
    meta_path = run_dir / f"meta_{timestamp}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    gif_path = None
    if gif:
        gif_path = run_dir / f"{run_name}.gif"
        ok = try_build_gif(frames, gif_path)
        if not ok:
            gif_path = None

    return {
        "run_dir": str(run_dir),
        "volume_path": str(vol_path),
        "meta_path": str(meta_path),
        "gif_path": str(gif_path) if gif_path is not None else None,
        "frame_count": len(frames),
        "closure_resonance": closure_result,
        "hierarchy_metrics_path": str(hierarchy_path) if hierarchy_path is not None else None,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="2D 矩阵叠加形成 3D 漩涡的张量动画")
    p.add_argument("--N", type=int, default=128, help="二维网格尺寸 N×N")
    p.add_argument("--T", type=int, default=160, help="时间帧数（堆叠层数）")
    p.add_argument("--extent", type=float, default=24.0, help="坐标范围 [-extent, extent]")
    p.add_argument("--axis", type=float, nargs=2, default=(1.0, 0.0), help="主轴方向 (ax ay)")
    p.add_argument("--epsilon", type=float, default=0.9, help="主轴相位调制幅度")
    p.add_argument("--kappa", type=float, default=0.12, help="轴向波数")
    p.add_argument("--omega", type=float, default=0.25, help="轴向角频率")
    p.add_argument("--phi0", type=float, default=0.0, help="轴向相位初相")
    p.add_argument("--axis2", type=float, nargs=2, default=None, help="第二主轴方向 (ax ay)")
    p.add_argument("--epsilon2", type=float, default=0.6, help="第二主轴相位调制幅度")
    p.add_argument("--kappa2", type=float, default=0.18, help="第二主轴波数")
    p.add_argument("--omega2", type=float, default=0.35, help="第二主轴角频率")
    p.add_argument("--phi02", type=float, default=0.6, help="第二主轴初相")
    p.add_argument("--axis3", type=float, nargs=2, default=None, help="第三主轴方向 (ax ay)")
    p.add_argument("--epsilon3", type=float, default=0.45, help="第三主轴相位调制幅度")
    p.add_argument("--kappa3", type=float, default=0.22, help="第三主轴波数")
    p.add_argument("--omega3", type=float, default=0.40, help="第三主轴角频率")
    p.add_argument("--phi03", type=float, default=1.1, help="第三主轴初相")
    p.add_argument("--resonance-gain", type=float, default=0.35, help="主轴共振反馈到幅度场的增益")
    p.add_argument("--hydrogen-like", action="store_true", help="启用类氢原子模式（中心势场 + 离散壳层）")
    p.add_argument("--potential-strength", type=float, default=2.2, help="中心势场强度 alpha")
    p.add_argument("--potential-softening", type=float, default=0.9, help="中心势场软化参数 eps")
    p.add_argument("--bohr-radius", type=float, default=5.0, help="类玻尔半径 a0")
    p.add_argument("--shell-count", type=int, default=3, help="离散壳层数量")
    p.add_argument("--shell-width", type=float, default=0.32, help="壳层高斯宽度（相对 a0）")
    p.add_argument("--shell-weight", type=float, default=0.85, help="壳层包络强度")
    p.add_argument("--core-weight", type=float, default=1.15, help="中心核包络强度")
    p.add_argument("--shell-breathing", type=float, default=0.08, help="壳层时间呼吸幅度")
    p.add_argument("--shell-drift", type=float, default=0.06, help="壳层半径时间漂移幅度")
    p.add_argument("--closure-analysis", action="store_true", help="启用闭合共振评分与稳定岛判据")
    p.add_argument("--closure-time-samples", type=int, default=240, help="闭合共振时间扫描采样数")
    p.add_argument("--closure-threshold", type=float, default=0.18, help="稳定岛闭合误差阈值")
    p.add_argument("--shell-projection-scale", type=float, default=1.0, help="壳层有效投影长度比例")
    p.add_argument("--chi0", type=float, default=1.0, help="层级时间流速基准常数 chi0")
    p.add_argument("--charge", type=int, default=1, help="涡旋绕数 q (±1, ±2, ...)")
    p.add_argument("--rc", type=float, default=6.0, help="涡旋核尺度")
    p.add_argument("--amplitude", type=float, default=1.0, help="外圈幅度上限")
    p.add_argument("--gif", action="store_true", help="若可用 Pillow，则输出 GIF 动画")
    p.add_argument("--seed", type=int, default=None, help="随机种子（可选）")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    perturbations = [
        AxisPerturbation(
            axis=(float(args.axis[0]), float(args.axis[1])),
            epsilon=float(args.epsilon),
            kappa=float(args.kappa),
            omega=float(args.omega),
            phi0=float(args.phi0),
        )
    ]
    if args.axis2 is not None:
        perturbations.append(
            AxisPerturbation(
                axis=(float(args.axis2[0]), float(args.axis2[1])),
                epsilon=float(args.epsilon2),
                kappa=float(args.kappa2),
                omega=float(args.omega2),
                phi0=float(args.phi02),
            )
        )
    if args.axis3 is not None:
        perturbations.append(
            AxisPerturbation(
                axis=(float(args.axis3[0]), float(args.axis3[1])),
                epsilon=float(args.epsilon3),
                kappa=float(args.kappa3),
                omega=float(args.omega3),
                phi0=float(args.phi03),
            )
        )

    vortex = VortexSpec(
        center=(0.0, 0.0),
        charge=int(args.charge),
        rc=float(args.rc),
        amplitude=float(args.amplitude),
    )
    hydrogen_like = HydrogenLikeSpec(
        enabled=bool(args.hydrogen_like),
        potential_strength=float(args.potential_strength),
        potential_softening=float(args.potential_softening),
        bohr_radius=float(args.bohr_radius),
        shell_count=max(1, int(args.shell_count)),
        shell_width=float(args.shell_width),
        shell_weight=float(args.shell_weight),
        core_weight=float(args.core_weight),
        shell_breathing=float(args.shell_breathing),
        shell_drift=float(args.shell_drift),
    )
    closure_spec = ClosureResonanceSpec(
        enabled=bool(args.closure_analysis),
        time_samples=max(32, int(args.closure_time_samples)),
        closure_threshold=float(args.closure_threshold),
        shell_projection_scale=float(args.shell_projection_scale),
        chi0=float(args.chi0),
    )

    result = simulate_tensor_animation(
        N=int(args.N),
        T=int(args.T),
        extent=float(args.extent),
        vortex=vortex,
        perturbations=perturbations,
        hydrogen_like=hydrogen_like,
        closure_spec=closure_spec,
        gif=bool(args.gif),
        resonance_gain=float(args.resonance_gain),
        seed=args.seed,
    )

    print("=" * 72)
    print("二维叠加 → 三维异向漩涡网络 / 类氢原子 张量动画")
    print("=" * 72)
    print(f"主轴数量:  {len(perturbations)}")
    print(f"类氢模式:  {'开启' if hydrogen_like.enabled else '关闭'}")
    print(f"闭合分析:  {'开启' if closure_spec.enabled else '关闭'}")
    print(f"输出目录: {result['run_dir']}")
    print(f"体数据:    {result['volume_path']}")
    if result.get("hierarchy_metrics_path"):
        print(f"层级指标:  {result['hierarchy_metrics_path']}")
    print(f"元数据:    {result['meta_path']}")
    if result["gif_path"]:
        print(f"GIF动画:   {result['gif_path']}")
    else:
        print("GIF动画:   未生成（缺少 Pillow 或写入失败，已保存帧图 PNG）")
    print(f"帧数:      {result['frame_count']}")
    closure_result = result.get("closure_resonance")
    if isinstance(closure_result, dict) and closure_result.get("enabled"):
        print(f"总闭合误差: {closure_result['total_closure_error']:.4f}")
        print(f"稳定岛判据: {'是' if closure_result['stable_island'] else '否'}")


if __name__ == "__main__":
    main()
