"""Execute the NZ official-reform entitlement module through real Axiom.

This is an opt-in, source-only PolicyEngine integration, not policyengine-nz
or a certified NZ bundle. The module computes legal family entitlement deltas;
Treasury cash/accrual timing, debt impairment, and petrol-trigger scenarios are
separate unimplemented bridges. Ordinary Simulation reform/dynamic/scoping
controls are rejected because this pilot does not implement them.
"""

import json
import subprocess
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from importlib import metadata as importlib_metadata
from importlib.util import find_spec
from numbers import Real
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_integer_dtype, is_numeric_dtype
from pydantic import Field

from policyengine.core import TaxBenefitModel, TaxBenefitModelVersion

from . import datasets as nz_datasets
from .datasets import PopulaceNewZealandDataset, year_data_from_frame

if TYPE_CHECKING:
    from policyengine.core import Simulation

PILOT_MODULE = "nz/policies/budget/official_budget_reform_replication.yaml"
TRANSPORT_CONTRACT = "data/microsimulation/official-budget-reform-transport.json"
WFF_ABATEMENT_CHANGE = "budget_2025_wff_abatement_entitlement_change"
IWTC_CHANGE = "budget_2026_iwtc_entitlement_change"
OUTPUTS = [WFF_ABATEMENT_CHANGE, IWTC_CHANGE]
POLICY_PERIOD = {"start": "2026-04-01", "end": "2027-03-31", "kind": "tax_year"}


class AxiomNewZealand(TaxBenefitModel):
    id: str = "axiom-rulespec-nz"
    description: str = (
        "New Zealand RuleSpec executed by Axiom over Microcosm family tables."
    )


nz_model = AxiomNewZealand()


