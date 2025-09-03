from policyengine_core.taxbenefitsystems import TaxBenefitSystem
from policyengine_core.parameters import Parameter as CoreParameter
from policyengine.models import Parameter, ParameterValue, Variable, Policy, Dynamics
import datetime
from policyengine.utils.version import get_model_version


def get_metadata(system: TaxBenefitSystem, country: str):
    current_law = Policy(name="Current law")
    static = Dynamics(name="Static")
    parameters = []
    parameter_values = []
    version = get_model_version(country)

    for param in system.parameters.get_descendants():
        if isinstance(param, CoreParameter):
            p = Parameter(
                name=param.name,
                label=param.metadata.get("label"),
                description=param.description,
                unit=param.metadata.get("unit"),
                data_type=type(param(2029)),
                country=country,
            )

            # Also add values
            values_list = param.values_list[::-1]
            for i in range(len(values_list)): # Moving forwards in time
                if i == len(values_list) - 1:
                    end_date = None
                else:
                    end_date = _safe_date(values_list[i + 1].instant_str)
                p_value = ParameterValue(
                    policy=None,
                    parameter=p,
                    value=values_list[i].value,
                    start_date=_safe_date(values_list[i].instant_str),
                    end_date=end_date,
                    model_version=version,
                    country=country,
                )
                parameter_values.append(p_value)

        else: # Parameter subfolder
            p = Parameter(
                name=param.name,
                label=param.metadata.get("label"),
                description=param.description,
                unit=None,
                data_type=None,
                country=country,
            )

    # Now, variables
    variables = []

    for variable in system.variables.values():
        v = Variable(
            name=variable.name,
            label=variable.label,
            description=variable.documentation,
            unit=variable.unit,
            data_type=variable.value_type,
            country=country,
            entity=variable.entity.key
        )
        variables.append(v)

    return {
        "current_law": current_law,
        "static": static,
        "parameters": parameters,
        "parameter_values": parameter_values,
        "variables": variables,
    }

def _safe_date(date_str: str | None) -> datetime.datetime | None:
    # 0000-01-01 to early- move it to 0001-01-01
    if date_str == "0000-01-01":
        date_str = "0001-01-01"
    if date_str is None:
        return None
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None