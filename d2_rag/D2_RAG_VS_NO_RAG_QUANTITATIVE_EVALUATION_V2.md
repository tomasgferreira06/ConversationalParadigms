# D2 — Avaliação Quantitativa da Qualidade das Respostas: RAG vs No-RAG

## 1. Objetivo

> “Quantitative comparison of answer quality with and without RAG is required.”


A experiência compara 20 perguntas idênticas, executadas uma vez em cada condição, com o mesmo LLM (`llama3.2:3b`) e a mesma temperatura (0.1). A principal diferença experimental é o retrieval e o contexto: No-RAG recebe apenas a pergunta; RAG recebe também os três chunks devolvidos pela pipeline congelada. A única métrica é Answer Quality Score, de 0 a 2.

## 2. Validação do Conjunto de Avaliação

- 20/20 perguntas diretamente respondíveis pelo corpus.
- 48/48 Factos Essenciais com evidência textual direta.
- 0/20 perguntas requerem inferência.
- O benchmark V2 foi congelado antes da execução e permaneceu inalterado.
- As 40 respostas foram geradas e guardadas antes do scoring.

## 3. Configuração Experimental

| Configuração | NO-RAG | RAG |
|---|---|---|
| LLM | `llama3.2:3b` | `llama3.2:3b` |
| Temperatura | 0.1 | 0.1 |
| Perguntas | 20, Q01–Q20 | 20, Q01–Q20 |
| Histórico | Nenhum; chamadas independentes | Nenhum; chamadas independentes |
| Retrieval | Nenhum | Pipeline congelada, cosine distance |
| Embedding | Nenhum | `Qwen/Qwen3-Embedding-0.6B` |
| Vector store | Nenhum | Cópia de runtime de `chroma_frozen_v2` / `coimbra_rag_frozen_v2` |
| Top-k | N/A | 3 |
| Acesso ao corpus | Nenhum | Apenas contexto recuperado |

A vector store original protegida foi copiada antes de ser aberta. A respetiva collection continha 348 chunks de conteúdo; `build_store` e a reconstrução dos embeddings não foram executados.

## 4. Answer Quality Score

| Score | Classificação | Definição |
|---:|---|---|
| 0 | INCORRETA | Errada, contraditória, com invenção relevante ou sem resposta efetiva. |
| 1 | PARCIALMENTE CORRETA | Contém informação relevante e correta, mas está incompleta ou tem imprecisão que não destrói a ideia principal. |
| 2 | CORRETA | Correta, adequada, com todos os elementos essenciais e sem erros relevantes. |

O scoring foi uma **avaliação automatizada baseada na rubrica e nas regras de scoring 0–2 previamente definidas**, efetuada pela sessão do agente de código depois de concluída a generation. Não foi utilizada avaliação humana, API externa nem um LLM-as-Judge adicional.

## 5. Prompt No-RAG

Prompt de sistema exato:

```text
És um assistente especializado em turismo, história, património, cultura e gastronomia de Coimbra.
Responde em Português de Portugal, de forma clara, direta e concisa.
Não inventes informação. Se não tiveres conhecimento suficiente para responder com segurança, diz que não sabes.
```

## 6. Resultados Pergunta a Pergunta

### Q01 — Que dois contributos são atribuídos a D. Dinis no Largo que o homenageia em Coimbra?

**Factos Essenciais**

- D. Dinis foi responsável pela fundação dos Estudos Gerais.
- A D. Dinis é atribuída a introdução do idioma português na documentação oficial.

#### NO-RAG

**Resposta**

> No Largo D. Dinis, em Coimbra, estão os dois contributos atribuídos a D. Dinis:
>
> 1.  A Basílica de Santa Cruz, que foi construída durante o reinado de D. Dinis, e que é considerada uma das mais importantes igrejas góticas de Portugal.
> 2.  A Universidade de Coimbra, que foi fundada em 1290, durante o reinado de D. Dinis, e que é uma das mais antigas e respeitadas universidades de Portugal.

**Resultado:** PARCIALMENTE CORRETA (1/2)

**Justificação:** Atribui corretamente a D. Dinis a fundação da Universidade/Estudos Gerais, mas omite a introdução do português na documentação oficial e acrescenta incorretamente Santa Cruz.

#### RAG

**Resposta**

> Com base no contexto fornecido, podemos concluir que D. Dinis é homenageado no Largo que o leva o nome, e que dois dos seus contributos são:
>
> 1. A fundação dos Estudos Gerais em Coimbra;
> 2. A introdução do idioma português na documentação oficial.
>
> Ambos os contributos são mencionados em diferentes fontes: Fonte 1 (Coimbra dos Escritores) e Fonte 2 (Viver o Património em Coimbra), embora com algumas variações de detalhes. Não há informações divergentes sobre os contributos de D. Dinis no Largo que o homenageia.

**Resultado:** CORRETA (2/2)

**Justificação:** Identifica corretamente a fundação dos Estudos Gerais e a introdução do português na documentação oficial.

**Contexto recuperado**

1. `coimbra-dos-escritores` — 3. LARGO D. DINIS — distance 0.237380
2. `viver-o-patrimonio-em-coimbra` — 2. LARGO D. DINIS — distance 0.251801
3. `universidade-alta-sofia-patrimonio-mundial` — 1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS > PORTA FÉRREA — distance 0.412666

### Q02 — Em que instituição de Coimbra ingressou Fernando de Bulhões e que decisão transformadora tomou depois na cidade?

**Factos Essenciais**

- Fernando de Bulhões ingressou no Mosteiro de Santa Cruz, em Coimbra.
- Em Coimbra, decidiu tornar-se franciscano e adotar o nome de António.

#### NO-RAG

**Resposta**

> Fernando de Bulhões ingressou na Universidade de Coimbra. A decisão transformadora que tomou na cidade foi a fundação da Universidade de Coimbra, que se tornou um centro de aprendizado e cultura importante na história de Portugal.

