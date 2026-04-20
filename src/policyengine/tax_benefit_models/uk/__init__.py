"""PolicyEngine UK tax-benefit model.

.. code-block:: python

    import policyengine as pe

    result = pe.uk.calculate_household(
        people=[{"age": 30, "employment_income": 50000}],
        year=2026,
    )
    print(result.person[0].income_tax, result.household.hbai_household_net_income)
"""

from importlib.util import find_spec

if find_spec("policyengine_uk") is not None:
    from policyengine.core import Dataset
    from policyengine.outputs import ProgramStatistics

    from .analysis import economic_impact_analysis
    from .datasets import (
        PolicyEngineUKDataset,
        UKYearData,
        create_datasets,
        ensure_datasets,
        load_datasets,
    )
    from .household import calculate_household
    from .model import (
        PolicyEngineUK,
        PolicyEngineUKLatest,
        managed_microsimulation,
        uk_latest,
    )

    model = uk_latest
    """The pinned UK ``TaxBenefitModelVersion`` for this policyengine release."""

    Dataset.model_rebuild()
    UKYearData.model_rebuild()
    PolicyEngineUKDataset.model_rebuild()
    PolicyEngineUKLatest.model_rebuild()
    ProgramStatistics.model_rebuild()

    __all__ = [
        "UKYearData",
        "PolicyEngineUKDataset",
        "create_datasets",
        "load_datasets",
        "ensure_datasets",
        "PolicyEngineUK",
        "PolicyEngineUKLatest",
        "managed_microsimulation",
        "model",
        "uk_latest",
        "calculate_household",
        "economic_impact_analysis",
        "ProgramStatistics",
    ]
else:
    __all__ = []
