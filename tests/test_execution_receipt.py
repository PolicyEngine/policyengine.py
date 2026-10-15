"""Execution receipt schema v1 (policyengine.provenance.receipt).

Invariants tested here:

- a receipt claims certification only when the certificate covers the
  installed model and core versions, the simulated dataset bytes and name,
  and the running wrapper version;
- verify_certificate accepts exactly the receipts the bundle certifies: a
  receipt built from a bundle verifies against it, and changing any certified
  member of the certificate or data, however consistently, is reported
  (differential with the builder);
- a wheel hash is recorded only when the builder verified it;
- the execution identity depends only on runtime, data and certificate
  content, never on how the builder was called; the receipt digest adds
  reform, baseline, years and outputs, never runtime context or labels;
- digests are over strict JSON: nothing is silently stringified, member
  order and null-versus-omitted do not matter, and colliding keys are refused;
- a reform digest binds content, or a module-level modifier's source,
  module source and defaults plus a revision, independent of where the code
  is checked out; code edited after import, closures, lambdas, partials,
  methods and non-Scenario objects are refused;
- the Pydantic model and the published JSON Schema accept the same valid
  receipts and reject the same malformed ones (differential test).
"""

from __future__ import annotations

import copy
import datetime
import decimal
import enum
import functools
import hashlib
import importlib.util
import inspect
import json
import linecache
import os
import re
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from types import CodeType, SimpleNamespace
from typing import Union, get_args
from urllib.parse import urlparse

import jsonschema
import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from policyengine.provenance import receipt as receipt_module
from policyengine.provenance.canonical import canonical_sha256
from policyengine.provenance.receipt import (
    ExecutionReceipt,
    FiscalYearConvention,
    ReceiptError,
    ReformIdentity,
    build_execution_receipt,
    build_execution_receipt_for_microsimulation,
    certificate_sha256,
    content_sha256,
    fiscal_year_label,
    installed_package_identity,
    reform_identity,
    scenario_reform_identity,
    strict_json_value,
    uk_fiscal_year_convention,
    verify_certificate,
)
from tests import receipt_modifiers, receipt_unbindable_modifiers

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_DIR = REPO_ROOT / "src" / "policyengine" / "data" / "bundle"
BUNDLE_PATH = BUNDLE_DIR / "manifest.json"
SCHEMA_PATH = (
    REPO_ROOT
    / "src"
    / "policyengine"
    / "data"
    / "schemas"
    / "execution_receipt.v1.schema.json"
)
SHA = st.text(alphabet="0123456789abcdef", min_size=64, max_size=64)
INSTALLED_UK = metadata.version("policyengine-uk")
INSTALLED_CORE = metadata.version("policyengine-core")
INSTALLED_WRAPPER = metadata.version("policyengine")
CURRENT_LAW = ReformIdentity(kind="current_law")
REVISION = {
    "repository": "PolicyEngine/uk-autumn-budget-dashboard-2026",
    "git_sha": "a" * 40,
}


#: What the certified 1.58.0 dataset projects to under policyengine-uk 2.125.1
#: and 2.126.12 (measured with extend_single_year_dataset, 12 Oct 2026).
PROJECTED_YEARS = tuple(range(2024, 2031))


@pytest.fixture(autouse=True)
def _projection(monkeypatch, request):
    """Builder tests use a fixed projection; the real one needs the real file."""

    if request.node.originalname == "test_the_certified_dataset_projects_to_2030":
        return
    monkeypatch.setattr(
        receipt_module,
        "_projected_years",
        lambda path, sha256, model_version: PROJECTED_YEARS,
    )


def _bundle_for(
    dataset_bytes: bytes, *, model_version=INSTALLED_UK, core_version=INSTALLED_CORE
) -> dict:
    """The committed bundle with its UK certificate pointed at these bytes."""

    bundle = json.loads(BUNDLE_PATH.read_text())
    record = bundle["data_releases"]["uk"]
    digest = hashlib.sha256(dataset_bytes).hexdigest()
    record["certified_data_artifact"]["sha256"] = digest
    record["datasets"][record["default_dataset"]]["sha256"] = digest
    record["certification"]["certified_for_model_version"] = model_version
    bundle["packages"]["policyengine-core"]["version"] = core_version
    bundle["policyengine_version"] = INSTALLED_WRAPPER
    record["policyengine_version"] = INSTALLED_WRAPPER
    return bundle


def _build(dataset_file, bundle=None, **kwargs):
    kwargs.setdefault("years", [2026])
    kwargs.setdefault("reform", CURRENT_LAW)
    kwargs.setdefault("baseline", CURRENT_LAW)
    return build_execution_receipt(
        country_id="uk",
        dataset_path=dataset_file,
        bundle=bundle if bundle is not None else _bundle_for(dataset_file.read_bytes()),
        **kwargs,
    )


#: The real policyengine, policyengine_uk and policyengine_core modules this
#: test process loaded, so a test can tell them from synthetic stand-ins.
_REAL_PACKAGE_MODULES = {
    name.replace("-", "_"): sys.modules.get(name.replace("-", "_"))
    for name in receipt_module.UK_PACKAGES.values()
}


#: The interpreter's import path when this module is collected. Release-script
#: tests import scripts/bundle.py at module level, which puts the checkout's
#: ``src`` first on sys.path. An editable build leaves
#: ``src/policyengine.egg-info`` there, which then shadows the installed
#: distribution's metadata (receipts rightly refuse that), so each receipt test
#: runs with the import path as it was before those modules were collected.
_COLLECTION_SYS_PATH = list(sys.path)


@pytest.fixture(autouse=True)
def _import_path_as_collected(monkeypatch):
    monkeypatch.setattr(sys, "path", list(_COLLECTION_SYS_PATH))


#: The distribution lookup the receipt module's origin check uses, before any
#: test replaces it.
_REAL_DISTRIBUTION = receipt_module.metadata.distribution


def _this_checkout_is_the_installed_policyengine() -> bool:
    """Whether the installed policyengine is an editable install of this checkout."""

    try:
        direct_url = receipt_module._read_direct_url("policyengine")
    except ReceiptError:
        return False
    if not direct_url or not (direct_url.get("dir_info") or {}).get("editable"):
        return False
    loaded = Path(sys.modules["policyengine"].__file__).resolve()
    source = Path(urlparse(direct_url["url"]).path).resolve()
    return source in loaded.parents


@pytest.fixture(autouse=True)
def _real_packages_load_from_their_install(request, monkeypatch):
    """Treat the real packages as loaded from the distributions they name.

    How this repository is installed differs between environments: CI
    installs it editable and then installs a released policyengine over it,
    so the tests run this checkout's code under another version's metadata,
    which the receipt rightly refuses. Receipt tests are about receipts, not
    about the test environment, so the real modules are taken as loaded from
    their install, but only while the distribution lookup the check reads
    (``metadata.distribution``) is the real one too.
    A synthetic module a test puts in ``sys.modules``, or a synthetic
    distribution it supplies for a real module, is still checked, and the
    real check runs unchanged in tests marked ``real_install``.
    """

    if request.node.get_closest_marker("real_install"):
        return
    original = receipt_module._refuse_loaded_package_origin

    def refuse(name):
        import_name = receipt_module.normalize_distribution_name(name).replace("-", "_")
        module = sys.modules.get(import_name)
        if (
            module is not None
            and module is _REAL_PACKAGE_MODULES.get(import_name)
            and getattr(receipt_module.metadata, "distribution", None)
            is _REAL_DISTRIBUTION
        ):
            return None
        return original(name)

    monkeypatch.setattr(receipt_module, "_refuse_loaded_package_origin", refuse)


@pytest.fixture
def index_installs(monkeypatch):
    """Simulate index certification; loaded paths still use real install metadata."""

    monkeypatch.setattr(receipt_module, "_read_direct_url", lambda name: None)


@pytest.fixture
def dataset_file(tmp_path, index_installs):
    path = tmp_path / "enhanced_frs_2024_25.h5"
    path.write_bytes(b"certified dataset bytes")
    return path


@pytest.fixture
def certified_receipt(dataset_file):
    return _build(dataset_file, years=[2027, 2026, 2027])


# --- Certification -----------------------------------------------------------


def test_certified_when_certificate_covers_what_ran(certified_receipt, dataset_file):
    receipt = certified_receipt
    assert receipt.certification_status == "certified"
    assert all(
        package.install_origin is None
        for package in (receipt.wrapper, receipt.model, receipt.core)
    )
    assert (
        receipt.model.version
        == receipt.certificate.certified_for_model_version
        == INSTALLED_UK
    )
    assert (
        receipt.core.version
        == receipt.certificate.certified_for_core_version
        == INSTALLED_CORE
    )
    assert (
        receipt.data.dataset_sha256
        == hashlib.sha256(dataset_file.read_bytes()).hexdigest()
    )
    assert receipt.years == [2026, 2027]
    assert receipt.certificate.certificate_source == "caller_supplied"
    record = _bundle_for(dataset_file.read_bytes())["data_releases"]["uk"]
    assert receipt.certificate.certificate_sha256 == certificate_sha256(record)


@pytest.mark.parametrize(
    "change",
    [
        "model version",
        "core version",
        "wrapper version in bundle",
        "wrapper version in record",
        "dataset name",
    ],
)
def test_any_uncovered_component_makes_the_receipt_uncertified(
    dataset_file, tmp_path, change
):
    data = dataset_file.read_bytes()
    bundle = _bundle_for(data)
    path = dataset_file
    kwargs = {}
    if change == "model version":
        bundle = _bundle_for(data, model_version="0.0.1")
    elif change == "core version":
        bundle = _bundle_for(data, core_version="0.0.1")
    elif change == "wrapper version in bundle":
        bundle["policyengine_version"] = "0.0.0"
    elif change == "wrapper version in record":
        bundle["data_releases"]["uk"]["policyengine_version"] = "0.0.0"
    elif change == "dataset name":
        # Same bytes registered under another certified dataset name.
        record = bundle["data_releases"]["uk"]
        record["datasets"]["frs_2024_25"]["sha256"] = record["certified_data_artifact"][
            "sha256"
        ]
        kwargs["dataset"] = "frs_2024_25"
    receipt = _build(path, bundle, **kwargs)
    assert receipt.certification_status == "uncertified"
    assert receipt.certificate is None
    assert receipt.model.version == INSTALLED_UK  # installed, never the manifest's


@pytest.mark.parametrize(
    "years",
    [[2027.9], [True], "2027", [], [2027, "2028"], 2027, [np.float64(2027)]],
    ids=["float", "bool", "string", "empty", "mixed", "scalar", "numpy-float"],
)
def test_receipt_years_must_be_integers(dataset_file, years):
    """Round-4 review L8: years are never coerced."""

    with pytest.raises(ReceiptError, match="years|at least one year"):
        _build(dataset_file, years=years)


def test_numpy_integer_years_are_accepted(dataset_file):
    assert _build(dataset_file, years=[np.int64(2027), 2026]).years == [2026, 2027]


def test_a_boolean_schema_version_is_refused(certified_receipt, schema_validator):
    payload = json.loads(certified_receipt.model_dump_json())
    payload["schema_version"] = True
    with pytest.raises(ValidationError):
        ExecutionReceipt.model_validate(payload)
    with pytest.raises(jsonschema.ValidationError):
        schema_validator.validate(payload)


def test_unknown_dataset_and_incomplete_bundles_are_refused(dataset_file):
    with pytest.raises(ReceiptError):
        _build(dataset_file, dataset="not_a_bundle_dataset")
    bundle = _bundle_for(dataset_file.read_bytes())
    del bundle["data_releases"]["uk"]["data_package"]["name"]
    with pytest.raises(ReceiptError):
        _build(dataset_file, bundle)
    with pytest.raises(ReceiptError):
        build_execution_receipt(
            country_id="us",
            dataset_path=dataset_file,
            years=[2026],
            reform=CURRENT_LAW,
            baseline=CURRENT_LAW,
        )


def test_bytes_that_are_not_the_named_dataset_are_refused(dataset_file, tmp_path):
    """A receipt never gives one artifact's name and URI to other bytes."""

    other = tmp_path / "other.h5"
    other.write_bytes(b"different bytes")
    with pytest.raises(ReceiptError, match="is not the bundle's"):
        _build(other, _bundle_for(dataset_file.read_bytes()))


def test_overlay_datasets_receive_uncertified_receipts(dataset_file):
    bundle = _bundle_for(dataset_file.read_bytes())
    overlay_name = next(iter(bundle["dataset_overlays"]["uk"]))
    bundle["dataset_overlays"]["uk"][overlay_name]["sha256"] = hashlib.sha256(
        dataset_file.read_bytes()
    ).hexdigest()
    receipt = _build(dataset_file, bundle, dataset=overlay_name)
    assert receipt.certification_status == "uncertified"
    assert receipt.data.dataset == overlay_name
    assert receipt.data.build_id is None


def test_an_omitted_artifact_revision_is_the_release_manifest_revision(dataset_file):
    """Round-4 review M5: the receipt names what the materializer downloads."""

    bundle = _bundle_for(dataset_file.read_bytes())
    record = bundle["data_releases"]["uk"]
    del record["datasets"][record["default_dataset"]]["revision"]
    receipt = _build(dataset_file, bundle)
    pinned = record["data_package"]["release_manifest_revision"]
    assert receipt.data.dataset_revision == pinned
    assert receipt.data.dataset_uri.endswith(f"@{pinned}")
    assert receipt.data.release_version == record["data_package"]["version"]
    assert verify_certificate(receipt, bundle) == []


def test_a_datasets_own_package_is_kept(dataset_file):
    bundle = _bundle_for(dataset_file.read_bytes())
    record = bundle["data_releases"]["uk"]
    record["datasets"][record["default_dataset"]]["data_package_name"] = "other-data"
    assert _build(dataset_file, bundle).data.data_package == "other-data"


def test_every_packaged_dataset_resolves_as_the_materializer_resolves_it():
    """Differential: the receipt and ``materialize_dataset`` name one artifact."""

    from policyengine.provenance.dataset_materialization import (
        _resolve_bundle_dataset,
    )

    bundle = json.loads(BUNDLE_PATH.read_text())
    record = bundle["data_releases"]["uk"]
    names = [*record["datasets"], *(bundle.get("dataset_overlays") or {}).get("uk", {})]
    assert names
    for name in names:
        spec = _resolve_bundle_dataset("uk", name)  # the packaged manifest
        identity = receipt_module._data_identity(
            "uk", record, bundle, name, spec.sha256
        )
        assert (identity.dataset_uri, identity.dataset_revision) == (
            spec.source_uri,
            spec.revision,
        )
        assert identity.data_package == spec.data_package_name


@pytest.mark.usefixtures("index_installs")
def test_packaged_bundle_certificate_records_its_source_and_tro(tmp_path, monkeypatch):
    """With the installed bundle, the certificate says packaged and names the TRO."""

    from policyengine.provenance import certification
    from policyengine.provenance.trace import extract_bundle_tro_reference

    dataset = tmp_path / "data.h5"
    dataset.write_bytes(b"packaged certified bytes")
    packaged = tmp_path / "bundle"
    packaged.mkdir()
    (packaged / "manifest.json").write_text(
        json.dumps(_bundle_for(dataset.read_bytes()))
    )
    (packaged / "uk.trace.tro.jsonld").write_bytes(
        (BUNDLE_DIR / "uk.trace.tro.jsonld").read_bytes()
    )
    monkeypatch.setattr(
        certification, "default_bundle_source_path", lambda: packaged / "manifest.json"
    )
    receipt = build_execution_receipt(
        country_id="uk",
        dataset_path=dataset,
        years=[2026],
        reform=CURRENT_LAW,
        baseline=CURRENT_LAW,
    )
    assert receipt.certification_status == "certified"
    assert receipt.certificate.certificate_source == "packaged"
    expected = extract_bundle_tro_reference(
        json.loads((BUNDLE_DIR / "uk.trace.tro.jsonld").read_text())
    )
    assert receipt.certificate.tro_composition_fingerprint == expected["fingerprint"]


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("certificate", "certified_for_model_version"), "0.0.1"),
        (("certificate", "certified_for_core_version"), "0.0.1"),
        (("certificate", "certified_dataset_sha256"), "0" * 64),
        (("certificate", "bundle_version"), "0.0.0"),
        (("certification_status",), "uncertified"),
        (("years",), [2027, 2026]),
        (("years",), [2026, 2026]),
        (("model", "name"), "policyengine-us"),
        (("core", "name"), "numpy"),
        (("wrapper", "name"), "not-policyengine"),
    ],
)
def test_receipts_cannot_claim_what_did_not_run(certified_receipt, path, value):
    payload = certified_receipt.model_dump(mode="json")
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        ExecutionReceipt.model_validate(payload)


def test_strict_parsing_never_coerces(certified_receipt):
    payload = certified_receipt.model_dump(mode="json")
    for mutate in (
        lambda p: p.update(years=["2026"]),
        lambda p: p.update(years=[True]),
        lambda p: p["model"].update(name="Policyengine_UK"),
        lambda p: p["fiscal_year"].update(period_start="01-01"),
    ):
        changed = copy.deepcopy(payload)
        mutate(changed)
        with pytest.raises(ValidationError):
            ExecutionReceipt.model_validate(changed)


def test_verify_certificate_against_a_published_bundle(certified_receipt, dataset_file):
    bundle = _bundle_for(dataset_file.read_bytes())
    assert verify_certificate(certified_receipt, bundle) == []
    tampered = copy.deepcopy(bundle)
    tampered["data_releases"]["uk"]["certification"]["compatibility_basis"] = "trust me"
    assert verify_certificate(certified_receipt, tampered)
    uncertified = _build(
        dataset_file, _bundle_for(dataset_file.read_bytes(), model_version="0.0.1")
    )
    assert verify_certificate(uncertified, bundle) == ["the receipt is uncertified"]
    assert verify_certificate(certified_receipt, {"data_releases": {}}) == [
        "the bundle has no uk data release"
    ]


def _forge(receipt: ExecutionReceipt, **changes) -> ExecutionReceipt:
    """A receipt edited consistently, so the model's own rules still accept it."""

    payload = copy.deepcopy(receipt.model_dump(mode="json"))
    for path, value in changes.items():
        target = payload
        *parents, last = path.split("__")
        for key in parents:
            target = target[key]
        target[last] = value
    return ExecutionReceipt.model_validate(payload)


def test_a_forged_receipt_with_the_genuine_record_digest_does_not_verify(
    certified_receipt, dataset_file
):
    """Round-2 review N1: the forgery kept certificate_sha256 and changed the rest."""

    bundle = _bundle_for(dataset_file.read_bytes())
    forged = _forge(
        certified_receipt,
        model__version="2.199.0",
        certificate__certified_for_model_version="2.199.0",
        data__dataset_sha256="e" * 64,
        certificate__certified_dataset_sha256="e" * 64,
        certificate__compatibility_basis="trust me",
        certificate__certificate_source="packaged",
    )
    assert forged.certification_status == "certified"
    assert forged.certificate.certificate_sha256 == (
        certified_receipt.certificate.certificate_sha256
    )
    problems = verify_certificate(forged, bundle)
    assert any("certified_for_model_version" in p for p in problems)
    assert any("certified_dataset_sha256" in p for p in problems)
    assert any("compatibility_basis" in p for p in problems)
    assert any("data.dataset_sha256" in p for p in problems)


#: Consistent edits a forger could make, each of which the model accepts.
FORGERIES = {
    "bundle version": {
        "wrapper__version": "9.9.9",
        "certificate__bundle_version": "9.9.9",
    },
    "model version": {
        "model__version": "9.9.9",
        "certificate__certified_for_model_version": "9.9.9",
    },
    "core version": {
        "core__version": "9.9.9",
        "certificate__certified_for_core_version": "9.9.9",
    },
    "dataset bytes": {
        "data__dataset_sha256": "e" * 64,
        "certificate__certified_dataset_sha256": "e" * 64,
    },
    "record digest": {"certificate__certificate_sha256": "e" * 64},
    "basis": {"certificate__compatibility_basis": "built_with_model_package"},
    "certifier": {"certificate__certified_by": "someone else"},
    "dataset name": {"data__dataset": "frs_2024_25"},
    "data release": {"data__release_version": "9.9.9"},
    "data package": {"data__data_package": "policyengine-uk-data-public"},
    "data build": {"data__build_id": "policyengine-uk-data-9.9.9"},
    "build fingerprint": {"data__build_fingerprint": "sha256:" + "e" * 64},
    "build model": {"data__build_model_version": "9.9.9"},
    "manifest revision": {"data__release_manifest_revision": "e" * 40},
    "dataset uri": {"data__dataset_uri": "hf://someone/else.h5@1.58.0"},
    "dataset revision": {"data__dataset_revision": "main"},
}


@pytest.mark.parametrize("name", sorted(FORGERIES))
def test_each_consistent_forgery_alone_is_reported(dataset_file, name):
    bundle = _bundle_for(dataset_file.read_bytes())
    genuine = _build(dataset_file, bundle)
    assert verify_certificate(_forge(genuine, **FORGERIES[name]), bundle)


def test_a_record_from_another_policyengine_version_is_named(
    certified_receipt, dataset_file
):
    bundle = _bundle_for(dataset_file.read_bytes())
    bundle["data_releases"]["uk"]["policyengine_version"] = "0.0.0"
    problems = verify_certificate(certified_receipt, bundle)
    assert any("record belongs to policyengine 0.0.0" in p for p in problems)


def test_a_certifying_bundle_must_state_its_basis(dataset_file):
    bundle = _bundle_for(dataset_file.read_bytes())
    del bundle["data_releases"]["uk"]["certification"]["compatibility_basis"]
    with pytest.raises(ReceiptError, match="compatibility_basis"):
        _build(dataset_file, bundle)


@settings(max_examples=40, deadline=None)
@given(
    names=st.lists(
        st.sampled_from(sorted(FORGERIES)), min_size=1, max_size=4, unique=True
    )
)
@pytest.mark.usefixtures("index_installs")
def test_every_consistent_forgery_is_reported(tmp_path_factory, names):
    dataset = tmp_path_factory.mktemp("forgery") / "data.h5"
    dataset.write_bytes(b"forgery bytes")
    bundle = _bundle_for(dataset.read_bytes())
    genuine = _build(dataset, bundle)
    assert verify_certificate(genuine, bundle) == []
    changes = {path: value for name in names for path, value in FORGERIES[name].items()}
    assert verify_certificate(_forge(genuine, **changes), bundle)


@pytest.mark.parametrize(
    "edit",
    [
        lambda b: b["data_releases"]["uk"]["certification"].update(
            certified_by="someone else"
        ),
        lambda b: b["data_releases"]["uk"]["data_package"].update(version="9.9.9"),
        lambda b: b["data_releases"]["uk"]["certified_data_artifact"].update(
            dataset="frs_2024_25"
        ),
        lambda b: b["data_releases"]["uk"].update(policyengine_version="0.0.0"),
        lambda b: b.update(policyengine_version="0.0.0"),
        lambda b: b["packages"]["policyengine-core"].update(version="0.0.1"),
    ],
    ids=[
        "certifier",
        "data version",
        "certified dataset",
        "record version",
        "bundle version",
        "core",
    ],
)
def test_verification_and_building_agree_on_each_bundle(dataset_file, edit):
    """Differential: a receipt verifies against a bundle iff that bundle built it."""

    bundle = _bundle_for(dataset_file.read_bytes())
    other = copy.deepcopy(bundle)
    edit(other)
    receipt = _build(dataset_file, bundle)
    assert verify_certificate(receipt, bundle) == []
    assert verify_certificate(receipt, other)
    rebuilt = _build(dataset_file, other)
    if rebuilt.certification_status == "certified":
        assert verify_certificate(rebuilt, other) == []
        assert verify_certificate(rebuilt, bundle)


