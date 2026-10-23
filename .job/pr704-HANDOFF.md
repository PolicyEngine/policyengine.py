# PR #704 review-fix handoff

- Draft PR: https://github.com/PolicyEngine/policyengine.py/pull/704
- Branch: `budget-local-data-manifest`; confirmed reviewed remote head `fd4e099ed3ff768041f3a537e6e38527c07b0bbf`.
- Validated implementation head SHA: `0d7bf1a641d61b8951f47ab12d8d4867f57df140`.
- The following commit updates only this handoff. Its exact final head is recorded in `.job/HEAD` and `.job/local-data-manifest.bundle`.

## Fixes

- Scan every TRO definition of the manifest artifact ID, including direct graph nodes, nested definitions and artifact references; require one distinct valid SHA-256 assertion. Preserve canonical inline/location checks.
- Validate both local and fetched manifest artifacts after revision rewriting. The certified/default artifact must be present and anchored; every overlapping managed artifact must agree with bundled repo/path/revision, repository type and pinned SHA-256. Compare identity fields separately to prevent ambiguous URI concatenation. Primary manifests may omit separately pinned regional artifacts and overlays.
- Share the existing release-relative diagnostics/evidence normalization with certification. Exact-pair model/core/build and fingerprint acceptance logic remains unchanged; unset fetch/cache/offline behavior is preserved for consistent bundles.
- Replace function attributes with a typed callable cache facade.
- Make the documented export conditional on successful download/verification/atomic replacement; remove release coordination from permanent public docs.
- PR body records the invariants and both downstream actions. No other repository was edited.

## Validation

**3,322 unique cases passed; five skipped.**

- Initial local/TRO-pin run: 88 passed, including two 80-example Hypothesis properties (byte mutation and duplicate placement).
- Broad 56-module provenance/certification/disclosure run: 3,256 passed, five skipped, one failure from the old missing-default error-message assertion. It now refuses earlier in the shared validator; the corrected complete TRO regeneration module passed all 40 cases on rerun.
- Release/bootstrap-focused run: 189 passed, including 59 cases outside the broad selection and two new default-anchor cases.
- Final affected manifest/certification run: 280 passed, including all 82 local-manifest cases, all 12 TRO-pin cases and four new repo/path-boundary cases. No failures remain in pytest's failure cache.
- `make format`, `make lint`, focused `mypy --follow-imports=silent src/policyengine/provenance/manifest.py`, `git diff --check`, and generated receipt schema checks passed. Documentation shell block passes `bash -n`.
- Every pytest invocation checked load1 <=110 and available disk >=55,000,000,000 bytes; no pytest workers. Observed load1 9.04–19.02; available disk 144.3–146.9 GB decimal. Tests used Python 3.13.9.
- Detailed logs and selected modules remain under `.job/`. No private manifests or microdata were committed.

## Downstream actions

- Dashboard: refresh vendored `tests/fixtures/w4/execution_receipt.v1.schema.json` when upgrading.
- Scorecard: `pipeline/uk_replay_variants.py:730` retains the setting in offline isolation, while `:750` requires exact runtime bundle equality. Clear `POLICYENGINE_*_DATA_MANIFEST_FILE` during isolation.
- Leave the PR draft; do not merge. No versions, country pins, data or certified releases changed.

## Workspace Git metadata and delivery

The protected workspace `.git` points into the caller's repository. All mutable Git metadata is instead inside this workspace:

```bash
GIT_DIR="$PWD/.job/git-copy/.git" GIT_WORK_TREE="$PWD" git status
GIT_DIR="$PWD/.job/git-copy/.git" GIT_WORK_TREE="$PWD" git log -4 --oneline
```

The original pointer and caller checkout were not changed. `.job/local-data-manifest.bundle` is portable relative to main `485dc23302ec4abc6a5f7df5c6c03b8525f64c4d`. The single final push is attempted after committing this handoff; its outcome is recorded in `.job/PUSH_RESULT.txt`. `.job/HEAD` contains the final branch SHA. No history was rewritten and nothing was pushed to main or master.
