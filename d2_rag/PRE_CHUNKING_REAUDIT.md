# Pre-Chunking Re-Audit

Auditoria dirigida depois da passagem corretiva descrita em
`PREPROCESSING_FIX_REPORT.md`. Verifica só os problemas bloqueantes identificados
em `PRE_CHUNKING_AUDIT.md` (C1, M1, M2, M3, m1), mais os checks globais de
regressão. Não repete a investigação exploratória original.

## Resultado por problema

| ID | Resolvido? | Evidência |
|---|---|---|
| **C1** | **YES** | Zero sequências de ≥4 tokens de um carácter no documento (antes: 14/33 parágrafos). `1593`, `2003`, `1948` (e `1913`, `1175`, `1933`) recuperados. `**Coordenadas:** 40.207449, -8.429593`; a sequência das 20 coordenadas é igual à do PDF. A sequência de caracteres sem whitespace é idêntica à anterior, por isso só foram removidos espaços. As 7 palavras novas no corpus são válidas. Rótulos SC700 corrigidos (`prisão académica`, `sala dos capelos`, `monumento à música`). |
| **M1** | **YES** | Páginas 34, 35 e 41 sem texto e sem headings (antes: 69 + 30 + 1 falsos headings). A página 40 mantém só o texto editorial UNESCO. Headings do documento: 148 → 48. `## 1.`–`## 31.` todos presentes e por ordem; subsecções `###` reais preservadas. Nenhuma página fora de 34/35/40/41 foi alterada. |
| **M2** | **YES** | "…de rochas e de modelos que constitui o mais antigo museu de Portugal que se mantém no seu espaço de origem." aparece num único parágrafo. O painel (título, citação de Bissaya Barreto, legendas, `a.`–`h.`) está depois de `<!-- caption_panel -->`, no fim da página 1, com o texto preservado. |
| **M3** | **YES** | "…com projeto do arquiteto Gonçalo Byrne. Com esta recente requalificação arquitetónica…" aparece num único parágrafo, sem nada entre "Gonçalo" e "Byrne". O conteúdo seguinte (§8 até "Cabrita Reis", §9) está presente. O painel foi movido para o fim da página. |
| **m1** | **YES** | `destaca-se Fernando de Bulhões` presente e `destacase` ausente. A hifenização normal continua a ser unida (`depositada` inalterado; teste `dis-|se` → `disse`). |

## Checks globais de regressão

| Check | Resultado |
|---|---|
| 8 PDFs raw, SHA-256 antes = depois = manifest | ✓ |
| 8 Markdown, não vazios, UTF-8, sem U+FFFD | ✓ |
| Marcadores `source_page` completos (1..N) e por ordem | ✓ nos 8 |
| Paths do manifest coerentes | ✓ |
| Coordenadas: sequência MD = sequência PDF | ✓ nos 8 |
| Anos preservados | ✓ (única diferença: `biblioteca-joanina-uctour`, não alterado, limitação A8 anterior) |
| 4 Markdown não afetados byte a byte iguais | ✓ |
| Idempotência (2 execuções) | ✓ |
| Fidelidade por página nos 4 regenerados: palavras ausentes do PDF | nenhuma (só `caption`/`panel`, do marcador HTML) |
| Fidelidade por página: palavras deslocadas para outra página | nenhuma |
| Suite de testes | 33/33 OK |

## Regressões introduzidas

Não foi encontrada nenhuma regressão **CRITICAL** nem **MAJOR**.

Observações novas, de severidade MINOR, a considerar no chunking:
- As legendas movidas ficam no fim da página 1, depois da última secção do
  roteiro, delimitadas por `<!-- caption_panel -->`.
- A regra m1 tem uma ambiguidade teórica (`análi-|se`) sem nenhuma ocorrência no
  corpus.

## Problemas conhecidos restantes (não bloqueantes)

- **M4:** unidades de baixa informação (legendas e números de página na UC).
  Tratar no chunking.
- **M5:** duplicação entre documentos. Tratar no chunking/retrieval.
- **m2–m8:** MINOR, conforme `PRE_CHUNKING_AUDIT.md`.
- Riscos de chunking da §6 do audit original: associação heading–conteúdo,
  secções que atravessam páginas e linhas de coordenadas.

## Decisão

# READY FOR CHUNKING

C1, M1, M2, M3 e m1 estão resolvidos e não foi introduzida nenhuma regressão
CRITICAL ou MAJOR. M4 e M5 ficam para a fase de chunking/retrieval, conforme
definido no audit original.

Esta decisão **não** autoriza a implementação do chunking. Essa fase aguarda
autorização explícita.
