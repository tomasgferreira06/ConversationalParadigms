# RAG Baseline V1 — Worksheet-Aligned Embedding

Data: 2026-09-28. Relatório da V0 (inalterado): `RAG_BASELINE_SMOKE_TEST.md`.

**Isto não é uma avaliação formal.** Não há ground truth, relevance judgements,
Precision/Recall/F1@k, MRR, nDCG nem LLM-as-Judge. As observações são manuais e
diagnósticas, sobre as mesmas 13 perguntas do smoke test da V0.

## 1. Motivation

- A **V0** usava `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`.
- A **worksheet de RAG da disciplina** usa `sentence-transformers/all-mpnet-base-v2`.
- O chunking já seguia a worksheet: `chunk_size = 1000`, `chunk_overlap = 100`,
  `length_function = len`, medido em **caracteres**.
- Decidiu-se alinhar também o embedding model com a worksheet antes da avaliação
  formal, mudando **uma única variável**: o embedding model. A V0 foi preservada como
  artefacto de diagnóstico.

## 2. Configuration

Definida em `d2_rag/scripts/rag_pipeline.py`. `BASELINE_V0` fica congelada. `BASELINE_V1`
é derivada dela com `dataclasses.replace`, pelo que só pode diferir nos campos indicados.
`BASELINE = BASELINE_V1`.

| Parâmetro | V0 (`BASELINE_V0`) | V1 (`BASELINE_V1` = `BASELINE`) |
|---|---|---|
| **Embedding model** | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | **`sentence-transformers/all-mpnet-base-v2`** |
| **Vector store** | `d2_rag/data/chroma_baseline/` | **`d2_rag/data/chroma_baseline_v1/`** |
| **Collection** | `coimbra_rag_baseline` | **`coimbra_rag_baseline_v1`** |
| Dimensão | 768 | 768 (verificada) |
| `normalize_embeddings` | true | true |
| Métrica | cosine (explícita) | cosine (explícita) |
| Texto embebido | `chunk["text"]` (`heading_context` + corpo) | igual |
| Chunks | `data/chunks/chunks.jsonl` (1000/100 chars) | o mesmo ficheiro (inalterado) |
| Roles indexados | `content` | `content` |
| Retrieval | similarity search, top_k = 3 | igual |
| LLM | Ollama `llama3.2:3b`, temperature 0.1 | igual |
| Prompts, contexto, fontes, `conflict_notes` | — | iguais (os testes fixam o `SYSTEM_PROMPT` literal) |

A CLI (`rag_baseline.py`) usa `BASELINE`, pelo que `--rebuild` só pode apagar e recriar
`chroma_baseline_v1/`. Nenhum caminho de código reconstrói a V0. Nenhuma dependência nova:
`pyproject.toml` inalterado; `.gitignore` passa a ignorar também `chroma_baseline_v1/`.

## 3. Vector Store Build

```text
uv run python d2_rag/scripts/rag_baseline.py --rebuild

Expected input chunks: 330
Indexed chunks: 317
Excluded caption_panel: 2
Excluded page_labels: 11
Collection 'coimbra_rag_baseline_v1' count: 317 (…\d2_rag\data\chroma_baseline_v1)
```

Validação independente, lendo a base com o cliente `chromadb`:

| Verificação | Resultado |
|---|---|
| Collections na store | só `coimbra_rag_baseline_v1` |
| Registos / embeddings | 317 / 317, dimensão 768, norma 1.0 |
| IDs | = os 317 `chunk_id` de conteúdo, únicos |
| Métrica | `cosine` |
| Documentos | = `chunk["text"]` nos 317 |
| Metadata | = `to_metadata(chunk)` nos 317 |
| PDF | todos com `source_pages` (ex.: `universidade…::c0013` → `[10, 11]`) |
| Web | todos com `url` e sem `source_pages` (ex.: `web-visitecoimbra-museus::c0007`) |
| Roles | só `content` |
| **Vetores novos, não copiados da V0** | 8 chunks reembebidos com `all-mpnet-base-v2`: cosine com o vetor guardado = 1.000000 |

## 4. Pipeline

Igual à V0 em tudo, exceto o embedding model (documentos e query) e a store/collection:

