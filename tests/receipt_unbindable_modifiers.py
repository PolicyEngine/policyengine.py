"""Modifier shapes a receipt refuses: a method and a closure."""


class Measure:
    def __init__(self, rate):
        self.rate = rate

    def apply(self, simulation):
        simulation.rate = self.rate


def make_modifier(rate):
    def modifier(simulation):
        simulation.rate = rate

    return modifier
