from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from .variable import Variable
    from .parameter import Parameter
    from .simulation import Simulation
    from .dataset import Dataset
    from .policy import Policy
    from .dynamic import Dynamic


class TaxBenefitModel(BaseModel):
    id: str
    name: str
    description: str | None = None

    def run(self, simulation: "Simulation") -> "Simulation":
        pass