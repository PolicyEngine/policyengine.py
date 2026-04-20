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

| Argument | Required | Purpose |
|---|---|---|
| `people` | Yes | List of person dicts. Keys are any person-level variable on the model. |
| `tax_unit` | One of the per-household-level keys | Tax-unit-level inputs (e.g. `filing_status`). |
| `spm_unit` | Optional | SPM-unit inputs. |
| `household` | Usually required | Household-level inputs. `state_code` is essentially always needed for US. |
| `family` | Optional | Family-level inputs. |
| `marital_unit` | Optional | Marital-unit inputs. |

If you pass multiple adults, PolicyEngine assigns them to one tax unit and one household by default. For separate tax units, use `pe.Simulation` directly and set the entity-membership arrays.

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
| `benunit` | Benefit unit (equivalent to UC claim). |
| `household` | Household-level inputs. |

## Reforms

Pass a `reform` dict of parameter-path to value:

```python
pe.us.calculate_household(
    ...,
    reform={"gov.irs.credits.ctc.amount.adult_dependent": 1_000},
)
```

For values effective on specific dates, use a nested dict:

```python
reform = {
    "gov.irs.credits.ctc.amount.adult_dependent": {
        "2026-01-01": 1_000,
        "2028-01-01": 2_000,
    },
}
```

Structural reforms (subclassing the model) are covered in [Reforms](reforms.md).

## Year

```python
pe.us.calculate_household(..., year=2026)
```

The year determines which parameter values apply. For year arithmetic (e.g. phase-ins), pass a `reform` with dated values rather than calling the function once per year.

## Extra variables

By default the result exposes every variable in the model. If your calculator-level output should contain variables that aren't in the default catalog, request them:

```python
result = pe.us.calculate_household(
    ...,
    extra_variables=["medicaid_income_level", "spm_unit_spm_threshold"],
)
```

## Accessing the result

```python
result.person[0].income_tax                  # scalar for first person
result.person[2].age                         # scalar for third person (the 8-year-old)
result.tax_unit.income_tax                   # scalar (one tax unit)
result.household.household_net_income        # scalar
```

The result is a Pydantic model — `.model_dump()` gives you a dict, and individual entity sections are regular attribute lookups.

## When not to use this

- Runs over many households in a loop will be much slower than one `Simulation` call. See [Microsimulation](microsim.md).
- If your input data lives in a DataFrame or file, the microsim path is cleaner — `calculate_household` is optimized for per-household construction from Python literals.

## Errors

Unknown variables raise with suggestions:

```
ValueError: Unknown variable 'income_ax'. Did you mean 'income_tax'?
```

Unknown parameters in reforms raise similarly. The catalog is enumerated at construction time — typos fail fast.
