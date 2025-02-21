from policyengine.model_api import *
from microdf import MicroDataFrame
from typing import Literal
import numpy as np
import pandas as pd

class Aggregate(Output):
    country: str
    policy: Policy
    dataset: Dataset
    year: str
    variable: str

    total: float | None = None
    non_zero_count: int | None = None
    average_among_non_zero: float | None = None
    
    def link_simulations(self):
        self.link_simulation(
            name="baseline",
            country=self.country,
            policy=self.policy,
            dataset=self.dataset,
            calculations=[("household_net_income", self.year)],
        )
    
    def compute(
        self,
    ):
        baseline_mdf = MicroDataFrame(self.simulations["baseline"].output["household"][self.year])
        baseline_mdf.weights = baseline_mdf["household_weight"]
        
        self.total = baseline_mdf[self.variable].sum()
        self.non_zero_count = (baseline_mdf[self.variable] > 0).sum()
        self.average_among_non_zero = self.total / self.non_zero_count
