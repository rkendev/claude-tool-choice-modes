## What

T004 — Artifact C (Tool Choice Modes Showcase). New CLI demonstrating
the three `tool_choice` modes (`auto`, `any`, specific-tool) by running
the same prompt against the same two tools and comparing each mode's
`stop_reason` and tool-call pattern. Closes Wk6–Wk7 of the CCA-F
small-projects plan.

## Why

CCA-F D2 has two Sev-≥4 gaps this artifact closes:

- **`tool_choice` modes** — quiz miss pattern Q12/Q10. The showcase
  makes the difference between "Claude can decide" and "Claude must
  act" visible at the protocol level.
- **Tool descriptions as routing** — the #1 D2 fix per the study
  notes. Both tools include "Do NOT use for X" anti-instructions
  to demonstrate description-driven routing in `auto` mode.

## How verified

- `make check` green: **238 tests** passing on baseline 219 + 9 showcase
  + 10 CLI = 19 new. The CLI tests were added after CI rejected the
  first push for coverage on `__main__.py` (CI enforces
  `--cov-fail-under=95`; project total is now 99.68%).
- VCR cassettes for all three modes redacted (`grep -i sk-ant tests/unit/cassettes/**/*.yaml` returns empty).
- Manual end-to-end: `uv run python -m claude_tool_choice_modes "What's the population of Tokyo?"` produces the three-mode summary block.
- CI green on this PR.
- (Post-merge): Smoke green on main.

## Implementation notes (carried forward from T003 audit)

- `vcr_config` fixture moved to `tests/conftest.py` (T003 had it in the test file; T004 has multiple cassette tests so project-scoped is cleaner).
- SDK-typing convention: T003's `playground.py:53–54` used per-arg
  ignores (`# type: ignore[list-item]` for `tools=`, `# type: ignore[arg-type]` for `messages=`). With `tool_choice=` added the overload
  resolution falls earlier and per-arg ignores became unused, so the
  showcase uses a single `# type: ignore[call-overload]` on the call
  site itself. Same intent, mypy-correct shape for the three-arg form.
- `messages.append({"role": "assistant", "content": [b.model_dump() for b in resp.content]})` applied up-front rather than waiting for a CI iteration to rediscover it.
- Each VCR test sets `ANTHROPIC_API_KEY` via `monkeypatch.setenv` so the
  SDK constructor-time auth check passes during cassette replay.
- **Loop fix discovered during cassette recording:** when `tool_choice`
  is `any` or `tool:NAME`, the protocol re-forces a tool_use on every
  turn — so the loop never reaches `end_turn` and hits the iteration
  cap. Standard pattern: pass the user-supplied `tool_choice` only on
  iteration 0, then switch to `{"type": "auto"}` so Claude can
  synthesize the final answer. Documented inline in `showcase.py`.
- **Parallel tool use fix:** Claude can return multiple `tool_use`
  blocks in a single response; the loop iterates over all of them and
  emits one `tool_result` per block in the follow-up user turn. The
  initial single-block implementation hit
  `tool_use ids were found without tool_result blocks` 400s during
  cassette recording.

## Out of scope

- A fourth mode for `tool_choice={"type": "none"}` — out of scope for this artifact's narrative; the three demonstrated modes cover the CCA-F D2 quiz pattern.
- Real geo-coding API. The two tools return mocked dict lookups; the artifact is about the *protocol mechanics*, not data quality.
- Stripping inherited template scaffolding. Wk5+ polish decision per the locked plan.
- Version bump / CHANGELOG.

## Closes

T004 of CCA-F small-projects plan v1; opens Artifact C for Wk7 polish (Medium #2 hook: "Tool Choice Modes: When Claude Must Act vs. Can Decide").
