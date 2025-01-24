import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel, Field

class SingleEconomyFinanceOutput(BaseModel):
    total_net_income: float = Field(..., description="Total net income of the household")
    total_market_income: float = Field(..., description="Total market income of the household")
    total_tax: float = Field(..., description="Total tax paid by the household")
    total_benefits: float = Field(..., description="Total benefits received by the household")
    employment_income_hh: typing.List[float] = Field(..., description="Employment income of the household")
    self_employment_income_hh: typing.List[float] = Field(..., description="Self-employment income of the household")
    household_net_income: typing.List[float] = Field(..., description="Net income of the household")
    equiv_household_net_income: typing.List[float] = Field(..., description="Equivalized net income of the household")
    household_income_decile: typing.List[int] = Field(..., description="Income decile of the household")
    household_market_income: typing.List[float] = Field(..., description="Market income of the household")
    wealth: typing.Optional[typing.List[float]] = Field(None, description="Wealth of the household")
    wealth_decile: typing.Optional[typing.List[int]] = Field(None, description="Wealth decile of the household")
    in_poverty: typing.List[bool] = Field(..., description="Poverty status of the household")
    person_in_poverty: typing.List[bool] = Field(..., description="Poverty status of individuals in the household")
    person_in_deep_poverty: typing.List[bool] = Field(..., description="Deep poverty status of individuals in the household")
    poverty_gap: float = Field(..., description="Poverty gap of the household")
    deep_poverty_gap: float = Field(..., description="Deep poverty gap of the household")
    poverty_rate: float = Field(..., description="Poverty rate of the household")
    deep_poverty_rate: float = Field(..., description="Deep poverty rate of the household")


def calculate_finance(
    simulation: "Simulation",
) -> SingleEconomyFinanceOutput:
    """
    Calculate various financial metrics for a given simulation.

    Args:
        simulation (Simulation): The simulation object containing the data.

    Returns:
        FinanceOutput: An object containing various financial metrics.

    """
    sim = simulation.selected_sim

    total_net_income = sim.calculate("household_net_income").sum()
    total_market_income = sim.calculate("household_market_income").sum()
    total_tax = sim.calculate("household_tax").sum()
    total_benefits = sim.calculate("household_benefits").sum()
    employment_income_hh = (
        sim.calculate("employment_income", map_to="household")
        .astype(float).tolist()
    )
    self_employment_income_hh = (
        sim.calculate("self_employment_income", map_to="household")
        .astype(float).tolist()
    )
    household_net_income = (
        sim.calculate("household_net_income").astype(float).tolist()
    )
    equiv_household_net_income = (
        sim.calculate("equiv_household_net_income").astype(float).tolist()
    )
    household_income_decile = (
        sim.calculate("household_income_decile").astype(int).tolist()
    )
    household_market_income = (
        sim.calculate("household_market_income").astype(float).tolist()
    )
    if "total_wealth" in sim.tax_benefit_system.variables:
        wealth = sim.calculate("total_wealth")
        household_count_people = sim.calculate("household_count_people").values
        wealth.weights *= household_count_people
        wealth_decile = wealth.decile_rank().clip(1, 10).astype(int)
        wealth = wealth.astype(float).tolist()
    else:
        wealth = None
        wealth_decile = None

    in_poverty = sim.calculate("in_poverty").astype(bool).tolist()
    person_in_poverty = (
        sim.calculate("in_poverty", map_to="person").astype(bool).tolist()
    )
    person_in_deep_poverty = (
        sim.calculate("in_deep_poverty", map_to="person").astype(bool).tolist()
    )
    poverty_gap = sim.calculate("poverty_gap").sum()
    deep_poverty_gap = sim.calculate("deep_poverty_gap").sum()

    poverty_rate = sim.calculate("in_poverty", map_to="person").mean()
    deep_poverty_rate = sim.calculate(
        "in_deep_poverty", map_to="person"
    ).mean()

    return SingleEconomyFinanceOutput(
        total_net_income=total_net_income,
        total_market_income=total_market_income,
        total_tax=total_tax,
        total_benefits=total_benefits,
        employment_income_hh=employment_income_hh,
        self_employment_income_hh=self_employment_income_hh,
        household_net_income=household_net_income,
        equiv_household_net_income=equiv_household_net_income,
        household_income_decile=household_income_decile,
        household_market_income=household_market_income,
        wealth=wealth,
        wealth_decile=wealth_decile,
        in_poverty=in_poverty,
        person_in_poverty=person_in_poverty,
        person_in_deep_poverty=person_in_deep_poverty,
        poverty_gap=poverty_gap,
        deep_poverty_gap=deep_poverty_gap,
        poverty_rate=poverty_rate,
        deep_poverty_rate=deep_poverty_rate,
    )
