#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quark_color_flavor_mapping_boundary_scan.py

Expanded boundary-focused scan for the color/flavor mapping hypothesis.
Goal:
  enlarge the blend and phase_push ranges and explicitly locate unstable regions
  where `mapping_supported` drops from True to False.

Outputs:
  resonance_data/quark_color_flavor_mapping_boundary_scan_YYYYMMDD_HHMMSS/
    - boundary_summary.json
    - boundary_points.csv
    - unstable_points.csv
    - boundary_maps.npz
    - mapping_supported_chirality_{pm1}.png
    - unstable_mask_chirality_{pm1}.png
    - boundary_mask_chirality_{pm1}.png
    - cluster_separation_chirality_{pm1}.png
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np

from quark_color_flavor_mapping_sweep import evaluate_configuration, plot_map, parse_int_list


@dataclass
class BoundaryPoint:
    chirality: int
    blend: float
    phase_push: float
    mapping_supported: bool
    cluster_separation_score: float
    stability_gap: float
    directionality_gap: float
    chirality_gap: float
    robustness_gap: float
    point_type: str


def ensure_out_dir() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("resonance_data") / f"quark_color_flavor_mapping_boundary_scan_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def build_grid(min_value: float, max_value: float, count: int) -> List[float]:
    if count < 2:
        return [float(min_value)]
    return np.linspace(min_value, max_value, count, dtype=np.float64).tolist()


