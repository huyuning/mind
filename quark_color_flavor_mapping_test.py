#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quark_color_flavor_mapping_test.py

Validate the hypothesis:
  - three color charges correspond to three eigen positions
  - six quark flavors correspond to six directed inference positions

Experimental structure:
  1. Build three base eigen modes beta_1, beta_2, beta_3.
  2. Construct nine second-layer positions v_ij.
     - diagonal v_ii: eigen positions
     - off-diagonal v_ij: directed flavor/inference positions
  3. Measure baseline self-preservation, closure and directional asymmetry.
  4. Compare chirality +1 / -1 sensitivity.
  5. Test perturbation robustness with repeated noisy trials.

Outputs:
  resonance_data/quark_color_flavor_mapping_test_YYYYMMDD_HHMMSS/
    - summary.json
    - base_modes.csv
    - nine_positions_metrics.csv
    - self_similarity_heatmap.png
    - asymmetry_heatmap.png
    - chirality_sensitivity_heatmap.png
    - feature_scatter.png
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


COLOR_LABELS = ["color-1", "color-2", "color-3"]
FLAVOR_MAP = {
    (0, 1): "u",
    (1, 0): "d",
    (0, 2): "s",
    (2, 0): "c",
    (1, 2): "b",
    (2, 1): "t",
}


@dataclass
class ModeSpec:
    label: str
    period: float
    duty: float
    phase: float
    amplitude: float


@dataclass
class PositionMetrics:
    name: str
    i: int
    j: int
    role: str
    mapped_label: str
    direction_sign: int
    source_similarity: float
    target_similarity: float
    self_score: float
    closure_score: float
    estimated_period: float
    estimated_phase: float
    binary_duty: float
    mean_level: float
    asymmetry_vs_reverse: float
    chirality_sensitivity: float
    robustness_mean: float
    robustness_std: float


def parse_triplet_list(value: str) -> List[Tuple[float, float, float]]:
    items: List[Tuple[float, float, float]] = []
    for part in value.split(";"):
        part = part.strip()
        if not part:
            continue
        fields = [x.strip() for x in part.split(",")]
        if len(fields) != 3:
            raise argparse.ArgumentTypeError(f"Expected 'T,D,phi', got '{part}'")
        period = float(fields[0])
        duty = float(fields[1])
        phase = float(fields[2]) % 1.0
        if period <= 0:
            raise argparse.ArgumentTypeError(f"Period must be > 0, got {period}")
        if not (0.0 < duty < 1.0):
            raise argparse.ArgumentTypeError(f"Duty must be in (0,1), got {duty}")
        items.append((period, duty, phase))
    if len(items) != 3:
        raise argparse.ArgumentTypeError("Exactly 3 triplets are required.")
    return items


def make_binary_signal(period: float, duty: float, phase: float, duration: float, dt: float) -> np.ndarray:
    n = int(math.ceil(duration / dt))
    t = np.arange(n, dtype=np.float64) * dt
    t0 = (phase % 1.0) * period
    return ((((t - t0) % period) < (duty * period)).astype(np.int8))


def make_continuous_signal(period: float, duty: float, phase: float, amplitude: float, duration: float, dt: float) -> np.ndarray:
    n = int(math.ceil(duration / dt))
    t = np.arange(n, dtype=np.float64) * dt
    t0 = (phase % 1.0) * period
    cycle_pos = ((t - t0) % period) / period
    values = np.zeros(n, dtype=np.float64)
    active = cycle_pos < duty
    if np.any(active):
        local = cycle_pos[active] / duty
        # Raised-cosine pulse on each active window. This is equivalent to sin^2(pi*local)
        # but makes the "cos pulse" interpretation explicit in the code.
        values[active] = amplitude * 0.5 * (1.0 - np.cos(2.0 * np.pi * local))
    return values


