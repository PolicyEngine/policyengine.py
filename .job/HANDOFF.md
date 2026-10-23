# PR #699 owner findings — Budget Monday re-cut

- Confirmed GitHub head before editing: `aa59b0d704852eab63087d8146f7da667d2178e0`, branch `accept-regional-model-mismatch`, canonical repository, draft PR.
- Implementation head SHA: `878392cf5a42d7b4916ae7b311c84aa30d383d38`. This handoff is a separate report-only commit; its final delivery SHA is saved in `.job/HEAD`.

Changes:

1. Refuse any explicitly different regional `built_with_model_package.name` before checking publisher claims or accepting a version mismatch. Missing build metadata retains its previous behavior. Four regression cases cover `policyengine-us` and another package, with audited mismatch acceptance or a UK compatibility claim; each checks that refusal leaves the bundle unchanged.
2. Forward `--accept-regional-model-mismatch` whenever the value `is not None`. One regression follows the real wrapper and certifier CLI into certification, confirms the empty string is forwarded and refused, and checks that the bundle is unchanged.
3. Document silent unknown-column skipping in both the certification skill and input-audit module docstring. Inspected policyengine-uk 2.147.2, immutable commit `fe0b99a36bd309a722b19937345e34290cb6dd73`: [`build_from_dataset`, lines 1116–1117](https://github.com/PolicyEngine/policyengine-uk/blob/fe0b99a36bd309a722b19937345e34290cb6dd73/policyengine_uk/simulation.py#L1113-L1127) and [`build_from_multi_year_dataset`, lines 1194–1195](https://github.com/PolicyEngine/policyengine-uk/blob/fe0b99a36bd309a722b19937345e34290cb6dd73/policyengine_uk/simulation.py#L1186-L1196) use `continue` without warning. The old core-warning claim was already absent from the approved head; the documentation now states the actual UK behavior explicitly.

Validation:

- `python3 ~/reviews/fleet-ops/tools/reservation.py allowed uk-hub` refused: `held back by route-a-release-rerun-d1811-2026-10-23 (reservation.py status)`.
- **0 pytest cases executed; 0 passed, 0 failed. Five new regression cases await CI.** No collection, full suite, country-model run, or audit was launched. Rely on CI as requested. Focused follow-up, once permitted: `pytest tests/test_certify_data_release.py tests/test_regional_input_evidence.py -n 2`.
- Ruff lint and formatting checks passed for all five changed Python files: the bundle wrapper, certification, input audit, and both test modules. `git diff --check` passed.
- Independent source/diff review found no blockers. No data release was certified.

Delivery:

- All writes stay in this assigned workspace; mutable Git metadata is isolated in `.job/repo.git`. Run `source .job/env` before Git commands here. The protected `.git` still points to the caller's read-only metadata.
- Two added commits: the fixes above and this report. No history rewrite. The final SHA is in `.job/HEAD`; portable new commits are in `.job/budget-fix-699-r3.bundle`.
- One normal push to `origin HEAD:accept-regional-model-mismatch` is attempted after the report commit. Its outcome is saved in `.job/PUSH_RESULT.txt` and reported to the caller. No push to main/master. Leave #699 draft.
