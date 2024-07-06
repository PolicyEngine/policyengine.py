from policyengine.economic_impact.base_metric_calculator import BaseMetricCalculator
from policyengine_uk import Microsimulation

class ChildPoverty(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
        age = self.baseline.calculate("age")

        baseline_poverty = self.baseline.calculate("in_deep_poverty", map_to="person")
        reform_poverty = self.reformed.calculate("in_deep_poverty", map_to="person")

        baseline = float(baseline_poverty[age < 18].mean())
        reform = float(reform_poverty[age < 18].mean())
        change = ((reform - baseline) / baseline) * 100

        return {
            "baseline": round(baseline*100,2),
            "reform": round(reform*100,2),
            "change": round(change,1)
        }

class AdultPoverty(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
        age = self.baseline.calculate("age")

        baseline_poverty = self.baseline.calculate("in_deep_poverty", map_to="person")
        reform_poverty = self.reformed.calculate("in_deep_poverty", map_to="person")

        baseline = float(baseline_poverty[(age >= 18) & (age < 65)].mean())
        reform = float(reform_poverty[(age >= 18) & (age < 65)].mean())
        change = ((reform - baseline) / baseline) * 100

        return {
            "baseline": round(baseline*100,2),
            "reform": round(reform*100,2),
            "change": round(change,1)
        }
    
class SeniorPoverty(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
        age = self.baseline.calculate("age")

        baseline_poverty = self.baseline.calculate("in_deep_poverty", map_to="person")
        reform_poverty = self.reformed.calculate("in_deep_poverty", map_to="person")

        baseline = float(baseline_poverty[age >= 65].mean())
        reform = float(reform_poverty[age >= 65].mean())
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