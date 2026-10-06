# D3 Judge Configuration V1

**Status: FROZEN.**

Judge: OpenAI Responses API, `gpt-5-mini-2025-08-07`, `reasoning_effort = medium`, temperature not sent
(provider-controlled). The machine source is `d3/evaluation/d3_judge_config_v1.json` (`status = "FROZEN"`).
`D3_JUDGE_CONFIG_V1.sha256` records the SHA-256 of this file and of the JSON (the hash is not written
inside either file); `d3/evaluation/run_d3_judge.py` verifies it, and checks that the frozen judge settings
are exactly the ones below, before any judge call. Any change to the judge (model, settings, prompt,
schema, policies) requires a new configuration version.

## 1. Purpose

Fix, before any judgement exists, how the final answers of the official D3 run are scored on the three
answer-quality dimensions of the frozen protocol: Correctness, Faithfulness/Groundedness and Relevance
(0 = Poor, 1 = Partial, 2 = Good). Nothing else is scored here.

## 2. Relationship to D3 Evaluation Protocol

This configuration implements `D3_EVALUATION_PROTOCOL_V1.md` Sections 9–12 and 17 and does not change it
(protocol SHA-256 `1dd9974ee18e000326b58e30902d8bf3810155d23961ea0c62677f464e6a1e59`). Agency (Exact
Capability Match, Tool Accuracy) and retrieval (Hit@3, Recall@3, MRR) were scored separately by the
deterministic scorer; the judge does not re-evaluate capability or tool selection, retrieval, the planner's
`rag_query` or cosine distances.

## 3. Source Run

| Item | Value |
|---|---|
| run_id | `20261006T172749+0100` (status COMPLETED, 35/35) |
| raw_results.jsonl | `ddf6823222266a93142d7576ac7b3af4514f2628b4683094cf5a9827d7f7ccfa` |
| run_manifest.json | `5c82b5ab5443a2b548528a8bd661fae9b7df81aef3a3848149a6f64411c156e7` |
| deterministic_scores_v1.json | `e3dd4a0e147260f8554dc1073acdce9f3bfbcacff55db7d4b8eae35c7bf685e6` |
| D3_DETERMINISTIC_SCORING_REPORT_V1.md | `b0beba33402a25fbaa76bf316fecb16484ad2a0321d996a33d786b1151d0e232` |

The runner checks these values (and the dataset, protocol and `RUN.sha256`) before anything else. The
deterministic scores are validated only to make sure they belong to the same run; their content never
enters the judge prompt.

## 4. Judge Model

Selected by the project owner (explicit decision, 2026-10-06):

| Setting | Value |
|---|---|
| Provider | OpenAI API |
| API | Responses API (official `openai` Python SDK) |
| Model family | GPT-5 mini |
| Exact model | `gpt-5-mini-2025-08-07` |
| Model version / snapshot | `gpt-5-mini-2025-08-07` (dated snapshot; no further digest is claimed) |
| Reasoning effort | `medium` (identical for every answer) |
| Temperature | not sent (`temperature = null`, policy `not_sent_provider_controlled`; Section 5) |
| Max output tokens | `6000` (reasoning tokens + three short scored reasons; see below) |
| Structured output | `text.format = {type: json_schema, name: d3_judge_scores, strict: true}` with the schema of Section 15 |
| store | `false` |
| Tools | none (no web search, file search, MCP, code interpreter, functions or computer use) |
| Background mode / Conversations | not used; every judgement is an independent request |
| SDK automatic retries | `0` (every attempt is a runner attempt, Section 16) |
| Request timeout | 120 s |

Rationale:

- the judge is different from the evaluated `llama3.2:3b` (the runner rejects a judge model equal to the
  planner or generator model recorded in the run manifest) and external to the evaluated system;
- GPT-5 mini is a substantially more capable, general-purpose reasoning model than the 3B-parameter model
  that generated the answers (no benchmark figure is claimed here);
- the dated snapshot `gpt-5-mini-2025-08-07` is used instead of the alias `gpt-5-mini`, which may point to
  a different version in the future; this keeps the academic evaluation reproducible;
- the same model, snapshot and request settings are used for all answers.

The selected snapshot is deliberately frozen for this evaluation; model availability is checked only at
execution time. There is no automatic fallback to any other model (e.g. `gpt-5`, `gpt-4.1`, `gpt-4o`): if
the API rejects the model as unavailable or deprecated, the judge run aborts under the failure policy
(Section 18), and changing the judge requires a new configuration version.

`max_output_tokens` counts the model's internal reasoning tokens as well as the visible JSON. 6000 leaves
ample room for medium-effort reasoning on a long judge input plus three short reasons, while bounding the
output. A response that ends incomplete (e.g. the limit is reached) is not parseable and is handled as a
technical failure (Section 16); it is never truncated into a score.

The API key is read from the environment variable `OPENAI_API_KEY`, loaded with `python-dotenv` from
`.env` at the repository root (an existing environment variable takes precedence) **only** on
`--execute`. `.env` is git-ignored, is not part of any hash and the key is never written to stdout,
stderr, manifests, results, reports or exceptions (authentication failures are recorded only as
"OpenAI authentication failed"; other API errors are redacted). `--validate-only` does not read the key.

