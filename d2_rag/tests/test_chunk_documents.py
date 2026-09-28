"""Tests for structure-aware chunking (synthetic fixtures + the real corpus, offline)."""

import json
import re
import sys
import unittest
from pathlib import Path


D2_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(D2_ROOT / "scripts"))

import chunk_documents as chunker  # noqa: E402


def _pdf_record(document_id="pdf-test", conflict=None):
    return {"document_id": document_id, "source_type": "pdf", "title": "Doc PDF",
            "source_organization": "Org", "primary_category": "city_history", "language": "pt",
            "original_filename": "doc.pdf", "conflict_notes": conflict}


def _web_record(document_id="web-test", conflict=None):
    return {"document_id": document_id, "source_type": "web_page", "title": "Doc Web",
            "source_organization": "Org", "primary_category": "gastronomy", "language": "pt",
            "url": "https://visitecoimbra.pt/doc/", "canonical_url": "https://visitecoimbra.pt/doc/",
            "conflict_notes": conflict}


def _front(document_id):
    return f'---\ndocument_id: "{document_id}"\ntitle: "T"\n---\n\n'


def _sentences(prefix, count):
    return " ".join(f"{prefix} frase número {i} com algum conteúdo descritivo." for i in range(count))


def _chunk(record, body):
    chunks, _stats = chunker.chunk_document(record, _front(record["document_id"]) + body)
    return chunks


def _body(chunk):
    return chunker.chunk_body(chunk)


class StructureParsingTests(unittest.TestCase):
    def test_headings_give_section_subsection_and_path(self):
        chunks = _chunk(_web_record(), "# Doc Web\n\n## Igrejas e Mosteiros\n\n### Sé Velha\n\nConstruída no século XII.\n\n### Sé Nova\n\nCatedral desde 1772.")
        self.assertEqual([c["section_path"] for c in chunks], [["Igrejas e Mosteiros", "Sé Velha"], ["Igrejas e Mosteiros", "Sé Nova"]])
        self.assertEqual(chunks[0]["section"], "Igrejas e Mosteiros")
        self.assertEqual(chunks[0]["subsection"], "Sé Velha")
        self.assertTrue(chunks[0]["text"].startswith("# Doc Web\n## Igrejas e Mosteiros\n### Sé Velha\n\nConstruída"))

    def test_front_matter_and_title_are_not_chunk_content(self):
        chunks = _chunk(_web_record(), "# Doc Web\n\nTexto único.")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(_body(chunks[0]), "Texto único.")
        self.assertNotIn("document_id", chunks[0]["text"])

    def test_page_markers_become_metadata(self):
        chunks = _chunk(_pdf_record(), "# Doc PDF\n\n<!-- source_page: 1 -->\n\n## A\n\nTexto da página um.")
        self.assertEqual(chunks[0]["source_pages"], [1])
        self.assertEqual(chunks[0]["source_page"], 1)
        self.assertNotIn("source_page", chunks[0]["text"])

    def test_section_continues_across_page_marker(self):
        body = ("# Doc PDF\n\n<!-- source_page: 10 -->\n\n## Torre\n\nTexto da página dez sobre a torre\n\n"
                "<!-- source_page: 11 -->\n\ncontinuação na página onze.\n\n## Escadas\n\nOutra secção.")
        chunks = _chunk(_pdf_record(), body)
        self.assertEqual(chunks[0]["section"], "Torre")
        self.assertEqual(chunks[0]["source_pages"], [10, 11])
        self.assertIsNone(chunks[0]["source_page"])
        self.assertIn("continuação na página onze.", _body(chunks[0]))
        self.assertEqual(chunks[1]["section"], "Escadas")

    def test_label_page_does_not_absorb_or_break_the_section(self):
        body = ("# Doc PDF\n\n<!-- source_page: 1 -->\n\n## Colégio\n\nTexto longo do colégio.\n\n"
                "<!-- source_page: 2 -->\n\nLegenda de fotografia\n\n"
                "<!-- source_page: 3 -->\n\nContinuação do colégio.")
        chunks = _chunk(_pdf_record(), body)
        roles = [(c["unit_role"], c["section"], _body(c)) for c in chunks]
        self.assertIn(("page_labels", None, "Legenda de fotografia"), roles)
        self.assertIn(("content", "Colégio", "Continuação do colégio."), roles)

    def test_single_blank_page_continues_but_blank_run_breaks_the_section(self):
        single = _chunk(_pdf_record(), "# D\n\n<!-- source_page: 1 -->\n\n## S\n\nA.\n\n<!-- source_page: 2 -->\n\n12\n\n<!-- source_page: 3 -->\n\nB.")
        self.assertEqual([c["section"] for c in single], ["S"])
        run = _chunk(_pdf_record(), "# D\n\n<!-- source_page: 1 -->\n\n## S\n\nA.\n\n<!-- source_page: 2 -->\n\n<!-- source_page: 3 -->\n\n<!-- source_page: 4 -->\n\nNova parte.")
        self.assertEqual([(c["section"], _body(c)) for c in run], [("S", "A."), (None, "Nova parte.")])

    def test_route_page_two_starts_a_new_region(self):
        body = ("# Rota\n\n<!-- source_page: 1 -->\n\n## 9. MOSTEIRO\n\nTexto do ponto nove.\n\n"
                "<!-- source_page: 2 -->\n\nintrodução\n\nEm 1064, Coimbra torna-se importante.")
        chunks = _chunk(_pdf_record("fundacao-da-nacionalidade"), body)
        self.assertEqual(chunks[-1]["section"], None)
        self.assertIn("Em 1064", _body(chunks[-1]))
        self.assertNotIn("Em 1064", _body(chunks[0]))

    def test_caption_panel_is_its_own_unit(self):
        chunks = _chunk(_pdf_record(), "# D\n\n<!-- source_page: 1 -->\n\n## 9. X\n\nTexto.\n\n<!-- caption_panel -->\n\nlegenda a\n\na. b.")
        self.assertEqual([(c["unit_role"], c["section"]) for c in chunks], [("content", "9. X"), ("caption_panel", None)])

    def test_printed_page_numbers_are_skipped(self):
        chunks = _chunk(_pdf_record(), "# D\n\n<!-- source_page: 1 -->\n\n8\n\n## S\n\nTexto.\n\n10 11")
        self.assertEqual([_body(c) for c in chunks], ["Texto."])


