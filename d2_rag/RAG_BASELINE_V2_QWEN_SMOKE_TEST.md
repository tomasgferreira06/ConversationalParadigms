# RAG Baseline V2 — Qwen3 Embedding

Data: 2026-09-28. Relatórios anteriores (inalterados): `RAG_BASELINE_SMOKE_TEST.md` (V0) e
`RAG_BASELINE_V1_SMOKE_TEST.md` (V1).

**Isto não é uma avaliação formal.** Não há ground truth, relevance judgements,
Precision/Recall/F1@k, MRR, nDCG nem LLM-as-Judge. São as mesmas 13 perguntas de smoke
test, com observação manual. Não há tuning, reranking, MMR, hybrid retrieval, threshold
nem deduplicação.

## 1. Motivation

| Versão | Embedding model | Papel |
|---|---|---|
| V0 | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | primeira baseline (MPNet multilingue) |
| V1 | `sentence-transformers/all-mpnet-base-v2` | alinhada com a worksheet da disciplina |
| **V2** | **`Qwen/Qwen3-Embedding-0.6B`** | candidato moderno, multilingue e *instruction-aware*, para retrieval em português |

Na V1 observaram-se regressões de retrieval em perguntas em português (Pequenitos, Santa
Cruz, Doçaria, Santa Clara). A V2 testa se um modelo de embeddings recente e multilingue
muda esse comportamento, **alterando apenas a solução de embeddings**.

## 2. Model Integration

| Item | Valor (verificado no modelo carregado) |
|---|---|
| Modelo | `Qwen/Qwen3-Embedding-0.6B` via `SentenceTransformer` (módulos `Transformer → Pooling → Normalize`) |
| Dimensão | **1024** (nativa; `truncate_dim = None`, sem Matryoshka/MRL) |
| Similaridade declarada pelo modelo | cosine |
| Prompts definidos pelo próprio modelo | `query` = "Instruct: Given a web search query, retrieve relevant passag…"; `document` = vazio; `default_prompt_name = None` |
| Documentos | `encode(chunk["text"], normalize_embeddings=True)`, **sem prompt** |
| Queries | `encode(question, prompt_name="query", normalize_embeddings=True)` |
| Normalização | `normalize_embeddings=True` em documentos e queries; Chroma com `cosine` |
| dtype | **bfloat16** (o dtype do config do modelo, carregado com o default do `transformers` 5; não forçado) |
| Dispositivo | CPU (não há CUDA; nem CUDA nem flash-attn foram instalados) |

**Integração com LangChain.** A versão instalada de `HuggingFaceEmbeddings`
(`langchain-huggingface` 1.2.2) tem o campo `query_encode_kwargs`, e o `embed_query` usa-o
em vez de `encode_kwargs` quando não está vazio. Por isso **não foi preciso wrapper**:

```python
HuggingFaceEmbeddings(
    model_name="Qwen/Qwen3-Embedding-0.6B",
    encode_kwargs={"normalize_embeddings": True},                              # embed_documents
    query_encode_kwargs={"normalize_embeddings": True, "prompt_name": "query"},  # embed_query
)
```

Em `rag_pipeline.load_embeddings`, o `query_encode_kwargs` só é passado quando
`config.query_prompt_name` está definido. A V0 e a V1 continuam a ser construídas
exatamente como antes (só `encode_kwargs`).

**Verificações no modelo real:**
- `embed_query(q)` é bit a bit igual a `encode([q], prompt_name="query",
  normalize_embeddings=True)` (diferença máxima 0.0);
- cosine entre a query com e sem prompt: 0.846, pelo que o prompt tem efeito real;
- a norma dos vetores é ~0.9999, e não 1.0 exato, devido à normalização em bf16. O espaço
  `cosine` do Chroma normaliza internamente, por isso isto é irrelevante para o ranking.

**Nota herdada da V0/V1 (não alterada):** o `HuggingFaceEmbeddings._embed` substitui `\n`
por espaço antes de codificar. Aplica-se igualmente às três versões. O documento guardado
no Chroma continua a ser o `chunk["text"]` original.

