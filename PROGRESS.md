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

## BLOCKER (Ruling B): 2.0.1 is published, but no data release is certified for it

**The repin to policyengine-us 2.0.1 cannot be completed in this repo.** It is blocked on
an act by the *data publisher*, not by anything in the wrapper.

The certified US data release `populace-us-2024-spm-20260909` publishes this claim:

```json
"build": {"built_with_model_package": {"name": "policyengine-us", "version": "2.0.0"}},
"compatible_model_packages": [{"name": "policyengine-us", "specifier": "==2.0.0"}]
```

`certify_data_release_compatibility` accepts exactly three bases — build-time match,
matching data build fingerprint, or a publisher `compatible_model_packages` claim. 2.0.1
satisfies none (the manifest records no `data_build_fingerprint`), so:

- `bundle.py certify-data --model-version 2.0.1` **refuses**:
  *"policyengine-us 2.0.1 matches neither the build-time model (2.0.0) nor any publisher
  compatibility claim ['==2.0.0']; a new data build or a published compatibility claim is
  required."*
- With 2.0.1 installed, the gate fires at **import of the US model** (`us_latest =
  PolicyEngineUSLatest()`, `model.py:512`), raising *"Data release manifest is not certified
  for the runtime model version 2.0.1 in country 'us'."* Not just microsimulation —
  `pe.us.calculate_household` and every US test error out too.

This is the documented, intended behaviour. `docs/engineering/skills/data-certification.md`:
*"Neither basis means certification is refused: a new data build or a published
compatibility claim is required."* There is no override flag, and I did not manufacture one:
hand-writing a claim into the bundle, or mutating the published release manifest at an
immutable release tag, would launder exactly the invariant this gate exists to protect.

I verified no published release covers 2.0.1: all 25 `policyengine/populace-us` tags and all
3 branches were enumerated; `populace-us-2024-spm-20260909` is the newest, and its manifest
carries `==2.0.0` on both the tag and `main`.

### The claim-widening is substantively justified (evidence for the publisher)

2.0.1 is 2.0.0 plus pe-us#9446 and nothing else. Verified by extracting and diffing both
published wheels:

| Check | Result |
|---|---|
| Files differing, whole wheel | 2 variable `.py` files + 1 added test (`tests/core/test_ald_determinism.py`) + dist-info |
| `variables/` file set | **identical** — 5981 files in both |
| `parameters/` file set | **identical** — 5970 files, and byte-identical content |
| Substance of both diffs | `list(set(all_alds) - ...)` -> `sorted(set(all_alds) - ...)` |
| 2.0.1 wheel sha256 | `20e355823bbc89e6c9f413435a7d0b92095cff65541ea366048ee448da025aee` (PyPI-declared == downloaded == brief) |

The change alters only the *order* of float summation within above-the-line-deduction
aggregation. No variable, parameter, or input schema changed, so the dataset's compatibility
with the model is unaffected — widening the claim to cover 2.0.1 asserts nothing the bytes
do not already support.

**Unblocking action (data publisher, one line):** publish a populace-us release whose
manifest claims `policyengine-us` compatibility covering 2.0.1 (a new release tag —
never an in-place edit of the existing immutable tag). The wrapper side is then
`bundle.py update-packages --us 2.0.1` + `certify-data --model-version 2.0.1` + relock.

**This lane therefore leaves the branch on the certified 2.0.0 tuple** and completes every
other part of the brief in full. A branch pinned to 2.0.1 would fail to import the US model
at all, making PR #515 entirely red and unreviewable — strictly worse than what it replaces.

### Consequence for Ruling C

Ruling C asks for the variable/parameter counts "regenerated for 2.0.1". Because the
`variables/` and `parameters/` file sets are provably identical between 2.0.0 and 2.0.1,
those counts are the same number on either pin. Regenerating on 2.0.0 yields exactly the
2.0.1 result.

## Done

- Read the prior lane's PROGRESS.md and the full branch history (24 commits off `origin/main`).
- Verified the 2.0.1 prerequisite from PyPI directly. Wheel sha256 matches the brief exactly.
- Ran the repin through the tooling, hit the certification gate, and reverted to the certified
  2.0.0 tuple with a clean tree (see BLOCKER above).
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
