# D3 Evaluation Set V1

Human-readable view of `d3_evaluation_set_v1.json` (the JSON is the machine source used by the evaluation scripts).

- **Created:** 2026-10-06
- **Status:** prepared for freezing — **no question has been executed** against the planner, RAG, MCP servers or any LLM.
- **Language:** Português de Portugal
- **Questions:** 35 (7 capability combinations × 5)
- **RAG source of truth:** `d2_rag/data/chunks/chunks.jsonl` (sha256 `011dcbcd8f533511…`, 35 documents, 348 indexed content chunks; FROZEN_V2, top-k = 3).
- **Gold chunks** were selected by reading the frozen chunks, never from retrieval output.
- **Weather / Places:** only tools and semantic requirements are annotated. No temperatures, precipitation, coordinates or distances are frozen; the real values will be captured at execution time and the final answers judged against them.
- **Forecast-day convention:** today = day 1 (tomorrow ⇒ ≥ 2 days, day after tomorrow ⇒ ≥ 3 days).

## Layout

| IDs | Category | Gold capabilities |
|---|---|---|
| D3_Q01–D3_Q05 | RAG | RAG |
| D3_Q06–D3_Q10 | WEATHER | Weather |
| D3_Q11–D3_Q15 | PLACES | Places |
| D3_Q16–D3_Q20 | RAG+WEATHER | RAG + Weather |
| D3_Q21–D3_Q25 | RAG+PLACES | RAG + Places |
| D3_Q26–D3_Q30 | WEATHER+PLACES | Weather + Places |
| D3_Q31–D3_Q35 | RAG+WEATHER+PLACES | RAG + Weather + Places |

## Question index

| ID | Category | Difficulty | Weather tool | Places tool | Question |
|---|---|---|---|---|---|
| D3_Q01 | RAG | easy | — | — | Quantos sinos tem a torre da Universidade de Coimbra, como se chamam e de que anos são? |
| D3_Q02 | RAG | easy | — | — | Que dois estilos de louça tradicional existem em Coimbra e em que se distinguem? |
| D3_Q03 | RAG | easy | — | — | Quem foi D. Sesnando e que papel teve na reconquista de Coimbra? |
| D3_Q04 | RAG | easy | — | — | Que tipo de doce é a arrufada de Coimbra e a que sabe? |
| D3_Q05 | RAG | hard | — | — | Como era a Judiaria Velha de Coimbra na Idade Média e que vestígios dessa comunidade ainda se conhecem? |
| D3_Q06 | WEATHER | easy | get_current_weather | — | Qual é a sensação térmica neste momento em Coimbra? |
| D3_Q07 | WEATHER | easy | get_current_weather | — | O céu está limpo ou nublado agora em Coimbra? |
| D3_Q08 | WEATHER | easy | get_current_weather | — | Está muito vento neste momento na Figueira da Foz? |
| D3_Q09 | WEATHER | medium | get_weather_forecast | — | Vou passar os próximos quatro dias em Coimbra. Vale a pena levar guarda-chuva? |
| D3_Q10 | WEATHER | hard | get_weather_forecast | — | Em Coimbra, depois de amanhã vai estar mais calor ou mais fresco do que amanhã? |
| D3_Q11 | PLACES | easy | — | search_place | Onde fica a Casa-Museu Bissaya Barreto? |
| D3_Q12 | PLACES | easy | — | get_distance_between_places | Qual é a distância entre o Mosteiro de Celas e a Igreja de Santo António dos Olivais? |
| D3_Q13 | PLACES | easy | — | search_place | Preciso da localização exata da Casa da Escrita, em Coimbra. |
| D3_Q14 | PLACES | medium | — | get_distance_between_places | A Mata Nacional do Choupal fica muito longe do Parque Dr. Manuel Braga? |
| D3_Q15 | PLACES | easy | — | get_distance_between_places | Que distância separa o Seminário Maior de Coimbra da Praça da Canção? |
| D3_Q16 | RAG+WEATHER | medium | get_weather_forecast | — | Qual é a temperatura máxima prevista para amanhã em Coimbra? E que produtos do rio Mondego marcam a gastronomia tradicional coimbrã? |
| D3_Q17 | RAG+WEATHER | medium | get_current_weather | — | Como está o tempo neste momento em Coimbra? E em que é que a guitarra de Coimbra difere da guitarra de Lisboa? |
| D3_Q18 | RAG+WEATHER | medium | get_weather_forecast | — | Chego a Coimbra depois de amanhã: que tempo se prevê para esse dia? E o que conta a lenda do Milagre das Rosas da Rainha Santa Isabel? |
| D3_Q19 | RAG+WEATHER | hard | get_current_weather | — | Apetece-me ir correr junto ao Mondego: dá para correr com o tempo que está agora em Coimbra? E que corrida de fim de ano é uma das provas mais emblemáticas da cidade? |
| D3_Q20 | RAG+WEATHER | medium | get_weather_forecast | — | Vou visitar o Paço das Escolas num dos próximos cinco dias. Há previsão de chuva em Coimbra nesse período? E para que servia a Sala dos Capelos? |
| D3_Q21 | RAG+PLACES | medium | — | search_place | Onde fica o Aqueduto de São Sebastião e quem o mandou construir e para quê? |
| D3_Q22 | RAG+PLACES | medium | — | search_place | Onde fica o Palácio de Sub-Ripas e como surgiu este edifício? |
| D3_Q23 | RAG+PLACES | medium | — | get_distance_between_places | Qual é a distância entre o Largo da Portagem e o Jardim da Manga? E de onde vem o nome deste jardim e quem participou no seu desenho? |
| D3_Q24 | RAG+PLACES | hard | — | search_place | Onde ficam as ruínas de Conímbriga e porque é que muitos dos seus habitantes se mudaram para Æminium? |
| D3_Q25 | RAG+PLACES | medium | — | get_distance_between_places | A que distância fica a Casa-Museu Miguel Torga da Praça da República, em Coimbra? E quem projetou a casa e quando abriu ao público? |
| D3_Q26 | WEATHER+PLACES | medium | get_current_weather | search_place | Vou agora ao Pátio da Inquisição, em Coimbra. Onde fica exatamente e que tempo está a fazer neste momento na cidade? |
| D3_Q27 | WEATHER+PLACES | medium | get_current_weather | get_distance_between_places | Tenho treino no Estádio Universitário de Coimbra. A que distância fica do Museu da Água, e está a fazer vento agora em Coimbra? |
| D3_Q28 | WEATHER+PLACES | medium | get_weather_forecast | get_distance_between_places | Amanhã quero caminhar na Mata Nacional de Vale de Canas. Que tempo se espera amanhã em Coimbra e a que distância fica a mata da Praça do Comércio? |
| D3_Q29 | WEATHER+PLACES | medium | get_weather_forecast | get_distance_between_places | Como vai estar o tempo em Coimbra nos próximos três dias, e que distância há entre o Convento São Francisco e a Ponte Pedonal Pedro e Inês? |
| D3_Q30 | WEATHER+PLACES | hard | get_current_weather | search_place | Queria levar os miúdos ao Exploratório – Centro Ciência Viva de Coimbra. Onde fica, e o tempo agora está bom para estar ao ar livre? |
| D3_Q31 | RAG+WEATHER+PLACES | hard | get_weather_forecast | search_place | Amanhã quero visitar a Torre de Almedina. Vai estar bom tempo em Coimbra? Gostava também de saber onde fica a torre e que funções teve ao longo dos séculos. |
| D3_Q32 | RAG+WEATHER+PLACES | hard | get_current_weather | get_distance_between_places | Como estão as condições do tempo agora em Coimbra? Quero passar pela Torre de Anto e depois pela Ponte de Santa Clara: que distância há entre as duas, e porque é que a torre se chama assim? |
| D3_Q33 | RAG+WEATHER+PLACES | hard | get_weather_forecast | search_place | Estou a pensar ir a Almalaguês depois de amanhã para conhecer as tecedeiras. Como vai estar o tempo em Coimbra nesse dia, onde fica Almalaguês e o que caracteriza a sua tecelagem? |
| D3_Q34 | RAG+WEATHER+PLACES | hard | get_current_weather | get_distance_between_places | Vou ao Café Santa Cruz. Quantos graus estão agora em Coimbra, a que distância fica o café do Mercado Municipal D. Pedro V, e que doce conventual é associado a esse café e como é feito? |
| D3_Q35 | RAG+WEATHER+PLACES | hard | get_weather_forecast | search_place | Vou estar uma semana em Coimbra. Como vai estar o tempo nos próximos sete dias, onde fica o Departamento de Matemática da Universidade de Coimbra e porque é que a inauguração desse edifício ficou na história? |

