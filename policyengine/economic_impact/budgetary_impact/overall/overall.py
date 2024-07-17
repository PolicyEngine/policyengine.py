from policyengine.economic_impact.base_metric_calculator import BaseMetricCalculator
from policyengine_uk import Microsimulation

class BudgetaryImpact(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):

        baseline_total_tax = self.baseline.calculate("household_tax").sum()
        reformed_total_tax = self.reformed.calculate("household_tax").sum()

        tax_revenue_impact = reformed_total_tax - baseline_total_tax

        baseline_total_benefits = self.baseline.calculate("household_benefits").sum()
        reformed_total_benefits = self.reformed.calculate("household_benefits").sum()


        benefit_spending_impact = reformed_total_benefits - baseline_total_benefits

        budgetary_impact = tax_revenue_impact - benefit_spending_impact



        return {
            "budgetary_impact" : round(budgetary_impact,2)
        }

class BenefitSpendingImpact(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):

        baseline_total_benefits = self.baseline.calculate("household_benefits").sum()
        reformed_total_benefits = self.reformed.calculate("household_benefits").sum()


        benefit_spending_impact = reformed_total_benefits - baseline_total_benefits

        

        return {
            "baseline_total_benefits": round(baseline_total_benefits,2),
            "reformed_total_benefits": round(reformed_total_benefits,2),
            "benefit_spending_impact": round(benefit_spending_impact,2)
        }
    
class TaxRevenueImpact(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):

        baseline_total_tax = self.baseline.calculate("household_tax").sum()
        reformed_total_tax = self.reformed.calculate("household_tax").sum()

        tax_revenue_impact = reformed_total_tax - baseline_total_tax
        

        return {
            "baseline_total_tax": round(baseline_total_tax,2),
            "reformed_total_tax": round(reformed_total_tax,2),
            "tax_revenue_impact": round(tax_revenue_impact,2)
        }