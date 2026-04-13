#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
second_layer_nine_positions_test.py

Experimentally test the relationships among the 9 positions (v_ij) in the second layer
under the new logic:
- Three dynamic eigen positions are along the diagonal (i == j): v11, v22, v33.
- Six relation positions are off-diagonal (i != j): v12, v13, v21, v23, v31, v32.

We generate three 0-1 square-wave dynamic modes (β1, β2, β3) with configurable
cycle T, duty D, and phase φ. Then we compute pairwise metrics for each (i, j):
- main period T_i, T_j
- duty cycle D_i, D_j
- phase anchor φ_i, φ_j (estimated via first rising edge modulo T)
- skeleton match ratio S_ij (flip-event matching within tolerance)
- cross-correlation peak C_ij (max normalized xcorr)
- period ratio rT_ij = T_j / T_i
- phase offset Δφ_ij normalized to [0, 1)

Outputs:
- A timestamped directory under resonance_data/second_layer_nine_test_YYYYMMDD_HHMMSS
- CSV table with metrics
- Heatmaps (PNG) for skeleton match and xcorr peak
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass
class ModeSpec:
    T: float      # main cycle
    D: float      # duty cycle in (0,1)
    phi: float    # phase offset in cycles [0,1)


def parse_triplet_list(value: str) -> List[Tuple[float, float, float]]:
    """
    Parse a semicolon-separated list of triplets: "T,D,phi;T,D,phi;T,D,phi"
    where phi is given in cycles [0,1).
    """
    items: List[Tuple[float, float, float]] = []
    for part in value.split(";"):
        part = part.strip()
        if not part:
            continue
        fields = [x.strip() for x in part.split(",")]
        if len(fields) != 3:
            raise argparse.ArgumentTypeError(
                f"Expected triplet 'T,D,phi', got '{part}'"
            )
        T = float(fields[0])
        D = float(fields[1])
        phi = float(fields[2])
        if not (0.0 < D < 1.0):
            raise argparse.ArgumentTypeError(f"D must be in (0,1), got {D}")
        phi = phi % 1.0
        if T <= 0:
            raise argparse.ArgumentTypeError(f"T must be > 0, got {T}")
        items.append((T, D, phi))
    if len(items) != 3:
        raise argparse.ArgumentTypeError("Exactly 3 triplets are required for three modes.")
    return items


def make_square_signal(T: float, D: float, phi: float, duration: float, dt: float) -> np.ndarray:
    """
    Generate a 0-1 square wave with period T, duty D, phase phi (in cycles) over given duration.
    """
    n = int(math.ceil(duration / dt))
    t = np.arange(n, dtype=np.float64) * dt
    # Phase in time
    t0 = (phi % 1.0) * T
    # within each period, on if ((t + phase) mod T) < D*T
    x = ((t + t0) % T) < (D * T)
    return x.astype(np.int8)


def flip_indices(sig: np.ndarray) -> np.ndarray:
    """
    Indices where the signal flips (0->1 or 1->0).
    """
    # prepend first element to align diffs
    diffs = np.diff(sig.astype(np.int8))
    idx = np.nonzero(diffs != 0)[0] + 1  # flip happens at index i where sig[i] != sig[i-1]
    return idx


def main_period(sig: np.ndarray, dt: float) -> float:
    """
    Estimate main period via FFT dominant frequency (excluding DC).
    """
    x = sig.astype(np.float64) - sig.mean()
    n = len(x)
    # Next power of 2 for FFT speed
    nfft = 1 << (n - 1).bit_length()
    X = np.fft.rfft(x, n=nfft)
    freqs = np.fft.rfftfreq(nfft, d=dt)
    # Exclude DC bin at index 0
    mag = np.abs(X)
    if len(mag) <= 1:
        return float("inf")
    k = np.argmax(mag[1:]) + 1
    f = freqs[k]
    if f <= 0:
        return float("inf")
    return 1.0 / f


