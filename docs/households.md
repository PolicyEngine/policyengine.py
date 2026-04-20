---
title: "Households"
---

`pe.us.calculate_household` and `pe.uk.calculate_household` compute every variable in the country model for a single household. Same keyword arguments, different entity structures.

## US

```python
result = pe.us.calculate_household(
    people=[
        {"age": 35, "employment_income": 40_000},
        {"age": 33},
        {"age": 8},
        {"age": 5},
    ],
    tax_unit={"filing_status": "JOINT"},
    household={"state_code": "TX"},
    year=2026,
)
```

### Entities

| Argument | Purpose |
|---|---|
| `people` | List of person dicts. Keys are any person-level variable on the model. |
| `tax_unit` | Tax-unit inputs (e.g. `filing_status`). |
| `spm_unit` | SPM-unit inputs. |
| `household` | Household inputs. `state_code` is essentially always needed. |
| `family` | Family-level inputs. |
| `marital_unit` | Marital-unit inputs. |

All adults default to one shared tax unit and household. For separate tax units (e.g. two adult roommates), construct the `Simulation` directly and set the entity-membership arrays.

## UK

```python
result = pe.uk.calculate_household(
    people=[
        {"age": 35, "employment_income": 50_000},
        {"age": 33, "employment_income": 30_000},
        {"age": 4},
    ],
    benunit={},
    household={},
    year=2026,
)
```

| Argument | Purpose |
|---|---|
| `people` | Person-level inputs. |
| `benunit` | Benefit unit (closest analog to US tax unit — single adult or couple plus their dependent children). |
| `household` | Household-level inputs. |

## Reforms

Pass a `reform` dict of parameter-path to value:

```python
pe.us.calculate_household(
    ...,
    reform={"gov.irs.credits.ctc.amount.adult_dependent": 1_000},
)
```

Scale parameters use bracket indexing:

```python
reform = {"gov.irs.credits.ctc.amount.base[0].amount": 3_000}
```

Time-varying reforms use a nested dict of `YYYY-MM-DD → value`:

```python
reform = {
    "gov.irs.credits.ctc.amount.adult_dependent": {
        "2026-01-01": 1_000,
        "2028-01-01": 2_000,
    },
}
```

Structural reforms (new variables, formula swaps) require the `Simulation` path — see [Reforms](reforms.md).

## Year

```python
pe.us.calculate_household(..., year=2026)
```

The year determines which parameter values apply. For multi-year analysis, call the function once per year rather than building a custom reform.

## Extra variables

The result exposes every variable in the model by default. To surface variables that aren't in the default catalog explicitly:

```python
result = pe.us.calculate_household(
    ...,
    extra_variables=["medicaid_income_level", "spm_unit_spm_threshold"],
)
```

## Accessing the result

```python
result.person[0].income_tax                  # first person
result.person[2].age                         # third person
result.tax_unit.income_tax                   # single tax unit
result.household.household_net_income        # single household
```

The result is a Pydantic model — `.model_dump()` gives you a dict, individual sections are regular attribute lookups.

## Errors

Unknown variables raise with the closest match:

```
ValueError: Unknown variable 'income_ax'. Did you mean 'income_tax'?
```

Unknown parameters in reforms raise similarly. Misplaced inputs (a person-level variable under `tax_unit=...`) raise with entity hints. The catalog is enumerated at construction time — typos fail fast.

## When not to use this

Loops over many households are much slower than a single `Simulation` call. For population analysis, see [Microsimulation](microsim.md) — the reform dict carries over identically.
