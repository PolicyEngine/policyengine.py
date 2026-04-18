import datetime
import warnings
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import (
    Parameter,
    ParameterNode,
    TaxBenefitModel,
    TaxBenefitModelVersion,
    Variable,
)
from policyengine.core.release_manifest import (
    certify_data_release_compatibility,
    dataset_logical_name,
    get_release_manifest,
    resolve_local_managed_dataset_source,
    resolve_managed_dataset_reference,
)
from policyengine.utils.entity_utils import (
    build_entity_relationships,
    filter_dataset_by_household_variable,
)
from policyengine.utils.parameter_labels import (
    build_scale_lookup,
    generate_label_for_parameter,
)

from .datasets import PolicyEngineUKDataset, UKYearData

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation

UK_GROUP_ENTITIES = ["benunit", "household"]


class PolicyEngineUK(TaxBenefitModel):
    id: str = "policyengine-uk"
    description: str = "The UK's open-source dynamic tax and benefit microsimulation model maintained by PolicyEngine."


uk_model = PolicyEngineUK()


def _get_runtime_data_build_metadata() -> dict[str, Optional[str]]:
    try:
        from policyengine_uk.build_metadata import get_data_build_metadata
    except ModuleNotFoundError as exc:
        if exc.name != "policyengine_uk.build_metadata":
            raise
        return {}

    return get_data_build_metadata() or {}


