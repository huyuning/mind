#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import animation

from hydrogen_color_field_emergence import compute_center, compute_effective_radius
from shell_flash_hydrogen_metrics import (
    focus_time,
    load_json,
    resonance_centroids_at_time,
    voxel_center_to_world,
    voxel_radius_to_world,
    voxelize_centroids,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成围绕闪现态的 3D 旋转 GIF")
    parser.add_argument("--summary", required=True, help="cellular_shell_basis 的 summary_*.json")
    parser.add_argument("--flash-analysis", required=True, help="flash_repro_analysis.json")
    parser.add_argument("--focus-series", choices=["ab", "ac", "bc", "tri"], default="bc", help="焦点闪现系列")
    parser.add_argument("--grid-size", type=int, default=61, help="体素密度场边长")
    parser.add_argument("--margin", type=float, default=1.4, help="体素化边界外扩")
    parser.add_argument("--resonance-cell-scale", type=float, default=0.10, help="共振胞元尺度")
    parser.add_argument("--wave-cell-multiplier", type=int, default=1, help="波中心倍数")
    parser.add_argument("--cell-separation", type=float, default=2.0, help="父胞元间距")
    parser.add_argument("--cell-phase-offset", type=float, default=0.35, help="第二胞元相位偏移")
    parser.add_argument("--cell2-radius-scale", type=float, default=0.92, help="第二胞元尺度")
    parser.add_argument("--third-cell", action="store_true", help="使用第三胞元配置")
    parser.add_argument("--cell3-phase-offset", type=float, default=1.1, help="第三胞元相位偏移")
    parser.add_argument("--cell3-radius-scale", type=float, default=1.05, help="第三胞元尺度")
    parser.add_argument("--resonance-distance-threshold", type=float, default=1.45, help="共振距离阈值")
    parser.add_argument("--resonance-phase-threshold", type=float, default=0.95, help="共振相位阈值")
    parser.add_argument("--frames", type=int, default=48, help="旋转帧数")
    parser.add_argument("--fps", type=int, default=12, help="GIF 帧率")
    parser.add_argument("--elevation", type=float, default=24.0, help="观察仰角")
    parser.add_argument("--density-quantile", type=float, default=0.965, help="用于显示密度点云的分位阈值")
    parser.add_argument("--max-density-points", type=int, default=2500, help="密度点云最大采样点数")
    return parser.parse_args()


def density_point_cloud(
    density: np.ndarray,
    meta: dict[str, float],
    quantile: float,
    max_points: int,
) -> tuple[np.ndarray, np.ndarray]:
    if density.size == 0 or float(np.max(density)) <= 0.0:
        return np.zeros((0, 3), dtype=np.float64), np.zeros(0, dtype=np.float64)
    threshold = float(np.quantile(density, np.clip(quantile, 0.0, 0.9999)))
    mask = density >= threshold
    idx = np.argwhere(mask)
    vals = density[mask]
    if len(idx) == 0:
        return np.zeros((0, 3), dtype=np.float64), np.zeros(0, dtype=np.float64)
    if len(idx) > max_points:
        order = np.argsort(vals)[-max_points:]
        idx = idx[order]
        vals = vals[order]
    points = np.zeros((len(idx), 3), dtype=np.float64)
    points[:, 0] = meta["origin_x"] + idx[:, 2] * meta["spacing"]
    points[:, 1] = meta["origin_y"] + idx[:, 1] * meta["spacing"]
    points[:, 2] = meta["origin_z"] + idx[:, 0] * meta["spacing"]
    return points, vals.astype(np.float64)


def main() -> None:
    args = parse_args()
    summary_path = Path(args.summary)
    flash_path = Path(args.flash_analysis)
    summary = load_json(summary_path)
    flash = load_json(flash_path)

    radii = np.array(summary["shell_radii"], dtype=np.float64)
    harmonic_orders = np.array(summary["harmonic_orders"], dtype=np.int64)
    t_focus = focus_time(flash, args.focus_series)
    centroids, weights = resonance_centroids_at_time(args.focus_series, t_focus, radii, harmonic_orders, args)

    sigma = float(np.max(radii) * args.resonance_cell_scale)
    density, _, meta = voxelize_centroids(
        centroids=centroids,
        weights=weights,
        grid_size=args.grid_size,
        margin=args.margin,
        sigma=sigma,
    )
    center_idx = compute_center(density, dimensions=3)
    effective_radius_voxel = compute_effective_radius(density, center_idx, dimensions=3)
    center_world = voxel_center_to_world(center_idx, meta)
    effective_radius_world = voxel_radius_to_world(effective_radius_voxel, meta)

    density_points, density_values = density_point_cloud(
        density=density,
        meta=meta,
        quantile=args.density_quantile,
        max_points=args.max_density_points,
    )

    fig = plt.figure(figsize=(8.6, 7.4))
    ax = fig.add_subplot(111, projection="3d")
    fig.patch.set_facecolor("#0b1020")
    ax.set_facecolor("#0b1020")

    span = max(2.4, effective_radius_world * 2.6)
    cx, cy, cz = center_world

    def style_axes() -> None:
        ax.set_xlim(cx - span, cx + span)
        ax.set_ylim(cy - span, cy + span)
        ax.set_zlim(cz - span, cz + span)
        ax.set_xlabel("x", color="#e5e7eb")
        ax.set_ylabel("y", color="#e5e7eb")
        ax.set_zlabel("z", color="#e5e7eb")
        ax.tick_params(colors="#cbd5e1")
        ax.xaxis.pane.set_facecolor((0.12, 0.15, 0.23, 0.28))
        ax.yaxis.pane.set_facecolor((0.12, 0.15, 0.23, 0.28))
        ax.zaxis.pane.set_facecolor((0.12, 0.15, 0.23, 0.28))
        ax.set_title(
            f"Flash State Rotating View ({args.focus_series})\n"
            f"t={t_focus:.2f}, effective_radius={effective_radius_world:.3f}",
            color="#e5e7eb",
        )

    def draw_frame(frame_idx: int) -> list[object]:
        ax.cla()
        style_axes()
        azim = 360.0 * frame_idx / max(args.frames, 1)
        ax.view_init(elev=args.elevation, azim=azim)

        artists: list[object] = []
        if len(density_points) > 0:
            density_sizes = 4.0 + 18.0 * (density_values / max(float(np.max(density_values)), 1e-9))
            artists.append(
                ax.scatter(
                    density_points[:, 0],
                    density_points[:, 1],
                    density_points[:, 2],
                    c=density_values,
                    cmap="viridis",
                    s=density_sizes,
                    alpha=0.18,
                    linewidths=0.0,
                )
            )
        if len(centroids) > 0:
            centroid_sizes = 80.0 + 180.0 * (weights / max(float(np.max(weights)), 1e-9))
            artists.append(
                ax.scatter(
                    centroids[:, 0],
                    centroids[:, 1],
                    centroids[:, 2],
                    c=weights,
                    cmap="magma",
                    s=centroid_sizes,
                    alpha=0.95,
                    edgecolors="#f8fafc",
                    linewidths=0.4,
                )
            )
        artists.append(
            ax.scatter(
                [cx],
                [cy],
                [cz],
                c=["cyan"],
                s=[80.0],
                marker="x",
                linewidths=2.0,
            )
        )
        return artists

    anim = animation.FuncAnimation(fig, draw_frame, frames=args.frames, interval=1000 / max(args.fps, 1), blit=False)

    out_gif = summary_path.parent / f"flash_localization_rotating_{args.focus_series}.gif"
    out_json = summary_path.parent / f"flash_localization_rotating_{args.focus_series}.json"
    writer = animation.PillowWriter(fps=args.fps)
    anim.save(out_gif, writer=writer)
    plt.close(fig)

    payload = {
        "summary_path": str(summary_path),
        "flash_analysis_path": str(flash_path),
        "focus_series": args.focus_series,
        "focus_time": t_focus,
        "centroid_count": int(len(centroids)),
        "density_point_count": int(len(density_points)),
        "center_world": [float(cx), float(cy), float(cz)],
        "effective_radius": float(effective_radius_world),
        "output_gif": str(out_gif),
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"GIF: {out_gif}")
    print(f"JSON: {out_json}")
    print(f"Effective radius: {effective_radius_world:.6f}")


if __name__ == "__main__":
    main()
