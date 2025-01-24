import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation
from .budget import calculate_budget_comparison
from .decile import calculate_decile_comparison


def calculate_macro_comparison(
    simulation: "Simulation",
) -> dict:
    return {
        "budget": calculate_budget_comparison(simulation),
        "decile": calculate_decile_comparison(simulation),
    }
