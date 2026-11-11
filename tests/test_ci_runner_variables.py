"""Which runner each CI job uses, and what the runner variables can move.

pr_code_changes.yaml explains the variables. These tests hold the workflows
to them:

1. Each covered job's ``runs-on`` is the one runner expression, built from
   its variable and ubuntu-latest, so an unset variable keeps ubuntu-latest.
2. Every other job keeps a literal GitHub-hosted label. Versioning, Publish,
   NotifyConsumers, the docs deploy and the certification jobs that resolve,
   prepare, catch up, accept and promote never move.
3. The expression picks the variable's runner exactly when the variable is
   set and CI_RUNNER_EVENTS is empty or lists the run's event, matched as a
   whole name: "pull_request" never matches "pull_request_target".
4. Every job that CI_RUNNER_X64 can move has a GITHUB_TOKEN that can only
   read: the organisation's default token can write, and a moved job takes
   its token to the other runner. The certification jobs keep their write
   token and the GitHub App key, so they have their own variable, for
   GitHub-hosted larger runners only.
"""

from itertools import product
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"

X64 = "ubuntu-latest"

# (workflow, job) -> variable
COVERED = {
    ("pr_code_changes.yaml", "check-changelog"): "CI_RUNNER_X64",
    ("pr_code_changes.yaml", "Lint"): "CI_RUNNER_X64",
    ("pr_code_changes.yaml", "Mypy"): "CI_RUNNER_X64",
    ("pr_code_changes.yaml", "Python-Compat"): "CI_RUNNER_X64",
    ("pr_code_changes.yaml", "BundleVerification"): "CI_RUNNER_X64",
    ("pr_code_changes.yaml", "Test"): "CI_RUNNER_X64",
    ("pr_docs_changes.yaml", "Test"): "CI_RUNNER_X64",
    ("push.yaml", "Lint"): "CI_RUNNER_X64",
    ("push.yaml", "Test"): "CI_RUNNER_X64",
    ("certify-uk-release.yaml", "qualify"): "CERTIFY_RUNNER_X64",
    ("certify-uk-release.yaml", "replay"): "CERTIFY_RUNNER_X64",
}

NEVER_MOVED = {
    ("push.yaml", "Docs"),
    ("push.yaml", "Versioning"),
    ("push.yaml", "Publish"),
    ("push.yaml", "NotifyConsumers"),
    ("certify-uk-release.yaml", "resolve"),
    ("certify-uk-release.yaml", "prepare"),
    ("certify-uk-release.yaml", "catch-up"),
    ("certify-uk-release.yaml", "accept"),
    ("certify-uk-release.yaml", "promote"),
}


def runner_expression(variable, label=X64):
    return (
        f"${{{{ vars.{variable} != '' && (vars.CI_RUNNER_EVENTS == '' || "
        "contains(format(',{0},', vars.CI_RUNNER_EVENTS), format(',{0},', github.event_name))) "
        f"&& vars.{variable} || '{label}' }}}}"
    )


def documents():
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        yield path.name, yaml.safe_load(path.read_text(encoding="utf-8"))


def jobs():
    for name, document in documents():
        for job_name, job in document["jobs"].items():
            if "runs-on" in job:
                yield (name, job_name), job["runs-on"]


# Invariant 1.


def test_covered_jobs_use_the_runner_expression():
    found = dict(jobs())
    for key, variable in COVERED.items():
        assert found[key] == runner_expression(variable), key


# Invariant 2.


def test_every_other_job_keeps_a_github_hosted_label():
    found = dict(jobs())
    assert NEVER_MOVED <= set(found)
    for key, runs_on in found.items():
        if key in COVERED:
            continue
        assert runs_on == X64, (key, runs_on)


# Invariant 3: the expression's rule, as GitHub evaluates it. "a && b || c"
# gives b when a and b are non-empty, else c; an unset variable is "".


def chosen_runner(variable_value, events_value, event, label=X64):
    if variable_value != "" and (
        events_value == "" or f",{event}," in f",{events_value},"
    ):
        return variable_value
    return label


EVENTS = [
    "pull_request",
    "pull_request_target",
    "push",
    "workflow_dispatch",
    "repository_dispatch",
    "schedule",
]
EVENT_LISTS = [
    "",
    "push",
    "push,workflow_dispatch",
    "pull_request",
    "pull_request_target",
    "repository_dispatch,schedule,workflow_dispatch",
]


@pytest.mark.parametrize(
    "variable_value,events_value,event",
    list(product(["", "pe-x64-4core"], EVENT_LISTS, EVENTS)),
)
def test_the_variable_applies_only_to_the_listed_events(
    variable_value, events_value, event
):
    chosen = chosen_runner(variable_value, events_value, event)
    listed = events_value == "" or event in events_value.split(",")
    if variable_value and listed:
        assert chosen == variable_value
    else:
        assert chosen == X64


# Invariant 4.


def test_ci_runner_jobs_hold_a_read_only_token():
    workflows = dict(documents())
    for (workflow, job_name), variable in COVERED.items():
        if variable != "CI_RUNNER_X64":
            continue
        document = workflows[workflow]
        job = document["jobs"][job_name]
        # A job's own permissions replace the workflow's; with neither, the
        # job gets the organisation's default token, which can write.
        permissions = job.get("permissions", document.get("permissions"))
        assert isinstance(permissions, dict), (workflow, job_name)
        for scope, level in permissions.items():
            assert level in ("read", "none") or scope == "id-token", (
                workflow,
                job_name,
                scope,
                level,
            )
