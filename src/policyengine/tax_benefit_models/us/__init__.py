"""PolicyEngine US tax-benefit model."""

from importlib.util import find_spec

if find_spec("policyengine_us") is not None:
    from policyengine.core import Dataset

    from .analysis import general_policy_reform_analysis
    from .datasets import PolicyEngineUSDataset, USYearData, create_datasets
    from .model import (
        PolicyEngineUS,
        PolicyEngineUSLatest,
        us_latest,
        us_model,
    )
    from .outputs import ProgramStatistics

    # Rebuild Pydantic models to resolve forward references
    Dataset.model_rebuild()
    USYearData.model_rebuild()
    PolicyEngineUSDataset.model_rebuild()
    PolicyEngineUSLatest.model_rebuild()

    __all__ = [
        "USYearData",
        "PolicyEngineUSDataset",
        "create_datasets",
        "PolicyEngineUS",
        "PolicyEngineUSLatest",
        "us_model",
        "us_latest",
        "general_policy_reform_analysis",
        "ProgramStatistics",
    ]
else:
    __all__ = []
