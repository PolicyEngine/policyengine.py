"""US-specific economic impact report."""

from typing import TYPE_CHECKING
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from .model_output import USModelOutput
    from ...database.models import ReportMetadata

from ...database.models import (
    USGovernmentBudget,
    USHouseholdIncome,
    USDecileImpact,
    USPovertyImpact,
    USInequalityImpact,
    USWinnersLosers,
    USProgramImpact,
)


class USEconomicImpactReport:
    """US-specific economic impact report."""
    
    def __init__(self, session: Session, report_metadata: "ReportMetadata"):
        """Initialise US economic impact report.
        
        Args:
            session: SimulationOrchestrator session
            report_metadata: Report metadata from database
        """
        self.session = session
        self.report = report_metadata
    
    def calculate_all_impacts(self, baseline: "USModelOutput", comparison: "USModelOutput") -> None:
        """Calculate all US economic impacts and populate database tables.
        
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
        self.calculate_program_impacts(baseline, comparison)
        
        # Commit all changes to the database
        self.session.commit()
    
    def calculate_government_budget(self, baseline: "USModelOutput", comparison: "USModelOutput") -> None:
        """Calculate government budget impacts."""
        budget = USGovernmentBudget(report_id=self.report.id)
        
        baseline_hh = baseline.household
        comparison_hh = comparison.household
        weights = baseline_hh["household_weight"]
        
        # Total tax revenues (federal + state)
        if "household_tax" in baseline_hh.columns:
            budget.total_tax_baseline = float((baseline_hh["household_tax"] * weights).sum())
            budget.total_tax_reform = float((comparison_hh["household_tax"] * weights).sum())
            budget.total_tax_change = budget.total_tax_reform - budget.total_tax_baseline
        
        # State tax (before refundable credits + refundable credits)
        if "household_state_tax_before_refundable_credits" in baseline_hh.columns and "household_refundable_state_tax_credits" in baseline_hh.columns:
            state_tax_baseline = baseline_hh["household_state_tax_before_refundable_credits"] - baseline_hh["household_refundable_state_tax_credits"]
            state_tax_reform = comparison_hh["household_state_tax_before_refundable_credits"] - comparison_hh["household_refundable_state_tax_credits"]
            budget.state_tax_baseline = float((state_tax_baseline * weights).sum())
            budget.state_tax_reform = float((state_tax_reform * weights).sum())
            budget.state_tax_change = budget.state_tax_reform - budget.state_tax_baseline
            
            # Federal tax (total - state)
            if "household_tax" in baseline_hh.columns:
                federal_tax_baseline = baseline_hh["household_tax"] - state_tax_baseline
                federal_tax_reform = comparison_hh["household_tax"] - state_tax_reform
                budget.federal_tax_baseline = float((federal_tax_baseline * weights).sum())
                budget.federal_tax_reform = float((federal_tax_reform * weights).sum())
                budget.federal_tax_change = budget.federal_tax_reform - budget.federal_tax_baseline
        
        # Total benefits
        if "household_benefits" in baseline_hh.columns:
            budget.total_benefits_baseline = float((baseline_hh["household_benefits"] * weights).sum())
            budget.total_benefits_reform = float((comparison_hh["household_benefits"] * weights).sum())
            budget.total_benefits_change = budget.total_benefits_reform - budget.total_benefits_baseline
        
        # Federal benefits (total - state)
        if "household_benefits" in baseline_hh.columns and "household_state_benefits" in baseline_hh.columns:
            federal_benefits_baseline = baseline_hh["household_benefits"] - baseline_hh["household_state_benefits"]
            federal_benefits_reform = comparison_hh["household_benefits"] - comparison_hh["household_state_benefits"]
            budget.federal_benefits_baseline = float((federal_benefits_baseline * weights).sum())
            budget.federal_benefits_reform = float((federal_benefits_reform * weights).sum())
            budget.federal_benefits_change = budget.federal_benefits_reform - budget.federal_benefits_baseline
        
        # State benefits
        if "household_state_benefits" in baseline_hh.columns:
            budget.state_benefits_baseline = float((baseline_hh["household_state_benefits"] * weights).sum())
            budget.state_benefits_reform = float((comparison_hh["household_state_benefits"] * weights).sum())
            budget.state_benefits_change = budget.state_benefits_reform - budget.state_benefits_baseline
        
        # Net impact (revenue increase - spending increase)
        if budget.total_tax_change is not None and budget.total_benefits_change is not None:
            budget.net_impact = budget.total_tax_change - budget.total_benefits_change
        
        self.session.add(budget)
    
    def calculate_household_income(self, baseline: "USModelOutput", comparison: "USModelOutput") -> None:
        """Calculate household income impacts."""
        income = USHouseholdIncome(report_id=self.report.id)
        
        baseline_hh = baseline.household
        comparison_hh = comparison.household
        weights = baseline_hh["household_weight"]
        
        # Market income
        if "household_market_income" in baseline_hh.columns:
            income.household_market_income_baseline = float((baseline_hh["household_market_income"] * weights).sum())
            income.household_market_income_reform = float((comparison_hh["household_market_income"] * weights).sum())
            income.household_market_income_change = income.household_market_income_reform - income.household_market_income_baseline
        
        # Net income
        if "household_net_income" in baseline_hh.columns:
            income.household_net_income_baseline = float((baseline_hh["household_net_income"] * weights).sum())
            income.household_net_income_reform = float((comparison_hh["household_net_income"] * weights).sum())
            income.household_net_income_change = income.household_net_income_reform - income.household_net_income_baseline
        
        # Net income including health benefits
        if "household_net_income_including_health_benefits" in baseline_hh.columns:
            income.household_net_income_with_health_baseline = float((baseline_hh["household_net_income_including_health_benefits"] * weights).sum())
            income.household_net_income_with_health_reform = float((comparison_hh["household_net_income_including_health_benefits"] * weights).sum())
            income.household_net_income_with_health_change = income.household_net_income_with_health_reform - income.household_net_income_with_health_baseline
        
        self.session.add(income)
    
    def calculate_decile_impacts(self, baseline: "USModelOutput", comparison: "USModelOutput") -> None:
        """Calculate impacts by income decile."""
        baseline_hh = baseline.household.copy()
        comparison_hh = comparison.household.copy()
        weights = baseline_hh["household_weight"]
        
        # Use equivalized household net income for decile creation
        income_var = "equiv_household_net_income" if "equiv_household_net_income" in baseline_hh.columns else "household_net_income"
        
        if income_var not in baseline_hh.columns:
            return
        
        # Create weighted deciles
        baseline_hh["decile"] = self._get_weighted_deciles(baseline_hh[income_var], weights)
        comparison_hh["decile"] = baseline_hh["decile"]
        
        # Calculate income changes
        baseline_hh["income_change"] = comparison_hh[income_var] - baseline_hh[income_var]
        total_benefit = (baseline_hh["income_change"] * weights).sum()
        
        # Overall (decile = 0)
        overall_impact = USDecileImpact(
            report_id=self.report.id,
            decile=0,
            relative_change=float(((comparison_hh[income_var] * weights).sum() / (baseline_hh[income_var] * weights).sum() - 1) * 100) if (baseline_hh[income_var] * weights).sum() != 0 else 0,
            average_change=float((baseline_hh["income_change"] * weights).sum() / weights.sum()),
            share_of_benefit=100.0
        )
        self.session.add(overall_impact)
        
        # By decile
        for decile in range(1, 11):
            decile_mask = baseline_hh["decile"] == decile
            decile_weights = weights[decile_mask]
            
            if decile_weights.sum() > 0:
                baseline_income = (baseline_hh.loc[decile_mask, income_var] * decile_weights).sum()
                reform_income = (comparison_hh.loc[decile_mask, income_var] * decile_weights).sum()
                income_change = (baseline_hh.loc[decile_mask, "income_change"] * decile_weights).sum()
                
                decile_impact = USDecileImpact(
                    report_id=self.report.id,
                    decile=decile,
                    relative_change=float((reform_income / baseline_income - 1) * 100) if baseline_income != 0 else 0,
                    average_change=float(income_change / decile_weights.sum()),
                    share_of_benefit=float(income_change / total_benefit * 100) if total_benefit != 0 else 0
                )
                self.session.add(decile_impact)
    
    def calculate_poverty_impacts(self, baseline: "USModelOutput", comparison: "USModelOutput") -> None:
        """Calculate poverty impacts using SPM definitions."""
        # Check if poverty variables exist
        baseline_hh = baseline.household
        comparison_hh = comparison.household
        
        poverty_variables = [
            ("in_poverty", "spm"),
            ("in_deep_poverty", "deep"),
        ]
        
        # Check if any poverty variables exist
        poverty_vars_exist = any(pv[0] in baseline_hh.columns for pv in poverty_variables)
        
        if not poverty_vars_exist:
            # Try SPM unit level poverty
            if hasattr(baseline, 'spm_unit') and baseline.spm_unit is not None:
                self._calculate_spm_unit_poverty(baseline, comparison)
            return
        
        # Get person-level data
        baseline_person = baseline.person
        comparison_person = comparison.person
        person_weights = baseline_person["person_weight"]
        
        # Demographic groups
        demographic_groups = ["all", "child", "adult", "senior"]
        
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
            
            # Also get poverty gap if available
            gap_var = poverty_var.replace("in_", "") + "_gap"
            has_gap = gap_var in baseline_hh.columns
            
            if has_gap:
                baseline_person["poverty_gap"] = baseline_person["person_household_id"].map(
                    baseline_hh.set_index("household_id")[gap_var]
                )
                comparison_person["poverty_gap"] = comparison_person["person_household_id"].map(
                    comparison_hh.set_index("household_id")[gap_var]
                )
            
            for group in demographic_groups:
                if group == "all":
                    mask = pd.Series([True] * len(baseline_person))
                elif group == "child" and "age" in baseline_person.columns:
                    mask = baseline_person["age"] < 18
                elif group == "adult" and "age" in baseline_person.columns:
                    mask = (baseline_person["age"] >= 18) & (baseline_person["age"] < 65)
                elif group == "senior" and "age" in baseline_person.columns:
                    mask = baseline_person["age"] >= 65
                else:
                    continue
                
                group_weights = person_weights[mask]
                if group_weights.sum() > 0:
                    poverty_impact = USPovertyImpact(
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
                    
                    # Add poverty gap if available
                    if has_gap:
                        poverty_impact.gap_baseline = float((baseline_person.loc[mask, "poverty_gap"] * group_weights).sum())
                        poverty_impact.gap_reform = float((comparison_person.loc[mask, "poverty_gap"] * group_weights).sum())
                        poverty_impact.gap_change = poverty_impact.gap_reform - poverty_impact.gap_baseline
                    
                    self.session.add(poverty_impact)
    
    def _calculate_spm_unit_poverty(self, baseline: "USModelOutput", comparison: "USModelOutput") -> None:
        """Calculate poverty using SPM unit level data."""
        baseline_spm = baseline.spm_unit
        comparison_spm = comparison.spm_unit
        
        if baseline_spm is None or "in_poverty" not in baseline_spm.columns:
            return
        
        # Get person data for demographics
        baseline_person = baseline.person
        comparison_person = comparison.person
        
        # Map SPM poverty to person level
        baseline_person["in_poverty"] = baseline_person["person_spm_unit_id"].map(
            baseline_spm.set_index("spm_unit_id")["in_poverty"]
        )
        comparison_person["in_poverty"] = comparison_person["person_spm_unit_id"].map(
            comparison_spm.set_index("spm_unit_id")["in_poverty"]
        )
        
        person_weights = baseline_person["person_weight"]
        
        # Calculate for all
        poverty_impact = USPovertyImpact(
            report_id=self.report.id,
            poverty_type="spm",
            demographic_group="all",
            headcount_baseline=float((baseline_person["in_poverty"] * person_weights).sum()),
            headcount_reform=float((comparison_person["in_poverty"] * person_weights).sum()),
            rate_baseline=float((baseline_person["in_poverty"] * person_weights).sum() / person_weights.sum()),
            rate_reform=float((comparison_person["in_poverty"] * person_weights).sum() / person_weights.sum())
        )
        poverty_impact.headcount_change = poverty_impact.headcount_reform - poverty_impact.headcount_baseline
        poverty_impact.rate_change = poverty_impact.rate_reform - poverty_impact.rate_baseline
        self.session.add(poverty_impact)
    
    def calculate_inequality_impacts(self, baseline: "USModelOutput", comparison: "USModelOutput") -> None:
        """Calculate inequality metrics."""
        inequality = USInequalityImpact(report_id=self.report.id)
        
        baseline_hh = baseline.household
        comparison_hh = comparison.household
        weights = baseline_hh["household_weight"]
        
        income_var = "equiv_household_net_income" if "equiv_household_net_income" in baseline_hh.columns else "household_net_income"
        
        if income_var in baseline_hh.columns:
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
            ) if baseline_total != 0 else 0
            inequality.top_10_percent_share_reform = float(
                (comparison_sorted.loc[top_10_mask, income_var] * comparison_sorted.loc[top_10_mask, "household_weight"]).sum() / comparison_total
            ) if comparison_total != 0 else 0
            inequality.top_10_percent_share_change = inequality.top_10_percent_share_reform - inequality.top_10_percent_share_baseline
            
            # Top 1%
            top_1_mask = cumulative_weight <= (total_weight * 0.01)
            inequality.top_1_percent_share_baseline = float(
                (baseline_sorted.loc[top_1_mask, income_var] * baseline_sorted.loc[top_1_mask, "household_weight"]).sum() / baseline_total
            ) if baseline_total != 0 else 0
            inequality.top_1_percent_share_reform = float(
                (comparison_sorted.loc[top_1_mask, income_var] * comparison_sorted.loc[top_1_mask, "household_weight"]).sum() / comparison_total
            ) if comparison_total != 0 else 0
            inequality.top_1_percent_share_change = inequality.top_1_percent_share_reform - inequality.top_1_percent_share_baseline
            
            # Bottom 50%
            bottom_50_mask = cumulative_weight >= (total_weight * 0.5)
            baseline_sorted_asc = baseline_hh.sort_values(income_var, ascending=True)
            comparison_sorted_asc = comparison_hh.sort_values(income_var, ascending=True)
            cumulative_weight_asc = baseline_sorted_asc["household_weight"].cumsum()
            bottom_50_mask = cumulative_weight_asc <= (total_weight * 0.5)
            
            inequality.bottom_50_percent_share_baseline = float(
                (baseline_sorted_asc.loc[bottom_50_mask, income_var] * baseline_sorted_asc.loc[bottom_50_mask, "household_weight"]).sum() / baseline_total
            ) if baseline_total != 0 else 0
            inequality.bottom_50_percent_share_reform = float(
                (comparison_sorted_asc.loc[bottom_50_mask, income_var] * comparison_sorted_asc.loc[bottom_50_mask, "household_weight"]).sum() / comparison_total  
            ) if comparison_total != 0 else 0
            inequality.bottom_50_percent_share_change = inequality.bottom_50_percent_share_reform - inequality.bottom_50_percent_share_baseline
        
        self.session.add(inequality)
    
    def calculate_winners_losers(self, baseline: "USModelOutput", comparison: "USModelOutput") -> None:
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
            income_var = "equiv_household_net_income" if "equiv_household_net_income" in baseline_hh.columns else "household_net_income"
            baseline_hh["decile"] = self._get_weighted_deciles(baseline_hh[income_var], weights)
            
            # Overall (decile = 0)
            overall_wl = USWinnersLosers(
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
                    decile_wl = USWinnersLosers(
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
    
    def calculate_program_impacts(self, baseline: "USModelOutput", comparison: "USModelOutput") -> None:
        """Calculate program-specific impacts."""
        # Programs can be at different entity levels
        tax_unit_programs = [
            ("eitc", "EITC"),
            ("ctc", "Child Tax Credit"),
        ]
        
        spm_unit_programs = [
            ("tanf", "TANF"),
        ]
        
        household_programs = [
            ("snap", "SNAP"),
            ("ssi", "SSI"),
            ("social_security", "Social Security"),
            ("wic", "WIC"),
            ("medicaid", "Medicaid"),
            ("unemployment_compensation", "Unemployment"),
        ]
        
        # Process tax unit programs
        if hasattr(baseline, 'tax_unit'):
            baseline_tu = baseline.tax_unit
            comparison_tu = comparison.tax_unit
            tu_weights = baseline_tu["tax_unit_weight"] if "tax_unit_weight" in baseline_tu.columns else None
            
            for var_name, program_label in tax_unit_programs:
                if var_name not in baseline_tu.columns:
                    continue
                
                self._create_program_impact(
                    var_name, program_label, 
                    baseline_tu, comparison_tu, tu_weights
                )
        
        # Process SPM unit programs
        if hasattr(baseline, 'spm_unit'):
            baseline_spm = baseline.spm_unit
            comparison_spm = comparison.spm_unit
            spm_weights = baseline_spm["spm_unit_weight"] if "spm_unit_weight" in baseline_spm.columns else None
            
            for var_name, program_label in spm_unit_programs:
                if var_name not in baseline_spm.columns:
                    continue
                    
                self._create_program_impact(
                    var_name, program_label,
                    baseline_spm, comparison_spm, spm_weights
                )
        
        # Process household programs
        baseline_hh = baseline.household
        comparison_hh = comparison.household
        weights = baseline_hh["household_weight"]
        
        for var_name, program_label in household_programs:
            if var_name not in baseline_hh.columns:
                continue
                
            self._create_program_impact(
                var_name, program_label,
                baseline_hh, comparison_hh, weights
            )
    
    def _create_program_impact(self, var_name, program_label, baseline_df, comparison_df, weights):
            """Create impact for a single program."""
            if weights is None:
                return  # Skip if no weights available
                
            program_impact = USProgramImpact(
                report_id=self.report.id,
                program_name=program_label
            )
            
            # Calculate total cost
            program_impact.baseline_cost = float((baseline_df[var_name] * weights).sum())
            program_impact.reform_cost = float((comparison_df[var_name] * weights).sum())
            program_impact.cost_change = program_impact.reform_cost - program_impact.baseline_cost
            
            # Calculate number of recipients (entities with positive benefits)
            baseline_recipients = (baseline_df[var_name] > 0) * weights
            comparison_recipients = (comparison_df[var_name] > 0) * weights
            
            program_impact.baseline_recipients = float(baseline_recipients.sum())
            program_impact.reform_recipients = float(comparison_recipients.sum())
            program_impact.recipients_change = program_impact.reform_recipients - program_impact.baseline_recipients
            
            # Calculate average benefit per recipient
            if program_impact.baseline_recipients > 0:
                baseline_recipient_mask = baseline_df[var_name] > 0
                baseline_recipient_weights = weights[baseline_recipient_mask]
                program_impact.baseline_average_benefit = float(
                    (baseline_df.loc[baseline_recipient_mask, var_name] * baseline_recipient_weights).sum() / baseline_recipient_weights.sum()
                )
            else:
                program_impact.baseline_average_benefit = 0
            
            if program_impact.reform_recipients > 0:
                reform_recipient_mask = comparison_df[var_name] > 0
                reform_recipient_weights = weights[reform_recipient_mask]
                program_impact.reform_average_benefit = float(
                    (comparison_df.loc[reform_recipient_mask, var_name] * reform_recipient_weights).sum() / reform_recipient_weights.sum()
                )
            else:
                program_impact.reform_average_benefit = 0
            
            program_impact.average_benefit_change = program_impact.reform_average_benefit - program_impact.baseline_average_benefit
            
            self.session.add(program_impact)
    
    def _get_weighted_deciles(self, values: pd.Series, weights: pd.Series) -> pd.Series:
        """Create weighted deciles for a series of values."""
        # Sort by values
        sorted_indices = values.argsort()
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