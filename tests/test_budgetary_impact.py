"""Tests for federal/state/unattributed budgetary impact partitioning.

The unit tests patch ``_sum_change`` and feed mocked reform-minus-baseline
deltas, so they exercise the partition arithmetic in isolation. The
integration test at the bottom runs ``calculate_budgetary_impact`` against a
tiny hand-built US output simulation so that every variable name it references
is resolved against the installed policyengine-us model — a future rename
(as happened with ``payroll_tax`` -> ``employee_payroll_tax``) fails loudly
here instead of silently returning a wrong number.
"""

from unittest.mock import patch

import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import Simulation
from policyengine.tax_benefit_models.us.analysis import (
    BudgetaryImpact,
    calculate_budgetary_impact,
    configure_budgetary_impact_variables,
)
from policyengine.tax_benefit_models.us.datasets import (
    PolicyEngineUSDataset,
    USYearData,
)
from policyengine.tax_benefit_models.us.model import us_latest

# Variables that calculate_budgetary_impact reads. Kept here so the
# integration test can assert each one still resolves against the installed
# policyengine-us model.
BUDGETARY_IMPACT_VARIABLES = (
    "household_tax",
    "household_benefits",
    "income_tax",
    "employee_payroll_tax",
    "state_income_tax",
    "federal_benefit_cost",
    "state_benefit_cost",
)


def _fake_sum_change_factory(variable_to_delta: dict[str, float]):
    """Return a fake _sum_change that looks up deltas by variable name."""

    def fake_sum_change(baseline_sim, reform_sim, variable):
        return variable_to_delta.get(variable, 0.0)

    return fake_sum_change


def _budgetary_impact_from_deltas(
    deltas: dict[str, float], *, include_health_benefits: bool = False
) -> BudgetaryImpact:
    with (
        patch(
            "policyengine.tax_benefit_models.us.analysis._sum_change",
            side_effect=_fake_sum_change_factory(deltas),
        ),
        patch(
            "policyengine.tax_benefit_models.us.analysis."
            "_include_health_benefits_in_net_income",
            return_value=include_health_benefits,
        ),
    ):
        return calculate_budgetary_impact(None, None)


def test_federal_income_tax_cut_is_fully_attributed():
    """A pure federal income tax cut lands entirely in ``federal``.

    ``household_tax`` moves with ``income_tax``, so nothing is left over:
    the residual is zero.
    """
    result = _budgetary_impact_from_deltas(
        {
            "income_tax": -100e9,
            "household_tax": -100e9,
        }
    )

    assert isinstance(result, BudgetaryImpact)
    assert result.federal == -100e9
    assert result.state == 0
    assert result.unattributed == 0
    assert result.total == -100e9


def test_shared_benefit_rollback_splits_federal_and_state():
    """Repealing ACA expansion cuts federal benefit spending 9x the state cut
    (90% vs 10% FMAP). Reduced spending is a positive fiscal impact, and
    because Medicaid is fully captured by the shared-funding aggregates the
    residual is zero."""
    result = _budgetary_impact_from_deltas(
        {
            # Federal share of Medicaid cost drops $90B, state share $10B.
            "federal_benefit_cost": -90e9,
            "state_benefit_cost": -10e9,
            # household_benefits stays 0: Medicaid/CHIP/MSP are excluded from
            # household_benefits by default, so a health reform does not move
            # it. The cost drop is captured only by the cost aggregates, which
            # calculate_budgetary_impact adds into total.
        }
    )

    # Federal "impact" = -(-90B) = +90B (government saves money).
    assert result.federal == 90e9
    assert result.state == 10e9
    assert result.unattributed == 0
    # total = 0 - 0 - (-90B) - (-10B) = +100B, fully split into fed/state.
    assert result.total == 100e9


