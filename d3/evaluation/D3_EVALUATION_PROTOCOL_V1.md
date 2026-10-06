# D3 Evaluation Protocol V1

Status: frozen before the first official run. Its SHA-256 is recorded in
`d3/evaluation/D3_EVALUATION_PROTOCOL_V1.sha256` (not inside this file). Any change to this
protocol after the first official run requires a new protocol version and a new run.

## 1. Purpose

D3-O1 asks for the integration of the D2 RAG agent with domain-coherent MCP servers and a detailed
evaluation using established RAG evaluation practice, optionally LLM-as-Judge. This protocol fixes,
before any result exists:

- which system is evaluated and which is not;
- the frozen dataset;
- the only official metrics and their exact formulas;
- how one official run is executed, traced and stored;
- how failures are handled;
- the LLM-as-Judge dimensions and rubric (the judge model itself is locked later, separately).

Data collection (the runner) and scoring (a later, separate scorer and judge) are distinct phases.

## 2. Evaluation Scope

The system under test is the **Coimbra Expert Agent** (`d3/coimbra_expert/expert_agent.py`):

    question -> Planner (llama3.2:3b, JSON plan) -> RAG and/or Weather MCP and/or Places MCP -> final answer

The outer classifier of the integrated chatbot (`integration/`: ELIZA_RUDE vs Coimbra Expert) is **not**
part of the D3 primary metrics. All 35 questions are Coimbra-tourism questions by construction, and
D3-O1 evaluates the agentic integration of RAG with MCP servers; routing errors of the D1/D2 classifier
would contaminate the agency metrics. The runner therefore calls the Coimbra Expert Agent directly and
does not use `integration/integrated_agent.py`.

## 3. Frozen Evaluation Dataset

| File | SHA-256 |
|---|---|
| `d3/evaluation/d3_evaluation_set_v1.json` (machine source of truth) | `3cef162c592e3e18c18103a970b926f949dc9e1115f971bfea3c5595674e0528` |
| `d3/evaluation/D3_EVALUATION_SET_V1.md` (human view) | `d15356000ee620fe6341396d7699653638a34685411f8ab0df37f5e7710f1f01` |
| `d3/evaluation/D3_EVALUATION_SET_AUDIT_V1.md` (construction audit) | `7171c366cd15c8e0b7bc13c5baa20c31ab94b28d062a84d9486cfc3cf805afaa` |

Freeze manifest: `d3/evaluation/D3_EVALUATION_SET_V1.sha256`. The four files are read-only.

- 35 questions, D3_Q01–D3_Q35, PT-PT.
- 7 capability combinations × 5 (RAG, Weather, Places, RAG+Weather, RAG+Places, Weather+Places, RAG+Weather+Places).
- RAG required in 20, Weather in 20, Places in 20.
- Weather tools: 10 `get_current_weather`, 10 `get_weather_forecast`. Places tools: 10 `search_place`, 10 `get_distance_between_places`.
- 58 Essential Facts, all with direct evidence; 35 gold chunks over 18 documents; at most 3 gold chunks per question.
- RAG source of truth: `d2_rag/data/chunks/chunks.jsonl`, FROZEN_V2 store `d2_rag/data/chroma_frozen_v2`
  (collection `coimbra_rag_frozen_v2`, Qwen/Qwen3-Embedding-0.6B, top_k = 3).

## 4. Evaluation Dimensions

| Block | Question answered | Official metrics |
|---|---|---|
| A. Agentic Selection | Did the planner choose the right capabilities and tools? | Exact Capability Match, Tool Accuracy |
| B. RAG Retrieval | Given the correct information need, does the frozen retriever put the gold evidence in the top 3? | Hit@3, Recall@3, MRR |
| C. Final Answer Quality | Is the final answer correct, grounded in what the system actually used, and relevant? | LLM-as-Judge: Correctness, Faithfulness/Groundedness, Relevance |

These are the only official metrics. No BLEU, ROUGE, BERTScore, embedding similarity, answer
precision, composite score or weighted global score is part of D3 V1.

## 5. Agentic Selection Metrics

