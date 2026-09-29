# D2 — RAG vs No-RAG Answer Quality Evaluation Set V2

## 1. Reason for V2

A revisão manual da V1 revelou um problema metodológico: alguns factos esperados resultavam de associações ou inferências entre documentos independentes, em vez de constarem explicitamente do corpus. A V2 foi reconstruída diretamente a partir do corpus congelado. Cada Essential Fact abaixo tem evidência textual direta, literal e identificada no documento que o suporta. A V1 permanece preservada, sem alterações, para transparência e memória do processo.

## 2. Evaluation Protocol

- Avaliar exatamente 20 perguntas em português, no domínio do turismo em Coimbra.
- Comparar RAG e No-RAG usando o mesmo LLM e as mesmas condições de geração, diferindo apenas o acesso ao corpus.
- Atribuir uma única pontuação de qualidade da resposta, de 0 a 2.
- Aplicar a Score Guidance específica de cada pergunta, derivada apenas dos respetivos Essential Facts.
- O conjunto é definido e validado antes de qualquer nova execução RAG ou No-RAG.
- Nesta fase não foi executado retrieval, RAG, No-RAG, LLM, embedding ou consulta ao vector store.

## 3. Answer Quality Score

| Score | Classification | Definition |
|---:|---|---|
| 2 | CORRECT | A resposta está factualmente correta, responde adequadamente à pergunta, contém todos os elementos essenciais e não apresenta erros relevantes. |
| 1 | PARTIALLY CORRECT | A resposta contém informação relevante e correta, mas está incompleta ou contém uma pequena imprecisão que não destrói a ideia principal. |
| 0 | INCORRECT | A resposta está errada, contradiz os factos essenciais, inventa informação relevante ou não responde efetivamente. |

## 4. Corpus Audit

Foram encontrados e lidos integralmente 35 documentos Markdown em `d2_rag/data/processed/`: 8 documentos processados de PDF e 27 páginas Web.

| document_id | title | source type | main supported topics |
|---|---|---|---|
| `biblioteca-joanina-uctour` | Biblioteca Joanina | PDF | História, pisos, acervo, conservação e Prisão Académica |
| `coimbra-dos-escritores` | Coimbra dos Escritores | PDF | Roteiro literário, autores, monumentos, jardins e espaços urbanos |
| `coimbra-para-os-pequenitos` | Coimbra para os Pequenitos | PDF | Museus, Parque Verde, UC Exploratório e Portugal dos Pequenitos |
| `fado-e-tradicoes-academicas` | O Fado e as Tradições Académicas | PDF | Fado, serenatas, Repúblicas, festas e património académico |
| `fundacao-da-nacionalidade` | Fundação da Nacionalidade | PDF | Formação de Portugal, Santa Cruz, Mondego e mosteiros |
| `jardins-historicos` | Jardins Históricos | PDF | Jardins, parques, monumentos, paisagismo e lazer |
| `universidade-alta-sofia-patrimonio-mundial` | Universidade de Coimbra — Alta e Sofia: Património Mundial | PDF | Universidade, Paço das Escolas, colégios e património da Alta e Sofia |
| `viver-o-patrimonio-em-coimbra` | Viver o Património em Coimbra | PDF | Alta, Baixa, largos, igrejas, edifícios e evolução urbana |
| `web-visitecoimbra-cancao-de-coimbra` | Canção de Coimbra | Web | Fado/Canção, guitarra, intérpretes e convenções de atuação |
| `web-visitecoimbra-ceira` | Ceira | Web | Paisagem rural, rio, passeios, piqueniques e lazer |
| `web-visitecoimbra-ceramica-de-coimbra` | Cerâmica de Coimbra | Web | Louça ratinha, desenho miúdo, produção e artesãos |
| `web-visitecoimbra-cestaria-de-bunho` | Cestaria de Bunho | Web | Artesanato de Arzila, matéria-prima, produção e património natural |
| `web-visitecoimbra-coimbra-by-night` | Coimbra By Night | Web | Vida noturna, casas de Fado e rooftops |
| `web-visitecoimbra-coimbra-dos-estudantes` | Coimbra dos Estudantes | Web | Ensino superior, traje, festas e Associação Académica |
| `web-visitecoimbra-coimbra-muralhada` | Coimbra Muralhada | Web | Æminium, muralhas, Reconquista e Núcleo da Cidade Muralhada |
| `web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira` | Coimbra: Uma Cidade com Tradição Cervejeira | Web | História da cerveja, produção monástica e cerveja artesanal |
| `web-visitecoimbra-d-afonso-henriques` | D. Afonso Henriques | Web | Primeiro rei, independência, túmulo e Mosteiro de Santa Cruz |
| `web-visitecoimbra-desporto` | Desporto | Web | Modalidades, instalações, clubes, provas e Regata da Queima das Fitas |
| `web-visitecoimbra-docaria-conventual-de-coimbra` | Doçaria Conventual de Coimbra | Web | Doces conventuais, ingredientes, origens e tradições |
| `web-visitecoimbra-gastronomia-em-coimbra` | Gastronomia em Coimbra | Web | Pratos, produtos regionais, rio Mondego, queijos e vinhos |
| `web-visitecoimbra-heranca-cultural-e-religiosa` | Herança Cultural e Religiosa | Web | Igrejas, mosteiros, colégios e monumentos religiosos |
| `web-visitecoimbra-heranca-judaica` | Herança Judaica | Web | Comunidade judaica, Judiaria Velha, Mikveh e Almocávar |
| `web-visitecoimbra-heranca-mocarabe` | Herança Moçárabe | Web | Domínio muçulmano, moçárabes e influências arquitetónicas |
| `web-visitecoimbra-luis-vaz-de-camoes` | Luís Vaz de Camões | Web | Camões, Os Lusíadas, exemplares em Coimbra e Inês de Castro |
| `web-visitecoimbra-mercados` | Mercados | Web | Mercado D. Pedro V, feiras e produtos locais |
| `web-visitecoimbra-museus` | Museus | Web | Espaços museológicos, coleções e património visitável |
| `web-visitecoimbra-o-brasao-da-cidade-de-coimbra` | O Brasão da Cidade de Coimbra | Web | Evolução, símbolos e interpretações do brasão |
| `web-visitecoimbra-pedro-e-ines` | Pedro e Inês | Web | Romance, conflito, morte de Inês e locais associados |
| `web-visitecoimbra-princesa-cindazunda` | Princesa Cindazunda | Web | Lenda, paz entre Alanos e Suevos e brasão |
| `web-visitecoimbra-rainha-santa-isabel` | Rainha Santa Isabel | Web | Milagre das Rosas, devoção, procissão e relíquia |
| `web-visitecoimbra-republicas` | Repúblicas | Web | Comunidades estudantis, autogestão, valores e lista de Repúblicas |
| `web-visitecoimbra-restauracao` | Restauração | Web | Tipos de cozinha e estabelecimentos de restauração |
| `web-visitecoimbra-santo-antonio` | Santo António | Web | Fernando de Bulhões, Santa Cruz, formação e decisão franciscana |
| `web-visitecoimbra-sesnando-david` | Sesnando David | Web | Reconquista, governo de Coimbra, Sé Velha e Feira Medieval |
| `web-visitecoimbra-tecelagem-de-almalagues` | Tecelagem de Almalaguês | Web | Tecelagem, materiais, peças, economia e continuidade da tradição |

