"""Entity-mapping limits for nullable US poverty status indicators."""

NULLABLE_SPM_POVERTY_VARIABLES = frozenset(
    {
        "in_poverty",
        "in_deep_poverty",
        "person_in_poverty",
        "spm_unit_is_in_spm_poverty",
        "spm_unit_is_in_deep_spm_poverty",
    }
)


def validate_poverty_status_mapping(
    variable: str, source_entity: str, target_entity: str, context: str
) -> None:
    """Reject undefined status aggregation before a generic mapper loses NaN."""
    if (
        variable in NULLABLE_SPM_POVERTY_VARIABLES
        and source_entity != target_entity
        and target_entity != "person"
    ):
        raise ValueError(
            f"{context}: nullable SPM poverty status '{variable}' cannot be mapped "
            f"from '{source_entity}' to '{target_entity}'. Aggregating statuses "
            "across entities has no defined measurement universe; use its native "
            "entity or project it to 'person'."
        )
