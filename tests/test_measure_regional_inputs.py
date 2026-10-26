"""Measure the actual dense H5 surface against its build model and the target."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from policyengine.provenance.manifest import RegionalInputArtifactEvidence

MODEL_VERSION = "2.147.2"
BUILD_VERSION = "2.132.6"
BUILD_CORE_VERSION = "3.33.3"
BUILT_AT = "2026-10-19T02:07:51.099627+00:00"
#: BUILT_AT in UTC, rounded up to the second: the probe's --exclude-newer.
BUILD_CUTOFF = "2026-10-19T02:07:52Z"
URI = (
    "hf://dataset/policyengine/regional@dense-cut/releases/dense/release_manifest.json"
)
LIMITATION = "Reviewed dense VAT limitation; dashboard holds a VAT limit"
DEFAULTS = ["local_bus_uncapped_single_fare", "salary_sacrifice_returned_to_income"]
#: An input of both models that the files never store: not a change.
ABSENT_UNDER_BOTH = "legacy_default_input"
#: A build-model variable that the target model no longer defines.
REMOVED = "removed_in_target"
#: A Microcosm column that neither model defines.
AREA_CODE = "constituency_code_oa"
BUILD_INPUTS = [
    "benunit_id",
    "employment_income_before_lsr",
    "household_weight",
    ABSENT_UNDER_BOTH,
    REMOVED,
]
BUILD_VARIABLES = sorted([*BUILD_INPUTS, "employment_income"])
PERSON = ("employment_income",)


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
            ABSENT_UNDER_BOTH,
            *DEFAULTS,
        }
        self.variables = {
            name: FakeVariable(name in inputs)
            for name in sorted(inputs | {"employment_income"})
        }


class FakeRunner:
    """Stands in for ``uv run`` reading the build model, so nothing installs."""

    def __init__(self, **surface):
        self.surface = {
            "model_version": BUILD_VERSION,
            "core_version": BUILD_CORE_VERSION,
            "variables": BUILD_VARIABLES,
            "inputs": BUILD_INPUTS,
        } | surface
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        stdout = "Installed 40 packages\n" + json.dumps(self.surface) + "\n"
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")


def _module():
    return importlib.import_module("policyengine.provenance.regional_input_surface")


def _h5(path, *, person=PERSON, periods=None, fmt="fixed", missing=None):
    """Write UK entity tables: one year, or each period's person columns."""
    with pd.HDFStore(path, mode="w") as store:
        if periods is None:
            store.put("time_period", pd.Series([2025]))
            periods = {None: person}
        for period, person_columns in periods.items():
            for entity, columns in {
                "person": person_columns or ("benunit_id",),
                "benunit": ("benunit_id",),
                "household": ("household_weight",),
            }.items():
                if (period, entity) == missing:
                    continue
                key = entity if period is None else f"{entity}/{period}"
                frame = pd.DataFrame({column: [1.0] for column in columns})
                store.put(key, frame, format=fmt)
    return path


def _response(artifact_paths, build=None):
    payload = {
        "schema_version": 1,
        "data_package": {"name": "microcosm-data", "version": "1"},
        "dataset_role": "non_default_local_area",
        "is_default": False,
        "default_datasets": {},
        "build": {
            "built_at": BUILT_AT,
            "built_with_model_package": {
                "name": "policyengine-uk",
                "version": BUILD_VERSION,
            },
            "built_with_core_package": {
                "name": "policyengine-core",
                "version": BUILD_CORE_VERSION,
            },
        }
        if build is None
        else build,
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


def _measure(module, paths, response=None, run=None, **kwargs):
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
            run=FakeRunner() if run is None else run,
            **kwargs,
        )


def _artifact(columns_by_period):
    return RegionalInputArtifactEvidence(
        repo_id="r",
        path="dense.h5",
        revision="cut",
        sha256="a" * 64,
        columns=sorted({column for c in columns_by_period.values() for column in c}),
        columns_by_period=columns_by_period,
    )


@pytest.mark.parametrize("fmt", ["fixed", "table"])
def test_actual_h5_columns_and_aliases_produce_bound_audit(tmp_path, model, fmt):
    paths = {"dense": _h5(tmp_path / "dense.h5", fmt=fmt)}
    response = _response(paths)
    result = _measure(model, paths, response)
    assert result.schema_version == 2
    assert result.model_version == MODEL_VERSION
    assert result.model_package == "policyengine-uk"
    assert result.build_model_version == BUILD_VERSION
    assert result.build_core_version == BUILD_CORE_VERSION
    assert result.build_model_variables == BUILD_VARIABLES
    assert result.build_model_inputs == BUILD_INPUTS
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
    assert result.never_modelled_columns == []
    assert result.limitations == [LIMITATION]
    assert result.audited_by == "Budget operator"


