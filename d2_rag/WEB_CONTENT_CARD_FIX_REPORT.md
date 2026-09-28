# Web Content Card & Corpus Coverage Fix

Data: 2026-09-28. Ponto de partida: `WEB_CONTENT_GAP_AUDIT.md` (não repetido).

## 1. Scope

Correção focada do **corpus Web** antes do congelamento para avaliação formal:

1. recuperar os quatro content cards da página da tradição cervejeira, eliminados por `DROP_SECTIONS`;
2. rever explicitamente os false negatives já identificados em `cancao-de-coimbra` e `ceramica-de-coimbra`;
3. aprovar e adquirir as três páginas já descobertas: Coimbra by Night, Restauração, Desporto.

Fora de âmbito (inalterados): Walker em geral, algoritmo de preprocessing, chunking, embeddings,
`RAGConfig`, prompts, LLM, vector stores. Não foi aberta nova wave de discovery (Natureza e Rio,
Atividades em Família, Cultura, Ciência e Tecnologia continuam fora).

## 2. Changes Implemented

Todas em `scripts/preprocess_web_documents.py`, sob a forma de configuração por documento
(revista por humanos) ou de regra de template conhecida:

| Alteração | Tipo | Efeito |
|---|---|---|
| `DROP_SECTIONS`: removidas as entradas da cerveja (`BREW!`, `Epicura`, `Portuguese Pedro`, `Praxis`), de `cancao-de-coimbra` (`Casas para ouvir a Canção de Coimbra`) e de `ceramica-de-coimbra` (`Saber mais sobre a Louça de Coimbra`) | config | recupera o conteúdo (decisões nas secções 3–5) |
| `CARD_LIST_DOCUMENTS` (novo): cerveja, Canção de Coimbra, By Night, Restauração, Desporto | config | nestes documentos, os flip-boxes consecutivos passam a **uma lista** `- Nome — descrição`, pela ordem da fonte, em vez de um heading por card |
| `Walker(cards_as_list=...)` + `_merge_cards` | render | só se aplica aos documentos acima; o comportamento por omissão do handler `flip-box` (heading + parágrafo, p. ex. `museus`, `heranca-cultural-e-religiosa`) mantém-se igual |
| `DROP_WIDGETS += {"taxonomy-filter", "form"}` | template | filtros de categoria/preço e o formulário "adicione o seu espaço" do diretório de restaurantes |
| `CONTAINER_WIDGETS = {"loop-grid"}` | template | o loop grid da Restauração é percorrido como contentor, e cada restaurante passa pelo handler `flip-box` existente |
| Um item de accordion que fique vazio deixa de emitir o seu título | render | sem isto, o título do filtro "Preço" herdaria a lista de restaurantes que se segue ao accordion |
| `SITE_CTA_PARAGRAPHS` | template | remove "Faça parte desta lista!" e "Gostava que o seu espaço fizesse parte do nosso site?" (CTA dirigido a empresas) |
| `PRICE_TIER` | template | remove o escalão de preço (`\| €€`) da categoria dos cards |
| `VALIDITY_NOTES` | provenance | `validity_notes` nos 5 documentos que nomeiam estabelecimentos privados |

Porque não bastava remover o `DROP_SECTIONS`: o handler `flip-box` existente emite um heading
por card. Para a cerveja, isso criaria quatro secções `## BREW!` / `## Epicura` / ... e quatro
chunks de 13–30 caracteres, exatamente o que a tarefa pedia para evitar (não inventar
secções, manter os cards juntos). A lista por documento resolve isto sem alterar o
comportamento das páginas que já usavam flip-boxes como secções de entidade.

Imagens, a face traseira do flip-box, o botão "Saber mais" e os URLs de destino continuam
excluídos, como antes.

## 3. Beer Page Fix

`web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira`

**Before** (a narrativa terminava assim e não havia nenhum card):

```
... enquanto desfrutam da companhia de amigos e de uma vista sobre o rio Mondego.
```

**After** (a narrativa fica intacta e os cards vêm logo a seguir, no fluxo normal):

```
... enquanto desfrutam da companhia de amigos e de uma vista sobre o rio Mondego.

- BREW! — Festival de cerveja artesanal
- Epicura — Cerveja Artesanal
- Portuguese Pedro — Cerveja
- Praxis — Cervejaria, Restaurante
```