## RAG (Q01–Q05)

### D3_Q01 — Quantos sinos tem a torre da Universidade de Coimbra, como se chamam e de que anos são?

**Category:** RAG  
**Difficulty:** easy

**Gold Capabilities:**

- RAG: YES
- Weather: NO
- Places: NO

**Expected Weather Tool:** null  
**Expected Places Tool:** null

**RAG Information Need:** sinos da Torre da Universidade de Coimbra: número, nomes e datas

**Essential Facts:**

- **F1** — A torre tem quatro sinos que regem a vida académica.
- **F2** — Um dos sinos é a "cabra", de 1741.
- **F3** — Outro sino é o "cabrão", de 1824.
- **F4** — Outro sino é o "bolão", de 1561.
- **F5** — O quarto sino é o dos "quartos" (o corpus não indica a sua data).

**Gold Evidence:**

- Gold documents: `viver-o-patrimonio-em-coimbra`, `fado-e-tradicoes-academicas`, `universidade-alta-sofia-patrimonio-mundial`
- Gold chunks: `viver-o-patrimonio-em-coimbra::c0003`, `fado-e-tradicoes-academicas::c0006`, `universidade-alta-sofia-patrimonio-mundial::c0013`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `viver-o-patrimonio-em-coimbra` | 1. PAÇO DAS ESCOLAS | `viver-o-patrimonio-em-coimbra::c0003` | F1, F2, F3, F4, F5 | “seguidos de quatro sinos que regem a vida académica: a “cabra” de 1741, o “cabrão” de 1824, o “bolão” de 1561 e o dos “quartos”.” |
| `fado-e-tradicoes-academicas` | 2. PAÇO DAS ESCOLAS | `fado-e-tradicoes-academicas::c0006` | F1, F2, F3, F4, F5 | “seguidos de quatro sinos que regem a vida académica: a “cabra” de 1741, o “cabrão” de 1824, o “bolão” de 1561 e o dos “quartos”.” |
| `universidade-alta-sofia-patrimonio-mundial` | 1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS > TORRE | `universidade-alta-sofia-patrimonio-mundial::c0013` | F1, F2, F3, F4, F5 | “seguidos de quatro sinos que regem a vida académica: a “cabra” de 1741, o “cabrão” de 1824, o “bolão” de 1561 e o dos “quartos”.” |

**Weather Requirement:**

- not applicable

**Places Requirement:**

- not applicable

**Notes:** The same passage appears verbatim in three documents; all three chunks are gold. The corpus gives no date for the "quartos" bell; an answer must not invent one.

### D3_Q02 — Que dois estilos de louça tradicional existem em Coimbra e em que se distinguem?

**Category:** RAG  
**Difficulty:** easy

**Gold Capabilities:**

- RAG: YES
- Weather: NO
- Places: NO

**Expected Weather Tool:** null  
**Expected Places Tool:** null

**RAG Information Need:** as duas vertentes da louça de Coimbra e as suas diferenças

**Essential Facts:**

- **F1** — A louça de Coimbra tem duas vertentes principais: a "louça ratinha" e a de "desenho miúdo".
- **F2** — A louça ratinha caracteriza-se pela simplicidade da decoração, com pinceladas rápidas que formam padrões geométricos ou naturais.
- **F3** — A louça de desenho miúdo é mais sofisticada, inspira-se na louça das Índias e tem motivos densos e detalhados.
- **F4** — Na louça de desenho miúdo predominam o azul e o branco.

**Gold Evidence:**

- Gold documents: `web-visitecoimbra-ceramica-de-coimbra`
- Gold chunks: `web-visitecoimbra-ceramica-de-coimbra::c0001`, `web-visitecoimbra-ceramica-de-coimbra::c0002`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `web-visitecoimbra-ceramica-de-coimbra` | (document introduction / no section heading) | `web-visitecoimbra-ceramica-de-coimbra::c0001` | F1 | “destacando-se em duas vertentes principais: a “louça ratinha” e a de “desenho miúdo”.” |
| `web-visitecoimbra-ceramica-de-coimbra` | (document introduction / no section heading) | `web-visitecoimbra-ceramica-de-coimbra::c0001` | F2 | “A “louça ratinha” caracteriza-se pela simplicidade das suas decorações, com pinceladas rápidas que formam padrões geométricos ou naturais.” |
| `web-visitecoimbra-ceramica-de-coimbra` | (document introduction / no section heading) | `web-visitecoimbra-ceramica-de-coimbra::c0002` | F3 | “a louça de “desenho miúdo” apresenta uma maior sofisticação, inspirando-se na luxuosa louça das Índias. As peças deste estilo exibem motivos densos e detalhados” |
| `web-visitecoimbra-ceramica-de-coimbra` | (document introduction / no section heading) | `web-visitecoimbra-ceramica-de-coimbra::c0002` | F4 | “As cores predominantes, o azul e o branco” |

**Weather Requirement:**

- not applicable

**Places Requirement:**

- not applicable

**Notes:** —

### D3_Q03 — Quem foi D. Sesnando e que papel teve na reconquista de Coimbra?

**Category:** RAG  
**Difficulty:** easy

**Gold Capabilities:**

- RAG: YES
- Weather: NO
- Places: NO

**Expected Weather Tool:** null  
**Expected Places Tool:** null

**RAG Information Need:** identidade de D. Sesnando e o seu papel na reconquista e governo de Coimbra

**Essential Facts:**

- **F1** — D. Sesnando foi um líder moçárabe (cristão que vivia sob domínio islâmico) do século XI.
- **F2** — Foi escolhido por Fernando Magno, rei de Leão e Castela, para um papel estratégico na Reconquista.
- **F3** — Foi essencial na reconquista de Coimbra, em 1064.
- **F4** — Durante o seu governo promoveu a reconstrução e o desenvolvimento de Coimbra.

**Gold Evidence:**

- Gold documents: `web-visitecoimbra-sesnando-david`
- Gold chunks: `web-visitecoimbra-sesnando-david::c0001`, `web-visitecoimbra-sesnando-david::c0002`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `web-visitecoimbra-sesnando-david` | (document introduction / no section heading) | `web-visitecoimbra-sesnando-david::c0001` | F1, F2 | “uma figura marcante do século XI, foi um líder moçárabe – cristão que vivia sob domínio islâmico – escolhido por Fernando Magno, rei de Leão e Castela, para desempenhar um papel estratégico na Reconquista.” |
| `web-visitecoimbra-sesnando-david` | (document introduction / no section heading) | `web-visitecoimbra-sesnando-david::c0001` | F3 | “Sesnando tornou-se essencial na reconquista de Coimbra em 1064” |
| `web-visitecoimbra-sesnando-david` | (document introduction / no section heading) | `web-visitecoimbra-sesnando-david::c0002` | F4 | “Durante o seu governo, Sesnando demonstrou ser um administrador brilhante, promovendo a reconstrução e o desenvolvimento de Coimbra.” |

**Weather Requirement:**

- not applicable

**Places Requirement:**

- not applicable

**Notes:** Distinct from the D2 V2 question on Mozarabic heritage (centuries of Moorish rule / churches).

### D3_Q04 — Que tipo de doce é a arrufada de Coimbra e a que sabe?

**Category:** RAG  
**Difficulty:** easy

**Gold Capabilities:**

- RAG: YES
- Weather: NO
- Places: NO

**Expected Weather Tool:** null  
**Expected Places Tool:** null

**RAG Information Need:** descrição da Arrufada de Coimbra

**Essential Facts:**

- **F1** — A arrufada é um pão doce tradicional de Coimbra.
- **F2** — Tem formato arredondado e massa fofa, levemente adocicada.
- **F3** — É aromatizada com canela e erva-doce.
- **F4** — Está ligada à doçaria conventual e era presença obrigatória em festas e celebrações.

**Gold Evidence:**

- Gold documents: `web-visitecoimbra-docaria-conventual-de-coimbra`
- Gold chunks: `web-visitecoimbra-docaria-conventual-de-coimbra::c0004`, `web-visitecoimbra-docaria-conventual-de-coimbra::c0002`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `web-visitecoimbra-docaria-conventual-de-coimbra` | Doces a não perder > Arrufada de Coimbra | `web-visitecoimbra-docaria-conventual-de-coimbra::c0004` | F1, F2, F3 | “A Arrufada de Coimbra é um pão doce tradicional, de formato arredondado e massa fofa, levemente adocicada, aromatizada com canela e erva-doce.” |
| `web-visitecoimbra-docaria-conventual-de-coimbra` | Doces a não perder > Arrufada de Coimbra | `web-visitecoimbra-docaria-conventual-de-coimbra::c0004` | F4 | “Ligada à doçaria conventual, era presença obrigatória em festas e celebrações” |
| `web-visitecoimbra-docaria-conventual-de-coimbra` | (document introduction / no section heading) | `web-visitecoimbra-docaria-conventual-de-coimbra::c0002` | F1 | “Outras especialidades incluem as arrufadas, pães doces e fofos” |

