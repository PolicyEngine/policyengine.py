**BREAKING (v4):** Separate the provenance layer from the core
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
