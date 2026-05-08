from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def write_provenance(path: str | Path, *, feature: str, source: str, method: str, unit: str, known_issues: Iterable[str] | None = None) -> None:
    """Write a small YAML-like provenance file without requiring PyYAML."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    issues = list(known_issues or [])
    lines = [
        f"feature: {feature}",
        f"source: {source}",
        f"method: {method}",
        f"unit: {unit}",
        "known_issues:",
    ]
    if issues:
        lines += [f"  - {i}" for i in issues]
    else:
        lines += ["  - none recorded"]
    lines.append(f"last_updated_utc: {datetime.now(timezone.utc).isoformat()}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
