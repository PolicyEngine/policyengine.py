from policyengine.users.uk.tables import (
    SimulationDB,
    DatasetDB,
    AggregateChangeDB,
    AggregateChangeReportElementDB,
    PolicyDB,
    DynamicsDB,
    ReportDB,
    VariableDB,
    ParameterDB,
    ParameterValueDB,
)
from policyengine.users.uk.models import (
    Simulation,
    Dataset,
    AggregateChange,
    AggregateChangeReportElement,
    Policy,
    Dynamics,
    Report,
    Variable,
    Parameter,
    ParameterValue,
    current_law,
    UKSingleYearDataset,
)
from pydantic import BaseModel
from sqlmodel import SQLModel, create_engine, MetaData, select, delete, Session
from policyengine.utils.dataframe_storage import (
    deserialise_dataframe_dict,
    serialise_dataframe_dict,
)
from policyengine.utils.parametric_reforms import apply_parametric_reform
from policyengine_uk.model_api import Scenario


class Database:
    tables = [
        DatasetDB,
        PolicyDB,
        DynamicsDB,
        SimulationDB,
        ReportDB,
        VariableDB,
        ParameterDB,
        ParameterValueDB,
        AggregateChangeDB,
        AggregateChangeReportElementDB,
    ]

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url)
        self.session = Session(self.engine)

    def drop_tables(self):
        for table in reversed(self.tables):
            table.__table__.drop(self.engine, checkfirst=True)

    def create_tables(self):
        # Create all tables explicitly using SQLModel metadata
        # SQLModel.metadata already has the table definitions from the models

        for table in self.tables:
            table.__table__.create(self.engine, checkfirst=True)

    def recreate_tables(self):
        # Drop and recreate all tables with current schema
        self.drop_tables()
        self.create_tables()

    @property
    def current_law(self):
        return self.get_policy("current law")

    @property
    def no_dynamics(self):
        return self.get_dynamics("static")

    def get_policy(self, name: str) -> PolicyDB:
        return self.session.exec(select(PolicyDB).where(PolicyDB.name == name)).first()

    def get_dynamics(self, name: str) -> DynamicsDB:
        return self.session.exec(
            select(DynamicsDB).where(DynamicsDB.name == name)
        ).first()

    def get_parameter(self, name: str) -> ParameterDB:
        return self.session.exec(
            select(ParameterDB).where(ParameterDB.name == name)
        ).first()

    def seed(self):
        from .metadata import (
            add_parameters_to_db,
            add_variables_to_db,
            add_datasets_to_db,
            add_basic_policies_to_db,
        )

        add_basic_policies_to_db(self)
        add_parameters_to_db(self)
        add_variables_to_db(self)
        add_datasets_to_db(self)

    def add_policy(self, policy: Policy | PolicyDB):
        if isinstance(policy, PolicyDB):
            self.session.add(policy)
            self.session.commit()
        elif isinstance(policy, Policy):
            policy_db = PolicyDB(
                name=policy.name,
                description=policy.description,
                parameter_values=[
                    ParameterValueDB(
                        parameter_id=self.get_parameter(pv.parameter.name).id,
                        value=pv.value,
                        start_date=pv.start_date,
                        end_date=pv.end_date,
                    )
                    for pv in (policy.parameter_values or [])
                ],
            )
            self.session.add(policy_db)
            self.session.commit()

    def list_policies(self):
        return self.session.exec(select(PolicyDB)).all()

    def add_simulation(self, simulation: SimulationDB):
        self.session.add(simulation)
        self.session.commit()

    def get_dataset(
        self,
        name: str,
    ) -> DatasetDB:
        return self.session.exec(
            select(DatasetDB).where(DatasetDB.name == name)
        ).first()

    def add_report(self, report: ReportDB):
        self.session.add(report)
        self.session.commit()
