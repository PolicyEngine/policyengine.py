from policyengine.model_api import *
from microdf import MicroDataFrame

class ImpactByDecile(Output):
    country: str
    baseline: Policy
    reform: Policy
    dataset: Dataset
    year: str
    decile: int
    decile_variable: str
    impact_variable: str
    
    def link_simulations(self):
        self.link_simulation(
            name="baseline",
            country=self.country,
            policy=self.baseline,
            dataset=self.dataset,
            calculations=[("household_net_income", self.year)],
        )
        
        self.link_simulation(
            name="reform",
            country=self.country,
            policy=self.reform,
            dataset=self.dataset,
            calculations=[("household_net_income", self.year)],
        )
    
    def compute(
        self,
    ):
        baseline_mdf = MicroDataFrame(self.simulations["baseline"].output["household"][self.year])
        baseline_mdf.weights = baseline_mdf["household_weight"]
        reform_mdf = MicroDataFrame(self.simulations["reform"].output["household"][self.year])
        reform_mdf.weights = reform_mdf["household_weight"]

        decile = baseline_mdf[self.decile_variable].decile_rank()
        baseline_total = baseline_mdf[decile == self.decile][self.impact_variable].sum()
        reform_total = reform_mdf[decile == self.decile][self.impact_variable].sum()

        self.output = reform_total - baseline_total
