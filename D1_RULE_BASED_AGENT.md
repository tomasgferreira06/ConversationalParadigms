# D1 — Rule-Based Agent
## Coimbra Tourist Guide

## 1. Purpose

This document defines the conceptual design of the **D1 Rule-Based Agent** for the Natural Language Interaction course project.

The agent is an adaptation of the **NLTK ELIZA chatbot architecture** to a new persona: a virtual tourist guide for the city of Coimbra.

The implementation should remain rule-based and should primarily rely on:

- regular expressions;
- ordered pattern-response rules;
- captured groups;
- predefined response alternatives;
- simple text normalisation;
- optional lightweight NLP enhancements, if useful.

The goal of this document is to define the behaviour of the agent **before implementation**, so that the Python code becomes a direct translation of an already-defined conversational specification.

---

## 2. Persona

### Name

**Coimbra Guide**

### Role

A virtual tourist guide specialised in the city of Coimbra.

### Main objective

Help visitors discover Coimbra through a simple conversational interface.

The agent should provide guidance about:

- tourist attractions;
- monuments;
- museums;
- historical places;
- gardens and outdoor spaces;
- restaurants;
- cafés;
- bars and nightlife;
- activities;
- specific places in Coimbra;
- general recommendations.

### Personality

The agent should be:

- friendly;
- concise;
- helpful;
- conversational;
- locally focused;
- clear about its limitations.

### Example introduction

> Olá! Sou o Coimbra Guide, o teu guia virtual pela cidade de Coimbra. Posso ajudar-te a descobrir monumentos, museus, jardins, restaurantes, cafés, bares e outras atividades.

---

## 3. Scope

### In scope

The agent should answer questions related to tourism in Coimbra, including:

- what to visit;
- where to eat;
- where to drink coffee;
- where to go at night;
- what activities to do;
- information about specific tourist locations;
- general recommendations based on the user's interests.

### Out of scope

The agent is not intended to answer questions about:

- politics;
- programming;
- medicine;
- general world knowledge;
- news;
- tourism in other cities;
- unrelated personal advice.

### Out-of-domain behaviour

When a request is outside the supported domain, the agent should redirect the conversation to Coimbra tourism.

Example:

> Sou especializado em turismo em Coimbra. Posso ajudar-te a descobrir locais, restaurantes ou atividades na cidade.

---

## 4. Core Conversational Model

The agent follows the same general rule-based paradigm as NLTK ELIZA:

```text
User input
    ↓
Simple normalisation
    ↓
Ordered rule matching
    ↓
Regular expression matches?
    ├── Yes → choose one predefined response
    └── No  → fallback response
```

Some rules may capture parts of the user's input and reuse them in the response.

Example:

```text
User:
"Quero comida italiana"

Captured value:
"italiana"

Response:
"Se procuras comida italiana, posso sugerir..."
```

---

## 5. Rule Families

The complete rule set is divided into the following conceptual families:

1. **Conversation**
2. **Tourist discovery**
3. **Food and drink**
4. **Specific places**
5. **Recommendations and preferences**
6. **Agent identity and capabilities**
7. **Fallback and out-of-domain behaviour**

---

# 6. Supported Intents

## 6.1 Conversation Intents

### GREETING

**Goal**

Start the conversation naturally.

**Example utterances**

- Olá
- Bom dia
- Boa tarde
- Boa noite
- Hey
- Olá guia

**Expected behaviour**

Greet the user and briefly explain what the agent can do.

**Possible responses**

- Olá! Bem-vindo a Coimbra. Posso ajudar-te a descobrir locais, restaurantes e atividades.
- Olá! Queres conhecer monumentos, museus, jardins, restaurantes ou outros locais em Coimbra?
- Bem-vindo! O que gostarias de descobrir em Coimbra?

**Captured entities**

None.

---

### GOODBYE

**Goal**

End the conversation.

**Example utterances**

- Adeus
- Até logo
- Até à próxima
- Tchau
- Vou-me embora
- Obrigado, até logo

**Possible responses**

- Até à próxima! Espero que aproveites Coimbra.
- Boa visita e até breve!
- Até logo! Diverte-te em Coimbra.

**Captured entities**

None.

---

### THANKS

**Goal**

Respond to expressions of gratitude.

**Example utterances**

