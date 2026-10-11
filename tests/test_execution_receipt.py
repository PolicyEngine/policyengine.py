"""Execution receipt schema v1 (policyengine.provenance.receipt).

Invariants tested here:

- a receipt claims certification only when the certificate covers the
  installed model version, the simulated dataset bytes and the running
  wrapper version;
- the execution identity digest depends only on runtime and data, and the
  receipt digest additionally on reform, baseline, years and outputs, never
  on runtime context;
- digests are unchanged by member order and by null-versus-omitted fields;
- the Pydantic model and the published JSON Schema accept the same valid
  receipts and reject the same malformed ones (differential test).
"""

import copy
import hashlib
import json
from importlib import metadata
from pathlib import Path

import jsonschema
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
    uk_fiscal_year_convention,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = REPO_ROOT / "src" / "policyengine" / "data" / "bundle" / "manifest.json"
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
INSTALLED_WRAPPER = metadata.version("policyengine")


def _bundle_for(dataset_bytes: bytes, *, model_version=INSTALLED_UK) -> dict:
    """The committed bundle with its UK certificate pointed at these bytes."""

    bundle = json.loads(BUNDLE_PATH.read_text())
    record = bundle["data_releases"]["uk"]
    digest = hashlib.sha256(dataset_bytes).hexdigest()
    record["certified_data_artifact"]["sha256"] = digest
    record["datasets"][record["default_dataset"]]["sha256"] = digest
    record["certification"]["certified_for_model_version"] = model_version
    bundle["policyengine_version"] = INSTALLED_WRAPPER
    record["policyengine_version"] = INSTALLED_WRAPPER
    return bundle


@pytest.fixture
def dataset_file(tmp_path):
    path = tmp_path / "enhanced_frs_2024_25.h5"
    path.write_bytes(b"certified dataset bytes")
    return path


@pytest.fixture
def certified_receipt(dataset_file):
    return build_execution_receipt(
        country_id="uk",
        dataset_path=dataset_file,
        years=[2027, 2026, 2027],
        bundle=_bundle_for(dataset_file.read_bytes()),
    )


def test_certified_when_certificate_covers_installed_model_and_bytes(
    certified_receipt, dataset_file
):
    receipt = certified_receipt
    assert receipt.certification_status == "certified"
    assert receipt.model.version == INSTALLED_UK
    assert receipt.certificate.certified_for_model_version == INSTALLED_UK
    assert (
        receipt.data.dataset_sha256
        == hashlib.sha256(dataset_file.read_bytes()).hexdigest()
    )
    assert receipt.years == [2026, 2027]
    assert receipt.fiscal_year.convention == "uk_fiscal_year"
    record = _bundle_for(dataset_file.read_bytes())["data_releases"]["uk"]
    assert receipt.certificate.certificate_sha256 == certificate_sha256(record)


def test_installed_versions_not_manifest_versions(dataset_file):
    bundle = _bundle_for(dataset_file.read_bytes(), model_version="0.0.1")
    receipt = build_execution_receipt(
        country_id="uk", dataset_path=dataset_file, years=[2026], bundle=bundle
    )
    assert receipt.model.version == INSTALLED_UK
    assert receipt.certification_status == "uncertified"
    assert receipt.certificate is None


def test_different_dataset_bytes_are_uncertified(dataset_file, tmp_path):
    other = tmp_path / "other.h5"
    other.write_bytes(b"different bytes")
    receipt = build_execution_receipt(
        country_id="uk",
        dataset_path=other,
        years=[2026],
        bundle=_bundle_for(dataset_file.read_bytes()),
    )
    assert receipt.certification_status == "uncertified"
    assert receipt.data.dataset_sha256 == hashlib.sha256(b"different bytes").hexdigest()


@pytest.mark.parametrize("where", ["bundle", "record"])
def test_other_wrapper_version_is_uncertified(dataset_file, where):
    bundle = _bundle_for(dataset_file.read_bytes())
    target = bundle if where == "bundle" else bundle["data_releases"]["uk"]
    target["policyengine_version"] = "0.0.0"
    receipt = build_execution_receipt(
        country_id="uk", dataset_path=dataset_file, years=[2026], bundle=bundle
    )
    assert receipt.certification_status == "uncertified"


