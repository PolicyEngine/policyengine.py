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
- a composition's digest covers its members' representation, digest and
  binding in application order and nothing else: reordering distinct members
  changes it, current-law members and labels do not, and it is code-bound
  exactly when a member is;
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
import sys
from collections.abc import Mapping
from importlib import metadata
from pathlib import Path
from types import CodeType, SimpleNamespace

import jsonschema
import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from policyengine.provenance import receipt as receipt_module
from policyengine.provenance.canonical import CanonicalJSONError, canonical_sha256
from policyengine.provenance.receipt import (
    ExecutionReceipt,
    FiscalYearConvention,
    ReceiptError,
    ReformIdentity,
    build_execution_receipt,
    build_execution_receipt_for_microsimulation,
    certificate_sha256,
    composed_reform_identity,
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


@pytest.fixture
def dataset_file(tmp_path):
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
        {"archive_info": {"hashes": {"sha256": "b" * 64}}},
        ["not", "an", "object"],
    ],
    ids=["sdist", "zip", "directory", "no-url", "not-an-object"],
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


# --- Compositions ------------------------------------------------------------------


def _member(index: int, *, code: bool = False, name=None) -> ReformIdentity:
    return ReformIdentity(
        kind="reform",
        representation="policyengine-uk.scenario/v1",
        reform_sha256=f"{index:064x}",
        binding="code_revision" if code else "content",
        name=name,
    )


def _compose(members, *, early: bool = False, name=None) -> ReformIdentity:
    return composed_reform_identity(members, applied_before_data_load=early, name=name)


def _composition_digest(early: bool, *members: ReformIdentity) -> str:
    """The published preimage, restated: phase plus ordered member identities."""

    return canonical_sha256(
        {
            "representation": "policyengine-uk.scenario_composition/v1",
            "payload": {
                "applied_before_data_load": early,
                "application": "parameter_changes_then_modifiers",
                "members": [
                    {
                        "representation": member.representation,
                        "reform_sha256": member.reform_sha256,
                        "binding": member.binding,
                    }
                    for member in members
                ],
            },
        }
    )