```text
Question → query embedding (all-mpnet-base-v2) → Chroma V1 (cosine) → top-3
  → contexto [Fonte 1..3] + nota de curadoria separada (se houver conflict_notes)
  → llama3.2:3b (mesmo system prompt, temperature 0.1) → ANSWER + SOURCES
```

## 5. Repeated Smoke Questions

As mesmas 13 perguntas, com a formulação exata do relatório V0 (verificada sem problemas
de codificação). Cada pergunta é independente. A distância mostrada é a cosine distance.

| # | Pergunta | V1 top-3 (distância) | Resposta V1 | Estado |
|---|---|---|---|---|
| 1 | Em que ano ficou concluída a construção da Biblioteca Joanina? | joanina c0002 *Biblioteca Joanina* (0.189); c0005 *Piso Nobre* (0.215); c0009 *Prisão Académica* (0.245) | "1728" | ✅ |
| 2 | Porque existem morcegos na Biblioteca Joanina? | joanina c0002 (0.181); c0005 *Piso Nobre* (0.182); c0009 (0.228) | cita "duas colónias de morcegos que contribuem para o controle de pragas" | ✅ |
| 3 | Quem projetou o Portugal dos Pequenitos? | jardins c0003 *2. PARQUE VERDE DO MONDEGO* (0.318); museus web c0022 *Casa da Cidadania da Língua* (0.318); pequenitos c0009 *4. PARQUE VERDE DO MONDEGO* (0.319) | abstém-se (diz que o contexto não menciona o Portugal dos Pequenitos) | ❌ retrieval; abstenção correta |
| 4 | Em que ano foi fundado o Mosteiro de Santa Cruz? | fundacao c0008 *6. MOSTEIRO DE SANTA CLARA-A-VELHA* (0.338, **só coordenadas**); viver c0029 "outros locais a visitar" (0.341); d-afonso-henriques web c0003 (0.343) | abstém-se | ❌ retrieval (§7) |
| 5 | Quem foi Sesnando David? | sesnando web c0002 (0.406); c0003 (0.429); museus web c0022 (0.458) | "administrador brilhante… reconstrução e desenvolvimento de Coimbra" | ⚠️ fiel à fonte (c0002), mas não diz quem ele era; c0001 (moçárabe, 1064) ficou em rank 7 |
| 6 | Que doces tradicionais posso encontrar em Coimbra? | doçaria web c0006 *Crúzios* (0.215); escritores c0024 (0.228); coimbra-dos-estudantes web c0003 (0.253) | só os Crúzios | ⚠️ parcial: a introdução da doçaria (c0002, top-1 na V0) ficou em rank 32 |
| 7 | O que são as Repúblicas de Coimbra? | republicas web c0001 (0.239); c0003 *Lista das Repúblicas* (0.266); muralhada web c0002 (0.294) | "espaços comunitários autogeridos por estudantes…" | ✅ |
| 8 | Que museus posso visitar em Coimbra? | museus web c0010 *Museu Municipal* (0.224); pequenitos c0013 (0.262); museus web c0001 (0.265) | Museu Municipal, Machado de Castro, Portugal dos Pequenitos, Museu da Água, Santa Clara-a-Velha | ⚠️ parcial por natureza (como na V0); todos os nomes estão no contexto (verificado) |
| 9 | Qual é a origem da Canção de Coimbra? | cancao web c0005 (0.226, frase de 98 caracteres); cancao web c0003 (0.231); cervejeira web c0001 (0.291) | abstém-se | ❌ (§8) |
| 10 | Que relação existe entre Pedro e Inês e Coimbra? | pedro-e-ines web c0001 (0.228); c0005 *Jardins da Quinta das Lágrimas* (0.253); c0004 (0.261) | refúgio em Coimbra, Quinta das Lágrimas, "Fonte das Lágrimas" | ✅ |
| D | O que é o Paço das Escolas? | museus web c0018 *Paço das Escolas* (0.261); viver c0003 *1. PAÇO DAS ESCOLAS* (0.335); fado c0006 *2. PAÇO DAS ESCOLAS* (0.343) | "conjunto arquitetónico que alberga o núcleo histórico da Universidade de Coimbra" | ✅ (melhor que a V0) |
| C | Quem fundou o Mosteiro de Santa Clara-a-Velha e quando? | museus web c0006 *Santa Clara-a-**Nova*** (0.285); museus web c0007 *Santa Clara-a-Velha* (0.288); fundacao c0008 (0.294, só coordenadas) | expõe as duas versões, mas atribui a da nota de curadoria à "Fonte 3" | ⚠️ (§9) |
| OOK | Qual foi o preço do bilhete para um jogo da Académica no Estádio Cidade de Coimbra em 2025? | pequenitos c0013 (0.306); escritores c0024 (0.313); escritores c0004 *2. PARQUE DR. MANUEL BRAGA* (0.324) | frase de insuficiência; o contexto não menciona o estádio | ✅ (§10) |