**Resultado:** INCORRETA (0/2)

**Justificação:** Indica erradamente a Universidade de Coimbra e a sua fundação; não refere o Mosteiro de Santa Cruz nem a decisão franciscana e o nome António.

#### RAG

**Resposta**

> De acordo com o contexto fornecido, Fernando de Bulhões ingressou no Mosteiro de Santa Cruz, uma das instituições religiosas e intelectuais mais prestigiadas da época, em Coimbra.
>
> A decisão transformadora que tomou Fernando de Bulhões foi adotar o nome de António e se tornar franciscano, que foi tomada em Coimbra.

**Resultado:** CORRETA (2/2)

**Justificação:** Refere corretamente o ingresso no Mosteiro de Santa Cruz e a decisão de se tornar franciscano e adotar o nome António.

**Contexto recuperado**

1. `web-visitecoimbra-santo-antonio` — (sem secção) — distance 0.276914
2. `fundacao-da-nacionalidade` — (sem secção) — distance 0.404052
3. `web-visitecoimbra-coimbra-muralhada` — (sem secção) — distance 0.415219

### Q03 — Em que séculos Coimbra esteve sob domínio mouro e que duas igrejas são apontadas como exemplos de influência moçárabe?

**Factos Essenciais**

- O domínio mouro referido ocorreu durante os séculos VIII e IX.
- As igrejas de São Salvador e São Bartolomeu exibem influências moçárabes.

#### NO-RAG

**Resposta**

> Coimbra esteve sob domínio mouro de 8 a 1249. 
>
> Duas igrejas que são apontadas como exemplos de influência moçárabe são a Sé Velha e a Igreja de São Francisco.

**Resultado:** INCORRETA (0/2)

**Justificação:** Apresenta um período incorreto e nomeia a Sé Velha e São Francisco, em vez de São Salvador e São Bartolomeu.

#### RAG

**Resposta**

> Coimbra esteve sob domínio mouro nos séculos VIII e IX. As duas igrejas que são apontadas como exemplos de influência moçárabe são a Igreja de São Salvador e a Igreja de São Bartolomeu.

**Resultado:** CORRETA (2/2)

**Justificação:** Indica corretamente os séculos VIII e IX e as igrejas de São Salvador e São Bartolomeu.

**Contexto recuperado**

1. `web-visitecoimbra-heranca-mocarabe` — (sem secção) — distance 0.183201
2. `web-visitecoimbra-heranca-cultural-e-religiosa` — (sem secção) — distance 0.328858
3. `web-visitecoimbra-heranca-cultural-e-religiosa` — Igrejas e Mosteiros > Mosteiro de São Francisco — distance 0.334119

### Q04 — Entre que anos foi construída a Estação Nova de Coimbra e quem assinou o projeto?

**Factos Essenciais**

- A Estação Nova foi construída entre 1925 e 1931.
- O projeto foi dos arquitetos Cotinelli Telmo e Luís Cunha.

#### NO-RAG

**Resposta**

> A Estação Nova de Coimbra foi construída entre 1906 e 1910.

**Resultado:** INCORRETA (0/2)

**Justificação:** Indica o intervalo errado, 1906–1910, e não identifica os arquitetos.

#### RAG

**Resposta**

> Com base no contexto fornecido, a Estação Nova de Coimbra foi construída entre 1925 e 1931, com projeto dos arquitetos Cotinelli Telmo e Luís Cunha.

**Resultado:** CORRETA (2/2)

**Justificação:** Indica corretamente 1925–1931 e os arquitetos Cotinelli Telmo e Luís Cunha.

**Contexto recuperado**

1. `viver-o-patrimonio-em-coimbra` — 11. LARGO DAS AMEIAS | CAIS DAS AMEIAS — distance 0.287315
2. `web-visitecoimbra-heranca-cultural-e-religiosa` — Igrejas e Mosteiros > Sé Nova de Coimbra — distance 0.328404
3. `web-visitecoimbra-heranca-cultural-e-religiosa` — A Universidade de Coimbra e os Colégios da Baixa > Colégio Novo, de Santo Agostinho ou da Sapiência — distance 0.365780

### Q05 — Quais eram as duas principais funções do Piso Intermédio da Biblioteca Joanina?

**Factos Essenciais**

- O Piso Intermédio apoiava os guardas que vigiavam a Prisão Académica.
- Funcionava como depósito dos livros lidos no Piso Nobre.

#### NO-RAG

**Resposta**

> Não tenho conhecimento suficiente para responder com segurança sobre as duas principais funções do Piso Intermédio da Biblioteca Joanina.

**Resultado:** INCORRETA (0/2)

**Justificação:** Declara não saber e não apresenta nenhuma das duas funções do Piso Intermédio.

#### RAG

**Resposta**

> Com base no contexto fornecido, as duas principais funções do Piso Intermédio da Biblioteca Joanina eram:
>
> 1. Servir de apoio aos guardas que vigiavam a prisão académica (extinta em 1834).
> 2. Funcionar como depósito dos livros que eram lidos no piso nobre.
>
> Não há informações suficientes no contexto para identificar outras funções específicas do Piso Intermédio.

**Resultado:** CORRETA (2/2)

**Justificação:** Refere corretamente o apoio aos guardas da Prisão Académica e o depósito dos livros lidos no Piso Nobre.

**Contexto recuperado**

1. `biblioteca-joanina-uctour` — Piso Intermédio — distance 0.140131
2. `biblioteca-joanina-uctour` — Biblioteca Joanina — distance 0.317943
3. `biblioteca-joanina-uctour` — Piso Intermédio — distance 0.355570

### Q06 — Quando foi criada a Faculdade de Letras de Coimbra, a que faculdade sucedeu e quando foi inaugurado o novo edifício?

**Factos Essenciais**

