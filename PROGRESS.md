# Repin wrapper PR #515 to policyengine-us 2.2.1 and populace-us-2024-spm-20260915

Lane: `wrapper-repin-600`. Worktree
`/Users/maxghenis/spm-rebuild-20260908/worktrees/policyengine-wrapper-repin-600`,
branched from origin head `1b6c001c860305d529e91d6f452f3359e29439fa` (PR #515,
`max/spm-canonical-wrapper-release-20260910`). Goal: main can publish
policyengine 6.0.0 on a country pin and a certified data release that agree.

## Prerequisites (verified this lane, primary sources, 2026-09-15)

| Prerequisite | Result |
|---|---|
| PyPI has policyengine-us 2.2.1 | Yes. Wheel sha256 `0993a6c73fcdfbe171a796aca9d302741bd8e00ab83388ad81c15a08740318c6`, uploaded 2026-09-15T04:45:46Z. |
| PyPI latest is 2.3.0 (not the target) | Yes, uploaded 06:11:55Z. Deliberately **not** pinned: the certified claim is `>=2.0.0,<2.3` and 2.2.1 is the built-with version. |
| HF tag `populace-us-2024-spm-20260915` exists and is readable | Yes. Release manifest records `build.built_with_model_package` = policyengine-us **2.2.1**, `build.build_id` = `populace-us-2024-spm-20260915`, H5 sha256 `6496cc4393d4d3c6574f76eca231de5898c803b9067645591fd5c4d3e65aee84`. |
| Release carries a publisher compatibility range | Yes. `compatible_model_packages` = `policyengine-us >=2.0.0,<2.3`, basis `publisher_claim`. |
| microcosm main contains PR #928 | Yes. Merged 2026-09-15T06:34:17Z, merge commit `743683b0e121378e93c9b426cd9c79d41d29595b`. |
| Branch head unmoved | Yes, `origin/max/spm-canonical-wrapper-release-20260910` = `1b6c001c`. |

## Baseline at `1b6c001c`

- `pyproject.toml` pins `policyengine-us==2.0.0` in the `models`, `us` and `dev` extras;
  `policyengine-core==3.32.5`, `spm-calculator==1.0.0`, `policyengine-uk==2.90.2`.
- `src/policyengine/data/bundle/manifest.json` → `data_releases.us` certifies build
  `populace-us-2024-spm-20260909` for model version `2.0.0`, basis
  `built_with_model_package`.
- The H5 sha256 is byte-identical across the 20260909 and 20260915 releases
  (`6496cc43…aee84`); the release-directory evidence files differ.

## Plan

1. Re-certify: `scripts/certify_data_release.py` against the 20260915 release manifest at
   model version 2.2.1.
2. Regenerate bundle artifacts: `scripts/bundle.py generate --include-tros --strict-tros`.
   The pyproject pins are **generated** from `manifest.json`; they are never hand-edited.
   `provenance/pyproject_pins.py::update_country_pins` is not used (it misses the `models`
   extra).
3. Refresh the lock: `scripts/release_lock.py --refresh`, then `--committed`.
4. Restore the `tests/test_spm_household.py` rewrite from `818c894e` (the version that
   needs the new country semantics) and run it against the repinned environment.
5. Full verification: pytest, lint/format, `scripts/bundle.py check --published-spm
   --include-tros --strict-tros`.
6. Commit in four steps, push, watch CI on #515, update the PR body. **Do not merge.**

The version in `pyproject.toml` is not touched: `bump_version.py` derives 6.0.0 from the
two `.breaking.md` fragments at release time.

## Done

- [x] Prerequisites verified against primary sources.
- [x] Worktree created at the pinned head.

## Next

- [ ] Map the certify/generate/lock machinery from the code before running it.
- [ ] Step 1: re-certify.
