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

        self.output_functions, self.outputs = self._get_outputs()

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

    def calculate(self, output: str, force: bool = False, **kwargs) -> Any:
        """Calculate the given output (path).

        Args:
            output (str): The output to calculate. Must be a valid path in the output tree.
            force (bool): Whether to force recalculation of the output, even if it has already been calculated.
            **kwargs: Any additional arguments to pass to the output function.

        Returns:
            Any: The output of the calculation (using the cache if possible).
        """
        if self.verbose:
            print(f"Calculating {output}...")
        if output.endswith("/"):
            output = output[:-1]

        if output == "":
            output = self.scope

        node = self.outputs

        for child_key in output.split("/")[:-1]:
            if child_key not in node:
                raise KeyError(
                    f"Output '{child_key}' not found in '{node}'. Available keys are: {list(node.keys())}"
                )
            node = node[child_key]

        parent = node
        child_key = output.split("/")[-1]
        if parent is None:
            parent = self.calculate("/".join(output.split("/")[:-1]))
        if child_key not in parent:
            try:
                is_numeric_key = int(child_key) in parent
            except ValueError:
                is_numeric_key = False
            if is_numeric_key:
                child_key = int(child_key)
            else:
                # Maybe you've requested a key that is only available as a dictionary
                # item in one of the output functions. Let's try to calculate the full output,
                # then check the result to see if it's there.
                self.calculate("/".join(output.split("/")[:-1]))
                if child_key not in parent:
                    raise KeyError(
                        f"Output '{child_key}' not found in '{output}'. Available keys are: {list(parent.keys())}"
                    )
        node = parent[child_key]

        # Check if any descendants are None

        if (
            force or parent[child_key] is None or len(kwargs) > 0
        ) and output in self.output_functions:
            output_function = self.output_functions[output]
            node = output_function(self, **kwargs)
            if len(kwargs) == 0:
                # Only save as part of the larger tree if no non-standard args are passed
                parent[child_key] = node

        if isinstance(node, dict) and len(kwargs) == 0:
            for child_key in node.keys():
                self.calculate(output + "/" + str(child_key))

        return node

    def _get_outputs(self) -> Tuple[dict, dict]:
        """Get all the output functions and construct the output tree.

        Returns:
            Tuple[dict, dict]: A tuple containing the output functions and the output tree.
        """
        from pathlib import Path
        import importlib.util

        output_functions = {}
        for output in Path(__file__).parent.glob("outputs/**/*.py"):
            module_name = output.stem
            spec = importlib.util.spec_from_file_location(module_name, output)
            if spec is None:
                raise RuntimeError(
                    f"Expected to load a spec from file '{output.absolute}'"
                )
            module = importlib.util.module_from_spec(spec)
            relative_path = str(
                output.relative_to(Path(__file__).parent / "outputs")
            ).replace(".py", "")
            if not self.comparison and "/comparison/" in relative_path:
                # If we're just analysing one scenario, skip loading the comparison modules.
                continue
            if f"{self.scope}/" not in relative_path:
                # Don't load household modules for macro comparisons, etc.
                continue

            if spec.loader is None:
                raise RuntimeError(
                    f"Expected module from '{output.absolute}' to have a loader, but it does not"
                )
            spec.loader.exec_module(module)

            # Only import the function with the same name as the module, enforcing one function per file
            try:
                output_functions[str(relative_path)] = getattr(
                    module, module_name
                )
            except AttributeError:
                raise AttributeError(
                    f"Each module must contain a function with the same name as the module. Module '{str(relative_path)}.py' does not."
                )

        # If we are just calculating for a single scenario, put all 'macro/single/' children under 'macro/'.
        # If not, duplicate them into 'macro/baseline/' and 'single/reform'.

        single_keys = [key for key in output_functions if "single/" in key]
        for key in single_keys:
            root = key.split("/")[0]
            rest = "/".join(key.split("/")[2:])
            func = output_functions[key]

            def passed_reform_simulation(func, is_reform):
                def adjusted_func(simulation: Simulation, **kwargs):
                    if is_reform:
                        simulation.selected_sim = simulation.reformed_sim
                    else:
                        simulation.selected_sim = simulation.baseline_sim
                    return func(simulation, **kwargs)

                adjusted_func.__name__ = func.__name__
                adjusted_func.__doc__ = func.__doc__

                return adjusted_func

            if self.comparison:
                output_functions[f"{root}/baseline/{rest}"] = (
                    passed_reform_simulation(func, False)
                )
                output_functions[f"{root}/reform/{rest}"] = (
                    passed_reform_simulation(func, True)
                )
            else:
                output_functions[f"{root}/{rest}"] = passed_reform_simulation(
                    func, False
                )

            del output_functions[key]

        # Construct the output tree, fill with Nones for now

        outputs = {}

        for output_path in output_functions.keys():
            parts = output_path.split("/")
            current = outputs
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = None

        return output_functions, outputs

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

                print(
                    weights[constituency_id],
                    simulation.default_calculation_period,
                )

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