## 5. Evaluation Questions

### Q01

**Question:** Que dois contributos são atribuídos a D. Dinis no Largo que o homenageia em Coimbra?

**Category:** História e património

**Difficulty:** Easy

**Question type:** Enumeration

**Expected answer:** D. Dinis é apresentado como responsável pela fundação dos Estudos Gerais e pela introdução do português na documentação oficial.

**Essential facts:**

#### Fact 1

D. Dinis foi responsável pela fundação dos Estudos Gerais.

**Evidence:**
> Foi ele o responsável pela fundação dos Estudos Gerais

**Source:** `coimbra-dos-escritores` — *Coimbra dos Escritores* — `3. LARGO D. DINIS`

#### Fact 2

A D. Dinis é atribuída a introdução do idioma português na documentação oficial.

**Evidence:**
> e a ele se deve também a introdução do idioma português na documentação oficial.

**Source:** `coimbra-dos-escritores` — *Coimbra dos Escritores* — `3. LARGO D. DINIS`

**Score guidance:** 2 = identifica corretamente os dois contributos; 1 = identifica corretamente apenas um; 0 = não identifica nenhum ou atribui contributos errados.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q02

**Question:** Em que instituição de Coimbra ingressou Fernando de Bulhões e que decisão transformadora tomou depois na cidade?

**Category:** História e património

**Difficulty:** Medium

**Question type:** Factual

**Expected answer:** Ingressou no Mosteiro de Santa Cruz e, em Coimbra, decidiu tornar-se franciscano e adotar o nome de António.

**Essential facts:**

#### Fact 1

Fernando de Bulhões ingressou no Mosteiro de Santa Cruz, em Coimbra.

**Evidence:**
> Fernando mudou-se ainda jovem para Coimbra, onde ingressou no Mosteiro de Santa Cruz

**Source:** `web-visitecoimbra-santo-antonio` — *Santo António* — `Santo António`

#### Fact 2

Em Coimbra, decidiu tornar-se franciscano e adotar o nome de António.

**Evidence:**
> A decisão de se tornar franciscano e adotar o nome de António foi tomada em Coimbra

**Source:** `web-visitecoimbra-santo-antonio` — *Santo António* — `Santo António`

**Score guidance:** 2 = indica Santa Cruz e a decisão de se tornar franciscano/adotar o nome António; 1 = apresenta corretamente apenas um destes elementos; 0 = nenhum elemento correto ou informação contraditória.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q03

**Question:** Em que séculos Coimbra esteve sob domínio mouro e que duas igrejas são apontadas como exemplos de influência moçárabe?

