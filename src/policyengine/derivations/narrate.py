"""LLM narration of a structured :class:`Derivation`.

This is the only piece of the derivations API that makes a network call. It
is kept in its own module so that callers who only want the deterministic
structured tree don't drag a network/LLM dependency into the import graph.

LiteLLM is imported lazily inside the call so that ``import
policyengine.derivations`` doesn't require any LLM credentials to succeed.
"""

from __future__ import annotations

from typing import Any

from .trace import Derivation

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 500
DEFAULT_TEMPERATURE = 0.0


def _build_prompt(
    derivation: Derivation,
    *,
    country: str | None,
    household_summary: str | None,
    extra_context: str | None,
    trace_max_depth: int,
) -> str:
    header_lines = [
        "You are summarizing how PolicyEngine derived a single variable's value "
        "for one household.",
        "",
        f"VARIABLE: {derivation.variable}",
        f"PERIOD: {derivation.period}",
        f"REFERENCE VALUE: {derivation.value}",
    ]
    if country:
        header_lines.insert(3, f"COUNTRY: {country.upper()}")
    if household_summary:
        header_lines.append(f"HOUSEHOLD: {household_summary}")
    if extra_context:
        header_lines.append("")
        header_lines.append(extra_context)

    trace_text = derivation.trace_text(max_depth=trace_max_depth)
    instructions = (
        "Write a 3-5 sentence narrative explaining how PolicyEngine arrived at "
        "this value. Reference the most important intermediate quantities by "
        "name and amount. Be concrete and quantitative. Plain prose, no "
        "headers, no bullet lists."
    )
    return (
        "\n".join(header_lines) + "\n\nPolicyEngine computation trace "
        "(indented dependency tree, non-zero nodes only):\n```\n"
        + trace_text
        + "\n```\n\n"
        + instructions
        + "\n"
    )


def narrate(
    derivation: Derivation,
    *,
    country: str | None = None,
    household_summary: str | None = None,
    extra_context: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    trace_max_depth: int = 8,
) -> str:
    """Synchronously ask an LLM to narrate this derivation.

    Imports LiteLLM lazily so that ``import policyengine.derivations`` has no
    LLM dependency. Returns the model's response text.
    """
    import litellm  # noqa: PLC0415 — lazy import keeps the base module light

    prompt = _build_prompt(
        derivation,
        country=country,
        household_summary=household_summary,
        extra_context=extra_context,
        trace_max_depth=trace_max_depth,
    )
    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


async def narrate_async(
    derivation: Derivation,
    *,
    country: str | None = None,
    household_summary: str | None = None,
    extra_context: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    trace_max_depth: int = 8,
) -> str:
    """Async variant of :func:`narrate` — same interface, awaitable result."""
    import litellm  # noqa: PLC0415 — lazy import keeps the base module light

    prompt = _build_prompt(
        derivation,
        country=country,
        household_summary=household_summary,
        extra_context=extra_context,
        trace_max_depth=trace_max_depth,
    )
    response: Any = await litellm.acompletion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()
