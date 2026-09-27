# RAG Smoke Test

## Purpose

Temporary technical baseline whose only goal is to show that the basic D2 RAG
pipeline runs end-to-end on our knowledge base. It is **not** the final D2
architecture or configuration, and it is **not** an evaluation. No tuning,
model comparison or RAG vs No-RAG comparison was done.

Script: `d2_rag/scripts/rag_smoke_test.py`
Tests: `d2_rag/tests/test_rag_smoke_test.py`

```bash
uv run python d2_rag/scripts/rag_smoke_test.py --rebuild
uv run python d2_rag/scripts/rag_smoke_test.py --question "Em que ano ficou concluída a Biblioteca Joanina?"
uv run python d2_rag/scripts/rag_smoke_test.py --rebuild --question "..." --question "..."
```

## Configuration

All values are **TEMPORARY BASELINE / TO BE EVALUATED**.

| Parameter | Value |
|---|---|
| Embedding model | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (HuggingFaceEmbeddings, normalized) |
| Chunking | `RecursiveCharacterTextSplitter`, applied per source page |
| chunk_size | 1000 characters (`len`) |
| chunk_overlap | 100 characters |
| Vector database | Chroma, persisted at `d2_rag/data/chroma_smoke/` (git-ignored, rebuildable), collection `d2_rag_smoke` |
| Similarity metric | cosine (`hnsw.space = cosine`). Chroma returns the cosine **distance**, and the output also shows similarity = 1 − distance |
| top-k | 3 |
| LLM | Ollama `llama3.2:3b` |
| temperature | 0.1 |
| Prompt | Portuguese system prompt ("answer only from the context, say when it is insufficient, do not invent"), zero-shot |

## Pipeline

```
Processed Markdown (d2_rag/data/processed/, via manifest.jsonl)
→ split on <!-- source_page: N --> into page Documents (the marker becomes metadata)
→ chunks (per page, so no chunk crosses a page; chunk_id = <document_id>::p<page>::c<index>)
→ embeddings
→ Chroma
→ top-k retrieval
→ prompt (system + context + question)
→ Ollama
→ answer + sources
```

Index built from the corpus: **8 documents, 56 non-empty page units, 209 chunks,
and 209 vectors in Chroma**.

## Smoke Questions

1. Em que ano ficou concluída a construção da Biblioteca Joanina?
2. Porque existem morcegos na Biblioteca Joanina?
3. Em que ano foi fundado o Mosteiro de Santa Cruz?
4. Quem idealizou e quem projetou o Portugal dos Pequenitos?
5. Que relação tiveram as cheias do Mondego com o Mosteiro de Santa Clara-a-Velha?
6. (out-of-knowledge) Qual é o horário de funcionamento e o preço do bilhete do Estádio Cidade de Coimbra em dias de jogo da Académica?

## Results

These are manual observations, not metrics.

| # | Retrieval relevant? | Answer coherent? | Observations |
|---|---|---|---|
| 1 | Yes. Rank 1 is `biblioteca-joanina-uctour` p. 2 (distance 0.297) | Yes: "1728" | Correct and grounded. Ranks 2–3 are the Joanina entry of the UC brochure (p. 11) and a caption-only chunk (p. 15). |
| 2 | Yes. Rank 1 is `biblioteca-joanina-uctour` p. 3 (0.381) | Partially | The context says the bats "contribuem para o controle de pragas". The answer omits this and adds an unsupported causal link ("resultado natural da conservação dos livros… que podem atrair insetos"). **Mild hallucination / misreading.** |
| 3 | **No** | Yes (abstained) | The answer (1131) is in 3 documents, but none of those chunks is in the top-10. The model correctly said the information was not available. See the chunking issue below. |
| 4 | Yes. Rank 1 is `coimbra-para-os-pequenitos` p. 1 (0.263), rank 2 is `fundacao-da-nacionalidade` p. 1 | Yes: Bissaya Barreto (idealized), Cassiano Branco (designed) | Correct. **The same text appears in two PDFs** (redundant retrieval). |
| 5 | **No** | Yes (abstained) | Top-3 was unrelated (Quinta das Lágrimas, captions, Largo do Poço). The relevant chunk (`fundacao-da-nacionalidade::p1::c10`, Santa Clara-a-Nova "fustigado… pelas cheias do Mondego") is only at rank 6. The model correctly said the information was insufficient. |
| OOK | Top-3 irrelevant, as expected (distances 0.41–0.45, higher than in-domain 0.26–0.38) | Yes | The model explicitly said the information was insufficient and invented no hours or prices. |

### Diagnostic observations (not addressed in this phase)

- **Headings separated from their body.** The splitter often cuts at the `\n\n`
  after a `## N. ENTITY` heading. The heading ends up at the end of the previous
  chunk, and the body (e.g. "Fundado, em 1131, …") starts the next chunk without
  naming the entity. This is the most likely cause of the Q3 miss (checked:
  `universidade-alta-sofia-patrimonio-mundial::p28::c1` ends with
  `## 24. MOSTEIRO DE SANTA CRUZ`, and `::p28::c2` holds the text). Q5 is
  similar, and the Santa Clara-a-Velha body also uses "inundações" rather
  than "cheias".
- **Low-information chunks.** The UC brochure has caption-only pages (e.g. "Casa da
  Livraria | Biblioteca Joanina") that become tiny chunks and take top-k slots.
- **Cross-item bleed.** Chunks often start with the `**Coordenadas:**` line of the
  previous item (overlap and layout effect).
- **Redundancy across PDFs.** The municipal brochures repeat the same entries
  (Portugal dos Pequenitos, Parque Dr. Manuel Braga, Santa Cruz), so duplicates
  fill the top-k.
- **Coarse pages.** Most municipal brochures have only 2 pages, so `source_page`
  is technically correct but not very informative there.

## Known Limitations

- No tuning of chunking, top-k, embedding model, LLM or prompt.
- No quantitative evaluation (no dataset, no Precision@k / Recall@k).
- No RAG vs No-RAG comparison.
- No systematic analysis of the corpus (duplication, caption pages).
- 6 questions, judged manually and run once.

## Decision

**Is the basic RAG pipeline operational end-to-end?**

**Yes.** Markdown loading, page metadata, chunking, embeddings, Chroma, retrieval,
prompting and Ollama generation all run and are traceable. Retrieval quality is
mixed (2 of 5 in-domain questions missed), but that is a quality question for the
later evaluation phase.
