# Execution receipts

An execution receipt travels with a published number, such as a dashboard row, a briefing figure or an API response. It names everything that determined that number, so a reader can tell exactly which model, data and certificate produced it, and two numbers can be compared knowing whether they came from the same run.

Schema v1 covers UK results and is defined by `policyengine.provenance.receipt.ExecutionReceipt`. The JSON Schema ships in the wheel at `policyengine/data/schemas/execution_receipt.v1.schema.json`, and the same file is in the repository at [`src/policyengine/data/schemas/execution_receipt.v1.schema.json`](https://github.com/PolicyEngine/policyengine.py/blob/main/src/policyengine/data/schemas/execution_receipt.v1.schema.json).

## What a receipt records

| Field | Contents |
|---|---|
| `wrapper`, `model`, `core` | The `policyengine`, `policyengine-uk` and `policyengine-core` versions that actually ran, read from the installed distributions rather than from the bundle manifest. `wheel_sha256` appears only when the receipt builder verified it. One way is `wheel_paths=` (evidence `installed_record_verified`): the installed files, and any bytecode cache the interpreter would load instead of a source file, are checked against that wheel's RECORD. The other is the installer's recorded archive hash (`installer_archive_hash`), taken only when the install came from a `.whl` URL; a source archive's hash is never recorded as a wheel hash. |
| `data` | The data release and build, and the model version the data was built with (`build_model_version`, distinct from `model.version`). Also the dataset's logical name, URI, revision and the SHA-256 of the bytes that were simulated. The dataset is resolved exactly as `materialize_dataset` resolves it (overlays, per-dataset repository, package and revision, and the release manifest revision when an artifact has none of its own), and the bytes must be the ones the bundle pins for it: a receipt never gives an artifact's name to other bytes. |
| `certification_status`, `certificate` | `certified` only when the bundle certifies all of: the installed model and core versions, that dataset name and those bytes, and the running `policyengine` version. Otherwise the receipt says `uncertified` and carries no certificate. `certificate_source` records whether the builder read the certificate from the installed bundle (`packaged`) or from a manifest the caller passed (`caller_supplied`). It is the producer's statement, not evidence: trust a certificate only after `verify_certificate` (below). With the packaged bundle, the composition fingerprint of its TRACE TRO is recorded as well. |
| `reform`, `baseline` | Both are required. Each is `current_law` or a digest of the reform bound to its representation (see below). |
| `fiscal_year` | What a year label means: year 2027 is the fiscal year from 6 April 2027 to 5 April 2028, shown as `2027-28`. v1 allows only this convention. |
| `years` | The reported years, sorted and unique. |
| `supported_years` | The years the installed model projects the dataset to, from the dataset's own year (policyengine-uk's `extend_single_year_dataset`, without running a formula; the same rule as the qualification `supported_years` gate). A reported year outside them is unsupported: policyengine-core fills it by carrying or uprating the latest inputs, so its results are not evidence. `unsupported_years` lists them. The certified 1.58.0 dataset projects to 2024–2030, so a 2031-32 figure on it is unsupported. |
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

For a country `Microsimulation` built with `managed_microsimulation()`, call `build_execution_receipt_for_microsimulation(sim, years=..., reform=..., baseline=...)`. It reads the dataset that was loaded from `sim.policyengine_bundle`. The file must still hash to the SHA-256 verified when it was loaded, and the receipt must name the dataset, URI, revision and package recorded then; otherwise it is refused, because it would describe bytes that did not run. A simulation loaded from an unmanaged file or URI recorded no load-time hash, so it cannot be receipted. The microsimulation does not record its reform, so pass the reform you built it with.

There are two ways to bind a policyengine-uk `Scenario`:
- A scenario built from `parameter_changes` is bound by content with `scenario_reform_identity(scenario)`.
- `Scenario.from_reform(d)` wraps `d` in a closure that cannot be bound by its code, so bind `d` itself with `reform_identity(d, "policyengine-uk.reform_dict/v1")`.

A scenario with a module-level `simulation_modifier` needs `code_revision={"repository": ..., "git_sha": <full commit sha>}`. The identity then says `binding: "code_revision"` and binds:
- the function's module and qualified name;
- the SHA-256 of its source and of its module's source file;
- the default arguments of every function in that module, encoded with their types and floats by their bits, so `1` and `1.0`, `0.0` and `-0.0`, a tuple and a list, or `None` and a missing key never share a digest (defaults with no exact encoding, such as objects, are refused);
- that revision.

None of these depends on where the code is checked out or which Python version runs it, so CI, a laptop and the server compute the same digest for the same code.

