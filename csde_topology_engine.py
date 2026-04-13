#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict, dataclass

from csde_data_schema import TriadRecord


@dataclass(frozen=True)
class TopologyTransition:
    triad_id: str
    lineage_id: str
    state: str
    split_required: bool
    active_split_count: int
    reconnect_ready: bool
    reconnect_applied: bool
    split_history_count: int
    reconnected_triad_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return dict(asdict(self))


def build_reconnected_triad_record(
    pyramid: dict[str, object],
    reconnect_report: dict[str, object] | None = None,
) -> TriadRecord:
    reconnect_report = reconnect_report or {}
    summary = dict(pyramid.get("summary", {}))
    geometry = dict(pyramid.get("geometry", {}))
    source_cell_ids = [str(value) for value in pyramid.get("source_cell_ids", [])]
    reconnected_id = str(reconnect_report.get("reconnected_triad_id", f"{pyramid['id']}:reconnected"))
    closure_center = summary.get("closure_center", pyramid.get("base_center", [0.0, 0.0, 0.0]))
    closure_radius = float(summary.get("closure_radius", 0.0))

    extras = {
        **summary,
        "lineage_id": str(pyramid.get("lineage_id", pyramid["id"])),
        "source": "topology_engine.reconnect",
        "reconnected_from": str(pyramid["id"]),
        "reconnect_report": dict(reconnect_report),
        "topology": geometry.get("topology", "unknown"),
        "topology_issues": list(geometry.get("issues", [])),
        "source_cell_ids": source_cell_ids,
    }
    return TriadRecord(
        id=reconnected_id,
        cell_ids=source_cell_ids,
        center=list(pyramid.get("base_center", [0.0, 0.0, 0.0])),
        phase=float(pyramid.get("phase", 0.0)),
        closure_center=list(closure_center),
        closure_radius=closure_radius,
        coherence_score=float(pyramid.get("connector_strength", summary.get("coherence_score", 0.0))),
        can_compose=bool(geometry.get("has_common_apex", False)),
        active=True,
        extras=extras,
    )


def apply_topology_transitions(
    pyramid_units: list[dict[str, object]],
    reconnect_reports: dict[str, dict[str, object]] | None = None,
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    reconnect_reports = reconnect_reports or {}
    transitioned_units: list[dict[str, object]] = []
    transition_reports: dict[str, dict[str, object]] = {}

    for pyramid in pyramid_units:
        triad_id = str(pyramid["id"])
        report = dict(reconnect_reports.get(triad_id, {}))
        unit = dict(pyramid)
        summary = dict(unit.get("summary", {}))
        geometry = dict(unit.get("geometry", {}))
        split_cells = list(unit.get("split_cells", []))

        split_required = bool(split_cells) or not bool(geometry.get("has_common_apex", True))
        reconnect_ready = bool(report.get("reconnect_ready", False))
        reconnect_applied = bool(reconnect_ready and report.get("split_history_count", 0) > 0)
        current_split_required = bool(split_required and not reconnect_applied)

        if reconnect_applied:
            topology_state = "reconnected"
            active_split_cells = []
            reconnected_triad_id = f"{triad_id}:reconnected"
            report["reconnected_triad_id"] = reconnected_triad_id
            reconnected_triad = build_reconnected_triad_record(unit, report)
            unit["reconnected_triad"] = reconnected_triad
        elif split_required:
            topology_state = "split"
            active_split_cells = split_cells
            reconnected_triad_id = None
            unit["reconnected_triad"] = None
        else:
            topology_state = "stable"
            active_split_cells = []
            reconnected_triad_id = None
            unit["reconnected_triad"] = None

        transition = TopologyTransition(
            triad_id=triad_id,
            lineage_id=str(unit.get("lineage_id", triad_id)),
            state=topology_state,
            split_required=current_split_required,
            active_split_count=len(active_split_cells),
            reconnect_ready=reconnect_ready,
            reconnect_applied=reconnect_applied,
            split_history_count=int(report.get("split_history_count", 0)),
            reconnected_triad_id=reconnected_triad_id,
        )

        unit["topology_transition"] = transition.to_dict()
        unit["topology_state"] = topology_state
        unit["active_split_cells"] = active_split_cells
        summary["split_required"] = current_split_required
        summary["split_count"] = len(split_cells)
        summary["active_split_count"] = len(active_split_cells)
        summary["reconnect_ready"] = reconnect_ready
        summary["reconnect_applied"] = reconnect_applied
        summary["topology_state"] = topology_state
        summary["reconnected_triad_id"] = reconnected_triad_id
        unit["summary"] = summary

        report.update(transition.to_dict())
        transitioned_units.append(unit)
        transition_reports[triad_id] = report

    return transitioned_units, transition_reports
