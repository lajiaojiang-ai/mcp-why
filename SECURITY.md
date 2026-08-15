# Security policy

`mcp-why` is a local diagnostic CLI:

- it does not upload configs, env values, transcripts, or credentials;
- `--probe` only sends `initialize` and `tools/list`;
- it never calls an MCP tool;
- reports print command names and paths, not secret values from `env`.

Report vulnerabilities privately. Do not open a public issue with real tokens or private config.
