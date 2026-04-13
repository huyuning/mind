#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping


ENGINE_NAME = "CSDE"
STATE_SCHEMA_NAME = "csde_state_schema"
STATE_SCHEMA_VERSION = "1.0.0"


JsonDict = Dict[str, Any]


def _copy_mapping(data: Mapping[str, Any] | None) -> JsonDict:
    return dict(data) if data is not None else {}


@dataclass
class CellRecord:
    id: str
    center: List[float]
    phase: float = 0.0
    frequency: float = 0.0
    amplitude: float = 0.0
    radius: float = 0.0
    level: int = 0
    parent_id: str | None = None
    active: bool = True
    extras: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        payload = asdict(self)
        payload["extras"] = _copy_mapping(self.extras)
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CellRecord":
        return cls(
            id=str(data["id"]),
            center=list(data.get("center", [])),
            phase=float(data.get("phase", 0.0)),
            frequency=float(data.get("frequency", 0.0)),
            amplitude=float(data.get("amplitude", 0.0)),
            radius=float(data.get("radius", 0.0)),
            level=int(data.get("level", 0)),
            parent_id=data.get("parent_id"),
            active=bool(data.get("active", True)),
            extras=_copy_mapping(data.get("extras")),
        )


@dataclass
class TriadRecord:
    id: str
    cell_ids: List[str]
    center: List[float]
    phase: float = 0.0
    closure_center: List[float] = field(default_factory=list)
    closure_radius: float = 0.0
    coherence_score: float = 0.0
    can_compose: bool = False
    active: bool = True
    extras: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        payload = asdict(self)
        payload["extras"] = _copy_mapping(self.extras)
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TriadRecord":
        return cls(
            id=str(data["id"]),
            cell_ids=[str(item) for item in data.get("cell_ids", [])],
            center=list(data.get("center", [])),
            phase=float(data.get("phase", 0.0)),
            closure_center=list(data.get("closure_center", [])),
            closure_radius=float(data.get("closure_radius", 0.0)),
            coherence_score=float(data.get("coherence_score", 0.0)),
            can_compose=bool(data.get("can_compose", False)),
            active=bool(data.get("active", True)),
            extras=_copy_mapping(data.get("extras")),
        )


@dataclass
class TriadCoreState:
    id: str
    node_duty: List[float]
    node_freq: List[float]
    node_phase: List[float]
    node_position: List[List[float]]
    node_velocity: List[List[float]]
    node_axis: List[List[float]]
    edge_state_real: List[float]
    edge_state_imag: List[float]
    connector_position: List[float] = field(default_factory=list)
    connector_velocity: List[float] = field(default_factory=list)
    connector_phase: float = 0.0
    connector_freq: float = 0.0
    connector_strength: float = 0.0
    active: bool = True
    extras: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        payload = asdict(self)
        payload["extras"] = _copy_mapping(self.extras)
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TriadCoreState":
        return cls(
            id=str(data["id"]),
            node_duty=[float(item) for item in data.get("node_duty", [])],
            node_freq=[float(item) for item in data.get("node_freq", [])],
            node_phase=[float(item) for item in data.get("node_phase", [])],
            node_position=[list(item) for item in data.get("node_position", [])],
            node_velocity=[list(item) for item in data.get("node_velocity", [])],
            node_axis=[list(item) for item in data.get("node_axis", [])],
            edge_state_real=[float(item) for item in data.get("edge_state_real", [])],
            edge_state_imag=[float(item) for item in data.get("edge_state_imag", [])],
            connector_position=list(data.get("connector_position", [])),
            connector_velocity=list(data.get("connector_velocity", [])),
            connector_phase=float(data.get("connector_phase", 0.0)),
            connector_freq=float(data.get("connector_freq", 0.0)),
            connector_strength=float(data.get("connector_strength", 0.0)),
            active=bool(data.get("active", True)),
            extras=_copy_mapping(data.get("extras")),
        )


@dataclass
class AxisNodeRecord:
    id: str
    center: List[float]
    direction: List[float]
    level: int
    strength: float
    persistence: float = 0.0
    parent_ids: List[str] = field(default_factory=list)
    phase: float = 0.0
    active: bool = True
    extras: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        payload = asdict(self)
        payload["extras"] = _copy_mapping(self.extras)
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AxisNodeRecord":
        return cls(
            id=str(data["id"]),
            center=list(data.get("center", [])),
            direction=list(data.get("direction", [])),
            level=int(data.get("level", 0)),
            strength=float(data.get("strength", 0.0)),
            persistence=float(data.get("persistence", 0.0)),
            parent_ids=[str(item) for item in data.get("parent_ids", [])],
            phase=float(data.get("phase", 0.0)),
            active=bool(data.get("active", True)),
            extras=_copy_mapping(data.get("extras")),
        )


