from policyengine.core import (
    TaxBenefitModel,
    TaxBenefitModelVersion,
    Variable,
    Parameter,
    ParameterValue,
)
import datetime
import requests
from importlib.metadata import version
from policyengine.utils import parse_safe_date
import pandas as pd
from microdf import MicroDataFrame
from pathlib import Path
from .datasets import PolicyEngineUSDataset, USYearData
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


class PolicyEngineUS(TaxBenefitModel):
    id: str = "policyengine-us"
    description: str = "The US's open-source dynamic tax and benefit microsimulation model maintained by PolicyEngine."


us_model = PolicyEngineUS()

pkg_version = version("policyengine-us")

# Get published time from PyPI
response = requests.get("https://pypi.org/pypi/policyengine-us/json")
data = response.json()
upload_time = data["releases"][pkg_version][0]["upload_time_iso_8601"]


class PolicyEngineUSLatest(TaxBenefitModelVersion):
    model: TaxBenefitModel = us_model
    version: str = pkg_version
    created_at: datetime.datetime = datetime.datetime.fromisoformat(
        upload_time
    )

    def __init__(self, **kwargs: dict):
        super().__init__(**kwargs)
        from policyengine_us.system import system
        from policyengine_core.enums import Enum

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
                    tax_benefit_model_version=self,
                    description=param_node.description,
                    data_type=type(param_node(2025)),
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
        from policyengine_us import Microsimulation
        from policyengine.utils.parametric_reforms import (
            simulation_modifier_from_parameter_values,
        )

        assert isinstance(simulation.dataset, PolicyEngineUSDataset)

        dataset = simulation.dataset
        dataset.load()
        microsim = Microsimulation(dataset=None)

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

        # Allow custom variable selection, or use defaults
        if simulation.variables is not None:
            entity_variables = simulation.variables
        else:
            # Default comprehensive variable set
            entity_variables = {
                "person": [
                    # IDs and weights
                    "person_id",
                    "marital_unit_id",
                    "family_id",
                    "spm_unit_id",
                    "tax_unit_id",
                    "household_id",
                    "person_weight",
                    # Demographics
                    "age",
                    "gender",
                    "is_adult",
                    "is_child",
                    # Income
                    "employment_income",
                    "self_employment_income",
                    "pension_income",
                    "social_security",
                    "ssi",
                    # Benefits
                    "snap",
                    "tanf",
                    "medicare",
                    "medicaid",
                    # Tax
                    "payroll_tax",
                ],
                "marital_unit": [
                    "marital_unit_id",
                    "marital_unit_weight",
                ],
                "family": [
                    "family_id",
                    "family_weight",
                ],
                "spm_unit": [
                    "spm_unit_id",
                    "spm_unit_weight",
                    "snap",
                    "tanf",
                    "spm_unit_net_income",
                ],
                "tax_unit": [
                    "tax_unit_id",
                    "tax_unit_weight",
                    "income_tax",
                    "payroll_tax",
                    "state_income_tax",
                    "eitc",
                    "ctc",
                    "adjusted_gross_income",
                ],
                "household": [
                    "household_id",
                    "household_weight",
                    "household_net_income",
                    "household_benefits",
                    "household_tax",
                    "household_market_income",
                ],
            }

        data = {
            "person": pd.DataFrame(),
            "marital_unit": pd.DataFrame(),
            "family": pd.DataFrame(),
            "spm_unit": pd.DataFrame(),
            "tax_unit": pd.DataFrame(),
            "household": pd.DataFrame(),
        }

        for entity, variables in entity_variables.items():
            for var in variables:
                data[entity][var] = microsim.calculate(
                    var, period=simulation.dataset.year, map_to=entity
                ).values

        data["person"] = MicroDataFrame(
            data["person"], weights="person_weight"
        )
        data["marital_unit"] = MicroDataFrame(
            data["marital_unit"], weights="marital_unit_weight"
        )
        data["family"] = MicroDataFrame(
            data["family"], weights="family_weight"
        )
        data["spm_unit"] = MicroDataFrame(
            data["spm_unit"], weights="spm_unit_weight"
        )
        data["tax_unit"] = MicroDataFrame(
            data["tax_unit"], weights="tax_unit_weight"
        )
        data["household"] = MicroDataFrame(
            data["household"], weights="household_weight"
        )

        simulation.output_dataset = PolicyEngineUSDataset(
            name=dataset.name,
            description=dataset.description,
            filepath=str(
                Path(simulation.dataset.filepath).parent
                / (simulation.id + ".h5")
            ),
            year=simulation.dataset.year,
            is_output_dataset=True,
            data=USYearData(
                person=data["person"],
                marital_unit=data["marital_unit"],
                family=data["family"],
                spm_unit=data["spm_unit"],
                tax_unit=data["tax_unit"],
                household=data["household"],
            ),
        )

        simulation.output_dataset.save()


us_latest = PolicyEngineUSLatest()
