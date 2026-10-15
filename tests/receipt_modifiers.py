"""Module-level simulation modifiers for receipt binding tests.

The module holds only functions, so its modifiers can be bound; shapes that
cannot be bound are in ``receipt_unbindable_modifiers``.
"""


def raise_basic_rate(simulation):
    simulation.tax_benefit_system.parameters.gov.hmrc.income_tax.rates.uk[
        0
    ].rate.update(period="year:2027:10", value=0.21)


def raise_higher_rate(simulation):
    simulation.tax_benefit_system.parameters.gov.hmrc.income_tax.rates.uk[
        1
    ].rate.update(period="year:2027:10", value=0.41)


def raise_basic_rate_to(simulation, rate=0.21):
    simulation.rate = rate


def raise_basic_rate_from(simulation, *, start=2027):
    simulation.start = start
