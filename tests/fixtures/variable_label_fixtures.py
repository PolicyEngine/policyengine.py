"""Fixtures for variable label tests."""

from unittest.mock import MagicMock


def create_mock_openfisca_variable(
    name: str,
    label: str | None = None,
    entity_key: str = "person",
    documentation: str | None = None,
    value_type: type = float,
    default_value=0,
) -> MagicMock:
    """Create a mock OpenFisca variable object.

    Mimics the attributes of an OpenFisca Variable class as seen by
    ``getattr(var_obj, "label", None)`` in the model loading code.
    """
    var = MagicMock()
    var.name = name
    var.documentation = documentation
    var.value_type = value_type
    var.default_value = default_value

    entity = MagicMock()
    entity.key = entity_key
    var.entity = entity

    # OpenFisca variables expose label as a class attribute.
    # If label is None we delete the attribute so getattr falls back.
    if label is not None:
        var.label = label
    else:
        del var.label

    return var


# Pre-built fixtures
VAR_WITH_LABEL = create_mock_openfisca_variable(
    name="employment_income",
    label="Employment income",
)

VAR_WITHOUT_LABEL = create_mock_openfisca_variable(
    name="age",
    label=None,
)

VAR_WITH_EMPTY_LABEL = create_mock_openfisca_variable(
    name="household_weight",
    label="",
)
