"""Example of creating a custom report item for PolicyEngine.

This example shows how to create a custom poverty gap metric that
can be computed and stored in the database alongside built-in metrics.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

import pandas as pd
from pydantic import BaseModel
from sqlalchemy import JSON
from sqlmodel import SQLModel, Field

from policyengine.models.report_items import ReportElementDataItem
from policyengine.models.simulation import Simulation
from policyengine.models.single_year_dataset import SingleYearDataset


# Define the SQLModel table for storing poverty gap data
class PovertyGapTable(SQLModel, table=True):
    __tablename__ = "reportitem_poverty_gap"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    simulation_id: UUID = Field(foreign_key="simulations.id")
    time_period: str | None = None
    country: str
    poverty_line: float
    income_variable: str
    entity_level: str = "person"
    
    # Results
    poverty_gap_index: float
    average_gap: float
    total_gap: float
    people_in_poverty: float


# Define the mapper functions (optional, but recommended for complex conversions)
def poverty_gap_to_table(
    item: "PovertyGap",
    session,  # SQLAlchemy session
    cascade: bool = False,
) -> PovertyGapTable:
    """Convert PovertyGap model to database table."""
    # Get simulation ID (assuming it's already in the database)
    from policyengine.database import Database
    
    # We need to ensure the simulation is stored first
    if hasattr(item.simulation, 'id') and item.simulation.id:
        sim_id = item.simulation.id
    else:
        # This would need proper handling in a real implementation
        raise ValueError("Simulation must be saved to database first")
    
    return PovertyGapTable(
        simulation_id=sim_id,
        time_period=str(item.time_period) if item.time_period else None,
        country=item.country,
        poverty_line=item.poverty_line,
        income_variable=item.income_variable,
        entity_level=item.entity_level,
        poverty_gap_index=item.poverty_gap_index,
        average_gap=item.average_gap,
        total_gap=item.total_gap,
        people_in_poverty=item.people_in_poverty,
    )


def poverty_gap_from_table(
    row: PovertyGapTable,
    session,
    cascade: bool = False,
) -> "PovertyGap":
    """Convert database table to PovertyGap model."""
    from policyengine.tables.simulation import SimulationTable
    
    # Fetch the simulation if needed
    sim = None
    if cascade and row.simulation_id:
        sim_row = session.get(SimulationTable, row.simulation_id)
        if sim_row:
            # Convert to Simulation model (simplified)
            sim = Simulation(id=sim_row.id)
    
    return PovertyGap(
        simulation=sim,
        time_period=row.time_period,
        country=row.country,
        poverty_line=row.poverty_line,
        income_variable=row.income_variable,
        entity_level=row.entity_level,
        poverty_gap_index=row.poverty_gap_index,
        average_gap=row.average_gap,
        total_gap=row.total_gap,
        people_in_poverty=row.people_in_poverty,
    )


# Define the Pydantic model
class PovertyGap(ReportElementDataItem):
    """Custom report item for calculating poverty gap metrics.
    
    The poverty gap measures how far below the poverty line
    the poor population falls on average.
    """
    
    simulation: Simulation
    time_period: int | str | None = None
    country: str
    poverty_line: float
    income_variable: str = "household_net_income"
    entity_level: str = "person"
    
    # Results (computed by run method)
    poverty_gap_index: float | None = None
    average_gap: float | None = None
    total_gap: float | None = None
    people_in_poverty: float | None = None
    
    @staticmethod
    def run(items: list["PovertyGap"]) -> list["PovertyGap"]:
        """Compute poverty gap metrics for provided items.
        
        This method calculates:
        - Poverty gap index: average shortfall as % of poverty line
        - Average gap: average income shortfall for those in poverty
        - Total gap: sum of all income shortfalls
        - People in poverty: weighted count below poverty line
        """
        if not items:
            return []
        
        results = []
        for item in items:
            # Get the simulation result data
            data: SingleYearDataset = item.simulation.result.data
            
            # Get the relevant entity table
            table: pd.DataFrame = data.tables[item.entity_level]
            
            # Get income and weights
            income = table[item.income_variable].values
            weights = table.get("weight_value", pd.Series(1, index=table.index)).values
            
            # Calculate poverty metrics
            in_poverty = income < item.poverty_line
            gap = (item.poverty_line - income) * in_poverty
            
            # Weighted calculations
            people_in_poverty = float((weights * in_poverty).sum())
            total_gap = float((weights * gap).sum())
            total_people = float(weights.sum())
            
            if people_in_poverty > 0:
                average_gap = total_gap / people_in_poverty
                poverty_gap_index = (total_gap / (item.poverty_line * total_people)) * 100
            else:
                average_gap = 0.0
                poverty_gap_index = 0.0
            
            # Create result with computed values
            result = PovertyGap(
                **item.model_dump(),
                poverty_gap_index=poverty_gap_index,
                average_gap=average_gap,
                total_gap=total_gap,
                people_in_poverty=people_in_poverty,
            )
            results.append(result)
        
        return results


# Example usage
if __name__ == "__main__":
    from policyengine.database import Database
    
    # Create database and register the custom type
    db = Database("sqlite:///example.db")
    
    # Register the custom type with the database
    db.register_custom_mapping(
        model_class=PovertyGap,
        table_class=PovertyGapTable,
        to_table_mapper=poverty_gap_to_table,
        from_table_mapper=poverty_gap_from_table,
    )
    
    # Now you can use PovertyGap just like built-in report items
    print("Custom poverty gap report item registered successfully!")
    
    # Example of creating a poverty gap item (would need real simulation)
    # poverty_gap = PovertyGap(
    #     simulation=my_simulation,
    #     country="uk",
    #     poverty_line=15000,
    #     income_variable="household_net_income",
    # )
    
    # Compute the metrics
    # results = PovertyGap.run([poverty_gap])
    
    # Store in database
    # db.add(results[0])