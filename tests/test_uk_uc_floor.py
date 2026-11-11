"""Tests for the UK Universal Credit coverage floor."""

import pytest

from policyengine.provenance.uk_uc_floor import (
    evaluate_uc_floor,
    load_uc_floor_benchmarks,
    measure_great_britain_uc,
)


def test_benchmarks_cite_a_source_for_every_measure():
    benchmarks = load_uc_floor_benchmarks()

    assert benchmarks.tolerance == 0.1
    assert benchmarks.geography == "great_britain"
    assert 2025 in benchmarks.years
    for year in benchmarks.years.values():
        for benchmark in (year.benefit_units, year.spend):
            assert benchmark.value > 0
            assert benchmark.source
            assert benchmark.url.startswith("https://")


def test_floor_passes_within_tolerance_and_fails_outside_it():
    year = load_uc_floor_benchmarks().years[2025]

    passing = evaluate_uc_floor(
        benefit_units=year.benefit_units.value * 0.95,
        spend=year.spend.value * 1.09,
        year=2025,
        dataset="candidate",
    )
    failing = evaluate_uc_floor(
        benefit_units=year.benefit_units.value * 0.5,
        spend=year.spend.value,
        year=2025,
        dataset="candidate",
    )

    assert passing.passed
    assert not failing.passed
    measures = {measure.name: measure for measure in failing.measures}
    assert not measures["benefit_units"].passed
    assert measures["benefit_units"].ratio == pytest.approx(0.5)
    assert measures["spend"].passed


def test_floor_refuses_a_year_without_benchmarks():
    with pytest.raises(ValueError, match="No Universal Credit floor benchmarks"):
        evaluate_uc_floor(benefit_units=1, spend=1, year=2019, dataset="candidate")


def test_measurement_excludes_northern_ireland():
    from policyengine_uk import Simulation

    simulation = Simulation(
        situation={
            "people": {
                "a": {"age": {2025: 30}},
                "b": {"age": {2025: 40}},
                "c": {"age": {2025: 50}},
            },
            "benunits": {
                "ni_one": {"members": ["a"]},
                "ni_two": {"members": ["b"]},
                "london": {"members": ["c"]},
            },
            "households": {
                "belfast": {
                    "members": ["a", "b"],
                    "region": {2025: "NORTHERN_IRELAND"},
                },
                "london": {"members": ["c"], "region": {2025: "LONDON"}},
            },
        }
    )
    universal_credit = simulation.calculate("universal_credit", 2025)
    assert (universal_credit > 0).all()

    benefit_units, spend = measure_great_britain_uc(simulation, 2025)

    assert benefit_units == pytest.approx(1)
    assert spend == pytest.approx(float(universal_credit[2]))
