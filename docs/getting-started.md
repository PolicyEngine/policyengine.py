---
title: "Getting started"
---

## Install

```bash
pip install policyengine
```

The base install contains the wrapper API. Install each country's rules alongside:

```bash
pip install policyengine[us]                # US
pip install policyengine[uk]                # UK
pip install policyengine[us,uk]             # both
```

Country modules (`pe.us`, `pe.uk`) are only importable if the matching country package is installed.

## Compute one household

```python
import policyengine as pe

result = pe.us.calculate_household(
    people=[{"age": 35, "employment_income": 60_000}],
    tax_unit={"filing_status": "SINGLE"},
    household={"state_code": "CA"},
    year=2026,
)

result.tax_unit.income_tax
result.tax_unit.eitc
result.household.household_net_income
```

Each `.*` lookup is a regular Python scalar. The result is a typed `HouseholdResult` with entity sections (`person[i]`, `tax_unit`, `spm_unit`, `household`) populated from every variable in the country model.

## Apply a reform

Reforms are parameter-path → value dicts:

```python
reformed = pe.us.calculate_household(
    people=[{"age": 35, "employment_income": 60_000}],
    tax_unit={"filing_status": "SINGLE"},
    year=2026,
    reform={"gov.irs.credits.ctc.amount.adult_dependent": 1_000},
)
```

For values effective on specific dates, pass a nested dict:

```python
reform = {
    "gov.irs.credits.ctc.amount.adult_dependent": {
        "2026-01-01": 1_000,
        "2028-01-01": 2_000,
    },
}
```

Scale parameters are addressed by bracket index:

```python
reform = {"gov.irs.credits.ctc.amount.base[0].amount": 3_000}
```

See [Reforms](reforms.md) for structural reforms and the `Simulation.policy=` counterpart for population analysis.

## Scale up

For population estimates — budget cost, distributional impact, poverty — move to a microsimulation over calibrated microdata. The reform dict carries over unchanged; only the constructor changes.

```python
from policyengine.core import Simulation

datasets = pe.us.ensure_datasets(
    datasets=["hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"],
    years=[2026],
)
dataset = datasets["enhanced_cps_2024_2026"]

baseline = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.us.model,
)
reformed = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.us.model,
    policy={"gov.irs.credits.ctc.amount.adult_dependent": 1_000},
)
```

(Note: `reform=` for household calc, `policy=` for `Simulation` — same dict shape.)

## What you get back

Every calculation returns a typed result with sections per entity:

- **US**: `person`, `family`, `marital_unit`, `tax_unit`, `spm_unit`, `household`
- **UK**: `person`, `benunit`, `household`

Person-level lookups index the list: `result.person[0].age`. Group-entity lookups don't: `result.tax_unit.income_tax`.

Unknown variable names raise with suggestions — no silent zero returns.

## Next

- [Households](households.md) — full reference for `calculate_household`
- [Reforms](reforms.md) — parametric and structural reforms
- [Microsimulation](microsim.md) — population-level analysis
