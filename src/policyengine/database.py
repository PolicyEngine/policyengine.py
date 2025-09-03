from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, Iterable, Optional, Tuple, Type, TypeVar, Union

from sqlmodel import SQLModel, Session, create_engine, select

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

    def __init__(self, url: str = "sqlite:///policyengine.db", echo: bool = False):
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
            s.add(row)
            s.commit()
            s.refresh(row)
            return row

    def add_all(self, objs: Iterable[Any], *, cascade: bool = True) -> list[SQLModel]:
        results: list[SQLModel] = []
        with self.session() as s:
            for obj in objs:
                self._resolve_table_class(obj)  # validate known type
                row = self._to_table(obj, s, cascade=cascade)
                s.add(row)
                results.append(row)
            s.commit()
            for row in results:
                s.refresh(row)
        return results

    def get(self, model_cls: Type[BM], id: int, *, cascade: bool = False) -> BM | None:
        """Load a BaseModel instance by primary key of its table."""
        table_cls = self._resolve_table_class(model_cls)
        with self.session() as s:
            row = s.get(table_cls, id)
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
            return ParameterValueTable(
                policy_id=policy_id,
                dynamics_id=dynamics_id,
                parameter_id=parameter_id,  # type: ignore[arg-type]
                model_version=obj.model_version,
                start_date=obj.start_date,
                end_date=obj.end_date,
                value=obj.value,
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
            return VariableTable(
                name=obj.name,
                label=obj.label,
                description=obj.description,
                unit=obj.unit,
                value_type=obj.value_type,
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
                value=row.value,
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
            return Variable(
                name=row.name,
                label=row.label,
                description=row.description,
                unit=row.unit,
                value_type=row.value_type,
                entity=row.entity,
                definition_period=row.definition_period,
                country=row.country,
            )

        # If already a BaseModel instance or unknown
        if isinstance(row, SQLModel):
            raise ValueError(f"No mapper for table row type: {type(row)}")
        return row
