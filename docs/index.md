---
title: "policyengine"
---

`policyengine` is the Python wrapper for PolicyEngine's tax-benefit microsimulation models. One package for both single-household calculations and population-scale microsimulation, US and UK.

## Install

```bash
pip install policyengine[us]                 # US rules
pip install policyengine[uk]                 # UK rules
pip install policyengine[us,uk]              # both
```

## Minimal example

```python
import policyengine as pe

result = pe.us.calculate_household(
    people=[{"age": 35, "employment_income": 60_000}],
    tax_unit={"filing_status": "SINGLE"},
    household={"state_code": "CA"},
    year=2026,
)

result.tax_unit.income_tax
result.household.household_net_income
```

## Where to go next

| If you want to | Go to |
|---|---|
| Install and run your first calculation | [Getting started](getting-started.md) |
| Compute taxes and benefits for one family | [Households](households.md) |
| Express a policy change | [Reforms](reforms.md) |
| Produce population estimates (budget cost, poverty) | [Microsimulation](microsim.md) |
| See the full catalog of typed outputs | [Outputs](outputs.md) |
| Run the canonical baseline-vs-reform bundle | [Impact analysis](impact-analysis.md) |
| Break results down by state, constituency, district | [Regions](regions.md) |
| Understand US vs UK differences | [Countries](countries.md) |
| Build publication-ready charts | [Visualisation](visualisation.md) |
| Pin a reproducible model-plus-data version | [Release bundles](release-bundles.md) |
| See a full worked script | [Examples](examples.md) |
| Develop against the source | [Development](dev.md) |
