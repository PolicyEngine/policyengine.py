# Finalize wrapper PR #515 on policyengine-us 2.0.1

## State

**Starting.** Prior lane (head `e7bfa2bd`) bound the wrapper to policyengine-us **2.0.0**
and left six tests red, blocked on wheel provenance and on wrapper-owner decisions it had
no standing to make. Both blocks are now lifted:

- **policyengine-us 2.0.1 is published** (verified this lane, 2026-09-12): PyPI returns 200,
  wheel sha256 `20e355823bbc89e6c9f413435a7d0b92095cff65541ea366048ee448da025aee`,
  sdist `3183f5b1adf4f17963eec46e04bb51da5cd9b6bbda4b38fdebaea7ffa486f660`,
  uploaded 2026-09-12T03:56:48Z. It is 2.0.0 plus the above-the-line-deduction determinism
  fix (pe-us #9446) that the accepted candidate wheel carried and the merged 2.0.0 lacked.
- **The root has ruled** on the four wrapper-owner decisions (rulings A-E in the brief).

This lane repins to 2.0.1, aligns the SPM resource contract with the authoritative country
behaviour, and settles all six red tests under those rulings.

## Rulings being applied

| Ruling | Substance |
|---|---|
| A | Country model behaviour is authoritative for the SPM resource contract. Housing cap consults the SPM housing portion only for units with housing assistance to cap. Unassisted units are zero, no geography or composition requirement. Assisted units without county still fail closed (`SPM_GEOGRAPHY_REQUIRED`). Explicit national computes. SPM measurement itself (threshold, poverty) always requires geography. Update the wrapper docstring(s) and `test_spm_household::test_state_only_tax_graph_succeeds_and_resource_graph_requires_geography`. |
| B | Pin policyengine-us==2.0.1, policyengine-core==3.32.5, spm-calculator==1.0.0 exactly; UK unchanged. Regenerate bundle manifest and uv.lock; run the repo's bundle checks. |
| C | `test_us_model_version_surface`: counts are identity facts of the pinned country. Regenerate; report before/after counts. |
| D | `test_us_household_snapshot[us_single_adult_no_income]`: `spm_unit.snap` 3596.04 -> 298.00 is a pre-existing country defect (one month's 2026 allotment reported annual), identical on 1.825.2 and 2.0.x, tracked at PolicyEngine/policyengine-us#9447. Do NOT rebaseline: xfail(strict=True) or exclude the single field, whichever is cleaner. |
| E | `test_us_household_snapshot` x3 (employment income, single parent, married two kids): regenerate, but justify every changed field old -> new against a located country change. Anything unexplained stays red and is reported. |

## Prerequisites (verified this lane, primary sources)

| Item | Value | Status |
|---|---|---|
| policyengine-us 2.0.1 wheel sha256 | `20e355823bbc89e6c9f413435a7d0b92095cff65541ea366048ee448da025aee` | verified (PyPI JSON, HTTP 200) |
| policyengine-us 2.0.1 sdist sha256 | `3183f5b1adf4f17963eec46e04bb51da5cd9b6bbda4b38fdebaea7ffa486f660` | verified |
| 2.0.1 declared deps | `policyengine-core>=3.30.1`, `spm-calculator==1.0.0` | verified |
| spm-calculator 1.0.0 wheel sha256 | `e354937a5e1a4045d4966ed594a528d8b02866fabaac9bb5672017004b627305` | carried from prior lane; to re-verify |
| policyengine-core 3.32.5 | pinned exactly by the bundle | to re-verify |
| HF data tag | `populace-us-2024-spm-20260909`, H5 `6496cc43...` | carried; to re-verify |

## Done

- Read the prior lane's PROGRESS.md and the full branch history (24 commits off `origin/main`).
- Verified the 2.0.1 prerequisite from PyPI directly. Wheel sha256 matches the brief exactly.
- Established the repin procedure the prior lane used (repository tooling only:
  `bundle.py update-packages`, `set-spm`, `certify-data`, `generate`; extras are generated
  from the bundle manifest, so no pin is hand-edited).

## Next

1. Ruling B: repin to 2.0.1 through the bundle tooling; recertify the US data release for
   2.0.1; regenerate derived artifacts; relock with uv; sync the venv.
2. Ruling A: read the 2.0.1 housing-cap source, rewrite the wrapper docstring and the
   contract test to assert the authoritative behaviour.
3. Ruling C: regenerate `us_model_surface`, record before/after counts.
4. Ruling D: mark the `us_single_adult_no_income` SNAP defect xfail(strict=True) / exclude
   the field, pointing at pe-us#9447.
5. Ruling E: regenerate the three drifting snapshots, justify every field against a located
   country change between 1.764.6 and 2.0.x.
6. Full `make test` as CI runs it; lint, mypy, changelog; push; `gh pr checks 515`; update
   the PR body and mark ready for review.
