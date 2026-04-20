# Regions and scoping

The package supports sub-national analysis through a geographic region system. Regions can scope simulations to states, constituencies, congressional districts, local authorities, and cities.

## Region system

### Region

A `Region` represents a geographic area with a unique prefixed code:

| Region type | Code format | Examples |
|---|---|---|
| National | `us`, `uk` | `us`, `uk` |
| State | `state/{code}` | `state/ca`, `state/ny` |
| Congressional district | `congressional_district/{ST-DD}` | `congressional_district/CA-01` |
| Place/city | `place/{ST-FIPS}` | `place/NJ-57000` |
| UK country | `country/{name}` | `country/england` |
| Constituency | `constituency/{name}` | `constituency/Sheffield Central` |
| Local authority | `local_authority/{code}` | `local_authority/E09000001` |

### RegionRegistry

Each model version has a `RegionRegistry` providing O(1) lookups:

```python
import policyengine as pe

registry = pe.us.model.region_registry

# Look up by code
california = registry.get("state/ca")
print(f"{california.label}: {california.region_type}")

# Get all regions of a type
states = registry.get_by_type("state")
print(f"{len(states)} states")

districts = registry.get_by_type("congressional_district")
print(f"{len(districts)} congressional districts")

# Get children of a region
ca_districts = registry.get_children("state/ca")
```

```python
import policyengine as pe

registry = pe.uk.model.region_registry

# UK countries
countries = registry.get_by_type("country")
for c in countries:
    print(f"{c.code}: {c.label}")
```

### Region counts

**US:** 1 national + 51 states (inc. DC) + 436 congressional districts + 333 census places = 821 regions

**UK:** 1 national + 4 countries. Constituencies and local authorities are available via extended registry builders.

## Scoping strategies

Scoping strategies control how a national dataset is narrowed to represent a sub-national region. They are applied during `Simulation.run()`, before the microsimulation calculation.

### RowFilterStrategy

Filters dataset rows where a household-level variable matches a specific value. Used for UK countries and US places/cities.

```python
from policyengine.core import Simulation
from policyengine.core.scoping_strategy import RowFilterStrategy

# Simulate only California households
simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.us.model,
    scoping_strategy=RowFilterStrategy(
        variable_name="state_fips",
        variable_value=6,  # California FIPS code
    ),
)
simulation.run()
```

This removes all non-California households from the dataset before running the simulation. The remaining household weights still reflect California's population.

```python
# UK: simulate only England
simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.uk.model,
    scoping_strategy=RowFilterStrategy(
        variable_name="country",
        variable_value="ENGLAND",
    ),
)
```

### WeightReplacementStrategy

Replaces household weights from a pre-computed weight matrix stored in Google Cloud Storage. Used for UK constituencies and local authorities, where the weight matrix (shape: N_regions x N_households) reweights all households to represent each region's demographics.

```python
from policyengine.core.scoping_strategy import WeightReplacementStrategy

simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.uk.model,
    scoping_strategy=WeightReplacementStrategy(
        weight_matrix_bucket="policyengine-uk-data",
        weight_matrix_key="parliamentary_constituency_weights.h5",
        lookup_csv_bucket="policyengine-uk-data",
        lookup_csv_key="constituencies_2024.csv",
        region_code="Sheffield Central",
    ),
)
```

Unlike row filtering, weight replacement keeps all households but assigns region-specific weights. This is more statistically robust for small geographic areas where filtering would leave too few households.

## Geographic impact outputs

The package provides output types that compute per-region metrics across all regions simultaneously.

### CongressionalDistrictImpact (US)

Groups households by `congressional_district_geoid` and computes weighted average and relative income changes per district.

```python
from policyengine.outputs.congressional_district_impact import (
    compute_us_congressional_district_impacts,
)

baseline_sim.run()
reform_sim.run()

impact = compute_us_congressional_district_impacts(baseline_sim, reform_sim)

for d in impact.district_results:
    print(f"District {d['state_fips']:02d}-{d['district_number']:02d}: "
          f"avg change=${d['average_household_income_change']:+,.0f}, "
          f"relative={d['relative_household_income_change']:+.2%}")
```

**Result fields per district:**
- `district_geoid`: Integer SSDD (state FIPS * 100 + district number)
- `state_fips`: State FIPS code
- `district_number`: District number within state
- `average_household_income_change`: Weighted mean change
- `relative_household_income_change`: Weighted relative change
- `population`: Weighted household count

### ConstituencyImpact (UK)

Uses pre-computed weight matrices (650 x N_households) to compute per-constituency income changes without filtering.

```python
from policyengine.outputs.constituency_impact import (
    compute_uk_constituency_impacts,
)

impact = compute_uk_constituency_impacts(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    weight_matrix_path="parliamentary_constituency_weights.h5",
    constituency_csv_path="constituencies_2024.csv",
    year="2025",
)

for c in impact.constituency_results:
    print(f"{c['constituency_name']}: "
          f"avg change={c['average_household_income_change']:+,.0f}")
```

**Result fields per constituency:**
- `constituency_code`, `constituency_name`: Identifiers
- `x`, `y`: Hex map coordinates
- `average_household_income_change`, `relative_household_income_change`
- `population`: Weighted household count

### LocalAuthorityImpact (UK)

Works identically to `ConstituencyImpact` but for local authorities (360 x N_households weight matrix).

```python
from policyengine.outputs.local_authority_impact import (
    compute_uk_local_authority_impacts,
)

impact = compute_uk_local_authority_impacts(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    weight_matrix_path="local_authority_weights.h5",
    local_authority_csv_path="local_authorities_2024.csv",
    year="2025",
)
```

## Using regions with `economic_impact_analysis()`

Scoping strategies compose naturally with the full analysis pipeline:

```python
from policyengine.core.scoping_strategy import RowFilterStrategy

# State-level analysis
baseline_sim = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.us.model,
    scoping_strategy=RowFilterStrategy(
        variable_name="state_fips",
        variable_value=6,  # California FIPS code
    ),
)
reform_sim = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.us.model,
    policy=reform,
    scoping_strategy=RowFilterStrategy(
        variable_name="state_fips",
        variable_value=6,  # California FIPS code
    ),
)

# Full analysis scoped to California
analysis = economic_impact_analysis(baseline_sim, reform_sim)
```
