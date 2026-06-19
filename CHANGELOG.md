## [4.17.9] - 2026-06-18

### Changed

- Certify the US data release `populace-us-2024-c86a631-6e1bcd0271a5-20260619T002242Z` (populace_us_2024, policyengine-us 1.729.0) directly from its data release manifest.


## [4.17.8] - 2026-06-18

### Changed

- Update the certified US Populace dataset to the incumbent-improved 2024 release.


## [4.17.7] - 2026-06-17

### Fixed

- Restore the previous US Populace default dataset and reject Populace releases whose critical fiscal calibration targets miss certification tolerances.


## [4.17.6] - 2026-06-17

### Changed

- Refresh the bundled US Populace release manifest to the 2026-06-17 certified build.


## [4.17.5] - 2026-06-16

### Fixed

- Certify the Populace-US data release `populace-us-2024-a912aea-76666318a202-20260616T175345Z` and keep data-only release refreshes aligned with release-scoped diagnostics artifacts.


## [4.17.4] - 2026-06-16

### Changed

- Certify the US data release `populace-us-2024-f32c2e5-0c38bc47db89-20260616T124451Z` (populace_us_2024, policyengine-us 1.729.0) directly from its data release manifest.


## [4.17.3] - 2026-06-15

### Changed

- Certify the US data release `populace-us-2024-0cdbb27-c239dfe51c11-20260615T201302Z` (populace_us_2024, policyengine-us 1.729.0) directly from its data release manifest.


## [4.17.2] - 2026-06-15

### Changed

- Require Populace-US data certification to verify the supplemental source-coverage release file before vendoring a release manifest.


## [4.17.1] - 2026-06-14

### Changed

- Refresh the bundled US model pin to policyengine-us 1.726.0 and teach the release-bundle refresh helper to fetch data-release manifests from Hugging Face dataset repos.


## [4.17.0] - 2026-06-14

### Added

- `Simulation.write_run_record(directory)` writes a self-contained, citable run record (reform, input, and results payloads, the certified bundle TRO, and a per-run TRACE TRO binding them by sha256), and `policyengine trace-tro-verify` fetches and rehashes every artifact a TRO claims — offline-capable for run-record directories.

### Changed

