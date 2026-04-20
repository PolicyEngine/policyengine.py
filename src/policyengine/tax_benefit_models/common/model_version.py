"""Base class for country ``TaxBenefitModelVersion`` implementations.

The US and UK model-version classes share roughly 300 lines of loading logic:
manifest certification, the variable-copy loop over the country ``system``,
the parameter-copy loop, entity-relationship construction, and simple
``save`` / ``load`` passthroughs. Only ``run`` (and the country-specific
``managed_microsimulation`` helper) diverge enough to warrant per-country
implementations.

This module extracts the shared behaviour into ``MicrosimulationModelVersion``.
Country subclasses declare class-level metadata (``country_code``,
``package_name``, ``group_entities``, ``entity_variables``) and override a
handful of thin hooks (``_load_system``, ``_load_region_registry``,
``_dataset_class``, ``run``).
"""

from __future__ import annotations

import datetime
import os
import warnings
from difflib import get_close_matches
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Optional

import pandas as pd

from policyengine.core import (
    Parameter,
    ParameterNode,
    TaxBenefitModelVersion,
    Variable,
)
from policyengine.provenance.manifest import (
    certify_data_release_compatibility,
    get_release_manifest,
)
from policyengine.utils.entity_utils import build_entity_relationships
from policyengine.utils.parameter_labels import (
    build_scale_lookup,
    generate_label_for_parameter,
)

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