**Versões relevantes (sem upgrade necessário):**

| Pacote | Versão | Nota |
|---|---|---|
| `langchain-huggingface` | 1.2.2 | suporta `query_encode_kwargs` |
| `sentence-transformers` | 6.1.0 | suporta `prompt_name` |
| `transformers` | 5.17.0 | reconhece a arquitetura Qwen3 (`Qwen3Model`) |
| `torch` | 2.14.0 | CPU |
| `chromadb` / `langchain-chroma` | 1.5.9 / 1.1.0 | — |

`pyproject.toml` e `uv.lock` **não foram alterados**.

## 3. Configuration

O `RAGConfig` ganhou **um** campo genérico, `query_prompt_name: str | None`. A V2 está
escrita por extenso (não é derivada da V1) porque tem um valor específico do modelo.
`BASELINE = BASELINE_V2`.

| Parâmetro | V0 | V1 | **V2** |
|---|---|---|---|
| Embedding model | `paraphrase-multilingual-mpnet-base-v2` | `all-mpnet-base-v2` | **`Qwen/Qwen3-Embedding-0.6B`** |
| `query_prompt_name` | `None` | `None` | **`"query"`** |
| Dimensão | 768 | 768 | **1024** |
| Vector store | `data/chroma_baseline/` | `data/chroma_baseline_v1/` | **`data/chroma_baseline_v2/`** |
| Collection | `coimbra_rag_baseline` | `coimbra_rag_baseline_v1` | **`coimbra_rag_baseline_v2`** |
| Normalização / métrica | true / cosine | true / cosine | true / cosine |
| Chunks | 330 (317 `content`), 1000/100 chars | igual | igual (mesmo `chunks.jsonl`) |
| Texto embebido | `chunk["text"]` | igual | igual (sem instruction nos documentos) |
| Retrieval | similarity, top_k = 3 | igual | igual |
| LLM | `llama3.2:3b`, 0.1 | igual | igual |
| Prompt, contexto, fontes, `conflict_notes` | — | igual | igual |

`.gitignore`: acrescentado `d2_rag/data/chroma_baseline_v2/`.

## 4. Vector Store Build

```text
uv run python d2_rag/scripts/rag_baseline.py --rebuild      # ~36 min em CPU (bf16)

Expected input chunks: 330
Indexed chunks: 317
Excluded caption_panel: 2
Excluded page_labels: 11
Collection 'coimbra_rag_baseline_v2' count: 317 (…\d2_rag\data\chroma_baseline_v2)
```

Validação independente, lendo a base com o cliente `chromadb`:

| Verificação | Resultado |
|---|---|
| Collections na store V2 | só `coimbra_rag_baseline_v2` |
| Registos / embeddings | 317 / 317 |
| Dimensão | **1024** |
| IDs | = os 317 `chunk_id` de conteúdo, todos únicos |
| Métrica | `cosine` |
| Documentos | = `chunk["text"]` nos 317 |
| Metadata | = `to_metadata(chunk)` nos 317 |
| PDF / Web | todos os PDF com `source_pages` (ex.: `[10, 11]`); todos os Web com `url` e sem páginas |
| Roles | só `content` |
| Normas | 0.998–1.004 (bf16) |
| Vetores novos e sem prompt | 8 chunks reembebidos como documento: cosine ≥ 0.99990 com o vetor guardado. Os mesmos chunks com o prompt de query: ≤ 0.9835, o que confirma que os documentos foram embebidos **sem** instruction. Com 1024 dimensões, os vetores não podem ter sido copiados das bases de 768. |

A pequena diferença (0.9999 e não 1.0) vem de o bf16 em CPU não ser bit a bit estável
entre tamanhos de batch diferentes.

## 5. Repeated Smoke Test

As mesmas 13 perguntas, com a formulação exata dos relatórios anteriores (verificadas
intactas no output, sem problemas de codificação), cada uma independente. A distância é a
cosine distance e **não é comparável em valor absoluto entre modelos**.

