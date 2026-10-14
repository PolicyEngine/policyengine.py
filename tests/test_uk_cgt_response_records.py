"""The record of the capital gains realisation response a UK run applies.

These tests check the record's parts without running the model: which
settings a request lists and in what order, the digest that keys a run's
cache and saved output, and when a saved output's record rules out reusing
it. ``test_uk_cgt_responses.py`` runs the model through each entry point.
"""

import datetime

import pytest

from policyengine.tax_benefit_models.uk import capital_gains_responses as records

ELASTICITY = "gov.simulation.capital_gains_responses.elasticity"
MTR_ELASTICITY = "gov.simulation.capital_gains_responses.mtr_elasticity"
SEPARATE = "gov.simulation.capital_gains_responses.separate_badr_elasticity"


class _Parameter:
    def __init__(self, name):
        self.name = name


class _Value:
    def __init__(self, name, value, start, end=None):
        self.parameter = _Parameter(name)
        self.value = value
        self.start_date = start
        self.end_date = end


def _values(*settings):
    return [_Value(*setting) for setting in settings]


START = datetime.datetime(2027, 1, 1)
END = datetime.date(2027, 12, 31)


def test_a_request_lists_response_settings_in_the_order_they_apply():
    policy = _values(
        ("gov.hmrc.cgt.higher_rate", 0.45, START),
        (ELASTICITY, 0.5, START, END),
    )
    dynamic = _values((ELASTICITY, 2, START), (SEPARATE, True, START))

    request = records.request((("policy", policy), ("dynamic", dynamic)))

    assert request["settings"] == [
        [ELASTICITY, "2027-01-01", "2027-12-31", 0.5, "policy"],
        [ELASTICITY, "2027-01-01", None, 2.0, "dynamic"],
        [SEPARATE, "2027-01-01", None, True, "dynamic"],
    ]
    assert len(request["digest"]) == 64


def test_no_settings_means_no_digest():
    request = records.request(
        (("policy", _values(("gov.hmrc.cgt.higher_rate", 0.45, START))),)
    )

    assert request == {"settings": [], "digest": None}


def test_the_digest_tells_requests_apart():
    def digest(*settings, source="dynamic"):
        return records.request(((source, _values(*settings)),))["digest"]

    central = digest((ELASTICITY, 1.0, START))
    assert digest((ELASTICITY, 1, START)) == central
    assert digest((ELASTICITY, 0.5, START)) != central
    assert digest((ELASTICITY, 1.0, START), source="policy") != central
    assert digest((MTR_ELASTICITY, -0.7, START)) != digest((ELASTICITY, -0.7, START))
    # The order the settings apply in decides which one wins.
    assert digest((ELASTICITY, 0.5, START), (ELASTICITY, 2.0, START)) != digest(
        (ELASTICITY, 2.0, START), (ELASTICITY, 0.5, START)
    )


def _record(**changes):
    record = {
        "schema_version": records.SCHEMA_VERSION,
        "model": {
            "package": "policyengine-uk",
            "version": records.installed_model_version(),
        },
        "period": "2027",
        "resolved": None,
        "request": {"settings": [], "digest": None},
    }
    record.update(changes)
    return record


@pytest.mark.parametrize(
    "record, problem",
    [
        (None, "predates the record"),
        (_record(schema_version=0), "another schema version"),
        (
            _record(model={"package": "policyengine-uk", "version": "0.0.1"}),
            "calculated with policyengine-uk 0.0.1",
        ),
        (
            _record(request={"settings": [], "digest": "0" * 64}),
            "other capital gains response settings",
        ),
    ],
)
def test_a_saved_record_rules_out_reuse(record, problem):
    assert problem in records.saved_record_problem(
        record, {"settings": [], "digest": None}
    )


def test_a_matching_saved_record_allows_reuse():
    assert records.saved_record_problem(_record(), {"digest": None}) is None


def test_a_record_carries_the_resolved_assumption(monkeypatch):
    resolved = {"convention": "retention", "elasticity": 1.0}
    monkeypatch.setattr(records, "resolve", lambda simulation, year: resolved)
    request = {"settings": [], "digest": None}

    record = records.build_record(object(), 2027, request)

    assert record == _record(resolved=resolved, request=request)
