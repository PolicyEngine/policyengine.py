from policyengine_core import Simulation as CountrySimulation
from policyengine_core import Microsimulation as CountryMicrosimulation
from policyengine_core.data import Dataset
from policyengine.utils.huggingface import download
from policyengine_core.reforms import Reform
from typing import Tuple, Any
from policyengine.constants import *
import pandas as pd
import h5py
from pathlib import Path
from typing import Literal


class Simulation:
    """The top-level class through which all PE usage is carried out."""

    country: Literal["uk", "us"]
    """The country for which the simulation is being run."""
    scope: Literal["macro", "household"]
    """The type of simulation being run (macro or household)."""
    data: dict | str | Dataset
    """The dataset being used for the simulation."""
    time_period: str | None
    """The time period for the simulation. Years are applicable."""
    baseline: dict | None
    """The baseline simulation inputs."""
    reform: dict | None
    """The reform simulation inputs."""
    options: dict
    """Dynamic options for the simulation type."""

    comparison: bool
    """Whether we are comparing two simulations, or analysing a single one."""
    baseline_sim: CountrySimulation
    """The tax-benefit simulation for the baseline scenario."""
    reformed_sim: CountrySimulation | None = None
    """The tax-benefit simulation for the reformed scenario. None if no reform has been configured"""
    selected_sim: CountrySimulation | None = None
    """The selected simulation for the current calculation. None if not a reform."""
    verbose: bool = False
    """Whether to print out progress messages."""

    def __init__(
        self,
        country: Literal["uk", "us"],
        scope: Literal["macro", "household"],
        data: str | dict | None = None,
        time_period: str | None = Literal[
            2024, 2025, 2026, 2027, 2028, 2029, 2030
        ],
        reform: dict | None = None,
        baseline: dict | None = None,
        verbose: bool = False,
        options: dict | None = None,
    ):
        """Initialise the simulation with the given parameters.

        Args:
            country (str): The country for which the simulation is being run.
            type (str): The type of simulation being run (macro or household).
            data (str): The dataset being used for the simulation.
            time_period (str): The time period for the simulation. Years are applicable.
            reform (dict): The reform simulation inputs.
        """
        self.country = country
        self.scope = scope
        self._set_dataset(data)
        self.time_period = time_period
        self.verbose = verbose
        self.options = options or {}
        self.baseline = baseline
        self.reform = reform

        self.comparison = reform is not None

        self._initialise_simulations()

    def _set_dataset(self, dataset: str | dict | None):
        if isinstance(dataset, dict):
            self.data = dataset
            return

        self.data = DEFAULT_DATASETS[self.country]
        if dataset in DATASETS[self.country]:
            self.data = DATASETS[self.country][dataset]

        # Short-term hacky fix: handle legacy 'array' datasets that don't specify the year for each variable: we should transition these to variable/period/value format.
        # But they're used frequently for now, and we need backwards compatibility.

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

    def _to_reform(self, value: int | dict):
        if isinstance(value, dict):
            return Reform.from_dict(value, country_id=self.country)
        return Reform.from_api(f"{value}", country_id=self.country)

    def _initialise_simulations(self):
        from policyengine_us import (
            Simulation as USSimulation,
            Microsimulation as USMicrosimulation,
        )
        from policyengine_uk import (
            Simulation as UKSimulation,
            Microsimulation as UKMicrosimulation,
        )

        self._parsed_reform = (
            self._to_reform(self.reform) if self.reform is not None else None
        )
        self._parsed_baseline = (
            self._to_reform(self.baseline)
            if self.baseline is not None
            else None
        )

        macro = self.scope == "macro"
        _simulation_type = {
            "uk": {
                True: UKMicrosimulation,
                False: UKSimulation,
            },
            "us": {
                True: USMicrosimulation,
                False: USSimulation,
            },
        }[self.country][macro]
        self.baseline_sim = _simulation_type(
            dataset=self.data if macro else None,
            situation=self.data if not macro else None,
            reform=self._parsed_baseline,
        )
        if self.time_period is not None:
            self.baseline_sim.default_calculation_period = self.time_period

        if "region" in self.options and isinstance(
            self.baseline_sim, CountryMicrosimulation
        ):
            self.baseline_sim = self._apply_region_to_simulation(
                self.baseline_sim,
                _simulation_type,
                self.options["region"],
                reform=self.baseline_sim.reform,
            )

        if "subsample" in self.options:
            self.baseline_sim = self.baseline_sim.subsample(
                self.options["subsample"]
            )

        if self.comparison:
            if self._parsed_baseline is not None:
                self._parsed_reform = (self._parsed_baseline, self.reform)
            self.reformed_sim = _simulation_type(
                dataset=self.data if macro else None,
                situation=self.data if not macro else None,
                reform=self._parsed_reform,
            )

            if self.time_period is not None:
                self.reformed_sim.default_calculation_period = self.time_period
            if "region" in self.options and isinstance(
                self.reformed_sim, CountryMicrosimulation
            ):
                self.reformed_sim = self._apply_region_to_simulation(
                    self.reformed_sim,
                    _simulation_type,
                    self.options["region"],
                    reform=self._parsed_reform,
                )

            if "subsample" in self.options:
                self.reformed_sim = self.reformed_sim.subsample(
                    self.options["subsample"]
                )

            # Set the 'baseline tax-benefit system' to be the actual baseline. For example, when working out an individual's
            # baseline MTR, it should use the actual policy baseline, not always current law.

            self.reformed_sim.get_branch("baseline").tax_benefit_system = (
                self.baseline_sim.tax_benefit_system
            )

    def _apply_region_to_simulation(
        self,
        simulation: CountryMicrosimulation,
        simulation_type: type,
        region: str,
        reform: Reform = None,
    ):
        if self.country == "us":
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
        elif self.country == "uk":
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
                    weights = f[str(self.time_period)][...]

                simulation.calculate("household_net_income")

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

                simulation.calculate("household_net_income")

                simulation.set_input(
                    "household_weight",
                    simulation.default_calculation_period,
                    weights[la_id],
                )

        simulation.default_calculation_period = self.time_period

        return simulation
