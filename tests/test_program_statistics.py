"""Unit tests for the shared program-statistics helpers.

These exercise :func:`validate_program_statistics_config` directly with
lightweight fakes so the country-agnostic validation logic (and, in particular,
the ``country_label`` threaded into the error message) is covered without
building a full country simulation.
"""

import pytest

from policyengine.outputs.program_statistics import (
    validate_program_statistics_config,
)


class _FakeVariable:
    def __init__(self, entity: str):
        self.entity = entity


class _FakeModelVersion:
    def __init__(
        self,
        variable_entities: dict[str, str],
        resolved_entity_variables: dict[str, list[str]],
    ):
        self._variable_entities = variable_entities
        self._resolved_entity_variables = resolved_entity_variables

    def get_variable(self, name: str) -> _FakeVariable:
        if name not in self._variable_entities:
            raise ValueError(name)
        return _FakeVariable(self._variable_entities[name])

    def resolve_entity_variables(self, simulation) -> dict[str, list[str]]:
        return self._resolved_entity_variables


class _FakeSimulation:
    def __init__(self, model_version: _FakeModelVersion):
        self.tax_benefit_model_version = model_version


def _simulation(
    variable_entities: dict[str, str],
    resolved_entity_variables: dict[str, list[str]],
) -> _FakeSimulation:
    return _FakeSimulation(
        _FakeModelVersion(variable_entities, resolved_entity_variables)
    )


def test_validate_config_passes_when_all_present():
    programs = {"income_tax": {"is_tax": True}}
    simulation = _simulation(
        {"income_tax": "tax_unit"},
        {"tax_unit": ["income_tax"]},
    )

    # Should not raise for either simulation.
    validate_program_statistics_config(
        programs,
        simulation,
        simulation,
        "Ruritania",
    )


def test_validate_config_missing_variable_reports_label():
    programs = {"income_tax": {"is_tax": True}}
    simulation = _simulation({}, {})

    with pytest.raises(ValueError) as exc_info:
        validate_program_statistics_config(
            programs,
            simulation,
            simulation,
            "Ruritania",
        )

    message = str(exc_info.value)
    assert message.startswith("Ruritania program statistics config is invalid")
    assert "income_tax" in message


def test_validate_config_unmaterialized_variable_reports_label():
    programs = {"income_tax": {"is_tax": True}}
    simulation = _simulation(
        {"income_tax": "tax_unit"},
        {"tax_unit": []},
    )

    with pytest.raises(ValueError) as exc_info:
        validate_program_statistics_config(
            programs,
            simulation,
            simulation,
            "Ruritania",
        )

    message = str(exc_info.value)
    assert message.startswith("Ruritania program statistics config is invalid")
    assert "income_tax on tax_unit" in message
