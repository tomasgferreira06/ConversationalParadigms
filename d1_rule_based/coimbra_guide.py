# Tomás Ferreira (2025168427) 
# Eduardo Pereira (2021233890)
#
# Natural Language Toolkit: Coimbra Guide
#
# Adapted from the NLTK ELIZA chatbot architecture.
#
# Persona:
#   Tourist guide specialised only in tourist attractions in Coimbra.
#
# Main idea:
#   - If the agent knows the answer, it answers.
#   - If it recognises the topic but does not have enough information, it says so.
#   - If the question is outside its domain, it says so explicitly.
#   - If the message is ambiguous, it asks the user to reformulate.
#
# The agent is intentionally simple, following the same pattern as the
# original NLTK ELIZA implementation, with only a very small context:
# the last tourist place, its category and a pending action.

import re

from nltk.chat.util import Chat, reflections


# A table of response pairs, where each pair consists of:
#   1. a regular expression;
#   2. a tuple of possible responses.
#
# Rules are checked from top to bottom.
# More specific rules must therefore come before more general rules.
# Each rule has several predefined responses, as in NLTK ELIZA; Chat
# selects one of them when that rule matches.

pairs = (

    # ------------------------------------------------------------------
    # Clearly outside the domain
    # ------------------------------------------------------------------

    (
        r"(.*)\b(comer|jantar|almo[cç]ar|restaurante|restaurantes|caf[eé]|caf[eé]s|"
        r"bar|bares|hotel|hot[eé]is|futebol|pol[ií]tica|medicina|programa[cç][aã]o|"
        r"python|bitcoin|intelig[eê]ncia artificial|tempo|meteorologia|[pP]orto|[lL]isboa)\b(.*)",
        (
            "Essa pergunta está fora do meu domínio. Fui criado apenas para falar sobre pontos turísticos de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "Não consigo ajudar com esse tema, porque o meu conhecimento está limitado aos pontos turísticos de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "Esse tema não faz parte do que fui preparado para responder. Posso ajudar-te com património, museus ou jardins de Coimbra.",
            "O meu domínio está limitado ao turismo em Coimbra. Se quiseres, podemos continuar pelo património, pelos museus ou pelos jardins.",
        ),
    ),


    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------

    (
        r"^(ol[aá]|ola|bom dia|boa tarde|boa noite|hey|viva|boas)(.*)",
        (
            "Olá! Sou o Coimbra Guide e conheço apenas pontos turísticos de Coimbra. Preferes património, museus ou jardins?",
            "Olá! Posso ajudar-te a descobrir pontos turísticos de Coimbra. Queres conhecer património, museus ou jardins?",
            "Olá! Estou aqui para te dar a conhecer alguns pontos turísticos de Coimbra. Preferes começar pelo património, pelos museus ou pelos jardins?",
        ),
    ),

    (
        r"(.*)(quem [ée]s|o que [ée]s|como te chamas|qual [ée] o teu nome)(.*)",
        (
            "Sou o Coimbra Guide, um agente baseado em regras especializado apenas em pontos turísticos de Coimbra. Preferes património, museus ou jardins?",
            "Sou um guia virtual com um domínio limitado aos pontos turísticos de Coimbra. Preferes património, museus ou jardins?",
            "Chamo-me Coimbra Guide e fui criado para falar apenas sobre pontos turísticos de Coimbra. Queres explorar património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(ajuda|o que sabes fazer|como me podes ajudar|o que posso perguntar)(.*)",
        (
            "Posso ajudar-te apenas com pontos turísticos de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "O meu domínio são os pontos turísticos de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "Posso orientar-te por alguns locais turísticos de Coimbra. Preferes património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(obrigad[oa]|muito obrigad[oa]|agrade[cç]o)(.*)",
        (
            "De nada! Queres saber mais sobre património, museus ou jardins?",
            "É um prazer ajudar! Queres saber mais sobre património, museus ou jardins?",
            "Ora essa! Podemos continuar a explorar Coimbra. Preferes património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(adeus|at[eé] logo|at[eé] [aà] pr[oó]xima|tchau|xau)(.*)",
        (
            "Até à próxima! Espero que tenhas uma boa visita a Coimbra.",
            "Boa visita a Coimbra! Até à próxima.",
            "Até breve! Espero ter ajudado a conhecer melhor alguns pontos turísticos de Coimbra.",
        ),
    ),

    (
        r"^\s*(?:n[aã]o sei|nao sei|n[aã]o tenho a certeza|nao tenho a certeza|n[aã]o fa[cç]o ideia|nao faco ideia)\s*$",
        (
            "Sem problema. Queres saber mais sobre património, museus ou jardins?",
            "Não faz mal não conheceres Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "Sem problema, posso ajudar-te a escolher. Preferes património, museus ou jardins?",
        ),
    ),

    # ------------------------------------------------------------------
    # Location of known tourist attractions
    # ------------------------------------------------------------------

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)(universidade de coimbra|universidade|pa[cç]o das escolas)(.*)",
        (
            "A Universidade de Coimbra fica na Alta da cidade e o núcleo histórico encontra-se no Paço das Escolas. Queres saber mais sobre património, museus ou jardins?",
            "Encontras a Universidade de Coimbra na Alta, sendo o Paço das Escolas o centro do seu núcleo histórico. Queres saber mais sobre património, museus ou jardins?",
            "A Universidade de Coimbra situa-se na Alta de Coimbra, com o núcleo histórico no Paço das Escolas. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)biblioteca joanina(.*)",
        (
            "A Biblioteca Joanina fica no Paço das Escolas, no núcleo histórico da Universidade de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "Encontras a Biblioteca Joanina no Paço das Escolas, dentro do núcleo histórico da Universidade de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "A Biblioteca Joanina situa-se no Paço das Escolas, na Universidade de Coimbra. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)s[eé] velha(.*)",
        (
            "A Sé Velha fica no centro histórico de Coimbra, entre a Baixa e a Universidade. Queres saber mais sobre património, museus ou jardins?",
            "Encontras a Sé Velha no centro histórico, entre a Baixa e a zona da Universidade. Queres saber mais sobre património, museus ou jardins?",
            "A Sé Velha situa-se no centro histórico de Coimbra, entre a Baixa e a Universidade. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)s[eé] nova(.*)",
        (
            "A Sé Nova fica na Alta de Coimbra, perto da Universidade. Queres saber mais sobre património, museus ou jardins?",
            "Encontras a Sé Nova na Alta, próxima da Universidade de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "A Sé Nova situa-se na Alta de Coimbra, perto da Universidade. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)jardim bot[aâ]nico(.*)",
        (
            "O Jardim Botânico fica junto à Universidade de Coimbra, na zona da Alta. Queres saber mais sobre património, museus ou jardins?",
            "Encontras o Jardim Botânico junto à Universidade, na zona da Alta de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "O Jardim Botânico situa-se na Alta, junto à Universidade de Coimbra. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)(museu(?: nacional)? )?machado de castro(.*)",
        (
            "O Museu Nacional Machado de Castro fica na Alta, muito perto da Universidade. Queres saber mais sobre património, museus ou jardins?",
            "Encontras o Museu Nacional Machado de Castro na Alta, junto à zona da Universidade. Queres saber mais sobre património, museus ou jardins?",
            "O Museu Nacional Machado de Castro situa-se na Alta de Coimbra, muito perto da Universidade. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)quinta das l[aá]grimas(.*)",
        (
            "A Quinta das Lágrimas fica em Santa Clara, na margem esquerda do Mondego. Queres saber mais sobre património, museus ou jardins?",
            "Encontras a Quinta das Lágrimas em Santa Clara, na margem esquerda do rio Mondego. Queres saber mais sobre património, museus ou jardins?",
            "A Quinta das Lágrimas situa-se em Santa Clara, do lado esquerdo do Mondego. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)santa clara(.*)",
        (
            "Santa Clara fica na margem esquerda do Mondego e é uma das zonas históricas da cidade. Queres saber mais sobre património, museus ou jardins?",
            "Santa Clara situa-se na margem esquerda do Mondego, numa zona histórica de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "Encontras Santa Clara do outro lado do Mondego, na margem esquerda, numa zona histórica da cidade. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)portugal dos pequenitos(.*)",
        (
            "O Portugal dos Pequenitos fica em Santa Clara, na margem esquerda do Mondego. Queres saber mais sobre património, museus ou jardins?",
            "Encontras o Portugal dos Pequenitos em Santa Clara, na margem esquerda do rio Mondego. Queres saber mais sobre património, museus ou jardins?",
            "O Portugal dos Pequenitos situa-se na zona de Santa Clara, junto à margem esquerda do Mondego. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)parque verde( do mondego)?(.*)",
        (
            "O Parque Verde do Mondego fica junto ao rio Mondego, numa zona central da cidade. Queres saber mais sobre património, museus ou jardins?",
            "Encontras o Parque Verde do Mondego junto ao rio, numa zona central de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "O Parque Verde do Mondego situa-se junto ao Mondego, numa zona central da cidade. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    # ------------------------------------------------------------------
    # Information about known tourist attractions
    # ------------------------------------------------------------------

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)(universidade de coimbra|universidade|pa[cç]o das escolas)(.*)",
        (
            "A Universidade de Coimbra é um dos principais símbolos da cidade e o Paço das Escolas é o centro do conjunto histórico. Queres saber mais sobre património, museus ou jardins?",
            "A Universidade de Coimbra é um dos pontos históricos mais marcantes da cidade, com o Paço das Escolas no centro do conjunto. Queres saber mais sobre património, museus ou jardins?",
            "A Universidade de Coimbra destaca-se como um dos grandes símbolos da cidade, e o Paço das Escolas integra o seu núcleo histórico. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)biblioteca joanina(.*)",
        (
            "A Biblioteca Joanina é uma biblioteca histórica da Universidade de Coimbra, conhecida sobretudo pelo seu interior barroco. Queres saber mais sobre património, museus ou jardins?",
            "A Biblioteca Joanina pertence à Universidade de Coimbra e é especialmente conhecida pelo seu interior barroco. Queres saber mais sobre património, museus ou jardins?",
            "A Biblioteca Joanina é um espaço histórico da Universidade de Coimbra, destacando-se sobretudo pela decoração barroca do interior. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)s[eé] velha(.*)",
        (
            "A Sé Velha é um dos monumentos medievais mais conhecidos de Coimbra e destaca-se pela arquitetura românica. Queres saber mais sobre património, museus ou jardins?",
            "A Sé Velha é um importante monumento medieval de Coimbra, conhecido pela sua arquitetura românica. Queres saber mais sobre património, museus ou jardins?",
            "A Sé Velha faz parte do património medieval da cidade e distingue-se pelo seu estilo românico. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)s[eé] nova(.*)",
        (
            "A Sé Nova é um dos principais edifícios religiosos da Alta de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "A Sé Nova é um edifício religioso de referência situado na Alta de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "Na Alta encontra-se a Sé Nova, um dos edifícios religiosos mais conhecidos dessa zona da cidade. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)jardim bot[aâ]nico(.*)",
        (
            "O Jardim Botânico da Universidade de Coimbra é um espaço verde histórico indicado para passear e conhecer diferentes espécies vegetais. Queres saber mais sobre património, museus ou jardins?",
            "O Jardim Botânico é um espaço verde histórico da Universidade de Coimbra, adequado para passear e observar diferentes espécies vegetais. Queres saber mais sobre património, museus ou jardins?",
            "Pertencente à Universidade de Coimbra, o Jardim Botânico combina um espaço verde histórico com diferentes espécies vegetais. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)(museu(?: nacional)? )?machado de castro(.*)",
        (
            "O Museu Nacional Machado de Castro reúne coleções de arte e arqueologia e encontra-se junto à Universidade. Queres saber mais sobre património, museus ou jardins?",
            "O Museu Nacional Machado de Castro apresenta coleções de arte e arqueologia e situa-se junto à Universidade de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "No Museu Nacional Machado de Castro podes encontrar coleções ligadas à arte e à arqueologia, perto da Universidade. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)quinta das l[aá]grimas(.*)",
        (
            "A Quinta das Lágrimas é um espaço histórico e ajardinado associado à tradição de Pedro e Inês. Queres saber mais sobre património, museus ou jardins?",
            "A Quinta das Lágrimas combina jardins e património histórico, estando associada à tradição de Pedro e Inês. Queres saber mais sobre património, museus ou jardins?",
            "A Quinta das Lágrimas é um local histórico com jardins, ligado à tradição de Pedro e Inês. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)santa clara(.*)",
        (
            "Santa Clara é uma zona histórica de Coimbra, na margem esquerda do Mondego, onde se encontram vários pontos de interesse. Queres saber mais sobre património, museus ou jardins?",
            "Santa Clara é uma zona histórica situada na margem esquerda do Mondego e reúne vários pontos de interesse. Queres saber mais sobre património, museus ou jardins?",
            "Na margem esquerda do Mondego, Santa Clara é uma zona histórica com vários locais de interesse. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)portugal dos pequenitos(.*)",
        (
            "O Portugal dos Pequenitos é um parque dedicado a representações em escala reduzida de arquitetura e património. Queres saber mais sobre património, museus ou jardins?",
            "O Portugal dos Pequenitos apresenta representações em escala reduzida ligadas à arquitetura e ao património. Queres saber mais sobre património, museus ou jardins?",
            "No Portugal dos Pequenitos encontras representações em escala reduzida de elementos de arquitetura e património. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)parque verde( do mondego)?(.*)",
        (
            "O Parque Verde do Mondego é um espaço verde junto ao rio, adequado para passear e descansar. Queres saber mais sobre património, museus ou jardins?",
            "O Parque Verde do Mondego é uma zona verde junto ao rio indicada para passeios e momentos de descanso. Queres saber mais sobre património, museus ou jardins?",
            "Junto ao Mondego, o Parque Verde é um espaço ao ar livre onde podes passear e descansar. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    # ------------------------------------------------------------------
    # Direct mention of known tourist attractions
    # ------------------------------------------------------------------

    (
        r"^(.*)\buniversidade\b(.*)$",
        (
            "A Universidade de Coimbra é um dos principais símbolos da cidade e o seu núcleo histórico situa-se no Paço das Escolas, na Alta. Queres saber mais sobre património, museus ou jardins?",
            "A Universidade de Coimbra é um dos pontos históricos mais marcantes da cidade e encontra-se na Alta. Queres saber mais sobre património, museus ou jardins?",
            "Na Alta encontra-se a Universidade de Coimbra, um dos grandes símbolos históricos da cidade. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)biblioteca joanina(.*)",
        (
            "A Biblioteca Joanina é uma biblioteca histórica da Universidade de Coimbra, conhecida sobretudo pelo seu interior barroco. Queres saber mais sobre património, museus ou jardins?",
            "A Biblioteca Joanina pertence à Universidade de Coimbra e é especialmente conhecida pelo seu interior barroco. Queres saber mais sobre património, museus ou jardins?",
            "A Biblioteca Joanina é um espaço histórico da Universidade de Coimbra, destacando-se sobretudo pela decoração barroca do interior. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(universidade de coimbra|pa[cç]o das escolas)(.*)",
        (
            "A Universidade de Coimbra e o Paço das Escolas fazem parte do conjunto histórico universitário situado na Alta da cidade. Queres saber mais sobre património, museus ou jardins?",
            "O Paço das Escolas integra o núcleo histórico da Universidade de Coimbra, na Alta. Queres saber mais sobre património, museus ou jardins?",
            "Na Alta podes encontrar a Universidade de Coimbra e o Paço das Escolas, parte central do conjunto histórico universitário. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)s[eé] velha(.*)",
        (
            "A Sé Velha é um dos monumentos medievais mais conhecidos de Coimbra e destaca-se pela arquitetura românica. Queres saber mais sobre património, museus ou jardins?",
            "A Sé Velha é um importante monumento medieval de Coimbra, conhecido pela sua arquitetura românica. Queres saber mais sobre património, museus ou jardins?",
            "A Sé Velha faz parte do património medieval da cidade e distingue-se pelo seu estilo românico. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)s[eé] nova(.*)",
        (
            "A Sé Nova fica na Alta e é um dos principais edifícios religiosos de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "A Sé Nova é um edifício religioso de referência situado na Alta de Coimbra. Queres saber mais sobre património, museus ou jardins?",
            "Na Alta encontra-se a Sé Nova, um dos edifícios religiosos mais conhecidos dessa zona. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)jardim bot[aâ]nico(.*)",
        (
            "O Jardim Botânico da Universidade de Coimbra é um espaço verde histórico, adequado para passear e conhecer diferentes espécies vegetais. Queres saber mais sobre património, museus ou jardins?",
            "O Jardim Botânico é um espaço verde histórico da Universidade de Coimbra onde podes passear e observar diferentes espécies vegetais. Queres saber mais sobre património, museus ou jardins?",
            "Pertencente à Universidade de Coimbra, o Jardim Botânico combina passeio, natureza e diferentes espécies vegetais. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)(museu(?: nacional)? )?machado de castro(.*)",
        (
            "O Museu Nacional Machado de Castro reúne coleções de arte e arqueologia e é uma das principais referências culturais da cidade. Queres saber mais sobre património, museus ou jardins?",
            "O Museu Nacional Machado de Castro é uma referência cultural de Coimbra, com coleções de arte e arqueologia. Queres saber mais sobre património, museus ou jardins?",
            "Entre os espaços culturais da cidade está o Museu Nacional Machado de Castro, dedicado a coleções de arte e arqueologia. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)quinta das l[aá]grimas(.*)",
        (
            "A Quinta das Lágrimas é um espaço histórico e ajardinado associado à tradição de Pedro e Inês. Queres saber mais sobre património, museus ou jardins?",
            "A Quinta das Lágrimas combina jardins e património histórico, estando associada à tradição de Pedro e Inês. Queres saber mais sobre património, museus ou jardins?",
            "A Quinta das Lágrimas é um local histórico com jardins, ligado à tradição de Pedro e Inês. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)santa clara(.*)",
        (
            "Santa Clara é uma zona histórica de Coimbra, na margem esquerda do Mondego, onde se encontram vários pontos de interesse. Queres saber mais sobre património, museus ou jardins?",
            "Santa Clara é uma zona histórica situada na margem esquerda do Mondego e reúne vários pontos de interesse. Queres saber mais sobre património, museus ou jardins?",
            "Na margem esquerda do Mondego, Santa Clara é uma zona histórica com vários locais de interesse. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)portugal dos pequenitos(.*)",
        (
            "O Portugal dos Pequenitos é um parque dedicado a representações em escala reduzida de arquitetura e património. Queres saber mais sobre património, museus ou jardins?",
            "O Portugal dos Pequenitos apresenta representações em escala reduzida ligadas à arquitetura e ao património. Queres saber mais sobre património, museus ou jardins?",
            "No Portugal dos Pequenitos encontras representações em escala reduzida de elementos de arquitetura e património. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)parque verde( do mondego)?(.*)",
        (
            "O Parque Verde do Mondego é um espaço verde junto ao rio, adequado para passear e descansar. Queres saber mais sobre património, museus ou jardins?",
            "O Parque Verde do Mondego é uma zona verde junto ao rio indicada para passeios e momentos de descanso. Queres saber mais sobre património, museus ou jardins?",
            "Junto ao Mondego, o Parque Verde é um espaço ao ar livre onde podes passear e descansar. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),

    # ------------------------------------------------------------------
    # Areas of Coimbra
    # ------------------------------------------------------------------

    (
        r"(.*)(alta|alta de coimbra)(.*)",
        (
            "Na Alta encontram-se a Universidade de Coimbra, a Biblioteca Joanina, a Sé Nova e o Museu Machado de Castro. Sobre qual destes locais queres saber mais?",
            "Na zona da Alta podes conhecer a Universidade de Coimbra, a Biblioteca Joanina, a Sé Nova e o Museu Machado de Castro. Sobre qual destes locais queres saber mais?",
            "A Alta reúne vários pontos de interesse, entre eles a Universidade de Coimbra, a Biblioteca Joanina, a Sé Nova e o Museu Machado de Castro. Sobre qual destes locais queres saber mais?",
        ),
    ),

    (
        r"(.*)(baixa|baixa de coimbra)(.*)",
        (
            "Na Baixa podes explorar o centro histórico e a Praça 8 de Maio. Queres continuar pelo património, pelos museus ou pelos jardins?",
            "A Baixa permite explorar o centro histórico e a Praça 8 de Maio. Preferes depois conhecer património, museus ou jardins?",
            "Na Baixa encontras o centro histórico e a Praça 8 de Maio. Queres saber mais sobre património, museus ou jardins?",
        ),
    ),


    # ------------------------------------------------------------------
    # Ambiguous expressions
    # ------------------------------------------------------------------
    #
    # Some vague expressions are resolved later using the minimal context.
    # If they reach these rules, there was not enough information to resolve
    # them safely.
    # ------------------------------------------------------------------

    (
        r"^\s*(outro|outra|esse|essa|isso|aquele|aquela)\s*$",
        (
            "Essa expressão é demasiado ambígua para eu perceber a que ponto turístico te referes. Podes indicar o nome do local ou dizer se procuras património, museus ou jardins?",
            "Não consigo identificar o local apenas por essa expressão. Podes indicar o nome ou escolher entre património, museus e jardins?",
            "Preciso de um pouco mais de informação para perceber a referência. Podes dizer o nome do local ou escolher património, museus ou jardins?",
        ),
    ),

    (
        r"(.*)\b(esse museu|esse monumento|esse jardim|esse local|essa zona|outro jardim|outro museu|outro monumento)\b(.*)",
        (
            "Não consegui perceber com segurança a que local te referes. Podes escrever o nome do ponto turístico ou indicar a categoria que procuras?",
            "A referência não é suficientemente clara para eu identificar o local. Podes escrever o nome ou indicar se procuras património, museus ou jardins?",
            "Não quero adivinhar a que local te referes. Podes indicar o nome do ponto turístico ou a categoria que procuras?",
        ),
    ),

    # ------------------------------------------------------------------
    # Tourist attraction categories
    # ------------------------------------------------------------------

    (
        r"(.*)(museu|museus)(.*)",
        (
            "Um dos principais museus de Coimbra é o Museu Nacional Machado de Castro. Queres saber mais sobre o Museu Machado de Castro?",
            "Nos museus que conheço em Coimbra, posso falar-te do Museu Nacional Machado de Castro. Queres saber mais sobre o Museu Machado de Castro?",
            "Posso sugerir-te o Museu Nacional Machado de Castro. Queres saber mais sobre o Museu Machado de Castro?",
        ),
    ),

    (
        r"(.*)(patrim[oó]nio|patrim[oó]nio hist[oó]rico|monumento|monumentos|"
        r"arquitetura hist[oó]rica|hist[oó]ria|hist[oó]rico|hist[oó]ricos|"
        r"coimbra antiga|local hist[oó]rico|locais hist[oó]ricos)(.*)",
        (
            "No património de Coimbra podes conhecer a Universidade, a Biblioteca Joanina, a Sé Velha, a Sé Nova, Santa Clara, a Quinta das Lágrimas e o Portugal dos Pequenitos. Sobre qual destes locais queres saber mais?",
            "Dentro do património que conheço podes explorar a Universidade, a Biblioteca Joanina, a Sé Velha, a Sé Nova, Santa Clara, a Quinta das Lágrimas e o Portugal dos Pequenitos. Sobre qual destes locais queres saber mais?",
            "Posso falar-te de vários locais de património: Universidade de Coimbra, Biblioteca Joanina, Sé Velha, Sé Nova, Santa Clara, Quinta das Lágrimas e Portugal dos Pequenitos. Sobre qual destes locais queres saber mais?",
        ),
    ),

    (
        r"(.*)(jardim|jardins|natureza|espa[cç]os verdes|ao ar livre|passear)(.*)",
        (
            "Para espaços verdes, podes conhecer o Jardim Botânico ou o Parque Verde do Mondego. Sobre qual destes locais queres saber mais?",
            "Nos jardins e espaços verdes que conheço, tens o Jardim Botânico e o Parque Verde do Mondego. Sobre qual destes locais queres saber mais?",
            "Posso sugerir-te o Jardim Botânico ou o Parque Verde do Mondego. Sobre qual destes locais queres saber mais?",
        ),
    ),

    # ------------------------------------------------------------------
    # General tourist attraction requests
    # ------------------------------------------------------------------

    (
        r"(.*)(pontos? tur[ií]sticos?|o que posso visitar|o que h[aá] para ver|"
        r"que s[ií]tios devo visitar|quero conhecer coimbra|o que n[aã]o devo perder|"
        r"lugares? que valem a pena|o que recomendas visitar|outro ponto tur[ií]stico|"
        r"outro local tur[ií]stico)(.*)",
        (
            "Posso ajudar-te com pontos turísticos de Coimbra. Preferes património, museus ou jardins?",
            "Conheço alguns dos principais pontos turísticos de Coimbra. Queres começar por património, museus ou jardins?",
            "Podemos começar por uma das três áreas que conheço melhor: património, museus ou jardins. Qual preferes?",
        ),
    ),

    # ------------------------------------------------------------------
    # Recognised tourism topic, but unknown / unsupported information
    # ------------------------------------------------------------------

    (
        r"(.*)(onde fica|onde [ée]|fala[- ]?me|o que sabes sobre|quero saber mais sobre|"
        r"vale a pena visitar|quero visitar|posso visitar)(.*)\b(coimbra)\b(.*)",
        (
            "Percebo que estás a perguntar por um ponto turístico de Coimbra, mas não tenho informação suficiente para identificar esse local. Podes indicar o nome exato do ponto turístico?",
            "A pergunta parece estar dentro do meu domínio, mas não consegui identificar o local. Podes escrever o nome exato do ponto turístico?",
            "Reconheço que estás a falar de turismo em Coimbra, mas falta-me informação para saber qual é o local. Podes indicar o nome?",
        ),
    ),

    (
        r"(.*)\b(museu|monumento|jardim|ponto tur[ií]stico|local hist[oó]rico|"
        r"atra[cç][aã]o tur[ií]stica)\b(.*)",
        (
            "Percebo que a pergunta é sobre pontos turísticos de Coimbra, mas não tenho informação suficiente para responder com segurança. Podes reformular ou indicar um local que eu conheça?",
            "Reconheço o tema turístico, mas não tenho informação suficiente para dar uma resposta fiável. Podes indicar melhor o local?",
            "A pergunta parece estar dentro do meu domínio, mas não consegui identificar informação suficiente. Podes reformular ou indicar o nome do local?",
        ),
    ),

    # ------------------------------------------------------------------
    # Exit
    # ------------------------------------------------------------------

    (
        r"sair",
        (
            "Até à próxima! Espero que tenhas uma boa visita a Coimbra.",
            "Boa visita a Coimbra e até à próxima!",
            "Até breve! Foi um prazer ajudar-te a explorar Coimbra.",
        ),
    ),

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    (
        r"(.*)",
        (
            "Não percebi suficientemente bem a tua pergunta. Podes reformular e indicar o ponto turístico de Coimbra sobre o qual queres saber mais?",
            "Não consegui identificar com segurança o que procuras. Podes dizer o nome de um ponto turístico ou escolher entre património, museus e jardins?",
            "Não tenho informação suficiente para perceber essa mensagem. Podes reformular ou escolher património, museus ou jardins?",
            "Não consegui associar essa frase a um ponto turístico que conheça. Podes tentar dizer de outra forma?",
            "Podes dar-me um pouco mais de informação? Posso ajudar-te com património, museus ou jardins de Coimbra.",
        ),
    ),
)


coimbra_chatbot = Chat(pairs, reflections)


# ------------------------------------------------------------------
# Minimal conversational context
# ------------------------------------------------------------------
#
# We remember only:
#   - the last clearly identified tourist place;
#   - the category of that place (património, museus or jardins);
#   - the action expected after a yes/no question.
#
# This is enough to resolve simple references such as:
#   "ele", "esse museu", "fica onde?", "há outro jardim?", "sim".
#
# No conversation history is stored.

last_place = None
last_category = None
pending_action = None


KNOWN_PLACES = (
    (r"\bbiblioteca joanina\b", "Biblioteca Joanina", "património"),
    (r"\b(?:universidade de coimbra|universidade|pa[cç]o das escolas)\b", "Universidade de Coimbra", "património"),
    (r"\bs[eé] velha\b", "Sé Velha", "património"),
    (r"\bs[eé] nova\b", "Sé Nova", "património"),
    (r"\bjardim bot[aâ]nico\b", "Jardim Botânico", "jardins"),
    (r"\b(?:museu(?: nacional)? )?machado de castro\b", "Museu Nacional Machado de Castro", "museus"),
    (r"\bquinta das l[aá]grimas\b", "Quinta das Lágrimas", "património"),
    (r"\bsanta clara\b", "Santa Clara", "património"),
    (r"\bportugal dos pequenitos\b", "Portugal dos Pequenitos", "património"),
    (r"\bparque verde(?: do mondego)?\b", "Parque Verde do Mondego", "jardins"),
)


CATEGORY_PLACES = {
    "património": (
        "Universidade de Coimbra",
        "Biblioteca Joanina",
        "Sé Velha",
        "Sé Nova",
        "Santa Clara",
        "Quinta das Lágrimas",
        "Portugal dos Pequenitos",
    ),
    "museus": (
        "Museu Nacional Machado de Castro",
    ),
    "jardins": (
        "Jardim Botânico",
        "Parque Verde do Mondego",
    ),
}



YES_PATTERN = re.compile(
    r"^\s*(?:sim|sim por favor|claro|pode ser|est[aá] bem|ok|quero|for[cç]a)\s*[.!?]*\s*$",
    re.IGNORECASE,
)

NO_PATTERN = re.compile(
    r"^\s*(?:n[aã]o|nao|n[aã]o obrigado|nao obrigado|agora n[aã]o|agora nao|"
    r"prefiro n[aã]o|prefiro nao|deixa estar)\s*[.!?]*\s*$",
    re.IGNORECASE,
)


def handle_pending_action(text):
    """Handle a short yes/no answer to the bot's previous question."""
    global pending_action

    if pending_action is None:
        return None

    if YES_PATTERN.match(text):
        action = pending_action
        pending_action = None

        if action == "describe_place" and last_place is not None:
            return coimbra_chatbot.respond(f"quero saber mais sobre {last_place}")

        if action == "show_location" and last_place is not None:
            return coimbra_chatbot.respond(f"onde fica {last_place}")

        if action == "suggest_alternative" and last_category is not None:
            return alternative_response(last_category, last_place)

        return (
            "Percebi a confirmação, mas não tenho uma ação concreta associada. "
            "Queres saber mais sobre património, museus ou jardins?"
        )

    if NO_PATTERN.match(text):
        pending_action = None
        return (
            "Sem problema. Queres saber mais sobre património, museus ou jardins?"
        )

    # If the user answers with something else, we treat it as a new request.
    pending_action = None
    return None

def find_places(text):
    """Return the tourist places clearly mentioned in a text."""
    places = []

    for pattern, place, category in KNOWN_PLACES:
        if re.search(pattern, text, re.IGNORECASE):
            if (place, category) not in places:
                places.append((place, category))

    return places


def get_place_category(place):
    """Return the category of a known tourist place."""
    for _, known_place, category in KNOWN_PLACES:
        if known_place == place:
            return category

    return None


def detect_category(text):
    """Detect a broad tourist category in the user's message."""
    patterns = (
        (
            r"\b(?:patrim[oó]nio|patrim[oó]nio hist[oó]rico|monumento|monumentos|"
            r"local hist[oó]rico|locais hist[oó]ricos|hist[oó]ria|hist[oó]rico|"
            r"hist[oó]ricos|arquitetura hist[oó]rica|coimbra antiga)\b",
            "património",
        ),
        (r"\b(?:museu|museus)\b", "museus"),
        (r"\b(?:jardim|jardins|parque|parques|espa[cç]os verdes|natureza)\b", "jardins"),
    )

    for pattern, category in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return category

    return None


def is_main_category(text):
    """Return True when the user asks directly for a broad tourist category."""
    return bool(
        re.fullmatch(
            r"\s*(?:patrim[oó]nio(?: hist[oó]rico)?|monumentos?|locais? hist[oó]ricos?|hist[oó]ria|museus?|jardins?)\s*",
            text,
            re.IGNORECASE,
        )
    )


def asks_for_alternative(text):
    """Detect requests for another place in the same category."""
    return bool(
        re.search(
            r"\b(?:outro|outra|outros|outras|mais)\b.*"
            r"\b(?:jardim|jardins|parque|parques|museu|museus|monumento|monumentos|patrim[oó]nio|"
            r"local hist[oó]rico|locais hist[oó]ricos)\b",
            text,
            re.IGNORECASE,
        )
        or re.search(
            r"\b(?:h[aá]|ha)\s+(?:mais|outro|outra|outros|outras)\b",
            text,
            re.IGNORECASE,
        )
    )


def alternative_response(category, current_place):
    """Suggest another known place from the same category."""
    global last_place, last_category, pending_action

    places = CATEGORY_PLACES.get(category, ())
    alternatives = [place for place in places if place != current_place]

    if not alternatives:
        category_name = {
            "património": "património",
            "museus": "museus",
            "jardins": "jardins e parques",
        }.get(category, category)

        pending_action = None
        return (
            f"Neste momento, dentro da categoria de {category_name}, não tenho outro local definido além de "
            f"{current_place}. Queres saber mais sobre património, museus ou jardins?"
        )

    if len(alternatives) == 1:
        other = alternatives[0]

        last_place = other
        last_category = category
        pending_action = "describe_place"

        return (
            f"Sim. Dentro da mesma categoria também conheço {other}. "
            f"Queres saber mais sobre {other}?"
        )

    pending_action = None
    options = ", ".join(alternatives[:-1]) + f" ou {alternatives[-1]}"
    return (
        f"Sim. Dentro da mesma categoria também conheço {options}. "
        f"Sobre qual destes locais queres saber mais?"
    )


def has_vague_reference(text):
    """Detect expressions that may refer to the last tourist place."""
    return bool(
        re.search(
            r"\b(?:ele|ela|isso|esse|essa|esse museu|esse monumento|"
            r"esse jardim|esse local|essa zona|l[aá])\b",
            text,
            re.IGNORECASE,
        )
        or re.search(
            r"^\s*(?:onde fica|fica onde|quero saber mais|fala[- ]?me mais)\s*\??\s*$",
            text,
            re.IGNORECASE,
        )
    )


def resolve_reference(text):
    """
    Replace a simple vague reference with the last tourist place.

    Example:
        last_place = "Jardim Botânico"
        "ele fica onde?" -> "onde fica Jardim Botânico"

    Example:
        last_place = "Museu Nacional Machado de Castro"
        "sim quero saber mais sobre ele"
        -> "quero saber mais sobre Museu Nacional Machado de Castro"
    """
    if last_place is None or not has_vague_reference(text):
        return text

    if re.search(r"\b(?:onde|fica|localiza|l[aá])\b", text, re.IGNORECASE):
        return f"onde fica {last_place}"

    if re.search(
        r"\b(?:saber mais|fala[- ]?me mais|sobre ele|sobre ela|sobre isso|"
        r"esse museu|esse monumento|esse jardim|esse local)\b",
        text,
        re.IGNORECASE,
    ):
        return f"quero saber mais sobre {last_place}"

    return f"quero saber mais sobre {last_place}"


def get_response(user_input):
    """Generate a response and update the minimal conversational context."""
    global last_place, last_category, pending_action

    text = user_input.strip()

    # A yes/no answer only has meaning when the bot is waiting for one.
    pending_response = handle_pending_action(text)
    if pending_response is not None:
        return pending_response

    # If the user explicitly asks for another place in the same category,
    # use the current category and previous place before any generic rule.
    if asks_for_alternative(text):
        requested_category = detect_category(text)

        if requested_category:
            last_category = requested_category

        if last_category is not None:
            return alternative_response(last_category, last_place)

    # Going back to a broad category cancels the previous place reference
    # and any pending yes/no action.
    if is_main_category(text):
        last_place = None
        last_category = detect_category(text)
        pending_action = None

    # Resolve simple pronouns and vague references using the previous place.
    resolved_text = resolve_reference(text)

    # If the current message explicitly names one place, remember it.
    explicit_places = find_places(resolved_text)

    response = coimbra_chatbot.respond(resolved_text)

    if len(explicit_places) == 1:
        last_place, last_category = explicit_places[0]
    else:
        # A category response may introduce exactly one place.
        # Example: "museus" -> Museu Nacional Machado de Castro.
        places_in_response = find_places(response or "")

        if len(places_in_response) == 1:
            last_place, last_category = places_in_response[0]
        elif len(places_in_response) > 1:
            # Several places were proposed, so a pronoun would be ambiguous.
            last_place = None

    # If the bot has just asked "Queres saber mais sobre <local>?",
    # remember that a following "sim" means "describe that place".
    pending_action = None

    if response is not None and re.search(
        r"queres saber mais sobre", response, re.IGNORECASE
    ):
        question_part = re.split(
            r"queres saber mais sobre", response, maxsplit=1, flags=re.IGNORECASE
        )[1]

        places_in_question = find_places(question_part)

        if len(places_in_question) == 1:
            last_place, last_category = places_in_question[0]
            pending_action = "describe_place"

    return response


def coimbra_chat():
    global last_place, last_category, pending_action

    last_place = None
    last_category = None
    pending_action = None

    print("Coimbra Guide")
    print("-------------")
    print("Guia virtual especializado apenas em pontos turísticos de Coimbra.")
    print('Escreve "sair" quando quiseres terminar.')
    print("=" * 72)
    print(
        "Olá! Sou o Coimbra Guide. Conheço apenas pontos turísticos de Coimbra. "
        "Preferes património, museus ou jardins?"
    )

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté à próxima!")
            break

        if user_input.lower() == "sair":
            print("Até à próxima!")
            break

        print(get_response(user_input))


def demo():
    coimbra_chat()


if __name__ == "__main__":
    coimbra_chat()
