from policyengine_uk import Simulation as PolicyEngineUKSimulation
from policyengine_uk.data.dataset_schema import (
    UKSingleYearDataset as PolicyEngineUKSingleYearDataset,
)
from policyengine_uk.model_api import Scenario as PolicyEngineUKScenario

from policyengine.models import Dataset, Simulation
from policyengine.utils.parametric_reforms import apply_parametric_reform

from policyengine.models.single_year_dataset import SingleYearDataset

from microdf import MicroDataFrame


def run_uk_simulation(simulation: Simulation) -> Dataset:
    """Run the UK-specific simulation."""
    # Implement UK-specific simulation logic here
    sim = _get_simulation(simulation)

    output = simulation.dataset.data.copy()
    output.tables["household"]["gov_tax"] = sim.calculate(
        "gov_tax",
    )
    output.tables["household"]["gov_spending"] = sim.calculate("gov_spending")
    output.tables["household"]["gov_balance"] = sim.calculate("gov_balance")

    # Cast to microdf
    output.tables["person"]["weight_value"] = sim.calculate(
        "household_weight", map_to="person"
    )
    output.tables["benunit"]["weight_value"] = sim.calculate(
        "household_weight", map_to="benunit"
    )
    output.tables["household"]["weight_value"] = sim.calculate(
        "household_weight", map_to="household"
    )

    simulation.result = Dataset(
        dataset_type="uk",
        data=output,
    )


def _get_simulation(simulation: Simulation):
    parametric_policy = apply_parametric_reform(
        simulation.policy.parameter_values or []
    )
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
    sim = PolicyEngineUKSimulation(
        dataset=PolicyEngineUKSingleYearDataset(
            person=simulation.dataset.data.tables["person"],
            benunit=simulation.dataset.data.tables["benunit"],
            household=simulation.dataset.data.tables["household"],
            fiscal_year=simulation.dataset.data.year,
        ),
        scenario=scenario,
    )
    sim.default_calculation_period = simulation.dataset.data.year
    return sim
