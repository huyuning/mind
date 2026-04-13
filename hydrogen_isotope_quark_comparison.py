#!/usr/bin/env python3
"""
Compare H / D / T isotopes in the project's effective-model language.

Scope:
- H  = proton core `uud` + electron shell
- D  = proton `uud` + neutron `udd` + electron shell
- T  = proton `uud` + neutron `udd` + neutron `udd` + electron shell

This is a structural toy comparison, not a QCD or nuclear-physics solver.
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

from cellular_plotly_pointcloud import line_trace, point_trace, save_plotly_3d_html

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


@dataclass
class QuarkSpec:
    label: str
    flavor: str
    color: str
    phase: float
    base_radius: float
    nucleon_label: str
    nucleon_center: Tuple[float, float, float]


@dataclass
class IsotopeSummary:
    isotope: str
    nucleon_count: int
    quark_count: int
    duration: float
    dt: float
    sample_count: int
    core_radius_mean: float
    core_radius_std: float
    pair_distance_mean: float
    pair_distance_std: float
    electron_shell_radius_mean: float
    electron_shell_radius_std: float
    quark_labels: List[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hydrogen isotope quark-composition comparison")
    parser.add_argument("--duration", type=float, default=14.0, help="total duration")
    parser.add_argument("--dt", type=float, default=0.04, help="time step")
    parser.add_argument("--nucleon-radius", type=float, default=1.18, help="mean single nucleon scale")
    parser.add_argument("--nucleon-separation", type=float, default=2.6, help="center distance between nucleons")
    parser.add_argument("--electron-radius", type=float, default=5.4, help="mean electron-shell radius")
    parser.add_argument("--electron-frequency", type=float, default=0.10, help="electron-shell orbital frequency")
    parser.add_argument("--frames", type=int, default=72, help="GIF frame count")
    parser.add_argument("--gif-fps", type=int, default=12, help="GIF fps")
    return parser.parse_args()


def create_output_dir() -> Path:
    root = Path("resonance_data")
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = root / f"hydrogen_isotope_quark_comparison_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def nucleon_quark_pattern(nucleon_kind: str) -> List[Tuple[str, str]]:
    if nucleon_kind == "proton":
        return [("up", "red"), ("up", "green"), ("down", "blue")]
    return [("up", "red"), ("down", "green"), ("down", "blue")]


def isotope_nucleons(isotope: str) -> List[str]:
    if isotope == "H":
        return ["proton"]
    if isotope == "D":
        return ["proton", "neutron"]
    if isotope == "T":
        return ["proton", "neutron", "neutron"]
    raise ValueError(f"Unsupported isotope: {isotope}")


def nucleon_centers(isotope: str, separation: float) -> List[np.ndarray]:
    if isotope == "H":
        return [np.array([0.0, 0.0, 0.0], dtype=np.float64)]
    if isotope == "D":
        return [
            np.array([-0.5 * separation, 0.0, 0.0], dtype=np.float64),
            np.array([0.5 * separation, 0.0, 0.0], dtype=np.float64),
        ]
    triangle_h = math.sqrt(3.0) * 0.5 * separation
    return [
        np.array([-0.5 * separation, 0.0, 0.0], dtype=np.float64),
        np.array([0.5 * separation, 0.0, 0.0], dtype=np.float64),
        np.array([0.0, triangle_h, 0.0], dtype=np.float64),
    ]


def build_isotope_specs(isotope: str, nucleon_radius: float, nucleon_separation: float) -> List[QuarkSpec]:
    specs: List[QuarkSpec] = []
    centers = nucleon_centers(isotope, nucleon_separation)
    for ni, (nucleon_kind, center) in enumerate(zip(isotope_nucleons(isotope), centers)):
        phase_shift = ni * 0.55
        local_radius = nucleon_radius * (1.0 + 0.06 * ni)
        for qi, (flavor, color) in enumerate(nucleon_quark_pattern(nucleon_kind)):
            phase = phase_shift + qi * 2.0 * math.pi / 3.0
            radius_factor = 0.92 if flavor == "up" else 1.05
            specs.append(
                QuarkSpec(
                    label=f"{nucleon_kind[0]}{ni+1}_{flavor[0]}_{color}",
                    flavor=flavor,
                    color=color,
                    phase=phase,
                    base_radius=local_radius * radius_factor,
                    nucleon_label=f"{nucleon_kind}_{ni+1}",
                    nucleon_center=(float(center[0]), float(center[1]), float(center[2])),
                )
            )
    return specs


def quark_position(spec: QuarkSpec, t: float) -> np.ndarray:
    base_freq, amplitude = FLAVOR_TO_FREQ_AMP[spec.flavor]
    axis = COLOR_TO_AXIS[spec.color]
    axis = axis / np.linalg.norm(axis)
    wobble = 1.0 + 0.17 * math.sin(2.0 * math.pi * base_freq * t + spec.phase)
    twist = 2.0 * math.pi * (0.54 * base_freq) * t + spec.phase
    local = np.array(
        [
            math.cos(twist),
            math.sin(twist),
            0.55 * math.sin(1.65 * twist + 0.45 * spec.phase),
        ],
        dtype=np.float64,
    )
    center = np.array(spec.nucleon_center, dtype=np.float64)
    axis_pull = amplitude * spec.base_radius * wobble * axis
    orbital = 0.38 * spec.base_radius * local
    return center + axis_pull + orbital


def electron_position(electron_radius: float, electron_frequency: float, isotope: str, t: float) -> np.ndarray:
    isotope_factor = {"H": 1.00, "D": 0.94, "T": 0.90}[isotope]
    phase = 2.0 * math.pi * electron_frequency * t
    breathing = 1.0 + 0.08 * math.sin(0.7 * phase + 0.2 * len(isotope))
    return isotope_factor * electron_radius * breathing * np.array(
        [
            math.cos(phase),
            math.sin(phase),
            0.30 * math.sin(0.45 * phase),
        ],
        dtype=np.float64,
    )


def simulate_isotope(isotope: str, args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray, np.ndarray, List[QuarkSpec]]:
    specs = build_isotope_specs(isotope, args.nucleon_radius, args.nucleon_separation)
    times = np.arange(0.0, args.duration + 0.5 * args.dt, args.dt, dtype=np.float64)
    quark_series = np.zeros((len(times), len(specs), 3), dtype=np.float64)
    electron_series = np.zeros((len(times), 3), dtype=np.float64)
    for ti, t in enumerate(times):
        for qi, spec in enumerate(specs):
            quark_series[ti, qi] = quark_position(spec, float(t))
        electron_series[ti] = electron_position(args.electron_radius, args.electron_frequency, isotope, float(t))
    return times, quark_series, electron_series, specs


def summarize_isotope(isotope: str, times: np.ndarray, quark_series: np.ndarray, electron_series: np.ndarray, specs: List[QuarkSpec]) -> IsotopeSummary:
    core_center = np.mean(quark_series, axis=1, keepdims=True)
    core_radii = np.linalg.norm(quark_series - core_center, axis=-1)
    pair_distances = []
    for i in range(quark_series.shape[1]):
        for j in range(i + 1, quark_series.shape[1]):
            pair_distances.append(np.linalg.norm(quark_series[:, i] - quark_series[:, j], axis=-1))
    pair_stack = np.stack(pair_distances, axis=0)
    electron_radii = np.linalg.norm(electron_series, axis=-1)
    return IsotopeSummary(
        isotope=isotope,
        nucleon_count=len(isotope_nucleons(isotope)),
        quark_count=len(specs),
        duration=float(times[-1] if len(times) else 0.0),
        dt=float(times[1] - times[0]) if len(times) > 1 else 0.0,
        sample_count=int(len(times)),
        core_radius_mean=float(np.mean(core_radii)),
        core_radius_std=float(np.std(core_radii)),
        pair_distance_mean=float(np.mean(pair_stack)),
        pair_distance_std=float(np.std(pair_stack)),
        electron_shell_radius_mean=float(np.mean(electron_radii)),
        electron_shell_radius_std=float(np.std(electron_radii)),
        quark_labels=[spec.label for spec in specs],
    )


def save_summary(out_dir: Path, summaries: List[IsotopeSummary], specs_map: Dict[str, List[QuarkSpec]]) -> None:
    payload = {
        "summaries": [asdict(item) for item in summaries],
        "specs": {key: [asdict(spec) for spec in value] for key, value in specs_map.items()},
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_comparison_panel(
    out_dir: Path,
    isotope_data: Dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, List[QuarkSpec]]],
) -> None:
    fig = plt.figure(figsize=(16.2, 5.4))
    isotopes = ["H", "D", "T"]
    for idx, isotope in enumerate(isotopes, start=1):
        times, quark_series, electron_series, specs = isotope_data[isotope]
        mid = len(times) // 2
        ax = fig.add_subplot(1, 3, idx, projection="3d")
        for qi, spec in enumerate(specs):
            traj = quark_series[:, qi, :]
            ax.plot(traj[:, 0], traj[:, 1], traj[:, 2], color=COLOR_TO_PLOT[spec.color], alpha=0.25, linewidth=1.0)
            ax.scatter([traj[mid, 0]], [traj[mid, 1]], [traj[mid, 2]], s=36, color=COLOR_TO_PLOT[spec.color])
        ax.scatter([electron_series[mid, 0]], [electron_series[mid, 1]], [electron_series[mid, 2]], s=48, color="#a78bfa")
        ax.scatter([0.0], [0.0], [0.0], s=38, color="black", marker="x")
        span = max(np.max(np.abs(electron_series)) * 1.12, 1.0)
        ax.set_xlim(-span, span)
        ax.set_ylim(-span, span)
        ax.set_zlim(-span * 0.65, span * 0.65)
        ax.set_title(f"{isotope}: quark-core snapshot")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_zlabel("z")
    fig.tight_layout()
    fig.savefig(out_dir / "isotope_quark_snapshot_comparison.png", dpi=180)
    plt.close(fig)


def save_plotly_isotope_htmls(
    out_dir: Path,
    isotope_data: Dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, List[QuarkSpec]]],
) -> None:
    for isotope, (times, quark_series, electron_series, specs) in isotope_data.items():
        mid = len(times) // 2
        traces = []
        for qi, spec in enumerate(specs):
            traj = quark_series[:, qi, :]
            traces.append(line_trace(points=traj, name=f"{spec.label} path", color=COLOR_TO_PLOT[spec.color], width=4.0, opacity=0.30))
            traces.append(
                point_trace(
                    points=np.array([traj[mid]], dtype=np.float64),
                    name=spec.label,
                    size=6.0,
                    opacity=0.95,
                    color=COLOR_TO_PLOT[spec.color],
                )
            )
        traces.append(line_trace(points=electron_series, name="electron shell path", color="#a78bfa", width=4.0, opacity=0.25))
        traces.append(
            point_trace(
                points=np.array([electron_series[mid]], dtype=np.float64),
                name="electron shell",
                size=6.5,
                opacity=0.95,
                color="#a78bfa",
            )
        )
        traces.append(
            point_trace(
                points=np.array([[0.0, 0.0, 0.0]], dtype=np.float64),
                name="nuclear center",
                size=5.5,
                opacity=1.0,
                color="#ffffff",
                symbol="x",
            )
        )
        axis_span = float(max(np.max(np.abs(electron_series)) * 1.15, 1.0))
        save_plotly_3d_html(
            output_path=out_dir / f"{isotope.lower()}_quark_snapshot.html",
            title=f"{isotope} Toy Isotope Quark Snapshot",
            traces=traces,
            axis_span=axis_span,
        )


def save_metric_panel(out_dir: Path, summaries: List[IsotopeSummary]) -> None:
    labels = [item.isotope for item in summaries]
    core_radius = [item.core_radius_mean for item in summaries]
    pair_distance = [item.pair_distance_mean for item in summaries]
    electron_radius = [item.electron_shell_radius_mean for item in summaries]

    x = np.arange(len(labels), dtype=np.float64)
    width = 0.24
    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    ax.bar(x - width, core_radius, width=width, label="core radius mean")
    ax.bar(x, pair_distance, width=width, label="pair distance mean")
    ax.bar(x + width, electron_radius, width=width, label="electron shell radius mean")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("scale")
    ax.set_title("H / D / T Toy-Isotope Metric Comparison")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out_dir / "isotope_metric_comparison.png", dpi=180)
    plt.close(fig)


def save_rotating_gif(
    out_dir: Path,
    isotope_data: Dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, List[QuarkSpec]]],
    fps: int,
    frames: int,
) -> None:
    fig = plt.figure(figsize=(15.8, 5.6))
    fig.patch.set_facecolor("#0b1020")
    axes = [fig.add_subplot(1, 3, i + 1, projection="3d") for i in range(3)]
    isotopes = ["H", "D", "T"]
    max_span = 1.0
    for isotope in isotopes:
        _, _, electron_series, _ = isotope_data[isotope]
        max_span = max(max_span, float(np.max(np.abs(electron_series)) * 1.12))
    base_times = isotope_data["H"][0]
    stride = max(1, int(math.ceil(len(base_times) / max(frames, 1))))
    frame_indices = list(range(0, len(base_times), stride))

    def draw(frame_i: int) -> list[object]:
        artists: list[object] = []
        for ax, isotope in zip(axes, isotopes):
            ax.cla()
            times, quark_series, electron_series, specs = isotope_data[isotope]
            idx = min(frame_indices[frame_i], len(times) - 1)
            current_t = float(times[idx])
            ax.set_xlim(-max_span, max_span)
            ax.set_ylim(-max_span, max_span)
            ax.set_zlim(-max_span * 0.65, max_span * 0.65)
            ax.set_xlabel("x", color="#e5e7eb")
            ax.set_ylabel("y", color="#e5e7eb")
            ax.set_zlabel("z", color="#e5e7eb")
            ax.tick_params(colors="#cbd5e1")
            ax.view_init(elev=24.0, azim=360.0 * frame_i / max(len(frame_indices), 1))
            ax.set_title(f"{isotope} @ t={current_t:.2f}", color="#e5e7eb")
            for qi, spec in enumerate(specs):
                traj = quark_series[: idx + 1, qi, :]
                artists.append(ax.plot(traj[:, 0], traj[:, 1], traj[:, 2], color=COLOR_TO_PLOT[spec.color], alpha=0.28, linewidth=1.0)[0])
                pos = quark_series[idx, qi]
                artists.append(ax.scatter([pos[0]], [pos[1]], [pos[2]], s=42, color=COLOR_TO_PLOT[spec.color]))
            etraj = electron_series[: idx + 1]
            artists.append(ax.plot(etraj[:, 0], etraj[:, 1], etraj[:, 2], color="#a78bfa", alpha=0.25, linewidth=1.0)[0])
            epos = electron_series[idx]
            artists.append(ax.scatter([epos[0]], [epos[1]], [epos[2]], s=45, color="#a78bfa"))
            artists.append(ax.scatter([0.0], [0.0], [0.0], s=28, color="white", marker="x"))
        return artists

    anim = animation.FuncAnimation(fig, draw, frames=len(frame_indices), interval=1000 / max(fps, 1), blit=False)
    anim.save(out_dir / "hydrogen_isotope_quark_comparison.gif", writer=animation.PillowWriter(fps=fps))
    plt.close(fig)


def main() -> None:
    args = parse_args()
    out_dir = create_output_dir()
    isotope_data: Dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, List[QuarkSpec]]] = {}
    summaries: List[IsotopeSummary] = []
    specs_map: Dict[str, List[QuarkSpec]] = {}

    for isotope in ["H", "D", "T"]:
        data = simulate_isotope(isotope, args)
        isotope_data[isotope] = data
        times, quark_series, electron_series, specs = data
        summaries.append(summarize_isotope(isotope, times, quark_series, electron_series, specs))
        specs_map[isotope] = specs

    save_summary(out_dir, summaries, specs_map)
    save_comparison_panel(out_dir, isotope_data)
    save_plotly_isotope_htmls(out_dir, isotope_data)
    save_metric_panel(out_dir, summaries)
    save_rotating_gif(out_dir, isotope_data, fps=args.gif_fps, frames=args.frames)

    print(f"Run directory: {out_dir}")
    for item in summaries:
        print(
            f"{item.isotope}: nucleons={item.nucleon_count}, quarks={item.quark_count}, "
            f"core_radius_mean={item.core_radius_mean:.4f}, electron_radius_mean={item.electron_shell_radius_mean:.4f}"
        )


if __name__ == "__main__":
    main()