**Weather Requirement:**

- not applicable

**Places Requirement:**

- not applicable

**Notes:** Not one of the sweets used in D2 V2 (Pastéis de Santa Clara, Barrigas de Freira, Manjar Branco) nor the dev-set question on conventual sweets in general.

### D3_Q05 — Como era a Judiaria Velha de Coimbra na Idade Média e que vestígios dessa comunidade ainda se conhecem?

**Category:** RAG  
**Difficulty:** hard

**Gold Capabilities:**

- RAG: YES
- Weather: NO
- Places: NO

**Expected Weather Tool:** null  
**Expected Places Tool:** null

**RAG Information Need:** caracterização da Judiaria Velha medieval e vestígios materiais da comunidade judaica

**Essential Facts:**

- **F1** — A Judiaria Velha era um espaço vibrante, com sinagoga, escolas, mercados e vida comercial ativa.
- **F2** — O bairro tinha estruturas como o Mikveh (banhos rituais de purificação) e o Almocávar (cemitério judaico).
- **F3** — A herança judaica ainda é visível em vestígios materiais, como o Mikveh recentemente identificado.

**Gold Evidence:**

- Gold documents: `web-visitecoimbra-heranca-judaica`
- Gold chunks: `web-visitecoimbra-heranca-judaica::c0001`, `web-visitecoimbra-heranca-judaica::c0002`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `web-visitecoimbra-heranca-judaica` | (document introduction / no section heading) | `web-visitecoimbra-heranca-judaica::c0001` | F1 | “era um espaço vibrante, com sinagoga, escolas, mercados e uma vida comercial ativa.” |
| `web-visitecoimbra-heranca-judaica` | (document introduction / no section heading) | `web-visitecoimbra-heranca-judaica::c0001` | F2 | “Este bairro destacava-se ainda pela existência de estruturas como o Mikveh (banhos rituais de purificação) e o Almocávar (cemitério judaico).” |
| `web-visitecoimbra-heranca-judaica` | (document introduction / no section heading) | `web-visitecoimbra-heranca-judaica::c0002` | F3 | “a herança judaica de Coimbra ainda é visível em vestígios materiais, como o recentemente identificado Mikveh” |

**Weather Requirement:**

- not applicable

**Places Requirement:**

- not applicable

**Notes:** Worded without "onde ficava" so that the gold plan has no geographic (Places) need; the street location in the corpus is optional context, not an Essential Fact.

## WEATHER (Q06–Q10)

### D3_Q06 — Qual é a sensação térmica neste momento em Coimbra?

**Category:** WEATHER  
**Difficulty:** easy

**Gold Capabilities:**

- RAG: NO
- Weather: YES
- Places: NO

**Expected Weather Tool:** get_current_weather  
**Expected Places Tool:** null

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- Tool: `get_current_weather`
- Location: Coimbra, Portugal
- Temporal: current
- Minimum forecast days: n/a (current conditions)
- Answer must: report the current apparent temperature (sensação térmica) in Coimbra, in °C, as returned by the tool

**Places Requirement:**

- not applicable

**Notes:** Asks for apparent temperature (a field of the current-weather output), not the air temperature asked in the smoke test.

### D3_Q07 — O céu está limpo ou nublado agora em Coimbra?

**Category:** WEATHER  
**Difficulty:** easy

**Gold Capabilities:**

- RAG: NO
- Weather: YES
- Places: NO

**Expected Weather Tool:** get_current_weather  
**Expected Places Tool:** null

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- Tool: `get_current_weather`
- Location: Coimbra, Portugal
- Temporal: current
- Minimum forecast days: n/a (current conditions)
- Answer must: state whether the sky in Coimbra is currently clear or cloudy, based on the returned cloud cover and/or weather description

**Places Requirement:**

- not applicable

**Notes:** —

### D3_Q08 — Está muito vento neste momento na Figueira da Foz?

**Category:** WEATHER  
**Difficulty:** easy

**Gold Capabilities:**

- RAG: NO
- Weather: YES
- Places: NO

**Expected Weather Tool:** get_current_weather  
**Expected Places Tool:** null

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- Tool: `get_current_weather`
- Location: Figueira da Foz, Portugal
- Temporal: current
- Minimum forecast days: n/a (current conditions)
- Answer must: report the current wind speed in Figueira da Foz (km/h) as returned by the tool
- Answer must: state whether that wind is strong, without contradicting the returned value

**Places Requirement:**

- not applicable

**Notes:** The only non-Coimbra weather need in the benchmark (Figueira da Foz, the coastal city at the Mondego estuary); tests location generality.

### D3_Q09 — Vou passar os próximos quatro dias em Coimbra. Vale a pena levar guarda-chuva?

**Category:** WEATHER  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: NO
- Weather: YES
- Places: NO

**Expected Weather Tool:** get_weather_forecast  
**Expected Places Tool:** null

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- Tool: `get_weather_forecast`
- Location: Coimbra, Portugal
- Temporal: next 4 days (today + 3)
- Minimum forecast days: 4
- Answer must: state whether precipitation is expected in Coimbra on any of the next four days, based on the returned precipitation amounts/probabilities
- Answer must: give a recommendation about the umbrella consistent with the returned forecast

**Places Requirement:**

- not applicable

**Notes:** Implicit weather intent (umbrella) rather than an explicit 'vai chover'.

### D3_Q10 — Em Coimbra, depois de amanhã vai estar mais calor ou mais fresco do que amanhã?

**Category:** WEATHER  
**Difficulty:** hard

**Gold Capabilities:**

- RAG: NO
- Weather: YES
- Places: NO

**Expected Weather Tool:** get_weather_forecast  
**Expected Places Tool:** null

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- Tool: `get_weather_forecast`
- Location: Coimbra, Portugal
- Temporal: tomorrow and the day after tomorrow (comparison)
- Minimum forecast days: 3
- Answer must: report the forecast temperatures for tomorrow and for the day after tomorrow in Coimbra
- Answer must: state which of the two days is warmer/cooler, consistent with the returned values

**Places Requirement:**

- not applicable

**Notes:** Requires a forecast covering at least 3 days (today, tomorrow, day after tomorrow) and a comparison between two forecast days.

## PLACES (Q11–Q15)

### D3_Q11 — Onde fica a Casa-Museu Bissaya Barreto?

**Category:** PLACES  
**Difficulty:** easy

**Gold Capabilities:**

- RAG: NO
- Weather: NO
- Places: YES

**Expected Weather Tool:** null  
**Expected Places Tool:** search_place

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- not applicable

**Places Requirement:**

- Tool: `search_place`
- Place: Casa-Museu Bissaya Barreto — city: Coimbra — country_code: pt
- Answer must: identify the location returned for Casa-Museu Bissaya Barreto (resolved name/address or coordinates as returned by the tool)

**Notes:** —

### D3_Q12 — Qual é a distância entre o Mosteiro de Celas e a Igreja de Santo António dos Olivais?

**Category:** PLACES  
**Difficulty:** easy

**Gold Capabilities:**

- RAG: NO
- Weather: NO
- Places: YES

**Expected Weather Tool:** null  
**Expected Places Tool:** get_distance_between_places

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- not applicable

**Places Requirement:**

- Tool: `get_distance_between_places`
- Origin: Mosteiro de Celas — city: Coimbra — country_code: pt
- Destination: Igreja de Santo António dos Olivais — city: Coimbra — country_code: pt
- Answer must: report the distance between the two places as returned by the tool, presented as a straight-line (geodesic) distance, never as a walking/driving route or travel time

**Notes:** —

### D3_Q13 — Preciso da localização exata da Casa da Escrita, em Coimbra.

**Category:** PLACES  
**Difficulty:** easy

**Gold Capabilities:**

- RAG: NO
- Weather: NO
- Places: YES

**Expected Weather Tool:** null  
**Expected Places Tool:** search_place

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- not applicable

**Places Requirement:**

