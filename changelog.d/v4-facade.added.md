**BREAKING (v4):** Collapse the household-calculator surface into a
single agent-friendly entry point, ``pe.us.calculate_household`` /
``pe.uk.calculate_household``.

New public API:

- ``policyengine/__init__.py`` populated with canonical accessors:
  ``pe.us``, ``pe.uk``, ``pe.Simulation`` (replacing the empty top-level
  module). ``import policyengine as pe`` now gives you everything a
  new coding session needs to reach in one line.
- ``pe.us.calculate_household(**kwargs)`` and ``pe.uk.calculate_household``
  take flat keyword arguments (``people``, per-entity overrides,
  ``year``, ``reform``, ``extra_variables``) instead of a pydantic
  input wrapper.
- ``reform=`` accepts a plain dict: ``{parameter_path: value}`` or
  ``{parameter_path: {effective_date: value}}``. Compiles internally.
- Returns :class:`HouseholdResult` (new) with dot-access:
  ``result.tax_unit.income_tax``, ``result.household.household_net_income``,
  ``result.person[0].age``. Singleton entities are
  :class:`EntityResult`; ``person`` is a list of them. ``to_dict()``
  and ``write(path)`` serialize to JSON.
- ``extra_variables=[...]`` is now a flat list; the library dispatches
  each name to its entity by looking it up on the model.
- Unknown variable names (in ``people``, entity overrides, or
  ``extra_variables``) raise ``ValueError`` with a ``difflib`` close-match
  suggestion and a paste-able fix hint.
- Unknown dot-access on a result raises ``AttributeError`` with the
  list of available variables plus the ``extra_variables=[...]`` call
  that would surface the requested one.

Removed (v4 breaking):

- ``USHouseholdInput`` / ``UKHouseholdInput`` / ``USHouseholdOutput`` /
  ``UKHouseholdOutput`` pydantic wrappers.
- ``calculate_household_impact`` — the name was misleading (it
  returned levels, not an impact vs. baseline). Reserved for a future
  delta function.
- The bare ``us_model`` / ``uk_model`` label-only singletons; each
  country module now exposes ``.model`` pointing at the real
  ``TaxBenefitModelVersion`` (kept ``us_latest`` / ``uk_latest``
  aliases for compatibility with any in-flight downstream code).

New internal module:

- ``policyengine.tax_benefit_models.common`` — ``compile_reform``,
  ``dispatch_extra_variables``, ``EntityResult``, ``HouseholdResult``
  shared by both country implementations.
