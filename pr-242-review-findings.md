# PR #242 Review Findings

## Critical

### 2. `Simulation.ensure()` catches all exceptions from `load()`, silently re-runs simulation

**File:** `src/policyengine/core/simulation.py:45-49`

```python
def ensure(self):
    cached_result = _cache.get(self.id)
    if cached_result:
        self.output_dataset = cached_result.output_dataset
        return
    try:
        self.tax_benefit_model_version.load(self)
    except Exception:       # <--- catches everything
        self.run()
        self.save()

    _cache.add(self.id, self)
```

The `except Exception` is intended to catch "file not found" when no cached simulation exists, but it also catches corrupted H5 files, permission errors, OOM, and schema mismatches. In all cases it silently re-runs the full simulation with no logging. A corrupted cache file would cause every request to silently recompute from scratch, destroying performance with no indication to the user.

**Fix:** Catch only `FileNotFoundError`. Log other exceptions before falling back to `run()`.

---

## Important

### 3. Five new poverty convenience functions are not exported

**File:** `src/policyengine/outputs/__init__.py`

The following public functions were added to `poverty.py` but are not imported or listed in `__all__`:

- `calculate_uk_poverty_by_age`
- `calculate_us_poverty_by_age`
- `calculate_uk_poverty_by_gender`
- `calculate_us_poverty_by_gender`
- `calculate_us_poverty_by_race`

Also missing: `AGE_GROUPS`, `GENDER_GROUPS`, `RACE_GROUPS` constants.

Users importing from `policyengine.outputs` (the expected pattern) will not see these functions.

**Fix:** Add the missing imports and `__all__` entries in `outputs/__init__.py`.

---

### 4. Poverty convenience functions overwrite `filter_variable` with group label

**File:** `src/policyengine/outputs/poverty.py:289` (and lines 327, 365, 404, 444)

```python
for pov in group_results.outputs:
    pov.filter_variable = group_name  # "child" replaces "age"
    results.append(pov)
```

After running the poverty calculation with e.g. `filter_variable="age", filter_variable_leq=17`, the code mutates `filter_variable` from `"age"` to `"child"`. The object becomes internally inconsistent: `filter_variable` says `"child"` but `filter_variable_leq` says `17`. If anyone inspects or re-uses the object, the filter metadata is misleading.

**Fix:** Add a separate field (e.g., `filter_group: str | None = None`) to the `Poverty` class for the group label, rather than overwriting `filter_variable`.

---

### 5. Bare `except Exception` in UK region CSV loaders

**File:** `src/policyengine/countries/uk/regions.py:59, 91`

```python
def _load_constituencies_from_csv() -> list[dict]:
    try:
        from policyengine_core.tools.google_cloud import download
    except ImportError:
        return []

    try:
        csv_path = download(...)
        df = pd.read_csv(csv_path)
        return [{"code": row["code"], "name": row["name"]} for _, row in df.iterrows()]
    except Exception:       # <--- catches everything
        return []
```

Same pattern in `_load_local_authorities_from_csv()`. Auth failures, CSV schema changes (`KeyError` on missing `code`/`name` columns), network errors, and corrupt files all silently return `[]`. Downstream, the registry treats this as "no constituencies exist" and the entire UK geographic impact feature silently degrades to empty results.

**Fix:** At minimum, add `logging.warning()` with the exception. Ideally, narrow the catch to expected failure modes (e.g., `IOError`, `OSError`) and let unexpected errors propagate.

---

### 6. UK model fetches PyPI metadata at module import time with no error handling

**File:** `src/policyengine/tax_benefit_models/uk/model.py:40-45`

```python
pkg_version = version("policyengine-uk")

response = requests.get("https://pypi.org/pypi/policyengine-uk/json")
data = response.json()
upload_time = data["releases"][pkg_version][0]["upload_time_iso_8601"]
```

This runs at module import time (not in a function or `__init__`). No timeout, no error handling, no fallback. If PyPI is down, slow, or unreachable (CI, air-gapped environments, proxy), importing the module hangs or crashes.

The US model already handles this correctly with a lazy-loading function `_get_us_package_metadata()` called from `__init__`.

**Fix:** Move to a lazy-loading function like the US model. Add a timeout and try/except.

---

### 7. `_resolve_id_column` returns nonexistent column name without validation

**File:** `src/policyengine/utils/entity_utils.py:7-19`

```python
def _resolve_id_column(person_data: pd.DataFrame, entity_name: str) -> str:
    prefixed = f"person_{entity_name}_id"
    bare = f"{entity_name}_id"
    if prefixed in person_data.columns:
        return prefixed
    return bare       # <--- returns bare even if it doesn't exist
```

If neither column exists, returns `bare` anyway. The caller then does `person_data[id_col].values` which raises a cryptic `KeyError: 'household_id'` with no context about what was being looked up or what columns are available.

**Fix:** Check both columns and raise a descriptive `ValueError` if neither exists:

```python
if bare in person_data.columns:
    return bare
raise ValueError(
    f"Cannot find ID column for entity '{entity_name}'. "
    f"Expected '{prefixed}' or '{bare}', available columns: {list(person_data.columns)}"
)
```

---

### 8. `filter_dataset_by_household_variable` passes unknown entities through unfiltered

**File:** `src/policyengine/utils/entity_utils.py:112-118`

```python
for entity_name, mdf in entity_data.items():
    df = pd.DataFrame(mdf)
    id_col = f"{entity_name}_id"
    if entity_name in filtered_ids and id_col in df.columns:
        filtered_df = df[df[id_col].isin(filtered_ids[entity_name])]
    else:
        filtered_df = df       # <--- entire entity passes through unfiltered
```

If an entity isn't in `filtered_ids` (e.g., missing from `group_entities`, or a misspelling), its data passes through completely unfiltered. The resulting dataset has a mix of filtered and unfiltered entities — some scoped to a region, others containing the entire national dataset. Simulation results would be silently wrong.

**Fix:** Log a warning or raise an error when the else branch is taken for a non-"person" entity.

---

### 9. `reform_dict_from_parameter_values` returns `None` despite `dict` return type

**File:** `src/policyengine/utils/parametric_reforms.py:35-36`

```python
def reform_dict_from_parameter_values(
    parameter_values: list[ParameterValue],
) -> dict:
    if not parameter_values:
        return None       # <--- type says dict, returns None
```

The type annotation says `-> dict` but returns `None` for empty/None inputs. Callers must handle `None` as a special case. The function also accepts `None` despite the type hint saying `list[ParameterValue]`.

**Fix:** Either return `{}` instead of `None` for empty inputs, or change the signature to `parameter_values: list[ParameterValue] | None` and `-> dict | None`.

---

### 10. `Poverty.run()` has no direct unit test

**File:** `src/policyengine/outputs/poverty.py:68-131`

The core `Poverty.run()` method has significant logic: entity mapping (`map_to_entity`), filter mask construction with three filter operators (`eq`, `leq`, `geq`), and the weighted headcount calculation. All existing poverty tests in `test_poverty_by_demographics.py` mock the base calculation functions — they never exercise `Poverty.run()` itself.

If there's a bug in filter construction, the `== True` comparison on line 125, or the weighted sum logic, no current test catches it.

**Fix:** Add a test that constructs a mock simulation with known poverty values and demographic data, calls `Poverty.run()` directly, and verifies headcount/rate calculations with each filter type (`eq`, `leq`, `geq`), including the combined adult filter that uses both `geq` and `leq` simultaneously.
