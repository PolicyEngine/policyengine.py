from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def validate_annual_household_inputs(
    *,
    year: Any,
    entities: Mapping[str, Sequence[Mapping[str, Any]]],
) -> int:
    """Validate annual-only household calculator inputs."""
    validated_year = _validate_annual_year(year)
    _validate_unperiodized_values(entities)
    return validated_year


def _validate_annual_year(year: Any) -> int:
    if isinstance(year, bool):
        raise _annual_period_error()
    if isinstance(year, int):
        return year
    if isinstance(year, str) and year.isdecimal() and len(year) == 4:
        return int(year)
    raise _annual_period_error()


def _annual_period_error() -> ValueError:
    return ValueError(
        "Household calculations require a calendar year as an integer, "
        "for example year=2026. Monthly periods are not supported by "
        "calculate_household."
    )


def _validate_unperiodized_values(
    entities: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    for entity, records in entities.items():
        for index, record in enumerate(records):
            for variable, value in record.items():
                if variable != "id" and isinstance(value, Mapping):
                    raise ValueError(
                        "Periodized household inputs are not supported by "
                        "calculate_household. Pass annual scalar input values "
                        f"only; received a periodized value for "
                        f"{_input_location(entity, index, len(records), variable)}."
                    )


def _input_location(
    entity: str,
    index: int,
    record_count: int,
    variable: str,
) -> str:
    if record_count == 1 and entity != "people":
        return f"{entity}.{variable}"
    return f"{entity}[{index}].{variable}"
