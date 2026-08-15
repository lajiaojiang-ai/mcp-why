from __future__ import annotations

import argparse
import json
from pathlib import Path

from .diagnose import diagnose_config, _extract_servers
from .discover import discover_configs
from .models import Report
from .probe import probe_stdio_server
from .report import render_json, render_text, write_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-why",
        description="Explain why an MCP server is configured but missing, empty, or silent.",
    )
    parser.add_argument("--config", action="append", dest="configs", help="Config file or directory; repeatable")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    parser.add_argument("--output", help="Write a markdown report")
    parser.add_argument("--probe", action="store_true", help="Best-effort initialize + tools/list; never calls a tool")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    discovered = discover_configs(args.configs)
    if args.configs and not discovered:
        # allow explicit files even if discover filtered them
        discovered = [("custom", Path(item)) for item in args.configs if Path(item).is_file()]
    if not discovered:
        print("No MCP config files found. Pass --config path/to/claude_desktop_config.json")
        return 1

    report = Report()
    for client, path in discovered:
        report.configs.append(str(path))
        findings = diagnose_config(path, client=client)
        if args.probe:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
            servers = _extract_servers(data)
            report.servers += len(servers)
            for name, spec in servers.items():
                if isinstance(spec, dict) and spec.get("command"):
                    findings.extend(probe_stdio_server(name, spec))
        else:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                report.servers += len(_extract_servers(data))
            except json.JSONDecodeError:
                pass
        report.findings.extend(findings)

    text = render_json(report) if args.json else render_text(report)
    print(text)
    if args.output:
        write_markdown(report, Path(args.output))
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
