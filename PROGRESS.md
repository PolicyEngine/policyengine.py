# Canonical SPM wrapper release PR

## State

**Complete, and independently re-verified.** Draft PR
https://github.com/PolicyEngine/policyengine.py/pull/515 is open against `main`
from `max/spm-canonical-wrapper-release-20260910`, with ten commits and hosted CI
run. #512 is left open and untouched, referenced as superseded.

The lane was cut off by a rate-limit re-pick after opening the PR and before
writing its report, leaving the deliverable at 0 bytes. The resumed lane re-ran
every local check from scratch, re-derived the file-set comparison, and put the
PR body's mechanism claims through a six-way adversarial audit.

Hosted CI: nine checks pass (changelog, Lint, Mypy, Verify bundle metadata,
Install + smoke-import on 3.11/3.12/3.13/3.14, docs build); the four `Test`
jobs fail, each with `39 failed, 1005 passed, 14 skipped` — identical to the
local run, one root cause.

## Done

- Read background: production checkout handoff/output/progress/native-loader
  reports and `rollout/wrapper-loader-candidate/FINAL-REPORT.md`.
- Step 1 file-set comparison. release-final carries 72 changed/untracked paths,
  production 70. release-final adds exactly six (the TRO schema fix plus a
  regenerated `uv.lock`); production holds only four extra working reports,
  which were not committed. 55 of 66 common paths are byte-identical.
  Eleven differ; after adversarial verification, four differ beyond the rebase,
  the TRO schema fix and the Python floor bump — all a deliberate, internally
  consistent relocation of release gates out of PR CI into `push.yaml`, plus
  extra `importorskip` gating release-final has and production lacks.
- Verified the TRO sidecars rebind to the working-tree manifest hash
  `d430b8e561d76e5836a17bf506b06b9cd16560eb77f15718dd46f4e78513de85`.
- Step 2 safety audit: all 36 untracked paths are text, 195 KB total. No
  wheels, venv, `__pycache__`, `.h5` or binaries; no secret-shaped strings; no
  `/Users/...` paths. Excluded the four production report files, and `.coverage`
  produced by my own test run.
- Corrected a provably false paragraph in the new runbook: it claimed
  `TestVendoredSidecarBinding` "currently fails" and cited superseded hashes.
  Verified the test now passes and rewrote the paragraph around the real
  binding.
- Step 3: seven logical commits, sentence-case subjects, each ending with the
  `Co-Authored-By: Claude Fable 5.1` trailer. All 72 paths land in exactly one
  commit; working tree clean afterwards.
- Step 4 local checks. Green: `make install`, ruff format, ruff check,
  `uv pip check`, `check-changelog.sh`, `bundle.py check`, `release_lock.py`,
  `policyengine bundle verify`, smoke import, `--collect-only`. `make test`
  exits 1: 39 failed, 1005 passed, 14 skipped. `mypy` exits 2 but its CI step
  is non-blocking and fails the same way on `main`.
- Established why no pin bump fixes the 39. `spm-calculator 1.0.0` reached PyPI
  today (2026-09-11T15:45:10Z), but `policyengine-us 2.0.0` has not (latest
  1.825.0). Probed in a throwaway venv: with calculator 1.0.0, country model
  1.764.6 cannot load its own variables, because
  `spm_unit_geographic_adjustment` imports `spm_calculator.geoadj`, removed in
  1.0.0. Publishing policyengine-us 2.0.0 is the gate.
- Steps 5-7: pushed the branch (it did not exist on origin), opened the draft
  PR, and watched CI to completion.
- Re-verification pass. Corrected the file-set numbers: 73 release-final paths
  (not 72), 67 common, 54 byte-identical, 13 differing (not 11), and production
  holds three exclusive reports, not four — `PROGRESS.md` exists in both
  checkouts under the same name. Of the 13, two are pure rebase artifacts
  (`origin/main` already carries 5.3.1 and the `spm-calculator`
  `country_dependency` pin), three are consequences of the rebase, two are the
  TRO schema fix and the Python floor, four are deliberate divergences, and two
  are non-code.
- Six-cluster adversarial audit of the PR body against source. Of ten claims an
  auditor flagged, nine were refuted and stand as written. One survived: the
  body and the source comment both justified storing the SPM receipt as an H5
  dataset by saying receipts "exceed HDF5's attribute-size limit". That limit
  was an HDF5 1.6-era compact-storage threshold lifted in 1.8. Confirmed by
  direct test on the pinned stack (h5py 3.16.0, libhdf5 2.0.0): attributes of
  65KB, 110KB, 282KB and 5MB all write and round-trip byte-identical into a
  `pd.HDFStore(mode="w")` file, with pandas still reading the frames after.
  The storage choice is sound and correctly described; only the stated
  necessity was false. Rewrote the comment and the PR body around the real
  reason. No behaviour change.
- Independently confirmed the integrity-critical claim: nothing is stubbed,
  mocked, faked or vendored for the canonical tuple. `src/policyengine/`
  contains no `ModuleType` or `sys.modules[...]` assignment at all, and the one
  `types.ModuleType('policyengine_us.spm')` in the tree is an adversarial test
  that plants a foreign module and asserts the loader rejects it.

## Next

Not this lane's work, recorded for the coordinator:

- Publish `policyengine-us 2.0.0` (and then wrapper 6.0.0), or make the US SPM
  path conditional on canonical availability — the `spm=` Simulation keyword as
  well as the adapter import. Until then the four `Test` jobs stay red.
- Data certification, the producer's immutable source-enrichment release, and
  population/API acceptance remain separate gates. The five historical US
  snapshot differences under country 1.824.7, including January-only annual
  SNAP, remain a country-owner investigation.