def duty_cycle(sig: np.ndarray) -> float:
    return float(sig.mean())


def phase_anchor(sig: np.ndarray, dt: float, T_est: float) -> float:
    """
    Estimate phase anchor (in cycles [0,1)) as the time of the first rising edge modulo T_est.
    If no rising edge exists, fall back to 0.
    """
    s = sig.astype(np.int8)
    rising = np.nonzero((s[1:] == 1) & (s[:-1] == 0))[0] + 1
    if rising.size == 0 or not np.isfinite(T_est) or T_est <= 0:
        return 0.0
    t_rise0 = rising[0] * dt
    return (t_rise0 % T_est) / T_est


def skeleton_match_ratio(sig_a: np.ndarray, sig_b: np.ndarray, tol_edges: int = 1) -> float:
    """
    Compare flip-event skeletons. Match ratio = matched_edges / max(len(edges_a), len(edges_b)).
    Two edges match if indices differ by <= tol_edges.
    """
    ea = flip_indices(sig_a)
    eb = flip_indices(sig_b)
    if ea.size == 0 and eb.size == 0:
        return 1.0
    if ea.size == 0 or eb.size == 0:
        return 0.0
    matched = 0
    used = np.zeros(eb.size, dtype=bool)
    for idx in ea:
        # find nearest unused edge in eb
        diff = np.abs(eb - idx)
        j = int(np.argmin(diff))
        if not used[j] and diff[j] <= tol_edges:
            used[j] = True
            matched += 1
    denom = max(ea.size, eb.size)
    return matched / float(denom) if denom > 0 else 0.0


def xcorr_peak(sig_a: np.ndarray, sig_b: np.ndarray) -> float:
    """
    Max normalized cross-correlation peak (discrete, unbiased by mean/std).
    """
    a = sig_a.astype(np.float64)
    b = sig_b.astype(np.float64)
    a = (a - a.mean())
    b = (b - b.mean())
    sa = a.std()
    sb = b.std()
    if sa == 0 or sb == 0:
        return 0.0
    a /= sa
    b /= sb
    corr = np.correlate(a, b, mode="full")
    peak = float(np.max(corr)) / len(a)
    return peak


def period_ratio(Ti: float, Tj: float) -> float:
    if not (np.isfinite(Ti) and np.isfinite(Tj)) or Ti <= 0:
        return float("inf")
    return Tj / Ti


def phase_offset(phi_i: float, phi_j: float) -> float:
    """
    Δφ in cycles, normalized to [0,1)
    """
    d = (phi_j - phi_i) % 1.0
    return d


def ensure_out_dir() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("resonance_data") / f"second_layer_nine_test_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def save_csv(out_dir: Path, header: List[str], rows: List[List[object]]) -> None:
    path = out_dir / "nine_positions_metrics.csv"
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for r in rows:
            writer.writerow(r)


