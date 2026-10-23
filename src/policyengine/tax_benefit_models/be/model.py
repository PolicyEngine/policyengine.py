"""Axiom-backed Belgium pilot model version.

Unlike the US and UK model versions, Belgium runs on the Axiom rules
engine: statutes encoded as RuleSpec YAML in TheAxiomFoundation/rulespec-be,
compiled and executed by ``axiom-rules-engine``, and driven over populace
entity tables through the ``microcosm.frame`` Axiom adapter. There is no
policyengine-core country package and no certified release manifest, so this
version subclasses ``TaxBenefitModelVersion`` directly and stays outside the
managed-release machinery.

Requirements (neither is on PyPI yet):

- ``microcosm-frame`` from PolicyEngine/microcosm
  (``packages/microcosm-frame``; Python 3.13+)
- ``axiom-rules-engine`` from TheAxiomFoundation/axiom-rules-engine (PyO3
  dense extension; its source Python package currently requires Python 3.14)
- a checkout of TheAxiomFoundation/rulespec-be, passed as ``rulespec_root``

These are source dependencies with no jointly released compatibility set.
The current Microcosm adapter and Axiom checkout must agree on the dense
``CompiledDenseProgram.from_file`` signature (including canonical RuleSpec
roots). The deterministic tests in this repository cover PolicyEngine's
integration invariants without pretending to execute statutes; the opt-in
source-stack test executes the real engine once compatible checkouts and the
dense extension are installed.

Scope: the composed worker pipeline only — employee social security
contributions (13.07 percent ordinary worker contribution) and personal
income tax before withholding for wage earners under individual assessment.
Dependants, joint assessment, other income categories, and employment tax
reductions are not yet encoded (TheAxiomFoundation/rulespec-be#1).
"""

import json
from copy import deepcopy
from hashlib import sha256
from importlib import metadata as importlib_metadata
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Union

import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import TaxBenefitModel, TaxBenefitModelVersion

from .datasets import (
    BEYearData,
    PopulaceBelgiumDataset,
    _person_with_household_weights,
)

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation

PILOT_MODULE = "be/statutes/income_tax/individual/pilot_worker_oracle_pipeline.yaml"
REMUNERATION = "belgium_pit_article_23_worker_remuneration"
EMPLOYEE_SSC = "belgium_employee_social_security_ordinary_worker_contribution"
PIT_BEFORE_WITHHOLDING = "belgium_pit_pilot_federal_and_local_tax_before_withholding"

#: Pipeline inputs the pilot supplies as scalars when the dataset does not
#: carry them (rulespec stage boundaries are supplied inputs by convention).
#: The work-bonus reference wage bridges 0 -> worker remuneration inside the
#: pipeline, so the scalar default keeps the statutory low-wage bonus active.
SUPPLIED_DEFAULTS: dict[str, Union[float, bool]] = {
    "belgium_pit_article_466_tax_share_on_nonprofessional_movable_income": 0.0,
    "belgium_pit_article_466bis_hypothetical_total_tax_if_treaty_exempt_foreign_professional_income_were_belgian": 0.0,
    "belgium_pit_article_466bis_treaty_exempt_foreign_professional_income_base_applies": False,
    "belgium_worker_work_bonus_supplied_reference_annual_remuneration": 0.0,
    "belgium_pit_communal_additional_tax_rate": 0.0,
    "belgium_pit_agglomeration_additional_tax_rate": 0.0,
}


class AxiomBelgium(TaxBenefitModel):
    id: str = "axiom-rulespec-be"
    description: str = (
        "Belgium tax rules encoded as RuleSpec (TheAxiomFoundation/rulespec-be), "
        "executed by the Axiom rules engine over populace entity tables."
    )


be_model = AxiomBelgium()


