from policyengine_core.model_api import *
from policyengine_core.periods import instant
from typing import List


def index_parameters(
    parameters: List[str], index: str, start_year: int, end_year: int
):
    """Create a reform that indexes parameters to a given index (e.g. inflation).

    Args:
        parameters (List[str]): The parameters to index.
        index (str): The index to use.
        start_year (int): The first year that will be added as an indexed entry.
        end_year (int): The last year that will be added as an indexed entry.

    Returns:
        Reform: A reform that indexes the given parameters to the index.
    """

    class reform(Reform):
        def apply(self):
            index_p = self.parameters.get_child(index)
            for parameter in parameters:
                param = self.parameters.get_child(parameter)
                for year in range(start_year, end_year + 1):
                    param.update(
                        start=instant(year),
                        stop=instant(year + 1),
                        value=param(start_year - 1)
                        * index_p(year)
                        / index_p(start_year - 1),
                    )

    return reform
