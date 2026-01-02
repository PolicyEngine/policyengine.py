"""Fixtures for parameter_labels utility tests."""

from enum import Enum
from typing import Any
from unittest.mock import MagicMock


class MockFilingStatus(Enum):
    """Mock filing status enum for testing breakdown labels."""

    SINGLE = "Single"
    JOINT = "Joint"
    HEAD_OF_HOUSEHOLD = "Head of household"


class MockStateCode(Enum):
    """Mock state code enum where key equals value."""

    CA = "CA"
    TX = "TX"
    NY = "NY"


def create_mock_parameter(
    name: str,
    label: str | None = None,
    parent: Any = None,
) -> MagicMock:
    """Create a mock CoreParameter object."""
    param = MagicMock()
    param.name = name
    param.metadata = {"label": label} if label else {}
    param.parent = parent
    return param


def create_mock_parent_node(
    name: str,
    label: str | None = None,
    breakdown: list[str] | None = None,
) -> MagicMock:
    """Create a mock parent ParameterNode with optional breakdown metadata."""
    parent = MagicMock()
    parent.name = name
    parent.metadata = {}
    if label:
        parent.metadata["label"] = label
    if breakdown:
        parent.metadata["breakdown"] = breakdown
    return parent


def create_mock_scale(
    name: str,
    label: str | None = None,
    scale_type: str | None = None,
) -> MagicMock:
    """Create a mock ParameterScale object."""
    scale = MagicMock()
    scale.name = name
    scale.metadata = {}
    if label:
        scale.metadata["label"] = label
    if scale_type:
        scale.metadata["type"] = scale_type
    return scale


def create_mock_variable(
    name: str,
    possible_values: type[Enum] | None = None,
) -> MagicMock:
    """Create a mock Variable object with optional enum values."""
    var = MagicMock()
    var.name = name
    if possible_values:
        var.possible_values = possible_values
    else:
        var.possible_values = None
    return var


def create_mock_system(
    variables: dict[str, MagicMock] | None = None,
    scales: list[MagicMock] | None = None,
) -> MagicMock:
    """Create a mock tax-benefit system."""
    system = MagicMock()
    system.variables = variables or {}

    descendants = list(scales) if scales else []
    system.parameters.get_descendants.return_value = descendants

    return system


# Pre-built fixtures for common test scenarios

PARAM_WITH_EXPLICIT_LABEL = create_mock_parameter(
    name="gov.tax.rate",
    label="Tax rate",
)

PARAM_WITHOUT_LABEL_NO_PARENT = create_mock_parameter(
    name="gov.tax.rate",
    label=None,
    parent=None,
)

PARENT_WITH_BREAKDOWN_AND_LABEL = create_mock_parent_node(
    name="gov.exemptions.personal",
    label="Personal exemption amount",
    breakdown=["filing_status"],
)

PARENT_WITH_BREAKDOWN_NO_LABEL = create_mock_parent_node(
    name="gov.exemptions.personal",
    label=None,
    breakdown=["filing_status"],
)

PARENT_WITHOUT_BREAKDOWN = create_mock_parent_node(
    name="gov.exemptions.personal",
    label="Personal exemption amount",
    breakdown=None,
)

SCALE_WITH_LABEL_MARGINAL = create_mock_scale(
    name="gov.tax.rates",
    label="Income tax rate",
    scale_type="marginal_rate",
)

SCALE_WITH_LABEL_SINGLE_AMOUNT = create_mock_scale(
    name="gov.tax.amounts",
    label="Tax amount",
    scale_type="single_amount",
)

SCALE_WITHOUT_LABEL = create_mock_scale(
    name="gov.tax.rates",
    label=None,
    scale_type="marginal_rate",
)

VARIABLE_WITH_FILING_STATUS_ENUM = create_mock_variable(
    name="filing_status",
    possible_values=MockFilingStatus,
)

VARIABLE_WITH_STATE_CODE_ENUM = create_mock_variable(
    name="state_code",
    possible_values=MockStateCode,
)

VARIABLE_WITHOUT_ENUM = create_mock_variable(
    name="age",
    possible_values=None,
)
