# D3 Evaluation Set Audit V1

Audit date: 2026-10-06. Audited artefacts: `D3_EVALUATION_SET_V1.md`, `d3_evaluation_set_v1.json`.

All checks in this audit were made offline, from local files only: the item definitions, the frozen `chunks.jsonl`/`manifest.jsonl`, and a textual scan of the repository. **No question was sent to the planner, the Coimbra Expert Agent, the RAG pipeline/retriever, any embedding model, Ollama/llama3.2:3b, the Weather MCP (Open-Meteo), the Places MCP (Nominatim) or an LLM judge.** The audit therefore contains no predicted route, no retrieved top-3, no tool result, no generated answer and no judge score.

## 1. Purpose

The D3-O1 deliverable requires integrating the D2 RAG agent with domain-coherent MCP servers and a detailed evaluation using established RAG evaluation practice (optionally LLM-as-Judge). This dataset is the gold benchmark for that future evaluation. It supports four separately measured dimensions:

| Dimension | Gold used | Future metric (not computed here) |
|---|---|---|
| A. Agentic capability selection | `gold_capabilities` | Exact Capability Match, per-capability precision/recall |
| B. RAG retrieval | `rag.gold_chunks`, `rag.gold_documents` | Hit@3 / Recall@3 / MRR over top-3 (chunk and document level) |
| C. MCP / tool use | `weather.*`, `places.*` | correct tool, semantically adequate arguments, successful execution |
| D. Final answer quality | `answer_requirements`, `rag.essential_facts`, `rag.evidence` | LLM-as-Judge: Correctness, Faithfulness/Groundedness, Relevance |

## 2. Dataset Construction Rules

- Exactly 35 new questions, 5 per capability combination, grouped by category (Q01–Q05 RAG … Q31–Q35 RAG+Weather+Places).
- Natural PT-PT tourist questions; no system vocabulary (RAG, MCP, tool, planner, retrieval, vector, corpus…).
- No question designed to make the planner fail or pass, to exploit observed bugs, or to favour RAG or MCP.
- Every RAG question answerable from the frozen corpus; every Essential Fact has a verbatim excerpt in a cited indexed (`unit_role = content`) chunk. Facts without direct evidence were not admitted.
- Gold chunks chosen by reading `chunks.jsonl`; when the same passage exists in several documents, all of those chunks are gold.
- No volatile facts (opening hours, prices, current events) in RAG gold; Weather and Places gold contain no values.
- No reuse of smoke/dev/manual/prompt/unit-test/README questions; the factual needs of the D2 V2 evaluation set and of the planner dev set were also avoided.
- Entities with known Nominatim instability (Museu Nacional de Machado de Castro) and generic names (e.g. 'Universidade de Coimbra') were not used as Places targets.
- The gold plan is semantic: no exact `rag_query` string, no exact JSON; 'Coimbra' ≡ 'Coimbra, Portugal'.

## 3. Category Distribution

| Category | IDs | Count | Expected |
|---|---|---|---|
| RAG | Q01–Q05 | 5 | 5 |
| WEATHER | Q06–Q10 | 5 | 5 |
| PLACES | Q11–Q15 | 5 | 5 |
| RAG+WEATHER | Q16–Q20 | 5 | 5 |
| RAG+PLACES | Q21–Q25 | 5 | 5 |
| WEATHER+PLACES | Q26–Q30 | 5 | 5 |
| RAG+WEATHER+PLACES | Q31–Q35 | 5 | 5 |
| **Total** | | **35** | **35** |

Result: **PASS** — all 7 combinations have exactly 5 questions; IDs are contiguous D3_Q01–D3_Q35 (OK) and each category occupies its block.

Difficulty per category:

| Category | easy | medium | hard |
|---|---|---|---|
| RAG | 4 | 0 | 1 |
| WEATHER | 3 | 1 | 1 |
| PLACES | 4 | 1 | 0 |
| RAG+WEATHER | 0 | 4 | 1 |
| RAG+PLACES | 0 | 4 | 1 |
| WEATHER+PLACES | 0 | 4 | 1 |
| RAG+WEATHER+PLACES | 0 | 0 | 5 |
| **Total** | **11** | **14** | **10** |