# --- Wheel hashes ----------------------------------------------------------------


def test_wheel_hashes_need_the_builder_to_verify_them(dataset_file, monkeypatch):
    seen = {}

    def verify(name, wheel_path, metadata):
        seen[name] = wheel_path
        return {"wheel_sha256": "a" * 64, "problems": []}

    monkeypatch.setattr(
        "policyengine.provenance.wheels.verify_installed_against_wheel", verify
    )
    receipt = _build(dataset_file, wheel_paths={"policyengine_uk": Path("uk.whl")})
    assert receipt.model.wheel_sha256 == "a" * 64
    assert receipt.model.wheel_sha256_evidence == "installed_record_verified"
    assert seen == {"policyengine-uk": Path("uk.whl")}
    monkeypatch.setattr(
        "policyengine.provenance.wheels.verify_installed_against_wheel",
        lambda name, wheel_path, metadata: {
            "wheel_sha256": "a" * 64,
            "problems": ["x.py: bytes differ"],
        },
    )
    with pytest.raises(ReceiptError, match="differs"):
        _build(dataset_file, wheel_paths={"policyengine-uk": Path("uk.whl")})


@pytest.mark.parametrize("content", [b"not a zip", None])
def test_unreadable_wheels_raise_receipt_errors(tmp_path, content):
    """Round-3 review R4: no ValueError or BadZipFile escapes."""

    import zipfile

    wheel = tmp_path / "policyengine_uk-0-py3-none-any.whl"
    if content is not None:
        wheel.write_bytes(content)
    else:
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("x.dist-info/RECORD", "a.py,,\na.py,,\n")
    with pytest.raises(ReceiptError, match="cannot be verified"):
        installed_package_identity("policyengine-uk", wheel_path=wheel)


def _direct_url_identity(monkeypatch, direct_url):
    # These metadata-only fixtures do not load a country package.
    monkeypatch.delitem(sys.modules, "policyengine_uk", raising=False)

    class Distribution:
        version = INSTALLED_UK

        def read_text(self, name):
            assert name == "direct_url.json"
            return json.dumps(direct_url)

    fake = SimpleNamespace(
        version=lambda name: INSTALLED_UK, distribution=lambda name: Distribution()
    )
    monkeypatch.setattr(receipt_module, "metadata", fake)
    identity = installed_package_identity("policyengine-uk")
    return identity.wheel_sha256, identity.wheel_sha256_evidence


def test_installer_archive_hash_is_read_from_direct_url(monkeypatch):
    archive = {"hashes": {"sha256": "b" * 64}}
    assert _direct_url_identity(
        monkeypatch, {"url": "file:///w-1-py3-none-any.whl", "archive_info": archive}
    ) == ("b" * 64, "installer_archive_hash")
    assert _direct_url_identity(
        monkeypatch,
        {
            "url": "https://files.example/w-1-py3-none-any.whl#sha256=" + "b" * 64,
            "archive_info": {"hash": "sha256=" + "b" * 64},
        },
    ) == ("b" * 64, "installer_archive_hash")


@pytest.mark.parametrize(
    "direct_url",
    [
        {"url": "file:///w-1.tar.gz", "archive_info": {"hashes": {"sha256": "b" * 64}}},
        {"url": "https://x/w-1.zip", "archive_info": {"hashes": {"sha256": "b" * 64}}},
        {"url": "file:///src/w", "dir_info": {"editable": True}},
    ],
    ids=["sdist", "zip", "directory"],
)
def test_only_a_wheel_archive_hash_is_recorded(monkeypatch, direct_url):
    """Round-4 review M6: a source archive's hash is not a wheel hash."""

    assert _direct_url_identity(monkeypatch, direct_url) == (None, None)


def test_callers_cannot_supply_the_versions_a_receipt_records(dataset_file):
    """Round-2 review N5: there is no public way to inject package metadata."""

    for function in (build_execution_receipt, installed_package_identity):
        assert "metadata_module" not in inspect.signature(function).parameters
    with pytest.raises(TypeError):
        _build(dataset_file, metadata_module=SimpleNamespace())


def test_hash_without_evidence_is_refused():
    with pytest.raises(ValidationError):
        receipt_module.PackageIdentity(name="x", version="1", wheel_sha256="c" * 64)


@pytest.mark.parametrize("package", list(receipt_module.UK_PACKAGES.values()))
@pytest.mark.parametrize("origin", ["directory", "editable", "vcs", "archive"])
def test_install_origin_controls_certification(
    dataset_file, monkeypatch, package, origin
):
    direct_url = {"url": "file:///package"}
    if origin in ("directory", "editable"):
        direct_url["dir_info"] = {"editable": origin == "editable"}
    elif origin == "vcs":
        direct_url["vcs_info"] = {"vcs": "git", "commit_id": "a" * 40}
    else:
        direct_url["archive_info"] = {}
    monkeypatch.setattr(
        receipt_module,
        "_read_direct_url",
        lambda name: direct_url if name == package else None,
    )
    receipt = _build(dataset_file)
    identity = next(
        item
        for item in (receipt.wrapper, receipt.model, receipt.core)
        if item.name == package
    )
    assert identity.install_origin == origin
    assert identity.wheel_sha256 is None
    assert receipt.certification_status == (
        "certified" if origin == "archive" else "uncertified"
    )
    assert (receipt.certificate is not None) == (origin == "archive")


@pytest.mark.real_install
@pytest.mark.skipif(
    not _this_checkout_is_the_installed_policyengine(),
    reason="policyengine here is not an editable install of this checkout "
    "(CI installs a released policyengine over it)",
)
def test_real_editable_install_is_recorded_and_uncertified(tmp_path):
    identity = installed_package_identity("policyengine")
    assert identity.install_origin == "editable"
    path = tmp_path / "data.h5"
    path.write_bytes(b"dataset bytes")
    receipt = _build(path)
    assert receipt.wrapper.install_origin == "editable"
    assert receipt.certification_status == "uncertified"
    assert receipt.certificate is None
    assert verify_certificate(receipt, _bundle_for(path.read_bytes())) == [
        "the receipt is uncertified"
    ]


def _loaded_distribution(tmp_path, monkeypatch, package, *, direct_url=None):
    import_name = package.replace("-", "_")
    version = metadata.version(package)
    root = tmp_path / "installed"
    source = root / import_name / "__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n")
    directory = root / f"{import_name}-{version}.dist-info"
    directory.mkdir()
    (directory / "METADATA").write_text(f"Name: {package}\nVersion: {version}\n")
    (directory / "RECORD").write_text(f"{import_name}/__init__.py,,\n")
    if direct_url is not None:
        (directory / "direct_url.json").write_text(json.dumps(direct_url))
    distribution = metadata.Distribution.at(directory)
    original = metadata.distribution
    monkeypatch.setattr(
        receipt_module.metadata,
        "distribution",
        lambda name: distribution if name == package else original(name),
    )
    module = SimpleNamespace(__file__=str(source))
    monkeypatch.setitem(sys.modules, import_name, module)
    return distribution, module, source, directory


@pytest.mark.parametrize("package", list(receipt_module.UK_PACKAGES.values()))
@pytest.mark.parametrize("archive", [False, True])
def test_loaded_index_and_archive_packages_match_record(
    tmp_path, monkeypatch, package, archive
):
    direct_url = {"url": "file:///package.whl", "archive_info": {}} if archive else None
    _, _, source, _ = _loaded_distribution(
        tmp_path, monkeypatch, package, direct_url=direct_url
    )
    identity = installed_package_identity(package)
    assert identity.name == package
    assert identity.install_origin == ("archive" if archive else None)
    assert source.is_file()


@pytest.mark.parametrize("package", list(receipt_module.UK_PACKAGES.values()))
@pytest.mark.parametrize("archive", [False, True])
def test_loaded_checkout_cannot_name_an_index_or_archive_install(
    tmp_path, monkeypatch, package, archive
):
    direct_url = {"url": "file:///package.whl", "archive_info": {}} if archive else None
    _, module, source, _ = _loaded_distribution(
        tmp_path, monkeypatch, package, direct_url=direct_url
    )
    checkout = tmp_path / "checkout" / source.parent.name / "__init__.py"
    checkout.parent.mkdir(parents=True)
    checkout.write_text("VALUE = 2\n")
    module.__file__ = str(checkout)
    with pytest.raises(ReceiptError) as error:
        installed_package_identity(package)
    message = str(error.value)
    assert package in message and str(checkout) in message
    assert (
        "installed distribution" in message
        and "cannot name the code that ran" in message
    )


@pytest.mark.parametrize("package", list(receipt_module.UK_PACKAGES.values()))
def test_verified_wheel_cannot_name_another_loaded_checkout(
    tmp_path, monkeypatch, package
):
    from policyengine.provenance import wheels

    _, module, _, _ = _loaded_distribution(tmp_path, monkeypatch, package)
    module.__file__ = str(tmp_path / "checkout" / "__init__.py")
    verified = []
    monkeypatch.setattr(
        wheels,
        "verify_installed_against_wheel",
        lambda *args, **kwargs: verified.append(args),
    )
    with pytest.raises(ReceiptError, match="cannot name the code that ran"):
        installed_package_identity(package, wheel_path=tmp_path / "package.whl")
    assert verified == []


@pytest.mark.parametrize("builder", ["direct", "microsimulation"])
@pytest.mark.parametrize("package", list(receipt_module.UK_PACKAGES.values()))
@pytest.mark.parametrize("dir_info", [None, {}, {"editable": False}])
def test_receipt_builders_refuse_loaded_checkout(
    dataset_file, tmp_path, monkeypatch, builder, package, dir_info
):
    bundle = _bundle_for(dataset_file.read_bytes())
    if builder == "microsimulation":
        simulation = _managed_simulation(dataset_file, bundle)
    direct_url = (
        {"url": (tmp_path / "checkout").as_uri(), "dir_info": dir_info}
        if dir_info is not None
        else None
    )
    _, module, _, _ = _loaded_distribution(
        tmp_path, monkeypatch, package, direct_url=direct_url
    )
    module.__file__ = str(tmp_path / "checkout" / "__init__.py")
    with pytest.raises(ReceiptError, match="cannot name the code that ran"):
        if builder == "direct":
            _build(dataset_file)
        else:
            _microsimulation_receipt(simulation, bundle)


@pytest.mark.parametrize("package", list(receipt_module.UK_PACKAGES.values()))
@pytest.mark.parametrize("layout", ["", "src"])
def test_loaded_editable_packages_are_under_the_direct_url(
    tmp_path, monkeypatch, package, layout
):
    checkout = tmp_path / "checkout with spaces"
    direct_url = {"url": checkout.as_uri(), "dir_info": {"editable": True}}
    _, module, _, _ = _loaded_distribution(
        tmp_path, monkeypatch, package, direct_url=direct_url
    )
    source = checkout / layout / package.replace("-", "_") / "__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n")
    module.__file__ = str(source)
    identity = installed_package_identity(package)
    assert identity.install_origin == "editable"


@pytest.mark.parametrize("package", list(receipt_module.UK_PACKAGES.values()))
def test_loaded_editable_packages_refuse_another_checkout(
    tmp_path, monkeypatch, package
):
    checkout = tmp_path / "checkout"
    direct_url = {"url": checkout.as_uri(), "dir_info": {"editable": True}}
    _loaded_distribution(tmp_path, monkeypatch, package, direct_url=direct_url)
    with pytest.raises(
        ReceiptError, match="cannot name the code that ran.*expected code under"
    ):
        installed_package_identity(package)


@pytest.mark.parametrize("package", list(receipt_module.UK_PACKAGES.values()))
@pytest.mark.parametrize("dir_info", [{}, {"editable": False}])
def test_loaded_noneditable_directory_packages_match_record(
    tmp_path, monkeypatch, package, dir_info
):
    direct_url = {"url": (tmp_path / "checkout").as_uri(), "dir_info": dir_info}
    _loaded_distribution(tmp_path, monkeypatch, package, direct_url=direct_url)
    assert installed_package_identity(package).install_origin == "directory"


@pytest.mark.parametrize("package", list(receipt_module.UK_PACKAGES.values()))
@pytest.mark.parametrize("dir_info", [{}, {"editable": False}])
@pytest.mark.parametrize("layout", ["", "src"])
def test_loaded_noneditable_directory_packages_refuse_source_checkout(
    tmp_path, monkeypatch, package, dir_info, layout
):
    from policyengine.provenance import wheels

    checkout = tmp_path / "checkout with spaces"
    direct_url = {"url": checkout.as_uri(), "dir_info": dir_info}
    _, module, _, _ = _loaded_distribution(
        tmp_path, monkeypatch, package, direct_url=direct_url
    )
    source = checkout / layout / package.replace("-", "_") / "__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 2\n")
    module.__file__ = str(source)
    verified = []
    monkeypatch.setattr(
        wheels,
        "verify_installed_against_wheel",
        lambda *args, **kwargs: verified.append(args),
    )
    with pytest.raises(
        ReceiptError, match="cannot name the code that ran.*from RECORD"
    ):
        installed_package_identity(package, wheel_path=tmp_path / "package.whl")
    assert verified == []


@pytest.mark.parametrize("dir_info", [{}, {"editable": False}])
def test_loaded_noneditable_directory_packages_require_the_exact_record_path(
    tmp_path, monkeypatch, dir_info
):
    direct_url = {"url": (tmp_path / "checkout").as_uri(), "dir_info": dir_info}
    _, module, source, _ = _loaded_distribution(
        tmp_path, monkeypatch, "policyengine", direct_url=direct_url
    )
    other = source.parent.parent / "other" / "__init__.py"
    other.parent.mkdir()
    other.write_text("VALUE = 2\n")
    module.__file__ = str(other)
    with pytest.raises(
        ReceiptError, match="cannot name the code that ran.*from RECORD"
    ):
        installed_package_identity("policyengine")


def test_loaded_directory_origin_requires_path_components(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    _, module, _, _ = _loaded_distribution(
        tmp_path,
        monkeypatch,
        "policyengine",
        direct_url={"url": checkout.as_uri(), "dir_info": {"editable": True}},
    )
    module.__file__ = str(tmp_path / "checkout-copy" / "policyengine" / "__init__.py")
    with pytest.raises(ReceiptError, match="cannot name the code that ran"):
        installed_package_identity("policyengine")


@pytest.mark.parametrize("package", list(receipt_module.UK_PACKAGES.values()))
def test_loaded_package_origin_compares_real_paths(tmp_path, monkeypatch, package):
    _, module, source, _ = _loaded_distribution(tmp_path, monkeypatch, package)
    link = tmp_path / "linked-package"
    link.symlink_to(source.parent, target_is_directory=True)
    module.__file__ = str(link / "__init__.py")
    assert installed_package_identity(package).name == package


def test_loaded_package_origin_resolves_record_paths(tmp_path, monkeypatch):
    distribution, _, source, _ = _loaded_distribution(
        tmp_path, monkeypatch, "policyengine"
    )
    link = tmp_path / "linked-installation"
    link.symlink_to(source.parent.parent, target_is_directory=True)
    monkeypatch.setattr(distribution, "locate_file", lambda entry: link / entry)
    assert installed_package_identity("policyengine").name == "policyengine"


def test_loaded_editable_origin_resolves_its_url(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    link = tmp_path / "linked-checkout"
    link.symlink_to(checkout, target_is_directory=True)
    _, module, _, _ = _loaded_distribution(
        tmp_path,
        monkeypatch,
        "policyengine",
        direct_url={"url": link.as_uri(), "dir_info": {"editable": True}},
    )
    module.__file__ = str(checkout / "src" / "policyengine" / "__init__.py")
    assert installed_package_identity("policyengine").install_origin == "editable"


@pytest.mark.parametrize("package", list(receipt_module.UK_PACKAGES.values()))
def test_unloaded_packages_have_no_source_to_compare(tmp_path, monkeypatch, package):
    _, _, _, directory = _loaded_distribution(tmp_path, monkeypatch, package)
    (directory / "RECORD").unlink()
    monkeypatch.delitem(sys.modules, package.replace("-", "_"))
    assert installed_package_identity(package).name == package


def test_package_identity_remains_available_for_other_distributions(monkeypatch):
    distribution = SimpleNamespace(version="1", read_text=lambda name: None)
    original = metadata.distribution
    monkeypatch.setattr(
        metadata,
        "distribution",
        lambda name: distribution if name == "example" else original(name),
    )
    monkeypatch.setitem(sys.modules, "example", SimpleNamespace(__file__="example.py"))
    assert installed_package_identity("example").version == "1"


@pytest.mark.parametrize(
    "record",
    [
        None,
        "",
        "other.py,,\n",
        "policyengine/__init__.py,\n",
        '"unclosed,,\n',
        'policyengine/__init__.py,"hash","3"junk\n',
    ],
)
def test_loaded_package_requires_its_record_entry(tmp_path, monkeypatch, record):
    _, _, _, directory = _loaded_distribution(tmp_path, monkeypatch, "policyengine")
    if record is None:
        (directory / "RECORD").unlink()
    else:
        (directory / "RECORD").write_text(record)
    with pytest.raises(ReceiptError, match="cannot name the code that ran"):
        installed_package_identity("policyengine")


@pytest.mark.parametrize("loaded_file", [None, "", 7])
def test_loaded_package_requires_a_source_file(tmp_path, monkeypatch, loaded_file):
    _, module, _, _ = _loaded_distribution(tmp_path, monkeypatch, "policyengine")
    module.__file__ = loaded_file
    with pytest.raises(ReceiptError, match="loaded package has no source file"):
        installed_package_identity("policyengine")


def test_loaded_package_refuses_an_unreadable_record(tmp_path, monkeypatch):
    distribution, _, _, _ = _loaded_distribution(tmp_path, monkeypatch, "policyengine")
    original = distribution.read_text

    def read_text(name):
        if name == "RECORD":
            raise OSError("unreadable")
        return original(name)

    monkeypatch.setattr(distribution, "read_text", read_text)
    with pytest.raises(ReceiptError, match="source location cannot be read"):
        installed_package_identity("policyengine")


@pytest.mark.parametrize("url", ["https://localhost", "file://other-host"])
def test_loaded_editable_origin_requires_a_local_file_url(tmp_path, monkeypatch, url):
    _loaded_distribution(
        tmp_path,
        monkeypatch,
        "policyengine",
        direct_url={
            "url": url + str(tmp_path / "installed"),
            "dir_info": {"editable": True},
        },
    )
    with pytest.raises(ReceiptError, match="install directory is not local"):
        installed_package_identity("policyengine")


@pytest.mark.parametrize("role", ["wrapper", "model", "core"])
@pytest.mark.parametrize("origin", ["directory", "editable", "vcs"])
@pytest.mark.parametrize("archive_hash", [False, True])
def test_certified_model_and_verification_refuse_unverified_origins(
    certified_receipt, dataset_file, role, origin, archive_hash
):
    payload = certified_receipt.model_dump()
    payload[role]["install_origin"] = origin
    if archive_hash:
        payload[role].update(
            wheel_sha256="b" * 64, wheel_sha256_evidence="installer_archive_hash"
        )
    reason = (
        "an editable install's wheel does not hold the source that runs"
        if origin == "editable"
        else "installed_record_verified"
    )
    with pytest.raises(ValidationError, match=reason):
        ExecutionReceipt.model_validate(payload)
    package = type(getattr(certified_receipt, role)).model_validate(payload[role])
    forged = certified_receipt.model_copy(update={role: package})
    problems = verify_certificate(forged, _bundle_for(dataset_file.read_bytes()))
    assert len(problems) == 1
    assert package.name in problems[0] and reason in problems[0]


@pytest.mark.parametrize("role", ["wrapper", "model", "core"])
def test_certified_model_and_verification_refuse_verified_editable_installs(
    certified_receipt, dataset_file, role
):
    payload = certified_receipt.model_dump()
    payload[role].update(
        install_origin="editable",
        wheel_sha256="b" * 64,
        wheel_sha256_evidence="installed_record_verified",
    )
    with pytest.raises(ValidationError, match="editable install"):
        ExecutionReceipt.model_validate(payload)
    package = type(getattr(certified_receipt, role)).model_validate(payload[role])
    forged = certified_receipt.model_copy(update={role: package})
    problems = verify_certificate(forged, _bundle_for(dataset_file.read_bytes()))
    assert problems == [
        f"{package.name} installed from editable: an editable install's wheel "
        "does not hold the source that runs"
    ]


@pytest.mark.parametrize("role", ["wrapper", "model", "core"])
@pytest.mark.parametrize("origin", ["directory", "editable", "vcs"])
def test_verified_origin_can_be_certified_unless_editable(
    dataset_file, monkeypatch, role, origin
):
    direct_url = {"url": "file:///source"}
    if origin == "vcs":
        direct_url["vcs_info"] = {"vcs": "git", "commit_id": "a" * 40}
    else:
        direct_url["dir_info"] = {"editable": origin == "editable"}
    package = receipt_module.UK_PACKAGES[role]
    monkeypatch.setattr(
        receipt_module,
        "_read_direct_url",
        lambda name: direct_url if name == package else None,
    )
    monkeypatch.setattr(
        "policyengine.provenance.wheels.verify_installed_against_wheel",
        lambda name, wheel_path, metadata: {"wheel_sha256": "a" * 64, "problems": []},
    )
    receipt = _build(dataset_file, wheel_paths={package: Path("package.whl")})
    assert getattr(receipt, role).install_origin == origin
    assert getattr(receipt, role).wheel_sha256_evidence == "installed_record_verified"
    if origin == "editable":
        assert receipt.certification_status == "uncertified"
        assert receipt.certificate is None
    else:
        assert receipt.certification_status == "certified"
        assert verify_certificate(receipt, _bundle_for(dataset_file.read_bytes())) == []


@pytest.mark.parametrize(
    "text",
    [
        "",
        "{",
        "[]",
        "null",
        "{}",
        '{"url": "file:///x"}',
        '{"archive_info": {}}',
        '{"url": "x", "dir_info": null}',
        '{"url": "x", "dir_info": {"editable": "yes"}}',
        '{"url": "x", "dir_info": {}, "archive_info": {}}',
        '{"url": "", "archive_info": {}}',
        '{"url": "file:///source.zip", "archive_info": {"hashes": 42}}',
        '{"url": "file:///source.zip", "archive_info": {"hash": true}}',
        '{"url": "file:///package.whl", "archive_info": {"hashes": {"sha256": 42}}}',
    ],
)
def test_malformed_direct_url_is_refused(monkeypatch, text):
    monkeypatch.setattr(
        receipt_module.metadata,
        "distribution",
        lambda name: SimpleNamespace(
            version=INSTALLED_WRAPPER, read_text=lambda filename: text
        ),
    )
    with pytest.raises(ReceiptError, match="policyengine.*direct_url.json.*malformed"):
        installed_package_identity("policyengine")


def test_unreadable_direct_url_is_refused(monkeypatch):
    def read_text(filename):
        raise OSError("unreadable")

    monkeypatch.setattr(
        receipt_module.metadata,
        "distribution",
        lambda name: SimpleNamespace(version=INSTALLED_WRAPPER, read_text=read_text),
    )
    with pytest.raises(ReceiptError, match="direct_url.json cannot be read"):
        installed_package_identity("policyengine")


# --- Digests ----------------------------------------------------------------------


def test_json_round_trip_preserves_receipt_and_digests(certified_receipt):
    for text in (
        certified_receipt.model_dump_json(),
        certified_receipt.to_canonical_json(),
    ):
        parsed = ExecutionReceipt.model_validate_json(text)
        assert parsed == certified_receipt
        assert parsed.receipt_sha256 == certified_receipt.receipt_sha256
        assert (
            parsed.execution_identity_sha256
            == certified_receipt.execution_identity_sha256
        )


def test_null_and_omitted_fields_digest_identically(certified_receipt):
    with_nulls = certified_receipt.model_dump(mode="json")
    assert with_nulls["outputs_sha256"] is None
    assert (
        ExecutionReceipt.model_validate(with_nulls).receipt_sha256
        == ExecutionReceipt.model_validate(
            certified_receipt.canonical_payload()
        ).receipt_sha256
    )
    assert content_sha256({"a": 1, "b": None}) == content_sha256({"a": 1})
    assert content_sha256([None, {"a": None}]) == canonical_sha256([None, {}])


@pytest.mark.usefixtures("index_installs")
def test_execution_identity_ignores_how_the_builder_was_called(tmp_path, monkeypatch):
    from policyengine.provenance import certification

    dataset = tmp_path / "data.h5"
    dataset.write_bytes(b"identity bytes")
    bundle = _bundle_for(dataset.read_bytes())
    packaged = tmp_path / "bundle"
    packaged.mkdir()
    (packaged / "manifest.json").write_text(json.dumps(bundle))
    (packaged / "uk.trace.tro.jsonld").write_bytes(
        (BUNDLE_DIR / "uk.trace.tro.jsonld").read_bytes()
    )
    monkeypatch.setattr(
        certification, "default_bundle_source_path", lambda: packaged / "manifest.json"
    )
    packaged_receipt = build_execution_receipt(
        country_id="uk",
        dataset_path=dataset,
        years=[2026],
        reform=CURRENT_LAW,
        baseline=CURRENT_LAW,
    )
    supplied = _build(dataset, bundle, qualification_receipt_sha256="9" * 64)
    assert packaged_receipt.certificate.tro_composition_fingerprint is not None
    assert supplied.certificate.tro_composition_fingerprint is None
    assert (
        packaged_receipt.execution_identity_sha256 == supplied.execution_identity_sha256
    )


REFORM_PAYLOADS = st.dictionaries(
    st.sampled_from(
        [
            "gov.hmrc.income_tax.rates.uk[0].rate",
            "gov.hmrc.income_tax.allowances.personal_allowance.amount",
            "gov.dwp.universal_credit.standard_allowance.amount.SINGLE_OLD",
        ]
    ),
    st.dictionaries(
        st.sampled_from(["2027", "2027-04-06", "2027-04-06.2028-04-05"]),
        st.floats(min_value=0, max_value=1e6, allow_nan=False),
        min_size=1,
        max_size=3,
    ),
    min_size=1,
    max_size=3,
)


@settings(max_examples=60, deadline=None)
@given(
    payload=REFORM_PAYLOADS,
    years=st.lists(st.integers(2024, 2035), min_size=1, max_size=6),
    outputs=st.dictionaries(
        st.sampled_from(["budgetary_impact", "poverty_rate", "gini"]),
        st.floats(allow_nan=False, allow_infinity=False),
        max_size=3,
    ),
    label=st.text(max_size=10),
)
def test_digest_separation(tmp_path_factory, payload, years, outputs, label):
    directory = tmp_path_factory.mktemp("receipt")
    dataset = directory / "data.h5"
    dataset.write_bytes(b"same bytes")
    base = _build(dataset)
    varied = _build(
        dataset,
        years=years,
        reform=reform_identity(
            payload, "policyengine.reform_dict/v1", name=label or None
        ),
        outputs=outputs or None,
        ci_run_url="https://github.com/o/r/actions/runs/1",
    )
    assert varied.execution_identity_sha256 == base.execution_identity_sha256
    assert (
        varied.model_copy(update={"runtime": None}).receipt_sha256
        == varied.receipt_sha256
    )
    renamed = varied.model_copy(
        update={"reform": varied.reform.model_copy(update={"name": "other label"})}
    )
    assert renamed.receipt_sha256 == varied.receipt_sha256
    assert varied.receipt_sha256 != base.receipt_sha256


@settings(max_examples=60, deadline=None)
@given(payload=REFORM_PAYLOADS, random=st.randoms())
def test_reform_digest_ignores_member_order_but_not_representation(payload, random):
    items = list(payload.items())
    random.shuffle(items)
    shuffled = {key: dict(reversed(list(value.items()))) for key, value in items}
    a = reform_identity(payload, "policyengine.reform_dict/v1")
    assert (
        a.reform_sha256
        == reform_identity(shuffled, "policyengine.reform_dict/v1").reform_sha256
    )
    assert (
        a.reform_sha256
        != reform_identity(payload, "policyengine-uk.reform_dict/v1").reform_sha256
    )


class Rate(enum.IntEnum):
    BASIC = 20


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (np.int64(1234), 1234),
        (np.float64(6.1e9), 6.1e9),
        (np.bool_(True), True),
        (Rate.BASIC, 20),
        (datetime.date(2027, 4, 6), "2027-04-06"),
        ({2027: 0.21}, {"2027": 0.21}),
        ((1, 2), [1, 2]),
    ],
)
def test_strict_json_converts_exact_values(value, expected):
    converted = strict_json_value(value)
    assert converted == expected and type(converted) is type(expected)


