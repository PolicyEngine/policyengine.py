from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from .baseline_parameter_value import BaselineParameterValue
    from .baseline_variable import BaselineVariable
    from .parameter import Parameter


class Model(BaseModel):
    id: str
    name: str
    description: str | None = None
    simulation_function: Callable

    def create_seed_objects(self, model_version):
        from policyengine_core.parameters import Parameter as CoreParameter

        from .baseline_parameter_value import BaselineParameterValue
        from .baseline_variable import BaselineVariable
        from .parameter import Parameter

        if self.id == "policyengine_uk":
            from policyengine_uk.tax_benefit_system import system
        elif self.id == "policyengine_us":
            from policyengine_us.system import system
        else:
            raise ValueError("Unsupported model.")

        parameters = []
        baseline_parameter_values = []
        baseline_variables = []
        seen_parameter_ids = set()

        for parameter in system.parameters.get_descendants():
            # Skip if we've already processed this parameter ID
            if parameter.name in seen_parameter_ids:
                continue
            seen_parameter_ids.add(parameter.name)
            param = Parameter(
                id=parameter.name,
                description=parameter.description,
                data_type=None,
                model=self,
            )
            parameters.append(param)
            if isinstance(parameter, CoreParameter):
                values = parameter.values_list[::-1]
                param.data_type = type(values[-1].value)
                for i in range(len(values)):
                    value_at_instant = values[i]
                    instant_str = safe_parse_instant_str(
                        value_at_instant.instant_str
                    )
                    if i + 1 < len(values):
                        next_instant_str = safe_parse_instant_str(
                            values[i + 1].instant_str
                        )
                    else:
                        next_instant_str = None
                    baseline_param_value = BaselineParameterValue(
                        parameter=param,
                        model_version=model_version,
                        value=value_at_instant.value,
                        start_date=instant_str,
                        end_date=next_instant_str,
                    )
                    baseline_parameter_values.append(baseline_param_value)

        for variable in system.variables.values():
            baseline_variable = BaselineVariable(
                id=variable.name,
                model_version=model_version,
                entity=variable.entity.key,
                label=variable.label,
                description=variable.documentation,
                data_type=variable.value_type,
            )
            baseline_variables.append(baseline_variable)

        return SeedObjects(
            parameters=parameters,
            baseline_parameter_values=baseline_parameter_values,
            baseline_variables=baseline_variables,
        )


def safe_parse_instant_str(instant_str: str) -> datetime:
    if instant_str == "0000-01-01":
        return datetime(1, 1, 1)
    else:
        try:
            return datetime.strptime(instant_str, "%Y-%m-%d")
        except ValueError:
            # Handle invalid dates like 2021-06-31
            # Try to parse year and month, then use last valid day
            parts = instant_str.split("-")
            if len(parts) == 3:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])

                # Find the last valid day of the month
                import calendar

                last_day = calendar.monthrange(year, month)[1]
                if day > last_day:
                    print(
                        f"Warning: Invalid date {instant_str}, using {year}-{month:02d}-{last_day:02d}"
                    )
                    return datetime(year, month, last_day)

            # If we can't parse it at all, print and raise
            print(f"Error: Cannot parse date {instant_str}")
            raise


class SeedObjects(BaseModel):
    parameters: list["Parameter"]
    baseline_parameter_values: list["BaselineParameterValue"]
    baseline_variables: list["BaselineVariable"]
