import typing
if typing.TYPE_CHECKING:
    from policyengine import Simulation
from .local_areas import calculate_local_areas
from .balance import calculate_balance
from .budget_window import calculate_budget_window
from .programs import calculate_programs


def calculate_gov(
    simulation: "Simulation",
) -> dict:
    return {
        "balance": calculate_balance(simulation),
        "budget_window": calculate_budget_window(simulation),
        "programs": calculate_programs(simulation),
        "local_areas": calculate_local_areas(simulation),
    }