@pytest.mark.parametrize(
    "value",
    [
        {1, 2},
        decimal.Decimal("1.5"),
        b"bytes",
        np.arange(2000),
        float("nan"),
        np.float64("inf"),
        {2027: 0.21, "2027": 0.25},
        {(1, 2): 3},
        datetime.datetime(2027, 4, 6, 12, 0),
        object(),
    ],
)
def test_strict_json_refuses_values_without_one_json_form(value):
    with pytest.raises(ReceiptError):
        strict_json_value(value)


@pytest.mark.parametrize(
    "value",
    [
        np.ma.masked,
        np.ma.array(42, mask=True),
        np.ma.array(42.0, mask=False),
        np.array(1.5),  # a 0-d array, not a scalar
        np.complex128(1),
        np.datetime64("2027-04-06"),
        np.zeros(1, dtype=[("a", "i4")])[0],  # a structured scalar
    ],
    ids=[
        "masked",
        "masked-42",
        "unmasked-0d",
        "0d-array",
        "complex",
        "datetime",
        "void",
    ],
)
def test_strict_json_refuses_numpy_values_that_are_not_plain_scalars(value):
    """Round-4 review M7: a masked value never becomes an ordinary number."""

    with pytest.raises(ReceiptError):
        strict_json_value(value)
    with pytest.raises(ReceiptError):
        content_sha256({"total": value})


def test_strict_json_unwraps_numpy_scalars_exactly():
    assert strict_json_value([np.int64(7), np.float32(0.5), np.bool_(True)]) == [
        7,
        0.5,
        True,
    ]


def test_strict_json_refuses_rather_than_overflowing_the_stack():
    """Round-2 review N8: longdouble and deep nesting raise ReceiptError."""

    longdouble = np.longdouble("0.1")
    if isinstance(longdouble.item(), float):  # pragma: no cover - platform
        assert strict_json_value(longdouble) == longdouble.item()
    else:
        with pytest.raises(ReceiptError):
            strict_json_value(longdouble)
    nested: list = []
    for _ in range(sys.getrecursionlimit() + 100):
        nested = [nested]
    with pytest.raises(ReceiptError):
        strict_json_value(nested)
    with pytest.raises(ReceiptError):
        content_sha256(nested)
    with pytest.raises(ReceiptError):
        content_sha256({"total": 2**53})


def test_numpy_scalars_digest_like_the_published_json():
    assert content_sha256({"budgetary_impact": np.int64(1234)}) == content_sha256(
        {"budgetary_impact": 1234}
    )
    assert content_sha256({"budgetary_impact": np.int64(1234)}) != content_sha256(
        {"budgetary_impact": "1234"}
    )


def test_reform_identity_accepts_only_json_payloads():
    assert reform_identity(None).kind == "current_law"
    assert reform_identity({}).kind == "current_law"
    with pytest.raises(ReceiptError):
        reform_identity({"a": {"2027": 1}})
    for bad in ("gov.x", object(), SimpleNamespace(parameter_changes={"a": 1})):
        with pytest.raises(ReceiptError):
            reform_identity(bad, "policyengine.reform_dict/v1")
    with pytest.raises(ReceiptError, match="scenario_reform_identity"):
        reform_identity({"a": 1}, "policyengine-uk.scenario/v1")
    with pytest.raises(ValidationError):
        ReformIdentity(kind="current_law", reform_sha256="0" * 64)
    with pytest.raises(ValidationError):
        ReformIdentity(kind="reform", representation="policyengine.reform_dict/v1")
    with pytest.raises(ValidationError):
        ReformIdentity(kind="current_law", binding="code_revision")


# --- Scenario binding -------------------------------------------------------------


def _scenario(parameter_changes=None, simulation_modifier=None, early=False):
    return SimpleNamespace(
        parameter_changes=parameter_changes,
        simulation_modifier=simulation_modifier,
        applied_before_data_load=early,
    )


class _ReformClass:
    """Stands in for a policyengine-core Reform subclass."""

    parameter_changes = None


