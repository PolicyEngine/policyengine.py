# Fix the release-candidate tooling's two defects (lane of 2026-09-14)

Branch `max/wrapper-release-candidates-20260914`, stacked on `818c894e`
("Build and verify isolated wrapper release candidates"). That commit is
already the head of PR #515's branch `max/spm-canonical-wrapper-release-20260910`
(verified against origin), so this lane's PR is the four commits on top of it.
The prior lane's record is preserved below, unchanged.

This branch cannot stand on `main`. Verified against `origin/main`:
`scripts/release_lock.py`, `scripts/check_release_credentials.py` and
`scripts/spm_bundle.py` do not exist there; `scripts/bundle.py` exists but has
no `--published-spm`; and `trace_tro.schema.json` exists but its `pe:emittedIn`
enum is `["local", "github-actions", "policyengine-api"]`, without the
`repository-bundle` value `release_build.py` emits.

## State

The release-candidate tooling stays. Three things it carried are fixed: an
unverified household-test rewrite, a stale publication-gate assertion, and a
source-origin check that refused namespace packages.

## Done

- Verified the worktree at `818c894e`, clean tree. Synced the locked
  environment (`uv sync --frozen`, Python 3.14.4).
- Reproduced both defects: baseline `pytest tests/test_release_build.py
  tests/test_spm_bundle_bootstrap.py tests/test_graph -q` gave 2 failed,
  98 passed.
- Established defect B's trigger with an instrumented probe over three import
  phases rather than assuming it. Bare `import policyengine`: 0 offenders.
  After `tests/conftest.py`: exactly one, the namespace package
  `policyengine.tax_benefit_models` (`__file__` None, `__path__` inside the
  checkout). After `tests/test_graph/test_extractor.py`: two more, the bare
  stand-ins it installs for `policyengine` and `policyengine.graph`. The
  conftest one is why the test failed even when run alone.
- **Commit `35981756`** restores `tests/test_spm_household.py` to its
  `1b6c001c` content, byte-identical (sha256 `fe6df0c7...`). The rewrite at
  `818c894e` (sha256 `061cbc1b...`) drives the assisted case through
  `pha_payment_standard`, `receives_housing_assistance`,
  `spm_unit_allocated_housing_subsidy` and `spm_unit_allocated_tenant_payment`
   — country behaviour the unified candidate policyengine-us#9467 carries, not
  the pinned model. It went through the R1–R3 reviews unverified. It comes back
  with the country repin, once #9467 publishes and the pin moves. Note this
  file is where Ruling A landed (see the prior lane below); `1b6c001c` is the
  reviewed post-Ruling-A content, so the revert keeps Ruling A intact.
- **Commit `14e5db47`** fixes the publication-gate assertion. `818c894e`
  replaced the Publish job's inline `bundle.py check --published-spm` with
  `release_build.py publish-check`, so the test's `next(...)` matched nothing
  and raised `StopIteration` instead of asserting. It now finds the step that
  carries the gate. `publish_check` still runs that same check
  (`scripts/release_build.py:1381`), pinned by
  `test_publication_checks_existing_strict_gates_before_member_comparison`.
- **Commit `abf75454`** fixes `assert_source_origin`. `module_origin` places a
  module by `__file__` when it has one and otherwise by every `__path__`
  portion, each of which must resolve inside the prepared source. Neither, an
  empty `__path__`, or any portion outside is still refused.
  `tests/test_graph/test_extractor.py` now restores `sys.modules` in a
  `finally`, leaving nothing behind. Three regression cases added.
- Mutation-checked the new tests. Reverting to the pre-fix logic fails the
  acceptance case; accepting any file-less module fails all three refusals.
- Targeted suite after the fixes: 104 passed, exit 0.
- `ruff format --check .`: exit 0. `ruff check .`: 11 UP038 findings, every one
  present at `818c894e` and none in a file this lane touches; the touched files
  pass clean. Local ruff is 0.12.11; CI installs latest, where UP038 is gone.

- Full suite: 1203 passed, 9 skipped, 280s, exit 0.
- Pushed `d841dae3`; draft PR #520 open against
  `max/spm-canonical-wrapper-release-20260910`.

## Corrections to earlier claims in this lane

- `abf75454`'s message names `tests/conftest.py` ->
  `tests/fixtures/us_reform_fixtures.py:12` as the import path to the namespace
  package. That path is real but not the first: `tests/conftest.py:6` ->
  `tests/fixtures/filtering_fixtures.py:7` reaches it earlier in every session.
  Both are unrestored module-level imports and the fix covers either.
- The rewrite's dependency on #9467 is now verified rather than assumed. Exactly
  two of the names it introduces are absent from the pinned policyengine-us
  2.0.0 -- `spm_unit_allocated_housing_subsidy` and
  `spm_unit_allocated_tenant_payment`, zero `class <name>(Variable)` definitions
  each -- and PolicyEngine/policyengine-us#9467's file list adds exactly those
  two variable files. `pre_subsidy_rent`, `pha_payment_standard` and
  `receives_housing_assistance` do exist in 2.0.0.