Contagem manual: **V1 → 6 ✅, 4 ⚠️, 3 ❌**. A V0 tinha 10 respostas corretas, 1 parcial
(Q8) e 2 falhas (Q4, Q9).

## 6. V0 vs V1 Diagnostic Comparison

Os dados da V0 vêm do relatório V0 (a store V0 **não** foi aberta). Distâncias de modelos
diferentes **não são comparáveis em valor absoluto**; só os rankings e as respostas o são.

| # | V0 top-1 | V1 top-1 | Resposta V0 | Resposta V1 | Observação |
|---|---|---|---|---|---|
| 1 | joanina c0002 | joanina c0002 | 1728 ✅ | 1728 ✅ | igual |
| 2 | joanina c0005 | joanina c0002 (c0005 em rank 2) | ✅ | ✅ | igual |
| 3 | fundacao c0009 (Cassiano Branco) | jardins c0003 (Parque Verde) | Cassiano Branco ✅ | abstém-se ❌ | **regressão**: fundacao c0009 → rank 6, pequenitos c0011 → rank 4 |
| 4 | fundacao c0007 (Santa Clara) | fundacao c0008 (coordenadas de Santa Clara) | abstém-se ❌ | abstém-se ❌ | falha mantém-se, **com ranks piores** (§7) |
| 5 | sesnando c0001 | sesnando c0002 | moçárabe, Fernando Magno, 1064 ✅ | administrador, reconstrução ⚠️ | **regressão parcial**: c0001 → rank 7 |
| 6 | doçaria c0002 (introdução) | doçaria c0006 (Crúzios) | lista de 6 doces ✅ | só Crúzios ⚠️ | **regressão**: c0002 → rank 32 |
| 7 | republicas c0001 | republicas c0001 | ✅ | ✅ | igual |
| 8 | museus c0001 | museus c0010 | 5 museus ⚠️ | 5 museus ⚠️ | equivalente |
| 9 | cancao c0005 (98 chars) | cancao c0005 (98 chars) | abstém-se ❌ | abstém-se ❌ | igual no top-1; c0001 desce de rank 2 para 6 (§8) |
| 10 | pedro-e-ines c0005 | pedro-e-ines c0001 | ✅ | ✅ | igual |
| D | fado c0005 (0.500) | museus c0018 *Paço das Escolas* | ✅ (match fraco) | ✅ | **melhor**: 3 documentos diferentes, todos da secção certa |
| C | fundacao c0007 (PDF, 1283) | museus c0006 (Santa Clara-a-**Nova**) | divergência exposta ✅ | divergência exposta com atribuição errada ⚠️ | **regressão**: o chunk PDF → rank 51 (§9) |
| OOK | Praça das Cortes… (0.478) | pequenitos c0013 (0.306) | recusa ✅ | recusa ✅ | igual na resposta (§10) |

**Padrões observados (sem correção):**

1. **Chunks curtos dominados pelo heading.** `fundacao::c0008` tem um corpo de 37
   caracteres (só `**Coordenadas:** 40.202822, -8.433311`), mas o texto embebido inclui o
   heading "6. MOSTEIRO DE SANTA CLARA-A-VELHA". Fica em rank 1 na Q4 e rank 3 no conflito,
   gastando um lugar do contexto sem informação. Na Q9 a frase de 98 caracteres continua
   em rank 1.
2. **Perguntas de tópico geral puxam chunks de introdução menos do que na V0** (Q5, Q6):
   a V1 prefere chunks sobre uma entidade específica (Crúzios) ou um aspeto (governo de
   Sesnando).