class AxiomBelgiumPilot(TaxBenefitModelVersion):
    """Pilot Belgium model version: worker SSC and PIT via Axiom."""

    country_code: ClassVar[str] = "be"

    rulespec_root: str
    period: Optional[int] = None
    output_variables: list[str] = [EMPLOYEE_SSC, PIT_BEFORE_WITHHOLDING]
    communal_additional_tax_rate: float = 0.0
    runtime_provenance: dict[str, Any]

    def __init__(self, **kwargs: Any) -> None:
        rulespec_root = Path(kwargs["rulespec_root"]).expanduser().resolve()
        runtime_provenance = _build_runtime_provenance(rulespec_root)
        version = _provenance_version(runtime_provenance)
        kwargs["rulespec_root"] = str(rulespec_root)
        kwargs["runtime_provenance"] = runtime_provenance
        kwargs["model"] = be_model
        # This is a content identity, not the unrelated 0.1.0 version shared
        # by the source-only Python wrapper and dense-extension distributions.
        kwargs["version"] = version
        kwargs["id"] = f"{be_model.id}@{version}"
        super().__init__(**kwargs)

    def run(self, simulation: "Simulation") -> "Simulation":
        current_provenance = _build_runtime_provenance(Path(self.rulespec_root))
        if current_provenance != self.runtime_provenance:
            raise RuntimeError(
                "The RuleSpec/Axiom runtime changed after this Belgium model "
                "version was constructed; construct a new AxiomBelgiumPilot "
                "so its content identity matches the code that will execute."
            )
        Frame, WeightKind, Weights, BE_SCHEMA, AxiomEngine = _load_axiom_runtime()

        rulespec_root = Path(self.rulespec_root)
        module = rulespec_root / PILOT_MODULE
        if not module.exists():
            raise FileNotFoundError(
                f"rulespec-be pilot module not found at {module}; pass a "
                "checkout of TheAxiomFoundation/rulespec-be as rulespec_root."
            )

        dataset = simulation.dataset
        assert isinstance(dataset, PopulaceBelgiumDataset)
        if dataset.data is None:
            dataset.load()
        assert dataset.data is not None

        household = pd.DataFrame(dataset.data.household).copy()
        person = _person_with_household_weights(
            pd.DataFrame(dataset.data.person),
            household,
        )
        for name, value in SUPPLIED_DEFAULTS.items():
            if name not in person.columns:
                person[name] = value
        person["belgium_pit_communal_additional_tax_rate"] = (
            self.communal_additional_tax_rate
        )

        weights = {
            "household": Weights(
                values=household["household_weight"].to_numpy(),
                kind=WeightKind.CALIBRATED,
            )
        }
        # The frame kernel owns weight columns (typed Weights vectors);
        # they stay on the pe.py-side MicroDataFrames only.
        frame = Frame(
            {
                "person": person.drop(columns=["person_weight"]),
                "household": household.drop(columns=["household_weight"]),
            },
            BE_SCHEMA,
            weights,
        )
        policy_period = self.period if self.period is not None else dataset.year
        engine = AxiomEngine(module, rulespec_roots=(rulespec_root,))
        outputs = engine.materialize(frame, self.output_variables, policy_period)
        for name, values in outputs.items():
            person[name] = values

        output_metadata = deepcopy(dataset.metadata)
        prior_runs = output_metadata.get("policyengine_axiom_runs", [])
        if not isinstance(prior_runs, list):
            raise ValueError(
                "Belgium dataset metadata field 'policyengine_axiom_runs' "
                "must be a list when present."
            )
        output_metadata["policyengine_axiom_runs"] = [
            *deepcopy(prior_runs),
            {
                "dataset_year": dataset.year,
                "policy_period": policy_period,
                "model_version": self.version,
                "configuration": {
                    "communal_additional_tax_rate": (self.communal_additional_tax_rate),
                    "output_variables": list(self.output_variables),
                },
                "provenance": deepcopy(self.runtime_provenance),
            },
        ]

        simulation.output_dataset = PopulaceBelgiumDataset(
            id=simulation.id,
            name=dataset.name,
            description=dataset.description,
            # Derived in-memory output: never alias the source HDF5 path. A
            # caller may choose a new destination explicitly before saving.
            filepath=None,
            year=dataset.year,
            policy_period=policy_period,
            is_output_dataset=True,
            metadata=output_metadata,
            data=BEYearData(
                person=MicroDataFrame(person, weights="person_weight"),
                household=MicroDataFrame(household, weights="household_weight"),
            ),
        )
        return simulation

    def save(self, simulation: "Simulation") -> None:
        """Pilot simulations are recomputed, not persisted."""

    def load(self, simulation: "Simulation") -> None:
        raise FileNotFoundError("Pilot simulations are recomputed, not persisted.")


