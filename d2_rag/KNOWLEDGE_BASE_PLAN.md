# D2 — Knowledge Base Plan

## 1. Goals

Esta fase define a knowledge base inicial do **Coimbra Tourism Expert** antes de qualquer recolha. Os objetivos são:

- delimitar o conhecimento turístico, histórico e cultural a cobrir;
- selecionar um conjunto pequeno, credível e complementar de fontes, privilegiando entidades primárias e institucionais;
- permitir respostas factuais, explicativas, comparativas e algumas respostas que combinem informação de vários documentos;
- garantir rastreabilidade desde cada futuro documento até à sua origem;
- registar desde a aquisição a informação necessária para controlo de qualidade, atualização e avaliação;
- manter o corpus suficientemente pequeno para inspeção manual e suficientemente diverso para revelar lacunas reais.

Este plano baseia-se no [enunciado oficial](../2026_ILN_CourseProject.pdf), no [plano inicial do D2](D2_PLAN.md) e em source discovery realizado em setembro de 2026. Não recolhe documentos, não cria dados e não implementa processamento ou RAG.

## 2. Source Selection Policy

### 2.1 Ordem de preferência

1. **Fonte primária responsável pelo local ou património**: Universidade de Coimbra, museu, monumento, operador de transportes ou entidade gestora.
2. **Fonte pública institucional especializada**: Património Cultural, I.P., Câmara Municipal de Coimbra, Turismo de Portugal ou Turismo Centro de Portugal.
3. **Publicação institucional com autoria e contexto claros**: guias, mapas e PDFs oficiais.
4. **Fonte secundária credível**, apenas quando preenche uma lacuna que não pode ser coberta adequadamente por fontes primárias e após justificação explícita.

Wikipedia, blogs, TripAdvisor, páginas comerciais, agregadores e conteúdo gerado por utilizadores não entram na baseline. Podem, no máximo, ajudar a detetar lacunas durante discovery; não serão adquiridos automaticamente.

### 2.2 Critérios de aceitação

Um documento candidato deve:

- contribuir diretamente para uma categoria e para perguntas plausíveis do domínio;
- ter organização responsável e URL canónica identificáveis;
- apresentar conteúdo substantivo em português, salvo exceção justificada;
- permitir distinguir conteúdo relativamente estável de informação operacional mutável;
- acrescentar factos, explicações ou perspetiva institucional não cobertos de forma equivalente por outro documento aceite;
- ter formato que possa ser preservado e posteriormente extraído de forma reprodutível;
- ter condições de acesso e utilização registadas no manifest, sem presumir que estar publicamente acessível equivale a licença irrestrita.

### 2.3 Critérios de rejeição ou adiamento

- páginas quase vazias, apenas promocionais ou dependentes de elementos dinâmicos sem conteúdo recuperável;
- listagens que apenas repetem páginas mais completas;
- notícias, agendas e páginas de eventos usadas como fonte de factos atuais;
- horários, preços, interrupções, disponibilidade e itinerários operacionais que rapidamente ficam desatualizados;
- conteúdo sem autoria/proveniência clara;
- duplicação integral ou quase integral de uma fonte mais autoritativa;
- documentos cujo âmbito regional introduza mais ruído do que conhecimento sobre o concelho/cidade de Coimbra.

### 2.4 Política temporal e de conflito

Factos históricos, descrições patrimoniais e enquadramentos culturais são o núcleo do corpus. Informação prática só deve entrar quando seja útil e relativamente estável, com data de aquisição e nota temporal.

Quando fontes institucionais divergirem, a divergência não deve ser apagada durante a recolha. Devem conservar-se a proveniência, as datas e a formulação de cada fonte, assinalando o caso para revisão. A entidade diretamente responsável pelo bem ou serviço tem prioridade operacional; isto é uma regra de curadoria, não garantia automática de correção.

## 3. Proposed Domain Taxonomy

### 3.1 Taxonomia inicial

