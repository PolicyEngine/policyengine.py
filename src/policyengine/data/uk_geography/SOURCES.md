# UK area lists

Codes, names and hex-map positions for the UK area regions and the labels of
geography outputs. They are not the lookup CSVs paired with the legacy
weight matrices, whose row order indexes those matrices.

## `local_authorities_2023.csv`

Columns `code,name,x,y`; 361 local authority districts on the April 2023 frame:
296 in England, 22 in Wales, 32 in Scotland and 11 in Northern Ireland,
including Ards and North Down (`N09000011`) and the four unitaries created on
1 April 2023 (`E06000063`–`E06000066`), and none of the 17 districts they
replaced.

- Codes and names: ONS, Local Authority Districts (April 2023) Names and Codes
  in the United Kingdom (columns `LAD23CD`, `LAD23NM`), ONS Open Geography
  Portal item `e8b361ba9e98418ba8ff2f892d00c352`. Contains public sector
  information licensed under the Open Government Licence v3.0.
- Hex positions: PolicyEngine's April 2023 local-authority hex layout, from
  PolicyEngine/policyengine-sim-api
  `projects/policyengine-simulation-executor/src/policyengine_simulation_executor/static_runtime_files/uk_local_authorities/`
  at commit `3ac09cf9205bc66a5809e70a634c457362d1a887`:
  - `names.csv` sha256 `9e183902e54383d56f7f311d0eaac6a9ee92522a5f21c58ce5118265ae3f1bf4`
  - `coordinates_lad23.csv` sha256 `b1489a5b0101ff6d91ef9262e992cca19b59359edb42d012c305a21a04571f64`
- Built by joining `coordinates_lad23.csv` to `names.csv` on `code`, sorted by
  code. The names match the ONS file exactly. Against policyengine-uk-data's
  `local_authorities_2021.csv` (360 rows on the same frame), this adds
  `N09000011` and replaces the shared (0, 0) placeholder of the four 2023
  unitaries with their own hexes.

## `constituencies_2024.csv`

Columns `code,name,x,y,region,country`; the 650 parliamentary constituencies
of the 2024 boundaries: 543 in England, 57 in Scotland, 32 in Wales and 18 in
Northern Ireland. Copied unchanged from PolicyEngine/policyengine-uk-data
`policyengine_uk_data/storage/constituencies_2024.csv` at commit
`26ccdd1fd1aff6665704fda37388a86adecb5122` (sha256 `f4f35d61ffc004190c438a7e1583caefd85054f962671a00069aedd0a1b5b737`).
Codes and names: ONS (Open Government Licence v3.0).