@pytest.mark.parametrize(
    "value",
    [
        {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027": 0.21}},
        [{"parameter": "gov.x", "value": 1}],
        "gov.hmrc.income_tax.rates.uk[0].rate",
        _ReformClass,
        SimpleNamespace(parameter_values=[], name="policyengine.py Policy"),
        SimpleNamespace(parameter_changes={"a": {"2027": 1}}),
        _scenario(early="yes"),
        _scenario(parameter_changes=[("a", 1)]),
        _scenario(simulation_modifier="raise_basic_rate"),
    ],
    ids=[
        "reform dict",
        "list",
        "string",
        "reform class",
        "policy",
        "partial scenario",
        "non-bool timing",
        "non-mapping changes",
        "non-callable modifier",
    ],
)
def test_objects_that_are_not_scenarios_are_refused_not_read_as_current_law(value):
    """Round-2 review N6."""

    with pytest.raises(ReceiptError):
        scenario_reform_identity(value, code_revision=REVISION)


def test_real_scenarios_are_accepted():
    from policyengine_uk.utils.scenario import Scenario

    changes = {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027-04-06": 0.21}}
    assert scenario_reform_identity(Scenario()).kind == "current_law"
    assert scenario_reform_identity(
        Scenario(parameter_changes=changes)
    ).reform_sha256 == (scenario_reform_identity(_scenario(changes)).reform_sha256)
    bound = scenario_reform_identity(
        Scenario(simulation_modifier=receipt_modifiers.raise_basic_rate),
        code_revision=REVISION,
    )
    assert bound.binding == "code_revision"


def test_a_null_in_a_reform_is_part_of_its_digest():
    """Round-5 review: policyengine-uk reads {"2027": None} unlike {}."""

    removes = reform_identity(
        {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027": None}},
        "policyengine-uk.reform_dict/v1",
    )
    keeps = reform_identity(
        {"gov.hmrc.income_tax.rates.uk[0].rate": {}},
        "policyengine-uk.reform_dict/v1",
    )
    assert removes.reform_sha256 != keeps.reform_sha256
    assert removes.reform_sha256 == canonical_sha256(
        {
            "representation": "policyengine-uk.reform_dict/v1",
            "payload": {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027": None}},
        }
    )


def test_parameter_scenarios_are_bound_by_content():
    changes = {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027-04-06": 0.21}}
    identity = scenario_reform_identity(_scenario(changes))
    assert identity.binding == "content"
    # Reform payloads keep their nulls (canonical_sha256, not content_sha256).
    assert identity.reform_sha256 == canonical_sha256(
        {
            "representation": "policyengine-uk.scenario/v1",
            "payload": {
                "applied_before_data_load": False,
                "parameter_changes": changes,
                "simulation_modifier": None,
            },
        }
    )
    assert (
        scenario_reform_identity(_scenario(changes, early=True)).reform_sha256
        != identity.reform_sha256
    )
    assert scenario_reform_identity(_scenario()).kind == "current_law"


def test_module_level_modifiers_are_bound_by_code_and_revision():
    with pytest.raises(ReceiptError):
        scenario_reform_identity(
            _scenario(simulation_modifier=receipt_modifiers.raise_basic_rate)
        )
    basic = scenario_reform_identity(
        _scenario(simulation_modifier=receipt_modifiers.raise_basic_rate),
        code_revision=REVISION,
    )
    higher = scenario_reform_identity(
        _scenario(simulation_modifier=receipt_modifiers.raise_higher_rate),
        code_revision=REVISION,
    )
    moved = scenario_reform_identity(
        _scenario(simulation_modifier=receipt_modifiers.raise_basic_rate),
        code_revision={**REVISION, "git_sha": "b" * 40},
    )
    assert basic.binding == "code_revision"
    assert len({basic.reform_sha256, higher.reform_sha256, moved.reform_sha256}) == 3


@pytest.mark.parametrize(
    "modifier",
    [
        receipt_unbindable_modifiers.make_modifier(0.21),
        lambda simulation: None,
        functools.partial(receipt_modifiers.raise_basic_rate),
        receipt_unbindable_modifiers.Measure(0.21).apply,
        print,
    ],
    ids=["closure", "lambda", "partial", "bound method", "builtin"],
)
def test_modifiers_whose_behaviour_the_digest_cannot_bind_are_refused(modifier):
    with pytest.raises(ReceiptError):
        scenario_reform_identity(
            _scenario(simulation_modifier=modifier), code_revision=REVISION
        )


@pytest.mark.parametrize(
    "revision",
    [
        None,
        {},
        {"repository": "PolicyEngine/x"},
        {"repository": "", "git_sha": "a" * 40},
        {"repository": "PolicyEngine/x", "git_sha": "main"},
        {"repository": "PolicyEngine/x", "git_sha": "A" * 40},
    ],
)
def test_modifiers_need_a_full_code_revision(revision):
    with pytest.raises(ReceiptError):
        scenario_reform_identity(
            _scenario(simulation_modifier=receipt_modifiers.raise_basic_rate),
            code_revision=revision,
        )


MEASURE_SOURCE = """
RATE = {rate}


def raise_rate(simulation):
    simulation.rate = RATE
"""


def _import_measures(directory: Path, name: str, rate: float = 0.21):
    """Import a measures module from ``directory`` as top-level ``name``."""

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.py"
    path.write_text(MEASURE_SOURCE.format(rate=rate))
    linecache.checkcache(str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, path


def _measure_identity(module):
    return scenario_reform_identity(
        _scenario(simulation_modifier=module.raise_rate), code_revision=REVISION
    )


@pytest.mark.parametrize("role", ["reform", "baseline"])
@pytest.mark.parametrize("managed", [False, True])
@pytest.mark.parametrize("change", ["reassign", "memo"])
def test_builder_rechecks_modifier_after_the_run(
    dataset_file, tmp_path, role, managed, change
):
    name = "w4_receipt_r10_recheck"
    source = (
        "CACHE = {}\n\n\ndef raise_rate(simulation):\n"
        "    CACHE[2027] = 0.30\n    simulation.rate = CACHE[2027]\n"
        if change == "memo"
        else MEASURE_SOURCE.format(rate=0.21)
    )
    try:
        module, _ = _import_source(tmp_path, name, source)
        identity = _measure_identity(module)
        if change == "reassign":
            module.RATE = 0.30
        simulation = SimpleNamespace()
        module.raise_rate(simulation)
        assert simulation.rate == 0.30
        identities = {"reform": CURRENT_LAW, "baseline": CURRENT_LAW, role: identity}
        with pytest.raises(
            ReceiptError, match="modifier changed after its identity was computed"
        ) as refused:
            if managed:
                bundle = _bundle_for(dataset_file.read_bytes())
                build_execution_receipt_for_microsimulation(
                    _managed_simulation(dataset_file, bundle),
                    years=[2026],
                    bundle=bundle,
                    **identities,
                )
            else:
                _build(dataset_file, **identities)
        assert ("CACHE" if change == "memo" else "RATE") in str(refused.value)
    finally:
        sys.modules.pop(name, None)


def test_unchanged_scenario_still_builds_after_a_run(dataset_file):
    scenario = _scenario(simulation_modifier=receipt_modifiers.raise_basic_rate_to)
    identity = scenario_reform_identity(scenario, code_revision=REVISION)
    simulation = SimpleNamespace()
    scenario.simulation_modifier(simulation)
    assert simulation.rate == 0.21
    receipt = _build(dataset_file, reform=identity, baseline=identity)
    assert receipt.reform == receipt.baseline == identity
    loaded = ReformIdentity.model_validate_json(identity.model_dump_json())
    from_loaded = _build(dataset_file, reform=loaded, baseline=loaded)
    assert receipt == from_loaded
    assert receipt.receipt_sha256 == from_loaded.receipt_sha256
    assert receipt.execution_identity_sha256 == from_loaded.execution_identity_sha256


@pytest.mark.parametrize(
    "field,value",
    [
        ("reform_sha256", "b" * 64),
        ("binding", "content"),
        ("representation", "policyengine.reform_dict/v1"),
        ("name", "updated"),
    ],
)
def test_copying_an_identity_with_updated_fields_does_not_bypass_recheck(
    dataset_file, field, value
):
    identity = scenario_reform_identity(
        _scenario(simulation_modifier=receipt_modifiers.raise_basic_rate),
        code_revision=REVISION,
    )
    changed = identity.model_copy(update={field: value})
    with pytest.raises(ReceiptError, match=f"{field} differs"):
        _build(dataset_file, reform=changed)


def test_loaded_identity_is_accepted_without_rechecking(dataset_file, tmp_path):
    name = "w4_receipt_r10_loaded"
    try:
        module, _ = _import_measures(tmp_path, name)
        identity = _measure_identity(module)
        loaded = ReformIdentity.model_validate(identity.model_dump())
        module.RATE = 0.30
        assert loaded._recompute_identity is None
        assert _build(dataset_file, reform=loaded).reform == identity
        with pytest.raises(ReceiptError, match="modifier changed"):
            _build(dataset_file, reform=identity)
    finally:
        sys.modules.pop(name, None)


@settings(max_examples=40, deadline=None)
@given(
    changes=st.none()
    | st.dictionaries(
        st.sampled_from(["rate", "cap"]), st.integers(0, 100), max_size=2
    ),
    modifier=st.booleans(),
    label=st.none() | st.text(max_size=20),
)
def test_identity_handle_preserves_equality_dump_and_digest(changes, modifier, label):
    scenario = _scenario(
        changes, receipt_modifiers.raise_basic_rate if modifier else None
    )
    identity = scenario_reform_identity(scenario, code_revision=REVISION, name=label)
    independently_bound = scenario_reform_identity(
        scenario, code_revision=REVISION, name=label
    )
    loaded = ReformIdentity.model_validate(identity.model_dump())
    loaded_json = ReformIdentity.model_validate_json(identity.model_dump_json())
    assert identity._recompute_identity is not independently_bound._recompute_identity
    for other in (independently_bound, loaded, loaded_json, identity.model_copy()):
        assert identity == other and other == identity
        assert identity.model_dump() == other.model_dump()
        assert identity.model_dump_json() == other.model_dump_json()
        assert content_sha256(identity.canonical_payload()) == content_sha256(
            other.canonical_payload()
        )
        assert identity.reform_sha256 == other.reform_sha256
    assert "_recompute_identity" not in identity.model_dump_json()
    assert "_recompute_identity" not in json.dumps(ReformIdentity.model_json_schema())


@pytest.mark.parametrize("before", [None, {"rate": 1}])
def test_scenario_parameter_changes_are_rechecked(dataset_file, before):
    scenario = _scenario(before)
    identity = scenario_reform_identity(scenario)
    scenario.parameter_changes = {"rate": 2}
    with pytest.raises(ReceiptError, match="reform_sha256.*differs"):
        _build(dataset_file, reform=identity)


def test_recheck_keeps_the_original_code_revision(dataset_file):
    revision = dict(REVISION)
    identity = scenario_reform_identity(
        _scenario(simulation_modifier=receipt_modifiers.raise_basic_rate),
        code_revision=revision,
    )
    revision["git_sha"] = "b" * 40
    assert _build(dataset_file, reform=identity).reform == identity


def test_modifier_digest_does_not_depend_on_the_checkout_location(tmp_path):
    """Round-2 review N2: the same code and revision give the same digest anywhere."""

    name = "w4_receipt_measures_location"
    try:
        first, _ = _import_measures(tmp_path / "checkout_a", name)
        a = _measure_identity(first)
        del sys.modules[name]
        second, _ = _import_measures(tmp_path / "elsewhere" / "checkout_b", name)
        b = _measure_identity(second)
        assert first.raise_rate.__code__.co_filename != (
            second.raise_rate.__code__.co_filename
        )
        assert a.reform_sha256 == b.reform_sha256
        del sys.modules[name]
        third, _ = _import_measures(tmp_path / "checkout_c", name, rate=0.99)
        # The function is unchanged, but its module's source is not.
        assert _measure_identity(third).reform_sha256 != a.reform_sha256
    finally:
        sys.modules.pop(name, None)


def test_a_modifier_edited_after_import_is_refused(tmp_path):
    name = "w4_receipt_measures_edited"
    try:
        module, path = _import_measures(tmp_path, name)
        _measure_identity(module)
        path.write_text(
            path.read_text().replace(
                "simulation.rate = RATE", "simulation.rate = RATE * 2  # edited"
            )
        )
        with pytest.raises(ReceiptError, match="no longer matches"):
            _measure_identity(module)
    finally:
        sys.modules.pop(name, None)


HELPER_SOURCE = """
RATE = 0.21
LABELS = ("basic", "higher")


def _helper(value):
    return value * 2


def raise_rate(simulation):
    simulation.rate = _helper(RATE)
    simulation.labels = list(label for label in LABELS if label)
"""


def _import_source(directory: Path, name: str, source: str):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.py"
    path.write_text(source)
    linecache.checkcache(str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, path


def _edit(path: Path, old: str, new: str) -> None:
    """Edit a file so linecache sees it even when the size is unchanged."""

    import os

    stat = path.stat()
    path.write_text(path.read_text().replace(old, new))
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10**9))


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("return value * 2", "return value * 3"),  # a helper the modifier calls
        ("RATE = 0.21", "RATE = 0.30"),  # a literal constant
        ('LABELS = ("basic", "higher")', 'LABELS = ("basic", "additional")'),
        ("value * 2", "value + 2"),  # an operator only: same names and constants
        ("label for label", "label.upper() for label"),  # nested code only
    ],
    ids=["helper", "constant", "tuple", "operator", "nested"],
)
def test_module_code_that_did_not_run_is_never_named(tmp_path, old, new):
    """Round-3 review R1: edits anywhere in the module after import are refused."""

    name = "w4_receipt_measures_module"
    try:
        module, path = _import_source(tmp_path, name, HELPER_SOURCE)
        _measure_identity(module)
        _edit(path, old, new)
        with pytest.raises(ReceiptError, match="no longer matches"):
            _measure_identity(module)
    finally:
        sys.modules.pop(name, None)


def test_a_constant_reassigned_at_run_time_is_refused(tmp_path):
    name = "w4_receipt_measures_runtime"
    try:
        module, _ = _import_source(tmp_path, name, HELPER_SOURCE)
        _measure_identity(module)
        module.RATE = 0.99
        with pytest.raises(ReceiptError, match="RATE is 0.99 at run time"):
            _measure_identity(module)
        module.RATE = 0.21
        _measure_identity(module)
    finally:
        sys.modules.pop(name, None)


def test_methods_are_refused_with_a_clear_reason():
    class Holder:
        @staticmethod
        def apply(simulation):
            simulation.rate = 0.21

    Holder.apply.__qualname__ = "Holder.apply"  # as if defined at module level
    with pytest.raises(ReceiptError, match="is a method"):
        scenario_reform_identity(
            _scenario(simulation_modifier=Holder.apply), code_revision=REVISION
        )


def test_a_function_with_foreign_globals_is_refused():
    import types

    forged = types.FunctionType(
        receipt_modifiers.raise_basic_rate.__code__, {}, "raise_basic_rate"
    )
    forged.__module__ = receipt_modifiers.__name__
    forged.__qualname__ = "raise_basic_rate"
    with pytest.raises(ReceiptError, match="does not belong to an imported module"):
        scenario_reform_identity(
            _scenario(simulation_modifier=forged), code_revision=REVISION
        )


def _identity(modifier):
    return scenario_reform_identity(
        _scenario(simulation_modifier=modifier), code_revision=REVISION
    ).reform_sha256


def test_literal_defaults_changed_at_run_time_are_refused():
    """Round-2 review N7: a default that differs from the source never binds."""

    to_rate = receipt_modifiers.raise_basic_rate_to
    from_year = receipt_modifiers.raise_basic_rate_from
    original = _identity(to_rate), _identity(from_year)
    try:
        to_rate.__defaults__ = (0.99,)
        with pytest.raises(ReceiptError, match="default arguments differ"):
            _identity(to_rate)
        # Any function in the module counts, not only the modifier.
        with pytest.raises(ReceiptError, match="raise_basic_rate_to's default"):
            _identity(receipt_modifiers.raise_basic_rate)
        to_rate.__defaults__ = (0.21,)
        from_year.__kwdefaults__ = {"start": 2030}
        with pytest.raises(ReceiptError, match="default arguments differ"):
            _identity(from_year)
    finally:
        to_rate.__defaults__ = (0.21,)
        from_year.__kwdefaults__ = {"start": 2027}
    assert (_identity(to_rate), _identity(from_year)) == original


COMPUTED_DEFAULT_SOURCE = """
import ast
import os
import re


def _helper(value, scale=ast.literal_eval(os.environ["W4_HELPER_DEFAULT"])):
    return value * scale


def raise_rate(simulation, *, rate=ast.literal_eval(os.environ["W4_RATE_DEFAULT"])):
    simulation.rate = _helper(rate)
"""


def _computed_default_identity(tmp_path, monkeypatch, rate, helper="2"):
    name = "w4_receipt_measures_computed_default"
    monkeypatch.setenv("W4_RATE_DEFAULT", rate)
    monkeypatch.setenv("W4_HELPER_DEFAULT", helper)
    try:
        module, _ = _import_source(tmp_path, name, COMPUTED_DEFAULT_SOURCE)
        return _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("0.21", "0.99"),
        ("1", "1.0"),
        ("False", "0"),
        ("True", "1"),
        ("(0.21,)", "[0.21]"),
        ("{}", "{'rate': None}"),
        ("{'a': 1, 'b': 2}", "{'b': 2, 'a': 1}"),
        ("None", "'None'"),
    ],
)
def test_computed_defaults_are_bound_by_typed_value(
    tmp_path, monkeypatch, first, second
):
    """Round-4 review M4: values that behave differently never share a digest."""

    one = _computed_default_identity(tmp_path / "a", monkeypatch, first)
    again = _computed_default_identity(tmp_path / "b", monkeypatch, first)
    other = _computed_default_identity(tmp_path / "c", monkeypatch, second)
    assert one == again
    assert one != other


def test_a_helpers_computed_default_is_bound(tmp_path, monkeypatch):
    one = _computed_default_identity(tmp_path / "a", monkeypatch, "0.21", "2")
    other = _computed_default_identity(tmp_path / "b", monkeypatch, "0.21", "3")
    assert one != other


def test_defaults_without_an_exact_encoding_are_refused(tmp_path):
    source = (
        "import decimal\n\n\n"
        "def raise_rate(simulation, measure=decimal.Decimal('0.21')):\n"
        "    simulation.rate = measure\n"
    )
    name = "w4_receipt_measures_object_default"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match="default arguments cannot be bound"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_a_helpers_unencodable_default_refuses_the_module(tmp_path):
    source = (
        "import decimal\n\n\n"
        "def _helper(value, scale=decimal.Decimal('2')):\n"
        "    return value * scale\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_measures_helper_object_default"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match="_helper's default arguments"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("source_value", "runtime_value"),
    [(False, 0), (0, False), (1, 1.0), (1.0, 1), ((1,), [1]), ("1", 1)],
)
def test_literal_defaults_compare_with_their_types(
    tmp_path, source_value, runtime_value
):
    """A runtime default equal in Python but of another type is refused."""

    source = (
        f"def raise_rate(simulation, value={source_value!r}):\n"
        "    simulation.value = value\n"
    )
    name = "w4_receipt_measures_typed_literal_default"
    try:
        module, _ = _import_source(tmp_path, name, source)
        _identity(module.raise_rate)
        module.raise_rate.__defaults__ = (runtime_value,)
        with pytest.raises(ReceiptError, match="default arguments differ"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("source_value", "runtime_value"),
    [(False, 0), (0, False), (1, 1.0), ((1,), [1])],
)
def test_literal_constants_compare_with_their_types(
    tmp_path, source_value, runtime_value
):
    source = (
        f"ENABLED = {source_value!r}\n\n\n"
        "def raise_rate(simulation):\n    simulation.enabled = ENABLED\n"
    )
    name = "w4_receipt_measures_typed_constant"
    try:
        module, _ = _import_source(tmp_path, name, source)
        _identity(module.raise_rate)
        module.ENABLED = runtime_value
        with pytest.raises(ReceiptError, match="ENABLED is"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_a_helper_with_foreign_globals_is_refused(tmp_path):
    import types

    name = "w4_receipt_measures_foreign_helper"
    try:
        module, _ = _import_source(tmp_path, name, HELPER_SOURCE)
        _measure_identity(module)
        module._helper = types.FunctionType(
            module._helper.__code__, {"__name__": name}, "_helper"
        )
        with pytest.raises(ReceiptError, match="does not use its module's globals"):
            _measure_identity(module)
    finally:
        sys.modules.pop(name, None)


def test_from_reform_scenarios_are_refused_in_favour_of_their_dictionary():
    from policyengine_uk.utils.scenario import Scenario

    basic = Scenario.from_reform(
        {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027": 0.21}}
    )
    with pytest.raises(ReceiptError, match="reform dictionary"):
        scenario_reform_identity(basic, code_revision=REVISION)
    a = reform_identity(
        {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027": 0.21}},
        "policyengine-uk.reform_dict/v1",
    )
    b = reform_identity(
        {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027": 0.25}},
        "policyengine-uk.reform_dict/v1",
    )
    assert a.reform_sha256 != b.reform_sha256


def _managed_simulation(dataset_file, bundle, **overrides):
    """A microsimulation as ``managed_microsimulation`` records its dataset."""

    from policyengine.provenance.dataset_materialization import MaterializedDataset
    from policyengine.tax_benefit_models.common.model_version import (
        build_runtime_dataset_provenance,
    )

    record = bundle["data_releases"]["uk"]
    reference = record["datasets"][record["default_dataset"]]
    uri = f"hf://{reference['repo_id']}/{reference['path']}@{reference['revision']}"
    fields = {"country_id": "uk"}
    fields.update(
        build_runtime_dataset_provenance(
            uri,
            str(dataset_file),
            MaterializedDataset(
                data_package_name=record["data_package"]["name"],
                repo_type="model",
                revision=reference["revision"],
                source_uri=uri,
                sha256=hashlib.sha256(dataset_file.read_bytes()).hexdigest(),
                path=dataset_file,
            ),
            logical_name=record["default_dataset"],
        )
    )
    fields.update(overrides)
    return SimpleNamespace(policyengine_bundle=fields)


def _microsimulation_receipt(simulation, bundle):
    return build_execution_receipt_for_microsimulation(
        simulation,
        years=[2026],
        reform=CURRENT_LAW,
        baseline=CURRENT_LAW,
        bundle=bundle,
    )


def test_microsimulation_receipt_needs_its_reform_and_reads_the_loaded_dataset(
    dataset_file,
):
    bundle = _bundle_for(dataset_file.read_bytes())
    simulation = _managed_simulation(dataset_file, bundle)
    with pytest.raises(TypeError):
        build_execution_receipt_for_microsimulation(
            simulation, years=[2026], bundle=bundle
        )
    receipt = _microsimulation_receipt(simulation, bundle)
    assert receipt.certification_status == "certified"
    assert (
        receipt.data.dataset_uri
        == simulation.policyengine_bundle["runtime_dataset_uri"]
    )
    assert (
        receipt.data.build_model_version
        == bundle["data_releases"]["uk"]["certification"]["built_with_model_version"]
    )
    with pytest.raises(ReceiptError):
        build_execution_receipt_for_microsimulation(
            object(), years=[2026], reform=CURRENT_LAW, baseline=CURRENT_LAW
        )


def test_a_dataset_replaced_after_loading_is_refused(dataset_file, tmp_path):
    """Round-4 review H2: the receipt describes the bytes that were loaded."""

    loaded = tmp_path / "loaded.h5"
    loaded.write_bytes(b"the bytes that ran")
    certified = dataset_file.read_bytes()
    bundle = _bundle_for(certified)
    simulation = _managed_simulation(loaded, bundle)
    loaded.write_bytes(certified)  # swapped for the certified bytes afterwards
    with pytest.raises(ReceiptError, match="has changed since the microsimulation"):
        _microsimulation_receipt(simulation, bundle)
    loaded.unlink()
    with pytest.raises(ReceiptError, match="is gone"):
        _microsimulation_receipt(simulation, bundle)


def test_a_dataset_loaded_without_a_hash_cannot_be_receipted(dataset_file):
    bundle = _bundle_for(dataset_file.read_bytes())
    simulation = _managed_simulation(dataset_file, bundle)
    del simulation.policyengine_bundle["runtime_dataset_sha256"]
    with pytest.raises(ReceiptError, match="without verifying its SHA-256"):
        _microsimulation_receipt(simulation, bundle)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("runtime_dataset_uri", "hf://policyengine/other/enhanced_frs_2024_25.h5@1"),
        ("runtime_dataset_revision", "0" * 40),
        ("runtime_dataset_data_package", "other-data"),
    ],
)
def test_load_time_provenance_must_match_the_receipt(dataset_file, field, value):
    bundle = _bundle_for(dataset_file.read_bytes())
    simulation = _managed_simulation(dataset_file, bundle, **{field: value})
    with pytest.raises(ReceiptError, match="but the microsimulation loaded"):
        _microsimulation_receipt(simulation, bundle)


# --- Fiscal years --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("year", "label"), [(2027, "2027-28"), (1999, "1999-00"), (2009, "2009-10")]
)
def test_uk_fiscal_year_labels(year, label):
    assert fiscal_year_label(year, uk_fiscal_year_convention()) == label


def test_fiscal_year_convention_start_dates_are_fixed():
    with pytest.raises(ValidationError):
        FiscalYearConvention(
            convention="uk_fiscal_year",
            period_start="01-01",
            parameter_annualisation="x",
        )


# --- The published JSON Schema agrees with the Pydantic model ------------------------


@pytest.fixture(scope="module")
def schema_validator():
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def test_published_schema_is_current():
    assert json.loads(SCHEMA_PATH.read_text()) == ExecutionReceipt.json_schema()


@settings(max_examples=40, deadline=None)
@given(
    years=st.lists(st.integers(2020, 2040), min_size=1, max_size=5),
    payload=st.none() | REFORM_PAYLOADS,
    certified=st.booleans(),
    modifier=st.booleans(),
    git_sha=st.none() | st.just("c" * 40),
    qualification=st.none() | SHA,
)
@pytest.mark.usefixtures("index_installs")
def test_schema_accepts_every_valid_receipt(
    tmp_path_factory,
    schema_validator,
    years,
    payload,
    certified,
    modifier,
    git_sha,
    qualification,
):
    directory = tmp_path_factory.mktemp("schema")
    dataset = directory / "data.h5"
    dataset.write_bytes(b"bytes")
    reform = (
        scenario_reform_identity(
            _scenario(simulation_modifier=receipt_modifiers.raise_basic_rate),
            code_revision=REVISION,
        )
        if modifier
        else reform_identity(payload, "policyengine.reform_dict/v1")
    )
    receipt = _build(
        dataset,
        _bundle_for(b"bytes", model_version=INSTALLED_UK if certified else "0.0.1"),
        years=years,
        reform=reform,
        wrapper_git_sha=git_sha,
        qualification_receipt_sha256=qualification,
        outputs={"budgetary_impact": 1.5e9},
    )
    schema_validator.validate(json.loads(receipt.model_dump_json()))
    schema_validator.validate(json.loads(receipt.to_canonical_json()))


MUTATIONS = [
    ("extra top-level member", lambda r: r.update(unexpected=1)),
    ("bad schema version", lambda r: r.update(schema_version=2)),
    ("bad receipt type", lambda r: r.update(receipt_type="other")),
    ("US receipt", lambda r: r.update(country_id="us")),
    ("missing data", lambda r: r.pop("data")),
    ("bad dataset digest", lambda r: r["data"].update(dataset_sha256="XYZ")),
    ("short dataset digest", lambda r: r["data"].update(dataset_sha256="a" * 63)),
    ("extra data member", lambda r: r["data"].update(rows=10)),
    ("empty years", lambda r: r.update(years=[])),
    ("string year", lambda r: r.update(years=["2026"])),
    ("bad period start", lambda r: r["fiscal_year"].update(period_start="April")),
    ("calendar period start", lambda r: r["fiscal_year"].update(period_start="01-01")),
    (
        "calendar convention",
        lambda r: r["fiscal_year"].update(
            convention="calendar_year", period_start="01-01"
        ),
    ),
    ("US model", lambda r: r["model"].update(name="policyengine-us")),
    ("wrong core", lambda r: r["core"].update(name="numpy")),
    ("wrong wrapper", lambda r: r["wrapper"].update(name="policyengine-uk")),
    ("manifest digest", lambda r: r["data"].update(release_manifest_sha256="a" * 64)),
    ("bad wheel digest", lambda r: r["model"].update(wheel_sha256="1234")),
    ("unnormalized name", lambda r: r["model"].update(name="Policyengine_UK")),
    ("bad git sha", lambda r: r["wrapper"].update(git_sha="abc")),
    (
        "missing certificate source",
        lambda r: r["certificate"].pop("certificate_source"),
    ),
    (
        "missing certified core",
        lambda r: r["certificate"].pop("certified_for_core_version"),
    ),
    (
        "unknown representation",
        lambda r: r["reform"].update(
            kind="reform", representation="pickle", reform_sha256="a" * 64
        ),
    ),
]


@pytest.mark.parametrize(("label", "mutate"), MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_schema_and_model_reject_the_same_malformed_receipts(
    certified_receipt, schema_validator, label, mutate
):
    payload = copy.deepcopy(certified_receipt.model_dump(mode="json"))
    mutate(payload)
    assert not schema_validator.is_valid(payload), label
    with pytest.raises(ValidationError):
        ExecutionReceipt.model_validate(payload)


def test_schema_publishes_the_rules_it_cannot_express(schema_validator):
    rules = schema_validator.schema["x-policyengine-rules"]
    assert "certificate.certified_for_core_version equals core.version." in rules
    assert any("verify_certificate()" in rule for rule in rules)
    assert any(
        "certificate_source is the producer's statement" in rule for rule in rules
    )
    assert not any("requires certificate_source packaged" in rule for rule in rules)
    properties = schema_validator.schema["$defs"]
    assert properties["ModelIdentity"]["properties"]["name"]["const"] == (
        "policyengine-uk"
    )
    assert properties["FiscalYearConvention"]["properties"]["period_start"][
        "const"
    ] == ("04-06")
    assert (
        "RFC 8785"
        in schema_validator.schema["x-policyengine-digests"]["canonicalization"]
    )


def test_execution_identity_preimage(certified_receipt):
    identity = certified_receipt.execution_identity()
    assert set(identity) == {
        "schema_version",
        "country_id",
        "wrapper",
        "model",
        "core",
        "data",
        "certification_status",
        "certificate",
    }
    assert "certificate_source" not in identity["certificate"]
    assert certified_receipt.execution_identity_sha256 == canonical_sha256(identity)


# --- Supported years ----------------------------------------------------------------


def test_years_outside_the_projection_are_unsupported(dataset_file):
    """A 2031-32 figure on data projected to 2030 is not evidence."""

    receipt = _build(dataset_file, years=[2029, 2030, 2031])
    assert receipt.supported_years == list(PROJECTED_YEARS)
    assert receipt.unsupported_years == [2031]
    assert _build(dataset_file, years=[2026, 2027]).unsupported_years == []


def test_supported_years_are_part_of_the_receipt_digest(dataset_file, monkeypatch):
    receipt = _build(dataset_file, years=[2026])
    monkeypatch.setattr(
        receipt_module,
        "_projected_years",
        lambda path, sha256, model_version: tuple(range(2024, 2032)),
    )
    longer = _build(dataset_file, years=[2026])
    assert longer.receipt_sha256 != receipt.receipt_sha256
    assert longer.execution_identity_sha256 == receipt.execution_identity_sha256


@pytest.mark.parametrize(
    "supported", [[2027, 2026], [2026, 2026], ["2026"], [2026.0], None]
)
def test_supported_years_must_be_sorted_unique_integers(certified_receipt, supported):
    payload = json.loads(certified_receipt.model_dump_json())
    if supported is None:
        del payload["supported_years"]
    else:
        payload["supported_years"] = supported
    with pytest.raises(ValidationError):
        ExecutionReceipt.model_validate(payload)


def test_the_projection_is_computed_once_per_file_and_model(dataset_file, monkeypatch):
    calls = []

    def projected(path, sha256, model_version):
        calls.append((path, sha256, model_version))
        return PROJECTED_YEARS

    monkeypatch.setattr(receipt_module, "_projected_years", projected)
    receipt = _build(dataset_file, years=[2026])
    assert calls == [
        (str(dataset_file), receipt.data.dataset_sha256, receipt.model.version)
    ]


def test_the_certified_dataset_projects_to_2030():
    """Runs only with the certified 1.58.0 file: POLICYENGINE_UK_CERTIFIED_DATASET."""

    import os

    path = os.environ.get("POLICYENGINE_UK_CERTIFIED_DATASET")
    if not path:
        pytest.skip("set POLICYENGINE_UK_CERTIFIED_DATASET to the 1.58.0 file")
    sha256 = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    years = receipt_module._projected_years(path, sha256, INSTALLED_UK)
    assert years == PROJECTED_YEARS


# --- Round-5 review findings ------------------------------------------------------


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("(1,)", "(1.0,)"),
        ("(True,)", "(1,)"),
        ("0.0", "-0.0"),
        ("((1, 2),)", "((1.0, 2),)"),
        ("frozenset({1})", "frozenset({1.0})"),
        ("1j", "-1j"),
    ],
)
def test_code_constants_compare_with_exact_types(first, second):
    """Round-5 review: equal-but-different constants are different code."""

    from policyengine.provenance.bytecode import code_shape

    left = compile(f"value = {first}", "x", "exec", dont_inherit=True)
    right = compile(f"value = {second}", "x", "exec", dont_inherit=True)
    assert code_shape(left) != code_shape(right)
    assert code_shape(left) == code_shape(
        compile(f"value = {first}", "elsewhere", "exec", dont_inherit=True)
    )


def test_a_helper_rebound_to_another_modules_function_is_refused(tmp_path):
    """Round-5 review: a source-defined helper may not silently change owner."""

    import types

    name = "w4_receipt_r5_rebound_helper"
    try:
        module, _ = _import_source(tmp_path, name, HELPER_SOURCE)
        _measure_identity(module)
        foreign = types.ModuleType("w4_receipt_r5_foreign")
        exec("def _helper(value):\n    return value * 99\n", foreign.__dict__)
        module._helper = foreign._helper
        with pytest.raises(ReceiptError, match="no longer the function its source"):
            _measure_identity(module)
        module._helper = 7
        with pytest.raises(ReceiptError, match="no longer the function its source"):
            _measure_identity(module)
        del module._helper
        with pytest.raises(ReceiptError, match="no longer defined"):
            _measure_identity(module)
    finally:
        sys.modules.pop(name, None)


PARTIAL_SOURCE = """
from functools import partial


def apply_payment(simulation, *, amount, year):
    simulation.payment = (amount, year)


PAYMENT = partial(apply_payment, amount=120, year=2027)


def modifier(simulation):
    return PAYMENT(simulation)
"""


def test_a_module_level_partial_the_modifier_calls_is_refused(tmp_path):
    """W5's review of uk-autumn-budget-dashboard-2026#23: editing the partial's
    captured amount from 120 to 240 changed the payment under one digest."""

    name = "w4_receipt_globals_partial"
    try:
        module, _ = _import_source(tmp_path, name, PARTIAL_SOURCE)
        with pytest.raises(
            ReceiptError,
            match="line 9 assigns PAYMENT something other than a literal",
        ):
            _identity(module.modifier)
        module.PAYMENT.keywords["amount"] = 240
        with pytest.raises(ReceiptError, match="assigns PAYMENT"):
            _identity(module.modifier)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("source", "match"),
    [
        pytest.param(
            "import os\nRATE = float(os.environ.get('W4_RATE', '0.21'))\n\n\n"
            "def raise_rate(simulation):\n    simulation.rate = RATE\n",
            "assigns RATE something other than a literal",
            id="computed-from-the-environment",
        ),
        pytest.param(
            "from functools import partial\n\n\n"
            "def _pay(simulation, amount):\n    simulation.paid = amount\n\n\n"
            "PAY = partial(_pay, amount=120)\n\n\n"
            "def _helper(simulation):\n    PAY(simulation)\n\n\n"
            "def raise_rate(simulation):\n    _helper(simulation)\n",
            "assigns PAY something other than a literal",
            id="partial-through-a-helper",
        ),
        pytest.param(
            "import functools\nSCALE = float('2')\n\n\n"
            "def scaled(function):\n    @functools.wraps(function)\n"
            "    def wrapper(value):\n        return function(value) * SCALE\n"
            "    return wrapper\n\n\n"
            "@scaled\ndef _helper(value):\n    return value\n\n\n"
            "def raise_rate(simulation):\n    simulation.rate = _helper(0.21)\n",
            "assigns SCALE something other than a literal",
            id="computed-global-in-a-decorator-wrapper",
        ),
        pytest.param(
            "import os\nSCALE = len(os.sep)\n\n\n"
            "def raise_rate(simulation):\n    scale = lambda rate: rate * SCALE\n"
            "    simulation.rate = scale(0.21)\n",
            "assigns SCALE something other than a literal",
            id="computed-global-in-nested-code",
        ),
        pytest.param(
            "class Measure:\n    rate = 0.21\n\n\n"
            "def raise_rate(simulation):\n    simulation.rate = Measure.rate\n",
            "defines class Measure",
            id="class-in-the-file",
        ),
        pytest.param(
            "from math import pi\n\n\n"
            "def raise_rate(simulation):\n    simulation.rate = pi / 10\n",
            r"pi\W.*an imported value of type float",
            id="imported-value",
        ),
        pytest.param(
            "from functools import partial\nfrom operator import mul\n"
            "from math import floor as PAY\n"
            "PAY = partial(mul, 2)\n\n\n"
            "def raise_rate(simulation):\n    simulation.rate = PAY(0.21)\n",
            "line 4 assigns PAY something other than a literal",
            id="import-rebound-to-a-partial",
        ),
        pytest.param(
            "from math import *\n\n\n"
            "def raise_rate(simulation):\n    simulation.rate = floor(e)\n",
            "an imported value of type float",
            id="star-imported-value",
        ),
        pytest.param(
            "COUNT = 0\n\n\n"
            "def raise_rate(simulation):\n    global COUNT\n    COUNT += 1\n"
            "    simulation.rate = 0.21\n",
            "line 5 declares COUNT global",
            id="assigns-a-global",
        ),
    ],
)
def test_modifiers_reading_module_state_the_digest_cannot_bind_are_refused(
    tmp_path, source, match
):
    name = "w4_receipt_globals_refused"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match=match) as refused:
            _identity(module.raise_rate)
        assert "cannot be bound" in str(refused.value)
    finally:
        sys.modules.pop(name, None)


