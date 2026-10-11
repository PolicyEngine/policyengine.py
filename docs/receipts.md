# Execution receipts

An execution receipt travels with a published number, such as a dashboard row, a briefing figure or an API response. It names everything that determined that number, so a reader can tell exactly which model, data and certificate produced it, and two numbers can be compared knowing whether they came from the same run.

Schema v1 covers UK results and is defined by `policyengine.provenance.receipt.ExecutionReceipt`. The JSON Schema ships in the wheel at `policyengine/data/schemas/execution_receipt.v1.schema.json`, and the same file is in the repository at [`src/policyengine/data/schemas/execution_receipt.v1.schema.json`](https://github.com/PolicyEngine/policyengine.py/blob/main/src/policyengine/data/schemas/execution_receipt.v1.schema.json).

## What a receipt records

| Field | Contents |
|---|---|
| `wrapper`, `model`, `core` | The `policyengine`, `policyengine-uk` and `policyengine-core` versions that actually ran, read from the installed distributions rather than from the bundle manifest. `wheel_sha256` appears only when the receipt builder verified it: either by checking the installed files against a wheel's RECORD (`wheel_paths=`, evidence `installed_record_verified`), or from the installer's recorded archive hash (`installer_archive_hash`). |
| `data` | The data release and build, and the model version the data was built with (`build_model_version`, distinct from `model.version`). Also the dataset's logical name, URI, revision and the SHA-256 of the bytes that were simulated. |
| `certification_status`, `certificate` | `certified` only when the bundle certifies all of: the installed model and core versions, that dataset name and those bytes, and the running `policyengine` version. Otherwise the receipt says `uncertified` and carries no certificate. `certificate_source` says whether the certificate came from the installed bundle (`packaged`) or from a manifest the caller passed (`caller_supplied`). With the packaged bundle, the composition fingerprint of its TRACE TRO is recorded as well. |
| `reform`, `baseline` | Both are required. Each is `current_law` or a digest of the reform bound to its representation (see below). |
| `fiscal_year` | What a year label means: year 2027 is the fiscal year from 6 April 2027 to 5 April 2028, shown as `2027-28`. |
| `years` | The reported years, sorted and unique. |
| `outputs_sha256` | Optional digest of the output payload the receipt binds. |
| `runtime` | Python version, platform and CI run URL. It is for diagnosis and is part of no digest. |

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
    baseline=reform_identity(None),
    outputs={"budgetary_impact": {"2027": 6.1e9, "2028": 6.4e9}},
)
print(receipt.certification_status, receipt.execution_identity_sha256)
receipt_json = receipt.to_canonical_json()
```

For a country `Microsimulation` built with `managed_microsimulation()`, call `build_execution_receipt_for_microsimulation(sim, years=..., reform=..., baseline=...)`. It reads the dataset that was loaded from `sim.policyengine_bundle` and hashes those bytes. The microsimulation does not record its reform, so pass the reform you built it with.

There are two ways to bind a policyengine-uk `Scenario`:
- A scenario built from `parameter_changes` is bound by content with `scenario_reform_identity(scenario)`.
- `Scenario.from_reform(d)` wraps `d` in a closure that cannot be bound by its code, so bind `d` itself with `reform_identity(d, "policyengine-uk.reform_dict/v1")`.

A scenario with a module-level `simulation_modifier` needs `code_revision={"repository": ..., "git_sha": ...}`. The modifier is then bound by its source, its loaded bytecode and that revision, and the identity says `binding: "code_revision"`. Closures, lambdas, `functools.partial`, bound methods and builtins are refused: their behaviour depends on values the digest cannot bind.

To check a certificate, call `verify_certificate(receipt, bundle)` with the policyengine manifest for `certificate.bundle_version`. It confirms that `certificate_sha256` matches that manifest's certification record.

Pass the release artifact that was loaded as `dataset_path`. A derived per-year file such as `enhanced_frs_2024_25_year_2026.h5` has different bytes, so a receipt built from it is `uncertified`.

## Digests

Every receipt digest is the lowercase hexadecimal SHA-256 of the [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) canonical JSON of a value, computed in two steps:
1. **Strict JSON conversion.** Only JSON-native values are accepted: strings, booleans, null, integers within ±(2^53−1), finite doubles, arrays and objects with string keys. Numpy scalars are converted to their values, integer keys to their decimal strings, and `datetime.date` to `YYYY-MM-DD`. Anything else is refused rather than silently stringified, including sets, `Decimal`, arrays, NaN and colliding keys.
2. **Null removal.** Object members whose value is `null` are removed. Array elements are kept.

RFC 8785 fixes member order, string escaping and number formatting, so Python and JavaScript produce the same bytes. Removing nulls means a producer that writes `"field": null` and one that omits the field compute the same digest. In Python use `policyengine.provenance.receipt.content_sha256`. In JavaScript:

```javascript
import canonicalize from "canonicalize";
import { createHash } from "node:crypto";

const dropNulls = (v) =>
  Array.isArray(v) ? v.map(dropNulls)
  : v && typeof v === "object"
    ? Object.fromEntries(Object.entries(v).filter(([, x]) => x !== null).map(([k, x]) => [k, dropNulls(x)]))
    : v;
const digest = (value) => createHash("sha256").update(canonicalize(dropNulls(value)), "utf8").digest("hex");
```

The pre-promotion replay interface with policyengine-scorecard follows a different rule, set by its own schemas: plain RFC 8785 over the document as sent, nulls included. `policyengine.provenance.canonical.canonical_sha256` computes that.

| Digest | Value hashed |
|---|---|
| `execution_identity_sha256` | `schema_version`, `country_id`, `wrapper`, `model`, `core`, `data`, `certification_status`, and the certificate's content: bundle version, record digest, basis, certified versions, dataset digest and certifier. Results with the same execution identity ran on the same runtime and data under the same certificate, however the receipt was built. |
| `receipt_sha256` | The whole receipt except `runtime` and the reform and baseline `name` labels. Renaming a measure therefore does not change it. |
| `certificate.certificate_sha256` | The bundle manifest's `data_releases.uk` record. |
| `reform.reform_sha256` | `{"representation": ..., "payload": ...}`, with the payload exactly as given. |
| `outputs_sha256` | The output payload. |

Reform digests are never normalized across representations. The same keys can legitimately mean different things in different representations: for example, a bare year in a policyengine-uk country dictionary changes that one year only. So each digest is tied to the representation that was submitted. The v1 representations are `policyengine.parameter_values/v1`, `policyengine.reform_dict/v1`, `policyengine-uk.reform_dict/v1`, `policyengine-uk.scenario/v1` and `policyengine-sim-api.policy/v1`.

## Rules JSON Schema cannot express

Consumers that validate with the JSON Schema rather than the Python model must also check the rules listed under `x-policyengine-rules` in the schema file:

- `years` is sorted with no duplicates;
- UK receipts report UK fiscal years, which start on 6 April;
- the three package names are `policyengine`, `policyengine-uk` and `policyengine-core`;
- a certificate is present exactly when the receipt is certified, and it names the receipt's country, model and core versions, dataset digest and `policyengine` version;
- a `current_law` reform has no digest, while any other reform has both a representation and a digest;
- a wheel digest always comes with its evidence.

## Compatibility

Adding an optional field is a compatible v1 change. Optional fields are omitted from digests when absent, so existing digests stay valid. Removing or redefining a field, or changing what a digest covers, requires schema v2.
