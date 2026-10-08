# Replace the temporary ACS WIC assumption

## Current behaviour

The certified local-area release
`populace-us-2024-buildo-acs-local-767312d60-20260923T074941Z` stores donor
participation decisions as `would_claim_wic`, with missing decisions on ACS
people. The current model consumes the monthly person input
`takes_up_wic_if_eligible`.

The wrapper's temporary compatibility exception preserves all valid existing
decisions and sets only missing decisions on people whose
`person_support_channel` is `acs_2024_1yr` to `True`. This explicitly assumes
that every eligible affected ACS person claims WIC; it does not make them
eligible. The country model still calculates eligibility and benefits.
Missing donor decisions, missing identifying provenance, and malformed values
remain errors. Source H5 files are never modified by this exception.

The shared loader applies this before calculation and year preparation,
including baseline/reform branches and verified state derivatives. Existing
national donor decisions are preserved. State derivatives remain opt-in
preparation artifacts, not new certified datasets or request-serving defaults.

## Replacement ownership

[Microcosm #1154](https://github.com/PolicyEngine/microcosm/issues/1154) tracks
the code repair, a rebuild/publication performed by a separate dataset owner,
certification in this repository, and removal of the exception. Do not close
that issue when the Microcosm code merges. Passing code tests does not certify
a replacement population.

The Microcosm repair must generate ACS participation after the demographic
inputs are populated and before combining the population with donors. It must
reuse the existing category-specific WIC generator, preserve donor decisions,
write complete boolean `takes_up_wic_if_eligible`, and reject default-filling
missing WIC participation. The dataset owner must rebuild affected calculations
and calibration outputs and satisfy every existing release check.

## Remove the exception

The removal change is prepared as a separate stacked draft PR now. It is
blocked until a new qualified local-area release is published. Do not invent
its revision or hash, weaken tests, or merge removal against the broken pin.

When the owner supplies the release:

1. Use the existing
   [US certification runbook](build-m-us-populace-certification.md), supplying
   the actual immutable replacement regional manifest. Keep the national
   manifest, default dataset, and model pins unchanged unless separately
   approved. A model mismatch requires a reviewed compatibility claim or a
   compatible replacement build, not a bypass.
2. Confirm complete current-name participation on the replacement, with no
   obsolete WIC input column, and record its immutable revision and hashes.
3. Update the already-open removal PR with certification changes and derived
   bundle metadata. Rebase and retarget it to `main` after its compatibility
   parent merges.
4. Delete only the ACS `True`-fill exception. Retain ordinary old-name mapping
   while other certified datasets require it. Restore strict missing-value
   regression tests and verify native current-name inputs.
5. Run the focused mapping/preparation tests and the certification checks on
   the actual replacement. Never reuse prepared outputs derived from another
   source revision/hash.

This work does not rebuild or publish the full dataset, launch paid compute,
modify the national latest pointer, deploy services, or introduce environment
variables or database changes.
