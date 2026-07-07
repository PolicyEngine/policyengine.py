from unittest.mock import MagicMock

import pandas as pd
import pytest

from policyengine.core import OutputCollection
from policyengine.outputs import (
    CliffImpact,
    CliffImpactInSimulation,
    LaborSupplyResponse,
    ProgramStatistics,
)
from policyengine.outputs import program_statistics as program_statistics_module
from policyengine.outputs.inequality import Inequality
from policyengine.tax_benefit_models.uk import analysis as uk_analysis
from policyengine.tax_benefit_models.us import analysis as us_analysis


def _empty_collection() -> OutputCollection:
    return OutputCollection(outputs=[], dataframe=pd.DataFrame())


def _empty_labor_supply_response() -> LaborSupplyResponse:
    return LaborSupplyResponse.model_construct()


def _empty_inequality(simulation) -> Inequality:
    return Inequality.model_construct(
        simulation=simulation,
        income_variable="household_net_income",
        gini=0.0,
        top_10_share=0.0,
        top_1_share=0.0,
        bottom_50_share=0.0,
    )


def _make_simulation(simulation_id: str, events: list[str]) -> MagicMock:
    simulation = MagicMock()
    simulation.id = simulation_id
    simulation.dataset.data.household = pd.DataFrame({"household_id": range(101)})
    simulation.tax_benefit_model_version.get_variable.return_value.entity = "household"
    simulation.ensure.side_effect = lambda: events.append(f"{simulation_id}.ensure")
    return simulation


def _patch_analysis_dependencies(
    monkeypatch,
    analysis_module,
    *,
    country_code: str,
    events: list[str],
    fail_on_cliff: bool,
    cliff_result: CliffImpact | None = None,
) -> None:
    class DummyProgramStatistics(ProgramStatistics):
        def run(self):
            self.baseline_total = 0.0
            self.reform_total = 0.0
            self.change = 0.0
            self.baseline_count = 0.0
            self.reform_count = 0.0
            self.winners = 0.0
            self.losers = 0.0

    def fake_program_statistics(**kwargs):
        return DummyProgramStatistics.model_construct(**kwargs)

    monkeypatch.setattr(
        analysis_module,
        "_validate_program_statistics_config",
        lambda baseline_simulation, reform_simulation: None,
    )
    monkeypatch.setattr(
        program_statistics_module, "ProgramStatistics", fake_program_statistics
    )
    monkeypatch.setattr(
        analysis_module,
        "configure_labor_supply_response_variables",
        lambda baseline_simulation, reform_simulation, country_code: None,
    )
    monkeypatch.setattr(
        analysis_module,
        "calculate_labor_supply_response",
        lambda baseline_simulation, reform_simulation, country_code: (
            _empty_labor_supply_response()
        ),
    )
    monkeypatch.setattr(
        analysis_module,
        "calculate_decile_impacts",
        lambda **kwargs: _empty_collection(),
    )

    if country_code == "uk":
        monkeypatch.setattr(
            analysis_module,
            "compute_intra_decile_impacts",
            lambda **kwargs: _empty_collection(),
        )
        monkeypatch.setattr(
            analysis_module,
            "calculate_uk_poverty_rates",
            lambda simulation: _empty_collection(),
        )
        monkeypatch.setattr(
            analysis_module,
            "calculate_uk_inequality",
            _empty_inequality,
        )
    else:
        monkeypatch.setattr(
            analysis_module,
            "calculate_us_poverty_rates",
            lambda simulation: _empty_collection(),
        )
        monkeypatch.setattr(
            analysis_module,
            "calculate_us_inequality",
            lambda simulation, preset: _empty_inequality(simulation),
        )

    if fail_on_cliff:

        def unexpected_cliff_call(*args, **kwargs):
            raise AssertionError("cliff helpers should not run by default")

        monkeypatch.setattr(
            analysis_module,
            "configure_cliff_impact_variables",
            unexpected_cliff_call,
        )
        monkeypatch.setattr(
            analysis_module,
            "calculate_cliff_impact",
            unexpected_cliff_call,
        )
        return

    def fake_configure_cliff_impact_variables(
        baseline_simulation,
        reform_simulation,
    ):
        events.append("configure_cliff")

    def fake_calculate_cliff_impact(
        baseline_simulation,
        reform_simulation,
    ):
        events.append("calculate_cliff")
        return cliff_result

    monkeypatch.setattr(
        analysis_module,
        "configure_cliff_impact_variables",
        fake_configure_cliff_impact_variables,
    )
    monkeypatch.setattr(
        analysis_module,
        "calculate_cliff_impact",
        fake_calculate_cliff_impact,
    )


@pytest.mark.parametrize(
    ("analysis_module", "country_code"),
    [(us_analysis, "us"), (uk_analysis, "uk")],
)
def test_economic_impact_analysis_defaults_cliff_impact_to_none(
    monkeypatch,
    analysis_module,
    country_code,
):
    events: list[str] = []
    baseline = _make_simulation("baseline", events)
    reform = _make_simulation("reform", events)
    _patch_analysis_dependencies(
        monkeypatch,
        analysis_module,
        country_code=country_code,
        events=events,
        fail_on_cliff=True,
    )

    result = analysis_module.economic_impact_analysis(baseline, reform)

    assert result.cliff_impact is None
    assert events == ["baseline.ensure", "reform.ensure"]


@pytest.mark.parametrize(
    ("analysis_module", "country_code"),
    [(us_analysis, "us"), (uk_analysis, "uk")],
)
def test_economic_impact_analysis_can_include_cliff_impacts(
    monkeypatch,
    analysis_module,
    country_code,
):
    events: list[str] = []
    baseline = _make_simulation("baseline", events)
    reform = _make_simulation("reform", events)
    cliff_result = CliffImpact(
        baseline=CliffImpactInSimulation(cliff_gap=1.0, cliff_share=0.1),
        reform=CliffImpactInSimulation(cliff_gap=2.0, cliff_share=0.2),
    )
    _patch_analysis_dependencies(
        monkeypatch,
        analysis_module,
        country_code=country_code,
        events=events,
        fail_on_cliff=False,
        cliff_result=cliff_result,
    )

    result = analysis_module.economic_impact_analysis(
        baseline,
        reform,
        include_cliff_impacts=True,
    )

    assert result.cliff_impact == cliff_result
    assert events == [
        "configure_cliff",
        "baseline.ensure",
        "reform.ensure",
        "calculate_cliff",
    ]
