**BREAKING (v4):** Remove the legacy `filter_field` / `filter_value`
fields from `Simulation` and `Region`, the `_auto_construct_strategy`
model validator that rewrote them into a `RowFilterStrategy`, and the
`_filter_dataset_by_household_variable` methods they fed on both
country models. All scoping now flows through `scoping_strategy:
Optional[ScopingStrategy]`. `Region.requires_filter` becomes a derived
property (`True` iff `scoping_strategy is not None`). The sub-national
region factories (`countries/us/regions.py`, `countries/uk/regions.py`)
construct `scoping_strategy=RowFilterStrategy(...)` /
`WeightReplacementStrategy(...)` directly. Callers that previously
passed `filter_field="place_fips", filter_value="44000"` now pass
`scoping_strategy=RowFilterStrategy(variable_name="place_fips",
variable_value="44000")`.