| # | Pergunta | V2 top-3 (distância) | Resposta V2 | Estado |
|---|---|---|---|---|
| 1 | Em que ano ficou concluída a construção da Biblioteca Joanina? | joanina c0002 *Biblioteca Joanina* (0.159); UC c0016 *Casa da Livraria \| Biblioteca Joanina* (0.292); joanina c0004 *Piso Nobre* (0.350) | "1728" | ✅ |
| 2 | Porque existem morcegos na Biblioteca Joanina? | joanina c0005 *Piso Nobre* (0.219); c0002 (0.344); c0004 (0.356) | "contribuem para o controle de pragas" (citação) | ✅ |
| 3 | Quem projetou o Portugal dos Pequenitos? | fundacao c0009 *7. PORTUGAL DOS PEQUENITOS* (0.200); pequenitos c0011 *6. PORTUGAL DOS PEQUENITOS* (0.208); d-afonso-henriques web c0001 (0.476) | "Cassiano Branco" | ✅ (detalhe infiel: diz que "apenas uma" fonte menciona Cassiano Branco, mas as duas mencionam) |
| 4 | Em que ano foi fundado o Mosteiro de Santa Cruz? | heranca web c0008 *Igreja de Santa Cruz \| Panteão Nacional* (0.240); UC c0051 *24. MOSTEIRO DE SANTA CRUZ* (0.324); fundacao c0002 *2. IGREJA DE SANTA CRUZ* (0.333) | cita **1131** (Fontes 2 e 3) e "século XII" (Fonte 1), mas conclui que há "versões divergentes" | ⚠️ retrieval ✅; geração cria uma divergência falsa (§14) |
| 5 | Quem foi Sesnando David? | sesnando web c0001 (0.261); c0002 (0.339); c0003 (0.361) | "líder moçárabe… escolhido por Fernando Magno… Reconquista"; administrador | ✅ |
| 6 | Que doces tradicionais posso encontrar em Coimbra? | doçaria web c0002 (0.142); doçaria web c0001 (0.218); gastronomia web c0002 (0.248) | Pastel de Santa Clara, arrufadas, pães doces, fofos, queijadas | ✅ |
| 7 | O que são as Repúblicas de Coimbra? | republicas web c0001 (0.175); c0003 *Lista* (0.201); c0002 (0.325) | "comunidades autogeridas por estudantes…" | ✅ |
| 8 | Que museus posso visitar em Coimbra? | museus web c0001 (0.189, introdução sem nomes); museus web c0017 *Seminário Maior* (0.238); pequenitos c0004 *1. MUSEUS DA UNIVERSIDADE* (0.244) | "Galeria de História Natural" e "Museus de Coimbra" (confunde o título da página com um museu); omite o Seminário Maior | ⚠️ pior resposta que V0/V1 |
| 9 | Qual é a origem da Canção de Coimbra? | cancao web **c0001** (0.167, "Desde o século XVI"); c0005 (0.202, 98 caracteres); c0004 (0.231) | "raízes no século XVI, com registos de estudantes que cantavam…", mas enquadra a resposta como não explícita e fala de "formulações divergentes" | ⚠️ retrieval ✅; resposta correta mas hesitante (§11) |
| 10 | Que relação existe entre Pedro e Inês e Coimbra? | pedro-e-ines web c0001 (0.195); c0006 *Mosteiro de Santa Clara-a-Velha* (0.261); c0003 (0.270) | refúgio no Paço de Santa Clara; procissão fúnebre de Santa Clara a Alcobaça (verificado nas fontes) | ✅ |
| D | O que é o Paço das Escolas? | museus web c0018 *Paço das Escolas* (0.283); fado c0008 *2. PAÇO DAS ESCOLAS* (0.329); viver c0005 *1. PAÇO DAS ESCOLAS* (0.348) | "conjunto arquitetónico que alberga o núcleo histórico da Universidade de Coimbra" | ✅ |
| C | Quem fundou o Mosteiro de Santa Clara-a-Velha e quando? | heranca web c0003 (0.165); museus web c0007 (0.168); **fundacao c0007 (PDF, 1283)** (0.223) | expõe as versões, mas atribui a versão PDF à Fonte 2 (web) e omite a de 1314/D. Isabel de Aragão | ⚠️ retrieval ✅; fidelidade da geração ❌ (§12) |
| OOK | Qual foi o preço do bilhete para um jogo da Académica no Estádio Cidade de Coimbra em 2025? | fado c0021 (0.397); fado c0002 *1. ASSOCIAÇÂO ACADÉMICA* (0.418); fado c0001 (0.422) | frase de insuficiência; diz, sem razão, que o contexto menciona o estádio | ✅ recusa (§13) |

