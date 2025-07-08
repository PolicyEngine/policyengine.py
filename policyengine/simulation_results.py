from abc import ABC, abstractmethod
from numpy.typing import ArrayLike
import pandas

from policyengine.simulation.simulation_options import SimulationOptions


class AbstractSimulationResults(ABC):
    @abstractmethod
    def calculate(
        self,
        variable_name: str,
        period: pandas.Period | None = None,
        map_to: str | None = None,
        decode_enums: bool = False,
    ) -> pandas.Series:
        pass

    @abstractmethod
    def variable_exists(self, variable_name: str) -> bool:
        pass


class MacroContext:
    options: SimulationOptions
    baseline_simulation: AbstractSimulationResults
    reform_simulation: AbstractSimulationResults | None = None

    def __init__(
        self,
        options: SimulationOptions,
        baseline: AbstractSimulationResults,
        reform: AbstractSimulationResults | None = None,
    ):
        self.options = options
        self.baseline_simulation = baseline
        self.reform_simulation = reform
