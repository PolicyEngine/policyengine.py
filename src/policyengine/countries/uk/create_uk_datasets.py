from policyengine_uk import Microsimulation
from policyengine.models.single_year_dataset import SingleYearDataset
from policyengine.models.dataset import Dataset

sim = Microsimulation()

efrs_2029 = Dataset(
    name="EFRS 2029",
    data=SingleYearDataset(
        tables=dict(
            person=sim.dataset[2029].person,
            benunit=sim.dataset[2029].benunit,
            household=sim.dataset[2029].household,
        ),
        year=2029,
    ),
    dataset_type="uk",
)
