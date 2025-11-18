from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

from .tax_benefit_model import TaxBenefitModel

if TYPE_CHECKING:
    from .parameter import Parameter
    from .parameter_value import ParameterValue
    from .simulation import Simulation
    from .variable import Variable


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

    def save(self, simulation: "Simulation"):
        raise NotImplementedError(
            "The TaxBenefitModel class must define a method to save simulations."
        )

    def load(self, simulation: "Simulation"):
        raise NotImplementedError(
            "The TaxBenefitModel class must define a method to load simulations."
        )

    def get_parameter(self, name: str) -> "Parameter":
        """Get a parameter by name.

        Args:
            name: The parameter name (e.g., "gov.hmrc.income_tax.allowances.personal_allowance.amount")

        Returns:
            Parameter: The matching parameter

        Raises:
            ValueError: If parameter not found
        """
        for param in self.parameters:
            if param.name == name:
                return param
        raise ValueError(
            f"Parameter '{name}' not found in {self.model.id} version {self.version}"
        )

    def get_variable(self, name: str) -> "Variable":
        """Get a variable by name.

        Args:
            name: The variable name (e.g., "income_tax", "household_net_income")

        Returns:
            Variable: The matching variable

        Raises:
            ValueError: If variable not found
        """
        for var in self.variables:
            if var.name == name:
                return var
        raise ValueError(
            f"Variable '{name}' not found in {self.model.id} version {self.version}"
        )

    def __repr__(self) -> str:
        # Give the id and version, and the number of variables, parameters, parameter values
        return f"<TaxBenefitModelVersion id={self.id} variables={len(self.variables)} parameters={len(self.parameters)} parameter_values={len(self.parameter_values)}>"
