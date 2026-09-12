"""Typed SPM selection and receipts for the certified US model bundle."""

from policyengine.core.spm import SPMProvenance, SPMSelection

__all__ = [
    "SPMSelection",
    "SPMProvenance",
    "resolve_spm_selection",
    "calculation_provenance",
]


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


def calculation_provenance(simulation) -> dict:
    return SPMProvenance.model_validate(simulation.spm_provenance()).model_dump(
        mode="json"
    )