def dominant_period(signal: np.ndarray, dt: float) -> float:
    centered = signal.astype(np.float64) - signal.mean()
    n = len(centered)
    nfft = 1 << (n - 1).bit_length()
    spec = np.fft.rfft(centered, n=nfft)
    freqs = np.fft.rfftfreq(nfft, d=dt)
    mag = np.abs(spec)
    if len(mag) <= 1:
        return float("inf")
    k = int(np.argmax(mag[1:]) + 1)
    if freqs[k] <= 0:
        return float("inf")
    return 1.0 / float(freqs[k])


def phase_anchor(binary_signal: np.ndarray, dt: float, period: float) -> float:
    rising = np.nonzero((binary_signal[1:] == 1) & (binary_signal[:-1] == 0))[0] + 1
    if rising.size == 0 or not np.isfinite(period) or period <= 0:
        return 0.0
    t0 = rising[0] * dt
    return float((t0 % period) / period)


def xcorr_peak(sig_a: np.ndarray, sig_b: np.ndarray) -> float:
    a = sig_a.astype(np.float64)
    b = sig_b.astype(np.float64)
    a -= a.mean()
    b -= b.mean()
    sa = a.std()
    sb = b.std()
    if sa == 0.0 or sb == 0.0:
        return 0.0
    corr = np.correlate(a / sa, b / sb, mode="full")
    return float(np.max(corr)) / len(a)


def cyclic_direction_sign(i: int, j: int) -> int:
    if i == j:
        return 0
    return 1 if ((j - i) % 3) == 1 else -1


def mapped_label(i: int, j: int) -> str:
    if i == j:
        return COLOR_LABELS[i]
    return FLAVOR_MAP[(i, j)]


def perturb_modes(
    base_modes: Sequence[ModeSpec],
    rng: np.random.Generator,
    period_noise: float,
    duty_noise: float,
    phase_noise: float,
    amplitude_noise: float,
) -> List[ModeSpec]:
    perturbed: List[ModeSpec] = []
    for mode in base_modes:
        period = max(0.05, mode.period * (1.0 + rng.normal(0.0, period_noise)))
        duty = float(np.clip(mode.duty + rng.normal(0.0, duty_noise), 0.05, 0.95))
        phase = float((mode.phase + rng.normal(0.0, phase_noise)) % 1.0)
        amplitude = max(0.05, mode.amplitude * (1.0 + rng.normal(0.0, amplitude_noise)))
        perturbed.append(
            ModeSpec(
                label=mode.label,
                period=period,
                duty=duty,
                phase=phase,
                amplitude=amplitude,
            )
        )
    return perturbed


def build_base_modes(args: argparse.Namespace) -> List[ModeSpec]:
    triplets = parse_triplet_list(args.modes)
    amps = [float(x) for x in args.amplitudes.split(",")]
    if len(amps) != 3:
        raise argparse.ArgumentTypeError("--amplitudes requires 3 comma-separated values")
    return [
        ModeSpec(f"beta{i + 1}", period=triplets[i][0], duty=triplets[i][1], phase=triplets[i][2], amplitude=amps[i])
        for i in range(3)
    ]


