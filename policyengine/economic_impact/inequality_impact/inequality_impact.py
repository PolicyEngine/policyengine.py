from typing import Union

class BaseMetricCalculator:
    """
    Base class for calculating metrics based on baseline and reformed data.
    
    Attributes:
        baseline (object): Object representing baseline data.
        reformed (object): Object representing reformed data.
    """
    
    def __init__(self, baseline: object, reformed: object) -> None:
        """
        Initialize with baseline and reformed data objects.
        
        Args:
            baseline (object): Object representing baseline data.
            reformed (object): Object representing reformed data.
        """
        self.baseline = baseline
        self.reformed = reformed

    def calculate_baseline(self, variable: str, period: int = 2024, map_to: str = "person") -> Union[float, int]:
        """
        Calculate baseline metric value.
        
        Args:
            variable (str): Variable to calculate.
            period (int): Year or period for calculation (default: 2024).
            map_to (str): Mapping type (default: "person").
        
        Returns:
            Union[float, int]: Calculated metric value.
        """
        return self.baseline.calculate(variable, period=period, map_to=map_to)
    
    def calculate_reformed(self, variable: str, period: int = 2024, map_to: str = "person") -> Union[float, int]:
        """
        Calculate reformed metric value.
        
        Args:
            variable (str): Variable to calculate.
            period (int): Year or period for calculation (default: 2024).
            map_to (str): Mapping type (default: "person").
        
        Returns:
            Union[float, int]: Calculated metric value.
        """
        return self.reformed.calculate(variable, period=period, map_to=map_to)

class GiniCalculator(BaseMetricCalculator):
    """
    Calculate Gini coefficient metrics based on baseline and reformed data.
    Inherits from BaseMetricCalculator.
    """
    
    def calculate(self) -> dict:
        """
        Calculate Gini coefficient metrics.
        
        Returns:
            dict: Dictionary containing "baseline", "reform", and "change" values.
        """
        baseline_person = self.calculate_baseline("household_net_income")
        reformed_person = self.calculate_reformed("household_net_income")
        
        baseline_value = baseline_person.gini()
        reformed_value = reformed_person.gini()
        change_value = reformed_value - baseline_value
        
        return {
            "baseline": baseline_value,
            "reform": reformed_value,
            "change": change_value
        }

class Top1PctShareCalculator(BaseMetricCalculator):
    """
    Calculate top 1% income share metrics based on baseline and reformed data.
    Inherits from BaseMetricCalculator.
    """
    
    def calculate(self) -> dict:
        """
        Calculate top 1% income share metrics.
        
        Returns:
            dict: Dictionary containing "baseline", "reform", and "change" values.
        """
        baseline_person = self.calculate_baseline("household_net_income")
        reformed_person = self.calculate_reformed("household_net_income")
        
        baseline_value = baseline_person.top_1_pct_share()
        reformed_value = reformed_person.top_1_pct_share()
        change_value = reformed_value - baseline_value
        
        return {
            "baseline": baseline_value,
            "reform": reformed_value,
            "change": change_value
        }

class Top10PctShareCalculator(BaseMetricCalculator):
    """
    Calculate top 10% income share metrics based on baseline and reformed data.
    Inherits from BaseMetricCalculator.
    """
    
    def calculate(self) -> dict:
        """
        Calculate top 10% income share metrics.
        
        Returns:
            dict: Dictionary containing "baseline", "reform", and "change" values.
        """
        baseline_person = self.calculate_baseline("household_net_income")
        reformed_person = self.calculate_reformed("household_net_income")
        
        baseline_value = baseline_person.top_10_pct_share()
        reformed_value = reformed_person.top_10_pct_share()
        change_value = reformed_value - baseline_value
        
        return {
            "baseline": baseline_value,
            "reform": reformed_value,
            "change": change_value
        }
