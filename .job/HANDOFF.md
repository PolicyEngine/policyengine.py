# PR #699 Budget review fix

- Confirmed origin heads: #699 `afee349d2c14de1b121b0b7e4f03b695d03f418c`; #704 `da2ae8fb8e97145093e35366686df99c1e38449e`.
- Merged #704 into `accept-regional-model-mismatch` with merge commit `c1a65198`. No history rewritten. Release order remains main → #704 → #699 → certification.
- Implementation validated through `b90eada3`; the final report commit is recorded in `.job/HEAD`.

Changes:

- Require typed audited evidence bound to the exact regional cut URI, original manifest digest, every regional H5 identity/hash, and exact target model. Recompute the surface comparison and refuse every dropped column. Record every defaulted input by inspecting all stored periods and the country loader's aliases.
- Port Microcosm #1348's comparison, strengthening its older-model proxy to measure actual byte-verified H5 columns. New producer: `scripts/audit_regional_input_surface.py`. The CLI works before the current bundle certifies its target model. Microcosm handoff callers must generate and forward the new evidence JSON.
- Preserve the regional manifest's raw-byte digest. Keep limitations, including the pre-2.135.7 VAT fix/dashboard limit, through Pydantic validation and bundle hashing.
- Expose the full regional record in receipts and TRACE (`@json` preserves JSON-LD semantics). Area receipts stay uncertified and identify their dense build model. National certification never widens. Explicit reversal removes the record, digest, area routes and dense artifact; the national certificate stays identical.
- Regenerate the receipt schema. Dashboard follow-up: refresh vendored `tests/fixtures/w4/execution_receipt.v1.schema.json`.

Validation:

- Tests first demonstrated missing-evidence acceptance, stale evidence/dropped-column failures, missing receipt/TRACE records, lost JSON-LD semantics, and premature audit CLI model initialization.
- **1,248 selected cases passed; two skipped**, across the UK run and successful reruns of three US metadata cases in the environment with the bundled US pin installed. The UK run initially reported 1,245 passes plus those three missing-package failures; all three reruns passed. One unrelated US offline-import integration case was explicitly deselected.
- Covered all changed provenance/certification modules, the existing roundtrip, required reversal cases, and #704's three local-manifest modules. Logs: `.job/logs/uk-final.txt`, `.job/logs/us-metadata-rerun.txt`.
- Expanded 53-module validation reported 3,008 passes and five skips with no failures before stalling for over nine minutes; it was interrupted and is not claimed complete. A subsequent wider pinned-environment attempt was also interrupted during slow package inspection. Initial setup problems (missing packages, inherited Git variables and an unpinned model) were diagnosed; final test subprocesses clear Git overrides. No interrupted test processes remain.
- `make format`, `make lint`, receipt schema generation/equality, `bundle.py check`, and diff checks pass.
- Mypy on all changed source modules: 24 diagnostics, identical to the merged baseline ignoring moved line numbers. Both new source modules have zero errors. Comparison: `.job/logs/mypy-comparison.txt`.
- Every pytest launch checked load1 ≤110 and free disk ≥55,000,000,000 bytes. At most two workers per invocation. Final launches: load1 75.71 / 97.69; available disk 103.7 GB decimal.

Actual Budget pair:

- National `microcosm-uk-2024-25-national-20261023T075039Z-a133f37a` (2.147.2), dense `microcosm-uk-2024-25-dense-20261019T000432Z-ee5c2dbe` (2.132.6).
- The exact model-inventory comparison has no dropped names and 16 added pure inputs, including both `salary_sacrifice_returned_to_income` and `local_bus_uncapped_single_fare`; the complete list is in certification guidance.
- The private dense H5 was unavailable (no HF credential; HTTP 401). This inventory is not a byte audit, and this job does not certify the actual pair. The certification follow-up must run the new audit against the real H5 and record its complete default list.

Delivery:

- All writes stayed in the assigned workspace. The protected `.git` points into the caller's checkout; mutable Git metadata is isolated in `.job/repo.git`. Use `source .job/env` before Git commands here. The caller checkout was not written.
- Portable commits: `.job/budget-fix-699.bundle`; final head: `.job/HEAD`. The single push attempt's output is saved in `.job/PUSH_RESULT.txt`. No main/master push; leave #699 draft.
- GitHub blocked the PR body update because the connector requires approval and approval policy is `never`. The replacement body, including the invariants, is saved in `.job/PR_BODY.md`; no PR metadata change was made.
