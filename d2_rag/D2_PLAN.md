# D2 — Expert Retrieval-Augmented Generation Agent

## 1. Objective

Design and, in later phases, implement a Portuguese-language expert RAG agent for tourism, history, and culture in Coimbra. The agent should answer domain questions usefully and ground its answers in a purpose-built, traceable knowledge base.

This document is the initial D2 specification. It defines scope, architectural direction, data strategy, evaluation readiness, and an incremental roadmap. It does not implement the RAG system, collect the full knowledge base, define final hyperparameters, or integrate D2 with D1.

## 2. Requirements from the Course Project

Primary source: [`../2026_ILN_CourseProject.pdf`](../2026_ILN_CourseProject.pdf).

### 2.1 Mandatory requirements from the official project statement

- Build an expert Retrieval-Augmented Generation (RAG) conversational agent.
- Base the agent on an **open Large Language Model (LLM)** and a **Vector Database**.
- Select a domain of expertise.
- Create the domain knowledge base using data collected for this purpose.
- Provide useful answers to questions in the selected domain.
- Quantitatively compare answer quality **without RAG** and **with RAG**.
- Use Python for project development and experimentation; suitable Python libraries should be used when possible.
- Present and discuss D2 with a professor in the class assigned to this deliverable. A separate formal D2 report is not required by the statement.

### 2.2 Current project decisions

- Proposed domain: **Coimbra Tourism Expert**.
- Primary interaction and knowledge-base language: **Portuguese**.
- Follow the RAG baseline taught in the course: document preparation, chunking, sentence embeddings, vector storage, semantic retrieval, context-aware prompting, and answer generation with an open LLM.
- Design source traceability and evaluation support from the start.
- Keep the No-RAG and RAG conditions comparable by using the same LLM, question set, and aligned generation settings.

These are implementation decisions, not additional requirements attributed to the official statement. The domain boundaries and technical choices remain subject to validation.

### 2.3 Optional or future extensions

- Reranking retrieved chunks.
- Additional preprocessing strategies, if experiments justify them.
- Few-shot prompts, if they provide measurable value.
- D1/D2 integration and text-classification-based routing. The statement presents this integration only as an ideal possibility; it is not part of the present D2 plan or implementation phase.
- MCP integration belongs to a possible D3 option and is not part of D2.

## 3. Domain

### Coimbra Tourism Expert

The proposed agent will provide Portuguese answers about Coimbra's tourism, history, and culture. This is a suitable expert RAG domain because relevant knowledge is distributed across institutional tourism pages, heritage and museum resources, and historical or cultural documents. Retrieval can connect a user's question to authoritative passages, while source metadata can make the evidence traceable.

The domain also supports meaningful evaluation: questions can be paired with relevant source passages, retrieval can be assessed independently, and grounded answers can be compared against the same LLM operating without retrieved context.

The domain and the boundaries below are an **initial proposal**, not a final frozen specification.

## 4. Scope

The initial knowledge scope is:

- University of Coimbra, including its historically and culturally relevant spaces;
- historical heritage and the history of Coimbra;
- monuments and architecturally significant sites;
- museums;
- places of tourist interest;
- local culture, traditions, and relevant cultural context;
- traditional gastronomy;
- practical tourism information that can be maintained as relatively stable knowledge;
- transport information relevant to tourism only when it is sufficiently stable and can carry source and validity metadata.

Expected question types include factual questions, explanations, comparisons, and itinerary-oriented information that can be answered from the curated corpus. Exact supported intents and depth of coverage are **TBD / To be evaluated** after source discovery and corpus analysis.

## 5. Out of Scope

The following are outside the current D2 scope:

- any modification or extension of D1;
- D1 functionality, including chit-chat, greetings, and farewells;
- D1/D2 integration;
- text classification or routing between agents;
- MCP servers or MCP-based functionality;
- reservations, purchases, bookings, or transactions;
- external actions of any kind;
- information that necessarily requires real-time accuracy, such as live availability, current disruptions, or rapidly changing opening details;
- authoritative handling of questions outside the Coimbra tourism domain.

For unsupported, out-of-domain, or insufficiently evidenced questions, the future agent should state the limitation rather than fabricate an answer. The exact fallback wording and behaviour are **TBD / To be evaluated**.

## 6. Knowledge Base Strategy

### 6.1 Source types and selection

Candidate sources should be selected for authority, relevance, stability, clarity, and permission to use their content. Likely source types include:

- official municipal and regional tourism resources;
- official University of Coimbra and heritage-site resources;
- official museum and monument pages or publications;
- public institutional cultural and historical resources;
- curated tourism documents and PDFs from credible organisations.

Specific sources and the corpus inclusion policy are **TBD / To be evaluated**. Every included document should have a recorded origin. Conflicting or time-sensitive claims should be identified during curation rather than silently merged.

No data is collected as part of this planning phase.

### 6.2 Planned data separation

The future corpus should separate:

- **raw data**: an unmodified or faithfully preserved copy/snapshot of each collected source, together with acquisition metadata;
- **processed data**: extracted, cleaned, normalised, and chunk-ready content derived reproducibly from raw data;
- **index data**: embeddings and vector-store state generated from a named processed-corpus version.

The directory names and serialization formats are **TBD / To be evaluated** and should only be created when their implementation phase begins.

### 6.3 Metadata and traceability

Recommended document-level metadata:

- `document_id`: stable internal identifier;
- `source`: publisher or source organisation;
- `title`: human-readable document title;
- `url`: original location when the source is web-based;
- `category`: controlled domain category, if useful for analysis or filtering;
- acquisition date and/or source validity information when relevant.

Recommended chunk-level metadata:

- `chunk_id`: unique identifier for the derived chunk;
- `document_id`: link back to the parent document;
- `page`: page number for paginated sources, when reliably available;
- chunk position or order within the parent document.

Not every field is universally mandatory. `document_id`, `chunk_id`, and sufficient source-identifying metadata should be required for traceability. `url` applies only when one exists; `page` applies only to paginated sources; `category` should be retained only if categories are defined consistently. The final metadata schema is **TBD / To be evaluated**.

Each chunk must be traceable to the processed document and, from there, to the original raw source. This provenance will support debugging, answer evidence, corpus maintenance, and retrieval ground truth.

### 6.4 Preparation principles

- Preserve the original raw material before transformation.
- Make extraction and cleaning reproducible.
- Remove extraction artefacts, repeated headers and footers, broken line wraps, navigation noise, and other non-content elements, especially in PDFs.
- Preserve headings and structural cues where they improve chunk meaning.
- Detect and manage exact or near-duplicate content to avoid retrieval bias.
- Keep meaningful Portuguese diacritics, punctuation, and names.
- Do not apply stemming, lemmatization, stopword removal, or aggressive normalisation by default; evaluate them only with a clear retrieval hypothesis.
- Record corpus and processing versions so experiments can be reproduced.
- Reserve a process for annotating relevant documents/chunks for future retrieval evaluation; do not create fictitious ground truth.

## 7. Baseline RAG Architecture

### 7.1 Indexing path

```text
Documents
  → Extraction
  → Cleaning and Preparation
  → Chunking
  → Sentence Embeddings
  → Vector Database
```

### 7.2 Question-answering path

```text
User Question
  → Query Embedding
  → Cosine-Similarity Search in the Vector Database
  → Ranked Top-k Chunks
  → Prompt Construction (instructions + retrieved context + question)
  → Open Instruction-Tuned LLM
  → Grounded Answer
```

The system prompt should require answers grounded in the supplied context and an explicit acknowledgement when the context is insufficient. The exact prompt, citation presentation, and fallback policy are **TBD / To be evaluated**.

## 8. Components

The later implementation is expected to need the following logical components. This list describes responsibilities, not a commitment to one Python file per component.

- **Document ingestion**: load source content and preserve provenance.
- **Text extraction**: extract usable text from supported source formats.
- **Preprocessing**: clean noise while retaining relevant structure and meaning.
- **Chunking**: split documents into retrieval units and attach chunk metadata.
- **Embedding generation**: encode chunks and queries with the same sentence-embedding model.
- **Vector store**: persist vectors, text, and metadata.
- **Retriever**: perform semantic similarity search and return ranked top-k chunks with scores and provenance.
- **Prompt construction**: combine system instructions, retrieved evidence, and the user question.
- **LLM interface**: invoke a local/open instruction-tuned model using controlled generation settings.
- **RAG agent**: coordinate retrieval, prompt construction, and answer generation.
- **No-RAG baseline**: invoke the same LLM without retrieved evidence under a comparable configuration.
- **Evaluation**: maintain questions and references, run both conditions, capture outputs/configurations, and compute or support retrieval and answer metrics.

Interfaces between these responsibilities should allow retriever and generator evaluation to be performed independently.

## 9. Initial Technology Baseline

The initial baseline follows tools and concepts used in the course practical work:

| Area | Initial baseline | Status |
|---|---|---|
| Language | Python | Course/project baseline |
| RAG orchestration | LangChain | Initial course baseline; exact use TBD |
| Chunking | `RecursiveCharacterTextSplitter` with overlap | Parameters TBD / To be evaluated |
| Embeddings | HuggingFace sentence embeddings | Model TBD / To be evaluated |
| Vector database | Chroma | Initial course baseline |
| Similarity | Cosine similarity | Initial baseline; configuration TBD |
| Retrieval | Ranked top-k semantic retrieval | `k` TBD / To be evaluated |
| Model runtime | Ollama | Initial course baseline |
| Generator | Open, instruction-tuned LLM with adequate Portuguese support | Model TBD / To be evaluated |
| Generation | Low temperature for factual answers | Exact value TBD / To be evaluated |
| Prompting | System prompt plus retrieved context and question | Template TBD / To be evaluated |