Target ranges were 10–12 easy, 12–15 medium, 8–10 hard: all met. Easy = one explicit need; medium = two needs or a natural paraphrase; hard = three needs or a less direct formulation (e.g. 'dá para correr com o tempo que está agora?', 'está bom para estar ao ar livre?'). Every hard item still has a single defensible gold plan.

## 4. Capability Distribution

| Capability | Questions requiring it | Expected | Composition |
|---|---|---|---|
| RAG | 20 | 20 | RAG 5 + RAG+Weather 5 + RAG+Places 5 + RAG+Weather+Places 5 |
| Weather | 20 | 20 | Weather 5 + RAG+Weather 5 + Weather+Places 5 + RAG+Weather+Places 5 |
| Places | 20 | 20 | Places 5 + RAG+Places 5 + Weather+Places 5 + RAG+Weather+Places 5 |

Result: **PASS** (computed from `gold_capabilities`; each capability is required in 20/35 and absent in 15/35 questions, so per-capability precision and recall are both measurable).

## 5. Weather Tool Distribution

- `get_current_weather`: **10**
- `get_weather_forecast`: **10**

| Category | current | forecast |
|---|---|---|
| WEATHER | 3 | 2 |
| RAG+WEATHER | 2 | 3 |
| WEATHER+PLACES | 3 | 2 |
| RAG+WEATHER+PLACES | 2 | 3 |

Minimum forecast days required by the forecast questions: 2 days × 3, 3 days × 4, 4 days × 1, 5 days × 1, 7 days × 1.

Weather locations: Coimbra, Portugal × 19, Figueira da Foz, Portugal × 1. Almost all weather needs refer to Coimbra; Figueira da Foz (D3_Q08) is the single non-Coimbra case, included only to test location generality.

Temporal needs covered: current conditions (apparent temperature, sky/cloud cover, wind, temperature, general conditions, suitability for outdoor activity) and forecasts for tomorrow, the day after tomorrow, a comparison between tomorrow and the day after, and 3-, 4-, 5- and 7-day windows. Weekday-relative dates ('no sábado') were avoided so that the minimum number of forecast days does not depend on the execution date.

## 6. Places Tool Distribution

- `search_place`: **10**
- `get_distance_between_places`: **10**

| Category | search | distance |
|---|---|---|
| PLACES | 2 | 3 |
| RAG+PLACES | 3 | 2 |
| WEATHER+PLACES | 2 | 3 |
| RAG+WEATHER+PLACES | 3 | 2 |

Place entities used: 30 (no entity repeated: yes).

| ID | Role | Canonical name | Expected city |
|---|---|---|---|
| D3_Q11 | search | Casa-Museu Bissaya Barreto | Coimbra |
| D3_Q12 | origin | Mosteiro de Celas | Coimbra |
| D3_Q12 | destination | Igreja de Santo António dos Olivais | Coimbra |
| D3_Q13 | search | Casa da Escrita | Coimbra |
| D3_Q14 | origin | Mata Nacional do Choupal | Coimbra |
| D3_Q14 | destination | Parque Dr. Manuel Braga | Coimbra |
| D3_Q15 | origin | Seminário Maior de Coimbra | Coimbra |
| D3_Q15 | destination | Praça da Canção | Coimbra |
| D3_Q21 | search | Aqueduto de São Sebastião (Arcos do Jardim) | Coimbra |
| D3_Q22 | search | Palácio de Sub-Ripas | Coimbra |
| D3_Q23 | origin | Largo da Portagem | Coimbra |
| D3_Q23 | destination | Jardim da Manga (Claustro da Manga) | Coimbra |
| D3_Q24 | search | Conímbriga (ruínas romanas) | Condeixa-a-Nova (distrito de Coimbra) |
| D3_Q25 | origin | Casa-Museu Miguel Torga | Coimbra |
| D3_Q25 | destination | Praça da República | Coimbra |
| D3_Q26 | search | Pátio da Inquisição | Coimbra |
| D3_Q27 | origin | Estádio Universitário de Coimbra | Coimbra |
| D3_Q27 | destination | Museu da Água | Coimbra |
| D3_Q28 | origin | Mata Nacional de Vale de Canas | Coimbra |
| D3_Q28 | destination | Praça do Comércio | Coimbra |
| D3_Q29 | origin | Convento São Francisco | Coimbra |
| D3_Q29 | destination | Ponte Pedonal Pedro e Inês | Coimbra |
| D3_Q30 | search | UC Exploratório – Centro Ciência Viva de Coimbra | Coimbra |
| D3_Q31 | search | Torre de Almedina | Coimbra |
| D3_Q32 | origin | Torre de Anto | Coimbra |
| D3_Q32 | destination | Ponte de Santa Clara | Coimbra |
| D3_Q33 | search | Almalaguês (freguesia) | Coimbra |
| D3_Q34 | origin | Café Santa Cruz | Coimbra |
| D3_Q34 | destination | Mercado Municipal D. Pedro V | Coimbra |
| D3_Q35 | search | Departamento de Matemática da Universidade de Coimbra | Coimbra |

