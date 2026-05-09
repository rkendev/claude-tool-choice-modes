# T004 — Artifact C: Tool Choice Modes Showcase (new repo)

## Goal

Build the third small-projects-portfolio artifact: a CLI that runs the SAME prompt against the SAME tools with DIFFERENT `tool_choice` settings, printing each round-trip's `stop_reason` and tool-call behavior side-by-side. The lesson: when Claude *can* skip a tool versus when it *must* use one — and when the architect picks the specific tool versus letting Claude decide.

This is **a new public repo**, NOT a directory inside any existing artifact's repo. Per the locked plan: "3–4 separate GitHub repos as a SERIES PATTERN, NOT a monorepo."

Repo name: `claude-tool-choice-modes`
Local location on VPS: `/root/projects/AI-Engineering/short_projects_exam_prep/claude-tool-choice-modes/`

## Workflow (same shape as T003)

**Phase A (scaffold):** new repo from `roy-ai-template@v0.5.0`, all 5 known post-scaffold fixes, GitHub repo public, secrets + topics, CI + Smoke green on initial commit, scaffold-disclosure note in README. Single feature branch `feat/t004-tool-choice-modes`.

**Phase B (artifact):** two demo tools, the showcase loop, three modes wired into a CLI, VCR cassettes for each mode, README with side-by-side output, PR-based merge.

## Phase A — Scaffold

Identical to T003 Phase A in structure, just with the new project name. Replicate exactly:

```bash
cd /root/projects/AI-Engineering/short_projects_exam_prep
copier copy --vcs-ref v0.5.0 \
  /root/projects/AI-Engineering/roy-ai-template \
  ./claude-tool-choice-modes \
  --trust --defaults \
  --data project_name=claude-tool-choice-modes \
  --data package_name=claude_tool_choice_modes \
  --data project_description="When Claude must act vs. can decide — a side-by-side showcase of the three tool_choice modes."
```

Then apply the **5 known post-scaffold fixes verbatim** from the canonical block — `feedback_copier_syntax.md` is the source of truth, but inlined here so this prompt stays self-contained:

```bash
cd claude-tool-choice-modes

# Bug #1 — defensive sed (load-bearing per T003 execution; copier _tasks creates "my-ai-project" residue)
grep -rl "my-ai-project" --include="*.toml" --include="*.md" --include="Makefile" --include="*.yaml" --include="*.yml" --include="*.example" . 2>/dev/null \
  | xargs -r sed -i 's/my-ai-project/claude-tool-choice-modes/g'

# Bug #2 — git init + main branch (copier 9.x doesn't auto-init)
git init && git checkout -b main

# Bug #4 — top-level pre-commit exclude for jinja-placeholder skill template
sed -i '1i exclude: ^\\.claude/skills/add-adapter/_adapter_template\\.py$\n' .pre-commit-config.yaml

# Bug #3 — install dev extras (template's [project.optional-dependencies].dev not installed by uv sync default)
uv sync --all-extras

# Bug #5 — smoke.sh executable bit (template ships it 100644)
chmod +x scripts/smoke.sh
git update-index --chmod=+x scripts/smoke.sh

# Move this T-prompt into tasks/ before the first commit so it lands in initial commit
mkdir -p tasks
mv ../C_T004_tool_choice_modes_prompt.md tasks/

git add -A
git commit -m "chore: scaffold from roy-ai-template@v0.5.0 + post-scaffold fixes"
make check
```

If pre-commit auto-fixers modify files on first run, amend:

```bash
git add -A && git commit --amend --no-edit
make check   # second pass — must be all-green
```

GitHub publish + secrets + topics:

```bash
gh repo create rkendev/claude-tool-choice-modes \
  --public \
  --source=. \
  --description "When Claude must act vs. can decide — a side-by-side showcase of the three tool_choice modes." \
  --push

gh secret set ANTHROPIC_API_KEY     # paste the key

# Skip OPENAI_API_KEY — verified during T003 that ci.yml/smoke.yml don't reference it.
# If a future workflow does, set it then.

gh repo edit rkendev/claude-tool-choice-modes \
  --add-topic claude,anthropic,tool-use,tool-choice,json-schema,cca-f
```

README scaffold-disclosure block (Phase A version — replace inherited template lead):

