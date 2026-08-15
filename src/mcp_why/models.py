from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    summary: str
    detail: str = ""
    client: str = ""
    server: str = ""
    path: str = ""
    hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    configs: list[str] = field(default_factory=list)
    servers: int = 0

    @property
    def errors(self) -> int:
        return sum(1 for item in self.findings if item.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for item in self.findings if item.severity == "warning")
