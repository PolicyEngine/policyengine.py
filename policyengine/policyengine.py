"""Simulate tax-benefit policy and derive society-level output statistics."""

from pydantic import BaseModel, Field
from typing import Literal
from .constants import DEFAULT_DATASETS_BY_COUNTRY
from policyengine_core.simulations import Simulation
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
from functools import wraps, partial
from typing import Dict, Any, Callable
import importlib
from policyengine.utils.types import *


class SimulationOptions(BaseModel):
    country: CountryType = Field(..., description="The country to simulate.")
    scope: ScopeType = Field(..., description="The scope of the simulation.")
    data: DataType = Field(None, description="The data to simulate.")
    time_period: TimePeriodType = Field(
        2025, description="The time period to simulate.", ge=2024, le=2035
    )
    reform: PolicyType = Field(None, description="The reform to simulate.")
    baseline: PolicyType = Field(None, description="The baseline to simulate.")
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


class PolicyEngine:
    """Simulate tax-benefit policies and derive society-level output statistics."""
    simulations: Dict[str, Simulation] = {}

    def __init__(self, **options: SimulationOptions):
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
                            func.__annotations__.get("engine")
                            == PolicyEngine
                        ):
                            wrapped_func = wraps(func)(
                                partial(func, engine=self)
                            )
                            wrapped_func.__annotations__ = func.__annotations__
                            setattr(
                                self,
                                func.__name__,
                                wrapped_func,
                            )

    def expect_simulation(
        self,
        name: str,
        country: CountryType,
        scope: ScopeType,
        policy: PolicyType,
        data: DataType,
        time_period: TimePeriodType,
        region: RegionType,
        subsample: SubsampleType,
    ) -> Simulation:
        if name in self.simulations:
            return self.simulations[name]
        else:
            simulation = self.build_simulation(
                country=country,
                scope=scope,
                policy=policy,
                data=data,
                time_period=time_period,
                region=region,
                subsample=subsample,
            )
            self.simulations[name] = simulation
            return simulation

    def build_simulation(
        self,
        country: CountryType,
        scope: ScopeType,
        policy: PolicyType,
        data: DataType,
        time_period: TimePeriodType,
        region: RegionType,
        subsample: SubsampleType,
    ):
        macro = scope == "macro"
        _simulation_type: Type[Simulation] = {
            "uk": {
                True: UKMicrosimulation,
                False: UKSimulation,
            },
            "us": {
                True: USMicrosimulation,
                False: USSimulation,
            },
        }[country][macro]

        data = _data_handle_cps_special_case(data)

        simulation: Simulation = _simulation_type(
            dataset=data if macro else None,
            situation=data if not macro else None,
            reform=policy,
        )

        simulation.default_calculation_period = time_period

        if region is not None:
            simulation = _apply_region_to_simulation(
                country=country,
                simulation=simulation,
                simulation_type=_simulation_type,
                region=region,
                policy=policy,
                time_period=time_period,
            )

        if subsample is not None:
            simulation = simulation.subsample(subsample)

        return simulation

def _apply_region_to_simulation(
    country: CountryType,
    simulation: CountryMicrosimulation,
    simulation_type: type,
    region: RegionType,
    policy: PolicyType | None,
) -> Simulation:
    if country == "us":
        df = simulation.to_input_dataframe()
        state_code = simulation.calculate(
            "state_code_str", map_to="person"
        ).values
        if region == "city/nyc":
            in_nyc = simulation.calculate("in_nyc", map_to="person").values
            simulation = simulation_type(dataset=df[in_nyc], reform=policy)
        elif "state/" in region:
            state = region.split("/")[1]
            simulation = simulation_type(
                dataset=df[state_code == state.upper()], reform=policy
            )
    elif country == "uk":
        if "country/" in region:
            region = region.split("/")[1]
            df = simulation.to_input_dataframe()
            country = simulation.calculate(
                "country", map_to="person"
            ).values
            simulation = simulation_type(
                dataset=df[country == region.upper()], reform=policy
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
                weights = f["2025"][...]

            simulation.set_input(
                "household_weight",
                "2025",
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
                weights = f["2025"][...]

            simulation.set_input(
                "household_weight",
                "2025",
                weights[la_id],
            )

    return simulation

def _data_handle_cps_special_case(
    data: DataType,
):
    """Handle special case for CPS data- this data doesn't specify time periods for each variable, but we still use it intensively."""
    if data is not None and "cps_2023" in data:
        if "hf://" in data:
            owner, repo, filename = data.split("/")[-3:]
            if "@" in filename:
                version = filename.split("@")[-1]
                filename = filename.split("@")[0]
            else:
                version = None
            data = download(
                repo=owner + "/" + repo,
                repo_filename=filename,
                local_folder=None,
                version=version,
            )
            data = Dataset.from_file(data, "2023")
    
    return data