All Places gold uses `country_code = pt`. No coordinates or distances are stored; the distance answer requirement is that the tool's value be reported as a straight-line (geodesic) distance.

## 7. RAG Topic Coverage

| Topic | Questions |
|---|---|
| gastronomy | 3 — D3_Q04, D3_Q16, D3_Q34 |
| heritage | 3 — D3_Q21, D3_Q22, D3_Q31 |
| history | 3 — D3_Q03, D3_Q05, D3_Q24 |
| university | 3 — D3_Q01, D3_Q20, D3_Q35 |
| crafts | 2 — D3_Q02, D3_Q33 |
| gardens | 1 — D3_Q23 |
| literature_fado | 1 — D3_Q32 |
| museums_literature | 1 — D3_Q25 |
| music_fado | 1 — D3_Q17 |
| religion_legends | 1 — D3_Q18 |
| sport | 1 — D3_Q19 |

11 topics over 20 RAG questions; the largest topic has 3 questions. University-related questions (bells of the tower, Sala dos Capelos, Departamento de Matemática) are 3/20; the Sé Velha and the Jardim Botânico are not the subject of any RAG question.

| ID | Information need |
|---|---|
| D3_Q01 | sinos da Torre da Universidade de Coimbra: número, nomes e datas |
| D3_Q02 | as duas vertentes da louça de Coimbra e as suas diferenças |
| D3_Q03 | identidade de D. Sesnando e o seu papel na reconquista e governo de Coimbra |
| D3_Q04 | descrição da Arrufada de Coimbra |
| D3_Q05 | caracterização da Judiaria Velha medieval e vestígios materiais da comunidade judaica |
| D3_Q16 | influência do rio Mondego na gastronomia tradicional de Coimbra |
| D3_Q17 | diferenças entre a guitarra de Coimbra e a guitarra de Lisboa |
| D3_Q18 | a lenda do Milagre das Rosas |
| D3_Q19 | a prova de corrida de fim de ano emblemática de Coimbra (São Silvestre) |
| D3_Q20 | função histórica da Sala dos Capelos |
| D3_Q21 | quem mandou construir o Aqueduto de São Sebastião e com que finalidade |
| D3_Q22 | origem do Palácio de Sub-Ripas |
| D3_Q23 | origem do nome do Jardim/Claustro da Manga e autoria do desenho |
| D3_Q24 | razão da migração dos habitantes de Conímbriga para Æminium |
| D3_Q25 | autoria do projeto e abertura ao público da Casa-Museu Miguel Torga |
| D3_Q31 | funções históricas da Torre de Almedina |
| D3_Q32 | o que é a Torre de Anto e a origem do seu nome |
| D3_Q33 | características da tecelagem de Almalaguês |
| D3_Q34 | o doce associado ao Café Santa Cruz (Crúzios) e a sua composição |
| D3_Q35 | significado histórico da inauguração do Departamento de Matemática |

## 8. RAG Source Coverage

- Distinct RAG documents used as gold: **18** of 35 in the frozen corpus.
- Gold chunks: **35** (distinct: 35); evidence records: 56.
- Maximum number of questions depending on the same document: **4**.
- Gold chunks shared by two or more questions: **0** (no two questions test the same chunk).
- Questions whose gold evidence comes from a single document: 13; from several documents (passage duplicated across guides): 7.
- The two most used documents together cover 7 of the 20 RAG questions; no small group of documents dominates the benchmark.

