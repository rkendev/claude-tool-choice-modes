"""CLI entrypoint: ``python -m claude_tool_choice_modes "<question>" [--mode ...]``.

Runs the same prompt against the same two tools with one or all three
``tool_choice`` modes and prints each round-trip's protocol-visible
behavior. ``--mode all`` (default) appends a comparison summary block.
"""

from __future__ import annotations

import argparse
import os
import sys

from .showcase import MODEL_DEFAULT, RunResult, run_with_choice
from .tools import ALL_TOOLS

VALID_TOOL_NAMES = {t["name"] for t in ALL_TOOLS}
DEFAULT_NAMED_TOOL = "get_city_country"


def _parse_mode(mode: str) -> list[dict[str, object]]:
    """Translate ``--mode`` into a list of ``tool_choice`` dicts to run."""
    if mode == "all":
        return [
            {"type": "auto"},
            {"type": "any"},
            {"type": "tool", "name": DEFAULT_NAMED_TOOL},
        ]
    if mode == "auto":
        return [{"type": "auto"}]
    if mode == "any":
        return [{"type": "any"}]
    if mode.startswith("tool:"):
        name = mode.split(":", 1)[1]
        if name not in VALID_TOOL_NAMES:
            raise ValueError(f"unknown tool name {name!r}; valid: {sorted(VALID_TOOL_NAMES)}")
        return [{"type": "tool", "name": name}]
    raise ValueError(f"unknown --mode {mode!r}; expected auto, any, tool:NAME, or all")


def _print_header(choice: dict[str, object]) -> None:
    bar = "=" * 60
    print(bar)
    label = choice["type"] if choice["type"] != "tool" else f"tool:{choice['name']}"
    print(f"[mode: {label}]   tool_choice = {choice}")
    print(bar)


def _print_result(r: RunResult) -> None:
    print(f"[result] stop_reasons: {r.stop_reasons}")
    print(f"         tool_calls: {r.tool_calls}")
    print(f"         final_text: {r.final_text!r}")


def _print_summary(results: list[RunResult]) -> None:
    bar = "=" * 60
    print(bar)
    print("[summary] same prompt, same tools, three different stop_reason patterns:")
    width = max(len(r.mode_label) for r in results)
    for r in results:
        print(f"  {r.mode_label.ljust(width)} → {r.stop_reasons}")
    print(bar)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m claude_tool_choice_modes",
        description=(
            "Run the same prompt against the same two tools with one or all "
            "three tool_choice modes and compare the resulting stop_reason "
            "patterns side-by-side."
        ),
    )
    parser.add_argument(
        "question",
        help='Natural-language question, e.g. "What\'s the population of Tokyo?"',
    )
    parser.add_argument(
        "--mode",
        default="all",
        help=(
            "One of: auto, any, tool:NAME, or all (default). "
            f"Valid tool names: {sorted(VALID_TOOL_NAMES)}."
        ),
    )
    parser.add_argument(
        "--model",
        default=MODEL_DEFAULT,
        help=f"Anthropic model id (default: {MODEL_DEFAULT}).",
    )
    args = parser.parse_args(argv)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "error: ANTHROPIC_API_KEY is not set; export it before running.",
            file=sys.stderr,
        )
        return 1

    try:
        choices = _parse_mode(args.mode)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    results: list[RunResult] = []
    for choice in choices:
        _print_header(choice)
        result = run_with_choice(args.question, choice, model=args.model)
        _print_result(result)
        results.append(result)
        print()

    if args.mode == "all":
        _print_summary(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