**Category:** História e património

**Difficulty:** Medium

**Question type:** Factual / Enumeration

**Expected answer:** Coimbra esteve sob domínio mouro nos séculos VIII e IX; a Igreja de São Salvador e a Igreja de São Bartolomeu são indicadas como exemplos de influência moçárabe.

**Essential facts:**

#### Fact 1

O domínio mouro referido ocorreu durante os séculos VIII e IX.

**Evidence:**
> Coimbra, durante os séculos VIII e IX, foi dominada pelos mouros

**Source:** `web-visitecoimbra-heranca-mocarabe` — *Herança Moçárabe* — `Herança Moçárabe`

#### Fact 2

As igrejas de São Salvador e São Bartolomeu exibem influências moçárabes.

**Evidence:**
> Algumas igrejas, como a Igreja de São Salvador e a Igreja de São Bartolomeu, exibem influências moçárabes

**Source:** `web-visitecoimbra-heranca-mocarabe` — *Herança Moçárabe* — `Herança Moçárabe`

**Score guidance:** 2 = indica os séculos VIII e IX e nomeia as duas igrejas; 1 = acerta o período ou as duas igrejas, ou apresenta apenas parte correta da resposta; 0 = nenhum elemento essencial correto.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q04

**Question:** Entre que anos foi construída a Estação Nova de Coimbra e quem assinou o projeto?

**Category:** História e património

**Difficulty:** Easy

**Question type:** Factual

**Expected answer:** Foi construída entre 1925 e 1931, segundo projeto dos arquitetos Cotinelli Telmo e Luís Cunha.

**Essential facts:**

#### Fact 1

A Estação Nova foi construída entre 1925 e 1931.

**Evidence:**
> A Estação Nova foi construída entre 1925 e 1931

**Source:** `viver-o-patrimonio-em-coimbra` — *Viver o Património em Coimbra* — `11. LARGO DAS AMEIAS | CAIS DAS AMEIAS`

#### Fact 2

O projeto foi dos arquitetos Cotinelli Telmo e Luís Cunha.

**Evidence:**
> com projeto dos arquitetos Cotinelli Telmo e Luís Cunha

**Source:** `viver-o-patrimonio-em-coimbra` — *Viver o Património em Coimbra* — `11. LARGO DAS AMEIAS | CAIS DAS AMEIAS`

**Score guidance:** 2 = apresenta corretamente o intervalo 1925–1931 e os dois arquitetos; 1 = acerta o intervalo ou os autores, ou omite um dos arquitetos; 0 = nenhum elemento correto.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q05

**Question:** Quais eram as duas principais funções do Piso Intermédio da Biblioteca Joanina?

**Category:** Universidade / monumentos / museus

**Difficulty:** Easy

**Question type:** Enumeration

**Expected answer:** Servia de apoio aos guardas da Prisão Académica e de depósito dos livros lidos no Piso Nobre.

**Essential facts:**

#### Fact 1

O Piso Intermédio apoiava os guardas que vigiavam a Prisão Académica.

**Evidence:**
> serviu de apoio aos guardas que vigiavam a prisão académica

**Source:** `biblioteca-joanina-uctour` — *Biblioteca Joanina* — `Piso Intermédio`

#### Fact 2

Funcionava como depósito dos livros lidos no Piso Nobre.

**Evidence:**
> e funcionou como depósito dos livros que eram lidos no piso nobre.

**Source:** `biblioteca-joanina-uctour` — *Biblioteca Joanina* — `Piso Intermédio`

**Score guidance:** 2 = refere as duas funções; 1 = refere corretamente apenas uma; 0 = não refere nenhuma ou apresenta funções erradas.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q06

**Question:** Quando foi criada a Faculdade de Letras de Coimbra, a que faculdade sucedeu e quando foi inaugurado o novo edifício?

**Category:** Universidade / monumentos / museus

**Difficulty:** Hard

**Question type:** Factual

**Expected answer:** Foi criada em 1911, sucedeu à antiga Faculdade de Teologia e o novo edifício foi inaugurado em 22 de novembro de 1951.

**Essential facts:**

#### Fact 1

A Faculdade de Letras foi criada em 1911.

**Evidence:**
> Criada em 1911, a Faculdade de Letras

**Source:** `universidade-alta-sofia-patrimonio-mundial` — *Universidade de Coimbra — Alta e Sofia: Património Mundial* — `3. FACULDADE DE LETRAS`

#### Fact 2

A Faculdade de Letras sucedeu à antiga Faculdade de Teologia.

**Evidence:**
> sucedeu à antiga Faculdade de Teologia

**Source:** `universidade-alta-sofia-patrimonio-mundial` — *Universidade de Coimbra — Alta e Sofia: Património Mundial* — `3. FACULDADE DE LETRAS`

#### Fact 3

O novo edifício foi inaugurado em 22 de novembro de 1951.

**Evidence:**
> a inauguração ocorreu a 22 de novembro de 1951.

