from policyengine.economic_impact.base_metric_calculator import BaseMetricCalculator
from policyengine_uk import Microsimulation

class IncomeTax(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):

        baseline = self.baseline.calculate("income_tax", map_to="household").sum()
        reform = self.reformed.calculate("income_tax", map_to="household").sum()

        change = ((reform - baseline) / baseline) * 100

        return {
            "baseline": round(baseline,2),
            "reform": round(reform,2),
            "change": round(change,1)
        }

class NationalInsurance(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):

        baseline = self.baseline.calculate("national_insurance", map_to="household").sum()
        reform = self.reformed.calculate("national_insurance", map_to="household").sum()

        change = ((reform - baseline) / baseline) * 100

        return {
            "baseline": round(baseline,2),
            "reform": round(reform,2),
            "change": round(change,1)
        }
    
class Vat(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):

        baseline = self.baseline.calculate("vat", map_to="household").sum()
        reform = self.reformed.calculate("vat", map_to="household").sum()

        change = ((reform - baseline) / baseline) * 100

        return {
            "baseline": round(baseline,2),
            "reform": round(reform,2),
            "change": round(change,1)
        }

class CouncilTax(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):

        baseline = self.baseline.calculate("council_tax", map_to="household").sum()
        reform = self.reformed.calculate("council_tax", map_to="household").sum()

        change = ((reform - baseline) / baseline) * 100

        return {
            "baseline": round(baseline,2),
            "reform": round(reform,2),
            "change": round(change,1)
        }

class FuelDuty(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):

        baseline = self.baseline.calculate("fuel_duty", map_to="household").sum()
        reform = self.reformed.calculate("fuel_duty", map_to="household").sum()

        change = ((reform - baseline) / baseline) * 100

        return {
            "baseline": round(baseline,2),
            "reform": round(reform,2),
            "change": round(change,1)
        }
    
class TaxCredits(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):

        baseline = self.baseline.calculate("tax_credits", map_to="household").sum() * -1
        reform = self.reformed.calculate("tax_credits", map_to="household").sum() * -1

        change = ((reform - baseline) / baseline) * 100

        return {
            "baseline": round(baseline,2),
            "reform": round(reform,2),
            "change": round(change,1)
        }

class UniversalCredit(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):

        baseline = self.baseline.calculate("universal_credit", map_to="household").sum() * -1
        reform = self.reformed.calculate("universal_credit", map_to="household").sum() * -1

        change = ((reform - baseline) / baseline) * 100 

        return {
            "baseline": round(baseline,2),
            "reform": round(reform,2),
            "change": round(change,1)
        }

class ChildBenefit(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):

        baseline = self.baseline.calculate("child_benefit", map_to="household").sum() * -1
        reform = self.reformed.calculate("child_benefit", map_to="household").sum() * -1

        change = ((reform - baseline) / baseline) * 100 

        return {
            "baseline": round(baseline,2),
            "reform": round(reform,2),
            "change": round(change,1)
        }
    
class StatePension(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):

        baseline = self.baseline.calculate("state_pension", map_to="household").sum()  * -1
        reform = self.reformed.calculate("state_pension", map_to="household").sum()  * -1

        change = ((reform - baseline) / baseline) * 100 

        return {
            "baseline": round(baseline,2),
            "reform": round(reform,2),
            "change": round(change,1)
        }

class PensionCredit(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):

        baseline = self.baseline.calculate("pension_credit", map_to="household").sum()  * -1
        reform = self.reformed.calculate("pension_credit", map_to="household").sum()  * -1

        change = ((reform - baseline) / baseline) * 100

        return {
            "baseline": round(baseline,2),
            "reform": round(reform,2),
            "change": round(change,1)
        }