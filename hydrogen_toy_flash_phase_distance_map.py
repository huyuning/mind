#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import hydrogen_quark_composition_toy as toy
from hydrogen_toy_flash_analysis import (
    Entity,
    pair_resonance_for_entities,
    subsample_indices,
)


@dataclass
class LocalEnsembleConfig:
    duration: float = 12.0
    dt: float = 0.04
    target_frames: int = 60
    electron_frequency: float = 0.11


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase-distance flash probability maps for the hydrogen toy")
    parser.add_argument("--phase-start", type=float, default=0.98)
    parser.add_argument("--phase-end", type=float, default=1.02)
    parser.add_argument("--phase-step", type=float, default=0.005)
    parser.add_argument("--distance-start", type=float, default=1.20)
    parser.add_argument("--distance-end", type=float, default=1.40)
    parser.add_argument("--distance-step", type=float, default=0.02)
    parser.add_argument("--ensemble-proton", type=float, nargs="+", default=[0.95, 1.00, 1.05])
    parser.add_argument("--ensemble-electron", type=float, nargs="+", default=[4.9, 5.0, 5.1])
    parser.add_argument("--include-electron-options", type=str, nargs="+", default=["false", "true"], choices=["false", "true"])
    parser.add_argument("--wave-cell-multiplier", type=int, default=2)
    parser.add_argument("--outdir", type=str, default=None)
    return parser.parse_args()


def inclusive_range(start: float, end: float, step: float) -> List[float]:
    values: List[float] = []
    current = start
    while current <= end + 1e-9:
        values.append(round(current, 10))
        current += step
    if values and abs(values[-1] - end) > 1e-9:
        values.append(round(end, 10))
    return values


def build_entities(specs: List[toy.QuarkSpec], include_electron: bool, electron_radius: float) -> List[Entity]:
    entities: List[Entity] = []
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


def simulate_modified_toy(
    duration: float,
    dt: float,
    proton_radius: float,
    electron_radius: float,
    electron_frequency: float,
    gb_phase_shift: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, List[toy.QuarkSpec]]:
    specs = toy.build_quark_specs(proton_radius)
    # Interpret "u_green__d_blue initial phase difference +0.05" as shifting d_blue phase forward.
    for spec in specs:
        if spec.label == "d_blue":
            spec.phase += gb_phase_shift
    times = np.arange(0.0, duration + 0.5 * dt, dt, dtype=np.float64)
    quark_series = np.zeros((len(times), len(specs), 3), dtype=np.float64)
    electron_series = np.zeros((len(times), 3), dtype=np.float64)
    for ti, t in enumerate(times):
        for qi, spec in enumerate(specs):
            quark_series[ti, qi] = toy.quark_position(spec, float(t))
        electron_series[ti] = toy.electron_position(electron_radius, electron_frequency, float(t))
    return times, quark_series, electron_series, specs


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


def pair_jump_abs(
    pair_key: str,
    entities: List[Entity],
    positions: Dict[str, np.ndarray],
    times: np.ndarray,
    frame_idx: np.ndarray,
    distance_threshold: float,
    phase_threshold: float,
    wave_cell_multiplier: int,
) -> int:
    label_a, label_b = pair_key.split("__")
    entity_a = next(item for item in entities if item.label == label_a)
    entity_b = next(item for item in entities if item.label == label_b)
    counts: List[int] = []
    for idx in frame_idx:
        t = float(times[idx])
        centroids, _ = pair_resonance_for_entities(
            entity_a=entity_a,
            entity_b=entity_b,
            pos_a=positions[label_a][idx],
            pos_b=positions[label_b][idx],
            t=t,
            multiplier=wave_cell_multiplier,
            distance_threshold=distance_threshold,
            phase_threshold=phase_threshold,
        )
        counts.append(int(len(centroids)))
    if len(counts) < 2:
        return 0
    return max(abs(counts[i] - counts[i - 1]) for i in range(1, len(counts)))


