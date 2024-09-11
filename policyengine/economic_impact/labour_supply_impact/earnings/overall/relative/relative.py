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
        # Calculate household counts
        # household_count_people_baseline = self.baseline.calculate("household_count_people")
        # household_count_people_reformed = self.reformed.calculate("household_count_people")

        # Calculate baseline and reformed substitution LSR
        substitution_lsr_hh_baseline = self._calculate_substitution_lsr(self.baseline)
        substitution_lsr_hh_reformed = self._calculate_substitution_lsr(self.reformed)

        # Compute the change in substitution LSR
        substitution_lsr_hh = np.array(substitution_lsr_hh_reformed) - np.array(substitution_lsr_hh_baseline)

        # Calculate baseline and reformed income LSR
        income_lsr_hh_baseline = self._calculate_income_lsr(self.baseline)
        income_lsr_hh_reformed = self._calculate_income_lsr(self.reformed)

        # Compute the change in income LSR
        income_lsr_hh = np.array(income_lsr_hh_reformed) - np.array(income_lsr_hh_baseline)

        # Calculate weights and earnings
        household_weight = self.baseline.calculate("household_weight")
        emp_income = MicroSeries(
            self.baseline.calculate("employment_income", map_to="household").astype(float).tolist(),
            weights=household_weight
        )
        self_emp_income = MicroSeries(
            self.baseline.calculate("self_employment_income", map_to="household").astype(float).tolist(),
            weights=household_weight
        )
        total_lsr_hh = substitution_lsr_hh + income_lsr_hh
        earnings = emp_income + self_emp_income
        original_earnings = earnings - total_lsr_hh

        # Calculate income LSR ratio
        income_lsr_hh = MicroSeries(income_lsr_hh, weights=household_weight)
        income = income_lsr_hh.sum() / original_earnings.sum() * 100

        return {"income": round(income,2)}

    def _calculate_substitution_lsr(self, simulation: Microsimulation):
        """Calculate substitution LSR for a given simulation."""
        if "employment_income_behavioral_response" in simulation.tax_benefit_system.variables:
            if any(simulation.calculate("employment_income_behavioral_response") != 0):
                return simulation.calculate("substitution_elasticity_lsr", map_to="household").astype(float).tolist()
        return (self.baseline.calculate("household_count_people") * 0).astype(float).tolist()

    def _calculate_income_lsr(self, simulation: Microsimulation):
        """Calculate income LSR for a given simulation."""
        if "employment_income_behavioral_response" in simulation.tax_benefit_system.variables:
            if any(simulation.calculate("employment_income_behavioral_response") != 0):
                return simulation.calculate("income_elasticity_lsr", map_to="household").astype(float).tolist()
        return (self.baseline.calculate("household_count_people") * 0).astype(float).tolist()


class SubstitutionLSR(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
        # Calculate household counts
        # household_count_people_baseline = self.baseline.calculate("household_count_people")
        # household_count_people_reformed = self.reformed.calculate("household_count_people")

        # Calculate baseline and reformed income LSR
        income_lsr_hh_baseline = self._calculate_income_lsr(self.baseline)
        income_lsr_hh_reformed = self._calculate_income_lsr(self.reformed)

        # Calculate baseline and reformed substitution LSR
        substitution_lsr_hh_baseline = self._calculate_substitution_lsr(self.baseline)
        substitution_lsr_hh_reformed = self._calculate_substitution_lsr(self.reformed)

        # Compute the change in substitution LSR
        substitution_lsr_hh = np.array(substitution_lsr_hh_reformed) - np.array(substitution_lsr_hh_baseline)
        household_weight = self.baseline.calculate("household_weight")
        
        # Convert to MicroSeries and compute total LSR
        substitution_lsr_hh = MicroSeries(substitution_lsr_hh, weights=household_weight)
        income_lsr_hh = np.array(income_lsr_hh_reformed) - np.array(income_lsr_hh_baseline)
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

        # Calculate substitution ratio
        substitution = substitution_lsr_hh.sum() / original_earnings.sum() * 100

        return {"substitution": round(substitution,2)}

    def _calculate_substitution_lsr(self, simulation: Microsimulation):
        """Calculate substitution LSR for a given simulation."""
        if "employment_income_behavioral_response" in simulation.tax_benefit_system.variables:
            if any(simulation.calculate("employment_income_behavioral_response") != 0):
                return simulation.calculate("substitution_elasticity_lsr", map_to="household").astype(float).tolist()
        return (self.baseline.calculate("household_count_people") * 0).astype(float).tolist()

    def _calculate_income_lsr(self, simulation: Microsimulation):
        """Calculate income LSR for a given simulation."""
        if "employment_income_behavioral_response" in simulation.tax_benefit_system.variables:
            if any(simulation.calculate("employment_income_behavioral_response") != 0):
                return simulation.calculate("income_elasticity_lsr", map_to="household").astype(float).tolist()
        return (self.baseline.calculate("household_count_people") * 0).astype(float).tolist()



class NetLSRChange(BaseMetricCalculator):
    def __init__(self, baseline: Microsimulation, reformed: Microsimulation, default_period: int = 2024) -> None:
        super().__init__(baseline, reformed, default_period)
        self.baseline = baseline
        self.reformed = reformed

    def calculate(self):
        income_result = IncomeLSR(baseline=self.baseline, reformed=self.reformed).calculate()
        substitution_result = SubstitutionLSR(baseline=self.baseline, reformed=self.reformed).calculate()
        
        income_value = income_result["income"]
        substitution_value = substitution_result["substitution"]

        net_change = (income_value + substitution_value)

        return {"net_change": round(net_change,2)}