#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from csde_data_schema import TriadCoreState
from csde_triad_dynamics import _triad_edge_complex


@dataclass(frozen=True)
class TriadQuantumConfig:
    hbar_eff: float = 1.0
    onsite_gain: float = 1.0
    connector_onsite_gain: float = 1.0
    edge_coupling_gain: float = 0.35
    connector_coupling_gain: float = 0.28
    connector_bias_gain: float = 0.12

    def to_params(self) -> dict[str, float]:
        return {key: float(value) for key, value in asdict(self).items()}

    @classmethod
    def from_params(cls, params: dict[str, float] | None = None) -> "TriadQuantumConfig":
        if not params:
            return cls()
        defaults = cls().to_params()
        defaults.update({key: float(value) for key, value in params.items()})
        return cls(**defaults)


@dataclass
class TriadQuantumState:
    id: str
    basis_labels: list[str]
    psi_real: list[float]
    psi_imag: list[float]
    hamiltonian_real: list[list[float]]
    hamiltonian_imag: list[list[float]]
    active: bool = True
    extras: dict[str, object] = field(default_factory=dict)

    def psi(self) -> np.ndarray:
        real = np.asarray(self.psi_real, dtype=np.float64)
        imag = np.asarray(self.psi_imag, dtype=np.float64)
        return real + 1j * imag

    def hamiltonian(self) -> np.ndarray:
        real = np.asarray(self.hamiltonian_real, dtype=np.float64)
        imag = np.asarray(self.hamiltonian_imag, dtype=np.float64)
        return real + 1j * imag


def normalize_quantum_state_vector(psi: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(psi))
    if norm < 1e-12:
        raise ValueError("Quantum state vector norm is zero.")
    return psi / norm


def hermitian_error(hamiltonian: np.ndarray) -> float:
    return float(np.max(np.abs(hamiltonian - hamiltonian.conj().T)))


def assert_hermitian(hamiltonian: np.ndarray, atol: float = 1e-9) -> None:
    error = hermitian_error(hamiltonian)
    if error > atol:
        raise ValueError(f"Hamiltonian is not Hermitian within tolerance: error={error:.3e}")


def build_triad_hamiltonian(
    state: TriadCoreState,
    params: dict[str, float] | TriadQuantumConfig | None = None,
) -> np.ndarray:
    cfg = params if isinstance(params, TriadQuantumConfig) else TriadQuantumConfig.from_params(params)
    hamiltonian = np.zeros((4, 4), dtype=np.complex128)

    node_freq = np.asarray(state.node_freq, dtype=np.float64)
    node_duty = np.asarray(state.node_duty, dtype=np.float64)
    node_phase = np.asarray(state.node_phase, dtype=np.float64)
    edge_values = _triad_edge_complex(state)
    connector_phase = float(state.connector_phase)
    connector_freq = float(state.connector_freq)
    connector_strength = max(0.0, float(state.connector_strength))

    for idx in range(3):
        hamiltonian[idx, idx] = cfg.onsite_gain * node_freq[idx]
    hamiltonian[3, 3] = cfg.connector_onsite_gain * connector_freq

    for edge_idx, (i, j) in enumerate(((0, 1), (1, 2), (2, 0))):
        coupling = cfg.edge_coupling_gain * complex(edge_values[edge_idx])
        hamiltonian[i, j] = coupling
        hamiltonian[j, i] = np.conjugate(coupling)

    connector_amp = np.sqrt(connector_strength + 1e-12)
    for idx in range(3):
        local_amp = np.sqrt(max(node_duty[idx], 0.0))
        phase_delta = 0.5 * (connector_phase - node_phase[idx])
        coupling_mag = cfg.connector_coupling_gain * connector_amp * local_amp + cfg.connector_bias_gain * connector_strength
        coupling = coupling_mag * np.exp(1j * phase_delta)
        hamiltonian[idx, 3] = coupling
        hamiltonian[3, idx] = np.conjugate(coupling)

    assert_hermitian(hamiltonian)
    return hamiltonian