def run_local_case(
    *,
    phase_threshold: float,
    distance_threshold: float,
    proton_radius: float,
    electron_radius: float,
    include_electron: bool,
    wave_cell_multiplier: int,
    base_cfg: LocalEnsembleConfig,
    gb_phase_shift: float,
    rb_perturb_strength: float,
) -> Dict[str, object]:
    times, quark_series, electron_series, specs = simulate_modified_toy(
        duration=base_cfg.duration,
        dt=base_cfg.dt,
        proton_radius=proton_radius,
        electron_radius=electron_radius,
        electron_frequency=base_cfg.electron_frequency,
        gb_phase_shift=gb_phase_shift,
    )
    entities = build_entities(specs, include_electron, electron_radius)
    positions = build_positions(times, quark_series, electron_series, specs, include_electron)
    frame_idx = subsample_indices(len(times), base_cfg.target_frames)

    gb_pair = "u_green__d_blue"
    rb_pair = "u_red__d_blue"
    gb_jump = pair_jump_abs(
        pair_key=gb_pair,
        entities=entities,
        positions=positions,
        times=times,
        frame_idx=frame_idx,
        distance_threshold=distance_threshold,
        phase_threshold=phase_threshold,
        wave_cell_multiplier=wave_cell_multiplier,
    )
    rb_jump = pair_jump_abs(
        pair_key=rb_pair,
        entities=entities,
        positions=positions,
        times=times,
        frame_idx=frame_idx,
        distance_threshold=distance_threshold,
        phase_threshold=phase_threshold,
        wave_cell_multiplier=wave_cell_multiplier,
    )

    # Perturbation mode: let r-b contribute a weak auxiliary channel.
    effective_jump = gb_jump + (rb_perturb_strength * rb_jump)
    flash_detected = effective_jump >= 1.0
    if flash_detected:
        focus_pair = gb_pair if gb_jump >= rb_perturb_strength * rb_jump else rb_pair
    else:
        focus_pair = None
    return {
        "flash_detected": flash_detected,
        "focus_pair": focus_pair,
        "gb_jump_abs": gb_jump,
        "rb_jump_abs": rb_jump,
        "effective_jump": effective_jump,
    }


def compute_map(
    *,
    phase_values: List[float],
    distance_values: List[float],
    proton_radii: List[float],
    electron_radii: List[float],
    include_electron_values: List[bool],
    wave_cell_multiplier: int,
    base_cfg: LocalEnsembleConfig,
    gb_phase_shift: float,
    rb_perturb_strength: float,
) -> tuple[np.ndarray, List[Dict[str, object]], List[Dict[str, object]]]:
    prob = np.zeros((len(distance_values), len(phase_values)), dtype=np.float64)
    rows: List[Dict[str, object]] = []
    summary_rows: List[Dict[str, object]] = []
    for di, distance_threshold in enumerate(distance_values):
        for pi, phase_threshold in enumerate(phase_values):
            local_rows: List[Dict[str, object]] = []
            for proton_radius in proton_radii:
                for electron_radius in electron_radii:
                    for include_electron in include_electron_values:
                        row = run_local_case(
                            phase_threshold=phase_threshold,
                            distance_threshold=distance_threshold,
                            proton_radius=proton_radius,
                            electron_radius=electron_radius,
                            include_electron=include_electron,
                            wave_cell_multiplier=wave_cell_multiplier,
                            base_cfg=base_cfg,
                            gb_phase_shift=gb_phase_shift,
                            rb_perturb_strength=rb_perturb_strength,
                        )
                        full_row = {
                            "phase_threshold": phase_threshold,
                            "distance_threshold": distance_threshold,
                            "proton_radius": proton_radius,
                            "electron_radius": electron_radius,
                            "include_electron": include_electron,
                            **row,
                        }
                        rows.append(full_row)
                        local_rows.append(full_row)
            total = len(local_rows)
            positive = sum(1 for row in local_rows if row["flash_detected"])
            probability = positive / total if total else 0.0
            pair_counts: Dict[str, int] = {}
            for row in local_rows:
                if row["flash_detected"] and row["focus_pair"] is not None:
                    pair_counts[str(row["focus_pair"])] = pair_counts.get(str(row["focus_pair"]), 0) + 1
            dominant_pair = max(pair_counts, key=pair_counts.get) if pair_counts else None
            mean_gb_jump = float(np.mean([float(row["gb_jump_abs"]) for row in local_rows])) if local_rows else 0.0
            mean_rb_jump = float(np.mean([float(row["rb_jump_abs"]) for row in local_rows])) if local_rows else 0.0
            prob[di, pi] = probability
            summary_rows.append(
                {
                    "phase_threshold": phase_threshold,
                    "distance_threshold": distance_threshold,
                    "total_cases": total,
                    "flash_positive": positive,
                    "flash_probability": probability,
                    "dominant_focus_pair": dominant_pair,
                    "mean_gb_jump_abs": mean_gb_jump,
                    "mean_rb_jump_abs": mean_rb_jump,
                }
            )
    return prob, rows, summary_rows