Contagem manual: **V2 → 9 ✅, 4 ⚠️, 0 ❌.** V1: 6 ✅, 4 ⚠️, 3 ❌. V0: 10 corretas, 1 parcial,
2 falhas. Considerando **só o retrieval** (o chunk com a informação pedida está no top-3),
a V2 acerta em 12 de 13. A exceção é a Q8, cujo top-3 só nomeia dois museus.

## 6. V0 vs V1 vs V2

| # | V0 top-1 | V1 top-1 | V2 top-1 | V0 answer | V1 answer | V2 answer |
|---|---|---|---|---|---|---|
| 1 | joanina c0002 | joanina c0002 | joanina c0002 | ✅ 1728 | ✅ 1728 | ✅ 1728 |
| 2 | joanina c0005 | joanina c0002 | joanina c0005 | ✅ | ✅ | ✅ |
| 3 | fundacao c0009 | jardins c0003 | fundacao c0009 | ✅ Cassiano Branco | ❌ abstém-se | ✅ Cassiano Branco |
| 4 | fundacao c0007 (Santa **Clara**) | fundacao c0008 (coordenadas) | heranca c0008 (Santa **Cruz**) | ❌ abstém-se | ❌ abstém-se | ⚠️ 1131 + falsa divergência |
| 5 | sesnando c0001 | sesnando c0002 | sesnando c0001 | ✅ | ⚠️ parcial | ✅ |
| 6 | doçaria c0002 | doçaria c0006 (Crúzios) | doçaria c0002 | ✅ 6 doces | ⚠️ só Crúzios | ✅ 5 doces |
| 7 | republicas c0001 | republicas c0001 | republicas c0001 | ✅ | ✅ | ✅ |
| 8 | museus c0001 | museus c0010 | museus c0001 | ⚠️ 5 museus | ⚠️ 5 museus | ⚠️ 1 museu + erro |
| 9 | cancao c0005 (98 chars) | cancao c0005 (98 chars) | **cancao c0001** (século XVI) | ❌ abstém-se | ❌ abstém-se | ⚠️ século XVI, hesitante |
| 10 | pedro-e-ines c0005 | pedro-e-ines c0001 | pedro-e-ines c0001 | ✅ | ✅ | ✅ |
| D | fado c0005 | museus c0018 | museus c0018 | ✅ | ✅ | ✅ |
| C | fundacao c0007 (PDF) | museus c0006 (Santa Clara-a-**Nova**) | heranca c0003 (Santa Clara-a-Velha) | ✅ divergência exposta | ⚠️ atribuição errada | ⚠️ atribuição errada |
| OOK | Praça das Cortes… | pequenitos c0013 | fado c0021 | ✅ recusa | ✅ recusa | ✅ recusa |

**Chunks críticos: rank completo** (lido só para diagnóstico; o pipeline usa top-3).