Verificado: cada nome aparece exatamente 1 vez e pela ordem da fonte (ids Elementor `1fb5ce9`,
`6e5bb02`, `62bd222`, `dc940ba`). No corpo não há `Saber mais`, `http`, `beerpraxis` nem
`instagram`, nem nenhum heading `## BREW!`. Não há duplicação front/back/responsive (a página
não tem variantes desktop-hidden; o back layer só tem o botão). Todo o texto narrativo anterior
continua presente, byte a byte.

## 4. Fado Card Review

`web-visitecoimbra-cancao-de-coimbra`, secção "Casas para ouvir a Canção de Coimbra" (3 flip-boxes).

| Card/entity | Decision | Reason |
|---|---|---|
| Fado ao Centro | INCLUDE | Espaço de espetáculos de Fado de Coimbra; responde diretamente a "onde ouvir Fado de Coimbra". Descrição factual e estável. |
| À Capella | INCLUDE | Casa de Fados e Centro Cultural numa capela do séc. XIV, na judiaria. Tem valor patrimonial e responde a "que casas de Fado existem". |
| Café Santa Cruz | INCLUDE | Café centenário numa antiga igreja com Fado à noite. É uma entidade turística estável e liga-se ao património de Santa Cruz. |
| Botão "Saber mais" / URLs dos sites | EXCLUDE | CTA / navegação externa, sem valor factual. |
| "Playlist Canção de Coimbra" (embed `html`) | EXCLUDE | Player incorporado, sem texto. |

Nenhum dos três cards é publicidade efémera nem promoção datada. A frase "apresenta
diariamente um espetáculo" é descritiva e não traz horário. Resultado: uma lista de 3 entradas
sob o heading real da fonte (1 chunk, 568 chars).

## 5. Ceramics Card Review

`web-visitecoimbra-ceramica-de-coimbra`, secção "Saber mais sobre a Louça de Coimbra". Aqui não há
flip-boxes: é um `nested-accordion` com três itens, renderizado pelo handler de accordion
existente, sem alterações.

| Card/entity | Decision | Reason |
|---|---|---|
| Refeitro | INCLUDE | Espaço onde se pode "observar a criação artesanal de louça de Coimbra". Responde a "que locais relacionados com cerâmica posso visitar". |
| Carlos Tomás | INCLUDE | Artesão com galeria na Sé Velha. Responde a "onde comprar cerâmica tradicional"; é informação pública do portal oficial, sem contactos. |
| Lojas de artesanato da Baixa | INCLUDE | Indicação genérica e estável de onde comprar louça tradicional e contemporânea. |
| Frase final "Estes locais oferecem excelentes opções..." | INCLUDE | Faz parte do mesmo item da fonte. É uma frase de ligação sem problema. |
| Imagens / link da galeria | EXCLUDE | Media e navegação. |

O heading "Saber mais sobre a Louça de Coimbra" é um heading editorial real da fonte, não o
botão genérico "Saber mais", e por isso foi mantido.

## 6. New Pages Added

