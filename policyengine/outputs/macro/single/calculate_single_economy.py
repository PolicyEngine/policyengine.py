"""Calculate comparison statistics between two economic scenarios."""

import typing

from policyengine import Simulation

from pydantic import BaseModel
from typing import List

from policyengine_core.simulations import Microsimulation
from typing import Dict
from dataclasses import dataclass
from typing import Literal
from microdf import MicroSeries
from sqlmodel import create_engine, Session, insert
from policyengine.entities import Variable, VariableState


class SingleEconomy(BaseModel):
    total_net_income: float
    employment_income_hh: List[float]
    self_employment_income_hh: List[float]
    total_tax: float
    total_state_tax: float
    total_benefits: float
    household_net_income: List[float]
    equiv_household_net_income: List[float]
    household_income_decile: List[int]
    household_market_income: List[float]
    household_wealth_decile: List[int] | None
    household_wealth: List[float] | None
    in_poverty: List[bool]
    person_in_poverty: List[bool]
    person_in_deep_poverty: List[bool]
    poverty_gap: float
    deep_poverty_gap: float
    person_weight: List[float]
    household_weight: List[float]
    household_count_people: List[int]
    gini: float
    top_10_percent_share: float
    top_1_percent_share: float
    is_male: List[bool]
    race: List[str] | None
    age: List[int]
    substitution_lsr: float
    income_lsr: float
    budgetary_impact_lsr: float
    income_lsr_hh: List[float]
    substitution_lsr_hh: List[float]
    weekly_hours: float | None
    weekly_hours_income_effect: float | None
    weekly_hours_substitution_effect: float | None
    type: Literal["general", "cliff"]
    programs: Dict[str, float] | None
    cliff_gap: float | None = None
    cliff_share: float | None = None


@dataclass
class UKProgram:
    name: str
    is_positive: bool


class UKPrograms:
    PROGRAMS = [
        UKProgram("income_tax", True),
        UKProgram("national_insurance", True),
        UKProgram("vat", True),
        UKProgram("council_tax", True),
        UKProgram("fuel_duty", True),
        UKProgram("tax_credits", False),
        UKProgram("universal_credit", False),
        UKProgram("child_benefit", False),
        UKProgram("state_pension", False),
        UKProgram("pension_credit", False),
        UKProgram("ni_employer", True),
    ]


