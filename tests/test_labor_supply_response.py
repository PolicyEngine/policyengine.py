import datetime
from typing import Optional

import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.core import Dynamic, Parameter, ParameterValue, Simulation
from policyengine.outputs import (
    LaborSupplyResponse,
    calculate_labor_supply_response,
    configure_labor_supply_response_variables,
)
from policyengine.tax_benefit_models.uk.analysis import (
    PolicyReformAnalysis as UKPolicyReformAnalysis,
)
from policyengine.tax_benefit_models.uk.datasets import (
    PolicyEngineUKDataset,
    UKYearData,
)
from policyengine.tax_benefit_models.uk.model import uk_latest
from policyengine.tax_benefit_models.us.analysis import (
    PolicyReformAnalysis as USPolicyReformAnalysis,
    economic_impact_analysis as us_economic_impact_analysis,
)
from policyengine.tax_benefit_models.us.datasets import (
    PolicyEngineUSDataset,
    USYearData,
)
from policyengine.tax_benefit_models.us.model import us_latest

US_EXPECTED_LSR_EXTRA_VARIABLES = [
    "self_employment_income",
    "weekly_hours_worked",
    "income_elasticity_lsr",
    "substitution_elasticity_lsr",
    "weekly_hours_worked_behavioural_response_income_elasticity",
    "weekly_hours_worked_behavioural_response_substitution_elasticity",
]


def _microdf(data: dict, weights: str) -> MicroDataFrame:
    return MicroDataFrame(pd.DataFrame(data), weights=weights)


def _replace_entity_frame(
    simulation: Simulation,
    entity: str,
    data: pd.DataFrame,
    weights: str,
) -> None:
    setattr(
        simulation.output_dataset.data,
        entity,
        MicroDataFrame(data, weights=weights),
    )


def _set_us_fixture_weights_and_household_index(
    simulation: Simulation,
) -> None:
    person = pd.DataFrame(simulation.output_dataset.data.person).copy()
    person["person_weight"] = [2.0, 2.0, 3.0]
    _replace_entity_frame(simulation, "person", person, "person_weight")

    household = pd.DataFrame(simulation.output_dataset.data.household).copy()
    household["household_weight"] = [2.0, 3.0]
    household.index = [10, 20]
    _replace_entity_frame(simulation, "household", household, "household_weight")


def _lsr_dynamic() -> Dynamic:
    return Dynamic(
        name="Mock labor-supply response",
        simulation_modifier=lambda microsim: microsim,
    )


def _dynamic_with_parameter(
    parameter_name: str,
    *,
    model_version,
) -> Dynamic:
    return Dynamic(
        name="Mock parameterized labor-supply response",
        parameter_values=[
            ParameterValue(
                parameter=Parameter(
                    name=parameter_name,
                    tax_benefit_model_version=model_version,
                ),
                start_date=datetime.datetime(2026, 1, 1),
                value=0.1,
            )
        ],
    )


def _make_us_lsr_simulation(
    tmp_path,
    simulation_id: str,
    *,
    include_lsr: bool,
    is_reform: bool = False,
    dynamic: Optional[Dynamic] = None,
) -> Simulation:
    person = {
        "person_id": [1, 2, 3],
        "household_id": [1, 1, 2],
        "marital_unit_id": [1, 1, 2],
        "family_id": [1, 1, 2],
        "spm_unit_id": [1, 1, 2],
        "tax_unit_id": [1, 1, 2],
        "person_weight": [1.0, 1.0, 1.0],
        "employment_income": [100.0, 100.0, 100.0],
        "self_employment_income": [0.0, 0.0, 50.0],
        "weekly_hours_worked": [42.0, 22.0, 35.0] if is_reform else [40.0, 20.0, 30.0],
    }
    if include_lsr:
        person.update(
            {
                "income_elasticity_lsr": [20.0, 30.0, 50.0]
                if is_reform
                else [10.0, 20.0, 30.0],
                "substitution_elasticity_lsr": [10.0, 15.0, 20.0]
                if is_reform
                else [5.0, 5.0, 10.0],
                "weekly_hours_worked_behavioural_response_income_elasticity": [
                    2.0,
                    3.0,
                    5.0,
                ]
                if is_reform
                else [1.0, 2.0, 3.0],
                "weekly_hours_worked_behavioural_response_substitution_elasticity": [
                    1.0,
                    2.0,
                    3.0,
                ]
                if is_reform
                else [0.5, 1.0, 1.5],
            }
        )

    data = USYearData(
        person=_microdf(person, "person_weight"),
        marital_unit=_microdf(
            {
                "marital_unit_id": [1, 2],
                "marital_unit_weight": [1.0, 1.0],
            },
            "marital_unit_weight",
        ),
        family=_microdf(
            {
                "family_id": [1, 2],
                "family_weight": [1.0, 1.0],
            },
            "family_weight",
        ),
        spm_unit=_microdf(
            {
                "spm_unit_id": [1, 2],
                "spm_unit_weight": [1.0, 1.0],
            },
            "spm_unit_weight",
        ),
        tax_unit=_microdf(
            {
                "tax_unit_id": [1, 2],
                "tax_unit_weight": [1.0, 1.0],
            },
            "tax_unit_weight",
        ),
        household=_microdf(
            {
                "household_id": [1, 2],
                "household_weight": [1.0, 1.0],
                "household_income_decile": [1, 2],
            },
            "household_weight",
        ),
    )
    dataset = PolicyEngineUSDataset(
        id=simulation_id,
        name=f"{simulation_id} output",
        description="Mocked US output dataset for labor-supply response",
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
        dynamic=dynamic,
    )