Notation: for question *i*, `G_i = (rag, weather, places)` is `gold_capabilities`. From the validated
plan returned by the planner:

    P_i.rag     = plan.use_rag
    P_i.weather = exists call in plan.tool_calls with call.server == "weather"
    P_i.places  = exists call in plan.tool_calls with call.server == "places"

If the planner fails (PlannerError: invalid plan twice), there is no plan: `P_i = (false, false, false)`.
Gold capability sets are never empty, so such a question is a miss.

### 5.1 Exact Capability Match (ECM)

    ECM_i = 1 if P_i == G_i (all three booleans equal), else 0
    ECM   = (1/35) * Σ_i ECM_i                        reported also as "Σ_i ECM_i / 35"

Missing a needed capability and adding an unneeded one are both mismatches.

### 5.2 Tool Accuracy (TA)

The dataset has 40 expected MCP tool selections: 20 Weather needs (`weather.expected_tool`) and 20
Places needs (`places.expected_tool`). For each gold need *n* on server *s* of question *i*:

    selected(i, s) = call.tool of the plan's call with call.server == s, or None if there is none
    TA_n = 1 if selected(i, s) == expected_tool(i, s), else 0
    TA   = (1/40) * Σ_n TA_n                          reported also as "Σ TA_n / 40"

Breakdown (not separate primary metrics): Weather Tool Accuracy = Σ over Weather needs / 20,
Places Tool Accuracy = Σ over Places needs / 20.

A missing call for a gold need is incorrect. A planner failure makes all needs of that question
incorrect. A call on a server that is not needed is **not** penalised again here: it is already
penalised by ECM. Tool arguments are stored for qualitative analysis but are not scored by a primary metric.

## 6. RAG Retrieval Metrics

### 6.1 Planner vs retriever separation (oracle information need)

Hit@3, Recall@3 and MRR measure the **retriever**, not the planner's query decomposition. For each
of the 20 questions with `gold_capabilities.rag == true`, the query used for these metrics is the
gold `rag.information_need` of the dataset, never the planner's `rag_query`. A bad `rag_query` is an
agency failure, not a retrieval failure.

**Oracle retrieval** (stored as `oracle_retrieval`):

    oracle_top3_i = retrieve(frozen_store, item.rag.information_need, k = 3)

with exactly the retriever and configuration the agent uses (`rag_pipeline.retrieve`, FROZEN_V2,
top_k = 3). "Oracle" only means that the correct information need is given to the retriever; the gold
documents are never given to the system. Oracle retrieval:

- runs after the end-to-end answer of the question is complete;
- is never passed to the planner, the tools, the final generator or the final answer;
- is used only for the retrieval metrics.

### 6.2 Formulas

For RAG question *i*: `Gc_i` = set of gold chunk IDs (`rag.gold_chunks`); `R_i` = ordered list of the
chunk IDs returned by the oracle retrieval (length ≤ 3).

    Hit@3_i    = 1 if |Gc_i ∩ set(R_i)| ≥ 1, else 0
    Hit@3      = (1/20) * Σ_i Hit@3_i                 reported also as "Σ Hit@3_i / 20"

    Recall@3_i = |Gc_i ∩ set(R_i)| / |Gc_i|           (distinct gold chunks retrieved)
    Recall@3   = (1/20) * Σ_i Recall@3_i              (macro average; no micro-aggregation)

    RR_i       = 1 / rank of the first r in R_i with r ∈ Gc_i   (rank 1 → 1.0, 2 → 0.5, 3 → 0.333…), 0 if none
    MRR        = (1/20) * Σ_i RR_i

Every question has |Gc_i| ≤ 3, so Recall@3_i = 1 is always attainable. Questions whose gold passage is
duplicated in several documents (D3_Q01, D3_Q20, D3_Q31, D3_Q32) have several gold chunks; Hit@3 and
Recall@3 are therefore always reported together. Gold chunks are never changed to improve Recall@3.
If the oracle retrieval of a question fails technically, that question scores 0 on the three metrics
and the failure is reported.

## 7. End-to-End Trace