class AxiomNewZealandPilot(TaxBenefitModelVersion):
    """Source-only 2026–27 WFF/IWTC entitlement comparison pilot."""

    country_code: ClassVar[str] = "nz"
    rulespec_root: str
    runtime_provenance: dict[str, Any]
    transport_contract: dict[str, Any] = Field(exclude=True)

    def __init__(self, **kwargs: Any) -> None:
        root = Path(kwargs["rulespec_root"]).expanduser().resolve()
        contract = _load_transport_contract(root)
        provenance = _build_runtime_provenance(root)
        version = sha256(
            json.dumps(provenance, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        identity = {
            "runtime_provenance": provenance,
            "version": version,
            "id": f"{nz_model.id}@{version}",
        }
        for field, current in identity.items():
            if field in kwargs and kwargs[field] != current:
                raise ValueError(
                    f"The saved NZ model {field} has changed relative to this runtime; "
                    "construct a new model explicitly instead of rebinding saved configuration."
                )
        kwargs.update(
            rulespec_root=str(root),
            transport_contract=contract,
            runtime_provenance=provenance,
            model=nz_model,
            version=version,
            id=f"{nz_model.id}@{version}",
        )
        super().__init__(**kwargs)

    def run(self, simulation: "Simulation") -> "Simulation":
        for name in ("policy", "dynamic", "scoping_strategy", "extra_variables"):
            if getattr(simulation, name):
                raise ValueError(
                    f"The NZ pilot does not support Simulation.{name}; it executes the pinned official-reform module only."
                )
        root = Path(self.rulespec_root)
        if _build_runtime_provenance(root) != self.runtime_provenance:
            raise RuntimeError(
                "The NZ RuleSpec/Axiom runtime changed; construct a new model version before running."
            )
        dataset = simulation.dataset
        if not isinstance(dataset, PopulaceNewZealandDataset):
            raise TypeError("AxiomNewZealandPilot requires PopulaceNewZealandDataset.")
        if dataset.is_output_dataset:
            raise ValueError("An NZ output dataset cannot be reused as a rules input.")
        if dataset.year != 2026:
            raise ValueError(
                "The NZ pilot only supports build label 2026 and tax year 2026–27."
            )
        frame = dataset.to_frame()
        input_frame_sha256 = _frame_sha256(frame)
        contract = self.transport_contract
        forbidden = set(
            contract["output_contract"]["formula_owned_excluded_from_dataset"]
        )
        stored = {
            name for entity in frame.entities for name in frame.table(entity).columns
        }
        if forbidden.intersection(stored):
            raise ValueError(
                f"NZ input contains formula-owned outputs: {sorted(forbidden.intersection(stored))}."
            )
        family = frame.table("family").copy()
        for item in contract["input_contract"]["required_target_inputs"]:
            _validate_input(family, item)
        padding_applied = []
        for item in contract["input_contract"]["adapter_padding_defaults"]:
            if item["name"] not in family:
                family.loc[:, item["name"]] = item["value"]
                padding_applied.append(item["name"])
            values = family[item["name"]]
            if values.isna().any() or not all(
                isinstance(value, (Real, Decimal))
                and not isinstance(value, (bool, np.bool_))
                and value == 0
                for value in values
            ):
                raise ValueError(
                    f"NZ adapter padding {item['name']!r} must contain numeric zeros only."
                )

        Frame, _, _, schema = nz_datasets._load_frame_runtime()
        tables = {entity: frame.table(entity).copy() for entity in frame.entities}
        tables["family"] = family
        frame = Frame(
            tables,
            schema,
            {"household": frame.weights_for("household")},
            frame.strata,
            metadata=frame.metadata,
        )
        AxiomEngine, AxiomPeriod = _load_axiom_runtime()
        source_period = contract["period"]
        period = {
            "start": source_period["start"],
            "end": source_period["end"],
            "kind": source_period["period_kind"],
        }
        engine = AxiomEngine(root / PILOT_MODULE, schema=schema, rulespec_roots=(root,))
        outputs = engine.materialize(frame, OUTPUTS, AxiomPeriod(**period))
        for name in OUTPUTS:
            values = np.asarray(outputs[name])
            if (
                values.shape != (frame.n("family"),)
                or not np.isfinite(values.astype(float)).all()
            ):
                raise ValueError(f"Axiom returned invalid NZ output {name!r}.")
            tables["family"][name] = values
        output_frame = Frame(
            tables,
            schema,
            {"household": frame.weights_for("household")},
            frame.strata,
            metadata=frame.metadata,
        )
        metadata = deepcopy(dataset.metadata)
        previous = metadata.get("policyengine_axiom_runs", [])
        if not isinstance(previous, list):
            raise ValueError("NZ policyengine_axiom_runs metadata must be a list.")
        metadata["policyengine_axiom_runs"] = [
            *previous,
            {
                "dataset_year": dataset.year,
                "input_artifact_sha256": dataset.source_sha256,
                "input_frame_sha256": input_frame_sha256,
                "weight_kind": dataset.weight_kind,
                "certified_population": False,
                "policy_period": period,
                "model_version": self.version,
                "output_variables": list(OUTPUTS),
                "padding_applied": padding_applied,
                "provenance": deepcopy(self.runtime_provenance),
                "official_score_bridge": deepcopy(contract["official_score_bridge"]),
            },
        ]
        simulation.output_dataset = PopulaceNewZealandDataset(
            id=simulation.id,
            name=dataset.name,
            description=dataset.description,
            filepath=None,
            year=dataset.year,
            policy_period=period,
            source_sha256=dataset.source_sha256,
            weight_kind=dataset.weight_kind,
            is_output_dataset=True,
            metadata=metadata,
            data=year_data_from_frame(output_frame),
        )
        return simulation

    def save(self, simulation: "Simulation") -> None:
        """Pilot outputs are in memory and recomputed, never saved over inputs."""

    def load(self, simulation: "Simulation") -> None:
        raise FileNotFoundError("NZ pilot simulations are recomputed, not persisted.")


def _load_axiom_runtime() -> tuple[Any, Any]:
    try:
        from microcosm.frame.adapters.axiom import AxiomEngine, AxiomPeriod
    except ImportError as error:
        raise ImportError(
            "The NZ pilot needs compatible microcosm-frame and Axiom source installs with AxiomPeriod support."
        ) from error
    return AxiomEngine, AxiomPeriod


def _validate_input(family: Any, item: dict[str, Any]) -> None:
    name, dtype = item["name"], item["dtype"]
    if name not in family:
        raise ValueError(
            f"Missing required NZ Family input {name!r}; no default is permitted."
        )
    values = family[name]
    if values.isna().any():
        raise ValueError(f"NZ Family input {name!r} contains nulls.")
    if dtype == "bool":
        valid = is_bool_dtype(values.dtype)
    elif dtype == "int16":
        valid = is_integer_dtype(values.dtype) and not is_bool_dtype(values.dtype)
    else:
        valid = (
            is_numeric_dtype(values.dtype) and not is_bool_dtype(values.dtype)
        ) or all(isinstance(value, Decimal) for value in values)
        if valid:
            try:
                decimals = [
                    value if isinstance(value, Decimal) else Decimal(str(value))
                    for value in values
                ]
                valid = all(
                    value.is_finite()
                    and abs(value) < Decimal("1e16")
                    and value == value.quantize(Decimal("0.01"))
                    for value in decimals
                )
            except (InvalidOperation, ValueError):
                valid = False
    if not valid:
        raise ValueError(f"NZ Family input {name!r} must satisfy dtype {dtype}.")
    if (
        dtype == "int16"
        and (
            (values < np.iinfo(np.int16).min) | (values > np.iinfo(np.int16).max)
        ).any()
    ):
        raise ValueError(f"NZ Family input {name!r} is outside int16 bounds.")


def _load_transport_contract(root: Path) -> dict[str, Any]:
    if not (root / PILOT_MODULE).is_file():
        raise FileNotFoundError(f"NZ Axiom module not found below {root}.")
    contract = json.loads((root / TRANSPORT_CONTRACT).read_text())
    if (
        contract.get("schema") != "axiom/nz-official-budget-reform-transport/1"
        or contract.get("jurisdiction") != "nz"
    ):
        raise ValueError("Unsupported NZ transport contract.")
    if (
        contract.get("runtime", {}).get("rulespec_module") != PILOT_MODULE
        or contract.get("runtime", {}).get("root_entity") != "Family"
    ):
        raise ValueError(
            "NZ transport contract names an unsupported module or root entity."
        )
    period = contract.get("period", {})
    if {
        "start": period.get("start"),
        "end": period.get("end"),
        "kind": period.get("period_kind"),
    } != POLICY_PERIOD:
        raise ValueError("The NZ pilot requires the explicit 2026–27 tax-year period.")
    inputs = contract["input_contract"]
    required = inputs["required_target_inputs"]
    padding = inputs["adapter_padding_defaults"]
    names = [item["name"] for item in required + padding]
    if len(names) != len(set(names)) or len(names) != inputs["engine_root_input_count"]:
        raise ValueError(
            "NZ transport input names must be unique and match the declared count."
        )
    if any(
        item.get("entity") != "family"
        or item.get("missing") != "fail_closed"
        or item.get("dtype") not in {"bool", "int16", "decimal128(18,2)"}
        for item in required
    ):
        raise ValueError(
            "NZ transport required inputs must be typed, fail-closed Family fields."
        )
    if any(
        item.get("value") != 0 or isinstance(item.get("value"), bool)
        for item in padding
    ):
        raise ValueError("NZ transport padding must be explicit numeric zero values.")
    outputs = contract["output_contract"]["requested"]
    if [item["name"] for item in outputs] != OUTPUTS or any(
        item.get("entity") != "family" or item.get("unit") != "NZD" for item in outputs
    ):
        raise ValueError(
            "NZ transport outputs must be the two Family entitlement deltas in NZD."
        )
    return contract


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _frame_sha256(frame: Any) -> str:
    """Identify actual in-memory inputs, including edits since artifact load.

    This is a fingerprint, not a weight aggregation. The receipt records the
    pandas version defining its row-hash algorithm alongside the runtime.
    """
    digest = sha256()
    for entity in nz_datasets.ENTITIES:
        table = frame.table(entity)
        header = [entity, list(table.columns), [str(dtype) for dtype in table.dtypes]]
        digest.update(json.dumps(header, separators=(",", ":")).encode())
        digest.update(
            pd.util.hash_pandas_object(table, index=True)
            .to_numpy(dtype="<u8")
            .tobytes()
        )
    digest.update(frame.weights_for("household").values.astype("<f8").tobytes())
    return digest.hexdigest()


def _module_path(name: str) -> Path:
    spec = find_spec(name)
    if spec is None or spec.origin is None or not Path(spec.origin).is_file():
        raise ImportError(f"Cannot locate the source-only NZ runtime module {name!r}.")
    return Path(spec.origin)


def _package_sha256(name: str) -> str:
    root = _module_path(name).parent
    digest = sha256()
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix().encode()
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _optional_version(distribution: str) -> str | None:
    try:
        return importlib_metadata.version(distribution)
    except importlib_metadata.PackageNotFoundError:
        # Source-built native extensions can have no distribution metadata.
        # Their file hash remains mandatory; do not invent an engine version.
        return None


def _build_runtime_provenance(root: Path) -> dict[str, Any]:
    """Identify all executed source trees without scanning unrelated files."""
    try:
        if Path(_git(root, "rev-parse", "--show-toplevel")).resolve() != root:
            raise ValueError("rulespec_root must be the rulespec-nz repository root.")
        dirty = _git(
            root,
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            "nz",
            TRANSPORT_CONTRACT,
            ".axiom/toolchain.toml",
        )
        if dirty:
            raise RuntimeError(
                "Commit the NZ RuleSpec source/transport changes before constructing a content-identified pilot."
            )
        return {
            "rulespec": {
                "repository": "TheAxiomFoundation/rulespec-nz",
                "commit": _git(root, "rev-parse", "HEAD"),
                "nz_tree": _git(root, "rev-parse", "HEAD:nz"),
                "module": PILOT_MODULE,
                "module_sha256": _file_sha256(root / PILOT_MODULE),
                "transport_contract_sha256": _file_sha256(root / TRANSPORT_CONTRACT),
            },
            "runtime": {
                "policyengine_nz_sha256": _package_sha256(
                    "policyengine.tax_benefit_models.nz"
                ),
                "pandas_version": importlib_metadata.version("pandas"),
                "numpy_version": importlib_metadata.version("numpy"),
                "microcosm_frame_version": importlib_metadata.version(
                    "microcosm-frame"
                ),
                "microcosm_frame_sha256": _package_sha256("microcosm.frame"),
                "axiom_python_version": importlib_metadata.version(
                    "axiom-rules-engine"
                ),
                "axiom_python_sha256": _package_sha256("axiom_rules_engine"),
                "axiom_dense_version": _optional_version("axiom-rules-engine-dense"),
                "axiom_dense_sha256": _file_sha256(
                    _module_path("axiom_rules_engine_dense")
                ),
            },
        }
    except (
        subprocess.CalledProcessError,
        importlib_metadata.PackageNotFoundError,
        ModuleNotFoundError,
    ) as error:
        raise ImportError(
            "The NZ pilot requires committed rulespec-nz plus compatible microcosm-frame, Axiom Python, and dense-extension source installs."
        ) from error
