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

pairs = (

    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------

    (
        r"^(ol[aá]|ola|bom dia|boa tarde|boa noite|hey|viva|boas)(.*)",
        (
            "Olá! Sou o Coimbra Guide e conheço apenas pontos turísticos de Coimbra. Preferes monumentos, museus, jardins ou locais históricos?",
            "Olá! Posso ajudar-te a descobrir pontos turísticos de Coimbra. Queres conhecer monumentos, museus, jardins ou zonas da cidade?",
        ),
    ),

    (
        r"(.*)(quem [ée]s|o que [ée]s|como te chamas|qual [ée] o teu nome)(.*)",
        (
            "Sou o Coimbra Guide, um agente baseado em regras especializado apenas em pontos turísticos de Coimbra. Que local gostarias de conhecer?",
            "Sou um guia virtual com um domínio limitado aos pontos turísticos de Coimbra. Preferes monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(ajuda|o que sabes fazer|como me podes ajudar|o que posso perguntar)(.*)",
        (
            "Posso ajudar-te apenas com pontos turísticos de Coimbra. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
            "O meu domínio são os pontos turísticos de Coimbra. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(obrigad[oa]|muito obrigad[oa]|valeu|agrade[cç]o)(.*)",
        (
            "De nada! Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
            "É um prazer ajudar! Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(adeus|at[eé] logo|at[eé] [aà] pr[oó]xima|tchau|xau)(.*)",
        (
            "Até à próxima! Que ponto turístico de Coimbra gostarias de guardar para uma próxima visita?",
            "Boa visita a Coimbra! Há algum ponto turístico sobre o qual ainda queiras saber alguma coisa?",
        ),
    ),

    (
        r"^\s*(?:n[aã]o sei|nao sei|n[aã]o tenho a certeza|nao tenho a certeza|n[aã]o fa[cç]o ideia|nao faco ideia)\s*$",
        (
            "Sem problema. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
            "Não faz mal não conheceres Coimbra. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    # ------------------------------------------------------------------
    # Location of known tourist attractions
    # ------------------------------------------------------------------

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)(universidade de coimbra|universidade|pa[cç]o das escolas)(.*)",
        (
            "A Universidade de Coimbra fica na Alta da cidade e o núcleo histórico encontra-se no Paço das Escolas. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)biblioteca joanina(.*)",
        (
            "A Biblioteca Joanina fica no Paço das Escolas, no núcleo histórico da Universidade de Coimbra. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)s[eé] velha(.*)",
        (
            "A Sé Velha fica no centro histórico de Coimbra, entre a Baixa e a Universidade. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)s[eé] nova(.*)",
        (
            "A Sé Nova fica na Alta de Coimbra, perto da Universidade. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)jardim bot[aâ]nico(.*)",
        (
            "O Jardim Botânico fica junto à Universidade de Coimbra, na zona da Alta. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)(museu(?: nacional)? )?machado de castro(.*)",
        (
            "O Museu Nacional Machado de Castro fica na Alta, muito perto da Universidade. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)quinta das l[aá]grimas(.*)",
        (
            "A Quinta das Lágrimas fica em Santa Clara, na margem esquerda do Mondego. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)santa clara(.*)",
        (
            "Santa Clara fica na margem esquerda do Mondego e é uma das zonas históricas da cidade. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)portugal dos pequenitos(.*)",
        (
            "O Portugal dos Pequenitos fica em Santa Clara, na margem esquerda do Mondego. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(onde fica|onde [ée]|onde encontro|como chego (a|ao|[aà]))(.*)parque verde( do mondego)?(.*)",
        (
            "O Parque Verde do Mondego fica junto ao rio Mondego, numa zona central da cidade. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    # ------------------------------------------------------------------
    # Information about known tourist attractions
    # ------------------------------------------------------------------

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)(universidade de coimbra|universidade|pa[cç]o das escolas)(.*)",
        (
            "A Universidade de Coimbra é um dos principais símbolos da cidade e o Paço das Escolas é o centro do conjunto histórico. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)biblioteca joanina(.*)",
        (
            "A Biblioteca Joanina é uma biblioteca histórica da Universidade de Coimbra, conhecida sobretudo pelo seu interior barroco. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)s[eé] velha(.*)",
        (
            "A Sé Velha é um dos monumentos medievais mais conhecidos de Coimbra e destaca-se pela arquitetura românica. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)s[eé] nova(.*)",
        (
            "A Sé Nova é um dos principais edifícios religiosos da Alta de Coimbra. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)jardim bot[aâ]nico(.*)",
        (
            "O Jardim Botânico da Universidade de Coimbra é um espaço verde histórico indicado para passear e conhecer diferentes espécies vegetais. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)(museu(?: nacional)? )?machado de castro(.*)",
        (
            "O Museu Nacional Machado de Castro reúne coleções de arte e arqueologia e encontra-se junto à Universidade. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)quinta das l[aá]grimas(.*)",
        (
            "A Quinta das Lágrimas é um espaço histórico e ajardinado associado à tradição de Pedro e Inês. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)santa clara(.*)",
        (
            "Santa Clara é uma zona histórica de Coimbra, na margem esquerda do Mondego, onde se encontram vários pontos de interesse. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)portugal dos pequenitos(.*)",
        (
            "O Portugal dos Pequenitos é um parque dedicado a representações em escala reduzida de arquitetura e património. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(fala[- ]?me (de|da|do|sobre)|o que sabes sobre|o que [ée]|quero saber mais sobre|vale a pena visitar)(.*)parque verde( do mondego)?(.*)",
        (
            "O Parque Verde do Mondego é um espaço verde junto ao rio, adequado para passear e descansar. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    # ------------------------------------------------------------------
    # Direct mention of known tourist attractions
    # ------------------------------------------------------------------

    (
        r"^(.*)\buniversidade\b(.*)$",
        (
            "A Universidade de Coimbra é um dos principais símbolos da cidade e o seu núcleo histórico situa-se no Paço das Escolas, na Alta. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)biblioteca joanina(.*)",
        (
            "A Biblioteca Joanina é uma biblioteca histórica da Universidade de Coimbra, conhecida sobretudo pelo seu interior barroco. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(universidade de coimbra|pa[cç]o das escolas)(.*)",
        (
            "A Universidade de Coimbra e o Paço das Escolas fazem parte do conjunto histórico universitário situado na Alta da cidade. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)s[eé] velha(.*)",
        (
            "A Sé Velha é um dos monumentos medievais mais conhecidos de Coimbra e destaca-se pela arquitetura românica. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)s[eé] nova(.*)",
        (
            "A Sé Nova fica na Alta e é um dos principais edifícios religiosos de Coimbra. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)jardim bot[aâ]nico(.*)",
        (
            "O Jardim Botânico da Universidade de Coimbra é um espaço verde histórico, adequado para passear e conhecer diferentes espécies vegetais. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)(museu(?: nacional)? )?machado de castro(.*)",
        (
            "O Museu Nacional Machado de Castro reúne coleções de arte e arqueologia e é uma das principais referências culturais da cidade. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)quinta das l[aá]grimas(.*)",
        (
            "A Quinta das Lágrimas é um espaço histórico e ajardinado associado à tradição de Pedro e Inês. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)santa clara(.*)",
        (
            "Santa Clara é uma zona histórica de Coimbra, na margem esquerda do Mondego, onde se encontram vários pontos de interesse. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)portugal dos pequenitos(.*)",
        (
            "O Portugal dos Pequenitos é um parque dedicado a representações em escala reduzida de arquitetura e património. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    (
        r"(.*)parque verde( do mondego)?(.*)",
        (
            "O Parque Verde do Mondego é um espaço verde junto ao rio, adequado para passear e descansar. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    # ------------------------------------------------------------------
    # Areas of Coimbra
    # ------------------------------------------------------------------

    (
        r"(.*)(alta|alta de coimbra)(.*)",
        (
            "Na Alta encontram-se a Universidade de Coimbra, a Biblioteca Joanina, a Sé Nova e o Museu Machado de Castro. Sobre qual destes locais queres saber mais?",
        ),
    ),

    (
        r"(.*)(baixa|baixa de coimbra)(.*)",
        (
            "Na Baixa podes explorar o centro histórico e a Praça 8 de Maio. Preferes conhecer um monumento, um museu ou outra zona de Coimbra?",
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
            "Essa expressão é demasiado ambígua para eu perceber a que ponto turístico te referes. Podes indicar o nome do local ou dizer se procuras um monumento, museu, jardim ou local histórico?",
        ),
    ),

    (
        r"(.*)\b(esse museu|esse monumento|esse jardim|esse local|essa zona|outro jardim|outro museu|outro monumento)\b(.*)",
        (
            "Não consegui perceber com segurança a que local te referes. Podes escrever o nome do ponto turístico ou indicar a categoria que procuras?",
        ),
    ),

    # ------------------------------------------------------------------
    # Tourist attraction categories
    # ------------------------------------------------------------------

    (
        r"(.*)(museu|museus)(.*)",
        (
            "Um dos principais museus de Coimbra é o Museu Nacional Machado de Castro. Queres saber mais sobre o Museu Machado de Castro?",
        ),
    ),

    (
        r"(.*)(monumento|monumentos|arquitetura hist[oó]rica|patrim[oó]nio)(.*)",
        (
            "Entre os monumentos de Coimbra podes conhecer a Universidade, a Sé Velha e Santa Clara. Sobre qual destes locais queres saber mais?",
        ),
    ),

    (
        r"(.*)(jardim|jardins|natureza|espa[cç]os verdes|ao ar livre|passear)(.*)",
        (
            "Para espaços verdes, podes conhecer o Jardim Botânico ou o Parque Verde do Mondego. Sobre qual destes locais queres saber mais?",
        ),
    ),

    (
        r"(.*)(hist[oó]ria|hist[oó]rico|hist[oó]ricos|coimbra antiga|locais hist[oó]ricos)(.*)",
        (
            "Para conhecer a história de Coimbra podes começar pela Universidade, pela Sé Velha ou por Santa Clara. Sobre qual destes locais queres saber mais?",
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
            "Posso ajudar-te com pontos turísticos de Coimbra. Preferes monumentos, museus, jardins ou locais históricos?",
            "Conheço alguns dos principais pontos turísticos de Coimbra. Queres começar por monumentos, museus, jardins ou zonas da cidade?",
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
        ),
    ),

    (
        r"(.*)\b(museu|monumento|jardim|ponto tur[ií]stico|local hist[oó]rico|"
        r"atra[cç][aã]o tur[ií]stica)\b(.*)",
        (
            "Percebo que a pergunta é sobre pontos turísticos de Coimbra, mas não tenho informação suficiente para responder com segurança. Podes reformular ou indicar um local que eu conheça?",
        ),
    ),

    # ------------------------------------------------------------------
    # Clearly outside the domain
    # ------------------------------------------------------------------

    (
        r"(.*)\b(comer|jantar|almo[cç]ar|restaurante|restaurantes|caf[eé]|caf[eé]s|"
        r"bar|bares|hotel|hot[eé]is|futebol|pol[ií]tica|medicina|programa[cç][aã]o|"
        r"python|bitcoin|intelig[eê]ncia artificial|tempo|meteorologia)\b(.*)",
        (
            "Essa pergunta está fora do meu domínio. Fui criado apenas para falar sobre pontos turísticos de Coimbra. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
            "Não consigo ajudar com esse tema, porque o meu conhecimento está limitado aos pontos turísticos de Coimbra. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?",
        ),
    ),

    # ------------------------------------------------------------------
    # Exit
    # ------------------------------------------------------------------

    (
        r"sair",
        (
            "Até à próxima! Que ponto turístico de Coimbra gostarias de visitar no futuro?",
        ),
    ),

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------
    #
    # If none of the rules above matches, the message may simply be unclear.
    # We do not assume that it is outside the domain.
    # ------------------------------------------------------------------

    (
        r"(.*)",
        (
            "Não percebi suficientemente bem a tua pergunta. Podes reformular e indicar o ponto turístico de Coimbra sobre o qual queres saber mais?",
            "Não consegui identificar com segurança o que procuras. Podes dizer o nome de um ponto turístico ou escolher entre monumentos, museus, jardins e locais históricos?",
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
#   - the category of that place;
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
    (r"\bbiblioteca joanina\b", "Biblioteca Joanina", "monumentos"),
    (r"\b(?:universidade de coimbra|universidade|pa[cç]o das escolas)\b", "Universidade de Coimbra", "monumentos"),
    (r"\bs[eé] velha\b", "Sé Velha", "monumentos"),
    (r"\bs[eé] nova\b", "Sé Nova", "monumentos"),
    (r"\bjardim bot[aâ]nico\b", "Jardim Botânico", "jardins"),
    (r"\b(?:museu(?: nacional)? )?machado de castro\b", "Museu Nacional Machado de Castro", "museus"),
    (r"\bquinta das l[aá]grimas\b", "Quinta das Lágrimas", "locais históricos"),
    (r"\bsanta clara\b", "Santa Clara", "locais históricos"),
    (r"\bportugal dos pequenitos\b", "Portugal dos Pequenitos", "locais históricos"),
    (r"\bparque verde(?: do mondego)?\b", "Parque Verde do Mondego", "jardins"),
)


CATEGORY_PLACES = {
    "jardins": (
        "Jardim Botânico",
        "Parque Verde do Mondego",
    ),
    "museus": (
        "Museu Nacional Machado de Castro",
    ),
    "monumentos": (
        "Universidade de Coimbra",
        "Sé Velha",
        "Sé Nova",
    ),
    "locais históricos": (
        "Quinta das Lágrimas",
        "Santa Clara",
        "Portugal dos Pequenitos",
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
            "Queres saber mais sobre monumentos, museus, jardins ou locais históricos?"
        )

    if NO_PATTERN.match(text):
        pending_action = None
        return (
            "Sem problema. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?"
        )

    # If the user answers with something else, we treat it as a new request.
    pending_action = None
    return None

def find_places(text):
    """Return the tourist places clearly mentioned in a text."""
    places = []

    for pattern, place, category in KNOWN_PLACES:
        if re.search(pattern, text, re.IGNORECASE):
            if place not in places:
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
        (r"\b(?:jardim|jardins|parque|parques|espa[cç]os verdes|natureza)\b", "jardins"),
        (r"\b(?:museu|museus)\b", "museus"),
        (r"\b(?:monumento|monumentos|patrim[oó]nio)\b", "monumentos"),
        (r"\b(?:local hist[oó]rico|locais hist[oó]ricos|hist[oó]ria|hist[oó]rico|hist[oó]ricos)\b", "locais históricos"),
    )

    for pattern, category in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return category

    return None


def is_main_category(text):
    """Return True when the user asks directly for a broad tourist category."""
    return bool(
        re.fullmatch(
            r"\s*(?:monumentos?|museus?|jardins?|locais? hist[oó]ricos?)\s*",
            text,
            re.IGNORECASE,
        )
    )


def asks_for_alternative(text):
    """Detect requests for another place in the same category."""
    return bool(
        re.search(
            r"\b(?:outro|outra|outros|outras|mais)\b.*"
            r"\b(?:jardim|jardins|parque|parques|museu|museus|monumento|monumentos|"
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
            "museus": "museus",
            "monumentos": "monumentos",
            "jardins": "jardins e parques",
            "locais históricos": "locais históricos",
        }.get(category, category)

        pending_action = None
        return (
            f"Neste momento, dentro da categoria de {category_name}, não tenho outro local definido além de "
            f"{current_place}. Queres saber mais sobre monumentos, museus, jardins ou locais históricos?"
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
        "Preferes monumentos, museus, jardins ou locais históricos?"
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
