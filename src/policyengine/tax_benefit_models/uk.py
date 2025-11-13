"""PolicyEngine UK tax-benefit model - imports from uk/ module."""

from .uk import *

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
PolicyEngineUKDataset.model_rebuild()
PolicyEngineUKLatest.model_rebuild()