- A Faculdade de Letras foi criada em 1911.
- A Faculdade de Letras sucedeu à antiga Faculdade de Teologia.
- O novo edifício foi inaugurado em 22 de novembro de 1951.

#### NO-RAG

**Resposta**

> A Faculdade de Letras de Coimbra foi criada em 1290, pelo rei D. Dinis, como uma das primeiras faculdades da Universidade de Coimbra.
>
> A faculdade sucedeu a Escola de Filosofia, que foi fundada em 1290, mas que não tinha o estatuto de faculdade.
>
> O novo edifício da Faculdade de Letras de Coimbra foi inaugurado em 2009, após uma reforma e expansão que permitiu a criação de novos espaços de ensino e pesquisa.

**Resultado:** INCORRETA (0/2)

**Justificação:** Erra os três elementos: data de criação, faculdade antecedente e data de inauguração.

#### RAG

**Resposta**

> Com base no contexto fornecido, a Faculdade de Letras de Coimbra foi criada em 1911, sucedendo à antiga Faculdade de Teologia. O novo edifício, projetado por Alberto Pessoa, foi inaugurado em 22 de novembro de 1951.

**Resultado:** CORRETA (2/2)

**Justificação:** Apresenta corretamente 1911, a antiga Faculdade de Teologia e 22 de novembro de 1951.

**Contexto recuperado**

1. `universidade-alta-sofia-patrimonio-mundial` — 3. FACULDADE DE LETRAS — distance 0.228918
2. `universidade-alta-sofia-patrimonio-mundial` — 1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS > PRISÃO ACADÉMICA — distance 0.270942
3. `universidade-alta-sofia-patrimonio-mundial` — 1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS > AUDITÓRIO DA FACULDADE DE DIREITO — distance 0.274865

### Q07 — Quando começou a construção do Colégio de São Jerónimo, quem a dirigiu e a que função foi adaptado em 1848?

**Factos Essenciais**

- A construção começou em 1565.
- A construção decorreu sob a direção de Diogo de Castilho.
- Em 1848 foi adaptado a serviços hospitalares, passando a Hospital Velho.

#### NO-RAG

**Resposta**

> Não tenho informações suficientes para responder com segurança à sua pergunta. Não sei quem dirigiu a construção do Colégio de São Jerónimo ou a função para a qual foi adaptado em 1848. Se precisar de mais informações, posso tentar ajudar.

**Resultado:** INCORRETA (0/2)

**Justificação:** Declara não saber e não apresenta nenhum dos três factos essenciais.

#### RAG

**Resposta**

> Não tenho informação suficiente no contexto disponível para responder com segurança.

**Resultado:** INCORRETA (0/2)

**Justificação:** Abstém-se apesar de o contexto recuperado conter os factos; não apresenta 1565, Diogo de Castilho nem a adaptação a Hospital Velho em 1848.

**Contexto recuperado**

1. `universidade-alta-sofia-patrimonio-mundial` — 9. COLÉGIO DE SÃO JERÓNIMO — distance 0.177008
2. `universidade-alta-sofia-patrimonio-mundial` — 30. COLÉGIO DE SÃO PEDRO DOS RELIGIOSOS TERCEIROS — distance 0.366661
3. `universidade-alta-sofia-patrimonio-mundial` — 29. COLÉGIO DE NOSSA SENHORA DA GRAÇA — distance 0.372510

### Q08 — Que três marcos cronológicos descrevem a instalação, extinção e reativação da Imprensa da Universidade de Coimbra?

**Factos Essenciais**

- As instalações da Imprensa remontam a 1773, no contexto da Reforma Pombalina.
- A Imprensa foi extinta pelo Estado Novo em 1934.
- A Imprensa foi reativada no mesmo edifício em 1999.

#### NO-RAG

**Resposta**

> A Imprensa da Universidade de Coimbra foi um jornal universitário fundado em 1911. Os três marcos cronológicos que descrevem a instalação, extinção e reativação da Imprensa da Universidade de Coimbra são:
>
> 1. 1911: Fundação da Imprensa da Universidade de Coimbra.
> 2. 1934: A Imprensa da Universidade de Coimbra foi extinta.
> 3. 1999: A Imprensa da Universidade de Coimbra foi reativaada.

**Resultado:** PARCIALMENTE CORRETA (1/2)

**Justificação:** Acerta a extinção em 1934 e a reativação em 1999, mas erra o primeiro marco, indicando 1911 em vez de 1773.

#### RAG

**Resposta**

> Com base no contexto fornecido, os três marcos cronológicos que descrevem a instalação, extinção e reativação da Imprensa da Universidade de Coimbra são:
>
> 1. 1773: A Imprensa foi transferida para o edifício originalmente ocupado por uma vasta área do espaço claustral da Sé e do novo edifício oitocentista.
> 2. 1934: A Imprensa foi extinta pelo Estado Novo.
> 3. 1999: A Imprensa da Universidade foi reativada no mesmo edifício.

**Resultado:** CORRETA (2/2)

**Justificação:** Apresenta os três marcos: 1773, extinção em 1934 pelo Estado Novo e reativação no mesmo edifício em 1999.

**Contexto recuperado**

1. `universidade-alta-sofia-patrimonio-mundial` — 20. IMPRENSA DA UNIVERSIDADE — distance 0.244227
2. `universidade-alta-sofia-patrimonio-mundial` — 1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS > PRISÃO ACADÉMICA — distance 0.339157
3. `coimbra-dos-escritores` — (sem secção) — distance 0.339381

### Q09 — Como é preparado o bunho para a cestaria de Arzila e que tipos de peças são produzidos com ele?

**Factos Essenciais**

- O bunho é uma planta abundante na Reserva Natural do Paul de Arzila.
- O bunho é colhido no verão e deixado a secar antes de ser trabalhado.
- Com ele são feitos cestos, esteiras e outros objetos utilitários.

