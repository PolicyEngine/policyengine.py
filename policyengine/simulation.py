"""Simulate tax-benefit policy and derive society-level output statistics."""

from pydantic import BaseModel, Field
from typing import Literal
from .constants import DEFAULT_DATASETS_BY_COUNTRY
from policyengine_core.simulations import Simulation as CountrySimulation
from policyengine_core.simulations import (
    Microsimulation as CountryMicrosimulation,
)
from .utils.reforms import ParametricReform, SimulationAdjustment
from policyengine_core.reforms import Reform as StructuralReform
from policyengine_core.data import Dataset
from .utils.huggingface import download
from policyengine_us import (
    Simulation as USSimulation,
    Microsimulation as USMicrosimulation,
)
from policyengine_uk import (
    Simulation as UKSimulation,
    Microsimulation as UKMicrosimulation,
)
import h5py
from pathlib import Path
import pandas as pd
from typing import Type
from functools import wraps
from .outputs.macro.comparison.calculate_economy_comparison import (
    calculate_economy_comparison,
    EconomyComparison,
)
from .outputs.macro.single.calculate_single_economy import (
    SingleEconomy,
    calculate_single_economy,
)

from .outputs.household.single.calculate_single_household import (
    SingleHousehold,
    calculate_single_household,
)

from .outputs.household.comparison.calculate_household_comparison import (
    HouseholdComparison,
    calculate_household_comparison,
)
from .outputs.macro.comparison.charts.create_all_charts import (
    create_all_charts,
    MacroCharts,
)
from typing import Any, Tuple

CountryType = Literal["uk", "us"]
ScopeType = Literal["household", "macro"]
DataType = (
    str | dict | Any | None
)  # Needs stricter typing. Any==policyengine_core.data.Dataset, but pydantic refuses for some reason.
TimePeriodType = int
ReformType = (
    ParametricReform | SimulationAdjustment | Type[StructuralReform] | None
)
RegionType = str | None
SubsampleType = int | None


class SimulationOptions(BaseModel):
    country: CountryType = Field(..., description="The country to simulate.")
    scope: ScopeType = Field(..., description="The scope of the simulation.")
    data: DataType = Field(None, description="The data to simulate.")
    time_period: TimePeriodType = Field(
        2025, description="The time period to simulate.", ge=2024, le=2035
    )
    reform: ReformType = Field(None, description="The reform to simulate.")
    baseline: ReformType = Field(None, description="The baseline to simulate.")
    region: RegionType = Field(
        None, description="The region to simulate within the country."
    )
    subsample: SubsampleType = Field(
        None,
        description="How many, if a subsample, households to randomly simulate.",
    )
    title: str | None = Field(
        "[Analysis title]",
        description="The title of the analysis (for charts). If not provided, a default title will be generated.",
    )