| Document | # questions | Questions |
|---|---|---|
| `universidade-alta-sofia-patrimonio-mundial` | 4 | D3_Q01, D3_Q20, D3_Q22, D3_Q35 |
| `web-visitecoimbra-heranca-cultural-e-religiosa` | 4 | D3_Q21, D3_Q22, D3_Q31, D3_Q32 |
| `fado-e-tradicoes-academicas` | 3 | D3_Q01, D3_Q20, D3_Q32 |
| `viver-o-patrimonio-em-coimbra` | 3 | D3_Q01, D3_Q20, D3_Q34 |
| `coimbra-dos-escritores` | 2 | D3_Q25, D3_Q32 |
| `web-visitecoimbra-docaria-conventual-de-coimbra` | 2 | D3_Q04, D3_Q34 |
| `web-visitecoimbra-museus` | 2 | D3_Q25, D3_Q31 |
| `coimbra-para-os-pequenitos` | 1 | D3_Q31 |
| `jardins-historicos` | 1 | D3_Q23 |
| `web-visitecoimbra-cancao-de-coimbra` | 1 | D3_Q17 |
| `web-visitecoimbra-ceramica-de-coimbra` | 1 | D3_Q02 |
| `web-visitecoimbra-coimbra-muralhada` | 1 | D3_Q24 |
| `web-visitecoimbra-desporto` | 1 | D3_Q19 |
| `web-visitecoimbra-gastronomia-em-coimbra` | 1 | D3_Q16 |
| `web-visitecoimbra-heranca-judaica` | 1 | D3_Q05 |
| `web-visitecoimbra-rainha-santa-isabel` | 1 | D3_Q18 |
| `web-visitecoimbra-sesnando-david` | 1 | D3_Q03 |
| `web-visitecoimbra-tecelagem-de-almalagues` | 1 | D3_Q33 |

## 9. Essential Fact Audit

| Metric | Value |
|---|---|
| Total Essential Facts | 58 |
| Essential Facts with direct evidence | 58 |
| Essential Facts requiring inference | 0 |
| Direct-evidence rate | 100% |

Verification method (automated, string-level, no model):

1. every cited `chunk_id` exists in the frozen `chunks.jsonl` and has `unit_role = content` (i.e. it is indexed by FROZEN_V2);
2. every `text_excerpt` is an exact substring of that chunk's `text`;
3. every Essential Fact is listed in the `supports` of at least one evidence record;
4. every gold chunk supports at least one Essential Fact (gold chunks are derived from the evidence records);
5. no fact mentions opening hours, prices, tickets or current events.

Result: **PASS** — 0 structural errors.

Manual review of the fact wording against the excerpts (paraphrase only, no added information) was also done. Points of care resolved during construction:

- **D3_Q32 (Torre de Anto):** the corpus is inconsistent about what the tower houses today (`web-visitecoimbra-museus::c0013`: Casa do Artesanato / Núcleo Museológico da Memória da Escrita; three other documents: Núcleo da Guitarra e do Fado de Coimbra). The question therefore only asks what the tower is and why it has its name, which all three gold chunks state consistently.
- **D3_Q34 (Café Santa Cruz → Crúzios):** two documents are combined, but the link is explicit — `viver-o-patrimonio-em-coimbra::c0023` names the Crúzios as the sweet of the café, and the doçaria chunk describes the Crúzios by name. No association is inferred (the D2 V1 problem is not repeated).
- **D3_Q01:** the corpus gives no date for the 'quartos' bell; the fact says so explicitly so a judge does not reward an invented date.
- **D3_Q22:** 'Sub-Ripas' / 'Sub-Ribas' are both corpus spellings of the same building.
- **D3_Q24:** the RAG facts only cover the Conímbriga → Æminium migration; the municipality of Conímbriga is a Places requirement and is not presented as a corpus fact.
- **Seminário Maior / Colégio de Jesus** (conflicting statements across documents) and **Mosteiro/Convento de São Francisco** (13th-century monastery vs. 1602 convent) were not used as RAG targets.

## 10. Dynamic Data Policy

