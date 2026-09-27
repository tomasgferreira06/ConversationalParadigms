# Pre-Chunking Corpus Audit

## 1. Objective

Auditar a **qualidade semântica** dos 8 Markdown produzidos na Phase 2A antes de
serem usados para chunking. A pergunta é se o Markdown representa fielmente o
conteúdo dos PDFs como unidades de significado recuperáveis, e não apenas se o
pipeline corre.

Esta auditoria não alterou nenhum ficheiro. Não foram criados chunks, embeddings,
Vector DB nem retrieval, e não foi usado nenhum LLM. Nenhuma correção foi aplicada:
os problemas ficam registados com a correção sugerida.

## 2. Audit Method

Para cada documento, o PDF raw (`pymupdf`, camada de texto) foi comparado com o
Markdown processado, **página a página**, de quatro formas:

1. **Fidelidade lexical por página.** Para cada `source_page`, compara-se o
   vocabulário do PDF (palavras com ≥3 caracteres, NFC, minúsculas) com o do
   Markdown dessa página:
   - *coverage*: fração do vocabulário da página raw presente na página MD;
   - *introduced*: palavras do MD que não existem em nenhum ponto do PDF;
   - *from other pages*: palavras do MD que só existem noutra página do PDF
     (deteta texto deslocado entre páginas);
   - *missing*: palavras raw ausentes, inspecionadas manualmente no PDF.
2. **Scan estrutural.** Lista completa dos headings de cada documento, com a
   página e o nível, e todos os parágrafos curtos (<140 caracteres) ou sem
   pontuação final (detetam falsos headings, legendas, números soltos e frases
   partidas).
3. **Verificações dirigidas no PDF.** Para cada suspeita, lê-se o texto raw na
   ordem do PDF, incluindo:
   - a direção das linhas (texto vertical);
   - a largura dos glifos de espaço (letras espaçadas);
   - todos os hífenes de fim de linha e o resultado no MD;
   - as coordenadas (sequência completa raw vs MD).
4. **Duplicação entre documentos.** Contenção de 5-gramas de palavras entre
   parágrafos (≥25 palavras) de documentos diferentes e entre secções dos locais
   pedidos.

Os documentos pequenos (2 páginas) foram inspecionados na íntegra. A brochura de
44 páginas foi inspecionada no início, meio e fim, nas transições entre páginas,
em todos os headings e nas páginas 1–9, 34–44.

Os scripts de auditoria ficaram no scratchpad da sessão, fora do repositório.

## 3. Corpus Summary

| document_id | Páginas | Headings | Coverage nas páginas de texto* | Tokens introduzidos | Texto noutra página | Coordenadas raw/MD |
|---|---:|---:|---|---|---|---|
| coimbra-para-os-pequenitos | 2 | 7 | p1 0.96 · p2 0.30 (mapa) | — | 0 | 12/12 ✓ |
| coimbra-dos-escritores | 2 | 15 | p1 0.98 · p2 0.49 (mapa) | — | 0 | 28/28 ✓ |
| fado-e-tradicoes-academicas | 2 | 12 | p1 0.98 · p2 0.51 (mapa) | — | 0 | 20/20 ✓ |
| fundacao-da-nacionalidade | 2 | 10 | p1 0.97 · p2 0.51 (mapa) | `destacase` | 0 | 18/18 ✓ |
| jardins-historicos | 2 | 10 | p1 0.98 · p2 0.56 (mapa) | — | 0 | 18/18 ✓ |
| universidade-alta-sofia-patrimonio-mundial | 44 | 148 | 0.97–1.00 (texto); 0.71–0.84 (p34–35, mapa) | — | 0 | n/a |
| biblioteca-joanina-uctour | 6 | 5 | p2 0.88 · p3 0.95 · p4 0.27 (comercial) | — | 0 | n/a |
| viver-o-patrimonio-em-coimbra | 2 | 20 | p1 0.98 · p2 0.42 (mapa) | `depositada`, `reconhecida`, `ímpar` (reparações corretas) | 0 | 38/38 ✓ |

\* O vocabulário em falta nas páginas 1 dos roteiros é sempre o mesmo bloco de
rodapé promocional: contactos da Câmara e a lista "Roteiro …" dos outros 7
roteiros. As coverages baixas correspondem a omissões deliberadas (labels de
mapa, conteúdo comercial), confirmadas no PDF.

