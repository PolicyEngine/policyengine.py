"""Default variable lists for PolicyEngine database storage.

These subsets of variables are commonly used in PolicyEngine operations
and should be prioritised for storage in the database.
"""

DEFAULT_VARIABLES_UK = [
    # Person demographics
    "age",
    "is_male",
    "is_adult",
    "person_weight",
    
    # Person income
    "employment_income",
    "self_employment_income",
    "employment_income_before_lsr",
    "self_employment_income_before_lsr",
    "farm_income",
    
    # Person tax
    "marginal_tax_rate",
    
    # Person location
    "country",
    
    # Household income
    "household_net_income",
    "household_market_income",
    "equiv_household_net_income",
    "household_income_decile",
    "total_wealth",
    "household_wealth_decile",
    
    # Household composition
    "household_count_people",
    "household_weight",
    
    # Household poverty
    "in_poverty",
    "poverty_gap",
    "deep_poverty_gap",
    "in_deep_poverty",
    
    # UK taxes
    "income_tax",
    "national_insurance",
    "ni_employer",
    "vat",
    "council_tax",
    "fuel_duty",
    
    # UK benefits
    "tax_credits",
    "universal_credit",
    "child_benefit",
    "state_pension",
    "pension_credit",
    
    # UK government aggregates
    "gov_tax",
    "gov_spending",
]

DEFAULT_VARIABLES_US = [
    # Person demographics
    "age",
    "is_male",
    "race",
    "is_adult",
    "person_weight",
    
    # Person income
    "employment_income",
    "self_employment_income",
    "employment_income_before_lsr",
    "self_employment_income_before_lsr",
    "farm_income",
    
    # Person tax
    "marginal_tax_rate",
    
    # Person behavioral response
    "employment_income_behavioral_response",
    "emp_self_emp_ratio",
    "substitution_elasticity_lsr",
    "income_elasticity_lsr",
    "weekly_hours_worked",
    "weekly_hours_worked_behavioural_response_income_elasticity",
    "weekly_hours_worked_behavioural_response_substitution_elasticity",
    
    # Person cliff analysis
    "cliff_evaluated",
    "cliff_gap",
    "is_on_cliff",
    
    # Person location
    "state_code_str",
    "in_nyc",
    
    # Household income
    "household_net_income",
    "household_market_income",
    "equiv_household_net_income",
    "household_income_decile",
    "total_wealth",
    "household_wealth_decile",
    
    # Household composition
    "household_count_people",
    "household_weight",
    
    # Household poverty
    "in_poverty",
    "poverty_gap",
    "deep_poverty_gap",
    "in_deep_poverty",
    
    # US tax/benefit
    "household_tax",
    "household_benefits",
    "household_state_income_tax",
]

def get_default_variables(country: str) -> list:
    """Get default variables for a given country.
    
    Args:
        country: Country code ('uk' or 'us')
        
    Returns:
        List of variable names to calculate
    """
    country = country.lower()
    
    if country == "uk":
        return DEFAULT_VARIABLES_UK
    elif country == "us":
        return DEFAULT_VARIABLES_US
    else:
        # Return a minimal set for unknown countries
        return ["age", "household_net_income", "household_weight", "person_weight"]