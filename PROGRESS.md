# Bind the canonical wrapper to published country 2.0.0; prepare the 6.0.0 release commit

## State

**Binding complete; release BLOCKED on a wheel-provenance defect that is not mine to fix.**

Everything the brief asked for has been done: the pins, the dataset certification, the
lock, the TROs and the release guards all bind the published canonical tuple. But while
verifying, I established by direct byte comparison that **the policyengine-us 2.0.0 wheel
published on PyPI is a different, later build than the wheel the acceptance matrix
accepted**, and that the published build changes household values, drops a determinism
fix, weakens its own Core pin, and breaks this PR's own SPM contract test. Details below.

Branch `max/spm-canonical-wrapper-release-20260910`, PR #515 (draft), starting head
`223bce47`, base `origin/main` `6a56ced4`.

## Prerequisites (all verified 2026-09-11 from primary sources)

| Item | Value |
|---|---|
| policyengine-us 2.0.0 on PyPI | 200; wheel sha256 `4ca187509efc2f7d3ace5035c27de88c744d0f112fdc7da027372f3ae07c540a`, uploaded 2026-09-12T01:11:24Z |
| spm-calculator 1.0.0 on PyPI | 200; wheel sha256 `e354937a5e1a4045d4966ed594a528d8b02866fabaac9bb5672017004b627305` (matches brief) |
| policyengine-core 3.32.5 on PyPI | 200; wheel sha256 `9d8c162d5fe5c784ae16c885da3ffbfc39a536add0e111133144d8edd555935f` |
| Core 3.32.5 gate | Both conditions met: PyPI 200, and `rollout/final-core-matrix-20260911-r2` records the same Core sha256 as its runtime |
| HF tag `populace-us-2024-spm-20260909` | commit `9a814a3b3b53c0ecd6e1737b6ec862c31300ef6f` |
| H5 it resolves to | `6496cc4393d4d3c6574f76eca231de5898c803b9067645591fd5c4d3e65aee84` (matches brief) |
| Certified release manifest | sha256 `6c39eb1e61afc1629f2abe57032dced9c0750c60e42b9acad812c7b3476a2989`; the local file under `rollout/h5-producer-20260911/certified/` is byte-identical to the Hub-published one |
| PR #515 at dispatch | draft, open, MERGEABLE, head `223bce47` == local == origin; 9 checks pass, 4 `Test` jobs fail |

## BLOCKER: the published country wheel is not the accepted country wheel

Verified by me directly, comparing zip members of the PyPI wheel against
`rollout/country-deterministic-wheel-20260910/wheels/policyengine_us-2.0.0-py3-none-any.whl`
(sha256 `4208998a…`, the build recorded in `final-core-matrix-20260911-r2/FINAL-RECEIPT.json`
as the acceptance runtime):

| Difference | Accepted `4208998a` | Published `4ca18750` |
|---|---|---|
| `policyengine_us/spm.py` | no `CountyRequiringSPMProvider`, no `masked_policyengine_amount` | **both added** |
| `adjusted_gross_income_person.py:24` | `sorted(set(all_alds) - set(PERSON_ALDS))` | `list(set(...))` — **determinism fix dropped**; AGI float summation order now varies with `PYTHONHASHSEED` |
| METADATA core pin | `policyengine-core==3.32.5` | `policyengine-core>=3.30.1` — **weakened** |
| NY CTC post-2024 phase-out, SURVIVING_SPOUSE | `110_000` | `75_000` (effective 2025-01-01) — **value changing** |

Three local 2.0.0 builds exist (`4208998a`, `05c729ae`, `08fe6f7e`); none is the published
one, and the published hash appears nowhere on disk. spm-calculator 1.0.0 is fine — the
published and local wheels are content-identical (all 68 members match; only zip
timestamps differ). Core 3.32.5 matches exactly.

**Consequences.** The poverty rates in `final-core-matrix-20260911-r2/FINAL-REPORT.md`
(13.018144 / 13.235362 / 13.634486 / 13.638541) cannot honestly be attributed to the
published tuple. And `CountyRequiringSPMProvider` — code that exists only in the published
build — is what makes 9 pre-existing microsim tests fail and makes this PR's own
`test_spm_household::test_state_only_tax_graph_succeeds_and_resource_graph_requires_geography`
fail with "DID NOT RAISE".

I have therefore **not** rewritten any numeric snapshot or contract assertion to match the
published build. Doing so would launder an unaccepted baseline and bury a determinism
regression behind a green suite.

## Done

- Verified every prerequisite from primary sources rather than from prior lanes' reports.
- Repinned via the repository tooling only — `bundle.py update-packages`,
  `bundle.py set-spm --calculator-version 1.0.0` (which downloads and re-hashes the
  published wheel), `bundle.py certify-data`, `bundle.py generate`. `pyproject.toml`
  extras are generated from the bundle manifest, so no pin was hand-edited.
- Promoted spm-calculator from the protective `country_dependency` pin to the
  registry-verified `runtime_dependency` the `--published-spm` release gate requires.
- **Fixed a real certification defect** (commit `a7080192`). The producer now publishes
  under `microcosm-data` with `evidence`-kind sidecars; four rules in
  `certification.py` matched the literal `populace-data` and the release-directory path
  rewrite matched only `diagnostics`. Certifying this release under the old rules produced
  a bundle where **8 of 10 certified artifact URIs returned HTTP 404**, with the
  reachability sweep silently disabled. With both names and both kinds recognised, all ten
  resolve (verified by HEAD request). Six regression tests added.
- Relocked with uv only, registry sources throughout, no local wheel links.
- Rebound both TRACE TROs with a Hugging Face token so the UK sidecar kept its full
  private release manifest instead of silently degrading.
- Ran the full suite. The previously-skipped SPM tests now **run**: skips fell 14 -> 9 and
  passes rose 1005 -> 1079.

## Next

1. Apply only the failure fixes that are safe — those asserting the superseded legacy pin
   identity. Leave the numeric and contract failures red and documented.
2. Push with `--force-with-lease` against `223bce47`, watch CI, leave the PR a draft.
3. Escalate the wheel-provenance blocker to the coordinator: either republish
   policyengine-us 2.0.0 from the accepted source, or re-run the acceptance matrix on the
   published wheel bytes (pinning `PYTHONHASHSEED`, given the dropped ALD fix).
