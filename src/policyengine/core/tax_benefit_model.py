from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .variable import Variable
    from .parameter import Parameter
    from .simulation import Simulation
    from .dataset import Dataset
    from .policy import Policy
    from .dynamic import Dynamic
    from .parameter_value import ParameterValue


class TaxBenefitModel(BaseModel):
    id: str
    description: str | None = None
