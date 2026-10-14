"""The capital gains realisation response through policyengine.py's UK routes.

policyengine-uk scales realised gains in response to a reform, at an
elasticity under ``gov.simulation.capital_gains_responses`` whose default is
the model's (policyengine-uk#2396). These tests run a tiny in-memory 2027
dataset through the population route with explicit settings, so they hold
whatever the installed default is, and check that:

- explicit settings reach policyengine-uk unchanged: each retention-rate
  elasticity scales gains by the retention ratio to its power, a static
  setting holds them, the OBR comparison splits relief gains, and an MTR
  elasticity is not read as a retention-rate one;
- the dynamic's settings win over the policy's, on both of the runner's
  paths, and conflicting settings raise;
- each run records the response it applied, and the record survives saving,
  loading, run records and JSON, while a saved output is not reused under
  other settings or another model release;
- the household route records the response too.
"""

from __future__ import annotations

import json
import math
import shutil

import pandas as pd
import pytest
from microdf import MicroDataFrame

pytest.importorskip("policyengine_uk")

import policyengine as pe  # noqa: E402
from policyengine.core import Policy, Simulation  # noqa: E402
from policyengine.core.run_record import (  # noqa: E402
    build_simulation_run_record_payloads,
)
from policyengine.tax_benefit_models.common.model_version import (  # noqa: E402
    output_dataset_filepath,
)
from policyengine.tax_benefit_models.uk import (  # noqa: E402
    capital_gains_responses as records,
)
from policyengine.tax_benefit_models.uk.datasets import (  # noqa: E402
    PolicyEngineUKDataset,
    UKYearData,
)

YEAR = 2027
RESPONSES = "gov.simulation.capital_gains_responses"
FROM_2027 = "2027-04-06.2100-12-31"
# Higher and additional CGT rates of 45%, so the marginal rate on main-rate
# gains above the basic rate band rises from 24% to 45%.
RATE_RISE = {
    "gov.hmrc.cgt.higher_rate": {FROM_2027: 0.45},
    "gov.hmrc.cgt.additional_rate": {FROM_2027: 0.45},
}
RATIO = (1 - 0.45) / (1 - 0.24)
# 20% of 50% gains qualify for the relief at 18%: the share-weighted rate
# rises from 0.4 x 18% + 0.6 x 24% to 0.4 x 18% + 0.6 x 45%.
MIXED_RATIO = (1 - 0.342) / (1 - 0.216)
GAINS_VARIABLES = {
    "person": [
        "capital_gains",
        "capital_gains_before_response",
        "capital_gains_behavioural_response",
        "capital_gains_badr_behavioural_response",
    ]
}


def settings(**values) -> dict:
    return {f"{RESPONSES}.{name}": {FROM_2027: value} for name, value in values.items()}


def dataset(path=None) -> PolicyEngineUKDataset:
    """Four people in their own households, observed in 2027: higher-rate
    gainers with and without gains qualifying for the relief, a basic-rate
    gainer, and someone without gains. Saved to ``path`` when given, as run
    records and saved outputs need an input file."""
    ids = [1, 2, 3, 4]
    person = pd.DataFrame(
        {
            "person_id": ids,
            "person_benunit_id": ids,
            "person_household_id": ids,
            "age": [45, 45, 45, 45],
            "employment_income": [80_000.0, 80_000.0, 20_000.0, 30_000.0],
            "capital_gains": [50_000.0, 50_000.0, 10_000.0, 0.0],
            "capital_gains_badr": [0.0, 20_000.0, 0.0, 0.0],
            "person_weight": [1.0, 1.0, 1.0, 1.0],
        }
    )
    benunit = pd.DataFrame({"benunit_id": ids, "benunit_weight": [1.0] * 4})
    household = pd.DataFrame(
        {
            "household_id": ids,
            "household_weight": [1.0] * 4,
            "region": ["LONDON"] * 4,
            "tenure_type": ["OWNED_OUTRIGHT"] * 4,
            "council_tax": [0.0] * 4,
            "rent": [0.0] * 4,
        }
    )
    built = PolicyEngineUKDataset(
        name="cgt-responses",
        description="capital gains responses",
        year=YEAR,
        data=UKYearData(
            person=MicroDataFrame(person, weights="person_weight"),
            benunit=MicroDataFrame(benunit, weights="benunit_weight"),
            household=MicroDataFrame(household, weights="household_weight"),
        ),
    )
    if path is not None:
        built.filepath = str(path)
        built.save()
    return built


def simulation(policy=None, dynamic=None, path=None, **kwargs) -> Simulation:
    return Simulation(
        dataset=dataset(path),
        tax_benefit_model_version=pe.uk.model,
        policy=policy,
        dynamic=dynamic,
        extra_variables=GAINS_VARIABLES,
        **kwargs,
    )


