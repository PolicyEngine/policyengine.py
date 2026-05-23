import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.core import OutputCollection, Simulation
from policyengine.outputs import LaborSupplyResponse, ProgramStatistics
from policyengine.outputs.inequality import Inequality
from policyengine.tax_benefit_models.uk import analysis as uk_analysis
from policyengine.tax_benefit_models.uk.analysis import (
    UK_PROGRAMS,
    _validate_program_statistics_config,
)
from policyengine.tax_benefit_models.uk.datasets import (
    PolicyEngineUKDataset,
    UKYearData,
)
from policyengine.tax_benefit_models.uk.model import uk_latest


def _microdf(data: dict, weights: str) -> MicroDataFrame:
    return MicroDataFrame(pd.DataFrame(data), weights=weights)


def _empty_labor_supply_response() -> LaborSupplyResponse:
    return LaborSupplyResponse.model_construct()


PROGRAM_VALUES = {
    "income_tax": [100.0, 0.0],
    "national_insurance": [0.0, 200.0],
    "vat": [300.0, 0.0],
    "council_tax": [0.0, 400.0],
    "fuel_duty": [500.0, 0.0],
    "ni_employer": [0.0, 600.0],
    "universal_credit": [700.0, 0.0],
    "child_benefit": [0.0, 800.0],
    "pension_credit": [900.0, 0.0],
    "income_support": [0.0, 1_000.0],
    "tax_credits": [1_100.0, 0.0],
    "working_tax_credit": [0.0, 1_200.0],
    "child_tax_credit": [1_300.0, 0.0],
    "state_pension": [0.0, 1_400.0],
}


def _weighted_values(
    values: list[float],
    multiplier: float,
    row_count: int,
) -> list[float]:
    return [values[index % len(values)] * multiplier for index in range(row_count)]


def _weights(row_count: int) -> list[float]:
    if row_count == 2:
        return [1.0, 2.0]
    return [1.0] * row_count


def _program_columns_by_entity(
    multiplier: float,
    row_count: int,
) -> dict[str, dict[str, list[float]]]:
    program_columns_by_entity = {entity: {} for entity in uk_latest.entity_variables}
    for program, values in PROGRAM_VALUES.items():
        entity = uk_latest.get_variable(program).entity
        program_columns_by_entity[entity][program] = _weighted_values(
            values,
            multiplier,
            row_count,
        )
    return program_columns_by_entity


def _make_uk_output_simulation(
    tmp_path,
    simulation_id: str,
    multiplier: float,
    row_count: int = 2,
):
    ids = list(range(1, row_count + 1))
    weights = _weights(row_count)
    program_columns_by_entity = _program_columns_by_entity(multiplier, row_count)
    data = UKYearData(
        person=_microdf(
            {
                "person_id": ids,
                "benunit_id": ids,
                "household_id": ids,
                "person_weight": weights,
                **program_columns_by_entity["person"],
            },
            "person_weight",
        ),
        benunit=_microdf(
            {
                "benunit_id": ids,
                "benunit_weight": weights,
                **program_columns_by_entity["benunit"],
            },
            "benunit_weight",
        ),
        household=_microdf(
            {
                "household_id": ids,
                "household_weight": weights,
                **program_columns_by_entity["household"],
            },
            "household_weight",
        ),
    )
    dataset = PolicyEngineUKDataset(
        id=simulation_id,
        name=f"{simulation_id} output",
        description="Mocked UK output dataset for program statistics",
        filepath=str(tmp_path / f"{simulation_id}.h5"),
        year=2026,
        is_output_dataset=True,
        data=data,
    )
    return Simulation(
        id=simulation_id,
        dataset=dataset,
        tax_benefit_model_version=uk_latest,
        output_dataset=dataset,
    )


