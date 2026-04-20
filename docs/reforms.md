---
title: "Reforms"
---

A reform is a change to the rules used in a calculation. PolicyEngine supports two kinds: **parametric** (adjust a parameter value) and **structural** (swap or subclass a rule formula).

## Parametric reforms

A dict of parameter path → new value. The same shape works for `calculate_household` (`reform=`) and `Simulation` (`policy=`).

```python
reform = {
    "gov.irs.credits.ctc.amount.adult_dependent": 1_000,
}

pe.us.calculate_household(..., reform=reform)
```

Scalar values are treated as effective January 1 of the simulation year and onward.

### Time-varying

```python
reform = {
    "gov.irs.credits.ctc.amount.adult_dependent": {
        "2026-01-01": 1_000,
        "2028-01-01": 2_000,
    },
}
```

Dates that haven't passed become "from this date onward." Earlier dates replace the baseline schedule.

### Multiple changes

Any number of paths in the same dict compose into one reform:

```python
reform = {
    "gov.irs.credits.ctc.amount.adult_dependent": 1_000,
    "gov.irs.credits.eitc.phase_out.rate[0]": 0.08,
    "gov.states.ca.tax.income.credits.eitc.max_amount": 500,
}
```

### Scale and array parameters

Scale parameters (brackets with thresholds and amounts) are addressed by bracket index:

```python
reform = {
    "gov.irs.income.tax.rate[0]": 0.12,               # first bracket rate
    "gov.irs.income.tax.threshold[1]": 50_000,        # second bracket threshold
    "gov.irs.credits.ctc.amount.base[0].amount": 3_000,
}
```

### Where parameters live

Every parameter has a canonical path matching the YAML directory structure in the country model. `gov.irs.credits.ctc.amount.adult_dependent` corresponds to `policyengine_us/parameters/gov/irs/credits/ctc/amount/adult_dependent.yaml`.

An auto-generated parameter reference is a planned addition; for now, browse the YAML tree in the country-model repository or rely on the error-message suggestions — an unknown path raises with the closest match.

## Parametric reforms in microsimulation

Same dict, different keyword name:

```python
from policyengine.core import Simulation

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

## Structural reforms

For rule changes that can't be expressed as a parameter change — swapping a formula, adding a variable, neutralising a program — drop down to the underlying country package. Both `policyengine_us` and `policyengine_uk` expose `Reform.from_dict(...)` and class-based reforms with overridable formulas; use them directly and run the simulation via `managed_microsimulation` (or by constructing a country-package `Microsimulation` yourself).

```python
from policyengine_us import Microsimulation
from policyengine_us.model_api import Reform

class NeutralizeEITC(Reform):
    def apply(self):
        self.neutralize_variable("eitc")

sim = Microsimulation(reform=NeutralizeEITC)
```

The current `policyengine.py` surface (`Simulation`, `calculate_household`) accepts parametric reforms only.

## Validating a reform before you run it

The parameter catalog is known at import time. Wrong paths raise before the simulation starts, with the closest-matching path.

For time-varying reforms, effective dates are checked against the parameter's defined start and end. A date before the parameter existed raises.

## Worked examples

- [Impact analysis](impact-analysis.md) — baseline-vs-reform with population estimates
- [Examples](examples.md) — runnable scripts for reform scenarios in `examples/`