- Tool: `search_place`
- Place: Casa da Escrita — city: Coimbra — country_code: pt
- Answer must: identify the location returned for Casa da Escrita (resolved name/address or coordinates as returned by the tool)

**Notes:** Imperative form (no question mark) - still a plain location request.

### D3_Q14 — A Mata Nacional do Choupal fica muito longe do Parque Dr. Manuel Braga?

**Category:** PLACES  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: NO
- Weather: NO
- Places: YES

**Expected Weather Tool:** null  
**Expected Places Tool:** get_distance_between_places

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- not applicable

**Places Requirement:**

- Tool: `get_distance_between_places`
- Origin: Mata Nacional do Choupal — city: Coimbra — country_code: pt
- Destination: Parque Dr. Manuel Braga — city: Coimbra — country_code: pt
- Answer must: report the distance between the two places as returned by the tool, presented as a straight-line (geodesic) distance, never as a walking/driving route or travel time
- Answer must: answer the 'muito longe?' framing using the returned distance, without inventing travel times

**Notes:** Indirect distance request ('fica muito longe?').

### D3_Q15 — Que distância separa o Seminário Maior de Coimbra da Praça da Canção?

**Category:** PLACES  
**Difficulty:** easy

**Gold Capabilities:**

- RAG: NO
- Weather: NO
- Places: YES

**Expected Weather Tool:** null  
**Expected Places Tool:** get_distance_between_places

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- not applicable

**Places Requirement:**

- Tool: `get_distance_between_places`
- Origin: Seminário Maior de Coimbra — city: Coimbra — country_code: pt
- Destination: Praça da Canção — city: Coimbra — country_code: pt
- Answer must: report the distance between the two places as returned by the tool, presented as a straight-line (geodesic) distance, never as a walking/driving route or travel time

**Notes:** —

## RAG+WEATHER (Q16–Q20)

### D3_Q16 — Qual é a temperatura máxima prevista para amanhã em Coimbra? E que produtos do rio Mondego marcam a gastronomia tradicional coimbrã?

**Category:** RAG+WEATHER  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: YES
- Weather: YES
- Places: NO

**Expected Weather Tool:** get_weather_forecast  
**Expected Places Tool:** null

**RAG Information Need:** influência do rio Mondego na gastronomia tradicional de Coimbra

**Essential Facts:**

- **F1** — A lampreia e a enguia do rio Mondego são protagonistas em pratos tradicionais.
- **F2** — Um exemplo é o famoso arroz de lampreia.

**Gold Evidence:**

- Gold documents: `web-visitecoimbra-gastronomia-em-coimbra`
- Gold chunks: `web-visitecoimbra-gastronomia-em-coimbra::c0001`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `web-visitecoimbra-gastronomia-em-coimbra` | (document introduction / no section heading) | `web-visitecoimbra-gastronomia-em-coimbra::c0001` | F1, F2 | “A influência do rio Mondego é marcante, com a lampreia e a enguia a serem protagonistas em pratos tradicionais, como o famoso arroz de lampreia.” |

**Weather Requirement:**

- Tool: `get_weather_forecast`
- Location: Coimbra, Portugal
- Temporal: tomorrow
- Minimum forecast days: 2
- Answer must: report the forecast maximum temperature for tomorrow in Coimbra, as returned by the tool

**Places Requirement:**

- not applicable

**Notes:** —

### D3_Q17 — Como está o tempo neste momento em Coimbra? E em que é que a guitarra de Coimbra difere da guitarra de Lisboa?

**Category:** RAG+WEATHER  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: YES
- Weather: YES
- Places: NO

**Expected Weather Tool:** get_current_weather  
**Expected Places Tool:** null

**RAG Information Need:** diferenças entre a guitarra de Coimbra e a guitarra de Lisboa

**Essential Facts:**

- **F1** — A guitarra de Coimbra tem uma caixa maior do que a de Lisboa.
- **F2** — É afinada num tom abaixo.
- **F3** — A sua voluta tem a forma de lágrima.

**Gold Evidence:**

- Gold documents: `web-visitecoimbra-cancao-de-coimbra`
- Gold chunks: `web-visitecoimbra-cancao-de-coimbra::c0002`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `web-visitecoimbra-cancao-de-coimbra` | (document introduction / no section heading) | `web-visitecoimbra-cancao-de-coimbra::c0002` | F1, F2, F3 | “Diferente da guitarra de Lisboa, possui uma caixa maior, é afinada num tom abaixo e a sua voluta apresenta a forma de lágrima” |

**Weather Requirement:**

- Tool: `get_current_weather`
- Location: Coimbra, Portugal
- Temporal: current
- Minimum forecast days: n/a (current conditions)
- Answer must: describe the current weather conditions in Coimbra (e.g. temperature, precipitation, weather description) as returned by the tool

**Places Requirement:**

- not applicable

**Notes:** —

### D3_Q18 — Chego a Coimbra depois de amanhã: que tempo se prevê para esse dia? E o que conta a lenda do Milagre das Rosas da Rainha Santa Isabel?

**Category:** RAG+WEATHER  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: YES
- Weather: YES
- Places: NO

**Expected Weather Tool:** get_weather_forecast  
**Expected Places Tool:** null

**RAG Information Need:** a lenda do Milagre das Rosas

**Essential Facts:**

- **F1** — Segundo a lenda, Isabel saía do palácio com pão escondido no regaço para distribuir aos pobres.
- **F2** — Interpelada pelo rei D. Dinis sobre o que levava, respondeu que eram rosas.
- **F3** — Ao abrir o manto, o pão tinha-se transformado em flores (rosas), mesmo em pleno inverno.

**Gold Evidence:**

- Gold documents: `web-visitecoimbra-rainha-santa-isabel`
- Gold chunks: `web-visitecoimbra-rainha-santa-isabel::c0001`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `web-visitecoimbra-rainha-santa-isabel` | (document introduction / no section heading) | `web-visitecoimbra-rainha-santa-isabel::c0001` | F1 | “Isabel saía do palácio com pão escondido no regaço para distribuir aos pobres.” |
| `web-visitecoimbra-rainha-santa-isabel` | (document introduction / no section heading) | `web-visitecoimbra-rainha-santa-isabel::c0001` | F2 | “Interpelada pelo rei D. Dinis, que a questionava sobre o que carregava, respondeu que eram rosas.” |
| `web-visitecoimbra-rainha-santa-isabel` | (document introduction / no section heading) | `web-visitecoimbra-rainha-santa-isabel::c0001` | F3 | “Ao abrir o manto, o pão transformara-se miraculosamente em flores, mesmo no rigor do inverno” |

**Weather Requirement:**

- Tool: `get_weather_forecast`
- Location: Coimbra, Portugal
- Temporal: day after tomorrow
- Minimum forecast days: 3
- Answer must: describe the forecast for the day after tomorrow in Coimbra (temperatures, precipitation, weather description) as returned by the tool

**Places Requirement:**

- not applicable

**Notes:** Weather need is a single future day (day 3 counting today as day 1).

### D3_Q19 — Apetece-me ir correr junto ao Mondego: dá para correr com o tempo que está agora em Coimbra? E que corrida de fim de ano é uma das provas mais emblemáticas da cidade?

**Category:** RAG+WEATHER  
**Difficulty:** hard

**Gold Capabilities:**

- RAG: YES
- Weather: YES
- Places: NO

**Expected Weather Tool:** get_current_weather  
**Expected Places Tool:** null

**RAG Information Need:** a prova de corrida de fim de ano emblemática de Coimbra (São Silvestre)

**Essential Facts:**

- **F1** — A prova é a São Silvestre de Coimbra, uma das mais emblemáticas do calendário desportivo da cidade.
- **F2** — Realiza-se anualmente no final de dezembro.
- **F3** — Percorre as principais ruas e avenidas de Coimbra, com destaque para os cenários históricos e o rio Mondego.

**Gold Evidence:**

- Gold documents: `web-visitecoimbra-desporto`
- Gold chunks: `web-visitecoimbra-desporto::c0004`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `web-visitecoimbra-desporto` | (document introduction / no section heading) | `web-visitecoimbra-desporto::c0004` | F1 | “a São Silvestre de Coimbra é uma das provas mais emblemáticas do calendário desportivo da cidade” |
| `web-visitecoimbra-desporto` | (document introduction / no section heading) | `web-visitecoimbra-desporto::c0004` | F2, F3 | “Realizada anualmente no final de dezembro, a corrida percorre as principais ruas e avenidas de Coimbra, com destaque para os cenários históricos e o rio Mondego” |

**Weather Requirement:**