## 5. Temperature / Sampling Policy

Decision of the project owner (2026-10-06), option (a):

- For this frozen Responses API judge configuration, `temperature`, `top_p` and `logprobs` are not sent.
  Sampling behaviour is provider-controlled and the explicit reasoning control is `reasoning_effort = medium`.
- The machine configuration stores `temperature = null` with
  `temperature_policy = "not_sent_provider_controlled"`: the parameter is not explicitly configurable or
  sent for this judge configuration, and the provider/model sampling behaviour is used.
- The explicit, frozen control is `reasoning_effort = medium`.
- The same provider, exact model snapshot, reasoning effort, system prompt, user-message template, strict
  JSON schema, `max_output_tokens`, `store = false`, absence of tools and the 2-attempt technical retry
  policy are used for all LLM-judged answers (31 in the source run).
- No claim of deterministic LLM inference is made: even with a fixed configuration, the judge's output
  may vary between repeated calls. This is why each answer receives a single official judgement.

**Compatibility note with the protocol.** `D3_EVALUATION_PROTOCOL_V1.md` (frozen, unchanged) asks for a
fixed temperature for the judge. For this judge, model and provider the sampling policy is fixed as
"temperature = provider-controlled / not configured", with `reasoning_effort = medium` explicitly frozen,
and the same policy is applied to every answer. This is a compatibility decision about the judge's request
settings only: the metrics, the dimensions (Correctness, Faithfulness/Groundedness, Relevance), the 0/1/2
rubric and every other protocol rule are unchanged.

## 6. Dimensions

Correctness, Faithfulness/Groundedness, Relevance, scored independently. No composite, weighted or
averaged-across-dimensions score exists.

## 7. Rubric

Integer scores only: 0 = Poor, 1 = Partial, 2 = Good (protocol Section 10, reproduced in the system prompt
of the JSON configuration).

- **Correctness.** 2: satisfies correctly the relevant requirements; stable facts correct w.r.t. the gold;
  weather/places values correct w.r.t. the raw outputs captured in the run; no important part missing.
  1: mostly correct but omits a relevant part, minor inaccuracy, partial answer to a need, or reasonable but
  incomplete conclusion. 0: substantially wrong, does not answer, contradicts the data, fails an essential
  part, or no useful answer because of an error.
- **Faithfulness / Groundedness.** 2: every relevant factual claim is supported by the evidence actually
  given to the generator. 1: a minor extrapolation or weakly supported claim, core grounded. 0: relevant
  hallucination, values absent from the data, invented relations, a distance not obtained, invented
  weather, contradictions with the evidence, substantially ungrounded, or no useful answer because of an error.
- **Relevance.** 2: answers directly all relevant needs, useful content, no material digressions.
  1: main answer present but irrelevant content, excessive vagueness or an omitted secondary part.
  0: does not answer the main request or mostly irrelevant, or no useful answer because of an error.

## 8. Correctness Evidence Policy

Stable facts are judged against the frozen gold: the Essential Facts of the item and their evidence
excerpts, plus `answer_requirements`. Weather and places values are judged against the raw tool outputs
of the same run. This is intentional: Correctness measures truth relative to the gold, even when the
system's actual retrieval did not contain the fact.

## 9. Faithfulness Evidence Policy

Every claim is judged against what the generator actually received: `generation_evidence.rag_context`,
`generation_evidence.weather_data`, `generation_evidence.places_data` and the raw tool outputs of the run.
For RAG-only plans the run recorded the D2 context reconstructed with the same frozen retriever; that is
the generator evidence. The gold material is not evidence for Faithfulness, and the oracle retrieval is
never used: a correct fact absent from the actual evidence is unsupported, and a faithful reproduction of
wrong tool data is faithful (Correctness handles the error).

## 10. Relevance Policy

Judged against the question: does the answer address all its needs directly, without material
digressions? Verbosity is not rewarded; a concise complete answer is not penalised.

## 11. Dynamic Data Policy

Weather and places facts are judged only against the raw outputs captured on 2026-10-06 in the source
run. No new call is made and nothing is compared with current data. Weather recommendations (umbrella,
running, being outdoors, "bom tempo") have no fixed yes/no gold: the judge checks that the weather data
used are correct and that the recommendation is coherent with them; two different reasonable
recommendations are not penalised against each other (protocol Section 12). Places distances are
straight-line (geodesic).

## 12. No-answer Policy

When the raw `final_answer` is null (or empty), the system ended with an execution error and produced no
useful answer. The judge is **not** called: Correctness = 0, Faithfulness = 0, Relevance = 0,
`evaluation_method = "protocol_deterministic_zero"`, `judge_called = false`, `attempts = 0`, with the
reason "No final answer was produced because the system ended with an execution error; protocol Section 10
assigns 0 to all three dimensions." The IDs are derived from the raw results, never hard-coded; in the
source run they are D3_Q22, D3_Q24, D3_Q34 and D3_Q35 (4), leaving 31 answers for the LLM judge.