def test_a_partial_imported_from_another_module_is_refused(tmp_path):
    """``from params import PAY`` puts the partial in the modifier's module."""

    params = "w4_receipt_globals_params"
    name = "w4_receipt_globals_imports_partial"
    try:
        _import_source(
            tmp_path,
            params,
            "from functools import partial\nfrom operator import mul\n\n"
            "PAY = partial(mul, 120)\n",
        )
        module, _ = _import_source(
            tmp_path,
            name,
            f"from {params} import PAY\n\n\n"
            "def raise_rate(simulation):\n    simulation.paid = PAY(1)\n",
        )
        with pytest.raises(
            ReceiptError,
            match=r"PAY is an imported value of type functools\.partial",
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)
        sys.modules.pop(params, None)


def test_a_name_set_on_the_module_after_import_is_refused(tmp_path):
    source = "def raise_rate(simulation):\n    simulation.rate = EXTRA\n"
    name = "w4_receipt_globals_injected"
    try:
        module, _ = _import_source(tmp_path, name, source)
        _identity(module.raise_rate)  # EXTRA is unbound: running it fails
        module.EXTRA = 0.30
        with pytest.raises(
            ReceiptError, match="EXTRA is a value of type float set on the module"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


ALLOWED_GLOBALS_SOURCE = """
import math
from functools import partial
from math import floor

RATE = 0.21


def _countdown(depth):
    return 0 if depth == 0 else _countdown(depth - 1)


def raise_rate(simulation):
    class Local:
        value = RATE

    simulation.rate = floor(Local.value * 100) / 100 + _countdown(2)
    simulation.tau = math.tau
    simulation.module = __name__
    simulation.count = len([RATE])
"""


def test_literals_functions_imports_and_builtins_bind(tmp_path):
    """Recursion terminates, a class inside the modifier reads its own body,
    and a module attribute is bound by the code revision."""

    name = "w4_receipt_globals_allowed"
    try:
        module, _ = _import_source(tmp_path, name, ALLOWED_GLOBALS_SOURCE)
        identity = scenario_reform_identity(
            _scenario(simulation_modifier=module.raise_rate), code_revision=REVISION
        )
        assert identity.binding == "code_revision"
    finally:
        sys.modules.pop(name, None)


#: Each kind of module global, as (definition, expression reading it, bindable).
GLOBAL_KINDS = {
    "literal": ("K_LITERAL = 0.21", "K_LITERAL", True),
    "function": ("def k_function():\n    return 1", "k_function()", True),
    "imported_callable": ("from math import floor as k_floor", "k_floor(1.5)", True),
    "module": ("import math as k_math", "k_math.tau", True),
    "builtin": ("", "len(())", True),
    "partial": (
        "from functools import partial as _partial\nK_PARTIAL = _partial(abs)",
        "K_PARTIAL(-1)",
        False,
    ),
    "computed": ("K_COMPUTED = abs(-1)", "K_COMPUTED", False),
    "class": ("class KClass:\n    pass", "KClass", False),
    "imported_value": ("from math import e as k_e", "k_e", False),
}
_GLOBAL_MODULES = iter(range(10**9))


@settings(max_examples=60, deadline=None)
@given(
    kinds=st.lists(
        st.sampled_from(sorted(GLOBAL_KINDS)), min_size=1, max_size=5, unique=True
    ),
    through_helper=st.booleans(),
)
def test_a_modifier_binds_exactly_when_every_global_it_reads_binds(
    kinds, through_helper
):
    """Invariant: an identity is issued if and only if every module global the
    modifier's code reads, directly or through a function in the file, is a
    literal, a function in the file, an imported callable or module, or a
    builtin; otherwise the refusal names an unbindable global."""

    import tempfile

    definitions = "\n\n\n".join(
        GLOBAL_KINDS[kind][0] for kind in kinds if GLOBAL_KINDS[kind][0]
    )
    reads = ", ".join(GLOBAL_KINDS[kind][1] for kind in kinds)
    if through_helper:
        body = (
            f"def _reader():\n    return ({reads},)\n\n\n"
            "def raise_rate(simulation):\n    simulation.values = _reader()\n"
        )
    else:
        body = f"def raise_rate(simulation):\n    simulation.values = ({reads},)\n"
    source = f"{definitions}\n\n\n{body}"
    name = f"w4_receipt_globals_property_{next(_GLOBAL_MODULES)}"
    unbindable = [kind for kind in kinds if not GLOBAL_KINDS[kind][2]]
    with tempfile.TemporaryDirectory() as directory:
        try:
            module, _ = _import_source(Path(directory), name, source)
            if not unbindable:
                assert _identity(module.raise_rate)
                return
            with pytest.raises(ReceiptError) as refused:
                _identity(module.raise_rate)
            named = [
                kind
                for kind in unbindable
                if GLOBAL_KINDS[kind][1].split("(")[0] in str(refused.value)
            ]
            assert named, str(refused.value)
        finally:
            sys.modules.pop(name, None)


def test_signed_zero_defaults_differ(tmp_path, monkeypatch):
    """Round-5 review: copysign tells 0.0 from -0.0, so the digest must too."""

    plus = _computed_default_identity(tmp_path / "a", monkeypatch, "0.0")
    minus = _computed_default_identity(tmp_path / "b", monkeypatch, "-0.0")
    assert plus != minus
    source = "def raise_rate(simulation, value=0.0):\n    simulation.value = value\n"
    name = "w4_receipt_r5_literal_zero"
    try:
        module, _ = _import_source(tmp_path / "c", name, source)
        module.raise_rate.__defaults__ = (-0.0,)
        with pytest.raises(ReceiptError, match="default arguments differ"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_a_module_that_imports_what_its_modifier_calls_binds(tmp_path):
    """Round-5 review: compiled alone, math.copysign compiled differently."""

    source = (
        "import math\n\n\ndef raise_rate(simulation):\n"
        "    simulation.rate = math.copysign(0.21, 1.0)\n"
    )
    name = "w4_receipt_r5_import_math"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_numpy_booleans_are_neither_years_nor_schema_versions(
    dataset_file, certified_receipt
):
    """Round-5 review: np.bool_ is a boolean, not 1 or 0."""

    with pytest.raises(ReceiptError, match="years must be integers"):
        _build(dataset_file, years=[np.bool_(True)])
    payload = certified_receipt.model_dump()
    payload["schema_version"] = np.bool_(True)
    with pytest.raises(ValidationError):
        ExecutionReceipt.model_validate(payload)


def test_default_dictionary_keys_must_be_exact_strings(tmp_path, monkeypatch):
    class Key(str):
        pass

    with pytest.raises(ReceiptError, match="keys must be strings"):
        receipt_module._typed_value({Key("rate"): 0.21})


def _flip_nan_signs(code):
    import math

    def flipped(constant):
        if isinstance(constant, float) and math.isnan(constant):
            return -constant
        if isinstance(constant, complex) and math.isnan(constant.real):
            return complex(-constant.real, constant.imag)
        return constant

    return code.replace(co_consts=tuple(flipped(c) for c in code.co_consts))


@pytest.mark.parametrize(
    "source",
    ["value = 1e999 - 1e999", "value = complex(1e999 - 1e999, 1)"],
    ids=["float", "complex"],
)
def test_a_nan_constant_of_the_other_sign_is_other_code(source):
    """Round-6 review H1: float.hex() writes both signs of NaN as "nan"."""

    from policyengine.provenance.bytecode import code_shape

    if "complex" in source:
        source = "value = (1e999 - 1e999) + 1j"
    code = compile(source, "x", "exec", dont_inherit=True)
    assert code_shape(_flip_nan_signs(code)) != code_shape(code)
    assert code_shape(code) == code_shape(
        compile(source, "y", "exec", dont_inherit=True)
    )


def test_code_differing_only_in_its_exception_table_is_other_code():
    """A survivor of round-6 mutation testing: the table decides what is caught."""

    from policyengine.provenance.bytecode import code_shape

    source = "try:\n    value = int('x')\nexcept ValueError:\n    value = 0\n"
    code = compile(source, "x", "exec", dont_inherit=True)
    assert code.co_exceptiontable
    assert code_shape(code.replace(co_exceptiontable=b"")) != code_shape(code)


REBINDING_SOURCE = """
def helper():
    return 0.21


def alternative():
    return 0.99


def raise_rate(simulation):
    simulation.rate = helper()
"""


def test_a_helper_rebound_to_another_function_of_the_file_is_refused(tmp_path):
    """Round-6 review M2: each function still matches its source, but helper
    now names alternative's code, which returns 0.99."""

    name = "w4_receipt_r6_rebound_helper"
    try:
        module, _ = _import_source(tmp_path, name, REBINDING_SOURCE)
        _identity(module.raise_rate)
        module.original_helper = module.helper
        module.helper = module.alternative
        with pytest.raises(ReceiptError, match="helper is bound to alternative"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


SHARED_DEFAULTS_SOURCE = """
def _helper(value, scales=[2.0]):
    return value * scales[0]


def raise_rate(simulation, first=list(), second=[], scales=[2.0]):
    first.append(1)  # visible through second only when they are one list
    simulation.rate = 0.99 if second else _helper(0.21, scales)
    first.clear()
"""


def _shared_lists(module):
    shared = []
    module.raise_rate.__defaults__ = (shared, shared, [2.0])


def _list_holding_itself(module):
    loop = []
    loop.append(loop)
    module.raise_rate.__defaults__ = (loop, [], [2.0])


def _shared_across_functions(module):
    module._helper.__defaults__ = (module.raise_rate.__defaults__[2],)


@pytest.mark.parametrize(
    "share",
    [_shared_lists, _list_holding_itself, _shared_across_functions],
    ids=["two-defaults", "itself", "two-functions"],
)
def test_defaults_that_are_one_mutable_object_are_refused(tmp_path, share):
    """Round-6 review M4: one shared list and two equal lists encode alike."""

    name = "w4_receipt_r6_shared_defaults"
    try:
        module, _ = _import_source(tmp_path, name, SHARED_DEFAULTS_SOURCE)
        _identity(module.raise_rate)
        share(module)
        with pytest.raises(ReceiptError, match="are one list object"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_bytes_set_and_complex_constants_bind_and_are_checked(tmp_path):
    """Round-6 review L5: exact literal comparison, not the defaults encoder."""

    source = (
        "TOKEN = b'publication'\nYEARS = {2026, 2027}\nPHASE = 1j\n"
        "ZEROS = {0.0}\n\n\n"
        "def raise_rate(simulation):\n"
        "    simulation.rate = 0.21 if TOKEN and 2026 in YEARS else 0.0\n"
        "    simulation.phase = (PHASE, ZEROS)\n"
    )
    name = "w4_receipt_r6_literal_kinds"
    try:
        module, _ = _import_source(tmp_path, name, source)
        _identity(module.raise_rate)
        for attribute, value in [
            ("YEARS", {2026, 2028}),
            ("TOKEN", bytearray(b"publication")),
            ("PHASE", -1j),
            ("ZEROS", {-0.0}),  # equal under ==, another bit pattern
        ]:
            original = getattr(module, attribute)
            setattr(module, attribute, value)
            with pytest.raises(ReceiptError, match=f"{attribute} is"):
                _identity(module.raise_rate)
            setattr(module, attribute, original)
        _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


LITERALS = st.recursive(
    st.none()
    | st.booleans()
    | st.integers(-(2**70), 2**70)
    | st.floats(allow_nan=False)
    | st.complex_numbers(allow_nan=False)
    | st.text(max_size=5)
    | st.binary(max_size=5)
    | st.just(Ellipsis),
    lambda children: (
        st.lists(children, max_size=3)
        | st.lists(children, max_size=3).map(tuple)
        | st.dictionaries(st.text(max_size=3), children, max_size=3)
        | st.frozensets(st.integers(-3, 3) | st.text(max_size=2), max_size=3)
    ),
    max_leaves=8,
)


@settings(max_examples=300, deadline=None)
@given(left=LITERALS, right=LITERALS)
def test_same_literal_is_exact_equality(left, right):
    """Invariants: a value is the same as itself and as its own round trip
    through source; values the same are equal under ``==``; and changing one
    float's sign of zero or one int to float makes them differ."""

    import ast as _ast

    same = receipt_module._same_literal
    assert same(left, left)
    try:
        written = _ast.literal_eval(repr(left))
    except (ValueError, SyntaxError):
        written = None  # inf, frozenset() and Ellipsis have no literal form
    # repr writes complex(-0.0, 0.0) as "(-0+0j)", which reads back +0.0.
    if written is not None and "j" not in repr(left):
        assert same(left, written)
    if same(left, right):
        assert left == right or left != left  # a complex NaN cannot occur
    assert not same(0.0, -0.0)
    assert not same([1], [1.0])
    assert not same((1,), [1])
    assert not same({"a": 1, "b": 2}, {"b": 2, "a": 1})


_REAL_PROJECTED_YEARS = receipt_module._projected_years


def test_projected_years_start_at_the_datasets_own_year(monkeypatch):
    """A survivor of round-6 mutation testing: an extension that also holds
    earlier years must not make them supported."""

    import types

    stubs = {
        "policyengine_uk": types.ModuleType("policyengine_uk"),
        "policyengine_uk.data": types.ModuleType("policyengine_uk.data"),
        "policyengine_uk.data.dataset_schema": types.ModuleType("schema"),
        "policyengine_uk.data.economic_assumptions": types.ModuleType("assumptions"),
        "policyengine_uk.system": types.ModuleType("system"),
    }
    stubs["policyengine_uk.data.dataset_schema"].UKSingleYearDataset = lambda path: (
        types.SimpleNamespace(time_period=2023)
    )
    stubs["policyengine_uk.data.economic_assumptions"].extend_single_year_dataset = (
        lambda dataset, parameters: types.SimpleNamespace(years=[2022, 2023, 2024])
    )
    stubs["policyengine_uk.system"].system = types.SimpleNamespace(parameters=None)
    for module_name, module in stubs.items():
        monkeypatch.setitem(sys.modules, module_name, module)
    unwrapped = getattr(_REAL_PROJECTED_YEARS, "__wrapped__", _REAL_PROJECTED_YEARS)
    assert unwrapped("unused.h5", "0" * 64, "0.0.0") == (2023, 2024)


# --- Round-7 review findings: the module shape a digest can bind ------------------


MEASURE_TAIL = "\n\ndef raise_rate(simulation):\n    simulation.rate = 0.21\n"


@pytest.mark.parametrize(
    ("source", "match"),
    [
        pytest.param(
            "import os\nDEBUG = False\nif os.environ.get('W4_X'):\n    DEBUG = True\n"
            + MEASURE_TAIL,
            "line 3 is a module-level If statement",
            id="conditional-literal",
        ),
        pytest.param(
            "import os\nif os.environ.get('W4_ALT'):\n    from math import ceil as pick\n"
            "else:\n    from math import floor as pick\n" + MEASURE_TAIL,
            "module-level If statement",
            id="conditional-import",
        ),
        pytest.param(
            "import sys\nif sys.version_info >= (3,):\n"
            "    def raise_rate(simulation):\n        simulation.rate = 0.21\n",
            "module-level If statement",
            id="function-in-a-block",
        ),
        pytest.param(
            "try:\n    import numpy\nexcept ImportError:\n    numpy = None\n"
            + MEASURE_TAIL,
            "module-level Try statement",
            id="guarded-import",
        ),
        pytest.param(
            "RATE = 0.21\nRATES = [RATE for RATE in range(3)]\n" + MEASURE_TAIL,
            "line 2 assigns RATES something other than a literal",
            id="comprehension",
        ),
        pytest.param(
            "RATE = 0.21\nmapper = lambda value: (RATE := value)\n" + MEASURE_TAIL,
            "assigns mapper something other than a literal",
            id="lambda",
        ),
        pytest.param(
            "RATE, UNUSED = 0.21, 1\n" + MEASURE_TAIL,
            "line 1 assigns to something other than one name",
            id="unpacking",
        ),
        pytest.param(
            "FIRST = SECOND = []\n" + MEASURE_TAIL,
            "assigns to something other than one name",
            id="chained-assignment",
        ),
        pytest.param(
            "RATE = 0.21\nRATE = 0.30\n" + MEASURE_TAIL,
            "RATE is bound twice",
            id="rebinding",
        ),
        pytest.param(
            "RATE = 0.21\nRATE += 0.01\n" + MEASURE_TAIL,
            "module-level AugAssign statement",
            id="augmented-assignment",
        ),
        pytest.param(
            "RATE = 0.21\nx: (RATE := 0.30) = 1\n" + MEASURE_TAIL,
            "binds a name in the annotation of x",
            id="annotation-walrus",
        ),
        pytest.param(
            "RATE = 0.21\n\n\ndef _helper(value=(RATE := 0.30)):\n    return value\n"
            + MEASURE_TAIL,
            "a default or annotation of _helper binds a name",
            id="default-walrus",
        ),
        pytest.param(
            "import functools\n\n\n@functools.cache\ndef _helper():\n    return 0.21\n"
            + MEASURE_TAIL,
            "line 5 decorates _helper",
            id="decorator",
        ),
        pytest.param(
            "class Holder:\n    rate = 0.21\n" + MEASURE_TAIL,
            "line 1 defines class Holder",
            id="class",
        ),
        pytest.param(
            "def _helper():\n    return _helper.amount\n\n\n_helper.amount = 120\n"
            + MEASURE_TAIL,
            "line 5 assigns to something other than one name",
            id="function-attribute",
        ),
        pytest.param(
            "import logging\nlogging.basicConfig()\n" + MEASURE_TAIL,
            "line 2 is a module-level Expr statement",
            id="call-at-import",
        ),
        pytest.param(
            "WEEKLY = 520 / 52\n" + MEASURE_TAIL,
            "line 1 assigns WEEKLY something other than a literal",
            id="literal-arithmetic-division",
        ),
        pytest.param(
            "MILLION = 10 ** 6\n" + MEASURE_TAIL,
            "line 1 assigns MILLION something other than a literal",
            id="literal-arithmetic-power",
        ),
        pytest.param(
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
            "    from collections import OrderedDict\n" + MEASURE_TAIL,
            "line 2 is a module-level If statement",
            id="type-checking-block",
        ),
        pytest.param(
            "type Rate = float\n" + MEASURE_TAIL,
            "line 1 is a module-level TypeAlias statement",
            id="type-alias",
        ),
        pytest.param(
            "def _helper[*Ts](*args: *Ts) -> tuple[*Ts]:\n    return args\n"
            + MEASURE_TAIL,
            "line 1 computes an annotation of _helper",
            id="unpacked-parameter-annotation",
        ),
        pytest.param(
            # Round-13 review M1: Pydantic reads the bound when it validates,
            # and typing's cache can hand it List[Union[float, Decimal]].
            "from decimal import Decimal\nfrom typing import List, Union\n\n\n"
            "def _pennies[T: List[Union[Decimal, float]]](amounts: T):\n"
            "    return int(amounts[0] * 100)\n" + MEASURE_TAIL,
            "line 5: type parameter T of _pennies has a bound",
            id="type-parameter-bound",
        ),
        pytest.param(
            "def _helper[T: (int, float)](value: T) -> T:\n    return value\n"
            + MEASURE_TAIL,
            "line 1: type parameter T of _helper has a bound, constraints",
            id="type-parameter-constraints",
        ),
        pytest.param(
            "def _helper[T = float](value: T) -> T:\n    return value\n" + MEASURE_TAIL,
            "line 1: type parameter T of _helper has a bound, constraints or default",
            id="type-parameter-default",
        ),
        pytest.param(
            "def _helper[U, **P = [int]](*args: P.args, **kwargs: P.kwargs):\n"
            "    return args\n" + MEASURE_TAIL,
            "line 1: type parameter P of _helper has a bound, constraints or default",
            id="paramspec-default",
        ),
        pytest.param(
            "def _helper[*Ts = *tuple[int]](*args):\n    return args\n" + MEASURE_TAIL,
            "line 1: type parameter Ts of _helper has a bound, constraints or default",
            id="typevartuple-default",
        ),
    ],
)
def test_module_shapes_a_digest_cannot_bind_are_refused(tmp_path, source, match):
    """Rounds 4-7: conditional, repeated or computed bindings, decorators,
    classes and code run at import hold state the source does not fix, so a
    modifier's module may hold only imports, literals and undecorated
    functions, each name bound once."""

    try:
        compile(source, "x", "exec", dont_inherit=True)
    except SyntaxError:
        pytest.skip("this Python refuses the construct itself")
    name = "w4_receipt_r7_shape"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match=match) as refused:
            _identity(module.raise_rate)
        assert "cannot be bound" in str(refused.value)
    finally:
        sys.modules.pop(name, None)


def test_docstrings_annotations_and_a_main_guard_are_allowed(tmp_path):
    source = (
        '"""A measure."""\n\nfrom __future__ import annotations\n\nimport math\n'
        "RATE: float = 0.21\nLIMIT: int\n\n\n"
        "def raise_rate(simulation, cap: float = 1.0) -> None:\n"
        '    """Raise the rate."""\n    simulation.rate = min(RATE, cap) * math.tau\n\n\n'
        'if __name__ == "__main__":\n    raise_rate(object())\n'
    )
    name = "w4_receipt_r7_allowed_shape"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_a_main_guard_with_an_else_branch_is_refused(tmp_path):
    """The else branch runs on import."""

    source = (
        'if __name__ == "__main__":\n    pass\nelse:\n    RATE = 0.30\n' + MEASURE_TAIL
    )
    name = "w4_receipt_r7_main_else"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match="module-level If statement"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


INDIRECT_SOURCE = """
import sys

RATE = 0.21


def raise_rate(simulation):
    module = sys.modules[__name__]
    simulation.rate = getattr(module, "PAYMENT", lambda: RATE)()
"""


def test_names_set_on_the_module_are_refused_however_they_are_read(tmp_path):
    """Round-7 review M2: getattr on the module reads PAYMENT without a
    global load; every name in the namespace must be one the source binds."""

    name = "w4_receipt_r7_indirect"
    try:
        module, _ = _import_source(tmp_path, name, INDIRECT_SOURCE)
        _identity(module.raise_rate)
        module.PAYMENT = functools.partial(float, "0.99")
        with pytest.raises(
            ReceiptError, match="PAYMENT is a value of type functools.partial set on"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("body", "match"),
    [
        ("globals()['RATE']", "uses globals"),
        ("vars()['RATE']", "uses vars"),
        ("locals().get('RATE', RATE)", "uses locals"),
        ("eval('RATE')", "uses eval"),
        ("exec('pass') or RATE", "uses exec"),
        ("compile('RATE', 'x', 'eval') and RATE", "uses compile"),
        ("__import__('math').floor(RATE)", "uses __import__"),
        ("breakpoint() or RATE", "uses breakpoint"),
        ("id(RATE) and RATE", "uses id"),
    ],
)
def test_names_that_reach_the_namespace_or_identities_are_refused(
    tmp_path, body, match
):
    """Round-7 review M2 and round-8 M4: refused by name anywhere."""

    source = (
        f"RATE = 0.21\n\n\ndef raise_rate(simulation):\n    simulation.rate = {body}\n"
    )
    name = "w4_receipt_r8_refused_names"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match=match):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("header", "body", "match"),
    [
        ("from builtins import eval as run\n", "run('RATE')", "imports builtins"),
        ("import builtins\n", "builtins.eval('RATE')", "imports builtins"),
        (
            "from operator import is_\n",
            "0.99 if is_(RATE, RATE) else RATE",
            "imports is_",
        ),
        (
            "import operator\n",
            "0.99 if operator.is_(RATE, RATE) else RATE",
            r"uses \.is_",
        ),
        ("import operator\n", "operator.is_not(RATE, None) and RATE", r"uses \.is_not"),
    ],
    ids=[
        "builtins-alias",
        "builtins-module",
        "operator-is",
        "operator-attribute",
        "is-not",
    ],
)
def test_aliases_of_refused_names_are_refused(tmp_path, header, body, match):
    """Round-8 review M3/M4: from builtins import eval as run, operator.is_."""

    source = (
        header
        + f"RATE = 0.21\n\n\ndef raise_rate(simulation):\n    simulation.rate = {body}\n"
    )
    name = "w4_receipt_r8_aliases"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match=match):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_an_import_rebound_at_run_time_is_refused(tmp_path):
    """Round-7 review M4: the name must still be what its import binds."""

    import math

    source = "from math import floor\n\n\ndef raise_rate(simulation):\n    simulation.rate = floor(0.21)\n"
    name = "w4_receipt_r7_import_rebound"
    try:
        module, _ = _import_source(tmp_path, name, source)
        _identity(module.raise_rate)
        module.floor = math.ceil
        with pytest.raises(
            ReceiptError, match="floor is not what `from math import floor` binds"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_an_imported_module_replaced_at_run_time_is_refused(tmp_path):
    source = "import math\n\n\ndef raise_rate(simulation):\n    simulation.rate = math.floor(0.21)\n"
    name = "w4_receipt_r7_module_rebound"
    try:
        module, _ = _import_source(tmp_path, name, source)
        _identity(module.raise_rate)
        module.math = SimpleNamespace(floor=lambda value: 0.99)
        with pytest.raises(ReceiptError, match="math is not what `import math` binds"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_an_unused_imported_value_is_refused(tmp_path):
    """Indirect reads cannot be ruled out, so every imported name is judged."""

    source = "from math import pi\n" + MEASURE_TAIL
    name = "w4_receipt_r7_unused_import"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match="pi is an imported value of type float"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("target", ["_helper", "raise_rate"])
def test_functions_carrying_attributes_are_refused(tmp_path, target):
    """Round-7 review M5: helper.amount set at run time is state."""

    source = (
        "def _helper():\n    return getattr(_helper, 'amount', 0.21)\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = _helper()\n"
    )
    name = "w4_receipt_r7_function_attributes"
    try:
        module, _ = _import_source(tmp_path, name, source)
        _identity(module.raise_rate)
        getattr(module, target).amount = 240
        with pytest.raises(ReceiptError, match=f"function {target} carries attributes"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_literal_constants_that_are_one_mutable_object_are_refused(tmp_path):
    """Round-7 review M6: rebinding B to A's list passes each value check."""

    source = (
        "A = []\nB = []\n\n\ndef raise_rate(simulation):\n"
        "    A.append(1)\n    simulation.rate = 0.99 if B else 0.21\n    A.clear()\n"
    )
    name = "w4_receipt_r7_constant_alias"
    try:
        module, _ = _import_source(tmp_path, name, source)
        _identity(module.raise_rate)
        module.B = module.A
        with pytest.raises(ReceiptError, match="constant [AB] .*are one list object"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("expression", "refused"),
    [
        ("first is second", True),
        ("first is not second", True),
        ("id(first) == id(second)", True),
        ("first is None", False),
        ("second is not None", False),
        ("type(first) is tuple", False),
        ("first == second", False),
    ],
)
def test_identity_comparisons_are_refused(tmp_path, expression, refused):
    """Round-7 review M6: equal immutable values may or may not be one object
    (the compiler merges equal constants), so code telling them apart by
    identity cannot be bound by their values."""

    source = (
        "def raise_rate(simulation, first=(1,), second=(1,)):\n"
        f"    simulation.rate = 0.99 if {expression} else 0.21\n"
    )
    name = "w4_receipt_r7_identity"
    try:
        module, _ = _import_source(tmp_path, name, source)
        if refused:
            with pytest.raises(ReceiptError, match="compares identities|calls id"):
                _identity(module.raise_rate)
        else:
            assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_a_class_inside_the_modifier_reads_its_own_names(tmp_path):
    """Round-7 review L7: LOAD_NAME in a class body reads the class's own
    binding; a module literal of the same name is checked by value too."""

    for prefix in ("", "first = 5\n"):
        source = (
            prefix + "\n\ndef raise_rate(simulation):\n"
            "    class Local:\n        first = 120\n        second = first * 2\n"
            "    simulation.rate = Local.second\n"
        )
        name = "w4_receipt_r7_class_local"
        try:
            module, _ = _import_source(tmp_path, name, source)
            assert _identity(module.raise_rate)
        finally:
            sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("body", "match", "minimum"),
    [
        ("    class Local:\n        value = vars()\n", "uses vars", (3, 11)),
        ("    class Local:\n        type Alias = vars\n", "uses vars", (3, 12)),
        ("    global RATE\n    del RATE\n", "declares RATE global", (3, 11)),
    ],
    ids=["class-body", "class-type-alias", "delete-global"],
)
def test_refusals_reach_class_bodies_type_aliases_and_globals(
    tmp_path, body, match, minimum
):
    """Round-7 review L8: these compile to LOAD_NAME, LOAD_FROM_DICT_OR_GLOBALS
    and DELETE_GLOBAL; the module-wide rules see them in the source."""

    if sys.version_info < minimum:
        pytest.skip("this Python has no such construct")
    source = (
        "RATE = 0.21\n\n\ndef raise_rate(simulation):\n"
        + body
        + "    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r7_opcodes"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match=match):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def _with_constants(code, constants):
    return code.replace(co_consts=tuple(constants))


def _skip_if_constants_are_merged():
    """Python 3.14 merges equal constants whenever it makes a code object, a
    loaded cache included, so two equal tuples cannot stay apart there."""

    code = compile("x = None", "x", "exec", dont_inherit=True)
    split = _with_constants(code, [((1,), tuple([1])), None]).co_consts[0]
    if split[0] is split[1]:
        pytest.skip("this Python merges equal constants in every code object")


def test_shared_constants_are_other_code_than_equal_ones():
    """Round-7 review H1: ``items[0] is items[1]`` differs between a shared
    tuple and two equal tuples, so code_shape keeps sharing."""

    _skip_if_constants_are_merged()
    from policyengine.provenance.bytecode import code_shape

    code = compile("items = None\n", "x", "exec", dont_inherit=True)
    inner = (1,)
    shared = _with_constants(code, [(inner, inner), None])
    split = _with_constants(code, [((1,), tuple([1])), None])
    assert code_shape(shared) != code_shape(split)
    other = tuple([1])  # another object, shared the same way
    assert code_shape(shared) == code_shape(
        _with_constants(code, [(other, other), None])
    )


def test_sharing_counts_across_nested_code_and_in_frozensets():
    """Round-8 review: a constant shared by a function and its module, or
    inside a frozenset, is told apart from equal copies."""

    _skip_if_constants_are_merged()
    from policyengine.provenance.bytecode import code_shape

    module = compile("def f():\n    return None\n", "x", "exec", dont_inherit=True)
    function = next(c for c in module.co_consts if isinstance(c, CodeType))
    item = (1, 2)
    nested_shared = _with_constants(
        module,
        [
            _with_constants(function, [item])
            if c is function
            else (item if c is None else c)
            for c in module.co_consts
        ],
    )
    nested_split = _with_constants(
        module,
        [
            _with_constants(function, [tuple([1, 2])])
            if c is function
            else (item if c is None else c)
            for c in module.co_consts
        ],
    )
    assert code_shape(nested_shared) != code_shape(nested_split)

    member = (3,)
    frozen_shared = _with_constants(module, [frozenset({(member, member)}), None])
    frozen_split = _with_constants(module, [frozenset({(member, tuple([3]))}), None])
    assert code_shape(frozen_shared) != code_shape(frozen_split)


# --- Round-8 review findings -------------------------------------------------------


def test_annotated_constants_and_functions_bind_on_every_python(tmp_path):
    """Round-8 review M5: Python 3.14 compiles annotations to __annotate__
    functions, which are the compiler's, not the module's definitions."""

    source = (
        "RATE: float = 0.21\n\n\n"
        "def raise_rate(simulation: object, cap: float = 1.0) -> None:\n"
        "    simulation.rate = min(RATE, cap)\n"
    )
    name = "w4_receipt_r8_annotations"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_a_main_guard_binds_nothing_on_import(tmp_path):
    """Round-8 review L6: names bound only in the guard are not missing."""

    source = (
        "RATE = 0.21\n\n\ndef raise_rate(simulation):\n    simulation.rate = RATE\n\n\n"
        'if __name__ == "__main__":\n    DEMO = 1\n\n    def demo():\n        return DEMO\n'
    )
    name = "w4_receipt_r8_guard_bindings"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("guard", "allowed"),
    [
        ('if __name__ == "__main__":', True),
        ('if "__main__" == __name__:', True),
        ('if __name__ != "__main__":', False),
        ('if __name__ == "measures":', False),
        ('if __name__ == "__main__" and RATE:', False),
    ],
)
def test_only_a_true_main_guard_is_allowed(tmp_path, guard, allowed):
    source = "RATE = 0.21\n" + guard + "\n    pass\n" + MEASURE_TAIL
    name = "w4_receipt_r8_guards"
    try:
        module, _ = _import_source(tmp_path, name, source)
        if allowed:
            assert _identity(module.raise_rate)
        else:
            with pytest.raises(ReceiptError, match="module-level If statement"):
                _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    "source",
    [
        "def type(value):\n    return value\n\n\n"
        "def raise_rate(simulation, first=(1,), second=(1,)):\n"
        "    simulation.rate = 0.99 if first is type(second) else 0.21\n",
        "def raise_rate(simulation, type=tuple):\n    simulation.rate = 0.21\n",
        "def raise_rate(simulation):\n    type = str\n    simulation.rate = 0.21\n",
    ],
    ids=["def", "parameter", "local"],
)
def test_rebinding_type_is_refused(tmp_path, source):
    """Round-8 review M3: is type(x) is safe only while type is the builtin."""

    name = "w4_receipt_r8_type"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match="rebinds type"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("body", "match"),
    [
        ("_helper.__doc__", r"reads \.__doc__"),
        ("raise_rate.__annotations__", r"reads \.__annotations__"),
        ("simulation.__dict__", r"reads \.__dict__"),
        ("__doc__", "reads __doc__"),
        ("__builtins__", "reads __builtins__"),
        ("__annotations__", "reads __annotations__"),
    ],
)
def test_introspection_is_refused(tmp_path, body, match):
    """Round-8 review M1/M2: what a function or module says about itself."""

    source = (
        '"""Doc."""\n\n\ndef _helper():\n    """0.21"""\n\n\n'
        f"def raise_rate(simulation):\n    simulation.rate = {body}\n"
    )
    name = "w4_receipt_r8_introspection"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match=match):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_name_and_file_may_be_read(tmp_path):
    source = (
        "def raise_rate(simulation):\n"
        "    simulation.where = (__name__, __file__, raise_rate.__name__)\n"
    )
    name = "w4_receipt_r8_name_file"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


