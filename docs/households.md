---
title: "Households"
---

`pe.us.calculate_household` and `pe.uk.calculate_household` compute a default set of tax, benefit and income outputs for a single household. Use `extra_variables` to request additional outputs.

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
    household={"state_code": "TX", "county_fips": "48201"},
    year=2026,
)
```

### Entities

| Argument | Purpose |
|---|---|
| `people` | List of person dicts. Keys are any person-level variable on the model. |
| `tax_unit` | Tax-unit inputs (e.g. `filing_status`). |
| `spm_unit` | SPM-unit inputs. |
| `household` | Household inputs, including `state_code` and observed five-digit `county_fips` for the default SPM geography selection. |
| `family` | Family-level inputs. |
| `marital_unit` | Marital-unit inputs. |

All adults default to one shared tax unit and household. For separate tax units (e.g. two adult roommates), construct the `Simulation` directly and set the entity-membership arrays.

### SPM geography and measurement selection

US household results include SPM resources and poverty by default. Provide the
household's county FIPS, as above, or explicitly select national measurement:

```python
result = pe.us.calculate_household(
    people=[{"age": 40, "employment_income": 50_000}],
    tax_unit={"filing_status": "SINGLE"},
    household={"state_code": "CA"},
    year=2026,
    spm={"geography_kind": "national"},
)
receipt = result.to_dict()["provenance"]["spm"]
result.write("household-result.json")  # Includes the JSON-compatible receipt.
```

County FIPS assigns a household to the selected year's Census SPM estimation
area; it does not select a separately estimated county rent factor. National
measurement is a conscious analytical choice and is recorded in provenance.
A fixed SPM area can instead be selected with
`spm={"geography_kind": "metro", "geography_id": area_id}`, using an area ID
available in the pinned artifact for the requested year.

The `spm` argument accepts a dictionary or `pe.us.SPMSelection`. Its complete
set of keys is:

| Key | Meaning |
|---|---|
| `forecast_content_sha256` | Optional assertion of the bundle's independently pinned artifact content hash. A different hash is rejected. |
| `scenario` | Scenario within that artifact: `ce_trend` by default or the `zero_real` sensitivity. |
| `geography_kind` | `county` by default; `national` or `metro` require an explicit choice. |
| `geography_id` | Required only for a fixed `metro` SPM area. |
| `county_vintage` | County assignment vintage, `"2020"` by default. |
| `as_of` | Optional information-date cutoff accepted by the pinned artifact. |

Forecast paths, provider objects and fallback policies are not settings. The
canonical artifact covers 2022–2035. Its receipt distinguishes published
national inputs from forecast components and research geography; an unsupported
year fails instead of being extrapolated by the wrapper. Scenario forecasts
are conditional research estimates, not agency forecasts or uncertainty bounds.

State alone is insufficient for SPM and raises `SPM_GEOGRAPHY_REQUIRED`.
Unknown counties or selected areas raise `SPM_GEOGRAPHY_UNAVAILABLE`; a measured
unit with no classified adult raises `SPM_COMPOSITION_REQUIRED`. These are
calculator `SPMInputError` exceptions with `code` and `to_dict()` attributes.
Geography is checked when an SPM-dependent formula runs, and only for the units
whose result depends on the measurement. SPM measurement itself — thresholds,
the geographic factor and SPM poverty — always requires this choice. Resource
outputs (net income, benefits, MTR, income decile and equivalized net income)
reach the measurement only through the capped housing subsidy, which the country
evaluates for units with housing assistance to cap; a unit receiving no housing
assistance has a capped subsidy of zero by construction and consults no
measurement. So a resource calculation for an unassisted unit succeeds on state
alone and records an empty measurement receipt, while the same calculation for
an assisted unit raises `SPM_GEOGRAPHY_REQUIRED`. A genuinely independent
tax-only country-model calculation can use state alone; the wrapper's default
outputs include SPM poverty and therefore always require the choice.

Supply observed inputs such as age, tenure, county and the source-backed
`is_spm_independent_minor_role`. Computed SPM thresholds, geographic factors,
resources, poverty outputs and `spm_measurement_adults` /
`spm_measurement_children` cannot be supplied as household inputs or axes.
Generic `is_adult`, `spm_unit_count_adults` and `spm_unit_count_children` remain
separate benefit inputs; they do not override SPM measurement composition.

These changes require the coordinated canonical country/calculator bundle, which
the packaged production manifest now pins and certifies: `policyengine-us`
2.0.0, `policyengine-core` 3.32.5, `spm-calculator` 1.0.0, and the US data
release `populace-us-2024-spm-20260909`. Local-wheel development manifest
fixtures remain explicitly uncertified. The measurement receipt identifies a
calculation; it does not certify a population dataset or establish publication
readiness.

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

The result exposes a default output catalog. To request additional variables:

```python
result = pe.us.calculate_household(
    ...,
    extra_variables=["medicaid_income_level", "spm_unit_spm_threshold"],
)
```

## Axes

Use `axes` to evaluate one household across a grid of input values. Pass either
the lower-level nested shape or a flat list of axis dictionaries; missing
`period` values default to `year`.

```python
result = pe.us.calculate_household(
    people=[
        {
            "age": 35,
            "employment_income": 60_000,
            "is_tax_unit_head": True,
            "charitable_cash_donations": 0,
        }
    ],
    tax_unit={"filing_status": "SINGLE"},
    household={"state_code": "CA", "county_fips": "06037"},
    year=2026,
    axes=[
        {
            "name": "charitable_cash_donations",
            "min": 0,
            "max": 10_000,
            "count": 3,
        }
    ],
    extra_variables=["charitable_cash_donations"],
)

result.person[0].charitable_cash_donations  # [0, 5000, 10000]
result.tax_unit.income_tax  # one value per axis point
```

When axes are present, result values are lists ordered by the axis grid instead
of scalars. For person results, each person still has their own result object;
each variable on that person is its own axis series.

## Accessing the result

```python
result.person[0].income_tax  # first person
result.person[2].age  # third person
result.tax_unit.income_tax  # single tax unit
result.household.household_net_income  # single household
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
