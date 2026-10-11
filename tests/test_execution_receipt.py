"""Execution receipt schema v1 (policyengine.provenance.receipt).

Invariants tested here:

- a receipt claims certification only when the certificate covers the
  installed model and core versions, the simulated dataset bytes and name,
  and the running wrapper version;
- a wheel hash is recorded only when the builder verified it;
- the execution identity depends only on runtime, data and certificate
  content, never on how the builder was called; the receipt digest adds
  reform, baseline, years and outputs, never runtime context or labels;
- digests are over strict JSON: nothing is silently stringified, member
  order and null-versus-omitted do not matter, and colliding keys are refused;
- a reform digest binds content, or a module-level modifier's code plus a
  revision; closures, lambdas, partials and methods are refused;
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
import json
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
        "dataset bytes",
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
    elif change == "dataset bytes":
        path = tmp_path / "other.h5"
        path.write_bytes(b"different bytes")
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


def test_overlay_datasets_receive_uncertified_receipts(dataset_file):
    bundle = _bundle_for(dataset_file.read_bytes())
    overlay_name = next(iter(bundle["dataset_overlays"]["uk"]))
    receipt = _build(dataset_file, bundle, dataset=overlay_name)
    assert receipt.certification_status == "uncertified"
    assert receipt.data.dataset == overlay_name
    assert receipt.data.build_id is None


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
    assert verify_certificate(_build(dataset_file, _bundle_for(b"x")), bundle) == [
        "the receipt is uncertified"
    ]


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


def test_installer_archive_hash_is_read_from_direct_url():
    class Distribution:
        version = INSTALLED_UK

        def read_text(self, name):
            assert name == "direct_url.json"
            return json.dumps(
                {
                    "url": "file:///w.whl",
                    "archive_info": {"hashes": {"sha256": "b" * 64}},
                }
            )

    fake = SimpleNamespace(
        version=lambda name: INSTALLED_UK, distribution=lambda name: Distribution()
    )
    identity = installed_package_identity("policyengine-uk", metadata_module=fake)
    assert (identity.wheel_sha256, identity.wheel_sha256_evidence) == (
        "b" * 64,
        "installer_archive_hash",
    )


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


def test_parameter_scenarios_are_bound_by_content():
    changes = {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027-04-06": 0.21}}
    identity = scenario_reform_identity(_scenario(changes))
    assert identity.binding == "content"
    assert identity.reform_sha256 == content_sha256(
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


def test_microsimulation_receipt_needs_its_reform_and_reads_the_loaded_dataset(
    dataset_file,
):
    simulation = SimpleNamespace(
        policyengine_bundle={
            "country_id": "uk",
            "runtime_dataset": "enhanced_frs_2024_25",
            "runtime_dataset_source": str(dataset_file),
        }
    )
    bundle = _bundle_for(dataset_file.read_bytes())
    with pytest.raises(TypeError):
        build_execution_receipt_for_microsimulation(
            simulation, years=[2026], bundle=bundle
        )
    receipt = build_execution_receipt_for_microsimulation(
        simulation,
        years=[2026],
        reform=CURRENT_LAW,
        baseline=CURRENT_LAW,
        bundle=bundle,
    )
    assert receipt.certification_status == "certified"
    assert (
        receipt.data.build_model_version
        == bundle["data_releases"]["uk"]["certification"]["built_with_model_version"]
    )
    with pytest.raises(ReceiptError):
        build_execution_receipt_for_microsimulation(
            object(), years=[2026], reform=CURRENT_LAW, baseline=CURRENT_LAW
        )


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
        _bundle_for(b"bytes" if certified else b"other"),
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
    assert any("period_start is 04-06" in rule for rule in rules)
    assert any("model.name is policyengine-uk" in rule for rule in rules)
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
