# Unified Corpus Chunking Report

## 1. Objective

Transformar os 32 documentos processados (PDF e Web) em chunks semanticamente
coerentes, com contexto estrutural e proveniência completa, e auditá-los **antes**
de gerar embeddings. A pergunta desta fase é: *os chunks preservam unidades de
significado, contexto estrutural e proveniência suficientes para serem
indexados?*

Não foram criados embeddings nem Vector DB, não foi implementado retrieval, e não
foi usado nenhum LLM. O corpus processado não foi alterado.

## 2. Input Corpus

Todos os registos `accepted` do `data/manifest.jsonl`:

| Tipo | Documentos | Origem |
|---|---:|---|
| PDF | 8 | `data/processed/*.md` (com `<!-- source_page: N -->`) |
| Web | 24 | `data/processed/web/*.md` (sem páginas) |
| **Total** | **32** | |

O manifest é a fonte da metadata. O front matter dos Markdown só é usado para
validar o `document_id`.

## 3. Strategy

**Estrutura primeiro, divisão por caracteres depois.**

```text
Processed Markdown
  → parser de estrutura (headings, páginas, marcadores)
  → unidades semânticas = caminho de headings + conteúdo sob ele
  → unidade ≤ 1000 caracteres → 1 chunk
    unidade > 1000 caracteres → RecursiveCharacterTextSplitter DENTRO da unidade
  → re-merge de fragmentos órfãos dentro da unidade
  → chunks + metadata → validação → chunks.jsonl + chunk_stats.json
```

Motivo: o smoke test e o `PRE_CHUNKING_AUDIT` (§6) mostraram que um splitter
aplicado ao documento inteiro separa headings do conteúdo e mistura secções no
overlap. Neste desenho:
- o splitter só vê o corpo de uma unidade, por isso **nenhum chunk mistura duas
  secções** e o overlap é sempre local;
- entidades vizinhas (monumentos, museus, doces) nunca são fundidas para
  aproximar o tamanho: um chunk menor e completo é preferível.

Script: `d2_rag/scripts/chunk_documents.py`. Um único ficheiro faz o parse, o
chunking, a validação e as estatísticas.

## 4. Baseline Configuration

| Parâmetro | Valor |
|---|---|
| Splitter | `RecursiveCharacterTextSplitter` (`langchain-text-splitters` 1.1.2, já no projeto; nenhuma dependência nova) |
| `chunk_size` | **1000** |
| `chunk_overlap` | **100** |
| `length_function` | `len` (caracteres) |
| Separadores | `["\n\n", "\n", ". ", " ", ""]`: parágrafo → linha (listas/versos) → frase → palavra |
| `keep_separator` | `"end"` (a pontuação fica no fim do fragmento) |

**TEMPORARY BASELINE / TO BE EVALUATED.** Estes valores seguem a worksheet da
disciplina. Não foram afinados nem comparados, e não são apresentados como
ótimos. O tamanho aplica-se ao **corpo** do chunk; o contexto de headings é
acrescentado depois.

## 5. Markdown Structure Parsing

**Headings.** `#` é o título do documento: não abre secção, porque o título vem do
manifest. `##`–`######` mantêm uma pilha: um heading de nível *L* substitui os de
nível ≥ *L*. `section = path[0]`, `subsection = path[1]`, e `section_path` é o
caminho completo. Um heading sem conteúdo próprio (por exemplo
`## 1. UNIVERSIDADE…` seguido de `### PORTA FÉRREA`) não gera chunk, mas continua
no caminho dos filhos.

**Páginas PDF.** Os `<!-- source_page: N -->` passam a metadata e nunca aparecem no
texto. Cada bloco guarda a sua página. A página de um chunk é calculada pelos
offsets do splitter (`add_start_index`), por isso um chunk pode ter várias páginas.

**Continuação entre páginas.** Por omissão, a secção **continua** através de um
marcador de página até ao próximo heading (R1). Regras estruturais:

| Regra | Situação | Tratamento | Base |
|---|---|---|---|
| R1 | Texto que continua na página seguinte | mantém a secção; `source_pages` com as duas páginas | UC p10→11 (TORRE), p24→25 (Santa Rita); Joanina p2→3, p3→4 |
| R2 | Página só de legendas (sem headings; todas as linhas ≤ 60 caracteres e sem pontuação final) | unidade própria `unit_role="page_labels"`, `section=null`; a secção interrompida continua depois | 11 páginas da brochura UC (p15 "Casa da Livraria \| Biblioteca Joanina" deixava de ficar dentro de "2. CASA DOS MELO") |
| R3 | Página 2 dos 6 roteiros municipais | nova região, `section=null` (introdução lateral) | layout documentado no PREPROCESSING_REPORT; lista `ROUTE_DOCUMENT_IDS` do preprocessing PDF. Sem isto, "Em 1064, Coimbra torna-se…" ficava em "9. MOSTEIRO DE SANTA CLARA-A-NOVA". |
| R4 | `<!-- caption_panel -->` | unidade `unit_role="caption_panel"`, `section=null` | recomendação do PREPROCESSING_FIX_REPORT (M2/M3) |
| R5 | Linhas só com números (`8`, `10 11`) | não entram no texto; 28 contadas | páginas impressas e índice do mapa, só na brochura UC (M4) |
| R6 | ≥ 2 páginas seguidas sem texto | a secção não atravessa esse intervalo | UC p34–36 (mapa + título "Roteiros Temáticos"): os roteiros (p37–40) ficavam em "31. PALÁCIO DA JUSTIÇA". Uma **única** página sem texto (fotografia, UC p12) não interrompe: "COLÉGIO DE SÃO PEDRO" (p14) continua em "1. UNIVERSIDADE…". |

**Web.** Sem páginas e sem marcadores. A proveniência é `document_id`, `url`,
`canonical_url` e `section_path`. Os documentos sem headings internos (17 dos 24)
ficam com `section = null`, e **não foram inventados headings**. Citações `>` e
listas ficam na unidade onde aparecem.

## 6. Metadata Schema

Uma linha JSON por chunk em `data/chunks/chunks.jsonl`. Todos os campos existem em
todos os chunks, com `null` onde não se aplicam:

| Campo | PDF | Web | Nota |
|---|---|---|---|
| `chunk_id` | ✓ | ✓ | `<document_id>::c0001`, sequencial na ordem do documento |
| `document_id`, `source_type`, `title`, `source_organization`, `primary_category`, `language` | ✓ | ✓ | do manifest |
| `section`, `subsection`, `section_path` | ✓ | ✓ | `null` / `[]` quando não há heading |
| `unit_role` | ✓ | ✓ | `content` \| `page_labels` \| `caption_panel` |
| `source_pages` | lista | `null` | **representação principal**; um chunk pode ter várias páginas |
| `source_page` | int ou `null` | `null` | só quando há exatamente uma página (compatibilidade) |
| `source_file` | nome do PDF | `null` | |
| `url`, `canonical_url` | `null` | ✓ | |
| `conflict_notes` | do manifest | do manifest | propagado ao **nível do documento** (ver §13) |
| `unit_chunk_index`, `unit_chunk_count` | ✓ | ✓ | posição dentro da unidade semântica |
| `overlap_chars` | ✓ | ✓ | caracteres partilhados com o chunk anterior **da mesma unidade** |
| `body_chars` | ✓ | ✓ | tamanho do conteúdo substantivo |
| `heading_context` | ✓ | ✓ | `# título` e os headings do caminho |
| `text` | ✓ | ✓ | `heading_context + "\n\n" + corpo`: o texto a embeber no futuro |

**Duas representações.** O contexto estrutural fica no `heading_context` e o
conteúdo no corpo (`text` sem o prefixo). O texto a embeber leva sempre a entidade:

```text
# Herança Cultural e Religiosa
## Igrejas e Mosteiros
### Mosteiro de Santa Clara-a-Velha

Construído no século XIV nas margens do Rio Mondego, …
```

O título do documento entra em todos os chunks para dar contexto aos documentos
sem headings (por exemplo "Santo António"). O custo é, no máximo, 157 caracteres
de contexto.

## 7. Pilot

