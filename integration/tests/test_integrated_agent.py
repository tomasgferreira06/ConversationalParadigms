"""D1 + D2 integration with mocks (no Ollama, no embedding model, no Chroma)."""

import sys
import unittest
from pathlib import Path
from unittest import mock

from langchain_core.documents import Document

INTEGRATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INTEGRATION_DIR))

import agents  # noqa: E402
import integrated_agent as ia  # noqa: E402


def fake_router(route):
    router = mock.Mock()
    router.classify.return_value = route
    router.predict_proba.return_value = {"eliza_rude": 0.08, "rag": 0.92} if route == "rag" else {"eliza_rude": 0.9, "rag": 0.1}
    return router


def build(route):
    eliza, rag = mock.Mock(), mock.Mock()
    eliza.respond.return_value = "Ah, és tu. Outra vez."
    rag.respond.return_value = "Resposta RAG."
    return ia.IntegratedAgent(fake_router(route), eliza, rag), eliza, rag


def chat(agent, inputs, debug_routing=False):
    """Run the loop over scripted inputs; return everything it wrote."""

    lines = iter(inputs)

    def read(_prompt):
        try:
            return next(lines)
        except StopIteration:
            raise EOFError from None

    written = []
    ia.run(agent, debug_routing=debug_routing, read=read, write=written.append)
    return "\n".join(written)


class RoutingDispatchTests(unittest.TestCase):
    def test_eliza_rude_route_calls_only_eliza_rude(self):
        agent, eliza, rag = build("eliza_rude")
        self.assertEqual(agent.respond("Olá"), ("eliza_rude", "Ah, és tu. Outra vez."))
        eliza.respond.assert_called_once_with("Olá")
        rag.respond.assert_not_called()

    def test_rag_route_calls_only_rag(self):
        agent, eliza, rag = build("rag")
        self.assertEqual(agent.respond("Que museus há em Coimbra?"), ("rag", "Resposta RAG."))
        rag.respond.assert_called_once_with("Que museus há em Coimbra?")
        eliza.respond.assert_not_called()

    def test_loop_prints_the_selected_agent_reply(self):
        agent, eliza, _rag = build("rag")
        output = chat(agent, ["Que museus há em Coimbra?"])
        self.assertIn("Agente: Resposta RAG.", output)
        agent.router.classify.assert_called_once_with("Que museus há em Coimbra?")
        eliza.respond.assert_not_called()


class ExitCommandTests(unittest.TestCase):
    def test_sair_calls_neither_agent_nor_the_classifier(self):
        for command in ("sair", "  SAIR ", "Sair"):
            with self.subTest(command=command):
                agent, eliza, rag = build("eliza_rude")
                chat(agent, [command, "Olá"])  # nothing after "sair" is read
                agent.router.classify.assert_not_called()
                eliza.respond.assert_not_called()
                rag.respond.assert_not_called()

    def test_sair_inside_a_sentence_does_not_exit(self):
        self.assertFalse(ia.is_exit("Onde posso sair à noite em Coimbra?"))
        self.assertFalse(ia.is_exit("Quero sair daqui."))
        agent, _eliza, rag = build("rag")
        chat(agent, ["Onde posso sair à noite em Coimbra?", "sair"])
        rag.respond.assert_called_once_with("Onde posso sair à noite em Coimbra?")

    def test_empty_input_is_skipped_and_eof_ends(self):
        agent, eliza, _rag = build("eliza_rude")
        chat(agent, ["", "   "])
        agent.router.classify.assert_not_called()
        eliza.respond.assert_not_called()


class DebugRoutingTests(unittest.TestCase):
    def test_normal_mode_hides_the_router(self):
        agent, _eliza, _rag = build("rag")
        output = chat(agent, ["Que museus há em Coimbra?"])
        self.assertNotIn("[router]", output)

    def test_debug_mode_shows_probabilities_and_route(self):
        agent, _eliza, _rag = build("rag")
        output = chat(agent, ["Que museus há em Coimbra?"], debug_routing=True)
        self.assertIn("[router]\neliza_rude=0.08\nrag=0.92\nselected=rag", output)


