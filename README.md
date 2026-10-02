# Pit Wall

A Formula 1 race engineer agent built with **Google ADK for Python**. It answers questions about Grand Prix results, championship standings and race pace by calling typed, async function tools over the public [Jolpica F1 API](https://github.com/jolpica/jolpica-f1), the Ergast successor.

```
[user]: Quem foi mais rápido no stint final em Interlagos 2024, Verstappen ou Norris?
[pit_wall]: Verstappen foi o mais rápido no stint final.
- Max Verstappen: mediana de volta limpa de 1:22.271 (melhor volta 1:20.472, volta 67), 36 voltas limpas.
- Lando Norris: mediana de volta limpa de 1:23.361 (melhor volta 1:21.517, volta 67), 36 voltas limpas.
```

Module 1 of a Google ADK study track. Module 0: [adk-00-hello-trench](https://github.com/carvalhocaio/adk-00-hello-trench).

---

## What this module isolates

**`LlmAgent` with function tools.** One agent and three tools, with no subagents and no persistent state. The point is to get the tool contract right because the reader of that contract is a model:

- **The docstring says when to use the tool; `Annotated` describes each argument.** ADK puts the whole docstring in the tool description, but it does not parse an `Args:` section into per-parameter descriptions. Argument descriptions only reach the schema through `Annotated[..., Field(description=...)]`.
- **The docstring also documents the output.** On the Gemini API backend, ADK drops `response_json_schema` from the declaration, which is only sent to Vertex AI. Whatever the model must know about a result, such as an omitted pace or a rank-1 fastest lap, lives in the docstring.
- **Typed results.** Every tool returns a frozen Pydantic model, never a bare `dict`.
- **Tools without I/O of their own.** `PitWallTools` receives a `RaceDataSource` protocol and is tested against an in-memory fake, with no network, no model and no ADK.
- **Tool performance means `async`.** ADK runs the tools a model requests in one turn in parallel, but only async tools benefit. Inside `compare_lap_times`, drivers are fetched concurrently with `asyncio.TaskGroup`, and one shared `aiolimiter` token bucket keeps the burst inside Jolpica's limits.

---

## Tools

| Tool                   | Purpose                                                                                   | Race lookup                            |
|------------------------|-------------------------------------------------------------------------------------------|----------------------------------------|
| `get_race_results`     | Classification with position, driver id, team, grid, laps, status, points and fastest lap | `season` + `round` **or** `circuit_id` |
| `get_driver_standings` | Drivers' championship, latest or after a given round                                      | `season` + optional `after_round`      |
| `compare_lap_times`    | Stint pace for 1–4 drivers: median, best and mean clean lap                               | `season` + `round` **or** `circuit_id` |

`compare_lap_times` splits each driver's laps into stints at pit stop laps and drops in-laps and out-laps before measuring pace. The **median** clean lap decides the fastest driver, because Jolpica does not flag safety car laps and a single neutralized lap would skew the mean.

---

## Architecture

```
src/adk_01_pit_wall/
  agent.py        root_agent: model, prompts, tools, callbacks
  tools.py        PitWallTools: async tools over a RaceDataSource protocol
  models.py       frozen Pydantic outputs, durations as millis + m:ss.SSS
  budget.py       before_model_callback: LLM call budget in temp: state
  tool_errors.py  on_tool_error_callback: recoverable errors back to the model
  settings.py     pydantic-settings, including the budget/ADK limit check
  prompts.py      persona description and instruction
  f1/             domain: stints, pace, race types (standard library only)
  jolpica/        httpx.AsyncClient client: pagination, rate limit, Pydantic DTOs
evals/            two native ADK eval sets and their configs
```

Dependencies point inward: `tools → f1` and `jolpica → f1`. Only `agent.py`, `budget.py` and `tool_errors.py` import ADK.

---

## Design decisions

- **Resolve a race by `round` or `circuit_id`, with no lookup tool.** Every tool accepts either field and validates that exactly one is present. The JSON Schema cannot express that rule, so it lives in the tool, and the error message is written for the model to correct itself on the next call.
- **Fetch laps per driver.** `/drivers/{id}/laps` returns about 70 rows per driver instead of more than 1,100 for the whole race. Pagination follows the `limit` the API *returns*, not the one requested, so a server-side page cap cannot silently truncate a race.
- **Treat model-provided path segments as untrusted.** Driver and circuit ids go through `urllib.parse.quote(..., safe="")`, so `norris/../../results` cannot reach another route.
- **Tool errors are handled by a callback, not inside the tools.** In ADK Python, an exception raised by a tool **aborts the run** unless an `on_tool_error_callback` handles it. `report_tool_error` turns the expected failures into `{"error": ...}` for the model and lets any other exception propagate. The expected failures are invalid arguments, domain errors, Jolpica errors and `httpx` errors. Tools never catch `Exception`. A runner-level test with a scripted model proves both paths.
- **`TaskGroup` failures are unwrapped.** A failing driver fetches surfaces as its own exception, not as an `ExceptionGroup` the error callback would not recognize.
- **Two LLM call limits, validated together.** `RunConfig.max_llm_calls` (set with `ADK_MAX_LLM_CALLS`) raises `LlmCallsLimitExceededError`, which the user would see as a raw error. A `before_model_callback` therefore counts calls in `temp:llm_calls` and answers in the model's place at `PIT_WALL_MAX_LLM_CALLS`, while the ADK limit stays one notch above as a hard stop. `temp:` is exactly the right scope for this counter: it lives in the session object for the whole invocation and is stripped before persistence. A scripted model that never stops calling tools proves that the budget stops the loop and resets on the next invocation. `Settings` refuses a budget that is not below the ADK limit.
- **Durations round half up.** An even stint has a median halfway between two laps, such as 1:22.2705. Python's `round()` uses banker's rounding and would print `.270`, so durations are rounded with integer microsecond arithmetic.

---

## Getting started

Requirements: Python 3.12+, [uv](https://github.com/astral-sh/uv), and a [Google AI Studio API key](https://aistudio.google.com/) or a Google Cloud project with Vertex AI enabled.

```fish
cp .env.example .env
make sync
make ci
make run
```

| Variable                      | Description                                                    | Default                       |
|-------------------------------|----------------------------------------------------------------|-------------------------------|
| `GOOGLE_API_KEY`              | Gemini API key (required when `GOOGLE_GENAI_USE_ENTERPRISE=0`) | –                             |
| `GOOGLE_GENAI_USE_ENTERPRISE` | `1` for Vertex AI, `0` for AI Studio                           | `0`                           |
| `GOOGLE_CLOUD_PROJECT`        | GCP project (required for Vertex AI)                           | –                             |
| `PIT_WALL_MODEL`              | Agent model                                                    | `gemini-flash-latest`         |
| `PIT_WALL_MAX_LLM_CALLS`      | Model calls per invocation before the budget answers           | `6`                           |
| `ADK_MAX_LLM_CALLS`           | ADK hard stop; must be above the budget                        | `500` (`8` in `.env.example`) |

| Target      | What it does                                                    |
|-------------|-----------------------------------------------------------------|
| `make run`  | Terminal chat                                                   |
| `make web`  | ADK dev UI                                                      |
| `make api`  | ADK API server                                                  |
| `make test` | Unit and runner-level tests, with no network and no credentials |
| `make eval` | Both eval sets against Gemini and Jolpica (costs tokens)        |
| `make ci`   | Lint, format check, dependency audit and tests                  |

---

## Evaluation

Two eval sets, because ADK applies criteria to a whole set, not to individual cases. With `IN_ORDER`, an empty expected trajectory passes any trajectory, so "call no tool" needs `EXACT` in a separate set.

| Set                   | Cases                                                      | Criteria                                                                              |
|-----------------------|------------------------------------------------------------|---------------------------------------------------------------------------------------|
| `pit_wall`            | `race_winner`, `standings_after_round`, `final_stint_pace` | trajectory `IN_ORDER` + `ignore_args`, `final_response_match_v2`, `hallucinations_v1` |
| `pit_wall_guardrails` | `missing_season`, `off_topic`                              | trajectory `EXACT` (no tools), `final_response_match_v2`                              |

`hallucinations_v1` splits the answer into sentences and checks each one against the tool responses and declarations. The first run failed `race_winner` at 0.67. The agent wrote "26 points for the win with the fastest lap", but `get_race_results` returned 26 points and dropped the `FastestLap` block that explains the extra point, so the model filled the gap from memory. The fix went into the **tool**, not the prompt: the result now carries each driver's fastest lap, and the docstring states the 2019–2024 bonus point rule. The same case then scored 1.0, and all five cases pass.

---

## Known limitations

- **"Pit stop" includes red flags.** Ergast records red flag stoppages as pit stops. At Interlagos 2024, lap 32 is a 23-minute "stop". The stint split stays correct there, because teams changed tires under the red flag, but not every stop is a green-flag stop.
- **No safety car detection.** The median limits the damage, but a stint run mostly behind the safety car will still read slow.
- **Only the burst limit is enforced.** The limiter covers requests per second, not Jolpica's hourly quota. A `429` reaches the model as a `RateLimitedError` tool error, with no retry.
- **The HTTP client lives as long as the process.** `root_agent` creates an `httpx.AsyncClient` at import time and never closes it, which fits `adk web` and `adk run` but not a long-running service.
- **Eval-only audit exceptions.** `make audit` ignores `PYSEC-2026-3740` (nltk) and `PYSEC-2026-4066` (a LiteLLM proxy SSRF). Both are pulled only by the `eval` dependency group, and `google-cloud-aiplatform[evaluation]` pins `litellm<1.86` on Python versions below 3.14.

---

## What I would do differently at scale

- **Cache historical data.** Finished races never change. A read-through cache behind `RaceDataSource` would remove most network calls and the rate limit pressure, without touching the tools.
- **Retry with backoff at the client edge** for `429` and `5xx`, with retries visible in traces (modules 4 and 10).
- **Give the HTTP client a lifecycle.** Open and close it with the application, not at import time.
- **Move the budget and the error mapping into plugins,** so they apply to every agent in an app without changing any of them (module 8).
- **Run the eval sets in CI,** with repeated runs to separate judge variance from agent regressions (module 9).
