from policyengine.economic_impact.base_metric_calculator import BaseMetricCalculator
from policyengine_uk import Microsimulation
from microdf import MicroDataFrame, MicroSeries


class Average(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
        
        baseline_income = MicroSeries(self.baseline.calculate("household_net_income"), weights = self.baseline.calculate("household_weight"))
        reform_income = MicroSeries(self.reformed.calculate("household_net_income") , weights = baseline_income.weights)
        
        decile = self.baseline.calculate("household_income_decile")
        income_change = reform_income - baseline_income
        
        
        avg_income_change_by_decile = (
                income_change.groupby(decile).sum()
                / baseline_income.groupby(decile).count()
            )
        
        
        avg_decile_dict = avg_income_change_by_decile.to_dict()
        result = dict(
                
        average={int(k): v for k, v in avg_decile_dict.items() if k > 0},
         )


        return {
            "average": result["average"],
           
        }