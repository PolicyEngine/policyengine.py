from policyengine_core import Simulation as CountrySimulation
from policyengine_core import Microsimulation as CountryMicrosimulation
from policyengine_core.data import Dataset
from policyengine.utils.huggingface import download
from policyengine_us import (
    Simulation as USSimulation,
    Microsimulation as USMicrosimulation,
)
from policyengine_uk import (
    Simulation as UKSimulation,
    Microsimulation as UKMicrosimulation,
)
from policyengine_core.reforms import Reform
from typing import Tuple, Any
from policyengine.constants import *


class Simulation:
    """The top-level class through which all PE usage is carried out."""

    country: str
    """The country for which the simulation is being run."""
    scope: str
    """The type of simulation being run (macro or household)."""
    data: str
    """The dataset being used for the simulation."""
    time_period: str
    """The time period for the simulation. Years are applicable."""
    baseline: dict
    """The baseline simulation inputs."""
    reform: dict
    """The reform simulation inputs."""
    options: dict
    """Dynamic options for the simulation type."""

    comparison: bool
    """Whether we are comparing two simulations, or analysing a single one."""
    baseline: CountrySimulation = None
    """The tax-benefit simulation for the baseline scenario."""
    reformed: CountrySimulation = None
    """The tax-benefit simulation for the reformed scenario."""
    verbose: bool = False
    """Whether to print out progress messages."""

    def __init__(
        self,
        country: str,
        scope: str,
        data: str = None,
        time_period: str = None,
        reform: dict = None,
        baseline: dict = None,
        verbose: bool = False,
        options: dict = None,
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

        if isinstance(reform, dict):
            reform = Reform.from_dict(reform, country_id=country)
        elif isinstance(reform, int):
            reform = Reform.from_api(reform, country_id=country)

        self.baseline = baseline
        self.reform = reform

        self.comparison = reform is not None

        self.output_functions, self.outputs = self._get_outputs()

        self._initialise_simulations()

    def _set_dataset(self, dataset: str):
        if dataset in DATASETS[self.country]:
            self.data = DATASETS[self.country][dataset]
        elif dataset is None:
            self.data = DEFAULT_DATASETS[self.country]
        else:
            self.data = dataset

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
                self.data = Dataset.from_file(self.data, 2023)

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
            output = list(self.outputs.keys())[0]

        node = self.outputs

        for child_key in output.split("/")[:-1]:
            node = node[child_key]

        parent = node
        child_key = output.split("/")[-1]
        if child_key not in parent and int(child_key) in parent:
            child_key = int(child_key)
        node = parent[child_key]

        # Check if any descendants are None

        if (
            force or parent[child_key] is None or len(kwargs) > 0
        ) and output in self.output_functions:
            output_function = self.output_functions[output]
            parent[child_key] = node = output_function(self, **kwargs)

        if isinstance(node, dict):
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

            spec.loader.exec_module(module)

            # Only import the function with the same name as the module, enforcing one function per file
            output_functions[str(relative_path)] = getattr(module, module_name)

        # If we are just calculating for a single scenario, put all 'macro/single/' children under 'macro/'.
        # If not, duplicate them into 'macro/baseline/' and 'single/reform'.

        single_keys = [key for key in output_functions if "single/" in key]
        for key in single_keys:
            root = key.split("/")[0]
            rest = "/".join(key.split("/")[2:])
            func = output_functions[key]

            def passed_reform_simulation(func, is_reform):
                def adjusted_func(simulation, **kwargs):
                    if is_reform:
                        simulation.selected = simulation.reformed
                    else:
                        simulation.selected = simulation.baseline
                    return func(simulation, **kwargs)

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

    def _initialise_simulations(self):
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
        self.baseline = _simulation_type(
            dataset=self.data if macro else None,
            situation=self.data if not macro else None,
            reform=self.baseline,
        )
        self.baseline.default_calculation_period = self.time_period

        if "subsample" in self.options:
            self.baseline = self.baseline.subsample(self.options["subsample"])

        if "region" in self.options:
            self.baseline = self._apply_region_to_simulation(
                self.baseline, _simulation_type, self.options["region"]
            )

        if self.comparison:
            self.reformed = _simulation_type(
                dataset=self.data if macro else None,
                situation=self.data if not macro else None,
                reform=self.reform,
            )
            self.reformed.default_calculation_period = self.time_period

            if "subsample" in self.options:
                self.reformed = self.reformed.subsample(
                    self.options["subsample"]
                )

            if "region" in self.options:
                self.reformed = self._apply_region_to_simulation(
                    self.reformed, _simulation_type, self.options["region"]
                )

    def _apply_region_to_simulation(
        self,
        simulation: CountryMicrosimulation,
        simulation_type: type,
        region: str,
    ):
        if self.country == "us":
            df = simulation.to_input_dataframe()
            state_code = simulation.calculate(
                "state_code_str", map_to="person"
            ).values
            if region == "city/nyc":
                in_nyc = simulation.calculate("in_nyc", map_to="person").values
                simulation = simulation_type(
                    dataset=df[in_nyc], reform=self.reform
                )
            elif "state/" in region:
                state = region.split("/")[1]
                simulation = simulation_type(
                    dataset=df[state_code == state.upper()], reform=self.reform
                )

        return simulation