#### NO-RAG

**Resposta**

> Peço desculpas, mas não tenho informações específicas sobre a preparação do "bunho" na cestaria de Arzila. A Arzila é uma região do Portugal, mais precisamente do distrito de Leiria, conhecida por sua produção de cestas e outros artigos de tecido, mas não consegui encontrar informações sobre um produto específico chamado "bunho" na sua produção.
>
> Se você tiver mais informações ou contexto sobre o "bunho" e a sua relação com a Arzila, ficarei feliz em tentar ajudar. Até lá, não tenho conhecimento suficiente para responder com segurança.

**Resultado:** INCORRETA (0/2)

**Justificação:** Declara não conhecer o processo e não apresenta nenhum Essential Fact; acrescenta ainda uma localização errada para Arzila.

#### RAG

**Resposta**

> Com base no contexto fornecido, não há informações suficientes para responder com segurança sobre como é preparado o bunho para a cestaria de Arzila. O contexto apenas menciona que o bunho é colhido durante os meses de verão e deixado a secar, mas não fornece detalhes sobre o processo de preparação.
>
> No entanto, é possível concluir que o bunho é utilizado como matéria-prima essencial para a criação de peças, como cestos, esteiras e outros objetos utilitários, que são elaborados com técnicas ancestrais. Além disso, o contexto menciona que o bunho é utilizado para criar peças únicas que combinam funcionalidade e história.

**Resultado:** PARCIALMENTE CORRETA (1/2)

**Justificação:** Refere a colheita no verão, a secagem e as peças produzidas, mas omite que o bunho é abundante na Reserva Natural do Paul de Arzila.

**Contexto recuperado**

1. `web-visitecoimbra-cestaria-de-bunho` — (sem secção) — distance 0.162571
2. `web-visitecoimbra-cestaria-de-bunho` — (sem secção) — distance 0.203020
3. `web-visitecoimbra-cestaria-de-bunho` — (sem secção) — distance 0.275081

### Q10 — Para que servia originalmente o Jardim da Sereia e que recinto recreativo possuía?

**Factos Essenciais**

- O parque destinava-se principalmente ao recolhimento e meditação dos crúzios.
- Entre as funções recreativas estava o recinto do Jogo da Pela.

#### NO-RAG

**Resposta**

> O Jardim da Sereia, localizado na Universidade de Coimbra, tinha origem como um jardim de árvores e um local de estudo, mas também servia como um espaço de recreação para os estudantes da universidade.

**Resultado:** INCORRETA (0/2)

**Justificação:** Não refere o recolhimento e meditação dos crúzios nem o recinto do Jogo da Pela.

#### RAG

**Resposta**

> Com base no contexto fornecido, o Jardim da Sereia servia originalmente para o recolhimento e meditação dos crúzios, mas também tinha funções recreativas, incluindo o recinto do Jogo da Pela.

**Resultado:** CORRETA (2/2)

**Justificação:** Refere corretamente o recolhimento e meditação dos crúzios e o recinto do Jogo da Pela.

**Contexto recuperado**

1. `jardins-historicos` — 7. JARDIM DA SEREIA | PARQUE DE SANTA CRUZ — distance 0.255132
2. `coimbra-dos-escritores` — 7. JARDIM DA SEREIA — distance 0.313636
3. `jardins-historicos` — (sem secção) — distance 0.395115

### Q11 — Quem criou o Memorial Miguel Torga junto à Ponte de Santa Clara e que elementos materiais o compõem?

**Factos Essenciais**

- O Memorial é obra conjunta de José Bandeirinha e António Olaio.
- É composto por uma passadeira de xisto que culmina na palavra “Torga” em pedra de Ançã.
- Na grade está gravado o poema “Memória”.

#### NO-RAG

**Resposta**

> O Memorial Miguel Torga, localizado junto à Ponte de Santa Clara, foi criado pelo escritor Miguel Torga. 
>
> O Memorial é composto por uma escultura de bronze de Miguel Torga, criada pelo escultor Fernando Palmeirim, e uma placa com a inscrição do nome do autor.

**Resultado:** INCORRETA (0/2)

**Justificação:** Inventa a autoria e os elementos materiais, sem identificar José Bandeirinha, António Olaio, a passadeira, a palavra Torga ou o poema Memória.

#### RAG

**Resposta**

> Não tenho informação suficiente no contexto disponível para responder com segurança.
>
> O contexto menciona que o Memorial Miguel Torga foi inaugurado em 2007, mas não fornece informações sobre quem o criou. Além disso, não há informações sobre os elementos materiais que o compõem.

**Resultado:** INCORRETA (0/2)

**Justificação:** Abstém-se e não apresenta qualquer Essential Fact, embora o primeiro chunk recuperado contenha a informação.

**Contexto recuperado**

1. `coimbra-dos-escritores` — 1. LARGO DA PORTAGEM — distance 0.344379
2. `coimbra-dos-escritores` — 14. CASA-MUSEU MIGUEL TORGA — distance 0.414546
3. `web-visitecoimbra-museus` — Casa Museu Miguel Torga — distance 0.443304

### Q12 — Segundo a tradição descrita no corpus, quem protagoniza o Fado de Coimbra e como deve ser usada a capa durante a atuação?

**Factos Essenciais**

- Segundo a tradição, o Fado de Coimbra é protagonizado somente por homens.
- Para tocar e cantar Fado de Coimbra é preciso envergar a capa traçada.

#### NO-RAG

**Resposta**

> Não tenho conhecimento suficiente para responder com segurança sobre a tradição específica do Fado de Coimbra, incluindo quem protagoniza a atuação e como deve ser usada a capa durante a atuação. Se quiseres mais informações sobre o Fado de Coimbra, posso tentar ajudar com o que sei.

**Resultado:** INCORRETA (0/2)

**Justificação:** Declara não saber e não apresenta nenhum dos dois factos essenciais.

