# D1 + D2 Integration — Text Classification Routing

Data: 2026-09-29. Todos os números vêm de `uv run python integration/train_classifier.py`
(guardados em `integration/results/classifier_results.json`; reproduzíveis byte a byte).

## 1. Motivation

O enunciado sugere integrar os agentes de D1 e D2 num único sistema em que, "dependendo da
interação, um agente diferente é ativado (…) o agente rule-based trata chit-chat, o especialista
trata perguntas do domínio. Pode ser desenvolvido um text classifier para este fim."

- **ELIZA_RUDE (D1)** trata chit-chat: cumprimentos, sentimentos, problemas pessoais, família,
  trabalho, comentários dirigidos à própria agente.
- **Coimbra Tourism Expert RAG (D2)** trata perguntas de turismo em Coimbra.
- Um **text classifier** supervisionado (slides *Text Classification*: Naive Bayes vs Logistic
  Regression, avaliação com P/R/F1) decide o routing. **Não responde ao utilizador**; só escolhe
  o agente.

## 2. Classes

| Label | Agent | Meaning |
|---|---|---|
| `eliza_rude` | ELIZA_RUDE (D1, `d1_rule_based_v2/eliza_rude.py`) | chit-chat / conversa pessoal ou genérica, fora do domínio turístico |
| `rag` | D2 RAG (`d2_rag/scripts/rag_pipeline.py`, `BASELINE = FROZEN_V2`) | perguntas do domínio Coimbra Tourism Expert |

## 3. Dataset

`integration/data/routing_dataset.csv` (UTF-8, `text,label`), escrito à mão.

| | Valor |
|---|---|
| Total | 200 |
| `eliza_rude` | 100 |
| `rag` | 100 |
| Palavras por utterance | min 1, máx 13, média 6.45 |
| Tokens / tokens distintos | 1312 / 516 (type-token ratio 0.393) |
| Utterances `rag` com a palavra "Coimbra" | 17 / 100 |
| Utterances `eliza_rude` com a palavra "Coimbra" | 0 / 100 |

**Estratégia de construção.**
- `eliza_rude`: inspirado na cobertura real das regras da ELIZA_RUDE (cumprimentos, "estou…",
  "sou…", "sinto…", "preciso…", "quero…", "gosto…", "tenho…", "não consigo…", "porque…",
  mãe/pai/amigos/trabalho/chefe, desculpas, agradecimentos, "sim"/"não", perguntas à própria
  agente, computador/robô) mas com frases naturais, não cópias das regexes; e conversa
  genérica sem relação com turismo ("Quanto é dois mais dois?", "Achas que vai chover amanhã?").
- `rag`: perguntas naturais sobre Universidade, património, história, monumentos, museus,
  Fado/Canção de Coimbra, tradições académicas, gastronomia, doçaria, cervejarias, bares,
  cerâmica, desporto, jardins, roteiros e escritores; com e sem "Coimbra", com nomes próprios
  (Chanterene, João de Ruão, Santa Clara-a-Velha, Criptopórtico de Aeminium…), perguntas
  curtas ("Arco de Almedina", "Rainha Santa Isabel"), pedidos ("Fala-me…", "Sugere-me…") e
  perguntas longas. Não são as perguntas dos smoke tests de D2.

**Casos de fronteira (intencionais).**