3. **Correspondência lexical de entidades mais fraca** em "Mosteiro de Santa Cruz" /
   "Santa Clara-a-Velha" / "Portugal dos Pequenitos". A hipótese plausível, **não
   verificada nesta tarefa**, é que o `all-mpnet-base-v2` foi treinado sobretudo em inglês
   e o corpus e as perguntas são em português.
4. **Onde há uma secção com o nome exato da pergunta** (Paço das Escolas), a V1 foi melhor
   que a V0.

## 7. Santa Cruz Case

Pergunta: "Em que ano foi fundado o Mosteiro de Santa Cruz?". Ranking completo lido só
para diagnóstico (o pipeline usa top-3).

| Chunk com "1131" | Contém o facto pedido? | Rank V0 | Rank V1 |
|---|---|---|---|
| `fundacao-da-nacionalidade::c0002` *2. IGREJA DE SANTA CRUZ \| PANTEÃO NACIONAL* ("Fundado em 1131…") | sim | **5** | **19** (0.414) |
| `universidade-alta-sofia-patrimonio-mundial::c0051` *24. MOSTEIRO DE SANTA CRUZ* | sim | **12** | **123** (0.493) |
| `viver-o-patrimonio-em-coimbra::c0024` *17. PRAÇA 8 DE MAIO* (inclui "igreja de santa cruz… Fundado em 1131") | sim, no fim do chunk | não registado | 8 (0.371) |
| `fundacao-da-nacionalidade::c0014` (introdução) | **não** (1131 = mudança da capital) | não registado | 7 (0.371) |

V1 top-10: coordenadas de Santa Clara-a-Velha, "outros locais a visitar", D. Afonso
Henriques, Praça 8 de Maio, Santa Clara-a-Velha, Santa Clara-a-Nova, …: continua a
dominar "Mosteiro" + "Santa". **A V1 não recupera melhor os chunks com o facto;
recupera-os pior** (5 → 19 e 12 → 123). O LLM abstém-se, o que é correto dado o contexto.

## 8. Canção de Coimbra Case

Pergunta: "Qual é a origem da Canção de Coimbra?"

| Chunk | Conteúdo | Rank V0 | Rank V1 |
|---|---|---|---|
| `cancao::c0005` | frase final genérica, 98 caracteres | 1 (0.342) | **1** (0.226) |
| `cancao::c0001` | contém "Desde o século XVI, há registos de estudantes que… cantavam" | 2 (0.388) | **6** (0.309) |
| `cancao::c0003` | desenvolvimento da canção, sem a origem | — | 2 (0.231) |

O rank 1 continua a ser o chunk curto e genérico. O chunk com a origem saiu do top-3, pelo
que na V1 **a abstenção é correta face ao contexto**: a falha passou de geração (V0: a
resposta estava no contexto e não foi usada) para retrieval. O resultado final é igual:
abstenção.

## 9. Conflict Case

Pergunta: "Quem fundou o Mosteiro de Santa Clara-a-Velha e quando?"

| Rank | Chunk | Conteúdo relevante | `conflict_notes` |
|---|---|---|---|
| 1 (0.285) | `web-visitecoimbra-museus::c0006` | *Santa Clara-a-**Nova*** (outro mosteiro) | sim |
| 2 (0.288) | `web-visitecoimbra-museus::c0007` | "mandado construir em 1314 por D. Isabel de Aragão" | sim |
| 3 (0.294) | `fundacao-da-nacionalidade::c0008` | só coordenadas (37 caracteres) | não |

