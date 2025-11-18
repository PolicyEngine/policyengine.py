import datetime
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import requests
from microdf import MicroDataFrame

from policyengine.core import (
    Parameter,
    ParameterValue,
    TaxBenefitModel,
    TaxBenefitModelVersion,
    Variable,
)
from policyengine.utils import parse_safe_date

from .datasets import PolicyEngineUKDataset, UKYearData

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


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

    entity_variables: dict[str, list[str]] = {
        "person": [
            # IDs and weights
            "person_id",
            "benunit_id",
            "household_id",
            "person_weight",
            # Demographics
            "age",
            "gender",
            "is_adult",
            "is_SP_age",
            "is_child",
            # Income
            "employment_income",
            "self_employment_income",
            "pension_income",
            "private_pension_income",
            "savings_interest_income",
            "dividend_income",
            "property_income",
            "total_income",
            "earned_income",
            # Benefits
            "universal_credit",
            "child_benefit",
            "pension_credit",
            "income_support",
            "working_tax_credit",
            "child_tax_credit",
            # Tax
            "income_tax",
            "national_insurance",
        ],
        "benunit": [
            # IDs and weights
            "benunit_id",
            "benunit_weight",
            # Structure
            "family_type",
            # Income and benefits
            "universal_credit",
            "child_benefit",
            "working_tax_credit",
            "child_tax_credit",
        ],
        "household": [
            # IDs and weights
            "household_id",
            "household_weight",
            # Income measures
            "household_net_income",
            "hbai_household_net_income",
            "equiv_hbai_household_net_income",
            "household_market_income",
            "household_gross_income",
            # Benefits and tax
            "household_benefits",
            "household_tax",
            "vat",
            # Housing
            "rent",
            "council_tax",
            "tenure_type",
        ],
    }

    def __init__(self, **kwargs: dict):
        super().__init__(**kwargs)
        from policyengine_core.enums import Enum
        from policyengine_uk.system import system

        self.id = f"{self.model.id}@{self.version}"

        self.variables = []
        for var_obj in system.variables.values():
            variable = Variable(
                id=self.id + "-" + var_obj.name,
                name=var_obj.name,
                tax_benefit_model_version=self,
                entity=var_obj.entity.key,
                description=var_obj.documentation,
                data_type=var_obj.value_type
                if var_obj.value_type is not Enum
                else str,
            )
            if (
                hasattr(var_obj, "possible_values")
                and var_obj.possible_values is not None
            ):
                variable.possible_values = list(
                    map(
                        lambda x: x.name,
                        var_obj.possible_values._value2member_map_.values(),
                    )
                )
            self.variables.append(variable)

        self.parameters = []
        from policyengine_core.parameters import Parameter as CoreParameter

        for param_node in system.parameters.get_descendants():
            if isinstance(param_node, CoreParameter):
                parameter = Parameter(
                    id=self.id + "-" + param_node.name,
                    name=param_node.name,
                    label=param_node.metadata.get("label", param_node.name),
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

        from policyengine.utils.parametric_reforms import (
            simulation_modifier_from_parameter_values,
        )

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

        if (
            simulation.policy
            and simulation.policy.simulation_modifier is not None
        ):
            simulation.policy.simulation_modifier(microsim)
        elif simulation.policy:
            modifier = simulation_modifier_from_parameter_values(
                simulation.policy.parameter_values
            )
            modifier(microsim)

        if (
            simulation.dynamic
            and simulation.dynamic.simulation_modifier is not None
        ):
            simulation.dynamic.simulation_modifier(microsim)
        elif simulation.dynamic:
            modifier = simulation_modifier_from_parameter_values(
                simulation.dynamic.parameter_values
            )
            modifier(microsim)

        data = {
            "person": pd.DataFrame(),
            "benunit": pd.DataFrame(),
            "household": pd.DataFrame(),
        }

        for entity, variables in self.entity_variables.items():
            for var in variables:
                data[entity][var] = microsim.calculate(
                    var, period=simulation.dataset.year, map_to=entity
                ).values

        data["person"] = MicroDataFrame(
            data["person"], weights="person_weight"
        )
        data["benunit"] = MicroDataFrame(
            data["benunit"], weights="benunit_weight"
        )
        data["household"] = MicroDataFrame(
            data["household"], weights="household_weight"
        )

        simulation.output_dataset = PolicyEngineUKDataset(
            id=simulation.id,
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

    def save(self, simulation: "Simulation"):
        """Save the simulation's output dataset."""
        simulation.output_dataset.save()

    def load(self, simulation: "Simulation"):
        """Load the simulation's output dataset."""
        simulation.output_dataset = PolicyEngineUKDataset(
            id=simulation.id,
            name=simulation.dataset.name,
            description=simulation.dataset.description,
            filepath=str(
                Path(simulation.dataset.filepath).parent
                / (simulation.id + ".h5")
            ),
            year=simulation.dataset.year,
            is_output_dataset=True,
        )


uk_latest = PolicyEngineUKLatest()
