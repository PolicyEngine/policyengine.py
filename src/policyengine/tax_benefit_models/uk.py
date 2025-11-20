"""PolicyEngine UK tax-benefit model - imports from uk/ module."""

from importlib.util import find_spec

if find_spec("policyengine_uk") is not None:
    from .uk import (
        PolicyEngineUK,
        PolicyEngineUKDataset,
        PolicyEngineUKLatest,
        ProgrammeStatistics,
        UKYearData,
        create_datasets,
        ensure_datasets,
        general_policy_reform_analysis,
        load_datasets,
        uk_latest,
        uk_model,
    )

    __all__ = [
        "UKYearData",
        "PolicyEngineUKDataset",
        "create_datasets",
        "load_datasets",
        "ensure_datasets",
        "PolicyEngineUK",
        "PolicyEngineUKLatest",
        "uk_model",
        "uk_latest",
        "general_policy_reform_analysis",
        "ProgrammeStatistics",
    ]

    # Rebuild models to resolve forward references
    PolicyEngineUKDataset.model_rebuild()
    PolicyEngineUKLatest.model_rebuild()
else:
    __all__ = []
