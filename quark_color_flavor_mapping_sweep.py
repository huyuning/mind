#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quark_color_flavor_mapping_sweep.py

Parameter sweep for the quark color / flavor mapping experiment.
Scans:
  - blend
  - phase_push
  - chirality

For each parameter point, compute the same aggregate criteria as
quark_color_flavor_mapping_test.py and track:
  - mapping_supported
  - cluster_separation_score
  - eigen / flavor stability gap
  - eigen / flavor directionality gap
  - eigen / flavor chirality sensitivity gap

Outputs:
  resonance_data/quark_color_flavor_mapping_sweep_YYYYMMDD_HHMMSS/
    - sweep_summary.json
    - sweep_points.csv
    - sweep_maps.npz
    - mapping_supported_chirality_{pm1}.png
    - cluster_separation_chirality_{pm1}.png
    - directionality_gap_chirality_{pm1}.png
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from quark_color_flavor_mapping_test import (
    build_base_modes,
    compute_asymmetry_matrix,
    compute_baseline_metrics,
    compute_chirality_sensitivity,
    perturbation_robustness,
    simulate_positions,
)


@dataclass
class SweepPoint:
    chirality: int
    blend: float
    phase_push: float
    mapping_supported: bool
    cluster_separation_score: float
    eigen_stability_mean: float
    flavor_self_similarity_mean: float
    stability_gap: float
    eigen_directionality_mean: float
    flavor_directionality_mean: float
    directionality_gap: float
    eigen_chirality_sensitivity_mean: float
    flavor_chirality_sensitivity_mean: float
    chirality_gap: float
    eigen_robustness_mean: float
    flavor_robustness_mean: float
    robustness_gap: float


def parse_float_list(value: str) -> List[float]:
    items = [x.strip() for x in value.split(",") if x.strip()]
    if not items:
        raise argparse.ArgumentTypeError("Expected at least one float value.")
    return [float(x) for x in items]


def parse_int_list(value: str) -> List[int]:
    items = [x.strip() for x in value.split(",") if x.strip()]
    if not items:
        raise argparse.ArgumentTypeError("Expected at least one integer value.")
    values = [int(x) for x in items]
    for val in values:
        if val not in (-1, 1):
            raise argparse.ArgumentTypeError("Chirality values must be -1 or 1.")
    return values


