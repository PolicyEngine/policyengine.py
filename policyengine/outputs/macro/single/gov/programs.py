from policyengine import Simulation
from dataclasses import dataclass


@dataclass
class UKProgram:
    name: str
    is_positive: bool


class UKPrograms:
    PROGRAMS = [
        UKProgram("income_tax", True),
        UKProgram("national_insurance", True),
        UKProgram("vat", True),
        UKProgram("council_tax", True),
        UKProgram("fuel_duty", True),
        UKProgram("tax_credits", False),
        UKProgram("universal_credit", False),
        UKProgram("child_benefit", False),
        UKProgram("state_pension", False),
        UKProgram("pension_credit", False),
        UKProgram("ni_employer", True),
    ]


def programs(simulation: Simulation) -> dict:
    if simulation.country == "uk":
        return {
            program.name: simulation.selected.calculate(
                program.name, map_to="household"
            ).sum()
            * (1 if program.is_positive else -1)
            for program in UKPrograms.PROGRAMS
        }
