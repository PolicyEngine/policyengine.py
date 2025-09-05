from policyengine_us import Simulation as PolicyEngineUSSimulation
from policyengine_core.data import Dataset

from policyengine.models import Dataset, Simulation
from policyengine.utils.parametric_reforms import apply_parametric_reform

from policyengine.models.single_year_dataset import SingleYearDataset

from microdf import MicroDataFrame
import pandas as pd


def run_us_simulation(simulation: Simulation) -> Dataset:
    """Run the US-specific simulation."""
    # Implement UK-specific simulation logic here
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
        dataset_type="us",
        data=output,
    )


def _get_simulation(simulation: Simulation):
    parametric_policy = apply_parametric_reform(
        simulation.policy.parameter_values or []
    )
    parametric_dynamic = apply_parametric_reform(
        simulation.dynamic.parameter_values or []
    )

    def modifier(sim):
        parametric_policy.simulation_modifier(sim)
        if simulation.policy.simulation_modifier:
            simulation.policy.simulation_modifier(sim)

        parametric_dynamic.simulation_modifier(sim)
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
