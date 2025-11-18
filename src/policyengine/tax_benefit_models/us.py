"""PolicyEngine US tax-benefit model - imports from us/ module."""

from importlib.util import find_spec

if find_spec("policyengine_us") is not None:
    from .us import (
        PolicyEngineUS,
        PolicyEngineUSDataset,
        PolicyEngineUSLatest,
        ProgramStatistics,
        USYearData,
        create_datasets,
        ensure_datasets,
        general_policy_reform_analysis,
        load_datasets,
        us_latest,
        us_model,
    )

    __all__ = [
        "USYearData",
        "PolicyEngineUSDataset",
        "create_datasets",
        "load_datasets",
        "ensure_datasets",
        "PolicyEngineUS",
        "PolicyEngineUSLatest",
        "us_model",
        "us_latest",
        "general_policy_reform_analysis",
        "ProgramStatistics",
    ]

    # Rebuild models to resolve forward references
    PolicyEngineUSDataset.model_rebuild()
    PolicyEngineUSLatest.model_rebuild()
else:
    __all__ = []