- Tool: `get_current_weather`
- Location: Coimbra, Portugal
- Temporal: current
- Minimum forecast days: n/a (current conditions)
- Answer must: describe the current weather conditions in Coimbra as returned by the tool
- Answer must: relate them to the running plan without contradicting the returned values

**Places Requirement:**

- not applicable

**Notes:** Indirect weather intent ('dá para correr com o tempo que está agora'); the RAG need does not name the event.

### D3_Q20 — Vou visitar o Paço das Escolas num dos próximos cinco dias. Há previsão de chuva em Coimbra nesse período? E para que servia a Sala dos Capelos?

**Category:** RAG+WEATHER  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: YES
- Weather: YES
- Places: NO

**Expected Weather Tool:** get_weather_forecast  
**Expected Places Tool:** null

**RAG Information Need:** função histórica da Sala dos Capelos

**Essential Facts:**

- **F1** — A Sala dos Capelos era a antiga sala do trono do Paço Real.
- **F2** — No século XVII foi adaptada para receber os atos mais importantes da vida académica.
- **F3** — Exemplos desses atos: abertura solene do ano letivo, provas doutorais, imposição de insígnias e investidura (tomada de posse) de reitores.

**Gold Evidence:**

- Gold documents: `viver-o-patrimonio-em-coimbra`, `fado-e-tradicoes-academicas`, `universidade-alta-sofia-patrimonio-mundial`
- Gold chunks: `viver-o-patrimonio-em-coimbra::c0002`, `fado-e-tradicoes-academicas::c0005`, `universidade-alta-sofia-patrimonio-mundial::c0009`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `viver-o-patrimonio-em-coimbra` | 1. PAÇO DAS ESCOLAS | `viver-o-patrimonio-em-coimbra::c0002` | F1, F2, F3 | “sala dos capelos - Antiga sala do trono do Paço Real que, no século XVII, é adaptada para receber os mais importantes atos da vida académica: abertura solene do ano letivo, provas doutorais, imposição de insígnias, investidura de reitores, entre outros.” |
| `fado-e-tradicoes-academicas` | 2. PAÇO DAS ESCOLAS | `fado-e-tradicoes-academicas::c0005` | F1, F2, F3 | “sala dos capelos - Antiga sala do trono do Paço Real que, no século XVII, é adaptada para receber os mais importantes atos da vida académica: abertura solene do ano letivo, provas doutorais, imposição de insígnias, investidura de reitores, entre outros.” |
| `universidade-alta-sofia-patrimonio-mundial` | 1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS > SALA DOS CAPELOS | `universidade-alta-sofia-patrimonio-mundial::c0009` | F1, F2, F3 | “Antiga sala do trono, que no século XVII, é adaptada para receber os mais importantes atos da vida académica (abertura solene do ano letivo, provas doutorais, imposição de insígnias, tomada de posse de reitores, entre outros).” |

**Weather Requirement:**

- Tool: `get_weather_forecast`
- Location: Coimbra, Portugal
- Temporal: next 5 days
- Minimum forecast days: 5
- Answer must: state on which of the next five days precipitation is expected in Coimbra (if any), based on the returned precipitation amounts/probabilities

**Places Requirement:**

- not applicable

**Notes:** 'Paço das Escolas' is mentioned as context only; no location is requested.

## RAG+PLACES (Q21–Q25)

### D3_Q21 — Onde fica o Aqueduto de São Sebastião e quem o mandou construir e para quê?

**Category:** RAG+PLACES  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: YES
- Weather: NO
- Places: YES

**Expected Weather Tool:** null  
**Expected Places Tool:** search_place

**RAG Information Need:** quem mandou construir o Aqueduto de São Sebastião e com que finalidade

**Essential Facts:**

- **F1** — O aqueduto foi mandado construir em 1570 pelo rei D. Sebastião.
- **F2** — Destinava-se a abastecer de água a Alta da cidade.

**Gold Evidence:**

- Gold documents: `web-visitecoimbra-heranca-cultural-e-religiosa`
- Gold chunks: `web-visitecoimbra-heranca-cultural-e-religiosa::c0023`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `web-visitecoimbra-heranca-cultural-e-religiosa` | Monumentos e outros edifícios históricos > Aqueduto de São Sebastião | `web-visitecoimbra-heranca-cultural-e-religiosa::c0023` | F1, F2 | “este aqueduto foi mandado construir em 1570 pelo rei D. Sebastião, para abastecer de água a Alta da cidade” |

**Weather Requirement:**

- not applicable

**Places Requirement:**

- Tool: `search_place`
- Place: Aqueduto de São Sebastião (Arcos do Jardim) — city: Coimbra — country_code: pt
- Answer must: identify the location returned for Aqueduto de São Sebastião (resolved name/address or coordinates as returned by the tool)

**Notes:** —

### D3_Q22 — Onde fica o Palácio de Sub-Ripas e como surgiu este edifício?

**Category:** RAG+PLACES  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: YES
- Weather: NO
- Places: YES

**Expected Weather Tool:** null  
**Expected Places Tool:** search_place

**RAG Information Need:** origem do Palácio de Sub-Ripas

**Essential Facts:**

- **F1** — Era uma antiga torre defensiva da muralha da cidade (a Torre da Contenda), adaptada a residência no século XVI.
- **F2** — Foi comprada por João Vaz, que a uniu através de um arco a outros edifícios (Casa de Cima e Casa de Baixo), formando o palácio.

**Gold Evidence:**

- Gold documents: `web-visitecoimbra-heranca-cultural-e-religiosa`, `universidade-alta-sofia-patrimonio-mundial`
- Gold chunks: `web-visitecoimbra-heranca-cultural-e-religiosa::c0024`, `universidade-alta-sofia-patrimonio-mundial::c0049`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `web-visitecoimbra-heranca-cultural-e-religiosa` | Monumentos e outros edifícios históricos > Palácio de Sub-Ripas | `web-visitecoimbra-heranca-cultural-e-religiosa::c0024` | F1 | “A antiga Torre da Contenda, integrada na muralha da cidade, foi adaptada a residência no século XVI e comprada por João Vaz.” |
| `web-visitecoimbra-heranca-cultural-e-religiosa` | Monumentos e outros edifícios históricos > Palácio de Sub-Ripas | `web-visitecoimbra-heranca-cultural-e-religiosa::c0024` | F2 | “Ele uniu-a, através de um arco, à Casa de Cima e à Casa de Baixo, formando o Palácio de Sub-Ribas” |
| `universidade-alta-sofia-patrimonio-mundial` | 22. PALÁCIO SUB-RIBAS | `universidade-alta-sofia-patrimonio-mundial::c0049` | F1 | “Antiga torre defensiva da linha de muralha da cidade, adaptada a residência no século XVI e comprada por João Vaz” |
| `universidade-alta-sofia-patrimonio-mundial` | 22. PALÁCIO SUB-RIBAS | `universidade-alta-sofia-patrimonio-mundial::c0049` | F2 | “acabando por unir, através de um arco passadiço, o que hoje conhecemos como “Casa de Cima” ou “Casa do Arco” e a “Casa de Baixo” ou “Casa da Torre”, o Palácio de Sub-Ribas propriamente dito.” |

**Weather Requirement:**

- not applicable

**Places Requirement:**

- Tool: `search_place`
- Place: Palácio de Sub-Ripas — city: Coimbra — country_code: pt
- Answer must: identify the location returned for Palácio de Sub-Ripas (resolved name/address or coordinates as returned by the tool)

**Notes:** The corpus spells the name both 'Sub-Ripas' and 'Sub-Ribas'; both are acceptable.

### D3_Q23 — Qual é a distância entre o Largo da Portagem e o Jardim da Manga? E de onde vem o nome deste jardim e quem participou no seu desenho?

**Category:** RAG+PLACES  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: YES
- Weather: NO
- Places: YES

**Expected Weather Tool:** null  
**Expected Places Tool:** get_distance_between_places

**RAG Information Need:** origem do nome do Jardim/Claustro da Manga e autoria do desenho

**Essential Facts:**

- **F1** — Segundo a lenda, o nome deve-se a D. João III ter traçado o desenho do claustro na manga do seu gibão.
- **F2** — João de Ruão participou diretamente no desenho de conjunto do claustro e nos quatro relevos dos cubelos da fonte central.

**Gold Evidence:**