class ChunkingTests(unittest.TestCase):
    def test_short_document_is_one_chunk(self):
        chunks = _chunk(_web_record(), "# Doc Web\n\nCeira\n\nUm texto curto.\n\nOutro parágrafo curto.")
        self.assertEqual(len(chunks), 1)
        self.assertIsNone(chunks[0]["section"])

    def test_long_section_is_split_within_the_section_with_local_overlap(self):
        long_paragraph = _sentences("Santa Cruz", 40)
        body = f"# D\n\n## Mosteiro de Santa Cruz\n\n{long_paragraph}\n\n## Sé Velha\n\nTexto curto da Sé Velha."
        chunks = _chunk(_web_record(), body)
        santa_cruz = [c for c in chunks if c["section"] == "Mosteiro de Santa Cruz"]
        self.assertGreater(len(santa_cruz), 1)
        self.assertTrue(all(c["body_chars"] <= chunker.CHUNK_SIZE for c in santa_cruz))
        self.assertTrue(any(c["overlap_chars"] > 0 for c in santa_cruz[1:]))
        # The document title comes from the manifest record, not from the body.
        self.assertTrue(all(c["text"].startswith("# Doc Web\n## Mosteiro de Santa Cruz\n\n") for c in santa_cruz))
        se_velha = [c for c in chunks if c["section"] == "Sé Velha"]
        self.assertEqual(len(se_velha), 1)
        self.assertEqual(se_velha[0]["overlap_chars"], 0)
        self.assertNotIn("Santa Cruz frase", _body(se_velha[0]))
        for chunk in santa_cruz:
            self.assertNotIn("Sé Velha", _body(chunk))

    def test_coordinates_stay_with_their_entity_and_never_cross(self):
        body = (f"# D\n\n<!-- source_page: 1 -->\n\n## 2. IGREJA\n\n{_sentences('Igreja', 12)}\n\n**Coordenadas:** 40.1, -8.4\n\n"
                "## 3. ARCO\n\nTexto do arco.\n\n**Coordenadas:** 40.2, -8.5")
        chunks = _chunk(_pdf_record(), body)
        for chunk in chunks:
            if "40.1, -8.4" in chunk["text"]:
                self.assertEqual(chunk["section"], "2. IGREJA")
            if "40.2, -8.5" in chunk["text"]:
                self.assertEqual(chunk["section"], "3. ARCO")
        arco = [c for c in chunks if c["section"] == "3. ARCO"]
        self.assertEqual(len(arco), 1)
        self.assertNotIn("40.1", arco[0]["text"])

    def test_orphan_fragments_are_re_merged_inside_the_unit(self):
        pieces = chunker.split_unit_body(("x" * 700 + ". ") * 2 + "\n\n**Coordenadas:** 1, 2", chunker._splitter())
        self.assertFalse(any(piece.strip() == "**Coordenadas:** 1, 2" for _start, piece in pieces))

    def test_blockquotes_and_lists_stay_in_their_section(self):
        body = "# D\n\n## Repúblicas\n\n> \"Uma citação.\"\n\n1. República Baco\n2. República dos Kagados"
        chunks = _chunk(_web_record(), body)
        self.assertEqual(len(chunks), 1)
        self.assertIn("> \"Uma citação.\"", _body(chunks[0]))
        self.assertIn("1. República Baco\n2. República dos Kagados", _body(chunks[0]))

    def test_web_provenance_and_conflict_notes(self):
        chunks = _chunk(_web_record(conflict="conflito X"), "# Doc Web\n\n## A\n\nTexto.")
        self.assertEqual(chunks[0]["url"], "https://visitecoimbra.pt/doc/")
        self.assertIsNone(chunks[0]["source_pages"])
        self.assertIsNone(chunks[0]["source_page"])
        self.assertEqual(chunks[0]["conflict_notes"], "conflito X")

    def test_chunk_ids_are_sequential_unique_and_deterministic(self):
        body = "# D\n\n## A\n\nUm.\n\n## B\n\nDois."
        first, second = _chunk(_web_record(), body), _chunk(_web_record(), body)
        self.assertEqual([c["chunk_id"] for c in first], ["web-test::c0001", "web-test::c0002"])
        self.assertEqual(first, second)