def test_composition_digest_is_its_phase_and_ordered_member_identities():
    basic = reform_identity(
        {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027-04-06": 0.21}},
        "policyengine-uk.reform_dict/v1",
        name="basic rate",
    )
    structural = scenario_reform_identity(
        _scenario(simulation_modifier=receipt_modifiers.raise_higher_rate),
        code_revision=REVISION,
        name="higher rate",
    )
    package = _compose([basic, structural], name="Budget package")
    assert package.representation == "policyengine-uk.scenario_composition/v1"
    assert package.binding == "code_revision"
    assert package.name == "Budget package"
    assert package.reform_sha256 == _composition_digest(False, basic, structural)
    assert _compose([basic]).binding == "content"
    assert _compose([basic]).reform_sha256 == _composition_digest(False, basic)
    assert _compose([basic]).reform_sha256 != basic.reform_sha256
    nested = _compose([package, basic], early=True)
    assert nested.binding == "code_revision"
    assert nested.reform_sha256 == _composition_digest(True, package, basic)


def test_the_phase_the_combined_scenario_runs_in_is_bound():
    """#579 review: Scenario.__add__ resets the phase, so it must be stated."""

    members = [_member(1), _member(2)]
    early = _compose(members, early=True)
    late = _compose(members, early=False)
    assert early.reform_sha256 != late.reform_sha256
    assert early.reform_sha256 == _composition_digest(True, *members)
    with pytest.raises(TypeError):
        composed_reform_identity(members)  # the phase has no default
    for phase in (0, 1, None, "False"):
        with pytest.raises(ReceiptError, match="applied_before_data_load"):
            composed_reform_identity(members, applied_before_data_load=phase)


@settings(max_examples=100, deadline=None)
@given(
    indices=st.lists(st.integers(1, 50), min_size=2, max_size=6, unique=True),
    code=st.lists(st.booleans(), min_size=6, max_size=6),
    random=st.randoms(),
    gaps=st.lists(st.integers(0, 6), max_size=4),
    labels=st.lists(st.text(max_size=5), min_size=6, max_size=6),
    early=st.booleans(),
)
def test_composition_order_matters_and_current_law_and_labels_do_not(
    indices, code, random, gaps, labels, early
):
    members = [_member(i, code=code[n]) for n, i in enumerate(indices)]
    composed = _compose(members, early=early)
    assert composed.reform_sha256 == _composition_digest(early, *members)
    assert composed.binding == (
        "code_revision" if any(code[: len(members)]) else "content"
    )
    shuffled = list(members)
    random.shuffle(shuffled)
    same_order = shuffled == members
    assert (
        _compose(shuffled, early=early).reform_sha256 == composed.reform_sha256
    ) == same_order
    padded = list(members)
    for gap in gaps:
        padded.insert(
            min(gap, len(padded)),
            ReformIdentity(kind="current_law", name=labels[gap % 6] or None),
        )
    assert _compose(padded, early=early).reform_sha256 == composed.reform_sha256
    relabelled = [
        member.model_copy(update={"name": labels[n] or None})
        for n, member in enumerate(members)
    ]
    assert (
        _compose(relabelled, early=early, name="x").reform_sha256
        == composed.reform_sha256
    )
    # Dropping or duplicating a member changes what ran, so it changes the digest.
    assert _compose(members[1:], early=early).reform_sha256 != composed.reform_sha256
    assert (
        _compose([*members, members[0]], early=early).reform_sha256
        != composed.reform_sha256
    )


@settings(max_examples=50, deadline=None)
@given(
    indices=st.lists(st.integers(1, 50), min_size=1, max_size=5, unique=True),
    position=st.integers(0, 4),
    change=st.sampled_from(["digest", "representation", "binding"]),
)
def test_changing_any_one_member_changes_the_composition(indices, position, change):
    """A nested identity's every bound member reaches the composition digest."""

    members = [_member(i) for i in indices]
    inner = _compose(members)
    target = position % len(members)
    edited = list(members)
    if change == "digest":
        edited[target] = _member(indices[target] + 100)
    elif change == "representation":
        edited[target] = edited[target].model_copy(
            update={"representation": "policyengine-uk.reform_dict/v1"}
        )
    else:
        edited[target] = _member(indices[target], code=True)
    assert _compose(edited).reform_sha256 != inner.reform_sha256
    # The same holds one level down, through a nested composition.
    assert (
        _compose([_compose(edited), _member(99)]).reform_sha256
        != _compose([inner, _member(99)]).reform_sha256
    )


def test_a_composition_of_nothing_is_current_law_with_its_own_name():
    named = ReformIdentity(kind="current_law", name="no change")
    assert _compose([]).kind == "current_law"
    assert _compose([CURRENT_LAW, named]) == ReformIdentity(kind="current_law")
    assert _compose([named], name="package") == ReformIdentity(
        kind="current_law", name="package"
    )
    assert (
        _compose([named, _member(1)]).reform_sha256
        == _compose([_member(1)]).reform_sha256
    )


@pytest.mark.parametrize(
    "update",
    [
        {"kind": "current_law"},  # a reform's digest kept under current law
        {"reform_sha256": "XYZ"},
        {"reform_sha256": None},
        {"representation": "not-a-representation"},
        {"binding": "anything"},
    ],
    ids=["kind", "digest", "no-digest", "representation", "binding"],
)
def test_members_edited_past_their_rules_are_refused(update):
    """#579 review: an invalid member is refused, never dropped or hashed."""

    real = reform_identity(
        {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027-04-06": 0.21}},
        "policyengine-uk.reform_dict/v1",
    )
    forged = real.model_copy(update=update)
    with pytest.raises(ReceiptError, match="Member 1 is not a valid identity"):
        _compose([_member(1), forged])


@pytest.mark.parametrize(
    "members",
    [
        {"gov.x": {"2027": 1}},
        "abc",
        [{"gov.x": {"2027": 1}}],
        [_member(1), "member"],
        [_member(1), None],
        _member(1),
        {},
        "",
        b"",
        (member for member in [_member(1)]),
        frozenset(),
    ],
    ids=[
        "dict",
        "string",
        "raw payload",
        "string member",
        "none member",
        "bare",
        "empty dict",
        "empty string",
        "empty bytes",
        "generator",
        "set",
    ],
)
def test_compositions_take_only_bound_identities(members):
    with pytest.raises(ReceiptError):
        _compose(members)


def test_any_sequence_of_members_is_the_same_composition():
    """Round-4 review: a tuple, a list and a UserList are one composition."""

    from collections import UserList

    members = [_member(1), _member(2, code=True)]
    assert _compose(tuple(members)) == _compose(list(members))
    assert _compose(UserList(members)) == _compose(list(members))


@pytest.mark.parametrize("members", [[], [CURRENT_LAW], [CURRENT_LAW, CURRENT_LAW]])
@pytest.mark.parametrize("phase", [0, 1, None, "True"])
def test_the_phase_is_checked_even_when_nothing_changes(members, phase):
    """Round-3 review: an invalid phase is refused before members are read."""

    with pytest.raises(ReceiptError, match="applied_before_data_load"):
        composed_reform_identity(members, applied_before_data_load=phase)


def test_reform_identity_refuses_the_composition_representation():
    with pytest.raises(ReceiptError, match="composed_reform_identity"):
        reform_identity({"members": []}, "policyengine-uk.scenario_composition/v1")


def test_a_composed_reform_makes_a_valid_receipt(dataset_file, schema_validator):
    package = _compose([_member(1), _member(2, code=True)])
    receipt = _build(dataset_file, reform=package)
    schema_validator.validate(json.loads(receipt.model_dump_json()))
    assert ExecutionReceipt.model_validate_json(receipt.to_canonical_json()) == receipt
    other = _build(dataset_file, reform=_compose([_member(2, code=True), _member(1)]))
    assert other.receipt_sha256 != receipt.receipt_sha256
    assert other.execution_identity_sha256 == receipt.execution_identity_sha256


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


def test_versions_installed_after_loading_are_refused(dataset_file, monkeypatch):
    """Round-9 review H1: upgrading a package mid-session changes what the
    metadata says but not the code already imported."""

    from policyengine.provenance import loaded

    _build(dataset_file)  # the installed versions are what was loaded
    monkeypatch.setitem(loaded._LOADED, "policyengine-uk", "0.0.1")
    with pytest.raises(
        ReceiptError,
        match=r"policyengine-uk 0\.0\.1 was loaded in this process, but .* is installed now",
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
    ],
    ids=[
        "get-type-hints",
        "imported-get-type-hints",
        "signature",
        "argspec",
        "get-annotations",
    ],
)
def test_readers_of_annotation_values_are_refused(tmp_path, header, body, match):
    """Round-9 review M2: annotation values are not bound, so code may not
    read them."""

    source = (
        header + "\n\ndef _helper(value: float) -> float:\n    return value\n\n\n"
        f"def raise_rate(simulation):\n    simulation.hints = {body}\n"
    )
    name = "w4_receipt_r9_annotation_readers"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match=match):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