**Source:** `universidade-alta-sofia-patrimonio-mundial` — *Universidade de Coimbra — Alta e Sofia: Património Mundial* — `3. FACULDADE DE LETRAS`

**Score guidance:** 2 = apresenta corretamente os três factos; 1 = apresenta corretamente um ou dois; 0 = não apresenta nenhum ou contradiz os dados essenciais.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q07

**Question:** Quando começou a construção do Colégio de São Jerónimo, quem a dirigiu e a que função foi adaptado em 1848?

**Category:** Universidade / monumentos / museus

**Difficulty:** Hard

**Question type:** Factual

**Expected answer:** A construção começou em 1565, sob direção de Diogo de Castilho; em 1848, o edifício foi adaptado a serviços hospitalares, o Hospital Velho.

**Essential facts:**

#### Fact 1

A construção começou em 1565.

**Evidence:**
> O Colégio de S. Jerónimo começou a ser construído sob a direção de Diogo de Castilho, a partir de 1565

**Source:** `universidade-alta-sofia-patrimonio-mundial` — *Universidade de Coimbra — Alta e Sofia: Património Mundial* — `9. COLÉGIO DE SÃO JERÓNIMO`

#### Fact 2

A construção decorreu sob a direção de Diogo de Castilho.

**Evidence:**
> começou a ser construído sob a direção de Diogo de Castilho

**Source:** `universidade-alta-sofia-patrimonio-mundial` — *Universidade de Coimbra — Alta e Sofia: Património Mundial* — `9. COLÉGIO DE SÃO JERÓNIMO`

#### Fact 3

Em 1848 foi adaptado a serviços hospitalares, passando a Hospital Velho.

**Evidence:**
> sendo, em 1848, adaptado a serviços hospitalares (Hospital Velho).

**Source:** `universidade-alta-sofia-patrimonio-mundial` — *Universidade de Coimbra — Alta e Sofia: Património Mundial* — `9. COLÉGIO DE SÃO JERÓNIMO`

**Score guidance:** 2 = indica 1565, Diogo de Castilho e a adaptação a Hospital Velho em 1848; 1 = acerta um ou dois elementos; 0 = nenhum elemento essencial correto.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q08

**Question:** Que três marcos cronológicos descrevem a instalação, extinção e reativação da Imprensa da Universidade de Coimbra?

**Category:** Universidade / monumentos / museus

**Difficulty:** Hard

**Question type:** Enumeration

**Expected answer:** As instalações remontam a 1773, no contexto da Reforma Pombalina; a Imprensa foi extinta em 1934 pelo Estado Novo e reativada no mesmo edifício em 1999.

**Essential facts:**

#### Fact 1

As instalações da Imprensa remontam a 1773, no contexto da Reforma Pombalina.

**Evidence:**
> Com a génese da Reforma Pombalina, em 1773, as instalações da Imprensa ocupavam originalmente uma vasta área

**Source:** `universidade-alta-sofia-patrimonio-mundial` — *Universidade de Coimbra — Alta e Sofia: Património Mundial* — `20. IMPRENSA DA UNIVERSIDADE`

#### Fact 2

A Imprensa foi extinta pelo Estado Novo em 1934.

**Evidence:**
> manteve a função original até 1934, época em que a Imprensa foi extinta pelo Estado Novo.

**Source:** `universidade-alta-sofia-patrimonio-mundial` — *Universidade de Coimbra — Alta e Sofia: Património Mundial* — `20. IMPRENSA DA UNIVERSIDADE`

#### Fact 3

A Imprensa foi reativada no mesmo edifício em 1999.

**Evidence:**
> Em 1999, foi reativada a Imprensa da Universidade no mesmo edifício.

**Source:** `universidade-alta-sofia-patrimonio-mundial` — *Universidade de Coimbra — Alta e Sofia: Património Mundial* — `20. IMPRENSA DA UNIVERSIDADE`

**Score guidance:** 2 = apresenta corretamente os três marcos e respetivo significado; 1 = apresenta corretamente um ou dois; 0 = nenhum marco correto ou cronologia contraditória.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q09

**Question:** Como é preparado o bunho para a cestaria de Arzila e que tipos de peças são produzidos com ele?

**Category:** Cultura / tradições / Fado / artesanato

**Difficulty:** Medium

**Question type:** Descriptive

**Expected answer:** O bunho, planta abundante no Paul de Arzila, é colhido no verão e deixado a secar; depois é usado em peças como cestos, esteiras e outros objetos utilitários.

**Essential facts:**

#### Fact 1

O bunho é uma planta abundante na Reserva Natural do Paul de Arzila.

**Evidence:**
> Esta arte utiliza o bunho, uma planta abundante na Reserva Natural do Paul de Arzila, como matéria-prima essencial.

**Source:** `web-visitecoimbra-cestaria-de-bunho` — *Cestaria de Bunho* — `Cestaria de Bunho`

#### Fact 2

O bunho é colhido no verão e deixado a secar antes de ser trabalhado.

