# Testing data processing speeds for API v2

## Process
### Initial configuration
1. Cloned [this PR](https://github.com/PolicyEngine/policyengine.py/pull/119), which introduces SQLModel-based data schematization
2. Commented out all intra-table relationships, which require more complete data loading than this test aims for
3. Imported and ran the `create_db_and_tables()` function defined in Nikhil's PR
4. Wrote a script to load from the CPS 2023's age dataset into the `entity` table using the `Entity` schema; note that this only creates households themselves
5. Within `GeneralEconomyTask`, added `_write_var_to_db()` to write a given `Variable` name and values to the database and `_get_var_id_from_db()` to fetch the `Variable` ID value from the database
6. Modified `calculate_single_economy.py` to write all calculated variables to the `variable_state` table using the `VariableState` schema; note that this does not write dependent variables

### Extra configuration to enable SQLite with array blobs
1. Added an optional key `data` of type `LargeBinary` to `Variable`; would assume this would be used in conjunction with API version or something similar

### Extra configuration to enable JSON
1. Disabled database loading in test script

### Speeds
| Config type     | Create database | Load variable metadata | Load households | Load VariableState data | Variables loaded | Mean VariableState loadtime per Variable |
|-----------------|-----------------|------------------------|-----------------|-------------------------|------------------|------------------------|
| SQLite local db | 0.05s           | 0.51s                  | 12.59s          | 16m 38s before crash*   |  12              | 1m 19.3s   |
| SQLite w/ batching | 0.05s        | 0.56s                  | 12.46s          |  9m 6.5s before crash** | 4                | 54.44s                 |
| SQLite w/ arr blob | 0.05s        | 0.59s                  | 12.54s          | 47.3s before crash***   | 4                | 0.02s                  |
| JSON            |  N/A            |  0.01s                 |  0.52s          | 15m 37.4s before crash* |  12              | 1m 14.0s               |
| DuckDB          |                 |                        |                 |                         | | |
|-----------------|-----------------|------------------------|-----------------|-------------------------|-|-|

\* Crashed due to config error resulting in incorrect running of UK programs
\*\* Crashed due to "database locked" error; appears to be caused by accessing database while open for another transaction
\*\*\* Crashed due to incorrect byte encoding process (my own error)