def test_uk_program_statistics_config_runs_against_mocked_outputs(tmp_path):
    baseline = _make_uk_output_simulation(tmp_path, "baseline", 1.0)
    reform = _make_uk_output_simulation(tmp_path, "reform", 2.0)

    _validate_program_statistics_config(baseline, reform)

    model_version = baseline.tax_benefit_model_version
    results = {}
    for program_name, program_info in UK_PROGRAMS.items():
        stats = ProgramStatistics(
            baseline_simulation=baseline,
            reform_simulation=reform,
            program_name=program_name,
            entity=model_version.get_variable(program_name).entity,
            is_tax=program_info["is_tax"],
        )
        stats.run()
        results[program_name] = stats

    assert set(results) == set(UK_PROGRAMS)
    assert results["fuel_duty"].baseline_total == 500.0
    assert results["state_pension"].baseline_total == 2_800.0
    assert results["ni_employer"].baseline_total == 1_200.0
    assert results["tax_credits"].baseline_total == 1_100.0
    assert results["fuel_duty"].is_tax is True
    assert results["ni_employer"].is_tax is True
    assert results["state_pension"].is_tax is False
    assert results["tax_credits"].is_tax is False


def test_uk_economic_impact_analysis_returns_configured_program_statistics(
    tmp_path,
    monkeypatch,
):
    baseline = _make_uk_output_simulation(
        tmp_path,
        "baseline",
        1.0,
        row_count=101,
    )
    reform = _make_uk_output_simulation(
        tmp_path,
        "reform",
        2.0,
        row_count=101,
    )

    monkeypatch.setattr(Simulation, "ensure", lambda self: None)
    monkeypatch.setattr(
        uk_analysis,
        "calculate_decile_impacts",
        lambda **kwargs: OutputCollection(outputs=[], dataframe=pd.DataFrame()),
    )
    monkeypatch.setattr(
        uk_analysis,
        "compute_intra_decile_impacts",
        lambda **kwargs: OutputCollection(outputs=[], dataframe=pd.DataFrame()),
    )
    monkeypatch.setattr(
        uk_analysis,
        "calculate_uk_poverty_rates",
        lambda simulation: OutputCollection(outputs=[], dataframe=pd.DataFrame()),
    )
    monkeypatch.setattr(
        uk_analysis,
        "calculate_uk_inequality",
        lambda simulation: Inequality(
            simulation=simulation,
            income_variable="household_net_income",
        ),
    )
    monkeypatch.setattr(
        uk_analysis,
        "configure_labor_supply_response_variables",
        lambda baseline_simulation, reform_simulation, country_code: None,
    )
    monkeypatch.setattr(
        uk_analysis,
        "calculate_labor_supply_response",
        lambda baseline_simulation, reform_simulation, country_code: (
            _empty_labor_supply_response()
        ),
    )

    result = uk_analysis.economic_impact_analysis(baseline, reform)

    program_names = {
        program.program_name for program in result.program_statistics.outputs
    }
    assert program_names == set(UK_PROGRAMS)
    assert set(result.program_statistics.dataframe["program_name"]) == set(UK_PROGRAMS)


def test_uk_program_statistics_config_fails_before_simulation_run(
    tmp_path, monkeypatch
):
    baseline = _make_uk_output_simulation(tmp_path, "baseline", 1.0)
    reform = _make_uk_output_simulation(tmp_path, "reform", 2.0)

    entity_variables = {
        entity: list(variables)
        for entity, variables in uk_latest.entity_variables.items()
    }
    entity_variables["household"].remove("fuel_duty")
    monkeypatch.setattr(
        baseline.tax_benefit_model_version,
        "entity_variables",
        entity_variables,
    )

    with pytest.raises(
        ValueError, match="UK program statistics config is invalid"
    ) as exc_info:
        _validate_program_statistics_config(baseline, reform)

    assert "fuel_duty" in str(exc_info.value)


def test_uk_programs_entities_match_model_metadata():
    expected_entities = {
        "fuel_duty": "household",
        "state_pension": "person",
        "ni_employer": "person",
        "tax_credits": "benunit",
    }

    for program_name in UK_PROGRAMS:
        assert program_name in uk_latest.variables_by_name, (
            f"{program_name} is not defined in the UK model"
        )

    for program_name, entity in expected_entities.items():
        assert uk_latest.get_variable(program_name).entity == entity
