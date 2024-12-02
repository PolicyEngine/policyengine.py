from policyengine import Simulation

DEFAULT_COUNT_YEARS = 1


def budget_window(simulation: Simulation, count_years: int = None) -> dict:
    sim = simulation.selected
    current_year = simulation.time_period
    if count_years is not None:
        years = list(range(current_year, current_year + count_years))
    else:
        years = [current_year]
    if simulation.country == "uk":
        total_tax = [sim.calculate("gov_tax", year).sum() for year in years]
        total_spending = [
            sim.calculate("gov_spending", year).sum() for year in years
        ]
        total_state_tax = [0 for year in years]
        total_budget = [
            total_tax[i] - total_spending[i] for i in range(len(years))
        ]
        total_federal_budget = total_budget
    elif simulation.country == "us":
        total_tax = [
            sim.calculate("household_tax", year).sum() for year in years
        ]
        total_spending = [
            sim.calculate("household_benefits", year).sum() for year in years
        ]
        total_state_tax = [
            sim.calculate("household_state_income_tax", year).sum()
            for year in years
        ]
        total_budget = [
            total_tax[i] - total_spending[i] for i in range(len(years))
        ]
        total_federal_budget = [
            total_tax[i] - total_spending[i] - total_state_tax
            for i in range(len(years))
        ]
    return {
        "total_tax": total_tax,
        "total_spending": total_spending,
        "total_state_tax": total_state_tax,
        "total_budget": total_budget,
        "total_federal_budget": total_federal_budget,
    }
