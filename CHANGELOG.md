# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