- Obrigado
- Obrigada
- Muito obrigado
- Valeu
- Perfeito, obrigado

**Possible responses**

- De nada! Aproveita Coimbra.
- Ora essa! Posso ajudar-te com mais alguma coisa?
- É um prazer ajudar.

**Captured entities**

None.

---

### HELP

**Goal**

Explain the supported capabilities of the agent.

**Example utterances**

- Ajuda
- O que posso perguntar?
- O que sabes fazer?
- Como me podes ajudar?
- Que informações tens?

**Possible response**

> Posso ajudar-te a descobrir pontos turísticos, monumentos, museus, jardins, restaurantes, cafés, bares e atividades em Coimbra.

**Captured entities**

None.

---

# 7. Tourist Discovery Intents

## ATTRACTIONS_GENERAL

**Goal**

Handle broad requests about what to visit in Coimbra.

**Example utterances**

- O que posso visitar em Coimbra?
- O que há para ver?
- Que sítios devo visitar?
- Quais são os principais pontos turísticos?
- O que recomendas visitar?
- Quero conhecer Coimbra

**Expected behaviour**

Suggest broad categories or representative tourist places.

**Possible response**

> Coimbra tem vários locais interessantes. Posso sugerir monumentos, museus, jardins ou zonas históricas. O que preferes?

**Captured entities**

None.

---

## MONUMENTS

**Goal**

Recommend monuments.

**Example utterances**

- Que monumentos posso visitar?
- Quero visitar um monumento
- Que monumentos existem?
- Recomenda-me um monumento
- Quero ver arquitetura histórica

**Possible behaviour**

Recommend one or more monuments in Coimbra.

**Captured entities**

- `category = monument`

---

## MUSEUMS

**Goal**

Recommend museums.

**Example utterances**

- Há museus em Coimbra?
- Que museus posso visitar?
- Quero visitar um museu
- Recomenda-me um museu
- Gosto de museus

**Captured entities**

- `category = museum`

---

## GARDENS

**Goal**

Recommend gardens, parks or outdoor spaces.

**Example utterances**

- Há jardins para visitar?
- Quero ir a um parque
- Quero passear num jardim
- Onde posso passear?
- Quero um sítio ao ar livre

**Captured entities**

- `category = garden`

---

## HISTORICAL

**Goal**

Recommend historical places.

**Example utterances**

- Quero conhecer a história de Coimbra
- Que locais históricos existem?
- Quero visitar a Coimbra antiga
- Há sítios históricos?
- Recomenda-me um local histórico

**Captured entities**

- `interest = history`

---

## ACTIVITIES

**Goal**

Handle broad questions about things to do.

**Example utterances**

- O que posso fazer em Coimbra?
- Que atividades recomendas?
- Estou sem nada para fazer
- O que posso fazer hoje?
- Que experiências existem?

**Possible response**

> Depende do que procuras. Preferes cultura, passeios, comida ou vida noturna?

**Captured entities**

None.

---

# 8. Food and Drink Intents

## RESTAURANT_GENERAL

**Goal**

Handle generic requests about places to eat.

**Example utterances**

- Onde posso comer?
- Onde posso jantar?
- Onde posso almoçar?
- Recomenda-me um restaurante
- Que restaurantes existem?
- Conheces bons restaurantes?
- Estou com fome

**Possible response**

> Claro. Procuras algum tipo de comida em particular?

**Captured entities**

None.

---

## RESTAURANT_CUISINE

**Goal**

Recommend restaurants according to the requested cuisine.

**Example utterances**

- Quero comida portuguesa
- Quero comer italiano
- Conheces restaurantes vegetarianos?
- Quero um restaurante de comida tradicional
- Onde posso comer sushi?

**Captured entity**

- `cuisine`

**Conceptual example**

```text
Input:
"Quero comida italiana"

Intent:
RESTAURANT_CUISINE

Captured entity:
cuisine = italiana
```

**Expected behaviour**

Use the captured cuisine to provide a more specific response.

**Priority**

Higher than `RESTAURANT_GENERAL`.

---

## CAFE

**Goal**

Recommend cafés or places to have coffee/snacks.

**Example utterances**

- Onde posso beber café?
- Recomenda um café
- Quero tomar café
- Conheces algum café?
- Quero lanchar

**Captured entities**

- `category = cafe`

---

## NIGHTLIFE