class Simulation:
    """Simulate tax-benefit policy and derive society-level output statistics."""

    is_comparison: bool
    """Whether the simulation is a comparison between two scenarios."""
    baseline_simulation: CountrySimulation
    """The baseline tax-benefit simulation."""
    reform_simulation: CountrySimulation | None = None
    """The reform tax-benefit simulation."""

    def __init__(self, options: SimulationOptions):
        self.options = SimulationOptions(**options)

        if self.options.data is None:
            self.options.data = DEFAULT_DATASETS_BY_COUNTRY[
                self.options.country
            ]

        self._initialise_simulations()

    def _set_data(self):
        if self.options.data is None:
            self.options.data = DEFAULT_DATASETS_BY_COUNTRY[
                self.options.country
            ]

        self._data_handle_cps_special_case()

    def _initialise_simulations(self):
        self.baseline_simulation = self._initialise_simulation(
            scope=self.options.scope,
            country=self.options.country,
            reform=self.options.baseline,
            data=self.options.data,
            time_period=self.options.time_period,
            region=self.options.region,
            subsample=self.options.subsample,
        )

        if self.options.reform is not None:
            self.reform_simulation = self._initialise_simulation(
                scope=self.options.scope,
                country=self.options.country,
                reform=self.options.reform,
                data=self.options.data,
                time_period=self.options.time_period,
                region=self.options.region,
                subsample=self.options.subsample,
            )
            self.is_comparison = True
        else:
            self.is_comparison = False

    def _initialise_simulation(
        self,
        country: CountryType,
        scope: ScopeType,
        reform: ReformType,
        data: DataType,
        time_period: TimePeriodType,
        region: RegionType,
        subsample: SubsampleType,
    ):
        macro = scope == "macro"
        _simulation_type: Type[CountrySimulation] = {
            "uk": {
                True: UKMicrosimulation,
                False: UKSimulation,
            },
            "us": {
                True: USMicrosimulation,
                False: USSimulation,
            },
        }[country][macro]

        if isinstance(reform, ParametricReform):
            reform = reform.model_dump()

        simulation_editing_reform = None

        if isinstance(reform, SimulationAdjustment):
            simulation_editing_reform = reform.root
            reform = None

        simulation: CountrySimulation = _simulation_type(
            dataset=data if macro else None,
            situation=data if not macro else None,
            reform=reform,
        )

        if region is not None:
            simulation = self._apply_region_to_simulation(
                country=country,
                simulation=simulation,
                simulation_type=_simulation_type,
                region=region,
                reform=reform,
                time_period=time_period,
            )

        simulation.default_calculation_period = time_period

        if subsample is not None:
            simulation = simulation.subsample(subsample)

        if simulation_editing_reform is not None:
            simulation_editing_reform(simulation)

        return simulation

    def _apply_region_to_simulation(
        self,
        country: CountryType,
        simulation: CountryMicrosimulation,
        simulation_type: type,
        region: RegionType,
        reform: ReformType | None,
        time_period: TimePeriodType,
    ) -> CountrySimulation:
        if country == "us":
            df = simulation.to_input_dataframe()
            state_code = simulation.calculate(
                "state_code_str", map_to="person"
            ).values
            if region == "city/nyc":
                in_nyc = simulation.calculate("in_nyc", map_to="person").values
                simulation = simulation_type(dataset=df[in_nyc], reform=reform)
            elif "state/" in region:
                state = region.split("/")[1]
                simulation = simulation_type(
                    dataset=df[state_code == state.upper()], reform=reform
                )
        elif country == "uk":
            if "country/" in region:
                region = region.split("/")[1]
                df = simulation.to_input_dataframe()
                country = simulation.calculate(
                    "country", map_to="person"
                ).values
                simulation = simulation_type(
                    dataset=df[country == region.upper()], reform=reform
                )
            elif "constituency/" in region:
                constituency = region.split("/")[1]
                constituency_names_file_path = download(
                    repo="policyengine/policyengine-uk-data",
                    repo_filename="constituencies_2024.csv",
                    local_folder=None,
                    version=None,
                )
                constituency_names_file_path = Path(
                    constituency_names_file_path
                )
                constituency_names = pd.read_csv(constituency_names_file_path)
                if constituency in constituency_names.code.values:
                    constituency_id = constituency_names[
                        constituency_names.code == constituency
                    ].index[0]
                elif constituency in constituency_names.name.values:
                    constituency_id = constituency_names[
                        constituency_names.name == constituency
                    ].index[0]
                else:
                    raise ValueError(
                        f"Constituency {constituency} not found. See {constituency_names_file_path} for the list of available constituencies."
                    )
                weights_file_path = download(
                    repo="policyengine/policyengine-uk-data",
                    repo_filename="parliamentary_constituency_weights.h5",
                    local_folder=None,
                    version=None,
                )

                with h5py.File(weights_file_path, "r") as f:
                    weights = f[str(time_period)][...]

                simulation.set_input(
                    "household_weight",
                    simulation.default_calculation_period,
                    weights[constituency_id],
                )
            elif "local_authority/" in region:
                la = region.split("/")[1]
                la_names_file_path = download(
                    repo="policyengine/policyengine-uk-data",
                    repo_filename="local_authorities_2021.csv",
                    local_folder=None,
                    version=None,
                )
                la_names_file_path = Path(la_names_file_path)
                la_names = pd.read_csv(la_names_file_path)
                if la in la_names.code.values:
                    la_id = la_names[la_names.code == la].index[0]
                elif la in la_names.name.values:
                    la_id = la_names[la_names.name == la].index[0]
                else:
                    raise ValueError(
                        f"Local authority {la} not found. See {la_names_file_path} for the list of available local authorities."
                    )
                weights_file_path = download(
                    repo="policyengine/policyengine-uk-data",
                    repo_filename="local_authority_weights.h5",
                    local_folder=None,
                    version=None,
                )

                with h5py.File(weights_file_path, "r") as f:
                    weights = f[str(self.time_period)][...]

                simulation.set_input(
                    "household_weight",
                    simulation.default_calculation_period,
                    weights[la_id],
                )

        return simulation

    def _data_handle_cps_special_case(self):
        """Handle special case for CPS data- this data doesn't specify time periods for each variable, but we still use it intensively."""
        if self.data is not None and "cps_2023" in self.data:
            if "hf://" in self.data:
                owner, repo, filename = self.data.split("/")[-3:]
                if "@" in filename:
                    version = filename.split("@")[-1]
                    filename = filename.split("@")[0]
                else:
                    version = None
                self.data = download(
                    repo=owner + "/" + repo,
                    repo_filename=filename,
                    local_folder=None,
                    version=version,
                )
                self.data = Dataset.from_file(self.data, "2023")

    def calculate(
        self,
    ) -> (
        SingleEconomy
        | EconomyComparison
        | SingleHousehold
        | HouseholdComparison
    ):
        """Calculate the default output statistics for the simulation type."""
        if self.options.scope == "macro":
            if self.is_comparison:
                return self.calculate_economy_comparison()
            else:
                return self.calculate_single_economy()
        elif self.options.scope == "household":
            if self.is_comparison:
                return self.calculate_household_comparison()
            else:
                return self.calculate_single_household()

    def calculate_economy_comparison(self) -> EconomyComparison:
        """Calculate comparison statistics between two economic scenarios."""
        return calculate_economy_comparison(self)

    def calculate_single_economy(self) -> SingleEconomy:
        """Calculate economy statistics for a single economic scenario."""
        return calculate_single_economy(self)

    def calculate_single_household(self) -> SingleHousehold:
        """Calculate household statistics for a single household scenario."""
        return calculate_single_household(self)

    def calculate_household_comparison(self) -> HouseholdComparison:
        """Calculate comparison statistics between two household scenarios."""
        return calculate_household_comparison(self)

    def create_all_charts(self) -> MacroCharts:
        """Create all macro charts for the simulation."""
        return create_all_charts(self)
