"""Adapters to convert between SQLAlchemy ORM models and Pydantic data models.

This module provides conversion functions to bridge between database models
and pure data models used for calculations.
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from .data_models import (
    SimulationDataModel,
    ParameterChangeModel,
    ScenarioModel,
    DatasetModel,
    SimulationMetadataModel,
    ReportMetadataModel,
    BudgetImpactModel,
    DecileImpactModel,
    PovertyImpactModel,
    InequalityImpactModel,
    EconomicImpactModel,
)

from .database.models import (
    SimulationMetadata,
    DatasetMetadata,
    ScenarioMetadata,
    ParameterChangeMetadata,
    ReportMetadata,
    UKGovernmentBudget,
    UKDecileImpact,
    UKPovertyImpact,
    UKInequalityImpact,
    USGovernmentBudget,
    USDecileImpact,
    USPovertyImpact,
    USInequalityImpact,
)


# Convert FROM SQLAlchemy TO Pydantic

def dataset_orm_to_pydantic(dataset: DatasetMetadata) -> DatasetModel:
    """Convert SQLAlchemy DatasetMetadata to Pydantic DatasetModel."""
    if not dataset:
        return None
    
    return DatasetModel(
        name=dataset.name,
        country=dataset.country,
        year=dataset.year,
        source=dataset.source,
        version=dataset.version,
        description=dataset.description,
        model_version=dataset.model_version,
    )


def parameter_change_orm_to_pydantic(change: ParameterChangeMetadata) -> ParameterChangeModel:
    """Convert SQLAlchemy ParameterChangeMetadata to Pydantic ParameterChangeModel."""
    if not change:
        return None
    
    return ParameterChangeModel(
        parameter_name=change.parameter.name if change.parameter else "",
        start_date=change.start_date,
        end_date=change.end_date,
        value=change.value,
        description=change.description,
        order_index=change.order_index,
    )


def scenario_orm_to_pydantic(scenario: ScenarioMetadata) -> ScenarioModel:
    """Convert SQLAlchemy ScenarioMetadata to Pydantic ScenarioModel."""
    if not scenario:
        return None
    
    return ScenarioModel(
        name=scenario.name,
        country=scenario.country,
        description=scenario.description,
        parameter_changes=[
            parameter_change_orm_to_pydantic(change)
            for change in scenario.parameter_changes
        ],
        parent_scenario_name=scenario.parent_scenario.name if scenario.parent_scenario else None,
        model_version=scenario.model_version,
    )


def simulation_metadata_orm_to_pydantic(sim: SimulationMetadata) -> SimulationMetadataModel:
    """Convert SQLAlchemy SimulationMetadata to Pydantic SimulationMetadataModel."""
    if not sim:
        return None
    
    return SimulationMetadataModel(
        id=sim.id,
        country=sim.country,
        year=sim.year,
        dataset=dataset_orm_to_pydantic(sim.dataset),
        scenario=scenario_orm_to_pydantic(sim.scenario),
        model_version=sim.model_version,
        status=sim.status.value if hasattr(sim.status, 'value') else sim.status,
        description=sim.description,
        tags=sim.tags or [],
    )


def report_metadata_orm_to_pydantic(report: ReportMetadata) -> ReportMetadataModel:
    """Convert SQLAlchemy ReportMetadata to Pydantic ReportMetadataModel."""
    if not report:
        return None
    
    return ReportMetadataModel(
        id=report.id,
        name=report.name,
        country=report.country,
        year=report.year,
        baseline_simulation_id=report.baseline_simulation_id,
        comparison_simulation_id=report.comparison_simulation_id,
        status=report.status.value if hasattr(report.status, 'value') else report.status,
        description=report.description,
        tags=report.tags or [],
    )


# Convert FROM Pydantic TO SQLAlchemy

def save_budget_impact_to_db(
    session: Session,
    report_id: str,
    impact: BudgetImpactModel,
    country: str
) -> None:
    """Save budget impact results to database.
    
    Args:
        session: SimulationOrchestrator session
        report_id: Report ID to associate with
        impact: Budget impact model with results
        country: Country code ('uk' or 'us')
    """
    if country.lower() == 'uk':
        budget = UKGovernmentBudget(
            report_id=report_id,
            gov_balance_baseline=impact.gov_balance_baseline,
            gov_balance_reform=impact.gov_balance_reform,
            gov_balance_change=impact.gov_balance_change,
            gov_tax_baseline=impact.gov_tax_baseline,
            gov_tax_reform=impact.gov_tax_reform,
            gov_tax_change=impact.gov_tax_change,
            gov_spending_baseline=impact.gov_spending_baseline,
            gov_spending_reform=impact.gov_spending_reform,
            gov_spending_change=impact.gov_spending_change,
        )
        
        # Add specific UK taxes/benefits from additional_metrics
        uk_tax_mapping = {
            "income_tax": "income_tax",
            "national_insurance": "national_insurance",
            "ni_employer": "ni_employer",
            "vat": "vat",
            "capital_gains_tax": "capital_gains_tax",
        }
        
        uk_benefit_mapping = {
            "universal_credit": "universal_credit",
            "state_pension": "state_pension",
            "pip": "pip",
            "dla": "dla",
            "housing_benefit": "housing_benefit",
            "working_tax_credit": "working_tax_credit",
            "child_tax_credit": "child_tax_credit",
        }
        
        for metric_name, attr_name in {**uk_tax_mapping, **uk_benefit_mapping}.items():
            if metric_name in impact.additional_metrics:
                metric = impact.additional_metrics[metric_name]
                setattr(budget, f"{attr_name}_baseline", metric.get("baseline"))
                setattr(budget, f"{attr_name}_reform", metric.get("reform"))
                setattr(budget, f"{attr_name}_change", metric.get("change"))
        
        session.add(budget)
        
    elif country.lower() == 'us':
        budget = USGovernmentBudget(
            report_id=report_id,
            federal_tax_baseline=impact.gov_tax_baseline,
            federal_tax_reform=impact.gov_tax_reform,
            federal_tax_change=impact.gov_tax_change,
            federal_benefits_baseline=impact.gov_spending_baseline,
            federal_benefits_reform=impact.gov_spending_reform,
            federal_benefits_change=impact.gov_spending_change,
        )
        
        # Handle state taxes and benefits from additional_metrics
        if "state_tax" in impact.additional_metrics:
            metric = impact.additional_metrics["state_tax"]
            budget.state_tax_baseline = metric.get("baseline")
            budget.state_tax_reform = metric.get("reform")
            budget.state_tax_change = metric.get("change")
        
        if "state_benefits" in impact.additional_metrics:
            metric = impact.additional_metrics["state_benefits"]
            budget.state_benefits_baseline = metric.get("baseline")
            budget.state_benefits_reform = metric.get("reform")
            budget.state_benefits_change = metric.get("change")
        
        # Calculate totals
        budget.total_tax_baseline = (budget.federal_tax_baseline or 0) + (budget.state_tax_baseline or 0)
        budget.total_tax_reform = (budget.federal_tax_reform or 0) + (budget.state_tax_reform or 0)
        budget.total_tax_change = (budget.federal_tax_change or 0) + (budget.state_tax_change or 0)
        
        budget.total_benefits_baseline = (budget.federal_benefits_baseline or 0) + (budget.state_benefits_baseline or 0)
        budget.total_benefits_reform = (budget.federal_benefits_reform or 0) + (budget.state_benefits_reform or 0)
        budget.total_benefits_change = (budget.federal_benefits_change or 0) + (budget.state_benefits_change or 0)
        
        budget.net_impact = budget.total_tax_change - budget.total_benefits_change
        
        session.add(budget)


def save_decile_impacts_to_db(
    session: Session,
    report_id: str,
    impacts: List[DecileImpactModel],
    country: str
) -> None:
    """Save decile impact results to database.
    
    Args:
        session: SimulationOrchestrator session
        report_id: Report ID to associate with
        impacts: List of decile impact models
        country: Country code ('uk' or 'us')
    """
    for impact in impacts:
        if country.lower() == 'uk':
            record = UKDecileImpact(
                report_id=report_id,
                decile_type=impact.decile_type,
                decile=impact.decile,
                variable_name="household_net_income",
                mean_change=impact.average_change,
            )
            session.add(record)
            
        elif country.lower() == 'us':
            record = USDecileImpact(
                report_id=report_id,
                decile=impact.decile,
                relative_change=impact.relative_change,
                average_change=impact.average_change,
            )
            session.add(record)


def save_poverty_impacts_to_db(
    session: Session,
    report_id: str,
    impacts: List[PovertyImpactModel],
    country: str
) -> None:
    """Save poverty impact results to database.
    
    Args:
        session: SimulationOrchestrator session
        report_id: Report ID to associate with
        impacts: List of poverty impact models
        country: Country code ('uk' or 'us')
    """
    for impact in impacts:
        if country.lower() == 'uk':
            # Map poverty types to UK definitions
            if impact.poverty_type == "poverty":
                poverty_type = "relative_ahc"  # Default UK poverty measure
            else:
                poverty_type = impact.poverty_type
            
            record = UKPovertyImpact(
                report_id=report_id,
                poverty_type=poverty_type,
                demographic_group=impact.demographic_group,
                headcount_baseline=impact.headcount_baseline,
                headcount_reform=impact.headcount_reform,
                headcount_change=impact.headcount_change,
                rate_baseline=impact.rate_baseline,
                rate_reform=impact.rate_reform,
                rate_change=impact.rate_change,
            )
            session.add(record)
            
        elif country.lower() == 'us':
            # Map poverty types to US definitions
            if impact.poverty_type == "poverty":
                poverty_type = "spm"  # Default US poverty measure
            else:
                poverty_type = impact.poverty_type
            
            record = USPovertyImpact(
                report_id=report_id,
                poverty_type=poverty_type,
                demographic_group=impact.demographic_group,
                headcount_baseline=impact.headcount_baseline,
                headcount_reform=impact.headcount_reform,
                headcount_change=impact.headcount_change,
                rate_baseline=impact.rate_baseline,
                rate_reform=impact.rate_reform,
                rate_change=impact.rate_change,
                gap_baseline=impact.gap_baseline,
                gap_reform=impact.gap_reform,
                gap_change=impact.gap_change,
            )
            session.add(record)


def save_inequality_impact_to_db(
    session: Session,
    report_id: str,
    impact: InequalityImpactModel,
    country: str
) -> None:
    """Save inequality impact results to database.
    
    Args:
        session: SimulationOrchestrator session
        report_id: Report ID to associate with
        impact: Inequality impact model
        country: Country code ('uk' or 'us')
    """
    if country.lower() == 'uk':
        record = UKInequalityImpact(
            report_id=report_id,
            gini_baseline=impact.gini_baseline,
            gini_reform=impact.gini_reform,
            gini_change=impact.gini_change,
            top_10_percent_share_baseline=impact.top_10_percent_share_baseline,
            top_10_percent_share_reform=impact.top_10_percent_share_reform,
            top_10_percent_share_change=impact.top_10_percent_share_change,
            top_1_percent_share_baseline=impact.top_1_percent_share_baseline,
            top_1_percent_share_reform=impact.top_1_percent_share_reform,
            top_1_percent_share_change=impact.top_1_percent_share_change,
        )
        session.add(record)
        
    elif country.lower() == 'us':
        record = USInequalityImpact(
            report_id=report_id,
            gini_baseline=impact.gini_baseline,
            gini_reform=impact.gini_reform,
            gini_change=impact.gini_change,
            top_10_percent_share_baseline=impact.top_10_percent_share_baseline,
            top_10_percent_share_reform=impact.top_10_percent_share_reform,
            top_10_percent_share_change=impact.top_10_percent_share_change,
            top_1_percent_share_baseline=impact.top_1_percent_share_baseline,
            top_1_percent_share_reform=impact.top_1_percent_share_reform,
            top_1_percent_share_change=impact.top_1_percent_share_change,
            bottom_50_percent_share_baseline=impact.bottom_50_percent_share_baseline,
            bottom_50_percent_share_reform=impact.bottom_50_percent_share_reform,
            bottom_50_percent_share_change=impact.bottom_50_percent_share_change,
        )
        session.add(record)


def save_economic_impact_to_db(
    session: Session,
    impact: EconomicImpactModel
) -> None:
    """Save complete economic impact results to database.
    
    Args:
        session: SimulationOrchestrator session
        impact: Complete economic impact model with all results
    """
    report_id = impact.report_metadata.id
    country = impact.report_metadata.country
    
    # Save each component
    if impact.budget_impact:
        save_budget_impact_to_db(session, report_id, impact.budget_impact, country)
    
    if impact.decile_impacts:
        save_decile_impacts_to_db(session, report_id, impact.decile_impacts, country)
    
    if impact.poverty_impacts:
        save_poverty_impacts_to_db(session, report_id, impact.poverty_impacts, country)
    
    if impact.inequality_impact:
        save_inequality_impact_to_db(session, report_id, impact.inequality_impact, country)
    
    # Commit all changes
    session.commit()


# Convert ModelOutput objects to SimulationDataModel

def modeloutput_to_simulation_data(model_output) -> SimulationDataModel:
    """Convert a ModelOutput (UK or US) to SimulationDataModel.
    
    Args:
        model_output: UKModelOutput or USModelOutput instance
        
    Returns:
        SimulationDataModel with the same data
    """
    # Get the tables from the ModelOutput
    tables = {}
    
    # Required fields
    if hasattr(model_output, 'person'):
        tables['person'] = model_output.person
    if hasattr(model_output, 'household'):
        tables['household'] = model_output.household
    
    # Optional fields
    optional_fields = ['marital_unit', 'family', 'tax_unit', 'spm_unit', 'benefit_unit']
    for field in optional_fields:
        if hasattr(model_output, field):
            value = getattr(model_output, field)
            if value is not None:
                tables[field] = value
    
    return SimulationDataModel(**tables)