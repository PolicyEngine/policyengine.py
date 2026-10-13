# Replace the temporary ACS-local SPM compatibility

> **TEMPORARY — THIS MUST BE REPLACED.** These two fixes stand in for data
> contracts that the certified ACS-local source should carry itself. Delete them
> as soon as the replacements below are certified.

Both fixes apply only to year files cut from the certified ACS-local source
`populace-us-2024-buildo-acs-local-767312d60-20260923T074941Z` (SHA-256
`769756c31f3ca646d12c272511744dec04c0e68870c6946dd945fbba65b6a7ec`). Without
them, every calculation on that source stops with `SPM_COMPOSITION_REQUIRED`
("SPM unit has no classified adult"). Source H5 files are unchanged.

## 1. Group quarters outside the SPM measurement (#597)

[`spm_measurement_scope`](../../../src/policyengine/tax_benefit_models/us/spm_measurement_scope.py)
follows Census's ACS SPM methodology, which measures the household population
only:

- Classification uses the source's record-type evidence. ACS records with
  `TYPEHUGQ` 2 or 3 and the matching `RELSHIPP` (37 or 38) are group quarters.
  ACS housing-unit records and the `asec` and `puf_tax_detail` channels are
  measured. Age is never used, and any other evidence raises an error.
- `create_datasets` stores the classification as the SPM-unit input
  `policyengine_outside_spm_measurement`, together with a
  `policyengine_spm_measurement_scope` record.
- When a run's input data carries that record, both the run and its baseline
  change their SPM variables:
  - Group-quarters units never reach the canonical SPM provider.
  - Their thresholds, resources and poverty indicators are NaN ("not
    measured").
  - Poverty indicators become floats (1.0, 0.0 or NaN).
- Measured units keep the canonical values. Every ordinary tax, benefit and
  income calculation is unchanged, and nobody is dropped.

The full source has 183,206 group-quarters SPM units, all single-person.

## 2. Certified SPM independence role for ASEC/PUF records (#598)

[`spm_independence_role`](../../../src/policyengine/tax_benefit_models/us/spm_independence_role.py)
handles the second gap:

- The source does not store `is_spm_independent_minor_role`, so the model falls
  back to "household head or spouse".
- That fallback leaves 28 Census-built ASEC/PUF SPM units, each formed around
  an independent 15–17-year-old, without a classified adult.
- `create_datasets` joins the certified national release's list
  `releases/populace-us-2024-spm-20260915/source_spm_person_independence.csv`
  (SHA-256 `22b5968d90fecfeef7614583e493fe10cc16bda8b5be82e6f49a5bc2102d3ce5`, pinned in the bundle manifest) onto the
  source's ASEC/PUF people by `person_id` and `person_spm_unit_id`.
- The join must be exact. ACS people keep the model's own fallback value.

Only those 28 units change.

## Remove the fixes

Each fix is removed as soon as its replacement is certified.

| Fix | Replacement |
| --- | --- |
| #597 | A certified ACS-local release declares SPM measurement scope itself (for example [Microcosm #977](https://github.com/PolicyEngine/microcosm/pull/977) activated in the release build), and a policyengine-us release that reads it ([policyengine-us #9462](https://github.com/PolicyEngine/policyengine-us/pull/9462) or its successor) is in the certified bundle. |
| #598 | A certified ACS-local release stores `is_spm_independent_minor_role` for its ASEC/PUF records (a rebuild that includes [Microcosm #959](https://github.com/PolicyEngine/microcosm/pull/959)). `independence_roles` raises once the source stores the role. |

Then:

1. Certify the replacement with the
   [US certification runbook](build-m-us-populace-certification.md).
2. Delete the module, its call sites in `datasets.py`, `model.py`,
   `model_version.py`, `simulation.py` and `run_record.py`, and its tests.
3. Run the focused SPM and country-model integration tests, and the real
   ACS-local preparation check in the simulation API.

These fixes do not rebuild or publish data, deploy services, or introduce
environment variables or database changes.
