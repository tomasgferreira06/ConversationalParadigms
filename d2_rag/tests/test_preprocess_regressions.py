"""Regression tests for the corrective preprocessing pass (C1, M1, M2, M3, m1).

Issue IDs refer to d2_rag/PRE_CHUNKING_AUDIT.md. The end-to-end tests read the
generated Markdown in data/processed/, and ConsistencyTests checks that those
files are exactly what the current pipeline produces from the raw PDFs.
"""

import re
import sys
import unittest
from pathlib import Path

import pymupdf


D2_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(D2_ROOT / "scripts"))

from preprocess_documents import (  # noqa: E402
    load_manifest,
    reconstruct_paragraphs,
    render_document,
)


PAGE_MARKER_RE = re.compile(r"<!-- source_page: (\d+) -->")
COORDINATE_RE = re.compile(r"-?\d{1,3}\.\d{5,6}")


def _processed(document_id: str) -> str:
    return (D2_ROOT / "data" / "processed" / f"{document_id}.md").read_text(encoding="utf-8")


def _page(markdown: str, page_number: int) -> str:
    parts = PAGE_MARKER_RE.split(markdown)
    pages = dict(zip((int(p) for p in parts[1::2]), parts[2::2]))
    return pages[page_number]


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _raw_text(document_id: str) -> str:
    record = next(r for r in load_manifest() if r["document_id"] == document_id)
    with pymupdf.open(D2_ROOT / record["local_raw_path"]) as document:
        return "".join(page.get_text() for page in document)


class C1LetterSpacingTests(unittest.TestCase):
    """fado-e-tradicoes-academicas: letter-spaced glyph runs in the PDF text layer."""

    @classmethod
    def setUpClass(cls):
        cls.markdown = _processed("fado-e-tradicoes-academicas")
        cls.flat = _flat(cls.markdown)

    def test_spaced_words_and_dates_are_reconstructed(self):
        for spaced, joined in [
            ("E s t a b e l e c i d a", "Estabelecida"),
            ("1 5 9 3", "1593"),
            ("2 0 0 3", "2003"),
            ("1 9 4 8", "1948"),
        ]:
            with self.subTest(joined=joined):
                self.assertNotIn(spaced, self.flat)
                self.assertIn(joined, self.flat)

    def test_no_runs_of_single_character_tokens_remain(self):
        body = PAGE_MARKER_RE.sub("", self.markdown)
        self.assertIsNone(re.search(r"(?:(?<!\S)\w\s+){5,}\w(?!\S)", body))

    def test_reconstructed_sentences_keep_word_boundaries(self):
        self.assertIn("Estabelecida, em 1593, na ala norte do edifício", self.flat)
        self.assertIn("desde 16 de julho de 2003", self.flat)
        self.assertIn("O exterior é robusto, simétrico, com escassas aberturas", self.flat)

    def test_text_that_was_already_correct_is_unchanged(self):
        self.assertIn(
            "O atual complexo académico começa a ser construído em 1954, "
            "segundo o projeto dos arquitetos Alberto José Pessoa e João Abel Manta.",
            self.flat,
        )
        for word in ("Académica", "Conímbriga", "Æminium", "Associação", "canção"):
            with self.subTest(word=word):
                self.assertIn(word, self.flat)

    def test_coordinates_are_preserved_in_source_order(self):
        self.assertIn("**Coordenadas:** 40.207449, -8.429593", self.markdown)
        self.assertNotIn("c o o r d e n a das", self.markdown)
        self.assertEqual(
            COORDINATE_RE.findall(self.markdown),
            COORDINATE_RE.findall(_raw_text("fado-e-tradicoes-academicas")),
        )


