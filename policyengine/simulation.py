from policyengine_core import Simulation as CountrySimulation
from policyengine_core.reforms import Reform
from typing import Tuple


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

    comparison: bool
    """Whether we are comparing two simulations, or analysing a single one."""
    baseline: CountrySimulation = None
    """The tax-benefit simulation for the baseline scenario."""
    reformed: CountrySimulation = None
    """The tax-benefit simulation for the reformed scenario."""

    def __init__(
        self,
        country: str,
        scope: str,
        data: str = None,
        time_period: str = None,
        reform: dict = None,
        baseline: dict = None,
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
        self.data = data
        self.time_period = time_period

        if isinstance(reform, dict):
            reform = Reform.from_dict(reform, country_id=country)
        elif isinstance(reform, int):
            reform = Reform.from_api(reform, country_id=country)

        self.reform = reform

        self.comparison = reform is not None

        self.output_functions, self.outputs = self._get_outputs()

        self._initialise_simulations()

    def calculate(self, output: str):
        """Calculate the given output (path).

        Args:
            output (str): The output to calculate. Must be a valid path in the output tree.

        Returns:
            Any: The output of the calculation (using the cache if possible).
        """
        if output.endswith("/"):
            output = output[:-1]

        node = self.outputs

        for child_key in output.split("/")[:-1]:
            node = node[child_key]

        parent = node
        child_key = output.split("/")[-1]
        node = parent[child_key]

        # Check if any descendants are None

        if parent[child_key] is None:
            output_function = self.output_functions[output]
            parent[child_key] = node = output_function(self)

        if isinstance(node, dict):
            for child_key in node.keys():
                self.calculate(output + "/" + child_key)

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

            def passed_reform_simulation(func):
                def adjusted_func(simulation):
                    simulation.baseline = simulation.reformed
                    return func(simulation)

                return adjusted_func

            if self.comparison:
                output_functions[f"{root}/baseline/{rest}"] = func
                output_functions[f"{root}/reform/{rest}"] = (
                    passed_reform_simulation(func)
                )
            else:
                output_functions[f"{root}/{rest}"] = func

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
        if self.country == "uk":
            from policyengine_uk import (
                Microsimulation as UKMicrosim,
                Simulation as UKSim,
            )

            self._simulation_type = UKMicrosim if macro else UKSim
        elif self.country == "us":
            from policyengine_us import (
                Microsimulation as USMicrosim,
                Simulation as USSim,
            )

            self._simulation_type = USMicrosim if macro else USSim
        self.baseline = self._simulation_type(
            dataset=self.data if macro else None,
            situation=self.data if not macro else None,
            reform=self.baseline,
        )
        self.baseline.default_calculation_period = self.time_period
        if self.comparison:
            self.reformed = self._simulation_type(
                dataset=self.data if macro else None,
                situation=self.data if not macro else None,
                reform=self.reform,
            )
            self.reformed.default_calculation_period = self.time_period
