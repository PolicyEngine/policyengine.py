import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel, Field


class SingleEconomyInequality(BaseModel):
    gini: float = Field(
        ..., description="Gini coefficient of income inequality"
    )
    top_10_percent_share: float = Field(
        ..., description="Income share of the top 10 percent"
    )
    top_1_percent_share: float = Field(
        ..., description="Income share of the top 1 percent"
    )


def calculate_inequality(simulation: "Simulation") -> SingleEconomyInequality:
    """
    Calculate inequality metrics for a given simulation.
    Args:
        simulation (Simulation): The simulation object containing the data
                                 and methods to perform the calculations.
    Returns:
        SingleEconomyInequality: An object containing the calculated Gini
                                 coefficient, top 10 percent income share,
                                 and top 1 percent income share.
    """

    personal_hh_equiv_income = simulation.selected_sim.calculate(
        "equiv_household_net_income"
    )
    personal_hh_equiv_income[personal_hh_equiv_income < 0] = 0
    household_count_people = simulation.selected_sim.calculate(
        "household_count_people"
    ).values
    personal_hh_equiv_income.weights *= household_count_people
    gini = personal_hh_equiv_income.gini()
    in_top_10_pct = personal_hh_equiv_income.decile_rank() == 10
    in_top_1_pct = personal_hh_equiv_income.percentile_rank() == 100

    personal_hh_equiv_income.weights /= household_count_people

    top_10_share = (
        personal_hh_equiv_income[in_top_10_pct].sum()
        / personal_hh_equiv_income.sum()
    )
    top_1_share = (
        personal_hh_equiv_income[in_top_1_pct].sum()
        / personal_hh_equiv_income.sum()
    )

    return SingleEconomyInequality(
        gini=gini,
        top_10_percent_share=top_10_share,
        top_1_percent_share=top_1_share,
    )
