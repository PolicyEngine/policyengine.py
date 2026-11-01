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

`state` takes a postal code or a FIPS code. `calculate` returns a weighted series, so `mean()` gives the weighted share of SPM units. Pass `reform=` to run a reform in every state, and read the baseline arm from `sim.baseline`.

To run each household in the state your file records, leave `state` out. The file then needs `state_fips`, and any county or state label it holds has to agree with `state_fips`.

## What your file needs

The file holds one row per person. Name a column after a variable, or `variable__period` to date it. A column with no period holds the value for `year`.

| Column | Needed | Notes |
| --- | --- | --- |
| `household_id`, `tax_unit_id`, `spm_unit_id`, `family_id`, `marital_unit_id` | Yes | Put each on every person's row, numbered across the whole file. Text IDs work. |
| `age` | Yes | Without it, everyone runs as 40. |
| `state_fips` | Unless you pass `state` | Without it, everyone runs as California. |
| `person_id` | No | The helper numbers the rows if you leave it out. |
| `household_weight` | No | Every household weighs 1 without it. |
| Income and other inputs | As your measure needs | Inputs you omit take their defaults, usually zero. |
| `county_fips` | No | Read it as text so that 06037 keeps its leading zero. The helper repairs 6037 either way. |

`prepare_flat_file` runs these checks and returns the frame the simulation loads, so you can inspect it. It refuses a file that lacks a required column, repeats a `person_id`, numbers groups within each household, gives one group's rows different values for a group-level variable such as `household_weight`, or holds a county outside its state. It logs columns that name no variable, then ignores them.

## What a state change clears

Passing `state` sets `state_fips` in every year your file holds. It also removes stored state labels and all geography finer than a state, such as county, ZIP code, congressional district and tract, because those values mean nothing in the new state.

With no county, the model applies county-keyed rules using the first county in the state alphabetically, such as Aitkin County in Minnesota. SPM thresholds use county in the default selection, so select `{"geography_kind": "national"}` as the recipe does. The selection applies to every state, which keeps thresholds identical across the loop. To keep real counties, leave `state` out and run each household where the file records it.

## What to watch for

- **Years before your file.** A run reads later years from your file's last value, but an earlier year falls back to defaults. A 2024 file read for 2023 runs everyone as California at age 40, with no income.
- **Medicaid dollars.** `medicaid` spreads each state's total spending across the weighted people the file puts in that state, so a small file gets very large amounts per person. Measure eligibility with `is_medicaid_eligible`. The same applies to `healthcare_benefit_value`.
- **Deciles.** Income deciles rank households within your file, not within the US.
- **Minors on their own.** The SPM calculation needs someone aged 18 or over in each SPM unit, or someone aged 15 to 17 with `is_household_head`, `is_household_spouse` or `is_spm_independent_minor_role` set. Those columns hold for all time, so `to_input_dataframe` names them `variable__ETERNITY`. Keep that suffix when you filter an export to one year.
- **Changing state after the build.** `sim.set_input("state_fips", ...)` leaves stored geography in place. Pass `state` so that the helper clears it first.

`policyengine.py` runs against the country model versions this release pins. Text variables such as `state_code_str` do not map to group entities in these versions, so calculate them at the household level.
