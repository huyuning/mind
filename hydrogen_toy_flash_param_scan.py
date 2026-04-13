#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from hydrogen_toy_flash_analysis import analyze as analyze_once


@dataclass
class ScanConfig:
    duration: float = 12.0
    dt: float = 0.04
    target_frames: int = 60
    include_electron: bool = False
    distance_threshold: float = 1.45
    phase_threshold: float = 0.95
    wave_cell_multiplier: int = 1
    proton_radius: float = 1.2
    electron_radius: float = 5.2
    electron_frequency: float = 0.11


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parameter scan for hydrogen toy flash cells")
    parser.add_argument("--outdir", type=str, default=None, help="output directory for scan results")
    parser.add_argument("--quick", action="store_true", help="use a quicker, coarser grid")
    parser.add_argument("--phase-start", type=float, default=None, help="optional phase-threshold scan start")
    parser.add_argument("--phase-end", type=float, default=None, help="optional phase-threshold scan end")
    parser.add_argument("--phase-step", type=float, default=None, help="optional phase-threshold scan step")
    parser.add_argument("--fixed-include-electron", type=str, choices=["true", "false"], default=None, help="fix include_electron instead of scanning it")
    parser.add_argument("--fixed-distance-threshold", type=float, default=None, help="fix distance_threshold instead of scanning it")
    parser.add_argument("--fixed-wave-cell-multiplier", type=int, default=None, help="fix wave_cell_multiplier instead of scanning it")
    parser.add_argument("--fixed-proton-radius", type=float, default=None, help="fix proton_radius instead of scanning it")
    parser.add_argument("--fixed-electron-radius", type=float, default=None, help="fix electron_radius instead of scanning it")
    return parser.parse_args()


def phase_range(start: float, end: float, step: float) -> List[float]:
    values: List[float] = []
    current = start
    # inclusive scan with rounding protection
    while current <= end + 1e-9:
        values.append(round(current, 10))
        current += step
    if values and abs(values[-1] - end) > 1e-9:
        values.append(round(end, 10))
    return values


def grid_values(quick: bool, args: argparse.Namespace) -> Dict[str, List[Any]]:
    if quick:
        values = {
            "include_electron": [False, True],
            "distance_threshold": [1.30, 1.45, 1.60],
            "phase_threshold": [0.70, 0.95, 1.10],
            "wave_cell_multiplier": [1, 2],
            "proton_radius": [1.0, 1.2],
            "electron_radius": [5.0, 5.4],
        }
    else:
        values = {
            "include_electron": [False, True],
            "distance_threshold": [1.25, 1.35, 1.45, 1.55, 1.70],
            "phase_threshold": [0.60, 0.80, 0.95, 1.05, 1.20],
            "wave_cell_multiplier": [1, 2],
            "proton_radius": [1.0, 1.2, 1.4],
            "electron_radius": [4.8, 5.2, 5.6],
        }

    if args.phase_start is not None and args.phase_end is not None and args.phase_step is not None:
        values["phase_threshold"] = phase_range(args.phase_start, args.phase_end, args.phase_step)
    if args.fixed_include_electron is not None:
        values["include_electron"] = [args.fixed_include_electron == "true"]
    if args.fixed_distance_threshold is not None:
        values["distance_threshold"] = [args.fixed_distance_threshold]
    if args.fixed_wave_cell_multiplier is not None:
        values["wave_cell_multiplier"] = [args.fixed_wave_cell_multiplier]
    if args.fixed_proton_radius is not None:
        values["proton_radius"] = [args.fixed_proton_radius]
    if args.fixed_electron_radius is not None:
        values["electron_radius"] = [args.fixed_electron_radius]
    return values


def run_one(cfg: ScanConfig) -> Dict[str, Any]:
    args = argparse.Namespace(
        duration=cfg.duration,
        dt=cfg.dt,
        target_frames=cfg.target_frames,
        include_electron=cfg.include_electron,
        distance_threshold=cfg.distance_threshold,
        phase_threshold=cfg.phase_threshold,
        wave_cell_multiplier=cfg.wave_cell_multiplier,
        proton_radius=cfg.proton_radius,
        electron_radius=cfg.electron_radius,
        electron_frequency=cfg.electron_frequency,
    )
    payload, out_dir = analyze_once(args)
    row = {
        **asdict(cfg),
        "flash_detected": bool(payload.get("flash_detected", False)),
        "focus_pair": payload.get("focus_pair"),
        "focus_jump_abs": int(payload.get("focus_jump_abs", 0)),
        "run_dir": str(out_dir),
    }
    return row


def main() -> None:
    args = parse_args()
    values = grid_values(args.quick, args)
    # output directory
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = Path(args.outdir) if args.outdir else Path("resonance_data") / f"hydrogen_toy_flash_param_scan_{ts}"
    root.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []

    for include_electron in values["include_electron"]:
        for wave_cell_multiplier in values["wave_cell_multiplier"]:
            for distance_threshold in values["distance_threshold"]:
                for phase_threshold in values["phase_threshold"]:
                    for proton_radius in values["proton_radius"]:
                        for electron_radius in values["electron_radius"]:
                            cfg = ScanConfig(
                                include_electron=include_electron,
                                wave_cell_multiplier=wave_cell_multiplier,
                                distance_threshold=distance_threshold,
                                phase_threshold=phase_threshold,
                                proton_radius=proton_radius,
                                electron_radius=electron_radius,
                            )
                            row = run_one(cfg)
                            rows.append(row)
                            print(
                                f"[scan] inc_elec={include_electron} mul={wave_cell_multiplier} "
                                f"dist={distance_threshold:.2f} phase={phase_threshold:.2f} "
                                f"pR={proton_radius:.2f} eR={electron_radius:.2f} -> flash={row['flash_detected']} "
                                f"jump={row['focus_jump_abs']} pair={row['focus_pair']}"
                            )

    # save CSV
    csv_path = root / "scan_results.csv"
    fieldnames = list(rows[0].keys()) if rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # quick report
    total = len(rows)
    positive = sum(1 for r in rows if r["flash_detected"])
    by_pair: Dict[str, int] = {}
    for r in rows:
        if r["flash_detected"]:
            by_pair[r["focus_pair"]] = by_pair.get(r["focus_pair"], 0) + 1
    report = {
        "total": total,
        "positive": positive,
        "positive_rate": (positive / total) if total else 0.0,
        "by_focus_pair": by_pair,
        "scan_values": values,
    }
    (root / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Scan outdir: {root}")
    print(f"Total combos: {total}, flash positives: {positive}")
    print(f"By focus pair: {by_pair}")


if __name__ == "__main__":
    main()
