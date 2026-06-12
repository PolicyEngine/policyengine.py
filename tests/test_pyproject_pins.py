"""Tests for country pin updates in pyproject.toml."""

import pytest

from policyengine.provenance.pyproject_pins import (
    PinUpdateError,
    update_country_pins,
)

PYPROJECT = """\
[project.optional-dependencies]
us = [
    "policyengine_core>=3.27.1",
    "policyengine-us==1.723.0",
]
uk = [
    "policyengine_core>=3.27.1",
    "policyengine-uk==2.89.0",
]
dev = [
    "policyengine_core>=3.27.1",
    "policyengine-us==1.723.0",
    "policyengine-uk==2.89.0",
]
"""


@pytest.fixture
def pyproject(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text(PYPROJECT)
    return path


class TestUpdateCountryPins:
    def test__given_new_versions__then_country_and_dev_pins_move(self, pyproject):
        update_country_pins(
            pyproject_path=pyproject,
            country="us",
            model_package="policyengine-us",
            model_version="1.730.0",
            core_version="3.28.0",
        )

        text = pyproject.read_text()
        assert text.count("policyengine-us==1.730.0") == 2
        assert text.count("policyengine_core>=3.28.0") == 2

    def test__given_same_versions__then_idempotent(self, pyproject):
        kwargs = dict(
            pyproject_path=pyproject,
            country="us",
            model_package="policyengine-us",
            model_version="1.723.0",
            core_version="3.27.1",
        )
        update_country_pins(**kwargs)
        first = pyproject.read_text()
        update_country_pins(**kwargs)

        assert pyproject.read_text() == first == PYPROJECT

    def test__given_us_update__then_uk_extra_untouched(self, pyproject):
        update_country_pins(
            pyproject_path=pyproject,
            country="us",
            model_package="policyengine-us",
            model_version="1.730.0",
            core_version="3.27.1",
        )

        assert "policyengine-uk==2.89.0" in pyproject.read_text()

    def test__given_stale_installed_core__then_floor_never_lowers(self, pyproject):
        update_country_pins(
            pyproject_path=pyproject,
            country="us",
            model_package="policyengine-us",
            model_version="1.730.0",
            core_version="3.26.1",
        )

        text = pyproject.read_text()
        assert "policyengine_core>=3.27.1" in text
        assert "3.26.1" not in text

    def test__given_unknown_country__then_raises(self, pyproject):
        with pytest.raises(PinUpdateError, match="unknown country"):
            update_country_pins(
                pyproject_path=pyproject,
                country="fr",
                model_package="policyengine-fr",
                model_version="1.0.0",
                core_version="3.27.1",
            )

    def test__given_wrong_model_package__then_raises(self, pyproject):
        with pytest.raises(PinUpdateError, match="expected model package"):
            update_country_pins(
                pyproject_path=pyproject,
                country="us",
                model_package="policyengine-uk",
                model_version="1.0.0",
                core_version="3.27.1",
            )
