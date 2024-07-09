from policyengine.economic_impact.inequality_impact.inequality_impact import BaseMetricCalculator
from policyengine_uk import Microsimulation

class MalePoverty(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
        is_male = self.baseline.calculate("is_male")

        baseline_poverty = self.baseline.calculate("in_deep_poverty", map_to="person")
        reform_poverty = self.reformed.calculate("in_deep_poverty", map_to="person")

        baseline = float(baseline_poverty[is_male].mean())
        reform = float(reform_poverty[is_male].mean())
        change = ((reform - baseline) / baseline) * 100

        return {
            "baseline": round(baseline*100,2),
            "reform": round(reform*100,2),
            "change": round(change,1)
        }

class FemalePoverty(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
        is_male = self.baseline.calculate("is_male")

        baseline_poverty = self.baseline.calculate("in_deep_poverty", map_to="person")
        reform_poverty = self.reformed.calculate("in_deep_poverty", map_to="person")

        baseline = float(baseline_poverty[~is_male].mean())
        reform = float(reform_poverty[~is_male].mean())
        change = ((reform - baseline) / baseline) * 100

        return {
            "baseline": round(baseline*100,2),
            "reform": round(reform*100,2),
            "change": round(change,1)
        }
    
class AllPoverty(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
        
        baseline_poverty = self.baseline.calculate("in_deep_poverty", map_to="person")
        reform_poverty = self.reformed.calculate("in_deep_poverty", map_to="person")

        baseline = float(baseline_poverty.mean())
        reform = float(reform_poverty.mean())
        change = ((reform - baseline) / baseline) * 100

        return {
            "baseline": round(baseline*100,2),
            "reform": round(reform*100,2),
            "change": round(change,1)
        }
