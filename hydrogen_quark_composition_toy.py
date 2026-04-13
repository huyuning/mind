#!/usr/bin/env python3
"""
Hydrogen atom quark-composition toy model in the project's effective-model language.

Important scope note:
- This is a structural toy model, not a Standard Model or QCD solver.
- The proton is represented as a three-cell `uud` core.
- "Color" is mapped to axis bias; "flavor" is mapped to frequency/amplitude windows.
- The electron is kept as an outer shell marker only; it is not treated as a quark.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import animation

from cellular_plotly_pointcloud import line_trace, point_trace, save_plotly_3d_html, mesh3d_from_param_grid

COLOR_TO_AXIS: Dict[str, np.ndarray] = {
    "red": np.array([1.0, 0.25, 0.15], dtype=np.float64),
    "green": np.array([0.20, 1.0, 0.20], dtype=np.float64),
    "blue": np.array([0.15, 0.25, 1.0], dtype=np.float64),
}

FLAVOR_TO_FREQ_AMP: Dict[str, Tuple[float, float]] = {
    "up": (0.34, 0.78),
    "down": (0.27, 1.00),
}

COLOR_TO_PLOT: Dict[str, str] = {
    "red": "#ef4444",
    "green": "#22c55e",
    "blue": "#3b82f6",
}

STANDARD_BOHR_RATIO = 5.29e-11 / 0.84e-15


@dataclass
class QuarkSpec:
    label: str
    flavor: str
    color: str
    phase: float
    base_radius: float


@dataclass
class ElectronCloudState:
    mode: str
    core_center_series: np.ndarray
    core_radius_series: np.ndarray
    cloud_center_series: np.ndarray
    crest_series: np.ndarray
    display_radius_series: np.ndarray
    physical_radius_series: np.ndarray
    anisotropy_series: np.ndarray
    excitation_series: np.ndarray
    surface_phase_series: np.ndarray
    target_bohr_ratio: float
    display_ratio: float


@dataclass
class HydrogenToySummary:
    duration: float
    dt: float
    sample_count: int
    electron_mode: str
    proton_core_radius_mean: float
    proton_core_radius_std: float
    proton_core_pair_distance_mean: float
    proton_core_pair_distance_std: float
    electron_probability_shell_radius_mean: float
    electron_probability_shell_radius_std: float
    electron_probability_shell_physical_radius_mean: float
    electron_probability_shell_physical_radius_std: float
    electron_crest_radius_mean: float
    electron_crest_radius_std: float
    electron_cloud_center_offset_mean: float
    electron_cloud_center_offset_std: float
    electron_shell_ratio_to_core_mean: float
    electron_shell_ratio_to_core_std: float
    electron_shell_anisotropy_mean: float
    electron_shell_anisotropy_std: float
    electron_excitation_mean: float
    electron_excitation_std: float
    electron_target_bohr_ratio: float
    electron_display_ratio: float
    color_axis_norm_red: float
    color_axis_norm_green: float
    color_axis_norm_blue: float
    quark_labels: List[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hydrogen quark-composition toy model")
    parser.add_argument("--duration", type=float, default=14.0, help="total duration")
    parser.add_argument("--dt", type=float, default=0.04, help="time step")
    parser.add_argument("--proton-radius", type=float, default=1.2, help="mean proton-core scale")
    parser.add_argument("--electron-mode", choices=["emergent", "manual", "hydrogenic"], default="emergent", help="electron shell source")
    parser.add_argument("--hydrogen-state", choices=["1s", "2p"], default="1s", help="hydrogenic bound state to visualize when electron-mode=hydrogenic")
    parser.add_argument("--electron-radius", type=float, default=5.2, help="legacy manual electron-shell radius")
    parser.add_argument("--electron-frequency", type=float, default=0.11, help="legacy manual electron-shell phase frequency")
    parser.add_argument("--target-bohr-ratio", type=float, default=STANDARD_BOHR_RATIO, help="physical electron-cloud to proton-core ratio target")
    parser.add_argument("--bohr-ratio-scale", type=float, default=1.0, help="scales the physical Bohr-ratio target")
    parser.add_argument("--visual-compression-exp", type=float, default=0.14, help="compress the physical shell ratio for visualization")
    parser.add_argument("--field-coupling", type=float, default=0.82, help="blend between dipole-like and swirl-like proton-core field")
    parser.add_argument("--cloud-breathing-gain", type=float, default=0.07, help="field-driven breathing amplitude of the electron probability shell")
    parser.add_argument("--cloud-anisotropy-gain", type=float, default=0.08, help="field-driven anisotropy of the electron probability shell")
    parser.add_argument("--center-offset-gain", type=float, default=0.018, help="small core-driven offset of the shell center")
    parser.add_argument("--frames", type=int, default=72, help="GIF frame count")
    parser.add_argument("--gif-fps", type=int, default=12, help="GIF fps")
    return parser.parse_args()


def create_output_dir() -> Path:
    root = Path("resonance_data")
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = root / f"hydrogen_quark_composition_toy_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def build_quark_specs(proton_radius: float) -> List[QuarkSpec]:
    return [
        QuarkSpec(label="u_red", flavor="up", color="red", phase=0.00, base_radius=proton_radius * 0.92),
        QuarkSpec(label="u_green", flavor="up", color="green", phase=2.0 * math.pi / 3.0, base_radius=proton_radius * 0.90),
        QuarkSpec(label="d_blue", flavor="down", color="blue", phase=4.0 * math.pi / 3.0, base_radius=proton_radius * 1.06),
    ]


def quark_position(spec: QuarkSpec, t: float) -> np.ndarray:
    base_freq, amplitude = FLAVOR_TO_FREQ_AMP[spec.flavor]
    axis = COLOR_TO_AXIS[spec.color]
    axis = axis / np.linalg.norm(axis)
    wobble = 1.0 + 0.18 * math.sin(2.0 * math.pi * base_freq * t + spec.phase)
    twist = 2.0 * math.pi * (0.55 * base_freq) * t + spec.phase
    local = np.array(
        [
            math.cos(twist),
            math.sin(twist),
            0.55 * math.sin(1.7 * twist + 0.6 * spec.phase),
        ],
        dtype=np.float64,
    )
    axis_pull = amplitude * spec.base_radius * wobble * axis
    orbital = 0.38 * spec.base_radius * local
    return axis_pull + orbital


def pair_distance_mean_series(quark_series: np.ndarray) -> np.ndarray:
    pair_distances = []
    for i in range(quark_series.shape[1]):
        for j in range(i + 1, quark_series.shape[1]):
            pair_distances.append(np.linalg.norm(quark_series[:, i] - quark_series[:, j], axis=-1))
    if not pair_distances:
        return np.zeros(quark_series.shape[0], dtype=np.float64)
    return np.mean(np.stack(pair_distances, axis=0), axis=0)


def zscore_like(values: np.ndarray) -> np.ndarray:
    mean = float(np.mean(values))
    std = float(np.std(values))
    if std < 1e-9:
        return np.zeros_like(values)
    return (values - mean) / std


def normalized_series(vectors: np.ndarray, fallback: np.ndarray) -> np.ndarray:
    out = np.zeros_like(vectors)
    ref = np.asarray(fallback, dtype=np.float64)
    ref_norm = float(np.linalg.norm(ref))
    last = ref / ref_norm if ref_norm > 1e-9 else np.array([1.0, 0.0, 0.0], dtype=np.float64)
    for idx, vec in enumerate(vectors):
        norm = float(np.linalg.norm(vec))
        if norm < 1e-9:
            out[idx] = last
            continue
        last = vec / norm
        out[idx] = last
    return out


def spherical_closed_surface(
    center: np.ndarray,
    radius: float,
    theta_count: int = 26,
    phi_count: int = 44,
    radial_mod_gain: float = 0.10,
    phase: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    theta = np.linspace(1e-3, np.pi - 1e-3, theta_count, dtype=np.float64)
    phi = np.linspace(0.0, 2.0 * np.pi, phi_count, endpoint=False, dtype=np.float64)
    theta_grid, phi_grid = np.meshgrid(theta, phi, indexing="ij")
    mod = (
        0.55 * np.cos(2.0 * phi_grid - phase)
        + 0.45 * np.sin(3.0 * theta_grid + 0.6 * phase)
    )
    local_r = radius * (1.0 + radial_mod_gain * mod)
    x = center[0] + local_r * np.sin(theta_grid) * np.cos(phi_grid)
    y = center[1] + local_r * np.sin(theta_grid) * np.sin(phi_grid)
    z = center[2] + local_r * np.cos(theta_grid)
    return x, y, z


def electron_position(electron_radius: float, electron_frequency: float, t: float) -> np.ndarray:
    phase = 2.0 * math.pi * electron_frequency * t
    breathing = 1.0 + 0.08 * math.sin(0.7 * phase)
    return electron_radius * breathing * np.array(
        [
            math.cos(phase),
            math.sin(phase),
            0.28 * math.sin(0.5 * phase),
        ],
        dtype=np.float64,
    )


def build_manual_electron_cloud(quark_series: np.ndarray, args: argparse.Namespace, times: np.ndarray) -> ElectronCloudState:
    crest_series = np.zeros((len(times), 3), dtype=np.float64)
    for ti, t in enumerate(times):
        crest_series[ti] = electron_position(args.electron_radius, args.electron_frequency, float(t))
    core_center = np.mean(quark_series, axis=1)
    relative = quark_series - core_center[:, None, :]
    core_radius = np.mean(np.linalg.norm(relative, axis=-1), axis=1)
    display_radius = 0.14 * np.maximum(np.linalg.norm(crest_series, axis=-1), 1e-6)
    physical_ratio = float(args.target_bohr_ratio) * float(args.bohr_ratio_scale)
    physical_radius = physical_ratio * np.maximum(core_radius, 1e-6)
    anisotropy = np.full(len(times), 0.06, dtype=np.float64)
    excitation = np.ones(len(times), dtype=np.float64)
    surface_phase = np.unwrap(np.arctan2(crest_series[:, 1], crest_series[:, 0]))
    return ElectronCloudState(
        mode="manual",
        core_center_series=core_center,
        core_radius_series=core_radius,
        cloud_center_series=crest_series.copy(),
        crest_series=crest_series,
        display_radius_series=display_radius,
        physical_radius_series=physical_radius,
        anisotropy_series=anisotropy,
        excitation_series=excitation,
        surface_phase_series=surface_phase,
        target_bohr_ratio=physical_ratio,
        display_ratio=float(np.mean(display_radius / np.maximum(core_radius, 1e-6))),
    )


def build_emergent_electron_cloud(quark_series: np.ndarray, specs: List[QuarkSpec], args: argparse.Namespace) -> ElectronCloudState:
    core_center = np.mean(quark_series, axis=1)
    relative = quark_series - core_center[:, None, :]
    core_radius = np.mean(np.linalg.norm(relative, axis=-1), axis=1)
    pair_mean = pair_distance_mean_series(quark_series)

    weights = np.asarray([FLAVOR_TO_FREQ_AMP[spec.flavor][1] for spec in specs], dtype=np.float64)
    weighted_relative = relative * weights[None, :, None]
    dipole = np.sum(weighted_relative, axis=1) / max(float(np.sum(weights)), 1e-9)

    swirl = np.zeros_like(dipole)
    for idx in range(len(specs)):
        swirl += np.cross(relative[:, idx], relative[:, (idx + 1) % len(specs)])
    swirl /= max(len(specs), 1)

    core_radius_safe = np.maximum(core_radius, 1e-6)
    dipole /= core_radius_safe[:, None]
    swirl /= np.maximum(core_radius_safe**2, 1e-6)[:, None]

    blend = float(np.clip(args.field_coupling, 0.0, 1.0))
    field = blend * dipole + (1.0 - blend) * swirl
    field_axis = normalized_series(field, np.array([1.0, 0.0, 0.0], dtype=np.float64))

    excitation_signal = 0.65 * np.tanh(zscore_like(np.linalg.norm(field, axis=-1))) + 0.35 * np.tanh(zscore_like(pair_mean))
    breathing_gain = float(max(args.cloud_breathing_gain, 0.0))
    excitation = np.clip(1.0 + breathing_gain * excitation_signal, 0.82, 1.22)

    target_ratio = float(max(args.target_bohr_ratio * args.bohr_ratio_scale, 1.0))
    compression_exp = float(np.clip(args.visual_compression_exp, 0.05, 1.0))
    display_ratio = float(target_ratio**compression_exp)

    physical_radius = target_ratio * core_radius_safe * excitation
    display_radius = display_ratio * core_radius_safe * excitation
    anisotropy = np.clip(0.02 + float(max(args.cloud_anisotropy_gain, 0.0)) * np.abs(excitation_signal), 0.02, 0.18)
    center_offset = float(max(args.center_offset_gain, 0.0)) * core_radius_safe[:, None] * excitation_signal[:, None] * field_axis
    cloud_center = core_center + center_offset
    crest_series = cloud_center + display_radius[:, None] * field_axis
    surface_phase = np.unwrap(np.arctan2(field_axis[:, 1], field_axis[:, 0]))

    return ElectronCloudState(
        mode="emergent",
        core_center_series=core_center,
        core_radius_series=core_radius_safe,
        cloud_center_series=cloud_center,
        crest_series=crest_series,
        display_radius_series=display_radius,
        physical_radius_series=physical_radius,
        anisotropy_series=anisotropy,
        excitation_series=excitation,
        surface_phase_series=surface_phase,
        target_bohr_ratio=target_ratio,
        display_ratio=display_ratio,
    )


def build_hydrogenic_electron_cloud(quark_series: np.ndarray, args: argparse.Namespace) -> ElectronCloudState:
    # Anchor to proton-core center-of-mass
    core_center_series = np.mean(quark_series, axis=1)
    # Use mean core radius to define mapping to model units
    relative = quark_series - core_center_series[:, None, :]
    core_radius_series = np.mean(np.linalg.norm(relative, axis=-1), axis=1)
    core_radius_mean = float(np.mean(core_radius_series))
    # Target Bohr ratio (a0 / r_p) mapped to model units
    target_ratio = float(max(args.target_bohr_ratio * args.bohr_ratio_scale, 1.0))
    a0_model = target_ratio * core_radius_mean
    # Choose most-probable radii from hydrogenic states:
    # 1s: r_mp = a0; 2p: r_mp = 4 a0
    if args.hydrogen_state == "2p":
        r_mp = 4.0 * a0_model
        anisotropy_val = 0.12
        # Choose fixed principal axis (z) for 2p display; could be aligned to core later
        axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    else:
        r_mp = 1.0 * a0_model
        anisotropy_val = 0.02
        axis = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    axis = axis / max(np.linalg.norm(axis), 1e-9)
    # Visual compression for display radius
    compression_exp = float(np.clip(args.visual_compression_exp, 0.05, 1.0))
    display_radius = (r_mp / max(core_radius_mean, 1e-6)) ** compression_exp * core_radius_mean
    # Build time series: hydrogenic stationary states → no intrinsic time modulation in density
    display_radius_series = np.full(len(core_radius_series), display_radius, dtype=np.float64)
    physical_radius_series = np.full(len(core_radius_series), r_mp, dtype=np.float64)
    anisotropy_series = np.full(len(core_radius_series), anisotropy_val, dtype=np.float64)
    excitation_series = np.ones(len(core_radius_series), dtype=np.float64)
    # Cloud center follows core center (Born-Oppenheimer-like anchoring)
    cloud_center_series = core_center_series.copy()
    crest_series = cloud_center_series + display_radius_series[:, None] * axis[None, :]
    surface_phase_series = np.zeros(len(core_radius_series), dtype=np.float64)
    return ElectronCloudState(
        mode=f"hydrogenic:{args.hydrogen_state}",
        core_center_series=core_center_series,
        core_radius_series=core_radius_series,
        cloud_center_series=cloud_center_series,
        crest_series=crest_series,
        display_radius_series=display_radius_series,
        physical_radius_series=physical_radius_series,
        anisotropy_series=anisotropy_series,
        excitation_series=excitation_series,
        surface_phase_series=surface_phase_series,
        target_bohr_ratio=target_ratio,
        display_ratio=float(display_radius / max(core_radius_mean, 1e-6)),
    )


def simulate_with_cloud(args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray, np.ndarray, ElectronCloudState, List[QuarkSpec]]:
    specs = build_quark_specs(args.proton_radius)
    times = np.arange(0.0, args.duration + 0.5 * args.dt, args.dt, dtype=np.float64)
    quark_series = np.zeros((len(times), len(specs), 3), dtype=np.float64)
    for ti, t in enumerate(times):
        for qi, spec in enumerate(specs):
            quark_series[ti, qi] = quark_position(spec, float(t))
    mode = getattr(args, "electron_mode", "emergent")
    if mode == "manual":
        cloud = build_manual_electron_cloud(quark_series, args, times)
    elif mode == "hydrogenic":
        cloud = build_hydrogenic_electron_cloud(quark_series, args)
    else:
        cloud = build_emergent_electron_cloud(quark_series, specs, args)
    return times, quark_series, cloud.crest_series, cloud, specs


def simulate(args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray, np.ndarray, List[QuarkSpec]]:
    times, quark_series, electron_series, _, specs = simulate_with_cloud(args)
    return times, quark_series, electron_series, specs


def summarize(
    times: np.ndarray,
    quark_series: np.ndarray,
    electron_series: np.ndarray,
    specs: List[QuarkSpec],
    cloud: ElectronCloudState,
) -> HydrogenToySummary:
    core_radii = np.linalg.norm(quark_series - cloud.core_center_series[:, None, :], axis=-1)
    pair_distances = []
    for i in range(quark_series.shape[1]):
        for j in range(i + 1, quark_series.shape[1]):
            pair_distances.append(np.linalg.norm(quark_series[:, i] - quark_series[:, j], axis=-1))
    pair_stack = np.stack(pair_distances, axis=0)
    center_offset = np.linalg.norm(cloud.cloud_center_series - cloud.core_center_series, axis=-1)
    crest_radii = np.linalg.norm(electron_series - cloud.core_center_series, axis=-1)
    shell_ratio = cloud.physical_radius_series / np.maximum(cloud.core_radius_series, 1e-6)
    return HydrogenToySummary(
        duration=float(times[-1] if len(times) else 0.0),
        dt=float(times[1] - times[0]) if len(times) > 1 else 0.0,
        sample_count=int(len(times)),
        electron_mode=cloud.mode,
        proton_core_radius_mean=float(np.mean(core_radii)),
        proton_core_radius_std=float(np.std(core_radii)),
        proton_core_pair_distance_mean=float(np.mean(pair_stack)),
        proton_core_pair_distance_std=float(np.std(pair_stack)),
        electron_probability_shell_radius_mean=float(np.mean(cloud.display_radius_series)),
        electron_probability_shell_radius_std=float(np.std(cloud.display_radius_series)),
        electron_probability_shell_physical_radius_mean=float(np.mean(cloud.physical_radius_series)),
        electron_probability_shell_physical_radius_std=float(np.std(cloud.physical_radius_series)),
        electron_crest_radius_mean=float(np.mean(crest_radii)),
        electron_crest_radius_std=float(np.std(crest_radii)),
        electron_cloud_center_offset_mean=float(np.mean(center_offset)),
        electron_cloud_center_offset_std=float(np.std(center_offset)),
        electron_shell_ratio_to_core_mean=float(np.mean(shell_ratio)),
        electron_shell_ratio_to_core_std=float(np.std(shell_ratio)),
        electron_shell_anisotropy_mean=float(np.mean(cloud.anisotropy_series)),
        electron_shell_anisotropy_std=float(np.std(cloud.anisotropy_series)),
        electron_excitation_mean=float(np.mean(cloud.excitation_series)),
        electron_excitation_std=float(np.std(cloud.excitation_series)),
        electron_target_bohr_ratio=float(cloud.target_bohr_ratio),
        electron_display_ratio=float(cloud.display_ratio),
        color_axis_norm_red=float(np.linalg.norm(COLOR_TO_AXIS["red"])),
        color_axis_norm_green=float(np.linalg.norm(COLOR_TO_AXIS["green"])),
        color_axis_norm_blue=float(np.linalg.norm(COLOR_TO_AXIS["blue"])),
        quark_labels=[spec.label for spec in specs],
    )


def estimate_axis_span(quark_series: np.ndarray, cloud: ElectronCloudState) -> float:
    quark_extent = float(np.max(np.abs(quark_series))) if quark_series.size else 0.0
    crest_extent = float(np.max(np.abs(cloud.crest_series))) if cloud.crest_series.size else 0.0
    shell_extent = float(np.max(cloud.display_radius_series)) if cloud.display_radius_series.size else 0.0
    return max(1.0, 1.15 * max(quark_extent, crest_extent + shell_extent))


def save_summary(out_dir: Path, summary: HydrogenToySummary, specs: List[QuarkSpec], args: argparse.Namespace) -> None:
    payload = asdict(summary)
    payload["quark_specs"] = [asdict(spec) for spec in specs]
    payload["electron_cloud_config"] = {
        "electron_mode": str(args.electron_mode),
        "hydrogen_state": str(getattr(args, "hydrogen_state", "1s")),
        "target_bohr_ratio": float(args.target_bohr_ratio),
        "bohr_ratio_scale": float(args.bohr_ratio_scale),
        "visual_compression_exp": float(args.visual_compression_exp),
        "field_coupling": float(args.field_coupling),
        "cloud_breathing_gain": float(args.cloud_breathing_gain),
        "cloud_anisotropy_gain": float(args.cloud_anisotropy_gain),
        "center_offset_gain": float(args.center_offset_gain),
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_snapshot(
    out_dir: Path,
    times: np.ndarray,
    quark_series: np.ndarray,
    electron_series: np.ndarray,
    specs: List[QuarkSpec],
    cloud: ElectronCloudState,
) -> None:
    mid = len(times) // 2
    fig = plt.figure(figsize=(8.8, 7.2))
    ax = fig.add_subplot(111, projection="3d")
    for qi, spec in enumerate(specs):
        traj = quark_series[:, qi, :]
        ax.plot(traj[:, 0], traj[:, 1], traj[:, 2], color=COLOR_TO_PLOT[spec.color], alpha=0.35, linewidth=1.4)
        ax.scatter([traj[mid, 0]], [traj[mid, 1]], [traj[mid, 2]], s=80, color=COLOR_TO_PLOT[spec.color], label=f"{spec.label}")
    ax.plot(electron_series[:, 0], electron_series[:, 1], electron_series[:, 2], color="#a78bfa", alpha=0.24, linewidth=1.0, linestyle="--")
    shell_x, shell_y, shell_z = spherical_closed_surface(
        center=cloud.cloud_center_series[mid],
        radius=float(cloud.display_radius_series[mid]),
        radial_mod_gain=float(cloud.anisotropy_series[mid]),
        phase=float(cloud.surface_phase_series[mid]),
    )
    ax.plot_surface(shell_x, shell_y, shell_z, color="#a78bfa", alpha=0.32, linewidth=0.0, antialiased=True, shade=True)
    ax.scatter([electron_series[mid, 0]], [electron_series[mid, 1]], [electron_series[mid, 2]], s=85, color="#a78bfa", label="electron probability crest")
    ax.scatter([0.0], [0.0], [0.0], s=60, color="black", marker="x", label="proton center")
    title = "Hydrogen Toy: Proton uud Core + Emergent Electron Probability Shell"
    if cloud.mode == "manual":
        title = "Hydrogen Toy: Proton uud Core + Manual Electron Shell"
    ax.set_title(title)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.legend(loc="upper left")
    span = estimate_axis_span(quark_series, cloud)
    ax.set_xlim(-span, span)
    ax.set_ylim(-span, span)
    ax.set_zlim(-span * 0.65, span * 0.65)
    fig.tight_layout()
    fig.savefig(out_dir / "hydrogen_quark_snapshot.png", dpi=180)
    plt.close(fig)


def save_plotly_snapshot(
    out_dir: Path,
    times: np.ndarray,
    quark_series: np.ndarray,
    electron_series: np.ndarray,
    specs: List[QuarkSpec],
    cloud: ElectronCloudState,
) -> None:
    mid = len(times) // 2
    traces = []
    for qi, spec in enumerate(specs):
        traj = quark_series[:, qi, :]
        traces.append(line_trace(points=traj, name=f"{spec.label} path", color=COLOR_TO_PLOT[spec.color], width=5.0, opacity=0.35))
        surf_x, surf_y, surf_z = spherical_closed_surface(
            center=traj[mid],
            radius=float(spec.base_radius) * 0.55,
            phase=float(spec.phase),
            radial_mod_gain=0.12,
        )
        traces.append(
            mesh3d_from_param_grid(
                X=surf_x,
                Y=surf_y,
                Z=surf_z,
                name=f"{spec.label} surface",
                color=COLOR_TO_PLOT[spec.color],
                opacity=0.62,
            )
        )
        traces.append(
            point_trace(
                points=np.array([traj[mid]], dtype=np.float64),
                name=spec.label,
                size=7.0,
                opacity=0.95,
                color=COLOR_TO_PLOT[spec.color],
            )
        )
    traces.append(line_trace(points=electron_series, name="electron probability crest", color="#a78bfa", width=4.0, opacity=0.28))
    e_x, e_y, e_z = spherical_closed_surface(
        center=cloud.cloud_center_series[mid],
        radius=float(cloud.display_radius_series[mid]),
        phase=float(cloud.surface_phase_series[mid]),
        radial_mod_gain=float(cloud.anisotropy_series[mid]),
    )
    traces.append(
        mesh3d_from_param_grid(
            X=e_x,
            Y=e_y,
            Z=e_z,
            name="electron probability shell",
            color="#a78bfa",
            opacity=0.42,
        )
    )
    traces.append(
        point_trace(
            points=np.array([electron_series[mid]], dtype=np.float64),
            name="electron probability crest",
            size=7.0,
            opacity=0.95,
            color="#a78bfa",
        )
    )
    traces.append(
        point_trace(
            points=np.array([[0.0, 0.0, 0.0]], dtype=np.float64),
            name="proton center",
            size=6.0,
            opacity=1.0,
            color="#ffffff",
            symbol="x",
        )
    )
    axis_span = estimate_axis_span(quark_series, cloud)
    title = "Hydrogen Toy: Proton uud Core + Emergent Electron Probability Shell"
    if cloud.mode == "manual":
        title = "Hydrogen Toy: Proton uud Core + Manual Electron Shell"
    save_plotly_3d_html(
        output_path=out_dir / "hydrogen_quark_snapshot.html",
        title=title,
        traces=traces,
        axis_span=axis_span,
    )


def save_radial_panel(
    out_dir: Path,
    times: np.ndarray,
    quark_series: np.ndarray,
    electron_series: np.ndarray,
    specs: List[QuarkSpec],
    cloud: ElectronCloudState,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(9.4, 7.0), sharex=True)
    for qi, spec in enumerate(specs):
        radius = np.linalg.norm(quark_series[:, qi, :], axis=-1)
        axes[0].plot(times, radius, color=COLOR_TO_PLOT[spec.color], label=spec.label, linewidth=1.6)
    axes[0].set_ylabel("core radius")
    axes[0].set_title("Quark-Core Radial Oscillation")
    axes[0].grid(alpha=0.25)
    axes[0].legend(loc="upper right")
    axes[1].plot(times, cloud.display_radius_series, color="#7c3aed", linewidth=1.8, label="display shell radius")
    axes[1].plot(times, np.linalg.norm(electron_series - cloud.core_center_series, axis=-1), color="#c084fc", linewidth=1.0, linestyle="--", label="probability crest radius")
    axes[1].set_ylabel("electron shell radius")
    axes[1].set_xlabel("time")
    if cloud.mode == "manual":
        axes[1].set_title("Manual Electron Shell Radius")
    else:
        axes[1].set_title("Emergent Electron Probability Shell Radius")
    axes[1].grid(alpha=0.25)
    axes[1].legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_dir / "hydrogen_quark_radial_series.png", dpi=180)
    plt.close(fig)


def save_rotating_gif(
    out_dir: Path,
    times: np.ndarray,
    quark_series: np.ndarray,
    electron_series: np.ndarray,
    specs: List[QuarkSpec],
    cloud: ElectronCloudState,
    fps: int,
    frames: int,
) -> None:
    fig = plt.figure(figsize=(8.2, 7.2))
    ax = fig.add_subplot(111, projection="3d")
    fig.patch.set_facecolor("#0b1020")
    ax.set_facecolor("#0b1020")
    span = estimate_axis_span(quark_series, cloud)
    stride = max(1, int(math.ceil(len(times) / max(frames, 1))))
    frame_indices = list(range(0, len(times), stride))

    def draw(frame_i: int) -> list[object]:
        ax.cla()
        idx = frame_indices[frame_i]
        current_t = float(times[idx])
        ax.set_xlim(-span, span)
        ax.set_ylim(-span, span)
        ax.set_zlim(-span * 0.65, span * 0.65)
        ax.set_xlabel("x", color="#e5e7eb")
        ax.set_ylabel("y", color="#e5e7eb")
        ax.set_zlabel("z", color="#e5e7eb")
        ax.tick_params(colors="#cbd5e1")
        ax.view_init(elev=24.0, azim=360.0 * frame_i / max(len(frame_indices), 1))
        title = "Hydrogen Toy uud Core + Emergent Electron Probability Shell"
        if cloud.mode == "manual":
            title = "Hydrogen Toy uud Core + Manual Electron Shell"
        ax.set_title(f"{title}\nTime = {current_t:.2f}", color="#e5e7eb")
        artists: list[object] = []
        for qi, spec in enumerate(specs):
            traj = quark_series[: idx + 1, qi, :]
            artists.append(ax.plot(traj[:, 0], traj[:, 1], traj[:, 2], color=COLOR_TO_PLOT[spec.color], alpha=0.35, linewidth=1.1)[0])
            pos = quark_series[idx, qi]
            artists.append(ax.scatter([pos[0]], [pos[1]], [pos[2]], s=75, color=COLOR_TO_PLOT[spec.color]))
        etraj = electron_series[: idx + 1]
        artists.append(ax.plot(etraj[:, 0], etraj[:, 1], etraj[:, 2], color="#a78bfa", alpha=0.28, linewidth=1.0, linestyle="--")[0])
        shell_x, shell_y, shell_z = spherical_closed_surface(
            center=cloud.cloud_center_series[idx],
            radius=float(cloud.display_radius_series[idx]),
            radial_mod_gain=float(cloud.anisotropy_series[idx]),
            phase=float(cloud.surface_phase_series[idx]),
        )
        artists.append(ax.plot_surface(shell_x, shell_y, shell_z, color="#a78bfa", alpha=0.28, linewidth=0.0, antialiased=True, shade=True))
        epos = electron_series[idx]
        artists.append(ax.scatter([epos[0]], [epos[1]], [epos[2]], s=70, color="#a78bfa"))
        artists.append(ax.scatter([0.0], [0.0], [0.0], s=50, color="white", marker="x"))
        return artists

    anim = animation.FuncAnimation(fig, draw, frames=len(frame_indices), interval=1000 / max(fps, 1), blit=False)
    anim.save(out_dir / "hydrogen_quark_composition.gif", writer=animation.PillowWriter(fps=fps))
    plt.close(fig)


def main() -> None:
    args = parse_args()
    out_dir = create_output_dir()
    times, quark_series, electron_series, cloud, specs = simulate_with_cloud(args)
    summary = summarize(times, quark_series, electron_series, specs, cloud)
    save_summary(out_dir, summary, specs, args)
    save_snapshot(out_dir, times, quark_series, electron_series, specs, cloud)
    save_plotly_snapshot(out_dir, times, quark_series, electron_series, specs, cloud)
    save_radial_panel(out_dir, times, quark_series, electron_series, specs, cloud)
    save_rotating_gif(out_dir, times, quark_series, electron_series, specs, cloud, fps=args.gif_fps, frames=args.frames)

    print(f"Run directory: {out_dir}")
    print(f"Quark core radius mean/std: {summary.proton_core_radius_mean:.4f} / {summary.proton_core_radius_std:.4f}")
    print(
        "Electron shell radius mean/std: "
        f"{summary.electron_probability_shell_radius_mean:.4f} / {summary.electron_probability_shell_radius_std:.4f}"
    )


if __name__ == "__main__":
    main()
