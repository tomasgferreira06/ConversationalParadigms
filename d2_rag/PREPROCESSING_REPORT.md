# D2 — Preprocessing Report

## Approach

A pipeline transforma deterministicamente cada PDF aceite no manifest numa representação Markdown:

```text
PDF raw imutável
  → extração por página
  → seleção de ordem de leitura
  → limpeza conservadora
  → reconstrução de parágrafos e headings
  → Markdown UTF-8 com proveniência de página
```

O ponto de entrada é `scripts/preprocess_documents.py`. O script lê apenas documentos com `status: accepted` em `data/manifest.jsonl`, verifica o SHA-256 ndo raw antes de processar e escreve o resultado no `processed_path` registado. Pode processar IDs explícitos com `--documets` ou todos os documentos aceites com `--all`.

Não existe aleatoriedade, timestamp gerado, chamada de rede ou LLM. Os outputs são sempre regenerados a partir dos PDFs raw, do manifest e do código versionado.

## Extraction

Foi usada a biblioteca **PyMuPDF 1.28.2** (`pymupdf`). O projeto não tinha uma biblioteca de PDF instalada. `pypdf` foi inicialmente avaliada por estar alinhada com a worksheet, mas corrompeu diacríticos destes documentos, produzindo exemplos como `C�MARA`, `Jo�o` e `Patrim�nio`. Foi removida e não faz parte das dependências finais.

PyMuPDF preservou os caracteres portugueses e disponibilizou texto, blocos, coordenadas de layout e direção das linhas. Foram usadas três estratégias explícitas:

1. **Roteiros municipais de duas páginas**: a primeira página é lida por blocos, coluna a coluna. Na segunda página, que contém um mapa, são omitidos rótulos cartográficos dispersos e preservado o bloco editorial lateral com a introdução e “outros locais a visitar”.
2. **Brochura Património Mundial**: são lidos blocos horizontais; tipografia vertical decorativa é ignorada para não interferir com a ordem do texto principal.
3. **UCTour**: é usada a extração textual ordenada, seguida de regras documentadas para browser/navigation noise e conteúdo duplicado.

Não foi usado OCR. Os oito PDFs contêm texto extraível.

## Cleaning Rules

A pipeline executa apenas transformações mecânicas e determinísticas:

- normalização Unicode NFC;
- substituição de non-breaking spaces e remoção de soft hyphens;
- normalização de whitespace horizontal e linhas em branco repetidas;
- junção de linhas do mesmo parágrafo;
- reparação de palavras partidas por hífen apenas quando a continuação começa por minúscula;
- deteção de headings numerados dos roteiros quando o título é predominantemente maiúsculo;
- deteção conservadora de headings curtos em maiúsculas;
- união de headings que ficaram repartidos por linhas consecutivas;
- conversão de `coordenadas: latitude, longitude` para `**Coordenadas:** latitude, longitude` sem alterar os valores;
- remoção de headers/footers exatamente repetidos em documentos com mais de duas páginas;
- remoção de running headers com o padrão exato `Coimbra, Património Mundial <página>`;
- remoção dos tokens UCTour conhecidos: `keyboard_arrow_left`, `chevron_left`, `chevron_right`, `fiber_manual_record`, `format_list_bulleted`, `shopping_cart` e `arrow_forward_ios`;
- remoção do cabeçalho de impressão do browser e do URL/page counter UCTour;
- substituição desses tokens por espaços quando surgem colados a palavras, evitando concatenar texto substantivo;
- três reparações exatas e revistas de letras artificialmente espaçadas: `c a s a d a l i v r a r i a`, `b i b l i o t e c a j o a n i n a` e `O b r a í m p a r e r e c o n h e c i d a`.

Não existe uma regra geral que una qualquer sequência de letras isoladas, porque isso poderia destruir iniciais, siglas ou texto legítimo. Não são corrigidas grafias da fonte, por exemplo `edificio`, nem factos, datas ou terminologia.

### Document-specific configuration

- Os seis roteiros municipais usam leitura em colunas e tratamento da página cartográfica.
- `universidade-alta-sofia-patrimonio-mundial` ignora texto vertical decorativo.
- `biblioteca-joanina-uctour` remove a página 1 da representação textual porque é uma pré-visualização truncada repetida integralmente a partir da página 2; o marcador da página 1 permanece. O conteúdo posterior a `Programas que incluem este espaço` é composto por programas, preços, compra, sitemap e footer e não é incluído. O texto descritivo que continua no início da página 4 é preservado.

