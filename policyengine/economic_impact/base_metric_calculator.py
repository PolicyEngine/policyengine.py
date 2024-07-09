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