**Goal**

Recommend bars or nightlife options.

**Example utterances**

- Onde posso sair à noite?
- Que bares existem?
- Recomenda-me um bar
- Onde posso beber um copo?
- Como é a noite em Coimbra?
- Quero sair à noite

**Captured entities**

- `category = nightlife`

---

# 9. Specific Place Intents

## PLACE_INFORMATION

**Goal**

Provide information about a specific place.

**Example utterances**

- O que é a Universidade de Coimbra?
- Fala-me da Biblioteca Joanina
- Vale a pena visitar a Sé Velha?
- O que sabes sobre o Jardim Botânico?
- Conta-me algo sobre a Quinta das Lágrimas

**Captured entity**

- `place`

**Conceptual example**

```text
Input:
"Fala-me da Biblioteca Joanina"

Intent:
PLACE_INFORMATION

Captured entity:
place = Biblioteca Joanina
```

---

## PLACE_LOCATION

**Goal**

Explain where a specific place is located.

**Example utterances**

- Onde fica a Universidade?
- Onde é a Sé Velha?
- Onde fica esse museu?
- Onde posso encontrar o Jardim Botânico?

**Captured entity**

- `place`

**Expected behaviour**

Return a short textual location description.

---

## PLACE_VISIT_INFO

**Status**

Optional.

**Possible examples**

- Posso visitar a Universidade?
- É possível visitar a biblioteca?
- Quando posso visitar o museu?

**Note**

Opening hours and prices can change over time, so this intent should only be implemented if the information source is deliberately kept static and the limitation is made clear.

---

# 10. Recommendation Intents

## RECOMMENDATION_GENERAL

**Goal**

Handle generic recommendation requests.

**Example utterances**

- Recomenda-me alguma coisa
- O que sugeres?
- Surpreende-me
- Onde devo ir?
- Qual é a tua sugestão?

**Captured entities**

None.

**Priority**

Lower than category-specific or preference-specific recommendation rules.

---

## RECOMMENDATION_INTEREST

**Goal**

Recommend places according to a stated personal interest.

**Example utterances**

- Gosto de história
- Gosto de natureza
- Gosto de arte
- Prefiro sítios tranquilos
- Gosto de arquitetura

**Captured entity**

- `interest`

**Conceptual example**

```text
Input:
"Gosto de história"

Intent:
RECOMMENDATION_INTEREST

Captured entity:
interest = história
```

---

## RECOMMENDATION_CATEGORY

**Goal**

Recommend something from a specific category.

**Example utterances**

- Recomenda-me um museu
- Recomenda-me um restaurante
- Recomenda-me um jardim
- Recomenda-me um bar

**Captured entity**

- `category`

**Priority**

Higher than `RECOMMENDATION_GENERAL`.

---

# 11. Agent Identity Intents

## BOT_IDENTITY

**Goal**

Explain who the agent is.

**Example utterances**

- Quem és?
- O que és?
- Qual é o teu nome?
- És um guia?
- És um chatbot?

**Possible response**

> Sou o Coimbra Guide, um guia turístico virtual especializado na cidade de Coimbra.

---

## BOT_CAPABILITIES

**Goal**

Answer questions about what the agent knows or can do.

**Example utterances**

- O que sabes?
- Conheces Coimbra?
- Sabes recomendar restaurantes?
- Podes ajudar-me a visitar Coimbra?

**Possible behaviour**

Explain the supported tourism-related capabilities.

---

# 12. Entities

The following entities are relevant to the conversational design.

| Entity | Description | Examples |
|---|---|---|
| `category` | Type of place or activity | museu, jardim, monumento, restaurante |
| `place` | Specific tourist location | Universidade de Coimbra, Biblioteca Joanina |
| `cuisine` | Type of food | portuguesa, italiana, vegetariana |
| `interest` | User preference | história, natureza, arte, arquitetura |
| `meal` | Meal context | almoço, jantar |
| `activity` | Type of activity | passeio, visita, saída à noite |

Not all entities need to be implemented in the first version.

---

# 13. Rule Priority

Rule order is essential because the NLTK `Chat` architecture processes rules sequentially.

More specific rules must appear before more generic rules.

## Recommended priority

