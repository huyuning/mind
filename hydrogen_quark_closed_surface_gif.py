#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import animation
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import hydrogen_quark_composition_toy as toy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a 1-minute closed-surface GIF for the hydrogen toy in quantum-style wording")
    parser.add_argument("--duration", type=float, default=12.0, help="simulation duration")
    parser.add_argument("--dt", type=float, default=0.04, help="simulation timestep")
    parser.add_argument("--proton-radius", type=float, default=1.2, help="mean proton-core scale")
    parser.add_argument("--electron-mode", choices=["emergent", "manual"], default="emergent", help="electron shell source")
    parser.add_argument("--electron-radius", type=float, default=5.2, help="legacy manual electron-shell radius")
    parser.add_argument("--electron-frequency", type=float, default=0.11, help="legacy manual electron-shell phase frequency")
    parser.add_argument("--target-bohr-ratio", type=float, default=toy.STANDARD_BOHR_RATIO, help="physical electron-cloud to proton-core ratio target")
    parser.add_argument("--bohr-ratio-scale", type=float, default=1.0, help="scales the physical Bohr-ratio target")
    parser.add_argument("--visual-compression-exp", type=float, default=0.14, help="compress the physical shell ratio for visualization")
    parser.add_argument("--field-coupling", type=float, default=0.82, help="blend between dipole-like and swirl-like proton-core field")
    parser.add_argument("--cloud-breathing-gain", type=float, default=0.07, help="field-driven breathing amplitude of the electron probability shell")
    parser.add_argument("--cloud-anisotropy-gain", type=float, default=0.08, help="field-driven anisotropy of the electron probability shell")
    parser.add_argument("--center-offset-gain", type=float, default=0.018, help="small core-driven offset of the shell center")
    parser.add_argument("--gif-seconds", type=float, default=60.0, help="output GIF playback duration in seconds")
    parser.add_argument("--gif-fps", type=int, default=5, help="output GIF frames per second")
    parser.add_argument("--theta-count", type=int, default=26, help="surface theta sampling")
    parser.add_argument("--phi-count", type=int, default=44, help="surface phi sampling")
    return parser.parse_args()


def create_output_dir() -> Path:
    root = Path("resonance_data")
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = root / f"hydrogen_quark_closed_surface_gif_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def sample_frame_indices(sample_count: int, total_frames: int) -> np.ndarray:
    if sample_count <= 1:
        return np.array([0], dtype=np.int64)
    positions = np.linspace(0, sample_count - 1, total_frames)
    return np.clip(np.round(positions).astype(np.int64), 0, sample_count - 1)