**Resultados globais de fidelidade:**
- Em 56 páginas, **nenhuma palavra aparece numa página diferente da do PDF**, por
  isso não há texto deslocado entre páginas.
- **Só um token corrompido** foi introduzido em todo o corpus (`destacase`). As
  outras três palavras novas são reparações corretas de letras espaçadas.
- Não há indícios de resumo, paráfrase ou factos introduzidos: o texto do MD é a
  sequência do PDF, com junção de linhas.
- Datas, nomes próprios e diacríticos estão preservados, sem `U+FFFD` nem
  soft hyphens. **A exceção é o texto com letras espaçadas do fado** (C1).
- Os marcadores `source_page` estão presentes, estão pela ordem certa e o texto a
  seguir a cada um pertence a essa página.

## 4. Per-Document Findings

### coimbra-para-os-pequenitos

- **Structure:** título correto; 6 secções numeradas (`## 1.`–`## 6.`) que
  correspondem ao PDF. As subentradas do §1 ("museu da ciência | laboratório
  chimico - …", "gabinete de física - …") ficam inline, como no PDF.
- **Text quality:** bom, exceto dois pontos:
  - §4 Parque Verde partido a meio de frase ("Percorrendo ce[rca…] | peões e para
    ciclovias"), por quebra de coluna, sem texto intrometido;
  - p2: `Mosteiro de Santa Clara-a- Velha`, com espaço depois do hífen.
- **Noise:** p1 §1 contém um **bloco de legendas intrometido a meio de uma frase**
  (ver M2).
- **Provenance:** correta. A p2 contém o título lateral e "outros locais a visitar".
- **Fidelity:** coverage de 0.96 na p1; o vocabulário em falta é só o rodapé
  promocional.
- **Chunking readiness:** não está pronto enquanto M2 não for corrigido.
- **Findings:** M2 (MAJOR), m2, m3 (MINOR).

### coimbra-dos-escritores

- **Structure:** título correto; 14 secções numeradas, pela ordem do PDF, sem
  falsos headings.
- **Text quality:** limpa. Não foram encontrados artefactos.
- **Noise:** a p2 tem apenas o título lateral ("escritores") e "outros locais a
  visitar".
- **Provenance / fidelity:** coverage de 0.98 na p1; 28/28 coordenadas.
- **Chunking readiness:** pronto. Duplica secções de `jardins-historicos` (ver §5).
- **Findings:** nenhum problema próprio.

### fado-e-tradicoes-academicas

- **Structure:** título correto; 11 secções numeradas corretas. `## 1. ASSOCIAÇÂO`
  com `Â` é um erro da própria fonte, confirmado no PDF (preservar).
- **Text quality:** **CRITICAL.** Cerca de 50% do texto (14 de 33 parágrafos,
  ~7.7k de 15.5k caracteres) está com letras espaçadas, incluindo datas:
  - `E s t a b e l e c i d a , e m 1 5 9 3 , n a a l a n o r t e d o edifício`
    (§2, Prisão Académica);
  - `d e s d e 1 6 d e j u l h o d e 2 0 0 3 , p o r d e c r e t o d o C o n s e l h o d e R e p …`;
  - `a 1 1 d e D eze m b r o d e 1 9 4 8`;
  - `O ex t e r i o r é r o b u s t o , s i m é t r i co , co m e s ca s s a s a b e r t u ra s` (§7 Sé Velha);
  - `c o o r d e n a das: 40.207449, -8.429593` (§10).
- **Causa (confirmada):** o próprio PDF tem glifos de espaço reais entre letras
  (fonte Montserrat-Light, justificação por espaçamento). Não é um artefacto do
  PyMuPDF. Os espaços entre letras têm 1.30–1.36 pt e os espaços entre palavras
  2.03 pt, por isso são distinguíveis. Filtrar os espaços estreitos reconstrói
  `Estabelecida, em 1593, na ala norte do`, o que confirma que a correção é
  viável.
- **Noise:** §7 partido a meio de frase ("retábulo da capela-mor, em | gótico
  flamejante"), por quebra de coluna.
- **Provenance / fidelity:** nenhum conteúdo perdido nem deslocado. O problema é
  a forma do texto, não o conteúdo. 20/20 coordenadas.
- **Chunking readiness:** **não está pronto.** Um texto assim produz embeddings
  degradados e datas irrecuperáveis ("1593" não existe como token).
- **Findings:** C1 (CRITICAL), m2 (MINOR).

### fundacao-da-nacionalidade

- **Structure:** título correto; 9 secções numeradas corretas.
- **Text quality:**
  - `destacase` (p1 §2): no PDF é `destaca-` + `se` em fim de linha. A regra de
    hífen juntou o pronome enclítico. É o único caso deste tipo no corpus (todos
    os hífenes de fim de linha foram verificados).
  - §7 partido a meio de frase ("composto por reproduções | à escala reduzida").
- **Noise:** p1 §8 tem um **bloco de legendas intrometido a meio de uma frase**,
  que parte o nome próprio "Gonçalo Byrne":
  `…com projeto do arquiteto Gonçalo` / `fundação da nacionalidade` /
  `igreja de santa cruz | panteão nacional bandeira da fundação túmulo d. afonso henriques túmulo d. sancho i` /
  `a. b. c. d.` / `Byrne. Com esta recente requalificação…` (ver M3).
- **Provenance:** correta. A p2 preserva a introdução histórica e "outros locais a
  visitar" e omite os labels do mapa. Confirmado no PDF: nenhum texto editorial
  perdido.
- **Text/p2:** a introdução, que no PDF tem 3 parágrafos, ficou num só (m4);
  `I lgreja` (×3) é um glifo da própria fonte.
- **Chunking readiness:** não está pronto enquanto M3 não for corrigido.
- **Findings:** M3 (MAJOR), m1, m2, m4 (MINOR).

### jardins-historicos

- **Structure:** título correto; 9 secções numeradas corretas.
- **Text quality:** boa. Há dois parágrafos partidos a meio de frase por quebra de
  coluna, sem intrusão:
  - "museu da água - … tratamento de água para | abastecimento da rede pública";
  - "busto de eça de queirós - … destinado a assinalar o | centenário da morte…".
- **Noise:** "O Mundo Calou-se / O Silêncio do Mundo …" é uma lista de títulos de
  esculturas da própria fonte (§7). Legítimo.
- **Provenance / fidelity:** coverage de 0.98 na p1; 18/18 coordenadas.
- **Chunking readiness:** pronto. Duplica secções de `coimbra-dos-escritores` e
  `coimbra-para-os-pequenitos` (§5).
- **Findings:** m2 (MINOR).

### universidade-alta-sofia-patrimonio-mundial (inspeção aprofundada)

- **Início (p1–9):**
  - p1/p3 contêm só o título de capa; p4/p8 contêm epígrafes verticais decorativas
    (António Nobre), omitidas como documentado;
  - p6 tem a introdução correta, com a lista de 4 pontos;
  - p7 tem o índice dos 31 pontos do roteiro, com números de mapa soltos (`13`,
    `10 11`, `2 3`…);
  - p9 é só uma legenda.
  - As páginas 2, 5 e 43 não têm texto no PDF; os marcadores estão presentes e
    corretos.
- **Meio (p10–33):** a estrutura é boa:
  - `## 1.`–`## 31.` correspondem às secções do PDF;
  - `###` (Porta Férrea, Via Latina, Sala dos Capelos…, Jardins da AAC…) são
    subsecções reais;
  - as secções continuam entre páginas pela ordem certa (p10→p11 "Torre",
    p24→p25 §19), fiel ao PDF;
  - cada página par de texto é seguida de uma página de legendas curtas (p13, p15,
    p17, p19, p21, p23, p25, p27, p29, p31, p33);
  - o número de página impresso (`8`, `12`, `14`…) aparece como parágrafo isolado;
  - §5 Arquivo está partido a meio de frase ("o edifício é inaugurado em | 1948.");
  - na p25, uma legenda está partida e intercalada com outras ("Colégio de Santa
    Rita, dos Agostinhos Descalços" … "ou dos Grilos").
- **Mapa (p34–35):** **MAJOR.** A nuvem de labels do mapa foi extraída e ~85 labels
  foram promovidos a headings `###`:
  - fragmentos cortados: `### USEU DA`, `### ÊNCIA`, `### AGA`, `### DONAL E INÊS`,
    `### O CENTRO`, `### EXPLORATÓRIO CENT DE CIÊNCIA VIVA DE COI`;
  - legenda: `### PARQUES AUTOCARRO`, `### LINHA 103`, `### PJ | SEF | PSP | PM | GNR`;
  - locais reais como secções vazias: `### SÉ VELHA`, `### JARDIM BOTÂNICO`,
    `### PORTUGAL DOS PEQUENITOS`.
  - O mesmo acontece em `### OCEANO ATLÂNTICO` (p41, mapa de Portugal), e `A8`
    (p40) é um label solto.
- **Final (p36–44):**
  - p36 tem o título vertical "Roteiros Temáticos" omitido (a secção seguinte
    perde o título, m5);
  - p37 tem a lista promocional de roteiros;
  - p38–39 têm o texto de apresentação dos roteiros, correto (a citação de
    Manuel Alegre foi preservada; a epígrafe vertical de António Nobre foi
    omitida);
  - p40 tem o texto UNESCO do Centro de Portugal;
  - p42 tem os créditos e p44 os contactos.
- **Running headers** "Coimbra, Património Mundial" foram removidos corretamente.
- **Fidelity:** coverage de 0.97–1.00 em todas as páginas de texto. O vocabulário
  em falta é só running headers, tipografia vertical decorativa e labels de mapa.
- **Chunking readiness:** não está pronto enquanto M1 não for corrigido. M4 deve
  ser tratado no chunking.
- **Findings:** M1, M4 (MAJOR); m2, m5, m6, m7, m8 (MINOR).

### biblioteca-joanina-uctour

- **Structure:** `# Biblioteca Joanina`, `## Biblioteca Joanina`, `## Piso Nobre`,
  `## Piso Intermédio`, `## Prisão Académica` correspondem ao conteúdo da página
  web.
- **Text quality:** excelente. Parágrafos completos, datas (1728, 1777, 1834, 1782,
  1 de novembro de 2010) e números (60 000 volumes, 2 metros e 11 centímetros)
  preservados.
- **Noise:**
  - "O que visitar" no início da p2 é um label de navegação;
  - a navegação, os preços, os bilhetes, o sitemap e o footer (p4–6) foram
    removidos corretamente, confirmado no PDF;
  - a p1 é uma pré-visualização duplicada, marcada e vazia, como documentado.
- **Provenance:** correta. A frase final da §Prisão Académica continua da p3 para
  a p4 ("na parte | baixa da cidade"), como no PDF.
- **Chunking readiness:** pronto.
- **Findings:** m7 (MINOR).

### viver-o-patrimonio-em-coimbra

- **Structure:** título correto; 19 secções numeradas corretas, incluindo os
  pontos 1 e 12, recuperados na Phase 2A.
- **Text quality:** boa. As 3 palavras novas (`depositada`, `reconhecida`,
  `ímpar`) vêm de reparações corretas de letras espaçadas e de um hífen legítimo
  (`deposita-|da`). Não foram encontradas letras espaçadas remanescentes.
- **Noise:** a p2 tem só o título lateral e "outros locais a visitar".
- **Provenance / fidelity:** coverage de 0.98 na p1; 38/38 coordenadas.
- **Chunking readiness:** pronto. O §1 Paço das Escolas é praticamente idêntico ao
  do fado (§5).
- **Findings:** nenhum problema próprio.

## 5. Cross-Document Duplication

A contenção de 5-gramas encontrou 61 pares de parágrafos entre documentos com
≥0.30. As medidas de secção abaixo são contenção em 5-gramas.

### A) Duplicação problemática (texto praticamente copiado)

| Local | Documentos / secções | Contenção |
|---|---|---:|
| Paço das Escolas (e subentradas) | fado §2 ↔ viver §1; ambos ↔ UC §1 (Torre, Gerais, Via Latina, Escadas de Minerva, Sala do Exame Privado…) | 0.92 (secção); 0.60–1.00 (parágrafos) |
| Associação Académica de Coimbra | fado §1 ↔ UC §14 | 1.00 |
| Parque Verde do Mondego | pequenitos §4 ↔ jardins §2 | 1.00 |
| Parque Dr. Manuel Braga | escritores §2 ↔ jardins §3 | 0.91 |
| Câmara Municipal | fundacao §1 ↔ viver §17 (Praça 8 de Maio) | 0.93 (parágrafo) |
| Sé Velha | fado §7 ↔ UC §21 | 0.89 |
| Torre de Anto | escritores §12 ↔ fado §6 | 0.66 |
| Jardim da Sereia | escritores §7 ↔ jardins §7 | 0.64 |
| Portugal dos Pequenitos | pequenitos §6 ↔ fundacao §7 | 0.55 (secção), 0.86 (parágrafo) |

O conteúdo sobre o Paço das Escolas existe essencialmente **três vezes**. Isto já
foi observado no smoke test: o top-3 de "Portugal dos Pequenitos" trouxe duas
cópias do mesmo texto.

### B) Sobreposição útil (mesmo local, perspetiva ou texto diferente)

| Local | Documentos | Contenção | Nota |
|---|---|---:|---|
| Biblioteca Joanina | UCTour (detalhe: pisos, morcegos, prisão) ↔ UC §1 "Casa da Livraria" | 0.00 | complementares; também mencionada em fado/viver |
| Jardim Botânico | escritores §4 ↔ jardins §4 ↔ UC §16 | 0.00–0.01 | perspetivas literária, paisagística e universitária |
| Santa Cruz | fundacao §2 ↔ UC §24 (↔ viver §17 parcial) | 0.49 | base comum (1131, D. Afonso Henriques) e detalhes diferentes |
| Penedo da Saudade | escritores §5 ↔ jardins §6 | 0.29 | parcialmente diferente |
| Santa Clara-a-Velha / -a-Nova | fundacao §6 e §9 | — | duas secções distintas no mesmo documento; não há duplicação |

Nesta fase não se remove nada. A política de deduplicação é uma decisão separada
(`D2_PLAN.md` §6).

## 6. Potential Chunking Risks

1. **Texto com letras espaçadas (C1):** embeddings de baixa qualidade e datas
   irrecuperáveis em metade do documento fado.
2. **Falsos headings como section metadata (M1):** se o chunking usar headings, a
   UC gera ~85 "secções" de lixo nas p34–35. Algumas têm nomes de locais reais
   (`### SÉ VELHA`, `### JARDIM BOTÂNICO`) e podem competir no retrieval com as
   secções verdadeiras.
3. **Duas secções fundidas / frase interrompida (M2, M3):** um chunk da secção
   Museus/Convento São Francisco inclui legendas de outra zona da página, e o
   nome "Gonçalo Byrne" fica partido.
4. **Unidades de baixa informação (M4):** páginas só com legendas e números de
   página isolados na UC geram chunks minúsculos. No smoke test,
   `Casa da Livraria | Biblioteca Joanina` ocupou lugares do top-3 em 2 de 5
   perguntas.
5. **Perda da associação heading–conteúdo:** o Markdown liga bem os headings ao
   corpo (fora do mapa, nenhum heading real ficou órfão). No entanto, um splitter
   por caracteres que corte no `\n\n` depois de `## N. TÍTULO` separa-os. O smoke
   test confirmou-o como causa principal da falha em "Mosteiro de Santa Cruz". O
   chunking deve ser **heading-aware** ou propagar o título da secção para cada
   chunk.
6. **Secções que atravessam páginas:** p10→p11 e p24→p25 (UC), p3→p4 (Joanina).
   Com chunking por página, o chunk da página seguinte começa sem heading (por
   exemplo `bastante italianizantes…`). O chunking deve **manter a secção corrente
   através dos marcadores de página**, preservando `source_page` por chunk.
7. **Frases partidas por quebra de coluna (m2):** 6 casos em que `\n\n` cai a meio
   de uma frase. São pontos de corte preferidos pelo splitter e podem separar um
   facto da sua data ("inaugurado em | 1948.").
8. **Duplicação (§5):** as cópias ocupam o top-k e diminuem a diversidade de
   fontes.
9. **Proveniência grossa nos roteiros:** todo o conteúdo dos roteiros está na p1,
   por isso `source_page` é correto mas pouco discriminativo. A secção numerada é
   o localizador útil.
10. **Linhas `**Coordenadas:**`:** pertencem ao fim da secção. Com overlap sem
    noção de secção, "sangram" para o início do chunk seguinte (observado no smoke
    test).

## 7. Issues Requiring Correction

| ID | Severidade | Documento | Página | Trecho | Tipo | Causa provável | Correção sugerida |
|---|---|---|---|---|---|---|---|
| C1 | **CRITICAL** | fado-e-tradicoes-academicas | 1 | `E s t a b e l e c i d a , e m 1 5 9 3 …` (14/33 parágrafos) | letras artificialmente espaçadas, incluindo datas | glifos de espaço reais no PDF (Montserrat-Light, justificação) | Extração ao nível do glifo (`rawdict`) só para este documento: descartar glifos de espaço mais estreitos que ~0.8× a largura do espaço de palavra. Já verificado numa amostra. Configurar em `DOCUMENT_CONFIG`, sem regra global. |
| M1 | **MAJOR** | universidade-alta-sofia-patrimonio-mundial | 34, 35 (+40, 41) | `### USEU DA`, `### ÊNCIA`, `### AGA`, `### SÉ VELHA`, `### LINHA 103`, `### OCEANO ATLÂNTICO`, `A8` | falsos headings a partir de labels de mapa | as páginas de mapa não estão configuradas como tal; a heurística de headings curtos em maiúsculas promove os labels | Tratar p34–35 e p40–41 como páginas cartográficas: omitir a nuvem de labels, como nos roteiros, e manter só blocos editoriais, se existirem. No mínimo, desativar a promoção a heading nestas páginas. |
| M2 | **MAJOR** | coimbra-para-os-pequenitos | 1 | `…modelos que constitui o` / `Portugal dos pequenitos` / `“Tudo é minúsculo…” Bissaya Barreto` / `pavilhão da guiné-bissau …` / `a. b. c. d. e. f. g. h.` / `mais antigo museu de Portugal…` | bloco de legendas inserido a meio de uma frase | a ordenação de blocos por coluna coloca a zona de legendas das fotografias entre dois blocos da mesma coluna | Detetar a zona de legendas (bloco com marcadores `a.`–`h.` e legendas em minúsculas) e emiti-la depois do texto da página, como bloco separado, ou omiti-la. Garantir a continuidade da frase. |
| M3 | **MAJOR** | fundacao-da-nacionalidade | 1 | `…arquiteto Gonçalo` / legendas `a. b. c. d.` / `Byrne. Com esta…` | idem; parte um nome próprio | idem | Mesma correção que M2. |
| M4 | **MAJOR** (chunking) | universidade-alta-sofia-patrimonio-mundial | 1, 3, 9, 13, 15, 17 … 33, 39; números em quase todas as páginas pares | `Casa da Livraria \| Biblioteca Joanina`, `12`, `14` | unidades de baixa informação | legendas e números de página impressos | Duas opções: no preprocessing, remover os números de página impressos isolados (padrão exato: um número sozinho na primeira linha, igual ao número impresso esperado); ou, no chunking, impor um comprimento mínimo ou juntar legendas curtas ao chunk vizinho. Não apagar as legendas: contêm nomes de locais. |
| M5 | **MAJOR** (retrieval) | vários | — | ver §5.A | duplicação entre documentos | os roteiros municipais reutilizam as mesmas descrições | Não corrigir no preprocessing. Decidir a política no chunking/retrieval (por exemplo, deduplicação por hash de parágrafo com registo de todas as fontes, ou diversidade de `document_id` no top-k). |
| m1 | MINOR | fundacao-da-nacionalidade | 1 | `destacase` | hífen enclítico removido | regra "hífen + minúscula" aplicada a `-se` | Manter o hífen quando a continuação é um clítico (`se`, `lhe`, `o`, `a`, `nos`…). É o único caso no corpus. |
| m2 | MINOR | fundacao §7, pequenitos §4, jardins (museu da água, busto de Eça), fado §7, UC §5 | 1 / 16 | `reproduções` \| `à escala`; `inaugurado em` \| `1948.` | parágrafo partido a meio de frase | quebra de coluna emitida como parágrafo novo | Juntar o parágrafo seguinte quando o anterior não termina em pontuação e o seguinte começa em minúscula ou dígito. |
| m3 | MINOR | coimbra-para-os-pequenitos | 2 | `Santa Clara-a- Velha` | espaço depois de hífen | hífen de fim de linha seguido de maiúscula junta com espaço | Com hífen interno de nome composto, juntar sem espaço. |
| m4 | MINOR | 6 roteiros | 2 | introdução num único parágrafo; `fundação da nacionalidade`, `outros locais a visitar` em texto simples | limites de parágrafo perdidos; títulos laterais não marcados | a coluna lateral não tem linhas em branco | Opcional: promover o título lateral e "outros locais a visitar" a heading (por exemplo `## Introdução`). |
| m5 | MINOR | UC | 36 | título vertical "Roteiros Temáticos" omitido | a secção p37–40 fica sem título | omissão deliberada de texto vertical | Opcional: recuperar este título vertical como heading. |
| m6 | MINOR | UC | 7 | `13`, `10 11`, `2 3` | números de mapa soltos junto ao índice | legenda do mapa do roteiro | Remover as linhas só com números nesta página; manter o índice dos 31 pontos (é útil). |
| m7 | MINOR | UC p37, p42, p44; Joanina p2 | — | lista de roteiros, créditos, contactos, `O que visitar` | ruído residual | blocos editoriais periféricos | Opcional. Impacto baixo. |
| m8 | MINOR | UC | 25 | `Colégio de Santa Rita, dos Agostinhos Descalços` … `ou dos Grilos` | legenda partida e intercalada | ordem de blocos das legendas | Opcional. |

## 8. Acceptable Limitations

| ID | Limitação | Justificação |
|---|---|---|
| A1 | Labels de mapa omitidos nas p2 dos roteiros | Confirmado no PDF: nuvem de labels sem ordem semântica. O texto editorial foi preservado na íntegra. |
| A2 | Tipografia vertical decorativa omitida (UC p1/3/4/8/36/38: epígrafes de António Nobre, "Coimbra, Património Mundial") | Decorativa; o texto principal está completo (exceção menor em m5). |
| A3 | Páginas UC 2, 5 e 43 sem texto | Não têm camada de texto; os marcadores estão preservados. OCR fora do âmbito. |
| A4 | Rodapé promocional das p1 dos roteiros (contactos, lista de roteiros) removido | Não é conteúdo substantivo. |
| A5 | Erros da fonte preservados (`ASSOCIAÇÂO`, `I lgreja`, `edificio`, `São Tómas`) | O preprocessing não corrige a fonte. |
| A6 | Frases que continuam entre páginas (UC p10→11, p24→25; Joanina p3→4) | Fiel ao PDF. Deve ser tratado no chunking (§6.6). |
| A7 | Proveniência pouco discriminativa nos roteiros (tudo na p1) | É a paginação real do PDF. |
| A8 | UCTour: p1 duplicada vazia; conteúdo comercial das p4–6 removido | Documentado e confirmado no PDF. |
| A9 | Sobreposição útil entre documentos (§5.B) | Perspetivas complementares; manter. |

## 9. Final Decision

# NOT READY FOR CHUNKING

**Justificação:**

- **C1 (CRITICAL):** cerca de metade do `fado-e-tradicoes-academicas` tem letras
  espaçadas, incluindo datas. É um problema de extração, a causa está confirmada e
  a correção é determinística. Fazer chunking agora daria embeddings de baixa
  qualidade para uma das 8 fontes.
- **M1–M3 (MAJOR)** devem ser corrigidos no mesmo passo porque são locais e
  baratos. M1 introduz ~85 falsos headings exatamente quando o chunking vai passar
  a usar headings como metadata. M2 e M3 fundem legendas no meio de frases.

**O corpus está, em geral, em bom estado:**
- fidelidade lexical elevada;
- nenhum texto deslocado entre páginas;
- 134/134 coordenadas preservadas pela ordem;
- nenhum resumo nem paráfrase;
- 4 documentos prontos sem alterações (`escritores`, `jardins`, `joanina`, `viver`).

**Próximo passo proposto** (a aprovar pelo utilizador):
1. corrigir C1, M1, M2, M3 e m1 no `preprocess_documents.py`, via `DOCUMENT_CONFIG`
   e com testes;
2. regenerar apenas os documentos afetados;
3. repetir esta auditoria nesses documentos.

M4, M5 e os riscos da §6 ficam para a fase de chunking/retrieval.