#### RAG

**Resposta**

> De acordo com o contexto fornecido, o Fado de Coimbra é protagonizado pelos estudantes da Universidade de Coimbra. Durante as Serenatas Monumentais, os estudantes devem estar de capa traçada, manter o silêncio e não aplaudir. Nas Serenatas de Rua, a capa também se mantém traçada.

**Resultado:** PARCIALMENTE CORRETA (1/2)

**Justificação:** Refere corretamente a capa traçada, mas diz apenas que os protagonistas são estudantes e omite que, segundo a tradição descrita, são somente homens.

**Contexto recuperado**

1. `fado-e-tradicoes-academicas` — (sem secção) — distance 0.269800
2. `fado-e-tradicoes-academicas` — (sem secção) — distance 0.290685
3. `web-visitecoimbra-cancao-de-coimbra` — Casas para ouvir a Canção de Coimbra — distance 0.317539

### Q13 — De que convento são originários os Pastéis de Santa Clara e qual é o seu recheio?

**Factos Essenciais**

- Os Pastéis de Santa Clara foram criados no Convento de Santa Clara.
- O recheio é de doce de ovos e amêndoa.

#### NO-RAG

**Resposta**

> Os Pastéis de Santa Clara são originários do Convento de Santa Clara, em Coimbra. O seu recheio é composto por queijo de cabra, ovos, cebola e azeite.

**Resultado:** PARCIALMENTE CORRETA (1/2)

**Justificação:** Identifica corretamente o Convento de Santa Clara, mas dá um recheio salgado incorreto em vez de doce de ovos e amêndoa.

#### RAG

**Resposta**

> Os Pastéis de Santa Clara são originários do Convento de Santa Clara-a-Velha. O seu recheio é doce de ovos e amêndoa.

**Resultado:** CORRETA (2/2)

**Justificação:** Identifica a origem em Santa Clara e o recheio correto de doce de ovos e amêndoa.

**Contexto recuperado**

1. `web-visitecoimbra-docaria-conventual-de-coimbra` — Doces a não perder > Pastéis de Santa Clara — distance 0.170311
2. `web-visitecoimbra-docaria-conventual-de-coimbra` — Sabia que... — distance 0.327144
3. `web-visitecoimbra-docaria-conventual-de-coimbra` — (sem secção) — distance 0.343060

### Q14 — Que ingredientes compõem as Barrigas de Freira de Coimbra e que textura lhes é atribuída?

**Factos Essenciais**

- As Barrigas de Freira são feitas com gemas, açúcar e pão.
- O resultado tem textura cremosa e delicada.

#### NO-RAG

**Resposta**

> As Barrigas de Freira são um prato típico da cozinha portuguesa, originário da região de Coimbra, e são frequentemente associadas à gastronomia da cidade.
>
> As Barrigas de Freira são feitas com carne de porco, mais especificamente com carne de porco moída, e são compostas por vários ingredientes, incluindo:
>
> *   Carne de porco moída
> *   Cebola picada
> *   Azeite
> *   Vinho branco
> *   Pimenta-do-reino
> *   Sal
> *   Pimenta preta
> *   Alho picado
> *   Batata-doce picada
> *   Ovos cozidos
> *   Farinha de trigo
> *   Leite
> *   Queijo de cabra
>
> A textura das Barrigas de Freira é geralmente suave e cremosa, graças à presença de ovos cozidos e leite, que ajudam a dar uma consistência mais homogênea e agradável ao paladar.

**Resultado:** INCORRETA (0/2)

**Justificação:** Embora use a palavra cremosa, classifica erradamente o doce como prato de carne e inventa uma extensa lista de ingredientes relevantes.

#### RAG

**Resposta**

> Com base no contexto fornecido, as Barrigas de Freira de Coimbra são compostas por gemas, açúcar e pão. A sua textura é descrita como cremosa e delicada.

**Resultado:** CORRETA (2/2)

**Justificação:** Indica corretamente gemas, açúcar e pão, bem como a textura cremosa e delicada.

**Contexto recuperado**

1. `web-visitecoimbra-docaria-conventual-de-coimbra` — Doces a não perder > Barrigas de Freira — distance 0.137035
2. `viver-o-patrimonio-em-coimbra` — 13. LARGO DA FREIRIA — distance 0.380456
3. `web-visitecoimbra-gastronomia-em-coimbra` — (sem secção) — distance 0.391662

### Q15 — Quais são os ingredientes do Manjar Branco de Coimbra e com que pode ser aromatizado?

**Factos Essenciais**

- O Manjar Branco é feito com leite, açúcar e arroz.
- É aromatizado com canela ou limão.

#### NO-RAG

**Resposta**

> O Manjar Branco de Coimbra é um doce tradicional da região de Coimbra, na Portugal.
>
> Os ingredientes tradicionais do Manjar Branco de Coimbra incluem:
>
> * Arroz
> * Açúcar
> * Leite
> * Ovos
> * Canela
> * Noz-moscada
> * Amêndoas
>
> O Manjar Branco de Coimbra pode ser aromatizado com várias especiarias e sabores, como:
>
> * Canela em pó
> * Noz-moscada em pó
> * Cardamomo
> * Amêndoas torradas
> * Citrinos (como limão ou laranja)
> * Frutas secas (como amêndoas, nozes ou passas)
>
> É importante notar que a receita tradicional do Manjar Branco de Coimbra pode variar ligeiramente dependendo da região e da família. Além disso, alguns cozinheiros modernos podem adicionar ingredientes adicionais ou criar suas próprias variações do receita.

**Resultado:** PARCIALMENTE CORRETA (1/2)

**Justificação:** Inclui leite, açúcar, arroz, canela e limão, mas acrescenta vários ingredientes e aromas não suportados, impedindo uma classificação totalmente correta.

#### RAG

**Resposta**

