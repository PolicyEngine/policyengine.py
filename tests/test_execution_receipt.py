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
import json
import linecache
import sys
from importlib import metadata
from pathlib import Path
from types import SimpleNamespace

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
from tests import receipt_modifiers

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

    import inspect

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
        receipt_modifiers.make_modifier(0.21),
        lambda simulation: None,
        functools.partial(receipt_modifiers.raise_basic_rate),
        receipt_modifiers.Measure(0.21).apply,
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


def test_rebound_names_are_not_treated_as_constants(tmp_path):
    source = (
        HELPER_SOURCE
        + "\nimport os\nDEBUG = False\nif os.environ.get('W4_X'):\n    DEBUG = True\n"
    )
    name = "w4_receipt_measures_rebound"
    try:
        module, _ = _import_source(tmp_path, name, source)
        module.DEBUG = True  # rebinding a non-constant is not a mismatch
        _measure_identity(module)
    finally:
        sys.modules.pop(name, None)


def test_functions_defined_in_module_level_blocks_bind(tmp_path):
    source = "import sys\nif sys.version_info >= (3,):\n    def raise_rate(simulation):\n        simulation.rate = 0.21\n"
    name = "w4_receipt_measures_block"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _measure_identity(module).binding == "code_revision"
    finally:
        sys.modules.pop(name, None)


def test_conditionally_defined_functions_with_different_code_are_refused(tmp_path):
    """Round-4 review M3: reversing a conditional definition changes what runs."""

    source = (
        "import os\n\nif os.environ.get('W4_ALT'):\n"
        "    def _helper():\n        return 0.30\n"
        "else:\n    def _helper():\n        return 0.21\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = _helper()\n"
    )
    name = "w4_receipt_measures_conditional_definition"
    try:
        module, _ = _import_source(tmp_path, name, source)
        with pytest.raises(ReceiptError, match="2 different definitions"):
            _measure_identity(module)
    finally:
        sys.modules.pop(name, None)


def test_identical_conditional_definitions_bind(tmp_path):
    source = (
        "import sys\n\nif sys.version_info >= (3,):\n"
        "    def raise_rate(simulation):\n        simulation.rate = 0.21\n"
        "else:\n    def raise_rate(simulation):\n        simulation.rate = 0.21\n"
    )
    name = "w4_receipt_measures_identical_definitions"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _measure_identity(module).binding == "code_revision"
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
        "class Measure:\n    rate = 0.21\n\n\n"
        "def raise_rate(simulation, measure=Measure()):\n"
        "    simulation.rate = measure.rate\n"
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


