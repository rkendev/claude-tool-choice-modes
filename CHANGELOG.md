# Changelog

> Scaffolded from [`roy-ai-template@v0.5.0`](https://github.com/rkendev/roy-ai-template/releases/tag/v0.5.0).
> The template's inherited CHANGELOG history (v0.1.0 → v0.5.0) is preserved
> in git history at the scaffold commit; the entries below cover only
> this artifact's own releases.

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
`[Unreleased]` collects changes landing on `main` ahead of the next tagged
release; each tagged version carries its release date and a stable anchor.

## [Unreleased]

## [0.1.0] — 2026-05-12

First stable release of `claude-tool-choice-modes`: a side-by-side
showcase of Claude's three `tool_choice` modes (`auto`, `any`, specific-tool)
running the same prompt against the same two tools and printing each
mode's `stop_reason` and tool-call pattern.

### Added

- **T004 — Tool choice modes showcase** (PR #1, merged squash commit).
  Scaffolded from `roy-ai-template@v0.5.0`. Ships:
  - `src/claude_tool_choice_modes/showcase.py` — `run_with_choice(question, tool_choice, ...)` orchestrates the round-trip loop with the relax-to-auto pattern applied after iteration 0 so `any` and specific-tool modes can reach `end_turn`.
  - `src/claude_tool_choice_modes/tools.py` — `POPULATION_TOOL` and `COUNTRY_TOOL` with deliberately-differentiated descriptions including "Do NOT use for X" anti-instructions.
  - `src/claude_tool_choice_modes/__main__.py` — `python -m` entrypoint with `--mode {auto,any,tool:<name>,all}` dispatch.
  - `tests/unit/test_showcase.py` — 9 tests covering schema, tool functions, three VCR-recorded cassette tests (one per mode), iteration cap, and unexpected stop_reason.
  - `tests/unit/test_cli.py` — 10 CLI plumbing tests covering argparse, env-var validation, and mode dispatch.
  - Project-scoped `tests/conftest.py` with VCR redaction config.
  - 3 VCR cassettes under `tests/unit/cassettes/test_showcase/` with redacted `authorization` and `x-api-key` headers.

- **T004 chore follow-up** (PR #2, merged squash commit). README "Why this matters" section softened the auto-mode example to reflect the recorded cassette behavior (Claude actually calls a tool in this run); test_choice_specific_tool_forces_named hardened against parallel-tool-use order fragility.

Total: **238 tests passing, 99.68% coverage**.

### Inherited from `roy-ai-template@v0.5.0` (preserved unchanged)

The full hexagonal scaffold (`src/.../{domain,application,infrastructure}/`
with three LLM adapters + `FallbackModel` orchestrator, 32-case contract
suite, `.claude/` rules + skills + commands, `make check` gate, CI +
smoke workflows, Docker compose) ships intact from the template. Wk3
polish — pruning the unused adapter stack down to just the Anthropic
path this showcase uses — is deferred pending a follow-up task.

[Unreleased]: https://github.com/rkendev/claude-tool-choice-modes/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/rkendev/claude-tool-choice-modes/releases/tag/v0.1.0