**Evidence:**
> Durante os meses de verão, o bunho é colhido e deixado a secar, preparando-se para ser trabalhado.

**Source:** `web-visitecoimbra-cestaria-de-bunho` — *Cestaria de Bunho* — `Cestaria de Bunho`

#### Fact 3

Com ele são feitos cestos, esteiras e outros objetos utilitários.

**Evidence:**
> As peças, que variam entre cestos, esteiras e outros objetos utilitários

**Source:** `web-visitecoimbra-cestaria-de-bunho` — *Cestaria de Bunho* — `Cestaria de Bunho`

**Score guidance:** 2 = indica o vínculo ao Paul de Arzila, a colheita no verão/secagem e os tipos de peças; 1 = apresenta corretamente um ou dois destes factos; 0 = nenhum facto essencial correto.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q10

**Question:** Para que servia originalmente o Jardim da Sereia e que recinto recreativo possuía?

**Category:** Cultura / tradições / Fado / artesanato

**Difficulty:** Medium

**Question type:** Descriptive

**Expected answer:** Destinava-se sobretudo ao recolhimento e meditação dos crúzios e incluía o recinto do Jogo da Pela para fins recreativos.

**Essential facts:**

#### Fact 1

O parque destinava-se principalmente ao recolhimento e meditação dos crúzios.

**Evidence:**
> O parque destinava-se principalmente ao recolhimento e meditação dos crúzios

**Source:** `coimbra-dos-escritores` — *Coimbra dos Escritores* — `7. JARDIM DA SEREIA`

#### Fact 2

Entre as funções recreativas estava o recinto do Jogo da Pela.

**Evidence:**
> mas tinha também funções recreativas – como por exemplo o conhecido recinto do Jogo da Pela.

**Source:** `coimbra-dos-escritores` — *Coimbra dos Escritores* — `7. JARDIM DA SEREIA`

**Score guidance:** 2 = refere o recolhimento/meditação dos crúzios e o Jogo da Pela; 1 = refere corretamente apenas um; 0 = nenhum elemento correto.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q11

**Question:** Quem criou o Memorial Miguel Torga junto à Ponte de Santa Clara e que elementos materiais o compõem?

**Category:** Cultura / tradições / Fado / artesanato

**Difficulty:** Hard

**Question type:** Descriptive

**Expected answer:** Foi uma obra conjunta do arquiteto José Bandeirinha e do escultor António Olaio. Integra uma passadeira de xisto que termina na palavra “Torga”, esculpida em pedra de Ançã, e tem o poema “Memória” gravado na grade.

**Essential facts:**

#### Fact 1

O Memorial é obra conjunta de José Bandeirinha e António Olaio.

**Evidence:**
> o Memorial Miguel Torga, obra conjunta do arquiteto José Bandeirinha e do escultor António Olaio.

**Source:** `coimbra-dos-escritores` — *Coimbra dos Escritores* — `1. LARGO DA PORTAGEM`

#### Fact 2

É composto por uma passadeira de xisto que culmina na palavra “Torga” em pedra de Ançã.

**Evidence:**
> É constituído por uma passadeira em xisto que culmina, para lá do gradeamento sobranceiro ao rio, com a palavra Torga esculpida em pedra de Ançã.

**Source:** `coimbra-dos-escritores` — *Coimbra dos Escritores* — `1. LARGO DA PORTAGEM`

#### Fact 3

Na grade está gravado o poema “Memória”.

**Evidence:**
> Na grade foi gravado o poema que esteve na origem da criação deste monumento: Memória.

**Source:** `coimbra-dos-escritores` — *Coimbra dos Escritores* — `1. LARGO DA PORTAGEM`

**Score guidance:** 2 = identifica os dois autores e os elementos materiais descritos, incluindo “Torga” e “Memória”; 1 = apresenta corretamente apenas parte substancial destes elementos; 0 = não apresenta os elementos essenciais ou inventa a autoria.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q12

**Question:** Segundo a tradição descrita no corpus, quem protagoniza o Fado de Coimbra e como deve ser usada a capa durante a atuação?

**Category:** Cultura / tradições / Fado / artesanato

**Difficulty:** Easy

**Question type:** Factual

**Expected answer:** Segundo a tradição, é protagonizado somente por homens e, para tocar e cantar, é preciso usar a capa traçada.

**Essential facts:**

#### Fact 1

Segundo a tradição, o Fado de Coimbra é protagonizado somente por homens.

**Evidence:**
> segundo a tradição, protagonizado somente por homens.

**Source:** `web-visitecoimbra-cancao-de-coimbra` — *Canção de Coimbra* — `Canção de Coimbra`

#### Fact 2

Para tocar e cantar Fado de Coimbra é preciso envergar a capa traçada.

**Evidence:**
> para tocar e cantar Fado de Coimbra é preciso envergar a capa, que deve estar traçada.

**Source:** `web-visitecoimbra-cancao-de-coimbra` — *Canção de Coimbra* — `Canção de Coimbra`

