import typing
if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel
from policyengine.utils.calculations import get_change

from .macro.single import calculate_government_balance, FiscalSummary

class FiscalComparison(BaseModel):
    baseline: FiscalSummary
    reform: FiscalSummary
    change: FiscalSummary

class EconomyComparison(BaseModel):
    fiscal: FiscalComparison

def calculate_economy_comparison(simulation: "Simulation"):
    if not simulation.is_comparison:
        raise ValueError("Simulation must be a comparison simulation.")
    
    baseline = simulation.baseline_simulation
    reform = simulation.reform_simulation
    options = simulation.options

    baseline_balance = calculate_government_balance(baseline, options)
    reform_balance = calculate_government_balance(reform, options)
    change = get_change(baseline_balance, reform_balance)
    fiscal_comparison = FiscalComparison(baseline=baseline_balance, reform=reform_balance, change=change)

    return EconomyComparison(
        fiscal=fiscal_comparison,
    )

