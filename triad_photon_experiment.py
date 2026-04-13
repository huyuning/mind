#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
triad_photon_experiment.py

Minimal "photon-like triad" experiment:
- A single triad of 3 binary channels encodes a photon-like closed rotating kernel.
- The user specifies a center cycle/duty/phase, a target spin axis, and a chirality.
- The script derives per-channel (T, D, phi, A), generates three 0-1 sequences,
  lifts each 0-1 active window into a continuous sin^2 pulse, builds a 3D spin
  trajectory through a basis transform, and outputs summary metrics.

Outputs:
- resonance_data/triad_photon_experiment_YYYYMMDD_HHMMSS/
  - summary.json
  - mode_table.csv
  - sphere_trajectory.csv
  - bit_sequences.png
  - spin_components.png
  - spin_trajectory_3d.png
  - spin_trajectory_3d.html
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


@dataclass
class ModeSpec:
    label: str
    period: float
    duty: float
    phase: float
    amplitude: float
    projection: float


def parse_axis(values: Sequence[str]) -> np.ndarray:
    if len(values) != 3:
        raise argparse.ArgumentTypeError("spin axis requires 3 values: x y z")
    axis = np.array([float(v) for v in values], dtype=np.float64)
    norm = float(np.linalg.norm(axis))
    if norm == 0.0:
        raise argparse.ArgumentTypeError("spin axis must be non-zero")
    return axis / norm


def make_square_signal(period: float, duty: float, phase: float, duration: float, dt: float) -> np.ndarray:
    n = int(math.ceil(duration / dt))
    t = np.arange(n, dtype=np.float64) * dt
    t0 = (phase % 1.0) * period
    # Positive phase means a delayed activation inside the cycle.
    return ((((t - t0) % period) < (duty * period)).astype(np.int8))


def make_continuous_sin_signal(period: float, duty: float, phase: float, duration: float, dt: float) -> np.ndarray:
    """
    Convert each binary "on" window into a continuous raised-cosine pulse.
    The 0-1 structure remains the timing skeleton, while the value evolves continuously.
    """
    n = int(math.ceil(duration / dt))
    t = np.arange(n, dtype=np.float64) * dt
    t0 = (phase % 1.0) * period
    cycle_pos = ((t - t0) % period) / period
    values = np.zeros(n, dtype=np.float64)
    active = cycle_pos < duty
    if np.any(active):
        local = cycle_pos[active] / duty
        # Raised-cosine: 0.5 * (1 - cos(2*pi*local)), equivalent to sin^2(pi*local)
        values[active] = 0.5 * (1.0 - np.cos(2.0 * np.pi * local))
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


def phase_anchor(signal: np.ndarray, dt: float, period: float) -> float:
    s = signal.astype(np.int8)
    rising = np.nonzero((s[1:] == 1) & (s[:-1] == 0))[0] + 1
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
    if sa == 0 or sb == 0:
        return 0.0
    corr = np.correlate(a / sa, b / sb, mode="full")
    return float(np.max(corr)) / len(a)


def build_encoding_basis() -> np.ndarray:
    """
    Three symmetric encoding axes. Columns correspond to the three 0-1 channels.
    Their average points to +z, while asymmetric modulation tilts the decoded direction.
    """
    u1 = np.array([1.0, 0.0, 1.0], dtype=np.float64)
    u2 = np.array([-0.5, math.sqrt(3.0) / 2.0, 1.0], dtype=np.float64)
    u3 = np.array([-0.5, -math.sqrt(3.0) / 2.0, 1.0], dtype=np.float64)
    basis = np.stack([u1, u2, u3], axis=1)
    basis /= np.linalg.norm(basis, axis=0, keepdims=True)
    return basis