def save_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def render_map(
    path: Path,
    prob: np.ndarray,
    phase_values: List[float],
    distance_values: List[float],
    title: str,
) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 6.2))
    im = ax.imshow(
        prob,
        origin="lower",
        aspect="auto",
        cmap="magma",
        vmin=0.0,
        vmax=1.0,
        extent=[phase_values[0], phase_values[-1], distance_values[0], distance_values[-1]],
    )
    ax.set_xlabel("phase_threshold")
    ax.set_ylabel("distance_threshold")
    ax.set_title(title)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("flash probability")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    phase_values = inclusive_range(args.phase_start, args.phase_end, args.phase_step)
    distance_values = inclusive_range(args.distance_start, args.distance_end, args.distance_step)
    include_electron_values = [item == "true" for item in args.include_electron_options]
    base_cfg = LocalEnsembleConfig()

    root = Path(args.outdir) if args.outdir else Path("resonance_data") / f"hydrogen_toy_flash_phase_distance_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    root.mkdir(parents=True, exist_ok=True)

    configs = [
        ("baseline", 0.0, 0.0, "Baseline: u_green__d_blue Flash Probability"),
        ("gb_phase_shift", 0.05, 0.0, "u_green__d_blue Initial Phase +0.05"),
        ("with_rb_perturb", 0.0, 0.35, "With u_red__d_blue Perturbation"),
    ]

    manifest: Dict[str, object] = {
        "phase_values": phase_values,
        "distance_values": distance_values,
        "ensemble_proton": args.ensemble_proton,
        "ensemble_electron": args.ensemble_electron,
        "include_electron_options": include_electron_values,
        "wave_cell_multiplier": args.wave_cell_multiplier,
        "maps": {},
    }

    for slug, gb_phase_shift, rb_perturb_strength, title in configs:
        prob, detail_rows, summary_rows = compute_map(
            phase_values=phase_values,
            distance_values=distance_values,
            proton_radii=args.ensemble_proton,
            electron_radii=args.ensemble_electron,
            include_electron_values=include_electron_values,
            wave_cell_multiplier=args.wave_cell_multiplier,
            base_cfg=base_cfg,
            gb_phase_shift=gb_phase_shift,
            rb_perturb_strength=rb_perturb_strength,
        )
        png_path = root / f"flash_phase_distance_map_{slug}.png"
        detail_csv = root / f"flash_phase_distance_detail_{slug}.csv"
        summary_csv = root / f"flash_phase_distance_summary_{slug}.csv"
        render_map(png_path, prob, phase_values, distance_values, title)
        save_csv(detail_csv, detail_rows)
        save_csv(summary_csv, summary_rows)
        manifest["maps"][slug] = {
            "gb_phase_shift": gb_phase_shift,
            "rb_perturb_strength": rb_perturb_strength,
            "png": str(png_path),
            "detail_csv": str(detail_csv),
            "summary_csv": str(summary_csv),
        }
        print(f"[map] {slug}: {png_path}")

    summary_path = root / "summary.json"
    summary_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Output directory: {root}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
