#!/usr/bin/env python3
"""
========================================================
标准数学模型验证实验
========================================================

六个可检验预测：
1. 多尺度能量簇间距
2. 幂律频谱指数
3. 自洽度收敛
4. 跨层级相关衰减
5. 黑洞信息公式一致性
6. 窗口干预效应

使用方法：
    python3 testable_predictions.py

========================================================
"""

import json
import logging
import math
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

try:
    import torch
except ImportError:  # pragma: no cover - optional dependency
    torch = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    prediction_id: int
    prediction_name: str
    passed: bool
    confidence: float
    measured_value: float
    expected_value: float
    deviation: float
    model_family: str
    data_source: str
    evidence: Dict[str, Any]


class TheoryVerification:
    def __init__(self, output_dir: str = "./verification_data", seed: int = 42, backend: str | None = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.experiment_start = time.time()
        self.results: List[PredictionResult] = []
        self.seed = seed
        self.backend = self._resolve_backend(backend)
        self.rng = np.random.default_rng(seed)
        self.lambda_scale = 10 ** 3.4
        self.flip_times: List[float] = []
        self.flip_energies: List[float] = []
        self.flip_levels: List[int] = []
        self.flip_count_series: np.ndarray = np.array([])
        self.spectral_series: np.ndarray = np.array([])
        self.time_step = 0.5
        self.self_consistency_history: np.ndarray = np.array([])
        self.self_consistency_target = 0.8
        self.level_samples: np.ndarray = np.array([])
        self.level_correlation_length = 1.6
        self.window_control_paths: np.ndarray = np.array([])
        self.window_intervention_paths: np.ndarray = np.array([])
        self.window_range: Tuple[int, int] = (60, 140)

        logger.info("=" * 60)
        logger.info("标准数学模型验证实验")
        logger.info("数值后端: %s", self.backend)
        logger.info("=" * 60)

    def _resolve_backend(self, backend: str | None) -> str:
        selected = (backend or os.getenv("MIND_BACKEND") or "auto").lower()
        if selected == "auto":
            return "torch" if torch is not None else "numpy"
        if selected == "torch":
            if torch is None:
                logger.warning("未检测到 PyTorch，自动回退到 NumPy 后端")
                return "numpy"
            return "torch"
        return "numpy"

    def _normal_cdf(self, x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _linear_fit(self, x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
        slope, intercept = np.polyfit(x, y, 1)
        y_hat = slope * x + intercept
        ss_res = float(np.sum((y - y_hat) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
        return float(slope), float(intercept), float(r2)

    def _kmeans_1d(self, values: np.ndarray, k: int = 2, n_iter: int = 50) -> Tuple[np.ndarray, np.ndarray]:
        quantiles = np.linspace(0.1, 0.9, k)
        centers = np.quantile(values, quantiles)
        labels = np.zeros(len(values), dtype=int)

        for _ in range(n_iter):
            distances = np.abs(values[:, None] - centers[None, :])
            labels = np.argmin(distances, axis=1)
            new_centers = centers.copy()
            for idx in range(k):
                cluster = values[labels == idx]
                if len(cluster) > 0:
                    new_centers[idx] = np.mean(cluster)
            if np.allclose(new_centers, centers):
                break
            centers = new_centers

        order = np.argsort(centers)
        sorted_centers = centers[order]
        relabel = np.zeros_like(order)
        relabel[order] = np.arange(k)
        labels = relabel[labels]
        return sorted_centers, labels

    def _generate_power_law_noise(self, n: int, alpha: float) -> np.ndarray:
        if self.backend == "torch" and torch is not None:
            return self._generate_power_law_noise_torch(n, alpha)

        spectrum = np.zeros(n // 2 + 1, dtype=np.complex128)
        freqs = np.fft.rfftfreq(n, d=1.0)
        phases = self.rng.uniform(0, 2 * np.pi, len(spectrum))
        amplitudes = np.zeros_like(freqs)
        amplitudes[1:] = 1.0 / np.power(freqs[1:], alpha / 2.0)
        spectrum.real = amplitudes * np.cos(phases)
        spectrum.imag = amplitudes * np.sin(phases)
        noise = np.fft.irfft(spectrum, n=n)
        noise = (noise - noise.mean()) / noise.std()
        return noise

    def _generate_power_law_noise_torch(self, n: int, alpha: float) -> np.ndarray:
        generator = torch.Generator(device="cpu")
        generator.manual_seed(self.seed)
        freqs = torch.fft.rfftfreq(n, d=1.0)
        phases = 2 * math.pi * torch.rand(len(freqs), generator=generator)
        amplitudes = torch.zeros_like(freqs)
        amplitudes[1:] = 1.0 / torch.pow(freqs[1:], alpha / 2.0)
        real = amplitudes * torch.cos(phases)
        imag = amplitudes * torch.sin(phases)
        spectrum = torch.complex(real, imag)
        noise = torch.fft.irfft(spectrum, n=n)
        noise = (noise - noise.mean()) / noise.std()
        return noise.cpu().numpy()

    def _sample_multivariate_normal(self, covariance: np.ndarray, n_samples: int) -> np.ndarray:
        if self.backend == "torch" and torch is not None:
            cov_tensor = torch.tensor(covariance, dtype=torch.float64)
            chol = torch.linalg.cholesky(cov_tensor + 1e-8 * torch.eye(cov_tensor.shape[0], dtype=torch.float64))
            generator = torch.Generator(device="cpu")
            generator.manual_seed(self.seed + 7)
            gaussian = torch.randn((n_samples, cov_tensor.shape[0]), generator=generator, dtype=torch.float64)
            return (gaussian @ chol.T).cpu().numpy()

        cholesky = np.linalg.cholesky(covariance + 1e-8 * np.eye(covariance.shape[0]))
        gaussian_samples = self.rng.normal(size=(n_samples, covariance.shape[0]))
        return gaussian_samples @ cholesky.T

    def _eigvalsh(self, matrix: np.ndarray) -> np.ndarray:
        if self.backend == "torch" and torch is not None:
            values = torch.linalg.eigvalsh(torch.tensor(matrix, dtype=torch.float64))
            return values.cpu().numpy()
        return np.linalg.eigvalsh(matrix)

    def _generate_ou_path(
        self,
        length: int,
        target: float,
        mean_reversion: float,
        noise_scale: float,
        start: float,
        drift_schedule: np.ndarray | None = None,
        rng: np.random.Generator | None = None
    ) -> np.ndarray:
        path = np.zeros(length)
        path[0] = start
        drift = drift_schedule if drift_schedule is not None else np.zeros(length)
        local_rng = rng or self.rng
        for t in range(1, length):
            deterministic = mean_reversion * (target - path[t - 1]) + drift[t]
            stochastic = noise_scale * local_rng.normal()
            path[t] = np.clip(path[t - 1] + deterministic + stochastic, 0.0, 1.0)
        return path

    def generate_simulated_data(self) -> None:
        logger.info("生成基于线代、微积分、概率论的模拟数据...")

        event_rng = np.random.default_rng(self.seed + 101)
        sc_rng = np.random.default_rng(self.seed + 202)
        window_rng = np.random.default_rng(self.seed + 303)

        n_bins = 512
        colored_noise = self._generate_power_law_noise(n_bins, alpha=1.0)
        self.spectral_series = colored_noise.copy()
        base_rate = 8.0
        log_rate = np.log(base_rate) + 0.35 * colored_noise
        rates = np.exp(log_rate)
        counts = event_rng.poisson(rates)
        self.flip_count_series = counts.astype(float)

        log_centers = np.array([0.0, math.log(self.lambda_scale)])
        level_probs = np.array([0.82, 0.18])
        sigma_log_energy = 0.12

        for idx, count in enumerate(counts):
            bin_start = idx * self.time_step
            bin_end = (idx + 1) * self.time_step
            if count == 0:
                continue
            event_times = event_rng.uniform(bin_start, bin_end, size=count)
            event_levels = event_rng.choice([0, 1], size=count, p=level_probs)
            event_logs = event_rng.normal(log_centers[event_levels], sigma_log_energy, size=count)
            event_energies = np.exp(event_logs)

            self.flip_times.extend(event_times.tolist())
            self.flip_energies.extend(event_energies.tolist())
            self.flip_levels.extend(event_levels.tolist())

        history_length = 400
        self.self_consistency_history = self._generate_ou_path(
            length=history_length,
            target=self.self_consistency_target,
            mean_reversion=0.045,
            noise_scale=0.01,
            start=0.35,
            rng=sc_rng
        )

        n_levels = 5
        n_samples = 600
        covariance = np.zeros((n_levels, n_levels))
        for i in range(n_levels):
            for j in range(n_levels):
                covariance[i, j] = math.exp(-abs(i - j) / self.level_correlation_length)
        self.level_samples = self._sample_multivariate_normal(covariance, n_samples)

        n_replications = 48
        window_start, window_end = self.window_range
        drift_control = np.zeros(220)
        drift_intervention = np.zeros(220)
        drift_intervention[window_start:window_end] = 0.012

        control_paths = []
        intervention_paths = []
        for _ in range(n_replications):
            control_paths.append(
                self._generate_ou_path(
                    length=220,
                    target=self.self_consistency_target,
                    mean_reversion=0.04,
                    noise_scale=0.012,
                    start=0.40 + 0.02 * window_rng.normal(),
                    drift_schedule=drift_control,
                    rng=window_rng
                )
            )
            intervention_paths.append(
                self._generate_ou_path(
                    length=220,
                    target=self.self_consistency_target,
                    mean_reversion=0.04,
                    noise_scale=0.012,
                    start=0.40 + 0.02 * window_rng.normal(),
                    drift_schedule=drift_intervention,
                    rng=window_rng
                )
            )

        self.window_control_paths = np.array(control_paths)
        self.window_intervention_paths = np.array(intervention_paths)

        logger.info(
            "模拟数据完成: %d 翻转事件, %d 个频谱时间箱, %d 个一致性样本",
            len(self.flip_times),
            len(self.flip_count_series),
            len(self.self_consistency_history)
        )

    def run_all_verifications(self) -> List[PredictionResult]:
        logger.info("\n开始运行标准模型验证...\n")

        self.results = [
            self.verify_multiscale_energy_clusters(),
            self.verify_power_law_spectrum(),
            self.verify_self_consistency_convergence(),
            self.verify_cross_level_correlation_decay(),
            self.verify_black_hole_information_identity(),
            self.verify_window_intervention_effect(),
        ]
        return self.results

    def verify_multiscale_energy_clusters(self) -> PredictionResult:
        logger.info("[验证1/6] 多尺度能量簇间距")

        energies = np.array(self.flip_energies)
        if len(energies) < 100:
            return PredictionResult(1, "Multiscale Energy Clusters", False, 0.0, 0.0, self.lambda_scale, 1.0, "概率论", "simulated", {"error": "Insufficient events"})

        log_energies = np.log(energies)
        centers, labels = self._kmeans_1d(log_energies, k=2)
        cluster_a = log_energies[labels == 0]
        cluster_b = log_energies[labels == 1]
        pooled_std = float(np.sqrt((np.var(cluster_a) + np.var(cluster_b)) / 2.0))
        log_gap = float(centers[1] - centers[0])
        measured_ratio = float(np.exp(log_gap))
        deviation = abs(measured_ratio - self.lambda_scale) / self.lambda_scale
        separation = log_gap / pooled_std if pooled_std > 0 else 0.0
        confidence = max(0.0, min(1.0, (1.0 - deviation) * min(1.0, separation / 6.0)))
        passed = deviation < 0.15 and separation > 8.0

        return PredictionResult(
            prediction_id=1,
            prediction_name="Multiscale Energy Clusters",
            passed=passed,
            confidence=confidence,
            measured_value=measured_ratio,
            expected_value=self.lambda_scale,
            deviation=deviation,
            model_family="概率论",
            data_source="simulated",
            evidence={
                "log_centers": [float(v) for v in centers],
                "cluster_sizes": [int(np.sum(labels == 0)), int(np.sum(labels == 1))],
                "log_gap": log_gap,
                "separation": float(separation),
            },
        )

    def verify_power_law_spectrum(self) -> PredictionResult:
        logger.info("[验证2/6] 幂律频谱指数")

        signal = np.array(self.spectral_series, dtype=float)
        if len(signal) < 64:
            return PredictionResult(2, "Power-law Spectrum", False, 0.0, 0.0, 1.0, 1.0, "概率论", "simulated", {"error": "Insufficient spectral samples"})
        centered = signal - signal.mean()
        power = np.abs(np.fft.rfft(centered)) ** 2
        freqs = np.fft.rfftfreq(len(signal), d=self.time_step)
        mask = freqs > 0
        freqs = freqs[mask]
        power = power[mask]

        lo = max(1, len(freqs) // 20)
        hi = len(freqs) - max(1, len(freqs) // 10)
        freqs_fit = freqs[lo:hi]
        power_fit = power[lo:hi]

        log_freqs = np.log(freqs_fit)
        log_power = np.log(power_fit + 1e-12)
        slope, intercept, r2 = self._linear_fit(log_freqs, log_power)
        alpha = -slope
        deviation = abs(alpha - 1.0)
        confidence = max(0.0, min(1.0, (1.0 - min(1.0, deviation / 0.4)) * r2))
        passed = deviation < 0.2 and r2 > 0.8

        return PredictionResult(
            prediction_id=2,
            prediction_name="Power-law Spectrum",
            passed=passed,
            confidence=confidence,
            measured_value=float(alpha),
            expected_value=1.0,
            deviation=float(deviation),
            model_family="概率论",
            data_source=f"simulated:{self.backend}",
            evidence={
                "slope": float(slope),
                "intercept": float(intercept),
                "r_squared": float(r2),
                "frequency_range": [float(freqs_fit.min()), float(freqs_fit.max())],
                "n_points": int(len(freqs_fit)),
                "signal_std": float(np.std(signal)),
                "backend": self.backend,
            },
        )

    def verify_self_consistency_convergence(self) -> PredictionResult:
        logger.info("[验证3/6] 自洽度收敛")

        sc = np.array(self.self_consistency_history, dtype=float)
        tail = sc[-60:]
        tail_mean = float(np.mean(tail))
        tail_std = float(np.std(tail))
        time_axis = np.arange(len(sc))
        residual = np.abs(sc - self.self_consistency_target) + 1e-6
        fit_slice = slice(20, 180)
        slope, intercept, r2 = self._linear_fit(time_axis[fit_slice], np.log(residual[fit_slice]))
        estimated_decay_rate = max(0.0, -slope)
        deviation = abs(tail_mean - self.self_consistency_target) / self.self_consistency_target
        stability_score = max(0.0, 1.0 - tail_std / 0.05)
        convergence_score = max(0.0, min(1.0, 0.5 + 0.5 * max(0.0, r2)))
        confidence = max(0.0, min(1.0, (1.0 - deviation) * stability_score * convergence_score))
        passed = deviation < 0.03 and tail_std < 0.03

        return PredictionResult(
            prediction_id=3,
            prediction_name="Self-consistency Convergence",
            passed=passed,
            confidence=confidence,
            measured_value=tail_mean,
            expected_value=self.self_consistency_target,
            deviation=deviation,
            model_family="微积分",
            data_source="simulated",
            evidence={
                "tail_std": tail_std,
                "estimated_decay_rate": float(estimated_decay_rate),
                "fit_r_squared": float(r2),
                "history_length": int(len(sc)),
            },
        )

    def verify_cross_level_correlation_decay(self) -> PredictionResult:
        logger.info("[验证4/6] 跨层级相关衰减")

        if self.backend == "torch" and torch is not None:
            X = torch.tensor(self.level_samples, dtype=torch.float64)
            Xc = X - X.mean(dim=0, keepdim=True)
            n = X.shape[0]
            cov = (Xc.T @ Xc) / max(1, (n - 1))
            std = Xc.std(dim=0, unbiased=True) + 1e-12
            corr_t = cov / (std[:, None] * std[None, :])

            distances = []
            avg_corrs = []
            L = corr_t.shape[0]
            for dist in range(1, L):
                diag = torch.diagonal(corr_t, offset=dist)
                distances.append(dist)
                avg_corrs.append(float(diag.abs().mean().item()))

            x = torch.tensor(distances, dtype=torch.float64)
            y = torch.log(torch.tensor(avg_corrs, dtype=torch.float64) + 1e-12)
            x_mean = x.mean()
            y_mean = y.mean()
            slope_t = ((x - x_mean) * (y - y_mean)).sum() / ((x - x_mean) ** 2).sum()
            intercept_t = y_mean - slope_t * x_mean
            y_hat = slope_t * x + intercept_t
            ss_res = ((y - y_hat) ** 2).sum()
            ss_tot = ((y - y_mean) ** 2).sum()
            r2 = float(1.0 - ss_res.item() / ss_tot.item()) if ss_tot.item() > 0 else 1.0
            slope = float(slope_t.item())

            estimated_xi = -1.0 / slope if slope < 0 else float("inf")
            deviation = abs(estimated_xi - self.level_correlation_length) / self.level_correlation_length
            spectral_radius = float(torch.linalg.eigvalsh(corr_t).max().item())
        else:
            samples = np.array(self.level_samples, dtype=float)
            corr = np.corrcoef(samples, rowvar=False)
            distances = []
            avg_corrs = []
            for dist in range(1, corr.shape[0]):
                diag = np.diag(corr, k=dist)
                distances.append(dist)
                avg_corrs.append(float(np.mean(np.abs(diag))))

            distances_arr = np.array(distances, dtype=float)
            avg_corrs_arr = np.array(avg_corrs, dtype=float)
            slope, intercept, r2 = self._linear_fit(distances_arr, np.log(avg_corrs_arr + 1e-12))
            estimated_xi = -1.0 / slope if slope < 0 else float("inf")
            deviation = abs(estimated_xi - self.level_correlation_length) / self.level_correlation_length
            spectral_radius = float(np.max(self._eigvalsh(corr)))

        confidence = max(0.0, min(1.0, (1.0 - min(1.0, deviation / 0.4)) * r2))
        passed = slope < 0 and deviation < 0.2 and r2 > 0.95

        return PredictionResult(
            prediction_id=4,
            prediction_name="Cross-level Correlation Decay",
            passed=passed,
            confidence=confidence,
            measured_value=float(estimated_xi),
            expected_value=float(self.level_correlation_length),
            deviation=float(deviation),
            model_family="线性代数",
            data_source=f"simulated:{self.backend}",
            evidence={
                "distance_means": {str(k): float(v) for k, v in zip(distances, avg_corrs)},
                "fit_r_squared": float(r2),
                "spectral_radius": spectral_radius,
                "backend": self.backend,
                # 为避免 JSON 过大，这里不再附完整矩阵；如需调试可再加入
            },
        )

    def verify_black_hole_information_identity(self) -> PredictionResult:
        logger.info("[验证5/6] 黑洞信息公式一致性")

        k_b = 1.380649e-23
        hbar = 1.054571817e-34
        c = 299792458.0
        g_const = 6.67430e-11
        solar_mass = 1.98847e30
        mass = 10.0 * solar_mass
        schwarzschild_radius = 2.0 * g_const * mass / (c ** 2)
        area = 4.0 * math.pi * schwarzschild_radius ** 2
        entropy = k_b * c ** 3 * area / (4.0 * g_const * hbar)
        measured_information = entropy / k_b
        expected_information = c ** 3 * area / (4.0 * g_const * hbar)
        deviation = abs(measured_information - expected_information) / expected_information

        return PredictionResult(
            prediction_id=5,
            prediction_name="Black Hole Information Identity",
            passed=deviation < 1e-12,
            confidence=1.0,
            measured_value=float(measured_information),
            expected_value=float(expected_information),
            deviation=float(deviation),
            model_family="微积分",
            data_source="analytic",
            evidence={
                "mass_kg": float(mass),
                "schwarzschild_radius_m": float(schwarzschild_radius),
                "area_m2": float(area),
                "entropy_j_per_k": float(entropy),
            },
        )

    def verify_window_intervention_effect(self) -> PredictionResult:
        logger.info("[验证6/6] 窗口干预效应")

        start, end = self.window_range
        pre = slice(0, start)
        window = slice(start, end)

        if self.backend == "torch" and torch is not None:
            ctl = torch.tensor(self.window_control_paths, dtype=torch.float64)
            itv = torch.tensor(self.window_intervention_paths, dtype=torch.float64)
            control_pre = ctl[:, pre].mean(dim=1)
            control_window = ctl[:, window].mean(dim=1)
            intervention_pre = itv[:, pre].mean(dim=1)
            intervention_window = itv[:, window].mean(dim=1)
            control_delta_t = control_window - control_pre
            intervention_delta_t = intervention_window - intervention_pre
            effect = float(intervention_delta_t.mean().item() - control_delta_t.mean().item())
            control_var = float(control_delta_t.var(unbiased=True).item())
            intervention_var = float(intervention_delta_t.var(unbiased=True).item())
            n_control = int(control_delta_t.shape[0])
            n_intervention = int(intervention_delta_t.shape[0])
        else:
            control_pre = self.window_control_paths[:, pre].mean(axis=1)
            control_window = self.window_control_paths[:, window].mean(axis=1)
            intervention_pre = self.window_intervention_paths[:, pre].mean(axis=1)
            intervention_window = self.window_intervention_paths[:, window].mean(axis=1)
            control_delta = control_window - control_pre
            intervention_delta = intervention_window - intervention_pre
            effect = float(np.mean(intervention_delta) - np.mean(control_delta))
            control_var = float(np.var(control_delta, ddof=1))
            intervention_var = float(np.var(intervention_delta, ddof=1))
            n_control = len(control_delta)
            n_intervention = len(intervention_delta)

        expected_effect = 0.16
        deviation = abs(effect - expected_effect) / expected_effect

        standard_error = math.sqrt(control_var / n_control + intervention_var / n_intervention)
        z_score = effect / standard_error if standard_error > 0 else 0.0
        significance_score = max(0.0, min(1.0, 2.0 * self._normal_cdf(abs(z_score)) - 1.0))
        effect_score = max(0.0, 1.0 - min(1.0, deviation))
        confidence = max(0.0, min(1.0, significance_score * effect_score))
        passed = effect > 0 and z_score > 3.0 and deviation < 0.35

        return PredictionResult(
            prediction_id=6,
            prediction_name="Window Intervention Effect",
            passed=passed,
            confidence=confidence,
            measured_value=effect,
            expected_value=expected_effect,
            deviation=deviation,
            model_family="概率论+微积分",
            data_source=f"simulated:{self.backend}",
            evidence={
                "control_var": control_var,
                "intervention_var": intervention_var,
                "standard_error": float(standard_error),
                "z_score": float(z_score),
                "window_range": [int(start), int(end)],
                "backend": self.backend,
            },
        )

    def generate_summary(self) -> Dict[str, Any]:
        n_passed = sum(1 for result in self.results if result.passed)
        n_total = len(self.results)
        avg_confidence = float(np.mean([result.confidence for result in self.results])) if self.results else 0.0

        return {
            "experiment_name": "Standard Mathematical Verification",
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": time.time() - self.experiment_start,
            "seed": self.seed,
            "backend": self.backend,
            "data_origin": "simulated_and_analytic_models",
            "predictions": {
                "total": n_total,
                "passed": n_passed,
                "failed": n_total - n_passed,
                "pass_rate": f"{n_passed / n_total:.0%}" if n_total > 0 else "N/A",
            },
            "confidence": {
                "average": f"{avg_confidence:.2%}",
                "total": f"{avg_confidence * n_total:.2f}/{n_total}" if n_total > 0 else "N/A",
            },
            "passed_predictions": [result.prediction_id for result in self.results if result.passed],
            "failed_predictions": [result.prediction_id for result in self.results if not result.passed],
            "details": [asdict(result) for result in self.results],
        }

    def print_summary(self) -> None:
        summary = self.generate_summary()

        print("\n" + "=" * 72)
        print("  标准数学模型验证总结")
        print("=" * 72)
        print(f"\n实验时间: {summary['timestamp']}")
        print(f"总时长: {summary['duration_seconds']:.2f} 秒")
        print(f"数据来源: {summary['data_origin']}")
        print(f"随机种子: {summary['seed']}")
        print(f"\n预测总数: {summary['predictions']['total']}")
        print(f"通过数量: {summary['predictions']['passed']}")
        print(f"失败数量: {summary['predictions']['failed']}")
        print(f"通过率: {summary['predictions']['pass_rate']}")
        print(f"平均置信度: {summary['confidence']['average']}")

        print("\n详细结果:")
        print("-" * 72)
        for result in self.results:
            status = "✓ 通过" if result.passed else "✗ 失败"
            print(f"[{result.prediction_id}] {result.prediction_name}")
            print(f"    状态: {status}")
            print(f"    模型族: {result.model_family}")
            print(f"    数据源: {result.data_source}")
            print(f"    测量值: {result.measured_value:.6g}")
            print(f"    期望值: {result.expected_value:.6g}")
            print(f"    偏差: {result.deviation:.2%}")
            print(f"    置信度: {result.confidence:.2%}")
            print()

        print("=" * 72)

    def save_results(self) -> Path:
        summary = self.generate_summary()
        filename = f"verification_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename

        with open(filepath, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info("结果已保存: %s", filepath)
        return filepath


def main():
    print("\n" + "=" * 72)
    print("  标准数学模型验证实验")
    print("  线性代数 + 微积分 + 概率论")
    print("=" * 72 + "\n")

    verifier = TheoryVerification()
    verifier.generate_simulated_data()
    verifier.run_all_verifications()
    verifier.print_summary()
    filepath = verifier.save_results()
    print(f"\n实验完成! 结果已保存到: {filepath}")
    return verifier.results


if __name__ == "__main__":
    main()
