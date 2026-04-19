"""PolicyEngine — one Python API for tax and benefit policy.

Canonical entry points for a fresh coding session:

.. code-block:: python

    import policyengine as pe

    # Single-household calculator (US).
    result = pe.us.calculate_household(
        people=[{"age": 35, "employment_income": 60000}],
        tax_unit={"filing_status": "SINGLE"},
        year=2026,
        reform={"gov.irs.credits.ctc.amount.adult_dependent": 1000},
    )
    print(result.tax_unit.income_tax, result.household.household_net_income)

    # UK:
    uk_result = pe.uk.calculate_household(
        people=[{"age": 30, "employment_income": 50000}],
        year=2026,
    )

    # Lower-level microsimulation building blocks.
    from policyengine import Simulation  # or: pe.Simulation

Each country module exposes ``calculate_household``, ``model``
(the pinned ``TaxBenefitModelVersion``), and the microsim helpers.
"""

from importlib.util import find_spec

from policyengine.core import Simulation as Simulation

if find_spec("policyengine_us") is not None:
    from policyengine.tax_benefit_models import us as us
else:  # pragma: no cover
    us = None  # type: ignore[assignment]

if find_spec("policyengine_uk") is not None:
    from policyengine.tax_benefit_models import uk as uk
else:  # pragma: no cover
    uk = None  # type: ignore[assignment]

__all__ = ["Simulation", "uk", "us"]
