"""Importing a maintenance script leaves the interpreter as it was.

Tests import the scripts under ``scripts/`` as modules. A script that put the
checkout's ``src`` first on ``sys.path`` when imported made every later test in
the session read ``src/policyengine.egg-info``, which editable setuptools
installs leave behind, as the installed distribution's metadata (#623). Only a
script's entry point, under ``if __name__ == "__main__":``, sets up the import
path or environment it runs with.
"""

import json
import os
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import pytest

from tests.fixtures.import_path import ADDED_BY_COLLECTION, CHECKOUT, SCRIPTS_DIR

SCRIPT_NAMES = sorted(path.stem for path in SCRIPTS_DIR.glob("*.py"))
SKIP_COUNTRY_IMPORTS = "POLICYENGINE_SKIP_COUNTRY_IMPORTS"

# Runs in a fresh interpreter, so no earlier import is cached and each script's
# module code (and its sibling scripts') runs again for every name.
PROBE = """
import importlib, json, os, sys

scripts_dir, names = sys.argv[1], sys.argv[2:]
# Import policyengine once without the country models: the scripts' imports of
# it are then cheap, and an environment default a script sets stays visible.
os.environ["POLICYENGINE_SKIP_COUNTRY_IMPORTS"] = "1"
import policyengine
del os.environ["POLICYENGINE_SKIP_COUNTRY_IMPORTS"]
sys.path.insert(0, scripts_dir)
results = {}
for name in names:
    for script in names:
        sys.modules.pop(script, None)
    path, environment = list(sys.path), dict(os.environ)
    try:
        importlib.import_module(name)
    except BaseException as error:
        results[name] = {"error": f"{type(error).__name__}: {error}"}
    else:
        results[name] = {
            "path_before": path,
            "path_after": list(sys.path),
            "environment_changes": {
                key: [environment.get(key), os.environ.get(key)]
                for key in sorted(set(environment) | set(os.environ))
                if environment.get(key) != os.environ.get(key)
            },
        }
    sys.path[:] = path
    os.environ.clear()
    os.environ.update(environment)
print(json.dumps(results))
"""


@pytest.fixture(scope="module")
def script_imports(tmp_path_factory):
    environment = {
        key: value for key, value in os.environ.items() if key != SKIP_COUNTRY_IMPORTS
    }
    result = subprocess.run(
        [sys.executable, "-c", PROBE, str(SCRIPTS_DIR), *SCRIPT_NAMES],
        cwd=tmp_path_factory.mktemp("script-imports"),
        env=environment,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout.splitlines()[-1])


def test_the_probe_covers_the_release_scripts():
    assert {"bundle", "certify_data_release", "generate_bundle_artifacts"} <= set(
        SCRIPT_NAMES
    )


@pytest.mark.parametrize("name", SCRIPT_NAMES)
def test_importing_a_script_leaves_sys_path_alone(script_imports, name):
    outcome = script_imports[name]
    assert "error" not in outcome, outcome.get("error")
    before, after = outcome["path_before"], outcome["path_after"]
    assert after == before, (
        f"importing scripts/{name}.py added {[e for e in after if e not in before]} "
        f"and removed {[e for e in before if e not in after]}"
    )


@pytest.mark.parametrize("name", SCRIPT_NAMES)
def test_importing_a_script_leaves_the_environment_alone(script_imports, name):
    outcome = script_imports[name]
    assert "error" not in outcome, outcome.get("error")
    assert outcome["environment_changes"] == {}


def test_collecting_tests_adds_no_checkout_directory_to_sys_path(pytestconfig):
    assert pytestconfig.stash[ADDED_BY_COLLECTION] == []


def test_policyengine_metadata_is_not_read_from_the_source_tree():
    src = (CHECKOUT / "src").resolve()
    locations = [
        Path(distribution.locate_file("")).resolve()
        for distribution in metadata.distributions(name="policyengine")
    ]
    if all(location == src for location in locations):
        pytest.skip("policyengine is installed only from the checkout's src")
    # importlib.metadata.distribution() returns the first one on sys.path.
    assert locations[0] != src


@pytest.mark.parametrize(
    "arguments",
    [
        ("scripts/certify_data_release.py", "--help"),
        ("scripts/generate_receipt_schemas.py", "--check"),
    ],
)
def test_entry_points_set_up_their_own_imports(arguments):
    environment = {
        key: value for key, value in os.environ.items() if key != SKIP_COUNTRY_IMPORTS
    }
    result = subprocess.run(
        [sys.executable, *arguments],
        cwd=CHECKOUT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
