"""Technical tests for the unified RAG baseline (no Ollama, no model download, no network)."""

import contextlib
import dataclasses
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding


D2_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(D2_ROOT / "scripts"))

import rag_baseline as cli  # noqa: E402
import rag_pipeline as rb  # noqa: E402


PDF_CHUNK = {
    "chunk_id": "universidade-alta-sofia-patrimonio-mundial::c0013",
    "document_id": "universidade-alta-sofia-patrimonio-mundial", "source_type": "pdf",
    "title": "Universidade de Coimbra — Alta e Sofia: Património Mundial",
    "source_organization": "Câmara Municipal de Coimbra", "primary_category": "university_heritage",
    "section": "1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS", "subsection": "TORRE",
    "section_path": ["1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS", "TORRE"],
    "unit_role": "content", "source_pages": [10, 11], "source_page": None,
    "source_file": "patrimoniomundial_brochura.pdf", "url": None, "canonical_url": None,
    "conflict_notes": None, "unit_chunk_index": 0, "unit_chunk_count": 1,
    "overlap_chars": 0, "body_chars": 20, "heading_context": "# U\n## 1.\n### TORRE",
    "text": "# U\n## 1.\n### TORRE\n\nEx-libris da Universidade.",
}
WEB_CHUNK = {
    "chunk_id": "web-visitecoimbra-museus::c0007", "document_id": "web-visitecoimbra-museus",
    "source_type": "web_page", "title": "Museus", "source_organization": "Câmara Municipal de Coimbra",
    "primary_category": "museums_collections", "section": "Mosteiro de Santa Clara-a-Velha",
    "subsection": None, "section_path": ["Mosteiro de Santa Clara-a-Velha"], "unit_role": "content",
    "source_pages": None, "source_page": None, "source_file": None,
    "url": "https://visitecoimbra.pt/o-que-visitar/museus/",
    "canonical_url": "https://visitecoimbra.pt/o-que-visitar/museus/",
    "conflict_notes": "Potential conflict with fundacao-da-nacionalidade regarding Santa Clara-a-Velha.",
    "unit_chunk_index": 0, "unit_chunk_count": 1, "overlap_chars": 0, "body_chars": 30,
    "heading_context": "# Museus\n## Mosteiro de Santa Clara-a-Velha",
    "text": "# Museus\n## Mosteiro de Santa Clara-a-Velha\n\nMandado construir em 1314.",
}


def _result(chunk, distance=0.2):
    return rb.to_document(chunk), distance


class SelectionAndMetadataTests(unittest.TestCase):
    def test_only_content_chunks_are_indexed(self):
        chunks = rb.load_chunks()
        kept, excluded = rb.select_indexable(chunks)
        self.assertEqual(len(chunks), 361)
        self.assertEqual(len(kept), 348)
        self.assertEqual(excluded, {"page_labels": 11, "caption_panel": 2})
        self.assertEqual({c["unit_role"] for c in kept}, {"content"})
        self.assertEqual(len({c["chunk_id"] for c in kept}), 348)

    def test_metadata_keeps_provenance_and_drops_nulls(self):
        meta = rb.to_metadata(PDF_CHUNK)
        self.assertEqual(meta["source_pages"], [10, 11])
        self.assertEqual(meta["section_path"], ["1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS", "TORRE"])
        self.assertNotIn("source_page", meta)  # None: absent in Chroma
        self.assertNotIn("url", meta)
        for key in ("text", "heading_context", "body_chars", "overlap_chars"):
            self.assertNotIn(key, meta)
        web = rb.to_metadata(WEB_CHUNK)
        self.assertEqual(web["url"], WEB_CHUNK["url"])
        self.assertNotIn("source_pages", web)

    def test_document_embeds_only_the_chunk_text_under_its_chunk_id(self):
        document = rb.to_document(PDF_CHUNK)
        self.assertEqual(document.page_content, PDF_CHUNK["text"])
        self.assertEqual(document.id, PDF_CHUNK["chunk_id"])


