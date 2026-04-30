import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import Simulation
from policyengine.outputs import ProgramStatistics
from policyengine.tax_benefit_models.us.analysis import (
    US_PROGRAMS,
    _validate_program_statistics_config,
)
from policyengine.tax_benefit_models.us.datasets import (
    PolicyEngineUSDataset,
    USYearData,
)
from policyengine.tax_benefit_models.us.model import us_latest


def _microdf(data: dict, weights: str) -> MicroDataFrame:
    return MicroDataFrame(pd.DataFrame(data), weights=weights)


def _make_us_output_simulation(tmp_path, simulation_id: str, multiplier: float):
    data = USYearData(
        person=_microdf(
            {
                "person_id": [1, 2],
                "household_id": [1, 2],
                "marital_unit_id": [1, 2],
                "family_id": [1, 2],
                "spm_unit_id": [1, 2],
                "tax_unit_id": [1, 2],
                "person_weight": [1.0, 2.0],
                "ssi": [100.0 * multiplier, 0.0],
                "social_security": [0.0, 200.0 * multiplier],
                "medicare_cost": [300.0 * multiplier, 0.0],
                "medicaid": [0.0, 400.0 * multiplier],
            },
            "person_weight",
        ),
        marital_unit=_microdf(
            {
                "marital_unit_id": [1, 2],
                "marital_unit_weight": [1.0, 2.0],
            },
            "marital_unit_weight",
        ),
        family=_microdf(
            {
                "family_id": [1, 2],
                "family_weight": [1.0, 2.0],
            },
            "family_weight",
        ),
        spm_unit=_microdf(
            {
                "spm_unit_id": [1, 2],
                "spm_unit_weight": [1.0, 2.0],
                "snap": [500.0 * multiplier, 0.0],
                "tanf": [0.0, 600.0 * multiplier],
            },
            "spm_unit_weight",
        ),
        tax_unit=_microdf(
            {
                "tax_unit_id": [1, 2],
                "tax_unit_weight": [1.0, 2.0],
                "income_tax": [700.0 * multiplier, 0.0],
                "employee_payroll_tax": [0.0, 800.0 * multiplier],
                "household_state_income_tax": [900.0 * multiplier, 0.0],
                "eitc": [0.0, 1_000.0 * multiplier],
                "ctc": [1_100.0 * multiplier, 0.0],
            },
            "tax_unit_weight",
        ),
        household=_microdf(
            {
                "household_id": [1, 2],
                "household_weight": [1.0, 2.0],
            },
            "household_weight",
        ),
    )
    dataset = PolicyEngineUSDataset(
        id=simulation_id,
        name=f"{simulation_id} output",
        description="Mocked US output dataset for program statistics",
        filepath=str(tmp_path / f"{simulation_id}.h5"),
        year=2026,
        is_output_dataset=True,
        data=data,
    )
    return Simulation(
        id=simulation_id,
        dataset=dataset,
        tax_benefit_model_version=us_latest,
        output_dataset=dataset,
    )


def test_us_program_statistics_config_runs_against_mocked_outputs(tmp_path):
    baseline = _make_us_output_simulation(tmp_path, "baseline", 1.0)
    reform = _make_us_output_simulation(tmp_path, "reform", 2.0)

    _validate_program_statistics_config(baseline, reform)

    results = {}
    for program_name, program_info in US_PROGRAMS.items():
        stats = ProgramStatistics(
            baseline_simulation=baseline,
            reform_simulation=reform,
            program_name=program_name,
            variable_name=program_info.get("variable_name", program_name),
            entity=program_info["entity"],
            is_tax=program_info["is_tax"],
        )
        stats.run()
        results[program_name] = stats

    assert set(results) == set(US_PROGRAMS)
    assert results["employee_payroll_tax"].baseline_total == 1_600.0
    assert results["medicare_cost"].baseline_total == 300.0
    assert results["state_income_tax"].variable_name == "household_state_income_tax"
    assert results["state_income_tax"].baseline_total == 900.0


def test_us_program_statistics_config_fails_before_simulation_run(
    tmp_path, monkeypatch
):
    baseline = _make_us_output_simulation(tmp_path, "baseline", 1.0)
    reform = _make_us_output_simulation(tmp_path, "reform", 2.0)

    entity_variables = {
        entity: list(variables)
        for entity, variables in us_latest.entity_variables.items()
    }
    entity_variables["person"].remove("medicare_cost")
    monkeypatch.setattr(
        baseline.tax_benefit_model_version,
        "entity_variables",
        entity_variables,
    )

    try:
        _validate_program_statistics_config(baseline, reform)
    except ValueError as exc:
        assert "US program statistics config is invalid" in str(exc)
        assert "medicare_cost" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
