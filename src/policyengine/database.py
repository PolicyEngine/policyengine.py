from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, Iterable, Optional, Tuple, Type, TypeVar, Union
from uuid import UUID

from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy import delete

# Base models
from policyengine.models.user import (
    User,
    UserPolicy,
    UserSimulation,
    UserReport,
    UserReportElement,
)
from policyengine.models.policy import Policy
from policyengine.models.dynamics import Dynamics
from policyengine.models.parameter import Parameter, ParameterValue
from policyengine.models.dataset import Dataset
from policyengine.models.single_year_dataset import SingleYearDataset
from policyengine.models.simulation import Simulation
from policyengine.models.reports import Report, ReportElement
from policyengine.models.variable import Variable
from policyengine.models.enums import DatasetType, OperationStatus

# Table models
from policyengine.tables import (
    UserTable,
    UserPolicyTable,
    UserSimulationTable,
    UserReportTable,
    UserReportElementTable,
    PolicyTable,
    DynamicsTable,
    ParameterTable,
    ParameterValueTable,
    DatasetTable,
    SimulationTable,
    ReportTable,
    ReportElementTable,
    VariableTable,
)


BM = TypeVar("BM")


class Database:
    """Lightweight Database layer bridging BaseModels and SQLModel tables.

    - Creates and manages an engine + sessions
    - Converts BaseModels to their SQLModel equivalents and persists them
    - Rehydrates BaseModels from stored SQLModel rows

    This is intentionally pragmatic and minimal; it favors a simple mapping
    over enforcing every possible constraint. Extend as needs grow.
    """

    def __init__(
        self,
        url: str = "sqlite:///policyengine.db",
        echo: bool = False,
        seed_countries: Iterable[str] | None = None,
    ):
        self.engine = create_engine(url, echo=echo, future=True)
        SQLModel.metadata.create_all(self.engine)

        # Mapping between BaseModel classes and SQLModel table classes
        self._bm_to_table: Dict[type, type[SQLModel]] = {
            User: UserTable,
            UserPolicy: UserPolicyTable,
            UserSimulation: UserSimulationTable,
            UserReport: UserReportTable,
            UserReportElement: UserReportElementTable,
            Policy: PolicyTable,
            Dynamics: DynamicsTable,
            Parameter: ParameterTable,
            ParameterValue: ParameterValueTable,
            Dataset: DatasetTable,
            Simulation: SimulationTable,
            Report: ReportTable,
            ReportElement: ReportElementTable,
            Variable: VariableTable,
        }

        self._table_to_bm: Dict[type[SQLModel], type] = {
            v: k for k, v in self._bm_to_table.items()
        }

        # Optionally seed metadata on init
        if seed_countries:
            self.seed(seed_countries)

    def reset(self) -> None:
        """Drop and recreate all tables, clearing all data.

        Use with care. This removes all rows from every table by
        dropping the schema and recreating it.
        """
        # Ensure models are loaded so metadata is complete
        SQLModel.metadata.drop_all(self.engine)
        SQLModel.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        with Session(self.engine) as s:
            yield s

    # ------------------- Public API -------------------
    def add(self, obj: Any, *, cascade: bool = True) -> SQLModel:
        """Persist a BaseModel by mapping it to its table model.

        Returns the created/updated table instance (with primary key).
        """
        table_cls = self._resolve_table_class(obj)
        with self.session() as s:
            row = self._to_table(obj, s, cascade=cascade)
            row = self._upsert_row(obj, row, s)
            s.add(row)
            s.commit()
            s.refresh(row)
            return row

    def add_all(self, objs: Iterable[Any], *, cascade: bool = True, refresh: bool = True) -> list[SQLModel]:
        results: list[SQLModel] = []
        with self.session() as s:
            # Pre-pass: for ParameterValue replacement semantics, delete existing
            # rows for the same (parameter, model_version, policy, dynamics, country)
            # to allow full replacement of a time-series for a given version.
            from policyengine.models.parameter import ParameterValue as PVModel
            from policyengine.tables import ParameterTable, ParameterValueTable, PolicyTable, DynamicsTable

            cleanup_keys: set[tuple[int, str, Optional[int], Optional[int], Optional[str]]] = set()
            # Caches to avoid repeated upserts/flushes
            param_cache: dict[tuple[str | None, str | None], int] = {}
            policy_cache: dict[tuple[str | None, str | None], int] = {}
            dynamics_cache: dict[tuple[str | None, str | None], int] = {}

            only_pv_models = True
            for obj in objs:
                if isinstance(obj, PVModel):
                    # Ensure parameter/policy/dynamics rows exist to resolve IDs
                    par_key = (obj.parameter.name, obj.parameter.country)
                    if par_key in param_cache:
                        par_id = param_cache[par_key]
                    else:
                        par_row = self._to_table(obj.parameter, s, cascade=cascade)
                        par_row = self._upsert_row(obj.parameter, par_row, s)  # type: ignore[arg-type]
                        s.add(par_row)
                        s.flush()
                        par_id = par_row.id  # type: ignore[assignment]
                        param_cache[par_key] = par_id
                    policy_id = None
                    dynamics_id = None
                    if obj.policy is not None:
                        pol_key = (obj.policy.name, obj.policy.country)
                        if pol_key in policy_cache:
                            policy_id = policy_cache[pol_key]
                        else:
                            pol_row = self._to_table(obj.policy, s, cascade=cascade)
                            pol_row = self._upsert_row(obj.policy, pol_row, s)  # type: ignore[arg-type]
                            s.add(pol_row)
                            s.flush()
                            policy_id = pol_row.id  # type: ignore[assignment]
                            policy_cache[pol_key] = policy_id
                    if obj.dynamics is not None:
                        dyn_key = (obj.dynamics.name, obj.dynamics.country)
                        if dyn_key in dynamics_cache:
                            dynamics_id = dynamics_cache[dyn_key]
                        else:
                            dyn_row = self._to_table(obj.dynamics, s, cascade=cascade)
                            dyn_row = self._upsert_row(obj.dynamics, dyn_row, s)  # type: ignore[arg-type]
                            s.add(dyn_row)
                            s.flush()
                            dynamics_id = dyn_row.id  # type: ignore[assignment]
                            dynamics_cache[dyn_key] = dynamics_id
                    key = (par_id, obj.model_version, policy_id, dynamics_id, obj.country)  # type: ignore[arg-type]
                    cleanup_keys.add(key)
                else:
                    only_pv_models = False

            # Perform cleanup deletes per key
            for (parameter_id, model_version, policy_id, dynamics_id, country) in cleanup_keys:
                conds = [
                    ParameterValueTable.parameter_id == parameter_id,
                    ParameterValueTable.model_version == model_version,
                    ParameterValueTable.country == country,
                ]
                conds.append(
                    ParameterValueTable.policy_id.is_(None)
                    if policy_id is None
                    else ParameterValueTable.policy_id == policy_id
                )
                conds.append(
                    ParameterValueTable.dynamics_id.is_(None)
                    if dynamics_id is None
                    else ParameterValueTable.dynamics_id == dynamics_id
                )
                stmt = delete(ParameterValueTable).where(*conds)
                s.exec(stmt)

            # Fast path: bulk insert parameter values in one executemany
            from policyengine.tables import ParameterValueTable as PVTable
            from sqlalchemy import insert as sa_insert

            if only_pv_models and len(objs) > 0:
                pv_dicts = []
                for obj in objs:  # type: ignore[union-attr]
                    row = self._to_table(obj, s, cascade=cascade)
                    # Ensure id assigned for UUID primary key
                    if getattr(row, "id", None) is None:
                        # SQLModel default_factory runs on instance creation, but be safe
                        import uuid

                        row.id = uuid.uuid4()
                    pv_dicts.append(
                        {
                            "id": row.id,
                            "policy_id": row.policy_id,
                            "dynamics_id": row.dynamics_id,
                            "parameter_id": row.parameter_id,
                            "model_version": row.model_version,
                            "start_date": row.start_date,
                            "end_date": row.end_date,
                            "value": row.value,
                            "country": row.country,
                        }
                    )
                if pv_dicts:
                    s.exec(sa_insert(PVTable), pv_dicts)
                s.commit()
                # No refresh needed for seed path
                return [] if not refresh else []

            # General path: process all objects (mixed types)
            for obj in objs:
                self._resolve_table_class(obj)  # validate known type
                row = self._to_table(obj, s, cascade=cascade)
                if isinstance(row, PVTable):
                    s.add(row)
                else:
                    row = self._upsert_row(obj, row, s)
                    s.add(row)
                results.append(row)
            s.commit()
            if refresh:
                for row in results:
                    s.refresh(row)
        return results

    # ------------------- Seeding -------------------
    def seed(self, countries: Iterable[str]) -> None:
        """Seed database with metadata for selected countries.

        Accepts any subset of {"uk", "us"}. Uses country-specific metadata
        helpers to load Variables, Parameters (via ParameterValues), and
        default Policy/Dynamics and upserts them into the DB.
        """
        for country in countries:
            country = country.lower()
            if country == "uk":
                from policyengine.countries.uk.metadata import get_uk_metadata

                md = get_uk_metadata()
            elif country == "us":
                from policyengine.countries.us.metadata import get_us_metadata

                md = get_us_metadata()
            else:
                raise ValueError(f"Unknown country code for seeding: {country}")

            # Upsert policy and dynamics anchors
            anchor_objs = []
            if md.get("current_law") is not None:
                md["current_law"].country = country
                anchor_objs.append(md["current_law"])
            if md.get("static") is not None:
                md["static"].country = country
                anchor_objs.append(md["static"])
            if anchor_objs:
                self.add_all(anchor_objs, refresh=False)

            # Variables
            variables = []
            for v in md.get("variables", []) or []:
                v.country = country
                variables.append(v)
            if variables:
                self.add_all(variables, refresh=False)

            # Parameter values (cascades will create parameters)
            pvalues = []
            for pv in md.get("parameter_values", []) or []:
                pv.country = country
                if pv.parameter is not None:
                    pv.parameter.country = country
                pvalues.append(pv)
            if pvalues:
                self.add_all(pvalues, refresh=False)

            # Country datasets provided by metadata
            datasets = md.get("datasets") or []
            if datasets:
                # ensure dataset names are set and deduplicate by name
                self.add_all(datasets, refresh=False)

    def get(self, model_cls: Type[BM], id: Any | None = None, *, cascade: bool = False, **filters: Any) -> BM | None:
        """Load a BaseModel by primary key or by attribute filters.

        Examples:
        - get(Dataset, id)
        - get(Policy, name="Current law", country="uk")
        - get(Parameter, name="gov.ubi.amount")
        """
        table_cls = self._resolve_table_class(model_cls)
        with self.session() as s:
            if id is not None:
                row = s.get(table_cls, id)
                if row is None:
                    return None
                return self._to_model(row, s, cascade=cascade)
            stmt = select(table_cls)
            conds = []
            for key, value in filters.items():
                if not hasattr(table_cls, key):
                    raise ValueError(f"Unknown field for {table_cls.__name__}: {key}")
                col = getattr(table_cls, key)
                if value is None:
                    conds.append(col.is_(None))
                else:
                    conds.append(col == value)
            if conds:
                stmt = stmt.where(*conds)
            row = s.exec(stmt).first()
            if row is None:
                return None
            return self._to_model(row, s, cascade=cascade)

    def list(self, model_cls: Type[BM], *, limit: int | None = None) -> list[BM]:
        """List BaseModel instances for a given class."""
        table_cls = self._resolve_table_class(model_cls)
        with self.session() as s:
            stmt = select(table_cls)
            if limit is not None:
                stmt = stmt.limit(limit)
            rows = s.exec(stmt).all()
            return [self._to_model(r, s, cascade=False) for r in rows]

    # ------------------- Mapping helpers -------------------
    def _resolve_table_class(self, obj_or_cls: Union[Any, type]) -> type[SQLModel]:
        if isinstance(obj_or_cls, type):
            if obj_or_cls in self._bm_to_table:
                return self._bm_to_table[obj_or_cls]
            if obj_or_cls in self._table_to_bm:
                return obj_or_cls  # already a table class
            raise ValueError(f"No table mapping for class: {obj_or_cls}")
        obj_type = type(obj_or_cls)
        if obj_type in self._bm_to_table:
            return self._bm_to_table[obj_type]
        if obj_type in self._table_to_bm:
            return obj_type
        raise ValueError(f"No table mapping for instance of: {obj_type}")

    # Specific mappers. These keep relationships simple and optional.
    def _to_table(self, obj: Any, s: Session, *, cascade: bool) -> SQLModel:
        # Users and links
        if isinstance(obj, User):
            return UserTable(id=obj.id, name=obj.name, email=obj.email)

        if isinstance(obj, UserPolicy):
            # policy is required
            policy_row = self._to_table(obj.policy, s, cascade=cascade)
            if getattr(policy_row, "id", None) is None:
                s.add(policy_row)
                s.flush()
            return UserPolicyTable(
                user_id=obj.user.id,
                policy_id=policy_row.id,  # type: ignore[arg-type]
                label=obj.label,
                description=obj.description,
            )

        if isinstance(obj, UserSimulation):
            sim_row = self._to_table(obj.simulation, s, cascade=cascade)
            if getattr(sim_row, "id", None) is None:
                s.add(sim_row)
                s.flush()
            return UserSimulationTable(
                user_id=obj.user.id,
                simulation_id=sim_row.id,  # type: ignore[arg-type]
                label=obj.label,
                description=obj.description,
            )

        if isinstance(obj, UserReport):
            report_row = self._to_table(obj.report, s, cascade=cascade)
            if getattr(report_row, "id", None) is None:
                s.add(report_row)
                s.flush()
            return UserReportTable(
                user_id=obj.user.id,
                report_id=report_row.id,  # type: ignore[arg-type]
                label=obj.label,
                description=obj.description,
            )

        if isinstance(obj, UserReportElement):
            el_row = self._to_table(obj.report_element, s, cascade=cascade)
            if getattr(el_row, "id", None) is None:
                s.add(el_row)
                s.flush()
            return UserReportElementTable(
                user_id=obj.user.id,
                report_element_id=el_row.id,  # type: ignore[arg-type]
                label=obj.label,
                description=obj.description,
            )

        # Policy, Dynamics, Parameters
        if isinstance(obj, Policy):
            return PolicyTable(name=obj.name, description=obj.description, country=obj.country)

        if isinstance(obj, Dynamics):
            parent_id = None
            if obj.parent_dynamics is not None and cascade:
                parent_row = self._to_table(obj.parent_dynamics, s, cascade=cascade)
                s.add(parent_row)
                s.flush()
                parent_id = parent_row.id
            return DynamicsTable(
                name=obj.name,
                parent_id=parent_id,
                description=obj.description,
                created_at=obj.created_at,
                updated_at=obj.updated_at,
                country=obj.country,
            )

        if isinstance(obj, Parameter):
            parent_id = None
            if obj.parent is not None and cascade:
                parent_row = self._to_table(obj.parent, s, cascade=cascade)
                s.add(parent_row)
                s.flush()
                parent_id = parent_row.id
            data_type = obj.data_type.__name__ if isinstance(obj.data_type, type) else str(obj.data_type)
            return ParameterTable(
                name=obj.name,
                parent_id=parent_id,
                label=obj.label,
                description=obj.description,
                unit=obj.unit,
                data_type=data_type,
                country=obj.country,
            )

        if isinstance(obj, ParameterValue):
            # Ensure dependent objects exist if cascading
            policy_id = None
            dynamics_id = None
            parameter_id = None
            if obj.policy is not None and cascade:
                pol_row = self._to_table(obj.policy, s, cascade=cascade)
                s.add(pol_row)
                s.flush()
                policy_id = pol_row.id
            if obj.dynamics is not None and cascade:
                dyn_row = self._to_table(obj.dynamics, s, cascade=cascade)
                s.add(dyn_row)
                s.flush()
                dynamics_id = dyn_row.id
            # parameter is required
            par_row = self._to_table(obj.parameter, s, cascade=cascade)
            s.add(par_row)
            s.flush()
            parameter_id = par_row.id
            # JSON-safe value handling (inf/-inf, NaN)
            return ParameterValueTable(
                policy_id=policy_id,
                dynamics_id=dynamics_id,
                parameter_id=parameter_id,  # type: ignore[arg-type]
                model_version=obj.model_version,
                start_date=obj.start_date,
                end_date=obj.end_date,
                value=self._json_safe_value(obj.value),
                country=obj.country,
            )

        # Dataset
        if isinstance(obj, Dataset):
            source_id = None
            if obj.source_dataset is not None and cascade:
                src_row = self._to_table(obj.source_dataset, s, cascade=cascade)
                s.add(src_row)
                s.flush()
                source_id = src_row.id
            data_bytes = None
            if isinstance(obj.data, SingleYearDataset):
                data_bytes = obj.data.serialise()
            elif isinstance(obj.data, (bytes, bytearray)):
                data_bytes = bytes(obj.data)
            return DatasetTable(
                name=obj.name,
                source_dataset_id=source_id,
                version=obj.version,
                data_bytes=data_bytes,
                dataset_type=obj.dataset_type,
            )

        # Simulation
        if isinstance(obj, Simulation):
            dataset_id = policy_id = dynamics_id = result_dataset_id = None
            if obj.dataset is not None and cascade:
                ds_row = self._to_table(obj.dataset, s, cascade=cascade)
                s.add(ds_row)
                s.flush()
                dataset_id = ds_row.id
            if obj.policy is not None and cascade:
                po_row = self._to_table(obj.policy, s, cascade=cascade)
                s.add(po_row)
                s.flush()
                policy_id = po_row.id
            if obj.dynamics is not None and cascade:
                dy_row = self._to_table(obj.dynamics, s, cascade=cascade)
                s.add(dy_row)
                s.flush()
                dynamics_id = dy_row.id
            if isinstance(obj.result, Dataset) and cascade:
                rs_row = self._to_table(obj.result, s, cascade=cascade)
                s.add(rs_row)
                s.flush()
                result_dataset_id = rs_row.id
            return SimulationTable(
                dataset_id=dataset_id,
                policy_id=policy_id,
                dynamics_id=dynamics_id,
                result_dataset_id=result_dataset_id,
                model_version=obj.model_version,
                country=obj.country,
                status=obj.status,
                created_at=obj.created_at,
                completed_at=obj.completed_at,
            )

        # Reports
        if isinstance(obj, Report):
            return ReportTable(name=obj.name, description=obj.description, country=obj.country)

        if isinstance(obj, ReportElement):
            report_id = None
            if obj.report is not None and cascade:
                rep_row = self._to_table(obj.report, s, cascade=cascade)
                s.add(rep_row)
                s.flush()
                report_id = rep_row.id
            return ReportElementTable(
                name=obj.name,
                description=obj.description,
                report_id=report_id,
                status=obj.status,
                country=obj.country,
            )

        # Variable
        if isinstance(obj, Variable):
            data_type = obj.data_type.__name__ if isinstance(obj.data_type, type) else str(obj.data_type)
            return VariableTable(
                name=obj.name,
                label=obj.label,
                description=obj.description,
                unit=obj.unit,
                data_type=data_type,
                entity=obj.entity,
                definition_period=obj.definition_period,
                country=obj.country,
            )

        # Already a table object
        if isinstance(obj, SQLModel):
            return obj

        raise ValueError(f"Unsupported object type for to_table: {type(obj)}")

    def _to_model(self, row: SQLModel, s: Session, *, cascade: bool) -> Any:
        # Users and links
        if isinstance(row, UserTable):
            return User(id=row.id or 0, name=row.name, email=row.email)

        if isinstance(row, UserPolicyTable):
            user = self._to_model(s.get(UserTable, row.user_id), s, cascade=False)
            policy = (
                self._to_model(s.get(PolicyTable, row.policy_id), s, cascade=False)
                if row.policy_id is not None
                else None
            )
            return UserPolicy(user=user, policy=policy, label=row.label, description=row.description)

        if isinstance(row, UserSimulationTable):
            user = self._to_model(s.get(UserTable, row.user_id), s, cascade=False)
            sim = (
                self._to_model(s.get(SimulationTable, row.simulation_id), s, cascade=False)
                if row.simulation_id is not None
                else None
            )
            return UserSimulation(user=user, simulation=sim, label=row.label, description=row.description)

        if isinstance(row, UserReportTable):
            user = self._to_model(s.get(UserTable, row.user_id), s, cascade=False)
            report = (
                self._to_model(s.get(ReportTable, row.report_id), s, cascade=False)
                if row.report_id is not None
                else None
            )
            return UserReport(user=user, report=report, label=row.label, description=row.description)

        if isinstance(row, UserReportElementTable):
            user = self._to_model(s.get(UserTable, row.user_id), s, cascade=False)
            el = (
                self._to_model(s.get(ReportElementTable, row.report_element_id), s, cascade=False)
                if row.report_element_id is not None
                else None
            )
            return UserReportElement(user=user, report_element=el, label=row.label, description=row.description)

        # Policy, Dynamics, Parameters
        if isinstance(row, PolicyTable):
            return Policy(name=row.name, description=row.description, country=row.country)

        if isinstance(row, DynamicsTable):
            parent = (
                self._to_model(s.get(DynamicsTable, row.parent_id), s, cascade=False)
                if (cascade and row.parent_id is not None)
                else None
            )
            return Dynamics(
                name=row.name,
                parent_dynamics=parent,
                description=row.description,
                created_at=row.created_at,
                updated_at=row.updated_at,
                country=row.country,
            )

        if isinstance(row, ParameterTable):
            parent = (
                self._to_model(s.get(ParameterTable, row.parent_id), s, cascade=False)
                if (cascade and row.parent_id is not None)
                else None
            )
            data_type_map = {"float": float, "int": int, "bool": bool, "string": str}
            data_type = data_type_map.get(row.data_type, str)
            return Parameter(
                name=row.name,
                parent=parent,
                label=row.label,
                description=row.description,
                unit=row.unit,
                data_type=data_type,
                country=row.country,
            )

        if isinstance(row, ParameterValueTable):
            policy = (
                self._to_model(s.get(PolicyTable, row.policy_id), s, cascade=False)
                if (cascade and row.policy_id is not None)
                else None
            )
            dynamics = (
                self._to_model(s.get(DynamicsTable, row.dynamics_id), s, cascade=False)
                if (cascade and row.dynamics_id is not None)
                else None
            )
            parameter = (
                self._to_model(s.get(ParameterTable, row.parameter_id), s, cascade=False)
                if row.parameter_id is not None
                else None
            )
            return ParameterValue(
                policy=policy,
                dynamics=dynamics,
                parameter=parameter,  # type: ignore[arg-type]
                model_version=row.model_version,
                start_date=row.start_date,
                end_date=row.end_date,
                value=self._json_restore_value(row.value),
                country=row.country,
            )

        # Dataset
        if isinstance(row, DatasetTable):
            source = (
                self._to_model(s.get(DatasetTable, row.source_dataset_id), s, cascade=False)
                if (cascade and row.source_dataset_id is not None)
                else None
            )
            data = (
                SingleYearDataset(serialised_bytes=row.data_bytes)
                if row.data_bytes is not None
                else None
            )
            return Dataset(
                name=row.name,
                source_dataset=source,
                version=row.version,
                data=data,
                dataset_type=row.dataset_type,
            )

        # Simulation
        if isinstance(row, SimulationTable):
            dataset = (
                self._to_model(s.get(DatasetTable, row.dataset_id), s, cascade=False)
                if row.dataset_id is not None
                else None
            )
            policy = (
                self._to_model(s.get(PolicyTable, row.policy_id), s, cascade=False)
                if row.policy_id is not None
                else None
            )
            dynamics = (
                self._to_model(s.get(DynamicsTable, row.dynamics_id), s, cascade=False)
                if row.dynamics_id is not None
                else None
            )
            result = (
                self._to_model(s.get(DatasetTable, row.result_dataset_id), s, cascade=False)
                if row.result_dataset_id is not None
                else None
            )
            return Simulation(
                dataset=dataset,  # type: ignore[arg-type]
                policy=policy,  # type: ignore[arg-type]
                dynamics=dynamics,  # type: ignore[arg-type]
                result=result,  # type: ignore[arg-type]
                model_version=row.model_version,
                country=row.country,
                status=row.status,
                created_at=row.created_at,
                completed_at=row.completed_at,
            )

        # Reports
        if isinstance(row, ReportTable):
            # Elements are not auto-hydrated to avoid heavy joins
            return Report(name=row.name, description=row.description, elements=[], country=row.country)

        if isinstance(row, ReportElementTable):
            report = (
                self._to_model(s.get(ReportTable, row.report_id), s, cascade=False)
                if (cascade and row.report_id is not None)
                else None
            )
            return ReportElement(
                name=row.name,
                description=row.description,
                report=report,  # type: ignore[arg-type]
                status=row.status,
                country=row.country,
            )

        # Variable
        if isinstance(row, VariableTable):
            data_type_map = {"float": float, "int": int, "bool": bool, "string": str}
            data_type = data_type_map.get(row.data_type, str)
            return Variable(
                name=row.name,
                label=row.label,
                description=row.description,
                unit=row.unit,
                data_type=data_type,
                entity=row.entity,
                definition_period=row.definition_period,
                country=row.country,
            )

        # If already a BaseModel instance or unknown
        if isinstance(row, SQLModel):
            raise ValueError(f"No mapper for table row type: {type(row)}")
        return row

    # ------------------- JSON helpers -------------------
    def _json_safe_value(self, v: Any) -> Any:
        """Make a JSON-compatible value while preserving inf/-inf/NaN semantics.

        - float('inf') -> "Infinity"
        - float('-inf') -> "-Infinity"
        - float('nan') -> "NaN"
        Recurses into lists/tuples/dicts.
        """
        import math

        if isinstance(v, float):
            if math.isinf(v):
                return "Infinity" if v > 0 else "-Infinity"
            if math.isnan(v):
                return "NaN"
            return v
        if isinstance(v, (list, tuple)):
            return [self._json_safe_value(x) for x in v]
        if isinstance(v, dict):
            return {k: self._json_safe_value(val) for k, val in v.items()}
        return v

    def _json_restore_value(self, v: Any) -> Any:
        """Restore special float markers from JSON back to Python floats.

        - "Infinity" -> float('inf')
        - "-Infinity" -> float('-inf')
        - "NaN" -> float('nan')
        Recurses into lists/tuples/dicts.
        """
        if isinstance(v, str):
            if v == "Infinity":
                return float("inf")
            if v == "-Infinity":
                return float("-inf")
            if v == "NaN":
                return float("nan")
            return v
        if isinstance(v, list):
            return [self._json_restore_value(x) for x in v]
        if isinstance(v, dict):
            return {k: self._json_restore_value(val) for k, val in v.items()}
        return v

    # ------------------- Upsert helpers -------------------
    def _upsert_row(self, obj: Any, new_row: SQLModel, s: Session) -> SQLModel:
        """Apply deduplication/upsert rules per model type.

        - Parameter: same name+country replaces
        - Variable: same name+country replaces
        - Policy: same name+country replaces
        - Dynamics: same name+country replaces
        - ParameterValue: same (parameter, model_version, start/end, policy, dynamics, country) replaces
        - Report/ReportElement: same name+country replaces (best-effort)
        """
        from policyengine.tables import (
            PolicyTable,
            DynamicsTable,
            ParameterTable,
            ParameterValueTable,
            VariableTable,
            ReportTable,
            ReportElementTable,
            DatasetTable,
        )

        # Policy
        if isinstance(new_row, PolicyTable):
            stmt = select(PolicyTable).where(
                PolicyTable.name == new_row.name, PolicyTable.country == new_row.country
            )
            existing = s.exec(stmt).first()
            if existing:
                existing.description = new_row.description
                existing.country = new_row.country
                return existing
            return new_row

        # Dynamics
        if isinstance(new_row, DynamicsTable):
            stmt = select(DynamicsTable).where(
                DynamicsTable.name == new_row.name, DynamicsTable.country == new_row.country
            )
            existing = s.exec(stmt).first()
            if existing:
                existing.parent_id = new_row.parent_id
                existing.description = new_row.description
                existing.created_at = new_row.created_at
                existing.updated_at = new_row.updated_at
                existing.country = new_row.country
                return existing
            return new_row

        # Parameter
        if isinstance(new_row, ParameterTable):
            stmt = select(ParameterTable).where(
                ParameterTable.name == new_row.name, ParameterTable.country == new_row.country
            )
            existing = s.exec(stmt).first()
            if existing:
                existing.parent_id = new_row.parent_id
                existing.label = new_row.label
                existing.description = new_row.description
                existing.unit = new_row.unit
                existing.data_type = new_row.data_type
                existing.country = new_row.country
                return existing
            return new_row

        # ParameterValue
        if isinstance(new_row, ParameterValueTable):
            stmt = select(ParameterValueTable).where(
                ParameterValueTable.parameter_id == new_row.parameter_id,
                ParameterValueTable.model_version == new_row.model_version,
                ParameterValueTable.start_date == new_row.start_date,
                ParameterValueTable.end_date.is_(new_row.end_date) if new_row.end_date is None else ParameterValueTable.end_date == new_row.end_date,
                ParameterValueTable.policy_id.is_(new_row.policy_id) if new_row.policy_id is None else ParameterValueTable.policy_id == new_row.policy_id,
                ParameterValueTable.dynamics_id.is_(new_row.dynamics_id) if new_row.dynamics_id is None else ParameterValueTable.dynamics_id == new_row.dynamics_id,
                ParameterValueTable.country == new_row.country,
            )
            existing = s.exec(stmt).first()
            if existing:
                existing.value = new_row.value
                return existing
            return new_row

        # Variable
        if isinstance(new_row, VariableTable):
            stmt = select(VariableTable).where(
                VariableTable.name == new_row.name, VariableTable.country == new_row.country
            )
            existing = s.exec(stmt).first()
            if existing:
                existing.label = new_row.label
                existing.description = new_row.description
                existing.unit = new_row.unit
                existing.data_type = new_row.data_type
                existing.entity = new_row.entity
                existing.definition_period = new_row.definition_period
                existing.country = new_row.country
                return existing
            return new_row

        # Reports
        if isinstance(new_row, ReportTable):
            stmt = select(ReportTable).where(
                ReportTable.name == new_row.name, ReportTable.country == new_row.country
            )
            existing = s.exec(stmt).first()
            if existing:
                existing.description = new_row.description
                existing.country = new_row.country
                return existing
            return new_row

        if isinstance(new_row, ReportElementTable):
            stmt = select(ReportElementTable).where(
                ReportElementTable.name == new_row.name, ReportElementTable.country == new_row.country
            )
            existing = s.exec(stmt).first()
            if existing:
                existing.description = new_row.description
                existing.report_id = new_row.report_id
                existing.status = new_row.status
                existing.country = new_row.country
                return existing
            return new_row

        # Dataset
        if isinstance(new_row, DatasetTable):
            # Deduplicate by dataset name; update payload
            stmt = select(DatasetTable).where(DatasetTable.name == new_row.name)
            existing = s.exec(stmt).first()
            if existing:
                existing.source_dataset_id = new_row.source_dataset_id
                existing.version = new_row.version
                existing.data_bytes = new_row.data_bytes
                existing.dataset_type = new_row.dataset_type
                return existing
            return new_row

        # Default: no special upsert, insert as-is
        return new_row
