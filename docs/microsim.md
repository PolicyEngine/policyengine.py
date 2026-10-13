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
(2024 for Enhanced FRS 2024–25), and that year's tables,
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

`create_datasets` names each US year file after its dataset's logical name,
`{data_folder}/{name}_year_{year}.h5`, which drops the revision. Files cut
from every release of a dataset therefore share names. After writing
everything else, it stamps each file with what the file was cut from and under
(`legacy_inputs.YEAR_FILE_STAMP_H5_DATASET`, UTF-8 JSON):

```json
{
  "packages": {"policyengine-core": "3.33.0", "policyengine-us": "2.2.1"},
  "register": {"would_claim_wic": "takes_up_wic_if_eligible"},
  "revision": 2,
  "source": {
    "sha256": "6496cc4393d4d3c6574f76eca231de5898c803b9067645591fd5c4d3e65aee84",
    "uri": "hf://policyengine/populace-us/populace_us_2024.h5@populace-us-2024-spm-20260915"
  }
}
```

- `packages`: the installed policyengine-core and policyengine-us versions.
  The file stores each input as policyengine-us calculates it for that year,
  and policyengine-core uprates an input from its stored year by a
  policyengine-us parameter, so either version can change the file's values;
- `register`: the whole `LEGACY_INPUT_RENAMES` it was cut under;
- `revision`: the year-file format revision;
- `source`: the identity of the dataset it was cut from
  (`dataset_materialization.dataset_source_identity`), in one of three shapes:
  - a bundle dataset: `{"uri", "sha256"}`, the `hf://…@revision` URI the
    bundle pins and the sha256 the local copy was verified against. A
    request of the certified default dataset's own URI selects the bundle
    dataset too;
  - any other explicit Hugging Face URI (`allow_unmanaged=True`): `{"uri"}`,
    the URI as given;
  - a local file (`allow_unmanaged=True`): `{"path", "size", "mtime_ns"}`,
    its resolved path, and its size in bytes and modification time from one
    `stat()`.

`ensure_datasets` reuses a year file only when its stamp equals the one a file
cut now from the requested dataset would carry, and its renames record lists
only renames in the stamped register. Otherwise it logs why and creates the
year files again. `load_datasets` refuses the file with the same reason, which
names the renames the file may lack, the source it was cut from and the
source requested, or the package versions it was cut with and those
installed. `legacy_inputs.year_file_stamp_problem(path, source)` returns the
reason, or `None` for a current year file; `source` is
`dataset_materialization.requested_dataset_source_identity("us", dataset)`.

Deciding stays cheap. Both functions read only each year file's stamp and
record, never its tables. They identify the requested source without
downloading or reading it: a bundle dataset by its bundle manifest entry, an
explicit URI by the URI, and a local file by its file-system metadata.
Package versions come from the installed distributions' metadata, so
policyengine-us is not imported.

`create_datasets` records the source file's size and modification time right
after materializing it (`dataset_materialization.dataset_source_snapshot`),
and checks them again once the year files are written. A downloaded file is
also hashed again, against the sha256 a bundle dataset was verified against
or an explicit URI was downloaded with (`dataset_source_change`). Another
process can replace a file in a shared data folder, for example by
materializing another release of the same dataset, or another file with the
same name, there. If the source changed, the year files are left unstamped,
so they are cut again, and `DatasetMaterializationError` is raised.

Requested datasets that are different sources with one name, such as two
revisions of one Hugging Face file or two local files called `pop.h5`, would
write the same year files. `ensure_datasets`, `load_datasets` and
`create_datasets` refuse them with `ValueError`; request them in separate
calls with separate data folders.

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
- it was cut from another source. The bundle may have re-pinned the dataset
  to another revision or sha256. The replacement of
  `populace_us_2024_acs_local` (PolicyEngine/microcosm#1154) is one such
  re-pin. A local file may have been rewritten, or another file with the
  same name may have been requested;
- it was cut with another policyengine-core or policyengine-us version;
- it has another format revision, or its stamp or record cannot be read.

So any change to `LEGACY_INPUT_RENAMES`, a re-pinned dataset or a new package
version makes the affected year files out of date. Two environments with
different registers or package versions that share a data folder cut each
other's year files again.

The source check has limits that follow from not reading the source:

- a local file is compared by path, size and modification time, the quick
  check `rsync` makes by default. Touching or copying the file cuts the
  year files again. A rewrite that keeps the size and the modification time
  (restored with `touch -r`, or landing within the file system's timestamp
  resolution) is not detected;
- an explicit Hugging Face URI is compared as a string. Pin it to a commit
  (`hf://owner/repo/file.h5@<commit>`): a URI without a revision, or with a
  branch, names whatever the branch holds when the files are cut;
- the source is checked when the year files are stamped, not as it is read.
  A source swapped out while it is loaded and then restored, bytes and
  times (renamed aside and back, or copied back with `cp -p`), is not
  noticed, whatever its kind. A local file modified, or replaced by a file of
  the same size, within one tick of the file system's timestamp resolution
  is not noticed either; a downloaded file is also checked by its sha256;
- an editable or source install of policyengine-us keeps its version string
  while its code changes, so its year files are not cut again;
- `create_datasets` takes no lock, so two processes cutting the same year
  files at once write them at the same time. Cut year files in one process
  at a time per data folder.

`ensure_datasets` raises, rather than cutting the files again, when a year
file cannot be opened for reasons unrelated to its contents: no permission, a
directory at its path, or a lock held by another process. A year file opened
directly, as `PolicyEngineUSDataset(filepath=...)`, is not checked, and saving
it again with `save()` drops its stamp.

## Pinned model versions

Every `policyengine` release pins specific country-model and country-data versions so results are reproducible. `pe.us.model` and `pe.uk.model` expose the pinned `TaxBenefitModelVersion`.

If the installed country-package version doesn't match the pinned manifest, `managed_microsimulation` warns. For strict reproducibility, pin country packages to the versions the `policyengine` release was built against — see [Release bundles](release-bundles.md).

## Next

- [Outputs](outputs.md) — catalog of typed output classes
- [Impact analysis](impact-analysis.md) — full baseline-vs-reform in one call
- [Regions](regions.md) — sub-national analysis