class GeneralEconomyTask:
    def __init__(self, simulation: Microsimulation, country_id: str):
        self._total_var_write_time = 0
        self.simulation = simulation
        self.country_id = country_id
        self.household_count_people = self.simulation.calculate(
            "household_count_people"
        )
        self._write_var_to_db(
            "household_count_people", self.household_count_people, "blob_sql"
        )

    def _connect_db(self, connection_string: str = "sqlite:///tax_policy.db"):
        """Connect to the database"""

        engine = create_engine(connection_string)
        return engine
    
    def _get_var_id_from_db(
        self, var_name: str
    ) -> int:
        """Retrieve a variable from the database"""
        engine = self._connect_db()
        with Session(engine) as session:
            query = (
                session.query(Variable)
                .filter(
                    Variable.name == var_name,
                )
            )
            variable_id = query.first().id
            if not variable_id:
                raise ValueError(f"Variable '{var_name}' not found in the database.")
        
            return variable_id
        
    def _write_var_to_db(
        self, var_name: str, data: MicroSeries, strategy: Literal["sql", "batched_sql", "blob_sql", "json"] = "sql"
    ) -> None:
        """Write a variable to the database"""
        match strategy:
            case "sql":
                self._write_var_to_db_sql(var_name, data)
            case "batched_sql":
                self._write_var_to_db_batched_sql(var_name, data)
            case "blob_sql":
                self._write_var_to_db_blob_sql(var_name, data)
            case "json":
                self._write_var_to_db_json(var_name, data)
            case _:
                raise ValueError(f"Unknown strategy: {strategy}")
        print(f"Variable '{var_name}' written to database with strategy '{strategy}'")

    def _write_var_to_db_blob_sql(
        self, var_name: str, data: MicroSeries
    ) -> None:
        
        import time
        from sqlmodel import select, SQLModel

        engine = self._connect_db()

        SQLModel.metadata.clear()
        # Dispose the engine to close all connections
        engine.dispose()

        # Recreate the engine
        engine = create_engine("sqlite:///tax_policy_sqlite_blob.db")

        # Recreate all tables with the new schema
        SQLModel.metadata.create_all(engine)

        start_time = time.time()
        with Session(engine) as session:
            statement = select(Variable).where(
                Variable.name == var_name
            )
            variable = session.exec(statement).first()
            if not variable:
                raise ValueError(f"Variable '{var_name}' not found in the database.")
            variable.results = data.to_json().encode("utf-8")
            print(variable.results)
            session.add(variable)
            session.commit()
            session.refresh(variable)
        end_time = time.time()
        total_time = end_time - start_time
        self._total_var_write_time += total_time
        print(
            f"Variable '{var_name}' written to database in {total_time:.2f} seconds"
        )

    def _write_var_to_db_json(
        self, var_name: str, data: MicroSeries
    ) -> None:
        """Write a variable to the database in JSON format"""
        import json
        import time

        start_time = time.time()
        with open(f"{var_name}.json", "w") as f:
            for index, value in enumerate(data):
                # Assuming 'time_period' is a fixed value for simplicity
                time_period = "2025"
                # Create a record in JSON format
                record = {
                    "variable_id": self._get_var_id_from_db(var_name),
                    "entity_id": index,
                    "time_period": time_period,
                    "value": json.dumps(value),
                    "simulation_id": 1
                }

                f.write(json.dumps(record) + "\n")
        end_time = time.time()
        total_time = end_time - start_time
        self._total_var_write_time += total_time
        print(
            f"Variable '{var_name}' written to JSON file in {total_time:.2f} seconds"
        )

    def _write_var_to_db_batched_sql(
        self, var_name: str, data: MicroSeries, batch_size: int = 1000 
    ) -> None:
        """Write a variable to the database in batches"""
        import time

        start_time = time.time()
        engine = self._connect_db()
        with Session(engine) as session:
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                records = []
                for index, value in enumerate(batch):
                    # Assuming 'time_period' is a fixed value for simplicity
                    time_period = "2025"

                    record = {
                        "variable_id": self._get_var_id_from_db(var_name),
                        "entity_id": index + i,
                        "time_period": time_period,
                        "value": str(value),
                        "simulation_id": 1
                    }
                    records.append(record)
                session.execute(
                    insert(VariableState).values(records)
                )
            session.commit()
        end_time = time.time()
        total_time = end_time - start_time
        self._total_var_write_time += total_time
        print(
            f"Variable '{var_name}' written to database in {total_time:.2f} seconds"
        )

    def _write_var_to_db_sql(
        self, var_name: str, data: MicroSeries
    ) -> None:
        import time

        start_time = time.time()
        engine = self._connect_db()
        with Session(engine) as session:
            for index, value in enumerate(data):
                # Assuming 'time_period' is a fixed value for simplicity
                time_period = "2025"
                record = VariableState(
                    variable_id=self._get_var_id_from_db(var_name),
                    entity_id=index,
                    time_period=time_period,
                    value=str(value),
                    simulation_id=1
                )
                session.add(record)
            session.commit()
        end_time = time.time()
        total_time = end_time - start_time
        self._total_var_write_time += total_time
        print(
            f"Variable '{var_name}' written to database in {total_time:.2f} seconds"
        )
    
    def calculate_tax_and_spending(self):
        if self.country_id == "uk":
            total_tax_raw = self.simulation.calculate("gov_tax")
            total_tax = total_tax_raw.sum()
            total_spending_raw = self.simulation.calculate("gov_spending")
            total_spending = total_spending_raw.sum()
            self._write_var_to_db("gov_tax", total_tax_raw, "blob_sql")
            self._write_var_to_db("gov_spending", total_spending_raw, "blob_sql")
        else:
            total_tax_raw = self.simulation.calculate("household_tax")
            total_tax = total_tax_raw.sum()
            self._write_var_to_db("household_tax", total_tax_raw, "blob_sql")
            total_spending_raw = self.simulation.calculate(
                "household_benefits"
            )
            total_spending = total_spending_raw.sum()
            self._write_var_to_db("household_benefits", total_spending_raw, "blob_sql")
        return total_tax, total_spending

    def calculate_inequality_metrics(self):
        personal_hh_equiv_income = self._get_weighted_household_income()

        try:
            gini = personal_hh_equiv_income.gini()
        except Exception as e:
            print(
                "WARNING: Gini index calculations resulted in an error: returning no change, but this is inaccurate."
            )
            print("Error: ", e)
            gini = 0.4

        in_top_10_pct = personal_hh_equiv_income.decile_rank() == 10
        in_top_1_pct = personal_hh_equiv_income.percentile_rank() == 100

        personal_hh_equiv_income.weights /= self.household_count_people

        top_10_share = (
            personal_hh_equiv_income[in_top_10_pct].sum()
            / personal_hh_equiv_income.sum()
        )
        top_1_share = (
            personal_hh_equiv_income[in_top_1_pct].sum()
            / personal_hh_equiv_income.sum()
        )

        return gini, top_10_share, top_1_share

    def _get_weighted_household_income(self):
        income = self.simulation.calculate("equiv_household_net_income")
        self._write_var_to_db(
            "equiv_household_net_income", income, "blob_sql"
        )
        income[income < 0] = 0
        income.weights *= self.household_count_people
        return income

    def calculate_income_breakdown_metrics(self):
        total_net_income_raw = self.simulation.calculate(
            "household_net_income"
        )
        total_net_income = total_net_income_raw.sum()
        self._write_var_to_db("household_net_income", total_net_income_raw, "blob_sql")
        employment_income_hh = (
            self.simulation.calculate("employment_income", map_to="household")
            .astype(float)
            .tolist()
        )
        self_employment_income_hh = (
            self.simulation.calculate(
                "self_employment_income", map_to="household"
            )
            .astype(float)
            .tolist()
        )
        self._write_var_to_db(
            "employment_income_hh", employment_income_hh, "blob_sql"
        )
        self._write_var_to_db(
            "self_employment_income_hh", self_employment_income_hh, "blob_sql"
        )

        return (
            total_net_income,
            employment_income_hh,
            self_employment_income_hh,
        )

    def calculate_household_income_metrics(self):
        household_net_income = (
            self.simulation.calculate("household_net_income")
            .astype(float)
            .tolist()
        )
        equiv_household_net_income = (
            self.simulation.calculate("equiv_household_net_income")
            .astype(float)
            .tolist()
        )
        household_income_decile = (
            self.simulation.calculate("household_income_decile")
            .astype(int)
            .tolist()
        )
        household_market_income = (
            self.simulation.calculate("household_market_income")
            .astype(float)
            .tolist()
        )
        self._write_var_to_db(
            "household_net_income", household_net_income, "blob_sql"
        )
        self._write_var_to_db(
            "equiv_household_net_income", equiv_household_net_income, "blob_sql"
        )
        self._write_var_to_db(
            "household_income_decile", household_income_decile, "blob_sql"
        )
        self._write_var_to_db(
            "household_market_income", household_market_income, "blob_sql"
        )

        return (
            household_net_income,
            equiv_household_net_income,
            household_income_decile,
            household_market_income,
        )

    def calculate_wealth_metrics(self):
        try:
            wealth = self.simulation.calculate("total_wealth")
            self._write_var_to_db("total_wealth", wealth, "blob_sql")

            wealth.weights *= self.household_count_people
            wealth_decile = (
                wealth.decile_rank().clip(1, 10).astype(int).tolist()
            )
            wealth = wealth.astype(float).tolist()
        except Exception as e:
            wealth = None
            wealth_decile = None
        return wealth, wealth_decile

    def calculate_demographic_metrics(self):
        try:
            is_male = (
                self.simulation.calculate("is_male").astype(bool).tolist()
            )
            self._write_var_to_db(
                "is_male", is_male, "blob_sql"
            )
        except Exception:
            is_male = None

        try:
            race = self.simulation.calculate("race").astype(str).tolist()
            self._write_var_to_db(
                "race", race, "blob_sql"
            )
        except Exception:
            race = None

        age = self.simulation.calculate("age").astype(int).tolist()
        self._write_var_to_db("age", age, "blob_sql")

        return is_male, race, age

    def calculate_poverty_metrics(self):
        in_poverty = (
            self.simulation.calculate("in_poverty").astype(bool).tolist()
        )
        person_in_poverty = (
            self.simulation.calculate("in_poverty", map_to="person")
            .astype(bool)
            .tolist()
        )
        person_in_deep_poverty = (
            self.simulation.calculate("in_deep_poverty", map_to="person")
            .astype(bool)
            .tolist()
        )
        poverty_gap_raw = self.simulation.calculate("poverty_gap")
        poverty_gap = poverty_gap_raw.sum()
        deep_poverty_gap_raw = self.simulation.calculate("deep_poverty_gap")
        deep_poverty_gap = deep_poverty_gap_raw.sum()
        self._write_var_to_db("in_poverty", in_poverty, "blob_sql")
        self._write_var_to_db("in_deep_poverty", person_in_deep_poverty, "blob_sql")
        self._write_var_to_db("poverty_gap", poverty_gap_raw, "blob_sql")
        self._write_var_to_db("deep_poverty_gap", deep_poverty_gap_raw, "blob_sql")
        return (
            in_poverty,
            person_in_poverty,
            person_in_deep_poverty,
            poverty_gap,
            deep_poverty_gap,
        )

    def calculate_weights(self):
        person_weight = (
            self.simulation.calculate("person_weight").astype(float).tolist()
        )
        household_weight = (
            self.simulation.calculate("household_weight")
            .astype(float)
            .tolist()
        )
        self._write_var_to_db("person_weight", person_weight, "blob_sql")
        self._write_var_to_db("household_weight", household_weight, "blob_sql")

        return person_weight, household_weight

    def calculate_labor_supply_responses(self):
        result = {
            "substitution_lsr": 0,
            "income_lsr": 0,
            "budgetary_impact_lsr": 0,
            "income_lsr_hh": (self.household_count_people * 0)
            .astype(float)
            .tolist(),
            "substitution_lsr_hh": (self.household_count_people * 0)
            .astype(float)
            .tolist(),
        }

        if not self._has_behavioral_response():
            return result

        result.update(
            {
                "substitution_lsr": self.simulation.calculate(
                    "substitution_elasticity_lsr"
                ).sum(),
                "income_lsr": self.simulation.calculate(
                    "income_elasticity_lsr"
                ).sum(),
                "income_lsr_hh": self.simulation.calculate(
                    "income_elasticity_lsr", map_to="household"
                )
                .astype(float)
                .tolist(),
                "substitution_lsr_hh": self.simulation.calculate(
                    "substitution_elasticity_lsr", map_to="household"
                )
                .astype(float)
                .tolist(),
            }
        )

        return result

    def _has_behavioral_response(self) -> bool:
        return (
            "employment_income_behavioral_response"
            in self.simulation.tax_benefit_system.variables
            and any(
                self.simulation.calculate(
                    "employment_income_behavioral_response"
                )
                != 0
            )
        )

    def calculate_lsr_working_hours(self):
        if self.country_id != "us":
            return {
                "weekly_hours": 0,
                "weekly_hours_income_effect": 0,
                "weekly_hours_substitution_effect": 0,
            }

        return {
            "weekly_hours": self.simulation.calculate(
                "weekly_hours_worked"
            ).sum(),
            "weekly_hours_income_effect": self.simulation.calculate(
                "weekly_hours_worked_behavioural_response_income_elasticity"
            ).sum(),
            "weekly_hours_substitution_effect": self.simulation.calculate(
                "weekly_hours_worked_behavioural_response_substitution_elasticity"
            ).sum(),
        }

    def calculate_uk_programs(self) -> Dict[str, float]:
        if self.country_id != "uk":
            return {}

        return {
            program.name: self.simulation.calculate(
                program.name, map_to="household"
            ).sum()
            * (1 if program.is_positive else -1)
            for program in UKPrograms.PROGRAMS
        }

    def calculate_cliffs(self):
        cliff_gap: MicroSeries = self.simulation.calculate("cliff_gap")
        is_on_cliff: MicroSeries = self.simulation.calculate("is_on_cliff")
        total_cliff_gap: float = cliff_gap.sum()
        total_adults: float = self.simulation.calculate("is_adult").sum()
        cliff_share: float = is_on_cliff.sum() / total_adults
        return CliffImpactInSimulation(
            cliff_gap=total_cliff_gap,
            cliff_share=cliff_share,
        )


