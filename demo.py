from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from mcp_why.cli import main


def run() -> None:
    print("== broken parentheses ==")
    main(["--config", str(ROOT / "examples/broken-parentheses.json")])
    print("\n== broken Windows npx ==")
    main(["--config", str(ROOT / "examples/broken-npx-windows.json")])
    print("\nDemo complete")


if __name__ == "__main__":
    run()
