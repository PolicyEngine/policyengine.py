"""Tests for the new economic impact output modules."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.outputs.analysis_strategy import AnalysisStrategy, ProgramDefinition
from policyengine.outputs.budget_summary import compute_budget_summary
from policyengine.outputs.change_aggregate import ChangeAggregate, ChangeAggregateType
from policyengine.outputs.decile_impact import DecileImpact, compute_decile_impacts

# ---------------------------------------------------------------------------
# Helpers (same pattern as test_intra_decile_impact.py)
# ---------------------------------------------------------------------------


def _make_variable_mock(name: str, entity: str) -> MagicMock:
    """Create a mock Variable with name and entity attributes."""
    var = MagicMock()
    var.name = name
    var.entity = entity
    return var


def _make_sim(household_data: dict, variables: list | None = None) -> MagicMock:
    """Create a mock Simulation with household-level data."""
    hh_df = MicroDataFrame(
        pd.DataFrame(household_data),
        weights="household_weight",
    )
    sim = MagicMock()
    sim.output_dataset.data.household = hh_df
    sim.id = "test-sim"
    if variables is not None:
        sim.tax_benefit_model_version.variables = variables
    return sim


# ---------------------------------------------------------------------------
# US AnalysisStrategy tests
# ---------------------------------------------------------------------------


def test_us_strategy_programs():
    """USAnalysisStrategy should contain expected program keys."""
    from policyengine.tax_benefit_models.us.analysis import USAnalysisStrategy

    strategy = USAnalysisStrategy()
    expected = {
        "income_tax",
        "employee_payroll_tax",
        "snap",
        "tanf",
        "ssi",
        "social_security",
    }
    assert set(strategy.programs.keys()) == expected


def test_us_strategy_conforms_to_protocol():
    """USAnalysisStrategy should satisfy the AnalysisStrategy protocol."""
    from policyengine.tax_benefit_models.us.analysis import USAnalysisStrategy

    assert isinstance(USAnalysisStrategy(), AnalysisStrategy)


def test_us_strategy_program_structure():
    """Each program entry should be a ProgramDefinition with 'entity' and 'is_tax'."""
    from policyengine.tax_benefit_models.us.analysis import USAnalysisStrategy

    for name, info in USAnalysisStrategy().programs.items():
        assert "entity" in info, f"US program {name} missing 'entity'"
        assert "is_tax" in info, f"US program {name} missing 'is_tax'"


# ---------------------------------------------------------------------------
# UK AnalysisStrategy tests (conditional on policyengine_uk being installed)
# ---------------------------------------------------------------------------

uk_installed = pytest.importorskip(
    "policyengine_uk", reason="policyengine_uk not installed"
)


def test_uk_strategy_programs():
    """UKAnalysisStrategy should contain expected programme keys."""
    from policyengine.tax_benefit_models.uk.analysis import UKAnalysisStrategy

    expected = {
        "income_tax",
        "national_insurance",
        "vat",
        "council_tax",
        "universal_credit",
        "child_benefit",
        "pension_credit",
        "income_support",
        "working_tax_credit",
        "child_tax_credit",
    }
    assert set(UKAnalysisStrategy().programs.keys()) == expected


def test_uk_strategy_conforms_to_protocol():
    """UKAnalysisStrategy should satisfy the AnalysisStrategy protocol."""
    from policyengine.tax_benefit_models.uk.analysis import UKAnalysisStrategy

    assert isinstance(UKAnalysisStrategy(), AnalysisStrategy)


def test_uk_strategy_program_structure():
    """Each programme entry should be a ProgramDefinition with 'entity' and 'is_tax'."""
    from policyengine.tax_benefit_models.uk.analysis import UKAnalysisStrategy

    for name, info in UKAnalysisStrategy().programs.items():
        assert "entity" in info, f"UK programme {name} missing 'entity'"
        assert "is_tax" in info, f"UK programme {name} missing 'is_tax'"


# ---------------------------------------------------------------------------
# Shared economic_impact_analysis tests
# ---------------------------------------------------------------------------


def test_economic_impact_analysis_rejects_bad_strategy():
    """economic_impact_analysis should raise TypeError for non-strategy objects."""
    from policyengine.outputs.economic_impact import economic_impact_analysis

    sim = MagicMock()
    with pytest.raises(TypeError, match="AnalysisStrategy protocol"):
        economic_impact_analysis(sim, sim, "not_a_strategy")


def test_economic_impact_analysis_calls_ensure():
    """economic_impact_analysis should call ensure() on both simulations."""
    from policyengine.outputs.economic_impact import economic_impact_analysis

    baseline = MagicMock()
    reform = MagicMock()

    strategy = MagicMock(spec=AnalysisStrategy)
    strategy.income_variable = "household_net_income"
    strategy.budget_variable_names = ["household_tax"]
    strategy.programs = {
        "income_tax": ProgramDefinition(entity="tax_unit", is_tax=True)
    }
    strategy.compute_poverty.return_value = MagicMock()
    strategy.compute_inequality.return_value = MagicMock()

    with (
        patch(
            "policyengine.outputs.economic_impact.compute_decile_impacts"
        ) as mock_decile,
        patch(
            "policyengine.outputs.economic_impact.compute_intra_decile_impacts"
        ) as mock_intra,
        patch(
            "policyengine.outputs.economic_impact.compute_budget_summary"
        ) as mock_budget,
        patch(
            "policyengine.outputs.economic_impact.compute_program_statistics"
        ) as mock_prog,
        patch("policyengine.outputs.economic_impact.PolicyReformAnalysis"),
    ):
        economic_impact_analysis(baseline, reform, strategy)

    baseline.ensure.assert_called_once()
    reform.ensure.assert_called_once()
    mock_decile.assert_called_once()
    mock_intra.assert_called_once()
    mock_budget.assert_called_once()
    mock_prog.assert_called_once()
    strategy.compute_poverty.assert_called_once_with(baseline, reform)
    strategy.compute_inequality.assert_called_once_with(baseline, reform)


# ---------------------------------------------------------------------------
# compute_budget_summary tests
# ---------------------------------------------------------------------------


def _make_budget_sim(variable_data: dict, variables: list) -> MagicMock:
    """Create a mock simulation for budget summary testing."""
    sim = MagicMock()
    sim.output_dataset.data.household = MicroDataFrame(
        pd.DataFrame(variable_data),
        weights="household_weight",
    )
    sim.id = "test-budget-sim"
    sim.tax_benefit_model_version.variables = variables

    def get_variable(name):
        for v in variables:
            if v.name == name:
                return v
        raise ValueError(f"Variable '{name}' not found in model")

    sim.tax_benefit_model_version.get_variable = get_variable
    return sim


def test_compute_budget_summary_looks_up_entity_from_tbm():
    """compute_budget_summary should resolve entity from TBM, not from caller."""
    variables = [
        _make_variable_mock("household_tax", "household"),
        _make_variable_mock("household_benefits", "household"),
    ]
    sim = _make_budget_sim(
        {
            "household_tax": [5000.0],
            "household_benefits": [2000.0],
            "household_weight": [1.0],
        },
        variables,
    )

    # Patch BudgetSummaryItem + OutputCollection to bypass Pydantic validation
    with (
        patch("policyengine.outputs.budget_summary.BudgetSummaryItem") as MockBSI,
        patch("policyengine.outputs.budget_summary.OutputCollection"),
    ):
        MockBSI.return_value = MagicMock()
        compute_budget_summary(sim, sim, ["household_tax", "household_benefits"])

    assert MockBSI.call_count == 2
    calls = MockBSI.call_args_list
    assert calls[0].kwargs["entity"] == "household"
    assert calls[1].kwargs["entity"] == "household"


def test_compute_budget_summary_variable_not_found():
    """compute_budget_summary should raise ValueError for unknown variable."""
    variables = [_make_variable_mock("household_tax", "household")]
    sim = _make_budget_sim(
        {"household_tax": [5000.0], "household_weight": [1.0]},
        variables,
    )

    with pytest.raises(ValueError, match="not found in model"):
        compute_budget_summary(sim, sim, ["nonexistent_variable"])


# ---------------------------------------------------------------------------
# DecileImpact tests
# ---------------------------------------------------------------------------


def test_decile_impact_variable_not_found():
    """DecileImpact.run() should raise ValueError for a nonexistent variable."""
    variables = [_make_variable_mock("household_net_income", "household")]
    sim = _make_sim(
        {"household_net_income": [50000.0], "household_weight": [1.0]},
        variables=variables,
    )

    di = DecileImpact.model_construct(
        baseline_simulation=sim,
        reform_simulation=sim,
        income_variable="nonexistent_variable",
        entity="household",
        decile=1,
    )
    with pytest.raises(ValueError, match="not found in model"):
        di.run()


def test_compute_decile_impacts_returns_10():
    """compute_decile_impacts should return 10 DecileImpact objects by default."""
    n = 100
    incomes = np.linspace(10000, 100000, n)
    reform_incomes = incomes + 500
    variables = [_make_variable_mock("household_net_income", "household")]

    baseline = _make_sim(
        {"household_net_income": incomes, "household_weight": np.ones(n)},
        variables=variables,
    )
    reform = _make_sim(
        {"household_net_income": reform_incomes, "household_weight": np.ones(n)},
        variables=variables,
    )

    result = compute_decile_impacts(
        baseline, reform, income_variable="household_net_income", entity="household"
    )

    assert len(result.outputs) == 10
    assert len(result.dataframe) == 10

    # Each decile should have absolute_change ~500
    for di in result.outputs:
        assert abs(di.absolute_change - 500.0) < 1e-6


def test_compute_decile_impacts_custom_quantiles():
    """compute_decile_impacts with quantiles=5 should return 5 outputs."""
    n = 100
    incomes = np.linspace(10000, 100000, n)
    variables = [_make_variable_mock("household_net_income", "household")]

    sim = _make_sim(
        {"household_net_income": incomes, "household_weight": np.ones(n)},
        variables=variables,
    )

    result = compute_decile_impacts(
        sim,
        sim,
        income_variable="household_net_income",
        entity="household",
        quantiles=5,
    )

    assert len(result.outputs) == 5


# ---------------------------------------------------------------------------
# ChangeAggregate error test
# ---------------------------------------------------------------------------


def test_change_aggregate_variable_not_found():
    """ChangeAggregate should raise ValueError for a nonexistent variable."""
    variables = [_make_variable_mock("employment_income", "person")]
    sim = _make_sim(
        {"household_net_income": [50000.0], "household_weight": [1.0]},
        variables=variables,
    )

    ca = ChangeAggregate.model_construct(
        baseline_simulation=sim,
        reform_simulation=sim,
        variable="nonexistent_variable",
        aggregate_type=ChangeAggregateType.COUNT,
    )
    with pytest.raises(ValueError, match="not found in model"):
        ca.run()
