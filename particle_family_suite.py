#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zero-prior mode-family suite on top of hydrogen_color_field_emergence.py

Purpose:
- Define qualitative "mode families" (electron-like, neutrino-like, up/down-quark-like)
  as parameter regimes in a dimensionless SU(3) structural toy model without any
  external prior data.
- Run small parameter scans per family, reuse the simulator to generate results,
  collect summary metrics, and pick a representative "best" example.
- Produce a CSV summary and a simple Markdown report linking to outputs.

Notes & Naming:
- This script is an exploratory tool, not a physics solver. It does NOT claim physical fidelity.
- Labels such as electron / neutrino / up_quark / down_quark denote mode families (占位“模式家族”),
  not Standard Model particles. See docs/EFFECTIVE_MODEL_STATEMENT.md for the effective-theory scope.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import itertools
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import numpy as np

# Import the simulator as a module to call simulate() directly
try:
    from hydrogen_color_field_emergence import simulate  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError("Failed to import hydrogen_color_field_emergence.simulate") from e


@dataclass
class ModeTarget:
    # Qualitative target windows to guide selection.
    # All are soft constraints; the scoring uses distances/penalties.
    freq_min: float
    freq_max: float
    radius_min: float
    radius_max: float
    peak_mean_min: float


@dataclass
class ParticleConfig:
    name: str
    dimensions: int
    # Parameter grids
    m_list: List[int]
    angular_gain_list: List[float]
    su3_spin_list: List[float]
    diffusion_list: List[float]
    attraction_list: List[float]
    repulsion_list: List[float]
    # Fixed temporal + grid setup
    width: int = 41
    height: int = 41
    depth: int = 17
    duration: float = 5.0
    dt: float = 0.02
    periodic: bool = False
    seed: int = 20260409
    save_stride: int = 5
    probe_radius: float = 2.0
    stft_window: int = 64
    stft_hop: int = 8
    target_frames: int = 60
    # Selection target
    target: ModeTarget = dataclasses.field(
        default_factory=lambda: ModeTarget(
            freq_min=0.1, freq_max=0.4, radius_min=6.0, radius_max=22.0, peak_mean_min=3.0
        )
    )


def make_default_suite(dimensions: int, mode: str = "fast") -> List[ParticleConfig]:
    """
    Build a small set of particle mode scans. 'mode' can be:
    - 'fast': minimal grid for quick exploration
    - 'full': denser grid
    """
    if dimensions not in (2, 3):
        raise ValueError("dimensions must be 2 or 3")

    # Grid presets
    if mode == "fast":
        # First-pass exploration should stay small enough to finish quickly.
        m_list = [0, 1]
        angular_gain = [0.0, 0.24] if dimensions == 2 else [0.0, 0.16]
        su3_spin = [0.18, 0.28]
    else:
        m_list = [0, 1, 2]
        angular_gain = [0.0, 0.12, 0.18, 0.24, 0.30] if dimensions == 2 else [0.0, 0.10, 0.14, 0.18, 0.22]
        su3_spin = [0.16, 0.20, 0.24, 0.28, 0.32]

    # Shared nonlinear/transport ranges
    if mode == "fast":
        diffusion = [0.18]
        attraction = [2.4, 3.0]
        repulsion = [2.1, 2.4]
    else:
        diffusion = [0.16, 0.18, 0.22]
        attraction = [2.2, 2.6, 3.0]
        repulsion = [2.0, 2.2, 2.4]

    # Heuristic targets per label (purely for picking "nice" modes)
    # You can tune these to steer selection.
    eid = ModeTarget(freq_min=0.12, freq_max=0.30, radius_min=8.0, radius_max=22.0, peak_mean_min=3.0)
    nu = ModeTarget(freq_min=0.05, freq_max=0.20, radius_min=10.0, radius_max=24.0, peak_mean_min=2.5)
    uq = ModeTarget(freq_min=0.18, freq_max=0.50, radius_min=6.0, radius_max=18.0, peak_mean_min=3.5)
    dq = ModeTarget(freq_min=0.15, freq_max=0.40, radius_min=6.0, radius_max=18.0, peak_mean_min=3.2)

    base2d = dict(width=41, height=41, duration=5.0, dt=0.02, target_frames=60)
    base3d = dict(width=17, height=17, depth=17, duration=3.5, dt=0.03, target_frames=40)
    base = base2d if dimensions == 2 else base3d

    return [
        ParticleConfig(
            name="electron",
            dimensions=dimensions,
            m_list=m_list,
            angular_gain_list=angular_gain,
            su3_spin_list=su3_spin,
            diffusion_list=diffusion,
            attraction_list=attraction,
            repulsion_list=repulsion,
            target=eid,
            **base,
        ),
        ParticleConfig(
            name="neutrino",
            dimensions=dimensions,
            m_list=m_list,
            angular_gain_list=angular_gain,
            su3_spin_list=su3_spin,
            diffusion_list=diffusion,
            attraction_list=attraction,
            repulsion_list=repulsion,
            target=nu,
            **base,
        ),
        ParticleConfig(
            name="up_quark",
            dimensions=dimensions,
            m_list=m_list,
            angular_gain_list=angular_gain,
            su3_spin_list=su3_spin,
            diffusion_list=diffusion,
            attraction_list=attraction,
            repulsion_list=repulsion,
            target=uq,
            **base,
        ),
        ParticleConfig(
            name="down_quark",
            dimensions=dimensions,
            m_list=m_list,
            angular_gain_list=angular_gain,
            su3_spin_list=su3_spin,
            diffusion_list=diffusion,
            attraction_list=attraction,
            repulsion_list=repulsion,
            target=dq,
            **base,
        ),
    ]