```markdown
# claude-tool-choice-modes

[![CI](https://github.com/rkendev/claude-tool-choice-modes/actions/workflows/ci.yml/badge.svg)](https://github.com/rkendev/claude-tool-choice-modes/actions/workflows/ci.yml)

When Claude *must* act versus when it *can* decide — a side-by-side
showcase of the three `tool_choice` modes (`auto`, `any`, and
`{"type": "tool", "name": ...}`) running the same prompt against the
same tools and printing the resulting `stop_reason` for each.

Built as Artifact C of a Claude Certified Architect Foundations
small-projects portfolio. Companion to
[claude-mcp-server-minimal](https://github.com/rkendev/claude-mcp-server-minimal)
(Artifact A) and
[claude-tools-roundtrip-playground](https://github.com/rkendev/claude-tools-roundtrip-playground)
(Artifact B).

> Repo bootstrapped from my own `roy-ai-template@v0.5.0` starter; the
> tool_choice showcase is original.
```

Group inherited template content under `## Inherited template scaffolding (background)` immediately after the artifact section. Same pattern as Artifacts A and B.

Phase A acceptance gates:

- `make check` green — record the test count baseline (expected ~219, same template).
- Public repo created; topics visible via `gh repo view`.
- Both `CI` and `Smoke` green on the initial commit (Smoke runs on push-to-main only by design).
- README badge resolves green.

## Phase B — Artifact

### B.1 The two demo tools

Two tools with **deliberately differentiated descriptions** so `tool_choice="auto"` has a meaningful routing decision to make. Both return mocked data — no real HTTP, no external services.

```python
# src/claude_tool_choice_modes/tools.py

CITY_DATA: dict[str, dict[str, int | str]] = {
    "Tokyo": {"population": 14094034, "country": "Japan"},
    "New York": {"population": 8336817, "country": "United States"},
    "Amsterdam": {"population": 921402, "country": "Netherlands"},
    "São Paulo": {"population": 12325232, "country": "Brazil"},
}


def get_city_population(city: str) -> int:
    """Return the most recent census population estimate for a major city."""
    if city not in CITY_DATA:
        raise ValueError(f"unknown city: {city}")
    return cast(int, CITY_DATA[city]["population"])


def get_city_country(city: str) -> str:
    """Return the country a major city is located in."""
    if city not in CITY_DATA:
        raise ValueError(f"unknown city: {city}")
    return cast(str, CITY_DATA[city]["country"])


POPULATION_TOOL: dict[str, Any] = {
    "name": "get_city_population",
    "description": (
        "Return the most recent census population estimate for a major "
        "city as an integer. Use this when the user asks how many people "
        "live in a city or how big a city is. Do NOT use for non-population "
        "facts such as country, area, or timezone."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "The city name, e.g. 'Tokyo'."},
        },
        "required": ["city"],
        "additionalProperties": False,
    },
}

COUNTRY_TOOL: dict[str, Any] = {
    "name": "get_city_country",
    "description": (
        "Return the country a major city is located in as a string. Use "
        "this when the user asks which country a city is in. Do NOT use "
        "for population, area, or other non-country facts."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "The city name, e.g. 'Tokyo'."},
        },
        "required": ["city"],
        "additionalProperties": False,
    },
}

ALL_TOOLS = [POPULATION_TOOL, COUNTRY_TOOL]
```

The "Do NOT use for X" anti-instructions in each description are the **CCA-F D2 disambiguation pattern** — the #1 fix per the study notes. Worth highlighting in the Medium post when Wk7 ships it.

### B.2 The showcase loop

`src/claude_tool_choice_modes/showcase.py` exposes a single function that runs one round-trip with a configurable `tool_choice` and returns a structured result:

```python
@dataclass(frozen=True)
class RunResult:
    """Captures one round-trip's protocol-visible behavior."""
    mode_label: str            # "auto", "any", or 'tool:get_city_population'
    stop_reasons: list[str]    # ordered, one per iteration
    tool_calls: list[tuple[str, dict[str, Any]]]  # (name, input) per tool_use
    final_text: str            # last end_turn's joined text content (may be empty)


def run_with_choice(
    question: str,
    tool_choice: dict[str, Any],   # e.g. {"type": "auto"}, {"type": "any"}, {"type": "tool", "name": "..."}
    *,
    model: str = MODEL_DEFAULT,
    client: Anthropic | None = None,
) -> RunResult: ...
```