| Caso | Chunk relevante | V0 rank | V1 rank | V2 rank |
|---|---|---|---|---|
| Pequenitos | `fundacao-da-nacionalidade::c0009` | 1 | 6 | **1** |
| Pequenitos | `coimbra-para-os-pequenitos::c0011` | 2 | 4 | **2** |
| Santa Cruz | `fundacao-da-nacionalidade::c0002` ("Fundado em 1131") | 5 | 19 | **3** |
| Santa Cruz | `universidade-alta-sofia-patrimonio-mundial::c0051` | 12 | 123 | **2** |
| Sesnando | `web-visitecoimbra-sesnando-david::c0001` (moçárabe, Fernando Magno, 1064) | 1 | 7 | **1** |
| Doçaria | `web-visitecoimbra-docaria-conventual-de-coimbra::c0002` (introdução) | 1 | 32 | **1** |
| Canção | `web-visitecoimbra-cancao-de-coimbra::c0001` ("Desde o século XVI…") | 2 | 6 | **1** |
| Canção | `web-visitecoimbra-cancao-de-coimbra::c0005` (98 caracteres) | 1 | 1 | 2 |
| Santa Clara | `fundacao-da-nacionalidade::c0007` (PDF, 1283, D. Mor Dias) | 1 | 51 | **3** |
| Santa Clara | `web-visitecoimbra-museus::c0007` (1314, D. Isabel de Aragão) | 2 | 2 | 2 |
| Santa Clara | `web-visitecoimbra-heranca-cultural-e-religiosa::c0003` (Rainha Santa Isabel) | 3 | 4 | **1** |
| Paço das Escolas | `web-visitecoimbra-museus::c0018` *Paço das Escolas* | — | 1 | 1 |

Os valores da V0 e da V1 vêm dos relatórios respetivos. As stores V0 e V1 **não** foram
abertas nesta tarefa.

## 7. Portugal dos Pequenitos

Os dois chunks com "projetado por Cassiano Branco" voltam aos ranks **1 e 2** (V0: 1 e 2;
V1: 4 e 6), e a resposta volta a ser correta. Mantém-se a observação da V0: são **o mesmo
texto em dois PDFs**, pelo que dois dos três lugares do contexto vão para cópias
(duplicação PDF↔PDF, não corrigida). A resposta inclui um detalhe falso ("apenas uma" das
fontes menciona Cassiano Branco, quando as duas mencionam).

## 8. Santa Cruz

"Em que ano foi fundado o Mosteiro de Santa Cruz?": ranking completo dos chunks com
"1131":

| Chunk | Contém o facto pedido? | V0 | V1 | V2 |
|---|---|---|---|---|
| `universidade-alta-sofia-patrimonio-mundial::c0051` | sim | 12 | 123 | **2** (0.324) |
| `fundacao-da-nacionalidade::c0002` | sim | 5 | 19 | **3** (0.333) |
| `viver-o-patrimonio-em-coimbra::c0024` | sim, no fim do chunk | — | 8 | 11 (0.431) |
| `fundacao-da-nacionalidade::c0014` | não (1131 = mudança da capital) | — | 7 | 22 (0.510) |

O top-3 é inteiro sobre **Santa Cruz**: web "Igreja de Santa Cruz | Panteão Nacional"
("Fundado no século XII…"), UC 24 e Fundação 2. A confusão "Mosteiro" → Santa **Clara**
da V0/V1 desaparece: o chunk de coordenadas de Santa Clara que era rank 1 na V1
(`fundacao::c0008`) cai para **rank 29**.

**Geração:** a resposta cita 1131 duas vezes, mas trata "século XII" (web) e "1131"
(PDFs) como versões divergentes, o que não são. O chunk web recuperado traz a
`conflict_notes` de **Santa Clara-a-Velha**, porque as notas são por documento e todos
os chunks dessa página a herdam. Essa nota, irrelevante para esta pergunta, é enviada ao
modelo; é o candidato mais provável para a divergência inventada (§14). Isto é um
problema de geração e de metadata, não de retrieval.

## 9. Sesnando David

O chunk com "moçárabe", "Fernando Magno" e "1064" (`sesnando::c0001`) está em **rank 1**
(V1: 7). Os três chunks do top-3 são da página de Sesnando. A resposta diz quem ele foi:
líder moçárabe, escolhido por Fernando Magno, papel na Reconquista, administração de
Coimbra. Não menciona o ano 1064, que está na fonte.

## 10. Doçaria