def _corpus_chunks():
    return [json.loads(l) for l in (D2_ROOT / "data" / "chunks" / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]


def _find(chunks, document_id, needle):
    found = [c for c in chunks if c["document_id"] == document_id and needle in _body(c)]
    if not found:
        raise AssertionError(f"{needle!r} not found in {document_id}")
    return found[0]


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunks = _corpus_chunks()

    def test_unknown_document_is_an_error_not_an_exit(self):
        with self.assertRaisesRegex(ValueError, "nope"):
            chunker.load_records(["nope"])

    def test_persisted_chunks_are_valid_and_reproducible(self):
        self.assertEqual(chunker.validate_chunks(self.chunks), [])
        fresh, _ = chunker.chunk_corpus(chunker.load_records())
        self.assertEqual(fresh, self.chunks)
        self.assertEqual(len({c["document_id"] for c in self.chunks}), 32)

    def test_every_chunk_has_required_metadata(self):
        for chunk in self.chunks:
            with self.subTest(chunk=chunk["chunk_id"]):
                for key in ("document_id", "source_type", "title", "primary_category", "source_organization"):
                    self.assertTrue(chunk[key])
                self.assertTrue(_body(chunk).strip())

    def test_facts_carry_the_right_section(self):
        cases = [
            ("fundacao-da-nacionalidade", "Fundado em 1131", "section", "2. IGREJA DE SANTA CRUZ | PANTEÃO NACIONAL"),
            ("universidade-alta-sofia-patrimonio-mundial", "Fundado, em 1131", "section", "24. MOSTEIRO DE SANTA CRUZ - PANTEÃO NACIONAL"),
            ("fado-e-tradicoes-academicas", "O exterior é robusto", "section", "7. SÉ VELHA"),
            ("universidade-alta-sofia-patrimonio-mundial", "com projeto do francês Mestre Roberto", "section", "21. SÉ VELHA"),
            ("biblioteca-joanina-uctour", "duas colónias de morcegos", "section", "Piso Nobre"),
            ("biblioteca-joanina-uctour", "A sua construção ficou concluída em 1728", "section", "Biblioteca Joanina"),
            ("coimbra-para-os-pequenitos", "projetado por Cassiano Branco", "section", "6. PORTUGAL DOS PEQUENITOS"),
            ("fundacao-da-nacionalidade", "projetado por Cassiano Branco", "section", "7. PORTUGAL DOS PEQUENITOS"),
            ("web-visitecoimbra-museus", "um dos mais importantes museus de belas-artes", "section", "Museu Nacional de Machado de Castro"),
            ("web-visitecoimbra-docaria-conventual-de-coimbra", "Os Crúzios são doces conventuais", "subsection", "Crúzios"),
            ("web-visitecoimbra-heranca-cultural-e-religiosa", "Fundado pela Rainha Santa Isabel", "subsection", "Mosteiro de Santa Clara-a-Velha"),
        ]
        for document_id, needle, field, expected in cases:
            with self.subTest(document_id=document_id, needle=needle):
                self.assertEqual(_find(self.chunks, document_id, needle)[field], expected)

    def test_real_page_continuations(self):
        torre = _find(self.chunks, "universidade-alta-sofia-patrimonio-mundial", "bastante italianizantes")
        self.assertEqual(torre["section_path"], ["1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS", "TORRE"])
        self.assertEqual(torre["source_pages"], [10, 11])
        santa_rita = _find(self.chunks, "universidade-alta-sofia-patrimonio-mundial", "chega a Coimbra")
        self.assertEqual(santa_rita["source_pages"], [24, 25])
        prisao = _find(self.chunks, "biblioteca-joanina-uctour", "baixa da cidade")
        self.assertEqual(prisao["section"], "Prisão Académica")
        self.assertIn(4, prisao["source_pages"])
        colegio = _find(self.chunks, "universidade-alta-sofia-patrimonio-mundial", "Fundado em 1574")
        self.assertEqual(colegio["section_path"], ["1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS", "COLÉGIO DE SÃO PEDRO"])

    def test_new_regions_are_not_attached_to_previous_sections(self):
        roteiros = _find(self.chunks, "universidade-alta-sofia-patrimonio-mundial", "O Roteiro dos Jardins Históricos")
        self.assertIsNone(roteiros["section"])
        intro = _find(self.chunks, "fundacao-da-nacionalidade", "Em 1064, Coimbra torna-se")
        self.assertIsNone(intro["section"])
        self.assertEqual(intro["source_pages"], [2])
        joanina_label = _find(self.chunks, "universidade-alta-sofia-patrimonio-mundial", "Casa da Livraria | Biblioteca Joanina")
        self.assertEqual(joanina_label["unit_role"], "page_labels")

    def test_every_coordinate_line_belongs_to_the_preceding_heading(self):
        checked = 0
        for chunk in (c for c in self.chunks if c["source_type"] == "pdf"):
            markdown = (D2_ROOT / "data" / "processed" / f"{chunk['document_id']}.md").read_text(encoding="utf-8")
            for coordinates in re.findall(r"\*\*Coordenadas:\*\* ([-\d., ]+\d)", _body(chunk)):
                # The source may give two points the same coordinates
                # (Escritores 12 and 13), so accept any occurrence's heading.
                marker = f"**Coordenadas:** {coordinates}"
                headings = {
                    re.findall(r"^## (.+)$", markdown[:m.start()], flags=re.MULTILINE)[-1]
                    for m in re.finditer(re.escape(marker), markdown)
                }
                self.assertIn(chunk["section"], headings)
                checked += 1
        self.assertGreater(checked, 50)

    def test_web_chunks_have_url_and_no_pages(self):
        for chunk in (c for c in self.chunks if c["source_type"] == "web_page"):
            self.assertTrue(chunk["url"].startswith("https://visitecoimbra.pt/"))
            self.assertIsNone(chunk["source_pages"])

    def test_conflict_notes_reach_the_conflicting_documents(self):
        for document_id in ("web-visitecoimbra-heranca-cultural-e-religiosa", "web-visitecoimbra-museus"):
            chunks = [c for c in self.chunks if c["document_id"] == document_id]
            self.assertTrue(chunks and all("Santa Clara-a-Velha" in c["conflict_notes"] for c in chunks))


if __name__ == "__main__":
    unittest.main()
