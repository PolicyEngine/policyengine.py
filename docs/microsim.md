---
title: "Microsimulation"
---

For population-level estimates — budget cost, winners and losers, poverty impact — run a microsimulation over calibrated microdata.

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

## Datasets

Microdata is stored as HDF5 on Hugging Face. `ensure_datasets` downloads, caches, and uprates:

```python
datasets = pe.us.ensure_datasets(
    years=[2024, 2026],
    data_folder="./data",        # local cache directory
)
dataset = datasets["populace_us_2024_2026"]
```

The default US dataset is **Populace US 2024** — a Populace-built dataset calibrated to IRS, CMS, SNAP, Census, and other administrative totals. The UK default is **Populace UK 2023** — a Populace-built Family Resources Survey dataset calibrated to UK administrative targets.

List datasets already known to the country:

```python
pe.us.load_datasets()        # or pe.uk.load_datasets()
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
`policyengine/populace-uk-private` Hugging Face dataset repository. Set
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
    datasets=["populace_uk_2023"],
    years=[2026],
    data_folder="./data",
)
dataset = datasets["populace_uk_2023_2026"]

simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.uk.model,
)
simulation.run()
```

To download the raw h5 artifact directly from Hugging Face, use
`huggingface_hub` and specify `repo_type="dataset"`:

```python
import os
from huggingface_hub import hf_hub_download

path = hf_hub_download(
    repo_id="policyengine/populace-uk-private",
    filename="populace_uk_2023.h5",
    repo_type="dataset",
    token=os.environ["HUGGING_FACE_TOKEN"],
)

print(path)
```

The repository URL is
<https://huggingface.co/datasets/policyengine/populace-uk-private>. A 404 from
the website or `RepositoryNotFoundError` from the Hub API usually means the
browser or token is not authenticated as an account with access, or that the
Hub call omitted `repo_type="dataset"`.

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
    Aggregate, AggregateType,
    ChangeAggregate, ChangeAggregateType,
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

Pass `allow_unmanaged=True` with a custom `dataset=` to opt out of the release bundle.

## Pinned model versions

Every `policyengine` release pins specific country-model and country-data versions so results are reproducible. `pe.us.model` and `pe.uk.model` expose the pinned `TaxBenefitModelVersion`.

If the installed country-package version doesn't match the pinned manifest, `managed_microsimulation` warns. For strict reproducibility, pin country packages to the versions the `policyengine` release was built against — see [Release bundles](release-bundles.md).

## Next

- [Outputs](outputs.md) — catalog of typed output classes
- [Impact analysis](impact-analysis.md) — full baseline-vs-reform in one call
- [Regions](regions.md) — sub-national analysis