def derive_mode_specs(
    center_period: float,
    center_duty: float,
    center_phase: float,
    center_amplitude: float,
    spin_axis: np.ndarray,
    chirality: int,
    period_scale: float,
    duty_scale: float,
    phase_scale: float,
    amplitude_scale: float,
) -> Tuple[List[ModeSpec], np.ndarray]:
    basis = build_encoding_basis()
    projections = basis.T @ spin_axis
    max_abs = float(np.max(np.abs(projections)))
    if max_abs > 1.0:
        projections = projections / max_abs

    if chirality >= 0:
        base_phases = np.array([0.0, 1.0 / 3.0, 2.0 / 3.0], dtype=np.float64)
    else:
        base_phases = np.array([0.0, 2.0 / 3.0, 1.0 / 3.0], dtype=np.float64)

    labels = ["p1", "p2", "p3"]
    specs: List[ModeSpec] = []
    for idx, proj in enumerate(projections):
        period = center_period * max(0.05, 1.0 + period_scale * proj)
        duty = float(np.clip(center_duty + duty_scale * proj, 0.05, 0.95))
        phase = float((center_phase + base_phases[idx] + phase_scale * proj) % 1.0)
        amplitude = center_amplitude * max(0.05, 1.0 + amplitude_scale * proj)
        specs.append(
            ModeSpec(
                label=labels[idx],
                period=period,
                duty=duty,
                phase=phase,
                amplitude=amplitude,
                projection=float(proj),
            )
        )
    return specs, basis