- Gold documents: `jardins-historicos`
- Gold chunks: `jardins-historicos::c0021`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `jardins-historicos` | 9. JARDIM DA MANGA | CLAUSTRO DA MANGA | `jardins-historicos::c0021` | F1 | “Conta a lenda que o nome se deve ao facto de D. João III ter traçado o desenho do claustro na manga do seu gibão” |
| `jardins-historicos` | 9. JARDIM DA MANGA | CLAUSTRO DA MANGA | `jardins-historicos::c0021` | F2 | “contou com a participação direta de João de Ruão, nomeadamente no desenho de conjunto do claustro e dos quatro relevos para os cubelos da fonte central.” |

**Weather Requirement:**

- not applicable

**Places Requirement:**

- Tool: `get_distance_between_places`
- Origin: Largo da Portagem — city: Coimbra — country_code: pt
- Destination: Jardim da Manga (Claustro da Manga) — city: Coimbra — country_code: pt
- Answer must: report the distance between the two places as returned by the tool, presented as a straight-line (geodesic) distance, never as a walking/driving route or travel time

**Notes:** —

### D3_Q24 — Onde ficam as ruínas de Conímbriga e porque é que muitos dos seus habitantes se mudaram para Æminium?

**Category:** RAG+PLACES  
**Difficulty:** hard

**Gold Capabilities:**

- RAG: YES
- Weather: NO
- Places: YES

**Expected Weather Tool:** null  
**Expected Places Tool:** search_place

**RAG Information Need:** razão da migração dos habitantes de Conímbriga para Æminium

**Essential Facts:**

- **F1** — No século V, Conímbriga passou a ser constantemente saqueada pelos povos germanos.
- **F2** — Por isso, muitos dos seus habitantes mudaram-se para Æminium (a Coimbra romana), que cresceu com o declínio de Conímbriga.

**Gold Evidence:**

- Gold documents: `web-visitecoimbra-coimbra-muralhada`
- Gold chunks: `web-visitecoimbra-coimbra-muralhada::c0001`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `web-visitecoimbra-coimbra-muralhada` | (document introduction / no section heading) | `web-visitecoimbra-coimbra-muralhada::c0001` | F1 | “Durante o século V DC, Conímbriga, localizada a cerca de 15 quilómetros de Æminium, passou a ser constantemente saqueada pelos povos germanos.” |
| `web-visitecoimbra-coimbra-muralhada` | (document introduction / no section heading) | `web-visitecoimbra-coimbra-muralhada::c0001` | F2 | “Por este motivo, muitos dos seus habitantes mudaram-se para Æminium.” |
| `web-visitecoimbra-coimbra-muralhada` | (document introduction / no section heading) | `web-visitecoimbra-coimbra-muralhada::c0001` | F2 | “Coimbra foi uma cidade romana chamada Æminium que cresceu devido ao declínio da vizinha cidade de Conímbriga.” |

**Weather Requirement:**

- not applicable

**Places Requirement:**

- Tool: `search_place`
- Place: Conímbriga (ruínas romanas) — city: Condeixa-a-Nova (distrito de Coimbra) — country_code: pt
- Answer must: identify the location returned for Conímbriga (resolved name/address or coordinates as returned by the tool)

**Notes:** Only place outside the city of Coimbra in the Places set. The expected municipality is a Places (not RAG) requirement; the corpus only states that Conímbriga is about 15 km from Æminium.

### D3_Q25 — A que distância fica a Casa-Museu Miguel Torga da Praça da República, em Coimbra? E quem projetou a casa e quando abriu ao público?

**Category:** RAG+PLACES  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: YES
- Weather: NO
- Places: YES

**Expected Weather Tool:** null  
**Expected Places Tool:** get_distance_between_places

**RAG Information Need:** autoria do projeto e abertura ao público da Casa-Museu Miguel Torga

**Essential Facts:**

- **F1** — A casa foi projetada pelo arquiteto Valdez.
- **F2** — Abriu ao público a 12 de agosto de 2007, dia do centenário do nascimento do poeta.

**Gold Evidence:**

- Gold documents: `coimbra-dos-escritores`, `web-visitecoimbra-museus`
- Gold chunks: `coimbra-dos-escritores::c0022`, `web-visitecoimbra-museus::c0024`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `coimbra-dos-escritores` | 14. CASA-MUSEU MIGUEL TORGA | `coimbra-dos-escritores::c0022` | F1, F2 | “projetada pelo arquiteto Valdez. Abriu ao público no dia 12 de agosto de 2007, dia do centenário do nascimento do Poeta.” |
| `web-visitecoimbra-museus` | Casa Museu Miguel Torga | `web-visitecoimbra-museus::c0024` | F1, F2 | “projetada pelo arquiteto Valdez. Abriu ao público no dia 12 de agosto de 2007, dia do centenário do nascimento do Poeta.” |

**Weather Requirement:**

- not applicable

**Places Requirement:**

- Tool: `get_distance_between_places`
- Origin: Casa-Museu Miguel Torga — city: Coimbra — country_code: pt
- Destination: Praça da República — city: Coimbra — country_code: pt
- Answer must: report the distance between the two places as returned by the tool, presented as a straight-line (geodesic) distance, never as a walking/driving route or travel time

**Notes:** Different entity and facts from the D2 V2 question on the Memorial Miguel Torga.

## WEATHER+PLACES (Q26–Q30)

### D3_Q26 — Vou agora ao Pátio da Inquisição, em Coimbra. Onde fica exatamente e que tempo está a fazer neste momento na cidade?

**Category:** WEATHER+PLACES  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: NO
- Weather: YES
- Places: YES

**Expected Weather Tool:** get_current_weather  
**Expected Places Tool:** search_place

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- Tool: `get_current_weather`
- Location: Coimbra, Portugal
- Temporal: current
- Minimum forecast days: n/a (current conditions)
- Answer must: describe the current weather conditions in Coimbra as returned by the tool

**Places Requirement:**

- Tool: `search_place`
- Place: Pátio da Inquisição — city: Coimbra — country_code: pt
- Answer must: identify the location returned for Pátio da Inquisição (resolved name/address or coordinates as returned by the tool)

**Notes:** No historical information is requested; the Pátio da Inquisição history in the corpus is out of scope.

### D3_Q27 — Tenho treino no Estádio Universitário de Coimbra. A que distância fica do Museu da Água, e está a fazer vento agora em Coimbra?

**Category:** WEATHER+PLACES  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: NO
- Weather: YES
- Places: YES

**Expected Weather Tool:** get_current_weather  
**Expected Places Tool:** get_distance_between_places

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- Tool: `get_current_weather`
- Location: Coimbra, Portugal
- Temporal: current
- Minimum forecast days: n/a (current conditions)
- Answer must: report the current wind speed in Coimbra (km/h) as returned by the tool

**Places Requirement:**

- Tool: `get_distance_between_places`
- Origin: Estádio Universitário de Coimbra — city: Coimbra — country_code: pt
- Destination: Museu da Água — city: Coimbra — country_code: pt
- Answer must: report the distance between the two places as returned by the tool, presented as a straight-line (geodesic) distance, never as a walking/driving route or travel time

**Notes:** —

### D3_Q28 — Amanhã quero caminhar na Mata Nacional de Vale de Canas. Que tempo se espera amanhã em Coimbra e a que distância fica a mata da Praça do Comércio?

**Category:** WEATHER+PLACES  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: NO
- Weather: YES
- Places: YES

**Expected Weather Tool:** get_weather_forecast  
**Expected Places Tool:** get_distance_between_places

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- Tool: `get_weather_forecast`
- Location: Coimbra, Portugal
- Temporal: tomorrow
- Minimum forecast days: 2
- Answer must: describe tomorrow's forecast for Coimbra (temperatures, precipitation, weather description) as returned by the tool

**Places Requirement:**

- Tool: `get_distance_between_places`
- Origin: Mata Nacional de Vale de Canas — city: Coimbra — country_code: pt
- Destination: Praça do Comércio — city: Coimbra — country_code: pt
- Answer must: report the distance between the two places as returned by the tool, presented as a straight-line (geodesic) distance, never as a walking/driving route or travel time

**Notes:** 'Praça do Comércio' must be resolved in Coimbra (not Lisboa); the question names Coimbra explicitly.

### D3_Q29 — Como vai estar o tempo em Coimbra nos próximos três dias, e que distância há entre o Convento São Francisco e a Ponte Pedonal Pedro e Inês?

**Category:** WEATHER+PLACES  
**Difficulty:** medium

**Gold Capabilities:**

- RAG: NO
- Weather: YES
- Places: YES

**Expected Weather Tool:** get_weather_forecast  
**Expected Places Tool:** get_distance_between_places

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- Tool: `get_weather_forecast`
- Location: Coimbra, Portugal
- Temporal: next 3 days
- Minimum forecast days: 3
- Answer must: summarise the forecast for Coimbra for each of the next three days as returned by the tool

