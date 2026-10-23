# Local manifest fallback handoff

- Draft PR: https://github.com/PolicyEngine/policyengine.py/pull/704
- Issue: https://github.com/PolicyEngine/policyengine.py/issues/703
- Branch: `budget-local-data-manifest`, based on `origin/main` `485dc23302ec4abc6a5f7df5c6c03b8525f64c4d`.
- Reviewed implementation head: `78e09ed63c3805b8739bc9ea229a0d393c213e46` (this handoff is committed immediately afterwards).
- Commits: `0bb58755` local manifest/certification/tests; `78e09ed6` receipt/schema/docs/tests.

## Design

`POLICYENGINE_<COUNTRY>_DATA_MANIFEST_FILE` always selects the local file when present. This avoids outage latency and gives deterministic behavior. Unset keeps the original cached network fetch and certification results.

The pin is the raw-byte `trov:sha256` for `composition/1/artifact/data_release_manifest` in the installed country TRACE TRO. Its arrangement must name the installed release's manifest URI. Missing, malformed, duplicate, or stale pins refuse. The current installed UK pin was checked as `49f9fa820db2e6544ff5cdceeb2d868a504843a6a1c1c06b37188621e700066f`. No environment digest is accepted. Local bytes are re-read and hashed on every call, before JSON parsing/revision rewriting, so cached remote/local loads cannot bypass verification. Invalid paths and digest errors fail closed with digest context.

Local bytes run through the unchanged certification acceptance logic. All four successful runtime bases gain `_local_manifest`; the claim-based set includes the corresponding local variants. Exact-pair model/core/build restrictions and fingerprint acceptance remain the same. TRACE accepts the basis as a string. Packaged receipts recheck local certification and record it in optional `runtime.data_certification_basis`, keeping the published bundle certificate basis and both digest domains unchanged. Unset receipts omit the new annotation. The schema is regenerated and checked. Caller-supplied bundles do not claim packaged provenance.

## Validation

- 38 local-manifest tests passed, including 80 Hypothesis byte mutations and 10 direct main-snapshot differential scenarios.
- 146 existing certification tests passed.
- 96 bundle/bootstrap/tooling tests passed.
- Broad provenance suite: 2,337 passed, 6 skipped, including all 6 new receipt tests.
- Wheel/package-pin tests: 96 passed.
- Total across these final focused runs: **2,713 passed, 6 skipped**. Skips cover private data, Python/model-version-specific cases, and disabled top-level country imports in the broad run.
- `make format`, `make lint`, `git diff --check`, and `scripts/generate_receipt_schemas.py --check` passed.
- Every pytest invocation checked load1 <=110 and `os.statvfs` available bytes >=55,000,000,000. Observed load was below 37 and free disk above 132 GB. No pytest workers were used.
- Local fixtures are synthetic; no private manifest or microdata is committed.

Detailed parent-run logs are local files under `.job/*tests.log`.

## Coordination and remaining work

- Leave PR draft; the hub reviews and merges it.
- Ship in the same policyengine.py release as María's weekend Microcosm cut certification. No versions or country/data pins were changed. `changelog.d/703.added.md` follows the release workflow.
- The G0 morning fetch/verify/atomic-refresh instructions are in `docs/bundles.md`. Refresh the local manifest after adopting the newly certified release.
- Dashboard follow-up: refresh `tests/fixtures/w4/execution_receipt.v1.schema.json` in `PolicyEngine/uk-autumn-budget-dashboard-2026` when upgrading; its receipt adapter has no basis allowlist, but its schema equality test requires the new schema. See `docs/receipts.md`.

## Workspace Git metadata

The assigned worktree's protected `.git` points into the caller's repository, where metadata writes are sandbox-blocked. All work and independent Git metadata stayed in this workspace. To inspect the actual branch here:

```bash
GIT_DIR="$PWD/.job/git-copy/.git" GIT_WORK_TREE="$PWD" git status
GIT_DIR="$PWD/.job/git-copy/.git" GIT_WORK_TREE="$PWD" git log -3 --oneline
```

The branch is pushed to the canonical repository. A portable `.job/local-data-manifest.bundle` is also left for harvesting; it contains `budget-local-data-manifest` relative to the main base. The original protected `.git` pointer was not changed. No caller files were written.