class VectorStoreTests(unittest.TestCase):
    def test_build_with_fake_embeddings_matches_content_chunks(self):
        chunks = rb.load_chunks()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            store, report = rb.build_store(chunks, DeterministicFakeEmbedding(size=16), Path(tmp) / "store")
            self.assertEqual(report["collection_count"], 348)
            self.assertEqual(report["excluded"], {"page_labels": 11, "caption_panel": 2})
            self.assertEqual(store._collection.configuration.get("hnsw", {}).get("space"), "cosine")
            got = store._collection.get(ids=[PDF_CHUNK["chunk_id"], WEB_CHUNK["chunk_id"]], include=["metadatas"])
            by_id = dict(zip(got["ids"], got["metadatas"]))
            self.assertEqual(by_id[PDF_CHUNK["chunk_id"]]["source_pages"], [10, 11])
            self.assertEqual(by_id[WEB_CHUNK["chunk_id"]]["url"], WEB_CHUNK["url"])
            roles = {m["unit_role"] for m in store._collection.get(include=["metadatas"])["metadatas"]}
            self.assertEqual(roles, {"content"})

    def test_missing_store_is_reported_not_rebuilt(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(rb.BaselineError) as caught:
                rb.open_store(DeterministicFakeEmbedding(size=16), Path(tmp) / "absent")
            self.assertIn("Run with --rebuild", str(caught.exception))
            self.assertFalse((Path(tmp) / "absent").exists())


class ContextAndPromptTests(unittest.TestCase):
    def test_context_separates_sources_with_provenance(self):
        context = rb.build_context([_result(PDF_CHUNK), _result(WEB_CHUNK)])
        self.assertIn("[Fonte 1]", context)
        self.assertIn("[Fonte 2]", context)
        self.assertIn("Páginas: p. 10, 11", context)
        self.assertIn("URL: https://visitecoimbra.pt/o-que-visitar/museus/", context)
        self.assertIn("Secção: 1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS > TORRE", context)
        self.assertIn(PDF_CHUNK["text"], context)

    def test_conflict_metadata_is_a_separate_note_only_when_present(self):
        self.assertIsNone(rb.conflict_note([_result(PDF_CHUNK)]))
        note = rb.conflict_note([_result(PDF_CHUNK), _result(WEB_CHUNK), _result(WEB_CHUNK)])
        self.assertIn("Metadados de curadoria", note)
        self.assertIn("não inventes a outra", note)
        self.assertEqual(note.count("Fonte 2:"), 1)
        self.assertNotIn("Fonte 3:", note)  # same note not repeated
        messages = rb.build_messages("Quem fundou?", [_result(WEB_CHUNK)])
        user = messages[1].content
        self.assertLess(user.index("[Fonte 1]"), user.index("[Metadados de curadoria"))
        self.assertNotIn("Metadados de curadoria", rb.build_messages("Q?", [_result(PDF_CHUNK)])[1].content)

    def test_prompt_structure(self):
        messages = rb.build_messages("Quando foi concluída a Biblioteca Joanina?", [_result(PDF_CHUNK)])
        system, user = messages[0].content, messages[1].content
        self.assertIn(rb.INSUFFICIENT, system)
        self.assertIn("versões contraditórias", system)
        self.assertIn("Português de Portugal", system)
        self.assertTrue(user.startswith("CONTEXTO:\n\n[Fonte 1]"))
        self.assertIn("PERGUNTA:\n\nQuando foi concluída a Biblioteca Joanina?", user)
        self.assertTrue(user.endswith("Responde apenas com base no contexto acima."))

    def test_sources_show_pages_for_pdf_and_url_for_web(self):
        sources = rb.format_sources([_result(PDF_CHUNK), _result(WEB_CHUNK), _result(WEB_CHUNK)])
        lines = sources.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("[universidade-alta-sofia-patrimonio-mundial]", lines[0])
        self.assertIn("páginas 10, 11", lines[0])
        self.assertIn("https://visitecoimbra.pt/o-que-visitar/museus/", lines[1])

    def test_display_body_strips_heading_context(self):
        self.assertEqual(cli.chunk_body(rb.to_document(WEB_CHUNK)), "Mandado construir em 1314.")
        self.assertEqual(cli.chunk_body(Document(page_content="Sem heading.")), "Sem heading.")


def _config(**overrides):
    values = dict(distance_space="cosine", top_k=3, llm_model="llama3.2:3b", llm_temperature=0.1,
                  indexed_roles=frozenset({"content"}))
    return rb.RAGConfig(**values, **overrides)


def _embeddings_with_fake_client(config):
    """The real HuggingFaceEmbeddings built by load_embeddings, with a fake SentenceTransformer."""

    from langchain_huggingface import HuggingFaceEmbeddings

    client = mock.Mock()
    client.encode.side_effect = lambda texts, **kwargs: np.zeros((len(texts), 4))

    def construct(**kwargs):
        embeddings = HuggingFaceEmbeddings.model_construct(multi_process=False, show_progress=False, **kwargs)
        embeddings._client = client
        return embeddings

    with mock.patch("langchain_huggingface.HuggingFaceEmbeddings", side_effect=construct) as hf:
        embeddings = rb.load_embeddings(config)
    return embeddings, client, hf


EMBEDDED = {"documents": [], "queries": []}


class RecordingEmbeddings(DeterministicFakeEmbedding):
    """Fake embeddings that record which texts were embedded as documents and as queries."""

    def embed_documents(self, texts):
        EMBEDDED["documents"].extend(texts)
        return super().embed_documents(texts)

    def embed_query(self, text):
        EMBEDDED["queries"].append(text)
        return super().embed_query(text)


class ConfigurationTests(unittest.TestCase):
    def test_v0_configuration_is_preserved(self):
        self.assertEqual(rb.BASELINE_V0, _config(
            embedding_model="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            query_prompt_name=None,
            collection_name="coimbra_rag_baseline",
            store_dir=D2_ROOT / "data" / "chroma_baseline",
        ))

    def test_v1_configuration_is_preserved(self):
        self.assertEqual(rb.BASELINE_V1, _config(
            embedding_model="sentence-transformers/all-mpnet-base-v2",
            query_prompt_name=None,
            collection_name="coimbra_rag_baseline_v1",
            store_dir=D2_ROOT / "data" / "chroma_baseline_v1",
        ))

    def test_v2_configuration_is_preserved_with_qwen3_and_its_query_prompt(self):
        self.assertEqual(rb.BASELINE_V2, _config(
            embedding_model="Qwen/Qwen3-Embedding-0.6B",
            query_prompt_name="query",
            collection_name="coimbra_rag_baseline_v2",
            store_dir=D2_ROOT / "data" / "chroma_baseline_v2",
        ))

    def test_versions_differ_only_in_the_embedding_solution_and_store(self):
        v0, v1, v2 = (vars(c) for c in (rb.BASELINE_V0, rb.BASELINE_V1, rb.BASELINE_V2))
        self.assertEqual({k for k in v0 if v0[k] != v1[k]}, {"embedding_model", "collection_name", "store_dir"})
        self.assertEqual({k for k in v1 if v1[k] != v2[k]},
                         {"embedding_model", "query_prompt_name", "collection_name", "store_dir"})

    def test_stores_and_collections_never_collide(self):
        configs = (rb.BASELINE_V0, rb.BASELINE_V1, rb.BASELINE_V2)
        self.assertEqual(len({c.collection_name for c in configs}), 3)
        dirs = [c.store_dir.resolve() for c in configs]
        self.assertEqual(len(set(dirs)), 3)
        for a in dirs:
            for b in dirs:
                self.assertNotIn(a, b.parents)
        self.assertTrue(all(d.parent == (D2_ROOT / "data").resolve() for d in dirs))

    def test_frozen_configs_change_only_the_store_of_their_historical_version(self):
        expected = {
            rb.FROZEN_V0: (rb.BASELINE_V0, "coimbra_rag_frozen_v0", "chroma_frozen_v0"),
            rb.FROZEN_V1: (rb.BASELINE_V1, "coimbra_rag_frozen_v1", "chroma_frozen_v1"),
            rb.FROZEN_V2: (rb.BASELINE_V2, "coimbra_rag_frozen_v2", "chroma_frozen_v2"),
        }
        for frozen, (historical, collection, directory) in expected.items():
            with self.subTest(config=collection):
                self.assertEqual(frozen, dataclasses.replace(
                    historical, collection_name=collection, store_dir=D2_ROOT / "data" / directory))
        self.assertIsNone(rb.FROZEN_V0.query_prompt_name)
        self.assertIsNone(rb.FROZEN_V1.query_prompt_name)
        self.assertEqual(rb.FROZEN_V2.query_prompt_name, "query")
        self.assertEqual(rb.FROZEN_V2.embedding_model, "Qwen/Qwen3-Embedding-0.6B")

    def test_cli_offers_only_the_frozen_configs_and_defaults_to_frozen_v2(self):
        self.assertEqual(rb.CONFIGS, {"frozen-v0": rb.FROZEN_V0, "frozen-v1": rb.FROZEN_V1,
                                      "frozen-v2": rb.FROZEN_V2})
        self.assertIs(rb.BASELINE, rb.FROZEN_V2)
        historical = {rb.BASELINE_V0.store_dir, rb.BASELINE_V1.store_dir, rb.BASELINE_V2.store_dir}
        self.assertFalse(historical & {c.store_dir for c in rb.CONFIGS.values()})

    def test_cli_rebuild_uses_only_the_selected_config(self):
        with mock.patch.object(cli, "load_embeddings") as load, \
                mock.patch.object(cli, "load_chunks", return_value=[]), \
                mock.patch.object(cli, "build_store", return_value=(None, {
                    "input_chunks": 0, "indexed_chunks": 0, "excluded": {}, "collection_count": 0})) as build,                 contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["--config", "frozen-v0", "--rebuild"]), 0)
        load.assert_called_once_with(rb.FROZEN_V0)
        build.assert_called_once_with([], load.return_value, config=rb.FROZEN_V0)

    def test_frozen_and_historical_stores_and_collections_never_collide(self):
        configs = (rb.BASELINE_V0, rb.BASELINE_V1, rb.BASELINE_V2, rb.FROZEN_V0, rb.FROZEN_V1, rb.FROZEN_V2)
        self.assertEqual(len({c.collection_name for c in configs}), 6)
        dirs = [c.store_dir.resolve() for c in configs] + [(D2_ROOT / "data" / "chroma_smoke").resolve()]
        self.assertEqual(len(set(dirs)), 7)
        for a in dirs:
            for b in dirs:
                self.assertNotIn(a, b.parents)

    def test_frozen_embedding_setups_match_their_historical_versions(self):
        for config in (rb.FROZEN_V0, rb.FROZEN_V1):
            with self.subTest(config=config.collection_name):
                with mock.patch("langchain_huggingface.HuggingFaceEmbeddings") as hf:
                    rb.load_embeddings(config)
                hf.assert_called_once_with(model_name=config.embedding_model,
                                           encode_kwargs={"normalize_embeddings": True})
        _embeddings, _client, hf = _embeddings_with_fake_client(rb.FROZEN_V2)
        hf.assert_called_once_with(
            model_name="Qwen/Qwen3-Embedding-0.6B",
            encode_kwargs={"normalize_embeddings": True},
            query_encode_kwargs={"normalize_embeddings": True, "prompt_name": "query"},
        )

    def test_every_version_selects_the_348_content_chunks(self):
        chunks = rb.load_chunks()
        for config in (rb.BASELINE_V0, rb.BASELINE_V1, rb.BASELINE_V2, rb.FROZEN_V0, rb.FROZEN_V1, rb.FROZEN_V2):
            with self.subTest(config=config.collection_name):
                kept, excluded = rb.select_indexable(chunks, config)
                self.assertEqual(len(kept), 348)
                self.assertEqual(excluded, {"page_labels": 11, "caption_panel": 2})

    def test_v0_v1_embed_queries_like_documents(self):
        for config in (rb.BASELINE_V0, rb.BASELINE_V1):
            with self.subTest(config=config.collection_name):
                with mock.patch("langchain_huggingface.HuggingFaceEmbeddings") as hf:
                    rb.load_embeddings(config)
                hf.assert_called_once_with(model_name=config.embedding_model,
                                           encode_kwargs={"normalize_embeddings": True})

    def test_v2_prompts_queries_only_and_normalizes_both(self):
        embeddings, client, hf = _embeddings_with_fake_client(rb.BASELINE_V2)
        hf.assert_called_once_with(
            model_name="Qwen/Qwen3-Embedding-0.6B",
            encode_kwargs={"normalize_embeddings": True},
            query_encode_kwargs={"normalize_embeddings": True, "prompt_name": "query"},
        )
        embeddings.embed_documents([PDF_CHUNK["text"]])
        self.assertEqual(client.encode.call_args.kwargs, {"show_progress_bar": False, "normalize_embeddings": True})
        embeddings.embed_query("Em que ano foi fundado o Mosteiro de Santa Cruz?")
        self.assertEqual(client.encode.call_args.args[0], ["Em que ano foi fundado o Mosteiro de Santa Cruz?"])
        self.assertEqual(client.encode.call_args.kwargs,
                         {"show_progress_bar": False, "normalize_embeddings": True, "prompt_name": "query"})

    def test_store_embeds_chunk_text_as_documents_and_the_question_as_query(self):
        EMBEDDED["documents"].clear()
        EMBEDDED["queries"].clear()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            store, _report = rb.build_store([PDF_CHUNK, WEB_CHUNK], RecordingEmbeddings(size=8), Path(tmp) / "s")
            rb.retrieve(store, "Quem fundou?")
        self.assertEqual(EMBEDDED["documents"], [PDF_CHUNK["text"], WEB_CHUNK["text"]])
        self.assertEqual(EMBEDDED["queries"], ["Quem fundou?"])

    def test_store_defaults_to_the_config_store_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = dataclasses.replace(rb.BASELINE, store_dir=Path(tmp) / "absent")
            with self.assertRaisesRegex(rb.BaselineError, "Run with --rebuild"):
                rb.open_store(DeterministicFakeEmbedding(size=16), config=config)
            self.assertFalse(config.store_dir.exists())

    def test_prompt_is_unchanged(self):
        self.assertEqual(rb.SYSTEM_PROMPT, (
            "És um assistente especializado em turismo, história, património, cultura e gastronomia de Coimbra.\n"
            "Responde à pergunta utilizando apenas o contexto fornecido.\n"
            "Não uses conhecimento externo para preencher informação que não esteja no contexto.\n"
            "Se o contexto não for suficiente para responder com segurança, diz explicitamente:\n"
            "\"Não tenho informação suficiente no contexto disponível para responder com segurança.\"\n"
            "Se existirem fontes recuperadas que apresentam versões contraditórias do mesmo facto, não escolhas "
            "silenciosamente uma delas. Explica brevemente que existem formulações divergentes e identifica as fontes.\n"
            "Responde em Português de Portugal, de forma clara e concisa.\n"
            "Não inventes fontes."
        ))

    def test_generation_uses_the_configured_model_and_temperature(self):
        messages = rb.build_messages("Q?", [_result(PDF_CHUNK)])
        with mock.patch("langchain_ollama.ChatOllama") as chat:
            chat.return_value.invoke.return_value.content = "Resposta."
            self.assertEqual(rb.generate(messages), "Resposta.")
        chat.assert_called_once_with(model="llama3.2:3b", temperature=0.1)
        chat.return_value.invoke.assert_called_once_with(messages)


if __name__ == "__main__":
    unittest.main()
