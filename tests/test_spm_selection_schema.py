"""Public schemas must let clients leave bundle-dependent settings omitted."""

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel

from policyengine.core.spm import SPMSelection


class SelectionEnvelope(BaseModel):
    spm: SPMSelection | None = None


@pytest.mark.parametrize("mode", ["validation", "serialization"])
@pytest.mark.parametrize("nested", [False, True])
def test_spm_schema_keeps_typed_optional_fields_without_client_defaults(mode, nested):
    schema = (
        SelectionEnvelope.model_json_schema(mode=mode)["$defs"]["SPMSelection"]
        if nested
        else SPMSelection.model_json_schema(mode=mode)
    )
    assert set(schema["properties"]) == set(SPMSelection.model_fields)
    assert schema.get("required", []) == []
    assert schema["additionalProperties"] is False
    for field in schema["properties"].values():
        assert "default" not in field
    assert schema["properties"]["geography_kind"]["enum"] == [
        "county",
        "national",
        "metro",
    ]
    assert schema["properties"]["county_vintage"]["pattern"] == r"^[0-9]{4}$"
    validator = Draft202012Validator(schema)
    validator.validate({})
    validator.validate({"scenario": "zero_real"})
    validator.validate({"geography_kind": "county", "as_of": None})
    assert not validator.is_valid({"geography_kind": "state"})
    assert not validator.is_valid({"provider": "/tmp/unpinned.json"})


def test_schema_inheritance_contract_preserves_python_runtime_defaults():
    selection = SPMSelection()
    assert selection.geography_kind == "county"
    assert selection.county_vintage == "2020"
    assert selection.model_dump() == {}
    assert selection.model_dump_json() == "{}"
    explicit = SPMSelection(geography_kind="county", county_vintage="2020", as_of=None)
    assert explicit.model_dump() == {
        "geography_kind": "county",
        "county_vintage": "2020",
        "as_of": None,
    }
