#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np

from csde_dimension_generation import (
    build_dimension_frame,
    orthonormalize_basis,
    phase_from_time,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal validation for CSDE single-cell dimension generation")
    parser.add_argument("--duration", type=float, default=8.0, help="simulation duration")
    parser.add_argument("--dt", type=float, default=0.04, help="sampling interval")
    parser.add_argument("--frequency", type=float, default=0.18, help="phase oscillation frequency")
    parser.add_argument("--phase-offset", type=float, default=0.35, help="initial phase offset")
    parser.add_argument("--sweep-gain", type=float, default=0.9, help="in-plane phase sweep gain")
    parser.add_argument("--lift-gain", type=float, default=0.32, help="out-of-plane lift gain")
    parser.add_argument("--torsion-phase", type=float, default=math.pi / 4.0, help="second-harmonic torsion phase")
    return parser.parse_args()


def create_output_dir() -> Path:
    root = Path("resonance_data")
    root.mkdir(parents=True, exist_ok=True)
    out_dir = root / f"csde_dimension_generation_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def main() -> None:
    args = parse_args()
    out_dir = create_output_dir()

    seed_basis = orthonormalize_basis(
        np.asarray(
            [
                [1.0, 0.2, 0.1],
                [0.1, 1.0, 0.25],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )
    )
    times = np.arange(0.0, args.duration + 0.5 * args.dt, args.dt, dtype=np.float64)
    states = []
    rows = []

    max_norm_error = 0.0
    max_orthogonality_error = 0.0
    min_cross_alignment = 1.0

    for time_value in times:
        phase = phase_from_time(time_value, args.frequency, args.phase_offset)
        state = build_dimension_frame(
            seed_basis,
            phase=phase,
            sweep_gain=args.sweep_gain,
            lift_gain=args.lift_gain,
            torsion_phase=args.torsion_phase,
        )
        states.append(state)

        norm_errors = [
            abs(float(np.linalg.norm(state.n0)) - 1.0),
            abs(float(np.linalg.norm(state.n1)) - 1.0),
            abs(float(np.linalg.norm(state.n2)) - 1.0),
        ]
        ortho_errors = [
            abs(float(np.dot(state.n0, state.n1))),
            abs(float(np.dot(state.n0, state.n2))),
            abs(float(np.dot(state.n1, state.n2))),
        ]
        cross_alignment = abs(float(np.dot(np.cross(state.n0, state.n1), state.n2)))

        max_norm_error = max(max_norm_error, *norm_errors)
        max_orthogonality_error = max(max_orthogonality_error, *ortho_errors)
        min_cross_alignment = min(min_cross_alignment, cross_alignment)

        rows.append(
            {
                "time": float(time_value),
                "phase": float(phase),
                "alpha": float(state.alpha),
                "beta": float(state.beta),
                "n0_x": float(state.n0[0]),
                "n0_y": float(state.n0[1]),
                "n0_z": float(state.n0[2]),
                "n1_x": float(state.n1[0]),
                "n1_y": float(state.n1[1]),
                "n1_z": float(state.n1[2]),
                "n2_x": float(state.n2[0]),
                "n2_y": float(state.n2[1]),
                "n2_z": float(state.n2[2]),
                "n1_strength": float(state.n1_strength),
                "n2_strength": float(state.n2_strength),
                "tangential_speed": float(state.tangential_speed),
                "cross_alignment": cross_alignment,
            }
        )

    tangent_alignments = []
    for idx in range(1, len(states) - 1):
        derivative = (states[idx + 1].n0 - states[idx - 1].n0) / max(2.0 * args.dt, 1e-9)
        tangent = derivative - float(np.dot(derivative, states[idx].n0)) * states[idx].n0
        tangent_norm = float(np.linalg.norm(tangent))
        if tangent_norm < 1e-6:
            continue
        tangent_unit = tangent / tangent_norm
        tangent_alignments.append(abs(float(np.dot(tangent_unit, states[idx].n1))))

    min_tangent_alignment = min(tangent_alignments) if tangent_alignments else 1.0
    mean_tangent_alignment = float(np.mean(tangent_alignments)) if tangent_alignments else 1.0
    n1_strength_range = (
        float(min(state.n1_strength for state in states)),
        float(max(state.n1_strength for state in states)),
    )
    n2_strength_range = (
        float(min(state.n2_strength for state in states)),
        float(max(state.n2_strength for state in states)),
    )

    success = (
        max_norm_error < 1e-5
        and max_orthogonality_error < 1e-5
        and min_cross_alignment > 0.999
        and min_tangent_alignment > 0.95
        and n1_strength_range[1] - n1_strength_range[0] > 0.20
        and n2_strength_range[1] - n2_strength_range[0] > 0.20
    )

    with (out_dir / "dimension_generation_series.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "success": bool(success),
        "duration": float(args.duration),
        "dt": float(args.dt),
        "sample_count": int(len(times)),
        "frequency": float(args.frequency),
        "phase_offset": float(args.phase_offset),
        "sweep_gain": float(args.sweep_gain),
        "lift_gain": float(args.lift_gain),
        "torsion_phase": float(args.torsion_phase),
        "max_norm_error": float(max_norm_error),
        "max_orthogonality_error": float(max_orthogonality_error),
        "min_cross_alignment": float(min_cross_alignment),
        "min_tangent_alignment": float(min_tangent_alignment),
        "mean_tangent_alignment": float(mean_tangent_alignment),
        "n1_strength_range": list(n1_strength_range),
        "n2_strength_range": list(n2_strength_range),
        "output_csv": str(out_dir / "dimension_generation_series.csv"),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Output directory: {out_dir}")
    print(json.dumps(summary, indent=2))
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
