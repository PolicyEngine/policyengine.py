from pydantic import BaseModel
import json

class Dataset(BaseModel):
    data: str | None = None
    situation: dict | None = None

    def __hash__(self):
        return hash(json.dumps(self.parameter_changes))

enhanced_frs = Dataset(data="hf://policyengine/policyengine-uk-data/enhanced_frs_2022_23.h5")
frs = Dataset(data="hf://policyengine/policyengine-uk-data/frs_2022_23.h5")
enhanced_cps = Dataset(data="hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5")
cps = Dataset(data="hf://policyengine/policyengine-us-data/cps_2023.h5")
pooled_cps = Dataset(data="hf://policyengine/policyengine-us-data/pooled_3_year_cps_2023.h5")