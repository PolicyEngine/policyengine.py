"""Simulate tax-benefit policy and derive society-level output statistics."""

from copy import deepcopy
import sys
from pydantic import BaseModel, Field
from typing import Literal

from .simulation_options import (
    CountryType,
    DataType,
    ReformType,
    RegionType,
    ScopeType,
    SimulationOptions,
    SubsampleType,
    TimePeriodType,
)

from policyengine.simulation_results import (
    AbstractSimulationResults,
    MacroContext,
)
from policyengine.utils.data.datasets import (
    get_default_dataset,
    process_gs_path,
    POLICYENGINE_DATASETS,
    DATASET_TIME_PERIODS,
)
from policyengine_core.simulations import Simulation as CountrySimulation
from policyengine_core.simulations import (
    Microsimulation as CountryMicrosimulation,
)
from policyengine.utils.reforms import ParametricReform

from policyengine_core.data import Dataset
from policyengine_us import (
    Simulation as USSimulation,
    Microsimulation as USMicrosimulation,
)
from policyengine_uk import (
    Simulation as UKSimulation,
    Microsimulation as UKMicrosimulation,
)
from importlib import metadata
import h5py
from pathlib import Path
import pandas as pd
from typing import Type, Any, Optional
from functools import wraps, partial
from typing import Callable
import importlib
from policyengine.utils.data_download import download
import logging

logger = logging.getLogger(__file__)


class Simulation:
    """Simulate tax-benefit policy and derive society-level output statistics."""

    is_comparison: bool
    """Whether the simulation is a comparison between two scenarios."""
    baseline_simulation: CountrySimulation
    """The baseline tax-benefit simulation."""
    reform_simulation: CountrySimulation | None = None
    """The reform tax-benefit simulation."""
    data_version: Optional[str] = None
    """The version of the data used in the simulation."""
    model_version: Optional[str] = None
    options: SimulationOptions

    def __init__(self, **kwargs):
        self.options = SimulationOptions.model_validate(kwargs)
        self.check_model_version()
        if not isinstance(self.options.data, dict) and not isinstance(
            self.options.data, Dataset
        ):
            logging.debug("Loading data")
            self._set_data(self.options.data)
            logging.info("Data loaded")
        self._initialise_simulations()
        logging.info("Simulations initialised")
        self.check_data_version()
        self._add_output_functions()
        logging.info("Output functions loaded")

    def _add_output_functions(self):
        logger.debug("Adding output functions to simulation")
        folder = Path(__file__).parent.parent / "outputs"

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
                logging.debug(f"Looking for modules in {python_module}.{name}")
                func = getattr(module, name)
                if isinstance(func, Callable):
                    logging.debug(f"Found function {name} in {python_module}")
                    if hasattr(func, "__annotations__"):
                        if (
                            func.__annotations__.get("simulation")
                            == Simulation
                        ):
                            logging.info(
                                f"Function {name} is an old macro function"
                            )
                            wrapped_func = wraps(func)(
                                partial(func, simulation=self)
                            )
                            wrapped_func.__annotations__ = func.__annotations__
                            setattr(
                                self,
                                func.__name__,
                                wrapped_func,
                            )
                        elif (
                            func.__annotations__.get("simulation")
                            == MacroContext
                        ):
                            logging.info(
                                f"Function {name} is a new macro function"
                            )
                            wrapped_func = wraps(func)(
                                partial(
                                    func, simulation=self
                                )  # _macro_context(self))
                            )
                            wrapped_func.__annotations__ = func.__annotations__
                            setattr(
                                self,
                                func.__name__,
                                wrapped_func,
                            )
                        else:
                            logging.debug(
                                f"Function {name} is not a macro function, skipping"
                            )

    def _set_data(self, file_address: str | None = None) -> None:

        # filename refers to file's unique name + extension;
        # file_address refers to URI + filename

        # If None is passed, user wants default dataset; get URL, then continue initializing.
        if file_address is None:
            file_address = get_default_dataset(
                country=self.options.country, region=self.options.region
            )
            print(
                f"No data provided, using default dataset: {file_address}",
                file=sys.stderr,
            )

        if file_address not in POLICYENGINE_DATASETS:
            # If it's a local file, no URI present and unable to infer version.
            filename = file_address
            version = None

        else:
            # All official PolicyEngine datasets are stored in GCS;
            # load accordingly
            filename, version = self._set_data_from_gs(file_address)
            self.data_version = version

        time_period = self._set_data_time_period(file_address)

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

    def check_model_version(self) -> None:
        """
        Check the package versions of the simulation against the current package versions.
        """
        package = f"policyengine-{self.options.country}"
        try:
            installed_version = metadata.version(package)
            self.model_version = installed_version
        except metadata.PackageNotFoundError:
            raise ValueError(
                f"Package {package} not found. Try running `pip install {package}`."
            )
        if self.options.model_version is not None:
            target_version = self.options.model_version
            if installed_version != target_version:
                raise ValueError(
                    f"Package {package} version {installed_version} does not match expected version {target_version}. Try running `pip install {package}=={target_version}`."
                )

    def check_data_version(self) -> None:
        """
        Check the data versions of the simulation against the current data versions.
        """
        if self.options.data_version is not None:
            if self.data_version != self.options.data_version:
                raise ValueError(
                    f"Data version {self.data_version} does not match expected version {self.options.data_version}."
                )

    def _set_data_time_period(self, file_address: str) -> Optional[int]:
        """
        Set the time period based on the file address.
        If the file address is a PE dataset, return the time period from the dataset.
        If it's a local file, return None.
        """
        if file_address in DATASET_TIME_PERIODS:
            return DATASET_TIME_PERIODS[file_address]
        else:
            # Local file, no time period available
            return None

    def _set_data_from_gs(self, file_address: str) -> tuple[str, str | None]:
        """
        Set the data from a GCS path and return the filename and version.
        """

        bucket, filename = process_gs_path(file_address)
        version = self.options.data_version

        print(f"Downloading {filename} from bucket {bucket}", file=sys.stderr)

        filepath, version = download(
            filepath=filename,
            gcs_bucket=bucket,
            version=version,
            return_version=True,
        )

        return filename, version


class SimpleSimulationResults(AbstractSimulationResults):
    def __init__(self, simulation: CountrySimulation):
        self._country_simulation = simulation

    def calculate(
        self,
        variable_name: str,
        period: pd.Period | None = None,
        map_to: str | None = None,
        decode_enums: bool = False,
    ) -> pd.Series:
        """
        Calculate a variable from the simulation results.
        """
        return self._country_simulation.calculate(
            variable_name, period=period, map_to=map_to, decode_enums=decode_enums  # type: ignore
        )

    def variable_exists(self, variable_name: str) -> bool:
        return (
            variable_name
            in self._country_simulation.tax_benefit_system.variables
        )


def _macro_context(simulation: Simulation):
    return MacroContext(
        simulation.options,
        SimpleSimulationResults(simulation.baseline_simulation),
        (
            SimpleSimulationResults(simulation.reform_simulation)
            if simulation.reform_simulation is not None
            else None
        ),
    )
