---
title: "Getting started"
---

## Install

```bash
pip install policyengine
```

By default `policyengine` does not bundle country models — install each country's rules alongside:

```bash
pip install policyengine policyengine-us        # US only
pip install policyengine policyengine-uk        # UK only
pip install policyengine policyengine-us policyengine-uk   # both
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

Each `.*` lookup is a regular Python scalar. The result object is typed; IDEs and type-checkers autocomplete attribute names from the country model's variable catalog.

## Apply a reform

```python
reformed = pe.us.calculate_household(
    people=[{"age": 35, "employment_income": 60_000}],
    tax_unit={"filing_status": "SINGLE"},
    year=2026,
    reform={"gov.irs.credits.ctc.amount.adult_dependent": 1_000},
)
```

Reforms are parameter-path → value dicts. For time-varying reforms pass a dict of effective-date strings instead of a scalar:

```python
reform = {
    "gov.irs.credits.ctc.amount.adult_dependent": {
        "2026-01-01": 1_000,
        "2028-01-01": 2_000,
    },
}
```

See [Reforms](reforms.md) for structural changes and multi-year reforms.

## Scale up

A single-household calculator is convenient for policy-walkthroughs and tests. For population estimates of budget cost, distributional impact, and poverty effects, move to [Microsimulation](microsim.md). The API is parallel — `pe.us.calculate_household` and `pe.us.Simulation` accept the same reform dict, so your hypothesis code carries over.

## What you get back

Every calculation returns a typed result object with sections per entity — `person`, `tax_unit`, `spm_unit`, `household`, `family` for the US; `person`, `benunit`, `household` for the UK. Indexing the person list (`result.person[0]`) returns a row for that person. Group-entity lookups (`result.tax_unit`, `result.household`) return the single group the household is organized into.

Every variable defined on the country model is available as an attribute. If you ask for one that doesn't exist, you get an error with the closest available suggestion — no silent zero returns.

## Next

- [Households](households.md) — full reference for `calculate_household`
- [Reforms](reforms.md) — parametric and structural reforms
- [Microsimulation](microsim.md) — population-level analysis
