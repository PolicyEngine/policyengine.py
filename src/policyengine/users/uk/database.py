from policyengine.users.uk.tables import (
    SimulationDB,
    DatasetDB,
    AggregateChangeDB,
    AggregateChangeReportElementDB,
    DatasetDB,
    PolicyDB,
    DynamicsDB,
    ReportDB,
    VariableDB,
    ParameterDB,
    ParameterValueDB,
)
from sqlmodel import SQLModel, create_engine, MetaData, select, delete, Session
from policyengine.utils.dataframe_storage import deserialise_dataframe_dict, serialise_dataframe_dict

class Database:
    tables = [
        DatasetDB,
        SimulationDB,
        PolicyDB,
        DynamicsDB,
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