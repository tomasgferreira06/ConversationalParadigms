# Web Corpus Discovery — visitecoimbra.pt

## 1. Objective

Mapear `https://visitecoimbra.pt/` como **nova fonte candidata** para a knowledge
base do D2 e responder a uma pergunta: *que conteúdo deste site deve entrar na
knowledge base?*

Isto é **discovery**, não ingestão:
- o texto das páginas foi analisado só em memória;
- não foi criado nenhum corpus web, chunk, embedding ou Vector DB, e não foi usado
  nenhum LLM;
- nenhuma página foi aprovada para o corpus final.

Artefactos, todos em `d2_rag/web_discovery/` (fora de `data/raw/`):

| Ficheiro | Conteúdo |
|---|---|
| `discovered_urls.jsonl` | 457 URLs, com metadata, classificação e razão |
| `candidate_urls.jsonl` | 97 páginas HTML em `candidate`, `review` ou `already_in_corpus` |
| `crawl_summary.json` | configuração, robots/sitemap, contagens e PDFs |
| `sample_extractions/` | 8 extrações Markdown só para avaliar a qualidade; não são corpus |

Script: `d2_rag/scripts/discover_web_corpus.py` (`--discover`, `--extract-samples`,
`--reclassify-pdfs`).

## 2. Crawl Configuration

| Item | Valor |
|---|---|
| Crawl4AI | **0.9.4** (pacote base, sem extras `[torch]`/`[transformer]`/`[all]`) |
| Fetcher | `AsyncHTTPCrawlerStrategy`, HTTP simples, sem browser. O site é server-rendered, o que foi verificado. |
| Root URL | `https://visitecoimbra.pt/` |
| robots | `check_robots_txt=True` no `CrawlerRunConfig`, mais verificação prévia com `urllib.robotparser` |
| Deep crawl | `BFSDeepCrawlStrategy`, `max_depth=3`, `max_pages=300` (limites de segurança), `include_external=False` |
| Fontes de descoberta | BFS a partir da raiz, mais o sitemap declarado no robots.txt (páginas do sitemap que o BFS não alcançou) |
| Concorrência / ritmo | `semaphore_count=2`; atraso por domínio de 1.5–2.5 s (`mean_delay=1.5`, `max_range=1.0`); `RateLimiter` com backoff em 429/503 |
| User-Agent | `D2-RAG-discovery/0.1 (academic project; conservative crawl)` |
| Domínio | só `visitecoimbra.pt` (`www.` canonicalizado para a mesma origem); `DomainFilter` mais `include_external=False` |
| Nunca descarregado | `wp-admin`/`wp-json`/`wp-content` (imagens e **PDFs**), feeds, pesquisa, login/conta/registo, taxonomias, templates do tema e fichas de restaurantes/alojamentos (exceto uma amostra de 2 + 2 para as caracterizar) |
| Canonicalização | https; sem `www.`; sem fragmento; remoção de `utm_*`, `fbclid`, `gclid`…; trailing slash; `redirected_url`; `<link rel=canonical>` |
| Execuções | 2 execuções de discovery (a segunda depois de corrigir regras de classificação) e 1 reclassificação offline dos PDFs. Cerca de 270 pedidos no total, mais 8 da amostra e ~20 verificações manuais pontuais. |

A API foi confirmada na versão instalada (assinaturas, semântica de
`URLPatternFilter(reverse=True)` e do `DomainFilter`, e dispatcher do deep crawl),
em vez de assumida.

**Incidente técnico da biblioteca:** passar `user_agent` ao `CrawlerRunConfig`
falha com a estratégia HTTP. O UA foi então definido nos headers da estratégia.

## 3. Discovery Results

| Métrica | N.º |
|---|---:|
| URLs descobertas (canonicalizadas) | **457** |
| … páginas/URLs HTML | 288 |
| … assets (imagens em `/wp-content/uploads/`) | 132 |
| … PDFs | 37 |
| Páginas descarregadas | 132 (131 HTML + 1 falha de tipo `text/xml`) |
| HTML válido (200) | 123 |
| Redirects | 0 |
| Erros | 9 (ver abaixo) |
| Línguas (`<html lang>`) | 122 `pt-PT`; 0 outras (as 9 falhas não têm lang) |
| Excluídas (HTML) | 182 |
| **Candidatas** | **29** |
| **Review** | 61 |
| `already_in_corpus` (HTML) | 7 |
| `unavailable` | 9 |
| PDFs: `already_in_corpus` / `new_candidate` / `irrelevant` / `unknown` | 7 / 2 / 27 / 1 |

