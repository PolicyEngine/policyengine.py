"""Fixtures for parametric reforms tests."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from policyengine.core import Parameter, ParameterValue


def create_mock_parameter(
    name: str = "gov.test.param",
    label: str = "Test Parameter",
) -> Parameter:
    """Create a mock Parameter for testing."""
    param = MagicMock(spec=Parameter)
    param.name = name
    param.label = label
    return param


def create_parameter_value(
    parameter: Parameter,
    value: float,
    start_date: date,
    end_date: date | None = None,
) -> ParameterValue:
    """Create a ParameterValue for testing."""
    return ParameterValue(
        parameter=parameter,
        value=value,
        start_date=start_date,
        end_date=end_date,
    )


# Pre-built fixtures for common test scenarios

MOCK_PARAM_SINGLE = create_mock_parameter(
    name="gov.irs.deductions.standard.amount.SINGLE",
    label="Standard Deduction (Single)",
)

MOCK_PARAM_JOINT = create_mock_parameter(
    name="gov.irs.deductions.standard.amount.JOINT",
    label="Standard Deduction (Joint)",
)

MOCK_PARAM_TAX_RATE = create_mock_parameter(
    name="gov.irs.income_tax.rates.bracket_1.rate",
    label="Tax Rate Bracket 1",
)

# Single parameter value
SINGLE_PARAM_VALUE = create_parameter_value(
    parameter=MOCK_PARAM_SINGLE,
    value=29200,
    start_date=date(2024, 1, 1),
)

# Parameter value with end date
PARAM_VALUE_WITH_END_DATE = create_parameter_value(
    parameter=MOCK_PARAM_SINGLE,
    value=29200,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 31),
)

# Multiple parameter values for the same parameter (different periods)
MULTI_PERIOD_PARAM_VALUES = [
    create_parameter_value(
        parameter=MOCK_PARAM_SINGLE,
        value=29200,
        start_date=date(2024, 1, 1),
    ),
    create_parameter_value(
        parameter=MOCK_PARAM_SINGLE,
        value=30000,
        start_date=date(2025, 1, 1),
    ),
]

# Multiple different parameters
MULTIPLE_DIFFERENT_PARAMS = [
    create_parameter_value(
        parameter=MOCK_PARAM_SINGLE,
        value=29200,
        start_date=date(2024, 1, 1),
    ),
    create_parameter_value(
        parameter=MOCK_PARAM_JOINT,
        value=58400,
        start_date=date(2024, 1, 1),
    ),
    create_parameter_value(
        parameter=MOCK_PARAM_TAX_RATE,
        value=0.10,
        start_date=date(2024, 1, 1),
    ),
]


@pytest.fixture
def mock_param_single():
    """Pytest fixture for a mock single filer parameter."""
    return MOCK_PARAM_SINGLE


@pytest.fixture
def mock_param_joint():
    """Pytest fixture for a mock joint filer parameter."""
    return MOCK_PARAM_JOINT


@pytest.fixture
def single_param_value():
    """Pytest fixture for a single parameter value."""
    return SINGLE_PARAM_VALUE


@pytest.fixture
def param_value_with_end_date():
    """Pytest fixture for a parameter value with end date."""
    return PARAM_VALUE_WITH_END_DATE


@pytest.fixture
def multi_period_param_values():
    """Pytest fixture for multiple values of the same parameter."""
    return MULTI_PERIOD_PARAM_VALUES


@pytest.fixture
def multiple_different_params():
    """Pytest fixture for multiple different parameters."""
    return MULTIPLE_DIFFERENT_PARAMS
