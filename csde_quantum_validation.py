#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import numpy as np

from csde_data_schema import CellRecord, FrameState, TriadCoreState, TriadRecord
from csde_stream_io import CSDEJsonlReader
from csde_quantum_core import (
    TriadQuantumConfig,
    TriadQuantumState,
    build_quantum_state_from_triad_core,
    hermitian_error,
    simulate_quantum_state,
)
from csde_quantum_observables import compute_basis_probabilities
from csde_triad_dynamics import build_triad_core_state_from_cells


Runner = Callable[[SimpleNamespace], tuple[Path, dict[str, Any]]]


@dataclass(frozen=True)
class ContinuityValidationResult:
    dt: float
    hbar_eff: float
    residual_rms: float
    residual_max_abs: float
    probability_drift_max_abs: float
    state_count: int

    def to_dict(self) -> dict[str, object]:
        return dict(asdict(self))


@dataclass(frozen=True)
class HamiltonianSpectrumValidationResult:
    dimension: int
    hermitian_error: float
    max_imag_eigenvalue_abs: float
    orthonormality_error: float
    eigen_residual_max_abs: float
    eigenvalues: list[float]

    def to_dict(self) -> dict[str, object]:
        return dict(asdict(self))


def _resolve_hbar_eff(state: TriadQuantumState, hbar_eff: float | None = None) -> float:
    value = float(hbar_eff if hbar_eff is not None else state.extras.get("hbar_eff", 1.0))
    if value <= 0.0:
        raise ValueError("hbar_eff must be positive.")
    return value


def compute_probability_current_matrix(
    state: TriadQuantumState,
    *,
    hbar_eff: float | None = None,
) -> np.ndarray:
    psi = state.psi()
    hamiltonian = state.hamiltonian()
    hbar = _resolve_hbar_eff(state, hbar_eff)
    size = psi.shape[0]
    current = np.zeros((size, size), dtype=np.float64)
    for i in range(size):
        for j in range(i + 1, size):
            flow = -(2.0 / hbar) * np.imag(np.conjugate(psi[i]) * hamiltonian[i, j] * psi[j])
            current[i, j] = float(flow)
            current[j, i] = float(-flow)
    return current


def compute_continuity_residual(
    state_t0: TriadQuantumState,
    state_t1: TriadQuantumState,
    dt: float,
    *,
    hbar_eff: float | None = None,
) -> dict[str, object]:
    if dt <= 0.0:
        raise ValueError("dt must be positive.")
    probs_t0 = np.abs(state_t0.psi()) ** 2
    probs_t1 = np.abs(state_t1.psi()) ** 2
    dprob_dt = (probs_t1 - probs_t0) / dt
    current = compute_probability_current_matrix(state_t0, hbar_eff=hbar_eff)
    divergence = np.sum(current, axis=1)
    residual = dprob_dt + divergence
    return {
        "basis_labels": list(state_t0.basis_labels),
        "probability_t0": probs_t0.astype(np.float64).tolist(),
        "probability_t1": probs_t1.astype(np.float64).tolist(),
        "dprob_dt": dprob_dt.astype(np.float64).tolist(),
        "divergence": divergence.astype(np.float64).tolist(),
        "residual": residual.astype(np.float64).tolist(),
        "residual_rms": float(np.sqrt(np.mean(np.square(residual)))),
        "residual_max_abs": float(np.max(np.abs(residual))),
        "probability_drift_max_abs": float(np.max(np.abs(probs_t1 - probs_t0))),
        "current_matrix": current.astype(np.float64).tolist(),
    }


