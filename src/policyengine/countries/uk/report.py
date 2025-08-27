"""UK-specific economic impact report."""

from typing import TYPE_CHECKING
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from .model_output import UKModelOutput
    from ...database.models import ReportMetadata

from ...database.models import (
    UKGovernmentBudget,
    UKHouseholdIncome,
    UKDecileImpact,
    UKPovertyImpact,
    UKInequalityImpact,
    UKWinnersLosers,
)


class UKEconomicImpactReport:
    """UK-specific economic impact report."""
    
    def __init__(self, session: Session, report_metadata: "ReportMetadata"):
        """Initialise UK economic impact report.
        
        Args:
            session: Database session
            report_metadata: Report metadata from database
        """
        self.session = session
        self.report = report_metadata
    
    def calculate_all_impacts(self, baseline: "UKModelOutput", comparison: "UKModelOutput") -> None:
        """Calculate all economic impacts and populate database tables.
        
        Args:
            baseline: Baseline simulation output
            comparison: Comparison/reform simulation output
        """
        # Calculate and store all impacts
        self.calculate_government_budget(baseline, comparison)
        self.calculate_household_income(baseline, comparison)
        self.calculate_decile_impacts(baseline, comparison)
        self.calculate_poverty_impacts(baseline, comparison)
        self.calculate_inequality_impacts(baseline, comparison)
        self.calculate_winners_losers(baseline, comparison)
        
        # Commit all changes to the database
        self.session.commit()
    
    def calculate_government_budget(self, baseline: "UKModelOutput", comparison: "UKModelOutput") -> None:
        """Calculate government budget impacts."""
        budget = UKGovernmentBudget(report_id=self.report.id)
        
        # Get weighted sums for government variables
        baseline_hh = baseline.household
        comparison_hh = comparison.household
        weights = baseline_hh["household_weight"]
        
        # Government balance
        if "gov_balance" in baseline_hh.columns:
            budget.gov_balance_baseline = float((baseline_hh["gov_balance"] * weights).sum())
            budget.gov_balance_reform = float((comparison_hh["gov_balance"] * weights).sum())
            budget.gov_balance_change = budget.gov_balance_reform - budget.gov_balance_baseline
        
        # Total tax revenues
        if "gov_tax" in baseline_hh.columns:
            budget.gov_tax_baseline = float((baseline_hh["gov_tax"] * weights).sum())
            budget.gov_tax_reform = float((comparison_hh["gov_tax"] * weights).sum())
            budget.gov_tax_change = budget.gov_tax_reform - budget.gov_tax_baseline
        
        # Individual taxes
        tax_variables = [
            ("income_tax", "income_tax"),
            ("national_insurance", "national_insurance"),
            ("ni_employer", "ni_employer"),
            ("vat", "vat"),
            ("capital_gains_tax", "capital_gains_tax"),
        ]
        
        for var_name, attr_name in tax_variables:
            if var_name in baseline_hh.columns:
                baseline_val = float((baseline_hh[var_name] * weights).sum())
                reform_val = float((comparison_hh[var_name] * weights).sum())
                setattr(budget, f"{attr_name}_baseline", baseline_val)
                setattr(budget, f"{attr_name}_reform", reform_val)
                setattr(budget, f"{attr_name}_change", reform_val - baseline_val)
        
        # Government spending
        if "gov_spending" in baseline_hh.columns:
            budget.gov_spending_baseline = float((baseline_hh["gov_spending"] * weights).sum())
            budget.gov_spending_reform = float((comparison_hh["gov_spending"] * weights).sum())
            budget.gov_spending_change = budget.gov_spending_reform - budget.gov_spending_baseline
        
        # Individual benefits
        benefit_variables = [
            ("universal_credit", "universal_credit"),
            ("state_pension", "state_pension"),
            ("pip", "pip"),
            ("dla", "dla"),
            ("housing_benefit", "housing_benefit"),
            ("working_tax_credit", "working_tax_credit"),
            ("child_tax_credit", "child_tax_credit"),
        ]
        
        for var_name, attr_name in benefit_variables:
            if var_name in baseline_hh.columns:
                baseline_val = float((baseline_hh[var_name] * weights).sum())
                reform_val = float((comparison_hh[var_name] * weights).sum())
                setattr(budget, f"{attr_name}_baseline", baseline_val)
                setattr(budget, f"{attr_name}_reform", reform_val)
                setattr(budget, f"{attr_name}_change", reform_val - baseline_val)
        
        self.session.add(budget)
    
    def calculate_household_income(self, baseline: "UKModelOutput", comparison: "UKModelOutput") -> None:
        """Calculate household income impacts."""
        income = UKHouseholdIncome(report_id=self.report.id)
        
        baseline_hh = baseline.household
        comparison_hh = comparison.household
        weights = baseline_hh["household_weight"]
        
        # Market income
        if "household_market_income" in baseline_hh.columns:
            income.household_market_income_baseline = float((baseline_hh["household_market_income"] * weights).sum())
            income.household_market_income_reform = float((comparison_hh["household_market_income"] * weights).sum())
            income.household_market_income_change = income.household_market_income_reform - income.household_market_income_baseline
        
        # HBAI net income
        if "hbai_household_net_income" in baseline_hh.columns:
            income.hbai_household_net_income_baseline = float((baseline_hh["hbai_household_net_income"] * weights).sum())
            income.hbai_household_net_income_reform = float((comparison_hh["hbai_household_net_income"] * weights).sum())
            income.hbai_household_net_income_change = income.hbai_household_net_income_reform - income.hbai_household_net_income_baseline
        
        # Comprehensive net income
        if "household_net_income" in baseline_hh.columns:
            income.household_net_income_baseline = float((baseline_hh["household_net_income"] * weights).sum())
            income.household_net_income_reform = float((comparison_hh["household_net_income"] * weights).sum())
            income.household_net_income_change = income.household_net_income_reform - income.household_net_income_baseline
        
        self.session.add(income)
    
    def calculate_decile_impacts(self, baseline: "UKModelOutput", comparison: "UKModelOutput") -> None:
        """Calculate impacts by decile for income, consumption, and wealth."""
        baseline_hh = baseline.household
        comparison_hh = comparison.household
        weights = baseline_hh["household_weight"]
        
        # Variables to aggregate
        aggregate_variables = [
            "household_net_income",
            "hbai_household_net_income", 
            "household_market_income",
            "gov_tax",
            "gov_spending",
            "household_benefits",
            "household_tax",
        ]
        
        # Decile types
        decile_types = [
            ("equiv_hbai_household_net_income", "equiv_hbai_household_net_income"),
            ("consumption", "consumption"),
            ("total_wealth", "total_wealth"),
        ]
        
        for decile_var, decile_type_name in decile_types:
            if decile_var not in baseline_hh.columns:
                continue
            
            # Create weighted deciles based on baseline values
            baseline_hh["decile"] = self._get_weighted_deciles(baseline_hh[decile_var], weights)
            comparison_hh["decile"] = baseline_hh["decile"]
            
            # Calculate for each variable
            for var in aggregate_variables:
                if var not in baseline_hh.columns:
                    continue
                
                # Overall (decile = 0)
                overall_impact = UKDecileImpact(
                    report_id=self.report.id,
                    decile_type=decile_type_name,
                    decile=0,
                    variable_name=var,
                    sum_baseline=float((baseline_hh[var] * weights).sum()),
                    sum_reform=float((comparison_hh[var] * weights).sum()),
                    mean_baseline=float((baseline_hh[var] * weights).sum() / weights.sum()),
                    mean_reform=float((comparison_hh[var] * weights).sum() / weights.sum())
                )
                overall_impact.sum_change = overall_impact.sum_reform - overall_impact.sum_baseline
                overall_impact.mean_change = overall_impact.mean_reform - overall_impact.mean_baseline
                self.session.add(overall_impact)
                
                # By decile
                for decile in range(1, 11):
                    decile_mask = baseline_hh["decile"] == decile
                    decile_weights = weights[decile_mask]
                    
                    if decile_weights.sum() > 0:
                        decile_impact = UKDecileImpact(
                            report_id=self.report.id,
                            decile_type=decile_type_name,
                            decile=decile,
                            variable_name=var,
                            sum_baseline=float((baseline_hh.loc[decile_mask, var] * decile_weights).sum()),
                            sum_reform=float((comparison_hh.loc[decile_mask, var] * decile_weights).sum()),
                            mean_baseline=float((baseline_hh.loc[decile_mask, var] * decile_weights).sum() / decile_weights.sum()),
                            mean_reform=float((comparison_hh.loc[decile_mask, var] * decile_weights).sum() / decile_weights.sum())
                        )
                        decile_impact.sum_change = decile_impact.sum_reform - decile_impact.sum_baseline
                        decile_impact.mean_change = decile_impact.mean_reform - decile_impact.mean_baseline
                        self.session.add(decile_impact)
    
    def calculate_poverty_impacts(self, baseline: "UKModelOutput", comparison: "UKModelOutput") -> None:
        """Calculate poverty impacts using HBAI definitions."""
        # Note: Poverty variables (in_poverty, in_relative_poverty, etc.) are not currently 
        # available in the model, so this method will not populate any data for now.
        # When these variables are added to policyengine-uk, this method will automatically
        # start working.
        
        baseline_hh = baseline.household
        comparison_hh = comparison.household
        
        # Poverty variables
        poverty_variables = [
            ("in_poverty", "absolute_bhc"),
            ("in_relative_poverty_bhc", "relative_bhc"),
            ("in_poverty_ahc", "absolute_ahc"),
            ("in_relative_poverty_ahc", "relative_ahc"),
        ]
        
        # Check if any poverty variables exist
        poverty_vars_exist = any(pv[0] in baseline_hh.columns for pv in poverty_variables)
        
        if not poverty_vars_exist:
            # No poverty variables available, skip calculation
            return
        
        # Get person-level data with household poverty status
        baseline_person = baseline.person
        comparison_person = comparison.person
        
        # Get person weights
        person_weights = baseline_person["person_weight"]
        
        # Demographic groups
        demographic_groups = ["all", "child", "working_age", "pensioner"]
        
        for poverty_var, poverty_type in poverty_variables:
            if poverty_var not in baseline_hh.columns:
                continue
            
            # Map household poverty to person level
            baseline_person["in_poverty"] = baseline_person["person_household_id"].map(
                baseline_hh.set_index("household_id")[poverty_var]
            )
            comparison_person["in_poverty"] = comparison_person["person_household_id"].map(
                comparison_hh.set_index("household_id")[poverty_var]
            )
            
            for group in demographic_groups:
                if group == "all":
                    mask = pd.Series([True] * len(baseline_person))
                elif group == "child" and "age" in baseline_person.columns:
                    mask = baseline_person["age"] < 18
                elif group == "working_age" and "age" in baseline_person.columns:
                    mask = (baseline_person["age"] >= 18) & (baseline_person["age"] < 65)
                elif group == "pensioner" and "age" in baseline_person.columns:
                    mask = baseline_person["age"] >= 65
                else:
                    continue
                
                group_weights = person_weights[mask]
                if group_weights.sum() > 0:
                    poverty_impact = UKPovertyImpact(
                        report_id=self.report.id,
                        poverty_type=poverty_type,
                        demographic_group=group,
                        headcount_baseline=float((baseline_person.loc[mask, "in_poverty"] * group_weights).sum()),
                        headcount_reform=float((comparison_person.loc[mask, "in_poverty"] * group_weights).sum()),
                        rate_baseline=float((baseline_person.loc[mask, "in_poverty"] * group_weights).sum() / group_weights.sum()),
                        rate_reform=float((comparison_person.loc[mask, "in_poverty"] * group_weights).sum() / group_weights.sum())
                    )
                    poverty_impact.headcount_change = poverty_impact.headcount_reform - poverty_impact.headcount_baseline
                    poverty_impact.rate_change = poverty_impact.rate_reform - poverty_impact.rate_baseline
                    self.session.add(poverty_impact)
    
    def calculate_inequality_impacts(self, baseline: "UKModelOutput", comparison: "UKModelOutput") -> None:
        """Calculate inequality metrics."""
        inequality = UKInequalityImpact(report_id=self.report.id)
        
        baseline_hh = baseline.household
        comparison_hh = comparison.household
        weights = baseline_hh["household_weight"]
        
        if "equiv_hbai_household_net_income" in baseline_hh.columns:
            income_var = "equiv_hbai_household_net_income"
            
            # Calculate Gini coefficient
            inequality.gini_baseline = self._calculate_gini(baseline_hh[income_var], weights)
            inequality.gini_reform = self._calculate_gini(comparison_hh[income_var], weights)
            inequality.gini_change = inequality.gini_reform - inequality.gini_baseline
            
            # Calculate top income shares
            baseline_sorted = baseline_hh.sort_values(income_var, ascending=False)
            comparison_sorted = comparison_hh.sort_values(income_var, ascending=False)
            
            # Top 10%
            cumulative_weight = baseline_sorted["household_weight"].cumsum()
            total_weight = weights.sum()
            top_10_mask = cumulative_weight <= (total_weight * 0.1)
            
            baseline_total = (baseline_hh[income_var] * weights).sum()
            comparison_total = (comparison_hh[income_var] * weights).sum()
            
            inequality.top_10_percent_share_baseline = float(
                (baseline_sorted.loc[top_10_mask, income_var] * baseline_sorted.loc[top_10_mask, "household_weight"]).sum() / baseline_total
            )
            inequality.top_10_percent_share_reform = float(
                (comparison_sorted.loc[top_10_mask, income_var] * comparison_sorted.loc[top_10_mask, "household_weight"]).sum() / comparison_total
            )
            inequality.top_10_percent_share_change = inequality.top_10_percent_share_reform - inequality.top_10_percent_share_baseline
            
            # Top 1%
            top_1_mask = cumulative_weight <= (total_weight * 0.01)
            inequality.top_1_percent_share_baseline = float(
                (baseline_sorted.loc[top_1_mask, income_var] * baseline_sorted.loc[top_1_mask, "household_weight"]).sum() / baseline_total
            )
            inequality.top_1_percent_share_reform = float(
                (comparison_sorted.loc[top_1_mask, income_var] * comparison_sorted.loc[top_1_mask, "household_weight"]).sum() / comparison_total
            )
            inequality.top_1_percent_share_change = inequality.top_1_percent_share_reform - inequality.top_1_percent_share_baseline
        
        self.session.add(inequality)
    
    def calculate_winners_losers(self, baseline: "UKModelOutput", comparison: "UKModelOutput") -> None:
        """Calculate winners and losers breakdown."""
        baseline_hh = baseline.household.copy()
        comparison_hh = comparison.household.copy()
        weights = baseline_hh["household_weight"]
        
        # Calculate income change
        if "household_net_income" in baseline_hh.columns:
            baseline_hh["pct_change"] = (
                (comparison_hh["household_net_income"] - baseline_hh["household_net_income"]) /
                baseline_hh["household_net_income"].clip(lower=1)
            ) * 100
            
            # Create deciles based on baseline income
            if "equiv_hbai_household_net_income" in baseline_hh.columns:
                baseline_hh["decile"] = self._get_weighted_deciles(
                    baseline_hh["equiv_hbai_household_net_income"], weights
                )
            else:
                baseline_hh["decile"] = self._get_weighted_deciles(
                    baseline_hh["household_net_income"], weights
                )
            
            # Overall (decile = 0)
            overall_wl = UKWinnersLosers(
                report_id=self.report.id,
                decile=0,
                gain_more_than_5_percent=float(((baseline_hh["pct_change"] >= 5) * weights).sum() / weights.sum()),
                gain_more_than_1_percent=float(((baseline_hh["pct_change"] >= 1) * weights).sum() / weights.sum()),
                no_change=float(((baseline_hh["pct_change"].abs() < 0.01) * weights).sum() / weights.sum()),
                lose_less_than_1_percent=float((((baseline_hh["pct_change"] < 0) & (baseline_hh["pct_change"] >= -1)) * weights).sum() / weights.sum()),
                lose_less_than_5_percent=float((((baseline_hh["pct_change"] < -1) & (baseline_hh["pct_change"] >= -5)) * weights).sum() / weights.sum()),
                lose_more_than_5_percent=float(((baseline_hh["pct_change"] < -5) * weights).sum() / weights.sum())
            )
            self.session.add(overall_wl)
            
            # By decile
            for decile in range(1, 11):
                decile_mask = baseline_hh["decile"] == decile
                decile_weights = weights[decile_mask]
                
                if decile_weights.sum() > 0:
                    decile_wl = UKWinnersLosers(
                        report_id=self.report.id,
                        decile=decile,
                        gain_more_than_5_percent=float(((baseline_hh.loc[decile_mask, "pct_change"] >= 5) * decile_weights).sum() / decile_weights.sum()),
                        gain_more_than_1_percent=float(((baseline_hh.loc[decile_mask, "pct_change"] >= 1) * decile_weights).sum() / decile_weights.sum()),
                        no_change=float(((baseline_hh.loc[decile_mask, "pct_change"].abs() < 0.01) * decile_weights).sum() / decile_weights.sum()),
                        lose_less_than_1_percent=float((((baseline_hh.loc[decile_mask, "pct_change"] < 0) & (baseline_hh.loc[decile_mask, "pct_change"] >= -1)) * decile_weights).sum() / decile_weights.sum()),
                        lose_less_than_5_percent=float((((baseline_hh.loc[decile_mask, "pct_change"] < -1) & (baseline_hh.loc[decile_mask, "pct_change"] >= -5)) * decile_weights).sum() / decile_weights.sum()),
                        lose_more_than_5_percent=float(((baseline_hh.loc[decile_mask, "pct_change"] < -5) * decile_weights).sum() / decile_weights.sum())
                    )
                    self.session.add(decile_wl)
    
    def _get_weighted_deciles(self, values: pd.Series, weights: pd.Series) -> pd.Series:
        """Create weighted deciles for a series of values."""
        # Sort by values
        sorted_indices = values.argsort()
        sorted_values = values.iloc[sorted_indices]
        sorted_weights = weights.iloc[sorted_indices]
        
        # Calculate cumulative weights
        cumsum_weights = sorted_weights.cumsum()
        total_weight = sorted_weights.sum()
        
        # Create decile boundaries
        decile_thresholds = [total_weight * i / 10 for i in range(1, 10)]
        
        # Assign deciles
        deciles = pd.Series(index=values.index, dtype=int)
        for i, idx in enumerate(sorted_indices):
            cum_weight = cumsum_weights.iloc[i]
            decile = 1
            for threshold in decile_thresholds:
                if cum_weight > threshold:
                    decile += 1
                else:
                    break
            deciles.loc[idx] = decile
        
        return deciles
    
    def _calculate_gini(self, values: pd.Series, weights: pd.Series) -> float:
        """Calculate Gini coefficient for weighted data."""
        # Sort by values
        sorted_indices = values.argsort()
        sorted_values = values.iloc[sorted_indices]
        sorted_weights = weights.iloc[sorted_indices]
        
        # Calculate cumulative weighted values
        cumsum_weighted_values = (sorted_values * sorted_weights).cumsum()
        
        # Calculate Gini
        total_weight = sorted_weights.sum()
        total_weighted_value = cumsum_weighted_values.iloc[-1]
        
        if total_weighted_value == 0:
            return 0.0
        
        # Area under Lorenz curve
        width = sorted_weights / total_weight
        area = ((cumsum_weighted_values / total_weighted_value) * width).sum()
        
        # Gini = 1 - 2 * area_under_lorenz_curve
        gini = 1 - 2 * area
        return float(np.clip(gini, 0, 1))