O piloto teve 7 documentos, examinados chunk a chunk **antes** do corpus completo:
- **PDF:** `fundacao-da-nacionalidade`, `universidade-alta-sofia-patrimonio-mundial`, `biblioteca-joanina-uctour`;
- **Web:** `web-visitecoimbra-heranca-cultural-e-religiosa`, `…-museus`, `…-docaria-conventual-de-coimbra`, `…-santo-antonio` (sem headings).

Foram encontrados e **corrigidos** três problemas estruturais antes de avançar:

| # | Problema | Evidência | Correção |
|---|---|---|---|
| 1 | Fragmentos órfãos. O splitter não junta o resto de um parágrafo grande com o parágrafo seguinte, e as coordenadas ficavam sozinhas em chunks de 37 caracteres. | Santa Cruz, Convento S. Francisco, título lateral "fundação da nacionalidade" | Re-merge de fragmentos adjacentes **dentro da unidade** quando o texto contíguo cabe em 1000. A Fundação passou de 19 para 15 chunks. |
| 2 | Página 2 dos roteiros atribuída à última secção da página 1 | intro histórica em "9. MOSTEIRO DE SANTA CLARA-A-NOVA" | R3 |
| 3 | Roteiros temáticos (UC p37–40) atribuídos a "31. PALÁCIO DA JUSTIÇA" | continuação através do mapa (p34–36) | R6. Uma primeira versão com 1 página vazia partia a secção 1 na p12; foi refinada para ≥ 2 páginas. |

**Resultado final do piloto:**
- headings junto ao texto certo;
- 26 monumentos, 23 museus e 9 doces, cada um no seu chunk e **sem fusões**;
- `section`/`subsection` corretos (`Igrejas e Mosteiros > Sé Velha de Coimbra`, `Doces a não perder > Crúzios`);
- continuações com `source_pages` corretos (`[10, 11]`, `[2, 3]`, `[3, 4]`);
- URLs corretas;
- Ceira: 1 documento → 1 chunk;
- Santo António, 3 chunks sem secção;
- overlap local (61 caracteres em Santa Cruz);
- citações e listas mantidas;
- sem front matter nem marcadores.

## 8. Corpus Statistics

| Métrica | Valor |
|---|---:|
| Documentos (PDF / Web) | 32 (8 / 24) |
| **Chunks** | **330** |
| Chunks PDF / Web | 206 / 124 |
| Corpo: min / p25 / mediana / média / p75 / max | 13 / 328 / 546 / 555 / 775 / **998** |
| Texto renderizado: min / mediana / max | 35 / 613 / 1075 |
| Corpo < 100 caracteres | 18 |
| Corpo > 1000 caracteres | **0** |
| Renderizado > 1000 (só por causa do contexto) | 25 |
| Chunks de unidades divididas | 160 |
| Chunks com overlap | 6 |
| Chunks multi-página | 8 |
| Chunks sem section | 95 |
| Chunks com subsection | 53 |
| Chunks com `conflict_notes` | 51 |
| Linhas de número de página omitidas | 28 |
| `unit_role` content / page_labels / caption_panel | 317 / 11 / 2 |

**Chunks por categoria:**

| Categoria | Chunks |
|---|---:|
| `university_heritage` | 77 |
| `culture_traditions` | 68 |
| `built_heritage` | 56 |
| `city_history` | 48 |
| `landscape_gardens` | 24 |
| `museums_collections` | 24 |
| `gastronomy` | 18 |
| `visitor_orientation` | 15 |

**Chunks por documento:**
- **PDF:** UC 68, Viver 29, Escritores 25, Jardins 24, Fado 23, Fundação 15, Pequenitos 13, Joanina 9.
- **Web:** Herança Cultural 27, Museus 24, Doçaria 12, Pedro e Inês 6, Canção 5; os restantes 19 têm 1–4 cada.

**Chunks sem secção (95), todos explicáveis:**
- 60 web: 17 documentos sem headings internos e introduções antes do primeiro heading;
- 14 da introdução da p2 dos roteiros;
- 11 `page_labels`;
- 8 PDF (introdução e índice da UC p6–7; roteiros temáticos p37–40);
- 2 `caption_panel`.