Besides the oracle retrieval, the retrieval the agent **actually** used is stored as
`actual_retrieval` (query + top 3). It is not used by the Hit@3/Recall@3/MRR primary metrics; it is
kept for diagnosis and because it is the RAG evidence the generator received (needed for Faithfulness).

- **RAG-only plan** (use_rag and no tool calls): the agent calls the frozen D2 `RAGAgent.respond(question)`
  unchanged, so the effective query is the **original question**. D2 is frozen and is not modified to
  expose its chunks. Because retrieval on the frozen store is deterministic, the runner reconstructs it
  after the answer with the same retriever and configuration: `retrieve(store, question, k = 3)`. This is
  recorded as `capture_method = "reconstructed_with_same_frozen_retriever"`, and the D2 prompt context is
  rebuilt from those chunks with the D2 functions (`build_context`, `conflict_note`, `build_messages`).
- **RAG combined with MCP tools**: the effective query is `plan.rag_query`; the runner observes the
  agent's own retrieval call (`capture_method = "observed_agent_call"`).
- **No RAG in the plan**: `actual_retrieval.performed = false`.

The trace is captured through the agent's existing injectable attributes (`planner`, `clients`,
`pipeline`, `generate`, `rag`), each wrapped by a transparent recording proxy that delegates every call
unchanged. No stdout or debug log is parsed. `expert_agent.py`, `planner.py`, the prompts, the MCP
clients/servers and D2 are not modified.

## 8. MCP Raw Execution Capture

For each planned MCP call the runner stores, **before** any transformation by the final generator:
server, tool, arguments (as validated by the planner), whether it was executed, success/error, and the
raw structured output returned by the MCP tool (`raw_output`). The agent executes the planned calls in
plan order and stops at the first failing call (existing behaviour); a planned call that was not executed
because an earlier call failed is stored with `executed = false`.

The blocks that actually reached the final generator are stored in `generation_evidence`:
`rag_context`, `weather_data` and `places_data` as they appear in the final prompt (`null` when the
block was "(não utilizado)"), plus the full user message of the final prompt (`generator_user_message`).
For the RAG-only path, the D2 prompt is reconstructed as described in Section 7. No chain-of-thought or
hidden reasoning is stored (the models used produce none).

## 9. LLM-as-Judge Dimensions

Each of the 35 final answers is scored on three independent dimensions:

- **Correctness**: does the answer correctly satisfy the question, w.r.t. the gold stable facts and the
  real Weather/Places outputs captured in that run?
- **Faithfulness / Groundedness**: is every relevant factual claim supported by the evidence the system
  actually used (actual RAG context, Weather raw output, Places raw output)?
- **Relevance**: does it directly address all needs of the question without material digressions?

Judge input per question: the question; from the frozen dataset the gold capabilities, Essential Facts
with evidence excerpts, expected tools and `answer_requirements`; from the run the `generation_evidence`,
the Weather and Places `raw_output`, and the final answer. The judged answer is the full string
returned by the agent (including the source lines the agent appends).

## 10. LLM-as-Judge Rubric

Scale: **0 = Poor, 1 = Partial, 2 = Good**.

### Correctness

- **2 — Good**: satisfies correctly the relevant requirements of the question; stable facts are correct
  w.r.t. the gold; the Weather/Places values used are correct w.r.t. the real outputs captured in that run;
  no important part of the question is missing.
- **1 — Partial**: mostly correct but omits a relevant part, contains a minor inaccuracy, answers a need
  only partially, or gives a reasonable but incomplete conclusion.
- **0 — Poor**: substantially wrong, does not answer the request, contradicts the data, fails an
  essential part, or the system ended with an error and no useful answer.

### Faithfulness / Groundedness

- **2 — Good**: every relevant factual claim is supported by the RAG context actually retrieved, the
  Weather raw output and the Places raw output, as applicable.
- **1 — Partial**: a minor extrapolation or weakly supported claim, while the core remains grounded.
- **0 — Poor**: relevant hallucination; values absent from the data; invented relations; a distance that
  was not obtained; invented weather; claims contradicting the evidence; or a substantially ungrounded answer.
- If there is no useful answer because of a system error, Faithfulness = 0 (an empty answer must not get
  an artificially high Faithfulness).