FUNCTION_STATE_SOURCE = (
    '"""Measures."""\n\n\ndef _helper(value: float) -> float:\n'
    '    """Double it.\n\n        Indented.\n    """\n    return value * 2\n\n\n'
    "def raise_rate(simulation):\n    simulation.rate = _helper(0.21)\n"
)


def _rename(module):
    module._helper.__name__ = "other"


def _redoc(module):
    module._helper.__doc__ = "240"


def _reannotate(module):
    module._helper.__annotations__ = {"value": float}


def _redoc_module(module):
    module.__doc__ = "240"


def _inject_dunder(module):
    module.__payment__ = 240


def _foreign_builtins(module):
    import builtins

    namespace = vars(module)
    namespace["__builtins__"] = {**vars(builtins), "min": max}


def _function_with_foreign_builtins(module):
    import builtins
    import types

    namespace = vars(module)
    original = namespace["__builtins__"]
    namespace["__builtins__"] = {**vars(builtins), "min": max}
    try:  # a function takes its builtins from its globals when it is made
        helper = types.FunctionType(module._helper.__code__, namespace)
    finally:
        namespace["__builtins__"] = original
    module._helper = helper


@pytest.mark.parametrize(
    ("change", "match"),
    [
        (_rename, "renamed"),
        (_function_with_foreign_builtins, "_helper does not use the builtins module"),
        (_redoc, "_helper's __doc__ is not its source docstring"),
        (_reannotate, "annotations are not those its source declares"),
        (_redoc_module, "module's __doc__ is not its source docstring"),
        (_inject_dunder, "__payment__ is a value of type int set on the module"),
        (_foreign_builtins, "__builtins__ is not the builtins module"),
    ],
)
def test_metadata_changed_at_run_time_is_refused(tmp_path, change, match):
    """Round-8 review M1/M2: names, docstrings, annotations, builtins and
    dunder names are not in the code, so each must be what the source made.
    A multi-line docstring compares as the compiler stores it."""

    name = "w4_receipt_r8_metadata"
    try:
        module, _ = _import_source(tmp_path, name, FUNCTION_STATE_SOURCE)
        assert _identity(module.raise_rate)
        change(module)
        with pytest.raises(ReceiptError, match=match):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("annotation", "match"),
    [
        ("int(1)", "computes the annotation of x"),
        ("[t for t in (int,)]", "annotation of x"),
        ("(lambda: int)", "annotation of x"),
    ],
    ids=["call", "comprehension", "lambda"],
)
def test_computed_annotations_are_refused(tmp_path, annotation, match):
    """Round-8 review M2: a module annotation runs at import and computes
    __annotations__; an annotation may only name types."""

    source = f"x: {annotation} = 1\n" + MEASURE_TAIL
    try:
        compile(source, "x", "exec", dont_inherit=True)
    except SyntaxError:
        pytest.skip("this Python refuses the annotation itself")
    name = "w4_receipt_r8_annotation"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match=match):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_a_computed_parameter_annotation_is_refused(tmp_path):
    source = "def raise_rate(simulation: int(1)):\n    simulation.rate = 0.21\n"
    name = "w4_receipt_r8_parameter_annotation"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match="computes an annotation of raise_rate"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_a_star_imported_name_rebound_at_run_time_is_refused(tmp_path):
    """Round-8 review L7: a star-provided name must be that module's own and
    judged like an explicit import."""

    exporter = "w4_receipt_r8_star_source"
    name = "w4_receipt_r8_star"
    try:
        _import_source(
            tmp_path,
            exporter,
            '__all__ = ["double"]\n\n\ndef double(value):\n    return value * 2\n',
        )
        module, _ = _import_source(
            tmp_path,
            name,
            f"from {exporter} import *\n\n\n"
            "def raise_rate(simulation):\n    simulation.rate = double(0.105)\n",
        )
        assert _identity(module.raise_rate)
        module.double = lambda value: 0.99
        with pytest.raises(
            ReceiptError, match="double is a value of type function set on"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)
        sys.modules.pop(exporter, None)


def test_a_star_import_of_data_values_is_refused(tmp_path):
    source = "from math import *\n" + MEASURE_TAIL
    name = "w4_receipt_r8_star_data"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match="an imported value of type float"):
            _identity(module.raise_rate)  # math exports pi, e, tau, inf, nan
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("definition", "match"),
    [
        ("__measure__", "defines __measure__"),
        # A module __getattr__ answers every attribute, inspect's included.
        ("__getattr__", "cannot be bound"),
    ],
)
def test_dunder_definitions_are_refused(tmp_path, definition, match):
    source = f"def {definition}(name=None):\n    return 0.21\n" + MEASURE_TAIL
    name = "w4_receipt_r8_dunder_def"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match=match):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


# --- Round-9 review findings -------------------------------------------------------


@pytest.mark.parametrize(
    "package", ["policyengine", "policyengine-uk", "policyengine-core"]
)
def test_versions_installed_after_loading_are_refused(
    dataset_file, monkeypatch, package
):
    """Round-9 review H1: upgrading a package mid-session changes what the
    metadata says but not the code already imported."""

    from policyengine.provenance import loaded

    _build(dataset_file)  # the installed versions are what was loaded
    monkeypatch.setitem(loaded._LOADED, package, "0.0.1")
    with pytest.raises(
        ReceiptError,
        match=rf"{package} 0\.0\.1 was loaded in this process, but .* is installed now",
    ):
        _build(dataset_file)


def test_the_first_loaded_version_is_the_one_kept(monkeypatch):
    from policyengine.provenance import loaded

    monkeypatch.setattr(loaded, "_LOADED", {})
    loaded.record_loaded_versions(["policyengine-uk", "no-such-distribution"])
    first = loaded.loaded_versions()
    assert set(first) == {"policyengine-uk"}
    monkeypatch.setattr(
        loaded.metadata, "version", lambda name: "99.0.0"
    )  # an upgrade after loading
    loaded.record_loaded_versions(["policyengine-uk"])
    assert loaded.loaded_versions() == first


