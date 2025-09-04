"""PolicyEngine models package.

This package splits the previous single-module models into submodules while
preserving the original import surface. You can continue using:

    from policyengine.models import Simulation, Dataset, ...

"""

from .dataset import Dataset
from .dynamics import Dynamics
from .enums import DatasetType, OperationStatus
from .parameter import Parameter, ParameterValue
from .policy import Policy
from .reports import (
    Report,
    ReportElement,
)
from .simulation import Simulation
from .variable import Variable
from .single_year_dataset import SingleYearDataset
from .user import (
    User,
    UserPolicy,
    UserSimulation,
    UserReport,
    UserReportElement,
)

# Resolve forward references for Pydantic models that reference each other
try:
    Policy.model_rebuild()
    Dynamics.model_rebuild()
    ParameterValue.model_rebuild()
    Report.model_rebuild()
    ReportElement.model_rebuild()
    # Data items rebuilt when their modules are imported directly
    UserPolicy.model_rebuild()
    UserSimulation.model_rebuild()
    UserReport.model_rebuild()
    UserReportElement.model_rebuild()
except Exception:
    # In case of partial imports during docs or static analysis
    pass
