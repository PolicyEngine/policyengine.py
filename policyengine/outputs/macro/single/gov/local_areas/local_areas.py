import typing
if typing.TYPE_CHECKING:
    from policyengine import Simulation
from policyengine.outputs.macro.single.gov.local_areas.local_authorities import (
    calculate_local_authorities,
)
from policyengine.outputs.macro.single.gov.local_areas.parliamentary_constituencies import (
    calculate_parliamentary_constituencies,
)


def calculate_local_areas(
    simulation: "Simulation",
) -> dict:
    if simulation.country != "uk":
        return None

    return {
        "local_authorities": calculate_local_authorities(simulation),
        "parliamentary_constituencies": calculate_parliamentary_constituencies(
            simulation
        ),
    }