| Utterance | Label | Porquê |
|---|---|---|
| Preciso de um restaurante em Coimbra. | rag | pedido de informação turística com padrão "Preciso de" da D1 |
| Preciso de férias. | eliza_rude | desabafo pessoal |
| Quero sair à noite em Coimbra. | rag | nightlife |
| Quero sair daqui. | eliza_rude | desabafo; contém "sair" |
| O meu trabalho está a correr mal. | eliza_rude | trabalho pessoal |
| Que trabalho realizou Nicolau Chanterene em Coimbra? | rag | "trabalho" artístico / património |
| Estou cansado de andar. | eliza_rude | estado pessoal |
| Onde posso fazer uma caminhada em Coimbra? | rag | atividade turística |
| **Quero comer.** | **eliza_rude** | **ambígua; decisão documentada abaixo** |
| Estou em Coimbra só um dia, o que devo visitar primeiro? | rag | começa por "Estou" (regra D1) |
| Consegues dizer-me onde fica a Sé Velha? / Podes recomendar-me um museu…? | rag | começam por "Consegues"/"Podes" (regras D1) |
| A minha mãe estudou na universidade e não se cala com isso. | eliza_rude | menciona "universidade" mas é sobre a família |
| O meu pai gosta de fado mas eu não suporto. | eliza_rude | menciona "fado" mas é opinião pessoal |
| Os meus amigos querem jantar fora e eu não tenho vontade nenhuma. | eliza_rude | menciona "jantar" mas é desabafo |

*Decisão sobre "Quero comer."*: `eliza_rude`. Exprime um desejo/estado pessoal sem pedido de
informação, sem lugar e sem referência ao domínio; um pedido turístico equivalente formula-se
como "Onde posso comer…?" / "Preciso de um restaurante…" (ambos `rag` no dataset). Como o
routing é por mensagem (sem contexto), a opção conservadora é a persona conversacional.

**Validação** (`validate_dataset`, falha com erro se algo não passar): sem texto vazio nem
espaços nas pontas; labels ∈ {`eliza_rude`, `rag`}; sem duplicados exatos; sem duplicados após
normalização (minúsculas, sem acentos, sem pontuação, espaços colapsados); classe maioritária
≤ 55%; leitura UTF-8 estrita. Resultado: 0 problemas.

## 4. Experimental Setup

- `train_test_split(test_size=0.3, random_state=42, stratify=y)` → treino 140 (70/70),
  teste 60 (30/30). Treino e teste disjuntos.
- O vectorizer é ajustado **apenas** no treino: `vectorizer.fit_transform(X_train)` em
  `train()`, e só `vectorizer.transform(X_test)` em `evaluate()`. Testado com mocks (o
  `fit_transform` é chamado uma vez, com `X_train`; qualquer `fit` durante a avaliação faz
  falhar o teste) e comparando o vocabulário com um vectorizer ajustado só em `X_train`.
- As duas experiências usam o **mesmo** split e o **mesmo** test set.
- O test set não foi alterado depois de ver os erros; nenhum exemplo foi movido para treino.
- Regra de seleção fixada no código **antes** de correr (`select_model`): ganha o maior macro
  F1, salvo se a diferença for menor que um exemplo de teste (1/60 = 0.017); nesse caso ganha o
  modelo com menor diferença entre os F1 das duas classes, e em empate total o baseline A
  (mais simples).
- Sem GridSearch nem tuning: configurações da worksheet.

## 5. Model A

`CountVectorizer(ngram_range=(1, 2), strip_accents="unicode")` + `MultinomialNB()` (α = 1,
Laplace smoothing, como nos slides). Restantes parâmetros por omissão (lowercase).

## 6. Model B

`TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode")` +
`LogisticRegression(max_iter=1000, random_state=42)` (L2, C = 1, lbfgs, por omissão).

## 7. Results

Test set: 60 utterances (30 `eliza_rude`, 30 `rag`).

| Model | Accuracy | Macro Precision | Macro Recall | Macro F1 |
|---|---|---|---|---|
| A: Count + MultinomialNB | 0.917 | 0.921 | 0.917 | 0.916 |
| B: TF-IDF + LogisticRegression | **0.950** | **0.951** | **0.950** | **0.950** |

**Model A — classification report**

```
              precision    recall  f1-score   support

  eliza_rude      0.963     0.867     0.912        30
         rag      0.879     0.967     0.921        30

    accuracy                          0.917        60
   macro avg      0.921     0.917     0.916        60
weighted avg      0.921     0.917     0.916        60
```

**Model B — classification report**

```
              precision    recall  f1-score   support

  eliza_rude      0.966     0.933     0.949        30
         rag      0.935     0.967     0.951        30

    accuracy                          0.950        60
   macro avg      0.951     0.950     0.950        60
weighted avg      0.951     0.950     0.950        60
```

