# Web Corpus Acquisition & Preprocessing

## 1. Objective

Adquirir e preprocessar a **primeira vaga** do corpus web aprovado a partir do
discovery de `visitecoimbra.pt` (decisão **PARTIALLY** em
`WEB_CORPUS_DISCOVERY.md`). O objetivo é ter um corpus reproduzível com a mesma
disciplina do corpus PDF:

```text
Web page → Raw HTML (imutável, SHA-256) → preprocessing determinístico e offline → Markdown
```

Não foram criados chunks, embeddings nem Vector DB, não foi usado nenhum LLM, e
não houve merge PDF + Web. Os PDFs e os seus Markdown não foram alterados.

## 2. Approved Corpus

A seleção humana está registada em `d2_rag/web_discovery/approved_urls.jsonl`
(24 entradas, com `document_id`, `canonical_url`, `title`, `proposed_category`,
`approval_group`, `decision_reason` e métricas do discovery). Os URLs são os
**exatos** do `candidate_urls.jsonl`, todos com `status: candidate` no discovery.
Não foi adicionada nenhuma página fora da lista.

| Grupo | Páginas |
|---|---|
| A) Património / História (3) | Herança Cultural e Religiosa, Herança Judaica, Herança Moçárabe |
| B) Museus (1) | Museus |
| C) Lendas e figuras (8) | D. Afonso Henriques, Luís Vaz de Camões, Santo António, Pedro e Inês, Rainha Santa Isabel, Sesnando David, Princesa Cindazunda, O Brasão da Cidade de Coimbra |
| D) Cultura e tradições (7) | Canção de Coimbra, Repúblicas, Coimbra dos Estudantes, Cerâmica de Coimbra, Tecelagem de Almalaguês, Cestaria de Bunho, Ceira |
| E) Gastronomia (4) | Gastronomia em Coimbra, Doçaria Conventual de Coimbra, Mercados, Coimbra: Uma Cidade com Tradição Cervejeira |
| F) Roteiro complementar (1) | Coimbra Muralhada (HTML) |

**Resultado: 24 aprovados, 24 adquiridos e 24 `accepted`; 0 `unavailable`.**

## 3. Acquisition

Script: `d2_rag/scripts/acquire_web_corpus.py` (só aquisição).

| Item | Valor |
|---|---|
| Crawl4AI | 0.9.4, `AsyncHTTPCrawlerStrategy` (sem browser) |
| robots | verificação prévia com `urllib.robotparser` (paragem se algum URL estiver proibido) mais `check_robots_txt=True` |
| Ritmo | 1 pedido de cada vez (`semaphore_count=1`), 1.5–2.5 s entre pedidos; um pedido por página |
| Domínio | a resposta tem de continuar em `visitecoimbra.pt` |
| Validação da resposta | HTTP 200, `text/html`, `<html lang>` pt, `<link rel=canonical>` igual ao aprovado, título igual ao do discovery, não é página de erro crítico do WordPress |
| Raw | `data/raw/web/<document_id>.html`: corpo HTML devolvido pelo servidor, descodificado pelo fetcher e gravado em UTF-8 **sem nenhuma transformação** |
| Hash | `content_hash = sha256` do ficheiro raw |
| Imutabilidade | um raw existente nunca é reescrito (o script salta-o) |
| Falhas | registadas como `unavailable` no manifest, sem substituição |
| Execução | piloto de 5 páginas (27-09-2026 22:59 UTC) e restantes 19 (23:06 UTC). Total: 24 pedidos, mais 1 ao robots.txt por execução |

**Manifest.** Os 24 registos foram acrescentados ao **mesmo** `data/manifest.jsonl`,
ordenados por `document_id` e com `source_type: "web_page"`. As 8 linhas PDF
ficaram **byte a byte iguais**, o que foi verificado contra o HEAD. Os campos
seguem o schema do `KNOWLEDGE_BASE_PLAN.md`:

