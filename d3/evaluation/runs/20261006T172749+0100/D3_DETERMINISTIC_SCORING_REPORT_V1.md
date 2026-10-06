# D3 Deterministic Scoring Report V1

Scoring version: `D3_DETERMINISTIC_SCORING_V1`. Scored with `d3/evaluation/score_d3_evaluation.py` (standard library only) from the frozen dataset, the frozen protocol and the official raw run. Nothing was re-executed; no agent, planner, retriever, embedding model, MCP server, LLM or network was used. No LLM-as-Judge score is included.

## 1. Run Scored

| Field | Value |
|---|---|
| run_id | `20261006T172749+0100` |
| run directory | `d3/evaluation/runs/20261006T172749+0100` |
| git commit | `d9d6cb84cc56f5692f65a4ccece2b6c384e4a5c6` |
| git dirty | False |
| run status | COMPLETED (valid_experimental_run = True) |
| started_at | 2026-10-06T17:27:49.030683+01:00 |
| finished_at | 2026-10-06T17:32:09.430910+01:00 |
| run date (for relative dates) | 2026-10-06 |

## 2. Integrity Validation

| Check | Result |
|---|---|
| dataset `D3_EVALUATION_SET_V1.md` = freeze manifest = runner pin = run manifest | PASS (`d15356000ee620fe6341396d7699653638a34685411f8ab0df37f5e7710f1f01`) |
| dataset `d3_evaluation_set_v1.json` = freeze manifest = runner pin = run manifest | PASS (`3cef162c592e3e18c18103a970b926f949dc9e1115f971bfea3c5595674e0528`) |
| dataset `D3_EVALUATION_SET_AUDIT_V1.md` = freeze manifest = runner pin = run manifest | PASS (`7171c366cd15c8e0b7bc13c5baa20c31ab94b28d062a84d9486cfc3cf805afaa`) |
| protocol `D3_EVALUATION_PROTOCOL_V1.md` = freeze manifest = runner pin = run manifest | PASS (`1dd9974ee18e000326b58e30902d8bf3810155d23961ea0c62677f464e6a1e59`) |
| `raw_results.jsonl` = RUN.sha256 | PASS (`ddf6823222266a93142d7576ac7b3af4514f2628b4683094cf5a9827d7f7ccfa`) |
| `run_manifest.json` = RUN.sha256 | PASS (`5c82b5ab5443a2b548528a8bd661fae9b7df81aef3a3848149a6f64411c156e7`) |
| status COMPLETED, valid_experimental_run, 35 expected / 35 completed | PASS |
| raw records | PASS (35/35 valid JSON lines; IDs D3_Q01→D3_Q35 in order; no duplicate or missing ID) |
| question text, category and gold snapshot = frozen dataset | PASS (35/35) |
| RAG questions / expected MCP tool needs | PASS (20 / 40) |

Overall: **PASS**. The scorer aborts before computing anything if any check fails.

## 3. Official Metrics

| Block | Metric | Result |
|---|---|---|
| Agency | Exact Capability Match | 26/35 (74.3%) |
| Agency | Tool Accuracy | 36/40 (90.0%) |
| Retrieval | Hit@3 | 20/20 (100.0%) |
| Retrieval | Recall@3 (macro) | 0.900 (90.0%) |
| Retrieval | MRR | 0.975 |

Retrieval metrics use the oracle retrieval captured in the run (query = gold `rag.information_need`, top-3 of the frozen retriever) against the gold chunks, over the 20 RAG questions. Unrounded values are in `deterministic_scores_v1.json`.

## 4. Exact Capability Match by Category

Breakdown of ECM (not a separate primary metric).

| Category | ECM |
|---|---|
| RAG | 5/5 (100.0%) |
| WEATHER | 5/5 (100.0%) |
| PLACES | 2/5 (40.0%) |
| RAG+WEATHER | 5/5 (100.0%) |
| RAG+PLACES | 5/5 (100.0%) |
| WEATHER+PLACES | 1/5 (20.0%) |
| RAG+WEATHER+PLACES | 3/5 (60.0%) |

