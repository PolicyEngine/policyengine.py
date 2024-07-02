from policyengine_core.reforms import Reform
from typing import Dict, Union

class BaseMetricCalculator:
    """
    Base class for calculating metrics based on baseline and reformed data.
    
    Attributes:
        baseline (object): Object representing baseline data.
        reformed (object): Object representing reformed data.
    """
    def __init__(self, baseline: object, reformed: object, default_period: int = 2024) -> None:
        """
        Initialize with baseline and reformed data objects.
        
        Args:
            baseline (object): Object representing baseline data.
            reformed (object): Object representing reformed data.
        """
        self.baseline = baseline
        self.reformed = reformed
        self.default_period = default_period
        self.baseline.default_calculation_period = default_period
        self.reformed.default_calculation_period = default_period

    def calculate_baseline(self, variable: str, period: int = None) -> Union[float, int]:
        """
        Calculate baseline metric value.
        
        Args:
            variable (str): Variable to calculate.
            period (int): Year or period for calculation (default: 2024).
        
        Returns:
            Union[float, int]: Calculated metric value.
        """
        if period is None:
            period = self.default_period
        return self.baseline.calculate(variable, period=period)
    
    def calculate_reformed(self, variable: str, period: int = None) -> Union[float, int]:
        """
        Calculate reformed metric value.
        
        Args:
            variable (str): Variable to calculate.
            period (int): Year or period for calculation (default: 2024).
        
        Returns:
            Union[float, int]: Calculated metric value.
        """
        if period is None:
            period = self.default_period
        return self.reformed.calculate(variable, period=period)

class GiniCalculator(BaseMetricCalculator):
    """
    Calculate Gini coefficient metrics based on baseline and reformed data.
    Inherits from BaseMetricCalculator.
    """
    def calculate(self) -> dict:
        baseline_personal_hh_equiv_income = self.calculate_baseline("equiv_household_net_income")
        baseline_household_count_people = self.calculate_baseline("household_count_people")
        baseline_personal_hh_equiv_income.weights *= baseline_household_count_people
        
        reformed_personal_hh_equiv_income = self.calculate_reformed("equiv_household_net_income")
        reformed_household_count_people = self.calculate_reformed("household_count_people")
        reformed_personal_hh_equiv_income.weights *= reformed_household_count_people
        
        try:
            baseline_value = baseline_personal_hh_equiv_income.gini()
        except:
            print("WARNING: Baseline Gini index calculations resulted in an error: returning 0.4, but this is inaccurate.")
            baseline_value = 0.4
        
        try:
            reformed_value = reformed_personal_hh_equiv_income.gini()
        except:
            print("WARNING: Reformed Gini index calculations resulted in an error: returning 0.4, but this is inaccurate.")
            reformed_value = 0.4

        change_value = reformed_value - baseline_value
        change_perc = (change_value / baseline_value) * 100
        
        return {
            "baseline": baseline_value,
            "reform": reformed_value,
            "change": change_value,
            "change_percentage": change_perc
        }

class Top1PctShareCalculator(BaseMetricCalculator):
    """
    Calculate top 1% income share metrics based on baseline and reformed data.
    Inherits from BaseMetricCalculator.
    """
    def calculate(self) -> dict:
        baseline_personal_hh_equiv_income = self.calculate_baseline("equiv_household_net_income")
        baseline_household_count_people = self.calculate_baseline("household_count_people")
        baseline_personal_hh_equiv_income.weights *= baseline_household_count_people
        
        reformed_personal_hh_equiv_income = self.calculate_reformed("equiv_household_net_income")
        reformed_household_count_people = self.calculate_reformed("household_count_people")
        reformed_personal_hh_equiv_income.weights *= reformed_household_count_people
        
        in_top_1_pct = baseline_personal_hh_equiv_income.percentile_rank() == 100
        in_top_1_pct = reformed_personal_hh_equiv_income.percentile_rank() == 100
        
        
        baseline_personal_hh_equiv_income.weights /= baseline_household_count_people
        reformed_personal_hh_equiv_income.weights /= reformed_household_count_people

        baseline_top_1_pct_share = (
            baseline_personal_hh_equiv_income[in_top_1_pct].sum()
            / baseline_personal_hh_equiv_income.sum()
        )

        
        reformed_top_1_pct_share = (
            reformed_personal_hh_equiv_income[in_top_1_pct].sum()
            / reformed_personal_hh_equiv_income.sum()
        )
        
        
        change_value = reformed_top_1_pct_share - baseline_top_1_pct_share
        change_perc = (change_value / baseline_top_1_pct_share) * 100

        return {
            "baseline": baseline_top_1_pct_share,
            "reform": reformed_top_1_pct_share,
            "change": change_value,
            "change_percentage": change_perc
        }

class Top10PctShareCalculator(BaseMetricCalculator):
    """
    Calculate top 10% income share metrics based on baseline and reformed data.
    Inherits from BaseMetricCalculator.
    """
    def calculate(self) -> dict:
        baseline_personal_hh_equiv_income = self.calculate_baseline("equiv_household_net_income")
        baseline_household_count_people = self.calculate_baseline("household_count_people")
        baseline_personal_hh_equiv_income.weights *= baseline_household_count_people
        
        reformed_personal_hh_equiv_income = self.calculate_reformed("equiv_household_net_income")
        reformed_household_count_people = self.calculate_reformed("household_count_people")
        reformed_personal_hh_equiv_income.weights *= reformed_household_count_people
        
        in_top_10_pct = baseline_personal_hh_equiv_income.decile_rank() == 10
        in_top_10_pct = reformed_personal_hh_equiv_income.decile_rank() == 10
        

        reformed_personal_hh_equiv_income.weights /= reformed_household_count_people
        baseline_personal_hh_equiv_income.weights /= baseline_household_count_people
        
        baseline_top_10_pct_share = (
            baseline_personal_hh_equiv_income[in_top_10_pct].sum()
            / baseline_personal_hh_equiv_income.sum()
        )

        reformed_top_10_pct_share = (
            reformed_personal_hh_equiv_income[in_top_10_pct].sum()
            / reformed_personal_hh_equiv_income.sum()
        )

        change_value = reformed_top_10_pct_share - baseline_top_10_pct_share
        change_perc = (change_value / baseline_top_10_pct_share) * 100

        return {
            "baseline": baseline_top_10_pct_share,
            "reform": reformed_top_10_pct_share,
            "change": change_value,
            "change_percentage": change_perc
        }
