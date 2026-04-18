`calculate_household_impact` (US and UK) and `Simulation` now accept an
`extra_variables` mapping (`{entity_name: [variable_name, ...]}`) so
callers can request variables beyond the bundled `entity_variables`
default set without monkey-patching. This unblocks benchmark suites
(e.g. `policybench`) that need variables such as
`adjusted_gross_income`, `state_agi`, `free_school_meals`, or
`is_medicaid_eligible` that the default list does not include. The
returned `USHouseholdOutput` / `UKHouseholdOutput` dicts gain the
requested keys; existing keys are unchanged.
