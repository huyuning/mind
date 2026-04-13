#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import itertools
import json
import random
import statistics
import subprocess
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="H1 node stability scan for angular modes")
    parser.add_argument("--dimensions", type=int, default=2)
    parser.add_argument("--width", type=int, default=41)
    parser.add_argument("--height", type=int, default=41)
    parser.add_argument("--duration", type=float, default=6.0)
    parser.add_argument("--dt", type=float, default=0.02)
    parser.add_argument("--m-values", type=int, nargs="+", default=[1, 2])
    parser.add_argument("--angular-gains", type=float, nargs="+", default=[0.14, 0.22, 0.30])
    parser.add_argument("--seeds", type=int, nargs="+", default=[20260409, 20260410, 20260411])
    parser.add_argument("--permutation-trials", type=int, default=20000)
    return parser.parse_args()


def permutation_pvalue(xs: list[float], ys: list[float], trials: int) -> tuple[float, float]:
    observed = abs(statistics.mean(xs) - statistics.mean(ys))
    combined = xs + ys
    rng = random.Random(20260410)
    count = 0
    for _ in range(trials):
        rng.shuffle(combined)
        a = combined[: len(xs)]
        b = combined[len(xs) :]
        diff = abs(statistics.mean(a) - statistics.mean(b))
        if diff >= observed - 1e-12:
            count += 1
    return observed, (count + 1) / (trials + 1)


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent
    outdir = root / "resonance_data" / f"h1_node_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    outdir.mkdir(parents=True, exist_ok=True)

    rows = []
    for m, gain, seed in itertools.product(args.m_values, args.angular_gains, args.seeds):
        cmd = [
            "python3",
            "hydrogen_color_field_emergence.py",
            "--dimensions",
            str(args.dimensions),
            "--width",
            str(args.width),
            "--height",
            str(args.height),
            "--duration",
            str(args.duration),
            "--dt",
            str(args.dt),
            "--angular-momentum",
            str(m),
            "--angular-gain",
            str(gain),
            "--seed",
            str(seed),
        ]
        print(f"RUN m={m} gain={gain:.2f} seed={seed}", flush=True)
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=True)
        run_dir = None
        for line in proc.stdout.splitlines():
            if line.startswith("Run directory: "):
                run_dir = line.split(": ", 1)[1].strip()
                break
        if run_dir is None:
            raise RuntimeError("Run directory not found in hydrogen_color_field_emergence.py output")

        summary_files = sorted((root / run_dir).glob("summary_*.json"))
        if not summary_files:
            raise RuntimeError(f"No summary found in {run_dir}")
        summary = json.loads(summary_files[0].read_text(encoding="utf-8"))
        rows.append(
            {
                "m": m,
                "angular_gain": gain,
                "seed": seed,
                "run_dir": run_dir,
                "angular_node_count": summary["angular_node_count"],
                "angular_zero_crossings": summary["angular_zero_crossings"],
                "dominant_angular_harmonic": summary["dominant_angular_harmonic"],
                "angular_contrast": summary["angular_contrast"],
                "effective_radius": summary["effective_radius"],
                "peak_mean": summary["final_peak_to_mean_ratio"],
                "dominant_frequency": summary["probe_dominant_frequency"],
            }
        )

    csv_path = outdir / "h1_node_scan.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    by_m = {}
    for m in args.m_values:
        subset = [r for r in rows if r["m"] == m]
        by_m[str(m)] = {
            "n": len(subset),
            "node_mean": statistics.mean(r["angular_node_count"] for r in subset),
            "node_std": statistics.pstdev(r["angular_node_count"] for r in subset),
            "zero_mean": statistics.mean(r["angular_zero_crossings"] for r in subset),
            "contrast_mean": statistics.mean(r["angular_contrast"] for r in subset),
        }

    by_gain = {}
    for m in args.m_values:
        for gain in args.angular_gains:
            subset = [r for r in rows if r["m"] == m and abs(r["angular_gain"] - gain) < 1e-12]
            by_gain[f"m={m},gain={gain:.2f}"] = {
                "n": len(subset),
                "node_mean": statistics.mean(r["angular_node_count"] for r in subset),
                "node_std": statistics.pstdev(r["angular_node_count"] for r in subset),
                "zero_mean": statistics.mean(r["angular_zero_crossings"] for r in subset),
            }

    m_values = list(args.m_values)
    if len(m_values) != 2:
        raise ValueError("Current analysis expects exactly two m values")
    x_nodes = [r["angular_node_count"] for r in rows if r["m"] == m_values[0]]
    y_nodes = [r["angular_node_count"] for r in rows if r["m"] == m_values[1]]
    node_diff, node_p = permutation_pvalue(x_nodes, y_nodes, args.permutation_trials)

    x_zeros = [r["angular_zero_crossings"] for r in rows if r["m"] == m_values[0]]
    y_zeros = [r["angular_zero_crossings"] for r in rows if r["m"] == m_values[1]]
    zero_diff, zero_p = permutation_pvalue(x_zeros, y_zeros, args.permutation_trials)

    report = {
        "outdir": str(outdir),
        "m_values": args.m_values,
        "angular_gains": args.angular_gains,
        "seeds": args.seeds,
        "by_m": by_m,
        "by_gain": by_gain,
        "node_mean_diff": node_diff,
        "node_permutation_p": node_p,
        "zero_mean_diff": zero_diff,
        "zero_permutation_p": zero_p,
    }
    (outdir / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# H1 Node Scan",
        "",
        f"- outdir: {outdir}",
        f"- node mean diff (m={m_values[0]} vs m={m_values[1]}): {node_diff:.4f}, permutation p={node_p:.4f}",
        f"- zero mean diff (m={m_values[0]} vs m={m_values[1]}): {zero_diff:.4f}, permutation p={zero_p:.4f}",
        "",
        "## By m",
        "",
    ]
    for m, stats in by_m.items():
        lines.append(
            f"- m={m}: n={stats['n']}, node_mean={stats['node_mean']:.3f}, "
            f"node_std={stats['node_std']:.3f}, zero_mean={stats['zero_mean']:.3f}, "
            f"contrast_mean={stats['contrast_mean']:.3f}"
        )
    lines.extend(["", "## By m and gain", ""])
    for key, stats in by_gain.items():
        lines.append(
            f"- {key}: n={stats['n']}, node_mean={stats['node_mean']:.3f}, "
            f"node_std={stats['node_std']:.3f}, zero_mean={stats['zero_mean']:.3f}"
        )
    (outdir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"OUTDIR {outdir}")
    print(f"NODE_DIFF {node_diff:.4f} P {node_p:.4f}")
    print(f"ZERO_DIFF {zero_diff:.4f} P {zero_p:.4f}")
    for m, stats in by_m.items():
        print(
            f"M{m} n={stats['n']} node_mean={stats['node_mean']:.3f} "
            f"node_std={stats['node_std']:.3f} zero_mean={stats['zero_mean']:.3f} "
            f"contrast_mean={stats['contrast_mean']:.3f}"
        )


if __name__ == "__main__":
    main()
