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

A `YYYY-MM-DD` key is an effective date: its value applies from that date until the next date in the same parameter's reform schedule. If no later value follows, the wrapper emits an interval ending on December 31, 2100.

Use `YYYY-MM-DD.YYYY-MM-DD` for an inclusive interval. For example, this UK reform applies for fiscal year 2027 only:

```python
reform = {
    "gov.hmrc.income_tax.rates.uk[0].rate": {
        "2027-04-06.2028-04-05": 0.21,
    },
}
```

`Simulation(policy=...)`, `Simulation(dynamic=...)`, and UK `calculate_household(reform=...)` accept these two date formats and reject an interval whose end precedes its start. They reject bare years such as `"2027"` or `2027`, because policyengine-uk reads them as fiscal year 2027 only, while policyengine-core's `Reform.from_dict` reads them as from 2027 onward. Use `"2027-04-06.2028-04-05"` for one UK fiscal year or `"2027-01-01"` for an effective date. The US household route retains its country package's period-key handling.

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
    "gov.irs.income.tax.rate[0]": 0.12,  # first bracket rate
    "gov.irs.income.tax.threshold[1]": 50_000,  # second bracket threshold
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

## Behavioural responses: UK capital gains

policyengine-uk realises capital gains in response to any reform that changes
a person's marginal rate on gains. From policyengine-uk {X}, pinned by
policyengine.py {Y}, the default is a retention-rate elasticity of 1.0. Each
person's realised gains scale by $((1 - t_1) / (1 - t_0))^{e}$, where $t_0$
and $t_1$ are their marginal rates on gains without and with the reform. Gains
qualifying for Business Asset Disposal Relief take the same 1.0. Before, the
elasticity was 0, so a CGT reform was costed statically unless the caller set
an elasticity.

For a marginal rate on gains rising from 24% to 45%, realised gains scale by
$0.55 / 0.76 \approx 0.7237$. A marginal tax rate elasticity of $-0.7$, a
different convention, gives $(0.45 / 0.24)^{-0.7} \approx 0.6440$: the two
are not interchangeable.

- **Who is affected.** Any reform that moves someone's marginal rate on gains
  is affected. That includes CGT rates, and also income tax bands and
  allowances, because gains are taxed on top of income. Results without a
  reform are unchanged.
- **The static costing.** Set the elasticities to zero for the years you run,
  as below:
  - on `Simulation`, pass them as `dynamic=`;
  - on `calculate_household`, merge them into `reform=`;
  - on `managed_microsimulation`, merge them into `reform=`, whose keys
    policyengine-uk reads itself.
- **Sensitivities.** The elasticity can be 0.5 or 2.0, the range CenTax
  consider. For the OBR's elasticities, set it to 3.6 and
  `separate_badr_elasticity` to true; `badr_elasticity` stays 1.4. That
  compares elasticities, not the OBR's full costing.
- **The marginal tax rate convention.** An `mtr_elasticity` set on its own
  applies alone in its periods, with a `CapitalGainsResponseWarning`. Setting
  `elasticity` to 0 for the same periods silences it. Setting both to nonzero
  values raises an error.
- **Precedence.** A dynamic's settings win over a policy's. With a policy
  modifier, the dynamic's values are written after the modifier, onto the
  annualised parameters, where a value dated after 1 January misses that year.
  Date them from 1 January.
- **Both sides of a comparison.** Set the same `dynamic` on the baseline and
  the reform. A response set on the reform side only also answers the
  baseline's policy, since each simulation's response is measured against
  current law.
- **The assumption's limits.** CenTax's 1.0 is a medium-term value for a
  package that also reforms the base and adjusts for income shifted between
  taxes. For a change to rates alone their reasoning points higher, and a
  first-year response is likely larger, so the default can overstate what a
  rate rise raises. Income tax on shifted income is not added back. See
  [the methodology page](methodology/uk-capital-gains-responses.md).

```python
RESPONSES = "gov.simulation.capital_gains_responses"
EVERY_YEAR = "2000-01-01.2100-12-31"
static = {
    f"{RESPONSES}.elasticity": {EVERY_YEAR: 0},
    f"{RESPONSES}.mtr_elasticity": {EVERY_YEAR: 0},
    f"{RESPONSES}.separate_badr_elasticity": {EVERY_YEAR: False},
}
static_costing = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.uk.model,
    policy={"gov.hmrc.cgt.higher_rate": {"2027-04-06": 0.45}},
    dynamic=static,
)
```

Every UK run records the response it applied (see
[The UK capital gains realisation response](microsim.md#the-uk-capital-gains-realisation-response)),
and [the methodology page](methodology/uk-capital-gains-responses.md)
explains how the response is measured.

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
