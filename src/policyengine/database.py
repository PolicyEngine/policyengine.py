from __future__ import annotations

from contextlib import contextmanager
import os
from datetime import datetime
from typing import (
    Any,
    Dict,
    Generator,
    Iterable,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID
import pickle

from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy import delete

# Constants for database connection
POLICYENGINE_DB = "policyengine"  # Special value to connect to PolicyEngine live DB using environment variables

# Base models
from policyengine.models.user import (
    User,
    UserPolicy,
    UserSimulation,
    UserReport,
    UserReportElement,
)
from policyengine.models.policy import Policy
from policyengine.models.dynamic import Dynamic
from policyengine.models.parameter import Parameter, ParameterValue
from policyengine.models.baseline_parameter import BaselineParameterValue
from policyengine.models.dataset import Dataset
from policyengine.models.single_year_dataset import SingleYearDataset
from policyengine.models.simulation import Simulation
from policyengine.models.reports import Report, ReportElement
from policyengine.models.variable import Variable
from policyengine.models.enums import DatasetType, OperationStatus
from policyengine.models.report_items.aggregate import (
    Aggregate,
    AggregateMetric,
)
from policyengine.models.report_items.count import Count
from policyengine.models.report_items.two_sim_change import (
    ChangeByBaselineGroup,
    VariableChangeGroupByQuantileGroup,
    VariableChangeGroupByVariableValue,
)

# Table models
from policyengine.tables import (
    UserTable,
    UserPolicyTable,
    UserSimulationTable,
    UserReportTable,
    UserReportElementTable,
    PolicyTable,
    DynamicTable,
    ParameterTable,
    ParameterValueTable,
    BaselineParameterValueTable,
    DatasetTable,
    SimulationTable,
    ReportTable,
    ReportElementTable,
    VariableTable,
    AggregateTable,
    CountTable,
    ChangeByBaselineGroupTable,
    VariableChangeGroupByQuantileGroupTable,
    VariableChangeGroupByVariableValueTable,
)


BM = TypeVar("BM")


class Database:
    """Lightweight Database layer bridging BaseModels and SQLModel tables.

    - Creates and manages an engine + sessions
    - Converts BaseModels to their SQLModel equivalents and persists them
    - Rehydrates BaseModels from stored SQLModel rows

    This is intentionally pragmatic and minimal; it favors a simple mapping
    over enforcing every possible constraint. Extend as needs grow.
    
    Usage:
        # In-memory database
        db = Database("sqlite:///:memory:")
        
        # Local file database
        db = Database("sqlite:///policyengine.db")
        
        # Connect to live PolicyEngine database (requires env vars)
        from policyengine import POLICYENGINE_DB
        db = Database(POLICYENGINE_DB)  # Uses POLICYENGINE_DB_PASSWORD env var
    """

    def __init__(
        self,
        url: str = "sqlite:///:memory:",
        seed_countries: Iterable[str] | None = None,
    ):
        # Special shortcut: connect to PolicyEngine live DB using env vars
        if url == POLICYENGINE_DB:
            pwd = os.getenv("POLICYENGINE_DB_PASSWORD")
            if not pwd:
                raise ValueError(
                    "POLICYENGINE_DB_PASSWORD is not set in environment."
                )
            user = os.getenv(
                "POLICYENGINE_DB_USER", "postgres.usugnrssspkdutcjeevk"
            )
            host = os.getenv(
                "POLICYENGINE_DB_HOST", "aws-1-us-east-1.pooler.supabase.com"
            )
            port = int(os.getenv("POLICYENGINE_DB_PORT", "5432"))
            dbname = os.getenv("POLICYENGINE_DB_NAME", "postgres")
            url = f"postgresql://{user}:{pwd}@{host}:{port}/{dbname}"

        self.engine = create_engine(url=url)
        SQLModel.metadata.create_all(self.engine)

        # Mapping between BaseModel classes and SQLModel table classes
        self._bm_to_table: Dict[type, type[SQLModel]] = {
            User: UserTable,
            UserPolicy: UserPolicyTable,
            UserSimulation: UserSimulationTable,
            UserReport: UserReportTable,
            UserReportElement: UserReportElementTable,
            Policy: PolicyTable,
            Dynamic: DynamicTable,
            Parameter: ParameterTable,
            ParameterValue: ParameterValueTable,
            BaselineParameterValue: BaselineParameterValueTable,
            Dataset: DatasetTable,
            Simulation: SimulationTable,
            Report: ReportTable,
            ReportElement: ReportElementTable,
            Variable: VariableTable,
            Aggregate: AggregateTable,
            Count: CountTable,
            ChangeByBaselineGroup: ChangeByBaselineGroupTable,
            VariableChangeGroupByQuantileGroup: VariableChangeGroupByQuantileGroupTable,
            VariableChangeGroupByVariableValue: VariableChangeGroupByVariableValueTable,
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

    def add_all(
        self,
        objs: Iterable[Any],
        *,
        cascade: bool = True,
        refresh: bool = True,
        chunk_size: int = 500,
        progress: bool = False,
    ) -> list[SQLModel]:
        """Insert or upsert a collection of BaseModel objects, generically.

        - Processes items in chunks, committing per chunk.
        - Optional lightweight progress output for visibility.
        - For specialized bulk behavior (e.g., ParameterValue series replacement),
          use a dedicated method instead of overloading this generic one.
        """
        items = list(objs)
        if not items:
            return []

        # Try to use an optimized batched upsert path for uniform models
        results: list[SQLModel] = []
        total = len(items)

        # Helper: determine table class for a base object
        def _tbl_cls_for(obj: Any) -> type[SQLModel]:
            return self._resolve_table_class(obj)

        first_tbl = _tbl_cls_for(items[0])
        uniform = all(_tbl_cls_for(o) is first_tbl for o in items)

        # Natural key config per table for fast batch upsert
        from policyengine.tables import (
            VariableTable as VarT,
            ParameterTable as ParT,
            PolicyTable as PolT,
            DynamicTable as DynT,
            ReportTable as RepT,
            ReportElementTable as RepElT,
            DatasetTable as DsT,
        )

        Key = tuple[str, ...]

        # Natural keys per table; kept minimal and generic
        bulk_key_fields: dict[type[SQLModel], Key] = {
            VarT: ("name", "country"),
            ParT: ("name", "country"),
            PolT: ("name", "country"),
            DynT: ("name", "country"),
            RepT: ("name", "country"),
            RepElT: ("name", "country"),
            DsT: ("name",),
        }

        use_bulk = uniform and (first_tbl in bulk_key_fields)

        with self.session() as s:
            pbar = None
            if progress:
                from tqdm.auto import tqdm  # type: ignore

                pbar = tqdm(total=total, desc="Adding", unit="row")

            if not use_bulk:
                # Fallback: existing per-row upsert path
                for start in range(0, total, max(1, chunk_size)):
                    end = min(start + chunk_size, total)
                    for obj in items[start:end]:
                        row = self._to_table(obj, s, cascade=cascade)
                        row = self._upsert_row(obj, row, s)
                        s.add(row)
                        results.append(row)
                    s.commit()
                    if pbar is not None:
                        pbar.update(end - start)
            else:
                # Optimized: batch fetch existing rows by natural key and update/insert
                key_fields = bulk_key_fields[first_tbl]
                # Derive updatable fields dynamically from table columns, excluding PKs and key fields
                # This keeps behavior general (e.g., if a table adds model_version later).
                table_columns = list(first_tbl.__table__.columns)
                pk_names = {c.name for c in table_columns if c.primary_key}
                upd_fields = tuple(
                    c.name
                    for c in table_columns
                    if (c.name not in pk_names) and (c.name not in key_fields)
                )

                for start in range(0, total, max(1, chunk_size)):
                    end = min(start + chunk_size, total)
                    batch = items[start:end]

                    # Convert to table rows first (to resolve FKs, etc.)
                    new_rows: list[SQLModel] = [
                        self._to_table(obj, s, cascade=cascade) for obj in batch
                    ]

                    # Build key -> new_row map for easy lookup
                    def _key_from_row(r: SQLModel) -> tuple[Any, ...]:
                        return tuple(getattr(r, k) for k in key_fields)

                    key_to_new = {_key_from_row(r): r for r in new_rows}

                    # Fetch existing rows in as few queries as possible
                    tbl = first_tbl
                    from sqlalchemy import and_, or_

                    existing_map: dict[tuple[Any, ...], SQLModel] = {}

                    # For Dataset (single key)
                    if key_fields == ("name",):
                        names = {k[0] for k in key_to_new.keys()}
                        if names:
                            stmt = select(tbl).where(getattr(tbl, "name").in_(list(names)))
                            for r in s.exec(stmt).all():
                                existing_map[(getattr(r, "name"),)] = r
                    else:
                        # Keys of form (name, country)
                        names = {k[0] for k in key_to_new.keys()}
                        countries_non_null = {k[1] for k in key_to_new.keys() if k[1] is not None}
                        names_null_country = {k[0] for k in key_to_new.keys() if k[1] is None}

                        conds = []
                        if names and countries_non_null:
                            conds.append(
                                and_(
                                    getattr(tbl, "name").in_(list(names)),
                                    getattr(tbl, "country").in_(list(countries_non_null)),
                                )
                            )
                        if names_null_country:
                            conds.append(
                                and_(
                                    getattr(tbl, "name").in_(list(names_null_country)),
                                    getattr(tbl, "country").is_(None),
                                )
                            )
                        if conds:
                            stmt = select(tbl).where(or_(*conds))
                            for r in s.exec(stmt).all():
                                key = (getattr(r, "name"), getattr(r, "country"))
                                if key in key_to_new:
                                    existing_map[key] = r

                    # Apply updates or stage inserts
                    for key, new_row in key_to_new.items():
                        existing = existing_map.get(key)
                        if existing is not None:
                            # Update only the allowed fields to mirror _upsert_row
                            for col in upd_fields:
                                setattr(existing, col, getattr(new_row, col))
                            results.append(existing)
                        else:
                            s.add(new_row)
                            results.append(new_row)

                    s.commit()
                    if pbar is not None:
                        pbar.update(end - start)

            if pbar is not None:
                pbar.close()
            if refresh:
                for row in results:
                    s.refresh(row)
        return results

    def delete_baseline_parameter_values_by_model_version(
        self, model_version: str, country: str | None = None
    ) -> int:
        """Delete all ParameterValue rows for a given model version and country.
        
        Args:
            model_version: The model version to delete
            country: Optional country filter
            
        Returns:
            Number of rows deleted
        """
        from policyengine.tables import BaselineParameterValueTable
        
        with self.session() as s:
            stmt = delete(BaselineParameterValueTable).where(
                BaselineParameterValueTable.model_version == model_version
            )
            if country is not None:
                stmt = stmt.where(BaselineParameterValueTable.country == country)

            result = s.exec(stmt)
            deleted_count = result.rowcount
            s.commit()
            
        return deleted_count

    # ------------------- Seeding -------------------
    def seed(self, countries: Iterable[str]) -> None:
        """Seed database with metadata for selected countries.

        Accepts any subset of {"uk", "us"}. Uses country-specific metadata
        helpers to load Variables, Parameters (via ParameterValues), and
        default Policy/Dynamic and upserts them into the DB.
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
                raise ValueError(
                    f"Unknown country code for seeding: {country}"
                )

            # Upsert policy and dynamic anchors
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

            # Convert parameter values to baseline parameter values
            baseline_values = []
            for pv in md.get("parameter_values", []) or []:
                if pv.parameter is not None:
                    # Create BaselineParameterValue instead
                    from policyengine.models.baseline_parameter import BaselineParameterValue
                    
                    bpv = BaselineParameterValue(
                        policy=pv.policy,
                        dynamic=pv.dynamic,
                        parameter=pv.parameter,
                        model_version=pv.model_version,
                        start_date=pv.start_date,
                        end_date=pv.end_date,
                        value=pv.value,
                        country=country,
                    )
                    baseline_values.append(bpv)
            
            if baseline_values:
                print(f"  Adding {len(baseline_values)} baseline parameter values...")
                self.add_all(
                    baseline_values,
                    refresh=False,
                    progress=True,
                    chunk_size=1000,
                )

            # Country datasets (default range) – sourced via dedicated helpers
            try:
                if country == "uk":
                    from policyengine.countries.uk.metadata import (
                        get_uk_datasets,
                    )

                    datasets = get_uk_datasets(2023, 2030)
                elif country == "us":
                    from policyengine.countries.us.metadata import (
                        get_us_datasets,
                    )

                    datasets = get_us_datasets(2024, 2035)
                else:
                    datasets = []
            except Exception:
                datasets = []
            if datasets:
                self.add_all(datasets, refresh=False)

    def get(
        self,
        model_cls: Type[BM],
        id: Any | None = None,
        *,
        cascade: bool = False,
        **filters: Any,
    ) -> BM | None:
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
                    raise ValueError(
                        f"Unknown field for {table_cls.__name__}: {key}"
                    )
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

    def list(
        self, model_cls: Type[BM], *, limit: int | None = None
    ) -> list[BM]:
        """List BaseModel instances for a given class."""
        table_cls = self._resolve_table_class(model_cls)
        with self.session() as s:
            stmt = select(table_cls)
            if limit is not None:
                stmt = stmt.limit(limit)
            rows = s.exec(stmt).all()
            return [self._to_model(r, s, cascade=False) for r in rows]

    # ------------------- Mapping helpers -------------------
    def _resolve_table_class(
        self, obj_or_cls: Union[Any, type]
    ) -> type[SQLModel]:
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

        # Policy, Dynamic, Parameters
        if isinstance(obj, Policy):
            # Pickle simulation_modifier if provided
            sim_bytes = None
            try:
                if obj.simulation_modifier is not None:
                    sim_bytes = pickle.dumps(obj.simulation_modifier)
            except Exception:
                # If pickling fails, store nothing; user can correct function
                sim_bytes = None
            return PolicyTable(
                id=getattr(obj, "id", None),
                name=obj.name,
                description=obj.description,
                country=obj.country,
                simulation_modifier_bytes=sim_bytes,
            )

        if isinstance(obj, Dynamic):
            parent_id = None
            if obj.parent_dynamic is not None and cascade:
                parent_row = self._to_table(
                    obj.parent_dynamic, s, cascade=cascade
                )
                parent_row = self._upsert_row(
                    obj.parent_dynamic, parent_row, s
                )
                s.add(parent_row)
                s.flush()
                parent_id = parent_row.id
            # Pickle simulation_modifier if provided
            sim_bytes = None
            if obj.simulation_modifier is not None:
                sim_bytes = pickle.dumps(obj.simulation_modifier)
            return DynamicTable(
                id=getattr(obj, "id", None),
                name=obj.name,
                parent_id=parent_id,
                description=obj.description,
                created_at=obj.created_at,
                updated_at=obj.updated_at,
                country=obj.country,
                simulation_modifier_bytes=sim_bytes,
            )

        if isinstance(obj, Parameter):
            parent_id = None
            if obj.parent is not None and cascade:
                parent_row = self._to_table(obj.parent, s, cascade=cascade)
                parent_row = self._upsert_row(obj.parent, parent_row, s)
                s.add(parent_row)
                s.flush()
                parent_id = parent_row.id
            data_type = (
                obj.data_type.__name__
                if isinstance(obj.data_type, type)
                else str(obj.data_type)
            )
            return ParameterTable(
                id=getattr(obj, "id", None),
                name=obj.name,
                parent_id=parent_id,
                label=obj.label,
                description=obj.description,
                unit=obj.unit,
                data_type=data_type,
                country=obj.country,
            )

        if isinstance(obj, BaselineParameterValue):
            # BaselineParameterValue - links to Policy or Dynamic by name lookup
            from policyengine.tables import (
                PolicyTable as PoTable,
                DynamicTable as DTable,
            )
            
            policy_id = None
            if obj.policy is not None:
                pol = obj.policy
                pol_row = s.exec(
                    select(PoTable).where(
                        PoTable.name == pol.name,
                        PoTable.country == pol.country,
                    )
                ).first()
                if pol_row is None:
                    # Create the policy if it doesn't exist
                    pol_row = self._to_table(pol, s, cascade=cascade)
                    pol_row = self._upsert_row(pol, pol_row, s)
                    s.add(pol_row)
                    s.flush()
                policy_id = pol_row.id
            
            dynamic_id = None
            if obj.dynamic is not None:
                dyn = obj.dynamic
                dyn_row = s.exec(
                    select(DTable).where(
                        DTable.name == dyn.name, DTable.country == dyn.country
                    )
                ).first()
                if dyn_row is None:
                    # Create the dynamic if it doesn't exist
                    dyn_row = self._to_table(dyn, s, cascade=cascade)
                    dyn_row = self._upsert_row(dyn, dyn_row, s)
                    s.add(dyn_row)
                    s.flush()
                dynamic_id = dyn_row.id
            
            # Handle parameter field
            parameter_id = None
            if obj.parameter:
                param_row = self._to_table(obj.parameter, s)
                if param_row.id is None:
                    # If parameter doesn't have an ID, try to find or create it
                    from policyengine.tables import ParameterTable as PTable
                    existing_param = s.exec(
                        select(PTable).where(
                            PTable.name == param_row.name,
                            PTable.country == param_row.country,
                        )
                    ).first()
                    if existing_param:
                        parameter_id = existing_param.id
                    else:
                        param_row = self._upsert_row(obj.parameter, param_row, s)
                        s.add(param_row)
                        s.flush()
                        parameter_id = param_row.id
                else:
                    parameter_id = param_row.id
            
            return BaselineParameterValueTable(
                id=getattr(obj, "id", None),
                policy_id=policy_id,
                dynamic_id=dynamic_id,
                parameter_id=parameter_id,
                model_version=obj.model_version,
                start_date=obj.start_date,
                end_date=obj.end_date,
                value=self._json_safe_value(obj.value),
                country=obj.country,
            )

        if isinstance(obj, ParameterValue):
            # Do not auto-create/link related rows here; only resolve by lookup.
            from policyengine.tables import (
                ParameterTable as PTable,
                PolicyTable as PoTable,
                DynamicTable as DTable,
            )

            # parameter is required and must already exist (by name+country)
            if obj.parameter is None:
                raise ValueError("ParameterValue.parameter is required")
            par = obj.parameter
            par_row = s.exec(
                select(PTable).where(
                    PTable.name == par.name, PTable.country == par.country
                )
            ).first()
            if par_row is None:
                raise ValueError(
                    f"Parameter not found for value: {par.name} ({par.country})"
                )

            policy_id = None
            if obj.policy is not None:
                pol = obj.policy
                pol_row = s.exec(
                    select(PoTable).where(
                        PoTable.name == pol.name,
                        PoTable.country == pol.country,
                    )
                ).first()
                if pol_row is None:
                    raise ValueError(
                        f"Policy not found for value: {pol.name} ({pol.country})"
                    )
                policy_id = pol_row.id

            dynamic_id = None
            if obj.dynamic is not None:
                dyn = obj.dynamic
                dyn_row = s.exec(
                    select(DTable).where(
                        DTable.name == dyn.name, DTable.country == dyn.country
                    )
                ).first()
                if dyn_row is None:
                    raise ValueError(
                        f"Dynamic not found for value: {dyn.name} ({dyn.country})"
                    )
                dynamic_id = dyn_row.id

            # JSON-safe value handling (inf/-inf, NaN)
            return ParameterValueTable(
                id=getattr(obj, "id", None),
                policy_id=policy_id,
                dynamic_id=dynamic_id,
                parameter_id=par_row.id,  # type: ignore[arg-type]
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
                src_row = self._to_table(
                    obj.source_dataset, s, cascade=cascade
                )
                src_row = self._upsert_row(obj.source_dataset, src_row, s)
                s.add(src_row)
                s.flush()
                source_id = src_row.id
            data_bytes = None
            if isinstance(obj.data, SingleYearDataset):
                data_bytes = obj.data.serialise()
            elif isinstance(obj.data, (bytes, bytearray)):
                data_bytes = bytes(obj.data)
            return DatasetTable(
                id=getattr(obj, "id", None),
                name=obj.name,
                source_dataset_id=source_id,
                version=obj.version,
                data_bytes=data_bytes,
                dataset_type=obj.dataset_type,
            )

        # Simulation
        if isinstance(obj, Simulation):
            dataset_id = policy_id = dynamic_id = result_dataset_id = None
            if obj.dataset is not None and cascade:
                ds_row = self._to_table(obj.dataset, s, cascade=cascade)
                ds_row = self._upsert_row(obj.dataset, ds_row, s)
                s.add(ds_row)
                s.flush()
                dataset_id = ds_row.id
            if obj.policy is not None and cascade:
                po_row = self._to_table(obj.policy, s, cascade=cascade)
                po_row = self._upsert_row(obj.policy, po_row, s)
                s.add(po_row)
                s.flush()
                policy_id = po_row.id
            if obj.dynamic is not None and cascade:
                dy_row = self._to_table(obj.dynamic, s, cascade=cascade)
                dy_row = self._upsert_row(obj.dynamic, dy_row, s)
                s.add(dy_row)
                s.flush()
                dynamic_id = dy_row.id
            if isinstance(obj.result, Dataset) and cascade:
                rs_row = self._to_table(obj.result, s, cascade=cascade)
                rs_row = self._upsert_row(obj.result, rs_row, s)
                s.add(rs_row)
                s.flush()
                result_dataset_id = rs_row.id
            return SimulationTable(
                id=getattr(obj, "id", None),
                dataset_id=dataset_id,
                policy_id=policy_id,
                dynamic_id=dynamic_id,
                result_dataset_id=result_dataset_id,
                model_version=obj.model_version,
                country=obj.country,
                status=obj.status,
                created_at=obj.created_at,
                completed_at=obj.completed_at,
            )

        # Reports
        if isinstance(obj, Report):
            return ReportTable(
                id=getattr(obj, "id", None),
                name=obj.name,
                description=obj.description,
                country=obj.country,
            )

        if isinstance(obj, ReportElement):
            report_id = None
            if obj.report is not None and cascade:
                rep_row = self._to_table(obj.report, s, cascade=cascade)
                rep_row = self._upsert_row(obj.report, rep_row, s)
                s.add(rep_row)
                s.flush()
                report_id = rep_row.id
            return ReportElementTable(
                id=getattr(obj, "id", None),
                name=obj.name,
                description=obj.description,
                report_id=report_id,
                status=obj.status,
                country=obj.country,
            )

        # Report item data rows
        if isinstance(obj, Aggregate):
            sim_row = self._to_table(obj.simulation, s, cascade=cascade)
            if getattr(sim_row, "id", None) is None:
                s.add(sim_row)
                s.flush()
            return AggregateTable(
                simulation_id=sim_row.id,  # type: ignore[arg-type]
                time_period=str(obj.time_period)
                if obj.time_period is not None
                else None,
                variable=obj.variable,
                entity_level=obj.entity_level,
                filter_variable=obj.filter_variable,
                filter_variable_value=self._json_safe_value(
                    obj.filter_variable_value
                ),
                filter_variable_min_value=obj.filter_variable_min_value,
                filter_variable_max_value=obj.filter_variable_max_value,
                metric=str(obj.metric),
                value=obj.value,
            )

        if isinstance(obj, Count):
            sim_row = self._to_table(obj.simulation, s, cascade=cascade)
            if getattr(sim_row, "id", None) is None:
                s.add(sim_row)
                s.flush()
            return CountTable(
                simulation_id=sim_row.id,  # type: ignore[arg-type]
                time_period=str(obj.time_period)
                if obj.time_period is not None
                else None,
                variable=obj.variable,
                entity_level=obj.entity_level,
                equals_value=self._json_safe_value(obj.equals_value),
                min_value=obj.min_value,
                max_value=obj.max_value,
                count=obj.count,
            )

        if isinstance(obj, ChangeByBaselineGroup):
            base_row = self._to_table(
                obj.baseline_simulation, s, cascade=cascade
            )
            ref_row = self._to_table(obj.reform_simulation, s, cascade=cascade)
            for r in (base_row, ref_row):
                if getattr(r, "id", None) is None:
                    s.add(r)
                    s.flush()
            return ChangeByBaselineGroupTable(
                baseline_simulation_id=base_row.id,  # type: ignore[arg-type]
                reform_simulation_id=ref_row.id,  # type: ignore[arg-type]
                variable=obj.variable,
                group_variable=obj.group_variable,
                group_value=self._json_safe_value(obj.group_value),
                entity_level=obj.entity_level,
                time_period=str(obj.time_period)
                if obj.time_period is not None
                else None,
                total_change=obj.total_change,
                relative_change=obj.relative_change,
                average_change_per_entity=obj.average_change_per_entity,
            )

        if isinstance(obj, VariableChangeGroupByQuantileGroup):
            base_row = self._to_table(
                obj.baseline_simulation, s, cascade=cascade
            )
            ref_row = self._to_table(obj.reform_simulation, s, cascade=cascade)
            for r in (base_row, ref_row):
                if getattr(r, "id", None) is None:
                    s.add(r)
                    s.flush()
            return VariableChangeGroupByQuantileGroupTable(
                baseline_simulation_id=base_row.id,  # type: ignore[arg-type]
                reform_simulation_id=ref_row.id,  # type: ignore[arg-type]
                variable=obj.variable,
                group_variable=obj.group_variable,
                quantile_group=obj.quantile_group,
                quantile_group_count=obj.quantile_group_count,
                change_lower_bound=float(obj.change_lower_bound),
                change_upper_bound=float(obj.change_upper_bound),
                change_bound_is_relative=bool(obj.change_bound_is_relative),
                fixed_entity_count_per_quantile_group=obj.fixed_entity_count_per_quantile_group,
                percent_of_group_in_change_group=obj.percent_of_group_in_change_group,
                entities_in_group_in_change_group=obj.entities_in_group_in_change_group,
            )

        if isinstance(obj, VariableChangeGroupByVariableValue):
            base_row = self._to_table(
                obj.baseline_simulation, s, cascade=cascade
            )
            ref_row = self._to_table(obj.reform_simulation, s, cascade=cascade)
            for r in (base_row, ref_row):
                if getattr(r, "id", None) is None:
                    s.add(r)
                    s.flush()
            return VariableChangeGroupByVariableValueTable(
                baseline_simulation_id=base_row.id,  # type: ignore[arg-type]
                reform_simulation_id=ref_row.id,  # type: ignore[arg-type]
                variable=obj.variable,
                group_variable=obj.group_variable,
                group_variable_value=self._json_safe_value(
                    obj.group_variable_value
                ),
                fixed_entity_count_per_quantile_group=obj.fixed_entity_count_per_quantile_group,
                percent_of_group_in_change_group=obj.percent_of_group_in_change_group,
                entities_in_group_in_change_group=obj.entities_in_group_in_change_group,
            )

        # Variable
        if isinstance(obj, Variable):
            data_type = (
                obj.data_type.__name__
                if isinstance(obj.data_type, type)
                else str(obj.data_type)
            )
            return VariableTable(
                id=getattr(obj, "id", None),
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
            user = self._to_model(
                s.get(UserTable, row.user_id), s, cascade=False
            )
            policy = (
                self._to_model(
                    s.get(PolicyTable, row.policy_id), s, cascade=False
                )
                if row.policy_id is not None
                else None
            )
            return UserPolicy(
                user=user,
                policy=policy,
                label=row.label,
                description=row.description,
            )

        if isinstance(row, UserSimulationTable):
            user = self._to_model(
                s.get(UserTable, row.user_id), s, cascade=False
            )
            sim = (
                self._to_model(
                    s.get(SimulationTable, row.simulation_id), s, cascade=False
                )
                if row.simulation_id is not None
                else None
            )
            return UserSimulation(
                user=user,
                simulation=sim,
                label=row.label,
                description=row.description,
            )

        if isinstance(row, UserReportTable):
            user = self._to_model(
                s.get(UserTable, row.user_id), s, cascade=False
            )
            report = (
                self._to_model(
                    s.get(ReportTable, row.report_id), s, cascade=False
                )
                if row.report_id is not None
                else None
            )
            return UserReport(
                user=user,
                report=report,
                label=row.label,
                description=row.description,
            )

        if isinstance(row, UserReportElementTable):
            user = self._to_model(
                s.get(UserTable, row.user_id), s, cascade=False
            )
            el = (
                self._to_model(
                    s.get(ReportElementTable, row.report_element_id),
                    s,
                    cascade=False,
                )
                if row.report_element_id is not None
                else None
            )
            return UserReportElement(
                user=user,
                report_element=el,
                label=row.label,
                description=row.description,
            )

        # Policy, Dynamic, Parameters
        if isinstance(row, PolicyTable):
            # Unpickle simulation_modifier if present
            sim_mod = None
            if getattr(row, "simulation_modifier_bytes", None):
                try:
                    sim_mod = pickle.loads(row.simulation_modifier_bytes)  # type: ignore[arg-type]
                except Exception:
                    sim_mod = None
            return Policy(
                id=row.id,
                name=row.name,
                description=row.description,
                simulation_modifier=sim_mod,
                country=row.country,
            )

        if isinstance(row, DynamicTable):
            parent = (
                self._to_model(
                    s.get(DynamicTable, row.parent_id), s, cascade=False
                )
                if (cascade and row.parent_id is not None)
                else None
            )
            # Unpickle simulation_modifier if present
            sim_mod = None
            if row.simulation_modifier_bytes is not None:
                sim_mod = pickle.loads(row.simulation_modifier_bytes)  # type: ignore[arg-type]
            return Dynamic(
                id=row.id,
                name=row.name,
                parent_dynamic=parent,
                description=row.description,
                created_at=row.created_at,
                updated_at=row.updated_at,
                simulation_modifier=sim_mod,
                country=row.country,
            )

        if isinstance(row, ParameterTable):
            parent = (
                self._to_model(
                    s.get(ParameterTable, row.parent_id), s, cascade=False
                )
                if (cascade and row.parent_id is not None)
                else None
            )
            data_type_map = {
                "float": float,
                "int": int,
                "bool": bool,
                "string": str,
            }
            data_type = data_type_map.get(row.data_type, str)
            return Parameter(
                id=row.id,
                name=row.name,
                parent=parent,
                label=row.label,
                description=row.description,
                unit=row.unit,
                data_type=data_type,
                country=row.country,
            )

        if isinstance(row, BaselineParameterValueTable):
            policy = (
                self._to_model(
                    s.get(PolicyTable, row.policy_id), s, cascade=False
                )
                if (cascade and row.policy_id is not None)
                else None
            )
            dynamic = (
                self._to_model(
                    s.get(DynamicTable, row.dynamic_id), s, cascade=False
                )
                if (cascade and row.dynamic_id is not None)
                else None
            )
            # Fetch the parameter
            parameter = (
                self._to_model(
                    s.get(ParameterTable, row.parameter_id), s, cascade=False
                )
                if row.parameter_id is not None
                else None
            )
            return BaselineParameterValue(
                id=row.id,
                policy=policy,
                dynamic=dynamic,
                parameter=parameter,
                model_version=row.model_version,
                start_date=row.start_date,
                end_date=row.end_date,
                value=self._json_restore_value(row.value),
                country=row.country,
            )

        if isinstance(row, ParameterValueTable):
            policy = (
                self._to_model(
                    s.get(PolicyTable, row.policy_id), s, cascade=False
                )
                if (cascade and row.policy_id is not None)
                else None
            )
            dynamic = (
                self._to_model(
                    s.get(DynamicTable, row.dynamic_id), s, cascade=False
                )
                if (cascade and row.dynamic_id is not None)
                else None
            )
            parameter = (
                self._to_model(
                    s.get(ParameterTable, row.parameter_id), s, cascade=False
                )
                if row.parameter_id is not None
                else None
            )
            return ParameterValue(
                id=row.id,
                policy=policy,
                dynamic=dynamic,
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
                self._to_model(
                    s.get(DatasetTable, row.source_dataset_id),
                    s,
                    cascade=False,
                )
                if (cascade and row.source_dataset_id is not None)
                else None
            )
            data = (
                SingleYearDataset(serialised_bytes=row.data_bytes)
                if row.data_bytes is not None
                else None
            )
            return Dataset(
                id=row.id,
                name=row.name,
                source_dataset=source,
                version=row.version,
                data=data,
                dataset_type=row.dataset_type,
            )

        # Simulation
        if isinstance(row, SimulationTable):
            dataset = (
                self._to_model(
                    s.get(DatasetTable, row.dataset_id), s, cascade=False
                )
                if row.dataset_id is not None
                else None
            )
            policy = (
                self._to_model(
                    s.get(PolicyTable, row.policy_id), s, cascade=False
                )
                if row.policy_id is not None
                else None
            )
            dynamic = (
                self._to_model(
                    s.get(DynamicTable, row.dynamic_id), s, cascade=False
                )
                if row.dynamic_id is not None
                else None
            )
            result = (
                self._to_model(
                    s.get(DatasetTable, row.result_dataset_id),
                    s,
                    cascade=False,
                )
                if row.result_dataset_id is not None
                else None
            )
            return Simulation(
                id=row.id,
                dataset=dataset,  # type: ignore[arg-type]
                policy=policy,  # type: ignore[arg-type]
                dynamic=dynamic,  # type: ignore[arg-type]
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
            return Report(
                id=row.id,
                name=row.name,
                description=row.description,
                elements=[],
                country=row.country,
            )

        if isinstance(row, ReportElementTable):
            report = (
                self._to_model(
                    s.get(ReportTable, row.report_id), s, cascade=False
                )
                if (cascade and row.report_id is not None)
                else None
            )
            return ReportElement(
                id=row.id,
                name=row.name,
                description=row.description,
                report=report,  # type: ignore[arg-type]
                status=row.status,
                country=row.country,
            )

        # Variable
        if isinstance(row, VariableTable):
            data_type_map = {
                "float": float,
                "int": int,
                "bool": bool,
                "string": str,
            }
            data_type = data_type_map.get(row.data_type, str)
            return Variable(
                id=row.id,
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
        - Dynamic: same name+country replaces
        - ParameterValue: same (parameter, model_version, start/end, policy, dynamic, country) replaces
        - BaselineParameterValue: same (parameter_id, model_version, start/end, policy, dynamic, country) replaces
        - Report/ReportElement: same name+country replaces (best-effort)
        """
        from policyengine.tables import (
            PolicyTable,
            DynamicTable,
            ParameterTable,
            ParameterValueTable,
            BaselineParameterValueTable,
            VariableTable,
            ReportTable,
            ReportElementTable,
            DatasetTable,
        )

        # If an explicit primary key is provided on the row, prefer updating
        # that row directly to avoid accidental duplication when callers
        # rehydrate then persist again.
        try:
            row_id = getattr(new_row, "id", None)
            if row_id is not None:
                existing_by_id = s.get(type(new_row), row_id)
                if existing_by_id is not None:
                    for field in getattr(new_row, "model_fields", {}).keys():
                        if field == "id":
                            continue
                        setattr(existing_by_id, field, getattr(new_row, field))
                    return existing_by_id
        except Exception:
            pass

        # Policy
        if isinstance(new_row, PolicyTable):
            stmt = select(PolicyTable).where(
                PolicyTable.name == new_row.name,
                PolicyTable.country == new_row.country,
            )
            existing = s.exec(stmt).first()
            if existing:
                existing.description = new_row.description
                existing.country = new_row.country
                existing.simulation_modifier_bytes = (
                    new_row.simulation_modifier_bytes
                )
                return existing
            return new_row

        # Dynamic
        if isinstance(new_row, DynamicTable):
            stmt = select(DynamicTable).where(
                DynamicTable.name == new_row.name,
                DynamicTable.country == new_row.country,
            )
            existing = s.exec(stmt).first()
            if existing:
                existing.parent_id = new_row.parent_id
                existing.description = new_row.description
                existing.created_at = new_row.created_at
                existing.updated_at = new_row.updated_at
                existing.country = new_row.country
                existing.simulation_modifier_bytes = (
                    new_row.simulation_modifier_bytes
                )
                return existing
            return new_row

        # Parameter
        if isinstance(new_row, ParameterTable):
            stmt = select(ParameterTable).where(
                ParameterTable.name == new_row.name,
                ParameterTable.country == new_row.country,
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

        # BaselineParameterValue
        if isinstance(new_row, BaselineParameterValueTable):
            stmt = select(BaselineParameterValueTable).where(
                BaselineParameterValueTable.parameter_id == new_row.parameter_id,
                BaselineParameterValueTable.model_version == new_row.model_version,
                BaselineParameterValueTable.start_date == new_row.start_date,
                BaselineParameterValueTable.end_date.is_(new_row.end_date)
                if new_row.end_date is None
                else BaselineParameterValueTable.end_date == new_row.end_date,
                BaselineParameterValueTable.policy_id.is_(new_row.policy_id)
                if new_row.policy_id is None
                else BaselineParameterValueTable.policy_id == new_row.policy_id,
                BaselineParameterValueTable.dynamic_id.is_(new_row.dynamic_id)
                if new_row.dynamic_id is None
                else BaselineParameterValueTable.dynamic_id == new_row.dynamic_id,
                BaselineParameterValueTable.country == new_row.country,
            )
            existing = s.exec(stmt).first()
            if existing:
                existing.value = new_row.value
                return existing
            return new_row

        # ParameterValue - for the simplified approach, we don't upsert these
        # They should be deleted and recreated during migration
        if isinstance(new_row, ParameterValueTable):
            # Just return the new row without checking for duplicates
            # The migration handles deletion/recreation
            return new_row

        # Variable
        if isinstance(new_row, VariableTable):
            stmt = select(VariableTable).where(
                VariableTable.name == new_row.name,
                VariableTable.country == new_row.country,
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
                ReportTable.name == new_row.name,
                ReportTable.country == new_row.country,
            )
            existing = s.exec(stmt).first()
            if existing:
                existing.description = new_row.description
                existing.country = new_row.country
                return existing
            return new_row

        if isinstance(new_row, ReportElementTable):
            stmt = select(ReportElementTable).where(
                ReportElementTable.name == new_row.name,
                ReportElementTable.country == new_row.country,
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
            stmt = select(DatasetTable).where(
                DatasetTable.name == new_row.name
            )
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
