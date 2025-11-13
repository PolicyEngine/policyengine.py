from policyengine.core import TaxBenefitModel, TaxBenefitModelVersion, Variable, Parameter, ParameterValue
import datetime
import requests
from importlib.metadata import version
from policyengine.utils import parse_safe_date
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
                    data_type=type(
                        param_node(2025)
                    ),
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
        """Run simulation - implementation depends on US dataset structure."""
        raise NotImplementedError("US simulation runner not yet implemented - pending dataset implementation")


us_latest = PolicyEngineUSLatest()