**Confusion matrices** (linhas = classe real, colunas = prevista)

| A | pred `eliza_rude` | pred `rag` |
|---|---|---|
| true `eliza_rude` | 26 | 4 |
| true `rag` | 1 | 29 |

| B | pred `eliza_rude` | pred `rag` |
|---|---|---|
| true `eliza_rude` | 28 | 2 |
| true `rag` | 1 | 29 |

## 8. Error Analysis

Todos os erros do test set (probabilidades `eliza_rude` / `rag` do próprio modelo):

| Utterance | True | A pred (P) | B pred (P) |
|---|---|---|---|
| Bom dia! | eliza_rude | **rag** (0.28 / 0.72) | **rag** (0.48 / 0.52) |
| Quero sair à noite em Coimbra. | rag | **eliza_rude** (0.60 / 0.40) | **eliza_rude** (0.53 / 0.47) |
| Adoro dias de sol. | eliza_rude | **rag** (0.36 / 0.64) | **rag** (0.40 / 0.60) |
| Quanto é dois mais dois? | eliza_rude | **rag** (0.49 / 0.51) | ok |
| Os exames estão a dar cabo de mim. | eliza_rude | **rag** (0.47 / 0.53) | ok |

Contribuições das features no Model B (coeficiente × TF-IDF; positivo = `rag`), verificadas no
modelo persistido:

- **Mensagens muito curtas / vocabulário não visto** — "Bom dia!": `bom` nunca aparece no
  treino; a única feature conhecida é `dia` (+0.17), que vem de perguntas RAG ("só um dia",
  "num dia de chuva"). "Adoro dias de sol.": `adoro`, `dias`, `sol` desconhecidas; só resta `de`
  (+0.50). Sem sinal lexical, a decisão cai para palavras funcionais.
