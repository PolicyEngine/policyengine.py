## [3.5.0] - 2026-04-18

### Added

- Support Python 3.9–3.12 (in addition to 3.13–3.14). PEP 604 `X | Y` annotations (evaluated at runtime by pydantic) are rewritten as `Optional[X]` / `Union[X, Y]`; `StrEnum` (3.11+) is replaced with `class Foo(str, Enum)`; PEP 695 generic class syntax in `core/cache.py` and `core/output.py` is rewritten using `typing.TypeVar` + `typing.Generic`. Ruff and mypy target versions dropped to py39. Requires `policyengine-us==1.602.0+` and `policyengine-uk==2.74.0+` from the `[us]`/`[uk]`/`[dev]` extras to also support 3.9/3.10.

### Changed

- Point CONTRIBUTING.md at the shared PolicyEngine contribution guide (https://github.com/PolicyEngine/.github) and trim the per-repo file to commands, repo-specific conventions, and anti-patterns. Removes the stale `changelog_entry.yaml` / `make changelog` instructions.
- Change the installed-vs-manifest country-model version check from a hard `ValueError` to a `UserWarning`. Calculations now run against whatever country-model version is installed; downstream code that cares about exact pinning can still inspect `model.release_manifest`. This stops routine country-model patch bumps from breaking `UKTaxBenefitModel`/`USTaxBenefitModel` instantiation in callers that pin `policyengine` but resolve `policyengine-uk`/`policyengine-us` via `>=`.

### Fixed

- Bump pinned country-model versions in `[us]`, `[uk]`, and `[dev]` extras, and the corresponding bundled release manifests, to versions that support Python 3.9, include the breakdown-range fixes required by the stricter validator in policyengine-core 3.24.0+, and ship with policyengine-core>=3.24.1. Previously `policyengine-us==1.602.0` and `policyengine-uk==2.74.0` were stale pins that no longer installed cleanly under modern core. Data-package pins (`policyengine-us-data==1.73.0`, `policyengine-uk-data==1.40.4`) are unchanged — the bumped model versions read the same dataset artefacts as before.
- Bump `policyengine_core` minimum to `>=3.25.0`. Includes the `set_input` preservation fix from PolicyEngine/policyengine-core#475 that restores UK household-impact calculations after `apply_reform` (#1628). All 11 `tests/test_household_impact.py` cases pass on the new pin.


## [3.4.5] - 2026-04-16

### Changed

- Added managed release-bundle runtime enforcement for bundled US and UK microsimulations, including manifest-backed dataset pinning and runtime bundle metadata.


## [3.4.4] - 2026-04-13

### Changed

- Add TRACE TRO export helpers for certified runtime bundles and expose them through `policyengine.core`.


## [3.4.3] - 2026-04-13

### Fixed

- Fix the release versioning workflow so it bumps from the highest known released version instead of regressing to a stale version from `pyproject.toml`.


## [3.4.1] - 2026-04-13

### Changed

- Add certified bundle metadata that records runtime model pins alongside build-time data artifact provenance and compatibility fingerprints.


## [3.4.2] - 2026-04-12

### Changed

- Align the bundled UK release manifest with the pinned `policyengine-uk` package version and updated data package revisions.


## [3.4.1] - 2026-04-09

### Fixed

- Fixed the UK paper reproduction workflow so the checked-in example runs on Python 3.14 and the associated analysis helpers handle that path cleanly.


## [3.4.0] - 2026-04-08

### Added

- Add winner, loser, and no-change percentages to the congressional district impact output.


## [3.3.0] - 2026-03-20

### Added

- Added documentation for economic impact analysis, advanced outputs (DecileImpact, Poverty, Inequality, IntraDecileImpact), regions and scoping strategies, simulation lifecycle (ensure vs run), Dynamic class, data loading, and simulation modifiers. Added US budgetary impact example script. Fixed PR docs CI to use MyST matching production.


## [3.2.4] - 2026-03-17

### Changed

- Skip redundant Lint and Test in Phase 2 of push workflow since code is identical to Phase 1


## [3.2.3] - 2026-03-17

### Fixed

- Use GitHub App token in push workflow Versioning job to enable auto-triggering of Phase 2 (Publish)


## [3.2.2] - 2026-03-17

### Changed

- Consolidate CI/CD workflows into a unified push workflow with two-phase sentinel pattern, enforce changelog fragments on PRs

### Fixed

- Use GITHUB_TOKEN instead of missing POLICYENGINE_GITHUB PAT in push workflow


## [3.2.1] - 2026-03-10

### Changed

- Migrated from changelog_entry.yaml to towncrier fragments to eliminate merge conflicts.
- Switched code formatter from black to ruff format.


# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.0] - 2026-02-24 17:31:22

### Added

- Python 3.14 support

## [3.1.16] - 2026-01-25 14:20:29

### Changed

- Bumped policyengine-core minimum version to 3.23.5 for pandas 3.0 compatibility

## [3.1.15] - 2025-12-14 23:51:27

### Added

- Household impacts

## [3.1.14] - 2025-12-10 21:59:24

### Fixed

- Improvements to loading taxbenefitsystems.

## [3.1.13] - 2025-12-10 19:29:28

### Fixed

- Naming improvements.

## [3.1.12] - 2025-12-10 14:43:52

### Fixed

- Bug where all datasets would be the last year.

## [3.1.11] - 2025-12-02 14:03:39

### Fixed

- Caching didn't save time!

## [3.1.10] - 2025-12-02 13:02:37

### Fixed

- Caching failure.

## [3.1.9] - 2025-12-02 12:48:37

### Fixed

- Added caching of saved simulations

## [3.1.8] - 2025-12-02 00:20:11

### Fixed

- Dataset speedup with better handling of string cols.

## [3.1.7] - 2025-11-24 16:34:53

### Fixed

- Build error

## [3.1.6] - 2025-11-24 16:23:57

### Fixed

- Parameter values now accessible from models.

## [3.1.5] - 2025-11-21 12:59:36

### Fixed

- Minor fixes

## [3.1.4] - 2025-11-20 14:06:49

### Fixed

- Minor fixes

## [3.1.3] - 2025-11-18 13:46:23

### Fixed

- Entity variables moved out to an editable constant.

## [3.1.2] - 2025-11-18 11:09:18

### Fixed

- Standardised saving and loading of simulations.

## [3.1.1] - 2025-11-17 11:45:43

### Added

- Policy and Dynamic classes now support addition operator (__add__) to combine policies and dynamics.
- Parameter values are appended when combining policies/dynamics.
- Simulation modifiers are chained in sequence when combining policies/dynamics.

## [3.1.0] - 2025-11-17 10:25:50

## [3.0.0] - 2025-09-23 08:43:22

### Fixed

- Major version bump to fix pypi issues.

## [2.0.0] - 2025-09-21 22:29:03

### Added

- Consolidated models and database integration.

## [1.0.0] - 2025-09-21 22:26:17

### Added

- Complete rewrite.

## [0.6.1] - 2025-08-14 08:11:19

### Fixed

- Fixed UK dataset loading issue.

## [0.6.0] - 2025-07-17 10:27:55

### Fixed

- Updated the UK data to the latest survey year.

## [0.5.0] - 2025-06-26 20:04:46

### Added

- Unit test for GeneralEconomyTask.calculate_cliffs() and fixture for the test
- Test for calculate_single_economy with cliff impacts

## [0.4.5] - 2025-06-05 05:08:16

### Fixed

- Added more log messages.

## [0.4.4] - 2025-06-04 07:35:40

### Fixed

- ECPS handling issue.

## [0.4.3] - 2025-06-02 07:53:55

### Fixed

- Removed bad type check.

## [0.4.2] - 2025-05-30 21:12:45

### Added

- Tests for Simulation._set_data()

### Changed

- Disambiguated filepath management in Simulation._set_data()
- Refactored Simulation._set_data() to divide functionality into smaller methods
- Prevented passage of non-Path URIs to Dataset.from_file() at end of Simulation._set_data() execution

## [0.4.1] - 2025-05-27 11:10:28

### Fixed

- Model and data versions are always available.

## [0.4.0] - 2025-05-26 21:26:48

### Added

- Error handling for data and package version mismatches.

## [0.3.10] - 2025-05-23 00:09:23

### Fixed

- Always look for new data file versions even if we have a local copy of one.

## [0.3.9] - 2025-05-20 08:28:29

### Fixed

- Added cliff impacts.

## [0.3.8] - 2025-05-19 22:42:39

### Fixed

- google storage caching is now fully sync, not async and reenabled.

## [0.3.7] - 2025-05-19 16:53:05

### Fixed

- revert cached downloads from google storage

## [0.3.6] - 2025-05-16 16:18:15

### Fixed

- Removed max and min year bounds for Simulations.

## [0.3.5] - 2025-05-16 14:00:30

### Fixed

- downloads from google storage should now be properly cached.

## [0.3.4] - 2025-05-16 12:55:50

### Fixed

- Fixed `format_fig` to work with Python 3.11.

## [0.3.3] - 2025-05-16 12:23:45

### Added

- Changelog entry check.

## [0.3.2] - 2025-05-15 21:56:02

### Added

- new class CachingGoogleStorageClient for locally caching gs files to disk.

## [0.3.1] - 2025-05-15 15:52:24

### Changed

- Refactored ParametricReform schema into clearer subschemas.
- Added conversion of Infinity and -Infinity to np.inf and -np.inf.

## [0.3.0] - 2025-05-13 23:23:01

### Changed

- Economy simulation comparisons now include country package version

## [0.2.1] - 2025-04-30 11:33:36

### Added

- Default dataset handling (extra backups added).

### Fixed

- Bug in state tax revenue calculation.

## [0.2.0] - 2025-04-29 13:08:11

### Added

- Google Cloud Storage data downloads.

## [0.1.3] - 2025-04-26 16:25:19

### Fixed

- Gracefully handle HuggingFace 429s.

## [0.1.2] - 2025-04-26 16:21:55

### Fixed

- Gracefully handle data download 429s.

## [0.1.1] - 2025-02-21 14:02:22

### Fixed

- Dependency for `pkg_resources`.

## [0.1.0] - 2024-11-30 00:00:00

### Added

- Initial version of package.



[3.2.0]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.16...3.2.0
[3.1.16]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.15...3.1.16
[3.1.15]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.14...3.1.15
[3.1.14]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.13...3.1.14
[3.1.13]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.12...3.1.13
[3.1.12]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.11...3.1.12
[3.1.11]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.10...3.1.11
[3.1.10]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.9...3.1.10
[3.1.9]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.8...3.1.9
[3.1.8]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.7...3.1.8
[3.1.7]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.6...3.1.7
[3.1.6]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.5...3.1.6
[3.1.5]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.4...3.1.5
[3.1.4]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.3...3.1.4
[3.1.3]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.2...3.1.3
[3.1.2]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.1...3.1.2
[3.1.1]: https://github.com/PolicyEngine/policyengine.py/compare/3.1.0...3.1.1
[3.1.0]: https://github.com/PolicyEngine/policyengine.py/compare/3.0.0...3.1.0
[3.0.0]: https://github.com/PolicyEngine/policyengine.py/compare/2.0.0...3.0.0
[2.0.0]: https://github.com/PolicyEngine/policyengine.py/compare/1.0.0...2.0.0
[1.0.0]: https://github.com/PolicyEngine/policyengine.py/compare/0.6.1...1.0.0
[0.6.1]: https://github.com/PolicyEngine/policyengine.py/compare/0.6.0...0.6.1
[0.6.0]: https://github.com/PolicyEngine/policyengine.py/compare/0.5.0...0.6.0
[0.5.0]: https://github.com/PolicyEngine/policyengine.py/compare/0.4.5...0.5.0
[0.4.5]: https://github.com/PolicyEngine/policyengine.py/compare/0.4.4...0.4.5
[0.4.4]: https://github.com/PolicyEngine/policyengine.py/compare/0.4.3...0.4.4
[0.4.3]: https://github.com/PolicyEngine/policyengine.py/compare/0.4.2...0.4.3
[0.4.2]: https://github.com/PolicyEngine/policyengine.py/compare/0.4.1...0.4.2
[0.4.1]: https://github.com/PolicyEngine/policyengine.py/compare/0.4.0...0.4.1
[0.4.0]: https://github.com/PolicyEngine/policyengine.py/compare/0.3.10...0.4.0
[0.3.10]: https://github.com/PolicyEngine/policyengine.py/compare/0.3.9...0.3.10
[0.3.9]: https://github.com/PolicyEngine/policyengine.py/compare/0.3.8...0.3.9
[0.3.8]: https://github.com/PolicyEngine/policyengine.py/compare/0.3.7...0.3.8
[0.3.7]: https://github.com/PolicyEngine/policyengine.py/compare/0.3.6...0.3.7
[0.3.6]: https://github.com/PolicyEngine/policyengine.py/compare/0.3.5...0.3.6
[0.3.5]: https://github.com/PolicyEngine/policyengine.py/compare/0.3.4...0.3.5
[0.3.4]: https://github.com/PolicyEngine/policyengine.py/compare/0.3.3...0.3.4
[0.3.3]: https://github.com/PolicyEngine/policyengine.py/compare/0.3.2...0.3.3
[0.3.2]: https://github.com/PolicyEngine/policyengine.py/compare/0.3.1...0.3.2
[0.3.1]: https://github.com/PolicyEngine/policyengine.py/compare/0.3.0...0.3.1
[0.3.0]: https://github.com/PolicyEngine/policyengine.py/compare/0.2.1...0.3.0
[0.2.1]: https://github.com/PolicyEngine/policyengine.py/compare/0.2.0...0.2.1
[0.2.0]: https://github.com/PolicyEngine/policyengine.py/compare/0.1.3...0.2.0
[0.1.3]: https://github.com/PolicyEngine/policyengine.py/compare/0.1.2...0.1.3
[0.1.2]: https://github.com/PolicyEngine/policyengine.py/compare/0.1.1...0.1.2
[0.1.1]: https://github.com/PolicyEngine/policyengine.py/compare/0.1.0...0.1.1