The loop is the same shape as Artifact B's `run_roundtrip`, with two differences:

1. The `tool_choice` parameter is passed to `client.messages.create(...)`.
2. The function returns a structured `RunResult` instead of just the text — the showcase needs to compare results across modes.

Branch behavior inside the loop:

- `stop_reason == "tool_use"`: dispatch to the right local function (`get_city_population` or `get_city_country` based on `tool_block.name`), append `tool_result` to messages, continue.
- `stop_reason == "end_turn"`: capture text, set on result, break.
- Anything else: raise `RoundTripIterationError` (same exception name as Artifact B for narrative consistency).
- Iteration cap: 5 (same as Artifact B).

Use the **same SDK-typing ignore convention** from Artifact B (`playground.py:53–54`): `# type: ignore[list-item]` on `tools=`, `# type: ignore[arg-type]` on `messages=`. Don't re-derive it.

Use the **same `[b.model_dump() for b in resp.content]` pattern** from Artifact B for the `messages.append({"role": "assistant", ...})` step. Don't waste a CI iteration rediscovering it.

### B.3 The CLI

`__main__.py` accepts a question and runs ALL THREE modes back-to-back:

```bash
python -m claude_tool_choice_modes "What's the population of Tokyo?"
```

Output structure (each mode prints a header + the round-trip steps + a result summary):

```
============================================================
[mode: auto]   tool_choice = {"type": "auto"}
============================================================
... round-trip step prints ...
[result] stop_reasons: ["end_turn"]
         tool_calls: []
         final_text: "Tokyo's population is approximately 14 million..."

============================================================
[mode: any]    tool_choice = {"type": "any"}
============================================================
... round-trip step prints ...
[result] stop_reasons: ["tool_use", "end_turn"]
         tool_calls: [("get_city_population", {"city": "Tokyo"})]
         final_text: "Based on the latest data, Tokyo has 14,094,034 residents..."

============================================================
[mode: tool:get_city_country]   tool_choice = {"type": "tool", "name": "get_city_country"}
============================================================
... round-trip step prints — NOTE Claude is forced to call the irrelevant tool ...
[result] stop_reasons: ["tool_use", "end_turn"]
         tool_calls: [("get_city_country", {"city": "Tokyo"})]
         final_text: "Tokyo is in Japan, but I should note the question was about population..."

============================================================
[summary] same prompt, same tools, three different stop_reason patterns:
  auto                       → ["end_turn"]                       (Claude skipped the tools)
  any                        → ["tool_use", "end_turn"]           (Claude picked get_city_population)
  tool:get_city_country      → ["tool_use", "end_turn"]           (forced to use the wrong tool)
============================================================
```

The third mode (`tool:get_city_country`) is the educational kicker — it shows how an architect can override Claude's natural choice, and why the named-tool mode is mostly useful for forcing a specific lookup pattern (or for testing tool descriptions).

CLI flags:
- `--mode` (default: `all`) — one of `auto`, `any`, `tool:NAME`, or `all`. Useful for reproducing a single mode without re-running everything.
- `--question` (positional, required) — the natural-language question.

`ANTHROPIC_API_KEY` validation at start: same pattern as Artifact B's `__main__.py` — exit 1 with stderr message if missing.

### B.4 Tests

Add `tests/unit/test_showcase.py`:

1. **`test_tool_schemas_are_well_formed`** — assert both `POPULATION_TOOL` and `COUNTRY_TOOL` have `type:object`, snake_case `input_schema`, `additionalProperties: false`, `required: ["city"]`.

2. **`test_get_city_population_known_value`** + **`test_get_city_country_known_value`** — pure-Python unit tests for the two local functions. Use Tokyo and Amsterdam as known values.

3. **`test_get_city_unknown_raises`** — both tools raise `ValueError` on unknown city.

4. **`test_choice_auto_round_trip`** (`@pytest.mark.vcr`) — record once with a real key. Assert the run completes; assert the recorded result has at least one `end_turn`. **Do NOT assert tool_calls is empty** — `auto` mode is non-deterministic; the test pins the recorded behavior, whatever it was.

5. **`test_choice_any_forces_tool_use`** (`@pytest.mark.vcr`) — record once. Assert `stop_reasons[0] == "tool_use"` and the final stop_reason is `"end_turn"`. This IS deterministic — `any` mode forces a tool call.

