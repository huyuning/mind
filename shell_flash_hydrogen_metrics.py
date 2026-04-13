#!/usr/bin/env python3
"""
把壳层动画中的“闪现胞元”接入 hydrogen_color_field_emergence.py 的判据体系，
计算 dominant_frequency 和 effective_radius。
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

import cellular_shell_basis_animation as shell_model
from hydrogen_color_field_emergence import (
    compute_center,
    compute_effective_radius,
    dominant_frequency,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="为壳层闪现态计算类氢判据")
    parser.add_argument("--summary", type=str, required=True, help="cellular_shell_basis 的 summary_*.json")
    parser.add_argument("--flash-analysis", type=str, required=True, help="shell_flash_repro_analysis.py 输出的 flash_repro_analysis.json")
    parser.add_argument("--focus-series", choices=["ab", "ac", "bc", "tri"], default="bc", help="要投影到类氢判据的闪现系列")
    parser.add_argument("--grid-size", type=int, default=41, help="体素化密度场的边长")
    parser.add_argument("--margin", type=float, default=1.2, help="体素化边界在数据包围盒外扩的边距")
    parser.add_argument("--wave-cell-multiplier", type=int, default=1, help="波中心倍数")
    parser.add_argument("--cell-separation", type=float, default=2.0, help="父胞元间距")
    parser.add_argument("--cell-phase-offset", type=float, default=0.35, help="第二胞元相位偏移")
    parser.add_argument("--cell2-radius-scale", type=float, default=0.92, help="第二胞元尺度")
    parser.add_argument("--third-cell", action="store_true", help="分析第三胞元版本")
    parser.add_argument("--cell3-phase-offset", type=float, default=1.1, help="第三胞元相位偏移")
    parser.add_argument("--cell3-radius-scale", type=float, default=1.05, help="第三胞元尺度")
    parser.add_argument("--resonance-distance-threshold", type=float, default=1.45, help="共振距离阈值")
    parser.add_argument("--resonance-phase-threshold", type=float, default=0.95, help="共振相位阈值")
    parser.add_argument("--resonance-cell-scale", type=float, default=0.10, help="共振胞元尺度，用于构造密度团")
    parser.add_argument("--use-weighted-signal", action="store_true", help="dominant_frequency 使用 count*mean_weight；默认输出两种并以 weighted 为主")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def infer_series_dt(rows: list[dict[str, Any]]) -> float:
    if len(rows) < 2:
        return 1.0
    return float(rows[1]["t"] - rows[0]["t"])


def series_payload(rows: list[dict[str, Any]], focus_series: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    count_key = f"{focus_series}_n"
    weight_key = f"{focus_series}_mean_w"
    times = np.array([row["t"] for row in rows], dtype=np.float64)
    counts = np.array([row[count_key] for row in rows], dtype=np.float64)
    weights = np.array([row[weight_key] for row in rows], dtype=np.float64)
    signal = counts * weights
    dt = infer_series_dt(rows)
    return times, counts, signal, dt


def focus_time(flash_analysis: dict[str, Any], focus_series: str) -> float:
    jumps = flash_analysis.get("jumps", {})
    focus = jumps.get(focus_series, {})
    return float(focus.get("time", 0.0))


def resonance_centroids_at_time(
    focus_series: str,
    t: float,
    radii: np.ndarray,
    harmonic_orders: np.ndarray,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray]:
    cell_a_offset = np.array([-0.5 * args.cell_separation, 0.0, 0.0], dtype=np.float64)
    cell_b_offset = np.array([0.5 * args.cell_separation, 0.0, 0.0], dtype=np.float64)
    cell_c_offset = np.array([0.0, math.sqrt(3.0) * 0.5 * args.cell_separation, 0.0], dtype=np.float64)

    if focus_series == "ab":
        return shell_model.pair_resonance_centroids(
            radii,
            harmonic_orders,
            t,
            args.wave_cell_multiplier,
            cell_a_offset,
            cell_b_offset,
            args.cell_phase_offset,
            args.cell2_radius_scale,
            args.resonance_distance_threshold,
            args.resonance_phase_threshold,
        )
    if focus_series == "ac":
        return shell_model.pair_resonance_centroids(
            radii,
            harmonic_orders,
            t,
            args.wave_cell_multiplier,
            cell_a_offset,
            cell_c_offset,
            args.cell3_phase_offset,
            args.cell3_radius_scale,
            args.resonance_distance_threshold,
            args.resonance_phase_threshold,
        )
    if focus_series == "bc":
        return shell_model.pair_resonance_centroids(
            radii,
            harmonic_orders,
            t,
            args.wave_cell_multiplier,
            cell_b_offset,
            cell_c_offset,
            args.cell3_phase_offset - args.cell_phase_offset,
            args.cell3_radius_scale / max(args.cell2_radius_scale, 1e-6),
            args.resonance_distance_threshold,
            args.resonance_phase_threshold,
        )
    return shell_model.triple_resonance_centroids(
        radii,
        harmonic_orders,
        t,
        args.wave_cell_multiplier,
        cell_a_offset,
        cell_b_offset,
        cell_c_offset,
        args.cell_phase_offset,
        args.cell3_phase_offset,
        args.cell2_radius_scale,
        args.cell3_radius_scale,
        args.resonance_distance_threshold,
        args.resonance_phase_threshold,
    )


def voxelize_centroids(
    centroids: np.ndarray,
    weights: np.ndarray,
    grid_size: int,
    margin: float,
    sigma: float,
) -> tuple[np.ndarray, tuple[float, float, float], dict[str, float]]:
    if len(centroids) == 0:
        density = np.zeros((grid_size, grid_size, grid_size), dtype=np.float64)
        return density, (0.0, 0.0, 0.0), {"origin_x": 0.0, "origin_y": 0.0, "origin_z": 0.0, "spacing": 1.0}

    mins = np.min(centroids, axis=0) - margin
    maxs = np.max(centroids, axis=0) + margin
    span = np.max(maxs - mins)
    center_world = 0.5 * (mins + maxs)
    mins = center_world - 0.5 * span
    maxs = center_world + 0.5 * span

    xs = np.linspace(mins[0], maxs[0], grid_size, dtype=np.float64)
    ys = np.linspace(mins[1], maxs[1], grid_size, dtype=np.float64)
    zs = np.linspace(mins[2], maxs[2], grid_size, dtype=np.float64)
    zz, yy, xx = np.meshgrid(zs, ys, xs, indexing="ij")
    density = np.zeros((grid_size, grid_size, grid_size), dtype=np.float64)
    sigma2 = max(sigma * sigma, 1e-9)

    for center, weight in zip(centroids, weights):
        r2 = (xx - center[0]) ** 2 + (yy - center[1]) ** 2 + (zz - center[2]) ** 2
        density += float(max(weight, 1e-6)) * np.exp(-0.5 * r2 / sigma2)

    world_center = tuple(float(v) for v in center_world)
    spacing = float(span / max(grid_size - 1, 1))
    meta = {
        "origin_x": float(mins[0]),
        "origin_y": float(mins[1]),
        "origin_z": float(mins[2]),
        "spacing": spacing,
    }
    return density, world_center, meta


def voxel_center_to_world(center_idx: tuple[float, float, float], meta: dict[str, float]) -> tuple[float, float, float]:
    cx, cy, cz = center_idx
    return (
        meta["origin_x"] + cx * meta["spacing"],
        meta["origin_y"] + cy * meta["spacing"],
        meta["origin_z"] + cz * meta["spacing"],
    )


def voxel_radius_to_world(radius_voxel: float, meta: dict[str, float]) -> float:
    return float(radius_voxel * meta["spacing"])


def main() -> None:
    args = parse_args()
    summary_path = Path(args.summary)
    flash_path = Path(args.flash_analysis)
    summary = load_json(summary_path)
    flash = load_json(flash_path)

    radii = np.array(summary["shell_radii"], dtype=np.float64)
    harmonic_orders = np.array(summary["harmonic_orders"], dtype=np.int64)
    rows = flash["rows"]

    times, counts, weighted_signal, dt = series_payload(rows, args.focus_series)
    count_dominant_frequency = dominant_frequency(counts, dt)
    weighted_dominant_frequency = dominant_frequency(weighted_signal, dt)

    t_focus = focus_time(flash, args.focus_series)
    centroids, weights = resonance_centroids_at_time(args.focus_series, t_focus, radii, harmonic_orders, args)
    sigma = float(np.max(radii) * args.resonance_cell_scale)
    density, _, meta = voxelize_centroids(centroids, weights, args.grid_size, args.margin, sigma=sigma)
    center_idx = compute_center(density, dimensions=3)
    effective_radius_voxel = compute_effective_radius(density, center_idx, dimensions=3)
    center_world = voxel_center_to_world(center_idx, meta)
    effective_radius_world = voxel_radius_to_world(effective_radius_voxel, meta)

    result = {
        "summary_path": str(summary_path),
        "flash_analysis_path": str(flash_path),
        "focus_series": args.focus_series,
        "focus_time": t_focus,
        "series_dt": dt,
        "count_series": counts.tolist(),
        "weighted_signal_series": weighted_signal.tolist(),
        "count_dominant_frequency": float(count_dominant_frequency),
        "dominant_frequency_basis": "weighted" if args.use_weighted_signal else "count",
        "dominant_frequency": float(weighted_dominant_frequency if args.use_weighted_signal else count_dominant_frequency),
        "weighted_dominant_frequency": float(weighted_dominant_frequency),
        "focus_centroid_count": int(len(centroids)),
        "focus_centroid_weights": weights.tolist(),
        "voxel_center_index": [float(center_idx[0]), float(center_idx[1]), float(center_idx[2])],
        "center_world": [float(center_world[0]), float(center_world[1]), float(center_world[2])],
        "effective_radius_voxel": float(effective_radius_voxel),
        "effective_radius": float(effective_radius_world),
        "voxel_meta": meta,
        "density_total_mass": float(np.sum(density)),
        "density_peak": float(np.max(density)) if density.size else 0.0,
    }

    out_json = summary_path.parent / f"flash_hydrogen_metrics_{args.focus_series}.json"
    out_md = summary_path.parent / f"flash_hydrogen_metrics_{args.focus_series}.md"
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")

    md_lines = [
        "# Flash Hydrogen Metrics",
        "",
        f"- Summary: `{summary_path}`",
        f"- Flash analysis: `{flash_path}`",
        f"- Focus series: `{args.focus_series}`",
        f"- Focus time: `{t_focus:.2f}`",
        f"- Dominant frequency (count): `{count_dominant_frequency:.6f}`",
        f"- Dominant frequency (weighted): `{weighted_dominant_frequency:.6f}`",
        f"- Effective radius: `{effective_radius_world:.6f}`",
        f"- Focus centroid count: `{len(centroids)}`",
        "",
        "## Notes",
        "",
        "- `dominant_frequency` 直接复用 `hydrogen_color_field_emergence.py` 的 FFT 主频判据。",
        "- `effective_radius` 通过把闪现共振中心体素化为 3D 密度场，再复用类氢脚本的 `compute_center()` 与 `compute_effective_radius()` 计算。",
    ]
    out_md.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"JSON: {out_json}")
    print(f"Markdown: {out_md}")
    print(f"Dominant frequency (weighted): {weighted_dominant_frequency:.6f}")
    print(f"Effective radius: {effective_radius_world:.6f}")


if __name__ == "__main__":
    main()
