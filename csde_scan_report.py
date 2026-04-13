#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from csde_experiment_registry import default_registry, load_metric_schema


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Markdown/JSON report for a CSDE parameter scan directory")
    parser.add_argument("--scan-dir", type=Path, required=True, help="scan directory containing summary.json and scan_results.csv")
    parser.add_argument("--top-k", type=int, default=5, help="number of top-ranked cases to highlight in the report")
    return parser.parse_args()


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_number(value: str) -> float | int | str:
    try:
        if value.strip().isdigit():
            return int(value)
        return float(value)
    except ValueError:
        return value


def normalize_rows(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for row in rows:
        normalized.append({key: parse_number(value) for key, value in row.items()})
    return normalized


def load_quantum_summary_for_run(run_dir: Path) -> Dict[str, Any]:
    summary_path = run_dir / "summary.json"
    report_path = run_dir / "quantum_consistency_report.json"
    payload: Dict[str, Any] = {}
    if summary_path.exists():
        payload.update(read_json(summary_path))
    if report_path.exists():
        report_payload = read_json(report_path)
        payload.setdefault("quantum_report_path", str(report_path))
        payload.setdefault("quantum_summary", report_payload.get("summary", {}))
    return payload


def collect_top_case_quantum_summaries(rows: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    for row in rows[:top_k]:
        run_dir = Path(str(row.get("run_dir", "")))
        quantum_payload = load_quantum_summary_for_run(run_dir) if run_dir.exists() else {}
        collected.append(
            {
                "case_id": row.get("case_id"),
                "run_dir": str(run_dir),
                "quantum_validation_enabled": bool(quantum_payload.get("quantum_validation_enabled", False)),
                "continuity_residual_rms_mean": quantum_payload.get("continuity_residual_rms_mean"),
                "continuity_residual_max_abs": quantum_payload.get("continuity_residual_max_abs"),
                "hermitian_error_max": quantum_payload.get("hermitian_error_max"),
                "eigen_residual_max_abs": quantum_payload.get("eigen_residual_max_abs"),
                "quantum_report_path": quantum_payload.get("quantum_report_path"),
            }
        )
    return collected


def metric_summary(rows: List[Dict[str, Any]], metric_name: str, objective: str) -> Dict[str, Any]:
    values = [float(row[metric_name]) for row in rows if metric_name in row]
    if not values:
        return {
            "name": metric_name,
            "objective": objective,
            "available": False,
            "mean": None,
            "best": None,
            "worst": None,
        }
    return {
        "name": metric_name,
        "objective": objective,
        "available": True,
        "mean": mean(values),
        "best": max(values) if objective == "max" else min(values),
        "worst": min(values) if objective == "max" else max(values),
    }


def detect_experiment_name(summary: Dict[str, Any], rows: List[Dict[str, Any]]) -> str | None:
    if "experiment_name" in summary:
        return str(summary["experiment_name"])
    run_dir = str(summary.get("best_cases", [{}])[0].get("run_dir", "")) if summary.get("best_cases") else ""
    if "hydrogen_coaxial_axis_emergence" in run_dir:
        return "hydrogen_coaxial_axis_emergence"
    if rows and "coaxial_depth_score" in rows[0]:
        return "hydrogen_coaxial_axis_emergence"
    return None


def generate_markdown(
    scan_dir: Path,
    summary: Dict[str, Any],
    rows: List[Dict[str, Any]],
    top_k: int,
    metric_schema: Dict[str, Any],
    experiment_metric_names: List[str],
    experiment_description: str | None,
    quantum_top_cases: List[Dict[str, Any]],
) -> str:
    highlighted = rows[:top_k]
    metric_lines = []
    for metric_name in experiment_metric_names:
        metric = metric_schema[metric_name]
        stats = metric_summary(rows, metric.name, metric.objective)
        if stats["available"]:
            metric_lines.append(
                f"- `{metric.name}` ({metric.objective})：mean={stats['mean']:.6f}, "
                f"best={stats['best']:.6f}, worst={stats['worst']:.6f}；{metric.description}"
            )
        else:
            metric_lines.append(
                f"- `{metric.name}` ({metric.objective})：当前扫描结果未提供该字段；{metric.description}"
            )

    best_case_lines = []
    quantum_by_case = {item["case_id"]: item for item in quantum_top_cases}
    for row in highlighted:
        quantum = quantum_by_case.get(row["case_id"], {})
        quantum_suffix = ""
        if quantum.get("quantum_validation_enabled"):
            quantum_suffix = (
                f", continuity_rms={quantum.get('continuity_residual_rms_mean', 'n/a')},"
                f" hermitian_error_max={quantum.get('hermitian_error_max', 'n/a')}"
            )
        best_case_lines.append(
            "- "
            + ", ".join(
                [
                    f"case_id={row['case_id']}",
                    f"run_dir={row['run_dir']}",
                    f"{summary['sort_metric']}={row[summary['sort_metric']]}",
                    f"axis_node_count_active={row.get('axis_node_count_active')}",
                    f"max_level={row.get('max_level')}",
                ]
            )
            + quantum_suffix
        )

    quantum_lines = []
    for item in quantum_top_cases:
        if item.get("quantum_validation_enabled"):
            quantum_lines.append(
                f"- case_id={item['case_id']} | continuity_rms={item.get('continuity_residual_rms_mean', 'n/a')} | "
                f"continuity_max={item.get('continuity_residual_max_abs', 'n/a')} | "
                f"hermitian_error_max={item.get('hermitian_error_max', 'n/a')} | "
                f"eigen_residual_max_abs={item.get('eigen_residual_max_abs', 'n/a')}"
            )
        else:
            quantum_lines.append(f"- case_id={item['case_id']} | quantum validation unavailable")

    scan_axes_lines = [
        f"- `{name}`: {values}"
        for name, values in summary.get("scan_axes", {}).items()
    ]

    return "\n".join(
        [
            "# CSDE 扫描报告",
            "",
            f"- 扫描目录：`{scan_dir}`",
            f"- 样本数：`{summary.get('case_count', len(rows))}`",
            f"- 排序指标：`{summary.get('sort_metric', 'n/a')}` / `{summary.get('sort_objective', 'n/a')}`",
            f"- 实验：`{experiment_description or '未识别实验描述'}`",
            "",
            "## 扫描轴",
            *scan_axes_lines,
            "",
            "## 指标统计",
            *metric_lines,
            "",
            f"## Top {min(top_k, len(highlighted))} 个案例",
            *best_case_lines,
            "",
            "## 量子一致性摘要",
            *quantum_lines,
            "",
        ]
    )


def main() -> None:
    args = parse_args()
    scan_dir = args.scan_dir
    summary_path = scan_dir / "summary.json"
    csv_path = scan_dir / "scan_results.csv"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing summary.json in {scan_dir}")
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing scan_results.csv in {scan_dir}")

    summary = read_json(summary_path)
    rows = normalize_rows(read_csv(csv_path))
    registry = default_registry()
    metric_schema = load_metric_schema()
    experiment_name = detect_experiment_name(summary, rows)
    experiment = registry[experiment_name] if experiment_name in registry else None
    experiment_description = experiment.description if experiment is not None else None
    experiment_metric_names = list(experiment.metric_names) if experiment is not None else list(metric_schema.keys())
    quantum_top_cases = collect_top_case_quantum_summaries(rows, args.top_k)

    report_md = generate_markdown(
        scan_dir=scan_dir,
        summary=summary,
        rows=rows,
        top_k=args.top_k,
        metric_schema=metric_schema,
        experiment_metric_names=experiment_metric_names,
        experiment_description=experiment_description,
        quantum_top_cases=quantum_top_cases,
    )

    report_json = {
        "scan_dir": str(scan_dir),
        "case_count": summary.get("case_count", len(rows)),
        "sort_metric": summary.get("sort_metric"),
        "sort_objective": summary.get("sort_objective"),
        "experiment_name": experiment_name,
        "experiment_description": experiment_description,
        "metric_summaries": [
            metric_summary(rows, metric_schema[name].name, metric_schema[name].objective)
            for name in experiment_metric_names
        ],
        "quantum_top_cases": quantum_top_cases,
        "top_cases": rows[: args.top_k],
    }

    md_path = scan_dir / "scan_report.md"
    json_path = scan_dir / "scan_report.json"
    md_path.write_text(report_md, encoding="utf-8")
    json_path.write_text(json.dumps(report_json, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Markdown report: {md_path}")
    print(f"JSON report: {json_path}")


if __name__ == "__main__":
    main()