def decode_spin_trajectory(
    signals: np.ndarray,
    amplitudes: np.ndarray,
    basis: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    weighted = signals.astype(np.float64) * amplitudes[:, None]
    raw = basis @ weighted
    norms = np.linalg.norm(raw, axis=0)
    safe_norms = np.where(norms > 1e-12, norms, 1.0)
    unit = raw / safe_norms[None, :]
    return raw, unit


def rotation_consistency(signals: np.ndarray, chirality: int) -> float:
    expected = [0, 1, 2] if chirality >= 0 else [0, 2, 1]
    expected_next = {expected[i]: expected[(i + 1) % 3] for i in range(3)}
    events: List[Tuple[int, int]] = []
    for channel in range(3):
        sig = signals[channel]
        rising = np.nonzero((sig[1:] == 1) & (sig[:-1] == 0))[0] + 1
        for idx in rising.tolist():
            events.append((idx, channel))
    if len(events) < 2:
        return 0.0
    events.sort()
    matches = 0
    total = 0
    for (_, c_now), (_, c_next) in zip(events[:-1], events[1:]):
        if c_now == c_next:
            continue
        total += 1
        if expected_next[c_now] == c_next:
            matches += 1
    return matches / total if total > 0 else 0.0


def ensure_out_dir() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("resonance_data") / f"triad_photon_experiment_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def save_mode_table(out_dir: Path, specs: Sequence[ModeSpec]) -> None:
    with (out_dir / "mode_table.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "period", "frequency", "duty", "phase", "amplitude", "projection"])
        for spec in specs:
            writer.writerow([
                spec.label,
                f"{spec.period:.6f}",
                f"{1.0 / spec.period:.6f}",
                f"{spec.duty:.6f}",
                f"{spec.phase:.6f}",
                f"{spec.amplitude:.6f}",
                f"{spec.projection:.6f}",
            ])


def save_trajectory_csv(out_dir: Path, time: np.ndarray, spin_raw: np.ndarray, spin_unit: np.ndarray) -> None:
    with (out_dir / "sphere_trajectory.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["t", "raw_x", "raw_y", "raw_z", "unit_x", "unit_y", "unit_z"])
        for idx, t in enumerate(time):
            writer.writerow([
                f"{t:.6f}",
                f"{spin_raw[0, idx]:.6f}",
                f"{spin_raw[1, idx]:.6f}",
                f"{spin_raw[2, idx]:.6f}",
                f"{spin_unit[0, idx]:.6f}",
                f"{spin_unit[1, idx]:.6f}",
                f"{spin_unit[2, idx]:.6f}",
            ])


def plot_bit_sequences(
    out_dir: Path,
    time: np.ndarray,
    binary_signals: np.ndarray,
    continuous_signals: np.ndarray,
) -> None:
    plt.figure(figsize=(10, 4.5))
    for idx in range(3):
        offset = 1.35 * idx
        plt.plot(time, continuous_signals[idx] + offset, linewidth=1.5, label=f"p{idx + 1} cont")
        plt.step(
            time,
            0.18 * binary_signals[idx] + offset - 0.22,
            where="post",
            linewidth=1.0,
            alpha=0.75,
            label=f"p{idx + 1} bin",
        )
    plt.xlabel("time")
    plt.ylabel("channel level")
    plt.title("Photon Triad Binary Skeleton + Continuous Sin Pulses")
    plt.yticks([0.0, 1.35, 2.70], ["p1", "p2", "p3"])
    plt.legend(loc="upper right", ncol=2, fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "bit_sequences.png", dpi=150)
    plt.close()


def plot_spin_components(out_dir: Path, time: np.ndarray, spin_unit: np.ndarray) -> None:
    plt.figure(figsize=(10, 4.5))
    plt.plot(time, spin_unit[0], label="Sx")
    plt.plot(time, spin_unit[1], label="Sy")
    plt.plot(time, spin_unit[2], label="Sz")
    plt.xlabel("time")
    plt.ylabel("unit spin component")
    plt.title("Decoded Spin Components")
    plt.ylim(-1.05, 1.05)
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(out_dir / "spin_components.png", dpi=150)
    plt.close()


def plot_spin_trajectory_3d(out_dir: Path, spin_unit: np.ndarray, spin_axis: np.ndarray) -> None:
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(spin_unit[0], spin_unit[1], spin_unit[2], linewidth=1.0, alpha=0.9)
    ax.quiver(
        0.0, 0.0, 0.0,
        float(spin_axis[0]), float(spin_axis[1]), float(spin_axis[2]),
        color="red", linewidth=2.0, arrow_length_ratio=0.12
    )
    ax.set_xlim(-1.0, 1.0)
    ax.set_ylim(-1.0, 1.0)
    ax.set_zlim(-1.0, 1.0)
    ax.set_xlabel("Sx")
    ax.set_ylabel("Sy")
    ax.set_zlabel("Sz")
    ax.set_title("Decoded Photon-Spin Trajectory")
    plt.tight_layout()
    plt.savefig(out_dir / "spin_trajectory_3d.png", dpi=150)
    plt.close()


def save_spin_trajectory_3d_html(out_dir: Path, spin_unit: np.ndarray, spin_axis: np.ndarray) -> None:
    x = spin_unit[0].tolist()
    y = spin_unit[1].tolist()
    z = spin_unit[2].tolist()
    axis = spin_axis.tolist()
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Photon Spin Trajectory 3D</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    body {{
      margin: 0;
      background: #0f1220;
      color: #e8ecf3;
      font-family: Arial, sans-serif;
    }}
    #plot {{
      width: 100vw;
      height: 100vh;
    }}
    .info {{
      position: absolute;
      top: 12px;
      left: 12px;
      z-index: 2;
      background: rgba(15, 18, 32, 0.78);
      padding: 10px 12px;
      border-radius: 8px;
      line-height: 1.4;
    }}
  </style>
</head>
<body>
  <div class="info">
    <div><strong>Photon Triad Spin Trajectory</strong></div>
    <div>Drag to rotate, scroll to zoom.</div>
    <div>Red arrow = target axis</div>
  </div>
  <div id="plot"></div>
  <script>
    const trace = {{
      type: "scatter3d",
      mode: "lines",
      x: {json.dumps(x)},
      y: {json.dumps(y)},
      z: {json.dumps(z)},
      line: {{
        color: "#5bc0ff",
        width: 5
      }},
      name: "spin trajectory"
    }};

    const axisTrace = {{
      type: "scatter3d",
      mode: "lines",
      x: [0, {axis[0]}],
      y: [0, {axis[1]}],
      z: [0, {axis[2]}],
      line: {{
        color: "#ff6b6b",
        width: 8
      }},
      name: "target axis"
    }};

    const axisTip = {{
      type: "scatter3d",
      mode: "markers",
      x: [{axis[0]}],
      y: [{axis[1]}],
      z: [{axis[2]}],
      marker: {{
        color: "#ff6b6b",
        size: 5
      }},
      name: "axis tip"
    }};

    const layout = {{
      paper_bgcolor: "#0f1220",
      plot_bgcolor: "#0f1220",
      margin: {{ l: 0, r: 0, t: 0, b: 0 }},
      showlegend: true,
      legend: {{
        bgcolor: "rgba(15, 18, 32, 0.7)",
        font: {{ color: "#e8ecf3" }}
      }},
      scene: {{
        xaxis: {{
          title: "Sx",
          range: [-1, 1],
          backgroundcolor: "#14192c",
          gridcolor: "rgba(255,255,255,0.15)",
          zerolinecolor: "rgba(255,255,255,0.25)",
          color: "#e8ecf3"
        }},
        yaxis: {{
          title: "Sy",
          range: [-1, 1],
          backgroundcolor: "#14192c",
          gridcolor: "rgba(255,255,255,0.15)",
          zerolinecolor: "rgba(255,255,255,0.25)",
          color: "#e8ecf3"
        }},
        zaxis: {{
          title: "Sz",
          range: [-1, 1],
          backgroundcolor: "#14192c",
          gridcolor: "rgba(255,255,255,0.15)",
          zerolinecolor: "rgba(255,255,255,0.25)",
          color: "#e8ecf3"
        }},
        aspectmode: "cube",
        camera: {{
          eye: {{ x: 1.35, y: 1.35, z: 1.1 }}
        }}
      }}
    }};

    Plotly.newPlot("plot", [trace, axisTrace, axisTip], layout, {{
      responsive: true,
      displaylogo: false
    }});
  </script>
</body>
</html>
"""
    (out_dir / "spin_trajectory_3d.html").write_text(html)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a minimal photon-like triad experiment.")
    parser.add_argument("--duration", type=float, default=12.0, help="Total duration.")
    parser.add_argument("--dt", type=float, default=0.002, help="Time step.")
    parser.add_argument("--center-period", type=float, default=1.0, help="Center cycle period.")
    parser.add_argument("--center-duty", type=float, default=1.0 / 3.0, help="Center duty cycle in (0,1).")
    parser.add_argument("--center-phase", type=float, default=0.0, help="Center phase in cycles.")
    parser.add_argument("--center-amplitude", type=float, default=1.0, help="Center amplitude.")
    parser.add_argument("--spin-axis", nargs=3, default=["0", "0", "1"], help="Target spin axis x y z.")
    parser.add_argument("--chirality", type=int, choices=[-1, 1], default=1, help="Rotation chirality.")
    parser.add_argument("--period-scale", type=float, default=0.08, help="Axis-induced period tilt scale.")
    parser.add_argument("--duty-scale", type=float, default=0.08, help="Axis-induced duty tilt scale.")
    parser.add_argument("--phase-scale", type=float, default=0.08, help="Axis-induced phase tilt scale.")
    parser.add_argument("--amplitude-scale", type=float, default=0.25, help="Axis-induced amplitude tilt scale.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spin_axis = parse_axis(args.spin_axis)
    specs, basis = derive_mode_specs(
        center_period=args.center_period,
        center_duty=args.center_duty,
        center_phase=args.center_phase,
        center_amplitude=args.center_amplitude,
        spin_axis=spin_axis,
        chirality=args.chirality,
        period_scale=args.period_scale,
        duty_scale=args.duty_scale,
        phase_scale=args.phase_scale,
        amplitude_scale=args.amplitude_scale,
    )

    time = np.arange(int(math.ceil(args.duration / args.dt)), dtype=np.float64) * args.dt
    binary_signals = np.stack(
        [make_square_signal(spec.period, spec.duty, spec.phase, args.duration, args.dt) for spec in specs],
        axis=0,
    )
    continuous_signals = np.stack(
        [make_continuous_sin_signal(spec.period, spec.duty, spec.phase, args.duration, args.dt) for spec in specs],
        axis=0,
    )
    amplitudes = np.array([spec.amplitude for spec in specs], dtype=np.float64)
    spin_raw, spin_unit = decode_spin_trajectory(continuous_signals, amplitudes, basis)

    estimated_periods = [dominant_period(continuous_signals[i], args.dt) for i in range(3)]
    estimated_phases = [phase_anchor(binary_signals[i], args.dt, specs[i].period) for i in range(3)]
    pair_xcorr = {
        "p12": xcorr_peak(continuous_signals[0], continuous_signals[1]),
        "p13": xcorr_peak(continuous_signals[0], continuous_signals[2]),
        "p23": xcorr_peak(continuous_signals[1], continuous_signals[2]),
    }

    mean_spin = np.mean(spin_unit, axis=1)
    mean_spin_norm = float(np.linalg.norm(mean_spin))
    mean_spin_dir = mean_spin / mean_spin_norm if mean_spin_norm > 1e-12 else mean_spin
    axis_alignment = float(np.dot(mean_spin_dir, spin_axis)) if mean_spin_norm > 1e-12 else 0.0
    rotation_score = rotation_consistency(binary_signals, args.chirality)

    out_dir = ensure_out_dir()
    save_mode_table(out_dir, specs)
    save_trajectory_csv(out_dir, time, spin_raw, spin_unit)
    plot_bit_sequences(out_dir, time, binary_signals, continuous_signals)
    plot_spin_components(out_dir, time, spin_unit)
    plot_spin_trajectory_3d(out_dir, spin_unit, spin_axis)
    save_spin_trajectory_3d_html(out_dir, spin_unit, spin_axis)

    summary = {
        "config": {
            "duration": args.duration,
            "dt": args.dt,
            "center_period": args.center_period,
            "center_duty": args.center_duty,
            "center_phase": args.center_phase,
            "center_amplitude": args.center_amplitude,
            "spin_axis": spin_axis.tolist(),
            "chirality": args.chirality,
            "period_scale": args.period_scale,
            "duty_scale": args.duty_scale,
            "phase_scale": args.phase_scale,
            "amplitude_scale": args.amplitude_scale,
        },
        "modes": [asdict(spec) for spec in specs],
        "estimated": {
            "periods": estimated_periods,
            "frequencies": [0.0 if not np.isfinite(p) or p <= 0 else 1.0 / p for p in estimated_periods],
            "phases": estimated_phases,
            "binary_duties": [float(binary_signals[i].mean()) for i in range(3)],
            "continuous_means": [float(continuous_signals[i].mean()) for i in range(3)],
        },
        "pair_xcorr": pair_xcorr,
        "spin_metrics": {
            "mean_spin_vector": mean_spin.tolist(),
            "mean_spin_direction": mean_spin_dir.tolist(),
            "mean_spin_norm": mean_spin_norm,
            "axis_alignment": axis_alignment,
            "rotation_consistency": rotation_score,
            "mean_sz": float(np.mean(spin_unit[2])),
        },
        "interpretation": {
            "status": (
                "aligned" if axis_alignment >= 0.75 else
                "partially_aligned" if axis_alignment >= 0.35 else
                "weak_alignment"
            ),
            "chirality_status": (
                "stable_rotation" if rotation_score >= 0.66 else
                "partial_rotation" if rotation_score >= 0.33 else
                "weak_rotation"
            ),
        },
    }
    with (out_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"Output directory: {out_dir}")
    print(f"Target spin axis: {spin_axis.tolist()}")
    print(f"Axis alignment: {axis_alignment:.6f}")
    print(f"Rotation consistency: {rotation_score:.6f}")
    print("Files: summary.json, mode_table.csv, sphere_trajectory.csv, bit_sequences.png, spin_components.png, spin_trajectory_3d.png, spin_trajectory_3d.html")


if __name__ == "__main__":
    main()
