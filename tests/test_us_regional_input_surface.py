"""Audit and accept a US local-area release built with an earlier policyengine-us.

The US ACS-local release stores PolicyEngine core's variable/period layout:
one H5 group per variable, holding one array per period. The audit reads the
group and period names, never the arrays, and compares them with the release's
build model and the installed target, as for the UK. A stored input that
policyengine-us has since renamed counts as supplying its live input when .py
maps it (``LEGACY_INPUT_RENAMES``).
"""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import h5py
import numpy as np
import pandas as pd
import pytest

from policyengine.provenance.certification import (
    CertificationError,
    certify_data_release,
)
from policyengine.provenance.manifest import (
    CountryReleaseManifest,
    RegionalInputArtifactEvidence,
)
from tests.test_certify_data_release import (
    MANIFEST_URI,
    US_LOCAL_AREA_MANIFEST_URI,
    _local_area_release_manifest_payload,
    _populace_manifest_payload_without_regions,
    _response,
    _tmp_bundle,
    _without_releases_record,
)

TARGET_VERSION = "2.2.2"
BUILD_VERSION = "2.2.1"
BUILD_CORE_VERSION = "3.32.5"
BUILT_AT = "2026-10-17T03:05:12.307208+00:00"
#: BUILT_AT rounded up to the second: the build-model probe's --exclude-newer.
BUILD_CUTOFF = "2026-10-17T03:05:13Z"
URI = (
    "hf://dataset/policyengine/populace-us@abc123/releases/microcosm-us-2024-local/"
    "populace-us-2024-buildo-acs-local/release_manifest.json"
)
LOCAL = "populace_us_2024_acs_local"
LIMITATION = "Built with policyengine-us 2.2.1; 2.2.2 changes no variables or inputs"
#: The legacy take-up column the ACS-local release stores, and its live input.
LEGACY_WIC, LIVE_WIC = "would_claim_wic", "takes_up_wic_if_eligible"
INPUTS = ["employment_income", "household_id", "household_weight", "person_id"]
STORED = [*INPUTS, LEGACY_WIC]


class FakeVariable:
    def __init__(self, is_input):
        self.is_input = is_input

    def is_input_variable(self):
        return self.is_input


def fake_us_system(inputs, others=("wic",)):
    """A policyengine_us stand-in whose system defines ``inputs`` and ``others``."""

    class System:
        def __init__(self):
            self.variables = {
                **{name: FakeVariable(True) for name in inputs},
                **{name: FakeVariable(False) for name in others},
            }

    return SimpleNamespace(CountryTaxBenefitSystem=System)


class FakeRunner:
    """Stands in for ``uv run`` reading the build model, so nothing installs."""

    def __init__(self, variables=None, inputs=None, **resolved):
        build_inputs = sorted([*INPUTS, LIVE_WIC]) if inputs is None else inputs
        self.surface = {
            "model_version": BUILD_VERSION,
            "core_version": BUILD_CORE_VERSION,
            "variables": sorted([*build_inputs, "wic"])
            if variables is None
            else variables,
            "inputs": build_inputs,
        } | resolved
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        stdout = "Installed 60 packages\n" + json.dumps(self.surface) + "\n"
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")


def _module():
    return importlib.import_module("policyengine.provenance.regional_input_surface")


def core_h5(path, columns_by_period, *, metadata=True):
    """Write PolicyEngine core's layout: a group per variable, a dataset per period."""
    with h5py.File(path, "w") as file:
        for period, columns in columns_by_period.items():
            for column in columns:
                file.require_group(column).create_dataset(period, data=np.ones(2))
        if metadata:
            # A top-level dataset is file metadata, not a stored variable.
            file.create_dataset("policyengine_legacy_input_renames", data="{}")
    return path