- No review examined either defect. `tests/test_spm_bundle_bootstrap.py` appears
  in none of the six `WRAPPER-RELEASE-BUILD*` files, none of the three frozen
  inventories and none of the three independent reviews.
  `WRAPPER-RELEASE-BUILD-R2-RESPONSE.md:35` carries
  `tests/test_spm_household.py` by hash and delegates it elsewhere; the three
  reviews contain zero occurrences of "household".

## Next

1. Wait for CI on PR #520 (`gh pr checks 520`).
2. The household rewrite returns with the country repin, once #9467 publishes.

---

*Below: the prior lane's record, restored verbatim. An earlier commit in this
lane (`44604506`) overwrote it; `abf75454`'s successor puts it back.*

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

- **Ruling A done** (`85b1d711`). Read the authoritative source in the 2.0.1 wheel:
  `spm_unit_capped_housing_subsidy` computes `assisted = housing_assistance > 0`, returns
  zeros without touching the provider when none is assisted, and otherwise calls
  `masked_policyengine_amount`, which evaluates only the assisted rows through
  `CountyRequiringSPMProvider`. Probed all four clauses against the installed model rather
  than assuming: 5/5 resource outputs compute with an empty measurement receipt when housing
  assistance is zero; 5/5 raise `SPM_GEOGRAPHY_REQUIRED` when it is positive; threshold and
  poverty raise either way; default outputs still require the choice. Updated the public
  docstring, `docs/households.md`, and the contract test (renamed, since its old name
  asserted the unconditional rule). 42/42 SPM household tests pass.
- **Ruling C done** (`456af5da`). Regenerated `us_model_surface`:
  `num_variables_bucketed_100s` 57 -> 61 (raw 6157), `num_parameters_bucketed_100s`
  978 -> 1025 (raw 102525), `data_package_name` `populace-data` -> `microcosm-data`.
  Counted the raw surface under both installed wheels: **identical** on 2.0.0 and 2.0.1
  (6157 / 102525 both), so this snapshot is already the 2.0.1 value.
- **Ruling D done** (`74675620`). Excluded the four contaminated fields rather than
  xfailing the case, because all four are downstream of the one defect and an xfail would
  have discarded the other 42 fields of coverage. Two guards make it honest:
  `_check_snapshot` preserves prior values for excluded fields under
  `PE_UPDATE_SNAPSHOTS=1` (verified by md5 across a refresh), and
  `test_snap_annualization_defect_still_present` fails loudly on fix. Note a strict xfail
  would *not* have failed loudly: the corrected annual figure is ~3,576 against a stored
  3,596.04, so the case would have gone on xfailing silently.
- Confirmed policyengine-us#9447 is OPEN and its body records the same values on 1.825.2
  and 2.0.0, independently corroborating Ruling D.

- **Ruling E done** (`04960e64`), and **Ruling D reversed on a corrected premise** (`2019530f`).
  Fanned out the country archaeology across the four drift signatures, each adversarially
  verified from three lenses (arithmetic, provenance, alternative-cause): 12 verdicts, 11
  upholding, 1 refuting. Two root causes explain all three Ruling-E cases, both reproduced
  from parameter values to the cent:
  - `c991cd844a` (PR #9100, 1.779.1) added published BLS CPI-U actuals, moving the
    2026-01-01 index 323.364 -> 326.588; the NSLP/SBP per-meal rates uprate through it, so
    the free-tier net school meal subsidy goes 1130.96 -> 1142.24.
  - `df3482f4ef` (PR #9059, 1.776.2) moved `uprating: gov.states.ca.cpi` off the CA standard
    deduction's file-level metadata, where `uprate_parameters` never read it, onto each
    filing status. The deduction un-freezes into 2026: SINGLE 5,706 -> 5,835.31,
    JOINT/HOH 11,412 -> 11,670.63. At the 6% and 9.3% marginal brackets that is -7.76 and
    -24.05 exactly.
- **The SNAP finding overturned Ruling D's premise, and I verified it myself before acting.**
  There is no annualization defect; the x12 is intact. The case is an ABAWD with no hours
  supplied, and two country changes decide it: `82745ca239` dropped
  `weekly_hours_worked_before_lsr`'s default from 40 to 0, and `74b0a75e5f` added
  `waived_states.yaml`, under which California's statewide ABAWD waiver expires 2026-01-31.
  One eligible month at 298.00. Measured directly: monthly snap 2026 is `[298, 0 x 11]`;
  the same household with hours = 40 returns 3607.571; CA/IL/NV return 298.00 while
  TX/NY/FL return 0.00. The year series I had cited as proof of a resolution defect
  (584/3522/298/0 for 2024-2027) is the CA waiver schedule read line by line. So the four
  fields were rebaselined under Ruling E's standard and the defect guard was replaced with
  a test pinning the real mechanism.

## Next

1. Ruling E: regenerate the three drifting snapshots, justify every field against a located
   country change. Root causes already isolated by measurement - the three cases reduce to
   exactly two: school meal subsidy 1130.96 -> 1142.24 (+11.28, both child cases) and CA
   state income tax (-7.76 at 60k single, -24.05 at 240k joint). Archaeology running.
2. Full `make test` as CI runs it; lint, mypy, changelog; push; `gh pr checks 515`; update
   the PR body and mark ready for review.
3. Ruling B stays blocked - see BLOCKER above. Hand the publisher the evidence pack.