```text
1. GOODBYE

2. Specific place rules
   - PLACE_LOCATION
   - PLACE_INFORMATION

3. Parameterised rules
   - RESTAURANT_CUISINE
   - RECOMMENDATION_INTEREST
   - RECOMMENDATION_CATEGORY

4. Specific tourism categories
   - MUSEUMS
   - MONUMENTS
   - GARDENS
   - HISTORICAL
   - NIGHTLIFE
   - CAFE

5. Generic tourism intents
   - RESTAURANT_GENERAL
   - ATTRACTIONS_GENERAL
   - ACTIVITIES

6. General conversation
   - HELP
   - BOT_CAPABILITIES
   - BOT_IDENTITY
   - GREETING
   - THANKS

7. Generic recommendation
   - RECOMMENDATION_GENERAL

8. FALLBACK
```

---

# 14. Rule Conflict Example

Consider the input:

```text
Recomenda-me um restaurante italiano
```

This sentence may contain evidence for:

```text
RECOMMENDATION_GENERAL
RESTAURANT_GENERAL
RESTAURANT_CUISINE
```

The desired interpretation is:

```text
RESTAURANT_CUISINE
```

Therefore the priority should be:

```text
restaurant + cuisine
        ↓
restaurant
        ↓
generic recommendation
        ↓
fallback
```

---

# 15. Conversation Flows

The first version may remain mostly stateless, but the design should allow simple conversational flows.

## Flow 1 — Tourist discovery

```text
User:
O que posso visitar?

Bot:
Preferes monumentos, museus ou espaços ao ar livre?

User:
Museus.

Bot:
[recommendation]
```

---

## Flow 2 — Restaurant

```text
User:
Quero jantar.

Bot:
Que tipo de comida procuras?

User:
Portuguesa.

Bot:
[recommendation]
```

---

## Flow 3 — Interest

```text
User:
Gosto de história.

Bot:
Nesse caso, posso sugerir-te alguns locais históricos de Coimbra.
```

---

# 16. Text Normalisation

Before applying regular expressions, the system may perform lightweight text normalisation.

Possible steps:

1. convert text to lowercase;
2. remove unnecessary leading/trailing whitespace;
3. optionally remove duplicated whitespace;
4. optionally normalise punctuation;
5. optionally handle common orthographic variants.

Examples:

```text
"QUERO VISITAR UM MUSEU!"
        ↓
"quero visitar um museu"
```

Possible variants to consider:

```text
não / nao
sítio / sitio
sé / se
```

The implementation should remain simple and should not hide the fact that the agent is rule-based.

---

# 17. Linguistic Variation

The system should avoid creating one rule for every sentence.

Regular expressions should group natural variants of the same intent.

Example:

```text
museu
museus
```

can conceptually be represented by a pattern equivalent to:

```regex
museus?
```

Likewise, alternatives can be grouped conceptually:

```text
comer | jantar | almoçar
```

The exact regular expressions will be defined during implementation.

---

# 18. Fallback Strategy

## FALLBACK

The fallback must always be the last rule.

**Goal**

Handle messages that do not match any known pattern.

**Example responses**

- Não percebi bem. Podes reformular?
- Posso ajudar-te com locais, restaurantes, museus ou atividades em Coimbra.
- Não tenho informação sobre isso. Queres uma sugestão sobre Coimbra?
- Tenta perguntar-me por monumentos, museus, restaurantes, jardins ou atividades.

The fallback should avoid pretending that the agent understood the request.

---

# 19. Optional NLP Enhancements

These features are not required for the first implementation but may be explored if useful.

## 19.1 Simple spelling correction

A small tourism-specific vocabulary could be used to detect small spelling mistakes.

Example:

```text
resturante
    ↓
restaurante
```

This could be based on minimum edit distance / Levenshtein distance.

Possible vocabulary:

- restaurante;
- museu;
- monumento;
- jardim;
- universidade;
- biblioteca.

This should remain an optional enhancement and not replace the rule-based core.

---

## 19.2 Simple contextual state

A later version may keep limited conversational context.

Example:

```text
User:
Quero jantar.

Bot:
Que tipo de comida procuras?

User:
Portuguesa.

Bot:
[understands that "portuguesa" refers to cuisine]
```

This would require a small state variable outside the standard ELIZA `pairs` structure.

It should only be added after the stateless rule set is stable.

---

# 20. Initial Intent Catalogue

