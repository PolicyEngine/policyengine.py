# Behavior input boundary progress

## State

- Branch: `feat/be-behavior-input-contract`
- Starting base: `3c3b4f6442f4a5adc47274734d71a6ca10103b43`
- Local `origin/main` at start: `3c3b4f6442f4a5adc47274734d71a6ca10103b43`
- Scope: data-only behavior input configuration and ID-keyed resolution; no
  simulation or country-computation integration.
- Upstream refresh: attempted on 2026-08-30, but GitHub DNS resolution is
  unavailable in the execution environment.

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

## Next

- Implement the minimal frozen Pydantic models and pure resolver.
- Add ownership/vocabulary documentation and a Towncrier fragment.
- Run focused and proportional regression checks, self-review, and attempt the
  required same-repository draft PR workflow.
