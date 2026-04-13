#!/usr/bin/env python3
from __future__ import annotations

import numpy as np

from csde_quantum_core import TriadQuantumState


def compute_basis_probabilities(state: TriadQuantumState) -> dict[str, float]:
    psi = state.psi()
    probabilities = np.abs(psi) ** 2
    return {
        label: float(probability)
        for label, probability in zip(state.basis_labels, probabilities)
    }


def compute_basis_phases(state: TriadQuantumState) -> dict[str, float]:
    psi = state.psi()
    return {
        label: float(np.angle(amplitude))
        for label, amplitude in zip(state.basis_labels, psi)
    }


def compute_pair_coherences(state: TriadQuantumState) -> dict[str, float]:
    psi = state.psi()
    labels = list(state.basis_labels)
    coherences: dict[str, float] = {}
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            coherences[f"{labels[i]}->{labels[j]}"] = float(abs(psi[i] * np.conjugate(psi[j])))
    return coherences


def compute_connector_occupancy(state: TriadQuantumState) -> float:
    probabilities = compute_basis_probabilities(state)
    return float(probabilities.get("connector", 0.0))


def summarize_quantum_state(state: TriadQuantumState) -> dict[str, object]:
    probabilities = compute_basis_probabilities(state)
    phases = compute_basis_phases(state)
    coherences = compute_pair_coherences(state)
    psi = state.psi()
    return {
        "state_id": state.id,
        "norm": float(np.vdot(psi, psi).real),
        "probabilities": probabilities,
        "phases": phases,
        "pair_coherences": coherences,
        "connector_occupancy": float(probabilities.get("connector", 0.0)),
        "node_total_probability": float(
            probabilities.get("node_0", 0.0)
            + probabilities.get("node_1", 0.0)
            + probabilities.get("node_2", 0.0)
        ),
    }


def project_quantum_state_to_triad_observables(state: TriadQuantumState) -> dict[str, object]:
    probabilities = compute_basis_probabilities(state)
    phases = compute_basis_phases(state)
    return {
        "triad_id": state.id,
        "node_probabilities": [
            float(probabilities.get("node_0", 0.0)),
            float(probabilities.get("node_1", 0.0)),
            float(probabilities.get("node_2", 0.0)),
        ],
        "node_phases": [
            float(phases.get("node_0", 0.0)),
            float(phases.get("node_1", 0.0)),
            float(phases.get("node_2", 0.0)),
        ],
        "connector_probability": float(probabilities.get("connector", 0.0)),
        "connector_phase": float(phases.get("connector", 0.0)),
    }
