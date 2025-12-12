"""PolicyEngine UK tax-benefit model."""

from importlib.util import find_spec

if find_spec("policyengine_uk") is not None:
    from policyengine.core import Dataset

    from .analysis import (
        UKHouseholdInput,
        UKHouseholdOutput,
        calculate_household_impact,
        economic_impact_analysis,
    )
    from .datasets import (
        PolicyEngineUKDataset,
        UKYearData,
        create_datasets,
        ensure_datasets,
        load_datasets,
    )
    from .model import (
        PolicyEngineUK,
        PolicyEngineUKLatest,
        uk_latest,
        uk_model,
    )
    from .outputs import ProgrammeStatistics

    # Rebuild Pydantic models to resolve forward references
    Dataset.model_rebuild()
    UKYearData.model_rebuild()
    PolicyEngineUKDataset.model_rebuild()
    PolicyEngineUKLatest.model_rebuild()

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
        "economic_impact_analysis",
        "calculate_household_impact",
        "UKHouseholdInput",
        "UKHouseholdOutput",
        "ProgrammeStatistics",
    ]
else:
    __all__ = []