**Score guidance:** 2 = refere somente homens e a capa traçada; 1 = refere corretamente apenas um; 0 = nenhum elemento correto ou descrição contraditória.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q13

**Question:** De que convento são originários os Pastéis de Santa Clara e qual é o seu recheio?

**Category:** Gastronomia / restauração

**Difficulty:** Easy

**Question type:** Factual

**Expected answer:** Foram criados no Convento de Santa Clara e são recheados com doce de ovos e amêndoa.

**Essential facts:**

#### Fact 1

Os Pastéis de Santa Clara foram criados no Convento de Santa Clara.

**Evidence:**
> Criados no Convento de Santa Clara

**Source:** `web-visitecoimbra-docaria-conventual-de-coimbra` — *Doçaria Conventual de Coimbra* — `Pastéis de Santa Clara`

#### Fact 2

O recheio é de doce de ovos e amêndoa.

**Evidence:**
> recheada com doce de ovos e amêndoa.

**Source:** `web-visitecoimbra-docaria-conventual-de-coimbra` — *Doçaria Conventual de Coimbra* — `Pastéis de Santa Clara`

**Score guidance:** 2 = indica o Convento de Santa Clara e o recheio de doce de ovos e amêndoa; 1 = indica corretamente apenas a origem ou o recheio; 0 = nenhum elemento correto.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q14

**Question:** Que ingredientes compõem as Barrigas de Freira de Coimbra e que textura lhes é atribuída?

**Category:** Gastronomia / restauração

**Difficulty:** Medium

**Question type:** Descriptive

**Expected answer:** São feitas com gemas, açúcar e pão, e têm uma textura cremosa e delicada.

**Essential facts:**

#### Fact 1

As Barrigas de Freira são feitas com gemas, açúcar e pão.

**Evidence:**
> feitos com gemas, açúcar e pão

**Source:** `web-visitecoimbra-docaria-conventual-de-coimbra` — *Doçaria Conventual de Coimbra* — `Barrigas de Freira`

#### Fact 2

O resultado tem textura cremosa e delicada.

**Evidence:**
> resultando numa textura cremosa e delicada.

**Source:** `web-visitecoimbra-docaria-conventual-de-coimbra` — *Doçaria Conventual de Coimbra* — `Barrigas de Freira`

**Score guidance:** 2 = indica os três ingredientes e a textura cremosa e delicada; 1 = indica corretamente os ingredientes ou a textura, ou omite um ingrediente; 0 = nenhum elemento essencial correto.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q15

**Question:** Quais são os ingredientes do Manjar Branco de Coimbra e com que pode ser aromatizado?

**Category:** Gastronomia / restauração

**Difficulty:** Medium

**Question type:** Factual

**Expected answer:** É feito com leite, açúcar e arroz, e pode ser aromatizado com canela ou limão.

**Essential facts:**

#### Fact 1

O Manjar Branco é feito com leite, açúcar e arroz.

**Evidence:**
> feita com leite, açúcar, arroz

**Source:** `web-visitecoimbra-docaria-conventual-de-coimbra` — *Doçaria Conventual de Coimbra* — `Manjar Branco`

#### Fact 2

É aromatizado com canela ou limão.

**Evidence:**
> aromatizada com canela ou limão.

**Source:** `web-visitecoimbra-docaria-conventual-de-coimbra` — *Doçaria Conventual de Coimbra* — `Manjar Branco`

**Score guidance:** 2 = apresenta leite, açúcar e arroz, mais canela ou limão; 1 = apresenta corretamente apenas os ingredientes-base ou apenas os aromas, ou omite um ingrediente; 0 = nenhum elemento essencial correto.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q16

**Question:** A que época remonta a tradição cervejeira de Coimbra, onde se concentrava a produção e para que fins era feita?

**Category:** Gastronomia / restauração

**Difficulty:** Hard

**Question type:** Descriptive

**Expected answer:** Remonta aos tempos medievais. A produção ocorria especialmente em mosteiros e conventos, onde os monges faziam cerveja para consumo próprio e para comercialização.

**Essential facts:**

#### Fact 1

A ligação de Coimbra à cerveja remonta aos tempos medievais.

**Evidence:**
> Coimbra tem uma forte ligação à cerveja, que remonta aos tempos medievais.

**Source:** `web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira` — *Coimbra: Uma Cidade com Tradição Cervejeira* — `Coimbra: Uma Cidade com Tradição Cervejeira`

#### Fact 2

A produção ocorria especialmente nos mosteiros e conventos.

**Evidence:**
> especialmente nos mosteiros e conventos

**Source:** `web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira` — *Coimbra: Uma Cidade com Tradição Cervejeira* — `Coimbra: Uma Cidade com Tradição Cervejeira`

#### Fact 3

Os monges produziam cerveja para consumo próprio e comercialização.

**Evidence:**
> onde os monges produziam cervejas para consumo próprio e para comercialização.

**Source:** `web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira` — *Coimbra: Uma Cidade com Tradição Cervejeira* — `Coimbra: Uma Cidade com Tradição Cervejeira`