**robots.txt** (HTTP 200):

```text
User-agent: *
Disallow: /wp-admin/
Allow: /wp-admin/admin-ajax.php
Sitemap: https://visitecoimbra.pt/wp-sitemap.xml
```

Crawling permitido para todo o conteúdo público. **Sitemap** (índice nativo do
WordPress, 9 sub-sitemaps):

| Sub-sitemap | URLs |
|---|---:|
| `page` | 106 |
| `restaurantes` | 70 |
| `alojamentos` | 48 |
| `experiencias` | 30 |
| taxonomias (estrela, preço, tipos de alojamento, tipos de restaurante) | 29 |
| `ova_framework_hf_el` (templates do tema) | 3 |

**Não houve bloqueio:** nenhum 403, 429 nem CAPTCHA, e os headers mostram
`X-WAF-Action: allow`.

**9 páginas indisponíveis no momento do crawl.** São erros do site, não bloqueios,
e foram verificadas manualmente com um pedido cada:
- **8 páginas com `HTTP 500` persistente**:
  - `/gastronomia/coimbra-vinhos-licores-gin-e-espumantes/`
  - `/gastronomia/cozinha-coimbra/`
  - `/gastronomia/experiencias-gastronomicas-em-coimbra/`
  - `/o-que-visitar/rotas-e-percursos/`
  - `/o-que-visitar/visitas-guiadas/`
  - `/viver-coimbra/`
  - `/viver-coimbra/tradicoes/`
  - `/viver-coimbra/vida-de-bairro/`
- **`/gastronomia/`** devolve `HTTP 200` com `Content-Type: text/xml`. O conteúdo é
  a mesma página "Ocorreu um erro crítico neste site" do WordPress. O fetcher HTTP
  tentou gravá-la como ficheiro e falhou no Windows (`os.O_NOFOLLOW`).

**Língua:** o site não tem versões separadas por URL (sem hreflang e sem prefixos
`/en/`). As traduções são feitas no browser pelo widget **GTranslate**, por isso
**não existe duplicação multilingue de páginas HTML**. As outras línguas existem
apenas como **PDFs** (ES/FR/UK).

## 4. Site Structure

Estrutura real, a partir do sitemap e do menu:

| Secção | Páginas | Natureza |
|---|---:|---|
| **O que visitar** | 9 | Cidade Património, Universidade, Museus, Herança cultural e religiosa, Herança judaica/moçárabe, À volta de Coimbra (2 em HTTP 500) |
| **Viver Coimbra** | 29 | Canção de Coimbra, Repúblicas, Coimbra dos estudantes, **8 lendas e figuras históricas**, 4 tradições/artesanato, 4 bairros, Erasmus, nómadas digitais, blog |
| **Gastronomia** | 9 | Gastronomia em Coimbra, doçaria conventual, mercados, cerveja, restauração (4 em erro) |
| **Roteiros temáticos** | 10 | Índice mais 9 roteiros; **7 correspondem aos nossos PDFs** |
| **O que fazer** | 11 | Cultura, ciência, arte contemporânea, família, desporto, natureza e rio, noite, agenda, Natal, Bienal |
| **Guia prático** | 6 | Altura do ano, como chegar, mover-se, onde ficar, postos de turismo |
| **Compras** | 10 | Lojas históricas, Kasbah, renovação da Baixa, feiras, galerias, mais 3 páginas de eventos |
| Fichas (custom post types) | 148 | 70 restaurantes, 48 alojamentos, 30 experiências |
| Institucional/conta | ~20 | Agentes e profissionais, login, registo, erro, coming soon |

## 5. Candidate Corpus

As 29 candidatas totalizam cerca de **14 700 palavras de conteúdo principal**,
depois de removido o boilerplate. As mais relevantes:

| Title | URL (path) | Category | Motivo | Contributo esperado |
|---|---|---|---|---|
| Herança Cultural e Religiosa | `/o-que-visitar/heranca-cultural-e-religiosa/` | built_heritage | 2155 palavras, 9% de sobreposição com PDFs | Fichas por monumento (Sé Velha, Santa Clara-a-Velha/Nova, Sé Nova, Celas, Santiago, Santa Cruz, Santo António dos Olivais…), cada uma **com o nome do monumento no mesmo bloco** |
| Museus | `/o-que-visitar/museus/` | museums_collections | 1468 palavras, 2% | Inventário descritivo de ~20 museus; **não coberto** pelos PDFs |
| A Universidade de Coimbra | `/o-que-visitar/a-universidade-de-coimbra/` | university_heritage | 933 palavras, **52%** (fado/UC) | Parcialmente redundante (Paço das Escolas); acrescenta enquadramento |
| Cidade Património da Humanidade | `/o-que-visitar/cidade-patrimonio-da-humanidade/` | university_heritage | 363 palavras, 43% | Parcialmente redundante com a brochura UC |
| Herança Judaica / Moçárabe | `/o-que-visitar/heranca-judaica/`, `/heranca-mocarabe/` | city_history | 312 e 118 palavras, ~0% | Tema novo |
| Lendas e figuras históricas (8) | `/viver-coimbra/lendas-e-figuras-historicas/*` | city_history | 321–519 palavras cada, ~0% | D. Afonso Henriques, Camões, Santo António, Pedro e Inês, Rainha Santa Isabel, Sesnando, Cindazunda, brasão: **conteúdo novo e estável** |
| Canção de Coimbra | `/viver-coimbra/cancao-de-coimbra/` | culture_traditions | 639 palavras, 2% | Origem, guitarra de Coimbra, intérpretes; complementa o roteiro do fado |
| Repúblicas; Coimbra dos Estudantes | `/viver-coimbra/republicas/`, `…/coimbra-dos-estudantes/` | culture_traditions | 339 e 347 palavras | Tradições académicas |
| Tradições (4) | `/viver-coimbra/tradicoes/*` | culture_traditions | 110–350 palavras | Cerâmica, tecelagem de Almalaguês, cestaria de bunho, Ceira: **novo** |
| Gastronomia (4) | `/gastronomia/{gastronomia-em-coimbra, docaria-conventual-de-coimbra, mercados, …cervejeira}/` | gastronomy | 245–746 palavras, 0% | **Categoria sem nenhuma cobertura** no corpus PDF |
| Natureza e Rio | `/o-que-fazer/natureza-e-rio/` | landscape_gardens | 727 palavras | Mondego, percursos; tem alguns termos operacionais |
| Coimbra em qualquer altura do ano | `/guia-pratico/coimbra-em-qualquer-altura-do-ano/` | visitor_orientation | 862 palavras | Página transversal; mistura estações com programação |
| Roteiro Coimbra Muralhada | `/roteiros-tematicos/coimbra-muralhada/` | visitor_orientation | 297 palavras, 0% | **Roteiro que não temos em PDF** |

**Review (61):**
- 30 **experiências**, cuja descrição não está no HTML (ver §9);
- 25 páginas temáticas mistas: compras (lojas históricas, Kasbah, feiras, galerias), o que fazer (cultura, ciência, arte contemporânea, família, desporto, noite), bairros, transportes, onde ficar, Erasmus, nómadas digitais, À volta de Coimbra;
- homepage, índices de secção e diretório de restauração.

## 6. Exclusions

| Grupo | N.º | Razão |
|---|---:|---|
| Fichas de restaurantes | 70 | Listagens comerciais e operacionais. A amostra (2) tem só ~37 palavras fora do template. |
| Fichas de alojamento | 48 | Idem (amostra de 2 com ~40 palavras) |
| Taxonomias | 29 | Listagens por estrela, preço e tipo |
| Assets `/wp-content/uploads/` | 132 | Imagens |
| Eventos, agenda e promoções | 8 | Agenda, Praxis Beer Fest, Strauss, Natal, Bienal Anozero, Magic Land, fim de ano, Guns N' Roses |
| Área profissional / institucional | 8 + 1 | Agentes e profissionais (fotogaleria, filme, identidade gráfica, toolkit), submissão de alojamentos |
| Conta / sistema / templates | 12 | Login, registo, password, perfil, página de erro, coming soon, templates do tema |
| Índices quase vazios | 6 | Menos de 80 palavras depois de remover o boilerplate (por exemplo `/planeie-a-sua-visita/`, `/roteiros-tematicos/`) |
| PDFs noutras línguas | 27 | Edições ES/FR/UK dos roteiros e da brochura |

## 7. Existing-PDF Overlap

**PDFs:** o site aloja **7 dos nossos 8 PDFs** com o mesmo filename.
- A exceção é o `UnivCoimbra - UCTour.pdf`, que vem do site da UC.
- Nenhum foi descarregado de novo.
- **2 PDFs portugueses novos:**
  - `CoimbraMuralhada_final.PT_.pdf` (roteiro Coimbra Muralhada);
  - `PATRIMONIO-MUNDIAL_PT_V2_1.pdf` (provavelmente o roteiro "Património Mundial do Centro" ou uma versão 2 da brochura; a confirmar).