def _load_axiom_runtime() -> tuple[Any, Any, Any, Any, Any]:
    """Load the source-only Microcosm/Axiom runtime at the execution boundary."""

    try:
        from microcosm.frame import Frame, WeightKind, Weights
        from microcosm.frame.adapters.axiom import BE_SCHEMA, AxiomEngine
    except ImportError as error:
        raise ImportError(
            "The Belgium pilot needs microcosm-frame "
            "(PolicyEngine/microcosm, packages/microcosm-frame) and "
            "axiom-rules-engine (TheAxiomFoundation/axiom-rules-engine) "
            "with its dense extension; install compatible source checkouts."
        ) from error
    return Frame, WeightKind, Weights, BE_SCHEMA, AxiomEngine


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _rulespec_tree_sha256(root: Path) -> str:
    """Hash every Belgian RuleSpec YAML path and byte payload deterministically."""

    country_root = root / "be"
    files = sorted(
        path
        for path in country_root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".yaml", ".yml"}
    )
    if not files:
        raise FileNotFoundError(
            f"No Belgian RuleSpec YAML files found below {country_root}."
        )
    digest = sha256()
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _module_sha256(module_name: str) -> str:
    try:
        spec = find_spec(module_name)
    except (ImportError, ModuleNotFoundError) as error:
        raise ImportError(
            f"The Belgium pilot cannot locate runtime module {module_name!r}."
        ) from error
    if spec is None or spec.origin is None:
        raise ImportError(
            f"The Belgium pilot cannot locate runtime module {module_name!r}."
        )
    path = Path(spec.origin)
    if not path.is_file():
        raise ImportError(
            f"Runtime module {module_name!r} has no hashable file at {path}."
        )
    return _sha256_file(path)


def _package_tree_sha256(package_name: str) -> str:
    """Hash every Python source path and payload in an import package."""
    try:
        spec = find_spec(package_name)
    except (ImportError, ModuleNotFoundError) as error:
        raise ImportError(
            f"The Belgium pilot cannot locate runtime package {package_name!r}."
        ) from error
    locations = None if spec is None else spec.submodule_search_locations
    if not locations:
        raise ImportError(
            f"Runtime package {package_name!r} has no hashable source tree."
        )

    roots = sorted(Path(location).resolve() for location in locations)
    files = [
        (root_index, root, path)
        for root_index, root in enumerate(roots)
        for path in sorted(root.rglob("*.py"))
        if path.is_file()
    ]
    if not files:
        raise ImportError(
            f"Runtime package {package_name!r} has no Python source files."
        )

    digest = sha256()
    for root_index, root, path in files:
        relative = f"{root_index}/{path.relative_to(root).as_posix()}".encode()
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _distribution_version(name: str) -> Optional[str]:
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        return None


def _build_runtime_provenance(rulespec_root: Path) -> dict[str, Any]:
    """Bind the exact RuleSpec corpus, adapter, wrapper, and native engine bytes."""

    module = rulespec_root / PILOT_MODULE
    if not module.is_file():
        raise FileNotFoundError(
            f"rulespec-be pilot module not found at {module}; pass a "
            "checkout of TheAxiomFoundation/rulespec-be as rulespec_root."
        )
    return {
        "rulespec": {
            "repository": "TheAxiomFoundation/rulespec-be",
            "module": PILOT_MODULE,
            "module_sha256": _sha256_file(module),
            "belgium_tree_sha256": _rulespec_tree_sha256(rulespec_root),
        },
        "runtime": {
            "microcosm_frame_version": _distribution_version("microcosm-frame"),
            "microcosm_frame_tree_sha256": _package_tree_sha256("microcosm.frame"),
            "microcosm_axiom_adapter_sha256": _module_sha256(
                "microcosm.frame.adapters.axiom"
            ),
            "axiom_python_version": _distribution_version("axiom-rules-engine"),
            "axiom_python_sha256": _module_sha256("axiom_rules_engine.dense"),
            "axiom_dense_version": _distribution_version("axiom-rules-engine-dense"),
            # The native binary embeds the Rust engine implementation. Its
            # full-file digest remains exact even while the source-only
            # packages reuse placeholder 0.1.0 distribution versions.
            "axiom_dense_sha256": _module_sha256("axiom_rules_engine_dense"),
        },
    }


def _provenance_version(provenance: dict[str, Any]) -> str:
    rulespec_sha = provenance["rulespec"]["belgium_tree_sha256"]
    canonical = json.dumps(
        provenance,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    runtime_sha = sha256(canonical).hexdigest()
    return f"rulespec-be@{rulespec_sha[:12]}+runtime@{runtime_sha[:12]}"
