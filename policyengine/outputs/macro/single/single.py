import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation
from .gov import calculate_gov
from .household import calculate_household


def calculate_single_macro_scenario(
    simulation: "Simulation",
) -> dict:
    return {
        "gov": calculate_gov(simulation),
        "household": calculate_household(simulation),
    }
