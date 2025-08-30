from policyengine.database import (
    Dataset,
    Simulation,
    Policy,
    Dynamics,
    Report,
    ReportElement,
    ReportElementDataItem,
    Variable,
    Parameter,
    ParameterValue
)
from sqlmodel import SQLModel, create_engine

class Database:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url)

    def create_tables(self):
        Dataset.__table__.create(self.engine)
        Simulation.__table__.create(self.engine)
        Policy.__table__.create(self.engine)
        Dynamics.__table__.create(self.engine)
        Report.__table__.create(self.engine)
        ReportElement.__table__.create(self.engine)
        ReportElementDataItem.__table__.create(self.engine)
        Variable.__table__.create(self.engine)
        Parameter.__table__.create(self.engine)
        ParameterValue.__table__.create(self.engine)
