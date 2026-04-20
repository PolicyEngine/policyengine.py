---
title: "Reforms"
---

A reform is a change to the rules used in a calculation. PolicyEngine supports two kinds: **parametric** (adjust a parameter value) and **structural** (swap or subclass a rule formula).

## Parametric reforms

A dict of parameter path → new value. The same shape works for `calculate_household`, `Simulation`, and the output helpers.

```python
reform = {
    "gov.irs.credits.ctc.amount.adult_dependent": 1_000,
}

pe.us.calculate_household(..., reform=reform)
```

Scalar values are treated as effective on January 1 of the simulation year and onward.

### Time-varying

```python
reform = {
    "gov.irs.credits.ctc.amount.adult_dependent": {
        "2026-01-01": 1_000,
        "2028-01-01": 2_000,
    },
    "gov.irs.credits.eitc.phase_out.rate[0]": {
        "2026-01-01": 0.08,
    },
}
```

Dates that haven't been passed yet become "from this date onward." Earlier dates replace the baseline schedule.

### Multiple changes

Any number of parameter paths in the same dict compose into one reform:

```python
reform = {
    "gov.irs.credits.ctc.amount.adult_dependent": 1_000,
    "gov.irs.credits.eitc.phase_out.rate[0]": 0.08,
    "gov.states.ca.tax.income.credits.eitc.max_amount": 500,
}
```

### Where parameters live

Every parameter has a canonical path that matches the YAML directory structure in the country model. `gov.irs.credits.ctc.amount.adult_dependent` corresponds to `policyengine_us/parameters/gov/irs/credits/ctc/amount/adult_dependent.yaml`.

An auto-generated parameter reference is pending; for now, browse the YAML tree in the country model repository (e.g. `policyengine-us/policyengine_us/parameters/`), or type-error your way there — an unknown path raises with suggestions.

### Scale and array parameters

Scale parameters (brackets with thresholds and amounts) are addressed by bracket index:

```python
reform = {
    "gov.irs.income.tax.rate[0]": 0.12,   # first bracket rate
    "gov.irs.income.tax.threshold[1]": 50_000,  # second bracket threshold
}
```

## Structural reforms

For rule changes that can't be expressed as a parameter change — swapping one formula for another, adding a variable, removing a program — subclass the country model:

```python
from policyengine.tax_benefit_models.us import PolicyEngineUS, us_latest


class MyReform(PolicyEngineUS):
    version = us_latest.version

    def __init__(self):
        super().__init__()
        self.neutralize_variable("eitc")
```

Pass the reformed model to `Simulation`:

```python
sim = pe.Simulation(model=MyReform(), year=2026)
```

`calculate_household` does not yet accept structural reforms directly — use `Simulation` or the country-specific `managed_microsimulation` context.

## Combining parametric and structural

Pass a parametric reform to the structural-reform constructor:

```python
sim = pe.Simulation(
    model=MyReform(),
    reform={"gov.irs.credits.ctc.amount.adult_dependent": 1_000},
    year=2026,
)
```

## Validating a reform before you run it

The parameter catalog is known at import time. If a path is wrong, the call raises *before* starting the simulation with a suggested path.

For time-varying reforms, the effective dates are checked against the parameter's defined start and end. A date before the parameter started or after a defined end date raises.

## Reform worked examples

- [Economic impact analysis](impact-analysis.md) — full baseline-vs-reform workflow with population estimates.
- [Examples](examples.md) — runnable scripts for reform scenarios in `examples/`.
