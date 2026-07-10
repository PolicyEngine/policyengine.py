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

import os
from importlib.util import find_spec

from policyengine import outputs as outputs
from policyengine.core import Simulation as Simulation
from policyengine.execution import (
    EXECUTION_RECEIPT_CANONICALIZATION as EXECUTION_RECEIPT_CANONICALIZATION,
)
from policyengine.execution import (
    EXECUTION_RECEIPT_SCHEMA_VERSION as EXECUTION_RECEIPT_SCHEMA_VERSION,
)
from policyengine.execution import ArtifactIdentity as ArtifactIdentity
from policyengine.execution import (
    CertifiedReleaseManifest as CertifiedReleaseManifest,
)
from policyengine.execution import ExecutionReceipt as ExecutionReceipt
from policyengine.execution import PackageResolution as PackageResolution
from policyengine.execution import PackageVersion as PackageVersion
from policyengine.execution import (
    RequestedExecutionAliases as RequestedExecutionAliases,
)
from policyengine.execution import (
    ResolvedExecutionBundle as ResolvedExecutionBundle,
)
from policyengine.execution import RuntimeIdentity as RuntimeIdentity
from policyengine.execution import TraceReference as TraceReference
from policyengine.execution import canonical_content_hash as canonical_content_hash

_SKIP_COUNTRY_IMPORTS = os.environ.get("POLICYENGINE_SKIP_COUNTRY_IMPORTS") == "1"

if not _SKIP_COUNTRY_IMPORTS and find_spec("policyengine_us") is not None:
    from policyengine.tax_benefit_models import us as us
else:  # pragma: no cover
    us = None  # type: ignore[assignment]

if not _SKIP_COUNTRY_IMPORTS and find_spec("policyengine_uk") is not None:
    from policyengine.tax_benefit_models import uk as uk
else:  # pragma: no cover
    uk = None  # type: ignore[assignment]

__all__ = [
    "ArtifactIdentity",
    "CertifiedReleaseManifest",
    "EXECUTION_RECEIPT_CANONICALIZATION",
    "EXECUTION_RECEIPT_SCHEMA_VERSION",
    "ExecutionReceipt",
    "PackageResolution",
    "PackageVersion",
    "RequestedExecutionAliases",
    "ResolvedExecutionBundle",
    "RuntimeIdentity",
    "Simulation",
    "TraceReference",
    "canonical_content_hash",
    "outputs",
    "uk",
    "us",
]
