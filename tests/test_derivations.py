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
        choice = types.SimpleNamespace(message=message, finish_reason="stop")
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
    assert captured["kwargs"]["model"] == "claude-sonnet-5-5"
    assert captured["kwargs"]["custom_llm_provider"] == "anthropic"
    assert captured["kwargs"]["max_tokens"] == 4096
    assert captured["kwargs"]["output_config"] == {"effort": "low"}
    assert "temperature" not in captured["kwargs"]
    assert "thinking" not in captured["kwargs"]
    assert "reasoning_effort" not in captured["kwargs"]


def test_narrate_async_uses_litellm_acompletion(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_acompletion(**kwargs):
        captured["kwargs"] = kwargs
        message = types.SimpleNamespace(content="Async stub.")
        choice = types.SimpleNamespace(message=message, finish_reason="stop")
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
    assert captured["kwargs"]["model"] == "claude-sonnet-5-5"
    assert captured["kwargs"]["custom_llm_provider"] == "anthropic"
    assert captured["kwargs"]["max_tokens"] == 4096
    assert captured["kwargs"]["output_config"] == {"effort": "low"}
    assert "temperature" not in captured["kwargs"]
    assert "thinking" not in captured["kwargs"]
    assert "reasoning_effort" not in captured["kwargs"]


@pytest.fixture
def narration_derivation():
    return Derivation(
        variable="x", value=1.0, period=2026, trace=TraceNode(name="x", value=1.0)
    )


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def call_narration(request):
    def call(derivation, **kwargs):
        if request.param:
            return asyncio.run(narrate_async(derivation, **kwargs))
        return narrate(derivation, **kwargs)

    return call


@pytest.fixture
def fake_narration_client(monkeypatch):
    client = types.SimpleNamespace(
        kwargs=None,
        response=types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content=" Narrative. "),
                    finish_reason="stop",
                )
            ]
        ),
    )

    def completion(**kwargs):
        client.kwargs = kwargs
        return client.response

    async def acompletion(**kwargs):
        return completion(**kwargs)

    client.completion = completion
    client.acompletion = acompletion
    monkeypatch.setitem(__import__("sys").modules, "litellm", client)
    return client


@pytest.mark.parametrize("model", ["claude-sonnet-5-5", "anthropic/claude-sonnet-5-5"])
def test_narration_rejects_temperature_for_sonnet_55(
    call_narration, narration_derivation, fake_narration_client, model
):
    with pytest.raises(ValueError, match="does not support temperature"):
        call_narration(narration_derivation, model=model, temperature=0.0)
    assert fake_narration_client.kwargs is None


@pytest.mark.parametrize("model", ["claude-sonnet-5-5", "anthropic/claude-sonnet-5-5"])
def test_narration_rejects_litellm_dropping_effort(
    call_narration, narration_derivation, fake_narration_client, model
):
    fake_narration_client.drop_params = True
    with pytest.raises(ValueError, match="Disable LITELLM_DROP_PARAMS"):
        call_narration(narration_derivation, model=model)
    assert fake_narration_client.kwargs is None


def test_narration_preserves_custom_model_options(
    call_narration, narration_derivation, fake_narration_client
):
    fake_narration_client.drop_params = True
    result = call_narration(
        narration_derivation,
        model="custom-provider/custom-model",
        temperature=0.2,
        max_tokens=512,
    )
    assert result == "Narrative."
    kwargs = fake_narration_client.kwargs
    assert kwargs["model"] == "custom-provider/custom-model"
    assert kwargs["temperature"] == 0.2
    assert kwargs["max_tokens"] == 512
    assert "output_config" not in kwargs
    assert "custom_llm_provider" not in kwargs


@pytest.mark.parametrize("finish_reason", ["refusal", "content_filter"])
def test_narration_raises_on_refusal(
    call_narration, narration_derivation, fake_narration_client, finish_reason
):
    fake_narration_client.response.choices[0].finish_reason = finish_reason
    with pytest.raises(ValueError, match="refused"):
        call_narration(narration_derivation)


@pytest.mark.parametrize("content", [None, "", "  "])
def test_narration_raises_when_response_has_no_text(
    call_narration, narration_derivation, fake_narration_client, content
):
    fake_narration_client.response.choices[0].message.content = content
    with pytest.raises(ValueError, match="no text"):
        call_narration(narration_derivation)


@pytest.mark.parametrize("stop_reason", ["end_turn", "refusal"])
@pytest.mark.parametrize("model", ["claude-sonnet-5-5", "anthropic/claude-sonnet-5-5"])
def test_narration_litellm_provider_translation_offline(
    monkeypatch, call_narration, narration_derivation, stop_reason, model
):
    """Exercise the pinned wrapper through HTTPX's local mocked transport."""
    import json
    import socket

    def no_network(*args, **kwargs):
        raise AssertionError("This test must not make a network connection")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket.socket, "connect_ex", no_network)
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")

    import httpx
    import litellm
    from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler

    monkeypatch.setattr(litellm, "drop_params", False)
    monkeypatch.delenv("LITELLM_ANTHROPIC_DISABLE_URL_SUFFIX", raising=False)
    real_completion = litellm.completion
    real_acompletion = litellm.acompletion
    requests = []

    def handle_http_request(http_request):
        assert http_request.method == "POST"
        assert str(http_request.url) == "https://offline.invalid/v1/messages"
        request = json.loads(http_request.content)
        requests.append(request)
        assert request["model"] == "claude-sonnet-5-5"
        assert request["max_tokens"] == 4096
        assert request["output_config"] == {"effort": "low"}
        assert [message["role"] for message in request["messages"]] == ["user"]
        assert not {
            "temperature",
            "top_p",
            "top_k",
            "thinking",
            "tool_choice",
            "tools",
            "extra_body",
        }.intersection(request)
        raw = {
            "id": "msg_offline_test",
            "type": "message",
            "role": "assistant",
            "model": "claude-sonnet-5-5",
            "content": [
                {"type": "thinking", "thinking": "", "signature": "mock-signature"},
                {"type": "text", "text": "First sentence. "},
                {"type": "text", "text": "Second sentence."},
            ],
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
        return httpx.Response(200, json=raw)

    def completion(**kwargs):
        with httpx.Client(transport=httpx.MockTransport(handle_http_request)) as client:
            return real_completion(
                **kwargs,
                api_key="offline-dummy-credential",
                api_base="https://offline.invalid",
                num_retries=0,
                client=HTTPHandler(client=client),
            )

    async def acompletion(**kwargs):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handle_http_request)
        ) as client:
            handler = AsyncHTTPHandler()
            await handler.close()
            handler.client = client
            return await real_acompletion(
                **kwargs,
                api_key="offline-dummy-credential",
                api_base="https://offline.invalid",
                num_retries=0,
                client=handler,
            )

    monkeypatch.setattr(litellm, "completion", completion)
    monkeypatch.setattr(litellm, "acompletion", acompletion)
    if stop_reason == "refusal":
        with pytest.raises(ValueError, match="refused"):
            call_narration(narration_derivation, model=model)
    else:
        assert (
            call_narration(narration_derivation, model=model)
            == "First sentence. Second sentence."
        )
    assert len(requests) == 1
