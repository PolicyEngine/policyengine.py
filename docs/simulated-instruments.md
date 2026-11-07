---
title: "Simulated instruments"
---

A simulated eligibility instrument runs one fixed population through each state's rules. The people stay the same, so differences across states come from the rules alone. `pe.us.flat_file_microsimulation` runs your own microdata this way.

## The recipe

```python
import pandas as pd
import policyengine as pe
from policyengine.countries.us.data import US_STATE_FIPS

people = pd.read_csv("your_survey.csv", dtype={"county_fips": str})

snap_eligible = {}
for state in US_STATE_FIPS:
    sim = pe.us.flat_file_microsimulation(
        people,
        year=2024,
        state=state,
        spm={"geography_kind": "national"},
    )
    snap_eligible[state] = sim.calculate("is_snap_eligible", "2024-01").mean()
```

`US_STATE_FIPS` maps postal codes to FIPS codes for the 50 states and DC, so the loop runs 51 times. `state` takes a postal code or a FIPS code.

`calculate` returns a weighted series, and `mean()` gives a weighted share of the variable's own entity: SPM units for `is_snap_eligible`, people for `is_medicaid_eligible`. A monthly variable such as `is_snap_eligible` takes a month, and an annual one such as `state_income_tax` takes a year.

Pass `reform=` to run a reform in every state, and read the baseline arm from `sim.baseline`.

To run each household in the state your file records, leave `state` out. The file then needs `state_fips`.

## What your file needs

The file holds one row per person. Name a column after a PolicyEngine variable, or `variable__period` to date it. A column with no period holds the value for `year`.

| Column | Needed | Notes |
| --- | --- | --- |
| `household_id`, `tax_unit_id`, `spm_unit_id`, `family_id`, `marital_unit_id` | Yes | Put each on every person's row, numbered across the whole file. |
| `age` | Yes | The helper refuses a file without it, which would otherwise run everyone as 40. |
| `state_fips` | Unless you pass `state` | The helper refuses a file with neither, which would otherwise run everyone as California. |
| `person_id` | No | The helper numbers the rows if you leave it out. |
| `household_weight` | No | Every household weighs 1 without it. |
| `employment_income` and other inputs | As your measure needs | Give each in its variable's period: `employment_income` holds annual dollars. Inputs you omit take their defaults, usually zero. |
| `county_fips` | No | Read it as text so that 06037 keeps its leading zero. The helper repairs 6037 either way, and reads a blank as no county. |

A survey that restarts a group's ID in each household needs one number per group first:

```python
for column in ["tax_unit_id", "spm_unit_id", "family_id", "marital_unit_id"]:
    people[column] = people.groupby(["household_id", column]).ngroup()
```

To see what the simulation loads, run the checks on their own:

```python
prepared = pe.us.prepare_flat_file(people, year=2024, state="MS")
```

`prepare_flat_file` refuses a file that:

- lacks a required column
- repeats a `person_id`
- numbers groups within each household
- gives one group's rows different values for a group-level variable such as `household_weight`

With `state` left out, it also refuses a county, tract, block, congressional district or state label that contradicts `state_fips` in any year the file holds. With `state` set, those columns leave instead, so they cannot contradict it.

It logs two things as warnings, which Python prints by default: columns that name no variable, which the run ignores, and county codes that name no county, which fall back to the first county in the state.

## Reading results back

Each person-level result follows the rows of your file. Group-level results come back in the order your file first names each group, so pass `map_to="person"` for one value per row:

```python
people["state_tax"] = sim.calculate("state_income_tax", 2024, map_to="person").values
```

`map_to="person"` repeats a group's value on each member's row, so a sum across rows counts it once per member. `sim.calculate("household_id", 2024)` holds your own IDs, which also lets you merge group results back. The helper replaces IDs that are text or exceed 2,147,483,647 with their order in the file, and logs the large ones.

## What a state change clears

Passing `state` sets `state_fips` in every year your file holds. It also removes stored state labels and all geography finer than a state, such as county, ZIP code, congressional district and tract, because those values mean nothing in the new state.

With no county, the model applies county-keyed rules using the first county in the state alphabetically, such as Aitkin County in Minnesota. SPM thresholds use county in the default selection, so select `{"geography_kind": "national"}` as the recipe does. The selection applies to every state, which keeps thresholds identical across the loop. To keep real counties, leave `state` out and run each household where the file records it.

With or without `state`, the helper removes stored copies of what the model derives from the state, such as `state_group`, so the model's formulas run.

## What to watch for

- **Years after your file.** A run carries your file's last value forward, and uprates the inputs that have an uprating rule. $20,000 of 2024 earnings reads as $20,987 in 2025, and a weight of 1,000 reads as 1,009.
- **Years before your file.** An earlier year falls back to defaults. A 2024 file read for 2023 runs everyone as California at age 40, with no income.
- **Medicaid dollars.** `medicaid` spreads each state's total spending across the weighted enrollees the file puts in that state, so a small file gets very large amounts per person. Measure eligibility with `is_medicaid_eligible`. The same applies to `healthcare_benefit_value`.
- **Deciles.** Income deciles rank households within your file, not within the US.
- **Minors on their own.** The SPM calculation needs someone aged 18 or over in each SPM unit, or someone aged 15 to 17 with `is_household_head`, `is_household_spouse` or `is_spm_independent_minor_role` set. Those columns hold for all time, so `sim.to_input_dataframe()`, which writes a simulation's inputs back out as a flat file, names them `variable__ETERNITY`. Keep that suffix when you filter an export to one year.
- **Changing state after the build.** `sim.set_input("state_fips", ...)` leaves stored geography in place. Pass `state` so that the helper clears it first.

`policyengine.py` runs against the country model versions this release pins. Text variables such as `state_code_str` do not map to group entities in these versions, so calculate them at the household level.
