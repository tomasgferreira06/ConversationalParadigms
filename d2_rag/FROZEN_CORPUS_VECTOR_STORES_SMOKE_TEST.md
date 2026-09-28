# Frozen Corpus — Vector Stores Rebuild & Smoke Test

Data: 2026-09-28. Corpus: snapshot congelado depois de `WEB_CONTENT_CARD_FIX_REPORT.md`.
**Smoke test qualitativo, não avaliação formal**: não há métricas, relevance judgements nem
vencedor.

## 1. Purpose

As stores dos smoke tests anteriores (`chroma_baseline`, `_v1`, `_v2`, e a `chroma_smoke`,
mais antiga) indexam o corpus anterior de **317** content chunks. O corpus congelado tem **348**:
inclui os cards recuperados e três páginas novas. Em vez de reconstruir essas stores, o que
invalidaria os relatórios históricos, foram criadas **três stores novas**, uma por solução de
embedding, todas a partir do mesmo `chunks.jsonl`. As stores históricas ficaram intactas
(secção 16).

## 2. Frozen Corpus Snapshot

Verificado antes de qualquer alteração (coincide com o esperado):

| | |
|---|---:|
| Documentos | 35 |
| — PDF | 8 |
| — Web | 27 |
| Chunks | 361 |
| — content (indexados) | 348 (193 PDF + 155 Web) |
| — page_labels (excluídos) | 11 |
| — caption_panel (excluídos) | 2 |

## 3. Configurations

`scripts/rag_pipeline.py`: três `RAGConfig` novas e explícitas, cada uma derivada da versão
histórica com `dataclasses.replace`, mudando **só** `collection_name` e `store_dir`. Não há
herança, factories nem ficheiros de configuração.

| | FROZEN_V0 | FROZEN_V1 | FROZEN_V2 |
|---|---|---|---|
| Derivada de | `BASELINE_V0` | `BASELINE_V1` | `BASELINE_V2` |
| Embedding model | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | `sentence-transformers/all-mpnet-base-v2` | `Qwen/Qwen3-Embedding-0.6B` |
| Dimensão | 768 | 768 | 1024 |
| Query prompt | None | None | `prompt_name="query"` (só queries) |
| normalize_embeddings | True | True | True |
| Store | `data/chroma_frozen_v0/` | `data/chroma_frozen_v1/` | `data/chroma_frozen_v2/` |
| Collection | `coimbra_rag_frozen_v0` | `coimbra_rag_frozen_v1` | `coimbra_rag_frozen_v2` |
| Distance | cosine | cosine | cosine |
| top_k | 3 | 3 | 3 |
| Roles indexados | content | content | content |
| Texto embebido | `chunk["text"]` | `chunk["text"]` | `chunk["text"]` |
| LLM / temperatura | llama3.2:3b / 0.1 | llama3.2:3b / 0.1 | llama3.2:3b / 0.1 |

`SYSTEM_PROMPT`, construção do contexto, fontes e `conflict_notes` não mudaram (o código não foi
tocado; há testes que o confirmam). `BASELINE_V0/V1/V2` mantêm os paths e collections
históricos.

Alterações ao código:

- `CONFIGS = {"frozen-v0", "frozen-v1", "frozen-v2"}`: as únicas configurações selecionáveis
  na CLI. As históricas não são selecionáveis, portanto nenhum `--rebuild` as pode apagar.
- O alias `BASELINE` (valor por omissão das funções do pipeline e da CLI) passou de
  `BASELINE_V2` para `FROZEN_V2`. Os valores são os mesmos exceto a store. Antes, um simples
  `rag_baseline.py --rebuild` apagaria a store histórica `chroma_baseline_v2`; agora já não.
- `rag_baseline.py`: nova opção `--config`, e a configuração escolhida passa a ser usada em
  `load_embeddings`, `build_store`, `open_store`, `retrieve(k=top_k)`, `check_ollama` e
  `generate`. Não há scripts duplicados.
- `.gitignore`: os três diretórios `d2_rag/data/chroma_frozen_v*/`.

## 4. Build

```
uv run python d2_rag/scripts/rag_baseline.py --config frozen-v0 --rebuild
uv run python d2_rag/scripts/rag_baseline.py --config frozen-v1 --rebuild
uv run python d2_rag/scripts/rag_baseline.py --config frozen-v2 --rebuild
```

Consulta (sem rebuild): `rag_baseline.py --config frozen-vN [--question "..."] [--retrieval-only]`.

