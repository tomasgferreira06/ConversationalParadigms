"""D1 + D2 integrated agent: a text classifier routes each message.

    user input -> text classifier -> ELIZA_RUDE (D1, chit-chat)
                                  -> RAG        (D2, Coimbra expert questions)

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

from agents import ElizaRudeAgent, RAGAgent, expert_agent, rag_pipeline
from router import AgentRouter, RouterError


EXIT_COMMAND = "sair"


def is_exit(text: str) -> bool:
    """Only the isolated word ends the program ("Onde posso sair à noite?" does not)."""

    return text.strip().lower() == EXIT_COMMAND


class IntegratedAgent:
    """The classifier's "rag" label means "send to the Coimbra Expert Agent" (D3), which
    plans RAG / WEATHER / BOTH itself; the D2 RAGAgent is its RAG capability."""

    def __init__(self, router, eliza, rag, on_close: Callable[[], None] | None = None):
        self.router = router
        self.agents = {"eliza_rude": eliza, "rag": rag}
        self._on_close = on_close

    @classmethod
    def load(cls, debug_agent: bool = False, write: Callable[[str], None] = print) -> "IntegratedAgent":
        router, eliza, rag = AgentRouter.load(), ElizaRudeAgent(), RAGAgent.load()
        expert = expert_agent.load_expert(rag, debug=write if debug_agent else None)  # starts the Weather MCP once
        return cls(router, eliza, expert, on_close=expert.close)

    def close(self) -> None:
        if self._on_close:
            self._on_close()

    def respond(self, text: str, on_route: Callable[[str], None] | None = None) -> tuple[str, str]:
        """(selected label, reply): the classifier picks the agent, the agent answers.

        `on_route(label)` is called after the classifier and before the agent runs (debug output order).
        """

        route = self.router.classify(text)
        if on_route:
            on_route(route)
        return route, self.agents[route].respond(text)


def format_routing(probabilities: dict[str, float], route: str) -> str:
    lines = ["[router]"] + [f"{label}={p:.2f}" for label, p in probabilities.items()] + [f"selected={route}"]
    return "\n".join(lines)


def run(agent: IntegratedAgent, debug_routing: bool = False,
        read: Callable[[str], str] = input, write: Callable[[str], None] = print) -> None:
    write('Agente integrado D1 + D2 (ELIZA_RUDE + Coimbra Expert). Escreve "sair" para terminar.')
    while True:
        try:
            text = read("\nTu: ")
        except EOFError:
            break
        if is_exit(text):
            break
        if not text.strip():
            continue
        text = text.strip()

        def show_routing(route: str) -> None:  # before the agent runs, so [router] precedes [expert-plan]
            if debug_routing:
                write(format_routing(agent.router.predict_proba(text), route))

        try:
            _route, reply = agent.respond(text, on_route=show_routing)
        except expert_agent.ExpertAgentError as exc:
            write(f"Agente: [erro] {exc}")
            continue
        write(f"Agente: {reply}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure") and not sys.stdin.isatty():
        sys.stdin.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="D1 + D2 integrated agent with text-classification routing.")
    parser.add_argument("--debug-routing", action="store_true",
                        help="show the class probabilities and the selected agent for each message")
    parser.add_argument("--debug-agent", action="store_true",
                        help="show the Coimbra Expert plan (RAG and/or Weather/Places MCP calls) and the capabilities used")
    args = parser.parse_args(argv)

    print("A carregar o router, a ELIZA_RUDE, o RAG (modelo de embeddings e vector store), o Weather MCP e o Places MCP...")
    try:
        agent = IntegratedAgent.load(debug_agent=args.debug_agent)
    except (RouterError, rag_pipeline.BaselineError, expert_agent.MCPClientError) as exc:
        print(f"\nERROR {exc}", file=sys.stderr)
        return 2
    try:
        run(agent, debug_routing=args.debug_routing)
    finally:
        agent.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