def build_quantum_state_from_triad_core(
    state: TriadCoreState,
    params: dict[str, float] | TriadQuantumConfig | None = None,
) -> TriadQuantumState:
    cfg = params if isinstance(params, TriadQuantumConfig) else TriadQuantumConfig.from_params(params)
    node_weights = np.clip(np.asarray(state.node_duty, dtype=np.float64), 0.0, None)
    connector_weight = max(0.0, float(state.connector_strength))
    amplitudes = np.sqrt(np.concatenate([node_weights, np.asarray([connector_weight], dtype=np.float64)]))
    phases = np.asarray([*state.node_phase, float(state.connector_phase)], dtype=np.float64)
    psi = amplitudes * np.exp(1j * phases)
    psi = normalize_quantum_state_vector(psi)
    hamiltonian = build_triad_hamiltonian(state, cfg)
    return TriadQuantumState(
        id=state.id,
        basis_labels=["node_0", "node_1", "node_2", "connector"],
        psi_real=np.real(psi).astype(np.float64).tolist(),
        psi_imag=np.imag(psi).astype(np.float64).tolist(),
        hamiltonian_real=np.real(hamiltonian).astype(np.float64).tolist(),
        hamiltonian_imag=np.imag(hamiltonian).astype(np.float64).tolist(),
        active=state.active,
        extras={
            "hbar_eff": cfg.hbar_eff,
            "source_triad_id": state.id,
            "source_connector_strength": float(state.connector_strength),
        },
    )


def quantum_step_unitary(
    state: TriadQuantumState,
    dt: float,
    *,
    hbar_eff: float | None = None,
) -> tuple[TriadQuantumState, dict[str, object]]:
    if dt <= 0.0:
        raise ValueError("dt must be positive.")
    psi = state.psi()
    hamiltonian = state.hamiltonian()
    assert_hermitian(hamiltonian)
    hbar = float(hbar_eff if hbar_eff is not None else state.extras.get("hbar_eff", 1.0))
    if hbar <= 0.0:
        raise ValueError("hbar_eff must be positive.")

    eigenvalues, eigenvectors = np.linalg.eigh(hamiltonian)
    unitary = eigenvectors @ np.diag(np.exp(-1j * eigenvalues * dt / hbar)) @ eigenvectors.conj().T
    psi_next = normalize_quantum_state_vector(unitary @ psi)

    next_state = TriadQuantumState(
        id=state.id,
        basis_labels=list(state.basis_labels),
        psi_real=np.real(psi_next).astype(np.float64).tolist(),
        psi_imag=np.imag(psi_next).astype(np.float64).tolist(),
        hamiltonian_real=np.real(hamiltonian).astype(np.float64).tolist(),
        hamiltonian_imag=np.imag(hamiltonian).astype(np.float64).tolist(),
        active=state.active,
        extras=dict(state.extras),
    )
    diagnostics = {
        "hbar_eff": hbar,
        "norm_before": float(np.vdot(psi, psi).real),
        "norm_after": float(np.vdot(psi_next, psi_next).real),
        "hermitian_error": hermitian_error(hamiltonian),
        "eigenvalues": np.real(eigenvalues).astype(np.float64).tolist(),
    }
    return next_state, diagnostics


def simulate_quantum_state(
    initial_state: TriadQuantumState,
    step_count: int,
    dt: float,
    *,
    hbar_eff: float | None = None,
) -> tuple[list[TriadQuantumState], list[dict[str, object]]]:
    if step_count < 0:
        raise ValueError("step_count must be non-negative.")
    states = [initial_state]
    diagnostics_history: list[dict[str, object]] = []
    current_state = initial_state
    for _ in range(step_count):
        current_state, diagnostics = quantum_step_unitary(current_state, dt, hbar_eff=hbar_eff)
        states.append(current_state)
        diagnostics_history.append(diagnostics)
    return states, diagnostics_history