class M1MapPageTests(unittest.TestCase):
    """universidade-alta-sofia-patrimonio-mundial: map labels promoted to headings."""

    @classmethod
    def setUpClass(cls):
        cls.markdown = _processed("universidade-alta-sofia-patrimonio-mundial")

    def test_map_labels_are_not_headings(self):
        for heading in [
            "### USEU DA",
            "### ÊNCIA",
            "### AGA",
            "### DONAL E INÊS",
            "### LINHA 103",
            "### PARQUES AUTOCARRO",
            "### PJ | SEF | PSP | PM | GNR",
            "### OCEANO ATLÂNTICO",
        ]:
            with self.subTest(heading=heading):
                self.assertNotIn(heading, self.markdown.splitlines())

    def test_label_only_map_pages_contain_no_text(self):
        for page_number in (34, 35, 41):
            with self.subTest(page=page_number):
                self.assertEqual(_page(self.markdown, page_number).strip(), "")

    def test_editorial_text_on_map_page_is_kept_and_label_dropped(self):
        page_40 = _flat(_page(self.markdown, 40))
        self.assertIn("Percorrer as áreas do Centro de Portugal classificadas pela UNESCO", page_40)
        self.assertNotIn("A8", page_40.split())

    def test_real_section_headings_are_preserved(self):
        numbered = re.findall(r"^## (\d+)\. ", self.markdown, flags=re.MULTILINE)
        self.assertEqual([int(n) for n in numbered], list(range(1, 32)))
        for heading in [
            "## 1. UNIVERSIDADE DE COIMBRA | PAÇO DAS ESCOLAS",
            "### PORTA FÉRREA",
            "### PAINÉIS DO TRAJE ACADÉMICO DA UNIVERSIDADE DE COIMBRA",
            "## 31. PALÁCIO DA JUSTIÇA | COLÉGIO DE SÃO TOMÁS DE AQUINO",
        ]:
            with self.subTest(heading=heading):
                self.assertIn(heading, self.markdown.splitlines())
        self.assertIn("O Roteiro dos Escritores conduz", _page(self.markdown, 39))


class CaptionPanelTests(unittest.TestCase):
    """M2/M3: the photo-caption panel must not interrupt the main text flow."""

    def test_m2_pequenitos_sentence_is_continuous(self):
        markdown = _processed("coimbra-para-os-pequenitos")
        page_1 = _page(markdown, 1)
        self.assertIn(
            "modelos que constitui o mais antigo museu de Portugal que se mantém no seu espaço de origem.",
            _flat(page_1),
        )
        panel = page_1.index("a. b. c. d. e. f. g. h.")
        self.assertGreater(panel, page_1.index("## 6. PORTUGAL DOS PEQUENITOS"))
        self.assertIn("“Tudo é minúsculo para nós", page_1[page_1.index("<!-- caption_panel -->"):])

    def test_m3_fundacao_proper_name_is_continuous(self):
        markdown = _processed("fundacao-da-nacionalidade")
        page_1 = _page(markdown, 1)
        self.assertIn(
            "com projeto do arquiteto Gonçalo Byrne. Com esta recente requalificação arquitetónica",
            _flat(page_1),
        )
        panel = page_1.index("<!-- caption_panel -->")
        self.assertGreater(panel, page_1.index("## 9. MOSTEIRO DE SANTA CLARA-A-NOVA"))
        self.assertGreater(panel, page_1.index("o classicismo."))
        self.assertIn("a. b. c. d.", page_1[panel:])
        self.assertIn("túmulo d. afonso henriques", page_1[panel:])


class M1EncliticHyphenTests(unittest.TestCase):
    """m1: a line-break hyphen before the enclitic pronoun 'se' is kept."""

    def test_enclitic_se_keeps_hyphen(self):
        self.assertEqual(
            reconstruct_paragraphs(["deste mosteiro, destaca-", "se Fernando de Bulhões"]),
            ["deste mosteiro, destaca-se Fernando de Bulhões"],
        )
        self.assertEqual(
            reconstruct_paragraphs(["pode encontrar-", "se no claustro"]),
            ["pode encontrar-se no claustro"],
        )

    def test_word_hyphenation_is_still_joined(self):
        self.assertEqual(
            reconstruct_paragraphs(["o património documental deposita-", "do no arquivo"]),
            ["o património documental depositado no arquivo"],
        )
        # 'se' as a final syllable after a consonant is ordinary hyphenation.
        self.assertEqual(
            reconstruct_paragraphs(["como ele dis-", "se ontem"]),
            ["como ele disse ontem"],
        )

    def test_fundacao_output(self):
        flat = _flat(_processed("fundacao-da-nacionalidade"))
        self.assertIn("destaca-se Fernando de Bulhões", flat)
        self.assertNotIn("destacase", flat)


class ConsistencyTests(unittest.TestCase):
    """Every processed file is exactly what the current pipeline produces."""

    def test_processed_files_match_a_fresh_render(self):
        for record in load_manifest():
            if record.get("status") != "accepted":
                continue
            with self.subTest(document_id=record["document_id"]):
                markdown, _stats = render_document(record)
                self.assertEqual(markdown, _processed(record["document_id"]))


if __name__ == "__main__":
    unittest.main()
