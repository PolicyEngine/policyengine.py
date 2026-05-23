"""Tests for ``policyengine.derivations``.

The deterministic part is exercised against a small US household; the
narration path is exercised with a fake LiteLLM client so the test stays
hermetic.
"""

from __future__ import annotations

import asyncio
import types

import pytest

from policyengine.derivations import (
    Derivation,
    TraceNode,
    derive,
    is_zero_value,
    narrate,
    narrate_async,
    top_level_contributions,
)


def _us_simulation() -> object:
    """Return a US Simulation set up with a single working adult.

    Skipped if ``policyengine_us`` is not installed in this environment.
    """
    pytest.importorskip("policyengine_us")
    from policyengine_us import Simulation  # type: ignore

    return Simulation(
        situation={
            "people": {
                "head": {
                    "age": {2026: 35},
                    "employment_income": {2026: 45000},
                }
            },
            "tax_units": {"tu": {"members": ["head"]}},
            "households": {"h": {"members": ["head"], "state_code": {2026: "TX"}}},
        }
    )


def test_is_zero_value_handles_scalars_and_arrays():
    assert is_zero_value(0)
    assert is_zero_value(0.0)
    assert is_zero_value(False)
    assert not is_zero_value(1)
    assert not is_zero_value(True)
    assert not is_zero_value(0.01)


def test_derive_returns_structured_tree_for_us_income_tax():
    sim = _us_simulation()
    derivation = derive(sim, "income_tax_before_credits", 2026)

    assert isinstance(derivation, Derivation)
    assert derivation.variable == "income_tax_before_credits"
    assert isinstance(derivation.value, float)
    assert derivation.value > 0
    assert isinstance(derivation.trace, TraceNode)
    assert derivation.trace.name == "income_tax_before_credits"
    # Tree should include the canonical AGI/taxable-income path. We don't
    # bind to specific numerics so the test stays stable across model
    # parameter updates.
    text = derivation.trace_text(max_depth=4)
    assert "taxable_income" in text
    assert "adjusted_gross_income" in text


def test_top_level_contributions_lists_immediate_children():
    sim = _us_simulation()
    derivation = derive(sim, "income_tax_before_credits", 2026)

    contributions = top_level_contributions(derivation)
    assert contributions, "expected at least one top-level dependency"
    names = {name for name, _ in contributions}
    # ``income_tax_before_credits`` is the sum of regular tax, AMT, capital
    # gains tax, etc. We check for the rates path which is always present.
    assert "income_tax_main_rates" in names


def test_trace_text_drops_zero_subtrees_below_depth_one():
    leaf_zero = TraceNode(name="dependent_zero_thing", value=0.0)
    leaf_nonzero = TraceNode(name="dependent_real_thing", value=5.0)
    intermediate = TraceNode(
        name="payable_component",
        value=0.0,
        children=(leaf_zero, leaf_nonzero),
    )
    root = TraceNode(name="root_var", value=5.0, children=(intermediate,))

    text = root.to_text()
    # Top-level zero is preserved (depth 1) so the caller sees the category.
    assert "payable_component = 0" in text
    # Zero leaves under it are dropped.
    assert "dependent_zero_thing" not in text
    # Non-zero leaves are kept.
    assert "dependent_real_thing = 5" in text


def test_trace_text_shows_per_entity_values_with_sum():
    # Multi-person households: per-person values come through as tuples and
    # render as "sum (per entity: a, b)" so summarisers don't silently drop
    # the spouse's contribution.
    root = TraceNode(
        name="irs_gross_income",
        value=(45000.0, 40000.0),
    )
    text = root.to_text()
    assert "85000" in text
    assert "45000" in text
    assert "40000" in text
    assert "per entity" in text


def test_is_zero_value_handles_multi_entity_tuples():
    assert is_zero_value((0, 0, 0))
    assert is_zero_value((False, False))
    assert not is_zero_value((0, 1))
    assert not is_zero_value((False, True))


def test_narrate_passes_trace_to_litellm(monkeypatch):
    captured: dict[str, object] = {}

    def fake_completion(**kwargs):
        captured["kwargs"] = kwargs
        message = types.SimpleNamespace(content="Stub narrative.")
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(choices=[choice])

    monkeypatch.setitem(
        __import__("sys").modules,
        "litellm",
        types.SimpleNamespace(completion=fake_completion),
    )

    derivation = Derivation(
        variable="federal_income_tax",
        value=4454.8,
        period=2026,
        trace=TraceNode(
            name="federal_income_tax",
            value=4454.8,
            children=(
                TraceNode(name="adjusted_gross_income", value=81820.85),
                TraceNode(name="standard_deduction", value=16100),
            ),
        ),
    )

    narrative = narrate(
        derivation,
        country="us",
        household_summary="TX, joint, 2 adults, ~$85k income",
    )
    assert narrative == "Stub narrative."
    prompt = captured["kwargs"]["messages"][0]["content"]
    assert "federal_income_tax" in prompt
    assert "adjusted_gross_income = 81820.85" in prompt
    assert "TX, joint, 2 adults, ~$85k income" in prompt
    assert "COUNTRY: US" in prompt


def test_narrate_async_uses_litellm_acompletion(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_acompletion(**kwargs):
        captured["kwargs"] = kwargs
        message = types.SimpleNamespace(content="Async stub.")
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(choices=[choice])

    monkeypatch.setitem(
        __import__("sys").modules,
        "litellm",
        types.SimpleNamespace(acompletion=fake_acompletion),
    )

    derivation = Derivation(
        variable="x",
        value=1.0,
        period=2026,
        trace=TraceNode(name="x", value=1.0),
    )
    result = asyncio.run(narrate_async(derivation))
    assert result == "Async stub."
    assert captured["kwargs"]["model"] == "claude-sonnet-4-6"