def build_position_signal(
    i: int,
    j: int,
    modes: Sequence[ModeSpec],
    base_cont: Sequence[np.ndarray],
    duration: float,
    dt: float,
    chirality: int,
    blend: float,
    phase_push: float,
    duty_push: float,
    period_push: float,
    amplitude_push: float,
) -> Tuple[np.ndarray, np.ndarray]:
    if i == j:
        mode = modes[i]
        cont = make_continuous_signal(mode.period, mode.duty, mode.phase, mode.amplitude, duration, dt)
        binary = make_binary_signal(mode.period, mode.duty, mode.phase, duration, dt)
        return cont, binary

    sign = cyclic_direction_sign(i, j) * chirality
    src = modes[i]
    tgt = modes[j]

    period = tgt.period * max(0.05, 1.0 + sign * period_push + 0.04 * (i - j))
    duty = float(np.clip(tgt.duty + sign * duty_push + 0.02 * (src.duty - tgt.duty), 0.05, 0.95))
    phase = float((tgt.phase + sign * phase_push + 0.14 * (src.phase - tgt.phase)) % 1.0)
    amplitude = tgt.amplitude * max(0.05, 1.0 + sign * amplitude_push)

    derived = make_continuous_signal(period, duty, phase, amplitude, duration, dt)
    shift_samples = int(round(sign * phase_push * tgt.period / dt))
    src_shifted = np.roll(base_cont[i], shift_samples)

    if sign >= 0:
        signal = (1.0 - blend) * derived + blend * (0.75 * src_shifted + 0.25 * base_cont[j])
    else:
        signal = (1.0 - blend) * derived + blend * (0.25 * src_shifted + 0.75 * base_cont[j])

    max_val = float(np.max(signal))
    binary = (signal >= 0.45 * max_val).astype(np.int8) if max_val > 0 else np.zeros_like(signal, dtype=np.int8)
    return signal, binary


def simulate_positions(
    modes: Sequence[ModeSpec],
    duration: float,
    dt: float,
    chirality: int,
    blend: float,
    phase_push: float,
    duty_push: float,
    period_push: float,
    amplitude_push: float,
) -> Dict[Tuple[int, int], Dict[str, np.ndarray]]:
    base_cont = [
        make_continuous_signal(m.period, m.duty, m.phase, m.amplitude, duration, dt)
        for m in modes
    ]
    base_bin = [
        make_binary_signal(m.period, m.duty, m.phase, duration, dt)
        for m in modes
    ]

    positions: Dict[Tuple[int, int], Dict[str, np.ndarray]] = {}
    for i in range(3):
        for j in range(3):
            cont, binary = build_position_signal(
                i=i,
                j=j,
                modes=modes,
                base_cont=base_cont,
                duration=duration,
                dt=dt,
                chirality=chirality,
                blend=blend,
                phase_push=phase_push,
                duty_push=duty_push,
                period_push=period_push,
                amplitude_push=amplitude_push,
            )
            positions[(i, j)] = {
                "continuous": cont,
                "binary": binary,
            }
    positions[(-1, -1)] = {  # helper storage
        "base_cont": np.array(base_cont, dtype=np.float64),
        "base_bin": np.array(base_bin, dtype=np.int8),
    }
    return positions


def compute_baseline_metrics(
    positions: Dict[Tuple[int, int], Dict[str, np.ndarray]],
    modes: Sequence[ModeSpec],
    duration: float,
    dt: float,
) -> Dict[Tuple[int, int], Dict[str, float]]:
    base_cont = positions[(-1, -1)]["base_cont"]
    metrics: Dict[Tuple[int, int], Dict[str, float]] = {}
    for i in range(3):
        for j in range(3):
            cont = positions[(i, j)]["continuous"]
            binary = positions[(i, j)]["binary"]
            source_similarity = xcorr_peak(cont, base_cont[i])
            target_similarity = xcorr_peak(cont, base_cont[j])
            if i == j:
                closure = source_similarity
            else:
                closure = max(0.0, source_similarity * target_similarity)
            metrics[(i, j)] = {
                "source_similarity": source_similarity,
                "target_similarity": target_similarity,
                "self_score": source_similarity,
                "closure_score": closure,
                "estimated_period": dominant_period(cont, dt),
                "estimated_phase": phase_anchor(binary, dt, modes[j].period if i != j else modes[i].period),
                "binary_duty": float(binary.mean()),
                "mean_level": float(cont.mean()),
            }
    return metrics


def compute_asymmetry_matrix(
    positions: Dict[Tuple[int, int], Dict[str, np.ndarray]],
) -> np.ndarray:
    matrix = np.zeros((3, 3), dtype=np.float64)
    for i in range(3):
        for j in range(3):
            if i == j:
                matrix[i, j] = 0.0
            else:
                a = positions[(i, j)]["continuous"]
                b = positions[(j, i)]["continuous"]
                matrix[i, j] = max(0.0, 1.0 - xcorr_peak(a, b))
    return matrix


