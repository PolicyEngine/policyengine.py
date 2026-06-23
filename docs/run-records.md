# Run records

A run record makes a simulation result permanently citable. It is a
self-contained directory binding everything that determined the result —
the certified runtime bundle, the reform, the input dataset, and the
outputs — by sha256, under a per-run TRACE Transparent Research Object
(TRO). The run TRO's composition fingerprint is the citable identifier:
any edit to any payload changes it, and the same run always reproduces
it.

Run records exist for the case where re-running is not the answer:
results produced on hosted infrastructure on a researcher's behalf, or
results that must remain checkable years after the versions that
produced them stopped being current. A published paper cites the
fingerprint; a referee runs one command to verify the record.

## Writing a record

```python
import policyengine as pe
from policyengine.core import Simulation

datasets = pe.us.ensure_datasets(years=[2026], data_folder="./data")
simulation = Simulation(
    dataset=datasets["populace_us_2024_2026"],
    tax_benefit_model_version=pe.us.model,
    policy={"gov.irs.credits.ctc.amount.base[0].amount": 3_000},
)
simulation.ensure()

record = simulation.write_run_record(
    "./record",
    bundle_tro_url=(
        "https://raw.githubusercontent.com/PolicyEngine/policyengine.py/"
        "main/src/policyengine/data/bundle/us.trace.tro.jsonld"
    ),
)
print(record.composition_fingerprint)  # the citable id
```

The directory contains:

| File | Contents |
|------|----------|
| `run.trace.tro.jsonld` | The per-run TRO binding every other file by sha256 |
| `bundle.trace.tro.jsonld` | The certified bundle TRO (model + data pins) |
| `reform.json` | The reform as parameter values with effective dates |
| `input.json` | Input dataset hash, dynamics, scoping, extra variables |
| `results.json` | Output dataset hash and per-entity table summaries |

All payload files are written with the same canonical JSON used for
hashing, so the record verifies offline exactly as written.

`bundle_tro_url` is optional but recommended: it is recorded on the run
TRO as `pe:bundleTroUrl`, letting a verifier cross-check the record's
local bundle TRO against independently fetched bytes instead of trusting
the record's copy.

## What a record refuses to certify

A reform carrying a `simulation_modifier` callable raises
`UncertifiableSimulationError`. Arbitrary Python cannot be bound by
hash, and a record that silently dropped it would certify something
other than what ran. Express the reform as parameter values, or skip the
record.

Identity fields (`Policy.id`, timestamps) never enter the hashed
payloads — the same reform produces the same `reform.json` bytes across
constructions, so fingerprints are content-determined.

## Verifying a record

```bash
policyengine trace-tro-verify record/run.trace.tro.jsonld
```

The verifier reads every artifact in the TRO's composition from its
arrangement location — relative paths resolve inside the record
directory, `https://` locations are fetched — rehashes the bytes, and
recomputes the composition fingerprint:

```
ok: bundle_tro (bundle.trace.tro.jsonld)
ok: reform (reform.json)
ok: input (input.json)
ok: results (results.json)
fingerprint: ok
ok: record/run.trace.tro.jsonld
```

This complements `trace-tro-validate`, which checks structure against
the shipped JSON Schema; `trace-tro-verify` checks substance. It works
on any TRO this package emits, including the bundled country TROs:

```bash
policyengine trace-tro us --out us.trace.tro.jsonld
policyengine trace-tro-verify us.trace.tro.jsonld
```

Artifacts a verifier knowingly cannot fetch (for example
restricted-access data pinned in a build TRO) can be excluded with
`--skip <artifact-id>`; they are listed as skipped rather than silently
ignored, so the verification stays honest about its coverage.

## What verification does and does not establish

Verification establishes that the record's bytes are exactly the bytes
the TRO binds, and that the pinned bundle is the one a public, certified
release describes. It does not make PolicyEngine's own runs
third-party-attested — when we run our own code, the record is our
structured, checkable claim, not an arm's-length guarantee. The
verifiable parts are the hashes anyone can recompute; institutional
accountability covers the rest. See [Release bundles](release-bundles.md)
for the certification layer underneath, and the
[TRACE case study](trace-case-study.md) for a worked verification.