| Categoria primária | Cobertura | Limites principais |
|---|---|---|
| `university_heritage` | História, espaços, património, ciência e tradições da Universidade de Coimbra | Não inclui vida académica atual sem relevância turística/cultural estável |
| `city_history` | Evolução histórica de Coimbra, períodos, acontecimentos e personalidades | Monumentos individuais ficam em `built_heritage` |
| `built_heritage` | Monumentos, arquitetura religiosa/civil, arqueologia e património classificado | Coleções museológicas ficam em `museums_collections` |
| `museums_collections` | Museus, núcleos museológicos, coleções e respetivo contexto | Evita agendas, exposições temporárias e bilheteira atual |
| `culture_traditions` | Fado/Canção de Coimbra, tradições académicas, festividades, lendas e património imaterial | Gastronomia tem categoria própria |
| `gastronomy` | Pratos, doçaria, origens e tradições gastronómicas locais | Não inclui recomendações de restaurantes ou disponibilidade comercial |
| `landscape_gardens` | Jardins históricos, paisagem urbana, Mondego e espaços verdes de interesse turístico | Natureza regional fora de Coimbra fica excluída |
| `visitor_orientation` | Relações entre locais, percursos conceptuais, mapas e orientação turística estável | Não é uma categoria para copiar listas promocionais nem dados real-time |
| `transport_access` | Operadores, interfaces, estações e modos de acesso estruturalmente relevantes | Exclui horários, preços, obras, atrasos e perturbações |

### 3.2 Sobreposições e decisões de modelação

As categorias sugeridas inicialmente tinham sobreposição significativa:

- `heritage`, `monuments` e `tourist_attractions` descrevem frequentemente o mesmo local;
- `history` atravessa Universidade, monumentos e museus;
- `practical_information` mistura factos estáveis com dados operacionais voláteis;
- `culture` é demasiado ampla se também absorver tradições e gastronomia.

A baseline usa por isso **uma categoria primária por documento** e futuras `tags` secundárias controladas, por exemplo `unesco`, `religious_heritage`, `roman_coimbra`, `fado` ou `accessibility`. `tourist_attractions` passa a ser uma perspetiva de uso, não uma categoria de conteúdo. Um monumento visitável continua a pertencer a `built_heritage`; um mapa que relaciona vários locais pertence a `visitor_orientation`.

A categoria `landscape_gardens` foi acrescentada porque Jardim Botânico, Quinta das Lágrimas, Mondego e jardins históricos não cabem bem em monumentos ou informação prática. A lista e o vocabulário de tags continuam **TBD / To be evaluated** após inspeção do corpus adquirido.

## 4. Candidate Sources

### 4.1 Shortlist institucional

Esta shortlist é deliberadamente seletiva. “Estabilidade” descreve o conteúdo de conhecimento pretendido, não garante que a página ou URL nunca mude.