**Score guidance:** 2 = refere a época medieval, os mosteiros/conventos e os dois fins da produção; 1 = apresenta corretamente um ou dois destes factos; 0 = nenhum facto essencial correto.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q17

**Question:** Que duas atividades são explicitamente recomendadas nas margens do rio Ceira?

**Category:** Turismo / lazer / atividades / desporto

**Difficulty:** Easy

**Question type:** Tourist factual recommendation

**Expected answer:** Passeios e piqueniques.

**Essential facts:**

#### Fact 1

As margens do rio Ceira são indicadas para passeios.

**Evidence:**
> As margens do rio Ceira são ideais para passeios

**Source:** `web-visitecoimbra-ceira` — *Ceira* — `Ceira`

#### Fact 2

As margens do rio Ceira são indicadas para piqueniques.

**Evidence:**
> As margens do rio Ceira são ideais para passeios e piqueniques

**Source:** `web-visitecoimbra-ceira` — *Ceira* — `Ceira`

**Score guidance:** 2 = indica passeios e piqueniques; 1 = indica corretamente apenas uma atividade; 0 = nenhuma das duas ou recomendações sem suporte.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q18

**Question:** O que existia na Ínsua dos Bentos quando a Câmara a comprou em 1888 e quem ficou encarregado do projeto para a transformar em jardim público?

**Category:** Turismo / lazer / atividades / desporto

**Difficulty:** Hard

**Question type:** Descriptive

**Expected answer:** Havia uma zona de laranjais, uma área descampada usada para corridas de cavalos e, a nascente, um campo de futebol onde jogava a Académica. O projeto do jardim público ficou a cargo de Jacinto de Matos.

**Essential facts:**

#### Fact 1

A Ínsua dos Bentos tinha uma zona de laranjais.

**Evidence:**
> constituída por uma zona de laranjais

**Source:** `coimbra-dos-escritores` — *Coimbra dos Escritores* — `2. PARQUE DR. MANUEL BRAGA`

#### Fact 2

Tinha uma área descampada para corridas de cavalos e, a nascente, um campo de futebol onde a Académica jogava.

**Evidence:**
> área descampada onde se realizaram corridas de cavalos e, a nascente ficava um campo de futebol, onde a Académica jogava.

**Source:** `coimbra-dos-escritores` — *Coimbra dos Escritores* — `2. PARQUE DR. MANUEL BRAGA`

#### Fact 3

Jacinto de Matos ficou encarregado do projeto de transformação em jardim público.

**Evidence:**
> ficando encarregue do projeto o paisagista floricultor portuense, Jacinto de Matos.

**Source:** `coimbra-dos-escritores` — *Coimbra dos Escritores* — `2. PARQUE DR. MANUEL BRAGA`

**Score guidance:** 2 = refere laranjais, corridas/campo da Académica e Jacinto de Matos; 1 = apresenta corretamente um ou dois destes blocos factuais; 0 = nenhum elemento essencial correto.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q19

**Question:** Quando e em que contexto universitário foi criado o Jardim Botânico de Coimbra, e que escritor o menciona numa obra?

**Category:** Turismo / lazer / atividades / desporto

**Difficulty:** Medium

**Question type:** Factual

**Expected answer:** Foi criado em 1772, durante a Reforma Pombalina da Universidade de Coimbra; Miguel Torga menciona o jardim e a vista sobre o rio no *Terceiro Dia d’ A Criação do Mundo*.

**Essential facts:**

#### Fact 1

O Jardim Botânico foi criado em 1772 durante a Reforma Pombalina da Universidade de Coimbra.

**Evidence:**
> O Jardim Botânico foi criado, em 1772, durante a Reforma Pombalina da Universidade de Coimbra.

**Source:** `coimbra-dos-escritores` — *Coimbra dos Escritores* — `4. JARDIM BOTÂNICO`

#### Fact 2

Miguel Torga menciona o jardim e a vista sobre o rio no *Terceiro Dia d’ A Criação do Mundo*.

**Evidence:**
> Miguel Torga que menciona este jardim e a vista sobre o rio no Terceiro Dia d’ A Criação do Mundo.

**Source:** `coimbra-dos-escritores` — *Coimbra dos Escritores* — `4. JARDIM BOTÂNICO`

**Score guidance:** 2 = indica 1772/Reforma Pombalina e Miguel Torga com a obra; 1 = apresenta corretamente apenas um dos dois factos ou omite o título; 0 = nenhum elemento essencial correto.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

### Q20

**Question:** Onde se realiza a Regata da Queima das Fitas, quem compete e o que o evento celebra?

**Category:** Turismo / lazer / atividades / desporto

**Difficulty:** Medium

**Question type:** Tourist factual recommendation / Descriptive

**Expected answer:** Realiza-se no rio Mondego; equipas de remo da Associação Académica de Coimbra competem com equipas convidadas; o evento celebra o desporto e o espírito académico.

