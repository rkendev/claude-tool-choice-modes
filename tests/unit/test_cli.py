"""CLI plumbing tests for ``python -m claude_tool_choice_modes``.

Mocks ``run_with_choice`` so no network is involved — the goal is
covering the argument parsing, mode dispatch, env validation, and
summary printing in ``__main__.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from claude_tool_choice_modes import __main__ as cli_module
from claude_tool_choice_modes.__main__ import _parse_mode, main
from claude_tool_choice_modes.showcase import RunResult


def _stub_run_with_choice(*, label: str, stop_reasons: list[str]) -> Any:
    def _stub(question: str, tool_choice: dict[str, Any], **_: Any) -> RunResult:
        return RunResult(
            mode_label=label,
            stop_reasons=stop_reasons,
            tool_calls=[],
            final_text="stub",
        )

    return _stub


class TestParseMode:
    def test_all_returns_three_choices(self) -> None:
        choices = _parse_mode("all")
        assert [c["type"] for c in choices] == ["auto", "any", "tool"]
        assert choices[2]["name"] == "get_city_country"

    def test_auto(self) -> None:
        assert _parse_mode("auto") == [{"type": "auto"}]

    def test_any(self) -> None:
        assert _parse_mode("any") == [{"type": "any"}]

    def test_tool_named(self) -> None:
        assert _parse_mode("tool:get_city_population") == [
            {"type": "tool", "name": "get_city_population"}
        ]

    def test_tool_unknown_name_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown tool name"):
            _parse_mode("tool:get_city_weather")

    def test_unknown_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown --mode"):
            _parse_mode("bogus")


class TestMain:
    def test_missing_api_key_returns_1(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        rc = main(["What's the population of Tokyo?"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "ANTHROPIC_API_KEY" in err

    def test_invalid_mode_returns_1(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "stub")
        rc = main(["--mode", "bogus", "Q"])
        assert rc == 1
        assert "unknown --mode" in capsys.readouterr().err

    def test_all_mode_runs_three_and_prints_summary(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "stub")

        calls: list[dict[str, Any]] = []

        def _stub(question: str, tool_choice: dict[str, Any], **_: Any) -> RunResult:
            calls.append(tool_choice)
            label = (
                tool_choice["type"]
                if tool_choice["type"] != "tool"
                else f"tool:{tool_choice['name']}"
            )
            return RunResult(
                mode_label=label,
                stop_reasons=["end_turn"],
                tool_calls=[],
                final_text="ok",
            )

        monkeypatch.setattr(cli_module, "run_with_choice", _stub)
        rc = main(["What's the population of Tokyo?"])
        assert rc == 0
        assert [c["type"] for c in calls] == ["auto", "any", "tool"]
        out = capsys.readouterr().out
        assert "[summary]" in out
        assert "auto" in out and "any" in out and "tool:get_city_country" in out

    def test_single_mode_no_summary(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "stub")
        monkeypatch.setattr(
            cli_module,
            "run_with_choice",
            _stub_run_with_choice(label="auto", stop_reasons=["end_turn"]),
        )
        rc = main(["--mode", "auto", "Q"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "[summary]" not in out
        assert "[result]" in out
