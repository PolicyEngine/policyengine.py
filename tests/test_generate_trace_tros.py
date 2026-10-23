"""Repository TRO generation must validate complete payloads before any writes."""

import json
import sys
from importlib.resources import files
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from policyengine.provenance.manifest import DataReleaseManifestUnavailableError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_trace_tros as generator  # noqa: E402


@pytest.fixture
def schema():
    return json.loads(
        files("policyengine")
        .joinpath("data", "schemas", "trace_tro.schema.json")
        .read_text()
    )


@pytest.fixture
def offline_generator(monkeypatch):
    """Use actual bundled US/UK pins, exercising the supported offline fallback."""

    def unavailable(country):
        raise DataReleaseManifestUnavailableError("No network in this test")

    monkeypatch.setattr(generator, "get_data_release_manifest", unavailable)
    return generator


def test_real_generated_country_payloads_validate(offline_generator, schema):
    payloads = offline_generator.generated_tros()
    assert {path.name for path, _ in payloads} == {
        "us.trace.tro.jsonld",
        "uk.trace.tro.jsonld",
    }
    for _, payload in payloads:
        tro = json.loads(payload)
        assert (
            tro["@graph"][0]["trov:hasPerformance"]["pe:emittedIn"]
            == "repository-bundle"
        )
        Draft202012Validator(schema).validate(tro)


@pytest.mark.parametrize("country", ["us", "uk"])
def test_packaged_repository_tros_validate(country, schema):
    payload = json.loads(
        files("policyengine")
        .joinpath("data", "bundle", f"{country}.trace.tro.jsonld")
        .read_text()
    )
    Draft202012Validator(schema).validate(payload)


def test_unknown_emission_still_rejected(offline_generator, schema):
    payload = json.loads(offline_generator.generated_tros()[0][1])
    payload["@graph"][0]["trov:hasPerformance"]["pe:emittedIn"] = "unknown-emission"
    with pytest.raises(ValidationError, match="unknown-emission"):
        Draft202012Validator(schema).validate(payload)


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("defect", ["emission", "composition"])
def test_last_serialized_country_failure_preserves_all_outputs(
    offline_generator, monkeypatch, tmp_path, existing, defect
):
    output = tmp_path / "bundle"
    before = {}
    if existing:
        output.mkdir()
        for country in ["uk", "us"]:
            path = output / f"{country}.trace.tro.jsonld"
            path.write_bytes(f"preserve original {country}".encode())
            before[path.name] = path.read_bytes()
    monkeypatch.setattr(offline_generator, "BUNDLE_TRO_DIR", output)
    serialize = offline_generator.serialize_trace_tro
    serialized = []

    def corrupt_last(tro):
        # Corrupt the serialized US output after the valid UK payload is prepared.
        payload = json.loads(serialize(tro))
        serialized.append(payload)
        if len(serialized) == 2:
            node = payload["@graph"][0]
            if defect == "emission":
                node["trov:hasPerformance"]["pe:emittedIn"] = "unknown-emission"
            else:
                del node["trov:hasComposition"]
        return json.dumps(payload).encode()

    monkeypatch.setattr(offline_generator, "serialize_trace_tro", corrupt_last)
    with pytest.raises(ValidationError):
        offline_generator.regenerate_all()
    assert len(serialized) == 2
    if existing:
        assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    else:
        assert not output.exists()


def test_dry_generation_has_no_writes_then_regeneration_writes_all(
    offline_generator, monkeypatch, tmp_path, schema
):
    output = tmp_path / "new-bundle"
    monkeypatch.setattr(offline_generator, "BUNDLE_TRO_DIR", output)
    expected = dict(offline_generator.generated_tros())
    assert not output.exists()
    written, regressions = offline_generator.regenerate_all()
    assert set(written) == set(expected)
    assert regressions == []
    for path in written:
        assert path.read_bytes() == expected[path]
        Draft202012Validator(schema).validate(json.loads(path.read_bytes()))