6. **`test_choice_specific_tool_forces_named`** (`@pytest.mark.vcr`) — record once with `tool_choice={"type": "tool", "name": "get_city_country"}`. Assert exactly that tool was called: `tool_calls[0][0] == "get_city_country"`. Even when the question is about population, the named-tool mode forces the country tool.

7. **`test_iteration_cap_raises`** (synthetic, no VCR) — same pattern as Artifact B: `MagicMock` client returning `stop_reason="tool_use"` indefinitely; assert `RoundTripIterationError` after 5 iterations.

8. **`test_unexpected_stop_reason_raises`** (synthetic) — same as Artifact B; covers the unhandled-stop_reason branch for coverage.

Net delta: 8 new tests. Expected total: scaffold baseline (~219) + 8 = ~227.

**VCR cassettes** land at `tests/unit/cassettes/test_showcase/` — three cassettes, one per VCR-marked test. Each must redact the `authorization` and `x-api-key` headers.

**Important: move the `vcr_config` fixture to `tests/conftest.py`** rather than embedding it in `test_showcase.py`. T003 left it in the test file because there was only one test file using VCR; T004 has multiple cassette tests and will benefit from project-scoped config. Same fixture content as T003's (`tests/unit/test_playground.py:118–126`).

**The dummy-API-key gotcha** (per `feedback_anthropic_sdk_vcr_replay.md` from Cowork memory, also encountered in T003): each VCR test must instantiate the client with an explicit dummy key OR set `ANTHROPIC_API_KEY` to a non-empty value via `monkeypatch.setenv`. Otherwise the SDK constructor raises before VCR can intercept. Pattern:

```python
@pytest.mark.vcr
def test_choice_any_forces_tool_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "cassette-replay-dummy-key")
    result = run_with_choice(
        "What's the population of Tokyo?",
        tool_choice={"type": "any"},
    )
    ...
```

### B.5 README artifact section

Replace the inherited template's lead with the H1+badge+lead block from Phase A, then add a `## Tool choice modes` H2 right under it (above `## Inherited template scaffolding`):

```markdown
## Tool choice modes

```bash
ANTHROPIC_API_KEY=sk-ant-... \
  uv run python -m claude_tool_choice_modes \
    "What's the population of Tokyo?"
```

Three round-trips against the same two tools. The summary at the end shows the difference:

```
[summary] same prompt, same tools, three different stop_reason patterns:
  auto                  → ["end_turn"]                  (Claude skipped the tools)
  any                   → ["tool_use", "end_turn"]      (Claude picked get_city_population)
  tool:get_city_country → ["tool_use", "end_turn"]      (forced to use the wrong tool)
```

Why this matters:

- **`auto`** lets Claude decide. Quality of the tool *description* is what routes Claude correctly when there are multiple tools — see the "Do NOT use for ..." anti-instructions in `tools.py`.
- **`any`** forces *some* tool call but lets Claude pick which. Used when the architect knows a tool is needed but doesn't want to constrain the model's choice across an ambiguous prompt.
- **`{"type": "tool", "name": "X"}`** forces a *specific* tool. The third demo intentionally forces the wrong tool (`get_city_country` for a population question) to show how the named mode overrides Claude's natural routing.

`make check` runs the showcase tests offline against committed VCR cassettes — no API key required for CI.
```

Then keep the existing inherited-template content under `## Inherited template scaffolding (background)`.

### B.6 PR body

Write `tasks/pr_body.md`:

```markdown
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

- `make check` green: <N> tests passing on baseline + 8.
- VCR cassettes for all three modes redacted (`grep -i sk-ant tests/unit/cassettes/**/*.yaml` returns empty).
- Manual end-to-end: `uv run python -m claude_tool_choice_modes "What's the population of Tokyo?"` produces the three-mode summary block.
- CI green on this PR.
- (Post-merge): Smoke green on main.

## Implementation notes (carried forward from T003 audit)

- `vcr_config` fixture moved to `tests/conftest.py` (T003 had it in the test file; T004 has multiple cassette tests so project-scoped is cleaner).
- SDK-typing ignore pattern matches `playground.py:53–54` from Artifact B (`# type: ignore[list-item]` for `tools=`, `# type: ignore[arg-type]` for `messages=`).
- `messages.append({"role": "assistant", "content": [b.model_dump() for b in resp.content]})` applied up-front rather than waiting for a CI iteration to rediscover it.
- Each VCR test sets `ANTHROPIC_API_KEY` via `monkeypatch.setenv` (or instantiates the client with `Anthropic(api_key="dummy")`) to satisfy the SDK's constructor-time auth check.