GENERIC_SOURCE = (
    "def helper[T](value: T) -> T:\n    return value\n\n\n"
    "def raise_rate(simulation):\n    simulation.rate = helper(0.21)\n"
)


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


# --- Infinite parameter values in reform payloads ---------------------------------


CAP = "gov.hmrc.pensions.salary_sacrifice_pension_cap"


def _reform_digest(payload):
    return reform_identity(payload, "policyengine-uk.reform_dict/v1").reform_sha256


@pytest.mark.parametrize(
    ("value", "spelling"),
    [(float("inf"), "Infinity"), (float("-inf"), "-Infinity")],
    ids=["inf", "-inf"],
)
def test_an_infinite_parameter_value_binds_by_its_reserved_encoding(value, spelling):
    """An uncapped threshold is ``inf`` in PolicyEngine; the digest names it.

    Round-1 review M2: the spellings are a published contract, so both are
    pinned by their exact canonical bytes.
    """

    from policyengine.provenance.canonical import canonical_json

    payload = {CAP: {"2026-04-06.2100-12-31": value}}
    expected = {
        "representation": "policyengine-uk.reform_dict/v1",
        "payload": {CAP: {"2026-04-06.2100-12-31": {"$nonfinite": spelling}}},
    }
    assert canonical_json(expected) == (
        b'{"payload":{"gov.hmrc.pensions.salary_sacrifice_pension_cap":'
        b'{"2026-04-06.2100-12-31":{"$nonfinite":"' + spelling.encode() + b'"}}},'
        b'"representation":"policyengine-uk.reform_dict/v1"}'
    )
    assert _reform_digest(payload) == canonical_sha256(expected)


def test_an_infinity_in_a_tuple_binds_as_one_in_a_list():
    """Round-1 review L1: tuples are walked like lists."""

    assert _reform_digest({CAP: (float("inf"), 1.0)}) == _reform_digest(
        {CAP: [float("inf"), 1.0]}
    )


def test_infinities_differ_from_each_other_and_from_any_finite_cap():
    values = [float("inf"), float("-inf"), 1e308, 2000.0, 0.0]
    digests = {_reform_digest({CAP: {"2027": value}}) for value in values}
    assert len(digests) == len(values)


