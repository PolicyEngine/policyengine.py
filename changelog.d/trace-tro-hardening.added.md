TRACE TRO hardening: bundle TROs now hash the country model wheel (read from
`PackageVersion.sha256` when present, otherwise fetched from PyPI), use HTTPS
artifact locations, carry structured `pe:*` certification fields and GitHub
Actions attestation metadata, and are validated in CI against a shipped JSON
Schema. Adds a `policyengine trace-tro` CLI, per-simulation TROs through
`policyengine.results.build_results_trace_tro` / `write_results_with_trace_tro`,
and restores the `TaxBenefitModelVersion.trace_tro` property and
`policyengine.core` re-exports that were dropped in #276.
