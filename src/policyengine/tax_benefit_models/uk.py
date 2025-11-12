from policyengine.core import *
from pydantic import BaseModel, Field, ConfigDict
import pandas as pd
from typing import Dict
import datetime
import requests
from policyengine.utils import parse_safe_date
from pathlib import Path
from importlib.metadata import version


class UKYearData(BaseModel):
    """Entity-level data for a single year."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    person: pd.DataFrame
    benunit: pd.DataFrame
    household: pd.DataFrame


class PolicyEngineUKDataset(Dataset):
    """UK dataset with multi-year entity-level data."""

    data: UKYearData | None = None

    def save(self) -> None:
        """Save dataset to HDF5 file."""
        filepath = self.filepath
        with pd.HDFStore(filepath, mode="w") as store:
            store["person"] = self.data.person
            store["benunit"] = self.data.benunit
            store["household"] = self.data.household

    def load(self) -> None:
        """Load dataset from HDF5 file into this instance."""
        filepath = self.filepath
        with pd.HDFStore(filepath, mode="r") as store:
            self.data = UKYearData(
                person=store["person"],
                benunit=store["benunit"],
                household=store["household"],
            )

    def __repr__(self) -> str:
        if self.data is None:
            return f"<PolicyEngineUKDataset id={self.id} year={self.year} filepath={self.filepath} (not loaded)>"
        else:
            n_people = len(self.data.person)
            n_benunits = len(self.data.benunit)
            n_households = len(self.data.household)
            return f"<PolicyEngineUKDataset id={self.id} year={self.year} filepath={self.filepath} people={n_people} benunits={n_benunits} households={n_households}>"


class PolicyEngineUK(TaxBenefitModel):
    id: str = "policyengine-uk"
    description: str = "The UK's open-source dynamic tax and benefit microsimulation model maintained by PolicyEngine."


uk_model = PolicyEngineUK()

pkg_version = version("policyengine-uk")

# Get published time from PyPI
response = requests.get("https://pypi.org/pypi/policyengine-uk/json")
data = response.json()
upload_time = data["releases"][pkg_version][0]["upload_time_iso_8601"]


class PolicyEngineUKLatest(TaxBenefitModelVersion):
    model: TaxBenefitModel = uk_model
    version: str = pkg_version
    created_at: datetime.datetime = datetime.datetime.fromisoformat(
        upload_time
    )

    def __init__(self, **kwargs: dict):
        super().__init__(**kwargs)
        from policyengine_uk.system import system

        self.id = f"{self.model.id}@{self.version}"

        self.variables = []
        for var_obj in system.variables.values():
            variable = Variable(
                id=self.id + "-" + var_obj.name,
                tax_benefit_model_version=self,
                entity=var_obj.entity.key,
                description=var_obj.documentation,
                data_type=var_obj.value_type,
            )
            self.variables.append(variable)

        self.parameters = []
        from policyengine_core.parameters import Parameter as CoreParameter

        for param_node in system.parameters.get_descendants():
            if isinstance(param_node, CoreParameter):
                parameter = Parameter(
                    id=self.id + "-" + param_node.name,
                    name=param_node.name,
                    tax_benefit_model_version=self,
                    description=param_node.description,
                    data_type=type(
                        param_node(2025)
                    ),  # Example year to infer type
                    unit=param_node.metadata.get("unit"),
                )
                self.parameters.append(parameter)

                for i in range(len(param_node.values_list)):
                    param_at_instant = param_node.values_list[i]
                    if i + 1 < len(param_node.values_list):
                        next_instant = param_node.values_list[i + 1]
                    else:
                        next_instant = None
                    parameter_value = ParameterValue(
                        parameter=parameter,
                        start_date=parse_safe_date(
                            param_at_instant.instant_str
                        ),
                        end_date=parse_safe_date(next_instant.instant_str)
                        if next_instant
                        else None,
                        value=param_at_instant.value,
                    )
                    self.parameter_values.append(parameter_value)

    def run(self, simulation: "Simulation") -> "Simulation":
        from policyengine_uk import Microsimulation
        from policyengine_uk.data import UKSingleYearDataset

        assert isinstance(simulation.dataset, PolicyEngineUKDataset)

        dataset = simulation.dataset
        dataset.load()
        input_data = UKSingleYearDataset(
            person=dataset.data.person,
            benunit=dataset.data.benunit,
            household=dataset.data.household,
            fiscal_year=dataset.year,
        )
        microsim = Microsimulation(dataset=input_data)

        entity_variables = {
            "person": [
                "person_id",
                "benunit_id",
                "household_id",
                "age",
                "employment_income",
                "person_weight",
            ],
            "benunit": ["benunit_id", "benunit_weight"],
            "household": [
                "household_id",
                "household_weight",
                "hbai_household_net_income",
                "equiv_hbai_household_net_income",
            ],
        }

        data = {
            "person": pd.DataFrame(),
            "benunit": pd.DataFrame(),
            "household": pd.DataFrame(),
        }

        for entity, variables in entity_variables.items():
            for var in variables:
                data[entity][var] = microsim.calculate(
                    var, period=simulation.dataset.year, map_to=entity
                ).values

        simulation.output_dataset = PolicyEngineUKDataset(
            name=dataset.name,
            description=dataset.description,
            filepath=str(
                Path(simulation.dataset.filepath).parent
                / (simulation.id + ".h5")
            ),
            year=simulation.dataset.year,
            is_output_dataset=True,
            data=UKYearData(
                person=data["person"],
                benunit=data["benunit"],
                household=data["household"],
            ),
        )

        simulation.output_dataset.save()


# Rebuild models to resolve forward references
PolicyEngineUKDataset.model_rebuild()
PolicyEngineUKLatest.model_rebuild()

uk_latest = PolicyEngineUKLatest()
