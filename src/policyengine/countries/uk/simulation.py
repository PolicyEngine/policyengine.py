from pydantic import BaseModel
from policyengine.models import Simulation, Dataset
from policyengine.utils.parametric_reforms import apply_parametric_reform
from policyengine_uk import Simulation as PolicyEngineUKSimulation
from policyengine_uk.model_api import Scenario as PolicyEngineUKScenario
from policyengine_uk.data.dataset_schema import (
    UKSingleYearDataset as PolicyEngineUKSingleYearDataset,
)
from .uk_single_year_dataset import UKSingleYearDataset

def run_uk_simulation(simulation: Simulation) -> Dataset:
    """Run the UK-specific simulation."""
    # Implement UK-specific simulation logic here
    sim = _get_simulation(simulation)

    output_dataset = Dataset(
        data=UKSingleYearDataset(
            person=simulation.dataset.data.person.copy(),
            benunit=simulation.dataset.data.benunit.copy(),
            household=simulation.dataset.data.household.copy(),
            year=simulation.dataset.data.year,
        ),
        dataset_type="uk",
    )
    output_dataset.data.household["gov_tax"] = sim.calculate("gov_tax", simulation.dataset.data.year)
    output_dataset.data.household["gov_spending"] = sim.calculate(
        "gov_spending", simulation.dataset.data.year
    )
    output_dataset.data.household["gov_balance"] = sim.calculate(
        "gov_balance", simulation.dataset.data.year
    )

    simulation.output_data = output_dataset

    return output_dataset

def _get_simulation(simulation: Simulation):
    parametric_policy = apply_parametric_reform(simulation.policy.parameter_values or [])
    parametric_dynamics = apply_parametric_reform(
        simulation.dynamics.parameter_values or []
    )

    def modifier(sim):
        parametric_policy.simulation_modifier(sim)
        if simulation.policy.simulation_modifier:
            simulation.policy.simulation_modifier(sim)

        parametric_dynamics.simulation_modifier(sim)
        if simulation.dynamics.simulation_modifier:
            simulation.dynamics.simulation_modifier(sim)

    scenario = PolicyEngineUKScenario(simulation_modifier=modifier)
    return PolicyEngineUKSimulation(
        dataset=PolicyEngineUKSingleYearDataset(
            person=simulation.dataset.data.person,
            benunit=simulation.dataset.data.benunit,
            household=simulation.dataset.data.household,
            fiscal_year=simulation.dataset.data.year,
        ),
        scenario=scenario,
    )