def test_unknown_dataset_is_refused(dataset_file):
    with pytest.raises(ReceiptError):
        build_execution_receipt(
            country_id="uk",
            dataset_path=dataset_file,
            years=[2026],
            dataset="not_a_bundle_dataset",
            bundle=_bundle_for(dataset_file.read_bytes()),
        )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("certificate", "certified_for_model_version"), "0.0.1"),
        (("certificate", "certified_dataset_sha256"), "0" * 64),
        (("certificate", "bundle_version"), "0.0.0"),
        (("certificate", "country_id"), "us"),
        (("fiscal_year", "convention"), "calendar_year"),
        (("certification_status",), "uncertified"),
        (("years",), [2027, 2026]),
        (("years",), [2026, 2026]),
    ],
)
def test_receipts_cannot_claim_what_did_not_run(certified_receipt, path, value):
    payload = certified_receipt.model_dump(mode="json")
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    if path == ("fiscal_year", "convention"):
        target["period_start"] = "01-01"
    with pytest.raises(ValidationError):
        ExecutionReceipt.model_validate(payload)


def test_json_round_trip_preserves_receipt_and_digests(certified_receipt):
    parsed = ExecutionReceipt.model_validate_json(certified_receipt.model_dump_json())
    assert parsed == certified_receipt
    assert parsed.receipt_sha256 == certified_receipt.receipt_sha256
    assert (
        parsed.execution_identity_sha256 == certified_receipt.execution_identity_sha256
    )
    canonical = ExecutionReceipt.model_validate_json(
        certified_receipt.to_canonical_json()
    )
    assert canonical == certified_receipt


