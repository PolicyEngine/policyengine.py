from policyengine.economic_impact.base_metric_calculator import BaseMetricCalculator
from policyengine_uk import Microsimulation
from policyengine_core.reforms import Reform
from microdf import MicroSeries
import numpy as np

class IncomeEffect(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
    # Calculate household weight
         household_weight = self.baseline.calculate("household_weight")
         
         # Calculate household count people
         household_count_people_baseline = self.baseline.calculate("household_count_people")
         household_count_people_reformed = self.reformed.calculate("household_count_people")
     
         # Initialize income LSR
         income_lsr_hh_baseline = (household_count_people_baseline * 0).astype(float).tolist()
         income_lsr_hh_reformed = (household_count_people_reformed * 0).astype(float).tolist()
         
         
         # Check if behavioral response exists and update income LSR
         if "employment_income_behavioral_response" in self.baseline.tax_benefit_system.variables:
             if any(self.baseline.calculate("employment_income_behavioral_response") != 0):
                 income_elasticity_baseline = self.baseline.calculate("income_elasticity_lsr", map_to="household")
                 income_lsr_hh_baseline = income_elasticity_baseline.astype(float).tolist()
         
         if "employment_income_behavioral_response" in self.reformed.tax_benefit_system.variables:
             if any(self.reformed.calculate("employment_income_behavioral_response") != 0):
                 income_elasticity_reformed = self.reformed.calculate("income_elasticity_lsr", map_to="household")
                 income_lsr_hh_reformed = income_elasticity_reformed.astype(float).tolist()
     
         
         # Calculate substitution LSR
         substitution_lsr_hh_baseline = (household_count_people_baseline * 0).astype(float).tolist()
         if "employment_income_behavioral_response" in self.baseline.tax_benefit_system.variables:
             if any(self.baseline.calculate("employment_income_behavioral_response") != 0):
                 substitution_lsr_hh_baseline = (
                     self.baseline.calculate("substitution_elasticity_lsr", map_to="household")
                     .astype(float)
                     .tolist()
                 )
         
         substitution_lsr_hh_reformed = (household_count_people_reformed * 0).astype(float).tolist()
         if "employment_income_behavioral_response" in self.reformed.tax_benefit_system.variables:
             if any(self.reformed.calculate("employment_income_behavioral_response") != 0):
                 substitution_lsr_hh_reformed = (
                     self.reformed.calculate("substitution_elasticity_lsr", map_to="household")
                     .astype(float)
                     .tolist()
                 )
         
         
         substitution_lsr_hh = np.array(substitution_lsr_hh_reformed) - np.array(substitution_lsr_hh_baseline)
         income_lsr_hh = np.array(income_lsr_hh_reformed) - np.array(income_lsr_hh_baseline)
     
         # Convert to MicroSeries
         income_lsr_hh = MicroSeries(income_lsr_hh, weights=household_weight)
         substitution_lsr_hh = MicroSeries(substitution_lsr_hh, weights=household_weight)
     
         decile = np.array(self.baseline.calculate("household_income_decile"))
         total_lsr_hh = substitution_lsr_hh + income_lsr_hh
     
         # Calculate earnings
         emp_income = MicroSeries(
             self.baseline.calculate("employment_income", map_to="household").astype(float).tolist(),
             weights=household_weight
         )
         
         self_emp_income = MicroSeries(
             self.baseline.calculate("self_employment_income", map_to="household").astype(float).tolist(),
             weights=household_weight
         )
     
         earnings = emp_income + self_emp_income
         original_earnings = earnings - total_lsr_hh
     
         # Calculate decile relative
         decile_rel = dict(
             income=(
                 income_lsr_hh.groupby(decile).sum()
                 / original_earnings.groupby(decile).sum()
             ).to_dict(),
         )
     
         
     
         decile_rel["income"] = {int(k): round(v *100,2) for k, v in decile_rel["income"].items() if k > 0}
    
     
         return {
             "income": decile_rel["income"]
         }