### Relevance

- **2 — Good**: answers directly all relevant needs with useful content and no material digressions.
- **1 — Partial**: contains the main answer but includes irrelevant content, is excessively vague, or
  omits a secondary part.
- **0 — Poor**: does not answer the main request, or most of the answer is irrelevant.

A question that ended with a system error and no answer scores 0 on all three dimensions.

Reporting per dimension: mean score over the 35 questions (0–2) and the count of 0/1/2 scores, overall
and per category. The three dimensions are never combined into one score.

## 11. Dynamic Data

Weather and Places values are not frozen in the dataset. Correctness and Faithfulness for the dynamic
parts are judged against the raw outputs captured **in the same run** (`weather.raw_output`,
`places.raw_output`), never against values from another date or another lookup. If Nominatim resolved
an unexpected candidate, the answer is judged against what was returned; the resolution itself is visible
in the raw output. Relative dates ("amanhã", "depois de amanhã") are interpreted relative to the run date
recorded in the manifest (the planner and the final prompt use the current local date).

## 12. Qualitative Recommendation Policy

Questions such as "Vale a pena levar guarda-chuva?" (D3_Q09), "dá para correr com o tempo que está
agora?" (D3_Q19), "está bom para estar ao ar livre?" (D3_Q30) or "Vai estar bom tempo?" (D3_Q31) have no
fixed YES/NO gold. The judge evaluates:

1. whether the weather data used are correct w.r.t. the captured Weather raw output;
2. whether the recommendation is coherent with those data.

Two different recommendations that are both coherent with the real output are not penalised against each
other.

## 13. Execution Procedure

Runner: `d3/evaluation/run_d3_evaluation.py`.

- Default (no flags) and `--validate-only`: validation only. Loads the dataset, validates schema and
  balance, verifies the dataset and protocol hashes, prints a summary and exits. It loads no model,
  embedding, vector store or MCP server, accesses no network and writes no run directory.
- Official run: only with **both** `--execute` and `--confirm-frozen-v1`. Either flag alone aborts before
  anything is loaded.

Pre-execution checks (all must pass before Ollama, embeddings, Chroma or MCP are touched; any failure
aborts): dataset file exists; JSON valid; IDs D3_Q01–D3_Q35 each exactly once; 35 questions; dataset
hashes equal the freeze manifest (and the values pinned in the runner); protocol hash equals
`D3_EVALUATION_PROTOCOL_V1.sha256` (and the value pinned in the runner); 7 categories × 5; capabilities
20/20/20; per-item schema.

One official run:

1. Copy the frozen store `chroma_frozen_v2` to a temporary runtime copy (the original is never opened);
   record a digest of the original store before and after the run.
2. Load the D2 RAGAgent (FROZEN_V2) on the runtime copy and the Coimbra Expert **once** (`load_expert`):
   one long-lived Weather MCP session and one long-lived Places MCP session for the whole run.
3. Process D3_Q01 → D3_Q35 in order, one at a time: end-to-end `expert.respond(question)`, then, for RAG
   questions, the isolated oracle retrieval. Each result line is written and flushed immediately.
4. Close both MCP sessions at the end (also on abort).

Not allowed: shuffling, cherry-picking, repeating a question because the answer was bad, repeating a
Nominatim lookup because of a strange candidate, re-running the planner to get a better plan, any
benchmark-level retry, resuming a run. The system's own internal behaviour (e.g. the planner's single
retry on invalid JSON) is part of the system and is kept.

## 14. Failure Handling

- **Startup failure** (before the first question: Ollama not reachable or model missing, embeddings or
  Chroma not loadable, an MCP server does not start): the run is **INVALID / ABORTED**
  (`status = ABORTED`, `abort_stage = startup`, `valid_experimental_run = false`) and does not count as an
  experimental run.
- **Per-question failure during the run** (planner error, MCP tool error, retrieval/generation error):
  the error is stored in that question's record (`error`, plus the stage-specific fields), the question is
  not repeated and the run continues with the next question. These are real results (e.g. tool execution
  failures) and are scored as specified (Sections 5, 6, 10).
