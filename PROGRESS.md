# Bind the canonical wrapper to published country 2.0.0; prepare the 6.0.0 release commit

## State

**In progress.** Prerequisites all verified; repinning the bundle manifest to the
canonical tuple next. Branch `max/spm-canonical-wrapper-release-20260910`, PR #515
(draft, open, mergeable), starting head `223bce47`, base `origin/main` `6a56ced4`.

## Prerequisites (all verified 2026-09-11)

| Item | Value |
|---|---|
| policyengine-us 2.0.0 on PyPI | HTTP 200; wheel sha256 `4ca187509efc2f7d3ace5035c27de88c744d0f112fdc7da027372f3ae07c540a`, uploaded 2026-09-12T01:11:24Z |
| policyengine-us 2.0.0 deps | `policyengine-core>=3.30.1`, `spm-calculator==1.0.0`, requires-python `<3.15,>=3.11` |
| spm-calculator 1.0.0 on PyPI | HTTP 200; wheel sha256 `e354937a5e1a4045d4966ed594a528d8b02866fabaac9bb5672017004b627305` (matches brief) |
| policyengine-core 3.32.5 on PyPI | HTTP 200; wheel sha256 `9d8c162d5fe5c784ae16c885da3ffbfc39a536add0e111133144d8edd555935f` |
| Core 3.32.5 was the acceptance runtime | `rollout/final-core-matrix-20260911-r2/FINAL-REPORT.md` records Core 3.32.5 `9d8c162d…` — byte-identical to the published wheel. Both gate conditions met. |
| HF tag `populace-us-2024-spm-20260909` | exists on `policyengine/populace-us`; tag commit `9a814a3b3b53c0ecd6e1737b6ec862c31300ef6f` |
| H5 it resolves to | `populace_us_2024.h5` LFS sha256 `6496cc4393d4d3c6574f76eca231de5898c803b9067645591fd5c4d3e65aee84` (matches brief) |
| Certified release manifest | `releases/populace-us-2024-spm-20260909/release_manifest.json`, sha256 `6c39eb1e61afc1629f2abe57032dced9c0750c60e42b9acad812c7b3476a2989` — the local certified file at `rollout/h5-producer-20260911/certified/…` is byte-identical to the Hub-published one |
| PR #515 | draft, open, MERGEABLE, head `223bce47` == local HEAD == origin branch |
| PR #515 CI at dispatch | 9 pass, 4 fail (`Test 3.11/3.12/3.13/3.14`) |

## Mechanism established by reading source (not assumed)

- `pyproject.toml`'s `[project.optional-dependencies]` is **generated** from the bundle
  manifest — `scripts/generate_bundle_artifacts.py:97-143` rewrites the whole block from
  `bundle["extras"]` × `bundle["packages"]`. Pins are therefore edited in
  `src/policyengine/data/bundle/manifest.json`, never by hand in pyproject.
- The wrapper **version** is owned by CI, not by this commit: `.github/workflows/push.yaml:136-137`
  Versioning runs `make changelog` → `.github/bump_version.py`, whose `infer_bump`
  (`bump_version.py:70-88`) returns `major` when any `.breaking.` fragment exists, and
  `bump_version.py:91-98` maps 5.3.1 → 6.0.0. So `pyproject` `version` stays 5.3.1 in this PR.
- `bump_version.sync_bundle_versions` (`:120-147`) also owns the manifest's own
  `bundle_version` / `policyengine_version` / `packages.policyengine.version` /
  per-country `bundle_id`. Those stay 5.3.1 here too.

## Done

- Verified every prerequisite above from the authoritative source (PyPI JSON API, HF Hub
  API, `gh pr view`), not from a prior lane's report.
- Read the release machinery: `scripts/bundle.py`, `generate_bundle_artifacts.py`,
  `prepare_package_bundle_update.py`, `certify_data_release.py`, `spm_bundle.py`,
  `Makefile`, `.github/workflows/push.yaml`, `.github/bump_version.py`.
- Confirmed `changelog.d/` already holds two `.breaking.md` fragments
  (`canonical-spm-python.breaking.md`, `canonical-spm-wrapper.breaking.md`), so the
  automatic bump is already major.

## Open question being investigated

Three different sha256 values for a "policyengine-us 2.0.0" wheel exist across today's
lanes: published `4ca18750…`, acceptance-matrix `4208998a…`, loader-candidate `05c729ae…`.
The first is the only one on PyPI. Determining whether the matrix's numerical acceptance
transfers to the published wheel bytes.

## Next

1. Repin the bundle manifest to the canonical tuple and regenerate pyproject.
2. Certify the US data release at the tag above into the manifest.
3. Refresh `uv.lock` (uv only, no local wheel links) and run the lock/release guards.
4. Run the full suite as CI does; the SPM tests must run, not skip.
5. Commit, force-with-lease push against `223bce47`, watch CI. Leave draft.
