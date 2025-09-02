from policyengine_uk import Scenario, Simulation
from policyengine.models import ParameterValue, Parameter
from typing import List
from policyengine_core.periods import instant


def apply_parametric_reform(provisions: List[ParameterValue]) -> Scenario:
    def modifier(sim: Simulation):
        for provision in provisions:
            parameter_name = provision.parameter.name
            sim.tax_benefit_system.parameters.get_child(parameter_name).update(
                start=instant(provision.start_date.strftime("%Y-%m-%d")),
                stop=instant(provision.end_date.strftime("%Y-%m-%d"))
                if provision.end_date
                else None,
                value=provision.value,
            )

    return Scenario(simulation_modifier=modifier)
