#!/usr/bin/env python3
"""
Export the 9-position color/flavor experiment into SU(3)-like components
and a time-indexed 3x3 complex Hermitian matrix sequence.

Input:
  - a quark_color_flavor_mapping_test output directory, or
  - a direct path to its summary.json

Outputs:
  - nine_position_series.csv
  - su3_components.csv
  - matrix_sequence.npz
  - conversion_summary.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np

from quark_color_flavor_mapping_test import ModeSpec, simulate_positions


POSITION_ORDER: List[Tuple[int, int, str]] = [
    (0, 0, "v11"),
    (0, 1, "v12"),
    (0, 2, "v13"),
    (1, 0, "v21"),
    (1, 1, "v22"),
    (1, 2, "v23"),
    (2, 0, "v31"),
    (2, 1, "v32"),
    (2, 2, "v33"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert v11...v33 color/flavor experiment outputs into SU(3)-style components and 3x3 complex matrices."
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to a quark_color_flavor_mapping_test output directory or its summary.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to <run_dir>/su3_matrix_export",
    )
    parser.add_argument(
        "--signal-kind",
        choices=["continuous", "binary"],
        default="continuous",
        help="Which reconstructed signal to export as v11...v33",
    )
    parser.add_argument(
        "--preview-rows",
        type=int,
        default=12,
        help="Number of first rows to include in the JSON preview payload.",
    )
    return parser.parse_args()


def resolve_paths(input_path: Path, output_dir: Path | None) -> Tuple[Path, Path]:
    if input_path.is_dir():
        run_dir = input_path
        summary_path = run_dir / "summary.json"
    else:
        summary_path = input_path
        run_dir = summary_path.parent
    if not summary_path.exists():
        raise FileNotFoundError(f"Could not find summary.json at '{summary_path}'")
    if output_dir is None:
        output_dir = run_dir / "su3_matrix_export"
    output_dir.mkdir(parents=True, exist_ok=True)
    return summary_path, output_dir


def load_summary(summary_path: Path) -> Dict[str, object]:
    with summary_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_modes_from_summary(summary: Dict[str, object]) -> List[ModeSpec]:
    base_modes = summary.get("base_modes")
    if not isinstance(base_modes, list) or len(base_modes) != 3:
        raise ValueError("summary.json must contain exactly 3 base_modes entries")
    modes: List[ModeSpec] = []
    for idx, item in enumerate(base_modes):
        if not isinstance(item, dict):
            raise ValueError(f"base_modes[{idx}] must be an object")
        modes.append(
            ModeSpec(
                label=str(item["label"]),
                period=float(item["period"]),
                duty=float(item["duty"]),
                phase=float(item["phase"]),
                amplitude=float(item["amplitude"]),
            )
        )
    return modes


def reconstruct_position_series(summary: Dict[str, object], signal_kind: str) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    config = summary.get("config")
    if not isinstance(config, dict):
        raise ValueError("summary.json is missing config")

    modes = build_modes_from_summary(summary)
    duration = float(config["duration"])
    dt = float(config["dt"])
    chirality = int(config["chirality"])
    blend = float(config["blend"])
    phase_push = float(config["phase_push"])
    duty_push = float(config["duty_push"])
    period_push = float(config["period_push"])
    amplitude_push = float(config["amplitude_push"])

    positions = simulate_positions(
        modes=modes,
        duration=duration,
        dt=dt,
        chirality=chirality,
        blend=blend,
        phase_push=phase_push,
        duty_push=duty_push,
        period_push=period_push,
        amplitude_push=amplitude_push,
    )
    n = len(positions[(0, 0)][signal_kind])
    t = np.arange(n, dtype=np.float64) * dt
    series: Dict[str, np.ndarray] = {}
    for i, j, name in POSITION_ORDER:
        series[name] = positions[(i, j)][signal_kind].astype(np.float64)
    return t, series


def build_su3_components(series: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    v11 = series["v11"]
    v12 = series["v12"]
    v13 = series["v13"]
    v21 = series["v21"]
    v22 = series["v22"]
    v23 = series["v23"]
    v31 = series["v31"]
    v32 = series["v32"]
    v33 = series["v33"]

    sqrt3 = math.sqrt(3.0)
    s = (v11 + v22 + v33) / sqrt3
    p12 = v11 - v22
    p_123 = (v11 + v22 - 2.0 * v33) / sqrt3

    b12 = 0.5 * (v12 + v21)
    f12 = 0.5 * (v21 - v12)
    b13 = 0.5 * (v13 + v31)
    f13 = 0.5 * (v31 - v13)
    b23 = 0.5 * (v23 + v32)
    f23 = 0.5 * (v32 - v23)

    return {
        "S": s,
        "B12": b12,
        "F12": f12,
        "P12": p12,
        "B13": b13,
        "F13": f13,
        "B23": b23,
        "F23": f23,
        "P_12_3": p_123,
        "a1": b12,
        "a2": f12,
        "a3": p12,
        "a4": b13,
        "a5": f13,
        "a6": b23,
        "a7": f23,
        "a8": p_123,
    }


def build_matrix_sequence(series: Dict[str, np.ndarray], components: Dict[str, np.ndarray]) -> np.ndarray:
    n = len(series["v11"])
    matrices = np.zeros((n, 3, 3), dtype=np.complex128)
    matrices[:, 0, 0] = series["v11"]
    matrices[:, 1, 1] = series["v22"]
    matrices[:, 2, 2] = series["v33"]
    matrices[:, 0, 1] = components["B12"] - 1j * components["F12"]
    matrices[:, 1, 0] = components["B12"] + 1j * components["F12"]
    matrices[:, 0, 2] = components["B13"] - 1j * components["F13"]
    matrices[:, 2, 0] = components["B13"] + 1j * components["F13"]
    matrices[:, 1, 2] = components["B23"] - 1j * components["F23"]
    matrices[:, 2, 1] = components["B23"] + 1j * components["F23"]
    return matrices


def save_series_csv(path: Path, t: np.ndarray, columns: Iterable[str], values: Dict[str, np.ndarray]) -> None:
    names = list(columns)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["t", *names])
        for idx, t_value in enumerate(t):
            row = [f"{t_value:.9f}"]
            row.extend(f"{float(values[name][idx]):.9f}" for name in names)
            writer.writerow(row)


def make_preview(
    t: np.ndarray,
    series: Dict[str, np.ndarray],
    components: Dict[str, np.ndarray],
    matrices: np.ndarray,
    preview_rows: int,
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    count = min(preview_rows, len(t))
    for idx in range(count):
        rows.append(
            {
                "t": float(t[idx]),
                "v11": float(series["v11"][idx]),
                "v12": float(series["v12"][idx]),
                "v21": float(series["v21"][idx]),
                "v22": float(series["v22"][idx]),
                "v33": float(series["v33"][idx]),
                "S": float(components["S"][idx]),
                "B12": float(components["B12"][idx]),
                "F12": float(components["F12"][idx]),
                "P12": float(components["P12"][idx]),
                "matrix_real": matrices[idx].real.round(9).tolist(),
                "matrix_imag": matrices[idx].imag.round(9).tolist(),
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    summary_path, output_dir = resolve_paths(args.input_path, args.output_dir)
    summary = load_summary(summary_path)
    t, series = reconstruct_position_series(summary, args.signal_kind)
    components = build_su3_components(series)
    matrices = build_matrix_sequence(series, components)

    save_series_csv(
        output_dir / "nine_position_series.csv",
        t,
        [name for _, _, name in POSITION_ORDER],
        series,
    )
    save_series_csv(
        output_dir / "su3_components.csv",
        t,
        ["S", "B12", "F12", "P12", "B13", "F13", "B23", "F23", "P_12_3", "a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8"],
        components,
    )
    np.savez_compressed(
        output_dir / "matrix_sequence.npz",
        t=t,
        matrix_real=matrices.real,
        matrix_imag=matrices.imag,
        **{name: values for name, values in series.items()},
        **{name: values for name, values in components.items()},
    )

    hermitian_error = float(np.max(np.abs(matrices - np.conjugate(np.swapaxes(matrices, 1, 2)))))
    conversion_summary = {
        "source_summary": str(summary_path),
        "signal_kind": args.signal_kind,
        "sample_count": int(len(t)),
        "dt": float(t[1] - t[0]) if len(t) > 1 else 0.0,
        "component_mapping": {
            "S": "(v11 + v22 + v33) / sqrt(3)",
            "B12": "(v12 + v21) / 2",
            "F12": "(v21 - v12) / 2",
            "P12": "v11 - v22",
            "B13": "(v13 + v31) / 2",
            "F13": "(v31 - v13) / 2",
            "B23": "(v23 + v32) / 2",
            "F23": "(v32 - v23) / 2",
            "P_12_3": "(v11 + v22 - 2*v33) / sqrt(3)",
        },
        "matrix_definition": [
            ["v11", "B12 - i*F12", "B13 - i*F13"],
            ["B12 + i*F12", "v22", "B23 - i*F23"],
            ["B13 + i*F13", "B23 + i*F23", "v33"],
        ],
        "hermitian_max_abs_error": hermitian_error,
        "preview_rows": make_preview(t, series, components, matrices, args.preview_rows),
    }
    with (output_dir / "conversion_summary.json").open("w", encoding="utf-8") as f:
        json.dump(conversion_summary, f, indent=2)

    print(f"Source summary: {summary_path}")
    print(f"Signal kind: {args.signal_kind}")
    print(f"Output directory: {output_dir}")
    print(f"Sample count: {len(t)}")
    print(f"Hermitian max abs error: {hermitian_error:.3e}")


if __name__ == "__main__":
    main()
