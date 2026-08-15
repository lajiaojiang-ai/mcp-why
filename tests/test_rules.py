import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp_why.diagnose import diagnose_config  # noqa: E402


class RuleTests(unittest.TestCase):
    def write(self, tmp, name, payload):
        path = Path(tmp) / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def codes(self, findings):
        return [item.code for item in findings]

    def test_invalid_json_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text("{not json", encoding="utf-8")
            findings = diagnose_config(path, client="claude-desktop")
        self.assertIn("invalid_json", self.codes(findings))

    def test_parentheses_in_server_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(
                tmp,
                "claude_desktop_config.json",
                {"mcpServers": {"Home Assistant (ha-mcp)": {"command": "npx", "args": ["-y", "fake"]}}},
            )
            findings = diagnose_config(path, client="claude-desktop")
        self.assertIn("risky_server_name", self.codes(findings))
        self.assertTrue(any("parentheses" in item.summary.lower() for item in findings))

    def test_missing_command_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(
                tmp,
                "mcp.json",
                {"mcpServers": {"demo": {"command": "definitely-not-a-real-binary-xyz"}}},
            )
            findings = diagnose_config(path, client="cursor")
        self.assertIn("command_not_found", self.codes(findings))

    def test_windows_npx_without_cmd_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(
                tmp,
                "claude_desktop_config.json",
                {"mcpServers": {"fs": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:\\data"]}}},
            )
            findings = diagnose_config(path, client="claude-desktop", platform="win32")
        self.assertIn("windows_npx", self.codes(findings))

    def test_unescaped_windows_path_in_json_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claude_desktop_config.json"
            path.write_text(
                '{\n  "mcpServers": {\n    "fs": {\n      "command": "node",\n      "args": ["C:\\Users\\demo\\server.js"]\n    }\n  }\n}\n',
                encoding="utf-8",
            )
            findings = diagnose_config(path, client="claude-desktop", platform="win32")
        self.assertTrue({"invalid_json", "windows_path"} & set(self.codes(findings)))

    def test_healthy_server_has_no_error_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(
                tmp,
                "mcp.json",
                {
                    "mcpServers": {
                        "demo": {
                            "command": sys.executable,
                            "args": ["-c", "print('ok')"],
                        }
                    }
                },
            )
            findings = diagnose_config(path, client="cursor")
        error_codes = [item.code for item in findings if item.severity == "error"]
        self.assertEqual(error_codes, [])


if __name__ == "__main__":
    unittest.main()
