from policyengine_core import Simulation as CountrySimulation
from policyengine_core.reforms import Reform
from typing import Tuple

class Simulation:
    """The top-level class through which all PE usage is carried out."""

    country: str
    """The country for which the simulation is being run."""
    type: str
    """The type of simulation being run (macro or household)."""
    data: str
    """The dataset being used for the simulation."""
    time_period: str
    """The time period for the simulation. Years are applicable."""
    baseline: dict
    """The baseline simulation inputs."""
    reform: dict
    """The reform simulation inputs."""
    custom_data: dict
    """The custom data for the simulation."""

    baseline: CountrySimulation
    reformed: CountrySimulation

    def __init__(self, country: str, type: str, data: str = None, time_period: str = None, reform: dict = None, baseline: dict = None):
        """Initialise the simulation with the given parameters.

        Args:
            country (str): The country for which the simulation is being run.
            type (str): The type of simulation being run (macro or household).
            data (str): The dataset being used for the simulation.
            time_period (str): The time period for the simulation. Years are applicable.
            reform (dict): The reform simulation inputs.
        """
        self.country = country
        self.type = type
        self.data = data
        self.time_period = time_period

        if isinstance(reform, dict):
            reform = Reform.from_dict(reform, country_id=country)
        elif isinstance(reform, int):
            reform = Reform.from_api(reform, country_id=country)

        self.reform = reform

        if country == "uk":
            from policyengine_uk import Microsimulation as UKMicrosimulation
            self.baseline = UKMicrosimulation(dataset=data, reform=baseline)
            self.baseline.default_calculation_period = time_period
            self.reformed = UKMicrosimulation(dataset=data, reform=reform)
            self.reformed.default_calculation_period = time_period

        self.output_functions, self.outputs = self.get_outputs()

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
        for key in output.split("/")[:-1]:
            node = node[key]

        parent = node
        child_key = output.split("/")[-1]
        node = parent[child_key]
        
        # Check if any descendants are None

        if parent[child_key] is None:
            output_function = self.output_functions[output]
            parent[child_key] = output_function(self)
        
        if isinstance(node, dict):
            for child_key in node.keys():
                self.calculate(output + "/" + child_key)

        return node

    def get_outputs(self) -> Tuple[dict, dict]:
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
            spec.loader.exec_module(module)
            relative_path = str(output.relative_to(Path(__file__).parent / "outputs")).replace(".py", "")

            # Only import the function with the same name as the module, enforcing one function per file
            output_functions[str(relative_path)] = getattr(module, module_name)
        
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