class CliffImpactInSimulation(BaseModel):
    cliff_gap: float
    cliff_share: float


def calculate_single_economy(
    simulation: Simulation, reform: bool = False
) -> Dict:
    include_cliffs = simulation.options.include_cliffs
    task_manager = GeneralEconomyTask(
        (
            simulation.baseline_simulation
            if not reform
            else simulation.reform_simulation
        ),
        simulation.options.country,
    )
    country_id = simulation.options.country

    total_tax, total_spending = task_manager.calculate_tax_and_spending()
    gini, top_10_share, top_1_share = (
        task_manager.calculate_inequality_metrics()
    )
    wealth, wealth_decile = task_manager.calculate_wealth_metrics()
    is_male, race, age = task_manager.calculate_demographic_metrics()
    labor_supply_responses = task_manager.calculate_labor_supply_responses()
    lsr_working_hours = task_manager.calculate_lsr_working_hours()
    (
        in_poverty,
        person_in_poverty,
        person_in_deep_poverty,
        poverty_gap,
        deep_poverty_gap,
    ) = task_manager.calculate_poverty_metrics()
    total_net_income, employment_income_hh, self_employment_income_hh = (
        task_manager.calculate_income_breakdown_metrics()
    )
    (
        household_net_income,
        equiv_household_net_income,
        household_income_decile,
        household_market_income,
    ) = task_manager.calculate_household_income_metrics()
    person_weight, household_weight = task_manager.calculate_weights()

    if country_id == "uk":
        uk_programs = task_manager.calculate_uk_programs()
    else:
        uk_programs = None

    total_state_tax = 0

    if country_id == "us":
        try:
            total_state_tax = task_manager.simulation.calculate(
                "household_state_income_tax"
            ).sum()
        except:
            total_state_tax = 0

    if include_cliffs:
        cliffs = task_manager.calculate_cliffs()
        cliff_gap = cliffs.cliff_gap
        cliff_share = cliffs.cliff_share
    else:
        cliff_gap = None
        cliff_share = None

    return SingleEconomy(
        **{
            "total_net_income": total_net_income,
            "employment_income_hh": employment_income_hh,
            "self_employment_income_hh": self_employment_income_hh,
            "total_tax": total_tax,
            "total_state_tax": total_state_tax,
            "total_benefits": total_spending,
            "household_net_income": household_net_income,
            "equiv_household_net_income": equiv_household_net_income,
            "household_income_decile": household_income_decile,
            "household_market_income": household_market_income,
            "household_wealth_decile": wealth_decile,
            "household_wealth": wealth,
            "in_poverty": in_poverty,
            "person_in_poverty": person_in_poverty,
            "person_in_deep_poverty": person_in_deep_poverty,
            "poverty_gap": poverty_gap,
            "deep_poverty_gap": deep_poverty_gap,
            "person_weight": person_weight,
            "household_weight": household_weight,
            "household_count_people": task_manager.household_count_people.astype(
                int
            ).tolist(),
            "gini": float(gini),
            "top_10_percent_share": float(top_10_share),
            "top_1_percent_share": float(top_1_share),
            "is_male": is_male,
            "race": race,
            "age": age,
            **labor_supply_responses,
            **lsr_working_hours,
            "type": "general" if not include_cliffs else "cliff",
            "programs": uk_programs,
            "cliff_gap": cliff_gap if include_cliffs else None,
            "cliff_share": cliff_share if include_cliffs else None,
        }
    )
