"""Tests for the entities and basic inputs a model version publishes."""

import importlib
import json
from types import SimpleNamespace

import pytest

from policyengine.core import Entity, TaxBenefitModel, TaxBenefitModelVersion
from policyengine.tax_benefit_models.common.model_version import (
    MicrosimulationModelVersion,
)


def _model_version() -> TaxBenefitModelVersion:
    return TaxBenefitModelVersion(
        id="test@1",
        model=TaxBenefitModel(id="test", name="Test"),
        version="1",
    )


@pytest.fixture(params=["uk", "us"])
def country(request) -> SimpleNamespace:
    """The country's published model version and its core tax-benefit system.

    Skips when the country package is not installed. The model is imported
    here, after that check, because the country module defines it only when
    the package is installed.
    """
    country_id = request.param
    country_system = pytest.importorskip(f"policyengine_{country_id}.system").system
    country_module = importlib.import_module(
        f"policyengine.tax_benefit_models.{country_id}"
    )
    return SimpleNamespace(
        id=country_id,
        model=getattr(country_module, f"{country_id}_latest"),
        system=country_system,
    )


def _core_entity(key: str, plural: str, is_person: bool) -> SimpleNamespace:
    return SimpleNamespace(
        key=key,
        plural=plural,
        is_person=is_person,
        label=key.title(),
        doc=f"The {key} entity.",
    )


def test_populate_entities_records_key_plural_and_person_flag_in_order():
    model = _model_version()
    system = SimpleNamespace(
        entities=[
            _core_entity("person", "people", True),
            _core_entity("benunit", "benunits", False),
            _core_entity("household", "households", False),
        ],
        basic_inputs=["region", "employment_income", "age"],
    )

    MicrosimulationModelVersion._populate_entities(model, system)

    assert model.entities == [
        Entity(key="person", plural="people", is_person=True),
        Entity(key="benunit", plural="benunits", is_person=False),
        Entity(key="household", plural="households", is_person=False),
    ]
    assert model.basic_inputs == ["region", "employment_income", "age"]


def test_populate_entities_accepts_a_country_model_without_basic_inputs():
    model = _model_version()
    system = SimpleNamespace(
        entities=[_core_entity("person", "people", True)],
        basic_inputs=None,
    )

    MicrosimulationModelVersion._populate_entities(model, system)

    assert model.basic_inputs == []


def test_model_version_defaults_to_no_entities_or_basic_inputs():
    model = _model_version()

    assert model.entities == []
    assert model.basic_inputs == []


def test_entities_and_basic_inputs_round_trip_through_json():
    model = _model_version()
    model.entities = [Entity(key="person", plural="people", is_person=True)]
    model.basic_inputs = ["age"]

    payload = json.loads(model.model_dump_json(include={"entities", "basic_inputs"}))

    assert payload == {
        "entities": [{"key": "person", "plural": "people", "is_person": True}],
        "basic_inputs": ["age"],
    }
    restored_entities = [
        Entity.model_validate(entity) for entity in payload["entities"]
    ]
    assert restored_entities == model.entities


def test_country_models_publish_their_entities_and_basic_inputs(country):
    model = country.model
    country_system = country.system

    assert [
        (entity.key, entity.plural, entity.is_person) for entity in model.entities
    ] == [
        (entity.key, entity.plural, bool(entity.is_person))
        for entity in country_system.entities
    ]
    assert [entity.key for entity in model.entities if entity.is_person] == ["person"]
    assert model.basic_inputs == list(country_system.basic_inputs)
    assert model.basic_inputs, "Each country package declares basic inputs"
    assert all(name in model.variables_by_name for name in model.basic_inputs)
    entity_keys = {entity.key for entity in model.entities}
    assert {variable.entity for variable in model.variables} <= entity_keys


# Read from the country packages pinned in pyproject.toml, independently of
# how the model version derives them.
PINNED_ENTITIES = {
    "uk": [
        ("person", "people", True),
        ("benunit", "benunits", False),
        ("household", "households", False),
    ],
    "us": [
        ("household", "households", False),
        ("spm_unit", "spm_units", False),
        ("family", "families", False),
        ("tax_unit", "tax_units", False),
        ("marital_unit", "marital_units", False),
        ("person", "people", True),
    ],
}


def test_country_models_publish_their_pinned_entities(country):
    assert [
        (entity.key, entity.plural, entity.is_person)
        for entity in country.model.entities
    ] == PINNED_ENTITIES[country.id]
    assert {"employment_income", "age"} <= set(country.model.basic_inputs)
