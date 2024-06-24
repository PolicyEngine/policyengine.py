from policyengine_core.reforms import Reform
from .inequality_impact.inequality_impact import GiniCalculator, Top10PctShareCalculator, Top1PctShareCalculator
from typing import Dict

class EconomicImpact:
    """
    A class to calculate economic impact metrics based on different reforms and countries.
    
    Attributes:
        reform (dict): Dictionary representing the reform parameters.
        country (str): Country code in lowercase ('uk' or 'us').
        Microsimulation (type): Class representing the microsimulation engine based on country.
        baseline (Microsimulation): Instance of Microsimulation for baseline scenario.
        reformed (Microsimulation): Instance of Microsimulation for reformed scenario based on given reform.
        metric_calculators (Dict[str, BaseMetricCalculator]): Dictionary mapping metric names to metric calculators.
    """
    
    def __init__(self, reform: dict, country: str) -> None:
        """
        Initialize EconomicImpact with reform parameters and country code.
        
        Args:
            reform (dict): Dictionary representing the reform parameters.
            country (str): Country code in lowercase ('uk' or 'us').
        """
        self.reform = reform
        self.country = country.lower()
        self.Microsimulation = self._get_simulation_class()
        
        # Initialize baseline and reformed simulations
        self.baseline = self.Microsimulation()
        self.reformed = self.Microsimulation(reform=Reform.from_dict(self.reform, country_id=self.country))

        # Set up metric calculators
        self.metric_calculators: Dict[str, object] = {
            "inequality/gini": GiniCalculator(self.baseline, self.reformed),
            "inequality/top_1_pct_share": Top1PctShareCalculator(self.baseline, self.reformed),
            "inequality/top_10_pct_share": Top10PctShareCalculator(self.baseline, self.reformed),
        }

    def _get_simulation_class(self) -> type:
        """
        Get the appropriate Microsimulation class based on the country code.
        
        Returns:
            type: Microsimulation class based on the country.
        
        Raises:
            ValueError: If the country is not supported ('uk' or 'us').
        """
        if self.country == "uk":
            from policyengine_uk import Microsimulation
        elif self.country == "us":
            from policyengine_us import Microsimulation
        else:
            raise ValueError(f"Unsupported country: {self.country}")
        return Microsimulation

    def calculate(self, metric: str) -> dict:
        """
        Calculate the specified economic impact metric.
        
        Args:
            metric (str): Name of the metric to calculate ("inequality/gini", "inequality/top_1_pct_share", "inequality/top_10_pct_share").
        
        Returns:
            dict: Dictionary containing metric values ("baseline", "reform", "change").
        
        Raises:
            ValueError: If the metric is unknown.
        """
        if metric not in self.metric_calculators:
            raise ValueError(f"Unknown metric: {metric}")
        return self.metric_calculators[metric].calculate()