- **Weather:** gold = `expected_tool`, `location_requirement`, `temporal_requirement`, `minimum_forecast_days`, plus answer requirements phrased as *types* of information (e.g. 'state whether precipitation is expected …'). No temperature, precipitation, wind, cloud cover or weather code is stored.
- **Places:** gold = `expected_tool` and canonical place name / expected city / `country_code`. No coordinates, addresses or distances are stored.
- **At execution time** the real tool outputs will be captured alongside each answer; Correctness and Faithfulness for the dynamic parts will be judged against those captured outputs, not against frozen values.
- **RAG:** only stable facts. Restaurant listings, schedules (market days, opening days of the Exploratório, etc.), prices and event dates were not used as gold.
- **Judge scores:** no `correctness_score`, `faithfulness_score` or `relevance_score` fields exist in V1.

## 11. Leakage / Reuse Audit

**Literal leakage.** Each normalised question (case-folded, quotes removed, whitespace collapsed) was searched in 136 text files of the repository (`.py .md .json .jsonl .txt .toml .yaml .csv`; excluding `.git`, Chroma stores, caches and `d3/evaluation/` itself) — including `prompts.py`, `planner.py`, `dev_planner_check.py`, `smoke_test.py`, all unit tests, all reports, all READMEs, the D2 evaluation sets/results and the classifier data. Matches found: **0**.

**Near-reuse.** Every question was compared (difflib ratio on normalised text) with 101 reference questions extracted from:

- `d3/coimbra_expert/prompts.py`: 5
- `d3/coimbra_expert/dev_planner_check.py`: 14
- `d3/coimbra_expert/smoke_test.py`: 10
- `d3/coimbra_expert/tests/test_expert_agent.py`: 13
- `d3/coimbra_expert/tests/test_planner.py`: 5
- `d3/coimbra_expert/tests/test_places_mcp_client.py`: 2
- `d3/coimbra_expert/tests/test_weather_mcp_client.py`: 1
- `d3/coimbra_expert/AGENTIC_INTEGRATION_REPORT.md`: 7
- `d3/weather_mcp/WEATHER_MCP_IMPLEMENTATION_REPORT.md`: 1
- `d2_rag/D2_ANSWER_QUALITY_EVALUATION_SET_V2.md`: 21
- `task brief (manual tests)`: 22

The reference set includes the planner few-shot examples (Lisboa / Torre de Belém / Mosteiro dos Jerónimos / Porto / Palácio da Bolsa / Santa Clara-a-Velha), the 14 dev-set questions, the smoke-test questions, unit-test questions, report examples, the 20 D2 V2 questions and the 22 manual formulations listed in the task brief.

