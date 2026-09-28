"""Technical tests for the unified RAG baseline (no Ollama, no model download, no network)."""

import sys
import tempfile
import unittest
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding


D2_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(D2_ROOT / "scripts"))

import rag_baseline as rb  # noqa: E402


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
        self.assertEqual(len(chunks), 330)
        self.assertEqual(len(kept), 317)
        self.assertEqual(excluded, {"page_labels": 11, "caption_panel": 2})
        self.assertEqual({c["unit_role"] for c in kept}, {"content"})
        self.assertEqual(len({c["chunk_id"] for c in kept}), 317)

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
            self.assertEqual(report["collection_count"], 317)
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
        self.assertEqual(rb.chunk_body(rb.to_document(WEB_CHUNK)), "Mandado construir em 1314.")
        self.assertEqual(rb.chunk_body(Document(page_content="Sem heading.")), "Sem heading.")


if __name__ == "__main__":
    unittest.main()