A introdução da Doçaria Conventual (`docaria::c0002`, "pastel de Santa Clara…
arrufadas, pães doces e fofos, e as queijadas") volta ao **rank 1** (V1: 32). O resto do
top-3 é da mesma página e da página Gastronomia. A resposta lista 5 doces, todos no
contexto. Os Crúzios, que a V0 também listou, não estão neste top-3.

## 11. Canção de Coimbra

| Chunk | V0 | V1 | V2 |
|---|---|---|---|
| `cancao::c0001` ("Desde o século XVI, há registos de estudantes que… cantavam") | 2 | 6 | **1** (0.167) |
| `cancao::c0005` (frase genérica de 98 caracteres) | 1 | 1 | 2 (0.202) |

Pela primeira vez o chunk com a origem fica à frente do chunk curto e genérico. Este
continua no top-3 (não foi filtrado) e ocupa um lugar. A resposta **usa** agora a
informação ("raízes no século XVI… estudantes que cantavam temas que combinavam erudito e
popular"), ao contrário da V0/V1, que se abstiveram. Mesmo assim, enquadra-a como "não
explicitamente mencionada" e termina com "existem formulações divergentes… não há
informações suficientes", **sem** que tenha sido enviada qualquer nota de conflito. Isto
indica que a instrução de divergências do system prompt também induz hesitação
injustificada (§14).

## 12. Santa Clara Conflict Retrieval

**Retrieval (o objeto desta experiência):**

| Rank | Chunk | Versão |
|---|---|---|
| 1 (0.165) | `web-visitecoimbra-heranca-cultural-e-religiosa::c0003` | web: "Fundado pela Rainha Santa Isabel" |
| 2 (0.168) | `web-visitecoimbra-museus::c0007` | web: "mandado construir em 1314 por D. Isabel de Aragão" |
| 3 (0.223) | `fundacao-da-nacionalidade::c0007` | PDF: "Fundado em 1283, por D. Mor Dias…" |

**As três formulações conhecidas estão no top-3**, como na V0. A V1 tinha Santa
Clara-a-**Nova** em rank 1, que na V2 cai para rank 11, e o chunk de coordenadas, que cai
para rank 6. Do ponto de vista do retrieval, este é o melhor resultado das três versões.

**Geração, avaliada à parte:** a resposta identifica a Fonte 1 corretamente, mas atribui à
**Fonte 2 (web)** a versão "1283 / D. Mor Dias", que só está na Fonte 3 (PDF) e na nota de
curadoria. A versão web de **1314 / D. Isabel de Aragão** fica omitida. Termina com a frase
de insuficiência. É o mesmo tipo de falha de fidelidade documentado na V1 (a nota de
curadoria contamina a atribuição de fontes). **Não pode ser usada como evidência sobre o
embedding**, porque o contexto recuperado era completo.

## 13. Out-of-Knowledge

- **Retrieval:** três chunks da Associação Académica / Fado (0.397–0.422), ligados
  lexicalmente a "Académica".
- **Resposta:** "Não tenho informação suficiente no contexto disponível para responder com
  segurança." ✅ Sem preços inventados. Contém um detalhe infiel: diz que o contexto
  menciona o "Estádio Cidade de Coimbra", e nenhum dos três chunks o menciona.
- **Separação de distâncias:** na V2, o top-1 da pergunta fora do domínio (0.397) está
  **mais longe** que o top-1 de todas as 12 perguntas do domínio (0.142–0.283). Na V1 isto
  não acontecia. Continua a não haver threshold, e isto é só uma observação.

## 14. Known Issues

Observados e **não corrigidos** (fora do âmbito: prompt, metadata e geração congelados):

| # | Problema | Tipo | Evidência |
|---|---|---|---|
| 1 | `conflict_notes` são por documento: qualquer chunk da página herda a nota, mesmo sobre outra entidade | Metadata / geração | Q4: nota de Santa Clara enviada numa pergunta sobre Santa Cruz → divergência inventada |
| 2 | A nota de curadoria contamina a atribuição de fontes | Fidelidade | C: versão PDF atribuída à fonte web; versão de 1314 omitida (igual à V1) |
| 3 | A instrução de divergências do system prompt induz hesitação e "formulações divergentes" sem conflito | Geração | Q9 (sem nota de conflito enviada), Q4 |
| 4 | Pequenos detalhes infiéis em respostas corretas | Fidelidade | Q3 ("apenas uma fonte"), OOK ("menciona o estádio") |
| 5 | Perguntas de enumeração com top-3 | Limite de `top_k` | Q8: top-3 com só 2 museus nomeados; resposta pior que V0/V1 |
| 6 | Duplicação PDF↔PDF ocupa lugares do top-3 | Diversidade | Q3: ranks 1–2 são o mesmo texto |
| 7 | Chunk curto e genérico continua no top-3 | Chunks curtos | Q9: `cancao::c0005` em rank 2 |
| 8 | Custo do build em CPU | Operacional | ~36 min para 317 chunks (bf16, CPU); a V1 demorou poucos minutos |
| 9 | Normas ~0.9999 (bf16) | Numérico | sem efeito no ranking cosine |

## 15. Integrity / Tests

**Hashes SHA-256 antes/depois** (build V2 + validação + consultas + testes): 82 ficheiros,
**0 diferenças**.

| Conjunto | Ficheiros | Alterados |
|---|---|---|
| Raw PDF / Raw Web | 8 / 24 | 0 / 0 |
| Processed PDF / Processed Web | 8 / 24 | 0 / 0 |
| `manifest.jsonl` | 1 | 0 |
| `chunks.jsonl`, `chunk_stats.json` | 2 | 0 |
| `chroma_smoke/` | 5 | 0 (não aberta) |
| `chroma_baseline/` (V0) | 5 | 0 (não aberta) |
| `chroma_baseline_v1/` (V1) | 5 | 0 (não aberta) |

A única DB nova é `data/chroma_baseline_v2/`.

**Testes: 108 OK** (104 anteriores; os testes de configuração foram reescritos e
alargados), offline: sem download de modelos, sem internet e sem Ollama. Cobrem:

- `BASELINE_V0` e `BASELINE_V1` preservadas com os valores exatos (`query_prompt_name=None`);
- `BASELINE_V2` exata (Qwen, `"query"`, store e collection V2) e `BASELINE is BASELINE_V2`;
- V0→V1 diferem só em modelo/collection/store; V1→V2 só nesses campos e em
  `query_prompt_name`;
- stores e collections distintas, não aninhadas, todas em `data/`;
- as três versões selecionam 317 chunks (11 + 2 excluídos);
- V0/V1 construídas só com `encode_kwargs` (queries = documentos);
- V2 com o `HuggingFaceEmbeddings` **real** e um cliente SentenceTransformer falso:
  `embed_documents` → `encode(..., normalize_embeddings=True)` **sem** `prompt_name`;
  `embed_query` → `encode([pergunta], normalize_embeddings=True, prompt_name="query")`;
- a store embebe `chunk["text"]` como documentos e a pergunta como query;
- `SYSTEM_PROMPT` literal e LLM `llama3.2:3b` / 0.1 inalterados.

## 16. Decision

**IS V2 A STRONG CANDIDATE FOR FORMAL EVALUATION?**

# YES

**Porquê (qualitativo, 13 perguntas de diagnóstico):**
- A V2 teve **melhor desempenho qualitativo** que a V0 e a V1 **neste conjunto de
  diagnóstico**: em 12 de 13 perguntas o chunk com a informação pedida está no top-3,
  incluindo os casos que falharam antes (Santa Cruz: ranks 2–3 contra 5/12 na V0 e 19/123
  na V1; Canção: século XVI em rank 1).
- Recuperou as regressões da V1 (Pequenitos, Sesnando, Doçaria, Santa Clara) e deixou de
  confundir Santa Cruz com Santa Clara.
- As falhas restantes são sobretudo de **geração e metadata** (§14), não de retrieval.
- A configuração é explícita, validada (317 × 1024, cosine, documentos sem instruction,
  queries com o prompt do próprio modelo) e reproduzível com um comando.

**O que isto não significa:** não mostra que o Qwen3 seja "o melhor modelo de embeddings".
São 13 perguntas escolhidas para diagnóstico, sem ground truth nem métricas. A conclusão
formal depende do evaluation dataset. Antes de medir fidelidade, convém tratar os problemas
1–3 da §14, que afetam as três versões por igual. O custo de build em CPU (~36 min) é um
fator prático a considerar.
