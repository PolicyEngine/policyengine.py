from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

from .release_manifest import CountryReleaseManifest, PackageVersion
from .tax_benefit_model import TaxBenefitModel

if TYPE_CHECKING:
    from .parameter import Parameter
    from .parameter_node import ParameterNode
    from .parameter_value import ParameterValue
    from .region import Region, RegionRegistry
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
    parameter_nodes: list["ParameterNode"] = Field(default_factory=list)

    # Region registry for geographic simulations
    region_registry: "RegionRegistry | None" = Field(
        default=None, description="Registry of supported geographic regions"
    )
    release_manifest: CountryReleaseManifest | None = Field(
        default=None,
        exclude=True,
    )
    model_package: PackageVersion | None = Field(default=None)
    data_package: PackageVersion | None = Field(default=None)
    default_dataset_uri: str | None = Field(default=None)

    @property
    def parameter_values(self) -> list["ParameterValue"]:
        """Aggregate all parameter values from all parameters."""
        return [
            pv for parameter in self.parameters for pv in parameter.parameter_values
        ]

    # Lookup dicts for O(1) access (excluded from serialization)
    variables_by_name: dict[str, "Variable"] = Field(default_factory=dict, exclude=True)
    parameters_by_name: dict[str, "Parameter"] = Field(
        default_factory=dict, exclude=True
    )
    parameter_nodes_by_name: dict[str, "ParameterNode"] = Field(
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

    def add_parameter_node(self, node: "ParameterNode") -> None:
        """Add a parameter node and index it for fast lookup."""
        self.parameter_nodes.append(node)
        self.parameter_nodes_by_name[node.name] = node

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

    def get_parameter_node(self, name: str) -> "ParameterNode":
        """Get a parameter node by name (O(1) lookup)."""
        if name in self.parameter_nodes_by_name:
            return self.parameter_nodes_by_name[name]
        raise ValueError(
            f"ParameterNode '{name}' not found in {self.model.id} version {self.version}"
        )

    def get_region(self, code: str) -> "Region | None":
        """Get a region by its code.

        Args:
            code: Region code (e.g., 'state/ca', 'place/NJ-57000')

        Returns:
            The Region if found, None if not found or no region registry
        """
        if self.region_registry is None:
            return None
        return self.region_registry.get(code)

    @property
    def release_bundle(self) -> dict[str, str | None]:
        return {
            "country_id": self.release_manifest.country_id
            if self.release_manifest is not None
            else None,
            "policyengine_version": self.release_manifest.policyengine_version
            if self.release_manifest is not None
            else None,
            "model_package": self.model_package.name
            if self.model_package is not None
            else None,
            "model_version": self.version,
            "data_package": self.data_package.name
            if self.data_package is not None
            else None,
            "data_version": self.data_package.version
            if self.data_package is not None
            else None,
            "default_dataset_uri": self.default_dataset_uri,
        }
    def __repr__(self) -> str:
        # Give the id and version, and the number of variables, parameters, parameter nodes, parameter values
        return f"<TaxBenefitModelVersion id={self.id} variables={len(self.variables)} parameters={len(self.parameters)} parameter_nodes={len(self.parameter_nodes)} parameter_values={len(self.parameter_values)}>"
