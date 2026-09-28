# Code Quality Refactor

Data: 2026-09-28. Base: commit `b35ffbd`. Auditoria prévia: `CODE_QUALITY_AUDIT.md`.

## 1. Scope

Refactor estrutural sem alteração de comportamento. Nada foi acrescentado ao pipeline:
preprocessing, chunking, embeddings, retrieval, prompts, modelos, configuração experimental,
dataset e outputs ficaram iguais. Nenhuma vector DB foi aberta, reconstruída ou alterada e
nenhum LLM foi chamado (Ollama foi simulado com `mock` nos testes de equivalência).

Implementado: H1, M1, M2, M3, M4, M5 e os LOW triviais L1, L2, L10, L14.
Não implementado: M6 (correção de comportamento) e os restantes LOW (ver §7).

## 2. Findings Implemented

| ID | Problema | Alteração | Benefício |
|----|----------|-----------|-----------|
| H1 | Configuração da baseline em globais; `generate()`/`_chroma()`/`load_embeddings()` sem parâmetros. | `RAGConfig` (`@dataclass(frozen=True)`) + `BASELINE` com os valores exatos; as funções aceitam `config=BASELINE`. | A configuração é explícita, única e serializável (`dataclasses.asdict`) para registar com resultados de avaliação. É possível avaliar variantes com `dataclasses.replace(BASELINE, top_k=5)` sem *monkeypatching*. |
| M1 | `rag_baseline.py` misturava o pipeline e a CLI. | Novo `rag_pipeline.py` (core, sem `print`/`argparse`/`input`); `rag_baseline.py` fica só com a CLI, com os mesmos argumentos e o mesmo output. | Retrieval avaliável sem LLM, prompt testável sem Chroma, CLI como interface. Os comandos documentados em `RAG_BASELINE_SMOKE_TEST.md` continuam válidos. |
| M2 | Seis leitores do manifest; só a etapa PDF validava. | `corpus.load_manifest` (movido sem alterações de `preprocess_documents`) é usado pelas etapas PDF, Web e chunking. | Um manifest corrompido ou com `document_id` duplicado falha com o número da linha em todas as etapas determinísticas. |
| M3 | O chunker importava `preprocess_documents` (e `pymupdf`) por uma constante; marcador `caption_panel` escrito como dois literais. | `ROUTE_DOCUMENT_IDS` e `CAPTION_PANEL_MARKER` passam para `corpus.py`; sai o `sys.path.insert`. | Etapas desacopladas; o contrato produtor→consumidor tem uma única definição. Verificado: importar o chunker já não carrega `pymupdf`. |
| M4 | `chunk_documents.load_records` fazia `raise SystemExit`. | Passa a `ValueError`; `main()` imprime para stderr e devolve 1. | A função core não termina o processo; o comportamento observável da CLI é o mesmo (mesma mensagem, exit 1). |
| M5 | `D2_ROOT`/`MANIFEST_PATH`/caminho dos chunks redefinidos em cada script. | `corpus.py` define `D2_ROOT`, `DATA_DIR`, `MANIFEST_PATH`, `CHUNKS_DIR`, `CHUNKS_PATH`; os caminhos de um só script ficam onde estavam. | "O chunker escreve onde o RAG lê" passa a ser uma única constante. |
| L1 | Hash `"sha256:<hex>"` implementado três vezes. | `corpus.sha256_file` / `sha256_bytes` nas etapas PDF e Web. | Um formato, uma implementação. |
| L2 | Leitura/escrita JSONL repetida. | `corpus.read_jsonl` / `write_jsonl` no chunker e no RAG. | Bytes de `chunks.jsonl` garantidos por um teste de formato. |
| L10 | D1 `find_places`: `if place not in places` comparava `str` com tuplos. | `if (place, category) not in places`. | A deduplicação passa a ser real; o output é idêntico (cada local aparece uma vez em `KNOWN_PLACES`). |
| L14 | `rag_baseline.section()` era um nome ambíguo. | `print_section()`. | Não se confunde com a metadata `section`. |

## 3. Architecture Before

```
d2_rag/scripts/
├── preprocess_documents.py      manifest loader validado, sha256, ROUTE_DOCUMENT_IDS,
│                                marcador caption_panel, extração PDF, CLI
├── preprocess_web_documents.py  manifest loader próprio, sha256 inline, extração Web, CLI
├── chunk_documents.py ──sys.path──▶ preprocess_documents (ROUTE_DOCUMENT_IDS → pymupdf)
│                                manifest inline, JSONL inline, SystemExit, chunking, CLI
├── rag_baseline.py              config global + chunks + Chroma + retrieval + prompt
│                                + Ollama + print + argparse + loop interativo
├── rag_smoke_test.py            (histórico)
├── acquire_web_corpus.py        (rede)
└── discover_web_corpus.py       (rede)
```

## 4. Architecture After