| # | Organização / título | URL | Categoria | Tipo / língua | Contributo esperado e autoridade | Estabilidade, duplicação e notas temporais |
|---:|---|---|---|---|---|---|
| 1 | Universidade de Coimbra — **Atributos: Universidade de Coimbra — Alta e Sofia** | https://worldheritage.uc.pt/pt/atributos/ | `university_heritage` | Web / PT | Síntese institucional dos atributos que fundamentam a classificação, história, arquitetura, ciência e tradições. A UC gere o sítio classificado. | Alta para conteúdo histórico. Sobrepõe-se parcialmente às páginas de visita da UC e ao Turismo Centro; deve ser a fonte de enquadramento principal. |
| 2 | Universidade de Coimbra, UCTour — **Biblioteca Joanina** | https://visit.uc.pt/engine.io/space-list/joanina | `university_heritage` | Web / PT | Descrição direta da Biblioteca Joanina, espaços, história e acervo pelo serviço oficial de turismo da UC. | História estável; horários, regras e bilhetes são voláteis e devem ser excluídos ou marcados como temporais. Possível sobreposição com #1. |
| 3 | Universidade de Coimbra — **O Museu da Ciência da Universidade de Coimbra** | https://www.uc.pt/org/historia_ciencia_na_uc/Textos/museu/omuse | `museums_collections` | Web / PT | Contexto institucional sobre o Museu da Ciência e as coleções científicas da UC. | Conteúdo histórico relativamente estável; confirmar atualidade e se existe página canónica mais recente antes da aquisição. |
| 4 | Câmara Municipal de Coimbra — **História da Cidade** | https://www.cm-coimbra.pt/areas/viver/a-cidade/historia/historia-da-cidade | `city_history` | Web / PT | Narrativa cronológica municipal, incluindo Coimbra romana/islâmica, primeira capital, Universidade e evolução urbana. | Alta para factos históricos gerais. Poderá repetir enquadramento das páginas de monumentos e UC. |
| 5 | Câmara Municipal de Coimbra — **Monumentos** | https://www.cm-coimbra.pt/areas/visitar/conhecer-coimbra/monumentos | `visitor_orientation` | Web / PT | Índice oficial e gerível dos principais monumentos, útil para delimitar cobertura e relações entre locais. | Alta como inventário, mas pouco conteúdo próprio. Não deve substituir páginas detalhadas nem ser repetido integralmente com elas. |
| 6 | Câmara Municipal de Coimbra — **Museus** | https://www.cm-coimbra.pt/areas/visitar/conhecer-coimbra/museus | `visitor_orientation` | Web / PT | Inventário municipal de museus e núcleos, útil para identificar cobertura e lacunas. | Alta como lista; elevada duplicação com páginas de cada museu. Pode ficar apenas como documento de orientação. |
| 7 | Câmara Municipal de Coimbra — **Museu Municipal** | https://www.cm-coimbra.pt/areas/visitar/conhecer-coimbra/museus/museu-municipal | `museums_collections` | Web / PT | Missão, núcleos e coleções do museu municipal, diretamente descritos pela entidade responsável. | Conteúdo institucional estável; horários e exposições devem ser tratados como temporais. |
| 8 | Museus e Monumentos de Portugal — **Museu Nacional de Machado de Castro** | https://www.museusemonumentos.pt/pt/museus-e-monumentos/museu-nacional-de-machado-de-castro | `museums_collections` | Web / PT | Fonte oficial do museu nacional; deverá cobrir edifício, criptopórtico e coleções. | História/coleções estáveis; informação de visita muda. Sobreposição com páginas da Câmara e Turismo de Portugal; preferir esta fonte quando o conteúdo for suficiente. |
| 9 | Património Cultural, I.P. — **Catedrais (Sé Velha e Sé Nova de Coimbra)** | https://www.patrimoniocultural.gov.pt/patrimonio-cultural-material/catedrais-pt/ | `built_heritage` | Web / PT | Descrição histórico-artística e patrimonial pelas autoridades nacionais do património. | Alta para história e arquitetura; a página agrega várias catedrais, pelo que a extração futura terá de preservar apenas as secções relevantes. |
| 10 | Património Cultural, I.P. — **Mosteiro de Santa Clara-a-Velha** | https://loja.patrimoniocultural.gov.pt/patrimonio/mosteiro-de-santa-clara-a-velha/ | `built_heritage` | Web / PT | História do mosteiro, relação com o Mondego, abandono e recuperação arqueológica, pela entidade patrimonial responsável. | História estável. Horários e estado de abertura são voláteis; foi encontrada também informação oficial de encerramento temporário, demonstrando que estes campos não devem ser conhecimento permanente. |
| 11 | Património Cultural, I.P. — **Ficha do Mosteiro de Santa Clara-a-Nova** | https://imovel.patrimoniocultural.gov.pt/detalhes.php?code=70695 | `built_heritage` | Web/database record / PT | Ficha institucional de classificação e nota histórico-artística do mosteiro novo. | Alta para classificação e história; densa e potencialmente ruidosa. Complementa #10, mas partilha contexto sobre a comunidade de Santa Clara. |
| 12 | Câmara Municipal de Coimbra — **Jardim Botânico** | https://www.cm-coimbra.pt/areas/visitar/conhecer-coimbra/parques-e-jardins/jardim-botanico | `landscape_gardens` | Web / PT | História, criação, figuras científicas, arquitetura e diversidade do jardim. | Conteúdo histórico estável. Sobreposição parcial com UC/UNESCO; uma futura página oficial do Jardim Botânico poderá ter prioridade se for mais completa. |
| 13 | Câmara Municipal de Coimbra — **Jardins da Quinta das Lágrimas** | https://www.cm-coimbra.pt/areas/visitar/conhecer-coimbra/parques-e-jardins/jardins-da-quinta-das-lagrimas | `landscape_gardens` | Web / PT | História dos jardins e distinção entre memória histórica e construção literária da lenda de Pedro e Inês. | Conteúdo cultural relativamente estável; requer cuidado para não apresentar lenda como facto histórico. Possível complemento por fonte proprietária, mas não comercial como base. |
| 14 | Câmara Municipal de Coimbra — **Etnografia e tradições — Património Cultural Imaterial de Coimbra** | https://www.cm-coimbra.pt/wp-content/uploads/2018/05/coimbra.old_joomlatools-files_docman-files_Etnografia-e-tradicoes-...-Patrimonio-Cultural-Imaterial-de-Coimbra.pdf | `culture_traditions` | PDF / PT | Documento municipal sobre tradições, etnografia, gastronomia e património imaterial; cobre temas pouco presentes nas páginas monumentais. | Conteúdo histórico estável, mas o PDF é antigo e o URL é frágil. Deve ser validado quanto a autoria, versão, completude e extração antes de aceitação. Sobrepõe-se a #15 e #16. |
| 15 | Câmara Municipal de Coimbra — **Mostra de Doçaria Conventual e Contemporânea de Coimbra** | https://www.cm-coimbra.pt/areas/viver/cultura/eventos-regulares/mostra-de-docaria-conventual-e-regional-de-coimbra | `gastronomy` | Web / PT | Identifica a herança conventual e especialidades de Coimbra através de fonte municipal. | Os factos gastronómicos são relativamente estáveis; datas/programa do evento são voláteis e devem ser excluídos. |
| 16 | Turismo Centro de Portugal — **Doçaria Regional do Centro de Portugal** | https://turismodocentro.pt/artigo/docaria-regional-do-centro-de-portugal/ | `gastronomy` | Web / PT | Contextualiza Pastéis de Santa Clara, Manjar Branco, Charcada, Arrufada e outras especialidades na região. Entidade regional oficial de turismo. | Estável, mas âmbito mais amplo que Coimbra e tom promocional. Adquirir apenas se acrescentar factos verificáveis a #14/#15; evitar conteúdo regional irrelevante. |
| 17 | Turismo Centro de Portugal — **Coimbra, uma cidade de muitos encantos** | https://turismodocentro.pt/artigo/coimbra-uma-cidade-de-muito-encanto/ | `visitor_orientation` | Web / PT | Visão transversal que relaciona Universidade, Alta/Baixa, monumentos, Mondego, gastronomia e atrações. Útil para perguntas multi-documento e orientação. | Estável no essencial, mas muito sobreposto e promocional. Usar como ponte entre temas, não como fonte principal para detalhes. |
| 18 | Câmara Municipal de Coimbra — **Mapa turístico de Coimbra 2023** | https://www.cm-coimbra.pt/wp-content/uploads/2023/02/mapa_turistico_2023.pdf | `visitor_orientation` | PDF/map / PT+EN | Relações espaciais, legenda de património UNESCO, cultura, serviços, natureza e mobilidade numa publicação oficial. | Parte espacial relativamente estável; serviços podem mudar. Extração textual de mapa pode ser difícil e terá de ser avaliada antes de aceitação. |
| 19 | SMTUC — **Mapa da rede de transportes** | https://www.smtuc.pt/mapa-redetransportes/ | `transport_access` | Web + image / PT | Fonte primária municipal para estrutura da rede de autocarros e identidade do operador. | Baixa a média: rede, linhas e paragens mudam. Nesta baseline serve apenas para conhecimento estrutural; não para horários ou resposta operacional. Conteúdo textual limitado. |
| 20 | CP — **Comboios Urbanos de Coimbra** | https://cp.pt/info/pt/coimbra | `transport_access` | Web / PT | Fonte primária para o papel de Coimbra-B, ligações ferroviárias e interfaces gerais com transporte urbano. | Estrutura geral moderadamente estável; horários, preços, promoções e serviço corrente mudam e ficam excluídos. A página contém elementos promocionais/placeholder que exigirão limpeza. |

