"""Storage-agnostic report handler.

This module provides business logic for working with reports using
Pydantic models, independent of storage implementation.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import uuid

from ..data_models import (
    ReportMetadataModel,
    EconomicImpactModel,
    BudgetImpactModel,
    HouseholdIncomeImpactModel,
    DecileImpactModel,
    PovertyImpactModel,
    InequalityImpactModel,
    SimulationDataModel
)


class ReportHandler:
    """Handles report operations using Pydantic models."""
    
    @staticmethod
    def create_report_metadata(
        name: str,
        country: str,
        baseline_simulation_id: str,
        comparison_simulation_id: str,
        year: Optional[int] = None,
        report_id: Optional[str] = None,
        status: str = "pending",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> ReportMetadataModel:
        """Create report metadata.
        
        Args:
            name: Report name
            country: Country code
            baseline_simulation_id: ID of baseline simulation
            comparison_simulation_id: ID of comparison/reform simulation
            year: Report year
            report_id: Unique ID (generated if not provided)
            status: Report status
            description: Human-readable description
            tags: List of tags for filtering
            
        Returns:
            ReportMetadataModel instance
        """
        return ReportMetadataModel(
            id=report_id or str(uuid.uuid4()),
            name=name,
            country=country.lower(),
            year=year or datetime.now().year,
            baseline_simulation_id=baseline_simulation_id,
            comparison_simulation_id=comparison_simulation_id,
            status=status,
            description=description,
            tags=tags or []
        )
    
    @staticmethod
    def calculate_economic_impact(
        baseline_data: SimulationDataModel,
        reform_data: SimulationDataModel,
        report_metadata: ReportMetadataModel,
        country: str = "uk"
    ) -> EconomicImpactModel:
        """Calculate full economic impact from baseline and reform data.
        
        Args:
            baseline_data: Baseline simulation data
            reform_data: Reform simulation data
            report_metadata: Report metadata
            country: Country code for specific calculations
            
        Returns:
            EconomicImpactModel with calculated impacts
        """
        # Calculate individual impact components
        budget_impact = ReportHandler.calculate_budget_impact(
            baseline_data, reform_data, country
        )
        
        household_income = ReportHandler.calculate_household_income_impact(
            baseline_data, reform_data
        )
        
        decile_impacts = ReportHandler.calculate_decile_impacts(
            baseline_data, reform_data
        )
        
        poverty_impacts = ReportHandler.calculate_poverty_impacts(
            baseline_data, reform_data, country
        )
        
        inequality_impact = ReportHandler.calculate_inequality_impact(
            baseline_data, reform_data
        )
        
        return EconomicImpactModel(
            report_metadata=report_metadata,
            budget_impact=budget_impact,
            household_income=household_income,
            decile_impacts=decile_impacts,
            poverty_impacts=poverty_impacts,
            inequality_impact=inequality_impact
        )
    
    @staticmethod
    def calculate_budget_impact(
        baseline_data: SimulationDataModel,
        reform_data: SimulationDataModel,
        country: str = "uk"
    ) -> BudgetImpactModel:
        """Calculate government budget impact.
        
        Args:
            baseline_data: Baseline simulation data
            reform_data: Reform simulation data
            country: Country code
            
        Returns:
            BudgetImpactModel with calculated impacts
        """
        baseline_household = baseline_data.household
        reform_household = reform_data.household
        
        # Calculate government balance (simplified)
        baseline_balance = 0.0
        reform_balance = 0.0
        
        if "gov_balance" in baseline_household.columns:
            weights = baseline_household.get("household_weight", 1)
            baseline_balance = (baseline_household["gov_balance"] * weights).sum()
            reform_balance = (reform_household["gov_balance"] * weights).sum()
        
        # Calculate tax revenues
        baseline_tax = 0.0
        reform_tax = 0.0
        
        tax_columns = [col for col in baseline_household.columns if "tax" in col.lower()]
        for col in tax_columns:
            if col in baseline_household.columns:
                weights = baseline_household.get("household_weight", 1)
                baseline_tax += (baseline_household[col] * weights).sum()
                reform_tax += (reform_household[col] * weights).sum()
        
        # Calculate government spending
        baseline_spending = 0.0
        reform_spending = 0.0
        
        benefit_columns = [col for col in baseline_household.columns if "benefit" in col.lower()]
        for col in benefit_columns:
            if col in baseline_household.columns:
                weights = baseline_household.get("household_weight", 1)
                baseline_spending += (baseline_household[col] * weights).sum()
                reform_spending += (reform_household[col] * weights).sum()
        
        return BudgetImpactModel(
            gov_balance_baseline=baseline_balance,
            gov_balance_reform=reform_balance,
            gov_balance_change=reform_balance - baseline_balance,
            gov_tax_baseline=baseline_tax,
            gov_tax_reform=reform_tax,
            gov_tax_change=reform_tax - baseline_tax,
            gov_spending_baseline=baseline_spending,
            gov_spending_reform=reform_spending,
            gov_spending_change=reform_spending - baseline_spending
        )
    
    @staticmethod
    def calculate_household_income_impact(
        baseline_data: SimulationDataModel,
        reform_data: SimulationDataModel
    ) -> HouseholdIncomeImpactModel:
        """Calculate household income impact.
        
        Args:
            baseline_data: Baseline simulation data
            reform_data: Reform simulation data
            
        Returns:
            HouseholdIncomeImpactModel with calculated impacts
        """
        baseline_household = baseline_data.household
        reform_household = reform_data.household
        
        weights = baseline_household.get("household_weight", 1)
        
        # Calculate market income
        baseline_market = 0.0
        reform_market = 0.0
        
        if "household_market_income" in baseline_household.columns:
            baseline_market = (baseline_household["household_market_income"] * weights).sum()
            reform_market = (reform_household["household_market_income"] * weights).sum()
        
        # Calculate net income
        baseline_net = 0.0
        reform_net = 0.0
        
        if "household_net_income" in baseline_household.columns:
            baseline_net = (baseline_household["household_net_income"] * weights).sum()
            reform_net = (reform_household["household_net_income"] * weights).sum()
        
        return HouseholdIncomeImpactModel(
            household_market_income_baseline=baseline_market,
            household_market_income_reform=reform_market,
            household_market_income_change=reform_market - baseline_market,
            household_net_income_baseline=baseline_net,
            household_net_income_reform=reform_net,
            household_net_income_change=reform_net - baseline_net
        )
    
    @staticmethod
    def calculate_decile_impacts(
        baseline_data: SimulationDataModel,
        reform_data: SimulationDataModel
    ) -> List[DecileImpactModel]:
        """Calculate impacts by income decile.
        
        Args:
            baseline_data: Baseline simulation data
            reform_data: Reform simulation data
            
        Returns:
            List of DecileImpactModel instances
        """
        baseline_household = baseline_data.household
        reform_household = reform_data.household
        
        impacts = []
        
        # Check if we have income data
        if "household_net_income" not in baseline_household.columns:
            return impacts
        
        # Calculate deciles based on baseline income
        baseline_household["decile"] = pd.qcut(
            baseline_household["household_net_income"],
            q=10,
            labels=range(1, 11),
            duplicates='drop'
        )
        reform_household["decile"] = baseline_household["decile"]
        
        # Calculate impact for each decile
        for decile in range(1, 11):
            decile_mask = baseline_household["decile"] == decile
            
            baseline_income = baseline_household.loc[decile_mask, "household_net_income"]
            reform_income = reform_household.loc[decile_mask, "household_net_income"]
            weights = baseline_household.loc[decile_mask, "household_weight"].fillna(1)
            
            # Calculate average change
            baseline_avg = (baseline_income * weights).sum() / weights.sum()
            reform_avg = (reform_income * weights).sum() / weights.sum()
            
            # Calculate relative change
            relative_change = ((reform_avg - baseline_avg) / baseline_avg * 100) if baseline_avg != 0 else 0
            
            # Calculate winner/loser percentages
            income_change = reform_income - baseline_income
            total_weight = weights.sum()
            
            gain_5 = ((income_change > baseline_income * 0.05) * weights).sum() / total_weight * 100
            gain_1 = ((income_change > baseline_income * 0.01) * weights).sum() / total_weight * 100
            no_change = ((abs(income_change) < baseline_income * 0.01) * weights).sum() / total_weight * 100
            lose_1 = ((income_change < -baseline_income * 0.01) * weights).sum() / total_weight * 100
            lose_5 = ((income_change < -baseline_income * 0.05) * weights).sum() / total_weight * 100
            
            impacts.append(DecileImpactModel(
                decile=decile,
                decile_type="income",
                relative_change=relative_change,
                average_change=reform_avg - baseline_avg,
                gain_more_than_5_percent=gain_5,
                gain_more_than_1_percent=gain_1,
                no_change=no_change,
                lose_less_than_1_percent=lose_1,
                lose_less_than_5_percent=lose_5,
                lose_more_than_5_percent=lose_5
            ))
        
        return impacts
    
    @staticmethod
    def calculate_poverty_impacts(
        baseline_data: SimulationDataModel,
        reform_data: SimulationDataModel,
        country: str = "uk"
    ) -> List[PovertyImpactModel]:
        """Calculate poverty impacts.
        
        Args:
            baseline_data: Baseline simulation data
            reform_data: Reform simulation data
            country: Country code
            
        Returns:
            List of PovertyImpactModel instances
        """
        impacts = []
        
        # Get poverty line variable name based on country
        poverty_vars = {
            "uk": ["in_poverty", "in_absolute_poverty", "in_relative_poverty"],
            "us": ["in_spm_poverty", "in_poverty", "in_deep_poverty"]
        }
        
        var_names = poverty_vars.get(country.lower(), ["in_poverty"])
        
        for var_name in var_names:
            if var_name not in baseline_data.person.columns:
                continue
            
            # Calculate for all demographic groups
            for group in ["all", "child", "adult", "senior"]:
                baseline_person = baseline_data.person
                reform_person = reform_data.person
                
                # Apply demographic filter
                if group == "child":
                    mask = baseline_person.get("age", 0) < 18
                elif group == "adult":
                    mask = (baseline_person.get("age", 0) >= 18) & (baseline_person.get("age", 0) < 65)
                elif group == "senior":
                    mask = baseline_person.get("age", 0) >= 65
                else:
                    mask = pd.Series([True] * len(baseline_person))
                
                baseline_poverty = baseline_person.loc[mask, var_name]
                reform_poverty = reform_person.loc[mask, var_name]
                weights = baseline_person.loc[mask, "person_weight"].fillna(1)
                
                # Calculate rates and headcounts
                total_weight = weights.sum()
                baseline_headcount = (baseline_poverty * weights).sum()
                reform_headcount = (reform_poverty * weights).sum()
                
                baseline_rate = baseline_headcount / total_weight if total_weight > 0 else 0
                reform_rate = reform_headcount / total_weight if total_weight > 0 else 0
                
                impacts.append(PovertyImpactModel(
                    poverty_type=var_name.replace("in_", "").replace("_poverty", ""),
                    demographic_group=group,
                    headcount_baseline=baseline_headcount,
                    headcount_reform=reform_headcount,
                    headcount_change=reform_headcount - baseline_headcount,
                    rate_baseline=baseline_rate,
                    rate_reform=reform_rate,
                    rate_change=reform_rate - baseline_rate
                ))
        
        return impacts
    
    @staticmethod
    def calculate_inequality_impact(
        baseline_data: SimulationDataModel,
        reform_data: SimulationDataModel
    ) -> InequalityImpactModel:
        """Calculate inequality impacts.
        
        Args:
            baseline_data: Baseline simulation data
            reform_data: Reform simulation data
            
        Returns:
            InequalityImpactModel with calculated impacts
        """
        baseline_household = baseline_data.household
        reform_household = reform_data.household
        
        # Check if we have income data
        if "household_net_income" not in baseline_household.columns:
            return InequalityImpactModel()
        
        weights = baseline_household.get("household_weight", 1)
        
        # Calculate Gini coefficient
        baseline_gini = ReportHandler._calculate_gini(
            baseline_household["household_net_income"], weights
        )
        reform_gini = ReportHandler._calculate_gini(
            reform_household["household_net_income"], weights
        )
        
        # Calculate income shares
        baseline_shares = ReportHandler._calculate_income_shares(
            baseline_household["household_net_income"], weights
        )
        reform_shares = ReportHandler._calculate_income_shares(
            reform_household["household_net_income"], weights
        )
        
        return InequalityImpactModel(
            gini_baseline=baseline_gini,
            gini_reform=reform_gini,
            gini_change=reform_gini - baseline_gini,
            top_10_percent_share_baseline=baseline_shares["top_10"],
            top_10_percent_share_reform=reform_shares["top_10"],
            top_10_percent_share_change=reform_shares["top_10"] - baseline_shares["top_10"],
            top_1_percent_share_baseline=baseline_shares["top_1"],
            top_1_percent_share_reform=reform_shares["top_1"],
            top_1_percent_share_change=reform_shares["top_1"] - baseline_shares["top_1"],
            bottom_50_percent_share_baseline=baseline_shares["bottom_50"],
            bottom_50_percent_share_reform=reform_shares["bottom_50"],
            bottom_50_percent_share_change=reform_shares["bottom_50"] - baseline_shares["bottom_50"]
        )
    
    @staticmethod
    def _calculate_gini(income: pd.Series, weights: pd.Series) -> float:
        """Calculate Gini coefficient.
        
        Args:
            income: Income values
            weights: Population weights
            
        Returns:
            Gini coefficient (0 to 1)
        """
        # Sort by income
        sorted_indices = income.argsort()
        sorted_income = income.iloc[sorted_indices]
        sorted_weights = weights.iloc[sorted_indices]
        
        # Calculate cumulative shares
        cumsum_weights = sorted_weights.cumsum()
        cumsum_weighted_income = (sorted_income * sorted_weights).cumsum()
        
        total_weights = sorted_weights.sum()
        total_income = (sorted_income * sorted_weights).sum()
        
        # Calculate Gini using trapezoid formula
        if total_income == 0 or total_weights == 0:
            return 0.0
        
        cumsum_weights_pct = cumsum_weights / total_weights
        cumsum_income_pct = cumsum_weighted_income / total_income
        
        # Add origin point
        cumsum_weights_pct = pd.concat([pd.Series([0]), cumsum_weights_pct])
        cumsum_income_pct = pd.concat([pd.Series([0]), cumsum_income_pct])
        
        # Calculate area under Lorenz curve
        area_under_lorenz = ((cumsum_weights_pct[1:] - cumsum_weights_pct[:-1]) * 
                            (cumsum_income_pct[1:] + cumsum_income_pct[:-1]) / 2).sum()
        
        # Gini = 1 - 2 * area_under_lorenz
        return 1 - 2 * area_under_lorenz
    
    @staticmethod
    def _calculate_income_shares(income: pd.Series, weights: pd.Series) -> Dict[str, float]:
        """Calculate income shares for different percentiles.
        
        Args:
            income: Income values
            weights: Population weights
            
        Returns:
            Dictionary with income shares for top 1%, top 10%, bottom 50%
        """
        # Sort by income
        sorted_indices = income.argsort()
        sorted_income = income.iloc[sorted_indices]
        sorted_weights = weights.iloc[sorted_indices]
        
        cumsum_weights = sorted_weights.cumsum()
        total_weights = sorted_weights.sum()
        total_income = (sorted_income * sorted_weights).sum()
        
        if total_income == 0 or total_weights == 0:
            return {"top_1": 0.0, "top_10": 0.0, "bottom_50": 0.0}
        
        # Find cutoff points
        p50_cutoff = total_weights * 0.5
        p90_cutoff = total_weights * 0.9
        p99_cutoff = total_weights * 0.99
        
        # Calculate shares
        bottom_50_mask = cumsum_weights <= p50_cutoff
        top_10_mask = cumsum_weights > p90_cutoff
        top_1_mask = cumsum_weights > p99_cutoff
        
        bottom_50_share = (sorted_income[bottom_50_mask] * sorted_weights[bottom_50_mask]).sum() / total_income
        top_10_share = (sorted_income[top_10_mask] * sorted_weights[top_10_mask]).sum() / total_income
        top_1_share = (sorted_income[top_1_mask] * sorted_weights[top_1_mask]).sum() / total_income
        
        return {
            "top_1": top_1_share,
            "top_10": top_10_share,
            "bottom_50": bottom_50_share
        }
    
    @staticmethod
    def validate_report_metadata(metadata: ReportMetadataModel) -> bool:
        """Validate report metadata.
        
        Args:
            metadata: ReportMetadataModel to validate
            
        Returns:
            True if valid, raises exception otherwise
        """
        if not metadata.name:
            raise ValueError("Report must have a name")
        
        if not metadata.country:
            raise ValueError("Report must have a country")
        
        if not metadata.baseline_simulation_id:
            raise ValueError("Report must have a baseline simulation ID")
        
        if not metadata.comparison_simulation_id:
            raise ValueError("Report must have a comparison simulation ID")
        
        valid_statuses = ["pending", "running", "completed", "failed"]
        if metadata.status not in valid_statuses:
            raise ValueError(f"Invalid status: {metadata.status}")
        
        return True