from policyengine.model_api import *
from microdf import MicroDataFrame
from typing import Literal
import numpy as np
import pandas as pd

class ChangeByQuantileGroup(Output):
    country: str
    baseline: Policy
    reform: Policy
    dataset: Dataset
    year: str
    quantile_group: int
    quantile_groups: int
    decile_variable: str
    change_variable: str
    fixed_entity_count: Literal["person", "household"] = "person"

    total_change: float | None = None
    relative_change: float | None = None
    average_change_per_household: float | None = None
    
    def link_simulations(self):
        self.link_simulation(
            name="baseline",
            country=self.country,
            policy=self.baseline,
            dataset=self.dataset,
            calculations=[("household_net_income", self.year), ("household_count_people", self.year)],
        )
        
        self.link_simulation(
            name="reform",
            country=self.country,
            policy=self.reform,
            dataset=self.dataset,
            calculations=[("household_net_income", self.year), ("household_count_people", self.year)],
        )
    
    def compute(
        self,
    ):
        baseline_mdf = MicroDataFrame(self.simulations["baseline"].output["household"][self.year])
        baseline_mdf.weights = baseline_mdf["household_weight"]
        if self.fixed_entity_count == "person":
            baseline_mdf.weights *= baseline_mdf["household_count_people"]
        reform_mdf = MicroDataFrame(self.simulations["reform"].output["household"][self.year])
        reform_mdf.weights = reform_mdf["household_weight"]
        if self.fixed_entity_count == "person":
            baseline_mdf.weights *= baseline_mdf["household_count_people"]

        quantile = baseline_mdf[self.decile_variable].rank(pct=True)
        quantile = np.where(reform_mdf[self.change_variable] < 0, -1, quantile)
        lower_quantile = (self.quantile_group - 1) / self.quantile_groups
        upper_quantile = self.quantile_group / self.quantile_groups
        in_group = pd.Series(quantile).between(lower_quantile, upper_quantile).values
        count_households_per_decile = baseline_mdf[self.decile_variable][in_group].count()
        baseline_total = baseline_mdf[in_group][self.change_variable].sum()
        reform_total = reform_mdf[in_group][self.change_variable].sum()

        self.total_change = reform_total - baseline_total
        self.relative_change = self.total_change / baseline_total
        self.average_change_per_household = self.total_change / count_households_per_decile
