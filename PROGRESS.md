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
| HF tag `populace-us-2024-spm-20260915` exists and is readable | Yes. `build.built_with_model_package` = policyengine-us **2.2.1**, `build.build_id` = `populace-us-2024-spm-20260915`, H5 sha256 `6496cc4393d4d3c6574f76eca231de5898c803b9067645591fd5c4d3e65aee84`. |
| Release carries a publisher compatibility range | Yes. `policyengine-us >=2.0.0,<2.3`, basis `publisher_claim`. Not the basis used — see below. |
| microcosm main contains PR #928 | Yes. Merged 2026-09-15T06:34:17Z, merge commit `743683b0e121378e93c9b426cd9c79d41d29595b`. |
| Branch head unmoved | Yes, `origin/max/spm-canonical-wrapper-release-20260910` = `1b6c001c`. |

## Sequence actually run (corrected from the brief)

The brief's order and two of its flags do not exist or cannot succeed. Verified
against the code, not assumed:

1. **`--data-producer populace` is required for the US.** `certification.py:753`
   defaults a missing producer to `legacy` for every country except UK, and the
   legacy strategy raises unconditionally.
2. **`scripts/release_lock.py --committed` does not exist.** The script has
   exactly one flag, `--refresh` (`release_lock.py:184`).
3. **`--refresh` cannot perform a repin.** It permits only the root package
   version to move and restores the lock on any graph change
   (`release_lock.py:169-179`). Run as instructed it failed with "Versioning
   changed the reviewed dependency graph" and left `uv.lock` byte-identical.
   The repin needs an ordinary registry-only `uv lock`, then plain
   `release_lock.py` — which is what PR CI runs
   (`pr_code_changes.yaml:120`) and what `docs/release-bundles.md:50-56`
   prescribes.
4. **`generate --include-tros --strict-tros` cannot prepare a sidecar for a
   changed data release.** Strict generation refuses to substitute remote bytes
   over the reviewed pin in the committed TRO
   (`generate_trace_tros.py:114-121`), and separately requires the lock to
   already carry the certified model (`:143-164`). Preparation is the
   non-strict `generate --include-tros`; `check … --strict-tros` is the gate.

Working order: certify → `uv lock` → `release_lock.py` → `generate
--include-tros` → `check --published-spm --include-tros --strict-tros`.

## Done

- [x] Prerequisites verified against primary sources.
- [x] Re-certified: basis **`built_with_model_package`**, zero warnings, because
      the release's build-time model equals the certified version.
- [x] Generated pins: `models`, `us`, `dev` extras at `policyengine-us==2.2.1`;
      `spm-calculator==1.0.0` kept, inside 2.2.1's `>=1.0.0,<=1.0.0.post1`.
- [x] Lock resolved to 2.2.1 from PyPI with the certified wheel hash;
      `release_lock.py` exits 0 with one root package at 5.3.1.
- [x] TRACE sidecars regenerated; `bundle.py check --published-spm
      --include-tros --strict-tros` exits 0.
- [x] Restored `tests/test_spm_household.py` from `818c894e`
      (sha256 `061cbc1b…`): 42 passed against the repinned environment.
- [x] Updated the identity-fact pins in four test modules.
- [x] Corrected two shipped mechanism claims that 2.2.1 falsifies (the public
      `calculate_household` docstring and `docs/households.md`), plus two
      unreleased changelog fragments that stated the superseded contract and pin.
- [x] Dropped the superseded `certify-us-…20260909` fragment.
- [x] Lint/format clean under the ruff CI installs (0.16.7).

## Review round

An adversarial review of the pushed diff raised 29 findings across six dimensions;
28 were refuted as pre-existing, out of scope, or wrong. Two things were changed
as a result, both verified against the installed 2.2.1 model rather than taken on
the reviewer's word:

- **The fail-closed set is five variables, not three.** Probing the pinned model
  directly (assisted unit, state only, default outputs narrowed the way the
  acceptance test narrows them) shows `spm_unit_capped_housing_subsidy`,
  `spm_unit_benefits`, `spm_unit_net_income`, `spm_unit_oecd_equiv_net_income`
  and `spm_unit_income_decile` all raise `SPM_GEOGRAPHY_REQUIRED`; the last two
  are downstream of `spm_unit_net_income`. The corrected prose now names the
  whole chain instead of reading as an exhaustive list of three. The same probe
  confirms every ordinary resource output, and `housing_assistance` itself,
  computes on state alone for the assisted unit.
- **`docs/bundles.md` still said the manifest pins `spm-calculator==0.3.1`.**
  True on `main`, false on this branch since the canonical-tuple commit. Corrected
  to 1.0.0; the separate historical note about reproducing the published 5.3.0
  package set with 0.3.1 is still accurate and is left alone.

The certification dimension came back clean under independent verification: all ten
artifacts match the live release's bytes by sha256, the manifest carries no
remaining `20260909` or `2.0.0` string, and the model wheel hash matches PyPI.

## Next

- [ ] Push to `origin/max/spm-canonical-wrapper-release-20260910`, watch CI on #515,
      update the PR body. Do not mark ready, do not merge.

The version in `pyproject.toml` is untouched: `bump_version.py` derives 6.0.0
from the two `.breaking.md` fragments at release time.
