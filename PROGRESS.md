# Progress: wrapper release candidates (max/wrapper-release-candidates-20260914)

## State
Branch stacked on the approved #515 head `1b6c001c`. Base commit `818c894e`
("Build and verify isolated wrapper release candidates") is Codex's
release-candidate tooling; it carries two real defects plus an unverified
household-test rewrite. This branch keeps the tooling and fixes the defects.

## Done
- Verified worktree at `818c894e`, clean tree.

## Next
1. Commit 1: revert `tests/test_spm_household.py` to the `1b6c001c` version.
2. Commit 2: fix `tests/test_spm_bundle_bootstrap.py` publication-gate assertion.
3. Commit 3: fix `assert_source_origin` namespace-package handling + extractor
   sys.modules restoration + regression test.
4. Verify: targeted pytest, full pytest, lint/format. Record exit codes.
5. Push and open a DRAFT PR against `max/spm-canonical-wrapper-release-20260910`.
