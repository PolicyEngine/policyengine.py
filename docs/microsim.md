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

`Simulation.ensure()` loads a cached result if one exists, or runs and caches on miss. Call `Simulation.run()` explicitly if you want to bypass the cache. A UK simulation's explicit capital gains response settings are part of its cache and saved-output identity; see [The UK capital gains realisation response](#the-uk-capital-gains-realisation-response).

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
the 2022–2036 artifact horizon and explicit geography errors. No provider or
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

**Legacy SPM sources (backward compatibility).** Some certified US sources
predate SPM declarations, for example the ACS-local Build O release. For those
sources, .py derives the declarations from evidence they carry, following
Census's ACS SPM methodology, which measures the household population only:

- ACS group-quarters SPM units are outside the SPM measurement. Their SPM
  thresholds, resources and poverty indicators are missing (NaN).
- Poverty indicators on those sources are floats: 1.0, 0.0, or NaN for "not
  measured".
- Poverty rates count measured people only. A group with nobody measured has
  a rate of `None`, not 0.
- The sources' ASEC and PUF records take the certified SPM independence role
  from the national release.

Ordinary tax, benefit and income results are unchanged. Outputs record the
declarations they used under `legacy_spm_declarations`. See
[the runbook](engineering/runbooks/us-legacy-spm-sources.md).

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
current UK certified default is **Microcosm UK 2024–25**, a Microcosm build
calibrated to HMRC, DWP, OBR and other administrative totals; constituency and
local-authority regions use its local-area release. **Enhanced FRS 2024–25**
(`enhanced_frs_2024_25`, policyengine-uk-data 1.58.1) and **Populace UK 2023**
remain available as named, non-default bundle datasets.

PolicyEngine.py obtains the repository type, immutable revision, and SHA-256
from the installed release bundle. An existing file in the configured data
directory is reused only after hash verification.

List datasets already known to the country:

```python
pe.us.load_datasets()  # or pe.uk.load_datasets()
```

### US local-area dataset

Alongside the certified national default, the bundle registers a US dataset for
finer geographic work: `populace_us_2024_acs_local`. It is a
Populace US 2024 build of roughly **1.6 million households** on an **ACS 2024
multispine**, with each household **PUMA-assigned** to a 119th-Congress
congressional district, county, and state, and calibrated to **state
administrative totals and state and congressional-district population**. Its
release validation summary records **four reviewed limitations**, so read that
summary before relying on it. It ships in its own immutable release. State and
congressional-district region simulations select it through the bundle's
`region_datasets` metadata; direct microsimulations can still load it by name.

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
UK release bundle points to the private `policyengine/populace-uk-private`
Hugging Face repository, and the Enhanced FRS datasets to
`policyengine/policyengine-uk-data-private`. Set `HUGGING_FACE_TOKEN` to a
token from a Hugging Face account with access:

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
    datasets=["microcosm_uk_2024_25"],
    years=[2026],
    data_folder="./data",
)
dataset = datasets["microcosm_uk_2024_25_2026"]

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
    "microcosm_uk_2024_25",
)