def test_health_inclusive_config_avoids_double_count():
    """With gov.simulation.include_health_benefits_in_net_income true,
    household_benefits already carries Medicaid/CHIP/MSP, so the cost
    aggregates must not be subtracted from total a second time."""
    result = _budgetary_impact_from_deltas(
        {
            "federal_benefit_cost": -90e9,
            "state_benefit_cost": -10e9,
            # household_benefits carries the full $100B cut because the
            # parameter folds the health programs into it.
            "household_benefits": -100e9,
        },
        include_health_benefits=True,
    )

    assert result.federal == 90e9
    assert result.state == 10e9
    assert result.unattributed == 0
    # total = 0 - (-100B), with no extra cost subtraction.
    assert result.total == 100e9


def test_unattributed_program_surfaces_in_residual_not_zero():
    """An SSI reform must not silently read as total ~= 0.

    SSI is 100% federal but is not in ``federal_benefit_cost``, so ``federal``
    and ``state`` stay zero. Because ``total`` is measured from
    ``household_benefits`` (which does include SSI), the impact appears in
    ``total`` and flows entirely into ``unattributed``.
    """
    result = _budgetary_impact_from_deltas(
        {
            # SSI benefits rise $30B; households receive more.
            "household_benefits": 30e9,
        }
    )

    assert result.federal == 0
    assert result.state == 0
    # Higher benefit spending = negative fiscal impact, carried by residual.
    assert result.unattributed == -30e9
    assert result.total == -30e9


def test_mixed_reform_partitions_with_nonzero_residual():
    """Federal + state tax cuts, a shared-benefit cut, and an unattributed
    (SSI) benefit increase partition into all three buckets."""
    result = _budgetary_impact_from_deltas(
        {
            "income_tax": -50e9,
            "employee_payroll_tax": -10e9,
            "state_income_tax": -20e9,
            "federal_benefit_cost": -5e9,
            "state_benefit_cost": -2e9,
            # household_tax falls by the three tax cuts: 50 + 10 + 20.
            "household_tax": -80e9,
            # household_benefits carries only the $8B SSI rise: the $7B
            # shared health-program cut is excluded from household_benefits
            # by default and enters total via the cost aggregates.
            "household_benefits": 8e9,
        }
    )

    # Federal = -50 + -10 - (-5) = -55.
    assert result.federal == -55e9
    # State = -20 - (-2) = -18.
    assert result.state == -18e9
    # Total = -80 - 8 - (-5 + -2) = -81.
    assert result.total == -81e9
    # Residual = -81 - (-55) - (-18) = -8, i.e. the $8B SSI spending rise.
    assert result.unattributed == -8e9


def test_zero_reform_gives_zero_impact():
    result = _budgetary_impact_from_deltas({})

    assert result.federal == 0
    assert result.state == 0
    assert result.unattributed == 0
    assert result.total == 0


def test_total_is_always_the_sum_of_parts():
    """The computed ``total`` field is federal + state + unattributed."""
    result = BudgetaryImpact(federal=12.0, state=3.0, unattributed=-5.0)
    assert result.total == 10.0
    # JSON round-trip keeps the invariant.
    restored = BudgetaryImpact.model_validate_json(result.model_dump_json())
    assert restored.total == result.total


# ---------------------------------------------------------------------------
# Integration test: real variable-name resolution against policyengine-us.
# ---------------------------------------------------------------------------


def _microdf(data: dict, weights: str) -> MicroDataFrame:
    return MicroDataFrame(pd.DataFrame(data), weights=weights)