**Places Requirement:**

- Tool: `get_distance_between_places`
- Origin: Convento São Francisco — city: Coimbra — country_code: pt
- Destination: Ponte Pedonal Pedro e Inês — city: Coimbra — country_code: pt
- Answer must: report the distance between the two places as returned by the tool, presented as a straight-line (geodesic) distance, never as a walking/driving route or travel time

**Notes:** —

### D3_Q30 — Queria levar os miúdos ao Exploratório – Centro Ciência Viva de Coimbra. Onde fica, e o tempo agora está bom para estar ao ar livre?

**Category:** WEATHER+PLACES  
**Difficulty:** hard

**Gold Capabilities:**

- RAG: NO
- Weather: YES
- Places: YES

**Expected Weather Tool:** get_current_weather  
**Expected Places Tool:** search_place

**RAG Information Need:** not applicable

**Essential Facts:**

- not applicable

**Gold Evidence:**

- not applicable

**Weather Requirement:**

- Tool: `get_current_weather`
- Location: Coimbra, Portugal
- Temporal: current
- Minimum forecast days: n/a (current conditions)
- Answer must: describe the current weather conditions in Coimbra as returned by the tool
- Answer must: judge whether conditions suit outdoor activities without contradicting the returned values

**Places Requirement:**

- Tool: `search_place`
- Place: UC Exploratório – Centro Ciência Viva de Coimbra — city: Coimbra — country_code: pt
- Answer must: identify the location returned for Exploratório – Centro Ciência Viva (resolved name/address or coordinates as returned by the tool)

**Notes:** Indirect weather intent ('está bom para estar ao ar livre?'). No RAG need: the question does not ask what the centre offers.

## RAG+WEATHER+PLACES (Q31–Q35)

### D3_Q31 — Amanhã quero visitar a Torre de Almedina. Vai estar bom tempo em Coimbra? Gostava também de saber onde fica a torre e que funções teve ao longo dos séculos.

**Category:** RAG+WEATHER+PLACES  
**Difficulty:** hard

**Gold Capabilities:**

- RAG: YES
- Weather: YES
- Places: YES

**Expected Weather Tool:** get_weather_forecast  
**Expected Places Tool:** search_place

**RAG Information Need:** funções históricas da Torre de Almedina

**Essential Facts:**

- **F1** — Foi a porta principal de acesso ao interior da muralha (intramuros) da cidade.
- **F2** — As suas origens remontam à época de ocupação islâmica.
- **F3** — No século XVI recebeu um piso superior para servir de Casa da Vereação, sendo também conhecida por Torre da Relação.
- **F4** — Atualmente acolhe o Núcleo da Cidade Muralhada.

**Gold Evidence:**

- Gold documents: `coimbra-para-os-pequenitos`, `web-visitecoimbra-heranca-cultural-e-religiosa`, `web-visitecoimbra-museus`
- Gold chunks: `coimbra-para-os-pequenitos::c0007`, `web-visitecoimbra-heranca-cultural-e-religiosa::c0027`, `web-visitecoimbra-museus::c0012`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `coimbra-para-os-pequenitos` | 3. TORRE DE ALMEDINA | NÚCLEO DA CIDADE MURALHADA | `coimbra-para-os-pequenitos::c0007` | F1, F2 | “Porta principal de acesso aos intramuros da cidade de Coimbra, cujas fundações remontam à época de ocupação islâmica.” |
| `coimbra-para-os-pequenitos` | 3. TORRE DE ALMEDINA | NÚCLEO DA CIDADE MURALHADA | `coimbra-para-os-pequenitos::c0007` | F3 | “no século XVI, época em que recebe o acrescento superior para servir de Casa da Vereação, sendo por isso também conhecida por Torre da Relação.” |
| `coimbra-para-os-pequenitos` | 3. TORRE DE ALMEDINA | NÚCLEO DA CIDADE MURALHADA | `coimbra-para-os-pequenitos::c0007` | F4 | “Atualmente está aqui sediado o Núcleo da Cidade Muralhada” |
| `web-visitecoimbra-heranca-cultural-e-religiosa` | Monumentos e outros edifícios históricos > Torre e Arco de Almedina | `web-visitecoimbra-heranca-cultural-e-religiosa::c0027` | F1, F2 | “Porta principal da muralha de Coimbra, com origens islâmicas, integrava o sistema defensivo da cidade.” |
| `web-visitecoimbra-heranca-cultural-e-religiosa` | Monumentos e outros edifícios históricos > Torre e Arco de Almedina | `web-visitecoimbra-heranca-cultural-e-religiosa::c0027` | F3 | “Remodelada no século XVI, recebeu um piso superior para funcionar como Casa da Vereação, conhecida como Torre da Relação.” |
| `web-visitecoimbra-heranca-cultural-e-religiosa` | Monumentos e outros edifícios históricos > Torre e Arco de Almedina | `web-visitecoimbra-heranca-cultural-e-religiosa::c0027` | F4 | “Hoje, abriga o Núcleo da Cidade Muralhada.” |
| `web-visitecoimbra-museus` | Torre de Almedina | `web-visitecoimbra-museus::c0012` | F1, F4 | “foi, em tempos, a principal porta de acesso aos intramuros da cidade de Coimbra. Atualmente alberga o Núcleo da Cidade Muralhada” |

**Weather Requirement:**

- Tool: `get_weather_forecast`
- Location: Coimbra, Portugal
- Temporal: tomorrow
- Minimum forecast days: 2
- Answer must: describe tomorrow's forecast for Coimbra as returned by the tool

**Places Requirement:**

- Tool: `search_place`
- Place: Torre de Almedina — city: Coimbra — country_code: pt
- Answer must: identify the location returned for Torre de Almedina (resolved name/address or coordinates as returned by the tool)

**Notes:** The three gold chunks are consistent with each other.

### D3_Q32 — Como estão as condições do tempo agora em Coimbra? Quero passar pela Torre de Anto e depois pela Ponte de Santa Clara: que distância há entre as duas, e porque é que a torre se chama assim?

**Category:** RAG+WEATHER+PLACES  
**Difficulty:** hard

**Gold Capabilities:**

- RAG: YES
- Weather: YES
- Places: YES

**Expected Weather Tool:** get_current_weather  
**Expected Places Tool:** get_distance_between_places

**RAG Information Need:** o que é a Torre de Anto e a origem do seu nome

**Essential Facts:**

- **F1** — É uma torre de origem medieval integrada na antiga muralha de Coimbra.
- **F2** — Deve o nome ao poeta António Nobre, que lá morou no século XIX (enquanto frequentava a Faculdade de Direito).

**Gold Evidence:**

- Gold documents: `web-visitecoimbra-heranca-cultural-e-religiosa`, `fado-e-tradicoes-academicas`, `coimbra-dos-escritores`
- Gold chunks: `web-visitecoimbra-heranca-cultural-e-religiosa::c0026`, `fado-e-tradicoes-academicas::c0012`, `coimbra-dos-escritores::c0020`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `web-visitecoimbra-heranca-cultural-e-religiosa` | Monumentos e outros edifícios históricos > Torre de Anto | Núcleo da Guitarra e do Fado de Coimbra | `web-visitecoimbra-heranca-cultural-e-religiosa::c0026` | F1, F2 | “Torre medieval integrada na muralha de Coimbra, adaptada a residência na época manuelina. No século XIX, foi lar do poeta António Nobre, origem do nome atual.” |
| `fado-e-tradicoes-academicas` | 6. TORRE DE ANTO | NÚCLEO DA GUITARRA E DO FADO DE COIMBRA | `fado-e-tradicoes-academicas::c0012` | F1 | “Torre de origem medieval integrada na antiga muralha de Coimbra” |
| `fado-e-tradicoes-academicas` | 6. TORRE DE ANTO | NÚCLEO DA GUITARRA E DO FADO DE COIMBRA | `fado-e-tradicoes-academicas::c0012` | F2 | “aqui morou, durante parte do tempo em que frequentou a Faculdade de Direito, o poeta António Nobre, o que originou a designação pela qual é hoje conhecida.” |
| `coimbra-dos-escritores` | 12. TORRE DE ANTO | NÚCLEO DA GUITARRA E DO FADO DE COIMBRA | `coimbra-dos-escritores::c0020` | F1 | “Torre de origem medieval integrada na antiga muralha de Coimbra” |
| `coimbra-dos-escritores` | 12. TORRE DE ANTO | NÚCLEO DA GUITARRA E DO FADO DE COIMBRA | `coimbra-dos-escritores::c0020` | F2 | “aqui morou, durante parte do tempo em que frequentou a faculdade de Direito, o poeta António Nobre, o que originou a designação pela qual é hoje conhecida.” |

