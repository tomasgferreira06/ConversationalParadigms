# Preprocessing Corrective Pass

## Scope

Correção estrita dos problemas **C1, M1, M2, M3 e m1** identificados em
`PRE_CHUNKING_AUDIT.md`, que é preservado sem alterações como evidência do estado
anterior.

Fora do âmbito, e não tratados:
- M4 e M5;
- MINOR m2–m8;
- chunking, embeddings, Vector DB, retrieval e LLM.

Todas as correções são determinísticas, sem LLM e sem chamadas externas. Estão
configuradas por documento em `DOCUMENT_CONFIG` e fundamentadas em medições
feitas nos próprios PDFs. Não introduzem nem reescrevem texto da fonte.

## Changes

Todas as alterações estão em `d2_rag/scripts/preprocess_documents.py`.

### C1 — Letras espaçadas (`fado-e-tradicoes-academicas`)

**Causa confirmada:** o PDF contém glifos de espaço reais entre letras. Foi medida
a largura de todos os glifos de espaço do documento (largura / tamanho da fonte),
por fonte:

| Fonte | Classe | Largura (em) | Ocorrências | Função |
|---|---|---|---:|---|
| Montserrat-Light (corpo) | A | 0.15–0.19 | 381 | espaçamento entre letras |
| | B | 0.27 | 2306 | espaço normal entre palavras |
| | C | 0.30 | 10 | espaçamento entre letras, só em "da Loucura e Jástá" |
| | D | 0.42 | 33 | espaço entre palavras em nomes de repúblicas com tracking |
| Montserrat-Black-SC700 (rótulos) | — | — | — | small caps: minúsculas em spans reduzidas (4.9–6.0 pt), uma palavra por span; espaços entre palavras em spans próprias de 7.0–7.4 pt |

O contexto de cada glifo das classes C e D foi verificado individualmente.

Um threshold global não é seguro: nos rótulos SC700, os espaços entre palavras
(0.21 em) são mais estreitos do que alguns espaços entre letras (até 0.235 em),
e na classe D os espaços entre palavras (0.42) são mais largos do que os espaços
normais (0.27).

**Regra (só para este documento):**
- O texto é reconstruído a partir dos glifos (`rawdict`) em vez de
  `get_text("blocks")`. Sem filtro, a reconstrução é idêntica a
  `get_text("blocks")` nas duas páginas, o que foi verificado.
- Em Montserrat-Light, descartam-se os espaços nas bandas `[0, 0.23)` e
  `[0.29, 0.33)`, ou seja, as classes A e C. Mantêm-se as classes B e D.
- Em Montserrat-Black-SC700, descartam-se os espaços dentro de spans com menos de
  6.5 pt.

Configuração: `letter_spacing_fonts` e `letter_spacing_small_caps`.

### M1 — Falsos headings de mapa (`universidade-alta-sofia-patrimonio-mundial`)

- Nova opção `map_pages = {34, 35, 40, 41}`.
- Nessas páginas, só se mantêm os blocos horizontais com pelo menos 120
  caracteres (`MAP_EDITORIAL_MIN_CHARS`). É o mesmo limiar que a pipeline já usa
  para encontrar o texto editorial nos mapas dos roteiros.
- Medições nas páginas:
  - p34 (92 blocos) e p35 (46 blocos) são só labels, com no máximo 57 caracteres;
  - p41 tem apenas "OCEANO / ATLÂNTICO";
  - p40 tem um bloco editorial de 1625 caracteres, que é mantido, e o label "A8".
- Estas páginas passam a emitir o warning
  `Map labels omitted; editorial text blocks retained.`

### M2 / M3 — Painel de legendas a meio de uma frase (`coimbra-para-os-pequenitos`, `fundacao-da-nacionalidade`)

**Causa (verificada na geometria dos blocos):** o painel de fotografias ocupa o
**fundo de uma coluna**, abaixo do fim do texto dessa coluna, enquanto a última
frase continua no **topo da coluna seguinte**. A leitura "coluna completa →
coluna seguinte" colocava o painel entre as duas metades da frase.

**Regra comum (opção `caption_panel_to_page_end`, ativa só nestes dois
documentos):**
1. A âncora é o bloco de marcadores (`a. b. c. …`, regex
   `(?:[a-z]\.\s*){2,}`).
2. O painel começa no título decorativo do painel, o bloco ≥ 14 pt mais próximo
   acima da âncora na mesma coluna (CinzelDecorative-Bold 20 pt nos dois PDFs;
   o corpo usa 7–7.2 pt).
