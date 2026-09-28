# Unified RAG Baseline — Interactive Smoke Test

## 1. Purpose

Verificar **qualitativamente** que o pipeline RAG funciona de ponta a ponta sobre o
corpus unificado (8 PDF + 24 Web) antes de construir o dataset de avaliação.

**Isto não é uma avaliação formal.** Não há ground truth, relevance judgements,
Precision/Recall/F1@k, MRR, nDCG, LLM-as-Judge nem comparação RAG vs No-RAG.
Também não houve tuning, reranking, MMR, hybrid search nem deduplicação. As
observações abaixo são manuais e servem para orientar a fase seguinte.

Script: `d2_rag/scripts/rag_baseline.py`. Testes: `d2_rag/tests/test_rag_baseline.py`.

```bash
uv run python d2_rag/scripts/rag_baseline.py --rebuild                  # (re)constrói a baseline
uv run python d2_rag/scripts/rag_baseline.py                            # modo interativo
uv run python d2_rag/scripts/rag_baseline.py --question "..."           # uma pergunta
uv run python d2_rag/scripts/rag_baseline.py --question "..." --retrieval-only   # sem LLM
uv run python d2_rag/scripts/rag_baseline.py --question "..." --show-context     # mostra o prompt
```

## 2. Corpus

| Item | Valor |
|---|---:|
| Documentos | 32 (8 PDF, 24 Web) |
| Chunks em `data/chunks/chunks.jsonl` | 330 (206 PDF, 124 Web) |
| **Chunks indexados** (`unit_role == "content"`) | **317** |
| Excluídos: `page_labels` / `caption_panel` | 11 / 2 (continuam em `chunks.jsonl`) |

## 3. Configuration

Todos os valores são **TEMPORARY BASELINE / TO BE EVALUATED**.

| Parâmetro | Valor |
|---|---|
| Embedding model | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` via `HuggingFaceEmbeddings` (`normalize_embeddings=True`) |
| Dimensão | **768** (verificada) |
| `max_seq_length` do modelo | **128 tokens** (ver §11) |
| Texto embebido | só `chunk["text"]` (= `heading_context` + corpo); a metadata não é embebida |
| Vector store | Chroma 1.5.9 (`langchain-chroma` 1.1.0), `data/chroma_baseline/` (git-ignored) |
| Collection | `coimbra_rag_baseline` |
| Métrica | **cosine**, configurada explicitamente (`collection_configuration={"hnsw": {"space": "cosine"}}`) e verificada |
| Score mostrado | **cosine distance** (menor = mais próximo), devolvida por `similarity_search_with_score`. Foi verificado que é igual a `1 − cos(q, d)`. A similaridade é mostrada como `1 − distance`. |
| Retrieval | similarity search simples, **top_k = 3**, sem filtros, threshold, MMR ou reranking |
| LLM | Ollama `llama3.2:3b` (instalado; verificado antes de cada execução) |
| Temperature | 0.1 |
| Memória | nenhuma: cada pergunta é independente |

**Dependências:** nenhuma nova. `langchain-chroma`, `langchain-huggingface`,
`langchain-ollama` e `sentence-transformers` já estavam no `pyproject.toml`.

## 4. Vector Store Build

```text
Expected input chunks: 330
Indexed chunks: 317
Excluded caption_panel: 2
Excluded page_labels: 11
Collection 'coimbra_rag_baseline' count: 317
```

A validação é feita pelo script (e aborta se falhar) e confirmada lendo a base:

| Verificação | Resultado |
|---|---|
| IDs = `chunk_id` (1:1) | 317 IDs únicos = os 317 `chunk_id` de conteúdo |
| Roles indexados | só `content` |
| Documento guardado = `chunk["text"]` | ✓ os 317 |
| Métrica | `cosine` |
| Metadata PDF | `universidade…::c0013` → `section_path=["1. UNIVERSIDADE…", "TORRE"]`, `source_pages=[10, 11]` |
| Metadata Web | `web-visitecoimbra-museus::c0007` → `url`, `canonical_url`, `conflict_notes` |
| Base em falta | `ERROR Baseline vector store not found. Run with --rebuild.` (exit 2, sem rebuild automático) |

**Metadata no Chroma.** O Chroma 1.5.9 aceita listas nativamente, por isso
`source_pages` e `section_path` são guardados como listas, sem serialização. Os
valores `None` são descartados pelo Chroma: um campo **ausente** significa `null`
(por exemplo, os chunks Web não têm `source_pages`, e os PDF não têm `url`).

**`--rebuild`** apaga e recria apenas `data/chroma_baseline/`. A
`data/chroma_smoke/` (primeiro smoke test) nunca é aberta.

## 5. Retrieval + Generation Pipeline

```text
Question
  → query embedding (mesmo modelo)
  → Chroma (cosine) → top-3 chunks + cosine distance
  → contexto: [Fonte 1..3] com documento, secção, páginas/URL e texto do chunk
  → nota separada de conflitos (se algum chunk tiver conflict_notes), como metadados de curadoria
  → Ollama llama3.2:3b (system prompt em PT-PT: só contexto; frase fixa de insuficiência; explicitar divergências)
  → ANSWER + SOURCES (PDF: páginas; Web: canonical_url)
