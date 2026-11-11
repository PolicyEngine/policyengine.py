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


@pytest.fixture(autouse=True)
def _index_install(monkeypatch):
    """Run as if policyengine-uk came from a package index, however it is
    installed here. Tests of other sources set their own."""
    monkeypatch.setattr(records, "installed_model_source", lambda: None)


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
            "source": None,
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
            _record(
                model={"package": "policyengine-uk", "version": "0.0.1", "source": None}
            ),
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


GIT = {"kind": "vcs", "vcs": "git", "commit": "c6c77ef3"}


@pytest.mark.parametrize(
    "direct_url, source",
    [
        (None, None),
        (
            '{"url": "https://github.com/PolicyEngine/policyengine-uk", '
            '"vcs_info": {"vcs": "git", "commit_id": "c6c77ef3", '
            '"requested_revision": "cgt-retention-default-2396"}}',
            GIT,
        ),
        (
            '{"url": "file:///home/user/policyengine-uk", '
            '"dir_info": {"editable": true}}',
            {"kind": "directory", "editable": True},
        ),
        (
            '{"url": "file:///home/user/policyengine-uk", "dir_info": {}}',
            {"kind": "directory", "editable": False},
        ),
        (
            '{"url": "https://example.org/policyengine_uk-2.131.0.whl", '
            '"archive_info": {"hashes": {"sha256": "ab12"}}}',
            {"kind": "archive", "sha256": "ab12"},
        ),
        (
            '{"url": "https://example.org/policyengine_uk-2.131.0.tar.gz", '
            '"archive_info": {"hash": "sha256=ab12"}}',
            {"kind": "archive", "sha256": "ab12"},
        ),
        (
            '{"url": "https://example.org/policyengine_uk-2.131.0.tar.gz", '
            '"archive_info": {}}',
            {"kind": "archive", "sha256": None},
        ),
        ("not json", {"kind": "unknown"}),
    ],
)
def test_the_install_source_is_read_from_direct_url(direct_url, source):
    # URLs are left out: a local path names the machine a run was on.
    assert records.source_from_direct_url(direct_url) == source


@pytest.mark.parametrize(
    "saved, installed, problem",
    [
        (None, None, None),
        (GIT, GIT, None),
        # A branch can report the version of a published release.
        (None, GIT, "from a package index, not from git commit c6c77ef3"),
        (GIT, None, "from git commit c6c77ef3, not from a package index"),
        (GIT, {**GIT, "commit": "d4e5f6a7"}, "not from git commit d4e5f6a7"),
        (None, {"kind": "directory", "editable": True}, "an editable local"),
        (
            {"kind": "directory", "editable": False},
            {"kind": "directory", "editable": False},
            "a local directory, whose code can change",
        ),
        (None, {"kind": "archive", "sha256": None}, "an unhashed archive"),
        (None, {"kind": "unknown"}, "an unrecognised source"),
    ],
)
def test_a_saved_output_is_reused_only_from_the_same_pinned_install(
    monkeypatch, saved, installed, problem
):
    monkeypatch.setattr(records, "installed_model_source", lambda: installed)
    record = _record(
        model={
            "package": "policyengine-uk",
            "version": records.installed_model_version(),
            "source": saved,
        }
    )

    found = records.saved_record_problem(record, {"digest": None})

    if problem is None:
        assert found is None
    else:
        assert problem in found


def test_a_record_carries_the_install_source(monkeypatch):
    monkeypatch.setattr(records, "installed_model_source", lambda: GIT)
    monkeypatch.setattr(records, "resolve", lambda simulation, year: None)

    record = records.build_record(object(), 2027, None)

    assert record["model"]["source"] == GIT
