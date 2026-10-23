"""Measure the actual dense H5 surface, never an older model's inventory."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from policyengine.provenance.manifest import RegionalInputArtifactEvidence

MODEL_VERSION = "2.147.2"
URI = (
    "hf://dataset/policyengine/regional@dense-cut/releases/dense/release_manifest.json"
)
LIMITATION = "Reviewed dense VAT limitation; dashboard holds a VAT limit"
DEFAULTS = ["local_bus_uncapped_single_fare", "salary_sacrifice_returned_to_income"]


class FakeSimulation:
    def __init__(self):
        self.move_values("employment_income", "employment_income_before_lsr")

    def move_values(self, source, target):
        pass


class FakeVariable:
    def __init__(self, is_input):
        self.is_input = is_input

    def is_input_variable(self):
        return self.is_input


class FakeCountryTaxBenefitSystem:
    def __init__(self):
        inputs = {
            "employment_income_before_lsr",
            "household_weight",
            "benunit_id",
            *DEFAULTS,
        }
        self.variables = {
            name: FakeVariable(name in inputs)
            for name in sorted(inputs | {"employment_income"})
        }


def _module():
    return importlib.import_module("policyengine.provenance.regional_input_surface")


def _h5(path, *, periods=None, fmt="fixed", missing=None):
    with pd.HDFStore(path, mode="w") as store:
        if periods is None:
            store.put("time_period", pd.Series([2025]))
            periods = {None: True}
        for period, has_income in periods.items():
            for entity, columns in {
                "person": {"employment_income": [1.0]} if has_income else {},
                "benunit": {"benunit_id": [0]},
                "household": {"household_weight": [1.0]},
            }.items():
                if (period, entity) == missing:
                    continue
                key = entity if period is None else f"{entity}/{period}"
                if not columns:
                    columns = {"benunit_id": [0]}
                store.put(key, pd.DataFrame(columns), format=fmt)
    return path


def _response(artifact_paths):
    payload = {
        "schema_version": 1,
        "data_package": {"name": "microcosm-data", "version": "1"},
        "dataset_role": "non_default_local_area",
        "is_default": False,
        "default_datasets": {},
        "artifacts": {
            name: {
                "kind": "microdata",
                "path": f"{name}.h5",
                "repo_id": "policyengine/regional",
                "revision": "dense-cut",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for name, path in artifact_paths.items()
        },
    }
    response = MagicMock(status_code=200)
    response.content = json.dumps(payload, indent=2).encode()
    return response


@pytest.fixture
def model(monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "version", lambda name: MODEL_VERSION)
    monkeypatch.setitem(
        sys.modules,
        "policyengine_uk",
        SimpleNamespace(
            CountryTaxBenefitSystem=FakeCountryTaxBenefitSystem,
            Simulation=FakeSimulation,
        ),
    )
    return module


def _measure(module, paths, response=None, **kwargs):
    response = _response(paths) if response is None else response
    with patch(
        "policyengine.provenance.certification.requests.get", return_value=response
    ):
        return module.measure_regional_input_surface(
            URI,
            paths,
            MODEL_VERSION,
            "Budget operator",
            [LIMITATION],
            **kwargs,
        )


@pytest.mark.parametrize("fmt", ["fixed", "table"])
def test_actual_h5_columns_and_aliases_produce_bound_audit(tmp_path, model, fmt):
    paths = {"dense": _h5(tmp_path / "dense.h5", fmt=fmt)}
    response = _response(paths)
    result = _measure(model, paths, response)
    assert result.model_version == MODEL_VERSION
    assert result.model_package == "policyengine-uk"
    assert result.regional_manifest_uri == URI
    assert (
        result.regional_manifest_sha256 == hashlib.sha256(response.content).hexdigest()
    )
    artifact = result.artifacts["dense"]
    assert artifact.sha256 == hashlib.sha256(paths["dense"].read_bytes()).hexdigest()
    assert artifact.repo_type == "dataset"
    assert artifact.columns == ["benunit_id", "employment_income", "household_weight"]
    assert artifact.columns_by_period == {"2025": artifact.columns}
    assert result.input_aliases == {"employment_income": "employment_income_before_lsr"}
    assert result.defaulted_inputs == DEFAULTS
    assert result.dropped_columns == []
    assert result.limitations == [LIMITATION]
    assert result.audited_by == "Budget operator"


def test_a_default_in_one_period_is_not_hidden_by_another_period(tmp_path, model):
    paths = {"dense": _h5(tmp_path / "dense.h5", periods={"2025": True, "2026": False})}
    result = _measure(model, paths)
    assert result.defaulted_inputs == [
        "employment_income_before_lsr",
        *DEFAULTS,
    ]
    assert "employment_income" in result.artifacts["dense"].columns_by_period["2025"]
    assert (
        "employment_income" not in result.artifacts["dense"].columns_by_period["2026"]
    )


@pytest.mark.parametrize("entity", ["person", "benunit", "household"])
def test_each_period_requires_every_entity(tmp_path, model, entity):
    paths = {
        "dense": _h5(
            tmp_path / "dense.h5",
            periods={"2025": True, "2026": True},
            missing=("2026", entity),
        )
    }
    with pytest.raises(ValueError, match="2026|entity"):
        _measure(model, paths)


def test_single_year_layout_requires_a_time_period(tmp_path, model):
    path = _h5(tmp_path / "dense.h5")
    with pd.HDFStore(path, mode="a") as store:
        store.remove("time_period")
    with pytest.raises(ValueError, match="time_period|period"):
        _measure(model, {"dense": path})


def test_extra_metadata_is_not_mistaken_for_a_model_column(tmp_path, model):
    path = _h5(tmp_path / "dense.h5")
    with pd.HDFStore(path, mode="a") as store:
        store.put("metadata", pd.Series(["producer build notes"]))
    assert _measure(model, {"dense": path}).dropped_columns == []


def test_an_actual_dropped_column_blocks_audit(tmp_path, model):
    path = _h5(tmp_path / "dense.h5")
    with pd.HDFStore(path, mode="a") as store:
        store.put("person", pd.DataFrame({"removed_column": [1]}))
    with pytest.raises(ValueError, match="[Dd]ropped|removed_column"):
        _measure(model, {"dense": path})


def test_installed_model_must_be_the_requested_exact_version(
    tmp_path, model, monkeypatch
):
    monkeypatch.setattr(model, "version", lambda name: "2.146.4")
    paths = {"dense": _h5(tmp_path / "dense.h5")}
    with pytest.raises(ValueError, match="2.147.2|2.146.4"):
        _measure(model, paths)


def test_artifact_bytes_must_match_the_manifest(tmp_path, model):
    paths = {"dense": _h5(tmp_path / "dense.h5")}
    response = _response(paths)
    payload = json.loads(response.content)
    payload["artifacts"]["dense"]["sha256"] = "0" * 64
    response.content = json.dumps(payload).encode()
    with pytest.raises(ValueError, match="sha256|[Hh]ash|bytes"):
        _measure(model, paths, response)


def test_file_changing_during_metadata_read_refuses(tmp_path, model, monkeypatch):
    paths = {"dense": _h5(tmp_path / "dense.h5")}
    response = _response(paths)
    original = pd.HDFStore.select
    mutated = False

    def select_and_modify(store, *args, **kwargs):
        nonlocal mutated
        result = original(store, *args, **kwargs)
        if not mutated and args[0] != "/time_period":
            with paths["dense"].open("ab") as file:
                file.write(b"changed while inspecting metadata")
            mutated = True
        return result

    monkeypatch.setattr(pd.HDFStore, "select", select_and_modify)
    with pytest.raises(ValueError, match="chang|sha256|[Hh]ash|bytes"):
        _measure(model, paths, response)


@pytest.mark.parametrize("names", [[], ["other"], ["dense", "other"]])
def test_every_routed_h5_requires_exactly_one_supplied_path(tmp_path, model, names):
    path = _h5(tmp_path / "dense.h5")
    response = _response({"dense": path})
    with pytest.raises(ValueError, match="artifact|[Hh]5"):
        _measure(model, {name: path for name in names}, response)


def test_comparison_uses_each_artifact_and_every_period():
    module = _module()
    artifact = RegionalInputArtifactEvidence(
        repo_id="r",
        path="dense.h5",
        revision="cut",
        sha256="a" * 64,
        columns=["income", "weight"],
        columns_by_period={"2025": ["income", "weight"], "2026": ["weight"]},
    )
    result = module.compare_input_surface(
        {"dense": artifact},
        ["income", "income_reported", "weight", "new_input"],
        ["income_reported", "weight", "new_input"],
        {"income": "income_reported"},
    )
    assert result == {
        "dropped_columns": [],
        "defaulted_inputs": ["income_reported", "new_input"],
    }


def test_comparison_refuses_a_period_union_that_hides_columns():
    module = _module()
    artifact = RegionalInputArtifactEvidence(
        repo_id="r",
        path="dense.h5",
        revision="cut",
        sha256="a" * 64,
        columns=["weight"],
        columns_by_period={"2025": ["weight", "removed"]},
    )
    with pytest.raises(ValueError, match="columns|union|period"):
        module.compare_input_surface({"dense": artifact}, ["weight"], ["weight"])


def test_conditional_alias_cannot_silently_claim_a_supplied_input(
    tmp_path, model, monkeypatch
):
    class ConditionalSimulation:
        def __init__(self):
            if self.condition:
                self.move_values("employment_income", "employment_income_before_lsr")

    monkeypatch.setattr(
        sys.modules["policyengine_uk"], "Simulation", ConditionalSimulation
    )
    paths = {"dense": _h5(tmp_path / "dense.h5")}
    with pytest.raises(ValueError, match="alias|move_values|conditional"):
        _measure(model, paths)


def test_audit_cli_writes_pydantic_evidence_json(tmp_path, model, monkeypatch):
    script_path = (
        Path(__file__).parents[1] / "scripts" / "audit_regional_input_surface.py"
    )
    spec = importlib.util.spec_from_file_location(
        "audit_regional_input_surface", script_path
    )
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    path = _h5(tmp_path / "dense.h5")
    result = _measure(model, {"dense": path})
    captured = {}

    def measure(**kwargs):
        captured.update(kwargs)
        return result

    monkeypatch.setattr(script, "measure_regional_input_surface", measure)
    output = tmp_path / "evidence.json"
    assert (
        script.main(
            [
                "--regional-manifest-uri",
                URI,
                "--artifact",
                f"dense={path}",
                "--model-version",
                MODEL_VERSION,
                "--audited-by",
                "Budget operator",
                "--limitation",
                LIMITATION,
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert captured["artifact_paths"] == {"dense": path}
    assert captured["limitations"] == [LIMITATION]
    assert json.loads(output.read_text()) == result.model_dump(mode="json")