- **Process crash / interruption mid-run**: the partial `raw_results.jsonl` is preserved and the manifest
  is marked `ABORTED` (`abort_stage = during_run`). Missing questions are never completed later inside the
  same `run_id`; a new attempt is a new run with a new `run_id`. Only a COMPLETED run is scored.

## 15. Reproducibility

Each run lives in its own directory `d3/evaluation/runs/<run_id>/` with
`run_id = YYYYMMDDTHHMMSS±HHMM` (local start time); an existing directory is never overwritten.

`run_manifest.json` records: run_id; status (RUNNING / COMPLETED / ABORTED); started_at; finished_at;
abort information; dataset paths and SHA-256; protocol path and SHA-256; git commit and dirty status;
Python version; installed versions of the relevant packages; planner model and temperature; final
generator model and temperature; embedding model and query prompt; top_k; collection name; original and
runtime vector-store paths and a content digest of the original store before and after the run; Weather
and Places MCP server paths with the SHA-256 of their server and service files (the servers have no
version number); Ollama model digests when Ollama reports them; question count expected and completed.
Information that is not available is stored as `null`, never invented.

When a run ends COMPLETED, `RUN.sha256` stores the SHA-256 of `raw_results.jsonl` and
`run_manifest.json`. These files are never modified afterwards; any processing writes new derived files.

The planner runs at temperature 0.0 and the generator at 0.1 (FROZEN_V2); Weather and Places data are
live. A run is therefore a single observation, not a deterministic replay.

## 16. Raw Result Schema

`raw_results.jsonl`: one JSON object per question, in dataset order. Every block is always present; a
capability that was not used has its fields set to `null` (never omitted).

    {
      "id", "category", "question",
      "timing": {"started_at", "finished_at", "duration_seconds"},
      "gold_snapshot": {"capabilities": {"rag", "weather", "places"},
                        "expected_weather_tool", "expected_places_tool"},
      "planner": {"success", "use_rag", "rag_query", "tool_calls": [{"server", "tool", "arguments"}], "error"},
      "actual_retrieval": {"performed", "query", "capture_method",
                           "top3": [{"rank", "chunk_id", "document_id", "section", "cosine_distance", "text"}]},
      "oracle_retrieval": {"required_by_gold", "query", "top3": [...], "error"},
      "weather": {"planned", "tool", "arguments", "executed", "success", "raw_output", "error"},
      "places":  {"planned", "tool", "arguments", "executed", "success", "raw_output", "error"},
      "generation_evidence": {"capture_method", "rag_context", "weather_data", "places_data",
                              "generator_user_message"},
      "final_answer",
      "error": null | {"stage", "type", "message"}
    }

`cosine_distance` is the score returned by the frozen Chroma store (cosine distance, lower = closer).
The gold snapshot is minimal; the frozen dataset remains the source of truth. The runner computes no
metric and no judge score.

## 17. Judge Configuration

**Judge model: NOT YET LOCKED.**

Requirements for the judge, to be fixed in a separate judge configuration file that is frozen (and
hashed) before the first judge run:

- a model different from the evaluated `llama3.2:3b`;
- more capable than the evaluated model;
- the same judge model, version and configuration for all 35 answers;
- fixed temperature;
- exact model identifier/version, prompt and parameters recorded before the first judge run.

The judge is not chosen merely because it is available. Raw results can be collected before the judge is
locked; the judge never influences the run.

## 18. What Is Not Evaluated

- the outer classifier of the integrated chatbot (ELIZA_RUDE vs Coimbra Expert) and keyword routing;
- D1 ELIZA_RUDE;
- n-gram or embedding similarity metrics (BLEU, ROUGE, BERTScore, semantic similarity), answer
  precision, composite or weighted global scores;
- the semantic quality of tool arguments and of the planner's `rag_query` as primary metrics (they are
  stored for qualitative error analysis only);
- latency (durations are recorded for information only).

## 19. Protocol Integrity

The SHA-256 of this file is stored in `d3/evaluation/D3_EVALUATION_PROTOCOL_V1.sha256` and pinned in the
runner; the runner refuses to execute if the file does not match. The hash is intentionally not written
inside this document.