As regras estão centralizadas em `DOCUMENT_CONFIG`, em vez de `if filename == ...` dispersos.

## Page Provenance

Cada página original tem exatamente um marcador, pela ordem do PDF:

```markdown
<!-- source_page: 1 -->
```

O marcador existe mesmo quando a página não contém texto extraível ou quando o seu conteúdo é puramente gráfico/duplicado. Isto permite que o futuro chunking associe texto ao `document_id` e à página de origem sem transformar páginas em headings Markdown.

Cada Markdown inclui front matter mínimo com `document_id`, `title`, `source_organization`, `source_file` e `language`. O manifest continua a ser a source of truth.

## Pilot Documents

O piloto obrigatório foi executado e inspecionado antes de processar os restantes cinco documentos:

1. `FUNDACAO-DA-NACIONALIDADE_PT.pdf` — roteiro municipal em colunas;
2. `patrimoniomundial_brochura.pdf` — brochura de 44 páginas com estrutura editorial complexa;
3. `UnivCoimbra - UCTour.pdf` — impressão de página web com navegação, duplicação e conteúdo comercial.

A primeira execução do piloto foi rejeitada para expansão: a página cartográfica gerava falsos headings, texto vertical perturbava a brochura e tokens UCTour colados a palavras permaneciam. Depois de regras restritas para estes padrões, o piloto foi novamente executado, inspecionado e considerado adequado.

## Findings per Document

### `fundacao-da-nacionalidade`

- Duas páginas; primeira página com três colunas e nove pontos de roteiro.
- Headings 1–9, nomes próprios, datas e coordenadas foram preservados.
- A segunda página mistura mapa e texto editorial. Os rótulos dispersos do mapa foram omitidos; introdução histórica e “outros locais a visitar” foram mantidos.
- Warning esperado: `Map labels omitted; editorial sidebar retained.`

### `universidade-alta-sofia-patrimonio-mundial`

- 44 páginas, com páginas gráficas, títulos verticais, running headers, texto principal, legendas e secções numeradas.
- A leitura por blocos horizontais evita inserir títulos verticais no meio dos parágrafos.
- Secções numeradas e subtítulos recuperáveis foram convertidos em headings.
- As páginas 2, 5 e 43 não têm texto extraível; os respetivos marcadores foram preservados e foram emitidos warnings.
- Algumas legendas de imagens permanecem como texto simples. Esta escolha é conservadora: não são descartadas quando podem conter nomes de locais.

### `biblioteca-joanina-uctour`

- Seis páginas produzidas por impressão do browser.
- A página 1 é uma versão truncada/duplicada do início da página 2 e não contribui texto para o Markdown.
- O texto substantivo das páginas 2–4 foi preservado: Biblioteca Joanina, Piso Nobre, conservação dos livros, morcegos, Piso Intermédio e Prisão Académica.
- Navigation tokens, cabeçalhos do browser, URL/page counter, programas, preços, botões, sitemap e footer foram removidos.
- A redução de caracteres é elevada por esta razão e não corresponde a resumo do conteúdo descritivo.

### Restantes roteiros

- `coimbra-para-os-pequenitos`: seis pontos recuperados, com coordenadas, mais introdução editorial da página 2.
- `coimbra-dos-escritores`: catorze pontos recuperados; leitura em colunas e texto introdutório preservados.
- `fado-e-tradicoes-academicas`: onze pontos recuperados; reparação exata de heading com letras espaçadas.
- `jardins-historicos`: nove pontos recuperados, incluindo descrições longas e coordenadas.
- `viver-o-patrimonio-em-coimbra`: dezanove pontos recuperados. A inspeção final detetou que os pontos 1 e 12 estavam acima da margem inicial; a regra de layout foi corrigida e os dois passaram a ser preservados. Uma frase adicional com letras espaçadas foi reparada por correspondência exata.

Todos os roteiros emitem o warning esperado relativo à omissão de rótulos cartográficos dispersos.

## Validation Examples

Os exemplos mostram transformações mecânicas, não reescrita.

### Roteiro e coordenadas

```text
2. IGREJA DE SANTA CRUZ | PANTEÃO NACIONAL
...
coordenadas: 40.210926, -8.429024
```

