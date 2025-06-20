# Testing data processing speeds for API v2

## Process
### Initial configuration
1. Cloned [this PR](https://github.com/PolicyEngine/policyengine.py/pull/119), which introduces SQLModel-based data schematization
2. Commented out all intra-table relationships, which require more complete data loading than this test aims for
3. Imported and ran the `create_db_and_tables()` function defined in Nikhil's PR
4. Wrote a script to load from the CPS 2023's age dataset into the `entity` table using the `Entity` schema; note that this only creates households themselves
5. Within `GeneralEconomyTask`, added `_write_var_to_db()` to write a given `Variable` name and values to the database and `_get_var_id_from_db()` to fetch the `Variable` ID value from the database
6. Modified `calculate_single_economy.py` to write all calculated variables to the `variable_state` table using the `VariableState` schema; note that this does not write dependent variables

### Configuration to enable SQLite
1. Created a local database, `tax_policy_sqlite.db`, to store output values