print(result.path)
print(result.bundle_dataset.sha256)
```

The bundle API uses the repository type recorded in the bundle, so callers do
not need repository-specific download logic. Authentication or authorization
failures are reported directly and do not cause a retry against another
repository type.

### UK year files and the data year

`ensure_datasets` and `create_datasets` cut one file per requested year from
the projection policyengine-uk makes of the certified dataset. policyengine-uk
takes the first year of a dataset as observed data. Its State Pension formulas
split each person's reported State Pension against that year's legislated
rates, and scale the share to the simulated year's rates, which follow the
triple lock. The projection uprates the reported amount by CPI, so handing a
projected year's tables to policyengine-uk as observed data would make the
State Pension follow CPI instead.

Each projected year file therefore keeps its data year, `dataset.data_year`
(2024 for Microcosm UK 2024–25), and that year's tables,
`dataset.data_year_data`. `Simulation.run()` projects the data year's tables
forward as policyengine-uk does, and uses the file's own tables for the
simulated year. A run of a year file then gives the same result, record by
record, as `policyengine_uk.Microsimulation` on the certified file, with or
without a reform. Keeping the data year's tables doubles a projected file: the
Enhanced FRS 2026 file is 226 MB, against 113 MB for its own tables. A dataset
built in memory without a data year is observed data for its own year, which
is how policyengine-uk treats a single-year dataset.

Row filtering applies to both sets of tables, matched by entity ID. Weight
replacement changes the simulated year's weights only; the data year and the
years between keep national weights. A row-filtered run is a simulation of the
region's households alone, so
variables that policyengine-uk calculates over every household in the
simulation are calculated over the region: income deciles, the relative
poverty median, and `shareholding`, which spreads corporate taxes across
households (PolicyEngine/policyengine.py#567). Variables of a person or
benefit unit that do not depend on those match the national run.

Year files written by earlier releases have no recorded data year.
`ensure_datasets` writes them again and `load_datasets` refuses them. A year
file opened directly, as `PolicyEngineUKDataset(filepath=...)`, is not
checked. A saved UK simulation output records the data year its run anchored
on; `Simulation.load()` refuses an output saved without one, and
`Simulation.ensure()` runs it again.

### The UK capital gains realisation response

policyengine-uk scales realised capital gains in response to a reform, at an
elasticity set under `gov.simulation.capital_gains_responses`. Its default is
the model's, so it can change between policyengine-uk releases. Each UK run
records the response it applied, read after every reform and modifier.

- **Where it is kept.** It is in `simulation.release_bundle["capital_gains_responses"]`,
  the run record's `results.json` and the saved output file.
- **What it holds.**
  - `model`: the policyengine-uk release. Its `source` is `null` for a
    release from a package index; otherwise it says where the install came
    from: a version control commit, an archive's SHA-256, or a local
    directory and whether it is editable.
  - `request`: the caller's explicit settings under that path, in the order
    they apply (policy, then dynamic), and their digest.
  - `resolved`: the assumption the release reports. That is the convention,
    the elasticities for main-rate gains and for gains qualifying for Business
    Asset Disposal Relief, the MTR elasticity, the separate relief switch, and
    whether each is the default, an override or set to zero for an MTR
    elasticity. It is `null` with a release that doesn't report it.
- **Modifiers.** Changes a simulation modifier makes aren't listed under
  `request`, as run records don't describe modifiers. `resolved` reflects them.
  Neither the `storage_id` nor `Simulation.load()` sees them, so two
  simulations with the same `id` whose modifiers set the response differently
  share a saved output. Give such simulations different ids.
- **Identity.** A simulation with explicit settings adds `-cgr-<digest>` to its
  `storage_id`, so its cache entry and saved output are kept apart from runs
  with other settings. The digest covers each setting as given, including
  whether it came from the policy or the dynamic and its dates. So the same
  value set another way, or with an explicit end date instead of none, is
  saved separately.
- **Reuse.** `Simulation.load()` reuses a saved UK output only when its record
  shows the same policyengine-uk release, installed from the same source, and
  the same settings. A branch installed from git or a local directory can
  carry the version number of a published release with another default.
  With policyengine-uk installed from a local directory, editable or not, no
  saved UK output is reused, as its code can change without its version
  changing.
- **Reruns.** Otherwise `load()` raises `StaleOutputError`, and
  `Simulation.ensure()` runs the simulation again and logs the reason at INFO.
  Outputs saved before outputs recorded the response are calculated once
  more, so a job that relies on a warm UK cache takes as long as a cold run
  the first time it runs after the upgrade.

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

A UK managed microsimulation also records, in
`sim.policyengine_bundle["capital_gains_responses"]`, the capital gains
realisation response it applies in each year of its dataset (see
[The UK capital gains realisation response](#the-uk-capital-gains-realisation-response)).
Its `reform=` goes to policyengine-uk unchanged, so no request is listed.
Settings that conflict are recorded as an error for that year, and raise when
the response is calculated.

For managed simulations, `sim.policyengine_bundle` records the actual source
package, repository type, revision, verified SHA-256, and local path.

## Renamed inputs in stored data

A country engine sets a stored column as an input only when it defines a
variable of that name. When policyengine-us renames an input, data written
before the rename keeps the old name, and the engine would skip it.
`policyengine.tax_benefit_models.us.legacy_inputs.LEGACY_INPUT_RENAMES` lists
each such rename; today it holds one entry, `would_claim_wic` →
`takes_up_wic_if_eligible` (the WIC take-up draw, PolicyEngine/microcosm#1026).

Every US load path applies it: `Simulation.run()`, `managed_microsimulation`
and `create_datasets` (and so `ensure_datasets` when it creates year files).
A rename applies when the data stores the old name, the engine does not define
the old name but does define the new one, and the data does not already store
the new name. The new input is then set from the stored values for every month
of every dataset year. The stored table must list the simulation's entity IDs
in the simulation's order, or loading fails rather than attach values to the
wrong people. Only values stored for a whole year are mapped, so a file that
stores the old name for part of a year, and not the new name, is refused. The
mapping turns itself off once the data stores the new name, or if the engine
defines the old name again.

The renames applied are recorded as `{old: new}` (`{}` when none applied):

- `Simulation.run()`: `simulation.output_dataset.metadata["legacy_input_renames"]`,
  also shown as `simulation.release_bundle["legacy_input_renames"]`. It
  includes renames applied when the input year file was cut, so a run over a
  `create_datasets` year file records the rename even though the file already
  stores the new name. A US `save()` writes the record into the output file,
  `load()` restores it, and a run record's `results.json` binds it;
- `managed_microsimulation`: `sim.policyengine_bundle["legacy_input_renames"]`;
- `create_datasets`: each year file, and each returned dataset's
  `metadata["legacy_input_renames"]`.

`{}` means that no stored column was mapped. It does not show that the data
carried the draw: data that stores neither name runs with the new input's
default, which for WIC is full take-up.

A saved US output written before this mapping existed has no record and may
have been calculated without the mapped inputs, so `load()` refuses it, and
`ensure()` runs the simulation again and saves the new output. Saved outputs
are checked only for the record, not for the register they were calculated
under.

### Year files

`create_datasets` stamps each year file, after writing everything else, with
the register it was cut under and a year-file format revision
(`legacy_inputs.YEAR_FILE_STAMP_H5_DATASET`, UTF-8 JSON
`{"register": {old: new, ...}, "revision": 1}`). `ensure_datasets` reuses a
year file only when its stamp equals this release's exactly and its renames
record lists only renames in the stamped register. Otherwise it logs why and
creates the year files again; `load_datasets` refuses the file with the same
reason, which names the renames the file may lack when its register is the
cause. To decide, both read only the stamp and the record, never the tables
or the source dataset. `legacy_inputs.year_file_stamp_problem(path)` returns
the reason, or `None` for a current year file.

A year file is out of date when:

- it has no stamp. Year files that policyengine.py 6.1.1 and earlier cut,
  with policyengine-us 2.x, from a source storing the draw only as
  `would_claim_wic` (such as the certified default) store neither WIC take-up
  name, so the draw is lost from them. Year files written with the renames
  record but before the stamp are cut again once, and so is a year file whose
  write did not finish;
- its register lacks an entry this release has. It may have lost that
  entry's input, as the older files lost the WIC draw;
- its register has an entry this release lacks, or maps an old name to
  another new name. It may store a new name this release's engine does not
  define, and a run skips any column the engine does not define;
- it has another format revision, or its stamp or record cannot be read.

So any change to `LEGACY_INPUT_RENAMES` makes every year file out of date,
and two policyengine.py versions with different registers that share a data
folder cut each other's year files again. `ensure_datasets` raises, rather
than cutting the files again, when a year file cannot be opened for reasons
unrelated to its contents: no permission, a directory at its path, or a lock
held by another process. A year file opened directly, as
`PolicyEngineUSDataset(filepath=...)`, is not checked, and saving it again with
`save()` drops its stamp.

## Pinned model versions

Every `policyengine` release pins specific country-model and country-data versions so results are reproducible. `pe.us.model` and `pe.uk.model` expose the pinned `TaxBenefitModelVersion`.

If the installed country-package version doesn't match the pinned manifest, `managed_microsimulation` warns. For strict reproducibility, pin country packages to the versions the `policyengine` release was built against — see [Release bundles](release-bundles.md).

## Next

- [Outputs](outputs.md) — catalog of typed output classes
- [Impact analysis](impact-analysis.md) — full baseline-vs-reform in one call
- [Regions](regions.md) — sub-national analysis
