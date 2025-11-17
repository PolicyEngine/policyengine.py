"""PolicyEngine UK tax-benefit model - imports from uk/ module."""

from .uk import (
    PolicyEngineUK,
    PolicyEngineUKDataset,
    PolicyEngineUKLatest,
    ProgrammeStatistics,
    UKYearData,
    create_datasets,
    general_policy_reform_analysis,
    uk_latest,
    uk_model,
)

__all__ = [
    "UKYearData",
    "PolicyEngineUKDataset",
    "create_datasets",
    "PolicyEngineUK",
    "PolicyEngineUKLatest",
    "uk_model",
    "uk_latest",
    "general_policy_reform_analysis",
    "ProgrammeStatistics",
]

# Rebuild models to resolve forward references
from policyengine.core import Dataset

Dataset.model_rebuild()
UKYearData.model_rebuild()
PolicyEngineUKDataset.model_rebuild()
PolicyEngineUKLatest.model_rebuild()
