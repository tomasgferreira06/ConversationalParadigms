"""
Coimbra Guide — D1 Rule-Based Agent
Natural Language Interaction 2026/2027

Adaptation of the NLTK ELIZA-style chatbot architecture to a new persona:
a virtual tourist guide for the city of Coimbra.

Core mechanism:
    ordered regular expressions -> predefined responses

The implementation intentionally remains rule-based. More specific rules are
placed before more generic ones, and the final rule is the fallback.

Run:
    python coimbra_guide.py

Dependency:
    pip install nltk
"""

import re
import unicodedata
from dataclasses import dataclass

from nltk.chat.util import Chat


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Lightweight normalisation before rule matching.

    Keeps Portuguese accents because they are useful in the generated replies,
    but normalises Unicode, whitespace and some punctuation.
    """
    text = unicodedata.normalize("NFC", text.strip())
    text = re.sub(r"\s+", " ", text)

    # NLTK's original ELIZA converse() strips only some final punctuation.
    # Here we remove common sentence-final punctuation ourselves so patterns
    # do not need to account for it everywhere.
    text = re.sub(r"[.!?…]+$", "", text)

    return text


# A small Portuguese reflection table keeps NLTK Chat's wildcard mechanism
# compatible with captured text. In practice, most captures in this project
# are places, cuisines and interests, so these substitutions are rarely used.
portuguese_reflections = {
    "eu": "tu",
    "meu": "teu",
    "minha": "tua",
    "meus": "teus",
    "minhas": "tuas",
    "tu": "eu",
    "teu": "meu",
    "tua": "minha",
    "teus": "meus",
    "tuas": "minhas",
}



# ---------------------------------------------------------------------------
# Minimal conversational state
# ---------------------------------------------------------------------------

@dataclass
class ConversationState:
    """
    Minimal deterministic conversational memory.

    The bot remains rule-based, but it can:
    - keep a short pending context;
    - remember a food preference and an area;
    - abandon a context after repeated failed replies;
    - allow strong/global intents to interrupt the current context.
    """
    pending_context: str | None = None
    context_failures: int = 0
    last_topic: str | None = None
    food_preference: str | None = None
    area: str | None = None


state = ConversationState()


YES_PATTERN = re.compile(
    r"^\s*(?:sim|claro|pode ser|podes|for[cç]a|porque n[aã]o|"
    r"est[aá] bem|ok|okay|boa|vamos|quero|quero sim)\s*$",
    re.IGNORECASE,
)

NO_PATTERN = re.compile(
    r"^\s*(?:n[aã]o|nao|agora n[aã]o|agora nao|deixa estar|"
    r"n[aã]o obrigado|nao obrigado|prefiro n[aã]o|prefiro nao)\s*$",
    re.IGNORECASE,
)

GOODBYE_PATTERN = re.compile(
    r".*\b(?:adeus|at[eé] logo|at[eé] amanh[aã]|at[eé] [aà] pr[oó]xima|"
    r"tchau|xau|vou[- ]?me embora|tenho de ir|vou andando|falamos depois)\b.*",
    re.IGNORECASE,
)

RESTAURANT_FOLLOWUP_PATTERN = re.compile(
    r"^\s*(?:carne|peixe|marisco|portuguesa|tradicional|regional|"
    r"italiana|italiano|vegetariana|vegetariano|vegan|vegana|"
    r"sushi|japonesa|japon[eê]s)\s*$",
    re.IGNORECASE,
)

TOURISM_CATEGORY_PATTERN = re.compile(
    r"^\s*(?:museus?|monumentos?|jardins?|parques?|hist[oó]ria|"
    r"cultura|natureza|comida|restaurantes?|caf[eé]s?|bares?|"
    r"vida noturna|passeios?)\s*$",
    re.IGNORECASE,
)


def reset_context() -> None:
    state.pending_context = None
    state.context_failures = 0


def set_context(name: str | None) -> None:
    state.pending_context = name
    state.context_failures = 0



GLOBAL_INTERRUPT_PATTERNS = (
    re.compile(r"^\s*(?:ol[aá]|ola|bom dia|boa tarde|boa noite|hey|viva|boas)(?:\b.*)?$", re.IGNORECASE),
    re.compile(r".*\b(?:ajuda|o que sabes fazer|como me podes ajudar)\b.*", re.IGNORECASE),
    re.compile(r".*\b(?:quem [ée]s|o que [ée]s|como te chamas|qual [ée] o teu nome)\b.*", re.IGNORECASE),
    re.compile(r".*\b(?:obrigad[oa]|valeu|agrade[cç]o)\b.*", re.IGNORECASE),
    GOODBYE_PATTERN,
)

CANCEL_CONTEXT_PATTERN = re.compile(
    r".*\b(?:esquece|deixa isso|deixa estar|muda de assunto|"
    r"afinal quero outra coisa|volta atr[aá]s|cancela)\b.*",
    re.IGNORECASE,
)

FOOD_KEYWORDS = {
    "carne": ("carne",),
    "peixe": ("peixe", "marisco"),
    "tradicional": ("portuguesa", "tradicional", "regional"),
    "italiana": ("italiana", "italiano"),
    "vegetariana": ("vegetariana", "vegetariano", "vegan", "vegana"),
    "sushi": ("sushi", "japonesa", "japonês", "japones"),
}

AREA_KEYWORDS = {
    "alta": ("alta", "alta de coimbra"),
    "baixa": ("baixa", "baixa de coimbra"),
    "santa clara": ("santa clara",),
    "universidade": ("universidade", "universidade de coimbra"),
    "praça da república": ("praça da república", "praca da republica"),
    "mondego": ("mondego", "zona ribeirinha", "parque verde"),
}


def is_global_interrupt(user_input: str) -> bool:
    """Return True for intents that should interrupt a pending slot/context."""
    text = normalize_text(user_input)
    return any(pattern.match(text) for pattern in GLOBAL_INTERRUPT_PATTERNS)


def extract_food_preference(user_input: str) -> str | None:
    """Extract a supported food preference from anywhere in the utterance."""
    text = normalize_text(user_input).lower()
    for canonical, variants in FOOD_KEYWORDS.items():
        for variant in variants:
            if re.search(rf"\b{re.escape(variant)}\b", text, re.IGNORECASE):
                return canonical
    return None


def extract_area(user_input: str) -> str | None:
    """Extract a supported Coimbra area from anywhere in the utterance."""
    text = normalize_text(user_input).lower()
    for canonical, variants in AREA_KEYWORDS.items():
        for variant in variants:
            if re.search(rf"\b{re.escape(variant)}\b", text, re.IGNORECASE):
                return canonical
    return None


def food_response(preference: str, area: str | None = None) -> str:
    """Return a deterministic recommendation and always end with a guiding question."""
    area_text = f" na zona da {area}" if area in {"alta", "baixa"} else ""
    if area == "santa clara":
        area_text = " em Santa Clara"
    elif area == "universidade":
        area_text = " perto da Universidade"
    elif area == "praça da república":
        area_text = " perto da Praça da República"
    elif area == "mondego":
        area_text = " junto à zona do Mondego"

    if preference == "carne":
        return f"Se procuras carne{area_text}, aposta em cozinha tradicional portuguesa e grelhados; queres que te sugira uma opção concreta?"
    if preference == "peixe":
        return f"Se preferes peixe ou marisco{area_text}, há opções de cozinha portuguesa em Coimbra; queres uma sugestão mais concreta?"
    if preference == "tradicional":
        return f"Para comida tradicional portuguesa{area_text}, o Zé Manel dos Ossos e o Solar do Bacalhau são referências conhecidas; queres que te indique uma delas?"
    if preference == "italiana":
        return f"Para comida italiana{area_text}, há várias pizzarias e restaurantes italianos no centro; queres que te dê uma sugestão específica?"
    if preference == "vegetariana":
        return f"Para opções vegetarianas{area_text}, há restaurantes e cafés com alternativas adequadas; queres uma recomendação concreta?"
    if preference == "sushi":
        return f"Para sushi ou cozinha japonesa{area_text}, existem várias opções nas zonas centrais e comerciais; queres que te sugira uma?"
    return "Posso ajudar-te a escolher; preferes carne, peixe, tradicional, italiana, vegetariana ou sushi?"


def area_restaurant_response(area: str, preference: str | None) -> str:
    """Handle restaurant-by-area questions, reusing remembered food preference."""
    if preference == "carne" and area == "baixa":
        return "Na Baixa, para carne e cozinha tradicional, podes considerar o Zé Manel dos Ossos ou o Solar do Bacalhau; queres saber mais sobre alguma destas opções?"
    if preference == "tradicional" and area == "baixa":
        return "Na Baixa, para comida tradicional portuguesa, podes considerar o Zé Manel dos Ossos ou o Solar do Bacalhau; qual deles queres explorar?"
    if preference:
        return food_response(preference, area)

    area_labels = {
        "alta": "na Alta",
        "baixa": "na Baixa",
        "santa clara": "em Santa Clara",
        "universidade": "perto da Universidade",
        "praça da república": "perto da Praça da República",
        "mondego": "junto ao Mondego",
    }
    label = area_labels.get(area, f"em {area}")
    return f"Há várias opções {label}; preferes carne, peixe, comida tradicional, italiana, vegetariana ou sushi?"


def ensure_question(response: str) -> str:
    """
    Enforce the conversational design rule that every bot response ends
    with a question that guides the next user turn.
    """
    response = response.strip()
    if response.endswith("?"):
        return response

    # Context-aware generic guiding questions.
    if state.pending_context == "restaurant_preference":
        return response.rstrip(".!") + "; que tipo de comida preferes?"
    if state.pending_context == "tourism_category":
        return response.rstrip(".!") + "; preferes museus, monumentos, jardins, história, comida ou vida noturna?"
    if state.last_topic == "restaurant":
        return response.rstrip(".!") + "; queres outra sugestão para comer?"
    if state.last_topic in {"museums", "monuments", "gardens", "history", "tourism"}:
        return response.rstrip(".!") + "; queres outra sugestão para visitar?"
    if state.last_topic == "nightlife":
        return response.rstrip(".!") + "; queres outra sugestão para sair à noite?"

    return response.rstrip(".!") + "; queres saber mais alguma coisa sobre Coimbra?"


def handle_pending_context(user_input: str) -> str | None:
    """
    Resolve a short follow-up using the current pending context.

    Strong/global intents are intentionally handled outside this function,
    before pending context, so that the user can always change subject.
    """
    text = normalize_text(user_input).lower()

    if not state.pending_context:
        return None

    if CANCEL_CONTEXT_PATTERN.match(text):
        reset_context()
        return "Sem problema, deixamos esse assunto de lado; o que gostarias de saber sobre Coimbra?"

    # A recommendation confirmation is intentionally weak context.
    # If the user writes something other than yes/no, assume they changed topic
    # and let the ordinary rule system handle the new message.
    if state.pending_context == "recommendation_confirmation" and not (
        YES_PATTERN.match(text) or NO_PATTERN.match(text)
    ):
        reset_context()
        return None

    # Generic confirmation / rejection
    if YES_PATTERN.match(text):
        if state.pending_context == "recommendation_confirmation":
            reset_context()
            state.last_topic = "tourism"
            return "Claro, posso sugerir a Universidade de Coimbra, a Sé Velha ou o Jardim Botânico; preferes história, arquitetura ou natureza?"

        if state.pending_context == "tourism_category":
            return "Claro; preferes museus, monumentos, jardins, história, comida ou vida noturna?"

        if state.pending_context == "restaurant_preference":
            return "Claro; preferes carne, peixe, comida tradicional, italiana, vegetariana ou sushi?"

    if NO_PATTERN.match(text):
        reset_context()
        return "Sem problema, podemos mudar de assunto; o que gostarias de saber sobre Coimbra?"

    if state.pending_context == "restaurant_preference":
        preference = extract_food_preference(text)
        if preference:
            state.food_preference = preference
            state.last_topic = "restaurant"
            reset_context()
            return food_response(preference, state.area)

        area = extract_area(text)
        if area:
            state.area = area
            state.context_failures = 0
            return area_restaurant_response(area, state.food_preference)

        state.context_failures += 1
        if state.context_failures == 1:
            return "Ainda não reconheci a preferência; podes dizer, por exemplo, carne, peixe, tradicional, italiana, vegetariana ou sushi?"
        reset_context()
        return "Ainda não consegui perceber a preferência, por isso deixei essa pergunta de lado; o que queres saber agora sobre Coimbra?"

    if state.pending_context == "tourism_category":
        # A complete food request should naturally switch from the broad
        # tourism menu to the restaurant sub-dialogue.
        if re.search(r"\b(?:comer|jantar|almo[cç]ar|restaurante|restaurantes|comida|fome)\b", text):
            preference = extract_food_preference(text)
            state.last_topic = "restaurant"

            if preference:
                state.food_preference = preference
                reset_context()
                return food_response(preference, state.area)

            set_context("restaurant_preference")
            return "Claro, podemos procurar um sítio para comer; preferes carne, peixe, comida tradicional, italiana, vegetariana ou sushi?"

        # A food preference embedded in a longer sentence should also be
        # recognised, e.g. "não sei bem, mas queria carne".
        preference = extract_food_preference(text)
        if preference:
            state.food_preference = preference
            state.last_topic = "restaurant"
            reset_context()
            return food_response(preference, state.area)

        if TOURISM_CATEGORY_PATTERN.match(text):
            reset_context()

            if text.startswith("museu"):
                state.last_topic = "museums"
                return "Recomendo o Museu Nacional Machado de Castro; queres saber onde fica ou o que podes ver lá?"
            if text.startswith("monumento"):
                state.last_topic = "monuments"
                return "Podes começar pela Universidade de Coimbra ou pela Sé Velha; qual dos dois queres conhecer melhor?"
            if text.startswith("jardim") or text.startswith("parque") or text == "natureza":
                state.last_topic = "gardens"
                return "Para natureza, recomendo o Jardim Botânico e um passeio junto ao Mondego; qual preferes?"
            if text in {"história", "historia", "cultura"}:
                state.last_topic = "history"
                return "Para história e cultura, visita a Universidade, a Sé Velha e o Museu Machado de Castro; sobre qual queres saber mais?"
            if text in {"comida", "restaurante", "restaurantes", "cafés", "cafes"}:
                set_context("restaurant_preference")
                state.last_topic = "restaurant"
                return "Claro; preferes carne, peixe, comida tradicional, italiana, vegetariana ou sushi?"
            if text in {"bar", "bares", "vida noturna"}:
                state.last_topic = "nightlife"
                return "Para sair à noite, começa pela Praça da República e pelas zonas próximas da Universidade; queres uma sugestão mais concreta?"
            if text.startswith("passeio"):
                state.last_topic = "walk"
                return "Para um passeio, combina o Jardim Botânico com a zona ribeirinha do Mondego; queres começar pelo jardim ou pelo rio?"

        state.context_failures += 1
        if state.context_failures == 1:
            return "Não reconheci essa categoria; preferes museus, monumentos, jardins, história, comida ou vida noturna?"
        reset_context()
        return "Ainda não percebi a categoria, por isso deixei essa escolha de lado; o que gostarias de descobrir em Coimbra?"

    return None


def update_context_from_turn(user_input: str, response: str) -> None:
    """
    Infer a pending context and update lightweight memory after a successful turn.
    """
    text = normalize_text(user_input).lower()
    response_lower = response.lower()

    preference = extract_food_preference(text)
    if preference:
        state.food_preference = preference
        state.last_topic = "restaurant"

    area = extract_area(text)
    if area:
        state.area = area

    # Restaurant clarification
    if (
        re.search(r"\b(?:comer|jantar|almo[cç]ar|restaurante|restaurantes|fome)\b", text)
        and (
            "preferência" in response_lower
            or "preferes comida" in response_lower
            or "tipo de comida" in response_lower
            or "tipo de cozinha" in response_lower
        )
    ):
        set_context("restaurant_preference")
        state.last_topic = "restaurant"
        return

    # Broad tourism / activity clarification
    if (
        re.search(r"\b(?:visitar|ver|turismo|atividade|atividades|fazer em coimbra)\b", text)
        and (
            "preferes monumentos" in response_lower
            or "preferes cultura" in response_lower
            or "história, cultura" in response_lower
            or "mais cultural" in response_lower
        )
    ):
        set_context("tourism_category")
        state.last_topic = "tourism"
        return

    # Greeting that explicitly asks whether the user wants to discover Coimbra
    if re.match(r"^\s*(?:ol[aá]|ola|bom dia|boa tarde|boa noite|hey|viva|boas)", text):
        set_context("tourism_category")
        state.last_topic = "tourism"
        return

    # Gratitude can naturally be followed by "sim", "pode ser", etc.
    if re.search(r"\b(?:obrigad[oa]|valeu|agrade[cç]o)\b", text):
        set_context("recommendation_confirmation")
        return

    if (
        "posso ajudar-te com mais alguma coisa" in response_lower
        or "se quiseres, posso sugerir mais locais" in response_lower
        or "queres uma sugestão sobre coimbra" in response_lower
    ):
        set_context("recommendation_confirmation")
        return

    # Do not keep stale pending state through unrelated successful turns.
    if not YES_PATTERN.match(text) and not NO_PATTERN.match(text):
        reset_context()


# ---------------------------------------------------------------------------
# Rule catalogue translated to ordered NLTK pairs
# ---------------------------------------------------------------------------
#
# IMPORTANT:
# NLTK Chat tests rules sequentially. Therefore:
#     specific rules -> generic rules -> fallback
#
# Group macros such as %1 reuse captured regex groups in the response.
# ---------------------------------------------------------------------------

pairs = (

    # =======================================================================
    # 1. GOODBYE
    # =======================================================================
    (
        r".*\b(?:adeus|at[eé] logo|at[eé] amanh[aã]|at[eé] [aà] pr[oó]xima|"
        r"tchau|xau|vou[- ]?me embora|tenho de ir|vou andando|falamos depois)\b.*",
        (
            "Até à próxima! Espero que aproveites Coimbra.",
            "Boa visita e até breve!",
            "Até logo! Diverte-te em Coimbra.",
            "Foi um prazer ajudar. Até à próxima!",
        ),
    ),

    # =======================================================================
    # 2. PLACE_LOCATION — specific named places
    # =======================================================================
    (
        r".*\b(?:onde fica|onde [ée]|onde posso encontrar|onde encontro|"
        r"sabes onde fica|como chego (?:a|ao|[aà]))\b.*"
        r"\b(?:universidade de coimbra|universidade|pa[cç]o das escolas)\b.*",
        (
            "A Universidade de Coimbra fica na Alta da cidade. O núcleo histórico principal encontra-se no Paço das Escolas.",
            "O Paço das Escolas, coração histórico da Universidade de Coimbra, fica na Alta de Coimbra.",
        ),
    ),
    (
        r".*\b(?:onde fica|onde [ée]|onde posso encontrar|onde encontro|"
        r"sabes onde fica|como chego (?:a|ao|[aà]))\b.*"
        r"\bbiblioteca joanina\b.*",
        (
            "A Biblioteca Joanina encontra-se no Paço das Escolas, no núcleo histórico da Universidade de Coimbra.",
            "Encontras a Biblioteca Joanina dentro do complexo histórico da Universidade, no Paço das Escolas.",
        ),
    ),
    (
        r".*\b(?:onde fica|onde [ée]|onde posso encontrar|onde encontro|"
        r"sabes onde fica|como chego (?:a|ao|[aà]))\b.*"
        r"\bs[eé] velha\b.*",
        (
            "A Sé Velha fica no centro histórico de Coimbra, no Largo da Sé Velha, entre a Baixa e a Universidade.",
            "Encontras a Sé Velha na zona histórica da cidade, subindo em direção à Alta.",
        ),
    ),
    (
        r".*\b(?:onde fica|onde [ée]|onde posso encontrar|onde encontro|"
        r"sabes onde fica|como chego (?:a|ao|[aà]))\b.*"
        r"\bs[eé] nova\b.*",
        (
            "A Sé Nova fica na Alta de Coimbra, junto à Universidade.",
            "Encontras a Sé Nova na zona da Alta, muito perto do núcleo universitário.",
        ),
    ),
    (
        r".*\b(?:onde fica|onde [ée]|onde posso encontrar|onde encontro|"
        r"sabes onde fica|como chego (?:a|ao|[aà]))\b.*"
        r"\bjardim bot[aâ]nico\b.*",
        (
            "O Jardim Botânico fica junto à Universidade de Coimbra, na encosta entre a Alta e a zona do rio.",
            "O Jardim Botânico encontra-se perto da Universidade, sendo facilmente acessível a partir da Alta.",
        ),
    ),
    (
        r".*\b(?:onde fica|onde [ée]|onde posso encontrar|onde encontro|"
        r"sabes onde fica|como chego (?:a|ao|[aà]))\b.*"
        r"\b(?:museu nacional )?machado de castro\b.*",
        (
            "O Museu Nacional Machado de Castro fica na Alta de Coimbra, muito perto da Universidade.",
            "Encontras o Museu Nacional Machado de Castro no centro histórico, junto à zona universitária.",
        ),
    ),
    (
        r".*\b(?:onde fica|onde [ée]|onde posso encontrar|onde encontro|"
        r"sabes onde fica|como chego (?:a|ao|[aà]))\b.*"
        r"\bquinta das l[aá]grimas\b.*",
        (
            "A Quinta das Lágrimas fica em Santa Clara, na margem esquerda do Mondego.",
            "Encontras a Quinta das Lágrimas na zona de Santa Clara, do outro lado do Mondego em relação à Baixa.",
        ),
    ),
    (
        r".*\b(?:onde fica|onde [ée]|onde posso encontrar|onde encontro|"
        r"sabes onde fica|como chego (?:a|ao|[aà]))\b.*"
        r"\b(?:mosteiro de )?santa clara[- ]a[- ]velha\b.*",
        (
            "O Mosteiro de Santa Clara-a-Velha fica em Santa Clara, na margem esquerda do Mondego.",
            "Encontras Santa Clara-a-Velha junto ao Mondego, na zona de Santa Clara.",
        ),
    ),
    (
        r".*\b(?:onde fica|onde [ée]|onde posso encontrar|onde encontro|"
        r"sabes onde fica|como chego (?:a|ao|[aà]))\b.*"
        r"\bportugal dos pequenitos\b.*",
        (
            "O Portugal dos Pequenitos fica em Santa Clara, na margem esquerda do Mondego.",
            "Encontras o Portugal dos Pequenitos na zona de Santa Clara, perto de vários outros pontos turísticos.",
        ),
    ),


    # =======================================================================
    # AREA_ATTRACTIONS — tourist zones / neighbourhoods
    # =======================================================================
    # Alternative word order: "O que a Alta de Coimbra tem para ver?"
    (
        r".*\b(?:alta(?: de coimbra)?)\b.*\b(?:tem para ver|h[aá] para ver|"
        r"posso visitar|devo visitar|posso fazer|recomendas)\b.*",
        (
            "Na Alta podes visitar a Universidade de Coimbra, o Paço das Escolas, a Biblioteca Joanina, a Sé Nova e o Museu Nacional Machado de Castro.",
            "A Alta concentra vários dos principais pontos históricos: Universidade, Biblioteca Joanina, Sé Nova e Museu Machado de Castro.",
        ),
    ),
    (
        r".*\b(?:baixa(?: de coimbra)?)\b.*\b(?:tem para ver|h[aá] para ver|"
        r"posso visitar|devo visitar|posso fazer|recomendas)\b.*",
        (
            "Na Baixa podes explorar a Praça 8 de Maio, a Igreja de Santa Cruz, as ruas comerciais e subir pela zona histórica em direção à Universidade.",
            "A Baixa é boa para passear, comer e começar a subida pelo centro histórico.",
        ),
    ),
    (
        r".*\b(?:santa clara)\b.*\b(?:tem para ver|h[aá] para ver|"
        r"posso visitar|devo visitar|posso fazer|recomendas)\b.*",
        (
            "Em Santa Clara podes visitar o Mosteiro de Santa Clara-a-Velha, o Portugal dos Pequenitos e a Quinta das Lágrimas.",
            "Santa Clara reúne vários pontos turísticos na margem esquerda do Mondego.",
        ),
    ),
    (
        r".*\b(?:o que (?:h[aá]|tem) para ver|o que posso visitar|"
        r"que s[ií]tios (?:h[aá]|existem)|o que recomendas|"
        r"o que posso fazer)\b.*\b(?:alta(?: de coimbra)?)\b.*",
        (
            "Na Alta podes visitar a Universidade de Coimbra, o Paço das Escolas, a Biblioteca Joanina, a Sé Nova e o Museu Nacional Machado de Castro.",
            "A Alta concentra vários dos principais pontos históricos: Universidade, Biblioteca Joanina, Sé Nova e Museu Machado de Castro.",
        ),
    ),
    (
        r".*\b(?:o que (?:h[aá]|tem) para ver|o que posso visitar|"
        r"que s[ií]tios (?:h[aá]|existem)|o que recomendas|"
        r"o que posso fazer)\b.*\b(?:baixa(?: de coimbra)?)\b.*",
        (
            "Na Baixa podes explorar a Praça 8 de Maio, a Igreja de Santa Cruz, as ruas comerciais e subir pela zona histórica em direção à Universidade.",
            "A Baixa é boa para passear, comer e começar a subida pelo centro histórico.",
        ),
    ),
    (
        r".*\b(?:o que (?:h[aá]|tem) para ver|o que posso visitar|"
        r"que s[ií]tios (?:h[aá]|existem)|o que recomendas|"
        r"o que posso fazer)\b.*\b(?:santa clara)\b.*",
        (
            "Em Santa Clara podes visitar o Mosteiro de Santa Clara-a-Velha, o Portugal dos Pequenitos e a Quinta das Lágrimas.",
            "Santa Clara reúne vários pontos turísticos na margem esquerda do Mondego, como Santa Clara-a-Velha, Portugal dos Pequenitos e Quinta das Lágrimas.",
        ),
    ),
    (
        r".*\b(?:o que (?:h[aá]|tem) para ver|o que posso visitar|"
        r"que s[ií]tios (?:h[aá]|existem)|o que recomendas|"
        r"o que posso fazer)\b.*\b(?:mondego|zona ribeirinha|parque verde)\b.*",
        (
            "Junto ao Mondego podes passear pela zona ribeirinha e pelo Parque Verde, uma opção mais relaxada e ao ar livre.",
            "A zona do Mondego é boa para caminhar e descansar, especialmente junto ao Parque Verde.",
        ),
    ),
    (
        r".*\b(?:o que (?:h[aá]|tem) para ver|o que posso visitar|"
        r"que s[ií]tios (?:h[aá]|existem)|o que recomendas|"
        r"o que posso fazer)\b.*\b(?:pra[cç]a da rep[uú]blica)\b.*",
        (
            "A Praça da República é sobretudo uma zona de convívio e vida estudantil, próxima do Jardim da Sereia e da Alta.",
            "Na Praça da República encontras ambiente estudantil e acesso fácil à Alta e ao Jardim da Sereia.",
        ),
    ),

    # Generic place-location capture. It is intentionally below the known
    # locations so that the specific factual replies win first.
    (
        r".*\b(?:onde fica|onde [ée]|onde posso encontrar|onde encontro|"
        r"sabes onde fica)\b\s+(.*)",
        (
            "Não tenho uma localização detalhada para %1. Posso ajudar melhor se for um dos principais locais turísticos de Coimbra.",
            "Reconheço que procuras a localização de %1, mas a minha base de regras cobre apenas alguns locais turísticos de Coimbra.",
        ),
    ),

    # =======================================================================
    # 3. PLACE_INFORMATION — specific named places
    # =======================================================================
    (
        r".*\b(?:o que [ée]|fala[- ]?me (?:d[aeo]|sobre)|o que sabes sobre|"
        r"conta[- ]?me (?:algo|alguma coisa) sobre|quero saber mais sobre|"
        r"conheces|d[aá][- ]?me informa[cç][aã]o sobre|vale a pena visitar)\b.*"
        r"\b(?:universidade de coimbra|universidade|pa[cç]o das escolas)\b.*",
        (
            "A Universidade de Coimbra é uma das instituições universitárias históricas mais conhecidas de Portugal. O Paço das Escolas é o núcleo monumental mais emblemático da visita.",
            "A Universidade de Coimbra domina a Alta da cidade e reúne vários espaços históricos, entre eles o Paço das Escolas e a Biblioteca Joanina.",
        ),
    ),
    (
        r".*\b(?:o que [ée]|fala[- ]?me (?:d[aeo]|sobre)|o que sabes sobre|"
        r"conta[- ]?me (?:algo|alguma coisa) sobre|quero saber mais sobre|"
        r"conheces|d[aá][- ]?me informa[cç][aã]o sobre|vale a pena visitar)\b.*"
        r"\bbiblioteca joanina\b.*",
        (
            "A Biblioteca Joanina é uma biblioteca histórica integrada no conjunto da Universidade de Coimbra e é conhecida pelo seu interior barroco.",
            "A Biblioteca Joanina faz parte do Paço das Escolas e é um dos espaços históricos mais visitados da Universidade.",
        ),
    ),
    (
        r".*\b(?:o que [ée]|fala[- ]?me (?:d[aeo]|sobre)|o que sabes sobre|"
        r"conta[- ]?me (?:algo|alguma coisa) sobre|quero saber mais sobre|"
        r"conheces|d[aá][- ]?me informa[cç][aã]o sobre|vale a pena visitar)\b.*"
        r"\bs[eé] velha\b.*",
        (
            "A Sé Velha é a catedral medieval de Coimbra e um dos monumentos românicos mais marcantes da cidade.",
            "A Sé Velha destaca-se pela arquitetura românica e pela sua localização no coração da zona histórica.",
        ),
    ),
    (
        r".*\b(?:o que [ée]|fala[- ]?me (?:d[aeo]|sobre)|o que sabes sobre|"
        r"conta[- ]?me (?:algo|alguma coisa) sobre|quero saber mais sobre|"
        r"conheces|d[aá][- ]?me informa[cç][aã]o sobre|vale a pena visitar)\b.*"
        r"\bs[eé] nova\b.*",
        (
            "A Sé Nova é a atual sede episcopal de Coimbra e encontra-se na Alta, junto à Universidade.",
            "A Sé Nova é um dos principais edifícios religiosos da Alta de Coimbra.",
        ),
    ),
    (
        r".*\b(?:o que [ée]|fala[- ]?me (?:d[aeo]|sobre)|o que sabes sobre|"
        r"conta[- ]?me (?:algo|alguma coisa) sobre|quero saber mais sobre|"
        r"conheces|d[aá][- ]?me informa[cç][aã]o sobre|vale a pena visitar)\b.*"
        r"\bjardim bot[aâ]nico\b.*",
        (
            "O Jardim Botânico da Universidade de Coimbra é um grande espaço verde histórico, adequado para passear e conhecer diferentes espécies vegetais.",
            "O Jardim Botânico combina património universitário, natureza e zonas tranquilas para passeio.",
        ),
    ),
    (
        r".*\b(?:o que [ée]|fala[- ]?me (?:d[aeo]|sobre)|o que sabes sobre|"
        r"conta[- ]?me (?:algo|alguma coisa) sobre|quero saber mais sobre|"
        r"conheces|d[aá][- ]?me informa[cç][aã]o sobre|vale a pena visitar)\b.*"
        r"\b(?:museu nacional )?machado de castro\b.*",
        (
            "O Museu Nacional Machado de Castro reúne coleções de arte e arqueologia e é também conhecido pelo criptopórtico romano preservado sob o edifício.",
            "O Museu Nacional Machado de Castro é uma referência cultural de Coimbra, junto à Universidade.",
        ),
    ),
    (
        r".*\b(?:o que [ée]|fala[- ]?me (?:d[aeo]|sobre)|o que sabes sobre|"
        r"conta[- ]?me (?:algo|alguma coisa) sobre|quero saber mais sobre|"
        r"conheces|d[aá][- ]?me informa[cç][aã]o sobre|vale a pena visitar)\b.*"
        r"\bquinta das l[aá]grimas\b.*",
        (
            "A Quinta das Lágrimas é um espaço histórico e ajardinado associado à tradição da história de Pedro e Inês.",
            "A Quinta das Lágrimas combina jardins, património e a memória cultural ligada a Pedro e Inês.",
        ),
    ),
    (
        r".*\b(?:o que [ée]|fala[- ]?me (?:d[aeo]|sobre)|o que sabes sobre|"
        r"conta[- ]?me (?:algo|alguma coisa) sobre|quero saber mais sobre|"
        r"conheces|d[aá][- ]?me informa[cç][aã]o sobre|vale a pena visitar)\b.*"
        r"\b(?:mosteiro de )?santa clara[- ]a[- ]velha\b.*",
        (
            "O Mosteiro de Santa Clara-a-Velha é um conjunto monástico histórico situado junto ao Mondego, em Santa Clara.",
            "Santa Clara-a-Velha é um importante local histórico da margem esquerda do Mondego.",
        ),
    ),
    (
        r".*\b(?:o que [ée]|fala[- ]?me (?:d[aeo]|sobre)|o que sabes sobre|"
        r"conta[- ]?me (?:algo|alguma coisa) sobre|quero saber mais sobre|"
        r"conheces|d[aá][- ]?me informa[cç][aã]o sobre|vale a pena visitar)\b.*"
        r"\bportugal dos pequenitos\b.*",
        (
            "O Portugal dos Pequenitos é um parque temático dedicado a representações em escala reduzida de arquitetura e património.",
            "O Portugal dos Pequenitos é uma atração de caráter educativo e recreativo situada em Santa Clara.",
        ),
    ),

    # Generic place information capture.
    (
        r".*\b(?:fala[- ]?me (?:d[aeo]|sobre)|o que sabes sobre|"
        r"quero saber mais sobre|d[aá][- ]?me informa[cç][aã]o sobre)\b\s+(.*)",
        (
            "Não tenho uma descrição específica de %1 na minha base de regras. Posso falar-te de alguns dos principais locais turísticos de Coimbra.",
            "Ainda não tenho informação detalhada sobre %1. Experimenta perguntar-me pela Universidade, Biblioteca Joanina, Sé Velha, Jardim Botânico ou Museu Machado de Castro.",
        ),
    ),

    # =======================================================================
    # 4. RESTAURANT_CUISINE
    # =======================================================================
    (
        r".*\b(?:comida |cozinha |restaurante(?:s)? (?:de )?)?"
        r"(portuguesa|tradicional|regional)\b.*",
        (
            "Se procuras comida %1, podes considerar restaurantes de cozinha tradicional no centro histórico, como o Zé Manel dos Ossos ou o Solar do Bacalhau.",
            "Para comida %1, a Baixa de Coimbra tem várias opções de cozinha portuguesa tradicional.",
        ),
    ),
    (
        r".*\b(?:comida |cozinha |restaurante(?:s)? (?:de )?)?"
        r"(italiana|italiano)\b.*",
        (
            "Se te apetece comida italiana, procura uma pizzaria ou restaurante italiano na Baixa ou na zona central de Coimbra.",
            "Para comida italiana, há várias opções no centro da cidade; posso também sugerir-te comida tradicional portuguesa.",
        ),
    ),
    (
        r".*\b(?:comida |cozinha |restaurante(?:s)? (?:de )?)?"
        r"(vegetariana|vegetariano|vegan|vegana)\b.*",
        (
            "Se procuras uma opção %1, o centro de Coimbra tem restaurantes e cafés com alternativas vegetarianas.",
            "Para comida %1, aconselho procurar opções na Baixa e nas zonas próximas da Universidade.",
        ),
    ),
    (
        r".*\b(sushi|japonesa|japon[eê]s)\b.*",
        (
            "Se te apetece %1, há restaurantes de cozinha japonesa em Coimbra, sobretudo nas zonas centrais e comerciais.",
            "Para %1, posso orientar-te para a zona central de Coimbra, onde existem várias opções.",
        ),
    ),


    (
        r".*\b(carne)\b.*",
        (
            "Se procuras carne, podes optar por restaurantes de cozinha tradicional portuguesa na Baixa e no centro histórico.",
            "Para carne, procura restaurantes tradicionais portugueses no centro de Coimbra.",
        ),
    ),
    (
        r".*\b(peixe|marisco)\b.*",
        (
            "Se preferes %1, procura restaurantes portugueses no centro e nas zonas mais movimentadas da cidade.",
            "Para %1, há opções de cozinha portuguesa em várias zonas centrais de Coimbra.",
        ),
    ),

    # =======================================================================
    # 5. RECOMMENDATION_INTEREST
    # =======================================================================
    (
        r".*\b(?:gosto (?:muito )?de|prefiro|tenho interesse (?:em|por)|adoro)\b.*"
        r"\b(hist[oó]ria|patrim[oó]nio)\b.*",
        (
            "Se gostas de %1, começa pela Universidade de Coimbra, Sé Velha e Mosteiro de Santa Clara-a-Velha.",
            "Para alguém interessado em %1, a Alta de Coimbra e os monumentos históricos são uma excelente escolha.",
        ),
    ),
    (
        r".*\b(?:gosto (?:muito )?de|prefiro|tenho interesse (?:em|por)|adoro)\b.*"
        r"\b(arte|cultura)\b.*",
        (
            "Se gostas de %1, o Museu Nacional Machado de Castro é uma boa opção.",
            "Para %1, podes combinar o Museu Machado de Castro com uma visita à Universidade.",
        ),
    ),
    (
        r".*\b(?:gosto (?:muito )?de|prefiro|tenho interesse (?:em|por)|adoro)\b.*"
        r"\b(natureza|espa[cç]os verdes|jardins?)\b.*",
        (
            "Se gostas de %1, o Jardim Botânico é uma escolha natural para um passeio.",
            "Para %1, podes visitar o Jardim Botânico ou passear junto ao Mondego.",
        ),
    ),
    (
        r".*\b(?:gosto (?:muito )?de|prefiro|tenho interesse (?:em|por)|adoro)\b.*"
        r"\b(arquitetura)\b.*",
        (
            "Se gostas de %1, visita a Universidade, a Sé Velha e a Sé Nova para veres estilos arquitetónicos diferentes.",
            "Para %1, a Alta de Coimbra oferece vários edifícios históricos interessantes.",
        ),
    ),
    (
        r".*\b(?:prefiro|gosto de)\b.*\b(s[ií]tios tranquilos|lugares calmos|tranquilidade)\b.*",
        (
            "Se procuras %1, experimenta o Jardim Botânico ou um passeio junto ao Mondego.",
            "Para um ambiente mais tranquilo, o Jardim Botânico é uma boa opção.",
        ),
    ),

    # =======================================================================
    # 6. RECOMMENDATION_CATEGORY
    # =======================================================================
    (
        r".*\b(?:(?:recomenda|sugere|aconselha)[- ]?me\b.*\bmuseu\b|"
        r"(?:que|qual)\s+museu\s+(?:recomendas|sugeres|aconselhas|devo visitar))\b.*",
        (
            "Se procuras um museu, recomendo o Museu Nacional Machado de Castro.",
            "Uma boa opção é o Museu Nacional Machado de Castro, perto da Universidade.",
        ),
    ),
    (
        r".*\b(?:(?:recomenda|sugere|aconselha)[- ]?me\b.*\bmonumento\b|"
        r"(?:que|qual)\s+monumento\s+(?:recomendas|sugeres|aconselhas|devo visitar))\b.*",
        (
            "Se procuras um monumento, podes começar pela Universidade de Coimbra ou pela Sé Velha.",
            "Uma boa opção é a Sé Velha, no centro histórico.",
        ),
    ),
    (
        r".*\b(?:(?:recomenda|sugere|aconselha)[- ]?me\b.*\b(?:jardim|parque)\b|"
        r"(?:que|qual)\s+(?:jardim|parque)\s+(?:recomendas|sugeres|aconselhas|devo visitar))\b.*",
        (
            "Se procuras um jardim, recomendo o Jardim Botânico da Universidade de Coimbra.",
            "Para um passeio ao ar livre, o Jardim Botânico é uma ótima opção.",
        ),
    ),
    (
        r".*\b(?:(?:recomenda|sugere|aconselha)[- ]?me\b.*\brestaurante\b|"
        r"(?:que|qual)\s+restaurante\s+(?:recomendas|sugeres|aconselhas|devo escolher))\b.*",
        (
            "Para um restaurante, podes considerar o Zé Manel dos Ossos, o Solar do Bacalhau ou outras opções na Baixa.",
            "Se queres um restaurante, diz-me primeiro se procuras comida tradicional, italiana, vegetariana ou outro estilo.",
        ),
    ),
    (
        r".*\b(?:(?:recomenda|sugere|aconselha)[- ]?me\b.*\bcaf[eé]\b|"
        r"(?:que|qual)\s+caf[eé]\s+(?:recomendas|sugeres|aconselhas))\b.*",
        (
            "Se procuras um café, o Café Santa Cruz é uma opção conhecida no centro histórico.",
            "Para tomar café no centro, podes considerar o Café Santa Cruz.",
        ),
    ),
    (
        r".*\b(?:(?:recomenda|sugere|aconselha)[- ]?me\b.*\bbar\b|"
        r"(?:que|qual)\s+bar\s+(?:recomendas|sugeres|aconselhas))\b.*",
        (
            "Para sair à noite, explora a Praça da República e as zonas próximas da Universidade.",
            "Se procuras um bar, a zona da Praça da República é um bom ponto de partida.",
        ),
    ),

    # =======================================================================
    # 7. MUSEUMS
    # =======================================================================
    (
        r".*\b(?:museu|museus)\b.*",
        (
            "Uma das principais opções é o Museu Nacional Machado de Castro, junto à Universidade.",
            "Podes visitar o Museu Nacional Machado de Castro. Também existem outros espaços culturais espalhados pela cidade.",
            "Se queres um museu, começaria pelo Museu Nacional Machado de Castro.",
        ),
    ),

    # =======================================================================
    # 8. MONUMENTS
    # =======================================================================
    (
        r".*\b(?:monumento|monumentos|edif[ií]cios hist[oó]ricos|"
        r"arquitetura hist[oó]rica|patrim[oó]nio hist[oó]rico)\b.*",
        (
            "Entre os monumentos de Coimbra, podes visitar a Universidade, a Sé Velha e Santa Clara-a-Velha.",
            "Para património histórico, a Alta de Coimbra e a Sé Velha são bons pontos de partida.",
            "Uma combinação interessante é Universidade de Coimbra, Sé Velha e Mosteiro de Santa Clara-a-Velha.",
        ),
    ),

    # =======================================================================
    # 9. GARDENS
    # =======================================================================
    (
        r".*\b(?:jardim|jardins|parque|parques|espa[cç]os? verdes?|"
        r"ao ar livre|passear)\b.*",
        (
            "Para passear ao ar livre, recomendo o Jardim Botânico da Universidade de Coimbra.",
            "O Jardim Botânico é uma boa opção se procuras natureza e tranquilidade.",
            "Também podes combinar um passeio pelo Jardim Botânico com a zona ribeirinha do Mondego.",
        ),
    ),

    # =======================================================================
    # 10. HISTORICAL
    # =======================================================================
    (
        r".*\b(?:hist[oó]ria de coimbra|locais? hist[oó]ricos?|"
        r"s[ií]tios? hist[oó]ricos?|coimbra antiga|parte hist[oó]rica|"
        r"zonas? hist[oó]ricas?|lugares? antigos?)\b.*",
        (
            "Para conhecer a história de Coimbra, começa pela Universidade, Sé Velha e Santa Clara-a-Velha.",
            "A Alta e a zona da Sé Velha são essenciais para explorar o lado histórico da cidade.",
            "Se procuras história, a Universidade de Coimbra e os monumentos da Alta são ótimos pontos de partida.",
        ),
    ),

    # =======================================================================
    # 11. NIGHTLIFE
    # =======================================================================
    (
        r".*\b(?:sair [aà] noite|vida noturna|bares?|beber um copo|"
        r"ir beber|depois do jantar)\b.*",
        (
            "Para sair à noite, a Praça da República e as zonas próximas da Universidade são bons pontos de partida.",
            "A vida noturna de Coimbra está muito ligada às zonas estudantis, especialmente perto da Praça da República.",
            "Se queres beber um copo, começa pela zona da Praça da República e explora a partir daí.",
        ),
    ),

    # =======================================================================
    # 12. CAFE
    # =======================================================================
    (
        r".*\b(?:caf[eé]|caf[eé]s|tomar caf[eé]|beber caf[eé]|lanchar|"
        r"pequeno[- ]almo[cç]o|fazer uma pausa)\b.*",
        (
            "Para tomar café no centro histórico, podes considerar o Café Santa Cruz.",
            "Uma opção conhecida é o Café Santa Cruz, na Praça 8 de Maio.",
            "Se queres fazer uma pausa, há vários cafés na Baixa e junto à zona universitária.",
        ),
    ),

    # =======================================================================
    # 12.5 RESTAURANT_AREA
    # =======================================================================
    (
        r".*\b(?:restaurante|restaurantes|comer|jantar|almo[cç]ar)\b.*\b(?:baixa(?: de coimbra)?)\b.*",
        (
            "Na Baixa há várias opções de restauração; preferes carne, peixe, comida tradicional, italiana, vegetariana ou sushi?",
        ),
    ),
    (
        r".*\b(?:restaurante|restaurantes|comer|jantar|almo[cç]ar)\b.*\b(?:alta(?: de coimbra)?)\b.*",
        (
            "Na Alta e nas zonas próximas da Universidade há várias opções para comer; que tipo de comida procuras?",
        ),
    ),
    (
        r".*\b(?:restaurante|restaurantes|comer|jantar|almo[cç]ar)\b.*\b(?:santa clara)\b.*",
        (
            "Em Santa Clara também encontras opções de restauração; preferes carne, peixe, tradicional, italiana, vegetariana ou sushi?",
        ),
    ),

    # =======================================================================
    # 13. RESTAURANT_GENERAL
    # =======================================================================
    (
        r".*\b(?:onde posso |quero |preciso de (?:um s[ií]tio para )?|"
        r"apetece[- ]?me )?(?:comer|jantar|almo[cç]ar|fazer uma refei[cç][aã]o)\b.*",
        (
            "Claro. Procuras algum tipo de comida em particular? Por exemplo: tradicional, italiana ou vegetariana.",
            "Há várias opções em Coimbra. Preferes comida portuguesa tradicional ou outro tipo de cozinha?",
            "Posso ajudar. Tens alguma preferência de comida?",
        ),
    ),
    (
        r".*\b(?:restaurante|restaurantes|onde se come bem|estou com fome)\b.*",
        (
            "Há várias opções. Preferes comida tradicional, italiana, vegetariana ou outro tipo?",
            "Se me disseres que tipo de comida procuras, consigo dar-te uma sugestão mais específica.",
            "Para restaurantes, a Baixa e o centro histórico têm várias opções. Que tipo de cozinha preferes?",
        ),
    ),

    # =======================================================================
    # 14. ATTRACTIONS_GENERAL
    # =======================================================================
    (
        r".*\b(?:o que posso visitar|o que h[aá] para ver|"
        r"que s[ií]tios devo visitar|pontos? tur[ií]sticos?|"
        r"o que recomendas visitar|quero conhecer coimbra|"
        r"fazer turismo|lugares? que valem a pena|"
        r"o que n[aã]o devo perder|atra[cç][oõ]es?|"
        r"locais? mais conhecidos|s[ií]tios? interessantes)\b.*",
        (
            "Coimbra tem vários locais interessantes. Preferes monumentos, museus, jardins ou zonas históricas?",
            "Podes começar pela Universidade, Sé Velha, Jardim Botânico e zona de Santa Clara. Queres algum tipo de local em particular?",
            "Há muito para visitar. Posso sugerir-te história, cultura, jardins ou comida, dependendo do que preferes.",
        ),
    ),

    # =======================================================================
    # 15. ACTIVITIES
    # =======================================================================
    (
        r".*\b(?:o que posso fazer|que atividades|atividades existem|"
        r"nada para fazer|o que h[aá] para fazer|quero fazer alguma coisa|"
        r"como posso passar a tarde|durante o dia|quero uma atividade|"
        r"experi[eê]ncias?)\b.*",
        (
            "Depende do que procuras. Preferes cultura, passeios, comida ou vida noturna?",
            "Podes fazer uma visita cultural, passear pelo Jardim Botânico, explorar a Baixa ou descobrir a vida noturna.",
            "Queres algo mais cultural, relaxado ou ligado à noite de Coimbra?",
        ),
    ),

    # =======================================================================
    # 16. HELP
    # =======================================================================
    (
        r".*\b(?:ajuda|preciso de ajuda|o que posso perguntar|como funciona|"
        r"como te posso usar|como me podes ajudar|que perguntas posso fazer|"
        r"que informa[cç][oõ]es tens|mostra[- ]?me o que sabes fazer|"
        r"o que sabes fazer)\b.*",
        (
            "Posso ajudar-te com monumentos, museus, jardins, restaurantes, cafés, bares e atividades em Coimbra.",
            'Podes perguntar-me "o que posso visitar?", "onde posso jantar?" ou "fala-me da Biblioteca Joanina".',
            "O meu domínio é o turismo em Coimbra: locais a visitar, comida, cafés, vida noturna e atividades.",
        ),
    ),

    # =======================================================================
    # 17. BOT_CAPABILITIES
    # =======================================================================
    (
        r".*\b(?:conheces coimbra|sabes .*coimbra|sabes recomendar|"
        r"podes recomendar|podes ajudar[- ]?me a visitar|"
        r"consegues sugerir|sabes onde comer|podes ser meu guia|"
        r"consegues ajudar turistas)\b.*",
        (
            "Sim. Sou especializado em turismo em Coimbra e posso ajudar com locais, comida e atividades.",
            "Posso recomendar monumentos, museus, jardins, restaurantes, cafés e opções de vida noturna.",
            "O meu domínio é o turismo em Coimbra.",
        ),
    ),

    # =======================================================================
    # 18. BOT_IDENTITY
    # =======================================================================
    (
        r".*\b(?:quem [ée]s|o que [ée]s|qual [ée] o teu nome|"
        r"como te chamas|[ée]s um guia|[ée]s um chatbot|"
        r"[ée]s humano|quem est[aá] a falar comigo|"
        r"que tipo de assistente [ée]s|[ée]s o coimbra guide)\b.*",
        (
            "Sou o Coimbra Guide, um guia turístico virtual especializado na cidade de Coimbra.",
            "Sou um chatbot baseado em regras criado para ajudar visitantes de Coimbra.",
            "Chamo-me Coimbra Guide e posso ajudar-te a descobrir a cidade.",
        ),
    ),

    # =======================================================================
    # 19. GREETING
    # =======================================================================
    (
        r"^\s*(?:ol[aá]|bom dia|boa tarde|boa noite|hey|viva|boas)"
        r"(?:\s+guia)?(?:,\s*tudo bem)?\s*$",
        (
            "Olá! Bem-vindo a Coimbra. Em que posso ajudar?",
            "Olá! Queres descobrir monumentos, museus, restaurantes ou outros locais em Coimbra?",
            "Bem-vindo! O que gostarias de conhecer em Coimbra?",
        ),
    ),
    (
        r"^\s*tudo bem\s*$",
        (
            "Tudo ótimo! E pronto para te ajudar a descobrir Coimbra. O que procuras?",
            "Tudo bem por aqui. Queres uma sugestão de algo para visitar em Coimbra?",
        ),
    ),

    # =======================================================================
    # 20. THANKS
    # =======================================================================
    (
        r".*\b(?:obrigad[oa]|muito obrigad[oa]|obrigad[ií]ssim[oa]|"
        r"valeu|agrade[cç]o)\b.*",
        (
            "De nada! Aproveita Coimbra.",
            "Ora essa! Posso ajudar-te com mais alguma coisa?",
            "É um prazer ajudar.",
            "De nada! Se quiseres, posso sugerir mais locais.",
        ),
    ),

    # =======================================================================
    # 21. RECOMMENDATION_GENERAL
    # =======================================================================
    (
        r".*\b(?:recomenda[- ]?me (?:alguma coisa|algo)|"
        r"o que sugeres|tens alguma sugest[aã]o|surpreende[- ]?me|"
        r"onde devo ir|o que recomendas|qual [ée] a tua sugest[aã]o|"
        r"diz[- ]?me um s[ií]tio|sugere[- ]?me alguma coisa|"
        r"escolhe um local para mim|d[aá][- ]?me uma ideia)\b.*",
        (
            "Uma sugestão é começares pela Universidade de Coimbra e depois desceres pela zona histórica até à Baixa.",
            "Que tal visitar a Universidade e a Sé Velha e terminar com um passeio pela Baixa?",
            "Se quiseres uma escolha simples: visita o Jardim Botânico. Se preferires história, escolhe a Universidade ou a Sé Velha.",
            "Posso escolher algo, mas também podes dizer-me se preferes história, natureza, comida ou vida noturna.",
        ),
    ),

    # =======================================================================
    # 22. Simple one-word / short follow-up rules
    #     These allow some of the proposed conversation flows without state.
    # =======================================================================
    (
        r"^\s*(?:museu|museus)\s*$",
        (
            "Nesse caso, recomendo o Museu Nacional Machado de Castro.",
            "Podes começar pelo Museu Nacional Machado de Castro, perto da Universidade.",
        ),
    ),
    (
        r"^\s*(?:monumento|monumentos)\s*$",
        (
            "Podes começar pela Universidade de Coimbra ou pela Sé Velha.",
            "Uma boa opção é a Sé Velha, no centro histórico.",
        ),
    ),
    (
        r"^\s*(?:jardim|jardins|natureza)\s*$",
        (
            "Nesse caso, recomendo o Jardim Botânico.",
            "O Jardim Botânico é uma boa escolha para um passeio tranquilo.",
        ),
    ),
    (
        r"^\s*(?:portuguesa|tradicional|regional)\s*$",
        (
            "Para comida tradicional portuguesa, procura opções na Baixa e no centro histórico.",
            "Podes considerar o Zé Manel dos Ossos ou o Solar do Bacalhau para cozinha tradicional.",
        ),
    ),
    (
        r"^\s*(?:italiana|italiano)\s*$",
        (
            "Para comida italiana, procura uma pizzaria ou restaurante italiano no centro de Coimbra.",
            "Há várias opções italianas na zona central da cidade.",
        ),
    ),
    (
        r"^\s*(?:vegetariana|vegetariano|vegan|vegana)\s*$",
        (
            "Para uma opção vegetariana, procura restaurantes e cafés na Baixa e perto da Universidade.",
            "Existem opções vegetarianas no centro de Coimbra.",
        ),
    ),

    # =======================================================================
    # 23. OUT-OF-DOMAIN patterns for some common obvious cases
    # =======================================================================
    (
        r".*\b(?:python|programa[cç][aã]o|bitcoin|futebol|mundial|"
        r"pol[ií]tica|medicina|receita m[eé]dica|intelig[eê]ncia artificial)\b.*",
        (
            "Sou especializado em turismo em Coimbra. Posso ajudar-te a descobrir locais, restaurantes ou atividades na cidade.",
            "Esse tema está fora do meu domínio. Experimenta perguntar-me por algo relacionado com Coimbra.",
        ),
    ),

    # =======================================================================
    # 24. FALLBACK — MUST ALWAYS BE LAST
    # =======================================================================
    (
        r"(.*)",
        (
            "Não percebi bem. Podes reformular?",
            "Posso ajudar-te com locais, restaurantes, museus ou atividades em Coimbra.",
            "Não tenho informação sobre isso. Queres uma sugestão sobre Coimbra?",
            "Tenta perguntar-me por monumentos, museus, restaurantes, jardins ou atividades.",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Chatbot
# ---------------------------------------------------------------------------

coimbra_guide_chatbot = Chat(pairs, portuguese_reflections)



DOMAIN_SIGNAL_PATTERN = re.compile(
    r".*\b(?:coimbra|universidade|biblioteca|s[eé] velha|s[eé] nova|"
    r"jardim|jardins|parque|museu|museus|monumento|monumentos|"
    r"hist[oó]ria|restaurante|restaurantes|comer|jantar|almo[cç]ar|"
    r"comida|carne|peixe|marisco|italiana|vegetariana|sushi|caf[eé]|"
    r"bar|bares|vida noturna|alta|baixa|santa clara|mondego|"
    r"visitar|turismo|atividade|atividades|passear|passeio|"
    r"recomenda|sugere|onde fica|fala[- ]?me|ajuda|"
    r"ol[aá]|ola|bom dia|boa tarde|boa noite|obrigad[oa]|"
    r"quem [ée]s|o que [ée]s|adeus|tchau|xau)\b.*",
    re.IGNORECASE,
)


def has_domain_signal(user_input: str) -> bool:
    return bool(DOMAIN_SIGNAL_PATTERN.match(normalize_text(user_input)))


def get_response(user_input: str) -> str:
    """Return one rule-based response for a user message."""
    raw = user_input.strip()
    normalised = normalize_text(user_input)

    if not raw:
        return "Ainda não escreveste nada; o que gostarias de saber sobre Coimbra?"

    if not normalised:
        return "Não consegui interpretar essa mensagem; podes escrevê-la por palavras?"

    # 1) Strong/global intents interrupt any pending slot.
    if is_global_interrupt(normalised):
        reset_context()
        state.last_topic = None

    # 1.5) Explicitly changing/cancelling the current subject is always valid.
    if CANCEL_CONTEXT_PATTERN.match(normalised):
        reset_context()
        state.last_topic = None
        return "Sem problema, mudamos de assunto; o que gostarias de descobrir agora em Coimbra?"

    # 2) Explicit restaurant-by-area request can reuse remembered preference.
    if re.search(r"\b(?:restaurante|restaurantes|comer|jantar|almo[cç]ar)\b", normalised, re.IGNORECASE):
        area = extract_area(normalised)
        if area:
            state.area = area
            state.last_topic = "restaurant"
            response = area_restaurant_response(area, state.food_preference)
            if state.food_preference is None:
                set_context("restaurant_preference")
            return ensure_question(response)

    # 3) Try to resolve the message as a contextual follow-up.
    contextual_response = handle_pending_context(normalised)
    if contextual_response is not None:
        return ensure_question(contextual_response)

    # 4) If there is no recognisable tourism/conversation signal at all,
    # avoid dragging an old topic into the fallback response.
    if not has_domain_signal(normalised):
        state.last_topic = None
        reset_context()
        return "Não consegui relacionar essa mensagem com turismo em Coimbra; queres perguntar por locais, restaurantes, museus, jardins ou atividades?"

    # 5) Ordinary ordered ELIZA-style rules.
    response = coimbra_guide_chatbot.respond(normalised)

    if response is None:
        response = "Não percebi bem; podes reformular a pergunta sobre Coimbra?"

    # 6) Update minimal memory/context from the turn.
    update_context_from_turn(normalised, response)

    return ensure_question(response)


def coimbra_guide_chat() -> None:
    """Interactive terminal conversation."""
    print("Coimbra Guide")
    print("-------------")
    print("Guia turístico virtual de Coimbra baseado em regras.")
    print('Escreve "sair" ou "quit" para terminar.')
    print("=" * 72)
    print(
        "Olá! Sou o Coimbra Guide. Posso ajudar-te a descobrir monumentos, "
        "museus, jardins, restaurantes, cafés e outras atividades em Coimbra; "
        "o que gostarias de conhecer?"
    )

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté à próxima! Queres voltar a explorar Coimbra comigo noutra ocasião?")
            break

        if not user_input:
            continue

        normalised_input = normalize_text(user_input)

        if normalised_input.lower() in {"sair", "quit"}:
            print("Até à próxima! Queres voltar a explorar Coimbra comigo noutra ocasião?")
            break

        response = get_response(user_input)
        print(response)

        # Natural farewells are handled conversationally. Only "sair" and
        # "quit" force an immediate exit, preserving the rule that normal bot
        # turns always end with a guiding question.


def demo() -> None:
    coimbra_guide_chat()


if __name__ == "__main__":
    coimbra_guide_chat()
