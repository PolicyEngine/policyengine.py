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
    """Population microsimulation over a certified dataset.

    Canonical call shape:

    .. code-block:: python

        import policyengine as pe
        from policyengine.core import Simulation

        datasets = pe.us.ensure_datasets(
            datasets=["hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"],
            years=[2026], data_folder="./data",
        )
        dataset = datasets["enhanced_cps_2024_2026"]

        # Baseline
        baseline = Simulation(dataset=dataset, tax_benefit_model_version=pe.us.model)

        # Reform — same flat dict shape as pe.us.calculate_household(reform=...).
        # Parameter path indexing uses "[0].amount" for scale/breakdown entries.
        reform = Simulation(
            dataset=dataset,
            tax_benefit_model_version=pe.us.model,
            policy={"gov.irs.credits.ctc.amount.base[0].amount": 3_000},
        )

        baseline.ensure()
        reform.ensure()

    The ``policy`` / ``dynamic`` kwargs accept either a ``Policy`` /
    ``Dynamic`` object or a flat ``{"param.path": value}`` /
    ``{"param.path": {date: value}}`` dict that is compiled against
    ``tax_benefit_model_version`` at construction time (unknown paths
    raise with close-match suggestions). Scalar values default to
    ``{dataset.year}-01-01`` as their effective date.

    See ``policyengine.core.scoping_strategy`` for sub-national scoping.
    """

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
        description=("Behavioural-response overlay. Same dict shape as ``policy``."),
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

        Runs at ``mode="after"`` because compiling needs both
        ``tax_benefit_model_version`` (for path validation) and
        ``dataset.year`` (for effective-date defaulting) — both on ``self``.
        """
        from policyengine.tax_benefit_models.common.reform import (
            compile_reform_to_dynamic,
            compile_reform_to_policy,
        )

        year = getattr(self.dataset, "year", None)
        for field, compiler in (
            ("policy", compile_reform_to_policy),
            ("dynamic", compile_reform_to_dynamic),
        ):
            value = getattr(self, field)
            if not isinstance(value, dict):
                continue
            if self.tax_benefit_model_version is None:
                raise ValueError(
                    f"Cannot compile a dict {field} without "
                    "tax_benefit_model_version; pass model_version or a "
                    f"{field.capitalize()}."
                )
            setattr(
                self,
                field,
                compiler(
                    value, year=year, model_version=self.tax_benefit_model_version
                ),
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
