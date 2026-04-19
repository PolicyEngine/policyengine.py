from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from policyengine.provenance.manifest import (
    CountryReleaseManifest,
    DataCertification,
    PackageVersion,
    get_data_release_manifest,
)
from policyengine.provenance.trace import build_trace_tro_from_release_bundle

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
    description: Optional[str] = None
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    variables: list["Variable"] = Field(default_factory=list)
    parameters: list["Parameter"] = Field(default_factory=list)
    parameter_nodes: list["ParameterNode"] = Field(default_factory=list)

    # Region registry for geographic simulations
    region_registry: "Optional[RegionRegistry]" = Field(
        default=None, description="Registry of supported geographic regions"
    )
    release_manifest: Optional[CountryReleaseManifest] = Field(
        default=None,
        exclude=True,
    )
    model_package: Optional[PackageVersion] = Field(default=None)
    data_package: Optional[PackageVersion] = Field(default=None)
    default_dataset_uri: Optional[str] = Field(default=None)
    data_certification: Optional[DataCertification] = Field(default=None)

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

    def get_region(self, code: str) -> "Optional[Region]":
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
    def release_bundle(self) -> dict[str, Optional[str]]:
        manifest_certification = (
            self.release_manifest.certification
            if self.release_manifest is not None
            else None
        )
        certification = self.data_certification or manifest_certification
        certified_data_artifact = (
            self.release_manifest.certified_data_artifact
            if self.release_manifest is not None
            else None
        )
        return {
            "bundle_id": self.release_manifest.bundle_id
            if self.release_manifest is not None
            else None,
            "country_id": self.release_manifest.country_id
            if self.release_manifest is not None
            else None,
            "policyengine_version": self.release_manifest.policyengine_version
            if self.release_manifest is not None
            else None,
            "model_package": self.model_package.name
            if self.model_package is not None
            else None,
            "model_version": self.model_package.version
            if self.model_package is not None
            else None,
            "data_package": self.data_package.name
            if self.data_package is not None
            else None,
            "data_version": self.data_package.version
            if self.data_package is not None
            else None,
            "default_dataset": self.release_manifest.default_dataset
            if self.release_manifest is not None
            else None,
            "default_dataset_uri": self.default_dataset_uri,
            "certified_data_build_id": (
                certification.data_build_id
                if certification is not None
                else (
                    certified_data_artifact.build_id
                    if certified_data_artifact is not None
                    else None
                )
            ),
            "certified_data_artifact_sha256": (
                certified_data_artifact.sha256
                if certified_data_artifact is not None
                else None
            ),
            "data_build_model_version": (
                certification.built_with_model_version
                if certification is not None
                else None
            ),
            "data_build_model_git_sha": (
                certification.built_with_model_git_sha
                if certification is not None
                else None
            ),
            "data_build_fingerprint": (
                certification.data_build_fingerprint
                if certification is not None
                else None
            ),
            "compatibility_basis": (
                certification.compatibility_basis if certification is not None else None
            ),
            "certified_by": (
                certification.certified_by if certification is not None else None
            ),
        }

    @property
    def trace_tro(self) -> dict:
        """Build a TRACE TRO for this certified bundle.

        Fetches the published data release manifest so the TRO can pin
        the exact dataset sha256. Requires a bundled release manifest.
        """
        if self.release_manifest is None:
            raise ValueError(
                "TRACE TRO export requires a bundled country release manifest."
            )
        data_release_manifest = get_data_release_manifest(
            self.release_manifest.country_id
        )
        return build_trace_tro_from_release_bundle(
            self.release_manifest,
            data_release_manifest,
            certification=self.data_certification,
        )

    def __repr__(self) -> str:
        # Give the id and version, and the number of variables, parameters, parameter nodes, parameter values
        return f"<TaxBenefitModelVersion id={self.id} variables={len(self.variables)} parameters={len(self.parameters)} parameter_nodes={len(self.parameter_nodes)} parameter_values={len(self.parameter_values)}>"