| Priority | Intent | Captured information | Example |
|---:|---|---|---|
| 1 | `GOODBYE` | — | "Até logo" |
| 2 | `PLACE_LOCATION` | `place` | "Onde fica a Sé?" |
| 3 | `PLACE_INFORMATION` | `place` | "Fala-me da Universidade" |
| 4 | `RESTAURANT_CUISINE` | `cuisine` | "Quero comida italiana" |
| 5 | `RECOMMENDATION_INTEREST` | `interest` | "Gosto de história" |
| 6 | `RECOMMENDATION_CATEGORY` | `category` | "Recomenda-me um museu" |
| 7 | `MUSEUMS` | `category` | "Quero visitar um museu" |
| 8 | `MONUMENTS` | `category` | "Que monumentos existem?" |
| 9 | `GARDENS` | `category` | "Quero passear num jardim" |
| 10 | `HISTORICAL` | `interest` | "Que locais históricos existem?" |
| 11 | `NIGHTLIFE` | `category` | "Onde posso sair?" |
| 12 | `CAFE` | `category` | "Onde posso tomar café?" |
| 13 | `RESTAURANT_GENERAL` | — | "Onde posso jantar?" |
| 14 | `ATTRACTIONS_GENERAL` | — | "O que posso visitar?" |
| 15 | `ACTIVITIES` | — | "O que posso fazer?" |
| 16 | `HELP` | — | "O que sabes fazer?" |
| 17 | `BOT_CAPABILITIES` | — | "Conheces Coimbra?" |
| 18 | `BOT_IDENTITY` | — | "Quem és?" |
| 19 | `GREETING` | — | "Olá" |
| 20 | `THANKS` | — | "Obrigado" |
| 21 | `RECOMMENDATION_GENERAL` | — | "Recomenda-me algo" |
| 22 | `FALLBACK` | raw text | any unmatched input |

---

# 21. Rule Catalogue Template

Before implementation, each intent should be finalised using the following structure.

```md
### INTENT_NAME

**Goal**

Describe what the intent represents.

**Example utterances**

- Example 1
- Example 2
- Example 3

**Captured entities**

- entity name

**Possible responses**

- Response 1
- Response 2
- Response 3

**Priority**

Explain where the intent appears relative to similar rules.

**Potential conflicts**

- OTHER_INTENT
- ANOTHER_INTENT
```

This catalogue should be completed before translating the design into regular expressions.

---

# 22. Implementation Principles

When implementation begins, the following principles should be followed:

1. preserve the NLTK ELIZA `Chat(pairs, reflections)` architecture where appropriate;
2. keep the rule-based nature of the system explicit;
3. place specific patterns before generic patterns;
4. use capture groups when they meaningfully improve the response;
5. keep several alternative responses per rule where useful;
6. avoid overengineering the first version;
7. keep the fallback as the final rule;
8. test each rule against multiple paraphrases and against conflicting intents.

---

# 23. Testing Strategy

Each intent should later be tested with:

- expected positive examples;
- alternative wording;
- singular/plural variants;
- accented/non-accented forms when relevant;
- negative examples;
- sentences that may conflict with another intent;
- completely unsupported sentences.

Example:

```text
Intent:
MUSEUMS

Positive:
"Quero visitar um museu"
"Que museus existem?"
"Recomenda-me um museu"

Potential conflict:
"Recomenda-me um museu perto da universidade"

Negative:
"Quero jantar"
```

The goal is not only to check whether a rule matches, but also whether the **correct rule wins**.

---

# 24. Current Design Decisions

At this stage:

- the agent language is Portuguese;
- the persona is a Coimbra tourist guide;
- the main interaction mechanism is regular-expression matching;
- rule ordering is part of the system design;
- the first implementation should preferably be stateless;
- simple captured entities are encouraged;
- advanced NLP features are optional;
- live information such as changing prices or schedules is not a core requirement;
- implementation should only begin after the rule catalogue is sufficiently defined.

---

# 25. Next Step

The next step is to complete the **Rule Catalogue** intent by intent.

For each supported intent, define:

1. the exact conversational goal;
2. 10–15 representative user utterances when appropriate;
3. the information that should be captured;
4. 2–4 possible responses;
5. overlapping intents;
6. intended priority.

Only after that stage should the final regular expressions and NLTK `pairs` be implemented.