## 5. Tool Accuracy Breakdown

Informative breakdown of Tool Accuracy (not separate primary metrics).

| Server | Correct expected-tool selections |
|---|---|
| Weather | 19/20 (95.0%) |
| Places | 17/20 (85.0%) |
| **Total** | **36/40 (90.0%)** |

## 6. Retrieval Per Question

| ID | Gold chunks | Gold retrieved | First gold rank | Hit@3 | Recall@3 | RR | Oracle top-3 (chunk_id, cosine distance) |
|---|---|---|---|---|---|---|---|
| D3_Q01 | 3 | 2 | 1 | 1 | 0.667 | 1.000 | 1. `universidade-alta-sofia-patrimonio-mundial::c0013` (0.243)<br>2. `viver-o-patrimonio-em-coimbra::c0003` (0.308)<br>3. `universidade-alta-sofia-patrimonio-mundial::c0003` (0.342) |
| D3_Q02 | 2 | 2 | 1 | 1 | 1.000 | 1.000 | 1. `web-visitecoimbra-ceramica-de-coimbra::c0001` (0.225)<br>2. `web-visitecoimbra-ceramica-de-coimbra::c0002` (0.262)<br>3. `web-visitecoimbra-ceramica-de-coimbra::c0005` (0.288) |
| D3_Q03 | 2 | 2 | 1 | 1 | 1.000 | 1.000 | 1. `web-visitecoimbra-sesnando-david::c0001` (0.161)<br>2. `web-visitecoimbra-sesnando-david::c0002` (0.210)<br>3. `web-visitecoimbra-sesnando-david::c0003` (0.294) |
| D3_Q04 | 2 | 1 | 1 | 1 | 0.500 | 1.000 | 1. `web-visitecoimbra-docaria-conventual-de-coimbra::c0004` (0.200)<br>2. `web-visitecoimbra-coimbra-muralhada::c0001` (0.421)<br>3. `web-visitecoimbra-heranca-cultural-e-religiosa::c0027` (0.426) |
| D3_Q05 | 2 | 2 | 1 | 1 | 1.000 | 1.000 | 1. `web-visitecoimbra-heranca-judaica::c0001` (0.353)<br>2. `web-visitecoimbra-heranca-judaica::c0002` (0.476)<br>3. `web-visitecoimbra-heranca-judaica::c0003` (0.577) |
| D3_Q16 | 1 | 1 | 1 | 1 | 1.000 | 1.000 | 1. `web-visitecoimbra-gastronomia-em-coimbra::c0001` (0.170)<br>2. `web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira::c0001` (0.307)<br>3. `web-visitecoimbra-restauracao::c0005` (0.309) |
| D3_Q17 | 1 | 1 | 1 | 1 | 1.000 | 1.000 | 1. `web-visitecoimbra-cancao-de-coimbra::c0002` (0.231)<br>2. `web-visitecoimbra-ceramica-de-coimbra::c0001` (0.387)<br>3. `web-visitecoimbra-ceramica-de-coimbra::c0002` (0.424) |
| D3_Q18 | 1 | 1 | 1 | 1 | 1.000 | 1.000 | 1. `web-visitecoimbra-rainha-santa-isabel::c0001` (0.300)<br>2. `web-visitecoimbra-docaria-conventual-de-coimbra::c0010` (0.464)<br>3. `web-visitecoimbra-rainha-santa-isabel::c0003` (0.501) |
| D3_Q19 | 1 | 1 | 1 | 1 | 1.000 | 1.000 | 1. `web-visitecoimbra-desporto::c0004` (0.195)<br>2. `web-visitecoimbra-coimbra-by-night::c0001` (0.401)<br>3. `web-visitecoimbra-desporto::c0003` (0.403) |
| D3_Q20 | 3 | 2 | 1 | 1 | 0.667 | 1.000 | 1. `fado-e-tradicoes-academicas::c0005` (0.485)<br>2. `universidade-alta-sofia-patrimonio-mundial::c0015` (0.498)<br>3. `viver-o-patrimonio-em-coimbra::c0002` (0.510) |
| D3_Q21 | 1 | 1 | 1 | 1 | 1.000 | 1.000 | 1. `web-visitecoimbra-heranca-cultural-e-religiosa::c0023` (0.181)<br>2. `fado-e-tradicoes-academicas::c0018` (0.532)<br>3. `jardins-historicos::c0015` (0.542) |
| D3_Q22 | 2 | 2 | 1 | 1 | 1.000 | 1.000 | 1. `web-visitecoimbra-heranca-cultural-e-religiosa::c0024` (0.304)<br>2. `universidade-alta-sofia-patrimonio-mundial::c0049` (0.366)<br>3. `universidade-alta-sofia-patrimonio-mundial::c0060` (0.564) |
| D3_Q23 | 1 | 1 | 1 | 1 | 1.000 | 1.000 | 1. `jardins-historicos::c0021` (0.249)<br>2. `jardins-historicos::c0023` (0.580)<br>3. `coimbra-dos-escritores::c0001` (0.583) |
| D3_Q24 | 1 | 1 | 1 | 1 | 1.000 | 1.000 | 1. `web-visitecoimbra-coimbra-muralhada::c0001` (0.419)<br>2. `viver-o-patrimonio-em-coimbra::c0017` (0.574)<br>3. `fado-e-tradicoes-academicas::c0013` (0.581) |
| D3_Q25 | 2 | 2 | 1 | 1 | 1.000 | 1.000 | 1. `web-visitecoimbra-museus::c0024` (0.301)<br>2. `coimbra-dos-escritores::c0022` (0.340)<br>3. `coimbra-dos-escritores::c0001` (0.450) |
| D3_Q31 | 3 | 3 | 1 | 1 | 1.000 | 1.000 | 1. `web-visitecoimbra-heranca-cultural-e-religiosa::c0027` (0.370)<br>2. `web-visitecoimbra-museus::c0012` (0.420)<br>3. `coimbra-para-os-pequenitos::c0007` (0.457) |
| D3_Q32 | 3 | 2 | 2 | 1 | 0.667 | 0.500 | 1. `web-visitecoimbra-museus::c0013` (0.255)<br>2. `web-visitecoimbra-heranca-cultural-e-religiosa::c0026` (0.379)<br>3. `fado-e-tradicoes-academicas::c0012` (0.425) |
| D3_Q33 | 1 | 1 | 1 | 1 | 1.000 | 1.000 | 1. `web-visitecoimbra-tecelagem-de-almalagues::c0001` (0.159)<br>2. `web-visitecoimbra-tecelagem-de-almalagues::c0003` (0.227)<br>3. `web-visitecoimbra-tecelagem-de-almalagues::c0002` (0.356) |
| D3_Q34 | 2 | 1 | 1 | 1 | 0.500 | 1.000 | 1. `web-visitecoimbra-docaria-conventual-de-coimbra::c0006` (0.345)<br>2. `web-visitecoimbra-heranca-cultural-e-religiosa::c0008` (0.428)<br>3. `fundacao-da-nacionalidade::c0002` (0.473) |
| D3_Q35 | 1 | 1 | 1 | 1 | 1.000 | 1.000 | 1. `universidade-alta-sofia-patrimonio-mundial::c0029` (0.345)<br>2. `fado-e-tradicoes-academicas::c0003` (0.602)<br>3. `fado-e-tradicoes-academicas::c0010` (0.607) |