- **1 PDF por esclarecer:** `mapa_turistico_2023.pdf`.

**Páginas HTML** (contenção de 5-gramas do conteúdo principal nos 8 Markdown):

| Tipo | Páginas | Evidência |
|---|---|---|
| **B) Redundante** (`already_in_corpus`) | 7 roteiros: fundação (0.84), fado (0.84), jardins (0.83), escritores (0.79), Coimbra Património Mundial (0.72), viver o património (0.71), Património Mundial do Centro (0.91, igual ao texto UNESCO da p40 da brochura UC) | O texto web é a introdução do próprio PDF |
| B/A) Parcialmente redundante | Universidade de Coimbra (0.52), Cidade Património da Humanidade (0.43), roteiro Pequenitos (0.37) | Blocos copiados (Paço das Escolas) mais enquadramento novo |
| **A) Complementar** | Herança cultural e religiosa (0.09), Museus, Lendas, Tradições, Canção de Coimbra, Gastronomia, Herança judaica/moçárabe, Muralhada (≈0) | Os mesmos locais tratados com texto diferente, ou temas ausentes dos PDFs |
| **C) Mais atual** | Páginas de 2024–2025 (o próprio site é de 2024+). A Canção de Coimbra menciona os concertos Coldplay em Coimbra. | Conteúdo mais recente, mas sem datas de revisão por página |
| **D) Mais volátil** | Museus, Natureza e Rio, altura do ano, galerias (horários), transportes, onde ficar | Termos operacionais, links de reserva e cartões de operadores |

**Conflito factual a registar.**
- A web diz, sobre Santa Clara-a-Velha: "Fundado pela Rainha Santa Isabel, o edifício sofreu inundações recorrentes…".
- O PDF municipal diz: "Fundado em 1283, por D. Mor Dias… a Rainha Santa Isabel interessou-se pela refundação".

Juntar as duas fontes pode introduzir contradições no contexto do LLM.

## 8. Sample Extraction Quality

Foram extraídas 8 páginas com Crawl4AI (Markdown bruto). Estão em
`sample_extractions/` e não foram indexadas.

| Página | Tipo | Total → conteúdo principal | Avaliação |
|---|---|---|---|
| Herança Cultural e Religiosa | património | 2779 → ~2170 (78%) | **Boa.** Um card por monumento, com heading. Tem links "Preparar visita" para sites externos. |
| Museus | museu | 2159 → ~1510 (70%) | **Boa**, com muitos links externos (57) e referências operacionais |
| A Universidade de Coimbra | universidade | 1487 → ~920 (62%) | Boa. **A pull quote aparece duplicada** como H1. As subsecções (Porta Férrea…) estão todas em `#`. |
| Canção de Coimbra | cultura | 1184 → ~630 (53%) | Boa. Tem um heading vazio ("Playlist…", player embebido) e cartões promocionais de casas de fado no fim. |
| Doçaria Conventual | gastronomia | 1323 → ~750 (57%) | Boa. A secção "Mostra de Doçaria…" é um evento. |
| Coimbra em qualquer altura do ano | transversal | 1551 → ~910 (59%) | Mista. Tem muitas imagens e links (51), programação sazonal e uma lista "Planeie a sua visita". |
| Roteiro Fundação da Nacionalidade | já no corpus | 810 → ~250 (31%) | Redundante: repete a introdução do PDF e aponta para os PDFs PT/ES/FR/UK. |
| Experiência "Ouvir fado" | problemática | 586 → ~31 (5%) | **Sem conteúdo.** Só tem data, autor, botões de partilha e navegação. A descrição não está no HTML. |

**Boilerplate:**
- Estrutura fixa: header com o **menu completo duplicado** (desktop e mobile), cerca
  de 150 linhas antes do conteúdo; depois o conteúdo; depois o footer (logótipos,
  telefone, email, redes sociais).
- Pode ser removido de forma determinística pelas fronteiras do template.
- Em alternativa, pode usar-se remoção por frequência de linhas, que é a que foi
  usada nas métricas.

**Headings:** o Elementor marca pull quotes e títulos de cards como `#` (H1). É
preciso normalizar antes de fazer chunking por headings.

## 9. Risks

- **Duplicação com os PDFs:** 7 roteiros quase iguais e 2–3 páginas parcialmente
  copiadas. Por outro lado, o próprio corpus PDF já tem duplicação (M5 do audit).