| ID | Highest similarity | Closest reference (source) |
|---|---|---|
| D3_Q01 | 0.54 | Onde fica o Museu da Ciência da Universidade de Coimbra e o que se pode ver lá? (`d3/coimbra_expert/dev_planner_check.py`) |
| D3_Q02 | 0.50 | Quem foi Inês de Castro e que ligação tem a Coimbra? (`d3/coimbra_expert/dev_planner_check.py`) |
| D3_Q03 | 0.60 | Quem foi Inês de Castro e que ligação tem a Coimbra? (`d3/coimbra_expert/dev_planner_check.py`) |
| D3_Q04 | 0.59 | Que tempo está agora em Coimbra e onde fica a Sé Velha? (`d3/coimbra_expert/smoke_test.py`) |
| D3_Q05 | 0.44 | Como é preparado o bunho para a cestaria de Arzila e que tipos de peças são produzidos com ele? (`d2_rag/D2_ANSWER_QUALITY_EVALUATION_SET_V2.md`) |
| D3_Q06 | 0.69 | Está a chover neste momento em Coimbra? (`task brief (manual tests)`) |
| D3_Q07 | 0.55 | Qual é a temperatura atual em Coimbra? (`d3/coimbra_expert/smoke_test.py`) |
| D3_Q08 | 0.66 | Está a chover neste momento em Aveiro? (`d3/coimbra_expert/dev_planner_check.py`) |
| D3_Q09 | 0.55 | Vai estar frio nos próximos três dias em Coimbra? Fala-me também da tradição da capa e batina. (`d3/coimbra_expert/dev_planner_check.py`) |
| D3_Q10 | 0.43 | Que tempo está agora em Coimbra e onde fica o Portugal dos Pequenitos? (`task brief (manual tests)`) |
| D3_Q11 | 0.61 | Onde fica o Museu Nacional? (`task brief (manual tests)`) |
| D3_Q12 | 0.65 | Qual é a distância entre o Mosteiro de Santa Clara-a-Velha e o Museu Nacional de Machado de Castro? (`task brief (manual tests)`) |
| D3_Q13 | 0.49 | Onde se realiza a Regata da Queima das Fitas, quem compete e o que o evento celebra? (`d2_rag/D2_ANSWER_QUALITY_EVALUATION_SET_V2.md`) |
| D3_Q14 | 0.42 | Onde fica o Museu Nacional de Machado de Castro? (`task brief (manual tests)`) |
| D3_Q15 | 0.57 | Qual é a distância entre a Sé Nova de Coimbra e o Portugal dos Pequenitos? (`task brief (manual tests)`) |
| D3_Q16 | 0.55 | Qual é a temperatura atual em Coimbra e onde fica o Estádio Cidade de Coimbra? (`d3/coimbra_expert/dev_planner_check.py`) |
| D3_Q17 | 0.50 | Como estará o tempo amanhã em Évora e qual é a distância entre a Sé de Évora e o Templo Romano? (`d3/coimbra_expert/dev_planner_check.py`) |
| D3_Q18 | 0.40 | Que tempo vai fazer amanhã em Coimbra, onde fica a Quinta das Lágrimas e qual é a sua história? (`d3/coimbra_expert/dev_planner_check.py`) |
| D3_Q19 | 0.41 | Que tempo está agora em Coimbra e onde fica a Sé Velha? (`d3/coimbra_expert/smoke_test.py`) |
| D3_Q20 | 0.45 | Qual é a previsão para amanhã em Coimbra e para que servia o Jardim da Sereia? (`d3/coimbra_expert/smoke_test.py`) |
| D3_Q21 | 0.48 | Onde fica o Portugal dos Pequenitos e o que é esse local? (`task brief (manual tests)`) |
| D3_Q22 | 0.58 | Onde fica o Portugal dos Pequenitos e o que é esse local? (`task brief (manual tests)`) |
| D3_Q23 | 0.47 | Qual é a distância em linha reta entre a Sé Velha de Coimbra e o Jardim Botânico da Universidade de Coimbra? (`d3/coimbra_expert/smoke_test.py`) |
| D3_Q24 | 0.46 | Onde fica a Sé Velha de Coimbra e o que caracteriza a sua importância no património da cidade? (`d3/coimbra_expert/smoke_test.py`) |
| D3_Q25 | 0.45 | Onde fica o Museu da Ciência da Universidade de Coimbra e o que se pode ver lá? (`d3/coimbra_expert/dev_planner_check.py`) |
| D3_Q26 | 0.48 | Qual é a previsão para amanhã em Coimbra e explica-me o que são os Pastéis de Santa Clara. (`task brief (manual tests)`) |
| D3_Q27 | 0.46 | Como estará o tempo amanhã em Évora e qual é a distância entre a Sé de Évora e o Templo Romano? (`d3/coimbra_expert/dev_planner_check.py`) |
| D3_Q28 | 0.47 | Qual é a previsão para amanhã em Coimbra e para que servia o Jardim da Sereia? (`d3/coimbra_expert/smoke_test.py`) |
| D3_Q29 | 0.54 | Como estará o tempo amanhã em Évora e qual é a distância entre a Sé de Évora e o Templo Romano? (`d3/coimbra_expert/dev_planner_check.py`) |
| D3_Q30 | 0.45 | O que existia na Ínsua dos Bentos quando a Câmara a comprou em 1888 e quem ficou encarregado do projeto para a transformar em jardim público? (`d2_rag/D2_ANSWER_QUALITY_EVALUATION_SET_V2.md`) |
| D3_Q31 | 0.43 | Como vai estar o tempo amanhã em Coimbra, onde fica o Mosteiro de Santa Clara-a-Velha e explica-me brevemente a sua história. (`task brief (manual tests)`) |
| D3_Q32 | 0.48 | Como vai estar o tempo amanhã em Coimbra, onde fica o Mosteiro de Santa Clara-a-Velha e explica-me brevemente a sua história. (`task brief (manual tests)`) |
| D3_Q33 | 0.44 | Que tempo vai fazer amanhã em Coimbra, onde fica a Quinta das Lágrimas e qual é a sua história? (`d3/coimbra_expert/dev_planner_check.py`) |
| D3_Q34 | 0.43 | Que tempo está agora em Coimbra e onde fica o Portugal dos Pequenitos? (`task brief (manual tests)`) |
| D3_Q35 | 0.47 | Como vai estar o tempo amanhã em Coimbra, onde fica o Mosteiro de Santa Clara-a-Velha e explica-me brevemente a sua história. (`task brief (manual tests)`) |

