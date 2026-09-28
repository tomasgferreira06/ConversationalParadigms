# D2 — RAG vs No-RAG Answer Quality Evaluation Set

Data: 2026-09-28. Estado: **conjunto congelado antes de qualquer execução.**

## 1. Purpose

Requisito da D2: *"Quantitative comparison of answer quality with and without RAG is required."*

Este documento define, **antes** de qualquer execução, as 20 perguntas com que vai ser
comparada a qualidade das respostas em duas condições: com RAG e sem RAG.

- **Mesmo LLM** (`llama3.2:3b`) e **mesmas 20 perguntas** nas duas condições; só muda a
  existência de contexto recuperado.
- **Uma única métrica**: Answer Quality Score (0–2), atribuída a cada resposta com base nos
  factos essenciais definidos aqui.
- As perguntas, as respostas esperadas e os factos essenciais foram escritos a partir da
  leitura integral dos 35 documentos processados do corpus congelado (`data/processed/`,
  8 PDF + 27 Web). Os relatórios de desenvolvimento não foram usados como fonte factual, apenas
  para identificar as perguntas já usadas em smoke tests.
- Não é uma avaliação da D3: não há métricas de retrieval, RAGAS nem LLM-as-Judge.

## 2. Evaluation Protocol

Condições futuras. **Nada disto foi executado nesta tarefa.**

| Condição | Pipeline |
|---|---|
| NO-RAG | pergunta → `llama3.2:3b` → resposta |
| RAG | pergunta → retrieval final (top-3) → `llama3.2:3b` → resposta |

Cada pergunta é feita de forma independente, sem histórico de conversa. Cada resposta recebe um
Answer Quality Score segundo a escala da secção 3, usando a resposta esperada e os factos
essenciais de cada pergunta como referência.

## 3. Answer Quality Score

Escala congelada, com uma única dimensão:

| Score | Label | Definição |
|---|---|---|
| **2** | **Correct** | A resposta está factualmente correta e responde adequadamente à pergunta. Contém os elementos essenciais necessários e não apresenta erros relevantes. |
| **1** | **Partially correct** | A resposta contém informação relevante e correta, mas está incompleta ou contém uma pequena imprecisão que não destrói a ideia principal. |
| **0** | **Incorrect** | A resposta está errada, contradiz os factos essenciais, inventa informação relevante ou não responde efetivamente à pergunta. |

Os "Essential facts" e a "Score guidance" de cada pergunta servem apenas para aplicar esta escala
de forma consistente; não são uma segunda métrica.

## 4. Corpus Coverage Used

Áreas encontradas na leitura dos 35 Markdown e documentos usados como suporte:

| Area | Documents used | Main knowledge available |
|---|---|---|
| História da cidade e fundação do reino | `fundacao-da-nacionalidade` (PDF), `web-visitecoimbra-coimbra-muralhada`, `web-visitecoimbra-heranca-judaica` | Æminium e Conímbriga, muralha, capital em 1131, D. Sesnando, judiaria, herança moçárabe |
| Lendas e figuras históricas | `web-visitecoimbra-o-brasao-da-cidade-de-coimbra`, `web-visitecoimbra-princesa-cindazunda` | brasão e lenda de Cindazunda; no corpus há também Rainha Santa, Pedro e Inês, Camões, Santo António e D. Afonso Henriques |
| Universidade e Paço das Escolas | `universidade-alta-sofia-patrimonio-mundial` (PDF), `fado-e-tradicoes-academicas` (PDF), `viver-o-patrimonio-em-coimbra` (PDF) | Torre e sinos, Via Latina, Sala dos Capelos, colégios da Sofia, edifícios do Estado Novo, Casa das Caldeiras |
| Monumentos e museus | `coimbra-para-os-pequenitos` (PDF), `web-visitecoimbra-coimbra-by-night` | Museu Machado de Castro, Torre de Almedina, Museu da Ciência, museus municipais, igrejas e mosteiros |
| Fado e tradições académicas | `web-visitecoimbra-cancao-de-coimbra`, `fado-e-tradicoes-academicas` (PDF), `universidade-alta-sofia-patrimonio-mundial` (PDF) | guitarra de Coimbra, serenatas, Queima das Fitas, Repúblicas, traje |
| Artesanato e tradições locais | `web-visitecoimbra-tecelagem-de-almalagues`, `web-visitecoimbra-cestaria-de-bunho` | tecelagem de Almalaguês, cestaria de bunho de Arzila; no corpus há também a louça de Coimbra |
| Gastronomia e doçaria | `web-visitecoimbra-gastronomia-em-coimbra`, `web-visitecoimbra-restauracao`, `web-visitecoimbra-docaria-conventual-de-coimbra`, `viver-o-patrimonio-em-coimbra` (PDF) | chanfana, lampreia, leitão, queijo Rabaçal, vinhos, doces conventuais e as suas histórias |
| Jardins, lazer e ciência | `jardins-historicos` (PDF), `coimbra-para-os-pequenitos` (PDF) | Parque Verde do Mondego, Jardim Botânico, Quinta das Lágrimas, Penedo da Saudade, UC Exploratório |
| Desporto | `web-visitecoimbra-desporto` | Académica, provas e eventos, atividades ao ar livre |