def run(policy=None, dynamic=None, **kwargs) -> Simulation:
    sim = simulation(policy, dynamic, **kwargs)
    sim.run()
    return sim


def person(sim, variable):
    return list(sim.output_dataset.data.person[variable])


def factors(sim) -> list:
    before = person(sim, "capital_gains_before_response")
    response = person(sim, "capital_gains_behavioural_response")
    return [1 + r / b if b else 1.0 for r, b in zip(response, before)]


# Explicit settings reach the model unchanged.


@pytest.mark.parametrize("elasticity", [0.5, 1.0, 2.0])
def test_a_retention_rate_elasticity_scales_gains_by_the_ratio(elasticity):
    sim = run(policy=RATE_RISE, dynamic=settings(elasticity=elasticity))

    assert factors(sim)[0] == pytest.approx(RATIO**elasticity, abs=1e-5)
    # The basic-rate gainer's rate doesn't move, and the last has no gains.
    assert factors(sim)[2:] == [1.0, 1.0]


def test_static_settings_hold_gains():
    static = settings(elasticity=0, mtr_elasticity=0, separate_badr_elasticity=False)
    sim = run(policy=RATE_RISE, dynamic=static)

    assert person(sim, "capital_gains_behavioural_response") == [0.0] * 4


def test_the_obr_comparison_splits_relief_gains():
    sim = run(
        policy=RATE_RISE,
        dynamic=settings(elasticity=3.6, separate_badr_elasticity=True),
    )
    relief = 20_000
    relief_response = person(sim, "capital_gains_badr_behavioural_response")[1]
    main_response = (
        person(sim, "capital_gains_behavioural_response")[1] - relief_response
    )

    assert 1 + relief_response / relief == pytest.approx(MIXED_RATIO**1.4, abs=1e-4)
    assert 1 + main_response / 30_000 == pytest.approx(MIXED_RATIO**3.6, abs=1e-4)


def test_an_mtr_elasticity_is_not_a_retention_rate_elasticity():
    sim = run(
        policy=RATE_RISE,
        dynamic=settings(elasticity=0, mtr_elasticity=-0.7),
    )

    # (45% / 24%) ** -0.7, not the retention-rate 0.55 / 0.76.
    assert factors(sim)[0] == pytest.approx(
        math.exp(-0.7 * math.log(0.45 / 0.24)), abs=1e-5
    )


def test_conflicting_settings_raise():
    with pytest.raises(ValueError, match="mtr_elasticity"):
        run(policy=RATE_RISE, dynamic=settings(elasticity=0.5, mtr_elasticity=-0.7))


def test_settings_split_between_policy_and_dynamic_conflict_too():
    with pytest.raises(ValueError, match="mtr_elasticity"):
        run(
            policy={**RATE_RISE, **settings(elasticity=0.5)},
            dynamic=settings(mtr_elasticity=-0.7),
        )


# Precedence.


def test_the_dynamic_wins_over_the_policy():
    sim = run(
        policy={**RATE_RISE, **settings(elasticity=0.5)},
        dynamic=settings(elasticity=2.0),
    )

    assert factors(sim)[0] == pytest.approx(RATIO**2.0, abs=1e-5)
    assert [
        setting[-1]
        for setting in sim.output_dataset.metadata[records.RECORD_KEY]["request"][
            "settings"
        ]
    ] == ["policy", "dynamic"]


def test_the_dynamic_wins_after_a_policy_modifier():
    """With a policy modifier the dynamic's values are written after it, to
    the annualised parameters; a value from 1 January covers the year."""
    rate_rise = Policy(
        name="CGT rate rise",
        simulation_modifier=lambda microsim: microsim,
    )
    sim = run(
        policy=rate_rise + simulation(policy=RATE_RISE).policy,
        dynamic={f"{RESPONSES}.elasticity": {"2027-01-01.2100-12-31": 2.0}},
    )

    assert factors(sim)[0] == pytest.approx(RATIO**2.0, abs=1e-5)


# The record of the response.


def test_a_run_records_the_response_it_applied():
    sim = run(policy=RATE_RISE, dynamic=settings(elasticity=1.0))
    record = sim.output_dataset.metadata[records.RECORD_KEY]

    assert record["model"] == {
        "package": "policyengine-uk",
        "version": records.installed_model_version(),
    }
    assert record["period"] == "2027"
    assert record["request"]["settings"] == [
        [f"{RESPONSES}.elasticity", "2027-04-06", "2100-12-31", 1.0, "dynamic"]
    ]
    if record["resolved"] is not None:
        assert record["resolved"]["convention"] == "retention"
        assert record["resolved"]["elasticity"] == 1.0
    assert sim.release_bundle[records.RECORD_KEY] == record
    assert json.loads(json.dumps(record)) == record