def _make_uk_lsr_simulation(
    tmp_path,
    simulation_id: str,
    *,
    include_lsr: bool,
    is_reform: bool = False,
    dynamic: Optional[Dynamic] = None,
) -> Simulation:
    person = {
        "person_id": [1, 2],
        "benunit_id": [1, 2],
        "household_id": [1, 2],
        "person_weight": [1.0, 1.0],
        "employment_income": [100.0, 200.0],
        "self_employment_income": [50.0, 0.0],
    }
    if include_lsr:
        person.update(
            {
                "income_elasticity_lsr": [15.0, 30.0] if is_reform else [10.0, 20.0],
                "substitution_elasticity_lsr": [7.0, 14.0]
                if is_reform
                else [5.0, 10.0],
            }
        )

    data = UKYearData(
        person=_microdf(person, "person_weight"),
        benunit=_microdf(
            {
                "benunit_id": [1, 2],
                "benunit_weight": [1.0, 1.0],
            },
            "benunit_weight",
        ),
        household=_microdf(
            {
                "household_id": [1, 2],
                "household_weight": [1.0, 1.0],
                "household_income_decile": [1, 2],
            },
            "household_weight",
        ),
    )
    dataset = PolicyEngineUKDataset(
        id=simulation_id,
        name=f"{simulation_id} output",
        description="Mocked UK output dataset for labor-supply response",
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
        dynamic=dynamic,
    )


def test_policy_reform_analysis_models_include_labor_supply_response():
    assert (
        USPolicyReformAnalysis.model_fields["labor_supply_response"].annotation
        is LaborSupplyResponse
    )
    assert (
        UKPolicyReformAnalysis.model_fields["labor_supply_response"].annotation
        is LaborSupplyResponse
    )


def test_us_default_outputs_do_not_include_optional_lsr_support_variables():
    assert "self_employment_income" not in us_latest.entity_variables["person"]
    assert "weekly_hours_worked" not in us_latest.entity_variables["person"]


def test_configure_labor_supply_response_variables_adds_us_extras(tmp_path):
    baseline = _make_us_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=False,
    )
    reform = _make_us_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=False,
        is_reform=True,
        dynamic=_lsr_dynamic(),
    )

    assert configure_labor_supply_response_variables(
        baseline,
        reform,
        country_code="us",
    )
    assert baseline.extra_variables["person"] == US_EXPECTED_LSR_EXTRA_VARIABLES
    assert reform.extra_variables == baseline.extra_variables


def test_configure_labor_supply_response_variables_detects_us_parameter_values(
    tmp_path,
):
    baseline = _make_us_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=False,
    )
    reform = _make_us_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=False,
        is_reform=True,
        dynamic=_dynamic_with_parameter(
            "gov.simulation.labor_supply_responses.elasticities.income",
            model_version=us_latest,
        ),
    )

    assert configure_labor_supply_response_variables(
        baseline,
        reform,
        country_code="us",
    )
    assert baseline.extra_variables["person"] == US_EXPECTED_LSR_EXTRA_VARIABLES
    assert reform.extra_variables == baseline.extra_variables