Áreas presentes no corpus mas **não usadas** como suporte (para evitar sobreposição com smoke
tests ou informação volátil): Biblioteca Joanina, Portugal dos Pequenitos, Repúblicas (lista),
diretório de restaurantes, bares e rooftops, cervejarias, casas de Fado, lojas de cerâmica,
roteiro dos escritores e mercados/feiras com datas.

## 5. Evaluation Questions

### Q01

**Question:** O que é a chanfana, prato típico da região de Coimbra?

**Category:** Gastronomia / restauração

**Difficulty:** Easy

**Question type:** Factual

**Expected answer:** É cabrito cozinhado em vinho tinto, um dos pratos tradicionais da cozinha
coimbrã, ligado ao campo.

**Essential facts:**
- carne de cabrito;
- cozinhada em vinho tinto.

**Score guidance:** 2 = cabrito + vinho tinto; 1 = só um dos dois elementos (p. ex. "carne em
vinho tinto" ou "prato de cabrito"); 0 = outro prato/ingredientes errados.

**Supporting sources:**
- `web-visitecoimbra-gastronomia-em-coimbra` — Gastronomia em Coimbra — corpo do texto ("a chanfana (cabrito cozinhado em vinho tinto)")
- `web-visitecoimbra-restauracao` — Restauração — introdução (chanfana entre os pratos tradicionais das tascas)

**Previously used in smoke tests:** No

### Q02

**Question:** Como se chamam os sinos da Torre da Universidade de Coimbra?

**Category:** Universidade / monumentos / museus

**Difficulty:** Medium

**Question type:** Enumeration

**Expected answer:** A Torre tem quatro sinos que regem a vida académica: a "cabra" (1741), o
"cabrão" (1824), o "bolão" (1561) e o dos "quartos".

**Essential facts:**
- quatro sinos;
- nomes: cabra, cabrão, bolão, quartos.

**Score guidance:** 2 = os quatro nomes (as datas não são obrigatórias); 1 = dois ou três nomes
corretos sem nomes inventados; 0 = só um nome, ou nomes inventados.

**Supporting sources:**
- `universidade-alta-sofia-patrimonio-mundial` — Universidade de Coimbra — Alta e Sofia — 1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS > TORRE
- `fado-e-tradicoes-academicas` — O Fado e as Tradições Académicas — 2. PAÇO DAS ESCOLAS (torre)
- `viver-o-patrimonio-em-coimbra` — Viver o Património em Coimbra — 1. PAÇO DAS ESCOLAS (torre)

**Previously used in smoke tests:** No

### Q03

**Question:** Onde ficava a Judiaria Velha de Coimbra e que estruturas existiam nesse bairro?

**Category:** História e património

**Difficulty:** Hard

**Question type:** Descriptive

**Expected answer:** A Judiaria Velha ficava entre a Rua Corpo de Deus e a atual Rua Visconde
da Luz. Tinha sinagoga, escolas, mercados e vida comercial ativa, e destacava-se por estruturas
como o Mikveh (banhos rituais de purificação) e o Almocávar (cemitério judaico).

**Essential facts:**
- localização entre a Rua Corpo de Deus e a (atual) Rua Visconde da Luz;
- sinagoga (e escolas/mercados);
- Mikveh — banhos rituais de purificação;
- Almocávar — cemitério judaico.

**Score guidance:** 2 = localização + Mikveh e pelo menos mais uma estrutura correta; 1 = só
estruturas corretas sem localização, ou localização com uma única estrutura; 0 = localização
errada ou estruturas inventadas.

**Supporting sources:**
- `web-visitecoimbra-heranca-judaica` — Herança Judaica — corpo do texto

**Previously used in smoke tests:** No

### Q04

**Question:** O que pode um visitante conhecer em Arzila, perto de Coimbra?

**Category:** Turismo / lazer / atividades

**Difficulty:** Medium

**Question type:** Tourist factual recommendation

**Expected answer:** Pode conhecer a cestaria de bunho, um artesanato tradicional de Arzila: ver
o processo de criação e adquirir peças como cestos e esteiras. Pode também descobrir o Paul de
Arzila, uma reserva natural e refúgio de biodiversidade onde cresce o bunho usado como
matéria-prima.

**Essential facts:**
- cestaria de bunho (artesanato tradicional de Arzila);
- o bunho vem do Paul de Arzila (Reserva Natural);
- o Paul de Arzila como espaço natural/biodiversidade a visitar.

**Score guidance:** 2 = cestaria de bunho + Paul de Arzila; 1 = só um dos dois; 0 = nenhum ou
atividades inventadas.

**Supporting sources:**
- `web-visitecoimbra-cestaria-de-bunho` — Cestaria de Bunho — corpo do texto

**Previously used in smoke tests:** No

### Q05

**Question:** Em que é que a guitarra portuguesa de Coimbra difere da guitarra de Lisboa?

**Category:** Cultura / tradições / Fado

**Difficulty:** Medium

**Question type:** Descriptive

**Expected answer:** A guitarra de Coimbra tem uma caixa maior, é afinada num tom abaixo e a sua
voluta tem a forma de uma lágrima, que simboliza a melancolia do repertório.

**Essential facts:**
- caixa maior;
- afinada um tom abaixo;
- voluta em forma de lágrima.

**Score guidance:** 2 = pelo menos dois dos três elementos, sem erros; 1 = um elemento correto;
0 = diferenças inventadas ou contrárias.

**Supporting sources:**
- `web-visitecoimbra-cancao-de-coimbra` — Canção de Coimbra — corpo do texto (parágrafo sobre a guitarra portuguesa de Coimbra)

**Previously used in smoke tests:** No

### Q06

**Question:** Como se chamava Coimbra no tempo dos romanos e porque é que essa cidade cresceu?

**Category:** História e património

**Difficulty:** Medium

**Question type:** Factual

**Expected answer:** Chamava-se Æminium. Cresceu devido ao declínio da vizinha Conímbriga, que no
século V foi constantemente saqueada pelos povos germanos; muitos dos seus habitantes
mudaram-se para Æminium.

**Essential facts:**
- nome romano: Æminium (Aeminium);
- crescimento ligado ao declínio de Conímbriga / saques no séc. V, com os habitantes a mudarem-se.

**Score guidance:** 2 = Æminium + declínio/saques de Conímbriga; 1 = só o nome correto; 0 = nome
errado (p. ex. "Conímbriga" como nome de Coimbra).

**Supporting sources:**
- `web-visitecoimbra-coimbra-muralhada` — Coimbra Muralhada — corpo do texto

**Previously used in smoke tests:** No

### Q07

**Question:** O que é o UC Exploratório e onde fica?

**Category:** Turismo / lazer / atividades

**Difficulty:** Easy

**Question type:** Descriptive

**Expected answer:** É o Centro Ciência Viva da Universidade de Coimbra, um espaço de promoção da
ciência e da cultura científica com atividades interativas para todos os públicos, incluindo um
planetário com projeção a 360 graus. Fica no Parque Verde do Mondego.

**Essential facts:**
- centro de ciência (Centro Ciência Viva da Universidade de Coimbra);
- localização no Parque Verde do Mondego.

**Score guidance:** 2 = centro de ciência da UC + Parque Verde do Mondego; 1 = só um dos dois;
0 = descrição errada. O planetário é um complemento, não é obrigatório.

**Supporting sources:**
- `coimbra-para-os-pequenitos` — Coimbra para os Pequenitos — 5. UC EXPLORATÓRIO — CIÊNCIA VIVA COIMBRA

**Previously used in smoke tests:** No

### Q08

**Question:** O que são os Crúzios e onde os posso provar em Coimbra?

**Category:** Gastronomia / restauração

**Difficulty:** Hard

**Question type:** Descriptive + Tourist factual recommendation

**Expected answer:** São doces conventuais de Coimbra, de massa fina e crocante recheada com
creme de ovos e amêndoa, batizados com o nome dos Cónegos (crúzios) do Mosteiro de Santa Cruz.
Podem ser provados no Café Santa Cruz, na Praça 8 de Maio.

**Essential facts:**
- doce conventual de massa fina recheada com creme de ovos e amêndoa;
- nome ligado aos cónegos do Mosteiro de Santa Cruz;
- Café Santa Cruz (Praça 8 de Maio).

**Score guidance:** 2 = descrição do doce + Café Santa Cruz; 1 = descrição correta sem o local,
ou o local sem descrição correta; 0 = doce descrito de forma errada.

**Supporting sources:**
- `web-visitecoimbra-docaria-conventual-de-coimbra` — Doçaria Conventual de Coimbra — Doces a não perder > Crúzios
- `viver-o-patrimonio-em-coimbra` — Viver o Património em Coimbra — 17. PRAÇA 8 DE MAIO

**Previously used in smoke tests:** No (tema vizinho: o smoke tinha uma pergunta genérica sobre
doces tradicionais; esta pergunta pede factos diferentes, de duas fontes).

### Q09

**Question:** Porque é que a colunata do Paço das Escolas se chama Via Latina?

**Category:** Universidade / monumentos / museus

**Difficulty:** Easy

**Question type:** Factual

**Expected answer:** O nome relembra a antiga regra que proibia falar qualquer idioma que não o
latim quando se passava por ela. É uma grande colunata de finais do século XVIII.

**Essential facts:**
- regra antiga: só se podia falar latim ao passar por ela.

**Score guidance:** 2 = regra do latim; 1 = ligação vaga ao latim/ensino em latim sem a regra;
0 = explicação inventada.

**Supporting sources:**
- `universidade-alta-sofia-patrimonio-mundial` — Universidade de Coimbra — Alta e Sofia — 1. PAÇO DAS ESCOLAS > VIA LATINA
- `fado-e-tradicoes-academicas` — O Fado e as Tradições Académicas — 2. PAÇO DAS ESCOLAS (via latina)
- `viver-o-patrimonio-em-coimbra` — Viver o Património em Coimbra — 1. PAÇO DAS ESCOLAS (via latina)

**Previously used in smoke tests:** No

### Q10

**Question:** Qual é a origem da Queima das Fitas?

**Category:** Cultura / tradições / Fado

**Difficulty:** Medium

**Question type:** Factual

**Expected answer:** Remonta a 1899, quando se realizou pela primeira vez o Centenário da
Sebenta: os estudantes apresentaram-se publicamente num cortejo, com fogo de artifício, um sarau
e algumas garraiadas.

**Essential facts:**
- ano de 1899;
- Centenário da Sebenta;
- (complemento) cortejo, fogo de artifício, sarau, garraiadas.

**Score guidance:** 2 = 1899 + Centenário da Sebenta; 1 = só um dos dois; 0 = origem/data
inventada ou contrária.

**Supporting sources:**
- `fado-e-tradicoes-academicas` — O Fado e as Tradições Académicas — 11. PRAÇA DA CANÇÃO

**Previously used in smoke tests:** No

### Q11

**Question:** Que atividades de lazer e desporto posso fazer no Parque Verde do Mondego?

**Category:** Turismo / lazer / atividades

**Difficulty:** Hard

**Question type:** Tourist factual recommendation / Enumeration

**Expected answer:** O parque estende-se por cerca de 4 km da margem do rio, com corredores para
peões e ciclovias e pavilhões com exposições temporárias. Na margem esquerda tem uma caixa de
areia para voleibol de praia, um skatepark, equipamentos de diversão infantil, um parque de
merendas e pavilhões de clubes de atividades náuticas (canoagem, remo e vela). A ponte pedonal
Pedro e Inês liga as duas margens.

**Essential facts:**
- passear a pé / andar de bicicleta (corredores pedonais e ciclovias);
- voleibol de praia;
- skatepark;
- atividades náuticas (canoagem, remo, vela);
- (complementos) parque infantil, merendas, exposições, ponte Pedro e Inês.

**Score guidance:** 2 = pelo menos quatro atividades/equipamentos corretos, incluindo as
náuticas; 1 = duas ou três corretas; 0 = só uma, ou atividades inventadas relevantes.

**Supporting sources:**
- `jardins-historicos` — Jardins Históricos — 2. PARQUE VERDE DO MONDEGO
- `coimbra-para-os-pequenitos` — Coimbra para os Pequenitos — 4. PARQUE VERDE DO MONDEGO

**Previously used in smoke tests:** No

### Q12

**Question:** Segundo a lenda da princesa Cindazunda, o que representam as figuras do brasão de Coimbra?

**Category:** História e património (lendas)

**Difficulty:** Hard

**Question type:** Descriptive

**Expected answer:** A figura feminina coroada é Cindazunda, princesa sueva dada em casamento
para selar a paz. O leão representa Ataces, rei dos Alanos, e a serpe alada (dragão) representa
Hermenerico, rei dos Suevos e pai de Cindazunda. A taça (cálice) simboliza as bodas / a aliança
matrimonial entre os dois povos.

**Essential facts:**
- donzela coroada = Cindazunda;
- leão = Ataces (Alanos);
- serpe alada / dragão = Hermenerico (Suevos);
- taça / cálice = bodas / aliança matrimonial.

**Score guidance:** 2 = Cindazunda + os dois reis associados ao leão e à serpe + taça como
bodas/aliança; 1 = Cindazunda e a ideia de união entre os dois reis, mas com a atribuição do
leão e da serpe omitida ou trocada; 0 = interpretação diferente apresentada como sendo esta
lenda, ou figuras inventadas.

**Supporting sources:**
- `web-visitecoimbra-princesa-cindazunda` — Princesa Cindazunda — corpo do texto
- `web-visitecoimbra-o-brasao-da-cidade-de-coimbra` — O Brasão da Cidade de Coimbra — corpo do texto

**Previously used in smoke tests:** No

### Q13

**Question:** Que tradição de casamento está associada ao Arroz Doce de Coimbra?

**Category:** Gastronomia / restauração

**Difficulty:** Medium

**Question type:** Descriptive

**Expected answer:** Quando as raparigas do povo e o noivo convidavam os familiares para o
casamento, ofereciam-lhes uma travessa de arroz doce coberta com um pano bordado nos teares de
Almalaguês. Quando a travessa era recolhida, os recém-casados recebiam o presente de casamento.

**Essential facts:**
- travessa de arroz doce oferecida aos familiares convidados para o casamento;
- coberta com pano bordado nos teares de Almalaguês;
- ao recolher a travessa, os noivos recebiam o presente de casamento.

**Score guidance:** 2 = oferta da travessa aos convidados + receber o presente ao recolhê-la;
1 = só a oferta em contexto de casamento; 0 = tradição inventada ou sem ligação a casamento.

**Supporting sources:**
- `web-visitecoimbra-docaria-conventual-de-coimbra` — Doçaria Conventual de Coimbra — Doces a não perder > Arroz Doce de Coimbra

**Previously used in smoke tests:** No

### Q14

**Question:** Para que foi originalmente construída a Casa das Caldeiras, em Coimbra?

**Category:** Universidade / monumentos / museus

**Difficulty:** Medium

**Question type:** Factual / Descriptive

**Expected answer:** Foi construída em 1941, na modernização das infraestruturas geradoras de
energia térmica para o funcionamento dos Hospitais da Universidade de Coimbra; tinha as
caldeiras que aqueciam esses edifícios. É um dos raros exemplos de património industrial da
cidade e hoje é um espaço com noites de música e eventos.

**Essential facts:**
- produção de energia térmica / caldeiras de aquecimento;
- ao serviço dos Hospitais da Universidade de Coimbra (a fonte Web diz "aqueciam a Universidade";
  as duas formulações são aceites);
- (complemento) 1941; património industrial; uso atual cultural/noturno.

**Score guidance:** 2 = função térmica/caldeiras ligada aos Hospitais/Universidade; 1 = só
"caldeiras" ou "património industrial", sem a função; 0 = função inventada.

**Supporting sources:**
- `universidade-alta-sofia-patrimonio-mundial` — Universidade de Coimbra — Alta e Sofia — 13. CASA DAS CALDEIRAS
- `web-visitecoimbra-coimbra-by-night` — Coimbra By Night — 10 locais imperdíveis para sair à noite em Coimbra (Casa das Caldeiras)

**Previously used in smoke tests:** No

### Q15

**Question:** Onde se realiza a Serenata Monumental da Queima das Fitas e como devem os estudantes comportar-se durante as serenatas monumentais?

**Category:** Cultura / tradições / Fado

**Difficulty:** Hard

**Question type:** Descriptive

**Expected answer:** Realiza-se todos os anos na escadaria da Sé Velha e marca o início da
Queima das Fitas: ao soarem as 12 badaladas, os estudantes trajados alinham num coro de silêncio
para escutar o Fado. Durante as Serenatas Monumentais têm de estar de capa traçada, manter o
silêncio e não aplaudir.

**Essential facts:**
- escadaria da Sé Velha;
- capa traçada;
- silêncio;
- não aplaudir;
- (complemento) marca o início da Queima das Fitas; 12 badaladas.

**Score guidance:** 2 = Sé Velha + pelo menos duas das três regras (capa traçada, silêncio, não
aplaudir); 1 = só o local, ou só as regras; 0 = local errado ou regras contrárias (p. ex.
"aplaudir no fim").

**Supporting sources:**
- `fado-e-tradicoes-academicas` — O Fado e as Tradições Académicas — 7. SÉ VELHA; página 2 (texto introdutório, regras das serenatas)
- `universidade-alta-sofia-patrimonio-mundial` — Universidade de Coimbra — Alta e Sofia — 21. SÉ VELHA

**Previously used in smoke tests:** No

### Q16

**Question:** Em que anos é que a Académica de Coimbra ganhou a Taça de Portugal?

**Category:** Turismo / lazer / atividades (desporto)

**Difficulty:** Easy

**Question type:** Factual

**Expected answer:** Em 1939 e em 2012. A equipa de futebol da Associação Académica de Coimbra
(fundada em 1887) é conhecida como "A Briosa".

**Essential facts:**
- 1939;
- 2012.

**Score guidance:** 2 = os dois anos, sem anos adicionais errados; 1 = só um dos anos correto;
0 = anos errados.

**Supporting sources:**
- `web-visitecoimbra-desporto` — Desporto — parágrafo final (Associação Académica de Coimbra, "A Briosa")

**Previously used in smoke tests:** No

### Q17

**Question:** Em que ano é que D. Afonso Henriques transferiu a capital do Condado Portucalense para Coimbra, e de onde?

**Category:** História e património

**Difficulty:** Easy

**Question type:** Factual

**Expected answer:** Em 1131, transferindo-a de Guimarães para Coimbra, o que foi importante
para a independência e fundação do Reino de Portugal, em 1143.

**Essential facts:**
- 1131;
- de Guimarães.

**Score guidance:** 2 = 1131 + Guimarães; 1 = só um dos dois correto; 0 = ano e origem errados.

**Supporting sources:**
- `fundacao-da-nacionalidade` — Fundação da Nacionalidade — página 2 (texto introdutório "fundação da nacionalidade")
- `web-visitecoimbra-coimbra-muralhada` — Coimbra Muralhada — corpo do texto (Coimbra como capital do Condado Portucalense, sem data)

**Previously used in smoke tests:** No

### Q18

**Question:** Em que edifício está instalado o Museu Nacional Machado de Castro, sobre que estrutura romana assenta, e quem homenageia o seu nome?

**Category:** Universidade / monumentos / museus

**Difficulty:** Hard

**Question type:** Factual (multi-facto)

**Expected answer:** Ocupa o antigo Paço Episcopal, construído sobre o criptopórtico do fórum de
Æminium, a mais significativa obra romana (séc. I) em território nacional. O nome homenageia o
escultor régio Joaquim Machado de Castro (1731-1822), nascido nos arredores de Coimbra.

**Essential facts:**
- antigo Paço Episcopal;
- criptopórtico do fórum romano de Æminium;
- homenagem ao escultor Joaquim Machado de Castro.

**Score guidance:** 2 = os três elementos (é aceitável "fórum romano" ou "criptopórtico" sem o
nome Æminium); 1 = dois dos três; 0 = um ou nenhum, ou informação contrária.

**Supporting sources:**
- `coimbra-para-os-pequenitos` — Coimbra para os Pequenitos — 2. MUSEU NACIONAL MACHADO DE CASTRO

**Previously used in smoke tests:** No

### Q19

**Question:** O que caracteriza a tecelagem de Almalaguês e que peças são típicas desta arte?

**Category:** Cultura / tradições / Fado (artesanato)

**Difficulty:** Medium

**Question type:** Descriptive

**Expected answer:** É uma tradição de tecelagem da freguesia de Almalaguês, nos arredores de
Coimbra, reconhecida pelos padrões geométricos minuciosos e pelas cores vibrantes, feita pelas
tecedeiras em teares. Era produzida originalmente em linho e hoje sobretudo em algodão. As peças
típicas são colchas, tapetes e atoalhados.

**Essential facts:**
- padrões geométricos e cores vibrantes, feita em teares pelas tecedeiras;
- linho originalmente, hoje sobretudo algodão;
- peças: colchas, tapetes, atoalhados.

**Score guidance:** 2 = caracterização (padrões/cores ou materiais) + pelo menos duas peças
típicas; 1 = só a caracterização ou só as peças; 0 = descrição errada (outra técnica/material).

**Supporting sources:**
- `web-visitecoimbra-tecelagem-de-almalagues` — Tecelagem de Almalaguês — corpo do texto

**Previously used in smoke tests:** No

### Q20

**Question:** Que peixes do rio Mondego são protagonistas na gastronomia de Coimbra, e qual é o prato famoso que os representa?

**Category:** Gastronomia / restauração

**Difficulty:** Easy

**Question type:** Factual

**Expected answer:** A lampreia e a enguia; o prato famoso é o arroz de lampreia.

**Essential facts:**
- lampreia;
- enguia;
- arroz de lampreia.

**Score guidance:** 2 = lampreia + enguia + arroz de lampreia; 1 = lampreia e arroz de lampreia
sem a enguia, ou os dois peixes sem o prato; 0 = peixes errados.

**Supporting sources:**
- `web-visitecoimbra-gastronomia-em-coimbra` — Gastronomia em Coimbra — corpo do texto e citação destacada

**Previously used in smoke tests:** No

## 6. Coverage Summary

| Q | Category | Difficulty | Type | Source type |
|---|---|---|---|---|
| Q01 | Gastronomia / restauração | Easy | Factual | Web |
| Q02 | Universidade / monumentos / museus | Medium | Enumeration | PDF |
| Q03 | História e património | Hard | Descriptive | Web |
| Q04 | Turismo / lazer / atividades | Medium | Tourist factual | Web |
| Q05 | Cultura / tradições / Fado | Medium | Descriptive | Web |
| Q06 | História e património | Medium | Factual | Web |
| Q07 | Turismo / lazer / atividades | Easy | Descriptive | PDF |
| Q08 | Gastronomia / restauração | Hard | Descriptive + tourist | Mixed (Web + PDF) |
| Q09 | Universidade / monumentos / museus | Easy | Factual | PDF |
| Q10 | Cultura / tradições / Fado | Medium | Factual | PDF |
| Q11 | Turismo / lazer / atividades | Hard | Tourist factual / Enumeration | PDF |
| Q12 | História e património | Hard | Descriptive | Web |
| Q13 | Gastronomia / restauração | Medium | Descriptive | Web |
| Q14 | Universidade / monumentos / museus | Medium | Factual / Descriptive | Mixed (PDF + Web) |
| Q15 | Cultura / tradições / Fado | Hard | Descriptive | PDF |
| Q16 | Turismo / lazer / atividades | Easy | Factual | Web |
| Q17 | História e património | Easy | Factual | PDF (+ Web sem data) |
| Q18 | Universidade / monumentos / museus | Hard | Factual (multi-facto) | PDF |
| Q19 | Cultura / tradições / Fado | Medium | Descriptive | Web |
| Q20 | Gastronomia / restauração | Easy | Factual | Web |

**Por categoria**

| Category | Nº | Easy | Medium | Hard |
|---|---:|---:|---:|---:|
| História e património | 4 | 1 | 1 | 2 |
| Universidade / monumentos / museus | 4 | 1 | 2 | 1 |
| Cultura / tradições / Fado | 4 | 0 | 3 | 1 |
| Gastronomia / restauração | 4 | 2 | 1 | 1 |
| Turismo / lazer / atividades | 4 | 2 | 1 | 1 |
| **Total** | **20** | **6** | **8** | **6** |

**Tipo de pergunta** (Q08 e Q11 contam em dois tipos):
- Factual: 8 (Q01, Q06, Q09, Q10, Q16, Q17, Q18, Q20).
- Descriptive: 9 (Q03, Q05, Q07, Q08, Q12, Q13, Q14, Q15, Q19).
- Enumeration: 2 (Q02, Q11).
- Tourist factual recommendation: 3 (Q04, Q08, Q11).

**Fontes**

- Documentos diferentes usados como suporte: **18 de 35**.
  - **PDF (6)**: `fundacao-da-nacionalidade`, `universidade-alta-sofia-patrimonio-mundial`,
    `fado-e-tradicoes-academicas`, `viver-o-patrimonio-em-coimbra`,
    `coimbra-para-os-pequenitos`, `jardins-historicos`.
  - **Web (12)**: `gastronomia-em-coimbra`, `restauracao`, `heranca-judaica`,
    `cestaria-de-bunho`, `cancao-de-coimbra`, `coimbra-muralhada`,
    `docaria-conventual-de-coimbra`, `princesa-cindazunda`, `o-brasao-da-cidade-de-coimbra`,
    `coimbra-by-night`, `desporto`, `tecelagem-de-almalagues`.
- Perguntas com suporte principal em PDF: **8** (Q02, Q07, Q09, Q10, Q11, Q15, Q17, Q18).
- Perguntas com suporte principal em Web: **10** (Q01, Q03, Q04, Q05, Q06, Q12, Q13, Q16, Q19, Q20).
- Perguntas mistas (factos essenciais em PDF e em Web): **2** (Q08, Q14).
- Não há concentração: nenhum documento suporta mais de 4 perguntas. Os mais usados,
  `universidade-alta-sofia-patrimonio-mundial` (Q02, Q09, Q14, Q15) e
  `fado-e-tradicoes-academicas` (Q02, Q09, Q10, Q15), partilham quase sempre esse suporte com
  outras fontes.

**Equilíbrio de conhecimento (para não favorecer o RAG):** o conjunto mistura factos
relativamente conhecidos sobre Coimbra (Q01, Q06, Q09, Q10, Q16, Q17, Q20), conhecimento local
específico (Q02, Q04, Q05, Q07, Q12, Q15, Q19) e detalhes que dependem mais das fontes (Q03,
Q08, Q11, Q13, Q14, Q18).

## 7. Validation

Segunda passagem, pergunta a pergunta, feita contra o texto dos documentos processados (secção
e frase localizadas), segundo os critérios A–H: resposta explícita no corpus; resposta esperada
e factos essenciais integralmente suportados pelas fontes indicadas; avaliável em 0/1/2; sem
conhecimento externo; sem informação volátil; diferente das perguntas dos smoke tests;
formulação natural.

| Q | Corpus-supported | Objective 0–2 | Stable | New vs smoke | Valid |
|---|---|---|---|---|---|
| Q01 | YES | YES | YES | YES | YES |
| Q02 | YES | YES | YES | YES | YES |
| Q03 | YES | YES | YES | YES | YES |
| Q04 | YES | YES | YES | YES | YES |
| Q05 | YES | YES | YES | YES | YES |
| Q06 | YES | YES | YES | YES | YES |
| Q07 | YES | YES | YES (dias de abertura excluídos da resposta esperada) | YES | YES |
| Q08 | YES | YES | YES | YES (tema vizinho: doces) | YES |
| Q09 | YES | YES | YES | YES | YES |
| Q10 | YES | YES | YES | YES | YES |
| Q11 | YES | YES | YES | YES | YES |
| Q12 | YES | YES | YES | YES | YES |
| Q13 | YES | YES | YES | YES | YES |
| Q14 | YES | YES | YES | YES | YES |
| Q15 | YES | YES | YES | YES | YES |
| Q16 | YES | YES | YES (resultados históricos) | YES | YES |
| Q17 | YES | YES | YES | YES | YES |
| Q18 | YES | YES | YES | YES | YES |
| Q19 | YES | YES | YES | YES | YES |
| Q20 | YES | YES | YES | YES | YES |

Notas de validação:

- **Candidatas substituídas antes de congelar**: temas ligados a perguntas de smoke ou
  desenvolvimento (fundação de Santa Clara-a-Velha, Biblioteca Joanina, Portugal dos Pequenitos,
  Repúblicas, Pedro e Inês/Quinta das Lágrimas); os restaurantes Guia Michelin (lista comercial
  volátil); a Feira dos 7 e 23 (calendário operacional); a Prisão Académica (datas de extinção
  diferentes entre fontes: 1834 vs 1832).
- **Divergências entre fontes nos factos usados**: nenhuma que afete os factos essenciais. Na
  Q14, "Hospitais da Universidade" (PDF) e "aqueciam a Universidade" (Web) são as duas aceites e
  isso fica registado. Na Q17, só o PDF dá o ano; a fonte Web não o contradiz.
- **Perguntas de smoke evitadas**: Biblioteca Joanina (ano de conclusão, morcegos), Portugal dos
  Pequenitos (projetista), Mosteiro de Santa Cruz (ano de fundação), Sesnando, doces
  tradicionais, Repúblicas, museus, origem da Canção de Coimbra, Pedro e Inês, Santa Clara-a-Velha
  (fundação/conflito), Paço das Escolas (definição), pergunta fora do domínio (preço de bilhete),
  cervejarias, onde ouvir Fado, onde sair à noite, restauração, desporto (atividades), onde
  comprar cerâmica. **Nenhuma das 20 perguntas é reutilizada.**

## 8. Frozen Set

TOTAL QUESTIONS: 20

ALL QUESTIONS SUPPORTED BY THE FROZEN CORPUS: YES

ALL EXPECTED ANSWERS VERIFIED AGAINST THE CORPUS: YES

QUESTION SET READY TO FREEZE BEFORE RAG/NO-RAG EXECUTION: YES