class ElizaRudeAgentTests(unittest.TestCase):
    def test_uses_respond_not_converse_with_converse_input_preparation(self):
        chat_ = mock.Mock()
        chat_.converse.side_effect = AssertionError("the integrated loop must own the conversation")
        chat_.respond.return_value = "Estás cansado. E eu estou farta. Estamos quites."
        reply = agents.ElizaRudeAgent(chat_).respond("Estou cansado!.")
        chat_.respond.assert_called_once_with("Estou cansado")
        self.assertEqual(reply, "Estás cansado. E eu estou farta. Estamos quites.")

    def test_real_eliza_rude_rules_are_used_unchanged(self):
        eliza = agents.ElizaRudeAgent()
        self.assertIs(eliza.chat, agents.d1.eliza_rude)
        greetings = {"Ah, és tu. Outra vez.", "Olá. Despacha-te, que tenho mais que fazer.",
                     "Hmm. O que é que queres agora?"}
        self.assertIn(eliza.respond("Olá!"), greetings)
        self.assertIn(eliza.respond("Estou cansado."), {
            "Estás cansado. E eu estou farta. Estamos quites.",
            "E queres uma medalha por estares cansado?",
            "Toda a gente está cansado de vez em quando. Supera.",
        })


class RAGAgentTests(unittest.TestCase):
    def test_default_configuration_is_the_active_frozen_baseline(self):
        self.assertIs(agents.rag_pipeline.BASELINE, agents.rag_pipeline.FROZEN_V2)
        rag = agents.RAGAgent(store=mock.Mock())
        self.assertIs(rag.config, agents.rag_pipeline.BASELINE)

    def test_respond_reuses_retrieve_build_messages_generate(self):
        rp = agents.rag_pipeline
        store, config = mock.Mock(), rp.BASELINE
        doc = Document(page_content="Ex-libris da Universidade.", metadata={
            "title": "Universidade", "document_id": "doc", "source_type": "pdf",
            "source_pages": [10], "section_path": ["TORRE"]})
        results = [(doc, 0.2)]
        with mock.patch.object(rp, "retrieve", return_value=results) as retrieve, \
                mock.patch.object(rp, "build_messages", wraps=rp.build_messages) as build_messages, \
                mock.patch.object(rp, "generate", return_value="A torre é a Cabra.") as generate:
            reply = agents.RAGAgent(store, config).respond("O que é a Cabra?")
        retrieve.assert_called_once_with(store, "O que é a Cabra?", k=config.top_k)
        build_messages.assert_called_once_with("O que é a Cabra?", results)
        generate.assert_called_once_with(rp.build_messages("O que é a Cabra?", results), config)
        self.assertTrue(reply.startswith("A torre é a Cabra.\n\nFontes:\n- Universidade [doc]"))

    def test_load_opens_the_existing_store_once_without_rebuilding(self):
        rp = agents.rag_pipeline
        with mock.patch.object(rp, "check_ollama") as check, \
                mock.patch.object(rp, "load_embeddings", return_value="emb") as load_embeddings, \
                mock.patch.object(rp, "open_store", return_value="store") as open_store, \
                mock.patch.object(rp, "build_store") as build_store:
            rag = agents.RAGAgent.load()
        check.assert_called_once_with(rp.BASELINE.llm_model)
        load_embeddings.assert_called_once_with(rp.BASELINE)
        open_store.assert_called_once_with("emb", config=rp.BASELINE)
        build_store.assert_not_called()
        self.assertEqual((rag.store, rag.config), ("store", rp.BASELINE))


class StartupTests(unittest.TestCase):
    def test_startup_loads_each_component_once(self):
        with mock.patch.object(ia.AgentRouter, "load") as router_load, \
                mock.patch.object(ia, "ElizaRudeAgent") as eliza_cls, \
                mock.patch.object(ia.RAGAgent, "load") as rag_load:
            agent = ia.IntegratedAgent.load()
        router_load.assert_called_once_with()
        eliza_cls.assert_called_once_with()
        rag_load.assert_called_once_with()
        self.assertIs(agent.router, router_load.return_value)

    def test_startup_error_exits_with_code_2(self):
        with mock.patch.object(ia.IntegratedAgent, "load", side_effect=ia.RouterError("[router] missing")), \
                mock.patch("sys.stderr"), mock.patch("builtins.print"):
            self.assertEqual(ia.main([]), 2)


if __name__ == "__main__":
    unittest.main()
