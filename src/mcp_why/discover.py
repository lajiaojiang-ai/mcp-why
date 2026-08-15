from __future__ import annotations

import os
from pathlib import Path

CLIENT_FILES = {
    "claude-desktop": [
        ("APPDATA", "Claude/claude_desktop_config.json"),
        ("HOME", "Library/Application Support/Claude/claude_desktop_config.json"),
    ],
    "claude-code": [
        ("HOME", ".claude.json"),
        ("HOME", ".claude/settings.json"),
    ],
    "cursor": [
        ("HOME", ".cursor/mcp.json"),
    ],
    "vscode": [
        ("APPDATA", "Code/User/mcp.json"),
        ("HOME", ".config/Code/User/mcp.json"),
    ],
    "kiro": [
        ("HOME", ".kiro/settings/mcp.json"),
        ("APPDATA", "Kiro/User/mcp.json"),
    ],
    "opencode": [
        ("HOME", ".config/opencode/opencode.json"),
        ("HOME", ".opencode/opencode.json"),
    ],
}


def discover_configs(extra: list[str] | None = None) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for client, specs in CLIENT_FILES.items():
        for env_name, rel in specs:
            root = os.environ.get(env_name)
            if not root and env_name == "HOME":
                root = str(Path.home())
            if not root:
                continue
            path = Path(root) / rel
            if path.is_file() and path.resolve() not in seen:
                seen.add(path.resolve())
                found.append((client, path))
    for item in extra or []:
        path = Path(item)
        if path.is_file() and path.resolve() not in seen:
            seen.add(path.resolve())
            found.append(("custom", path))
        elif path.is_dir():
            for child in path.rglob("*.json"):
                if child.resolve() not in seen:
                    seen.add(child.resolve())
                    found.append(("custom", child))
    return found
