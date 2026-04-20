---
title: "Microsimulation"
---

For population-level estimates — budget cost, winners and losers, poverty impact — run a microsimulation over calibrated microdata.

## Quick example

```python
import policyengine as pe
from policyengine.outputs.aggregate import Aggregate, AggregateType

pe.us.ensure_datasets(
    datasets=["hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"],
    years=[2026],
)

baseline = pe.Simulation(
    country="us",
    dataset="hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5",
    year=2026,
)

total_snap = Aggregate(
    variable="snap",
    type=AggregateType.SUM,
).compute(baseline)
```

## Datasets

Microdata is stored as HDF5 files on Hugging Face. Install once to download and cache:

```python
pe.us.ensure_datasets(
    datasets=["hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"],
    years=[2024, 2026],
)
```

The default US dataset is **Enhanced CPS 2024** — CPS ASEC with IRS SOI tax return records imputed in and calibration weights tuned to match IRS, CMS, SNAP, and other administrative totals. The UK default is **Enhanced FRS** — Family Resources Survey with tax-return microdata fused in and calibration to HMRC and DWP totals.

List all available datasets:

```python
pe.us.load_datasets()        # or pe.uk.load_datasets()
```

## Simulations

A `Simulation` takes a country, a dataset, a year, and an optional reform:

```python
baseline = pe.Simulation(
    country="us",
    dataset="hf://.../enhanced_cps_2024.h5",
    year=2026,
)

reformed = pe.Simulation(
    country="us",
    dataset="hf://.../enhanced_cps_2024.h5",
    year=2026,
    reform={"gov.irs.credits.ctc.amount.adult_dependent": 1_000},
)
```

Each simulation wraps a PolicyEngine country model plus the dataset plus the weight vector.

## Outputs

Outputs are callables that consume a `Simulation` and return a typed result. They cover single-value aggregates, cross-sectional distributions, and geographic breakdowns. See [Outputs](outputs.md).

```python
from policyengine.outputs import (
    Aggregate, AggregateType,
    ChangeAggregate, ChangeAggregateType,
    DecileImpact,
    Poverty,
    Inequality,
)

# Cost of the SNAP program
snap_cost = Aggregate(variable="snap", type=AggregateType.SUM).compute(baseline)

# Reform budget impact
budget = ChangeAggregate(
    variable="household_net_income",
    type=ChangeAggregateType.DIFFERENCE,
).compute(baseline, reformed)
```

## Memory and performance

A full Enhanced CPS microsimulation uses ~4 GB of memory and takes ~15–30 seconds on a laptop. For repeated runs with different reforms, reuse the baseline `Simulation` and construct the reform-only instance on top.

Downsampled datasets are available for testing:

```python
pe.us.ensure_datasets(
    datasets=["hf://policyengine/policyengine-us-data/cps_small_2024.h5"],
    years=[2026],
)
```

These run in seconds and are fine for integration tests. Don't use them for production analysis — the weights are not calibration-tuned.

## Managed microsimulation

If you're orchestrating many reforms, the `managed_microsimulation` context handles dataset prep, cache reuse, and teardown:

```python
from policyengine.us import managed_microsimulation

with managed_microsimulation(year=2026) as sim:
    baseline = Aggregate("snap", AggregateType.SUM).compute(sim)
```

## Pinned model versions

Every release of `policyengine` pins a specific version of each country model, so results are reproducible. `pe.us.model` and `pe.uk.model` expose the pinned `TaxBenefitModelVersion`.

If the installed country package version doesn't match the pinned manifest, `managed_microsimulation` raises a warning with the version gap. For strict reproducibility, pin the country packages to the same versions the `policyengine` release was built against — see [Provenance](release-bundles.md).

## Next

- [Outputs](outputs.md) — catalog of typed output classes
- [Impact analysis](impact-analysis.md) — baseline-vs-reform in one call
- [Regions](regions.md) — sub-national analysis (states, constituencies, districts)
