from policyengine.economic_impact.base_metric_calculator import BaseMetricCalculator
from policyengine_uk import Microsimulation
from policyengine_core.reforms import Reform
from microdf import MicroSeries
import numpy as np


class IncomeLSR(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
        income_lsr_baseline = 0
        income_lsr_reformed = 0
        
        if "employment_income_behavioral_response" in self.baseline.tax_benefit_system.variables:
            if any(self.baseline.calculate("employment_income_behavioral_response") != 0):
                income_lsr_baseline = self.baseline.calculate("income_elasticity_lsr").sum()
    
        if "employment_income_behavioral_response" in self.reformed.tax_benefit_system.variables:
            if any(self.reformed.calculate("employment_income_behavioral_response") != 0):
                income_lsr_reformed = self.reformed.calculate("income_elasticity_lsr").sum()
    
        income_lsr = income_lsr_reformed - income_lsr_baseline        
        # Convert to billions and round to 2 decimal places
        income_lsr_billion = round(income_lsr / 1e9, 2)
        
        return {
            "income_lsr": income_lsr_billion
        }

class SubstitutionLSR(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
        substitution_lsr_baseline = 0
        substitution_lsr_reformed = 0
        
        if "employment_income_behavioral_response" in self.baseline.tax_benefit_system.variables:
            if any(self.baseline.calculate("employment_income_behavioral_response") != 0):
                substitution_lsr_baseline = self.baseline.calculate("substitution_elasticity_lsr").sum()
    
        if "employment_income_behavioral_response" in self.reformed.tax_benefit_system.variables:
            if any(self.reformed.calculate("employment_income_behavioral_response") != 0):
                substitution_lsr_reformed = self.reformed.calculate("substitution_elasticity_lsr").sum()
    
        substitution_lsr = substitution_lsr_reformed - substitution_lsr_baseline
        # Convert to billions and round to 2 decimal places
        substitution_lsr_billion = round(substitution_lsr / 1e9, 2)
        
        return {
            "substitution_lsr": substitution_lsr_billion
        }

class NetLSRChange(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
        income_result = IncomeLSR(baseline=self.baseline, reformed=self.reformed).calculate()
        substitution_result = SubstitutionLSR(baseline=self.baseline, reformed=self.reformed).calculate()
        
        income_value = income_result["income_lsr"]
        substitution_value = substitution_result["substitution_lsr"]

        net_change = (income_value + substitution_value)
        # Round to 2 decimal places
        net_change_billion = round(net_change, 2)

        return {"net_change": net_change_billion}
