# Execution receipts

An execution receipt travels with a published number, such as a dashboard row, a briefing figure or an API response. It names everything that determined that number, so a reader can tell exactly which model, data and certificate produced it, and two numbers can be compared knowing whether they came from the same run.

Schema v1 is defined by `policyengine.provenance.receipt.ExecutionReceipt`. The JSON Schema ships in the wheel at `policyengine/data/schemas/execution_receipt.v1.schema.json`, and the same file is in the repository at [`src/policyengine/data/schemas/execution_receipt.v1.schema.json`](https://github.com/PolicyEngine/policyengine.py/blob/main/src/policyengine/data/schemas/execution_receipt.v1.schema.json).

## What a receipt records

| Field | Contents |
|---|---|
| `wrapper`, `model`, `core` | The `policyengine`, country model and `policyengine-core` versions that actually ran, read from the installed distributions rather than from the bundle manifest. `wheel_sha256` appears only when it was verified, and `wheel_sha256_evidence` says how. |
| `data` | The data release and build, the model version the data was built with (`build_model_version`, distinct from `model.version`), plus the dataset's logical name, URI, revision and the SHA-256 of the bytes that were simulated. |
| `certification_status`, `certificate` | `certified` only when the bundle's certificate covers the installed model version, those dataset bytes and the running `policyengine` version. Otherwise the receipt says `uncertified` and carries no certificate. The certificate carries the digest of the bundle's certification record and, when the packaged bundle was used, the composition fingerprint of its TRACE TRO. |
| `reform`, `baseline` | `current_law`, or a digest of the reform bound to its representation (see below). |
| `fiscal_year` | What a year label means. In UK receipts, year 2027 is the fiscal year from 6 April 2027 to 5 April 2028, shown as `2027-28`. |
| `years` | The reported years, sorted and unique. |
| `outputs_sha256` | Optional digest of the output payload the receipt binds. |
| `runtime` | Python version, platform and CI run URL. It is recorded for diagnosis and excluded from both digests. |

## Building one

```python
from policyengine.provenance import materialize_dataset
from policyengine.provenance.receipt import build_execution_receipt, reform_identity

source = materialize_dataset("uk")  # the certified release artifact, hash-verified
reform = {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027-04-06": 0.21}}

receipt = build_execution_receipt(
    country_id="uk",
    dataset_path=source.path,
    years=[2027, 2028],
    reform=reform_identity(
        reform, "policyengine.reform_dict/v1", name="basic rate 21p"
    ),
    outputs={"budgetary_impact": {"2027": 6.1e9, "2028": 6.4e9}},
)
print(receipt.certification_status, receipt.execution_identity_sha256)
receipt_json = receipt.to_canonical_json()
```

For a country `Microsimulation` built with `managed_microsimulation()`, `build_execution_receipt_for_microsimulation(sim, years=..., reform=...)` reads the dataset that was loaded from `sim.policyengine_bundle` and hashes it. A policyengine-uk `Scenario` is bound with `scenario_reform_identity(scenario)`. If the scenario has a `simulation_modifier`, pass `code_revision={"repository": ..., "git_sha": ...}`. The modifier is then bound by its source digest and that revision, and the identity says `binding: "code_revision"`. Values captured in its closure are not bound, so prefer `parameter_changes` wherever a reform can be expressed that way.

Pass the release artifact that was loaded as `dataset_path`. A derived per-year file such as `enhanced_frs_2024_25_year_2026.h5` has different bytes, so a receipt built from it is `uncertified`.

## Digests

Every digest is the lowercase hexadecimal SHA-256 of the [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) canonical JSON of a value, after removing object members whose value is `null`. RFC 8785 fixes member order, string escaping and number formatting, so Python and JavaScript produce the same bytes. Removing nulls means a producer that writes `"field": null` and one that omits the field compute the same digest. The `rfc8785` package (Python) and `canonicalize` (JavaScript) implement the scheme, and so does `policyengine.provenance.canonical`.

| Digest | Value hashed |
|---|---|
| `execution_identity_sha256` | `schema_version`, `country_id`, `wrapper`, `model`, `core`, `data`, `certification_status` and `certificate`. Results with the same execution identity ran on the same runtime, data and certificate. |
| `receipt_sha256` | The whole receipt except `runtime`. |
| `certificate.certificate_sha256` | The bundle manifest's `data_releases.<country>` record. |
| `reform.reform_sha256` | `{"representation": ..., "payload": ...}`, with the payload exactly as given. |
| `outputs_sha256` | The output payload. |

Reform digests are never normalized across representations. The same keys can legitimately mean different things in different representations: for example, a bare year in a policyengine-uk country dictionary changes that one year only. So each digest is tied to the representation that was submitted. The v1 representations are `policyengine.parameter_values/v1`, `policyengine.reform_dict/v1`, `policyengine-uk.reform_dict/v1`, `policyengine-uk.scenario/v1` and `policyengine-sim-api.policy/v1`.

## Rules JSON Schema cannot express

Consumers that validate with the JSON Schema rather than the Python model must also check the rules listed under `x-policyengine-rules` in the schema file:

- `years` is sorted with no duplicates;
- UK receipts report UK fiscal years;
- a certificate is present exactly when the receipt is certified, and it names the receipt's country, model version, dataset digest and `policyengine` version;
- a `current_law` reform has no digest, while any other reform has both a representation and a digest;
- a wheel digest always comes with its evidence.

## Compatibility

Adding an optional field is a compatible v1 change. Optional fields are omitted from digests when absent, so existing digests stay valid. Removing or redefining a field, or changing what a digest covers, requires schema v2.
