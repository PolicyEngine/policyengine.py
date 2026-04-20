"""PolicyEngine US tax-benefit model.

Typical usage (fresh session, no other imports required):

.. code-block:: python

    import policyengine as pe

    # Household calculator.
    result = pe.us.calculate_household(
        people=[{"age": 35, "employment_income": 60000}],
        tax_unit={"filing_status": "SINGLE"},
        year=2026,
    )
    print(result.tax_unit.income_tax)

    # Reform + extra variables.
    reformed = pe.us.calculate_household(
        people=[{"age": 35, "employment_income": 60000}],
        tax_unit={"filing_status": "SINGLE"},
        year=2026,
        reform={"gov.irs.credits.ctc.amount.adult_dependent": 1000},
        extra_variables=["adjusted_gross_income"],
    )
"""

from importlib.util import find_spec

if find_spec("policyengine_us") is not None:
    from policyengine.core import Dataset
    from policyengine.outputs import ProgramStatistics

    from .analysis import (
        BudgetaryImpact,
        calculate_budgetary_impact,
        economic_impact_analysis,
    )
    from .datasets import (
        PolicyEngineUSDataset,
        USYearData,
        create_datasets,
        ensure_datasets,
        load_datasets,
    )
    from .household import calculate_household
    from .model import (
        PolicyEngineUS,
        PolicyEngineUSLatest,
        managed_microsimulation,
        us_latest,
    )

    model = us_latest
    """The pinned US ``TaxBenefitModelVersion`` for this policyengine release."""

    Dataset.model_rebuild()
    USYearData.model_rebuild()
    PolicyEngineUSDataset.model_rebuild()
    PolicyEngineUSLatest.model_rebuild()
    ProgramStatistics.model_rebuild()

    __all__ = [
        "USYearData",
        "PolicyEngineUSDataset",
        "create_datasets",
        "load_datasets",
        "ensure_datasets",
        "PolicyEngineUS",
        "PolicyEngineUSLatest",
        "managed_microsimulation",
        "model",
        "us_latest",
        "calculate_household",
        "economic_impact_analysis",
        "calculate_budgetary_impact",
        "BudgetaryImpact",
        "ProgramStatistics",
    ]
else:
    __all__ = []
