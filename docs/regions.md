---
title: "Regional analysis"
---

Sub-national impact breakdowns using geographically-stratified microdata and the `...Impact` output classes.

## US states

Every US dataset includes `state_code` on each household. Use `Aggregate` or `ChangeAggregate` with a filter:

```python
ca_cost = Aggregate(
    variable="snap",
    type=AggregateType.SUM,
    filter="state_code == 'CA'",
).compute(baseline)
```

For all-states-at-once, use `StateImpact`:

```python
from policyengine.outputs import StateImpact

state_impact = StateImpact().compute(baseline, reformed)
# Dict keyed by two-letter state code
```

## US congressional districts

```python
from policyengine.outputs import CongressionalDistrictImpact

impacts = CongressionalDistrictImpact().compute(baseline, reformed)

# Keyed by district ID (e.g. "CA-12")
for district_id, result in impacts.items():
    print(district_id, result.winners_share, result.mean_impact)
```

Requires a district-stratified dataset. The default Enhanced CPS includes district assignments calibrated against district-level ACS population and income distributions.

## UK parliamentary constituencies

```python
from policyengine.outputs import ConstituencyImpact

impacts = ConstituencyImpact().compute(baseline, reformed)
```

Constituency codes follow ONS nomenclature. Requires the constituency-stratified FRS dataset.

## UK local authorities

```python
from policyengine.outputs import LocalAuthorityImpact

impacts = LocalAuthorityImpact().compute(baseline, reformed)
```

## Custom geographies

If you have a geography not covered by the built-in impact classes, compute the underlying variables via `Simulation.calculate` and group them yourself:

```python
households = baseline.calculate("household_net_income").values
reform_households = reformed.calculate("household_net_income").values
geography = baseline.calculate("custom_geography_id").values

import pandas as pd
df = pd.DataFrame({
    "baseline": households,
    "reformed": reform_households,
    "geo": geography,
})
df.groupby("geo")[["baseline", "reformed"]].mean()
```

## Data availability

Not every country has sub-national strata in every dataset. Check `Dataset.geo_fields` for what a given dataset supports:

```python
dataset = pe.us.load_datasets()[0]
dataset.geo_fields        # ["state_code", "congressional_district"]
```