def validate_continuity_equation(
    states: list[TriadQuantumState],
    dt: float,
    *,
    hbar_eff: float | None = None,
) -> ContinuityValidationResult:
    if len(states) < 2:
        raise ValueError("At least two quantum states are required for continuity validation.")
    residual_rms_values: list[float] = []
    residual_max_values: list[float] = []
    drift_values: list[float] = []
    for state_t0, state_t1 in zip(states[:-1], states[1:]):
        residual = compute_continuity_residual(state_t0, state_t1, dt, hbar_eff=hbar_eff)
        residual_rms_values.append(float(residual["residual_rms"]))
        residual_max_values.append(float(residual["residual_max_abs"]))
        drift_values.append(float(residual["probability_drift_max_abs"]))
    resolved_hbar = _resolve_hbar_eff(states[0], hbar_eff)
    return ContinuityValidationResult(
        dt=float(dt),
        hbar_eff=resolved_hbar,
        residual_rms=float(np.mean(residual_rms_values)),
        residual_max_abs=float(np.max(residual_max_values)),
        probability_drift_max_abs=float(np.max(drift_values)),
        state_count=len(states),
    )


def compute_hamiltonian_eigenspectrum(state: TriadQuantumState) -> dict[str, object]:
    hamiltonian = state.hamiltonian()
    eigenvalues, eigenvectors = np.linalg.eigh(hamiltonian)
    orthonormality = eigenvectors.conj().T @ eigenvectors
    identity = np.eye(eigenvectors.shape[1], dtype=np.complex128)
    orthonormality_error = float(np.max(np.abs(orthonormality - identity)))
    residuals = []
    for idx in range(eigenvectors.shape[1]):
        vector = eigenvectors[:, idx]
        residuals.append(np.max(np.abs(hamiltonian @ vector - eigenvalues[idx] * vector)))
    return {
        "eigenvalues": np.real(eigenvalues).astype(np.float64).tolist(),
        "max_imag_eigenvalue_abs": float(np.max(np.abs(np.imag(eigenvalues)))),
        "hermitian_error": hermitian_error(hamiltonian),
        "orthonormality_error": orthonormality_error,
        "eigen_residual_max_abs": float(np.max(residuals) if residuals else 0.0),
        "dimension": int(hamiltonian.shape[0]),
    }


def validate_hamiltonian_eigenspectrum(state: TriadQuantumState) -> HamiltonianSpectrumValidationResult:
    spectrum = compute_hamiltonian_eigenspectrum(state)
    return HamiltonianSpectrumValidationResult(
        dimension=int(spectrum["dimension"]),
        hermitian_error=float(spectrum["hermitian_error"]),
        max_imag_eigenvalue_abs=float(spectrum["max_imag_eigenvalue_abs"]),
        orthonormality_error=float(spectrum["orthonormality_error"]),
        eigen_residual_max_abs=float(spectrum["eigen_residual_max_abs"]),
        eigenvalues=[float(value) for value in spectrum["eigenvalues"]],
    )


def validate_quantum_model_from_triad_core(
    triad_state: TriadCoreState,
    *,
    quantum_params: dict[str, float] | TriadQuantumConfig | None = None,
    step_count: int = 64,
    dt: float = 0.05,
) -> dict[str, object]:
    quantum_state = build_quantum_state_from_triad_core(triad_state, params=quantum_params)
    states, _ = simulate_quantum_state(quantum_state, step_count=step_count, dt=dt)
    continuity = validate_continuity_equation(states, dt)
    spectrum = validate_hamiltonian_eigenspectrum(quantum_state)
    return {
        "state_id": triad_state.id,
        "basis_probabilities": compute_basis_probabilities(quantum_state),
        "continuity": continuity.to_dict(),
        "spectrum": spectrum.to_dict(),
    }


def _infer_dt_from_frames(frames: list[FrameState], dt: float | None = None) -> float:
    if dt is not None:
        if dt <= 0.0:
            raise ValueError("dt must be positive.")
        return float(dt)
    if len(frames) < 2:
        return 0.05
    deltas = [
        float(frames[idx + 1].time) - float(frames[idx].time)
        for idx in range(len(frames) - 1)
        if float(frames[idx + 1].time) > float(frames[idx].time)
    ]
    if not deltas:
        return 0.05
    return float(np.median(np.asarray(deltas, dtype=np.float64)))


