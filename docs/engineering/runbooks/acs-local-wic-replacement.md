# Replace the temporary ACS WIC assumption

## Behaviour before removal

The certified local-area release
`populace-us-2024-buildo-acs-local-767312d60-20260923T074941Z` stores donor
participation decisions as `would_claim_wic`, with missing decisions on ACS
people. The current model consumes the monthly person input
`takes_up_wic_if_eligible`.

The compatibility parent preserves all valid existing decisions and sets only missing
decisions on people whose `person_support_channel` is `acs_2024_1yr` to `True`.
This explicitly assumes that every eligible affected ACS person claims WIC;
it does not change eligibility. Missing donor decisions, missing identifying
provenance, and malformed values remain errors. Source H5 files are unchanged.

The existing loader applies this before calculation and year preparation,
including baseline and reform branches. The fix does not add partitioning,
state/year preparation APIs, new dataset defaults, or deployment behavior.

## Replacement ownership

[Microcosm #1154](https://github.com/PolicyEngine/microcosm/issues/1154) tracks
the code repair, a dataset rebuild and publication by a separate dataset owner,
certification in this repository, and removal of the exception. Merging the
[code repair](https://github.com/PolicyEngine/microcosm/pull/1156) does not
publish a replacement population or complete that issue.

The repair generates ACS participation after completing demographic inputs and
before combining ACS records with donors. It reuses the existing WIC generator,
preserves donor decisions, writes complete boolean participation inputs, and
rejects missing decisions. The dataset owner must rebuild the affected outputs
and satisfy the existing release checks.

## Remove the exception

The separate stacked [removal PR #563](https://github.com/PolicyEngine/policyengine.py/pull/563)
must remain a draft until the replacement dataset has been published and
certified. Do not invent its revision or hash or relax its failing check.

This branch removes the exception and rejects all missing legacy decisions,
including ACS decisions. `test_acs_wic_replacement.py` intentionally fails
while the known incomplete source remains certified. That failure is a merge
requirement, not a test to skip. No replacement is currently certified by
these changes.

Once the replacement is available:

1. Follow the [US certification runbook](build-m-us-populace-certification.md)
   with its actual immutable regional manifest. Keep national defaults and
   model pins unchanged unless separately approved.
2. Verify complete current-name participation on the replacement and record
   its revision and hashes.
3. Add the real certification changes to the removal PR and rebase it onto
   `main` after the temporary compatibility fix merges.
4. Delete only the ACS missing-value exception. Keep ordinary legacy-name
   mapping while other certified datasets require it.
5. Run the focused mapping and country-model integration tests and validate
   preparation against the actual replacement dataset.

This fix does not rebuild or publish data, deploy services, or introduce
environment variables or database changes.