def test_null_and_omitted_optional_fields_digest_identically(certified_receipt):
    with_nulls = certified_receipt.model_dump(mode="json")
    assert with_nulls["outputs_sha256"] is None
    without = certified_receipt.canonical_payload()
    assert "outputs_sha256" not in without
    assert (
        ExecutionReceipt.model_validate(with_nulls).receipt_sha256
        == ExecutionReceipt.model_validate(without).receipt_sha256
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


@settings(max_examples=100, deadline=None)
@given(
    payload=REFORM_PAYLOADS,
    years=st.lists(st.integers(2024, 2035), min_size=1, max_size=6),
    outputs=st.dictionaries(
        st.sampled_from(["budgetary_impact", "poverty_rate", "gini"]),
        st.floats(allow_nan=False, allow_infinity=False),
        max_size=3,
    ),
    ci_run_url=st.none() | st.just("https://github.com/o/r/actions/runs/1"),
)
def test_execution_identity_ignores_reform_years_outputs_and_runtime(
    tmp_path_factory, payload, years, outputs, ci_run_url
):
    directory = tmp_path_factory.mktemp("receipt")
    dataset = directory / "data.h5"
    dataset.write_bytes(b"same bytes")
    bundle = _bundle_for(b"same bytes")
    base = build_execution_receipt(
        country_id="uk", dataset_path=dataset, years=[2026], bundle=bundle
    )
    varied = build_execution_receipt(
        country_id="uk",
        dataset_path=dataset,
        years=years,
        reform=reform_identity(payload, "policyengine.reform_dict/v1"),
        outputs=outputs or None,
        bundle=bundle,
        ci_run_url=ci_run_url,
    )
    assert varied.execution_identity_sha256 == base.execution_identity_sha256
    same_content = varied.model_copy(update={"runtime": None})
    assert same_content.receipt_sha256 == varied.receipt_sha256
    if sorted(set(years)) != [2026] or outputs:
        assert varied.receipt_sha256 != base.receipt_sha256


@settings(max_examples=100, deadline=None)
@given(payload=REFORM_PAYLOADS, random=st.randoms())
def test_reform_digest_ignores_member_order_but_not_representation(payload, random):
    items = list(payload.items())
    random.shuffle(items)
    shuffled = {key: dict(reversed(list(value.items()))) for key, value in items}
    a = reform_identity(payload, "policyengine.reform_dict/v1")
    b = reform_identity(shuffled, "policyengine.reform_dict/v1")
    c = reform_identity(payload, "policyengine-uk.reform_dict/v1")
    assert a.reform_sha256 == b.reform_sha256
    assert a.reform_sha256 != c.reform_sha256
    assert a.reform_sha256 == content_sha256(
        {"representation": "policyengine.reform_dict/v1", "payload": payload}
    )


def test_empty_reform_is_current_law_and_strings_are_refused():
    assert reform_identity(None).kind == "current_law"
    assert reform_identity({}).kind == "current_law"
    with pytest.raises(ReceiptError):
        reform_identity({"a": {"2027": 1}})
    with pytest.raises(ReceiptError):
        reform_identity("gov.x", "policyengine.reform_dict/v1")
    with pytest.raises(ValidationError):
        ReformIdentity(kind="current_law", reform_sha256="0" * 64)
    with pytest.raises(ValidationError):
        ReformIdentity(kind="reform", representation="policyengine.reform_dict/v1")


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


def test_verified_package_hash_is_recorded_with_its_evidence(dataset_file):
    receipt = build_execution_receipt(
        country_id="uk",
        dataset_path=dataset_file,
        years=[2026],
        bundle=_bundle_for(dataset_file.read_bytes()),
        package_hashes={"policyengine_uk": ("a" * 64, "installed_record_verified")},
    )
    assert receipt.model.wheel_sha256 == "a" * 64
    assert receipt.model.wheel_sha256_evidence == "installed_record_verified"
    assert receipt.core.wheel_sha256_evidence in (None, "installer_archive_hash")


def test_installer_archive_hash_is_read_from_direct_url(monkeypatch):
    class FakeDistribution:
        version = INSTALLED_UK

        def read_text(self, name):
            assert name == "direct_url.json"
            return json.dumps(
                {
                    "url": "file:///wheels/policyengine_uk.whl",
                    "archive_info": {"hashes": {"sha256": "b" * 64}},
                }
            )

    monkeypatch.setattr(
        receipt_module.metadata, "distribution", lambda name: FakeDistribution()
    )
    identity = installed_package_identity("policyengine-uk")
    assert identity.wheel_sha256 == "b" * 64
    assert identity.wheel_sha256_evidence == "installer_archive_hash"


def test_hash_without_evidence_is_refused():
    with pytest.raises(ValidationError):
        receipt_module.PackageIdentity(name="x", version="1", wheel_sha256="c" * 64)


# --- The published JSON Schema agrees with the Pydantic model ------------


@pytest.fixture(scope="module")
def schema_validator():
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def test_published_schema_is_current():
    assert json.loads(SCHEMA_PATH.read_text()) == ExecutionReceipt.json_schema()


@settings(max_examples=60, deadline=None)
@given(
    years=st.lists(st.integers(2020, 2040), min_size=1, max_size=5),
    payload=st.none() | REFORM_PAYLOADS,
    wheel=st.none() | SHA,
    certified=st.booleans(),
)
def test_schema_accepts_every_valid_receipt(
    tmp_path_factory, schema_validator, years, payload, wheel, certified
):
    directory = tmp_path_factory.mktemp("schema")
    dataset = directory / "data.h5"
    dataset.write_bytes(b"bytes")
    bundle = _bundle_for(b"bytes" if certified else b"other")
    receipt = build_execution_receipt(
        country_id="uk",
        dataset_path=dataset,
        years=years,
        reform=reform_identity(payload, "policyengine.reform_dict/v1"),
        bundle=bundle,
        package_hashes=(
            {"policyengine-core": (wheel, "installed_record_verified")}
            if wheel
            else None
        ),
    )
    schema_validator.validate(json.loads(receipt.model_dump_json()))
    schema_validator.validate(json.loads(receipt.to_canonical_json()))


MUTATIONS = [
    ("extra top-level member", lambda r: r.update(unexpected=1)),
    ("bad schema version", lambda r: r.update(schema_version=2)),
    ("bad receipt type", lambda r: r.update(receipt_type="other")),
    ("bad country", lambda r: r.update(country_id="fr")),
    ("missing data", lambda r: r.pop("data")),
    ("bad dataset digest", lambda r: r["data"].update(dataset_sha256="XYZ")),
    ("short dataset digest", lambda r: r["data"].update(dataset_sha256="a" * 63)),
    ("extra data member", lambda r: r["data"].update(rows=10)),
    ("empty years", lambda r: r.update(years=[])),
    ("bad period start", lambda r: r["fiscal_year"].update(period_start="April")),
    ("bad wheel digest", lambda r: r["model"].update(wheel_sha256="1234")),
    ("bad git sha", lambda r: r["wrapper"].update(git_sha="abc")),
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
    schema = schema_validator.schema
    assert (
        "certificate.certified_for_model_version equals model.version."
        in (schema["x-policyengine-rules"])
    )
    assert "RFC 8785" in schema["x-policyengine-digests"]["canonicalization"]


def test_execution_identity_digest_preimage_is_documented(certified_receipt):
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
    assert certified_receipt.execution_identity_sha256 == canonical_sha256(identity)


# --- policyengine-uk Scenario and managed microsimulations ---------------


class _Scenario:
    def __init__(self, parameter_changes=None, simulation_modifier=None, early=False):
        self.parameter_changes = parameter_changes
        self.simulation_modifier = simulation_modifier
        self.applied_before_data_load = early


def _raise_basic_rate(simulation):
    simulation.tax_benefit_system.parameters.gov.hmrc.income_tax.rates.uk[
        0
    ].rate.update(period="year:2027:10", value=0.21)


REVISION = {
    "repository": "PolicyEngine/uk-autumn-budget-dashboard-2026",
    "git_sha": "a" * 40,
}


def test_parameter_only_scenario_is_bound_by_content():
    changes = {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027-04-06": 0.21}}
    identity = scenario_reform_identity(_Scenario(changes))
    assert identity.binding == "content"
    assert identity.representation == "policyengine-uk.scenario/v1"
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
        scenario_reform_identity(_Scenario(changes, early=True)).reform_sha256
        != identity.reform_sha256
    )


def test_empty_scenario_is_current_law():
    assert scenario_reform_identity(_Scenario()).kind == "current_law"


def test_modifier_scenario_needs_a_code_revision_and_says_so():
    with pytest.raises(ReceiptError):
        scenario_reform_identity(_Scenario(simulation_modifier=_raise_basic_rate))
    identity = scenario_reform_identity(
        _Scenario(simulation_modifier=_raise_basic_rate), code_revision=REVISION
    )
    assert identity.binding == "code_revision"
    other_revision = scenario_reform_identity(
        _Scenario(simulation_modifier=_raise_basic_rate),
        code_revision={**REVISION, "git_sha": "b" * 40},
    )
    assert other_revision.reform_sha256 != identity.reform_sha256


def test_modifier_without_source_is_refused():
    with pytest.raises(ReceiptError):
        scenario_reform_identity(
            _Scenario(simulation_modifier=print), code_revision=REVISION
        )


def test_current_law_cannot_claim_code_binding():
    with pytest.raises(ValidationError):
        ReformIdentity(kind="current_law", binding="code_revision")


def test_microsimulation_receipt_reads_the_loaded_dataset(dataset_file, monkeypatch):
    class Microsimulation:
        policyengine_bundle = {
            "country_id": "uk",
            "runtime_dataset": "enhanced_frs_2024_25",
            "runtime_dataset_source": str(dataset_file),
        }

    bundle = _bundle_for(dataset_file.read_bytes())
    receipt = build_execution_receipt_for_microsimulation(
        Microsimulation(), years=[2026], bundle=bundle
    )
    assert receipt.certification_status == "certified"
    assert receipt.data.dataset == "enhanced_frs_2024_25"
    assert (
        receipt.data.build_model_version
        == (bundle["data_releases"]["uk"]["certification"]["built_with_model_version"])
    )


def test_microsimulation_without_bundle_fields_is_refused():
    with pytest.raises(ReceiptError):
        build_execution_receipt_for_microsimulation(object(), years=[2026])


def test_packaged_bundle_receipt_records_the_tro_fingerprint(tmp_path):
    """With the packaged bundle, the certificate names the bundle TRO."""

    from policyengine.provenance.trace import extract_bundle_tro_reference

    bundle = json.loads(BUNDLE_PATH.read_text())
    record = bundle["data_releases"]["uk"]
    if (
        record["certification"]["certified_for_model_version"] != INSTALLED_UK
        or bundle["policyengine_version"] != INSTALLED_WRAPPER
    ):
        pytest.fail("The installed packages do not match the committed bundle pins.")
    fake = tmp_path / "data.h5"
    fake.write_bytes(b"not the certified bytes")
    uncertified = build_execution_receipt(
        country_id="uk", dataset_path=fake, years=[2026]
    )
    assert uncertified.certification_status == "uncertified"
    tro = json.loads(BUNDLE_PATH.with_name("uk.trace.tro.jsonld").read_text())
    expected = extract_bundle_tro_reference(tro)["fingerprint"]
    assert (
        receipt_module._packaged_tro_fingerprint(
            BUNDLE_PATH.with_name("uk.trace.tro.jsonld")
        )
        == expected
    )