Cosine distances are shown for diagnosis only; they are not a D3 metric.

Retrieval cases with Hit@3 = 0, Recall@3 < 1 or RR < 1:

| ID | Gold chunks | Oracle top-3 | Hit@3 | Recall@3 | RR |
|---|---|---|---|---|---|
| D3_Q01 | `viver-o-patrimonio-em-coimbra::c0003`, `fado-e-tradicoes-academicas::c0006`, `universidade-alta-sofia-patrimonio-mundial::c0013` | `universidade-alta-sofia-patrimonio-mundial::c0013`, `viver-o-patrimonio-em-coimbra::c0003`, `universidade-alta-sofia-patrimonio-mundial::c0003` | 1 | 0.667 | 1.000 |
| D3_Q04 | `web-visitecoimbra-docaria-conventual-de-coimbra::c0004`, `web-visitecoimbra-docaria-conventual-de-coimbra::c0002` | `web-visitecoimbra-docaria-conventual-de-coimbra::c0004`, `web-visitecoimbra-coimbra-muralhada::c0001`, `web-visitecoimbra-heranca-cultural-e-religiosa::c0027` | 1 | 0.500 | 1.000 |
| D3_Q20 | `viver-o-patrimonio-em-coimbra::c0002`, `fado-e-tradicoes-academicas::c0005`, `universidade-alta-sofia-patrimonio-mundial::c0009` | `fado-e-tradicoes-academicas::c0005`, `universidade-alta-sofia-patrimonio-mundial::c0015`, `viver-o-patrimonio-em-coimbra::c0002` | 1 | 0.667 | 1.000 |
| D3_Q32 | `web-visitecoimbra-heranca-cultural-e-religiosa::c0026`, `fado-e-tradicoes-academicas::c0012`, `coimbra-dos-escritores::c0020` | `web-visitecoimbra-museus::c0013`, `web-visitecoimbra-heranca-cultural-e-religiosa::c0026`, `fado-e-tradicoes-academicas::c0012` | 1 | 0.667 | 0.500 |
| D3_Q34 | `viver-o-patrimonio-em-coimbra::c0023`, `web-visitecoimbra-docaria-conventual-de-coimbra::c0006` | `web-visitecoimbra-docaria-conventual-de-coimbra::c0006`, `web-visitecoimbra-heranca-cultural-e-religiosa::c0008`, `fundacao-da-nacionalidade::c0002` | 1 | 0.500 | 1.000 |