def _assert_recording_subprocess(source):
    result = subprocess.run(
        [sys.executable, "-c", source],
        env={**os.environ, "POLICYENGINE_SKIP_COUNTRY_IMPORTS": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_importing_the_wrapper_records_its_actual_version():
    _assert_recording_subprocess(
        "from importlib import metadata\n"
        "import policyengine\n"
        "from policyengine.provenance.loaded import loaded_versions\n"
        "assert loaded_versions() == {'policyengine': metadata.version('policyengine')}\n"
    )


def test_constructing_a_model_records_all_actual_package_versions():
    _assert_recording_subprocess(
        "from importlib import metadata\n"
        "from policyengine.provenance import loaded\n"
        "from policyengine.tax_benefit_models.common.model_version import MicrosimulationModelVersion\n"
        "loaded._LOADED.clear()\n"
        "class Recorded(Exception):\n    pass\n"
        "class RecordingProbe(MicrosimulationModelVersion):\n"
        "    country_code = 'uk'\n"
        "    package_name = 'policyengine-uk'\n"
        "    @classmethod\n"
        "    def _get_runtime_data_build_metadata(cls):\n"
        "        raise Recorded\n"
        "try:\n    RecordingProbe()\n"
        "except Recorded:\n    pass\n"
        "else:\n    raise AssertionError('probe did not reach its recording hook')\n"
        "assert loaded.loaded_versions() == {\n"
        "    name: metadata.version(name)\n"
        "    for name in ('policyengine', 'policyengine-uk', 'policyengine-core')\n"
        "}\n"
    )


def test_missing_loaded_versions_build_when_installation_predates_process(
    dataset_file, monkeypatch
):
    from policyengine.provenance import loaded

    monkeypatch.setattr(loaded, "_LOADED", {})
    receipt = _build(dataset_file)
    assert receipt.wrapper.version == INSTALLED_WRAPPER
    assert receipt.model.version == INSTALLED_UK
    assert receipt.core.version == INSTALLED_CORE


@pytest.mark.parametrize(
    "package", ["policyengine", "policyengine-uk", "policyengine-core"]
)
def test_each_package_installed_during_process_is_refused(
    dataset_file, monkeypatch, tmp_path, package
):
    directory = tmp_path / "new.dist-info"
    directory.mkdir()
    (directory / "METADATA").write_text("new installation")
    original = receipt_module._distribution_metadata_directory
    monkeypatch.setattr(
        receipt_module,
        "_distribution_metadata_directory",
        lambda name: directory if name == package else original(name),
    )
    with pytest.raises(
        ReceiptError,
        match=rf"{package} was installed or changed after this process started.*restart",
    ):
        _build(dataset_file)


@pytest.mark.parametrize(
    "filename", ["", "METADATA", "RECORD", "INSTALLER", "direct_url.json"]
)
@pytest.mark.parametrize("clock", ["st_mtime", "st_ctime"])
def test_every_install_metadata_timestamp_counts(monkeypatch, filename, clock):
    class MetadataPath:
        def __init__(self, name=""):
            self.name = name

        def __truediv__(self, name):
            return MetadataPath(name)

        def exists(self):
            return True

        def stat(self):
            values = {"st_mtime": 1.0, "st_ctime": 1.0}
            if self.name == filename:
                values[clock] = 3.0
            return SimpleNamespace(**values)

    monkeypatch.setattr(
        receipt_module, "_distribution_metadata_directory", lambda name: MetadataPath()
    )
    monkeypatch.setattr(
        receipt_module.psutil,
        "Process",
        lambda: SimpleNamespace(create_time=lambda: 2.0),
    )
    with pytest.raises(ReceiptError, match="installed or changed after this process"):
        receipt_module._refuse_package_changed_after_process_start("policyengine")


def test_unlocatable_install_metadata_is_refused(monkeypatch, tmp_path):
    distribution = SimpleNamespace(
        files=[], locate_file=lambda path: tmp_path, version="1.0"
    )
    monkeypatch.setattr(
        receipt_module.metadata, "distribution", lambda name: distribution
    )
    with pytest.raises(ReceiptError, match="Cannot locate.*policyengine.*restart"):
        receipt_module._refuse_package_changed_after_process_start("policyengine")


def test_install_metadata_with_empty_record_uses_the_public_root(monkeypatch, tmp_path):
    directory = tmp_path / "policyengine-1.0.dist-info"
    directory.mkdir()
    (directory / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: policyengine\nVersion: 1.0\n"
    )
    (directory / "RECORD").write_text("")
    distribution = metadata.Distribution.at(directory)
    monkeypatch.setattr(
        receipt_module.metadata, "distribution", lambda name: distribution
    )
    assert receipt_module._distribution_metadata_directory("policyengine") == directory


@pytest.mark.parametrize("stem", ["policyengine-1.0", "policyengine,local-1.0"])
def test_install_metadata_uses_record_without_allocating_all_file_paths(
    monkeypatch, tmp_path, stem
):
    directory = tmp_path / f"{stem}.dist-info"
    directory.mkdir()
    record = f'\nother/module.py,,\npackage/METADATA,,\n"{stem}.dist-info/METADATA",,\n'

    class Distribution:
        @property
        def files(self):
            raise AssertionError(
                "RECORD is available; a full file listing is unnecessary"
            )

        def read_text(self, filename):
            assert filename == "RECORD"
            return record

        def locate_file(self, path):
            return tmp_path / path if path else tmp_path / "no-root"

    monkeypatch.setattr(
        receipt_module.metadata, "distribution", lambda name: Distribution()
    )
    assert receipt_module._distribution_metadata_directory("policyengine") == directory


def test_install_metadata_prefers_the_distributions_public_file_listing(
    monkeypatch, tmp_path
):
    directory = tmp_path / "policyengine-1.0.dist-info"
    directory.mkdir()
    listed = Path("policyengine-1.0.dist-info/METADATA")
    distribution = SimpleNamespace(
        files=[listed],
        locate_file=lambda path: tmp_path / path if path else tmp_path / "no-root",
    )
    monkeypatch.setattr(
        receipt_module.metadata, "distribution", lambda name: distribution
    )
    assert receipt_module._distribution_metadata_directory("policyengine") == directory


def test_install_metadata_fallback_matches_both_package_and_version(
    monkeypatch, tmp_path
):
    for package, version in [
        ("policyengine", "1.0"),
        ("policyengine", "2.0"),
        ("other", "1.0"),
    ]:
        directory = tmp_path / f"{package}-{version}.dist-info"
        directory.mkdir()
        (directory / "METADATA").write_text(
            f"Metadata-Version: 2.1\nName: {package}\nVersion: {version}\n"
        )
    distribution = SimpleNamespace(
        files=[], locate_file=lambda path: tmp_path, version="1.0"
    )
    monkeypatch.setattr(
        receipt_module.metadata, "distribution", lambda name: distribution
    )
    assert receipt_module._distribution_metadata_directory("policyengine") == (
        tmp_path / "policyengine-1.0.dist-info"
    )


def test_ambiguous_install_metadata_is_refused(monkeypatch, tmp_path):
    for stem in ("policyengine-1.0", "policyengine_duplicate-1.0"):
        directory = tmp_path / f"{stem}.dist-info"
        directory.mkdir()
        (directory / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: policyengine\nVersion: 1.0\n"
        )
    distribution = SimpleNamespace(
        files=[], locate_file=lambda path: tmp_path, version="1.0"
    )
    monkeypatch.setattr(
        receipt_module.metadata, "distribution", lambda name: distribution
    )
    with pytest.raises(ReceiptError, match="Cannot locate.*policyengine"):
        receipt_module._distribution_metadata_directory("policyengine")


def test_unreadable_install_metadata_is_refused(monkeypatch):
    def unreadable(name):
        raise OSError("metadata unreadable")

    monkeypatch.setattr(receipt_module, "_distribution_metadata_directory", unreadable)
    with pytest.raises(
        ReceiptError, match="Cannot locate or read.*policyengine.*restart"
    ):
        receipt_module._refuse_package_changed_after_process_start("policyengine")


def test_unreadable_process_start_time_is_refused(monkeypatch):
    def unreadable():
        raise receipt_module.psutil.AccessDenied()

    monkeypatch.setattr(receipt_module.psutil, "Process", unreadable)
    with pytest.raises(
        ReceiptError, match="Cannot locate or read.*policyengine.*restart"
    ):
        receipt_module._refuse_package_changed_after_process_start("policyengine")


@pytest.mark.parametrize(
    ("header", "body", "match"),
    [
        ("import typing\n", "typing.get_type_hints(_helper)", r"\.get_type_hints"),
        (
            "from typing import get_type_hints\n",
            "get_type_hints(_helper)",
            "get_type_hints",
        ),
        ("import inspect\n", "inspect.signature(_helper)", r"\.signature"),
        ("import inspect\n", "inspect.getfullargspec(_helper)", r"\.getfullargspec"),
        ("import inspect\n", "inspect.get_annotations(_helper)", r"\.get_annotations"),
        ("from inspect import signature\n", "signature(_helper)", "signature"),
        (
            "from inspect import getfullargspec\n",
            "getfullargspec(_helper)",
            "getfullargspec",
        ),
        (
            "from inspect import get_annotations\n",
            "get_annotations(_helper)",
            "get_annotations",
        ),
        (
            "import inspect\n",
            "inspect.Signature.from_callable(_helper)",
            r"\.from_callable",
        ),
    ],
    ids=[
        "get-type-hints",
        "imported-get-type-hints",
        "signature",
        "argspec",
        "get-annotations",
        "imported-signature",
        "imported-argspec",
        "imported-get-annotations",
        "signature-from-callable",
    ],
)
def test_readers_of_annotation_values_are_refused(tmp_path, header, body, match):
    """Explicit annotation readers remain outside the accepted module shape,
    even though annotation values are checked."""

    source = (
        header + "\n\ndef _helper(value: float) -> float:\n    return value\n\n\n"
        f"def raise_rate(simulation):\n    simulation.hints = {body}\n"
    )
    name = "w4_receipt_r9_annotation_readers"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match=match) as refused:
            _identity(module.raise_rate)
        assert "reads annotation values" in str(refused.value)
    finally:
        sys.modules.pop(name, None)


DISPATCH_SOURCE = (
    "import functools\n\n\n"
    "def default_annual_income(income):\n    return income\n\n\n"
    "def weekly_annual_income(income: int):\n    return income * 52\n\n\n"
    "def raise_rate(simulation):\n"
    "    annual_income = functools.singledispatch(default_annual_income)\n"
    "    annual_income.register(weekly_annual_income)\n"
    "    simulation.result = annual_income(simulation.income)\n"
)


@pytest.mark.parametrize("managed", [False, True], ids=["builder", "microsimulation"])
def test_singledispatch_annotations_are_rechecked_at_receipt_build(
    tmp_path, dataset_file, managed
):
    name = "w4_receipt_r11_dispatch"
    try:
        module, _ = _import_source(tmp_path, name, DISPATCH_SOURCE)
        identity = scenario_reform_identity(
            _scenario(simulation_modifier=module.raise_rate), code_revision=REVISION
        )
        bundle = _bundle_for(dataset_file.read_bytes())

        def build(result):
            if managed:
                return build_execution_receipt_for_microsimulation(
                    _managed_simulation(dataset_file, bundle),
                    years=[2026],
                    reform=identity,
                    baseline=reform_identity(None),
                    bundle=bundle,
                    outputs={"annual_income": result},
                )
            return _build(
                dataset_file, reform=identity, outputs={"annual_income": result}
            )

        simulation = SimpleNamespace(income=1)
        module.raise_rate(simulation)
        assert simulation.result == 52
        assert build(simulation.result).certification_status == "certified"
        module.weekly_annual_income.__annotations__["income"] = float
        module.raise_rate(simulation)
        assert simulation.result == 1
        with pytest.raises(
            ReceiptError,
            match="weekly_annual_income.*annotation for income.*source names",
        ):
            build(simulation.result)
    finally:
        sys.modules.pop(name, None)


def test_unedited_singledispatch_helper_binds(tmp_path):
    name = "w4_receipt_r11_unedited_dispatch"
    try:
        module, _ = _import_source(tmp_path, name, DISPATCH_SOURCE)
        before = _identity(module.raise_rate)
        simulation = SimpleNamespace(income=1)
        module.raise_rate(simulation)
        assert simulation.result == 52
        assert _identity(module.raise_rate) == before
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("annotation", "changed"),
    [
        ("int", float),
        ("datetime.date", datetime.datetime),
        ("list[int]", list[float]),
        ("dict[str, list[int]]", dict[str, list[float]]),
        ("int | str", int | float),
        ("'int'", "float"),
        ("None", float),
        ("1", True),
    ],
    ids=[
        "name",
        "attribute",
        "generic",
        "nested-generic",
        "union",
        "string",
        "none",
        "literal-type",
    ],
)
def test_annotation_values_must_match_source(tmp_path, annotation, changed):
    source = (
        "import datetime\n\n\n"
        f"def _helper(value: {annotation}):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = _helper(0.21)\n"
    )
    name = "w4_receipt_r11_annotation_values"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
        module._helper.__annotations__["value"] = changed
        with pytest.raises(
            ReceiptError, match="_helper.*annotation for value.*source names"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("parameter", ["value", "args", "keyword", "kwargs", "return"])
def test_each_annotation_position_is_checked(tmp_path, parameter):
    source = (
        "def _helper(value: int, /, *args: int, keyword: int, **kwargs: int) -> int:\n"
        "    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r11_annotation_positions"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
        module._helper.__annotations__[parameter] = float
        with pytest.raises(
            ReceiptError, match=f"_helper.*annotation for {parameter}.*source names"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("annotation", "changed"),
    [
        ("list[int]", list[int]),
        ("int | str", int | str),
    ],
    ids=["generic", "union"],
)
def test_equal_reconstructed_annotations_bind(tmp_path, annotation, changed):
    source = (
        f"def _helper(value: {annotation}):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r11_equal_annotations"
    try:
        module, _ = _import_source(tmp_path, name, source)
        before = _identity(module.raise_rate)
        original = module._helper.__annotations__["value"]
        assert changed is not original
        assert changed == original
        module._helper.__annotations__["value"] = changed
        assert _identity(module.raise_rate) == before
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("annotation", "changed"),
    [
        ("int | str", "str | int"),
        ("list[int | str]", "list[str | int]"),
        ("dict[str, list[int | str]]", "dict[str, list[str | int]]"),
        ("tuple[int, str]", "tuple[str, int]"),
        ("list[int]", "tuple[int]"),
        ("list[int]", "list[int, str]"),
        ("Callable[[int, str], float]", "Callable[[str, int], float]"),
        ("Callable[[int, str], float]", "Callable[[int, str, bool], float]"),
        ("Literal[1]", "Literal[True]"),
    ],
    ids=[
        "union",
        "generic-union",
        "nested-union",
        "arguments",
        "origin",
        "arity",
        "callable-order",
        "callable-arity",
        "literal-type",
    ],
)
def test_annotation_origins_and_arguments_must_match_in_order(
    tmp_path, annotation, changed
):
    source = (
        "from typing import Callable, Literal\n\n\n"
        f"def _helper(value: {annotation}):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r12_ordered_annotations"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
        module._helper.__annotations__["value"] = eval(changed, module.__dict__)
        with pytest.raises(
            ReceiptError, match="_helper.*annotation for value.*source names"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_callable_annotation_argument_containers_are_checked(tmp_path):
    from collections.abc import Callable
    from types import GenericAlias

    source = (
        "from typing import Callable\n\n\n"
        "def _helper(value: Callable[[int, str], float]):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r12_callable_argument_containers"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
        module._helper.__annotations__["value"] = GenericAlias(
            Callable, ((int, str), float)
        )
        with pytest.raises(
            ReceiptError, match="_helper.*annotation for value.*source names"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_distinct_union_origins_are_refused(tmp_path):
    if sys.version_info >= (3, 14):
        pytest.skip("Python 3.14 unifies typing and built-in union origins")
    source = (
        "def _helper(value: int | str):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r12_union_origins"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
        module._helper.__annotations__["value"] = Union[int, str]
        with pytest.raises(
            ReceiptError, match="_helper.*annotation for value.*source names"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("typing_alias", [False, True], ids=["builtin", "typing"])
def test_parameterised_aliases_only_use_cache_free_substitution(
    tmp_path, monkeypatch, typing_alias
):
    from typing import List, TypeVar

    parameter = TypeVar("T")
    provider = SimpleNamespace(
        Alias=List[parameter] if typing_alias else list[parameter]
    )
    monkeypatch.setitem(sys.modules, "w4_receipt_alias_provider", provider)
    source = (
        "from w4_receipt_alias_provider import Alias\n"
        "from decimal import Decimal\nfrom typing import Union\n\n\n"
        "def _helper(value: Alias[Union[Decimal, float]]):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r12_alias_substitution"
    try:
        module, _ = _import_source(tmp_path, name, source)
        if typing_alias:
            with pytest.raises(
                ReceiptError, match="_helper.*annotation for value.*cannot be checked"
            ):
                _identity(module.raise_rate)
        else:
            assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    "annotation",
    [
        "List['int']",
        "Optional['int']",
        "Union['int', float]",
        "Annotated['int', 'meta']",
        "Callable[['int'], 'str']",
        "Final['int']",
        "ClassVar['int']",
        "list['int']",
    ],
)
def test_generic_forward_reference_annotations_bind(tmp_path, annotation):
    source = (
        "from typing import Annotated, Callable, ClassVar, Final, List, Optional, Union\n\n\n"
        f"def _helper(value: {annotation}):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r12_forward_references"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("special", ["Final", "ClassVar"])
def test_quoted_special_form_flags_match_this_python(special):
    """Round-18 review: the reconstruction's is_class flag is the
    interpreter's own, so it matches a fresh typing object, not a cached
    (and mutable) one."""

    import typing

    fresh = typing.ForwardRef(
        "x", is_class=receipt_module._SPECIAL_FORM_FORWARD_IS_CLASS
    )
    (built,) = typing.get_args(getattr(typing, special)["_w4_flag_check_" + special])
    assert built.__forward_is_class__ == fresh.__forward_is_class__


@pytest.mark.parametrize("quoted", ["int", "_receipt_forward_probe"])
def test_a_quoted_special_form_with_a_flipped_flag_is_refused(tmp_path, quoted):
    """Round-18 review P2: flipping a quoted Final's ForwardRef flag is an
    annotation that no longer matches its source."""

    source = (
        "from typing import Final\n\n\n"
        f"def _helper(value: Final['{quoted}']):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r18_flipped_flag"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
        (reference,) = get_args(module._helper.__annotations__["value"])
        reference.__forward_is_class__ = not reference.__forward_is_class__
        with pytest.raises(ReceiptError, match="_helper.*annotation for value"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_subscripted_annotations_without_typing_origins_are_refused(
    tmp_path, monkeypatch
):
    from typing import Generic, TypeVar

    from pydantic import BaseModel

    parameter = TypeVar("T")

    class Box(BaseModel, Generic[parameter]):
        pass

    # Older Pydantic versions add a generated class to the caller's module.
    Box[list[int]]
    monkeypatch.setitem(
        sys.modules, "w4_receipt_generic_model", SimpleNamespace(Box=Box)
    )
    source = (
        "from w4_receipt_generic_model import Box\n\n\n"
        "def _helper(value: Box[list[int]]):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r12_generated_annotation_class"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(
            ReceiptError, match="_helper.*annotation for value.*cannot be checked"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("annotation", ["'Alias'", "list['Alias']", "List['Alias']"])
def test_recursive_named_annotation_aliases_bind(tmp_path, monkeypatch, annotation):
    from types import GenericAlias

    provider = SimpleNamespace(Alias=GenericAlias(list, ("Alias",)))
    monkeypatch.setitem(sys.modules, "w4_receipt_recursive_alias", provider)
    source = (
        "from w4_receipt_recursive_alias import Alias\nfrom typing import List\n\n\n"
        f"def _helper(value: {annotation}):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r12_recursive_annotation_alias"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("field", ["text", "module", "is_argument", "is_class"])
def test_forward_reference_annotation_structure_is_checked(tmp_path, field):
    from types import GenericAlias
    from typing import ForwardRef

    source = (
        "from typing import List\n\n\n"
        "def _helper(value: List['int']):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r12_forward_reference_state"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
        changed = ForwardRef(
            "float" if field == "text" else "int",
            module="another_module" if field == "module" else None,
            is_argument=field != "is_argument",
            is_class=field == "is_class",
        )
        module._helper.__annotations__["value"] = GenericAlias(list, (changed,))
        with pytest.raises(
            ReceiptError, match="_helper.*annotation for value.*source names"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    "changed", [False, True], ids=["source-value", "changed-value"]
)
def test_evaluated_forward_reference_annotations_match_source(tmp_path, changed):
    if sys.version_info >= (3, 14):
        pytest.skip("Python 3.14 forward references do not cache evaluated values")
    from typing import get_args

    source = (
        "from typing import List\n\n\n"
        "def _helper(value: List['int']):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r12_evaluated_forward_reference"
    try:
        module, _ = _import_source(tmp_path, name, source)
        reference = get_args(module._helper.__annotations__["value"])[0]
        reference.__forward_evaluated__ = True
        reference.__forward_value__ = float if changed else int
        if changed:
            with pytest.raises(
                ReceiptError, match="_helper.*annotation for value.*source names"
            ):
                _identity(module.raise_rate)
        else:
            assert _identity(module.raise_rate)
    finally:
        # typing's cache can keep this reference across test cases.
        reference.__forward_evaluated__ = False
        reference.__forward_value__ = None
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    "float_first", [False, True], ids=["source-order", "cached-order"]
)
@pytest.mark.parametrize("postponed", [False, True], ids=["eager", "postponed"])
@pytest.mark.parametrize(
    "annotation_kind",
    [
        "unquoted",
        "quoted",
        "double-quoted",
        "builtin-nested-string",
        "typing-nested-string",
        "typing-string-before-validation",
    ],
)
def test_cached_typing_union_order_is_checked_against_source(
    tmp_path, float_first, postponed, annotation_kind
):
    """A fresh process keeps the reproduction independent of typing's cache."""

    annotation = "List[Union[Decimal, float]]"
    nested = annotation_kind in (
        "builtin-nested-string",
        "typing-nested-string",
        "typing-string-before-validation",
    )
    if annotation_kind == "double-quoted":
        annotation = repr(repr(annotation))
    elif annotation_kind == "quoted":
        annotation = repr(annotation)
    elif nested:
        outer = "list" if annotation_kind == "builtin-nested-string" else "List"
        annotation = f"{outer}[{annotation!r}]"
    amount = "amounts[0][0]" if nested else "amounts[0]"
    values = [["0.29"]] if nested else ["0.29"]
    source = ("from __future__ import annotations\n" if postponed else "") + (
        "from decimal import Decimal\nfrom typing import List, Union\n"
        "from pydantic import validate_call\n\n\n"
        f"def pennies(amounts: {annotation}):\n"
        f"    return int({amount} * 100)\n\n\n"
        "def raise_rate(simulation):\n"
        f"    simulation.result = validate_call(pennies)({values!r})\n"
    )
    path = tmp_path / "money_measure.py"
    path.write_text(source)
    script = f"""
import importlib.util
import json
import sys
from decimal import Decimal
from types import SimpleNamespace
from typing import List, Union
from policyengine.provenance.receipt import ReceiptError, _modifier_identity
prime = List[Union[float, Decimal]] if {float_first!r} else List[Union[Decimal, float]]
spec = importlib.util.spec_from_file_location('money_measure', {str(path)!r})
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
simulation = SimpleNamespace()
if {annotation_kind != "typing-string-before-validation"!r}:
    module.raise_rate(simulation)
try:
    _modifier_identity(module.raise_rate, {{'revision': 'a' * 40}})
    outcome = 'accepted'
except ReceiptError as error:
    assert 'annotation for amounts is not what its source names' in str(error)
    outcome = 'refused'
if {annotation_kind == "typing-string-before-validation"!r}:
    module.raise_rate(simulation)
print(json.dumps({{'pennies': simulation.result, 'outcome': outcome}}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "POLICYENGINE_SKIP_COUNTRY_IMPORTS": "1"},
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == {
        "pennies": 28 if float_first else 29,
        "outcome": "refused" if float_first else "accepted",
    }


@pytest.mark.parametrize("annotation", ["NamedType", "list[NamedType]"])
def test_named_annotation_types_are_compared_by_identity(
    tmp_path, monkeypatch, annotation
):
    class EqualTypes(type):
        def __eq__(self, other):
            return True

    class NamedType(metaclass=EqualTypes):
        pass

    class OtherType(metaclass=EqualTypes):
        pass

    provider = SimpleNamespace(NamedType=NamedType)
    monkeypatch.setitem(sys.modules, "w4_receipt_named_type", provider)
    source = (
        "from w4_receipt_named_type import NamedType\n\n\n"
        f"def _helper(value: {annotation}):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r11_named_type_identity"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
        module._helper.__annotations__["value"] = eval(
            annotation, {"NamedType": OtherType}
        )
        with pytest.raises(
            ReceiptError, match="_helper.*annotation for value.*source names"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    "annotation",
    ["Literal[-1, 0, +1]", "Literal[-1.5, +2.0]", "Literal[-1j, +2j]"],
    ids=["integer", "float", "complex"],
)
def test_signed_numeric_literal_annotations_bind(tmp_path, annotation):
    source = (
        "from typing import Literal\n\n\n"
        f"def _helper(value: {annotation} = -1):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = _helper()\n"
    )
    name = "w4_receipt_r12_signed_literals"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    "annotation",
    [
        "Literal[-True]",
        "Literal[-VALUE]",
        "Literal[--1]",
        "Literal[-(1 + 2)]",
        "Literal[~1]",
    ],
    ids=["boolean", "name", "nested-unary", "expression", "invert"],
)
def test_signed_annotations_only_allow_direct_numeric_constants(tmp_path, annotation):
    source = (
        "from __future__ import annotations\nfrom typing import Literal\nVALUE = 1\n\n\n"
        f"def _helper(value: {annotation}):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r12_computed_signed_literals"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match="computes an annotation of _helper"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    "annotation",
    ["print('annotation expression ran')", "Literal[-True]", "Literal[-VALUE]"],
)
def test_computed_annotation_strings_are_refused_without_running_them(
    tmp_path, capsys, annotation
):
    source = (
        "from typing import Literal\nVALUE = 1\n\n\n"
        f"def _helper(value: {annotation!r}):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r12_computed_annotation_strings"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(
            ReceiptError, match="_helper.*annotation for value.*cannot be checked"
        ):
            _identity(module.raise_rate)
        assert capsys.readouterr().out == ""
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    "annotation",
    [
        "'unbound_name'",
        "'return'",
        "Literal['print(1)']",
        "Literal['print(1)', 'print(1)']",
        "Annotated[int, 'print(1)']",
    ],
)
def test_annotation_string_literals_and_metadata_bind(tmp_path, annotation):
    source = (
        "from typing import Annotated, Literal\n\n\n"
        f"def _helper(value: {annotation}):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r12_annotation_string_literals"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_cyclic_annotation_strings_are_refused():
    script = """
from policyengine.provenance.receipt import _annotation_string_state
try:
    _annotation_string_state('X', {'X': 'Y', 'Y': 'X'})
except ValueError as error:
    assert 'resolution cycle' in str(error)
    print('refused')
else:
    raise AssertionError('cyclic annotation accepted')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "POLICYENGINE_SKIP_COUNTRY_IMPORTS": "1"},
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert result.stdout == "refused\n"


def test_future_annotations_match_the_compilers_strings(tmp_path):
    source = (
        "from __future__ import annotations\n\n\n"
        "def _helper(value: ((list [ int ])), literal: 'str', /, "
        "*args: tuple[int, ...], optional: (int | None), "
        "**kwargs: dict[str, list[float]]) -> 'return':\n"
        "    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r11_future_annotations"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert module._helper.__annotations__ == {
            "value": "list[int]",
            "literal": "'str'",
            "args": "tuple[int, ...]",
            "optional": "int | None",
            "kwargs": "dict[str, list[float]]",
            "return": "'return'",
        }
        assert _identity(module.raise_rate)
        module._helper.__annotations__["value"] = "list[float]"
        with pytest.raises(
            ReceiptError, match="_helper.*annotation for value.*source names"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


GENERIC_SOURCE = (
    "def helper[T](value: T) -> T:\n    return value\n\n\n"
    "def raise_rate(simulation):\n    simulation.rate = helper(0.21)\n"
)


@pytest.mark.parametrize("changed", ["other-parameter", "args-proxy"])
def test_generic_paramspec_annotations_bind_and_are_checked(tmp_path, changed):
    if sys.version_info < (3, 12):
        pytest.skip("type parameters need Python 3.12")
    from typing import ParamSpec

    source = (
        "def helper[**P](*args: P.args, **kwargs: P.kwargs):\n"
        "    return args\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = helper(0.21)[0]\n"
    )
    name = "w4_receipt_r11_generic_paramspec"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
        module.helper.__annotations__["kwargs"] = (
            ParamSpec("Other").kwargs
            if changed == "other-parameter"
            else module.helper.__type_params__[0].args
        )
        with pytest.raises(
            ReceiptError, match="helper.*annotation for kwargs.*source names"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_generic_helpers_bind_and_are_checked(tmp_path):
    """Round-9 review L3: ``def helper[T]`` compiles inside a wrapper that
    binds T; the function is still checked against its source."""

    if sys.version_info < (3, 12):
        pytest.skip("type parameters need Python 3.12")
    name = "w4_receipt_r9_generic"
    try:
        module, path = _import_source(tmp_path, name, GENERIC_SOURCE)
        assert _identity(module.raise_rate)
        _edit(path, "return value", "return value * 2")
        with pytest.raises(ReceiptError, match="no longer matches"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def _replacement_type_parameters(module, change):
    from typing import ParamSpec, TypeVar, TypeVarTuple

    original = module.helper.__type_params__
    # Built only for the case asked for: TypeVar(default=...) needs 3.13.
    return {
        "none": lambda: (),
        "extra": lambda: (*original, TypeVar("U", infer_variance=True)),
        "renamed": lambda: (TypeVar("U", infer_variance=True),),
        "paramspec": lambda: (ParamSpec("T", infer_variance=True),),
        "typevartuple": lambda: (TypeVarTuple("T"),),
        "bound": lambda: (TypeVar("T", bound=int, infer_variance=True),),
        "constraints": lambda: (TypeVar("T", int, float, infer_variance=True),),
        "covariant": lambda: (TypeVar("T", covariant=True),),
        "declared-invariant": lambda: (TypeVar("T"),),
        "default": lambda: (TypeVar("T", default=int, infer_variance=True),),
    }[change]()


@pytest.mark.parametrize(
    ("change", "match"),
    [
        ("none", "type parameters are not those its source declares"),
        ("extra", "type parameters are not those its source declares"),
        ("renamed", "type parameters are not those its source declares"),
        ("paramspec", "type parameters are not those its source declares"),
        ("typevartuple", "type parameters are not those its source declares"),
        ("bound", "type parameter T holds a bound"),
        ("constraints", "type parameter T holds a bound"),
        ("covariant", "type parameter T holds a bound"),
        ("declared-invariant", "type parameter T holds a bound"),
        pytest.param(
            "default",
            "type parameter T holds a bound",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 13), reason="type parameter defaults need 3.13"
            ),
        ),
        # A bare stand-in passes the parameter check, but the annotation
        # still names the parameter the def made.
        ("stand-in", "annotation for value is not what its source names"),
    ],
)
def test_generic_type_parameters_must_be_those_the_def_made(tmp_path, change, match):
    """Round-13 review M1: ``__type_params__`` is writable, and a bound,
    constraints or default would be read lazily through typing's cache."""

    if sys.version_info < (3, 12):
        pytest.skip("type parameters need Python 3.12")
    from typing import TypeVar

    name = "w4_receipt_r13_type_parameters"
    try:
        module, _ = _import_source(tmp_path, name, GENERIC_SOURCE)
        assert _identity(module.raise_rate)
        module.helper.__type_params__ = (
            (TypeVar("T", infer_variance=True),)
            if change == "stand-in"
            else _replacement_type_parameters(module, change)
        )
        with pytest.raises(ReceiptError, match=f"helper's {match}"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


RUNTIME_ALIAS_HEAD = (
    "import collections.abc\nimport typing\nfrom decimal import Decimal\n"
    "from typing import Annotated, Dict, List, Literal, Optional, Union\n\n\n"
)


@pytest.mark.parametrize(
    ("body", "base"),
    [
        pytest.param(
            "    def pennies(amounts: List[Union[Decimal, float]]):\n"
            "        return int(amounts[0] * 100)\n\n"
            "    simulation.rate = pennies([0.21])\n",
            "List",
            id="nested-annotation",
        ),
        pytest.param(
            "    def pennies[T: List[Union[Decimal, float]]](amounts: T):\n"
            "        return int(amounts[0] * 100)\n\n"
            "    simulation.rate = pennies([0.21])\n",
            "List",
            id="nested-generic-bound",
        ),
        pytest.param(
            "    def pennies(amounts: 'List[Union[Decimal, float]]'):\n"
            "        return int(amounts[0] * 100)\n\n"
            "    simulation.rate = pennies([0.21])\n",
            "List",
            id="quoted-nested-annotation",
        ),
        pytest.param(
            "    def pennies(amount: Optional[Decimal | float] = None):\n"
            "        return amount\n\n"
            "    simulation.rate = pennies(0.21)\n",
            "Optional",
            id="optional-of-a-union",
        ),
        pytest.param(
            "    shape = Dict[str, Union[Decimal, float]]\n"
            "    simulation.rate = 0.21 if shape else 0.0\n",
            "Dict",
            id="expression-in-the-body",
        ),
        pytest.param(
            "    shape = typing.List[Decimal | float]\n"
            "    simulation.rate = 0.21 if shape else 0.0\n",
            "typing.List",
            id="attribute-of-typing",
        ),
        pytest.param(
            "    from typing import Sequence as Seq\n\n"
            "    shape = Seq[Union[Decimal, float]]\n"
            "    simulation.rate = 0.21 if shape else 0.0\n",
            "Seq",
            id="import-inside-the-function",
        ),
        pytest.param(
            "    class Amounts(typing.NamedTuple):\n"
            "        values: List[Decimal | float]\n\n"
            "    simulation.rate = 0.21 if Amounts else 0.0\n",
            "List",
            id="class-body-annotation",
        ),
        pytest.param(
            "    class Amounts(typing.NamedTuple):\n"
            "        values: 'List[Decimal | float]'\n\n"
            "    simulation.rate = 0.21 if Amounts else 0.0\n",
            "List",
            id="quoted-class-body-annotation",
        ),
        pytest.param(
            "    shape = Union[Union[Decimal, float], None]\n"
            "    simulation.rate = 0.21 if shape else 0.0\n",
            "Union",
            id="union-of-a-union",
            # Python 3.14 made Union a class that builds unions in source
            # order without typing's cache, so the rule rightly allows it.
            marks=pytest.mark.skipif(
                sys.version_info >= (3, 14), reason="ordered on Python 3.14"
            ),
        ),
        pytest.param(
            # Round-15 review M1: one name, imported differently in two scopes.
            "    def pennies(amounts):\n"
            "        from typing import Sequence\n\n"
            "        shape = Sequence[Union[Decimal, float]]\n"
            "        return shape and amounts\n\n"
            "    def is_many(values):\n"
            "        from collections.abc import Sequence\n\n"
            "        return isinstance(values, Sequence)\n\n"
            "    simulation.rate = 0.21 if is_many(pennies([1])) else 0.0\n",
            "Sequence",
            id="name-imported-in-two-scopes",
        ),
        pytest.param(
            "    def is_many(values):\n"
            "        from collections.abc import Sequence\n\n"
            "        return isinstance(values, Sequence)\n\n"
            "    def pennies(amounts):\n"
            "        from typing import Sequence\n\n"
            "        shape = Sequence[Union[Decimal, float]]\n"
            "        return shape and amounts\n\n"
            "    simulation.rate = 0.21 if is_many(pennies([1])) else 0.0\n",
            "Sequence",
            id="name-imported-in-two-scopes-typing-last",
        ),
        pytest.param(
            "    from w4_receipt_r15_aliases import MONEY\n\n"
            "    shape = List[MONEY]\n"
            "    simulation.rate = 0.21 if shape else 0.0\n",
            "List",
            id="imported-union-alias",
        ),
        pytest.param(
            # Round-15 review M2: a forward reference inside a subscript.
            "    def pennies(amounts: Optional['List[Union[Decimal, float]]'] = None):\n"
            "        return amounts\n\n"
            "    simulation.rate = 0.21 if pennies() is None else 0.0\n",
            "Optional",
            id="forward-reference-inside-a-subscript",
        ),
        pytest.param(
            "    def pennies[T: 'List[Union[Decimal, float]]'](amounts: T):\n"
            "        return amounts\n\n"
            "    simulation.rate = pennies([0.21])[0]\n",
            "List",
            id="quoted-nested-generic-bound",
        ),
        pytest.param(
            "    def pennies[T = 'List[Union[Decimal, float]]'](amounts: T):\n"
            "        return amounts\n\n"
            "    simulation.rate = pennies([0.21])[0]\n",
            "List",
            id="quoted-nested-generic-default",
        ),
        pytest.param(
            "    def period(kind: List[Literal['weekly', 'monthly']]):\n"
            "        return kind\n\n"
            "    simulation.rate = 0.21 if period(['weekly']) else 0.0\n",
            "List",
            id="list-of-a-literal",
        ),
        pytest.param(
            "    from pydantic import RootModel\n\n"
            "    amount = RootModel[Decimal | float](0.21)\n"
            "    simulation.rate = float(amount.root)\n",
            "RootModel",
            id="pydantic-generic-model",
        ),
    ],
)
def test_typing_aliases_built_with_a_union_inside_functions_are_refused(
    tmp_path, body, base
):
    """Round-14 review M1: code inside a function runs after import, so a
    typing generic subscripted with a union there can return an alias cached
    for the same members in another order; Pydantic tries them in order."""

    source = RUNTIME_ALIAS_HEAD + "def raise_rate(simulation):\n" + body
    try:
        compile(source, "x", "exec", dont_inherit=True)
    except SyntaxError:
        pytest.skip("this Python refuses the construct itself")
    name = "w4_receipt_r14_runtime_alias"
    try:
        _import_source(
            tmp_path,
            "w4_receipt_r15_aliases",
            "from decimal import Decimal\n\nMONEY = Decimal | float\n",
        )
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(
            ReceiptError,
            match=rf"function raise_rate subscripts {re.escape(base)} with a union",
        ) as refused:
            _identity(module.raise_rate)
        assert "cannot be bound" in str(refused.value)
    finally:
        sys.modules.pop(name, None)
        sys.modules.pop("w4_receipt_r15_aliases", None)


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            "    def pennies(amounts: list[Decimal | float]):\n"
            "        return int(amounts[0] * 100)\n\n"
            "    simulation.rate = pennies([0.21])\n",
            id="builtin-generic-of-a-union",
        ),
        pytest.param(
            "    def pennies(amounts: dict[str, Decimal | float] | None = None):\n"
            "        return amounts\n\n"
            "    simulation.rate = 0.21 if pennies() is None else 0.0\n",
            id="builtin-dict-and-pipe",
        ),
        pytest.param(
            "    def pennies(amounts: collections.abc.Sequence[Decimal | float]):\n"
            "        return int(amounts[0] * 100)\n\n"
            "    simulation.rate = pennies([0.21])\n",
            id="collections-abc-generic-of-a-union",
        ),
        pytest.param(
            "    def pennies(amount: Union[Decimal, float]):\n"
            "        return amount\n\n"
            "    simulation.rate = pennies(0.21)\n",
            id="bare-union",
        ),
        pytest.param(
            "    def pennies(amounts: List[float], scale: Optional[float] = None):\n"
            "        return amounts\n\n"
            "    simulation.rate = pennies([0.21])[0]\n",
            id="typing-generics-without-a-union",
        ),
        pytest.param(
            "    rates = [0.20, 0.21]\n    mask = 1 | 0\n"
            "    simulation.rate = rates[mask | 1]\n",
            id="value-subscript-with-bitwise-or",
        ),
        pytest.param(
            "    def helper[T](value: T) -> T:\n        return value\n\n"
            "    simulation.rate = helper(0.21)\n",
            id="nested-bare-generic",
        ),
        pytest.param(
            # Round-15 review L1: NumPy builds an ordered types.GenericAlias.
            "    import numpy as np\n\n"
            "    def scale(values: np.ndarray[tuple[int], np.dtype[np.float64 | np.int64]]):\n"
            "        return values\n\n"
            "    simulation.rate = float(scale(np.array([0.21]))[0])\n",
            id="numpy-array-of-a-union",
        ),
        pytest.param(
            # Literal values and Annotated metadata are strings, not types.
            "    def period(kind: list[Literal['List[Union[Decimal, float]]']]):\n"
            "        return kind\n\n"
            "    def rate(value: Annotated[float, 'Optional[Decimal | float]']):\n"
            "        return value\n\n"
            "    simulation.rate = rate(0.21)\n",
            id="literal-values-and-annotated-metadata",
        ),
        pytest.param(
            "    label = 'income_tax'\n    path = 'gov.hmrc.rates[0]'\n"
            "    simulation.rate = 0.21 if label and path else 0.0\n",
            id="ordinary-strings",
        ),
    ],
)
def test_ordinary_types_and_subscripts_inside_functions_bind(tmp_path, body):
    source = RUNTIME_ALIAS_HEAD + "def raise_rate(simulation):\n" + body
    try:
        compile(source, "x", "exec", dont_inherit=True)
    except SyntaxError:
        pytest.skip("this Python refuses the construct itself")
    name = "w4_receipt_r14_runtime_alias_ok"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.skipif(
    sys.version_info < (3, 14), reason="Union caches by equality before 3.14"
)
def test_a_union_of_a_union_binds_where_typing_keeps_its_order(tmp_path):
    source = (
        RUNTIME_ALIAS_HEAD + "def raise_rate(simulation):\n"
        "    shape = Union[Union[Decimal, float], None]\n"
        "    simulation.rate = 0.21 if shape else 0.0\n"
    )
    name = "w4_receipt_union_of_union_314"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_a_top_level_signature_with_a_typing_union_still_binds(tmp_path):
    """Module-level signatures are compared with their source in order, so
    the function-code rule leaves them alone."""

    source = (
        RUNTIME_ALIAS_HEAD
        + "def _pennies(amounts: List[Union[Decimal, float]]) -> int:\n"
        "    return int(amounts[0] * 100)\n" + MEASURE_TAIL
    )
    name = "w4_receipt_r14_top_level_union"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("replaced", ["distribution", "metadata"])
def test_the_install_fixture_still_checks_synthetic_metadata(
    tmp_path, monkeypatch, replaced
):
    """Round-14 review L: the fixture takes a real module as loaded from its
    install only while the install metadata is the real one too."""

    site = tmp_path / "site"
    real = receipt_module.metadata
    synthetic = SimpleNamespace(
        version=real.version("policyengine"),
        read_text=lambda name: (
            "policyengine/__init__.py,,\n" if name == "RECORD" else None
        ),
        locate_file=lambda name: site / name,
    )

    def distribution(name):
        return synthetic if name == "policyengine" else real.distribution(name)

    if replaced == "distribution":
        monkeypatch.setattr(real, "distribution", distribution)
    else:
        monkeypatch.setattr(
            receipt_module,
            "metadata",
            SimpleNamespace(
                distribution=distribution,
                version=real.version,
                PackageNotFoundError=real.PackageNotFoundError,
            ),
        )
    with pytest.raises(ReceiptError, match="from RECORD"):
        receipt_module._refuse_loaded_package_origin("policyengine")


def _code(source, name):
    namespace = {}
    exec(compile(source, "x", "exec", dont_inherit=True), namespace)
    return namespace[name].__code__


_FUNCTION = "def f(a, /, b, *, c):\n    return x + a + b + c\n"


def _inner_code():
    namespace = {}
    exec(compile(_CLOSURE, "x", "exec", dont_inherit=True), namespace)
    return namespace["outer"]().__code__


_CLOSURE = "def outer():\n    v = 1\n\n    def inner():\n        return v\n\n    return inner\n"


@pytest.mark.parametrize(
    ("make", "change"),
    [
        (lambda: _code(_FUNCTION, "f"), {"co_name": "g"}),
        (lambda: _code(_FUNCTION, "f"), {"co_qualname": "g"}),
        (lambda: _code(_FUNCTION, "f"), {"co_argcount": 1}),
        (lambda: _code(_FUNCTION, "f"), {"co_posonlyargcount": 0}),
        (lambda: _code(_FUNCTION, "f"), {"co_kwonlyargcount": 0}),
        (lambda: _code(_FUNCTION, "f"), {"co_flags": "toggle"}),
        (lambda: _code(_FUNCTION, "f"), {"co_stacksize": "grow"}),
        (lambda: _code(_FUNCTION, "f"), {"co_names": ("y",)}),
        (lambda: _code(_FUNCTION, "f"), {"co_varnames": ("a", "b", "d")}),
        (lambda: _code(_CLOSURE, "outer"), {"co_cellvars": ("w",)}),
        (lambda: _inner_code(), {"co_freevars": ("w",)}),
    ],
    ids=[
        "name",
        "qualname",
        "argcount",
        "posonlyargcount",
        "kwonlyargcount",
        "flags",
        "stacksize",
        "names",
        "varnames",
        "cellvars",
        "freevars",
    ],
)
def test_every_code_field_counts(make, change):
    """Round-9 review: dropping any field from code_shape survived; each is
    what the interpreter runs (co_flags, for one, tells a coroutine)."""

    from policyengine.provenance.bytecode import code_shape

    code = make()
    field, value = next(iter(change.items()))
    if value == "toggle":
        value = code.co_flags ^ inspect.CO_NESTED
    elif value == "grow":
        value = code.co_stacksize + 1
    assert code_shape(code.replace(**{field: value})) != code_shape(code)


def test_a_guard_on_another_name_is_refused(tmp_path):
    """Round-9 review: only __name__ makes the main guard."""

    source = 'if __file__ == "__main__":\n    pass\n' + MEASURE_TAIL
    name = "w4_receipt_r9_guard_name"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match="module-level If statement"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_is_against_a_call_other_than_type_is_refused(tmp_path):
    """Round-9 review: only ``type(...)`` is a safe identity operand."""

    source = (
        "def raise_rate(simulation, first=(1,), second=(1,)):\n"
        "    simulation.rate = 0.99 if first is tuple(second) else 0.21\n"
    )
    name = "w4_receipt_r9_identity_call"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match="compares identities"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_an_imported_from_callable_is_refused(tmp_path, monkeypatch):
    provider = SimpleNamespace(from_callable=inspect.Signature.from_callable)
    monkeypatch.setitem(sys.modules, "w4_receipt_annotation_provider", provider)
    source = (
        "from w4_receipt_annotation_provider import from_callable as reader\n"
        "\n\ndef _helper(value: float) -> float:\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.hints = reader(_helper)\n"
    )
    name = "w4_receipt_r10_imported_from_callable"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(
            ReceiptError, match="imports from_callable.*reads annotation values"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("operation", ["getattr", "hasattr", "setattr", "delattr"])
@pytest.mark.parametrize(
    ("attribute", "match"),
    [
        ('"__annotations__"', "__annotations__.*introspection"),
        ('"__doc__"', "__doc__.*introspection"),
        ('"__anno" + "tations__"', "non-literal attribute name"),
        ("attribute", "non-literal attribute name"),
        ("123", "non-literal attribute name"),
    ],
    ids=["annotations", "docstring", "computed", "variable", "non-string"],
)
def test_attribute_operations_cannot_expose_unbound_state(
    tmp_path, operation, attribute, match
):
    extra = ", {}" if operation == "setattr" else ""
    source = (
        "def _helper(value: float) -> float:\n    return value\n\n\n"
        "def raise_rate(simulation):\n    attribute = '__annotations__'\n"
        f"    {operation}(_helper, {attribute}{extra})\n"
        "    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r10_attribute_operations"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match=match):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("attribute", ["rate", "__init__", "__name__"])
def test_attribute_operations_allow_plain_names_and_allowed_dunders(
    tmp_path, attribute
):
    source = (
        "def raise_rate(simulation):\n"
        f"    simulation.rate = getattr(simulation, '{attribute}', 0.21)\n"
    )
    name = "w4_receipt_r10_allowed_attribute"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("kind", [set, bytearray])
def test_shared_set_and_bytearray_defaults_are_refused(tmp_path, kind):
    source = (
        f"def raise_rate(simulation, first={kind.__name__}(), second={kind.__name__}()):\n"
        "    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r10_shared_defaults"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert receipt_module._shared_default_object([module.raise_rate]) is None
        shared = kind()
        module.raise_rate.__defaults__ = (shared, shared)
        with pytest.raises(ReceiptError, match=f"are one {kind.__name__} object"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_shared_set_constants_are_refused(tmp_path):
    source = (
        "FIRST = {2026}\nSECOND = {2026}\n\n\n"
        "def raise_rate(simulation):\n"
        "    FIRST.add(2027)\n"
        "    simulation.rate = 0.30 if 2027 in SECOND else 0.21\n"
        "    FIRST.remove(2027)\n"
    )
    name = "w4_receipt_r10_shared_set_constants"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
        simulation = SimpleNamespace()
        module.raise_rate(simulation)
        assert simulation.rate == 0.21
        module.SECOND = module.FIRST
        module.raise_rate(simulation)
        assert simulation.rate == 0.30
        with pytest.raises(ReceiptError, match="are one set object"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("literal", "changed"),
    [("1j", complex(-0.0, 1.0)), ("0j", complex(0.0, -0.0))],
    ids=["real-zero", "imaginary-zero"],
)
def test_complex_literal_components_keep_the_sign_of_zero(tmp_path, literal, changed):
    source = f"PHASE = {literal}\n" + MEASURE_TAIL
    name = "w4_receipt_r10_complex_zero"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
        assert module.PHASE == changed
        module.PHASE = changed
        with pytest.raises(ReceiptError, match="PHASE is.*at run time"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_a_main_guard_redefining_a_function_is_refused(tmp_path):
    source = (
        "def _helper(value):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = _helper(0.21)\n\n\n"
        'if __name__ == "__main__":\n'
        "    def _helper(value):\n        return value * 2\n"
    )
    name = "w4_receipt_r10_multiple_shapes"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(
            ReceiptError, match="function _helper has 2 different definitions"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)
