import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation, SimulationOptions

from policyengine_core.simulations import Microsimulation

from pydantic import BaseModel
from typing import Literal, List
import numpy as np


class PovertyRateMetric(BaseModel):
    age_group: Literal["child", "working_age", "senior", "all"]
    racial_group: Literal["white", "black", "hispanic", "other", "all"]
    relative: bool
    poverty_rate: Literal[
        "uk_hbai_bhc", "uk_hbai_bhc_half", "us_spm", "us_spm_half"
    ]
    value: float


AGE_BOUNDS = {
    "child": (0, 18),
    "working_age": (18, 65),
    "senior": (65, np.inf),
    "all": (0, np.inf),
}


def calculate_poverty(
    simulation: Microsimulation,
    options: "SimulationOptions",
) -> List[PovertyRateMetric]:
    """Calculate poverty statistics for a set of households."""

    poverty_metrics = []
    age = simulation.calculate("age")
    person_weight = simulation.calculate("person_weight").values
    if options.country == "us":
        racial_groups = ["white", "black", "hispanic", "other", "all"]
    else:
        racial_groups = ["all"]
    for age_group in ["child", "working_age", "senior", "all"]:
        lower_age, upper_age = AGE_BOUNDS[age_group]
        in_age_group = (age >= lower_age) & (age < upper_age)
        for racial_group in racial_groups:
            if racial_group != "all":
                in_racial_group = simulation.calculate("race") == racial_group
            else:
                in_racial_group = np.ones_like(age, dtype=bool)
            for relative in [True, False]:
                for poverty_rate in [
                    "uk_hbai_bhc",
                    "uk_hbai_bhc_half",
                    "us_spm",
                    "us_spm_half",
                ]:
                    if not poverty_rate.startswith(options.country):
                        continue

                    if poverty_rate == "uk_hbai_bhc":
                        in_poverty = simulation.calculate(
                            "in_poverty", map_to="person"
                        )
                    elif poverty_rate == "uk_hbai_bhc_half":
                        in_poverty = simulation.calculate(
                            "in_deep_poverty", map_to="person"
                        )
                    elif poverty_rate == "us_spm":
                        in_poverty = simulation.calculate(
                            "in_poverty", map_to="person"
                        )
                    elif poverty_rate == "us_spm_half":
                        in_poverty = simulation.calculate(
                            "in_deep_poverty", map_to="person"
                        )

                    in_group = np.array(in_age_group & in_racial_group)
                    total_in_group = (in_group * person_weight).sum()
                    total_in_group_in_poverty = (
                        in_group * in_poverty * person_weight
                    ).sum()
                    if relative:
                        result = total_in_group_in_poverty / total_in_group
                    else:
                        result = total_in_group_in_poverty

                    poverty_metrics.append(
                        PovertyRateMetric(
                            age_group=age_group,
                            racial_group=racial_group,
                            relative=relative,
                            poverty_rate=poverty_rate,
                            value=result,
                        )
                    )

    return poverty_metrics
