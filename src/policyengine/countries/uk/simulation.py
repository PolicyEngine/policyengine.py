try:
    from policyengine_uk import Simulation as PolicyEngineUKSimulation
    from policyengine_uk.data.dataset_schema import (
        UKSingleYearDataset as PolicyEngineUKSingleYearDataset,
    )
    from policyengine_uk.model_api import Scenario as PolicyEngineUKScenario

    UK_AVAILABLE = True
except ImportError:
    UK_AVAILABLE = False
    PolicyEngineUKSimulation = None
    PolicyEngineUKSingleYearDataset = None
    PolicyEngineUKScenario = None

from policyengine.models import Dataset, Simulation
from policyengine.models.single_year_dataset import SingleYearDataset

try:
    from microdf import MicroDataFrame

    MICRODF_AVAILABLE = True
except ImportError:
    MICRODF_AVAILABLE = False
    MicroDataFrame = None


def run_uk_simulation(simulation: Simulation) -> Dataset:
    """Run the UK-specific simulation."""
    if not UK_AVAILABLE:
        raise ImportError(
            "policyengine-uk is not installed. "
            "Install it with: pip install 'policyengine[uk]' or pip install policyengine-uk"
        )
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


def _apply_uk_parametric_reform(provisions, sim):
    """Apply parametric reforms to UK simulation."""
    try:
        from policyengine_core.periods import instant
    except ImportError:
        raise ImportError(
            "policyengine-core is not installed. "
            "Install it with: pip install 'policyengine[uk]'"
        )

    for provision in provisions:
        parameter_name = provision.parameter.name
        sim.tax_benefit_system.parameters.get_child(parameter_name).update(
            start=instant(provision.start_date.strftime("%Y-%m-%d")),
            stop=instant(provision.end_date.strftime("%Y-%m-%d"))
            if provision.end_date
            else None,
            value=provision.value,
        )


def _get_simulation(simulation: Simulation):
    def modifier(sim):
        # Apply parametric reforms
        if simulation.policy.parameter_values:
            _apply_uk_parametric_reform(
                simulation.policy.parameter_values, sim
            )
        if simulation.policy.simulation_modifier:
            simulation.policy.simulation_modifier(sim)

        if simulation.dynamic.parameter_values:
            _apply_uk_parametric_reform(
                simulation.dynamic.parameter_values, sim
            )
        if simulation.dynamic.simulation_modifier:
            simulation.dynamic.simulation_modifier(sim)

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
