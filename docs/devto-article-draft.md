---
title: "MCP server configured, but zero tools show up? Here's probably why"
published: false
description: "A field guide to silent MCP client config failures — parentheses in server names, raw npx on Windows, NVM paths, broken JSON — and a tiny local CLI that diagnoses them."
tags: mcp, claude, ai, debugging
---

You add an MCP server to your config. The JSON is valid. The client even says "connected." And then: **zero tools**. No error. No hint. The official `/doctor` says nothing is wrong.

If this has happened to you, welcome — the GitHub issues are full of us:

- [MCP servers fail to connect with `npx` on Windows](https://github.com/modelcontextprotocol/servers/issues/40) — 112 comments
- [MCP Servers Don't Work with NVM](https://github.com/modelcontextprotocol/servers/issues/64) — 182 reactions
- [Claude Desktop silently drops all tools when a server key contains parentheses](https://github.com/homeassistant-ai/ha-mcp/issues/1743)
- [Claude Code's `/doctor` fails to detect MCP configuration errors](https://github.com/anthropics/claude-code/issues/64768)

After reading through these threads, the failures cluster into a handful of causes — and none of them are the MCP *server's* fault. They're **client config** failures that official tools don't diagnose. Here's the field guide.

## 1. Parentheses (or brackets) in the server name

```json
{
  "mcpServers": {
    "Home Assistant (ha-mcp)": { "command": "npx", "args": ["-y", "ha-mcp"] }
  }
}
```

This looks harmless. But at least one major client **silently drops every tool** when an `mcpServers` key contains parentheses. Server shows connected, `tools/list` completes, and the UI displays nothing. One user reported chasing this for hours.

**Fix:** rename the key — letters, numbers, hyphens, underscores only.

## 2. Raw `npx` on Windows

```json
{ "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem"] }
```

GUI apps on Windows frequently fail to spawn `npx` directly. The terminal works; the desktop client doesn't, because GUI processes don't get your shell environment.

**Fix:** wrap it:

```json
{ "command": "cmd", "args": ["/c", "npx", "-y", "..."] }
```

## 3. NVM (or any version-manager) paths

`npx` works in your terminal because your shell loads NVM. GUI apps don't load your shell profile, so the binary simply isn't on their PATH. The 182-reaction issue above is exactly this.

**Fix:** use the absolute path to the binary, or a shim the GUI can resolve.

## 4. JSON that "looks fine"

One unescaped Windows path (`"cwd": "C:\tools\my-server"`) and the whole config silently fails to parse. Some clients report this; others just show zero servers.

**Fix:** run the file through any JSON validator — `python -m json.tool config.json`.

## 5. Stale caches and environment drift

Users report `uv`-launched servers that keep failing *after* the underlying script was fixed, because the tool runner cached the broken environment. Also: `env` blocks that reference variables the GUI process doesn't have.

**Fix:** clear the tool runner's cache; inline absolute paths in `env`.

## I got tired of checking these by hand

So I wrote a tiny local CLI that reads MCP client configs and reports exactly these failure classes — with the reason and a suggested fix for each:

```bash
pipx install git+https://github.com/lajiaojiang-ai/mcp-why.git
mcp-why                    # auto-discover common client configs
mcp-why --config path/to/claude_desktop_config.json
```

Example output:

```
[ERROR] risky_server_name: Server name 'Home Assistant (ha-mcp)' contains parentheses or brackets
  why: Some clients silently drop every tool when an mcpServers key contains parentheses.
  fix: Rename the key to letters, numbers, hyphen, or underscore only.

[WARNING] windows_npx: Server 'Home Assistant (ha-mcp)' launches npx directly on Windows
  why: GUI apps often fail to spawn npx unless wrapped with cmd.exe /c.
  fix: Use {"command":"cmd","args":["/c","npx","-y","..."]}.
```

There's also an optional `--probe` that sends only `initialize` + `tools/list` over stdio (it never calls a tool, and it can't touch your real endpoints — it's read-only diagnostics against config + a handshake).

Repo: **https://github.com/lajiaojiang-ai/mcp-why**

## Honest limitations

- v0.1 knows six failure classes. There are more — send issues.
- It's a **config** diagnostician. If the config is fine and the server itself is broken, use the official [MCP Inspector](https://github.com/modelcontextprotocol/inspector) — they're complements, not competitors.
- Client behavior changes fast; a rule that's true for one client version may soften in the next.

If it saved you from one more hour of staring at a valid-looking config, that's the whole point. Star it if it's useful, open an issue if it's wrong.
