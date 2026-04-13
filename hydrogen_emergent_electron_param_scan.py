#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import hydrogen_quark_composition_toy as toy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan emergent electron-cloud parameters for the hydrogen toy")
    parser.add_argument("--duration", type=float, default=14.0, help="simulation duration")
    parser.add_argument("--dt", type=float, default=0.04, help="simulation timestep")
    parser.add_argument("--proton-radius", type=float, default=1.2, help="mean proton-core scale")
    parser.add_argument("--field-couplings", type=float, nargs="+", default=[0.70, 0.82, 0.94], help="field coupling scan values")
    parser.add_argument("--cloud-breathing-gains", type=float, nargs="+", default=[0.04, 0.07, 0.10], help="breathing gain scan values")
    parser.add_argument("--center-offset-gains", type=float, nargs="+", default=[0.005, 0.018, 0.03], help="center offset gain scan values")
    parser.add_argument("--bohr-ratio-scales", type=float, nargs="+", default=[0.90, 1.00, 1.10], help="physical Bohr-ratio scale scan values")
    parser.add_argument("--cloud-anisotropy-gain", type=float, default=0.08, help="fixed anisotropy gain")
    parser.add_argument("--visual-compression-exp", type=float, default=0.14, help="visual compression exponent")
    parser.add_argument("--top-k", type=int, default=10, help="number of top configs to highlight")
    return parser.parse_args()


def create_output_dir() -> Path:
    root = Path("resonance_data")
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = root / f"hydrogen_emergent_electron_param_scan_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def evaluate_config(args: argparse.Namespace, field_coupling: float, breathing_gain: float, center_offset_gain: float, bohr_ratio_scale: float) -> Dict[str, Any]:
    sim_args = SimpleNamespace(
        duration=args.duration,
        dt=args.dt,
        proton_radius=args.proton_radius,
        electron_mode="emergent",
        electron_radius=5.2,
        electron_frequency=0.11,
        target_bohr_ratio=toy.STANDARD_BOHR_RATIO,
        bohr_ratio_scale=bohr_ratio_scale,
        visual_compression_exp=args.visual_compression_exp,
        field_coupling=field_coupling,
        cloud_breathing_gain=breathing_gain,
        cloud_anisotropy_gain=args.cloud_anisotropy_gain,
        center_offset_gain=center_offset_gain,
        frames=72,
        gif_fps=12,
    )
    times, quark_series, electron_series, cloud, specs = toy.simulate_with_cloud(sim_args)
    summary = toy.summarize(times, quark_series, electron_series, specs, cloud)

    center_offset_ratio = summary.electron_cloud_center_offset_mean / max(summary.electron_probability_shell_radius_mean, 1e-9)
    physical_ratio_error = abs(summary.electron_shell_ratio_to_core_mean - toy.STANDARD_BOHR_RATIO) / toy.STANDARD_BOHR_RATIO
    excitation_std_ratio = summary.electron_probability_shell_radius_std / max(summary.electron_probability_shell_radius_mean, 1e-9)
    anisotropy_mean = summary.electron_shell_anisotropy_mean
    score = (
        1.8 * physical_ratio_error
        + 1.5 * center_offset_ratio
        + 1.0 * anisotropy_mean
        + 0.8 * excitation_std_ratio
    )
    return {
        "field_coupling": field_coupling,
        "cloud_breathing_gain": breathing_gain,
        "center_offset_gain": center_offset_gain,
        "bohr_ratio_scale": bohr_ratio_scale,
        "electron_probability_shell_radius_mean": summary.electron_probability_shell_radius_mean,
        "electron_probability_shell_radius_std": summary.electron_probability_shell_radius_std,
        "electron_probability_shell_physical_radius_mean": summary.electron_probability_shell_physical_radius_mean,
        "electron_shell_ratio_to_core_mean": summary.electron_shell_ratio_to_core_mean,
        "electron_cloud_center_offset_mean": summary.electron_cloud_center_offset_mean,
        "center_offset_ratio": center_offset_ratio,
        "electron_shell_anisotropy_mean": anisotropy_mean,
        "electron_excitation_std": summary.electron_excitation_std,
        "physical_ratio_error": physical_ratio_error,
        "excitation_std_ratio": excitation_std_ratio,
        "score": score,
    }


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_topk_plot(path: Path, rows: List[Dict[str, Any]], top_k: int) -> None:
    rows = sorted(rows, key=lambda item: item["score"])[:top_k]
    labels = [
        (
            f"k={row['field_coupling']:.2f}, "
            f"b={row['cloud_breathing_gain']:.2f}, "
            f"c={row['center_offset_gain']:.3f}, "
            f"r={row['bohr_ratio_scale']:.2f}"
        )
        for row in rows
    ]
    scores = [row["score"] for row in rows]

    fig, ax = plt.subplots(figsize=(11.5, 6.0))
    ax.barh(range(len(rows)), scores, color="#7c3aed", alpha=0.85)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("physics-likeness score (lower is better)")
    ax.set_title("Emergent Electron Probability Shell Parameter Scan")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    out_dir = create_output_dir()
    rows: List[Dict[str, Any]] = []
    for field_coupling in args.field_couplings:
        for breathing_gain in args.cloud_breathing_gains:
            for center_offset_gain in args.center_offset_gains:
                for bohr_ratio_scale in args.bohr_ratio_scales:
                    rows.append(
                        evaluate_config(
                            args=args,
                            field_coupling=field_coupling,
                            breathing_gain=breathing_gain,
                            center_offset_gain=center_offset_gain,
                            bohr_ratio_scale=bohr_ratio_scale,
                        )
                    )

    rows.sort(key=lambda item: item["score"])
    csv_path = out_dir / "emergent_electron_scan.csv"
    plot_path = out_dir / "emergent_electron_scan_topk.png"
    summary_path = out_dir / "summary.json"
    write_csv(csv_path, rows)
    save_topk_plot(plot_path, rows, args.top_k)

    summary = {
        "scan_size": len(rows),
        "standard_bohr_ratio": toy.STANDARD_BOHR_RATIO,
        "top_k": args.top_k,
        "best_config": rows[0] if rows else None,
        "csv": str(csv_path),
        "plot": str(plot_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Run directory: {out_dir}")
    if rows:
        print(f"Best config score: {rows[0]['score']:.6f}")
        print(
            "Best config: "
            f"field={rows[0]['field_coupling']:.2f}, "
            f"breathing={rows[0]['cloud_breathing_gain']:.2f}, "
            f"offset={rows[0]['center_offset_gain']:.3f}, "
            f"ratio_scale={rows[0]['bohr_ratio_scale']:.2f}"
        )


if __name__ == "__main__":
    main()