torna-se:

```markdown
## 2. IGREJA DE SANTA CRUZ | PANTEÃO NACIONAL

...

**Coordenadas:** 40.210926, -8.429024
```

### Ruído UCTour colado ao texto

```text
temperatura,BILHETESos livros podem
```

torna-se:

```text
temperatura, os livros podem
```

### Artefacto de letras espaçadas revisto

```text
c a s a d a l i v r a r i a
```

torna-se:

```text
casa da livraria
```

### Proveniência

O conteúdo de cada página é precedido por `<!-- source_page: N -->`; não é fundido através desse marcador.

## Final Audit

| Document ID | Raw pages | Extracted chars | Processed chars | Approx. removed | Headings | Warnings |
|---|---:|---:|---:|---:|---:|---:|
| `coimbra-para-os-pequenitos` | 2 | 8,360 | 8,338 | 0.26% | 7 | 1 |
| `coimbra-dos-escritores` | 2 | 16,120 | 16,029 | 0.56% | 15 | 1 |
| `fado-e-tradicoes-academicas` | 2 | 16,584 | 16,409 | 1.06% | 12 | 1 |
| `fundacao-da-nacionalidade` | 2 | 8,968 | 8,924 | 0.49% | 10 | 1 |
| `jardins-historicos` | 2 | 17,944 | 17,811 | 0.74% | 10 | 1 |
| `universidade-alta-sofia-patrimonio-mundial` | 44 | 38,313 | 38,356 | 0.00%* | 148 | 3 |
| `biblioteca-joanina-uctour` | 6 | 16,510 | 5,338 | 67.67% | 5 | 0 |
| `viver-o-patrimonio-em-coimbra` | 2 | 17,091 | 17,007 | 0.49% | 20 | 1 |

\* A adição de sintaxe Markdown pode tornar a representação alguns caracteres maior; a percentagem reportada é limitada a zero. Estas métricas são indicadores de inspeção, não provas automáticas de qualidade.

A auditoria confirmou:

- 8 PDFs raw esperados e 8 Markdown;
- um `document_id` e paths coerentes para cada par;
- todos os outputs não vazios;
- exatamente um marcador por página e na ordem correta;
- UTF-8 sem `U+FFFD`;
- hashes SHA-256 raw iguais aos registados no manifest;
- outputs idênticos em execuções repetidas do piloto;
- 11 testes unitários de transformação aprovados.

## Remaining Problems

- A ordem de leitura de PDFs editoriais não pode ser inferida perfeitamente em todos os layouts. A estratégia foi validada para estes oito ficheiros, não para PDFs arbitrários.
- Texto presente apenas em imagens não é extraído, porque OCR está fora desta baseline.
- As páginas 2, 5 e 43 da brochura não contêm texto extraível.
- Rótulos individuais dos mapas dos roteiros são deliberadamente omitidos; preservar a nuvem de rótulos produziria texto sem ordem semântica fiável. O PDF continua a ser a source of truth.
- Tipografia vertical decorativa da brochura é omitida. O texto horizontal principal e headings correspondentes são preservados quando existem.
- Algumas legendas, números isolados e labels editoriais podem permanecer na brochura. Removê-los por heurística agressiva arriscaria eliminar nomes de locais.
- A deteção de headings baseia-se em padrões tipográficos/textuais e pode promover algumas legendas em maiúsculas. Isto deve ser revisto na inspeção pré-chunking, sem alterar conteúdo.
- O UCTour contém informação que poderá mudar ao longo do tempo. A pipeline preserva a formulação do PDF raw, não valida a atualidade dos factos.
- O manifest não inclui URLs nem datas de aquisição porque não foram fornecidos e não foram inferidos.

## Decision

A pipeline é **suficientemente robusta para estes oito documentos** e foi aplicada a todos depois da aprovação do piloto. Preserva conteúdo substantivo, diacríticos, datas, nomes próprios, coordenadas e proveniência, enquanto torna explícitas as perdas deliberadas de ruído cartográfico/web e as páginas sem texto.

Esta decisão aprova apenas a representação intermédia PDF → Markdown. Não aprova ainda chunking nem qualquer componente RAG. Antes da próxima fase deve ser feita uma última revisão humana dos oito Markdown, com atenção especial à brochura longa e às limitações acima.