A digest must only name code that ran, so before binding, the module's source as read now is compiled and checked against what was imported, ignoring file names and line numbers:
- the module's source is compiled as a whole (so each function compiles in its module's context, imports included), and the modifier and every other function defined at module scope in that file (in blocks such as `if` too, or wrapped by a decorator that sets `__wrapped__`) must use the module's own globals and match that code, nested code and constants included, with constants compared by exact type and float bits;
- a name the source binds only with `def` must still be that function (or a wrapper of it), not another module's function or any other object;
- literal default arguments in the source, such as `rate=0.21`, must still be the function's defaults, with the same type;
- every module-scope name all of whose bindings assign a literal, such as `RATE = 0.21`, at top level or in a block, must still hold one of those values, with the same type (scopes are followed: a comprehension's own loop variable is not a binding but a `:=` in it is, a lambda's body is its own scope, and a function's defaults and decorators bind in the module);
- a function name defined more than once with different code, as in `if FLAG: def helper(): ...` / `else: def helper(): ...`, is refused, because which definition the source selects now cannot be checked.

A measures file edited after import, or a literal constant or default reassigned while the process runs, is therefore refused rather than misdescribed. The check does not cover other module state, such as objects built at import, imported modules, class bodies and methods, or data the code reads at run time: `code_revision` names the code, not the process.

Some modifiers are refused outright because their behaviour depends on values the digest cannot bind: closures, lambdas, nested functions, methods, `functools.partial` and builtins. Anything that is not a `Scenario` is refused too, rather than read as current law.

To check a certificate, call `verify_certificate(receipt, bundle)` with the policyengine manifest for `certificate.bundle_version`. It rebuilds the certificate from that manifest's certification record, the same way the builder does. Then it compares every identity member: the record digest, the basis, the certified model, core and dataset digest, the certifier and the bundle version. It also checks that the receipt's whole `data` identity is the certified dataset with the certified bytes. An empty list means the bundle certifies exactly what the receipt claims, and through the receipt's own rules that pins `model.version`, `core.version` and `wrapper.version` too. `certificate_source`, `qualification_receipt_sha256`, `tro_composition_fingerprint` and wheel hashes are not determined by the bundle, so it does not check them.

Pass the release artifact that was loaded as `dataset_path`. A derived per-year file such as `enhanced_frs_2024_25_year_2026.h5` has different bytes from the artifact the bundle pins, so a receipt for it is refused.

## Digests

Every receipt digest is the lowercase hexadecimal SHA-256 of the [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) canonical JSON of a value, computed in two steps:
1. **Strict JSON conversion.** Only JSON-native values are accepted: strings, booleans, null, integers within ±(2^53−1), finite doubles, arrays and objects with string keys. NumPy boolean, integer and floating scalars are converted to their values, integer keys to their decimal strings, and `datetime.date` to `YYYY-MM-DD`. Anything else is refused rather than silently stringified, including sets, `Decimal`, arrays (0-d and masked ones too, so `np.ma.masked` never becomes `0.0`), NaN and colliding keys.
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

Reform digests are the exception: a reform payload is digested with its nulls kept, because there a null can mean something. `Scenario.from_reform({"p": {"2027": None}})` removes a value that `{"p": {}}` keeps, so the two must not share a digest.

The pre-promotion replay interface with policyengine-scorecard follows a different rule, set by its own schemas: plain RFC 8785 over the document as sent, nulls included. `policyengine.provenance.canonical.canonical_sha256` computes that.

| Digest | Value hashed |
|---|---|
| `execution_identity_sha256` | `schema_version`, `country_id`, `wrapper`, `model`, `core`, `data`, `certification_status`, and the certificate's content: bundle version, record digest, basis, certified versions, dataset digest and certifier. Results with the same execution identity ran on the same runtime and data under the same certificate, however the receipt was built. |
| `receipt_sha256` | The whole receipt except `runtime` and the reform and baseline `name` labels. Renaming a measure therefore does not change it. |
| `certificate.certificate_sha256` | The bundle manifest's `data_releases.uk` record. |
| `reform.reform_sha256` | `{"representation": ..., "payload": ...}`, with the payload exactly as given, nulls kept (strict JSON conversion, then RFC 8785, with no null removal). |
| `outputs_sha256` | The output payload. |

Reform digests are never normalized across representations. The same keys can legitimately mean different things in different representations: for example, a bare year in a policyengine-uk country dictionary changes that one year only. So each digest is tied to the representation that was submitted. The v1 representations are `policyengine.parameter_values/v1`, `policyengine.reform_dict/v1`, `policyengine-uk.reform_dict/v1`, `policyengine-uk.scenario/v1` and `policyengine-sim-api.policy/v1`.

## Rules JSON Schema cannot express

Consumers that validate with the JSON Schema rather than the Python model must also check the rules listed under `x-policyengine-rules` in the schema file:

- `years` is sorted with no duplicates, and each year is written as an integer (`2027`, not `2027.0`);
- `supported_years` is sorted with no duplicates, and a year in `years` but not in `supported_years` must be shown as provisional or not at all;
- a certificate is present exactly when the receipt is certified, and it names the receipt's country, model and core versions, dataset digest and `policyengine` version;
- a `current_law` reform has no digest, while any other reform has both a representation and a digest;
- a wheel digest always comes with its evidence;
- a certificate is trusted only after it, and the receipt's `data`, have been checked against the published manifest it names (`verify_certificate`).

The schema itself fixes the package names (`policyengine`, `policyengine-uk`, `policyengine-core`) and the UK fiscal-year convention, which starts on 6 April.

## Compatibility

Adding an optional field is a compatible v1 change. Optional fields are omitted from digests when absent, so existing digests stay valid. Removing or redefining a field, or changing what a digest covers, requires schema v2.
