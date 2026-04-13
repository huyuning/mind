#!/usr/bin/env python3
"""
Use the previous spherical point-cloud cell logic to test whether the hydrogen toy
prototype develops flash cells.

Method:
- Reuse `hydrogen_quark_composition_toy.py` as the moving hydrogen toy source.
- Reuse `cellular_shell_basis_animation.py` spherical child-cell center generation.
- Build resonance counts between moving quark-cell point-cloud peaks.
- Detect discrete count jumps (flash birth events).
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import cellular_shell_basis_animation as shell_model
import hydrogen_quark_composition_toy as toy


@dataclass
class Entity:
    label: str
    role: str
    harmonic_order: int
    base_radius: float
    phase_offset: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze flash cells in the hydrogen toy via spherical point clouds")
    parser.add_argument("--duration", type=float, default=14.0, help="toy duration")
    parser.add_argument("--dt", type=float, default=0.04, help="toy dt")
    parser.add_argument("--proton-radius", type=float, default=1.2, help="toy proton radius")
    parser.add_argument("--electron-radius", type=float, default=5.2, help="toy electron shell radius")
    parser.add_argument("--electron-frequency", type=float, default=0.11, help="toy electron shell frequency")
    parser.add_argument("--include-electron", action="store_true", help="include electron shell as an outer cell in flash analysis")
    parser.add_argument("--distance-threshold", type=float, default=1.45, help="resonance distance threshold")
    parser.add_argument("--phase-threshold", type=float, default=0.95, help="resonance phase threshold")
    parser.add_argument("--wave-cell-multiplier", type=int, default=1, help="per-cell wave-center multiplier")
    parser.add_argument("--target-frames", type=int, default=72, help="subsampled frame count for analysis")
    return parser.parse_args()


def build_entities(specs: List[toy.QuarkSpec], include_electron: bool, electron_radius: float) -> List[Entity]:
    entities = []
    for spec in specs:
        harmonic_order = 3 if spec.flavor == "up" else 4
        entities.append(
            Entity(
                label=spec.label,
                role="quark",
                harmonic_order=harmonic_order,
                base_radius=float(spec.base_radius),
                phase_offset=float(spec.phase),
            )
        )
    if include_electron:
        entities.append(
            Entity(
                label="electron_shell",
                role="electron",
                harmonic_order=2,
                base_radius=float(electron_radius * 0.22),
                phase_offset=0.0,
            )
        )
    return entities


def build_positions(
    times: np.ndarray,
    quark_series: np.ndarray,
    electron_series: np.ndarray,
    specs: List[toy.QuarkSpec],
    include_electron: bool,
) -> Dict[str, np.ndarray]:
    positions: Dict[str, np.ndarray] = {}
    for qi, spec in enumerate(specs):
        positions[spec.label] = quark_series[:, qi, :]
    if include_electron:
        positions["electron_shell"] = electron_series
    return positions


def subsample_indices(sample_count: int, target_frames: int) -> np.ndarray:
    stride = max(1, int(math.ceil(sample_count / max(target_frames, 1))))
    return np.arange(0, sample_count, stride, dtype=np.int64)


def pair_resonance_for_entities(
    entity_a: Entity,
    entity_b: Entity,
    pos_a: np.ndarray,
    pos_b: np.ndarray,
    t: float,
    multiplier: int,
    distance_threshold: float,
    phase_threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    centers_a, phases_a = shell_model.child_cell_centers(
        radius=float(entity_a.base_radius),
        harmonic_order=int(entity_a.harmonic_order),
        t=float(t),
        shell_index=0,
        shell_count=1,
        multiplier=multiplier,
        center_offset=pos_a,
        phase_offset=float(entity_a.phase_offset),
        radius_scale=1.0,
    )
    centers_b, phases_b = shell_model.child_cell_centers(
        radius=float(entity_b.base_radius),
        harmonic_order=int(entity_b.harmonic_order),
        t=float(t),
        shell_index=0,
        shell_count=1,
        multiplier=multiplier,
        center_offset=pos_b,
        phase_offset=float(entity_b.phase_offset),
        radius_scale=1.0,
    )
    centroids: List[np.ndarray] = []
    weights: List[float] = []
    count = min(len(centers_a), len(centers_b))
    for idx in range(count):
        dist = float(np.linalg.norm(centers_a[idx] - centers_b[idx]))
        phase_diff = float(shell_model.wrapped_phase_delta(float(phases_a[idx]), float(phases_b[idx])))
        if dist > distance_threshold or phase_diff > phase_threshold:
            continue
        resonance_strength = max(0.0, 1.0 - dist / max(distance_threshold, 1e-6))
        phase_strength = max(0.0, 1.0 - phase_diff / max(phase_threshold, 1e-6))
        centroids.append(0.5 * (centers_a[idx] + centers_b[idx]))
        weights.append(0.5 * (resonance_strength + phase_strength))
    if not centroids:
        return np.zeros((0, 3), dtype=np.float64), np.zeros(0, dtype=np.float64)
    return np.vstack(centroids), np.asarray(weights, dtype=np.float64)


def analyze(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    toy_args = argparse.Namespace(
        duration=args.duration,
        dt=args.dt,
        proton_radius=args.proton_radius,
        electron_radius=args.electron_radius,
        electron_frequency=args.electron_frequency,
        frames=args.target_frames,
        gif_fps=12,
    )
    base_root = Path("resonance_data")
    base_root.mkdir(parents=True, exist_ok=True)
    out_dir = base_root / f"hydrogen_toy_flash_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    times, quark_series, electron_series, specs = toy.simulate(toy_args)
    entities = build_entities(specs, args.include_electron, args.electron_radius)
    positions = build_positions(times, quark_series, electron_series, specs, args.include_electron)
    frame_idx = subsample_indices(len(times), args.target_frames)
    sampled_times = times[frame_idx]

    rows: List[Dict[str, Any]] = []
    pair_names = []
    for i in range(len(entities)):
        for j in range(i + 1, len(entities)):
            pair_names.append((entities[i].label, entities[j].label))

    for ti, idx in enumerate(frame_idx):
        t = float(times[idx])
        row: Dict[str, Any] = {"t": t}
        for label_a, label_b in pair_names:
            entity_a = next(item for item in entities if item.label == label_a)
            entity_b = next(item for item in entities if item.label == label_b)
            centroids, weights = pair_resonance_for_entities(
                entity_a=entity_a,
                entity_b=entity_b,
                pos_a=positions[label_a][idx],
                pos_b=positions[label_b][idx],
                t=t,
                multiplier=args.wave_cell_multiplier,
                distance_threshold=args.distance_threshold,
                phase_threshold=args.phase_threshold,
            )
            pair_key = f"{label_a}__{label_b}"
            row[f"{pair_key}_n"] = int(len(centroids))
            row[f"{pair_key}_mean_w"] = float(np.mean(weights)) if len(weights) else 0.0
        rows.append(row)

    jump_summary: Dict[str, Any] = {}
    focus_pair = None
    focus_jump_abs = -1
    for label_a, label_b in pair_names:
        pair_key = f"{label_a}__{label_b}"
        key = f"{pair_key}_n"
        if len(rows) < 2:
            jump_summary[pair_key] = {"max_jump": 0, "time": 0.0, "prev_count": 0, "count": 0}
            continue
        best_i = max(range(1, len(rows)), key=lambda i: abs(rows[i][key] - rows[i - 1][key]))
        delta = int(rows[best_i][key] - rows[best_i - 1][key])
        jump_summary[pair_key] = {
            "max_jump": delta,
            "time": float(rows[best_i]["t"]),
            "prev_count": int(rows[best_i - 1][key]),
            "count": int(rows[best_i][key]),
        }
        if abs(delta) > focus_jump_abs:
            focus_jump_abs = abs(delta)
            focus_pair = pair_key

    payload = {
        "analysis_type": "hydrogen_toy_spherical_point_cloud_flash",
        "include_electron": bool(args.include_electron),
        "distance_threshold": float(args.distance_threshold),
        "phase_threshold": float(args.phase_threshold),
        "wave_cell_multiplier": int(args.wave_cell_multiplier),
        "pair_names": [f"{a}__{b}" for a, b in pair_names],
        "focus_pair": focus_pair,
        "focus_jump_abs": int(focus_jump_abs),
        "flash_detected": bool(focus_jump_abs > 0),
        "jump_summary": jump_summary,
        "rows": rows,
    }

    json_path = out_dir / "hydrogen_toy_flash_analysis.json"
    md_path = out_dir / "hydrogen_toy_flash_analysis.md"
    png_path = out_dir / "hydrogen_toy_flash_series.png"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_lines = [
        "# Hydrogen Toy Flash Analysis",
        "",
        f"- Flash detected: `{payload['flash_detected']}`",
        f"- Focus pair: `{focus_pair}`",
        f"- Focus jump abs: `{focus_jump_abs}`",
        "",
        "## Jump Summary",
        "",
        "```json",
        json.dumps(jump_summary, indent=2),
        "```",
    ]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(10.6, 5.6))
    for label_a, label_b in pair_names:
        pair_key = f"{label_a}__{label_b}"
        key = f"{pair_key}_n"
        ax.plot(sampled_times, [row[key] for row in rows], linewidth=1.6, label=pair_key)
    ax.set_xlabel("time")
    ax.set_ylabel("resonance count")
    ax.set_title("Hydrogen Toy Flash Count Series")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    return payload, out_dir


def main() -> None:
    args = parse_args()
    payload, out_dir = analyze(args)
    print(f"Run directory: {out_dir}")
    print(f"Flash detected: {payload['flash_detected']}")
    print(f"Focus pair: {payload['focus_pair']}")
    print(f"Focus jump abs: {payload['focus_jump_abs']}")


if __name__ == "__main__":
    main()