- **Conflitos factuais entre fontes** (exemplo de Santa Clara-a-Velha). É preciso
  uma política de prioridade entre fontes.
- **Informação temporal:** horários, links de reserva, eventos (Mostra de doçaria,
  concertos) e programação sazonal. As páginas não têm data de revisão explícita.
- **Páginas dinâmicas:** as 30 experiências (e as fichas comerciais) não têm
  descrição no HTML servido. Avaliá-las exigiria um fetch com browser (Playwright),
  que não foi feito.
- **Instabilidade do site:** 9 páginas estavam com erro crítico do WordPress no
  momento do crawl. Uma aquisição futura deve repetir o pedido e registar a data.
- **Conteúdo promocional:** cartões de operadores privados (casas de fado,
  galerias, tours) e links "Saber mais" externos.
- **Multilinguismo:** risco baixo em HTML (GTranslate é client-side). Nos PDFs há 27
  traduções, que ficam excluídas.
- **Restrições de crawl:** nenhuma encontrada além de `/wp-admin/`. Manter o ritmo
  conservador.
- **Taxonomia:** as categorias existentes chegam para os candidatos. As lacunas
  observadas (compras/artesanato, eventos, bairros) ou estão em `review` ou são
  voláteis. **Não se recomenda criar uma categoria nova agora**: as tradições e o
  artesanato cabem em `culture_traditions`. Uma futura `shopping_crafts` só se
  justificaria se as páginas de compras fossem aprovadas.

## 10. Proposed Web Corpus

A quantidade proposta não vem do número de URLs descobertas. Proposta para uma
próxima fase, a aprovar:

| Bloco | Páginas | Nota |
|---|---:|---|
| Núcleo complementar | **~20** | Herança cultural e religiosa, Museus, Herança judaica, Herança moçárabe, 8 lendas e figuras, Canção de Coimbra, Repúblicas, Coimbra dos Estudantes, 4 tradições, Muralhada (HTML) |
| Gastronomia | **3–4** | Gastronomia em Coimbra, Doçaria conventual, Mercados, Tradição cervejeira; remover o evento da doçaria |
| Parcialmente redundantes | **2** | Universidade de Coimbra e Cidade Património: incluir só se a deduplicação por parágrafo for aplicada |
| Condicionais | 0–4 | Natureza e Rio e altura do ano (com limpeza de conteúdo operacional); Lojas históricas e Kasbah (histórico, depois de review) |
| Páginas em HTTP 500 | 0–3 | Repetir o fetch mais tarde (Cozinha de Coimbra, Vinhos/licores, Rotas e percursos podem ser úteis) |
| PDFs novos | **1–2** | `CoimbraMuralhada_final.PT_.pdf` (e `PATRIMONIO-MUNDIAL_PT_V2_1.pdf` depois de verificação), pela pipeline PDF existente |
| **Excluir** | — | 7 roteiros HTML redundantes, 118 fichas comerciais, 30 experiências (até haver fetch com browser), eventos e agenda, institucional |

**Total recomendado: ~25–30 páginas HTML, com cerca de 12–15 mil palavras de
conteúdo principal, mais 1–2 PDFs.**

## 11. Decision

**Does visitecoimbra.pt provide enough complementary, stable and useful content to justify adding a curated web corpus to the RAG?**

# PARTIALLY

**Justificação:**

- **Sim para um subconjunto curado de ~25–30 páginas.**
  - Cobrem lacunas reais do corpus PDF: museus, lendas e figuras históricas,
    gastronomia (categoria hoje vazia), artesanato, Canção de Coimbra, heranças
    judaica e moçárabe.
  - Oferecem descrições de monumentos em blocos autocontidos, com o nome da
    entidade junto ao facto, o que ajudaria nas falhas de retrieval vistas no smoke
    test.
  - A fonte é oficial (Câmara Municipal), em português, e a extração é limpa
    depois de remover o template.
- **Não para o site em bloco.**
  - ~60% das URLs são comerciais, taxonómicas, institucionais ou assets.
  - Os 7 roteiros repetem os nossos PDFs.
  - As experiências não têm conteúdo no HTML.
  - Várias páginas misturam informação operacional ou promocional.
  - 9 páginas estavam em erro no momento do crawl.
  - Existe pelo menos um conflito factual com os PDFs, o que exige uma política de
    prioridade entre fontes antes de qualquer merge.

A aquisição definitiva, a limpeza do template e a normalização dos headings
**ficam à espera de autorização**. Nenhuma página foi aprovada automaticamente
para o corpus final.