def compute_chirality_sensitivity(
    baseline: Dict[Tuple[int, int], Dict[str, np.ndarray]],
    flipped: Dict[Tuple[int, int], Dict[str, np.ndarray]],
) -> np.ndarray:
    matrix = np.zeros((3, 3), dtype=np.float64)
    for i in range(3):
        for j in range(3):
            matrix[i, j] = max(
                0.0,
                1.0 - xcorr_peak(
                    baseline[(i, j)]["continuous"],
                    flipped[(i, j)]["continuous"],
                ),
            )
    return matrix


def perturbation_robustness(
    base_modes: Sequence[ModeSpec],
    args: argparse.Namespace,
    rng: np.random.Generator,
) -> Dict[Tuple[int, int], Tuple[float, float]]:
    values: Dict[Tuple[int, int], List[float]] = {(i, j): [] for i in range(3) for j in range(3)}
    for _ in range(args.repeats):
        noisy_modes = perturb_modes(
            base_modes=base_modes,
            rng=rng,
            period_noise=args.period_noise,
            duty_noise=args.duty_noise,
            phase_noise=args.phase_noise,
            amplitude_noise=args.amplitude_noise,
        )
        sim = simulate_positions(
            modes=noisy_modes,
            duration=args.duration,
            dt=args.dt,
            chirality=args.chirality,
            blend=args.blend,
            phase_push=args.phase_push,
            duty_push=args.duty_push,
            period_push=args.period_push,
            amplitude_push=args.amplitude_push,
        )
        metrics = compute_baseline_metrics(sim, noisy_modes, args.duration, args.dt)
        for key in values:
            values[key].append(metrics[key]["self_score"])
    result: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for key, seq in values.items():
        arr = np.array(seq, dtype=np.float64)
        result[key] = (float(arr.mean()), float(arr.std(ddof=0)))
    return result


def plot_heatmap(path: Path, data: np.ndarray, title: str, cmap: str = "viridis", vmin: float | None = None, vmax: float | None = None) -> None:
    plt.figure(figsize=(5.4, 4.4))
    plt.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax)
    plt.title(title)
    plt.xlabel("j")
    plt.ylabel("i")
    plt.xticks([0, 1, 2], ["1", "2", "3"])
    plt.yticks([0, 1, 2], ["1", "2", "3"])
    plt.colorbar(label="value")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def plot_feature_scatter(path: Path, records: Sequence[PositionMetrics]) -> None:
    plt.figure(figsize=(6.2, 4.8))
    for rec in records:
        color = "#1f77b4" if rec.role == "eigen" else "#d62728"
        marker = "o" if rec.role == "eigen" else "s"
        plt.scatter(rec.self_score, rec.asymmetry_vs_reverse, color=color, marker=marker, s=60)
        plt.text(rec.self_score + 0.003, rec.asymmetry_vs_reverse + 0.003, rec.name, fontsize=8)
    plt.xlabel("Self Similarity")
    plt.ylabel("Directional Asymmetry")
    plt.title("Eigen vs Flavor Feature Separation")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def save_base_modes(path: Path, modes: Sequence[ModeSpec]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "period", "frequency", "duty", "phase", "amplitude"])
        for mode in modes:
            writer.writerow([
                mode.label,
                f"{mode.period:.6f}",
                f"{1.0 / mode.period:.6f}",
                f"{mode.duty:.6f}",
                f"{mode.phase:.6f}",
                f"{mode.amplitude:.6f}",
            ])


