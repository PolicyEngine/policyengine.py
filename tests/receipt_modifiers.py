"""Module-level simulation modifiers for receipt binding tests."""


def raise_basic_rate(simulation):
    simulation.tax_benefit_system.parameters.gov.hmrc.income_tax.rates.uk[
        0
    ].rate.update(period="year:2027:10", value=0.21)


def raise_higher_rate(simulation):
    simulation.tax_benefit_system.parameters.gov.hmrc.income_tax.rates.uk[
        1
    ].rate.update(period="year:2027:10", value=0.41)


class Measure:
    def __init__(self, rate):
        self.rate = rate

    def apply(self, simulation):
        simulation.rate = self.rate


def make_modifier(rate):
    def modifier(simulation):
        simulation.rate = rate

    return modifier


def raise_basic_rate_to(simulation, rate=0.21):
    simulation.rate = rate


def raise_basic_rate_from(simulation, *, start=2027):
    simulation.start = start
