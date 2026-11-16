"""Source-bindable, noncommutative modifiers for ordered execution tests."""


def add_one(simulation):
    simulation.ordered_value += 1
    simulation.ordered_trace.append("add")


def double(simulation):
    simulation.ordered_value *= 2
    simulation.ordered_trace.append("double")


def add_default(simulation, amount=3):
    simulation.ordered_value += amount
    simulation.ordered_trace.append("default")


def remember_before(simulation):
    simulation.before_value = simulation.ordered_value


def bump_limit(simulation):
    simulation.max_spiral_loops += 1


def scale_limit(simulation):
    simulation.max_spiral_loops *= 2