def test_a_comprehension_variable_does_not_unbind_a_constant(tmp_path):
    """Round-4 review M3: a comprehension's own loop variable is not a binding."""

    source = (
        "RATE = 0.21\nRATES = [RATE for RATE in range(3)]\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = RATE\n"
    )
    name = "w4_receipt_measures_comprehension"
    try:
        module, _ = _import_source(tmp_path, name, source)
        _identity(module.raise_rate)
        module.RATE = 0.99
        with pytest.raises(ReceiptError, match="RATE is 0.99 at run time"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_a_walrus_in_a_comprehension_unbinds_a_constant(tmp_path):
    source = (
        "RATE = 0.21\nRATES = [(RATE := x) for x in range(3)]\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = RATE\n"
    )
    name = "w4_receipt_measures_walrus"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert module.RATE == 2
        # RATE is computed, so it is not a constant, and reading it is refused.
        with pytest.raises(ReceiptError, match="reads RATE, a value of type int"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_conditional_literals_admit_each_branch_only(tmp_path, monkeypatch):
    source = (
        "import os\n\nif os.environ.get('W4_HIGH'):\n    RATE = 0.30\n"
        "else:\n    RATE = 0.21\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = RATE\n"
    )
    name = "w4_receipt_measures_conditional"
    monkeypatch.delenv("W4_HIGH", raising=False)
    try:
        module, _ = _import_source(tmp_path, name, source)
        _identity(module.raise_rate)
        module.RATE = 0.30
        _identity(module.raise_rate)
        module.RATE = 0.99
        with pytest.raises(ReceiptError, match=r"RATE is 0.99 at run time but \["):
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


WRAPPED_SOURCE = """
import functools

RATE = 0.21


def _logged(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        return function(*args, **kwargs)

    return wrapper


@_logged
def _helper(value):
    return value * 2


def raise_rate(simulation):
    simulation.rate = _helper(RATE)
"""


def test_a_wrapped_helper_is_checked_through_its_wrapper(tmp_path):
    name = "w4_receipt_r5_wrapped_helper"
    try:
        module, path = _import_source(tmp_path, name, WRAPPED_SOURCE)
        assert _measure_identity(module).binding == "code_revision"
        _edit(path, "return value * 2", "return value * 3")
        with pytest.raises(ReceiptError, match="no longer matches"):
            _measure_identity(module)
    finally:
        sys.modules.pop(name, None)


def test_a_lambda_walrus_does_not_unbind_a_module_constant(tmp_path):
    """Round-5 review: a lambda body is its own scope."""

    source = (
        "RATE = 0.21\nmapper = lambda value: (RATE := value)\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = RATE\n"
    )
    name = "w4_receipt_r5_lambda_walrus"
    try:
        module, _ = _import_source(tmp_path, name, source)
        _identity(module.raise_rate)
        module.RATE = 0.30
        with pytest.raises(ReceiptError, match="RATE is 0.3 at run time"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


def test_a_walrus_in_a_default_binds_the_module(tmp_path):
    """Round-5 review: defaults are evaluated in the enclosing scope."""

    source = (
        "RATE = 0.21\n\n\ndef _helper(value=(RATE := 0.30)):\n    return value\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = RATE\n"
    )
    name = "w4_receipt_r5_default_walrus"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert module.RATE == 0.30
        # Not mistaken for a reassigned constant ("RATE is 0.3 at run time but
        # 0.21"): RATE is computed, and reading it is refused for that reason.
        with pytest.raises(ReceiptError, match="reads RATE, a value of type float"):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


# --- Module globals the modifier reads -------------------------------------------

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
            match=r"modifier reads PAYMENT, a value of type functools\.partial",
        ):
            _identity(module.modifier)
        module.PAYMENT.keywords["amount"] = 240
        with pytest.raises(ReceiptError, match="reads PAYMENT"):
            _identity(module.modifier)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    ("source", "match"),
    [
        pytest.param(
            "import os\nRATE = float(os.environ.get('W4_RATE', '0.21'))\n\n\n"
            "def raise_rate(simulation):\n    simulation.rate = RATE\n",
            r"raise_rate reads RATE, a value of type float computed by the module",
            id="computed-from-the-environment",
        ),
        pytest.param(
            "from functools import partial\n\n\n"
            "def _pay(simulation, amount):\n    simulation.paid = amount\n\n\n"
            "PAY = partial(_pay, amount=120)\n\n\n"
            "def _helper(simulation):\n    PAY(simulation)\n\n\n"
            "def raise_rate(simulation):\n    _helper(simulation)\n",
            r"_helper reads PAY, a value of type functools\.partial",
            id="partial-through-a-helper",
        ),
        pytest.param(
            "import functools\nSCALE = float('2')\n\n\n"
            "def scaled(function):\n    @functools.wraps(function)\n"
            "    def wrapper(value):\n        return function(value) * SCALE\n"
            "    return wrapper\n\n\n"
            "@scaled\ndef _helper(value):\n    return value\n\n\n"
            "def raise_rate(simulation):\n    simulation.rate = _helper(0.21)\n",
            r"scaled\.<locals>\.wrapper reads SCALE",
            id="computed-global-in-a-decorator-wrapper",
        ),
        pytest.param(
            "import os\nSCALE = len(os.sep)\n\n\n"
            "def raise_rate(simulation):\n    scale = lambda rate: rate * SCALE\n"
            "    simulation.rate = scale(0.21)\n",
            r"raise_rate reads SCALE",
            id="computed-global-in-nested-code",
        ),
        pytest.param(
            "class Measure:\n    rate = 0.21\n\n\n"
            "def raise_rate(simulation):\n    simulation.rate = Measure.rate\n",
            r"reads Measure, a class defined in the file",
            id="class-in-the-file",
        ),
        pytest.param(
            "from math import pi\n\n\n"
            "def raise_rate(simulation):\n    simulation.rate = pi / 10\n",
            r"reads pi, an imported value of type float",
            id="imported-value",
        ),
        pytest.param(
            "from functools import partial\nfrom operator import mul\n"
            "from math import floor as PAY\n"
            "PAY = partial(mul, 2)\n\n\n"
            "def raise_rate(simulation):\n    simulation.rate = PAY(0.21)\n",
            r"reads PAY, a value of type functools\.partial",
            id="import-rebound-to-a-partial",
        ),
        pytest.param(
            "from math import *\n\n\n"
            "def raise_rate(simulation):\n    simulation.rate = floor(e)\n",
            r"reads e, an imported value of type float",
            id="star-imported-value",
        ),
        pytest.param(
            "COUNT = 0\n\n\n"
            "def raise_rate(simulation):\n    global COUNT\n    COUNT += 1\n"
            "    simulation.rate = 0.21\n",
            r"raise_rate assigns or deletes the module global COUNT",
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
        assert "literal constant or a default argument" in str(refused.value)
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
            match=r"reads PAY, an imported value of type functools\.partial",
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
            ReceiptError, match="reads EXTRA, a value of type float set on the module"
        ):
            _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)


ALLOWED_GLOBALS_SOURCE = """
import math
from functools import partial
from math import floor

RATE = 0.21
UNREAD = partial(floor)  # computed, but nothing the modifier runs reads it


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
    """Recursion terminates, a class inside the modifier reads its own body, a
    module attribute is bound by the code revision, and unread state is not
    the modifier's."""

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
                if f"reads {GLOBAL_KINDS[kind][1].split('(')[0]}," in str(refused.value)
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


def test_a_method_bound_to_a_module_name_is_not_a_module_function(tmp_path):
    """Only code compiled at module scope is compared with the module's code."""

    source = (
        "class Holder:\n    def apply(self, simulation):\n        simulation.rate = 0.21\n\n\n"
        "apply_holder = Holder.apply\n\n\n"
        "def raise_rate(simulation):\n    simulation.rate = 0.21\n"
    )
    name = "w4_receipt_r5_bound_method"
    try:
        module, _ = _import_source(tmp_path, name, source)
        assert _identity(module.raise_rate)
    finally:
        sys.modules.pop(name, None)