| | Coimbra by Night | Restauração | Desporto |
|---|---|---|---|
| URL | https://visitecoimbra.pt/o-que-fazer/coimbra-by-night/ | https://visitecoimbra.pt/gastronomia/restauracao/ | https://visitecoimbra.pt/o-que-fazer/desporto/ |
| document_id | `web-visitecoimbra-coimbra-by-night` | `web-visitecoimbra-restauracao` | `web-visitecoimbra-desporto` |
| Categoria | `visitor_orientation` | `gastronomy` | `visitor_orientation` |
| Grupo de aprovação | `G_leisure_orientation` (wave 2) | `E_gastronomy` (wave 2) | `G_leisure_orientation` (wave 2) |
| Conteúdo principal | intro sobre a noite na Alta/Baixa; "10 locais imperdíveis para sair à noite" (Quebra Costas, Murphy's Irish Pub, Casa das Caldeiras, Galeria Bar Santa Clara, LARGO, Docas do Parque Verde, O Moelas, BIXOS, Bares do Centro Histórico, NB Club); casas de Fado; "6 rooftops a não perder" (Hotel Oslo, Terraço da Alta, Hotel Mondego, LOGGIA/Museu Machado de Castro, Passaporte, Sapientia) | intro à restauração (tascas, pratos típicos, cozinhas internacionais); diretório de **70** estabelecimentos no formato `Nome — tipo de cozinha — descrição` (cervejarias, pastelarias, gelatarias, marisqueiras, Guia Michelin, vegetarianos, ...) | "Cidade do desporto": margens do Mondego, Estádio Cidade de Coimbra, clubes, Regata da Queima das Fitas, São Silvestre; "10 atividades desportivas" (paddle, vela/windsurf, running, caminhadas no Choupal/Vale de Canas, BTT, natação, ténis/padel, Escalódromo, skate, atletismo); AAC fundada em 1887 |
| Motivo | perguntas sobre vida noturna, bares, rooftops e zonas: nenhuma cobertura no corpus | nomes de restaurantes e cervejarias (p. ex. "Cervejaria Praxis"): nenhuma cobertura, completa a página da cerveja | modalidades e espaços para visitantes: nenhuma cobertura |

Categoria: a taxonomia do `KNOWLEDGE_BASE_PLAN.md` tem 9 categorias fixas e nenhuma de
lazer/desporto. Mantivemos a taxonomia e usámos `visitor_orientation` ("orientação turística
estável") para By Night e Desporto. Fica registado como decisão de modelação (secção 16).

Excluído nestas páginas: filtros de tipo de cozinha e preço, o escalão de preço (`€`/`€€`/`€€€`)
de cada restaurante, o formulário e os CTAs para empresas, os botões "Saber mais", os
carrosséis de imagens e o `slides` vazio. Não havia horários, preços em valor, telefones nem
agenda nas descrições (verificado por regex; a regra de horários existente não encontrou
nenhuma frase a remover).

## 7. Raw Acquisition

Pipeline seguido: discovered (`discovered_urls.jsonl`) → review (`candidate_urls.jsonl`, não
editado porque é output gerado) → **approved** (3 linhas acrescentadas a `approved_urls.jsonl`,
com `decision_reason` "wave 2"; as 24 linhas anteriores ficaram inalteradas) →
`acquire_web_corpus.py --documents ...` (robots.txt respeitado, 1 pedido de cada vez, com
rate limit) → raw imutável → manifest → `preprocess_web_documents.py --all --accept`.

| document_id | HTTP | Bytes | SHA-256 |
|---|---|---|---|
| web-visitecoimbra-coimbra-by-night | 200 | 292 155 | `951eed04307293ee02bdd5a7e6fbff41971bf0a10db5f93f12a631d99d843a4a` |
| web-visitecoimbra-restauracao | 200 | 444 617 | `53c46d58d0c1ae3986b097444a91aec49c1a9b7ac3295ea3a2703adfac962bf1` |
| web-visitecoimbra-desporto | 200 | 289 720 | `fc88f1054719333d5887be9c8347ef05ae7a4202e70e728e2a9ba847abb54eb9` |

Validado pelo `check_response` existente: mesmo domínio, canonical = URL aprovado, `text/html`,
`lang=pt-PT` e título igual ao aprovado. O hash no manifest coincide com o ficheiro. A primeira
tentativa de aquisição ficou bloqueada no arranque do crawl4ai (Windows, com a saída ligada a um
pipe) e não escreveu nada: nem raw nem manifest. Foi terminada e repetida sem pipe, com sucesso.

## 8. Processed Web Corpus

| | Before | After |
|---|---:|---:|
| Web docs | 24 | **27** |
| Palavras (corpo) | 10 301 | 14 109 |
| Caracteres (corpo) | 64 682 | 88 607 |

| Documento | Palavras | Caracteres |
|---|---|---|
| cancao-de-coimbra | 511 → 616 | 3 161 → 3 772 |
| ceramica-de-coimbra | 210 → 291 | 1 412 → 1 950 |
| coimbra-uma-cidade-com-tradicao-cervejeira | 212 → 234 | 1 428 → 1 563 |
| coimbra-by-night (novo) | 614 | 3 597 |
| desporto (novo) | 932 | 5 901 |
| restauracao (novo) | 2 054 | 13 143 |

Todos os 27 passam `validate()`, sem avisos novos. Os 27 foram regenerados a partir do raw
(`--all`), não apenas os afetados.

## 9. Existing Corpus Regression

Comparação byte a byte de `data/processed/web/` antes e depois:

| Classe | Documentos |
|---|---|
| Sem alteração (byte-identical) | 21 das 24 páginas antigas |
| EXPECTED CONTENT RECOVERY | `coimbra-uma-cidade-com-tradicao-cervejeira` (+4 cards), `cancao-de-coimbra` (+secção das casas de Fado), `ceramica-de-coimbra` (+secção com 3 locais) |
| EXPECTED NEW DOCUMENT | `coimbra-by-night`, `restauracao`, `desporto` |
| UNEXPECTED CHANGE | **nenhuma** |

Os diffs dos 3 documentos antigos só têm **adições**: nenhuma linha existente foi removida ou
alterada. As novas regras (loop-grid, filtros, accordion vazio, CTA, escalão de preço) não
mudaram nenhuma outra página. No manifest, os 24 registos Web antigos mudaram apenas em
`extraction_notes` (sai a menção às secções já não excluídas) e, nos 3 recuperados, em
`validity_notes`. IDs, URLs, hashes e datas de aquisição ficaram iguais.

## 10. Template Noise Audit

Procura automática nos 27 documentos por: menus (`O que visitar`, `O que fazer`,
`Guia prático`), `Facebook`, `Instagram`, `YouTube`, linhas `EN`/`PT`, `Planeie a`,
`Congressos e Eventos`, `Saber mais`, `Elementor`, `wp-content`, `.jpg/.png/.webp`,
`Agentes e profissionais`, `©`/copyright, `turismo@`, privacidade/cookies, `Pesquisar`,
`Newsletter`, `Preparar visita`, `Ver experiências`, `Clique aqui`, `Faça parte`, `http`.

| Termo | Ocorrências | Contexto / decisão |
|---|---:|---|
| `Saber mais` | 1 | `## Saber mais sobre a Louça de Coimbra`: heading editorial real, não é o botão. Aceite. |
| todos os outros | 0 | — |

Linhas repetidas entre documentos: nenhuma em ≥3 documentos. Em 2 documentos só aparece o bloco
"Casas para ouvir a Canção de Coimbra", que o próprio portal repete em Canção de Coimbra e em
Coimbra by Night (secção 13), e `### Mosteiro de Santa Clara-a-Velha`, que já existia antes.
Nenhum template global domina os documentos.

## 11. Chunking

Mesmo algoritmo e mesma configuração: `chunk_size=1000`, `chunk_overlap=100`,
`length_function=len`, separadores, `heading_context`, parsing estrutural, unit roles,
provenance e tratamento de páginas. `chunk_documents.py` não foi alterado.

| | Before | After |
|---|---:|---:|
| Documentos | 32 (8 PDF + 24 Web) | **35** (8 PDF + 27 Web) |
| Chunks | 330 | **361** |
| — PDF | 206 | 206 |
| — Web | 124 | 155 |
| content | 317 | 348 |
| page_labels | 11 | 11 |
| caption_panel | 2 | 2 |
| body chars min / median / max | 13 / 545.5 / 998 | 13 / 575 / 998 |
| body < 100 chars | 18 | 18 (nenhum novo) |
| body > chunk_size | 0 | 0 |
| URLs Web distintos | 24 | 27 |

Por categoria: `gastronomy` 18 → 33, `visitor_orientation` 15 → 27, `culture_traditions`
68 → 72. As restantes categorias não mudaram.

Chunks antigos: todos os 330 continuam presentes e iguais, exceto
`web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira::c0002`, que ganhou a lista dos 4
cards no fim (564 chars). Os ids dos chunks dos outros documentos antigos não mudaram
(ceramica e cancao ganharam chunks no fim, c0003–c0005 e c0006).

## 12. Content Coverage Verification

Rastreio raw → processed → chunk (texto; sem embeddings nem Chroma):

| Entidade | chunk_id | section | Texto no chunk |
|---|---|---|---|
| BREW! | `...tradicao-cervejeira::c0002` | — (intro) | `- BREW! — Festival de cerveja artesanal` |
| Epicura | idem | — | `- Epicura — Cerveja Artesanal` |
| Portuguese Pedro | idem | — | `- Portuguese Pedro — Cerveja` |
| Praxis | idem | — | `- Praxis — Cervejaria, Restaurante` |
| Cervejaria Praxis | `web-visitecoimbra-restauracao::c0004` | — | `- Cervejaria Praxis — Cervejaria — Descubra a 1ª microcervejeira artesanal portuguesa. Praxis, Topázio, Onyx e muito mais.` |
| Cervejaria Almedina | `web-visitecoimbra-restauracao::c0004` | — | `- Cervejaria Almedina — Cervejaria — Localizada no coração da baixa Coimbrã...` |
| Nicola de Coimbra | `web-visitecoimbra-restauracao::c0008` | — | `- Nicola de Coimbra — Pastelaria — ... doçaria conventual...` |
| Quebra Costas | `web-visitecoimbra-coimbra-by-night::c0002` | 10 locais imperdíveis para sair à noite em Coimbra | `- Quebra Costas — Situado nas famosas escadas...` |
| Docas do Parque Verde | `web-visitecoimbra-coimbra-by-night::c0002` | idem | `- Docas do Parque Verde — Um conjunto de bares junto ao Mondego...` |
| NB Club | `web-visitecoimbra-coimbra-by-night::c0003` | idem | `- NB Club — A discoteca mais famosa da cidade...` |
| LOGGIA | `web-visitecoimbra-coimbra-by-night::c0005` | 6 rooftops a não perder | `- LOGGIA — Situado no Museu Machado de Castro...` |
| Paddle no Rio Mondego | `web-visitecoimbra-desporto::c0005` | Aqui estão 10 atividades desportivas... | `- 1. Paddle no Rio Mondego — Explore o rio...` |
| Mata Nacional do Choupal | `web-visitecoimbra-desporto::c0005` | idem | `- 4. Caminhadas e Trilhos — Descubra percursos pedestres como a Mata Nacional do Choupal...` |
| Escalódromo de Coimbra | `web-visitecoimbra-desporto::c0006` | idem | `- 8. Escalódromo de Coimbra — ...` |
| São Silvestre de Coimbra | `web-visitecoimbra-desporto::c0004` | — | `Prova disso mesmo a São Silvestre de Coimbra é uma das provas mais emblemáticas...` |
| À Capella (Fado) | `web-visitecoimbra-cancao-de-coimbra::c0006` | Casas para ouvir a Canção de Coimbra | `- À Capella — Instalado num espaço emblemático (uma antiga capela do século XIV)...` |
| Refeitro / Carlos Tomás / Lojas da Baixa | `web-visitecoimbra-ceramica-de-coimbra::c0003`/`c0004`/`c0005` | Saber mais sobre a Louça de Coimbra (subsection = entidade) | nome no `heading_context`; descrição no corpo |

Todas as entidades acima estão presentes no raw, aparecem uma vez no processed e aparecem nos
chunks indicados. "Praxis" aparece exatamente em 2 documentos Web: cerveja e restauração.

## 13. Duplication

- Exact duplicates: 4 → 5 grupos. Novo: `cancao-de-coimbra::c0006` = `coimbra-by-night::c0004`
  (a lista das 3 casas de Fado). **Duplicação da fonte**: o portal publica o mesmo bloco nas
  duas páginas. Mantido, e a mesma política já se aplica aos duplicados PDF existentes. Um
  mesmo facto em dois documentos de contexto diferente (Fado vs vida noturna) é aceitável.
- Near duplicates (containment ≥ 0.8): 29 → 30 pares, e o único novo é o par acima
  (`cross_document_web`).
- Dentro dos documentos novos: os 70 restaurantes aparecem uma vez cada ("Restaurante Munich"
  e "Restaurante Marisqueira Munich II" são entradas distintas na fonte, com descrições
  semelhantes mas não idênticas).

## 14. Tests

`uv run python -m unittest discover -s tests`: **118 testes, OK**.

Novos ou atualizados:

| Requisito | Teste |
|---|---|
| A–E beer: presentes, 1×, ordem, sem "Saber mais"/URLs, narrativa mantida | `test_beer_page_recovers_the_four_cards_once_in_order_without_back_layer` |
| F sem duplicação front/back/responsive | o mesmo, mais `test_card_list_document_renders_cards_as_one_list_in_source_order` (back layer "Preparar visita" ausente) e o `test_desktop_hidden_duplicate_is_skipped` existente |
| G Fado/Cerâmica INCLUDE | `test_cancao_keeps_culture_and_fado_houses_and_drops_player`, `test_ceramica_keeps_reviewed_places_to_see_and_buy_pottery` |
| H EXCLUDE continuam ausentes | `test_still_excluded_cards_and_sections_stay_absent` (navegação "Ver também", app "Judeus em Coimbra", evento Mostra de Doçaria), mais a player playlist |
| I páginas novas não vazias e úteis | `test_new_pages_keep_their_entities_and_drop_directory_ui` (19 entradas By Night, 70 restaurantes, 10 atividades, >600 palavras, sem UI/€) |
| J determinismo | `test_rendering_is_deterministic`, `test_processed_files_equal_a_fresh_offline_render` (27 docs) e `test_persisted_chunks_are_valid_and_reproducible` |
| Regras de template novas (sintéticas) | `test_directory_loop_grid_filters_form_and_price_tier`, `test_empty_accordion_item_does_not_adopt_following_content` |
| Chunks | `test_recovered_and_new_web_entities_reach_a_chunk` |
| Provenance | `test_establishment_pages_record_their_validity_limit` |

Contagens atualizadas nos testes existentes: manifest 32 → 35 docs e 24 → 27 Web; chunks
330 → 361 e 317 → 348 content (`test_rag_baseline.py` lê o `chunks.jsonl` real; o teste com
fake embeddings escreve só num `TemporaryDirectory`).

Correção de teste: `test_no_words_are_introduced` passou a normalizar o raw para NFC. O raw da
Restauração é o primeiro com acentos decompostos (11 caracteres NFD, p. ex. "mão",
"únicas" no card da Gelataria Così). O `clean_text` sempre normalizou para NFC, portanto a
falha era do teste e não uma palavra introduzida.

Compile/import: `compileall` OK em `scripts/` e `tests/`, e os 9 módulos importam. Exceção
pré-existente e ignorada pelo git: `scripts/tempCodeRunnerFile.py`, um fragmento do VS Code Code
Runner que não compila e não é usado.

## 15. Integrity

SHA-256 guardados **antes** de qualquer alteração e reverificados no fim (`sha256sum -c`):
**65/65 byte-identical**.

| Artefacto | Estado |
|---|---|
| 8 raw PDF | inalterados |
| 8 processed PDF | inalterados |
| 24 raw Web anteriores | inalterados (a aquisição salta raws existentes) |
| `data/chroma_smoke/` | inalterado (não aberto) |
| `data/chroma_baseline/` (V0) | inalterado |
| `data/chroma_baseline_v1/` | inalterado |
| `data/chroma_baseline_v2/` | inalterado |
| RAG_BASELINE_SMOKE_TEST.md, RAG_BASELINE_V1_SMOKE_TEST.md, RAG_BASELINE_V2_QWEN_SMOKE_TEST.md, CHUNKING_REPORT.md, WEB_CONTENT_GAP_AUDIT.md | inalterados |
| Manifest | 8 linhas PDF byte-identical e nas mesmas posições; IDs únicos (35); canonical URLs Web únicos (27); todas `source_type=web_page`, `language=pt`, `source_organization=Câmara Municipal de Coimbra`, `status=accepted`, hash = ficheiro; IDs dos 24 Web anteriores inalterados |
| Outputs reproduzíveis | nova execução de `--all --accept` → `processed/web` idêntico; `chunk_corpus()` fresco = `chunks.jsonl` persistido |

**VECTOR STORES ARE STALE RELATIVE TO THE NEW CORPUS.**
**VECTOR STORES REQUIRE REBUILD BEFORE THE NEXT RAG TEST.**

As quatro stores foram construídas a partir das 317 content chunks anteriores. O corpus tem
agora 348, e nenhuma store contém os cards recuperados nem as três páginas novas.

## 16. Known Limitations

- **Estabelecimentos comerciais podem tornar-se obsoletos**: bares, restaurantes, cervejarias,
  casas de Fado e marcas podem fechar, mudar de nome ou de conceito. Fica registado em
  `validity_notes` nos 5 documentos afetados.
- **Horários e preços não são preservados**: o escalão `€`–`€€€` foi removido, e o corpus não
  responde a "quanto custa" nem a "a que horas abre".
- **O corpus representa um snapshot das fontes** (aquisição de 2026-09-27/28). A lista de 70
  restaurantes é a do portal nessa data, que é uma seleção do portal e não um diretório
  exaustivo.
- As descrições dos restaurantes são texto do portal, muitas vezes escrito pelo próprio
  estabelecimento ("O nosso restaurante..."). São mantidas sem paráfrase, como tom promocional
  da fonte.
- Categorias: nightlife e desporto ficaram em `visitor_orientation` porque a taxonomia fixa
  não tem categoria de lazer. Se a avaliação por categoria o exigir, é preciso decidir sobre uma
  10.ª categoria.
- Os 3 itens de Cerâmica são secções curtas de accordion da fonte (chunks de 100/100/226 chars,
  com o nome da entidade no `heading_context`). Estão no limite mínimo, mas não abaixo.
- A Restauração não tem headings internos: os seus 15 chunks têm `section = None`, e o contexto
  é o título "Restauração" e o formato `Nome — tipo — descrição`.

## 17. Decision

IS THE WEB CORPUS READY TO BE FROZEN FOR FORMAL EVALUATION? **YES**

Os dois problemas confirmados estão corrigidos, as revisões de Fado e Cerâmica estão decididas
e documentadas, não há regressões inesperadas nem template noise, e os outputs são
determinísticos.

VECTOR STORES REQUIRE REBUILD? **YES**
