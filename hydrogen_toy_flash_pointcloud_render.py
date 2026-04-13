#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cellular_plotly_pointcloud import point_trace, save_plotly_3d_html
import cellular_shell_basis_animation as shell_model
import hydrogen_quark_composition_toy as toy
from hydrogen_toy_flash_analysis import (
    Entity,
    build_entities,
    build_positions,
    pair_resonance_for_entities,
    subsample_indices,
)


COLOR_TO_PLOT: Dict[str, str] = {
    "red": "#ef4444",
    "green": "#22c55e",
    "blue": "#3b82f6",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the flash-cell state of the hydrogen toy with spherical point clouds")
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--dt", type=float, default=0.04)
    parser.add_argument("--target-frames", type=int, default=60)
    parser.add_argument("--proton-radius", type=float, default=1.0)
    parser.add_argument("--electron-radius", type=float, default=5.0)
    parser.add_argument("--electron-frequency", type=float, default=0.11)
    parser.add_argument("--include-electron", action="store_true")
    parser.add_argument("--distance-threshold", type=float, default=1.30)
    parser.add_argument("--phase-threshold", type=float, default=1.01)
    parser.add_argument("--wave-cell-multiplier", type=int, default=2)
    parser.add_argument("--child-shell-count", type=int, default=2)
    parser.add_argument("--child-cell-scale", type=float, default=0.16)
    parser.add_argument("--theta-count", type=int, default=10)
    parser.add_argument("--phi-count", type=int, default=18)
    return parser.parse_args()


def create_output_dir() -> Path:
    root = Path("resonance_data")
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = root / f"hydrogen_toy_flash_pointcloud_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def detect_focus(
    entities: List[Entity],
    positions: Dict[str, np.ndarray],
    times: np.ndarray,
    frame_idx: np.ndarray,
    distance_threshold: float,
    phase_threshold: float,
    wave_cell_multiplier: int,
) -> tuple[str | None, int, int]:
    pair_names: List[Tuple[str, str]] = []
    for i in range(len(entities)):
        for j in range(i + 1, len(entities)):
            pair_names.append((entities[i].label, entities[j].label))

    focus_pair: str | None = None
    focus_jump_abs = -1
    focus_frame = 0
    for label_a, label_b in pair_names:
        entity_a = next(item for item in entities if item.label == label_a)
        entity_b = next(item for item in entities if item.label == label_b)
        counts: List[int] = []
        for idx in frame_idx:
            centroids, _ = pair_resonance_for_entities(
                entity_a=entity_a,
                entity_b=entity_b,
                pos_a=positions[label_a][idx],
                pos_b=positions[label_b][idx],
                t=float(times[idx]),
                multiplier=wave_cell_multiplier,
                distance_threshold=distance_threshold,
                phase_threshold=phase_threshold,
            )
            counts.append(int(len(centroids)))
        if len(counts) < 2:
            continue
        best_i = max(range(1, len(counts)), key=lambda i: abs(counts[i] - counts[i - 1]))
        jump_abs = abs(counts[best_i] - counts[best_i - 1])
        if jump_abs > focus_jump_abs:
            focus_jump_abs = jump_abs
            focus_pair = f"{label_a}__{label_b}"
            focus_frame = int(frame_idx[best_i])
    return focus_pair, focus_jump_abs, focus_frame


