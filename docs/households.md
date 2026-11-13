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
    # The married couple, then each child: see "Several groups of one entity".
    marital_unit=[{"members": [0, 1]}, {"members": [2]}, {"members": [3]}],
    tax_unit={"filing_status": "JOINT"},
    household={"state_code": "TX", "county_fips": "48201"},
    year=2026,
)
```

### Entities

| Argument | Purpose |
|---|---|
| `people` | List of person dicts. Keys are any person-level variable on the model. |
| `tax_unit` | Tax-unit inputs (e.g. `filing_status`), or a list of tax units. |
| `spm_unit` | SPM-unit inputs, or a list of SPM units. |
| `household` | Household inputs, including `state_code` and observed five-digit `county_fips` for the default SPM geography selection. |
| `family` | Family-level inputs, or a list of families. |
| `marital_unit` | Marital-unit inputs, or a list of marital units. |

A mapping puts every person in one group of that entity, and the household always holds everyone.

### Several groups of one entity

To split people into several marital units, families, SPM units or tax units, pass a list of groups. Each group is a mapping with `members`, a list of indexes into `people`, plus that group's own inputs. Each person belongs to exactly one group of the entity: `calculate_household` raises if a list leaves someone out, names someone twice or names an index outside `people`.

policyengine-us defines a marital unit as one unmarried person or one married couple, and two of its rules depend on that. Medicaid's optional pathway for seniors and people with disabilities applies the couple income limit to a marital unit of exactly two people. SSI treats two aged, blind or disabled heads or spouses in one marital unit as a joint claim and, unless exactly one member counts as living in a medical treatment facility, adds up countable income across the whole unit. So pass marital units whenever the household holds anyone besides one person or one couple:

```python
result = pe.us.calculate_household(
    people=[
        {"age": 68},
        {"age": 66},
        {"age": 17, "employment_income": 6_000},
    ],
    marital_unit=[{"members": [0, 1]}, {"members": [2]}],
    tax_unit={"filing_status": "JOINT"},
    household={"state_code": "CA"},
    year=2026,
    spm={"geography_kind": "national"},
    extra_variables=["ssi"],
)
result.marital_unit[1]  # the 17-year-old's marital unit
```

With one marital unit for all three, SSI would add the 17-year-old's earnings to the couple's income, and Medicaid's optional senior-or-disabled pathway would hold the couple to the individual income limit.

A list of tax units covers, for example, an adult child who files their own return:

```python
result = pe.us.calculate_household(
    people=[
        {"age": 52, "employment_income": 60_000},
        {"age": 22, "employment_income": 18_000},
    ],
    marital_unit=[{"members": [0]}, {"members": [1]}],
    tax_unit=[
        {"members": [0], "filing_status": "SINGLE"},
        {"members": [1], "filing_status": "SINGLE"},
    ],
    household={"state_code": "NY", "county_fips": "36061"},
    year=2026,
)
result.tax_unit[1].income_tax  # the adult child's return
```

An entity passed as a list comes back as a list of results in the same order. Under axes, each group's variables are axis series, as each person's are.

Each group needs the people its rules expect. policyengine-us makes the oldest person aged 18 or over in each tax unit its head, so a tax unit of children has no head. SPM measurement needs an adult in each SPM unit: a unit of children raises `SPM_COMPOSITION_REQUIRED` when its poverty status computes, as it does among the default outputs.

Group ids such as `tax_unit_id` keep the values you pass, 0 by default. To see each person's group in `result.person`, pass ids as group inputs, for example `tax_unit=[{"members": [0], "tax_unit_id": 1}, {"members": [1], "tax_unit_id": 2}]`.

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
canonical artifact covers 2022–2036. Its receipt distinguishes published
national inputs from forecast components and research geography; an unsupported
year fails instead of being extrapolated by the wrapper. Scenario forecasts
are conditional research estimates, not agency forecasts or uncertainty bounds.

State alone is insufficient for SPM and raises `SPM_GEOGRAPHY_REQUIRED`.
Unknown counties or selected areas raise `SPM_GEOGRAPHY_UNAVAILABLE`; a measured
unit with no classified adult raises `SPM_COMPOSITION_REQUIRED`. These are
calculator `SPMInputError` exceptions with `code` and `to_dict()` attributes.
Geography is checked when an SPM-dependent formula runs, and only for the units
whose result depends on the measurement. SPM measurement itself — thresholds,
the geographic factor and SPM poverty — always requires this choice. The
ordinary resource outputs — household net income, benefits, income decile and
equivalized net income, and each person's marginal tax rate — take the
household's housing assistance amount rather than the capped SPM subsidy, so
they succeed on state alone and record an empty measurement receipt whether or
not the unit is allocated assistance. The country's cap
(`spm_unit_capped_housing_subsidy`) is what consults the canonical housing
portion, and only for units allocated assistance. So for an assisted unit
without a geography the cap and everything downstream of it —
`spm_unit_benefits`, `spm_unit_net_income` and in turn
`spm_unit_oecd_equiv_net_income` and `spm_unit_income_decile` — raise
`SPM_GEOGRAPHY_REQUIRED`, while a unit allocated none has a capped subsidy of
zero by construction and consults no measurement. A genuinely independent
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
2.2.2, `policyengine-core` 3.33.3, `spm-calculator` 1.1.0, and the US data
release `populace-us-2024-spm-20260915`. Local-wheel development manifest
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

Time-varying reforms use a nested dict of date keys to values:

```python
reform = {
    "gov.irs.credits.ctc.amount.adult_dependent": {
        "2026-01-01": 1_000,
        "2028-01-01": 2_000,
    },
}
```

For UK households, a `YYYY-MM-DD` key is effective from that date until the next value for the same parameter, or December 31, 2100 if no later value follows. A `YYYY-MM-DD.YYYY-MM-DD` key applies over that inclusive interval. Scalar values default to January 1 of `year`.

UK households reject bare years such as `"2027"` or `2027`, because the underlying packages assign different meanings to them. Use `"2027-04-06.2028-04-05"` for one UK fiscal year or `"2027-01-01"` for an effective date. See [Reforms](reforms.md) for the shared `Simulation(policy=...)` and `Simulation(dynamic=...)` date contract. The US household route retains its country package's period-key handling.

UK household results record the capital gains realisation response the calculation applied, under `result["provenance"]["capital_gains_responses"]`: the policyengine-uk release, the reform's explicit `gov.simulation.capital_gains_responses` settings, and the assumption policyengine-uk resolved (see [The UK capital gains realisation response](microsim.md#the-uk-capital-gains-realisation-response)). `result.write(...)` includes it.

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
result.person[0].medicaid  # first person
result.person[2].age  # third person
result.tax_unit.income_tax  # single tax unit
result.marital_unit[1]  # second marital unit, when passed as a list
result.household.household_net_income  # single household
```

The result is a `dict` with attribute access: `.to_dict()` gives a plain dict, `.write(path)` writes it as JSON, and individual sections are regular attribute lookups.

## Errors

Unknown variables raise with the closest match:

```
ValueError: Unknown variable 'income_ax'. Did you mean 'income_tax'?
```

Unknown parameters in reforms raise similarly. Misplaced inputs (a person-level variable under `tax_unit=...`) raise with entity hints. The catalog is enumerated at construction time — typos fail fast.

## When not to use this

Loops over many households are much slower than a single `Simulation` call. For population analysis, see [Microsimulation](microsim.md) — the reform dict carries over identically.