**Essential facts:**

#### Fact 1

A Regata da Queima das Fitas realiza-se no rio Mondego.

**Evidence:**
> A Regata da Queima das Fitas, realizada no Rio Mondego

**Source:** `web-visitecoimbra-desporto` — *Desporto* — `Desporto`

#### Fact 2

Competem equipas de remo da Associação Académica de Coimbra e equipas convidadas.

**Evidence:**
> as equipas de remo da Associação Académica de Coimbra competem contra equipas convidadas

**Source:** `web-visitecoimbra-desporto` — *Desporto* — `Desporto`

#### Fact 3

O evento celebra o desporto e o espírito académico.

**Evidence:**
> celebrando o desporto e o espírito académico

**Source:** `web-visitecoimbra-desporto` — *Desporto* — `Desporto`

**Score guidance:** 2 = indica o Mondego, os dois grupos de equipas e a celebração do desporto/espírito académico; 1 = apresenta corretamente um ou dois destes factos; 0 = nenhum facto essencial correto.

**Previously used in smoke tests:** No

**Corpus answerable:** YES

**Requires inference:** NO

## 6. Coverage Summary

### Category distribution

| Category | Questions | Count |
|---|---|---:|
| História e património | Q01–Q04 | 4 |
| Universidade / monumentos / museus | Q05–Q08 | 4 |
| Cultura / tradições / Fado / artesanato | Q09–Q12 | 4 |
| Gastronomia / restauração | Q13–Q16 | 4 |
| Turismo / lazer / atividades / desporto | Q17–Q20 | 4 |

### Difficulty distribution

| Difficulty | Questions | Count |
|---|---|---:|
| Easy | Q01, Q04, Q05, Q12, Q13, Q17 | 6 |
| Medium | Q02, Q03, Q09, Q10, Q14, Q15, Q19, Q20 | 8 |
| Hard | Q06, Q07, Q08, Q11, Q16, Q18 | 6 |

The final 6/8/6 split meets the target without artificial reasoning: “Hard” means only that the answer contains three explicit facts from the same passage.

### Question type distribution

| Question type | Count |
|---|---:|
| Factual | 8 |
| Descriptive | 6 |
| Enumeration | 4 |
| Tourist factual recommendation | 2 |

Questions with a combined label are counted once under their principal type.

### Source coverage

| Measure | Count |
|---|---:|
| Questions supported by PDF-derived documents | 10 |
| Questions supported by Web documents | 10 |
| Different corpus documents used | 12 |
| Questions fully answerable from one document | 20/20 |
| Questions requiring multiple documents | 0/20 |

There are no multi-document questions; consequently, no relationship depends on combining independent sources.

## 7. Fact-level Corpus Support Audit

| Q | Essential facts | All have direct evidence | Requires inference | Valid |
|---|---:|---|---|---|
| Q01 | 2 | YES | NO | YES |
| Q02 | 2 | YES | NO | YES |
| Q03 | 2 | YES | NO | YES |
| Q04 | 2 | YES | NO | YES |
| Q05 | 2 | YES | NO | YES |
| Q06 | 3 | YES | NO | YES |
| Q07 | 3 | YES | NO | YES |
| Q08 | 3 | YES | NO | YES |
| Q09 | 3 | YES | NO | YES |
| Q10 | 2 | YES | NO | YES |
| Q11 | 3 | YES | NO | YES |
| Q12 | 2 | YES | NO | YES |
| Q13 | 2 | YES | NO | YES |
| Q14 | 2 | YES | NO | YES |
| Q15 | 2 | YES | NO | YES |
| Q16 | 3 | YES | NO | YES |
| Q17 | 2 | YES | NO | YES |
| Q18 | 3 | YES | NO | YES |
| Q19 | 2 | YES | NO | YES |
| Q20 | 3 | YES | NO | YES |
| **Total** | **48** | **YES — 48/48** | **NO — 0/20** | **YES — 20/20** |

## 8. Final Checks

The sources cited above were reopened after question drafting. Every Evidence excerpt was checked against the named Markdown file and every Essential Fact was tested with the question: “If I knew only what is written in this passage, could I assert this fact?” All 48 answers were YES. A literal automated check also confirmed that every Evidence excerpt exists in its named source.

- TOTAL QUESTIONS: 20
- TOTAL CORPUS DOCUMENTS READ: 35
- QUESTIONS WITH ALL ESSENTIAL FACTS DIRECTLY SUPPORTED: 20/20
- ESSENTIAL FACTS WITH DIRECT TEXTUAL EVIDENCE: 48/48
- QUESTIONS REQUIRING INFERENCE: 0/20
- QUESTIONS DEPENDING ON EXTERNAL KNOWLEDGE: 0/20
- QUESTIONS WITH VOLATILE INFORMATION: 0/20
- QUESTIONS REUSED FROM SMOKE TESTS: 0/20
- QUESTIONS EXECUTED AGAINST RAG: 0
- QUESTIONS EXECUTED AGAINST NO-RAG: 0