- **obrigatórios:**
  - `document_id`, `title`, `source_organization`, `url`, `language`
  - `primary_category`, `source_type`, `status`
  - `acquired_at`, `access_checked_at`
- **opcionais do plano:**
  - `content_hash`, `decision_reason`
  - `validity_notes`, `source_last_modified_at`
- **nomes existentes no manifest PDF:** `local_raw_path` e `processed_path`, reutilizados por compatibilidade.
- **campos novos (documentados):**
  - `canonical_url`, `http_status`, `raw_representation`
  - `http_last_modified`: o header HTTP. É a hora da cache do servidor, **não** uma data de revisão; por isso não foi usado como `source_last_modified_at`.
  - `conflict_notes`, `extraction_notes`

`source_last_modified_at` fica `null`: as páginas não publicam
`article:modified_time`, e a data não foi inventada.

**Organização.** `source_organization = "Câmara Municipal de Coimbra"` em todas as
páginas, o mesmo nome dos 7 PDFs municipais. O portal visitecoimbra.pt ("Turismo
de Coimbra") é o site de turismo oficial do município: tem o logótipo CMC e
contactos `@cm-coimbra.pt`, e aloja os PDFs da CMC.

**Convenção de `document_id`.** `web-visitecoimbra-<último segmento do path canónico>`, por exemplo `web-visitecoimbra-heranca-cultural-e-religiosa`.
- O prefixo `web-` distingue estes documentos dos PDF.
- Não depende do título, da categoria nem de parâmetros da URL.
- É legível.
- É fixado em `approved_urls.jsonl` no momento da aprovação, por isso fica estável mesmo que o título ou o path mudem.
- Em caso de colisão futura, junta-se o segmento pai.

**Compatibilidade com as ferramentas PDF.** O `preprocess_documents.py`, o
`rag_smoke_test.py` e o `ConsistencyTests` selecionavam todos os registos
`accepted` do manifest. Passaram a selecionar também `source_type == "pdf"`.
- A alteração é só de seleção: nenhuma regra PDF mudou.
- Os outputs PDF continuam byte a byte iguais.

## 4. Preprocessing Pipeline

Script: `d2_rag/scripts/preprocess_web_documents.py`. É **offline**: lê o raw e
verifica o hash antes de processar.

```text
Raw HTML (hash verificado)
  → template removal       : só o container Elementor data-elementor-type="wp-page"
  → structural walk        : widgets Elementor em ordem de documento; vista desktop canónica
  → heading normalization  : # título → ## secção/entidade → ### sub-entidade
  → commercial/temporal    : CTAs, cards comerciais, eventos, frases com horário
  → cleanup                : secções vazias (até ponto fixo), níveis sem saltos
  → Markdown + front matter mínimo
```

`--accept` marca como `accepted` os documentos que passam a validação e escreve
`extraction_notes`, `conflict_notes` e `validity_notes` no manifest.

## 5. Cleaning Rules

Toda a configuração está centralizada no topo do script.

| Regra | Implementação | Base |
|---|---|---|
| **Template** (menu desktop, menu mobile duplicado, header, footer, contactos, redes sociais) | Só se processa o único `[data-elementor-type="wp-page"]`. O header (`wp-post` 2986), o footer (`wp-post` 2995) e a `section` 6207 ficam de fora por estrutura. | Os 24 raws têm exatamente 1 container |
| **Duplicados responsive** | Os elementos `elementor-hidden-desktop` são ignorados; é verificado que o seu texto aparece no output (warning se não aparecer) | Pull quote duplicada na Herança |
| **Media** | `image`, `image-carousel`, `gallery`, `video`, `html` (embeds/player vazio) são descartados, e as imagens não são descarregadas | RAG textual |
| **CTAs** | `button` ("Saber mais", "Ler mais", lojas de apps), `nested-carousel` (carrossel de experiências), `ova_heading` (banner "Planeie a sua visita…"; única ocorrência no corpus), verso dos `flip-box` ("Preparar visita") | Inspeção dos 24 raws |
| **Secções CTA do site** | `SITE_CTA_SECTIONS`: "Não sabe por onde começar?" (webapp), "Experiências" (teaser) | Template partilhado |
| **Secções comerciais/evento** | `DROP_SECTIONS` por documento, revistas manualmente (§7): o heading e tudo abaixo até ao próximo heading do mesmo nível | Não distinguíveis estruturalmente |
| **Operacional** | Remove-se só a **frase** que contém um intervalo horário explícito (`\d{1,2}h… às \d{1,2}h`) | A regex de termos foi rejeitada: apanhava "segunda metade do século", "preserva", "Domingos" |
| **Links** | Mantém-se o texto âncora e remove-se o URL; o URL da página está no manifest | |
| **Parágrafos com `<br>`** | Com 3 ou mais `<br>` (listas, versos) mantêm uma linha por quebra; com menos, `<br>` é espaço | Repúblicas (23), Camões (4) vs. quebras visuais a meio de frase (1–2) |
| **Whitespace** | NFC, remoção de NBSP e de soft hyphen, colapso de espaços | |
| **Secções vazias** | Um heading sem conteúdo até ao próximo heading do mesmo nível ou superior é removido, **repetindo até estabilizar** | Bug da primeira versão: "Ver também" ficava órfão |
| **Widgets desconhecidos** | O texto é mantido, com warning (não aconteceu no corpus) | Não perder conteúdo |

## 6. Heading Normalization

O Elementor usa `<h1>` para tudo (pull quotes, títulos de cards, destaques), por
isso os níveis HTML foram **ignorados**. A hierarquia vem da **estrutura dos
widgets**:

| Origem | Resultado |
|---|---|
| Título da página (manifest ← `<title>` da fonte) | `# Título` |
| Widget `heading` com texto de secção | `##` (ou um nível abaixo do item de acordeão onde está) |
| Widget `heading` que começa por aspas (`"`, `“`, `«`) | citação `>`, e **não** heading |
| Widget `heading` com **mais de 12 palavras** | citação `>`. Os headings reais do corpus têm 1–8 palavras e as frases de destaque 17–29; não há casos entre 9 e 16. |
| Item de `nested-accordion` com título | heading um nível abaixo do último heading (por exemplo `## Igrejas e Mosteiros`) |
| Item de acordeão **sem título** | contentor visual; não cria nível (corrigido no Projeto MIKVEH) |
| `flip-box` (card) | título da frente → heading um nível abaixo do último heading; descrição → parágrafo logo a seguir |
| Pós-processamento | nenhum heading desce mais do que um nível em relação ao anterior |

Com isto, o nome de cada entidade fica **imediatamente antes** do seu texto:

```markdown
# Herança Cultural e Religiosa
## Igrejas e Mosteiros
### Sé Velha de Coimbra
Construída no século XII, …
### Mosteiro de Santa Clara-a-Velha
…
```

**Não foi inventado nenhum heading.** Todos os headings existem na fonte como
heading, título de card ou título de acordeão.

## 7. Pilot Results

O piloto teve 5 páginas estruturalmente diferentes e foi feito **antes** de
adquirir as restantes 19.

| Página | Estrutura | Resultado |
|---|---|---|
| Herança Cultural e Religiosa | acordeão com 3 grupos e 26 cards | 3 `##` e 26 `###`, cada monumento com o seu texto. A pull quote duplicada (responsive) aparece 1×. O verso "Preparar visita" foi removido. |
| Museus | 25 cards, carrossel promocional, banner CTA | 25 `##`. Removidos o carrossel de experiências (tuk-tuk, barcos, tours…), o banner "Planeie a sua visita" e **a frase de horário** ("…das 10h às 13h e das 14h às 17h"). "Junho de 2018" mantido. |
| Canção de Coimbra | texto cultural, player, cards de casas de fado | Texto completo e na ordem. Pull quote em `>`. "Playlist" (player vazio) removida como secção vazia. **"Casas para ouvir…"** (3 cards comerciais) removida por configuração. |
| Doçaria Conventual | acordeão de doces e secção de evento | `## Doces a não perder` → `### Arroz Doce de Coimbra` … `### Talhadas de Príncipe`. "Sabia que…" mantido. **"Mostra de Doçaria Conventual e Contemporânea"** (evento: acordeão, heading, texto e "Saber mais") removida por configuração. |
| Pedro e Inês | texto narrativo, citação de Camões, acordeão de locais | Narrativa completa (1355, 1357, D. Afonso IV). Verso em `>`. `## Para reviver esta emocionante história em Coimbra` com os locais em `###`. |

**Verificação raw vs processed nas 24 páginas:**
- Sem palavras introduzidas: todas as palavras do Markdown existem no HTML raw. A exceção de "cerâmica" e "david" é apenas aparente: vêm do `<title>` da página, usado no `# título`.
- Perdas verificadas elemento a elemento (`p`, `li`, títulos e descrições de cards, títulos de acordeão, `text-editor` sem `<p>`): **todas** correspondem a remoções previstas.

Três exemplos:

```text
RAW : …modelos… O horário de abertura é à 2ª, 3ª e 5ª feiras das 10h às 13h e das 14h às 17h.
MD  : …A entrada é gratuita mas é preciso marcar.            (frase de horário removida)

RAW : <h1>"O Fado de Coimbra é uma expressão musical única no mundo…"</h1>   (Elementor H1)
MD  : > "O Fado de Coimbra é uma expressão musical única no mundo…"

RAW : <p>1. República do Prá-Kys-Tão<br>2. República Boa-Bay-Ela<br>…</p>
MD  : 1. República do Prá-Kys-Tão
      2. República Boa-Bay-Ela
```

**Correções feitas durante a revisão do corpus completo:**
- **Secções vazias:** a remoção passou a repetir-se até estabilizar ("Ver também" ficava órfão).
- **Headings longos:** frases de destaque passaram a citação.
- **Itens de acordeão sem título:** deixaram de criar um nível.
- **Níveis de heading:** sem saltos.
- **`<br>`:** as listas e os versos mantêm as linhas.
- **`image-carousel`:** passou a ser descartado.
- **Secções configuradas:** Louça de Coimbra, cervejarias e APP.
- **`source_last_modified_at`:** deixou de usar o header HTTP.

## 8. Per-Document Summary

A contagem de palavras é do corpo, sem o front matter. "Headings" conta os `##`–`######`.

| document_id | Title | Category | Raw (KB) | Processed words | Headings | Notes / warnings |
|---|---|---|---:|---:|---:|---|
| `web-visitecoimbra-cancao-de-coimbra` | Canção de Coimbra | culture_traditions | 226 | 511 | 0 | secções removidas: Casas para ouvir a Canção de Coimbra; vazia: Playlist |
| `web-visitecoimbra-ceira` | Ceira | culture_traditions | 187 | 98 | 0 | — (documento curto) |
| `web-visitecoimbra-ceramica-de-coimbra` | Cerâmica de Coimbra | culture_traditions | 209 | 210 | 0 | removida: Saber mais sobre a Louça de Coimbra |
| `web-visitecoimbra-cestaria-de-bunho` | Cestaria de Bunho | culture_traditions | 202 | 319 | 0 | removida: Experiências |
| `web-visitecoimbra-coimbra-dos-estudantes` | Coimbra dos Estudantes | culture_traditions | 234 | 314 | 0 | vazias: cards "Ver também" (AAC, Museu Académico, Roteiro das Tradições Académicas) |
| `web-visitecoimbra-coimbra-muralhada` | Coimbra Muralhada | visitor_orientation | 209 | 266 | 0 | — |
| `web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira` | Coimbra: Uma Cidade com Tradição Cervejeira | gastronomy | 216 | 212 | 0 | removidas: BREW!, Epicura, Portuguese Pedro, Praxis |
| `web-visitecoimbra-d-afonso-henriques` | D. Afonso Henriques | city_history | 218 | 413 | 0 | — |
| `web-visitecoimbra-docaria-conventual-de-coimbra` | Doçaria Conventual de Coimbra | gastronomy | 257 | 683 | 11 | removida: Mostra de Doçaria… (evento) |
| `web-visitecoimbra-gastronomia-em-coimbra` | Gastronomia em Coimbra | gastronomy | 208 | 231 | 0 | — |
| `web-visitecoimbra-heranca-cultural-e-religiosa` | Herança Cultural e Religiosa | built_heritage | 347 | 2037 | 29 | removida: Não sabe por onde começar?; 1 duplicado responsive; **2 cards repetidos na fonte** (Mosteiro de São Francisco, Seminário Maior); **conflito registado** |
| `web-visitecoimbra-heranca-judaica` | Herança Judaica | city_history | 213 | 242 | 1 | removida: APP - Exposição “Judeus em Coimbra” |
| `web-visitecoimbra-heranca-mocarabe` | Herança Moçárabe | city_history | 187 | 107 | 0 | — (documento curto) |
| `web-visitecoimbra-luis-vaz-de-camoes` | Luís Vaz de Camões | city_history | 210 | 407 | 0 | — |
| `web-visitecoimbra-mercados` | Mercados | gastronomy | 221 | 233 | 0 | — |
| `web-visitecoimbra-museus` | Museus | museums_collections | 395 | 1131 | 23 | 1 frase de horário removida; **conflito registado**; `validity_notes` |
| `web-visitecoimbra-o-brasao-da-cidade-de-coimbra` | O Brasão da Cidade de Coimbra | city_history | 197 | 336 | 0 | — |
| `web-visitecoimbra-pedro-e-ines` | Pedro e Inês | city_history | 218 | 493 | 3 | — |
| `web-visitecoimbra-princesa-cindazunda` | Princesa Cindazunda | city_history | 192 | 340 | 0 | — |
| `web-visitecoimbra-rainha-santa-isabel` | Rainha Santa Isabel | city_history | 219 | 404 | 0 | — |
| `web-visitecoimbra-republicas` | Repúblicas | culture_traditions | 201 | 312 | 1 | — |
| `web-visitecoimbra-santo-antonio` | Santo António | city_history | 204 | 293 | 0 | — |
| `web-visitecoimbra-sesnando-david` | Sesnando David | city_history | 201 | 437 | 1 | — |
| `web-visitecoimbra-tecelagem-de-almalagues` | Tecelagem de Almalaguês | culture_traditions | 202 | 272 | 0 | removida: Experiências |

**Totais:**
- 24 documentos, **~10 300 palavras** processadas;
- 5.4 MB de raw e 124 KB de Markdown.

**Distribuição por categoria:**

| Categoria | N.º |
|---|---:|
| `city_history` | 10 |
| `culture_traditions` | 7 |
| `gastronomy` | 4 |
| `built_heritage` | 1 |
| `museums_collections` | 1 |
| `visitor_orientation` | 1 |

## 9. Known Conflicts

Os conflitos foram registados em `conflict_notes`. **O texto web não foi
corrigido**: o Markdown preserva a formulação da fonte, e isso é verificado por
teste.

| Documento web | Formulação web | PDF municipal (`fundacao-da-nacionalidade`) |
|---|---|---|
| `web-visitecoimbra-heranca-cultural-e-religiosa` | Santa Clara-a-Velha: "Fundado pela Rainha Santa Isabel, o edifício sofreu inundações recorrentes…" | "Fundado em 1283, por D. Mor Dias… em 1314, Dona Isabel de Aragão, a Rainha Santa Isabel, interessou-se pela refundação do mosteiro" |
| `web-visitecoimbra-museus` | "O Mosteiro de Santa Clara foi mandado construir em 1314 por D. Isabel de Aragão" | idem |

O conflito dos Museus é **novo**: foi encontrado nesta fase. A política de
autoridade entre fontes fica para decisão posterior.

## 10. PDF/Web Overlap

A sobreposição foi medida por contenção de 5-gramas do corpo de cada documento
web nos 8 Markdown PDF:

| Classe | Limiar | Documentos |
|---|---|---:|
| complementary | < 0.2 | **24** |
| partially_redundant | 0.2 – 0.6 | 0 |
| strongly_redundant | ≥ 0.6 | 0 |

O máximo é 0.091, na Herança Cultural e Religiosa face à brochura UC.

A seleção da vaga 1 excluiu, como previsto, as páginas redundantes do discovery
(roteiros HTML, Universidade, Cidade Património).

**Atenção:** a métrica é **textual**. Há **sobreposição temática** que ela não
mede. Por exemplo, Santa Clara-a-Velha, Sé Velha, Santa Cruz e Torre de Anto
aparecem nos PDFs e na web com textos diferentes. É aí que estão os conflitos
factuais, e é aí que a unificação terá de decidir.

Não foi feita nenhuma deduplicação.

## 11. Remaining Issues

| Problema | Severidade | Nota |
|---|---|---|
| Resíduo operacional conservador: "A entrada é gratuita mas é preciso marcar." (Museus) | MINOR | A regra só remove intervalos horários explícitos; alargá-la seria arriscado |
| Cards repetidos **na própria fonte** (Herança: Mosteiro de São Francisco e Seminário Maior, 2× cada, texto idêntico) | MINOR | Mantidos por fidelidade e sinalizados em warning; a decisão fica para o chunking |
| Título visual da página em `text-editor` (por exemplo "Doçaria conventual de Coimbra") fica como primeira linha de texto | MINOR | Não é heading e não se perde nada |
| Pull quotes podem repetir uma frase do corpo (por exemplo, na cervejeira a citação repete uma frase do parágrafo seguinte) | MINOR | Duplicação intra-documento pequena |
| Documentos curtos (Ceira 98 palavras, Herança Moçárabe 107) | MINOR | Acima do mínimo de 80 |
| As secções comerciais e de evento dependem de uma lista **por documento** | Limitação | Revista manualmente; uma nova vaga ou uma mudança no site exige revisão |
| Snapshot de 27-09-2026; o site pode mudar e não publica data de revisão | Limitação | Nova aquisição = novo raw e novo hash; o raw atual é imutável |
| Conflitos com os PDFs (§9) e sobreposição temática (§10) | A decidir | Política de source authority antes da unificação |
| 9 páginas do site em HTTP 500 durante o discovery | Fora do âmbito | Não aprovadas nesta vaga |

## 12. Decision

**IS THE WEB CORPUS READY FOR CHUNKING?**

# YES

**Justificação:**
- **Aquisição completa:** as 24 páginas aprovadas foram adquiridas e aceites, com raw imutável e SHA-256 verificado, e com proveniência completa no manifest único.
- **Preprocessing:** determinístico, offline e idempotente (processed = render fresco a partir do raw, com os 24 hashes iguais entre execuções).
- **Template e conteúdo comercial:** sem resíduos do template (menus, footer, contactos). CTAs, cards comerciais e eventos foram removidos só onde se isolam com segurança.
- **Fidelidade:** 0 palavras introduzidas, e todas as perdas são remoções previstas e documentadas.
- **Estrutura:** a hierarquia de headings foi normalizada, cada entidade fica junto ao seu texto, e não há headings falsos, órfãos nem saltos de nível.
- **Testes:** 55/55 OK (22 novos da web), sem rede.

**Condições para a fase de chunking (não bloqueiam):**
- a proveniência web é `document_id` + `url` + secção (heading), **sem `source_page`**;
- as citações `>` devem ficar dentro da secção onde aparecem;
- os conflitos registados e a sobreposição temática com os PDFs exigem uma política de autoridade antes do merge PDF + Web.

O chunking **não** foi implementado e aguarda autorização.
