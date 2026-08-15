from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from .models import Finding

_RISKY_NAME = re.compile(r"[()\[\]{}<>]")
_WIN_DRIVE_PATH = re.compile(r'(?<!\\)[A-Za-z]:\\(?!\\)')


def diagnose_config(path: str | Path, client: str = "generic", platform: str | None = None) -> list[Finding]:
    path = Path(path)
    platform = platform or sys.platform
    findings: list[Finding] = []
    raw = path.read_text(encoding="utf-8")

    if platform.startswith("win") and _looks_like_unescaped_windows_path(raw):
        findings.append(
            Finding(
                code="windows_path",
                severity="error",
                summary="JSON text contains an unescaped Windows path",
                detail="Backslashes in JSON strings must be doubled, e.g. C:\\\\Users\\\\name.",
                client=client,
                path=str(path),
                hint="Use forward slashes or escaped backslashes in args and cwd.",
            )
        )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        findings.append(
            Finding(
                code="invalid_json",
                severity="error",
                summary="Config is not valid JSON",
                detail=str(exc),
                client=client,
                path=str(path),
            )
        )
        return findings

    servers = _extract_servers(data)
    if not servers:
        findings.append(
            Finding(
                code="no_servers",
                severity="warning",
                summary="No MCP servers were found in this config",
                client=client,
                path=str(path),
            )
        )
        return findings

    for name, spec in servers.items():
        findings.extend(_diagnose_server(name, spec, path, client, platform))
    return findings


def _extract_servers(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    if isinstance(data.get("mcpServers"), dict):
        return data["mcpServers"]
    mcp = data.get("mcp")
    if isinstance(mcp, dict) and isinstance(mcp.get("servers"), dict):
        return mcp["servers"]
    if isinstance(data.get("servers"), dict):
        return data["servers"]
    return {}


def _diagnose_server(name: str, spec: Any, path: Path, client: str, platform: str) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(spec, dict):
        findings.append(
            Finding(
                code="invalid_server_spec",
                severity="error",
                summary=f"Server {name!r} is not an object",
                client=client,
                server=name,
                path=str(path),
            )
        )
        return findings

    if _RISKY_NAME.search(name):
        findings.append(
            Finding(
                code="risky_server_name",
                severity="error",
                summary=f"Server name {name!r} contains parentheses or brackets",
                detail="Some clients silently drop every tool when an mcpServers key contains parentheses.",
                client=client,
                server=name,
                path=str(path),
                hint="Rename the key to letters, numbers, hyphen, or underscore only.",
            )
        )

    command = spec.get("command")
    url = spec.get("url")
    if not command and not url:
        findings.append(
            Finding(
                code="missing_command",
                severity="error",
                summary=f"Server {name!r} has neither command nor url",
                client=client,
                server=name,
                path=str(path),
            )
        )
        return findings

    if command:
        findings.extend(_diagnose_command(name, spec, path, client, platform, str(command)))
    return findings


def _diagnose_command(name: str, spec: dict[str, Any], path: Path, client: str, platform: str, command: str) -> list[Finding]:
    findings: list[Finding] = []
    resolved = _resolve_command(command)
    if resolved is None:
        findings.append(
            Finding(
                code="command_not_found",
                severity="error",
                summary=f"Command {command!r} for server {name!r} is not on PATH",
                client=client,
                server=name,
                path=str(path),
                hint="Use an absolute path, or install the binary in a PATH directory the GUI app can see.",
            )
        )

    if platform.startswith("win") and command.lower() in {"npx", "npx.cmd", "npm", "npm.cmd"}:
        findings.append(
            Finding(
                code="windows_npx",
                severity="warning",
                summary=f"Server {name!r} launches {command} directly on Windows",
                detail="Claude Desktop and other GUI apps often fail to spawn npx unless wrapped with cmd.exe /c.",
                client=client,
                server=name,
                path=str(path),
                hint='Use {"command":"cmd","args":["/c","npx","-y","..."]}.',
            )
        )

    if command.lower() in {"npx", "npx.cmd"} and _looks_like_nvm_path(resolved):
        findings.append(
            Finding(
                code="nvm_npx",
                severity="warning",
                summary=f"Server {name!r} uses an nvm-managed npx",
                detail="GUI apps usually do not inherit nvm shell PATH, so MCP servers fail only outside the terminal.",
                client=client,
                server=name,
                path=str(path),
                hint="Point command at a non-nvm Node install, or wrap with cmd.exe /c and a login shell.",
            )
        )

    args = spec.get("args") or []
    if isinstance(args, list) and any("uv" in str(item) for item in args):
        findings.append(
            Finding(
                code="uv_cache_risk",
                severity="info",
                summary=f"Server {name!r} appears to use uv/uvx",
                detail="A cached Windows-incompatible extra can make the whole MCP panel disappear.",
                client=client,
                server=name,
                path=str(path),
                hint="Clear the uv cache and pin a Windows-compatible extra if the panel stays empty.",
            )
        )
    return findings


def _resolve_command(command: str) -> str | None:
    if os.path.isabs(command) and Path(command).exists():
        return command
    return shutil.which(command)


def _looks_like_nvm_path(resolved: str | None) -> bool:
    if not resolved:
        return False
    lowered = resolved.replace("\\", "/").lower()
    return "/nvm/" in lowered or "nvm-windows" in lowered or "/.nvm/" in lowered


def _looks_like_unescaped_windows_path(raw: str) -> bool:
    # Valid JSON never contains a single-backslash drive path inside a string.
    # If the file still has C:\ it is either invalid JSON or a copy-paste hazard.
    return bool(_WIN_DRIVE_PATH.search(raw))
