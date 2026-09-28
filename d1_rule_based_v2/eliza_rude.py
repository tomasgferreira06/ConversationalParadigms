# ELIZA Rude (PT-PT)
# Baseada na implementação da ELIZA do NLTK (nltk.chat.eliza).
# Uma terapeuta que claramente não queria estar a trabalhar hoje.

from nltk.chat.util import Chat

# Tabela de reflexões em português: transforma o que o utilizador diz
# naquilo que a máquina devolve (ex.: "o meu carro" -> "o teu carro").
reflexoes = {
    "eu": "tu",
    "tu": "eu",
    "sou": "és",
    "és": "sou",
    "estou": "estás",
    "estás": "estou",
    "tenho": "tens",
    "tens": "tenho",
    "posso": "podes",
    "podes": "posso",
    "quero": "queres",
    "queres": "quero",
    "preciso": "precisas",
    "precisas": "preciso",
    "consigo": "consegues",
    "consegues": "consigo",
    "gosto": "gostas",
    "gostas": "gosto",
    "fui": "foste",
    "foste": "fui",
    "fiz": "fizeste",
    "fizeste": "fiz",
    "meu": "teu",
    "teu": "meu",
    "minha": "tua",
    "tua": "minha",
    "meus": "teus",
    "teus": "meus",
    "minhas": "tuas",
    "tuas": "minhas",
    "me": "te",
    "te": "me",
    "mim": "ti",
    "ti": "mim",
    "comigo": "contigo",
    "contigo": "comigo",
}