| | Input | Indexed | Excluded | Count | Tempo (CPU, inclui carregar o modelo) | Tamanho |
|---|---:|---:|---|---:|---:|---:|
| FROZEN_V0 | 361 | 348 | 11 page_labels, 2 caption_panel | 348 | ≈ 1 min 43 s | 4.7 MB |
| FROZEN_V1 | 361 | 348 | 11 page_labels, 2 caption_panel | 348 | ≈ 2 min 46 s | 4.7 MB |
| FROZEN_V2 | 361 | 348 | 11 page_labels, 2 caption_panel | 348 | ≈ 49 min 57 s | 5.2 MB |

Os tempos são wall clock, tirados dos timestamps dos logs. O V2 (Qwen em bf16 no CPU) correu em
parte ao mesmo tempo que a validação V0/V1 e o smoke V1, por isso o valor está inflacionado. O
histórico foi ~36 min para 317 chunks. Cada store reconstrói-se individualmente, e o
`build_store` só apaga o `store_dir` da própria configuração.

## 5. Vector Store Validation

Validação direta nas collections Chroma, em modo de leitura, contra `chunks.jsonl`:

| Verificação | V0 | V1 | V2 |
|---|---|---|---|
| Collections na store | só `coimbra_rag_frozen_v0` | só `coimbra_rag_frozen_v1` | só `coimbra_rag_frozen_v2` |
| count / embeddings | 348 / 348 | 348 / 348 | 348 / 348 |
| Dimensão | 768 | 768 | 1024 |
| IDs = os 348 `chunk_id` content; únicos | ✅ | ✅ | ✅ |
| hnsw space | cosine | cosine | cosine |
| documents = `chunk["text"]` | ✅ | ✅ | ✅ |
| metadata = `to_metadata(chunk)` | ✅ | ✅ | ✅ |
| Só `unit_role == content` | ✅ | ✅ | ✅ |
| PDF com `source_pages` (193) / Web com `url` (155) | ✅ | ✅ | ✅ |
| Norma dos vetores | 1.0000 | 1.0000 | 0.998–1.004 (bf16) |
| Vetor guardado = `encode(texto, normalize)` sem prompt | máx. diferença 7e-9 | 7e-8 | ver §5.1 |
| `embed_query` = `encode(q, normalize)` sem prompt | diferença 0.0 | 0.0 | não, usa o prompt (§5.1) |

### 5.1 V2: query vs document

- **Queries**: `embed_query(q)` = `encode(q, prompt_name="query", normalize_embeddings=True)`,
  com diferença máxima de **0.0**. O prompt é o do próprio modelo: `"Instruct: Given a web search
  query, retrieve relevant passages that answer the query\nQuery:"`. Sem prompt, a diferença
  seria 0.066.
- **Documentos**: sem prompt. O modelo tem `default_prompt_name = None`. Para ter uma prova exata
  apesar do bf16, reproduzi um lote de build completo (32 chunks, com a mesma ordenação por
  comprimento do sentence-transformers). `encode(texto, normalize_embeddings=True)` sem prompt
  dá **coseno 1.000000 e diferença máxima 1.5e-8** face aos vetores guardados. O mesmo lote com
  `prompt_name="query"` dá coseno mínimo 0.970. Os documentos não levam instrução.
- Nota técnica: o `HuggingFaceEmbeddings` do LangChain substitui `"\n"` por `" "` antes do
  `encode`, tanto em documentos como em queries. É comportamento da biblioteca, já estava
  presente em todas as stores anteriores e não foi alterado. Sem esta substituição e com lotes
  diferentes, o bf16 dá cosenos de 0.87–0.99 sem que isso seja um erro.

## 6. New Knowledge Smoke Questions

As mesmas 6 perguntas nas três configurações, cada uma independente e sem histórico de chat,
usando `retrieve` → `build_messages` → `generate` do pipeline sem alterações:

| Q | Pergunta |
|---|---|
| Q1 | Que cervejarias existem em Coimbra? |
| Q2 | Onde posso ouvir Fado de Coimbra? |
| Q3 | Onde posso sair à noite em Coimbra? |
| Q4 | Que opções de restauração existem em Coimbra? |
| Q5 | Que atividades desportivas posso fazer em Coimbra? |
| Q6 | Onde posso comprar ou conhecer cerâmica tradicional de Coimbra? |

