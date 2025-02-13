import typing

from policyengine import Simulation, SimulationOptions

from policyengine_core.simulations import Microsimulation

from pydantic import BaseModel


class InequalitySummary(BaseModel):
    gini: float
    """The Gini coefficient of the household net income distribution."""
    top_10_share: float
    """The share of total income held by the top 10% of households."""
    top_1_share: float
    """The share of total income held by the top 1% of households."""


def _calculate_inequality(
    simulation: Microsimulation,
):
    """Calculate inequality statistics for a set of households."""
    income = simulation.calculate("equiv_household_net_income")
    income[income < 0] = 0
    household_count_people = simulation.calculate("household_count_people")
    income.weights *= household_count_people
    personal_hh_equiv_income = income
    try:
        gini = personal_hh_equiv_income.gini()
    except:
        print("WARNING: Gini calculation failed. Setting to 0.4.")
        gini = 0.4
    in_top_10_pct = personal_hh_equiv_income.decile_rank() == 10
    in_top_1_pct = personal_hh_equiv_income.percentile_rank() == 100

    personal_hh_equiv_income.weights /= (
        household_count_people  # Don't double-count people
    )

    top_10_share = (
        personal_hh_equiv_income[in_top_10_pct].sum()
        / personal_hh_equiv_income.sum()
    )
    top_1_share = (
        personal_hh_equiv_income[in_top_1_pct].sum()
        / personal_hh_equiv_income.sum()
    )

    return InequalitySummary(
        gini=gini,
        top_10_share=top_10_share,
        top_1_share=top_1_share,
    )