def test_a_numpy_infinity_binds_as_a_float_one():
    numpy = pytest.importorskip("numpy")
    for value in (numpy.float64("inf"), numpy.float32("-inf")):
        assert _reform_digest({CAP: {"2027": value}}) == _reform_digest(
            {CAP: {"2027": float(value)}}
        )


class _EqualsNothing(str):
    """A key whose own ``__eq__`` would hide that it spells a reserved key."""

    def __eq__(self, other):
        return False

    __hash__ = str.__hash__


class _Pairs(Mapping):
    """A mapping that yields its pairs as given, equal keys included."""

    def __init__(self, pairs):
        self._pairs = pairs

    def __getitem__(self, key):
        for candidate, value in reversed(self._pairs):
            if candidate is key or candidate == key:
                return value
        raise KeyError(key)

    def __iter__(self):
        return (key for key, _ in self._pairs)

    def __len__(self):
        return len(self._pairs)


class _Level(enum.IntEnum):
    ONE = 1


@pytest.mark.parametrize(
    "payload",
    [
        {CAP: {"2027": {"$nonfinite": "Infinity"}}},
        {"$nonfinite": "Infinity"},
        [{"$nonfinite": "-Infinity"}],
        {CAP: ({"$nonfinite": "Infinity"},)},
        {CAP: {"2027": {_EqualsNothing("$nonfinite"): "Infinity"}}},
    ],
    ids=["value", "top-level", "array-member", "tuple-member", "str-subclass-key"],
)
def test_a_payload_using_the_reserved_key_is_refused(payload):
    """Otherwise the object would digest like the infinity it spells.

    Round-1 review L1 and L3: a tuple is walked like a list, and a ``str``
    subclass that compares unequal to everything is checked by its text.
    """

    with pytest.raises(ReceiptError, match=r"\$nonfinite is reserved"):
        _reform_digest(payload)


@pytest.mark.parametrize(
    "pairs",
    [
        [("2027", 2000.0), ("2027", 1000.0)],
        [("2027", 2000.0), ("2027", float("inf"))],
        [(2027, 2000.0), ("2027", 1000.0)],
        [(_Level.ONE, 2.0), (1, 2.0)],
        [(_EqualsNothing("2027"), 1.0), ("2027", float("inf"))],
    ],
    ids=[
        "duplicate",
        "duplicate-inf",
        "int-and-str",
        "intenum-and-int",
        "str-subclass",
    ],
)
def test_colliding_keys_are_still_refused_with_infinities_allowed(pairs):
    """Round-1 review M1: encoding first used to drop one of the entries."""

    with pytest.raises(ReceiptError, match="collide"):
        _reform_digest({CAP: _Pairs(pairs)})


def test_nan_is_still_refused():
    with pytest.raises(ReceiptError, match="not a finite number"):
        _reform_digest({CAP: {"2027": float("nan")}})


def test_a_scenario_with_an_infinite_parameter_change_binds():
    identity = scenario_reform_identity(
        _scenario(parameter_changes={CAP: {"2027": float("inf")}})
    )
    assert identity.binding == "content"
    assert (
        identity.reform_sha256
        != scenario_reform_identity(
            _scenario(parameter_changes={CAP: {"2027": 1e308}})
        ).reform_sha256
    )


_FINITE_LEAVES = (
    st.none()
    | st.booleans()
    | st.integers(min_value=-(2**60), max_value=2**60)
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.floats(allow_nan=False, allow_infinity=False).map(np.float64)
    | st.floats(allow_nan=False, allow_infinity=False, width=32).map(np.float32)
    | st.integers(min_value=-(2**31), max_value=2**31).map(np.int64)
    | st.booleans().map(np.bool_)
    | st.sampled_from([_Level.ONE])
    | st.text(max_size=6)
    | st.dates()
)
_PAYLOAD_KEYS = st.text(max_size=4).filter(
    lambda key: key != "$nonfinite"
) | st.integers(min_value=-3, max_value=3)
#: Nested payloads of every kind strict conversion takes, finite numbers only.
FINITE_PAYLOADS = st.recursive(
    _FINITE_LEAVES,
    lambda children: (
        st.lists(children, max_size=4)
        | st.lists(children, max_size=4).map(tuple)
        | st.lists(st.tuples(_PAYLOAD_KEYS, children), max_size=4).map(_Pairs)
    ),
    max_leaves=20,
)


def _outcome(digest):
    try:
        return digest()
    except (ReceiptError, CanonicalJSONError):
        return "refused"