def test_configure_labor_supply_response_variables_detects_us_parameter_descendants(
    tmp_path,
):
    baseline = _make_us_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=False,
    )
    reform = _make_us_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=False,
        is_reform=True,
        dynamic=_dynamic_with_parameter(
            "gov.simulation.labor_supply_responses.elasticities.substitution.all",
            model_version=us_latest,
        ),
    )

    assert configure_labor_supply_response_variables(
        baseline,
        reform,
        country_code="us",
    )
    assert baseline.extra_variables["person"] == US_EXPECTED_LSR_EXTRA_VARIABLES
    assert reform.extra_variables == baseline.extra_variables


def test_configure_labor_supply_response_variables_detects_policy_mapping_parameters(
    tmp_path,
):
    baseline = _make_us_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=False,
    )
    reform = _make_us_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=False,
        is_reform=True,
    )
    reform.policy = {"gov.simulation.labor_supply_responses.elasticities.income": 0.1}

    assert configure_labor_supply_response_variables(
        baseline,
        reform,
        country_code="us",
    )
    assert baseline.extra_variables["person"] == US_EXPECTED_LSR_EXTRA_VARIABLES
    assert reform.extra_variables == baseline.extra_variables


@pytest.mark.parametrize(
    "parameter_name",
    [
        "gov.simulation.labour_supply_responses.income_elasticity",
        "gov.simulation.labor_supply_responses.income_elasticity",
    ],
)
def test_configure_labor_supply_response_variables_detects_uk_parameter_values(
    tmp_path,
    parameter_name,
):
    baseline = _make_uk_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=False,
    )
    reform = _make_uk_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=False,
        is_reform=True,
        dynamic=_dynamic_with_parameter(
            parameter_name,
            model_version=uk_latest,
        ),
    )

    assert configure_labor_supply_response_variables(
        baseline,
        reform,
        country_code="uk",
    )
    assert baseline.extra_variables["person"] == [
        "income_elasticity_lsr",
        "substitution_elasticity_lsr",
    ]
    assert reform.extra_variables == baseline.extra_variables


@pytest.mark.parametrize(
    ("country_code", "parameter_name", "model_version"),
    [
        (
            "us",
            "gov.simulation.labor_supply_responses.elasticities.income_support",
            us_latest,
        ),
        (
            "uk",
            "gov.simulation.labour_supply_responses.income_elasticity_adjustment",
            uk_latest,
        ),
    ],
)
def test_configure_labor_supply_response_variables_ignores_parameter_siblings(
    tmp_path,
    country_code,
    parameter_name,
    model_version,
):
    make_simulation = (
        _make_us_lsr_simulation if country_code == "us" else _make_uk_lsr_simulation
    )
    baseline = make_simulation(
        tmp_path,
        "baseline",
        include_lsr=False,
    )
    reform = make_simulation(
        tmp_path,
        "reform",
        include_lsr=False,
        is_reform=True,
        dynamic=_dynamic_with_parameter(
            parameter_name,
            model_version=model_version,
        ),
    )

    assert not configure_labor_supply_response_variables(
        baseline,
        reform,
        country_code=country_code,
    )
    assert baseline.extra_variables == {}
    assert reform.extra_variables == {}


def test_configure_labor_supply_response_variables_ignores_inactive_runs(tmp_path):
    baseline = _make_us_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=False,
    )
    reform = _make_us_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=False,
        is_reform=True,
    )

    assert not configure_labor_supply_response_variables(
        baseline,
        reform,
        country_code="us",
    )
    assert baseline.extra_variables == {}
    assert reform.extra_variables == {}


def test_us_economic_impact_analysis_configures_lsr_extras_before_ensure(
    tmp_path,
    monkeypatch,
):
    baseline = _make_us_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=False,
    )
    reform = _make_us_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=False,
        is_reform=True,
        dynamic=_lsr_dynamic(),
    )
    ensure_calls = []

    class StopAfterEnsure(Exception):
        pass

    def fake_ensure(self):
        assert self.extra_variables["person"] == US_EXPECTED_LSR_EXTRA_VARIABLES
        ensure_calls.append(self.id)
        if len(ensure_calls) == 2:
            raise StopAfterEnsure

    monkeypatch.setattr(Simulation, "ensure", fake_ensure)

    with pytest.raises(StopAfterEnsure):
        us_economic_impact_analysis(baseline, reform)

    assert ensure_calls == ["baseline", "reform"]