- Os chunks com a versão PDF ficaram fora do top-3: `fundacao::c0007` ("Fundado em 1283,
  por D. Mor Dias") → **rank 51** (V0: 1). O web da Herança Cultural ("Fundado pela Rainha
  Santa Isabel") → rank 4 (V0: 3).
- A nota de curadoria foi enviada separada, como na V0.
- **Resposta:** a frase de insuficiência, seguida de "A Fonte 1 afirma … 1314 por
  D. Isabel de Aragão, enquanto **a Fonte 3 afirma … 1283 por D. Mor Dias, com uma
  refoundation em 1314**".
- **Problema de fidelidade observado:** a Fonte 3 não contém essa informação. A versão
  "1283 / D. Mor Dias" só está na **nota de curadoria**, escrita em inglês ("refoundation
  from 1314"), e o modelo copiou até a palavra inglesa. Na V0 isto não se via, porque o
  chunk PDF estava no contexto. É uma questão do prompt/nota (geração), não do embedding;
  a V1 tornou-a visível. **Não foi corrigida** (fora do âmbito: prompt inalterado).
- Houve também uma atribuição errada de fonte ("Fonte 1" é Santa Clara-a-Nova; a frase
  de 1314 está na Fonte 2).

## 10. Out-of-Knowledge

"Qual foi o preço do bilhete para um jogo da Académica no Estádio Cidade de Coimbra em
2025?"

- **Resposta:** "Não tenho informação suficiente no contexto disponível para responder com
  segurança", explicando que o contexto não menciona o estádio nem jogos. ✅ Sem invenção.
- **Retrieval:** distâncias 0.306–0.324. Na V1 o top-1 de uma pergunta fora do domínio
  (0.306) está **mais próximo** que o top-1 de várias perguntas do domínio (Q3 0.318,
  Q4 0.338, Q5 0.406). A distância da V1 separa menos entre dentro e fora do domínio do que
  a da V0 (onde o OOK tinha as distâncias mais altas da sessão). Não há threshold na
  baseline, por isso isto não afeta o comportamento atual; fica registado.

## 11. Regression / Integrity

**Hashes SHA-256 antes/depois** (build V1 + consultas + testes): 77 ficheiros, **0
diferenças**.

| Conjunto | Ficheiros | Alterados |
|---|---|---|
| Raw PDF | 8 | 0 |
| Raw Web | 24 | 0 |
| Processed PDF | 8 | 0 |
| Processed Web | 24 | 0 |
| `manifest.jsonl` | 1 | 0 |
| `chunks.jsonl`, `chunk_stats.json` | 2 | 0 |
| `chroma_baseline/` (V0) | 5 | 0 (nunca aberta) |
| `chroma_smoke/` | 5 | 0 (nunca aberta) |

A única DB nova é `data/chroma_baseline_v1/`.

**Testes:** 104 OK (98 anteriores + 6 novos, 1 substituído), offline, sem download de
modelos e sem Ollama:

- a V0 continua representável, com os valores exatos (modelo, store, collection);
- a V1 tem exatamente `all-mpnet-base-v2`, `chroma_baseline_v1/`,
  `coimbra_rag_baseline_v1` e é a `BASELINE`;
- V0 e V1 diferem **apenas** em `embedding_model`, `collection_name` e `store_dir`; os
  paths não colidem nem estão aninhados;
- a V1 seleciona 317 chunks (11 `page_labels` e 2 `caption_panel` excluídos);
- `load_embeddings` usa o modelo V1 com `normalize_embeddings=True` (mock do
  HuggingFace);
- `open_store` usa por defeito a store da configuração;
- `SYSTEM_PROMPT` igual ao literal anterior; LLM `llama3.2:3b` / 0.1 (teste já
  existente).

## 12. Decision

**IS V1 SUITABLE AS THE FORMAL RETRIEVAL BASELINE?**

# YES — como baseline de referência, não como configuração "melhor"

**Porque sim:**
- É a configuração da worksheet da disciplina (embedding e chunking 1000/100 chars), o que
  faz dela o ponto de partida metodologicamente justificado.
- Foi construída de raiz, validada (317/317, IDs, cosine, documentos, metadata e vetores
  novos) e é reproduzível a partir de `chunks.jsonl` com um único comando.
- Difere da V0 **apenas** no embedding model, o que torna a comparação V0/V1 limpa.
- O pipeline funciona de ponta a ponta, e a recusa fora do domínio continua correta.

**O que o smoke test mostra (qualitativo, 13 perguntas):**
- a V1 recuperou **pior** que a V0 neste conjunto (3 regressões claras: Q3, Q6, conflito;
  2 parciais: Q5 e os ranks de Santa Cruz e Canção) e melhor numa (Paço das Escolas);
- os problemas de chunks curtos dominados pelo heading mantêm-se;
- há um problema de fidelidade no uso da nota de curadoria (§9), independente do
  embedding.

Isto é exatamente o que a avaliação formal deve medir. Recomenda-se manter a V0 (intacta,
em `chroma_baseline/`) disponível como comparação, e tratar a questão da nota de curadoria
antes de medir fidelidade. Nenhuma destas ações foi tomada nesta tarefa.
