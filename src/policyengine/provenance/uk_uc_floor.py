"""Universal Credit coverage floor for UK certification candidates.

In August 2026 (#491) the UK default was reverted after a certified dataset
carried about half of Universal Credit's caseload and spend: its calibration
had no benefit targets, and no check compared its outputs with administrative
totals. This is the standing floor #491 proposed. A candidate dataset's
benefit units with Universal Credit, and its Universal Credit spend, in Great
Britain must each be within 10% of DWP's and the OBR's figures for the same
year.

Both benchmarks cover Great Britain (Northern Ireland's Universal Credit is
administered separately), so Northern Ireland households are excluded from
the measurement. The receipt holds weighted national totals only.

Run it with ``scripts/check_uk_uc_floor.py``.
"""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Optional

import numpy as np
from pydantic import BaseModel

UC_FLOOR_RESOURCE = ("data", "qualification", "uk_uc_floor.json")
NORTHERN_IRELAND_REGION = "NORTHERN_IRELAND"


class UCFloorBenchmark(BaseModel):
    value: float
    source: str
    url: str


class UCFloorYear(BaseModel):
    benefit_units: UCFloorBenchmark
    spend: UCFloorBenchmark


class UCFloorBenchmarks(BaseModel):
    schema_version: int
    description: str
    tolerance: float
    geography: str
    years: dict[int, UCFloorYear]


class UCFloorMeasure(BaseModel):
    name: str
    measured: float
    benchmark: float
    ratio: float
    passed: bool
    source: str


class UCFloorReceipt(BaseModel):
    schema_version: int = 1
    check: str = "uk_uc_floor"
    dataset: str
    year: int
    geography: str
    tolerance: float
    model_version: Optional[str] = None
    measures: list[UCFloorMeasure]
    passed: bool


def load_uc_floor_benchmarks() -> UCFloorBenchmarks:
    resource = files("policyengine").joinpath(*UC_FLOOR_RESOURCE)
    return UCFloorBenchmarks.model_validate(json.loads(resource.read_text()))


def measure_great_britain_uc(simulation, year: int) -> tuple[float, float]:
    """Return weighted (benefit units with UC, UC spend) in Great Britain."""
    universal_credit = np.asarray(
        simulation.calculate("universal_credit", year), dtype=float
    )
    weights = np.asarray(simulation.calculate("benunit_weight", year), dtype=float)
    northern_ireland_household = (
        np.asarray(simulation.calculate("region", year)).astype(str)
        == NORTHERN_IRELAND_REGION
    ).astype(float)
    # Mapping to benefit units spreads a household's value over its members;
    # any positive share marks a benefit unit in a Northern Ireland household.
    northern_ireland = (
        np.asarray(
            simulation.map_result(northern_ireland_household, "household", "benunit"),
            dtype=float,
        )
        > 0
    )
    great_britain = ~northern_ireland
    benefit_units = float(weights[great_britain & (universal_credit > 0)].sum())
    spend = float((universal_credit * weights)[great_britain].sum())
    return benefit_units, spend


def evaluate_uc_floor(
    *,
    benefit_units: float,
    spend: float,
    year: int,
    dataset: str,
    model_version: Optional[str] = None,
    benchmarks: Optional[UCFloorBenchmarks] = None,
) -> UCFloorReceipt:
    benchmarks = benchmarks or load_uc_floor_benchmarks()
    if year not in benchmarks.years:
        raise ValueError(
            f"No Universal Credit floor benchmarks for {year}; "
            f"available years: {sorted(benchmarks.years)}"
        )
    year_benchmarks = benchmarks.years[year]
    measures = []
    for name, measured, benchmark in (
        ("benefit_units", benefit_units, year_benchmarks.benefit_units),
        ("spend", spend, year_benchmarks.spend),
    ):
        ratio = measured / benchmark.value
        measures.append(
            UCFloorMeasure(
                name=name,
                measured=measured,
                benchmark=benchmark.value,
                ratio=ratio,
                passed=abs(ratio - 1) <= benchmarks.tolerance,
                source=benchmark.source,
            )
        )
    return UCFloorReceipt(
        dataset=dataset,
        year=year,
        geography=benchmarks.geography,
        tolerance=benchmarks.tolerance,
        model_version=model_version,
        measures=measures,
        passed=all(measure.passed for measure in measures),
    )


def check_uc_floor(dataset_path: str, year: int, *, dataset: str) -> UCFloorReceipt:
    """Measure a UK dataset file and evaluate it against the floor."""
    from importlib.metadata import version

    from policyengine_uk import Microsimulation

    benefit_units, spend = measure_great_britain_uc(
        Microsimulation(dataset=dataset_path), year
    )
    return evaluate_uc_floor(
        benefit_units=benefit_units,
        spend=spend,
        year=year,
        dataset=dataset,
        model_version=version("policyengine-uk"),
    )
