"""Errors raised while ``Simulation.ensure()`` runs or saves a simulation.

``ensure()`` first tries to load a saved output and runs the simulation when
there is none it can use. An error raised by the run or the save must not
carry the handled load error as its implicit context (``__context__``):
Python prints that context first, followed by "During handling of the above
exception, another exception occurred", so the error looks as if it came
from the saved-output lookup. The Public API's telemetry report groups
errors by the first traceback in a stack.
"""

import logging
from typing import Any

import pytest
from pydantic import Field

from policyengine.core import (
    Simulation,
    StaleOutputError,
    TaxBenefitModel,
    TaxBenefitModelVersion,
)
from policyengine.core.simulation import _cache

# The three ways ``load()`` can report that there is no usable saved output:
# none saved, one that must not be reused, and an unexpected failure.
LOAD_ERROR_TYPES = {
    "no-saved-output": FileNotFoundError,
    "stale-output": StaleOutputError,
    "unexpected-error": RuntimeError,
}


class ScriptedModelVersion(TaxBenefitModelVersion):
    """A model version whose load, run and save raise the errors given."""

    load_error: Any = None
    run_error: Any = None
    save_error: Any = None
    calls: list[str] = Field(default_factory=list)

    def load(self, simulation):
        self.calls.append("load")
        if self.load_error is not None:
            raise self.load_error

    def run(self, simulation):
        self.calls.append("run")
        if self.run_error is not None:
            raise self.run_error
        return simulation

    def save(self, simulation):
        self.calls.append("save")
        if self.save_error is not None:
            raise self.save_error


def scripted_simulation(
    simulation_id: str | None = None, **errors: BaseException | None
) -> Simulation:
    model_version = ScriptedModelVersion(
        model=TaxBenefitModel(id="scripted"), version="0", **errors
    )
    identity = {"id": simulation_id} if simulation_id is not None else {}
    return Simulation(tax_benefit_model_version=model_version, **identity)


@pytest.fixture(autouse=True)
def empty_simulation_cache():
    """Start and end each test with an empty in-memory simulation cache."""
    _cache.clear()
    yield
    _cache.clear()


@pytest.mark.parametrize("load_error_name", LOAD_ERROR_TYPES)
def test_run_error_raised_through_ensure_carries_no_load_error(load_error_name):
    run_error = RuntimeError("run failed")
    simulation = scripted_simulation(
        load_error=LOAD_ERROR_TYPES[load_error_name]("saved output unusable"),
        run_error=run_error,
    )

    with pytest.raises(RuntimeError, match="run failed") as caught:
        simulation.ensure()

    assert caught.value is run_error
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None
    assert simulation.tax_benefit_model_version.calls == ["load", "run"]


@pytest.mark.parametrize("load_error_name", LOAD_ERROR_TYPES)
def test_save_error_raised_through_ensure_carries_no_load_error(load_error_name):
    save_error = OSError("saved output could not be written")
    simulation = scripted_simulation(
        load_error=LOAD_ERROR_TYPES[load_error_name]("saved output unusable"),
        save_error=save_error,
    )

    with pytest.raises(OSError, match="could not be written") as caught:
        simulation.ensure()

    assert caught.value is save_error
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None
    assert simulation.tax_benefit_model_version.calls == ["load", "run", "save"]


def test_ensure_does_not_run_when_the_saved_output_loads():
    simulation = scripted_simulation()

    simulation.ensure()

    assert simulation.tax_benefit_model_version.calls == ["load"]


@pytest.mark.parametrize("load_error_name", LOAD_ERROR_TYPES)
def test_ensure_runs_and_saves_without_a_usable_saved_output(load_error_name):
    simulation = scripted_simulation(
        load_error=LOAD_ERROR_TYPES[load_error_name]("saved output unusable")
    )

    simulation.ensure()

    assert simulation.tax_benefit_model_version.calls == ["load", "run", "save"]


def test_ensure_logs_a_stale_output_rerun_at_info(caplog):
    simulation = scripted_simulation(
        load_error=StaleOutputError("saved under an earlier release")
    )

    with caplog.at_level(logging.INFO, logger="policyengine.core.simulation"):
        simulation.ensure()

    [record] = caplog.records
    assert record.levelno == logging.INFO
    assert record.getMessage() == (
        f"Running simulation {simulation.id} again: saved under an earlier release"
    )


def test_ensure_logs_an_unexpected_load_error_with_its_traceback(caplog):
    load_error = RuntimeError("unreadable saved output")
    simulation = scripted_simulation(load_error=load_error)

    with caplog.at_level(logging.INFO, logger="policyengine.core.simulation"):
        simulation.ensure()

    [record] = caplog.records
    assert record.levelno == logging.WARNING
    assert record.exc_info is not None
    assert record.exc_info[1] is load_error


@pytest.mark.parametrize("load_error_name", LOAD_ERROR_TYPES)
def test_preemption_during_the_run_carries_no_load_error(load_error_name):
    # Modal delivers a preemption to the running function as a
    # KeyboardInterrupt, which is not an Exception.
    interruption = KeyboardInterrupt()
    simulation = scripted_simulation(
        load_error=LOAD_ERROR_TYPES[load_error_name]("saved output unusable"),
        run_error=interruption,
    )

    with pytest.raises(KeyboardInterrupt) as caught:
        simulation.ensure()

    assert caught.value is interruption
    assert caught.value.__context__ is None
    assert simulation.tax_benefit_model_version.calls == ["load", "run"]


def test_preemption_during_the_load_propagates_without_a_run():
    interruption = KeyboardInterrupt()
    simulation = scripted_simulation(load_error=interruption)

    with pytest.raises(KeyboardInterrupt) as caught:
        simulation.ensure()

    assert caught.value is interruption
    assert simulation.tax_benefit_model_version.calls == ["load"]
    assert _cache.get(simulation.id) is None


def test_ensure_uses_the_cached_result_of_an_earlier_run():
    first = scripted_simulation(
        simulation_id="cached-run", load_error=FileNotFoundError("no saved output")
    )
    first.ensure()
    second = scripted_simulation(simulation_id="cached-run")

    second.ensure()

    assert first.tax_benefit_model_version.calls == ["load", "run", "save"]
    assert second.tax_benefit_model_version.calls == []


@pytest.mark.parametrize("failing_step", ["run", "save"])
def test_ensure_caches_nothing_when_the_run_or_save_fails(failing_step):
    simulation = scripted_simulation(
        load_error=FileNotFoundError("no saved output"),
        **{f"{failing_step}_error": RuntimeError(f"{failing_step} failed")},
    )

    with pytest.raises(RuntimeError, match=f"{failing_step} failed"):
        simulation.ensure()

    assert _cache.get(simulation.id) is None


def test_ensure_logs_nothing_when_no_output_is_saved(caplog):
    simulation = scripted_simulation(load_error=FileNotFoundError("no saved output"))

    with caplog.at_level(logging.DEBUG, logger="policyengine.core.simulation"):
        simulation.ensure()

    assert caplog.records == []
