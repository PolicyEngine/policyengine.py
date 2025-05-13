"""Simulate tax-benefit policy and derive society-level output statistics."""

from pydantic import BaseModel, Field
from typing import Literal
from .constants import get_default_dataset
from policyengine_core.simulations import Simulation as CountrySimulation
from policyengine_core.simulations import (
    Microsimulation as CountryMicrosimulation,
)
from .utils.reforms import ParametricReform
from policyengine_core.reforms import Reform as StructuralReform
from policyengine_core.data import Dataset
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
from functools import wraps, partial
from typing import Dict, Any, Callable
import importlib
from policyengine.utils.data_download import download

CountryType = Literal["uk", "us"]
ScopeType = Literal["household", "macro"]
DataType = (
    str | dict | Any | None
)  # Needs stricter typing. Any==policyengine_core.data.Dataset, but pydantic refuses for some reason.
TimePeriodType = int
ReformType = ParametricReform | Type[StructuralReform] | None
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

    def __init__(self, **options: SimulationOptions):
        self.options = SimulationOptions(**options)

        self._set_data()
        self._initialise_simulations()
        self._add_output_functions()

    def _add_output_functions(self):
        folder = Path(__file__).parent / "outputs"

        for module in folder.glob("**/*.py"):
            if module.stem == "__init__":
                continue
            python_module = (
                module.relative_to(folder.parent)
                .with_suffix("")
                .as_posix()
                .replace("/", ".")
            )
            module = importlib.import_module("policyengine." + python_module)
            for name in dir(module):
                func = getattr(module, name)
                if isinstance(func, Callable):
                    if hasattr(func, "__annotations__"):
                        if (
                            func.__annotations__.get("simulation")
                            == Simulation
                        ):
                            wrapped_func = wraps(func)(
                                partial(func, simulation=self)
                            )
                            wrapped_func.__annotations__ = func.__annotations__
                            setattr(
                                self,
                                func.__name__,
                                wrapped_func,
                            )

    def _set_data(self):
        if self.options.data is None:
            self.options.data = get_default_dataset(
                country=self.options.country,
                region=self.options.region,
            )

        elif isinstance(self.options.data, str):
            filename = self.options.data
            if "://" in self.options.data:
                bucket = None
                hf_repo = None
                hf_org = None
                if "gs://" in self.options.data:
                    bucket, filename = self.options.data.split("://")[
                        -1
                    ].split("/")
                    hf_org = "policyengine"
                elif "hf://" in self.options.data:
                    hf_org, hf_repo, filename = self.options.data.split("://")[
                        -1
                    ].split("/", 2)

                if not Path(filename).exists():
                    file_path = download(
                        filepath=filename,
                        huggingface_org=hf_org,
                        huggingface_repo=hf_repo,
                        gcs_bucket=bucket,
                    )
                    filename = str(Path(file_path))
            if "cps_2023" in filename:
                time_period = 2023
            else:
                time_period = None
            self.options.data = Dataset.from_file(
                filename, time_period=time_period
            )

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
    ) -> CountrySimulation:
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

        simulation: CountrySimulation = _simulation_type(
            dataset=data if macro else None,
            situation=data if not macro else None,
            reform=reform,
        )

        simulation.default_calculation_period = time_period

        if region is not None:
            simulation = self._apply_region_to_simulation(
                country=country,
                simulation=simulation,
                simulation_type=_simulation_type,
                region=region,
                reform=reform,
                time_period=time_period,
            )

        if subsample is not None:
            simulation = simulation.subsample(subsample)

        simulation.default_calculation_period = time_period

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
                    huggingface_repo="policyengine-uk-data",
                    gcs_bucket="policyengine-uk-data-private",
                    filepath="constituencies_2024.csv",
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
                    huggingface_repo="policyengine-uk-data",
                    gcs_bucket="policyengine-uk-data-private",
                    filepath="parliamentary_constituency_weights.h5",
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
                    huggingface_repo="policyengine-uk-data",
                    gcs_bucket="policyengine-uk-data-private",
                    filepath="local_authorities_2021.csv",
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
                    huggingface_repo="policyengine-uk-data",
                    gcs_bucket="policyengine-uk-data-private",
                    filepath="local_authority_weights.h5",
                )

                with h5py.File(weights_file_path, "r") as f:
                    weights = f[str(self.time_period)][...]

                simulation.set_input(
                    "household_weight",
                    simulation.default_calculation_period,
                    weights[la_id],
                )

        return simulation
