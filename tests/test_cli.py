import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp_why import cli  # noqa: E402
from mcp_why.discover import discover_configs  # noqa: E402


class CliTests(unittest.TestCase):
    def test_cli_reports_risky_name_and_writes_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "claude_desktop_config.json"
            config.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "Home Assistant (ha-mcp)": {
                                "command": "npx",
                                "args": ["-y", "fake-server"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            output = Path(tmp) / "report.md"
            rc = cli.main(["--config", str(config), "--output", str(output)])
            self.assertEqual(rc, 1)
            text = output.read_text(encoding="utf-8")
            self.assertIn("risky_server_name", text)
            self.assertIn("windows_npx", text)

    def test_discover_finds_explicit_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mcp.json"
            path.write_text("{}", encoding="utf-8")
            found = discover_configs([str(path)])
            self.assertEqual(found[-1][1].resolve(), path.resolve())


if __name__ == "__main__":
    unittest.main()