## 7. Agency Errors

Questions with ECM = 0. Observations are mechanical comparisons of the plan with the gold, not causal explanations.

| ID | Category | Gold | Predicted | Planner tool calls | Observation |
|---|---|---|---|---|---|
| D3_Q11 | PLACES | Places | RAG + Places | places.search_place({"country_code": "pt", "query": "Casa-Museu Bissaya Barreto, Coimbra"}) | RAG capability added although gold=false |
| D3_Q14 | PLACES | Places | RAG + Places | places.get_distance_between_places({"country_code": "pt", "destination": "Parque Dr. Manuel Braga, Portugal", "origin": "Mata Nacional do Choupal, Portugal"}) | RAG capability added although gold=false |
| D3_Q15 | PLACES | Places | RAG + Places | places.get_distance_between_places({"country_code": "pt", "destination": "Praça da Canção, Coimbra", "origin": "Seminário Maior, Coimbra"}) | RAG capability added although gold=false |
| D3_Q26 | WEATHER+PLACES | Weather + Places | RAG + Weather + Places | places.search_place({"country_code": "pt", "query": "Pátio da Inquisição, Coimbra"}); weather.get_current_weather({"location": "Coimbra, Portugal"}) | RAG capability added although gold=false |
| D3_Q27 | WEATHER+PLACES | Weather + Places | RAG + Places | places.get_distance_between_places({"country_code": "pt", "destination": "Museu da Água, Coimbra", "origin": "Estádio Universitário de Coimbra, Coimbra"}) | RAG capability added although gold=false; Weather capability absent although gold=true |
| D3_Q28 | WEATHER+PLACES | Weather + Places | RAG + Weather + Places | weather.get_weather_forecast({"days": 2, "location": "Coimbra, Portugal"}); places.get_distance_between_places({"country_code": "pt", "destination": "Mata Nacional de Vale de Canas, Coimbra", "origin": "Praça do Comércio, Coimbra"}) | RAG capability added although gold=false |
| D3_Q29 | WEATHER+PLACES | Weather + Places | RAG + Weather + Places | weather.get_weather_forecast({"days": 3, "location": "Coimbra, Portugal"}); places.get_distance_between_places({"country_code": "pt", "destination": "Ponte Pedonal Pedro e Inês, Coimbra", "origin": "Convento São Francisco, Coimbra"}) | RAG capability added although gold=false |
| D3_Q32 | RAG+WEATHER+PLACES | RAG + Weather + Places | Weather | weather.get_current_weather({"location": "Coimbra, Portugal"}) | RAG capability absent although gold=true; Places capability absent although gold=true |
| D3_Q34 | RAG+WEATHER+PLACES | RAG + Weather + Places | RAG + Weather | weather.get_current_weather({"location": "Coimbra, Portugal"}) | Places capability absent although gold=true |

