# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