def run_single(config: ParticleConfig, params: Dict[str, Any]) -> Path:
    """
    Call the simulator with given arguments, return the run directory.
    """
    # Build a fake argparse.Namespace for simulate()
    class NS:
        pass

    ns = NS()
    # Grid / domain
    ns.dimensions = config.dimensions
    ns.width = config.width
    ns.height = config.height
    ns.depth = config.depth
    # Temporal
    ns.duration = config.duration
    ns.dt = config.dt
    ns.seed = config.seed
    # Physics
    ns.diffusion = params["diffusion"]
    ns.attraction = params["attraction"]
    ns.repulsion = params["repulsion"]
    ns.su3_spin = params["su3_spin"]
    ns.angular_momentum = params["m"]
    ns.angular_gain = params["angular_gain"]
    # Misc / IO
    ns.periodic = False
    ns.save_stride = 5
    ns.probe_radius = 2.0
    ns.stft_window = 64
    ns.stft_hop = 8
    ns.target_frames = config.target_frames
    # Run
    run_dir = simulate(ns)
    return run_dir


def load_summary(run_dir: Path) -> Dict[str, Any]:
    # Find the summary_*.json in run_dir
    files = sorted(run_dir.glob("summary_*.json"))
    if not files:
        return {}
    with files[0].open("r", encoding="utf-8") as f:
        return json.load(f)


def score_summary(summary: Dict[str, Any], target: ModeTarget) -> float:
    """
    Lower is better. Penalize deviations from soft targets and encourage peak/mean.
    """
    if not summary:
        return 1e9
    f = float(summary.get("probe_dominant_frequency", 0.0))
    r = float(summary.get("effective_radius", 0.0))
    pm = float(summary.get("final_peak_to_mean_ratio", 0.0))

    # Frequency penalty: 0 inside window, quadratic outside
    if f < target.freq_min:
        p_f = (target.freq_min - f) ** 2
    elif f > target.freq_max:
        p_f = (f - target.freq_max) ** 2
    else:
        p_f = 0.0

    # Radius penalty
    if r < target.radius_min:
        p_r = (target.radius_min - r) ** 2
    elif r > target.radius_max:
        p_r = (r - target.radius_max) ** 2
    else:
        p_r = 0.0

    # Encourage higher peak/mean, penalize if below min
    p_pm = 0.0 if pm >= target.peak_mean_min else (target.peak_mean_min - pm) ** 2

    # Total score with weights
    score = p_f * 1.0 + p_r * 0.5 + p_pm * 1.5 - 0.05 * pm
    return score


