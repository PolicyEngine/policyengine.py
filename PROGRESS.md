# Canonical SPM wrapper release PR

## State

**Complete.** Draft PR https://github.com/PolicyEngine/policyengine.py/pull/515
is open against `main` from `max/spm-canonical-wrapper-release-20260910`, with
eight commits and hosted CI run. #512 is left open and untouched, referenced as
superseded.

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

## Next

Not this lane's work, recorded for the coordinator:

- Publish `policyengine-us 2.0.0` (and then wrapper 6.0.0), or make the US SPM
  path conditional on canonical availability — the `spm=` Simulation keyword as
  well as the adapter import. Until then the four `Test` jobs stay red.
- Data certification, the producer's immutable source-enrichment release, and
  population/API acceptance remain separate gates. The five historical US
  snapshot differences under country 1.824.7, including January-only annual
  SNAP, remain a country-owner investigation.