def save_metrics_csv(path: Path, records: Sequence[PositionMetrics]) -> None:
    fieldnames = list(asdict(records[0]).keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow(asdict(rec))


def ensure_out_dir() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("resonance_data") / f"quark_color_flavor_mapping_test_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the 3-color / 6-flavor mapping hypothesis.")
    parser.add_argument("--duration", type=float, default=12.0, help="Total duration.")
    parser.add_argument("--dt", type=float, default=0.002, help="Time step.")
    parser.add_argument("--modes", type=str, default="1.0,0.50,0.00;1.0,0.50,0.33;1.0,0.50,0.67", help="Three triplets T,D,phi;T,D,phi;T,D,phi")
    parser.add_argument("--amplitudes", type=str, default="1.0,1.0,1.0", help="Three comma-separated amplitudes.")
    parser.add_argument("--chirality", type=int, choices=[-1, 1], default=1, help="Baseline chirality.")
    parser.add_argument("--blend", type=float, default=0.34, help="Source-target mixing for directed flavor positions.")
    parser.add_argument("--phase-push", type=float, default=0.09, help="Directed phase warp.")
    parser.add_argument("--duty-push", type=float, default=0.06, help="Directed duty warp.")
    parser.add_argument("--period-push", type=float, default=0.05, help="Directed period warp.")
    parser.add_argument("--amplitude-push", type=float, default=0.12, help="Directed amplitude warp.")
    parser.add_argument("--repeats", type=int, default=14, help="Perturbation repeat count.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed.")
    parser.add_argument("--period-noise", type=float, default=0.03, help="Relative period noise.")
    parser.add_argument("--duty-noise", type=float, default=0.025, help="Absolute duty noise.")
    parser.add_argument("--phase-noise", type=float, default=0.025, help="Absolute phase noise in cycles.")
    parser.add_argument("--amplitude-noise", type=float, default=0.06, help="Relative amplitude noise.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    base_modes = build_base_modes(args)

    baseline = simulate_positions(
        modes=base_modes,
        duration=args.duration,
        dt=args.dt,
        chirality=args.chirality,
        blend=args.blend,
        phase_push=args.phase_push,
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
        chirality=-args.chirality,
        blend=args.blend,
        phase_push=args.phase_push,
        duty_push=args.duty_push,
        period_push=args.period_push,
        amplitude_push=args.amplitude_push,
    )
    chirality_sensitivity = compute_chirality_sensitivity(baseline, flipped)
    robustness = perturbation_robustness(base_modes, args, rng)

    records: List[PositionMetrics] = []
    for i in range(3):
        for j in range(3):
            role = "eigen" if i == j else "flavor"
            name = f"v{i + 1}{j + 1}"
            rec = PositionMetrics(
                name=name,
                i=i + 1,
                j=j + 1,
                role=role,
                mapped_label=mapped_label(i, j),
                direction_sign=cyclic_direction_sign(i, j) * args.chirality,
                source_similarity=baseline_metrics[(i, j)]["source_similarity"],
                target_similarity=baseline_metrics[(i, j)]["target_similarity"],
                self_score=baseline_metrics[(i, j)]["self_score"],
                closure_score=baseline_metrics[(i, j)]["closure_score"],
                estimated_period=baseline_metrics[(i, j)]["estimated_period"],
                estimated_phase=baseline_metrics[(i, j)]["estimated_phase"],
                binary_duty=baseline_metrics[(i, j)]["binary_duty"],
                mean_level=baseline_metrics[(i, j)]["mean_level"],
                asymmetry_vs_reverse=float(asymmetry[i, j]),
                chirality_sensitivity=float(chirality_sensitivity[i, j]),
                robustness_mean=robustness[(i, j)][0],
                robustness_std=robustness[(i, j)][1],
            )
            records.append(rec)

    eigen_records = [r for r in records if r.role == "eigen"]
    flavor_records = [r for r in records if r.role == "flavor"]

    eigen_self_mean = float(np.mean([r.self_score for r in eigen_records]))
    flavor_self_mean = float(np.mean([r.self_score for r in flavor_records]))
    eigen_asym_mean = float(np.mean([r.asymmetry_vs_reverse for r in eigen_records]))
    flavor_asym_mean = float(np.mean([r.asymmetry_vs_reverse for r in flavor_records]))
    eigen_chiral_mean = float(np.mean([r.chirality_sensitivity for r in eigen_records]))
    flavor_chiral_mean = float(np.mean([r.chirality_sensitivity for r in flavor_records]))
    eigen_robust_mean = float(np.mean([r.robustness_mean for r in eigen_records]))
    flavor_robust_mean = float(np.mean([r.robustness_mean for r in flavor_records]))

    cluster_separation_score = 0.5 * ((eigen_self_mean - flavor_self_mean) + (flavor_asym_mean - eigen_asym_mean))
    mapping_supported = (
        eigen_self_mean > flavor_self_mean + 0.05
        and flavor_asym_mean > eigen_asym_mean + 0.05
        and flavor_chiral_mean > eigen_chiral_mean + 0.03
    )

    out_dir = ensure_out_dir()
    save_base_modes(out_dir / "base_modes.csv", base_modes)
    save_metrics_csv(out_dir / "nine_positions_metrics.csv", records)

    self_map = np.array([[baseline_metrics[(i, j)]["self_score"] for j in range(3)] for i in range(3)], dtype=np.float64)
    plot_heatmap(out_dir / "self_similarity_heatmap.png", self_map, "Self Similarity Heatmap", vmin=0.0, vmax=1.0)
    plot_heatmap(out_dir / "asymmetry_heatmap.png", asymmetry, "Directional Asymmetry Heatmap", vmin=0.0, vmax=1.0)
    plot_heatmap(out_dir / "chirality_sensitivity_heatmap.png", chirality_sensitivity, "Chirality Sensitivity Heatmap", vmin=0.0, vmax=1.0)
    plot_feature_scatter(out_dir / "feature_scatter.png", records)

    summary = {
        "hypothesis": {
            "colors_to_eigen": ["v11", "v22", "v33"],
            "flavors_to_directed_positions": ["v12", "v21", "v13", "v31", "v23", "v32"],
            "flavor_map": {f"v{i + 1}{j + 1}": FLAVOR_MAP[(i, j)] for (i, j) in FLAVOR_MAP},
        },
        "config": {
            "duration": args.duration,
            "dt": args.dt,
            "chirality": args.chirality,
            "blend": args.blend,
            "phase_push": args.phase_push,
            "duty_push": args.duty_push,
            "period_push": args.period_push,
            "amplitude_push": args.amplitude_push,
            "repeats": args.repeats,
            "seed": args.seed,
            "period_noise": args.period_noise,
            "duty_noise": args.duty_noise,
            "phase_noise": args.phase_noise,
            "amplitude_noise": args.amplitude_noise,
        },
        "base_modes": [asdict(m) for m in base_modes],
        "aggregate": {
            "eigen_stability_mean": eigen_self_mean,
            "flavor_self_similarity_mean": flavor_self_mean,
            "eigen_directionality_mean": eigen_asym_mean,
            "flavor_directionality_mean": flavor_asym_mean,
            "eigen_chirality_sensitivity_mean": eigen_chiral_mean,
            "flavor_chirality_sensitivity_mean": flavor_chiral_mean,
            "eigen_robustness_mean": eigen_robust_mean,
            "flavor_robustness_mean": flavor_robust_mean,
            "cluster_separation_score": float(cluster_separation_score),
            "mapping_supported": bool(mapping_supported),
        },
        "positions": [asdict(r) for r in records],
    }
    with (out_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"Output directory: {out_dir}")
    print(f"Eigen stability mean: {eigen_self_mean:.6f}")
    print(f"Flavor self-similarity mean: {flavor_self_mean:.6f}")
    print(f"Flavor directionality mean: {flavor_asym_mean:.6f}")
    print(f"Cluster separation score: {cluster_separation_score:.6f}")
    print(f"Mapping supported: {mapping_supported}")


if __name__ == "__main__":
    main()
