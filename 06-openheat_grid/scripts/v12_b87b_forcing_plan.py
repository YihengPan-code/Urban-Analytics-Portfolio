"""Audit the B8.7b forcing-day/hour/scenario plan from B8.5-F5.

Inputs:
    configs/v12/systemb_b87b_n300_execution_precheck.yaml, F5 pairwise label
    table, and optional F5 manifest/pre-execution metadata.
Outputs:
    b87b_forcing_design_audit.csv and b87b_expected_run_count.csv.
Saved metrics:
    Forcing day count, hour count, scenario count, target base versus
    overhead_as_canopy pair, per-slice expected multiplicity, and expected
    additional run count for 150 new candidates. This script does not create a
    run-ready manifest, runner, raster, QGIS/SOLWEIG execution, AOI/B9 output,
    local WBGT, hazard/risk score, or System A/B coupling.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean
from v12_b87b_input_inventory import config_list, load_config, out_path, path_exists_metadata
from v12_b87b_input_inventory import read_csv_rows, write_csv_rows


@dataclass(frozen=True)
class ForcingPlanResult:
    """B8.7b forcing-plan audit result."""

    status: str
    forcing_day_count: int
    hour_count: int
    scenario_count: int
    expected_additional_run_count: int
    headline: str


def sorted_numeric_text(values: set[str]) -> list[str]:
    """Sort numeric text values if possible."""
    return sorted(values, key=lambda value: int(value) if value.isdigit() else value)


def run(config_path: Path = DEFAULT_CONFIG) -> ForcingPlanResult:
    """Audit F5 forcing design and compute B8.7b expected run count."""
    config = load_config(config_path)
    pairwise = read_csv_rows(config["f5_pairwise_label_path"])
    manifest_exists, _ = path_exists_metadata(config.get("f5_manifest_path", ""))
    manifest = read_csv_rows(config["f5_manifest_path"]) if manifest_exists == "yes" else []

    forcing_days = sorted({clean(row.get("forcing_day_id")) for row in pairwise if clean(row.get("forcing_day_id"))})
    hours = sorted_numeric_text({clean(row.get("hour_sgt")) for row in pairwise if clean(row.get("hour_sgt"))})
    if manifest:
        scenarios = sorted({clean(row.get("scenario")) for row in manifest if clean(row.get("scenario"))})
        date_by_day = {
            clean(row.get("forcing_day_id")): clean(row.get("date"))
            for row in manifest
            if clean(row.get("forcing_day_id")) and clean(row.get("date"))
        }
        source = "f5_manifest_path"
    else:
        scenarios = config_list(config, "expected_scenarios")
        date_by_day = {}
        source = "f5_pairwise_label_path_plus_config_expected_scenarios"

    expected_days = int(config["expected_forcing_days"])
    expected_hours = int(config["expected_hours_per_day"])
    expected_scenarios = config_list(config, "expected_scenarios")
    expected_scenario_count = len(expected_scenarios)
    new_candidate_count = int(config["expected_new_candidate_count"])
    actual_multiplicity = len(forcing_days) * len(hours) * len(scenarios)
    expected_run_count = new_candidate_count * actual_multiplicity
    configured_planned = int(config["planned_additional_solweig_run_count"])
    design_matches_expected = (
        len(forcing_days) == expected_days
        and len(hours) == expected_hours
        and set(scenarios) == set(expected_scenarios)
    )
    status = "PASS" if design_matches_expected and expected_run_count == configured_planned else "WARN"

    audit_rows: list[dict[str, Any]] = []
    for forcing_day in forcing_days:
        for hour in hours:
            for scenario in scenarios:
                audit_rows.append(
                    {
                        "forcing_day_id": forcing_day,
                        "date": date_by_day.get(forcing_day, ""),
                        "hour_sgt": hour,
                        "scenario": scenario,
                        "expected_run_multiplicity": new_candidate_count,
                        "source": source,
                        "status": "PASS" if status == "PASS" else "WARN_ACTUAL_F5_DESIGN_REPORTED",
                        "claim_boundary": CLAIM_BOUNDARY,
                    }
                )
    write_csv_rows(
        out_path(config, "b87b_forcing_design_audit.csv"),
        audit_rows,
        [
            "forcing_day_id",
            "date",
            "hour_sgt",
            "scenario",
            "expected_run_multiplicity",
            "source",
            "status",
            "claim_boundary",
        ],
    )

    count_rows = [
        {
            "run_count_item": "additional_new_n150_candidate_runs",
            "cell_count": new_candidate_count,
            "forcing_day_count": len(forcing_days),
            "hour_count": len(hours),
            "scenario_count": len(scenarios),
            "expected_additional_run_count": expected_run_count,
            "configured_planned_run_count": configured_planned,
            "formula": (
                f"{new_candidate_count} new cells x {len(forcing_days)} forcing days x "
                f"{len(hours)} hours x {len(scenarios)} scenarios"
            ),
            "source": source,
            "status": status,
            "claim_boundary": CLAIM_BOUNDARY,
        }
    ]
    write_csv_rows(
        out_path(config, "b87b_expected_run_count.csv"),
        count_rows,
        [
            "run_count_item",
            "cell_count",
            "forcing_day_count",
            "hour_count",
            "scenario_count",
            "expected_additional_run_count",
            "configured_planned_run_count",
            "formula",
            "source",
            "status",
            "claim_boundary",
        ],
    )
    headline = (
        f"{len(forcing_days)} forcing days x {len(hours)} hours x {len(scenarios)} scenarios "
        f"= {expected_run_count} previewed additional runs"
    )
    return ForcingPlanResult(
        status=status,
        forcing_day_count=len(forcing_days),
        hour_count=len(hours),
        scenario_count=len(scenarios),
        expected_additional_run_count=expected_run_count,
        headline=headline,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Audit B8.7b forcing design from F5 labels/manifest and calculate "
            "expected new-candidate run count. Does not create an execution manifest."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
