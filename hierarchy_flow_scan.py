#!/usr/bin/env python3
"""
层级时间流速参数扫描与报告生成

目标
- 扫描多轴闭合锁相模型中的关键参数区域；
- 评估哪些区域会让 chi_l 更平滑，哪些区域会让 chi_l 更分裂；
- 输出 JSON/Markdown 报告与热力图。

默认扫描维度
- frequency_detuning_scale: 调整辅助主轴相对主轴1的频率失谐程度
- shell_drift_scale: 调整类氢壳层漂移强度
- resonance_gain: 调整主轴共振对有效壳层半径的畸变增益

输出
- report_*.json: 完整数值报告
- report_*.md: 可阅读总结
- metrics_volume_*.npz: 三维扫描体数据
- smoothness_heatmap_*.png: chi_l 平滑区域投影热力图
- splitness_heatmap_*.png: chi_l 分裂区域投影热力图
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

from vortex_tensor_animation import (
    AxisPerturbation,
    ClosureResonanceSpec,
    HydrogenLikeSpec,
    VortexSpec,
    build_hydrogen_like_envelope,
    create_output_dir,
    meshgrid_centered,
    radial_distance,
    closure_resonance_score,
)


@dataclass
class ScanSummary:
    detuning_scale: float
    shell_drift_scale: float
    resonance_gain: float
    smooth_score: float
    split_score: float
    chi_span_mean: float
    chi_temporal_std: float
    delta_chi_mean_abs: float
    closure_error_mean: float
    closure_error_normalized_mean: float
    stable_island_fraction: float
    shell_distortion_mean: float


def linspace_values(start: float, stop: float, steps: int) -> np.ndarray:
    return np.linspace(start, stop, steps, dtype=np.float64)


def build_base_perturbations() -> List[AxisPerturbation]:
    return [
        AxisPerturbation(axis=(1.0, 0.0), epsilon=0.9, kappa=0.14, omega=0.30, phi0=0.0),
        AxisPerturbation(axis=(0.2, 1.0), epsilon=0.7, kappa=0.19, omega=0.43, phi0=0.8),
        AxisPerturbation(axis=(-0.8, 0.5), epsilon=0.5, kappa=0.23, omega=0.36, phi0=1.2),
    ]


def scale_detuning(
    perturbations: List[AxisPerturbation],
    detuning_scale: float,
) -> List[AxisPerturbation]:
    if not perturbations:
        return []
    base = perturbations[0]
    scaled = [base]
    for perturb in perturbations[1:]:
        scaled_omega = base.omega + detuning_scale * (perturb.omega - base.omega)
        scaled.append(
            AxisPerturbation(
                axis=perturb.axis,
                epsilon=perturb.epsilon,
                kappa=perturb.kappa,
                omega=float(scaled_omega),
                phi0=perturb.phi0,
            )
        )
    return scaled


def distort_shell_radii(
    shell_radii: List[float],
    perturbations: List[AxisPerturbation],
    resonance_gain: float,
    t: float,
) -> Tuple[List[float], float]:
    if not shell_radii:
        return [], 0.0
    if resonance_gain <= 1e-12 or not perturbations:
        return [float(radius) for radius in shell_radii], 0.0

    omega_values = np.array([abs(p.omega) for p in perturbations], dtype=np.float64)
    kappa_values = np.array([abs(p.kappa) for p in perturbations], dtype=np.float64)
    detuning_contrast = float(np.std(omega_values) / (np.mean(omega_values) + 1e-12))
    kappa_contrast = float(np.std(kappa_values) / (np.mean(kappa_values) + 1e-12))

    distorted: List[float] = []
    rel_distortions: List[float] = []
    shell_count = max(len(shell_radii), 1)
    for shell_index, radius in enumerate(shell_radii, start=1):
        phase_terms = np.array(
            [np.cos(p.kappa * radius - p.omega * t + p.phi0) for p in perturbations],
            dtype=np.float64,
        )
        mean_resonance = float(np.mean(phase_terms))
        if len(phase_terms) > 1:
            pairwise_terms = [
                float(phase_terms[i] * phase_terms[j])
                for i in range(len(phase_terms))
                for j in range(i + 1, len(phase_terms))
            ]
            pairwise_resonance = float(np.mean(pairwise_terms))
        else:
            pairwise_resonance = mean_resonance

        shell_weight = shell_index / shell_count
        resonance_mix = 0.58 * mean_resonance + 0.42 * pairwise_resonance
        distortion_strength = resonance_gain * (
            0.10
            + 0.16 * shell_weight * detuning_contrast
            + 0.08 * kappa_contrast
        )
        distortion_factor = float(np.clip(1.0 + distortion_strength * resonance_mix, 0.45, 1.85))
        distorted_radius = max(0.2, float(radius * distortion_factor))
        distorted.append(distorted_radius)
        rel_distortions.append(abs(distorted_radius - float(radius)) / (abs(float(radius)) + 1e-12))

    shell_distortion_mean = float(np.mean(rel_distortions)) if rel_distortions else 0.0
    return distorted, shell_distortion_mean


def evaluate_parameter_point(
    detuning_scale: float,
    shell_drift_scale: float,
    resonance_gain: float,
    T: int,
    r: np.ndarray,
    hydrogen_like_base: HydrogenLikeSpec,
    closure_spec: ClosureResonanceSpec,
    perturbations_base: List[AxisPerturbation],
) -> Dict[str, float]:
    perturbations = scale_detuning(perturbations_base, detuning_scale=detuning_scale)
    hydrogen_like = HydrogenLikeSpec(
        enabled=True,
        potential_strength=hydrogen_like_base.potential_strength,
        potential_softening=hydrogen_like_base.potential_softening,
        bohr_radius=hydrogen_like_base.bohr_radius,
        shell_count=hydrogen_like_base.shell_count,
        shell_width=hydrogen_like_base.shell_width,
        shell_weight=hydrogen_like_base.shell_weight,
        core_weight=hydrogen_like_base.core_weight,
        shell_breathing=hydrogen_like_base.shell_breathing * shell_drift_scale,
        shell_drift=hydrogen_like_base.shell_drift * shell_drift_scale,
    )

    omega_star_history: List[List[float]] = []
    chi_history: List[List[float]] = []
    delta_chi_history: List[List[float]] = []
    closure_error_history: List[float] = []
    closure_error_normalized_history: List[float] = []
    stable_island_history: List[float] = []
    shell_distortion_history: List[float] = []

    for t_idx in range(T):
        _, _, shell_radii = build_hydrogen_like_envelope(r=r, t=float(t_idx), spec=hydrogen_like)
        shell_radii_eff, shell_distortion_mean = distort_shell_radii(
            shell_radii=shell_radii,
            perturbations=perturbations,
            resonance_gain=resonance_gain,
            t=float(t_idx),
        )
        closure_result = closure_resonance_score(
            perturbations=perturbations,
            shell_radii=shell_radii_eff,
            closure_spec=closure_spec,
        )
        if not closure_result.get("enabled"):
            continue
        shell_scores = closure_result.get("shell_scores", [])
        if not shell_scores:
            continue

        omega_star_history.append([float(item["omega_star"]) for item in shell_scores])
        chi_history.append([float(item["chi_level"]) for item in shell_scores])
        delta_chi_history.append([float(x) for x in closure_result.get("delta_chi", [])])
        closure_error_history.append(float(closure_result["total_closure_error"]))
        closure_error_normalized_history.append(
            float(closure_result.get("total_closure_error_normalized", 0.0))
        )
        stable_island_history.append(1.0 if closure_result["stable_island"] else 0.0)
        shell_distortion_history.append(shell_distortion_mean)

    if not chi_history:
        return {
            "smooth_score": 0.0,
            "split_score": 0.0,
            "chi_span_mean": float("nan"),
            "chi_temporal_std": float("nan"),
            "delta_chi_mean_abs": float("nan"),
            "closure_error_mean": float("nan"),
            "closure_error_normalized_mean": float("nan"),
            "stable_island_fraction": 0.0,
            "shell_distortion_mean": 0.0,
        }

    chi_arr = np.array(chi_history, dtype=np.float64)
    delta_arr = np.array(delta_chi_history, dtype=np.float64) if delta_chi_history and delta_chi_history[0] else np.empty((len(delta_chi_history), 0))
    closure_arr = np.array(closure_error_history, dtype=np.float64)
    closure_norm_arr = np.array(closure_error_normalized_history, dtype=np.float64)
    stable_arr = np.array(stable_island_history, dtype=np.float64)

    chi_span_mean = float(np.mean(np.max(chi_arr, axis=1) - np.min(chi_arr, axis=1)))
    chi_temporal_std = float(np.mean(np.std(chi_arr, axis=0)))
    delta_chi_mean_abs = float(np.mean(np.abs(delta_arr))) if delta_arr.size > 0 else 0.0
    closure_error_mean = float(np.mean(closure_arr))
    closure_error_normalized_mean = float(np.mean(closure_norm_arr))
    stable_island_fraction = float(np.mean(stable_arr))
    shell_distortion_mean = float(np.mean(shell_distortion_history)) if shell_distortion_history else 0.0

    smooth_score = float(
        1.0
        / (
            1.0
            + chi_span_mean
            + delta_chi_mean_abs
            + chi_temporal_std
            + 0.25 * closure_error_normalized_mean
            + 0.35 * shell_distortion_mean
        )
    )
    split_score = float(
        chi_span_mean
        + 0.75 * delta_chi_mean_abs
        + 0.50 * chi_temporal_std
        + 0.25 * closure_error_normalized_mean
        + 0.40 * shell_distortion_mean
    )

    return {
        "smooth_score": smooth_score,
        "split_score": split_score,
        "chi_span_mean": chi_span_mean,
        "chi_temporal_std": chi_temporal_std,
        "delta_chi_mean_abs": delta_chi_mean_abs,
        "closure_error_mean": closure_error_mean,
        "closure_error_normalized_mean": closure_error_normalized_mean,
        "stable_island_fraction": stable_island_fraction,
        "shell_distortion_mean": shell_distortion_mean,
    }


def make_heatmap(
    values: np.ndarray,
    x_values: np.ndarray,
    y_values: np.ndarray,
    title: str,
    cbar_label: str,
    output_path: Path,
    highlight: Tuple[float, float] | None = None,
    gain_label: float | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
    im = ax.imshow(
        values,
        origin="lower",
        aspect="auto",
        extent=[x_values[0], x_values[-1], y_values[0], y_values[-1]],
        cmap="viridis",
    )
    if gain_label is None:
        ax.set_title(title)
    else:
        ax.set_title(f"{title} (gain={gain_label:.3f})")
    ax.set_xlabel("frequency detuning scale")
    ax.set_ylabel("shell drift scale")
    if highlight is not None:
        ax.scatter([highlight[0]], [highlight[1]], s=80, c="red", marker="x", linewidths=2)
    fig.colorbar(im, ax=ax, label=cbar_label)
    fig.savefig(output_path, dpi=140)
    plt.close(fig)


def write_markdown_report(
    report_path: Path,
    config: Dict[str, object],
    best_smooth: Dict[str, float],
    best_split: Dict[str, float],
) -> None:
    lines = [
        "# 层级时间流速参数扫描报告",
        "",
        "## 扫描配置",
        f"- `detuning_scale`: {config['detuning_min']} -> {config['detuning_max']} ({config['detuning_steps']} steps)",
        f"- `shell_drift_scale`: {config['drift_scale_min']} -> {config['drift_scale_max']} ({config['drift_scale_steps']} steps)",
        f"- `resonance_gain`: {config['gain_min']} -> {config['gain_max']} ({config['gain_steps']} steps)",
        f"- `time_frames`: {config['time_frames']}",
        "",
        "## 最平滑区域",
        f"- `detuning_scale`: {best_smooth['detuning_scale']:.4f}",
        f"- `shell_drift_scale`: {best_smooth['shell_drift_scale']:.4f}",
        f"- `resonance_gain`: {best_smooth['resonance_gain']:.4f}",
        f"- `smooth_score`: {best_smooth['smooth_score']:.6f}",
        f"- `chi_span_mean`: {best_smooth['chi_span_mean']:.6f}",
        f"- `chi_temporal_std`: {best_smooth['chi_temporal_std']:.6f}",
        f"- `delta_chi_mean_abs`: {best_smooth['delta_chi_mean_abs']:.6f}",
        f"- `closure_error_mean`: {best_smooth['closure_error_mean']:.6f}",
        f"- `closure_error_normalized_mean`: {best_smooth['closure_error_normalized_mean']:.6f}",
        f"- `stable_island_fraction`: {best_smooth['stable_island_fraction']:.6f}",
        f"- `shell_distortion_mean`: {best_smooth['shell_distortion_mean']:.6f}",
        "",
        "## 最分裂区域",
        f"- `detuning_scale`: {best_split['detuning_scale']:.4f}",
        f"- `shell_drift_scale`: {best_split['shell_drift_scale']:.4f}",
        f"- `resonance_gain`: {best_split['resonance_gain']:.4f}",
        f"- `split_score`: {best_split['split_score']:.6f}",
        f"- `chi_span_mean`: {best_split['chi_span_mean']:.6f}",
        f"- `chi_temporal_std`: {best_split['chi_temporal_std']:.6f}",
        f"- `delta_chi_mean_abs`: {best_split['delta_chi_mean_abs']:.6f}",
        f"- `closure_error_mean`: {best_split['closure_error_mean']:.6f}",
        f"- `closure_error_normalized_mean`: {best_split['closure_error_normalized_mean']:.6f}",
        f"- `stable_island_fraction`: {best_split['stable_island_fraction']:.6f}",
        f"- `shell_distortion_mean`: {best_split['shell_distortion_mean']:.6f}",
        "",
        "## 指标解释",
        "- `smooth_score` 越大表示层级时间流速更平滑、更接近均匀闭合。",
        "- `split_score` 越大表示层级时间流速跨层差异更大、分裂更明显。",
        "- `chi_span_mean` 反映同一时刻各层 `chi_l` 的总体跨度。",
        "- `chi_temporal_std` 反映各层时间流速随时间的波动。",
        "- `delta_chi_mean_abs` 反映相邻层级时间流速差的平均绝对值。",
        "- `stable_island_fraction` 反映该参数点在时间扫描中落入稳定岛的比例。",
        "- `closure_error_normalized_mean` 是按主轴对数归一化后的平均闭合误差，也是新的稳定岛判据依据。",
        "- `shell_distortion_mean` 反映 `resonance_gain` 通过共振混频引起的有效壳层半径平均畸变。",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="层级时间流速参数扫描")
    p.add_argument("--detuning-min", type=float, default=0.0, help="频率失谐缩放最小值")
    p.add_argument("--detuning-max", type=float, default=2.0, help="频率失谐缩放最大值")
    p.add_argument("--detuning-steps", type=int, default=9, help="频率失谐缩放扫描步数")
    p.add_argument("--drift-scale-min", type=float, default=0.0, help="壳层漂移缩放最小值")
    p.add_argument("--drift-scale-max", type=float, default=2.6, help="壳层漂移缩放最大值")
    p.add_argument("--drift-scale-steps", type=int, default=9, help="壳层漂移缩放扫描步数")
    p.add_argument("--gain-min", type=float, default=0.0, help="共振增益最小值")
    p.add_argument("--gain-max", type=float, default=1.2, help="共振增益最大值")
    p.add_argument("--gain-steps", type=int, default=7, help="共振增益扫描步数")
    p.add_argument("--time-frames", type=int, default=24, help="每个参数点的时间采样帧数")
    p.add_argument("--grid-size", type=int, default=64, help="构造壳层半径时使用的网格尺寸")
    p.add_argument("--extent", type=float, default=24.0, help="空间范围 [-extent, extent]")
    p.add_argument("--chi0", type=float, default=1.0, help="层级时间流速基准常数")
    p.add_argument("--closure-time-samples", type=int, default=180, help="闭合时间扫描采样数")
    p.add_argument("--closure-threshold", type=float, default=0.32, help="归一化稳定岛判据阈值")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    out_root = create_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / f"hierarchy_flow_scan_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    detuning_values = linspace_values(args.detuning_min, args.detuning_max, args.detuning_steps)
    drift_values = linspace_values(args.drift_scale_min, args.drift_scale_max, args.drift_scale_steps)
    gain_values = linspace_values(args.gain_min, args.gain_max, args.gain_steps)

    perturbations_base = build_base_perturbations()
    hydrogen_like_base = HydrogenLikeSpec(
        enabled=True,
        potential_strength=2.2,
        potential_softening=0.9,
        bohr_radius=5.0,
        shell_count=3,
        shell_width=0.32,
        shell_weight=0.85,
        core_weight=1.15,
        shell_breathing=0.08,
        shell_drift=0.06,
    )
    closure_spec = ClosureResonanceSpec(
        enabled=True,
        time_samples=max(32, args.closure_time_samples),
        closure_threshold=float(args.closure_threshold),
        shell_projection_scale=1.0,
        chi0=float(args.chi0),
    )

    X, Y = meshgrid_centered(args.grid_size, args.extent)
    r = radial_distance(X, Y, VortexSpec(center=(0.0, 0.0), charge=1, rc=6.0, amplitude=1.0).center)

    smooth_volume = np.zeros((len(gain_values), len(drift_values), len(detuning_values)), dtype=np.float64)
    split_volume = np.zeros((len(gain_values), len(drift_values), len(detuning_values)), dtype=np.float64)
    stable_fraction_volume = np.zeros((len(gain_values), len(drift_values), len(detuning_values)), dtype=np.float64)
    shell_distortion_volume = np.zeros((len(gain_values), len(drift_values), len(detuning_values)), dtype=np.float64)

    summaries: List[ScanSummary] = []
    slice_dir = run_dir / "gain_slices"
    slice_dir.mkdir(parents=True, exist_ok=True)
    for g_idx, resonance_gain in enumerate(gain_values):
        for y_idx, drift_scale in enumerate(drift_values):
            for x_idx, detuning_scale in enumerate(detuning_values):
                metrics = evaluate_parameter_point(
                    detuning_scale=float(detuning_scale),
                    shell_drift_scale=float(drift_scale),
                    resonance_gain=float(resonance_gain),
                    T=int(args.time_frames),
                    r=r,
                    hydrogen_like_base=hydrogen_like_base,
                    closure_spec=closure_spec,
                    perturbations_base=perturbations_base,
                )
                smooth_volume[g_idx, y_idx, x_idx] = metrics["smooth_score"]
                split_volume[g_idx, y_idx, x_idx] = metrics["split_score"]
                stable_fraction_volume[g_idx, y_idx, x_idx] = metrics["stable_island_fraction"]
                shell_distortion_volume[g_idx, y_idx, x_idx] = metrics["shell_distortion_mean"]
                summaries.append(
                    ScanSummary(
                        detuning_scale=float(detuning_scale),
                        shell_drift_scale=float(drift_scale),
                        resonance_gain=float(resonance_gain),
                        smooth_score=float(metrics["smooth_score"]),
                        split_score=float(metrics["split_score"]),
                        chi_span_mean=float(metrics["chi_span_mean"]),
                        chi_temporal_std=float(metrics["chi_temporal_std"]),
                        delta_chi_mean_abs=float(metrics["delta_chi_mean_abs"]),
                        closure_error_mean=float(metrics["closure_error_mean"]),
                        closure_error_normalized_mean=float(metrics["closure_error_normalized_mean"]),
                        stable_island_fraction=float(metrics["stable_island_fraction"]),
                        shell_distortion_mean=float(metrics["shell_distortion_mean"]),
                    )
                )

        make_heatmap(
            smooth_volume[g_idx],
            x_values=detuning_values,
            y_values=drift_values,
            title="Hierarchy Flow Smoothness",
            cbar_label="smooth_score",
            output_path=slice_dir / f"smoothness_gain_{g_idx:02d}_{timestamp}.png",
            gain_label=float(resonance_gain),
        )
        make_heatmap(
            split_volume[g_idx],
            x_values=detuning_values,
            y_values=drift_values,
            title="Hierarchy Flow Splitness",
            cbar_label="split_score",
            output_path=slice_dir / f"splitness_gain_{g_idx:02d}_{timestamp}.png",
            gain_label=float(resonance_gain),
        )
        make_heatmap(
            stable_fraction_volume[g_idx],
            x_values=detuning_values,
            y_values=drift_values,
            title="Stable Island Fraction",
            cbar_label="stable_island_fraction",
            output_path=slice_dir / f"stable_fraction_gain_{g_idx:02d}_{timestamp}.png",
            gain_label=float(resonance_gain),
        )

    best_smooth = max(summaries, key=lambda item: item.smooth_score)
    best_split = max(summaries, key=lambda item: item.split_score)

    smooth_map = np.max(smooth_volume, axis=0)
    split_map = np.max(split_volume, axis=0)
    stable_fraction_map = np.max(stable_fraction_volume, axis=0)
    best_gain_for_smooth = gain_values[np.argmax(smooth_volume, axis=0)]
    best_gain_for_split = gain_values[np.argmax(split_volume, axis=0)]

    smooth_heatmap_path = run_dir / f"smoothness_heatmap_{timestamp}.png"
    split_heatmap_path = run_dir / f"splitness_heatmap_{timestamp}.png"
    stable_heatmap_path = run_dir / f"stable_fraction_heatmap_{timestamp}.png"
    best_gain_smooth_path = run_dir / f"smooth_best_gain_heatmap_{timestamp}.png"
    best_gain_split_path = run_dir / f"split_best_gain_heatmap_{timestamp}.png"
    metrics_volume_path = run_dir / f"metrics_volume_{timestamp}.npz"

    make_heatmap(
        smooth_map,
        x_values=detuning_values,
        y_values=drift_values,
        title="Hierarchy Flow Smoothness",
        cbar_label="smooth_score",
        output_path=smooth_heatmap_path,
        highlight=(best_smooth.detuning_scale, best_smooth.shell_drift_scale),
    )
    make_heatmap(
        split_map,
        x_values=detuning_values,
        y_values=drift_values,
        title="Hierarchy Flow Splitness",
        cbar_label="split_score",
        output_path=split_heatmap_path,
        highlight=(best_split.detuning_scale, best_split.shell_drift_scale),
    )
    make_heatmap(
        stable_fraction_map,
        x_values=detuning_values,
        y_values=drift_values,
        title="Stable Island Fraction",
        cbar_label="stable_island_fraction",
        output_path=stable_heatmap_path,
    )
    make_heatmap(
        best_gain_for_smooth,
        x_values=detuning_values,
        y_values=drift_values,
        title="Best Resonance Gain For Smoothness",
        cbar_label="resonance_gain",
        output_path=best_gain_smooth_path,
    )
    make_heatmap(
        best_gain_for_split,
        x_values=detuning_values,
        y_values=drift_values,
        title="Best Resonance Gain For Splitness",
        cbar_label="resonance_gain",
        output_path=best_gain_split_path,
    )

    np.savez(
        metrics_volume_path,
        detuning_values=detuning_values,
        drift_values=drift_values,
        gain_values=gain_values,
        smooth_volume=smooth_volume,
        split_volume=split_volume,
        stable_fraction_volume=stable_fraction_volume,
        shell_distortion_volume=shell_distortion_volume,
        smooth_projection=smooth_map,
        split_projection=split_map,
        stable_projection=stable_fraction_map,
        best_gain_for_smooth=best_gain_for_smooth,
        best_gain_for_split=best_gain_for_split,
    )

    report = {
        "timestamp": timestamp,
        "config": {
            "detuning_min": args.detuning_min,
            "detuning_max": args.detuning_max,
            "detuning_steps": args.detuning_steps,
            "drift_scale_min": args.drift_scale_min,
            "drift_scale_max": args.drift_scale_max,
            "drift_scale_steps": args.drift_scale_steps,
            "gain_min": args.gain_min,
            "gain_max": args.gain_max,
            "gain_steps": args.gain_steps,
            "time_frames": args.time_frames,
            "grid_size": args.grid_size,
            "extent": args.extent,
            "chi0": args.chi0,
            "closure_time_samples": args.closure_time_samples,
            "closure_threshold": args.closure_threshold,
        },
        "best_smooth": asdict(best_smooth),
        "best_split": asdict(best_split),
        "gain_values": gain_values.tolist(),
        "smooth_projection": smooth_map.tolist(),
        "split_projection": split_map.tolist(),
        "stable_fraction_projection": stable_fraction_map.tolist(),
        "smooth_volume": smooth_volume.tolist(),
        "split_volume": split_volume.tolist(),
        "stable_fraction_volume": stable_fraction_volume.tolist(),
        "shell_distortion_volume": shell_distortion_volume.tolist(),
        "best_gain_for_smooth": best_gain_for_smooth.tolist(),
        "best_gain_for_split": best_gain_for_split.tolist(),
        "all_points": [asdict(item) for item in summaries],
        "artifacts": {
            "metrics_volume": str(metrics_volume_path),
            "smoothness_heatmap": str(smooth_heatmap_path),
            "splitness_heatmap": str(split_heatmap_path),
            "stable_fraction_heatmap": str(stable_heatmap_path),
            "smooth_best_gain_heatmap": str(best_gain_smooth_path),
            "split_best_gain_heatmap": str(best_gain_split_path),
            "gain_slice_dir": str(slice_dir),
        },
    }

    report_json_path = run_dir / f"report_{timestamp}.json"
    report_md_path = run_dir / f"report_{timestamp}.md"
    report_json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown_report(
        report_path=report_md_path,
        config=report["config"],
        best_smooth=report["best_smooth"],
        best_split=report["best_split"],
    )

    print("=" * 72)
    print("层级时间流速参数扫描")
    print("=" * 72)
    print(f"输出目录:     {run_dir}")
    print(
        "最平滑区域:   "
        f"detuning={best_smooth.detuning_scale:.4f}, "
        f"drift_scale={best_smooth.shell_drift_scale:.4f}, "
        f"gain={best_smooth.resonance_gain:.4f}, "
        f"smooth_score={best_smooth.smooth_score:.6f}"
    )
    print(
        "最分裂区域:   "
        f"detuning={best_split.detuning_scale:.4f}, "
        f"drift_scale={best_split.shell_drift_scale:.4f}, "
        f"gain={best_split.resonance_gain:.4f}, "
        f"split_score={best_split.split_score:.6f}"
    )
    print(f"JSON报告:     {report_json_path}")
    print(f"Markdown报告: {report_md_path}")
    print(f"体数据:       {metrics_volume_path}")
    print(f"平滑热力图:   {smooth_heatmap_path}")
    print(f"分裂热力图:   {split_heatmap_path}")
    print(f"稳定岛热力图: {stable_heatmap_path}")


if __name__ == "__main__":
    main()
