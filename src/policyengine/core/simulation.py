import logging
from datetime import datetime
from typing import Any, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from .cache import LRUCache
from .dataset import Dataset
from .dynamic import Dynamic
from .policy import Policy
from .scoping_strategy import ScopingStrategy
from .tax_benefit_model_version import TaxBenefitModelVersion

logger = logging.getLogger(__name__)

_cache: LRUCache["Simulation"] = LRUCache(max_size=100)


class Simulation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    policy: Optional[Union[Policy, dict[str, Any]]] = Field(
        default=None,
        description=(
            "Reform policy. Pass a ``Policy`` directly, or a flat "
            "``{'param.path': value}`` / ``{'param.path': {date: value}}`` "
            "dict and it will be compiled against "
            "``tax_benefit_model_version`` at run time."
        ),
    )
    dynamic: Optional[Union[Dynamic, dict[str, Any]]] = Field(
        default=None,
        description=(
            "Behavioural-response overlay. Same dict shape as ``policy``."
        ),
    )
    dataset: Dataset = None

    scoping_strategy: Optional[ScopingStrategy] = Field(
        default=None,
        description="Strategy for scoping dataset to a sub-national region",
    )

    extra_variables: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Additional variables to calculate beyond the model version's "
            "default entity_variables, keyed by entity name. Use when a "
            "caller needs variables that are not in the bundled default set."
        ),
    )

    tax_benefit_model_version: TaxBenefitModelVersion = None

    output_dataset: Optional[Dataset] = None

    @model_validator(mode="after")
    def _compile_dict_reforms(self) -> "Simulation":
        """Coerce dict ``policy`` / ``dynamic`` inputs into proper objects.

        We can't do this in a ``field_validator`` because compiling a
        reform requires the ``tax_benefit_model_version`` (for parameter
        path validation) and the ``dataset.year`` (for the scalar
        effective-date default). By the time ``model_validator(mode="after")``
        fires, both are already on ``self``.
        """
        from policyengine.tax_benefit_models.common.reform import (
            compile_reform_to_dynamic,
            compile_reform_to_policy,
        )

        if isinstance(self.policy, dict):
            if self.tax_benefit_model_version is None:
                raise ValueError(
                    "Cannot compile a dict policy without "
                    "tax_benefit_model_version; pass model_version or a Policy."
                )
            year = getattr(self.dataset, "year", None)
            self.policy = compile_reform_to_policy(
                self.policy,
                year=year,
                model_version=self.tax_benefit_model_version,
            )
        if isinstance(self.dynamic, dict):
            if self.tax_benefit_model_version is None:
                raise ValueError(
                    "Cannot compile a dict dynamic without "
                    "tax_benefit_model_version; pass model_version or a Dynamic."
                )
            year = getattr(self.dataset, "year", None)
            self.dynamic = compile_reform_to_dynamic(
                self.dynamic,
                year=year,
                model_version=self.tax_benefit_model_version,
            )
        return self

    def run(self):
        self.tax_benefit_model_version.run(self)

    def ensure(self):
        cached_result = _cache.get(self.id)
        if cached_result:
            self.output_dataset = cached_result.output_dataset
            return
        try:
            self.tax_benefit_model_version.load(self)
        except FileNotFoundError:
            self.run()
            self.save()
        except Exception:
            logger.warning(
                "Unexpected error loading simulation %s; falling back to run()",
                self.id,
                exc_info=True,
            )
            self.run()
            self.save()

        _cache.add(self.id, self)

    def save(self):
        """Save the simulation's output dataset."""
        self.tax_benefit_model_version.save(self)

    def load(self):
        """Load the simulation's output dataset."""
        self.tax_benefit_model_version.load(self)

    @property
    def release_bundle(self) -> dict[str, Optional[str]]:
        bundle = (
            self.tax_benefit_model_version.release_bundle
            if self.tax_benefit_model_version is not None
            else {}
        )
        return {
            **bundle,
            "dataset_filepath": self.dataset.filepath
            if self.dataset is not None
            else None,
        }