def test_inactive_labor_supply_response_tolerates_missing_optional_columns(
    tmp_path,
):
    baseline = _make_us_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=False,
    )
    reform = _make_us_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=False,
        is_reform=True,
    )
    for simulation in (baseline, reform):
        simulation.output_dataset.data.person = (
            simulation.output_dataset.data.person.drop(
                columns=[
                    "self_employment_income",
                    "weekly_hours_worked",
                ]
            )
        )

    result = calculate_labor_supply_response(
        baseline,
        reform,
        country_code="us",
    )

    assert result.income_lsr == pytest.approx(0.0)
    assert result.substitution_lsr == pytest.approx(0.0)
    assert result.relative_lsr == {
        "income": pytest.approx(0.0),
        "substitution": pytest.approx(0.0),
    }
    assert result.hours.baseline == pytest.approx(0.0)
    assert result.hours.reform == pytest.approx(0.0)


def test_calculate_us_labor_supply_response_uses_legacy_shape(tmp_path):
    baseline = _make_us_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=True,
    )
    reform = _make_us_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=True,
        is_reform=True,
        dynamic=_lsr_dynamic(),
    )

    result = calculate_labor_supply_response(
        baseline,
        reform,
        country_code="us",
    )

    assert result.model_dump().keys() == {
        "substitution_lsr",
        "income_lsr",
        "relative_lsr",
        "total_change",
        "revenue_change",
        "decile",
        "hours",
    }
    assert result.income_lsr == pytest.approx(40.0)
    assert result.substitution_lsr == pytest.approx(25.0)
    assert result.total_change == pytest.approx(65.0)
    assert result.revenue_change == pytest.approx(0.0)
    assert result.relative_lsr == {
        "income": pytest.approx(40.0 / 285.0),
        "substitution": pytest.approx(25.0 / 285.0),
    }
    assert result.decile["average"]["income"] == {
        1: pytest.approx(20.0),
        2: pytest.approx(20.0),
    }
    assert result.decile["average"]["substitution"] == {
        1: pytest.approx(15.0),
        2: pytest.approx(10.0),
    }
    assert result.decile["relative"]["income"] == {
        1: pytest.approx(20.0 / 165.0),
        2: pytest.approx(20.0 / 120.0),
    }
    assert result.decile["relative"]["substitution"] == {
        1: pytest.approx(15.0 / 165.0),
        2: pytest.approx(10.0 / 120.0),
    }
    assert result.hours.baseline == pytest.approx(90.0)
    assert result.hours.reform == pytest.approx(99.0)
    assert result.hours.change == pytest.approx(9.0)
    assert result.hours.income_effect == pytest.approx(4.0)
    assert result.hours.substitution_effect == pytest.approx(3.0)


def test_calculate_us_labor_supply_response_uses_positional_household_data(
    tmp_path,
):
    baseline = _make_us_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=True,
    )
    reform = _make_us_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=True,
        is_reform=True,
        dynamic=_lsr_dynamic(),
    )
    _set_us_fixture_weights_and_household_index(baseline)
    _set_us_fixture_weights_and_household_index(reform)

    result = calculate_labor_supply_response(
        baseline,
        reform,
        country_code="us",
    )

    assert result.income_lsr == pytest.approx(100.0)
    assert result.substitution_lsr == pytest.approx(60.0)
    assert result.total_change == pytest.approx(160.0)
    assert result.relative_lsr == {
        "income": pytest.approx(100.0 / 690.0),
        "substitution": pytest.approx(60.0 / 690.0),
    }
    assert result.decile["average"]["income"] == {
        1: pytest.approx(20.0),
        2: pytest.approx(20.0),
    }
    assert result.decile["average"]["substitution"] == {
        1: pytest.approx(15.0),
        2: pytest.approx(10.0),
    }
    assert result.decile["relative"]["income"] == {
        1: pytest.approx(20.0 / 165.0),
        2: pytest.approx(20.0 / 120.0),
    }
    assert result.decile["relative"]["substitution"] == {
        1: pytest.approx(15.0 / 165.0),
        2: pytest.approx(10.0 / 120.0),
    }
    assert result.hours.baseline == pytest.approx(210.0)
    assert result.hours.reform == pytest.approx(233.0)
    assert result.hours.change == pytest.approx(23.0)