class MicrosimulationModelVersion(TaxBenefitModelVersion):
    """Shared init / save / load logic for country microsim model versions.

    Subclasses must set the four class attributes below and implement the
    country-specific hooks. ``run`` is intentionally left abstract: its
    country-specific logic (reform application, simulation builder, output
    post-processing) varies enough that a shared skeleton would hide real
    divergences.
    """

    # --- Subclass metadata -------------------------------------------------
    country_code: ClassVar[str] = ""
    """ISO-ish country identifier used by the release manifest ("us"/"uk")."""

    package_name: ClassVar[str] = ""
    """Distribution name used with ``importlib.metadata.version``."""

    group_entities: ClassVar[list[str]] = []
    """Group entities (non-person) for this country, in dataset order."""

    entity_variables: dict[str, list[str]] = {}
    """Variables to materialise per entity when writing output datasets."""

    # --- Construction ------------------------------------------------------
    def __init__(self, **kwargs: Any) -> None:
        if not self.country_code or not self.package_name:
            raise RuntimeError(
                f"{type(self).__name__} must declare country_code and "
                "package_name class attributes"
            )

        manifest = get_release_manifest(self.country_code)
        if kwargs.get("version") is None:
            kwargs["version"] = manifest.model_package.version

        installed_model_version = metadata.version(self.package_name)
        if installed_model_version != manifest.model_package.version:
            warnings.warn(
                f"Installed {self.package_name} version "
                f"({installed_model_version}) does not match the bundled "
                "policyengine.py manifest "
                f"({manifest.model_package.version}). Calculations will "
                "run against the installed version, but dataset "
                "compatibility is not guaranteed. To silence this "
                "warning, install the version pinned by the manifest.",
                UserWarning,
                stacklevel=2,
            )

        model_build_metadata = self._get_runtime_data_build_metadata()
        data_certification = certify_data_release_compatibility(
            self.country_code,
            runtime_model_version=installed_model_version,
            runtime_data_build_fingerprint=model_build_metadata.get(
                "data_build_fingerprint"
            ),
        )

        super().__init__(**kwargs)
        self.release_manifest = manifest
        self.model_package = manifest.model_package
        self.data_package = manifest.data_package
        self.default_dataset_uri = manifest.default_dataset_uri
        self.data_certification = data_certification
        self.region_registry = self._load_region_registry()
        self.id = f"{self.model.id}@{self.version}"

        system = self._load_system()
        self._populate_variables(system)
        self._populate_parameters(system)

    # --- Hooks ------------------------------------------------------------
    @classmethod
    def _get_runtime_data_build_metadata(cls) -> dict[str, Optional[str]]:
        """Return build metadata from the country package, if available."""
        raise NotImplementedError

    def _load_system(self):
        """Return the country package's ``system`` object."""
        raise NotImplementedError

    def _load_region_registry(self):
        """Return the country's ``RegionRegistry``."""
        raise NotImplementedError

    @property
    def _dataset_class(self):
        """Return the country's ``PolicyEngine{Country}Dataset`` class."""
        raise NotImplementedError

    # --- Shared loading helpers ------------------------------------------
    def _populate_variables(self, system) -> None:
        from policyengine_core.enums import Enum
        from policyengine_core.parameters.operations.get_parameter import (
            get_parameter,
        )

        for var_obj in system.variables.values():
            default_val = var_obj.default_value
            if var_obj.value_type is Enum:
                default_val = default_val.name
            elif var_obj.value_type is datetime.date:
                default_val = default_val.isoformat()

            variable = Variable(
                id=self.id + "-" + var_obj.name,
                name=var_obj.name,
                label=getattr(var_obj, "label", None),
                tax_benefit_model_version=self,
                entity=var_obj.entity.key,
                description=var_obj.documentation,
                data_type=(
                    var_obj.value_type if var_obj.value_type is not Enum else str
                ),
                default_value=default_val,
                value_type=var_obj.value_type,
            )
            if (
                hasattr(var_obj, "possible_values")
                and var_obj.possible_values is not None
            ):
                variable.possible_values = list(
                    map(
                        lambda x: x.name,
                        var_obj.possible_values._value2member_map_.values(),
                    )
                )
            # Resolve parameter-path adds/subtracts to concrete lists so
            # consumers always see list[str].
            for attr in ("adds", "subtracts"):
                value = getattr(var_obj, attr, None)
                if value is None:
                    continue
                if isinstance(value, str):
                    try:
                        param = get_parameter(system.parameters, value)
                        setattr(variable, attr, list(param("2025-01-01")))
                    except Exception:
                        setattr(variable, attr, None)
                else:
                    setattr(variable, attr, value)
            self.add_variable(variable)

    def _populate_parameters(self, system) -> None:
        from policyengine_core.parameters import Parameter as CoreParameter
        from policyengine_core.parameters import ParameterNode as CoreParameterNode

        scale_lookup = build_scale_lookup(system)

        for param_node in system.parameters.get_descendants():
            if isinstance(param_node, CoreParameter):
                parameter = Parameter(
                    id=self.id + "-" + param_node.name,
                    name=param_node.name,
                    label=generate_label_for_parameter(
                        param_node, system, scale_lookup
                    ),
                    tax_benefit_model_version=self,
                    description=param_node.description,
                    data_type=type(param_node(2025)),
                    unit=param_node.metadata.get("unit"),
                    _core_param=param_node,
                )
                self.add_parameter(parameter)
            elif isinstance(param_node, CoreParameterNode):
                node = ParameterNode(
                    id=self.id + "-" + param_node.name,
                    name=param_node.name,
                    label=param_node.metadata.get("label"),
                    description=param_node.description,
                    tax_benefit_model_version=self,
                )
                self.add_parameter_node(node)

    # --- Shared run-surface helpers --------------------------------------
    def _build_entity_relationships(self, dataset) -> pd.DataFrame:
        """Build a DataFrame mapping each person to their containing entities."""
        person_data = pd.DataFrame(dataset.data.person)
        return build_entity_relationships(person_data, self.group_entities)

    def resolve_entity_variables(
        self,
        simulation: Simulation,
    ) -> dict[str, list[str]]:
        """Merge :attr:`entity_variables` with ``simulation.extra_variables``.

        Returned dict has one key per known entity, value being the
        union of the bundled defaults and the caller's extras, with
        duplicates removed and original order preserved (defaults
        first, extras appended).

        Raises ``ValueError`` with close-match suggestions if the
        caller passes an unknown entity key or a variable name that
        does not resolve on the tax-benefit system's variable
        registry.
        """
        extras = dict(simulation.extra_variables or {})
        known_entities = set(self.entity_variables)
        unknown_entities = [e for e in extras if e not in known_entities]
        if unknown_entities:
            lines = [
                f"Simulation.extra_variables contains entity keys not "
                f"defined on {self.model.id} {self.version}:"
            ]
            for entity in unknown_entities:
                suggestions = get_close_matches(
                    entity, sorted(known_entities), n=1, cutoff=0.7
                )
                hint = f" (did you mean '{suggestions[0]}'?)" if suggestions else ""
                lines.append(f"  - '{entity}'{hint}")
            raise ValueError("\n".join(lines))

        known_variables = set(self.variables_by_name)
        unknown_variables: list[tuple[str, str]] = []
        for entity, names in extras.items():
            for name in names:
                if name not in known_variables:
                    unknown_variables.append((entity, name))
        if unknown_variables:
            lines = [
                f"Simulation.extra_variables contains variable names not "
                f"defined on {self.model.id} {self.version}:"
            ]
            for entity, name in unknown_variables:
                suggestions = get_close_matches(
                    name, sorted(known_variables), n=1, cutoff=0.7
                )
                hint = f" (did you mean '{suggestions[0]}'?)" if suggestions else ""
                lines.append(f"  - '{name}' (on '{entity}'){hint}")
            raise ValueError("\n".join(lines))

        resolved: dict[str, list[str]] = {}
        for entity, defaults in self.entity_variables.items():
            seen: set[str] = set()
            merged: list[str] = []
            for var in list(defaults) + list(extras.get(entity, [])):
                if var not in seen:
                    seen.add(var)
                    merged.append(var)
            resolved[entity] = merged
        return resolved

    def save(self, simulation: Simulation) -> None:
        """Persist the simulation's output dataset to its bundled filepath."""
        simulation.output_dataset.save()

    def load(self, simulation: Simulation) -> None:
        """Rehydrate the simulation's output dataset from disk.

        Loads timestamps from filesystem metadata when the file exists so
        serialised simulations round-trip ``created_at``/``updated_at``.
        """
        filepath = str(
            Path(simulation.dataset.filepath).parent / (simulation.id + ".h5")
        )

        simulation.output_dataset = self._dataset_class(
            id=simulation.id,
            name=simulation.dataset.name,
            description=simulation.dataset.description,
            filepath=filepath,
            year=simulation.dataset.year,
            is_output_dataset=True,
        )

        if os.path.exists(filepath):
            simulation.created_at = datetime.datetime.fromtimestamp(
                os.path.getctime(filepath)
            )
            simulation.updated_at = datetime.datetime.fromtimestamp(
                os.path.getmtime(filepath)
            )