**Weather Requirement:**

- Tool: `get_current_weather`
- Location: Coimbra, Portugal
- Temporal: current
- Minimum forecast days: n/a (current conditions)
- Answer must: describe the current weather conditions in Coimbra as returned by the tool

**Places Requirement:**

- Tool: `get_distance_between_places`
- Origin: Torre de Anto — city: Coimbra — country_code: pt
- Destination: Ponte de Santa Clara — city: Coimbra — country_code: pt
- Answer must: report the distance between the two places as returned by the tool, presented as a straight-line (geodesic) distance, never as a walking/driving route or travel time

**Notes:** The question deliberately does not ask what the tower houses today: web-visitecoimbra-museus::c0013 gives a different current designation (Casa do Artesanato / Núcleo Museológico da Memória da Escrita) from the other three documents (Núcleo da Guitarra e do Fado), so that need would not have a single gold answer.

### D3_Q33 — Estou a pensar ir a Almalaguês depois de amanhã para conhecer as tecedeiras. Como vai estar o tempo em Coimbra nesse dia, onde fica Almalaguês e o que caracteriza a sua tecelagem?

**Category:** RAG+WEATHER+PLACES  
**Difficulty:** hard

**Gold Capabilities:**

- RAG: YES
- Weather: YES
- Places: YES

**Expected Weather Tool:** get_weather_forecast  
**Expected Places Tool:** search_place

**RAG Information Need:** características da tecelagem de Almalaguês

**Essential Facts:**

- **F1** — A tecelagem de Almalaguês é reconhecida pelos padrões geométricos minuciosos e pelas cores vibrantes.
- **F2** — Era originalmente produzida em linho; hoje é mais comum o uso do algodão.
- **F3** — As peças mais emblemáticas são as colchas, os tapetes e os atoalhados.

**Gold Evidence:**

- Gold documents: `web-visitecoimbra-tecelagem-de-almalagues`
- Gold chunks: `web-visitecoimbra-tecelagem-de-almalagues::c0001`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `web-visitecoimbra-tecelagem-de-almalagues` | (document introduction / no section heading) | `web-visitecoimbra-tecelagem-de-almalagues::c0001` | F1 | “Reconhecida pelos padrões geométricos minuciosos e pelas cores vibrantes” |
| `web-visitecoimbra-tecelagem-de-almalagues` | (document introduction / no section heading) | `web-visitecoimbra-tecelagem-de-almalagues::c0001` | F2 | “Originalmente produzida em linho, a tecelagem adaptou-se ao longo do tempo, sendo hoje mais comum o uso do algodão.” |
| `web-visitecoimbra-tecelagem-de-almalagues` | (document introduction / no section heading) | `web-visitecoimbra-tecelagem-de-almalagues::c0001` | F3 | “Entre as peças mais emblemáticas destacam-se as colchas ricamente trabalhadas, os tapetes e os atoalhados” |

**Weather Requirement:**

- Tool: `get_weather_forecast`
- Location: Coimbra, Portugal
- Temporal: day after tomorrow
- Minimum forecast days: 3
- Answer must: describe the forecast for the day after tomorrow in Coimbra as returned by the tool

**Places Requirement:**

- Tool: `search_place`
- Place: Almalaguês (freguesia) — city: Coimbra — country_code: pt
- Answer must: identify the location returned for Almalaguês (resolved name/address or coordinates as returned by the tool)

**Notes:** The weather location is explicitly Coimbra (Almalaguês is a parish of the Coimbra municipality); a forecast for Almalaguês itself is semantically acceptable.

### D3_Q34 — Vou ao Café Santa Cruz. Quantos graus estão agora em Coimbra, a que distância fica o café do Mercado Municipal D. Pedro V, e que doce conventual é associado a esse café e como é feito?

**Category:** RAG+WEATHER+PLACES  
**Difficulty:** hard

**Gold Capabilities:**

- RAG: YES
- Weather: YES
- Places: YES

**Expected Weather Tool:** get_current_weather  
**Expected Places Tool:** get_distance_between_places

**RAG Information Need:** o doce associado ao Café Santa Cruz (Crúzios) e a sua composição

**Essential Facts:**

- **F1** — No Café Santa Cruz pode ser apreciado o doce chamado Crúzios.
- **F2** — O doce foi reinventado e batizado com o nome dos Cónegos do mosteiro vizinho.
- **F3** — Os Crúzios são feitos com massa fina e crocante, recheada com um creme de ovos e amêndoa.

**Gold Evidence:**

- Gold documents: `viver-o-patrimonio-em-coimbra`, `web-visitecoimbra-docaria-conventual-de-coimbra`
- Gold chunks: `viver-o-patrimonio-em-coimbra::c0023`, `web-visitecoimbra-docaria-conventual-de-coimbra::c0006`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `viver-o-patrimonio-em-coimbra` | 17. PRAÇA 8 DE MAIO | `viver-o-patrimonio-em-coimbra::c0023` | F1, F2 | “atualmente Café Santa Cruz. É neste café que pode ser apreciada uma das iguarias doceiras de Coimbra: os Crúzios, doce reinventado e batizado com o nome dos Cónegos do vizinho mosteiro.” |
| `web-visitecoimbra-docaria-conventual-de-coimbra` | Doces a não perder > Crúzios | `web-visitecoimbra-docaria-conventual-de-coimbra::c0006` | F3 | “Os Crúzios são doces conventuais de Coimbra, feitos com massa fina e crocante, recheada com um delicado creme de ovos e amêndoa.” |

**Weather Requirement:**

- Tool: `get_current_weather`
- Location: Coimbra, Portugal
- Temporal: current
- Minimum forecast days: n/a (current conditions)
- Answer must: report the current temperature in Coimbra (°C) as returned by the tool

**Places Requirement:**

- Tool: `get_distance_between_places`
- Origin: Café Santa Cruz — city: Coimbra — country_code: pt
- Destination: Mercado Municipal D. Pedro V — city: Coimbra — country_code: pt
- Answer must: report the distance between the two places as returned by the tool, presented as a straight-line (geodesic) distance, never as a walking/driving route or travel time

**Notes:** Cross-document but not inferential: both chunks name 'Crúzios' explicitly; the viver-o-patrimonio chunk links Crúzios to the café, the doçaria chunk describes Crúzios. The link café→doce is stated in the corpus, not inferred.

### D3_Q35 — Vou estar uma semana em Coimbra. Como vai estar o tempo nos próximos sete dias, onde fica o Departamento de Matemática da Universidade de Coimbra e porque é que a inauguração desse edifício ficou na história?

**Category:** RAG+WEATHER+PLACES  
**Difficulty:** hard

**Gold Capabilities:**

- RAG: YES
- Weather: YES
- Places: YES

**Expected Weather Tool:** get_weather_forecast  
**Expected Places Tool:** search_place

**RAG Information Need:** significado histórico da inauguração do Departamento de Matemática

**Essential Facts:**

- **F1** — O edifício foi inaugurado a 17 de abril de 1969.
- **F2** — O dia e a cerimónia da inauguração marcam o início da Crise Académica.

**Gold Evidence:**

- Gold documents: `universidade-alta-sofia-patrimonio-mundial`
- Gold chunks: `universidade-alta-sofia-patrimonio-mundial::c0029`

| Document | Section | Chunk | Supports | Excerpt |
|---|---|---|---|---|
| `universidade-alta-sofia-patrimonio-mundial` | 8. DEPARTAMENTO DE MATEMÁTICA DA FACULDADE DE CIÊNCIAS E TECNOLOGIA | `universidade-alta-sofia-patrimonio-mundial::c0029` | F1, F2 | “Construção inaugurada a 17 de abril de 1969, dia e cerimónia que marcam o início da Crise Académica.” |

**Weather Requirement:**

- Tool: `get_weather_forecast`
- Location: Coimbra, Portugal
- Temporal: next 7 days
- Minimum forecast days: 7
- Answer must: summarise the 7-day forecast for Coimbra as returned by the tool

**Places Requirement:**

- Tool: `search_place`
- Place: Departamento de Matemática da Universidade de Coimbra — city: Coimbra — country_code: pt
- Answer must: identify the location returned for Departamento de Matemática da Universidade de Coimbra (resolved name/address or coordinates as returned by the tool)

**Notes:** The search target is a specific department building, not the generic 'Universidade de Coimbra'.