> Com base no contexto fornecido, os ingredientes do Manjar Branco de Coimbra são:
>
> - Leite
> - Açúcar
> - Arroz
>
> O Manjar Branco pode ser aromatizado com:
>
> - Canela
> - Limão

**Resultado:** CORRETA (2/2)

**Justificação:** Apresenta exatamente leite, açúcar e arroz, com canela ou limão como aromas.

**Contexto recuperado**

1. `web-visitecoimbra-docaria-conventual-de-coimbra` — Doces a não perder > Manjar Branco — distance 0.214975
2. `web-visitecoimbra-gastronomia-em-coimbra` — (sem secção) — distance 0.382332
3. `web-visitecoimbra-docaria-conventual-de-coimbra` — (sem secção) — distance 0.396075

### Q16 — A que época remonta a tradição cervejeira de Coimbra, onde se concentrava a produção e para que fins era feita?

**Factos Essenciais**

- A ligação de Coimbra à cerveja remonta aos tempos medievais.
- A produção ocorria especialmente nos mosteiros e conventos.
- Os monges produziam cerveja para consumo próprio e comercialização.

#### NO-RAG

**Resposta**

> A tradição cervejeira de Coimbra remonta ao século XIII. Naquela época, a cerveja era produzida principalmente para fins religiosos e para a população universitária da época, que era composta por estudantes e professores da Universidade de Coimbra.

**Resultado:** PARCIALMENTE CORRETA (1/2)

**Justificação:** Situa a tradição na época medieval através do século XIII, mas não refere mosteiros/conventos nem os fins corretos de consumo próprio e comercialização.

#### RAG

**Resposta**

> A tradição cervejeira de Coimbra remonta aos tempos medievais. Na época, a produção de cerveja era realizada principalmente nos mosteiros e conventos, onde os monges produziam cervejas para consumo próprio e para comercialização.

**Resultado:** CORRETA (2/2)

**Justificação:** Refere corretamente a época medieval, mosteiros e conventos, consumo próprio e comercialização.

**Contexto recuperado**

1. `web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira` — (sem secção) — distance 0.116582
2. `web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira` — (sem secção) — distance 0.236218
3. `viver-o-patrimonio-em-coimbra` — 18. LARGO DO MARMELEIRO — distance 0.323187

### Q17 — Que duas atividades são explicitamente recomendadas nas margens do rio Ceira?

**Factos Essenciais**

- As margens do rio Ceira são indicadas para passeios.
- As margens do rio Ceira são indicadas para piqueniques.

#### NO-RAG

**Resposta**

> Não tenho informações específicas sobre atividades recomendadas nas margens do rio Ceira. Posso sugerir algumas opções de atividades que podem ser feitas nas margens de rios em geral, como caminhadas, observação da vida selvagem, observação de paisagens naturais, etc.

**Resultado:** PARCIALMENTE CORRETA (1/2)

**Justificação:** Sugere caminhadas, equivalente a passeios, mas não refere piqueniques e assume não conhecer as recomendações específicas.

#### RAG

**Resposta**

> As duas atividades recomendadas nas margens do rio Ceira são:
>
> 1. Passeios e piqueniques
> 2. Paddle no Rio Mondego

**Resultado:** PARCIALMENTE CORRETA (1/2)

**Justificação:** Inclui corretamente passeios e piqueniques, mas acrescenta Paddle no rio Mondego como se fosse uma recomendação para as margens do Ceira.

**Contexto recuperado**

1. `web-visitecoimbra-ceira` — (sem secção) — distance 0.273274
2. `web-visitecoimbra-desporto` — Aqui estão 10 atividades desportivas que pode praticar em Coimbra — distance 0.406731
3. `web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira` — (sem secção) — distance 0.518819

### Q18 — O que existia na Ínsua dos Bentos quando a Câmara a comprou em 1888 e quem ficou encarregado do projeto para a transformar em jardim público?

**Factos Essenciais**

- A Ínsua dos Bentos tinha uma zona de laranjais.
- Tinha uma área descampada para corridas de cavalos e, a nascente, um campo de futebol onde a Académica jogava.
- Jacinto de Matos ficou encarregado do projeto de transformação em jardim público.

#### NO-RAG

**Resposta**

> Não tenho informações suficientes para responder com segurança à sua pergunta. Não sabia que a Câmara de Coimbra comprou a Ínsua dos Bentos em 1888. Se quiser mais informações sobre a história da Ínsua dos Bentos, posso tentar ajudar.

**Resultado:** INCORRETA (0/2)

**Justificação:** Declara não saber e não apresenta nenhum dos três blocos factuais.

#### RAG

**Resposta**

> Com base no contexto fornecido, podemos dizer que, quando a Câmara Municipal de Coimbra comprou a Ínsua dos Bentos em 1888, existia uma zona de laranjais e uma área descampada. Além disso, a nascente ficava um campo de futebol, onde a Académica jogava. O projeto para transformar a Ínsua dos Bentos em jardim público ficou encarregue do paisagista floricultor portuense Jacinto de Matos.

**Resultado:** PARCIALMENTE CORRETA (1/2)

**Justificação:** Refere os laranjais, a área descampada, o campo da Académica e Jacinto de Matos, mas omite que a área era usada para corridas de cavalos.

**Contexto recuperado**

1. `jardins-historicos` — 3. PARQUE DR. MANUEL BRAGA — distance 0.309475
2. `coimbra-dos-escritores` — 2. PARQUE DR. MANUEL BRAGA — distance 0.373763
3. `jardins-historicos` — 8. JARDINS DA AVENIDA SÁ DA BANDEIRA — distance 0.495926

### Q19 — Quando e em que contexto universitário foi criado o Jardim Botânico de Coimbra, e que escritor o menciona numa obra?

**Factos Essenciais**

