#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


EPSILON = 1e-6


def normalize_vector(vec: np.ndarray, fallback: np.ndarray | None = None) -> np.ndarray:
    arr = np.asarray(vec, dtype=np.float64)
    norm = float(np.linalg.norm(arr))
    if norm > EPSILON:
        return arr / norm
    if fallback is not None:
        fallback_arr = np.asarray(fallback, dtype=np.float64)
        fallback_norm = float(np.linalg.norm(fallback_arr))
        if fallback_norm > EPSILON:
            return fallback_arr / fallback_norm
    return np.array([1.0, 0.0, 0.0], dtype=np.float64)


def orthonormalize_basis(seed_basis: np.ndarray) -> np.ndarray:
    basis = np.asarray(seed_basis, dtype=np.float64)
    if basis.shape != (3, 3):
        raise ValueError(f"seed_basis must have shape (3, 3), got {basis.shape}")

    b0 = normalize_vector(basis[0], fallback=np.array([1.0, 0.0, 0.0], dtype=np.float64))
    raw_b1 = basis[1] - float(np.dot(basis[1], b0)) * b0
    b1 = normalize_vector(raw_b1, fallback=np.array([0.0, 1.0, 0.0], dtype=np.float64))
    if abs(float(np.dot(b0, b1))) > 0.98:
        ref = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        if abs(float(np.dot(b0, ref))) > 0.95:
            ref = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        b1 = normalize_vector(np.cross(ref, b0), fallback=np.array([0.0, 1.0, 0.0], dtype=np.float64))
    b2 = normalize_vector(np.cross(b0, b1), fallback=np.array([0.0, 0.0, 1.0], dtype=np.float64))
    b1 = normalize_vector(np.cross(b2, b0), fallback=b1)
    return np.vstack([b0, b1, b2])


def smoothstep01(value: float) -> float:
    x = float(np.clip(value, 0.0, 1.0))
    return x * x * (3.0 - 2.0 * x)


def phase_from_time(time_value: float, frequency: float, phase_offset: float = 0.0) -> float:
    return 2.0 * math.pi * float(frequency) * float(time_value) + float(phase_offset)


def phase_coupled_primary_axis(
    seed_basis: np.ndarray,
    phase: float,
    sweep_gain: float = 0.9,
    lift_gain: float = 0.32,
    torsion_phase: float = math.pi / 4.0,
) -> tuple[np.ndarray, float, float]:
    basis = orthonormalize_basis(seed_basis)
    alpha = float(sweep_gain) * math.sin(float(phase))
    beta = float(lift_gain) * math.sin(2.0 * float(phase) + float(torsion_phase))
    vector = (
        math.cos(alpha) * math.cos(beta) * basis[0]
        + math.sin(alpha) * math.cos(beta) * basis[1]
        + math.sin(beta) * basis[2]
    )
    return normalize_vector(vector, fallback=basis[0]), alpha, beta


@dataclass(frozen=True)
class DimensionGenerationState:
    phase: float
    alpha: float
    beta: float
    n0: np.ndarray
    n1: np.ndarray
    n2: np.ndarray
    n0_strength: float
    n1_strength: float
    n2_strength: float
    tangential_speed: float
    stage: str


def build_dimension_frame(
    seed_basis: np.ndarray,
    phase: float,
    sweep_gain: float = 0.9,
    lift_gain: float = 0.32,
    torsion_phase: float = math.pi / 4.0,
    derivative_eps: float = 1e-3,
) -> DimensionGenerationState:
    basis = orthonormalize_basis(seed_basis)
    n0, alpha, beta = phase_coupled_primary_axis(
        basis,
        phase,
        sweep_gain=sweep_gain,
        lift_gain=lift_gain,
        torsion_phase=torsion_phase,
    )
    n0_plus, _, _ = phase_coupled_primary_axis(
        basis,
        phase + derivative_eps,
        sweep_gain=sweep_gain,
        lift_gain=lift_gain,
        torsion_phase=torsion_phase,
    )
    n0_minus, _, _ = phase_coupled_primary_axis(
        basis,
        phase - derivative_eps,
        sweep_gain=sweep_gain,
        lift_gain=lift_gain,
        torsion_phase=torsion_phase,
    )
    derivative = (n0_plus - n0_minus) / max(2.0 * derivative_eps, EPSILON)
    tangent = derivative - float(np.dot(derivative, n0)) * n0
    tangential_speed = float(np.linalg.norm(tangent))
    fallback_n1 = basis[1] - float(np.dot(basis[1], n0)) * n0
    n1 = normalize_vector(tangent, fallback=fallback_n1)
    n2 = normalize_vector(np.cross(n0, n1), fallback=basis[2])
    n1 = normalize_vector(np.cross(n2, n0), fallback=n1)

    speed_scale = max(abs(float(sweep_gain)) + 0.5 * abs(float(lift_gain)), EPSILON)
    n1_strength = smoothstep01(tangential_speed / speed_scale)
    lift_ratio = abs(math.sin(2.0 * float(phase) + float(torsion_phase)))
    n2_strength = n1_strength * smoothstep01(lift_ratio)
    stage = classify_dimension_stage(n1_strength, n2_strength)

    return DimensionGenerationState(
        phase=float(phase),
        alpha=float(alpha),
        beta=float(beta),
        n0=n0,
        n1=n1,
        n2=n2,
        n0_strength=1.0,
        n1_strength=float(n1_strength),
        n2_strength=float(n2_strength),
        tangential_speed=tangential_speed,
        stage=stage,
    )


def classify_dimension_stage(n1_strength: float, n2_strength: float) -> str:
    if n1_strength < 0.25:
        return "seed"
    if n2_strength < 0.25:
        return "planar"
    if n2_strength < 0.65:
        return "lift"
    return "closure"
