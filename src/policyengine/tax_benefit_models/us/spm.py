"""Typed SPM selection and receipts for the certified US model bundle."""

from policyengine.core.spm import SPMProvenance, SPMSelection

__all__ = [
    "SPMSelection",
    "SPMProvenance",
    "SPM_GEOGRAPHY_SOURCES",
    "resolve_spm_selection",
    "resolve_household_spm_selection",
    "calculation_provenance",
]

# How a household calculation's SPM geography was chosen, reported as
# ``provenance["spm_geography_source"]``: the caller's own ``geography_kind``,
# the bundle default as given, or national measurement in place of the default
# county selection because the household names no county.
SPM_GEOGRAPHY_SOURCES = ("selection", "default", "national_fallback")


def resolve_spm_selection(selection=None) -> dict:
    """Resolve public options against an independently pinned bundle artifact."""
    from policyengine.bundle import get_current_bundle

    configured = get_current_bundle().get("measurements", {}).get("spm")
    if not isinstance(configured, dict):
        raise ValueError(
            "The current bundle has no certified SPM measurement configuration"
        )
    defaults = SPMSelection.model_validate(configured)
    if defaults.forecast_content_sha256 is None or defaults.scenario is None:
        raise ValueError(
            "The bundle must pin the SPM artifact hash and default scenario"
        )
    chosen = SPMSelection.model_validate({} if selection is None else selection)
    if chosen.forecast_content_sha256 not in (None, defaults.forecast_content_sha256):
        raise ValueError("SPM selection does not match this bundle's artifact hash")
    # Serialization intentionally preserves omissions in a partial selection.
    # Materialize the validated bundle defaults before applying that selection,
    # so the returned config freezes every setting for later replay.
    values = {name: getattr(defaults, name) for name in SPMSelection.model_fields}
    values.update(chosen.model_dump(exclude_unset=True))
    if (
        chosen.geography_kind != defaults.geography_kind
        and "geography_kind" in chosen.model_fields_set
    ):
        values["geography_id"] = chosen.geography_id
    # Explicit null must not remove an independently expected artifact identity.
    values["forecast_content_sha256"] = defaults.forecast_content_sha256
    values["scenario"] = chosen.scenario or defaults.scenario
    return SPMSelection.model_validate(values).model_dump()


def resolve_household_spm_selection(
    selection=None, *, household_names_county: bool
) -> tuple[dict, str]:
    """Resolve one household calculation's SPM selection and how it was chosen.

    A ``geography_kind`` the caller chose is honoured as given, so an explicit
    county selection for a household with no county still raises
    ``SPM_GEOGRAPHY_REQUIRED``. Otherwise the bundle default applies, except
    that the default county selection becomes national measurement when the
    household names no county. A state alone does not identify a Census SPM
    estimation area, and national measurement is the one geography that needs
    no area. The substitution is reported in the returned source, never made
    silently.

    Every other setting, such as ``scenario``, is kept. Population simulations
    do not use this function: their data must supply observed counties.

    Returns the resolved configuration and one of ``SPM_GEOGRAPHY_SOURCES``.
    """
    chosen = SPMSelection.model_validate({} if selection is None else selection)
    # Resolve before deciding: this also rejects a selection that asserts a
    # different artifact hash, whichever geography is finally used.
    config = resolve_spm_selection(chosen)
    if "geography_kind" in chosen.model_fields_set:
        return config, "selection"
    if config["geography_kind"] != "county" or household_names_county:
        return config, "default"
    # ``model_dump`` keeps only the settings the caller chose.
    national = {**chosen.model_dump(), "geography_kind": "national"}
    return resolve_spm_selection(national), "national_fallback"


def calculation_provenance(simulation) -> dict:
    return SPMProvenance.model_validate(simulation.spm_provenance()).model_dump(
        mode="json"
    )
