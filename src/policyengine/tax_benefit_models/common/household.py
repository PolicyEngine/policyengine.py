from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from typing import Any


def validate_annual_household_inputs(
    *,
    year: Any,
    entities: Mapping[str, Sequence[Mapping[str, Any]]],
    listed_entities: Collection[str] = (),
) -> int:
    """Validate annual-only household calculator inputs.

    Errors name an input of an entity in ``listed_entities``, which the caller
    passed as a list of groups, by its group's position, even in a list of
    one group.
    """
    validated_year = _validate_annual_year(year)
    _validate_unperiodized_values(entities, listed_entities=listed_entities)
    return validated_year


def _validate_annual_year(year: Any) -> int:
    if isinstance(year, bool):
        raise _annual_period_error(year)
    if isinstance(year, int):
        return year
    if isinstance(year, str) and year.isdecimal() and len(year) == 4:
        return int(year)
    raise _annual_period_error(year)


def _annual_period_error(year: Any) -> ValueError:
    return ValueError(
        "Household calculations require a calendar year as an integer, "
        "for example year=2026. "
        "Monthly periods are not supported by calculate_household. "
        f"Received year={year!r}."
    )


def _validate_unperiodized_values(
    entities: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    listed_entities: Collection[str] = (),
) -> None:
    for entity, records in entities.items():
        for index, record in enumerate(records):
            for variable, value in record.items():
                if variable != "id" and isinstance(value, Mapping):
                    location = _input_location(
                        entity,
                        index,
                        len(records),
                        variable,
                        listed=entity in listed_entities,
                    )
                    raise ValueError(
                        "Periodized household inputs are not supported by "
                        "calculate_household. Pass annual scalar input values "
                        f"only; received a periodized value for {location}."
                    )


def _input_location(
    entity: str,
    index: int,
    record_count: int,
    variable: str,
    *,
    listed: bool = False,
) -> str:
    if record_count == 1 and entity != "people" and not listed:
        return f"{entity}.{variable}"
    return f"{entity}[{index}].{variable}"
