from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from sqlmodel import (
    Field,
    Session,
    SQLModel,
    create_engine,
    Relationship,
    select,
)
from enum import Enum
from pydantic import validator
from pathlib import Path


# Enums and Constants
class CountryCode(str, Enum):
    UK = "uk"
    US = "us"


class EntityType(str, Enum):
    ENTITY = "entity"  # Generic entity type


class BaseModel(SQLModel):
    """Base model with ID as primary key"""

    id: Optional[int] = Field(default=None, primary_key=True)


# Core policy models
class Country(BaseModel, table=True):
    """Country model representing supported jurisdictions"""

    code: str = Field(index=True, unique=True)  # 'uk', 'us'
    name: str  # 'United Kingdom', 'United States'

    # Relationships
    parameters: List["Parameter"] = Relationship(back_populates="country")
    reforms: List["Reform"] = Relationship(back_populates="country")
    entities: List["Entity"] = Relationship(back_populates="country")
    variables: List["Variable"] = Relationship(back_populates="country")
    simulation: List["Simulation"] = Relationship(back_populates="country")


class Reform(BaseModel, table=True):
    """A reform is a change to policy."""

    reform_id: str = Field(index=True)  # '35'
    name: str  # 'Set of parameter changes involving main tax rate'
    description: Optional[str] = None
    country_id: Optional[int] = Field(default=None, foreign_key="country.id")
    is_structural: bool = Field(
        default=False
    )  # True if the reform contains non-parametric changes

    # Relationships
    country: Optional[Country] = Relationship(back_populates="reforms")
    parameter_changes: List["ParameterChange"] = Relationship(
        back_populates="reform"
    )
    simulations: List["Simulation"] = Relationship(back_populates="reform")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if "parameters_dict" in kwargs:
            # Create ParameterChange objects from the provided dictionary
            for parameter_name, changes in kwargs["parameters_dict"].items():
                for time_period, value in changes.items():
                    parameter_change = ParameterChange(
                        parameter_name=parameter_name,
                        time_period=time_period,
                        value=value,
                    )
                    self.parameter_changes.append(parameter_change)


class Parameter(BaseModel, table=True):
    """Tax or benefit parameter definition"""

    country_id: int = Field(foreign_key="country.id")
    parameter_name: str = Field(index=True)  # 'gov.tax.rate'

    # Relationships
    country: Country = Relationship(back_populates="parameters")
    parameter_changes: List["ParameterChange"] = Relationship(
        back_populates="parameter"
    )


class ParameterChange(BaseModel, table=True):
    """Change to a parameter in a reform"""

    parameter_id: int = Field(foreign_key="parameter.id")
    reform_id: int = Field(foreign_key="reform.id")
    value: str
    time_period: str  # '2025'

    # Relationships
    parameter: Parameter = Relationship(back_populates="parameter_changes")
    reform: Reform = Relationship(back_populates="parameter_changes")


# Entity and dataset models
class Entity(BaseModel, table=True):
    """Entity model representing individuals, households, or other units"""

    id: Optional[int] = Field(default=None, primary_key=True)
    country_id: int = Field(foreign_key="country.id")
    entity_type: str = Field(
        index=True
    )  # Type of entity (person, household, etc.)
    dataset_id: Optional[int] = Field(default=None, foreign_key="dataset.id")

    # Relationships
    country: Country = Relationship(back_populates="entities")
    dataset: Optional["Dataset"] = Relationship(back_populates="entities")
    variable_states: List["VariableState"] = Relationship(
        back_populates="entity"
    )


class VersionedDataset(BaseModel, table=True):
    """Dataset containing entity records"""

    name: str
    description: Optional[str] = None
    dataset_series_id: int = Field(foreign_key="datasetseries.id")

    datasets: List["Dataset"] = Relationship(
        back_populates="versioned_dataset"
    )
    dataset_series: "DatasetSeries" = Relationship(
        back_populates="versioned_datasets"
    )


class DatasetSeries(BaseModel, table=True):
    """Series of related datasets (e.g., annual survey data)"""

    name: str
    description: Optional[str] = None

    # Relationships
    versioned_datasets: List["VersionedDataset"] = Relationship(
        back_populates="dataset_series"
    )


class Dataset(BaseModel, table=True):
    """Tags linking datasets to series with versioning"""

    versioned_dataset_id: int = Field(
        foreign_key="versioneddataset.id", primary_key=True
    )
    dataset_series_id: int = Field(
        foreign_key="datasetseries.id", primary_key=True
    )
    version: str

    # Relationships
    entities: List[Entity] = Relationship(back_populates="dataset")
    versioned_dataset: VersionedDataset = Relationship(
        back_populates="datasets"
    )
    simulations: List["Simulation"] = Relationship(back_populates="dataset")


