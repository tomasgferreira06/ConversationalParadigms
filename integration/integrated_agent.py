"""D1 + D2 integrated agent: a text classifier routes each message.

    user input -> text classifier -> ELIZA_RUDE (D1, chit-chat)
                                  -> RAG        (D2, Coimbra tourism questions)

Startup loads, once: the router (vectorizer + classifier), ELIZA_RUDE, the RAG
embedding model and its Chroma store (frozen configuration, BASELINE). Then,
per message: read it; "sair" on its own ends the program before the classifier
(so it never reaches ELIZA_RUDE's own "sair" rule); otherwise classify it and
send it to the selected agent. Each message is routed independently.

Usage:
    uv run python integration/integrated_agent.py
    uv run python integration/integrated_agent.py --debug-routing
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from agents import ElizaRudeAgent, RAGAgent, rag_pipeline
from router import AgentRouter, RouterError


EXIT_COMMAND = "sair"


def is_exit(text: str) -> bool:
    """Only the isolated word ends the program ("Onde posso sair à noite?" does not)."""

    return text.strip().lower() == EXIT_COMMAND


class IntegratedAgent:
    def __init__(self, router, eliza, rag):
        self.router = router
        self.agents = {"eliza_rude": eliza, "rag": rag}

    @classmethod
    def load(cls) -> "IntegratedAgent":
        return cls(AgentRouter.load(), ElizaRudeAgent(), RAGAgent.load())

    def respond(self, text: str) -> tuple[str, str]:
        """(selected label, reply): the classifier picks the agent, the agent answers."""

        route = self.router.classify(text)
        return route, self.agents[route].respond(text)


def format_routing(probabilities: dict[str, float], route: str) -> str:
    lines = ["[router]"] + [f"{label}={p:.2f}" for label, p in probabilities.items()] + [f"selected={route}"]
    return "\n".join(lines)


def run(agent: IntegratedAgent, debug_routing: bool = False,
        read: Callable[[str], str] = input, write: Callable[[str], None] = print) -> None:
    write('Agente integrado D1 + D2 (ELIZA_RUDE + Coimbra Tourism Expert). Escreve "sair" para terminar.')
    while True:
        try:
            text = read("\nTu: ")
        except EOFError:
            break
        if is_exit(text):
            break
        if not text.strip():
            continue
        route, reply = agent.respond(text.strip())
        if debug_routing:
            write(format_routing(agent.router.predict_proba(text.strip()), route))
        write(f"Agente: {reply}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    # Piped stdin on Windows is decoded with the console code page (cp1252),
    # which garbles accented input; a real console already yields Unicode.
    if hasattr(sys.stdin, "reconfigure") and not sys.stdin.isatty():
        sys.stdin.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="D1 + D2 integrated agent with text-classification routing.")
    parser.add_argument("--debug-routing", action="store_true",
                        help="show the class probabilities and the selected agent for each message")
    args = parser.parse_args(argv)

    print("A carregar o router, a ELIZA_RUDE e o RAG (modelo de embeddings e vector store)...")
    try:
        agent = IntegratedAgent.load()
    except (RouterError, rag_pipeline.BaselineError) as exc:
        print(f"\nERROR {exc}", file=sys.stderr)
        return 2
    run(agent, debug_routing=args.debug_routing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