def _build_triad_state_from_record(frame: FrameState, triad: TriadRecord) -> TriadCoreState | None:
    cell_lookup = {cell.id: cell for cell in frame.cells}
    cells = [cell_lookup.get(cell_id) for cell_id in triad.cell_ids]
    if any(cell is None for cell in cells):
        return None
    return build_triad_core_state_from_cells(
        [cell for cell in cells if cell is not None],
        triad_id=triad.id,
        connector_strength=float(triad.coherence_score) if triad.coherence_score > 0.0 else None,
    )


def iter_frame_triad_core_states(frame: FrameState) -> list[TriadCoreState]:
    triad_states: list[TriadCoreState] = []
    if frame.triads:
        for triad in frame.triads:
            state = _build_triad_state_from_record(frame, triad)
            if state is not None:
                triad_states.append(state)
        if triad_states:
            return triad_states
    if len(frame.cells) >= 3:
        triad_states.append(build_triad_core_state_from_cells(frame.cells[:3], triad_id=f"frame-{frame.frame_index}-triad-0"))
    return triad_states


def validate_run_dir(
    run_dir: str | Path,
    *,
    quantum_params: dict[str, float] | TriadQuantumConfig | None = None,
    step_count: int = 64,
    dt: float | None = None,
) -> dict[str, object]:
    run_path = Path(run_dir)
    reader = CSDEJsonlReader(run_path)
    frames = reader.poll_states()
    if not frames:
        raise ValueError(f"No frame data found in run directory: {run_path}")

    resolved_dt = _infer_dt_from_frames(frames, dt)
    frame_reports: list[dict[str, object]] = []
    continuity_rms_values: list[float] = []
    continuity_max_values: list[float] = []
    hermitian_errors: list[float] = []
    eigen_residuals: list[float] = []
    processed_triads = 0

    for frame in frames:
        triad_states = iter_frame_triad_core_states(frame)
        triad_reports: list[dict[str, object]] = []
        for triad_state in triad_states:
            report = validate_quantum_model_from_triad_core(
                triad_state,
                quantum_params=quantum_params,
                step_count=step_count,
                dt=resolved_dt,
            )
            triad_reports.append(report)
            continuity_rms_values.append(float(report["continuity"]["residual_rms"]))
            continuity_max_values.append(float(report["continuity"]["residual_max_abs"]))
            hermitian_errors.append(float(report["spectrum"]["hermitian_error"]))
            eigen_residuals.append(float(report["spectrum"]["eigen_residual_max_abs"]))
            processed_triads += 1
        frame_reports.append(
            {
                "frame_index": int(frame.frame_index),
                "time": float(frame.time),
                "triad_count": len(triad_reports),
                "triads": triad_reports,
            }
        )

    status_path = run_path / "status.json"
    status_payload = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    report = {
        "run_dir": str(run_path),
        "engine_name": status_payload.get("engine_name", "CSDE"),
        "experiment_name": status_payload.get("experiment_name", "unknown"),
        "run_id": status_payload.get("run_id", run_path.name),
        "frame_count": len(frames),
        "processed_triad_count": processed_triads,
        "dt": float(resolved_dt),
        "step_count": int(step_count),
        "quantum_params": quantum_params.to_params() if isinstance(quantum_params, TriadQuantumConfig) else (quantum_params or TriadQuantumConfig().to_params()),
        "summary": {
            "continuity_residual_rms_mean": float(np.mean(continuity_rms_values)) if continuity_rms_values else 0.0,
            "continuity_residual_max_abs": float(np.max(continuity_max_values)) if continuity_max_values else 0.0,
            "hermitian_error_max": float(np.max(hermitian_errors)) if hermitian_errors else 0.0,
            "eigen_residual_max_abs": float(np.max(eigen_residuals)) if eigen_residuals else 0.0,
        },
        "frames": frame_reports,
    }
    return report