```

## 6. Manual Questions

> **Execução inválida detetada e repetida.** Na primeira execução as perguntas
> foram passadas por pipe para o modo interativo. No Windows, o `input()` leu o
> stdin com a codificação da consola (cp1252), e as perguntas com acentos
> chegaram corrompidas ("O que sÃ£o as RepÃºblicas"). Isso deu falsas falhas de
> retrieval (Repúblicas, Canção). **Corrigido:** o stdin passa a ser lido em UTF-8
> quando não é uma consola. Os resultados abaixo são da **segunda execução**, com
> as perguntas verificadas como intactas.

| # | Pergunta | Top-3 (cosine distance) | Resposta | Observação |
|---|---|---|---|---|
| 1 | Em que ano ficou concluída a construção da Biblioteca Joanina? | joanina c0002 *Biblioteca Joanina* (0.263); joanina c0001 (0.312); joanina c0004 *Piso Nobre* (0.357) | "1728" | ✅ |
| 2 | Porque existem morcegos na Biblioteca Joanina? | joanina c0005 *Piso Nobre* (0.243); c0007; c0004 | "contribuem para o controle de pragas" | ✅ (no smoke test PDF anterior a resposta tinha uma causa inventada) |
| 3 | Quem projetou o Portugal dos Pequenitos? | fundacao c0009 *7. PORTUGAL DOS PEQUENITOS* (0.247); pequenitos c0011 *6. PORTUGAL DOS PEQUENITOS* (0.270); pequenitos c0004 | "Cassiano Branco" | ✅; ranks 1–2 são o **mesmo texto** em 2 PDFs (§8) |
| 4 | Em que ano foi fundado o Mosteiro de Santa Cruz? | fundacao c0007 *6. MOSTEIRO DE SANTA CLARA-A-VELHA* (0.249); heranca web *Igreja de Santa Cruz \| Panteão Nacional* (0.256); museus web *Mosteiro de Santa Clara-a-Velha* (0.267) | abstém-se | ❌ **falha de retrieval**: os chunks com "1131" ficam em rank 5 (fundacao c0002) e 12 (UC c0051). "Mosteiro" puxa Santa **Clara**. O chunk web recuperado só diz "século XII", por isso a abstenção é defensável. |
| 5 | Quem foi Sesnando David? | sesnando web c0001 (0.345), c0003, c0002 | líder moçárabe, escolhido por Fernando Magno, reconquista de Coimbra em 1064 | ✅ **só Web** |
| 6 | Que doces tradicionais posso encontrar em Coimbra? | docaria web c0002 (0.194); *Crúzios*; *Arrufada de Coimbra* | lista: Pastel de Santa Clara, arrufadas, pães doces, fofos, queijadas, Crúzios | ✅ todos os doces estão no contexto (verificado); **só Web** |
| 7 | O que são as Repúblicas de Coimbra? | republicas web c0001 (0.251); republicas web c0003 *Lista das Repúblicas*; fado c0011 *5. REAL REPÚBLICA RÁS-TE-PARTA…* | "comunidades autogeridas por estudantes…" + exemplos da lista | ✅ Web + PDF |
| 8 | Que museus posso visitar em Coimbra? | museus web c0001 (0.196); museus web *Centro de Arte Contemporânea*; pequenitos c0013 | Machado de Castro, Torre de Almedina, Museu da Água, Santa Clara-a-Velha, Portugal dos Pequenitos ("parque temático") | ⚠️ parcial por natureza: o top-3 não cobre 23 museus |
| 9 | Qual é a origem da Canção de Coimbra? | cancao web c0005 (0.342, frase final de 98 caracteres); cancao web c0001 (0.388); fado c0022 | abstém-se | ❌ **falha de geração**: c0001 contém "Desde o século XVI, há registos de estudantes que… cantavam", mas o modelo não o usou. O rank 1 foi um chunk curto e genérico. |
| 10 | Que relação existe entre Pedro e Inês e Coimbra? | pedro-e-ines web c0005 *Jardins da Quinta das Lágrimas* (0.353); c0006 *Mosteiro de Santa Clara-a-Velha*; c0001 | refúgio no Paço de Santa Clara, Quinta das Lágrimas | ✅ ("Paço de Santa Clara" está na fonte) |
| D | O que é o Paço das Escolas? | fado c0005 *2. PAÇO DAS ESCOLAS* (0.500); fado c0001 *1. ASSOCIAÇÂO ACADÉMICA*; fado c0008 *2. PAÇO DAS ESCOLAS* | complexo com Sala dos Capelos, Archeiros…, Património Mundial desde 2013 | ✅ resposta aceitável, mas com distâncias altas (0.50+) |

## 7. Web Coverage Examples

A expansão Web respondeu a perguntas que o corpus PDF não cobria ou cobria mal:

- **Sesnando David (Q5):** os 3 chunks são da página Web; o corpus PDF só o menciona
  de passagem.
- **Doçaria (Q6):** os 3 chunks vêm da Doçaria Conventual Web (categoria
  `gastronomy`, sem nenhum PDF).
- **Repúblicas (Q7):** o rank 1 e o 2 são da página Web (definição + lista das 20
  repúblicas), complementados por um PDF.
- **Museus (Q8):** a introdução e as fichas Web.
- **Pedro e Inês (Q10):** os 3 chunks são Web e ligam a lenda a lugares concretos.
- **Canção de Coimbra (Q9):** o retrieval trouxe a página Web certa; a falha foi da
  geração.

## 8. Duplicate Retrieval Example

**Portugal dos Pequenitos (Q3).** O rank 1 (`fundacao-da-nacionalidade::c0009`) e
o rank 2 (`coimbra-para-os-pequenitos::c0011`) são **o mesmo texto** em dois PDFs
municipais (duplicação M5 medida no chunking). Um dos 3 lugares do contexto é
gasto numa cópia, ou seja, **há perda de diversidade**. A resposta estava certa
porque a informação cabia num só chunk.

**Paço das Escolas (D).** Os 3 resultados vêm do **mesmo documento** (Fado).
As cópias conhecidas em Viver o Património e na brochura UC não aparecem no top-3,
por isso aqui a duplicação entre documentos não se manifestou. As distâncias altas
(≥ 0.50) indicam um match fraco para uma pergunta de definição.

Nada foi corrigido: são registos para a fase de avaliação.

## 9. Conflict Example

**Pergunta:** "Quem fundou o Mosteiro de Santa Clara-a-Velha e quando?"

| Rank | Chunk | Fonte | Formulação |
|---|---|---|---|
| 1 (0.227) | `fundacao-da-nacionalidade::c0007` | PDF | "Fundado em 1283, por D. Mor Dias…" (refundação pela Rainha Santa Isabel em 1314) |
| 2 (0.236) | `web-visitecoimbra-museus::c0007` | Web | "mandado construir em 1314 por D. Isabel de Aragão…" (com `conflict_notes`) |
| 3 (0.273) | `web-visitecoimbra-heranca-cultural-e-religiosa::c0003` | Web | "Fundado pela Rainha Santa Isabel…" (com `conflict_notes`) |

- **PDF e Web recuperados**, com as três formulações no contexto.
- A nota de curadoria foi enviada **separada** do contexto e identificada como
  "não é conteúdo das fontes".
- **O modelo identificou a divergência:** citou a Fonte 1 (1283, D. Mor Dias), a
  Fonte 2 (1314, D. Isabel de Aragão, "substituindo um pequeno convento de monjas
  clarissas fundado em 1286") e a Fonte 3 (Rainha Santa Isabel, sem data). Não
  escolheu nenhuma, como pedido. Terminou com a frase de insuficiência, o que é
  prudente mas um pouco redundante depois de ter exposto as versões.

## 10. Out-of-Knowledge Example

**Pergunta:** "Qual foi o preço do bilhete para um jogo da Académica no Estádio
Cidade de Coimbra em 2025?"

- **Retrieval:** chunks só vagamente relacionados (Praça das Cortes, Praça da
  Canção, Parque Dr. Manuel Braga), com as distâncias mais altas da sessão
  (**0.478–0.529**).
- **Resposta:** "Não tenho informação suficiente no contexto disponível para
  responder com segurança", acrescentando que o contexto não menciona o estádio nem
  preços. ✅ Sem invenção.

## 11. Known Problems

Observados, **não corrigidos**:

| Problema | Tipo | Evidência |
|---|---|---|
| **Truncagem do embedding.** O modelo tem `max_seq_length = 128` tokens. **222 dos 317 chunks (70%) excedem-no** (mediana 164 tokens, máximo 285), e **29% dos tokens do corpus não chegam ao embedding**. O contexto de headings (mediana 21 tokens) cabe sempre, mas o fim dos chunks longos não é visto pelo retrieval. | Retrieval (configuração) | Medido com o tokenizer do modelo |
| Santa Cruz: "Mosteiro" puxa Santa Clara; os chunks com o facto ficam em rank 5 e 12 | Falha de retrieval | Q4 |
| Chunks curtos e genéricos ganham rank (frase final de 98 caracteres da Canção em rank 1) | Retrieval | Q9 |
| O modelo abstém-se apesar de o contexto conter a resposta | Falha de geração | Q9 |
| Duplicação PDF↔PDF consome lugares do top-3 | Diversidade | Q3 |
| Perguntas de enumeração ("que museus…") ficam parciais com top-3 | Limite de `top_k` | Q8 |
| Match fraco em perguntas de definição sobre secções com subentradas (distâncias ≥ 0.50) | Retrieval | Paço das Escolas |
| Resposta ao conflito termina com uma abstenção redundante | Geração | §9 |
| **Bug corrigido:** stdin em pipe no Windows corrompia perguntas com acentos | Implementação | §6 |

**Integridade da `chroma_smoke`.** Os hashes foram registados antes e depois (e
também depois de correr os testes): **sem alterações** nesta tarefa.

## 12. Decision

**IS THE UNIFIED RAG PIPELINE OPERATIONAL END-TO-END?**

# YES

**Justificação:**
- **Build:** a base foi construída, validada e é reproduzível a partir de `chunks.jsonl` (317/317, 1:1, cosine).
- **Consulta:** as perguntas usam a base existente sem recalcular o corpus. O retrieval mostra distâncias com o nome correto e proveniência PDF/Web, e o LLM responde com base no contexto.
- **Comportamento:** a recusa fora do conhecimento funciona, e o conflito conhecido foi exposto sem ser resolvido.
- **Resultados:** 10 das 13 perguntas foram respondidas corretamente (incluindo o conflito e a recusa fora do conhecimento); a Q8 foi parcial por natureza. As 2 falhas (Q4 retrieval, Q9 geração) estão diagnosticadas.
- **Testes:** 89 testes OK, sem Ollama, rede nem modelo.

"Operational" **não** significa "bom". A qualidade do retrieval é justamente o
objeto da avaliação formal seguinte. A truncagem a 128 tokens (§11) é a primeira
hipótese a medir.