# Variable models
class Variable(BaseModel, table=True):
    """Definition of a specific variable (income, expenditure, etc.)"""

    country_id: int = Field(foreign_key="country.id")
    name: str = Field(index=True)
    description: Optional[str] = None

    # Relationships
    country: Country = Relationship(back_populates="variables")
    variable_states: List["VariableState"] = Relationship(
        back_populates="variable"
    )


class VariableState(BaseModel, table=True):
    """Specific value of a variable for an entity at a point in time"""

    variable_id: int = Field(foreign_key="variable.id")
    entity_id: int = Field(foreign_key="entity.id")
    time_period: str  # '2025'
    value: str  # '30000'
    simulation_run_id: Optional[int] = Field(
        default=None, foreign_key="simulationrun.id"
    )

    # Relationships
    variable: Variable = Relationship(back_populates="variable_states")
    entity: Entity = Relationship(back_populates="variable_states")
    simulation_run: Optional["Simulation"] = Relationship(
        back_populates="variable_states"
    )


class Simulation(BaseModel, table=True):
    """Record of a specific policy simulation"""

    country_id: int = Field(foreign_key="country.id")

    reform_id: Optional[int] = Field(default=None, foreign_key="reform.id")
    package_version: str
    dataset_id: int = Field(foreign_key="dataset.id")
    run_date: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    reform: Optional[Reform] = Relationship(back_populates="simulations")
    country: Country = Relationship(back_populates="simulations")
    dataset: Dataset = Relationship(back_populates="simulations")
    variable_states: List["VariableState"] = Relationship(
        back_populates="simulation"
    )


# Database management functions
def create_db_and_tables(connection_string="sqlite:///tax_policy.db"):
    """Create database and tables"""
    engine = create_engine(connection_string)
    SQLModel.metadata.create_all(engine)
    return engine


# Example data creation for UK tax parameter change
def add_uk_sim():
    """Create example data for the UK tax rate change scenario"""
    Path("tax_policy.db").unlink(missing_ok=True)
    engine = create_db_and_tables()

    from policyengine import Simulation

    sim = Simulation(
        country="uk",
        scope="macro",
        subsample=1000,
    )

    person_df = sim.baseline_simulation.calculate_dataframe(
        ["person_id", "age"]
    )
    household_df = sim.baseline_simulation.calculate_dataframe(
        ["household_id", "household_net_income"]
    )

    with Session(engine) as session:
        # Create countries
        uk = Country(code="uk", name="United Kingdom")
        us = Country(code="us", name="United States")
        session.add(uk)
        session.add(us)
        session.commit()

        # Create dataset and series
        dataset_series = DatasetSeries(
            name="Enhanced FRS", description="Enhanced Family Resources Survey"
        )
        session.add(dataset_series)

        dataset = Dataset(
            name="EFRS 2022",
            description="Enhanced Family Resources Survey 2022",
        )
        session.add(dataset)
        session.commit()

        # Tag dataset
        dataset_tag = Dataset(
            id=1,  # Doesn't seem to work without this
            dataset=dataset,
            dataset_series=dataset_series,
            version="2025.1",
        )
        session.add(dataset_tag)
        session.commit()

        # Add simulation run

        sim_run = Simulation(
            country=uk,
            reform=None,
            package_version="1.0.0",
            dataset=dataset,
            run_date=datetime.utcnow(),
        )
        session.add(sim_run)
        session.commit()

        # Create variables
        variable_names = list(person_df.columns) + list(household_df.columns)
        for variable_name in variable_names:
            variable = Variable(
                country=uk,
                name=variable_name,
                description=f"Variable {variable_name} for UK tax simulation",
            )
            session.add(variable)
        session.commit()

        # Create all person entities
        for i in range(len(person_df)):
            person = Entity(
                country=uk,
                entity_type="person",
                dataset_tag_id=dataset_tag.id,
            )
            session.add(person)
            for variable_name in list(person_df.columns):
                # Get the variable object by name
                variable = session.exec(
                    select(Variable)
                    .where(Variable.name == variable_name)
                    .where(Variable.country_id == uk.id)
                ).one()
                variable_state = VariableState(
                    variable=variable,
                    entity=person,
                    time_period="2025",
                    value=str(
                        person_df[variable_name].iloc[i]
                    ),  # Convert to string as value is expected to be str
                    simulation_run=sim_run,
                )
                session.add(variable_state)
        session.commit()

        # Create all household entities
        for i in range(len(household_df)):
            household = Entity(
                country=uk,
                entity_type="household",
                dataset_tag_id=dataset_tag.id,
            )
            session.add(household)
            for variable_name in list(household_df.columns):
                # Get the variable object by name
                variable = session.exec(
                    select(Variable)
                    .where(Variable.name == variable_name)
                    .where(Variable.country_id == uk.id)
                ).one()
                variable_state = VariableState(
                    variable=variable,
                    entity=household,
                    time_period="2025",
                    value=household_df[variable_name].iloc[i],
                )
                session.add(variable_state)
        session.commit()

        print("Successfully created example data for UK tax parameter change.")


if __name__ == "__main__":
    add_uk_sim()
