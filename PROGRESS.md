# Behavior input boundary progress

## State

- Branch: `feat/be-behavior-input-contract`
- Starting base: `3c3b4f6442f4a5adc47274734d71a6ca10103b43`
- Local `origin/main` at start: `3c3b4f6442f4a5adc47274734d71a6ca10103b43`
- Live `origin/main` was fetched on 2026-08-31 and remains exactly
  `3c3b4f6442f4a5adc47274734d71a6ca10103b43`.
- Live comparison: this worktree's common repository is shallow and therefore
  counts 1,161 commits at `origin/main`. An independent non-shallow clone has
  the same `origin/main` SHA with 1,168 commits, matching GitHub's live history
  count. The apparent seven-commit difference was shallow history, not an
  upstream advance; the exact comparison base remains
  `3c3b4f6442f4a5adc47274734d71a6ca10103b43`.
- The local `main` ref is unrelated divergent work and is not a safe upstream
  substitute.
- Scope: data-only behavior input configuration and ID-keyed resolution; no
  simulation or country-computation integration.
- Frozen-review status: implementation-ready. The code, tests, documentation,
  type check, Ruff, and diff checks are green; issue #510 and its Towncrier
  fragment now bind the change. Draft publication and independent frozen-head
  review remain.

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
  disabled; later green validation is recorded below.
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
  for the implementation slice. A syncing `uv run` remains blocked because the
  sandbox cannot write the configured user cache; later validation therefore
  uses `uv run --no-sync` with an existing development environment.
- Hardened the source-aliasing test against MicroDataFrame scalar-setter
  differences across pandas/microdf versions and corrected the Ruff import
  grouping. The 17 focused tests and direct Ruff checks remain green.
- Documented cross-system ownership, legal/behavioral vocabulary, the
  stable-ID resolution contract, and the explicit execution non-goals in the
  model architecture guide.
- Stronger validation through `uv run --no-sync` and the canonical clone's
  existing development environment is green: 17 focused behavior tests; 36
  Belgium/labor-supply tests with 4 expected source-stack skips; and 73
  dataset, model, and extra-variable regression tests.
- Whole-repository Ruff format-check and lint pass (`197 files already
  formatted`; no lint findings), and both working-tree and branch diffs pass
  `git diff --check`.
- The architecture Markdown parses successfully through Quarto's Pandoc. The
  full `make docs` render is environment-blocked because Quarto attempts to
  open its Sass database in a non-writable user cache, not because of a
  documentation diagnostic.
- GitNexus reported that this worktree was not indexed; its index attempt was
  blocked by the non-writable global registry. The generated untracked index
  artifacts were removed, and impact review used direct source/history instead.
- Final architecture review confirmed the source/API scope is clean and added
  the audit's exact legal-operability, non-inference, and explicit non-goal
  guardrails to the documentation.
- Focused mypy validation passes for `src/policyengine/core/behavior.py`, and a
  runtime API probe reconfirms JSON round-trip, private resolver scope, and no
  top-level `pe.be` export.
- Towncrier comparison was run with an available local installation and fails
  only because no new fragment exists: `No new newsfragments found on this
  branch.` A fragment was not fabricated without the required issue number.
- Independent final reviews found no blocking code or architecture defect and
  assessed implementation risk as low. The previously missing issue-numbered
  Towncrier fragment is now resolved by issue #510.
- Created PolicyEngine/policyengine.py issue #510, added
  `changelog.d/510.added.md`, and re-fetched the live upstream base without a
  branch divergence.

## Next

- Re-run Towncrier, focused tests, Ruff, and diff checks on the issue-bound
  tree.
- Push the same-repository branch, open only a draft PR beginning `Fixes #510`,
  and verify its live base/head/draft state.
- Freeze the published head for independent review; keep the full docs render
  as a disclosed environment-only residual check.