## 13. Judge Input

One user message per answer, built by `build_judge_payload` and the frozen `user_message_template`:

- **[A] QUESTION** — the original question.
- **[B] GOLD ANSWER REQUIREMENTS** — Essential Facts and evidence excerpts (RAG items),
  `answer_requirements` (stable facts, weather requirements, places requirements), and the semantic weather
  (location, temporal need) and places (place, origin, destination) requirements.
- **[C] ACTUAL GENERATION EVIDENCE** — `rag_context`, `weather_data`, `places_data` exactly as they reached
  the generator, and the raw Weather/Places tool outputs.
- **[D] FINAL ANSWER** — the full string returned by the agent (including its appended source lines).

## 14. Excluded Inputs

Never shown to the judge: the oracle retrieval; the actual-retrieval records and cosine distances; the
planner output and `rag_query`; expected tools; question ID and category; any deterministic metric (ECM,
Tool Accuracy, Hit@3, Recall@3, MRR) or scoring file; human observations about the system; scores or
answers of other questions; any hint about an expected score. The judge is instructed not to use external
or general knowledge.

## 15. Structured Output Schema

    {"correctness":  {"score": 0 | 1 | 2, "reason": "<short, concrete>"},
     "faithfulness": {"score": 0 | 1 | 2, "reason": "<short, concrete>"},
     "relevance":    {"score": 0 | 1 | 2, "reason": "<short, concrete>"}}

The exact JSON schema of `output_schema` (each dimension: `score` integer enum [0, 1, 2], `reason`
string; all keys required; `additionalProperties: false` everywhere) is sent with Responses API
Structured Outputs in strict mode. Every output is also validated strictly by the runner: exactly these
three keys, each with exactly `score` and `reason`; `score` an integer in {0, 1, 2} (no booleans, floats,
nulls or other values); `reason` a non-empty string of at most 800 characters (2–3 sentences pointing to
the concrete part of the answer/evidence). No overall score, no chain-of-thought; hidden reasoning is
neither requested nor stored. Stored per answer: the parsed scores, the output text, `response.id`,
`response.model`, `status` and `usage` (input, output, total, reasoning and cached tokens when reported).

## 16. Retry Policy

At most 2 attempts per answer. Attempt 2 happens only after a transport/API error, unparseable output or
output outside the schema, with exactly the same system prompt, user message and configuration. A score is
never re-requested because it looks surprising: the first valid judgement is the official one (single
pass; no majority vote or self-consistency).

## 17. Execution Procedure

1. (Done) The configuration is FROZEN and `D3_JUDGE_CONFIG_V1.sha256` holds the SHA-256 of
   `D3_JUDGE_CONFIG_V1.md` and `d3_judge_config_v1.json`.
2. Put the API key in `.env` (`OPENAI_API_KEY=...`) or in the environment.
3. `uv run python d3/evaluation/run_d3_judge.py --validate-only` (must print READY TO JUDGE; no key needed).
4. `uv run python d3/evaluation/run_d3_judge.py --execute --confirm-judge-v1` (once): loads `.env`, checks
   that `OPENAI_API_KEY` is not empty (otherwise the judge run aborts at startup with
   "OPENAI_API_KEY is not configured."), creates the OpenAI client and judges the answers.

The run processes D3_Q01 → D3_Q35 in order and writes to
`d3/evaluation/runs/20261006T172749+0100/judge/<judge_run_id>/`:
`judge_results_v1.jsonl` (35 lines, deterministic zeros included), `judge_manifest.json`,
`D3_LLM_JUDGE_REPORT_V1.md` and `LLM_JUDGE_V1.sha256` (the last two only when COMPLETED). An existing
judge run directory is never overwritten.

## 18. Failure Handling

- Validation failure (any hash, the source run, the deterministic scoring, the configuration): abort before
  any client is created.
- Judge client cannot be created: judge run ABORTED (`abort_stage = startup`).
- Both attempts for one answer fail technically: judge run ABORTED (`abort_stage = judging`); the partial
  `judge_results_v1.jsonl` is preserved, the failed answer is recorded without scores, no score is invented,
  and the run is never completed later under the same `judge_run_id`. A new attempt is a new judge run.

## 19. Reproducibility / Integrity

The judge manifest records the judge_run_id, status, timestamps, the source run and the SHA-256 of its raw
results and manifest, the dataset, protocol, deterministic-scoring and judge-config hashes, provider, exact
model, version/digest when reported (never invented), `temperature = null` with its policy
(`not_sent_provider_controlled`; no effective temperature is invented), reasoning effort, the request
settings, max attempts, expected/completed
counts and technical retries. Each result line keeps the parsed scores, the raw judge response, provider
metadata (tokens, timing) when available and the attempt log. When COMPLETED, `LLM_JUDGE_V1.sha256` stores
the SHA-256 of the results, the manifest and the report; these files are never modified afterwards.