def save_csv(path: Path, rows: List[BoundaryPoint]) -> None:
    if not rows:
        with path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([field for field in BoundaryPoint.__dataclass_fields__.keys()])
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def compute_boundary_mask(support_map: np.ndarray) -> np.ndarray:
    boundary = np.zeros_like(support_map, dtype=np.float64)
    rows, cols = support_map.shape
    for i in range(rows):
        for j in range(cols):
            current = support_map[i, j]
            neighbors = []
            if i > 0:
                neighbors.append(support_map[i - 1, j])
            if i + 1 < rows:
                neighbors.append(support_map[i + 1, j])
            if j > 0:
                neighbors.append(support_map[i, j - 1])
            if j + 1 < cols:
                neighbors.append(support_map[i, j + 1])
            if any(n != current for n in neighbors):
                boundary[i, j] = 1.0
    return boundary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expanded boundary scan for unstable mapping regions.")
    parser.add_argument("--duration", type=float, default=12.0, help="Total duration.")
    parser.add_argument("--dt", type=float, default=0.002, help="Time step.")
    parser.add_argument("--modes", type=str, default="1.0,0.50,0.00;1.0,0.50,0.33;1.0,0.50,0.67", help="Three triplets T,D,phi;T,D,phi;T,D,phi")
    parser.add_argument("--amplitudes", type=str, default="1.0,1.0,1.0", help="Three comma-separated amplitudes.")
    parser.add_argument("--blend-min", type=float, default=0.05, help="Minimum blend.")
    parser.add_argument("--blend-max", type=float, default=0.98, help="Maximum blend.")
    parser.add_argument("--blend-count", type=int, default=12, help="Number of blend grid points.")
    parser.add_argument("--phase-push-min", type=float, default=0.00, help="Minimum phase_push.")
    parser.add_argument("--phase-push-max", type=float, default=0.50, help="Maximum phase_push.")
    parser.add_argument("--phase-push-count", type=int, default=11, help="Number of phase_push grid points.")
    parser.add_argument("--chirality-values", type=parse_int_list, default=parse_int_list("-1,1"), help="Comma-separated chirality values from {-1,1}.")
    parser.add_argument("--duty-push", type=float, default=0.06, help="Directed duty warp.")
    parser.add_argument("--period-push", type=float, default=0.05, help="Directed period warp.")
    parser.add_argument("--amplitude-push", type=float, default=0.12, help="Directed amplitude warp.")
    parser.add_argument("--repeats", type=int, default=8, help="Perturbation repeat count per point.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed.")
    parser.add_argument("--period-noise", type=float, default=0.03, help="Relative period noise.")
    parser.add_argument("--duty-noise", type=float, default=0.025, help="Absolute duty noise.")
    parser.add_argument("--phase-noise", type=float, default=0.025, help="Absolute phase noise in cycles.")
    parser.add_argument("--amplitude-noise", type=float, default=0.06, help="Relative amplitude noise.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    blend_values = build_grid(args.blend_min, args.blend_max, args.blend_count)
    phase_push_values = build_grid(args.phase_push_min, args.phase_push_max, args.phase_push_count)
    chirality_values = args.chirality_values

    all_points = []
    boundary_points: List[BoundaryPoint] = []
    unstable_points: List[BoundaryPoint] = []
    support_maps: Dict[int, np.ndarray] = {}
    unstable_maps: Dict[int, np.ndarray] = {}
    boundary_maps: Dict[int, np.ndarray] = {}
    cluster_maps: Dict[int, np.ndarray] = {}

    for chirality in chirality_values:
        support_map = np.zeros((len(blend_values), len(phase_push_values)), dtype=np.float64)
        cluster_map = np.zeros_like(support_map)
        point_cache: Dict[tuple[int, int], BoundaryPoint] = {}

        for bi, blend in enumerate(blend_values):
            for pi, phase_push in enumerate(phase_push_values):
                point = evaluate_configuration(args, chirality, blend, phase_push)
                record = BoundaryPoint(
                    chirality=chirality,
                    blend=blend,
                    phase_push=phase_push,
                    mapping_supported=point.mapping_supported,
                    cluster_separation_score=point.cluster_separation_score,
                    stability_gap=point.stability_gap,
                    directionality_gap=point.directionality_gap,
                    chirality_gap=point.chirality_gap,
                    robustness_gap=point.robustness_gap,
                    point_type="regular",
                )
                all_points.append(record)
                point_cache[(bi, pi)] = record
                support_map[bi, pi] = 1.0 if point.mapping_supported else 0.0
                cluster_map[bi, pi] = point.cluster_separation_score

        unstable_map = 1.0 - support_map
        boundary_map = compute_boundary_mask(support_map)

        for (bi, pi), record in point_cache.items():
            if unstable_map[bi, pi] > 0.5:
                unstable_points.append(
                    BoundaryPoint(**{**asdict(record), "point_type": "unstable"})
                )
            if boundary_map[bi, pi] > 0.5:
                boundary_points.append(
                    BoundaryPoint(**{**asdict(record), "point_type": "boundary"})
                )

        support_maps[chirality] = support_map
        unstable_maps[chirality] = unstable_map
        boundary_maps[chirality] = boundary_map
        cluster_maps[chirality] = cluster_map

    out_dir = ensure_out_dir()
    save_csv(out_dir / "boundary_points.csv", boundary_points)
    save_csv(out_dir / "unstable_points.csv", unstable_points)

    np.savez(
        out_dir / "boundary_maps.npz",
        blend_values=np.array(blend_values, dtype=np.float64),
        phase_push_values=np.array(phase_push_values, dtype=np.float64),
        chirality_values=np.array(chirality_values, dtype=np.int64),
        **{f"mapping_supported_chirality_{c}": support_maps[c] for c in chirality_values},
        **{f"unstable_mask_chirality_{c}": unstable_maps[c] for c in chirality_values},
        **{f"boundary_mask_chirality_{c}": boundary_maps[c] for c in chirality_values},
        **{f"cluster_separation_chirality_{c}": cluster_maps[c] for c in chirality_values},
    )

    per_chirality = {}
    for chirality in chirality_values:
        suffix = "p1" if chirality > 0 else "m1"
        plot_map(
            out_dir / f"mapping_supported_chirality_{suffix}.png",
            support_maps[chirality],
            blend_values,
            phase_push_values,
            f"Mapping Supported (chirality={chirality})",
            cmap="viridis",
            vmin=0.0,
            vmax=1.0,
        )
        plot_map(
            out_dir / f"unstable_mask_chirality_{suffix}.png",
            unstable_maps[chirality],
            blend_values,
            phase_push_values,
            f"Unstable Region Mask (chirality={chirality})",
            cmap="Reds",
            vmin=0.0,
            vmax=1.0,
        )
        plot_map(
            out_dir / f"boundary_mask_chirality_{suffix}.png",
            boundary_maps[chirality],
            blend_values,
            phase_push_values,
            f"Boundary Mask (chirality={chirality})",
            cmap="cividis",
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
        unstable_count = int(np.sum(unstable_maps[chirality]))
        boundary_count = int(np.sum(boundary_maps[chirality]))
        per_chirality[str(chirality)] = {
            "unstable_count": unstable_count,
            "boundary_count": boundary_count,
        }

    summary = {
        "grid": {
            "blend_values": blend_values,
            "phase_push_values": phase_push_values,
            "chirality_values": chirality_values,
            "point_count": len(all_points),
        },
        "aggregates": {
            "unstable_count": len(unstable_points),
            "unstable_ratio": len(unstable_points) / len(all_points) if all_points else 0.0,
            "boundary_count": len(boundary_points),
            "boundary_ratio": len(boundary_points) / len(all_points) if all_points else 0.0,
            "per_chirality": per_chirality,
            "first_unstable_point": asdict(unstable_points[0]) if unstable_points else None,
            "first_boundary_point": asdict(boundary_points[0]) if boundary_points else None,
        },
        "boundary_points": [asdict(p) for p in boundary_points],
        "unstable_points": [asdict(p) for p in unstable_points],
    }
    with (out_dir / "boundary_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"Output directory: {out_dir}")
    print(f"Point count: {len(all_points)}")
    print(f"Boundary count: {len(boundary_points)}")
    print(f"Unstable count: {len(unstable_points)}")
    if unstable_points:
        first = unstable_points[0]
        print(
            "First unstable point: "
            f"chirality={first.chirality}, blend={first.blend:.6f}, phase_push={first.phase_push:.6f}"
        )
    else:
        print("No unstable point found in current grid.")


if __name__ == "__main__":
    main()