def test_storage_ids_tell_settings_apart():
    plain = simulation(id="cgt-run")
    central = simulation(id="cgt-run", dynamic=settings(elasticity=1.0))
    lower = simulation(id="cgt-run", dynamic=settings(elasticity=0.5))

    assert plain.storage_id == "cgt-run"
    assert central.storage_id.startswith("cgt-run-cgr-")
    assert len({plain.storage_id, central.storage_id, lower.storage_id}) == 3


def saved(tmp_path, **kwargs) -> Simulation:
    """A run of an input saved in ``tmp_path``, its output saved beside it."""
    sim = run(path=tmp_path / "input.h5", **kwargs)
    sim.save()
    return sim


def test_the_record_survives_saving_and_loading(tmp_path):
    original = saved(
        tmp_path, id="cgt-run", policy=RATE_RISE, dynamic=settings(elasticity=0.5)
    )
    reloaded = simulation(
        id="cgt-run", policy=RATE_RISE, dynamic=settings(elasticity=0.5)
    )
    reloaded.dataset.filepath = original.dataset.filepath
    reloaded.load()

    assert (
        reloaded.output_dataset.metadata[records.RECORD_KEY]
        == original.output_dataset.metadata[records.RECORD_KEY]
    )
    assert (
        reloaded.release_bundle[records.RECORD_KEY]
        == (original.release_bundle[records.RECORD_KEY])
    )


def test_a_saved_output_is_not_reused_under_other_settings(tmp_path):
    original = saved(
        tmp_path, id="cgt-run", policy=RATE_RISE, dynamic=settings(elasticity=0.5)
    )
    other = simulation(id="cgt-run", policy=RATE_RISE, dynamic=settings(elasticity=2))
    other.dataset.filepath = original.dataset.filepath
    # Another request saves elsewhere; copied into its place, the output is
    # still refused.
    shutil.copy(original.output_dataset.filepath, str(output_dataset_filepath(other)))

    with pytest.raises(ValueError, match="other capital gains response settings"):
        other.load()


def test_a_saved_output_is_not_reused_under_another_model_release(
    tmp_path, monkeypatch
):
    original = saved(tmp_path, id="cgt-run", policy=RATE_RISE)
    monkeypatch.setattr(records, "installed_model_version", lambda: "0.0.1")
    reloaded = simulation(id="cgt-run", policy=RATE_RISE)
    reloaded.dataset.filepath = original.dataset.filepath

    with pytest.raises(ValueError, match="calculated with policyengine-uk"):
        reloaded.load()


def test_a_saved_output_without_a_record_is_not_reused(tmp_path):
    original = saved(tmp_path, id="cgt-run", policy=RATE_RISE)
    output = original.output_dataset
    output.metadata.pop(records.RECORD_KEY)
    output.save()
    reloaded = simulation(id="cgt-run", policy=RATE_RISE)
    reloaded.dataset.filepath = original.dataset.filepath

    with pytest.raises(ValueError, match="predates the record"):
        reloaded.load()


def test_changed_settings_are_not_saved_or_recorded(tmp_path):
    sim = saved(tmp_path, policy=RATE_RISE, dynamic=settings(elasticity=0.5))
    sim.dynamic = simulation(dynamic=settings(elasticity=2.0)).dynamic

    with pytest.raises(ValueError, match="changed since this output"):
        sim.save()
    with pytest.raises(ValueError, match="changed since this output"):
        build_simulation_run_record_payloads(sim)


def test_a_run_record_binds_the_response(tmp_path):
    sim = saved(tmp_path, policy=RATE_RISE, dynamic=settings(elasticity=1.0))
    payloads = build_simulation_run_record_payloads(sim)

    assert (
        payloads["results"][records.RECORD_KEY]
        == (sim.output_dataset.metadata[records.RECORD_KEY])
    )


# The household route.


def test_the_household_route_records_the_response():
    result = pe.uk.calculate_household(
        people=[{"age": 45, "employment_income": 80_000, "capital_gains": 50_000}],
        year=YEAR,
        reform={**RATE_RISE, **settings(elasticity=1.0)},
        extra_variables=["capital_gains"],
    )
    record = result["provenance"][records.RECORD_KEY]

    assert result.person[0]["capital_gains"] == pytest.approx(50_000 * RATIO, abs=0.5)
    assert record["request"]["settings"] == [
        [f"{RESPONSES}.elasticity", "2027-04-06", "2100-12-31", 1.0, "reform"]
    ]
    assert json.loads(json.dumps(result.to_dict()))["provenance"] == {
        records.RECORD_KEY: record
    }
