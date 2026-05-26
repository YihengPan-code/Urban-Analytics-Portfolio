"""Detect local QGIS/UMEP/SOLWEIG execution candidates for Sprint B3.

Inputs:
  - Local PATH and common Windows QGIS/OSGeo4W install paths.

Outputs:
  - outputs/v12_solweig_n24_execution/qgis_environment_candidates.csv
  - outputs/v12_solweig_n24_execution/qgis_environment_detection.md

Saved metrics:
  - candidate executable path, kind, availability, version/probe status.
  - qgis_process provider/algorithm query outcome when safely invocable.

This script does not install packages and does not execute SOLWEIG.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/v12_solweig_n24_execution"


@dataclass
class Candidate:
    kind: str
    command: str
    exists: bool
    probe_status: str
    probe_output: str


def run_probe(command: str, args: list[str], timeout_s: int = 45) -> tuple[str, str]:
    try:
        proc = subprocess.run(
            [command, *args],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
        out = (proc.stdout + proc.stderr).strip()
        return f"exit_{proc.returncode}", out[:4000]
    except Exception as exc:
        return "probe_failed", str(exc)


def find_candidates() -> list[Candidate]:
    paths: list[tuple[str, str]] = []
    for exe in ["qgis_process", "qgis_process-qgis-ltr", "qgis", "qgis-bin", "python-qgis"]:
        found = shutil.which(exe)
        if found:
            paths.append((exe, found))

    common = [
        r"C:\OSGeo4W\bin\qgis_process-qgis-ltr.bat",
        r"C:\OSGeo4W\bin\qgis_process.bat",
        r"C:\OSGeo4W\bin\qgis-ltr-bin.exe",
        r"C:\OSGeo4W\bin\qgis-bin.exe",
        r"C:\Program Files\QGIS 3.44.3\bin\qgis_process-qgis-ltr.bat",
        r"C:\Program Files\QGIS 3.44.3\bin\qgis_process-qgis.bat",
        r"C:\Program Files\QGIS 3.44.3\bin\qgis_process.bat",
        r"C:\Program Files\QGIS 3.44.3\bin\python-qgis.bat",
        r"C:\Program Files\QGIS 3.44.3\bin\qgis-ltr-bin.exe",
        r"C:\Program Files\QGIS 3.44.3\bin\qgis-bin.exe",
        r"C:\Program Files\QGIS 3.44.3\apps\qgis\bin\qgis_process.exe",
        r"C:\Program Files\QGIS 3.42.0\bin\qgis_process-qgis-ltr.bat",
        r"C:\Program Files\QGIS 3.42.0\bin\qgis_process.bat",
        r"C:\Program Files\QGIS 3.40.0\bin\qgis_process-qgis-ltr.bat",
        r"C:\Program Files\QGIS 3.40.0\bin\qgis_process.bat",
    ]
    for p in common:
        path = Path(p)
        if path.exists():
            paths.append((path.name, str(path)))

    seen = set()
    unique = []
    for kind, command in paths:
        key = command.lower()
        if key not in seen:
            seen.add(key)
            unique.append((kind, command))

    candidates: list[Candidate] = []
    for kind, command in unique:
        if "qgis_process" in kind.lower() or "qgis_process" in command.lower():
            status, output = run_probe(command, ["--version"])
        elif "python-qgis" in kind.lower():
            status, output = run_probe(command, ["--version"])
        else:
            status, output = "not_probed", "GUI executable candidate; not launched from preflight."
        candidates.append(Candidate(kind=kind, command=command, exists=True, probe_status=status, probe_output=output))
    if not candidates:
        candidates.append(Candidate("none", "", False, "missing", "No qgis_process/qgis/python-qgis candidate found on PATH or common Windows paths."))
    return candidates


def probe_algorithms(candidates: list[Candidate]) -> tuple[str, str]:
    qgis_process = next((c.command for c in candidates if c.exists and "qgis_process" in c.command.lower()), "")
    if not qgis_process:
        return "not_run", "No qgis_process candidate was available for provider/algorithm listing."
    status, output = run_probe(qgis_process, ["list"], timeout_s=90)
    matches = []
    for line in output.splitlines():
        low = line.lower()
        if any(token in low for token in ["solweig", "umep", "sky view", "svf", "wall height", "wall aspect", "outdoor thermal comfort"]):
            matches.append(line)
    if matches:
        return status, "\n".join(matches[:300])
    return status, output[:4000]


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect QGIS/UMEP/SOLWEIG candidates without executing SOLWEIG.")
    parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = find_candidates()
    alg_status, alg_output = probe_algorithms(candidates)
    df = pd.DataFrame([c.__dict__ for c in candidates])
    df.to_csv(OUT_DIR / "qgis_environment_candidates.csv", index=False)

    qgis_available = any(c.exists and c.probe_status.startswith("exit_0") and "qgis_process" in c.command.lower() for c in candidates)
    solweig_seen = "solweig" in alg_output.lower()
    umep_seen = "umep" in alg_output.lower()
    status = "PASS" if qgis_available and solweig_seen else "BLOCKED"

    lines = [
        "# Sprint B3 QGIS / UMEP Environment Detection",
        "",
        f"Status: **{status}**",
        "",
        f"- qgis_process available: `{qgis_available}`",
        f"- UMEP mention in algorithm query: `{umep_seen}`",
        f"- SOLWEIG mention in algorithm query: `{solweig_seen}`",
        f"- algorithm query status: `{alg_status}`",
        "",
        "## Candidates",
        "",
        df[["kind", "command", "exists", "probe_status"]].to_markdown(index=False),
        "",
        "## Algorithm Query Snippet",
        "",
        "```text",
        alg_output if alg_output else "(empty)",
        "```",
        "",
        "## Manual QGIS Python Console Instructions",
        "",
        "If this report is BLOCKED but QGIS is installed, open QGIS with UMEP enabled, then run:",
        "",
        "```python",
        "from pathlib import Path",
        "script = Path(r'C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid/scripts/qgis/v12_b3_n24_run_solweig_from_manifest.py')",
        "exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'))",
        "```",
        "",
        "Do not run from the conda openheat Python; QGIS Processing and UMEP must be loaded in the QGIS Python environment.",
    ]
    (OUT_DIR / "qgis_environment_detection.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[{status}] wrote QGIS detection outputs under {OUT_DIR}")
    if status != "PASS":
        raise SystemExit("BLOCKED: QGIS/UMEP/SOLWEIG environment not confirmed.")


if __name__ == "__main__":
    main()
