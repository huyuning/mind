#!/usr/bin/env python3
"""
意识选择滤波模型仿真

目标：
1. 生成一组“未来模态”，每个模态具有频率、相位和结构特征。
2. 定义多个不同的主体态（意识态）。
3. 计算意识选择滤波 K_Psi 以及对应的现实显现概率分布。
4. 保存结果到 verification_data/ 目录，并打印摘要。

理论对应：
    K_Psi^(n)(t) =
        (1 / Z_Psi)
        * exp(
            - (omega_n - omega_psi)^2 / (2 sigma_omega^2)
            - (1 - cos(phi_n - phi_psi)) / sigma_phi^2
            + beta * <Psi, z_n>
        )

    p_real^(n) ∝ p_prior^(n) * K_Psi^(n)
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np


@dataclass
class FutureMode:
    mode_id: int
    omega: float
    phi: float
    gamma: float
    sigma: float
    feature_vector: List[float]
    prior_probability: float


@dataclass
class SubjectState:
    name: str
    omega_psi: float
    phi_psi: float
    feature_vector: List[float]


def normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm <= 1e-12:
        return vec.copy()
    return vec / norm


def softmax(scores: np.ndarray) -> np.ndarray:
    shifted = scores - np.max(scores)
    exp_scores = np.exp(shifted)
    return exp_scores / np.sum(exp_scores)


def generate_future_modes(
    n_modes: int,
    feature_dim: int,
    rng: np.random.Generator,
) -> List[FutureMode]:
    raw_feature_vectors = rng.normal(size=(n_modes, feature_dim))
    normalized_features = np.array([normalize(v) for v in raw_feature_vectors])

    omegas = rng.uniform(0.6, 6.0, size=n_modes)
    phis = rng.uniform(-math.pi, math.pi, size=n_modes)
    gammas = rng.uniform(0.1, 1.0, size=n_modes)
    sigmas = rng.uniform(0.2, 1.0, size=n_modes)

    # 先验权重：让较低阻尼、较高稳定性的模态获得更大基线概率
    prior_scores = 0.5 * gammas + 0.8 * sigmas - 0.1 * np.abs(omegas - np.mean(omegas))
    priors = softmax(prior_scores)

    modes = []
    for idx in range(n_modes):
        modes.append(
            FutureMode(
                mode_id=idx,
                omega=float(omegas[idx]),
                phi=float(phis[idx]),
                gamma=float(gammas[idx]),
                sigma=float(sigmas[idx]),
                feature_vector=normalized_features[idx].tolist(),
                prior_probability=float(priors[idx]),
            )
        )
    return modes


def build_subject_states(feature_dim: int, rng: np.random.Generator) -> List[SubjectState]:
    base_vectors = np.array([normalize(v) for v in rng.normal(size=(4, feature_dim))])
    return [
        SubjectState(
            name="focused_low_frequency",
            omega_psi=1.2,
            phi_psi=0.2,
            feature_vector=base_vectors[0].tolist(),
        ),
        SubjectState(
            name="synchronous_mid_frequency",
            omega_psi=2.8,
            phi_psi=1.1,
            feature_vector=base_vectors[1].tolist(),
        ),
        SubjectState(
            name="high_tension_high_frequency",
            omega_psi=4.9,
            phi_psi=-0.7,
            feature_vector=base_vectors[2].tolist(),
        ),
        SubjectState(
            name="diffuse_open_state",
            omega_psi=3.5,
            phi_psi=2.4,
            feature_vector=base_vectors[3].tolist(),
        ),
    ]


def compute_filter_distribution(
    subject: SubjectState,
    modes: List[FutureMode],
    sigma_omega: float,
    sigma_phi: float,
    beta: float,
) -> Dict[str, object]:
    psi = normalize(np.array(subject.feature_vector, dtype=float))
    omegas = np.array([m.omega for m in modes], dtype=float)
    phis = np.array([m.phi for m in modes], dtype=float)
    priors = np.array([m.prior_probability for m in modes], dtype=float)
    features = np.array([m.feature_vector for m in modes], dtype=float)

    frequency_term = -((omegas - subject.omega_psi) ** 2) / (2.0 * sigma_omega**2)
    phase_term = -(1.0 - np.cos(phis - subject.phi_psi)) / (sigma_phi**2)
    match_term = beta * (features @ psi)

    raw_scores = frequency_term + phase_term + match_term
    filter_weights = softmax(raw_scores)

    posterior_unnormalized = priors * filter_weights
    posterior = posterior_unnormalized / posterior_unnormalized.sum()

    top_idx = np.argsort(posterior)[::-1][:5]
    top_modes = [
        {
            "mode_id": int(modes[i].mode_id),
            "probability": float(posterior[i]),
            "prior_probability": float(priors[i]),
            "filter_weight": float(filter_weights[i]),
            "omega": float(omegas[i]),
            "phi": float(phis[i]),
            "alignment": float(features[i] @ psi),
        }
        for i in top_idx
    ]

    entropy = float(-np.sum(posterior * np.log(posterior + 1e-12)))
    expected_omega = float(np.sum(posterior * omegas))

    return {
        "subject": asdict(subject),
        "parameters": {
            "sigma_omega": sigma_omega,
            "sigma_phi": sigma_phi,
            "beta": beta,
        },
        "summary": {
            "expected_frequency": expected_omega,
            "distribution_entropy": entropy,
            "max_probability": float(np.max(posterior)),
        },
        "top_modes": top_modes,
        "posterior_distribution": posterior.tolist(),
        "filter_weights": filter_weights.tolist(),
        "raw_scores": raw_scores.tolist(),
    }


def maybe_plot(
    results: List[Dict[str, object]],
    output_dir: Path,
) -> List[str]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return []

    saved_files = []
    for result in results:
        subject_name = result["subject"]["name"]
        posterior = np.array(result["posterior_distribution"], dtype=float)
        x = np.arange(len(posterior))
        top_modes = result["top_modes"]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(x, posterior, color="steelblue", alpha=0.8)
        ax.set_title(f"Future Mode Manifestation Distribution: {subject_name}")
        ax.set_xlabel("Mode index")
        ax.set_ylabel("Manifestation probability")

        for mode in top_modes[:3]:
            ax.annotate(
                f"m{mode['mode_id']}",
                (mode["mode_id"], mode["probability"]),
                xytext=(0, 5),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )

        plot_path = output_dir / f"consciousness_filter_{subject_name}.png"
        fig.tight_layout()
        fig.savefig(plot_path, dpi=150)
        plt.close(fig)
        saved_files.append(str(plot_path))

    return saved_files


def main() -> None:
    parser = argparse.ArgumentParser(description="意识选择滤波模型仿真")
    parser.add_argument("--modes", type=int, default=24, help="未来模态数量")
    parser.add_argument("--feature-dim", type=int, default=5, help="模态/主体特征维度")
    parser.add_argument("--sigma-omega", type=float, default=0.8, help="频率共振带宽")
    parser.add_argument("--sigma-phi", type=float, default=0.9, help="相位共振带宽")
    parser.add_argument("--beta", type=float, default=1.8, help="主体态匹配强度")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./verification_data"),
        help="输出目录",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="若安装 matplotlib，则输出每个主体态的概率分布图",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    modes = generate_future_modes(args.modes, args.feature_dim, rng)
    subjects = build_subject_states(args.feature_dim, rng)

    results = [
        compute_filter_distribution(
            subject=subject,
            modes=modes,
            sigma_omega=args.sigma_omega,
            sigma_phi=args.sigma_phi,
            beta=args.beta,
        )
        for subject in subjects
    ]

    output = {
        "experiment_name": "Consciousness Selection Filter Simulation",
        "timestamp": datetime.now().isoformat(),
        "seed": args.seed,
        "mode_count": args.modes,
        "feature_dim": args.feature_dim,
        "theory_formula": "K_Psi^(n) proportional to exp(freq resonance + phase locking + subject-mode alignment)",
        "future_modes": [asdict(mode) for mode in modes],
        "results": results,
    }

    plots = maybe_plot(results, args.output_dir) if args.plot else []
    if plots:
        output["plots"] = plots

    filename = args.output_dir / f"consciousness_filter_simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("=" * 72)
    print("意识选择滤波模型仿真")
    print("=" * 72)
    print(f"输出文件: {filename}")
    if plots:
        print(f"图像文件数: {len(plots)}")
    print()

    for result in results:
        summary = result["summary"]
        subject_name = result["subject"]["name"]
        print(f"[{subject_name}]")
        print(f"  期望频率: {summary['expected_frequency']:.3f}")
        print(f"  分布熵: {summary['distribution_entropy']:.3f}")
        print(f"  最大显现概率: {summary['max_probability']:.3f}")
        print("  Top modes:")
        for mode in result["top_modes"][:3]:
            print(
                "   "
                f" mode={mode['mode_id']:>2d} "
                f"p={mode['probability']:.4f} "
                f"prior={mode['prior_probability']:.4f} "
                f"K={mode['filter_weight']:.4f} "
                f"omega={mode['omega']:.3f} "
                f"align={mode['alignment']:.3f}"
            )
        print()


if __name__ == "__main__":
    main()
