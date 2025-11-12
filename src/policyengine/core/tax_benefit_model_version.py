from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .tax_benefit_model import TaxBenefitModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .variable import Variable
    from .parameter import Parameter
    from .parameter_value import ParameterValue
    from .simulation import Simulation


class TaxBenefitModelVersion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    model: TaxBenefitModel
    version: str
    description: str | None = None
    created_at: datetime | None = Field(default_factory=datetime.utcnow)

    variables: list["Variable"] = Field(default_factory=list)
    parameters: list["Parameter"] = Field(default_factory=list)
    parameter_values: list["ParameterValue"] = Field(default_factory=list)

    def run(self, simulation: "Simulation") -> "Simulation":
        raise NotImplementedError(
            "The TaxBenefitModel class must define a method to execute simulations."
        )

    def __repr__(self) -> str:
        # Give the id and version, and the number of variables, parameters, parameter values
        return f"<TaxBenefitModelVersion id={self.id} variables={len(self.variables)} parameters={len(self.parameters)} parameter_values={len(self.parameter_values)}>"
