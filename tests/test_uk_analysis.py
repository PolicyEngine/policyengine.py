from unittest.mock import MagicMock

import pandas as pd

from policyengine.core import OutputCollection
from policyengine.outputs import ProgramStatistics
from policyengine.outputs.inequality import Inequality
from policyengine.tax_benefit_models.uk import analysis as uk_analysis


def _empty_collection() -> OutputCollection:
    return OutputCollection(outputs=[], dataframe=pd.DataFrame())


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
    monkeypatch.setattr(uk_analysis, "ProgramStatistics", fake_program_statistics)
    monkeypatch.setattr(uk_analysis, "calculate_uk_poverty_rates", fake_poverty_rates)
    monkeypatch.setattr(uk_analysis, "calculate_uk_inequality", fake_inequality)

    result = uk_analysis.economic_impact_analysis(
        baseline_simulation=baseline,
        reform_simulation=reform,
    )

    assert result.decile_impacts.dataframe["source"].tolist() == ["standard"]
    assert result.wealth_decile_impacts.dataframe["source"].tolist() == ["wealth"]

    assert decile_calls[0] == {
        "baseline_simulation": baseline,
        "reform_simulation": reform,
    }
    assert decile_calls[1] == {
        "baseline_simulation": baseline,
        "reform_simulation": reform,
        "income_variable": "household_net_income",
        "decile_variable": "household_wealth_decile",
        "entity": "household",
    }
    assert intra_calls == [
        {
            "baseline_simulation": baseline,
            "reform_simulation": reform,
            "income_variable": "household_net_income",
            "decile_variable": "household_wealth_decile",
            "entity": "household",
        }
    ]
    assert result.intra_wealth_decile_impacts.dataframe["decile"].tolist() == (
        list(range(1, 11)) + [0]
    )
