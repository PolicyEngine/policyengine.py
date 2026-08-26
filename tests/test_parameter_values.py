"""Tests for parameter history conversion from PolicyEngine Core."""

from datetime import datetime
from types import SimpleNamespace

from policyengine.core.parameter import Parameter
from policyengine.core.parameter_value import ParameterValue


def _parameter_with_core_values(*values: tuple[str, object]) -> Parameter:
    parameter = Parameter.model_construct(
        name="gov.test.value",
        tax_benefit_model_version=None,
    )
    parameter._core_param = SimpleNamespace(
        values_list=[
            SimpleNamespace(instant_str=start_date, value=value)
            for start_date, value in values
        ]
    )
    parameter._parameter_values = None
    return parameter


def test__newest_first_core_values__then_history_is_chronological_and_inclusive():
    parameter = _parameter_with_core_values(
        ("2024-07-15", 30),
        ("2022-03-10", 20),
        ("2020-01-01", 10),
    )

    values = parameter.parameter_values

    assert [value.start_date for value in values] == [
        datetime(2020, 1, 1),
        datetime(2022, 3, 10),
        datetime(2024, 7, 15),
    ]
    assert [value.end_date for value in values] == [
        datetime(2022, 3, 9),
        datetime(2024, 7, 14),
        None,
    ]
    assert [value.value for value in values] == [10, 20, 30]
    assert all(value.parameter is parameter for value in values)


def test__single_core_value__then_history_is_open_ended():
    parameter = _parameter_with_core_values(("2024-01-01", 10))

    (value,) = parameter.parameter_values

    assert value.start_date == datetime(2024, 1, 1)
    assert value.end_date is None


def test__duplicate_effective_starts__then_first_core_value_wins():
    parameter = _parameter_with_core_values(
        ("2024-01-01", "effective"),
        ("2024-01-01", "shadowed"),
        ("2020-01-01", "older"),
    )

    values = parameter.parameter_values

    assert len(values) == 2
    assert values[0].value == "older"
    assert values[0].end_date == datetime(2023, 12, 31)
    assert values[1].value == "effective"
    assert values[1].end_date is None


def test__year_zero_core_value__then_existing_safe_date_normalization_is_preserved():
    parameter = _parameter_with_core_values(
        ("2020-01-01", 20),
        ("0000-01-01", 10),
    )

    values = parameter.parameter_values

    assert values[0].start_date == datetime(1, 1, 1)
    assert values[0].end_date == datetime(2019, 12, 31)
    assert values[1].start_date == datetime(2020, 1, 1)
    assert values[1].end_date is None


def test__repeated_access__then_parameter_history_is_cached():
    parameter = _parameter_with_core_values(("2024-01-01", 10))

    first = parameter.parameter_values

    assert parameter.parameter_values is first


def test__explicit_parameter_values__then_setter_override_is_preserved():
    parameter = _parameter_with_core_values(("2024-01-01", 10))
    override = [
        ParameterValue(
            parameter=parameter,
            value=99,
            start_date=datetime(2030, 1, 1),
            end_date=None,
        )
    ]

    parameter.parameter_values = override

    assert parameter.parameter_values is override


def test__parameter_without_core_reference__then_history_is_empty():
    parameter = Parameter.model_construct(
        name="gov.test.value",
        tax_benefit_model_version=None,
    )
    parameter._core_param = None
    parameter._parameter_values = None

    values = parameter.parameter_values

    assert values == []
    assert parameter.parameter_values is values
