# New Zealand Axiom pilot

The source-only NZ adapter executes the two WFF/IWTC entitlement comparisons in
`rulespec-nz/nz/policies/budget/official_budget_reform_replication.yaml` through
the real Axiom dense runtime. It does not install a `policyengine-nz` model or
expose a certified `pe.nz` bundle.

## Prerequisites

Use Python 3.14 and compatible source installations of `microcosm-frame`,
`axiom-rules-engine`, and its compiled dense extension. Microcosm must provide
`NZ_SCHEMA`, `AxiomPeriod`, explicit `rulespec_roots`, and the shared Axiom HDF5
reader. These dependencies remain source-only; this change does not add an
unavailable package extra or change US/UK pins.

The rules checkout must have committed NZ source, the official-budget transport
contract, and its toolchain configuration. The adapter records the RuleSpec
commit, source and contract hashes, Microcosm/Python source hashes, and native
binary hash. A source-built extension can lack package version metadata; its
binary hash remains mandatory. Wrapper package versions do not establish the
native engine's release version.

Restoring a serialized model configuration verifies the saved runtime identity.
It fails if source or native code has changed; create a new model explicitly to
run a different version.

## Input and calculation contract

Use the example in `examples/nz_axiom_pilot.py` with a supplied HDF5 artifact and
its verified SHA-256. The reader uses Microcosm's actual entity-table codec,
including Decimal and nullable-boolean preservation.

- The artifact contains person, household, and family tables and build label
  `2026`. Axiom receives the explicit tax year `2026-04-01` to `2027-03-31`.
- Only the household table stores weights. Frame resolves person and family
  weights through membership; the adapter exposes those effective weights in
  memory through MicroDataFrames. Family members must share one household.
- All 11 substantive family inputs must be present and satisfy the transport
  contract. The 10 unrelated eager-graph padding inputs may default to their
  declared zero values. Stored formula outputs and nonzero padding fail.
- Decimal inputs retain their values. The pilot rejects values outside the
  declared `decimal128(18,2)` contract; the runtime also checks whether its native
  numeric boundary can represent them.
- Outputs remain in memory. Running or saving a simulation never writes over
  its input artifact. Receipts identify both the original artifact and the
  actual in-memory inputs, including edits made after loading.
- This pilot supports neither arbitrary reforms nor dynamic or geographic
  scoping controls. Use `Simulation.run()` for an explicit fresh execution.

The two outputs are `budget_2025_wff_abatement_entitlement_change` and
`budget_2026_iwtc_entitlement_change`. Aggregate them with the returned
MicroSeries `.sum()`, not manual multiplication by person or family weights.

NZ model configurations and direct `PopulaceNewZealandDataset` outputs support
Pydantic JSON round-trips. The NZ-only table codec retains exact Decimals,
nullable booleans, categories, indices, dtypes, and effective weight columns.
Serialize the output dataset itself with `output_dataset.model_dump_json()` and
restore it with `PopulaceNewZealandDataset.model_validate_json(...)`.

The shared `Simulation` model still serializes through base-typed dataset/model
fields, which omit subclass details. Its generic JSON form is not a complete NZ
run archive; this pilot does not change that pre-existing cross-country behavior.

## What the result does not establish

The adapter does not certify the input population, repair missing family
inputs, fit weights, or calibrate to official cost estimates. A positive test
on a synthetic population is an integration check, not an NZ national result.

These annual family-entitlement changes are not yet comparable to Treasury's
forecast operating costs. Fiscal-year payment timing, WFF debt impairment,
and the temporary IWTC petrol-trigger/payment-tail treatment require explicit
bridges. The output receipt retains the upstream `bridge_required` status.
Do not attach these totals as completed Scorecard budget-score replications.

## Verification

Ordinary boundary tests use non-statutory runtime doubles. The opt-in test uses
Microcosm's real writer and reader plus Axiom's compiled RuleSpec module, with
nonuniform household weights and two upstream companion cases:

```sh
POLICYENGINE_SKIP_COUNTRY_IMPORTS=1 \
RUN_NZ_AXIOM_INTEGRATION=1 \
RULESPEC_NZ_ROOT=/path/to/rulespec-nz \
uv run --no-sync pytest --noconftest -q tests/test_nz_axiom_pilot.py
```