```
d2_rag/scripts/
├── corpus.py                    NOVO: paths partilhados, JSONL, manifest validado,
│                                SHA-256, ROUTE_DOCUMENT_IDS, CAPTION_PANEL_MARKER
├── preprocess_documents.py  ──▶ corpus    PDF → Markdown
├── preprocess_web_documents.py ─▶ corpus  HTML → Markdown
├── chunk_documents.py       ──▶ corpus    Markdown → chunks
├── rag_pipeline.py          ──▶ corpus    NOVO: RAGConfig/BASELINE, vector store,
│                                          retrieval, prompt, geração
├── rag_baseline.py          ──▶ rag_pipeline   só CLI
├── rag_smoke_test.py            inalterado (histórico)
├── acquire_web_corpus.py        inalterado
└── discover_web_corpus.py       inalterado
d2_rag/tests/
├── test_corpus.py               NOVO
└── … (restantes; só test_rag_baseline e test_chunk_documents tocados)
```

Dois ficheiros novos, nenhum package, nenhuma dependência nova, nenhuma alteração ao
`pyproject.toml`. Os scripts continuam a ser executados como antes
(`uv run python d2_rag/scripts/<script>.py`).

## 5. Responsibility Boundaries

| Responsabilidade | Onde |
|------------------|------|
| Layout de `data/`, manifest, JSONL, hashes, contrato do Markdown processado | `corpus.py` |
| Preprocessing PDF (layout, limpeza, Markdown) | `preprocess_documents.py` |
| Preprocessing Web (DOM Elementor, limpeza, Markdown, escrita do manifest web) | `preprocess_web_documents.py` |
| Chunking estrutural, validação e estatísticas dos chunks | `chunk_documents.py` |
| Configuração experimental do RAG | `rag_pipeline.RAGConfig` / `BASELINE` |
| Vector store (chunks → Documents, embeddings, Chroma build/open) | `rag_pipeline.py` — `select_indexable`, `to_metadata`, `load_embeddings`, `build_store`, `open_store` |
| Retrieval | `rag_pipeline.retrieve` (não precisa do LLM) |
| Contexto, prompt, fontes | `rag_pipeline.build_context`, `conflict_note`, `build_messages`, `format_sources` (não precisam de Chroma) |
| Geração | `rag_pipeline.check_ollama`, `generate` |
| CLI (argumentos, apresentação, loop interativo) | `rag_baseline.py` |

## 6. Duplication Removed

- 3 cópias do leitor do manifest → 1 (`corpus.load_manifest`): PDF, Web e chunking.
- 3 definições de `D2_ROOT` + 3 de `MANIFEST_PATH` + 2 do caminho dos chunks nas etapas
  tocadas → 1 cada.
- 2 implementações do hash `sha256:` → 1 módulo (`sha256_file`, `sha256_bytes`).
- 2 literais `"<!-- caption_panel -->"` → 1.
- `ROUTE_DOCUMENT_IDS` deixa de ser importado de outro script.
- Escrita e leitura JSONL no chunker e no RAG → `write_jsonl` / `read_jsonl`.
- Balanço do diff nos ficheiros existentes: +82 / −332 linhas; novos: `corpus.py`,
  `rag_pipeline.py` (conteúdo movido de `rag_baseline.py`), `test_corpus.py`.

## 7. Findings Not Implemented

| ID | Porquê |
|----|--------|
| M6 (`discover_web_corpus` rebenta com o manifest atual) | É uma correção de comportamento (crash → resultado), fora do âmbito de um refactor que preserva comportamento, e não é validável offline de ponta a ponta. **Correção recomendada:** em `load_pdf_corpus` e `classify_pdf`, considerar só os registos com `source_type == "pdf"`. |
| L3 (duplicação acquire/discover) | Scripts de rede de uma fase concluída (raw imutável); não há regressão offline possível. |
| L4 (`stdout.reconfigure` repetido) | São duas linhas explícitas; abstraí-las esconderia o porquê (Windows). |
| L5 (`store._collection`) | Não existe API pública equivalente em `langchain_chroma`; fica documentado com um comentário. |
| L6 (`--documents` desconhecido ignorado na etapa Web) / L7 (sem tratamento de erros) | Seria uma alteração de comportamento. |
| L8 (listas de resíduos diferentes) | São intencionais (etapas diferentes). |
| L9 (`rag_smoke_test` duplica a baseline) | É um artefacto histórico com configuração própria e fica congelado. |
| L11 (`get_place_category` sem uso, estado global no D1) | O D1 está fechado e o estado global é uma decisão deliberada. |
| L12 (`tempCodeRunnerFile.py`) | É um ficheiro local ignorado pelo git; pode ser apagado à mão. |
| L13 (limpeza de `chunk_documents.json`) | É inofensiva. |
| L15 (TypedDict/dataclass para chunks/manifest) | Não há type checker; arriscaria a forma do JSON (ver audit §10). |
| Função `answer(store, question, config)` que orquestra retrieve→prompt→generate | Seria funcionalidade nova; pertence à fase de avaliação. A CLI imprime o retrieval antes de chamar o LLM, e juntar os dois mudaria o timing do output. |