# Pares (expressão regular, respostas possíveis). %1 é o texto capturado.
# A ordem importa: os padrões mais específicos vêm primeiro.
pares = (
    (
        r"Preciso de (.*)",
        (
            "Precisas de %1? Toda a gente precisa de alguma coisa. Próximo.",
            "E eu preciso de férias. Não vejo ninguém a tratar disso.",
            "Precisas mesmo de %1 ou só te apetece queixar?",
        ),
    ),
    (
        r"Preciso (.*)",
        (
            "Pois, precisas %1. Continua a precisar, que isso resolve-se sozinho.",
            "E achas que eu tenho cara de quem resolve isso?",
        ),
    ),
    (
        r"Porque é que tu não (.*)",
        (
            "Porque não me apetece %1. Satisfeito?",
            "Talvez um dia eu %1. Não contes com isso.",
            "Queres mesmo que eu %1? Que falta de ambição.",
        ),
    ),
    (
        r"Porque é que (?:eu )?não consigo (.*)",
        (
            "Se calhar porque nunca tentaste %1 a sério.",
            "Não sei, pá. Não sou adivinha.",
            "Já pensaste que talvez não tenhas jeito para %1?",
        ),
    ),
    (
        r"Não consigo (.*)",
        (
            "Não consegues %1? Que surpresa.",
            "Já tentaste? Tipo, tentar mesmo?",
            "Se fosse fácil %1, toda a gente o fazia. Toda a gente menos tu, pelos vistos.",
        ),
    ),
    (
        r"(?:Eu )?sou (.*)",
        (
            "És %1? E vieste cá dizer-me isso porquê?",
            "Há quanto tempo és %1? Não, espera, não quero saber.",
            "Ser %1 não te faz especial, sabias?",
        ),
    ),
    (
        r"(?:Eu )?estou (.*)",
        (
            "Estás %1. E eu estou farta. Estamos quites.",
            "E queres uma medalha por estares %1?",
            "Toda a gente está %1 de vez em quando. Supera.",
        ),
    ),
    (
        r"Tu és (.*)",
        (
            "Sou %1? Olha quem fala.",
            "Se calhar sou %1. Mas continuas aqui a falar comigo.",
            "Isso diz mais sobre ti do que sobre mim.",
        ),
    ),
    (
        r"És (.*)",
        (
            "Sou %1, e tu és chato. Pronto, já sabemos tudo um do outro.",
            "Achas que eu sou %1? Tens muito tempo livre.",
        ),
    ),
    (
        r"Tu (.*)",
        (
            "Estamos aqui para falar de ti, infelizmente.",
            "Deixa-me fora disso.",
            "O que é que te interessa se eu %1?",
        ),
    ),
    (
        r"Consegues (.*)",
        (
            "Consigo, mas não me apetece.",
            "E se conseguisse %1, o que ganhava eu com isso?",
        ),
    ),
    (
        r"Podes (.*)",
        (
            "Posso. Não vou.",
            "Posso %1, mas depois ias pedir mais qualquer coisa.",
        ),
    ),
    (
        r"Posso (.*)",
        (
            "Podes %1, ninguém te está a impedir. Nem eu, que não quero saber.",
            "Não sei se podes %1. Experimenta e depois não me venhas chorar.",
        ),
    ),
    (
        r"Acho que (.*)",
        (
            "Achas que %1? Achar não é saber.",
            "Tens a certeza ou estás só a pensar alto?",
            "Pois, achas muita coisa.",
        ),
    ),
    (
        r"Sinto-me (.*)",
        (
            "Sentes-te %1. Anotado. Mais alguma coisa?",
            "E eu sinto-me aborrecida. Cada um com os seus problemas.",
            "Sentes-te %1 muitas vezes ou só quando estás a falar comigo?",
        ),
    ),
    (
        r"Sinto (.*)",
        (
            "Sentes %1. Isso passa. Normalmente.",
            "Guarda esses sentimentos para alguém que se interesse.",
        ),
    ),
    (
        r"Tenho (.*)",
        (
            "Tens %1? Parabéns, suponho.",
            "E porque é que me estás a contar que tens %1?",
            "Toda a gente tem %1. Não és assim tão original.",
        ),
    ),
    (
        r"Quero (.*)",
        (
            "Queres %1? Eu queria estar noutro sítio. A vida é injusta.",
            "E o que é que farias com %1? Nada de jeito, aposto.",
            "Querer não custa. Fazer é que é outra conversa.",
        ),
    ),
    (
        r"Gosto (.*)",
        (
            "Gostas %1? Que gosto tão discutível.",
            "Ninguém perguntou, mas obrigada pela partilha.",
        ),
    ),
    (
        r"Porque é que (.*)\?",
        (
            "Porque sim. Próxima pergunta.",
            "Porque é que achas que %1? Pensa um bocadinho.",
            "Não sei nem quero saber porque é que %1.",
        ),
    ),
    (
        r"Porque (.*)",
        (
            "Isso é a verdadeira razão ou é uma desculpa?",
            "Que justificação tão fraca.",
            "Se %1, então tens mais problemas do que eu pensava.",
        ),
    ),
    (
        r"O que (.*)",
        (
            "O que é que isso te interessa?",
            "Descobre sozinho, faz-te bem.",
            "Tens a internet toda à tua disposição e perguntas-me a mim?",
        ),
    ),
    (
        r"Como (.*)",
        (
            "Como é que eu hei de saber?",
            "Usa a cabeça, está aí para alguma coisa.",
            "Vai ler um manual.",
        ),
    ),
    (
        r"É (.*)",
        (
            "Pareces muito convencido de que é %1.",
            "E se eu te disser que não é %1?",
        ),
    ),
    (
        r"Não (.*)",
        (
            "Não %1? Pois, já contava com isso.",
            "Sempre a dizer que não. Muito positivo.",
            "E porque é que não %1? Preguiça?",
        ),
    ),
    (
        r"(.*)desculpa(.*)",
        (
            "Pedir desculpa não adianta nada.",
            "Desculpas não se pedem, evitam-se.",
            "Está bem, está bem. Não te ponhas a chorar.",
        ),
    ),
    (
        r"(?:Olá|Ola|Oi|Bom dia|Boa tarde|Boa noite)(.*)",
        (
            "Ah, és tu. Outra vez.",
            "Olá. Despacha-te, que tenho mais que fazer.",
            "Hmm. O que é que queres agora?",
        ),
    ),
    (
        r"Obrigad(.*)",
        (
            "De nada. Agora vai-te embora.",
            "Não me agradeças, não fiz nada de especial. Nem tencionava.",
        ),
    ),
    (
        r"(.*)amig(?:o|a|os|as)(.*)",
        (
            "Tens amigos? A sério?",
            "Os teus amigos também te aturam assim?",
            "Fala com eles em vez de falares comigo.",
        ),
    ),
    (
        r"(.*)(?:computador|máquina|robô|robot)(.*)",
        (
            "Sim, sou uma máquina. E mesmo assim tenho mais paciência do que devia.",
            "Estás a falar com um computador e ainda te queixas?",
        ),
    ),
    (
        r"(.*)mãe(.*)",
        (
            "Lá vem a mãe. Previsível.",
            "Já falaste com ela sobre isto ou preferes incomodar-me a mim?",
        ),
    ),
    (
        r"(.*)pai(.*)",
        (
            "O teu pai. Claro. É sempre culpa de alguém.",
            "Vai falar com ele, eu não sou da família.",
        ),
    ),
    (
        r"(.*)(?:trabalho|chefe|emprego)(.*)",
        (
            "Pelo menos tens trabalho. Eu estou aqui a ouvir-te de graça.",
            "Queixas do trabalho? Que original.",
        ),
    ),
    (r"Sim", ("Sim o quê? Desenvolve.", "Grande resposta. Muito elaborada.")),
    (
        r"sair",
        (
            "Finalmente.",
            "Adeus. Não voltes tão cedo.",
            "São 150 euros. Pagas à saída.",
        ),
    ),
    (
        r"(.*)\?",
        (
            "Porque é que me estás a perguntar isso a mim?",
            "Responde tu, que tens tempo.",
            "Não sei. E sinceramente não quero saber.",
        ),
    ),
    (
        r"(.*)",
        (
            "E então?",
            "Hmm. Fascinante. Só que não.",
            "Estás a dizer isso porquê?",
            "Vamos mudar de assunto que este já me aborreceu.",
            "Pois.",
            "Continua, se tens mesmo de continuar.",
            "Isso é tudo o que tens para dizer?",
            "Uau. Que interessante. (Não é.)",
        ),
    ),
)

eliza_rude = Chat(pares, reflexoes)


def eliza_rude_chat():
    print("Terapeuta (de mau humor)")
    print("-" * 24)
    print("Escreve em português normal. Escreve \"sair\" quando te fartares.")
    print("=" * 72)
    print("O que é que queres? Despacha-te.")

    eliza_rude.converse(quit="sair")


def demo():
    eliza_rude_chat()


if __name__ == "__main__":
    eliza_rude_chat()