def save_heatmap(out_dir: Path, data: np.ndarray, title: str, fname: str, vmin: float = 0.0, vmax: float = 1.0) -> None:
    plt.figure(figsize=(5, 4))
    plt.imshow(data, cmap="viridis", vmin=vmin, vmax=vmax)
    plt.title(title)
    plt.xlabel("j")
    plt.ylabel("i")
    plt.xticks([0, 1, 2], ["1", "2", "3"])
    plt.yticks([0, 1, 2], ["1", "2", "3"])
    plt.colorbar(label="value")
    plt.tight_layout()
    plt.savefig(out_dir / fname, dpi=150)
    plt.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Test the 9 positions (v_ij) relationships in second layer.")
    p.add_argument("--duration", type=float, default=20.0, help="Total duration (s).")
    p.add_argument("--dt", type=float, default=0.002, help="Time step (s).")
    p.add_argument(
        "--modes",
        type=parse_triplet_list,
        default=parse_triplet_list("1.0,0.50,0.00;1.0,0.50,0.33;1.0,0.50,0.67"),
        help="Three triplets 'T,D,phi;T,D,phi;T,D,phi' with phi in cycles.",
    )
    p.add_argument("--tol-edges", type=int, default=2, help="Edge matching tolerance in samples.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    duration = args.duration
    dt = args.dt
    tol_edges = args.tol_edges
    triplets = args.modes
    modes = [ModeSpec(T=t[0], D=t[1], phi=t[2]) for t in triplets]

    # Generate signals
    sigs = [make_square_signal(m.T, m.D, m.phi, duration, dt) for m in modes]

    # Estimate per-mode primary stats
    T_est = [main_period(s, dt) for s in sigs]
    D_est = [duty_cycle(s) for s in sigs]
    phi_est = [phase_anchor(s, dt, T_est[i]) for i, s in enumerate(sigs)]

    # Prepare matrices
    S = np.zeros((3, 3), dtype=np.float64)   # skeleton match
    C = np.zeros((3, 3), dtype=np.float64)   # xcorr peak
    RT = np.zeros((3, 3), dtype=np.float64)  # period ratio
    DP = np.zeros((3, 3), dtype=np.float64)  # phase offset

    rows_csv: List[List[object]] = []
    header = [
        "i", "j",
        "T_i", "D_i", "phi_i",
        "T_j", "D_j", "phi_j",
        "rT=Tj/Ti", "Δφ(cycles)",
        "S_skeleton", "C_xcorr",
        "type",  # E or R
    ]

    for i in range(3):
        for j in range(3):
            s_i = sigs[i]
            s_j = sigs[j]
            # metrics
            s_match = skeleton_match_ratio(s_i, s_j, tol_edges=tol_edges)
            c_peak = xcorr_peak(s_i, s_j)
            rT = period_ratio(T_est[i], T_est[j])
            dphi = phase_offset(phi_est[i], phi_est[j])

            S[i, j] = s_match
            C[i, j] = c_peak
            RT[i, j] = rT
            DP[i, j] = dphi

            typ = "E" if i == j else "R"
            rows_csv.append([
                i + 1, j + 1,
                f"{T_est[i]:.6f}", f"{D_est[i]:.6f}", f"{phi_est[i]:.6f}",
                f"{T_est[j]:.6f}", f"{D_est[j]:.6f}", f"{phi_est[j]:.6f}",
                f"{rT:.6f}", f"{dphi:.6f}",
                f"{s_match:.6f}", f"{c_peak:.6f}",
                typ,
            ])

    out_dir = ensure_out_dir()
    save_csv(out_dir, header, rows_csv)
    save_heatmap(out_dir, S, "Skeleton Match (S_ij)", "skeleton_match.png", vmin=0.0, vmax=1.0)
    save_heatmap(out_dir, C, "XCorr Peak (C_ij)", "xcorr_peak.png", vmin=0.0, vmax=1.0)
    # Period ratio may exceed 1, cap colorbar reasonably
    vmax_rt = float(np.nanmax(np.clip(RT, 0.0, 2.0)))
    save_heatmap(out_dir, np.clip(RT, 0.0, 2.0), "Period Ratio (Tj/Ti)", "period_ratio.png", vmin=0.0, vmax=max(vmax_rt, 1.0))
    save_heatmap(out_dir, DP, "Phase Offset Δφ (cycles)", "phase_offset.png", vmin=0.0, vmax=1.0)

    # Print a concise summary
    print(f"Output directory: {out_dir}")
    print("Dynamic eigen positions (E): v11, v22, v33 (diagonal).")
    print("Relation positions (R): v12, v13, v21, v23, v31, v32 (off-diagonal).")
    print("CSV: nine_positions_metrics.csv")
    print("Heatmaps: skeleton_match.png, xcorr_peak.png, period_ratio.png, phase_offset.png")


if __name__ == "__main__":
    main()