### 4.2 Leitura da shortlist

- Os itens **#1–#18** formam o conjunto de candidatos mais forte para revisão pré-recolha.
- **#19–#20** são candidatos condicionais: devem entrar apenas se for possível isolar afirmações estruturais e úteis. Caso contrário, `transport_access` deverá ser assumida como lacuna intencional da primeira versão.
- Índices (#5 e #6) e sínteses (#17) não devem dominar o corpus; servem para relações, cobertura e perguntas de composição.
- Páginas detalhadas oficiais têm prioridade sobre descrições duplicadas de portais turísticos.
- A shortlist não equivale a documentos aceites. Cada item terá estado `proposed` até revisão de acesso, conteúdo, direitos de utilização e redundância.

## 5. Proposed Initial Corpus Size

Propõe-se uma baseline de **16 a 20 documentos aceites**, com objetivo operacional de **18**, após revisão da shortlist.

Este intervalo deriva do desenho do corpus:

- nove categorias precisam de pelo menos uma fonte substantiva, mas as categorias nucleares (`university_heritage`, `built_heritage`, `museums_collections` e `culture_traditions`) exigem mais de uma perspetiva ou entidade;
- 16–20 documentos permitem cobrir os principais núcleos sem transformar a curadoria e inspeção manual numa tarefa desproporcionada para um projeto académico;
- a diversidade inclui páginas institucionais, registos patrimoniais e poucos PDFs/mapas, permitindo testar mais tarde problemas reais de extração sem os multiplicar;
- o conjunto suporta avaliação por categoria e perguntas que cruzem Universidade/cidade, história/monumentos, mosteiros/gastronomia e espaços/transportes;
- um intervalo, em vez de uma quota rígida, permite rejeitar páginas duplicadas ou pobres sem inserir substitutos artificiais.

O objetivo não é equilibrar todas as categorias pelo mesmo número. O corpus deve refletir a importância do domínio e a qualidade disponível. A expansão só deverá ocorrer após uma coverage review baseada em perguntas sem resposta, baixa cobertura de uma categoria ou falhas de retrieval atribuíveis à ausência documental.

## 6. Metadata Schema

O schema abaixo é para **document metadata**. `chunk_id`, número de página e posição do chunk não pertencem a esta fase.

### 6.1 Campos obrigatórios

| Campo | Tipo conceptual | Finalidade |
|---|---|---|
| `document_id` | string | Identificador interno estável, independente do nome do ficheiro e do URL. Não deve codificar categoria mutável. |
| `source_organization` | string | Nome normalizado da entidade responsável/publicadora. É preferível a um `source` ambíguo. |
| `title` | string | Título humano do documento no momento da aquisição. |
| `url` | string | URL canónica de origem para esta baseline web. Se no futuro existir uma fonte sem URL, o schema poderá aceitar `null` com justificação. |
| `primary_category` | enum/string controlada | Uma categoria da taxonomia aprovada. |
| `language` | código BCP 47 simplificado | Baseline: `pt`; registar outra língua quando necessário. |
| `source_type` | enum | Baseline proposta: `web_page`, `pdf`, `database_record`, `map` ou `other`. |
| `status` | enum | Estado de curadoria: `proposed`, `reviewing`, `accepted`, `rejected`, `superseded` ou `unavailable`. |
| `acquired_at` | datetime ISO 8601 ou null | Obrigatório semanticamente após aquisição; deve ser `null` enquanto a fonte é apenas proposta. |
| `access_checked_at` | datetime ISO 8601 | Data da última confirmação do URL/acesso, distinta da aquisição. |

### 6.2 Campos opcionais ou condicionais

| Campo | Quando usar |
|---|---|
| `tags` | Lista curta de termos controlados para temas secundários; vocabulário ainda TBD. |
| `source_published_at` | Quando a fonte apresenta uma data de publicação verificável. |
| `source_last_modified_at` | Quando a fonte fornece uma data de atualização confiável. |
| `temporal_scope` | Descrição do período a que o conteúdo se refere, quando relevante. |
| `validity_notes` | Avisos sobre volatilidade, por exemplo “não usar horários/preços” ou validade declarada pela fonte. |
| `license_or_usage_notes` | Licença publicada, termos relevantes ou necessidade de revisão. Não inferir uma licença ausente. |
| `version_label` | Edição/revisão declarada, especialmente em PDFs, mapas ou regulamentos. |
| `content_hash` | Hash calculado sobre o raw adquirido para detetar alterações e duplicação; só existe após recolha. |
| `local_path` | Caminho relativo para o ficheiro raw; só existe após recolha aceite. |
| `supersedes_document_id` | Quando uma nova aquisição substitui uma versão anterior sem destruir o histórico. |
| `decision_reason` | Justificação curta para aceitação, rejeição ou substituição. Fortemente recomendada quando `status` não é `proposed`. |
| `notes` | Observações de curadoria não cobertas pelos campos anteriores. |

`validity` não deve ser um booleano vago. A baseline separa datas publicadas, período do conteúdo e notas de validade. Datas devem incluir timezone quando conhecido; caso contrário, usar apenas a precisão realmente fornecida pela fonte.

## 7. Corpus Manifest Design

### 7.1 Baseline escolhida: JSONL

O manifest futuro deverá ser um único ficheiro versionável:

```text
d2_rag/data/manifest.jsonl
```

Cada linha representará um documento e seguirá o schema de metadata. Nesta fase não é criada qualquer entrada.

### 7.2 Justificação

- um objeto por linha mantém alterações localizadas e diffs Git legíveis;
- suporta campos opcionais, listas como `tags` e evolução do schema melhor do que CSV;
- evita reescrever e causar conflitos em todo um array JSON;
- é simples de validar e processar posteriormente em Python sem impor uma base de dados;
- preserva valores `null` explícitos e tipos, ao contrário de convenções CSV ambíguas.

CSV seria cómodo para edição tabular, mas lida pior com listas, notas extensas, valores nulos e evolução. Um único JSON array é válido, mas produz diffs maiores e mais conflitos. Não é necessária uma base de dados para um corpus desta dimensão.

### 7.3 Regras operacionais futuras

- uma fonte descoberta recebe `status: proposed` antes da aquisição;
- uma aquisição preserva o raw, preenche `acquired_at`, `local_path` e `content_hash`;
- aceitação e rejeição exigem `decision_reason`;
- versões anteriores não são silenciosamente sobrescritas: a nova entrada pode referenciar `supersedes_document_id`;
- indisponibilidade posterior não apaga a entrada nem o raw já legitimamente preservado;
- alterações de conteúdo são detetadas por hash, não apenas por URL ou timestamp;
- ordem recomendada no ficheiro: por `document_id`, para diffs estáveis;
- validação formal do schema fica para a fase de recolha/ingestion e não é implementada agora.

## 8. Proposed Data Directory Structure

Estrutura mínima proposta para quando a recolha for autorizada:

```text
d2_rag/
├── D2_PLAN.md
├── KNOWLEDGE_BASE_PLAN.md
└── data/
    ├── manifest.jsonl
    └── raw/
```

- `raw/` conterá apenas cópias fiéis dos documentos adquiridos, com nomes derivados do `document_id` e extensão original adequada.
- `manifest.jsonl` será a fonte de verdade sobre origem, estado, versão e ficheiro local.
- Não se propõem subpastas por categoria: categorias podem mudar e estão no manifest; duplicar essa organização no filesystem introduziria movimentos e inconsistências.
- `processed/` só deverá ser criado na fase de extração/preprocessing.
- diretórios para embeddings, Chroma ou índices não pertencem a esta fase.

Como ainda não foi autorizada recolha, `data/`, `raw/` e `manifest.jsonl` **não são criados agora**. Diretórios vazios e um manifest sem entradas não acrescentariam informação ao repositório.

## 9. Expected Coverage

### 9.1 Cobertura esperada por tipo de pergunta

- **Factual**: datas fundacionais, classificação patrimonial, funções de edifícios, coleções, especialidades gastronómicas e relações espaciais gerais.
- **Explicativa**: importância da Universidade para a cidade; efeito do Mondego em Santa Clara-a-Velha; origem conventual de parte da doçaria; valor do criptopórtico ou do património UNESCO.
- **Comparativa**: Sé Velha vs. Sé Nova; Santa Clara-a-Velha vs. Santa Clara-a-Nova; Museu Nacional vs. Museu Municipal; Biblioteca Joanina vs. outros espaços universitários.
- **Multi-documento**: relação entre história urbana, Universidade e Alta/Sofia; itinerários conceptuais por património religioso; ligações entre conventos, tradições e gastronomia; seleção de locais segundo interesse histórico, científico ou artístico.
- **Orientação estável**: identificar áreas, operadores e interfaces relevantes, sem prometer serviço atual, horários ou preços.

### 9.2 Distribuição desejada

O corpus inicial deverá conter:

- fontes de entidade diretamente responsável, não apenas portais turísticos;
- sínteses transversais em número limitado;
- pelo menos um documento substantivo para cada categoria mantida;
- múltiplas fontes nas áreas centrais, sem replicar descrições idênticas;
- combinação de documentos focados num local e documentos que relacionam vários locais.

A cobertura real só poderá ser confirmada depois da aquisição e inspeção. A existência de uma URL candidata não prova que o conteúdo extraído será suficiente.

## 10. Known Gaps / Risks

- **Cultura e tradições**: a cobertura institucional online é menos estruturada do que a de monumentos. O PDF municipal pode ser valioso, mas precisa de validação e poderá ser difícil de extrair.
- **Gastronomia**: muitas fontes são promocionais ou regionais; é necessário distinguir especialidades da cidade de produtos de toda a Região de Coimbra e evitar recomendações comerciais.
- **Transportes**: rede, horários, preços e obras mudam rapidamente. A baseline poderá ficar limitada a conhecimento estrutural ou excluir a categoria se este não for útil sem atualidade.
- **Informação prática**: horários e bilhetes aparecem misturados com história nas páginas oficiais. A futura preparação deverá separar ou marcar estas secções.
- **Duplicação institucional**: Câmara, UC, Turismo Centro e Turismo de Portugal repetem descrições dos locais mais conhecidos. A autoridade responsável deve prevalecer e as sínteses só ficam quando acrescentarem relações úteis.
- **URLs e sites em mudança**: há páginas antigas, endpoints pouco canónicos e URLs de PDF frágeis. O manifest deve preservar URL, data e hash; a seleção deve confirmar a página canónica antes de recolher.
- **Conteúdo dinâmico ou bloqueado**: algumas páginas oficiais devolveram conteúdo limitado ou bloqueio ao crawler durante discovery. Acessibilidade técnica terá de ser revista sem contornar políticas do site.
- **PDFs e mapas**: podem conter colunas, headers/footers, legendas visuais ou texto difícil de extrair. A utilidade para RAG depende de inspeção posterior.
- **Licenciamento**: autoridade não equivale a licença aberta. Termos e licença devem ser registados e respeitados antes de preservar/reutilizar conteúdo.
- **Facto vs. lenda**: Pedro e Inês, tradições e narrativas identitárias exigem linguagem que distinga documentação histórica, tradição e construção literária.
- **Viés de centralidade**: Universidade e centro histórico têm muito mais documentação e podem dominar retrieval, ocultando museus, jardins, gastronomia ou outros locais.
- **Âmbito geográfico**: “Coimbra” pode significar cidade, concelho, distrito ou região. A baseline deve privilegiar cidade/concelho e marcar explicitamente exceções.

## 11. Future Evaluation Considerations

A seleção permite construir, mais tarde e sem criar dados fictícios agora:

- perguntas simples com um único facto e uma única fonte relevante;
- perguntas explicativas com vários trechos relevantes do mesmo documento;
- perguntas comparativas que exigem dois documentos ou entidades;
- perguntas de síntese com evidência distribuída por categorias;
- perguntas ambíguas que testem distinções como Sé Velha/Sé Nova e Santa Clara-a-Velha/Santa Clara-a-Nova;
- perguntas temporais que o sistema deve recusar ou qualificar, em vez de usar horários/preços desatualizados;
- perguntas fora de cobertura e perguntas plausíveis cuja resposta não exista no corpus.

Para viabilizar relevance judgements, os futuros documentos devem conservar `document_id` estável e proveniência. Depois do processamento, chunks herdarão esse identificador. Ground truth deverá indicar todos os documentos/chunks considerados relevantes, e não apenas a fonte usada para escrever a resposta de referência.

A criação do dataset deverá evitar avaliar apenas os locais mais documentados. Deverá estratificar por categoria, tipo de pergunta e dificuldade, e incluir:

- negativos claros fora do domínio;
- negativos dentro do domínio mas ausentes do corpus;
- casos com nomes semelhantes;
- informação duplicada em várias fontes;
- informação contraditória ou temporalmente sensível;
- perguntas multi-hop cuja resposta dependa de mais de uma passagem.

O dataset, número de perguntas, rubrica, labels de relevância e divisão de desenvolvimento/teste continuam fora desta fase.

## 12. Decisions Still TBD

- Aprovar ou ajustar a taxonomia e definir o vocabulário controlado de `tags`.
- Confirmar se o âmbito geográfico é cidade, concelho, ou inclui exceções regionais explicitamente marcadas.
- Rever manualmente cada candidato e decidir `accepted`/`rejected` antes da recolha.
- Confirmar URLs canónicos para Biblioteca Joanina, Museu da Ciência e documentos municipais antigos.
- Verificar termos de uso/licenças e definir a política de preservação de páginas web.
- Decidir se páginas-índice (#5/#6) e sínteses promocionais (#17) acrescentam valor suficiente.
- Escolher entre o PDF municipal e as páginas gastronómicas quando houver duplicação.
- Decidir se `transport_access` entra na primeira versão ou fica como lacuna documentada.
- Definir a granularidade de aquisição: página completa versus secção relevante de páginas agregadoras, preservando sempre contexto e proveniência.
- Definir convenção de `document_id` sem acoplar identidade a categoria ou título mutável.
- Definir schema version e método futuro de validação do JSONL.
- Definir política de atualização e periodicidade de revalidação por classe de estabilidade.
- Confirmar o objetivo de 18 documentos depois da revisão de qualidade; permanecer no intervalo 16–20 apenas se todos acrescentarem cobertura real.
- Só após autorização: criar `data/raw/`, iniciar o manifest sem entradas fictícias e recolher os documentos aprovados.