Estas perguntas não são um evaluation dataset. Só confirmam o caminho completo
raw → processed → chunks → embeddings → retrieval → RAG.

## 7. Retrieval Comparison

Top-3 por configuração: `chunk_id` (sem o prefixo `web-visitecoimbra-`), secção e cosine
distance. **As distâncias não são comparáveis entre modelos**; a comparação faz-se apenas por
ranks, chunks recuperados e cobertura.

| Q | V0 top-3 | V1 top-3 | V2 top-3 |
|---|---|---|---|
| Q1 | 1. cerveja::c0002 (lista dos 4 cards) 0.174 · 2. cerveja::c0001 0.208 · 3. ceramica::c0005 (Lojas da Baixa) 0.266 | 1. cerveja::c0001 (narrativa) 0.281 · 2. coimbra-dos-estudantes::c0003 0.283 · 3. coimbra-dos-escritores::c0004 (Parque Dr. Manuel Braga) 0.284 | 1. cerveja::c0002 0.167 · 2. cerveja::c0001 0.186 · 3. restauracao::c0004 (Cervejaria Almedina/Praxis) 0.214 |
| Q2 | 1. coimbra-by-night::c0004 (Casas para ouvir…) 0.303 · 2. cancao::c0006 (Casas para ouvir…) 0.309 · 3. viver-o-patrimonio::c0015 (9. Largo do Romal) 0.389 | 1. cancao::c0003 0.301 · 2. cancao::c0006 (Casas para ouvir…) 0.305 · 3. cancao::c0005 0.308 | 1. cancao::c0006 0.188 · 2. coimbra-by-night::c0004 0.194 · 3. fado-e-tradicoes-academicas::c0021 0.267 |
| Q3 | 1. by-night::c0003 (10 locais…) 0.191 · 2. by-night::c0002 (10 locais…) 0.193 · 3. by-night::c0001 (intro) 0.242 | 1. cancao::c0005 0.326 · 2. viver-o-patrimonio::c0025 (17. Praça 8 de Maio) 0.337 · 3. coimbra-dos-escritores::c0009 (5. Penedo da Saudade) 0.338 | 1. by-night::c0001 0.190 · 2. by-night::c0002 0.202 · 3. by-night::c0003 0.211 |
| Q4 | 1. ceramica::c0005 (Lojas da Baixa) 0.352 · 2. restauracao::c0001 (intro) 0.366 · 3. viver-o-patrimonio::c0028 0.372 | 1. restauracao::c0001 0.176 · 2. restauracao::c0002 0.209 · 3. restauracao::c0003 0.223 | 1. restauracao::c0001 0.255 · 2. restauracao::c0003 0.259 · 3. restauracao::c0008 0.273 |
| Q5 | 1. desporto::c0006 (10 atividades) 0.154 · 2. desporto::c0005 (10 atividades) 0.192 · 3. desporto::c0004 0.239 | 1. desporto::c0006 0.270 · 2. desporto::c0007 0.305 · 3. coimbra-dos-estudantes::c0003 0.327 | 1. desporto::c0005 0.129 · 2. desporto::c0006 0.134 · 3. desporto::c0001 0.158 |
| Q6 | 1. ceramica::c0005 (Lojas da Baixa) 0.277 · 2. ceramica::c0003 (Refeitro) 0.333 · 3. ceramica::c0004 (Carlos Tomás) 0.354 | 1. ceramica::c0004 (Carlos Tomás) 0.190 · 2. ceramica::c0003 (Refeitro) 0.199 · 3. ceramica::c0005 (Lojas da Baixa) 0.231 | 1. ceramica::c0005 (Lojas da Baixa) 0.187 · 2. cerveja::c0002 0.266 · 3. cerveja::c0001 0.299 |

Documento Web certo no rank 1: V0 5/6 (falha na Q4), V1 4/6 (falha na Q1, o rank 1 é a
narrativa da cerveja sem nomes, e falha na Q3), V2 6/6. Esta é uma leitura descritiva, não uma
métrica.

## 8. RAG Answers