**Overlap.** Só aparece em 6 chunks. Com separadores de parágrafo, o
`RecursiveCharacterTextSplitter` só transporta overlap quando o corte cai **dentro**
de um parágrafo: um parágrafo inteiro com mais de 100 caracteres não cabe na janela
de 100. É o comportamento da baseline e fica registado para a fase de avaliação.

## 9. Small Chunk Audit

Os 18 chunks com corpo < 100 caracteres, classificados manualmente. **Nenhum foi
apagado.**

| Classe | N.º | Chunks |
|---|---:|---|
| Unidade curta útil: coordenadas com o heading da entidade no texto | 5 | Fundação c0008 (6. Santa Clara-a-Velha), Escritores c0014 (7. Jardim da Sereia), c0016 (8. Av. Sá da Bandeira), Viver c0025 (17. Praça 8 de Maio), e mais 1. O corpo da entidade tinha ~1000 caracteres, por isso as coordenadas não couberam. |
| Unidade curta útil: secção de uma frase | 2 | Herança Judaica c0003 (Projeto MIKVEH); Pedro e Inês c0006 (Mosteiro de Santa Clara-a-Velha) |
| Resto de divisão com significado | 1 | Canção c0005 (frase final da página) |
| Legenda, crédito ou contacto (isolados de propósito, `page_labels`) | 9 | UC c0001, c0002, c0006, c0018, c0022, c0026, c0048, c0067, c0068 |
| Ruído herdado do preprocessing | 2 | Joanina c0001 "O que visitar" (MINOR m7); Jardins c0022 "jardins Históricos" (título lateral da p2) |

**Conclusão:** o chunking **não cria lixo próprio**. O ruído restante vem do
preprocessing (já documentado) ou está marcado por `unit_role` e pode ser filtrado
no retrieval.

## 10. Large Chunk Audit

**Nenhum corpo excede 1000 caracteres** (máximo 998).

Os 25 chunks com **texto renderizado** acima de 1000 (máximo 1075) resultam
exclusivamente do contexto de headings (máximo 157 caracteres, por exemplo
`# Universidade de Coimbra — Alta e Sofia: Património Mundial` + `## 1. …` + `### …`).
Não é um bug; o limite aplica-se ao corpo.

## 11. Provenance Audit

- **PDF:**
  - todos os 206 chunks têm `source_pages` não vazio;
  - 8 são multi-página: Joanina `[2,3]` e `[3,4]`; UC `[6,7]` ×2, `[10,11]` TORRE, `[24,25]` Santa Rita, `[37,38]` e `[38,39]`;
  - verificado por teste: **todas as linhas de coordenadas** estão no chunk da secção cujo heading as precede no Markdown.
- **Web:**
  - todos os 124 chunks têm `url` do domínio `visitecoimbra.pt` e `source_pages = null`;
  - nenhum `source_page` foi inventado.
- **Amostras heading → facto** (em teste):

| Facto | Documento | Secção/subsecção |
|---|---|---|
| "Fundado em 1131" | Fundação | `2. IGREJA DE SANTA CRUZ \| PANTEÃO NACIONAL` |
| "Fundado, em 1131" | UC | `24. MOSTEIRO DE SANTA CRUZ - PANTEÃO NACIONAL` |
| "O exterior é robusto" | Fado | `7. SÉ VELHA` |
| "Mestre Roberto" | UC | `21. SÉ VELHA` |
| "concluída em 1728" | Joanina | `Biblioteca Joanina` |
| "morcegos" | Joanina | `Piso Nobre` |
| "Cassiano Branco" | Pequenitos | `6. PORTUGAL DOS PEQUENITOS` |
| "Cassiano Branco" | Fundação | `7. PORTUGAL DOS PEQUENITOS` |
| "museus de belas-artes" | web Museus | `Museu Nacional de Machado de Castro` |
| "Crúzios" | web Doçaria | subsection `Crúzios` |
| "Fundado pela Rainha Santa Isabel" | web Herança | subsection `Mosteiro de Santa Clara-a-Velha` |

## 12. Duplicate Analysis

Nada foi removido. Os métodos são determinísticos: hash do corpo normalizado e
contenção de 5-gramas ≥ 0.8.