def write_quantum_consistency_report(
    report: dict[str, object],
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _quantum_summary_from_report(report: dict[str, object], report_path: Path) -> dict[str, object]:
    summary = dict(report.get("summary", {}))
    return {
        "quantum_validation_enabled": True,
        "quantum_report_path": str(report_path),
        "quantum_frame_count": int(report.get("frame_count", 0)),
        "quantum_processed_triad_count": int(report.get("processed_triad_count", 0)),
        **summary,
    }


def run_post_run_quantum_validation(
    run_dir: str | Path,
    summary: dict[str, Any] | None = None,
    *,
    quantum_params: dict[str, float] | TriadQuantumConfig | None = None,
    step_count: int = 64,
    dt: float | None = None,
    quiet: bool = True,
) -> tuple[dict[str, object] | None, dict[str, Any]]:
    run_path = Path(run_dir)
    state_stream_path = run_path / "state_stream.jsonl"
    updated_summary = dict(summary or {})
    if not state_stream_path.exists():
        updated_summary.setdefault("quantum_validation_enabled", False)
        updated_summary["quantum_validation_skipped"] = "missing_state_stream"
        return None, updated_summary

    report = validate_run_dir(
        run_path,
        quantum_params=quantum_params,
        step_count=step_count,
        dt=dt,
    )
    report_path = write_quantum_consistency_report(report, run_path / "quantum_consistency_report.json")
    updated_summary.update(_quantum_summary_from_report(report, report_path))

    summary_path = run_path / "summary.json"
    if summary_path.exists():
        try:
            existing_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            existing_summary.update(updated_summary)
            summary_path.write_text(json.dumps(existing_summary, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            summary_path.write_text(json.dumps(updated_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        summary_path.write_text(json.dumps(updated_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    if not quiet:
        print(f"Quantum validation report: {report_path}")
    return report, updated_summary


def wrap_runner_with_quantum_post_validation(
    runner: Runner,
    *,
    quantum_params: dict[str, float] | TriadQuantumConfig | None = None,
    step_count: int = 64,
    dt: float | None = None,
    quiet: bool = True,
) -> Runner:
    def wrapped(case_args: SimpleNamespace) -> tuple[Path, dict[str, Any]]:
        run_dir, summary = runner(case_args)
        _, updated_summary = run_post_run_quantum_validation(
            run_dir,
            summary=summary,
            quantum_params=quantum_params,
            step_count=step_count,
            dt=dt,
            quiet=quiet,
        )
        return run_dir, updated_summary

    return wrapped


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate quantum consistency for a CSDE run directory.")
    parser.add_argument("--run-dir", required=True, help="Path to a CSDE run directory containing state_stream.jsonl")
    parser.add_argument("--step-count", type=int, default=64, help="Number of unitary substeps used for each triad validation")
    parser.add_argument("--dt", type=float, default=None, help="Override frame dt; otherwise inferred from frame times")
    parser.add_argument("--output", type=str, default=None, help="Optional output JSON path")
    parser.add_argument("--print-frames", action="store_true", help="Print per-frame report in addition to summary")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    report = validate_run_dir(
        args.run_dir,
        step_count=int(args.step_count),
        dt=args.dt,
    )
    output_path = Path(args.output) if args.output else Path(args.run_dir) / "quantum_consistency_report.json"
    write_quantum_consistency_report(report, output_path)

    summary = report["summary"]
    print(f"run_id={report['run_id']}")
    print(f"experiment_name={report['experiment_name']}")
    print(f"frame_count={report['frame_count']}")
    print(f"processed_triad_count={report['processed_triad_count']}")
    print(f"dt={report['dt']:.6f}")
    print(f"continuity_residual_rms_mean={summary['continuity_residual_rms_mean']:.6e}")
    print(f"continuity_residual_max_abs={summary['continuity_residual_max_abs']:.6e}")
    print(f"hermitian_error_max={summary['hermitian_error_max']:.6e}")
    print(f"eigen_residual_max_abs={summary['eigen_residual_max_abs']:.6e}")
    print(f"report_path={output_path}")

    if args.print_frames:
        print(json.dumps(report["frames"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
