#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from hydrogen_toy_flash_analysis import analyze as analyze_once


@dataclass
class LocalEnsembleConfig:
    duration: float = 12.0
    dt: float = 0.04
    target_frames: int = 60
    electron_frequency: float = 0.11


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize flash probability near the critical phase_threshold")
    parser.add_argument("--phase-start", type=float, default=0.98, help="phase_threshold scan start")
    parser.add_argument("--phase-end", type=float, default=1.02, help="phase_threshold scan end")
    parser.add_argument("--phase-step", type=float, default=0.005, help="phase_threshold scan step")
    parser.add_argument("--distance-thresholds", type=float, nargs="+", default=[1.25, 1.30, 1.35], help="local distance-threshold ensemble")
    parser.add_argument("--proton-radii", type=float, nargs="+", default=[0.95, 1.00, 1.05], help="local proton-radius ensemble")
    parser.add_argument("--electron-radii", type=float, nargs="+", default=[4.9, 5.0, 5.1], help="local electron-radius ensemble")
    parser.add_argument("--include-electron-options", type=str, nargs="+", default=["false", "true"], choices=["false", "true"], help="whether to include electron shell in local ensemble")
    parser.add_argument("--wave-cell-multiplier", type=int, default=2, help="fixed wave-cell multiplier around the critical regime")
    parser.add_argument("--outdir", type=str, default=None, help="optional explicit output directory")
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


def run_one(
    phase_threshold: float,
    distance_threshold: float,
    proton_radius: float,
    electron_radius: float,
    include_electron: bool,
    wave_cell_multiplier: int,
    base_cfg: LocalEnsembleConfig,
) -> Dict[str, Any]:
    args = argparse.Namespace(
        duration=base_cfg.duration,
        dt=base_cfg.dt,
        target_frames=base_cfg.target_frames,
        include_electron=include_electron,
        distance_threshold=distance_threshold,
        phase_threshold=phase_threshold,
        wave_cell_multiplier=wave_cell_multiplier,
        proton_radius=proton_radius,
        electron_radius=electron_radius,
        electron_frequency=base_cfg.electron_frequency,
    )
    payload, out_dir = analyze_once(args)
    return {
        "phase_threshold": phase_threshold,
        "distance_threshold": distance_threshold,
        "proton_radius": proton_radius,
        "electron_radius": electron_radius,
        "include_electron": include_electron,
        "flash_detected": bool(payload.get("flash_detected", False)),
        "focus_pair": payload.get("focus_pair"),
        "focus_jump_abs": int(payload.get("focus_jump_abs", 0)),
        "run_dir": str(out_dir),
    }


def main() -> None:
    args = parse_args()
    base_cfg = LocalEnsembleConfig()
    phase_values = inclusive_range(args.phase_start, args.phase_end, args.phase_step)

    root = Path(args.outdir) if args.outdir else Path("resonance_data") / f"hydrogen_toy_flash_probability_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    root.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    curve_rows: List[Dict[str, Any]] = []

    include_electron_values = [item == "true" for item in args.include_electron_options]

    for phase_threshold in phase_values:
        local_rows: List[Dict[str, Any]] = []
        for distance_threshold in args.distance_thresholds:
            for proton_radius in args.proton_radii:
                for electron_radius in args.electron_radii:
                    for include_electron in include_electron_values:
                        row = run_one(
                            phase_threshold=phase_threshold,
                            distance_threshold=distance_threshold,
                            proton_radius=proton_radius,
                            electron_radius=electron_radius,
                            include_electron=include_electron,
                            wave_cell_multiplier=args.wave_cell_multiplier,
                            base_cfg=base_cfg,
                        )
                        rows.append(row)
                        local_rows.append(row)
        total = len(local_rows)
        positive = sum(1 for row in local_rows if row["flash_detected"])
        probability = positive / total if total else 0.0
        mean_jump = float(np.mean([row["focus_jump_abs"] for row in local_rows])) if local_rows else 0.0
        pair_counts: Dict[str, int] = {}
        for row in local_rows:
            if row["flash_detected"]:
                pair = row["focus_pair"] or "none"
                pair_counts[pair] = pair_counts.get(pair, 0) + 1
        dominant_pair = None
        if pair_counts:
            dominant_pair = max(pair_counts, key=pair_counts.get)
        curve_rows.append(
            {
                "phase_threshold": phase_threshold,
                "total_cases": total,
                "flash_positive": positive,
                "flash_probability": probability,
                "mean_focus_jump_abs": mean_jump,
                "dominant_focus_pair": dominant_pair,
            }
        )
        print(
            f"[curve] phase={phase_threshold:.3f} total={total} positive={positive} "
            f"prob={probability:.4f} dominant_pair={dominant_pair}"
        )

    detail_csv = root / "flash_probability_detail.csv"
    with detail_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    curve_csv = root / "flash_probability_curve.csv"
    with curve_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(curve_rows[0].keys()) if curve_rows else [])
        writer.writeheader()
        for row in curve_rows:
            writer.writerow(row)

    fig, ax = plt.subplots(figsize=(9.4, 5.6))
    x = [row["phase_threshold"] for row in curve_rows]
    y = [row["flash_probability"] for row in curve_rows]
    ax.plot(x, y, marker="o", linewidth=2.0, color="#7c3aed")
    ax.axvline(1.00, color="#ef4444", linestyle="--", linewidth=1.4, label="current critical estimate = 1.00")
    ax.set_xlabel("phase_threshold")
    ax.set_ylabel("flash probability")
    ax.set_title("Hydrogen Toy Flash Probability Near the Critical Phase Threshold")
    ax.set_ylim(-0.03, 1.03)
    ax.grid(alpha=0.25)
    ax.legend(loc="lower right")
    fig.tight_layout()
    png_path = root / "flash_probability_curve.png"
    fig.savefig(png_path, dpi=180)
    plt.close(fig)

    summary = {
        "phase_values": phase_values,
        "distance_thresholds": args.distance_thresholds,
        "proton_radii": args.proton_radii,
        "electron_radii": args.electron_radii,
        "include_electron_options": include_electron_values,
        "wave_cell_multiplier": args.wave_cell_multiplier,
        "curve_rows": curve_rows,
        "detail_csv": str(detail_csv),
        "curve_csv": str(curve_csv),
        "curve_png": str(png_path),
    }
    summary_path = root / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Output directory: {root}")
    print(f"Curve PNG: {png_path}")
    print(f"Curve CSV: {curve_csv}")


if __name__ == "__main__":
    main()
