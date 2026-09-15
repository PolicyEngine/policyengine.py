# Progress: wrapper release candidates (max/wrapper-release-candidates-20260914)

## State
Branch stacked on the approved #515 head `1b6c001c`. Base commit `818c894e`
("Build and verify isolated wrapper release candidates") is Codex's
release-candidate tooling; it carries two real defects plus a household-test
rewrite the R1-R3 reviews passed through unverified. This branch keeps the
tooling and fixes all three. It cannot stand on `main`: it depends on #515's
`release_lock.py`, `check_release_credentials.py`, `spm_bundle.py`, the
`--published-spm` flag and the TRACE `repository-bundle` schema enum.

## Done
- Verified the worktree at `818c894e`, clean tree.
- Reproduced both defects against the locked environment (`uv sync --frozen`,
  Python 3.14.4): baseline `pytest tests/test_release_build.py
  tests/test_spm_bundle_bootstrap.py tests/test_graph -q` gave 2 failed,
  98 passed.
- Established defect B's trigger with an instrumented probe over three import
  phases rather than assuming it. Bare `import policyengine`: 0 offenders.
  After `tests/conftest.py`: exactly one, the namespace package
  `policyengine.tax_benefit_models` (`__file__` None, `__path__` inside the
  checkout). After `tests/test_graph/test_extractor.py`: two more, the bare
  stand-ins it installs for `policyengine` and `policyengine.graph`. The
  conftest one is why the test failed even when run alone.
- Commit 1 `35981756`: restored `tests/test_spm_household.py` to its
  `1b6c001c` content (byte-identical, sha256 `fe6df0c7...`).
- Commit 2 `14e5db47`: the bootstrap publication-gate assertion now follows
  `release_build.py publish-check`.
- Commit 3 `abf75454`: `module_origin` places namespace packages by `__path__`;
  the extractor restores `sys.modules`; three regression cases added.
- Mutation-checked the new tests. Pre-fix logic fails the acceptance case;
  accepting any file-less module fails all three refusals.
- Targeted suite after the fixes: 104 passed, exit 0.
- `ruff format --check .`: exit 0. `ruff check .`: 11 UP038 findings, all
  pre-existing at `818c894e` and none in a file this branch touches; the
  files this branch touches pass clean.

## Next
1. Full `uv run --no-sync pytest tests -q`; record counts and exit code.
2. Push and open a DRAFT PR against `max/spm-canonical-wrapper-release-20260910`.
