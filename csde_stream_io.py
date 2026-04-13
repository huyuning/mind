#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, TextIO

from csde_data_schema import EventRecord, FrameState, MetricRecord, RunStatus, build_schema_descriptor
from csde_engine_protocols import CSDEReader, CSDEWriter


STATE_STREAM_FILENAME = "state_stream.jsonl"
EVENT_STREAM_FILENAME = "event_stream.jsonl"
METRIC_STREAM_FILENAME = "metric_stream.csv"
STATUS_FILENAME = "status.json"
SCHEMA_FILENAME = "schema.json"


@dataclass(frozen=True)
class CSDEStreamPaths:
    root_dir: Path
    state_stream_path: Path
    event_stream_path: Path
    metric_stream_path: Path
    status_path: Path
    schema_path: Path

    @classmethod
    def from_root(cls, root_dir: Path) -> "CSDEStreamPaths":
        return cls(
            root_dir=root_dir,
            state_stream_path=root_dir / STATE_STREAM_FILENAME,
            event_stream_path=root_dir / EVENT_STREAM_FILENAME,
            metric_stream_path=root_dir / METRIC_STREAM_FILENAME,
            status_path=root_dir / STATUS_FILENAME,
            schema_path=root_dir / SCHEMA_FILENAME,
        )


class JsonlStreamFile:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle: TextIO = self.path.open("a", encoding="utf-8")

    def write_json_line(self, payload: Dict[str, object]) -> None:
        self.handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
        self.handle.flush()

    def close(self) -> None:
        self.handle.close()


class MetricCsvStreamFile:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle: TextIO = self.path.open("a", newline="", encoding="utf-8")
        self.writer: csv.DictWriter[str] | None = None
        self.fieldnames: List[str] | None = None

    def write_row(self, row: Dict[str, object]) -> None:
        fieldnames = list(row.keys())
        if self.writer is None:
            self.fieldnames = fieldnames
            self.writer = csv.DictWriter(self.handle, fieldnames=self.fieldnames)
            if self.path.stat().st_size == 0:
                self.writer.writeheader()
        elif fieldnames != self.fieldnames:
            raise ValueError("Metric CSV fieldnames changed during streaming; use a stable metric schema.")
        self.writer.writerow(row)
        self.handle.flush()

    def close(self) -> None:
        self.handle.close()


class JsonlTailReader:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = 0
        self.partial = ""

    def poll(self) -> List[Dict[str, object]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            handle.seek(self.offset)
            chunk = handle.read()
            self.offset = handle.tell()
        if not chunk:
            return []
        data = self.partial + chunk
        lines = data.splitlines(keepends=False)
        if data and not data.endswith("\n"):
            self.partial = lines.pop() if lines else data
        else:
            self.partial = ""
        rows: List[Dict[str, object]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows


class CsvTailReader:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = 0
        self.partial = ""
        self.header: List[str] | None = None

    def poll(self) -> List[Dict[str, object]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            handle.seek(self.offset)
            chunk = handle.read()
            self.offset = handle.tell()
        if not chunk:
            return []
        data = self.partial + chunk
        lines = data.splitlines(keepends=False)
        if data and not data.endswith("\n"):
            self.partial = lines.pop() if lines else data
        else:
            self.partial = ""
        if not lines:
            return []
        if self.header is None:
            self.header = [item.strip() for item in lines.pop(0).split(",")]
        rows: List[Dict[str, object]] = []
        for line in lines:
            values = [item.strip() for item in line.split(",")]
            rows.append(dict(zip(self.header, values, strict=False)))
        return rows


class CSDEJsonlWriter(CSDEWriter):
    def __init__(self, root_dir: str | Path) -> None:
        self.paths = CSDEStreamPaths.from_root(Path(root_dir))
        self.paths.root_dir.mkdir(parents=True, exist_ok=True)
        self.state_stream = JsonlStreamFile(self.paths.state_stream_path)
        self.event_stream = JsonlStreamFile(self.paths.event_stream_path)
        self.metric_stream = MetricCsvStreamFile(self.paths.metric_stream_path)
        self.paths.schema_path.write_text(json.dumps(build_schema_descriptor(), indent=2), encoding="utf-8")

    def write_state(self, frame: FrameState) -> None:
        self.state_stream.write_json_line(frame.to_dict())

    def write_event(self, event: EventRecord) -> None:
        self.event_stream.write_json_line(event.to_dict())

    def write_metric(self, metric: MetricRecord) -> None:
        row: Dict[str, object] = {
            "frame_index": metric.frame_index,
            "time": metric.time,
            **metric.values,
        }
        self.metric_stream.write_row(row)

    def update_status(self, status: RunStatus) -> None:
        self.paths.status_path.write_text(json.dumps(status.to_dict(), indent=2), encoding="utf-8")

    def close(self) -> None:
        self.state_stream.close()
        self.event_stream.close()
        self.metric_stream.close()


class CSDEJsonlReader(CSDEReader):
    def __init__(self, root_dir: str | Path) -> None:
        self.paths = CSDEStreamPaths.from_root(Path(root_dir))
        self.state_reader = JsonlTailReader(self.paths.state_stream_path)
        self.event_reader = JsonlTailReader(self.paths.event_stream_path)
        self.metric_reader = CsvTailReader(self.paths.metric_stream_path)

    def poll_states(self) -> list[FrameState]:
        return [FrameState.from_dict(item) for item in self.state_reader.poll()]

    def poll_events(self) -> list[EventRecord]:
        return [EventRecord.from_dict(item) for item in self.event_reader.poll()]

    def poll_metrics(self) -> list[MetricRecord]:
        records: list[MetricRecord] = []
        for row in self.metric_reader.poll():
            frame_index = int(row.get("frame_index", 0))
            time = float(row.get("time", 0.0))
            values = {
                key: float(value)
                for key, value in row.items()
                if key not in {"frame_index", "time"} and value != ""
            }
            records.append(MetricRecord(frame_index=frame_index, time=time, values=values))
        return records

    def read_status(self) -> RunStatus | None:
        if not self.paths.status_path.exists():
            return None
        return RunStatus.from_dict(json.loads(self.paths.status_path.read_text(encoding="utf-8")))