def us_regional_manifest(paths, build=None) -> dict:
    return {
        "schema_version": 1,
        "data_package": {"name": "microcosm-data", "version": "0.1.0"},
        "dataset_role": "non_default_local_area",
        "is_default": False,
        "default_datasets": {},
        "build": {
            "build_id": "populace-us-2024-buildo-acs-local",
            "built_at": BUILT_AT,
            "built_with_model_package": {
                "name": "policyengine-us",
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
                "repo_id": "policyengine/populace-us",
                "revision": "abc123",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for name, path in paths.items()
        },
    }


def _served(payload) -> MagicMock:
    response = MagicMock(status_code=200)
    response.content = json.dumps(payload, indent=2).encode()
    return response


@pytest.fixture
def us_model(monkeypatch):
    """The audit module with policyengine-us 2.2.2 'installed' as a stand-in."""
    module = _module()
    installed = {"policyengine-us": TARGET_VERSION}
    monkeypatch.setattr(module, "version", lambda name: installed[name])
    monkeypatch.setitem(
        sys.modules, "policyengine_us", fake_us_system([*INPUTS, LIVE_WIC])
    )
    return module


def measure(module, paths, *, manifest=None, run=None):
    manifest = us_regional_manifest(paths) if manifest is None else manifest
    with patch(
        "policyengine.provenance.certification.requests.get",
        return_value=_served(manifest),
    ):
        return module.measure_regional_input_surface(
            URI,
            paths,
            TARGET_VERSION,
            "DTrim99",
            [LIMITATION],
            run=FakeRunner() if run is None else run,
        )


def test_a_us_core_layout_file_is_audited_against_policyengine_us(tmp_path, us_model):
    paths = {LOCAL: core_h5(tmp_path / f"{LOCAL}.h5", {"2024": STORED})}
    evidence = measure(us_model, paths)

    assert evidence.model_package == "policyengine-us"
    assert evidence.model_version == TARGET_VERSION
    assert (evidence.build_model_version, evidence.build_core_version) == (
        BUILD_VERSION,
        BUILD_CORE_VERSION,
    )
    artifact = evidence.artifacts[LOCAL]
    assert artifact.sha256 == hashlib.sha256(paths[LOCAL].read_bytes()).hexdigest()
    # The metadata dataset is not a column; each group is.
    assert artifact.columns == sorted(STORED)
    assert artifact.columns_by_period == {"2024": sorted(STORED)}
    # .py maps the stored legacy take-up column onto its live input, so the
    # live input is supplied and the legacy column is neither dropped nor
    # recorded as never modelled.
    assert evidence.input_aliases == {LEGACY_WIC: LIVE_WIC}
    assert evidence.dropped_columns == []
    assert evidence.never_modelled_columns == []
    assert evidence.defaulted_inputs == []
    assert evidence.audited_by == "DTrim99"
    assert evidence.limitations == [LIMITATION]


def test_the_us_build_model_is_read_with_policyengine_us_at_its_pins(
    tmp_path, us_model
):
    run = FakeRunner()
    measure(
        us_model, {LOCAL: core_h5(tmp_path / f"{LOCAL}.h5", {"2024": STORED})}, run=run
    )

    ((command, _),) = run.calls
    assert command[command.index("--exclude-newer") + 1] == BUILD_CUTOFF
    assert [command[i + 1] for i, part in enumerate(command) if part == "--with"] == [
        f"policyengine-us=={BUILD_VERSION}",
        f"policyengine-core=={BUILD_CORE_VERSION}",
    ]
    assert "import policyengine_us" in command[-1]
    assert "policyengine_uk" not in command[-1]
    assert 'version("policyengine-us")' in command[-1]


def test_a_us_column_the_build_model_defines_and_the_target_does_not_refuses(
    tmp_path, us_model
):
    paths = {LOCAL: core_h5(tmp_path / f"{LOCAL}.h5", {"2024": [*STORED, "retired"]})}
    run = FakeRunner(inputs=sorted([*INPUTS, LIVE_WIC, "retired"]))
    with pytest.raises(ValueError, match=r"policyengine-us 2\.2\.1 defines.*retired"):
        measure(us_model, paths, run=run)


def test_a_us_column_neither_model_defines_is_recorded_not_refused(tmp_path, us_model):
    paths = {LOCAL: core_h5(tmp_path / f"{LOCAL}.h5", {"2024": [*STORED, "puma_code"]})}
    assert measure(us_model, paths).never_modelled_columns == ["puma_code"]


def test_a_us_input_the_file_lacks_and_the_build_model_lacked_is_defaulted(
    tmp_path, monkeypatch, us_model
):
    monkeypatch.setitem(
        sys.modules,
        "policyengine_us",
        fake_us_system([*INPUTS, LIVE_WIC, "new_input"]),
    )
    paths = {LOCAL: core_h5(tmp_path / f"{LOCAL}.h5", {"2024": STORED})}
    assert measure(us_model, paths).defaulted_inputs == ["new_input"]


def test_without_the_legacy_column_the_live_input_is_not_supplied(tmp_path, us_model):
    """The rename applies only to stored data that carries the legacy column."""
    paths = {LOCAL: core_h5(tmp_path / f"{LOCAL}.h5", {"2024": INPUTS})}
    run = FakeRunner(inputs=sorted(INPUTS))
    assert measure(us_model, paths, run=run).defaulted_inputs == [LIVE_WIC]


def test_a_us_file_in_entity_table_layout_refuses(tmp_path, us_model):
    path = tmp_path / f"{LOCAL}.h5"
    with pd.HDFStore(path, mode="w") as store:
        store.put("person/2024", pd.DataFrame({"person_id": [1.0]}))
    with pytest.raises(ValueError, match="variable/period layout"):
        measure(us_model, {LOCAL: path})


def test_a_us_period_that_is_not_a_year_refuses(tmp_path, us_model):
    paths = {
        LOCAL: core_h5(
            tmp_path / f"{LOCAL}.h5", {"2024": STORED, "2024-01": ["employment_income"]}
        )
    }
    with pytest.raises(ValueError, match="2024-01"):
        measure(us_model, paths)


def test_the_installed_policyengine_us_must_be_the_requested_version(
    tmp_path, monkeypatch, us_model
):
    monkeypatch.setattr(us_model, "version", lambda name: "2.2.1")
    paths = {LOCAL: core_h5(tmp_path / f"{LOCAL}.h5", {"2024": STORED})}
    with pytest.raises(ValueError, match="policyengine-us 2.2.1 differs"):
        measure(us_model, paths)


def _artifact(columns_by_period):
    return RegionalInputArtifactEvidence(
        repo_id="r",
        path="local.h5",
        revision="cut",
        sha256="a" * 64,
        columns=sorted({column for c in columns_by_period.values() for column in c}),
        columns_by_period=columns_by_period,
    )


def test_a_us_legacy_column_the_build_model_defined_is_mapped_not_dropped():
    """A column renamed since the build is read through .py's rename."""
    comparison = _module().compare_input_surface(
        {LOCAL: _artifact({"2024": ["person_id", LEGACY_WIC]})},
        ["person_id", LIVE_WIC],
        ["person_id", LIVE_WIC],
        {LEGACY_WIC: LIVE_WIC},
        build_model_variables=["person_id", LEGACY_WIC],
        build_model_inputs=["person_id", LEGACY_WIC],
        model_package="policyengine-us",
    )
    assert comparison == {
        "dropped_columns": [],
        "never_modelled_columns": [],
        "defaulted_inputs": [],
    }


@pytest.mark.parametrize(
    ("model_package", "donor_is_a_variable"),
    [("policyengine-us", True), ("policyengine-uk", False)],
)
def test_aliases_must_have_each_model_s_own_shape(model_package, donor_is_a_variable):
    """A UK move reads a variable the model defines; a US rename, one it doesn't."""
    variables = ["person_id", LIVE_WIC, *([LEGACY_WIC] if donor_is_a_variable else [])]
    with pytest.raises(ValueError, match="Unsupported input alias"):
        _module().compare_input_surface(
            {LOCAL: _artifact({"2024": ["person_id", LEGACY_WIC]})},
            variables,
            ["person_id", LIVE_WIC],
            {LEGACY_WIC: LIVE_WIC},
            build_model_variables=["person_id"],
            build_model_inputs=["person_id"],
            model_package=model_package,
        )


# Certification ----------------------------------------------------------------

REASON = "2.2.2 adds only the spm-calculator pin and 2036 CPI-U points to 2.2.1"
CERTIFIED = "1.724.0"
BUILT_WITH = "1.723.0"
CORE = "3.27.1"


def local_area_release() -> dict:
    """The fixture ACS-local release, built with 1.723.0 and claiming nothing."""
    release = _local_area_release_manifest_payload()
    release["build"]["built_at"] = BUILT_AT
    release["build"]["built_with_core_package"] = {
        "name": "policyengine-core",
        "version": CORE,
    }
    return release


def national_release() -> dict:
    release = _populace_manifest_payload_without_regions()
    release["compatible_model_packages"] = [
        {"name": "policyengine-us", "specifier": f">={BUILT_WITH},<1.725"}
    ]
    return release


def us_evidence(release: dict) -> dict:
    artifact = release["artifacts"][LOCAL]
    return {
        "schema_version": 2,
        "regional_manifest_uri": US_LOCAL_AREA_MANIFEST_URI,
        "regional_manifest_sha256": hashlib.sha256(
            json.dumps(release).encode()
        ).hexdigest(),
        "model_package": "policyengine-us",
        "model_version": CERTIFIED,
        "build_model_version": BUILT_WITH,
        "build_core_version": CORE,
        "artifacts": {
            LOCAL: {
                key: artifact[key] for key in ("repo_id", "path", "revision", "sha256")
            }
            | {
                "columns": ["person_id", LEGACY_WIC],
                "columns_by_period": {"2024": ["person_id", LEGACY_WIC]},
            }
        },
        "model_variables": ["person_id", LIVE_WIC],
        "model_inputs": ["person_id", LIVE_WIC],
        "build_model_variables": ["person_id", LIVE_WIC],
        "build_model_inputs": ["person_id", LIVE_WIC],
        "input_aliases": {LEGACY_WIC: LIVE_WIC},
        "dropped_columns": [],
        "never_modelled_columns": [],
        "defaulted_inputs": [],
        "audited_by": "DTrim99",
        "limitations": [LIMITATION],
    }


@pytest.fixture
def us_surfaces(monkeypatch):
    """Stand in for the two policyengine-us models certification re-reads."""
    module = _module()
    reads = []

    def target(model_version, model_package="policyengine-uk"):
        reads.append(("target", model_package, model_version))
        return ["person_id", LIVE_WIC], ["person_id", LIVE_WIC], {LEGACY_WIC: LIVE_WIC}

    def build(
        model_version,
        core_version,
        run=None,
        exclude_newer=None,
        model_package="policyengine-uk",
    ):
        reads.append(("build", model_package, model_version, core_version))
        return ["person_id", LIVE_WIC], ["person_id", LIVE_WIC]

    monkeypatch.setattr(module, "_model_surface", target)
    monkeypatch.setattr(module, "_build_model_surface", build)
    return reads


def certify_us(bundle_path, regional: dict, **kwargs):
    with (
        patch(
            "policyengine.provenance.certification.requests.get",
            side_effect=_without_releases_record(
                [_response(national_release()), _response(regional)]
            ),
        ),
        patch("policyengine.provenance.certification.head_artifact", return_value=True),
        patch(
            "policyengine.provenance.certification.head_release_file",
            return_value=True,
        ),
        patch(
            "policyengine.provenance.certification.head_artifact_reference",
            return_value=True,
        ),
        patch(
            "policyengine.provenance.certification.fetch_pypi_wheel_metadata",
            return_value={"sha256": "d" * 64, "url": "https://example"},
        ),
        patch(
            "policyengine.provenance.certification.policyengine_version",
            return_value="9.9.9",
        ),
    ):
        return certify_data_release(
            country="us",
            data_producer="populace",
            manifest_uri=MANIFEST_URI,
            regional_manifest_uri=US_LOCAL_AREA_MANIFEST_URI,
            model_version=CERTIFIED,
            bundle_path=bundle_path,
            **kwargs,
        )


def test_us_accepted_mismatch_routes_the_local_area_release_and_records_it(
    tmp_path, us_surfaces
):
    bundle_path = _tmp_bundle(tmp_path)
    regional = local_area_release()
    evidence = us_evidence(regional)

    result = certify_us(
        bundle_path,
        regional,
        regional_model_mismatch_reason=REASON,
        regional_input_surface_evidence=evidence,
    )

    release = json.loads(bundle_path.read_text())["data_releases"]["us"]
    assert release["regional_release_kind"] == "local_area"
    assert release["region_datasets"]["state"] == {
        "path_template": "populace_us_2024_acs_local.h5"
    }
    # No UK limitation is added: the record carries the audit's own.
    assert release["regional_certification"] == {
        "compatibility_basis": "accepted_model_mismatch",
        "certified_for_model_version": CERTIFIED,
        "built_with_model_version": BUILT_WITH,
        "accepted_reason": REASON,
        "area_receipts": "uncertified",
        "regional_manifest_uri": US_LOCAL_AREA_MANIFEST_URI,
        "regional_manifest_sha256": evidence["regional_manifest_sha256"],
        "defaulted_inputs": [],
        "dropped_columns": [],
        "never_modelled_columns": [],
        "stored_columns": "auditor_attested",
        "limitations": [LIMITATION],
        "evidence": evidence,
    }
    assert CountryReleaseManifest.model_validate(release).regional_certification
    # Both policyengine-us models were re-read; no UK model was.
    assert {read[1] for read in us_surfaces} == {"policyengine-us"}
    assert any("accepted mismatch" in warning for warning in result.warnings)


def test_us_accepted_mismatch_without_evidence_refuses(tmp_path, us_surfaces):
    with pytest.raises(CertificationError, match="audited input-surface evidence"):
        certify_us(
            _tmp_bundle(tmp_path),
            local_area_release(),
            regional_model_mismatch_reason=REASON,
        )
