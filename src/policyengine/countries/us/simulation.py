try:
    from policyengine_us import Simulation as PolicyEngineUSSimulation

    US_AVAILABLE = True
except ImportError:
    US_AVAILABLE = False
    PolicyEngineUSSimulation = None

# Note: Dataset import is from policyengine.models, not policyengine_core

from policyengine.models import Dataset, Simulation
from policyengine.models.single_year_dataset import SingleYearDataset

try:
    from microdf import MicroDataFrame

    MICRODF_AVAILABLE = True
except ImportError:
    MICRODF_AVAILABLE = False
    MicroDataFrame = None

import pandas as pd


def run_us_simulation(simulation: Simulation) -> Dataset:
    """Run the US-specific simulation."""
    if not US_AVAILABLE:
        raise ImportError(
            "policyengine-us is not installed. "
            "Install it with: pip install 'policyengine[us]' or pip install policyengine-us"
        )
    # Implement US-specific simulation logic here
    sim = _get_simulation(simulation)

    output = simulation.dataset.data.copy()
    output.tables["tax_unit"]["income_tax"] = sim.calculate(
        "income_tax",
    )

    for entity in [
        "person",
        "family",
        "tax_unit",
        "marital_unit",
        "spm_unit",
        "household",
    ]:
        output.tables[entity]["weight_value"] = sim.calculate(
            "household_weight", map_to=entity
        )

    simulation.result = Dataset(
        dataset_type="us_single_year",
        data=output,
    )


def _apply_us_parametric_reform(provisions, sim):
    """Apply parametric reforms to US simulation."""
    try:
        from policyengine_core.periods import instant
    except ImportError:
        raise ImportError(
            "policyengine-core is not installed. "
            "Install it with: pip install 'policyengine[us]'"
        )

    for provision in provisions:
        parameter_name = provision.parameter.name
        sim.tax_benefit_system.parameters.get_child(parameter_name).update(
            start=instant(provision.start_date.strftime("%Y-%m-%d")),
            stop=(
                instant(provision.end_date.strftime("%Y-%m-%d"))
                if provision.end_date
                else None
            ),
            value=provision.value,
        )


def _get_simulation(simulation: Simulation):
    def modifier(sim):
        # Apply parametric reforms
        if simulation.policy.parameter_values:
            _apply_us_parametric_reform(
                simulation.policy.parameter_values, sim
            )
        if simulation.policy.simulation_modifier:
            simulation.policy.simulation_modifier(sim)

        if simulation.dynamic.parameter_values:
            _apply_us_parametric_reform(
                simulation.dynamic.parameter_values, sim
            )
        if simulation.dynamic.simulation_modifier:
            simulation.dynamic.simulation_modifier(sim)

    sim = PolicyEngineUSSimulation(
        dataset=convert_entity_tables_to_us_dataset(simulation.dataset.data),
    )
    modifier(sim)
    sim.default_calculation_period = simulation.dataset.data.year
    return sim


def convert_entity_tables_to_us_dataset(
    dataset: SingleYearDataset,
) -> pd.DataFrame:
    person_df = pd.DataFrame()

    for table_name, table in dataset.tables.items():
        if table_name == "person":
            for col in table.columns:
                person_df[f"{col}__{dataset.year}"] = table[col].values
        else:
            foreign_key = dataset.tables["person"][f"person_{table_name}_id"]
            primary_key = dataset.tables[table_name][f"{table_name}_id"]

            projected = table.set_index(primary_key).loc[foreign_key]

            for col in projected.columns:
                person_df[f"{col}__{dataset.year}"] = projected[col].values

    return person_df