## 8. Regression Validation

**Testes.** Antes: 89 OK. Depois: **98 OK** (89 originais + 9 novos), ~8 s, offline.

Testes adicionados (só onde o refactor extraiu ou alterou comportamento sem cobertura):

- `test_corpus.py` (6): ordem do manifest; JSON inválido, `document_id` duplicado ou em
  falta com número de linha; manifest ausente; manifest real com 32 IDs únicos; formato de
  bytes do `write_jsonl` (UTF-8 literal, LF); formato `sha256:` de ficheiro e de bytes.
- `test_rag_baseline.py` (2): `BASELINE` igual aos valores exatos da baseline; `generate`
  passa `llama3.2:3b` / `0.1` ao `ChatOllama` (com mock).
- `test_chunk_documents.py` (1): ID desconhecido → `ValueError`, não `SystemExit`.

Testes alterados: `test_rag_baseline.py` passa a importar `rag_pipeline` (core) e
`rag_baseline` (só para `chunk_body`, que é de apresentação). Nenhuma asserção existente
foi alterada.

**Artefactos (SHA-256 antes/depois).**

| Artefactos | Ficheiros | Diferenças |
|------------|-----------|------------|
| PDF Markdown (`data/processed/*.md`) | 8 | 0 |
| Web Markdown (`data/processed/web/*.md`) | 24 | 0 |
| `manifest.jsonl`, `chunks.jsonl`, `chunk_stats.json` | 3 | 0 |
| `chroma_baseline/`, `chroma_smoke/` (lidos só como bytes) | 10 | 0 |

**Saídas determinísticas regeneradas.**

- PDF e Web: `test_processed_files_match_a_fresh_render` renderiza os 32 documentos a partir
  do raw e compara com os ficheiros persistidos → iguais.
- Chunking: `chunk_documents.main()` foi executado com o output redirecionado para um
  diretório temporário → `chunks.jsonl` e `chunk_stats.json` **byte-idênticos** aos
  commitados. `--documents nope` → mesma mensagem, exit 1.

**Equivalência antigo vs. novo (RAG e D1),** com o `rag_baseline.py` de `b35ffbd` lado a
lado com o novo, fake embeddings, Chroma em diretório temporário e Ollama simulado:

- relatório de build e metadata/documentos guardados na coleção: iguais (317 indexados; 11
  `page_labels` e 2 `caption_panel` excluídos);
- transcrição completa da CLI para 5 perguntas × {com contexto + resposta, retrieval-only}
  (53 459 caracteres): igual;
- argumentos do `ChatOllama`, `SYSTEM_PROMPT`, `METADATA_FIELDS`, configuração,
  `STORE_DIR` e `--help`: iguais;
- D1: transcrição de 17 turnos (resposta + `last_place`/`last_category`/`pending_action`)
  com a mesma seed: igual.

**Outras verificações.** `compileall` OK; todos os 9 scripts importam sem erro;
`--help` de preprocessing PDF/Web e chunking OK; nenhum import morto (análise AST). Não
existe lint/type checker configurado no projeto, e nenhum foi instalado.

## 9. Remaining Technical Debt

1. **M6** — `discover_web_corpus.py` não é reexecutável com o manifest atual (correção de
   uma linha, recomendada à parte).
2. Duplicação acquire/discover (L3) e `rag_smoke_test` (L9): congeladas por decisão.
3. Esquema dos chunks implícito (`dict[str, Any]`), imposto em runtime por
   `validate_chunks`. Reavaliar TypedDict se for adotado um type checker.
4. `SYSTEM_PROMPT` continua a ser uma constante fora do `RAGConfig`. Se a avaliação comparar
   prompts, deve passar a fazer parte da configuração.
5. Não há lint/type checking. Recomendação: `ruff` (baixo custo), não instalado.
6. O embedding trunca em 128 tokens ~70% dos chunks (limitação conhecida, documentada em
   `RAG_BASELINE_SMOKE_TEST.md`). É uma questão experimental, não de código.

## 10. Conclusion

**IS THE PROJECT STRUCTURE APPROPRIATE FOR THE NEXT EVALUATION PHASE? — YES.**

O retrieval pode ser avaliado sem LLM (`rag_pipeline.retrieve`), o prompt e a geração sem
Chroma (`build_messages`, `generate`), a vector store reconstrói-se à parte (`build_store`)
e a configuração experimental é um objeto explícito e serializável (`BASELINE`). Os
utilitários de corpus são reutilizáveis (`corpus.py`) e a CLI é apenas uma interface. Tudo
isto foi conseguido com dois módulos novos, sem dependências novas e sem alterar nenhum
artefacto, configuração ou output.
