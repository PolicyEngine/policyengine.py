"""Decile convenience construction preserves explicit measurement choices."""

from types import SimpleNamespace

import pytest

from policyengine.core.spm import SPMSelection
from policyengine.outputs import decile_impact


def test_decile_factory_uses_same_explicit_selection_for_baseline_and_reform(
    monkeypatch,
):
    selection = SPMSelection(geography_kind="national", scenario="zero_real")
    created = []

    def construct(**kwargs):
        simulation = SimpleNamespace(**kwargs, ensure=lambda: None)
        created.append(simulation)
        return simulation

    class AnalysisReached(Exception):
        pass

    def analyse(baseline, reform, **kwargs):
        assert baseline.spm == reform.spm == selection
        raise AnalysisReached

    monkeypatch.setattr(decile_impact, "Simulation", construct)
    monkeypatch.setattr(decile_impact, "_prepare_decile_analysis", analyse)
    with pytest.raises(AnalysisReached):
        decile_impact.calculate_decile_impacts(
            dataset=object(), tax_benefit_model_version=object(), spm=selection
        )
    assert len(created) == 2


def test_decile_supplied_simulations_cannot_silently_ignore_selection():
    with pytest.raises(ValueError, match="supplied simulations"):
        decile_impact.calculate_decile_impacts(
            baseline_simulation=object(),
            reform_simulation=object(),
            spm=SPMSelection(geography_kind="national"),
        )
