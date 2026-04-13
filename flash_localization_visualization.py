#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
    parser = argparse.ArgumentParser(description="可视化闪现态的局域化空间分布")
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
    return parser.parse_args()


def radial_profile_3d(density: np.ndarray, center: tuple[float, float, float], bins: int = 24) -> tuple[np.ndarray, np.ndarray]:
    cx, cy, cz = center
    zz, yy, xx = np.mgrid[0 : density.shape[0], 0 : density.shape[1], 0 : density.shape[2]]
    rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2 + (zz - cz) ** 2)
    edges = np.linspace(0.0, float(np.max(rr)), bins + 1)
    values = np.zeros(bins, dtype=np.float64)
    centers = 0.5 * (edges[:-1] + edges[1:])
    for i in range(bins):
        mask = (rr >= edges[i]) & (rr < edges[i + 1])
        if np.any(mask):
            values[i] = float(np.mean(density[mask]))
    return centers, values


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

    xy_projection = np.max(density, axis=0)
    xz_projection = np.max(density, axis=1)
    radial_r, radial_v = radial_profile_3d(density, center_idx, bins=28)

    fig = plt.figure(figsize=(14.5, 10.5))
    fig.patch.set_facecolor("white")

    ax1 = fig.add_subplot(2, 2, 1, projection="3d")
    if len(centroids) > 0:
        size_scale = 160.0 * (weights / max(float(np.max(weights)), 1e-9) + 0.15)
        scatter = ax1.scatter(
            centroids[:, 0],
            centroids[:, 1],
            centroids[:, 2],
            c=weights,
            s=size_scale,
            cmap="magma",
            alpha=0.9,
            edgecolors="black",
            linewidths=0.35,
        )
        fig.colorbar(scatter, ax=ax1, shrink=0.75, label="resonance weight")
    ax1.set_title(f"3D Flash Centroids ({args.focus_series}) @ t={t_focus:.2f}")
    ax1.set_xlabel("x")
    ax1.set_ylabel("y")
    ax1.set_zlabel("z")

    ax2 = fig.add_subplot(2, 2, 2)
    im_xy = ax2.imshow(xy_projection, cmap="magma", origin="lower", aspect="equal")
    ax2.scatter([center_idx[0]], [center_idx[1]], c="cyan", s=40, marker="x", linewidths=1.5)
    ax2.set_title("XY Max Projection")
    ax2.set_xlabel("voxel x")
    ax2.set_ylabel("voxel y")
    fig.colorbar(im_xy, ax=ax2, shrink=0.8, label="max density")

    ax3 = fig.add_subplot(2, 2, 3)
    im_xz = ax3.imshow(xz_projection, cmap="viridis", origin="lower", aspect="equal")
    ax3.scatter([center_idx[0]], [center_idx[2]], c="red", s=40, marker="x", linewidths=1.5)
    ax3.set_title("XZ Max Projection")
    ax3.set_xlabel("voxel x")
    ax3.set_ylabel("voxel z")
    fig.colorbar(im_xz, ax=ax3, shrink=0.8, label="max density")

    ax4 = fig.add_subplot(2, 2, 4)
    ax4.plot(radial_r * meta["spacing"], radial_v, color="#7c3aed", linewidth=2.0)
    ax4.axvline(effective_radius_world, color="#ef4444", linestyle="--", linewidth=1.5, label=f"effective radius = {effective_radius_world:.3f}")
    ax4.set_title("Radial Localization Profile")
    ax4.set_xlabel("radius")
    ax4.set_ylabel("mean density")
    ax4.grid(alpha=0.25)
    ax4.legend(loc="upper right")

    fig.suptitle(
        f"Flash Localization Visualization\ncenter=({center_world[0]:.3f}, {center_world[1]:.3f}, {center_world[2]:.3f}), "
        f"effective_radius={effective_radius_world:.3f}, centroids={len(centroids)}",
        fontsize=14,
        y=0.98,
    )
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.95])

    out_png = summary_path.parent / f"flash_localization_{args.focus_series}.png"
    out_json = summary_path.parent / f"flash_localization_{args.focus_series}.json"
    fig.savefig(out_png, dpi=180)
    plt.close(fig)

    payload = {
        "summary_path": str(summary_path),
        "flash_analysis_path": str(flash_path),
        "focus_series": args.focus_series,
        "focus_time": t_focus,
        "centroid_count": int(len(centroids)),
        "center_world": [float(v) for v in center_world],
        "effective_radius": float(effective_radius_world),
        "density_peak": float(np.max(density)) if density.size else 0.0,
        "output_png": str(out_png),
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"PNG: {out_png}")
    print(f"JSON: {out_json}")
    print(f"Effective radius: {effective_radius_world:.6f}")


if __name__ == "__main__":
    main()
