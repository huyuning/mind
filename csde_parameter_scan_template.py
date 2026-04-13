#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import itertools
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Sequence

import hydrogen_coaxial_axis_emergence as axis_emergence
from csde_quantum_validation import wrap_runner_with_quantum_post_validation


Runner = Callable[[SimpleNamespace], tuple[Path, Dict[str, Any]]]


@dataclass(frozen=True)
class ScanAxis:
    name: str
    values: Sequence[Any]


@dataclass(frozen=True)
class ScanMetric:
    name: str
    objective: str  # "max" | "min"


def parse_float_list(text: str) -> List[float]:
    return [float(item.strip()) for item in text.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CSDE experiment orchestration parameter-scan template")
    parser.add_argument("--duration", type=float, default=14.0, help="simulation duration for each case")
    parser.add_argument("--dt", type=float, default=0.04, help="simulation timestep for each case")
    parser.add_argument("--proton-radius", type=float, default=1.2, help="base proton-core scale for each case")
    parser.add_argument("--phase-thresholds", type=parse_float_list, default=[0.96, 1.02, 1.08], help="comma-separated phase-threshold scan values")
    parser.add_argument("--pair-distance-factors", type=parse_float_list, default=[1.8, 2.05, 2.3], help="comma-separated pair-distance-factor scan values")
    parser.add_argument("--coaxial-angle-thresholds", type=parse_float_list, default=[0.20, 0.26, 0.32], help="comma-separated coaxial-angle-threshold scan values")
    parser.add_argument("--merge-center-thresholds", type=parse_float_list, default=[0.6, 0.82], help="comma-separated merge-center-threshold scan values")
    parser.add_argument("--top-k", type=int, default=8, help="number of best cases to keep in summary")
    parser.add_argument("--sort-metric", type=str, default="latest_mass_total_proxy", help="summary metric used for top-k ranking")
    parser.add_argument("--sort-objective", choices=["max", "min"], default="max", help="whether the sort metric should be maximized or minimized")
    return parser.parse_args()


def create_output_dir() -> Path:
    root = Path("resonance_data")
    root.mkdir(parents=True, exist_ok=True)
    out_dir = root / f"csde_parameter_scan_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def build_default_axes(args: argparse.Namespace) -> List[ScanAxis]:
    return [
        ScanAxis("phase_threshold", list(args.phase_thresholds)),
        ScanAxis("pair_distance_factor", list(args.pair_distance_factors)),
        ScanAxis("coaxial_angle_threshold", list(args.coaxial_angle_thresholds)),
        ScanAxis("merge_center_threshold", list(args.merge_center_thresholds)),
    ]


def base_namespace(args: argparse.Namespace) -> SimpleNamespace:
    # This default runner targets hydrogen_coaxial_axis_emergence.py.
    # Replace or extend these fields when adapting the template to another CSDE experiment module.
    return SimpleNamespace(
        duration=args.duration,
        dt=args.dt,
        stream_write=True,
        stream_every=1,
        proton_radius=args.proton_radius,
        phase_threshold=1.08,
        pair_distance_factor=2.05,
        merge_angle_threshold=0.38,
        merge_center_threshold=0.82,
        coaxial_angle_threshold=0.26,
        coaxial_phase_threshold=0.78,
        coaxial_center_threshold=1.15,
        decay_time=1.4,
        reinforce_gain=0.34,
        retire_threshold=0.12,
        max_level=3,
        axis_line_scale=0.9,
    )


def apply_case(base_args: SimpleNamespace, case_values: Dict[str, Any]) -> SimpleNamespace:
    payload = dict(vars(base_args))
    payload.update(case_values)
    return SimpleNamespace(**payload)


def default_runner(case_args: SimpleNamespace) -> tuple[Path, Dict[str, Any]]:
    wrapped_runner = wrap_runner_with_quantum_post_validation(axis_emergence.run)
    return wrapped_runner(case_args)


def summarize_case(case_id: int, case_values: Dict[str, Any], out_dir: Path, summary: Dict[str, Any]) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "case_id": case_id,
        "run_dir": str(out_dir),
        **case_values,
        "axis_node_count_total": int(summary.get("axis_node_count_total", 0)),
        "axis_node_count_active": int(summary.get("axis_node_count_active", 0)),
        "max_level": int(summary.get("max_level", 0)),
        "latest_mass_total_proxy": float(summary.get("latest_mass_total_proxy", 0.0)),
        "latest_mass_parallel_proxy": float(summary.get("latest_mass_parallel_proxy", 0.0)),
        "latest_absorbed_axis_proxy": float(summary.get("latest_absorbed_axis_proxy", 0.0)),
        "dominant_frequency_std": float(summary.get("dominant_frequency_std", 0.0)),
        "resonance_frequency_stability_score": float(summary.get("resonance_frequency_stability_score", 0.0)),
    }
    row["coaxial_depth_score"] = float(row["axis_node_count_active"]) * (1.0 + 0.25 * float(row["max_level"]))
    return row


def product_cases(axes: Sequence[ScanAxis]) -> Iterable[Dict[str, Any]]:
    names = [axis.name for axis in axes]
    value_lists = [axis.values for axis in axes]
    for combo in itertools.product(*value_lists):
        yield dict(zip(names, combo, strict=False))


def sort_rows(rows: List[Dict[str, Any]], metric: str, objective: str) -> List[Dict[str, Any]]:
    reverse = objective == "max"
    return sorted(rows, key=lambda item: float(item.get(metric, 0.0)), reverse=reverse)


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_scan(args: argparse.Namespace, runner: Runner = default_runner) -> Path:
    output_dir = create_output_dir()
    axes = build_default_axes(args)
    base_args = base_namespace(args)
    rows: List[Dict[str, Any]] = []

    for case_id, case_values in enumerate(product_cases(axes), start=1):
        case_args = apply_case(base_args, case_values)
        run_dir, summary = runner(case_args)
        rows.append(summarize_case(case_id=case_id, case_values=case_values, out_dir=run_dir, summary=summary))

    ordered = sort_rows(rows, metric=args.sort_metric, objective=args.sort_objective)
    summary = {
        "engine_name": "CSDE",
        "template_name": "csde_parameter_scan_template",
        "case_count": len(rows),
        "scan_axes": {axis.name: list(axis.values) for axis in axes},
        "sort_metric": args.sort_metric,
        "sort_objective": args.sort_objective,
        "top_k": args.top_k,
        "best_cases": ordered[: args.top_k],
    }

    write_csv(output_dir / "scan_results.csv", ordered)
    write_json(output_dir / "summary.json", summary)
    return output_dir


def main() -> None:
    args = parse_args()
    output_dir = run_scan(args)
    print(f"Run directory: {output_dir}")
    print(f"Summary: {output_dir / 'summary.json'}")
    print(f"CSV: {output_dir / 'scan_results.csv'}")


if __name__ == "__main__":
    main()
