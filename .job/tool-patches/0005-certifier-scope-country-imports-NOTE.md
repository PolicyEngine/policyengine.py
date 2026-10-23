For microcosm #1348's owner: fifth local-only rehearsal patch; apply after 0001–0004. No heavy execution or external action was run for this patch.

The live certified-constant rewrite spent minutes importing `policyengine.provenance.uk_qualification`: importing any policyengine submodule first runs policyengine/__init__.py, which eagerly initializes both installed country modules. The constant replacement/rewrite helpers themselves operate only on record JSON, string literals and files. The repository already exposes POLICYENGINE_SKIP_COUNTRY_IMPORTS=1 for provenance-only imports. This patch applies that environment variable to the constant-rewrite subprocess only.

The UC-floor subprocess receives the same scoped variable to avoid the wrapper's eager country imports. Its actual UK calculation remains intact: uk_uc_floor.check_uc_floor directly imports policyengine_uk.Microsimulation and computes the weighted national UC totals. No floor criterion, receipt check or acceptance requirement changes. Snapshots and the full test suite receive no skip flag.

Validation: 17 lightweight offline stdlib unittest regressions passed in 0.329 seconds. The new regression asserts that exactly constant-rewrite and UC-floor receive the flag, while snapshot update and full tests preserve their environments. Ruff check and Ruff format --check passed. The current live process loaded earlier code, so this patch does not claim to measure an optimized rewrite.

The optional command-display shortening was left out to keep this patch focused on measured import overhead; full commands remain in the handoff receipts.
