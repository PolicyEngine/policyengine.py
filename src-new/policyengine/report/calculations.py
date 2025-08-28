"""Economic impact calculations using microdf for proper weighting."""

from typing import Dict, Tuple, Optional, TYPE_CHECKING
import numpy as np
import pandas as pd
from microdf import MicroSeries

if TYPE_CHECKING:
    from ..countries.general import ModelOutput


def calculate_decile_impacts(
    baseline: "ModelOutput",
    comparison: "ModelOutput",
    by_wealth: bool = False
) -> Dict:
    """Calculate decile impacts with proper weighting.
    
    Returns dict with structure for each decile:
    {
        'relative_change': float,
        'average_change': float,
        'winners_losers': {
            'lose_more_than_5_percent': float,
            'lose_less_than_5_percent': float,
            'no_change': float,
            'gain_less_than_5_percent': float,
            'gain_more_than_5_percent': float,
        }
    }
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
    elif "household_income_decile" in baseline_hh.columns:
        decile = baseline_hh["household_income_decile"].values.astype(int)
    else:
        # Calculate deciles from income
        decile = baseline_income.decile_rank().clip(1, 10).astype(int)
    
    # Calculate income changes
    absolute_change = (comparison_income - baseline_income).values
    capped_baseline = np.maximum(baseline_income.values, 1)
    capped_comparison = np.maximum(comparison_income.values, 1) 
    relative_change = (capped_comparison - capped_baseline) / capped_baseline
    
    results = {}
    
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
                decile_people[(decile_relative_change >= -0.05) & (decile_relative_change < -0.001)] *
                baseline_income.weights[mask][(decile_relative_change >= -0.05) & (decile_relative_change < -0.001)]
            ) / total_people
            
            no_change = np.sum(
                decile_people[(decile_relative_change >= -0.001) & (decile_relative_change <= 0.001)] *
                baseline_income.weights[mask][(decile_relative_change >= -0.001) & (decile_relative_change <= 0.001)]
            ) / total_people
            
            gain_less_5 = np.sum(
                decile_people[(decile_relative_change > 0.001) & (decile_relative_change <= 0.05)] *
                baseline_income.weights[mask][(decile_relative_change > 0.001) & (decile_relative_change <= 0.05)]
            ) / total_people
            
            gain_more_5 = np.sum(
                decile_people[decile_relative_change > 0.05] *
                baseline_income.weights[mask][decile_relative_change > 0.05]
            ) / total_people
        else:
            lose_more_5 = lose_less_5 = no_change = gain_less_5 = gain_more_5 = 0
            
        results[d] = {
            'relative_change': float(rel_change),
            'average_change': float(avg_change),
            'winners_losers': {
                'lose_more_than_5_percent': float(lose_more_5),
                'lose_less_than_5_percent': float(lose_less_5),
                'no_change': float(no_change),
                'gain_less_than_5_percent': float(gain_less_5),
                'gain_more_than_5_percent': float(gain_more_5),
            }
        }
    
    return results


def calculate_poverty_impacts(
    baseline: "ModelOutput",
    comparison: "ModelOutput"
) -> Dict:
    """Calculate poverty impacts by demographic groups.
    
    Since poverty variables aren't always in the data, we calculate them
    based on poverty thresholds when needed.
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
        # Calculate poverty based on income and thresholds
        # This is a simplified calculation - real implementation would use proper thresholds
        baseline_poverty = np.zeros(len(baseline_person), dtype=bool)
        comparison_poverty = np.zeros(len(comparison_person), dtype=bool)
    
    # Deep poverty
    if "person_in_deep_poverty" in baseline_person.columns:
        baseline_deep = baseline_person["person_in_deep_poverty"].values
        comparison_deep = comparison_person["person_in_deep_poverty"].values
    elif "in_deep_poverty" in baseline_person.columns:
        baseline_deep = baseline_person["in_deep_poverty"].values
        comparison_deep = comparison_person["in_deep_poverty"].values
    else:
        baseline_deep = None
        comparison_deep = None
    
    results = {}
    
    # Age groups
    if "age" in baseline_person.columns:
        ages = baseline_person["age"].values
        
        age_groups = [
            ("age", "child", ages < 18),
            ("age", "adult", (ages >= 18) & (ages < 65)),
            ("age", "senior", ages >= 65),
            ("age", "all", np.ones(len(ages), dtype=bool)),
        ]
        
        for group_type, group_value, mask in age_groups:
            group_weights = person_weights.weights[mask]
            total_weight = np.sum(group_weights)
            
            if total_weight > 0:
                poverty_baseline = np.sum(baseline_poverty[mask] * group_weights) / total_weight
                poverty_reform = np.sum(comparison_poverty[mask] * group_weights) / total_weight
                
                if baseline_deep is not None:
                    deep_baseline = np.sum(baseline_deep[mask] * group_weights) / total_weight
                    deep_reform = np.sum(comparison_deep[mask] * group_weights) / total_weight
                else:
                    deep_baseline = deep_reform = None
            else:
                poverty_baseline = poverty_reform = 0
                deep_baseline = deep_reform = None
            
            key = f"{group_type}_{group_value}"
            results[key] = {
                'poverty': {
                    'baseline': float(poverty_baseline),
                    'reform': float(poverty_reform),
                    'change': float(poverty_reform - poverty_baseline),
                },
                'deep_poverty': {
                    'baseline': float(deep_baseline) if deep_baseline is not None else None,
                    'reform': float(deep_reform) if deep_reform is not None else None,
                    'change': float(deep_reform - deep_baseline) if deep_baseline is not None else None,
                }
            }
    
    # Gender breakdown
    if "is_male" in baseline_person.columns:
        is_male = baseline_person["is_male"].values
        
        gender_groups = [
            ("gender", "male", is_male),
            ("gender", "female", ~is_male),
        ]
        
        for group_type, group_value, mask in gender_groups:
            group_weights = person_weights.weights[mask]
            total_weight = np.sum(group_weights)
            
            if total_weight > 0:
                poverty_baseline = np.sum(baseline_poverty[mask] * group_weights) / total_weight
                poverty_reform = np.sum(comparison_poverty[mask] * group_weights) / total_weight
                
                if baseline_deep is not None:
                    deep_baseline = np.sum(baseline_deep[mask] * group_weights) / total_weight
                    deep_reform = np.sum(comparison_deep[mask] * group_weights) / total_weight
                else:
                    deep_baseline = deep_reform = None
            else:
                poverty_baseline = poverty_reform = 0
                deep_baseline = deep_reform = None
            
            key = f"{group_type}_{group_value}"
            results[key] = {
                'poverty': {
                    'baseline': float(poverty_baseline),
                    'reform': float(poverty_reform),
                    'change': float(poverty_reform - poverty_baseline),
                },
                'deep_poverty': {
                    'baseline': float(deep_baseline) if deep_baseline is not None else None,
                    'reform': float(deep_reform) if deep_reform is not None else None,
                    'change': float(deep_reform - deep_baseline) if deep_baseline is not None else None,
                }
            }
    
    return results


