---
title: "Microsimulation"
---

For population-level estimates — budget cost, winners and losers, poverty impact — run a microsimulation over calibrated microdata.

For US decile analysis, `calculate_decile_impacts(dataset=..., spm=...)` passes
the selection to both constructed simulations. When supplying existing
baseline and reform simulations, set `spm` on each simulation directly.

## Quick example

```python
import policyengine as pe
from policyengine.core import Simulation
from policyengine.outputs import Aggregate, AggregateType

datasets = pe.us.ensure_datasets(years=[2026])
dataset = next(iter(datasets.values()))

baseline = Simulation(dataset=dataset, tax_benefit_model_version=pe.us.model)
baseline.ensure()

total_snap = Aggregate(
    simulation=baseline,
    variable="snap",
    aggregate_type=AggregateType.SUM,
)
total_snap.run()
total_snap.result
```

`Simulation.ensure()` loads a cached result if one exists, or runs and caches on miss. Call `Simulation.run()` explicitly if you want to bypass the cache.

### Canonical US SPM settings and provenance

The coordinated canonical SPM integration resolves measurement settings from
the bundle. Its default uses each household's observed `county_fips` and native
SPM membership. To make an explicit national sensitivity calculation:

```python
simulation = pe.Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.us.model,
    spm={"geography_kind": "national", "scenario": "zero_real"},
)
simulation.run()
settings = simulation.spm_config
receipt = simulation.spm_provenance()
serialized = simulation.model_dump_json(include={"spm", "spm_receipt"})
```

