# Code Quality & Architecture Audit

Data: 2026-09-28. Âmbito: D1 (`d1_rule_based/`) e D2 (`d2_rag/scripts/`, `d2_rag/tests/`),
`pyproject.toml`, manifest e artefactos gerados. Auditoria feita **antes** de qualquer
alteração de código, sobre o commit `b35ffbd` (working tree limpo).

Estado inicial verificado:

- `python -m unittest discover -s d2_rag/tests` → **89 testes, OK** (7.4 s, offline).
- Hashes SHA-256 registados para 35 artefactos determinísticos (8 PDF Markdown, 24 Web
  Markdown, `manifest.jsonl`, `chunks.jsonl`, `chunk_stats.json`) e, só como bytes, para os
  10 ficheiros de `chroma_baseline/` e `chroma_smoke/` (nenhuma das bases foi aberta).
- Não existe ferramenta de lint/type checking configurada (sem ruff/mypy/pytest no projeto).

---

## 1. Current Architecture

```
ConversationalParadigms/
├── pyproject.toml            # projeto "virtual" uv (sem build-system), Python ≥ 3.13
├── d1_rule_based/
│   ├── eliza.py              # ELIZA original do NLTK (referência)
│   └── coimbra_guide.py      # agente rule-based: tabela de regras + contexto mínimo global
└── d2_rag/
    ├── scripts/              # cada ficheiro é um entry point executado como ficheiro
    │   ├── discover_web_corpus.py      # Crawl4AI: descoberta/classificação (rede)
    │   ├── acquire_web_corpus.py       # Crawl4AI: aquisição raw HTML + manifest (rede)
    │   ├── preprocess_documents.py     # PDF → Markdown (PyMuPDF, determinístico)
    │   ├── preprocess_web_documents.py # HTML → Markdown (BeautifulSoup, determinístico)
    │   ├── chunk_documents.py          # Markdown → chunks.jsonl + chunk_stats.json
    │   ├── rag_smoke_test.py           # 1.º smoke test (histórico, só PDF, chroma_smoke)
    │   └── rag_baseline.py             # baseline RAG unificada (Chroma + HF + Ollama + CLI)
    ├── tests/                # unittest; importam os scripts via sys.path.insert
    └── data/                 # manifest.jsonl, raw/, processed/, chunks/, chroma_*/
```

Fluxo de dados (cada etapa é um script independente, ligado por ficheiros):

```
approved_urls.jsonl ─acquire→ raw/web/*.html ─preprocess_web→ processed/web/*.md ┐
raw/*.pdf ───────────────────────────────preprocess_pdf→ processed/*.md ─────────┤
                                            manifest.jsonl (fonte de verdade) ───┤
                                                                   chunk_documents┘
                                          → chunks/chunks.jsonl → rag_baseline → chroma_baseline/
```

Dependências entre módulos (imports locais):

- `chunk_documents` → `preprocess_documents` (apenas para a constante `ROUTE_DOCUMENT_IDS`,
  via `sys.path.insert`).
- Todos os outros scripts são independentes entre si.
- Os testes importam cada script como módulo top-level (`sys.path.insert(0, scripts/)`).

## 2. Strengths

O código está, na generalidade, bem estruturado para um projeto académico. Pontos fortes
concretos:

1. **Pipeline por ficheiros com contratos explícitos.** Cada etapa lê/escreve artefactos
   versionados; o manifest é a fonte de verdade de proveniência.
2. **Determinismo verificado por testes.** `test_processed_files_match_a_fresh_render`
   (PDF e Web) e `test_persisted_chunks_are_valid_and_reproducible` comparam o output fresco
   com os ficheiros persistidos, byte a byte. Isto é a melhor rede de segurança para um
   refactor.
3. **Funções core puras e pequenas.** `parse_units`, `split_unit_body`, `html_to_blocks`,
   `render_markdown`, `build_context`, `build_messages`, `format_sources` são testáveis sem
   I/O.
