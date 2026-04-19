Pre-launch cleanup — remove dead code and drop `plotly` from the core dependency set:

- Delete `policyengine.tax_benefit_models.us` and `policyengine.tax_benefit_models.uk` module shims. Python resolves the package directory first, so the `.py` shims were always shadowed; worse, both attempted to re-export `general_policy_reform_analysis` which is not defined anywhere, making `from policyengine.tax_benefit_models.us import general_policy_reform_analysis` raise `ImportError` at runtime.
- Delete `_create_entity_output_model` plus the `PersonOutput` / `BenunitOutput` / `HouseholdEntityOutput` factory products in `policyengine.tax_benefit_models.uk.analysis` — built via `pydantic.create_model` but never referenced anywhere in the codebase.
- Delete `policyengine.core.DatasetVersion` (only consumer was an `Optional` field on `Dataset` that was never set, and the `policyengine.core` re-export).
- Move `plotly>=5.0.0` from the base install to a new `policyengine[plotting]` extra. Only `policyengine.utils.plotting` uses it, and that module is itself only used by the `examples/` scripts. The package now imports cleanly without `plotly`.
