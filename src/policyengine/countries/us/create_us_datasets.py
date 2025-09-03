from policyengine_us import Microsimulation
from policyengine.models.single_year_dataset import SingleYearDataset
from policyengine.models.dataset import Dataset
import pandas as pd

sim = Microsimulation()

tables = {}

for entity in sim.tax_benefit_system.entities_by_singular().keys():
    for variable in sim.tax_benefit_system.variables:
        if sim.tax_benefit_system.variables[variable].entity.key != entity:
            continue
        known_periods = map(str, sim.get_known_periods(variable))
        if "2024" in known_periods:
            tables[entity] = tables.get(entity, pd.DataFrame())
            tables[entity][variable] = sim.get_holder(variable).get_array(2024)

ecps_2024 = Dataset(
    name="ECPS 2024",
    data=SingleYearDataset(
        tables=tables,
        year=2024,
    ),
    dataset_type="us",
)
