"""Minimal server-side PDF generation for mission reports.

The production environment does not currently install ReportLab, so this module
emits a small standards-compliant PDF text document from the backend report
payload. It intentionally avoids fabricated values and writes only fields that
the backend mission report already contains.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List


def _escape(text: str) -> str:
    cleaned = str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return cleaned.encode("latin-1", "replace").decode("latin-1")


def _lines(report: Dict[str, Any]) -> List[str]:
    mission = report.get("mission") or {}
    route = mission.get("route") or {}
    budget = mission.get("time_budget") or {}
    environment = report.get("environment") or {}
    radiation = report.get("radiation") or {}
    terrain_coverage = report.get("terrain_coverage") or {}

    lines: List[str] = ["DHRUVION MISSION REPORT"]
    lines.append(f"Report: {report.get('report_id') or 'unknown'}")
    lines.append(f"Mission: {mission.get('name') or report.get('mission_id') or 'unknown'}")
    lines.append(f"Mission ID: {mission.get('mission_id') or report.get('mission_id') or 'unknown'}")
    lines.append(f"Region: {mission.get('region_id') or 'unknown'}")
    lines.append(f"Status: {mission.get('status') or 'unknown'}")
    lines.append(f"Generated: {report.get('generated_at') or 'unknown'}")

    start = mission.get("start") or {}
    destination = mission.get("destination") or {}
    lines.append(f"Start: {start.get('x')} {start.get('y')}")
    lines.append(f"Destination: {destination.get('x')} {destination.get('y')}")
    lines.append(f"Strategy: {route.get('strategy') or mission.get('route_strategy') or 'unknown'}")
    lines.append(f"Distance: {route.get('distance_m')}")
    lines.append(f"Duration: {route.get('estimated_duration_min')}")
    lines.append(f"Feasibility: {mission.get('feasibility_status') or 'unknown'}")
    lines.append(f"Outbound: {budget.get('outbound_min')}")
    lines.append(f"Exploration: {budget.get('exploration_min')}")
    lines.append(f"Return: {budget.get('return_min')}")
    lines.append(f"Reserve: {budget.get('reserve_min')}")
    lines.append(f"Total: {budget.get('total_min')}")
    lines.append(f"Limit: {budget.get('limit_min')}")

    warnings = report.get("warnings") or []
    limitations = report.get("limitations") or []
    lines.append(f"Warnings: {warnings}")
    lines.append(f"Limitations: {limitations}")

    return [line for line in lines if line is not None]


def generate_mission_report_pdf(report: Dict[str, Any]) -> bytes:
    lines = _lines(report)
    content_parts: List[str] = ["BT", "/F1 12 Tf", "72 760 Td", f"({_escape(lines[0])}) Tj", "ET"]
    # Simple single-line-per-operation content stream; sufficient for text reports.
    operations: List[str] = []
    y = 760
    for line in lines:
        escaped = _escape(line)
        operations.append(f"BT /F1 10 Tf 72 {y} Td ({escaped}) Tj ET")
        y -= 14
    content_stream = "\n".join(operations).encode("latin-1")

    objects: List[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Length " + str(len(content_stream)).encode("ascii") + b" >>\nstream\n" + content_stream + b"\nendstream")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets: List[int] = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii") + body + b"\nendobj\n")
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode("ascii")
    )
    return bytes(pdf)
