import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from langchain_core.embeddings import DeterministicFakeEmbedding  # noqa: E402

from rag_smoke_test import (  # noqa: E402
    build_vector_store,
    load_manifest,
    load_processed_documents,
    split_documents,
    split_markdown_by_page,
)


REQUIRED_METADATA = ("document_id", "title", "source_organization", "source_file", "source_page")


class SplitMarkdownByPageTests(unittest.TestCase):
    def test_pages_become_metadata_and_markers_are_removed(self):
        markdown = (
            '---\ndocument_id: "x"\n---\n\n# Title\n\n'
            "<!-- source_page: 1 -->\n\n"
            "<!-- source_page: 2 -->\n\nTexto da página dois.\n\n"
            "<!-- source_page: 3 -->\n\nTexto da página três.\n"
        )

        pages = split_markdown_by_page(markdown)

        self.assertEqual(pages, [(2, "Texto da página dois."), (3, "Texto da página três.")])


class CorpusLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = load_processed_documents()
        cls.chunks = split_documents(cls.pages)

    def test_all_accepted_documents_are_loaded(self):
        expected = {r["document_id"] for r in load_manifest()}
        loaded = {p.metadata["document_id"] for p in self.pages}
        self.assertEqual(loaded, expected)

    def test_source_page_is_propagated(self):
        joanina_pages = {
            p.metadata["source_page"]
            for p in self.pages
            if p.metadata["document_id"] == "biblioteca-joanina-uctour"
        }
        self.assertIn(3, joanina_pages)
        morcegos = [c for c in self.chunks if "morcegos" in c.page_content]
        self.assertTrue(morcegos)
        self.assertEqual(morcegos[0].metadata["source_page"], 3)

    def test_chunks_have_metadata_and_no_page_markers(self):
        for chunk in self.chunks:
            for key in REQUIRED_METADATA + ("chunk_id",):
                self.assertTrue(chunk.metadata.get(key), f"{key} missing in {chunk.metadata}")
            self.assertNotIn("source_page:", chunk.page_content)

    def test_no_empty_chunks(self):
        self.assertTrue(all(c.page_content.strip() for c in self.chunks))

    def test_chunk_ids_are_unique(self):
        ids = [c.metadata["chunk_id"] for c in self.chunks]
        self.assertEqual(len(ids), len(set(ids)))


class VectorStoreTests(unittest.TestCase):
    def test_rebuild_produces_non_empty_collection(self):
        chunks = split_documents(load_processed_documents())
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            store = build_vector_store(
                chunks, DeterministicFakeEmbedding(size=32), Path(tmp) / "chroma"
            )
            self.assertEqual(store._collection.count(), len(chunks))


if __name__ == "__main__":
    unittest.main()
