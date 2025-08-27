"""Example showing how to use the refactored PolicyEngine architecture.

This demonstrates the separation between:
1. Pure data models (Pydantic)
2. Calculation functions that work with pure models
3. SimulationOrchestrator models (SQLAlchemy)
4. Adapter layer for conversion
"""

import pandas as pd
from src.policyengine.data_models import (
    SimulationDataModel,
    ReportMetadataModel,
)
from src.policyengine.calculations import (
    calculate_economic_impacts,
    calculate_decile_impacts,
    calculate_inequality_impacts,
)
from src.policyengine.countries.uk.model_output import UKModelOutput
from src.policyengine.countries.us.model_output import USModelOutput


def example_pure_calculations_uk():
    """Example of UK calculations without any database dependency."""
    print("=" * 60)
    print("UK EXAMPLE - Pure Calculations (No SimulationOrchestrator)")
    print("=" * 60)
    
    # Create sample UK household data
    uk_household = pd.DataFrame({
        "household_net_income": [25000, 35000, 45000, 55000, 75000, 95000],
        "household_weight": [1000, 1200, 1100, 900, 800, 600],
        "household_count_people": [2, 3, 2, 4, 3, 2],
        "household_tax": [3000, 5000, 8000, 11000, 16000, 22000],
        "household_benefits": [3000, 2000, 1000, 500, 200, 100],
        "gov_balance": [0, 2000, 7000, 10500, 15800, 21900],
    })
    
    uk_person = pd.DataFrame({
        "person_weight": [1000] * 6 + [1200] * 9 + [1100] * 6 + [900] * 12 + [800] * 9 + [600] * 6,
        "age": list(range(48)),  # Various ages
        "is_male": [i % 2 for i in range(48)],  # Alternating gender
        "in_poverty": [1] * 6 + [1] * 3 + [0] * 39,  # Some in poverty
    })
    
    # Create baseline
    baseline = UKModelOutput(
        person=uk_person,
        household=uk_household,
        benefit_unit=pd.DataFrame(),
    )
    
    # Create reform scenario with tax reduction
    reform_household = uk_household.copy()
    reform_household["household_tax"] *= 0.9  # 10% tax reduction
    reform_household["household_net_income"] = (
        reform_household["household_net_income"] + 
        (uk_household["household_tax"] - reform_household["household_tax"])
    )
    reform_household["gov_balance"] = (
        reform_household["household_tax"] - reform_household["household_benefits"]
    )
    
    reform_person = uk_person.copy()
    reform_person["in_poverty"][:9] = 0  # Some lifted out of poverty
    
    reform = UKModelOutput(
        person=reform_person,
        household=reform_household,
        benefit_unit=pd.DataFrame(),
    )
    
    # Calculate impacts using pure functions
    print("\n1. Calculating decile impacts...")
    decile_impacts = calculate_decile_impacts(baseline, reform)
    for impact in decile_impacts[:3]:  # Show first 3 deciles
        print(f"   Decile {impact.decile}: {impact.relative_change:.2%} change, "
              f"£{impact.average_change:,.0f} average")
    
    print("\n2. Calculating inequality impacts...")
    inequality = calculate_inequality_impacts(baseline, reform)
    print(f"   Gini coefficient: {inequality.gini_baseline:.3f} → {inequality.gini_reform:.3f}")
    print(f"   Top 10% share: {inequality.top_10_percent_share_baseline:.1%} → "
          f"{inequality.top_10_percent_share_reform:.1%}")
    
    print("\n3. Calculating complete economic impact...")
    report_metadata = ReportMetadataModel(
        name="UK Tax Reform Analysis",
        country="uk",
        baseline_simulation_id="baseline_sim",
        comparison_simulation_id="reform_sim",
    )
    
    full_impact = calculate_economic_impacts(baseline, reform, report_metadata)
    
    print(f"\n   Budget impact: £{full_impact.budget_impact.gov_balance_change:,.0f}")
    print(f"   Households better off: "
          f"{sum(1 for d in full_impact.decile_impacts if d.relative_change > 0)}/10 deciles")
    
    return full_impact