def ensure_out_dir() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("resonance_data") / f"quark_color_flavor_mapping_sweep_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def plot_map(
    path: Path,
    data: np.ndarray,
    blends: List[float],
    phase_pushes: List[float],
    title: str,
    cmap: str = "viridis",
    vmin: float | None = None,
    vmax: float | None = None,
) -> None:
    plt.figure(figsize=(6.0, 4.6))
    plt.imshow(data, cmap=cmap, origin="lower", vmin=vmin, vmax=vmax, aspect="auto")
    plt.title(title)
    plt.xlabel("phase_push")
    plt.ylabel("blend")
    plt.xticks(range(len(phase_pushes)), [f"{x:.3f}" for x in phase_pushes], rotation=45)
    plt.yticks(range(len(blends)), [f"{x:.3f}" for x in blends])
    plt.colorbar(label="value")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def save_csv(path: Path, rows: List[SweepPoint]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def evaluate_configuration(args: argparse.Namespace, chirality: int, blend: float, phase_push: float) -> SweepPoint:
    base_modes = build_base_modes(args)
    rng = np.random.default_rng(args.seed)

    baseline = simulate_positions(
        modes=base_modes,
        duration=args.duration,
        dt=args.dt,
        chirality=chirality,
        blend=blend,
        phase_push=phase_push,
        duty_push=args.duty_push,
        period_push=args.period_push,
        amplitude_push=args.amplitude_push,
    )
    baseline_metrics = compute_baseline_metrics(baseline, base_modes, args.duration, args.dt)
    asymmetry = compute_asymmetry_matrix(baseline)

    flipped = simulate_positions(
        modes=base_modes,
        duration=args.duration,
        dt=args.dt,
        chirality=-chirality,
        blend=blend,
        phase_push=phase_push,
        duty_push=args.duty_push,
        period_push=args.period_push,
        amplitude_push=args.amplitude_push,
    )
    chirality_sensitivity = compute_chirality_sensitivity(baseline, flipped)
    robustness_args = SimpleNamespace(**vars(args))
    robustness_args.chirality = chirality
    robustness_args.blend = blend
    robustness_args.phase_push = phase_push
    robustness = perturbation_robustness(base_modes, robustness_args, rng)

    eigen_self = []
    flavor_self = []
    eigen_asym = []
    flavor_asym = []
    eigen_chiral = []
    flavor_chiral = []
    eigen_rob = []
    flavor_rob = []

    for i in range(3):
        for j in range(3):
            if i == j:
                eigen_self.append(baseline_metrics[(i, j)]["self_score"])
                eigen_asym.append(float(asymmetry[i, j]))
                eigen_chiral.append(float(chirality_sensitivity[i, j]))
                eigen_rob.append(float(robustness[(i, j)][0]))
            else:
                flavor_self.append(baseline_metrics[(i, j)]["self_score"])
                flavor_asym.append(float(asymmetry[i, j]))
                flavor_chiral.append(float(chirality_sensitivity[i, j]))
                flavor_rob.append(float(robustness[(i, j)][0]))

    eigen_stability_mean = float(np.mean(eigen_self))
    flavor_self_similarity_mean = float(np.mean(flavor_self))
    eigen_directionality_mean = float(np.mean(eigen_asym))
    flavor_directionality_mean = float(np.mean(flavor_asym))
    eigen_chirality_sensitivity_mean = float(np.mean(eigen_chiral))
    flavor_chirality_sensitivity_mean = float(np.mean(flavor_chiral))
    eigen_robustness_mean = float(np.mean(eigen_rob))
    flavor_robustness_mean = float(np.mean(flavor_rob))

    stability_gap = eigen_stability_mean - flavor_self_similarity_mean
    directionality_gap = flavor_directionality_mean - eigen_directionality_mean
    chirality_gap = flavor_chirality_sensitivity_mean - eigen_chirality_sensitivity_mean
    robustness_gap = eigen_robustness_mean - flavor_robustness_mean
    cluster_separation_score = 0.5 * (stability_gap + directionality_gap)
    mapping_supported = (
        eigen_stability_mean > flavor_self_similarity_mean + 0.05
        and flavor_directionality_mean > eigen_directionality_mean + 0.05
        and flavor_chirality_sensitivity_mean > eigen_chirality_sensitivity_mean + 0.03
    )

    return SweepPoint(
        chirality=chirality,
        blend=blend,
        phase_push=phase_push,
        mapping_supported=mapping_supported,
        cluster_separation_score=cluster_separation_score,
        eigen_stability_mean=eigen_stability_mean,
        flavor_self_similarity_mean=flavor_self_similarity_mean,
        stability_gap=stability_gap,
        eigen_directionality_mean=eigen_directionality_mean,
        flavor_directionality_mean=flavor_directionality_mean,
        directionality_gap=directionality_gap,
        eigen_chirality_sensitivity_mean=eigen_chirality_sensitivity_mean,
        flavor_chirality_sensitivity_mean=flavor_chirality_sensitivity_mean,
        chirality_gap=chirality_gap,
        eigen_robustness_mean=eigen_robustness_mean,
        flavor_robustness_mean=flavor_robustness_mean,
        robustness_gap=robustness_gap,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep blend, phase_push and chirality for color/flavor mapping stability.")
    parser.add_argument("--duration", type=float, default=12.0, help="Total duration.")
    parser.add_argument("--dt", type=float, default=0.002, help="Time step.")
    parser.add_argument("--modes", type=str, default="1.0,0.50,0.00;1.0,0.50,0.33;1.0,0.50,0.67", help="Three triplets T,D,phi;T,D,phi;T,D,phi")
    parser.add_argument("--amplitudes", type=str, default="1.0,1.0,1.0", help="Three comma-separated amplitudes.")
    parser.add_argument("--blend-values", type=parse_float_list, default=parse_float_list("0.22,0.34,0.46,0.58"), help="Comma-separated blend values.")
    parser.add_argument("--phase-push-values", type=parse_float_list, default=parse_float_list("0.04,0.08,0.12,0.16"), help="Comma-separated phase_push values.")
    parser.add_argument("--chirality-values", type=parse_int_list, default=parse_int_list("-1,1"), help="Comma-separated chirality values from {-1,1}.")
    parser.add_argument("--duty-push", type=float, default=0.06, help="Directed duty warp.")
    parser.add_argument("--period-push", type=float, default=0.05, help="Directed period warp.")
    parser.add_argument("--amplitude-push", type=float, default=0.12, help="Directed amplitude warp.")
    parser.add_argument("--repeats", type=int, default=10, help="Perturbation repeat count per sweep point.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed.")
    parser.add_argument("--period-noise", type=float, default=0.03, help="Relative period noise.")
    parser.add_argument("--duty-noise", type=float, default=0.025, help="Absolute duty noise.")
    parser.add_argument("--phase-noise", type=float, default=0.025, help="Absolute phase noise in cycles.")
    parser.add_argument("--amplitude-noise", type=float, default=0.06, help="Relative amplitude noise.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    blend_values = args.blend_values
    phase_push_values = args.phase_push_values
    chirality_values = args.chirality_values

    rows: List[SweepPoint] = []
    map_supported_maps: Dict[int, np.ndarray] = {}
    cluster_maps: Dict[int, np.ndarray] = {}
    directionality_maps: Dict[int, np.ndarray] = {}

    for chirality in chirality_values:
        support_map = np.zeros((len(blend_values), len(phase_push_values)), dtype=np.float64)
        cluster_map = np.zeros_like(support_map)
        directionality_map = np.zeros_like(support_map)
        for bi, blend in enumerate(blend_values):
            for pi, phase_push in enumerate(phase_push_values):
                point = evaluate_configuration(args, chirality, blend, phase_push)
                rows.append(point)
                support_map[bi, pi] = 1.0 if point.mapping_supported else 0.0
                cluster_map[bi, pi] = point.cluster_separation_score
                directionality_map[bi, pi] = point.directionality_gap
        map_supported_maps[chirality] = support_map
        cluster_maps[chirality] = cluster_map
        directionality_maps[chirality] = directionality_map

    out_dir = ensure_out_dir()
    save_csv(out_dir / "sweep_points.csv", rows)

    np.savez(
        out_dir / "sweep_maps.npz",
        blend_values=np.array(blend_values, dtype=np.float64),
        phase_push_values=np.array(phase_push_values, dtype=np.float64),
        chirality_values=np.array(chirality_values, dtype=np.int64),
        **{f"mapping_supported_chirality_{c}": map_supported_maps[c] for c in chirality_values},
        **{f"cluster_separation_chirality_{c}": cluster_maps[c] for c in chirality_values},
        **{f"directionality_gap_chirality_{c}": directionality_maps[c] for c in chirality_values},
    )

    for chirality in chirality_values:
        suffix = "p1" if chirality > 0 else "m1"
        plot_map(
            out_dir / f"mapping_supported_chirality_{suffix}.png",
            map_supported_maps[chirality],
            blend_values,
            phase_push_values,
            f"Mapping Supported (chirality={chirality})",
            cmap="viridis",
            vmin=0.0,
            vmax=1.0,
        )
        plot_map(
            out_dir / f"cluster_separation_chirality_{suffix}.png",
            cluster_maps[chirality],
            blend_values,
            phase_push_values,
            f"Cluster Separation (chirality={chirality})",
            cmap="magma",
        )
        plot_map(
            out_dir / f"directionality_gap_chirality_{suffix}.png",
            directionality_maps[chirality],
            blend_values,
            phase_push_values,
            f"Directionality Gap (chirality={chirality})",
            cmap="plasma",
        )

    supported_points = [row for row in rows if row.mapping_supported]
    best_point = max(rows, key=lambda r: r.cluster_separation_score)
    summary = {
        "grid": {
            "blend_values": blend_values,
            "phase_push_values": phase_push_values,
            "chirality_values": chirality_values,
            "point_count": len(rows),
        },
        "aggregates": {
            "supported_count": len(supported_points),
            "supported_ratio": len(supported_points) / len(rows) if rows else 0.0,
            "best_cluster_separation_score": best_point.cluster_separation_score,
            "best_point": asdict(best_point),
        },
        "points": [asdict(r) for r in rows],
    }
    with (out_dir / "sweep_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"Output directory: {out_dir}")
    print(f"Point count: {len(rows)}")
    print(f"Supported count: {len(supported_points)}")
    print(f"Supported ratio: {summary['aggregates']['supported_ratio']:.6f}")
    print(f"Best cluster separation score: {best_point.cluster_separation_score:.6f}")
    print(
        "Best point: "
        f"chirality={best_point.chirality}, "
        f"blend={best_point.blend:.6f}, "
        f"phase_push={best_point.phase_push:.6f}"
    )


if __name__ == "__main__":
    main()