- Updated the TRACE case study with a June 2026 status section covering shipped TRO tooling (bundle TROs via #401, populace build TROs, run records #403, trace-tro-verify, Zenodo mirroring #405).


## [4.16.2] - 2026-06-12

### Changed

- Certify country data releases directly from their Hugging Face release manifests (`scripts/certify_data_release.py`), replacing the policyengine-bundles import flow. The vendored US manifest is regenerated through the new path (byte-identical apart from the certification source strings), and the vendored bundle archive copies are no longer shipped.


## [4.16.1] - 2026-06-12

### Changed

- Import PolicyEngine bundle 4.16.0: the `populace-data` release manifest (`populace_us_2024` built from primary sources) replaces `policyengine-us-data` as the certified US data release, with policyengine-us 1.723.0 and policyengine-core 3.27.1. Dataset references and region datasets now honor per-artifact repo pins so inherited datasets keep resolving from their original repos.


## [4.16.0] - 2026-06-11

### Added

- Support dataset-type Hugging Face repos in dataset materialization (retry with repo_type=dataset before surfacing the original failure).


## [4.15.0] - 2026-06-10

### Added

- Add schema-v2 `policyengine-bundles` archive import support for future bundle-driven release updates.


## [4.14.3] - 2026-06-08

### Changed

- Refresh the bundled US release manifest to policyengine-us 1.722.4.


## [4.14.2] - 2026-06-07

### Changed

- Reverted the certified US dataset to Enhanced CPS (`policyengine-us-data` 1.115.5, `policyengine-us` 1.715.2). The microplex MP 2cdd45d artifact promoted in 4.14.1 loses to production eCPS on a correctly-scored target surface (full PE-native loss 0.0428 vs 0.0266; eCPS wins 2334 of 2809 targets) and is 14–49× worse on income components.


## [4.14.1] - 2026-06-05

### Changed

- Update the bundled US release manifest to the MP/eCPS 2024 `enhanced_cps_2024` artifact.


## [4.14.0] - 2026-06-04

### Added

- Add a verified importer for vendoring release assets from `policyengine-bundles`.


## [4.13.1] - 2026-06-01

### Changed

- Refresh the bundled US release manifest to policyengine-us 1.715.2 and require explicit data-release compatibility assertions when refreshing bundles across model versions.


## [4.13.0] - 2026-06-01

### Added

- Add AI-facing release-bundle guidance for single-country refreshes and compatibility fallbacks.


## [4.12.1] - 2026-05-30

### Fixed

- Restore runtime loading for `gs://` dataset URIs and materialize remote
  datasets before handing them to country package microsimulations.


## [4.12.0] - 2026-05-28

### Added

- Added opt-in macro cliff impact outputs for US and UK reform analyses.


## [4.11.0] - 2026-05-23

### Added

- Added JOSS paper (paper.md and paper.bib) for submission to the Journal of Open Source Software.

### Fixed

- Fixed AttributeError in `examples/paper_repro_uk.py` (`programme_statistics` -> `program_statistics`).


## [4.10.0] - 2026-05-21

### Added

- UK constituency and local-authority output helpers can now resolve standard geography files locally or download them from GCS by default.

### Fixed

- Align the pull-request changelog check with Towncrier's post-merge fragment discovery and add model-neutral AI PR guidance.


## [4.9.2] - 2026-05-20

### Changed

- Update the bundled UK release to calibrated fuel-duty litres.


## [4.9.1] - 2026-05-20

### Changed

- Update the bundled US model and enhanced CPS data release while preserving explicitly versioned dataset entries.


## [4.9.0] - 2026-05-19

### Added

- - Add a legacy-compatible labor-supply response output for US and UK macro analyses.


## [4.8.1] - 2026-05-19

### Changed

- Add UK program-statistics rows for fuel duty, state pension, employer National Insurance, and tax credits.


## [4.8.0] - 2026-05-19

### Added

- Add UK wealth-decile impact outputs and integration coverage for economic impact analysis.


## [4.7.0] - 2026-05-18

### Added

- Add ``policyengine.derivations`` for per-variable computation explanations: ``derive(simulation, variable, period)`` returns a structured ``Derivation`` (with pruned trace and top-level contributions); ``narrate(derivation)`` optionally hands it to an LLM for a plain-prose walkthrough.


## [4.6.0] - 2026-05-18

### Added

- Added the US long-run managed dataset bundle.

### Fixed

- Refresh US long-term dataset hash pins from data release manifests.


## [4.5.1] - 2026-05-16

### Changed

- Updated the bundled US release manifest to policyengine-us 1.691.10 and policyengine-us-data 1.115.3.


## [4.5.0] - 2026-05-16

### Added

- Add metadata-aware loading for pre-built long-term US projected datasets.


## [4.4.4] - 2026-05-13

### Changed

- Update the bundled US release to policyengine-us 1.691.3 and policyengine-us-data 1.113.1.


## [4.4.3] - 2026-05-11

### Changed

- Derive US program-statistics entity from variable metadata instead of duplicating it in the program list.
- Update the bundled US release to policyengine-us 1.690.7 and refresh data provenance metadata.


## [4.4.2] - 2026-05-09

### Fixed

- Point the bundled US data release manifest at a revision that certifies policyengine-core 3.26.1 compatibility.


## [4.4.1] - 2026-05-09

### Fixed

- Preserve core-package compatibility metadata when parsing data release manifests, and deploy the Quarto documentation output from the correct `_site` directory.


## [4.4.0] - 2026-05-09

### Added

- Extended `DataReleaseManifest` with optional preservation-mirror fields. Added a `PreservationMirror` model (kind, url, optional doi / sha256 / deposited_at), a `preservation_mirrors` list on each `DataReleaseArtifact`, and a top-level `preservation_dois` list on the manifest. Back-compatible: all new fields have defaults, and pre-existing manifests continue to validate. Populated by release pipelines that mirror artifacts to Zenodo or another preservation-grade host; addresses PolicyEngine/policyengine-us-data#810.
- Added `docs/trace-case-study.md`, a working draft describing the PolicyEngine TRACE use case for Lars Vilhuber (AEA Data Editor) and the TRACE project team. Covers which PolicyEngine surfaces warrant institutional certification, the precise claims a TRO lets us make, UK data as the strongest case, the three concrete workstreams (us-data build TROs, policyengine-api webapp-run TROs, policyengine-app "Cite this result" UI), and open questions we want feedback on.

### Changed

- Updated GitHub Actions workflows for Node 24-compatible action runtimes.
- Updated the bundled UK release to policyengine-uk 2.88.14 and policyengine-uk-data 1.55.5.
- Bump the bundled US model pin to policyengine-us 1.687.0.

### Fixed

- Country model imports now work without network access when the bundled release manifest already certifies the installed country package version. Hugging Face release-manifest transport failures fall back to bundled data certification only when the runtime model version and data build fingerprint gates still match.
- Sync bundled release manifest bundle IDs and `policyengine_version` fields during release version bumps.
- Two small follow-ups surfaced by the v4 audit:

  - ``Simulation.save()`` now raises a helpful ``ValueError`` when ``output_dataset`` is still ``None`` (run or ensure was never called), instead of the raw ``AttributeError: 'NoneType' object has no attribute 'save'``.
  - New ``scripts/check_data_staleness.py`` prints a one-line verdict per country comparing the bundled release manifest's pinned model version against the installed country package; exits non-zero when any country is stale. Drop into CI to get automated "bundle is behind" alerts without waiting for a human to notice.

  Also clarified the ``load()`` docstring: ``created_at``/``updated_at`` are filesystem ``ctime``/``mtime`` approximations, not a true round-trip of the original timestamps.


## [4.3.1] - 2026-04-21

### Changed

- Migrated TRACE TRO emission from the prerelease TROv namespace `https://w3id.org/trace/2023/05/trov#` to the canonical `https://w3id.org/trace/trov/0.1#`. This aligns policyengine.py with policyengine-us-data (which already uses the canonical namespace per us-data PR #746), so both sides can share SHACL validators and TROs emitted by either side validate against the same vocabulary. Fixes #313.


## [4.3.0] - 2026-04-20

### Added

- Added `policyengine.provenance.refresh_release_bundle`. Given a country and optional new model/data versions, the helper fetches the updated PyPI wheel metadata + HF dataset sha256, rewrites `data/release_manifests/{country}.json` and the matching extra pin in `pyproject.toml`, and (optionally) regenerates the bundle's TRACE TRO sidecar. A thin `scripts/refresh_release_bundle.py` wrapper exposes the library function as a CLI for release engineers. Unit-tested offline via mocked PyPI/HF responses.


## [4.2.1] - 2026-04-20

### Changed

- Rewrite docs content for the v4 API: separate pages per task (households, reforms, microsim, outputs, impact analysis, regions), updated code samples against real output classes and `Simulation` dict reforms.


## [4.2.0] - 2026-04-20

### Added

- Added ``policyengine.graph`` — a static-analysis-based variable dependency graph for PolicyEngine source trees. ``extract_from_path(path)`` walks a directory of Variable subclasses, parses formula-method bodies for ``entity("<var>", period)`` and ``add(entity, period, [list])`` references, and returns a ``VariableGraph``. Queries include ``deps(var)`` (direct dependencies), ``impact(var)`` (transitive downstream), and ``path(src, dst)`` (shortest dependency chain). No runtime dependency on country models — indexes ``policyengine-us`` (4,577 variables) in under a second.


## [4.1.1] - 2026-04-20

### Fixed

- Fixed `Simulation.extra_variables` being silently ignored on the US and UK microsim paths. The field is declared on the base `Simulation` and honored by the household calculator, but the country `run()` methods previously only iterated `self.entity_variables` — extras passed via `Simulation(extra_variables={...})` never reached the output dataset. Both country paths now route through a shared `MicrosimulationModelVersion.resolve_entity_variables` helper that merges defaults with extras, dedupes overlapping entries, and validates entity keys + variable names with close-match suggestions. Closes #303.
- Fixed structural-reform propagation in the US microsim path. `Simulation(policy={"gov.contrib.ctc.*": ...})` previously crashed at `.ensure()` with `AttributeError: 'NoneType' object has no attribute 'entity'` because `_build_simulation_from_dataset` instantiated entities against the module-level `policyengine_us.system` (no reform applied) instead of `microsim.tax_benefit_system` (reform applied). Published external reforms that activate all three `gov.contrib.ctc.*.in_effect` gates (e.g., app.policyengine.org policy 94589) now run end-to-end through `pe.us.economic_impact_analysis`.


## [4.1.0] - 2026-04-20

### Added

- ``Simulation(policy={...})`` and ``Simulation(dynamic={...})`` now accept the same flat ``{"param.path": value}`` / ``{"param.path": {date: value}}`` dict that ``pe.{uk,us}.calculate_household(reform=...)`` accepts. Dicts are compiled to full ``Policy`` / ``Dynamic`` objects on construction using the ``tax_benefit_model_version`` for parameter-path validation and ``dataset.year`` for scalar effective-date defaulting. Removes the last place where population microsim required building ``Parameter`` / ``ParameterValue`` by hand.
- **BREAKING (v4):** Collapse the household-calculator surface into a
  single agent-friendly entry point, ``pe.us.calculate_household`` /
  ``pe.uk.calculate_household``.

  New public API:

  - ``policyengine/__init__.py`` populated with canonical accessors:
    ``pe.us``, ``pe.uk``, ``pe.Simulation`` (replacing the empty top-level
    module). ``import policyengine as pe`` now gives you everything a
    new coding session needs to reach in one line.
  - ``pe.us.calculate_household(**kwargs)`` and ``pe.uk.calculate_household``
    take flat keyword arguments (``people``, per-entity overrides,
    ``year``, ``reform``, ``extra_variables``) instead of a pydantic
    input wrapper.
  - ``reform=`` accepts a plain dict: ``{parameter_path: value}`` or
    ``{parameter_path: {effective_date: value}}``. Compiles internally.
  - Returns :class:`HouseholdResult` (new) with dot-access:
    ``result.tax_unit.income_tax``, ``result.household.household_net_income``,
    ``result.person[0].age``. Singleton entities are
    :class:`EntityResult`; ``person`` is a list of them. ``to_dict()``
    and ``write(path)`` serialize to JSON.
  - ``extra_variables=[...]`` is now a flat list; the library dispatches
    each name to its entity by looking it up on the model.
  - Unknown variable names (in ``people``, entity overrides, or
    ``extra_variables``) raise ``ValueError`` with a ``difflib`` close-match
    suggestion and a paste-able fix hint.
  - Unknown dot-access on a result raises ``AttributeError`` with the
    list of available variables plus the ``extra_variables=[...]`` call
    that would surface the requested one.

  Removed (v4 breaking):

  - ``USHouseholdInput`` / ``UKHouseholdInput`` / ``USHouseholdOutput`` /
    ``UKHouseholdOutput`` pydantic wrappers.
  - ``calculate_household_impact`` — the name was misleading (it
    returned levels, not an impact vs. baseline). Reserved for a future
    delta function.
  - The bare ``us_model`` / ``uk_model`` label-only singletons; each
    country module now exposes ``.model`` pointing at the real
    ``TaxBenefitModelVersion`` (kept ``us_latest`` / ``uk_latest``
    aliases for compatibility with any in-flight downstream code).

  New internal module:

  - ``policyengine.tax_benefit_models.common`` — ``compile_reform``,
    ``dispatch_extra_variables``, ``EntityResult``, ``HouseholdResult``
    shared by both country implementations.

### Changed

- Extracted shared `MicrosimulationModelVersion` base class in `policyengine.tax_benefit_models.common`. Country subclasses now declare class-level metadata (`country_code`, `package_name`, `group_entities`) and implement a handful of thin hooks; `run()` stays per-country. Byte-level snapshot tests verify zero output drift.
- Documentation refreshed for the v4 agent-first surface. README, `core-concepts`, `economic-impact-analysis`, `country-models-{uk,us}`, `regions-and-scoping`, `examples`, and `dev` now lead with `pe.uk.*` / `pe.us.*` entry points and flat-kwarg `calculate_household` usage. Removed leftover docs for the dropped `filter_field`/`filter_value` simulation fields. `examples/household_impact_example.py` rewritten against the v4 API.
- **BREAKING (v4):** Separate the provenance layer from the core
  value-object layer.

  - ``policyengine/core/release_manifest.py`` → ``policyengine/provenance/manifest.py``
  - ``policyengine/core/trace_tro.py`` → ``policyengine/provenance/trace.py``
  - New ``policyengine.provenance`` package re-exports the public
    surface (``get_release_manifest``, ``get_data_release_manifest``,
    ``build_trace_tro_from_release_bundle``, ``build_simulation_trace_tro``,
    ``serialize_trace_tro``, ``canonical_json_bytes``,
    ``compute_trace_composition_fingerprint``, etc.).
  - ``policyengine.core`` no longer re-exports provenance types.
    ``policyengine.core`` shrinks to value objects only (Dataset,
    Variable, Parameter, Policy, Dynamic, Simulation, Region,
    TaxBenefitModel, TaxBenefitModelVersion, scoping strategies).
  - ``import policyengine.core.scoping_strategy`` no longer imports
    ``h5py`` at module load; the weight-replacement code path
    lazy-imports it. ``import policyengine.outputs.constituency_impact``
    and ``import policyengine.outputs.local_authority_impact`` do the
    same.
  - Migration for downstream: replace
    ``from policyengine.core import DataReleaseManifest`` (et al.)
    with ``from policyengine.provenance import DataReleaseManifest``.
    The country-module imports in internal code (``tax_benefit_models/{us,uk}/model.py``
    and ``datasets.py``) are already updated.


## [3.7.0] - 2026-04-19

### Removed

- Pre-launch cleanup — remove dead code and drop `plotly` from the core dependency set:

  - Delete `policyengine.tax_benefit_models.us` and `policyengine.tax_benefit_models.uk` module shims. Python resolves the package directory first, so the `.py` shims were always shadowed; worse, both attempted to re-export `general_policy_reform_analysis` which is not defined anywhere, making `from policyengine.tax_benefit_models.us import general_policy_reform_analysis` raise `ImportError` at runtime.
  - Delete `_create_entity_output_model` plus the `PersonOutput` / `BenunitOutput` / `HouseholdEntityOutput` factory products in `policyengine.tax_benefit_models.uk.analysis` — built via `pydantic.create_model` but never referenced anywhere in the codebase.
  - Delete `policyengine.core.DatasetVersion` (only consumer was an `Optional` field on `Dataset` that was never set, and the `policyengine.core` re-export).
  - Move `plotly>=5.0.0` from the base install to a new `policyengine[plotting]` extra. Only `policyengine.utils.plotting` uses it, and that module is itself only used by the `examples/` scripts. The package now imports cleanly without `plotly`.
- **BREAKING (v4):** Remove the legacy `filter_field` / `filter_value`
  fields from `Simulation` and `Region`, the `_auto_construct_strategy`
  model validator that rewrote them into a `RowFilterStrategy`, and the
  `_filter_dataset_by_household_variable` methods they fed on both
  country models. All scoping now flows through `scoping_strategy:
  Optional[ScopingStrategy]`. `Region.requires_filter` becomes a derived
  property (`True` iff `scoping_strategy is not None`). The sub-national
  region factories (`countries/us/regions.py`, `countries/uk/regions.py`)
  construct `scoping_strategy=RowFilterStrategy(...)` /
  `WeightReplacementStrategy(...)` directly. Callers that previously
  passed `filter_field="place_fips", filter_value="44000"` now pass
  `scoping_strategy=RowFilterStrategy(variable_name="place_fips",
  variable_value="44000")`.


## [3.6.0] - 2026-04-18

### Added

- `certify_data_release_compatibility` now accepts full PEP 440 version
  specifiers (`>=1.637.0,<2.0.0`, `~=1.637`, etc.) in a data release
  manifest's `compatible_model_packages`, not only `==X.Y.Z`. This lets
  the US data package declare a range of compatible `policyengine-us`
  versions when the `data_build_fingerprint` is known to be stable
  across them, avoiding the need to regenerate the dataset for every
  model patch release. Adds `packaging>=23.0` as a direct dependency.
- TRACE TRO hardening: bundle TROs now hash the country model wheel (read from
  `PackageVersion.sha256` when present, otherwise fetched from PyPI), use HTTPS
  artifact locations, carry structured `pe:*` certification fields and GitHub
  Actions attestation metadata, and are validated in CI against a shipped JSON
  Schema. Adds a `policyengine trace-tro` CLI, per-simulation TROs through
  `policyengine.results.build_results_trace_tro` / `write_results_with_trace_tro`,
  and restores the `TaxBenefitModelVersion.trace_tro` property and
  `policyengine.core` re-exports that were dropped in #276.

### Changed

- TRACE TRO emission now conforms to the public TROv 2023/05 vocabulary:
  switched namespace to `https://w3id.org/trace/2023/05/trov#`, flattened
  `trov:hash` nodes to the native `trov:sha256` property, renamed
  `trov:path`→`trov:hasLocation` and the inverse pointer on ArtifactLocation
  to `trov:hasArtifact`, corrected `TrustedResearchSystem`→`TransparentResearchSystem`
  and `TrustedResearchPerformance`→`TransparentResearchPerformance`, and replaced
  the locally-invented `ArrangementBinding` chain with
  `trov:accessedArrangement` as used by the published trov-demos. Every TRO
  now carries `pe:emittedIn` (`"local"` or `"github-actions"`) so a verifier
  can distinguish a CI-emitted TRO from a laptop rebuild. Per-simulation TROs
  accept a `bundle_tro_url` that is recorded as `pe:bundleTroUrl`, letting a
  verifier independently fetch and re-hash the bundle to detect a forged
  reference. The composition fingerprint now joins hashes with `\n` to
  prevent hex-length concatenation collisions. Adds `policyengine
  trace-tro-validate` CLI, removes the broken `--offline` flag, wires
  `scripts/generate_trace_tros.py` into the `Versioning` CI job so bundled
  TROs ship with every release, inlines the real model wheel sha256 on
  `us.json`/`uk.json`, and cleans up the dead `DataReleaseArtifact.https_uri`
  / `_data_release_manifest_url` helpers.
- Bump the bundled US release manifest to `policyengine-us==1.653.3` (from
  1.647.0) to unblock downstream projects that want to pin the latest
  working model version through `policyengine.py`. The dataset stays at
  `policyengine-us-data==1.73.0` (the latest US data release tagged on
  Hugging Face); certification is now
  `matching_data_build_fingerprint` with `built_with_model_version`
  recording the 1.647.0 that actually produced the data. Both bundled
  manifests (`us.json`, `uk.json`) update `policyengine_version` and
  `bundle_id` to 3.5.0 to match the current package version.


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