4. **Dependências pesadas importadas tardiamente** (`langchain_huggingface`, `chromadb`,
   `ollama`, `langchain_ollama` dentro das funções): os testes correm sem Ollama, sem
   download de modelos e sem rede (fake embeddings + Chroma em diretório temporário).
5. **`pathlib` em todo o lado, raiz resolvida a partir de `__file__`.** Nenhuma dependência
   do cwd; escrita com `newline="\n"` e `encoding="utf-8"` explícitos (bytes estáveis em
   Windows).
6. **Regras de domínio documentadas com o PORQUÊ.** Ex.: `MIN_BLANK_PAGES_FOR_BREAK`,
   `SECTION_RESET_PAGES`, `letter_spacing_fonts`, `OPERATIONAL_SENTENCE`, `DROP_SECTIONS`.
7. **PDF e Web mantidos separados** — semânticas de extração genuinamente diferentes
   (layout PyMuPDF vs. DOM Elementor). Não há falsa abstração.
8. **Erros de pipeline RAG com mensagens acionáveis** (`BaselineError`: "Run with
   --rebuild", "ollama pull …") e exit code 2 distinto.
9. **Sem imports mortos** (verificado por análise AST de todos os `.py`).

## 3. Findings

Severidade: **HIGH** = afeta a correção ou bloqueia a fase seguinte (avaliação);
**MEDIUM** = dívida estrutural com custo real de manutenção/teste; **LOW** = cosmético,
localizado ou de benefício marginal.

### HIGH

#### H1 — Configuração experimental da baseline presa em globais de módulo

- **Localização:** `scripts/rag_baseline.py:33-41`, usada em `load_embeddings` (l.114),
  `_chroma` (l.124-127), `retrieve` (l.169), `check_ollama` (l.258), `generate` (l.272).
- **Problema:** `generate()` usa `LLM_MODEL`/`LLM_TEMPERATURE` globais sem parâmetro;
  `_chroma()` usa `COLLECTION_NAME`/`DISTANCE_SPACE` globais; `load_embeddings()` usa
  `EMBEDDING_MODEL` global; `select_indexable()` usa `INDEXED_ROLES` global.
- **Evidência:** não há forma de gerar uma resposta com outra temperatura ou de abrir outra
  coleção sem *monkeypatching* do módulo. Não existe um objeto único que descreva a
  configuração usada numa execução.
- **Impacto:** a fase seguinte é avaliação quantitativa. O `D2_PLAN.md` (§ reprodutibilidade)
  exige registar modelo, temperatura, retrieval settings e versão do índice com os outputs.
  Com globais dispersas, cada script de avaliação teria de copiar os valores à mão (risco de
  divergência silenciosa entre o que se executa e o que se reporta).
- **Recomendação:** um `@dataclass(frozen=True) RAGConfig` com uma instância `BASELINE`
  (valores **exatamente** iguais aos atuais), passado como parâmetro opcional
  (`config=BASELINE`) às funções que hoje leem globais. Serializável com
  `dataclasses.asdict`. Sem framework de configuração.

### MEDIUM

#### M1 — `rag_baseline.py` mistura o pipeline RAG com a CLI

- **Localização:** `scripts/rag_baseline.py` (374 linhas).
- **Problema:** o mesmo módulo contém configuração, carregamento de chunks, conversão de
  metadata, embeddings, Chroma build/open, retrieval, contexto/prompt, fontes, Ollama **e**
  apresentação (`section`, `print_retrieval`, `answer_question`, `main`, loop interativo).
  `answer_question` intercala `print` com os passos do pipeline.
- **Evidência:** um futuro script de avaliação que queira `retrieve` + `build_messages` +
  `generate` teria de importar um módulo chamado "baseline" cujo docstring o descreve como
  "interactive smoke test", arrastando a camada de apresentação.
- **Impacto:** coesão baixa; o nome do módulo deixa de corresponder ao papel quando houver
  mais de uma configuração. As funções individuais já são testáveis (ponto forte 3), por isso
  o impacto é MEDIUM e não HIGH.
- **Recomendação:** separar em **dois** módulos (não quatro): `rag_pipeline.py` (core, sem
  `print`/`argparse`/`input`) e `rag_baseline.py` (só CLI, mesmos comandos e output — os
  comandos documentados nos relatórios continuam válidos).

#### M2 — Leitura do manifest implementada seis vezes, com validação divergente

- **Localização:**
  `preprocess_documents.load_manifest` (l.279, **valida** JSON, `document_id` em falta e
  duplicado, com número de linha); `preprocess_web_documents.load_manifest` (l.405, sem
  validação); `chunk_documents.load_records` (l.306, inline, sem validação);
  `rag_smoke_test.load_manifest` (l.71); `acquire_web_corpus.load_jsonl(MANIFEST_PATH)`
  (l.191); `discover_web_corpus` (l.311, 347, 381 — três leituras inline).
- **Problema:** o manifest é a fonte de verdade do corpus, mas só a etapa PDF deteta um
  manifest corrompido ou com IDs duplicados. O chunker — que produz o input da vector store —
  aceitaria um `document_id` duplicado sem aviso (só falharia mais tarde, em
  `validate_chunks`, com uma mensagem sobre `chunk_id`).
- **Impacto:** duplicação real (código equivalente) + inconsistência de validação entre
  etapas que consomem o mesmo ficheiro.
- **Recomendação:** um único `load_manifest` validado num módulo partilhado, usado pelas
  etapas determinísticas (PDF, Web, chunking). Filtros por `status`/`source_type` ficam
  junto de cada consumidor (são diferentes em cada etapa e são uma linha).

#### M3 — Chunking acoplado ao script de preprocessing PDF; contrato de formato duplicado

- **Localização:** `chunk_documents.py:27-28` (`sys.path.insert` +
  `from preprocess_documents import ROUTE_DOCUMENT_IDS`); `chunk_documents.py:44`
  (`CAPTION_PANEL_MARKER = "<!-- caption_panel -->"`) vs.
  `preprocess_documents.py:61` (`CAPTION_PANEL_COMMENT = "<!-- caption_panel -->"`).
- **Problema:** para ler uma constante, o chunker importa 760 linhas de extração PDF e
  exige `pymupdf` instalado. O marcador de painel de legendas é um contrato
  produtor→consumidor escrito como dois literais independentes.
- **Impacto:** acoplamento desnecessário entre etapas; se o marcador mudar num lado, o
  chunker passa a fundir legendas no conteúdo (apanhado apenas indiretamente pelo teste de
  reprodutibilidade).
- **Recomendação:** mover `ROUTE_DOCUMENT_IDS` e o marcador para o módulo partilhado do
  corpus; ambos os scripts importam daí. Remove o `sys.path.insert`.

#### M4 — Função core do chunker termina o processo (`SystemExit`)

- **Localização:** `chunk_documents.load_records` (l.311).
- **Problema:** `raise SystemExit(...)` dentro de uma função reutilizável (usada pelos
  testes) em vez de uma exceção de domínio; `preprocess_documents._select_records` faz o
  mesmo caso com `ValueError`.
- **Impacto:** acoplamento core → processo; inconsistente entre etapas; mais difícil de
  testar.
- **Recomendação:** `ValueError` na função; `main()` converte em mensagem para stderr e
  exit code 1 (o mesmo comportamento observável que `SystemExit(str)` tem hoje).

#### M5 — Constantes de caminho redefinidas em cada script

- **Localização:** `D2_ROOT = Path(__file__).resolve().parents[1]` em 7 scripts;
  `MANIFEST_PATH` em 6; o caminho dos chunks existe como `CHUNKS_DIR` (chunker) e
  `CHUNKS_PATH` (RAG), e ainda literal nos testes.
- **Problema:** o layout de `data/` está espalhado; o contrato "o chunker escreve onde o RAG
  lê" depende de dois literais estarem sincronizados.
- **Impacto:** baixo risco hoje (tudo relativo a `__file__`, sem dependência do cwd), mas é
  a duplicação mais transversal do projeto.
- **Recomendação:** centralizar **só os caminhos partilhados** (`D2_ROOT`, `DATA_DIR`,
  `MANIFEST_PATH`, `CHUNKS_DIR`, `CHUNKS_PATH`) no módulo partilhado. Caminhos usados por um
  único script (ex.: `RAW_WEB_DIR`, `web_discovery/`) ficam onde estão.

#### M6 — `discover_web_corpus.py` falha com o manifest atual (bug latente)

- **Localização:** `discover_web_corpus.classify_pdf` (l.333) e `load_pdf_corpus` (l.309).
- **Problema:** ambos assumem que todos os registos do manifest são PDF (verdade quando o
  script foi escrito). Desde a aquisição web, o manifest tem 24 registos `web_page` sem
  `original_filename`.
- **Evidência (reproduzida offline):**
  `classify_pdf("…/x_PT_.pdf", manifest)` → `KeyError: 'original_filename'`. Além disso,
  `load_pdf_corpus` incluiria as páginas web no "corpus PDF", pelo que uma nova descoberta
  marcaria as páginas já adquiridas como sobreposição com elas próprias.
- **Impacto:** `--discover` e `--reclassify-pdfs` já não são reexecutáveis. Não afeta nenhum
  artefacto existente nem a fase de avaliação.
- **Recomendação:** filtrar `source_type == "pdf"` nas duas funções. **Não implementado neste
  refactor**: é uma correção de comportamento (de crash para resultado), fora do âmbito
  "preservar 100% do comportamento", e o script não pode ser validado offline de ponta a
  ponta. Fica registado como correção recomendada de uma linha.

### LOW

| ID | Localização | Problema | Recomendação |
|----|-------------|----------|--------------|
| L1 | `preprocess_documents._sha256`, `preprocess_web_documents.render_document` (inline), `acquire_web_corpus._sha256` | Formato `"sha256:<hex>"` implementado três vezes. | Helper partilhado (trivial) nas etapas tocadas. |
| L2 | 8 leituras e 3 escritas JSONL | `[json.loads(l) for l in …splitlines() if l.strip()]` repetido; escrita `json.dumps(…, ensure_ascii=False) + "\n"`. | `read_jsonl`/`write_jsonl` partilhados nas etapas tocadas; bytes idênticos. |
| L3 | `acquire_web_corpus.py`, `discover_web_corpus.py` | `USER_AGENT`, `SITE_HOST`, `_html_attr`, construção do `AsyncHTTPCrawlerStrategy` duplicados. | Não mexer: scripts de rede de uma fase concluída (raw é imutável), sem validação offline possível. |
| L4 | 6 `main()` | `sys.stdout.reconfigure(encoding="utf-8")` repetido. | Não mexer (2 linhas explícitas; abstrair esconde o porquê Windows). |
| L5 | `rag_baseline.py:147,149,159` | Uso de API privada `store._collection` (`count`, `get`). | Aceitar; `langchain_chroma` não expõe contagem pública. Documentar. |
| L6 | `preprocess_web_documents.main` | `--documents` com ID desconhecido é ignorado em silêncio (PDF e chunker rejeitam). | Documentar; corrigir altera comportamento (fora de âmbito). |
| L7 | `preprocess_web_documents.main` | Sem tratamento de erros: hash raw divergente sai como traceback (a mensagem é clara). | Documentar. |
| L8 | `preprocess_web_documents.validate` vs `chunk_documents.WEB_TEMPLATE_RESIDUE` | Listas de resíduos de template diferentes. | Intencional (etapas diferentes, marcadores diferentes). Não unificar. |
| L9 | `rag_smoke_test.py` | Duplica embeddings/Chroma/retrieval/Ollama da baseline. | Manter congelado: é o artefacto do 1.º smoke test (`RAG_SMOKE_TEST.md`), com coleção e chunking próprios. |
| L10 | `coimbra_guide.find_places` (l.666) | `if place not in places` compara `str` com lista de tuplos: a deduplicação nunca atua (sem efeito hoje, porque cada local aparece uma vez em `KNOWN_PLACES`). | Corrigir a comparação (trivial, comportamento idêntico). |
| L11 | `coimbra_guide.py` | `get_place_category` nunca é usada; estado conversacional em globais. | Manter: o estado global é uma decisão deliberada de simplicidade (ELIZA-like) e o D1 é entregável fechado. |
| L12 | `scripts/tempCodeRunnerFile.py` | Artefacto do VS Code Code Runner (fragmento de prompt, sintaxe inválida). Já está no `.gitignore`. | Pode ser apagado localmente; não tocado. |
| L13 | `chunk_documents.main` (l.513-515) | Remove `chunk_documents.json` antigo (compatibilidade com nome de output anterior). | Manter (inofensivo, idempotente). |
| L14 | `rag_baseline.section()` | Nome ambíguo: imprime um banner, mas "section" é também metadata de chunk. | Renomear para `print_section` ao separar a CLI (M1). |
| L15 | chunks/manifest como `dict[str, Any]` | Esquema implícito (24 campos por chunk). | Não introduzir TypedDict/dataclass agora (ver §10). |

## 4. Duplication

| Duplicação | Ocorrências | Equivalente? | Decisão |
|------------|-------------|--------------|---------|
| Leitura do manifest | 6 módulos (8 sítios) | Sim (parse); validação diverge | Unificar nas etapas determinísticas (M2) |
| Leitura JSONL genérica | 8 | Sim | Helper partilhado onde se toca (L2) |
| Escrita JSONL | chunker + discover (2×) | Sim | Helper no chunker; discover não se toca (L3) |
| SHA-256 `"sha256:"` | 3 + testes | Sim | Helper partilhado nas etapas PDF/Web (L1) |
| `D2_ROOT`/`MANIFEST_PATH`/chunks path | 7 / 6 / 2 | Sim | Centralizar (M5) |
| `ROUTE_DOCUMENT_IDS`, marcador `caption_panel` | 2 | Sim (contrato) | Centralizar (M3) |
| Embeddings/Chroma/retrieve/Ollama | `rag_smoke_test` vs `rag_baseline` | Parcial (config, coleção e chunking diferentes) | Não unificar (L9) |
| `chunk_body` | chunker (dict, usa `heading_context`) vs RAG (Document sem `heading_context`) | **Não** | Manter ambos |
| `_shingles` | discover vs chunker | **Não** (tratamento de textos < n palavras difere) | Manter ambos |
| Front matter em `render_markdown` | PDF vs Web | **Não** (campos diferentes) | Manter ambos |
| Escrita do manifest | `acquire.write_manifest` (upsert ordenado) vs `preprocess_web.write_web_records` (substituição in-place) | **Não** (semântica diferente, ambos preservam linhas PDF byte a byte) | Manter ambos |
| `USER_AGENT`, `_html_attr`, crawler HTTP | acquire vs discover | Sim | Não mexer (L3) |

## 5. Responsibility Analysis

| Módulo | Responsabilidades atuais | Avaliação |
|--------|--------------------------|-----------|
| `preprocess_documents.py` (763 l.) | config por documento, extração PyMuPDF por layout, limpeza, Markdown, validação, CLI | Coeso: tudo é "PDF → Markdown". Tamanho justificado por regras de layout reais. `_render_page_body` (60 l.) é uma cascata linear de regras — legível, não dividir. Só a leitura do manifest e o hash pertencem a outro sítio. |
| `preprocess_web_documents.py` (494 l.) | seleção DOM, `Walker`, pós-processamento de blocos, Markdown, validação, escrita do manifest, CLI | Coeso. `Walker._widget` é longo mas é um dispatch por tipo de widget — dividir espalharia a lógica Elementor. |
| `chunk_documents.py` (522 l.) | parse estrutural, split, proveniência, validação, estatísticas, CLI | Coeso: uma responsabilidade ("produzir e validar `chunks.jsonl`"). Validação/estatísticas poderiam ir para outro ficheiro, mas só são usadas aqui (§10). Problemas reais: M3, M4, M5. |
| `rag_baseline.py` (374 l.) | config + dados + vector store + retrieval + prompt + LLM + CLI | Baixa coesão (M1) e configuração não parametrizável (H1). |
| `discover_web_corpus.py` (603 l.) | robots/sitemaps, crawl, análise, classificação, outputs | Coeso para uma ferramenta de descoberta; bug M6. |
| `acquire_web_corpus.py` (239 l.) | fetch, verificação, manifest | Coeso. |
| `rag_smoke_test.py` (375 l.) | pipeline completo do 1.º smoke test | Histórico, autocontido; não tocar. |
| `coimbra_guide.py` | regras, contexto, CLI | Adequado ao paradigma ELIZA. |

## 6. Dependency Boundaries

- **CLI → core:** nos scripts de preprocessing e chunking, `main()` faz parsing e
  apresentação e as funções core devolvem dados/estatísticas. Boa separação.
- **Violações:**
  - `chunk_documents.load_records` → `SystemExit` (M4).
  - `acquire_web_corpus.acquire` → `SystemExit` e `print` (script de rede; não mexer).
  - `rag_baseline.answer_question` mistura pipeline e `print` (M1).
  - `chunk_documents` → `preprocess_documents` → `pymupdf` (M3).
- **Bibliotecas externas:** Chroma, HuggingFace e Ollama só são tocadas em 4 funções
  (`load_embeddings`, `_chroma`, `check_ollama`, `generate`), todas com import tardio. Boa
  fronteira; manter.

## 7. Testability

- Offline e sem serviços: 89 testes cobrem parsing, chunking, Web/PDF end-to-end contra os
  artefactos reais, metadata, vector store com fake embeddings, contexto e prompt.
- **Lacunas relevantes para o refactor:**
  - `generate()` e `check_ollama()` não têm testes (dependem de Ollama). Depois de H1,
    `generate` passa a receber a configuração — deve haver um teste (com `mock`) que prove
    que o modelo e a temperatura da baseline chegam ao `ChatOllama`.
  - Nenhum teste fixa os valores da configuração experimental (um valor alterado por engano
    não seria detetado).
  - A validação do manifest (`load_manifest`) não tem testes, e passará a proteger três
    etapas.
- Os testes usam `sys.path.insert` para importar scripts. É a consequência de os scripts
  serem executados como ficheiros; aceitável (§10).

## 8. Proposed Target Structure

```
d2_rag/scripts/
├── corpus.py                    NOVO  layout de data/, JSONL, manifest validado, SHA-256,
│                                      contrato partilhado do Markdown processado
├── preprocess_documents.py            PDF → Markdown (usa corpus)
├── preprocess_web_documents.py        HTML → Markdown (usa corpus)
├── chunk_documents.py                 Markdown → chunks (usa corpus; já não importa o PDF)
├── rag_pipeline.py              NOVO  RAGConfig/BASELINE, chunks→Documents, embeddings,
│                                      Chroma build/open, retrieval, contexto/prompt,
│                                      fontes, Ollama — sem print/argparse
├── rag_baseline.py                    só CLI (mesmos argumentos, mesmo output)
├── discover_web_corpus.py             inalterado (M6 documentado)
├── acquire_web_corpus.py              inalterado
└── rag_smoke_test.py                  inalterado (histórico)
```

**Porque não um package `d2_rag/rag/` ou `d2_rag/core/`:** os scripts são executados como
ficheiros (`uv run python d2_rag/scripts/x.py`), pelo que `scripts/` já está no `sys.path` e
módulos irmãos importam-se sem *hacks*. Um package exigiria `sys.path` manipulado em cada
script ou transformar o projeto uv (hoje sem `build-system`) num package instalável —
alteração de configuração do projeto sem benefício proporcional. Dois módulos novos chegam
para os objetivos: retrieval avaliável sem LLM, geração testável sem Chroma, vector store
reconstruível à parte, CLI como mera interface, utilitários de corpus reutilizáveis e
configuração experimental explícita.

## 9. Refactor Plan

Ordenado por prioridade; cada passo validado com a suite antes do seguinte.

1. **`corpus.py`** (M2, M3, M5, L1, L2): caminhos partilhados, `read_jsonl`/`write_jsonl`,
   `load_manifest` validado (movido de `preprocess_documents`, sem alterações), `sha256_*`,
   `ROUTE_DOCUMENT_IDS`, `CAPTION_PANEL_MARKER`. Testes próprios.
2. **Preprocessing PDF e Web** passam a usar `corpus` (sem alterar extração/render).
   Validação: testes de reprodutibilidade PDF e Web + hashes.
3. **Chunking** usa `corpus`; remove `sys.path.insert` e a dependência de
   `preprocess_documents`; `load_records` levanta `ValueError` (M4). Validação: teste de
   reprodutibilidade dos chunks + regeneração de `chunks.jsonl`/`chunk_stats.json` para
   diretório temporário e comparação de hashes.
4. **`rag_pipeline.py` + `RAGConfig`** (H1, M1): mover o core, parametrizar pela configuração;
   `rag_baseline.py` fica só CLI (L14). Testes: imports atualizados, teste da configuração
   exata da baseline, teste de `generate` com mock.
5. **D1** (L10): corrigir a comparação em `find_places`.
6. Regressão completa: suite, compile check, hashes de todos os artefactos, `git diff`.

## 10. Things NOT Worth Refactoring

1. **Dividir `rag_baseline.py` em 4+ ficheiros** (`config.py`, `vector_store.py`,
   `retrieval.py`, `generation.py`). Cada um teria 20-60 linhas; a separação core/CLI resolve
   o problema real. Micro-módulos só acrescentam imports.
2. **Unificar preprocessing PDF e Web** numa abstração `Preprocessor`/`Extractor`. As
   semânticas são diferentes (geometria de página vs. DOM); só utilitários (hash, manifest,
   JSONL) são partilhados.
3. **Package instalável / `src/` layout / entry points no `pyproject.toml`.** Mudaria a
   configuração do projeto e a forma de executar os scripts documentada nos relatórios.
4. **Dataclass/TypedDict para chunks e registos do manifest.** Não há type checker
   configurado; os registos são serializados diretamente para JSONL e o manifest é reescrito
   preservando linhas PDF byte a byte — um modelo tipado arriscaria alterar a ordem/forma
   das chaves. O contrato dos chunks já é imposto em runtime por `validate_chunks` e
   documentado em `CHUNKING_REPORT.md`. Reavaliar se for adotado mypy.
5. **Pydantic, sistema de configuração (YAML/TOML/env), DI, factories, repositories.**
   Um dataclass congelado cobre a necessidade.
6. **Separar validação/estatísticas do chunker** para outro ficheiro. Só o chunker as usa;
   a coesão atual ("produzir e validar chunks") é boa.
7. **Tocar `discover_web_corpus.py` e `acquire_web_corpus.py`** para remover duplicação
   (L3). Fase concluída, raw imutável, sem forma de validar offline. A única alteração que
   se justifica aí é a correção M6, que é de comportamento.
8. **Tornar `rag_smoke_test.py` dependente de `rag_pipeline`.** Alteraria um artefacto
   histórico com configuração própria (coleção `d2_rag_smoke`, chunking por página).
9. **Refatorar o D1** (classe para o estado, separar regras em ficheiro de dados). O D1 é
   deliberadamente um ELIZA simples e está fechado.
10. **Abstrair `sys.stdout.reconfigure`** e outras duas-linhas de `main()`.
11. **Introduzir ruff/black/mypy/pytest** nesta tarefa. Recomendação para depois: `ruff`
    (lint + imports) é o de melhor custo/benefício; não instalado.
12. **Substituir `store._collection`** por API pública: não existe equivalente direto em
    `langchain_chroma` para `count()`.