`spm_config` exposes all six resolved settings; `spm_provenance()` returns a
detached JSON-compatible measurement receipt after calculation. The stored
`spm_receipt` is a Pydantic model. Before calculation, serializing a partial
selection preserves omitted options so they continue to inherit the bundle's
defaults after JSON restoration; successful calculation freezes all six settings.
Selection participates in simulation identity
and cached results. The example serializes the measurement settings and receipt;
the existing full simulation model graph contains circular model/variable
references and cannot currently be exported with an unrestricted
`model_dump_json()`. Use simulation persistence and run records for saved runs.
The same `spm=` selection is accepted by
`pe.us.managed_microsimulation`; its returned country simulation exposes
`spm_config` and `spm_provenance()` too. See the [household SPM
contract](households.md#spm-geography-and-measurement-selection) for exact keys,
the 2022–2035 artifact horizon and explicit geography errors. No provider or
forecast-file path can replace the bundle's pinned artifact.

For a small local development dataset, explicitly opt out of managed data
selection:

```python
simulation = pe.us.managed_microsimulation(
    dataset=str(local_h5_path),
    allow_unmanaged=True,
    spm={"geography_kind": "county"},
)
```

This does not certify the local file. The canonical population release must
preserve the prior native arrays, memberships and weights while adding the
source-backed `is_spm_independent_minor_role` input. Formula-owned measurement
counts, thresholds, geographic factors, SPM resources and poverty outputs must
not be present as input columns; the wrapper validates the input DataFrames
before passing them to the country model. Generic adult/child counts remain
separate. The native source enrichment is not recalibration, and inherited
schema-5 calibration diagnostics cannot be relabeled as schema 6.

The wrapper's native pandas HDF loader accepts files that store only calibrated
`household_weight`. It maps missing person and group weight columns through
native membership IDs in memory, retaining supplied weight columns and the
original row order. Inputs are aligned to country populations by native entity ID,
and calculated outputs are aligned back to those IDs before attaching weights.
Independently shuffled entity tables therefore retain the correct geography and
results. Null or duplicate entity IDs are rejected before weight mapping.
Group weights are not sums of person weights. The file is
opened read-only; missing or ambiguous links raise an error instead of creating
unweighted rows. Core variable/period H5 files use the same mapping.

The packaged 5.3.0 production manifest retains `policyengine-us==1.764.6` and
does not yet certify this integration. Local-wheel tests use an explicitly
uncertified development manifest. Registry publication, a producer-issued data
compatibility certification and final bundle promotion remain separate gates;
measurement provenance alone does not satisfy them.

## Datasets

Microdata is stored as HDF5 on Hugging Face. `ensure_datasets` downloads, caches, and uprates:

```python
datasets = pe.us.ensure_datasets(
    years=[2024, 2026],
    data_folder="./data",  # local cache directory
)
dataset = datasets["populace_us_2024_2026"]
```

The default US dataset is **Populace US 2024** — a Populace-built dataset
calibrated to IRS, CMS, SNAP, Census, and other administrative totals. The
current UK certified default is **Enhanced FRS 2024–25**, supplied by
`policyengine-uk-data`. **Populace UK 2023** remains available as a named,
non-default bundle dataset.

PolicyEngine.py obtains the repository type, immutable revision, and SHA-256
from the installed release bundle. An existing file in the configured data
directory is reused only after hash verification.

List datasets already known to the country:

```python
pe.us.load_datasets()  # or pe.uk.load_datasets()
```

### US local-area dataset

Alongside the certified national default, the bundle registers a **non-default**
US dataset for finer geographic work: `populace_us_2024_acs_local`. It is a
Populace US 2024 build of roughly **1.6 million households** on an **ACS 2024
multispine**, with each household **PUMA-assigned** to a 119th-Congress
congressional district, county, and state, and calibrated to **state
administrative totals and state and congressional-district population**. Its
release gate summary records **four reviewed limitations**, so read that gate
summary before relying on it. It ships in its own immutable release and is never
selected implicitly — you load it by name.

Two-line load:

```python
import policyengine as pe

sim = pe.us.managed_microsimulation(dataset="populace_us_2024_acs_local")
```

Or materialize it as a `PolicyEngineUSDataset` for `Simulation`:

```python
datasets = pe.us.ensure_datasets(datasets=["populace_us_2024_acs_local"], years=[2024])
dataset = datasets["populace_us_2024_acs_local_2024"]
```

Because this file carries PUMA-assigned district, county, and state identifiers
calibrated to state and congressional-district population, **state and
congressional-district breakdowns should filter this dataset** rather than the
national default. Filter it with the same `state_fips` /
`congressional_district_geoid` row filters used elsewhere (see
[Regional analysis](regions.md)):

```python
from policyengine.core import Simulation
from policyengine.core.scoping_strategy import RowFilterStrategy

ca = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.us.model,
    scoping_strategy=RowFilterStrategy(variable_name="state_fips", variable_value=6),
)
```

### UK private data and raw h5 access

UK population data uses licensed Family Resources Survey inputs. The default
UK release bundle points to the private
`policyengine/policyengine-uk-data-private` Hugging Face repository. Set
`HUGGING_FACE_TOKEN` to a token from a Hugging Face account with access:

```bash
export HUGGING_FACE_TOKEN=hf_...
```

For `policyengine.py` analyses, use the logical dataset name from the release
bundle. `ensure_datasets` resolves it to the pinned private Hugging Face file,
downloads it, caches it locally, and creates year-specific uprated datasets:

```python
import policyengine as pe
from policyengine.core import Simulation

datasets = pe.uk.ensure_datasets(
    datasets=["enhanced_frs_2024_25"],
    years=[2026],
    data_folder="./data",
)
dataset = datasets["enhanced_frs_2024_25_2026"]

simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.uk.model,
)
simulation.run()
```

To materialize the raw certified artifact without creating uprated yearly
datasets, use PolicyEngine.py's bundle API:

```python
from policyengine.provenance import materialize_dataset

result = materialize_dataset(
    "uk",
    "enhanced_frs_2024_25",
)

print(result.path)
print(result.bundle_dataset.sha256)
```

The bundle API uses the repository type recorded in the bundle, so callers do
not need repository-specific download logic. Authentication or authorization
failures are reported directly and do not cause a retry against another
repository type.

## Simulations

A `Simulation` needs a dataset, a tax-benefit model version, and optionally a policy (reform):

```python
baseline = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.us.model,
)

reformed = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.us.model,
    policy={"gov.irs.credits.ctc.amount.base[0].amount": 3_000},
)
```

`policy=` accepts the same flat `{"param.path": value}` dict shape as `pe.us.calculate_household(reform=...)`, or a `Policy` object with explicit `ParameterValue` entries. Scale parameters use bracket indexing — see [Reforms](reforms.md).

## Outputs

Every output has the same lifecycle: instantiate with the simulation(s) and configuration, call `.run()`, read the typed result fields.

```python
from policyengine.outputs import (
    Aggregate,
    AggregateType,
    ChangeAggregate,
    ChangeAggregateType,
)

snap_cost = Aggregate(
    simulation=baseline,
    variable="snap",
    aggregate_type=AggregateType.SUM,
)
snap_cost.run()

budget = ChangeAggregate(
    baseline_simulation=baseline,
    reform_simulation=reformed,
    variable="household_net_income",
    aggregate_type=ChangeAggregateType.SUM,
)
budget.run()
```

See [Outputs](outputs.md) for the full catalog.

## Memory and performance

A full Populace US microsimulation uses roughly 4 GB of memory and takes 15-30 seconds on a laptop. For parameter sweeps, reuse the baseline:

```python
baseline = Simulation(dataset=dataset, tax_benefit_model_version=pe.us.model)
for amount in [0, 1_000, 2_000, 3_000]:
    reformed = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        policy={"gov.irs.credits.ctc.amount.base[0].amount": amount},
    )
    # each iteration runs only the reform
```

Smaller custom H5 datasets can be passed explicitly for testing:

```python
datasets = pe.us.ensure_datasets(
    datasets=["/path/to/smoke_test_populace_us_2024.h5"],
    years=[2026],
    allow_unmanaged=True,
)
```

These run in seconds and are fine for integration tests. Don't use them for production analysis — the weights are not calibration-tuned.

## Managed microsimulation

`managed_microsimulation` constructs a country-package `Microsimulation` pinned to the `policyengine.py` release bundle (so the dataset selection is certified, not ad-hoc):

```python
from policyengine.tax_benefit_models.us import managed_microsimulation

sim = managed_microsimulation()
# `sim` is a policyengine_us.Microsimulation — use its API directly
```

Pass `allow_unmanaged=True` with a custom `dataset=` to opt out of the release
bundle. Explicit local paths and Hugging Face URIs remain supported in this
mode. GCS dataset URIs are not supported.

For managed simulations, `sim.policyengine_bundle` records the actual source
package, repository type, revision, verified SHA-256, and local path.

## Pinned model versions

Every `policyengine` release pins specific country-model and country-data versions so results are reproducible. `pe.us.model` and `pe.uk.model` expose the pinned `TaxBenefitModelVersion`.

If the installed country-package version doesn't match the pinned manifest, `managed_microsimulation` warns. For strict reproducibility, pin country packages to the versions the `policyengine` release was built against — see [Release bundles](release-bundles.md).

## Next

- [Outputs](outputs.md) — catalog of typed output classes
- [Impact analysis](impact-analysis.md) — full baseline-vs-reform in one call
- [Regions](regions.md) — sub-national analysis
