"""One round-trip per `tool_choice` mode, captured as a structured RunResult.

Same loop shape as Artifact B's ``run_roundtrip``, with two differences:
the ``tool_choice`` parameter is forwarded to ``client.messages.create``,
and the function returns a ``RunResult`` so the CLI can compare modes
side-by-side.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from anthropic import Anthropic

from .tools import ALL_TOOLS, COUNTRY_TOOL, POPULATION_TOOL, get_city_country, get_city_population

MODEL_DEFAULT = "claude-haiku-4-5-20251001"
MAX_ITERATIONS = 5
MAX_TOKENS = 1024


def _call_population(city: str) -> str:
    return str(get_city_population(city))


def _call_country(city: str) -> str:
    return get_city_country(city)


_TOOL_DISPATCH: dict[str, Callable[[str], str]] = {
    "get_city_population": _call_population,
    "get_city_country": _call_country,
}


class RoundTripIterationError(RuntimeError):
    """Raised on iteration cap or an unexpected ``stop_reason``."""


@dataclass(frozen=True)
class RunResult:
    """Captures one round-trip's protocol-visible behavior."""

    mode_label: str
    stop_reasons: list[str] = field(default_factory=list)
    tool_calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    final_text: str = ""


def _label_for(tool_choice: dict[str, Any]) -> str:
    kind = tool_choice["type"]
    if kind == "tool":
        return f"tool:{tool_choice['name']}"
    return cast(str, kind)


def run_with_choice(
    question: str,
    tool_choice: dict[str, Any],
    *,
    model: str = MODEL_DEFAULT,
    client: Anthropic | None = None,
) -> RunResult:
    """Run a single round-trip with the given ``tool_choice`` and return a RunResult.

    Branch on ``stop_reason``: ``tool_use`` dispatches the named local
    function, appends a ``tool_result`` user turn, continues. ``end_turn``
    captures the text and returns. Anything else raises
    ``RoundTripIterationError``. Iteration cap: ``MAX_ITERATIONS``.
    """
    if client is None:
        client = Anthropic()

    label = _label_for(tool_choice)
    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]
    stop_reasons: list[str] = []
    tool_calls: list[tuple[str, dict[str, Any]]] = []

    print(f"[step 1] tools sent to Claude: {[t['name'] for t in ALL_TOOLS]}")
    print(f"[step 1] tool_choice: {json.dumps(tool_choice)}")

    for iteration in range(MAX_ITERATIONS):
        # Force tool_choice ONLY on the first turn. Once Claude has
        # produced a tool_use under the forced mode, subsequent turns
        # use {"type": "auto"} so Claude can synthesize a final
        # end_turn response — otherwise `any` and `tool:NAME` modes
        # loop forever (the protocol re-forces a tool_use every turn).
        active_choice: dict[str, Any] = tool_choice if iteration == 0 else {"type": "auto"}
        resp = client.messages.create(  # type: ignore[call-overload]
            model=model,
            max_tokens=MAX_TOKENS,
            tools=[POPULATION_TOOL, COUNTRY_TOOL],
            tool_choice=active_choice,
            messages=messages,
        )

        stop_reasons.append(cast(str, resp.stop_reason))

        if resp.stop_reason == "tool_use":
            print(f"[step {iteration + 2}] stop_reason=tool_use")
            tool_result_blocks: list[dict[str, Any]] = []
            for tool_block in (b for b in resp.content if b.type == "tool_use"):
                raw_input = cast("dict[str, Any]", tool_block.input)
                tool_calls.append((tool_block.name, raw_input))
                print(f"  tool_use: name={tool_block.name} input={json.dumps(raw_input)}")

                tool_func = _TOOL_DISPATCH[tool_block.name]
                result = tool_func(raw_input["city"])
                print(f"  local result: {result}")

                tool_result_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": str(result),
                    }
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": [b.model_dump() for b in resp.content],
                }
            )
            messages.append({"role": "user", "content": tool_result_blocks})
            continue

        if resp.stop_reason == "end_turn":
            text = "".join(block.text for block in resp.content if block.type == "text")
            print(f"[step {iteration + 2}] stop_reason=end_turn")
            print(f"  text: {text!r}")
            return RunResult(
                mode_label=label,
                stop_reasons=stop_reasons,
                tool_calls=tool_calls,
                final_text=text,
            )

        raise RoundTripIterationError(
            f"unexpected stop_reason at iteration {iteration}: {resp.stop_reason!r}"
        )

    raise RoundTripIterationError(f"iteration cap ({MAX_ITERATIONS}) reached without end_turn")
