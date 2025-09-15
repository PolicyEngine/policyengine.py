from pydantic import BaseModel
from ..models import Simulation, Model, Dataset, Policy, Dynamic, ModelVersion
import pandas as pd
import importlib.metadata

def run_policyengine_uk(dataset: "Dataset", policy: "Policy | None" = None, dynamic: "Dynamic | None" = None) -> dict[str, "pd.DataFrame"]:
    data: dict[str, pd.DataFrame] = dataset.data

    from policyengine_uk import Microsimulation
    from policyengine_uk.data import UKSingleYearDataset

    pe_input_data = UKSingleYearDataset(
        person=data["person"],
        benunit=data["benunit"],
        household=data["household"],
        fiscal_year=dataset.year,
    )

    sim = Microsimulation(dataset=pe_input_data)

    if policy is not None:
        policy.simulation_modifier(sim)

    # Skip reforms for now

    output_data = {}

    for entity in ["person", "benunit", "household"]:
        output_data[entity] = pd.DataFrame()
        for variable in sim.tax_benefit_system.variables.values():
            correct_entity = variable.entity.key == entity
            has_data = dataset.year in sim.get_holder(variable_name=variable.name).get_known_periods()
            if correct_entity and has_data:
                output_data[entity][variable.name] = sim.get_array(variable.name, dataset.year)
    
    return output_data

policyengine_uk_model = Model(
    id="policyengine_uk",
    name="PolicyEngine UK",
    description="PolicyEngine's open-source tax-benefit microsimulation model.",
    simulation_function=run_policyengine_uk,
)

# Get policyengine-uk version


policyengine_uk_latest_version = ModelVersion(
    model=policyengine_uk_model,
    version=importlib.metadata.distribution("policyengine_uk").version,
)