def test_a_default_in_one_period_is_not_hidden_by_another_period(tmp_path, model):
    paths = {
        "dense": _h5(
            tmp_path / "dense.h5",
            periods={
                "2025": (*PERSON, "salary_sacrifice_returned_to_income"),
                "2026": PERSON,
            },
        )
    }
    result = _measure(model, paths)
    assert result.defaulted_inputs == DEFAULTS
    periods = result.artifacts["dense"].columns_by_period
    assert "salary_sacrifice_returned_to_income" in periods["2025"]
    assert "salary_sacrifice_returned_to_income" not in periods["2026"]


@pytest.mark.parametrize("entity", ["person", "benunit", "household"])
def test_each_period_requires_every_entity(tmp_path, model, entity):
    paths = {
        "dense": _h5(
            tmp_path / "dense.h5",
            periods={"2025": PERSON, "2026": PERSON},
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
    result = _measure(model, {"dense": path})
    assert result.dropped_columns == []
    assert result.never_modelled_columns == []


def test_a_column_neither_model_defines_is_recorded_not_refused(tmp_path, model):
    path = _h5(tmp_path / "dense.h5", person=(*PERSON, AREA_CODE))
    result = _measure(model, {"dense": path})
    assert result.never_modelled_columns == [AREA_CODE]
    assert result.dropped_columns == []
    assert AREA_CODE in result.artifacts["dense"].columns


def test_a_column_the_build_model_defines_and_the_target_does_not_blocks_audit(
    tmp_path, model
):
    path = _h5(tmp_path / "dense.h5", person=(*PERSON, REMOVED))
    with pytest.raises(ValueError, match=f"dropped.*{REMOVED}"):
        _measure(model, {"dense": path})


def test_an_input_absent_under_both_models_is_not_reported(tmp_path, model):
    paths = {"dense": _h5(tmp_path / "dense.h5")}
    assert ABSENT_UNDER_BOTH not in _measure(model, paths).defaulted_inputs
    # Had the build model computed it, area runs would now default it.
    computed = FakeRunner(
        inputs=[name for name in BUILD_INPUTS if name != ABSENT_UNDER_BOTH]
    )
    assert ABSENT_UNDER_BOTH in _measure(model, paths, run=computed).defaulted_inputs


def test_build_model_is_read_at_its_manifest_pins_without_the_callers_settings(
    tmp_path, model, monkeypatch
):
    for name in (
        "UV_FROZEN",
        "UV_PROJECT_ENVIRONMENT",
        "VIRTUAL_ENV",
        "UV_INDEX_URL",
        "UV_EXTRA_INDEX_URL",
        "UV_CONSTRAINT",
        "UV_OVERRIDE",
        "UV_CONFIG_FILE",
    ):
        monkeypatch.setenv(name, "from the caller")
    monkeypatch.setenv("UV_CACHE_DIR", "/kept/cache")
    monkeypatch.setenv("KEPT_SETTING", "1")
    run = FakeRunner()
    _measure(model, {"dense": _h5(tmp_path / "dense.h5")}, run=run)
    ((command, kwargs),) = run.calls
    assert command[:-1] == [
        "uv",
        "run",
        "--no-project",
        "--no-config",
        "--default-index",
        "https://pypi.org/simple",
        "--exclude-newer",
        BUILD_CUTOFF,
        "--python",
        "3.13",
        "--with",
        f"policyengine-uk=={BUILD_VERSION}",
        "--with",
        f"policyengine-core=={BUILD_CORE_VERSION}",
        "python",
        "-I",
        "-c",
    ]
    assert command[-1] == model.BUILD_MODEL_PROBE
    assert kwargs["check"] is True
    assert "VIRTUAL_ENV" not in kwargs["env"]
    assert {name for name in kwargs["env"] if name.startswith("UV_")} == {
        "UV_CACHE_DIR"
    }
    assert kwargs["env"]["KEPT_SETTING"] == "1"


@pytest.mark.parametrize(
    ("built_at", "cutoff"),
    [
        (BUILT_AT, BUILD_CUTOFF),
        ("2026-10-19T03:07:51+01:00", "2026-10-19T02:07:51Z"),
        ("2026-10-19T02:07:51", "2026-10-19T02:07:51Z"),
        (None, None),
    ],
)
def test_the_build_model_resolves_as_of_the_release_build_in_utc(
    tmp_path, model, built_at, cutoff
):
    paths = {"dense": _h5(tmp_path / "dense.h5")}
    response = _response(paths)
    payload = json.loads(response.content)
    payload["build"]["built_at"] = built_at
    response.content = json.dumps(payload).encode()
    run = FakeRunner()
    _measure(model, paths, response, run=run)
    ((command, _),) = run.calls
    if cutoff is None:
        assert "--exclude-newer" not in command
    else:
        assert command[command.index("--exclude-newer") + 1] == cutoff


def test_an_unreadable_build_time_refuses_before_any_model_is_read(tmp_path, model):
    paths = {"dense": _h5(tmp_path / "dense.h5")}
    response = _response(paths)
    payload = json.loads(response.content)
    payload["build"]["built_at"] = "the day before the Budget"
    response.content = json.dumps(payload).encode()
    run = FakeRunner()
    with pytest.raises(ValueError, match="built_at"):
        _measure(model, paths, response, run=run)
    assert run.calls == []


@pytest.mark.parametrize(
    "resolved",
    [{"model_version": "2.132.7"}, {"core_version": "3.33.4"}],
    ids=["model", "core"],
)
def test_a_build_model_resolved_at_other_versions_refuses(tmp_path, model, resolved):
    paths = {"dense": _h5(tmp_path / "dense.h5")}
    with pytest.raises(ValueError, match="resolved"):
        _measure(model, paths, run=FakeRunner(**resolved))


@pytest.mark.parametrize(
    "unrecorded", ["built_with_model_package", "built_with_core_package", "build"]
)
def test_an_unrecorded_build_version_leaves_no_baseline_and_refuses(
    tmp_path, model, unrecorded
):
    paths = {"dense": _h5(tmp_path / "dense.h5")}
    response = _response(paths)
    payload = json.loads(response.content)
    if unrecorded == "build":
        del payload["build"]
    else:
        del payload["build"][unrecorded]
    response.content = json.dumps(payload).encode()
    run = FakeRunner()
    with pytest.raises(ValueError, match="baseline"):
        _measure(model, paths, response, run=run)
    assert run.calls == []


def test_a_failed_build_model_probe_refuses(tmp_path, model):
    paths = {"dense": _h5(tmp_path / "dense.h5")}

    def unresolvable(command, **kwargs):
        raise subprocess.CalledProcessError(
            1, command, stderr="No solution found when resolving --with dependencies"
        )

    with pytest.raises(ValueError, match="build model.*No solution"):
        _measure(model, paths, run=unresolvable)


@pytest.mark.parametrize(
    ("audited_by", "limitations"),
    [("\u200b", [LIMITATION]), ("Budget operator", ["\u200b"]), (" ", [LIMITATION])],
)
def test_an_invisible_auditor_or_limitation_refuses(
    tmp_path, model, audited_by, limitations
):
    paths = {"dense": _h5(tmp_path / "dense.h5")}
    with patch(
        "policyengine.provenance.certification.requests.get",
        return_value=_response(paths),
    ):
        with pytest.raises(ValueError, match="a reader can see"):
            model.measure_regional_input_surface(
                URI, paths, MODEL_VERSION, audited_by, limitations, run=FakeRunner()
            )


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


def test_comparison_is_relative_to_the_build_model():
    result = _module().compare_input_surface(
        {"dense": _artifact({"2025": ["weight", "area_code", "removed"]})},
        ["weight", "new_input", "old_input", "was_formula"],
        ["weight", "new_input", "old_input", "was_formula"],
        build_model_variables=["weight", "old_input", "was_formula", "removed"],
        build_model_inputs=["weight", "old_input", "removed"],
    )
    assert result == {
        "dropped_columns": ["removed"],
        "never_modelled_columns": ["area_code"],
        "defaulted_inputs": ["new_input", "was_formula"],
    }


def test_comparison_uses_each_artifact_and_every_period():
    artifact = _artifact(
        {"2025": ["income", "weight", "new_input"], "2026": ["income", "weight"]}
    )
    result = _module().compare_input_surface(
        {"dense": artifact},
        ["income", "income_reported", "weight", "new_input"],
        ["income_reported", "weight", "new_input"],
        {"income": "income_reported"},
        build_model_variables=["income", "income_reported", "weight"],
        build_model_inputs=["income_reported", "weight"],
    )
    assert result == {
        "dropped_columns": [],
        "never_modelled_columns": [],
        "defaulted_inputs": ["new_input"],
    }


def test_comparison_refuses_a_period_union_that_hides_columns():
    artifact = RegionalInputArtifactEvidence(
        repo_id="r",
        path="dense.h5",
        revision="cut",
        sha256="a" * 64,
        columns=["weight"],
        columns_by_period={"2025": ["weight", "removed"]},
    )
    with pytest.raises(ValueError, match="columns|union|period"):
        _module().compare_input_surface(
            {"dense": artifact},
            ["weight"],
            ["weight"],
            build_model_variables=["weight"],
            build_model_inputs=["weight"],
        )


def test_comparison_refuses_build_inputs_outside_the_build_variables():
    with pytest.raises(ValueError, match="build_model_inputs"):
        _module().compare_input_surface(
            {"dense": _artifact({"2025": ["weight"]})},
            ["weight"],
            ["weight"],
            build_model_variables=["weight"],
            build_model_inputs=["weight", "unknown"],
        )


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


def _manifest_with_build_time():
    from policyengine.provenance.manifest import DataReleaseManifest

    return DataReleaseManifest.model_validate(
        {
            "schema_version": 1,
            "data_package": {"name": "microcosm-data", "version": "1"},
            "build": {"built_at": BUILT_AT},
        }
    )


def test_certification_rereads_both_models_and_accepts_their_own_surfaces(
    tmp_path, model
):
    evidence = _measure(model, {"dense": _h5(tmp_path / "dense.h5")})
    run = FakeRunner()
    model.verify_model_surfaces(evidence, _manifest_with_build_time(), run=run)
    ((command, _),) = run.calls
    assert f"policyengine-uk=={BUILD_VERSION}" in command
    assert command[command.index("--exclude-newer") + 1] == BUILD_CUTOFF


@pytest.mark.parametrize(
    ("field", "edit"),
    [
        # A stored column the build model defines, claimed as never modelled.
        ("build_model_variables", lambda names: [n for n in names if n != REMOVED]),
        # The same column claimed as a target variable, so not dropped.
        ("model_variables", lambda names: sorted([*names, REMOVED])),
        # New defaults claimed as build inputs, so not defaulted.
        ("build_model_inputs", lambda names: sorted([*names, *DEFAULTS])),
        ("model_inputs", lambda names: names[1:]),
    ],
)
def test_an_edited_model_surface_refuses_at_certification(tmp_path, model, field, edit):
    evidence = _measure(model, {"dense": _h5(tmp_path / "dense.h5")})
    edited = evidence.model_copy(update={field: edit(getattr(evidence, field))})
    with pytest.raises(ValueError, match=field):
        model.verify_model_surfaces(
            edited, _manifest_with_build_time(), run=FakeRunner()
        )


def test_edited_input_aliases_refuse_at_certification(tmp_path, model):
    evidence = _measure(model, {"dense": _h5(tmp_path / "dense.h5")})
    edited = evidence.model_copy(update={"input_aliases": {}})
    with pytest.raises(ValueError, match="input_aliases"):
        model.verify_model_surfaces(
            edited, _manifest_with_build_time(), run=FakeRunner()
        )


def test_certification_needs_the_target_model_installed(tmp_path, model, monkeypatch):
    evidence = _measure(model, {"dense": _h5(tmp_path / "dense.h5")})
    monkeypatch.setattr(model, "version", lambda name: BUILD_VERSION)
    with pytest.raises(ValueError, match=f"{BUILD_VERSION}.*{MODEL_VERSION}"):
        model.verify_model_surfaces(
            evidence, _manifest_with_build_time(), run=FakeRunner()
        )


def test_the_build_model_probe_reads_the_model_api_the_audit_uses():
    """Run the probe with this interpreter, in place of a uv environment."""
    pytest.importorskip("policyengine_uk")
    module = _module()
    model_version = importlib.metadata.version("policyengine-uk")
    core_version = importlib.metadata.version("policyengine-core")

    def run_here(command, **kwargs):
        python = command.index("python")
        return subprocess.run([sys.executable, *command[python + 1 :]], **kwargs)

    surface = module._build_model_surface(model_version, core_version, run=run_here)
    variables, inputs, _ = module._model_surface(model_version)
    assert surface == (variables, inputs)


def test_audit_cli_writes_pydantic_evidence_json(tmp_path, model, monkeypatch, capsys):
    script_path = (
        Path(__file__).parents[1] / "scripts" / "audit_regional_input_surface.py"
    )
    spec = importlib.util.spec_from_file_location(
        "audit_regional_input_surface", script_path
    )
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    path = _h5(tmp_path / "dense.h5", person=(*PERSON, AREA_CODE))
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
    assert "0 dropped, 1 never-modelled, 2 defaulted" in capsys.readouterr().out


def test_audit_cli_bootstraps_before_target_model_is_certified(tmp_path):
    """The target must be auditable before it matches the current bundle."""
    script = Path(__file__).parents[1] / "scripts" / "audit_regional_input_surface.py"
    code = """
import importlib.util
import os
import runpy
import sys
os.environ.pop('POLICYENGINE_SKIP_COUNTRY_IMPORTS', None)
original = importlib.util.find_spec
def refuse_country_autoload(name, *args, **kwargs):
    if name in {'policyengine_uk', 'policyengine_us'}:
        raise RuntimeError('audit triggered automatic country import')
    return original(name, *args, **kwargs)
importlib.util.find_spec = refuse_country_autoload
sys.argv = [sys.argv[1], '--help']
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(script)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "--model-version" in result.stdout
