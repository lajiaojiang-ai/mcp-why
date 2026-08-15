from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .models import Finding


def probe_stdio_server(name: str, spec: dict[str, Any], timeout: float = 8.0) -> list[Finding]:
    """Best-effort initialize + tools/list. Never executes a tool."""
    command = spec.get("command")
    if not command:
        return []
    args = [str(command), *[str(x) for x in (spec.get("args") or [])]]
    env = os.environ.copy()
    extra_env = spec.get("env") or {}
    if isinstance(extra_env, dict):
        env.update({str(k): str(v) for k, v in extra_env.items()})
    cwd = spec.get("cwd") or None
    try:
        proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=cwd,
            env=env,
        )
    except OSError as exc:
        return [
            Finding(
                code="probe_spawn_failed",
                severity="error",
                summary=f"Could not start server {name!r}",
                detail=str(exc),
                server=name,
            )
        ]

    findings: list[Finding] = []
    try:
        init = _rpc(1, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "mcp-why", "version": "0.1.0"}})
        listed = _rpc(2, "tools/list", {})
        payload = (init + listed).encode("utf-8")
        assert proc.stdin is not None
        assert proc.stdout is not None
        proc.stdin.write(payload)
        proc.stdin.close()
        raw = proc.stdout.read()
        if proc.wait(timeout=timeout) != 0 and not raw:
            findings.append(
                Finding(
                    code="probe_exit",
                    severity="warning",
                    summary=f"Server {name!r} exited before answering initialize/tools/list",
                    server=name,
                )
            )
            return findings
        messages = _parse_rpc_stream(raw.decode("utf-8", errors="replace"))
        tools = None
        for message in messages:
            result = message.get("result") or {}
            if "tools" in result:
                tools = result["tools"]
        if tools is None:
            findings.append(
                Finding(
                    code="probe_no_tools_list",
                    severity="warning",
                    summary=f"Server {name!r} did not return tools/list",
                    server=name,
                    hint="The process started, but the client may still show zero tools.",
                )
            )
        elif len(tools) == 0:
            findings.append(
                Finding(
                    code="probe_zero_tools",
                    severity="warning",
                    summary=f"Server {name!r} answered tools/list with 0 tools",
                    server=name,
                )
            )
    except Exception as exc:  # probe is best-effort
        findings.append(
            Finding(
                code="probe_failed",
                severity="warning",
                summary=f"Probe of server {name!r} failed",
                detail=str(exc),
                server=name,
            )
        )
    finally:
        if proc.poll() is None:
            proc.kill()
    return findings


def _rpc(req_id: int, method: str, params: dict[str, Any]) -> str:
    body = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
    return f"Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"


def _parse_rpc_stream(text: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    remaining = text
    while "Content-Length:" in remaining:
        header, _, rest = remaining.partition("\r\n\r\n")
        try:
            length = int(header.split(":")[-1].strip())
        except ValueError:
            break
        blob = rest[:length]
        remaining = rest[length:]
        try:
            messages.append(json.loads(blob))
        except json.JSONDecodeError:
            break
    if not messages:
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return messages