def _make_us_output_simulation(
    tmp_path,
    simulation_id: str,
    *,
    income_tax: float = 0.0,
    employee_payroll_tax: float = 0.0,
    state_income_tax: float = 0.0,
    federal_benefit_cost: float = 0.0,
    state_benefit_cost: float = 0.0,
    household_tax: float = 0.0,
    household_benefits: float = 0.0,
) -> Simulation:
    """Build a two-record US output simulation with the budgetary-impact
    variables materialized at their real entities.

    Mirrors the pattern in tests/test_us_program_statistics.py: all non-zero
    values sit in the first record (weight 1.0), so each weighted total equals
    the value passed in.
    """
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
                "federal_benefit_cost": [federal_benefit_cost, 0.0],
                "state_benefit_cost": [state_benefit_cost, 0.0],
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
            },
            "spm_unit_weight",
        ),
        tax_unit=_microdf(
            {
                "tax_unit_id": [1, 2],
                "tax_unit_weight": [1.0, 2.0],
                "income_tax": [income_tax, 0.0],
                "employee_payroll_tax": [employee_payroll_tax, 0.0],
                "state_income_tax": [state_income_tax, 0.0],
            },
            "tax_unit_weight",
        ),
        household=_microdf(
            {
                "household_id": [1, 2],
                "household_weight": [1.0, 2.0],
                "household_tax": [household_tax, 0.0],
                "household_benefits": [household_benefits, 0.0],
            },
            "household_weight",
        ),
    )
    dataset = PolicyEngineUSDataset(
        id=simulation_id,
        name=f"{simulation_id} output",
        description="Mocked US output dataset for budgetary impact",
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


def test_budgetary_impact_variables_resolve_against_model():
    """Every variable calculate_budgetary_impact reads must exist in the
    installed policyengine-us model, so a rename fails loudly here."""
    for variable in BUDGETARY_IMPACT_VARIABLES:
        assert variable in us_latest.variables_by_name, (
            f"{variable} is not defined in the installed policyengine-us model"
        )


def test_configure_budgetary_impact_variables_materializes_aggregates(tmp_path):
    """federal_benefit_cost / state_benefit_cost are not in the default US
    output, so economic_impact_analysis materializes them via
    configure_budgetary_impact_variables before running. Without this wiring
    calculate_budgetary_impact would raise on real data, so guard it here.
    """
    baseline = _make_us_output_simulation(tmp_path, "baseline")
    reform = _make_us_output_simulation(tmp_path, "reform")

    configure_budgetary_impact_variables(baseline, reform)

    for simulation in (baseline, reform):
        person_extras = simulation.extra_variables["person"]
        assert "federal_benefit_cost" in person_extras
        assert "state_benefit_cost" in person_extras


def test_calculate_budgetary_impact_runs_against_real_output_simulation(tmp_path):
    """End-to-end: resolve every referenced variable against a real US model
    version and confirm the partition arithmetic on tiny output data.

    If policyengine-us renames any of the referenced variables,
    ``ChangeAggregate`` raises inside ``calculate_budgetary_impact`` and this
    test fails, rather than the reform analysis silently breaking.
    """
    baseline = _make_us_output_simulation(
        tmp_path,
        "baseline",
        income_tax=1000.0,
        employee_payroll_tax=500.0,
        state_income_tax=300.0,
        federal_benefit_cost=200.0,
        state_benefit_cost=50.0,
        household_tax=1800.0,
        household_benefits=250.0,
    )
    reform = _make_us_output_simulation(
        tmp_path,
        "reform",
        income_tax=900.0,
        employee_payroll_tax=480.0,
        state_income_tax=280.0,
        federal_benefit_cost=180.0,
        state_benefit_cost=45.0,
        household_tax=1660.0,
        household_benefits=235.0,
    )

    result = calculate_budgetary_impact(baseline, reform)

    assert isinstance(result, BudgetaryImpact)
    # federal = Δincome_tax + Δemployee_payroll_tax - Δfederal_benefit_cost
    #         = -100 + -20 - (-20) = -100
    assert result.federal == -100.0
    # state = Δstate_income_tax - Δstate_benefit_cost = -20 - (-5) = -15
    assert result.state == -15.0
    # total = Δhousehold_tax - Δhousehold_benefits - Δhealth cost
    #       = -140 - (-15) - (-20 + -5) = -100
    assert result.total == -100.0
    # unattributed = total - federal - state = -100 - (-100) - (-15) = 15
    assert result.unattributed == 15.0
