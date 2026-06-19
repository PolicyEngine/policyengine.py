---
title: "Regional analysis"
---

Sub-national breakdowns: state / district filters on any output, plus dedicated classes for US congressional districts and UK constituencies / local authorities.

## US states

`state_code` is an Enum variable on every household (values `"CA"`, `"TX"`, ...). Pass it as a filter on any `Aggregate` or `ChangeAggregate`:

```python
from policyengine.outputs import Aggregate, AggregateType

ca_snap = Aggregate(
    simulation=baseline,
    variable="snap",
    aggregate_type=AggregateType.SUM,
    filter_variable="state_code",
    filter_variable_eq="CA",
)
ca_snap.run()
```

Each state is a region in the US registry, with its own dataset:

```python
states = pe.us.model.region_registry.get_by_type("state")
for region in states:
    print(region.code, region.label, region.dataset_path)
```

For state-specific datasets (rather than filtering a national one), pass `scoping_strategy=region.scoping_strategy` or resolve the dataset path directly.

## US congressional districts

```python
from policyengine.outputs import compute_us_congressional_district_impacts

impacts = compute_us_congressional_district_impacts(
    baseline_simulation=baseline,
    reform_simulation=reform,
)
for row in impacts.district_results:
    print(row["district_geoid"], row["avg_change"], row["winner_percentage"])
```

`district_geoid` is the SSDD integer (state FIPS × 100 + district number). Requires a dataset with `congressional_district_geoid` populated — the default enhanced CPS does.

## UK parliamentary constituencies

Constituency-level impacts group household output rows by the longwise
`constituency_code_oa` column carried by the dataset. If the constituency CSV is
available locally or from the PolicyEngine UK GCS bucket, PolicyEngine uses it
to attach names and map coordinates; otherwise results still compute and use
the code as the label.

```python
from policyengine.outputs import compute_uk_constituency_impacts

impacts = compute_uk_constituency_impacts(
    baseline_simulation=baseline,
    reform_simulation=reform,
)
impacts.constituency_results
```

To force a specific metadata file, pass `constituency_csv_path`. To avoid
downloading metadata and fall back to code-only labels, pass
`download_missing_assets=False`. The legacy `weight_matrix_path` and `year`
arguments are accepted for backward compatibility but ignored.

## UK local authorities

```python
from policyengine.outputs import compute_uk_local_authority_impacts

impacts = compute_uk_local_authority_impacts(
    baseline_simulation=baseline,
    reform_simulation=reform,
)
impacts.local_authority_results
```

Local-authority impacts follow the same longwise pattern using `la_code_oa`.
Pass `local_authority_csv_path` to use a specific metadata CSV, or
`download_missing_assets=False` to skip metadata download and use code-only
labels. The legacy `weight_matrix_path` and `year` arguments are accepted for
backward compatibility but ignored.

## Region registries

`pe.us.model.region_registry` and `pe.uk.model.region_registry` enumerate supported sub-national units:

```python
pe.us.model.region_registry.get_by_type("state")
pe.us.model.region_registry.get_by_type("congressional_district")

pe.uk.model.region_registry.get_by_type("constituency")
pe.uk.model.region_registry.get_by_type("local_authority")
```

Other helpers: `.get(code)` resolves a single region, `.get_children(parent_code)` returns sub-regions, `.get_national()` returns the national region.

## Custom geographies

For a geography not covered by the built-in classes, compute the underlying variables via `Simulation.run()` and group yourself:

```python
import pandas as pd

baseline.run()
reform.run()

baseline_hh = baseline.output_dataset.data.household
reform_hh = reform.output_dataset.data.household

df = pd.DataFrame({
    "baseline": baseline_hh["household_net_income"].values,
    "reform": reform_hh["household_net_income"].values,
    "geo": baseline_hh["custom_geography_id"].values,
    "weight": baseline_hh["household_weight"].values,
})

df["change"] = df["reform"] - df["baseline"]
df.groupby("geo").apply(lambda g: (g["change"] * g["weight"]).sum() / g["weight"].sum())
```

## Scoping datasets to a region

For reforms defined only over a sub-national slice, pass a scoping strategy to `Simulation`. `RowFilterStrategy` keeps only matching households. `WeightReplacementStrategy` is legacy matrix infrastructure and is not used by the UK Populace constituency or local-authority registry.

```python
from policyengine.core.scoping_strategy import RowFilterStrategy

baseline = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.us.model,
    scoping_strategy=RowFilterStrategy(
        variable_name="state_code",
        variable_value="CA",
    ),
)
```

Regions that filter (US places, UK countries, and any region with `region.requires_filter == True`) carry their own `scoping_strategy`. Pull it off the region object rather than reconstructing it:

```python
nyc = pe.us.model.region_registry.get("place/NY-51000")
baseline = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.us.model,
    scoping_strategy=nyc.scoping_strategy,
)
```

US states and congressional districts don't use a scoping strategy — they point to dedicated state- or district-specific datasets via `region.dataset_path`. Pass that dataset to `Simulation` instead.