def render_entity_pointcloud(
    entity: Entity,
    position: np.ndarray,
    t: float,
    theta_grid: np.ndarray,
    phi_grid: np.ndarray,
    child_shell_count: int,
    child_cell_scale: float,
    wave_cell_multiplier: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    xs, ys, zs, cs, _ = shell_model.child_cell_points(
        radii=np.array([entity.base_radius], dtype=np.float64),
        harmonic_orders=np.array([entity.harmonic_order], dtype=np.int64),
        t=float(t),
        child_shell_count=child_shell_count,
        child_cell_scale=child_cell_scale,
        child_theta_grid=theta_grid,
        child_phi_grid=phi_grid,
        wave_cell_multiplier=wave_cell_multiplier,
        center_offset=np.asarray(position, dtype=np.float64),
        phase_offset=float(entity.phase_offset),
        radius_scale=1.0,
    )
    return xs, ys, zs, cs


def main() -> None:
    args = parse_args()
    out_dir = create_output_dir()
    sim_args = argparse.Namespace(
        duration=args.duration,
        dt=args.dt,
        proton_radius=args.proton_radius,
        electron_radius=args.electron_radius,
        electron_frequency=args.electron_frequency,
        frames=args.target_frames,
        gif_fps=12,
    )
    times, quark_series, electron_series, specs = toy.simulate(sim_args)
    entities = build_entities(specs, args.include_electron, args.electron_radius)
    positions = build_positions(times, quark_series, electron_series, specs, args.include_electron)
    frame_idx = subsample_indices(len(times), args.target_frames)

    focus_pair, focus_jump_abs, focus_frame = detect_focus(
        entities=entities,
        positions=positions,
        times=times,
        frame_idx=frame_idx,
        distance_threshold=args.distance_threshold,
        phase_threshold=args.phase_threshold,
        wave_cell_multiplier=args.wave_cell_multiplier,
    )
    if focus_pair is None:
        raise RuntimeError("No focus pair detected; try flash-positive parameters.")

    t_focus = float(times[focus_frame])
    label_a, label_b = focus_pair.split("__")
    entity_a = next(item for item in entities if item.label == label_a)
    entity_b = next(item for item in entities if item.label == label_b)
    theta_grid, phi_grid = shell_model.spherical_grid(args.theta_count, args.phi_count)

    entity_clouds: Dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
    for entity in entities:
        entity_clouds[entity.label] = render_entity_pointcloud(
            entity=entity,
            position=positions[entity.label][focus_frame],
            t=t_focus,
            theta_grid=theta_grid,
            phi_grid=phi_grid,
            child_shell_count=args.child_shell_count,
            child_cell_scale=args.child_cell_scale,
            wave_cell_multiplier=args.wave_cell_multiplier,
        )

    flash_centroids, flash_weights = pair_resonance_for_entities(
        entity_a=entity_a,
        entity_b=entity_b,
        pos_a=positions[label_a][focus_frame],
        pos_b=positions[label_b][focus_frame],
        t=t_focus,
        multiplier=args.wave_cell_multiplier,
        distance_threshold=args.distance_threshold,
        phase_threshold=args.phase_threshold,
    )

    fig = plt.figure(figsize=(11.0, 9.0))
    ax = fig.add_subplot(111, projection="3d")
    for entity in entities:
        xs, ys, zs, cs = entity_clouds[entity.label]
        base_color = "#a78bfa" if entity.role == "electron" else COLOR_TO_PLOT.get(entity.label.split("_")[-1], "#94a3b8")
        ax.scatter(xs, ys, zs, c=cs, cmap="coolwarm", s=5.0, alpha=0.16 if entity.role == "electron" else 0.22, linewidths=0.0)
        pos = positions[entity.label][focus_frame]
        ax.scatter([pos[0]], [pos[1]], [pos[2]], s=90, color=base_color, edgecolors="black", linewidths=0.5, label=entity.label)

    if len(flash_centroids) > 0:
        flash_sizes = 110.0 + 220.0 * (flash_weights / max(float(np.max(flash_weights)), 1e-9))
        ax.scatter(
            flash_centroids[:, 0],
            flash_centroids[:, 1],
            flash_centroids[:, 2],
            c=flash_weights,
            cmap="magma",
            s=flash_sizes,
            alpha=0.98,
            edgecolors="white",
            linewidths=0.6,
            label="flash cells",
        )

    ax.scatter([0.0], [0.0], [0.0], s=70, color="black", marker="x", label="proton center")
    span = max(np.max(np.abs(quark_series[focus_frame])) * 1.9, 2.8)
    ax.set_xlim(-span, span)
    ax.set_ylim(-span, span)
    ax.set_zlim(-span, span)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.set_title(
        f"Hydrogen Toy Flash State Point Cloud\nfocus_pair={focus_pair}, t={t_focus:.2f}, "
        f"phase_threshold={args.phase_threshold:.3f}, distance_threshold={args.distance_threshold:.3f}"
    )
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()

    png_path = out_dir / "hydrogen_toy_flash_pointcloud.png"
    fig.savefig(png_path, dpi=180)
    plt.close(fig)

    traces = []
    for entity in entities:
        xs, ys, zs, cs = entity_clouds[entity.label]
        points = np.column_stack([xs, ys, zs]) if len(xs) else np.zeros((0, 3), dtype=np.float64)
        traces.append(
            point_trace(
                points=points,
                name=f"{entity.label} cloud",
                size=3.0,
                opacity=0.10 if entity.role == "electron" else 0.18,
                color_values=cs if len(cs) else None,
                colorscale="RdBu",
                showscale=False,
            )
        )
        pos = positions[entity.label][focus_frame]
        base_color = "#a78bfa" if entity.role == "electron" else COLOR_TO_PLOT.get(entity.label.split("_")[-1], "#94a3b8")
        traces.append(
            point_trace(
                points=np.array([pos], dtype=np.float64),
                name=entity.label,
                size=6.0,
                opacity=0.98,
                color=base_color,
            )
        )
    if len(flash_centroids) > 0:
        traces.append(
            point_trace(
                points=flash_centroids,
                name="flash cells",
                size=8.0,
                opacity=0.98,
                color_values=flash_weights,
                colorscale="Magma",
                showscale=True,
            )
        )
    traces.append(
        point_trace(
            points=np.array([[0.0, 0.0, 0.0]], dtype=np.float64),
            name="proton center",
            size=5.5,
            opacity=1.0,
            color="#ffffff",
            symbol="x",
        )
    )
    html_path = out_dir / "hydrogen_toy_flash_pointcloud.html"
    save_plotly_3d_html(
        output_path=html_path,
        title=(
            f"Hydrogen Toy Flash State Point Cloud<br>"
            f"focus_pair={focus_pair}, t={t_focus:.2f}, "
            f"phase_threshold={args.phase_threshold:.3f}, distance_threshold={args.distance_threshold:.3f}"
        ),
        traces=traces,
        axis_span=float(span),
    )

    payload = {
        "focus_pair": focus_pair,
        "focus_jump_abs": int(focus_jump_abs),
        "focus_time": float(t_focus),
        "focus_frame_index": int(focus_frame),
        "distance_threshold": float(args.distance_threshold),
        "phase_threshold": float(args.phase_threshold),
        "wave_cell_multiplier": int(args.wave_cell_multiplier),
        "flash_centroid_count": int(len(flash_centroids)),
        "output_png": str(png_path),
        "output_html": str(html_path),
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Run directory: {out_dir}")
    print(f"PNG: {png_path}")
    print(f"Focus pair: {focus_pair}")
    print(f"Focus time: {t_focus:.4f}")
    print(f"Flash centroid count: {len(flash_centroids)}")


if __name__ == "__main__":
    main()