def example_pure_calculations_us():
    """Example of US calculations without any database dependency."""
    print("\n" + "=" * 60)
    print("US EXAMPLE - Pure Calculations (No SimulationOrchestrator)")
    print("=" * 60)
    
    # Create sample US household data
    us_household = pd.DataFrame({
        "household_net_income": [30000, 45000, 60000, 80000, 120000, 200000],
        "household_weight": [1500, 1300, 1200, 1000, 700, 400],
        "household_count_people": [2, 3, 3, 4, 3, 2],
        "household_tax": [3500, 6000, 10000, 16000, 28000, 55000],
        "household_benefits": [4000, 2500, 1500, 800, 300, 100],
        "household_state_tax": [800, 1200, 1800, 2500, 4000, 7000],
    })
    
    us_person = pd.DataFrame({
        "person_weight": [1500] * 6 + [1300] * 9 + [1200] * 9 + [1000] * 12 + [700] * 9 + [400] * 6,
        "age": list(range(51)),  # Various ages
        "is_male": [i % 2 for i in range(51)],  # Alternating gender
        "in_poverty": [1] * 6 + [1] * 4 + [0] * 41,  # Some in poverty
    })
    
    # Create baseline
    baseline = USModelOutput(
        person=us_person,
        household=us_household,
        # US-specific entities
        tax_unit=pd.DataFrame(),
        spm_unit=pd.DataFrame(),
        family=pd.DataFrame(),
        marital_unit=pd.DataFrame(),
    )
    
    # Create reform scenario with benefit increase
    reform_household = us_household.copy()
    reform_household["household_benefits"] *= 1.2  # 20% benefit increase
    reform_household["household_net_income"] = (
        reform_household["household_net_income"] + 
        (reform_household["household_benefits"] - us_household["household_benefits"])
    )
    
    reform_person = us_person.copy()
    reform_person["in_poverty"][:10] = 0  # All lifted out of poverty
    
    reform = USModelOutput(
        person=reform_person,
        household=reform_household,
        tax_unit=pd.DataFrame(),
        spm_unit=pd.DataFrame(),
        family=pd.DataFrame(),
        marital_unit=pd.DataFrame(),
    )
    
    # Calculate impacts
    print("\n1. Calculating impacts...")
    report_metadata = ReportMetadataModel(
        name="US Benefit Expansion Analysis",
        country="us",
        baseline_simulation_id="baseline_sim",
        comparison_simulation_id="reform_sim",
    )
    
    impact = calculate_economic_impacts(baseline, reform, report_metadata)
    
    print(f"\n   Benefit spending change: ${impact.budget_impact.gov_spending_change:,.0f}")
    print(f"   Average income change: "
          f"${impact.household_income.household_net_income_change / len(us_household):,.0f}")
    
    # Show poverty reduction
    poverty_impacts = impact.poverty_impacts
    for p in poverty_impacts:
        if p.demographic_group == "all":
            print(f"   Poverty rate: {p.rate_baseline:.1%} → {p.rate_reform:.1%} "
                  f"({p.rate_change:+.1%})")
    
    return impact


def example_with_adapters():
    """Example showing how to use adapters for database integration."""
    print("\n" + "=" * 60)
    print("ADAPTER EXAMPLE - Converting Between Models")
    print("=" * 60)
    
    from src.policyengine.adapters import (
        modeloutput_to_simulation_data,
        dataset_orm_to_pydantic,
        scenario_orm_to_pydantic,
    )
    
    # Create a UK model output
    uk_output = UKModelOutput(
        person=pd.DataFrame({"age": [25, 30, 35]}),
        household=pd.DataFrame({"household_net_income": [30000, 40000, 50000]}),
        benefit_unit=pd.DataFrame(),
    )
    
    # Convert to generic SimulationDataModel
    generic_data = modeloutput_to_simulation_data(uk_output)
    print(f"\n1. Converted UKModelOutput to SimulationDataModel")
    print(f"   Available tables: {generic_data.table_names}")
    
    # The generic model can be used with any calculation function
    # This demonstrates the abstraction - calculations don't need to know
    # about specific country implementations
    
    # Create a US model output
    us_output = USModelOutput(
        person=pd.DataFrame({"age": [28, 33, 38]}),
        household=pd.DataFrame({"household_net_income": [35000, 45000, 55000]}),
        tax_unit=pd.DataFrame(),
        spm_unit=pd.DataFrame(),
        family=pd.DataFrame(),
        marital_unit=pd.DataFrame(),
    )
    
    # Convert to generic SimulationDataModel
    generic_data_us = modeloutput_to_simulation_data(us_output)
    print(f"\n2. Converted USModelOutput to SimulationDataModel")
    print(f"   Available tables: {generic_data_us.table_names}")
    
    print("\n3. Both can be used with the same calculation functions!")
    print("   This demonstrates the power of the abstraction layer.")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("REFACTORED POLICYENGINE ARCHITECTURE EXAMPLES")
    print("=" * 60)
    print("\nThe new architecture separates:")
    print("1. Pure data models (Pydantic) - no database dependencies")
    print("2. Calculation functions - work with pure models")
    print("3. SimulationOrchestrator models (SQLAlchemy) - for persistence")
    print("4. Adapters - convert between model types")
    print("\nThis separation allows:")
    print("- Testing calculations without a database")
    print("- Using calculations in different contexts")
    print("- Swapping storage backends easily")
    print("- Better code organization and maintainability")
    
    # Run examples
    uk_impact = example_pure_calculations_uk()
    us_impact = example_pure_calculations_us()
    example_with_adapters()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\n✓ UK calculations completed: {len(uk_impact.decile_impacts)} deciles analyzed")
    print(f"✓ US calculations completed: {len(us_impact.poverty_impacts)} poverty groups analyzed")
    print(f"✓ Adapter conversions demonstrated")
    print("\nThe refactored architecture successfully separates concerns!")
    print("Calculations can now be used independently of database implementation.")


if __name__ == "__main__":
    main()