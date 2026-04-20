---
title: "PolicyEngine"
subtitle: "Tax-benefit microsimulation for Python"
---

Compute household taxes and benefits, simulate reforms, and measure distributional impact — across the US and UK — from a single Python package.

## Install

```bash
pip install policyengine
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
print(result.household.household_net_income)
```

## Where to go

| If you want to… | Start here |
|---|---|
| Compute taxes and benefits for one household | [Households](households.md) |
| Simulate a policy change | [Reforms](reforms.md) |
| Run a population microsimulation | [Microsimulation](microsim.md) |
| Measure a reform's distributional impact | [Impact analysis](impact-analysis.md) |
| See every output type | [Outputs](outputs.md) |
| Look up a variable | Reference (auto-generated catalog, pending) |
| Contribute | [Development](dev.md) |

## What PolicyEngine is

A platform that encodes the tax and benefit rules of a country as Python formulas and YAML parameters, runs them over microdata or single households, and exposes the results through a small set of typed outputs. The country rules live in country-specific packages (`policyengine-us`, `policyengine-uk`); this package wraps them in one API.

Under the hood PolicyEngine combines the rules with calibrated microdata — the enhanced CPS for the US, the enhanced FRS for the UK — and returns weighted population estimates that match administrative totals.

## Citation

Woodruff and Ghenis (2024), *Enhancing Survey Microdata with Administrative Records: A Novel Approach to Microsimulation Dataset Construction*.