3. Os blocos dessa coluna desde o título são retirados do fluxo principal e
   emitidos **depois do texto da página**, após o marcador
   `<!-- caption_panel -->`. Não são promovidos a headings e o texto das
   legendas é preservado sem alterações.
4. Só nessa coluna: se o último bloco de texto termina sem pontuação final,
   junta-se ao primeiro bloco da coluna seguinte, restaurando a frase
   interrompida. Isto não aplica a correção genérica de m2 a outras quebras de
   coluna.

Não há nenhuma referência textual a "Gonçalo Byrne" ou a "mais antigo museu" no
código.

### m1 — Hífen enclítico (`fundacao-da-nacionalidade`)

- Em `reconstruct_paragraphs`, a quebra de linha `…-` + `se …` mantém o hífen
  quando o fragmento anterior termina em vogal, `r`, `m` ou `z` (por exemplo
  `destaca-se`, `encontrar-se`).
- Depois de consoante, `se` é hifenização normal (`dis-se` → `disse`) e continua
  a ser junto.
- O conjunto de clíticos é mínimo: apenas `se` (`KEPT_HYPHEN_ENCLITICS`).
- Em todo o corpus existem só duas quebras de linha com hífen seguidas de
  minúscula (`destaca-|se` e `deposita-|da`); ambas ficam corretas.

### Alteração de suporte

`render_document()` foi extraída de `process_document()`. Faz o render validado
em memória, sem escrever. Não muda comportamento: foi confirmado que todos os
outputs não afetados continuam byte a byte iguais. É usada pelos testes e pelo
dry-run.

## Regression Tests

Novo ficheiro: `d2_rag/tests/test_preprocess_regressions.py` (15 testes).

| Classe | Cobre | Verifica |
|---|---|---|
| `C1LetterSpacingTests` (5) | C1 | Ausência de `E s t a b e l e c i d a`, `1 5 9 3`, `2 0 0 3`, `1 9 4 8` e presença de `Estabelecida`, `1593`, `2003`, `1948`. Nenhuma sequência de 6 tokens de um carácter. Frases com limites de palavra corretos. Texto que já estava correto fica inalterado. Diacríticos (`Conímbriga`, `Æminium`…). `**Coordenadas:** 40.207449, -8.429593` e a sequência completa de coordenadas igual à do PDF. |
| `M1MapPageTests` (4) | M1 | 8 falsos headings ausentes. Páginas 34, 35 e 41 vazias. Texto UNESCO da p40 presente e "A8" ausente. Headings `## 1.`–`## 31.` todos presentes e por ordem, mais subsecções e texto das p38–39. |
| `CaptionPanelTests` (2) | M2, M3 | "…modelos que constitui o mais antigo museu de Portugal…" contínuo. "…arquiteto Gonçalo Byrne. Com esta recente requalificação…" contínuo. Painel depois da última secção da página e conteúdo das legendas preservado. |
| `M1EncliticHyphenTests` (3) | m1 | `destaca-se` e `encontrar-se` mantêm o hífen. `deposita-|do` → `depositado` e `dis-|se` → `disse`. No output: `destaca-se` presente e `destacase` ausente. |
| `ConsistencyTests` (1) | todos | Cada um dos 8 Markdown em disco é exatamente igual a um render fresco a partir do PDF raw. |

**Os testes falharam antes da correção:** foram executados sobre os outputs antigos
antes de alterar a pipeline e deram **23 falhas** nas classes C1, M1, M2, M3 e m1.
O `ConsistencyTests` passou, o que confirma que a extração de `render_document`
não mudou comportamento.

**Depois da correção, a suite completa passa: 33 testes, OK.**
- 11 testes pré-existentes de preprocessing, sem alterações;
- 7 testes pré-existentes do smoke test, sem alterações;
- 15 testes novos.

## Documents Regenerated

Apenas:

1. `fado-e-tradicoes-academicas`
2. `universidade-alta-sofia-patrimonio-mundial`
3. `coimbra-para-os-pequenitos`
4. `fundacao-da-nacionalidade`

```bash
uv run python d2_rag/scripts/preprocess_documents.py --documents \
  fado-e-tradicoes-academicas universidade-alta-sofia-patrimonio-mundial \
  coimbra-para-os-pequenitos fundacao-da-nacionalidade
```

## Before / After Examples

