"""Economic impact calculations using pure data models.

These calculations work with Pydantic models and are independent of database concerns.
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from microdf import MicroSeries

from .data_models import (
    SimulationDataModel,
    BudgetImpactModel,
    HouseholdIncomeImpactModel,
    DecileImpactModel,
    PovertyImpactModel,
    InequalityImpactModel,
    EconomicImpactModel,
    ReportMetadataModel,
)


def calculate_decile_impacts(
    baseline: SimulationDataModel,
    comparison: SimulationDataModel,
    by_wealth: bool = False
) -> List[DecileImpactModel]:
    """Calculate decile impacts with proper weighting.
    
    Args:
        baseline: Baseline simulation data
        comparison: Comparison simulation data
        by_wealth: Whether to group by wealth instead of income
        
    Returns:
        List of DecileImpactModel objects
    """
    # Get household data
    baseline_hh = baseline.household
    comparison_hh = comparison.household
    
    # Get incomes and weights
    baseline_income = MicroSeries(
        baseline_hh["household_net_income"].values,
        weights=baseline_hh.get("household_weight", pd.Series(np.ones(len(baseline_hh)))).values
    )
    comparison_income = MicroSeries(
        comparison_hh["household_net_income"].values,
        weights=baseline_income.weights
    )
    
    # Get people per household for winner/loser calculations
    people_per_hh = baseline_hh.get("household_count_people", pd.Series(np.ones(len(baseline_hh)))).values
    
    # Determine deciles
    if by_wealth and "total_wealth" in baseline_hh.columns:
        wealth = MicroSeries(
            baseline_hh["total_wealth"].values,
            weights=baseline_income.weights * people_per_hh
        )
        decile = wealth.decile_rank().clip(1, 10).astype(int)
        decile_type = "wealth"
    elif "household_income_decile" in baseline_hh.columns:
        decile = baseline_hh["household_income_decile"].values.astype(int)
        decile_type = "income"
    else:
        # Calculate deciles from income
        decile = baseline_income.decile_rank().clip(1, 10).astype(int)
        decile_type = "income"
    
    # Calculate income changes
    absolute_change = (comparison_income - baseline_income).values
    capped_baseline = np.maximum(baseline_income.values, 1)
    capped_comparison = np.maximum(comparison_income.values, 1) 
    relative_change = (capped_comparison - capped_baseline) / capped_baseline
    
    results = []
    
    for d in range(1, 11):
        mask = decile == d
        if not np.any(mask):
            continue
            
        # Calculate average and relative changes
        decile_baseline = baseline_income[mask]
        decile_comparison = comparison_income[mask]
        
        total_baseline = decile_baseline.sum()
        total_comparison = decile_comparison.sum()
        
        if total_baseline != 0:
            rel_change = (total_comparison - total_baseline) / total_baseline
        else:
            rel_change = 0
            
        avg_change = (total_comparison - total_baseline) / decile_baseline.count()
        
        # Calculate winners and losers
        decile_relative_change = relative_change[mask]
        decile_people = people_per_hh[mask]
        total_people = np.sum(decile_people * baseline_income.weights[mask])
        
        if total_people > 0:
            lose_more_5 = np.sum(
                decile_people[decile_relative_change < -0.05] * 
                baseline_income.weights[mask][decile_relative_change < -0.05]
            ) / total_people
            
            lose_less_5 = np.sum(
                decile_people[(decile_relative_change >= -0.05) & (decile_relative_change < -0.01)] *
                baseline_income.weights[mask][(decile_relative_change >= -0.05) & (decile_relative_change < -0.01)]
            ) / total_people
            
            lose_less_1 = np.sum(
                decile_people[(decile_relative_change >= -0.01) & (decile_relative_change < -0.001)] *
                baseline_income.weights[mask][(decile_relative_change >= -0.01) & (decile_relative_change < -0.001)]
            ) / total_people
            
            no_change = np.sum(
                decile_people[(decile_relative_change >= -0.001) & (decile_relative_change <= 0.001)] *
                baseline_income.weights[mask][(decile_relative_change >= -0.001) & (decile_relative_change <= 0.001)]
            ) / total_people
            
            gain_less_1 = np.sum(
                decile_people[(decile_relative_change > 0.001) & (decile_relative_change <= 0.01)] *
                baseline_income.weights[mask][(decile_relative_change > 0.001) & (decile_relative_change <= 0.01)]
            ) / total_people
            
            gain_less_5 = np.sum(
                decile_people[(decile_relative_change > 0.01) & (decile_relative_change <= 0.05)] *
                baseline_income.weights[mask][(decile_relative_change > 0.01) & (decile_relative_change <= 0.05)]
            ) / total_people
            
            gain_more_5 = np.sum(
                decile_people[decile_relative_change > 0.05] *
                baseline_income.weights[mask][decile_relative_change > 0.05]
            ) / total_people
        else:
            lose_more_5 = lose_less_5 = lose_less_1 = no_change = gain_less_1 = gain_less_5 = gain_more_5 = 0
        
        results.append(DecileImpactModel(
            decile=d,
            decile_type=decile_type,
            relative_change=float(rel_change),
            average_change=float(avg_change),
            gain_more_than_5_percent=float(gain_more_5),
            gain_more_than_1_percent=float(gain_less_5 + gain_more_5),  # Cumulative
            no_change=float(no_change),
            lose_less_than_1_percent=float(lose_less_1),
            lose_less_than_5_percent=float(lose_less_5),
            lose_more_than_5_percent=float(lose_more_5),
        ))
    
    return results


def calculate_poverty_impacts(
    baseline: SimulationDataModel,
    comparison: SimulationDataModel
) -> List[PovertyImpactModel]:
    """Calculate poverty impacts by demographic groups.
    
    Args:
        baseline: Baseline simulation data
        comparison: Comparison simulation data
        
    Returns:
        List of PovertyImpactModel objects
    """
    baseline_person = baseline.person
    comparison_person = comparison.person
    
    # Get weights
    person_weights = MicroSeries(
        np.ones(len(baseline_person)),
        weights=baseline_person.get("person_weight", pd.Series(np.ones(len(baseline_person)))).values
    )
    
    # Get poverty status - check if it exists first
    if "person_in_poverty" in baseline_person.columns:
        baseline_poverty = baseline_person["person_in_poverty"].values
        comparison_poverty = comparison_person["person_in_poverty"].values
    elif "in_poverty" in baseline_person.columns:
        baseline_poverty = baseline_person["in_poverty"].values
        comparison_poverty = comparison_person["in_poverty"].values
    else:
        # No poverty data available
        return []
    
    # Deep poverty
    baseline_deep = None
    comparison_deep = None
    if "person_in_deep_poverty" in baseline_person.columns:
        baseline_deep = baseline_person["person_in_deep_poverty"].values
        comparison_deep = comparison_person["person_in_deep_poverty"].values
    elif "in_deep_poverty" in baseline_person.columns:
        baseline_deep = baseline_person["in_deep_poverty"].values
        comparison_deep = comparison_person["in_deep_poverty"].values
    
    # Poverty gap if available
    baseline_gap = None
    comparison_gap = None
    if "poverty_gap" in baseline_person.columns:
        baseline_gap = baseline_person["poverty_gap"].values
        comparison_gap = comparison_person["poverty_gap"].values
    
    results = []
    
    # Age groups
    if "age" in baseline_person.columns:
        ages = baseline_person["age"].values
        
        age_groups = [
            ("child", ages < 18),
            ("adult", (ages >= 18) & (ages < 65)),
            ("senior", ages >= 65),
            ("all", np.ones(len(ages), dtype=bool)),
        ]
        
        for group_name, mask in age_groups:
            group_weights = person_weights.weights[mask]
            total_weight = np.sum(group_weights)
            
            if total_weight > 0:
                # Regular poverty
                poverty_count_baseline = np.sum(baseline_poverty[mask] * group_weights)
                poverty_count_reform = np.sum(comparison_poverty[mask] * group_weights)
                poverty_rate_baseline = poverty_count_baseline / total_weight
                poverty_rate_reform = poverty_count_reform / total_weight
                
                results.append(PovertyImpactModel(
                    poverty_type="poverty",
                    demographic_group=group_name,
                    headcount_baseline=float(poverty_count_baseline),
                    headcount_reform=float(poverty_count_reform),
                    headcount_change=float(poverty_count_reform - poverty_count_baseline),
                    rate_baseline=float(poverty_rate_baseline),
                    rate_reform=float(poverty_rate_reform),
                    rate_change=float(poverty_rate_reform - poverty_rate_baseline),
                    gap_baseline=float(np.sum(baseline_gap[mask] * group_weights)) if baseline_gap is not None else None,
                    gap_reform=float(np.sum(comparison_gap[mask] * group_weights)) if comparison_gap is not None else None,
                    gap_change=float(np.sum(comparison_gap[mask] * group_weights) - np.sum(baseline_gap[mask] * group_weights)) if baseline_gap is not None else None,
                ))
                
                # Deep poverty if available
                if baseline_deep is not None:
                    deep_count_baseline = np.sum(baseline_deep[mask] * group_weights)
                    deep_count_reform = np.sum(comparison_deep[mask] * group_weights)
                    deep_rate_baseline = deep_count_baseline / total_weight
                    deep_rate_reform = deep_count_reform / total_weight
                    
                    results.append(PovertyImpactModel(
                        poverty_type="deep",
                        demographic_group=group_name,
                        headcount_baseline=float(deep_count_baseline),
                        headcount_reform=float(deep_count_reform),
                        headcount_change=float(deep_count_reform - deep_count_baseline),
                        rate_baseline=float(deep_rate_baseline),
                        rate_reform=float(deep_rate_reform),
                        rate_change=float(deep_rate_reform - deep_rate_baseline),
                    ))
    
    return results


def calculate_inequality_impacts(
    baseline: SimulationDataModel,
    comparison: SimulationDataModel
) -> InequalityImpactModel:
    """Calculate inequality metrics using microdf.
    
    Args:
        baseline: Baseline simulation data
        comparison: Comparison simulation data
        
    Returns:
        InequalityImpactModel object
    """
    baseline_hh = baseline.household
    comparison_hh = comparison.household
    
    # Get incomes with proper weighting
    baseline_income = MicroSeries(
        baseline_hh["household_net_income"].values,
        weights=baseline_hh.get("household_weight", pd.Series(np.ones(len(baseline_hh)))).values
    )
    comparison_income = MicroSeries(
        comparison_hh["household_net_income"].values,
        weights=baseline_income.weights
    )
    
    # Weight by household members for person-level metrics
    if "household_count_people" in baseline_hh.columns:
        people_per_hh = baseline_hh["household_count_people"].values
        baseline_income.weights *= people_per_hh
        comparison_income.weights *= people_per_hh
    
    # Calculate Gini coefficients
    try:
        gini_baseline = baseline_income.gini()
        gini_reform = comparison_income.gini()
    except:
        gini_baseline = gini_reform = 0
    
    # Calculate top income shares
    in_top_10 = baseline_income.percentile_rank() > 90
    in_top_1 = baseline_income.percentile_rank() > 99
    in_bottom_50 = baseline_income.percentile_rank() <= 50
    
    total_baseline = baseline_income.sum()
    total_reform = comparison_income.sum()
    
    if total_baseline > 0:
        top_10_baseline = baseline_income[in_top_10].sum() / total_baseline
        top_1_baseline = baseline_income[in_top_1].sum() / total_baseline
        bottom_50_baseline = baseline_income[in_bottom_50].sum() / total_baseline
    else:
        top_10_baseline = top_1_baseline = bottom_50_baseline = 0
    
    if total_reform > 0:
        top_10_reform = comparison_income[in_top_10].sum() / total_reform
        top_1_reform = comparison_income[in_top_1].sum() / total_reform
        bottom_50_reform = comparison_income[in_bottom_50].sum() / total_reform
    else:
        top_10_reform = top_1_reform = bottom_50_reform = 0
    
    return InequalityImpactModel(
        gini_baseline=float(gini_baseline),
        gini_reform=float(gini_reform),
        gini_change=float(gini_reform - gini_baseline),
        top_10_percent_share_baseline=float(top_10_baseline),
        top_10_percent_share_reform=float(top_10_reform),
        top_10_percent_share_change=float(top_10_reform - top_10_baseline),
        top_1_percent_share_baseline=float(top_1_baseline),
        top_1_percent_share_reform=float(top_1_reform),
        top_1_percent_share_change=float(top_1_reform - top_1_baseline),
        bottom_50_percent_share_baseline=float(bottom_50_baseline),
        bottom_50_percent_share_reform=float(bottom_50_reform),
        bottom_50_percent_share_change=float(bottom_50_reform - bottom_50_baseline),
    )


def calculate_budgetary_impacts(
    baseline: SimulationDataModel,
    comparison: SimulationDataModel
) -> BudgetImpactModel:
    """Calculate budgetary impacts from tax and benefit changes.
    
    Args:
        baseline: Baseline simulation data
        comparison: Comparison simulation data
        
    Returns:
        BudgetImpactModel object
    """
    baseline_hh = baseline.household
    comparison_hh = comparison.household
    
    weights = baseline_hh.get("household_weight", pd.Series(np.ones(len(baseline_hh)))).values
    
    budget = BudgetImpactModel()
    
    # Government balance if available
    if "gov_balance" in baseline_hh.columns:
        budget.gov_balance_baseline = float((baseline_hh["gov_balance"].values * weights).sum())
        budget.gov_balance_reform = float((comparison_hh["gov_balance"].values * weights).sum())
        budget.gov_balance_change = budget.gov_balance_reform - budget.gov_balance_baseline
    
    # Calculate tax revenue impact
    if "household_tax" in baseline_hh.columns:
        budget.gov_tax_baseline = float((baseline_hh["household_tax"].values * weights).sum())
        budget.gov_tax_reform = float((comparison_hh["household_tax"].values * weights).sum())
        budget.gov_tax_change = budget.gov_tax_reform - budget.gov_tax_baseline
    elif "gov_tax" in baseline_hh.columns:
        budget.gov_tax_baseline = float((baseline_hh["gov_tax"].values * weights).sum())
        budget.gov_tax_reform = float((comparison_hh["gov_tax"].values * weights).sum())
        budget.gov_tax_change = budget.gov_tax_reform - budget.gov_tax_baseline
    
    # Calculate benefit spending impact
    if "household_benefits" in baseline_hh.columns:
        budget.gov_spending_baseline = float((baseline_hh["household_benefits"].values * weights).sum())
        budget.gov_spending_reform = float((comparison_hh["household_benefits"].values * weights).sum())
        budget.gov_spending_change = budget.gov_spending_reform - budget.gov_spending_baseline
    elif "gov_spending" in baseline_hh.columns:
        budget.gov_spending_baseline = float((baseline_hh["gov_spending"].values * weights).sum())
        budget.gov_spending_reform = float((comparison_hh["gov_spending"].values * weights).sum())
        budget.gov_spending_change = budget.gov_spending_reform - budget.gov_spending_baseline
    
    # Additional specific metrics can be calculated and stored in additional_metrics
    # For example, specific tax types or benefit programs
    for col in baseline_hh.columns:
        if col.endswith("_tax") or col.endswith("_benefit") or col.startswith("gov_"):
            if col not in ["household_tax", "gov_tax", "household_benefits", "gov_spending", "gov_balance"]:
                baseline_val = float((baseline_hh[col].values * weights).sum())
                reform_val = float((comparison_hh[col].values * weights).sum())
                budget.additional_metrics[col] = {
                    "baseline": baseline_val,
                    "reform": reform_val,
                    "change": reform_val - baseline_val
                }
    
    return budget


def calculate_household_income_impacts(
    baseline: SimulationDataModel,
    comparison: SimulationDataModel
) -> HouseholdIncomeImpactModel:
    """Calculate household income impacts.
    
    Args:
        baseline: Baseline simulation data
        comparison: Comparison simulation data
        
    Returns:
        HouseholdIncomeImpactModel object
    """
    baseline_hh = baseline.household
    comparison_hh = comparison.household
    
    weights = baseline_hh.get("household_weight", pd.Series(np.ones(len(baseline_hh)))).values
    
    income = HouseholdIncomeImpactModel()
    
    # Market income
    if "household_market_income" in baseline_hh.columns:
        income.household_market_income_baseline = float((baseline_hh["household_market_income"].values * weights).sum())
        income.household_market_income_reform = float((comparison_hh["household_market_income"].values * weights).sum())
        income.household_market_income_change = income.household_market_income_reform - income.household_market_income_baseline
    
    # Net income
    if "household_net_income" in baseline_hh.columns:
        income.household_net_income_baseline = float((baseline_hh["household_net_income"].values * weights).sum())
        income.household_net_income_reform = float((comparison_hh["household_net_income"].values * weights).sum())
        income.household_net_income_change = income.household_net_income_reform - income.household_net_income_baseline
    
    # Additional income metrics
    income_columns = [
        "equiv_household_net_income",
        "hbai_household_net_income",
        "household_net_income_including_health_benefits",
        "disposable_income",
    ]
    
    for col in income_columns:
        if col in baseline_hh.columns:
            baseline_val = float((baseline_hh[col].values * weights).sum())
            reform_val = float((comparison_hh[col].values * weights).sum())
            income.additional_metrics[col] = {
                "baseline": baseline_val,
                "reform": reform_val,
                "change": reform_val - baseline_val
            }
    
    return income


def calculate_economic_impacts(
    baseline: SimulationDataModel,
    comparison: SimulationDataModel,
    report_metadata: ReportMetadataModel
) -> EconomicImpactModel:
    """Calculate all economic impacts.
    
    Args:
        baseline: Baseline simulation data
        comparison: Comparison simulation data
        report_metadata: Report metadata
        
    Returns:
        Complete EconomicImpactModel with all impacts
    """
    return EconomicImpactModel(
        report_metadata=report_metadata,
        budget_impact=calculate_budgetary_impacts(baseline, comparison),
        household_income=calculate_household_income_impacts(baseline, comparison),
        decile_impacts=calculate_decile_impacts(baseline, comparison),
        poverty_impacts=calculate_poverty_impacts(baseline, comparison),
        inequality_impact=calculate_inequality_impacts(baseline, comparison),
    )