try:
    from policyengine_core.taxbenefitsystems import TaxBenefitSystem
    from policyengine_core.parameters import Parameter as CoreParameter

    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False
    TaxBenefitSystem = None
    CoreParameter = None
from policyengine.models import (
    Parameter,
    ParameterValue,
    Variable,
    Policy,
    Dynamic,
)
import datetime
from policyengine.utils.version import get_model_version


def get_metadata(system, country: str):
    if not CORE_AVAILABLE:
        raise ImportError(
            "policyengine-core is not installed. "
            "Install it with: pip install 'policyengine[core]'"
        )

    if system is None:
        raise ValueError("System parameter cannot be None")

    current_law = Policy(name="Current law")
    static = Dynamic(name="Static")
    parameters = []
    parameter_values = []
    version = get_model_version(country)

    param_tree = system.parameters

    for param in param_tree.get_descendants():
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
            for i in range(len(values_list)):  # Moving forwards in time
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

        else:  # Parameter subfolder
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
            entity=variable.entity.key,
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
    """Parse a date safely.

    Accepts YYYY-MM-DD and ISO timestamps (YYYY-MM-DDTHH:MM:SS), and treats
    "infinity" / "+infinity" or None as open-ended (returns None).
    Also normalises the invalid 0000-01-01 to 0001-01-01 for compatibility.
    """
    if date_str is None:
        return None
    s = date_str.strip()
    low = s.lower()
    if low in {"infinity", "+infinity", "inf", "+inf", "-infinity", "-inf"}:
        # Treat as open-ended; dates should not use infinities here
        return None
    if s == "0000-01-01":
        s = "0001-01-01"
    # Try date only
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        pass
    # Try ISO timestamp variants
    try:
        # Remove trailing Z if present (naive)
        if s.endswith("Z"):
            s = s[:-1]
        return datetime.datetime.fromisoformat(s)
    except Exception:
        # As a final fallback, use the earliest valid date to satisfy required fields
        return datetime.datetime(1, 1, 1)
