"""PolicyEngine UK tax-benefit model."""

from .analysis import general_policy_reform_analysis
from .datasets import PolicyEngineUKDataset, UKYearData, create_datasets
from .model import PolicyEngineUK, PolicyEngineUKLatest, uk_latest, uk_model
from .outputs import ProgrammeStatistics

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