| Q | V0 | V1 | V2 |
|---|---|---|---|
| Q1 | ✅ os 4 cards | ❌ "não há uma lista específica" (o retrieval não trouxe os nomes) | ✅ os 4 cards + Cervejaria Almedina + Cervejaria Praxis |
| Q2 | ✅ as 3 casas | ✅ as 3 casas, com descrição | ✅ as 3 casas |
| Q3 | ⚠️ 8/10 locais + **falsa divergência** ("formulações divergentes") | ❌ "Não tenho informação suficiente" (retrieval falhou) | ✅ 10/10 locais |
| Q4 | ⚠️ só tipos genéricos (tascas, cafés…); nenhum estabelecimento | ✅ tipos + 6 nomes (A Taberna … Briosa) | ✅ tipos + 12 nomes |
| Q5 | ✅ as 10 atividades + São Silvestre | ⚠️ 3 atividades + locais listados como se fossem "atividades"; afirma erradamente que o futebol "não pode ser praticado"; "puedes" | ✅ as 10 atividades + Choupal, Vale de Canas |
| Q6 | ✅ os 3 locais (com uma ressalva cautelosa sobre o Refeitro) | ⚠️ Lojas da Baixa + Refeitro; omite Carlos Tomás apesar de estar no contexto | ⚠️ só as Lojas da Baixa (o retrieval só trouxe esse item) |

Todos os nomes de estabelecimentos citados nas respostas existem no contexto recuperado
(verificado automaticamente nas Q1, Q3 e Q4); não foram detetados nomes inventados. Em nenhuma
das 18 execuções houve nota de `conflict_notes` no prompt.

## 9. Beer / Breweries

- **V0 e V2** recuperam `cerveja::c0002`, o chunk com a lista BREW! / Epicura / Portuguese Pedro
  / Praxis, no rank 1. O **V2** traz ainda, no rank 3, `restauracao::c0004` com
  "Cervejaria Almedina" e "Cervejaria Praxis": 6/6 entidades no top-3 e na resposta.
- **V1** recupera só a narrativa (`c0001`) e dois chunks sem relação. O LLM responde
  corretamente que o contexto não nomeia cervejarias. É uma falha de **retrieval**, não de
  geração.

## 10. Fado

As três configurações recuperam a lista "Casas para ouvir a Canção de Coimbra" e as três
respostas nomeiam Fado ao Centro, À Capella e Café Santa Cruz. No V0 e no V2, o top-3 tem os
dois chunks **idênticos** da fonte (`cancao-de-coimbra::c0006` = `coimbra-by-night::c0004`,
duplicação já documentada no relatório do fix), que ocupam 2 dos 3 lugares. Registado; não
foi deduplicado.

## 11. Nightlife

- **V0** e **V2**: os 3 chunks de Coimbra by Night. V2 cita os 10 locais; V0 cita 8 e acrescenta
  uma falsa "divergência" entre fontes que só listam locais diferentes (ver §15).
- **V1**: nenhum chunk da página, e responde que não tem informação. É uma falha de retrieval.
- Os rooftops (`by-night::c0005`) não entram no top-3 de nenhuma configuração, por causa do
  limite de top_k=3 com uma pergunta aberta.

## 12. Restaurants

Como era de esperar com top_k=3, nenhuma configuração enumera os 70 estabelecimentos.
- **V1** e **V2**: 3/3 chunks de `web-visitecoimbra-restauracao`, com 6 e 12 estabelecimentos
  no contexto, respetivamente, todos citados corretamente.
- **V0**: só a introdução da página (rank 2), com o chunk das Lojas de artesanato em rank 1 e um
  chunk PDF em rank 3. A resposta fica genérica, sem nomes.

## 13. Sport

- **V2**: c0005 + c0006 (as 10 atividades) + intro, e a resposta lista as 10 atividades e os
  espaços (Choupal, Vale de Canas, campos do Mondego).
- **V0**: as 10 atividades + a São Silvestre.
- **V1**: c0006 + c0007 (só as atividades 8–10 e a AAC). A resposta mistura locais com
  atividades e faz uma afirmação errada sobre o futebol. É um problema de **retrieval**
  (contexto parcial) combinado com **geração**.

## 14. Ceramics

- **V0** e **V1**: os 3 itens (Lojas da Baixa, Refeitro, Carlos Tomás). V1 omite Carlos Tomás
  na resposta: problema de **geração**.
- **V2**: só as Lojas da Baixa. Nos ranks 2 e 3 aparecem os chunks da cerveja, provavelmente
  por "tradicional"/"artesanal"; é uma hipótese, não verificada. Refeitro e Carlos Tomás são
  chunks de ~100 caracteres (limitação já registada no relatório do fix: secções curtas de
  accordion), e a V2 coloca-os abaixo do top-3.

## 15. Known Issues