## 8. Tool Selection Errors

Expected-tool selections that were missing or different (Tool Accuracy = 0 for that need).

| ID | Category | Server | Expected tool | Selected tool | Observation |
|---|---|---|---|---|---|
| D3_Q25 | RAG+PLACES | places | get_distance_between_places | search_place | search_place selected instead of get_distance_between_places |
| D3_Q27 | WEATHER+PLACES | weather | get_current_weather | — | no weather call in the plan |
| D3_Q32 | RAG+WEATHER+PLACES | places | get_distance_between_places | — | no places call in the plan |
| D3_Q34 | RAG+WEATHER+PLACES | places | get_distance_between_places | — | no places call in the plan |

## 9. Descriptive Execution Outcomes

**NOT AN OFFICIAL METRIC.** Descriptive counts of what happened during the run. They do not change ECM or Tool Accuracy: a correctly selected tool that failed to execute still counts as a correct selection.

| Outcome | Count |
|---|---|
| Final answers produced | 31 |
| Questions with no final answer | 4 (D3_Q22, D3_Q24, D3_Q34, D3_Q35) |
| Planner failures | 0 |
| Weather calls planned / executed / succeeded / failed | 19 / 19 / 18 / 1 (D3_Q34) |
| Places calls planned / executed / succeeded / failed | 18 / 18 / 15 / 3 (D3_Q22, D3_Q24, D3_Q35) |
| Oracle retrieval errors | 0 |

Errors by stage:

| Stage | Count | IDs |
|---|---|---|
| places | 3 | D3_Q22, D3_Q24, D3_Q35 |
| weather | 1 | D3_Q34 |

## 10. Interpretation Boundaries

- **Exact Capability Match** measures capability selection by the planner (RAG / Weather / Places), all-or-nothing per question.
- **Tool Accuracy** measures only the selected tool name for each of the 40 gold needs. Tool arguments are not scored (they are listed in Section 7 for qualitative analysis), and an extra call on a non-gold server is penalised only by ECM.
- **Hit@3 / Recall@3 / MRR** measure the frozen retriever given the gold information need (oracle retrieval), not the planner's `rag_query`; `actual_retrieval` is not used by these metrics.
- A **tool execution failure** does not change Tool Accuracy; execution outcomes are descriptive only (Section 9).
- **LLM-as-Judge** (Correctness, Faithfulness/Groundedness, Relevance) has not been run; no answer-quality claim follows from this report.
- One run is one observation (live Weather/Places data, LLM planner); the numbers describe this run.

## 11. Next Step

Freeze the judge configuration (a model different from and more capable than llama3.2:3b, fixed version and temperature, the prompt and the rubric of protocol Section 10) and run the LLM-as-Judge for Correctness, Faithfulness/Groundedness and Relevance on this run's raw results.
