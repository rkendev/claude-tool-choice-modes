"""Tests for the tool_choice modes showcase.

Eight tests, no live network on ``make check``: tool schema shape,
both local lookup functions (happy + unknown-city), three VCR-replayed
round-trips (one per mode), and two synthetic-mock loop-control tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from claude_tool_choice_modes.showcase import (
    MAX_ITERATIONS,
    RoundTripIterationError,
    run_with_choice,
)
from claude_tool_choice_modes.tools import (
    ALL_TOOLS,
    COUNTRY_TOOL,
    POPULATION_TOOL,
    get_city_country,
    get_city_population,
)


def test_tool_schemas_are_well_formed() -> None:
    """Both tool schemas pass the CCA-F D2 shape checks."""
    for tool in (POPULATION_TOOL, COUNTRY_TOOL):
        schema = tool["input_schema"]
        assert schema["type"] == "object"
        assert set(schema["properties"]) == {"city"}
        assert schema["properties"]["city"]["type"] == "string"
        assert schema["required"] == ["city"]
        assert schema["additionalProperties"] is False
    assert {t["name"] for t in ALL_TOOLS} == {
        "get_city_population",
        "get_city_country",
    }


def test_get_city_population_known_value() -> None:
    assert get_city_population("Tokyo") == 14094034
    assert get_city_population("Amsterdam") == 921402


def test_get_city_country_known_value() -> None:
    assert get_city_country("Tokyo") == "Japan"
    assert get_city_country("Amsterdam") == "Netherlands"


def test_get_city_unknown_raises() -> None:
    """Both local lookup functions raise ValueError on an unknown city."""
    with pytest.raises(ValueError, match="unknown city"):
        get_city_population("Atlantis")
    with pytest.raises(ValueError, match="unknown city"):
        get_city_country("Atlantis")


@pytest.mark.vcr
def test_choice_auto_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    """`auto` mode round-trip — pin to whatever the cassette recorded.

    `auto` is non-deterministic; the test does not assert tool_calls is
    empty. It only asserts the run completes and ends with `end_turn`.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "cassette-replay-dummy-key")
    result = run_with_choice(
        "What's the population of Tokyo?",
        tool_choice={"type": "auto"},
    )
    assert result.mode_label == "auto"
    assert "end_turn" in result.stop_reasons
    assert result.stop_reasons[-1] == "end_turn"


@pytest.mark.vcr
def test_choice_any_forces_tool_use(monkeypatch: pytest.MonkeyPatch) -> None:
    """`any` mode forces a tool call — deterministic across replays."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "cassette-replay-dummy-key")
    result = run_with_choice(
        "What's the population of Tokyo?",
        tool_choice={"type": "any"},
    )
    assert result.mode_label == "any"
    assert result.stop_reasons[0] == "tool_use"
    assert result.stop_reasons[-1] == "end_turn"
    assert len(result.tool_calls) >= 1


@pytest.mark.vcr
def test_choice_specific_tool_forces_named(monkeypatch: pytest.MonkeyPatch) -> None:
    """Named-tool mode forces THE SPECIFIC tool, even when the wrong one for the question.

    Question is about population; we force `get_city_country`. The
    architect's override beats Claude's natural routing.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "cassette-replay-dummy-key")
    result = run_with_choice(
        "What's the population of Tokyo?",
        tool_choice={"type": "tool", "name": "get_city_country"},
    )
    assert result.mode_label == "tool:get_city_country"
    # `disable_parallel_tool_use` is not set, so Claude can return
    # multiple tool_use blocks in one response (the cassette shows
    # country + population called in parallel). Order isn't guaranteed
    # across re-records — assert the named tool appears anywhere in
    # the call list rather than pinning it to index 0.
    assert "get_city_country" in [c[0] for c in result.tool_calls]
    assert result.stop_reasons[-1] == "end_turn"


def test_iteration_cap_raises() -> None:
    """A stuck tool_use loop raises after MAX_ITERATIONS rounds."""
    fake_client = MagicMock()
    stuck = MagicMock()
    stuck.stop_reason = "tool_use"
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "get_city_population"
    tool_block.id = "stub_id"
    tool_block.input = {"city": "Tokyo"}
    tool_block.model_dump.return_value = {"type": "tool_use"}
    stuck.content = [tool_block]
    fake_client.messages.create.return_value = stuck

    with pytest.raises(RoundTripIterationError, match=r"iteration cap"):
        run_with_choice(
            "stuck loop test",
            tool_choice={"type": "any"},
            client=fake_client,
        )

    assert fake_client.messages.create.call_count == MAX_ITERATIONS


def test_unexpected_stop_reason_raises() -> None:
    """A non-{tool_use, end_turn} stop_reason aborts the loop."""
    fake_client = MagicMock()
    weird = MagicMock()
    weird.stop_reason = "max_tokens"
    weird.content = []
    fake_client.messages.create.return_value = weird

    with pytest.raises(RoundTripIterationError, match=r"unexpected stop_reason"):
        run_with_choice(
            "weird stop_reason",
            tool_choice={"type": "auto"},
            client=fake_client,
        )