def test_inactive_us_labor_supply_response_does_not_require_lsr_columns(tmp_path):
    baseline = _make_us_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=False,
    )
    reform = _make_us_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=False,
        is_reform=True,
    )
    _set_us_fixture_weights_and_household_index(baseline)
    _set_us_fixture_weights_and_household_index(reform)

    result = calculate_labor_supply_response(
        baseline,
        reform,
        country_code="us",
    )

    assert result.income_lsr == pytest.approx(0.0)
    assert result.substitution_lsr == pytest.approx(0.0)
    assert result.total_change == pytest.approx(0.0)
    assert result.relative_lsr == {
        "income": pytest.approx(0.0),
        "substitution": pytest.approx(0.0),
    }
    assert result.decile == {
        "average": {
            "income": {1: pytest.approx(0.0), 2: pytest.approx(0.0)},
            "substitution": {1: pytest.approx(0.0), 2: pytest.approx(0.0)},
        },
        "relative": {
            "income": {1: pytest.approx(0.0), 2: pytest.approx(0.0)},
            "substitution": {1: pytest.approx(0.0), 2: pytest.approx(0.0)},
        },
    }
    assert result.hours.baseline == pytest.approx(210.0)
    assert result.hours.reform == pytest.approx(233.0)
    assert result.hours.income_effect == pytest.approx(0.0)
    assert result.hours.substitution_effect == pytest.approx(0.0)


def test_labor_supply_response_relative_values_guard_zero_earnings(tmp_path):
    baseline = _make_us_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=True,
    )
    reform = _make_us_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=True,
        is_reform=True,
        dynamic=_lsr_dynamic(),
    )
    baseline.output_dataset.data.person["employment_income"] = [20.0, 15.0, 30.0]
    baseline.output_dataset.data.person["self_employment_income"] = [0.0, 0.0, 0.0]

    result = calculate_labor_supply_response(
        baseline,
        reform,
        country_code="us",
    )

    assert result.relative_lsr == {
        "income": pytest.approx(0.0),
        "substitution": pytest.approx(0.0),
    }
    assert result.decile["relative"]["income"] == {
        1: pytest.approx(0.0),
        2: pytest.approx(0.0),
    }
    assert result.decile["relative"]["substitution"] == {
        1: pytest.approx(0.0),
        2: pytest.approx(0.0),
    }


def test_active_labor_supply_response_requires_lsr_columns(tmp_path):
    baseline = _make_us_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=False,
    )
    reform = _make_us_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=False,
        is_reform=True,
        dynamic=_lsr_dynamic(),
    )

    with pytest.raises(ValueError, match="income_elasticity_lsr"):
        calculate_labor_supply_response(
            baseline,
            reform,
            country_code="us",
        )


def test_calculate_uk_labor_supply_response_returns_zero_hours(tmp_path):
    baseline = _make_uk_lsr_simulation(
        tmp_path,
        "baseline",
        include_lsr=True,
    )
    reform = _make_uk_lsr_simulation(
        tmp_path,
        "reform",
        include_lsr=True,
        is_reform=True,
        dynamic=_lsr_dynamic(),
    )

    result = calculate_labor_supply_response(
        baseline,
        reform,
        country_code="uk",
    )

    assert result.income_lsr == pytest.approx(15.0)
    assert result.substitution_lsr == pytest.approx(6.0)
    assert result.total_change == pytest.approx(21.0)
    assert result.relative_lsr == {
        "income": pytest.approx(15.0 / 329.0),
        "substitution": pytest.approx(6.0 / 329.0),
    }
    assert result.decile["average"]["income"] == {
        1: pytest.approx(5.0),
        2: pytest.approx(10.0),
    }
    assert result.decile["average"]["substitution"] == {
        1: pytest.approx(2.0),
        2: pytest.approx(4.0),
    }
    assert result.hours.baseline == pytest.approx(0.0)
    assert result.hours.reform == pytest.approx(0.0)
    assert result.hours.change == pytest.approx(0.0)
    assert result.hours.income_effect == pytest.approx(0.0)
    assert result.hours.substitution_effect == pytest.approx(0.0)