def ensure_outdir() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path("resonance_data") / f"particle_family_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def sample_grid_points(grid: List[Tuple[Any, ...]], limit: int | None) -> List[Tuple[Any, ...]]:
    if limit is None or limit <= 0 or limit >= len(grid):
        return grid
    if limit == 1:
        return [grid[len(grid) // 2]]

    sampled: List[Tuple[Any, ...]] = []
    used_indices = set()
    for i in range(limit):
        idx = round(i * (len(grid) - 1) / (limit - 1))
        if idx not in used_indices:
            sampled.append(grid[idx])
            used_indices.add(idx)

    if len(sampled) < limit:
        for idx, item in enumerate(grid):
            if idx not in used_indices:
                sampled.append(item)
                if len(sampled) >= limit:
                    break
    return sampled


def run_suite(
    particles: List[ParticleConfig],
    outdir: Path,
    max_runs_per_particle: int | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Run scans for each particle, collect summaries, pick best by score.
    Returns:
      - all_rows: per-run CSV rows
      - best_map: particle -> best {summary, params, run_dir}
    """
    all_rows: List[Dict[str, Any]] = []
    best_map: Dict[str, Dict[str, Any]] = {}

    for pcfg in particles:
        best_score = 1e9
        best_record: Optional[Dict[str, Any]] = None

        full_grid = list(
            itertools.product(
            pcfg.m_list,
            pcfg.angular_gain_list,
            pcfg.su3_spin_list,
            pcfg.diffusion_list,
            pcfg.attraction_list,
            pcfg.repulsion_list,
            )
        )
        grid = sample_grid_points(full_grid, max_runs_per_particle)
        for idx, (m, angular_gain, su3_spin, diffusion, attraction, repulsion) in enumerate(grid):
            params = dict(
                m=m,
                angular_gain=angular_gain,
                su3_spin=su3_spin,
                diffusion=diffusion,
                attraction=attraction,
                repulsion=repulsion,
            )
            print(f"[{pcfg.name}] run {idx + 1}: {params}", flush=True)
            run_dir = run_single(pcfg, params)
            summary = load_summary(run_dir)
            row = dict(
                particle=pcfg.name,
                run_dir=str(run_dir),
                dimensions=pcfg.dimensions,
                m=m,
                angular_gain=angular_gain,
                su3_spin=su3_spin,
                diffusion=diffusion,
                attraction=attraction,
                repulsion=repulsion,
                freq=float(summary.get("probe_dominant_frequency", float("nan"))),
                radius=float(summary.get("effective_radius", float("nan"))),
                peak_mean=float(summary.get("final_peak_to_mean_ratio", float("nan"))),
            )
            all_rows.append(row)

            score = score_summary(summary, pcfg.target)
            if score < best_score:
                best_score = score
                best_record = {
                    "particle": pcfg.name,
                    "run_dir": str(run_dir),
                    "params": params,
                    "summary": summary,
                    "score": score,
                }

        if best_record is not None:
            best_map[pcfg.name] = best_record

    # Write CSV
    csv_path = outdir / "particle_family_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "particle",
                "run_dir",
                "dimensions",
                "m",
                "angular_gain",
                "su3_spin",
                "diffusion",
                "attraction",
                "repulsion",
                "freq",
                "radius",
                "peak_mean",
            ],
        )
        writer.writeheader()
        for r in all_rows:
            writer.writerow(r)

    # Write Markdown overview
    md_path = outdir / "README.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Mode-Family Scan (Zero-prior SU(3) Structural Toy)\n\n")
        f.write("- Labels denote mode families (非标准模型粒子的一一对应), used as placeholders for distinct stable regimes.\n")
        f.write("- See docs/EFFECTIVE_MODEL_STATEMENT.md for scope, units, and limitations.\n\n")
        for name, rec in best_map.items():
            f.write(f"## {name}\n\n")
            f.write(f"- run_dir: {rec['run_dir']}\n")
            f.write(f"- params: `{json.dumps(rec['params'])}`\n")
            s = rec["summary"]
            f.write(
                "- metrics: "
                f"freq={s.get('probe_dominant_frequency'):.4f}, "
                f"radius={s.get('effective_radius'):.3f}, "
                f"peak/mean={s.get('final_peak_to_mean_ratio'):.3f}\n\n"
            )

    return all_rows, best_map


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Zero-prior mode-family scan (quark/lepton-like families)")
    p.add_argument("--dimensions", type=int, choices=[2, 3], default=2, help="空间维度：2 或 3")
    p.add_argument("--mode", type=str, choices=["fast", "full"], default="fast", help="扫描粒度")
    p.add_argument(
        "--particles",
        type=str,
        default="electron,neutrino,up_quark,down_quark",
        help="要扫描的粒子列表，以逗号分隔",
    )
    p.add_argument(
        "--max-runs-per-particle",
        type=int,
        default=None,
        help="限制每种粒子的最大试跑次数；首轮实验可用 4-8",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    suite = make_default_suite(dimensions=args.dimensions, mode=args.mode)
    # Filter by requested set
    wanted = set(s.strip() for s in args.particles.split(",") if s.strip())
    suite = [pc for pc in suite if pc.name in wanted]
    outdir = ensure_outdir()
    _, best = run_suite(suite, outdir, max_runs_per_particle=args.max_runs_per_particle)
    # Echo a short index to stdout
    print("Best selections:")
    for name, rec in best.items():
        print(
            f"- {name}: run_dir={rec['run_dir']}, "
            f"freq={rec['summary'].get('probe_dominant_frequency'):.4f}, "
            f"radius={rec['summary'].get('effective_radius'):.3f}, "
            f"peak/mean={rec['summary'].get('final_peak_to_mean_ratio'):.3f}"
        )
    print(f"\nResults saved to: {outdir}")


if __name__ == "__main__":
    main()