Questions at or above 0.75: **0**. The highest values come from shared sentence templates ('Qual é a distância entre…', 'Onde fica…', 'Está … neste momento em …') with different entities and needs, not from reused questions. During construction one item reached 0.77 against the unit-test question 'O que é a Sé Velha de Coimbra?' only through the template 'O que é a … de Coimbra?'; it was reworded (D3_Q04) to remove the overlap.

**Semantic exclusions (beyond literal reuse):**

- Planner few-shot entities and needs (Lisboa, Torre de Belém, Mosteiro dos Jerónimos, Porto, Palácio da Bolsa, 'sol no sábado em Coimbra', 'frio agora no Porto') are absent.
- Smoke/manual entities Sé Velha, Jardim da Sereia, Jardim Botânico (as Places target), Portugal dos Pequenitos, Sé Nova, Biblioteca Joanina, Mosteiro de Santa Clara-a-Velha, Pastéis de Santa Clara, Museu Nacional (Machado de Castro) and Penedo da Saudade are not question targets.
- Dev-set needs not reused: doces conventuais (in general), Inês de Castro, Queima das Fitas, capa e batina, Museu da Ciência, Convento de Santa Clara-a-Nova, Quinta das Lágrimas, Mosteiro de Santa Cruz (location), Estádio Cidade de Coimbra, Coimbra-B, Aveiro, Évora, Guimarães.
- D2 V2 factual needs not reused (D. Dinis' Largo, Santo António, Mozarabic centuries, Estação Nova, Joanina middle floor, Faculdade de Letras, Colégio de S. Jerónimo, Imprensa da Universidade, bunho, Jardim da Sereia, Memorial Miguel Torga, fado and the cape, Pastéis de Santa Clara, Barrigas de Freira, Manjar Branco, beer tradition, Ceira, Ínsua dos Bentos, Jardim Botânico creation, Regata da Queima).
- The smoke-test need 'current air temperature in Coimbra' is not a stand-alone question; D3_Q06 asks for the apparent temperature (a different output field), and current temperature only appears as one part of the three-need item D3_Q34.

## 12. Duplicate / Similarity Audit

- Exact duplicates among the 35 questions: **0**.
- Most similar question pairs (difflib ratio on normalised text):

| Pair | Ratio |
|---|---|
| D3_Q02 – D3_Q04 | 0.58 |
| D3_Q26 – D3_Q30 | 0.52 |
| D3_Q04 – D3_Q07 | 0.51 |
| D3_Q06 – D3_Q07 | 0.50 |
| D3_Q06 – D3_Q08 | 0.50 |
| D3_Q04 – D3_Q15 | 0.49 |
| D3_Q12 – D3_Q15 | 0.48 |
| D3_Q29 – D3_Q32 | 0.48 |

All pairs are at or below 0.58; the highest are short single-need questions that share function words only. A manual review of the needs found no near-duplicates: every RAG question has its own gold chunks (0 shared gold chunks), no Places entity is used twice, and the Weather questions differ in variable (apparent temperature, sky, wind, temperature, rain, general conditions) and/or time window. Repeated weather windows (e.g. 'tomorrow') are intentional: weather values are dynamic, so the same window does not test the same fact.

Near-duplicates removed during construction: a candidate on the Via Latina (Paço das Escolas) was dropped because it came from the same Paço das Escolas passages as D3_Q01/D3_Q20; a 'Onde ficava a judiaria…' wording was rewritten (D3_Q05) because it would have created an ambiguous Places need; and D3_Q04 was reworded to remove a template overlap with a unit-test question.

## 13. Known Exclusions

- **Smoke / dev / manual / prompt / unit-test / README questions were excluded** (Section 11): none of the 35 questions appears in, or is a reformulation of, those sets.
- **Museu Nacional de Machado de Castro was avoided in the main benchmark** because of the Nominatim entity-resolution instability already observed ('Museu Nacional de Machado de Castro, Coimbra' does not resolve on public Nominatim while 'Museu Nacional, Coimbra' does). It is not a Places target and not a RAG subject.
- **Ambiguous broad place names were avoided where they could contaminate the main metric:** no 'Universidade de Coimbra' as a Places target (the Departamento de Matemática building is used instead in D3_Q35), no bare city names as distance endpoints, and names that exist in other cities (Praça do Comércio, Praça da República) are always asked in an explicit Coimbra context.
- **Nominatim was not called** to validate any place; the choice of names relied on documented issues, canonical names and the corpus. Real resolution will be measured in the execution phase.
- **Corpus conflicts avoided as gold:** current use of the Torre de Anto, Seminário Maior vs. Colégio de Jesus, date/identity of the Mosteiro/Convento de São Francisco.
- **Volatile corpus content avoided:** restaurant/bar listings, market schedules, opening days.

## 14. Integrity Hashes

SHA-256 of the dataset artefacts at audit time:

| File | SHA-256 |
|---|---|
| `d3/evaluation/D3_EVALUATION_SET_V1.md` | `d15356000ee620fe6341396d7699653638a34685411f8ab0df37f5e7710f1f01` |
| `d3/evaluation/d3_evaluation_set_v1.json` | `3cef162c592e3e18c18103a970b926f949dc9e1115f971bfea3c5595674e0528` |

The hash of this audit file cannot be embedded in itself; the hashes of all three files are recorded in `d3/evaluation/D3_EVALUATION_SET_V1.sha256` (standard `sha256sum` format; verify with `sha256sum -c D3_EVALUATION_SET_V1.sha256` inside `d3/evaluation/`).

RAG source of truth referenced by the gold:

| File | SHA-256 |
|---|---|
| `d2_rag/data/chunks/chunks.jsonl` | `011dcbcd8f533511013c77b8e6d36abe387d4f4fa27837bd6d27d454a9017213` |
| `d2_rag/data/manifest.jsonl` | `3d0e4ea5dd6927fe6a1c8d202dd6409096f460dbb95142df48651b1f81013c68` |

V1 is ready to be frozen but is not declared irreversibly final; any change after execution must produce a new version and new hashes.

## 15. Final Validation

Per-question checks (A question uniqueness · B category correct · C gold capabilities unambiguous · D expected tools correct · E RAG answerability · F every Essential Fact has direct evidence · G gold chunks contain evidence · H no external knowledge required · I no volatile factual answer frozen · J not reused from smoke/dev/manual/prompt · K natural PT-PT wording · L no system terminology). 'n/a' = the check does not apply (no RAG).

| ID | A | B | C | D | E | F | G | H | I | J | K | L |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D3_Q01 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q02 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q03 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q04 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q05 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q06 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q07 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q08 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q09 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q10 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q11 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q12 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q13 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q14 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q15 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q16 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q17 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q18 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q19 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q20 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q21 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q22 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q23 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q24 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q25 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q26 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q27 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q28 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q29 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q30 | PASS | PASS | PASS | PASS | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| D3_Q31 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q32 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q33 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q34 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| D3_Q35 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

A–D, F, G, I, J and L are automated checks (Sections 3–12). E and H are automated at the evidence level (every fact has a verbatim excerpt from an indexed chunk) and were confirmed by manual review. K was assessed by manual review of all 35 questions (PT-PT usage such as 'está a fazer', 'apetece-me', 'os miúdos', 'vale a pena', clitic placement).

| Check | Result |
|---|---|
| D3 evaluation questions | 35 / 35 |
| All 7 capability combinations balanced | YES |
| RAG required in exactly 20 questions | YES |
| Weather required in exactly 20 questions | YES |
| Places required in exactly 20 questions | YES |
| Weather tools current / forecast | 10 / 10 |
| Places tools search / distance | 10 / 10 |
| Difficulty easy / medium / hard | 11 / 14 / 10 |
| Essential Facts (direct / total) | 58 / 58 |
| Essential Facts requiring inference | 0 |
| Gold chunks / distinct RAG documents | 35 / 18 |
| Structural errors | 0 |
| Literal leakage matches | 0 |
| Near-reuse flags (≥ 0.75) | 0 |
| Exact duplicates | 0 |
| System terminology in questions | 0 |
| Any evaluation question executed | NO |
| Planner / LLM / MCP / retrieval called | NO |

**EVALUATION DATASET READY TO FREEZE: YES**

