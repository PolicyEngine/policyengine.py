# Canonical SPM wrapper release PR

## State

Turning the canonical SPM wrapper worktree
(`max/spm-canonical-wrapper-release-20260910`, base `6a56ced4` = `origin/main`)
into a reviewable draft PR against `main` with hosted CI.

Verified at start: `git rev-parse origin/main` = `6a56ced4f959ce9a1f3b794389a4b42699de8abc`
= local HEAD. `git ls-remote origin refs/heads/max/spm-canonical-wrapper-release-20260910`
is empty, so the branch does not yet exist on origin.

## Done

- Read background: production checkout handoff/output/progress/native-loader
  reports and `rollout/wrapper-loader-candidate/FINAL-REPORT.md`.
- Step 1 file-set comparison. release-final carries 72 changed/untracked paths;
  production carries 70. Release-final adds exactly six: the TRO schema fix
  (`src/policyengine/data/schemas/trace_tro.schema.json`, regenerated
  `uk`/`us.trace.tro.jsonld`, `tests/test_generate_trace_tros.py`,
  `changelog.d/repository-tro-schema.fixed.md`) plus a regenerated `uv.lock`.
  Production holds only four extra paths, all working reports that must not be
  committed. 55 of the 66 common paths are byte-identical; 11 differ.
- Verified the TRO sidecars rebind to the working-tree manifest hash
  `d430b8e561d76e5836a17bf506b06b9cd16560eb77f15718dd46f4e78513de85`.
- Step 2 safety audit: all 36 untracked paths are text, 195 KB total. No wheels,
  venv, `__pycache__`, `.h5` or binaries; no secret-shaped strings; no
  `/Users/...` paths. Every `/tmp/...` occurrence is a runbook example or a
  rejection sentinel in a test, never a default in committed logic.
- Step 4 local checks (see the report for exit codes). Green: ruff format, ruff
  check, `uv pip check`, `scripts/bundle.py check`, `scripts/release_lock.py`,
  `policyengine bundle verify`, the Python-Compat smoke import.
- `make test` FAILS: 39 failed, 1005 passed, 14 skipped, exit 1. All 39 share
  one cause: `ModuleNotFoundError: No module named
  'spm_calculator.policyengine_adapter'`, from the new lazy validation imports
  in `us/model.py` and `us/household.py`.
- Established why no pin bump fixes that. `spm-calculator 1.0.0` reached PyPI
  today (2026-09-11T15:45:10Z), but `policyengine-us 2.0.0` has not (latest
  1.825.0). Probed in a throwaway venv: with calculator 1.0.0, country model
  1.764.6 cannot even load its variables (`spm_unit_geographic_adjustment`
  imports `spm_calculator.geoadj`, removed in 1.0.0). So the canonical tuple
  needs policyengine-us 2.0.0, which is unpublished.

## Next

- Step 3: logical commits with the Fable 5.1 co-author trailer.
- Step 5: push branch. Step 6: draft PR. Step 7: watch CI and report.