@dataclass
class CoaxialClusterRecord:
    id: str
    level: int
    center: List[float]
    direction: List[float]
    axis_ids: List[str] = field(default_factory=list)
    coherence: float = 0.0
    active: bool = True
    extras: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        payload = asdict(self)
        payload["extras"] = _copy_mapping(self.extras)
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CoaxialClusterRecord":
        return cls(
            id=str(data["id"]),
            level=int(data.get("level", 0)),
            center=list(data.get("center", [])),
            direction=list(data.get("direction", [])),
            axis_ids=[str(item) for item in data.get("axis_ids", [])],
            coherence=float(data.get("coherence", 0.0)),
            active=bool(data.get("active", True)),
            extras=_copy_mapping(data.get("extras")),
        )


@dataclass
class FrameState:
    frame_index: int
    time: float
    cells: List[CellRecord] = field(default_factory=list)
    triads: List[TriadRecord] = field(default_factory=list)
    axis_nodes: List[AxisNodeRecord] = field(default_factory=list)
    coaxial_clusters: List[CoaxialClusterRecord] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    metadata: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "frame_index": self.frame_index,
            "time": self.time,
            "cells": [item.to_dict() for item in self.cells],
            "triads": [item.to_dict() for item in self.triads],
            "axis_nodes": [item.to_dict() for item in self.axis_nodes],
            "coaxial_clusters": [item.to_dict() for item in self.coaxial_clusters],
            "metrics": dict(self.metrics),
            "metadata": _copy_mapping(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FrameState":
        return cls(
            frame_index=int(data.get("frame_index", 0)),
            time=float(data.get("time", 0.0)),
            cells=[CellRecord.from_dict(item) for item in data.get("cells", [])],
            triads=[TriadRecord.from_dict(item) for item in data.get("triads", [])],
            axis_nodes=[AxisNodeRecord.from_dict(item) for item in data.get("axis_nodes", [])],
            coaxial_clusters=[CoaxialClusterRecord.from_dict(item) for item in data.get("coaxial_clusters", [])],
            metrics={str(key): float(value) for key, value in data.get("metrics", {}).items()},
            metadata=_copy_mapping(data.get("metadata")),
        )


@dataclass
class EventRecord:
    event_index: int
    time: float
    event_type: str
    payload: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "event_index": self.event_index,
            "time": self.time,
            "event_type": self.event_type,
            "payload": _copy_mapping(self.payload),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EventRecord":
        return cls(
            event_index=int(data.get("event_index", 0)),
            time=float(data.get("time", 0.0)),
            event_type=str(data.get("event_type", "unknown")),
            payload=_copy_mapping(data.get("payload")),
        )


@dataclass
class MetricRecord:
    frame_index: int
    time: float
    values: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "frame_index": self.frame_index,
            "time": self.time,
            "values": dict(self.values),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MetricRecord":
        return cls(
            frame_index=int(data.get("frame_index", 0)),
            time=float(data.get("time", 0.0)),
            values={str(key): float(value) for key, value in data.get("values", {}).items()},
        )


@dataclass
class RunStatus:
    run_id: str
    experiment_name: str
    state_schema_version: str = STATE_SCHEMA_VERSION
    status: str = "initialized"
    latest_frame_index: int = -1
    latest_time: float = 0.0
    message: str = ""
    metadata: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "engine_name": ENGINE_NAME,
            "schema_name": STATE_SCHEMA_NAME,
            "schema_version": self.state_schema_version,
            "run_id": self.run_id,
            "experiment_name": self.experiment_name,
            "status": self.status,
            "latest_frame_index": self.latest_frame_index,
            "latest_time": self.latest_time,
            "message": self.message,
            "metadata": _copy_mapping(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RunStatus":
        return cls(
            run_id=str(data.get("run_id", "")),
            experiment_name=str(data.get("experiment_name", "")),
            state_schema_version=str(data.get("schema_version", STATE_SCHEMA_VERSION)),
            status=str(data.get("status", "initialized")),
            latest_frame_index=int(data.get("latest_frame_index", -1)),
            latest_time=float(data.get("latest_time", 0.0)),
            message=str(data.get("message", "")),
            metadata=_copy_mapping(data.get("metadata")),
        )


def build_schema_descriptor() -> JsonDict:
    return {
        "engine_name": ENGINE_NAME,
        "schema_name": STATE_SCHEMA_NAME,
        "schema_version": STATE_SCHEMA_VERSION,
        "object_types": [
            "cells",
            "axis_nodes",
            "coaxial_clusters",
            "events",
            "metrics",
            "run_status",
        ],
    }
