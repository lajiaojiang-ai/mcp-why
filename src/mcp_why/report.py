from __future__ import annotations

import json
from pathlib import Path

from .models import Finding, Report


def render_text(report: Report) -> str:
    lines = [
        f"mcp-why: {len(report.configs)} config(s), {report.servers} server(s), "
        f"{report.errors} error(s), {report.warnings} warning(s)",
        "",
    ]
    if not report.findings:
        lines.append("No problems found in the scanned configs.")
        return "\n".join(lines)
    for item in report.findings:
        lines.append(_format_finding(item))
        lines.append("")
    return "\n".join(lines)


def render_json(report: Report) -> str:
    payload = {
        "configs": report.configs,
        "servers": report.servers,
        "errors": report.errors,
        "warnings": report.warnings,
        "findings": [item.to_dict() for item in report.findings],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def write_markdown(report: Report, output: Path) -> None:
    lines = ["# mcp-why report", "", render_text(report)]
    output.write_text("\n".join(lines), encoding="utf-8")


def _format_finding(item: Finding) -> str:
    where = item.server or item.path or "config"
    block = [f"[{item.severity.upper()}] {item.code}: {item.summary}"]
    if item.client:
        block.append(f"  client: {item.client}")
    if item.path:
        block.append(f"  file: {item.path}")
    if item.detail:
        block.append(f"  why: {item.detail}")
    if item.hint:
        block.append(f"  fix: {item.hint}")
    return "\n".join(block)