@settings(max_examples=300, deadline=None)
@given(payload=st.one_of(REFORM_PAYLOADS, FINITE_PAYLOADS))
def test_payloads_without_infinities_digest_as_before(payload):
    """Differential: allowing infinities changes no finite payload's digest.

    Round-1 review L6: payloads cover nesting, int and colliding keys,
    tuples, nulls, strings, dates, numpy scalars and integers past 2**53;
    each is either digested as before or refused by both.
    """

    from policyengine.provenance.receipt import strict_json_value

    representation = "policyengine-uk.reform_dict/v1"
    if isinstance(payload, (Mapping, list, tuple)) and payload:
        before = _outcome(
            lambda: canonical_sha256(
                strict_json_value(
                    {"representation": representation, "payload": payload}
                )
            )
        )
        assert _outcome(lambda: _reform_digest(payload)) == before


def test_an_infinite_modifier_default_binds_and_nan_is_refused(tmp_path, monkeypatch):
    """Round-1 review L5: an uncapped default binds by ``float.hex()``."""

    plus = _computed_default_identity(tmp_path / "a", monkeypatch, "1e999")
    again = _computed_default_identity(tmp_path / "b", monkeypatch, "1e999")
    minus = _computed_default_identity(tmp_path / "c", monkeypatch, "-1e999")
    largest = _computed_default_identity(
        tmp_path / "d", monkeypatch, "1.7976931348623157e308"
    )
    assert plus == again
    assert len({plus, minus, largest}) == 3
    source = "def raise_rate(simulation, cap=float('nan')):\n    simulation.cap = cap\n"
    name = "w4_receipt_588_nan_default"
    try:
        module, _ = _import_source(tmp_path / "e", name, source)
        with pytest.raises(ReceiptError, match="NaN has no one value"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_typed_infinities_are_spelled_by_float_hex():
    """Round-2 review: the typed encoding of an infinite default is pinned."""

    typed = receipt_module._typed_value
    assert typed(float("inf")) == {"type": "float", "hex": "inf"}
    assert typed(float("-inf")) == {"type": "float", "hex": "-inf"}


class _ForgedDate(datetime.date):
    """A date whose own ``isoformat`` spells a reserved object."""

    def isoformat(self):
        return {"$nonfinite": "Infinity"}


def test_a_date_subclass_digests_as_its_date():
    """Round-2 review: a subclass cannot choose its text, or forge an infinity."""

    forged = _reform_digest({CAP: {"2027": _ForgedDate(2027, 4, 6)}})
    assert forged == _reform_digest({CAP: {"2027": datetime.date(2027, 4, 6)}})
    assert forged != _reform_digest({CAP: {"2027": float("inf")}})
    assert content_sha256([_ForgedDate(2027, 4, 6)]) == content_sha256(["2027-04-06"])


class _OtherText(str):
    """A key whose ``str()`` differs from its characters."""

    def __str__(self):
        return "other"


class _OtherBytes(str):
    """A key whose ``encode`` would change RFC 8785's key order."""

    def encode(self, *args, **kwargs):
        return b"\xff"


def test_string_subclass_keys_digest_by_their_characters():
    """Round-2 review: keys become exact strings in content and reform digests.

    Before #588, an overridden ``encode`` changed the key order RFC 8785
    sorted by; now the key sorts by its characters, as an exact string does.
    """

    assert content_sha256({_OtherText("a"): 1}) == content_sha256({"a": 1})
    assert _reform_digest({_OtherText(CAP): 1.0}) == _reform_digest({CAP: 1.0})
    assert content_sha256({_OtherBytes("z"): 1, "a": 2}) == content_sha256(
        {"z": 1, "a": 2}
    )
    with pytest.raises(ReceiptError, match="collide"):
        content_sha256({_EqualsNothing("a"): 1, "a": 2})


class _HostileChar(str):
    def __eq__(self, other):
        return False

    def __hash__(self):
        return 0


class _ForgedText(str):
    """A string whose iterator would let its text escape its quotes."""

    def __iter__(self):
        return (_HostileChar(char) for char in str.__str__(self))


def test_a_string_subclass_value_cannot_forge_an_infinity():
    """Round-3 review: string values are written as exact strings."""

    forged = _ForgedText('","2028":{"$nonfinite":"Infinity"},"2029":"')
    payload = {CAP: {"2027": forged}}
    assert _reform_digest(payload) == _reform_digest(
        {CAP: {"2027": str.__str__(forged)}}
    )
    assert _reform_digest(payload) != _reform_digest(
        {CAP: {"2027": "", "2028": float("inf"), "2029": ""}}
    )
    assert content_sha256([forged]) == content_sha256([str.__str__(forged)])