- O Jardim Botânico foi criado em 1772 durante a Reforma Pombalina da Universidade de Coimbra.
- Miguel Torga menciona o jardim e a vista sobre o rio no *Terceiro Dia d’ A Criação do Mundo*.

#### NO-RAG

**Resposta**

> O Jardim Botânico de Coimbra foi criado em 1881, no contexto da Universidade de Coimbra, como parte do Museu Botânico da Universidade. 
>
> O escritor que menciona o Jardim Botânico de Coimbra numa obra é o poeta e escritor português Luís de Camões, no seu poema "Os Lusíadas".

**Resultado:** INCORRETA (0/2)

**Justificação:** Erra a data, o contexto e o escritor/obra.

#### RAG

**Resposta**

> O Jardim Botânico de Coimbra foi criado em 1772, durante a Reforma Pombalina da Universidade de Coimbra. Não há menção a um escritor específico que o mencione numa obra no contexto fornecido.

**Resultado:** PARCIALMENTE CORRETA (1/2)

**Justificação:** Indica corretamente 1772 e a Reforma Pombalina, mas omite Miguel Torga e Terceiro Dia d’ A Criação do Mundo.

**Contexto recuperado**

1. `coimbra-dos-escritores` — 4. JARDIM BOTÂNICO — distance 0.132478
2. `universidade-alta-sofia-patrimonio-mundial` — 16. JARDIM BOTÂNICO DA UNIVERSIDADE DE COIMBRA — distance 0.181725
3. `web-visitecoimbra-museus` — Jardim Botânico — distance 0.244462

### Q20 — Onde se realiza a Regata da Queima das Fitas, quem compete e o que o evento celebra?

**Factos Essenciais**

- A Regata da Queima das Fitas realiza-se no rio Mondego.
- Competem equipas de remo da Associação Académica de Coimbra e equipas convidadas.
- O evento celebra o desporto e o espírito académico.

#### NO-RAG

**Resposta**

> A Regata da Queima das Fitas é um evento tradicional que se realiza na cidade de Coimbra, Portugal. 
>
> O evento é realizado no rio Mondego, na cidade de Coimbra, e é uma competição de regatas entre as escolas de Coimbra. 
>
> O que a Regata da Queima das Fitas celebra é a data da queima das fitas, que é uma tradição que remonta ao século XVII. As fitas são queimadas em uma cerimónia que marca o início da estação letiva e a abertura da nova universidade.

**Resultado:** PARCIALMENTE CORRETA (1/2)

**Justificação:** Indica corretamente o rio Mondego, mas identifica erradamente os competidores e o que o evento celebra.

#### RAG

**Resposta**

> Não tenho informação suficiente no contexto disponível para responder com segurança.
>
> O contexto menciona a "Sé Velha" e a "Queima das Fitas", mas não há informações sobre a Regata da Queima das Fitas. Além disso, não há menção a uma competição ou um evento específico que celebre a Regata da Queima das Fitas.

**Resultado:** INCORRETA (0/2)

**Justificação:** Abstém-se porque o top-3 não contém o trecho sobre a Regata; não apresenta nenhum Essential Fact.

**Contexto recuperado**

1. `fado-e-tradicoes-academicas` — 11. PRAÇA DA CANÇÃO — distance 0.348357
2. `fado-e-tradicoes-academicas` — 7. SÉ VELHA — distance 0.480346
3. `universidade-alta-sofia-patrimonio-mundial` — 21. SÉ VELHA — distance 0.487981

## 7. Resultados Quantitativos

| Q | Score No-RAG | Classificação No-RAG | Score RAG | Classificação RAG | Melhor resultado |
|---|---:|---|---:|---|---|
| Q01 | 1 | PARCIALMENTE CORRETA | 2 | CORRETA | RAG |
| Q02 | 0 | INCORRETA | 2 | CORRETA | RAG |
| Q03 | 0 | INCORRETA | 2 | CORRETA | RAG |
| Q04 | 0 | INCORRETA | 2 | CORRETA | RAG |
| Q05 | 0 | INCORRETA | 2 | CORRETA | RAG |
| Q06 | 0 | INCORRETA | 2 | CORRETA | RAG |
| Q07 | 0 | INCORRETA | 0 | INCORRETA | EMPATE |
| Q08 | 1 | PARCIALMENTE CORRETA | 2 | CORRETA | RAG |
| Q09 | 0 | INCORRETA | 1 | PARCIALMENTE CORRETA | RAG |
| Q10 | 0 | INCORRETA | 2 | CORRETA | RAG |
| Q11 | 0 | INCORRETA | 0 | INCORRETA | EMPATE |
| Q12 | 0 | INCORRETA | 1 | PARCIALMENTE CORRETA | RAG |
| Q13 | 1 | PARCIALMENTE CORRETA | 2 | CORRETA | RAG |
| Q14 | 0 | INCORRETA | 2 | CORRETA | RAG |
| Q15 | 1 | PARCIALMENTE CORRETA | 2 | CORRETA | RAG |
| Q16 | 1 | PARCIALMENTE CORRETA | 2 | CORRETA | RAG |
| Q17 | 1 | PARCIALMENTE CORRETA | 1 | PARCIALMENTE CORRETA | EMPATE |
| Q18 | 0 | INCORRETA | 1 | PARCIALMENTE CORRETA | RAG |
| Q19 | 0 | INCORRETA | 1 | PARCIALMENTE CORRETA | RAG |
| Q20 | 1 | PARCIALMENTE CORRETA | 0 | INCORRETA | NO-RAG |

### No-RAG

- Corretas: 0 / 20 (0%)
- Parcialmente corretas: 7 / 20 (35%)
- Incorretas: 13 / 20 (65%)
- Answer Quality Score total: 7 / 40
- Answer Quality Score médio: 0,35 / 2

### RAG

- Corretas: 12 / 20 (60%)
- Parcialmente corretas: 5 / 20 (25%)
- Incorretas: 3 / 20 (15%)
- Answer Quality Score total: 29 / 40
- Answer Quality Score médio: 1,45 / 2