| Tipo | Resultado |
|---|---|
| Duplicados exatos | **4 grupos**: Fado ↔ Viver (Paço das Escolas, 2 grupos); Herança web consigo própria (Mosteiro de São Francisco e Seminário Maior repetidos na própria página) |
| A) Mesmo documento | 2 pares (os cards repetidos da Herança web) |
| B) Entre documentos PDF | **26 pares**: Paço das Escolas (Fado, Viver, UC), AAC (Fado ↔ UC), Parque Verde (Pequenitos ↔ Jardins), Parque Manuel Braga, Jardim da Sereia, Av. Sá da Bandeira (Escritores ↔ Jardins), Sé Velha (Fado ↔ UC)… (é o M5 do audit) |
| C) PDF ↔ Web | **1 par (0.84)**: Casa-Museu Miguel Torga (Escritores c0022 ↔ Museus c0024) |

Estes números são a linha de base para medir o impacto da duplicação no retrieval.
A lista completa está em `data/chunks/chunk_stats.json`.

## 13. Known Issues

| Problema | Impacto |
|---|---|
| **Duplicação entre PDFs** (26 pares, sobretudo Paço das Escolas) | pode ocupar o top-k; medir na avaliação |
| **Sobreposição temática PDF/Web** com textos diferentes (Santa Clara-a-Velha, Sé Velha, Santa Cruz…) | o retrieval pode trazer versões concorrentes |
| **Conflitos de fonte** (Santa Clara-a-Velha): `conflict_notes` propagado ao **nível do documento** para os 51 chunks da Herança e dos Museus web | Opção desta baseline, porque o manifest é document-level. Não foi feita propagação por secção nem simétrica para o lado PDF (a Fundação não tem nota no manifest). Fica para a política de autoridade. |
| Overlap raro (6 chunks) | característica da baseline (§8) |
| Ruído residual do preprocessing | 2 chunks minúsculos (§9) |
| Regras R3/R6 dependem do layout conhecido destes PDFs | um PDF novo exige revisão |
| Coordenadas iguais para dois pontos no próprio PDF (Escritores 12 e 13) | fiel à fonte |
| **`chroma_smoke`**: os hashes de 3 ficheiros mudaram às 00:42:40 durante esta sessão (`chroma.sqlite3`, `data_level0.bin`, `length.bin`) | **Não foi causado pelo chunking** (experiência controlada: nem o chunker nem a suite completa a alteram). O conteúdo está intacto: 209 embeddings do build original (2026-09-25 23:12), `max_seq_id=209`, mesma coleção e diretório. O padrão (6 registos em `acquire_write`, índice HNSW regravado) é o de um processo que **abriu** a coleção, por exemplo uma consulta ao `rag_smoke_test.py`. A origem não foi identificada. |

## 14. Decision

**IS THE UNIFIED CORPUS READY FOR EMBEDDING?**

# YES

**Justificação:**
- **Validação:** os 330 chunks passam o contrato: IDs únicos, sem chunks vazios, metadata completa, PDF com páginas e Web com URL e sem páginas, sem front matter, marcadores ou resíduos de template, sem headings no corpo, e overlap só dentro da unidade.
- **Estrutura:** cada facto verificado está no chunk da sua entidade. As continuações entre páginas mantêm a secção, e as regiões novas (introduções, roteiros, legendas) não se colam a secções anteriores.
- **Tamanhos:** nenhum corpo excede a baseline. O chunking não cria chunks de lixo, e os pequenos estão classificados.
- **Reprodutibilidade:** duas execuções dão o mesmo `chunks.jsonl` (SHA-256 `ff50f77c…`); o ficheiro em disco é igual a um chunking fresco (teste); os `chunk_id` são determinísticos.
- **Testes:** 79/79 OK, sem rede (24 novos de chunking).
- **Corpus intacto:** os 65 hashes (8 PDF, 8 MD PDF, 24 HTML, 24 MD Web e manifest) estão iguais.

**Condições para a fase seguinte (não bloqueiam):**
- embeber o campo `text` (com contexto) e guardar o resto como metadata;
- decidir se `page_labels` e `caption_panel` entram no índice ou ficam filtrados;
- medir o efeito da duplicação (§12) e dos conflitos (§13) na avaliação de retrieval.

A geração de embeddings **não** foi feita e aguarda autorização.