- **Palavras presentes nas regras da ELIZA_RUDE** — "Quero sair à noite em Coimbra.": `quero`
  (−0.20), `quero sair`, `sair` e `noite` (vêm de "Quero sair daqui." e "Boa noite, ainda estás
  acordada?") superam `coimbra` (+0.22) e `em coimbra` (+0.11). Este é precisamente um dos
  casos de fronteira desenhados; mostra que o classificador **não** se limita a detetar
  "Coimbra" — mas também que "Quero…" puxa fortemente para D1.
- **Perguntas genéricas em forma interrogativa** (só A) — "Quanto é dois mais dois?": o NB
  associa a forma de pergunta à classe `rag`. Margem mínima (0.49/0.51).
- **Palavras funcionais** (só A) — "Os exames estão a dar cabo de mim.": `de`, `a` são mais
  frequentes em `rag`.

Observação geral: entre as features mais fortes para `rag` estão palavras funcionais (`de`,
`da`, `do`, `que`, `onde`, `na`, `ao`) além de conteúdo (`coimbra`, `visitar`, `cidade`); para
`eliza_rude`, marcadores pessoais (`meu`, `minha`, `me`, `estou`, `sinto`, `quero`, `não`,
`olá`). O modelo aprendeu em parte o *estilo* (pergunta informativa vs. frase pessoal).

## 9. Selected Router

**Model B — TF-IDF + LogisticRegression.** Macro F1 0.950 vs 0.916 (+0.034, i.e. 2 exemplos
de teste, acima da margem de 1 exemplo fixada antes). É também o mais equilibrado: F1 por classe
0.949 / 0.951 (A: 0.912 / 0.921), e reduz os falsos `rag` de 4 para 2 mantendo 1 falso
`eliza_rude`. A diferença é pequena em termos absolutos (60 exemplos de teste), mas está na
direção de todos os critérios (accuracy, macro F1, equilíbrio, confusion matrix). Além disso a
LR é discriminativa (modela P(c|d) diretamente, como nos slides) e dá probabilidades menos
extremas que o NB, úteis para o modo de debug.

O modelo final é reajustado com o mesmo split de treino (140) — exatamente o modelo avaliado —
e persistido:

- `integration/models/router_vectorizer.joblib` (24.5 KB; vocabulário de 1052 n-gramas)
- `integration/models/router_classifier.joblib` (9.3 KB)

São pequenos e versionados; regeneram-se deterministicamente com
`uv run python integration/train_classifier.py` (um teste verifica que um novo treino produz
exatamente os resultados guardados e as mesmas probabilidades do modelo persistido).
Num retreino, `classifier_results.json` e `router_classifier.joblib` saem byte-idênticos; o
`router_vectorizer.joblib` difere só no atributo interno do sklearn `_stop_words_id` (o `id()`
em memória de um objeto, usado como cache), com vocabulário, ordem e `idf_` idênticos.
scikit-learn 1.9.1 (fixado no `uv.lock`).

## 10. Integrated Architecture

```
                        User
                         ↓
               integration/integrated_agent.py
                         ↓
           "sair"? ── sim ──→ termina (antes do classifier)
                         ↓ não
        Text Classifier (AgentRouter: TF-IDF + LogReg, argmax)
                ↙                          ↘
        ELIZA_RUDE                          RAG
           D1                                D2
  eliza_rude.respond(text)     retrieve → build_messages → generate
  (d1_rule_based_v2,           (rag_pipeline, BASELINE = FROZEN_V2:
   regras inalteradas)          Qwen3-Embedding-0.6B, chroma_frozen_v2,
                                top_k=3, llama3.2:3b, T=0.1)
                ↘                          ↙
                       Resposta
```

- **Startup (uma vez):** `AgentRouter.load()` (joblib), `ElizaRudeAgent()` (a instância NLTK
  `Chat` existente), `RAGAgent.load()` → `check_ollama`, `load_embeddings`, `open_store` (store
  existente; nunca `build_store`).
- **ELIZA_RUDE:** só `respond()`; nunca `converse()` (o loop pertence ao sistema integrado).
  `ElizaRudeAgent` aplica a mesma preparação que o `converse()` do NLTK faz em D1 (remove
  `!` e `.` finais), para que as respostas sejam as mesmas que em D1.
- **RAG:** `RAGAgent.respond()` reutiliza `retrieve`, `build_messages`, `generate` e
  `format_sources` do `rag_pipeline`; nenhum código RAG duplicado e nenhuma configuração nova.
- **"sair":** `text.strip().lower() == "sair"` termina antes do classifier, por isso nunca chega à
  regra `sair` da ELIZA_RUDE; "Onde posso sair à noite em Coimbra?" não termina.
- **Routing:** cada mensagem é classificada isoladamente; argmax, sem threshold.
- `--debug-routing` mostra `[router] eliza_rude=… rag=… selected=…` antes de cada resposta.

## 11. Routing Examples

**Frases novas** (nenhuma está no dataset, verificado após normalização; são casos de
`test_router.py`):

| Input | P(eliza_rude) | P(rag) | Classe | Agente |
|---|---|---|---|---|
| Quais são os monumentos mais importantes de Coimbra? | 0.30 | 0.70 | rag | D2 RAG |
| A Universidade de Coimbra tem visitas guiadas? | 0.31 | 0.69 | rag | D2 RAG |
| Quais são os bares mais animados perto da Praça da República? | 0.30 | 0.70 | rag | D2 RAG |
| Em que século foi construída a Sé Velha? | 0.36 | 0.64 | rag | D2 RAG |
| Onde é que posso assistir a um espetáculo de fado esta noite? | 0.41 | 0.59 | rag | D2 RAG |
| Conheces um restaurante com leitão perto do centro? | 0.42 | 0.58 | rag | D2 RAG |
| Preciso de um sítio para jantar perto da Sé Velha. | 0.37 | 0.63 | rag | D2 RAG |
| Onde se pode sair à noite na Baixa? | 0.40 | 0.60 | rag | D2 RAG |
| Olá, boa tarde. | 0.61 | 0.39 | eliza_rude | D1 ELIZA_RUDE |
| Hoje sinto-me mesmo em baixo. | 0.66 | 0.34 | eliza_rude | D1 ELIZA_RUDE |
| O meu chefe obriga-me a fazer horas extra. | 0.66 | 0.34 | eliza_rude | D1 ELIZA_RUDE |
| A minha família não me apoia. | 0.67 | 0.33 | eliza_rude | D1 ELIZA_RUDE |
| Tu és a assistente mais mal-educada que conheço. | 0.65 | 0.35 | eliza_rude | D1 ELIZA_RUDE |
| Preciso de uma pausa. | 0.59 | 0.41 | eliza_rude | D1 ELIZA_RUDE |
| Quero ir para casa. | 0.55 | 0.45 | eliza_rude | D1 ELIZA_RUDE |
| Obrigadíssimo, foste útil. | 0.52 | 0.48 | eliza_rude | D1 ELIZA_RUDE |

As 21 frases novas de `test_router.py` são todas encaminhadas corretamente.

**Execução real do sistema integrado** (`--debug-routing`, router + ELIZA_RUDE + Qwen3
embeddings + Ollama llama3.2:3b reais; a store usada foi uma **cópia** de `chroma_frozen_v2` —
ver §13). Excerto (entre parênteses retos: se a frase está no treino, no teste ou é nova):

```
Tu: Olá!                                   [treino]
[router] eliza_rude=0.64 rag=0.36 selected=eliza_rude
Agente: Olá. Despacha-te, que tenho mais que fazer.

Tu: O meu chefe irrita-me.                 [treino]
[router] eliza_rude=0.67 rag=0.33 selected=eliza_rude
Agente: Queixas do trabalho? Que original.

Tu: Onde posso sair à noite em Coimbra?    [nova]
[router] eliza_rude=0.39 rag=0.61 selected=rag
Agente: (…) Bares e clubes no Centro Histórico, como BIXOS (…) Docas do Parque Verde.
Fontes:
- Coimbra By Night [web-visitecoimbra-coimbra-by-night] — (…)

Tu: Estou cansado.                         [nova]
[router] eliza_rude=0.62 rag=0.38 selected=eliza_rude
Agente: Toda a gente está cansado de vez em quando. Supera.

Tu: Conta-me a história da Biblioteca Joanina.   [teste]
[router] eliza_rude=0.43 rag=0.57 selected=rag
Agente: A história da Biblioteca Joanina começa com a sua construção, que ficou concluída em 1728 (…)
Fontes:
- Biblioteca Joanina [biblioteca-joanina-uctour] — Biblioteca Joanina — páginas 2 (…)

Tu: Quero comer.                           [treino]
[router] eliza_rude=0.65 rag=0.35 selected=eliza_rude
Agente: Querer não custa. Fazer é que é outra conversa.

Tu: sair
(termina; o input seguinte nunca é lido)
```

Isto é um smoke test de integração (os pedidos chegam ao agente certo e cada agente responde);
**não** é uma avaliação da qualidade das respostas RAG.

## 12. Tests

`uv run python -m unittest discover -s integration/tests` → **57 testes, OK** (< 1 s; sem
Ollama, sem modelo de embeddings, sem Chroma).

| Ficheiro | Cobre |
|---|---|
| `test_routing_dataset.py` (15) | tamanho 200, labels válidas, 100/100, sem duplicados exatos nem normalizados, UTF-8 estrito/NFC/sem caracteres de controlo, estatísticas de diversidade, `rag` não depende só de "Coimbra", casos de fronteira documentados; a validação rejeita dataset vazio, label inválida, texto vazio, duplicados, desequilíbrio |
| `test_train_classifier.py` (16) | split 70/30 reproduzível, estratificado e disjunto; vectorizer ajustado só no treino (mock + vocabulário); configurações A/B; ambos treinam e preveem as duas classes; métricas e confusion matrix coerentes; regra de seleção; persistência/load; `run()` determinístico; resultados guardados = novo treino |
| `test_router.py` (11) | modelo final é TF-IDF+LR; 9 casos RAG (monumentos, museu, universidade, fado, restaurante, nightlife, desporto, história, património), 7 ELIZA_RUDE (cumprimento, sentimento, problema pessoal, trabalho, família, agradecimento, comentário à agente), 5 de fronteira, todos novos; `predict_proba` é distribuição; `classify` = argmax; artefactos carregados uma só vez; erros claros |
| `test_integrated_agent.py` (15) | rota `eliza_rude` chama só a ELIZA_RUDE; rota `rag` chama só o RAG; "sair" não chama classifier nem agentes; "sair" dentro de frase não termina; input vazio/EOF; debug só com `--debug-routing`; ELIZA_RUDE usa `respond` (nunca `converse`) com as regras reais; RAG reutiliza `retrieve`/`build_messages`/`generate` com `BASELINE`=`FROZEN_V2` e abre a store sem a reconstruir; startup carrega cada componente uma vez |

Suite de D2 inalterada: `uv run python -m unittest discover -s d2_rag/tests` → 123 OK.

## 13. Limitations

- **Dataset pequeno e manual** (200 frases, escritas por uma pessoa); o test set tem 60 frases,
  por isso cada erro vale 1.7 pontos percentuais e a diferença A vs B (2 frases) tem pouca
  significância estatística.
- **Apenas duas classes.** Perguntas fora de ambos os domínios (ex.: "Qual é a capital de
  França?") vão para uma das duas; não há classe "fora do domínio" nem threshold.
- **Probabilidades pouco confiantes.** Com TF-IDF, C=1 e 140 exemplos, a LR raramente passa
  de 0.70; várias decisões corretas têm margens pequenas (ex.: "Obrigadíssimo, foste útil."
  0.52/0.48). Não afeta o argmax, mas não se deve interpretar a probabilidade como confiança
  calibrada.
- **Classificador lexical.** Frases com vocabulário não visto ("Bom dia!", "Adoro dias de
  sol.") decidem-se por palavras funcionais; formulações muito diferentes do dataset podem
  falhar. Os marcadores das regras D1 ("Quero…", "sair") podem vencer o contexto turístico.
- **"Coimbra" só aparece em exemplos `rag`** (17/100; 0 em `eliza_rude`), logo uma frase
  pessoal com "Coimbra" ("Estou farto de Coimbra") tende a ir para o RAG.
- **Sem contexto de turnos anteriores**: cada mensagem é classificada isoladamente ("E a Sé
  Nova?" depois de uma pergunta sobre a Sé Velha não herda a rota).
- **Abrir a Chroma reescreve bytes da store.** Verificado numa cópia: abrir e consultar
  `chroma_frozen_v2` reescreve `chroma.sqlite3`, `data_level0.bin` e `length.bin` (o conteúdo
  lógico mantém-se: 348 chunks, mesmos resultados). É comportamento do Chroma e já acontece
  com o `rag_baseline.py` existente; qualquer execução real do sistema integrado (ou de D2) o
  fará. Por isso a execução de §11 usou uma cópia e a store no disco ficou byte-idêntica.

## 14. Decision

**IS THE CLASSIFIER SUITABLE FOR ROUTING D1/D2?** **YES** — accuracy 0.950 e macro F1 0.950 no
test set, equilibrado entre classes (F1 0.949 / 0.951), 21/21 frases novas corretas e erros
explicáveis, com as limitações da §13.

**IS THE INTEGRATED AGENT READY FOR DEMONSTRATION?** **YES** — `integration/integrated_agent.py`
arranca os três componentes uma vez, encaminha corretamente em execução real (Ollama +
embeddings + store), trata "sair" antes do classifier e tem modo `--debug-routing`.

Esta tarefa não alterou nem executou a avaliação obrigatória de D2 **RAG vs No-RAG**
(`d2_rag/D2_ANSWER_QUALITY_EVALUATION_SET.md` inalterado): o classifier mede routing, não
qualidade de respostas.
