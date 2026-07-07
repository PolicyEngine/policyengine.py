from unittest.mock import MagicMock

import pandas as pd

from policyengine.core import OutputCollection
from policyengine.outputs import LaborSupplyResponse, ProgramStatistics
from policyengine.outputs import program_statistics as program_statistics_module
from policyengine.outputs.inequality import Inequality
from policyengine.tax_benefit_models.uk import analysis as uk_analysis


def _empty_collection() -> OutputCollection:
    return OutputCollection(outputs=[], dataframe=pd.DataFrame())


def _empty_labor_supply_response() -> LaborSupplyResponse:
    return LaborSupplyResponse.model_construct()


def _make_simulation() -> MagicMock:
    simulation = MagicMock()
    simulation.dataset.data.household = pd.DataFrame({"household_id": range(101)})
    simulation.tax_benefit_model_version.get_variable.return_value.entity = "household"
    return simulation


def test_uk_economic_impact_analysis_includes_wealth_decile_outputs(monkeypatch):
    baseline = _make_simulation()
    reform = _make_simulation()

    decile_calls = []
    standard_deciles = OutputCollection(
        outputs=[],
        dataframe=pd.DataFrame({"source": ["standard"]}),
    )
    wealth_deciles = OutputCollection(
        outputs=[],
        dataframe=pd.DataFrame({"source": ["wealth"]}),
    )
    intra_wealth_deciles = OutputCollection(
        outputs=[],
        dataframe=pd.DataFrame({"decile": list(range(1, 11)) + [0]}),
    )

    def fake_calculate_decile_impacts(**kwargs):
        decile_calls.append(kwargs)
        if kwargs.get("decile_variable") == "household_wealth_decile":
            return wealth_deciles
        return standard_deciles

    intra_calls = []

    def fake_compute_intra_decile_impacts(**kwargs):
        intra_calls.append(kwargs)
        return intra_wealth_deciles

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

    def fake_poverty_rates(_simulation):
        return _empty_collection()

    def fake_inequality(simulation):
        return Inequality.model_construct(
            simulation=simulation,
            income_variable="equiv_hbai_household_net_income",
            gini=0.0,
            top_10_share=0.0,
            top_1_share=0.0,
            bottom_50_share=0.0,
        )

    monkeypatch.setattr(
        uk_analysis, "calculate_decile_impacts", fake_calculate_decile_impacts
    )
    monkeypatch.setattr(
        uk_analysis, "compute_intra_decile_impacts", fake_compute_intra_decile_impacts
    )
    monkeypatch.setattr(
        uk_analysis,
        "_validate_program_statistics_config",
        lambda baseline_simulation, reform_simulation: None,
    )
    monkeypatch.setattr(
        program_statistics_module, "ProgramStatistics", fake_program_statistics
    )
    monkeypatch.setattr(uk_analysis, "calculate_uk_poverty_rates", fake_poverty_rates)
    monkeypatch.setattr(uk_analysis, "calculate_uk_inequality", fake_inequality)
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

    result = uk_analysis.economic_impact_analysis(
        baseline_simulation=baseline,
        reform_simulation=reform,
    )

    assert result.decile_impacts.dataframe["source"].tolist() == ["standard"]
    assert result.wealth_decile_impacts.dataframe["source"].tolist() == ["wealth"]

    assert len(decile_calls) == 2
    standard_call = decile_calls[0]
    assert standard_call["baseline_simulation"] is baseline
    assert standard_call["reform_simulation"] is reform

    wealth_call = decile_calls[1]
    assert wealth_call["baseline_simulation"] is baseline
    assert wealth_call["reform_simulation"] is reform
    assert wealth_call["income_variable"] == "household_net_income"
    assert wealth_call["decile_variable"] == "household_wealth_decile"
    assert wealth_call["entity"] == "household"

    assert len(intra_calls) == 1
    intra_call = intra_calls[0]
    assert intra_call["baseline_simulation"] is baseline
    assert intra_call["reform_simulation"] is reform
    assert intra_call["income_variable"] == "household_net_income"
    assert intra_call["decile_variable"] == "household_wealth_decile"
    assert intra_call["entity"] == "household"
    assert result.intra_wealth_decile_impacts.dataframe["decile"].tolist() == (
        list(range(1, 11)) + [0]
    )
