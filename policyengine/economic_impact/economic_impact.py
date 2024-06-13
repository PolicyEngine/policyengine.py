from policyengine_core.reforms import Reform

class EconomicImpact:
    def __init__(self, reform, country):
        self.reform = reform
        self.country = country.lower()
        self.Microsimulation = self._get_simulation_class()
        
        # Initialize baseline and reformed simulations
        self.baseline = self.Microsimulation()
        self.reformed = self.Microsimulation(reform=Reform.from_dict(self.reform, country_id=self.country))

        # Set up metric calculators
        self.metric_calculators = {
            "inequality/gini": self.calculate_gini,
            "inequality/top_1_pct_share": self.calculate_top_1_pct_share,
            "inequality/top_10_pct_share": self.calculate_top_10_pct_share,
            # We willadd more metrics here as needed
        }
    # to get micrsosim based on country
    def _get_simulation_class(self):
        if self.country == "uk":
            from policyengine_uk import Microsimulation
        elif self.country == "us":
            from policyengine_us import Microsimulation
        else:
            raise ValueError(f"Unsupported country: {self.country}")
        return Microsimulation
    
    def calculate_baseline(self, variable, period=2024, map_to="person"):
        self.baseline_person = self.baseline.calculate(variable, period=period, map_to=map_to)
    
    def calculate_reformed(self, variable, period=2024, map_to="person"):
        self.reformed_person = self.reformed.calculate(variable, period=period, map_to=map_to)
    
    def calculate_gini(self):
        self.calculate_baseline("household_net_income")
        self.calculate_reformed("household_net_income")
        
        baseline_value = self.baseline_person.gini()
        reformed_value = self.reformed_person.gini()
        change_value = reformed_value - baseline_value
        
        return {
            "baseline": baseline_value,
            "reform": reformed_value,
            "change": change_value
        }
    
    def calculate_top_1_pct_share(self):
        self.calculate_baseline("household_net_income")
        self.calculate_reformed("household_net_income")
        
        baseline_value = self.baseline_person.top_1_pct_share()
        reformed_value = self.reformed_person.top_1_pct_share()
        change_value = reformed_value - baseline_value
        
        return {
            "baseline": baseline_value,
            "reform": reformed_value,
            "change": change_value
        }
    
    def calculate_top_10_pct_share(self):
        self.calculate_baseline("household_net_income")
        self.calculate_reformed("household_net_income")
        
        baseline_value = self.baseline_person.top_10_pct_share()
        reformed_value = self.reformed_person.top_10_pct_share()
        change_value = reformed_value - baseline_value
        
        return {
            "baseline": baseline_value,
            "reform": reformed_value,
            "change": change_value
        }

    # We can add more methods for other metrics as needed

    def calculate(self, metric):
        if metric not in self.metric_calculators:
            raise ValueError(f"Unknown metric: {metric}")
        return self.metric_calculators[metric]()