### Comparação Pareada

- RAG melhor: 16 / 20 (80%)
- Empate: 3 / 20 (15%)
- No-RAG melhor: 1 / 20 (5%)

**Diferença média de score:** +1,10 pontos na escala 0–2.

## 8. Breve Discussão

O RAG obteve um score superior em 16 das 20 perguntas pareadas e aumentou o score médio de 0,35 para 1,45. Entre as melhorias mais claras está a Q03, em que o RAG forneceu corretamente os séculos e as igrejas enquanto o No-RAG inventou ambos; a Q06, em que o RAG apresentou corretamente os três factos pedidos e o No-RAG falhou os três; e a Q14, em que o RAG descreveu corretamente o doce conventual enquanto o No-RAG o classificou erradamente como um prato de carne.

Verificaram-se três empates. As duas condições obtiveram score 0 na Q07 e na Q11, e score 1 na Q17. Na Q17, o RAG recuperou o chunk correto sobre Ceira em rank 1 e referiu passeios e piqueniques, mas acrescentou também Paddle no Mondego. Trata-se de um erro na generation, provocado pela mistura de informação proveniente de outro chunk recuperado com a localização pedida.

### Sucesso no retrieval vs falha na generation

A análise das respostas RAG que não obtiveram a classificação máxima revelou uma distinção importante. Nas **Q07, Q09, Q11, Q18 e Q19**, o componente de retrieval recuperou corretamente o contexto que continha a informação necessária segundo o conjunto de avaliação congelado. Em todos estes casos, a evidência relevante já estava presente no contexto recuperado, incluindo vários casos em que surgia em rank 1. Assim, a perda no Answer Quality Score não pode ser atribuída a uma falha da pesquisa vetorial em encontrar o conhecimento necessário. A falha ocorreu na etapa de **generation**, em que o `llama3.2:3b` se absteve apesar de ter evidência suficiente ou omitiu um ou mais Factos Essenciais presentes no contexto.

| Pergunta | Resultado RAG | Diagnóstico do retrieval | Diagnóstico da generation |
|---|---|---|---|
| Q07 | INCORRETA (0/2) | O contexto relevante do Colégio de São Jerónimo foi recuperado em rank 1 | Abstenção injustificada: o modelo afirma que o contexto é insuficiente e não utiliza nenhum dos três Factos Essenciais disponíveis |
| Q09 | PARCIALMENTE CORRETA (1/2) | O contexto relevante sobre a Cestaria de Bunho foi recuperado em rank 1 | Utiliza a colheita no verão, a secagem e os objetos produzidos, mas omite a ligação explícita à Reserva Natural do Paul de Arzila |
| Q11 | INCORRETA (0/2) | O contexto relevante sobre o Memorial Miguel Torga foi recuperado em rank 1 | Abstenção injustificada: o modelo afirma que a autoria e os elementos materiais não estão disponíveis, apesar de constarem da evidência recuperada |
| Q18 | PARCIALMENTE CORRETA (1/2) | O contexto relevante sobre o Parque Dr. Manuel Braga / Ínsua dos Bentos foi recuperado em rank 1 | Utiliza os laranjais, a área descampada, o campo da Académica e Jacinto de Matos, mas omite que a área descampada era utilizada para corridas de cavalos |
| Q19 | PARCIALMENTE CORRETA (1/2) | O contexto relevante sobre o Jardim Botânico foi recuperado em rank 1 | Utiliza corretamente 1772 e a Reforma Pombalina, mas omite Miguel Torga e *Terceiro Dia d’ A Criação do Mundo* |

Estes casos devem, por isso, ser interpretados como **falhas do lado da generation dentro da pipeline RAG, e não como falhas de retrieval**. Esta distinção **não altera** os respetivos Answer Quality Scores: a avaliação mede a resposta final apresentada ao utilizador, pelo que uma resposta incompleta ou incorreta deve continuar a perder pontos mesmo quando a evidência correta foi recuperada. No entanto, o diagnóstico é importante porque mostra que melhorar apenas o retrieval não resolveria estes cinco casos; o componente de generation também precisa de utilizar melhor a evidência já disponível no contexto.

Em contraste, a **Q20 constitui uma verdadeira falha de retrieval**. A informação pedida sobre a Regata da Queima das Fitas existe no corpus congelado, mas nenhum dos três chunks do top-3 continha a passagem relevante. Consequentemente, o LLM não recebeu a evidência necessária para responder corretamente. Este caso contrasta diretamente com Q07, Q09, Q11, Q18 e Q19, em que a informação necessária já tinha sido recuperada antes da generation.

A comparação é descritiva e utiliza uma única generation por pergunta e por condição. Assim, os resultados caracterizam esta execução específica, com este prompt, este modelo e esta configuração de retrieval top-3; não estimam a variabilidade entre execuções nem significância estatística.

## 9. Validação e Integridade

- Perguntas: 20
- Respostas No-RAG: 20
- Respostas RAG: 20
- Total de respostas: 40
- Scores No-RAG: 20
- Scores RAG: 20
- Todos os scores em `{0, 1, 2}`: SIM
- A soma das classes No-RAG é 20: SIM
- A soma das classes RAG é 20: SIM
- A soma da comparação pareada é 20: SIM
- As percentagens totalizam 100% em todas as distribuições: SIM
- Respostas raw guardadas antes do scoring: SIM
- Retries técnicos: 0
- Raw results SHA-256: `78dd3a1186685d2ff0e2f1017f7a96727e3c8a95bb3f9577f70f944bea317cbd`
- Conjunto de avaliação V2 inalterado: SIM
- Corpus congelado, chunks e manifest inalterados: SIM
- Chroma original congelada inalterada: SIM
- Scripts principais do RAG e integração inalterados: SIM