def main() -> None:
    args = parse_args()
    out_dir = create_output_dir()
    sim_args = argparse.Namespace(
        duration=args.duration,
        dt=args.dt,
        proton_radius=args.proton_radius,
        electron_mode=args.electron_mode,
        electron_radius=args.electron_radius,
        electron_frequency=args.electron_frequency,
        target_bohr_ratio=args.target_bohr_ratio,
        bohr_ratio_scale=args.bohr_ratio_scale,
        visual_compression_exp=args.visual_compression_exp,
        field_coupling=args.field_coupling,
        cloud_breathing_gain=args.cloud_breathing_gain,
        cloud_anisotropy_gain=args.cloud_anisotropy_gain,
        center_offset_gain=args.center_offset_gain,
        frames=72,
        gif_fps=args.gif_fps,
    )
    times, quark_series, electron_series, cloud, specs = toy.simulate_with_cloud(sim_args)
    total_frames = max(1, int(round(args.gif_seconds * args.gif_fps)))
    frame_indices = sample_frame_indices(len(times), total_frames)

    fig = plt.figure(figsize=(8.8, 7.6))
    ax = fig.add_subplot(111, projection="3d")
    fig.patch.set_facecolor("#0b1020")
    ax.set_facecolor("#0b1020")

    span = toy.estimate_axis_span(quark_series, cloud)
    legend_handles = [
        Patch(facecolor=toy.COLOR_TO_PLOT["red"], edgecolor="none", alpha=0.78, label="Proton-core quark state surface"),
        Patch(facecolor="#a78bfa", edgecolor="none", alpha=0.45, label="Electron-state probability shell"),
        Line2D([0], [0], color="#a78bfa", linestyle="--", linewidth=2.0, label="Probability-crest track"),
        Line2D([0], [0], marker="x", color="white", linestyle="None", markersize=8, label="Proton center reference"),
    ]

    def draw(frame_i: int) -> list[object]:
        idx = int(frame_indices[frame_i])
        current_t = float(times[idx])
        ax.cla()
        ax.set_xlim(-span, span)
        ax.set_ylim(-span, span)
        ax.set_zlim(-span * 0.65, span * 0.65)
        ax.set_xlabel("x", color="#e5e7eb")
        ax.set_ylabel("y", color="#e5e7eb")
        ax.set_zlabel("z", color="#e5e7eb")
        ax.tick_params(colors="#cbd5e1")
        ax.view_init(elev=22.0, azim=230.0)
        ax.set_title(
            f"Hydrogen Toy Quantum-State Probability Surfaces ({cloud.mode})\nTime = {current_t:.2f} | Playback = {frame_i / max(args.gif_fps, 1):.1f}s",
            color="#e5e7eb",
        )
        legend = ax.legend(handles=legend_handles, loc="upper left", frameon=True, fontsize=9)
        legend.get_frame().set_facecolor("#111827")
        legend.get_frame().set_edgecolor("#334155")
        legend.get_frame().set_alpha(0.82)
        for text in legend.get_texts():
            text.set_color("#e5e7eb")

        artists: list[object] = []
        for qi, spec in enumerate(specs):
            center = quark_series[idx, qi]
            surf_x, surf_y, surf_z = toy.spherical_closed_surface(
                center=center,
                radius=float(spec.base_radius) * 0.55,
                theta_count=args.theta_count,
                phi_count=args.phi_count,
                radial_mod_gain=0.12,
                phase=float(spec.phase + 0.5 * current_t),
            )
            artists.append(
                ax.plot_surface(
                    surf_x,
                    surf_y,
                    surf_z,
                    color=toy.COLOR_TO_PLOT[spec.color],
                    alpha=0.78,
                    linewidth=0.0,
                    antialiased=True,
                    shade=True,
                )
            )
            artists.append(
                ax.scatter([center[0]], [center[1]], [center[2]], s=55, color=toy.COLOR_TO_PLOT[spec.color], edgecolors="black", linewidths=0.4)
            )

        e_center = electron_series[idx]
        e_traj = electron_series[: idx + 1]
        artists.append(ax.plot(e_traj[:, 0], e_traj[:, 1], e_traj[:, 2], color="#a78bfa", alpha=0.26, linewidth=1.0, linestyle="--")[0])
        e_x, e_y, e_z = toy.spherical_closed_surface(
            center=cloud.cloud_center_series[idx],
            radius=float(cloud.display_radius_series[idx]),
            theta_count=args.theta_count,
            phi_count=args.phi_count,
            radial_mod_gain=float(cloud.anisotropy_series[idx]),
            phase=float(cloud.surface_phase_series[idx]),
        )
        artists.append(
            ax.plot_surface(
                e_x,
                e_y,
                e_z,
                color="#a78bfa",
                alpha=0.45,
                linewidth=0.0,
                antialiased=True,
                shade=True,
            )
        )
        artists.append(ax.scatter([e_center[0]], [e_center[1]], [e_center[2]], s=45, color="#a78bfa"))
        artists.append(ax.scatter([0.0], [0.0], [0.0], s=42, color="white", marker="x"))
        return artists

    anim = animation.FuncAnimation(
        fig,
        draw,
        frames=len(frame_indices),
        interval=1000 / max(args.gif_fps, 1),
        blit=False,
    )
    gif_path = out_dir / "hydrogen_quantum_probability_shell_1min.gif"
    anim.save(gif_path, writer=animation.PillowWriter(fps=args.gif_fps))
    plt.close(fig)

    summary = {
        "simulation_duration": float(args.duration),
        "dt": float(args.dt),
        "electron_mode": str(args.electron_mode),
        "target_bohr_ratio": float(args.target_bohr_ratio),
        "bohr_ratio_scale": float(args.bohr_ratio_scale),
        "visual_compression_exp": float(args.visual_compression_exp),
        "gif_seconds": float(args.gif_seconds),
        "gif_fps": int(args.gif_fps),
        "gif_frame_count": int(len(frame_indices)),
        "theta_count": int(args.theta_count),
        "phi_count": int(args.phi_count),
        "output_gif": str(gif_path),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Run directory: {out_dir}")
    print(f"GIF: {gif_path}")
    print(f"Playback seconds: {args.gif_seconds:.1f}")
    print(f"Frame count: {len(frame_indices)}")


if __name__ == "__main__":
    main()