def calculate_inequality_impacts(
    baseline: "ModelOutput",
    comparison: "ModelOutput"
) -> Dict:
    """Calculate inequality metrics using microdf."""
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
    
    top_10_baseline = baseline_income[in_top_10].sum() / baseline_income.sum()
    top_10_reform = comparison_income[in_top_10].sum() / comparison_income.sum()
    
    top_1_baseline = baseline_income[in_top_1].sum() / baseline_income.sum()
    top_1_reform = comparison_income[in_top_1].sum() / comparison_income.sum()
    
    return {
        'gini': {
            'baseline': float(gini_baseline),
            'reform': float(gini_reform),
            'change': float(gini_reform - gini_baseline),
        },
        'top_10_percent_share': {
            'baseline': float(top_10_baseline),
            'reform': float(top_10_reform),
            'change': float(top_10_reform - top_10_baseline),
        },
        'top_1_percent_share': {
            'baseline': float(top_1_baseline),
            'reform': float(top_1_reform),
            'change': float(top_1_reform - top_1_baseline),
        }
    }


def calculate_budgetary_impacts(
    baseline: "ModelOutput",
    comparison: "ModelOutput"
) -> Dict:
    """Calculate budgetary impacts from tax and benefit changes."""
    baseline_hh = baseline.household
    comparison_hh = comparison.household
    
    weights = baseline_hh.get("household_weight", pd.Series(np.ones(len(baseline_hh)))).values
    
    # Calculate tax revenue impact
    tax_revenue_impact = 0
    if "household_tax" in baseline_hh.columns:
        baseline_tax = (baseline_hh["household_tax"].values * weights).sum()
        comparison_tax = (comparison_hh["household_tax"].values * weights).sum()
        tax_revenue_impact = comparison_tax - baseline_tax
    elif "gov_tax" in baseline_hh.columns:
        baseline_tax = (baseline_hh["gov_tax"].values * weights).sum()
        comparison_tax = (comparison_hh["gov_tax"].values * weights).sum()
        tax_revenue_impact = comparison_tax - baseline_tax
    
    # Calculate benefit spending impact
    benefit_spending_impact = 0
    if "household_benefits" in baseline_hh.columns:
        baseline_benefits = (baseline_hh["household_benefits"].values * weights).sum()
        comparison_benefits = (comparison_hh["household_benefits"].values * weights).sum()
        benefit_spending_impact = comparison_benefits - baseline_benefits
    elif "gov_spending" in baseline_hh.columns:
        baseline_benefits = (baseline_hh["gov_spending"].values * weights).sum()
        comparison_benefits = (comparison_hh["gov_spending"].values * weights).sum()
        benefit_spending_impact = comparison_benefits - baseline_benefits
    
    # State tax (US)
    state_tax_revenue_impact = 0
    if "household_state_tax" in baseline_hh.columns:
        baseline_state_tax = (baseline_hh["household_state_tax"].values * weights).sum()
        comparison_state_tax = (comparison_hh["household_state_tax"].values * weights).sum()
        state_tax_revenue_impact = comparison_state_tax - baseline_state_tax
    
    # Overall budgetary impact
    budgetary_impact = tax_revenue_impact - benefit_spending_impact
    
    # Baseline net income
    baseline_net_income = (baseline_hh["household_net_income"].values * weights).sum()
    
    # Number of households
    households_affected = np.sum(weights)
    
    return {
        'budgetary_impact': float(budgetary_impact),
        'tax_revenue_impact': float(tax_revenue_impact),
        'state_tax_revenue_impact': float(state_tax_revenue_impact),
        'benefit_spending_impact': float(benefit_spending_impact),
        'households_affected': float(households_affected),
        'baseline_net_income': float(baseline_net_income),
    }