## Out of scope

- A fourth mode for `tool_choice={"type": "none"}` — out of scope for this artifact's narrative; the three demonstrated modes cover the CCA-F D2 quiz pattern.
- Real geo-coding API. The two tools return mocked dict lookups; the artifact is about the *protocol mechanics*, not data quality.
- Stripping inherited template scaffolding. Wk5+ polish decision per the locked plan.
- Version bump / CHANGELOG.

## Closes

T004 of CCA-F small-projects plan v1; opens Artifact C for Wk7 polish (Medium #2 hook: "Tool Choice Modes: When Claude Must Act vs. Can Decide").
```

## Anti-patterns to avoid

- Do NOT add a fourth mode (`{"type": "none"}` or any custom). Three is the lesson.
- Do NOT use real geo-coding APIs. Mocked dict lookups are deliberate.
- Do NOT use `anthropic.tools.run` or any high-level abstraction. Raw `client.messages.create(...)` loop with explicit `stop_reason` checks. Visibility is the feature.
- Do NOT touch `src/claude_tool_choice_modes/{domain,application,infrastructure}/` — inherited scaffolding, Wk5+ polish decision.
- Do NOT bump version, do NOT touch CHANGELOG. Wk7 ships v0.1.0 of this repo (after Medium #2 publishes per the locked plan).
- Do NOT collapse the three modes into one parametrized test. Three distinct test functions read better in CI output and produce three distinct cassettes — easier to debug if one mode breaks.

## Protocols (inlined)

- **API verification:** Verify the `tool_choice` parameter shape against the installed Anthropic SDK before writing code. SDK 0.96.0 (inherited from `roy-ai-template@v0.5.0`) accepts `{"type": "auto"}`, `{"type": "any"}`, `{"type": "tool", "name": "..."}`. Confirm with `uv run python -c "from anthropic.types import message_create_params; help(message_create_params)"` or `cat .venv/lib/python*/site-packages/anthropic/types/tool_choice*.py`.
- **Test-count reporting:** Read totals from the `make check` pytest summary line. Never `grep -c "def test_"`.
- **Pre-commit:** Always `uv run pre-commit run --all-files` or `make check`. Bare `pre-commit` errors.
- **Branch protocol:** New work on `feat/t004-tool-choice-modes`. PR-based; squash-merge on acceptance.
- **Task close:** local `make check` green + CI green on PR + acceptance-specific verification (manual run with real key) → squash-merge → Smoke green on main post-merge.
- **Smoke note:** `smoke.yml` is configured `on: push: branches: [main]` only by design. Do NOT block on Smoke-on-PR.
- **Carry-forwards from T003 audit:** `vcr_config` in `tests/conftest.py` (project-scoped); SDK-typing ignores per `playground.py:53–54` convention; `model_dump()` for content roundtrip; dummy API key for VCR replay.

## Plan mode requirements

Begin in plan mode. Walk through:

1. Pre-flight verification — re-confirm 5-bug list status, Anthropic SDK 0.96.0, `tool_choice` parameter shape (snake_case `tool_choice` field, dict shape with `"type"` key).
2. The two tools' descriptions — show the proposed text and confirm the "Do NOT use for X" anti-instruction pattern is in both.
3. The `RunResult` dataclass — confirm field shape for downstream serialization in tests.
4. The CLI mode parsing — how `--mode auto`, `--mode any`, `--mode tool:get_city_country`, and `--mode all` are implemented.
5. Test plan with cassette layout — three VCR cassettes with file paths.
6. Expected new test count + total.
7. PR body draft (in `tasks/pr_body.md`).
8. The full file list (created/modified) for both phases.

Wait for explicit approval before any `copier copy` or code changes.

## Out of scope (later in Wk7 / Wk8)

- Wk7 (per locked plan): Artifact C README polish + Medium #2 publish ("Tool Choice Modes: When Claude Must Act vs. Can Decide") + tag `v0.1.0` of this repo.
- Wk8: T005 — Artifact D (MCP Resources Audit, new repo or curated GitHub gist).