class PolicyEngineUKLatest(TaxBenefitModelVersion):
    model: TaxBenefitModel = uk_model
    version: str = None
    created_at: datetime.datetime = None

    entity_variables: dict[str, list[str]] = {
        "person": [
            # IDs and weights
            "person_id",
            "benunit_id",
            "household_id",
            "person_weight",
            # Demographics
            "age",
            "gender",
            "is_male",
            "is_adult",
            "is_SP_age",
            "is_child",
            # Income
            "employment_income",
            "self_employment_income",
            "pension_income",
            "private_pension_income",
            "savings_interest_income",
            "dividend_income",
            "property_income",
            "total_income",
            "earned_income",
            # Benefits
            "universal_credit",
            "child_benefit",
            "pension_credit",
            "income_support",
            "working_tax_credit",
            "child_tax_credit",
            # Tax
            "income_tax",
            "national_insurance",
        ],
        "benunit": [
            # IDs and weights
            "benunit_id",
            "benunit_weight",
            # Structure
            "family_type",
            # Income and benefits
            "universal_credit",
            "child_benefit",
            "pension_credit",
            "income_support",
            "working_tax_credit",
            "child_tax_credit",
        ],
        "household": [
            # IDs and weights
            "household_id",
            "household_weight",
            "household_count_people",
            # Income measures
            "household_net_income",
            "household_income_decile",
            "household_wealth_decile",
            "hbai_household_net_income",
            "equiv_hbai_household_net_income",
            "household_market_income",
            "household_gross_income",
            # Benefits and tax
            "household_benefits",
            "household_tax",
            "vat",
            # Housing
            "rent",
            "council_tax",
            "tenure_type",
            # Poverty measures
            "in_poverty_bhc",
            "in_poverty_ahc",
            "in_relative_poverty_bhc",
            "in_relative_poverty_ahc",
        ],
    }

    def __init__(self, **kwargs: dict):
        manifest = get_release_manifest("uk")
        if "version" not in kwargs or kwargs.get("version") is None:
            kwargs["version"] = manifest.model_package.version

        installed_model_version = metadata.version("policyengine-uk")
        if installed_model_version != manifest.model_package.version:
            warnings.warn(
                "Installed policyengine-uk version "
                f"({installed_model_version}) does not match the bundled "
                "policyengine.py manifest "
                f"({manifest.model_package.version}). Calculations will "
                "run against the installed version, but dataset "
                "compatibility is not guaranteed. To silence this "
                "warning, install the version pinned by the manifest.",
                UserWarning,
                stacklevel=2,
            )

        model_build_metadata = _get_runtime_data_build_metadata()
        data_certification = certify_data_release_compatibility(
            "uk",
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
        from policyengine_core.enums import Enum
        from policyengine_uk.system import system

        # Attach region registry
        from policyengine.countries.uk.regions import uk_region_registry

        self.region_registry = uk_region_registry

        self.id = f"{self.model.id}@{self.version}"

        for var_obj in system.variables.values():
            # Serialize default_value for JSON compatibility
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
                data_type=var_obj.value_type if var_obj.value_type is not Enum else str,
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
            # Extract and resolve adds/subtracts.
            # Core stores these as either list[str] or a parameter path string.
            # Resolve parameter paths to lists so consumers always get list[str].
            if hasattr(var_obj, "adds") and var_obj.adds is not None:
                if isinstance(var_obj.adds, str):
                    try:
                        from policyengine_core.parameters.operations.get_parameter import (
                            get_parameter,
                        )

                        param = get_parameter(system.parameters, var_obj.adds)
                        variable.adds = list(param("2025-01-01"))
                    except (ValueError, Exception):
                        variable.adds = None
                else:
                    variable.adds = var_obj.adds
            if hasattr(var_obj, "subtracts") and var_obj.subtracts is not None:
                if isinstance(var_obj.subtracts, str):
                    try:
                        from policyengine_core.parameters.operations.get_parameter import (
                            get_parameter,
                        )

                        param = get_parameter(system.parameters, var_obj.subtracts)
                        variable.subtracts = list(param("2025-01-01"))
                    except (ValueError, Exception):
                        variable.subtracts = None
                else:
                    variable.subtracts = var_obj.subtracts
            self.add_variable(variable)

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

    def _build_entity_relationships(
        self, dataset: PolicyEngineUKDataset
    ) -> pd.DataFrame:
        """Build a DataFrame mapping each person to their containing entities."""
        person_data = pd.DataFrame(dataset.data.person)
        return build_entity_relationships(person_data, UK_GROUP_ENTITIES)

    def _filter_dataset_by_household_variable(
        self,
        dataset: PolicyEngineUKDataset,
        variable_name: str,
        variable_value: str,
    ) -> PolicyEngineUKDataset:
        """Filter a dataset to only include households where a variable matches."""
        filtered = filter_dataset_by_household_variable(
            entity_data=dataset.data.entity_data,
            group_entities=UK_GROUP_ENTITIES,
            variable_name=variable_name,
            variable_value=variable_value,
        )
        return PolicyEngineUKDataset(
            id=dataset.id + f"_filtered_{variable_name}_{variable_value}",
            name=dataset.name,
            description=f"{dataset.description} (filtered: {variable_name}={variable_value})",
            filepath=dataset.filepath,
            year=dataset.year,
            is_output_dataset=dataset.is_output_dataset,
            data=UKYearData(
                person=filtered["person"],
                benunit=filtered["benunit"],
                household=filtered["household"],
            ),
        )

    def run(self, simulation: "Simulation") -> "Simulation":
        from policyengine_uk import Microsimulation
        from policyengine_uk.data import UKSingleYearDataset

        from policyengine.utils.parametric_reforms import (
            simulation_modifier_from_parameter_values,
        )

        assert isinstance(simulation.dataset, PolicyEngineUKDataset)

        dataset = simulation.dataset
        dataset.load()

        # Apply regional scoping if specified
        if simulation.scoping_strategy:
            scoped_data = simulation.scoping_strategy.apply(
                entity_data=dataset.data.entity_data,
                group_entities=UK_GROUP_ENTITIES,
                year=dataset.year,
            )
            dataset = PolicyEngineUKDataset(
                id=dataset.id + "_scoped",
                name=dataset.name,
                description=dataset.description,
                filepath=dataset.filepath,
                year=dataset.year,
                is_output_dataset=dataset.is_output_dataset,
                data=UKYearData(
                    person=scoped_data["person"],
                    benunit=scoped_data["benunit"],
                    household=scoped_data["household"],
                ),
            )
        elif simulation.filter_field and simulation.filter_value:
            dataset = self._filter_dataset_by_household_variable(
                dataset, simulation.filter_field, simulation.filter_value
            )

        input_data = UKSingleYearDataset(
            person=dataset.data.person,
            benunit=dataset.data.benunit,
            household=dataset.data.household,
            fiscal_year=dataset.year,
        )
        microsim = Microsimulation(dataset=input_data)

        if simulation.policy and simulation.policy.simulation_modifier is not None:
            simulation.policy.simulation_modifier(microsim)
        elif simulation.policy:
            modifier = simulation_modifier_from_parameter_values(
                simulation.policy.parameter_values
            )
            modifier(microsim)

        if simulation.dynamic and simulation.dynamic.simulation_modifier is not None:
            simulation.dynamic.simulation_modifier(microsim)
        elif simulation.dynamic:
            modifier = simulation_modifier_from_parameter_values(
                simulation.dynamic.parameter_values
            )
            modifier(microsim)

        data = {
            "person": pd.DataFrame(),
            "benunit": pd.DataFrame(),
            "household": pd.DataFrame(),
        }

        combined: dict[str, list[str]] = {
            entity: list(variables)
            for entity, variables in self.entity_variables.items()
        }
        for entity, extras in (simulation.extra_variables or {}).items():
            combined.setdefault(entity, [])
            for var in extras:
                if var not in combined[entity]:
                    combined[entity].append(var)
        for entity, variables in combined.items():
            if entity not in data:
                data[entity] = pd.DataFrame()
            for var in variables:
                data[entity][var] = microsim.calculate(
                    var, period=simulation.dataset.year, map_to=entity
                ).values

        data["person"] = MicroDataFrame(data["person"], weights="person_weight")
        data["benunit"] = MicroDataFrame(data["benunit"], weights="benunit_weight")
        data["household"] = MicroDataFrame(
            data["household"], weights="household_weight"
        )

        simulation.output_dataset = PolicyEngineUKDataset(
            id=simulation.id,
            name=dataset.name,
            description=dataset.description,
            filepath=str(
                Path(simulation.dataset.filepath).parent / (simulation.id + ".h5")
            ),
            year=simulation.dataset.year,
            is_output_dataset=True,
            data=UKYearData(
                person=data["person"],
                benunit=data["benunit"],
                household=data["household"],
            ),
        )

    def save(self, simulation: "Simulation"):
        """Save the simulation's output dataset."""
        simulation.output_dataset.save()

    def load(self, simulation: "Simulation"):
        """Load the simulation's output dataset."""
        import os

        filepath = str(
            Path(simulation.dataset.filepath).parent / (simulation.id + ".h5")
        )

        simulation.output_dataset = PolicyEngineUKDataset(
            id=simulation.id,
            name=simulation.dataset.name,
            description=simulation.dataset.description,
            filepath=filepath,
            year=simulation.dataset.year,
            is_output_dataset=True,
        )

        # Load timestamps from file system metadata
        if os.path.exists(filepath):
            simulation.created_at = datetime.datetime.fromtimestamp(
                os.path.getctime(filepath)
            )
            simulation.updated_at = datetime.datetime.fromtimestamp(
                os.path.getmtime(filepath)
            )


def _managed_release_bundle(
    dataset_uri: str,
    dataset_source: Optional[str] = None,
) -> dict[str, Optional[str]]:
    bundle = dict(uk_latest.release_bundle)
    bundle["runtime_dataset"] = dataset_logical_name(dataset_uri)
    bundle["runtime_dataset_uri"] = dataset_uri
    if dataset_source:
        bundle["runtime_dataset_source"] = dataset_source
    bundle["managed_by"] = "policyengine.py"
    return bundle


def managed_microsimulation(
    *,
    dataset: Optional[str] = None,
    allow_unmanaged: bool = False,
    **kwargs,
):
    """Construct a country-package Microsimulation pinned to this bundle.

    By default this enforces the dataset selection from the bundled
    `policyengine.py` release manifest. Arbitrary dataset URIs require
    `allow_unmanaged=True`.
    """

    from policyengine_uk import Microsimulation

    if "dataset" in kwargs:
        raise ValueError(
            "Pass `dataset=` directly to managed_microsimulation, not through "
            "**kwargs, so policyengine.py can enforce the release bundle."
        )

    dataset_uri = resolve_managed_dataset_reference(
        "uk",
        dataset,
        allow_unmanaged=allow_unmanaged,
    )
    dataset_source = resolve_local_managed_dataset_source(
        "uk",
        dataset_uri,
        allow_local_mirror=not (
            allow_unmanaged and dataset is not None and "://" in dataset
        ),
    )
    runtime_dataset = dataset_source
    if isinstance(dataset_source, str) and "hf://" not in dataset_source:
        from policyengine_uk.data.dataset_schema import (
            UKMultiYearDataset,
            UKSingleYearDataset,
        )

        if UKMultiYearDataset.validate_file_path(dataset_source, False):
            runtime_dataset = UKMultiYearDataset(dataset_source)
        elif UKSingleYearDataset.validate_file_path(dataset_source, False):
            runtime_dataset = UKSingleYearDataset(dataset_source)
    microsim = Microsimulation(dataset=runtime_dataset, **kwargs)
    microsim.policyengine_bundle = _managed_release_bundle(
        dataset_uri,
        dataset_source,
    )
    return microsim


uk_latest = PolicyEngineUKLatest()
