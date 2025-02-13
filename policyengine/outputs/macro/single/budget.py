import typing

from policyengine import Simulation, SimulationOptions

from policyengine_core.simulations import Microsimulation

from pydantic import BaseModel


class TaxBenefitProgram(BaseModel):
    name: str
    """The name of the tax-benefit program."""
    is_positive: bool
    """Whether the program is positive on the *government* balance sheet."""


UK_PROGRAMS = [
    TaxBenefitProgram(name="income_tax", is_positive=True),
    TaxBenefitProgram(name="national_insurance", is_positive=True),
    TaxBenefitProgram(name="ni_employer", is_positive=True),
    TaxBenefitProgram(name="vat", is_positive=True),
    TaxBenefitProgram(name="council_tax", is_positive=True),
    TaxBenefitProgram(name="fuel_duty", is_positive=True),
    TaxBenefitProgram(name="tax_credits", is_positive=False),
    TaxBenefitProgram(name="universal_credit", is_positive=False),
    TaxBenefitProgram(name="child_benefit", is_positive=False),
    TaxBenefitProgram(name="state_pension", is_positive=False),
    TaxBenefitProgram(name="pension_credit", is_positive=False),
]


class FiscalSummary(BaseModel):
    tax_revenue: float
    """The total tax revenue collected by the government."""
    federal_tax: float
    """The total tax revenue collected by the federal (or national) government."""
    federal_balance: float
    """Federal taxes subtract spending."""
    state_tax: float
    """The total tax revenue collected by the state government."""
    government_spending: float
    """The total spending by the (federal) government on modeled programs."""
    tax_benefit_programs: dict[str, float]
    """The total revenue change to the government from each tax-benefit program."""
    household_net_income: float
    """The total net income of the households in the simulation."""


def _calculate_government_balance(
    simulation: Microsimulation,
    options: "SimulationOptions",
) -> FiscalSummary:
    """Calculate government balance metrics for a set of households."""
    tb_programs = {}
    if options.country == "uk":
        total_tax = simulation.calculate("gov_tax").sum()
        total_spending = simulation.calculate("gov_spending").sum()
        for program in UK_PROGRAMS:
            tb_programs[program.name] = simulation.calculate(
                program.name
            ).sum() * (1 if program.is_positive else -1)
        total_state_tax = 0
    else:
        total_tax = simulation.calculate("household_tax").sum()
        total_spending = simulation.calculate("household_benefits").sum()
        total_state_tax = simulation.calculate(
            "household_state_income_tax"
        ).sum()

    national_tax = total_tax - total_state_tax

    total_net_income = simulation.calculate("household_net_income").sum()

    return FiscalSummary(
        tax_revenue=total_tax,
        federal_tax=national_tax,
        federal_balance=national_tax - total_spending,
        state_tax=total_state_tax,
        government_spending=total_spending,
        tax_benefit_programs=tb_programs,
        household_net_income=total_net_income,
    )
