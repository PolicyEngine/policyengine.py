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
    model_config = {"arbitrary_types_allowed": True}

    id: str = Field(default_factory=lambda: str(uuid4()))
    model: TaxBenefitModel
    version: str
    description: str | None = None
    created_at: datetime | None = Field(default_factory=datetime.utcnow)

    variables: list["Variable"] = Field(default_factory=list)
    parameters: list["Parameter"] = Field(default_factory=list)

    @property
    def parameter_values(self) -> list["ParameterValue"]:
        """Aggregate all parameter values from all parameters."""
        return [
            pv
            for parameter in self.parameters
            for pv in parameter.parameter_values
        ]

    # Lookup dicts for O(1) access (excluded from serialization)
    variables_by_name: dict[str, "Variable"] = Field(
        default_factory=dict, exclude=True
    )
    parameters_by_name: dict[str, "Parameter"] = Field(
        default_factory=dict, exclude=True
    )

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

    def add_parameter(self, param: "Parameter") -> None:
        """Add a parameter and index it for fast lookup."""
        self.parameters.append(param)
        self.parameters_by_name[param.name] = param

    def add_variable(self, var: "Variable") -> None:
        """Add a variable and index it for fast lookup."""
        self.variables.append(var)
        self.variables_by_name[var.name] = var

    def get_parameter(self, name: str) -> "Parameter":
        """Get a parameter by name (O(1) lookup)."""
        if name in self.parameters_by_name:
            return self.parameters_by_name[name]
        raise ValueError(
            f"Parameter '{name}' not found in {self.model.id} version {self.version}"
        )

    def get_variable(self, name: str) -> "Variable":
        """Get a variable by name (O(1) lookup)."""
        if name in self.variables_by_name:
            return self.variables_by_name[name]
        raise ValueError(
            f"Variable '{name}' not found in {self.model.id} version {self.version}"
        )

    def __repr__(self) -> str:
        # Give the id and version, and the number of variables, parameters, parameter values
        return f"<TaxBenefitModelVersion id={self.id} variables={len(self.variables)} parameters={len(self.parameters)} parameter_values={len(self.parameter_values)}>"