**C1**
```text
p r i s ã o a c a d é m i c a - E s t a b e l e c i d a , e m 1 5 9 3 , n a a l a n o r t e d o edifício
→ prisão académica - Estabelecida, em 1593, na ala norte do edifício

d e s d e 1 6 d e j u l h o d e 2 0 0 3 , p o r d e c r e t o d o C o n s e l h o d e R e p …
→ desde 16 de julho de 2003, por decreto do Conselho de Repúblicas

a 1 1 d e D eze m b r o d e 1 9 4 8
→ a 11 de Dezembro de 1948

O ex t e r i o r é r o b u s t o , s i m é t r i co , co m e s ca s s a s a b e r t u ra s
→ O exterior é robusto, simétrico, com escassas aberturas

Palácio d a L o u c u ra e J á s t á
→ Palácio da Loucura e Jástá

c o o r d e n a das: 40.207449, -8.429593
→ **Coordenadas:** 40.207449, -8.429593
```

**M1** (UC, p34–35, p40–41)
```text
### IGREJA DE SANTA / ### JUSTA / ### USEU DA / ### ÊNCIA / ### AGA / ### LINHA 103 / ### OCEANO ATLÂNTICO …
(100 falsos headings; p34: 69, p35: 30, p41: 1)
→ páginas 34, 35 e 41 com marcador e sem texto; p40 mantém apenas o texto UNESCO
```
Os headings do documento passaram de 148 para 48.

**M2 / M3**
```text
…de rochas e de modelos que constitui o
Portugal dos pequenitos / “Tudo é minúsculo…” / pavilhão da guiné-bissau … / a. b. c. d. e. f. g. h.
mais antigo museu de Portugal que se mantém no seu espaço de origem.
→ …de rochas e de modelos que constitui o mais antigo museu de Portugal que se mantém no seu espaço de origem.
  (painel preservado no fim da página 1, depois de <!-- caption_panel -->)

…com projeto do arquiteto Gonçalo
fundação da nacionalidade / igreja de santa cruz | … / a. b. c. d.
Byrne. Com esta recente requalificação…
→ …com projeto do arquiteto Gonçalo Byrne. Com esta recente requalificação…
```

**m1**
```text
destacase Fernando de Bulhões → destaca-se Fernando de Bulhões
```

## Integrity Checks

| Verificação | Resultado |
|---|---|
| SHA-256 dos 8 PDFs raw, antes e depois | **8/8 iguais** (e iguais a `content_hash` no manifest) |
| SHA-256 dos 4 Markdown não afetados (`escritores`, `jardins`, `joanina`, `viver`), antes e depois | **4/4 byte a byte iguais** |
| Dry-run dos 8 documentos antes de escrever | só os 4 alvo diferem |
| Idempotência: duas execuções da regeneração | SHA-256 idênticos |
| Dry-run vs ficheiro regenerado | idênticos |
| C1: sequência de caracteres sem whitespace, fado antigo vs novo | **idêntica** (só a linha de coordenadas muda de markup); 454 espaços removidos |
| C1: palavras novas sem ocorrência no resto do corpus | 7, todas válidas: apresentaram, constituíram, estadista, jástá, loucura, publicamente, reunido |
| M1: páginas alteradas na UC | apenas 34, 35, 40 e 41 |
| M2/M3: diferenças | só mudança de posição do painel e junção da frase; texto das legendas inalterado |
| 8 raw / 8 MD / manifest paths coerentes / não vazios / UTF-8 / sem U+FFFD | OK |
| Marcadores `source_page` completos e por ordem | OK nos 8 |
| Coordenadas: sequência MD = sequência PDF | OK nos 8 |
| Anos (PDF vs MD) | OK nos 8, exceto `biblioteca-joanina-uctour` (1777 da p1 duplicada e 2026 do conteúdo comercial), documento não alterado e limitação A8 anterior |
| D1 | não alterado |

## Remaining Known Issues

Não tratados nesta passagem, por decisão de âmbito:

- **M4:** unidades de baixa informação (páginas só com legendas e números de
  página impressos na UC). Resolvido de forma natural apenas o número "38" da
  página 40, que caiu com a regra de mapa.
- **M5:** duplicação entre documentos.
- **m2:** outras frases partidas por quebra de coluna, por exemplo fundação §7
  "reproduções | à escala", pequenitos §4, jardins, fado §7 e UC §5. Só foi
  corrigida a quebra onde o painel de legendas estava.
- **m3–m8:** como em `PRE_CHUNKING_AUDIT.md`.

**Considerações novas para o chunking (não são regressões):**
- O painel de legendas fica no fim da página 1, depois da última secção do
  roteiro (pequenitos §6, fundação §9), delimitado por `<!-- caption_panel -->`.
  O chunking deve tratar este marcador como fronteira, para não anexar as
  legendas à última secção.
- A regra de m1 pode, em documentos futuros, manter o hífen num substantivo em
  `-se` partido depois de uma vogal (por exemplo `análi-|se`). No corpus atual
  não existe nenhum caso destes.
