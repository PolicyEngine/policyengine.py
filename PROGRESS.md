# Behavior input boundary progress

## State

- Branch: `feat/be-behavior-input-contract`
- Starting base: `3c3b4f6442f4a5adc47274734d71a6ca10103b43`
- Local `origin/main` at start: `3c3b4f6442f4a5adc47274734d71a6ca10103b43`
- Last fetch attempt: 2026-08-31; blocked because the execution environment
  cannot resolve `github.com`.
- Live comparison: GitHub's repository page shows a newer `main` history than
  the 1,161 commits available in local `origin/main`. Publication and final
  base selection remain gated on fetching the actual upstream Git objects.
- The local `main` ref is unrelated divergent work and is not a safe upstream
  substitute.
- Scope: data-only behavior input configuration and ID-keyed resolution; no
  simulation or country-computation integration.

## Done

- Verified the worktree was clean and the requested branch, base, local
  `origin/main`, and merge-base matched exactly.
- Read all repository instruction files, the relevant engineering skills, and
  the complete defensive correctness audit.
- Completed read-only review of `YearData`, Pydantic, pandas, tests,
  documentation, changelog, and package conventions.
- Added the focused behavior-input tests first. The isolated test run is red at
  collection because the not-yet-implemented public models are absent, as
  expected. The normal `uv run` environment could not be created offline, so
  the red run used the available Python environment with repository conftests
  disabled; full validation remains pending.
- Resumed from the TDD commit and inspected the dirty implementation, salvage
  ref `refs/codex-salvage/feat-be-behavior-input-contract-20260830-212607-7535`,
  complete architecture audit, and all repository instruction files. The dirty
  implementation is byte-identical to the salvage snapshot.
- Confirmed the requested boundary has no dependency on `Simulation.run()`, a
  legal-variable registry, positional entity mapping, or source runtimes.
- Added the frozen, extra-forbidding `BehaviorInputBinding` and `BehaviorInputs`
  models, exported only those configuration models from `policyengine.core`,
  and kept the pure resolver internal.
- The resolver requires non-null unique stable entity IDs, returns copied
  ID-indexed series, preserves nullable values, and does not mutate source
  tables or remap entities.
- Focused diagnostic validation passes all 17 contract tests under the available
  Python 3.14 environment. Direct Ruff format/check and `git diff --check` pass
  for the implementation slice. The canonical `uv run` remains blocked because
  the sandbox cannot write the configured user cache; canonical validation is
  still pending.
- Hardened the source-aliasing test against MicroDataFrame scalar-setter
  differences across pandas/microdf versions and corrected the Ruff import
  grouping. The 17 focused tests and direct Ruff checks remain green.

## Next

- Add ownership/vocabulary documentation and a Towncrier fragment.
- Run focused and proportional regression checks, self-review, and attempt the
  required same-repository draft PR workflow only after current upstream Git
  objects can be fetched and reconciled.