Documentados apenas. Nada foi corrigido: o corpus, o k, o prompt e a geração não mudaram.

| # | Problema | Camada | Onde |
|---|---|---|---|
| 1 | Chunks idênticos da fonte ocupam 2 dos 3 lugares do top-3 | retrieval (duplicação no corpus) | Q2 V0, V2 |
| 2 | top_k=3 não chega para perguntas de enumeração abertas (70 restaurantes, 10 bares + 6 rooftops) | retrieval (k) | Q3, Q4 |
| 3 | Chunks curtos de entidades (Refeitro, Carlos Tomás) competem mal | retrieval / chunking | Q6 V2 |
| 4 | Documento certo ausente do top-3 | retrieval | V1 Q1 e Q3; V0 Q4 |
| 5 | Chunk irrelevante recuperado (Lojas de artesanato para cervejarias/restauração; cerveja para cerâmica) | retrieval | Q1/Q4 V0, Q6 V2 |
| 6 | Falsa "divergência" entre fontes sem conflito real | geração | Q3 V0 (o mesmo padrão dos relatórios anteriores) |
| 7 | Omissão de uma entidade presente no contexto | geração | Q6 V1 |
| 8 | Locais apresentados como atividades; afirmação errada sobre o futebol; palavra em espanhol ("puedes") | geração | Q5 V1 |
| 9 | O `conflict_notes` ao nível do documento não foi ativado neste smoke (não é objeto da tarefa) | — | — |

## 16. Tests / Integrity

**Testes**: `uv run python -m unittest discover -s tests` dá **123 OK** (eram 118). Não
descarregam modelos, não usam Ollama e não tocam em stores reais (mocks, fake embeddings e
`TemporaryDirectory`). Testes novos ou alterados em `tests/test_rag_baseline.py`:

- as configurações históricas V0/V1/V2 mantêm-se exatamente iguais (paths e collections
  históricos);
- `FROZEN_V0/V1/V2` são `replace(BASELINE_Vx)` e diferem só em collection e store; o modelo e a
  dimensão implícita são os mesmos;
- V2 usa `query_prompt_name="query"` (`query_encode_kwargs`) e V0/V1 não usam prompt (mock do
  `HuggingFaceEmbeddings`);
- as 6 collections são únicas; as 7 stores (incluindo `chroma_smoke`) não coincidem nem estão
  aninhadas;
- `CONFIGS` contém só as configurações frozen, `BASELINE is FROZEN_V2`, e nenhuma store da CLI é
  histórica;
- `--config frozen-v0 --rebuild` usa só a `FROZEN_V0` (com `build_store` mockado);
- as 6 configurações selecionam 348 chunks e excluem 11 + 2;
- `SYSTEM_PROMPT`, `llama3.2:3b` e a temperatura 0.1 estão inalterados (testes existentes).

Compile/import OK.

**Integridade**: SHA-256 de 111 ficheiros guardados antes de qualquer alteração e reverificados
no fim: **111/111 byte-identical**.

| Artefacto | Estado |
|---|---|
| raw PDF (8), processed PDF (8), raw Web (27), processed Web (27) | inalterados |
| `manifest.jsonl`, `chunks.jsonl`, `chunk_stats.json`, `approved_urls.jsonl` | inalterados |
| `chroma_smoke`, `chroma_baseline`, `chroma_baseline_v1`, `chroma_baseline_v2` (20 ficheiros) | inalterados; nunca abertos |
| Relatórios `.md` existentes (incluindo os smoke tests históricos e o do fix) | inalterados |

Alterações desta tarefa: `scripts/rag_pipeline.py`, `scripts/rag_baseline.py`,
`tests/test_rag_baseline.py` e `.gitignore`. Criados: `data/chroma_frozen_v0|v1|v2/` (ignorados
pelo git) e este relatório. Os scripts do smoke e da validação ficaram fora do repositório.

## 17. Decision

ARE ALL THREE RETRIEVAL CONFIGURATIONS READY FOR FORMAL EVALUATION? **YES**

As três stores estão construídas sobre o mesmo corpus congelado, com 348/348 chunks, dimensões,
métrica, documentos, metadata e tratamento de query/document validados. O conhecimento novo é
acessível de ponta a ponta. As diferenças qualitativas acima são precisamente o que a avaliação
formal deve medir, e não são defeitos de construção.

IS THE CORPUS STILL FROZEN AND UNCHANGED? **YES**