These choices are a starting point aligned with the discipline, not evidence that every tool or default value is optimal. Final models and hyperparameters must be selected according to local resource constraints and controlled experiments. No dependency is installed in this phase.

## 10. Evaluation Strategy

The mandatory comparison will use the same evaluation questions and the same open LLM in two conditions:

```text
A. No-RAG: question → LLM → answer
B. RAG:    question → retrieval → context + question → same LLM → answer
```

Generation settings should be identical wherever the comparison permits. Any unavoidable prompt difference is part of the treatment and must be documented. Model version, prompts, temperature, random seed where supported, corpus/index version, retrieval settings, and outputs should be recorded for reproducibility.

The architecture should support two separate evaluation layers:

1. **Retrieval quality**
   - prepare questions with human-validated relevant documents or chunks;
   - retain stable identifiers so retrieved results can be matched to ground truth;
   - enable metrics such as Precision@k and Recall@k;
   - use F1 when its definition is appropriate to the labelled task;
   - inspect ranking errors in addition to aggregate metrics.

2. **Answer quality**
   - run the same questions in No-RAG and RAG conditions;
   - prepare reference facts/answers or a scoring rubric using credible sources;
   - assess dimensions such as correctness, completeness, relevance, groundedness, and hallucination incidence;
   - aggregate scores quantitatively and retain examples for qualitative error analysis.

The final dataset, annotation procedure, metrics, judge type, sample size, and statistical analysis are deliberately **TBD / To be evaluated**. Automated judging, if later considered, must not replace a justified and reproducible protocol without validation.

## 11. Experimental Questions

Later experiments may investigate:

- Which chunk size best balances local precision and sufficient context?
- How much chunk overlap improves continuity without producing excessive duplication?
- Which Portuguese or multilingual sentence-embedding model provides the best retrieval quality within available resources?
- What top-k value provides useful evidence without adding distracting context?
- Does a reranking stage measurably improve retrieval and final answers?
- Which system and answer prompt best promotes grounded, useful Portuguese responses?
- Which low-temperature setting provides an appropriate balance of stability and answer quality?
- Does any additional preprocessing improve retrieval compared with conservative cleaning?
- How sensitive are results to source mix, duplicate content, and document categories?
- How does retrieval quality affect final answer quality and hallucination rate?

No experiment or final value is selected in this phase.

## 12. Open Decisions / TBD

- Confirm or refine the precise domain boundaries and supported question types.
- Define source inclusion, exclusion, licensing/usage, freshness, and conflict-resolution criteria.
- Select the initial authoritative sources and corpus size.
- Decide how to handle facts that change over time and how to expose source validity.
- Define the raw, processed, manifest, and index formats and naming conventions.
- Finalise mandatory versus optional metadata fields.
- Select supported input formats and extraction tools.
- Define duplicate-detection and document-versioning methods.
- Select chunk size and chunk overlap.
- Select the HuggingFace embedding model.
- Confirm Chroma cosine-similarity configuration and persistence approach.
- Select top-k and decide whether metadata filters are useful.
- Select an open instruction-tuned LLM with suitable Portuguese quality and feasible local resource requirements.
- Define the Ollama model/version management approach.
- Select temperature and other generation parameters.
- Define the system prompt, context format, source attribution format, and insufficient-context behaviour.
- Decide whether reranking is justified after the baseline is measured.
- Define the evaluation question taxonomy, dataset size, and train/development/test separation if applicable.
- Define retrieval relevance labels and annotation guidelines.
- Define answer-quality rubric, metrics, evaluators, and agreement checks.
- Establish quantitative success criteria for the RAG versus No-RAG comparison.

## 13. Implementation Roadmap

Implementation should proceed incrementally only after approval:

1. **Phase 1 — Knowledge base**  
   Confirm scope and source policy; identify credible sources; define provenance metadata; collect and catalogue an initial corpus.

2. **Phase 2 — Ingestion and chunking**  
   Implement reproducible extraction, cleaning, duplicate handling, chunking, and metadata propagation; inspect sample outputs.

3. **Phase 3 — Embeddings and Vector DB**  
   Select an initial embedding model; generate embeddings; build and version a Chroma index; verify vector/metadata persistence.

4. **Phase 4 — Baseline retrieval**  
   Implement query embedding and cosine-similarity top-k retrieval; expose ranks, scores, text, and provenance for inspection.

5. **Phase 5 — Baseline RAG**  
   Connect retrieved chunks to a grounded prompt and the selected open LLM through Ollama; implement insufficient-context behaviour.

6. **Phase 6 — No-RAG baseline**  
   Implement the comparable same-LLM condition without retrieved context and record all relevant configuration.

7. **Phase 7 — Evaluation dataset**  
   Build and validate domain questions, retrieval relevance judgements, reference facts or answers, and an answer-scoring rubric.

8. **Phase 8 — Experiments and improvements**  
   Compare No-RAG with RAG quantitatively; evaluate retrieval separately; test selected parameters one at a time or under a documented design; add improvements such as reranking only when supported by results.

No roadmap phase is implemented by this document.
