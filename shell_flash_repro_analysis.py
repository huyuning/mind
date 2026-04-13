#!/usr/bin/env python3
"""
复现并分析壳层动画中的“闪现”胞元。

用途：
- 从一次既有运行的 summary.json 还原时间采样、壳层半径与谐波配置
- 复算各类共振胞元数量随时间的变化
- 定位最大跳变发生的时刻与类型
- 导出详细 JSON/Markdown 报告，便于稳定复现实验
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

import cellular_shell_basis_animation as model


@dataclass
class JumpEvent:
    series_name: str
    time: float
    previous_count: int
    current_count: int
    delta: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="复现并分析胞元闪现")
    parser.add_argument("--summary", type=str, required=True, help="目标运行的 summary_*.json 路径")
    parser.add_argument("--frame-target", type=int, default=54, help="回放时采用的目标帧数，用于还原 GIF 抽帧")
    parser.add_argument("--wave-cell-multiplier", type=int, default=1, help="每个谐波波峰生成的波中心倍数")
    parser.add_argument("--cell-separation", type=float, default=2.0, help="胞元间距")
    parser.add_argument("--cell-phase-offset", type=float, default=0.35, help="第二胞元相位偏移")
    parser.add_argument("--cell2-radius-scale", type=float, default=0.92, help="第二胞元尺度")
    parser.add_argument("--third-cell", action="store_true", help="分析包含第三胞元的配置")
    parser.add_argument("--cell3-phase-offset", type=float, default=1.1, help="第三胞元相位偏移")
    parser.add_argument("--cell3-radius-scale", type=float, default=1.05, help="第三胞元尺度")
    parser.add_argument("--resonance-distance-threshold", type=float, default=1.45, help="共振距离阈值")
    parser.add_argument("--resonance-phase-threshold", type=float, default=0.95, help="共振相位阈值")
    parser.add_argument("--focus-series", choices=["ab", "ac", "bc", "tri"], default="bc", help="重点展开分析的跳变系列")
    return parser.parse_args()


def times_from_summary(summary: dict[str, Any], frame_target: int) -> np.ndarray:
    duration = float(summary["duration"])
    dt = float(summary["dt"])
    all_times = np.arange(0.0, duration + 0.5 * dt, dt, dtype=np.float64)
    stride = max(1, int(math.ceil(len(all_times) / max(1, frame_target))))
    return all_times[::stride]


def load_summary(path: Path) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    summary = json.loads(path.read_text(encoding="utf-8"))
    radii = np.array(summary["shell_radii"], dtype=np.float64)
    harmonic_orders = np.array(summary["harmonic_orders"], dtype=np.int64)
    return summary, radii, harmonic_orders


def pair_centroids(
    radii: np.ndarray,
    harmonic_orders: np.ndarray,
    t: float,
    wave_cell_multiplier: int,
    offset_a: np.ndarray,
    offset_b: np.ndarray,
    phase_b: float,
    scale_b: float,
    distance_threshold: float,
    phase_threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    return model.pair_resonance_centroids(
        radii,
        harmonic_orders,
        t,
        wave_cell_multiplier,
        offset_a,
        offset_b,
        phase_b,
        scale_b,
        distance_threshold,
        phase_threshold,
    )


def compute_series(args: argparse.Namespace, radii: np.ndarray, harmonic_orders: np.ndarray, times: np.ndarray) -> list[dict[str, Any]]:
    cell_a_offset = np.array([-0.5 * args.cell_separation, 0.0, 0.0], dtype=np.float64)
    cell_b_offset = np.array([0.5 * args.cell_separation, 0.0, 0.0], dtype=np.float64)
    cell_c_offset = np.array([0.0, math.sqrt(3.0) * 0.5 * args.cell_separation, 0.0], dtype=np.float64)

    rows: list[dict[str, Any]] = []
    for t in times:
        ab_centers, ab_weights = pair_centroids(
            radii,
            harmonic_orders,
            float(t),
            args.wave_cell_multiplier,
            cell_a_offset,
            cell_b_offset,
            args.cell_phase_offset,
            args.cell2_radius_scale,
            args.resonance_distance_threshold,
            args.resonance_phase_threshold,
        )

        ac_centers = np.zeros((0, 3), dtype=np.float64)
        ac_weights = np.zeros(0, dtype=np.float64)
        bc_centers = np.zeros((0, 3), dtype=np.float64)
        bc_weights = np.zeros(0, dtype=np.float64)
        tri_centers = np.zeros((0, 3), dtype=np.float64)
        tri_weights = np.zeros(0, dtype=np.float64)

        if args.third_cell:
            ac_centers, ac_weights = pair_centroids(
                radii,
                harmonic_orders,
                float(t),
                args.wave_cell_multiplier,
                cell_a_offset,
                cell_c_offset,
                args.cell3_phase_offset,
                args.cell3_radius_scale,
                args.resonance_distance_threshold,
                args.resonance_phase_threshold,
            )
            bc_centers, bc_weights = pair_centroids(
                radii,
                harmonic_orders,
                float(t),
                args.wave_cell_multiplier,
                cell_b_offset,
                cell_c_offset,
                args.cell3_phase_offset - args.cell_phase_offset,
                args.cell3_radius_scale / max(args.cell2_radius_scale, 1e-6),
                args.resonance_distance_threshold,
                args.resonance_phase_threshold,
            )
            tri_centers, tri_weights = model.triple_resonance_centroids(
                radii,
                harmonic_orders,
                float(t),
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

        rows.append(
            {
                "t": float(t),
                "ab_n": int(len(ab_centers)),
                "ac_n": int(len(ac_centers)),
                "bc_n": int(len(bc_centers)),
                "tri_n": int(len(tri_centers)),
                "ab_mean_w": float(np.mean(ab_weights)) if len(ab_weights) else 0.0,
                "ac_mean_w": float(np.mean(ac_weights)) if len(ac_weights) else 0.0,
                "bc_mean_w": float(np.mean(bc_weights)) if len(bc_weights) else 0.0,
                "tri_mean_w": float(np.mean(tri_weights)) if len(tri_weights) else 0.0,
            }
        )
    return rows


def largest_jump(rows: list[dict[str, Any]], series_name: str) -> JumpEvent:
    key = f"{series_name}_n"
    if len(rows) < 2:
        return JumpEvent(series_name, 0.0, 0, 0, 0)
    best_i = max(range(1, len(rows)), key=lambda i: abs(rows[i][key] - rows[i - 1][key]))
    previous_count = int(rows[best_i - 1][key])
    current_count = int(rows[best_i][key])
    return JumpEvent(
        series_name=series_name,
        time=float(rows[best_i]["t"]),
        previous_count=previous_count,
        current_count=current_count,
        delta=current_count - previous_count,
    )


def detail_candidates(
    args: argparse.Namespace,
    radii: np.ndarray,
    harmonic_orders: np.ndarray,
    t: float,
    focus_series: str,
) -> dict[str, Any]:
    cell_a_offset = np.array([-0.5 * args.cell_separation, 0.0, 0.0], dtype=np.float64)
    cell_b_offset = np.array([0.5 * args.cell_separation, 0.0, 0.0], dtype=np.float64)
    cell_c_offset = np.array([0.0, math.sqrt(3.0) * 0.5 * args.cell_separation, 0.0], dtype=np.float64)

    if focus_series == "ab":
        offset_1, offset_2 = cell_a_offset, cell_b_offset
        phase_2, scale_2 = args.cell_phase_offset, args.cell2_radius_scale
    elif focus_series == "ac":
        offset_1, offset_2 = cell_a_offset, cell_c_offset
        phase_2, scale_2 = args.cell3_phase_offset, args.cell3_radius_scale
    elif focus_series == "bc":
        offset_1, offset_2 = cell_b_offset, cell_c_offset
        phase_2 = args.cell3_phase_offset - args.cell_phase_offset
        scale_2 = args.cell3_radius_scale / max(args.cell2_radius_scale, 1e-6)
    else:
        triple_centers, triple_weights = model.triple_resonance_centroids(
            radii,
            harmonic_orders,
            float(t),
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
        return {
            "count": int(len(triple_centers)),
            "mean_weight": float(np.mean(triple_weights)) if len(triple_weights) else 0.0,
        }

    candidates: list[dict[str, Any]] = []
    for shell_idx, (radius, harmonic_order) in enumerate(zip(radii, harmonic_orders)):
        centers_1, phases_1 = model.child_cell_centers(
            float(radius),
            int(harmonic_order),
            float(t),
            shell_idx,
            len(radii),
            args.wave_cell_multiplier,
            center_offset=offset_1,
        )
        centers_2, phases_2 = model.child_cell_centers(
            float(radius),
            int(harmonic_order),
            float(t),
            shell_idx,
            len(radii),
            args.wave_cell_multiplier,
            center_offset=offset_2,
            phase_offset=phase_2,
            radius_scale=scale_2,
        )
        count = min(len(centers_1), len(centers_2))
        for idx in range(count):
            dist = float(np.linalg.norm(centers_1[idx] - centers_2[idx]))
            phase_diff = float(model.wrapped_phase_delta(float(phases_1[idx]), float(phases_2[idx])))
            candidates.append(
                {
                    "shell_idx": int(shell_idx),
                    "harmonic_order": int(harmonic_order),
                    "pair_idx": int(idx),
                    "dist": dist,
                    "phase_diff": phase_diff,
                    "pass": bool(
                        dist <= args.resonance_distance_threshold
                        and phase_diff <= args.resonance_phase_threshold
                    ),
                }
            )
    candidates.sort(key=lambda row: (row["dist"], row["phase_diff"]))
    return {
        "count": sum(1 for item in candidates if item["pass"]),
        "top10": candidates[:10],
    }


def write_markdown(
    out_path: Path,
    summary_path: Path,
    rows: list[dict[str, Any]],
    focus_jump: JumpEvent,
    focus_detail: dict[str, Any],
) -> None:
    lines = [
        "# Flash Reproduction Analysis",
        "",
        f"- Summary: `{summary_path}`",
        f"- Focus series: `{focus_jump.series_name}`",
        f"- Largest jump: `{focus_jump.previous_count} -> {focus_jump.current_count}` at `t={focus_jump.time:.2f}`",
        "",
        "## Mechanism",
        "",
        "- The flash is caused by thresholded resonance birth, not by continuous amplitude divergence.",
        "- A candidate cell appears only after both distance and phase conditions pass.",
        "- Near the threshold, a small center displacement across adjacent frames causes a visible on/off switch.",
        "",
        "## Focus Detail",
        "",
        "```json",
        json.dumps(focus_detail, indent=2),
        "```",
        "",
        "## First Rows",
        "",
        "```json",
        json.dumps(rows[:8], indent=2),
        "```",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    summary_path = Path(args.summary)
    summary, radii, harmonic_orders = load_summary(summary_path)
    times = times_from_summary(summary, args.frame_target)
    rows = compute_series(args, radii, harmonic_orders, times)

    jumps = {
        name: asdict(largest_jump(rows, name))
        for name in ["ab", "ac", "bc", "tri"]
    }
    focus_jump = largest_jump(rows, args.focus_series)
    focus_detail = detail_candidates(args, radii, harmonic_orders, focus_jump.time, args.focus_series)

    run_dir = summary_path.parent
    json_out = run_dir / "flash_repro_analysis.json"
    md_out = run_dir / "flash_repro_analysis.md"

    payload = {
        "summary_path": str(summary_path),
        "focus_series": args.focus_series,
        "jumps": jumps,
        "focus_detail": focus_detail,
        "rows": rows,
    }
    json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(md_out, summary_path, rows, focus_jump, focus_detail)

    print(f"JSON: {json_out}")
    print(f"Markdown: {md_out}")
    print(f"Focus jump: {focus_jump.series_name} {focus_jump.previous_count} -> {focus_jump.current_count} at t={focus_jump.time:.2f}")


if __name__ == "__main__":
    main()
